# Demo 16D — incremental ACQW geometry and linear-grading validation

Demo 16D is a small extension of the licensed, validated Demo 16C workflow. It
keeps the same GaAs/AlGaAs material system (`x_Al = 0.55`), 10 nm total GaAs
well thickness, 0.05 nm mesh, production renderer, nextnano++ parser/structure
checks, local grading metrology, quantum-output gate, and short raw-output paths.

The seven cases are fixed and deterministic:

| case | description | well 1 / barrier / well 2 (nm) | grades L/R (nm) | full physics |
|---|---|---:|---:|:---:|
| `case_01` | reference | 7.10 / 1.80 / 2.90 | 0.70 / 0.70 | yes |
| `case_02` | thin barrier | 7.10 / 0.85 / 2.90 | 0.40 / 0.40 | yes |
| `case_03` | thick barrier | 7.10 / 2.50 / 2.90 | 0.70 / 0.70 | no |
| `case_04` | low asymmetry, `s=0.30` | 6.50 / 1.80 / 3.50 | 0.70 / 0.70 | no |
| `case_05` | high asymmetry, `s=0.55` | 7.75 / 1.80 / 2.25 | 0.70 / 0.70 | yes |
| `case_06` | asymmetric grading | 7.10 / 2.50 / 2.90 | 0.40 / 1.40 | no |
| `case_07` | deliberate linear overlap | 7.10 / 0.85 / 2.90 | 1.40 / 1.40 | yes |

Case 07 uses the existing production overlap behavior. Because the two compact
linear ramps overlap, Demo 14 renders its authoritative profile through
`ternary_import`; it does not emit overriding linear regions that would invent a
flat Al0.55 plateau. All other cases use native `ternary_linear` regions.

## Commands

Run from the repository root:

```powershell
python nextnano/demos/16D_acqw_linear_grading_geometry_validation/run_demo16d.py --preflight
python nextnano/demos/16D_acqw_linear_grading_geometry_validation/run_demo16d.py --syntax
python nextnano/demos/16D_acqw_linear_grading_geometry_validation/run_demo16d.py --structure
python nextnano/demos/16D_acqw_linear_grading_geometry_validation/run_demo16d.py --validate
python nextnano/demos/16D_acqw_linear_grading_geometry_validation/run_demo16d.py --physics
python nextnano/demos/16D_acqw_linear_grading_geometry_validation/run_demo16d.py --analyze-existing <run_dir>
```

With no flag, the command runs preflight. Only `--physics` launches full licensed
solves, exactly for cases 01, 02, 05, and 07, after parser and realized-composition
gates pass. Solver output is kept at the short run-root paths `p01`, `p02`, `p05`,
and `p07` to preserve Demo 16C's Windows path-length fix.

After each successful quantum solve, the existing Demo 14 → Demo 11 absolute
χ² pipeline evaluates the real Gamma/HH states on the established 1400–1800 nm
focused grid with the existing broadening, state selection, units, and constants.
The run saves exact 1550 nm values, peak wavelengths, signed detunings, per-case
spectral CSVs, and the four-case comparison plots. This is descriptive fixed-case
validation only: there is no random search, optimization, Bayesian optimization,
or Ax use in Demo 16D.

Runs are written below:

`nextnano/results/demo_runs/16D_acqw_linear_grading_geometry_validation/<run_id>/`

The free nextnano++ build may parse the decks but cannot run the production-size
structure or quantum calculations. Run `--structure`, `--validate`, and `--physics`
on the licensed work laptop. `--analyze-existing` never calls the solver.
