"""Every Demo 13 result table, and the units metadata that goes with them.

Section 14 asks for many complementary tables with descriptive filenames, units
on every column, CSV for all of them and Markdown/JSON for the summaries, and --
critically -- that resuming a run never overwrites earlier results.  The last
one is handled upstream by the append-only ledger in :mod:`axsearch13`: every
table here is a *projection* of that ledger, rebuilt from it each time, so a
table can be regenerated freely without any history being at risk.

A note on filtering: no table silently drops a trial.  The invalid and failed
trials have their own table *and* remain in the complete history with their
rejection reason, because "which designs did the optimizer reject, and why" is a
result, not noise.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO12_DIR = DEMO_DIR.parent / "12_graded_interface_coupled_quantum_well_optimization"
for _path in (str(SHARED), str(DEMO12_DIR), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import grading12  # noqa: E402
from demo_workflow import write_json_atomically, write_text_atomically  # noqa: E402

import design13  # noqa: E402
import feasibility13  # noqa: E402
import grading13  # noqa: E402

#: Unit of every column name Demo 13 writes. ``a.u.`` marks the relative chi(2)
#: scale of Demo 11's Eq. 2: a lineshape and a trend, with no absolute
#: calibration, and therefore never labelled pm/V anywhere in this demo.
COLUMN_UNITS: Mapping[str, str] = {
    "trial_index": "count",
    "iteration": "count",
    "candidate_id": "identifier",
    "generation_method": "name",
    "generator": "name",
    "status": "category",
    "trial_outcome_class": "category",
    "failure_reason": "text",
    "rejection_reason": "text",
    "runtime_seconds": "s",
    "input_file_path": "path",
    "output_directory_path": "path",
    "parameter_asymmetry_s": "dimensionless",
    "parameter_central_barrier_thickness_nm": "nm",
    # The REALIZED width, written by design13.canonicalize. Correctly nm.
    "parameter_grading_thickness_nm": "nm",
    "parameter_grading_profile": "category",
    # The semantic grading columns from grading13. The distinction that matters
    # is the first one: a fraction of the feasible maximum is dimensionless, and
    # labelling it nm is how a number in [0, 1] came to be read as a length.
    # `grading_fraction_of_feasible_max` already has a richer entry further down
    # this map; it is deliberately not repeated here.
    "proposed_grading_fraction": "fraction of the feasible maximum in [0,1]",
    "maximum_feasible_grading_nm": "nm",
    "proposed_grading_thickness_nm_unsnapped": "nm",
    "realized_grading_thickness_nm": "nm",
    "proposed_interface_mode": "category",
    "realized_interface_mode": "category",
    "proposed_grading_profile": "category",
    "realized_grading_profile": "category",
    "collapsed_to_abrupt": "boolean",
    "is_genuinely_graded": "boolean",
    "grading_unavailable_reason": "text",
    "objective_scale_note": "text",
    "perturbation_fraction_of_nominal": "dimensionless",
    "relative_drift_per_fractional_change": "dimensionless",
    "target_wavelength_nm": "nm",
    "relative_chi2_at_target_wavelength_abs": "a.u. (relative |chi2|)",
    "relative_peak_chi2_abs": "a.u. (relative |chi2|)",
    "peak_wavelength_nm": "nm",
    "signed_detuning_nm": "nm",
    "absolute_detuning_nm": "nm",
    "relative_integrated_chi2_abs": "a.u.*nm",
    "bandwidth_above_fraction_nm": "nm",
    "bandwidth_fraction_of_peak": "dimensionless",
    "integrated_wavelength_window_nm": "nm",
    "E_e1_eV": "eV",
    "E_e2_eV": "eV",
    "E_hh1_eV": "eV",
    "E_hh2_eV": "eV",
    "electron_energies_eV": "eV",
    "heavy_hole_energies_eV": "eV",
    "transition_e1_hh1_eV": "eV",
    "transition_e2_hh2_eV": "eV",
    "anticrossing_gap_meV": "meV",
    "heavy_hole_anticrossing_gap_meV": "meV",
    "electron_level_gaps_meV": "meV",
    "heavy_hole_level_gaps_meV": "meV",
    "overlap_e1_hh1": "dimensionless",
    "overlap_e2_hh2": "dimensionless",
    "z_e1_e1_nm": "nm",
    "z_e1_e2_nm": "nm",
    "z_e2_e2_nm": "nm",
    "z_hh1_hh1_nm": "nm",
    "z_hh1_hh2_nm": "nm",
    "z_hh2_hh2_nm": "nm",
    "electron_hole_centroid_separation_nm": "nm",
    "intersubband_dipole_e1_e2_e_nm": "e*nm",
    "intersubband_oscillator_strength_e1_e2": "dimensionless",
    "wide_well_probability": "probability",
    "narrow_well_probability": "probability",
    "electron2_wide_well_probability": "probability",
    "electron2_narrow_well_probability": "probability",
    "central_barrier_probability": "probability",
    "outer_barrier_probability": "probability",
    "left_boundary_probability": "probability",
    "right_boundary_probability": "probability",
    "total_boundary_probability": "probability",
    "maximum_boundary_probability": "probability",
    "raw_solver_state_index": "index",
    "tracked_state_labels": "index",
    "raw_state_indices": "index",
    "state_tracking_confidence": "overlap in [0,1]",
    "state_tracking_margin": "overlap difference",
    "state_tracking_ambiguous": "boolean",
    "state_tracking_reference_trial": "trial index",
    "state_tracking_method": "name",
    "solver_completed": "boolean",
    "expected_outputs_available": "boolean",
    "normalization_valid": "boolean",
    "orthonormality_error": "dimensionless",
    "orthonormality_tolerance": "dimensionless",
    "origin_independence_absolute_residual": "a.u.",
    "origin_independence_relative_residual": "dimensionless",
    "origin_independence_error": "dimensionless or a.u.",
    "origin_independence_comparison_mode": "category",
    "origin_independence_valid": "0 or 1",
    "required_states_valid": "0 or 1",
    "physical_qc_valid": "0 or 1",
    "physical_qc_failed_tests": "names",
    "bound_state_count": "count",
    "states_failing_bound_criterion": "count",
    "states_failing_bound_criterion_in_chi2_sum": "count",
    "quasi_bound_policy": "category",
    "requested_electron_states": "count",
    "extracted_electron_states": "count",
    "extracted_state_rows": "count",
    "chi2_max_states_per_band": "count",
    "chi2_electron_states_used": "count",
    "chi2_heavy_hole_states_used": "count",
    "chi2_triple_sum_terms_evaluated": "count",
    "chi2_triple_sum_terms_significant": "count",
    "solver_states_not_reaching_the_sum": "count",
    "trial_valid": "boolean",
    "valid_low_response": "boolean",
    "constraint_violations": "names",
    "objective_value": "a.u. (objective units)",
    "objective_metric": "name",
    "best_objective_so_far": "a.u. (objective units)",
    "expected_acquisition_value": "acquisition units (model dependent)",
    "robustness_score": "dimensionless in [0,1]",
    "weighted_score": "dimensionless",
    "evaluations": "count",
    "evaluations_to_threshold": "count",
    "snap_distance": "normalized design distance",
    "design_distance": "normalized design distance",
    "importance": "first-order Sobol index",
    "predicted_mean": "metric units",
    "predicted_standard_error": "metric units",
    "detuning_side": "category",
    "qc_warnings": "names",
    "bound_state_policy": "category",
    "ax_constraint_violations": "names",
    "feasible_under_ax_constraints": "boolean",
    "design_hash": "hex digest of the realized structure",
    "canonical_hash": "hex digest of the realized structure",
    "proposed_grading_fraction": "fraction of the feasible maximum in [0,1]",
    "grading_fraction_of_feasible_max": "fraction of the feasible maximum in [0,1]",
    "maximum_feasible_grading_thickness_nm": "nm",
    "realized_grading_thickness_nm": "nm",
    "minimum_flat_region_nm": "nm",
    "layer_thickness_nm": "nm",
    "consumed_nm": "nm",
    "remaining_flat_nm": "nm",
    "graded_interface_count": "count",
    "binding_layer": "name",
    "geometry_feasible": "boolean",
    "solver_launched": "boolean",
    "proposal_attempt": "count",
    "requested_bo_iteration": "count",
    "replacement_trial_index": "trial index",
    "sobol_proposals": "count",
    "model_based_proposals": "count",
    "preflight_invalid_proposals": "count",
    "duplicate_proposals": "count",
    "solver_attempts": "count",
    "ax_completed_observations": "count",
    "standardized_slack": "posterior standard deviations",
    "minimum_raw_slack": "metric units",
    "best_raw_slack": "metric units",
    "resolvable_by_surrogate": "boolean",
}

#: Tables that also get Markdown and JSON, because they are the ones a human
#: reads directly rather than loads into a script.
SUMMARY_TABLES: tuple[str, ...] = (
    "bo_best_objective_so_far_by_iteration",
    "bo_top_ranked_valid_designs",
    "bo_invalid_and_failed_trials",
    "demo11_demo12_demo13_best_design_comparison",
    "bo_parameter_importance",
    "bo_pareto_optimal_designs",
    "bo_random_grid_search_efficiency_comparison",
    "bo_run_plan_and_case_counts",
    "bo_demo12_warm_start_provenance",
    "bo_search_space_definition",
    "bo_constraint_modelling_decisions",
    "bo_budget_accounting",
)

#: Every table Demo 13 promises, with the meaning of one row.
TABLE_CATALOGUE: Mapping[str, str] = {
    "bo_all_trials_parameters_and_outcomes": "one Ax trial, with every input parameter, physical output, QC metric, objective, constraint, status and provenance path",
    "bo_trial_input_parameters": "one Ax trial's canonical design parameters and the geometry they resolve to",
    "bo_trial_nonlinear_optical_outputs": "one Ax trial's chi(2) measures",
    "bo_trial_electronic_structure_outputs": "one Ax trial's energies, gaps, overlaps and matrix elements",
    "bo_trial_state_localization_and_tracking": "one Ax trial's state-character probabilities and state-tracking result",
    "bo_trial_quality_control_results": "one Ax trial's numerical-quality and validity checks",
    "bo_best_objective_so_far_by_iteration": "one BO iteration, with the best valid objective found up to and including it",
    "bo_top_ranked_valid_designs": "one valid design, ranked by the active objective",
    "bo_invalid_and_failed_trials": "one rejected or failed trial, with the exact reason",
    "demo11_demo12_demo13_best_design_comparison": "one reference or best design from Demos 11, 12 and 13, on identical columns",
    "bo_generated_candidates_by_iteration": "one Ax proposal, with its lifecycle state (proposed, executed, completed, rejected, failed, duplicate)",
    "bo_surrogate_predictions_selected_parameter_slices": "one point of a surrogate slice, with predicted mean and standard error",
    "bo_acquisition_values_for_proposed_candidates": "one proposed candidate, with the acquisition value Ax reported for it",
    "bo_parameter_importance": "one parameter's first-order Sobol sensitivity for one modelled metric",
    "bo_pareto_optimal_designs": "one nondominated design under the active multi-objective set",
    "bo_top_designs_local_validation_results": "one local-refinement, mesh, state-count or padding check on a top design",
    "bo_top_designs_fabrication_robustness": "one fabrication perturbation applied to a top design",
    "bo_random_grid_search_efficiency_comparison": "one search method, with the evaluations it needed to reach the best known design",
    "bo_run_plan_and_case_counts": "the planned and completed evaluation budget for this run",
    "bo_demo12_warm_start_provenance": "one candidate Demo 12 case, with its compatibility decision and whether Ax used it",
    "bo_search_space_definition": "one active search-space parameter",
    "bo_constraint_feasibility_audit": "one (trial, constraint) pair, with the exact value, threshold, comparison and verdict, and whether Ax was told about it",
    "bo_constraint_modelling_decisions": "one configured constraint, with its observed spread and why it is or is not modelled by the surrogate",
    "bo_candidate_rejection_history": "one Ax proposal that was refused before the solver ran, with the reason and the replacement that ran instead",
    "bo_budget_accounting": "the run's proposal and evaluation counters, kept separate",
    "bo_geometry_feasibility_by_layer": "one layer of one trial's stack, with how much a centred grade consumes and whether flat material survives",
}


def unit_for(column: str) -> str:
    """Unit of one column, matched by name and then by suffix."""

    name = str(column)
    if name in COLUMN_UNITS:
        return COLUMN_UNITS[name]
    for suffix, unit in (
        ("_nm", "nm"),
        ("_eV", "eV"),
        ("_meV", "meV"),
        ("_probability", "probability"),
        ("_seconds", "s"),
        ("_count", "count"),
        # A fraction is dimensionless. Falling through to "unspecified" is how a
        # ratio ends up beside a column of nanometres with nothing to tell them
        # apart -- which is the whole failure this demo is being hardened
        # against.
        ("_fraction", "dimensionless"),
        ("_fraction_of_feasible_max", "dimensionless"),
        ("_fraction_of_nominal", "dimensionless"),
        ("_predicted_mean", "metric units"),
        ("_predicted_standard_error", "metric units"),
    ):
        if name.endswith(suffix):
            return unit
    return "unspecified"


def _flatten(value: Any) -> Any:
    """CSV-safe rendering: lists and mappings become compact strings."""

    if isinstance(value, (list, tuple)):
        return ";".join(str(_flatten(item)) for item in value)
    if isinstance(value, Mapping):
        return ";".join(f"{key}={_flatten(item)}" for key, item in value.items())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_table(
    parent: Path,
    name: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    markdown: bool | None = None,
    note: str = "",
) -> Path:
    """Write one table as CSV, its units sidecar, and optionally Markdown/JSON."""

    tables = Path(parent) / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    data = [dict(row) for row in rows]
    fieldnames: list[str] = []
    for row in data:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(str(key))
    if not fieldnames:
        fieldnames = ["note"]
        data = [{"note": note or "no rows for this table in this run"}]
    csv_path = tables / f"{name}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow({key: _flatten(row.get(key)) for key in fieldnames})
    write_json_atomically(
        tables / f"{name}.units.json",
        {
            "table": name,
            "row_meaning": TABLE_CATALOGUE.get(name, ""),
            "note": note,
            "columns": {column: unit_for(column) for column in fieldnames},
        },
    )
    if markdown is None:
        markdown = name in SUMMARY_TABLES
    if markdown:
        write_json_atomically(tables / f"{name}.json", data)
        write_text_atomically(tables / f"{name}.md", _markdown(name, fieldnames, data, note))
    return csv_path


def _markdown(
    name: str, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]], note: str
) -> str:
    header = [f"# {name}", ""]
    if TABLE_CATALOGUE.get(name):
        header += [f"One row = {TABLE_CATALOGUE[name]}.", ""]
    if note:
        header += [note, ""]
    header += [
        "| " + " | ".join(f"{column} ({unit_for(column)})" for column in fieldnames) + " |",
        "|" + "---|" * len(fieldnames),
    ]
    for row in rows:
        cells = []
        for column in fieldnames:
            value = _flatten(row.get(column))
            if isinstance(value, float):
                cells.append(f"{value:.6g}")
            else:
                cells.append("—" if value is None else str(value))
        header.append("| " + " | ".join(cells) + " |")
    return "\n".join(header) + "\n"


# ---------------------------------------------------------------------------
# projections of the ledger
# ---------------------------------------------------------------------------


_INPUT_COLUMNS = (
    "trial_index", "iteration", "candidate_id", "generation_method",
    "parameter_asymmetry_s", "parameter_central_barrier_thickness_nm",
    "parameter_grading_thickness_nm", "parameter_grading_profile",
    "resolved_wide_well_nm", "resolved_narrow_well_nm",
    "resolved_central_barrier_nm", "grading_implementation", "status",
)

_NONLINEAR_COLUMNS = (
    "trial_index", "iteration", "candidate_id", "chi2_mode", "chi2_units",
    "relative_peak_chi2_abs", "peak_wavelength_nm", "relative_chi2_at_target_wavelength_abs",
    "signed_detuning_nm", "absolute_detuning_nm", "relative_integrated_chi2_abs",
    "integrated_wavelength_window_nm", "bandwidth_above_fraction_nm",
    "bandwidth_fraction_of_peak", "trial_valid", "status",
)

_ELECTRONIC_COLUMNS = (
    "trial_index", "iteration", "candidate_id", "E_e1_eV", "E_e2_eV", "E_hh1_eV",
    "E_hh2_eV", "transition_e1_hh1_eV", "transition_e2_hh2_eV",
    "anticrossing_gap_meV", "heavy_hole_anticrossing_gap_meV",
    "electron_level_gaps_meV", "heavy_hole_level_gaps_meV", "overlap_e1_hh1",
    "overlap_e2_hh2", "z_e1_e1_nm", "z_e1_e2_nm", "z_e2_e2_nm", "z_hh1_hh1_nm",
    "z_hh1_hh2_nm", "z_hh2_hh2_nm", "electron_hole_centroid_separation_nm",
    "intersubband_dipole_e1_e2_e_nm", "intersubband_oscillator_strength_e1_e2",
    "status",
)

_LOCALIZATION_COLUMNS = (
    "trial_index", "iteration", "candidate_id", "narrow_well_probability",
    "wide_well_probability", "electron2_narrow_well_probability",
    "electron2_wide_well_probability", "central_barrier_probability",
    "outer_barrier_probability", "left_boundary_probability",
    "right_boundary_probability", "total_boundary_probability",
    "maximum_boundary_probability", "raw_solver_state_index",
    "raw_state_indices", "tracked_state_labels", "state_tracking_confidence",
    "state_tracking_margin", "state_tracking_ambiguous",
    "state_tracking_reference_trial", "state_tracking_method", "status",
)

_QC_COLUMNS = (
    "trial_index", "iteration", "candidate_id", "solver_completed",
    "expected_outputs_available", "normalization_valid", "orthonormality_error",
    "orthonormality_tolerance", "origin_independence_absolute_residual",
    "origin_independence_relative_residual", "origin_independence_comparison_mode",
    "origin_independence_valid", "bound_state_count",
    "states_failing_bound_criterion", "states_failing_bound_criterion_in_chi2_sum",
    "quasi_bound_policy", "requested_electron_states", "extracted_electron_states",
    "chi2_max_states_per_band", "chi2_electron_states_used",
    "chi2_heavy_hole_states_used", "chi2_triple_sum_terms_evaluated",
    "chi2_triple_sum_terms_significant", "solver_states_not_reaching_the_sum",
    "required_states_valid", "physical_qc_valid", "physical_qc_failed_tests",
    "trial_valid", "valid_low_response", "constraint_violations",
    "rejection_reason", "status",
)


def _project(records: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> list[dict[str, Any]]:
    return [{column: record.get(column) for column in columns} for record in records]


def objective_metric_name(spec: Any) -> str:
    return spec.objective_metrics[0] if spec.objective_metrics else "objective_value"


def best_so_far_by_iteration(
    records: Sequence[Mapping[str, Any]], spec: Any
) -> list[dict[str, Any]]:
    """Best *valid* objective up to and including each BO iteration.

    An invalid trial never improves the best-so-far curve.  Letting it would
    make the headline plot of the whole demo report a number that failed quality
    control, which is precisely the failure mode Section 22 forbids.
    """

    metric = objective_metric_name(spec)
    minimize = metric in set(spec.minimized_metrics)
    iterations = sorted({int(record.get("iteration", 0)) for record in records})
    rows: list[dict[str, Any]] = []
    best: float | None = None
    best_trial: int | None = None
    for iteration in iterations:
        for record in sorted(
            (row for row in records if int(row.get("iteration", 0)) == iteration),
            key=lambda row: int(row.get("trial_index", 0)),
        ):
            if str(record.get("status")) != "completed" or not record.get("trial_valid"):
                continue
            value = record.get(metric)
            if value is None:
                continue
            candidate = float(value)
            better = (
                best is None
                or (candidate < best if minimize else candidate > best)
            )
            if better:
                best, best_trial = candidate, int(record.get("trial_index", -1))
        counted = [row for row in records if int(row.get("iteration", 0)) <= iteration]
        rows.append(
            {
                "iteration": iteration,
                "objective_metric": metric,
                "objective_direction": "minimize" if minimize else "maximize",
                "trials_run_through_iteration": len(counted),
                "valid_trials_through_iteration": sum(
                    1 for row in counted if row.get("trial_valid")
                ),
                "best_objective_so_far": best,
                "best_trial_index": best_trial,
            }
        )
    return rows


def _grading_columns(record: Mapping[str, Any]) -> dict[str, Any]:
    """Semantic grading columns for a table row, or a stated absence.

    ``source`` is dropped: it describes where :mod:`grading13` read the numbers
    from, which is provenance for a debugger rather than a column of a results
    table.
    """

    view = grading13.try_from_record(record)
    if view is None:
        return {
            "realized_grading_thickness_nm": None,
            "realized_interface_mode": grading13.UNKNOWN,
            "grading_unavailable_reason": (
                "this ledger record carries no realized grading thickness under any "
                "known field name"
            ),
        }
    return {key: value for key, value in view.as_record().items() if key != "source"}


def top_ranked_valid_designs(
    records: Sequence[Mapping[str, Any]], spec: Any, *, limit: int = 20
) -> list[dict[str, Any]]:
    metric = objective_metric_name(spec)
    minimize = metric in set(spec.minimized_metrics)
    valid = [
        record
        for record in records
        if str(record.get("status")) == "completed"
        and record.get("trial_valid")
        and record.get(metric) is not None
        and math.isfinite(float(record[metric]))
    ]
    # Deterministic on ties. Sorting by objective alone leaves equal-objective
    # trials in whatever order the ledger happened to yield, so two runs over
    # the same completed study could disagree about which design is "rank 1".
    # The trial index breaks the tie: earlier trial wins, always.
    ordered = sorted(
        valid,
        key=lambda row: (
            float(row[metric]) if minimize else -float(row[metric]),
            int(row.get("trial_index", 0)),
        ),
    )
    return [
        {
            "rank": index,
            "trial_index": record.get("trial_index"),
            "iteration": record.get("iteration"),
            "objective_metric": metric,
            "objective_value": record.get(metric),
            **{
                name: record.get(name)
                for name in (
                    "parameter_asymmetry_s", "parameter_central_barrier_thickness_nm",
                    "parameter_grading_thickness_nm", "parameter_grading_profile",
                    "relative_peak_chi2_abs", "peak_wavelength_nm",
                    "relative_chi2_at_target_wavelength_abs", "signed_detuning_nm",
                    "maximum_boundary_probability", "state_tracking_confidence",
                    "orthonormality_error", "physical_qc_valid",
                )
            },
            # Realized-versus-proposed, so a reader ranking designs is never
            # left guessing whether `parameter_grading_thickness_nm` was what
            # Ax asked for or what the mesh built.
            **_grading_columns(record),
            "validated": False,
            "validation_note": "Ax objective only; Stage 5 local, mesh, state-count "
            "and padding checks have not been applied to this row",
            "objective_scale_note": "relative nonlinear-optical merit in arbitrary "
            "units; not calibrated chi(2) in pm/V",
        }
        for index, record in enumerate(ordered[:limit], start=1)
    ]


def invalid_and_failed_trials(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        status = str(record.get("status"))
        if status == "completed" and record.get("trial_valid"):
            continue
        rows.append(
            {
                "trial_index": record.get("trial_index"),
                "iteration": record.get("iteration"),
                "candidate_id": record.get("candidate_id"),
                "status": status,
                "trial_outcome_class": record.get("trial_outcome_class"),
                "reported_to_ax_as": record.get("reported_to_ax_as"),
                "failure_reason": record.get("failure_reason"),
                "rejection_reason": record.get("rejection_reason"),
                "constraint_violations": record.get("constraint_violations"),
                "physical_qc_failed_tests": record.get("physical_qc_failed_tests"),
                **{
                    name: record.get(name)
                    for name in (
                        "parameter_asymmetry_s",
                        "parameter_central_barrier_thickness_nm",
                        "parameter_grading_thickness_nm",
                        "parameter_grading_profile",
                        "relative_chi2_at_target_wavelength_abs",
                        "relative_peak_chi2_abs",
                    )
                },
                "output_directory_path": record.get("output_directory_path"),
            }
        )
    return rows


def pareto_designs(
    records: Sequence[Mapping[str, Any]], spec: Any, *, ax_frontier: Sequence[Mapping[str, Any]] = ()
) -> list[dict[str, Any]]:
    """Nondominated valid designs, from Ax in MOO mode and from the data otherwise.

    In single-objective mode Ax has no frontier to report, but the tradeoff
    between intrinsic strength, wavelength match and robustness still exists in
    the data, so it is computed here with the same Demo 12 helper Demo 12 used.
    """

    objectives: dict[str, str] = {}
    for name in spec.objective_metrics:
        objectives[name] = "minimize" if name in set(spec.minimized_metrics) else "maximize"
    if len(objectives) < 2:
        objectives = {
            "relative_peak_chi2_abs": "maximize",
            "relative_chi2_at_target_wavelength_abs": "maximize",
            "absolute_detuning_nm": "minimize",
        }
    usable = [
        dict(record)
        for record in records
        if str(record.get("status")) == "completed"
        and record.get("trial_valid")
        and all(record.get(name) is not None for name in objectives)
    ]
    front = grading12.pareto_front(usable, objectives)
    ax_indices = {int(row["trial_index"]) for row in ax_frontier if "trial_index" in row}
    return [
        {
            "trial_index": row.get("trial_index"),
            "iteration": row.get("iteration"),
            "pareto_source": "ax_and_data"
            if int(row.get("trial_index", -1)) in ax_indices
            else "data",
            "objectives": ";".join(f"{name}:{direction}" for name, direction in objectives.items()),
            **{
                name: row.get(name)
                for name in (
                    "parameter_asymmetry_s", "parameter_central_barrier_thickness_nm",
                    "parameter_grading_thickness_nm", "parameter_grading_profile",
                    "relative_peak_chi2_abs", "relative_chi2_at_target_wavelength_abs", "peak_wavelength_nm",
                    "signed_detuning_nm", "absolute_detuning_nm", "robustness_score",
                    "maximum_boundary_probability", "state_tracking_confidence",
                )
            },
        }
        for row in front
    ]


def search_space_rows(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    encoding = str(cfg["bo"]["search_space"].get("encoding", "hierarchical"))
    rows = [spec.as_row() for spec in design13.search_space_specs(cfg)]
    for row in rows:
        row["encoding"] = encoding
        row["unit"] = unit_for(f"parameter_{row['parameter']}")
    if encoding == "hierarchical":
        lower, upper = design13.graded_thickness_bounds(cfg)
        rows.insert(
            0,
            {
                "parameter": "interface_mode",
                "type": "choice (hierarchical root)",
                "lower": None,
                "upper": None,
                "values": "abrupt;graded",
                "encoding": encoding,
                "unit": "category",
            },
        )
        for row in rows:
            if row["parameter"] == "grading_thickness_nm":
                row["lower"] = lower
                row["upper"] = upper
                row["type"] = "range (only present when interface_mode=graded)"
            if row["parameter"] == "grading_profile":
                row["values"] = ";".join(design13.graded_profiles(cfg))
                row["type"] = "choice (only present when interface_mode=graded)"
    return rows


def write_all(
    parent: Path,
    *,
    cfg: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    spec: Any,
    candidates: Sequence[Mapping[str, Any]] = (),
    surrogate_rows: Sequence[Mapping[str, Any]] = (),
    acquisition_rows: Sequence[Mapping[str, Any]] = (),
    importance: Mapping[str, Any] | None = None,
    ax_frontier: Sequence[Mapping[str, Any]] = (),
    comparison_rows: Sequence[Mapping[str, Any]] = (),
    validation_rows: Sequence[Mapping[str, Any]] = (),
    robustness_rows: Sequence[Mapping[str, Any]] = (),
    efficiency_rows: Sequence[Mapping[str, Any]] = (),
    warm_start_rows: Sequence[Mapping[str, Any]] = (),
    plan_record: Mapping[str, Any] | None = None,
    rejection_rows: Sequence[Mapping[str, Any]] = (),
    budget_record: Mapping[str, Any] | None = None,
    synthetic: bool = False,
) -> list[str]:
    """Write the complete table set and return the filenames written."""

    note = (
        "SYNTHETIC — NOT LICENSED NEXTNANO OUTPUT. Generated by the Stage 1 "
        "solver-free smoke test."
        if synthetic
        else ""
    )
    written: list[str] = []

    def emit(name: str, rows: Sequence[Mapping[str, Any]], **kwargs: Any) -> None:
        write_table(parent, name, rows, note=note, **kwargs)
        written.append(name)

    emit("bo_all_trials_parameters_and_outcomes", records)
    emit("bo_trial_input_parameters", _project(records, _INPUT_COLUMNS))
    emit("bo_trial_nonlinear_optical_outputs", _project(records, _NONLINEAR_COLUMNS))
    emit("bo_trial_electronic_structure_outputs", _project(records, _ELECTRONIC_COLUMNS))
    emit("bo_trial_state_localization_and_tracking", _project(records, _LOCALIZATION_COLUMNS))
    emit("bo_trial_quality_control_results", _project(records, _QC_COLUMNS))
    emit("bo_best_objective_so_far_by_iteration", best_so_far_by_iteration(records, spec))
    emit("bo_top_ranked_valid_designs", top_ranked_valid_designs(records, spec))
    emit("bo_invalid_and_failed_trials", invalid_and_failed_trials(records))
    emit("demo11_demo12_demo13_best_design_comparison", comparison_rows)
    emit("bo_generated_candidates_by_iteration", candidates)
    emit("bo_surrogate_predictions_selected_parameter_slices", surrogate_rows)
    emit("bo_acquisition_values_for_proposed_candidates", acquisition_rows)
    emit("bo_parameter_importance", _importance_rows(importance))
    emit("bo_pareto_optimal_designs", pareto_designs(records, spec, ax_frontier=ax_frontier))
    emit("bo_top_designs_local_validation_results", validation_rows)
    emit("bo_top_designs_fabrication_robustness", robustness_rows)
    emit("bo_random_grid_search_efficiency_comparison", efficiency_rows)
    emit("bo_search_space_definition", search_space_rows(cfg))
    constraint_specs = feasibility13.build_constraints(cfg)
    emit("bo_constraint_feasibility_audit", feasibility13.audit_rows(records, constraint_specs))
    emit("bo_candidate_rejection_history", rejection_rows)
    emit("bo_budget_accounting", [dict(budget_record)] if budget_record else [])
    emit(
        "bo_constraint_modelling_decisions",
        feasibility13.constraint_spread(records, constraint_specs),
    )
    emit("bo_demo12_warm_start_provenance", warm_start_rows)
    emit("bo_run_plan_and_case_counts", [dict(plan_record)] if plan_record else [])
    return written


def _importance_rows(importance: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not importance:
        return []
    if not importance.get("available"):
        return [
            {
                "metric": None,
                "parameter": None,
                "importance": None,
                "method": importance.get("method"),
                "available": False,
                "reason": importance.get("reason"),
            }
        ]
    rows: list[dict[str, Any]] = []
    for metric, values in (importance.get("importance") or {}).items():
        for parameter, value in values.items():
            rows.append(
                {
                    "metric": metric,
                    "parameter": parameter,
                    "importance": value,
                    "absolute_importance": abs(float(value)),
                    "method": importance.get("method"),
                    "available": True,
                    "reason": "",
                }
            )
    return sorted(rows, key=lambda row: -row["absolute_importance"])
