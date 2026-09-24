"""WORK-laptop package for 0.2·π/a: decks, validation, packaging and the HOME lock entry.

No solver runs here. A SYNTHETIC pilot run folder (test-only; its energies at the
shared nodes are the control's reference values, the rest are made up) exercises
validate -> package -> unzip -> verify -> lock-entry.
"""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import zipfile

import numpy as np
import pytest

from demo30.paths import DEMO_ROOT

KR = runpy.run_path(str(DEMO_ROOT / "work_laptop" / "kmax_run.py"), run_name="kmax_run_test")
REPO = DEMO_ROOT.parents[2]


def test_decks_differ_from_the_control_only_in_the_k_endpoint_and_points():
    plan = json.loads((DEMO_ROOT / "work_laptop" / "run_plan.json").read_text(encoding="utf-8"))
    pilot = (DEMO_ROOT / plan["decks"]["pilot"]["path"]).read_text(encoding="utf-8")
    full = (DEMO_ROOT / plan["decks"]["full"]["path"]).read_text(encoding="utf-8")
    assert "point{ k = [0, 1.111428878464, 0] }" in pilot and "num_points = 7" in pilot
    assert "point{ k = [0, 1.111428878464, 0] }" in full and "num_points = 601" in full
    diff = [(a, b) for a, b in zip(pilot.splitlines(), full.splitlines()) if a != b]
    assert diff == [("                    num_points = 7", "                    num_points = 601")]
    assert "k_integration_disabled{}" in full  # per-k states deliberately not requested, as in the control
    assert abs(float(KR["EXT_KMAX"]) - 0.2 * np.pi / 0.565325) < 1e-12
    for mode in ("pilot", "full"):
        assert plan["decks"][mode]["free_parse_check"]["status"] in ("PASS", "NOT_RUN")


def _fake_pilot(tmp_path: Path, perturb: float = 0.0, return_code: int = 0, flat: bool = False) -> Path:
    ref = json.loads((DEMO_ROOT / "work_laptop" / "control_reference_nodes.json").read_text(encoding="utf-8"))
    folder = tmp_path / "D030_2026-01-01_kp8-disp-k0p20pia-n7-pilot-300K"
    stem = folder / "data" / "k0p20pia_n7_pilot"
    disp_dir = stem / "bias_00000" / "QuantumDispersions" / "acqw" / "kp8"
    q_dir = stem / "bias_00000" / "Quantum" / "acqw" / "kp8"
    disp_dir.mkdir(parents=True)
    q_dir.mkdir(parents=True)
    (stem / "job_done.txt").write_text("done\n")
    (stem / "k0p20pia_n7_pilot.in").write_text((DEMO_ROOT / "work_laptop" / "decks" / "k0p20pia_n7_pilot.in").read_text())
    k = np.arange(7) * float(KR["EXT_KMAX"]) / 6
    base = np.array([ref["nodes"][str(c)]["energies_eV"] for c in (0, 100, 200, 300)])
    energies = np.vstack([base, base[-1] + 0.05 * np.arange(1, 4)[:, None]])  # SYNTHETIC beyond node 3
    if flat:
        energies = np.repeat(base[:1], 7, axis=0)
    energies[2, 0] += perturb
    header = "|k|[1/nm] " + " ".join(f"Band_{i + 1}[eV]" for i in range(14))
    (disp_dir / "dispersion_Gamma_to_y.dat").write_text(
        header + "\n" + "\n".join(" ".join(f"{v:.13f}" for v in [k[i], *energies[i]]) for i in range(7)) + "\n")
    (disp_dir / "kVectors_Gamma_to_y.dat").write_text(
        "no. kx[1/nm] ky[1/nm] kz[1/nm]\n" + "\n".join(f"{i} 0.0 {k[i]:.13f} 0.0" for i in range(7)) + "\n")
    (q_dir / "energy_spectrum_k00000.dat").write_text("no. Energy[eV]\n" + "\n".join(f"{i + 1} {e}" for i, e in enumerate(base[0])) + "\n")
    (q_dir / "spinor_composition_k00000_CbHhLhSo.dat").write_text("no. cb1 cb2 hh1 lh1 lh2 hh2 so1 so2\n1 1 0 0 0 0 0 0 0\n")
    (folder / "solver_log_redacted.txt").write_text("nextnano++ 3.0.0\n[redacted license line]\nDONE.\n")
    (folder / "run_info.json").write_text(json.dumps({
        "run_id": folder.name, "mode": "pilot", "started_utc": "2026-01-01T00:00:00+00:00",
        "finished_utc": "2026-01-01T00:01:00+00:00", "runtime_s": 60, "return_code": return_code, "threads": 4,
        "command": [], "executable_sha256": "x", "database_sha256": "y",
        "deck": "work_laptop/decks/k0p20pia_n7_pilot.in", "deck_sha256": "z"}))
    return folder


def test_validation_passes_for_consistent_finite_k_data(tmp_path):
    report = KR["validate_folder"](_fake_pilot(tmp_path))
    assert report["result"] == "PASS", report["problems"]
    assert report["facts"]["max_abs_energy_difference_vs_control_eV"] < 1e-9


@pytest.mark.parametrize("kwargs,needle", [({"perturb": 1e-3}, "differ from the control"),
                                           ({"return_code": 1}, "return code"),
                                           ({"flat": True}, "28K failure mode")])
def test_validation_catches_bad_runs(tmp_path, kwargs, needle):
    report = KR["validate_folder"](_fake_pilot(tmp_path, **kwargs))
    assert report["result"] == "FAIL" and any(needle in p for p in report["problems"])


def test_package_verifies_at_home_and_yields_a_lock_entry(tmp_path, capsys):
    folder = _fake_pilot(tmp_path / "work")
    KR["validate_folder"](folder)
    KR["package"](type("A", (), {"folder": str(folder)}))
    archive = folder.parent / f"{folder.name}.zip"
    home = tmp_path / "home_raw" / "demo_030"
    with zipfile.ZipFile(archive) as z:
        z.extractall(home)
    unpacked = home / folder.name
    proc = subprocess.run([sys.executable, str(REPO / "nextnano" / "scripts" / "raw_data.py"), "verify", str(unpacked)],
                          capture_output=True, text=True)
    assert proc.returncode == 0 and "PASS" in proc.stdout, proc.stdout + proc.stderr
    capsys.readouterr()
    KR["lock_entry"](type("A", (), {"folder": str(unpacked), "write": False}))
    entry = json.loads(capsys.readouterr().out)["kp8_dispersion_k0p20"]
    assert entry["expected_dir"] == f"demo_030/{folder.name}" and entry["required"] is False
    assert len(entry["files"]) == 4 and entry["deck"]["sha256"]
