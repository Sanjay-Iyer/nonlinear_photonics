"""Geometry feasibility, candidate regeneration and budget accounting.

No nextnano executable is used. The premium trials that motivated all three are
reproduced here from their recorded parameters.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "nextnano" / "demos" / "13_ax_bayesian_optimization_graded_acqw"
SHARED = DEMO.parent / "_shared"
DEMO12 = DEMO.parent / "12_graded_interface_coupled_quantum_well_optimization"
for path in (str(DEMO), str(SHARED), str(DEMO12)):
    if path not in sys.path:
        sys.path.insert(0, path)

import axsearch13  # noqa: E402
import demo_workflow  # noqa: E402
import design13  # noqa: E402
import geometry13  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")

#: The two premium proposals that reached the solver stage and should not have.
#: (trial, asymmetry, barrier_nm, requested grading_nm)
PREMIUM_INVALID = [
    (4, 0.503818, 2.058127, 2.268731),
    (12, 0.368472, 0.565246, 1.314021),
]


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


@pytest.fixture(scope="module")
def thickness_cfg(cfg):
    """The raw-thickness parameterization, for the cases that need it."""

    variant = copy.deepcopy(cfg)
    variant["bo"]["search_space"]["parameterization"] = "thickness"
    return variant


def _resolved(cfg, asymmetry, barrier, grading, profile="linear"):
    variant = copy.deepcopy(cfg)
    variant["bo"]["search_space"]["parameterization"] = "thickness"
    return design13.resolve_config(
        {
            "asymmetry_s": asymmetry,
            "central_barrier_thickness_nm": barrier,
            "grading_thickness_nm": grading,
            "grading_profile": profile if grading > 0 else "abrupt",
        },
        variant,
    )


# ---------------------------------------------------------------------------
# one authority
# ---------------------------------------------------------------------------


def test_location_interface_table_matches_demo12(cfg):
    """geometry13's per-mode table must equal what Demo 12 actually grades."""

    import demo12
    import grading12

    for mode in ("none", "all", "outer_only", "central_only", "left_only", "right_only"):
        variant = copy.deepcopy(cfg)
        variant["grading"]["location_mode"] = mode
        selected = tuple(
            interface.name
            for interface in grading12.select_interfaces(demo12.interfaces(variant), mode)
        )
        assert set(selected) == set(geometry13.graded_interfaces_for(mode)), mode


def test_design13_delegates_to_geometry13(cfg):
    """There must be exactly one implementation of geometric validity."""

    source = (DEMO / "design13.py").read_text(encoding="utf-8")
    assert "geometry13.evaluate" in source
    # The superseded local rule must be gone from the code, not just unused.
    assert "narrowest = min(" not in source
    assert "exceeds the narrowest adjacent" not in source


# ---------------------------------------------------------------------------
# the premium failures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("trial,asymmetry,barrier,grading", PREMIUM_INVALID)
def test_premium_invalid_geometries_are_rejected(thickness_cfg, trial, asymmetry, barrier, grading):
    """Trials 4 and 12 of the 2026-07-31 run: impossible, and now unproposable."""

    with pytest.raises(demo_workflow.DemoError) as failure:
        _resolved(thickness_cfg, asymmetry, barrier, grading)
    message = str(failure.value)
    assert "flat material" in message or "consume" in message


@pytest.mark.parametrize("trial,asymmetry,barrier,grading", PREMIUM_INVALID)
def test_premium_invalid_geometries_exceed_the_feasible_maximum(
    thickness_cfg, trial, asymmetry, barrier, grading
):
    probe = _resolved(thickness_cfg, asymmetry, barrier, 0.0)
    maximum, binding = geometry13.maximum_feasible_grading_nm(probe)
    assert grading > maximum
    assert binding == "centre_barrier"


def test_feasible_grading_just_below_the_maximum_is_accepted(thickness_cfg):
    probe = _resolved(thickness_cfg, 0.503818, 2.058127, 0.0)
    maximum, _binding = geometry13.maximum_feasible_grading_nm(probe)
    resolved = _resolved(thickness_cfg, 0.503818, 2.058127, maximum * 0.99)
    assert geometry13.evaluate(resolved).feasible is True


def test_the_maximum_itself_is_exactly_feasible(thickness_cfg):
    probe = _resolved(thickness_cfg, 0.46, 1.8, 0.0)
    maximum, _binding = geometry13.maximum_feasible_grading_nm(probe)
    verdict = geometry13.evaluate(probe, grading_thickness_nm=maximum)
    assert verdict.feasible is True
    # Comfortably past the bound, so mesh snapping cannot round it back inside.
    just_over = geometry13.evaluate(
        probe, grading_thickness_nm=maximum + 10 * geometry13.mesh_snap_nm(probe)
    )
    assert just_over.feasible is False


# ---------------------------------------------------------------------------
# the per-mode rule
# ---------------------------------------------------------------------------


def test_location_mode_changes_the_feasible_maximum(cfg):
    """The naive narrowest-layer rule is correct only for location_mode: all."""

    maxima = {}
    for mode in ("all", "outer_only", "central_only", "left_only", "right_only"):
        variant = copy.deepcopy(cfg)
        variant["grading"]["location_mode"] = mode
        variant["bo"]["search_space"]["parameterization"] = "thickness"
        probe = design13.resolve_config(
            {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
             "grading_thickness_nm": 0.0, "grading_profile": "abrupt"},
            variant,
        )
        maxima[mode], _b = geometry13.maximum_feasible_grading_nm(probe)
    # centre_barrier is 1.8 nm with 0.1 nm of flat material required.
    # `all` grades both its sides: 0.5g + 0.5g <= 1.7  ->  g <= 1.7
    assert maxima["all"] == pytest.approx(1.7)
    # `central_only` also grades both sides of the barrier, so same bound.
    assert maxima["central_only"] == pytest.approx(1.7)
    # `outer_only` does not grade the barrier at all; the wells bound it, and
    # each is cut once, so the narrow 2.7 nm well allows 2*(2.7-0.1) = 5.2 nm.
    assert maxima["outer_only"] > maxima["all"]
    # A single-sided cut always allows more than a double-sided one.
    assert maxima["outer_only"] == pytest.approx(2 * (2.7 - 0.1))


def test_two_grades_on_one_thin_layer_is_the_binding_case(cfg):
    variant = copy.deepcopy(cfg)
    variant["grading"]["location_mode"] = "all"
    variant["bo"]["search_space"]["parameterization"] = "thickness"
    probe = design13.resolve_config(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 0.6,
         "grading_thickness_nm": 0.0, "grading_profile": "abrupt"},
        variant,
    )
    verdict = geometry13.evaluate(probe, grading_thickness_nm=0.9)
    assert verdict.feasible is False
    barrier = next(b for b in verdict.budgets if b.layer == "centre_barrier")
    assert len(barrier.graded_interfaces) == 2
    assert barrier.consumed_nm == pytest.approx(0.9)
    assert barrier.remaining_flat_nm == pytest.approx(-0.3)


def test_minimum_flat_region_is_respected(cfg):
    variant = copy.deepcopy(cfg)
    variant["bo"]["search_space"]["parameterization"] = "thickness"
    variant["grading"]["minimum_flat_region_nm"] = 0.5
    probe = design13.resolve_config(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
         "grading_thickness_nm": 0.0, "grading_profile": "abrupt"},
        variant,
    )
    maximum, _b = geometry13.maximum_feasible_grading_nm(probe)
    assert maximum == pytest.approx(1.3)  # 1.8 - 0.5


def test_abrupt_designs_are_always_constructible(cfg):
    probe = _resolved(cfg, 0.56, 0.5, 0.0)
    verdict = geometry13.evaluate(probe)
    assert verdict.feasible is True
    assert verdict.realized_grading_nm == 0.0


def test_mesh_snapping_never_rounds_up_past_feasibility(cfg):
    assert geometry13.snap_to_mesh(1.2345, 0.01) == pytest.approx(1.23)
    assert geometry13.snap_to_mesh(1.7, 0.01) == pytest.approx(1.7)
    assert geometry13.snap_to_mesh(0.999999, 0.01) == pytest.approx(0.99)
    assert geometry13.snap_to_mesh(1.2345, 0.0) == pytest.approx(1.2345)


# ---------------------------------------------------------------------------
# the fraction parameterization
# ---------------------------------------------------------------------------


def test_fraction_parameterization_is_the_shipped_default(cfg):
    assert design13.grading_parameterization(cfg) == "fraction"
    names = [spec.name for spec in design13.search_space_specs(cfg)]
    assert "grading_fraction_of_feasible_max" in names
    assert "grading_thickness_nm" not in names


# Barriers and fractions inside the LIVE search space. v3 raised the barrier
# floor to 0.85 nm and the fraction floor to 0.35, so v2's corners (0.5 nm
# barrier, 0.05 fraction) are no longer proposable and asking geometry to
# realize them tests nothing the optimizer can reach.
@pytest.mark.parametrize("asymmetry,barrier", [(0.36, 0.85), (0.46, 1.8), (0.56, 2.5),
                                               (0.503818, 2.058127), (0.368472, 0.9)])
@pytest.mark.parametrize("fraction", [0.35, 0.5, 0.999, 1.0])
def test_every_fraction_yields_a_constructible_geometry(cfg, asymmetry, barrier, fraction):
    """The point of the parameterization: an impossible grade is unproposable.

    Includes the exact well/barrier geometries of premium trials 4 and 12,
    which the raw-thickness form allowed Ax to break.
    """

    resolved = design13.resolve_config(
        {
            "asymmetry_s": asymmetry,
            "central_barrier_thickness_nm": barrier,
            "grading_fraction_of_feasible_max": fraction,
            "grading_profile": "linear",
        },
        cfg,
    )
    assert geometry13.evaluate(resolved).feasible is True


def test_fraction_records_proposal_and_realization_separately(cfg):
    canonical = design13.canonicalize(
        {
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.8,
            "grading_fraction_of_feasible_max": 0.5,
            "grading_profile": "linear",
        },
        cfg,
    )
    assert canonical["_proposed_grading_fraction"] == pytest.approx(0.5)
    assert canonical["_maximum_feasible_grading_nm"] == pytest.approx(1.7)
    assert canonical["grading_thickness_nm"] == pytest.approx(0.85)


def test_the_same_fraction_realizes_differently_as_the_barrier_moves(cfg):
    widths = []
    for barrier in (0.6, 1.2, 1.8, 2.4):
        canonical = design13.canonicalize(
            {"asymmetry_s": 0.46, "central_barrier_thickness_nm": barrier,
             "grading_fraction_of_feasible_max": 0.8, "grading_profile": "linear"},
            cfg,
        )
        widths.append(canonical["grading_thickness_nm"])
    assert widths == sorted(widths)
    assert widths[0] < widths[-1]


def test_provenance_fields_are_not_part_of_design_identity(cfg):
    """Two proposals that build the same deck are the same structure."""

    canonical = design13.canonicalize(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
         "grading_fraction_of_feasible_max": 0.5, "grading_profile": "linear"},
        cfg,
    )
    physical = design13.physical_design(canonical)
    assert "_proposed_grading_fraction" not in physical
    thickness_cfg = copy.deepcopy(cfg)
    thickness_cfg["bo"]["search_space"]["parameterization"] = "thickness"
    same = design13.canonicalize(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
         "grading_thickness_nm": physical["grading_thickness_nm"],
         "grading_profile": "linear"},
        thickness_cfg,
    )
    assert design13.physical_design(same) == physical


def test_design_hash_is_stable_and_structure_only(cfg):
    first = design13.design_hash(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
         "grading_fraction_of_feasible_max": 0.5, "grading_profile": "linear"}, cfg)
    again = design13.design_hash(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.8,
         "grading_fraction_of_feasible_max": 0.5, "grading_profile": "linear"}, cfg)
    other = design13.design_hash(
        {"asymmetry_s": 0.50, "central_barrier_thickness_nm": 1.8,
         "grading_fraction_of_feasible_max": 0.5, "grading_profile": "linear"}, cfg)
    assert first == again != other
    assert len(first) == 16


# ---------------------------------------------------------------------------
# preflight and regeneration
# ---------------------------------------------------------------------------


def test_preflight_accepts_a_constructible_unique_candidate(cfg):
    verdict = axsearch13.preflight(
        {"interface_mode": "graded", "asymmetry_s": 0.46,
         "central_barrier_thickness_nm": 1.8,
         "grading_fraction_of_feasible_max": 0.5, "grading_profile": "linear"},
        cfg, {},
    )
    assert verdict["accepted"] is True
    assert verdict["design_hash"]
    assert verdict["realized_grading_thickness_nm"] == pytest.approx(0.85)
    assert verdict["maximum_feasible_grading_nm"] == pytest.approx(1.7)


def test_preflight_rejects_the_trial_12_geometry(thickness_cfg):
    verdict = axsearch13.preflight(
        {"asymmetry_s": 0.368472, "central_barrier_thickness_nm": 0.565246,
         "grading_thickness_nm": 1.314021, "grading_profile": "erf"},
        thickness_cfg, {},
    )
    assert verdict["accepted"] is False
    assert axsearch13.REJECT_GEOMETRY in verdict["rejection_reason"]


def test_preflight_rejects_the_trial_13_resuggestion(thickness_cfg):
    """Trial 13 was trial 12's design proposed again; both must be refused."""

    parameters = {"asymmetry_s": 0.368472, "central_barrier_thickness_nm": 0.565246,
                  "grading_thickness_nm": 1.314021, "grading_profile": "erf"}
    first = axsearch13.preflight(parameters, thickness_cfg, {})
    assert first["accepted"] is False
    # Even after being recorded, a re-proposal is refused -- and for the
    # geometry reason, since an unbuildable design never gets a hash to
    # collide on.
    again = axsearch13.preflight(parameters, thickness_cfg, {"whatever": 12})
    assert again["accepted"] is False


def test_preflight_rejects_a_canonical_duplicate(cfg):
    parameters = {"interface_mode": "graded", "asymmetry_s": 0.46,
                  "central_barrier_thickness_nm": 1.8,
                  "grading_fraction_of_feasible_max": 0.5, "grading_profile": "linear"}
    design_hash = design13.design_hash(parameters, cfg)
    verdict = axsearch13.preflight(parameters, cfg, {design_hash: 7})
    assert verdict["accepted"] is False
    assert axsearch13.REJECT_DUPLICATE in verdict["rejection_reason"]
    assert verdict["duplicate_of_trial"] == 7


def test_seen_hashes_remember_rejected_candidates(cfg, tmp_path):
    ledger = axsearch13.Ledger(tmp_path)
    ledger.write({"trial_index": 12, "status": "rejected", "design_hash": "abc123"})
    assert axsearch13.seen_design_hashes(ledger, cfg).get("abc123") == 12
    relaxed = copy.deepcopy(cfg)
    relaxed["bo"]["prevent_resuggestion_of_rejected_candidates"] = False
    assert "abc123" not in axsearch13.seen_design_hashes(ledger, relaxed)


@pytest.mark.slow
def test_regeneration_replaces_a_rejected_candidate_within_the_iteration(cfg, tmp_path):
    """A refused proposal must not cost an iteration."""

    import demo13

    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 3, "num_iterations": 1, "batch_size": 1})
    experiment = demo13.Experiment(variant, tmp_path / "exp")
    rejection_log: list[dict] = []
    accepted, events = demo13._accepted_candidates(experiment, variant, 1, rejection_log)
    assert len(accepted) == 1
    # Whatever happened, the accepted candidate is constructible and unique.
    verdict = axsearch13.preflight(
        accepted[0].parameters, variant, {}
    )
    assert verdict["accepted"] is True
    for row in rejection_log:
        assert row["replacement_trial_index"] == accepted[0].trial_index
        assert row["solver_launched"] is False


def test_regeneration_is_bounded(cfg, tmp_path):
    """An empty feasible region must terminate, not spin."""

    import demo13

    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 2, "num_iterations": 1,
                          "batch_size": 1, "max_candidate_regeneration_attempts": 3})
    experiment = demo13.Experiment(variant, tmp_path / "exp")
    # Refuse everything.
    original = axsearch13.preflight
    axsearch13.preflight = lambda *a, **k: {
        "accepted": False, "rejection_reason": "geometry_preflight: forced",
        "canonical": {"asymmetry_s": 0.4, "central_barrier_thickness_nm": 1.0,
                      "grading_thickness_nm": 0.0, "grading_profile": "abrupt"},
        "design_hash": None, "duplicate_of_trial": None,
        "maximum_feasible_grading_nm": 0.0, "realized_grading_thickness_nm": 0.0,
        "proposed_grading_fraction": None, "geometry_reason": "forced",
    }
    try:
        rejection_log: list[dict] = []
        accepted, _events = demo13._accepted_candidates(
            experiment, variant, 1, rejection_log
        )
    finally:
        axsearch13.preflight = original
    assert accepted == []
    assert len(rejection_log) == 3


def test_zero_regeneration_attempts_is_refused(cfg, tmp_path):
    import demo13

    variant = copy.deepcopy(cfg)
    variant["bo"]["max_candidate_regeneration_attempts"] = 0
    experiment = demo13.Experiment(variant, tmp_path / "exp")
    with pytest.raises(demo_workflow.DemoError):
        demo13._accepted_candidates(experiment, variant, 1, [])


# ---------------------------------------------------------------------------
# budget accounting
# ---------------------------------------------------------------------------


def _ledger_with(tmp_path, rows):
    ledger = axsearch13.Ledger(tmp_path)
    for row in rows:
        ledger.write(row)
    return ledger


def test_rejected_proposals_do_not_consume_bo_iterations(cfg, tmp_path):
    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 2, "num_iterations": 3, "batch_size": 1})
    ledger = _ledger_with(tmp_path, [
        {"trial_index": 0, "status": "completed", "generation_method": "Sobol"},
        {"trial_index": 1, "status": "completed", "generation_method": "Sobol"},
        {"trial_index": 2, "status": "rejected", "generation_method": "MBM",
         "rejection_reason": "geometry_preflight: too wide"},
        {"trial_index": 3, "status": "rejected", "generation_method": "MBM",
         "rejection_reason": "canonical_duplicate: same as trial 2"},
        {"trial_index": 4, "status": "completed", "generation_method": "MBM"},
    ])
    plan = axsearch13.plan(variant, ledger)
    # Two initial + one real model-based evaluation: two iterations remain.
    assert plan["completed_bo_iterations"] == 1
    assert plan["remaining_bo_iterations"] == 2
    assert plan["rejected_proposals"] == 2
    assert plan["recorded_proposals"] == 5
    assert plan["budget_consuming_trials"] == 3


def test_rejections_can_be_made_to_count_when_the_yaml_asks(cfg, tmp_path):
    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 2, "num_iterations": 3, "batch_size": 1,
                          "invalid_preflight_counts_as_bo_iteration": True,
                          "duplicate_counts_as_bo_iteration": True})
    ledger = _ledger_with(tmp_path, [
        {"trial_index": 0, "status": "completed", "generation_method": "Sobol"},
        {"trial_index": 1, "status": "completed", "generation_method": "Sobol"},
        {"trial_index": 2, "status": "rejected", "generation_method": "MBM",
         "rejection_reason": "geometry_preflight: too wide"},
        {"trial_index": 3, "status": "rejected", "generation_method": "MBM",
         "rejection_reason": "canonical_duplicate: same as trial 2"},
        {"trial_index": 4, "status": "completed", "generation_method": "MBM"},
    ])
    assert axsearch13.plan(variant, ledger)["completed_bo_iterations"] == 3


def test_budget_accounting_separates_proposals_from_evaluations(cfg, tmp_path):
    ledger = _ledger_with(tmp_path, [
        {"trial_index": 0, "status": "completed", "generation_method": "Sobol",
         "trial_valid": True, "trial_outcome_class": "valid",
         "solver_completed": True, "output_directory_path": "runs/t0000"},
        {"trial_index": 1, "status": "completed", "generation_method": "Sobol",
         "trial_valid": False, "trial_outcome_class": "scientifically_invalid",
         "solver_completed": True, "output_directory_path": "runs/t0001"},
        {"trial_index": 2, "status": "rejected", "generation_method": "MBM",
         "rejection_reason": "geometry_preflight: too wide"},
        {"trial_index": 3, "status": "rejected", "generation_method": "MBM",
         "rejection_reason": "canonical_duplicate: same as trial 2"},
        {"trial_index": 4, "status": "failed", "generation_method": "MBM",
         "output_directory_path": "runs/t0004"},
        {"trial_index": 5, "status": "completed", "generation_method": "MBM",
         "trial_valid": True, "trial_outcome_class": "valid_with_warning",
         "solver_completed": True, "output_directory_path": "runs/t0005"},
    ])
    budget = axsearch13.budget_accounting(cfg, ledger)
    assert budget["sobol_proposals"] == 2
    assert budget["sobol_observations_completed"] == 2
    assert budget["model_based_proposals"] == 4
    assert budget["model_based_observations_completed"] == 1
    assert budget["preflight_invalid_proposals"] == 1
    assert budget["duplicate_proposals"] == 1
    assert budget["abandoned_ax_trials"] == 2
    assert budget["solver_attempts"] == 4
    assert budget["solver_completed_cases"] == 3
    assert budget["ax_completed_observations"] == 3
    assert budget["scientifically_feasible_observations"] == 2
    assert budget["warning_only_observations"] == 1
    assert budget["rejected_observations"] == 1
    assert budget["mechanically_failed_trials"] == 1
    assert "valid model-based evaluation" in budget["iteration_definition"]


# ---------------------------------------------------------------------------
# checkpoint compatibility
# ---------------------------------------------------------------------------


def test_resuming_under_a_changed_parameterization_is_refused(cfg, tmp_path):
    import demo13

    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 2, "num_iterations": 1})
    demo13.Experiment(variant, tmp_path / "exp")
    changed = copy.deepcopy(variant)
    changed["bo"]["search_space"]["parameterization"] = "thickness"
    with pytest.raises(demo_workflow.DemoError) as failure:
        demo13.Experiment(changed, tmp_path / "exp")
    message = str(failure.value)
    assert "search space has changed" in message
    assert "parameterization" in message
    assert "new directory" in message
    # The old experiment is untouched.
    assert (tmp_path / "exp" / "ax_experiment_snapshot.json").is_file()


def test_resuming_an_unstamped_snapshot_is_refused_with_instructions(cfg, tmp_path):
    import demo13

    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 2, "num_iterations": 1})
    demo13.Experiment(variant, tmp_path / "exp")
    (tmp_path / "exp" / "experiment_schema.json").unlink()
    with pytest.raises(demo_workflow.DemoError) as failure:
        demo13.Experiment(variant, tmp_path / "exp")
    assert "no recorded search-space schema" in str(failure.value)


def test_matching_schema_resumes_cleanly(cfg, tmp_path):
    import demo13

    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 2, "num_iterations": 1})
    first = demo13.Experiment(variant, tmp_path / "exp")
    assert not first.resumed
    second = demo13.Experiment(variant, tmp_path / "exp")
    assert second.resumed
    stored = json.loads((tmp_path / "exp" / "experiment_schema.json").read_text("utf-8"))
    assert stored["parameterization"] == "fraction"
    assert stored["experiment_schema_version"] == demo13.EXPERIMENT_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# the whole main() path, which unit tests alone did not cover
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("parameterization", ["fraction", "thickness"])
def test_surrogate_slices_use_the_searched_grading_parameter(cfg, parameterization):
    """Slices must vary a parameter that exists in the search space.

    The unit tests all passed while `main()` raised KeyError: the surrogate
    slice builder still named `grading_thickness_nm`, which the fraction
    parameterization removes. Only an end-to-end run caught it.
    """

    import demo13

    variant = copy.deepcopy(cfg)
    variant["bo"]["search_space"]["parameterization"] = parameterization
    grading = design13.grading_parameter_name(variant)
    canonical, encoded = demo13._slice_points(variant, "asymmetry_s", grading)
    assert canonical and encoded
    assert all(grading in point for point in canonical)

    def _constructible(point):
        try:
            design13.resolve_config(point, variant)
        except demo_workflow.DemoError:
            return False
        return True

    constructible = [point for point in canonical if _constructible(point)]
    if parameterization == "fraction":
        # Every point of the surface is a design that could actually be built.
        assert len(constructible) == len(canonical)
    else:
        # Under the raw-thickness form the slice sweeps past what the
        # held-fixed barrier can carry, so part of the surrogate surface
        # describes structures that cannot exist. That is the weakness the
        # fraction parameterization removes, and it is asserted here so the
        # difference is on the record rather than folklore.
        assert 0 < len(constructible) < len(canonical)

    base = demo13._slice_base_point(variant, {})
    assert grading in base
    if parameterization == "fraction":
        lower, upper = design13.graded_fraction_bounds(variant)
        assert lower <= base[grading] <= upper
        assert "grading_thickness_nm" not in base


def test_partial_dependence_covers_every_range_parameter(cfg):
    import demo13

    grading = design13.grading_parameter_name(cfg)
    for spec in design13.search_space_specs(cfg):
        if not isinstance(spec, design13.RangeSpec):
            continue
        base = demo13._slice_base_point(cfg, {})
        base[spec.name] = float(spec.lower)
        assert design13.resolve_config(base, cfg)
    assert grading in {
        spec.name
        for spec in design13.search_space_specs(cfg)
        if isinstance(spec, design13.RangeSpec)
    }
