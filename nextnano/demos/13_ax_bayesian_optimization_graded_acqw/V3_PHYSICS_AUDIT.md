# v3 physics audit

Reviewer: semiconductor quantum-well physicist / nonlinear-photonics materials
scientist. Subject: experiment v3, 16 completed licensed trials, best feasible
t0021.

**Verdict: PASS WITH WARNINGS.** No physically wrong statement survives in the
code or the regenerated reports. Every warning below concerns a claim the data
cannot support.

---

## 1. What v3 actually establishes

| Claim | Status |
|---|---|
| 16 licensed trials completed, 0 mechanical failures | ✅ supported — plumbing |
| 7 graded proposals were geometrically unbuildable and never reached the solver | ✅ supported |
| t0021 is the best **feasible** design found | ✅ supported |
| t0021 is *an optimum* | ❌ **not supported** — see §3 |
| grading helps / hurts | ❌ **not supported** — see §4 |
| relative chi(2) 0.411027 at 1550 nm | ✅ as a *relative* number only |

## 2. Feasibility is the dominant result, and it is not the objective

Three of sixteen completed trials were feasible. The binding constraint is
`absolute_detuning_nm <= 15`; t0021 sits at **−13 nm** signed detuning, i.e.
**87 % of the way to the constraint boundary**, and t0022 failed at −16 nm.

This reframes the campaign: the optimizer was not searching a smooth response
surface for a maximum, it was searching a **narrow feasible sliver** near a
sharp detuning boundary. Two consequences:

- an unconstrained objective surface is actively misleading here — its maximum
  is in infeasible territory. Phase 7's feasibility probabilities and
  constrained-EI proxy exist because of this;
- Stage 5 must sample the detuning boundary densely enough to resolve it, not
  just refine around the point.

## 3. t0021 sits on the lower barrier bound — again

t0021 has `central_barrier_thickness_nm = 0.85`, exactly the v3 lower bound. The
same thing happened in v2 at its own bound of 0.5 nm. An optimizer pinned to a
bound is reporting that the bound binds, not that it found an interior maximum.

What is *better* than v2: 0.85 nm is 3 monolayers of AlGaAs (a = 0.565325 nm,
one ML along [001] = 0.2827 nm), so it is a growable layer, and at the 0.05 nm
mesh it spans **17 cells**. v2's 0.5 nm was 1.77 ML across 5 cells.

❌ **Rejected claim:** "0.85 nm is the optimal barrier." The supportable
statement is that the objective increases monotonically toward the bound over
the sampled region and the true optimum is at or below 0.85 nm — possibly below
the thickness at which an abrupt Al₀.₅₅ step is a meaningful model at all.

⚠️ Do **not** simply lower the bound in a v4. Below 3 ML the envelope-function
treatment is being applied to a layer comparable to the interdiffusion length
(0.3–1 nm), and the "barrier" is no longer a barrier in the continuum sense.

## 4. Grading remains unanswerable — and v3 made this *visible* rather than fixing it

The genuine graded population:

| Profile | Genuinely graded trials | Feasible |
|---|---:|---:|
| erf | 3 | 0 |
| sigmoid | 1 | 0 |
| cosine | 1 | 0 |
| linear | **0** | 0 |

Five genuine graded designs, **none feasible**, all failing on detuning.

❌ **Rejected claims**, all of which the counts invite:
- "grading hurts" — five designs, each varying asymmetry, barrier, width and
  profile simultaneously, cannot separate grading from the other three;
- any profile ranking — erf 3 / sigmoid 1 / cosine 1 is not a ranking, and
  **linear was never built at all** despite being proposed;
- "erf is favoured by the model" — erf appears 3 times in the genuine set and
  **6 of 7 refusals were erf proposals**. That is the model repeatedly asking
  for erf and being refused on geometry, which says something about where the
  model was searching, not about erf's physics.

The only supportable statement: **within the feasible region v3 explored, no
graded design satisfied the detuning constraint.** That is a statement about
the constraint and the sampled region, not about grading.

`accounting13.grading_population_counts` reports
`profile_ranking_supportable: false` and is what stops a report drawing the
ranking.

## 5. State tracking near strongest coupling

t0021's `state_tracking_confidence = 0.993439` is reassuring but is a
*self-consistency* measure: nearest-neighbour overlap assignment against an
already-completed neighbour. It does not establish that the physical state
ordering is correct.

⚠️ Three concerns, all sharper at 0.85 nm than they were at v2's 0.5 nm bound in
one respect and weaker in another:

1. the assignment depends on **BO evaluation order** — the reference chain is
   whatever completed nearest first. Two runs sampling the same designs in a
   different order can chain differently. Stage 5 §E addresses this with a fixed
   anchor;
2. a thin central barrier maximises tunnel coupling, so the lowest two electron
   states are most nearly degenerate — exactly where overlap assignment is least
   discriminating;
3. Demo 11's registry entry still records that its Eq. 2 state-window
   convergence **FAILED** and that an asymmetry optimum near s ≈ 0.42 was an
   anticrossing artifact of window truncation. t0021 is at s = 0.387565. That is
   inherited physics, not a Demo 13 bug, and it is not resolved.

## 6. Boundary probability does not belong in the surrogate

`maximum_boundary_probability` for t0021 is 3.4248 × 10⁻⁵ against a 10⁻³ bound —
a factor of 29 inside, and it is nearly constant across the campaign. Ax logs
`Outcome maximum_boundary_probability is constant, within tolerance` on every
fit and its Sobol indices come back NaN.

A modelled constraint that carries no information cannot help the acquisition
and risks the all-infeasible pathology documented in `AX_FEASIBILITY_ANALYSIS.md`.
**Recommendation:** move it to `outcome_modelling.never_model` in v4, keeping it
enforced outside Ax. Not changed here — that alters the modelled outcome set and
would make v3's checkpoint inconsistent with its own configuration.

The metric itself is correctly defined (largest per-state leakage into the 5 %
edge region) and is correctly distinguished from a total summed over states.

## 7. Units

The objective is a Demo 11 Eq. 2 **relative** susceptibility under
`metric.mode: relative`: a lineshape and a trend with no absolute scale.
`chi2_units` was **empty on all 16 v3 trials** — an unlabelled chi(2) column is
precisely the one that gets quoted as pm/V. Now defaulted to
`a.u. (relative |chi2|)`.

❌ 0.411027 is not "0.411 of anything". Ratios between v3 designs are ratios on
this relative scale, and v2's numbers are **not comparable** — different mesh,
different search space.

## 8. Realized grading is unverified

The bundle carried no alloy-composition output. Five trials are recorded as
genuinely graded with realized widths 0.86–1.70 nm, but **no profile has been
checked against its request**. Demo 12's requested-vs-realized validation is the
check that would do it, and it needs the raw output. Phase 10 provides the
commands.

⚠️ Until then, "t0019 realized a 0.86 nm erf grade" rests on the geometry
calculation, not on solver evidence.

## Required before any v3 design is called validated

1. mesh convergence on t0021 (0.025 / 0.05 / 0.10 nm) — **the gate**;
2. state-count convergence 4 → 6, given Demo 11's unresolved truncation;
3. domain-padding convergence;
4. order-independent state tracking with a fixed anchor;
5. dense sampling across the detuning boundary between t0021 (−13 nm) and
   t0022 (−16 nm);
6. alloy-profile verification for all five graded trials;
7. a balanced paired campaign before any grading claim.

**Signed: PASS WITH WARNINGS.**
