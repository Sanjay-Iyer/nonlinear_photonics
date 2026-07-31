# Demo 11 — paper validation: interband χ⁽²⁾ of asymmetric coupled quantum wells

**Target:** *Enhanced Interband Optical Nonlinearities from Coupled Quantum
Wells*, Ramesh et al., [arXiv:2602.23246v1](https://arxiv.org/abs/2602.23246).

This is the capstone. It does not introduce new physics — it asks whether the
machinery built in Demos 1–10 reproduces a published result, and says plainly,
claim by claim, where it does and where it cannot.

## The headline, stated first

**The absolute χ⁽²⁾ magnitude is not independently reproducible from this
paper.** The paper does not publish the HSE06 unit-cell matrix element
`r_e,hh`, the wells-per-unit-length `N_z`, or the k-space quadrature
conventions, and those three set the scale. Anyone claiming to have
independently reproduced "2340 pm/V" from the paper alone is fitting, not
predicting.

What **is** reproducible, and what this demo actually tests:

- the electronic structure of the designed layers;
- the interband transition energies;
- the resonance wavelengths;
- the asymmetry, barrier-thickness, and interface-grading **trends**, which are
  ratios in which the unknown absolute scale cancels.

## What it already reproduces

Run at home on the Free edition against the paper's exact designed structure,
with **no material parameter adjusted**:

| quantity | paper | this repository | difference |
|---|---|---|---|
| E₁ − HH₁ | 1.49 eV | **1.4897 eV** | −0.3 meV |
| E₂ − HH₂ | 1.62 eV | **1.6316 eV** | +11.6 meV |
| two-photon resonance | ~1520 nm | **1519.8 nm** | 0.2 nm |
| one-photon resonance | ~760 nm | **759.9 nm** | 0.1 nm |
| \|χ⁽²⁾\| peak, 1400–1800 nm scan | ~1520 nm | **1518.0 nm** | 2 nm |
| asymmetry s | 0.42 | 0.42 | — |

The states also show the expected coupled-well character: e₁ is 95 % in the
thick well, e₂ is 73 % in the thin well.

That fixture is committed under
`nextnano/tests/fixtures/nextnano_pp_3_0_0/demo11_acqw_paper/` and the whole
pipeline runs against it in the test suite.

## Physical structure

```
AlGaAs(9.1) | GaAs 7.1 | AlGaAs 1.8 | GaAs 2.9 | AlGaAs(9.1)      = 30 nm period
             thick well   tunnel      thin well
```

`s = (7.1 − 2.9)/(7.1 + 2.9) = 0.42`, total GaAs 10 nm, Al fraction 0.55. The
18.2 nm period barrier is split in half on each side, giving the paper's 30 nm
period exactly.

> The paper's Section 2.2 says "Each period is 20 nm" in the same sentence that
> lists 10 + 1.8 + 18.2. Its own Fig. 1 caption says 30 nm, and the arithmetic
> agrees. We take 20 nm to be a typo, and record it, because `N_z` depends on it.

**Al₀.₅₅Ga₀.₄₅As is indirect** — X lies below Γ above x ≈ 0.45. This deck solves
the Γ valley only, which is the valley governing the interband transition the
paper measures. X-valley barrier states would matter for transport or capture;
neither is part of this reproduction.

## The eight stages

| stage | what it does | solver cases |
|---|---|---|
| 1 | electronic structure of the published design | 1 |
| 2 | grid / domain / quantum-region / state-count convergence | 12 |
| 3 | asymmetry sweep at fixed 10 nm total well | 14 |
| 4 | tunnelling-barrier sweep, 0.5–5 nm | 9 |
| 5 | χ⁽²⁾ via Eq. 2 in three modes | post-processing |
| 6 | wavelength dependence, broad and telecom-focused | post-processing |
| 7 | abrupt versus 1 nm graded interfaces | 2 |
| 8 | the classified comparison report | — |

38 solver cases total.

## The χ⁽²⁾ equation

`_shared/chi2.py` implements the paper's Eq. 2 exactly. Three properties are
enforced and unit-tested, because each catches a different class of error:

1. **A symmetric structure gives identically zero.** Parity forbids a
   second-order response. This is the paper's own claim at both ends of the
   asymmetry sweep, and it comes out as a hard zero, not a small number.
2. **The result is independent of where z = 0 is placed** — but *only* for an
   orthonormal envelope basis. Eq. 2 contains diagonal dipoles `⟨ψᵢ|z|ψᵢ⟩`,
   which individually shift with the origin; the dependence cancels between its
   two terms. A non-orthogonal basis therefore makes χ⁽²⁾ depend on an
   arbitrary coordinate choice, so the module **refuses** rather than returning
   a meaningless number. Both the orthonormality error and the measured
   origin-dependence go into every run manifest.
3. **Resonances land at `2ħω = E` and `ħω = E`.** The paper's "peaks around
   760 nm and 1520 nm" are one physical statement about the same 1.62 eV
   transition, not two coincidences.

### Three modes, deliberately separated

| mode | needs | may claim |
|---|---|---|
| `relative` *(default)* | nothing beyond the solver | lineshape, resonance positions, all trends. **Arbitrary units.** |
| `absolute` | `r_e_hh_nm` **and** `n_wells_per_metre` | a genuine pm/V prediction |
| `calibrated` | one published value + a named source | a *calibrated reproduction*, explicitly not independent |

`absolute` **refuses to run** without both inputs. `demo.yaml` leaves them
`null`, so the default run stays relative rather than inventing a scale.

`calibrated` fits exactly one global real factor and stamps every artifact. It
agrees with the calibration target **by construction**, which the report says
out loud — that entry carries no evidential weight on its own.

## Run

```bash
python nextnano/demos/11_paper_validation_interband_chi2_acqw/run.py
```

## Outputs

Beyond the usual per-case artifacts:

- `paper_comparison_report.md` — the classified comparison, headline first
- `assumptions_and_unknowns.yaml` — everything the reproduction rests on
- `comparison.json`, `tables/paper_targets.csv`, `tables/our_results.csv`,
  `tables/comparison_metrics.csv`

Published values live in `paper_targets.yaml`, each with its `kind` and its
`source`, and are **never** mixed with the simulation inputs in `demo.yaml`.
That separation is what stops a change to the model from silently looking like
a change to the paper's claims.

## Classification vocabulary

Every comparison gets exactly one:

- `directly_reproduced` — computed here and agrees within a stated tolerance
- `qualitatively_reproduced` — the trend or the location of an optimum matches
- `calibrated_reproduction` — agrees because a factor was fitted to it
- `not_reproducible_from_available_information` — the paper omits an input
- `outside_nextnano_scope` — depends on physics this calculation does not model
- `requires_author_data_or_code`

The measured multi-period χ⁽²⁾ values (1170, 1345, 1730, 2750 pm/V) are all
`outside_nextnano_scope`. They fold in surface band bending, standing waves,
sample placement, and the Eq. 3 field-overlap extraction with its free
parameter α. An electronic-structure calculation should not reproduce them and
this demo does not try.

## Validation criteria

1. Structural parameters transcribed correctly (bookkeeping, not physics).
2. Ground transition within `transition_energy_tolerance_meV` of 1.49 eV.
3. Excited transition within tolerance of 1.62 eV.
4. The end-to-end Eq. 2 scan peaks near 1520 nm.
5. χ⁽²⁾ maximum near s = 0.42.
6. χ⁽²⁾ vanishes at the symmetric limit.
7. Barrier optimum near 1 nm.
8. Grading reduces χ⁽²⁾ in roughly the published proportion.
9. Envelopes orthonormal and χ⁽²⁾ origin-independent.

## The 1 nm versus 1.8 nm barrier

The paper predicts an ideal optimum near **1 nm** and the fabricated structure
used **1.8 nm**. These are two different statements — an optimisation result and
a growth choice — and the demo reports both rather than treating the difference
as a discrepancy.

## Common failures

- **`absolute mode needs r_e_hh_nm and n_wells_per_metre`.** Working as
  intended. Supply them from a documented source or stay in relative mode.
- **`the e envelopes are not orthonormal`.** Usually too coarse a grid, or
  states taken from different quantum regions. Fix the mesh; do not raise the
  tolerance.
- **Transition energies off by tens of meV.** Check the Al fraction, the band
  offset convention, and the grid before concluding anything about the paper.
  Do **not** tune material parameters to close the gap — record the difference.
- **s = 1.0 in the asymmetry sweep.** That is a single 10 nm well, a different
  geometry. The sweep stops at 0.90; the χ⁽²⁾ → 0 claim at s = 1 is verified
  analytically by the symmetric-structure test instead.

## Licensed-validation status

`implemented_dry_run` — see `nextnano/demos/demo_registry.yaml`.

- **Home, syntax:** all 38 decks parse cleanly under Free nextnano++ 3.0.0,
  including the four `ternary_linear` graded interfaces.
- **Home, execution:** the paper's structure *ran* on the Free edition (it needs
  only Γ + HH at 300 K), on a reduced 0.4 nm grid. That is where the transition
  energies above come from. It is a coarse grid, so those numbers are a strong
  indication rather than a converged result.
- **Still owed on the licensed laptop:** all 38 cases at production mesh, Stage 2
  convergence, and Stages 3, 4, and 7 in full.

## Work-laptop checklist

```bash
git pull
conda activate NMIP
python nextnano/demos/11_paper_validation_interband_chi2_acqw/run.py
```

- [ ] `paper_comparison_report.md`: check the classification summary first.
- [ ] Stage 2 converged before believing any Stage 5 number.
- [ ] `chi2_vs_asymmetry.png` peaks near s = 0.42 and reaches zero at s = 0.
- [ ] `chi2_vs_barrier.png` peaks near 1 nm.
- [ ] `chi2_focused_wavelength.png` peaks near 1520 nm.
- [ ] Graded/abrupt ratio near the published 1200/2340.
- [ ] `envelopes_orthonormal` and `chi2_origin_independent` PASS everywhere.
- [ ] Nothing anywhere reports a pm/V value while in relative mode.
