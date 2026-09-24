"""Boss-ready Demo 30 figure: can absorption explain the calculated vs measured Fig. 2d resonance?

Draws ONLY from saved, validated Demo 30 outputs; no physics is recomputed:

- outputs/summary.json: stage status, peak wavelengths, |A|^2 at 1550 nm;
- outputs/30E_paper_comparison/sh_shapes_normalized.csv: SH shapes, each normalized to its own maximum;
- outputs/30E_paper_comparison/measured_vs_model.csv: measured Fig. 2d points, normalized;
- outputs/30D_propagation/absorption_factor.csv: |A|^2 for the 80-period sample.

It writes plots/30_boss_absorption_comparison.png. It refuses to draw if a required stage is
not PASS, or if the outputs are stale (the check behind `scripts/run_demo30.py --check-stale`).

This file sits outside scripts/ on purpose: the stale check hashes demo30/*.py and
scripts/*.py, and this figure produces none of the 30A-30F outputs.

    python nextnano/demos/30_absorption_study/presentation/make_boss_figure.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT / "scripts"))
from run_demo30 import check_stale  # noqa: E402

OUTPUTS = DEMO_ROOT / "outputs"
FIGURE = DEMO_ROOT / "plots" / "30_boss_absorption_comparison.png"
PRIMARY = "consistent_2x2__strict"  # 2 conduction x 2 heavy-hole states, stored k <= 0.1·π/a
PERIODS = "80"

# entity colors of demo30/plotting.py: blue = no absorption, orange = with absorption, black = measured
BLUE, ORANGE, INK, INK2, GRID, SHADE = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#dddcd7", "#f0efec"


def read_csv(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {key: np.array([float(r[key]) for r in rows]) for key in rows[0]}


def load() -> tuple[dict, dict, dict, dict]:
    summary = json.loads((OUTPUTS / "summary.json").read_text(encoding="utf-8"))
    failed = {k: v for k, v in summary["status"].items() if "optional" not in k and v != "PASS"}
    if failed:
        raise SystemExit(f"refusing to draw: stages not PASS: {failed}")
    if check_stale() != 0:
        raise SystemExit("refusing to draw from stale outputs; rerun scripts/run_demo30.py first")
    shapes = read_csv(OUTPUTS / "30E_paper_comparison" / "sh_shapes_normalized.csv")
    measured = read_csv(OUTPUTS / "30E_paper_comparison" / "measured_vs_model.csv")
    factor = read_csv(OUTPUTS / "30D_propagation" / "absorption_factor.csv")
    if not np.array_equal(shapes["wavelength_nm"], factor["wavelength_nm"]):
        raise SystemExit("30D and 30E wavelength grids differ")
    return summary, shapes, measured, factor


def style(ax, ylabel: str, title: str) -> None:
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=INK2, labelsize=10)
    ax.set_ylabel(ylabel, color=INK, fontsize=10.5)
    ax.set_title(title, color=INK, fontsize=11.5, loc="left", fontweight="bold", pad=8)


def main() -> int:
    summary, shapes, measured, factor = load()
    wl = shapes["wavelength_nm"]
    win = shapes["within_comparison_window"] == 1  # the 30E comparison window, 1492.7-1800 nm
    trust_nm = summary["comparison_B"]["window_nm"][0]
    peaks = summary["comparison_B"]["peaks_nm"]
    calc_nm = peaks["SH transparent (control)"]
    meas_nm = peaks["measured SH, 80-period sample (10 nm sampling)"]
    if any(abs(v - calc_nm) > 1.0 for k, v in peaks.items() if k.startswith("SH absorptive")):
        raise SystemExit("an absorption variant moves the peak by more than 1 nm; the labels below would be wrong")
    at1550 = {k: v[PERIODS] for k, v in summary["A2_table"]["1550"].items() if k != "within_validity_window"}

    x0, x1 = 1390, 1810
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(9, 8.2), sharex=True, dpi=200,
                                      gridspec_kw={"height_ratios": [1.55, 1]})
    for ax in (top, bottom):
        ax.axvspan(x0, trust_nm, color=SHADE, lw=0, zorder=0)

    # A: where is the peak? (shapes, each normalized to its own maximum)
    top.plot(wl[win], shapes["transparent_(control)"][win], color=BLUE, lw=2.2, label="Calculated, no absorption")
    top.plot(wl[win], shapes[f"absorptive_{PRIMARY}"][win], color=ORANGE, lw=2.2, ls=(0, (4, 2)),
             label="Calculated, with absorption")
    top.plot(measured["wavelength_nm"], measured["measured_normalized"], "s", ms=7, color=INK, zorder=5,
             label="Measured (Fig. 2d, 80-period sample)")
    for x in (calc_nm, meas_nm):
        top.axvline(x, color=INK2, lw=1.0, ls=(0, (1, 2)), zorder=1)
    top.annotate("", xy=(calc_nm, 1.075), xytext=(meas_nm, 1.075),
                 arrowprops=dict(arrowstyle="<->", color=INK2, lw=1.0, shrinkA=0, shrinkB=0))
    top.text((calc_nm + meas_nm) / 2, 1.09, f"{meas_nm - calc_nm:.0f} nm", ha="center", va="bottom", fontsize=10, color=INK)
    top.text(calc_nm - 4, 1.2, f"calculated peak ≈ {calc_nm:.0f} nm\n(with or without absorption)",
             ha="right", va="top", fontsize=9.5, color=INK)
    top.text(meas_nm + 4, 1.2, f"measured peak ≈ {meas_nm:.0f} nm", ha="left", va="top", fontsize=9.5, color=INK)
    top.text((x0 + trust_nm) / 2, 0.5, "calculation\nnot reliable\nbelow 1493 nm\n(k cutoff\n0.1·π/a)",
             ha="center", va="center", fontsize=8.5, color=INK2)
    top.legend(loc="center right", bbox_to_anchor=(1.0, 0.7), frameon=False, fontsize=9.5)
    top.set_ylim(0, 1.22)
    top.set_yticks(np.arange(0, 1.01, 0.2))
    style(top, "SH intensity (normalized)", "A   Peak position: absorption does not move the calculated peak")

    # B: how much SH survives? |A|^2 of 1994 Eq. 5 (absorption at omega and 2 omega)
    a2 = factor[f"A2__{PERIODS}periods__{PRIMARY}"]
    bottom.axhline(1.0, color=INK2, lw=1.0, ls=(0, (1, 2)), zorder=1)
    bottom.text(trust_nm + 6, 1.015, "no absorption = 100%", ha="left", va="bottom", fontsize=9, color=INK2)
    bottom.plot(wl[win], a2[win], color=ORANGE, lw=2.2)
    y = at1550[PRIMARY]
    bottom.plot([1550, 1550], [0, y], color=INK2, lw=1.0, ls=(0, (1, 2)), zorder=1)
    bottom.plot([1550], [y], "o", ms=8, mfc=ORANGE, mec="white", mew=1.6, zorder=5)
    bottom.text(1557, y - 0.07, f"≈ {y:.0%} of the SH intensity remains at 1550 nm\n"
                f"(80 periods = 2.4 µm; {100 * min(at1550.values()):.0f}–{max(at1550.values()):.0%} across model variants)",
                ha="left", va="top", fontsize=9.5, color=INK)
    bottom.set_ylim(0, 1.12)
    bottom.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    bottom.yaxis.set_major_formatter(PercentFormatter(1.0))
    bottom.set_xlim(x0, x1)
    bottom.set_xlabel("Fundamental wavelength (nm)", color=INK, fontsize=10.5)
    style(bottom, "SH intensity remaining (|A|²)",
          "B   Magnitude: absorption removes about half of the SH near the resonance")

    fig.text(0.012, 0.985, "Absorption lowers the SH signal but does not move the calculated resonance",
             ha="left", va="top", fontsize=12.5, fontweight="bold", color=INK)
    fig.text(0.012, 0.008,
             "Mixed Demo 28 model: 8-band k·p in-plane dispersion; single-band k = 0 wavefunctions and matrix elements, frozen at k = 0;\n"
             "2 conduction × 2 heavy-hole states; Γ = 5 meV; k ≤ 0.1·π/a. SH propagation with absorption at ω and 2ω: Almogy & Yariv (1994) Eq. 5.\n"
             "In A each curve is normalized to its own maximum (the measured data are in arbitrary units). Source: Demo 30 outputs 30D, 30E.",
             ha="left", va="bottom", fontsize=8, color=INK2, linespacing=1.4)
    fig.tight_layout(rect=(0, 0.075, 1, 0.965))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE)
    plt.close(fig)
    print(f"wrote {FIGURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
