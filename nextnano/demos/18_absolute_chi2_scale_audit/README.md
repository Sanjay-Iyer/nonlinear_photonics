# Demo 18 - absolute chi(2) scale audit

Demo 18 asks why the existing absolute interband susceptibility calculation is
far below the paper's thousands-of-pm/V scale. It does not optimize or redesign
the quantum wells. One licensed nextnano++ solve supplies one set of energies
and envelopes; every scale variant is then evaluated in Python from those same
states.

## Fixed structure

The only solver structure is an abrupt GaAs/Al0.55Ga0.45As ACQW:

```text
7.1 nm GaAs / 1.8 nm AlGaAs / 2.9 nm GaAs
18.2 nm period barrier; 30.0 nm nominal period
```

The deck and solver path are reused from Demo 16E/16B and Demo 14. nextnano++
calculates Gamma-electron and heavy-hole energies, envelopes and probabilities.
Python normalizes the envelopes, constructs electron-hole overlaps and electron
and heavy-hole position matrices, evaluates the two-state Eq. 2 sum, integrates
over in-plane k, and applies the absolute conversion to pm/V.

## Six audits

1. `N_z`: `pair_per_period = 1/(30 nm)` versus
   `two_wells_per_period = 2/(30 nm)`.
2. k cutoff: `legacy_pi_over_a = 0.1*pi/a` versus
   `bz_2pi_over_a = 0.1*2*pi/a`.
3. Larger-cutoff radial-grid convergence at 96, 192 and 384 points.
4. Spin degeneracy recorded and evaluated separately at 1 and 2.
5. Production absolute prefactor checked against an independent SI
   reconstruction with explicit nm, inverse-nm, eV and pm conversions.
6. The documented `r_e_hh = 0.751 nm` value exposed in configuration and tested
   at 0.90x, 1.00x and 1.10x, with expected 0.81x, 1.00x and 1.21x scaling.

No convention is silently promoted, and Demo 11/14/16E defaults are unchanged.

## Home-laptop preflight

Preflight needs no solver executable or license. From the repository root:

```powershell
python .\nextnano\demos\18_absolute_chi2_scale_audit\run_demo18.py --preflight
```

It checks imports, YAML, the fixed case, abrupt deck rendering, the case matrix,
the independent prefactor, expected `N_z`/spin/`r^2` scaling, all three k grids,
the output-path rule and CLI parsing using a small synthetic state fixture.

## Licensed work-laptop run

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"
python .\nextnano\demos\18_absolute_chi2_scale_audit\run_demo18.py --physics --verbose
```

Exactly one licensed nextnano++ solve is performed. Its output is reused for all
eight convention rows and the separate `r_e_hh` sensitivity calculation.

Results are written below the configured machine `results_root`, normally:

```text
C:\nn_results\18_absolute_chi2_scale_audit\demo18_<timestamp>_<sha>_<id>\
```

Important artifacts are:

```text
demo18_debug.log
resolved_demo18_config.yaml
inputs/reference_abrupt.in
solver/                         raw nextnano++ tree
logs/                           preserved stdout/stderr copies
summaries/demo18_master_summary.csv
summaries/demo18_summary.json
summaries/solver_quantities.json
summaries/kgrid_convergence.csv
summaries/r_ehh_sensitivity.csv
summaries/spectra/*.csv
plots/*.png
```

On any exception, the full Python traceback is appended to
`demo18_debug.log`. A solver failure preserves the generated input, return-code
record, stdout, stderr, raw result directory and output inventory; failed runs
are never cleaned up. Inspect or share that one debug log first.

