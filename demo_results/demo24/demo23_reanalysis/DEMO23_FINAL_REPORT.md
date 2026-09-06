# Demo 23 final scientific report

## 1. Executive summary

Demo 23 isolates the effect of in-plane energy dispersion on the already validated 16-pathway Equation 2 calculation. No production matrix element, prefactor, broadening, geometry, wavelength grid, or k-space normalization changes between 23A–23D.

The 23A baseline regression is **PASS**: maximum complex error `4.80457733343e-13 pm/V` against tolerance `1e-09 pm/V`. The complete boss-hybrid validation is **FAIL**.

### Master mode table

| Mode | Dispersion | χ²(1550) pm/V | Peak χ² pm/V | Peak λ nm | FWHM nm | RMSE vs 23D | Normalized RMSE vs digitized paper |
|---|---|---:|---:|---:|---:|---:|---:|
| 23A | shared reduced-mass parabola | 18.0487 | 45.106 | 1502 | 270.9247 | 0.1286447 | 0.2913604 |
| 23B | four independent anchored parabolas | 25.79 | 74.06316 | 1502 | 172.1021 | 0.0167185 | 0.2766391 |
| 23C | electron parabolas + nonparabolic kp8 holes | 26.70382 | 83.04521 | 1503 | 165.9554 | 0.006741697 | 0.2589147 |
| 23D | raw/interpolated kp8 energies for all four states | 26.48225 | 81.49067 | 1503 | 166.3493 | 0 | 0.2623911 |

### Validation table

| Check | Result | Threshold | PASS/FAIL |
|---|---|---|---|
| 23A regression | 4.804577333433123e-13 | <= 1e-09 pm/V | **PASS** |
| state tracking | finite-k spinors absent; solver band columns + Kramers-pair averaging used | finite-k overlap; score >= 0.6; margin >= 0.15; no ambiguous | **FAIL** |
| e1 fit | RMSE 1.20147 meV | <= 1 meV | **FAIL** |
| e2 fit | RMSE 0.759617 meV | <= 1 meV | **PASS** |
| 23C-vs-23D spectral RMSE | 0.00674169749715477 | <= 0.01 | **PASS** |
| k-grid convergence | N=201 vs 301 | max complex relative change <= 0.001 | **FAIL** |
| kmax convergence | nominal fraction 0.1 | max complex relative change <= 0.001 | **FAIL** |
| isotropy | 11.31775702642912 | <= 1.0 meV | **FAIL** |
| interpolation bounds | 4.440892098500626e-16 | node residual <= 1e-12 eV; no extrapolation | **PASS** |
| normalization consistency | 39.47841760435743 | bare/production = (2pi)^2 = 39.4784176044 | **PASS** |

## 2. What changed relative to Demo 21

Demo 21 uses one shared parabolic transition shift. Demo 23 adds separately fitted e1/e2/hh1/hh2 parabolas, a boss-requested electron-parabola/nonparabolic-hole hybrid, and a raw-kp8 energy-only reference. The four modes are evaluated on the same k and wavelength grids.

## 3. What remained fixed

- `M(k)=M(0)` and all 16 Equation 2 pathways.
- Gamma `5 meV`; r(e,hh) `0.751 nm`.
- Nz `3.333333e+07 m^-1` (one_asymmetric_coupled_qw_period_per_30_nm).
- Spin degeneracy `2` and measure `d2k_over_2pi_squared`.
- Nominal kmax `0.5557144 nm^-1` under `k_BZ = pi/a; kmax = fraction_of_bz * pi/a`.
- No unexplained residual `1/hbar` was introduced.

## 4. Professional nextnano runs completed

The report is produced only after the required real Professional kp8 output directories are parsed successfully. Demo 23 has no synthetic production-result fallback. See `solver_manifest.json`, `raw/`, and the per-deck inventories in `tables/inventories/`.

## 5. State-tracking validation

Tracked identities are recorded at every k point in `tables/state_tracking.csv`, including raw solver index, overlap score, assignment margin, confidence, and dominant spinor character. Ambiguous target tracking stops analysis before fitting.

This Professional output contains only k=0 spinors. Target Kramers pairs are identified at k=0 and their fixed solver dispersion columns are averaged at finite k. Therefore finite-k overlap tracking is unavailable and the state-tracking validation is marked FAIL, even though the energy-only A–D diagnostics are still produced.

## 6. Electron dispersion fits

| State | m*/m0 | RMSE meV | Max error meV | k at max nm^-1 | Fit range nm^-1 |
|---|---:|---:|---:|---:|---|
| e1 | 0.0728459 | 1.201475 | 3.392776 | 0.5557144 | 0–0.5557144 |
| e2 | 0.08480375 | 0.7596168 | 2.171135 | 0.5557144 | 0–0.5557144 |

Figure 2 overlays tracked kp8 points and fits; Figure 3 shows signed residuals over the actual Equation 2 range. The validation table applies the configured electron-fit RMSE gate.

## 7. Heavy-hole nonparabolicity

| State | Diagnostic m*/m0 | RMSE meV | Max error meV | k at max nm^-1 | Pattern |
|---|---:|---:|---:|---:|---|
| hh1 | -0.3977517 | 2.939178 | 4.819502 | 0.5557144 | systematic |
| hh2 | -0.7085993 | 3.104615 | 5.223755 | 0.2371048 | systematic |

These heavy-hole masses are diagnostics only. 23C and 23D use shape-preserving interpolation of tracked kp8 hole energies. Figure 5b is a local-curvature diagnostic and does not feed production physics.

## 8. Transition-energy comparison

Figures 6 and 7 show ΔE11, ΔE12, ΔE21, and ΔE22 at the same k index. The horizontal line is twice the photon energy at 1550 nm, exposing which k regions approach the SHG resonance as the dispersion model changes.

## 9. 23A results

χ²(1550) = `18.0487 pm/V`; peak = `45.106 pm/V` at `1502 nm`; FWHM = `270.9247 nm`.

## 10. 23B results

χ²(1550) = `25.79 pm/V`; peak = `74.06316 pm/V` at `1502 nm`; FWHM = `172.1021 nm`.

## 11. 23C boss-model results

χ²(1550) = `26.70382 pm/V`; peak = `83.04521 pm/V` at `1503 nm`; FWHM = `165.9554 nm`.

## 12. 23D raw-kp8 reference

χ²(1550) = `26.48225 pm/V`; peak = `81.49067 pm/V` at `1503 nm`; FWHM = `166.3493 nm`.

## 13. A-D spectrum comparison

Figure 8 shows the full wavelength range and Figure 9 shows absolute and relative differences to 23D. Pointwise relative deviations use an explicitly reported denominator floor near spectral nodes; the 1% acceptance gate uses whole-spectrum RMSE normalized by the 23D peak.

## 14. Pathway-level interpretation

- 23A: electron subtotal `(79.6056 + i -467.5316) pm/V`; signed HH subtotal `(-61.56722 + i 468.1419) pm/V`; largest terms: C_m1_n1_l1=467.50593; V_m1_n1_l1=464.81891; C_m2_n2_l2=55.338206; V_m2_n2_l2=37.750186; C_m1_n2_l2=4.4390403.
- 23B: electron subtotal `(-25.54484 + i -680.4799) pm/V`; signed HH subtotal `(51.32073 + i 681.3328) pm/V`; largest terms: C_m1_n1_l1=687.26611; V_m1_n1_l1=683.31601; C_m2_n2_l2=77.777849; V_m2_n2_l2=53.057887; C_m1_n2_l2=6.4024402.
- 23C: electron subtotal `(-16.8259 + i -733.8885) pm/V`; signed HH subtotal `(43.51983 + i 734.6155) pm/V`; largest terms: C_m1_n1_l1=739.21219; V_m1_n1_l1=734.96352; C_m2_n2_l2=80.369213; V_m2_n2_l2=54.825644; C_m1_n2_l2=6.0676999.
- 23D: electron subtotal `(1.84927 + i -753.9844) pm/V`; signed HH subtotal `(24.62097 + i 754.7817) pm/V`; largest terms: C_m1_n1_l1=757.03979; V_m1_n1_l1=752.68866; C_m2_n2_l2=79.873536; V_m2_n2_l2=54.487507; C_m1_n2_l2=6.0101896.

All individual terms and subtotals at 1550 nm and each mode's peak are in `tables/pathway_contributions_1550_and_peaks.csv` and Figure 12. Figure 13 compares the eight largest 1550-nm pathways across modes.

## 15. k-integrand interpretation

- 23A: maximum absolute node at k=`0.2723001 nm^-1`; 10–90% absolute-weight range `0.1000286`–`0.4797668 nm^-1`; coherence ratio `0.9841914`.
- 23B: maximum absolute node at k=`0.3426906 nm^-1`; 10–90% absolute-weight range `0.1185524`–`0.4908811 nm^-1`; coherence ratio `0.9844978`.
- 23C: maximum absolute node at k=`0.3482477 nm^-1`; 10–90% absolute-weight range `0.1185524`–`0.4871763 nm^-1`; coherence ratio `0.9838929`.
- 23D: maximum absolute node at k=`0.344543 nm^-1`; 10–90% absolute-weight range `0.1185524`–`0.4871763 nm^-1`; coherence ratio `0.9835353`.

Figure 10 shows real, imaginary, and magnitude per-node contributions. Figure 11 shows the cumulative complex integral; the absolute-weight quantiles above locate where the integrand is large without hiding cancellation.

## 16. k-grid convergence

Grid convergence is **FAIL**. Figure 14 and `tables/k_grid_convergence.csv` report χ²(1550), peak χ², and peak wavelength for every configured N_k and mode.

## 17. kmax convergence

Nominal kmax convergence is **FAIL**. Figure 15 compares the configured cutoff ladder and marks the nominal 0.1 π/a cutoff.

## 18. Isotropy validation

The two-direction isotropy check is **FAIL**. Figure 16 plots state-resolved energy differences. Passing supports the radial reduction over the sampled production range; failure means a direct 2D kp calculation is required.

## 19. Comparison to Ramesh et al. Equation 2 spectrum

The full comparison uses **Digitized from Ramesh et al. Fig. 2d**, an `eye-digitized published figure` with `45` points. It is not raw or tabulated author data and is not an acceptance gate.

| Reference | Value | Category | Source type | Use |
|---|---|---|---|---|
| Fig. 2d simulated spectrum | 45 points, 400-1850 nm | paper simulation | eye-digitized published figure | shape/peak/diagnostic error comparison |
| simulated resonance | ~1520 nm | paper simulation | paper text | peak-location comparison |
| measured resonance | ~1560 nm | paper experiment | paper text | separate peak-location marker only |
| ideal abrupt chi2 at 1550 nm | ~2340 pm/V | paper simulation | paper text, growth-interruption discussion | 1550-nm point comparison with geometry caveat |

P1 overlays absolute simulated susceptibility curves; the paper experiment is represented only by its separately labeled peak-location marker. P2 compares normalized shape, and P2b explicitly diagnoses the digitized paper zeros near 605 and 1330 nm. P3 compares peak locations, P4 compares 1550-nm values with an explicit abrupt-versus-graded caveat, and P5 reports digitization-dependent errors.

| Mode | Normalized RMSE vs digitized paper | Peak λ error nm | χ²(1550) error pm/V |
|---|---:|---:|---:|
| 23A | 0.2913604 | -18 | -2406.951 |
| 23B | 0.2766391 | -18 | -2399.21 |
| 23C | 0.2589147 | -17 | -2398.296 |
| 23D | 0.2623911 | -17 | -2398.518 |

## 20. Remaining normalization/prefactor questions

- The residual 1/hbar on the boss derivation slide remains dimensionally unresolved and was not implemented.
- Nz remains one coupled-well period per 30 nm; counting two individual wells is only a factor-two diagnostic.
- Full finite-k complex matrix elements and their gauge consistency remain future work, not Demo 23 physics.
- A direct physical 2D kp-grid susceptibility is needed if the two-direction isotropy gate fails.

The production calculation consistently uses the spin-degenerate `g_s k dk/(2π)` measure. Bare `2πk dk` and the two-individual-wells Nz interpretation remain labeled diagnostics and are not mixed into A–D results.

## 21. Final scientific conclusion

- Did 23A reproduce the validated baseline? **PASS**, max complex error `4.8045773e-13 pm/V`.
- Is e1 sufficiently parabolic? RMSE `1.201475 meV`, evaluated against the explicit fit gate in the validation table.
- Is e2 sufficiently parabolic? RMSE `0.7596168 meV`, evaluated against the explicit fit gate in the validation table.
- hh1 nonparabolicity: diagnostic RMSE `2.939178 meV`, max error `4.819502 meV` at k=`0.5557144 nm^-1`.
- hh2 nonparabolicity: diagnostic RMSE `3.104615 meV`, max error `5.223755 meV` at k=`0.2371048 nm^-1`.
- 23B change from 23A at 1550 nm: `7.7413 pm/V`.
- Additional 23C hole-dispersion change from 23B at 1550 nm: `0.9138184 pm/V`.
- Does 23C reproduce 23D to ≤1% spectral RMSE? **PASS**; RMSE `0.67417%`.
- A–D χ²(1550) and peak wavelengths are reported in the master table above.
- Dominant pathways and the dominant k range are reported in Sections 14–15 and their complete CSVs.
- Is kmax converged? **FAIL**. Is the radial approximation supported? **FAIL**.
- Full-spectrum comparison to the paper: normalized RMSE is `0.2589147` for 23C and `0.2623911` for 23D; their peak offsets from the digitized paper curve are `-17 nm` and `-17 nm`. These are diagnostic because the paper curve is eye-digitized.

See `plots/`, `paper_comparison_plots/`, and `tables/` for the complete evidence set.
