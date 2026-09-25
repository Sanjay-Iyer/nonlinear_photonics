# Demo 29B — 100/300/500 K full-8-band electronic structure

Run **100 K and 500 K only**. The preserved 300 K reference is
`pilot_target_300K_trial2`. The 29A3 denser 300 K run is paused. These
instructions do not calculate full-8-band χ².

## 1. WORK — update the canonical `main` checkout

In PowerShell, save any local tracked work if `git status --short` is not empty.
If the fast-forward pull fails, stop and inspect the local branch; do not reset.

```powershell
Set-Location C:\Code\optics\nextnano\nonlinear_photonics
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git log -1 --oneline
```

## 2. WORK — activate `photonics` and check the frozen acquisition

```powershell
conda activate photonics
Set-Location C:\Code\optics\nextnano\nonlinear_photonics\nextnano\demos\29_temperature_chi2_study
python --version
python -c "import numpy, scipy, nextnanopy; print(numpy.__version__, scipy.__version__, 'nextnanopy available')"
python scripts\audit_dependencies.py
python scripts\run_nextnano.py --check
python scripts\run_nextnano.py --check-29b --output outputs\29B_deck_comparison.json
```

The last command writes a machine-readable report proving that the frozen
executed 300 K pilot deck and the generated 100/300/500 K decks differ only
at `temperature`. It must report `PASS`, 301 points, `0.10·π/a`, and finite-k
integration `0.03, 5, 1, none, no`. The runner also verifies that the WORK
nextnano executable and database hashes equal the successful 300 K pilot's
record before creating a run directory. A hash mismatch needs review, not an
automatic rerun or a changed deck. Keep the work-laptop license configured
through the existing private settings; never put it in Git or a transfer ZIP.

## 3. WORK — run and package 100 K

```powershell
python scripts\run_nextnano.py --run --temperature 100 --temperature-full8 --output nextnano\work_runs\29B_100K_full8
$runExit100 = $LASTEXITCODE
$run100 = 'nextnano\work_runs\29B_100K_full8'
$id100 = (Get-Content "$run100\run_metadata.json" -Raw | ConvertFrom-Json).run_id
$debug100 = "nextnano\run_logs\100K\$id100\demo29_29B_100K_debug_$id100.zip"
if (-not (Test-Path $debug100)) {
    python scripts\collect_debug.py --input $run100 --temperature 100 --run-id $id100 --output-dir "nextnano\run_logs\100K\${id100}_retry"
    $debug100 = "nextnano\run_logs\100K\${id100}_retry\demo29_29B_100K_debug_$id100.zip"
}
Get-Item $debug100 | Select-Object FullName,Length
if ($runExit100 -ne 0) { throw '100 K run failed; transfer the debug ZIP and retain the solver directory.' }
python scripts\package_29b.py --input $run100
if ($LASTEXITCODE -ne 0) { throw '100 K raw packaging failed; transfer the debug ZIP and retain the solver directory.' }
$raw100 = "nextnano\transfer\demo29_29B_100K_full8_raw_$id100.zip"
Get-Item $raw100 | Select-Object FullName,Length
```

The debug ZIP is generated automatically, including after a solver failure.
**Transfer `$debug100` first** if the run or raw packaging fails. Only package
raw data after the runner reports a successful solver and full validation.
`package_29b.py` independently rechecks every exported complex spinor and
native table, the 301-point dispersion, k-grid SHA-256, temperature/deck,
and the runtime logs; it writes a SHA-256 manifest for every archived file.
If the run stops early, do not run the package command.

## 4. WORK — run and package 500 K

```powershell
python scripts\run_nextnano.py --run --temperature 500 --temperature-full8 --output nextnano\work_runs\29B_500K_full8
$runExit500 = $LASTEXITCODE
$run500 = 'nextnano\work_runs\29B_500K_full8'
$id500 = (Get-Content "$run500\run_metadata.json" -Raw | ConvertFrom-Json).run_id
$debug500 = "nextnano\run_logs\500K\$id500\demo29_29B_500K_debug_$id500.zip"
if (-not (Test-Path $debug500)) {
    python scripts\collect_debug.py --input $run500 --temperature 500 --run-id $id500 --output-dir "nextnano\run_logs\500K\${id500}_retry"
    $debug500 = "nextnano\run_logs\500K\${id500}_retry\demo29_29B_500K_debug_$id500.zip"
}
Get-Item $debug500 | Select-Object FullName,Length
if ($runExit500 -ne 0) { throw '500 K run failed; transfer the debug ZIP and retain the solver directory.' }
python scripts\package_29b.py --input $run500
if ($LASTEXITCODE -ne 0) { throw '500 K raw packaging failed; transfer the debug ZIP and retain the solver directory.' }
$raw500 = "nextnano\transfer\demo29_29B_500K_full8_raw_$id500.zip"
Get-Item $raw500 | Select-Object FullName,Length
```

Each run prints its run ID and approximately 15-second blocks with temperature,
start/current time, elapsed time, solver stage, PID, process state, output
activity age, discovered/complete spinor frames, and the latest meaningful
solver message. There is no estimated percentage or time remaining. The
actual k-grid and frame count come from `k_points.txt`; the original 300 K
pilot had 81 integration frames and five complete points on Γ→+y. The new
run must pass deck/solver identity, 301 dispersion points, the same k-grid,
all 14 states × eight finite complex components in every frame, compositions,
and finite native growth dipole and growth/in-plane momentum tables.

**Keep these original WORK directories untouched** until HOME verifies and
analyzes the returned archives:

```text
nextnano\work_runs\29B_100K_full8
nextnano\work_runs\29B_500K_full8
```

Transfer four ZIPs by the usual external route: `$debug100`, `$raw100`,
`$debug500`, `$raw500`. Neither the directories nor ZIPs belong in Git.

## 5. HOME — place, verify, and compare

Copy the four ZIPs into `C:\code\nonlinear_photonics\nextnano_raw\`.
Substitute the two run IDs printed on WORK:

```powershell
Set-Location C:\code\nonlinear_photonics\nextnano\demos\29_temperature_chi2_study
$py = 'C:\Users\iyer95\miniconda3\envs\NMIP\python.exe'
$id100 = '<paste-100K-run-ID>'
$id500 = '<paste-500K-run-ID>'
$zip100 = "C:\code\nonlinear_photonics\nextnano_raw\demo29_29B_100K_full8_raw_$id100.zip"
$zip500 = "C:\code\nonlinear_photonics\nextnano_raw\demo29_29B_500K_full8_raw_$id500.zip"
& $py scripts\unpack_dense.py --zip $zip100 --destination C:\code\nonlinear_photonics\nextnano_raw\demo29
& $py scripts\unpack_dense.py --zip $zip500 --destination C:\code\nonlinear_photonics\nextnano_raw\demo29
```

The unpacker checks every SHA-256 before extracting and refuses to overwrite
an existing run folder. Compare the two new raw directories with the preserved
300 K original:

```powershell
$raw100 = 'C:\code\nonlinear_photonics\nextnano_raw\demo29\29B_100K_full8'
$raw300 = 'C:\code\nonlinear_photonics\nextnano_raw\demo29_300K_target_pilot_raw\pilot_target_300K_trial2'
$raw500 = 'C:\code\nonlinear_photonics\nextnano_raw\demo29\29B_500K_full8'
& $py scripts\run_nextnano.py --check-29b --reference-run $raw300 --output outputs\29B_reference_verification.json
& $py scripts\compare_29b.py --raw-100 $raw100 --raw-300 $raw300 --raw-500 $raw500 --output outputs\29B_full8band_temperature
& $py scripts\check_optical.py
```

The HOME comparison produces state/transition energy, composition,
localization, tracking, position-matrix, and native dipole/momentum CSVs in
`outputs\29B_full8band_temperature\comparison\`, plus plots and a summary
JSON. Per-temperature analyses and complex matrix blocks remain in sibling
folders `100K`, `300K_reference`, and `500K`. The comparison flags low state
overlap or state reordering rather than forcing agreement. `check_optical.py`
should still report **BLOCKED**: this is electronic structure only, not a
full-8-band χ² temperature result. All output folders are write-once; use a
new output name for a revised analysis.
