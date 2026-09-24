"""Focused tests for solver monitoring and read-only diagnostic packaging."""
from pathlib import Path
import json
import sys
import zipfile

from chi2 import run_debug
from chi2 import acquisition
from chi2.acquisition import _monitor_command, check_decks, config, job_decks
from scripts.collect_debug import main as collect_main


def _file(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(root: Path):
    _file(root / "kp8/kp8/bias_00000/QuantumDispersions/acqw/kp8/dispersion_Gamma_to_y.dat",
          "k e1\n0 1.0\n0.25 1.1\n0.5 1.2\n")
    _file(root / "kp8/kp8/bias_00000/QuantumDispersions/acqw/kp8/kVectors_Gamma_to_y.dat",
          "no kx ky kz\n0 0 0 0\n1 0 0.25 0\n2 0 0.5 0\n")
    frame = root / "kp8/kp8/bias_00000/Quantum/acqw/kp8/k00000"
    _file(frame / "spinor_composition_CbHhLhSo.dat", "no cb1 cb2 hh1 hh2 lh1 lh2 so1 so2\n1 1 0 0 0 0 0 0 0\n")
    for state in range(1, 15):
        for component in run_debug.COMPONENTS:
            _file(frame / f"envelope_{state:04d}_{component}.dat", "z real imag\n0 1 0\n1 0 0\n")
    _file(root / "kp8/kp8/bias_00000/job_done.txt", "done\n")
    _file(root / "kp8.log", "nextnano++ 3.0.0 test-build\nlicense key: SECRET-LICENSE-CONTENT\n")
    _file(root / "decks/kp8.in", job_decks(300, config(), pilot_finite_k=True)["kp8"])
    _file(root / "run_metadata.json", json.dumps({"temperature_K": 300, "pilot": True,
                                                   "pilot_kind": "finite_k", "source_config": config()}))
    _file(root / "kp8/kp8/bias_00000/Quantum/acqw/kp8/momentum_unexpected.dat", "x y\n0 1\n")
    return frame


def test_elapsed_and_pilot_deck():
    assert run_debug.elapsed_hms(0) == "00:00:00"
    assert run_debug.elapsed_hms(3671.8) == "01:01:11"
    assert check_decks(config())["finite_k_pilot"]["frame_count"] == "read from k_points.txt after solver run"
    deck = job_decks(300, config(), pilot_finite_k=True)["kp8"]
    assert "num_points = 301" in deck
    assert "point{ k = [0, 0.555714439232, 0] }" in deck
    assert "k_integration_disabled{}" not in deck
    assert "relative_size = 0.03" in deck
    assert "num_points = 5" in deck
    assert "force_k0_subspace = no" in deck
    assert "all_k_points = yes" in deck


def test_frame_discovery_missing_and_unexpected_paths(tmp_path):
    root = tmp_path / "existing"
    _run(root)
    report = run_debug.scan_output(root, expected_frames=3)
    assert report["dispersion"]["points"] == 3
    assert report["frame_identifiers"] == ["k00000"]
    assert report["missing_frames"] == ["k00001", "k00002"]
    assert report["actual_finite_k_state_frames"] == 1
    assert report["complete_state_frames"] == 1
    assert report["parser_recognized_frames"] == ["k00000"]
    assert report["unexpected_file_locations_total"] == 0
    assert any("momentum_unexpected" in path for path in report["relevant_files_ignored_by_parser"])
    assert any(row["relative_path"].endswith("spinor_composition_CbHhLhSo.dat")
               and row["bytes"] > 0 and row["modified_utc"] for row in report["tree"])


def test_debug_zip_manifest_redaction_and_no_raw_data(tmp_path):
    root = tmp_path / "existing"
    _run(root)
    _file(root / "kp8/kp8/bias_00000/Quantum/acqw/kp8/huge_raw.dat", "1 2 3\n" * 100000)
    destination = tmp_path / "reports"
    result = run_debug.collect_debug(root, destination, 300, None, "test_run",
                                     {"git": {"branch": "codex/test", "commit": "abc", "dirty_before_run": False},
                                      "path_checks": {"license_configured_and_exists": True}},
                                     redactions=["SECRET-LICENSE-CONTENT"])
    assert Path(result["zip"]).stat().st_size < 200_000
    with zipfile.ZipFile(result["zip"]) as archive:
        names = archive.namelist()
        assert "run_manifest.json" in names
        assert "output_tree.txt" in names
        assert "finite_k_diagnostic.json" in names
        assert "paths_report.txt" in names
        assert "executed_decks/kp8.in" in names
        assert not any(name.endswith("huge_raw.dat") for name in names)
        combined = b"".join(archive.read(name) for name in names)
        assert b"SECRET-LICENSE-CONTENT" not in combined
        assert b"<REDACTED SENSITIVE LINE>" in combined
        manifest = json.loads(archive.read("run_manifest.json"))
        assert manifest["run_id"] == "test_run"
        assert manifest["git"]["dirty_before_run"] is False
        assert manifest["nextnano_version_build"] == "nextnano++ 3.0.0 test-build"


def test_existing_run_cli_does_not_launch_solver(tmp_path, monkeypatch):
    root = tmp_path / "existing"
    _run(root)
    def forbidden(*args, **kwargs):
        raise AssertionError("No subprocess should launch a solver during diagnosis")
    monkeypatch.setattr(run_debug.subprocess, "Popen", forbidden)
    # Git provenance uses subprocess.run, so give the CLI a harmless fixed state.
    monkeypatch.setattr(run_debug, "git_state", lambda: {"branch": "test", "commit": "abc", "dirty_before_run": False})
    destination = tmp_path / "cli_reports"
    assert collect_main(["--input", str(root), "--temperature", "300",
                         "--output-dir", str(destination)]) == 0
    assert len(list(destination.glob("demo29_300K_debug_*.zip"))) == 1
    assert (root / "kp8.log").read_text(encoding="utf-8").startswith("nextnano++")


def test_monitored_local_process_writes_separate_logs(tmp_path, capsys):
    root = tmp_path / "run"
    root.mkdir()
    record = _monitor_command([sys.executable, "-c", "print('test solver milestone')"],
                              tmp_path / "logs", root, 300, "8-band finite-k pilot",
                              "synthetic process", 49, 5, 0.01)
    assert record["return_code"] == 0
    assert record["pid"] > 0
    assert "test solver milestone" in (tmp_path / "logs/stdout.log").read_text()
    assert "Elapsed:" in capsys.readouterr().out


def test_runner_auto_diagnoses_after_synthetic_job(tmp_path, monkeypatch, capsys):
    demo = tmp_path / "demo29"
    _file(demo / "scripts/audit_dependencies.py", "print('PASS: local audit')\n")
    for name in ("solver.exe", "database.nnp", "license.txt"):
        _file(tmp_path / name, "synthetic fixture\n")
    monkeypatch.setattr(acquisition, "ROOT", demo)
    monkeypatch.setattr(acquisition, "_solver_paths", lambda: {
        "exe": str(tmp_path / "solver.exe"), "database": str(tmp_path / "database.nnp"),
        "license": str(tmp_path / "license.txt")})
    monkeypatch.setattr(run_debug, "git_state", lambda: {
        "branch": "codex/test", "commit": "abc", "dirty_before_run": False})

    def fake_process(command, log_dir, result, t, label, stage, expected_frames, timeout, interval):
        _file(log_dir / "stdout.log", "DONE.\nnextnano++ synthetic test\n")
        _file(log_dir / "stderr.log", "")
        return {"start_utc": "2026-01-01T00:00:00Z", "end_utc": "2026-01-01T00:00:01Z",
                "elapsed_seconds": 1.0, "return_code": 0, "termination_status": "exited",
                "pid": 123, "command": acquisition._redact_command(command)}

    monkeypatch.setattr(acquisition, "_monitor_command", fake_process)
    result = demo / "nextnano/work_runs/pilot_finite_k_300K_test"
    acquisition.run(300, config(), result, pilot_finite_k=True, run_id="synthetic_test")
    logs = demo / "nextnano/run_logs/300K/synthetic_test"
    assert (logs / "runner.log").is_file()
    assert (logs / "run_manifest.json").is_file()
    assert (logs / "paths_report.txt").is_file()
    assert (logs / "finite_k_diagnostic.json").is_file()
    assert (logs / "demo29_300K_debug_synthetic_test.zip").is_file()
    assert "WARNING: target-path coverage incomplete" in capsys.readouterr().out
    manifest = json.loads((logs / "run_manifest.json").read_text())
    assert manifest["execution"]["kp8"]["command"][manifest["execution"]["kp8"]["command"].index("-l") + 1] == "<LICENSE_PATH_REDACTED>"


def test_actual_integration_grid_is_distinct_from_dispersion():
    run = (Path(__file__).resolve().parents[4] / "nextnano_raw" /
           "pilot_finite_k_300K_pilotfk_20260924T184053442360Z_26300" /
           "pilot_finite_k_300K_pilotfk_20260924T184053442360Z_26300")
    if not run.is_dir():
        return  # The licensed data live outside Git and may be absent on WORK.
    report = run_debug.scan_output(run)
    grid = report["integration_grid"]
    assert report["dispersion"]["points"] == 301
    assert grid["points"] == 9
    assert grid["complete_target_path_frames"] == 1
    assert grid["rows"][8]["direction"] == "+y"
    assert grid["rows"][8]["magnitude_per_nm"] > report["dispersion"]["k_max_per_nm"]
