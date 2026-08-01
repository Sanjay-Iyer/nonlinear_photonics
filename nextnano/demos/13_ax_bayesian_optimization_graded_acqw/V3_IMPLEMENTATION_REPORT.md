# v3 implementation report — Agent 1

Subject: experiment v3 (`demo13-search-space-3`, 0.05 nm mesh, 0.85–2.5 nm
barrier), 16 completed licensed trials, best feasible t0021.

All work was done on the home laptop against the transferred v3 bundle. **No
nextnano executable exists here and none was invoked.** The Downloads bundle is
the evidence of record and was never written to.

---

## What was wrong, in one paragraph

The v3 campaign ran correctly — 16 completed trials, zero solver failures, seven
unbuildable proposals correctly refused before any deck was rendered. What
failed was *describing* it. The campaign reported itself as `status: failed`
with `optimization_completed: false`; its seven refusals were counted as zero
preflight-invalid proposals, described as "canonical duplicates", plotted as
evaluated abrupt designs, and their history table was empty; BO iterations were
numbered by proposal attempt and ran to 17 in a 10-iteration study; and 350 of
625 surrogate grid points were plotted as independent graded predictions when
their physical structure was the same abrupt design.

Two of those were regressions introduced by the previous hardening pass, which
added a new rejection reason without teaching three separate copies of the
classification logic about it.

## Files changed

| File | Change |
|---|---|
| `accounting13.py` | **new** — the single authoritative classifier and counter: `campaign_accounting`, `rejection_category`, `is_duplicate`, `lifecycle_phrase`, `rejection_history`, `trial_iteration_mapping`, `proposed_versus_realized_grading`, `grading_population_counts` |
| `demo13.py` | accounting wired into console/manifests/lifecycle; `_lifecycle` delegates; refused proposals excluded from `results`; `_branch_validity`; `_feasibility_probabilities`; schema carries bounds/mesh/mapping; `SCHEMA_FIELD_DEFAULTS` |
| `axsearch13.py` | `budget_accounting` delegates classification instead of substring-matching |
| `design13.py` | `fraction_spans_feasible_interval`; collapse threshold `<=` → `<` |
| `geometry13.py` | `realize_from_fraction` gains the optional `[minimum, maximum]` interval mapping |
| `metrics13.py` | `DEFAULT_RELATIVE_CHI2_UNITS`; `chi2_units` never blank |
| `analysis13.py` | `rehydrate_experiment_state` — rebuild a runnable experiment from a bundle |
| `tables13.py` | three new tables wired through |
| `demo_registry.yaml` | v3 evidence replaces v2's; stale "0.5 nm winner" text removed |
| tests | `test_demo13_v3_accounting.py` (15), `test_demo13_v3_reporting.py` (25) |
| reports | `V3_EVIDENCE_MANIFEST`, `V3_STALE_CODE_AND_REPORT_AUDIT`, `V3_REANALYSIS_VERIFICATION`, `V3_PHYSICS_AUDIT`, `V3_SOFTWARE_AUDIT`, `V3_AX_BO_AUDIT`, `V3_PLOT_FUNCTION_AUDIT`, `V3_CROSS_AUDIT_SUMMARY`, `V3_STAGE5_EXECUTION_PLAN` |

## Confirmed v3 accounting

Every consumer projects one dict. Verified in the regenerated bundle:

| Quantity | Value |
|---|---:|
| proposed candidates | 23 |
| preflight rejected | 7 (all `subresolution_grade`) |
| canonical duplicates | 0 |
| solver completed | 16 |
| Sobol completed | 6 (of 7 proposed) |
| model-based completed | 10 (of 16 proposed) |
| feasible completed | 3 — t0005, t0017, t0021 |
| pending | 0 |
| remaining evaluations | 0 |
| optimization completed | **True** |

`23 = 7 + 16`, asserted at runtime as `accounting_identity_holds`.

## Grading populations

| | |
|---|---:|
| proposed graded | 12 |
| refused graded | 7 |
| evaluated genuine graded | 5 |
| **feasible genuine graded** | **0** |
| evaluated abrupt | 11 |
| genuine per profile | erf 3, sigmoid 1, cosine 1, **linear 0** |

5 + 11 = 16. `profile_ranking_supportable: false`.

## Iteration mapping

MBM 1–10 over `t0007 t0008 t0009 t0011 t0017 t0018 t0019 t0020 t0021 t0022`.
The ledger's `iteration` field reached **17** for t0022 — that column counts
proposal attempts and must never be used for a "by BO iteration" axis.

## Reanalysis

Exit 0, zero `Executing` lines, zero `Generated new trial` lines. All four
protected files byte-identical before and after; all 23 terminal ledger records
unchanged; `generation_strategy_advanced: False`.

## Remaining risk

1. **No alloy profile has ever been verified.** Five trials are recorded as
   genuinely graded on the strength of geometry arithmetic alone.
2. **t0021 sits on the barrier lower bound**, exactly as v2's winner did.
3. **Grading is unanswerable** from 5 graded designs, none feasible.
4. **State tracking may depend on evaluation order** — unresolved.
5. **v3 ran from a dirty work-laptop tree**; the recorded commit does not fully
   describe the code that produced it.
6. Stage 5 currently shares the v3 experiment directory.

**Agent 1 verdict: PASS WITH WARNINGS.** The reporting path is correct and
tested. The scientific limits are unchanged by any of it and are recorded in
`V3_PHYSICS_AUDIT.md`.
