# Demo 30 — optional 0.2·π/a extension: WORK-laptop package

**Status: prepared, NOT run.** No 0.2·π/a data exist in Demo 30 until you bring a run
back. Demo 30's main result uses the **0.1·π/a control** and does not need this run.

## What the run is

A single licensed nextnano++ run. Its deck is the control deck
(`D023_2026-09-04_kp8-disp-k0p10pia-n301-300K`) with exactly **two lines changed**:

| Line | Control | This run |
|---|---|---|
| k endpoint | `point{ k = [0, 0.555714439232, 0] }` (0.1·π/a) | `point{ k = [0, 1.111428878464, 0] }` (0.2·π/a) |
| points | `num_points = 301` | `num_points = 601` (pilot: `7`) |

- **k grid.** The endpoint is exactly 2 × the control endpoint, so every control k node is
  also a node of the new grid (spacing 0.0018524 nm⁻¹).
- **Held fixed.** Structure, temperature (300 K), states (6 e + 8 h), grids and outputs
  are unchanged.
- **Per-k states are intentionally not requested.** The Demo 30 model uses only the 8-band
  dispersion and freezes matrix elements at k = 0. That also avoids the Demo 28K failure,
  where per-k states came back only at k = 0.

Both decks passed the Free nextnano++ 3.0.0 grammar check on HOME (`run_plan.json`).

## Do we need this run? Two routes

- **Route A — no run.** The failed 28K run (`nextnano_pro_raw_results/`) already contains an
  8-band dispersion to exactly 0.2·π/a with 601 points.
  - On the 301 k nodes it shares with the control, its 14 relevant states reproduce the
    control energies to **3×10⁻¹¹ eV** (checked read-only on 2026-09-24).
  - For Demo 30's frozen-matrix model, that dispersion is enough.
  - Registering it (a copy, with status `partial`: dispersion valid, per-k states missing)
    needs your approval, because you asked to leave 28K untouched for now.
  - Caveat: its deck asked for 8 e + 16 h states and different outputs. The shared-node
    agreement shows this does not change the dispersion, but it is not a single-line diff.
- **Route B — this package.** A clean run: the control deck with only the two changes
  above. About 20 minutes on WORK. Use this route if "every other parameter held fixed"
  should hold literally.

## Expected cost

| | Runtime | Output |
|---|---|---|
| Pilot (7 k points) | about 1–2 min | about 18 MB (the k = 0 state files dominate) |
| Full (601 k points) | about 20 min | about 18.5 MB, 740 files (zip about 5–7 MB) |

The estimates are based on the control run, which took 10 min 20 s for 301 k points on
WORK, and on 28K, which took 16.6 min for 601 k points with 24 states.

## Exact commands

**HOME** (already done; rerun only if the control deck changes):

```powershell
python nextnano/demos/30_absorption_study/work_laptop/kmax_run.py prepare
```

Then commit and push, when you decide to.

**WORK** (from the repository root, in a Python environment with numpy and PyYAML):

```powershell
git pull
python nextnano/demos/30_absorption_study/work_laptop/kmax_run.py preflight
python nextnano/demos/30_absorption_study/work_laptop/kmax_run.py pilot
```

**Continue only if the pilot says PASS.** Then:

```powershell
python nextnano/demos/30_absorption_study/work_laptop/kmax_run.py full
python nextnano/demos/30_absorption_study/work_laptop/kmax_run.py package C:/nn_results/D030_<date>_kp8-disp-k0p20pia-n601-300K
```

Upload `C:/nn_results/D030_<date>_kp8-disp-k0p20pia-n601-300K.zip` to Google Drive, folder
`nextnano_raw/demo_030/`. **Do not commit it to Git.**

**HOME:**

1. Download the zip.
2. Unzip it into `nextnano_raw/demo_030/`, so that
   `nextnano_raw/demo_030/D030_<date>_kp8-disp-k0p20pia-n601-300K/` exists.
3. Run:

```powershell
python nextnano/scripts/raw_data.py verify nextnano_raw/demo_030/D030_<date>_kp8-disp-k0p20pia-n601-300K
python nextnano/demos/30_absorption_study/work_laptop/kmax_run.py lock-entry nextnano_raw/demo_030/D030_<date>_kp8-disp-k0p20pia-n601-300K --write
python nextnano/demos/30_absorption_study/scripts/run_demo30.py
```

`lock-entry --write` adds `kp8_dispersion_k0p20` to `inputs/raw_data.lock.json`. From then
on, 30F computes the 0.2·π/a comparison automatically. Commit the lock change, not the data.

## What `pilot`, `full` and `validate` check

Results go to `validation.json` in the run folder. The run fails if any of these fail:

- the solver exit code is 0, `job_done.txt` exists, and the log has no "LIMITED FREE VERSION";
- the dispersion has the expected number of k points, ends at 1.111428878464 nm⁻¹, and
  has 14 states with finite energies;
- **genuine finite-k data:** energies change by more than 0.05 eV between k = 0 and k_max
  (the 28K failure mode would fail here);
- **same physics as the control:** at the shared k nodes (0, 100, 200, 300 of the control
  grid), every state matches the control to ≤ 1×10⁻⁶ eV
  (`control_reference_nodes.json`);
- the k = 0 spectrum and spinor composition exist; the pair assignment needs them.

Paths come from `nextnano/config/paths.local.yaml` or the tracked work-machine YAML.
They can be overridden with `--exe/--database/--license/--results-root`. The script refuses
a Free executable. The license path is replaced by `<license>` in `run_info.json`, and
license lines are redacted from the solver log.

## Run folder produced on WORK

```text
C:/nn_results/D030_<date>_kp8-disp-k0p20pia-n601-300K/
    RUN_RECORD.json         written by `package`; the metadata that travels with the data
    SHA256SUMS.txt          every file under data/
    run_info.json           command, times, executable/database hashes
    validation.json         the checks above
    solver_log_redacted.txt
    data/k0p20pia_n601/...  untouched nextnano++ output, including the deck copy
```

If a run fails, keep it and package it anyway: `package` records `"status": "failed"`.
Bring it home too, because a failed run is information. Demo 30 never uses it as input.
