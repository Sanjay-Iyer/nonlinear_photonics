# v3 final plot and table function audit

**Verdict: PASS WITH WARNINGS.**

## Method

Every figure was compared against the CSV it is drawn from, and every table
against the ledger it projects. Figures were additionally checked for the one
property that cannot be inferred from the file itself: whether they are real
plots or placeholders.

## Findings

### PT1 — placeholders were indistinguishable from real figures — FIXED

A placeholder is a matplotlib figure carrying its reason as text, ~25 kB — the
same size as a populated plot. Any automated check for "truthful placeholders"
was therefore impossible, which is precisely the question this audit has to ask.
Each placeholder now writes `<figure>.placeholder.json`.

Result on the current bundle: **32 populated, 15 placeholders, 47 total.** The
15 are exactly the figures whose CSVs contain no finite data, and every one of
them needs raw solver output the transferred bundle does not contain.

### PT2 — `chi2_units` blank on every row — FIXED

`bo_trial_nonlinear_optical_outputs.csv` had an empty `chi2_units` on all 23
rows and its sidecar declared the column `unspecified`. An unlabelled chi(2)
column is the one that gets read as pm/V. Fixed at projection time, because the
ledger is immutable and every v3 record predates the field.

### PT3 — the profile boxplot still draws boxes for n = 1 — NOT FIXED

`bo_grading_profile_objective_distribution` groups completed trials by profile
and boxplots the objective. On v3 that is erf 3, sigmoid 1, cosine 1 — and
**every graded trial was infeasible**, so the graded boxes are objective values
of designs that failed the constraints. Group sizes are not drawn.

Mitigated in the guide, whose entry says explicitly that this cannot rank
profiles, and by `grading_population_counts`. But the figure is still easier to
over-read than its CSV.

### PT4 — the acquisition figure still plots unconstrained EI — NOT FIXED

The constrained proxy and per-constraint feasibility probabilities are in the
CSV; the PNG's z-axis is still `expected_improvement`. On a campaign where 13 of
16 completed trials were infeasible, the unconstrained maximum sits in
infeasible territory. The guide entry says so; the figure does not.

### PT5 — `bo_grading_profile_effect.csv` ships ranking material — NOT FIXED

It carries per-profile mean/best/worst with **no supportability flag in the file
itself**. A reader opening only that CSV sees a ranking. The flag lives in
`grading_population_counts`; it should be a column here too.

This matters more than it looks: an independent reviewer flagged that the
reports *claim* the pipeline "refuses to rank grading profiles", while this file
ships exactly the material for one.

### PT6 — verified correct, unchanged

| Function | Check |
|---|---|
| `_surrogate` overlays | observed points use the axis actually being drawn |
| `grading_axis` | a fraction is labelled a fraction; nm is labelled nm |
| `_branch_validity` | 350/625 sub-resolution graded points withheld with a reason |
| `best_so_far_by_iteration` | invalid trials never improve the curve |
| `top_ranked_valid_designs` | deterministic `(objective, trial_index)` ordering |
| `physics_curves` | same ordering as the ranked table |
| `_paper` y-label | pm/V gated on `metric.mode != relative` |
| guide→CSV links | derived from the figure filename; cannot drift |

## Table audit

All 28 catalogued tables have a `.units.json` sidecar. Row populations,
cross-file identities and iteration semantics were verified — see
`V3_FINAL_TEST_REPORT.md` for the checked relationships.

## Physics-driven caveat on two figures

The independent physics audit found that `detuning_side` was inverted on every
trial (every blue-shifted peak labelled `red_of_target`). Any figure or table
column derived from that label was wrong until this pass. The underlying
`signed_detuning_nm` values were always correct; only the categorical label was
inverted.
