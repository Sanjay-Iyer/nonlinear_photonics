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

## What it reproduces

From the licensed work-laptop run of 2026-07-31 (38 cases at production mesh,
commit `d1aed8d`), with **no material parameter adjusted**:

| quantity | paper | this repository | difference | status |
|---|---|---|---|---|
| E₁ − HH₁ | 1.49 eV | **1.48906 eV** | −0.94 meV | `reproduced` |
| E₂ − HH₂ | 1.62 eV | **1.62967 eV** | +9.7 meV | `reproduced` |
| two-photon resonance | ~1520 nm | **1521.6 nm** | +1.6 nm | `reproduced` |
| \|χ⁽²⁾\| peak, 1400–1800 nm scan | ~1520 nm | **1519 nm** | −1 nm | `reproduced` |
| barrier optimum | 1 nm | **1.0 nm** | 0 | `reproduced` |
| graded/abrupt ratio | 0.513 | **0.571** | +0.058 | `reproduced` |
| asymmetry optimum | 0.42 | see below | — | **`provisionally_consistent`** |

Orthonormality holds everywhere: the worst case across all 38 runs is 1.6e-13
against a 1e-3 tolerance.

A committed fixture under
`nextnano/tests/fixtures/nextnano_pp_3_0_0/demo11_acqw_paper/` runs the whole
pipeline in the test suite without a licence.

## What the first licensed run exposed

Three of the four issues below were invisible in the report that run produced,
because every individual comparison was inside its tolerance.

**1. A false failure at the parity zero.** The symmetric structure at s = 0 has
χ⁽²⁾ = 0 by parity, and came out at 5.7e-14. The origin-independence check
divided the origin-shift residual by that, turning ~1e-14 of rounding noise
into a 14 % "relative error" and failing the whole criterion. The check now
compares absolutely below a configured scale floor and relatively above it, and
records which comparison it used. The near-zero case is still checked — against
the tolerance that means something there.

**2. The asymmetry optimum was scored on the wrong metric.** χ⁽²⁾ was compared
at a fixed 1550 nm across a sweep in which the two-photon resonance moves about
100 nm against a 5 meV linewidth. Every structure was being sampled at a
different detuning, so the ranking partly measured which resonance happened to
land nearest 1550 nm. Under the detuning-independent peak metric the optimum
moves from s = 0.42 to **s = 0.50** — and beats its runner-up (s = 0.55) by
**0.4 %**, on a sweep whose grid convergence still drifts about 1 %. That is not
a resolved optimum in either direction.

**3. χ⁽²⁾(s) is discontinuous.** Between s = 0.38 and s = 0.42 the peak
magnitude jumps by a factor of **8.5**, while ⟨e₂|hh₂⟩ collapses from 0.958 to
0.448 and E_hh₂ reverses direction. An energy level that turns around under a
monotonic change of geometry is what an avoided crossing looks like when states
are followed by index. The paper's design point sits exactly on it.

**4. The state-count convergence check was vacuous.** Requesting 3, 4 and 6
states from the solver gave χ⁽²⁾ agreeing to ~1e-13 — because `chi2_spectrum`
sums over the first `max_states_per_band` states of each band regardless of how
many the solver returned. All three cases evaluated an identical number of
identical terms. The knob that widens the sum is now separate, swept in its own
right, and the whole path is audited layer by layer.

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

## The stages

| stage | what it does | solver cases |
|---|---|---|
| 1 | electronic structure of the published design | 1 |
| 2 | grid / domain / quantum-region / state-count / summation-window convergence | 15 |
| 2p | padding convergence repeated at five asymmetries, not only at 0.42 | 15 |
| 3 | asymmetry sweep at fixed 10 nm total well | 14 |
| 3b | refined asymmetry sweep, s = 0.36–0.52 in steps of 0.01 | 17 |
| 4 | tunnelling-barrier sweep, 0.5–5 nm | 9 |
| 5 | χ⁽²⁾ via Eq. 2 in three modes | post-processing |
| 6 | wavelength dependence, broad and telecom-focused | post-processing |
| 7 | abrupt versus 1 nm graded interfaces | 2 |
| 8 | the classified comparison report | — |

73 solver cases total. Stage 3b and the physical-state tracking that consumes
it exist because of what the first licensed run found; see below.

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

## The two χ⁽²⁾ metrics

Sweep optima are reported under both, separately, and they are not
interchangeable.

| metric | what it measures | used for |
|---|---|---|
| `peak_chi2_magnitude` | largest \|χ⁽²⁾\| anywhere in the scanned band — intrinsic, detuning-independent | **primary**: the paper's optimum claims |
| `chi2_at_reference_wavelength` | \|χ⁽²⁾\| at 1550 nm — what a device at that wavelength sees | secondary, application-specific |

The fixed-wavelength value is never labelled the intrinsic χ⁽²⁾ maximum. Where
the two disagree — as they do for the asymmetry sweep and do not for the
barrier sweep — the report says so and shows both.

## Classification vocabulary

Every comparison gets exactly one classification, saying what *kind* of
comparison it is:

- `directly_reproduced` — computed here and agrees within a stated tolerance
- `qualitatively_reproduced` — the trend or the location of an optimum matches
- `calibrated_reproduction` — agrees because a factor was fitted to it
- `not_reproducible_from_available_information` — the paper omits an input
- `outside_nextnano_scope` — depends on physics this calculation does not model
- `requires_author_data_or_code`

## Reproduction status

Separately, every *claim* gets one status, saying how far the work has actually
got with it. Being inside a tolerance is not the same as being reproduced, and
the two are not merged:

- `mechanically_completed` — it ran; nothing is claimed about the number
- `numerically_converged` — stable against the numerical parameters swept
- `reproduced` — agrees within tolerance, **and** on the metric the paper's
  claim is actually about
- `provisionally_consistent` — consistent, but resting on something unsettled
- `unresolved` — raises a question this run cannot answer
- `failed` — did not pass

These are per-claim and deliberately independent. The reference structure's
1520 nm resonance is `reproduced` on its own evidence and is **not** downgraded
because the asymmetry optimum is unresolved; they are different claims about
different things.

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
5. χ⁽²⁾ **peak-magnitude** maximum near s = 0.42 — provisional; scored on the
   intrinsic metric, not the fixed-wavelength one.
6. χ⁽²⁾(s) is smooth enough for an optimum to mean anything: no adjacent-point
   step larger than a factor of 2.
7. χ⁽²⁾ vanishes at the symmetric limit.
8. Barrier optimum near 1 nm.
9. Grading reduces χ⁽²⁾ in roughly the published proportion.
10. Envelopes orthonormal and χ⁽²⁾ origin-independent.
11. Eq. 2 summed over exactly the configured state window.
12. The state-count sweep actually varied the sum.
13. Every state entering Eq. 2 passes the bound-state criterion.

## Quasi-bound states

Boundary probability is recorded per state and per end of the domain, not just
as a maximum — a state leaking out of one contact and one leaking symmetrically
out of both are different defects. `validation.quasi_bound_state_policy`
chooses what happens to a state that fails the bound-state criterion:

| policy | effect |
|---|---|
| `warn` *(default)* | keep it in Eq. 2, flag the case |
| `exclude` | drop it from Eq. 2 and record why |
| `fail_case` | mark the case invalid |

`warn` is the default because it is what every result to date was produced
with. `exclude` changes which states Eq. 2 sums over and therefore changes the
physics; it is a deliberate experiment, not a cleanup. The policy in force is
named in the validation report either way.

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

- **Home, syntax:** all decks parse cleanly under Free nextnano++ 3.0.0,
  including the four `ternary_linear` graded interfaces.
- **Licensed, 2026-07-31:** 38 cases at production mesh, all completed. That run
  produced the transition energies, resonances, barrier optimum and
  graded/abrupt ratio above, and exposed the four issues listed near the top.
- **Still owed on the licensed laptop:** the 35 new cases (Stage 2 summation
  window, Stage 2p padding at five asymmetries, Stage 3b refined sweep), the
  state-count audit, and physical-state tracking across the refined sweep.

## Work-laptop run

The demo takes no flags; everything scientific is in `demo.yaml`.

```bash
git pull
```

```bash
conda activate llm
```

```bash
python nextnano/scripts/run_input.py --check-config
```

```bash
python nextnano/demos/11_paper_validation_interband_chi2_acqw/run.py
```

```bash
python nextnano/scripts/audit_state_counts.py
```

```bash
python nextnano/scripts/bundle_results.py --include-plots
```

Set `$env:PYTHONIOENCODING="utf-8"` first if you are piping output; the reports
contain `χ⁽²⁾`.

### What to check

- [ ] `paper_comparison_report.md`: **reproduction status table first**, then
      the two-metric optimum table.
- [ ] `audit_state_counts.py` reports PASS, not INCONCLUSIVE. Anything else
      means state-count convergence is still unverified.
- [ ] `refined_chi2_raw_vs_tracked.png`: do the two curves coincide? If they do,
      the s = 0.38 → 0.42 cliff is **not** a labelling artifact and needs
      another explanation. If they diverge, the raw-index curve was comparing
      different physical states at different points and its optimum meant
      nothing.
- [ ] `refined_assignment_overlap.png`: a dip marks where the tracker found the
      crossing hard. Cross-check against `state_tracking.csv` ambiguity flags.
- [ ] `chi2_vs_asymmetry.png`: both metrics plotted; the discontinuity is not
      smoothed and should still be visible.
- [ ] Stage 2p: does boundary probability come down at 9 nm padding at *every*
      probed asymmetry, or only at 0.42?
- [ ] `chi2_vs_barrier.png` peaks near 1 nm under both metrics.
- [ ] `envelopes_orthonormal` and `chi2_origin_independent` PASS everywhere —
      including s = 0, which must now pass on its absolute residual.
- [ ] Nothing anywhere reports a pm/V value while in relative mode.
