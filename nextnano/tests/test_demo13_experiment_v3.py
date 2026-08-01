"""Home-laptop tests for the Demo 13 v3 search space. No solver is invoked.

v3 exists to fix the two things reanalysis could not: v2's winner sat on the
barrier lower bound, and v2 never built enough genuine grades to say whether
grading helps. Both fixes are properties of the *configuration*, so they are
testable without a licence -- which is the point of testing them here.

The rule these tests exist to protect: a graded proposal the mesh cannot
resolve is **rejected**, not quietly canonicalized to abrupt. v2 collapsed such
proposals, which is how designs with no grading in them entered the surrogate's
training data wearing a profile label.
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

import axsearch13  # noqa: E402
import demo13  # noqa: E402
import demo_workflow  # noqa: E402
import design13  # noqa: E402
import grading13  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


# ---------------------------------------------------------------------------
# the configuration is what was asked for
# ---------------------------------------------------------------------------


def test_v3_workflow_targets_a_fresh_experiment_directory(cfg):
    workflow = cfg["workflow"]
    assert workflow["experiment_state_dir"] == "demo13_ax_experiment_v3"
    assert workflow["mode"] == "closed_loop"
    assert cfg["simulation"]["run_solver"] is True
    # v2 must not be named anywhere in the active configuration.
    assert "demo13_ax_experiment_v2" not in str(workflow)


def test_v3_bounds_and_budget(cfg):
    space = cfg["bo"]["search_space"]
    assert [space["central_barrier_thickness_nm"]["lower"],
            space["central_barrier_thickness_nm"]["upper"]] == [0.85, 2.5]
    assert [space["asymmetry_s"]["lower"],
            space["asymmetry_s"]["upper"]] == [0.36, 0.56]
    assert set(design13.graded_profiles(cfg)) == {"linear", "sigmoid", "erf", "cosine"}
    assert cfg["bo"]["num_initial_trials"] == 6
    assert cfg["bo"]["num_iterations"] == 10
    assert cfg["bo"]["batch_size"] == 1
    assert cfg["bo"]["optimization_mode"] == "target_wavelength"
    assert cfg["bo"]["objectives"]["target_wavelength"]["maximize"] == [
        "relative_chi2_at_target_wavelength_abs"
    ]
    assert float(cfg["bo"]["target_wavelength_nm"]) == 1550.0


def test_v3_minimum_grading_is_declared_and_enforced(cfg):
    assert design13.minimum_resolvable_grading_nm(cfg) == pytest.approx(0.80)
    assert design13.rejects_subresolution_grades(cfg) is True
    # The collapse threshold must not sit below the physical minimum, or a
    # sub-resolution grade would be accepted as a real graded design.
    collapse = float(cfg["bo"]["search_space"]["minimum_graded_thickness_nm"])
    assert collapse >= design13.minimum_resolvable_grading_nm(cfg)


def test_v3_mesh_resolves_the_thinnest_barrier(cfg):
    """A barrier is not a grade: it gets no local refinement, so this is it."""

    active = float(cfg["numerical"]["active_region_grid_spacing_nm"])
    thinnest = float(cfg["bo"]["search_space"]["central_barrier_thickness_nm"]["lower"])
    assert active == pytest.approx(0.05)
    assert thinnest / active >= 10, "the thinnest barrier must span >= 10 mesh cells"


def test_v3_grade_mesh_resolves_the_staircase_sublayers(cfg):
    """Non-native profiles are built from sublayers; the grid must see them."""

    import grading12

    grading = cfg["grading"]
    minimum = design13.minimum_resolvable_grading_nm(cfg)
    sublayer_nm = minimum / int(grading["staircase_sublayers"])
    spacing = grading12.required_grade_spacing_nm(
        minimum, int(grading["minimum_grid_points_per_grade"])
    )
    assert spacing <= sublayer_nm, (
        "each staircase sublayer must be at least one grade-mesh spacing wide"
    )


def test_v3_does_not_warm_start_across_a_mesh_change(cfg):
    """Two meshes are two different calculations of the same design."""

    assert cfg["bo"]["warm_start"]["use_demo12_warm_start"] is False


def test_v3_config_validates(cfg):
    demo13.validate_demo13_config(cfg)


def test_validation_rejects_a_collapse_threshold_below_the_resolvable_minimum(cfg):
    broken = copy.deepcopy(cfg)
    broken["bo"]["search_space"]["minimum_graded_thickness_nm"] = 0.10
    with pytest.raises(demo_workflow.DemoError, match="below"):
        demo13.validate_demo13_config(broken)


def test_validation_rejects_a_staircase_finer_than_its_grade_mesh(cfg):
    """The hard rule: a sublayer narrower than the mesh that samples it."""

    broken = copy.deepcopy(cfg)
    broken["grading"]["staircase_sublayers"] = 64  # 0.80 / 64 = 0.0125 nm
    with pytest.raises(demo_workflow.DemoError, match="staircase sublayers"):
        demo13.validate_demo13_config(broken)


def test_v3_samples_each_staircase_sublayer_more_than_once(cfg):
    """Beyond the hard rule: v3 deliberately buys a second point per sublayer.

    At the previous 10 points per grade the grade mesh would land at exactly one
    point per 0.05 nm sublayer -- legal, but a staircase sampled at its own
    period. 32 points halves that.
    """

    import grading12

    minimum = design13.minimum_resolvable_grading_nm(cfg)
    sublayer_nm = minimum / int(cfg["grading"]["staircase_sublayers"])
    spacing = grading12.required_grade_spacing_nm(
        minimum, int(cfg["grading"]["minimum_grid_points_per_grade"])
    )
    assert sublayer_nm / spacing >= 2.0


# ---------------------------------------------------------------------------
# v2 checkpoints cannot load into v3
# ---------------------------------------------------------------------------


def test_schema_version_was_bumped_for_v3(cfg):
    schema = demo13.experiment_schema(cfg)
    assert schema["experiment_schema_version"] == "demo13-search-space-3"


def test_schema_records_bounds_and_mesh_not_only_names(cfg):
    """Names alone would have let a v2 snapshot look compatible.

    v2 and v3 share the encoding, the parameterization and all four parameter
    names. Only the bounds, the resolvable minimum and the mesh differ.
    """

    schema = demo13.experiment_schema(cfg)
    assert schema["range_bounds"]["central_barrier_thickness_nm"] == [0.85, 2.5]
    assert schema["minimum_resolvable_grading_nm"] == pytest.approx(0.80)
    assert schema["active_region_grid_spacing_nm"] == pytest.approx(0.05)


def test_a_v2_shaped_experiment_refuses_to_resume_under_v3(cfg, tmp_path):
    """The concrete protection: a v2 snapshot loaded under v3 must raise."""

    import json

    state = tmp_path / "demo13_ax_experiment_v2"
    state.mkdir()
    # A v2 schema: same names and encoding, older version and bounds.
    v2_schema = {
        "experiment_schema_version": "demo13-search-space-2",
        "encoding": "hierarchical",
        "parameterization": "fraction",
        "parameters": sorted(
            spec.name for spec in design13.search_space_specs(cfg)
        ),
    }
    (state / "experiment_schema.json").write_text(json.dumps(v2_schema), encoding="utf-8")
    (state / "ax_experiment_snapshot.json").write_text("{}", encoding="utf-8")

    with pytest.raises(demo_workflow.DemoError, match="search space has changed"):
        demo13.Experiment(cfg, state)


def test_bound_change_alone_blocks_a_resume(cfg, tmp_path):
    """Even at the same schema version, different bounds must not resume."""

    import json

    state = tmp_path / "state"
    state.mkdir()
    stale = dict(demo13.experiment_schema(cfg))
    stale["range_bounds"] = dict(stale["range_bounds"])
    stale["range_bounds"]["central_barrier_thickness_nm"] = [0.5, 2.5]
    (state / "experiment_schema.json").write_text(json.dumps(stale), encoding="utf-8")
    (state / "ax_experiment_snapshot.json").write_text("{}", encoding="utf-8")

    with pytest.raises(demo_workflow.DemoError, match="search space has changed"):
        demo13.Experiment(cfg, state)


# ---------------------------------------------------------------------------
# sub-resolution grades are rejected, zero-thickness grades are abrupt
# ---------------------------------------------------------------------------


def _graded(barrier, fraction, profile="linear", asymmetry=0.46):
    return {
        "asymmetry_s": asymmetry,
        "central_barrier_thickness_nm": barrier,
        "interface_mode": "graded",
        "grading_fraction_of_feasible_max": fraction,
        "grading_profile": profile,
    }


def _abrupt(barrier, asymmetry=0.46):
    return {
        "asymmetry_s": asymmetry,
        "central_barrier_thickness_nm": barrier,
        "interface_mode": "abrupt",
    }


def test_a_subresolution_graded_proposal_is_rejected_not_collapsed(cfg):
    verdict = axsearch13.preflight(_graded(1.2, 0.35, "sigmoid"), cfg, {})
    assert verdict["accepted"] is False
    assert axsearch13.REJECT_SUBRESOLUTION in verdict["rejection_reason"]
    # The width that would have been built is reported, not just "too small".
    assert verdict["realized_grading_before_collapse_nm"] == pytest.approx(0.38)
    assert verdict["minimum_resolvable_grading_nm"] == pytest.approx(0.80)
    # It never reaches the solver, and it is not recorded as an abrupt design.
    assert verdict["design_hash"] is None


def test_a_graded_proposal_where_no_grade_fits_says_so(cfg):
    """Below a 0.90 nm barrier the graded branch is empty; say why."""

    verdict = axsearch13.preflight(_graded(0.85, 1.0), cfg, {})
    assert verdict["accepted"] is False
    assert axsearch13.REJECT_SUBRESOLUTION in verdict["rejection_reason"]
    assert "no grade at all is constructible" in verdict["rejection_reason"]
    assert verdict["maximum_feasible_grading_nm"] == pytest.approx(0.75)


def test_a_resolvable_graded_proposal_is_accepted(cfg):
    verdict = axsearch13.preflight(_graded(1.2, 0.95, "sigmoid"), cfg, {})
    assert verdict["accepted"] is True
    assert verdict["realized_grading_thickness_nm"] >= 0.80
    view = grading13.from_record(
        {"trial_index": 0, "parameters": _graded(1.2, 0.95, "sigmoid"),
         "canonical_parameters": verdict["canonical"]}
    )
    assert view.is_genuinely_graded is True
    assert view.profile_evidence == "sigmoid"
    assert view.collapsed_to_abrupt is False


def test_abrupt_is_still_proposable_at_the_thinnest_barrier(cfg):
    """The graded branch is empty below 0.90 nm; the abrupt branch is not."""

    verdict = axsearch13.preflight(_abrupt(0.85), cfg, {})
    assert verdict["accepted"] is True
    assert verdict["realized_grading_thickness_nm"] == 0.0
    assert verdict["design_hash"]


def test_a_zero_realized_grade_is_classified_abrupt_everywhere(cfg):
    """Rejection governs proposals; classification governs description."""

    view = grading13.from_parameters(_abrupt(1.5), cfg)
    assert view.realized_interface_mode == grading13.ABRUPT
    assert view.realized_grading_profile == grading13.ABRUPT
    assert view.realized_grading_thickness_nm == 0.0
    assert view.is_genuinely_graded is False
    assert view.profile_evidence is None


def test_rejection_does_not_consume_a_bo_iteration(cfg):
    assert cfg["bo"]["invalid_preflight_counts_as_bo_iteration"] is False
    assert int(cfg["bo"]["max_candidate_regeneration_attempts"]) >= 10


def test_disabling_the_rule_restores_the_v2_collapse(cfg):
    """The rule is a switch, and the switch is what v2 had turned off."""

    permissive = copy.deepcopy(cfg)
    permissive["bo"]["search_space"]["reject_subresolution_grades"] = False
    verdict = axsearch13.preflight(_graded(1.2, 0.35, "sigmoid"), permissive, {})
    assert verdict["accepted"] is True
    # ...and this is precisely the v2 defect: a "sigmoid" trial with no grade.
    assert verdict["realized_grading_thickness_nm"] == 0.0
    assert verdict["canonical"]["grading_profile"] == "abrupt"


# ---------------------------------------------------------------------------
# the graded branch is reachable often enough to be worth searching
# ---------------------------------------------------------------------------


def test_the_fraction_lower_bound_admits_grades_at_wide_barriers(cfg):
    """A lower bound that rejected everything would make v3 pointless."""

    lower, _upper = design13.graded_fraction_bounds(cfg)
    widest = float(cfg["bo"]["search_space"]["central_barrier_thickness_nm"]["upper"])
    maximum = design13.maximum_feasible_grading_for(
        {"asymmetry_s": 0.46, "central_barrier_thickness_nm": widest}, cfg
    )
    assert lower * maximum >= design13.minimum_resolvable_grading_nm(cfg), (
        "at the widest barrier the smallest allowed fraction must still build a "
        "resolvable grade, or no fraction near the lower bound is ever usable"
    )


def test_a_usable_graded_design_exists_across_most_of_the_barrier_range(cfg):
    """Fraction 1.0 must be constructible wherever the graded branch is live."""

    minimum = design13.minimum_resolvable_grading_nm(cfg)
    live = []
    for barrier in (0.9, 1.0, 1.2, 1.5, 2.0, 2.5):
        verdict = axsearch13.preflight(_graded(barrier, 1.0), cfg, {})
        live.append((barrier, verdict["accepted"]))
    assert all(accepted for _barrier, accepted in live), live
    # And confirm the documented boundary: below 0.90 nm nothing fits.
    assert axsearch13.preflight(_graded(0.88, 1.0), cfg, {})["accepted"] is False
