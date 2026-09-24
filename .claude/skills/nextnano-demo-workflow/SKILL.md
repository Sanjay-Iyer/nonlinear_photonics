---
name: nextnano-demo-workflow
description: Checklists for building or changing a numbered demo under nextnano/demos, registering or verifying raw nextnano++ output in nextnano_raw/, and preparing a licensed WORK-laptop run (pilot, validation, Google Drive transfer). Use it whenever a task creates a demo, touches raw nextnano data, or prepares a nextnano deck for the work laptop.
---

# nextnano demo workflow — operational checklists

The rules are defined in `nextnano/docs/DEMO_WORKFLOW.md`. That document is canonical:
read it first. This skill only turns it into checklists, and if the two ever disagree,
the workflow document wins. The mandatory short list is in `AGENTS.md`.

## Before touching anything

- [ ] Check `git status` and `git log --oneline -5`. Another agent may be working in
      parallel (for example on Demo 29 or a `codex/*` branch). Never modify a demo you
      were not asked to work on.
- [ ] Use the NMIP interpreter (see `AGENTS.md`).

## New demo

- [ ] Create `nextnano/demos/NN_short_name/` with package `demoNN/`.
- [ ] Write README.md, PLAN.md, RESULTS.md, PROVENANCE.md and SOURCES.md (workflow section 7).
- [ ] Copy known-good code; do not import it. Record source path, commit, SHA-256 and
      any modification in PROVENANCE.md. Keep a copied `equation2.py` byte-identical.
- [ ] Pin raw runs in `inputs/raw_data.lock.json` (workflow section 3.5). The resolver must
      fail with the run ID and the folder to put it in when data are missing.
- [ ] Put every constant in config, with its source.
- [ ] Provide one entry command. Outputs record config, lock hashes, code hashes and
      git commit/dirty state.
- [ ] Tests: regression to the reference baseline, unit tests for new physics,
      determinism, and the isolation audit.

## Registering data that already exist in the repository

```text
<python> nextnano/scripts/raw_data.py register --demo NN --run-id DNNN_YYYY-MM-DD_desc \
    --source <historical path> --record <metadata.json>
<python> nextnano/scripts/raw_data.py verify nextnano_raw/demo_NNN/<run_id>
```

`register` copies the source (it never moves it) into `data/`, then writes
`SHA256SUMS.txt` and `RUN_RECORD.json`. It refuses to overwrite an existing run folder.
Then pin the files the demo reads in its lock file.

## A run returned from the WORK laptop (Google Drive)

- [ ] Download `<run_id>.zip` and unzip it into `nextnano_raw/demo_NNN/`.
- [ ] Run `<python> nextnano/scripts/raw_data.py verify nextnano_raw/demo_NNN/<run_id>`.
- [ ] Read `status` in RUN_RECORD.json. A failed run is kept but never used as valid input.
- [ ] Add or update the lock entry, rerun the demo, and document the result.

## Preparing a WORK-laptop run

- [ ] Provide the deck plus a script with `preflight`, `pilot`, `full`, `validate` and
      `package` modes, and a README with exact commands and runtime/size estimates.
- [ ] Syntax-check at home with the Free parser (`--parse`). This is not a licensed run.
- [ ] Make the pilot prove that the outputs the analysis needs exist. For example, check
      for nonzero-k rows, because 28K returned k = 0 only.
- [ ] Package as RUN_RECORD.json + SHA256SUMS.txt + data/, zipped as `<run_id>.zip`.
      Include no license files. Upload to Google Drive, never Git.

## Before finishing

- [ ] `git status` shows no raw data, zips, PDFs or solver output added by accident, and no
      change to concurrent or historical demos.
- [ ] `git check-ignore -v nextnano_raw/<any path>` reports the ignore rule.
- [ ] Show the user the git status, the files changed, the tests and a proposed commit
      grouping. Commit only when asked.
