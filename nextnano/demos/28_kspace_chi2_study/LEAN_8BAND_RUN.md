# Lean extended 8-band run — current instructions

This supersedes the original 1201-point acquisition instructions. Existing raw
runs and 28A–28J results are not modified. No Professional solve was run on HOME.

## Changes

- Endpoint stays **0.20 pi/a**, with **601** uniform radial k points.
- Same structure, spatial grid, LAPACK solver, **8 electron + 16 valence** states.
- Keep unshifted complex **CB/HH/LH/SO** envelopes and composition at each k.
- Disable duplicate S/X/Y/Z envelopes, shifted copies, probability profiles,
  duplicate composition representation and oscillator strengths.
- Keep small energy, dipole/momentum, material and solver records as cross-checks.
- No single-band anchors or k=0 matrix freezing; Equation 2 is unchanged.

The 601-point grid has the same nominal spacing as 301 points through 0.10 pi/a.
That is a starting point, not proof of converged high-k tracking. All thirteen
analysis cutoffs and five presentation cutoffs remain available.

Edit `config/extended_8band.json`: `k_points=601`, `output_profile="lean"`,
`transfer_limit_bytes=1000000000`. Plans now go to
`outputs/28K_extended_8band/work_laptop_lean/`. The original `work_laptop/`
preflight artifacts remain historical and untouched.

## First: tiny WORK pilot

Pull the updated Demo28 code/config/docs/tests. Activate the project Python
environment. Executable/database/license resolution remains CLI options, then
`NEXTNANO_*` variables, then `nextnano/config/paths.local.yaml`.

From the repository root:

```powershell
python nextnano/demos/28_kspace_chi2_study/scripts/run_extended_8band.py --run --pilot
```

This executes Professional **on WORK** for three k points spanning the same range,
24 states, same lean outputs. It is an output-coverage check, not a convergence test.
It uses separate `nextnano/extended_8band_lean_pilot/` and pilot plan directories.
Require raw and compact validation PASS before the full run. Specifically, verify
CB/HH/LH/SO envelopes at nonzero k survive `envelopes = no`; grammar alone cannot
prove output behavior. Keep any failed pilot for inspection, without substituting
k=0 data. Production analysis rejects pilot datasets.

Safe HOME parser-only checks: `--preflight` and `--preflight --pilot`.
Without `--run`, no physics solve launches.

## Then: full WORK run

```powershell
python nextnano/demos/28_kspace_chi2_study/scripts/run_extended_8band.py --run
```

Existing output folders are refused. No currently running process is touched.
New settings apply only to a new invocation after pulling. Successful lean runs
automatically create and validate a separate compact transfer folder.

Packing preserves parsed float64/complex128 values without quantization and
checks every array for exact numerical round-trip equality. It does NOT calculate
chi2, normalize wavefunctions, or track states on WORK. It preserves both printed
dispersion and per-k energies, plus k/spatial grids and state/component IDs.
Source text formatting is not preserved in the arrays; original solver text is
retained unchanged on WORK. No original files are automatically deleted.

## Size and disk budget

For 281 spatial samples, 601 k points, 24 states, eight complex components:

| Item | Estimate |
|---|---:|
| Essential envelope text on WORK | about 2.4–2.5 GB |
| Wavefunction binary payload before compression | 518,802,432 bytes |
| Entire transfer folder | target below 1 GB; measured and validated |

Actual size depends on the emitted grid and supporting records. No compression
ratio is promised. Exceeding the 1,000,000,000-byte transfer budget causes FAIL,
without deleting data or silently dropping states/k points. This is NOT a 1 GB
cap on nextnano's temporary text output. WORK needs space for raw text plus the
compact copy. Lean-run time and actual full-grid size are not benchmarked yet.

## Copy only this folder home

```text
nextnano/demos/28_kspace_chi2_study/nextnano/extended_8band_lean_work_results_transfer/
├── frames/k00000.npz ... k00600.npz
├── dispersion.npz
├── native_metadata/
├── decks/extended_8band.in
├── run_configuration.json
├── requested_k_grid.csv
├── run_metadata.json
├── solver.log
├── source_checksums.json
├── compact.json
├── checksums.json
└── return_validation.json
```

From the HOME repository root:

```powershell
python nextnano/demos/28_kspace_chi2_study/scripts/run_extended_8band.py --validate nextnano/demos/28_kspace_chi2_study/nextnano/extended_8band_lean_work_results_transfer
```

PASS / exit 0 checks every frame, precision, IDs, component ordering, grids,
energies/composition, source provenance, hashes and folder size. Validation is
read-only and uses the bundle's recorded configuration, not current defaults.
No extraction to envelope text is needed. Keep later analysis outside this folder.
Keep original WORK text until transfer and home analysis are verified.

Future HOME preparation, from the Demo28 directory:

```powershell
python scripts/prepare_returned_8band.py --input nextnano/extended_8band_lean_work_results_transfer
```

The raw-text path also still works. Degenerate-state and optical-operator review
remain required before interpreting the reduced Equation 2 response as consistent
8-band optical physics. Compact packaging does not resolve that mapping.

## If an old 1201-point run is already complete

No restart is needed merely to package it. From the repository root:

```powershell
python nextnano/demos/28_kspace_chi2_study/scripts/run_extended_8band.py --pack nextnano/demos/28_kspace_chi2_study/nextnano/extended_8band_work_results
```

This never launches nextnano. Destination: source name plus `_transfer`; `--output`
selects a different NEW folder. The packer uses the source's own config, validates
it and preserves all its samples. The 1201-point wavefunction payload is about
1.04 GB before compression/metadata: fitting its transfer under 1 GB is measured,
not guaranteed. Incomplete/inconsistent runs are rejected; originals stay intact.

## HOME checks

Both full and pilot decks pass the installed Free grammar parser. Tests cover
exact raw/packed equality, identical derived matrices, checksum corruption,
missing frames, size-budget refusal, pilot isolation and original preservation.
All are software fixtures, not new Professional physics results. See
`outputs/28K_extended_8band/LEAN_VALIDATION.md` for counts.
