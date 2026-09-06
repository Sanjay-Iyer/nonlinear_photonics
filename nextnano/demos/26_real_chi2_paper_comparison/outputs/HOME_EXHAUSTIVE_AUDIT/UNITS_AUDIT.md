# Units audit

Primary source context and equation mapping are in EQ2_LITERAL_AUDIT.md. This is a dimensional and source-code audit, not an absolute-amplitude reproduction claim. No solver was invoked.

## Traceable code and data

- `C:/code/nonlinear_photonics/nextnano/demos/20_quantum_well_interface_grading_scaled/s06_chi2.py`: Chi2Settings (r_e_hh_nm=0.751, n_wells_per_metre=1/30e-9, spin_degeneracy=2, lattice_constant_nm=0.565325), absolute_prefactor at lines 514-534, transition_energies_eV immediately afterward.
- `C:/code/nonlinear_photonics/nextnano/demos/22_k_resolved_8band_chi2_validation/chi2_22.py`: radial_weights and chi2_from_k_inputs.
- `C:/code/nonlinear_photonics/nextnano/demos/26_real_chi2_paper_comparison/extended_implementation_audit.py`: HC, Q, EPS0, prefactor, integration_weights, independent_eq2.
- Inputs: `demo_results/demo24/demo23_reanalysis/tables/tracked_dispersions_and_fits.csv`, `demo_results/demo19/tables/demo19_master_results.csv` case 04, and `demo_results/demo24/demo23_reanalysis/spectra/23D_chi2.csv`.

## Denominator units

| Quantity | Code convention | Assessment |
|---|---|---|
| Ee and Ehh | eV on one common electron-energy reference | Delta=Ee-Ehh is in eV. Offsets common to both cancel. The aligned energy column is a provenance decision, not a unit conversion. |
| Fundamental photon energy | 1239.841984/lambda_nm in eV | hc expressed in eV nm. At 1000 nm, E=1.239841984 eV; two-photon term 2.479683968 eV. |
| nm versus m wavelength | hc is paired with nm input | No additional 1e9 is needed in the denominator. |
| Angular versus ordinary frequency | E=hbar omega=h nu=hc/lambda | Using hc is correct; do not use hbar c/lambda, which would introduce a 2pi error. |
| Gamma | gamma_meV times 1e-3 eV | Baseline 5 meV=0.005 eV, same units as Delta and photon energy. |
| Two denominator product | eV^2 | Converted to J^2 through division by q^2 in prefactor. |
| Frequency-to-energy form | D_omega=D_E/hbar | 1/(hbar^2 D_omega,1 D_omega,2)=1/(D_E,1 D_E,2); no residual hbar^-2 is allowed. |

The printed paper labels transitions with omega while specifying broadening in meV. This is shorthand requiring a consistent energy conversion; the code does that. The boss guide's energy-domain update is consistent on this point. A factor two due to FWHM interpretation changes resonance width, whereas a factor two in a global susceptibility prefactor changes only amplitude.

## Numerators and density normalization

Normalized scalar envelopes satisfy integral |psi|^2 dz=1. With z in nm, psi has nm^-1/2, overlap O is dimensionless, and ze/zh have nm. The independent numerator is two overlaps times one position matrix element, hence nm. Complex conjugation is essential to physics but does not alter dimensions.

r_ehh=0.751 nm=7.51 angstrom=7.51e-10 m is a Bloch dipole LENGTH, not a dimensionless overlap, momentum matrix element, or energy. Its square contributes m^2. The production global prefactor uses Nz=1/(30 nm)=3.3333e7 m^-1. The 30 nm period agrees with 18.2+7.1+1.8+2.9 nm; whether one counts an asymmetric pair as one active quantum-well unit or counts two wells is a density convention needing source agreement.

For a state sum per area, (1/A) sum_k tends to integral d^2k/(2pi)^2. Under the radial-isotropy assumption this is integral k dk/(2pi). Spin degeneracy gs=2 multiplies it. The numerical k grid is nm^-1, so the weights are nm^-2, converted using 1e18 m^-2. Converting k itself to m^-1 and retaining that same prefactor conversion would double-count 1e18.

The code prefactor is exactly:

    Nz*q^3*r_m^2/(6*epsilon0) * (1e-9 * 1e18 / q^2) * 1e12

where 1e-9 converts numerator nm to m; 1e18 converts nm^-2 measure to m^-2; q^-2 converts inverse eV^2 to inverse J^2; 1e12 converts m/V to pm/V. Multiplying all physical factors gives m/V: Nz supplies m^-1, r^2 z supplies m^3, and the k measure supplies m^-2, leaving q^3/(epsilon0 J^2), which has m/V.

The unnormalized radial measure 2pi*k*dk differs from gs*k*dk/(2pi) by 4pi^2/gs (2pi^2 for gs=2). Provided this is applied uniformly, normalized spectral shape is unchanged. If both Kramers partners are summed explicitly, adding another gs=2 can double-count states; this must be decided consistently for any spinor diagnostic. A single-ray dispersion used radially also assumes angular isotropy, which is a model approximation rather than a missing constant.

## Absolute-normalization ambiguities that remain

1. `2602.23246v1.pdf`, printed p11, explicitly defines Nz as wells per unit length. The newer local `Quantum-Well-Metasurface to Maximize Nonlinear Polarization.pdf`, printed p11, calls Nz spin degeneracy. With normalized envelopes and a per-area k measure, a bulk susceptibility in m/V still needs a longitudinal density normalization; spin degeneracy alone is dimensionless. This paper-version inconsistency cannot be resolved by silently replacing the code's Nz. It affects absolute units/amplitude, and should be clarified with the actual reproduction script.
2. The exact hidden normalization of the paper's symbolic k sum is not specified in the inspected passages. Area and spin factors can be grouped in different places; dimensional closure and no double counting matter more than matching symbol names.
3. `docs/equation_2_from_paper/Xi2 (1).m` uses energy-valued denominators yet retains an hbar^-2 in Apre, along with mixed comments/units for r, Nz, ee0 and empirical powers of ten. Its absolute prefactor is not a validated SI reference. Its global constants alone cannot repair normalized topology. Summing its eight spinor components into one scalar also needs independent physical justification.
4. Source r_ehh and density choices affect absolute scale. A normalized comparison cannot validate them. The present audit does not claim to reproduce the paper's absolute susceptibility.
5. Mixing energy origins across geometries or using a hole quasiparticle energy as if it were a valence electron eigenenergy can change Delta incorrectly; present frozen inputs use a shared electron-energy convention, but matrix/geometry alignment is separately audited.

## Conclusion

No eV/meV, hc/lambda, hbar, nm/m, or radial-measure dimensional error was found in the baseline energy-domain implementation. The correct unit conversions are explicit and dimensionally close to pm/V. This rules against a simple denominator-unit explanation for missing P1/P3. It does not settle absolute normalization, paper-version Nz wording, active-period counting, spin counting for reconstructed states, or equivalence of the integration domain. Those require provenance/author files before any physical amplitude claim.
