# AGENTS.md — mandatory rules for this repository

This repository replicates and extends the second-order susceptibility χ(2) of
GaAs/AlGaAs asymmetric coupled quantum wells (Ramesh et al., arXiv:2602.23246) with
nextnano++ and Python. Numbered demos live in `nextnano/demos/`.

**Canonical workflow:** [`nextnano/docs/DEMO_WORKFLOW.md`](nextnano/docs/DEMO_WORKFLOW.md).
It covers demo isolation, raw data, and the HOME/WORK transfer. The rules below
summarize it; if they ever disagree, the workflow document wins.

## Must

1. **Never commit raw nextnano++ output.** That means solver files, `.dat`, logs,
   wavefunctions and zips of runs, with no size exceptions. Raw data live locally in
   `nextnano_raw/demo_NNN/<run_id>/` and move between machines by hand via Google Drive.
2. **Never run a licensed nextnano++ solve on the HOME laptop.** Licensed runs are done
   manually on the WORK laptop. HOME may only syntax-check decks with the Free build
   (`--parse`).
3. **New demos are self-contained.** No runtime imports or file reads from other demo
   folders, `demo_results/`, or other historical data locations. Copy known-good code into
   the demo and record it in the demo's `PROVENANCE.md`.
4. **Give each new demo a unique Python package name** (`demo30`, not `chi2`).
5. **Select raw data only through the demo's lock file** (`inputs/raw_data.lock.json`), with
   hash verification. Never pick "the newest folder", "the latest run" or "the first glob
   match". If data are missing, fail with a message naming the run and where to put it.
6. **Historical demos are frozen.** Do not modify, reformat or clean them up. A demo being
   developed concurrently (currently Demo 29) is read-only unless you were asked to
   work on it.
7. **Do not commit or push** unless the user explicitly asks. Stage only the files of the
   change; never use a blanket `git add -A`.
8. **Do not tune physics to match a paper** (Γ, k cutoffs, prefactors, fitted absorption).
   A copied Equation 2 engine stays byte-identical unless an approved, documented bug
   fix says otherwise.
9. **Write k cutoffs as explicit multiples** (`0.1·π/a` or `0.1·2π/a`), never "0.1 BZ".

## Environment

- HOME Python: `C:\Users\iyer95\miniconda3\envs\NMIP\python.exe` (conda is not on PATH).
  numpy is 2.x, so use `np.trapezoid`.
- Set `PYTHONIOENCODING=utf-8` when piping output that contains Unicode.
- Per-machine nextnano paths live in the gitignored `nextnano/config/paths.local.yaml`.
  Work-laptop paths are in `nextnano/docs/WORK_LAPTOP_PATHS.txt`.
- Test one demo: `<python> -m pytest nextnano/demos/<demo>/tests -q`.
