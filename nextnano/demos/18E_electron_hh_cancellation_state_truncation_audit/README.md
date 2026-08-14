# Demo 18E - electron/HH cancellation and state-truncation audit

Demo 18E follows Demos 18B-18D without modifying them. It audits why the two
large pathways in the paper's reduced susceptibility expression nearly cancel.
It is not a geometry search and does not fit an HH weight.

## Scientific scope

The primary source is the provenance-gated archived Demo 18D `Case_19` solve:

```text
C:\nn_results\18D_solver_physics_dual_objective_reproduction\
  demo18d_20260814T010423Z_66dca051_ce7cd6\solver\Case_19
```

That solve already requested six electron and six HH states. The exported state
gate identifies E1-E3 and HH1-HH6 as bound, so the 2e/2hh, 2e/3hh, 3e/2hh, and
3e/3hh audits need **zero new licensed solves**.

Primary physics remains fixed at Gamma = 5 meV, spin = 2, Nz = 2/30 nm,
`r_e_hh = 0.751 nm`, and `hh_relative_weight = 1.0`.

The 2023 paper labels the reduced expression Eq. (3); earlier repository demos
refer to it as Eq. 2. Artifact filenames keep the repository's `eq2` convention.

## Rotation protocol

HH2 and HH3 differ by 1.367506377 meV and therefore are not exactly degenerate.
Arbitrary rotations of nondegenerate eigenvectors are not new eigenvectors; using
rotated diagonal energies while discarding the off-diagonal Hamiltonian would be
an inconsistent test. Demo 18E therefore separates two questions:

- substitution/state-count audits use the actual, nondegenerate eigenstates and
  actual energies;
- the continuous rotation audit replaces HH2/HH3 by their mean energy **only in
  an explicitly labelled exact-degenerate control**. It transforms overlaps and
  both position matrices with the same unitary. The complete subspace must then
  be invariant, while `HH1 + HH_a(theta)` intentionally exposes truncation
  dependence.

The generalized implementation uses the complex bra/ket products explicitly:
`conj(O[n,m]) z_e[n,l] O[l,m]` for the electron pathway and
`O[n,m] z_hh[m,l] conj(O[n,l])` for the HH pathway. This is mandatory for the
random complex-phase control.

## Work-laptop commands

Preflight never invokes nextnano++:

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"

python .\nextnano\demos\18E_electron_hh_cancellation_state_truncation_audit\run_demo18e.py `
    --preflight `
    --verbose
```

The requested archived-physics analysis also launches no solver; it reads the
completed Demo 18D and Demo 18B trees and writes a unique run below
`C:\nn_results\18E_electron_hh_cancellation_state_truncation_audit\`:

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"

python .\nextnano\demos\18E_electron_hh_cancellation_state_truncation_audit\run_demo18e.py `
    --physics `
    --verbose
```

Paths can be overridden with `--demo18d-run`, `--demo18b-run`, and
`--output-root`. `--analyze-handoff` is a local diagnostic for the exported CSV
matrices in `demo_results/demo18d`; it is never described as a licensed rerun and
cannot draw the raw HH2/HH3 wavefunctions.

## Outputs

- `demo18e_state_identity.csv`
- `demo18e_state_selection_audit.csv`
- `demo18e_rotation_invariance.csv`
- `demo18e_state_count_convergence.csv`
- `demo18e_eq2_term_table.csv`
- `demo18e_cancellation_pairs.csv`
- `demo18e_sign_convention_audit.csv`
- `demo18e_multiplicity_audit.csv`
- `demo18e_phase_invariance.csv`
- `demo18e_permutation_invariance.csv`
- `demo18e_valence_model_audit.json`
- `demo18e_missing_paper_inputs.md`
- full selected spectra, ten requested figures, `demo18e_summary.json`, and
  `demo18e_debug.log`

The phase and permutation controls are hard gates. Any failure stops the audit
before HH2/HH3 rotation results are interpreted.

## Multiband boundary

The current solve is a one-band effective-mass Gamma/HH calculation. The
repository and work installation support 6-band and 8-band k.p calculations, but
the paper does not specify its exact valence model. Its reduced Eq. (3) separates
a scalar HH envelope from a fixed Bloch `r_e_hh`; a multiband spinor has
component-resolved HH/LH/SO content and optical matrix elements. Demo 18E records
that support but does not force a multiband spinor through the scalar one-band
formula without a published projection derivation. A future controlled
energy/composition comparison would require one optional licensed solve and a
separate theoretical mapping; it is not required for the primary state audit.

