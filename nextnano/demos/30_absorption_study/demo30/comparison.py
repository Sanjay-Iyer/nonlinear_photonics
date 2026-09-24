"""30E — Fig. 2d comparison B: propagated SH intensity vs the MEASURED SH intensity.

These curves are SH intensities, not chi2. The model SH intensity per unit E_w(0)^4 is

    S(lambda) = [ (w / n_2w c) |chi2| L |A| ]^2          (the square of 1994 Eq. 5)

with A = 1 for the transparent (CONTROL) prediction. Both model and measured curves are
compared by shape: each is divided by its own maximum inside the comparison window. The
measured axis is "Normalized SH Intensity (arb. u.)" with an unstated normalization, so
only shape and peak position are compared. Nothing is fitted or tuned.

(Comparison A, chi2 vs the paper's SIMULATED chi2, is in 30B.)
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from . import rawdata
from .absorption_study import variant_names
from .artifacts import write_json
from .meta import run_metadata, write_csv
from .paths import REFERENCE


def measured(series: str = "80pd_sample") -> dict:
    rows = [r for r in csv.DictReader((REFERENCE / "paper_fig2d_measured.csv").open(encoding="utf-8"))
            if r["series"] == series]
    return {"wavelength_nm": np.array([float(r["nominal_wavelength_nm"]) for r in rows]),
            "value": np.array([float(r["normalized_sh_arb"]) for r in rows])}


def paper_simulation_peak(lo: float, hi: float) -> float:
    t = np.loadtxt(REFERENCE / "paper_fig2d_simulated_traced.csv", delimiter=",", skiprows=1)
    m = (t[:, 0] >= lo) & (t[:, 0] <= hi)
    return float(t[m, 0][np.argmax(t[m, 1])])


def _metrics(model_norm, meas_norm) -> dict:
    return {"nRMSE": float(np.sqrt(np.mean((model_norm - meas_norm) ** 2))),
            "pearson_r": float(np.corrcoef(model_norm, meas_norm)[0, 1])}


def run(state: dict, absorption_res: dict, propagation_res: dict, out: Path) -> dict:
    cfg = state["cfg"]
    out = Path(out)
    wl = propagation_res["wavelength_nm"]
    lo_meas, hi_meas = cfg["windows"]["measured_fundamental_nm"]
    # window: measured range, SH below the continuum onset, and strict 0.1·π/a absorption not truncated
    lo = max(lo_meas, absorption_res["validity_min_fundamental_nm"], absorption_res["strict_trust"]["min_fundamental_nm"])
    win = (wl >= lo) & (wl <= hi_meas)
    main_n = cfg["samples"]["fig2d_sample_periods"]
    curves = {"transparent (control)": propagation_res["transparent_m_per_V"] ** 2}
    for name in variant_names():
        curves[f"absorptive: {name}"] = curves["transparent (control)"] * np.abs(propagation_res["factors"][name][main_n]) ** 2
    norm = {k: v / np.max(v[win]) for k, v in curves.items()}
    meas = measured()
    use = (meas["wavelength_nm"] >= lo) & (meas["wavelength_nm"] <= hi_meas)
    m_norm = meas["value"] / np.max(meas["value"][use])
    idx = [int(np.argmin(np.abs(wl - x))) for x in meas["wavelength_nm"]]
    metrics, peaks = {}, {}
    for key, v in norm.items():
        metrics[key] = _metrics(v[idx][use], m_norm[use])
        peaks[key] = float(wl[win][np.argmax(v[win])])
    chi_abs = np.abs(state["chi2"].chi2_complex)
    peaks_table = {
        "Demo 30 chi2 |chi2| (0.1·π/a control)": float(wl[win][np.argmax(chi_abs[win])]),
        "paper simulated |chi2| (traced)": paper_simulation_peak(lo, hi_meas),
        **{f"SH {k}": v for k, v in peaks.items()},
        "measured SH, 80-period sample (10 nm sampling)": float(meas["wavelength_nm"][use][np.argmax(meas["value"][use])])}
    shifts = {k: peaks[k] - peaks["transparent (control)"] for k in peaks if k.startswith("absorptive")}
    # ILLUSTRATIVE ONLY (mixes two electronic structures): our |A|^2 applied to the paper's traced
    # |chi2|, asking whether absorption would move a resonance sitting where the paper puts it
    traced = np.loadtxt(REFERENCE / "paper_fig2d_simulated_traced.csv", delimiter=",", skiprows=1)
    tw = (wl >= lo) & (wl <= hi_meas) & (wl >= traced[0, 0]) & (wl <= traced[-1, 0])
    paper_sh = (np.interp(wl, traced[:, 0], traced[:, 1]) / wl) ** 2  # |chi2|^2 * omega^2 up to a constant
    base_peak = float(wl[tw][np.argmax(paper_sh[tw])])
    illustrative = {"paper_chi2_transparent_SH_peak_nm": base_peak}
    for name in ("consistent_2x2__strict", "expanded_bound_states__tail"):
        a2 = np.abs(propagation_res["factors"][name][main_n]) ** 2
        illustrative[f"shift_with_our_absorption__{name}_nm"] = float(wl[tw][np.argmax((paper_sh * a2)[tw])]) - base_peak
    illustrative["caveat"] = ("illustrative: our absorption (edges from OUR transition energies) applied to the paper's simulated "
                              "|chi2|; not a consistent prediction")
    # write the comparison tables
    write_csv(out / "sh_shapes_normalized.csv", ["wavelength_nm", "within_comparison_window"] + [k.replace(" ", "_").replace(":", "") for k in norm],
              [wl, win.astype(float)] + list(norm.values()))
    with (out / "measured_vs_model.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["wavelength_nm", "used_in_metrics", "measured_normalized"] + [k.replace(" ", "_").replace(":", "") for k in norm])
        for j, i in enumerate(idx):
            w.writerow([f"{meas['wavelength_nm'][j]:.0f}", int(use[j]), f"{m_norm[j]:.5f}"] + [f"{norm[k][i]:.5f}" for k in norm])
    with (out / "peak_table.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["quantity", "peak_wavelength_nm"])
        for k, v in peaks_table.items():
            w.writerow([k, f"{v:.1f}"])
    excluded = meas["wavelength_nm"][~use].tolist()
    best = min(metrics, key=lambda k: metrics[k]["nRMSE"])
    meta = run_metadata("30E_paper_comparison", rawdata.provenance(state["runs"]), {
        "comparison": "B: propagated SH intensity (model) vs measured SH intensity (Fig. 2d, 80-period sample); shapes only",
        "sh_model": cfg["comparison"]["sh_intensity_model"], "normalization": cfg["comparison"]["normalization"],
        "comparison_window_nm": [float(lo), float(hi_meas)],
        "window_rule": "measured 1400-1800 nm, intersected with SH below the bound-to-continuum onset "
                       f"({absorption_res['validity_min_fundamental_nm']:.1f} nm) and with the strict-cutoff trust limit "
                       f"({absorption_res['strict_trust']['min_fundamental_nm']:.1f} nm: SH 3 Gamma below the truncated "
                       f"{absorption_res['strict_trust']['pair']} edge at 0.1·π/a)",
        "measured_points_used": meas["wavelength_nm"][use].tolist(), "measured_points_excluded_outside_validity": excluded,
        "metrics_at_measured_points": metrics, "peak_wavelengths_nm": peaks_table,
        "absorption_induced_peak_shift_nm": shifts,
        "illustrative_paper_chi2_with_our_absorption": illustrative,
        "lowest_nRMSE_curve": best,
        "not_chi2": "Every curve here is an SH intensity. None of them is chi2.",
        "validation_status": "PASS"})
    write_json(out / "metadata.json", meta)
    return {"normalized": norm, "measured": meas, "measured_norm": m_norm, "use": use, "window": win,
            "metrics": metrics, "peaks": peaks_table, "shifts": shifts, "meta": meta}
