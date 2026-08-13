# Demo 18B - absolute chi2 reproduction audit

Demo 18B follows Demo 18 without changing it. It is a controlled numerical,
state-selection, matrix-extraction, and Eq. 2 reproduction audit of the fixed
abrupt 7.1/1.8/2.9 nm GaAs/Al0.55Ga0.45As coupled quantum well. It performs no
geometry or material optimization and applies no empirical scale factor.

## What is held fixed

- 7.1 nm and 2.9 nm GaAs wells, separated by 1.8 nm AlGaAs
- 18.2 nm physical period barrier and 30.0 nm nominal period
- abrupt interfaces and Al fraction 0.55
- Gamma electrons and heavy holes, six requested states per band
- the paper's primary two-bound-state Eq. 2 model
- Gamma = 5 meV
- primary Nz = two wells per 30 nm period
- primary kmax = 0.10(2pi/a), 384 radial points, spin factor 2
- repository assumption r_e,hh = 0.751 nm, clearly distinguished from the
  unpublished numerical HSE06 value in the 2026 paper

Only numerical domain padding and mesh spacing change during licensed solves.
The six unique decks are four domains at 0.05 nm and two additional meshes on
the largest domain. The largest-domain 0.05 nm solve is reused in both ladders.

## Audits

The workflow freezes the exact Demo 18 reference; strictly classifies every
participating state; measures domain, mesh, k-cutoff and state-count convergence;
compares Python overlaps and off-diagonal position matrices with nextnano's own
tables; tests origin invariance; writes every Eq. 2 triple-sum term; separates
electron and HH paths; diagnoses diagonal matrix elements and state identity;
records every degeneracy; and cross-checks the production calculation against a
from-scratch Eq. 2 implementation and independent SI prefactor.

The paper says the envelopes came from Schrödinger-Poisson calculations, but it
does not publish a doping profile, carrier density/quasi-Fermi level,
electrostatic boundary conditions, or fixed/interface charge. The current deck
contains `no_density = yes`. Demo 18B records that mismatch and does not invent
a nontrivial Poisson configuration. An undoped zero-charge Poisson calculation
would be physically equivalent to the present flat electrostatic solution and
would not reproduce the unknown paper setup.

## Home-laptop preflight

```powershell
python .\nextnano\demos\18B_absolute_chi2_reproduction_audit\run_demo18b.py --preflight
python -m pytest .\nextnano\tests\test_demo18b_absolute_chi2_reproduction_audit.py -q
```

Preflight renders every deck and checks analytic/nonuniform-grid matrix
integrals, nextnano fixture matrices and units, origin invariance, independent
Eq. 2 agreement, configuration, CLI, and case-insensitive CSV headers. It does
not create synthetic physics conclusions.

## Licensed run

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"
python .\nextnano\demos\18B_absolute_chi2_reproduction_audit\run_demo18b.py --physics --verbose
```

Results are written beneath the configured machine root:

```text
C:\nn_results\18B_absolute_chi2_reproduction_audit\demo18b_<timestamp>_<sha>_<id>\
```

The workflow preserves each generated deck, raw nextnano tree, stdout/stderr,
resolved config, debug log, spectra, fourteen figures, and these tables:

```text
summaries/state_audit.csv
summaries/matrix_elements.csv
summaries/state_localization.csv
summaries/domain_convergence.csv
summaries/mesh_convergence.csv
summaries/eq2_terms.csv
summaries/convention_audit.csv
summaries/native_matrix_comparison.csv
summaries/state_count_convergence.csv
summaries/origin_invariance.csv
summaries/k_saturation.csv
summaries/degeneracy_ledger.csv
summaries/demo18b_master_summary.csv
summaries/demo18b_summary.json
```

All CSV headers are unique under case-insensitive comparison, so PowerShell
`Import-Csv` works. Rebuild analysis without rerunning the solver using:

```powershell
python .\nextnano\demos\18B_absolute_chi2_reproduction_audit\run_demo18b.py `
  --analyze-existing C:\nn_results\18B_absolute_chi2_reproduction_audit\demo18b_...
```

Inspect the master table with:

```powershell
Import-Csv .\summaries\demo18b_master_summary.csv | Format-Table `
  case_id,mesh_nm,quantum_padding_nm,chi2_1550_pm_per_V,peak_wavelength_nm,strict_selected_states_bound_pass
```

## What counts as success

Technical success does not require reaching 2340 pm/V. It means all six solves
completed, the exact reference reproduced Demo 18, state/domain/mesh verdicts
were written, native matrices and the independent Eq. 2 implementation were
compared, and the discrepancy was classified A-E with evidence. A still-low,
converged, independently validated result is a valid and important outcome.
