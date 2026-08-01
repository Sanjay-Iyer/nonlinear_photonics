"""Ax feasibility regression tests for Demo 13; no nextnano executable is used.

These tests encode the diagnosis of the 2026-07-31 licensed run, in which
BoTorch reported ``When all training points are infeasible`` on every
model-based iteration -- starting at the seventh trial, which is exactly when
the first genuinely feasible design appeared.

The replay below uses that run's own metric values.  It is the executable form
of ``AX_FEASIBILITY_ANALYSIS.md``: if someone re-adds a constant 0/1 flag to the
Ax constraint set, ``test_constant_flag_constraints_make_every_point_infeasible``
fails and says why.
"""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import warnings

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "nextnano" / "demos" / "13_ax_bayesian_optimization_graded_acqw"
SHARED = DEMO.parent / "_shared"
for path in (str(DEMO), str(SHARED)):
    if path not in sys.path:
        sys.path.insert(0, path)

import axsearch13  # noqa: E402
import demo_workflow  # noqa: E402
import feasibility13  # noqa: E402
import metrics13  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")

#: The completed trials of the 2026-07-31 licensed run, as recorded.
#: (trial, asymmetry, barrier_nm, relative chi2 at target, signed detuning nm,
#:  boundary probability, tracking confidence, physical_qc_valid)
LICENSED_RUN = [
    (0, 0.530834, 1.492930, 0.5613, -46.0, 2e-5, 0.99, 1),
    (1, 0.459974, 2.310718, 0.2164, -40.0, 2e-5, 0.99, 1),
    (2, 0.484148, 0.960144, 0.8102, -28.0, 2e-5, 0.99, 1),
    (3, 0.406645, 1.767340, 0.4893, -40.0, 2e-5, 0.99, 1),
    (5, 0.382883, 1.247482, 0.1292, -16.0, 2e-5, 0.99, 1),
    (6, 0.557136, 1.519931, 0.5332, -41.0, 4e-3, 0.99, 0),
    (7, 0.366793, 0.874098, 0.1059, 3.0, 2e-5, 0.99, 1),
    (8, 0.388011, 0.816067, 0.4332, -13.0, 2e-5, 0.99, 1),
    (9, 0.394081, 0.645657, 0.5544, -10.0, 2e-5, 0.99, 1),
]


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


def _records(cfg, upto: int | None = None) -> list[dict]:
    rows = []
    for (index, asym, barrier, chi2, detuning, boundary, confidence, physical) in (
        LICENSED_RUN[:upto] if upto else LICENSED_RUN
    ):
        rows.append(
            {
                "trial_index": index,
                "iteration": 0 if index <= 6 else index - 6,
                "status": "completed",
                "relative_chi2_at_target_wavelength_abs": chi2,
                "signed_detuning_nm": detuning,
                "absolute_detuning_nm": abs(detuning),
                "peak_wavelength_nm": 1550.0 + detuning,
                "maximum_boundary_probability": boundary,
                "state_tracking_confidence": confidence,
                "orthonormality_error": 3e-7,
                "origin_independence_valid": 1,
                "required_states_valid": 1,
                "physical_qc_valid": physical,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# signed versus absolute detuning
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "peak_nm,signed,absolute,passes",
    [
        (1537.0, -13.0, 13.0, True),
        (1522.0, -28.0, 28.0, False),
        (1553.0, 3.0, 3.0, True),
        (1565.0, 15.0, 15.0, True),   # exactly on the bound
        (1566.0, 16.0, 16.0, False),
        (1504.0, -46.0, 46.0, False),
    ],
)
def test_signed_and_absolute_detuning_are_separate_metrics(
    cfg, peak_nm, signed, absolute, passes
):
    """A design 13 nm red of target is as close as one 13 nm blue of it."""

    record = metrics13.build_record(
        parameters={
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 0.0,
            "grading_profile": "abrupt",
        },
        cfg=cfg,
        observables={
            "chi2_peak_wavelength_nm": peak_nm,
            "chi2_relative_at_reference": 0.5,
            "chi2_peak_magnitude": 1.0,
        },
        validation={},
        status="completed",
    )
    assert record["signed_detuning_nm"] == pytest.approx(signed)
    assert record["absolute_detuning_nm"] == pytest.approx(absolute)
    spec = next(
        item
        for item in feasibility13.build_constraints(cfg)
        if item.name == "maximum_detuning_nm"
    )
    assert spec.metric == "absolute_detuning_nm"
    assert spec.satisfied_by(record["absolute_detuning_nm"]) is passes


def test_detuning_side_is_reported_but_never_constrained(cfg):
    # A peak at a SHORTER wavelength than the target is blue-shifted. This test
    # previously asserted the inverse and so encoded the bug: every v3 trial
    # peaked short of 1550 nm and was labelled `red_of_target`.
    for peak_nm, side in ((1537.0, "blue_of_target"), (1563.0, "red_of_target"),
                          (1550.0, "on_target")):
        record = metrics13.build_record(
            parameters={"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.5,
                        "grading_thickness_nm": 0.0, "grading_profile": "abrupt"},
            cfg=cfg,
            observables={"chi2_peak_wavelength_nm": peak_nm,
                         "chi2_relative_at_reference": 0.5, "chi2_peak_magnitude": 1.0},
            validation={},
            status="completed",
        )
        assert record["detuning_side"] == side
    constrained = {spec.metric for spec in feasibility13.build_constraints(cfg)}
    assert "signed_detuning_nm" not in constrained


# ---------------------------------------------------------------------------
# the reproduction
# ---------------------------------------------------------------------------


def _ax_client(cfg, constraint_metrics, records):
    """A minimal Ax client fed the licensed run's observations."""

    from ax.api.client import Client
    from ax.api.configs import RangeParameterConfig

    client = Client(random_seed=17)
    client.configure_experiment(
        name="feasibility_replay",
        parameters=[
            RangeParameterConfig(name="asymmetry_s", bounds=(0.36, 0.56), parameter_type="float"),
            RangeParameterConfig(name="central_barrier_thickness_nm", bounds=(0.5, 2.5),
                                 parameter_type="float"),
        ],
    )
    all_specs = {spec.metric: spec for spec in feasibility13.build_constraints(cfg)}
    client.configure_optimization(
        objective="relative_chi2_at_target_wavelength_abs",
        outcome_constraints=[all_specs[name].ax_string for name in constraint_metrics],
    )
    client.configure_generation_strategy(
        initialization_budget=1, initialize_with_center=False,
        use_existing_trials_for_initialization=True,
    )
    for row, (_i, asym, barrier, *_rest) in zip(records, LICENSED_RUN):
        index = client.attach_trial(
            parameters={"asymmetry_s": asym, "central_barrier_thickness_nm": barrier}
        )
        raw = {"relative_chi2_at_target_wavelength_abs": row["relative_chi2_at_target_wavelength_abs"]}
        raw.update({name: float(row[name]) for name in constraint_metrics})
        client.complete_trial(index, raw_data=raw)
    return client


def _all_infeasible(client) -> bool:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.get_next_trials(max_trials=1)
    return any("infeasible" in str(item.message).lower() for item in caught)


ALL_METRICS = [
    "absolute_detuning_nm", "maximum_boundary_probability", "state_tracking_confidence",
    "orthonormality_error", "origin_independence_valid", "required_states_valid",
    "physical_qc_valid",
]
CONTINUOUS = ["absolute_detuning_nm", "maximum_boundary_probability", "state_tracking_confidence"]
CONSTANT_OR_BINARY = [
    "orthonormality_error", "origin_independence_valid", "required_states_valid",
    "physical_qc_valid",
]


@pytest.mark.slow
@pytest.mark.parametrize("metric", CONSTANT_OR_BINARY)
def test_constant_flag_constraints_make_every_point_infeasible(cfg, metric):
    """Each of these, alone, reproduces the licensed run's warning."""

    assert _all_infeasible(_ax_client(cfg, [metric], _records(cfg))) is True


@pytest.mark.slow
@pytest.mark.parametrize("metric", CONTINUOUS)
def test_continuous_constraints_do_not_make_every_point_infeasible(cfg, metric):
    assert _all_infeasible(_ax_client(cfg, [metric], _records(cfg))) is False


@pytest.mark.slow
def test_the_shipped_constraint_set_never_reports_all_points_infeasible(cfg):
    """The whole point of the fix, on the data that exposed the bug."""

    modelled = [
        spec.metric
        for spec in feasibility13.modelled_constraints(feasibility13.build_constraints(cfg))
    ]
    assert set(modelled) == set(CONTINUOUS)
    for upto in (6, 7, 8, 9):
        client = _ax_client(cfg, modelled, _records(cfg, upto))
        assert _all_infeasible(client) is False, f"regressed at {upto} observations"


@pytest.mark.slow
def test_feasible_observation_is_recognized_as_soon_as_it_appears(cfg):
    """Section 11: the seventh trial is feasible and must be seen immediately."""

    specs = feasibility13.modelled_constraints(feasibility13.build_constraints(cfg))
    metrics = [spec.metric for spec in specs]
    six = feasibility13.feasibility_summary(_records(cfg, 6), specs)
    assert six["any_feasible"] is False
    assert six["initial_design_all_infeasible"] is True
    seven = feasibility13.feasibility_summary(_records(cfg, 7), specs)
    assert seven["any_feasible"] is True
    assert seven["first_feasible_trial"] == 7
    client = _ax_client(cfg, metrics, _records(cfg, 7))
    assert _all_infeasible(client) is False
    best, _metrics, trial_index, _arm = client.get_best_parameterization(
        use_model_predictions=False
    )
    assert trial_index is not None


# ---------------------------------------------------------------------------
# constraint-set selection
# ---------------------------------------------------------------------------


def test_binary_flags_are_enforced_but_never_modelled(cfg):
    specs = feasibility13.build_constraints(cfg)
    by_metric = {spec.metric: spec for spec in specs}
    for metric in ("physical_qc_valid", "required_states_valid", "origin_independence_valid"):
        assert by_metric[metric].enforcement == feasibility13.ENFORCEMENT_POST
        assert by_metric[metric].is_binary_flag is True
    for metric in CONTINUOUS:
        assert by_metric[metric].enforcement == feasibility13.ENFORCEMENT_AX


def test_never_model_list_moves_a_constraint_out_of_the_surrogate(cfg):
    assert (
        next(s for s in feasibility13.build_constraints(cfg)
             if s.metric == "orthonormality_error").enforcement
        == feasibility13.ENFORCEMENT_POST
    )
    variant = copy.deepcopy(cfg)
    variant["bo"]["outcome_modelling"]["never_model"] = []
    variant["bo"]["outcome_modelling"]["always_model"] = ["orthonormality_error"]
    assert (
        next(s for s in feasibility13.build_constraints(variant)
             if s.metric == "orthonormality_error").enforcement
        == feasibility13.ENFORCEMENT_AX
    )


def test_spread_diagnostic_flags_an_unresolvable_modelled_constraint(cfg):
    """The check that would have caught this on the first run."""

    variant = copy.deepcopy(cfg)
    variant["bo"]["outcome_modelling"]["never_model"] = []
    variant["bo"]["outcome_modelling"]["always_model"] = ["orthonormality_error"]
    specs = feasibility13.build_constraints(variant)
    spread = feasibility13.constraint_spread(_records(cfg), specs)
    unresolvable = feasibility13.unresolvable_modelled_constraints(spread)
    assert "maximum_orthonormality_error" in unresolvable
    row = next(r for r in spread if r["metric"] == "orthonormality_error")
    assert row["resolvable_by_surrogate"] is False
    assert "every observation infeasible" in row["diagnosis"]
    # The shipped configuration has no unresolvable modelled constraint.
    assert not feasibility13.unresolvable_modelled_constraints(
        feasibility13.constraint_spread(_records(cfg), feasibility13.build_constraints(cfg))
    )


def test_audit_reconstructs_every_constraint_for_every_trial(cfg):
    specs = feasibility13.build_constraints(cfg)
    rows = feasibility13.audit_rows(_records(cfg), specs)
    assert len(rows) == len(LICENSED_RUN) * len(specs)
    required = {
        "trial_index", "constraint", "ax_metric_name", "source_field",
        "raw_metric_value", "submitted_to_ax_value", "ax_value_type",
        "constraint_operator", "constraint_threshold", "constraint_passed",
        "value_is_finite", "trial_feasible_all_constraints",
        "trial_feasible_ax_constraints_only", "given_to_ax",
    }
    assert required <= set(rows[0])
    # Trial 2 sits 28 nm off target: infeasible on detuning, nothing else.
    trial2 = [row for row in rows if row["trial_index"] == 2]
    failed = {row["constraint"] for row in trial2 if row["constraint_passed"] is False}
    assert failed == {"maximum_detuning_nm"}
    assert all(row["trial_feasible_all_constraints"] is False for row in trial2)
    # Trial 8 is 13 nm off target and passes everything.
    trial8 = [row for row in rows if row["trial_index"] == 8]
    assert all(row["constraint_passed"] is True for row in trial8)
    assert all(row["trial_feasible_all_constraints"] is True for row in trial8)
    # Only the modelled constraints carry a submitted value.
    for row in rows:
        if row["given_to_ax"]:
            assert row["submitted_to_ax_value"] is not None
        else:
            assert row["ax_value_type"] == "not submitted"


def test_audit_identifies_trial_6_as_a_boundary_probability_rejection(cfg):
    specs = feasibility13.build_constraints(cfg)
    rows = [row for row in feasibility13.audit_rows(_records(cfg), specs)
            if row["trial_index"] == 6]
    failed = {row["constraint"] for row in rows if row["constraint_passed"] is False}
    assert "maximum_boundary_probability" in failed
    assert "require_physical_qc" in failed


# ---------------------------------------------------------------------------
# the bound-state policy
# ---------------------------------------------------------------------------


def _trial6_record(cfg, policy, *, continuous_bound: float | None = None,
                   peak_nm: float = 1509.0):
    """Trial 6's observables, with the bound-state policy under test.

    ``continuous_bound`` loosens the *continuous* boundary-probability
    constraint so the policy's own effect can be seen in isolation. With the
    shipped configuration the two share a threshold, so a design that fails the
    bound-state QC test also fails the continuous constraint and is invalid
    whatever the policy says -- which is itself worth knowing, and is why
    ``constraint`` is the honest alternative default.
    """

    variant = copy.deepcopy(cfg)
    variant.setdefault("physical_qc", {})["bound_state_policy"] = policy
    if continuous_bound is not None:
        variant["bo"]["outcome_constraints"]["maximum_boundary_probability"] = continuous_bound
    observables = {
        "chi2_peak_wavelength_nm": peak_nm,
        "chi2_relative_at_reference": 0.5332,
        "chi2_peak_magnitude": 1.2419,
        "maximum_boundary_probability_bound_states": 4e-3,
        "orthonormality_error_electron": 3e-7,
        "orthonormality_error_heavy_hole": 3e-7,
        "electron_energies_eV": [0.10, 0.16, 0.30, 0.45],
        "heavy_hole_energies_eV": [-0.02, -0.05, -0.09, -0.13],
    }
    validation = {
        "job_done_file_present": True, "no_stale_job_running_file": True,
        "probability_normalized": True, "envelopes_orthonormal": True,
        "electron_energies_ordered": True, "two_bound_electron_states": True,
        "bound_state_boundary_probability_small": False,  # the trial 6 failure
        "chi2_states_pass_bound_criterion": True, "chi2_origin_independent": True,
        "chi2_state_window_as_configured": True,
    }
    return metrics13.build_record(
        parameters={"asymmetry_s": 0.557136, "central_barrier_thickness_nm": 1.519931,
                    "grading_thickness_nm": 0.0, "grading_profile": "abrupt"},
        cfg=variant, observables=observables, validation=validation, status="completed",
        tracking={"state_tracking_confidence": 0.99, "assignment_margin": 0.5},
    )


def test_bound_state_qc_and_the_continuous_constraint_share_a_threshold(cfg):
    """With the shipped bounds the two agree, so no policy can rescue trial 6."""

    for policy in ("warn", "constraint"):
        record = _trial6_record(cfg, policy)
        assert record["trial_outcome_class"] == metrics13.OUTCOME_INVALID
        assert "maximum_boundary_probability" in record["constraint_violations"]


def test_warn_policy_keeps_the_warning_visible_and_is_not_a_clean_pass(cfg):
    record = _trial6_record(cfg, "warn", continuous_bound=1e-2, peak_nm=1552.0)
    assert record["trial_outcome_class"] == metrics13.OUTCOME_VALID_WITH_WARNING
    assert "bound_state_boundary_probability_small" in record["qc_warnings"]
    # The named failing test stays visible; it is never reported as passing.
    assert "bound_state_boundary_probability_small" in record["physical_qc_failed_tests"]
    assert record["physical_qc_valid"] == 0
    assert record["objective_available"] is True


def test_reject_policy_makes_the_trial_scientifically_invalid(cfg):
    record = _trial6_record(cfg, "reject", continuous_bound=1e-2, peak_nm=1552.0)
    assert record["trial_outcome_class"] == metrics13.OUTCOME_INVALID
    assert record["trial_valid"] is False
    # Metrics survive the rejection.
    assert record["relative_chi2_at_target_wavelength_abs"] == pytest.approx(0.5332)


def test_fail_trial_policy_withholds_the_objective(cfg):
    record = _trial6_record(cfg, "fail_trial", continuous_bound=1e-2, peak_nm=1552.0)
    assert record["trial_outcome_class"] == metrics13.OUTCOME_MECHANICAL_FAILURE
    assert record["objective_available"] is False
    assert metrics13.ax_raw_data(record, ("relative_chi2_at_target_wavelength_abs",)) is None


def test_constraint_policy_defers_to_the_continuous_bound(cfg):
    record = _trial6_record(cfg, "constraint")
    # The continuous boundary-probability constraint still rejects it, and it is
    # the only voice doing so.
    assert "maximum_boundary_probability" in record["constraint_violations"]
    assert "require_physical_qc" not in record["constraint_violations"]


def test_unknown_bound_state_policy_is_refused(cfg):
    with pytest.raises(demo_workflow.DemoError):
        _trial6_record(cfg, "ignore_it")


def test_every_outcome_class_is_from_the_declared_vocabulary(cfg):
    for policy in metrics13.BOUND_STATE_POLICIES:
        record = _trial6_record(cfg, policy, continuous_bound=1e-2, peak_nm=1552.0)
        assert record["trial_outcome_class"] in metrics13.TRIAL_OUTCOME_CLASSES


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------


def test_relative_metrics_are_never_labelled_pm_per_volt(cfg):
    import plots13
    import tables13

    for metric in ("relative_chi2_at_target_wavelength_abs", "relative_peak_chi2_abs",
                   "relative_integrated_chi2_abs"):
        assert "pm/V" not in tables13.unit_for(metric)
        assert "a.u." in tables13.unit_for(metric)
    for label in plots13.AXIS.values():
        assert "pm/V" not in label
    assert str((cfg.get("metric") or {}).get("mode")) == "relative"


def test_metric_names_carry_the_relative_prefix(cfg):
    """Naming them chi2_* invited the reading the units string denies."""

    assert "relative_chi2_at_target_wavelength_abs" in axsearch13.OPTIMIZABLE_METRICS
    assert "chi2_at_target_wavelength_abs" not in axsearch13.OPTIMIZABLE_METRICS
    assert axsearch13.RENAMED_METRICS["chi2_at_target_wavelength_abs"] == (
        "relative_chi2_at_target_wavelength_abs"
    )
