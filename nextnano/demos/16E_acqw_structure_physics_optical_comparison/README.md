# Demo 16E — ten-structure ACQW physics and optical comparison

Demo 16E broadens the licensed, validated Demo 16D workflow from four solved
structures to ten, and adds the comparisons that make ten independent solves
readable as one picture:

    structure → composition → quantum states → localization → χ²(λ) → 1550 nm

Everything physical is reused: Demo 14's geometry, grading renderer and deck
template; Demo 16's parser, structure invocation and interface metrology; Demo
16B's quantum-output gate, solve and state analysis; Demo 11's absolute χ²
pipeline through Demo 14's adapter. The fixed material context is unchanged —
GaAs wells, Al<sub>0.55</sub>Ga<sub>0.45</sub>As barriers, 10 nm total GaAs well
thickness, 0.05 nm mesh, 5 meV broadening, 1400–1800 nm focused scan, 1550 nm
target.

**This is a validation and understanding demo, not a search.** There is no Ax, no
Bayesian optimization, no acquisition function, no adaptive sampling and no
winner. The ten cases are fixed in `validation_cases.yaml` before anything runs.
Cases are described as having a larger χ² or a smaller detuning; nothing is
selected because of it.

## The ten fixed structures

| case | name | well 1 / barrier / well 2 (nm) | grades L/R (nm) | s | representation |
|---|---|---:|---:|---:|---|
| `case_01` | reference graded | 7.10 / 1.80 / 2.90 | 0.70 / 0.70 | 0.42 | native linear |
| `case_02` | abrupt reference | 7.10 / 1.80 / 2.90 | abrupt | 0.42 | abrupt |
| `case_03` | thin barrier | 7.10 / 0.85 / 2.90 | 0.40 / 0.40 | 0.42 | native linear |
| `case_04` | thick barrier | 7.10 / 2.50 / 2.90 | 0.70 / 0.70 | 0.42 | native linear |
| `case_05` | low asymmetry | 6.50 / 1.80 / 3.50 | 0.70 / 0.70 | 0.30 | native linear |
| `case_06` | high asymmetry | 7.75 / 1.80 / 2.25 | 0.70 / 0.70 | 0.55 | native linear |
| `case_07` | asymmetric grading | 7.10 / 2.50 / 2.90 | 0.40 / 1.40 | 0.42 | native linear |
| `case_08` | controlled overlap | 7.10 / 0.85 / 2.90 | 1.40 / 1.40 | 0.42 | imported profile |
| `case_09` | native linear wide grade | 7.10 / 1.80 / 2.90 | 1.00 / 1.00 | 0.42 | native linear |
| `case_10` | imported linear equivalent | 7.10 / 1.80 / 2.90 | 1.00 / 1.00 | 0.42 | imported profile |

Three deliberate axes run through the set:

* **barrier thickness** — `case_03` (0.85 nm) → `case_01` (1.80) → `case_04` (2.50);
* **well asymmetry** at fixed 10 nm total — `case_05` (0.30) → `case_01` (0.42) →
  `case_06` (0.55);
* **interface treatment** at one fixed layer geometry — `case_02` (abrupt) →
  `case_01` (0.70 nm grades) → `case_09` (1.00 nm grades).

Two pairs answer specific questions rather than adding structures:

* **`case_01` vs `case_02`** — what does grading a fixed layer stack change?
  Compared in composition, E1/E2/HH1/HH2, localization, χ²(1550), peak
  wavelength and full spectrum.
* **`case_09` vs `case_10`** — an *implementation* equivalence test, not a
  physics comparison. Both decks encode one `x_Al(z)`; if the native
  `ternary_linear{}` and the imported table disagree beyond the stated budgets,
  the run says so.

`case_08` uses the already validated overlap behaviour: because the two 1.40 nm
ramps overlap across a 0.85 nm barrier, Demo 14 renders the authoritative profile
through `ternary_import` rather than emitting overriding linear regions that
would invent a flat Al<sub>0.55</sub> plateau. Its realized barrier peak is
≈ 0.267, and that is recorded as the expected value, not a defect.

### Why the imported table carries the profile's knots

nextnano++ interpolates an imported table linearly between its rows. A table
sampled only on the 0.05 nm mesh therefore cuts the corner at every ramp end,
because the profile's knots are not mesh points: for `case_10`'s 1.00 nm grades
all eight knots land exactly half a mesh cell from the nearest sample, the worst
possible offset, and the realized composition came out wrong by

    d (h - d) / h × |Δslope| = 0.0125 × 0.44 = 5.5e-3

against a 5e-3 tolerance — while native `case_09`, which hands nextnano++ the
exact ramp endpoints, was exact. That is a property of the sampling, not of the
structure, and it would have made the equivalence pair measure the table rather
than the solver.

`case_10` therefore asks the production importer to include the profile's own
knots (`grading14.import_samples(..., include_breakpoints=True)`), which
`build_structure_profile` now records along with their exact values. Eight extra
rows make the table reproduce the analytic profile exactly (residual ~3e-15 at
solver cell centres) rather than approximately.

This is opt-in, and only `case_10` opts in. `case_08`'s table is production's own
automatic fallback — the behaviour Demo 16E exists to validate — so it is left
byte-identical, as are the tables Demos 13, 14 and 17 have already recorded.
`case_08` carries the same sampling artifact at 3.9e-3, below the tolerance;
enabling knots there too is a one-flag change, but it would move a case this
study is meant to observe rather than improve.

### How the abrupt case is built

Demo 14's profile builder has no abrupt branch (a 10-90 width must be positive),
so `case_02` requests a 0.001 nm sentinel width — one fortieth of a mesh cell, so
the sampled profile is a step at every mesh coordinate and every solver cell
centre. **The deck is abrupt outright:** `demo16e.abrupt_blocks` emits only the
two `binary{ GaAs }` well regions carved out of the Al<sub>0.55</sub> matrix,
with no ramp regions at all. Using the sentinel means the intended profile, the
interface bookkeeping and the overlap oracle all come from the same production
code as every other case.

Two consequences are handled explicitly and recorded in
`comparison_metrics.json`:

* an abrupt interface has no 10-90 width, so the metrology window opens to
  0.40 nm — the narrowest real grade in the study — otherwise the crossing search
  would have fewer than three mesh points and report nothing;
* a step sampled on a finite grid is ambiguous within one cell, so the gated
  composition maximum excludes one mesh cell either side of each interface. The
  all-points maximum and the number of excluded points are reported beside it.

## Conventions

* `detuning_nm = peak_wavelength_nm - 1550`. Positive means the peak lies red of
  1550 nm.
* `L = P_left - P_right`. Positive means the state sits mainly in well 1 (the
  thick, left well), negative mainly in well 2, near zero balanced or
  delocalized. `P_left + P_barrier + P_right + P_outside = 1` exactly;
  `P_outside` is the tail in the outer AlGaAs barriers and is reported, never
  folded into a well.
* Heavy-hole energies are nextnano++'s, on the electron energy scale, where a
  more strongly confined hole lies *higher*. `HH1 - HH2 > 0` is therefore the
  hole confinement separation, the mirror of `E2 - E1`.
* χ² at 1550 nm is interpolated on the production focused spectrum and then
  checked against the production evaluation of the same quantity; a mismatch
  raises rather than being reported.
* Energy shifts are measured against `case_01` and quoted in meV.

## Commands

Run from the repository root:

```powershell
python .\nextnano\demos\16E_acqw_structure_physics_optical_comparison\run_demo16e.py --preflight
```

```powershell
python .\nextnano\demos\16E_acqw_structure_physics_optical_comparison\run_demo16e.py --syntax
```

```powershell
python .\nextnano\demos\16E_acqw_structure_physics_optical_comparison\run_demo16e.py --structure
```

```powershell
python .\nextnano\demos\16E_acqw_structure_physics_optical_comparison\run_demo16e.py --validate
```

```powershell
python .\nextnano\demos\16E_acqw_structure_physics_optical_comparison\run_demo16e.py --physics --verbose
```

```powershell
python .\nextnano\demos\16E_acqw_structure_physics_optical_comparison\run_demo16e.py --analyze-existing <run_dir>
```

With no flag the command runs preflight. Only `--physics` launches licensed
solves, and each case must pass deck generation, the parser gate, the
realized-composition gate and the required-quantum-output gate before anything is
analysed. `--analyze-existing` rebuilds every table and figure from a completed
run and never calls the solver.

## Work-laptop execution

The tracked work-laptop machine configuration already exists — do not create
another one. In PowerShell, from the repository root
(`C:\Code\optics\nextnano\nonlinear_photonics`):

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"
```

Then:

```powershell
python .\nextnano\demos\16E_acqw_structure_physics_optical_comparison\run_demo16e.py --preflight
```

followed by:

```powershell
python .\nextnano\demos\16E_acqw_structure_physics_optical_comparison\run_demo16e.py --physics --verbose
```

Raw nextnano++ output goes to the short configured results root, one directory
per case:

```text
C:\nn_results\16E_acqw_structure_physics_optical_comparison\<run_id>\p01
...
C:\nn_results\16E_acqw_structure_physics_optical_comparison\<run_id>\p10
```

This preserves the Demo 16C/16D Windows path-length fix; Demo 16E never writes
solver output under `nextnano/results/demo_runs/...`.

The free nextnano++ build on the home laptop parses all ten decks but caps 1D
simulations at 100 grid points, so `--structure`, `--validate` and `--physics`
belong on the licensed work laptop.

## What a successful licensed run produces

Under `C:\nn_results\16E_acqw_structure_physics_optical_comparison\<run_id>\`:

```text
summaries/demo16e_master_summary.csv        one row per case, every field below
summaries/demo16e_master_summary.json       the same, plus conventions and reports
summaries/structure_summary.csv             requested vs realized geometry
summaries/abrupt_vs_graded.json             case_01 vs case_02
summaries/native_vs_imported_equivalence.json   case_09 vs case_10, with budgets
plots/composition_all_cases.png             all ten x_Al(z), plus a barrier zoom
plots/energy_levels_all_cases.png           E1/E2 and HH1/HH2 per case
plots/energy_shifts_vs_reference.png        ΔE1/ΔE2/ΔHH1/ΔHH2 vs case_01, in meV
plots/wavefunction_localization_all_cases.png   left/barrier/right/outside per state
plots/chi2_wavelength_all_cases.png         ten spectra, 1550 nm line, peaks marked
plots/chi2_wavelength_grouped.png           the same spectra in three legible panels
plots/chi2_at_1550_all_cases.png            χ² at exactly 1550 nm
plots/peak_wavelength_and_detuning.png      peak position and signed detuning
plots/abrupt_vs_graded_comparison.png       composition, energies, localization, spectra
plots/native_vs_imported_equivalence.png    differences against their budgets
cases/<case>/plots/composition.png          intended vs realized x_Al(z)
cases/<case>/plots/wavefunctions.png        bands, E1/E2, HH1/HH2, with L annotated
cases/<case>/comparison_metrics.json        full composition metrology
cases/<case>/physics/wavefunctions.csv      the four probability densities
cases/<case>/physics/optical/parsed/        production χ² spectrum and settings
p01 .. p10                                  raw nextnano++ output
```

The master summary carries, per case: geometry (`well_1_nm`,
`central_barrier_nm`, `well_2_nm`, `asymmetry_s`, `left_grading_nm`,
`right_grading_nm`, `overlap`, `representation`); composition
(`realized_peak_xAl`, `max_composition_error`, `rms_composition_error`); states
(`E1_eV`, `E2_eV`, `HH1_eV`, `HH2_eV`, `E2_minus_E1_meV`, `HH1_minus_HH2_meV`,
`transition_e1_hh1_eV`, `transition_e2_hh2_eV`, and the four
`delta_*_meV_vs_reference`); localization (left / barrier / right / outside
probability and `L` for each of E1, E2, HH1, HH2); and optics (`chi2_at_1550`,
`peak_chi2`, `peak_wavelength_nm`, `detuning_from_1550_nm`, `chi2_units`).

## Relationship to Demo 16D

Demo 16D is unchanged and still runs. Demo 16E reuses its case, render,
validation and path-safety patterns rather than replacing them. Three shared
changes, all additive and all defaulting to the previous behaviour:

* `demo16b.solve_case` gained an optional `build=` hook so a caller can solve the
  deck it validated. Demo 16B, 16C and 16D pass nothing and behave as before.
* `grading14.build_structure_profile` records the profile's knots
  (`breakpoints_nm`, `breakpoint_al_fractions`) for compact-support families.
  Extra keys in `request`; nothing else reads them unless it asks.
* `grading14.import_datafile` / `render_imported_blocks` gained
  `include_breakpoints=False`. With the default, every existing imported table is
  byte-identical.
* `runlog14.write_json_atomic` and `write_text_atomic` retry the `os.replace`
  step; see below.

### Atomic writes on Windows

A licensed run lost a case at `os.replace` with `PermissionError: [WinError 5]`
— `case_06` in one run, `case_04` in another, so not case-specific: a virus
scanner or the search indexer holds a just-written file open for a few hundred
milliseconds. `runlog14` now retries only the rename, six attempts over about
1.5 s with increasing delays. The temporary file is already written and flushed,
so a retry re-attempts exactly the atomic step and never re-serialises anything.
If every attempt fails the error names both the temporary and the destination
path, and the temporary is left in place for inspection.

## Tests

```powershell
python -m pytest nextnano/tests/test_demo16e_structure_physics_optical.py nextnano/tests/test_demo16d_geometry_validation.py -q
```
