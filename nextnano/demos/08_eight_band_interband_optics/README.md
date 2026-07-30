# Demo 8 — eight-band k·p interband optical transitions

## Learning objective

A transition being energetically available tells you nothing about whether light
can drive it. Strength lives in the **matrix element**, which depends on the
polarisation and on how well the electron and hole envelopes overlap. This demo
computes both, and never calls a transition strong on energy alone.

## The finding that makes 8 bands necessary

Measured at home on nextnano++ 3.0.0 (Free edition, 2026-07-30):

> Asking for `momentum_matrix_elements{ Gamma{} HH{} }` over **separate**
> one-band Γ and HH solutions produces only `Gamma_Gamma/` and `HH_HH/` —
> *intraband* elements within each band. **No interband element is written at
> all.**

That is not a configuration mistake; it is structural. Two independent
eigenproblems have no operator connecting them. Only the coupled 8-band
Hamiltonian puts conduction and valence states in the same problem, which is
where an interband momentum matrix element can come from.

The same run also confirmed the intersubband selection rule directly: for
Γ→Γ intersubband transitions the growth-polarised f₁₂ was 0.065 and the
in-plane f₁₂ was **exactly zero**.

## Physical structure

Demo 7's validated strained InGaAs/GaAs well, unchanged, so the only new
variables are the electronic model and the optical request. The symmetry-broken
variant adds a 1.5 nm higher-indium step at one side of the well.

## Controlled comparison order

| model | bands | in-plane k | optical request |
|---|---|---|---|
| M1 `M1_oneband_e_h` | Γ + HH + LH, one-band | – | transition energies, overlaps |
| M2 `M2_sixband_valence` | Γ + `kp_6band` | – | transition energies, overlaps |
| M3 `M3_eightband_zone_centre` | `kp_8band` | – | + momentum matrix elements |
| M4 `M4_eightband_k_resolved` | `kp_8band` | ✓ | + momentum matrix elements |

Plus: a symmetry-broken twin of M4, well-width and field sweeps, and two
convergence reruns (more k points, finer spectral grid).

## Polarisation convention

Growth is along **x** in a 1D nextnano++ deck, so:

- `[1, 0, 0]` = **TM**, polarised along the growth axis;
- `[0, 1, 0]` = **TE**, polarised in the quantum-well plane.

Both are named in `analysis.polarizations` and the name is what appears in the
output file name. This was confirmed at home for the one-band intersubband case.

## The spectrum is post-processed — read this before quoting it

`spectrum.json` and `spectrum.png` are built **in this repository**, not by an
absorption solver:

```
S(E) = Σ_t  f_t · γ² / [ (E − E_t)² + γ² ],    γ = broadening_meV / 1000
```

- Units: **arbitrary**, declared as such in the JSON and on every axis label.
- It is **not** an absorption coefficient and has no cm⁻¹ value. No carrier
  density, refractive index, confinement factor, or normalisation enters.
- `broadening_meV` is the HWHM of each line and stands in for every mechanism
  the calculation omits — dephasing, phonons, interface roughness, well-width
  fluctuation. It is an **input**, not a result.

Two spectra from the same run may be compared. A spectrum from this demo may not
be compared with a measured absorption spectrum.

## Units discipline

Momentum matrix elements come out in **ħ/nm**; position/dipole matrix elements
in **e·nm**. They are different quantities. The parser records the unit string
from each file's header into the manifest, and the two are never added,
subtracted, or plotted on a shared axis.

## Sweeps and convergence reruns

- `well_width_nm`: 5, 7, 9 nm
- `electric_field_kV_cm`: 0, 25, 50 (Demo 5's validated imposed-field mechanism)
- `kconv`: in-plane k points doubled
- `specres`: spectral grid doubled

Both convergence reruns exist because a spectrum can look perfectly smooth and
still be under-sampled in either dimension.

## Run

```bash
python nextnano/demos/08_eight_band_interband_optics/run.py
```

## Expected outputs

Per case: `extracted/band_edges.csv`, `transitions.csv`,
`state_composition.json` for KP8, `spectrum.json`,
`plots/spectrum.png`, `plots/transition_energy_map.png`, log, manifest.
Parent: `sweep_manifest.json`, `validation_report.md`,
`tables/model_comparison.csv`, `tables/symmetry_comparison.csv`,
`extracted/sweep_summary.*`, `failed_runs.csv`, `suspicious_runs.csv`, `plots/`.

## Plots

`model_comparison_transitions.png`, `state_composition.png`,
`electron_hole_overlap.png`, `matrix_element_heatmap.png`,
`polarization_resolved_strengths.png`, `spectrum.png`,
`spectrum_symmetry_broken.png`, `oscillator_strength_vs_field.png`,
`k_convergence.png`, `spectral_resolution_check.png`.

## Scientific tests

1. **Strong versus suppressed.** A transition counts as strong only if its
   strength clears `strong_transition_fraction` of the strongest transition in
   the *same* run. Energy never enters that judgement.
2. **Break the symmetry.** The stepped well should give strength to transitions
   the symmetric well suppresses. `tables/symmetry_comparison.csv` is the direct
   before/after.
3. **Apply a field.** A modest field separates the electron and hole envelopes,
   so overlaps and oscillator strengths should fall.
4. **Compare models.** One-band, 6-band, and 8-band transition energies are
   plotted together; the differences are the point.

## Validation criteria

1. All four models produced a generated input; nothing was discarded.
2. Transition energies are present and finite.
3. Interband matrix elements exist in the 8-band model.
4. Matrix-element units are read from the file headers and recorded.

## Common failures

- **No interband elements in M1/M2.** Expected — that is the demo's finding, not
  a bug.
- **8-band output not found.** The `kp8` sub-directory name in the parser
  profile is unconfirmed; the run fails with a listing of what was written.
- **Spurious states in the gap.** The 8-band Hamiltonian is prone to spurious
  solutions; `classify_by_energy{}` is enabled, and `avoid_spurious` is
  available in the grammar if it turns out to be needed on the licensed run.
- **Spectrum changes when `specres` doubles.** The lines are narrower than the
  spectral grid — raise `spectral_points` or `broadening_meV`.

## Advancement criteria

- Why can an energetically resonant transition still be optically weak?
- What is an optical selection rule, in terms of the matrix element?
- How does polarisation change which transitions are allowed here?
- Why does 8-band coupling change the optical matrix elements rather than just
  the energies?
- What does spectral broadening represent, and why is it an input?

## Licensed-validation status

`licensed_run_pending`, with **unvalidated output syntax** — see
`nextnano/demos/demo_registry.yaml`.

- **Home, syntax:** all 13 generated decks parse cleanly under Free
  nextnano++ 3.0.0 `--parse`.
- **Home, execution: impossible.** The Free edition refuses every k·p model.
  There is **no real-output fixture for this demo**.
- **Confirmed at home anyway** (one-band probe deck, committed reasoning in the
  parser profile): the `Gamma_Gamma`/`HH_HH`-only behaviour, the intersubband
  selection rule, the `e·nm` dipole unit, and the `ħ/nm` momentum unit.
- **Unconfirmed:** the `kp8` output sub-directory name, the KP8 matrix-element
  and transition-energy file names, and which named polarisation vector ends up
  in which file name.

## Work-laptop checklist

```bash
git pull
conda activate llm
python nextnano/demos/08_eight_band_interband_optics/run.py
```

- [ ] Record the exact 8-band output paths and reconcile the parser profile.
- [ ] Confirm M1 and M2 write **no** interband matrix elements while M3/M4 do.
- [ ] `tables/model_comparison.csv`: 8-band transition energies differ from the
      one-band ones by more than the grid tolerance.
- [ ] TE and TM strengths differ; confirm which vector produced which file.
- [ ] `state_composition.png`, `electron_hole_overlap.png`,
      `matrix_element_heatmap.png`, and `polarization_resolved_strengths.png`
      contain real data rather than licensed-run placeholders.
- [ ] `tables/symmetry_comparison.csv`: at least one transition that is
      suppressed in the symmetric well gains strength in the stepped well.
- [ ] `oscillator_strength_vs_field.png` falls with field.
- [ ] `k_convergence.png`: the `kconv` spectrum overlays the reference.
- [ ] `spectral_resolution_check.png`: doubling only the post-processing grid
      does not change the resolved lineshape.
- [ ] Check for spurious in-gap 8-band solutions before believing any transition.
