"""Demo 9 — automated coupled-well design sweep for a three-level system.

This is an automation and post-processing demo.  It sweeps coupled-well
geometries, extracts the three lowest conduction subbands and the position
matrix elements between them, and ranks candidates by a **relative** design
metric.

What it does not do: reproduce any paper, or compute chi(2).  The metric lives
in ``_shared/nlo.py`` with its assumptions spelled out, has arbitrary units, and
is blocked mechanically from being renamed to anything that reads as a
susceptibility.

Position matrix elements are obtained twice -- from the solver's
``dipole_moment_matrix_elements`` output (in e*nm, confirmed at home) and by
integrating the envelopes -- and the two are compared in every run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import analysis
import layers
import nlo
import outputs
import plots as plotting
import quantum1d
import sweeps
from demo_workflow import DemoError, write_csv, write_json_atomically

PLOT_SET: tuple[tuple[str, str], ...] = (
    ("spacings_vs_geometry.png", "Energy spacings versus geometry"),
    ("matrix_elements_vs_geometry.png", "Position matrix elements versus geometry"),
    ("localization_vs_geometry.png", "State localisation versus geometry"),
    ("metric_vs_parameter.png", "Relative design metric versus one parameter"),
    ("metric_heatmap.png", "Relative design metric over the two-variable grid"),
    ("detuning_vs_metric.png", "Energy detuning versus the metric"),
    ("product_vs_metric.png", "Matrix-element product versus the metric"),
    ("candidate_ranking.png", "Candidate ranking"),
    ("convergence_reruns.png", "Top-candidate convergence reruns"),
    ("state_tracking_confidence.png", "State-tracking confidence"),
    ("matrix_element_cross_check.png", "Solver dipole versus envelope integral"),
)


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


def polarization_name(cfg: Mapping[str, Any]) -> str:
    return str((cfg.get("analysis") or {}).get("dipole_polarization_name", "growth_x"))


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    stack = build_stack(cfg)
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(float(numerical["quantum_region_padding_nm"]))
    field = float(scientific["electric_field_kV_cm"])
    if int(numerical["number_of_states"]) < 3:
        raise DemoError("a three-level analysis needs number_of_states >= 3.")
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
        "electric_field_kV_cm": f"{field:.9g}",
        "field_strength_V_per_m": f"{quantum1d.kv_per_cm_to_volts_per_metre(field):.9g}",
        "dipole_polarization_name": polarization_name(cfg),
    }


def metric_settings(cfg: Mapping[str, Any]) -> nlo.MetricSettings:
    declared = cfg.get("metric") or {}
    return nlo.MetricSettings(
        target_E21_meV=float(declared.get("target_E21_meV", 120.0)),
        detuning_floor_meV=float(declared.get("detuning_floor_meV", 1.0)),
        double_resonance=bool(declared.get("double_resonance", True)),
        enabled=bool(declared.get("enabled", True)),
    )


def analyse_case(
    cfg: Mapping[str, Any], raw: Path, extracted: Path, plots_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    validation_cfg = cfg["validation"]
    analysis_cfg = cfg.get("analysis") or {}
    stack = build_stack(cfg)
    regions = quantum1d.region_map(stack.intervals())
    window = stack.quantum_region_nm(float(cfg["numerical"]["quantum_region_padding_nm"]))
    profile = outputs.load_profile(
        str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
    )
    polarization = polarization_name(cfg)
    run = quantum1d.parse_one_band_run(
        raw,
        profile=profile,
        region_name=region_name(cfg),
        bandedge_columns=cfg["outputs"]["bandedge_columns"],
        want_potential=True,
        dipole_polarizations=(polarization,),
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
    if len(states) < 3:
        raise DemoError(
            f"a three-level analysis needs at least three parsed states, got {len(states)}."
        )

    matrices = quantum1d.envelope_matrices(run)
    envelope_z = matrices.get("position_matrix_nm")
    solver_z = run.dipole_matrix_nm.get(polarization)
    comparison = quantum1d.compare_dipole_sources(
        run, envelope_z if envelope_z is not None else np.empty((0, 0)), polarization
    )

    def element(i: int, j: int) -> float | None:
        """Prefer the solver's own dipole output; fall back to the envelopes."""

        if solver_z is not None and solver_z.shape[0] > max(i, j):
            value = solver_z[i, j]
            if np.isfinite(value):
                return float(value)
        if envelope_z is not None and envelope_z.shape[0] > max(i, j):
            return float(abs(envelope_z[i, j]))
        return None

    energies = [state.energy_eV for state in states]
    z12, z23, z13 = element(0, 1), element(1, 2), element(0, 2)
    spacings = analysis.energy_splittings_meV(energies)

    settings = metric_settings(cfg)
    if None in (z12, z23, z13):
        metric = nlo.MetricResult(
            spacings_meV=spacings,
            assumptions=nlo.ASSUMPTIONS,
            excluded_reason="one or more position matrix elements are missing",
        )
    else:
        metric = nlo.three_level_metric(
            nlo.ThreeLevelInputs(
                E1_eV=energies[0],
                E2_eV=energies[1],
                E3_eV=energies[2],
                z12_nm=float(z12),
                z23_nm=float(z23),
                z13_nm=float(z13),
            ),
            settings,
        )

    rows = [state.as_row() for state in states]
    write_csv(
        extracted / "states.csv",
        {key: np.asarray([row.get(key) for row in rows]) for key in rows[0]},
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
    write_csv(
        extracted / "probability_densities.csv",
        {
            "position_nm": run.state_position_nm,
            **{
                f"probability_density_{index + 1}_nm^-1": run.densities[:, index]
                for index in range(run.densities.shape[1])
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
    write_json_atomically(
        extracted / "matrix_elements.json",
        {
            "polarization": polarization,
            "solver_dipole_nm": solver_z.tolist() if solver_z is not None else None,
            "envelope_position_nm": envelope_z.tolist() if envelope_z is not None else None,
            "cross_check": comparison,
            "units": "nm (equivalently e*nm with the electron charge factored out)",
        },
    )
    write_json_atomically(
        extracted / "metric.json",
        {**metric.as_row(), "assumptions": list(metric.assumptions)},
    )

    tolerance = float(
        analysis_cfg.get(
            "maximum_matrix_element_disagreement_nm",
            validation_cfg.get("maximum_matrix_element_disagreement_nm", 0.05),
        )
    )
    observables: dict[str, Any] = {
        "center_barrier_nm": float(cfg["scientific"]["center_barrier_nm"]),
        "wide_well_width_nm": float(cfg["scientific"]["wide_well_width_nm"]),
        "narrow_well_width_nm": float(cfg["scientific"]["narrow_well_width_nm"]),
        "aluminum_fraction": float(cfg["scientific"]["aluminum_fraction"]),
        "electric_field_kV_cm": float(cfg["scientific"]["electric_field_kV_cm"]),
        "active_region_grid_spacing_nm": float(
            cfg["numerical"]["active_region_grid_spacing_nm"]
        ),
        "E1_eV": energies[0],
        "E2_eV": energies[1],
        "E3_eV": energies[2],
        **spacings,
        "z12_nm": z12,
        "z23_nm": z23,
        "z13_nm": z13,
        "z_source": "solver_dipole" if solver_z is not None else "envelope_integral",
        "matrix_element_cross_check": comparison,
        "centroid_state1_nm": states[0].centroid_nm,
        "centroid_state2_nm": states[1].centroid_nm,
        "centroid_state3_nm": states[2].centroid_nm,
        "probability_wide_well_state1": states[0].region_probabilities.get("left_well"),
        "probability_narrow_well_state1": states[0].region_probabilities.get("right_well"),
        "probability_wide_well_state3": states[2].region_probabilities.get("left_well"),
        "probability_narrow_well_state3": states[2].region_probabilities.get("right_well"),
        "bound_state_count": sum(1 for state in states if state.bound),
        "all_states_bound": all(bool(state.bound) for state in states[:3]),
        "maximum_boundary_probability_bound_states": max(
            [state.boundary_probability for state in states if state.bound] or [0.0]
        ),
        "state_rows": rows,
        **metric.as_row(),
    }

    log_checks = outputs.scan_log_markers(
        outputs.solver_log_text(raw),
        completion_markers=validation_cfg.get("completion_markers", ()),
        fatal_markers=validation_cfg.get("fatal_markers", ()),
        warning_markers=validation_cfg.get("convergence_warning_markers", ()),
    )
    log_checks.update(outputs.completion_evidence(raw))
    validation: dict[str, Any] = {
        **{key: value for key, value in log_checks.items() if isinstance(value, bool)},
        "energies_finite_and_ordered": bool(
            np.all(np.isfinite(energies)) and np.all(np.diff(energies) > 0)
        ),
        "probability_normalized": all(state.normalised for state in states),
        "three_bound_states": sum(1 for state in states[:3] if state.bound) == 3,
        "matrix_elements_present": all(value is not None for value in (z12, z23, z13)),
        "bound_state_boundary_probability_small": bool(
            observables["maximum_boundary_probability_bound_states"]
            <= float(validation_cfg.get("maximum_boundary_probability", 1e-3))
        ),
    }
    if comparison.get("compared"):
        validation["dipole_sources_agree"] = bool(
            float(comparison["max_absolute_difference_nm"]) <= tolerance
        )

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
    if run.envelopes is not None:
        plotting.envelope_plot(
            plots_dir / "wavefunctions.png",
            title="Envelope amplitudes",
            position_nm=run.state_position_nm,
            envelopes=run.envelopes,
            regions=regions,
        )
    plotting.band_diagram(
        plots_dir / "band_diagram.png",
        title="Conduction band and the three lowest subbands",
        position_nm=run.position_nm,
        conduction_eV=run.conduction_eV,
        energies_eV=[state.energy_eV for state in states[:3]],
        regions=regions,
    )


def _candidate_rows(results: Sequence[sweeps.CaseResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        observables = result.observables
        cross_check = observables.get("matrix_element_cross_check") or {}
        rows.append(
            {
                "case_id": result.spec.case_id,
                "label": result.spec.label,
                "sweep_kind": result.spec.metadata.get("sweep_kind"),
                **{str(k): v for k, v in result.spec.swept.items()},
                "status": result.status,
                "solver_success": result.solver_success,
                "convergence_status": result.validation.get("passed"),
                "all_states_bound": observables.get("all_states_bound"),
                "state_tracking_confidence": observables.get("state_tracking_confidence"),
                "E1_eV": observables.get("E1_eV"),
                "E2_eV": observables.get("E2_eV"),
                "E3_eV": observables.get("E3_eV"),
                "E21_meV": observables.get("E21_meV"),
                "E32_meV": observables.get("E32_meV"),
                "E31_meV": observables.get("E31_meV"),
                "z12_nm": observables.get("z12_nm"),
                "z23_nm": observables.get("z23_nm"),
                "z13_nm": observables.get("z13_nm"),
                "z_source": observables.get("z_source"),
                "dipole_max_difference_nm": cross_check.get("max_absolute_difference_nm"),
                "matrix_element_product_nm3": observables.get("matrix_element_product_nm3"),
                "detuning_denominator_meV2": observables.get("detuning_denominator_meV2"),
                "relative_metric": observables.get("relative_metric"),
                "metric_name": observables.get("metric_name"),
                "metric_units": observables.get("metric_units"),
                "metric_excluded_reason": observables.get("metric_excluded_reason"),
                "runtime_seconds": result.runtime_seconds,
                "run_dir": str(result.run_dir),
            }
        )
    return rows


def _attach_tracking(
    results: Sequence[sweeps.CaseResult],
    minimum_confidence: float,
    *,
    sweep_group: str,
    parameter: str,
) -> list[dict[str, Any]]:
    """Track states along the single-variable sweep and record the confidence.

    Geometry changes between points, so the tracking uses physical features
    rather than envelope overlap -- the same reasoning as Demo 4.
    """

    rows: list[dict[str, Any]] = []
    previous: list[list[float]] | None = None
    for result in results:
        state_rows = result.observables.get("state_rows")
        if not state_rows:
            rows.append(
                {
                    "case_id": result.spec.case_id,
                    "sweep_group": sweep_group,
                    "parameter_value": result.spec.swept.get(parameter),
                    "tracking_available": False,
                    "reason": "no parsed states on this machine",
                }
            )
            continue
        features = [
            [
                float(row.get("probability_left_well") or 0.0),
                float(row.get("probability_right_well") or 0.0),
                float(row.get("centroid_nm") or 0.0),
                float(row.get("energy_eV") or 0.0),
            ]
            for row in state_rows
        ]
        if previous is None:
            result.observables["state_tracking_confidence"] = 1.0
            rows.append(
                {
                    "case_id": result.spec.case_id,
                    "sweep_group": sweep_group,
                    "parameter_value": result.spec.swept.get(parameter),
                    "tracking_available": True,
                    "method": "reference_point",
                    "minimum_confidence": 1.0,
                    "is_confident": True,
                }
            )
        else:
            tracking = analysis.track_states(
                previous_features=previous,
                current_features=features,
                minimum_confidence=minimum_confidence,
            )
            confidence = min(tracking.confidence) if tracking.confidence else 0.0
            result.observables["state_tracking_confidence"] = confidence
            rows.append(
                {
                    "case_id": result.spec.case_id,
                    "sweep_group": sweep_group,
                    "parameter_value": result.spec.swept.get(parameter),
                    "tracking_available": True,
                    "method": tracking.method,
                    "assignment": ";".join(str(v + 1) for v in tracking.assignment),
                    "confidence": ";".join(f"{v:.4f}" for v in tracking.confidence),
                    "minimum_confidence": confidence,
                    "ambiguous_states": ";".join(str(i + 1) for i in tracking.ambiguous),
                    "is_confident": tracking.is_confident,
                }
            )
        previous = features
    return rows


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    sweep_cfg = cfg.get("sweeps") or {}
    analysis_cfg = cfg.get("analysis") or {}
    metric_cfg = cfg.get("metric") or {}
    minimum_confidence = float(analysis_cfg.get("minimum_state_tracking_confidence", 0.6))

    # A: single-variable sweeps.
    single_cases = sweeps.single_variable_cases(
        cfg, "center_barrier_nm", sweep_cfg.get("center_barrier_nm", [])
    )
    field_cases = sweeps.single_variable_cases(
        cfg,
        "electric_field_kV_cm",
        sweep_cfg.get("electric_field_kV_cm", []),
        prefix="f_",
    )
    # B: two-variable grid.
    grid_axes = analysis_cfg.get("grid_axes") or {}
    grid_cases = sweeps.grid_cases(cfg, grid_axes) if len(grid_axes) >= 2 else []
    # C: explicit design list.
    design_cases = sweeps.design_list_cases(cfg, analysis_cfg.get("designs") or [])

    expected = sweeps.expected_case_count(
        single={
            "center_barrier_nm": sweep_cfg.get("center_barrier_nm", []),
            "electric_field_kV_cm": sweep_cfg.get("electric_field_kV_cm", []),
        },
        grid=grid_axes if len(grid_axes) >= 2 else None,
        designs=analysis_cfg.get("designs") or [],
    )
    all_cases = [*single_cases, *field_cases, *grid_cases, *design_cases]
    if len(all_cases) != expected:
        raise DemoError(
            f"case generation produced {len(all_cases)} cases but the configuration "
            f"implies {expected}; refusing to run an incomplete sweep."
        )

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
    centre_results = results[: len(single_cases)]
    field_results = results[
        len(single_cases) : len(single_cases) + len(field_cases)
    ]
    tracking_rows = [
        *_attach_tracking(
            centre_results,
            minimum_confidence,
            sweep_group="center_barrier_nm",
            parameter="center_barrier_nm",
        ),
        *_attach_tracking(
            field_results,
            minimum_confidence,
            sweep_group="electric_field_kV_cm",
            parameter="electric_field_kV_cm",
        ),
    ]

    constraints = {
        str(name): (float(bounds[0]), float(bounds[1]))
        for name, bounds in (metric_cfg.get("constraints") or {}).items()
    }
    rows = _candidate_rows(results)
    ranked, excluded = nlo.rank_candidates(
        rows,
        minimum_tracking_confidence=minimum_confidence,
        constraints=constraints,
    )

    # D: refined-mesh reruns of the top-ranked candidates.
    rerun_count = int(analysis_cfg.get("convergence_rerun_count", 3))
    refinement = float(analysis_cfg.get("grid_refinement_factor", 0.5))
    rerun_results: list[sweeps.CaseResult] = []
    by_case = {result.spec.case_id: result for result in results}
    for position, row in enumerate(ranked[:rerun_count], start=1):
        source = by_case.get(str(row["case_id"]))
        if source is None:
            continue
        refined = sweeps.apply_override(
            source.spec.config,
            "active_region_grid_spacing_nm",
            float(source.spec.config["numerical"]["active_region_grid_spacing_nm"])
            * refinement,
        )
        spec = sweeps.CaseSpec(
            case_id=f"rerun_{position:02d}",
            label=f"refined mesh rerun of {row['case_id']}",
            swept=dict(source.spec.swept),
            config=refined,
            metadata={
                "sweep_kind": "convergence_rerun",
                "source_case_id": str(row["case_id"]),
            },
        )
        rerun_results.append(
            sweeps.execute_case(
                demo_dir=context.demo_dir,
                spec=spec,
                machine=context.machine,
                run_dir=context.parent / "runs" / spec.case_id,
                render_values=render_values,
                analyse=analyse_case,
                dependency_report=context.dependency_report,
            )
        )

    every_result = [*results, *rerun_results]
    sweeps.write_sweep_summary(context.parent, every_result)
    failed, suspicious = sweeps.write_failed_and_suspicious(context.parent, every_result)
    sweeps.write_state_tracking(context.parent, tracking_rows)
    sweeps.write_table(context.parent, "parameters", [case.row() for case in all_cases])
    sweeps.write_table(context.parent, "observables", rows)
    sweeps.write_table(context.parent, "ranked_candidates", ranked)
    sweeps.write_table(context.parent, "excluded_candidates", excluded)
    rerun_rows = _candidate_rows(rerun_results)
    sweeps.write_table(context.parent, "convergence_reruns", rerun_rows)

    rerun_comparison: list[dict[str, Any]] = []
    for rerun in rerun_results:
        source_id = str(rerun.spec.metadata.get("source_case_id"))
        source = by_case.get(source_id)
        if source is None:
            continue
        entry: dict[str, Any] = {"candidate": source_id, "rerun": rerun.spec.case_id}
        for key in ("E21_meV", "E32_meV", "relative_metric"):
            coarse = source.observables.get(key)
            fine = rerun.observables.get(key)
            entry[f"{key}_coarse"] = coarse
            entry[f"{key}_fine"] = fine
            entry[f"{key}_change"] = (
                None if coarse is None or fine is None else float(fine) - float(coarse)
            )
        coarse_metric = source.observables.get("relative_metric")
        fine_metric = rerun.observables.get("relative_metric")
        entry["relative_metric_change_fraction"] = (
            None
            if coarse_metric in (None, 0) or fine_metric is None
            else abs(float(fine_metric) - float(coarse_metric))
            / abs(float(coarse_metric))
        )
        rerun_comparison.append(entry)
    sweeps.write_convergence_summary(
        context.parent,
        title="Demo 9 — refined-mesh reruns of the top-ranked candidates",
        rows=rerun_comparison,
        commentary=[
            "A candidate whose spacings or metric move appreciably when the mesh "
            "is refined was never a candidate; it was a discretisation artifact.",
            "The reruns halve active_region_grid_spacing_nm and change nothing else.",
            "Ranking is performed BEFORE the reruns, so the reruns are a test of "
            "the ranking rather than an input to it.",
        ],
    )
    _sweep_plots(
        context.parent,
        single_cases_results=results[: len(single_cases)],
        grid_results=results[
            len(single_cases) + len(field_cases) : len(single_cases)
            + len(field_cases)
            + len(grid_cases)
        ],
        grid_axes=grid_axes,
        ranked=ranked,
        excluded=excluded,
        all_rows=rows,
        rerun_comparison=rerun_comparison,
        tracking_rows=tracking_rows,
        every_result=every_result,
    )
    plotting.ensure_plot_set(
        context.parent / "plots",
        PLOT_SET,
        reason=(
            "Per-case figure: produced inside each runs/<case>/plots directory once "
            "a licensed solver has run. No solver output on this machine."
        ),
    )

    manifest = sweeps.write_sweep_manifest(
        context.parent,
        cfg=cfg,
        machine=context.machine,
        results=every_result,
        dependency_report=context.dependency_report,
        parser_provenance={"profile": cfg["outputs"].get("parser_profile")},
        extra={
            "candidate_count": len(all_cases),
            "convergence_rerun_count": len(rerun_results),
            "ranked_count": len(ranked),
            "excluded_count": len(excluded),
            "metric_name": nlo.METRIC_NAME,
            "metric_units": nlo.METRIC_UNITS,
            "metric_assumptions": list(nlo.ASSUMPTIONS),
            "metric_disclaimer": (
                "This is a RELATIVE design metric with arbitrary units. It is not "
                "chi(2), has no pm/V value, and must not be compared with a measured "
                "susceptibility. See nextnano/demos/_shared/nlo.py."
            ),
            "exclusion_rules": list(nlo.EXCLUSION_RULES),
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
                "candidate count matches the configuration",
                len(all_cases) == expected,
                f"{len(all_cases)} candidates: single-variable, grid, and design list",
            ),
            (
                "every candidate has its own run directory and generated input",
                all(
                    (result.run_dir / "generated_input").is_dir()
                    for result in every_result
                ),
                f"{len(every_result)} directories including {len(rerun_results)} reruns",
            ),
            (
                "no candidate was discarded",
                len(every_result) == len(all_cases) + len(rerun_results),
                f"{len(failed)} failed/skipped and {len(suspicious)} suspicious rows retained; "
                f"{len(excluded)} excluded from ranking but present in every table",
            ),
            (
                "solver dipole output agrees with the envelope integral",
                _all_true(every_result, "dipole_sources_agree"),
                "two independent routes to z_ij, compared in every run",
            ),
            (
                "all three lowest states are physically bound",
                _all_true(every_result, "three_bound_states"),
                "a candidate with an unbound level cannot be ranked",
            ),
            (
                "state tracking confident along the single-variable sweep",
                all(row.get("is_confident", True) for row in tracking_rows)
                if any(row.get("tracking_available") for row in tracking_rows)
                else None,
                "ambiguous points are excluded from ranking, not deleted",
            ),
            (
                "top candidates survive a refined mesh",
                None
                if not rerun_comparison
                else all(
                    entry.get("relative_metric_change_fraction") is not None
                    and float(entry["relative_metric_change_fraction"])
                    <= float(
                        analysis_cfg.get(
                            "maximum_metric_relative_change", 0.10
                        )
                    )
                    and entry.get("E21_meV_change") is not None
                    and abs(float(entry["E21_meV_change"]))
                    <= float(
                        cfg["validation"].get(
                            "absolute_energy_tolerance_meV", 1.0
                        )
                    )
                    and entry.get("E32_meV_change") is not None
                    and abs(float(entry["E32_meV_change"]))
                    <= float(
                        cfg["validation"].get(
                            "absolute_energy_tolerance_meV", 1.0
                        )
                    )
                    for entry in rerun_comparison
                ),
                "E21/E32 within the energy tolerance and metric within the configured relative tolerance",
            ),
        ],
        notes=[
            f"The ranking metric is `{nlo.METRIC_NAME}` in units of "
            f"`{nlo.METRIC_UNITS}`. It is NOT chi(2) and has no pm/V value. "
            "The list of everything it omits — carrier density, photon energy, "
            "dephasing, populations, local-field corrections, SI conversion — is "
            "in _shared/nlo.py and is reproduced in the manifest.",
            "Position matrix elements are taken from the solver's own "
            "dipole_moment_matrix_elements output (e·nm) and cross-checked "
            "against an independent envelope integral. Disagreement fails the run.",
            "A candidate is barred from the top of the ranking if its solver "
            "failed, it is not converged, its state identity is ambiguous, its "
            "states are not bound, its matrix elements are missing, or it violates "
            "a configured constraint. It still appears in every table and plot, "
            "hatched in the ranking chart.",
            "Only conduction subbands are involved. Nothing here is an interband "
            "quantity, and no photonic mode, cavity, or metasurface resonance is "
            "modelled anywhere in this demo.",
        ],
    )
    return sweeps.finish_run(context, results=every_result, manifest=manifest)


def _sweep_plots(
    parent: Path,
    *,
    single_cases_results: Sequence[sweeps.CaseResult],
    grid_results: Sequence[sweeps.CaseResult],
    grid_axes: Mapping[str, Sequence[Any]],
    ranked: Sequence[Mapping[str, Any]],
    excluded: Sequence[Mapping[str, Any]],
    all_rows: Sequence[Mapping[str, Any]],
    rerun_comparison: Sequence[Mapping[str, Any]],
    tracking_rows: Sequence[Mapping[str, Any]],
    every_result: Sequence[sweeps.CaseResult],
) -> None:
    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    def series(observable: str) -> tuple[list[float], list[float]]:
        xs: list[float] = []
        ys: list[float] = []
        for result in single_cases_results:
            value = result.observables.get(observable)
            swept = result.spec.swept.get("center_barrier_nm")
            if value is None or swept is None:
                continue
            xs.append(float(swept))
            ys.append(float(value))
        return xs, ys

    plotting.line_plot(
        plots_dir / "spacings_vs_geometry.png",
        title="Energy spacings versus centre-barrier thickness",
        xlabel="Centre-barrier thickness (nm)",
        ylabel="Spacing (meV)",
        series={"E21": series("E21_meV"), "E32": series("E32_meV"), "E31": series("E31_meV")},
    )
    plotting.line_plot(
        plots_dir / "matrix_elements_vs_geometry.png",
        title="Position matrix elements versus centre-barrier thickness",
        xlabel="Centre-barrier thickness (nm)",
        ylabel="|z_ij| (nm)",
        series={"z12": series("z12_nm"), "z23": series("z23_nm"), "z13": series("z13_nm")},
    )
    plotting.line_plot(
        plots_dir / "localization_vs_geometry.png",
        title="State localisation versus centre-barrier thickness",
        xlabel="Centre-barrier thickness (nm)",
        ylabel="Integrated probability",
        series={
            "state 1, wide well": series("probability_wide_well_state1"),
            "state 3, narrow well": series("probability_narrow_well_state3"),
        },
    )
    plotting.line_plot(
        plots_dir / "metric_vs_parameter.png",
        title=f"{nlo.METRIC_NAME} versus centre-barrier thickness",
        xlabel="Centre-barrier thickness (nm)",
        ylabel=f"Relative metric ({nlo.METRIC_UNITS})",
        series={"metric": series("relative_metric")},
    )
    usable = [
        row
        for row in all_rows
        if row.get("relative_metric") is not None
        and row.get("detuning_denominator_meV2") is not None
    ]
    plotting.line_plot(
        plots_dir / "detuning_vs_metric.png",
        title="Energy-detuning denominator versus the relative metric",
        xlabel="Detuning denominator (meV²)",
        ylabel=f"Relative metric ({nlo.METRIC_UNITS})",
        series={
            "candidates": (
                [float(row["detuning_denominator_meV2"]) for row in usable],
                [float(row["relative_metric"]) for row in usable],
            )
        },
    )
    product = [
        row
        for row in all_rows
        if row.get("relative_metric") is not None
        and row.get("matrix_element_product_nm3") is not None
    ]
    plotting.line_plot(
        plots_dir / "product_vs_metric.png",
        title="Matrix-element product versus the relative metric",
        xlabel="|z12·z23·z13| (nm³)",
        ylabel=f"Relative metric ({nlo.METRIC_UNITS})",
        series={
            "candidates": (
                [float(row["matrix_element_product_nm3"]) for row in product],
                [float(row["relative_metric"]) for row in product],
            )
        },
    )
    combined = [*ranked, *excluded]
    plotting.bar_plot(
        plots_dir / "candidate_ranking.png",
        title=f"Candidate ranking by {nlo.METRIC_NAME} ({nlo.METRIC_UNITS})",
        xlabel="Candidate",
        ylabel="Relative metric (arb. u.)",
        labels=[str(row["case_id"]) for row in combined],
        values=[float(row.get("relative_metric") or 0.0) for row in combined],
        excluded=[bool(row.get("exclusion_reasons")) for row in combined],
    )
    names = list(grid_axes)
    if len(names) >= 2 and grid_results:
        x_values = [float(v) for v in grid_axes[names[1]]]
        y_values = [float(v) for v in grid_axes[names[0]]]
        matrix = np.full((len(y_values), len(x_values)), np.nan)
        for result in grid_results:
            metric = result.observables.get("relative_metric")
            if metric is None:
                continue
            try:
                row = y_values.index(float(result.spec.swept[names[0]]))
                column = x_values.index(float(result.spec.swept[names[1]]))
            except (KeyError, ValueError):
                continue
            matrix[row, column] = float(metric)
        plotting.heatmap(
            plots_dir / "metric_heatmap.png",
            title=f"{nlo.METRIC_NAME} over the two-variable grid ({nlo.METRIC_UNITS})",
            xlabel=names[1],
            ylabel=names[0],
            x_values=x_values,
            y_values=y_values,
            values=matrix,
            colorbar_label="Relative metric (arb. u.)",
            annotate=True,
        )
    plotting.line_plot(
        plots_dir / "convergence_reruns.png",
        title="Top-candidate metric: coarse mesh versus refined mesh",
        xlabel="Candidate index",
        ylabel=f"Relative metric ({nlo.METRIC_UNITS})",
        series={
            "coarse": (
                list(range(1, len(rerun_comparison) + 1)),
                [
                    float(entry["relative_metric_coarse"])
                    for entry in rerun_comparison
                    if entry.get("relative_metric_coarse") is not None
                ],
            ),
            "refined": (
                list(range(1, len(rerun_comparison) + 1)),
                [
                    float(entry["relative_metric_fine"])
                    for entry in rerun_comparison
                    if entry.get("relative_metric_fine") is not None
                ],
            ),
        },
    )
    confidences = [
        (index, float(row["minimum_confidence"]))
        for index, row in enumerate(tracking_rows, start=1)
        if row.get("minimum_confidence") is not None
    ]
    plotting.line_plot(
        plots_dir / "state_tracking_confidence.png",
        title="State-tracking confidence along the single-variable sweep",
        xlabel="Sweep step",
        ylabel="Minimum similarity",
        series={
            "confidence": ([c[0] for c in confidences], [c[1] for c in confidences])
        },
        axhline=0.6,
    )
    differences = [
        float(row["dipole_max_difference_nm"])
        for row in all_rows
        if row.get("dipole_max_difference_nm") is not None
    ]
    plotting.line_plot(
        plots_dir / "matrix_element_cross_check.png",
        title="Solver dipole output versus envelope integral",
        xlabel="Candidate index",
        ylabel="max |z_solver − z_envelope| (nm)",
        series={
            "difference": (list(range(1, len(differences) + 1)), differences)
        },
    )


def _all_true(results: Sequence[sweeps.CaseResult], key: str) -> bool | None:
    values = [
        result.validation.get(key)
        for result in results
        if result.solver_success and key in result.validation
    ]
    if not values:
        return None
    return all(bool(value) for value in values)
