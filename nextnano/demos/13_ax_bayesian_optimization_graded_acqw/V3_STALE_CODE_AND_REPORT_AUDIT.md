# v3 stale-code and report audit — Phase 9

Repository-wide sweep, repeated independently by Agent 2. Every row was checked
against the received v3 bundle, not inferred from the source.

## Findings acted on

| # | File / symbol | Valid or stale | Action | Protecting test |
|---|---|---|---|---|
| P1 | `axsearch13.budget_accounting` — rejection classification by substring | **stale**: matched only `geometry_preflight` / `canonical_duplicate`, so all 7 v3 `subresolution_grade` refusals counted as neither | delegated to `accounting13.rejection_category` | `test_budget_accounting_agrees_with_the_authoritative_counts` |
| P2 | `demo13.validation_lifecycle` — `plan_record.get("remaining_new_solver_runs", 1)` | **stale**: `plan()` returns no such key, so the `.get` default made `optimization_completed` permanently False | reads `accounting["optimization_completed"]` | `test_optimization_completed_is_read_from_the_accounting` |
| P3 | `demo13._lifecycle` — "rejected as a canonical duplicate" | **stale**: applied to every rejected record; wrong 7/7 on v3 | delegates to `accounting13.lifecycle_phrase`, which branches on the actual category | `test_a_subresolution_rejection_is_not_described_as_a_duplicate` |
| P4 | `demo13.main` — `results` built from all 23 records | **stale**: refused proposals became `skipped_no_solver` "cases", so `completed(16) != len(results)(23)` stamped `status: failed` | refused proposals excluded from `results`; counts carried in `extra` | verified end-to-end (`status` no longer `failed`) |
| P5 | `demo13.main` — `rejection_rows=loop_result.get("rejections")` | **stale**: in-memory loop state, absent on any reanalysis → empty table | rebuilt from the ledger by `accounting13.rejection_history` | `test_rejection_history_is_rebuilt_from_the_ledger` |
| P6 | ledger `iteration` field used as "BO iteration" | **stale**: counts proposal attempts, reached **17** in a 10-iteration study | `accounting13.trial_iteration_mapping` supplies MBM 1–10 | `test_mbm_iterations_are_numbered_one_to_ten`, `test_the_recorded_iteration_field_is_not_the_bo_iteration` |
| P7 | plots reading `parameter_grading_*` for refused proposals | **stale**: those columns hold the *canonicalized* design, so 7 graded proposals read as evaluated abrupt 0 nm trials | `bo_proposed_vs_realized_grading` reports `realized_interface_mode: not_realized` | `test_refused_proposals_are_not_realized_abrupt_designs` |
| P8 | surrogate slice points marked `prediction_available` | **stale**: 350 of 625 collapsed to abrupt yet carried a graded coordinate | `demo13._branch_validity` marks them unavailable **for the branch they claim**, with the reason | `test_a_subresolution_grid_point_is_unavailable_for_the_graded_branch` |
| P9 | `expected_improvement_method` string | **understated**: said "not a replay of Ax's Monte-Carlo acquisition" but the figure could still read as the real thing | explicit "NOT the original constrained Ax acquisition", plus feasibility probabilities and a constrained-EI proxy | `test_feasibility_probability_uses_the_correct_threshold_direction` |
| P12 | `metrics13.build_record` — `chi2_units` | **stale**: empty for all 16 v3 trials, leaving a chi(2) column with no stated scale | `DEFAULT_RELATIVE_CHI2_UNITS = "a.u. (relative \|chi2\|)"` | covered by `COLUMN_UNITS` tests; value asserted below |
| P2b | `demo_registry.yaml` `pending_licensed_checks` | **stale**: "the winner sits at a 0.5 nm barrier", "the 0.5 nm central barrier" — the **v2** winner | rewritten for v3: t0021, 0.85 nm, five graded trials none feasible, no alloy profiles transferred | `test_registry_status_reflects_licensed_completion_but_not_validation` |
| P2c | `demo_registry.yaml` `licensed_validation` | **stale**: described v2 (16 trials, 8 feasible, t0012) | replaced with the v3 campaign, plus an explicit `superseded` note that v2's numbers are not comparable | as above |

## Findings deliberately NOT changed

| Item | Why it is correct |
|---|---|
| `demo13.py:107` "a 0.5 nm barrier and a 0.10 nm mesh" | A comment **explaining why the schema must reject v2 snapshots**. Naming v2's parameters is the point. |
| `demo13.py:1927` "40 % of a 0.5 nm barrier" | Docstring of `perturbation_fraction`, illustrating why perturbations must be scaled. Still a valid illustration; the v3 figure would be 24 % at 0.85 nm. |
| `demo.yaml:57` `experiment_state_dir: demo13_ax_experiment_v2` | Inside a comment showing how to switch **back** to reanalysing v2. Live setting is v3. |
| `WORK_LAPTOP_RUN_GUIDE.md` naming v2 | Generated file, regenerated from the live config below. |
| `PHYSICS_AUDIT.md`, `CROSS_AUDIT_SUMMARY.md`, `STAGE5_VALIDATION_PLAN.md` naming t0012 | **v2 documents.** They describe the v2 campaign and are historically correct. v3 has its own set (`V3_*`). Superseding notes added rather than rewriting history. |
| `parameter_grading_thickness_nm` in output tables | The **realized** width, correctly in nm. |
| `pm/V` occurrences | Every one is a denial ("never pm/V"). |

## Verified-clean searches

| Search | Result |
|---|---|
| `implemented_dry_run` in Demo 13 | only the lifecycle fallback for a campaign with no licensed trial, and Demos 11/12's own genuine status |
| `optimization_completed=false` | now True for v3; regression-tested |
| `status=failed` | now `dry_run_complete` on a no-solver machine and `completed` on the work laptop |
| blank `chi2_units` | fixed at source with a non-empty default |
| bare `peak_chi2_abs` / `chi2_at_target_wavelength_abs` | zero occurrences |
| `signed_detuning` in constraint code | zero occurrences; `absolute_detuning_nm <= 15` is the constraint |
| `bias_00000` in path construction | zero; comments only |

## Guide-to-CSV link audit (defect 13)

`report13.plots_guide` emits `plot_data/<figure stem>.csv` for every entry, and
`plots13._write_csv` writes to exactly that path, so links cannot drift by
construction. The v3 bundle's mismatch was `bo_grading_profile_effect.png`,
whose guide entry pointed at the *distribution* CSV. Both figures now derive
their CSV name from their own filename.

⚠️ **Residual (not fixed):** the guide's per-figure *prose* is hand-written and
can still describe a figure inaccurately without any string being detectably
stale. `V3_PLOT_FUNCTION_AUDIT.md` covers that by inspecting the plot functions
themselves rather than searching for strings.

## Provenance (defect 16)

`run_manifest.json → git_dirty: true` for the v3 campaign, at commit `587612a`.
**Reported honestly, not corrected**: the recorded commit does not fully
describe the code that produced v3's results. This is now stated in
`V3_EVIDENCE_MANIFEST.md`, in the registry's `licensed_validation`, and in
`V3_REANALYSIS_VERIFICATION.md`. Any future licensed run must start from a
clean tree; that check is step 1 of both work-laptop command blocks.
