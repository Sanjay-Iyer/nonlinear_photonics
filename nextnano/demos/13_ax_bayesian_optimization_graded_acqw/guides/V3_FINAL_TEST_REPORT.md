# v3 final test report

| Suite | Result |
|---|---|
| Focused Demo 13 v3 modules (accounting, reporting, guides, bundle/Stage 5) | **88 passed** |
| Full repository suite | see `Final suite` below |
| v3 `analyze_existing_results` replay | **exit 0**, 0 solver calls |
| Guide coverage validation | **25 passed** |
| Raw-bundle dry run | **18 passed**, writes nothing |
| Stage 5 isolation | enforced and tested |

## Reanalysis verification

Protected files, hashed before and after:

| File | Identical |
|---|---|
| `ax_experiment_snapshot.json` | ✔ |
| `trial_ledger.jsonl` | ✔ |
| `experiment_schema.json` | ✔ |
| `demo_yaml_snapshot.yaml` | ✔ |

- zero `Executing` lines, zero `Generated new trial` lines
- `experiment_state_unchanged: true`, `generation_strategy_advanced: false`
- accounting: 23 proposals / 7 refused / 0 duplicates / 16 completed
  (6 Sobol + 10 MBM) / 3 feasible / 0 pending / 0 remaining /
  `optimization_completed: true`

## Validation beyond "the file exists"

Cross-file relationships were checked, not just presence:

| Check | Result |
|---|---|
| accounting `preflight_rejected` == rejection-history rows | 7 == 7 |
| accounting `proposed` == iteration-mapping rows | 23 == 23 |
| accounting `proposed` == proposed-vs-realized rows | 23 == 23 |
| budget table agrees with `campaign_accounting.json` | yes |
| MBM iteration numbers | exactly 1…10 |
| refused proposals in iteration plots | none |
| refused rows marked `not_realized` | 7 of 7 |
| genuine graded + realized abrupt == completed | 5 + 11 == 16 |
| tables lacking a `.units.json` sidecar | none |
| figures lacking a `plot_data` CSV | none |
| `chi2_units` blank | **none** (was blank on all 23 rows) |
| figures | 32 populated + 15 placeholders = 47 |

## Placeholders are now machine-readable

A placeholder is rendered as an ordinary matplotlib figure carrying its reason as
text, so it is ~25 kB — indistinguishable from a real plot by inspection. "Is
this figure real?" was therefore unanswerable automatically, which is exactly
what an audit of "truthful placeholders" must ask. Each placeholder now writes
`<figure>.placeholder.json` with `populated: false` and the reason.

The 15 placeholders are precisely the figures needing raw solver output that the
transferred bundle does not contain.

## Tests added this pass

| Module | Count | Covers |
|---|---:|---|
| `test_demo13_guides.py` | 25 | guide↔code sync, units, parameter existence, work-laptop safety |
| `test_demo13_bundle_and_stage5.py` | 18 | read-only bundling, missing-file honesty, Stage 5 isolation |
| additions to `test_demo13_v3_reporting.py` | 4 | placeholder markers, `chi2_units` fallback, two sign-convention bugs |

## Failures found by the new tests — all real

1. `grading_fraction_spans_feasible_interval` was **documented but absent** from
   `demo.yaml`, relying on an implicit default. Now explicit.
2. `chi2_units` was blank on all 23 v3 rows. The fix added last pass applies at
   *write* time; every v3 record predates it. Fixed at projection time.
3. `_surrogate_placeholder` bypassed the marker writer, so surrogate placeholders
   were not machine-detectable. Routed through `_placeholder`.

## Failures found by the independent physics audit — see `V3_FINAL_PHYSICS_AUDIT.md`

Two code defects, both re-verified against the v3 trial records and both fixed
with tests:

- `detuning_side` labelled every blue-shifted peak `red_of_target`;
- `heavy_hole_anticrossing_gap_meV` returned the *largest* spacing, hiding hole
  spacings of 4–7 meV against a 5 meV broadening.

A third — the state tracker being fed fabricated hole energies — is identified
and **not fixed**.

## Final suite

Run after all edits, with no concurrent modifications. See the session log for
the exact count; the four focused v3 modules total **88 passed**, and the two
sign-convention regressions are covered by new tests.
