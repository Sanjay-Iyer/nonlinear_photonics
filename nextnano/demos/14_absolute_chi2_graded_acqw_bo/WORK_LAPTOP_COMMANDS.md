# Demo 14 — work-laptop commands

Run in order. Every command carries one of three labels:

| Label | Meaning |
|---|---|
| **SAFE** | Reads, renders or tests only. No nextnano++ process starts. |
| **PAID — 2 runs** | The licensed startup gate. Exactly two solver calls. |
| **PAID — 30 runs** | The full campaign. |

Demo 14 writes only under `nextnano/results/demo_runs/14_absolute_chi2_graded_acqw_bo/`.
It cannot touch Demo 13.

---

## 1. Pull and check the tree — SAFE

```bash
cd /c/code/nonlinear_photonics && git status --porcelain && git pull && git rev-parse HEAD
```

## 2. Activate the licensed environment — SAFE

```bash
conda activate NMIP
```

## 3. Verify Python and the solver — SAFE

```bash
python -c "import ax, botorch, numpy, scipy, yaml; print('ax', ax.__version__); import nextnanopy; print('nextnanopy', nextnanopy.__version__)"
```

## 4. Create the machine config — SAFE, **do this once**

`nextnano/config/machines/nextnano_machine.local.yaml` is **gitignored on
purpose** — it holds machine-specific paths, and the repository's own comment
says it is "created by hand on each machine, never tracked. A `git pull` will
never overwrite it." So `git pull` does **not** deliver it. Create it here, once,
with the values proven by the successful licensed run on this laptop:

```bash
cat > nextnano/config/machines/nextnano_machine.local.yaml <<'YAML'
# Work laptop. Values taken from a successful licensed nextnano++ run's
# machine_summary.json / run_manifest.json and the raw solver log, so they are
# known-good rather than discovered. Explicit paths are used instead of
# auto-discovery precisely because these are already proven.
#
# This file is gitignored and must never be committed.
portable_root: ../2026_07_03
executable: C:\Code\optics\nextnano\2026_07_03\nextnano++\bin\nextnano++_Intel_64bit.exe
license: C:\Code\optics\nextnano\2026_07_03\License\License_nnp.lic
database: C:\Code\optics\nextnano\2026_07_03\nextnano++\database\database.nnp
threads: 4
run_solver: true
results_root: null
YAML
echo "written"
```

The keys are exactly the seven the loader accepts (`portable_root`,
`executable`, `license`, `database`, `threads`, `run_solver`, `results_root`) —
it validates strictly and rejects anything else.

`run_solver: true` is deliberate rather than `auto`: these paths are known-good,
so there is no reason to let discovery decide, and an explicit `true` means a
missing file fails loudly instead of quietly downgrading to a dry run.

Verify it resolves:

```bash
python -c "import sys; sys.path.insert(0,'nextnano/demos/_shared'); import demo_workflow as w; m=w.load_machine_config(); print('source    :', m.source_path); print('executable:', m.executable); print('license   :', m.license); print('database  :', m.database); print('threads   :', m.threads); print('run_solver:', m.run_solver)"
```

All four paths must print, `run_solver` must be `True`, and `source` must end in
`nextnano_machine.local.yaml`.

## 5. Run the Demo 14 test suite — SAFE

```bash
python -m pytest nextnano/tests/test_demo14_grading.py nextnano/tests/test_demo14_absolute_chi2.py nextnano/tests/test_demo14_harness.py -q
```

Expect **94 passed**.

## 6. Run the whole repository suite — SAFE

```bash
python -m pytest nextnano/tests/ -q
```

## 7. Demo 14 production preflight — SAFE

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --preflight
```

Must end with `DEMO 14 REAL RUN PREFLIGHT: PASS`. On the work laptop this also
checks that the nextnano++ executable exists.

## 8. Mock campaign, to prove the harness on this machine — SAFE

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --mock-campaign
```

Writes to a temporary directory, spends no licensed time, and must print
`Mock campaign: COMPLETED 5/5 trials`.

---

## 9. THE LICENSED STARTUP GATE — PAID — 2 runs

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --gate
```

This is the one thing the home laptop could not do. It builds the **same linear
composition profile twice** — natively via `ternary_linear{}` and as an imported
table via `ternary_import{}` — solves both, and compares electron energies,
heavy-hole energies, χ²(1550), peak wavelength and boundary probability.

**Why it matters:** fermi, erf and cosine all reach nextnano++ through
`ternary_import`, a path no nextnano++ instance in this project has ever
executed. If the solver reads an imported profile differently than we intend,
24 of the 30 campaign trials silently solve the wrong material and still produce
plausible pm/V numbers. Two runs to de-risk twenty-four.

### What PASS looks like

```
  DEMO 14 LICENSED STARTUP GATE
  Paid solver calls : 2 (native linear, imported linear)
  electron_energies_eV      native=[6 values]  imported=[6 values]  diff=...  PASS
  heavy_hole_energies_eV    ...                                              PASS
  chi2_xzx_abs_at_1550_pm_per_V ...                                          PASS
  peak_wavelength_nm        ...                                              PASS
  maximum_boundary_probability ...                                           PASS
  Paper reference plausible : True
  Paper reference valid     : True
  GATE PASSED -- the 30-trial campaign may be launched.
```

**Only proceed to step 10 if you see `GATE PASSED`.** Step 10 refuses to start
otherwise; it reads `demo14_startup_gate_result.json` and requires
`gate_passed: true` exactly — a `null` verdict never counts as a pass.

If the gate FAILS, stop and send me the gate directory. That result is the most
scientifically valuable thing this session can produce, because it means the
import path does not do what we assumed.

---

## 10. THE REAL 30-TRIAL CAMPAIGN — PAID — 30 runs

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --run
```

Creates a NEW directory `demo14_<UTC>_<sha>_<id>/`. It cannot resume an old run
— resuming requires naming the directory explicitly (step 12).

10 stratified initialization trials (every grading family gets at least 2), then
20 Ax/BoTorch trials, to **30 completed** solver trials. A physically infeasible
trial counts against the budget; a preflight rejection does not and is escalated
as a bug; a technical failure stops the campaign with everything preserved.

The debug bundle is built automatically when it finishes.

## 11. Watch progress from another shell — SAFE

```bash
python -c "import json,sys,pathlib; r=sorted(pathlib.Path('nextnano/results/demo_runs/14_absolute_chi2_graded_acqw_bo').glob('demo14_*'))[-1]; print(json.dumps(json.loads((r/'RUN_STATUS.json').read_text()), indent=2))"
```

To stop cleanly, press **Ctrl+C once** in the campaign shell. It finishes the
current trial, checkpoints, sets the status to `INTERRUPTED` and exits.

## 12. Resume an interrupted run — PAID — remaining trials only

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --resume nextnano/results/demo_runs/14_absolute_chi2_graded_acqw_bo/<RUN_DIRECTORY>
```

Completed trials are never repeated.

## 13. Analyze a completed or partial run — SAFE

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --analyze nextnano/results/demo_runs/14_absolute_chi2_graded_acqw_bo/<RUN_DIRECTORY>
```

## 14. Regenerate plots without the solver — SAFE

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --plots nextnano/results/demo_runs/14_absolute_chi2_graded_acqw_bo/<RUN_DIRECTORY>
```

## 15. Build the LLM debug bundle — SAFE

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --debug-bundle nextnano/results/demo_runs/14_absolute_chi2_graded_acqw_bo/<RUN_DIRECTORY>
```

Produces `debug_bundle/demo14_<run_id>_debug_bundle.zip` plus `CONTENTS.md`
stating exactly what is and is not inside. **This is the file to send back.**

## 16. Build the full raw bundle only if asked — SAFE

```bash
python nextnano/demos/14_absolute_chi2_graded_acqw_bo/run_demo14.py --full-raw-bundle nextnano/results/demo_runs/14_absolute_chi2_graded_acqw_bo/<RUN_DIRECTORY>
```

---

## What to send back

1. `debug_bundle/demo14_<run_id>_debug_bundle.zip`
2. The gate directory `demo14_startup_gate/` (especially if it failed)
3. The console output of steps 9 and 10

## If something goes wrong

The campaign stops itself on any technical failure and writes
`summaries/DEMO14_FAILURE_SUMMARY.md` naming the trial, stage and reason. Build
the debug bundle (step 15) and send it — the failed trial's directory, deck,
imported profile, solver stdout/stderr and traceback are all preserved.
