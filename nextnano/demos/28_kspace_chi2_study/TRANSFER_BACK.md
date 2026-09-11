# Current lean run: copy one compact directory home

For the updated 601-point run, copy ONLY:

```text
nextnano/demos/28_kspace_chi2_study/nextnano/extended_8band_lean_work_results_transfer/
```

The runner automatically creates this lossless numerical bundle after a successful
lean run. It includes all complex CB/HH/LH/SO envelopes, energies, composition,
grids/state IDs, exact deck/config/log, provenance and checksums. The whole folder
is checked against a 1 GB budget. Original text remains on WORK and is not deleted.

From the HOME repository root:

```powershell
python nextnano/demos/28_kspace_chi2_study/scripts/run_extended_8band.py --validate nextnano/demos/28_kspace_chi2_study/nextnano/extended_8band_lean_work_results_transfer
```

Use [LEAN_8BAND_RUN.md](LEAN_8BAND_RUN.md) for pilot/full-run commands, the compact
layout, size caveats, direct HOME ingestion and packing an already-completed run.
No chi2 calculation or plots need to run on WORK. Compact storage preserves the
parsed numbers exactly, not original text formatting. Keep the original WORK text
until transfer and HOME analysis have been verified.

## Historical uncompressed transfer instructions

The instructions below apply only to an original raw-text bundle, NOT the current
compact default. They are retained for already-existing runs.

After the new WORK-laptop command finishes, copy this entire directory, preserving
all nested paths, into the same location in the home repository:

```text
nextnano/demos/28_kspace_chi2_study/nextnano/extended_8band_work_results/
├── raw/                         all untouched nextnano outputs
├── decks/extended_8band.in       exact executed deck
├── run_configuration.json
├── requested_k_grid.csv
├── run_metadata.json            command, executable/database hashes, times/status
├── solver.log                   combined stdout/stderr, version/header if emitted
├── checksums.json
└── return_validation.json       work-side result
```

The solver's native simulation metadata stays under `raw/`. The executable and
licensed database are identified by hash, not bundled; license contents are not
copied. No processed Python plots are needed. If you supplied `--output`, copy
that alternative complete folder instead. Do not merge it into an old raw folder.

From the HOME repository root, with the project Python environment active:

```powershell
python nextnano/demos/28_kspace_chi2_study/scripts/run_extended_8band.py --validate nextnano/demos/28_kspace_chi2_study/nextnano/extended_8band_work_results
```

PASS / exit 0 means the grid, energies, component-file coverage, exact deck/config
and complete checksum manifest pass. FAIL / exit 2 reports missing/corrupt or
inconsistent data. This command is read-only and never starts nextnano.
Do not edit files inside the transfer bundle; keep subsequent Python outputs
outside it. Retain a failed run too: naming/layout differences may be repairable
in the reader without rerunning the solver. Never manufacture absent finite-k data.

Next: use `WORK_LAPTOP_8BAND_RUN.md` for the 28L input-preparation command.
Optical operator and branch/spin mapping review precedes 28M χ² evaluation.
