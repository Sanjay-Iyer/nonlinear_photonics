"""The chi2 control reproduces Demo 28A; the lock selects and verifies exact raw data."""
import csv
import json
import shutil

import numpy as np
import pytest

from demo30 import baseline, rawdata
from demo30 import parse_nextnano as io
from demo30.meta import sha256_bytes
from demo30.paths import DEMO_ROOT, REFERENCE


def test_equation2_is_byte_identical_to_demo28():
    assert sha256_bytes(DEMO_ROOT / "demo30" / "equation2.py") == baseline.EQUATION2_SHA256_DEMO28


def test_control_reproduces_demo28A(state):
    reg = baseline.regression(state)
    assert reg["status"] == "PASS", reg["checks"]
    assert reg["checks"]["demo28A_spectrum"]["max_complex_error_pm_per_V"] <= 1e-8
    assert state["inputs"]["k_per_nm"][-1] == pytest.approx(0.1 * np.pi / 0.565325, abs=1e-9)


def test_comparison_A_reproduces_demo28J(state):
    assert baseline.comparison_a(state)["reproduces_demo28J"]


def test_parsers_read_exactly_the_locked_files(state):
    """Uniqueness-checked parser searches land on the files whose hashes the lock pins."""
    kp8, sb = state["runs"]["kp8_dispersion"], state["runs"]["singleband"]
    found = [
        (kp8, [io.find_one(kp8.parser_root, "dispersion_*.dat"), io.find_one(kp8.parser_root, "kp8/energy_spectrum_k00000.dat"),
               io.find_one(kp8.parser_root, "spinor_composition_k00000_CbHhLhSo.dat")]),
        (sb, [io.find_one(sb.parser_root, f"{b}/{f}_k00000.dat") for b in ("Gamma", "HH") for f in ("energy_spectrum", "envelopes")])]
    for run, paths in found:
        for p in paths:
            assert p.relative_to(run.folder).as_posix() in run.entry["files"]


def test_missing_raw_data_fails_with_instructions(tmp_path):
    with pytest.raises(rawdata.RawDataMissing) as err:
        rawdata.resolve_required(root=tmp_path)
    text = str(err.value)
    for needle in ("D020_2026-08-20_sb-case04-graded-300K", "D023_2026-09-04_kp8-disp-k0p10pia-n301-300K",
                   "Google Drive", str(tmp_path / "demo_023"), "raw_data.py register"):
        assert needle in text


def test_modified_raw_data_is_rejected(state, tmp_path):
    run = state["runs"]["singleband"]
    copy = tmp_path / run.entry["expected_dir"]
    shutil.copytree(run.folder, copy)
    assert rawdata.resolve("singleband", root=tmp_path).verified_files == run.verified_files  # a faithful copy passes
    pinned = copy / next(iter(run.entry["files"]))
    pinned.write_bytes(pinned.read_bytes() + b" ")
    with pytest.raises(rawdata.RawDataMismatch, match="hash differs"):
        rawdata.resolve("singleband", root=tmp_path)


def test_failed_status_is_rejected(state, tmp_path):
    run = state["runs"]["singleband"]
    copy = tmp_path / run.entry["expected_dir"]
    shutil.copytree(run.folder, copy)
    record = json.loads((copy / "RUN_RECORD.json").read_text())
    record["status"] = "failed"
    (copy / "RUN_RECORD.json").write_text(json.dumps(record))
    with pytest.raises(rawdata.RawDataMismatch, match="status"):
        rawdata.resolve("singleband", root=tmp_path)


def test_measured_fig2d_digitization_is_complete():
    rows = list(csv.DictReader((REFERENCE / "paper_fig2d_measured.csv").open(encoding="utf-8")))
    assert len(rows) == 33
    expected = [1400, 1500, 1530, 1540, 1550, 1560, 1570, 1580, 1600, 1700, 1800]
    for series in ("80pd_sample", "AlGaAs_control", "GaAs_control"):
        pts = [r for r in rows if r["series"] == series]
        assert [int(r["nominal_wavelength_nm"]) for r in pts] == expected
        assert all(abs(float(r["digitized_wavelength_nm"]) - float(r["nominal_wavelength_nm"])) < 0.5 for r in pts)
        assert all(0 < float(r["normalized_sh_arb"]) < 210 for r in pts)
    sample = {int(r["nominal_wavelength_nm"]): float(r["normalized_sh_arb"]) for r in rows if r["series"] == "80pd_sample"}
    assert max(sample, key=sample.get) == 1560
