# v3 Ax / BoTorch audit

Reviewer: Ax/BoTorch engineer. Environment: ax-platform 1.3.1, botorch 0.18.1,
torch 2.12.1+cpu.

**Verdict: PASS WITH WARNINGS.**

---

## 1. Adapter reconstruction

**PASS.** `fit_status: refitted_current_generation_node`, `TorchAdapter`,
16 observations, node MBM → MBM, `generation_strategy_advanced: False`,
`new_trials_generated: False`, snapshot hash unchanged. The reconstruction
loads its own `Client` and fits through `GenerationNode._fit`, which does not
transition; `GenerationStrategy.fit` is still correctly avoided because it calls
`_maybe_transition_to_next_node` first.

## 2. Search-space hierarchy and branch validity

**PASS — and this is where the most consequential fix landed.**

The hierarchical space is sound (two-valued `interface_mode` root). What was
wrong was *what got fed to it*: 350 of 625 points on the asymmetry slice were
graded coordinates whose realized width fell below 0.80 nm. Ax accepted them —
they are legal parameterizations — and the model dutifully predicted. But the
**physical structure at all of them is the same abrupt design**, so the surface
showed a graded continuum over a region where nothing varied, repeated once per
profile label.

Legality in the Ax space is not sufficiency for a physical plot.
`_branch_validity` now checks membership of the branch a point *claims*, and
withholds it with a reason otherwise.

⚠️ Consequence to read correctly: the graded region of a v3 surrogate surface is
genuinely **sparse**. That sparsity is the truth — v3 could not build grades
there — and should not be interpolated over.

## 3. Objective and constraints

**PASS.** Objective `relative_chi2_at_target_wavelength_abs` (maximize). Three
modelled constraints: `absolute_detuning_nm <= 15`,
`maximum_boundary_probability <= 0.001`, `state_tracking_confidence >= 0.8`.
The **absolute** detuning is constrained; `signed_detuning_nm` appears in no
constraint anywhere (searched). Binary 0/1 validity flags remain in
`post_processing_qc` and never enter the surrogate —
`test_binary_qc_flags_never_enter_the_feasibility_product` pins this, closing
defect 11.

⚠️ `maximum_boundary_probability` is effectively constant, so it contributes
nothing to the model and its Sobol indices are NaN. It should move to
`never_model` in v4 (see the physics audit §6).

## 4. Feasibility, and why the acquisition surface needed rebuilding

**This campaign is constraint-dominated**: 3 of 16 completed trials feasible,
t0021 at −13 nm against a 15 nm bound, t0022 failing at −16 nm. An
**unconstrained** objective surface therefore has its maximum in infeasible
territory, and presenting it as "where to look next" is actively wrong.

Added per grid point:

- `probability_satisfies_<metric>` per modelled constraint, from Gaussian tail
  probabilities of the reconstructed posterior, with the direction taken from
  the constraint operator (`<=` → `P(y ≤ b)`, `>=` → `P(y ≥ b)`);
- `probability_of_feasibility` — their product;
- `constrained_expected_improvement_proxy` = EI × P(feasible).

⚠️ **Three honest limitations, all stated in the row itself:**

1. this is **not** Ax's acquisition. Ax generated with a Monte-Carlo,
   constraint-weighted, noisy-observation acquisition (qLogNoisyEI). Analytic EI
   on the objective is a different function of the same posterior, and the exact
   acquisition **cannot be replayed from a snapshot** — the sampler state is not
   serialized. `expected_improvement_method` says so explicitly;
2. the joint probability multiplies per-constraint probabilities, assuming
   conditional independence. Ax does not assume that. Labelled a *proxy*;
3. with 16 observations these probabilities are as uncertain as the posterior
   they come from.

## 5. Model error is real and should be shown

t0022 was proposed by the model and came back at −16 nm detuning, i.e.
infeasible. Comparing the reconstructed posterior's prediction at t0022 against
its observed detuning is the cheapest honest measure of how much this surrogate
should be trusted near the boundary, and Stage 5 should report it. With 16
points across 4 mixed dimensions, the posterior's small interior standard errors
are **not** calibrated uncertainty.

## 6. Iteration semantics

**PASS.** The ledger's `iteration` counts *proposal attempts* and reached 17 in
a 10-iteration study, because seven refusals advanced it. Plots captioned "by BO
iteration" now use `mbm_iteration_number` 1–10 over
`t0007 t0008 t0009 t0011 t0017 t0018 t0019 t0020 t0021 t0022`, and refusals are
excluded from iteration plots entirely.
`test_rejections_do_not_shift_completed_numbering` proves removing the refusals
does not renumber the evaluations.

## 7. Candidate generation

**PASS.** The v3 mapping spans `[0, maximum]`, so a low fraction at a narrow
barrier is unbuildable — 7 of 23 proposals were spent this way, six of them
`erf`. The optional interval mapping spans `[minimum, maximum]` instead, making
every fraction resolvable by construction; refusal is then reserved for
geometries with no room at all (barrier < 0.90 nm under the current
central-barrier rule).

It is **opt-in and schema-recorded** because it changes what a stored fraction
means. v3's recorded observations are untouched and all seven refusals still
refuse under the default.

## 8. Parameter importance

**PASS WITH WARNINGS.** Sixteen observations over four mixed dimensions. Indices
describe the fitted surrogate, not the physics; negative first-order Sobol
values are estimator noise at this sample size and are reported rather than
clipped; NaN indices for the constant boundary metric are reported as undefined,
not zero. No physical ranking may be drawn from them.

## Risks from the brief

| # | Risk | Finding |
|---|---|---|
| 4 | sub-resolution rejections labelled duplicates | fixed; 0 duplicates in v3 |
| 8 | collapsed points marked prediction-available | fixed; 350/625 withheld with reasons |
| 9 | analytic EI mistaken for Ax's acquisition | explicit denial + constrained proxy |
| 11 | binary QC flags described as Ax-modelled | fixed and tested |
| 14 | generation proposes many sub-resolution grades | interval mapping available; v3 default preserved |
| 17 | state tracking depends on evaluation order | **real, unresolved** — Stage 5 §E |
| 18 | boundary probability nearly constant | confirmed; recommended for `never_model` in v4 |

**Signed: PASS WITH WARNINGS.**
