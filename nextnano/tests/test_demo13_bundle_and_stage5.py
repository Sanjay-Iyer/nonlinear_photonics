"""Raw-bundle helper and Stage 5 isolation. No solver, no licensed run.

Two safety properties are pinned here:

* ``bundle_raw_trials.py`` copies *out of* an experiment and never writes into
  it, and says out loud what it could not find -- because a bundle that silently
  omitted the alloy-composition profiles is exactly how v3 ended up with five
  "genuinely graded" trials and no evidence that any grade was ever built;
* Stage 5 cannot be pointed at the optimization experiment directory, which
  holds the immutable ledger of a licensed campaign.
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
DEMO11 = DEMO.parent / "11_paper_validation_interband_chi2_acqw"
DEMO12 = DEMO.parent / "12_graded_interface_coupled_quantum_well_optimization"
SCRIPTS = ROOT / "nextnano" / "scripts"
for path in (str(DEMO), str(SHARED), str(DEMO11), str(DEMO12), str(SCRIPTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import bundle_raw_trials as brt  # noqa: E402
import demo13  # noqa: E402
import demo_workflow  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


@pytest.fixture
def fake_experiment(tmp_path):
    """An experiment with raw output for two trials, one graded, one abrupt."""

    state = tmp_path / "demo13_ax_experiment_v3"
    (state / "runs" / "t0021").mkdir(parents=True)
    (state / "runs" / "t0019" / "extracted").mkdir(parents=True)

    (state / "runs" / "t0021" / "case.in").write_text("deck\n", encoding="utf-8")
    (state / "runs" / "t0021" / "console.log").write_text("log\n", encoding="utf-8")
    (state / "runs" / "t0021" / "demo_resolved.yaml").write_text("a: 1\n", encoding="utf-8")
    (state / "runs" / "t0019" / "case.in").write_text("deck\n", encoding="utf-8")
    (state / "runs" / "t0019" / "output_alloy_composition.dat").write_text(
        "z x\n0 0.55\n", encoding="utf-8"
    )
    (state / "runs" / "t0019" / "extracted" / "requested_composition_profile.csv").write_text(
        "z_nm,alloy_x\n0,0.55\n", encoding="utf-8"
    )

    records = [
        {"trial_index": 21, "candidate_id": "t0021", "status": "completed",
         "canonical_parameters": {"grading_thickness_nm": 0.0}},
        {"trial_index": 19, "candidate_id": "t0019", "status": "completed",
         "canonical_parameters": {"grading_thickness_nm": 0.86}},
        {"trial_index": 12, "candidate_id": "t0012", "status": "rejected",
         "canonical_parameters": {"grading_thickness_nm": 0.0}},
        {"trial_index": 3, "candidate_id": "t0003", "status": "completed",
         "canonical_parameters": {"grading_thickness_nm": 1.27}},
    ]
    (state / "trial_ledger.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    return state


# ---------------------------------------------------------------------------
# trial selection
# ---------------------------------------------------------------------------


def test_only_genuinely_graded_trials_are_selected(fake_experiment):
    """A refused proposal built no grade and cannot verify a profile."""

    graded = brt.genuinely_graded_trials(fake_experiment)
    assert graded == ["t0003", "t0019"]
    assert "t0021" not in graded, "t0021 realized 0 nm; it is abrupt"
    assert "t0012" not in graded, "t0012 was refused; nothing was built"


def test_the_default_selection_covers_the_priority_and_graded_trials(fake_experiment):
    trials = brt.resolve_trials(fake_experiment, None)
    for expected in ("t0021", "t0022", "t0017", "t0005"):
        assert expected in trials
    assert "t0003" in trials and "t0019" in trials
    assert len(trials) == len(set(trials)), "no trial may be requested twice"


def test_explicit_trials_override_the_default(fake_experiment):
    assert brt.resolve_trials(fake_experiment, ["t0019"]) == ["t0019"]


# ---------------------------------------------------------------------------
# copying, and saying what is missing
# ---------------------------------------------------------------------------


def test_a_dry_run_writes_nothing(fake_experiment, tmp_path):
    out = tmp_path / "bundle"
    manifest = brt.build_bundle(
        fake_experiment, out, ["t0021", "t0019"], list(brt.DEFAULT_CATEGORIES),
        dry_run=True,
    )
    assert manifest["dry_run"] is True
    assert manifest["total_files"] > 0
    assert not out.exists(), "a dry run must not create the destination"


def test_copying_leaves_the_source_untouched(fake_experiment, tmp_path):
    before = {
        p: p.read_bytes() for p in fake_experiment.rglob("*") if p.is_file()
    }
    brt.build_bundle(
        fake_experiment, tmp_path / "bundle", ["t0021", "t0019"],
        list(brt.DEFAULT_CATEGORIES),
    )
    after = {p: p.read_bytes() for p in fake_experiment.rglob("*") if p.is_file()}
    assert after == before, "the source experiment was modified"


def test_alloy_profiles_are_copied_when_present(fake_experiment, tmp_path):
    out = tmp_path / "bundle"
    brt.build_bundle(fake_experiment, out, ["t0019"], list(brt.DEFAULT_CATEGORIES))
    copied = {p.name for p in (out / "t0019").rglob("*") if p.is_file()}
    assert "output_alloy_composition.dat" in copied
    assert "requested_composition_profile.csv" in copied


def test_a_missing_category_is_named_not_silently_dropped(fake_experiment, tmp_path):
    """t0021 has no alloy output; the manifest must say so."""

    manifest = brt.build_bundle(
        fake_experiment, tmp_path / "bundle", ["t0021"],
        list(brt.DEFAULT_CATEGORIES),
    )
    unavailable = {item["what"] for item in manifest["unavailable"]}
    assert "t0021/alloy-profiles" in unavailable
    assert manifest["trials"]["t0021"]["empty_categories"]


def test_a_missing_trial_is_named(fake_experiment, tmp_path):
    manifest = brt.build_bundle(
        fake_experiment, tmp_path / "bundle", ["t9999"], ["inputs"]
    )
    assert any(item["what"] == "t9999" for item in manifest["unavailable"])


def test_an_experiment_without_raw_output_says_so(tmp_path):
    """A results bundle carries no runs/ -- the exact v3 situation."""

    state = tmp_path / "state"
    state.mkdir()
    (state / "trial_ledger.jsonl").write_text("", encoding="utf-8")
    manifest = brt.build_bundle(state, tmp_path / "out", ["t0021"], ["inputs"])
    assert manifest["runs_directory_present"] is False
    reason = manifest["unavailable"][0]["reason"]
    assert "no raw solver output" in reason
    assert "machine that executed" in reason


def test_the_manifest_records_hashes_of_copied_files(fake_experiment, tmp_path):
    out = tmp_path / "bundle"
    brt.build_bundle(fake_experiment, out, ["t0019"], ["inputs"])
    manifest = json.loads((out / "raw_bundle_manifest.json").read_text(encoding="utf-8"))
    files = manifest["trials"]["t0019"]["files"]
    assert files and all(len(f["sha256"]) == 64 for f in files)


def test_writing_into_a_non_empty_destination_is_refused(fake_experiment, tmp_path):
    out = tmp_path / "bundle"
    out.mkdir()
    (out / "existing.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(brt.BundleError, match="not empty"):
        brt.build_bundle(fake_experiment, out, ["t0019"], ["inputs"])
    brt.build_bundle(fake_experiment, out, ["t0019"], ["inputs"], overwrite=True)
    assert (out / "existing.txt").is_file(), "overwrite must not wipe the directory"


def test_an_unknown_category_is_rejected(fake_experiment, tmp_path):
    with pytest.raises(brt.BundleError, match="unknown category"):
        brt.build_bundle(fake_experiment, tmp_path / "b", ["t0019"], ["nonsense"])


def test_include_all_requires_force(fake_experiment, tmp_path):
    with pytest.raises(SystemExit):
        brt.main([
            "--experiment", fake_experiment.name,
            "--results-root", str(fake_experiment.parent),
            "--include", "all", "--out", str(tmp_path / "b"),
        ])


def test_the_cli_dry_run_exits_zero(fake_experiment, tmp_path, capsys):
    code = brt.main([
        "--experiment", fake_experiment.name,
        "--results-root", str(fake_experiment.parent),
        "--trials", "t0019",
        "--out", str(tmp_path / "b"),
        "--dry-run",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "would copy" in out and "dry run: nothing was written" in out
    assert not (tmp_path / "b").exists()


# ---------------------------------------------------------------------------
# Stage 5 isolation
# ---------------------------------------------------------------------------


def test_stage5_defaults_to_its_own_directory(cfg, tmp_path):
    target = demo13.stage5_state_dir(cfg, tmp_path)
    assert target.name != cfg["workflow"]["experiment_state_dir"]
    assert target.name == "demo13_ax_experiment_v3_stage5"


def test_stage5_pointed_at_the_experiment_is_rejected(cfg):
    bad = copy.deepcopy(cfg)
    bad["validation_study"]["output_state_dir"] = bad["workflow"]["experiment_state_dir"]
    with pytest.raises(demo_workflow.DemoError, match="must not be the optimization"):
        demo13.validate_demo13_config(bad)


def test_the_shipped_configuration_isolates_stage5(cfg, tmp_path):
    demo13.validate_demo13_config(cfg)
    assert (
        demo13.stage5_state_dir(cfg, tmp_path).resolve()
        != (tmp_path / cfg["workflow"]["experiment_state_dir"]).resolve()
    )


def test_stage5_falls_back_safely_when_unconfigured(cfg, tmp_path):
    variant = copy.deepcopy(cfg)
    variant["validation_study"].pop("output_state_dir", None)
    demo13.validate_demo13_config(variant)
    target = demo13.stage5_state_dir(variant, tmp_path)
    assert target.name.endswith("_stage5")
    assert target.name != variant["workflow"]["experiment_state_dir"]
