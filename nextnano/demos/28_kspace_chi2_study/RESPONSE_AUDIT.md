# 28D / 28E / 28G: imaginary response, linewidth and pathways

These are controlled diagnostics of the **historical mixed-model baseline**, not
a new eight-band-only calculation or an absorption measurement. They use the same
301 cached k samples and frozen single-band matrices as 28A. The retained second
valence branch is LH-dominated in the cached eight-band data: reproducing the old
spectrum does not establish a faithful two-HH-state model.

## Run and configure

From this Demo 28 directory, with the dependencies in `requirements.txt` installed:

```powershell
python scripts/run_response_audit.py
python -m pytest tests/test_response_audit.py -q
```

No nextnano process is launched. `--input PATH` selects another compatible raw
dataset; `--output PATH` selects the parent directory for the three study outputs.
`--no-plots` preserves all numerical calculations. Changing the model/state
selection is not implemented by this command. D5 deliberately rejects complex
matrix inputs rather than silently stripping arbitrary wavefunction phases.

Edit `config/response_audit.json`:

- `gamma_meV`: all linewidth cases; 0.1, 0.5, 1, 2, 5, 10, 20 meV here.
- `selected_gamma_meV`: four clean meeting curves; 1, 2, 5, 20 meV here.
- `near_resonance_detuning_meV` / `off_resonance_detuning_meV`: fixed 25 / 100 meV windows.
- `ratio_real_floor_fraction`: mask `|Re| <= 0.001 max|Re|` before forming a ratio.
- `feature_wavelengths_nm`: requested wavelength probes. Measured prominent
  absolute-component peaks are additionally included in pathway ranking.
- `top_pathways`: number displayed, not number calculated. All 16 are calculated.
- `baseline_config`: wavelength grid, raw source and physical settings.

The only susceptibility evaluator is `chi2/equation2.py::calculate_chi2`.
Its `pathway_definitions` helper supplies the numerator and transition arrays to
both the evaluator and these diagnostics. `chi2/response_audit.py` does not contain
a second implementation of the Equation 2 susceptibility.

## 28D: where the imaginary component comes from

For this dataset, the largest imaginary part of each overlap/z matrix and each
complete pathway numerator is **exactly zero**. Evaluating the real-matrix
representation against the complex-dtype representation changes the final
complex spectrum by **0 pm/V**. Because the invariant products are already real,
this D5 test is a consistency control, not a new approximation.

The imaginary component therefore enters through the `i*Gamma` denominators and
is then added/cancelled between pathways. No time-dependent carrier population is
calculated in this workflow. Initial occupation assumptions in a perturbative
response formula are different from propagating photoexcited populations. The
paper's occupation assumption and the Fourier/causality convention are discussed
in the main physics/paper audit; this numerical result by itself does not identify
`Im chi2` with a measured nonlinear absorption coefficient.

At Gamma = 5 meV:

| Quantity | Result |
|---|---:|
| Largest imaginary invariant numerator | 0 nm |
| Full versus real-matrix representation spectrum error | 0 pm/V |
| Electron + hole versus total spectrum error | 3.39e-13 pm/V |
| max absolute electron-group Im | 888.029 pm/V |
| max absolute hole-group Im | 831.540 pm/V |
| max absolute total Im | 57.898 pm/V |

The maxima in the last three rows need not occur at identical wavelengths and
must not be subtracted as though they did. The CSV contains the actual pointwise
sum. These are decomposition terms, not separately measurable susceptibilities.
In particular a common shift of the z coordinate changes individual diagonal-z
terms and electron/hole groups but cancels from the total. An automated test
checks this origin invariance. Arbitrary wavefunction phase must likewise not be
interpreted as a physical imaginary contribution; the complete products matter.

Start with `outputs/28D_imaginary_source/plots/28D_imag_electron_hole.png` and the
separate `28D_real_electron_hole.png`. The small total between two large opposite
curves makes the cancellation explicit; no normalization was applied.

## 28E: resonance windows and Gamma sensitivity

For each fundamental wavelength, compute

`min_(n,m,k,p=1,2) |E_e,n(k) - E_h,m(k) - p*hc/lambda|`.

This uses the actual discrete transition energies, not paper peak locations.
Near resonance means this minimum is <=25 meV. Off resonance means >=100 meV.
The intervening region is excluded from both classifications. These masks remain
fixed across Gamma so the comparison does not move its goalposts as Gamma changes.
The domain is 400–1850 nm on a uniform 1 nm wavelength grid: 500 near samples,
736 off samples and 215 intermediate samples. Results are thus specific to these
windows and wavelength sampling, not universal fractions of all frequencies.

At 5 meV the off-resonance L2 ratio `||Im||/||Re||` is **0.014384** and every
off-resonance sample has `|Re|>|Im|`. Near resonance the L2 ratio is **1.15586**,
but only **35.4%** of near-window samples have `|Im|>|Re|`; the safe pointwise
median ratio is **0.12250**. Large near-resonance Im dominates the L2 norm without
dominating every point. The two-denominator, many-pathway response should not be
reduced to the rule “Im always dominates near every resonance.”

At 0.1 meV the off-resonance L2 ratio decreases to **0.000287816**, approximately
50 times smaller than at 5 meV. This is evidence that the smooth off-resonance Im
comes from broadening. It is **not** evidence that the entire resonant imaginary
response vanishes in a converged Gamma-to-zero limit.

| Gamma (meV) | max absolute Re (pm/V) | max absolute Im (pm/V) | off L2 Im/Re |
|---:|---:|---:|---:|
| 0.1 | 138.360 | 188.891 | 0.000288 |
| 0.5 | 130.261 | 85.439 | 0.001439 |
| 1 | 116.315 | 77.185 | 0.002878 |
| 2 | 97.148 | 68.572 | 0.005756 |
| 5 | 71.311 | 57.898 | 0.014384 |
| 10 | 54.176 | 51.792 | 0.028729 |
| 20 | 39.975 | 47.121 | 0.057150 |

**Grid limitation:** tiny Gamma produces spikes and many extra detected zero
crossings on the unchanged 301-point k / 1 nm wavelength grids. The 0.1 meV
dominant Im maximum moves to 1375 nm; do not interpret that as a converged physical
peak shift. The 0.5 meV case still has extra small oscillatory zero crossings.
Grid and spectral refinement are required before interpreting narrow-linewidth
peaks. The complete sweep retains them transparently; meeting plots use 1,2,5,20
meV and avoid the visibly unresolved 0.1 meV case.

`gamma_summary.csv` saves dominant sampled absolute-component maxima, zero
locations, and apparent half-prominence lobe widths. These widths describe the
*integrated spectral lobe*, not a fit of the homogeneous denominator linewidth.
For example Gamma=5 meV gives Re/Im lobe widths 32.904/131.928 nm; neither can be
directly converted to a carrier lifetime. Dominant peaks may switch branches:
10 meV Im is largest at 1413 nm; 20 meV Re at 1372 nm. No connected peak-tracking
plot falsely identifies those maxima as a continuous physical branch.

Clean figures: `outputs/28E_linewidth/plots/28E_real_gamma_selected.png`,
`28E_imag_gamma_selected.png`, and `28E_ratio_selected.png`. Full sweeps are saved
as `28E_real_gamma_sweep.png` and `28E_imag_gamma_sweep.png`. Ratio gaps are masked
near Re=0, not clipped to invented finite values. The horizontal ratio=1 line is
the component-equality threshold.

## 28G: pathways and resonances

Labels `C_m1_n2_l2` and `V_m1_n2_l2` use one-based indices. C is the electron
intersubband term; V is the valence term including its minus sign. In C, diagonal
z means n=ell; in V it means m=ell. All 16 are retained in the output NPZ and CSV.

The largest individual pathways by wavelength-grid complex L2 norm are
`C_m1_n1_l1`, `V_m1_n1_l1`, `C_m2_n2_l2`, `V_m2_n2_l2`. However ranking individual
magnitudes is not ranking net feature creation: the first pair cancels almost
completely. The norm cancellation measure is

`1 - ||sum_j chi_j||_2 / sum_j ||chi_j||_2`.

It is not an absorbed-power fraction, and its value depends on the spectral
window and coordinate convention for individual terms.

- All 16 terms: 97.1914% cancellation by this measure.
- C111/V111: 99.7118% cancellation; residual L2 = 78.481 pm/V.
- C222/V222: 81.1061% cancellation; residual L2 = 877.148 pm/V.
- A tiny C_m2_n1_l1 / V_m2_n1_l2 pair cancels 99.9779%, but its individual norm
  sum is only 6.518 pm/V. A large percentage alone does not imply significance.
- Sum of diagonal-z terms has L2 norm 1.02934 times the total.
- Sum of off-diagonal-z terms has L2 norm 0.147682 times the total, so it is
  smaller but not negligible. These ratios need not add to one because the
  complex terms interfere.

Thus diagonal terms dominate this baseline and substantial cancellation is
present, but off-diagonal terms affect residual features. Do not claim all
off-diagonal terms cancel exactly or that the individual C111 magnitude alone
explains the final peak. `feature_pathway_ranking.csv` gives all 16 contributions
at the configured probes and measured peaks; `pairwise_cancellation.csv` covers
all 120 pairs, including weak pairs.

The resonance map uses `lambda=hc/E_nm(k)` (one-photon denominator) and
`lambda=2hc/E_nm(k)` (two-photon denominator). These are exact locations of
minimum denominator magnitude at fixed k for the stated finite constant Gamma;
they are not guaranteed maxima of the summed susceptibility. All four transition
tracks move toward shorter fundamental wavelength as k increases. For example,
e1-h1 two-photon resonance moves from 1660.481 to 1479.314 nm over the available
k range. Adding k therefore adds new resonant regions, while cancellation and
the radial measure determine how the final maximum responds.

Use `outputs/28G_pathways/plots/28G_resonance_map.png` for this explanation.
`28G_real_diagonal.png` / `28G_imag_diagonal.png` show the net effect clearly.
The top-pathway figures show only four individual terms, never an unreadable
16-line overlay. Every plot also has a matching SVG.

## Saved output and provenance

| Location | Contents |
|---|---|
| 28D `parsed_data/`, `chi2_inputs/` | Parsed raw data and saved energies, matrices, weights, before Eq2 |
| 28D `baseline/` | Full spectrum, all pathways, unweighted per-k integrand |
| 28D `real_numerators/` | D5 real-input representation control |
| 28D `electron_hole_total.csv` | Pointwise signed group and total spectra |
| 28E `cases/gamma_*_meV/` | Complete complex spectra/pathways, safe ratios, masks, feature metadata |
| 28E `gamma_summary.csv` | Peak, zero, lobe-width and near/off comparison table |
| 28G `numerators.npz` | All numerator and one/two-transition arrays, labels and actual k |
| 28G `pathway_table.csv` | Indices, diagonal flag, numerator ranges, denominator structure, amplitudes |
| 28G `pathway_spectra.csv` | Re/Im of all 16 contributions over wavelength |
| 28G `resonance_map.csv` | Actual energy and one/two-photon resonance for every transition/k |
| Each `metadata.json` | Config, source, units, settings, hashes, timestamp and caveats |

E/G metadata intentionally references the existing D raw/code manifests and
shared saved inputs with explicit relative paths. Production imports remain
inside this Demo 28 package; old demo names describe provenance/model identity,
not runtime imports.

## Validation and visual review

`tests/test_response_audit.py`: **11 PASS, 0 FAIL** on the cached dataset. Tests
cover pathway shapes, electron/hole summation, common-origin cancellation,
small-Gamma off-resonance trend, ratio masking, one/two-photon windows, the
cancellation metric, edge-width handling, configuration and manifest paths.

All 12 generated PNGs were individually opened and inspected: separate signed
components, clean axes, no clipped legends, and matching SVG output. The complete
Gamma sweep is intentionally noisy at 0.1 meV; this is documented numerical
underresolution rather than hidden by smoothing or removing the case.
