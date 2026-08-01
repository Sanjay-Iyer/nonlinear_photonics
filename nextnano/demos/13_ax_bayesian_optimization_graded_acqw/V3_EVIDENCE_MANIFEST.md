# v3 evidence manifest — Phase 1

Captured 2026-08-01. Nothing in this phase was altered; every number below was
recomputed from the transferred bundle rather than read out of a report.

## Provenance

| | |
|---|---|
| Repository commit at start | `587612a` ("demo13") |
| Working tree at start | clean |
| Home-laptop git state | clean |
| **Work-laptop git state when v3 ran** | **`587612a`, `git_dirty: true`** |
| Bundle | `C:\Users\iyer95\Downloads\13_v3-20260801T155314Z-1-001\13_v3` |
| Bundle produced | 2026-08-01T15:53:14Z |
| Files in bundle | 243 |

⚠️ The v3 campaign was executed from a **dirty** work-laptop tree
(`run_manifest.json → git_dirty: true`). The recorded commit `587612a` therefore
does **not** fully describe the code that produced these results. This is
reported, not corrected — see `V3_STALE_CODE_AND_REPORT_AUDIT.md` item P16.

## Protected files, as received

| File | Bytes | SHA-256 |
|---|---:|---|
| `ax_experiment_snapshot.json` | 541 384 | `ecec3286bc4049885903c8783c7e26f7420112e62911bbf70f21959aa77c324c` |
| `trial_ledger.jsonl` | 131 610 | `3bba7f9663b6a5afcd940f9948d2fb26fc8bcbe8a591a9c2bce7f05b44ad91d1` |
| `experiment_schema.json` | 691 | `20e567626ee8e25e35944d4a39c7ea3e02316065fa4da8e17c49257814259470` |
| `demo_yaml_snapshot.yaml` | 10 151 | `6e7470f242eadf377594efb7f9985863e918bb9cad64628f564b3e9fdde7aead` |
| `experiment_manifest.json` | 2 309 | `d1dbefba95a4771530fbd78a8a6284ea120128c033aef3ec90258787952481cd` |
| `run_manifest.json` | 21 438 | `68a11e4e2dec2fd788e38ac1c378ec89eebec3e0b95de5a3c6d3f3a80f0b26e1` |

The Downloads copy is the **evidence of record** and is never written to. All
work happens on a rehydrated copy (below).

## Schema — confirms this is v3, not v2

```json
{"experiment_schema_version": "demo13-search-space-3",
 "encoding": "hierarchical", "parameterization": "fraction",
 "range_bounds": {"asymmetry_s": [0.36, 0.56],
                  "central_barrier_thickness_nm": [0.85, 2.5],
                  "grading_fraction_of_feasible_max": [0.35, 1.0]},
 "minimum_resolvable_grading_nm": 0.8,
 "active_region_grid_spacing_nm": 0.05}
```

Every v3 marker is present: the 0.85 nm barrier floor, the 0.80 nm resolvable
grade and the 0.05 nm mesh. A v2 snapshot cannot load under this schema.

## Counts, recomputed from `trial_ledger.jsonl`

| Quantity | Value | How derived |
|---|---:|---|
| Ledger lines | 23 | one per write; no trial was written twice |
| Unique trial indices | 23 | 0–22 contiguous |
| **Proposals** | **23** | = rejected + completed |
| **Preflight rejected** | **7** | indices 0, 10, 12, 13, 14, 15, 16 |
| **Completed** | **16** | |
| Sobol *proposed* | 7 | one Sobol proposal (t0000) was rejected |
| **Sobol completed** | **6** | t0001–t0006 |
| MBM *proposed* | 16 | six MBM proposals were rejected |
| **MBM completed** | **10** | t0007, t0008, t0009, t0011, t0017, t0018, t0019, t0020, t0021, t0022 |
| **Feasible completed** | **3** | t0005, t0017, t0021 |
| Mechanically failed | 0 | |
| Duplicates | 0 | no rejection carries `canonical_duplicate` |
| Pending | 0 | |

`7 + 16 = 23` ✔ `6 + 10 = 16` ✔

The MBM completed sequence matches the brief exactly. Note the brief's "6
Sobol" refers to *completed* Sobol evaluations; seven Sobol proposals were made,
of which t0000 was rejected. That distinction is real and is why the Sobol
phase produced six observations from seven proposals.

## No solver ran for any rejected proposal

Three independent confirmations:

1. every rejected record carries `solver_launched: false`;
2. `console_logs/` contains exactly 16 logs, for trials
   `1,2,3,4,5,6,7,8,9,11,17,18,19,20,21,22` — the completed set, and **no log
   for any of 0, 10, 12, 13, 14, 15, 16**;
3. every rejection reason is `subresolution_grade: …`, produced by the
   preflight gate that runs before any deck is rendered.

All seven rejections are sub-resolution graded proposals. None is a duplicate,
a geometry failure, or a canonicalization failure.

## Rehydrated working copy

The bundle carries the ledger JSONL but not the per-trial
`trials/trial_XXXX.json` files, which `axsearch13.Ledger` reads. Those are
recoverable from the JSONL (it holds the complete record for every write), so
`analysis13.rehydrate_experiment_state` reconstructs them into

`nextnano/results/demo_runs/13_ax_bayesian_optimization_graded_acqw/demo13_ax_experiment_v3/`

| | |
|---|---|
| Files copied | snapshot, ledger, schema, YAML snapshot, experiment manifest |
| Trial records written | 23 |
| Malformed ledger lines | 0 |
| Trial indices | 0–22, contiguous |

This directory is gitignored and is a *working copy*. It refuses to overwrite a
non-empty experiment directory. Raw solver output (`runs/`) is **not** in the
bundle and is not reconstructed — see Phase 10.

## What the bundle does NOT contain

- `trials/` per-trial JSON (reconstructed, see above)
- `runs/` — raw nextnano output, generated `case.in` decks, execution logs
- **native alloy-composition profiles** — so no claim about *realized* grading
  shape can be checked from this bundle. This is why Phase 10 exists.

## Defects confirmed against the received reports

Each was verified in the bundle, not taken on trust:

| # | Claim | Evidence in bundle |
|---|---|---|
| 1 | run status `failed`, `optimization_completed=false` | `run_manifest.json → status: failed`; lifecycle `optimization_completed: False` |
| 4 | sub-resolution rejections mislabelled duplicates | `demo13._lifecycle` returns "rejected as a canonical duplicate" for *every* rejected record |
| 5 | rejection history empty | `tables/bo_candidate_rejection_history.csv` = `note,no rows for this table in this run` |
| 6 | budget reports zero preflight-invalid | `bo_budget_accounting.csv → preflight_invalid_proposals=0, duplicate_proposals=0` while `abandoned_ax_trials=7` |
| 16 | dirty git provenance | `run_manifest.json → git_dirty: true` |

Root causes (found in code, Phase 2 fixes them):

- **#6** `axsearch13.budget_accounting` classifies rejections by matching
  `REJECT_GEOMETRY` or `REJECT_DUPLICATE` in the reason string. v3's rejections
  carry `REJECT_SUBRESOLUTION`, which matches neither, so both counters read 0.
  This is a regression introduced when `REJECT_SUBRESOLUTION` was added without
  updating the accounting.
- **#1** `demo13` computes `optimization_completed` from
  `plan_record.get("remaining_new_solver_runs", 1) == 0`, but `plan()` returns
  no such key — it returns `remaining_trials`. The default `1` is therefore
  always used and the flag is **always** False. Same regression.
- **#1 (status)** `sweeps.write_sweep_manifest` sets `failed` unless
  `completed == len(results)`; `results` includes the 7 rejected proposals, so
  16 ≠ 23.
- **#4** `demo13._lifecycle` hard-codes the duplicate wording.

## Phase 1 verdict

**Agent 1:** evidence inventoried and hashed; working copy rehydrated; five
reported defects reproduced with located root causes.

**Agent 2 — PASS.** Counts independently recomputed from the ledger and agree
with the brief (23/7/16/6/10/3). The 7-plus-16 identity holds. No solver launch
for any rejected proposal, corroborated three ways. Protected files hashed
before any work. Two of the four root causes are regressions introduced by the
previous hardening pass, which the previous pass's own tests did not catch —
recorded as a testing gap to be closed in Phase 2, not merely fixed.
