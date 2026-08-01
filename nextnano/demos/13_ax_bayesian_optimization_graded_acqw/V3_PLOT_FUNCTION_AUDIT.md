# v3 plot-function audit

Agent 2 requirement: *inspect plot functions even when no stale string is
present.* A figure can be wrong without any searchable token being wrong, so
this audit reads what each function **plots**, not what it is named.

Method: for every figure, compare its guide entry, filename, CSV, units sidecar
and the columns the function actually reads.

---

## Findings

### F1 — Iteration plots read the wrong column (defect 3)

`plots13._series_plot(x_key="iteration")` reads the ledger's `iteration`, which
counts **proposal attempts** and reached 17 in a 10-iteration study. A figure
captioned "by BO iteration" therefore showed an x-axis running past its own
budget, with gaps where refusals fell.

**Fixed** by `bo_trial_iteration_mapping.csv` supplying `mbm_iteration_number`
1–10, and by refusals being excluded from iteration plots.

⚠️ **Residual:** the *caption* still has to match the column. Guides are
hand-written prose; only the CSV link is derived. Any figure whose caption says
"iteration" must be checked against its CSV's `mbm_iteration_number` column.

### F2 — Scatter plots read canonicalized parameters for refused proposals (defect 7)

`plots13._parameter_sampling` and `_scatter_coloured` read
`parameter_grading_thickness_nm` / `parameter_grading_profile`. For a refused
graded proposal those hold the **canonicalized** design — abrupt, 0 nm — so
seven graded proposals appeared as evaluated abrupt points, at the correct
asymmetry and barrier, indistinguishable from real abrupt evaluations. Nothing
in the figure was blank; it was simply describing designs that never existed.

**Fixed** by `bo_proposed_vs_realized_grading.csv`, which reports
`realized_interface_mode: not_realized` for refusals and never merges proposed
with realized into one column.

⚠️ **Residual:** `context.completed` already excludes rejected records, so the
*objective* scatter plots were never contaminated. The contamination was in
sampling/lifecycle plots that use all records. Any new plot iterating all
records must use the proposed-vs-realized table, not `parameter_*`.

### F3 — Surrogate surfaces plotted physically identical points (defect 8)

`_surface` plots every row whose x, y and z are finite. 350 of 625 asymmetry-slice
rows were graded coordinates realizing below 0.80 nm — all the *same* abrupt
structure, drawn as a smooth graded continuum, once per profile label.

This is the audit's clearest example of a figure that is wrong with no stale
string anywhere: correct function, correct keys, correct units, correct CSV
link, physically meaningless surface.

**Fixed** by `_branch_validity`, which withholds a point from the branch it
claims and records why.

### F4 — Acquisition surface implied Ax's acquisition (defect 9)

`bo_acquisition_function_asymmetry_vs_grading_thickness.png` plotted analytic
objective-only EI. On a campaign where 13 of 16 completed trials were
infeasible, its maximum sits in infeasible territory.

**Fixed** by adding feasibility probabilities and a constrained-EI proxy, and by
an `expected_improvement_method` string that denies the identification
explicitly.

⚠️ **Residual:** the *figure* still plots `expected_improvement` on its z-axis.
The constrained proxy is in the CSV. A reader looking only at the PNG still sees
the unconstrained surface — the honest labelling is one layer away.

### F5 — Profile distribution mixes populations (defect 10)

`bo_grading_profile_objective_distribution` groups completed trials by
`parameter_grading_profile` and boxplots the objective. Three problems, none of
them a stale string:

1. it mixes feasible and infeasible trials — on v3, **all five graded trials
   were infeasible**, so the graded boxes are objective values of designs that
   failed the constraints;
2. group sizes are 1–3 and are not drawn, so a box from one point looks like a
   distribution;
3. `abrupt` includes both genuinely abrupt designs and any collapsed proposal.

**Mitigated** by `grading_population_counts`, which reports per-profile counts
split by all/feasible/genuine and sets `profile_ranking_supportable: false`.

⚠️ **Residual (accepted):** the boxplot itself still draws boxes for n = 1. It
should print n per group or degrade to a strip plot below n = 3. Recorded as an
open item rather than changed, because it needs a plotting change this pass did
not otherwise require.

### F6 — Guide-to-CSV link (defect 13)

`report13.plots_guide` derives `plot_data/<stem>.csv` from the figure filename
and `plots13._write_csv` writes exactly that path, so links cannot drift by
construction. The v3 bundle's mismatch was in the hand-written prose of
`bo_grading_profile_effect`, which pointed a reader at the distribution CSV.
Both figures now derive their own CSV name.

### F7 — Placeholder honesty

`_surrogate_placeholder` carries the model's own reason, and
`PLACEHOLDER_REASON_NO_SURROGATE` never mentions licensed output. Verified in
the regenerated bundle: withheld surrogate rows carry a **branch** reason
naming the 0.80 nm minimum, never a solver excuse.

### F8 — Units sidecars

Every figure has `plot_data/<stem>.csv`; every table has `<name>.units.json`.
`tables13.unit_for` resolves the new columns:
`proposed_grading_fraction` → *fraction of the feasible maximum in [0,1]*,
`realized_grading_thickness_nm` → *nm*. `chi2_units` is no longer blank.

---

## Verified-correct (checked, unchanged)

| Function | Why it is right |
|---|---|
| `_surrogate` observed overlays | `_observed_grading_coordinate` returns the trial's value on the axis being drawn |
| `grading_axis` | fraction axis labelled as a fraction, thickness as nm |
| `_paper` y-label | pm/V gated on `metric.mode != relative`; unreachable here |
| `best_so_far_by_iteration` | invalid trials never improve the curve |
| `physics_curves` | deterministic `(objective, trial_index)` ordering, shared with the ranked table |

## Open items

1. Plot the constrained-EI proxy, not unconstrained EI, on the acquisition figure.
2. Print n per group on the profile boxplot; degrade to a strip plot below n = 3.
3. Add a caption-to-column check so "by BO iteration" prose cannot outlive its column.

**Verdict: PASS WITH WARNINGS.** Three residuals are documented above; none
produces a false statement in the regenerated bundle, but items 1 and 2 leave a
figure that is easier to over-read than its CSV.
