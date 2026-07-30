# Demo 3 — quantum-well numerical convergence

## Learning objective

Quantify whether Demo 2's low-energy observables are stable with respect to
mesh spacing, outer-domain padding, quantum-region size, and requested state
count. The physical well and alloy remain unchanged; each run changes exactly
one numerical factor from the YAML baseline.

Enabled physics is identical to Demo 2. No new device physics is introduced.

## Run

```powershell
conda activate NMIP
python .\nextnano\demos\03_quantum_well_convergence\run.py
```

Every sweep point receives its own generated input and preserved output
directory. The parent run contains JSON/CSV summaries, a Markdown table,
failed/skipped/suspicious-run list, five requested plots, and a machine-readable
recommendation. Failed cases are never discarded.

Case directories use short `cases/grid`, `cases/domain`, `cases/qregion`, and
`cases/states` path components plus a short `case.in` input stem. This avoids
the Windows legacy 260-character path limit without abbreviating any scientific
labels in manifests or convergence tables.

Tracked observables include E1, E2, E2−E1, well and boundary probability, grid
points, runtime, solver success, validation status, and difference from the
finest successful grid reference.

The recommendation is the **coarsest** tested grid meeting absolute and
relative energy tolerances plus probability thresholds. The finest grid is a
reference calculation, not automatically the correct production choice.

Pass requires all sweep points to execute and parse successfully, stable
low-energy states under refinement/padding/state-count changes, negligible
boundary probability, justified tolerance compliance, and no hidden failed
runs. Abrupt spacing transitions should be reviewed even if energy tolerances
pass.

Before advancing, be able to explain: whether E1/E2 approach stable values,
when domain padding stops mattering, why boundary probability diagnoses finite
domain error, why requesting more states should not move low states, and why
runtime versus accuracy determines the practical production grid.
