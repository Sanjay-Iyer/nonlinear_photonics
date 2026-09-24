"""Demo 30 figures, drawn only from arrays the stages have already computed.

Colors come from the validated reference categorical order (dataviz skill: blue,
orange, aqua; the first three slots pass all-pairs CVD checks). Measured data are
black markers; the paper simulation is a black dashed line; sample thickness uses one
blue sequential ramp. There are no dual y-axes. The top wavelength axis in 30C/30D is
the same quantity in other units (SH wavelength = fundamental / 2).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import absorption as ab  # noqa: E402
from .paths import REFERENCE  # noqa: E402

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#dddcd7"
THICKNESS = {4: "#86b6ef", 12: "#3987e5", 16: "#1c5cab", 80: "#0d366b"}  # sequential blue steps 250..700
VARIANT_STYLE = {
    "consistent_2x2__strict": dict(color=ORANGE, ls="-", label="2×2 states, strict k ≤ 0.1·π/a (primary)"),
    "consistent_2x2__tail": dict(color=ORANGE, ls="--", label="2×2 states + analytical high-k tail"),
    "expanded_bound_states__strict": dict(color=AQUA, ls="-", label="expanded bound states, strict"),
    "expanded_bound_states__tail": dict(color=AQUA, ls="--", label="expanded bound states + tail"),
}


def _style(ax, xlabel=None, ylabel=None, title=None):
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=INK2, labelsize=8.5)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK, fontsize=9)
    if title:
        ax.set_title(title, color=INK, fontsize=9.5, loc="left")


def _sh_axis(ax):
    top = ax.secondary_xaxis("top", functions=(lambda x: x / 2, lambda x: 2 * x))
    top.set_xlabel("second-harmonic wavelength (nm)", color=INK2, fontsize=8.5)
    top.tick_params(colors=INK2, labelsize=8)


def _shade_untrusted(ax, lo, hi, label, y=0.98, va="top"):
    ax.axvspan(lo, hi, color="#f0efec", zorder=0, lw=0)
    ax.text((lo + hi) / 2, y, label, transform=ax.get_xaxis_transform(), ha="center", va=va,
            fontsize=7.5, color=INK2)


def chi2_vs_paper(path: Path, state: dict, comp_a: dict):
    wl, chi = state["wl"], state["chi2"].chi2_complex
    eye = np.loadtxt(REFERENCE / "paper_fig2d_simulated.csv", delimiter=",", skiprows=1)
    traced = np.loadtxt(REFERENCE / "paper_fig2d_simulated_traced.csv", delimiter=",", skiprows=1)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.6), sharex=True, dpi=150)
    a1.plot(wl, chi.real, color=BLUE, lw=1.6, label="Re χ(2)")
    a1.plot(wl, chi.imag, color=ORANGE, lw=1.6, label="Im χ(2)")
    a1.axhline(0, color=INK2, lw=0.6)
    _style(a1, ylabel="χ(2) (pm/V, Demo 28A units)",
           title="(a) Control χ(2): Demo 28A recomputed from the registered raw data, k ≤ 0.1·π/a, Γ = 5 meV")
    a1.legend(fontsize=8, frameon=False, loc="upper right")
    m = comp_a["eye_45_point_reference"]
    a2.plot(traced[:, 0], traced[:, 1] / traced[:, 1].max(), color=INK, lw=1.2, ls=(0, (4, 2)),
            label="paper simulated |χ(2)| (traced from Fig. 2d)")
    a2.plot(eye[:, 0], eye[:, 1] / eye[:, 1].max(), "o", ms=4, mfc="white", mec=INK, mew=0.9,
            label="paper, older 45-point digitization (used for nRMSE)")
    a2.plot(wl, np.abs(chi.real) / np.abs(chi.real).max(), color=BLUE, lw=1.6,
            label=f"model |Re χ(2)|  (nRMSE {m['abs_real']['nRMSE']:.3f})")
    a2.plot(wl, np.abs(chi) / np.abs(chi).max(), color=AQUA, lw=1.6,
            label=f"model |χ(2)|  (nRMSE {m['magnitude']['nRMSE']:.3f})")
    _style(a2, xlabel="fundamental wavelength (nm)", ylabel="normalized to own maximum",
           title="(b) Comparison A — susceptibility shape vs the paper's SIMULATED |χ(2)| (no propagation)")
    a2.legend(fontsize=7.5, frameon=False, loc="upper left")
    a2.set_xlim(400, 1850)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def absorption_coefficients(path: Path, ares: dict, cfg: dict, trust_nm: float):
    wl = ares["wavelength_nm"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 7.4), sharex=True, dpi=150, gridspec_kw={"height_ratios": [3, 2]})
    lo = 1150
    m = wl >= lo
    for name, st in VARIANT_STYLE.items():
        a1.plot(wl[m], ab.per_cm(ares["alpha_I_2w"][name])[m], lw=1.6, **st)
    period = cfg["samples"]["period_nm"]
    ymax = max(ab.per_cm(v[m]).max() for v in ares["alpha_I_2w"].values()) * 1.08
    valid = wl >= ares["validity_min_fundamental_nm"]
    reached = max(ab.per_cm(v[valid]).max() for v in ares["alpha_I_2w"].values())
    for n in cfg["samples"]["periods"]:
        level = 1e7 / (n * period)  # cm^-1 where the absorption length equals the sample thickness
        if level < reached:  # only thicknesses the modeled absorption actually reaches
            a1.axhline(level, color=THICKNESS[n], lw=1.0, ls=":")
            a1.text(1848, level, f"1/α_I = {n * period / 1000:.2f} µm ({n} periods)",
                    va="bottom", ha="right", fontsize=7.5, color=INK2)
    _shade_untrusted(a1, lo, ares["validity_min_fundamental_nm"], "SH above the\ncontinuum onset:\nnot modeled",
                     y=0.5, va="center")
    a1.axvline(trust_nm, color=INK2, lw=0.8, ls="--")
    a1.text(trust_nm + 4, 0.83, "strict 0.1·π/a\ntruncation limit", transform=a1.get_xaxis_transform(), fontsize=7.5, color=INK2)
    a1.set_ylim(0, ymax)
    _style(a1, ylabel="α_I(2ω)  (cm⁻¹, intensity)",
           title="(a) Absorption of the second harmonic in the MQW stack (period-averaged, x-polarized)")
    _sh_axis(a1)
    a1.legend(fontsize=7.5, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.93))
    for name, st in VARIANT_STYLE.items():
        a2.semilogy(wl[m], ab.per_cm(ares["alpha_I_w"][name])[m], lw=1.4, **{k: v for k, v in st.items() if k != "label"})
    l80 = cfg["samples"]["fig2d_sample_periods"] * period * 1e-7  # cm
    a2.axhline(0.01 / (l80 / 2), color=INK2, lw=0.8, ls=":")
    a2.text(lo + 8, 0.01 / (l80 / 2), "α_E·L = 0.01 for 80 periods (negligibility threshold)", va="bottom", fontsize=7.5, color=INK2)
    _style(a2, xlabel="fundamental wavelength (nm)", ylabel="α_I(ω)  (cm⁻¹, log)",
           title="(b) Absorption of the fundamental: Lorentzian-tail upper bound, far below the threshold")
    a2.set_xlim(lo, 1850)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def absorption_factor(path: Path, pres: dict, ares: dict, cfg: dict, trust_nm: float):
    wl = pres["wavelength_nm"]
    main_n = cfg["samples"]["fig2d_sample_periods"]
    lo = 1350
    m = wl >= lo
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 7.0), sharex=True, dpi=150)
    for name, st in VARIANT_STYLE.items():
        a1.plot(wl[m], np.abs(pres["factors"][name][main_n][m]) ** 2, lw=1.6, **st)
    _shade_untrusted(a1, lo, max(ares["validity_min_fundamental_nm"], lo), "not modeled")
    a1.axvline(trust_nm, color=INK2, lw=0.8, ls="--")
    a1.set_ylim(0, 1.05)
    _style(a1, ylabel="|A|²  (SH intensity factor)",
           title=f"(a) Fig. 2d sample ({main_n} periods, {main_n * cfg['samples']['period_nm'] / 1000:.1f} µm): "
                 "SH suppression by absorption (1994 Eq. 5)")
    _sh_axis(a1)
    a1.legend(fontsize=7.5, frameon=False, loc="lower right")
    for n in cfg["samples"]["periods"]:
        a2.plot(wl[m], np.abs(pres["factors"]["consistent_2x2__strict"][n][m]) ** 2, color=THICKNESS[n], lw=1.6,
                label=f"{n} periods ({n * cfg['samples']['period_nm'] / 1000:.2f} µm)")
    _shade_untrusted(a2, lo, max(ares["validity_min_fundamental_nm"], lo), "not modeled")
    a2.axvline(trust_nm, color=INK2, lw=0.8, ls="--")
    a2.set_ylim(0, 1.05)
    _style(a2, xlabel="fundamental wavelength (nm)", ylabel="|A|²",
           title="(b) Thickness dependence (primary model: 2×2 states, strict k ≤ 0.1·π/a)")
    a2.legend(fontsize=7.5, frameon=False, loc="lower right")
    a2.set_xlim(lo, 1850)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig2d_comparison(path: Path, state: dict, eres: dict, cfg: dict):
    wl = state["wl"]
    lo_w, hi_w = eres["meta"]["comparison_window_nm"]
    x0, x1 = 1390, 1810
    m = (wl >= x0) & (wl <= x1)
    traced = np.loadtxt(REFERENCE / "paper_fig2d_simulated_traced.csv", delimiter=",", skiprows=1)
    chi = np.abs(state["chi2"].chi2_complex)
    win = (wl >= lo_w) & (wl <= hi_w)
    tm = (traced[:, 0] >= lo_w) & (traced[:, 0] <= hi_w)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 7.6), sharex=True, dpi=150, gridspec_kw={"height_ratios": [2, 3]})
    a1.plot(traced[:, 0], traced[:, 1] / traced[tm, 1].max(), color=INK, lw=1.2, ls=(0, (4, 2)),
            label="paper simulated |χ(2)| (traced)")
    a1.plot(wl[m], chi[m] / chi[win].max(), color=BLUE, lw=1.6, label="model |χ(2)|, control")
    _shade_untrusted(a1, x0, lo_w, "outside\ncomparison")
    _style(a1, ylabel="|χ(2)| / window max",
           title="(a) Comparison A: susceptibilities (NOT an SH signal)")
    a1.legend(fontsize=7.5, frameon=False, loc="upper right")
    a1.set_ylim(0, 1.15)
    norm = eres["normalized"]
    mw = m & win  # model SH curves are compared (and drawn) only inside the comparison window
    a2.plot(wl[mw], norm["transparent (control)"][mw], color=BLUE, lw=1.6, label="SH, transparent (control, A = 1)")
    a2.fill_between(wl[mw], norm["absorptive: expanded_bound_states__strict"][mw],
                    norm["absorptive: expanded_bound_states__tail"][mw], color=AQUA, alpha=0.35, lw=0,
                    label="SH with absorption, expanded bound states (strict … tail)")
    a2.plot(wl[mw], norm["absorptive: consistent_2x2__strict"][mw], color=ORANGE, lw=1.6,
            label="SH with absorption, 2×2 states, strict (primary)")
    a2.plot(wl[mw], norm["absorptive: consistent_2x2__tail"][mw], color=ORANGE, lw=1.4, ls="--",
            label="SH with absorption, 2×2 states + tail")
    meas, mn, use = eres["measured"], eres["measured_norm"], eres["use"]
    a2.plot(meas["wavelength_nm"][use], mn[use], "s", ms=6.5, color=INK, label="measured SH, 80-period sample (Fig. 2d)")
    a2.plot(meas["wavelength_nm"][~use], mn[~use], "s", ms=6.5, mfc="white", mec=INK,
            label="measured point outside the validity window")
    _shade_untrusted(a2, x0, lo_w, "outside comparison:\nSH above the continuum\nonset (< 1408 nm) or\nstrict-cutoff truncation\n(< 1493 nm)",
                     y=0.62, va="center")
    _style(a2, xlabel="fundamental wavelength (nm)", ylabel="SH intensity / window max",
           title="(b) Comparison B: SH intensity, 80 periods (1994 Eq. 5), each curve normalized to its own maximum")
    a2.legend(fontsize=7.5, frameon=False, loc="upper right")
    a2.set_xlim(x0, x1)
    a2.set_ylim(0, 1.15)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chi1_diagnostic(path: Path, ares: dict, state: dict):
    """Diagnostic: chi1 at the SH photon energy, with the transition energies marked."""
    e = ares["E_2w_eV"]
    order = np.argsort(e)
    e = e[order]
    m = (e >= 1.35) & (e <= 1.95)
    s = state["settings"].gamma_sign
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.8), sharex=True, dpi=150)
    for model, color in (("consistent_2x2", ORANGE), ("expanded_bound_states", AQUA)):
        c = ares["chi1"][model]["2w"]
        a1.plot(e[m], (-s * c.strict.imag)[order][m], color=color, lw=1.6, label=f"{model}, strict")
        a1.plot(e[m], (-s * c.tail.imag)[order][m], color=color, lw=1.4, ls="--", label=f"{model} + tail")
        a2.plot(e[m], c.strict.real[order][m], color=color, lw=1.6, label=f"{model}, strict")
    strong = sorted((p for p in ares["sets"]["expanded_bound_states"] if p.overlap_sq[0] >= 0.05),
                    key=lambda p: p.transition_eV[0])
    groups = []  # pairs closer than 10 meV share one label
    for p in strong:
        if groups and p.transition_eV[0] - groups[-1][-1].transition_eV[0] < 0.010:
            groups[-1].append(p)
        else:
            groups.append([p])
    for group in groups:
        for p in group:
            for ax in (a1, a2):
                ax.axvline(p.transition_eV[0], color=INK2, lw=0.7, ls=":")
        a1.text(group[0].transition_eV[0], 0.99, " " + ", ".join(p.label for p in group), rotation=90, va="top",
                ha="right", transform=a1.get_xaxis_transform(), fontsize=7, color=INK2)
    for p in ares["sets"]["consistent_2x2"]:
        if p.overlap_sq[0] >= 0.05:
            a1.axvline(p.transition_eV[-1], color=ORANGE, lw=0.8, ls=(0, (1, 2)))
    _style(a1, ylabel="−Im χ(1)  (> 0: absorption)",
           title="(a) Absorptive part at the SH energy. Gray dotted: T(0) of strong pairs; "
                 "orange dotted: 2×2 truncation edges T(k_max)")
    a1.legend(fontsize=7.5, frameon=False, loc="upper left")
    _style(a2, xlabel="photon energy ħω_SH = 2ħω (eV)", ylabel="Re χ(1)  (strict only)",
           title="(b) Dispersive part (resonant term only; the analytical tail has no finite Re)")
    a2.legend(fontsize=7.5, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
