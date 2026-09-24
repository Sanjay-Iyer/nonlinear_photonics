# Demo 30 — absorption and second-harmonic generation in the Fig. 2d sample

**Question.** How does linear absorption of the fundamental (ω) and of the second
harmonic (2ω) change the predicted wavelength dependence of SHG from the 2026 coupled
quantum wells (Ramesh et al., arXiv:2602.23246)? Does it move the prediction toward the
measured Fig. 2d response?

**Short answer** (details in [RESULTS.md](RESULTS.md)):

- Absorption roughly halves the SH intensity of the 80-period sample near the resonance.
- It does this almost uniformly, so the predicted peak moves by only 0–1 nm (1503 nm,
  versus 1560 nm measured).
- The shape agreement barely improves.

**Licensed nextnano run required: NO.** Everything runs at home from existing,
hash-verified raw data. An *optional* 0.2·π/a extension package is prepared in
[`work_laptop/`](work_laptop/README.md) but has not been run.

## Run it

From the repository root, with Python ≥ 3.10, numpy, scipy and matplotlib (on HOME, the
NMIP interpreter):

```powershell
python nextnano/demos/30_absorption_study/scripts/run_demo30.py
python -m pytest nextnano/demos/30_absorption_study/tests -q
python nextnano/demos/30_absorption_study/scripts/audit_isolation.py
```

- `run_demo30.py` regenerates every file in `outputs/` and `plots/` in about 10 s. It
  never runs nextnano.
- `run_demo30.py --check-stale` reports outputs whose config, lock or code has changed since
  they were written.

## Raw data (never in Git)

The runs are pinned by hash in [`inputs/raw_data.lock.json`](inputs/raw_data.lock.json) and
read from `<repo>/nextnano_raw/`. Override the location with `--raw-root DIR` or
`NEXTNANO_RAW_ROOT`.

| Run | Role |
|---|---|
| `D020_2026-08-20_sb-case04-graded-300K` | single-band k = 0 anchors, envelopes and band edges (required) |
| `D023_2026-09-04_kp8-disp-k0p10pia-n301-300K` | 8-band dispersion to the **control k_max = 0.1·π/a** (required) |
| `D023_2026-09-04_kp8-disp-k0p125pia-n301-300K` | optional 30F extension and tail check |

If a run is missing, the demo stops and says which run to download or re-register, and
where. These runs are byte-identical copies of tracked historical data, re-registered with
`nextnano/scripts/raw_data.py register` (see `inputs/registration/`).

## Where do I find…?

| What | Where |
|---|---|
| Approved plan and decisions | [PLAN.md](PLAN.md) |
| Findings, tables, validation map | [RESULTS.md](RESULTS.md) |
| Copied code and data, with hashes | [PROVENANCE.md](PROVENANCE.md) |
| Papers and equations used | [SOURCES.md](SOURCES.md) |
| Every constant, with its source | [config/demo30.json](config/demo30.json) |
| χ(2) control (Eq. 2, unchanged) | `demo30/equation2.py` (copied), `demo30/baseline.py`, `outputs/30B_chi2_baseline/` |
| χ(1) construction and prefactor derivation | `demo30/chi1.py` |
| α_E / α_I, sign convention | `demo30/absorption.py` |
| Expanded bound-state set | `demo30/bound_states.py` |
| 1994 Eq. 5 propagation | `demo30/propagation.py`, `outputs/30D_propagation/` |
| Fig. 2d comparison | `demo30/comparison.py`, `outputs/30E_paper_comparison/` |
| Measured Fig. 2d points | `reference/paper_fig2d_measured.csv`, `reference/FIG2D_DIGITIZATION.md`, `scripts/digitize_fig2d_measured.py` |
| k extension (0.125·π/a now; 0.2·π/a later) | `demo30/extension.py`, `outputs/30F_k_extension/`, [work_laptop/README.md](work_laptop/README.md) |
| Headline numbers | `outputs/summary.json` |
| Isolation audit report | `outputs/isolation_audit.json` |

## Figures

| File | Question it answers | Kind |
|---|---|---|
| `plots/30A_fig2d_digitization_overlay.png` | Are the digitized measured points right? | check |
| `plots/30B_chi2_vs_paper_simulation.png` | Does the control reproduce Demo 28A and 28J? | required |
| `plots/30C_absorption_coefficients.png` | How strongly are ω and 2ω absorbed, compared with the sample thicknesses? | required |
| `plots/30D_absorption_factor.png` | How much does absorption suppress the SH, by wavelength and thickness? | required |
| `plots/30E_fig2d_comparison.png` | Do transparent vs absorption-aware SH predictions match the measured Fig. 2d? | **main result** |
| `plots/30C_diagnostic_chi1_re_im.png` | Where are the transitions and the cutoff edges in χ(1)? | diagnostic |

## Directory map

```text
30_absorption_study/
  README.md, PLAN.md, RESULTS.md, PROVENANCE.md, SOURCES.md, requirements.txt
  config/demo30.json            every constant
  inputs/raw_data.lock.json     exact raw runs + hashes
  inputs/registration/          RUN_RECORD metadata used to register them
  reference/                    copied Demo 28 references + new Fig. 2d digitization
  demo30/                       the package (unique name; copies of Demo 28 modules + new physics)
  scripts/                      run_demo30.py, audit_isolation.py, digitize_fig2d_measured.py
  work_laptop/                  optional 0.2·π/a run: decks, kmax_run.py, README
  outputs/                      30A-30F results (CSV/JSON), summary.json
  plots/                        the figure set
  tests/                        pytest suite
```

Related: [Demo 31](../31_multilayer_shg_propagation_study/README.md) is reserved for the
multilayer, phase-mismatch and standing-wave optics that Demo 30 deliberately leaves out.
The canonical workflow is [`nextnano/docs/DEMO_WORKFLOW.md`](../../docs/DEMO_WORKFLOW.md).
