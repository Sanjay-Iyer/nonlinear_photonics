# 01 — Complex components

## Hypothesis

The paper may show a signed component such as Re(χ²), while the repository has
been comparing the paper against |χ²|. Re(χ²) can cross zero even when |χ²|
does not, because Im(χ²) remains finite.

## Exact change

No physics and no arithmetic were changed. The calculation remains complex
through the complete 16-term sum and k integration. This experiment exposes
Re(χ²), Im(χ²), |χ²| and phase before the existing final magnitude operation.

## Quantitative result

### Demo 21 parabolic

- No Re(χ²) crossing occurs in 550–650 nm.
- Re(χ²) crosses at **1394.57 nm**, not at the paper's approximately 1330 nm node.
- At that crossing Im(χ²) is **−30.49 pm/V**, leaving |χ²| at **0.6760** of the
  full-spectrum peak.
- Using |Re(χ²)| instead of |χ²| reduces normalized paper RMSE from **0.2912 to
  0.2126**, but does not produce the first paper node.

### Hybrid non-parabolic

- Re(χ²) crosses at **577.37 nm** and **1268.10 nm**.
- At 577.37 nm, Im(χ²) is **+23.90 pm/V**, leaving |χ²| at **0.2548** of its peak.
- At 1268.10 nm, Im(χ²) is **−47.17 pm/V**, leaving |χ²| at **0.5029** of its peak.
- Using |Re(χ²)| reduces normalized paper RMSE from **0.2038 to 0.1126**.
- The crossings are displaced from the paper nodes at approximately 605 and
  1330 nm.

Neither model shows an abrupt per-nanometre phase jump at the two paper nodes.
The maximum phase steps are 6.65°/3.33° for Demo 21 and 0.98°/0.20° for the
hybrid in the first/second diagnostic windows. The phase still evolves over
each window, but the complex trajectory does not pass close to the origin.

## Interpretation

This is an **IMPORTANT finding**, not yet a confirmed bug. The hybrid algebra
is capable of signed real-part cancellation, and |Re(χ²)| resembles the paper
substantially better than |χ²|. However, the imaginary component fills both
zeros, and the crossing wavelengths remain wrong. We must confirm from the
paper's plotted observable whether it reports magnitude, a real tensor
component, or another convention before changing the official comparison.

The trusted production implementation retains complex amplitudes through the
term and k sums and applies `np.abs` only through its final magnitude property.
That is preliminary evidence against an early-absolute-value bug; Experiment 02
will test all alternative orderings explicitly.

## Decision

**KEEP the diagnostic; do not change the official observable yet.** Proceed to
the controlled absolute-value-ordering experiment.

## Files

- `01_complex_full_spectrum.png`: Re, Im and magnitude for both models.
- `01_real_vs_paper.png`: signed real components versus the normalized paper curve.
- `01_zoom_600nm.png`, `01_zoom_1330nm.png`: node-region diagnostics.
- `01_phase.png`: principal complex phase.
- `complex_components.csv`: complex values and phase at every wavelength.
- `complex_metrics.csv`: crossings, residual magnitudes, phase motion and errors.

