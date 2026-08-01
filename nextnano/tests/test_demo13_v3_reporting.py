"""Rejection history, iteration semantics, grading provenance and surrogate grids.

Pinned against the real v3 campaign: seven refused sub-resolution graded
proposals, ten completed model-based evaluations, five genuinely graded trials
(erf 3, sigmoid 1, cosine 1, linear 0) of which none was feasible, and eleven
realized-abrupt trials.
"""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "nextnano" / "demos" / "13_ax_bayesian_optimization_graded_acqw"
SHARED = DEMO.parent / "_shared"
DEMO11 = DEMO.parent / "11_paper_validation_interband_chi2_acqw"
DEMO12 = DEMO.parent / "12_graded_interface_coupled_quantum_well_optimization"
for path in (str(DEMO), str(SHARED), str(DEMO11), str(DEMO12)):
    if path not in sys.path:
        sys.path.insert(0, path)

import accounting13  # noqa: E402
import axsearch13  # noqa: E402
import demo13  # noqa: E402
import demo_workflow  # noqa: E402
import design13  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


@pytest.fixture(scope="module")
def interval_cfg(cfg):
    variant = copy.deepcopy(cfg)
    variant["bo"]["search_space"]["grading_fraction_spans_feasible_interval"] = True
    return variant


def _rejected_graded(index, fraction, maximum, profile, iteration):
    return {
        "trial_index": index,
        "candidate_id": f"t{index:04d}",
        "status": "rejected",
        "generation_method": "MBM",
        "iteration": iteration,
        "solver_launched": False,
        "trial_valid": False,
        "rejection_reason": (
            f"{axsearch13.REJECT_SUBRESOLUTION}: realized "
            f"{fraction * maximum:.2f} nm below 0.8 nm"
        ),
        "duplicate_of_trial": None,
        "proposed_grading_fraction": fraction,
        "maximum_feasible_grading_thickness_nm": maximum,
        "realized_grading_thickness_nm": 0.0,
        "parameters": {
            "asymmetry_s": 0.43,
            "central_barrier_thickness_nm": 1.25,
            "interface_mode": "graded",
            "grading_fraction_of_feasible_max": fraction,
            "grading_profile": profile,
        },
        # Canonicalization has already turned this into an abrupt 0 nm design.
        "canonical_parameters": {
            "grading_thickness_nm": 0.0,
            "grading_profile": "abrupt",
            "_proposed_grading_fraction": fraction,
            "_maximum_feasible_grading_nm": maximum,
        },
        "parameter_grading_thickness_nm": 0.0,
        "parameter_grading_profile": "abrupt",
    }


def _completed(index, method, valid, iteration, profile="abrupt", grading=0.0):
    graded = grading > 0
    return {
        "trial_index": index,
        "candidate_id": f"t{index:04d}",
        "status": "completed",
        "generation_method": method,
        "iteration": iteration,
        "solver_launched": True,
        "trial_valid": valid,
        "parameters": {
            "asymmetry_s": 0.4,
            "central_barrier_thickness_nm": 1.3,
            "interface_mode": "graded" if graded else "abrupt",
            **({"grading_profile": profile} if graded else {}),
        },
        "canonical_parameters": {
            "grading_thickness_nm": grading,
            "grading_profile": profile if graded else "abrupt",
        },
        "parameter_grading_thickness_nm": grading,
        "parameter_grading_profile": profile if graded else "abrupt",
    }


@pytest.fixture
def v3_records():
    """The real v3 pattern, including which profiles were refused."""

    records = [_rejected_graded(0, 0.4398, 1.569, "linear", 1)]
    records += [
        _completed(i, "Sobol", i == 5, i,
                   profile={3: "sigmoid", 4: "cosine"}.get(i, "abrupt"),
                   grading={3: 1.27, 4: 1.70}.get(i, 0.0))
        for i in (1, 2, 3, 4, 5, 6)
    ]
    records += [
        _completed(7, "MBM", False, 2),
        _completed(8, "MBM", False, 3, profile="erf", grading=1.23),
        _completed(9, "MBM", False, 4),
        _rejected_graded(10, 0.5443, 1.296, "erf", 5),
        _completed(11, "MBM", False, 6, profile="erf", grading=1.09),
    ]
    records += [
        _rejected_graded(i, f, m, "erf", it)
        for i, f, m, it in (
            (12, 0.4370, 1.156, 7), (13, 0.3802, 1.166, 8), (14, 0.3581, 1.410, 9),
            (15, 0.6278, 1.005, 10), (16, 0.5599, 1.327, 11),
        )
    ]
    records += [
        _completed(17, "MBM", True, 12),
        _completed(18, "MBM", False, 13),
        _completed(19, "MBM", False, 14, profile="erf", grading=0.86),
        _completed(20, "MBM", False, 15),
        _completed(21, "MBM", True, 16),
        _completed(22, "MBM", False, 17),
    ]
    return sorted(records, key=lambda r: r["trial_index"])


# ---------------------------------------------------------------------------
# Phase 3 -- rejection history
# ---------------------------------------------------------------------------


def test_rejection_history_is_rebuilt_from_the_ledger(v3_records, cfg):
    """It used to come from loop state, so reanalysis produced an empty table."""

    rows = accounting13.rejection_history(v3_records, cfg)
    assert len(rows) == 7
    assert [r["trial_index"] for r in rows] == [0, 10, 12, 13, 14, 15, 16]


def test_every_required_rejection_field_is_present_and_populated(v3_records, cfg):
    rows = accounting13.rejection_history(v3_records, cfg)
    required = (
        "proposal_attempt_index", "requested_bo_iteration", "trial_index",
        "candidate_id", "proposed_interface_mode", "proposed_grading_fraction",
        "proposed_grading_thickness_nm_unsnapped", "maximum_feasible_grading_nm",
        "minimum_required_grading_nm", "realized_grading_thickness_nm_before_collapse",
        "rejection_reason", "rejection_category", "solver_launched",
        "replacement_trial_index", "consumed_bo_budget",
    )
    for row in rows:
        for field in required:
            assert field in row, field
            assert row[field] is not None, f"{field} is empty on t{row['trial_index']}"


def test_rejection_history_reports_the_proposed_not_the_canonicalized_design(
    v3_records, cfg
):
    """The defect: `parameter_*` say abrupt/0 nm for a refused graded proposal."""

    rows = accounting13.rejection_history(v3_records, cfg)
    for row in rows:
        assert row["proposed_interface_mode"] == "graded"
        assert row["proposed_grading_profile"] in {"linear", "erf"}
        assert row["proposed_grading_thickness_nm_unsnapped"] > 0
        assert row["solver_launched"] is False
        assert row["consumed_bo_budget"] is False
    assert sum(1 for r in rows if r["proposed_grading_profile"] == "erf") == 6


def test_rejection_history_names_the_replacement_that_ran(v3_records, cfg):
    rows = accounting13.rejection_history(v3_records, cfg)
    by_index = {r["trial_index"]: r for r in rows}
    assert by_index[0]["replacement_trial_index"] == 1
    assert by_index[10]["replacement_trial_index"] == 11
    assert by_index[12]["replacement_trial_index"] == 17


# ---------------------------------------------------------------------------
# Phase 4 -- iteration semantics
# ---------------------------------------------------------------------------


def test_mbm_iterations_are_numbered_one_to_ten(v3_records):
    rows = accounting13.trial_iteration_mapping(v3_records)
    mbm = [r for r in rows if r["mbm_iteration_number"] is not None]
    assert [r["mbm_iteration_number"] for r in mbm] == list(range(1, 11))
    assert [r["trial_index"] for r in mbm] == [7, 8, 9, 11, 17, 18, 19, 20, 21, 22]


def test_the_recorded_iteration_field_is_not_the_bo_iteration(v3_records):
    """The ledger's `iteration` counts proposal attempts and reached 17."""

    rows = accounting13.trial_iteration_mapping(v3_records)
    last = next(r for r in rows if r["trial_index"] == 22)
    assert last["requested_bo_iteration_recorded"] == 17
    assert last["mbm_iteration_number"] == 10


def test_rejected_proposals_never_appear_in_iteration_plots(v3_records):
    rows = accounting13.trial_iteration_mapping(v3_records)
    for row in rows:
        if row["status"] == "rejected":
            assert row["appears_in_iteration_plots"] is False
            assert row["mbm_iteration_number"] is None


def test_rejections_do_not_shift_completed_numbering(v3_records):
    """Removing the refusals must not renumber the completed evaluations."""

    rows = accounting13.trial_iteration_mapping(v3_records)
    with_rejections = [
        (r["trial_index"], r["mbm_iteration_number"])
        for r in rows if r["mbm_iteration_number"]
    ]
    without = accounting13.trial_iteration_mapping(
        [r for r in v3_records if r["status"] != "rejected"]
    )
    assert with_rejections == [
        (r["trial_index"], r["mbm_iteration_number"])
        for r in without if r["mbm_iteration_number"]
    ]


def test_sobol_evaluations_are_numbered_separately(v3_records):
    rows = accounting13.trial_iteration_mapping(v3_records)
    sobol = [r for r in rows if r["sobol_evaluation_number"] is not None]
    assert [r["sobol_evaluation_number"] for r in sobol] == [1, 2, 3, 4, 5, 6]


# ---------------------------------------------------------------------------
# Phase 5 -- proposed versus realized
# ---------------------------------------------------------------------------


def test_refused_proposals_are_not_realized_abrupt_designs(v3_records, cfg):
    """The defect: seven graded proposals plotted as evaluated abrupt trials."""

    rows = accounting13.proposed_versus_realized_grading(v3_records, cfg)
    refused = [r for r in rows if r["was_rejected"]]
    assert len(refused) == 7
    for row in refused:
        assert row["proposed_interface_mode"] == "graded"
        assert row["realized_interface_mode"] == "not_realized"
        assert row["realized_grading_thickness_nm"] is None
        assert row["counts_as_profile_evidence"] is None
        assert row["is_genuinely_graded"] is False


def test_the_v3_grading_populations(v3_records, cfg):
    counts = accounting13.grading_population_counts(v3_records, cfg)
    assert counts["proposed_graded"] == 12
    assert counts["rejected_graded"] == 7
    assert counts["evaluated_genuine_graded"] == 5
    assert counts["evaluated_abrupt"] == 11
    assert counts["feasible_genuine_graded"] == 0
    assert counts["genuine_graded_per_profile"] == {"cosine": 1, "erf": 3, "sigmoid": 1}
    assert counts["evaluated_genuine_graded"] + counts["evaluated_abrupt"] == 16


def test_no_profile_ranking_is_supportable_from_v3(v3_records, cfg):
    counts = accounting13.grading_population_counts(v3_records, cfg)
    assert counts["profile_ranking_supportable"] is False
    assert "never a ranking" in counts["interpretation"]
    # linear was proposed but never built: it must not appear as evidence.
    assert "linear" not in counts["genuine_graded_per_profile"]


def test_no_graded_design_was_feasible(v3_records, cfg):
    """The scientific limit: grading cannot be judged from this campaign."""

    counts = accounting13.grading_population_counts(v3_records, cfg)
    assert counts["feasible_genuine_graded_per_profile"] == {}


# ---------------------------------------------------------------------------
# Phase 3 -- candidate generation valid by construction
# ---------------------------------------------------------------------------


def test_the_interval_mapping_makes_every_fraction_resolvable(interval_cfg):
    minimum = design13.minimum_resolvable_grading_nm(interval_cfg)
    for fraction in (0.35, 0.36, 0.5, 0.75, 1.0):
        for profile in ("linear", "sigmoid", "erf", "cosine"):
            verdict = axsearch13.preflight(
                {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.2,
                 "interface_mode": "graded",
                 "grading_fraction_of_feasible_max": fraction,
                 "grading_profile": profile},
                interval_cfg, {},
            )
            assert verdict["accepted"], (fraction, profile, verdict["rejection_reason"])
            assert verdict["realized_grading_thickness_nm"] >= minimum
            assert verdict["canonical"]["grading_profile"] == profile


def test_the_interval_mapping_still_refuses_a_geometry_with_no_room(interval_cfg):
    for barrier in (0.85, 0.88):
        verdict = axsearch13.preflight(
            {"asymmetry_s": 0.46, "central_barrier_thickness_nm": barrier,
             "interface_mode": "graded", "grading_fraction_of_feasible_max": 1.0,
             "grading_profile": "linear"},
            interval_cfg, {},
        )
        assert verdict["accepted"] is False
    ok = axsearch13.preflight(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 0.90,
         "interface_mode": "graded", "grading_fraction_of_feasible_max": 0.35,
         "grading_profile": "linear"},
        interval_cfg, {},
    )
    assert ok["accepted"] is True


def test_abrupt_is_proposable_at_the_thinnest_barrier_under_both_mappings(
    cfg, interval_cfg
):
    for variant in (cfg, interval_cfg):
        verdict = axsearch13.preflight(
            {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 0.85,
             "interface_mode": "abrupt"},
            variant, {},
        )
        assert verdict["accepted"] is True
        assert verdict["realized_grading_thickness_nm"] == 0.0


def test_the_default_mapping_still_refuses_every_v3_refusal(cfg):
    """v3's recorded observations must not be reinterpreted by this change."""

    for fraction, barrier, profile in (
        (0.4398, 1.5, "linear"), (0.5443, 1.4, "erf"), (0.4370, 1.256, "erf"),
        (0.3802, 1.266, "erf"), (0.3581, 1.51, "erf"), (0.6278, 1.105, "erf"),
        (0.5599, 1.427, "erf"),
    ):
        verdict = axsearch13.preflight(
            {"asymmetry_s": 0.43, "central_barrier_thickness_nm": barrier,
             "interface_mode": "graded",
             "grading_fraction_of_feasible_max": fraction,
             "grading_profile": profile},
            cfg, {},
        )
        assert verdict["accepted"] is False, (fraction, barrier, profile)


def test_the_mapping_is_part_of_the_experiment_schema(cfg, interval_cfg):
    """Two mappings give the same fraction two different meanings."""

    assert demo13.experiment_schema(cfg)["grading_fraction_spans_feasible_interval"] is False
    assert (
        demo13.experiment_schema(interval_cfg)["grading_fraction_spans_feasible_interval"]
        is True
    )


def test_a_snapshot_predating_a_schema_field_stays_loadable(cfg, tmp_path):
    """Adding an identity field must not invalidate every existing checkpoint."""

    import json

    state = tmp_path / "state"
    state.mkdir()
    stored = dict(demo13.experiment_schema(cfg))
    stored.pop("grading_fraction_spans_feasible_interval")
    (state / "experiment_schema.json").write_text(json.dumps(stored), encoding="utf-8")

    # The schema check is exercised directly: building a real Experiment would
    # need a loadable Ax snapshot, which is not what this test is about.
    stub = types.SimpleNamespace(
        schema_path=state / "experiment_schema.json", state_dir=state
    )
    # Compatible with the documented default...
    demo13.Experiment._check_schema_compatible(stub, cfg)
    # ...and incompatible with anything else.
    variant = copy.deepcopy(cfg)
    variant["bo"]["search_space"]["grading_fraction_spans_feasible_interval"] = True
    with pytest.raises(demo_workflow.DemoError, match="search space has changed"):
        demo13.Experiment._check_schema_compatible(stub, variant)


# ---------------------------------------------------------------------------
# Phase 6 -- surrogate grids
# ---------------------------------------------------------------------------


def test_a_subresolution_grid_point_is_unavailable_for_the_graded_branch(cfg):
    """350 of 625 v3 slice points were collapsed abrupt designs marked available."""

    verdict = demo13._branch_validity(
        cfg,
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.2,
         "interface_mode": "graded", "grading_fraction_of_feasible_max": 0.35,
         "grading_profile": "linear"},
    )
    assert verdict["requested_branch"] == "graded"
    assert verdict["branch_valid"] is False
    assert "below the 0.8 nm minimum" in verdict["branch_invalid_reason"]
    assert "abrupt" in verdict["branch_invalid_reason"]


def test_a_resolvable_grid_point_is_valid(cfg):
    verdict = demo13._branch_validity(
        cfg,
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 2.4,
         "interface_mode": "graded", "grading_fraction_of_feasible_max": 0.9,
         "grading_profile": "erf"},
    )
    assert verdict["branch_valid"] is True
    assert verdict["branch_invalid_reason"] == ""


def test_an_abrupt_grid_point_is_always_branch_valid(cfg):
    verdict = demo13._branch_validity(
        cfg, {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 0.9,
              "interface_mode": "abrupt"},
    )
    assert verdict["requested_branch"] == "abrupt"
    assert verdict["branch_valid"] is True


# ---------------------------------------------------------------------------
# Phase 7 -- acquisition and feasibility
# ---------------------------------------------------------------------------


def test_feasibility_probability_uses_the_correct_threshold_direction(cfg, tmp_path):
    """Reversing these would make the most infeasible region look best."""

    experiment = type("_E", (), {"cfg": cfg})()
    # Detuning is an upper bound at 15 nm: a mean far below it is nearly certain.
    good = demo13._feasibility_probabilities(experiment, {
        "absolute_detuning_nm_predicted_mean": 2.0,
        "absolute_detuning_nm_predicted_standard_error": 1.0,
    })
    bad = demo13._feasibility_probabilities(experiment, {
        "absolute_detuning_nm_predicted_mean": 40.0,
        "absolute_detuning_nm_predicted_standard_error": 1.0,
    })
    assert good["probability_satisfies_absolute_detuning_nm"] > 0.99
    assert bad["probability_satisfies_absolute_detuning_nm"] < 0.01

    # Tracking confidence is a LOWER bound at 0.8: high mean is good.
    high = demo13._feasibility_probabilities(experiment, {
        "state_tracking_confidence_predicted_mean": 0.99,
        "state_tracking_confidence_predicted_standard_error": 0.01,
    })
    low = demo13._feasibility_probabilities(experiment, {
        "state_tracking_confidence_predicted_mean": 0.50,
        "state_tracking_confidence_predicted_standard_error": 0.01,
    })
    assert high["probability_satisfies_state_tracking_confidence"] > 0.99
    assert low["probability_satisfies_state_tracking_confidence"] < 0.01


def test_binary_qc_flags_never_enter_the_feasibility_product(cfg):
    experiment = type("_E", (), {"cfg": cfg})()
    result = demo13._feasibility_probabilities(experiment, {
        "absolute_detuning_nm_predicted_mean": 5.0,
        "absolute_detuning_nm_predicted_standard_error": 1.0,
        "physical_qc_valid_predicted_mean": 1.0,
        "physical_qc_valid_predicted_standard_error": 0.1,
    })
    assert "probability_satisfies_physical_qc_valid" not in result


def test_no_modelled_posterior_gives_a_stated_absence(cfg):
    experiment = type("_E", (), {"cfg": cfg})()
    result = demo13._feasibility_probabilities(experiment, {})
    assert result["probability_of_feasibility"] is None
    assert result["feasibility_probability_note"]
