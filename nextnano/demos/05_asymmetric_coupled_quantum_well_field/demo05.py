"""Demo 5 — asymmetric coupled quantum well tuned by an electric field.

A wide well and a narrow well share a thin barrier.  At zero field the two
single-well levels are detuned by the width difference; a field tilts the
structure and can bring them into resonance, at which point they hybridise and
repel — an avoided crossing.  On either side of it the *same eigenvalue index*
describes a physically different state, which is why every number here is
followed by envelope overlap rather than by index.
"""

from __future__ import annotations

from pathlib import Path
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
    ("band_diagrams_selected_fields.png", "Tilted conduction band at selected fields"),
    ("energies_vs_field.png", "Electron energies versus electric field"),
    ("centroid_vs_field.png", "State centroid <z> versus electric field"),
    ("well_probability_vs_field.png", "Per-well probability versus electric field"),
    ("spacings_vs_field.png", "E2 − E1 and E3 − E2 versus electric field"),
    ("wavefunctions_near_crossing.png", "Envelopes before, near, and after a crossing"),
    ("state_tracking_confidence.png", "State-tracking confidence versus field"),
    ("overlap_matrix.png", "Envelope overlap matrix at the strongest field step"),
    ("field_unit_check.png", "Requested versus solver-reported electric field"),
    ("padding_check.png", "Energies versus quantum-region padding"),
)

FIELD_DIRECTIONS: dict[str, str] = {
    "+x": "[1, 0, 0]",
    "-x": "[-1, 0, 0]",
}


def build_stack(cfg: Mapping[str, Any]) -> layers.LayerStack:
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    return layers.asymmetric_double_well(
        left_well_width_nm=float(scientific["wide_well_width_nm"]),
        right_well_width_nm=float(scientific["narrow_well_width_nm"]),
        centre_barrier_nm=float(scientific["center_barrier_nm"]),
        left_outer_barrier_nm=float(scientific["left_outer_barrier_nm"]),
        right_outer_barrier_nm=float(scientific["right_outer_barrier_nm"]),
        aluminum_fraction=float(scientific["aluminum_fraction"]),
        active_grid_spacing_nm=float(numerical["active_region_grid_spacing_nm"]),
        exterior_grid_spacing_nm=float(numerical["exterior_grid_spacing_nm"]),
    )


def region_name(cfg: Mapping[str, Any]) -> str:
    return str((cfg.get("analysis") or {}).get("quantum_region_name", "cqw"))


def direction_vector(cfg: Mapping[str, Any]) -> str:
    key = str(cfg["scientific"].get("field_direction", "+x")).strip()
    try:
        return FIELD_DIRECTIONS[key]
    except KeyError as exc:
        raise DemoError(
            f"field_direction must be one of {sorted(FIELD_DIRECTIONS)}, got {key!r}."
        ) from exc


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    stack = build_stack(cfg)
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(float(numerical["quantum_region_padding_nm"]))
    field_kV_cm = float(scientific["electric_field_kV_cm"])
    return {
        "temperature_K": scientific["temperature_K"],
        "number_of_states": int(numerical["number_of_states"]),
        "quantum_region_name": region_name(cfg),
        "quantum_start_nm": f"{start:.9g}",
        "quantum_end_nm": f"{end:.9g}",
        "grid_lines": stack.grid_lines(),
        "structure_regions": stack.structure_regions(
            contact_name="qw_contact",
            contact_thickness_nm=float(scientific["contact_thickness_nm"]),
        ),
        "field_direction_vector": direction_vector(cfg),
        "electric_field_kV_cm": f"{field_kV_cm:.9g}",
        "field_strength_V_per_m": f"{quantum1d.kv_per_cm_to_volts_per_metre(field_kV_cm):.9g}",
    }


def analyse_case(
    cfg: Mapping[str, Any], raw: Path, extracted: Path, plots_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    validation_cfg = cfg["validation"]
    analysis_cfg = cfg.get("analysis") or {}
    stack = build_stack(cfg)
    regions = quantum1d.region_map(stack.intervals())
    window = stack.quantum_region_nm(
        float(cfg["numerical"]["quantum_region_padding_nm"])
    )
    profile = outputs.load_profile(
        str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
    )
    run = quantum1d.parse_one_band_run(
        raw,
        profile=profile,
        region_name=region_name(cfg),
        bandedge_columns=cfg["outputs"]["bandedge_columns"],
        want_potential=True,
    )
    states = quantum1d.state_table(
        run,
        regions=regions,
        minimum_confined_probability=float(
            validation_cfg.get("minimum_confined_probability", 0.5)
        ),
        normalisation_tolerance=float(validation_cfg.get("normalization_tolerance", 1e-3)),
        boundary_edge_fraction=float(analysis_cfg.get("boundary_edge_fraction", 0.05)),
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
    normalised_densities = np.column_stack(
        [
            analysis.normalise_density(run.state_position_nm, run.densities[:, index])[0]
            for index in range(min(run.state_count, run.densities.shape[1]))
        ]
    )
    write_csv(
        extracted / "probability_densities.csv",
        {
            "position_nm": run.state_position_nm,
            **{
                f"probability_density_{index + 1}_nm^-1": normalised_densities[:, index]
                for index in range(normalised_densities.shape[1])
            },
        },
    )
    if run.potential_V is not None:
        write_csv(
            extracted / "potential.csv",
            {
                "position_nm": run.potential_V[0],
                "electrostatic_potential_V": run.potential_V[1],
            },
        )
    if run.electric_field_kV_cm is not None:
        write_csv(
            extracted / "electric_field.csv",
            {
                "position_nm": run.electric_field_kV_cm[0],
                "electric_field_kV_cm": run.electric_field_kV_cm[1],
            },
        )

    requested = float(cfg["scientific"]["electric_field_kV_cm"])
    sign = 1.0 if str(cfg["scientific"].get("field_direction", "+x")) == "+x" else -1.0
    measured = quantum1d.measured_field_kV_cm(run)
    from_potential = quantum1d.potential_slope_kV_cm(run)
    tolerance = float(analysis_cfg.get("field_unit_tolerance", 0.02))
    reference = max(abs(requested), 1.0)
    field_agrees = (
        measured is not None
        and abs(measured - sign * requested) <= tolerance * reference
    )
    potential_agrees = (
        from_potential is not None
        and abs(from_potential - sign * requested) <= tolerance * reference
    )

    # Fit only the homogeneous left outer barrier.  Fitting the whole stepped
    # heterostructure would mix the imposed field with material discontinuities.
    tilt = None
    if run.position_nm.size > 1:
        left_start, left_end = stack.interval("left_outer_barrier")
        barrier = (run.position_nm >= left_start) & (run.position_nm <= left_end)
        if int(np.count_nonzero(barrier)) >= 2:
            tilt = float(
                np.polyfit(run.position_nm[barrier], run.conduction_eV[barrier], 1)[0]
            )
    expected_tilt_sign = np.sign(sign * requested)
    tilt_matches = (
        True
        if abs(requested) < 1e-9
        else (tilt is not None and np.sign(tilt) == expected_tilt_sign)
    )

    energies = [state.energy_eV for state in states]
    spacings = analysis.energy_splittings_meV(energies)
    log_checks = outputs.scan_log_markers(
        outputs.solver_log_text(raw),
        completion_markers=validation_cfg.get("completion_markers", ()),
        fatal_markers=validation_cfg.get("fatal_markers", ()),
        warning_markers=validation_cfg.get("convergence_warning_markers", ()),
    )
    log_checks.update(outputs.completion_evidence(raw))

    observables: dict[str, Any] = {
        "electric_field_kV_cm": requested,
        "field_direction": str(cfg["scientific"].get("field_direction", "+x")),
        "quantum_region_padding_nm": float(cfg["numerical"]["quantum_region_padding_nm"]),
        "grid_points": int(run.position_nm.size),
        "state_count": len(states),
        "electron_energies_eV": energies,
        "E1_eV": energies[0],
        "E2_eV": energies[1] if len(energies) > 1 else None,
        "E3_eV": energies[2] if len(energies) > 2 else None,
        **spacings,
        "measured_field_kV_cm": measured,
        "field_from_potential_slope_kV_cm": from_potential,
        "conduction_band_tilt_eV_per_nm": tilt,
        "centroid_state1_nm": states[0].centroid_nm,
        "centroid_state2_nm": states[1].centroid_nm if len(states) > 1 else None,
        "centroid_state3_nm": states[2].centroid_nm if len(states) > 2 else None,
        "dipole_state1_nm": states[0].centroid_nm,
        "probability_wide_well_state1": states[0].region_probabilities.get("left_well"),
        "probability_narrow_well_state1": states[0].region_probabilities.get("right_well"),
        "probability_wide_well_state2": (
            states[1].region_probabilities.get("left_well") if len(states) > 1 else None
        ),
        "probability_narrow_well_state2": (
            states[1].region_probabilities.get("right_well") if len(states) > 1 else None
        ),
        "maximum_boundary_probability_bound_states": max(
            [state.boundary_probability for state in states if state.bound] or [0.0]
        ),
        "bound_state_count": sum(1 for state in states if state.bound),
        "all_states_bound": all(bool(state.bound) for state in states),
        "state_rows": rows,
    }
    if "position_matrix_nm" in matrices:
        position = matrices["position_matrix_nm"]
        if position.shape[0] >= 2:
            observables["z12_nm"] = float(position[0, 1])
        if position.shape[0] >= 3:
            observables["z23_nm"] = float(position[1, 2])
            observables["z13_nm"] = float(position[0, 2])

    validation: dict[str, Any] = {
        **{key: value for key, value in log_checks.items() if isinstance(value, bool)},
        "energies_finite_and_ordered": bool(
            np.all(np.isfinite(energies)) and np.all(np.diff(energies) > 0)
        ),
        "probability_normalized": all(state.normalised for state in states),
        "at_least_two_bound_states": sum(1 for state in states if state.bound) >= 2,
        "bound_state_boundary_probability_small": bool(
            observables["maximum_boundary_probability_bound_states"]
            <= float(validation_cfg.get("maximum_boundary_probability", 1e-3))
        ),
        "solver_field_matches_request": bool(field_agrees),
        "potential_slope_matches_request": bool(potential_agrees),
        "band_tilt_sign_matches_convention": bool(tilt_matches),
    }

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
    field = cfg["scientific"]["electric_field_kV_cm"]
    title = f"F = {field} kV/cm"
    energies = [state.energy_eV for state in states]
    plotting.band_diagram(
        plots_dir / "band_diagram.png",
        title=f"Tilted conduction band and eigenenergies ({title})",
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
    densities = np.column_stack(
        [
            analysis.normalise_density(run.state_position_nm, run.densities[:, index])[0]
            for index in range(min(run.state_count, run.densities.shape[1]))
        ]
    )
    plotting.density_plot(
        plots_dir / "probability_densities.png",
        title=f"Probability densities ({title})",
        position_nm=run.state_position_nm,
        densities=densities,
        regions=regions,
    )
    if run.potential_V is not None:
        plotting.line_plot(
            plots_dir / "potential.png",
            title=f"Electrostatic potential ({title})",
            xlabel="Position (nm)",
            ylabel="φ (V)",
            series={"potential": (run.potential_V[0], run.potential_V[1])},
            markers=False,
        )


def _envelopes_of(result: sweeps.CaseResult) -> np.ndarray | None:
    path = result.run_dir / "extracted" / "envelopes.csv"
    if not path.is_file():
        return None
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 2:
        return None
    return data


def track_across_field(
    results: Sequence[sweeps.CaseResult], minimum_confidence: float
) -> tuple[list[dict[str, Any]], list[list[float]]]:
    """Follow every state across the field sweep using envelope overlap.

    The geometry is fixed here, so envelopes from neighbouring field points live
    on the same grid and their overlap is meaningful -- unlike Demo 4, where the
    wells move.  The returned branch table holds the energies *after* relabelling,
    which is what the avoided-crossing search needs.
    """

    rows: list[dict[str, Any]] = []
    branches: list[list[float]] = []
    previous: np.ndarray | None = None
    permutation: list[int] | None = None
    for result in results:
        data = _envelopes_of(result)
        energies = result.observables.get("electron_energies_eV") or []
        if data is None or not energies:
            rows.append(
                {
                    "electric_field_kV_cm": result.spec.swept.get("electric_field_kV_cm"),
                    "case_id": result.spec.case_id,
                    "tracking_available": False,
                    "reason": "no envelopes parsed on this machine",
                }
            )
            continue
        grid, current = data[:, 0], data[:, 1:]
        if previous is None:
            permutation = list(range(current.shape[1]))
            rows.append(
                {
                    "electric_field_kV_cm": result.spec.swept.get("electric_field_kV_cm"),
                    "case_id": result.spec.case_id,
                    "tracking_available": True,
                    "method": "reference_point",
                    "solver_state_to_branch": list(permutation),
                    "overlap_matrix": np.eye(current.shape[1]).tolist(),
                    "minimum_confidence": None,
                    "is_confident": True,
                }
            )
        else:
            tracking = analysis.track_states(
                x=grid,
                previous_envelopes=previous,
                current_envelopes=current,
                minimum_confidence=minimum_confidence,
            )
            assert permutation is not None
            new_permutation = [0] * len(tracking.assignment)
            for current_index, previous_index in enumerate(tracking.assignment):
                if 0 <= previous_index < len(permutation):
                    new_permutation[current_index] = permutation[previous_index]
                else:
                    new_permutation[current_index] = current_index
            permutation = new_permutation
            rows.append(
                {
                    "electric_field_kV_cm": result.spec.swept.get("electric_field_kV_cm"),
                    "case_id": result.spec.case_id,
                    "tracking_available": True,
                    "method": tracking.method,
                    "assignment": ";".join(str(v + 1) for v in tracking.assignment),
                    "solver_state_to_branch": list(permutation),
                    "overlap_matrix": [
                        list(matrix_row) for matrix_row in tracking.similarity_matrix
                    ],
                    "confidence": ";".join(f"{v:.4f}" for v in tracking.confidence),
                    "minimum_confidence": min(tracking.confidence) if tracking.confidence else None,
                    "ambiguous_states": ";".join(str(i + 1) for i in tracking.ambiguous),
                    "is_confident": tracking.is_confident,
                }
            )
        previous = current
        branch_row = [float("nan")] * max(len(energies), len(permutation or []))
        for index, branch in enumerate(permutation or []):
            if index < len(energies) and branch < len(branch_row):
                branch_row[branch] = float(energies[index])
        branches.append(branch_row)
    return rows, branches


def tracked_state_rows(
    results: Sequence[sweeps.CaseResult],
    tracking_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return one tidy row per physical branch and field.

    Solver state numbers are retained as provenance, but every plotted state
    observable is labelled by the overlap-tracked branch.
    """

    table: list[dict[str, Any]] = []
    for result, tracking in zip(results, tracking_rows):
        mapping = tracking.get("solver_state_to_branch")
        state_rows = result.observables.get("state_rows") or []
        if not isinstance(mapping, Sequence) or isinstance(mapping, (str, bytes)):
            continue
        for solver_index, branch_index in enumerate(mapping):
            if solver_index >= len(state_rows):
                continue
            state = state_rows[solver_index]
            table.append(
                {
                    "electric_field_kV_cm": result.spec.swept.get(
                        "electric_field_kV_cm"
                    ),
                    "branch": int(branch_index) + 1,
                    "solver_state": solver_index + 1,
                    "energy_eV": state.get("energy_eV"),
                    "centroid_nm": state.get("centroid_nm"),
                    "wide_well_probability": state.get(
                        "probability_left_well"
                    ),
                    "narrow_well_probability": state.get(
                        "probability_right_well"
                    ),
                    "tracking_confident": tracking.get("is_confident"),
                }
            )
    return table


def _tracked_series(
    rows: Sequence[Mapping[str, Any]], branch: int, observable: str
) -> tuple[list[float], list[float]]:
    points = [
        (float(row["electric_field_kV_cm"]), float(row[observable]))
        for row in rows
        if row.get("branch") == branch
        and row.get("electric_field_kV_cm") is not None
        and row.get(observable) is not None
    ]
    points.sort()
    return [point[0] for point in points], [point[1] for point in points]


def _series(
    results: Sequence[sweeps.CaseResult], observable: str
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for result in results:
        field = result.spec.swept.get("electric_field_kV_cm")
        value = result.observables.get(observable)
        if field is None or value is None:
            continue
        xs.append(float(field))
        ys.append(float(value))
    return xs, ys


def _sweep_plots(
    parent: Path,
    field_results: Sequence[sweeps.CaseResult],
    padding_results: Sequence[sweeps.CaseResult],
    tracking_rows: Sequence[Mapping[str, Any]],
    tracked_rows: Sequence[Mapping[str, Any]],
) -> None:
    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    plotting.line_plot(
        plots_dir / "energies_vs_field.png",
        title="Overlap-tracked electron branches versus electric field",
        xlabel="Electric field (kV/cm)",
        ylabel="Energy (eV)",
        series={
            "branch 1": _tracked_series(tracked_rows, 1, "energy_eV"),
            "branch 2": _tracked_series(tracked_rows, 2, "energy_eV"),
            "branch 3": _tracked_series(tracked_rows, 3, "energy_eV"),
        },
    )
    plotting.line_plot(
        plots_dir / "centroid_vs_field.png",
        title="State centroid <z> versus electric field",
        xlabel="Electric field (kV/cm)",
        ylabel="<z> (nm)",
        series={
            "branch 1": _tracked_series(tracked_rows, 1, "centroid_nm"),
            "branch 2": _tracked_series(tracked_rows, 2, "centroid_nm"),
            "branch 3": _tracked_series(tracked_rows, 3, "centroid_nm"),
        },
    )
    plotting.line_plot(
        plots_dir / "well_probability_vs_field.png",
        title="Per-well probability versus electric field",
        xlabel="Electric field (kV/cm)",
        ylabel="Integrated probability",
        series={
            "branch 1, wide well": _tracked_series(
                tracked_rows, 1, "wide_well_probability"
            ),
            "branch 1, narrow well": _tracked_series(
                tracked_rows, 1, "narrow_well_probability"
            ),
            "branch 2, wide well": _tracked_series(
                tracked_rows, 2, "wide_well_probability"
            ),
            "branch 2, narrow well": _tracked_series(
                tracked_rows, 2, "narrow_well_probability"
            ),
        },
    )
    plotting.line_plot(
        plots_dir / "spacings_vs_field.png",
        title="Instantaneous eigenvalue spacings versus electric field",
        xlabel="Electric field (kV/cm)",
        ylabel="Spacing (meV)",
        series={
            "E2 − E1": _series(field_results, "E21_meV"),
            "E3 − E2": _series(field_results, "E32_meV"),
        },
    )
    plotting.line_plot(
        plots_dir / "field_unit_check.png",
        title="Requested versus solver-reported field (unit and sign check)",
        xlabel="Requested field (kV/cm)",
        ylabel="Reported field (kV/cm)",
        series={
            "electric_field.dat": (
                _series(field_results, "measured_field_kV_cm")[0],
                _series(field_results, "measured_field_kV_cm")[1],
            ),
            "−dφ/dx": (
                _series(field_results, "field_from_potential_slope_kV_cm")[0],
                _series(field_results, "field_from_potential_slope_kV_cm")[1],
            ),
        },
    )
    confidences = [
        (float(row["electric_field_kV_cm"]), float(row["minimum_confidence"]))
        for row in tracking_rows
        if row.get("minimum_confidence") is not None
        and row.get("electric_field_kV_cm") is not None
    ]
    plotting.line_plot(
        plots_dir / "state_tracking_confidence.png",
        title="Minimum envelope-overlap confidence versus field",
        xlabel="Electric field (kV/cm)",
        ylabel="min |<ψ_prev|ψ_now>|",
        series={"confidence": ([c[0] for c in confidences], [c[1] for c in confidences])},
        axhline=0.6,
    )
    padding_xs = [
        float(result.spec.swept["quantum_region_padding_nm"])
        for result in padding_results
        if result.observables.get("E1_eV") is not None
    ]
    plotting.line_plot(
        plots_dir / "padding_check.png",
        title="E1 and E2 versus quantum-region padding (numerical control)",
        xlabel="Quantum-region padding (nm)",
        ylabel="Energy (eV)",
        series={
            "E1": (
                padding_xs,
                [
                    float(result.observables["E1_eV"])
                    for result in padding_results
                    if result.observables.get("E1_eV") is not None
                ],
            ),
            "E2": (
                padding_xs,
                [
                    float(result.observables["E2_eV"])
                    for result in padding_results
                    if result.observables.get("E2_eV") is not None
                ],
            ),
        },
    )
    _band_diagram_panel(plots_dir, field_results)
    _crossing_plot(plots_dir, field_results)
    _overlap_matrix_plot(plots_dir, tracking_rows)


def _band_diagram_panel(plots_dir: Path, results: Sequence[sweeps.CaseResult]) -> None:
    """Overlay the actual conduction-band profiles at representative fields."""

    import matplotlib.pyplot as plt

    profiles: list[tuple[float, np.ndarray]] = []
    for result in results:
        field = result.spec.swept.get("electric_field_kV_cm")
        path = result.run_dir / "extracted" / "band_profile.csv"
        if field is None or not path.is_file():
            continue
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        if data.ndim == 2 and data.shape[1] >= 2:
            profiles.append((float(field), data))
    target = plots_dir / "band_diagrams_selected_fields.png"
    if not profiles:
        plotting.placeholder(target, "Tilted conduction band at selected fields")
        return
    desired = {-100.0, -25.0, 0.0, 25.0, 100.0}
    selected = [item for item in profiles if item[0] in desired] or profiles
    fig, ax = plt.subplots(figsize=(7.2, 4.7))
    for field, data in sorted(selected):
        ax.plot(data[:, 0], data[:, 1], label=f"{field:g} kV/cm")
    ax.set(
        title="Actual conduction-band profiles at selected electric fields",
        xlabel="Position (nm)",
        ylabel="Conduction-band edge (eV)",
    )
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.25)
    plotting.save_figure(fig, target)


def _crossing_plot(plots_dir: Path, results: Sequence[sweeps.CaseResult]) -> None:
    usable = [result for result in results if result.solver_success]
    target = plots_dir / "wavefunctions_near_crossing.png"
    if len(usable) < 3:
        plotting.placeholder(target, "Envelopes before, near, and after a crossing")
        return
    gaps = [
        (abs(float(result.observables.get("E21_meV") or 1e9)), result)
        for result in usable
        if result.observables.get("E21_meV") is not None
    ]
    if not gaps:
        plotting.placeholder(target, "Envelopes before, near, and after a crossing")
        return
    gaps.sort(key=lambda item: item[0])
    centre = gaps[0][1]
    order = sorted(usable, key=lambda r: float(r.spec.swept["electric_field_kV_cm"]))
    index = order.index(centre)
    picks = [order[max(0, index - 1)], centre, order[min(len(order) - 1, index + 1)]]
    series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    for result in picks:
        data = _envelopes_of(result)
        if data is None:
            continue
        field = result.spec.swept["electric_field_kV_cm"]
        for state in range(min(2, data.shape[1] - 1)):
            series[f"F={field}: ψ{state + 1}"] = (data[:, 0], data[:, 1 + state])
    plotting.line_plot(
        target,
        title="Envelopes before, at, and after the closest approach of E1 and E2",
        xlabel="Position (nm)",
        ylabel="Envelope amplitude ψ (nm$^{-1/2}$)",
        series=series,
        markers=False,
    )


def _overlap_matrix_plot(
    plots_dir: Path, tracking_rows: Sequence[Mapping[str, Any]]
) -> None:
    target = plots_dir / "overlap_matrix.png"
    usable = [row for row in tracking_rows if row.get("overlap_matrix")]
    if not usable:
        plotting.placeholder(target, "Adjacent-field state-overlap matrix")
        return
    non_reference = [
        row for row in usable if row.get("minimum_confidence") is not None
    ]
    chosen = min(
        non_reference or usable,
        key=lambda row: float(row.get("minimum_confidence") or 1.0),
    )
    matrix = np.asarray(chosen["overlap_matrix"], dtype=float)
    if matrix.size == 0:
        plotting.placeholder(target, "Adjacent-field state-overlap matrix")
        return
    plotting.matrix_heatmap(
        target,
        title=(
            "Adjacent-field |<ψ_previous|ψ_current>| at "
            f"F = {chosen.get('electric_field_kV_cm')} kV/cm"
        ),
        matrix=matrix,
        labels=[f"{index + 1}" for index in range(matrix.shape[0])],
        colorbar_label="envelope-overlap confidence",
    )


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    sweep_cfg = cfg.get("sweeps") or {}
    analysis_cfg = cfg.get("analysis") or {}
    minimum_confidence = float(
        analysis_cfg.get("minimum_state_tracking_confidence", 0.6)
    )

    field_cases = sweeps.single_variable_cases(
        cfg, "electric_field_kV_cm", sweep_cfg.get("electric_field_kV_cm", [])
    )
    padding_cases = sweeps.single_variable_cases(
        cfg,
        "quantum_region_padding_nm",
        sweep_cfg.get("quantum_region_padding_nm", []),
        prefix="padding_",
    )
    all_cases = [*field_cases, *padding_cases]
    if not all_cases:
        raise DemoError("demo.yaml declares no sweep values for Demo 5.")

    results: list[sweeps.CaseResult] = []
    for case in all_cases:
        results.append(
            sweeps.execute_case(
                demo_dir=context.demo_dir,
                spec=case,
                machine=context.machine,
                run_dir=context.parent / "runs" / case.case_id,
                render_values=render_values,
                analyse=analyse_case,
                dependency_report=context.dependency_report,
            )
        )
    field_results = results[: len(field_cases)]
    padding_results = results[len(field_cases) :]
    field_results_sorted = sorted(
        field_results, key=lambda r: float(r.spec.swept["electric_field_kV_cm"])
    )

    sweeps.write_sweep_summary(context.parent, results)
    failed, suspicious = sweeps.write_failed_and_suspicious(context.parent, results)
    tracking_rows, branches = track_across_field(field_results_sorted, minimum_confidence)
    sweeps.write_state_tracking(context.parent, tracking_rows)
    tracked_rows = tracked_state_rows(field_results_sorted, tracking_rows)
    sweeps.write_table(context.parent, "tracked_states", tracked_rows)
    write_json_atomically(
        context.parent / "extracted" / "state_overlap_matrices.json",
        {
            str(row.get("electric_field_kV_cm")): row["overlap_matrix"]
            for row in tracking_rows
            if row.get("overlap_matrix")
        },
    )

    crossings: list[dict[str, Any]] = []
    if branches:
        fields = [
            float(row["electric_field_kV_cm"])
            for row in tracking_rows
            if row.get("tracking_available") and row.get("electric_field_kV_cm") is not None
        ]
        array = np.asarray(branches, dtype=float)
        if array.ndim == 2 and array.shape[0] == len(fields) and np.isfinite(array).all():
            crossings = analysis.detect_avoided_crossings(
                fields,
                array,
                minimum_gap_meV=float(
                    analysis_cfg.get("avoided_crossing_minimum_gap_meV", 12.0)
                ),
                relative_curvature=float(
                    analysis_cfg.get("avoided_crossing_relative_curvature", 0.6)
                ),
            )
    sweeps.write_table(context.parent, "avoided_crossings", crossings)
    sweeps.write_table(
        context.parent,
        "field_convention",
        [
            {
                "electric_field_kV_cm": result.spec.swept.get("electric_field_kV_cm"),
                "measured_field_kV_cm": result.observables.get("measured_field_kV_cm"),
                "field_from_potential_slope_kV_cm": result.observables.get(
                    "field_from_potential_slope_kV_cm"
                ),
                "conduction_band_tilt_eV_per_nm": result.observables.get(
                    "conduction_band_tilt_eV_per_nm"
                ),
                "status": result.status,
            }
            for result in field_results_sorted
        ],
    )
    _sweep_plots(
        context.parent,
        field_results_sorted,
        padding_results,
        tracking_rows,
        tracked_rows,
    )
    plotting.ensure_plot_set(
        context.parent / "plots",
        PLOT_SET,
        reason=(
            "Per-case figure: produced inside each runs/<case>/plots directory once "
            "a licensed solver has run. No solver output on this machine."
        ),
    )

    padding_differences_meV: dict[str, float] = {}
    for state_key in ("E1_eV", "E2_eV"):
        values = [
            float(result.observables[state_key])
            for result in padding_results
            if result.observables.get(state_key) is not None
        ]
        if len(values) >= 2:
            padding_differences_meV[state_key] = 1000.0 * (max(values) - min(values))
    padding_stable: bool | None = None
    if len(padding_differences_meV) == 2:
        padding_stable = all(
            difference
            <= float(cfg["validation"].get("absolute_energy_tolerance_meV", 1.0))
            for difference in padding_differences_meV.values()
        )
    both_signs = {
        np.sign(float(result.spec.swept["electric_field_kV_cm"]))
        for result in field_results
        if result.solver_success
    }
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
            "avoided_crossing_count": len(crossings),
            "state_tracking_confident": (
                all(row.get("is_confident", False) for row in tracking_rows)
                if tracking_available
                else None
            ),
            "energies_stable_under_padding": padding_stable,
            "padding_energy_range_meV": padding_differences_meV,
            "field_sign_convention": (
                "positive electric_field_kV_cm with field_direction '+x' tilts the "
                "conduction band upward towards +x; measured on nextnano++ 3.0.0 "
                "Free at home and re-checked in every run"
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
                "every field point produced a generated input",
                all((result.run_dir / "generated_input").is_dir() for result in results),
                f"{len(results)} case directories written",
            ),
            (
                "no sweep point was discarded",
                len(results) == len(all_cases),
                f"{len(failed)} failed/skipped and {len(suspicious)} suspicious rows retained",
            ),
            (
                "solver-reported field matches the request",
                _all_true(results, "solver_field_matches_request"),
                "electric_field.dat compared against the requested kV/cm",
            ),
            (
                "potential slope matches the request",
                _all_true(results, "potential_slope_matches_request"),
                "−dφ/dx compared against the requested kV/cm",
            ),
            (
                "band tilt follows the documented sign convention",
                _all_true(results, "band_tilt_sign_matches_convention"),
                "checked from the band-edge profile, never inferred from a plot",
            ),
            (
                "both field polarities were exercised",
                (len(both_signs - {0.0}) == 2) if both_signs else None,
                "positive and negative fields both ran successfully",
            ),
            (
                "bound-state boundary probability negligible",
                _all_true(results, "bound_state_boundary_probability_small"),
                "a strong tilt pushes states towards one wall; this is the diagnostic",
            ),
            (
                "state tracking confident at every field step",
                all(row.get("is_confident", True) for row in tracking_rows)
                if any(row.get("tracking_available") for row in tracking_rows)
                else None,
                "envelope overlap between neighbouring field points",
            ),
            (
                "energies stable under larger quantum-region padding",
                padding_stable,
                "distinguishes field-induced localisation from a boundary artifact",
            ),
        ],
        notes=[
            "The imposed field is analytic: run{} contains only quantum{}. Adding "
            "poisson{} to run{} would replace the tilt with the contact-pinned "
            "electrostatic solution — that is Demo 6's job, not this one's.",
            "State identity is followed by envelope overlap, so the eigenvalue "
            "index may legitimately change meaning across an avoided crossing.",
            f"Avoided-crossing flags found: {len(crossings)}. A flag is an "
            "invitation to inspect the envelopes, not a proof.",
            "<z> here is the centroid of the probability density of a single "
            "state — an expectation value, not a transition dipole. The "
            "off-diagonal z_ij values are reported separately.",
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
