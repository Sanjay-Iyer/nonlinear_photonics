# Demo 7 — strained InGaAs/GaAs: one-band versus 6-band valence

## Learning objective

InGaAs has a larger lattice constant than GaAs. Grown thin enough on a GaAs
substrate it does not relax — it compresses in the growth plane and stretches
along the growth axis to match. That strain does two distinct things:

- the **hydrostatic** part shifts the average band positions;
- the **biaxial** part lifts the heavy-hole/light-hole degeneracy that exists at
  the zone centre of the unstrained bulk.

A one-band hole model cannot represent HH/LH mixing at all: it assigns each
state to one band by construction. A 6-band valence k·p Hamiltonian can, so its
states carry component weights — and those weights, not the eigenvalue index,
are the only legitimate basis for calling a state "HH-like".

## Physical structure

```
GaAs barrier (25 nm) | In(x)Ga(1−x)As well (7 nm) | GaAs barrier (25 nm)
```

on a **GaAs substrate**, growth along the simulation x axis. `x = 0.15` and
7 nm are the composition and thickness of this repository's validated
`hello_05a_inGaAs_GaAs_strain.in` deck: about 1.1 % compressive mismatch, thin
enough to stay pseudomorphic.

## Controlled model progression

| model | strain | quantum | valence | `run{}` |
|---|---|---|---|---|
| M1 `M1_classical_unstrained` | `no_strain{}` | – | – | *(empty)* |
| M2 `M2_classical_strained` | `pseudomorphic_strain{}` | – | – | `strain{}` |
| M3 `M3_oneband_electron_hh` | ✓ | ✓ | one-band HH + LH | `strain{} quantum{}` |
| M4 `M4_sixband_valence` | ✓ | ✓ | `kp_6band{}` | `strain{} quantum{}` |

Never start from M4. Every difference between two adjacent rows must be
attributable to the single mechanism that was turned on.

M1 uses `strain{ no_strain{} }` rather than simply omitting the block, so the
baseline states what it is doing.

## Sweeps

- `indium_fraction`: 0.10, 0.15, 0.20, 0.25 (more indium ⇒ more mismatch)
- `well_width_nm`: 4, 6, 7, 9, 12 nm
- one refined-mesh rerun of M4, to *measure* the extra grid sensitivity of a
  multiband Hamiltonian rather than assume it.

## Expected qualitative behaviour

- Strain lowers the compressively strained well's conduction edge and pushes
  the **heavy-hole** band above the light-hole band in the well (compressive
  in-plane strain ⇒ HH on top).
- The GaAs barrier stays lattice-matched and unstrained. That is the check that
  the substrate/growth convention is what you think it is.
- One-band and 6-band hole energies agree for the most strongly HH-like state
  and diverge for the rest.
- Some 6-band states will be genuinely **mixed** and must not be given a
  single-band name.
- e1–h1 falls with increasing indium fraction and with increasing well width.

## Run

```bash
python nextnano/demos/07_strained_ingaas_gaas_6band/run.py
```

## Expected outputs

Per case: `extracted/band_edges.csv`, `hydrostatic_strain.csv`,
`strain_tensor.csv`, `electron_states.csv`, `electron_densities.csv`,
`hole_states.csv`, `hole_densities.csv`, `hole_characters.json`, plots, log,
manifest. Parent: `sweep_manifest.json`, `validation_report.md`,
`tables/model_comparison.csv`, `tables/state_character.csv`,
`extracted/sweep_summary.*`, `failed_runs.csv`, `suspicious_runs.csv`, `plots/`.

## Plots

`strained_vs_unstrained_bandedges.png`, `strain_profile.png`,
`oneband_vs_sixband_holes.png`, `state_character.png`,
`probability_densities.png`, `transitions_vs_indium.png`,
`transitions_vs_width.png`, `character_vs_parameter.png`,
`grid_sensitivity.png`.

## Hole-state ordering — a real trap

nextnano++ lists hole states with **decreasing** electron-scale energy, so state
index 1 is the *most confined* hole, not the lowest number in eV. The parser
preserves the solver's order and never sorts hole spectra; sorting them would
silently relabel physical states. Only electron spectra are checked for
ascending order.

## Validation criteria

1. All four models produced a generated input; nothing was discarded.
2. Strain is genuinely off in M1 (`no_strain{}`, no `run{ strain{} }`).
3. Hydrostatic strain is nonzero in the InGaAs well.
4. The GaAs barrier is unstrained — confirms substrate and orientation.
5. Hole component weights exist and are normalised before any state is named.
6. Electron energies are finite and ascending.
7. The refined-mesh rerun's E1 shift is measured and reported.

## Common failures

- **Both barrier and well are strained.** The substrate is not GaAs, or the
  growth direction does not match the simulation axis.
- **HH and LH still degenerate in the well.** Strain did not actually run —
  check `run{ strain{} }` is present.
- **Strain files not found.** The run fails with a listing of the files that
  *were* written. Update the strain entries in
  `nextnano/config/parsers/nextnano_pp_3_0_0.yaml`; nothing else needs to change.
- **All 6-band states come back "mixed".** Either `character_dominant_threshold`
  is too high, or the spinor-composition columns are being read in the wrong
  order — check the header names recorded in the manifest.

## Advancement criteria

- Why does lattice mismatch create strain, and when does a layer relax instead?
- How does biaxial strain split HH from LH, and which one ends up on top here?
- Why is a one-band hole model incomplete, and what exactly can it not represent?
- What does a multiband component weight mean physically?
- Can a state change from HH-like to LH-like as a parameter is swept? What would
  that look like in `tables/state_character.csv`?

## Licensed-validation status

`licensed_run_pending`, and this demo carries **unvalidated output syntax** —
see `nextnano/demos/demo_registry.yaml`.

- **Home, syntax:** all 14 generated decks parse cleanly under Free
  nextnano++ 3.0.0 `--parse`.
### First licensed run, 2026-07-30 — 13 of 14 cases failed on a filename

Every deck was **accepted and executed** by the solver (all wrote
`job_done.txt`). All but the unstrained baseline then failed in *this
repository's parser*, because the guessed strain filename was wrong. The failure
message listed the files that were actually written, which is how the real
names were obtained:

| guessed | actual |
|---|---|
| `Strain/strain_simulation_system.dat` | **`Strain/strain_simulation.dat`** (plus `strain_crystal.dat`) |
| `kp6/spinor_composition_k00000*.dat` | **`kp6/spinor_composition_k00000_CbHhLhSo.dat`** (plus an `_SXYZ` twin — the wildcard would have been ambiguous) |
| `kp6/` sub-directory | `kp6/` — correct |
| `kp6/envelopes_k00000.dat` | **`kp6/envelopes_k00000_SXYZ.dat`** |

`Quantum/qw/LH/`, `Structure/lattice_constants.dat`, and `bias_00000/bandgap.dat`
were also confirmed. All of these are now `confirmed: true` in the parser
profile, and the 8-band patterns have been re-based on the observed `kp6`
convention (still unconfirmed until Demo 8 runs).

This is the designed failure mode working: a wrong guess produced a loud,
actionable error rather than a wrong number, and the fix was one YAML file.

- **Home, execution: impossible.** The Free edition refuses both strain
  (`does not allow importing or computing strain`) and every k·p model
  (`does not allow running k.p quantum mechanics`). There is therefore **no
  real-output fixture for this demo**, unlike Demos 4, 5, 6, and 9.
- **Unconfirmed output patterns** (marked `confirmed: false` in the parser
  profile):
  - `strain{ output_strain_tensor{} }` file name and component column order;
  - the `kp_6band` output sub-directory name;
  - the `spinor_composition` file name and column order.

  If any is wrong, the run fails with an actionable listing of the files the
  solver actually wrote, and only that one YAML file needs editing.

Nothing in this demo's physics has been checked by any solver yet.

## Work-laptop checklist

```bash
git pull
conda activate llm
python nextnano/demos/07_strained_ingaas_gaas_6band/run.py
```

- [ ] Note the exact strain and `kp_6band` output paths from the first failure
      (or success) and reconcile them with the parser profile.
- [ ] `tables/model_comparison.csv`: M1 shows HH and LH degenerate in the well,
      M2 shows them split.
- [ ] `hydrostatic_strain_in_barrier` ≈ 0 and `hydrostatic_strain_in_well` ≠ 0.
- [ ] `tables/state_character.csv` has real character labels, not
      `character_unavailable_reason`.
- [ ] `state_character.png` contains normalised HH/LH/SO weights, and
      `probability_densities.png` contains actual electron and hole profiles.
- [ ] Record the refined-mesh E1 shift; if it exceeds
      `absolute_energy_tolerance_meV`, tighten the production mesh before Demo 8.
- [ ] Return the output paths, validation report, tables, and plots so the parser
      profile and registry can be updated on the home laptop.
