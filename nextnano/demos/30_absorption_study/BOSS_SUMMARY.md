# Demo 30: can absorption explain the Fig. 2d resonance mismatch?

**Answer: no.**

- In the 80-period sample, absorption removes about half of the second-harmonic (SH)
  intensity.
- It does so almost uniformly across the resonance.
- The calculated SH peak stays at ≈ 1503 nm with or without absorption. The measured peak
  is at ≈ 1560 nm.

![Absorption lowers the SH signal but does not move the calculated resonance](plots/30_boss_absorption_comparison.png)

## Question

Does adding absorption move the calculated wavelength dependence of the SHG response
toward the measured Fig. 2d result (Ramesh et al., arXiv:2602.23246, 80-period sample)?

## Model

This is **not** a pure full-8-band optical calculation. It uses the existing mixed Demo 28
model:

- 8-band k·p gives the in-plane dispersion E(k∥);
- a single-band k = 0 calculation gives the wavefunctions, overlaps and matrix elements,
  which stay frozen at their k = 0 values.

The primary model has 2 conduction × 2 heavy-hole states, Γ = 5 meV, control cutoff
k ≤ 0.1·π/a, and 300 K. The sample is 80 periods × 30 nm = 2.4 µm.

## Method

1. The paper's Eq. 2 gives χ(2). The existing code is unchanged.
2. The same states, energies and Γ give the linear susceptibility χ(1).
3. Im χ(1) gives the linear absorption.
4. Absorption is calculated at the fundamental (ω) and at the second harmonic (2ω).
5. The 1994 Almogy–Yariv equation for SHG in an absorbing medium (Opt. Lett. 19, 1828,
   Eq. 5) gives the SH intensity leaving the 2.4 µm stack.
6. The SH spectra without and with absorption are compared with the measured Fig. 2d
   points. Only the shapes are compared, because the measured data are in arbitrary units.

Nothing was fitted to Fig. 2d, and no new nextnano run was needed.

## Results

| Quantity | Result |
|---|---|
| No-absorption peak | ≈ 1503 nm |
| With-absorption peak | ≈ 1503–1504 nm |
| Measured peak | ≈ 1560 nm (points every 10 nm) |
| SH absorption at 1550 nm | ≈ 6.7–7.3 × 10³ cm⁻¹, depending on the model variant |
| 80-period SH intensity remaining at 1550 nm | ≈ 47 % (44–47 % across variants) |
| Fundamental absorption | negligible: ≈ 2–22 cm⁻¹, < 1 % pump loss over 2.4 µm |
| nRMSE against the measured shape (lower is better) | 0.659 → 0.627 at best (0.648 for the primary model) |

- **Absorption matters for the magnitude.**
  - In the 80-period sample, about half of the SH is absorbed.
  - Thinner samples lose much less. At 1550 nm, 96 %, 89 % and 85 % of the SH remains
    for 4, 12 and 16 periods.
- **It does not move the peak.** Absorption changes only slowly across the narrow
  calculated resonance. The peak moves by 0–1 nm and stays about 57 nm short of the
  measured peak.
- **The shape agreement barely improves.** The nRMSE falls only from 0.659 to 0.627, and
  the correlation with the measured points stays negative (−0.36 → −0.31).
- **The paper's own χ(2) gives the same answer.** The paper's simulated χ(2) peaks at
  ≈ 1520 nm, and applying our absorption to it shifts that peak by 0 nm. This check is
  illustrative only, because it mixes the two calculations.

## Conclusion

Absorption is important for the magnitude of the generated second harmonic, especially
for the 80-period sample, but it does not significantly shift the resonance. Therefore,
absorption alone does not explain the wavelength mismatch between the calculation and
the measurement.

## Next question: Demo 31

The next logical study is **Demo 31**, which adds phase mismatch, standing waves and
multilayer optical propagation.

*This is motivation for Demo 31, not a Demo 30 result.* Demo 30's simple
background-index estimate suggests phase mismatch could be important:

- At 1550 nm the coherence length is ≈ 1.6 µm, shorter than the 2.4 µm stack.
- For a transparent, uniform slab, that alone would reduce the SH to ≈ 10 % of its
  phase-matched value.
- Demo 30 did not apply this factor to any result.

Also, the paper's own simulated χ(2) peaks at ≈ 1520 nm, not 1560 nm, so part of the gap
already exists in the paper's calculation.

## Limits

- **Mixed model.** The matrix elements are frozen at k = 0 (see Model).
- **Absorption strength.** The absolute value is uncertain by up to about 2×, because of
  the matrix-element convention and because excitons, light holes and the continuum are
  not included. This changes how much SH is lost, not where the peak is: all four
  absorption variants peak at 1503–1504 nm.
- **Uniform slab at normal incidence.** Reflections, standing waves, phase mismatch and
  bulk SH are not included; they are Demo 31.
- **Period and temperature.** The period is 30 nm, taken from the layer stack (the paper's
  text says 20 nm). Only 300 K was calculated.

## Where the numbers come from

- **Saved outputs.** Every value comes from saved, validated Demo 30 outputs. Every stage
  passes, and `scripts/run_demo30.py --check-stale` confirms the outputs are current.
- **Source files.**
  - Table: `outputs/summary.json`.
  - Peaks and nRMSE: `outputs/30E_paper_comparison/`.
  - SH fraction remaining (|A|²): `outputs/30D_propagation/`.
- **nRMSE.** The root-mean-square difference between the peak-normalized calculated and
  measured curves, at the 10 measured wavelengths between 1500 and 1800 nm.
- **Figure.** `presentation/make_boss_figure.py` draws it from those outputs.
  `outputs/` and `plots/` are local and not tracked in Git.
- **Full details.** [RESULTS.md](RESULTS.md).
