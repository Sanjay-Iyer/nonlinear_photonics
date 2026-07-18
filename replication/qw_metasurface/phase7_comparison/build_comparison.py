"""Phase 7 - assemble the three-way comparison table from phase checkpoints.

Reads the latest checkpoint JSON from each phase and emits comparison.csv plus a
Markdown table for REPORT.md. Paper reference values come from paper_params.yaml.

Usage:
  python build_comparison.py --config ../config/paper_params.yaml
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import load_config

ROOT = Path(__file__).resolve().parents[1]


def latest(phase_dir, pattern):
    cands = sorted((ROOT / phase_dir / "checkpoints").glob(pattern),
                   key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def load_json(ckpt, name):
    if ckpt is None:
        return None
    p = ckpt / name
    return json.load(open(p, encoding="utf-8")) if p.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)

    p2 = load_json(latest("phase2_aestimo", "ckpt_*x0p550*"), "analysis.json")
    p3 = load_json(latest("phase3_kdotpy", "ckpt_*kdotpy*"), "analysis.json")
    p4 = load_json(latest("phase4_chi2", "ckpt_*chi2_spectrum*"), "summary.json")
    p4s = load_json(latest("phase4_chi2", "ckpt_*sensitivity*"), "sensitivity.json")
    p5 = load_json(latest("phase5_metasurface", "ckpt_*_full*"), "full_results.json")
    p5e = load_json(latest("phase5_metasurface", "ckpt_*effective*"), "effective_enhancement.json")
    p6 = load_json(latest("phase6_bnn", "ckpt_*bnn_trained*"), "bnn_results.json")

    def g(d, *keys, default=None):
        for k in keys:
            if d is None:
                return default
            d = d.get(k) if isinstance(d, dict) else None
        return d if d is not None else default

    a_e22_ideal = g(p2, "variants", "ideal", "E22_eV")
    a_e22_graded = g(p2, "variants", "graded", "E22_eV")
    k_e22 = g(p3, "kdotpy", "E22_eV")
    bnn_e22 = g(p6, "nominal_prediction", "E22_eV", "mean")
    bnn_e22_s = g(p6, "nominal_prediction", "E22_eV", "sigma")

    a_peak_lam = g(p4, "aestimo_graded", "peak_pump_nm")
    k_peak_lam = g(p4, "kdotpy_graded", "peak_pump_nm")
    bnn_peaklam = g(p6, "nominal_prediction", "chi2_peak_wavelength_nm", "mean")

    a_chi_157 = g(p4, "aestimo_graded", "coherent_at_1570nm_nm_per_V")
    k_chi_157 = g(p4, "kdotpy_graded", "coherent_at_1570nm_nm_per_V")
    a_chi_peak = g(p4, "aestimo_graded", "coherent_peak_nm_per_V")
    a_echan = g(p4, "aestimo_graded", "electron_channel_peak_nm_per_V")
    bnn_chi = g(p6, "nominal_prediction", "chi2_peak_nm_per_V", "mean")
    bnn_chi_s = g(p6, "nominal_prediction", "chi2_peak_nm_per_V", "sigma")

    gmrB = g(p5, "resonance_B", "lambda0_nm")
    Q = g(p5, "resonance_B", "Q")
    enh57_eff = g(p5e, "effective_ExEz_vs_45deg")
    enh115_eff = g(p5e, "effective_ExEz_vs_normal_ExEx")
    chi_ms = g(p5e, "chi2_eff_MQW_plus_MS_effective_nm_per_V")

    def f(v, nd=3):
        return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "-"

    def pm(m, s, nd=3):
        if not isinstance(m, (int, float)):
            return "-"
        return f"{m:.{nd}f} ± {s:.{nd}f}" if isinstance(s, (int, float)) else f"{m:.{nd}f}"

    rows = [
        ["Quantity", "Paper (exp)", "Paper (sim)", "aestimo", "kdotpy", "BNN (mean ± σ)"],
        ["E(HH2→CB2) [eV]", "~1.58 (inferred)", "~1.62 (Ref38)",
         f"{f(a_e22_ideal)} / {f(a_e22_graded)} (ideal/graded)", f(k_e22), pm(bnn_e22, bnn_e22_s)],
        ["χ² peak λ_pump [nm]", "~1570", "~1500",
         f(a_peak_lam, 0), f(k_peak_lam, 0), pm(bnn_peaklam, None, 0)],
        ["χ²_eff,MQW @1.57µm [nm/V] (coherent)", "1.6", "~2.7 peak / 1.183 film-avg",
         f(a_chi_157), f(k_chi_157), pm(bnn_chi, bnn_chi_s)],
        ["χ²_eff,MQW electron-channel [nm/V] (diagnostic)", "-", "-", f(a_echan, 2), "-", "-"],
        ["GMR B λ [nm]", "1567", "1580", f(gmrB, 0), "n/a", "n/a"],
        ["Q factor", "1124", "-", f(Q, 0), "n/a", "n/a"],
        ["ExEz enhancement vs 45° (effective)", "~57×", "-", f(enh57_eff, 0) + "×", "n/a", "n/a"],
        ["ExEz vs normal ExEx (effective)", "~11.5×", "-", f(enh115_eff, 0) + "×", "n/a", "n/a"],
        ["χ²_eff,MQW+MS [nm/V]", "≈14 (17 uncorr.)", "-", f(chi_ms, 2), "n/a", "n/a"],
    ]

    out = ROOT / "phase7_comparison" / "results"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "comparison.csv", "w", newline="", encoding="utf-8") as fcsv:
        csv.writer(fcsv).writerows(rows)

    md = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    md = md.split("\n")
    md.insert(1, "|" + "---|" * len(rows[0]))
    md = "\n".join(md)
    (out / "comparison.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\n[phase7] wrote {out}/comparison.csv and comparison.md")


if __name__ == "__main__":
    main()
