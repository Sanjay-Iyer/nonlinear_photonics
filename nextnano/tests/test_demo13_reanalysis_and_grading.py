"""Home-laptop tests for Demo 13 reanalysis, model reconstruction and grading.

No nextnano executable is invoked anywhere in this file, and none of these
tests needs a licensed solver.  They cover the two defects that made the
completed 16-trial licensed study unreportable:

* a deserialized Ax client has no fitted adapter, so every surrogate-derived
  output came back empty while the observations sat in the snapshot;
* plotting and reporting code still looked for ``grading_thickness_nm`` after
  the search space moved to ``grading_fraction_of_feasible_max``, which blanked
  figures *silently* rather than raising.

Where an evaluated study is needed, the deterministic Stage 1 synthetic surface
provides it.  It has the same hierarchical search space, the same metrics and
the same ledger schema as the licensed run, so it exercises the same code paths
without presenting any number as a physical result.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "nextnano" / "demos" / "13_ax_bayesian_optimization_graded_acqw"
SHARED = DEMO.parent / "_shared"
DEMO11 = DEMO.parent / "11_paper_validation_interband_chi2_acqw"
DEMO12 = DEMO.parent / "12_graded_interface_coupled_quantum_well_optimization"
for path in (str(DEMO), str(SHARED), str(DEMO11), str(DEMO12)):
    if path not in sys.path:
        sys.path.insert(0, path)

import analysis13  # noqa: E402
import axsearch13  # noqa: E402
import demo13  # noqa: E402
import demo_workflow  # noqa: E402
import design13  # noqa: E402
import grading13  # noqa: E402
import plots13  # noqa: E402
import synthetic13  # noqa: E402
import tables13  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


@pytest.fixture(scope="module")
def evaluated_study(tmp_path_factory, cfg):
    """A completed, checkpointed study on the synthetic surface.

    Six initial trials plus four model-based iterations is enough to leave the
    generation strategy on a model-based node, which is the state the licensed
    run finished in and the state the reconstruction has to handle.
    """

    small = copy.deepcopy(cfg)
    small["bo"]["num_initial_trials"] = 6
    small["bo"]["num_iterations"] = 4
    small["bo"]["batch_size"] = 1
    state = tmp_path_factory.mktemp("study") / "demo13_ax_experiment_synthetic"
    outcome = demo13.synthetic_loop(small, state)
    return {"cfg": small, "state_dir": state, "experiment": outcome["experiment"]}


# ---------------------------------------------------------------------------
# Phase 1 -- the experiment state is protected
# ---------------------------------------------------------------------------


def test_state_manifest_round_trips_and_detects_change(evaluated_study):
    state = evaluated_study["state_dir"]
    manifest = analysis13.state_manifest(state)
    assert manifest["ledger_record_count"] > 0
    assert manifest["trial_file_count"] == manifest["ledger_record_count"]
    assert manifest["files"]["ax_experiment_snapshot.json"]["sha256"]
    assert analysis13.verify_state_manifest(state, manifest)["unchanged"] is True

    snapshot = state / "ax_experiment_snapshot.json"
    snapshot.write_text(snapshot.read_text(encoding="utf-8") + " ", encoding="utf-8")
    verdict = analysis13.verify_state_manifest(state, manifest)
    assert verdict["unchanged"] is False
    assert "ax_experiment_snapshot.json" in verdict["changed_entries"]


def test_reconstruction_never_modifies_terminal_ledger_records(evaluated_study):
    """The Phase 1 promise, checked at record granularity."""

    state = evaluated_study["state_dir"]
    before = analysis13.terminal_ledger_fingerprint(state)
    assert before, "the synthetic study should have terminal records"

    model = analysis13.reconstruct_predictive_model(state / "ax_experiment_snapshot.json")
    model.predict(
        [{"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8, "interface_mode": "abrupt"}]
    )
    model.parameter_importance()

    after = analysis13.terminal_ledger_fingerprint(state)
    assert after == before
    assert model.record["original_experiment_state_modified"] is False


def test_read_only_experiment_refuses_every_mutation(evaluated_study, cfg):
    state = evaluated_study["state_dir"]
    experiment = demo13.Experiment(evaluated_study["cfg"], state, read_only=True)
    assert experiment.resumed is True
    assert experiment.ledger.records(), "read-only mode must still read the ledger"

    for action in ("checkpoint", "generate", "complete", "fail", "abandon"):
        with pytest.raises(demo_workflow.DemoError, match="read-only"):
            if action == "checkpoint":
                experiment.checkpoint()
            elif action == "generate":
                experiment.generate(1)
            elif action == "complete":
                experiment.complete(0, {"relative_chi2_at_target_wavelength_abs": 1.0})
            elif action == "fail":
                experiment.fail(0, "no")
            else:
                experiment.abandon(0, "no")


def test_read_only_refuses_to_invent_a_missing_experiment(cfg, tmp_path):
    """Selecting the wrong directory must fail loudly, not create a study."""

    missing = tmp_path / "demo13_ax_experiment_v2"
    with pytest.raises(demo_workflow.DemoError, match="will not create one"):
        demo13.Experiment(cfg, missing, read_only=True)
    assert not (missing / "ax_experiment_snapshot.json").exists()


def test_terminal_ledger_records_are_immutable_even_with_allow_update(tmp_path):
    ledger = axsearch13.Ledger(tmp_path)
    ledger.write({"trial_index": 0, "status": "completed"})
    with pytest.raises(demo_workflow.DemoError, match="never rewrites"):
        ledger.write({"trial_index": 0, "status": "completed"}, allow_update=True)


def test_read_only_ledger_creates_nothing(tmp_path):
    root = tmp_path / "absent"
    axsearch13.Ledger(root, read_only=True)
    assert not root.exists()


# ---------------------------------------------------------------------------
# Phase 2 -- the predictive adapter is reconstructed
# ---------------------------------------------------------------------------


def test_predictive_adapter_is_reconstructed_without_advancing_the_strategy(
    evaluated_study,
):
    state = evaluated_study["state_dir"]
    model = analysis13.reconstruct_predictive_model(state / "ax_experiment_snapshot.json")
    record = model.record

    assert model.available, record["fit_status_reason"]
    assert record["fit_status"] == "refitted_current_generation_node"
    assert record["generation_strategy_advanced"] is False
    assert record["new_trials_generated"] is False
    assert record["original_experiment_state_modified"] is False
    assert record["generation_node_before"] == record["generation_node_after"]
    assert record["ax_version"]
    assert record["observations_used"] > 0
    # Trials, not metric rows: one trial contributes several rows.
    assert record["observations_used"] <= record["observation_rows_used"]
    assert record["objective_metric"]
    assert record["constraint_metrics"]


def test_reconstruction_fits_only_completed_finite_observations(evaluated_study):
    model = analysis13.reconstruct_predictive_model(
        evaluated_study["state_dir"] / "ax_experiment_snapshot.json"
    )
    assert model.record["data_rows_dropped_not_completed"] == 0
    assert model.record["data_rows_dropped_non_finite"] == 0
    assert model.record["observations_used"] == model.record["data_completed_trials"]


def test_objective_and_constraint_predictions_are_finite(evaluated_study):
    model = analysis13.reconstruct_predictive_model(
        evaluated_study["state_dir"] / "ax_experiment_snapshot.json"
    )
    rows = model.predict(
        [{"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8, "interface_mode": "abrupt"}]
    )
    row = rows[0]
    assert row["prediction_available"] is True
    means = {
        key: value for key, value in row.items() if str(key).endswith("_predicted_mean")
    }
    assert means, "the objective must be predicted"
    import math

    assert all(math.isfinite(float(value)) for value in means.values())
    sems = [
        value
        for key, value in row.items()
        if str(key).endswith("_predicted_standard_error") and value is not None
    ]
    assert sems and all(math.isfinite(float(value)) for value in sems)
    # The modelled outcome constraints must be predictable too, not only the
    # objective: feasibility is what the surrogate is being asked about.
    assert any("detuning" in key for key in means)


def test_hierarchical_branches_predict_and_invalid_ones_say_why(evaluated_study):
    model = analysis13.reconstruct_predictive_model(
        evaluated_study["state_dir"] / "ax_experiment_snapshot.json"
    )
    abrupt = {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
              "interface_mode": "abrupt"}
    graded = {**abrupt, "interface_mode": "graded",
              "grading_fraction_of_feasible_max": 0.5, "grading_profile": "linear"}
    abrupt_with_children = {**abrupt, "grading_fraction_of_feasible_max": 0.5,
                            "grading_profile": "linear"}
    graded_missing_children = {**abrupt, "interface_mode": "graded"}

    rows = model.predict([abrupt, graded, abrupt_with_children, graded_missing_children])
    assert rows[0]["prediction_available"] is True
    assert rows[1]["prediction_available"] is True
    assert rows[2]["prediction_available"] is False
    assert rows[3]["prediction_available"] is False
    for bad in rows[2:]:
        assert "not a valid parameterization" in bad["reason"]
        # The reason must be about the search space, never about the solver.
        assert "licensed" not in bad["reason"].lower()


def test_parameter_importance_is_populated_and_caveated(evaluated_study):
    model = analysis13.reconstruct_predictive_model(
        evaluated_study["state_dir"] / "ax_experiment_snapshot.json"
    )
    importance = model.parameter_importance()
    assert importance["available"] or importance["reason"]
    assert "not a statistical significance test" in importance["interpretation_caveat"]
    for values in importance["importance"].values():
        # Ax's internal one-hot columns are an encoding detail, never a design
        # parameter, and must not reach a report.
        assert not any("_OH_PARAM_" in name for name in values)


def test_unavailable_model_reports_a_truthful_reason_not_a_missing_solver(tmp_path):
    model = analysis13.reconstruct_predictive_model(tmp_path / "does_not_exist.json")
    assert model.available is False
    assert "no Ax snapshot exists" in model.record["fit_status_reason"]
    rows = model.predict([{"asymmetry_s": 0.4}])
    assert rows[0]["prediction_available"] is False
    assert "licensed" not in rows[0]["reason"].lower()


def test_reconstruction_report_is_written_outside_the_experiment_directory(
    evaluated_study, tmp_path
):
    model = analysis13.reconstruct_predictive_model(
        evaluated_study["state_dir"] / "ax_experiment_snapshot.json"
    )
    path = analysis13.write_reconstruction_report(tmp_path, model)
    assert path.name == "analysis_model_reconstruction.json"
    assert not (evaluated_study["state_dir"] / path.name).exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key in (
        "ax_version", "observations_used", "objective_metric", "constraint_metrics",
        "model_class", "fit_status", "predictive_metrics",
        "reconstruction_timestamp_utc", "original_experiment_state_modified",
    ):
        assert key in payload, key


# ---------------------------------------------------------------------------
# Phase 3 -- one authoritative reading of the grading
# ---------------------------------------------------------------------------


def test_abrupt_always_realizes_zero_grading(cfg):
    view = grading13.from_parameters(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
         "interface_mode": "abrupt"},
        cfg,
    )
    assert view.realized_grading_thickness_nm == 0.0
    assert view.realized_interface_mode == grading13.ABRUPT
    assert view.realized_grading_profile == grading13.ABRUPT
    assert view.is_genuinely_graded is False
    assert view.profile_evidence is None


def test_graded_proposal_that_snaps_to_zero_is_physically_abrupt():
    record = {
        "trial_index": 7,
        "parameters": {"interface_mode": "graded", "grading_profile": "cosine",
                       "grading_fraction_of_feasible_max": 0.05},
        "canonical_parameters": {"grading_thickness_nm": 0.0,
                                 "grading_profile": "abrupt",
                                 "_proposed_grading_fraction": 0.05,
                                 "_maximum_feasible_grading_nm": 0.08},
    }
    view = grading13.from_record(record)
    assert view.proposed_interface_mode == grading13.GRADED
    assert view.proposed_grading_profile == "cosine"
    assert view.realized_interface_mode == grading13.ABRUPT
    assert view.realized_grading_profile == grading13.ABRUPT
    assert view.collapsed_to_abrupt is True
    # The whole point: this trial is not evidence about the cosine profile,
    # because no cosine grade was ever built.
    assert view.profile_evidence is None


def test_unsnapped_and_realized_thickness_are_distinguished():
    record = {
        "trial_index": 12,
        "parameters": {"interface_mode": "graded", "grading_profile": "sigmoid",
                       "grading_fraction_of_feasible_max": 0.9343092},
        "canonical_parameters": {"grading_thickness_nm": 1.1,
                                 "grading_profile": "sigmoid",
                                 "_proposed_grading_fraction": 0.9343092,
                                 "_maximum_feasible_grading_nm": 1.1839421},
    }
    view = grading13.from_record(record)
    assert view.realized_grading_thickness_nm == pytest.approx(1.1)
    assert view.proposed_grading_thickness_nm_unsnapped == pytest.approx(
        0.9343092 * 1.1839421
    )
    # The mesh snap is visible: the request and the structure differ, and both
    # are reported rather than one standing in for the other.
    assert view.proposed_grading_thickness_nm_unsnapped > view.realized_grading_thickness_nm
    assert view.proposed_grading_fraction == pytest.approx(0.9343092)
    assert view.is_genuinely_graded is True
    assert view.profile_evidence == "sigmoid"


def test_grading_view_reads_both_v2_ledger_spellings():
    """Completed and rejected v2 trials stored the maximum under different names."""

    completed = {"trial_index": 1, "parameters": {"interface_mode": "graded",
                                                 "grading_profile": "linear"},
                 "realized_grading_thickness_nm": 0.9,
                 "maximum_feasible_grading_nm": 1.2,
                 "proposed_grading_fraction": 0.75}
    rejected = {"trial_index": 2, "parameters": {"interface_mode": "graded",
                                                 "grading_profile": "linear"},
                "realized_grading_thickness_nm": 0.9,
                "maximum_feasible_grading_thickness_nm": 1.2,
                "proposed_grading_fraction": 0.75}
    for record in (completed, rejected):
        view = grading13.from_record(record)
        assert view.maximum_feasible_grading_nm == pytest.approx(1.2)
        assert view.realized_grading_thickness_nm == pytest.approx(0.9)


def test_grading_view_never_invents_a_zero_for_an_unreadable_record():
    with pytest.raises(grading13.GradingError):
        grading13.from_record({"trial_index": 3})
    assert grading13.try_from_record({"trial_index": 3}) is None


def test_evidence_counts_refuse_to_support_a_ranking_from_single_samples():
    records = [
        {"trial_index": i, "parameters": {"interface_mode": "graded",
                                          "grading_profile": profile},
         "canonical_parameters": {"grading_thickness_nm": 1.0,
                                  "grading_profile": profile}}
        for i, profile in enumerate(("linear", "sigmoid", "erf"))
    ]
    counts = grading13.evidence_counts(records)
    assert counts["genuinely_graded_trials"] == 3
    assert counts["profile_ranking_supportable"] is False

    plenty = [
        {"trial_index": i, "parameters": {"interface_mode": "graded",
                                          "grading_profile": profile},
         "canonical_parameters": {"grading_thickness_nm": 1.0,
                                  "grading_profile": profile}}
        for i, profile in enumerate(["linear"] * 3 + ["sigmoid"] * 3)
    ]
    assert grading13.evidence_counts(plenty)["profile_ranking_supportable"] is True


def test_collapsed_graded_trials_are_counted_separately():
    records = [
        {"trial_index": 0, "parameters": {"interface_mode": "graded",
                                          "grading_profile": "cosine"},
         "canonical_parameters": {"grading_thickness_nm": 0.0,
                                  "grading_profile": "abrupt"}},
        {"trial_index": 1, "parameters": {"interface_mode": "abrupt"},
         "canonical_parameters": {"grading_thickness_nm": 0.0,
                                  "grading_profile": "abrupt"}},
    ]
    counts = grading13.evidence_counts(records)
    assert counts["graded_proposals_that_collapsed_to_abrupt"] == 1
    assert counts["realized_abrupt_trials"] == 2
    assert counts["genuinely_graded_trials"] == 0


# ---------------------------------------------------------------------------
# Phase 5 -- surrogate outputs use the coordinate they claim to
# ---------------------------------------------------------------------------


def test_slice_points_use_the_live_grading_parameter(cfg):
    name = design13.grading_parameter_name(cfg)
    assert name == "grading_fraction_of_feasible_max", (
        "this test exists to catch the fraction parameterization; update it "
        "deliberately if the default search space changes"
    )
    points, encoded = demo13._slice_points(cfg, "asymmetry_s", name)
    assert points and len(points) == len(encoded)
    assert all(name in point for point in points)
    # The bug this pins: every encoded point used to come back abrupt, because
    # the encoder looked for a thickness that fraction points do not carry.
    assert all(point["interface_mode"] == "graded" for point in encoded)
    assert all(name in point for point in encoded)
    assert len({point[name] for point in encoded}) > 1


def test_slice_points_reject_a_stale_thickness_axis(cfg):
    with pytest.raises(demo_workflow.DemoError, match="not a range parameter"):
        demo13._slice_points(cfg, "asymmetry_s", "grading_thickness_nm")


def test_encoded_abrupt_points_carry_no_inactive_children(cfg):
    encoded = demo13._encode_search_point(
        cfg,
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
         "grading_profile": "abrupt",
         "grading_fraction_of_feasible_max": 0.5},
    )
    assert encoded["interface_mode"] == "abrupt"
    assert "grading_fraction_of_feasible_max" not in encoded
    assert "grading_profile" not in encoded


def test_slice_rows_carry_realized_thickness_beside_the_fraction(cfg):
    name = design13.grading_parameter_name(cfg)
    points, _ = demo13._slice_points(cfg, "asymmetry_s", name)
    columns = demo13._realized_grading_columns(cfg, points[len(points) // 2])
    assert "realized_grading_thickness_nm" in columns
    assert "proposed_grading_fraction" in columns
    assert columns["realized_grading_thickness_nm"] >= 0.0


def test_grading_axis_label_never_calls_a_fraction_nanometres(cfg):
    key, label = plots13.grading_axis(cfg)
    assert key == "grading_fraction_of_feasible_max"
    assert "nm" not in label.lower().replace("dimensionless", "")
    assert "fraction" in label.lower()

    thickness_cfg = copy.deepcopy(cfg)
    thickness_cfg["bo"]["search_space"]["parameterization"] = "thickness"
    key, label = plots13.grading_axis(thickness_cfg)
    assert key == "grading_thickness_nm"
    assert "(nm)" in label


def test_surrogate_placeholder_never_blames_a_missing_solver(tmp_path):
    path = tmp_path / "bo_surrogate_mean_asymmetry_vs_grading_thickness.png"
    plots13._surrogate_placeholder(
        path, [{"reason": "adapter could not be reconstructed"}]
    )
    text = (path.with_suffix(".txt") if path.with_suffix(".txt").exists() else path)
    # The placeholder writer is shared; assert on the reason string itself,
    # which is what any renderer receives.
    assert "licensed" not in plots13.PLACEHOLDER_REASON_NO_SURROGATE.lower()
    assert "model availability" in plots13.PLACEHOLDER_REASON_NO_SURROGATE.lower()


def test_every_emitted_grading_column_declares_a_unit():
    """A new column without a unit is how a fraction gets read as nanometres."""

    emitted = set(tables13._grading_columns({
        "trial_index": 0,
        "parameters": {"interface_mode": "abrupt"},
        "canonical_parameters": {"grading_thickness_nm": 0.0,
                                 "grading_profile": "abrupt"},
    }))
    missing = sorted(emitted - set(tables13.COLUMN_UNITS))
    assert not missing, f"columns emitted without a declared unit: {missing}"
    # And the one distinction that matters most: the fraction must not be nm.
    fraction_unit = tables13.unit_for("proposed_grading_fraction")
    assert "nm" not in fraction_unit
    assert "fraction" in fraction_unit
    assert tables13.unit_for("realized_grading_thickness_nm") == "nm"
    assert tables13.unit_for("grading_fraction_of_feasible_max") == fraction_unit


def test_grading_columns_are_shared_between_tables_and_plots():
    """demo13 and tables13 must not describe a trial with different names."""

    record = {
        "trial_index": 1,
        "parameters": {"interface_mode": "graded", "grading_profile": "linear"},
        "canonical_parameters": {"grading_thickness_nm": 1.0,
                                 "grading_profile": "linear"},
    }
    assert demo13._grading_columns(record) == tables13._grading_columns(record)


def test_configured_slice_fixed_values_match_the_live_search_space(cfg):
    """A fixed value naming a dead parameter is silently ignored, so pin it."""

    fixed = dict((cfg["bo"].get("surrogate_slices") or {}).get("fixed_values") or {})
    live = {spec.name for spec in design13.search_space_specs(cfg)}
    unknown = sorted(set(fixed) - live - {"grading_profile"})
    assert not unknown, (
        f"surrogate_slices.fixed_values names parameters this search space does "
        f"not have: {unknown}"
    )


# ---------------------------------------------------------------------------
# Phase 6 -- ranking and baseline comparison
# ---------------------------------------------------------------------------


def _ranked_record(index, value, valid=True, status="completed"):
    return {
        "trial_index": index,
        "iteration": index,
        "status": status,
        "trial_valid": valid,
        "relative_chi2_at_target_wavelength_abs": value,
        "parameters": {"interface_mode": "abrupt"},
        "canonical_parameters": {"grading_thickness_nm": 0.0,
                                 "grading_profile": "abrupt"},
    }


class _Spec:
    """Minimal stand-in for :class:`axsearch13.OptimizationSpec`."""

    objective = "relative_chi2_at_target_wavelength_abs"
    objective_metrics: tuple = ("relative_chi2_at_target_wavelength_abs",)
    minimized_metrics: tuple = ()
    is_multi_objective = False


def test_best_trial_is_included_and_ranked_first():
    records = [
        _ranked_record(10, 0.71), _ranked_record(11, 0.83),
        _ranked_record(12, 0.994), _ranked_record(13, 0.55),
    ]
    rows = tables13.top_ranked_valid_designs(records, _Spec(), limit=3)
    assert [row["trial_index"] for row in rows] == [12, 11, 10]
    assert rows[0]["rank"] == 1


def test_top_n_is_deterministic_on_ties():
    records = [_ranked_record(5, 0.9), _ranked_record(2, 0.9), _ranked_record(9, 0.9)]
    first = tables13.top_ranked_valid_designs(records, _Spec(), limit=3)
    second = tables13.top_ranked_valid_designs(list(reversed(records)), _Spec(), limit=3)
    assert [row["trial_index"] for row in first] == [2, 5, 9]
    assert [row["trial_index"] for row in first] == [row["trial_index"] for row in second]


def test_invalid_and_failed_trials_are_excluded_from_the_ranking():
    records = [
        _ranked_record(1, 9.99, valid=False),
        _ranked_record(2, 5.0, status="failed"),
        _ranked_record(3, 0.4),
    ]
    rows = tables13.top_ranked_valid_designs(records, _Spec(), limit=5)
    assert [row["trial_index"] for row in rows] == [3]


def test_non_finite_objectives_never_win_the_ranking():
    records = [_ranked_record(1, float("inf")), _ranked_record(2, 0.5)]
    rows = tables13.top_ranked_valid_designs(records, _Spec(), limit=5)
    assert [row["trial_index"] for row in rows] == [2]


def test_ranked_rows_distinguish_proposed_and_realized_grading():
    rows = tables13.top_ranked_valid_designs([_ranked_record(4, 0.6)], _Spec())
    assert rows[0]["realized_interface_mode"] == grading13.ABRUPT
    assert rows[0]["realized_grading_thickness_nm"] == 0.0
    assert rows[0]["proposed_interface_mode"] == grading13.ABRUPT
    # The note must say the scale is relative and arbitrary. It names pm/V only
    # to deny it, which is the point.
    note = rows[0]["objective_scale_note"]
    assert "arbitrary units" in note and "not calibrated" in note


def test_physics_curves_include_the_supplied_baseline(cfg, tmp_path):
    baseline = {
        "source_demo": "11_paper_validation_interband_chi2_acqw",
        "case_or_trial": "s1_ref",
        "output_directory_path": None,
        "relative_chi2_at_target_wavelength_abs": 0.55,
    }
    curves = demo13.physics_curves(cfg, [], tmp_path, baseline=baseline)
    roles = [row["role"] for row in curves["curve_provenance"]]
    assert "baseline" in roles
    row = next(r for r in curves["curve_provenance"] if r["role"] == "baseline")
    # It has no run directory in this fixture, so it is reported as excluded --
    # with a reason. What must never happen is silence.
    assert row["included"] is False and row["reason"]


def test_physics_curves_state_when_no_baseline_exists(cfg, tmp_path):
    curves = demo13.physics_curves(cfg, [], tmp_path, baseline=None)
    row = next(r for r in curves["curve_provenance"] if r["role"] == "baseline")
    assert row["included"] is False
    assert "no Demo 11 abrupt reference" in row["reason"]


# ---------------------------------------------------------------------------
# Phase 7 -- validation metadata says what actually happened
# ---------------------------------------------------------------------------


_PLAN = {"num_initial_trials": 6, "num_iterations": 10, "batch_size": 1,
         "remaining_new_solver_runs": 0}


def test_reanalysis_of_licensed_trials_reports_licensed_completion():
    """The work-laptop case, which the home laptop cannot run end to end.

    Sixteen completed non-synthetic trials reloaded in analyze mode: licensed
    execution is behind this run even though nothing was launched.
    """

    records = [
        {"trial_index": i, "status": "completed", "trial_valid": True}
        for i in range(16)
    ]
    lifecycle = demo13.validation_lifecycle(
        records=records,
        plan_record=_PLAN,
        mode="analyze_existing_results",
        # Reloaded records make every CaseResult look solver-successful.
        solver_ran_this_process=True,
        model_available=True,
        validation={"enabled": False, "solver_ran": False},
        dependency_report={"all_dependencies_physically_validated": False},
    )
    assert lifecycle["licensed_execution_completed"] is True
    assert lifecycle["licensed_trials_completed"] == 16
    assert lifecycle["licensed_trials_expected"] == 16
    assert lifecycle["solver_invoked_by_this_run"] is False
    assert lifecycle["reporting_completed"] is True
    assert lifecycle["stage5_physical_validation_completed"] is False
    assert lifecycle["state"] == "licensed_optimization_completed_validation_pending"


def test_synthetic_trials_never_count_as_licensed_execution():
    records = [
        {"trial_index": i, "status": "completed", "synthetic": True} for i in range(16)
    ]
    lifecycle = demo13.validation_lifecycle(
        records=records,
        plan_record=_PLAN,
        mode="synthetic_smoke_test",
        solver_ran_this_process=True,
        model_available=True,
        validation={},
        dependency_report=None,
    )
    assert lifecycle["licensed_execution_completed"] is False
    assert lifecycle["licensed_trials_completed"] == 0
    assert lifecycle["synthetic_trials_completed"] == 16
    assert lifecycle["state"] == "implemented_dry_run"


def test_stage5_completion_is_the_only_route_to_physically_validated():
    records = [{"trial_index": 0, "status": "completed"}]
    lifecycle = demo13.validation_lifecycle(
        records=records,
        plan_record=_PLAN,
        mode="validate_top_designs",
        solver_ran_this_process=True,
        model_available=True,
        validation={"enabled": True, "solver_ran": True},
        dependency_report=None,
    )
    assert lifecycle["state"] == "physically_validated"


def test_registry_status_reflects_licensed_completion_but_not_validation():
    import registry

    record = registry.load_registry().record("13_ax_bayesian_optimization_graded_acqw")
    assert record.status == "licensed_optimization_completed_validation_pending"
    assert record.status in registry.SOLVER_TRUSTED
    assert record.status not in registry.PHYSICALLY_TRUSTED
    assert record.physically_validated is False
    assert record.solver_exercised is True


def test_registry_pending_checks_still_demand_stage_five():
    import registry

    record = registry.load_registry().record("13_ax_bayesian_optimization_graded_acqw")
    text = " ".join(record.pending_licensed_checks).lower()
    assert "stage 5" in text
    assert record.pending_licensed_checks, "validation must remain owed"


def test_demo_yaml_points_at_the_completed_experiment_in_analysis_mode(cfg):
    workflow = cfg["workflow"]
    assert workflow["mode"] == "analyze_existing_results"
    assert workflow["experiment_state_dir"] == "demo13_ax_experiment_v2"


# ---------------------------------------------------------------------------
# Stage 5 preparation — perturbations must stay perturbations
# ---------------------------------------------------------------------------


def _abrupt_design(barrier=0.5, grading=0.0):
    return {
        "trial_index": 12,
        "parameter_asymmetry_s": 0.4603,
        "parameter_central_barrier_thickness_nm": barrier,
        "parameter_grading_thickness_nm": grading,
        "parameter_grading_profile": "abrupt" if not grading else "linear",
        "parameters": {"interface_mode": "abrupt" if not grading else "graded"},
        "canonical_parameters": {
            "grading_thickness_nm": grading,
            "grading_profile": "abrupt" if not grading else "linear",
        },
    }


def test_grading_perturbation_never_turns_an_abrupt_design_graded(cfg):
    """Adding a grade to an abrupt design changes the device, not a tolerance."""

    cases = demo13.robustness_cases(cfg, _abrupt_design())
    assert cases, "other perturbations must still be planned"
    assert not [case for case in cases if case[1] == "grading_thickness_nm"]


def test_grading_perturbation_still_applies_to_a_genuinely_graded_design(cfg):
    cases = demo13.robustness_cases(cfg, _abrupt_design(barrier=1.8, grading=1.0))
    grading = [case for case in cases if case[1] == "grading_thickness_nm"]
    assert grading, "a design with a real grade must still be perturbed in it"


def test_perturbation_fraction_exposes_the_thin_barrier_sensitivity(cfg):
    """A 0.2 nm tolerance is 40 % of a 0.5 nm barrier and 3 % of a 7 nm well."""

    design = _abrupt_design(barrier=0.5)
    barrier = demo13.perturbation_fraction(cfg, design, "central_barrier_nm", 0.2)
    well = demo13.perturbation_fraction(cfg, design, "wide_well_nm", 0.2)
    assert barrier == pytest.approx(0.4)
    assert well is not None and well < 0.05
    assert barrier > 8 * well
