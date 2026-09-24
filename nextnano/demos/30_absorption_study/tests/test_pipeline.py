"""Quantified comparisons, determinism and isolation of the whole Demo 30 pipeline."""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from demo30 import absorption_study, pipeline
from demo30.paths import DEMO_ROOT, OUTPUTS


def test_strict_vs_tail_and_2x2_vs_expanded_are_quantified(state):
    res = absorption_study.compute(state)
    q = absorption_study.quantify(res, state["cfg"], state)
    for model in absorption_study.MODELS:
        v = q["alpha_I_2w_tail_vs_strict"][model]
        assert v["max_relative_difference_in_window"] > 0
        assert set(v["table"]) == {"1500", "1550", "1560", "1600", "1700"}
    for kind in absorption_study.KINDS:
        assert q["alpha_I_2w_expanded_vs_2x2"][kind]["ratio_min_in_window"] >= 1.0  # more states never absorb less
    assert q["alpha_w_check"]["PASS"]
    assert all(v["PASS"] for v in q["resonance_alignment"].values())
    assert q["plateau_absorption_per_period"]["PASS"]


def _numeric_files(root: Path):
    return sorted(p for p in root.rglob("*") if p.suffix in (".csv", ".npy"))


def test_deterministic_rerun(state, tmp_path):
    pipeline.run_all(tmp_path / "a", make_plots=False)
    pipeline.run_all(tmp_path / "b", make_plots=False)
    files_a = _numeric_files(tmp_path / "a")
    assert len(files_a) > 10
    for fa in files_a:
        fb = tmp_path / "b" / fa.relative_to(tmp_path / "a")
        assert fa.read_bytes() == fb.read_bytes(), fa.name
    npz_a = np.load(tmp_path / "a" / "30B_chi2_baseline" / "chi2_results" / "pathways.npz")
    npz_b = np.load(tmp_path / "b" / "30B_chi2_baseline" / "chi2_results" / "pathways.npz")
    np.testing.assert_array_equal(npz_a["values"], npz_b["values"])


def test_isolation_audit_passes(state):
    """Runs in a subprocess: audit hooks cannot be removed once installed."""
    proc = subprocess.run([sys.executable, str(DEMO_ROOT / "scripts" / "audit_isolation.py")],
                          capture_output=True, text=True, timeout=600)
    report = json.loads((OUTPUTS / "isolation_audit.json").read_text())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert report["status"] == "PASS" and not report["blocked_reads"]


def test_isolation_guard_really_blocks(state):
    code = f"""
import runpy, sys
mod = runpy.run_path(r"{DEMO_ROOT / 'scripts' / 'audit_isolation.py'}", run_name="not_main")
blocked = []
sys.addaudithook(mod["make_guard"](mod["allowed_roots"](), blocked))
open(r"{DEMO_ROOT / 'PLAN.md'}").close()
for forbidden in (r"{DEMO_ROOT.parent / '28_kspace_chi2_study' / 'README.md'}", r"{DEMO_ROOT.parents[2] / 'docs' / 'case_04' / 'case_result.json'}"):
    try:
        open(forbidden)
        print("NOT BLOCKED", forbidden)
    except RuntimeError:
        print("blocked")
"""
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120).stdout
    assert out.split() == ["blocked", "blocked"]
