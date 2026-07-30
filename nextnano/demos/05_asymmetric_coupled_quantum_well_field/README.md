# Demo 5 — asymmetric coupled quantum well with electric-field tuning

## Learning objective

Demo 4's two wells were identical, so its eigenstates were forced into definite
parity. Make one well wider than the other and that symmetry is gone: at zero
field the two single-well levels are detuned, and each state lives mostly in one
well. An electric field tilts the structure and can bring the two wells into
resonance — where they hybridise, repel, and **exchange character**.

The point of the demo is that after such a crossing, "state 2" no longer means
what it meant before. Following states by eigenvalue index gives a plausible,
smooth, and wrong answer.

## Physical structure

```
AlGaAs outer | wide GaAs well | AlGaAs coupling barrier | narrow GaAs well | AlGaAs outer
   20 nm     |     8 nm       |          3 nm           |       5 nm       |    20 nm
```

The **wide well is grown first**, so it sits at *low* x. Every sign statement
below depends on that.

## Enabled physics

- everything from Demo 4;
- an **imposed** electrostatic tilt via `poisson{ electric_field{} }`.

## Disabled physics

Doping, self-consistent carrier charge, strain, k·p, transport, optics. In
particular `run{}` contains **only** `quantum{}` — see the sign/unit section.

## Field convention — measured, not assumed

Measured on nextnano++ 3.0.0 (Free edition, home laptop, 2026-07-30):

| fact | evidence |
|---|---|
| `strength` is in **V/m** | `strength = 1.0e7` produced exactly `100` in `electric_field.dat` (kV/cm) and a 0.400 V drop over 40 nm |
| positive strength along `+x` tilts the conduction band **upward** towards +x | `Ec(0) = 3.1477 eV`, `Ec(40 nm) = 3.5477 eV`; consistent with `Ec = −eφ + const` |
| the imposed field survives only without a Poisson step | with `run{ poisson{} }` the tilt was replaced by the contact-pinned solution and the field came out as 1e−10 kV/cm |

`demo05.py` converts `electric_field_kV_cm → V/m` with `× 1e5`, and **every run
re-checks it** three ways: against `electric_field.dat`, against `−dφ/dx` from
`potential.dat`, and against the sign of the band-edge slope. If the Standard
edition differs, the run fails with the measured numbers instead of quietly
producing a wrong field.

The mandatory contact is confined to a 2 nm slab rather than `everywhere{}`.
That is harmless here and essential in Demo 6.

## Parameters

`wide_well_width_nm`, `narrow_well_width_nm`, `center_barrier_nm`,
`left_outer_barrier_nm`, `right_outer_barrier_nm`, `aluminum_fraction`,
`temperature_K`, `electric_field_kV_cm`, `field_direction` (`"+x"` / `"-x"`),
`contact_thickness_nm`; numerically `active_region_grid_spacing_nm`,
`exterior_grid_spacing_nm`, `number_of_states`, `quantum_region_padding_nm`.

## Sweeps

- `electric_field_kV_cm` from −100 to +100 kV/cm, 17 points, denser near zero.
- `quantum_region_padding_nm`: 10 and 20 nm — the artifact control.

## Expected qualitative behaviour

- The conduction band acquires a linear tilt whose slope is exactly `eF`.
- One field polarity pushes the two well levels apart; the other brings them
  together, through resonance, and past it.
- Near resonance the two states hybridise: both spread over both wells, the gap
  reaches a minimum without closing, and each state's centroid moves rapidly.
- Beyond resonance the localisations have **swapped**.
- Far from resonance each state sits in one well and shifts roughly linearly
  with field — the quantum-confined Stark effect.

## Run

```bash
python nextnano/demos/05_asymmetric_coupled_quantum_well_field/run.py
```

## Expected outputs

Per case: generated input, raw output, `extracted/states.csv`,
`extracted/band_profile.csv`, `extracted/envelopes.csv`,
`extracted/probability_densities.csv`, `extracted/potential.csv`,
`extracted/electric_field.csv`, `extracted/envelope_matrices.json`, plots,
log, manifest. Parent: `sweep_manifest.json`, `validation_report.md`,
`extracted/sweep_summary.*`, `failed_runs.csv`, `suspicious_runs.csv`,
`state_tracking.csv`, `extracted/state_overlap_matrices.json`,
`tables/tracked_states.csv`, `tables/avoided_crossings.csv`,
`tables/field_convention.csv`, `console_logs/`, `plots/`.

## Plots

`band_diagrams_selected_fields.png`, `energies_vs_field.png`,
`centroid_vs_field.png`, `well_probability_vs_field.png`,
`spacings_vs_field.png`, `wavefunctions_near_crossing.png`,
`state_tracking_confidence.png`, `overlap_matrix.png`,
`field_unit_check.png`, `padding_check.png`. Full band profiles and envelopes
for each individual field are in `runs/<case>/plots/`.

The energy, centroid, and well-probability curves use physical branches followed
by envelope overlap. `overlap_matrix.png` is the adjacent-field state-overlap
matrix at the least-confident tracking step; it is not the position matrix
`z_ij`.

## State tracking

Geometry is fixed across the field sweep, so envelopes from neighbouring points
share a grid and `|⟨ψ_prev|ψ_now⟩|` is meaningful. Each point is matched to the
previous one by optimal assignment on that overlap, and the per-state confidence
is recorded. A confidence below `minimum_state_tracking_confidence` marks the
point ambiguous — which is the expected signature of a sharp avoided crossing,
not a bug to be suppressed.

Envelope signs are canonicalised (largest-magnitude sample made positive) so an
arbitrary solver-side sign flip is never mistaken for a physical change.

## Validation criteria

1. Every field point produced a generated input; none was discarded.
2. `electric_field.dat` agrees with the requested field within
   `field_unit_tolerance`.
3. `−dφ/dx` agrees with the requested field within the same tolerance.
4. The band-edge slope has the sign the convention predicts.
5. **Both** polarities ran successfully.
6. Bound-state probability at the domain edges stays small — a strong tilt
   pushes states towards one wall, and this is the diagnostic that catches it.
7. State tracking is confident at every step, or the ambiguous steps are
   reported.
8. E1 and E2 are unchanged when the quantum-region padding is doubled. This is
   what separates genuine field-induced localisation from a boundary artifact.

## Common failures

- **Field comes out zero.** `run{}` contains a Poisson step, or the contact
  covers `everywhere{}` while Poisson runs. Both are checked here.
- **Field is 10⁵ × wrong.** `strength` was given in kV/cm instead of V/m; the
  unit check catches it on the first case.
- **Tracking confidence collapses everywhere**, not just near resonance. The
  field steps are too coarse — halve them near the crossing.
- **Energies move with padding.** The tilt has pushed a state against the
  Dirichlet wall; the "localisation" is the box, not the field.
- **No crossing found.** The field range is too narrow for this detuning, or the
  wells are too similar in width.

## Advancement criteria

- How does the field direction change the potential, and what fixes the sign?
- Why do the two states exchange localisation as the field passes resonance?
- What makes a crossing *avoided* rather than exact — what would have to be zero
  for the levels to actually cross?
- Why is eigenvalue order insufficient for tracking, and what replaces it?
- Why does a coupled asymmetric well matter for second-order nonlinear optics?
  (Because it can give three levels with simultaneously large `z12`, `z23`, and
  `z13` — the product Demo 9 screens for.)

## Licensed-validation status

`licensed_run_pending` — see `nextnano/demos/demo_registry.yaml`.

- **Home, syntax:** all 19 generated decks parse cleanly under Free
  nextnano++ 3.0.0 `--parse`.
- **Home, execution:** a reduced-grid version at +50 kV/cm was executed by the
  Free edition; its real output is committed under
  `nextnano/tests/fixtures/nextnano_pp_3_0_0/demo05_field_cqw/`. On that run the
  requested field, `electric_field.dat`, and `−dφ/dx` all agreed at 50.0 kV/cm,
  the band tilt was `+0.00508 eV/nm` (= eF), and state 1 sat 94 % in the wide
  well while state 2 sat 82 % in the narrow well.
- **Still owed on the licensed laptop:** the full ±100 kV/cm sweep at production
  grid spacing, re-confirmation of the V/m unit and sign on the Standard
  edition, and that avoided-crossing flags survive a padding and grid recheck.

## Work-laptop checklist

```bash
git pull
conda activate llm
python nextnano/demos/05_asymmetric_coupled_quantum_well_field/run.py
```

- [ ] `sweep_manifest.json` reports `status: completed` and 19 cases.
- [ ] `extracted/failed_runs.csv` and `suspicious_runs.csv` contain only `none`.
- [ ] `tables/field_convention.csv`: requested = measured = `−dφ/dx` at every point.
- [ ] Band tilt is positive for positive field with `field_direction: "+x"`.
- [ ] `validation_report.md` shows PASS for both polarities.
- [ ] `tables/avoided_crossings.csv` lists at least one flag; open the
      corresponding `runs/<case>/plots/wavefunctions.png` and confirm both
      states are delocalised there.
- [ ] `state_tracking.csv` confidence dips only near the flagged crossing.
- [ ] `tables/tracked_states.csv` follows physical branches through any exchange
      of solver eigenvalue index.
- [ ] `plots/overlap_matrix.png` shows adjacent-field overlaps, and
      `band_diagrams_selected_fields.png` shows actual band profiles.
- [ ] Both E1 and E2 change by less than `absolute_energy_tolerance_meV`
      between padding cases.
