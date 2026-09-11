"""
Re chi2 vs Im chi2, in absolute pm/V, at k_max = 0.1 x (2 pi/a).

Shows why the observable question has an answer: Re is signed and passes through
zero; Im is large exactly there; so |chi2| = sqrt(Re^2 + Im^2) cannot reach zero.

Output (same directory):
    plot3_real_vs_imaginary.png

Run with:  C:\\Users\\iyer95\\miniconda3\\envs\\NMIP\\python.exe make_real_imag_plot.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "cutoff_test.py")).read()
exec(_src.split("# ---------------- full spectra")[0])   # chi2, PI_OVER_A, HC

wl = np.arange(400.0, 1851.0, 1.0)
c = chi2(wl, 0.1 * 2 * PI_OVER_A)
re, im, mag = c.real, c.imag, np.abs(c)

# where does Re change sign?
zc = [wl[i] - re[i] * (wl[i + 1] - wl[i]) / (re[i + 1] - re[i])
      for i in range(len(re) - 1) if re[i] * re[i + 1] < 0]

print("Re zero crossings (nm):", ", ".join(f"{z:.0f}" for z in zc))
for z in zc:
    j = int(round(z - 400))
    print(f"   at {z:7.1f} nm :  Re = {re[j]:+8.2f}   Im = {im[j]:+8.2f}"
          f"   |chi2| = {mag[j]:7.2f} pm/V")
print(f"Re range: {re.min():+.1f} to {re.max():+.1f} pm/V")
print(f"Im range: {im.min():+.1f} to {im.max():+.1f} pm/V")

fig, ax = plt.subplots(figsize=(10, 4.8))
ax.axhline(0, color="0.6", lw=0.9, zorder=1)
ax.plot(wl, mag, color="0.65", lw=1.4, ls=":", zorder=2,
        label=r"$|\chi^{(2)}|$")
ax.plot(wl, re, color="crimson", lw=2, zorder=4,
        label=r"$\mathrm{Re}\,\chi^{(2)}$")
ax.plot(wl, im, color="steelblue", lw=1.8, ls="--", zorder=3,
        label=r"$\mathrm{Im}\,\chi^{(2)}$")
ax.set_xlabel("fundamental wavelength (nm)", fontsize=11)
ax.set_ylabel(r"$\chi^{(2)}$ (pm/V)", fontsize=11)
ax.set_xlim(400, 1850)
ax.legend(fontsize=10, loc="upper left", frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
fig.tight_layout()

p = os.path.join(HERE, "plot3_real_vs_imaginary.png")
fig.savefig(p, dpi=150)
print("\nwrote " + p)
