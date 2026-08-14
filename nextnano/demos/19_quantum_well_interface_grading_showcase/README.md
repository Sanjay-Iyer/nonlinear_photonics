# Demo 19 — Quantum-Well Interface Grading Showcase

Demo 19 compares thirteen deterministic interface-grading definitions on one
fixed GaAs/Al0.55Ga0.45As asymmetric coupled quantum well. The physical stack is
7.1 nm GaAs / 1.8 nm AlGaAs / 2.9 nm GaAs with the established 18.2 nm total
period barrier. Only interface grading changes.

The permanent interface names are:

- I1: outer barrier → thick GaAs well
- I2: thick GaAs well → tunnel AlGaAs barrier
- I3: tunnel AlGaAs barrier → thin GaAs well
- I4: thin GaAs well → outer barrier

Every nonzero width is a full start-to-end composition transition centered on
the corresponding nominal abrupt interface. Nominal interface positions and the
30.0 nm total period remain fixed.

## Rendering

- Abrupt: native binary/constant material regions.
- Linear: native Nextnano++ `ternary_linear{}` regions, one per graded interface.
- Fermi-like, erf and cosine: Python generates `x_Al(z)` and the validated Demo 14
  importer supplies a DAT table through `ternary_import{}`. “Fermi-like” is a
  mathematical logistic profile, not a claimed native Nextnano++ keyword.
- `ternary_pyramid` is prohibited and checked by preflight.

## Commands

Solver-free preflight (safe on any machine):

```powershell
python .\nextnano\demos\19_quantum_well_interface_grading_showcase\run_demo19.py --verbose
```

Licensed work-laptop physics (exactly 13 independent solves):

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"
python .\nextnano\demos\19_quantum_well_interface_grading_showcase\run_demo19.py --physics --verbose
```

The physics command refuses to start unless all thirteen composition/deck gates
pass and the configured executable, database, and license files exist. It never
falls back to mock or synthetic physics.

## Outputs

The source directory contains the pre-run case table, implementation audit,
solver-free realized-profile validation, generated input examples, pending result
schemas, and a concise boss summary. `preflight_output/` contains all thirteen
rendered decks, imported profile files where applicable, and the two input plots.

A licensed run is written under:

`C:\nn_results\19_quantum_well_interface_grading_showcase\demo19_<timestamp>_<git>_<id>\`

It contains every solver input/output, per-case validation data, the master and
presentation tables, plots 01–10, and the populated boss summary. Failed cases
remain present with their failure stage and reason.

Absolute χ² uses one fixed inherited convention for every case. Demo 19's claim
is the controlled change relative to the abrupt reference, not absolute
experimental or paper agreement.
