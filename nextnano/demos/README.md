# nextnano++ learning sequence: Demos 1–3

These demos form one controlled progression:

1. classical GaAs/AlGaAs band edges;
2. one-band electron confinement in the same finite well;
3. convergence of the Demo 2 observables with grid, domain, quantum region,
   and requested state count.

No coupled wells, electric fields, Schrödinger–Poisson, multiband k·p, strain,
transport, or optical spectra are introduced here.

## Home laptop: generate and validate

```powershell
& "$HOME\miniconda3\Scripts\conda.exe" run -n NMIP python .\nextnano\demos\01_classical_single_quantum_well\run.py
& "$HOME\miniconda3\Scripts\conda.exe" run -n NMIP python .\nextnano\demos\02_one_band_finite_quantum_well\run.py
& "$HOME\miniconda3\Scripts\conda.exe" run -n NMIP python .\nextnano\demos\03_quantum_well_convergence\run.py
```

The tracked defaults use `run_solver: auto`. When no installed/configured
solver exists, a home run performs strict YAML validation, deterministic input
rendering, run-directory creation, and provenance writing. It never fabricates
solver output.

## Work laptop: licensed execution

```powershell
git pull
conda activate llm
python .\nextnano\demos\01_classical_single_quantum_well\run.py
```

Running the directory itself also works:

```powershell
python .\nextnano\demos\01_classical_single_quantum_well
```

No configuration edit is normally required. The runner first reuses the
existing `nextnano/config/paths.local.yaml`, then the active `llm`
environment's nextnanopy configuration, then the sibling portable package.
The relative portable root is resolved from the Git repository root, so no
drive letter is assumed. Inspect Demo 1's manifest, extracted table, log, and
plot before advancing to Demo 2, and run Demo 3 only after Demo 2 passes.

Only if automatic discovery reports an ambiguity, copy the example to the
gitignored `nextnano_machine.local.yaml` and enter the exact reported path.

Normal scientific and numerical changes belong in each `demo.yaml`; the Python
commands need no flags. All generated inputs and outputs remain in
`nextnano/results/demo_runs` (or the explicitly configured results root).
Nothing is copied into or written beneath the portable package.

## Syntax provenance

Geometry, materials, grids, classical band requests, and the one-band quantum
block are derived from the repository's validated `hello_02_algaas_qw.in` and
`hello_04a_qw_77K_oneband.in` decks. Demo 1 deliberately does not use the
validated bulk deck's `run{ strain{} }`, because this lesson disables strain.
Its empty `run{}` trigger and neutral mandatory contact were successfully
executed with licensed nextnano++ 3.0.0 on 2026-07-30. Demos 2–3 use the
validated `run{ quantum{} }` pattern.
