"""Accounting, rejection classification and iteration semantics for the v3 campaign.

Every count here is pinned against the **real** v3 ledger pattern: 23 proposals,
of which 7 were refused at preflight as sub-resolution grades and 16 completed
(6 Sobol, 10 model-based), 3 of them feasible.

Two of the defects these tests cover were regressions introduced by the previous
hardening pass, which added a new rejection reason without teaching the
accounting about it. The tests are therefore written against the *reason
constants* rather than against literal strings, so a future reason cannot slip
through the same gap.
"""

from __future__ import annotations

import copy
from pathlib import Path
import sys

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

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


def _completed(index, method, valid, profile="abrupt", grading=0.0):
    return {
        "trial_index": index,
        "status": "completed",
        "generation_method": method,
        "trial_valid": valid,
        "solver_launched": True,
        "parameters": {"interface_mode": "graded" if grading else "abrupt",
                       "grading_profile": profile},
        "canonical_parameters": {"grading_thickness_nm": grading,
                                 "grading_profile": profile if grading else "abrupt"},
    }


def _rejected(index, method, reason, duplicate_of=None):
    return {
        "trial_index": index,
        "status": "rejected",
        "generation_method": method,
        "trial_valid": False,
        "solver_launched": False,
        "rejection_reason": reason,
        "duplicate_of_trial": duplicate_of,
        "parameters": {"interface_mode": "graded", "grading_profile": "erf"},
        "canonical_parameters": {"grading_thickness_nm": 0.0,
                                 "grading_profile": "abrupt"},
    }


@pytest.fixture
def v3_records():
    """The actual v3 proposal pattern, trial indices and all."""

    sub = f"{axsearch13.REJECT_SUBRESOLUTION}: realized 0.38 nm below 0.8 nm"
    records = [_rejected(0, "Sobol", sub)]
    records += [_completed(i, "Sobol", i == 5) for i in (1, 2, 3, 4, 5, 6)]
    records += [_completed(i, "MBM", False) for i in (7, 8, 9, 11)]
    records += [_rejected(i, "MBM", sub) for i in (10, 12, 13, 14, 15, 16)]
    records += [_completed(i, "MBM", i in (17, 21)) for i in (17, 18, 19, 20, 21, 22)]
    return sorted(records, key=lambda r: r["trial_index"])


# ---------------------------------------------------------------------------
# the confirmed v3 numbers
# ---------------------------------------------------------------------------


def test_v3_accounting_matches_the_confirmed_campaign(v3_records, cfg):
    acc = accounting13.campaign_accounting(v3_records, cfg)
    assert acc["proposed_candidates"] == 23
    assert acc["preflight_rejected"] == 7
    assert acc["canonical_duplicates"] == 0
    assert acc["solver_completed"] == 16
    assert acc["solver_failed"] == 0
    assert acc["sobol_completed"] == 6
    assert acc["model_based_completed"] == 10
    assert acc["feasible_completed"] == 3
    assert acc["pending"] == 0
    assert acc["remaining_evaluations"] == 0
    assert acc["optimization_completed"] is True


def test_the_accounting_identity_is_checked_not_assumed(v3_records, cfg):
    acc = accounting13.campaign_accounting(v3_records, cfg)
    assert acc["accounting_identity_holds"] is True
    assert acc["rejection_identity_holds"] is True
    assert (
        acc["proposed_candidates"]
        == acc["rejected_total"] + acc["solver_completed"]
        + acc["solver_failed"] + acc["pending"]
    )


def test_v3_trial_indices_are_reported(v3_records, cfg):
    acc = accounting13.campaign_accounting(v3_records, cfg)
    assert acc["feasible_trial_indices"] == [5, 17, 21]
    assert acc["rejected_trial_indices"] == [0, 10, 12, 13, 14, 15, 16]
    assert acc["model_based_completed_trial_indices"] == [
        7, 8, 9, 11, 17, 18, 19, 20, 21, 22
    ]


def test_sobol_proposed_exceeds_sobol_completed(v3_records, cfg):
    """One Sobol proposal was refused; six became observations."""

    acc = accounting13.campaign_accounting(v3_records, cfg)
    assert acc["sobol_proposed"] == 7
    assert acc["sobol_completed"] == 6
    assert acc["model_based_proposed"] == 16
    assert acc["model_based_completed"] == 10


# ---------------------------------------------------------------------------
# rejection classification -- the regression that produced 0 and 0 beside 7
# ---------------------------------------------------------------------------


def test_a_subresolution_grade_is_not_a_duplicate(v3_records, cfg):
    rejected = [r for r in v3_records if r["status"] == "rejected"]
    for record in rejected:
        assert accounting13.rejection_category(record) == "subresolution_grade"
        assert accounting13.is_duplicate(record) is False
    acc = accounting13.campaign_accounting(v3_records, cfg)
    assert acc["rejections_by_category"] == {"subresolution_grade": 7}


def test_every_rejection_reason_constant_is_classified(cfg):
    """The gap that caused the regression: a reason nothing knew about."""

    for constant in (
        axsearch13.REJECT_DUPLICATE,
        axsearch13.REJECT_SUBRESOLUTION,
        axsearch13.REJECT_GEOMETRY,
        axsearch13.REJECT_UNRESOLVABLE,
    ):
        record = _rejected(0, "MBM", f"{constant}: because")
        assert accounting13.rejection_category(record) != "unclassified_rejection", (
            f"{constant} is not classified; add it to _REJECTION_CATEGORIES"
        )


def test_an_unknown_reason_is_named_not_silently_folded_in():
    record = _rejected(0, "MBM", "something_new: reason")
    assert accounting13.rejection_category(record) == "unclassified_rejection"
    assert accounting13.is_duplicate(record) is False


def test_a_duplicate_is_decided_by_its_reason_not_by_extra_provenance():
    """Requiring `duplicate_of_trial` too would under-count real duplicates."""

    with_trial = _rejected(3, "MBM", f"{axsearch13.REJECT_DUPLICATE}: same", duplicate_of=1)
    without = _rejected(3, "MBM", f"{axsearch13.REJECT_DUPLICATE}: same")
    assert accounting13.is_duplicate(with_trial) is True
    assert accounting13.is_duplicate(without) is True
    # But a sub-resolution refusal is never a duplicate, whatever else it carries.
    sub = _rejected(4, "MBM", f"{axsearch13.REJECT_SUBRESOLUTION}: too thin", duplicate_of=1)
    assert accounting13.is_duplicate(sub) is False


def test_preflight_categories_exclude_duplicates():
    assert "canonical_duplicate" not in accounting13.PREFLIGHT_CATEGORIES
    assert "subresolution_grade" in accounting13.PREFLIGHT_CATEGORIES


def test_budget_accounting_agrees_with_the_authoritative_counts(v3_records, cfg, tmp_path):
    """The legacy table must not be a second, disagreeing derivation."""

    ledger = axsearch13.Ledger(tmp_path)
    for record in v3_records:
        ledger.write(record)
    legacy = axsearch13.budget_accounting(cfg, ledger)
    acc = accounting13.campaign_accounting(v3_records, cfg)
    assert legacy["preflight_invalid_proposals"] == acc["preflight_rejected"] == 7
    assert legacy["duplicate_proposals"] == acc["canonical_duplicates"] == 0
    assert legacy["ax_completed_observations"] == acc["solver_completed"] == 16


# ---------------------------------------------------------------------------
# lifecycle wording
# ---------------------------------------------------------------------------


def test_a_subresolution_rejection_is_not_described_as_a_duplicate(v3_records):
    rejected = next(r for r in v3_records if r["status"] == "rejected")
    phrase = accounting13.lifecycle_phrase(rejected)
    assert "duplicate" not in phrase
    assert "mesh-resolvable minimum" in phrase
    assert "never simulated" in phrase
    # And demo13 must delegate rather than keep its own wording.
    assert demo13._lifecycle(rejected) == phrase


def test_a_real_duplicate_is_still_described_as_one():
    record = _rejected(4, "MBM", f"{axsearch13.REJECT_DUPLICATE}: same", duplicate_of=2)
    phrase = accounting13.lifecycle_phrase(record)
    assert "canonical duplicate" in phrase and "trial 2" in phrase


def test_completed_but_infeasible_says_so(v3_records):
    record = next(
        r for r in v3_records if r["status"] == "completed" and not r["trial_valid"]
    )
    assert "rejected by outcome constraints" in accounting13.lifecycle_phrase(record)


# ---------------------------------------------------------------------------
# lifecycle state feeds off the accounting, not a missing key
# ---------------------------------------------------------------------------


def test_optimization_completed_is_read_from_the_accounting(v3_records, cfg):
    """It used to read a key `plan()` never returned, so it was always False."""

    acc = accounting13.campaign_accounting(v3_records, cfg)
    lifecycle = demo13.validation_lifecycle(
        records=v3_records,
        plan_record={"num_initial_trials": 6, "num_iterations": 10, "batch_size": 1},
        mode="analyze_existing_results",
        solver_ran_this_process=True,
        model_available=True,
        validation={},
        dependency_report=None,
        accounting=acc,
    )
    assert lifecycle["optimization_completed"] is True
    assert lifecycle["remaining_evaluations"] == 0
    assert lifecycle["licensed_trials_completed"] == 16
    assert lifecycle["solver_invoked_by_this_run"] is False
    assert lifecycle["state"] == "licensed_optimization_completed_validation_pending"


def test_an_unfinished_campaign_still_reports_incomplete(cfg):
    partial = [_completed(i, "Sobol", False) for i in range(4)]
    acc = accounting13.campaign_accounting(partial, cfg)
    assert acc["optimization_completed"] is False
    assert acc["remaining_evaluations"] == 12
