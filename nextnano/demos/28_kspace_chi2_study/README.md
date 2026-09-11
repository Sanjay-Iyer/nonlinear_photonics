# Demo 28 — traceable complex susceptibility and k-space audit

This package continues the historical calculation; it does not redesign its physics to fit the paper.

1. **nextnano input:** the structure and electronic-structure calculation live in `nextnano/inputs/`.
2. **Raw output:** cached files directly produced by Professional live in `nextnano/raw_results/` (extended data separately).
3. **Input construction:** Python parses energies and envelopes, builds overlaps and position matrices, and aligns dispersion shifts to historical energy anchors.
4. **Equation 2:** one implementation in `chi2/equation2.py` keeps all 16 complex pathways.
5. **k integration:** `chi2/k_integration.py` provides explicit radial trapezoidal weights; cutoffs select existing solved nodes only.
6. **Re and Im:** extracted after the complex sum, not before. Absolute magnitudes are additional outputs, not replacements.
7. **Studies:** 28A is the regression anchor; 28B–28J investigate its behavior and limitations using shared physics.

No Professional solve was launched on the home laptop. All executed physics uses cached results. Copy this entire directory, including its raw datasets and `validation/`, to reproduce it without any previous demo folder.

## Start here

For the **new 28K/28L/28M Professional acquisition**, use
[WORK_LAPTOP_8BAND_RUN.md](WORK_LAPTOP_8BAND_RUN.md) and
[TRANSFER_BACK.md](TRANSFER_BACK.md). This extension requests 1201 finite-k
8-band points through 0.20 pi/a; it does not replace or rerun 28A–28J.
Acquisition preflight passes, but Professional output coverage and the reviewed
8-band-to-Equation-2 optical mapping remain pending. No new physics results exist.

From this directory, with Python 3.10+ and the packages in `requirements.txt` installed:

```powershell
python -m pip install -r requirements.txt
python scripts/calculate_chi2.py
python scripts/run_kspace_sweep.py
python studies/28C_extended_k/run.py
python scripts/run_numerical_audit.py
python scripts/run_response_audit.py
python scripts/run_causality_audit.py
python scripts/run_state_audit.py
python scripts/run_state_audit.py --input nextnano/raw_extended --output outputs/28I_state_character/extended
python -m pytest tests -q -p no:cacheprovider
python -I scripts/audit_dependencies.py
```

Run A/B before the numerical audits and output-validation tests. The `-I` dependency audit uses isolated Python startup and blocks access to historical demo folders during A/B execution. Installing dependencies requires an appropriate Python environment; it does not install nextnano or its license.

The optional `scripts/run_nextnano.py` defaults to preflight. Do not use `--run` on this laptop. See `WORK_LAPTOP_RUN.md` for the separate licensed-machine workflow.

## Directory map

```text
28_kspace_chi2_study/
  README.md, PHYSICS_GUIDE.md, DATA_LINEAGE.md
  RESULTS.md, BOSS_QUESTIONS.md, NEXT_QUESTIONS.md
  SOURCE_AUDIT.md, PAPER_AUDIT.md, CAUSALITY_AUDIT.md
  RESPONSE_AUDIT.md, STATE_AUDIT.md, WORK_LAPTOP_RUN.md
  config/                 baseline, cutoffs and audit parameters
  nextnano/
    inputs/               reproducible baseline input decks
    raw_results/          baseline + independent grid-density raw datasets
    raw_extended/         separately identified extended-k raw dataset
  chi2/                   shared parser, input builder, Eq2, weights, audits
  scripts/                small runnable entry points
  studies/                study-specific navigation / launchers
  validation/             vendored historical regression and paper data
  outputs/
    28A_baseline/          parsed_data → chi2_inputs → chi2_results → plots
    28B_kspace_cutoff/     each cutoff + cumulative/shell diagnostics
    28C_extended_k/       cached extension, validity caveats
    28D_imaginary_source/
    28E_linewidth/
    28F_causality/
    28G_pathways/
    28H_grid_convergence/
    28I_state_character/
    28J_paper_comparison/
    dependency_audit/
  tests/
```

## Where do I find…?

All paths below are relative to this directory; no previous-demo path is required at runtime.

| Quantity or stage | Exact location |
|---|---|
| Baseline 8-band input | `nextnano/inputs/kp8_dispersion.in` |
| Historical single-band input | `nextnano/inputs/singleband_case04_graded.in` |
| Professional raw files | `nextnano/raw_results/kp8/`, `nextnano/raw_results/singleband_case04_graded/` |
| Raw-file details | `nextnano/README.md`; every study's `raw_manifest.json` hashes |
| Parser | `chi2/parse_nextnano.py` |
| Parsed energies and normalized wavefunctions | `outputs/28A_baseline/parsed_data/` |
| Derived energies | `outputs/28A_baseline/chi2_inputs/electron_energies.csv`, `hole_energies.csv`, `transition_energies.csv` |
| Overlap and z matrices | `outputs/28A_baseline/chi2_inputs/overlap_eh.npy`, `z_e.npy`, `z_h.npy` |
| Input builder | `chi2/input_builder.py::build_inputs` |
| Wavefunction integrals | `chi2/matrix_elements.py::from_envelopes` |
| Equation 2 | `chi2/equation2.py::calculate_chi2`; products in `pathway_definitions` |
| k weights and cutoff selection | `chi2/k_integration.py::radial_weights`, `select_range` |
| Saved k and weights | `outputs/28A_baseline/chi2_inputs/k_per_nm.csv` |
| Complex/Re/Im/absolute spectra | `outputs/28A_baseline/chi2_results/chi2_spectrum.csv` |
| Per-k integrand and all pathways | `outputs/28A_baseline/chi2_results/chi2_k_lambda_integrand.npz`, `pathways.npz` |
| Clean baseline Re/Im | `outputs/28A_baseline/plots/28A_real.png`, `28A_imag.png` |
| Clean selected-cutoff Re/Im | `outputs/28B_kspace_cutoff/plots/28B_real_selected.png`, `28B_imag_selected.png` |
| Cumulative and shell response | `outputs/28B_kspace_cutoff/cumulative_and_shells.csv` and `plots/28B_real_cumulative.png`, `28B_imag_cumulative.png` |
| Paper comparison | `outputs/28J_paper_comparison/` |
| Configuration | `config/baseline.json`, `config/kspace_sweeps.json`, other named audit JSON files |
| Provenance and checks | each output's `metadata.json`, `raw_manifest.json`, `code_manifest.json` or documented relative reference |
| Meeting explanations | `PHYSICS_GUIDE.md`, `BOSS_QUESTIONS.md` |

## Change the k cutoffs

Edit `config/kspace_sweeps.json`:

```json
"k_cutoffs_pi_over_a": [0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.10],
"selected_cutoffs_pi_over_a": [0.01,0.04,0.07,0.10]
```

Then run `python scripts/run_kspace_sweep.py`. Values mean **f times pi/a**, with a = 0.565325 nm, not an independently established geometric fraction of the paper's BZ. Full baseline kmax is 0.555714439232 nm^-1. Values above the available dataset are rejected. Between samples, the last included native node lies below the request; metadata records both values. Weights are recomputed after selection.

Use a new output directory when changing configuration (`--output ...`) so older cases cannot be confused with the new sweep. `run_numerical_audit.py` compares the default A/B output locations; its paper comparison reads only cases explicitly listed by the current sweep metadata.

`config/baseline.json` controls gamma, state-independent prefactor constants and wavelength grid. Changing it intentionally breaks the historical 28A regression gate; create a labeled investigation configuration rather than claiming a changed baseline still reproduces the old result. States and matrix treatment are fixed in the current historical input builder; future alternatives belong in a separately labeled builder, not silent edits to Eq2.

## What this baseline actually is

It is a **mixed-model historical reproduction**: 8-band dispersion shifts, single-band k=0 energies and matrix elements, frozen matrices versus k, fixed solver column pairs. It is not a new, fully self-consistent 8-band optical calculation. One historical valence pair is LH-dominated. Reproducing the reference establishes numerical continuity, not correctness of every physical approximation.

The older plot with nRMSE about 0.066 used a different extrapolated cutoff diagnostic. Here the native-data baseline has nRMSE **0.237873 for |Re|** and **0.262391 for |chi|**. Do not conflate these models. See `SOURCE_AUDIT.md`.

Future questions can add a study/configuration and call the same input builder, `calculate_chi2`, saved-input routines and diagnostics. There is no need to copy the Equation 2 loop.
