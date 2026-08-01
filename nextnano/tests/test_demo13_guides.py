"""Guide-to-code synchronization. A stale guide must be a test failure.

The guides in ``guides/`` are generated from :mod:`catalog13`, and this module
is what stops that catalogue becoming "a second hardcoded list that drifts":

* plot entries are checked against the list the renderer actually iterates;
* table entries against the table catalogue;
* metric units against ``tables13.COLUMN_UNITS`` -- never restated;
* parameter entries against real dotted paths in ``demo.yaml``;
* the files on disk against what the generator produces right now.

If any of those diverge, this fails rather than a reader discovering it.
"""

from __future__ import annotations

from pathlib import Path
import re
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

import catalog13  # noqa: E402
import guides13  # noqa: E402
import plots13  # noqa: E402
import report13  # noqa: E402
import tables13  # noqa: E402

GUIDES = DEMO / "guides"

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return yaml.safe_load((DEMO / "demo.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def guide_text():
    """Only the GENERATED beginner guides.

    The audit reports that also live in `guides/` are historical documents: they
    have to be able to name the v2 winner and quote a pm/V label in the course of
    recording them as superseded or denied. Scanning them for those strings would
    make an accurate audit fail its own check.
    """

    return {
        name: (GUIDES / name).read_text(encoding="utf-8")
        for name in guides13.GUIDE_FILES
    }


# ---------------------------------------------------------------------------
# the guides exist and match what the generator produces
# ---------------------------------------------------------------------------


def test_every_guide_file_exists():
    for name in guides13.GUIDE_FILES:
        assert (GUIDES / name).is_file(), f"{name} has not been generated"


def test_guides_on_disk_match_the_generator():
    """A guide edited by hand, or left stale after a code change, fails here."""

    for name, builder in guides13.GUIDE_FILES.items():
        on_disk = (GUIDES / name).read_text(encoding="utf-8")
        assert on_disk == builder(), (
            f"{name} is out of date. Regenerate with `python guides13.py`; do not "
            "edit the generated file by hand."
        )


# ---------------------------------------------------------------------------
# plots
# ---------------------------------------------------------------------------


def test_every_rendered_plot_has_a_guide_entry():
    missing = [name for name, _ in plots13.PLOT_SET if name not in report13.PLOT_GUIDE]
    assert not missing, f"plots with no guide entry: {missing}"


def test_every_rendered_plot_has_catalogue_notes():
    missing = [name for name, _ in plots13.PLOT_SET if name not in catalog13.PLOT_NOTES]
    assert not missing, f"plots with no population/v3 note: {missing}"


def test_no_guide_entry_describes_a_plot_that_is_not_rendered():
    rendered = {name for name, _ in plots13.PLOT_SET}
    orphan_guide = [n for n in report13.PLOT_GUIDE if n not in rendered]
    orphan_notes = [n for n in catalog13.PLOT_NOTES if n not in rendered]
    assert not orphan_guide, f"guide entries for nonexistent plots: {orphan_guide}"
    assert not orphan_notes, f"catalogue notes for nonexistent plots: {orphan_notes}"


def test_every_plot_population_is_a_named_population():
    for name, note in catalog13.PLOT_NOTES.items():
        assert note["population"] in catalog13.POPULATIONS, (
            f"{name} claims population {note['population']!r}, which is not defined"
        )


def test_plot_csv_links_follow_the_writer(guide_text):
    """The guide's CSV path must be the one the plot writer actually uses."""

    text = guide_text["PLOTS_GUIDE.md"]
    for name, _ in plots13.PLOT_SET:
        expected = catalog13.plot_csv_name(name)
        assert expected.endswith(f"{Path(name).stem}.csv")
        assert f"`{expected}`" in text, f"{name}: CSV link missing or wrong"


# ---------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------


def test_every_table_has_a_guide_entry(guide_text):
    text = guide_text["TABLES_GUIDE.md"]
    for name in tables13.TABLE_CATALOGUE:
        assert f"`{name}.csv`" in text, f"{name} is not documented"


def test_the_repaired_v3_tables_are_documented(guide_text):
    text = guide_text["TABLES_GUIDE.md"]
    for name in (
        "bo_budget_accounting",
        "bo_candidate_rejection_history",
        "bo_trial_iteration_mapping",
        "bo_proposed_vs_realized_grading",
    ):
        assert name in text


# ---------------------------------------------------------------------------
# metrics and units -- stated once, in the code
# ---------------------------------------------------------------------------


def test_metric_units_come_from_the_code_not_the_guide(guide_text):
    """The guide must not restate a unit; it renders `tables13.unit_for`."""

    text = guide_text["OUTPUT_RESULTS_GUIDE.md"]
    for name in catalog13.METRIC_NOTES:
        unit = tables13.unit_for(name)
        assert f"**Units:** {unit}" in text, (
            f"{name}: guide unit disagrees with tables13.unit_for -> {unit!r}"
        )


def test_the_required_metrics_are_all_documented():
    required = {
        "relative_chi2_at_target_wavelength_abs", "relative_peak_chi2_abs",
        "peak_wavelength_nm", "signed_detuning_nm", "absolute_detuning_nm",
        "trial_valid", "orthonormality_error", "origin_independence_valid",
        "maximum_boundary_probability", "state_tracking_confidence",
        "state_tracking_margin", "proposed_grading_fraction",
        "realized_grading_thickness_nm", "probability_of_feasibility",
        "constrained_expected_improvement_proxy", "best_objective_so_far",
        "rejection_reason", "mbm_iteration_number",
    }
    missing = sorted(required - set(catalog13.METRIC_NOTES))
    assert not missing, f"undocumented result metrics: {missing}"


def test_the_grading_fraction_is_never_documented_as_a_length():
    note = catalog13.METRIC_NOTES["proposed_grading_fraction"]
    assert "NOT a length" in note["caution"]
    assert tables13.unit_for("proposed_grading_fraction") != "nm"
    assert tables13.unit_for("realized_grading_thickness_nm") == "nm"


# ---------------------------------------------------------------------------
# parameters -- every documented setting must exist in demo.yaml
# ---------------------------------------------------------------------------


def _resolve(cfg, dotted: str):
    cursor = cfg
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def test_every_documented_parameter_exists_in_the_yaml(cfg):
    """A documented setting that no longer exists must fail, not mislead."""

    missing = [
        entry["path"]
        for entry in catalog13.PARAMETER_NOTES
        if _resolve(cfg, entry["path"]) is None
    ]
    assert not missing, f"documented settings absent from demo.yaml: {missing}"


def test_the_required_input_parameters_are_documented():
    documented = {entry["path"] for entry in catalog13.PARAMETER_NOTES}
    required = {
        "bo.search_space.asymmetry_s",
        "bo.search_space.central_barrier_thickness_nm",
        "bo.search_space.grading_profile",
        "bo.search_space.grading_fraction_of_feasible_max",
        "bo.search_space.minimum_mesh_resolvable_nonzero_grading_nm",
        "numerical.active_region_grid_spacing_nm",
        "grading.minimum_grid_points_per_grade",
        "bo.target_wavelength_nm",
        "bo.outcome_constraints.maximum_detuning_nm",
        "bo.outcome_constraints.maximum_boundary_probability",
        "bo.outcome_constraints.minimum_state_tracking_confidence",
        "numerical.number_of_electron_states",
        "numerical.domain_padding_nm",
        "bo.num_initial_trials", "bo.num_iterations", "bo.batch_size",
        "bo.random_seed", "workflow.mode", "workflow.experiment_state_dir",
        "simulation.run_solver", "validation_study.enabled",
    }
    missing = sorted(required - documented)
    assert not missing, f"undocumented input parameters: {missing}"


def test_search_space_parameters_are_marked_as_invalidating_checkpoints():
    for entry in catalog13.PARAMETER_NOTES:
        if entry["path"].startswith("bo.search_space.") and entry["path"].endswith(
            ("asymmetry_s", "central_barrier_thickness_nm", "grading_profile")
        ):
            assert entry["invalidates_checkpoint"] is True, entry["path"]


def test_the_geometry_rule_is_explained(guide_text):
    """The 0.85 vs 0.90 nm asymmetry is the single most confusing rule here."""

    text = guide_text["INPUT_PARAMETERS_GUIDE.md"]
    assert "0.85" in text and "0.90" in text
    assert "abrupt" in text.lower() and "graded" in text.lower()


# ---------------------------------------------------------------------------
# no stale terminology anywhere in the guides
# ---------------------------------------------------------------------------


def test_guides_never_call_relative_chi2_pm_per_volt(guide_text):
    for name, text in guide_text.items():
        for match in re.finditer(r"pm/V", text):
            window = text[max(0, match.start() - 120): match.end() + 60]
            # A denial may be prose ("never pm/V") or a verdict cell in a
            # supported/not-supported table ("| chi2 = 0.411 pm/V | **no** ...").
            assert re.search(r"never|not\b|Never|NOT|\*\*no\*\*", window), (
                f"{name}: 'pm/V' appears without a denial near it"
            )


def test_guides_do_not_present_v2_results_as_current(guide_text):
    for name, text in guide_text.items():
        assert "t0012" not in text, f"{name} names the v2 winner"
        assert "demo13_ax_experiment_v2" not in text, f"{name} names the v2 experiment"
        assert "search-space-2" not in text, f"{name} names the old schema"


def test_guides_do_not_mix_trial_and_iteration_terminology(guide_text):
    """The ledger's `iteration` column must be called out, not used silently."""

    for name in ("PLOTS_GUIDE.md", "TABLES_GUIDE.md", "OUTPUT_RESULTS_GUIDE.md"):
        text = guide_text[name]
        if "iteration" in text.lower():
            assert "mbm_iteration_number" in text or "MBM iteration" in text, (
                f"{name} uses 'iteration' without distinguishing MBM iterations "
                "from proposal attempts"
            )


def test_guides_state_the_v3_result_consistently(guide_text):
    """Every guide that mentions the result must agree on it."""

    for name in ("README.md", "PLOTS_GUIDE.md", "TABLES_GUIDE.md",
                 "OUTPUT_RESULTS_GUIDE.md"):
        text = guide_text[name]
        assert "t0021" in text
        assert "not a validated optimum" in text or "not yet a validated" in text


def test_guides_never_claim_grading_was_settled(guide_text):
    text = guide_text["OUTPUT_RESULTS_GUIDE.md"]
    assert "grading helps / hurts | **no**" in text
    assert "erf is the best profile | **no**" in text


# ---------------------------------------------------------------------------
# work-laptop safety
# ---------------------------------------------------------------------------


def test_work_laptop_guide_marks_every_command_block(guide_text):
    text = guide_text["WORK_LAPTOP_GUIDE.md"]
    assert "SAFE" in text and "SPENDS SOLVER TIME" in text
    # Every numbered step must carry a marking.
    for heading in re.findall(r"^## \d+\. .+$", text, flags=re.MULTILINE):
        assert "SAFE" in heading or "SPENDS SOLVER TIME" in heading, heading


def test_work_laptop_guide_does_not_hand_over_a_stage5_launch_command(guide_text):
    text = guide_text["WORK_LAPTOP_GUIDE.md"]
    assert "validate_top_designs" in text, "the mode must still be named as unsafe"
    # ...but never as a ready-to-paste command line.
    assert "run_demo13.py" in text
    launchable = re.findall(r"^python .*run_demo13\.py.*$", text, flags=re.MULTILINE)
    for line in launchable:
        assert "validate_top_designs" not in line, (
            "the guide must not provide a runnable Stage 5 launch command"
        )
    assert "NOT AUTHORIZED" in text


def test_work_laptop_guide_requires_a_clean_tree_and_hash_checks(guide_text):
    text = guide_text["WORK_LAPTOP_GUIDE.md"]
    assert "git status --porcelain" in text
    assert text.count("sha256") >= 1
    assert "unchanged" in text


def test_troubleshooting_covers_the_known_failure_modes(guide_text):
    text = guide_text["TROUBLESHOOTING_GUIDE.md"]
    for phrase in (
        "no Ax snapshot", "search space has changed", "Generated new trial",
        "Executing", "read-only", "placeholder", "rejection_history",
        "duplicate", "iteration", "alloy", "Stage 5", "dirty",
    ):
        assert phrase.lower() in text.lower(), f"troubleshooting omits {phrase!r}"
