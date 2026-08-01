# Old-code audit — Demo 13, 2026-08-01

Repository-wide sweep for assumptions left behind by two changes:

1. the Ax search space moved from `grading_thickness_nm` (nm) to
   `grading_fraction_of_feasible_max` (dimensionless);
2. the 16-trial licensed campaign completed, so "dry run" and "no licensed
   output" statements became false.

Scope: the whole `nextnano/` tree, not only Demo 13. Search terms are the ones
named in the hardening brief. Counts are non-test, non-generated-output hits.

**The audit's central rule:** not every occurrence is stale. `parameter_grading_thickness_nm`
in a ledger record or an output table is the *realized physical width* and is
correct. What was stale was code that expected the **Ax search-space parameter**
to be called that.

---

## A. Findings that were defects, and their fixes

### A1. Surrogate slice points encoded as abrupt — every grading axis was inert

| | |
|---|---|
| **File** | `demo13.py`, `_slice_points` → `axsearch13.ax_parameters` |
| **Valid?** | No — stale |
| **Severity** | Highest. Silently wrong figures, not empty ones. |

`ax_parameters()` converts a *canonical* design, reading
`canonical["grading_thickness_nm"]`. Slice points are not canonical designs:
under the fraction parameterization they carry
`grading_fraction_of_feasible_max` and no thickness at all. The lookup
defaulted to `0.0`, hit the `thickness <= 0` branch, and encoded **every** slice
point onto the abrupt branch. All five surrogate surfaces were therefore drawn
over a grading axis that never varied, and the model was queried at the same
abrupt point 625 times.

**Action taken:** new `demo13._encode_search_point`, which takes a point already
in Ax coordinates and imposes only the hierarchical branch structure.
`_slice_points` and the partial-dependence loop both use it.

**Test:** `test_slice_points_use_the_live_grading_parameter` asserts every
encoded slice point is `interface_mode == "graded"` and that the grading
coordinate takes more than one distinct value.

### A2. Surrogate and partial-dependence plots keyed on a dead column

| | |
|---|---|
| **File** | `plots13.py` — 5 × `_surface(y_key="grading_thickness_nm")`, `bo_partial_dependence_grading_thickness.png` |
| **Valid?** | No — stale |

The slice rows carry `grading_fraction_of_feasible_max`. Looking up
`grading_thickness_nm` returned nothing, `usable` came back empty, and the
figure degraded to a placeholder — the *silent* version of the earlier
`KeyError`.

**Action taken:** `plots13.grading_axis(cfg)` resolves the live key and its
honest label from the configuration. All five surfaces and the partial-dependence
curve use it.

**Test:** `test_grading_axis_label_never_calls_a_fraction_nanometres`,
`test_slice_points_reject_a_stale_thickness_axis`.

### A3. A fraction plotted on an axis labelled "nm"

| | |
|---|---|
| **File** | `plots13.py` `AXIS["grading"] = "Grading thickness (nm)"` used for slice axes |
| **Valid?** | No — stale |

Once A2 was fixed the axis would have shown a number in [0.05, 1.0] under a
nanometre label.

**Action taken:** `grading13.AXIS_PROPOSED_FRACTION` is used for the fraction
coordinate; `AXIS["grading"]` is retained for genuinely physical thickness axes.
Realized nanometres are written into every slice CSV beside the fraction.

**Test:** `test_grading_axis_label_never_calls_a_fraction_nanometres`,
`test_slice_rows_carry_realized_thickness_beside_the_fraction`.

### A4. Observed-point overlays mixed two different coordinates

| | |
|---|---|
| **File** | `plots13.py` `_surrogate`, `observed_ag` / `observed_bg` |
| **Valid?** | No — stale |

Overlays used `parameter_grading_thickness_nm` (realized nm) on a surface whose
vertical axis is the proposed fraction. Two different quantities on one axis.

**Action taken:** `_observed_grading_coordinate` returns the trial's value *on
the axis being drawn* — proposed fraction under the fraction parameterization,
realized thickness under the thickness one.

### A5. `surrogate_slices.fixed_values.grading_thickness_nm: 1.5`

| | |
|---|---|
| **File** | `demo.yaml` |
| **Valid?** | No — stale, and out of range |

`1.5` is not a legal value of a fraction in `[0.05, 1.0]`. The key named no live
parameter, so it was ignored and the slice silently used its default.

**Action taken:** replaced with `grading_fraction_of_feasible_max: 0.5`, with a
comment stating it is dimensionless.

**Test:** `test_configured_slice_fixed_values_match_the_live_search_space`
fails if any fixed value names a parameter the search space does not have.

### A6. Predictive adapter never reconstructed (Defect 1)

| | |
|---|---|
| **File** | `axsearch13.surrogate_predictions`, `axsearch13.parameter_importance` |
| **Valid?** | No — wrong assumption about Ax |

Both used `experiment.client`, whose `GenerationStrategy.adapter` is `None` on a
deserialized client: the adapter is built during `gen` and is not serialized.
Every prediction raised `UnsupportedError`, and the rows carried that exception
text as their "reason".

**Action taken:** new `analysis13.reconstruct_predictive_model`. See
`analysis_model_reconstruction.json`. The two old functions remain in
`axsearch13` for the live-loop path but are no longer on the reporting path.

**Tests:** `test_predictive_adapter_is_reconstructed_without_advancing_the_strategy`
and six others.

### A7. Terminal ledger records were overwritable via `allow_update=True`

| | |
|---|---|
| **File** | `axsearch13.Ledger.write` |
| **Valid?** | No — contradicted the class's own docstring |

The terminal-record check sat *inside* `if not allow_update`, so one keyword
argument could overwrite a completed licensed trial. The docstring already
claimed "a terminal record is never overwritten".

**Action taken:** terminal check moved outside the branch. `allow_update` now
only covers its one legitimate case, finishing a `pending_no_solver` trial.

**Tests:** `test_ledger_records_are_immutable_once_terminal` (updated — it
previously asserted the hole), `test_pending_ledger_records_may_still_be_finished`.

### A8. Reanalysis wrote into the protected experiment directory

| | |
|---|---|
| **File** | `demo13.Experiment.__init__`, `main` |
| **Valid?** | No |

Every load rewrote `demo_yaml_snapshot.yaml` and `experiment_schema.json`, and
`main` rewrote `experiment_manifest.json`. A missing directory was silently
*created* as a new empty study.

**Action taken:** `Experiment(read_only=True)`; every mutator raises; the
manifest goes to the run bundle instead; a missing experiment in analysis mode
raises and lists the directories that do hold a snapshot.

**Tests:** `test_read_only_experiment_refuses_every_mutation`,
`test_read_only_refuses_to_invent_a_missing_experiment`,
`test_read_only_ledger_creates_nothing`.

### A9. `demo.yaml` pointed at the wrong experiment, in a solver-spending mode

| | |
|---|---|
| **File** | `demo.yaml` `workflow` |
| **Valid?** | No — stale and dangerous |

HEAD had `experiment_state_dir: demo13_ax_experiment` and `mode: closed_loop`.
A work laptop pulling HEAD and running would have called the licensed solver
against the wrong experiment directory.

**Action taken:** `experiment_state_dir: demo13_ax_experiment_v2`,
`mode: analyze_existing_results`.

**Test:** `test_demo_yaml_points_at_the_completed_experiment_in_analysis_mode`.

### A10. Placeholders blamed a missing solver for a missing model

| | |
|---|---|
| **File** | `plots13.PLACEHOLDER_REASON` applied to surrogate figures |
| **Valid?** | No — false statement |

Surrogate figures fell back to "No licensed nextnano++ output for this figure
yet". For the completed study that is untrue: the licensed output is precisely
what the model was fitted to.

**Action taken:** `PLACEHOLDER_REASON_NO_SURROGATE` plus
`_surrogate_placeholder`, which quotes the model's own recorded reason.

**Test:** `test_surrogate_placeholder_never_blames_a_missing_solver`,
`test_unavailable_model_reports_a_truthful_reason_not_a_missing_solver`.

### A11. Surface CSVs contained only the plottable subset

| | |
|---|---|
| **File** | `plots13._surface` |
| **Valid?** | No |

`_write_csv` received only rows that already had finite x, y and z. An empty
figure therefore had an empty CSV with no machine-readable reason.

**Action taken:** every requested row is written, with a `row_is_plottable`
column and the per-row `reason`.

### A12. `baseline_and_best_*` figures had no baseline

| | |
|---|---|
| **File** | `demo13.physics_curves` |
| **Valid?** | No |

The baseline was searched for *inside Demo 13's own ledger*
(`design_role == "reference"`), which never contains the Demo 11 reference. The
figures were named for a row they could not have. `demo11_best` was already
loaded a few lines away for the comparison table.

**Action taken:** `physics_curves(..., baseline=demo11_best)`, plus a
`curve_provenance` list and `baseline_and_best_curve_provenance.json` recording
every included and excluded row with a reason.

**Tests:** `test_physics_curves_include_the_supplied_baseline`,
`test_physics_curves_state_when_no_baseline_exists`.

### A13. Top-N ranking was not deterministic on ties

| | |
|---|---|
| **File** | `tables13.top_ranked_valid_designs`, `demo13.physics_curves` |
| **Valid?** | No |

Sorting by objective alone left equal-objective trials in ledger order. Also
accepted non-finite objectives.

**Action taken:** explicit `(objective, trial_index)` key in both places, so
tables and figures cannot disagree; non-finite objectives filtered.

**Tests:** `test_top_n_is_deterministic_on_ties`,
`test_non_finite_objectives_never_win_the_ranking`,
`test_best_trial_is_included_and_ranked_first` (pins trial 12).

### A14. Registry still declared the demo a dry run

| | |
|---|---|
| **File** | `demo_registry.yaml`, `_shared/registry.py` |
| **Valid?** | No — stale |

`status: implemented_dry_run` after 16 licensed trials. The vocabulary had no
state between "no solver has seen this" and "physically validated".

**Action taken:** new status
`licensed_optimization_completed_validation_pending`, in `SOLVER_TRUSTED` but
not in `PHYSICALLY_TRUSTED`. Demo 13 set to it, with `licensed_validation`
evidence that states the objective is relative and Stage 5 outstanding.

**Tests:** `test_registry_status_reflects_licensed_completion_but_not_validation`,
`test_registry_pending_checks_still_demand_stage_five`,
`test_registry_declares_demo13` (updated).

### A15. Validation report inferred licensed completion from *this process*

| | |
|---|---|
| **File** | `demo13.main` — `licensed = any(result.solver_success ...)` |
| **Valid?** | No |

In `analyze_existing_results` no solver runs, so this reported "no licensed
nextnano++ solver ran on this machine" for a study of 16 completed licensed
trials.

**Action taken:** `validation_lifecycle.json` separates licensed execution,
optimization completion, reporting, Stage 5 and dependency validation.
Licensed completion is read from the ledger.

### A16. `parameter_importance` presented undefined indices and one-hot columns

| | |
|---|---|
| **File** | `axsearch13.parameter_importance` |
| **Valid?** | Partly — one-hot merging was already correct |

`maximum_boundary_probability` is constant across the observations, so its
Sobol indices are NaN. Those would have been reported as numbers.

**Action taken:** `analysis13.ReconstructedModel.parameter_importance` drops
metrics whose indices are not finite, names them under
`metrics_without_defined_importance` with the reason, and attaches a caveat
quoting the **trial** count.

### A17. "observations" meant metric rows, not trials

| | |
|---|---|
| **File** | `analysis13` (introduced during this pass, caught before release) |
| **Valid?** | No |

`lookup_data()` returns one row per (trial, metric). For 16 trials × 4 metrics
that is 64 rows. Reporting 64 "observations" inflates the apparent evidence
fourfold, and the importance caveat quotes that number.

**Action taken:** `observations_used` counts distinct trials;
`observation_rows_used` carries the row count.

### A18. Latent pm/V label over a relative quantity

| | |
|---|---|
| **File** | `plots13._paper` |
| **Valid?** | Dormant, but a real trap |

`paper_comparison.units` alone selected `"Simulated |χ²| (pm/V)"`. Demo 13 runs
`metric.mode: relative`, whose values have no absolute scale.

**Action taken:** the pm/V label now additionally requires
`metric.mode != "relative"`.

### A19. Improvement ratio was not labelled as relative

| | |
|---|---|
| **File** | `report13.verdict` |
| **Valid?** | Incomplete |

The headline ratio was stated without saying what scale it is on — the source
of "1.8 times larger absolute chi2" style claims.

**Action taken:** the ratio is stated "on the relative arbitrary-unit scale",
followed by an explicit sentence that it is neither a pm/V ratio nor a measured
enhancement.

### A20. Provenance fields leaked into the `parameter_` namespace

| | |
|---|---|
| **File** | `metrics13.build_record` line 449, `synthetic13` line 149 |
| **Valid?** | No — cosmetic, but it is in the v2 ledger |

`build_record` prefixes every canonical key without stripping
`design13.PROVENANCE_FIELDS` first, producing `parameter__proposed_grading_fraction`
and `parameter__maximum_feasible_grading_nm` (double underscore) on every
completed v2 trial.

**Action taken:** *not* changed — rewriting it would not alter the existing v2
ledger, and those fields are the only place a completed v2 trial records its
proposed fraction. `grading13` reads both spellings instead, so the data is
usable. Flagged for v3, where `physical_design()` should be applied first.

**Test:** `test_grading_view_reads_both_v2_ledger_spellings`.

---

## B. Occurrences checked and found VALID — deliberately not changed

| Symbol | Where | Why it is correct |
|---|---|---|
| `parameter_grading_thickness_nm` | ledger records; `tables13` unit map (`nm`); `bo_top_ranked_valid_designs`; `report13.comparison_rows`; `plots13._parameter_sampling` | This is the **realized** width written by `design13.canonicalize`. A physical column, correctly in nm. |
| `grading_thickness_nm` | `design13.canonicalize`, `geometry13.evaluate`, `resolve_config` | The realized geometry variable. Not the Ax parameter. |
| `duplicate_tolerance.grading_thickness_nm` | `demo.yaml` | Deduplication compares **realized** designs. Correct. |
| `state_tracking.parameter_scales.grading_thickness_nm` | `demo.yaml` | Normalizes the realized physical coordinate. Correct. |
| `validation_study.local_refinement.grading_thickness_nm`, `fabrication_perturbations.grading_thickness_nm` | `demo.yaml` | Stage 5 perturbs the **physical** structure in nm, not the Ax coordinate. Correct — see C1 for the one place this needs care. |
| `synthetic13` `grading_thickness_nm` | synthetic surface | The synthetic objective is a function of realized geometry. Correct. |
| `relative_peak_chi2_abs`, `relative_chi2_at_target_wavelength_abs` | throughout | Current metric names. Verified by word-boundary search: **zero** bare `peak_chi2_abs` or `chi2_at_target_wavelength_abs` occurrences outside `axsearch13.RENAMED_METRICS` and the test that pins the rename. |
| `signed_detuning_nm` | reported in tables and plots | Reported everywhere, constrained nowhere. Verified: `feasibility13.py` and `axsearch13.py` contain **no** `signed_detuning` reference at all; the constrained metric is `absolute_detuning_nm`, bound by `maximum_detuning_nm: 15.0`. |
| `physical_qc_valid` | `constraints_enforced_outside_ax` | Correctly kept **out** of the Gaussian-process model; a binary flag is not a GP outcome. |
| `pm/V` | `report13`, guides, `README` | Every occurrence is a *denial* ("never pm/V"). Correct and worth keeping. |
| `bias_00000` | `_shared/demo_workflow.py:421`, `_shared/sweeps.py:219` (comments only) | Both are **comments** documenting the Windows path-length budget of nextnano++'s output tree. No path is constructed from a fixed `bias_00000`; layout resolution goes through `run_subdirectory()` and the keyed `RUN_SUBDIRECTORIES` map. Verified: zero occurrences in executable path-building code. |
| intermediate `case` directory in output paths | `_shared/sweeps.py`, `demo13.run_trial` | Resolved through `run_subdirectory(run_dir, key)`, not string concatenation. The earlier defect (commit `ac1be5a`, "Fix the run-output path that failed all 16 licensed Demo 13 trials") was fixed before this pass; no fixed-path assumption remains. |
| `implemented_dry_run` | `demo13.main` lifecycle fallback; Demo 11/12 registry entries | The fallback is reached only when no licensed trial exists. Demos 11 and 12 genuinely are dry runs. |

---

## C. Open items — flagged, not fixed in this pass

### C1. Stage 5 perturbs `grading_thickness_nm` but the winner is abrupt

`validation_study.local_refinement.grading_thickness_nm: [-0.25, 0.25]` is a
physical perturbation, which is right. But trial 12 realizes **0 nm** of
grading, so a −0.25 nm perturbation is meaningless and a +0.25 nm one changes
the interface *mode*, not just a width. `demo13.validation_cases` maps
`grading_thickness_nm → grading.selected_thickness_nm` (`demo13.py:1380`),
which is the physical setting, so it will build — but it will silently compare
an abrupt design against a graded one and call the difference "local
refinement".

**Fixed in this pass.** `robustness_cases` now skips a grading perturbation
entirely when the design realizes no grading, so a fabrication tolerance can
never silently change the interface mode. A companion function
`perturbation_fraction` reports each perturbation's size relative to the
dimension it perturbs, and `relative_drift_per_fractional_change` is written
alongside the raw drift — because ±0.2 nm is 40 % of a 0.5 nm barrier and 3 % of
a 7 nm well, and averaging those into one robustness score hides the only
sensitivity that matters for a design sitting at the barrier bound.

**Tests:** `test_grading_perturbation_never_turns_an_abrupt_design_graded`,
`test_grading_perturbation_still_applies_to_a_genuinely_graded_design`,
`test_perturbation_fraction_exposes_the_thin_barrier_sensitivity`.

### C2. `metrics13.build_record` provenance leak

See A20. Fix in v3 only; changing it now would make new records inconsistent
with the v2 ledger they must be compared against.

### C3. `axsearch13.surrogate_predictions` / `parameter_importance` now unused on the reporting path

Kept because the live closed loop still calls them and they are correct there
(a live client *has* a fitted adapter). They are dead weight on the analysis
path and should be consolidated once v3 lands.
