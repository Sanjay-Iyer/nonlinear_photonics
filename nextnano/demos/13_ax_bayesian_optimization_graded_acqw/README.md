# Demo 13 — Ax Bayesian Optimization of Graded Asymmetric Coupled Quantum Wells

Demo 12 mapped the graded GaAs/AlGaAs asymmetric coupled-quantum-well design
space with structured sweeps. Demo 13 searches the same space with Bayesian
optimization through the [Ax platform](https://ax.dev), so that a design with a
larger |χ²| at 1550 nm can be found in tens of licensed nextnano++ runs instead
of hundreds — **without** letting the optimizer buy that number by exploiting a
numerical artifact.

Nothing about the physics is new here. A trial is rendered by
`demo12.render_values` and analysed by `demo11.analyse_case`, so a Demo 13 trial
and a Demo 12 grid case with the same geometry are the same calculation. What is
new is the search, and the safeguards around it.

## What it optimizes

| | |
|---|---|
| objective (default) | maximize `chi2_at_target_wavelength_abs`, the relative \|χ²\| at 1550 nm |
| parameters | `asymmetry_s`, `central_barrier_thickness_nm`, `grading_thickness_nm`, `grading_profile` |
| constraints | detuning, boundary probability, state-tracking confidence, orthonormality, origin independence, expected state count, physical QC |
| budget | `num_initial_trials + num_iterations × batch_size` nextnano evaluations |

Other modes: `intrinsic_peak` (maximize peak |χ²|), `multi_objective` (Ax
multi-objective, returns a Pareto set), and an optional `weighted_score`.

## Everything is in `demo.yaml`

```bash
python run_demo13.py
```

No flags are needed for normal operation. Changing `bo.num_iterations` from 10
to 5 runs five BO rounds; changing it to 20 runs twenty. The expected evaluation
count is recomputed and printed before every run.

```bash
python run_demo13.py --check
```

reports the environment, the search space and the planned budget, and runs
nothing.

## Run modes (`workflow.mode`)

| mode | what it does | needs a licence |
|---|---|---|
| `synthetic_smoke_test` | the whole loop against a deterministic surface with a known optimum | no |
| `demo12_replay` | Ax vs random vs grid over completed Demo 12 results | no |
| `prepare_candidates` | generate the next candidate's input and stop | no |
| `run_pending_candidates` | execute candidates whose inputs already exist | yes |
| `closed_loop` | the full loop; the standard work-laptop mode | yes |
| `analyze_existing_results` | rebuild tables, figures and guides from the ledger | no |
| `validate_top_designs` | Stage 5 local, mesh, state-count, padding and fabrication checks | yes |

## The four things that keep the search honest

1. **A crashed trial is a failed Ax trial, never a zero.** Giving a solver crash
   an objective of zero teaches the surrogate that a whole region is genuinely
   bad, when nothing was measured there at all.
2. **Physical invalidity is expressed as outcome constraints,** so a rejected
   design keeps every metric it produced and the optimizer can learn where the
   feasible region is — instead of the result being quietly deleted.
3. **States are tracked by envelope overlap, never by energy order.** Demo 11's
   licensed run showed an 8.5× jump in χ² produced by two states swapping labels
   through an avoided crossing. That discontinuity looks like an enormous gain to
   an acquisition function. Each trial is assigned against its nearest evaluated
   neighbour in normalized parameter space, and an ambiguous assignment is a
   rejection.
4. **One structure has one parameterization.** An abrupt interface is abrupt
   whichever profile label rides along with it. The default hierarchical search
   space makes that structural — the `abrupt` branch has no grading parameters at
   all — so five labels can never become five licensed nextnano runs.

## Checkpointing

The Ax snapshot and an append-only trial ledger are written after every generated
and completed trial. The snapshot is written to a temporary file and renamed, so
an interrupted write cannot truncate it. A terminal ledger record is never
rewritten. Interrupt a run at any point and rerun the same command: it continues
from the first unfinished iteration.

The whole optimization lives in one directory
(`workflow.experiment_state_dir` under the results root). Copy that directory to
move a study between the home and work laptops.

## Guides

| file | what it explains |
|---|---|
| [`RESULTS_OVERVIEW.md`](RESULTS_OVERVIEW.md) | the goal, the space, the best current design, and whether it is validated |
| [`AX_OPTIMIZATION_GUIDE.md`](AX_OPTIMIZATION_GUIDE.md) | how Bayesian optimization works here, written for a first-time reader |
| [`PLOTS_GUIDE.md`](PLOTS_GUIDE.md) | every figure: question, axes, encoding, interpretation, limitations, CSV |
| [`TABLES_GUIDE.md`](TABLES_GUIDE.md) | every table: rows, columns, units, filtering, intended use |
| [`PAPER_COMPARISON_GUIDE.md`](PAPER_COMPARISON_GUIDE.md) | what may and may not be claimed against the published figure |
| [`WORK_LAPTOP_RUN_GUIDE.md`](WORK_LAPTOP_RUN_GUIDE.md) | exact commands for the licensed machine |

Figures carry axis labels and nothing else — no titles, no captions, no
interpretation. All of that is in the guides. Every figure has a CSV with the
same base filename holding exactly the plotted numbers.

## Units

χ² is Demo 11's Eq. 2 **relative** susceptibility: a lineshape and a trend, with
no absolute scale. Axes read `Normalized |χ²| (a.u.)`. `pm/V` appears nowhere.

## Modules

| file | responsibility |
|---|---|
| `design13.py` | design space, canonicalization, deduplication, normalized distances |
| `axsearch13.py` | the Ax layer, the immutable ledger, iteration accounting |
| `metrics13.py` | one trial's complete record, and the numbers Ax is given |
| `tracking13.py` | nearest-neighbour physical state tracking across scattered trials |
| `synthetic13.py` | Stage 1 synthetic surface with a known optimum |
| `replay13.py` | Demo 12 warm start and Stage 2 replay against random and grid |
| `tables13.py` | every table, with units metadata |
| `plots13.py` | every figure, with its matching CSV |
| `report13.py` | the guides, the overview, and the Section 23 comparison |
| `demo13.py` | run modes, the closed loop, provenance |

## Status

Implemented and exercised end to end on the home laptop with no licensed solver:
input generation, the Ax loop, checkpoint and resume, tables, figures and guides.
Synthetic Stage 1 recovers the known optimum. **No licensed nextnano++ result
exists yet.** See `demo_registry.yaml` for the pending licensed checks.
