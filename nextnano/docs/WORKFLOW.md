# nextnano++ home-to-work workflow

Two laptops, one git repository, a repeated push/pull cycle.

- **Home laptop = development.** Write Python, author and edit input decks,
  generate parameter sweeps, organize configs, write analysis/parsing code and
  docs. Commit and push. *No nextnano license or solver needed here.*
- **Work laptop = execution.** Pull, run the nextnano++ Standard solver,
  inspect results and errors. *This is the authority on input syntax, the
  database, the license, and whether a model succeeds.*

The repo can live at a **different absolute path on each laptop** — tracked
code never hardcodes the location (everything resolves relative to the script
via `pathlib`). Neither repo is ever moved.

```
Home:  edit → git commit → git push
Work:  git pull → run nextnano++ → inspect
Fix:   Home edit → commit → push → Work pull → run again   (repeat)
```

---

## Home laptop — the development loop

```powershell
cd <your-home-repo-path>          # wherever you keep it
git pull
conda activate NMIP
python -m pip install -r requirements.txt
```

Then work:

1. Create or edit input decks under `nextnano/inputs/` (see the numbered
   families below).
2. Create or edit Python scripts (`nextnano/scripts/`, `nextnano/analysis/`).
3. Generate parameter-sweep inputs from a template (see below).
4. Review, commit, push:

```powershell
git status
git diff
git add nextnano
git commit -m "Add nextnano quantum-well composition sweep"
git push
```

Optional non-licensed checks (fast, no solver):

```powershell
python -m pytest
python .\nextnano\scripts\run_input.py --help
```

### Input file organization

```
nextnano/inputs/
  01_smoke_tests/        hello_01_bulk_gaas.in, hello_02_algaas_qw.in
  02_reference_models/   trusted baseline models
  03_parameter_sweeps/   generated decks live here, per model family
  04_paper_replications/ decks reproducing published results
  templates/             {{placeholder}} templates for generate_inputs.py
```

Within a family, use descriptive numbered names, e.g.
`01_baseline.in`, `02_thickness_sweep_template.in`,
`03_composition_sweep_template.in`. Decks and templates are ordinary tracked
text files — edit at home, run at work. **nextnano Standard is not required to
create or edit them.**

### Generating sweeps

Decks are generated from a template + a small sweep YAML. Generation is pure
text substitution (no license) and deterministic (same config → identical
decks):

```powershell
python .\nextnano\scripts\generate_inputs.py `
    --config .\nextnano\config\sweeps\example_sweep.yaml
```

This writes decks into `nextnano/inputs/03_parameter_sweeps/<model_name>/`,
a **tracked** location — commit them so the work laptop can run them. Templates
use `{{name}}` placeholders (double braces, so they never clash with
nextnano's own `global{ ... }` blocks). Use `--dry-run` to preview.

---

## Work laptop — execution

### One-time setup

```powershell
cd C:\Code\optics\nextnano\nonlinear_photonics
git pull
conda activate NMIP
python -m pip install -r requirements.txt
```

Create the ignored local config **by hand** (it never arrives via git and a
pull will never overwrite it):

```powershell
copy nextnano\config\paths.local.yaml.example nextnano\config\paths.local.yaml
notepad nextnano\config\paths.local.yaml
```

Fill in this work laptop's real paths:

```yaml
nextnano++:
  exe: "C:/Code/optics/nextnano/2026_07_03/nextnano++/bin/nextnano++_Intel_64bit.exe"
  database: "C:/Code/optics/nextnano/2026_07_03/nextnano++/database/database.nnp"
  license: "C:/Code/optics/nextnano/2026_07_03/License/License_nnp.lic"
  outputdirectory: "C:/Code/optics/nextnano/nonlinear_photonics/nextnano/output"
  threads: 4
```

### Preflight, then run

```powershell
python .\nextnano\scripts\run_input.py --check-config
```

Expect `RESULT: PASS`. Then run the smoke tests one at a time, checking the
exit code each time:

```powershell
python .\nextnano\scripts\run_input.py `
    .\nextnano\inputs\01_smoke_tests\hello_01_bulk_gaas.in
$LASTEXITCODE
```

After it returns `0`:

```powershell
python .\nextnano\scripts\run_input.py `
    .\nextnano\inputs\01_smoke_tests\hello_02_algaas_qw.in
$LASTEXITCODE
```

Run a whole sweep (wildcards are expanded inside the script, so quote them):

```powershell
python .\nextnano\scripts\run_input.py `
    ".\nextnano\inputs\03_parameter_sweeps\qw_composition_sweep\*.in"
$LASTEXITCODE
```

Each deck writes to its own subdirectory under `nextnano/output/`, so decks in
one sweep never overwrite each other. Raw output stays local (gitignored).

---

## Test 3 — Standard-dimensionality check (2D + 3D)

**Purpose.** Prove the licensed nextnano++ can execute **2D and 3D** domains.
Per nextnano's product comparison, the **Free** edition supports **only 1D**,
while **Evaluation** and **Standard** support 1D/2D/3D. So a successful 2D and
3D run confirms a licensed (Evaluation/Standard) dimensional capability — it
does **not** distinguish Evaluation from Standard by dimensionality alone.
Because this work laptop uses `License_nnp.lic` from the Standard install, a
pass validates the **Standard** workflow.

The two decks live in `nextnano/inputs/01_smoke_tests/03_standard_dimensions/`
and are intentionally tiny (coarse ~2 nm grid, homogeneous GaAs, one confined
Γ electron state) so they run in well under a second.

```powershell
cd C:\Code\optics\nextnano\nonlinear_photonics
git pull
conda activate NMIP
python .\nextnano\scripts\run_input.py --check-config
```

Run 2D first:

```powershell
python .\nextnano\scripts\run_input.py `
    .\nextnano\inputs\01_smoke_tests\03_standard_dimensions\hello_03a_gaas_rectangle_2d.in
$LASTEXITCODE
```

Then 3D:

```powershell
python .\nextnano\scripts\run_input.py `
    .\nextnano\inputs\01_smoke_tests\03_standard_dimensions\hello_03b_gaas_cuboid_3d.in
$LASTEXITCODE
```

Then both together (quote the wildcard — the script expands it):

```powershell
python .\nextnano\scripts\run_input.py `
    ".\nextnano\inputs\01_smoke_tests\03_standard_dimensions\hello_03*.in"
$LASTEXITCODE
```

Or use the convenience wrapper (runs 3A then 3B, stops on failure):

```powershell
python .\nextnano\scripts\run_smoke_tests.py --test 3
$LASTEXITCODE
```

### Inspect the newest logs and confirm dimensionality

Each deck writes to its own subdirectory under `nextnano\output\`
(`hello_03a_gaas_rectangle_2d\`, `hello_03b_gaas_cuboid_3d\`). Find the newest
output and log files:

```powershell
Get-ChildItem -Recurse .\nextnano\output\hello_03a_gaas_rectangle_2d, `
                       .\nextnano\output\hello_03b_gaas_cuboid_3d |
    Sort-Object LastWriteTime -Descending | Select-Object -First 20 FullName, LastWriteTime
```

Open the newest `*.log` and confirm the dimensionality nextnano++ reports:

```powershell
# 2D run should report a two-dimensional simulation; 3D run, three-dimensional.
Get-ChildItem -Recurse .\nextnano\output\hello_03a_gaas_rectangle_2d -Filter *.log |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1 |
    Get-Content | Select-String -Pattern "2D|two-dimensional|dimension"

Get-ChildItem -Recurse .\nextnano\output\hello_03b_gaas_cuboid_3d -Filter *.log |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1 |
    Get-Content | Select-String -Pattern "3D|three-dimensional|dimension"
```

### Test 3 passes only when — for **each** deck

- the runner exit code (`$LASTEXITCODE`) is `0`;
- nextnano++ recognizes the domain as 2D (3A) / 3D (3B);
- normal solver output is generated in the deck's output subdirectory;
- the log contains **no** fatal error and **no** license-restriction error.

**Interpretation on success:** both the 2D rectangle and the 3D cuboid executed
using the licensed nextnano++ configuration. Because the Free edition supports
only 1D, this confirms access to licensed Evaluation/Standard dimensional
capabilities; and since this machine uses `License_nnp.lic` from the Standard
install, the runs validate the work-laptop Standard workflow.

> **Home-laptop caveat.** The 2D/3D-specific syntax (`simulate2D{}` /
> `simulate3D{}`, `ygrid`/`zgrid`, `rectangle{}` / `cuboid{}`) is *not*
> validated at home — the Free executable rejects 2D/3D by license, and
> nextnanopy only confirms the files are nextnano++ inputs. Authoritative
> parse + execution validation happens here, on the work laptop. If the Free
> solver ever refuses these files specifically due to the 1D restriction, that
> is expected — do not rewrite them back to 1D.

---

## The error-correction cycle

1. Run the deck on the **work laptop**.
2. Copy the relevant error message into notes (or send it back to the
   development LLM at home).
3. **Do not** edit unrelated files directly on the work laptop.
4. Fix the input or code in the **home** repository.
5. Commit and push from home.
6. `git pull` on the work laptop.
7. Run the same deck again.
8. Repeat until it succeeds.

If you must make a minor emergency edit on the work laptop, commit it (or copy
it back to home) **before the next pull**, so the two clones don't diverge.

---

## Keeping results

Raw solver output under `nextnano/output/` is gitignored and stays on the work
laptop. When you want to preserve something small and specific, copy it into
the tracked `nextnano/results/` area and commit it deliberately:

```
nextnano/results/
  processed/       small parsed/reduced data
  figures/         plots worth keeping
  run_manifests/   which commit + deck + paths produced a result
```

Nothing is auto-copied there — it is a deliberate, curated location. Record
runs in [`runlog.md`](runlog.md) (get the commit with
`git rev-parse --short HEAD`).

Confirm the working tree is clean after a run — outputs and `paths.local.yaml`
must not show up:

```powershell
git status --short
```
