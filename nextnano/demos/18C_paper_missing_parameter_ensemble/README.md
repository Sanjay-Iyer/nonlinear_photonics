# Demo 18C - paper missing-parameter ensemble

Demo 18C follows Demo 18B without changing Demo 18 or Demo 18B. It asks whether
20 predefined combinations of missing inputs, conventions, and explicitly labelled
diagnostic proxies can naturally move the complete two-electron/two-HH Eq. 2 result
from the converged Demo 18B value (84.91 pm/V) toward the paper's ideal abrupt-
interface value (2340 pm/V).

This is a bounded sensitivity experiment, not a fit. The complete complex Eq. 2
electron and HH branches are recalculated for each combination and combined as

```text
chi_diagnostic = chi_e_raw + hh_relative_weight * chi_hh_raw
```

The raw branches are always retained. No result may be interpreted as evidence that
the paper used a diagnostic electric field or HH weight.

The reported `cancellation_factor` uses the electron and weighted-HH branches that
form the diagnostic total. `raw_cancellation_factor` separately reports the
unweighted physical Eq. 2 branch cancellation.

## Frozen design

- Seed: `1803`
- Primary combinations: exactly `20`
- Unique licensed Nextnano++ solves: `17`
- Continuous design: best of 512 deterministic maximin Latin-hypercube candidates
- Combo 00: converged Demo 18B geometry/domain/mesh
- Combos 01-15: space-filling ensemble
- Combos 16/17: low/high HH-weight diagnostics reusing Solve 00
- Combo 18: bounded combined high-side case
- Combo 19: convention cross-check reusing Solve 00
- `Nz=2` and spin `=2`: each used in exactly 16/20 combinations

The checked-in [demo18c_combinations.csv](demo18c_combinations.csv) is generated
before physics and validated byte-for-value against the deterministic seed-1803
generator. The runner prints its SHA256 before the first solve. A failed combination
is retained; it is never replaced.

## What changes at solver level

New Nextnano++ states are required for:

- imposed growth-direction electric-field proxy;
- 7.0-7.2 nm thick-well rounding;
- 2.8-3.0 nm thin-well rounding;
- 1.7-1.9 nm tunneling-barrier rounding.

The period barrier is derived as `30 nm - well1 - barrier - well2`, so every case
remains a 30 nm period. The imposed field uses the repository-validated
`poisson{ electric_field{} }` potential tilt while `run{}` remains quantum-only and
the quantum region remains `no_density = yes`. `electric_field.dat` must reproduce
the requested signed field or that solver case fails its gate.

Electron/HH confinement-mass and CB/HH offset scales remain exactly 1.0. The current
validated abrupt-structure renderer does not expose transparent database overrides,
so varying them would violate the requirement not to patch solver output. The
requested and adopted ranges and this reason are explicit in
[demo18c_parameter_ranges.csv](demo18c_parameter_ranges.csv).

Post-processing-only quantities are:

- GaAs interband unit-cell matrix element `r_e_hh_nm`;
- diagnostic HH relative weight;
- wells-per-period `Nz` convention;
- spin convention;
- radial k-space cutoff (all cases use 768 k points).

## Fixed physics and gates

- abrupt interfaces;
- broadening Gamma = 5 meV;
- two bound electron and two bound HH states in Eq. 2;
- 1550 nm primary wavelength;
- 60 nm outer-domain padding, 42 nm quantum padding, 0.025 nm active mesh;
- strict Demo 18B bound-state criteria;
- orthonormality, full overlap matrix, electron/HH z matrices, and transition-energy
  reporting;
- solver return code, completion marker, expected quantum output, and imposed-field
  validation.

Failed or unbound cases remain in `demo18c_combo_results.csv` but are excluded from
`demo18c_ranked_results.csv`.

## Commands on the licensed work laptop

From the repository root in PowerShell:

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"

python .\nextnano\demos\18C_paper_missing_parameter_ensemble\run_demo18c.py `
    --preflight `
    --n-combos 20 `
    --seed 1803 `
    --verbose

python .\nextnano\demos\18C_paper_missing_parameter_ensemble\run_demo18c.py `
    --physics `
    --n-combos 20 `
    --seed 1803 `
    --verbose
```

`--preflight` deliberately does not import Matplotlib. `--physics` imports and
validates the plotting runtime before creating the run directory or starting any
licensed solve. If the active conda environment reports a `pyexpat` DLL error, test
it directly before physics:

```powershell
python -c "import pyexpat; import matplotlib.pyplot as plt; print('plotting OK')"
```

Repair or switch the active Python environment until that command succeeds; do not
start the 17-solve campaign with a broken plotting runtime.

The runner deliberately preloads Python's `pyexpat` extension before NumPy, YAML,
and the Nextnano support modules. On Windows this prevents a later scientific
dependency from selecting an incompatible expat DLL before Matplotlib imports
`plistlib`. If the direct command succeeds but an older runner still fails, update
the runner to the version containing this preload before starting physics.

The expected result family is:

```text
C:\nn_results\18C_paper_missing_parameter_ensemble\demo18c_<timestamp>_<git>_<id>\
```

To regenerate summaries from preserved solver outputs without rerunning the licensed
solver:

```powershell
python .\nextnano\demos\18C_paper_missing_parameter_ensemble\run_demo18c.py `
    --analyze-existing "C:\nn_results\18C_paper_missing_parameter_ensemble\<run-id>" `
    --n-combos 20 `
    --seed 1803 `
    --verbose
```

## Outputs

Inputs copied into each run's `config_snapshot`:

- `demo18c.yaml`
- `demo18c_parameter_ranges.csv`
- `demo18c_combinations.csv`
- machine configuration

Primary summaries:

- `demo18c_combo_results.csv`
- `demo18c_ranked_results.csv`
- `demo18c_master_summary.csv`
- `demo18c_parameter_importance.csv`
- `demo18c_best5_analysis.md`
- `demo18c_within20_comparisons.csv` when a valid case is within 20%
- `demo18c_summary.json`
- selected full branch-resolved spectra under `summaries/spectra/`
- nine requested plots under `plots/`

The parameter-importance correlations are exploratory only because the ensemble has
20 cases and deliberately includes coupled changes.

## Scientific success

- Outcome A: no valid case within 50% of 2340 pm/V.
- Outcome B: at least one valid case within a factor of two (1170-3510 pm/V).
- Outcome C: at least one valid case within 20% (1872-2808 pm/V).
- Outcome D: at least one valid case within 10% (2106-2574 pm/V).

A scientifically meaningful success is a physically valid Outcome B, C, or D case
whose bound states, orthonormality, transition energies, and near-IR spectrum remain
credible. Even Outcome D shows reachability inside the tested envelope; it does not
prove the authors' unpublished parameters.
