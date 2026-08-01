# v3 reanalysis verification — Phase 11

Reanalysis was run **locally**, on the home laptop, against the v3 experiment
rehydrated from the transferred bundle. No nextnano executable exists on this
machine and none was invoked.

## Command

```bash
C:/Users/iyer95/miniconda3/envs/NMIP/python.exe nextnano/demos/13_ax_bayesian_optimization_graded_acqw/run_demo13.py
```

with `workflow.mode: analyze_existing_results` and
`workflow.experiment_state_dir: demo13_ax_experiment_v3`.

**Exit code 0.** Bundle: `20260801T172828Z_4f1cfe21`.

## Immutability — hashed before and after

| File | Before | After | Identical |
|---|---|---|---|
| `ax_experiment_snapshot.json` | `ecec3286bc404988…` | `ecec3286bc404988…` | ✔ |
| `trial_ledger.jsonl` | `3bba7f9663b6a5af…` | `3bba7f9663b6a5af…` | ✔ |
| `experiment_schema.json` | `20e567626ee8e25e…` | `20e567626ee8e25e…` | ✔ |
| `demo_yaml_snapshot.yaml` | `6e7470f242eadf37…` | `6e7470f242eadf37…` | ✔ |

`extracted/experiment_state_protection.json`:

```
experiment_state_unchanged   = True
terminal_records_changed     = []
terminal_records_removed     = []
ax_snapshot_modified         = False
generation_strategy_advanced = False
new_trials_generated         = False
```

| Requirement | Result |
|---|---|
| zero nextnano calls | ✔ zero `Executing` lines |
| zero new Ax candidates | ✔ zero `Generated new trial` lines; `new_trials_generated: False` |
| zero ledger modifications | ✔ all 23 terminal record hashes unchanged |
| zero checkpoint modifications | ✔ snapshot SHA-256 identical |
| all reports regenerated | ✔ 74 tables, 47 plot CSVs, 89 figures |
| lifecycle counts agree | ✔ see below |
| surrogate outputs finite | ✔ see below |
| truthful placeholders | ✔ withheld points carry a branch reason, not a solver excuse |

## Accounting — every consumer agrees

`extracted/campaign_accounting.json`, `tables/bo_budget_accounting.csv`,
`run_manifest.json → extra.campaign_accounting` and the console block are one
projection of one dict:

| Field | Value |
|---|---:|
| proposed candidates | **23** |
| preflight rejected | **7** |
| canonical duplicates | **0** |
| solver completed | **16** |
| Sobol completed | **6** |
| model-based completed | **10** |
| feasible completed | **3** |
| pending | **0** |
| remaining evaluations | **0** |
| optimization completed | **True** |
| analysis-only run | **True** |

`accounting_identity_holds: true` — 23 = 7 + 16 + 0 + 0.

`run_manifest.json → status` is now `dry_run_complete` (correct: this machine
has no solver). On the work laptop with `run_solver: true` the same code yields
`completed`, because refused proposals are no longer counted as cases that
failed to complete.

## Repaired outputs

| Table | Before | After |
|---|---|---|
| `bo_candidate_rejection_history.csv` | `note,no rows for this table in this run` | **7 rows**, every field populated |
| `bo_trial_iteration_mapping.csv` | did not exist | **23 rows**; MBM 1–10 |
| `bo_proposed_vs_realized_grading.csv` | did not exist | **23 rows** |
| `bo_budget_accounting.csv` | 0 preflight-invalid beside 7 abandoned | 7 preflight-rejected, 0 duplicates |

## Surrogate outputs — rows, finite values, and figures

| CSV | Rows | Finite predictions | Figure |
|---|---:|---:|---|
| `bo_surrogate_mean_asymmetry_vs_grading_thickness` | 625 | 275 | figure |
| `bo_surrogate_uncertainty_asymmetry_vs_grading_thickness` | 625 | 275 | figure |
| `bo_surrogate_mean_barrier_vs_grading_thickness` | 625 | 412 | figure |
| `bo_surrogate_uncertainty_barrier_vs_grading_thickness` | 625 | 412 | figure |
| `bo_acquisition_function_asymmetry_vs_grading_thickness` | 625 | 275 | figure |
| `bo_partial_dependence_asymmetry` | 25 | 25 | figure |
| `bo_partial_dependence_barrier_thickness` | 25 | 25 | figure |
| `bo_partial_dependence_grading_thickness` | 25 | 25 | figure |

**The finite counts are deliberately below the row counts.** 350 of 625 points
on the asymmetry slice, and 213 of 625 on the barrier slice, are graded
coordinates whose realized width falls below the 0.80 nm the mesh can resolve.
Their physical structure is abrupt. They are withheld from the graded surface
and each carries the reason:

> a graded point here realizes 0.38 nm, below the 0.8 nm minimum this mesh can
> resolve; the largest grade this geometry allows is 1.10 nm. The physical
> structure is abrupt, so it is not plotted as a graded prediction.

In the received bundle those same points were marked `prediction_available` and
plotted, so a surrogate surface showed a continuum of "graded" predictions over
a region where the structure never changed.

**No CSV contains rows without finite values in a populated figure**, and no
figure is a placeholder while its CSV holds usable data.

## Agent 2 audit — Phase 11

**PASS.**

- Hashes independently recomputed before and after; all four identical.
- Console, `campaign_accounting.json`, `bo_budget_accounting.csv` and
  `run_manifest.json` cross-checked field by field: no disagreement.
- Every surrogate CSV inspected: withheld rows carry a **branch** reason, never
  an error string and never "no licensed output".
- Iteration mapping manually checked against the required MBM sequence
  `t0007 t0008 t0009 t0011 t0017 t0018 t0019 t0020 t0021 t0022` → 1…10. ✔
- Rejection history manually checked: 7 rows, all `solver_launched: false`,
  replacement trials 1/11/17 consistent with the ledger order.

⚠️ **Warning carried forward:** this verification ran on a *rehydrated* copy.
The per-trial JSON files were reconstructed from `trial_ledger.jsonl` because
the bundle did not include them. The JSONL is the authoritative append-only
record and 0 lines were malformed, but the work-laptop original remains the
reference. Repeat the hash check there.
