# Demo 31 — draft plan (not approved, not started)

This is a starting point for a later review. Nothing here is implemented.

## Proposed sub-studies

| ID | Content |
|---|---|
| 31A | **Sample stack.** Reconstruct each measured sample (4, 12, 16 and 80 periods; controls) from the 2026 paper (Fig. 3c inset, Methods 5.2): sapphire / epoxy / GaAs cap 10 nm / MQW / bulk Al0.55Ga0.45As layer. List every unknown thickness explicitly. |
| 31B | **Optical constants.** Complex n(λ) at ω and 2ω for every layer, with sources. The MQW layer uses Demo 30's background index plus χ(1) (copied, not imported). |
| 31C | **Fields.** Transfer-matrix fields at ω and 2ω, for oblique p polarization at 45°, with E_x and E_z inside each layer. |
| 31D | **SH signal.** The reciprocity overlap SH ∝ \|Σ χ ∫ E(2ω)(E(ω))² dv\|² (2026 Eq. 3) with Demo 30's χ(2)_xzx, and bulk GaAs/AlGaAs terms as a switchable option. |
| 31E | **Limits.** The homogeneous, reflection-free, phase-matched limit must reproduce Demo 30's A (1994 Eq. 5). A transparent thin film must scale as L². Adding Δk alone must give the sinc² behavior. |
| 31F | **Comparison.** Compare with Fig. 2d (80 periods) and with the paper's χ_eff at 1550 nm (Fig. 3c). No fitting to force agreement. |

## Open questions to settle before 31A

- The thicknesses of the bulk AlGaAs layer and the epoxy. The paper gives the layer order
  and relative sample thicknesses but no numbers for these.
- Whether the paper's simulated field profiles included the MQW absorption. This matters
  for the absolute χ_eff comparison.
- The detected polarization and collection geometry (p-out, transmission, 45° incidence)
  for the wavelength scan in Fig. 2d.
- Whether "Normalized SH Intensity" in Fig. 2d is divided by the fundamental power squared,
  and what that implies for the ω² factor.
