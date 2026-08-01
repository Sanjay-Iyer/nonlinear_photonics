# Physics and materials audit — Demo 13 hardening pass, 2026-08-01

Reviewer role: semiconductor quantum-well physicist and materials chemist.
Scope: whether the repaired outputs represent the structures that were actually
simulated, and whether any claim in the reports exceeds what the model supports.

**Verdict: PASS WITH WARNINGS.**

The code changes are physically sound and remove three ways the reports could
have misdescribed the simulated structures. The warnings are all about claims
that must not be made from the v2 data — none of them is now made by the code,
but several are one careless sentence away.

---

## 1. Do plotted and ranked parameters represent the realized structure?

**Now yes; before, partly no.**

`design13.canonicalize` has always written the *realized* width into
`grading_thickness_nm`, so ledger columns and physical scatter plots were
correct. The failure was on the surrogate side: slice points carried a fraction,
were encoded as abrupt (audit A1), and were then drawn on an axis labelled
"Grading thickness (nm)" (A3). A reader would have concluded that the surrogate
saw no dependence on grading — over a grid where grading never varied.

`grading13.GradingView` now separates the four quantities that were being
conflated, and I consider the distinction physically necessary, not
bookkeeping:

- `proposed_grading_fraction` — an optimizer coordinate. No physical meaning.
- `maximum_feasible_grading_nm` — set by the well and barrier widths of *that*
  candidate. It is a geometry constraint, and it changes from trial to trial.
- `proposed_grading_thickness_nm_unsnapped` — the width requested.
- `realized_grading_thickness_nm` — the width built, after `mesh_snap_nm: 0.01`.

Trial 12 of the local synthetic study makes the point: fraction 0.9343 of a
1.1839 nm maximum is 1.1062 nm requested, 1.1 nm built. A 6 pm discrepancy is
negligible physically, but the *machinery* that produces it is the same
machinery that turns a small fraction at a thin barrier into exactly zero.

## 2. Are grading conclusions supported by the number of genuine graded trials?

**This is the most important warning.**

`grading13.evidence_counts` now reports, per profile, how many trials **built** a
non-zero grade, and sets `profile_ranking_supportable: false` unless at least
two profiles have ≥ 3 genuine trials each.

For the licensed v2 study as described (three isolated graded trials, the winner
abrupt with realized grading 0 nm), the following claims are **rejected**:

- ❌ *"Grading is worse than an abrupt interface."* Three graded trials, scattered
  over asymmetry, barrier thickness, profile shape and grade width
  simultaneously, cannot separate the effect of grading from the effect of the
  other three coordinates. The correct statement is that **the search did not
  find a graded design that beat the best abrupt one**, which is a statement
  about the search, not about grading.
- ❌ *"The linear profile outperforms sigmoid/erf/cosine"* (or any ordering) from
  one observation per profile. That is a single sample per category.
- ❌ Any claim about grading drawn from a trial whose realized width is 0 nm.
  Such a trial is an abrupt structure that happens to carry a profile label.
  `profile_evidence` returns `None` for it, and that is now enforced in code.

The one claim the data does support: **the optimizer preferred abrupt designs**,
and the best design it found realizes zero grading.

## 3. Is the arbitrary-unit χ⁽²⁾ described correctly?

**Yes, and it is now defended in three places.**

The objective is Demo 11's Eq. 2 *relative* interband susceptibility with
`metric.mode: relative`. It is a lineshape and a trend with no absolute scale.

- `report13.verdict` now states the improvement ratio is "on the relative
  arbitrary-unit scale" and adds an explicit sentence that it is neither a pm/V
  ratio nor a measured enhancement (A19).
- `plots13._paper` can no longer label an axis pm/V while `metric.mode` is
  `relative` (A18).
- Ranked table rows carry `objective_scale_note`.

❌ **Rejected claim:** *"1.8× larger absolute χ⁽²⁾."* A ratio of two relative
merits is dimensionless and says nothing about absolute magnitude. The stated
best value of ≈ 0.994 relative units at 1550 nm is a position on an arbitrary
scale, not 0.994 of anything physical.

⚠️ **Warning:** `metric.calibration_target_pm_per_V: 2340.0` exists in
`demo.yaml`. It is not used by the relative mode, but it is one configuration
change away from producing numbers that *look* absolute. Demo 13 should never
run calibrated; if it ever does, every "relative" caveat in the guides becomes
wrong simultaneously.

## 4. Is state tracking reliable near avoided crossings?

**Not established, and the winner sits exactly where it matters.**

`state_tracking_confidence ≈ 0.9999` for trial 12 is reassuring but is a
*self-consistency* measure: nearest-neighbour overlap assignment against an
already-completed neighbour in normalized parameter space. It says the
assignment was unambiguous given the reference it chose. It does not say the
physical state ordering is stable.

Three specific concerns for Stage 5:

1. The assignment is made against the **nearest already-completed trial**, so it
   depends on BO evaluation order. Two runs that sample the same designs in a
   different order can produce different reference chains. This must be checked
   by re-tracking with a fixed anchor (`anchor_case: reference_abrupt`).
2. Demo 11's registry entry already records that the s ≈ 0.42 asymmetry optimum
   was an **anticrossing artifact of state-window truncation**. The Demo 13
   winner at s ≈ 0.4603 is not far from that region.
3. A 0.5 nm central barrier strengthens tunnel coupling and pushes the coupled
   doublet toward the strong-coupling limit, where the two lowest electron
   states are most nearly degenerate — precisely where an overlap-based
   assignment is least discriminating.

## 5. Is the boundary metric interpreted correctly?

**Yes as implemented, with a modelling caveat.**

`maximum_boundary_probability` is the largest per-state leakage into the
`boundary_edge_fraction: 0.05` edge region, bounded at 1e-3. That is the right
quantity for "is any state quasi-bound", and it is distinct from a *total*
boundary probability summed over states. No confusion between the two was found
in the code.

⚠️ **Warning:** in the observations it is **constant**, which is why Ax logs
`Outcome maximum_boundary_probability is constant, within tolerance` and why its
Sobol indices come back NaN. A constant modelled constraint contributes nothing
to the surrogate and risks the all-infeasible pathology already documented in
`AX_FEASIBILITY_ANALYSIS.md`. It is correctly reported as undefined rather than
zero (A16), but for v3 it should follow `orthonormality_error` into
`never_model`.

## 6. Is the lower barrier physically meaningful?

**This is the second major warning: 0.5 nm is a bound, not an optimum.**

The winner sits exactly on `central_barrier_thickness_nm.lower: 0.5`. An
optimizer that pushes a parameter to its bound is telling you the bound is
binding, not that it found an interior maximum.

Physically, 0.5 nm of Al₀.₅₅Ga₀.₄₅As is **less than two monolayers** (GaAs
a = 0.565 nm, so a monolayer along [001] is ≈ 0.283 nm). At that thickness:

- the "barrier" is not a barrier in the continuum sense — the envelope-function
  approximation with an abrupt 0.55 Al step is being applied to a layer thinner
  than the scale over which the alloy potential is even defined;
- real interdiffusion during growth (typically 0.3–1 nm) would wash it out
  entirely, so the structure is arguably not growable as specified;
- `active_region_grid_spacing_nm: 0.10` gives **5 mesh cells** across it. That
  is not obviously too few, but it has not been demonstrated to be enough, and
  it is the first thing Stage 5 must settle.

❌ **Rejected claim:** *"0.5 nm is the optimum central barrier thickness."* The
supportable statement is that the objective increases monotonically toward the
lower bound over the sampled region, and that the true optimum is at or below
0.5 nm — possibly outside the physically meaningful range of the model.

## 7. Does any claim exceed the model?

Checked and currently clean, given the fixes:

| Claim | Status |
|---|---|
| "16 licensed trials completed, zero solver failures" | ✅ Supported — plumbing, not physics. |
| "t0012 is the best trial found" | ✅ Supported, with deterministic ranking (A13). |
| "t0012 is the optimum" | ❌ Not supported. Bound-limited; Stage 5 pending. |
| "grading does not help" | ❌ Not supported. See §2. |
| "relative χ² ≈ 0.994 at 1550 nm" | ✅ Supported as a relative number. |
| "peak at ≈ 1537 nm, |detuning| ≈ 13 nm" | ✅ Supported; within the 15 nm constraint but not comfortably. |
| "state tracking confidence 0.9999 means the state identity is right" | ⚠️ Overreach. See §4. |

## Required before this becomes a physics result

1. Mesh convergence at 0.05 nm across the 0.5 nm barrier.
2. State-count convergence (4 → 6 states) — Demo 11's window truncation failure
   is inherited physics, not a Demo 13 bug.
3. Outer-domain padding sensitivity.
4. Bidirectional state tracking with a fixed anchor, order-independent.
5. Fabrication perturbations of ±0.2 nm, which at a 0.5 nm barrier is a **40 %**
   change — the robustness question is unusually sharp here.
6. A v3 campaign that samples enough genuinely graded designs to answer the
   grading question at all.

**Signed: PASS WITH WARNINGS.** No physically wrong statement is produced by the
code as it now stands. Every warning above concerns a claim that the data cannot
support and that the reports must continue to refuse to make.
