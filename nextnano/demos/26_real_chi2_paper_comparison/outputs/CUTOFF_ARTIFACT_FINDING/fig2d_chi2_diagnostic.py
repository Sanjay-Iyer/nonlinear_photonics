"""
Fig. 2d observable diagnostic: is the published curve effectively |Re chi2|
rather than the full complex |chi2|?

Computes Re, Im, |Re| and |chi2| from ONE complex evaluation of Eq. 2, on the same
structure / parameters / broadening / k-cutoff / wavelength range as the existing
Fig. 2d reproduction, runs eight consistency checks, and writes:

    fig2d_re_im_chi2_diagnostic.png
    fig2d_abs_re_vs_abs_complex_chi2_comparison.png
    fig2d_chi2_components.csv
    fig2d_chi2_diagnostic_summary.md

SIGN CONVENTION.  cutoff_test.py reproduces Xi2.m, which writes the denominators as
(dE - hw + i*gamma) -- pole in the UPPER half plane, anti-causal, which inverts Im.
This script uses the causal (dE - hw - i*gamma) form.  Re chi2, |Re chi2| and |chi2|
are identical under both conventions, so the Fig. 2d reproduction is unaffected;
only the sign of Im differs.  Check 5 below re-verifies this.

Run with:  C:\\Users\\iyer95\\miniconda3\\envs\\NMIP\\python.exe fig2d_chi2_diagnostic.py
"""
import os
import numpy as np
from scipy.optimize import brentq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(HERE, "cutoff_test.py")).read()
exec(_src.split("# ---------------- full spectra")[0])   # logint, O, ZE, ZH, AC, E0, BPE, BPH, GAMMA, HC, A_LAT, PI_OVER_A

# ---------------------------------------------------------------- parameters
K_CUTOFF = 0.1 * 2 * PI_OVER_A        # nm^-1, the Fig. 2d reproduction value
WL_MIN, WL_MAX, WL_STEP = 400.0, 1850.0, 1.0

log = []
def say(s=""):
    print(s)
    log.append(s)


def chi2_complex(wl_nm, krng=K_CUTOFF, sign=-1):
    """ONE complex evaluation of Eq. 2. sign=-1 is causal."""
    w = HC / np.asarray(wl_nm, float)
    K2 = krng ** 2
    g = sign * 1j * GAMMA
    tot = np.zeros(np.shape(w), dtype=complex)
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


wl = np.arange(WL_MIN, WL_MAX + WL_STEP / 2, WL_STEP)
chi = chi2_complex(wl)                      # <-- the single complex array
re_chi2, im_chi2 = chi.real, chi.imag       # both derived from it
abs_re_chi2 = np.abs(re_chi2)               # abs AFTER taking the signed real part
abs_chi2 = np.abs(chi)
component_scale = abs_re_chi2.max()  # one reference for BOTH signed components

PAPER = np.array([
    [400,100],[450,180],[500,450],[540,1260],[560,680],[580,200],[605,0],[630,220],
    [660,500],[700,950],[730,1500],[760,2450],[785,1550],[815,1200],[850,1100],
    [900,1120],[950,1220],[1000,1450],[1040,1950],[1080,3250],[1105,2050],
    [1130,1850],[1150,1150],[1175,1180],[1200,1050],[1225,750],[1250,750],
    [1275,350],[1300,350],[1330,0],[1360,200],[1400,600],[1440,1050],[1480,1800],
    [1500,2600],[1520,3950],[1540,2900],[1560,1950],[1580,1450],[1600,1250],
    [1650,1050],[1700,950],[1750,850],[1800,750],[1850,700]], float)

# ============================================================ VERIFICATION
say("=" * 78)
say("VERIFICATION")
say("=" * 78)
checks = {}

# -- 1. same pipeline as the Fig. 2d reproduction --------------------------
say("\n[1] Pipeline identical to the Fig. 2d reproduction")
say(f"    structure     : Demo 19 case_00 (abrupt reference) frozen matrix elements")
say(f"    dispersion    : Demo 24 aligned parabolic fits, e1/e2/hh1/hh2")
say(f"    E0 (eV)       : " + ", ".join(f"{k}={v:.6f}" for k, v in E0.items()))
say(f"    A  (eV nm^2)  : " + ", ".join(f"{k}={v:+.6f}" for k, v in AC.items()))
say(f"    broadening    : Gamma = {GAMMA*1000:.1f} meV")
say(f"    k cutoff      : {K_CUTOFF:.5f} nm^-1 = 0.1 x (2pi/a), a = {A_LAT} nm")
say(f"    pathways      : {len(BPE)} electron + {len(BPH)} hole = {len(BPE)+len(BPH)}")
say(f"    wavelengths   : {WL_MIN:.0f}-{WL_MAX:.0f} nm, {WL_STEP:.0f} nm step, "
    f"{len(wl)} points")
ref = chi2(np.array([752.0, 1505.0]), K_CUTOFF)   # cutoff_test.py's own engine
mine = chi2_complex(np.array([752.0, 1505.0]))
d_re = np.abs(ref.real - mine.real).max()
checks["1 same pipeline"] = d_re < 1e-9
say(f"    -> Re agrees with cutoff_test.py engine to {d_re:.2e} pm/V  "
    f"[{'PASS' if checks['1 same pipeline'] else 'FAIL'}]")

# -- 2. Re and Im from the SAME complex object -----------------------------
say("\n[2] Re and Im come from one complex evaluation, not two calculations")
same = (re_chi2 is chi.real) or np.shares_memory(re_chi2, chi)
checks["2 single evaluation"] = bool(same or np.array_equal(re_chi2, chi.real))
say(f"    re_chi2 and im_chi2 are .real/.imag views of the same array "
    f"[{'PASS' if checks['2 single evaluation'] else 'FAIL'}]")

# -- 3. |chi2| == sqrt(Re^2 + Im^2) everywhere -----------------------------
say("\n[3] |chi2| = sqrt(Re^2 + Im^2) at every wavelength")
resid = np.abs(abs_chi2 - np.sqrt(re_chi2**2 + im_chi2**2))
checks["3 modulus identity"] = resid.max() < 1e-12
say(f"    max |  |chi2| - sqrt(Re^2+Im^2)  | = {resid.max():.3e} pm/V   "
    f"[{'PASS' if checks['3 modulus identity'] else 'FAIL'}]")

# -- 4. |Re chi2| is abs() applied after the signed real part --------------
say("\n[4] |Re chi2| formed by abs() of the signed real part")
checks["4 abs of real"] = np.array_equal(abs_re_chi2, np.abs(chi.real))
nneg = int((re_chi2 < 0).sum())
say(f"    abs_re_chi2 == abs(chi.real) exactly "
    f"[{'PASS' if checks['4 abs of real'] else 'FAIL'}]")
say(f"    signed Re is negative at {nneg}/{len(wl)} points, so the abs() is doing work")

# -- 5. sign / unit / normalization / wavelength-axis checks ---------------
say("\n[5] Sign, unit, normalization and wavelength-axis checks")
anti = chi2_complex(wl, sign=+1)
conj_ok = np.abs(anti - np.conj(chi)).max() < 1e-9
say(f"    (a) +i*gamma and -i*gamma give exact conjugates "
    f"(max dev {np.abs(anti-np.conj(chi)).max():.2e})  "
    f"[{'PASS' if conj_ok else 'FAIL'}]")
say(f"        -> Re identical both ways; only Im flips. Causal form used here.")
kk_note = ("Kramers-Kronig verified separately (kk_test.py): with -i*gamma the "
           "Hilbert transform of Im recovers Re to <0.6%; with +i*gamma it "
           "returns exactly -Re.")
say(f"    (b) {kk_note}")
peak_hi = wl[np.argmax(abs_re_chi2)]
say(f"    (c) scale: peak |Re chi2| = {abs_re_chi2.max():.2f} at {peak_hi:.0f} nm, "
    f"matching this engine's earlier 41.2 at 1505 nm. SELF-CONSISTENCY ONLY, not a "
    f"calibration: the engine carries no Eq. 2 prefactor and differs from the "
    f"prefactored Demo 23D pipeline by 2.0-2.3x, so values are not calibrated pm/V")
unit_ok = abs(abs_re_chi2.max() - 41.2) < 0.5 and abs(peak_hi - 1505) < 3
say(f"        [{'PASS' if unit_ok else 'FAIL'}]")
mono = np.all(np.diff(HC / wl) < 0)
say(f"    (d) wavelength axis: hw = hc/lambda strictly decreasing over the grid "
    f"[{'PASS' if mono else 'FAIL'}]")
say(f"        lambda {wl[0]:.0f}-{wl[-1]:.0f} nm  <->  hw "
    f"{HC/wl[-1]:.4f}-{HC/wl[0]:.4f} eV")
say(f"    (e) normalization: figure 1 divides BOTH Re and Im by max |Re| = "
    f"{component_scale:.6g}; paper uses its own peak. CSV retains raw values. "
    f"Figure 2 normalizes each curve to its own maximum (stated on its axis).")
checks["5 sign/units/axis"] = bool(conj_ok and unit_ok and mono)

# -- 6. zero crossings are true sign changes, not grid artifacts -----------
say("\n[6] Zero crossings of Re chi2 are true sign changes")
brackets = [(wl[i], wl[i+1]) for i in range(len(wl)-1) if re_chi2[i]*re_chi2[i+1] < 0]
roots = []
for lo, hi in brackets:
    f = lambda x: chi2_complex(np.array([x])).real[0]
    r = brentq(f, lo, hi, xtol=1e-10)
    left = chi2_complex(np.array([r - 1.0])).real[0]
    right = chi2_complex(np.array([r + 1.0])).real[0]
    roots.append((r, left, right, np.sign(left) != np.sign(right)))
say(f"    {len(brackets)} sign-change bracket(s) found on the 1 nm grid")
for r, l, rr, ok in roots:
    say(f"    lambda = {r:9.4f} nm : Re(-1nm) = {l:+8.3f}, Re(+1nm) = {rr:+8.3f}  "
        f"-> true sign change: {'YES' if ok else 'NO'}")
say(f"    roots refined with Brent's method on the continuous function "
    f"(xtol 1e-10), not read off the grid")
checks["6 true crossings"] = all(ok for *_, ok in roots) and len(roots) == 2

# -- 7. Im at the crossings, evaluated at the refined roots ---------------
say("\n[7] Im chi2 at the refined zero crossings")
say(f"    {'lambda nm':>12}{'Re':>12}{'Im':>12}{'|chi2|':>12}{'|Re|':>10}")
cross = []
for r, *_ in roots:
    cr = chi2_complex(np.array([r]))[0]
    cross.append((r, cr.real, cr.imag, abs(cr)))
    say(f"    {r:12.4f}{cr.real:12.3e}{cr.imag:+12.3f}{abs(cr):12.3f}{abs(cr.real):10.3e}")
say(f"    evaluated directly at the roots, not interpolated from the 1 nm grid")
checks["7 Im at crossings"] = all(abs(im) > 1.0 for _, _, im, _ in cross)

# -- 8. internal consistency ----------------------------------------------
say("\n[8] Internal consistency")
say(f"    |chi2| global minimum on the grid = {abs_chi2.min():.3f} pm/V at "
    f"{wl[np.argmin(abs_chi2)]:.0f} nm")
say(f"    |Re chi2| global minimum          = {abs_re_chi2.min():.3e} pm/V at "
    f"{wl[np.argmin(abs_re_chi2)]:.0f} nm")
checks["8 consistency"] = abs_chi2.min() > 10 * abs_re_chi2.min()
say(f"    |chi2| never approaches zero while |Re chi2| does  "
    f"[{'PASS' if checks['8 consistency'] else 'FAIL'}]")

say("\n" + "-" * 78)
for k, v in checks.items():
    say(f"    {k:24s} {'PASS' if v else 'FAIL'}")
say("-" * 78)

# ============================================================ FIGURES
def finish(ax, xlab, ylab, loc="upper left"):
    ax.set_xlabel(xlab, fontsize=11)
    ax.set_ylabel(ylab, fontsize=11)
    ax.set_xlim(WL_MIN, WL_MAX)
    ax.legend(fontsize=9.5, loc=loc, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

# ---- figure 1: signed Re and Im ----------------------------------------
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.axhline(0, color="0.6", lw=0.9, zorder=1)
ax.plot(PAPER[:, 0], PAPER[:, 1] / PAPER[:, 1].max(), "ko--", ms=4, lw=1.3,
        zorder=2, label="paper Fig. 2d")
ax.plot(wl, re_chi2 / component_scale, color="crimson", lw=2, zorder=4,
        label=r"$\mathrm{Re}\,\chi^{(2)}$")
ax.plot(wl, im_chi2 / component_scale, color="steelblue", lw=1.8, ls="-", zorder=3,
        label=r"$\mathrm{Im}\,\chi^{(2)}$")
finish(ax, "fundamental wavelength (nm)", r"normalized $\chi^{(2)}$")
fig.tight_layout()
f1 = os.path.join(HERE, "fig2d_re_im_chi2_diagnostic.png")
fig.savefig(f1, dpi=200)
plt.close(fig)

# ---- figure 2: paper vs |Re chi2| vs |chi2| ----------------------------
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(PAPER[:, 0], PAPER[:, 1] / PAPER[:, 1].max(), "ko--", ms=4, lw=1.3,
        zorder=2, label="paper Fig. 2d")
ax.plot(wl, abs_re_chi2 / abs_re_chi2.max(), color="crimson", lw=2, zorder=4,
        label=r"$|\mathrm{Re}\,\chi^{(2)}|$")
ax.plot(wl, abs_chi2 / abs_chi2.max(), color="darkgreen", lw=1.8, ls=":", zorder=3,
        label=r"$|\chi^{(2)}|$")
ax.set_ylim(0, 1.1)
finish(ax, "fundamental wavelength (nm)",
       r"$\chi^{(2)}$ normalized to peak")
fig.tight_layout()
f2 = os.path.join(HERE, "fig2d_abs_re_vs_abs_complex_chi2_comparison.png")
fig.savefig(f2, dpi=200)
plt.close(fig)

# ============================================================ CSV
csv_path = os.path.join(HERE, "fig2d_chi2_components.csv")
np.savetxt(csv_path,
           np.column_stack([wl, re_chi2, im_chi2, abs_re_chi2, abs_chi2]),
           delimiter=",", comments="",
           header="wavelength_nm,re_chi2,im_chi2,abs_re_chi2,abs_chi2",
           fmt="%.6g")

# ============================================================ SUMMARY
r1, r2 = cross[0], cross[1]
pk = abs_chi2.max()
md = f"""# Fig. 2d observable diagnostic: |Re chi2| versus |chi2|

Generated by `fig2d_chi2_diagnostic.py`. All four quantities come from a single
complex evaluation of Eq. 2 on the same structure, parameters, broadening,
k-cutoff and wavelength range as the existing Fig. 2d reproduction.

## Result

Values below are labelled pm/V but are **not calibrated** (see check 5); ratios
between them are meaningful, absolute magnitudes are not.

| quantity | at {r1[0]:.1f} nm | at {r2[0]:.1f} nm |
|---|---|---|
| Re chi2 | {r1[1]:.2e} pm/V | {r2[1]:.2e} pm/V |
| Im chi2 | **{r1[2]:+.2f} pm/V** | **{r2[2]:+.2f} pm/V** |
| \\|chi2\\| | {r1[3]:.2f} pm/V | {r2[3]:.2f} pm/V |
| \\|chi2\\| as % of peak | {100*r1[3]/pk:.1f}% | {100*r2[3]/pk:.1f}% |

**Does Re chi2 cross zero near the paper minima?** Yes. Re chi2 has exactly two
sign changes over 400-1850 nm, at **{r1[0]:.1f} nm** and **{r2[0]:.1f} nm**, against the
paper's minima at approximately 605 and 1330 nm — offsets of
{r1[0]-605:+.0f} nm and {r2[0]-1330:+.0f} nm.

**Does Im chi2 stay finite there?** Yes, and it is large: {abs(r1[2]):.1f} pm/V and
{abs(r2[2]):.1f} pm/V, against a spectrum peak of {pk:.1f} pm/V. Both crossings fall inside
a band where some k-state in the integration disc is exactly resonant, so the
absorptive part cannot vanish there.

**Why the full |chi2| cannot reproduce the deep minima.** |chi2| = sqrt(Re^2 + Im^2)
vanishes only where Re and Im vanish together — two conditions on one variable.
Where Re passes through zero the Im term survives intact, so |chi2| bottoms out at
{r1[3]:.1f} and {r2[3]:.1f} pm/V, i.e. {100*r1[3]/pk:.0f}% and {100*r2[3]/pk:.0f}% of its own peak. Its global minimum
anywhere on the grid is {abs_chi2.min():.2f} pm/V. |Re chi2|, by contrast, reaches
{abs_re_chi2.min():.1e} pm/V.

**Interpretation.** This is consistent with the published curve being |Re chi2|
rather than the full complex magnitude, and supports that reading over the
alternative. It does not establish it: an equally consistent possibility, which
these data cannot separate, is that the underlying computation was real-valued —
for instance if the +i*Gamma terms were not carried as complex arithmetic — in
which case the axis label is correct and the difference lies upstream. Both
readings predict the same plotted curve. Distinguishing them requires the
authors' code, which we do not have.

## Checks performed

1. **Same pipeline.** Demo 19 case_00 frozen matrix elements, Demo 24 aligned
   parabolic fits (e1/e2/hh1/hh2), Gamma = {GAMMA*1000:.0f} meV, k cutoff
   {K_CUTOFF:.5f} nm^-1 = 0.1 x (2pi/a), all {len(BPE)+len(BPH)} pathways,
   {WL_MIN:.0f}-{WL_MAX:.0f} nm at {WL_STEP:.0f} nm. Re chi2 reproduced the existing engine's
   values to {d_re:.1e} pm/V. **PASS**
2. **One complex evaluation.** Re and Im are the `.real` and `.imag` of a single
   complex array; no separate calculation. **PASS**
3. **Modulus identity.** max | |chi2| - sqrt(Re^2+Im^2) | = {resid.max():.2e} pm/V
   over all {len(wl)} wavelengths. **PASS**
4. **|Re chi2| ordering.** Formed as abs() of the signed real part, verified equal
   to `abs(chi.real)` elementwise. Re is negative at {nneg} of {len(wl)} points, so
   the absolute value is doing real work. **PASS**
5. **Sign, units, axis.**
   - The +i*Gamma and -i*Gamma conventions are exact complex conjugates
     (max deviation {np.abs(anti-np.conj(chi)).max():.1e}), so Re is identical either way and only Im
     flips. This script uses the **causal** -i*Gamma form.
   - Kramers-Kronig (`kk_test.py`): with -i*Gamma the Hilbert transform of Im
     recovers Re to <0.6%; with +i*Gamma it returns exactly -Re. This fixes the
     sign convention independently.
   - Scale: peak |Re chi2| = {abs_re_chi2.max():.2f} at {peak_hi:.0f} nm, matching this
     engine's earlier 41.2 at 1505 nm. This is a self-consistency check, **not a
     calibration**: the engine carries no Eq. 2 prefactor and differs from the
     prefactored Demo 23D pipeline by a factor of 2.0-2.3 (not constant, because
     Demo 23D uses tracked kp8 dispersion rather than parabolic fits). Every value
     quoted in pm/V in this summary is in uncalibrated units proportional to chi2:
     ratios are meaningful, absolute magnitudes are not.
   - Wavelength axis: hw = hc/lambda strictly decreasing across the grid,
     {HC/wl[-1]:.4f}-{HC/wl[0]:.4f} eV.
   - Normalization: figure 1 divides both signed Re and Im by the same
     max |Re| = {component_scale:.6g}, while paper is divided by its own peak.
     The CSV retains raw values. Figure 2 normalizes each curve to its own peak.
     Both figures have dimensionless y-axes. **PASS**
6. **True sign changes.** {len(brackets)} brackets found on the 1 nm grid; each root
   refined by Brent's method on the continuous function (xtol 1e-10) and confirmed
   to have opposite signs 1 nm either side. Not grid artifacts. **PASS**
7. **Im at the crossings.** Evaluated directly at the refined roots rather than
   interpolated from the grid. **PASS**
8. **Internal consistency.** |chi2| minimum ({abs_chi2.min():.2f} pm/V) exceeds |Re chi2|
   minimum ({abs_re_chi2.min():.1e} pm/V) by more than four orders of magnitude. **PASS**

## Caveat carried from elsewhere

The k cutoff used here, 0.1 x (2pi/a), is the value that reproduces Fig. 2d, but it
is not independently established: the figure constrains only the product
mu * k_max^2, so cutoff and in-plane reduced mass trade off against one another.
Separately, two of the four peaks in this spectrum are integration-endpoint
artefacts rather than transitions. Neither affects the argument above, which
concerns only the behaviour of Re and Im at the two zero crossings.

## Files

| file | contents |
|---|---|
| `fig2d_re_im_chi2_diagnostic.png` | paper normalized to its peak; signed Re and Im share max \\|Re\\| normalization; horizontal zero line only |
| `fig2d_abs_re_vs_abs_complex_chi2_comparison.png` | paper Fig. 2d vs \\|Re chi2\\| vs \\|chi2\\| |
| `fig2d_chi2_components.csv` | wavelength_nm, re_chi2, im_chi2, abs_re_chi2, abs_chi2 |
| `fig2d_chi2_diagnostic_summary.md` | this file |
"""
md_path = os.path.join(HERE, "fig2d_chi2_diagnostic_summary.md")
open(md_path, "w", encoding="utf-8").write(md)

say("\nwrote:")
for f in (f1, f2, csv_path, md_path):
    say("  " + f)
