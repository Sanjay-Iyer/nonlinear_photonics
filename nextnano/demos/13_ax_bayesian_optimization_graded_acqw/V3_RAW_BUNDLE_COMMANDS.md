# Supplemental raw-output bundle — Phase 10

The transferred v3 bundle carried tables, plots, the Ax snapshot, the ledger and
the schema, but **no raw solver output**: no generated `case.in`, no execution
logs, no resolved configurations, and — most importantly — **no native
alloy-composition profiles**.

Consequence: the five trials recorded as genuinely graded (t0003 sigmoid,
t0004 cosine, t0008 erf, t0011 erf, t0019 erf) have **never had their realized
grading verified against what was requested**. Every statement about realized
grade shape currently rests on the geometry calculation, not on solver output.

These commands build a **small** supplemental bundle. Do not copy the whole
solver tree: nextnano++ writes a deep per-bias output hierarchy per trial.

## Trials to include

| Trial | Why |
|---|---|
| t0021 | best feasible; Stage 5 primary |
| t0022 | near-feasible boundary case, detuning −16 nm |
| t0017 | second feasible |
| t0005 | feasible Sobol reference |
| t0003, t0004, t0008, t0011, t0019 | the five genuine graded trials — the only ones that can verify grading realization |

Nine trials.

## Commands (work laptop, PowerShell, from the repository root)

### 1. Confirm a clean tree first

```powershell
git status --porcelain
```

⚠️ v3 was run from a **dirty** tree. Do not repeat that.

### 2. Pull this work

```powershell
git pull
```

### 3. Build the supplemental bundle

```powershell
python .\nextnano\scripts\bundle_raw_trials.py --experiment demo13_ax_experiment_v3 --trials t0003 t0004 t0005 t0008 t0011 t0017 t0019 t0021 t0022 --include inputs logs resolved-config alloy-profiles extracted --out .\nextnano\results\transfer\demo13_v3_raw_supplement
```

⚠️ **`bundle_raw_trials.py` does not exist yet.** It is specified below and is
the one piece of Phase 10 that is designed but not implemented — this pass ran
out of scope before writing it. Until it exists, the equivalent by hand:

```powershell
$trials = @('t0003','t0004','t0005','t0008','t0011','t0017','t0019','t0021','t0022')
$src = '.\nextnano\results\demo_runs\13_ax_bayesian_optimization_graded_acqw\demo13_ax_experiment_v3\runs'
$dst = '.\nextnano\results\transfer\demo13_v3_raw_supplement'
foreach ($t in $trials) {
  New-Item -ItemType Directory -Force "$dst\$t" | Out-Null
  Copy-Item "$src\$t\*.in" "$dst\$t\" -ErrorAction SilentlyContinue
  Copy-Item "$src\$t\demo_resolved.yaml" "$dst\$t\" -ErrorAction SilentlyContinue
  Copy-Item "$src\$t\extracted" "$dst\$t\extracted" -Recurse -ErrorAction SilentlyContinue
  Get-ChildItem "$src\$t\raw_output" -Recurse -Filter '*alloy*' -ErrorAction SilentlyContinue |
    ForEach-Object { Copy-Item $_.FullName "$dst\$t\" -ErrorAction SilentlyContinue }
}
```

### 4. Record what was copied and what was left behind

```powershell
python -c "import json,glob,os;d='./nextnano/results/transfer/demo13_v3_raw_supplement';m={'trials':{os.path.basename(t):sorted(os.path.relpath(f,t) for f in glob.glob(t+'/**/*',recursive=True) if os.path.isfile(f)) for t in glob.glob(d+'/t*')},'omitted':'full raw_output tree except alloy-composition files','experiment':'demo13_ax_experiment_v3'};open(d+'/raw_bundle_manifest.json','w').write(json.dumps(m,indent=2));print(sum(len(v) for v in m['trials'].values()),'files across',len(m['trials']),'trials')"
```

### 5. Verify sizes before transferring

```powershell
Get-ChildItem .\nextnano\results\transfer\demo13_v3_raw_supplement -Recurse | Measure-Object -Property Length -Sum
```

Expect well under 50 MB. If it is hundreds of MB, the raw tree was copied
wholesale — stop and narrow the filter.

## `bundle_raw_trials.py` — specification

Not yet implemented. Required behaviour:

- `--experiment`, `--trials`, `--out`, and `--include` from
  `{inputs, logs, resolved-config, alloy-profiles, extracted, all}`;
- **never** copy the whole `raw_output` tree unless `--include all` is passed
  *and* `--force` confirms it;
- write `raw_bundle_manifest.json` listing, per trial, every file **copied** and
  every category **omitted with the reason** — a bundle that silently omits the
  alloy profiles is how this gap arose;
- refuse to write into an existing non-empty directory without `--overwrite`;
- copy only; never modify the source experiment.

## Profile verification, once the bundle arrives

Compare requested against realized composition for the five graded trials using
Demo 12's procedure (`_extract_realized_composition` +
`grading12.compare_profiles`), reporting per trial:

- requested profile, requested width, realized width;
- composition RMS against `native_staircase_composition_rms_tolerance` (0.02);
- endpoint compositions against `composition_endpoint_tolerance` (1e-4);
- realized transition width against `grading_thickness_tolerance_nm` (0.05).

⚠️ **Agent 2 standing instruction:** no claim that a graded trial realized its
requested profile may be made until this report exists and its source files are
identified. "The geometry said 0.86 nm" is not evidence that 0.86 nm was grown.
