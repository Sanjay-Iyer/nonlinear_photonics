# Literal Equation 2 audit

Scope: primary physics/source audit for Demo 26 - Exhaustive Home-Laptop Reproduction Audit. No nextnano execution and no modification of the saved baseline. Test numbers and fresh numerical engine comparisons are assigned in the enclosing numbered audit; this note supplies their literal-source evidence.

## Primary sources inspected

- `C:/code/nonlinear_photonics/2602.23246v1.pdf`, Methods 5.1, printed page 11, Equation 2 and its surrounding assumptions. The existing rendered page `tmp/pdfs/eq2_review/ramesh-11.png` was visually inspected and the equation/source text checked against PDF extraction.
- `C:/code/nonlinear_photonics/Quantum-Well-Metasurface to Maximize Nonlinear Polarization.pdf`, Methods, printed page 11: electron Equation 2 and HH Equation 3. These retain the same numerator/denominator algebra, but the prose describing Nz differs (see units audit).
- `C:/code/nonlinear_photonics/Interband second-order nonlinear optical susceptibility of asymmetric coupled quantum wells.pdf`, PDF page 3 (journal page 251111-2), Equation 3: corroborating earlier formula and occupied-valence assumption.
- `C:/code/nonlinear_photonics/docs/equation_2_from_paper/Equation_2_Study_Guide_Boss_Derivation_Nextnano.md`, sections 24-29, and its Boss Update PDF: repository account of the boss's energy-domain and radial-integral update. This is a secondary reconstruction, not an independently authenticated original slide. It explicitly starts from general Eq1; its prefactor cannot be copied into specialized Eq2 without repeating the specialization.

## Explicit mapping

Define O[n,m]=<e_n|hh_m>, ze[n,l]=<e_n|z|e_l>, zh[m,l]=<hh_m|z|hh_l>, Delta[n,m]=Ee[n]-Ehh[m], and E=hc/lambda at the FUNDAMENTAL wavelength. Then:

- Electron numerator: conj(O[n,m]) ze[n,l] O[l,m].
- HH numerator: O[n,m] zh[m,l] conj(O[n,l]), with an external minus sign.
- Common denominator D2=Delta[n,m]-2E+i Gamma_E.
- Electron D1=Delta[l,m]-E+i Gamma_E.
- HH D1=Delta[n,l]-E+i Gamma_E.
- m,n,l each range over two states: eight electron terms plus eight HH terms.
- Prefactor in energy units: Nz e^3 r_ehh^2/(6 epsilon0); the frequency-domain hbar^-2 cancels exactly against the two denominator conversion factors.

| Printed item | Assessment of current baseline |
|---|---|
| m/n/l indexing | Correct explicit loops and transitions in both engines. |
| Electron z orientation | ze[n,l], correct. |
| HH z orientation | zh[m,l], correct. |
| Relative sign | Electron minus HH, correct. |
| First/common denominator | Delta[n,m]-2E, correct. |
| Second denominator | Delta[l,m]-E for electron; Delta[n,l]-E for HH, correct. |
| Bra/ket conjugation | Independent evaluator correct; production correct ONLY on real overlap inputs. See critical limitation below. |
| Gamma sign | +iGamma matches printed Eq2; reversing it conjugates the response for real numerators. |
| Gamma placement | Same +iGamma in both denominators, matching print. No additional factor two on D2 linewidth. |
| Occupation | Filled valence, empty conduction reduction; the v1 Methods explicitly set the initial valence occupation to unity. This does not prove a matching electrostatic carrier distribution in a separate solver deck. |
| SH frequency permutation | omega1=omega2=omega gives 2E and E. Printed specialized Eq2 already supplies its factor 1/6; adding another factor two is not supported by literal transcription. Other polarization conventions would need a separate derivation. |
| Energy reference | Ee-Ehh on a common electron-energy axis; hole energy is not a positive hole excitation energy to be subtracted again. |
| HWHM/FWHM | In an isolated Lorentzian intensity, +iGamma gives HWHM Gamma. The paper calls 5 meV broadening without explicitly saying HWHM/FWHM; 2.5 meV is a defensible sensitivity check, not an established correction. |

## Actual implementation limitation found

`nextnano/demos/22_k_resolved_8band_chi2_validation/chi2_22.py`, function `chi2_from_k_inputs`, advertises complex input support but uses `o[n,m]*ze[n,l]*o[l,m]` and `-o[n,m]*zh[m,l]*o[n,l]`. It omits the two conjugates identified above. The independent implementation at `nextnano/demos/26_real_chi2_paper_comparison/extended_implementation_audit.py`, function `independent_eq2`, includes them.

Therefore an ordinary transcription error is strongly disfavored for the REAL frozen-matrix baseline, but a general complex-input implementation problem is present in production. It can fail continuous eigenstate-phase invariance, even though all +/- sign-flip tests pass. This is not evidence that the current real-input spectrum is numerically wrong, and cannot by itself explain its missing paper features. Complex kp8-derived matrices must use the conjugated independent expression; do not propagate the production limitation into a new diagnostic. The enclosing audit supplies an explicit continuous-phase numerical regression.

This also corrects the earlier overly broad statement that production/independent agreement validated complex conjugation. Agreement on purely real matrices cannot distinguish conjugated and unconjugated algebra.

## What earlier numerical evidence actually establishes

The earlier `EXTENDED_IMPLEMENTATION_AUDIT/INDEPENDENT_ENGINE_COMPARISON.csv` contains pathway, subtotal, and final comparisons. The saved maximum final discrepancy was about 5.326e-10 pm/V over 1,451 wavelengths, with 23,216 pathway samples and 4,353 subtotal/final samples. The independent source does not import or call the production susceptibility function.

However, the old `INDEPENDENT_DENOMINATOR_AUDIT.csv` only records shapes, finiteness, and an assertion of formula checking. It is NOT a numerical denominator-by-denominator comparison between engines. The new enclosing audit must use the separately captured production d1/d2 arrays to close this gap. Independence here is algebraic reimplementation, not independent physics inputs: both use the same saved dispersions and frozen matrices.

## BZ interpretation remains unresolved

The code defines k_BZ=pi/a with a=0.565325 nm and baseline kmax=0.1pi/a, about 0.5557 nm^-1. This is a code convention, not a universal crystallographic definition of the zincblende Brillouin-zone radius.

For the fcc Bravais lattice of zincblende, the reciprocal plane associated with G=(0,4pi/a,0) places Gamma-X at 2pi/a along conventional [010]. Thus 0.1 Gamma-X is 0.2pi/a, about 1.1114 nm^-1. Along [011] the intersecting {111} reciprocal plane gives a different radial boundary, 3pi/(sqrt(2)a). Consequently a circular radial truncation, a direction-dependent fraction of the bulk BZ, a square Cartesian k window, and a fraction of BZ area are not identical domains. A phrase describing one-tenth of an area would scale linear extent by sqrt(0.1), but v1 wording 'away from zone center' favors a distance interpretation.

Neither paper version inspected specifies the actual kx/ky integration bounds and geometry sufficiently to choose among these. Constant measure prefactors cannot alter normalized shape; changing domain or cutoff can. Available data beyond baseline must be inventoried before declaring new data required. The colleague's exact k grid, units, integration domain, and lattice convention can settle this at home. No extrapolation to 0.2pi/a is licensed by a dataset ending at 0.125pi/a.

## Outcome

Literal energy-domain denominators, state loops, relative sign, and the frozen-real baseline are supported. Complex-input conjugation is a real implementation limitation, absolute normalization retains convention uncertainties, and BZ-domain equivalence is unresolved. These are distinct conclusions; none is a demonstrated paper reproduction.

## Fresh exhaustive-audit numerical closure

`engine_verification.json` in this directory records a direct production execution with captured intermediate denominators: maximum d1 and d2 disagreement is zero, maximum pathway disagreement is about 4.69e-13 pm/V, and total disagreement about 8.76e-13 pm/V. Continuous complex state phases change production |chi| by up to 4.518 pm/V, while the conjugated independent engine stays invariant within about 4.59e-13 pm/V. Thus the complex-input limitation is experimentally demonstrated, not merely hypothetical. These are new direct-engine checks; the larger old 5.326e-10 comparison includes serialized stored-output precision. Existing-artifact preservation remains true.
