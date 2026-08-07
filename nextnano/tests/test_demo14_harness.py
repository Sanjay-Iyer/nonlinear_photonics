"""Demo 14 run harness: logging, failure capture, checkpointing, resume, bundle.

Spec sections 23 and 24. Every failure mode is *caused* here rather than
assumed, because the whole purpose of the harness is to leave usable evidence
when something goes wrong, and that claim is only worth anything if the
evidence has been checked.
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile

import numpy as np
import pytest
import yaml

import bundle14
import campaign14
import demo14
import grading14
import preflight14
import runlog14
import solver14


@pytest.fixture()
def cfg():
    return demo14.load_config()


@pytest.fixture()
def mini(cfg):
    return preflight14.miniature_config(cfg)


def _run(cfg, tmp_path, **kwargs):
    return campaign14.run_campaign(
        cfg, results_root=tmp_path, mock=True, **kwargs
    )


# --- configuration ---------------------------------------------------------


def test_production_config_is_valid_and_defaults_to_real(cfg):
    assert demo14.validate_config(cfg) == []
    assert cfg["workflow"]["mock_solver"] is False, "production must default to REAL"
    assert cfg["chi2"]["mode"] == "absolute"
    assert cfg["optimization"]["target_completed_trials"] == 30
    assert cfg["optimization"]["initialization_trials"] == 10
    assert cfg["optimization"]["bo_trials"] == 20
    assert "abrupt" not in cfg["optimization"]["search_space"]["grading_profile"]["values"]


@pytest.mark.parametrize("mutation,match", [
    ({"optimization": {"bo_trials": 5}}, "must equal"),
    ({"chi2": {"mode": "relative"}}, "absolute"),
    ({"nextnano": {"solver_timeout_seconds": 0}}, "finite"),
])
def test_invalid_configurations_are_refused(cfg, mutation, match):
    import copy

    broken = copy.deepcopy(cfg)
    for section, changes in mutation.items():
        broken[section].update(changes)
    with pytest.raises(demo14.Demo14ConfigError, match=match):
        demo14.validate_config(broken)


def test_abrupt_branch_is_rejected(cfg):
    import copy

    broken = copy.deepcopy(cfg)
    broken["optimization"]["search_space"]["grading_profile"]["values"].append("abrupt")
    with pytest.raises(demo14.Demo14ConfigError, match="abrupt"):
        demo14.validate_config(broken)


# --- run isolation ---------------------------------------------------------


def test_each_run_gets_a_unique_directory_and_never_resumes_implicitly(mini, tmp_path):
    first = _run(mini, tmp_path)
    second = _run(mini, tmp_path)
    assert first["run_directory"] != second["run_directory"]
    assert first["run_id"] != second["run_id"]
    # A second run must start from zero, not continue the first.
    assert second["completed_trials"] == mini["optimization"]["target_completed_trials"]


def test_mock_runs_are_unmistakable(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    assert "MOCK" in root.name
    assert outcome["scientific_valid"] is False
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "mock"
    assert manifest["scientific_valid"] is False
    status = json.loads((root / "RUN_STATUS.json").read_text(encoding="utf-8"))
    assert status["scientific_valid"] is False
    for record in campaign14.read_ledger(runlog14.RunPaths(root)):
        assert record["scientific_valid"] is False


# --- the full run directory ------------------------------------------------


def test_run_directory_contains_every_required_artifact(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    for relative in (
        "manifest.json", "RUN_STATUS.json", "resolved_config.yaml",
        "logs/run.log", "logs/run_debug.log", "logs/warnings.log",
        "logs/errors.log", "logs/events.jsonl", "logs/timing.jsonl",
        "optimization/trial_ledger.jsonl", "optimization/best_so_far.csv",
        "optimization/proposals.csv", "summaries/timing_summary.csv",
        "summaries/DEMO14_RUN_SUMMARY.md",
        "environment/pip_freeze.txt", "environment/git_status.txt",
        "environment/system_info.txt", "environment/packages.json",
    ):
        assert (root / relative).is_file(), f"missing {relative}"


def test_every_trial_directory_is_complete(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    trials = sorted((root / "trials").iterdir())
    assert trials
    for trial in trials:
        for relative in (
            "trial_manifest.json", "trial_result.json", "preflight.json",
            "parameters_requested.yaml", "parameters_realized.yaml",
            "grading_profile.csv", "grading_profile_metadata.json",
            "physics/chi2_summary.json", "qc/constraints.json",
            "nextnano_input/case.in", "logs/stdout.txt", "logs/stderr.txt",
        ):
            assert (trial / relative).is_file(), f"{trial.name} missing {relative}"


def test_the_exact_deck_and_imported_profile_are_preserved(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    for trial in sorted((root / "trials").iterdir()):
        result = json.loads((trial / "trial_result.json").read_text(encoding="utf-8"))
        family = result["parameters"]["grading_profile"]
        deck = (trial / "nextnano_input" / "case.in").read_text(encoding="utf-8")
        directives = "\n".join(
            l for l in deck.splitlines() if not l.lstrip().startswith("#")
        )
        if family == "linear":
            assert "ternary_linear{" in directives
            assert not (trial / "nextnano_input" / "al_profile.dat").is_file()
        else:
            assert "ternary_import{" in directives
            data = trial / "nextnano_input" / "al_profile.dat"
            assert data.is_file(), f"{family} trial has no imported profile"
            rows = [l.split() for l in data.read_text(encoding="utf-8").splitlines() if l.strip()]
            xs = [float(r[0]) for r in rows]
            assert all(b > a for a, b in zip(xs, xs[1:]))


def test_constraints_are_recorded_per_metric_not_as_one_boolean(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    trial = sorted((root / "trials").iterdir())[0]
    constraints = json.loads((trial / "qc" / "constraints.json").read_text(encoding="utf-8"))
    assert "rows" in constraints and len(constraints["rows"]) >= 4
    for row in constraints["rows"]:
        assert {"metric", "value", "bound", "comparison", "passed"} <= set(row)


# --- structured events -----------------------------------------------------


def test_event_journal_covers_the_trial_lifecycle(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    rows = [json.loads(l) for l in
            (root / "logs" / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    kinds = {r["event_type"] for r in rows}
    for required in (
        "RUN_STARTED", "TRIAL_PROPOSED", "PREFLIGHT_STARTED", "PREFLIGHT_PASSED",
        "GEOMETRY_RENDERED", "NEXTNANO_INPUT_WRITTEN", "SOLVER_STARTED",
        "SOLVER_FINISHED", "CHI2_STARTED", "CHI2_FINISHED", "CHECKPOINT_WRITTEN",
        "TRIAL_COMPLETED", "RUN_COMPLETED",
    ):
        assert required in kinds, f"no {required} event"
    for row in rows:
        assert {"timestamp", "run_id", "event_type", "stage", "status"} <= set(row)


# --- failure modes ---------------------------------------------------------


@pytest.mark.parametrize("behaviour,stage", [
    ("nonzero_exit", "solver"),
    ("missing_output", "solver"),
    ("parser_failure", "solver"),
    ("timeout", "solver"),
    ("nan_objective", "chi2"),
])
def test_technical_failure_stops_the_campaign_and_preserves_evidence(
    mini, tmp_path, behaviour, stage
):
    """A pipeline bug must not be proved 29 more times at licensed prices."""

    outcome = _run(mini, tmp_path, mock_plan={"t0000": behaviour})
    assert outcome["status"] == "FAILED"
    assert outcome["technical_failures"] == 1
    assert outcome["completed_trials"] == 0
    assert behaviour in (outcome["stop_reason"] or "") or outcome["stop_reason"]

    root = Path(outcome["run_directory"])
    trial = root / "trials" / "t0000"
    assert trial.is_dir(), "failed-trial directory was deleted"
    result = json.loads((trial / "trial_result.json").read_text(encoding="utf-8"))
    assert result["status"] == "technical_failure"
    assert result["failure_stage"] == stage
    assert result["failure_reason"]
    assert (trial / "logs" / "traceback.txt").is_file()
    assert (trial / "nextnano_input" / "case.in").is_file(), "the deck must survive"
    status = json.loads((root / "RUN_STATUS.json").read_text(encoding="utf-8"))
    assert status["status"] == "FAILED"
    assert status["last_error"]
    assert (root / "summaries" / "DEMO14_FAILURE_SUMMARY.md").is_file()
    assert (root / "logs" / "errors.log").read_text(encoding="utf-8").strip()


def test_a_physical_qc_failure_is_not_a_technical_failure(mini, tmp_path):
    """An infeasible trial is a result; the campaign continues and it counts."""

    outcome = _run(mini, tmp_path, mock_plan={"t0000": "qc_failure"})
    assert outcome["status"] == "COMPLETED"
    assert outcome["technical_failures"] == 0
    assert outcome["completed_trials"] == mini["optimization"]["target_completed_trials"]

    root = Path(outcome["run_directory"])
    result = json.loads(
        (root / "trials" / "t0000" / "trial_result.json").read_text(encoding="utf-8")
    )
    assert result["status"] == "infeasible"
    assert result["feasible"] is False
    assert "physical_qc_valid" in [r["metric"] for r in result["constraints"]["rows"]]


def test_no_objective_is_fabricated_for_a_failed_trial(mini, tmp_path):
    outcome = _run(mini, tmp_path, mock_plan={"t0000": "nan_objective"})
    root = Path(outcome["run_directory"])
    result = json.loads(
        (root / "trials" / "t0000" / "trial_result.json").read_text(encoding="utf-8")
    )
    assert result["objective_pm_per_V"] is None, "a NaN objective must not become a number"
    assert result["status"] == "technical_failure"


def test_solver_stdout_and_stderr_are_captured_separately(mini, tmp_path):
    outcome = _run(mini, tmp_path, mock_plan={"t0000": "nonzero_exit"})
    trial = Path(outcome["run_directory"]) / "trials" / "t0000"
    assert (trial / "logs" / "stdout.txt").is_file()
    assert (trial / "logs" / "stderr.txt").is_file()
    assert "exit 3" in (trial / "logs" / "stderr.txt").read_text(encoding="utf-8")
    assert (trial / "logs" / "stderr.txt").read_text(encoding="utf-8") != (
        trial / "logs" / "stdout.txt"
    ).read_text(encoding="utf-8")


# --- checkpointing and resume ----------------------------------------------


def test_checkpoint_is_written_after_every_trial(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    rows = [json.loads(l) for l in
            (root / "logs" / "events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    checkpoints = [r for r in rows if r["event_type"] == "CHECKPOINT_WRITTEN"
                   and r.get("status") == "ok"]
    assert len(checkpoints) >= mini["optimization"]["target_completed_trials"]


def test_ledger_records_one_line_per_trial(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    records = campaign14.read_ledger(runlog14.RunPaths(Path(outcome["run_directory"])))
    assert len(records) == mini["optimization"]["target_completed_trials"]
    assert [r["trial_index"] for r in records] == list(range(len(records)))


def test_resume_continues_without_duplicating_completed_trials(mini, tmp_path):
    """Crash after trial 1, resume, and finish the budget exactly once."""

    stopped = _run(mini, tmp_path, mock_plan={"t0001": "nonzero_exit"})
    assert stopped["status"] == "FAILED"
    root = Path(stopped["run_directory"])
    before = campaign14.read_ledger(runlog14.RunPaths(root))
    assert len(before) == 2

    resumed = campaign14.run_campaign(
        mini, results_root=tmp_path, mock=True, resume_dir=root
    )
    after = campaign14.read_ledger(runlog14.RunPaths(root))
    assert resumed["run_directory"] == str(root), "resume must not create a new directory"
    assert resumed["run_id"] == stopped["run_id"]
    indices = [r["trial_index"] for r in after]
    assert len(indices) == len(set(indices)), "resume duplicated a trial"
    assert indices == sorted(indices)
    assert len(after) > len(before)


def test_status_file_is_readable_at_every_point(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    status = json.loads(
        (Path(outcome["run_directory"]) / "RUN_STATUS.json").read_text(encoding="utf-8")
    )
    for key in (
        "run_id", "status", "completed_trials", "failed_trials", "rejected_trials",
        "target_completed_trials", "current_best_trial",
        "current_best_objective_pm_per_V", "last_checkpoint",
    ):
        assert key in status, key
    assert status["status"] == "COMPLETED"


# --- provenance ------------------------------------------------------------


def test_manifest_captures_the_scientific_configuration(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    manifest = json.loads(
        (Path(outcome["run_directory"]) / "manifest.json").read_text(encoding="utf-8")
    )
    for key in (
        "run_id", "git_commit", "git_dirty", "packages", "random_seed",
        "resolved_config_sha256", "search_space", "objective", "constraints",
        "target_wavelength_nm", "broadening_meV", "mesh_nm", "r_e_hh_nm",
        "r_e_hh_provenance", "n_wells_per_metre", "nz_mode", "spin_degeneracy",
        "k_parallel", "planned_completed_trials", "final_status",
    ):
        assert manifest.get(key) is not None, f"manifest is missing {key}"
    assert manifest["r_e_hh_nm"] == pytest.approx(0.751)
    assert manifest["n_wells_per_metre"] == pytest.approx(3.3333333e7, rel=1e-6)
    assert "7.51" in manifest["r_e_hh_provenance"]


def test_environment_snapshot_redacts_secrets(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    path = (Path(outcome["run_directory"]) / "environment"
            / "environment_variables_redacted.json")
    env = json.loads(path.read_text(encoding="utf-8"))
    assert env, "no environment recorded"
    for name, value in env.items():
        lowered = name.lower()
        if any(hint in lowered for hint in ("key", "token", "secret", "password")):
            assert value == "<redacted>", f"{name} leaked"


def test_resolved_config_is_written_and_hashed(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    resolved = yaml.safe_load((root / "resolved_config.yaml").read_text(encoding="utf-8"))
    assert resolved["chi2"]["mode"] == "absolute"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["resolved_config_sha256"]) == 64


# --- debug bundle ----------------------------------------------------------


def test_debug_bundle_contains_the_evidence_needed_to_debug(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    archive_path = bundle14.build_debug_bundle(root)
    assert archive_path.is_file()
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        payload = json.loads(archive.read("BUNDLE_MANIFEST.json"))
        contents = archive.read("CONTENTS.md").decode("utf-8")
    for required in (
        "manifest.json", "RUN_STATUS.json", "resolved_config.yaml",
        "logs/run.log", "logs/events.jsonl", "optimization/trial_ledger.jsonl",
        "CONTENTS.md", "raw_output_inventory.json",
    ):
        assert required in names, f"bundle missing {required}"
    assert any(n.endswith("trial_result.json") for n in names)
    assert any(n.endswith("case.in") for n in names), "decks must be in the bundle"
    assert any(n.endswith("grading_profile.csv") for n in names)
    assert payload["scientific_valid"] is False
    assert "MOCK" in contents
    assert "What is NOT included" in contents


def test_bundle_from_a_failed_run_carries_the_traceback(mini, tmp_path):
    outcome = _run(mini, tmp_path, mock_plan={"t0000": "parser_failure"})
    archive_path = bundle14.build_debug_bundle(Path(outcome["run_directory"]))
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        assert any(n.endswith("traceback.txt") for n in names)
        assert "logs/errors.log" in names
        assert any("FAILURE_SUMMARY" in n for n in names)


def test_mock_bundle_filename_is_marked(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    archive_path = bundle14.build_debug_bundle(Path(outcome["run_directory"]))
    assert "MOCK" in archive_path.name


# --- analysis --------------------------------------------------------------


def test_analysis_and_plots_run_from_artifacts_alone(mini, tmp_path):
    import analysis14

    outcome = _run(mini, tmp_path)
    root = Path(outcome["run_directory"])
    assert analysis14.analyze_run(root) == 0
    inventory = json.loads(
        (root / "plots" / "plot_inventory.json").read_text(encoding="utf-8")
    )
    assert inventory["written"], f"no plots written; failures={inventory['failed']}"
    assert inventory["scientific_valid"] is False
    assert (root / "summaries" / "per_family_statistics.csv").is_file()


def test_per_family_statistics_separate_exploration_from_performance(mini, tmp_path):
    import analysis14

    outcome = _run(mini, tmp_path)
    run = analysis14.load_run(Path(outcome["run_directory"]))
    for row in analysis14.per_family_statistics(run["records"]):
        for key in ("number_initialized", "number_bo_selected", "number_completed",
                    "number_feasible", "best_chi2_at_1550_pm_per_V"):
            assert key in row


# --- solver wrapper --------------------------------------------------------


def test_solver_invocation_record_is_complete(mini, tmp_path):
    outcome = _run(mini, tmp_path)
    trial = sorted((Path(outcome["run_directory"]) / "trials").iterdir())[0]
    record = json.loads((trial / "trial_manifest.json").read_text(encoding="utf-8"))
    solver = record["solver"]
    for key in (
        "solver_executable", "solver_argv", "working_directory", "input_path",
        "input_sha256", "imported_files", "solver_started_utc",
        "solver_finished_utc", "solver_elapsed_seconds", "solver_return_code",
        "solver_timed_out", "stdout_path", "stderr_path", "solver_mode",
    ):
        assert key in solver, f"solver record missing {key}"
    assert solver["solver_mode"] == "mock"
    assert len(solver["input_sha256"]) == 64


def test_unknown_mock_behaviour_is_refused():
    with pytest.raises(ValueError, match="unknown mock behaviour"):
        solver14.execute_mock(
            trial_id="t0000", parameters={}, deck=Path("x.in"),
            output_dir=Path("."), logs_dir=Path("."), behaviour="explode",
        )
