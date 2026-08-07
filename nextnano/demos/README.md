# nextnano++ learning sequence: Demos 1–10

These demos form one controlled progression. Run and validate them in order:

1. classical GaAs/AlGaAs band edges;
2. one-band electron confinement in the same finite well;
3. convergence of grid, domain, quantum region, and requested state count;
4. symmetric coupled wells and tunnelling-induced splitting;
5. asymmetric coupled wells, imposed field, localisation, and avoided crossings;
6. donor doping and staged self-consistent Schrödinger–Poisson;
7. strained InGaAs/GaAs with one-band and 6-band valence comparison;
8. 8-band interband transitions and polarization-resolved optics;
9. a relative three-level nonlinear-optics design sweep (never absolute χ(2));
10. first 2D confinement and mesh/domain/symmetry diagnostics.

Three further demos build on that sequence rather than extending it:

11. paper validation of the interband χ(2) of an asymmetric coupled quantum
    well, with corrected origin-independence and quasi-bound diagnostics;
12. graded GaAs/AlGaAs interfaces: profile shapes, locations, robustness, and a
    grid-and-Pareto optimization over the completed sweeps;
13. [Ax](https://ax.dev) Bayesian optimization of the same graded design space,
    replacing the grid with a closed loop that proposes, simulates, quality-
    controls, and learns — see
    [`13_ax_bayesian_optimization_graded_acqw/README.md`](13_ax_bayesian_optimization_graded_acqw/README.md).

Demos 1–3 have passed licensed work-laptop validation. Demos 4–5 are complete
for the next licensed validation cycle. Demos 6–13 remain gated by their
documented Standard-only syntax and output checks. The authoritative
machine-readable state is [`demo_registry.yaml`](demo_registry.yaml).

Demo 13 needs one dependency the others do not: `ax-platform`, pinned in
[`requirements.txt`](../../requirements.txt). Installing it does not require a
nextnano licence.

## Home laptop: generate and validate

```powershell
& "$HOME\miniconda3\Scripts\conda.exe" run -n NMIP python .\nextnano\demos\01_classical_single_quantum_well\run.py
& "$HOME\miniconda3\Scripts\conda.exe" run -n NMIP python .\nextnano\demos\02_one_band_finite_quantum_well\run.py
& "$HOME\miniconda3\Scripts\conda.exe" run -n NMIP python .\nextnano\demos\03_quantum_well_convergence\run.py
& "$HOME\miniconda3\Scripts\conda.exe" run -n NMIP python .\nextnano\demos\04_symmetric_double_quantum_well\run.py
& "$HOME\miniconda3\Scripts\conda.exe" run -n NMIP python .\nextnano\demos\05_asymmetric_coupled_quantum_well_field\run.py
```

The tracked defaults use `run_solver: auto`. When no installed/configured
solver exists, a home run performs strict YAML validation, deterministic input
rendering, run-directory creation, and provenance writing. It never fabricates
solver output.

## Work laptop: licensed execution

```powershell
git pull
conda activate llm
python .\nextnano\demos\04_symmetric_double_quantum_well\
python .\nextnano\demos\05_asymmetric_coupled_quantum_well_field\
```

Running the directory itself also works:

```powershell
python .\nextnano\demos\04_symmetric_double_quantum_well
```

No configuration edit is normally required. The runner first reuses the
existing `nextnano/config/paths.local.yaml`, then the active `llm`
environment's nextnanopy configuration, then the sibling portable package.
The relative portable root is resolved from the Git repository root, so no
drive letter is assumed. Inspect each demo's validation report, tables, plots,
and failed/suspicious-run lists before advancing.

For licensed work-laptop execution, first read
[`WORK_LAPTOP_PATHS.txt`](../docs/WORK_LAPTOP_PATHS.txt) and
[`WORK_LAPTOP_PATHS.json`](../docs/WORK_LAPTOP_PATHS.json), then select the
tracked [`nextnano_machine.work.yaml`](../config/machines/nextnano_machine.work.yaml)
with
`$env:NEXTNANO_MACHINE_CONFIG = "nextnano/config/machines/nextnano_machine.work.yaml"`.
Those manifests are authoritative: never substitute home-laptop, Codex-sandbox,
temporary-checkout, or guessed paths.
Every demo must keep deep raw nextnano++ output beneath the selected config's
short `results_root` (`C:/nn_results` on the work laptop); repository run trees
may continue to hold summaries, CSV/JSON files, and plots. The generic
`nextnano_machine.example.yaml` remains documentation, while the optional
gitignored `nextnano_machine.local.yaml` is only for genuine local overrides.

Normal scientific and numerical changes belong in each `demo.yaml`; the Python
commands need no flags. All generated inputs and outputs remain in
`nextnano/results/demo_runs` (or the explicitly configured results root).
Nothing is copied into or written beneath the portable package.

`nextnano/results/demo_runs/**` is gitignored, so results come home in a
bundle rather than a commit:

```powershell
python .\nextnano\scripts\bundle_results.py --include-plots
```

Demo 11 additionally has a solver-free audit that runs against an existing run
directory and reports whether its state-count parameters reached the
calculation at all:

```powershell
python .\nextnano\scripts\audit_state_counts.py
```

## Syntax provenance

Geometry, materials, grids, classical band requests, and the one-band quantum
block are derived from the repository's validated `hello_02_algaas_qw.in` and
`hello_04a_qw_77K_oneband.in` decks. Demo 1 deliberately does not use the
validated bulk deck's `run{ strain{} }`, because this lesson disables strain.
Its classical run trigger and neutral mandatory contact were successfully
executed with licensed nextnano++ 3.0.0 on 2026-07-30. Demos 2–3 use the
validated `run{ quantum{} }` pattern.

Demos 4–5 reuse that one-band syntax. Demo 5 defines an imposed field with
`poisson{ electric_field{ direction strength } }` but keeps
`run{ quantum{} }`; putting `poisson{}` in the run block would change the
physical problem. The version-pinned parser profile under `../config/parsers/`
records the installed nextnano++ 3.0.0 output layout and refuses missing or
ambiguous matches.
