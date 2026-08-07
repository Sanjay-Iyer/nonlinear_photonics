# Demo 14 — physics sources and provenance

_Spec §1. Every nontrivial constant, equation, normalization convention and
parameter used by the absolute χ⁽²⁾ model, with its source and units._

**Rule for this file: no value enters it without a source, and no multiplicative
factor is ever fitted to make our output match a published number.** Where a
quantity is ambiguous in the literature, the ambiguity is recorded rather than
silently resolved.

## Sources

| Tag | Reference |
|---|---|
| **Ramesh 2023** | Ramesh et al., "Interband second-order nonlinear optical susceptibility of asymmetric coupled quantum wells", *Appl. Phys. Lett.* **123**, 251111 (2023), doi 10.1063/5.0168596. PDF in repo root. |
| **Ramesh 2026** | Ramesh et al., "Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells", arXiv:2602.23246v1. PDF in repo root (`2602.23246v1.pdf`). |
| **Schaefer 2024** | Cited by the user for the isotropic radial k∥ form. **Not yet independently verified against a PDF in this repo.** |
| **Fathi/Ramesh 2026** | QW-metasurface paper (`Quantum-Well-Metasurface to Maximize Nonlinear Polarization.pdf`). Uses a symmetrized convention — see §Tensor conventions. |
| **nextnano++ 3.0.0** | Installed build; grammar `keywords_nnp.xml`, database `database_free.nnp`. |

---

## The governing equation

**Ramesh 2023 Eq. (3)**, verbatim in structure (OCR cleaned):

```
                 N_z e^3 r_e,hh^2
chi2_xzx(w1,w2) = ----------------  SUM   SUM   SUM  ( electron term  -  hole term )
                    6 eps0 hbar^2    k||   m,n    l
```

electron term (Eq. 5):

```
  <psi_hh,m|psi_e,n> <psi_e,n|z|psi_e,l> <psi_e,l|psi_hh,m>
  ---------------------------------------------------------
  (w_en,hhm(k||) - w1 - w2 + iG) (w_el,hhm(k||) - w1 + iG)
```

hole term (Eq. 6), subtracted:

```
  <psi_e,n|psi_hh,m> <psi_hh,m|z|psi_hh,l> <psi_hh,l|psi_e,n>
  -----------------------------------------------------------
  (w_en,hhm(k||) - w1 - w2 + iG) (w_en,hhl(k||) - w1 + iG)
```

and `chi2_xzx = chi2_xzx,e + chi2_xzx,hh` (Eq. 7).

**As published the denominators are angular frequencies**, so `Γ` must enter as
`Γ_rad/s = Γ_J / ħ`. This is the §7 trap, and it is why the two-implementation
cross-test below is required.

Implemented in [`nextnano/demos/_shared/chi2.py:474`](../nextnano/demos/_shared/chi2.py:474)
(`chi2_spectrum`).

---

## Constants

### `r_e_hh` — Bloch interband matrix element — **RESOLVED**

| | |
|---|---|
| **Value** | **7.51 Å = 7.51e-10 m = 0.751 nm** |
| **Config** | `metric.r_e_hh_nm: 0.751` |
| **Source** | Ramesh 2023, verified verbatim from the PDF |
| **Method** | DFT, VASP, HSE06 hybrid functional |
| **Definition** | `r_e,hh = <u*_e | r | u_hh>` (Eq. 4) |

Quoted from Ramesh 2023:

> "The interband matrix element of the unit cell wavefunctions was determined to
> be r_e,hh = 7.51 Å using density functional theory (DFT) performed with the
> Vienna Ab initio Simulation Package using HSE06 hybrid functionals."

**This is a position matrix element, not `e·r`.** Eq. (3) already carries `e^3`.
Do not multiply by the electron charge again. A unit test must lock this.

Because it is a property of the **GaAs bulk unit cell**, it does not depend on
the barrier alloy — which matters, because Ramesh 2023 used Al₀.₄Ga₀.₆As while
Ramesh 2026 and Demo 14 use Al₀.₅₅Ga₀.₄₅As. Carrying the constant across is
legitimate; carrying a *barrier-dependent* quantity across would not be.

χ⁽²⁾ scales as `r²`, so this single number sets the absolute scale quadratically.
A sensitivity sweep is still required (§4).

### `N_z` — well/period density — **RESOLVED, with recorded ambiguity**

| | |
|---|---|
| **Value** | **N_z = 1 / L_period = 1 / 30 nm = 3.3333333e7 m⁻¹** |
| **Config** | `metric.n_wells_per_metre: 3.3333333e7`, `metric.Nz_mode: period_density` |
| **Source** | Ramesh 2023 Eq. (1) definition + Ramesh 2026 layer structure |

Ramesh 2023 states, verified verbatim:

> "In Eq. (1), N_z is the number of QWs per unit length"

**That phrase does not distinguish periods from individual wells**, and a coupled
structure has two wells per period. Recorded readings:

| Reading | Value | Note |
|---|---|---|
| **periods per unit length (chosen)** | 3.3333e7 m⁻¹ | Ramesh 2023/2026 wording + Schaefer 2024's more specific "periods per unit length" |
| individual wells per unit length | 6.6667e7 m⁻¹ | literal "number of QWs", ×2 |
| Fathi/Ramesh 2026 usage | — | calls N_z *spin degeneracy* while using essentially the same equation — **inconsistent with both papers above** |

Decision: `Nz_mode: period_density`. **Spin degeneracy stays in its own variable
`spin_degeneracy` and is never folded into N_z** — the code already does this
([`chi2.py:258`](../nextnano/demos/_shared/chi2.py:258)).

A sensitivity table over these readings must run before the normalization is
called validated. No multiplicative constant may be fitted.

### Period length — 30 nm, with a recorded publication inconsistency

Reference structure: 18.2 nm AlGaAs / 7.1 nm GaAs / 1.8 nm AlGaAs / 2.9 nm GaAs
= **30.0 nm**. Fig. 1a's caption states 30 nm and the thicknesses sum to 30 nm,
but the Section 2.2 body text says "Each period is 20 nm" in the same sentence
that lists them. Treated as a typo. Already recorded in
`11_paper_validation_interband_chi2_acqw/paper_targets.yaml`, where the note
explains it matters *because N_z sets the absolute scale*.

### Other settings

| Quantity | Value | Source |
|---|---|---|
| Γ (broadening) | 5 meV | Ramesh 2023 and 2026 |
| states per band | first 2 electron, first 2 HH | Ramesh 2023 |
| k∥ cutoff | 0.1 × Brillouin zone from Γ | Ramesh 2023 ("saturated by one-tenth of the Brillouin zone") |
| zone edge convention | π/a | **our assumption** — the papers do not state π/a vs 2π/a |
| GaAs lattice constant | 0.565325 nm | material database |
| electron in-plane mass | 0.067 m₀ | standard GaAs; **paper does not state its value** |
| HH in-plane mass | 0.112 m₀ | standard GaAs; **paper does not state its value** |
| spin degeneracy | 2, as a separate factor | **our assumption**; paper does not say whether it folded one in |
| barrier alloy (Demo 14) | Al₀.₅₅Ga₀.₄₅As | Ramesh 2026 |
| barrier alloy (Ramesh 2023) | Al₀.₄Ga₀.₆As | Ramesh 2023 — *different paper, different alloy* |

---

## Unit chain — verified analytically

The repo evaluates the **energy form**: denominators in eV rather than rad/s,
which exactly absorbs the published `ħ²` (since `E = ħω`, `1/(ħ²ω²) = 1/E²`).

| Factor | Units |
|---|---|
| `N_z e³ r²/(6 ε₀)` | m⁻¹ · C³ · m² / (C² J⁻¹ m⁻¹) = **C J m²** |
| k∥ measure `∫d²k/(2π)²` | **m⁻²** |
| `<e\|z\|e>` matrix element | **m** |
| denominator product | **J⁻²** |
| **product** | C J m² · m⁻² · m · J⁻² = C m / J = C m /(C V) = **m/V** ✓ |

The `m⁻²` that makes the units work comes **only** from the 2D k∥ measure — which
is why §3's "do not use a plain unweighted average over k samples" is not a
stylistic preference but a dimensional requirement.

Implementation constant ([`chi2.py:653`](../nextnano/demos/_shared/chi2.py:653)):
`unit_conversion = 1e-9 * 1e18 / e²` — respectively nm→m for `z`, nm⁻²→m⁻² for
the k weights, and eV⁻²→J⁻² for the denominators. Each factor matches the table.

**Order-of-magnitude probe.** With the resolved constants and *placeholder*
matrix elements (z = 2 nm, overlap² = 0.25, on resonance), the model gives
~350 pm/V against the paper's 2340 pm/V — same order. This is a smoke test with
guessed inputs, **not** a validation; the real check is the §16/§5 paper-reference
gate with solver matrix elements.

---

## k∥ integration — already the radial 2D form

Ramesh 2023, verified verbatim:

> "The summation over k∥ was converted to an integral in two-dimensional k-space
> (kx, ky). We found the integral over k states for χ⁽²⁾ saturated by one-tenth of
> the Brillouin zone from zone center (k = 0)."

[`_k_grid`](../nextnano/demos/_shared/chi2.py:432) already implements
`(1/A)Σ_k → ∫d²k/(2π)² = (1/2π)∫k dk` for an isotropic integrand, with
trapezoidal weights on the radial measure and spin degeneracy as a separate
multiplicative factor. **It is not a plain unweighted average.** The `k_t dk_t`
radial form attributed to Schaefer 2024 is what the code already does.

Still missing, and required:

- a direct 2D Cartesian `(kx, ky)` implementation to cross-check the radial one;
- `k_parallel_integration_converged`, `k_parallel_relative_error`,
  `k_parallel_cutoff_used` outputs;
- a cutoff/refinement convergence sweep and test.

---

## Two implementations, cross-tested

Required by §2 of the resolution. Both must agree numerically:

| Form | Denominators | Γ | ħ² |
|---|---|---|---|
| `angular_frequency_form` | rad/s | `Γ_rad_s = Γ_J / ħ` | explicit `1/ħ²` in the prefactor |
| `energy_form` (current) | joules | `Γ_J` directly | cancels against the denominators |

The energy form exists and is tested. The angular-frequency form must be
implemented as an independent path — not a rescaling of the other — or the test
proves nothing.

---

## Tensor and effective-χ⁽²⁾ conventions — keep separate

Per §6 of the resolution, these are **different quantities** and must never be
silently equated:

| Quantity | Meaning |
|---|---|
| `chi2_material_xzx_pm_per_V` | the density-matrix material susceptibility — **the BO objective** |
| `chi2_experiment_effective_pm_per_V` | folds in optical-field distribution, standing-wave and extraction effects. **Must not be produced** until that weighting is actually implemented |

Ramesh 2026 notes the coupled-QW structure has `χ_xzx = χ_xxz` with
`χ_xxz ≈ 0`, giving a **factor of 1/2** in their experimental MQW extraction.
The Fathi metasurface paper instead reports `|χ_xzx + χ_xxz|` under a symmetrized
convention. Every factor-of-two conversion between these must be stored
explicitly with its source. *(Both statements are recorded from the user's
review; independent verification against the two PDFs is still outstanding.)*

---

## Validation targets — never fit targets

Already in `paper_targets.yaml`, each tagged by kind and cited to a section.

| Quantity | Value | kind |
|---|---|---|
| ideal abrupt simulation @1550 | 2340 pm/V | simulated |
| EDS Al-profile simulation | 1200 pm/V | simulated |
| EDS Ga-profile simulation | 1363 pm/V | simulated |
| growth-interrupted experiment | 1345 pm/V | measured |
| 4-period sample (best) | 2750 pm/V | measured |
| bulk GaAs reference | 377 pm/V | reference |
| simulated resonance | 1520 nm | spectral |
| measured resonance | 1560 nm | spectral |

If the absolute scale comes out badly wrong, audit in this order before touching
anything else: **Å→m conversion; N_z; 2D k-space normalization and 2π factors;
energy vs angular-frequency convention; Γ; spin degeneracy; tensor/permutation
factors.** Stop before BO.

---

## Open provenance items

1. **Schaefer 2024** is not in the repo; its radial-form and "periods per unit
   length" attributions are recorded from the user's review, not verified here.
2. **Zone-edge convention** (π/a vs 2π/a) is our assumption; it moves `k_max` by
   2× and the k-measure by 4×.
3. **In-plane effective masses** are standard GaAs values, not the paper's.
4. **The §6 tensor factor-of-two statements** need verification against the 2026
   and Fathi PDFs.
5. `nextnano++` **`erf` availability in `analytic_function` is unverified** — the
   free build cannot execute imports or analytic functions, and `--parse` accepts
   arbitrary function strings (a deliberately bogus one parsed clean).
