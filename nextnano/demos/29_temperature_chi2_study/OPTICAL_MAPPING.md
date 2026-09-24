# Full-8-band optical mapping gate

The first new 300 K solver pair provides 8-band k=0 energies, CB/HH/LH/SO
character, complex wavefunctions, and a 301-point dispersion, but **only one
k=0 spinor/composition frame**. It cannot supply finite-k same-band position
matrices or complex component-overlap tensors. The paper's selected-subband
Equation 2 also needs an established interband optical operator and spin
reduction before a physical full-8-band χ² can be asserted.

The nextnano++ `output_states{ all_k_points = yes }` documentation limits its
wavefunction output to points used in `k_integration{}`. The Demo 29 deck uses
`k_integration_disabled{}` and a separate 301-point `dispersion{ path{ } }`.
The real output confirms that these dispersion points do not create exported
finite-k spinors. A different solver output/acquisition route would be needed
to evaluate `M(k)` on exactly that path; merely renaming files cannot do it.
See https://www.nextnano.com/docu/nextnanoplus/latest/reference/keywords/quantum/region/output_states.html

`chi2/full8.py::contract_interband` accepts a sourced 8×8 operator in this exact
saved basis order: `cb1, cb2, hh1, hh2, lh1, lh2, so1, so2`. It contracts
`T_abuv(k) = ∫ F*_{a,u}(z,k) F_{b,v}(z,k) dz` with `B_uv`. No identity operator is
accepted: the full-spinor inner product of different eigenstates is not the
historical interband optical factor. `Z_ab(k) = Σu ∫ F*_{a,u} z F_{b,u} dz` is
derived separately and checked for Hermiticity.

The nextnano manual documents this eight-component basis and states that the
exported KP8 dipole and momentum tables are envelope-operator sums. Both Demo
28's archived 301-point output and the first Demo 29 300 K output have only
k=0 spinors/composition, so neither can settle finite-k coupling or tracking.
The prepared Demo 28 finite-8-band adapter also
requires a reviewed optical operator and spin convention rather than providing
a default. Relevant official documentation:

- https://www.nextnano.com/docu/nextnanoplus/latest/reference/models/quantum/envelope_function_representation.html
- https://www.nextnano.com/docu/nextnanoplus/latest/reference/keywords/quantum/region/dipole_moment_matrix_elements.html
- https://www.nextnano.com/docu/nextnanoplus/latest/reference/keywords/quantum/region/momentum_matrix_elements.html

Before enabling a primary susceptibility, document and review:

1. The optical polarization and the operator's complex 8×8 matrix in the
   documented basis, including its derivation/source and units.
2. Whether the historical `r_e,hh = 0.751 nm` prefactor is retained, rescaled or
   replaced. Never include that factor both inside the operator and again in
   the prefactor.
3. How spin-resolved, possibly mixed or split doublets enter the reduced
   two-electron/two-valence Equation 2. An explicit sum of both spin channels
   must not also use the old spin-degeneracy factor of two.
   The software gate accepts only a documented single-channel times-two
   symmetry treatment or explicit spin-resolved summation without that factor;
   neither treatment has been established for these data yet.
4. Review of overlap and character flags from the returned 300 K run, especially
   near valence crossings. The old fixed `(3,4)` pair was LH dominated at k=0;
   the new HH-like selection is a recorded model change.

`config/optical_operator.json` deliberately has `status: UNRESOLVED` and null
fields. `optical_gate` rejects that configuration. The mixed-control calculation
does not depend on this gate and can run after each matched solver pair returns.

The full-8-band gate now has **two** dependencies: a supported finite-k state
export on the fixed 301-point path and a justified optical matrix/spin
convention. Do not invent missing spinors, freeze matrices at k=0 while
claiming finite-k treatment, or publish a primary spectrum to bypass either.
Do not alter kmax, k density, Γ, geometry, or temperature-specific processing
without a reviewed technical reason.

## First finite-k pilot evidence (300 K, 2026-09-24)

The transferred Professional pilot exported nine complete 14-state frames,
each with eight complex spinor components, composition, and growth-dipole and
momentum tables. Integrated spinor probabilities agree with composition;
off-diagonal `<a|z|b>` from spinors agrees with the growth-dipole table to its
printed precision. The separate 301-point dispersion was unchanged. Its
positive-y path ended at 0.555714439232 nm⁻¹, while the integration-grid
positive-y sample was 1.5478201 nm⁻¹. Thus only the k=0 frame lies on the
required path. The previous 49-frame prediction was incorrect; the diagnostic
now reads actual `k_points.txt` coordinates.

The reported in-plane-y envelope momentum tables contain zeros for every
sampled pair. They are not an approved replacement for the Bloch interband
operator; nextnano's momentum-matrix documentation describes the exported
quantity as envelope momentum. Its Matrix elements reference explicitly says
these `quantum{}` matrix tables are not used by nextnano's optical spectra.
The nextnano optical-absorption tutorial instead uses an 8×8 kinematic-momentum
operator (including spin-orbit effects) and exports transition intensities
proportional to the **squared magnitude** of its optical matrix element.
Those intensities alone do not retain the complex phase needed for the coherent
products in χ² Equation 2. A sourced implementation of the 8×8 operator, or
another validated phase-preserving output, is still required. Sources:
https://www.nextnano.com/docu/nextnanoplus/latest/reference/models/quantum/matrix_elements.html
and https://www.nextnano.com/docu/nextnanoplus/latest/tutorials/quantum_well_optical_absorption.html .

The optical polarization, complex 8×8 operator,
units, historical `r_e,hh` relationship, and spin factor remain **UNRESOLVED**.
The old mixed-model control can be run separately at 100/300/500 K without
changing this gate. Its single-band k=0 factors and `M(k)=M(0)` must always
remain labeled as historical mixed-model assumptions.
