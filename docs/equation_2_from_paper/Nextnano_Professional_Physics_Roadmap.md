# Nextnano++ Professional Physics Roadmap

## Guiding Strategy

**Collect broadly, analyze narrowly.**

When a Professional run is already being performed, save any low-overhead raw outputs that may support later analysis, while keeping each demo focused on one scientific question.

The goal is to avoid repeatedly rerunning expensive nextnano++ Professional calculations just because a useful output was not saved the first time.

---

## 1. Runtime / Effort Tiers

| Tier | Typical cost | Meaning |
|---|---|---|
| **Tier 0 — Capture** | Negligible extra compute; more disk usage | Save richer outputs from a run already being performed |
| **Tier 1 — Short targeted** | Minutes to ~1 hour | Small pilot or one limited kp8 deck |
| **Tier 2 — Medium** | ~1–4 hours | One serious 1D finite-k Professional calculation |
| **Tier 3 — Large** | Several hours to ~1 day | Several decks, geometry comparisons, or physics comparisons |
| **Tier 4 — Very large** | ~day(s) | Full 2D k-space, large parameter sweeps, continuum studies |
| **Tier 5 — Advanced / external** | Days+ | Excitons, many-body models, DFT, major model development |

These are planning estimates only. Actual runtime depends on grid size, number of states, kp8 output volume, solver settings, and workstation performance.

---

## 2. Category A — State Physics and Finite-k Wavefunctions

This is the highest-priority category and should be the core of Demo 25.

| Physics / output | Tier | Why it matters |
|---|---:|---|
| More electron states | 0–2 | Search beyond e1/e2 and identify additional physically relevant transitions |
| More hole states | 0–2 | Same for HH/LH states |
| Enough states to cover an energy window | 0–2 | Avoid missing relevant states because of energy ordering |
| E_n(k) for every retained state | 0 | Fundamental reusable dataset |
| Full finite-k envelopes | 0–2 | Needed to test M(k)=M(0) directly |
| Full kp8 spinor components | 0–2 | Needed for rigorous multiband state/matrix analysis |
| CB/HH/LH/SO fractions vs k | 0 | Tracks physical state identity |
| Relative spinor phases/signs | 0 if exportable | Important for interference and complex matrix elements |
| State-overlap tracking between adjacent k points | 0–1 | Detects state swaps and avoided crossings |
| Bound/quasi-bound/continuum classification | 0–1 | Prevents interpreting unbound numerical states as QW states |
| Localization in each well/barrier | 0–1 | Shows state transfer/localization |
| <z>(k) | 0–1 | Directly related to asymmetric-QW dipole physics |
| Layer-resolved probability | 0–1 | Gives simple physical localization diagnostics |

**Suggested demo:** Demo 25 — Finite-k state + matrix-element capture.

Start with a small pilot. Only launch the larger production run if the pilot proves that finite-k state/wavefunction output is actually available.

---

## 3. Category B — Optical Matrix-Element Physics

Also include in Demo 25 if nextnano can export these quantities without dramatically increasing runtime.

| Physics / output | Tier | Why it matters |
|---|---:|---|
| O_nm(k) electron-hole overlaps | 0–2 | Tests the fixed-overlap approximation |
| z^e_nl(k) | 0–2 | Electron-side Equation 2 numerator |
| z^hh_ml(k) | 0–2 | Hole-side Equation 2 numerator |
| Full pairwise z matrices | 0–2 | Future-proofs expanded Equation 2 calculations |
| Optical momentum matrix elements | 0–2 | Independent optical-strength check |
| Direct dipole/position matrix elements | 0–2 | Cross-check against reconstructed matrix elements |
| Oscillator strengths | 0–1 | Identifies optically bright transitions |
| Polarization-resolved oscillator strengths | 0–2 | Important specifically for chi^(2)_xzx |
| Complex optical matrix elements | 0–2 | Retains phase/sign, not only magnitude |
| All pairwise optical strengths | 0–2 | Screens additional states without another solver run |

**Main question:** Does M(k) differ enough from M(0) to change the resonance peaks and cancellation structure?

---

## 4. Category C — Band Structure, Confinement, and Continuum Physics

| Physics | Tier | Why it matters |
|---|---:|---|
| Ec(z), HH/LH/SO band edges | 0 | Verifies exact solved confinement potential |
| Barrier heights | 0 | Determines when states become unbound |
| Continuum thresholds | 0 | Important for high-energy-state interpretation |
| Raw eigenvectors | 0–2 | Maximum future reusability |
| dE/dk | Python after capture | Group-velocity / dispersion diagnostic |
| d²E/dk² | Python after capture | Effective mass and nonparabolicity |
| Avoided-crossing analysis | Python after capture | Finds strong state mixing |
| DOS / subband DOS | Mostly Python | Helps quantify available in-plane states |
| Every DeltaE_nm(k) | Python | Enables future resonance searches without new solver runs |
| Explicit continuum-state contributions to chi^(2) | 3–4 | Tests whether bound-state truncation misses high-energy response |

**Suggested later demo:** Demo 27 or 28 — Extended-state / continuum validation, only if Demo 25 shows higher or quasi-continuum states might contribute.

---

## 5. Category D — Exact Structure / Paper Reproduction Physics

Given the Demo 26 findings, this category is very high priority.

| Physics | Tier | Why it matters |
|---|---:|---|
| Exact abrupt paper geometry | 2 | Current graded geometry may not match the paper calculation |
| Current 1-nm graded geometry | Existing baseline | Comparison reference |
| Abrupt vs graded direct comparison | 2–3 | Tests structural origin of spectral mismatch |
| Exact x_Al(z) profile | 0 | Reproducibility |
| Exact numerical band offsets | 0 | Verifies material model |
| Central barrier thickness sensitivity | 3 | Strongly affects coupled-well states |
| Well-width sensitivity | 3 | Shifts resonance energies |
| Al composition sensitivity | 3 | Alters band offsets and transition energies |
| Interface grading width | 3 | Alters energies and matrix elements |
| Interface profile shape | 3 | Linear / erf / cosine / etc. |
| Interface roughness / disorder | 4 | Adds realistic spatial disorder and broadening |

**Suggested demo:** Demo 27 — Exact paper geometry reproduction.

Compare current graded structure vs exact abrupt paper structure. Do not optimize geometry yet.

---

## 6. Category E — Electrostatic Physics

| Physics | Tier | Why it matters |
|---|---:|---|
| Flat-band Schrödinger calculation | Baseline | Current/simple reference |
| Self-consistent Schrödinger-Poisson | 2–3 | Can shift state energies and localization |
| Hartree/electrostatic potential | 0 if computed | Shows actual internal potential |
| Charge density | 0 | Needed to understand Poisson solution |
| Doping profile | 0 | Reproducibility |
| Carrier occupations | 0 | Determines charge/self-consistency |
| Applied electric field | 2–3 | Tests quantum-confined Stark response |
| Bias sweep | 3–4 | Maps field sensitivity of chi^(2) |
| Piezoelectric field | 1–2 if applicable | Probably secondary for this material system |

**Suggested demo:** Demo 28 — Flat-band vs Schrödinger-Poisson.

---

## 7. Category F — k-Space Physics

| Physics | Tier | Why it matters |
|---|---:|---|
| 1D radial k to current cutoff | Existing baseline | Current method |
| Larger radial kmax | 2 | Resolves BZ-cutoff ambiguity |
| More radial k points | 2 | Convergence |
| Multiple crystallographic directions | 2–3 | Tests anisotropy |
| Gamma-X vs other directions | 2–3 | Checks directional band mixing |
| Full kx,ky map | 4 | Directly removes radial/isotropic approximation |
| Full 2D matrix elements | 4–5 | Much larger output/computation |
| Angular dependence of HH/LH mixing | 3–4 | May alter pathway strengths |
| Angular dependence of optical matrices | 3–4 | Direct nonlinear-optics relevance |

**Suggested demos:** Demo 29A — Larger radial kmax; Demo 29B — Directional anisotropy; Demo 29C — Full 2D kx,ky.

Proceed in that order.

---

## 8. Category G — Temperature / Linewidth / Scattering Physics

| Physics | Tier | Why it matters |
|---|---:|---|
| Temperature-dependent band parameters | 2–3 | Moves gaps and band offsets |
| Temperature sweep | 3 | Tests spectral peak shifts |
| Constant Gamma = 5 meV | Baseline | Paper assumption |
| Different constant Gamma | Python | Already largely tested |
| State-dependent Gamma_n | 2–3 | Different states may have different lifetimes |
| k-dependent Gamma(k) | 3 | High-k states may broaden differently |
| Energy-dependent Gamma(E) | 3 | More realistic lineshape |
| Interface/scattering-derived linewidth | 4 | More sophisticated physical model |

**Suggested demo:** Demo 30 — Temperature and linewidth physics.

---

## 9. Category H — Strain, Spin, and Multiband Corrections

| Physics | Tier | Why it matters |
|---|---:|---|
| Strain tensor | 0–2 | Changes HH/LH splitting |
| Strain-shifted band edges | 0–2 | Alters state energies |
| Spin splitting vs k | 0–2 | Tests spin-degeneracy assumption |
| Spin-resolved optical transitions | 1–3 | Tests whether branches contribute differently |
| Full HH/LH/SO mixing | High priority capture | Important at finite k |
| Kramers-pair tracking | 0–2 | Prevents accidental branch switching |

Capture these if cheap; do not create a dedicated demo unless the data say they matter.

---

## 10. Category I — Excitonic and Many-Body Physics

| Physics | Tier | Why it matters |
|---|---:|---|
| Exciton binding / Coulomb interaction | 4–5 | Can shift and enhance interband resonances |
| Electron-hole correlated states | 4–5 | Beyond independent-particle Equation 2 |
| State filling | 3–4 | Alters occupation factors |
| Screening | 4–5 | Changes optical interaction |
| Carrier-density effects | 3–4 | Relevant at high excitation |
| Many-body band-gap renormalization | 5 | Can move resonances |
| Coulomb enhancement of oscillator strengths | 4–5 | Changes peak magnitude and shape |

**Suggested demo:** Demo 31 — Exciton / many-body feasibility study.

---

## 11. Category J — Microscopic Bloch Matrix-Element Physics

| Physics | Tier | Why it matters |
|---|---:|---|
| Constant r_e,hh | Baseline | Current approximation |
| r_e,hh(k) | 4–5 | May vary with HH/LH mixing |
| Band-character-dependent interband coupling | 4–5 | More physical for strongly mixed states |
| Composition dependence of r | 4–5 | Tests GaAs vs AlGaAs environment |
| Independent DFT r_e,hh | 5 | Validates microscopic input |
| DFT vs kp optical matrix elements | 5 | Cross-method validation |

**Suggested demo:** Demo 32 — Bloch matrix-element validation.

---

## 12. Additional Category — Solver / Model Cross-Validation

Potential comparisons:

- kp8
- simpler effective-mass / single-band model where appropriate
- kp6 for valence states if available
- nextnano direct optical-transition outputs
- independent Python reconstruction

**Why it helps:** Isolates which spectral features specifically arise from multiband kp8 physics.

**Tier:** 2–3.

---

## 13. Additional Category — Numerical Domain / Boundary Convergence

Test:

- simulation-domain thickness
- outer barrier thickness
- spatial grid spacing
- boundary conditions
- number of requested eigenstates
- state proximity to simulation boundaries

**Why it helps:** Higher and quasi-bound states can be sensitive to numerical-domain choices, and numerical artifacts can masquerade as physical resonances.

**Tier:** 1–2.

---

## 14. Recommended Demo Sequence

### Demo 25 — Finite-k Data Harvest
**Tier 1 → 2**

Capture higher states, full spinors, finite-k envelopes, optical matrix elements, oscillator strengths, localization, confinement, band edges, and raw eigenvectors.

### Demo 27 — Exact Paper Structure
**Tier 2**

Compare current graded structure with the exact abrupt paper structure.

### Demo 28 — Schrödinger vs Schrödinger-Poisson
**Tier 2–3**

Determine whether self-consistent electrostatics changes state energies, localization, and spectral structure.

### Demo 29 — k-Space Validation
- **29A:** Larger radial kmax — Tier 2
- **29B:** Several crystallographic directions — Tier 3
- **29C:** Full 2D kx,ky — Tier 4

### Demo 30 — Temperature / Linewidth
**Tier 3**

Test temperature dependence and physically improved broadening models.

### Demo 31 — Continuum / Exciton / Many-Body
**Tier 4–5**

Only if higher-energy spectral features remain unexplained.

### Demo 32 — Microscopic Interband Matrix Element
**Tier 5**

Test r_e,hh(k), band-character dependence, and potentially independent DFT validation.

---

## 15. Priority for Reproducing the Paper

If the immediate goal is paper reproduction, prioritize:

1. Exact structure
2. Correct state identity and matrix-element data
3. Finite-k M(k)
4. Schrödinger-Poisson equivalence
5. k-space / BZ convention
6. Numerical domain convergence
7. More advanced physics only after the above are settled

Delay major compute on excitons, many-body physics, DFT, temperature sweeps, and full 2D k-space until the simpler reproduction issues are resolved.

---

## 16. Core Rule for Every Future Professional Run

Before every expensive nextnano++ Professional calculation, ask:

1. **What physical question is this run intended to answer?**
2. **What low-overhead raw outputs can be saved now that may prevent another Professional run later?**

> **Collect broadly, analyze narrowly.**

A geometry demo can still save complete states, spinors, matrix elements, localization, oscillator strengths, and raw eigenvectors even though the scientific question for that demo is only geometry.
