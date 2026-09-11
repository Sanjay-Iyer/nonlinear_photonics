# 28F: what the Kramers-Kronig check establishes

## Short answer

The numerical full-frequency dispersion test **passes for the implemented rational Equation 2**, using the Fourier convention consistent with `+iGamma`. It does **not** certify that Equation 2, continued unchanged to every negative and positive frequency, is the complete real-field material response. That continuation fails the separate real-field conjugation-symmetry test. The physical completeness conclusion is **INCONCLUSIVE**, not “nonlinear absorption validated” and not “the paper is acausal.”

No licensed nextnano calculation was run. This is an audit of the existing 301-point cached-data model. Its very broad energy domain is a mathematical test of the formula, not a claim that the two-state electronic model describes this material up to 32 eV.

## Why a one-dimensional relation is legitimate here

Write the retarded second-order response in terms of delays from the output time:

\[
P^{(2)}(t)=\int_0^\infty\!d\tau_1\int_0^\infty\!d\tau_2\,
R^{(2)}(\tau_1,\tau_2)E(t-\tau_1)E(t-\tau_2).
\]

For fields reconstructed with `exp(+i omega t)`, the degenerate-frequency response is

\[
F(E)=\chi^{(2)}(-2\omega;\omega,\omega)
=\int_0^\infty\!d\tau_1\int_0^\infty\!d\tau_2\,
R^{(2)}(\tau_1,\tau_2)e^{-iE(\tau_1+\tau_2)/\hbar},\quad E=\hbar\omega.
\]

Both input frequencies move in the same direction. Positive delays make this analytic in the **lower** complex-energy half-plane, provided the kernel has the required stability/integrability. The `-2omega` in the three-frequency bookkeeping notation is the output-frequency constraint, not an independent negative input direction. This reasoning does not extend automatically to mixed-sign paths such as optical rectification. Lucarini's harmonic-generation analysis establishes the same-direction condition and distinguishes it from general nonlinear frequency paths. [Lucarini, Sec. III B-C, Eqs. 13-22](https://arxiv.org/pdf/0710.0958)

For a decaying function analytic below the real axis, define

\[
H[f](E)=\frac{1}{\pi}\operatorname{PV}\int_{-\infty}^{\infty}\frac{f(E')}{E-E'}\,dE'.
\]

The tested relations are

\[
\operatorname{Re}F=H[\operatorname{Im}F],\qquad
\operatorname{Im}F=-H[\operatorname{Re}F].
\]

Energy rather than angular frequency is safe: the constant Jacobian cancels between `dE'` and the denominator. Wavelength is not a linear frequency coordinate and is **not** used for the transform. The relations above are derived with the stated sign convention; reversing the time convention reverses both Hilbert-transform signs.

## Pole/sign audit

The authoritative `chi2/equation2.py::calculate_chi2_energy` contains the same loop as the positive-wavelength calculation. Each denominator is `transition - a*E + i*Gamma` with `a=1` or `2`. Its pole is

\[
E_p=(E_{transition}+i\Gamma)/a.
\]

At positive Gamma, all poles are above the real axis; the function is analytic below it. Thus `+iGamma` is consistent with **inverse `exp(+i omega t)`** and a decaying retarded response. Under inverse `exp(-i omega t)`, the retarded convention would instead require `-iGamma`. A denominator sign alone cannot decide whether a response is causal without also stating the Fourier convention. The inspected paper specifies `+iGamma` but does not explicitly state that convention in its Eq. 2 discussion. [Ramesh et al., Methods 5.1](https://arxiv.org/html/2602.23246v1#S5.SS1)

The finite k sum has no poles in the lower half-plane, and each term decays at least as `E^-2`. This supplies a direct analytic justification for the full-line check of the **implemented expression**. We do not infer that its high-energy behavior is the complete material's high-energy behavior.

## Numerical procedure and analytic control

Run from this demo directory:

```powershell
python scripts/run_causality_audit.py
```

Parameters are in `config/causality.json`. Before evaluating the QW expression at each bandwidth, the checker tests a damped harmonic-oscillator SHG function:

\[
F_{test}(E)=\frac{1}{D(2E)D(E)^2},\qquad
D(E)=\Omega^2-E^2+i\gamma E.
\]

This independent analytic control has upper-half-plane poles, decays as `E^-6`, and obeys `F(-E)=F(E)*`. Here `Omega=1.5 eV` and `gamma=0.1 eV`; these are test parameters, not the QW linewidth. The harmonic oscillator provides an independent reference for harmonic-generation dispersion relations. [Bassani and Lucarini](https://arxiv.org/abs/physics/9812026)

The implementation uses a uniform signed-energy grid, includes both endpoints, and applies the FFT Hilbert transform with threefold total-domain zero padding. Padding reduces periodic-image contamination, but it cannot reconstruct missing spectral tails. Widths are independently increased while the step remains 0.001 eV. The central comparison is 0.65-3.2 eV; the edge region is `0.8*width <= |E| <= 0.95*width`. All spectra are computed through the one authoritative Equation 2 evaluator, including negative and zero photon energies. Negative frequencies are not manufactured by conjugating the positive-frequency curve.

## Executed results

Relative RMS means RMS(reconstruction error) divided by RMS(direct component), separately for Re and Im in the specified region. The configured central numerical threshold is 0.001 (0.1%).

| Energy interval | Points | Re central relative RMS | Im central relative RMS |
|---|---:|---:|---:|
| -8 to 8 eV | 16,001 | 1.52835e-4 | 2.14251e-4 |
| -16 to 16 eV | 32,001 | 4.01906e-5 | 2.80025e-5 |
| -32 to 32 eV | 64,001 | 1.61672e-5 | 1.33379e-5 |

At the broadest interval the analytic control's central relative RMS errors are `2.03e-13` (Re) and `1.78e-12` (Im). The model's central absolute RMS errors are `0.00018546 pm/V` and `0.00015386 pm/V`; maximum absolute errors are `0.00333566 pm/V` and `0.00209026 pm/V`. These are numerical residuals, not uncertainty in the physical model.

Edge errors must not be hidden: at +/-32 eV the edge Re relative RMS is `0.07139`, whereas the edge Im relative RMS is about `1295.54`. The latter is large because the true edge Im RMS is only `4.39e-7 pm/V`; its absolute reconstruction error is `0.00056823 pm/V`. The edge region is **not reliable**. Broadening the domain decreases absolute errors, but not necessarily relative error where the exact signal vanishes quickly. Finite grid spacing also contributes; this audit does not claim arbitrarily accurate pointwise KK reconstruction.

All four PNG plots were visually inspected; labels, legends and traces are readable. SVG versions are saved alongside them.

## Why the physical conclusion remains limited

For a complete response to real fields, a real time-domain kernel requires

\[
F(-E)=F(E)^*.
\]

The direct unchanged Eq. 2 continuation gives

```text
max |F(-E)-F(E)*| / max |F(E)| = 0.99717318
```

This is not a small bandwidth effect: the value is essentially unchanged at every bandwidth. The expression contains positive-transition resonant denominators but no explicitly mirrored negative-frequency resonances. **Inference:** it should be treated as a resonant expression/complex-envelope contribution, not automatically as the full real-field response at all frequencies. A fuller density-matrix derivation may provide the required conjugate/counter-rotating contributions. No such completion was silently added, because doing so changes the model and must be checked against the derivation.

Do not impose even Re/odd Im by hand and then apply a positive-frequency linear-optics KK formula: that would test a different function. Do not label the good central overlay as proof of measured absorption, passivity, accurate oscillator strengths, or state-truncation adequacy. In particular, signs of Im in a nonlinear susceptibility do not provide the same standalone absorption test as in a simple passive linear dielectric.

**Reportable status:** analytic checker PASS; mathematical full-line Eq. 2 KK PASS at the stated tolerance; **physical completeness INCONCLUSIVE** because the continuation fails real-field symmetry and the paper's convention/completion is unresolved. If only the existing 400-1850 nm display samples were available, the full-line reconstruction would instead be **INCONCLUSIVE DUE TO BANDWIDTH/TRUNCATION**. We explicitly evaluated a broader mathematical model here rather than pretending those display samples were sufficient.

## Files

| Item | Location relative to this demo |
|---|---|
| Configuration | `config/causality.json` |
| Checker and orchestration | `chi2/causality.py` |
| Authoritative physics consumer | `chi2/equation2.py::calculate_chi2_energy` |
| Complete signed-energy spectrum and reconstructions | `outputs/28F_causality/chi2_signed_energy.csv` |
| Every bandwidth, including analytic test | `outputs/28F_causality/kk_bandwidth_*_eV.npz` |
| Central and edge errors | `outputs/28F_causality/bandwidth_metrics.csv` |
| Settings, sign, poles, data lineage and limitations | `outputs/28F_causality/metadata.json` |
| Re reconstruction | `outputs/28F_causality/plots/28F_re_from_im_KK.png` |
| Im reconstruction | `outputs/28F_causality/plots/28F_im_from_re_KK.png` |
| Analytic checker | `outputs/28F_causality/plots/28F_analytic_checker.png` |
| Real-field symmetry failure | `outputs/28F_causality/plots/28F_reality_symmetry.png` |

The nine `tests/test_causality.py` tests passed, including both sign conventions, deliberate wrong-sign detection, nonuniform-grid rejection, bandwidth improvement, and config loading.
