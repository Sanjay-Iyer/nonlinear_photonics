# nextnano_raw — local raw nextnano++ data

This folder holds raw nextnano++ output on the machine where you are working.
**It never goes to Git.** Only this README and `.gitignore` are tracked; every run
folder is ignored, whatever its size. Raw data move between the WORK and HOME
laptops by hand, through Google Drive.

The policy behind this folder is in
[`nextnano/docs/DEMO_WORKFLOW.md`](../nextnano/docs/DEMO_WORKFLOW.md) (section 3 and 5).
This README is the practical summary; if the two ever differ, the workflow document wins.

## Layout

```text
nextnano_raw/
├── README.md, .gitignore            tracked
└── demo_NNN/                        ignored: one folder per GENERATING demo
    └── <run_id>/                    one folder per solver invocation (one deck)
        ├── RUN_RECORD.json          what, when, where, which deck, which physics, status
        ├── SHA256SUMS.txt           sha256 of every file under data/ (sha256sum format)
        └── data/                    byte-identical solver output (+ the executed deck)
```

## Run IDs

`D<NNN>_<YYYY-MM-DD>_<descriptor>`

- `NNN` — three-digit number of the demo that **generated** the data.
- `YYYY-MM-DD` — date the solver run **started** (exact UTC time goes in RUN_RECORD.json).
- `descriptor` — a short, hyphen-separated label, controlled variable first. Decimals are
  written with `p`: `k0p10pia` means k_max = 0.10·π/a. Always name the cutoff as a
  multiple of π/a (or 2π/a); never "0.1 BZ". The descriptor is a label, not a parameter
  store: the full parameters live in RUN_RECORD.json.

Examples:

| Run ID | Meaning |
|---|---|
| `D020_2026-08-20_sb-case04-graded-300K` | Demo 20 single-band Γ + HH, case 04 (1 nm linear grading), 300 K |
| `D023_2026-09-04_kp8-disp-k0p10pia-n301-300K` | Demo 23 8-band dispersion to 0.10·π/a, 301 k points, 300 K |
| `D029_2026-09-XX_T100K-kp8-k0p10pia-n301` | a future Demo 29 temperature run |
| `D030_YYYY-MM-DD_kp8-disp-k0p20pia-n601-300K` | the optional Demo 30 extended-k run |

A run folder name is never reused. A repeat run gets a new date or a `-r2` suffix.

## Where the data come from

1. **Returned WORK-laptop runs.** On WORK the run is validated, packaged as
   `<run_id>.zip` (RUN_RECORD.json + SHA256SUMS.txt + data/), and uploaded to Google Drive.
   On HOME:
   1. download `<run_id>.zip`;
   2. unzip it into `nextnano_raw/demo_NNN/` so that `nextnano_raw/demo_NNN/<run_id>/` exists;
   3. verify it:
      `python nextnano/scripts/raw_data.py verify nextnano_raw/demo_NNN/<run_id>`
2. **Registered copies of historical data** that already exist elsewhere in the repository
   (for example `demo_results/demo23/raw/...`). The historical location is never moved or
   edited; a byte-identical copy is registered here:
   `python nextnano/scripts/raw_data.py register --help`

List what is on this machine with `python nextnano/scripts/raw_data.py list`.

## Rules

- **Immutable.** Nothing under `data/` is edited, renamed or rewritten after registration.
  Analysis writes its outputs elsewhere. A damaged run is re-downloaded or re-registered.
- **Explicit selection.** A demo names the runs it needs in its tracked
  `inputs/raw_data.lock.json` (run ID, date, model, temperature, k_max, k points, deck
  hash, file hashes, status) and verifies the hashes before parsing. Nothing ever picks
  "the newest folder", "the latest run" or "the first glob match".
- **Failed runs are kept**, marked `"status": "failed"` in RUN_RECORD.json, and are never
  used as valid inputs.
- **Location override.** Demos look for `<repo>/nextnano_raw` by default. Point them
  elsewhere with `--raw-root` or the `NEXTNANO_RAW_ROOT` environment variable (for
  example when someone receives a demo folder plus its raw packages).
