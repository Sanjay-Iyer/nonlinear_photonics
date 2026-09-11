"""
Two diagnostics on whether the Im chi2 spectrum is physical.

1. im_chi2_cutoff_vs_no_cutoff.png
   Im chi2 with the Fig. 2d reproduction cutoff (0.1 x 2pi/a) against the same model
   with the k cutoff pushed out of the window (20 pi/a).  For the diagonal pathways
   the k integral is exact:
       Im = SUM_pairs Neff * pi^2/(M w) * [W(2w) - W(w)],
       W(E) = 1 iff dE <= E <= dE + M k_max^2.
   Without a cutoff the one- and two-photon contributions cancel exactly wherever
   both are switched on, leaving ONE plateau between 2hw = dE and hw = dE.  The hard
   cutoff chops that plateau into two opposite-signed boxes with a gap between them.

2. im_chi2_diagonal_vs_offdiagonal.png
   Im chi2 split by pathway.  Diagonal pathways (a = b) have numerators
   |<e|h>|^2 (<e|z|e> - <h|z|h>): squared amplitudes times expectation values, real
   for any wavefunction phase.  Off-diagonal pathways have numerators
   <h|e1><e1|z|e2><e2|h>: a product of genuine transition amplitudes, which can be
   complex.

Causal (dE - hw - i*gamma) convention.  Values are proportional to chi2 but are NOT
calibrated pm/V: this engine carries no Eq. 2 prefactor, and differs from the
prefactored Demo 23D pipeline by a factor of 2.0-2.3.  Axes are labelled arb. units.

Formatting: axis labels and legend only.

Run with:  C:\\Users\\iyer95\\miniconda3\\envs\\NMIP\\python.exe make_im_physicality_plots.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "cutoff_test.py")).read()
exec(_src.split("# ---------------- full spectra")[0])

K_PAPER = 0.1 * 2 * PI_OVER_A
K_NONE = 20 * PI_OVER_A


def chi2_parts(wl_nm, krng, which="all"):
    w = HC / np.asarray(wl_nm, float)
    K2 = krng ** 2
    g = -1j * GAMMA
    tot = np.zeros_like(w, dtype=complex)
    for (a_, b_, c_) in BPE:
        d = a_ == b_
        if (which == "diag" and not d) or (which == "off" and d):
            continue
        ea, eb, hc_ = ename(a_), ename(b_), hname(c_)
        num = O[(a_, c_ - 2)] * ZE[(a_, b_)] * O[(b_, c_ - 2)]
        M1 = abs(AC[ea] - AC[hc_]); M2 = abs(AC[eb] - AC[hc_])
        E13 = abs(E0[ea] - E0[hc_]); E23 = abs(E0[eb] - E0[hc_])
        tot -= num * logint(M1, E13 - 2 * w + g, M2, E23 - w + g, K2)
    for (a_, b_, c_) in BPH:
        d = a_ == b_
        if (which == "diag" and not d) or (which == "off" and d):
            continue
        ha, hb, ec = hname(a_), hname(b_), ename(c_)
        num = O[(c_, a_ - 2)] * ZH[(a_ - 2, b_ - 2)] * O[(c_, b_ - 2)]
        M3 = abs(AC[ha] - AC[ec]); M4 = abs(AC[hb] - AC[ec])
        H13 = abs(E0[ha] - E0[ec]); H23 = abs(E0[hb] - E0[ec])
        tot += num * logint(M3, H13 - 2 * w + g, M4, H23 - w + g, K2)
    return tot


wl = np.arange(400.0, 1851.0, 1.0)
im_paper = chi2_parts(wl, K_PAPER).imag
im_none = chi2_parts(wl, K_NONE).imag
im_diag = chi2_parts(wl, K_PAPER, "diag").imag
im_off = chi2_parts(wl, K_PAPER, "off").imag


def finish(ax):
    ax.set_xlabel("fundamental wavelength (nm)", fontsize=11)
    ax.set_ylabel(r"$\mathrm{Im}\,\chi^{(2)}$ (arb. units)", fontsize=11)
    ax.set_xlim(400, 1850)
    ax.legend(fontsize=10, loc="lower left", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


fig, ax = plt.subplots(figsize=(10, 4.8))
ax.axhline(0, color="0.6", lw=0.9)
ax.plot(wl, im_none, color="0.35", lw=2.2, label=r"cutoff removed ($k_{max}=20\,\pi/a$)")
ax.plot(wl, im_paper, color="steelblue", lw=1.8, ls="--",
        label=r"Fig. 2d cutoff ($k_{max}=0.1\times2\pi/a$)")
finish(ax)
fig.tight_layout()
p1 = os.path.join(HERE, "im_chi2_cutoff_vs_no_cutoff.png")
fig.savefig(p1, dpi=200)
plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.8))
ax.axhline(0, color="0.6", lw=0.9)
ax.plot(wl, im_paper, color="steelblue", lw=2.2, label="total")
ax.plot(wl, im_diag, color="darkorange", lw=1.6, ls="--",
        label="diagonal pathways (real numerator)")
ax.plot(wl, im_off, color="purple", lw=1.6, ls=":",
        label="off-diagonal pathways (can be complex)")
finish(ax)
fig.tight_layout()
p2 = os.path.join(HERE, "im_chi2_diagonal_vs_offdiagonal.png")
fig.savefig(p2, dpi=200)
plt.close(fig)

print("wrote:\n  " + p1 + "\n  " + p2)
