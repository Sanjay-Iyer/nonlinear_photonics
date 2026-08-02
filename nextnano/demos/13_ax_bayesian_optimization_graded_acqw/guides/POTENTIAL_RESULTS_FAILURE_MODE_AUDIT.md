# Failure-mode coverage audit

Every scenario below maps to at least one **named, executing** test. Where a
scenario already had coverage, the existing test is cited rather than a new one
written; where it had none, the new test is marked **NEW**.

Run the whole set with:

```bash
python -m pytest nextnano/tests/test_demo13_state_energies_and_anchor.py nextnano/tests/test_demo13_failure_modes_and_gate.py -q
```

## Coverage matrix

| # | Scenario | Test | File | Status |
|---|----------|------|------|--------|
| 1 | Missing real energies | `test_missing_hole_energies_raise_instead_of_being_invented`, `test_missing_electron_energies_also_raise`, `test_missing_energy_failure_is_persistent_and_scoped_to_one_trial` | `test_demo13_state_energies_and_anchor.py` | existing |
| 2 | Malformed energies | `test_malformed_energy_data_is_rejected_not_coerced`, `test_non_finite_energies_are_rejected`, `test_short_energy_band_is_rejected_rather_than_padded` | `test_demo13_state_energies_and_anchor.py` | existing |
| 3 | Reordered states | `test_real_hole_energies_let_a_hole_swap_be_detected` | `test_demo13_state_energies_and_anchor.py` | existing |
| 4 | State crossing | `test_plain_crossing_keeps_a_clean_identity` | `test_demo13_failure_modes_and_gate.py` | **NEW** |
| 5 | Avoided crossing | `test_avoided_crossing_hybridises_without_swapping_labels` | `test_demo13_failure_modes_and_gate.py` | **NEW** |
| 6 | Near-degenerate states | `test_near_degenerate_hole_states_are_tracked_by_overlap` | `test_demo13_state_energies_and_anchor.py` | existing |
| 7 | Wavefunction sign reversal | `test_sign_reversal_does_not_change_the_assignment`, `test_anchor_sign_reversal_is_handled` | `test_demo13_state_energies_and_anchor.py` | existing |
| 8 | Shuffled evaluation order | `test_anchor_assignment_is_independent_of_case_ordering`, `test_repeated_anchor_runs_are_identical`, `test_anchor_does_not_chain_between_cases` | `test_demo13_state_energies_and_anchor.py` | existing |
| 9 | Missing anchor | `test_missing_anchor_configuration_fails_loudly`, `test_incomplete_anchor_data_fails`, `test_unrecognised_anchor_name_is_refused_not_defaulted` | `test_demo13_state_energies_and_anchor.py` | existing |
| 10 | Incompatible anchor grid | `test_incompatible_grids_are_refused` | `test_demo13_state_energies_and_anchor.py` | existing |
| 11 | Ambiguous assignment | `test_ambiguous_state_assignment_is_recorded_not_smoothed`, `test_anchor_reports_ambiguity_rather_than_smoothing_it` | `test_demo13_ax_bayesian_optimization.py`, `test_demo13_state_energies_and_anchor.py` | existing |
| 12 | Incorrect historical detuning side | `test_real_v3_sign_corrections_are_read_only`, `test_derived_status_detects_each_corrected_field` | `test_demo13_v3_reporting.py` | existing |
| 13 | Incorrect historical heavy-hole gap | `test_the_hole_anticrossing_gap_is_the_smallest_spacing`, `test_real_v3_sign_corrections_are_read_only` | `test_demo13_v3_reporting.py` | existing |
| 14 | Corrected value unavailable | `test_unrecomputable_historical_values_are_unavailable_not_zero` | `test_demo13_v3_reporting.py` | existing |
| 15 | High χ² but infeasible detuning | `test_a_high_objective_infeasible_design_never_ranks_as_a_winner` | `test_demo13_failure_modes_and_gate.py` | **NEW** |
| 16 | No feasible trials | `test_a_campaign_with_no_feasible_trial_says_so_plainly` | `test_demo13_failure_modes_and_gate.py` | **NEW** |
| 17 | Winner at a search boundary | `test_a_winner_on_a_search_bound_is_detected_not_asserted` (lower/upper/interior), `test_the_v3_winner_reproduces_the_documented_bound` | `test_demo13_failure_modes_and_gate.py` | **NEW** |
| 18 | Missing alloy profile | `test_missing_alloy_output_names_the_directory_it_searched` | `test_demo13_ax_bayesian_optimization.py` | existing |
| 19 | Output missing a solver-written file | `test_a_run_missing_a_solver_written_file_is_named_with_what_it_blocks`, `test_a_file_demo13_never_writes_is_not_reported_as_a_failure` | `test_demo13_failure_modes_and_gate.py` | **NEW** |
| 20 | Stage 5 pointing at the protected v3 directory | `test_protected_experiment_names_are_refused`, `test_a_destination_inside_a_protected_experiment_is_refused`, `test_a_destination_containing_a_protected_experiment_is_refused`, `test_a_directory_holding_a_ledger_is_refused_whatever_it_is_called`, `test_a_symlink_to_a_protected_directory_is_refused`, `test_a_dotdot_alias_of_a_protected_directory_is_refused`, `test_a_differently_cased_protected_name_is_refused`, `test_the_experiment_directory_itself_is_refused_on_the_real_path` | `test_demo13_failure_modes_and_gate.py` | **NEW** (hardened) |

## What each new test establishes

**Crossing vs avoided crossing (4, 5).** These are different physics and had
been treated as one case. At a plain crossing the envelopes pass through
unchanged and only the energy order swaps, so each state still has exactly one
good partner and the assignment stays confident (`> 0.9`) while the labels
reorder. At an avoided crossing the envelopes *hybridise* into symmetric and
antisymmetric combinations and the energies repel to their minimum separation;
no state keeps a clean identity, and the tracker must report a collapsed
assignment margin (`< 0.5`) instead of a confident match. Reporting the second
case as confident is the failure this pair guards against.

**High objective, infeasible (15).** The largest χ² in a study is not the
winner if it is 46 nm off target. `top_ranked_valid_designs` filters on
`trial_valid`, and the test asserts the infeasible design is absent from the
ranking entirely rather than present with a flag a reader might miss.

**No feasible trials (16).** `feasibility_summary` must say that improvement
among infeasible designs is not progress, in those words, rather than reporting
a best-so-far curve that reads as success.

**Winner at a search boundary (17).** `guides13.py` asserted "t0021 sits on the
barrier **lower bound**" as hardcoded prose. That sentence keeps printing after
the winner moves. `design13.parameters_at_search_bounds` now computes it from
the live search space; the test checks the lower bound, the upper bound and an
interior point, and confirms the computed sentence reproduces the documented
claim for t0021.

**Missing solver output (19).** The bundle manifest reports every required file
as present/absent together with *the check its absence blocks*. A file Demo 13
structurally never writes is listed separately as `expected: false` — an earlier
version reported `requested_composition_profile.csv` as a missing *required*
file, which made every bundle on every machine, including the licensed one,
print a line an operator would reasonably read as a solver failure. That file is
written only by Demo 12's `_write_requested_profile`; Demo 13 analyses trials
with `demo11.analyse_case`, which does not emit it, so the realized alloy
profile must come from the native solver output instead.

**Stage 5 isolation (20).** Previously a single string comparison against
`workflow.experiment_state_dir`. Now `validation13.assert_isolated` refuses, on
the resolved path: the configured experiment; any directory named as a known
campaign; any directory holding a checkpoint or ledger whatever it is called;
any destination *inside* a protected experiment; and any destination
*containing* one. Symlinks and `..` aliases are resolved first, so neither
evades the check.

## Defects found by adversarial probing, and fixed

Four defects were found by attacking the two properties that protect a licensed
campaign and a licensed budget, rather than by reading the code:

1. **`stage5_state_dir` omitted the `demo_id` path segment** that
   `experiment_state_dir` includes, so Stage 5 resolved a level up, beside other
   demos' results. Worse, `assert_isolated` rebuilt the experiment path the same
   wrong way, so the "is this the campaign directory?" comparison compared two
   differently-constructed paths and **could never fire**. Regression:
   `test_stage5_is_a_sibling_of_the_experiment_not_a_level_above`,
   `test_the_experiment_directory_itself_is_refused_on_the_real_path`.

2. **The gate's anchor could name a different trial than the design it
   recomputes**, while loading wavefunctions from the design's directory — which
   would label one trial's states with another trial's identity and report the
   mismatch as a confident assignment. Now rejected at configuration load.
   Regression: `test_the_gate_anchor_must_be_the_design_it_recomputes`.

3. **A differently-cased protected directory name passed the name check.** On
   Windows `DEMO13_AX_EXPERIMENT_V3` and `demo13_ax_experiment_v3` are the same
   directory. The content check would still have caught it once the campaign
   directory existed, but protection must not depend on that. Regression:
   `test_a_differently_cased_protected_name_is_refused`.

4. **Any truthy `gate_passed` unblocked the full campaign.**
   `gate_is_satisfied` used `bool(record.get("gate_passed"))`, so a hand-edited
   `"yes"`, a timestamp, or even the string `"false"` would have released
   roughly sixty-nine licensed cases. Now requires exactly `True`. Regression:
   `test_only_an_exact_true_unblocks_the_campaign` (7 parameterized cases),
   `test_a_malformed_gate_result_does_not_unblock_the_campaign`.

## Deliberately not duplicated

The following already had adequate coverage and no test was added:
reordered states, near-degenerate states, sign reversal, shuffled order,
missing/incomplete anchor, incompatible grids, ambiguous assignment, the three
historical-correction scenarios, and missing alloy output. Adding a second
assertion of the same behaviour would grow the suite without growing what it
establishes.

## Limits

Every test here runs without a licensed solver. They establish that the code
*handles* each scenario correctly; they do not establish what nextnano++ will
actually produce at 0.025 nm or 0.10 nm. That is what the two-case Stage 5 gate
is for, and it has not run.
