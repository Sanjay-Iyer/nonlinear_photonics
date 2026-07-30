# Demo 10 — first 2D quantum-confinement model

## Learning objective

A quantum well confines electrons in one direction and leaves two free. Etch it
into a narrow ridge and a second direction becomes confined: each 1D subband
splits into a ladder of wire subbands, and the answer now depends on a mesh in
**two** directions at once.

Most of what can go wrong here is numerical, so the physics is kept minimal —
one-band Γ effective mass, no strain, no polarization, no excitons, four
states — and the effort goes into mesh, domain, symmetry, and alignment tests.

## Physical structure

A rectangular **GaAs core** inside an **AlGaAs matrix**:

```
        y
        ↑        AlGaAs matrix
        │   ┌───────────────────┐
        │   │  ┌─────────────┐  │
        │   │  │  GaAs core  │  │  height = wire_height_nm  (8 nm)
        │   │  └─────────────┘  │  width  = wire_width_nm  (20 nm)
        │   └───────────────────┘
        └──────────────────────────→ x
```

The **third direction is assumed translationally invariant**: this is an
infinitely long wire, free-electron-like along its axis. The 2D eigenvalues are
the subband *edges* of that dispersion, not total energies.

The vertical dimension plays the role of a quantum well (compare Demo 2); the
lateral one is the new confinement.

## Syntax provenance

The 2D-specific constructs — `simulate2D{}`, `ygrid{}`, `rectangle{}`, and a
quantum region carrying both `x` and `y` with
`boundary{ x = dirichlet  y = dirichlet }` — come from this repository's
validated `hello_03a_gaas_rectangle_2d.in`. The only change is the material map:
`hello_03a` was homogeneous GaAs confined purely by the Dirichlet box, while
this demo has a real heterostructure barrier.

At home the Free edition parses the deck and, under `--structure`, builds the
real 2D grid (63 × 51 = 3213 points for the baseline) before stopping with
`This version of nextnano++ does not allow running 2D simulations` — the
expected 1D-only gate, not a syntax problem.

## Parameters

Physical: `wire_width_nm`, `wire_height_nm`, `lateral_barrier_nm`,
`vertical_barrier_nm`, `aluminum_fraction`, `temperature_K`.

Numerical: `grid_spacing_x_nm`, `grid_spacing_y_nm`,
`exterior_grid_spacing_nm`, `number_of_states`, `domain_padding_x_nm`,
`domain_padding_y_nm`, `geometry_offset_x_nm`, `geometry_offset_y_nm`.

## Required tests — all of them run

| test | how |
|---|---|
| 1. coarse vs fine mesh | `grid_spacing_x_nm`, `grid_spacing_y_nm` sweeps |
| 2. isotropic vs anisotropic mesh | `analysis.anisotropy_cases`: (1,1), (2,0.5), (0.5,2) |
| 3. larger x padding | `domain_padding_x_nm` sweep |
| 4. larger y padding | `domain_padding_y_nm` sweep |
| 5. geometry shifted relative to the mesh | `analysis.alignment_offsets_nm`: 0.25, 0.5 nm |
| 6. width sweep | `wire_width_nm`: 10–40 nm |
| 7. 1D limit | `analysis.wide_limit_width_nm` = 80 nm |

Mesh anisotropy is computed and reported for **every** case, isotropic ones
included, so a silently anisotropic mesh cannot hide.

## Expected outputs

Per 2D case: `extracted/energies.csv`,
`probability_density_state_1.csv`, `probability_density_state_2.csv`,
`material_map.csv`, `conduction_band_map.csv`, `horizontal_slice.csv`,
`vertical_slice.csv`, `grid.json`, plots, log, manifest. Parent:
`sweep_manifest.json`, `validation_report.md`, `tables/mesh_tests.csv`,
`tables/one_d_limit_comparison.csv`, `extracted/sweep_summary.*`,
`failed_runs.csv`, `suspicious_runs.csv`, `plots/`.

## Plots

`material_map.png`, `conduction_band_map.png`, `ground_state_density.png`,
`first_excited_density.png`, `horizontal_slice.png`, `vertical_slice.png`,
`energy_vs_width.png`, `mesh_convergence.png`, `domain_convergence.png`,
`symmetry_error.png`, `mesh_anisotropy.png`, `one_d_limit.png`.

## Validation criteria

1. Every requested test produced a generated input; nothing was discarded.
2. **A symmetric geometry gives a symmetric ground state.** Reflection
   asymmetry `max|f − Pf| / max|f|` must stay below `maximum_symmetry_error`
   about both axes. The test is skipped — and says so — for the deliberately
   shifted alignment cases.
3. **Sub-cell translation does not move the energy.** Shifting the geometry by
   0.25 or 0.5 nm relative to the mesh must not shift E1 by more than
   `absolute_energy_tolerance_meV`.
4. Boundary probability inside a 5 % frame is negligible.
5. Probability densities integrate to 1 over the cross-section.
6. Energies are finite and ordered.
7. Finest-pair x/y mesh and largest-pair x/y domain tests meet the configured
   energy tolerance.
8. The wide 2D wire approaches a separately solved 1D finite well with the
   same 8 nm vertical confinement.

## Cost control

2D is expensive because the mesh cost is the *product* of two directions and the
eigenproblem grows with it. `render_values` refuses any configuration implying
more than 250 000 grid points rather than letting a typo run for hours.

## Common failures

- **Asymmetric ground state in a symmetric wire.** The mesh is not symmetric
  about the structure centre. `analysis.symmetry_error` refuses to report a
  number when the grid itself is not centred, so the mesh gets blamed rather
  than the physics.
- **Energy jumps with a 0.25 nm shift.** The mesh is too coarse to resolve the
  interface; refine before believing anything else.
- **2D output not found.** No 2D run has ever executed here — the field-output
  names are unconfirmed. The run fails with a listing of what was written.
- **Field reshape fails.** The storage order (row-major in x or in y) is an
  explicit, recorded assumption. `read_2d_field` prefers self-describing
  x/y/value triples and only falls back to a flat reshape whose assumption is
  written into `grid.json` and the manifest.

## Advancement criteria

- Why is a 2D model needed at all — what does it capture that Demo 2 cannot?
- Which physical direction is assumed invariant, and what does that make the
  eigenvalues *mean*?
- How can a numerical mesh break a symmetry the structure does not have?
- When is a 1D model still sufficient? (Inspect the separately solved 1D
  reference in `one_d_limit.png` and `tables/one_d_limit_comparison.csv`.)
- Why is 2D so much more expensive than 1D?

## Licensed-validation status

`licensed_run_pending`, with **unvalidated output syntax** — see
`nextnano/demos/demo_registry.yaml`.

- **Home, syntax:** the 24 2D decks plus one 1D reference deck generate
  deterministically; the 2D syntax parses cleanly under `--parse`, and
  `--structure` builds the real 2D grid before the expected 1D-only gate.
- **Home, execution: impossible.** The Free edition is 1D only. There is **no
  real-output fixture for this demo**; the 2D analysis functions
  (`normalise_density_2d`, `centroid_2d`, `boundary_probability_2d`,
  `symmetry_error`, `slice_2d`) are unit-tested against synthetic arrays
  instead, which validates the logic but not the file format.
- **Unconfirmed:** the 2D field-output file names, `grid_y.dat`, and the field
  storage order.

Do **not** proceed to 3D in this task.

## Work-laptop checklist

```bash
git pull
conda activate llm
python nextnano/demos/10_first_2d_quantum_confinement/run.py
```

- [ ] Record the exact 2D output file names and layout; reconcile the parser
      profile and the storage-order assumption in `grid.json`.
- [ ] `symmetry_error.png`: the centred cases sit at the noise floor.
- [ ] Alignment cases shift E1 by less than `absolute_energy_tolerance_meV`.
- [ ] `mesh_convergence.png` and `domain_convergence.png` both flatten.
- [ ] `mesh_anisotropy.png`: E1 does not depend on the anisotropy ratio at fixed
      resolution — if it does, report it, that is the finding.
- [ ] `one_d_limit.png` and `tables/one_d_limit_comparison.csv`: the 80 nm
      wire's E1 approaches the separately solved 1D finite-well result.
- [ ] The parent `material_map.png`, `conduction_band_map.png`, ground-state,
      and first-excited-state maps contain real solver data.
- [ ] Watch the runtime and grid-point count in `tables/mesh_tests.csv` before
      refining further.
