# Demo 4 — symmetric double quantum well and tunnelling

## Learning objective

Two identical wells that are close enough to share their electrons no longer
have two independent ground states. The single-well level splits into a
**symmetric** and an **antisymmetric** combination, and the size of that
splitting is a direct measurement of how strongly the wells are coupled through
the barrier between them.

This demo measures the splitting, the parity of each state, and where the
probability actually sits — and then checks whether any of it depends on the
size of the simulation box rather than on the physics.

## Physical structure

```
AlGaAs outer barrier | GaAs well | AlGaAs centre barrier | GaAs well | AlGaAs outer barrier
     20 nm           |   6 nm    |      4 nm (swept)     |   6 nm    |        20 nm
```

Both GaAs wells are identical. Any asymmetry in the result is therefore either a
numerical artifact or a genuine consequence of near-degeneracy — never a
property of the structure.

## Enabled physics

- 1D simulation, 300 K
- classical Γ / HH / LH / SO band edges
- one-band Γ-electron Schrödinger equation, several states
- Dirichlet quantum-region boundaries

## Disabled physics

Doping, Poisson, self-consistency, strain, polarization, 6-band and 8-band k·p,
transport, and optical spectra. The zero-bias `fermi` contact is the mandatory
electrostatic reference required by every nextnano++ deck; it enables none of
those calculations.

## Parameters

| physical (`scientific`) | meaning |
|---|---|
| `well_width_nm` | width of each identical GaAs well |
| `center_barrier_nm` | AlGaAs barrier separating them — the coupling knob |
| `left_outer_barrier_nm`, `right_outer_barrier_nm` | confining barriers at the ends |
| `aluminum_fraction` | Al mole fraction, sets the barrier height |
| `temperature_K` | lattice temperature |

| numerical (`numerical`) | meaning |
|---|---|
| `active_region_grid_spacing_nm` | mesh inside the wells and centre barrier |
| `exterior_grid_spacing_nm` | mesh in the outer barriers |
| `number_of_states` | eigenstates requested from the solver |
| `quantum_region_padding_nm` | how far the quantum region extends past the wells |

Changing a `scientific` value changes the device. Changing a `numerical` value
must not change the answer — which is exactly what the padding sweep tests.

## Sweeps

- `center_barrier_nm`: 1, 2, 3, 4, 5, 7.5, 10, 15, 20 nm — the physics sweep.
- `quantum_region_padding_nm`: 10, 20 nm — the numerical control.

## Expected qualitative behaviour

- **Thin centre barrier**: strong tunnelling. The lowest two states are a
  clearly split symmetric/antisymmetric pair, both spread over both wells, with
  visible amplitude *inside* the centre barrier.
- **Thick centre barrier**: tunnelling is exponentially suppressed. E2 − E1
  collapses towards zero and the two wells behave as effectively isolated.
- E2 − E1 should fall roughly exponentially with barrier thickness, so the
  splitting plot uses a logarithmic axis.

## Run

```bash
python nextnano/demos/04_symmetric_double_quantum_well/run.py
```

No flags. Everything scientific lives in `demo.yaml`.

## Expected outputs

Per case, under `runs/<case_id>/`: `generated_input/`, `raw_output/`,
`extracted/states.csv`, `extracted/band_profile.csv`,
`extracted/envelopes.csv`, `extracted/probability_densities.csv`,
`extracted/envelope_matrices.json`, `plots/`,
`console.log`, `demo_resolved.yaml`, `machine_summary.json`, `run_manifest.json`.

At the parent run level: `sweep_manifest.json`, `run_manifest.json`,
`validation_report.md`, `extracted/sweep_summary.{csv,json}`,
`extracted/failed_runs.csv`, `extracted/suspicious_runs.csv`,
`extracted/state_tracking.csv`, `tables/splitting_table.csv`,
`console_logs/`, and `plots/`.

## Plots

| file | shows |
|---|---|
| `band_diagram.png` | conduction-band profile with horizontal eigenenergies |
| `wavefunctions.png` | **signed envelope amplitudes** ψ(z), nm^(−1/2) |
| `probability_densities.png` | **normalised** \|ψ\|², nm^(−1) |
| `band_edge_with_display_offsets.png` | \|ψ\|² drawn on each eigenenergy — the vertical offset is a **display choice**, stated on the figure |
| `energies_vs_center_barrier.png` | E1, E2, E3 versus barrier thickness |
| `splitting_vs_center_barrier.png` | E2 − E1 versus barrier thickness (log axis) |
| `localization_vs_center_barrier.png` | per-well and centre-barrier probability |
| `thin_vs_thick_barrier_wavefunctions.png` | thin/thick comparison |
| `padding_check.png` | E1 and E2 versus quantum-region padding |
| `state_tracking_confidence.png` | tracking confidence at each sweep step |

Amplitude, probability density, and energy are kept in separate figures with
separate units. Only the last band figure combines them, and it says so.

## Validation criteria

1. Every sweep point produced a generated input; none was discarded.
2. Energies are finite and strictly ordered.
3. Probability densities integrate to 1 within `normalization_tolerance`.
4. At least two states pass the **physical** bound test — energy below the
   enclosing conduction-band maximum *and* enough probability in the wells.
   A state is never called bound because of its index.
5. The lowest two states are balanced between the identical wells,
   `|P_left − P_right| ≤ well_balance_tolerance`.
6. The lowest two states have definite parity about the centre-barrier midpoint,
   symmetric first and antisymmetric second, at or above
   `minimum_parity_confidence`.
7. E2 − E1 decreases as the centre barrier thickens (5 % noise allowance).
8. Bound-state probability near the domain edges stays below
   `maximum_boundary_probability`. States *above* the barrier are excluded from
   this test — they legitimately reach the Dirichlet walls.
9. E1 and E2 are stable when the quantum-region padding is doubled.
10. State tracking is confident at every step.

## Common failures

- **Splitting does not decrease.** Usually the grid is too coarse to resolve a
  thin barrier, or `number_of_states` is small enough that a higher subband pair
  is being read as the lowest pair.
- **Parity confidence low.** The structure is not actually symmetric (check the
  two outer barriers) or the grid does not sample the centre symmetrically.
- **Boundary probability high.** The outer barriers or the quantum-region
  padding are too small; the Dirichlet wall is doing the confining.
- **Near-degenerate pair localises in one well.** Genuine physics for a thick
  barrier: any superposition of two degenerate states is also a solution, so the
  solver may return localised combinations. Diagnose with the splitting, not
  with the shapes.
- **A path-length error on Windows.** Case directory names are abbreviated for
  exactly this reason; if it still happens, move the repository closer to the
  drive root or set `results_root`.

## Advancement criteria

Before Demo 5, be able to answer:

- Why are the two lowest states split at all?
- What distinguishes the symmetric from the antisymmetric state, and why does
  the antisymmetric one lie higher?
- Why does a thicker barrier reduce the splitting, and roughly how fast?
- When is it legitimate to treat the two wells as isolated?
- How could a Dirichlet boundary imitate real confinement, and which diagnostic
  in this demo would catch that?

## Licensed-validation status

`physically_validated` — see `nextnano/demos/demo_registry.yaml`.

- **Home, syntax:** every generated deck of the full sweep parses cleanly under
  the Free nextnano++ 3.0.0 `--parse` runmode.
- **Home, execution:** a reduced-grid version of this deck (1 nm mesh, 4 states)
  was *executed* by the Free edition and its real output is committed under
  `nextnano/tests/fixtures/nextnano_pp_3_0_0/demo04_symmetric_dqw/`. The parser
  and every analysis above run against it in the test suite.
- **Licensed result:** all 11 cases completed. E2 − E1 decreased monotonically
  from 35.2928 meV at 1 nm to 6.1312e-5 meV at 20 nm; the lowest pair retained
  the expected parity and left/right balance. Doubling the quantum-region
  padding moved E1 and E2 by less than 5e-5 meV.
- A third shallow bound state at the 1 and 2 nm barriers has slightly elevated
  boundary weight. It remains visible as a diagnostic but is not part of the
  lowest tunnelling pair validated by this demo.

The Free-edition fixture is a plumbing check, not physics: 100 grid points and
a 1 nm mesh are far from converged.

## Work-laptop checklist

```bash
git pull
conda activate llm
python nextnano/demos/04_symmetric_double_quantum_well/run.py
```

- [ ] `sweep_manifest.json` reports `status: completed` and 11 cases.
- [ ] `extracted/failed_runs.csv` contains only `none`.
- [ ] `validation_report.md` shows PASS, not "not evaluated", for every criterion.
- [ ] `tables/splitting_table.csv` shows E2 − E1 falling from the 1 nm to the
      20 nm barrier.
- [ ] `parity_state1 = symmetric` and `parity_state2 = antisymmetric` at every
      thickness where the pair is still resolvably split.
- [ ] Both E1 and E2 change by less than `absolute_energy_tolerance_meV`
      between the two padding cases.
- [ ] The parent plot set contains real representative band, envelope, and
      probability-density plots in addition to the sweep plots.
