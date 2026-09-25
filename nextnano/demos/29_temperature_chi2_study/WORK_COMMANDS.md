# Demo 29 next handoff: 29A3 dense 300 K validation only

The 29A2 five-point analysis rejected matrix interpolation. This next solve
acquires more 300 K 8-band spinors. It is **not** a full-8-band χ² result and
does not start the 100 K or 500 K full-8-band runs. Keep the original WORK
solver directory until HOME verifies the returned archive.

## 1. WORK: pull the updated branch

From a clean work-laptop checkout (save any tracked local changes first):

```powershell
Set-Location C:\Code\optics\nextnano\nonlinear_photonics
git fetch origin
git switch codex/demo29-temperature-chi2
git status -sb
```

If this branch was already checked out from its **old rewritten history**, a
fast-forward pull may refuse. Confirm `git status --porcelain` is empty, then
run `git reset --hard origin/codex/demo29-temperature-chi2` to align that
clean checkout. Do not run the reset if Git reports tracked edits you need.

## 2. WORK: environment and static preflight

```powershell
conda activate photonics
Set-Location C:\Code\optics\nextnano\nonlinear_photonics\nextnano\demos\29_temperature_chi2_study
python --version
python -c "import numpy, scipy, nextnanopy; print('NumPy',numpy.__version__,'SciPy',scipy.__version__,'nextnanopy available')"
python scripts\run_nextnano.py --check
python scripts\audit_dependencies.py
```

`--check` must show `status: PASS`, `kmax_pi_over_a: 0.1`, 301 dispersion
points, and `29A3_dense` with `relative_size: 0.036`, `num_points: 11`.
The runner uses `NEXTNANO_EXE`, `NEXTNANO_DATABASE`, `NEXTNANO_LICENSE` or
the work-laptop's gitignored `nextnano/config/paths.local.yaml`; it checks
the paths before a Professional run. Do not print or transfer license text.

## 3. WORK: run 29A3 once

```powershell
python scripts\run_nextnano.py --run --temperature 300 --dense-finite-k --output nextnano\work_runs\29A3_300K_dense_validation
```

The runner refuses to overwrite this directory. It prints a unique **Run ID**,
the solver and log paths, then roughly 15-second status blocks with current
stage, start/current time, elapsed time, PID, process state, last output age,
actual discovered frames, complete spinor frames, and latest solver message.
There is no invented percentage or time-remaining estimate. After the solver
exits, expect a 301-point dispersion through `0.555714439232 nm⁻¹` and a
coverage report from the **actual** `k_points.txt`. A useful 29A3 result
needs at least eight complete on-path frames reaching at least 90% of kmax;
the debug package still appears if this check fails. A solver exit code 0
alone is not the scientific validation.

## 4. WORK: identify and save the small debug ZIP

```powershell
$run = 'nextnano\work_runs\29A3_300K_dense_validation'
$meta = Get-Content "$run\run_metadata.json" -Raw | ConvertFrom-Json
$runId = $meta.run_id
$debug = "nextnano\run_logs\300K\$runId\demo29_29A3_300K_debug_$runId.zip"
Get-Item $debug | Select-Object FullName,Length
```

Transfer **`$debug` first**, especially on failure. It contains the executed
deck, study configuration, Git/solver/Python provenance, stdout/stderr and
runner logs, warnings/errors, k-grid mapping, frame inventory, short file
previews, and preliminary target-path tracking/matrix summaries when those
checks can run. It excludes the complete wavefunction dataset.

If automatic debug packaging fails, regenerate without rerunning nextnano:

```powershell
python scripts\collect_debug.py --input nextnano\work_runs\29A3_300K_dense_validation --temperature 300 --output-dir "nextnano\run_logs\300K\${runId}_retry"
```

## 5. WORK: package the complete scientific raw data after success

```powershell
python scripts\package_dense.py --input nextnano\work_runs\29A3_300K_dense_validation
$rawZip = "nextnano\transfer\demo29_29A3_300K_full8_raw_$runId.zip"
Get-Item $rawZip | Select-Object FullName,Length
```

`package_dense.py` refuses insufficient path coverage and an existing ZIP.
Its lossless archive contains the exact deck, `k_points.txt`, 301-point
dispersion, all exported 8-component spinors/compositions/energies and native
matrix tables, solver and runtime logs, configuration, metadata, and SHA-256
manifest. **Retain `nextnano\work_runs\29A3_300K_dense_validation` untouched**
on WORK until HOME verifies this archive and analyzes the frames. Neither ZIP
belongs in Git.

## 6. HOME: place, unpack, verify, analyze

Copy the ZIP to `C:\code\nonlinear_photonics\nextnano_raw\` by your normal
manual transfer route. Substitute the printed `$runId` from WORK:

```powershell
Set-Location C:\code\nonlinear_photonics\nextnano\demos\29_temperature_chi2_study
$py = 'C:\Users\iyer95\miniconda3\envs\NMIP\python.exe'
$runId = '<paste-the-WORK-Run-ID>'
$zip = "C:\code\nonlinear_photonics\nextnano_raw\demo29_29A3_300K_full8_raw_$runId.zip"
& $py scripts\unpack_dense.py --zip $zip --destination C:\code\nonlinear_photonics\nextnano_raw\demo29
```

The unpacker verifies **every** SHA-256 hash before extraction and refuses
an existing run folder. Then:

```powershell
$raw = 'C:\code\nonlinear_photonics\nextnano_raw\demo29\29A3_300K_dense_validation'
& $py scripts\analyze_pilot.py --input $raw --output outputs\29A_full8band_300K\29A3_dense_validation\target_path
& $py scripts\analyze_sampling.py --analysis outputs\29A_full8band_300K\29A3_dense_validation\target_path --output outputs\29A_full8band_300K\29A3_dense_validation\sampling.json
& $py scripts\check_optical.py
```

The first analysis writes state tracking (`tracking.csv`), complex position
and component-overlap blocks, normalization/composition checks, and a native
growth-dipole comparison. The sampling report tests interpolation. The
optical check currently prints **BLOCKED** because the phase-preserving
8-band Bloch operator, polarization and spin convention are unresolved;
this is the expected scientific gate, not a failed solver run. There is no
authorized `calculate_full8.py` command until that mapping is established.

## Decision after HOME analysis

Accept 29A3 as a state/matrix validation only if actual path coverage,
tracking confidence and interpolation sensitivity pass. Resolve the optical
mapping separately before 29A4. Do not launch 29B's 100 K and 500 K
full-8-band runs until a defensible 300 K full-8-band χ² baseline exists.
