# 29A2 optical mapping: scientific gate remains closed

**Decision (2026-09-24):** the present files and published definitions do not
determine a phase-preserving, correctly normalized interband optical operator
for the exported eight-component spinors. No full-8-band χ² value is reported.
`config/optical_operator.json` remains `UNRESOLVED`, and `optical_gate()` must
continue to reject it. The 29A3 state run is useful for tracking and
intersubband matrices; it cannot by itself close this gate.

## Equation and what is known

The [Ramesh et al. paper, Methods Eq. 2](https://arxiv.org/pdf/2602.23246)
evaluates χ²_xzx with two interband optical factors and one growth-direction
intersubband position factor. Its simplified model separates Bloch unit-cell
and envelope wavefunctions, pulls a scalar `r_e,hh²` outside the sum, assumes
filled valence states, and retains two electron and two HH levels. The
historical Demo 29 code records `r_e,hh = 0.751 nm` and multiplies the radial
k weights by a spin factor of 2. Those are **historical Eq. 2 settings**, not
a component-resolved 8-band operator or a derivation of spin reduction for
mixed doublets. The paper says its unit-cell interband factor was obtained
with DFT; it does not publish a complex 8×8 matrix in nextnano's saved basis.

The [nextnano envelope-function reference](https://www.nextnano.com/docu/nextnanoplus/latest/reference/models/quantum/envelope_function_representation.html)
identifies the saved Td basis order as
`cb1, cb2, hh1, hh2, lh1, lh2, so1, so2`. Its Kane basis has a different
ordering and phase convention. The complex envelopes provide
`T_abuv(k) = ∫F*_{a,u}(z,k) F_{b,v}(z,k) dz` and the growth-position matrix
`Z_ab(k) = Σ_u∫F*_{a,u}(z,k) z F_{b,u}(z,k) dz`. The returned pilot supplies
these at five positive Γ→y points. `Z` is Hermitian; off-diagonal elements
match nextnano's growth-dipole table within 4.1×10⁻⁶ nm at the printed
precision. Diagonal nextnano dipole entries are zeroed by its output
convention, so the off-diagonal comparison is the meaningful check.

For a full-spinor interband transition, the needed amplitude has the form

`D_ab^opt(k) = Σ_uv ∫F*_{a,u}(z,k) B_uv^opt(z,k) F_{b,v}(z,k) dz`,

where `B^opt` includes the Bloch/kinematic-momentum optical coupling for the
chosen polarization and its transformation into the **saved Td basis**. This
is a coherent complex amplitude; an identity matrix gives only full-state
orthogonality and is invalid. A growth-position `Z_eh` made from the identity
Bloch factor is also not a substitute for the interband optical amplitude.

The [nextnano optical tutorial](https://www.nextnano.com/docu/nextnanoplus/latest/tutorials/quantum_well_optical_absorption.html)
defines its optical transition using an 8×8 **kinematic momentum** matrix,
including spin-orbit contributions, contracted with the envelopes. Its
`transition_disp` output retains `|ε·π|²`, not the complex phase. The
[quantum matrix-element reference](https://www.nextnano.com/docu/nextnanoplus/latest/reference/models/quantum/matrix_elements.html)
says the exported `quantum{}` dipole/momentum tables are envelope-operator
sums and are not the optical-spectrum matrix. The in-plane envelope-momentum
table being zero therefore does not establish a zero interband transition.

## Required mapping before 29A4

| Item | Required decision | Present state |
|---|---|---|
| Basis | Explicit Kane→saved-Td unitary transform, ordering and Bloch phases | Td order known; transform/phase for an optical operator not established |
| Polarization | Map the paper's χ²_xzx axes to nextnano's 1D growth-x coordinates and select both interband polarizations | Not established |
| Operator | Sourced complex 8×8 kinematic-momentum or length-gauge dipole, including CB, HH, LH, SO and spin-orbit terms | Not available in the returned data or cited docs |
| Units | Convert momentum to a transition dipole with an explicit gauge/energy convention and any spatially varying material parameters | Not established |
| Spin | Track/sum the two channels and mixed doublets without also applying the historical radial factor of 2 | Not established |
| Scalar 0.751 nm | If optical matrix is dimensionless relative to it, retain `r_e,hh²` once; if matrix is an absolute length, replace that factor | Not decided; no scaling fit permitted |
| Phase | Preserve complex amplitudes and use a gauge-consistent doublet contraction/pathway product | Raw phases are basis/gauge dependent; transition intensities cannot restore them |

The existing `full8.contract_interband` function is only a mathematical
contraction hook. Its arbitrary approved-operator JSON schema is **not** a
scientific derivation. The current configuration cannot pass the gate, and
the paper's scalar, nextnano's envelope tables, or intensity-only optics
output must not be inserted as a guessed operator. A defensible path requires
either nextnano's exact phase-resolved 8-band optical operator/API for this
build, or a separately derived and cross-validated operator in the exported
Td basis with the matching material parameters. Document its source, units,
polarization, spin treatment, and a comparison to a trusted optical
transition calculation before enabling Eq. 2.

## Sampling and state implications

The current five target-path samples do establish k-dependent same-band
position matrices, but hh1–hh2 changes sharply and nonmonotonically and hh2
has one weak tracking step. The 29A2 leave-one-out interpolation check rejects
five-point interpolation. 29A3 therefore acquires more 300 K spinors while
preserving the 301-point dispersion and `0.10·π/a` cutoff. This does **not**
authorize 29A4 or any 100/500 K full-8-band solve. No explicit thermal carrier
occupations are introduced by the existing Equation 2 engine.
