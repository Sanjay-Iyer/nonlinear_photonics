# v3 software audit

Reviewer: senior Python engineer. Scope: correctness and immutability of the
v3 reanalysis path.

**Verdict: PASS WITH WARNINGS.**

---

## 1. The central finding: two defects were regressions from the previous pass

`REJECT_SUBRESOLUTION` was added in the last hardening pass without teaching
`budget_accounting` about it, and `optimization_completed` was wired to a plan
key that never existed. Both shipped, both ran on a licensed campaign, and the
previous pass's own test suite passed throughout.

The failure was structural: **classification logic lived in three places** —
`budget_accounting` (substring match), `plan._consumes_budget` (different
substring match) and `_lifecycle` (a hard-coded sentence) — and adding a fourth
rejection kind only had to be forgotten in one of them.

`accounting13` is now the single classifier, and
`test_every_rejection_reason_constant_is_classified` iterates the reason
constants so a *newly added* reason fails the suite rather than silently
counting as nothing.

## 2. Immutability

**PASS.** Verified by hashing, not by inspection:

- all four protected files byte-identical before and after reanalysis;
- all 23 terminal ledger records hash-identical;
- `Experiment(read_only=True)` refuses checkpoint, generate, complete, fail and
  abandon; `Ledger(read_only=True)` refuses writes and creates no directory;
- the reconstruction loads a **separate** `Client` and never serializes.

## 3. Single source of truth

**PASS.** Console, `campaign_accounting.json`, `bo_budget_accounting.csv`,
`run_manifest.json` and the validation report are all projections of one
`campaign_accounting()` dict. `budget_table_row()` is a rename-and-select, not a
second derivation. The legacy `axsearch13.budget_accounting` now delegates its
classification rather than duplicating it.

`accounting_identity_holds` and `rejection_identity_holds` are computed and
emitted, so an inconsistent ledger is *reported* rather than silently producing
plausible-looking wrong totals.

## 4. Rejected proposals are not solver cases

**PASS.** They are excluded from `results` before `write_sweep_manifest`, which
is what fixed `status: failed`. They remain fully reported in
`bo_candidate_rejection_history`, `bo_trial_iteration_mapping`,
`bo_proposed_vs_realized_grading` and the candidate table, and their counts are
carried in the manifest's `extra`. Nothing is dropped, only reclassified.

## 5. Rehydration

**PASS WITH WARNINGS.** `analysis13.rehydrate_experiment_state` reconstructs
per-trial JSON from the JSONL (last write wins, matching live `Ledger`
behaviour), refuses to overwrite a non-empty directory, and reports
`ledger_lines_malformed` (0 for v3).

⚠️ It cannot reconstruct `runs/` — raw solver output is not in a bundle. Any
analysis needing raw output (alloy profiles, re-extraction) must run on the work
laptop or use the Phase 10 supplemental bundle.

⚠️ The local verification therefore ran against a *reconstruction*. The JSONL is
authoritative and lossless here, but the work-laptop original remains the
reference and the hash check should be repeated there.

## 6. Schema compatibility

**PASS.** The schema now carries range bounds, choice values, the resolvable
minimum, the mesh and the fraction mapping — not just parameter names, which
v2 and v3 share.

A real gap was found and closed during this pass: adding
`grading_fraction_spans_feasible_interval` to the schema made the **existing v3
snapshot unloadable**, because a key absent from the stored schema compared
unequal to the configured value. `SCHEMA_FIELD_DEFAULTS` now declares what a
field meant *before it existed*, so a new identity field can be introduced
without invalidating every checkpoint — while still rejecting any value other
than that default.

⚠️ Every future schema field must be added to `SCHEMA_FIELD_DEFAULTS` or it will
break existing snapshots. That is deliberate: a field with no meaningful
"before" default *should* break them.

## 7. The opt-in mapping does not rewrite history

**PASS.** `grading_fraction_spans_feasible_interval` defaults to `False`, and
`test_the_default_mapping_still_refuses_every_v3_refusal` replays all seven v3
refusals to prove the recorded campaign is not reinterpreted. The mapping is in
the schema, so a v3 snapshot cannot be loaded under it.

One behaviour did change for everyone: the collapse threshold moved from
`thickness <= minimum` to `thickness < minimum`. Necessary — the interval
mapping's lower endpoint *is* the minimum, so an inclusive test made it
unreachable. For v3 this changes nothing: every refused grade was strictly
below 0.80 nm and every accepted one strictly above.

## 8. Missing-key handling

**PASS.** `rejection_category` returns `unclassified_rejection` for an unknown
reason instead of folding it into a known bucket. `grading13.from_record` raises
rather than inventing a zero. Refused proposals report
`realized_interface_mode: not_realized`, not `abrupt`.

## 9. Test coverage

**PASS.** 40 new tests across two modules, pinned to the real v3 pattern.

| Defect | Test |
|---|---|
| status failed / optimization_completed false | `test_optimization_completed_is_read_from_the_accounting` |
| duplicate mislabel | `test_a_subresolution_rejection_is_not_described_as_a_duplicate` |
| empty rejection history | `test_rejection_history_is_rebuilt_from_the_ledger` |
| zero preflight-invalid | `test_v3_accounting_matches_the_confirmed_campaign` |
| a *future* unknown reason | `test_every_rejection_reason_constant_is_classified` |
| iteration numbering | `test_mbm_iterations_are_numbered_one_to_ten` |
| refused plotted as abrupt | `test_refused_proposals_are_not_realized_abrupt_designs` |
| collapsed surrogate points | `test_a_subresolution_grid_point_is_unavailable_for_the_graded_branch` |
| constraint direction | `test_feasibility_probability_uses_the_correct_threshold_direction` |
| binary flags in feasibility | `test_binary_qc_flags_never_enter_the_feasibility_product` |
| schema field addition | `test_a_snapshot_predating_a_schema_field_stays_loadable` |

## Open items

1. `maximum_boundary_probability` should leave the modelled constraint set in v4.
2. `metrics13.build_record` still leaks `PROVENANCE_FIELDS` into `parameter__*`
   (carried from v2; `grading13` reads both spellings).
3. `axsearch13.budget_accounting` is now a thin legacy wrapper; retire it once
   nothing consumes the old field names.
4. Rejected records do not store `realized_grading_before_collapse_nm`; it is
   recomputed from fraction × maximum. Newer runs should record it directly.

**Signed: PASS WITH WARNINGS.**

## 2026-08-02 targeted continuation

- `tracking13.load_trial_states` is the only authority for state-energy loading
  and refuses fabricated scientific fallbacks.
- `demo13.validation_anchor_tracking` makes the configured anchor reachable from
  the prepared Stage 5 production path and writes a separate anchor summary and
  table; it never writes into the optimization experiment.
- `derived13.corrected_records` is the single detached correction boundary for
  historical reports. It is idempotent and never mutates ledger records.
- `bo.target_wavelength_nm` is now the authoritative target resolved into both
  Demo 11 extraction and Demo 13 reporting. Checkpoint identity covers the
  audited physics/extraction settings while old v3 snapshots remain compatible
  only at their stored defaults.
- Independent narrow audit: **PASS**. Focused boundary: 67 tests passed; the
  immutable v3 ledger SHA256 was unchanged.

The older statement that `anchor_case` is read by no code is superseded by this
addendum. Stage 5 remains prepared and unauthorized.
