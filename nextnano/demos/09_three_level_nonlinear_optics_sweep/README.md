# Demo 9 — automated three-level design sweep

## What this demo is, and is not

**Is:** an automation and post-processing demo. It sweeps coupled-well
geometries, extracts the three lowest conduction subbands and the position
matrix elements between them, ranks candidates by a documented **relative**
metric, and re-runs the top candidates on a finer mesh to check they were real.

**Is not:** a reproduction of any paper, and **not** a χ⁽²⁾ calculation. The
metric has arbitrary units, is never printed in pm/V, and the code that would
let it be renamed to something susceptibility-shaped raises instead
(`nlo.assert_not_labelled_as_chi2`).

## Why the metric is not χ⁽²⁾

The resonant three-level second-order response has the structure

```
chi(2) ~ (N e³ / ε₀) · z12 z23 z31 / [(E21 − ħω − iΓ21)(E31 − 2ħω − iΓ31)]
```

Reaching a number in pm/V additionally requires, at minimum: the sheet carrier
density N and how it is distributed over the three subbands; the pump photon
energy ħω; the dephasing rates Γ, which nextnano++ does not supply and which
dominate the on-resonance magnitude; the population differences at the operating
temperature and bias; a local-field / effective-medium treatment relating a
microscopic polarisation to a macroscopic susceptibility; and consistent SI
conversion.

**None of those is present here.** What remains — the product of three position
matrix elements over an energy-detuning denominator — is the *geometry-driven*
part, which is exactly what a structure sweep can legitimately optimise. The
full list of omissions is in `_shared/nlo.py`, is copied into every run
manifest, and is repeated in `validation_report.md`.

## Structure

Demo 5's asymmetric coupled well with the same imposed-field mechanism, plus
`dipole_moment_matrix_elements` along the growth axis.

## Position matrix elements — obtained twice

1. **From the solver.** `dipole_moment_matrix_elements{ polarization{ re=[1,0,0] } Gamma{} }`
   writes `|<i|ε·d|j>|` in **e·nm**, which with a growth-axis polarisation *is*
   |z_ij| in nm. The magnitude column is selected by its **header-declared
   unit**, so the squared column (e²·nm²) can never be mistaken for a length.
2. **From the envelopes.** ∫ψᵢ z ψⱼ dz, computed independently in
   `analysis.position_matrix_element_nm`.

Every run compares them and fails if they disagree by more than
`maximum_matrix_element_disagreement_nm`. On the home fixture they agreed to
**3.6 × 10⁻⁶ nm** over 12 off-diagonal elements.

## Sweep modes

| mode | source | count |
|---|---|---|
| A single-variable | `sweeps.center_barrier_nm`, `sweeps.electric_field_kV_cm` | 5 + 5 |
| B two-variable grid | `analysis.grid_axes` (wide well × field) | 3 × 3 |
| C design list | `analysis.designs` | 3 |
| D convergence reruns | top `convergence_rerun_count` candidates at half the mesh | 3 |

The generator asserts the produced case count equals the count the configuration
implies, and refuses to run an incomplete sweep.

## Ranking rules

A candidate is **excluded from the top of the ranking** — but kept in every
table and plot, hatched red in the ranking chart — if any of:

- `solver_failed`
- `not_converged`
- `state_tracking_ambiguous`
- `states_not_bound`
- `matrix_elements_missing`
- `constraint_violated` (E21 or E32 outside `metric.constraints`)

Silently dropping a failed candidate would hide exactly the failures a design
sweep exists to surface.

Ranking happens **before** the convergence reruns, so the reruns are a test of
the ranking rather than an input to it.

## Run

```bash
python nextnano/demos/09_three_level_nonlinear_optics_sweep/run.py
```

## Expected outputs

Per candidate: `extracted/states.csv`, `band_profile.csv`, `envelopes.csv`,
`probability_densities.csv`, `potential.csv`, `electric_field.csv`,
`matrix_elements.json`, `metric.json`, plots, log, manifest.

Parent: `sweep_manifest.json`, `validation_report.md`,
`convergence_summary.md`, `extracted/sweep_summary.*`, `failed_runs.csv`,
`suspicious_runs.csv`, `state_tracking.csv`, and under `tables/`:
`parameters.csv`, `observables.csv`, `ranked_candidates.csv`,
`excluded_candidates.csv`, `convergence_reruns.csv`.

## Plots

`spacings_vs_geometry.png`, `matrix_elements_vs_geometry.png`,
`localization_vs_geometry.png`, `metric_vs_parameter.png`,
`metric_heatmap.png`, `detuning_vs_metric.png`, `product_vs_metric.png`,
`candidate_ranking.png`, `convergence_reruns.png`,
`state_tracking_confidence.png`, `matrix_element_cross_check.png`.

## Validation criteria

1. Candidate count matches the configuration exactly.
2. Every candidate has its own run directory and generated input.
3. No candidate was discarded.
4. Solver dipole output agrees with the envelope integral.
5. All three lowest states are physically bound in every ranked candidate.
6. State tracking is confident along both the barrier and field sweeps.
7. Top candidates survive the refined mesh.

## Common failures

- **Metric is `None`.** A matrix element is missing or the three states are not
  ordered; the reason is in `metric_excluded_reason`.
- **Ranking dominated by near-resonant noise.** `detuning_floor_meV` is too
  small, so the denominator collapses. The floor is why the on-resonance
  ordering is set by a configuration choice, and that is stated in the metric's
  assumptions.
- **Dipole sources disagree.** One of the two is being read wrongly. Resolve it
  before using any matrix element — do not pick the one you like.
- **Tracking confidence low across the whole sweep.** The geometry steps are too
  large; the tracking is feature-based here because the wells move.

## Advancement criteria

- Why do both the energy denominators *and* the matrix elements matter?
- Why can a perfectly resonant structure still have a weak metric?
- Why is state tracking essential in an optimisation rather than a nicety?
- Why must failed candidates stay visible?
- What exactly would still be needed to turn this into an absolute χ⁽²⁾?

## Licensed-validation status

`licensed_run_pending` — see `nextnano/demos/demo_registry.yaml`.

- **Home, syntax:** all 22 generated candidate decks parse cleanly under Free
  nextnano++ 3.0.0 `--parse`.
- **Home, execution:** a reduced-grid candidate at +20 kV/cm was executed by the
  Free edition; its real output — including the dipole, momentum, and oscillator
  tables — is committed under
  `nextnano/tests/fixtures/nextnano_pp_3_0_0/demo09_dipole/`. On that run:
  z12 = 0.879 nm, z23 = 1.371 nm, z13 = 1.999 nm, E21 = 55.4 meV,
  E32 = 67.8 meV, all three states bound, and the two independent routes to
  z_ij agreed to 3.6e−6 nm.
- **Still owed on the licensed laptop:** the full 22-candidate sweep at
  production mesh, the convergence reruns, and confirmation that no ranked
  candidate carries an exclusion reason.

### First licensed run, 2026-07-30 — 12 of 24 cases killed by Windows path length

The 10 single-variable cases, both convergence reruns, ran perfectly. All 9 grid
cases and all 3 design cases died with exit code 4294967295, leaving
`job_running.txt` behind and no matrix-element files.

It was not physics: `grid_005` had *identical* parameters to `f_03`, which
succeeded. It was the case directory name. `grid_007_www10p0_efm20p0` pushed

```
.../runs/<case>/raw_output/case/bias_00000/Quantum/cqw/Gamma_Gamma/dipole_moment_matrix_elements_k00000_growth_x.txt
```

past the 259-character Windows limit, and the solver died precisely while
writing that file. The path-budget guard *did* warn beforehand; it just did not
prevent the run. Fixed by:

- grid and design case directories are now `g001…`, `d01…` (values live in
  `parameters.csv`, the manifest, and the label, not in the filesystem);
- the budget constant is calibrated against the measured 104-character tail
  instead of a guessed 90;
- a solver failure that follows a budget warning now says so in the failure
  reason instead of only reporting an opaque exit code.

What did run was healthy. The refined-mesh reruns moved E21 by 0.06 meV and the
metric by 0.2 % and 1.5 %, and every validation criterion passed — including the
dipole/envelope cross-check.

## Work-laptop checklist

```bash
git pull
conda activate llm
python nextnano/demos/09_three_level_nonlinear_optics_sweep/run.py
```

- [ ] `tables/ranked_candidates.csv` has an empty `exclusion_reasons` column
      throughout.
- [ ] `tables/excluded_candidates.csv` lists a reason for every excluded row.
- [ ] `matrix_element_cross_check.png` stays below
      `maximum_matrix_element_disagreement_nm`.
- [ ] `convergence_summary.md`: the metric of each top candidate moves little
      when the mesh halves. If it moves a lot, that candidate was a
      discretisation artifact.
- [ ] `state_tracking.csv` contains separate barrier and field sweep groups and
      is confident, or the ambiguous points are excluded.
- [ ] Refined reruns keep E21/E32 within the energy tolerance and the relative
      metric within `maximum_metric_relative_change`.
- [ ] Nothing anywhere in the output is labelled χ⁽²⁾ or given a pm/V value.
