# nextnano++ split-machine workflow

A self-contained, **portable** corner of this repo for nextnano++
semiconductor simulations, built around a two-laptop split:

- **Home laptop** — no nextnano license. Author input decks, Python
  automation, and analysis; run the non-licensed test suite; commit and push.
- **Work laptop** — nextnano Standard, portable install. Pull, create one
  local config file, and execute.

The tracked code is location-independent: every resource is resolved relative
to the script file (`Path(__file__).resolve().parents[1]`), so the two
laptops can keep the repository in **completely different directories** and
nothing needs to move. The only per-machine data is one gitignored YAML file.

```
nextnano/
  inputs/                 # hand-authored .in decks
    hello_01_bulk_gaas.in
    hello_02_algaas_qw.in
    templates/            # parameterized decks for sweeps
  scripts/
    nn_config.py          # portable config: load + validate + preflight
    run_input.py          # CLI: --check-config / --dry-run / run
  analysis/notebooks/     # exploratory analysis
  config/
    paths.local.yaml.example   # tracked template (placeholders only)
    paths.local.yaml           # per-machine, GITIGNORED, hand-authored
  docs/runlog.md          # ledger tying commits to runs
  output/                 # runtime results, GITIGNORED (.gitkeep tracked)
  tests/                  # non-licensed pytest suite
  README.md
```

Nothing about the license, the solver binary, the database, or run outputs is
ever tracked. Only text you author is.

---

## Home laptop (authoring + non-licensed validation)

No license required. `pip install nextnanopy` works without one, so you can
import nextnanopy, load decks, and run the full test suite here.

```powershell
git pull
conda activate NMIP
python -m pip install -r requirements.txt
python -m pytest
python .\nextnano\scripts\run_input.py --help
```

Home development covers: input authoring, Python automation, validation,
output parsing, analysis, documentation, the non-licensed test suite, and
(optionally) Free-edition smoke tests. You **cannot** run the licensed solver
here — that is what the work laptop is for.

To sanity-check a deck loads and to preview where it would write, without any
solver:

```powershell
# (needs a local config; see "Per-machine setup". A Free/no-license config is
#  enough for --dry-run, which only loads decks and prints the plan.)
python .\nextnano\scripts\run_input.py --dry-run .\nextnano\inputs\hello_01_bulk_gaas.in
```

---

## Work laptop (licensed execution)

**The repository does NOT need to be moved.** Leave it where it is:

```
C:\Code\optics\nextnano\nonlinear_photonics
```

### 1. Pull and install deps

```powershell
cd C:\Code\optics\nextnano\nonlinear_photonics
git pull
conda activate NMIP
python -m pip install -r requirements.txt
```

### 2. Create the local config (once per machine)

`nextnano\config\paths.local.yaml` is gitignored, so it does **not** arrive
with the pull — create it by hand:

```powershell
copy nextnano\config\paths.local.yaml.example nextnano\config\paths.local.yaml
notepad nextnano\config\paths.local.yaml
```

Fill in the **local-only** values for this work laptop:

```yaml
nextnano++:
  exe: "C:/Code/optics/nextnano/2026_07_03/nextnano++/bin/nextnano++_Intel_64bit.exe"
  database: "C:/Code/optics/nextnano/2026_07_03/nextnano++/database/database.nnp"
  license: "C:/Code/optics/nextnano/2026_07_03/License/License_nnp.lic"
  outputdirectory: "C:/Code/optics/nextnano/nonlinear_photonics/nextnano/output"
  threads: 4
```

These values live only in this gitignored file. They are **never** embedded in
tracked Python code or used as runtime defaults.

### 3. Preflight

Verify every path resolves before running the solver (executes nothing):

```powershell
python .\nextnano\scripts\run_input.py --check-config
```

Every required line must read `PASS` and the final `RESULT: PASS`. If not, the
failing line names exactly what to fix (usually a wrong path in
`paths.local.yaml`).

### 4. Run the Hello World tests, one at a time

Run the first deck alone and check the exit code:

```powershell
python .\nextnano\scripts\run_input.py `
    .\nextnano\inputs\hello_01_bulk_gaas.in

$LASTEXITCODE
```

`hello_01` is a bulk GaAs slab — no self-consistency, no quantum. It exists
purely to prove the executable launches, the license validates, the database
resolves, and output lands where you expect. It should finish in seconds.

**Only after it returns `0`**, run the second deck:

```powershell
python .\nextnano\scripts\run_input.py `
    .\nextnano\inputs\hello_02_algaas_qw.in

$LASTEXITCODE
```

`hello_02` is a 10 nm GaAs / Al(0.3)Ga(0.7)As quantum well; expect 4 confined
electron states with e1 ~30–40 meV above the GaAs conduction band edge.

**Only after both individual tests pass**, run them together via wildcard (the
script expands the pattern itself, so it works in PowerShell):

```powershell
python .\nextnano\scripts\run_input.py `
    ".\nextnano\inputs\hello_*.in"

$LASTEXITCODE
```

Each deck writes to its own subdirectory (`output\hello_01_bulk_gaas\`,
`output\hello_02_algaas_qw\`), so running them together cannot let one
overwrite the other.

### 5. Inspect outputs and confirm git stays clean

```powershell
# newest output files
Get-ChildItem -Recurse .\nextnano\output | Sort-Object LastWriteTime -Descending | Select-Object -First 15 FullName, LastWriteTime

# git must show nothing to commit: outputs and paths.local.yaml are ignored
git status --short
```

`git status --short` should be empty (or show only files you intentionally
edited). If it lists anything under `nextnano\output\` or
`paths.local.yaml`, the ignore rules are being bypassed — stop and check.

Then record the run in [`docs/runlog.md`](docs/runlog.md) (get the SHA with
`git rev-parse --short HEAD`), commit that, and push.

---

## The runner CLI

```
python nextnano/scripts/run_input.py [--check-config] [--dry-run] [--config PATH] [inputs ...]
```

| mode | executes solver? | purpose |
|------|:---:|---------|
| `--check-config` | no | Preflight: Python, nextnanopy, config, path existence, output writability, threads, inputs. |
| `--dry-run` | no | Resolve config + inputs, print the plan and per-input output dir, load each deck. |
| *(default)* | yes | Run each deck, time it, print a PASS/FAIL table. |

Exit codes: `0` success · `1` a run or required check failed · `2` bad
invocation (no/unmatched inputs, or invalid config) · `3` execution requested
but nextnanopy not importable.

Wildcards are expanded **inside** the script, so `"hello_*.in"` behaves the
same in PowerShell, cmd.exe, and POSIX shells. An unmatched path or wildcard is
always an explicit error.

### Editions / profiles

The `license` value selects the profile:

- **Standard** — a real `license:` path. `--check-config` verifies the license
  file exists; execution uses it.
- **Free / non-execution** — leave `license: ""` empty (or set `profile: free`).
  No license is required. Useful on the home laptop for `--dry-run` and, if you
  install the Free edition, small smoke tests.

---

## Never commit

- **The license file** — licensed to you; its path lives only in the
  gitignored `paths.local.yaml`, and `*.lic` is ignored repo-wide.
- **The `output/` directory contents** — regenerated on demand; committing
  binary `.vtr`/`.fld`/`.dat` artifacts bloats history. The empty dir is kept
  via `output/.gitkeep`.
- The nextnano binaries and material database — they ship with the install,
  not with this repo.

The root `.gitignore` enforces all of the above; `git check-ignore <path>`
confirms any specific file.
