# Demo 15 — broad-search scope (specified, NOT yet implemented)

Demo 14 is the **paper-anchored** campaign: it holds total thickness, barrier
alloy and the asymmetry window near the Ramesh values so that an absolute pm/V
number can be checked against a published one. Demo 15 is the **broad search**:
same material family, same absolute objective, but the paper is an anchor rather
than a cage.

This file records the agreed scope so the next session starts from a decision,
not a discussion. **None of it is built yet.**

## What changes from Demo 14

| Parameter | Demo 14 | Demo 15 |
|---|---|---|
| `total_qw_thickness_nm` | fixed 10.0 | **BO parameter**, 8.0–12.5 |
| `asymmetry_s` | 0.30–0.55 | **0.00–0.9293** (see below) |
| `central_barrier_thickness_nm` | 0.85–2.50 | **0.25–3.00** |
| `central_barrier_al_fraction` | fixed 0.55 | **BO parameter**, 0.35–0.60 |
| grading widths (each) | 0.40–1.40 | **0.20–2.00** |
| detuning ≤ 40 nm | hard Ax constraint | **diagnostic only**, `detuning_hard_limit_nm: null` |
| spectral scan | 1400–1800 nm | ~1400–1700 nm, boundary-hit flagged |
| `N_z` | fixed 3.3333e7 m⁻¹ | **per-trial**, from the realized period |
| grading profile | linear/fermi/erf/cosine | unchanged |
| material system | GaAs / AlGaAs | unchanged |
| budget | 30 completed | 30 completed, labelled **exploratory** |

## The asymmetry ceiling is physics, not caution

`d_thin = D(1-s)/2`, so a free `D` makes large `s` produce sub-monolayer wells:
at D = 8.0 nm, s = 0.99 gives a **0.04 nm** thin well, which is not a structure
and which the envelope-function model does not describe.

Zincblende GaAs has a = 0.565325 nm, so one monolayer along [001] is
a/2 = 0.282662 nm. Requiring at least one monolayer:

```
s_max(D) = 1 - 2 * 0.282662 / D
```

| D | s_max |
|---|---|
| 8.0 nm | 0.9293 |
| 10.0 nm | 0.9435 |
| 12.5 nm | 0.9548 |

`s_max` **increases** with D, so evaluating it at the smallest D gives a bound
valid across the whole range: **s ∈ [0.00, 0.9293]** is feasible by construction
for every `D ∈ [8.0, 12.5]`. No Ax constraint, no rejection, no wasted licensed
proposal. It covers 93.9% of the requested 0.00–0.99 range, and the missing 6%
is the sub-monolayer region.

Record `requested_asymmetry_upper_bound: 0.99` beside
`realized_asymmetry_upper_bound: 0.9293` with the monolayer rule, so the
narrowing is visible rather than silent.

## Barrier thinner than Demo 14 allowed

0.25 nm is below one monolayer. It is solvable, and it is not excluded — but it
must be **labelled**, per the three thresholds already in the Demo 14 config:

- `< 0.25 nm` — outside the continuum envelope model;
- `0.25–0.85 nm` — exploratory theoretical structure, sub-fabrication;
- `≥ 0.85 nm` — fabrication-realistic (Demo 13's floor, 3 ML).

Store `requested` and `mesh-realized` barrier thickness separately for every
trial, plus the monolayer count.

## Al fraction becomes per-trial — the one change that touches verified code

`grading14.build_profile` and `grading14.measure` **already take
`max_al_fraction` as a parameter**, so the renderer generalizes without
modification. What must change is the caller: `demo14.build_grading` currently
passes the fixed `cfg["materials"]["barrier_al_fraction"]`, and Demo 15 must
pass the trial's own `central_barrier_al_fraction`.

The consequence to watch: the nominal 10/90 thresholds are
`0.10 * x_max` and `0.90 * x_max`, **not** the constants 0.055 and 0.495. Those
literals appear in `test_demo14_grading.py` as the module-level `XMAX`, which
must become a parameter there. `measure()` itself already computes them from its
argument and needs no change.

## N_z must follow the geometry, or BO can win by packing

With `D` and the central barrier both free, the physical period changes per
trial:

```
L_period = D + t_barrier + period_barrier(18.2 nm)
N_z      = 1 / L_period
```

The Ramesh reference reproduces L = 10.0 + 1.8 + 18.2 = 30.0 nm and
N_z = 3.3333e7 m⁻¹, which is the check that the formula is right.

**This creates a real interpretation hazard.** χ⁽²⁾ is linear in N_z, so a
design can raise the objective purely by shortening the period — more nonlinear
units per metre, not a better coupled-well response. Demo 15 must therefore
report both:

- `chi2_xzx_abs_at_1550_pm_per_V` — physical, per-trial N_z. **The objective.**
- `chi2_xzx_abs_at_1550_fixed_period_pm_per_V` — same states renormalized to the
  30 nm reference period. **Diagnostic only, never optimized.**

If the best trial's advantage disappears under the fixed-period diagnostic, the
campaign found packing, not physics, and the report must say so.

## Detuning stops being a feasibility gate

The objective already evaluates χ⁽²⁾ *at* 1550 nm, so a design with a large
response at 1550 is not bad merely because an even larger peak sits 60 nm away.
`detuning_hard_limit_nm: null` by default; `peak_wavelength_nm`,
`signed_detuning_nm`, `absolute_detuning_nm` and `detuning_side` stay recorded.

Because peaks may now sit far from 1550, `peak_at_scan_boundary` must be an
anomaly, not a silent result.

## Required at campaign close

- **Boundary-hit analysis.** Flag `SEARCH_SPACE_BOUNDARY_PRESSURE` per parameter
  when the best trials cluster at a bound, and recommend expansion from evidence
  rather than expanding everything again.
- **Reference-vs-best comparison**: the Ramesh geometry and the best Demo 15
  design side by side, with absolute and percentage improvement — against the
  *modelled* reference, never against an experimental effective χ⁽²⁾, which is
  not the same quantity.
- **Language**: "best design found in a 30-trial broad-search exploratory
  campaign". Never "global optimum" — 30 trials over six dimensions is a scout,
  not a survey.

## Physics QC does not relax

Broader design freedom, identical rigour: boundary probability ≤ 1e-3, tracking
confidence ≥ 0.8, orthonormality, origin independence, required states, physical
QC, absolute-units validity, finite χ⁽²⁾, valid composition profile. The
optimizer must not be able to win through unbound states, state swaps,
sub-resolution geometry, NaNs or scan-boundary artifacts.

## What Demo 15 inherits unchanged

`grading14`, `physics14`, `runlog14`, `solver14`, `bundle14`, the mock solver,
the licensed startup gate and the whole run harness. The startup gate still
applies: `ternary_import` remains unexecuted by any nextnano++ build in this
project, and Demo 15 uses it for three of four families exactly as Demo 14 does.

## Stress test to run before the first Demo 15 campaign

Tens of thousands of solver-free samples over the full six-dimensional space,
reporting: samples, buildable, rejected with reasons, minimum realized thin well,
minimum realized barrier, maximum interface overlap, composition bounds. The
target is 100% buildable; anything less means the parameterization, not the
science, needs changing.
