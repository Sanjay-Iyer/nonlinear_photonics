# nextnano++ split-machine workflow

A self-contained corner of this repo for nextnano++ semiconductor
simulations, structured around a two-laptop split:

- **Home laptop** — no nextnano license. Author input decks (`inputs/`),
  templates, analysis notebooks, and driver code. Commit and push.
- **Work laptop** — nextnano Standard, portable install. Pull, fill in the
  per-machine paths once, and execute.

Nothing about the license, the solver binary, the database, or the run
outputs lives in git. Only text you author does.

```
nextnano/
  inputs/               # hand-authored .in decks
    templates/          # parameterized decks for sweeps
  scripts/              # nextnanopy drivers + postprocessing
    nn_config.py        # loads per-machine paths into nextnanopy
    run_input.py        # CLI: run decks, time them, pass/fail summary
  analysis/notebooks/   # exploratory analysis
  config/
    paths.local.yaml.example   # template; copy -> paths.local.yaml
    paths.local.yaml           # per-machine, GITIGNORED, hand-authored
  docs/runlog.md        # ledger tying commits to runs
  output/               # runtime results, GITIGNORED (never committed)
```

## The loop

**On the home laptop**

1. Write or edit a deck in `inputs/` (or a template in `inputs/templates/`).
2. Write/adjust any driver or analysis code in `scripts/` or
   `analysis/notebooks/`.
3. `git add`, commit, push. (You cannot run the solver here — no license.)

**On the work laptop**

1. `git pull`.
2. Run a deck:
   ```
   cd nextnano/scripts
   python run_input.py ../inputs/hello_01_bulk_gaas.in
   ```
   or several at once:
   ```
   python run_input.py ../inputs/hello_*.in
   ```
3. Results land in `output/` (gitignored). Record anything worth
   remembering in `docs/runlog.md`, commit that, and push.

Because `output/` never travels through git, `docs/runlog.md` is how the two
machines share what actually happened: date, commit SHA, deck, machine,
runtime, notes.

## One-time setup, per machine

Do this once on **each** laptop (the work laptop needs the real paths; the
home laptop only needs it if you want the config loader to import cleanly).

1. Install `nextnanopy` and `pyyaml` into whatever Python env you use:
   ```
   pip install nextnanopy pyyaml
   ```
2. Copy the config template and fill in the real paths for this machine:
   ```
   copy config\paths.local.yaml.example config\paths.local.yaml
   ```
   Then edit `config/paths.local.yaml` and set:
   - `exe` — the nextnano++ solver executable
   - `database` — the shipped material database `.in`
   - `license` — your license file
   - `outputdirectory` — where results are written (default: `nextnano/output`)

`config/paths.local.yaml` is gitignored on purpose. It is the *only*
machine-specific file, and it does not arrive with a `git pull` — that is
why each machine creates its own.

### Smoke tests

Two decks exist purely to confirm the install is wired up correctly:

- `inputs/hello_01_bulk_gaas.in` — bulk GaAs band edges. No self-consistency,
  no quantum. If this runs, the executable launches, the license validates,
  the database resolves, and output lands where you expect. Finishes in
  seconds.
- `inputs/hello_02_algaas_qw.in` — 10 nm GaAs / Al(0.3)Ga(0.7)As quantum
  well; expect 4 confined electron states with e1 ~30-40 meV above the GaAs
  conduction band edge.

Run both first on a fresh machine before trusting any real deck.

## Never commit

- **The license file** — it is licensed to you and must stay off git.
  Its path lives only in the gitignored `paths.local.yaml`.
- **The `output/` directory** — regenerated on demand; committing it bloats
  history with binary `.vtr`/`.fld`/`.dat` artifacts.
- The nextnano binaries and material database — they ship with the install,
  not with this repo.

The root `.gitignore` enforces all of the above, but treat this list as the
intent behind those rules.
