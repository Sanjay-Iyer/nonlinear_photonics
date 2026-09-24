# Demo and raw-data workflow (canonical)

This document is the single source of truth for:

- how new numbered demos are built (isolation, naming, documentation);
- how raw nextnano++ output is stored, identified and verified;
- how licensed runs move between the HOME and WORK laptops.

It applies to Demo 30 onward and to all newly stored raw data. Other files only
summarize or point here, and this document wins if they ever disagree:

| File | Role |
|---|---|
| `AGENTS.md` (repo root) | the short list of mandatory rules, for any coding agent |
| `CLAUDE.md` (repo root) | tells Claude Code to read AGENTS.md and this document |
| `.claude/skills/nextnano-demo-workflow/SKILL.md` | Claude-specific checklists that apply these rules |
| `nextnano_raw/README.md` | how to use the local raw-data folder |

[`WORKFLOW.md`](WORKFLOW.md) in this directory describes the original portable
workflow used by Demos 1–27 (`demo_runs`, `bundle_results.py`, smoke tests). It stays
valid for those demos.

## 1. The two machines

| | HOME laptop | WORK laptop |
|---|---|---|
| nextnano++ | Free 3.0.0: syntax check only (`--parse`; ≤ 100 grid points, no k·p runs) | Professional 3.0.0 (licensed) |
| Role | write code, decks, docs; analyze cached or returned raw data | run licensed decks, validate, package |
| Raw data | `nextnano_raw/` (local) | solver writes under a short root (`C:/nn_results/...`), then packages |

- Never run a licensed solve on HOME.
- Per-machine paths live only in the gitignored `nextnano/config/paths.local.yaml`.
- The licensed WORK executable needs `-l <license>` even for `--parse`.
- Work-laptop paths are listed in [`WORK_LAPTOP_PATHS.txt`](WORK_LAPTOP_PATHS.txt).

## 2. Demo isolation

1. **A new demo is self-contained.** At runtime it imports only its own package and
   installed third-party libraries. It reads only its own directory and the raw-data runs
   pinned in its lock file (section 3.5).
2. **No runtime dependency on history.** No imports or file reads from other demo
   directories (`../18_…`, `../23_…`, `../28_…`), `demo_results/`, `docs/case_*`,
   `nextnano_pro_raw_results/` or any other historical location.
3. **Copy, don't import.** Reuse known-good code by copying it into the demo. Record every
   copied file in the demo's `PROVENANCE.md`: source path, source commit, SHA-256 at copy
   time, and whether it was modified (what and why). Keep a copied Equation 2 engine
   byte-identical unless a documented bug fix is approved.
4. **Unique package name.** Name the demo's Python package after the demo (`demo30`), not
   something generic like `chi2`. Demos 28 and 29 both use `chi2`; two such packages on one
   `sys.path` can silently import each other.
5. **Isolation test.** Each demo has an audit that runs its pipeline with a Python audit
   hook blocking reads of forbidden roots, and checks that no imported module comes from
   another demo.
6. **History is frozen.** Do not refactor, reformat or "clean up" historical demos. A real
   defect is documented in the new demo (and, with approval, as a dated note in the old
   one). A demo that is being developed concurrently, by a person or another agent, is
   read-only for everyone else.

## 3. Raw nextnano data

### 3.1 Location and the Git rule

- All raw nextnano++ output lives under `nextnano_raw/` at the repository root.
- **Raw output never goes to Git. There is no size exception.** This covers solver
  output, `.dat` files, wavefunctions, solver logs, zip archives of runs, and returned
  WORK datasets. Only `nextnano_raw/README.md` and `nextnano_raw/.gitignore` are tracked.
  Both `nextnano_raw/.gitignore` and the root `.gitignore` enforce this.
- Git carries code, decks, configuration, metadata, lock files with hashes,
  documentation, and derived results and plots.
- Raw data move between machines by hand through Google Drive (section 5).
- Demos created before this policy (up to Demo 29) keep their existing layouts. When
  their data are needed by a new demo, a copy is registered here. The historical
  location is not moved.

### 3.2 Layout and names

```text
nextnano_raw/demo_NNN/<run_id>/
    RUN_RECORD.json    metadata (section 3.3)
    SHA256SUMS.txt     sha256 of every file under data/: sha256sum format, sorted, LF
    data/              byte-identical solver output, including the executed deck
```

- `demo_NNN`: three-digit number of the demo that **generated** the data (`demo_020`,
  `demo_023`, `demo_029`, `demo_030`). A demo that only reads data does not own them.
- `run_id = D<NNN>_<YYYY-MM-DD>_<descriptor>`:
  - `YYYY-MM-DD` is the date the solver run started, taken from the solver log or record;
    the exact UTC time goes in RUN_RECORD.json.
  - `descriptor` is short and hyphen-separated, controlled variable first, with decimals
    written as `p` (`k0p10pia` = 0.10·π/a). It is a label, not a parameter store.
  - Examples: `D020_2026-08-20_sb-case04-graded-300K`,
    `D023_2026-09-04_kp8-disp-k0p10pia-n301-300K`,
    `D029_2026-09-XX_T100K-kp8-k0p10pia-n301`,
    `D030_YYYY-MM-DD_kp8-disp-k0p20pia-n601-300K`.
  - A sub-study letter goes in the descriptor (`D028_2026-09-11_28K-kp8-...`).
- One solver invocation (one deck) is one run folder. Names are never reused: a repeat
  gets a new date or a `-r2` suffix.
- **Cutoffs are always written as explicit multiples:** `0.1·π/a` (0.5557 nm⁻¹ for
  a = 0.565325 nm) or `0.1·2π/a`. Never the ambiguous "0.1 BZ".

### 3.3 RUN_RECORD.json

Required keys:

| Key | Content |
|---|---|
| `run_id`, `originating_demo`, `sub_study` | identity |
| `date`, `started_utc` | solver start (date in the name; exact time here) |
| `machine`, `licensed` | e.g. `"WORK"`, `true` |
| `solver` | version and edition; executable/database SHA-256 when known |
| `deck` | path under `data/` and its SHA-256 |
| `physics` | model, temperature_K, k_direction, k_max_per_nm, k_max_label, k_points, states |
| `structure` | short description of the layer structure and grading |
| `status` | `valid`, `failed`, `partial` or `superseded` (+ `superseded_by`) |
| `provenance` | how the folder was produced: WORK run + Google Drive transfer, or a registered copy of a historical tracked path (+ its git commit) |
| `registered_utc`, `notes` | registration time; anything unusual |

### 3.4 Immutability and verification

- Nothing under `data/` is edited, renamed or rewritten after registration. Analysis
  writes elsewhere.
- `python nextnano/scripts/raw_data.py verify <run folder>` re-checks every hash in
  `SHA256SUMS.txt`.
- A damaged run is re-downloaded or re-registered, never patched.
- Failed runs are kept, marked `failed`, and never used as valid inputs.

### 3.5 How a demo selects raw data

- Each demo tracks `inputs/raw_data.lock.json`. For every run it uses, the lock records:
  - `run_id`, originating demo, date, model, temperature, k_max, k points, status;
  - the expected folder (`demo_NNN/<run_id>`);
  - the deck hash and the SHA-256 of every file the demo reads.
- The demo resolves exactly `<raw root>/demo_NNN/<run_id>/`. The raw root is chosen as:
  `--raw-root` flag, then the `NEXTNANO_RAW_ROOT` environment variable, then
  `<repo>/nextnano_raw`.
- Before parsing, the demo verifies every locked file hash.
  - Missing folder: fail, naming the run and the exact folder to download or register it into.
  - Hash mismatch: fail.
  - Status other than `valid`: fail unless explicitly allowed.
- **Never select data by "newest folder", "latest run" or "first glob match".** A parser
  that searches inside a run folder must require exactly one match.
- Outputs record the run IDs and hashes they were computed from, so stale results can be
  detected.

## 4. Reproducibility

- One documented entry command per demo regenerates all of its outputs and plots.
- Every constant lives in a config file, with a note on where it came from.
- Output metadata records the configuration, lock and raw hashes, code hashes, the git
  commit (with a dirty flag), and a timestamp.
- Plots are produced by scripts from saved numerical arrays. Outputs and figures are never
  edited by hand.
- A deterministic rerun must reproduce the numerical outputs; test it.
- Data digitized from papers come from a script (no undocumented clicking), with the CSV,
  an overlay image and an uncertainty estimate saved.
- Nothing is fitted or tuned to force agreement with a paper (Γ, cutoffs, prefactors,
  absorption).
- Nothing is committed or pushed without an explicit instruction from the user. Stage
  only the files that belong to the change (no blanket `git add -A`).

## 5. HOME ↔ WORK procedure for a licensed run

HOME

1. Write the deck plus one script with `preflight`, `pilot`, `full`, `validate` and
   `package` modes, and a README with exact commands and runtime/size estimates.
2. Syntax-check the deck with the Free build (a grammar check, not a licensed run):
   `"<free exe>" --parse -d "<database_free.nnp>" -o <scratch dir> <deck.in>`.
3. Run the demo's tests. Commit and push when the user approves.

WORK

4. `git pull`.
5. Preflight: the licensed `--parse` needs `-l <license>`.
6. **Run the pilot first and validate it.** The pilot must prove that the outputs the
   analysis needs really exist. For example, the Demo 28K run requested per-k states and
   returned only k = 0.
7. Run the full deck. The solver writes under a short root (`C:/nn_results/...`) to stay
   below Windows path limits.
8. Validate on WORK:
   - exit code 0, `job_done.txt` present, licensed banner (no "LIMITED FREE VERSION");
   - the expected files are present, values are finite, and k coverage is complete.
9. Package: `RUN_RECORD.json` + `SHA256SUMS.txt` + `data/`, zipped as `<run_id>.zip`.
   Never include license files. Failed runs are packaged too, with `"status": "failed"`.
10. Upload the zip by hand to Google Drive (folder `nextnano_raw/demo_NNN/`). **Not Git.**

HOME

11. Download the zip and unzip it into `nextnano_raw/demo_NNN/`.
12. `python nextnano/scripts/raw_data.py verify nextnano_raw/demo_NNN/<run_id>`.
13. Pin the run in the demo's lock file, run the analysis, document the result.

## 6. Naming conventions

- Demo directories: `NN_short_snake_case` (`30_absorption_study`,
  `31_multilayer_shg_propagation_study`).
- Python package: `demoNN`.
- Sub-studies: `NNA`, `NNB`, … and output folders named after them
  (`outputs/30B_chi2_baseline`).
- Raw runs: section 3.2.

## 7. Documentation for each demo

| File | Content |
|---|---|
| `README.md` | the question; the exact run command; inputs, including raw run IDs; a "where do I find X" table; whether a licensed solver run was required |
| `PLAN.md` | the approved plan and decisions, with a change log |
| `RESULTS.md` | per sub-study: what was calculated, numbers traceable to output files, plots, limitations, raw-data source |
| `PROVENANCE.md` | copied code and reference data: source path, commit, hash, modifications |
| `SOURCES.md` | papers with equation and page references, and digitization notes. Papers are cited, not copied into the demo |

## 8. Environment facts

- HOME Python: `C:\Users\iyer95\miniconda3\envs\NMIP\python.exe` (conda is not on PATH).
  numpy is 2.x, so use `np.trapezoid`, not `np.trapz`.
- Set `PYTHONIOENCODING=utf-8` when output containing Unicode is piped.
- HOME Free parser:
  `C:/Program Files/nextnano/2026_07_03/nextnano++/bin 32bit/nextnano++_Microsoft_32bit_free.exe`
  with `database_free.nnp` from the same package.
- A demo's own tests are the fast signal: `<python> -m pytest nextnano/demos/<demo>/tests -q`.
