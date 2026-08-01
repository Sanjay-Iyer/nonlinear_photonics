# v3 final stale-code audit — Phase 3

Repository-wide search, repeated independently by Agent 2. Every hit was opened
and read; a token appearing is not the same as a defect.

## Findings acted on in this pass

| # | File | Location | Current meaning | Verdict | Correction | Protecting test |
|---|---|---|---|---|---|---|
| S1 | `demo_registry.yaml` | comment above demo 13's `status` | Described the **v2** campaign (16 trials, 8 feasible, best t0012) as if current, directly above the v3 status | **stale** | Rewritten for v3: 23 proposals / 7 refused / 16 completed / 3 feasible / best t0021, with v2 named as superseded | `test_registry_declares_demo13` |
| S2 | `tables13._project` | table projection | `chi2_units` was blank on **all 23 v3 rows**: the fix added last pass applies at *write* time, and every v3 record predates it | **stale** | `_COLUMN_FALLBACKS` supplies the unit at projection time; an existing value is never overwritten | `test_chi2_units_are_never_blank_even_on_historical_records` |
| S3 | `demo.yaml` `workflow.mode` | shipped as `closed_loop` | v3 is complete, so this does nothing *today* — but one `num_iterations` bump turns the same command into licensed solver spend | **unsafe default** | Shipped as `analyze_existing_results`, with the trap explained inline | `test_demo_yaml_points_at_the_current_experiment` |
| S4 | `demo.yaml` search space | `grading_fraction_spans_feasible_interval` was documented but **absent** from the YAML, relying on an implicit default | **stale doc** | Added explicitly with its meaning and schema consequence | `test_every_documented_parameter_exists_in_the_yaml` |
| S5 | `validation_study` | no output directory, so Stage 5 would write inside the protected experiment | **unsafe** | `output_state_dir` added; a configuration pointing Stage 5 at the experiment is rejected at startup | `test_stage5_pointed_at_the_experiment_is_rejected` |

## Every remaining hit, and why it is correct

| Token | Where it still appears | Verdict |
|---|---|---|
| `demo13_ax_experiment_v2` | `test_demo13_experiment_v3.py`, `test_demo13_reanalysis_and_grading.py`, `test_demo13_guides.py` | **valid** — tests that assert a v2 snapshot must *not* load, that a missing directory must not be invented, and that no guide names v2 |
| `search-space-2` | `test_demo13_experiment_v3.py`, `test_demo13_guides.py` | **valid** — asserts the schema version was bumped and that no guide names the old one |
| `t0012` | `demo_registry.yaml` `superseded` field; `test_demo13_guides.py` | **valid** — the registry explicitly labels it as the superseded v2 result; the test asserts no guide names it |
| `implemented_dry_run` | `registry.py` vocabulary; Demos 11 and 12's genuine status; `demo13._lifecycle` fallback | **valid** — the fallback is reached only when no licensed trial exists |
| `status: failed` | `sweeps.py` for genuinely failed cases; test fixtures | **valid** — v3's manifest no longer reports it |
| `parameter_grading_thickness_nm` in `plots13` | scatter/sampling plots | **valid** — this column is the **realized** width, correctly in nm |
| `pm/V` | guides, `report13`, `README` | **valid** — every occurrence is a denial; `test_guides_never_call_relative_chi2_pm_per_volt` enforces a denial within 120 characters of each one |
| `metric.calibration_target_pm_per_V: 2340.0` | `demo.yaml` | **valid but latent** — unused while `metric.mode: relative`; the pm/V axis label is gated on the mode |

## Duplicated implementations — checked specifically

Agent 2 searched for a second accounting or lifecycle implementation, the defect
class that produced last pass's regressions.

| Symbol | Status |
|---|---|
| `accounting13.campaign_accounting` | the single counter |
| `accounting13.rejection_category` | the single classifier |
| `accounting13.lifecycle_phrase` | the single wording |
| `axsearch13.budget_accounting` | **delegates** classification to `accounting13`; retained only for old field names |
| `demo13._lifecycle` | **delegates** to `accounting13.lifecycle_phrase` |

No independent second derivation remains.
`test_budget_accounting_agrees_with_the_authoritative_counts` fails if one
appears.

## Searches that came back clean

- bare `peak_chi2_abs` / `chi2_at_target_wavelength_abs` — zero
- `signed_detuning` in constraint construction — zero (`absolute_detuning_nm` is constrained)
- `bias_00000` in path building — zero (comments only, about the Windows path budget)
- old grading-thickness parameterization as an *Ax* parameter — zero
- rejected proposals in completed-trial plots — verified: `context.completed`
  excludes them, and `bo_proposed_vs_realized_grading` reports them as
  `not_realized`
- infeasible trials in feasible-only summaries — verified:
  `grading_population_counts` separates all / feasible / genuinely graded
- collapsed graded surrogate points as unique designs — fixed last pass;
  350 of 625 are withheld with a branch reason
- objective-only EI described as Ax's acquisition — the method string denies it
  explicitly and a constrained proxy sits beside it
- stale CSV links — derived from the figure filename, so they cannot drift

## Agent 2 verdict — Phase 3

**PASS.** The search was repeated independently. Five real items were found and
fixed; the remainder are tests asserting the absence of stale terms, or
historical references explicitly labelled as superseded. S2 and S3 are the ones
worth noting: S2 was a fix that looked complete last pass but did not reach the
historical records it was written for, and S3 was a configuration that was safe
only by accident.
