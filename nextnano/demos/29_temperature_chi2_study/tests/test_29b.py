"""29B temperature-only deck and guarded transfer checks; no licensed solver."""
import hashlib
import json
from pathlib import Path
import zipfile

import pytest
import numpy as np

from chi2.acquisition import config, job_decks
from chi2 import compare_29b, run_debug, temperature_study


def test_frozen_reference_and_both_temperature_decks():
    record, frozen = temperature_study.reference()
    report = temperature_study.check_decks()
    assert report["status"] == "PASS"
    assert report["reference_raw_verified_here"] is False
    assert hashlib.sha256(frozen.encode()).hexdigest() == record["reference_deck_sha256"]
    for t in (100, 300, 500):
        jobs = job_decks(t, config(), temperature_full8=True)
        assert set(jobs) == {"kp8"}
        assert jobs["kp8"] == temperature_study._temperature_line(frozen, t)
        assert report["decks"][str(t)]["otherwise_byte_identical_to_frozen_300K_deck"]
    assert "relative_size = 0.03" in jobs["kp8"]
    assert "num_points = 5" in jobs["kp8"]
    assert "num_points = 301" in jobs["kp8"]


def test_29b_rejects_solver_or_deck_drift(tmp_path, monkeypatch):
    exe, database = tmp_path / "solver.exe", tmp_path / "database.nnp"
    exe.write_bytes(b"different solver")
    database.write_bytes(b"different database")
    with pytest.raises(ValueError, match="executable differs"):
        temperature_study.check_solver(exe, database)
    run = tmp_path / "29B_100K_full8"
    (run / "decks").mkdir(parents=True)
    (run / "decks/kp8.in").write_text(job_decks(100, config(), temperature_full8=True)["kp8"] + "\n")
    (run / "run_metadata.json").write_text(json.dumps({"temperature_K": 100,
        "pilot_kind": "temperature_full8_finite_k", "jobs": {"kp8": {"status": "PASS"}}}))
    with pytest.raises(ValueError, match="metadata/deck/solver"):
        temperature_study.validate_run(run, 100)


def test_29b_debug_zip_is_compact(tmp_path):
    from test_29a3 import dense_fixture
    run, _ = dense_fixture(tmp_path)
    result = run_debug.collect_debug(run, tmp_path / "debug_29b", 100,
                                     run_id="29B_100K_test", stage="29B")
    assert Path(result["zip"]).name == "demo29_29B_100K_debug_29B_100K_test.zip"
    with zipfile.ZipFile(result["zip"]) as archive:
        names = set(archive.namelist())
        assert {"executed_decks/kp8.in", "k_grid_report.tsv", "state_frame_inventory.tsv",
                "run_manifest.json"} <= names
        assert not any(name.endswith("envelope_0001_cb1.dat") for name in names)


def test_29b_home_comparison_writes_electronic_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(compare_29b.temperature_study, "check_decks", lambda root: {"status": "PASS"})
    monkeypatch.setattr(compare_29b.temperature_study, "validate_run", lambda root, t: {"status": "PASS"})
    z = np.array([0., 1.])
    psi = np.eye(16, dtype=complex)[:14].reshape(14, 8, 2)
    monkeypatch.setattr(compare_29b, "_k0_spinors", lambda root: (psi, {"z": z}))

    def synthetic_analysis(root, output):
        t = int(root.name[:3])
        (output / "matrix_blocks").mkdir(parents=True)
        labels = {}
        seeds = {"e1": 5, "e2": 6, "hh1": 2, "hh2": 0}
        for label, pair in seeds.items():
            labels[label] = {"solver_states": [2*pair+1, 2*pair+2],
                             "pair_energy_eV": (3.0 if label.startswith("e") else 1.4) + t/10000,
                             "character": {"CB": 1.0 if label.startswith("e") else 0.0,
                                           "HH": 0.0 if label.startswith("e") else 1.0,
                                           "LH": 0.0, "SO": 0.0},
                             "well_fraction": .9, "subspace_overlap": .9,
                             "next_best_overlap": .1, "solver_pair_reassigned_from_k0": False,
                             "flag": False}
        frames = []
        for i, k in enumerate((0., .1)):
            frame = {"id": f"k{i:05d}", "ky_per_nm": k, "labels": labels,
                     "native_tables": {"growth_dipole_e_nm": {"finite": True,
                         "max_abs": 1., "e1_e2_block": .2, "hh1_hh2_block": .3}}}
            frames.append(frame)
            np.savez(output / "matrix_blocks" / f"k{i:05d}.npz",
                     z_matrix_nm=np.ones((14, 14)))
        return {"temperature_K": t, "k0_selection": {"selected": seeds},
                "frames": frames, "native_growth_dipole_offdiagonal_max_abs_difference_nm": 0.0}

    monkeypatch.setattr(compare_29b, "analyze", synthetic_analysis)
    roots = {t: tmp_path / f"{t}K" for t in (100, 300, 500)}
    output = tmp_path / "comparison_output"
    summary = compare_29b.compare(roots, output)
    assert summary["status"] == "PASS"
    assert summary["cross_temperature_k0_subspace_match"][100]["hh2"]["consistent"]
    assert (output / "comparison/selected_states_vs_temperature.csv").is_file()
    assert (output / "comparison/transitions_vs_temperature.csv").is_file()
    assert (output / "comparison/position_blocks_vs_k.png").is_file()
    assert not any(p.name.endswith("chi2.csv") for p in output.rglob("*"))
