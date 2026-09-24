"""30B — the chi2 control: Demo 28A recomputed from the registered raw data.

Physics is unchanged: the copied Eq. 2 engine, the Demo 28A mixed-model inputs (8-band
dispersion shifts + single-band k=0 anchors and envelopes), Gamma = 5 meV, and the
stored k grid to k_max = 0.1·π/a. The output must reproduce Demo 28A to 1e-8 pm/V.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import rawdata
from .artifacts import save_inputs, save_spectrum, write_json
from .config import load_config, settings, wavelength_grid
from .diagnostics import features, paper_metrics
from .equation2 import calculate_chi2, prefactor
from .input_builder import build_inputs
from .meta import run_metadata, sha256_bytes
from .paths import DEMO_ROOT, REFERENCE

EQUATION2_SHA256_DEMO28 = "6f69da8fe002f7954f6f5013712522c9e63445f7aa5e7ac447e608e36283a460"


def control_inputs(runs: dict[str, rawdata.ResolvedRun]):
    """Demo 28A chi2 inputs built from the two verified raw runs."""
    return build_inputs(runs["kp8_dispersion"].parser_root, runs["singleband"].parser_root)


def compute(raw_root=None):
    """Everything later stages need: config, verified runs, inputs, settings, chi2."""
    cfg = load_config()
    runs = rawdata.resolve_required(raw_root)
    inputs, parsed = control_inputs(runs)
    s = settings(cfg)
    wl = wavelength_grid(cfg)
    kmax = float(inputs["k_per_nm"][-1])
    if abs(kmax - cfg["baseline_chi2"]["k_max_per_nm"]) > 1e-9:
        raise ValueError(f"control k grid ends at {kmax} nm^-1, expected 0.1·π/a")
    chi2 = calculate_chi2(wl, inputs, s)
    return {"cfg": cfg, "runs": runs, "inputs": inputs, "parsed": parsed, "settings": s, "wl": wl, "chi2": chi2}


def regression(state: dict) -> dict:
    cfg, wl, chi = state["cfg"], state["wl"], state["chi2"].chi2_complex
    tol = cfg["baseline_chi2"]["reference_tolerance_pm_per_V"]
    ref28 = np.loadtxt(REFERENCE / "demo28A_chi2_spectrum.csv", delimiter=",", skiprows=1)
    ref26 = np.loadtxt(REFERENCE / "demo26_baseline_reference.csv", delimiter=",", skiprows=1)
    checks = {}
    for name, ref, cols in (("demo28A_spectrum", ref28, (2, 3)), ("demo26_reference", ref26, (1, 2))):
        same_grid = np.array_equal(wl, ref[:, 0])
        err = float(np.max(np.abs(chi - (ref[:, cols[0]] + 1j * ref[:, cols[1]])))) if same_grid else None
        checks[name] = {"max_complex_error_pm_per_V": err, "tolerance": tol,
                        "PASS": bool(same_grid and err <= tol)}
    import json
    prior = json.loads((REFERENCE / "prior_condensed_baseline_summary.json").read_text())
    evaluator = lambda w: calculate_chi2(w, state["inputs"], state["settings"]).chi2_complex
    feats = features(wl, chi, evaluator)
    ours = np.array([r["wavelength_nm"] for r in feats["Re_zero_crossings"]])
    theirs = np.array([r["wavelength_nm"] for r in prior["features"]["re_zero_crossings"]])
    zero_err = float(np.max(np.abs(ours - theirs))) if ours.shape == theirs.shape else None
    checks["re_zero_crossings"] = {"ours_nm": ours.tolist(), "reference_nm": theirs.tolist(),
                                   "max_error_nm": zero_err, "tolerance_nm": cfg["baseline_chi2"]["feature_zero_tolerance_nm"],
                                   "PASS": zero_err is not None and zero_err <= cfg["baseline_chi2"]["feature_zero_tolerance_nm"]}
    eq_hash = sha256_bytes(DEMO_ROOT / "demo30" / "equation2.py")
    checks["equation2_unchanged"] = {"sha256": eq_hash, "demo28_sha256": EQUATION2_SHA256_DEMO28,
                                     "PASS": eq_hash == EQUATION2_SHA256_DEMO28}
    r = state["chi2"]
    reint = float(np.max(np.abs(prefactor(state["settings"]) * (r.summed_integrand @ r.k_weights_nm_minus2) - chi)))
    checks["integrand_reintegration"] = {"max_error_pm_per_V": reint, "PASS": reint < 1e-9}
    return {"checks": checks, "features": feats,
            "status": "PASS" if all(c["PASS"] for c in checks.values()) else "FAIL"}


def comparison_a(state: dict) -> dict:
    """Comparison A: chi2 (model) vs the paper's SIMULATED chi2 curve, shape only."""
    cfg, wl, chi = state["cfg"], state["wl"], state["chi2"].chi2_complex
    eye = np.loadtxt(REFERENCE / "paper_fig2d_simulated.csv", delimiter=",", skiprows=1)
    metrics_eye = paper_metrics(wl, chi, eye)
    expected = cfg["baseline_chi2"]["demo28J_paper_nrmse"]
    reproduced = all(abs(metrics_eye[key]["nRMSE"] - expected[key]) <= expected["tolerance"]
                     for key in ("abs_real", "magnitude"))
    traced = np.loadtxt(REFERENCE / "paper_fig2d_simulated_traced.csv", delimiter=",", skiprows=1)
    metrics_traced = paper_metrics(wl, chi, traced)
    return {"eye_45_point_reference": metrics_eye, "demo28J_values": expected,
            "reproduces_demo28J": bool(reproduced), "traced_curve_reference": metrics_traced,
            "note": "Each curve normalized to its own maximum (Demo 28J convention). The model is ~50x smaller "
                    "than the paper in absolute pm/V; see Demo 28 for the prefactor discussion."}


def run(out: Path, raw_root=None) -> dict:
    state = compute(raw_root)
    out = Path(out)
    save_inputs(out / "chi2_inputs", state["inputs"], state["settings"], state["wl"])
    save_spectrum(out / "chi2_results", state["chi2"], save_integrand=False)
    reg = regression(state)
    comp = comparison_a(state)
    meta = run_metadata("30B_chi2_baseline", rawdata.provenance(state["runs"]), {
        "model": state["inputs"]["model"], "k_max_label": "0.1·π/a",
        "k_max_per_nm": float(state["inputs"]["k_per_nm"][-1]), "k_points": len(state["inputs"]["k_per_nm"]),
        "kp8_pair_ids": state["inputs"]["kp8_pair_ids"], "limitations": state["inputs"]["limitations"],
        "regression": reg, "comparison_A": comp,
        "validation_status": "PASS" if reg["status"] == "PASS" and comp["reproduces_demo28J"] else "FAIL"})
    write_json(out / "metadata.json", meta)
    state["meta"] = meta
    return state
