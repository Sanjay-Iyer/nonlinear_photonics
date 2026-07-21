# nextnano++ workflow

A self-contained, **portable** corner of this repo for nextnano++
semiconductor simulations, built around a two-laptop split:

- **Home laptop = development** — author input decks, generate sweeps, write
  Python and analysis, commit and push. No license or solver needed.
- **Work laptop = execution** — pull, run the nextnano++ Standard solver,
  inspect results and errors.

Tracked code is location-independent: every resource resolves relative to the
script file (`Path(__file__).resolve().parents[1]`), so the two laptops can
keep the repository at **different absolute paths** and nothing moves. The only
per-machine data is one gitignored YAML file.

**→ The full cycle, commands, and error-correction loop are in
[docs/WORKFLOW.md](docs/WORKFLOW.md). Start there.**

```
nextnano/
  inputs/
    01_smoke_tests/       hello_01_bulk_gaas.in, hello_02_algaas_qw.in
      03_standard_dimensions/     hello_03a (2D), hello_03b (3D)
      04_temperature_and_multiband/  04a (T=77K), 04b (6-band), 04c (8-band)
      05_strain_and_polarization/    05a (strain), 05b (piezo/pyro nitride)
      06_device_and_optical/         06a (current+recomb), 06b (optics), 06c (SCP)
    02_reference_models/  trusted baselines
    03_parameter_sweeps/  generated decks (tracked), per model family
    04_paper_replications/
    templates/            {{placeholder}} templates for generate_inputs.py
  scripts/
    nn_config.py          portable config: load + validate + preflight
    run_input.py          runner: --check-config / run decks
    generate_inputs.py    template + sweep YAML -> input decks
    run_smoke_tests.py    run a smoke stage/range (--test 1..6 | 4-6 | all)
    verify_standard_smoke_tests.py  inspect logs+outputs -> PASS/FAIL/INCONCLUSIVE
  analysis/
    scripts/  notebooks/   output parsing + analysis
  config/
    paths.local.yaml.example   tracked template (placeholders only)
    paths.local.yaml           per-machine, GITIGNORED, hand-authored
    models/  sweeps/           model + sweep definitions (sweeps/example_sweep.yaml)
  docs/
    WORKFLOW.md  runlog.md
  results/                 curated, TRACKED outputs you deliberately keep
    processed/  figures/  run_manifests/
  output/                  raw solver output, GITIGNORED (.gitkeep tracked)
  tests/                   non-licensed pytest suite
  README.md
```

Nothing about the license, the solver binary, the database, or raw output is
ever tracked. Only text you author (and the small results you curate) is.

---

## Quick reference

**Home (author + generate + push):**
```powershell
git pull ; conda activate NMIP ; python -m pip install -r requirements.txt
python .\nextnano\scripts\generate_inputs.py --config .\nextnano\config\sweeps\example_sweep.yaml
python -m pytest                       # optional non-licensed checks
git add nextnano ; git commit -m "..." ; git push
```

**Work (pull + run):**
```powershell
git pull ; conda activate NMIP ; python -m pip install -r requirements.txt
# one-time: copy paths.local.yaml.example -> paths.local.yaml and fill in real paths
python .\nextnano\scripts\run_input.py --check-config
python .\nextnano\scripts\run_input.py .\nextnano\inputs\01_smoke_tests\hello_01_bulk_gaas.in ; $LASTEXITCODE
```

### Smoke tests

Staged proof that the licensed Standard install exercises each solver feature
the Free edition lacks. One capability is added per deck, so a failure isolates
one feature.

| stage | decks | proves (Standard-only feature) |
|-------|-------|--------|
| 1 | `hello_01_bulk_gaas.in` | 1D executable/license/database wiring |
| 2 | `hello_02_algaas_qw.in` | 1D quantum well (4 confined states) |
| 3 | `03_standard_dimensions/` 03a (2D), 03b (3D) | **2D + 3D** execution (Free is 1D-only) |
| 4 | `04_temperature_and_multiband/` 04a, 04b, 04c | **T≠300 K**, **6-band k·p**, **8-band k·p** |
| 5 | `05_strain_and_polarization/` 05a, 05b | **strain**; **piezo + pyro** polarization (wurtzite) |
| 6 | `06_device_and_optical/` 06a, 06b, 06c | **drift-diffusion + SRH/Auger/radiative**; **optical spectra**; **self-consistent Schrödinger–Current–Poisson** |

Run a stage (or range) — stops on first failure, nonzero exit if any deck fails
— then verify the outputs (inspects logs + files, not just the exit code):
```powershell
python .\nextnano\scripts\run_smoke_tests.py --test 4 ; $LASTEXITCODE
python .\nextnano\scripts\verify_standard_smoke_tests.py --test 4
```

Feature-coverage matrix, per-deck syntax sources, expected output, pass
criteria, and troubleshooting are in
[docs/WORKFLOW.md](docs/WORKFLOW.md#tests-46--standard-only-solver-feature-checks).
Every stage-4–6 deck was syntax-validated at home with the Free nextnano++
3.0.0 `--parse` runmode; the Standard *execution* is confirmed on the work
laptop (no Standard model is claimed to have run at home).

## The runner CLI

```
python nextnano/scripts/run_input.py [--check-config] [--config PATH] [inputs ...]
```

- `--check-config` — verify Python, nextnanopy, and the machine paths
  (exe/database/license exist, output writable). Runs no solver.
- *(default)* — run each deck, timing it, with a PASS/FAIL summary. Validates
  exe/database/license exist first and fails clearly if not. Wildcards are
  expanded inside the script (quote them in PowerShell); an unmatched pattern
  is an error. Each deck gets its own output subdirectory.

Exit codes: `0` ok · `1` a run failed · `2` bad invocation / invalid config ·
`3` nextnanopy not importable when execution was requested.

## Never commit

- **The license file** — `*.lic` is gitignored repo-wide; its path lives only
  in the gitignored `paths.local.yaml`.
- **Raw `output/` contents** — regenerated on demand; the empty dir is kept via
  `output/.gitkeep`.
- The nextnano binaries and database — they ship with the install.

`git check-ignore <path>` confirms any specific file. See
[docs/WORKFLOW.md](docs/WORKFLOW.md) for everything else.
