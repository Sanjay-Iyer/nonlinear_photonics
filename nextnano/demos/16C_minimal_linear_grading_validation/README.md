# Demo 16C — minimal linear grading validation

Demo 16C asks one question: does changing a simple linear grading-width input
cause nextnano++ to construct the corresponding GaAs/AlGaAs alloy profile?

The fixed structure is AlGaAs / 7.1 nm GaAs / 1.8 nm AlGaAs / 2.9 nm GaAs /
AlGaAs with `x_Al = 0.55` and a 0.05 nm active-region mesh. The only case
variables are the central barrier's left and right linear 10–90% grading widths:

| case | left (nm) | right (nm) | purpose |
|---|---:|---:|---|
| `case_01` | 0.40 | 0.40 | near-abrupt production minimum |
| `case_02` | 0.70 | 0.70 | medium grade |
| `case_03` | 1.00 | 1.00 | wider grade |
| `case_04` | 0.40 | 1.00 | independent asymmetric control |

No random cases, nonlinear profiles, optimization, convergence sweeps, or
overlapping grades are present. Geometry and rendering come from Demo 14;
parser/structure invocation and local interface metrology come from Demo 16;
composition-table parsing and the optional physics checks reuse Demo 16B.

## Commands

Run from the repository root in the configured Python environment:

```powershell
python nextnano/demos/16C_minimal_linear_grading_validation/run_demo16c.py --preflight
python nextnano/demos/16C_minimal_linear_grading_validation/run_demo16c.py --syntax
python nextnano/demos/16C_minimal_linear_grading_validation/run_demo16c.py --structure
python nextnano/demos/16C_minimal_linear_grading_validation/run_demo16c.py --validate
python nextnano/demos/16C_minimal_linear_grading_validation/run_demo16c.py --physics
```

Running with no flag is the same safe, solver-free action as `--preflight`.
Only `--physics` launches full solves, and only for cases 01 and 03. It first
requires both syntax and realized-composition validation to pass.

For the full solves, the deeply nested nextnano++ raw trees use short run-root
directories (`p01` and `p03`). This keeps the longest Gamma/HH state paths below
Windows' 259-character limit. Human-facing decks, logs, results, and summaries
remain under `cases/case_01/physics/` and `cases/case_03/physics/`. The command
prints the exact full-solver argv and verifies return code 0, `job_done.txt`,
band edges, Gamma/HH energy spectra, probabilities, and envelopes before the
state analyzer runs.

The free nextnano++ build accepts all four production decks with `--parse`, but
its 100-grid-point limit refuses the 441-point production stack in
`--structure`. Run `--structure`, `--validate`, and `--physics` on the licensed
work laptop. This limitation is preserved as an honest failure transcript; the
demo does not weaken the required 0.05 nm mesh to manufacture a pass.

## Outputs

Runs are written below:

`nextnano/results/demo_runs/16C_minimal_linear_grading_validation/<run_id>/`

Each `cases/case_XX/` directory contains the requested parameters, intended
profile, exact deck, parser/structure transcripts, and—after a successful
licensed structure run—the realized profile, comparison metrics, and plot.
`summary.csv` contains the requested-versus-realized measurements and
`plots/all_four_intended_profiles.png` overlays the four intended profiles.
