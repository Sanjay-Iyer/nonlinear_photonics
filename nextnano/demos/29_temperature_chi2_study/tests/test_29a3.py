"""29A3 diagnostics and transfer tests use tiny synthetic data, never a solver."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pytest

from chi2.acquisition import check_decks, config, job_decks
from chi2 import run_debug
from chi2.sampling import block_strength, interpolation_diagnostics
from scripts.package_pilot import main as package_main
from scripts.unpack_dense import main as unpack_main


def put(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def dense_fixture(tmp_path: Path) -> tuple[Path, Path]:
    run = tmp_path / "29A3_300K_dense_validation"
    logs = tmp_path / "logs"
    meta = {"temperature_K": 300, "pilot_kind": "dense_finite_k", "run_id": "29A3_test",
            "log_dir": str(logs), "jobs": {"kp8": {"status": "PASS"}}}
    put(run / "run_metadata.json", json.dumps(meta))
    put(run / "decks/kp8.in", job_decks(300, config(), dense_finite_k=True)["kp8"])
    for name in ("runner.log", "run_manifest.json", "paths_report.txt",
                 "finite_k_diagnostic.json", "warnings_errors.txt"):
        put(logs / name, "{}\n" if name.endswith(".json") else "synthetic\n")
    base = run / "kp8/kp8/bias_00000"
    dispersion = np.linspace(0, 0.555714439232, 301)
    put(base / "QuantumDispersions/acqw/kp8/dispersion_Gamma_to_y.dat",
        "k e1\n" + "".join(f"{x:.12f} 1\n" for x in dispersion))
    grid = np.linspace(0, 0.52, 8)
    put(base / "Quantum/acqw/kp8/k_points.txt",
        "no kx ky kz\n" + "".join(f"{i} 0 {x:.12f} 0\n" for i, x in enumerate(grid)))
    for i in range(8):
        frame = base / f"Quantum/acqw/kp8/k{i:05d}"
        put(frame / "spinor_composition_CbHhLhSo.dat", "no cb1 cb2 hh1 hh2 lh1 lh2 so1 so2\n")
        for state in range(1, 15):
            for component in run_debug.COMPONENTS:
                put(frame / f"envelope_{state:04d}_{component}.dat", "z real imag\n0 1 0\n")
        native = base / f"Quantum/acqw/kp8_kp8/k{i:05d}"
        for name in ("dipole_moment_matrix_elements_growth_z.txt",
                     "momentum_matrix_elements_growth_z.txt",
                     "momentum_matrix_elements_inplane_y.txt"):
            put(native / name, "synthetic\n")
    return run, logs


def test_dense_deck_preserves_dispersion_and_changes_only_state_sampling():
    c = config()
    assert check_decks(c)["29A3_dense"]["frame_count"] == "read from k_points.txt after solver run"
    deck = job_decks(300, c, dense_finite_k=True)["kp8"]
    pilot = job_decks(300, c, pilot_finite_k=True)["kp8"]
    assert "num_points = 301" in deck
    assert "point{ k = [0, 0.555714439232, 0] }" in deck
    assert "relative_size = 0.036" in deck and "num_points = 11" in deck
    assert "relative_size = 0.03" in pilot and "num_points = 5" in pilot
    assert "singleband" not in job_decks(300, c, dense_finite_k=True)
    with pytest.raises(ValueError, match="300 K"):
        job_decks(100, c, dense_finite_k=True)


def test_sampling_detects_nonlinear_matrix_and_rotation_invariance():
    k = np.linspace(0, 0.464346, 5)
    smooth = interpolation_diagnostics(k, np.array([.9160, .9155, .9139, .9118, .9096]))
    sharp = interpolation_diagnostics(k, np.array([.9569, .2998, .3852, .2929, .1666]))
    assert smooth["max_linear_relative_error"] < .01
    assert sharp["max_linear_relative_error"] > 1
    assert sharp["nonmonotonic"]
    z = np.zeros((4, 4), complex)
    z[:2, 2:] = [[1, 2j], [3, 4]]
    before = block_strength(z, [1, 2], [3, 4])
    q = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    z[:2, 2:] = q.T @ z[:2, 2:] @ q
    assert block_strength(z, [1, 2], [3, 4]) == pytest.approx(before)


def test_dense_debug_zip_and_full_raw_manifest(tmp_path, monkeypatch):
    run, logs = dense_fixture(tmp_path)
    debug = run_debug.collect_debug(run, tmp_path / "debug", 300, run_id="29A3_test",
                                    stage="29A3")
    assert Path(debug["zip"]).name == "demo29_29A3_300K_debug_29A3_test.zip"
    with zipfile.ZipFile(debug["zip"]) as archive:
        names = set(archive.namelist())
        assert {"k_grid_report.tsv", "state_frame_inventory.tsv", "run_manifest.json"} <= names
        assert not any(name.endswith("envelope_0001_cb1.dat") for name in names)
    # The synthetic solver output is intentionally unphysical; packaging checks
    # file coverage and hashes, while HOME physics analysis reports its error.
    archive = tmp_path / "dense.zip"
    assert package_main(["--input", str(run), "--zip", str(archive), "--dense"]) == 0
    monkeypatch.setattr(sys, "argv", ["unpack_dense", "--zip", str(archive),
                                   "--destination", str(tmp_path / "returned")])
    assert unpack_main() == 0
    returned = tmp_path / "returned" / run.name
    manifest = json.loads((returned / "transfer_manifest.json").read_text())
    assert "runtime_logs/runner.log" in manifest["sha256"]
    assert "config/study.json" in manifest["sha256"]
    name = "decks/kp8.in"
    assert hashlib.sha256((returned / name).read_bytes()).hexdigest() == manifest["sha256"][name]
    assert unpack_main() == 2  # never overwrite a verified raw run
