# Demo 6 — doped coupled well with self-consistent Schrödinger–Poisson

## Learning objective

Up to Demo 5 the potential was given and the electrons were computed in it. Add
donors and that stops being possible: the electrons move, their charge changes
the electrostatic potential, and the changed potential moves them again. The
Schrödinger and Poisson equations have to be solved **together**, iteratively,
until neither changes.

The second, harder lesson is that **a solver can finish successfully without
converging**. `run{ quantum_poisson{} }` exits with `DONE.` and writes
`job_done.txt` even when it has given up. This demo reads completion from one
place and convergence from another, and never lets the first imply the second.

## Physical structure

Demo 5's geometry at zero applied field, plus modulation doping:

```
AlGaAs outer (20 nm) | wide GaAs (8 nm) | AlGaAs (3 nm) | narrow GaAs (5 nm) | AlGaAs outer (20 nm)
      ^ donors at 6–12 nm, then an 8 nm undoped spacer
```

Donors sit in the barrier, not in the wells. The electrons transfer into the
wells and leave their ionized parents behind; that spatial charge separation is
what bends the bands. `demo06.py` refuses to run if the donor layer overlaps a
well, or if `spacer_thickness_nm` disagrees with the geometry.

## Staged progression

Each stage enables exactly one new mechanism, and every stage's full deck is
written to disk, so the difference between two stages is a diff of two real
input files.

| stage | doping | Poisson | Schrödinger | feedback | `run{}` |
|---|---|---|---|---|---|
| A `A_undoped_no_poisson` | – | – | ✓ | – | `quantum{}` |
| B `B_doped_classical_poisson` | ✓ | ✓ | – | – | `poisson{}` |
| C `C_quantum_on_poisson_potential` | ✓ | ✓ | ✓ | – (`no_density`) | `poisson{} quantum{}` |
| D `D_self_consistent` | ✓ | ✓ | ✓ | ✓ | `quantum_poisson{}` |
| E | Stage D repeated across `donor_density_cm3` | | | | |

## Contact placement is physics here

A contact attached to `everywhere{}` makes the **whole domain** a Dirichlet
region. Once Poisson actually runs, the potential is pinned everywhere and no
band bending can appear — measured at home on nextnano++ 3.0.0, where a
domain-wide contact plus `run{ poisson{} }` produced a flat potential and a
field of 1e−10 kV/cm despite a requested 100 kV/cm. The contact here is a 2 nm
slab at x = 0.

## Doping range — basis

`donor_density_cm3` sweeps 5e17 → 1e19 cm⁻³. That range is **not invented**: it
is the band used by the vendor examples shipped with nextnano++ 3.0.0
(`examples/basics/basics_1D_doping_heterostructure.nnp`, 1e18–1e19 cm⁻³) and by
this repository's own `hello_06c` p‑i‑n deck (1e18 cm⁻³).

Doping is never raised in order to populate a desired subband. The sweep exists
to show what doping does, not to manufacture an outcome.

## Parameters

Physical: geometry as in Demo 5, plus `donor_density_cm3`,
`donor_region_start_nm`, `donor_region_end_nm`, `donor_ionization_energy_eV`,
`donor_degeneracy`, `spacer_thickness_nm`, `contact_bias_V`, `temperature_K`.

Numerical: grid spacings, `number_of_states`, `quantum_region_padding_nm`,
`poisson_tolerance`, `maximum_iterations`, `potential_mixing_alpha`.

## Expected qualitative behaviour

- Stage A: flat barriers, the Demo 5 zero-field levels.
- Stage B: the ionized donor layer and the transferred electrons bend the
  conduction band; a built-in field appears near the doped layer.
- Stage C: the levels shift and the wells are no longer equivalent to Stage A —
  but the density that produced the bending is still classical.
- Stage D: the quantum density is narrower and displaced relative to the
  classical one, so the self-consistent potential differs from Stage C's.
- Stage E: more doping ⇒ more transferred charge ⇒ more bending ⇒ higher
  subband occupation, with additional subbands crossing the Fermi level.

## Run

```bash
python nextnano/demos/06_self_consistent_doped_coupled_well/run.py
```

## Expected outputs

Per case: `extracted/band_edges.csv`, `conduction_band.csv`, `potential.csv`,
`electric_field.csv`, `densities.csv`, `states.csv`, `occupations.csv`,
`iteration_history.csv`, `convergence.json`, plots, log, manifest.

Parent: `sweep_manifest.json`, `validation_report.md`,
`convergence_summary.md`, `extracted/sweep_summary.*`, `failed_runs.csv`,
`suspicious_runs.csv`, `tables/stage_comparison.csv`, `tables/doping_sweep.csv`,
`console_logs/`, `plots/`.

## Plots

`undoped_vs_doped_bandedges.png`, `classical_vs_selfconsistent.png`,
`densities.png`, `electrostatic_potential.png`, `electric_field.png`,
`subband_energies_vs_doping.png`, `population_vs_doping.png`,
`iteration_residuals.png`, `potential_change_vs_iteration.png`,
`convergence_status.png`, `charge_balance.png`.

## How convergence is judged

Three facts, in decreasing authority:

1. **The solver's own verdict.** If `summary.log` contains a
   "failed to converge" warning, the status is
   `solver_reported_not_converged`, full stop. No residual arithmetic here
   overrides it.
2. **The iteration cap.** Stopping at `maximum_iterations` is reported as
   `max_iterations_reached` — *never* as convergence.
3. **The residuals.** Compared against `poisson_tolerance`, each first divided
   by its own scale. `Residual_EDensity` is an absolute sheet density in cm⁻²
   sitting near 1e12; testing it directly against a 1e−6 potential tolerance
   would be a unit error, not a criterion.

## Units

nextnano++ writes carrier and dopant densities in units of **1e18 cm⁻³**
(declared in each file's header). The parser rescales to cm⁻³ before any
integration, and the position axis is converted nm → cm, so every reported sheet
density is genuinely in cm⁻².

## Validation criteria

1. All stages produced a generated input; nothing was discarded.
2. Stage B bends the conduction band by more than 1 meV relative to Stage A.
3. The self-consistent loop converged below tolerance.
4. No case merely hit the iteration cap.
5. The solver reported no convergence warning.
6. Integrated electron sheet density balances the ionized-donor sheet density
   within `maximum_charge_imbalance`.
7. Every quantum stage has at least one physically bound state.
8. E1 is stable when the quantum-region padding is doubled — the bending must
   come from charge, not from the box.

## Common failures

- **Flat bands despite doping.** The contact covers `everywhere{}`, or the
  `impurities{}` block is missing so the doping regions name an undefined
  species.
- **`max_iterations_reached`.** Check the *physics* first — donor placement,
  spacer thickness, contact, quantum-region size. Only after that consider
  `potential_mixing_alpha`. Loosening `poisson_tolerance` to obtain a
  "converged" label is not a fix.
- **Charge does not balance.** The quantum region is smaller than the region
  where electrons actually are, so part of the density is outside the integral.
- **Bound-state boundary probability high.** Strong bending has pushed a state
  against the Dirichlet wall.

## Advancement criteria

- Why must Schrödinger and Poisson be solved iteratively rather than in sequence?
- How exactly does modulation doping bend the bands, and why is the spacer there?
- What determines which subbands are occupied?
- What is the Fermi level doing in this calculation, and what is it measured
  relative to?
- How can a perfectly smooth-looking potential still fail charge consistency?

## Licensed-validation status

`licensed_run_pending` — see `nextnano/demos/demo_registry.yaml`.

- **Home, syntax:** all 11 generated decks (4 stages + 5 doping + 2 padding)
  parse cleanly under Free nextnano++ 3.0.0 `--parse`.
- **Home, execution:** a reduced-grid Stage D was executed by the Free edition
  and its real output is committed under
  `nextnano/tests/fixtures/nextnano_pp_3_0_0/demo06_doped_scf/`. That run is
  itself the demo's lesson: it exited `DONE.`, wrote `job_done.txt`, and
  `summary.log` contains `WARNING: QUANTUM-POISSON failed to converge.` The
  analysis correctly returns `converged: false` and
  `status: solver_reported_not_converged` while still recording that the
  relative residuals were 6e−16. Charge balanced to 7e−14 relative, band bending
  322 meV, three occupied subbands.
- **Still owed on the licensed laptop:** genuine convergence at production grid
  spacing without hitting the cap, charge balance across the whole doping sweep,
  and confirmation that band bending is attributable to doping rather than the
  contact.

The fixture's numbers are a 57-point, 1 nm-mesh Free-edition run. They test the
machinery. They are not converged physics.

## Work-laptop checklist

```bash
git pull
conda activate llm
python nextnano/demos/06_self_consistent_doped_coupled_well/run.py
```

- [ ] `convergence_summary.md`: every case shows `converged`, none shows
      `max_iterations_reached` or `solver_reported_not_converged`.
- [ ] `tables/stage_comparison.csv`: band bending grows from Stage A to B, and
      Stage D differs from Stage C.
- [ ] `tables/doping_sweep.csv`: `relative_charge_imbalance` below
      `maximum_charge_imbalance` at every doping level.
- [ ] `occupied_subband_count` increases with doping.
- [ ] Both E1 and E2 pass the two-case quantum-region padding check.
- [ ] Every doped case contains `designed_donor_density.csv`; every Poisson
      case contains `potential.csv` and `electric_field.csv`.
- [ ] Quantum cases contain `fermi_levels.csv`, `states.csv`, and, where
      populated, `occupations.csv`.
- [ ] `plots/iteration_residuals.png` shows residuals falling, not stalling.
- [ ] If a case fails to converge, keep its directory and report the residual
      and iteration count. Do not retune the tolerance to make it pass.
