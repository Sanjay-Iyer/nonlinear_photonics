# Demo 19 Implementation Report

## Status

The complete 13-case workflow is implemented and solver-free preflight passes.
No licensed physics was run in this environment because the executable,
database, and license paths named by the required machine configuration do not
exist here. No mock or synthetic physics was substituted.

## Locations

- Code: `nextnano/demos/19_quantum_well_interface_grading_showcase/`
- Machine configuration: `nextnano/config/machines/nextnano_machine.work.yaml`
- Pre-run case table: `demo19_grading_cases.csv`
- Implementation audit: `demo19_grading_implementation_audit.csv`
- Realized-profile validation: `demo19_realized_grading_validation.csv`
- Input examples: `demo19_nextnano_input_examples.md`
- Boss summary: `demo19_boss_summary.md`
- Presentation table: `demo19_presentation_table.csv`
- Licensed result family: `C:\nn_results\19_quantum_well_interface_grading_showcase\`

## Files created

Top-level Demo 19 files:

- `README.md`
- `IMPLEMENTATION_REPORT.md`
- `cases19.py`
- `demo19.py`
- `plots19.py`
- `run_demo19.py`
- `graded_acqw19.in.j2`
- `demo19_grading_cases.csv`
- `demo19_grading_implementation_audit.csv`
- `demo19_realized_grading_validation.csv`
- `demo19_nextnano_input_examples.md`
- `demo19_master_results.csv` (physics columns intentionally pending)
- `demo19_presentation_table.csv` (physics columns intentionally pending)
- `demo19_boss_summary.md` (preflight status; populated after physics)

Preflight output:

- `preflight_output/preflight_report.json`
- `preflight_output/plots/01_grading_composition_profiles.png`
- `preflight_output/plots/02_grading_profile_shapes.png`
- For every `case_00` through `case_12`:
  - `preflight_output/cases/case_XX/case.in`
  - `preflight_output/cases/case_XX/grading_manifest.json`
  - `preflight_output/cases/case_XX/requested_composition_profile.csv`
- Smooth cases 10, 11 and 12 additionally contain:
  - `preflight_output/cases/case_XX/al_profile.dat`

Repository test:

- `nextnano/tests/test_demo19_interface_grading_showcase.py`

No existing tracked file was modified.

## Rendering audit

- Abrupt: native binary/constant Nextnano++ regions.
- Linear: native `ternary_linear{}` syntax at each nonzero I1–I4 interface.
- Fermi-like: Python endpoint-normalized logistic `x_Al(z)`, rendered through
  `import{}` and `ternary_import{}`.
- erf: Python endpoint-normalized erf `x_Al(z)`, rendered through import.
- Cosine: Python raised-cosine `x_Al(z)`, rendered through import.
- `ternary_pyramid` is neither generated nor accepted by preflight.

All requested widths are realized as explicit centered full-transition
intervals. Imported profiles are sampled at the fixed 0.05 nm active mesh and
linearly interpolated by Nextnano++; their measured maximum errors relative to
the mathematical profile are below the 0.005 Al-fraction gate. All 13 cases pass
and no grading intervals overlap. The 1.4 nm symmetric case retains a 0.4 nm
pure central-barrier plateau.

## Licensed execution

```powershell
$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"
python .\nextnano\demos\19_quantum_well_interface_grading_showcase\run_demo19.py --physics --verbose
```

This command performs exactly 13 independent licensed Nextnano++ solves. It
refuses to start unless all preflight gates pass and all three configured
licensed-installation files exist.

## Presentation priorities

Before physics, the most useful figures are plots 01 and 02. After physics, the
primary boss-facing figures are:

1. `03_abrupt_vs_graded_wavefunctions.png`
2. `04_chi2_spectra_linear_grading.png`
3. `06_grade_width_relative_to_abrupt.png`
4. `08_grading_location_comparison.png`
5. `09_profile_shape_chi2_comparison.png`

The compact slide table is `demo19_presentation_table.csv` in the licensed run's
`tables` directory.
