"""Demo 4 — symmetric double quantum well and tunnelling-induced splitting.

Two identical GaAs wells separated by an AlGaAs barrier.  With a thin barrier
the wells share their electrons and the lowest pair splits into a symmetric and
an antisymmetric combination; with a thick barrier the pair becomes degenerate
and each state can localise anywhere in the two-dimensional degenerate subspace.

The scientific content of the demo is the *measurement* of that behaviour:
per-well probabilities, parity of the envelope, the E2-E1 splitting, and whether
any of it survives a larger simulation box.
"""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

import numpy as np

import analysis
import layers
import outputs
import plots as plotting
import quantum1d
import sweeps
from demo_workflow import DemoError, write_csv, write_json_atomically

PLOT_SET: tuple[tuple[str, str], ...] = (
    ("band_diagram.png", "Conduction band with electron eigenenergies"),
    ("wavefunctions.png", "Electron envelope amplitudes"),
    ("probability_densities.png", "Electron probability densities"),
    ("band_edge_with_display_offsets.png", "Band edge with display-offset densities"),
    ("energies_vs_center_barrier.png", "Lowest energies versus centre-barrier thickness"),
    ("splitting_vs_center_barrier.png", "E2 − E1 versus centre-barrier thickness"),
    ("localization_vs_center_barrier.png", "Per-well localisation versus centre barrier"),
    ("thin_vs_thick_barrier_wavefunctions.png", "Thin- versus thick-barrier envelopes"),
    ("padding_check.png", "Energies versus quantum-region padding"),
    ("state_tracking_confidence.png", "State-tracking confidence across the sweep"),
)


def build_stack(cfg: Mapping[str, Any]) -> layers.LayerStack:
    """Resolve the five-layer stack from the demo's scientific parameters."""

    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    return layers.symmetric_double_well(
        well_width_nm=float(scientific["well_width_nm"]),
        centre_barrier_nm=float(scientific["center_barrier_nm"]),
        left_outer_barrier_nm=float(scientific["left_outer_barrier_nm"]),
        right_outer_barrier_nm=float(scientific["right_outer_barrier_nm"]),
        aluminum_fraction=float(scientific["aluminum_fraction"]),
        active_grid_spacing_nm=float(numerical["active_region_grid_spacing_nm"]),
        exterior_grid_spacing_nm=float(numerical["exterior_grid_spacing_nm"]),
    )


def region_name(cfg: Mapping[str, Any]) -> str:
    return str((cfg.get("analysis") or {}).get("quantum_region_name", "dqw"))


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Template substitutions for one configuration."""

    stack = build_stack(cfg)
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(float(numerical["quantum_region_padding_nm"]))
    return {
        "temperature_K": cfg["scientific"]["temperature_K"],
        "number_of_states": int(numerical["number_of_states"]),
        "quantum_region_name": region_name(cfg),
        "quantum_start_nm": f"{start:.9g}",
        "quantum_end_nm": f"{end:.9g}",
        "grid_lines": stack.grid_lines(),
        "structure_regions": stack.structure_regions(contact_name="qw_contact"),
    }


def structure_centre_nm(stack: layers.LayerStack) -> float:
    """Mid-point of the centre barrier: the symmetry plane of the structure."""

    low, high = stack.interval("centre_barrier")
    return 0.5 * (low + high)


def analyse_case(
    cfg: Mapping[str, Any], raw: Path, extracted: Path, plots_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse one completed run and measure the coupled-well observables."""

    validation_cfg = cfg["validation"]
    analysis_cfg = cfg.get("analysis") or {}
    stack = build_stack(cfg)
    regions = quantum1d.region_map(stack.intervals())
    padding = float(cfg["numerical"]["quantum_region_padding_nm"])
    window = stack.quantum_region_nm(padding)

    profile = outputs.load_profile(
        str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
    )
    run = quantum1d.parse_one_band_run(
        raw,
        profile=profile,
        region_name=region_name(cfg),
        bandedge_columns=cfg["outputs"]["bandedge_columns"],
    )
    centre = structure_centre_nm(stack)
    states = quantum1d.state_table(
        run,
        regions=regions,
        minimum_confined_probability=float(
            validation_cfg.get("minimum_confined_probability", 0.6)
        ),
        normalisation_tolerance=float(validation_cfg.get("normalization_tolerance", 1e-3)),
        boundary_edge_fraction=float(analysis_cfg.get("boundary_edge_fraction", 0.05)),
        symmetry_centre_nm=centre,
        quantum_window_nm=window,
    )
    if not states:
        raise DemoError("no electron states were parsed from the run output.")

    matrices = quantum1d.envelope_matrices(run)
    rows = [state.as_row() for state in states]
    write_csv(
        extracted / "states.csv",
        {key: np.asarray([row.get(key) for row in rows]) for key in rows[0]},
    )
    if matrices:
        write_json_atomically(
            extracted / "envelope_matrices.json",
            {name: matrix.tolist() for name, matrix in matrices.items()},
        )
    write_csv(
        extracted / "band_profile.csv",
        {
            "position_nm": run.position_nm,
            "conduction_band_eV": run.conduction_eV,
        },
    )
    if run.envelopes is not None:
        write_csv(
            extracted / "envelopes.csv",
            {
                "position_nm": run.state_position_nm,
                **{
                    f"psi_{index + 1}_nm^-0.5": run.envelopes[:, index]
                    for index in range(run.envelopes.shape[1])
                },
            },
        )
    densities = _normalised_densities(run)
    write_csv(
        extracted / "probability_densities.csv",
        {
            "position_nm": run.state_position_nm,
            **{
                f"probability_density_{index + 1}_nm^-1": densities[:, index]
                for index in range(densities.shape[1])
            },
        },
    )

    left = [state.region_probabilities.get("left_well", 0.0) for state in states]
    right = [state.region_probabilities.get("right_well", 0.0) for state in states]
    centre_barrier = [
        state.region_probabilities.get("centre_barrier", 0.0) for state in states
    ]
    energies = [state.energy_eV for state in states]
    splittings = analysis.energy_splittings_meV(energies)
    balance = [abs(l - r) for l, r in zip(left, right)]
    tolerance = float(analysis_cfg.get("well_balance_tolerance", 0.10))

    log_text = outputs.solver_log_text(raw)
    log_checks = outputs.scan_log_markers(
        log_text,
        completion_markers=validation_cfg.get("completion_markers", ()),
        fatal_markers=validation_cfg.get("fatal_markers", ()),
        warning_markers=validation_cfg.get("convergence_warning_markers", ()),
    )
    log_checks.update(outputs.completion_evidence(raw))

    observables: dict[str, Any] = {
        "center_barrier_nm": float(cfg["scientific"]["center_barrier_nm"]),
        "quantum_region_padding_nm": padding,
        "structure_centre_nm": centre,
        "grid_points": int(run.position_nm.size),
        "state_count": len(states),
        "electron_energies_eV": energies,
        "E1_eV": energies[0],
        "E2_eV": energies[1] if len(energies) > 1 else None,
        "E3_eV": energies[2] if len(energies) > 2 else None,
        **splittings,
        "probability_left_well_state1": left[0],
        "probability_right_well_state1": right[0],
        "probability_centre_barrier_state1": centre_barrier[0],
        "probability_left_well_state2": left[1] if len(left) > 1 else None,
        "probability_right_well_state2": right[1] if len(right) > 1 else None,
        "probability_centre_barrier_state2": centre_barrier[1] if len(centre_barrier) > 1 else None,
        "centroid_state1_nm": states[0].centroid_nm,
        "centroid_state2_nm": states[1].centroid_nm if len(states) > 1 else None,
        "parity_state1": states[0].parity_label,
        "parity_state2": states[1].parity_label if len(states) > 1 else None,
        "parity_confidence_state1": states[0].parity_confidence,
        "parity_confidence_state2": states[1].parity_confidence if len(states) > 1 else None,
        # A state above the barrier legitimately reaches the Dirichlet walls, so
        # the domain-size diagnostic is only meaningful for the bound states.
        "maximum_boundary_probability_bound_states": max(
            [state.boundary_probability for state in states if state.bound] or [0.0]
        ),
        # The scientific object of this demo is the lowest tunnelling pair.
        # A third, very shallow bound state appears for the 1 and 2 nm barriers
        # in the licensed run and is deliberately retained as a diagnostic.
        "maximum_boundary_probability_lowest_pair": max(
            [state.boundary_probability for state in states[:2] if state.bound]
            or [0.0]
        ),
        "maximum_boundary_probability_all_states": max(
            state.boundary_probability for state in states
        ),
        "maximum_well_imbalance": max(balance[:2]) if len(balance) >= 2 else balance[0],
        "bound_state_count": sum(1 for state in states if state.bound),
        "all_states_bound": all(bool(state.bound) for state in states),
        "state_rows": rows,
    }
    if "overlap" in matrices and matrices["overlap"].shape[0] >= 2:
        observables["overlap_state1_state2"] = float(matrices["overlap"][0, 1])
    if "position_matrix_nm" in matrices and matrices["position_matrix_nm"].shape[0] >= 2:
        observables["z12_nm_from_envelopes"] = float(matrices["position_matrix_nm"][0, 1])

    minimum_parity = float(validation_cfg.get("minimum_parity_confidence", 0.8))
    validation: dict[str, Any] = {
        **{key: value for key, value in log_checks.items() if isinstance(value, bool)},
        "energies_finite_and_ordered": bool(
            np.all(np.isfinite(energies)) and np.all(np.diff(energies) > 0)
        ),
        "probability_normalized": all(state.normalised for state in states),
        "at_least_two_bound_states": sum(1 for state in states if state.bound) >= 2,
        "lowest_pair_boundary_probability_small": bool(
            observables["maximum_boundary_probability_lowest_pair"]
            <= float(validation_cfg.get("maximum_boundary_probability", 1e-4))
        ),
        "lowest_pair_balanced_between_identical_wells": bool(
            observables["maximum_well_imbalance"] <= tolerance
        ),
        "lowest_pair_has_definite_parity": bool(
            states[0].parity_confidence is not None
            and states[0].parity_confidence >= minimum_parity
            and (
                len(states) < 2
                or (
                    states[1].parity_confidence is not None
                    and states[1].parity_confidence >= minimum_parity
                )
            )
        ),
        "lowest_pair_is_symmetric_then_antisymmetric": bool(
            states[0].parity_label == "symmetric"
            and (len(states) < 2 or states[1].parity_label == "antisymmetric")
        ),
    }
    validation["log_files"] = log_checks.get("fatal_markers_found", [])

    _per_case_plots(cfg, run, states, regions, plots_dir)
    return observables, validation


def _per_case_plots(
    cfg: Mapping[str, Any],
    run: quantum1d.OneBandRun,
    states: Sequence[analysis.StateObservables],
    regions: Mapping[str, tuple[float, float]],
    plots_dir: Path,
) -> None:
    if not cfg["outputs"].get("write_plots", True):
        return
    title = f"centre barrier = {cfg['scientific']['center_barrier_nm']} nm"
    energies = [state.energy_eV for state in states]
    plotting.band_diagram(
        plots_dir / "band_diagram.png",
        title=f"Conduction band and eigenenergies ({title})",
        position_nm=run.position_nm,
        conduction_eV=run.conduction_eV,
        energies_eV=energies,
        regions=regions,
    )
    if run.envelopes is not None:
        plotting.envelope_plot(
            plots_dir / "wavefunctions.png",
            title=f"Envelope amplitudes ({title})",
            position_nm=run.state_position_nm,
            envelopes=run.envelopes,
            regions=regions,
        )
    normalised = _normalised_densities(run)
    plotting.density_plot(
        plots_dir / "probability_densities.png",
        title=f"Probability densities ({title})",
        position_nm=run.state_position_nm,
        densities=normalised,
        regions=regions,
    )
    plotting.band_with_display_offsets(
        plots_dir / "band_edge_with_display_offsets.png",
        title=f"Band edge with display-offset densities ({title})",
        position_nm=run.position_nm,
        conduction_eV=run.conduction_eV,
        energies_eV=energies,
        densities=_interpolate_to(run.position_nm, run.state_position_nm, normalised),
        regions=regions,
    )


def _normalised_densities(run: quantum1d.OneBandRun) -> np.ndarray:
    columns = []
    for index in range(min(run.state_count, run.densities.shape[1])):
        normalised, _ = analysis.normalise_density(
            run.state_position_nm, run.densities[:, index]
        )
        columns.append(normalised)
    return np.column_stack(columns) if columns else np.empty((run.state_position_nm.size, 0))


def _interpolate_to(
    target_x: np.ndarray, source_x: np.ndarray, values: np.ndarray
) -> np.ndarray:
    if values.size == 0:
        return values
    return np.column_stack(
        [
            np.interp(target_x, source_x, values[:, index], left=0.0, right=0.0)
            for index in range(values.shape[1])
        ]
    )


def _feature_vectors(result: sweeps.CaseResult) -> list[list[float]] | None:
    """Physical features used to follow states between different geometries.

    Envelope overlap is not usable here: changing the centre barrier moves the
    wells, so the same physical state lives at different absolute coordinates.
    The features are therefore geometry-relative.
    """

    rows = result.observables.get("state_rows")
    if not rows:
        return None
    centre = float(result.observables.get("structure_centre_nm", 0.0))
    vectors: list[list[float]] = []
    for row in rows:
        vectors.append(
            [
                float(row.get("probability_left_well") or 0.0),
                float(row.get("probability_right_well") or 0.0),
                float(row.get("probability_centre_barrier") or 0.0),
                float(row.get("centroid_nm") or 0.0) - centre,
                float(row.get("energy_eV") or 0.0),
            ]
        )
    return vectors


def track_across_sweep(
    results: Sequence[sweeps.CaseResult], minimum_confidence: float
) -> list[dict[str, Any]]:
    """Follow each state from one centre-barrier thickness to the next."""

    rows: list[dict[str, Any]] = []
    previous: tuple[sweeps.CaseResult, list[list[float]]] | None = None
    for result in results:
        features = _feature_vectors(result)
        if features is None:
            rows.append(
                {
                    "case_id": result.spec.case_id,
                    "tracking_available": False,
                    "reason": "no parsed states on this machine",
                }
            )
            continue
        if previous is None:
            previous = (result, features)
            rows.append(
                {
                    "case_id": result.spec.case_id,
                    "tracking_available": True,
                    "method": "reference_point",
                    "minimum_confidence": None,
                }
            )
            continue
        tracking = analysis.track_states(
            previous_features=previous[1],
            current_features=features,
            minimum_confidence=minimum_confidence,
        )
        rows.append(
            {
                "case_id": result.spec.case_id,
                "previous_case_id": previous[0].spec.case_id,
                "tracking_available": True,
                "method": tracking.method,
                "assignment": ";".join(str(value + 1) for value in tracking.assignment),
                "confidence": ";".join(f"{value:.4f}" for value in tracking.confidence),
                "minimum_confidence": min(tracking.confidence) if tracking.confidence else None,
                "ambiguous_states": ";".join(str(index + 1) for index in tracking.ambiguous),
                "is_confident": tracking.is_confident,
            }
        )
        previous = (result, features)
    return rows


def _series(
    results: Sequence[sweeps.CaseResult], parameter: str, observable: str
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for result in results:
        value = result.observables.get(observable)
        swept = result.spec.swept.get(parameter)
        if value is None or swept is None:
            continue
        xs.append(float(swept))
        ys.append(float(value))
    return xs, ys


def _sweep_plots(
    parent: Path, barrier_results: Sequence[sweeps.CaseResult],
    padding_results: Sequence[sweeps.CaseResult],
    tracking_rows: Sequence[Mapping[str, Any]],
) -> None:
    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    parameter = "center_barrier_nm"
    plotting.line_plot(
        plots_dir / "energies_vs_center_barrier.png",
        title="Lowest electron energies versus centre-barrier thickness",
        xlabel="Centre-barrier thickness (nm)",
        ylabel="Energy (eV)",
        series={
            "E1": _series(barrier_results, parameter, "E1_eV"),
            "E2": _series(barrier_results, parameter, "E2_eV"),
            "E3": _series(barrier_results, parameter, "E3_eV"),
        },
    )
    plotting.line_plot(
        plots_dir / "splitting_vs_center_barrier.png",
        title="Symmetric–antisymmetric splitting versus centre-barrier thickness",
        xlabel="Centre-barrier thickness (nm)",
        ylabel="E2 − E1 (meV)",
        series={"E2 − E1": _series(barrier_results, parameter, "E21_meV")},
        logy=True,
    )
    plotting.line_plot(
        plots_dir / "localization_vs_center_barrier.png",
        title="Per-well localisation of the lowest pair",
        xlabel="Centre-barrier thickness (nm)",
        ylabel="Integrated probability",
        series={
            "state 1, left well": _series(barrier_results, parameter, "probability_left_well_state1"),
            "state 1, right well": _series(barrier_results, parameter, "probability_right_well_state1"),
            "state 2, left well": _series(barrier_results, parameter, "probability_left_well_state2"),
            "state 2, right well": _series(barrier_results, parameter, "probability_right_well_state2"),
            "state 1, centre barrier": _series(
                barrier_results, parameter, "probability_centre_barrier_state1"
            ),
        },
    )
    plotting.line_plot(
        plots_dir / "padding_check.png",
        title="E1 and E2 versus quantum-region padding (numerical control)",
        xlabel="Quantum-region padding (nm)",
        ylabel="Energy (eV)",
        series={
            "E1": _series(padding_results, "quantum_region_padding_nm", "E1_eV"),
            "E2": _series(padding_results, "quantum_region_padding_nm", "E2_eV"),
        },
    )
    confidences = [
        (index, float(row["minimum_confidence"]))
        for index, row in enumerate(tracking_rows, start=1)
        if row.get("minimum_confidence") is not None
    ]
    plotting.line_plot(
        plots_dir / "state_tracking_confidence.png",
        title="Minimum state-tracking confidence along the sweep",
        xlabel="Sweep step",
        ylabel="Minimum |similarity| of the assignment",
        series={
            "confidence": (
                [item[0] for item in confidences],
                [item[1] for item in confidences],
            )
        },
    )
    _copy_representative_case_plots(plots_dir, barrier_results)
    _representative_plot(plots_dir, barrier_results)


def _copy_representative_case_plots(
    plots_dir: Path, results: Sequence[sweeps.CaseResult]
) -> None:
    """Promote one real, representative case into the parent evidence set."""

    usable = [result for result in results if result.solver_success]
    if not usable:
        return
    reference = min(
        usable,
        key=lambda item: abs(float(item.spec.swept["center_barrier_nm"]) - 4.0),
    )
    for filename in (
        "band_diagram.png",
        "wavefunctions.png",
        "probability_densities.png",
        "band_edge_with_display_offsets.png",
    ):
        source = reference.run_dir / "plots" / filename
        if source.is_file():
            shutil.copy2(source, plots_dir / filename)


def _representative_plot(
    plots_dir: Path, results: Sequence[sweeps.CaseResult]
) -> None:
    """Plot the actual lowest-pair envelopes for the sweep endpoints."""

    usable = [result for result in results if result.solver_success]
    target = plots_dir / "thin_vs_thick_barrier_wavefunctions.png"
    if len(usable) < 2:
        plotting.placeholder(
            target,
            "Thin- versus thick-barrier envelopes",
            reason=plotting.PLACEHOLDER_TEXT,
        )
        return
    thin = min(usable, key=lambda item: float(item.spec.swept["center_barrier_nm"]))
    thick = max(usable, key=lambda item: float(item.spec.swept["center_barrier_nm"]))
    series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    for label, result in (("thin barrier", thin), ("thick barrier", thick)):
        path = result.run_dir / "extracted" / "envelopes.csv"
        if not path.is_file():
            continue
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        if data.ndim != 2 or data.shape[1] < 3:
            continue
        centre = float(result.observables.get("structure_centre_nm", 0.0))
        barrier = float(result.spec.swept["center_barrier_nm"])
        for state in range(2):
            series[f"{label} ({barrier:g} nm): ψ{state + 1}"] = (
                data[:, 0] - centre,
                data[:, 1 + state],
            )
    plotting.line_plot(
        target,
        title="Lowest-pair envelopes for thin and thick centre barriers",
        xlabel="Position relative to structure centre (nm)",
        ylabel="Envelope amplitude ψ (nm$^{-1/2}$)",
        series=series,
        markers=False,
    )


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    sweep_cfg = cfg.get("sweeps") or {}
    analysis_cfg = cfg.get("analysis") or {}
    minimum_confidence = float(
        analysis_cfg.get(
            "minimum_state_tracking_confidence",
            cfg["validation"].get("minimum_state_tracking_confidence", 0.6),
        )
    )

    barrier_cases = sweeps.single_variable_cases(
        cfg, "center_barrier_nm", sweep_cfg.get("center_barrier_nm", [])
    )
    padding_cases = sweeps.single_variable_cases(
        cfg,
        "quantum_region_padding_nm",
        sweep_cfg.get("quantum_region_padding_nm", []),
        prefix="padding_",
    )
    all_cases = [*barrier_cases, *padding_cases]
    if not all_cases:
        raise DemoError("demo.yaml declares no sweep values for Demo 4.")

    results: list[sweeps.CaseResult] = []
    for case in all_cases:
        run_dir = context.parent / "runs" / case.case_id
        results.append(
            sweeps.execute_case(
                demo_dir=context.demo_dir,
                spec=case,
                machine=context.machine,
                run_dir=run_dir,
                render_values=render_values,
                analyse=analyse_case,
                dependency_report=context.dependency_report,
            )
        )
    barrier_results = results[: len(barrier_cases)]
    padding_results = results[len(barrier_cases) :]

    sweeps.write_sweep_summary(context.parent, results)
    failed, suspicious = sweeps.write_failed_and_suspicious(context.parent, results)
    tracking_rows = track_across_sweep(barrier_results, minimum_confidence)
    sweeps.write_state_tracking(context.parent, tracking_rows)
    splitting_rows = [
        {
            "center_barrier_nm": result.spec.swept.get("center_barrier_nm"),
            "E1_eV": result.observables.get("E1_eV"),
            "E2_eV": result.observables.get("E2_eV"),
            "E21_meV": result.observables.get("E21_meV"),
            "overlap_state1_state2": result.observables.get("overlap_state1_state2"),
            "maximum_well_imbalance": result.observables.get("maximum_well_imbalance"),
            "parity_state1": result.observables.get("parity_state1"),
            "parity_state2": result.observables.get("parity_state2"),
            "status": result.status,
        }
        for result in barrier_results
    ]
    sweeps.write_table(context.parent, "splitting_table", splitting_rows)
    _sweep_plots(context.parent, barrier_results, padding_results, tracking_rows)
    plotting.ensure_plot_set(
        context.parent / "plots",
        PLOT_SET,
        reason=(
            "Per-case figure: produced inside each runs/<case>/plots directory once "
            "a licensed solver has run. No solver output on this machine."
        ),
    )

    splittings = [
        (float(row["center_barrier_nm"]), float(row["E21_meV"]))
        for row in splitting_rows
        if row.get("E21_meV") is not None and row.get("center_barrier_nm") is not None
    ]
    splittings.sort()
    splitting_decreases: bool | None = None
    if len(splittings) >= 2:
        splitting_decreases = all(
            later[1] <= earlier[1] * 1.05
            for earlier, later in zip(splittings, splittings[1:])
        )
    padding_stable: bool | None = None
    padding_differences_meV: dict[str, float] = {}
    for state_key in ("E1_eV", "E2_eV"):
        values = [
            float(result.observables[state_key])
            for result in padding_results
            if result.observables.get(state_key) is not None
        ]
        if len(values) >= 2:
            padding_differences_meV[state_key] = 1000.0 * (max(values) - min(values))
    if len(padding_differences_meV) == 2:
        padding_stable = all(
            difference <= float(
                cfg["validation"].get("absolute_energy_tolerance_meV", 0.5)
            )
            for difference in padding_differences_meV.values()
        )
    tracking_available = any(
        row.get("tracking_available") for row in tracking_rows
    )

    manifest = sweeps.write_sweep_manifest(
        context.parent,
        cfg=cfg,
        machine=context.machine,
        results=results,
        dependency_report=context.dependency_report,
        parser_provenance={"profile": cfg["outputs"].get("parser_profile")},
        extra={
            "splitting_decreases_with_barrier": splitting_decreases,
            "energies_stable_under_padding": padding_stable,
            "padding_energy_range_meV": padding_differences_meV,
            "state_tracking_confident": (
                all(row.get("is_confident", False) for row in tracking_rows)
                if tracking_available
                else None
            ),
        },
    )
    sweeps.write_validation_report(
        context.parent,
        cfg=cfg,
        manifest=manifest,
        registry_record=context.registry_record,
        dependency_report=context.dependency_report,
        criteria=[
            (
                "every sweep point produced a generated input",
                all(
                    (result.run_dir / "generated_input").is_dir() for result in results
                ),
                f"{len(results)} case directories written",
            ),
            (
                "no sweep point was discarded",
                len(results) == len(all_cases),
                f"{len(failed)} failed/skipped and {len(suspicious)} suspicious rows retained",
            ),
            (
                "lowest pair is symmetric then antisymmetric",
                _all_true(results, "lowest_pair_is_symmetric_then_antisymmetric"),
                "parity measured from the envelope, not from the state index",
            ),
            (
                "lowest pair balanced between the identical wells",
                _all_true(results, "lowest_pair_balanced_between_identical_wells"),
                "|P_left - P_right| within the configured tolerance",
            ),
            (
                "E2 − E1 decreases as the centre barrier thickens",
                splitting_decreases,
                "monotone within a 5% allowance for solver noise",
            ),
            (
                "lowest tunnelling pair has negligible boundary probability",
                _all_true(results, "lowest_pair_boundary_probability_small"),
                "the lowest pair is tested; leakage of an additional shallow "
                "bound state is retained separately as a diagnostic",
            ),
            (
                "energies stable under larger quantum-region padding",
                padding_stable,
                "difference compared against absolute_energy_tolerance_meV",
            ),
            (
                "state-tracking diagnostics retained at every sweep point",
                len(tracking_rows) == len(barrier_results),
                "parity identifies the lowest pair; feature confidence may fall "
                "when the pair becomes physically near-degenerate",
            ),
        ],
        notes=[
            "Physics enabled: 1D classical band edges and the one-band Γ electron "
            "Schrödinger equation. Doping, Poisson, strain, k·p, transport, and "
            "optics are all absent.",
            "State tracking uses per-well probabilities, centroid relative to the "
            "structure centre, and energy — never the eigenvalue index.",
            "A near-degenerate thick-barrier pair may localise arbitrarily within "
            "its degenerate subspace; that is physics, not a solver defect.",
            "For the 1 and 2 nm barriers, a third shallow state has more boundary "
            "weight than the lowest pair. It is reported but does not invalidate "
            "the tunnelling-pair result.",
        ],
    )
    return sweeps.finish_run(context, results=results, manifest=manifest)


def _all_true(results: Sequence[sweeps.CaseResult], key: str) -> bool | None:
    values = [
        result.validation.get(key)
        for result in results
        if result.solver_success and key in result.validation
    ]
    if not values:
        return None
    return all(bool(value) for value in values)
