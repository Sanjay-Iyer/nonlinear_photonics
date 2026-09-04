# 00 — Baseline

## Hypothesis

Freeze the current results before changing any physics or arithmetic. Every
later experiment must start from these same cached licensed states and be
compared to these curves.

## Exact change

None. Demo 21's parabolic spectrum is evaluated by the trusted production
function. The hybrid curve replaces only the finite-k dispersion with the four
polynomials from `8_band_non_parabolic_v2.py`; it uses the same Demo 21 energies,
matrix elements, broadening and Eq. 2 normalization.

The script checks the reconstructed Demo 21 complex spectrum against all 401
stored values from 1400–1800 nm. Maximum allowed disagreement is
`1e-11 pm/V`; the run passed.

## Quantitative result

| Curve | minimum 550–650 nm | normalized depth | minimum 1200–1400 nm | normalized depth | dominant peak | normalized RMSE vs paper |
|---|---:|---:|---:|---:|---:|---:|
| Paper | 605 nm | 0 | 1330 nm | 0 | 1520 nm | 0 |
| Demo 21 parabolic | 550 nm (window boundary) | 0.0451 | 1200 nm (window boundary) | 0.2797 | 1502 nm | 0.2912 |
| Hybrid non-parabolic | 584 nm | 0.2545 | 1269 nm | 0.5028 | 1045 nm | 0.2038 |

The boundary minima for Demo 21 mean it does not form an internal node in
either diagnostic window. The hybrid improves the full-spectrum normalized
RMSE by about 30%, but it fills both paper nodes substantially and moves the
dominant peak from the paper's 1520 nm to 1045 nm.

## Interpretation

Non-parabolic dispersion changes the shape significantly and gives a better
global error metric, but it does not solve the defining node problem. Matching
resonance regions is not sufficient: the coherent cancellations remain wrong
or are being hidden by the chosen observable.

## Decision

**KEEP as immutable reference.** Do not modify or overwrite these outputs.

## Files

- `00_full_spectrum.png`: normalized shape comparison.
- `00_raw_spectrum.png`: raw Eq. 2 values, including an expanded calculated-scale panel.
- `baseline_spectra.csv`: complex and magnitude spectra at every wavelength.
- `baseline_metrics.csv`: node, peak and normalized-error metrics.

