# Demo 17C — bulk control calibration and enhancement analysis

Pure Python. **No solver, no licence.** Reads Demo 17's saved artifacts, fits
**one** global scalar to **one** published number, and reports everything else as
a prediction.

## Result

```
K = 2340.0 / 84.7009 = 27.6266      anchored on case_02 @ 1550 nm
```

| | published quantity | predicted | published | error |
|---|---|---:|---:|---:|
| — | ideal abrupt @1550 (**the anchor — not evidence**) | 2340.0 | 2340 | *fitted* |
| **PASS** | Fig. 2d peak height | **4027.5** | 4000 ±15 % | **0.7 %** |
| **PASS** | EDS-profile graded @1550 (1.00 nm grade) | **1247.8** | 1200–1363 | **inside** |
| **PASS** | native/imported twin | 1247.8 | 1200–1363 | inside |

**One fitted scalar, three unfitted published numbers reproduced.** The 1247.8
lands between the paper's two EDS-profile values (Al 1200, Ga 1363), and the
peak lands 0.7 % from the Fig. 2d height that 16F deliberately declined to make
a target — precisely because nothing was fitted to it.

### The two anchors agree

Anchoring instead on the Fig. 2d peak (`--anchor-peak --anchor-target 4000`)
gives **K = 27.4382**, against 27.6266 from the 1550 nm anchor — **0.7 % apart**,
and the roles swap cleanly (the 1550 nm row becomes a prediction at 2324 vs 2340).

Two *independently published* numbers therefore yield the same calibration factor
to under a percent. That is a check on the **spectral shape**: if our lineshape
between 1550 nm and the resonance peak were wrong, the two anchors would
disagree. They don't.

## Why the anchor is not bulk GaAs

The requested design was `K = 377 / χ²_calc,GaAs`, with the bulk value from the
same Eq. 2 evaluator. **That cannot be done, for a physical reason.**

Eq. 2 sums *envelope* asymmetry:

$$\sum_{m,n,l}\frac{\langle\psi_{hh,m}|\psi_{e,n}\rangle\langle\psi_{e,n}|z|\psi_{e,l}\rangle\langle\psi_{e,l}|\psi_{hh,m}\rangle}{(\ldots)} - (\text{valence term})$$

Every factor is a confined-subband integral, and the two terms **cancel exactly**
for any symmetric structure — the paper says so itself and this repo already
carries it as `chi2_zero_at_symmetric_limits: 0.0`. Bulk GaAs has no confined
envelopes, so the same evaluator returns **zero**, and `K = 377/0` is undefined.

Bulk GaAs's 377 pm/V comes from the **zincblende unit-cell bond asymmetry (d14)** —
the unit-cell physics `r_e_hh` parameterises, not the envelope physics Eq. 2
computes. Two different mechanisms. That is exactly why the paper reports the
well as an enhancement *over* bulk rather than as bulk plus a term.

So 377 and 290 pm/V are used for the two roles they genuinely support:

- the **denominator of the enhancement ratio**, and
- the **reference lines** on the calibrated spectrum plot.

The anchor instead comes from the paper's own 2340 pm/V — a number computed by
the *same equation* for the *same class of structure*.

`bulk_reference.chi2_calc_bulk_gaas_raw` and `anchor_mode: bulk_gaas` are
implemented and tested. Set them the moment a raw bulk χ⁽²⁾ exists from a theory
that can produce one; Demo 17C will not invent it.

## Enhancement over bulk — the number that does not depend on K

$$\text{Enhancement}(\lambda)=\frac{\chi^{(2)}_{\text{calibrated}}(\lambda)}{377}=\frac{K\,\chi^{(2)}_{\text{calc}}(\lambda)}{377}$$

Both numerator and denominator are calibrated quantities, so **K cancels**. The
enhancement is not a calibrated result at all — it is what the raw evaluator
already said, expressed against the bulk reference. That makes it the most robust
output of this demo.

| published point | pm/V | enhancement |
|---|---:|---:|
| 4-period measured | 2750 | **7.29×** ← the paper's ">7×" claim |
| ideal abrupt simulated | 2340 | 6.21× |
| 80-period measured | 1730 | 4.59× |
| EDS Ga profile | 1363 | 3.62× |
| EDS Al profile | 1200 | 3.18× |

The paper's **">7× over bulk GaAs" refers to the measured 4-period sample**
(2750/377 = 7.29×), not to the 2340 pm/V ideal-abrupt simulation, which is
6.21×. Both are reported so the claim is checked against the number it actually
describes.

Our cases whose **peak** enhancement lands in the 6–8× band: `case_01` (7.77×),
`case_09`/`case_10` (7.05×). `case_02` reaches 10.68× at peak, 6.21× at 1550 nm.

## What this does and does not show

This is a **calibrated reproduction**, not an absolute prediction. Every artifact
is stamped with that, matching how `_shared/chi2.calibrate` already labels its
own output.

- The **absolute scale** rests on the fitted K and is not independent evidence.
- The **anchor row reproduces its target by construction** — it is arithmetic,
  and it is marked `is_anchor_not_evidence` everywhere.
- What the physics supplies is every **ratio**: between structures, between
  wavelengths, and against bulk. Those were already correct before calibration
  and are unchanged by it.
- The **27.6× K itself is still unexplained.** Demo 17b bounded the candidates —
  N_z counting length (×3) and the Eq.1/Eq.2 or permutation factor (×3, probably
  one factor not two), with `r_e_hh` and the m_j doublet both closed.
  **Calibration removes the offset; it does not identify it.**

## Note on `case_01`

The brief expected `case_01` (0.70 nm grade) at 1200–1350 pm/V; it lands at
1487. The case that matches the paper's graded values is **`case_09`** (1.00 nm
grade, 1247.8 pm/V) — which is also the case 16F used when matching the paper's
graded/abrupt ratio of 0.513, because the EDS-measured profiles are ~1 nm wide.
A 0.70 nm grade is narrower, so a higher χ⁽²⁾ is the expected ordering, not a
discrepancy.

## Files

| file | what it owns |
|---|---|
| `demo17c.yaml` | anchor, bulk reference, the unfitted predictions, enhancement claim |
| `calibration17c.py` | bulk-reference logic, K, application, predictions, artifacts |
| `run_demo17c.py` | CLI and the four-step report |

Outputs to `demo_results/demo_17c/`: `calibrated_summary.csv`,
`calibrated_report.json`, `chi2_calibrated_spectrum.png`.

## Spectra

The committed hand-off has no `chi2_focused.csv`, so the plot draws per-case peak
(triangle) and 1550 nm (circle) markers and says so on the figure rather than
inventing curves. Point `--results-dir` at the raw run tree, or copy the spectra,
for full 1400–1800 nm curves.

## Commands

```bash
python nextnano/demos/17c_bulk_calibration_and_enhancement/run_demo17c.py
```

Anchor on the Fig. 2d peak instead of the 1550 nm value:

```bash
python nextnano/demos/17c_bulk_calibration_and_enhancement/run_demo17c.py --anchor-peak --anchor-target 4000
```

Full spectra from a raw run tree:

```bash
python nextnano/demos/17c_bulk_calibration_and_enhancement/run_demo17c.py --results-dir "C:\nn_results\17_paper_chi2_reproduction_corrected\demo17_20260813T204646Z_cfcb1ed7_81add7"
```

Exit code is 1 if any unfitted prediction falls outside its stated tolerance.
