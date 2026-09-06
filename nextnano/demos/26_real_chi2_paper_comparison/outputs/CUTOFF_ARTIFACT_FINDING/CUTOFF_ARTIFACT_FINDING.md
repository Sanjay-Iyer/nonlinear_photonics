# Figure 2d reproduced: P1/P3 are k-integration endpoint artefacts

Date 2026-09-06. Home laptop, no nextnano solver invoked. Existing Demo 23/24
artefacts only; nothing in `HOME_EXHAUSTIVE_AUDIT/` or any prior output was modified.

## Source that unblocked this

`docs/equation_2_from_paper/Xi2 (1).m` is the author-side Octave routine. Two lines
decide everything:

```matlab
P(st,:)=polyfit(ke(8:16),eigens(states(st),8:16),2);   % parabolic FIT over a narrow k window
...
integral(@(k) funer(wic,wic2,k),0,krng)                % then INTEGRATE THE PARABOLA out to krng
```

The model dispersion is a parabola extrapolated well past its fit range. That is why
audit TEST 134 ("0.20 pi/a candidate") was recorded NOT TESTABLE: it correctly refused
to extrapolate the *nextnano* dispersion beyond 0.125 pi/a. But the author's algorithm
performs exactly that extrapolation by construction, so the test **is** runnable at home
without any new solve.

## The mathematics

Substituting u = k^2, the author's integrand is exact:

    pi * int_0^K2 du /((M1 u + a)(M2 u + b))
      = (pi/C) [ log((M2 K2 + b)/b) - log((M1 K2 + a)/a) ],   C = M2 a - M1 b

with a = dE13 - 2w + i g, b = dE23 - w + i g. Each log diverges **twice**:

- at the band edge, |a| -> 0, i.e. 2hw = dE(0)            -> the physical resonance
- at the cutoff,   |M1 K2 + a| -> 0, i.e. 2hw = dE(0) + M K2  -> **pure numerics**

A hard integration limit therefore *always* manufactures a mirror peak of opposite
sign, and it carries its own 1w/2w pair. One cutoff -> four peaks, with a sign change
(a zero) between each opposite-signed pair. That is the exact topology of Fig. 2d.

## Numerical result

Cutoff needed to place the artefact at the paper's 2.296 eV (= 540 nm 1w = 1080 nm 2w):

| transition | dE(0) eV | M eV nm^2 | krng nm^-1 | krng / (pi/a) |
|---|---|---|---|---|
| e1-hh1 | 1.49335 | 0.61881 | 1.13890 | 0.2049 |
| e1-hh2 | 1.52837 | 0.57679 | 1.15364 | 0.2076 |
| e2-hh1 | 1.61322 | 0.54506 | 1.11923 | 0.2014 |
| e2-hh2 | 1.64823 | 0.50304 | 1.13478 | 0.2042 |

All four cluster within 3% of **0.2045 pi/a = 0.1 x (2pi/a)** - i.e. "10% of the BZ"
with the zone radius taken as **2pi/a** (Gamma-X) rather than the **pi/a** used in our
production runs. This resolves audit TEST 133, which left the BZ convention open.

At krng = 0.1 x 2pi/a, observable |Re chi2|:

| feature | paper nm | model nm | err |
|---|---|---|---|
| P1 peak | 540 | 546 | +6 |
| Z1 zero | 605 | 617 | +12 |
| P2 peak | 760 | 752 | -8 |
| P3 peak | 1080 | 1093 | +13 |
| Z2 zero | 1330 | 1327 | -3 |
| P4 peak | 1520 | 1505 | -15 |

normalised RMSE **0.0658**, correlation **+0.941** (production 0.1 x pi/a: 0.2374 / +0.305,
and no P1/P3 at all). All six Fig. 2d features are recovered for the first time.

## Artefact, not physics - two independent discriminators

1. **The peak tracks the integration limit.** As krng goes 0.10 -> 0.30 pi/a the "P1"
   peak marches 687, 656, 621, 584, 561, 546, 540, 531, 517, 473, 407 nm, while P2 (752)
   and P4 (1505) never move. This continues the march already recorded in Demo 24N
   (1502 -> 1431 -> 1376 -> 1318 nm over 0.05 -> 0.125 pi/a) straight onto the paper's P3.
2. **Softening the boundary moves and kills it.** Replacing the hard cut with a cos^2
   taper of fractional width t at the top of the k range:

   | t | P1 | P3 | P2 | P4 |
   |---|---|---|---|---|
   | 0.00 | 546 (0.38) | 1092 (0.93) | 752 | 1504 |
   | 0.10 | 560 (0.28) | 1122 (0.71) | 752 | 1504 |
   | 0.35 | 596 (0.19) | 1192 (0.52) | 752 | 1504 |
   | 0.50 | 612 (0.16) | 1226 (0.45) | 752 | 1504 |

   (parentheses = height as fraction of spectrum max.) Genuine band-structure
   resonances are pinned; these are not.

The integral is also simply not converged: peak |Re chi2| rises monotonically
19.9 -> 32.3 -> 37.8 -> 41.2 -> 43.3 -> 44.7 -> 46.4 pm/V over krng 0.05 -> 0.40 pi/a.

## Reconciliation with the Demo 24N "unreachable" result

Demo 24N established that 2.296 eV is unreachable by any bound-subband pair, because the
electron subbands cross the Al0.55Ga0.45As CB edge at k ~ 0.73-0.85 nm^-1 where the
largest Ee - Ehh has only reached ~1.93-1.97 eV. **That remains correct for the real kp8
dispersion.** The parabola has no barrier and keeps rising, so it reaches 2.296 eV at
k ~ 1.11-1.14 nm^-1 - beyond the k where those states have already left the well.
Both results are consistent; the paper's model simply is not the real dispersion there.

## Observable: |Re chi2|, not |chi2|

Same krng, same everything else:

| observable | nRMSE | corr | value at Z1 | value at Z2 |
|---|---|---|---|---|
| \|Re chi2\| | **0.0658** | **+0.941** | 0.014 | 0.017 |
| \|chi2\| (full complex) | 0.2374 | +0.441 | 0.265 | 0.580 |

With Gamma = 5 meV, |chi2| = 0 needs Re = 0 **and** Im = 0 at the same wavelength - a
codimension-2 condition a one-parameter curve does not meet. The published curve touches
zero twice, so it cannot be the complex magnitude. This is provable from the figure alone
and supersedes the weaker "no evidence of a labelling inconsistency" conclusion in
`PAPER_OBSERVABLE_AUDIT.md`, which did not use the zero-touching argument.

## Not explained here

Absolute scale. Peak |Re chi2| = 41.2 pm/V against the paper's 3950 pm/V, a factor ~96.
`Xi2.m` mixes SI (`e0` F/m, `ee` C), esu (`ee0=1`), angstroms (`rehh=7.51`) and eV-s
(`hbr`) inside `Apre`, then applies an ad-hoc `1e9`. The vertical calibration is not
reproducible from the file as written.

## Other defects in Xi2.m (shape-relevant, untested here)

- **Spinor components are summed, not inner-producted.** `wftn(:,st)` adds all eight kp8
  components into one scalar, so overlaps compute |sum_n psi_n|^2 cross terms instead of
  sum_n |psi_n|^2. Orthonormality and HH/LH identity are both destroyed - the same failure
  mode as the "hh2 is 97.6% LH" finding (TEST 136).
- **`+i*gma`** puts the pole in the upper half plane (gain, not loss). Harmless for
  Re/abs, wrong sign for Im.
- **`nbdsts=9` with `find(eig(:,11)~=0)`** retains the k-vector row as a state whenever
  ke(11) != 0, shifting every state index by one.
- **`hheig=find(eigens(:,11)<0.3)`** hard-codes the CB/VB split at 0.3 eV. Our nextnano
  output has holes at 1.41-1.45 eV and electrons at 2.95-3.09 eV, so this selects nothing.
- **`z=d-60`** hard-codes the dipole origin. The electron+hole sum is genuinely
  origin-invariant (verified: 5.1e-13 pm/V under a 20 nm shift), but only if both are
  summed - electron-only is 10.7x larger (441 vs 41 pm/V) and origin-dependent.

## Files

- `cutoff_test.py` - analytic k-integral, cutoff prediction table, krng scan
- `final_check.py` - BZ-convention test, gauge/origin controls, convergence
- `taper.py` - hard-cut vs smooth-taper discriminator, figure
- `demo26_figure2_explained.png`

Run with `C:\Users\iyer95\miniconda3\envs\NMIP\python.exe`.
