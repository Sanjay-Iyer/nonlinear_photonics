# Demo 18D - solver-physics dual-objective reproduction

Demo 18D follows Demo 18B and Demo 18C without modifying either. It tests whether
actual Nextnano quantum-state changes can reproduce both the paper-scale amplitude
and the telecom spectral location.

The crucial correction from Demo 18C is that Combo 16 did not move the quantum
transitions. It reused the baseline states and changed only `hh_relative_weight`
from 1.0 to 0.6. The electron and HH spectra contain multiple resonant features;
changing their relative coefficient changes their cancellation differently at each
wavelength. The existing ~1663 nm feature then becomes the global maximum while the
~1520 nm feature remains as a shoulder. This is a dominant-peak swap, not a physical
red-shift of the solved spectrum.

## Immutable physics

Every primary result asserts:

- `hh_relative_weight = 1.0`
- `spin_degeneracy = 2`
- `wells_per_period_for_Nz = 2`
- `r_e_hh = 0.751 nm`
- Gamma = 5 meV
- two strictly bound electron and two strictly bound HH states
- abrupt interfaces
- the converged Demo 18B domain, padding, 0.025 nm mesh, matrix extraction, and Eq. 2

The three `r_e_hh` values 0.65, 0.751, and 1.00 nm are reported only as secondary
scale diagnostics. They never alter peak wavelength or the primary ranking.

## Frozen cases

The checked-in [demo18d_combinations.csv](demo18d_combinations.csv) contains exactly
20 unique solver-level states generated before physics with seed 1804:

- Case 00: Demo 18B baseline
- Cases 01-04: solver-physics anchors from Demo 18C Combos 07, 18, 01, and 02
- Cases 05-16: 12 local maximin Latin-hypercube points
- Cases 17-19: three predefined local refinements near the best unweighted 18C region

All 20 are rerun. No 18C solver output is reused as a primary 18D solve, avoiding an
unsupported cross-run provenance assumption. The completed 18C solver tree is read
first only to create `demo18d_reanalysis_of_18c.csv` with common unweighted
postprocessing.

## Dual objective

For every case:

```text
amplitude_relative_error = abs(chi2_1550 - 2340) / 2340
spectral_distance_nm = distance of dominant peak to [1520, 1560]
spectral_penalty = spectral_distance_nm / 40
combined_score = hypot(amplitude_relative_error, spectral_penalty)
```

The physical ranking prefers cases whose dominant peak lies inside 1520-1560 nm,
then minimizes the combined score. A separate in-window-only ranking is also saved.
Every full 1400-1800 nm spectrum is retained, including unweighted electron and HH
branches. The two strongest local maxima and the 1520-1560 to 1640-1680 peak ratio
are reported.

## Work-laptop commands

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"

python .\nextnano\demos\18D_solver_physics_dual_objective_reproduction\run_demo18d.py `
    --preflight `
    --n-cases 20 `
    --seed 1804 `
    --verbose

python .\nextnano\demos\18D_solver_physics_dual_objective_reproduction\run_demo18d.py `
    --physics `
    --n-cases 20 `
    --seed 1804 `
    --verbose
```

The default 18C source is:

```text
C:\nn_results\18C_paper_missing_parameter_ensemble\demo18c_20260814T000204Z_5a55a919_dd365f
```

Override it when necessary with `--demo18c-run "C:\path\to\completed\run"`.
The expected 18D result family is:

```text
C:\nn_results\18D_solver_physics_dual_objective_reproduction\demo18d_<run-id>\
```

## Outputs

- `demo18d_reanalysis_of_18c.csv`
- `demo18d_results.csv`
- `demo18d_ranked_results.csv`
- `demo18d_spectral_window_ranked_results.csv`
- `demo18d_master_summary.csv`
- full spectra for all 20 cases
- state, matrix-element, and localization tables
- 11 diagnostic plots, including best-state wavefunctions and band edges

## Success

Outcome A means no valid in-window case exceeds 500 pm/V. Outcomes B-E require an
in-window dominant peak and increasingly strong amplitude agreement; Outcome D is
within 20%, and Outcome E within 10%. An amplitude-only match at 1663 nm is never a
reproduction.

