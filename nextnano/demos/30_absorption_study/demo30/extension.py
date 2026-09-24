"""30F — optional k extension beyond the 0.1·π/a control, using only real solved k states.

Existing data reach 0.125·π/a: D023_..._k0p125pia, whose deck differs from the control deck
ONLY in the k endpoint. This stage recomputes the whole chain on that run with everything
else held fixed: the same single-band run, Eq. 2, Gamma, chi1 construction, background
index and samples. It reports:

- the analytical-tail check: 0.1·π/a strict + analytical tail vs 0.125·π/a strict
  (real k states), where the 0.125·π/a result is not itself truncated;
- the chi2 / SH-peak / Fig. 2d-metric changes from 0.1·π/a to 0.125·π/a.

A 0.2·π/a comparison needs data this repository does not register yet. See
work_laptop/README.md and RESULTS.md (30F) for the two routes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import absorption as ab
from . import absorption_study, comparison, propagation_study, rawdata
from .artifacts import write_json
from .equation2 import calculate_chi2
from .input_builder import build_inputs
from .meta import run_metadata, write_csv


def state_for_kp8_run(control: dict, kp8_run: rawdata.ResolvedRun) -> dict:
    """The control state with ONLY the 8-band dispersion run swapped."""
    inputs, parsed = build_inputs(kp8_run.parser_root, control["runs"]["singleband"].parser_root)
    if inputs["kp8_pair_ids"] != control["inputs"]["kp8_pair_ids"]:
        raise ValueError("the extended run assigns different 8-band pairs than the control")
    chi2 = calculate_chi2(control["wl"], inputs, control["settings"])
    runs = {**control["runs"], "kp8_dispersion": kp8_run}
    return {**control, "runs": runs, "inputs": inputs, "parsed": parsed, "chi2": chi2}


EXTENSIONS = {"kp8_dispersion_k0p125": "0.125·π/a", "kp8_dispersion_k0p20": "0.2·π/a"}


def run(control: dict, control_absorption: dict, control_comparison: dict, out: Path, raw_root=None) -> dict:
    """Every extension run present in the lock and on disk; absent ones are reported, never faked."""
    out = Path(out)
    lock = rawdata.load_lock()
    results, statuses = {}, {}
    for role, label in EXTENSIONS.items():
        if role not in lock["runs"]:
            statuses[label] = "NOT IN LOCK (no data yet; see work_laptop/README.md)"
            continue
        try:
            ext_run = rawdata.resolve(role, lock, raw_root)
        except rawdata.RawDataMissing as exc:
            statuses[label] = f"SKIPPED: {str(exc).splitlines()[0]}"
            continue
        results[label] = run_one(control, control_absorption, control_comparison, ext_run, label,
                                 out / label.replace("·π/a", "pia").replace(".", "p"))
        statuses[label] = results[label]["meta"]["validation_status"]
    meta = run_metadata("30F_k_extension", rawdata.provenance(control["runs"]), {
        "extensions": statuses, "results": {label: r["meta"]["summary"] for label, r in results.items()},
        "validation_status": "PASS" if all(v == "PASS" for v in statuses.values() if not v.startswith(("NOT", "SKIP"))) else "FAIL"})
    write_json(out / "metadata.json", meta)
    return {"meta": meta, "results": results}


def run_one(control: dict, control_absorption: dict, control_comparison: dict, ext_run, label: str, out: Path) -> dict:
    ext = state_for_kp8_run(control, ext_run)
    ares = absorption_study.compute(ext)
    pres = propagation_study.run(ext, ares, out / "0p125pia_propagation")
    eres = comparison.run(ext, ares, pres, out / "0p125pia_comparison")
    wl = ares["wavelength_nm"]
    # analytical-tail check: 0.1·π/a strict + tail vs 0.125·π/a strict (real k states)
    lo = max(ares["validity_min_fundamental_nm"], ares["strict_trust"]["min_fundamental_nm"])
    win = (wl >= lo) & (wl <= 1800.0)
    tail_check = {}
    for model in absorption_study.MODELS:
        ctrl_tail = control_absorption["alpha_I_2w"][f"{model}__tail"]
        ctrl_strict = control_absorption["alpha_I_2w"][f"{model}__strict"]
        ext_strict = ares["alpha_I_2w"][f"{model}__strict"]
        rel_tail = (ctrl_tail - ext_strict) / ext_strict
        rel_strict = (ctrl_strict - ext_strict) / ext_strict
        region = win & (wl < control_absorption["strict_trust"]["min_fundamental_nm"])  # where 0.1·π/a strict is truncated
        significant = win & (ext_strict > 0.1 * np.max(ext_strict[win]))  # ignore the tiny far Lorentzian tails
        tail_check[model] = {
            "window_nm": [float(wl[win][0]), float(wl[win][-1])],
            "significant_absorption_nm": [float(wl[significant][0]), float(wl[significant][-1])],
            "max_abs_rel_diff_tail0p10_vs_strict0p125__significant": float(np.max(np.abs(rel_tail[significant]))),
            "max_abs_rel_diff_strict0p10_vs_strict0p125__significant": float(np.max(np.abs(rel_strict[significant]))),
            "in_truncated_region_nm": [float(wl[region][0]), float(wl[region][-1])] if region.any() else None,
            "in_truncated_region__tail0p10_rel_diff_max": float(np.max(np.abs(rel_tail[region]))) if region.any() else None,
            "in_truncated_region__strict0p10_rel_diff_max": float(np.max(np.abs(rel_strict[region]))) if region.any() else None,
            "at_nm": {f"{x:.0f}": {"tail_0p10_cm-1": float(ab.per_cm(ctrl_tail[i])), "strict_0p125_cm-1": float(ab.per_cm(ext_strict[i])),
                                   "strict_0p10_cm-1": float(ab.per_cm(ctrl_strict[i]))}
                      for x in (1450.0, 1470.0, 1500.0, 1550.0, 1600.0) for i in [int(np.argmin(np.abs(wl - x)))] if win[i]}}
    chi_c, chi_e = control["chi2"].chi2_complex, ext["chi2"].chi2_complex
    m = (wl >= 1400) & (wl <= 1800)
    i1550 = int(np.argmin(np.abs(wl - 1550.0)))
    delta = {"peak_abs_chi2_nm": {"0.1·π/a": float(wl[m][np.argmax(np.abs(chi_c[m]))]),
                                  label: float(wl[m][np.argmax(np.abs(chi_e[m]))])},
             "chi2_at_1550nm_pm_per_V": {"0.1·π/a": [float(chi_c[i1550].real), float(chi_c[i1550].imag)],
                                          label: [float(chi_e[i1550].real), float(chi_e[i1550].imag)]},
             "comparison_B_metrics": {"0.1·π/a": control_comparison["meta"]["metrics_at_measured_points"],
                                      label: eres["meta"]["metrics_at_measured_points"]},
             "sh_peaks_nm": {"0.1·π/a": control_comparison["meta"]["peak_wavelengths_nm"],
                             label: eres["meta"]["peak_wavelengths_nm"]}}
    write_csv(out / "alpha_I_2w_tail_check.csv",
              ["wavelength_nm", "in_window", "strict_0p10_cm-1__2x2", "tail_0p10_cm-1__2x2", "strict_0p125_cm-1__2x2",
               "strict_0p10_cm-1__expanded", "tail_0p10_cm-1__expanded", "strict_0p125_cm-1__expanded"],
              [wl, win.astype(float)] + [ab.per_cm(d["alpha_I_2w"][f"{mdl}__{kind}"])
                                         for mdl in absorption_study.MODELS
                                         for d, kind in ((control_absorption, "strict"), (control_absorption, "tail"), (ares, "strict"))])
    meta = run_metadata("30F_k_extension", rawdata.provenance(ext["runs"]), {
        "extension_run": ext_run.run_id, "k_max_label": label, "k_max_per_nm": float(ext["inputs"]["k_per_nm"][-1]),
        "held_fixed": "single-band run, Eq. 2, Gamma, chi1 construction, background index, samples, windows",
        "tail_check": tail_check, "control_vs_extension": delta, "strict_trust_limit": ares["strict_trust"],
        "validation_status": "PASS"})
    meta["summary"] = {"run_id": ext_run.run_id, "tail_check": tail_check, "control_vs_extension": delta}
    write_json(out / "metadata.json", meta)
    return {"meta": meta, "state": ext, "absorption": ares}
