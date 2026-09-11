"""
Regenerates the Fig. 2d comparison as TWO SEPARATE plots, stripped to axes +
legend only: no titles, no feature gridlines, no in-plot annotation.

Does not touch demo26_figure2_explained.png -- that two-panel figure is kept.

Outputs (same directory):
    plot1_cutoff_comparison.png      paper vs |Re chi2| at the two BZ cutoffs
    plot2_observable_comparison.png  paper vs |Re chi2| vs |chi2| at one cutoff

Run with:  C:\\Users\\iyer95\\miniconda3\\envs\\NMIP\\python.exe make_split_plots.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# reuse the analytic chi2() engine from cutoff_test.py (constants + function only)
_src = open(os.path.join(HERE, "cutoff_test.py")).read()
exec(_src.split("# ---------------- full spectra")[0])   # defines chi2, PI_OVER_A, HC

PAPER = np.array([
    [400, 100], [450, 180], [500, 450], [540, 1260], [560, 680], [580, 200],
    [605, 0], [630, 220], [660, 500], [700, 950], [730, 1500], [760, 2450],
    [785, 1550], [815, 1200], [850, 1100], [900, 1120], [950, 1220],
    [1000, 1450], [1040, 1950], [1080, 3250], [1105, 2050], [1130, 1850],
    [1150, 1150], [1175, 1180], [1200, 1050], [1225, 750], [1250, 750],
    [1275, 350], [1300, 350], [1330, 0], [1360, 200], [1400, 600],
    [1440, 1050], [1480, 1800], [1500, 2600], [1520, 3950], [1540, 2900],
    [1560, 1950], [1580, 1450], [1600, 1250], [1650, 1050], [1700, 950],
    [1750, 850], [1800, 750], [1850, 700]], float)

wl = np.arange(400.0, 1851.0, 1.0)
paper_n = PAPER[:, 1] / PAPER[:, 1].max()

c_wide = chi2(wl, 0.1 * 2 * PI_OVER_A)   # 0.1 x (2 pi/a) -- reproduces the paper
c_narr = chi2(wl, 0.1 * PI_OVER_A)       # 0.1 x (pi/a)   -- our production runs


def norm(y):
    return y / y.max()


def style(ax):
    """axes + legend only"""
    ax.set_xlabel("fundamental wavelength (nm)", fontsize=11)
    ax.set_ylabel(r"$\chi^{(2)}$ normalized", fontsize=11)
    ax.set_xlim(400, 1850)
    ax.set_ylim(0, 1.1)
    ax.legend(fontsize=9.5, loc="upper left", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ----------------------------------------------------------------- plot 1
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(PAPER[:, 0], paper_n, "ko--", ms=4, lw=1.4, label="paper Fig. 2d")
ax.plot(wl, norm(np.abs(c_wide.real)), color="crimson", lw=2,
        label=r"$|\mathrm{Re}\,\chi^{(2)}|$, $k_{max}=0.1\times2\pi/a$")
ax.plot(wl, norm(np.abs(c_narr.real)), color="steelblue", lw=1.6, ls="--",
        label=r"$|\mathrm{Re}\,\chi^{(2)}|$, $k_{max}=0.1\times\pi/a$")
style(ax)
fig.tight_layout()
p1 = os.path.join(HERE, "plot1_cutoff_comparison.png")
fig.savefig(p1, dpi=150)
plt.close(fig)

# ----------------------------------------------------------------- plot 2
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(PAPER[:, 0], paper_n, "ko--", ms=4, lw=1.4, label="paper Fig. 2d")
ax.plot(wl, norm(np.abs(c_wide.real)), color="crimson", lw=2,
        label=r"$|\mathrm{Re}\,\chi^{(2)}|$")
ax.plot(wl, norm(np.abs(c_wide)), color="darkgreen", lw=1.8, ls=":",
        label=r"$|\chi^{(2)}|$ full complex")
style(ax)
fig.tight_layout()
p2 = os.path.join(HERE, "plot2_observable_comparison.png")
fig.savefig(p2, dpi=150)
plt.close(fig)

print("wrote:")
print("  " + p1)
print("  " + p2)
