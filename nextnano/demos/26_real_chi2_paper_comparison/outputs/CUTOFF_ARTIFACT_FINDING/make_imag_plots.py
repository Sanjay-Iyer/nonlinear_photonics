"""
Im chi2 -- nonlinear absorption -- in the CAUSAL convention.

NOTE ON SIGN.  cutoff_test.py reproduces Xi2.m, which writes the denominators as
(dE - hw + i*gamma).  That puts the pole in the UPPER half of the complex frequency
plane, which is anti-causal, and flips the sign of Im chi2.  Verified three ways:
the two conventions are exact complex conjugates; and a Kramers-Kronig Hilbert
transform recovers Re from Im to <0.6% with -i*gamma, but returns exactly -Re with
+i*gamma.  Re chi2 and |chi2| are identical under both, so nothing else changes.

This script uses the causal (dE - hw - i*gamma) form throughout.

Outputs (same directory):
    plot3_real_vs_imaginary.png   Re and Im together, absolute pm/V
    plot4_imaginary_only.png      Im alone, with the two absorption bands marked

Run with:  C:\\Users\\iyer95\\miniconda3\\envs\\NMIP\\python.exe make_imag_plots.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "cutoff_test.py")).read()
exec(_src.split("# ---------------- full spectra")[0])   # logint, O, ZE, ZH, AC, E0, ...

K = 0.1 * 2 * PI_OVER_A          # 1.1114 nm^-1


def chi2_causal(wl_nm, krng):
    """Eq. 2 with the causal (dE - hw - i*gamma) denominators."""
    w = HC / np.asarray(wl_nm, float)
    K2 = krng ** 2
    g = -1j * GAMMA
    tot = np.zeros_like(w, dtype=complex)
    for (a_, b_, c_) in BPE:
        ea, eb, hc_ = ename(a_), ename(b_), hname(c_)
        num = O[(a_, c_ - 2)] * ZE[(a_, b_)] * O[(b_, c_ - 2)]
        M1 = abs(AC[ea] - AC[hc_]); M2 = abs(AC[eb] - AC[hc_])
        E13 = abs(E0[ea] - E0[hc_]); E23 = abs(E0[eb] - E0[hc_])
        tot -= num * logint(M1, E13 - 2 * w + g, M2, E23 - w + g, K2)
    for (a_, b_, c_) in BPH:
        ha, hb, ec = hname(a_), hname(b_), ename(c_)
        num = O[(c_, a_ - 2)] * ZH[(a_ - 2, b_ - 2)] * O[(c_, b_ - 2)]
        M3 = abs(AC[ha] - AC[ec]); M4 = abs(AC[hb] - AC[ec])
        H13 = abs(E0[ha] - E0[ec]); H23 = abs(E0[hb] - E0[ec])
        tot += num * logint(M3, H13 - 2 * w + g, M4, H23 - w + g, K2)
    return tot


# resonance windows: a transition is reachable for some k in [0, K]
lo = min(abs(E0[e] - E0[h]) for e in ("e1", "e2") for h in ("h1", "h2"))
hi = max(abs(E0[e] - E0[h]) + abs(AC[e] - AC[h]) * K * K
         for e in ("e1", "e2") for h in ("h1", "h2"))
ONE = (HC / hi, HC / lo)              # 1-photon absorption band, nm
TWO = (2 * HC / hi, 2 * HC / lo)      # 2-photon absorption band, nm

wl = np.arange(400.0, 1851.0, 1.0)
c = chi2_causal(wl, K)
re, im = c.real, c.imag

print(f"one-photon band : {ONE[0]:.0f} - {ONE[1]:.0f} nm")
print(f"two-photon band : {TWO[0]:.0f} - {TWO[1]:.0f} nm   <- TPA")
for lam in (1310., 1550., 1600., 1660., 1700.):
    j = int(lam - 400)
    print(f"  at {lam:6.0f} nm :  Re = {re[j]:+8.2f}   Im = {im[j]:+8.2f} pm/V"
          + ("   [inside TPA band]" if TWO[0] <= lam <= TWO[1] else ""))
print(f"Im range: {im.min():+.1f} to {im.max():+.1f} pm/V")


def style(ax):
    ax.set_xlabel("fundamental wavelength (nm)", fontsize=11)
    ax.set_xlim(400, 1850)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ------------------------------------------------------- plot 3: Re and Im
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.axhline(0, color="0.6", lw=0.9)
ax.plot(wl, np.abs(c), color="0.65", lw=1.4, ls=":", label=r"$|\chi^{(2)}|$")
ax.plot(wl, re, color="crimson", lw=2, label=r"$\mathrm{Re}\,\chi^{(2)}$")
ax.plot(wl, im, color="steelblue", lw=1.8, ls="--", label=r"$\mathrm{Im}\,\chi^{(2)}$")
ax.set_ylabel(r"$\chi^{(2)}$ (pm/V)", fontsize=11)
ax.legend(fontsize=10, loc="upper left", frameon=False)
style(ax)
fig.tight_layout()
p3 = os.path.join(HERE, "plot3_real_vs_imaginary.png")
fig.savefig(p3, dpi=150)
plt.close(fig)

# --------------------------------------------------- plot 4: Im on its own
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.axhline(0, color="0.6", lw=0.9)
ax.axvspan(*ONE, color="0.88", zorder=0)
ax.axvspan(*TWO, color="steelblue", alpha=0.13, zorder=0)
ax.plot(wl, im, color="steelblue", lw=2, label=r"$\mathrm{Im}\,\chi^{(2)}$")
ax.set_ylabel(r"$\mathrm{Im}\,\chi^{(2)}$ (pm/V)", fontsize=11)
ylo, yhi = im.min() * 1.18, im.max() * 1.25
ax.set_ylim(ylo, yhi)
ax.text(sum(ONE) / 2, yhi * 0.86, "one-photon\nabsorption", ha="center",
        fontsize=9, color="0.35")
ax.text(sum(TWO) / 2, yhi * 0.86, "two-photon absorption", ha="center",
        fontsize=9, color="steelblue")
ax.axvline(1550, color="crimson", lw=1.2, ls="--")
j = int(1550 - 400)
ax.text(1560, ylo * 0.72, f"1550 nm\nIm = {im[j]:+.1f} pm/V", fontsize=9,
        color="crimson", va="center")
style(ax)
fig.tight_layout()
p4 = os.path.join(HERE, "plot4_imaginary_only.png")
fig.savefig(p4, dpi=150)
plt.close(fig)

print("\nwrote:\n  " + p3 + "\n  " + p4)
