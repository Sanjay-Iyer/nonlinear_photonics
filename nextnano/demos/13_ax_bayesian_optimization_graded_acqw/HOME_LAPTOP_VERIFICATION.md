# Home-laptop verification — Demo 13 hardening pass, 2026-08-01

Everything below ran on the home laptop with **no licensed nextnano++ solver**
and **no nextnano process launched at any point**.

## Environment

| | |
|---|---|
| Python | 3.11.15 (conda-forge, MSC v.1944 64-bit) |
| Interpreter | `C:\Users\iyer95\miniconda3\envs\NMIP\python.exe` |
| ax-platform | 1.3.1 (matches the repository pin) |
| botorch | 0.18.1 |
| torch | 2.12.1+cpu |
| numpy | 2.4.6 |
| pandas | 3.0.3 |
| OS | Windows 11 Home 10.0.26200 |
| Commit at start | `3591135` |

---

## Limits of what this machine can verify

**The completed 16-trial licensed experiment is not on this machine and cannot
be.** `.gitignore` excludes `nextnano/results/demo_runs/**`, so
`demo13_ax_experiment_v2` has never been in git and no `git pull` will bring it
here. Confirmed by search: the only experiment directories present are
`demo13_ax_experiment` (1 trial), `demo13_ax_experiment_synthetic` (16 trials)
and `demo13_verify_shortbo` (1 trial).

Three consequences, stated plainly rather than glossed:

1. **Phase 1's "confirm all 16 trial directories exist" cannot be executed
   here.** It is delivered as a *tool* (`analysis13.state_manifest`) plus a test
   that exercises it against a 16-trial fixture, and as step 4 of the
   work-laptop checklist.
2. **"Zero solver calls in analyze mode" *is* verified end-to-end here** — see
   command 5 below — but against the 16-trial synthetic experiment, not against
   v2. The code path is identical; the experiment is not.
3. **`demo13_ax_experiment_v2` as a directory name is unverified.** It comes
   from the hardening brief. The code now fails loudly and lists the available
   directories rather than inventing an empty study — demonstrated below.

Where an evaluated 16-trial study was needed, `demo13_ax_experiment_synthetic`
provided it: **same hierarchical search space, same fraction parameterization,
same four metrics, same ledger schema, same Ax version, same
`GenerationStrategy` ending on the MBM node**. It exercises identical code
paths. Its *numbers* are synthetic and are never presented as physical.

---

## Commands run, and results

### 1. Full repository test suite

```bash
C:/Users/iyer95/miniconda3/envs/NMIP/python.exe -m pytest nextnano/tests/ -q
```

**Result: `579 passed` in 759 s. Zero failures.**

Baseline before this pass was 533 collected (530 passed, 3 failed). The three
failures were consequences of deliberate contract changes made in this pass and
are documented below.

### 2. New test module in isolation

```bash
C:/Users/iyer95/miniconda3/envs/NMIP/python.exe -m pytest nextnano/tests/test_demo13_reanalysis_and_grading.py -q
```

**Result: `45 passed`.**

### 3. Synthetic smoke test — full pipeline, end to end

`workflow.mode: synthetic_smoke_test`, 5 initial trials + 4 BO iterations:

```bash
C:/Users/iyer95/miniconda3/envs/NMIP/python.exe nextnano/demos/13_ax_bayesian_optimization_graded_acqw/run_demo13.py
```

**Result: exit 0.** Console reported:

```
  completed trials            : 9
  failed trials               : 0
  feasible trials             : 5 of 9 completed
  proposals / evaluations     : 9 proposed, 9 completed, 0 preflight-invalid, 0 duplicate
  analysis surrogate          : refitted_current_generation_node (TorchAdapter; 9 observations)
```

That last line is the defect being fixed, working. Before this pass it would
have been an `UnsupportedError` swallowed into every prediction row.

### 4. Analyze-existing mode against a deliberately wrong directory

With the committed `demo.yaml` (`mode: analyze_existing_results`,
`experiment_state_dir: demo13_ax_experiment_v2`), which does not exist here:

```bash
C:/Users/iyer95/miniconda3/envs/NMIP/python.exe nextnano/demos/13_ax_bayesian_optimization_graded_acqw/run_demo13.py
```

**Result: refused, with an actionable message and no directory created:**

```
ERROR: analysis mode found no Ax snapshot in ...\demo13_ax_experiment_v2. It will
not create one, because an empty experiment would then be reported as though it
were the completed study.
Experiment directories that do hold a snapshot: demo13_ax_experiment,
demo13_ax_experiment_synthetic, demo13_verify_shortbo
Set workflow.experiment_state_dir to the one you meant.
```

This is the behaviour the work laptop needs if the directory name differs.

### 5. `analyze_existing_results` end to end against a 16-trial experiment

`demo.yaml` temporarily repointed to `demo13_ax_experiment_synthetic`
(16 completed trials, MBM node, same search space), then restored:

```bash
C:/Users/iyer95/miniconda3/envs/NMIP/python.exe nextnano/demos/13_ax_bayesian_optimization_graded_acqw/run_demo13.py
```

**Result: exit 0.**

```
  completed trials            : 16
  analysis surrogate          : refitted_current_generation_node (TorchAdapter; 16 observations)
  experiment state            : unchanged after reanalysis
```

`grep -c "Executing\|Generated new trial"` over the console log: **0**.

`extracted/experiment_state_protection.json`:

```
experiment_state_unchanged   = True
terminal_records_changed     = []
terminal_records_removed     = []
ax_snapshot_modified         = False
generation_strategy_advanced = False
new_trials_generated         = False
```

Every surrogate-derived artifact populated, and every figure a real plot rather
than a placeholder:

| CSV | rows | finite predictions |
|---|---|---|
| `bo_surrogate_mean_asymmetry_vs_grading_thickness.csv` | 625 | 625 |
| `bo_surrogate_uncertainty_asymmetry_vs_grading_thickness.csv` | 625 | 625 |
| `bo_surrogate_mean_barrier_vs_grading_thickness.csv` | 625 | 625 |
| `bo_surrogate_uncertainty_barrier_vs_grading_thickness.csv` | 625 | 625 |
| `bo_acquisition_function_asymmetry_vs_grading_thickness.csv` | 625 | 625 |
| `bo_partial_dependence_asymmetry.csv` | 25 | 25 |
| `bo_partial_dependence_barrier_thickness.csv` | 25 | 25 |
| `bo_partial_dependence_grading_thickness.csv` | 25 | 25 |
| `bo_parameter_importance.csv` | 15 | 15 |

Each surrogate CSV carries both `grading_fraction_of_feasible_max` (the Ax
coordinate) and `realized_grading_thickness_nm`,
`proposed_grading_thickness_nm_unsnapped`, `maximum_feasible_grading_nm`,
`realized_interface_mode` (the structure).

Three things this run reported as *absent, with a reason* — all correct for a
synthetic experiment, and all of them silent before this pass:

- `validation_lifecycle.json` → `state: implemented_dry_run`,
  `licensed_trials_completed: 0`, `synthetic_trials_completed: 16`. The
  synthetic filter works: a machine with no licence cannot claim a licensed run.
  The work-laptop case is covered instead by
  `test_reanalysis_of_licensed_trials_reports_licensed_completion`, which
  asserts 16 non-synthetic completed records in analyze mode yield
  `licensed_optimization_completed_validation_pending` with
  `solver_invoked_by_this_run: False`.
- `baseline_and_best_curve_provenance.json` → `baseline_found: false`, with the
  reason "no Demo 11 abrupt reference result was found under the results root".
- Each top design → `included: false`, "this record carries no output directory,
  so its raw solver output cannot be located" (synthetic trials have no run
  directories).

### 6. Reconstruction against a real 16-trial snapshot

Against `demo13_ax_experiment_synthetic/ax_experiment_snapshot.json`:

```
fit_status                        = refitted_current_generation_node
model_class                       = TorchAdapter
generation_node before → after    = MBM → MBM
observations_used                 = 16 trials (64 metric rows)
predictive_metrics                = absolute_detuning_nm, maximum_boundary_probability,
                                    relative_chi2_at_target_wavelength_abs,
                                    state_tracking_confidence
generation_strategy_advanced      = False
new_trials_generated              = False
original_experiment_state_modified = False   (SHA-256 identical before/after)
```

---

## Required checks from the brief

| Check | Result | Evidence |
|---|---|---|
| Analyze-existing makes zero solver calls | ✅ end-to-end | Command 5: zero `Executing` / `Generated new trial` lines in a real 16-trial analyze run, plus two structural guarantees |
| No new candidates generated | ✅ | `new_trials_generated = False`; `test_read_only_experiment_refuses_every_mutation` |
| No Ax trial status changes | ✅ | trial count and statuses identical after reconstruction |
| No terminal ledger record changes | ✅ | `test_reconstruction_never_modifies_terminal_ledger_records`, per-record SHA-256 |
| Predictive adapter reconstruction succeeds | ✅ | `TorchAdapter` on a real 16-trial snapshot |
| Objective posterior predictions finite | ✅ | `test_objective_and_constraint_predictions_are_finite` |
| Constraint predictions finite where modelled | ✅ | all 3 constraint metrics predicted |
| Hierarchical abrupt prediction works | ✅ | `test_hierarchical_branches_predict_and_invalid_ones_say_why` |
| Hierarchical graded prediction works | ✅ | same |
| Partial-dependence CSV has finite predictions | ✅ | 25/25 finite in all three curves |
| Surrogate slice CSV has finite predictions | ✅ | 625/625 finite in all five surfaces |
| Acquisition output finite or truthful reason | ✅ | 625/625 finite; method string denies it is Ax's acquisition |
| Parameter importance populated or truthful reason | ✅ | populated; constant metric reported as undefined, not zero |
| Fraction parameterization uses no stale thickness bounds | ✅ | `test_slice_points_reject_a_stale_thickness_axis` |
| Plotted physical grading uses realized thickness | ✅ | realized columns in every slice CSV; axis labelled as a fraction |
| Zero-realized-grade proposals treated as abrupt | ✅ | `test_graded_proposal_that_snaps_to_zero_is_physically_abrupt` |
| Best design selection includes trial 12 | ✅ | `test_best_trial_is_included_and_ranked_first` |
| Baseline-and-best outputs contain the right rows | ✅ | `baseline_and_best_curve_provenance.json`; two tests |
| Placeholders never falsely claim licensed output absent | ✅ | `test_surrogate_placeholder_never_blames_a_missing_solver` |
| Arbitrary-unit χ⁽²⁾ never labelled pm/V | ✅ | pm/V label now gated on `metric.mode != relative` |
| Absolute detuning is the feasibility metric | ✅ | verified by search: zero `signed_detuning` references in constraint code |
| Old v2 outputs still load | ✅ | `test_grading_view_reads_both_v2_ledger_spellings` |
| Stage 5 code accepts the fraction parameterization | ✅ | `validation_cases` maps to the physical `grading.selected_thickness_nm`, not to the Ax coordinate. `robustness_cases` no longer perturbs the grading of a design that realizes none (`test_grading_perturbation_never_turns_an_abrupt_design_graded`), and `perturbation_fraction` separates the ±40 % thin-barrier change from the ±3 % well change (`test_perturbation_fraction_exposes_the_thin_barrier_sensitivity`) |
| All pre-existing tests continue passing | ✅ | 571 passed; 3 deliberate contract changes updated below |

---

## Pre-existing tests changed, and why

Three tests failed after the code changes. All three asserted behaviour this
pass deliberately changed; none indicates a regression.

1. **`test_ledger_records_are_immutable_once_terminal`** — asserted that
   `allow_update=True` *could* overwrite a terminal record
   (`ledger.write({...,"status":"failed"}, allow_update=True)` then
   `assert status == "failed"`). That contradicted the `Ledger` class docstring
   and meant one keyword could overwrite a completed licensed trial. Rewritten
   to assert the guarantee.

2. **`test_ledger_index_is_append_only`** — passes unchanged. Its behaviour
   (updating a *pending* record) is preserved, and is now also covered
   explicitly by the new `test_pending_ledger_records_may_still_be_finished`.

3. **`test_registry_declares_demo13`** — asserted `status ==
   "implemented_dry_run"` and `licensed_validation is None`. Both were true when
   written and are false after 16 licensed trials. Updated to assert the new
   status and that the evidence text states the objective is not calibrated
   pm/V and that Stage 5 remains owed.

---

## Not verified here — carried to the work laptop

1. That `demo13_ax_experiment_v2` is the correct directory name.
2. That the v2 experiment holds 16 trial files and 16 ledger records.
3. Zero `Executing ... case.in` lines in an actual analyze-mode console log.
4. That the reconstruction succeeds on the **real** v2 snapshot. The synthetic
   fixture matches it in schema, Ax version and generation-node state, so the
   code path is identical — but the real snapshot has not been loaded.
5. Any physical statement whatsoever. No licensed solver ran here.
