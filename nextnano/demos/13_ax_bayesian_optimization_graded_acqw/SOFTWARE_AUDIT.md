# Software audit — Demo 13 hardening pass, 2026-08-01

Reviewer role: senior Python engineer. Scope: correctness, safety and
reproducibility of the reanalysis path, not the physics.

**Verdict: PASS WITH WARNINGS.**

---

## 1. Path handling

**PASS.** No new path construction was introduced. `run_subdirectory(run_dir,
key)` resolves layout directories through a keyed map; nothing concatenates a
fixed `case` or `bias_00000` component (verified by search — the only
`bias_00000` occurrences in the tree are comments about the Windows 260-character
path budget). `analysis13` uses `Path` throughout and `rglob` for tree hashing,
so it is case- and separator-agnostic.

⚠️ **Warning:** `_tree_manifest` hashes *relative path + size*, not content. It
detects added, removed, renamed and truncated files, which is the failure mode
that matters (a reporting run damaging trial output). It would not detect an
in-place edit that preserves length. Content-hashing 16 trials of raw solver
output was judged too expensive for something that runs on every reanalysis;
the five critical *files* are fully content-hashed.

## 2. Immutable ledger protection

**PASS — and a real hole was closed.**

`Ledger.write` had its terminal-record check nested inside `if not
allow_update`, so `allow_update=True` could overwrite a completed licensed
trial. The class docstring already promised the opposite. The check now sits
outside the branch; `allow_update` retains only its legitimate use, finishing a
`pending_no_solver` record.

The pre-existing test `test_ledger_records_are_immutable_once_terminal`
**asserted the hole** (`ledger.write({...}, allow_update=True)` then
`assert status == "failed"`). It has been rewritten to assert the guarantee, and
`test_pending_ledger_records_may_still_be_finished` covers the legitimate path
that test used to cover by accident.

`Ledger(read_only=True)` additionally creates no directory and refuses all
writes.

## 3. Checkpoint safety

**PASS.** `save_client`'s existing unique-temp-plus-retry-rename logic is
untouched and remains appropriate for Windows AV interference. What changed is
that reanalysis never calls it: `Experiment.checkpoint()` raises under
`read_only`. Reconstruction loads its **own** `Client` from the snapshot file
and never serializes, so the file is provably untouched — asserted by comparing
its SHA-256 before and after, recorded in `analysis_model_reconstruction.json`
as `original_experiment_state_modified`.

## 4. Schema compatibility

**PASS.** `_check_schema_compatible` is unchanged and still refuses to resume a
snapshot whose recorded search-space schema differs from the configuration —
which is what prevents a v2 checkpoint being loaded under a v3 search space.

⚠️ **Warning:** in `read_only` mode the schema check still runs *before* the
read-only branch would matter, and `experiment_schema.json` is no longer
rewritten. That is correct, but it means a v2 directory lacking
`experiment_schema.json` (written before schema stamping existed) raises rather
than being silently upgraded. That is the intended behaviour, and the error
message says what to do.

## 5. Field naming

**PASS WITH WARNINGS.** `grading13` is now the single authority and accepts all
four historical spellings of the feasible maximum and all four of the proposed
fraction, including the `parameter__`-prefixed forms produced by
`metrics13.build_record`'s failure to strip `design13.PROVENANCE_FIELDS`.

⚠️ **Warning (deliberate non-fix):** that leak is left in place. Fixing it now
would make new records inconsistent with the v2 ledger they must be compared
against, and the leaked fields are the only record a completed v2 trial has of
its proposed fraction. Flagged for v3 in `OLD_CODE_AUDIT.md` §C2.

## 6. Missing-key handling

**PASS.** `grading13.from_record` raises `GradingError` rather than defaulting to
0.0 when no realized thickness is present under any known name — inventing an
abrupt structure would be worse than failing. `try_from_record` is the
non-raising variant used on table and plot paths so one bad row cannot kill a
reporting run, and `demo13._grading_columns` emits an explicit
`grading_unavailable_reason` instead of a silent `None`.

## 7. Typed exceptions

**PASS.** New failures raise `DemoError` (read-only violations, missing
experiment, stale slice axis) or `GradingError`/`ReconstructionError`. No bare
`Exception` raises were added. Broad `except Exception` remains only where it
was already the deliberate policy — reconstruction fallback, sensitivity
computation, per-point prediction — and in every case the exception text is
captured into the output record rather than swallowed.

## 8. Unit sidecars

**PASS.** `grading13.UNITS` declares a unit for every field
`GradingView.as_record()` emits, and `tables13.COLUMN_UNITS` — the map the CSV
sidecars are actually written from — now covers every one of those columns plus
the two new Stage 5 robustness columns. `proposed_grading_fraction` is
`fraction of the feasible maximum in [0,1]`;
`realized_grading_thickness_nm` is `nm`.

`test_every_emitted_grading_column_declares_a_unit` fails if a future column is
emitted without a declared unit, which is the mechanism by which a fraction
would get read as a length.

## 9. Reproducibility

**PASS.** Reanalysis is a pure function of the snapshot, the ledger and the
configuration. The reconstruction refits from the same observations with the
same generator spec, so repeated runs produce the same surrogate up to BoTorch's
own optimizer tolerance. `random_seed: 17` is unchanged.

⚠️ **Warning:** GP hyperparameter fitting is not bitwise deterministic across
BoTorch/torch versions. Surrogate *figures* may differ slightly between machines
even from identical data. The reconstruction record pins `ax_version` and
`botorch_version` so a discrepancy is diagnosable.

## 10. Deterministic top-N selection

**PASS.** `top_ranked_valid_designs` and `physics_curves` now share an explicit
`(objective, trial_index)` sort key, so tables and figures cannot disagree about
rank 1. Non-finite objectives are filtered before sorting. Verified by
`test_top_n_is_deterministic_on_ties` (same result from reversed input) and
`test_non_finite_objectives_never_win_the_ranking`.

## 11. Test coverage

**PASS.** 45 new tests in `test_demo13_reanalysis_and_grading.py`, plus one
added and two corrected in the existing suite. Full suite: **579 passed, 0
failed** (533 collected before this pass: 530 passed, 3 failed) (see `HOME_LAPTOP_VERIFICATION.md` for the exact command and output).
Coverage of the specific defects:

| Defect | Test |
|---|---|
| Adapter not predictive after load | `test_predictive_adapter_is_reconstructed_without_advancing_the_strategy` |
| Strategy advanced by fitting | same, asserts `generation_node_before == after` |
| New trial generated | same, asserts `new_trials_generated is False` |
| Checkpoint modified | `test_reconstruction_never_modifies_terminal_ledger_records` |
| Terminal record modified | same, at per-record hash granularity |
| Failed/non-finite observations fitted | `test_reconstruction_fits_only_completed_finite_observations` |
| Abrupt point with inactive children | `test_hierarchical_branches_predict_and_invalid_ones_say_why` |
| Graded point missing children | same |
| Fraction mislabelled as nm | `test_grading_axis_label_never_calls_a_fraction_nanometres` |
| Realized vs unsnapped confusion | `test_unsnapped_and_realized_thickness_are_distinguished` |
| Zero-grade counted as profile evidence | `test_graded_proposal_that_snaps_to_zero_is_physically_abrupt` |
| Stale thickness bounds | `test_slice_points_reject_a_stale_thickness_axis` |
| Trial 12 omitted from top-N | `test_best_trial_is_included_and_ranked_first` |
| Baseline missing | `test_physics_curves_include_the_supplied_baseline` |
| Placeholder falsely blames solver | `test_surrogate_placeholder_never_blames_a_missing_solver` |
| Registry says dry run | `test_registry_status_reflects_licensed_completion_but_not_validation` |

## 12. Zero solver calls in analysis mode

**PASS, structurally rather than by inspection.** In
`analyze_existing_results`, `loop_result` is set without calling `closed_loop`,
so `run_trial` — the only caller of `sweeps.execute_case` — is unreachable.
Independently, `Experiment(read_only=True).generate()` raises, so even a future
code path that tried to propose would fail loudly rather than spend licensed
solver time.

Confirmed end-to-end as well: a full `analyze_existing_results` run against a
16-trial experiment produced zero `Executing` and zero `Generated new trial`
lines, exit 0, and `experiment_state_unchanged: true`
(`HOME_LAPTOP_VERIFICATION.md` command 5).

⚠️ **Warning:** that run used the *synthetic* 16-trial experiment, because v2
does not exist on this machine. The code path is identical — same mode, same
read-only `Experiment`, same reconstruction — but the assertion has not been
made against v2 itself. Repeat the `Executing`-line check on the work laptop.

---

## Open items (non-blocking)

1. Consolidate `axsearch13.surrogate_predictions` / `parameter_importance`,
   now unused on the reporting path, once v3 lands.
2. `metrics13.build_record` provenance leak — fix in v3 only.
3. `_tree_manifest` uses path+size, not content hashes, for trial trees.

**Signed: PASS WITH WARNINGS.**
