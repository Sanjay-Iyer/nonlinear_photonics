# Nextnano++ Professional Physics Capture Reference

## Purpose

This document is a reference for deciding what physics and raw outputs are worth saving during future nextnano++ Professional runs for the coupled GaAs/AlGaAs quantum-well nonlinear-optics project.

The guiding strategy is:

> **Collect broadly, analyze narrowly.**
>
> When a Professional run is already being performed, save any low-overhead finite-k outputs that may support later analysis, while keeping the scientific question for that demo focused.

This is especially important because Professional finite-k calculations are expensive, and a richer raw dataset may prevent the need for another solver run later.

---

# 1. Highest-priority physics to capture now

These are the outputs that should be prioritized for Demo 25 because they are directly relevant to the current spectral-shape problem and the missing approximately 2.296 eV transition.

## 1. More electron and hole states than the current four-state model

Do not stop at `e1`, `e2`, `hh1`, and `hh2`. Save several higher-energy electron and hole states together with their physical character.

**Why it helps:** The missing paper peak pair near approximately 540/1080 nm appears to require a transition energy near 2.296 eV, so higher states may reveal a physically relevant transition that the current four-state model cannot represent.

Recommended information to save for every state:

- Energy versus `k`
- State index and tracked physical identity
- Bound / quasi-bound / continuum-like classification
- Electron, HH, LH, and SO character
- Localization in each well/barrier
- Optical transition strength if available

---

## 2. Full finite-k spinor character

Save CB/HH/LH/SO fractions at every sampled `k` for all retained states.

**Why it helps:** This reveals HH-LH mixing, avoided crossings, changes in state identity, and regions where a nominal heavy-hole state is no longer predominantly heavy-hole-like.

Useful outputs:

- CB fraction
- HH fraction
- LH fraction
- SO fraction
- Full spinor coefficients if available
- State-tracking confidence or overlap with the previous k point

---

## 3. Finite-k wavefunctions / envelopes

Save the wavefunctions or envelope functions at every `k`, not only at `k = 0`.

These are needed to calculate:

`O_nm(k) = <psi_hh,m(k) | psi_e,n(k)>`

`z_e,nl(k) = <psi_e,n(k) | z | psi_e,l(k)>`

`z_hh,ml(k) = <psi_hh,m(k) | z | psi_hh,l(k)>`

**Why it helps:** Demo 23 used the approximation `M(k) = M(0)`. Finite-k wavefunctions allow that approximation to be tested directly and may explain the misplaced cancellation features near approximately 605 and 1330 nm.

---

## 4. Optical matrix elements directly from nextnano, if available

Save any finite-k optical quantities that nextnano++ can export directly, including:

- Momentum matrix elements
- Dipole matrix elements
- Position matrix elements
- Oscillator strengths
- Polarization-resolved transition strengths

**Why it helps:** Direct solver outputs provide an independent cross-check against matrix elements reconstructed from the envelope functions and may reveal additional multiband physics.

Important: document units and conventions carefully. Do not assume momentum and position matrix elements are interchangeable without the proper conversion.

---

## 5. Localization and confinement information

For every state and every `k`, save enough information to determine where the state is located and whether it remains confined.

Useful quantities:

- Probability in wide well
- Probability in narrow well
- Probability in barrier regions
- Probability near simulation boundaries
- Expectation value `<z>`
- Localization length if available
- Bound / leaking / continuum-like status

**Why it helps:** A transition at the correct energy is not useful if one of the participating states has become unbound or barrier-like. This is particularly important when searching for the approximately 2.296 eV transition.

---

## 6. Enough states to cover an energy window, not only a fixed state count

Choose the number of states so the calculation spans the energy range needed to test the missing resonances.

**Why it helps:** Requesting only a fixed number such as four electron and four hole states could still miss the physically relevant state if the energy ordering changes or if several barrier-like states appear first.

Practical target:

- Retain enough electron and hole states to search all physically meaningful transitions through and beyond approximately 2.30 eV.
- Track whether those states remain bound and optically active.

---

## 7. Raw band-edge potentials and state energies

Save the solved band-edge profiles and all corresponding state energies.

Useful outputs:

- Conduction-band edge `Ec(z)`
- Heavy-hole / light-hole valence-band edges
- Spin-orbit band edge if available
- All eigenenergies versus `k`
- Barrier heights and continuum thresholds

**Why it helps:** These data make it possible to determine why a state exists or does not exist and whether a required transition is fundamentally inaccessible in the current structure.

---

# 2. Additional high-value physics to capture when low-overhead

These quantities may not be necessary for the immediate Demo 25 question, but they are valuable future-proofing if nextnano can save them without requiring a major new calculation.

## 8. Complex optical momentum or dipole matrix elements versus k

Save the full complex matrix elements when available, not only their magnitudes.

**Why it helps:** The phase and sign of optical amplitudes can determine whether Equation 2 pathways cancel or reinforce each other.

---

## 9. Polarization-resolved optical transition strengths

Save optical strengths separately for the relevant Cartesian polarizations.

**Why it helps:** A transition may exist energetically but couple weakly to the polarization required for `chi^(2)_xzx`, so polarization information distinguishes an energetically allowed state from an optically relevant one.

---

## 10. Expectation value `<z>` for every state versus k

Save the mean position of each state along the growth direction.

**Why it helps:** This shows how electron and hole localization changes with `k` and directly relates to the diagonal `z` matrix elements that are important in asymmetric coupled quantum wells.

---

## 11. Layer-resolved wavefunction probability

Save the fraction of each state's probability in each physical layer or well.

**Why it helps:** This gives a simple quantitative description of state transfer between the two wells and can expose localization changes at avoided crossings.

---

## 12. Bound-state / continuum leakage metric

Record whether each state remains physically confined as `k` increases.

**Why it helps:** It prevents continuum or boundary-sensitive numerical states from being mistaken for real confined optical transitions.

---

## 13. Effective mass and local band curvature versus k

Save enough dispersion data to calculate `dE/dk` and `d^2E/dk^2` locally.

**Why it helps:** This identifies where parabolic effective-mass approximations fail and quantifies nonparabolicity without requiring another solver run.

---

## 14. Avoided-crossing diagnostics

Preserve energy, state overlap, spinor character, and localization through suspected crossings.

**Why it helps:** At an avoided crossing, two states can exchange character and their optical matrix elements can change sharply even though the energy curves remain smooth.

---

## 15. Full eight-band spinor components

Save the individual kp8 components rather than only summarized CB/HH/LH/SO percentages when practical.

**Why it helps:** Full spinors permit more rigorous multicomponent matrix-element reconstruction and provide a better diagnostic when states are strongly mixed.

---

## 16. Relative phases / signs of spinor components

Preserve signed or complex spinor amplitudes if nextnano exports them.

**Why it helps:** Probabilities alone lose phase information, while interference and cancellation in nonlinear susceptibility depend on signed/complex amplitudes.

---

## 17. All pairwise oscillator strengths among retained states

Save oscillator strengths for every physically meaningful electron-hole state pair, not only the lowest transitions.

**Why it helps:** This quickly separates bright transitions from energetically correct but optically negligible candidates.

---

## 18. All pairwise z-matrix elements among retained electron and hole states

Save or calculate a complete matrix for the retained state set.

**Why it helps:** If Equation 2 is later expanded beyond `e1/e2/hh1/hh2`, the required intersubband matrix elements will already be available.

---

## 19. Exact band-edge profiles for the solved structure

Preserve the final numerical `Ec(z)` and valence-band profiles used in the actual solver calculation.

**Why it helps:** These profiles allow later verification that the calculation used the intended geometry, composition, offsets, and confinement potentials.

---

## 20. Electrostatic / Hartree potential

Save the electrostatic potential if the calculation includes self-consistent Poisson physics.

**Why it helps:** Internal electrostatic shifts can change localization and transition energies and may matter if future calculations become self-consistent rather than flat-band.

Note: if the current deck is intentionally a flat-band quantum solve with no Poisson self-consistency, record that explicitly instead of implying such a field exists.

---

## 21. Local material-composition profile `x_Al(z)`

Save the exact composition profile actually passed to the solver.

**Why it helps:** It makes abrupt versus graded interface comparisons reproducible and allows later debugging of whether the modeled structure truly matches the intended paper geometry.

---

## 22. Strain and strain-shifted band edges, if applicable

Save strain tensors and strain-induced band shifts if strain physics is enabled.

**Why it helps:** Strain changes heavy-hole/light-hole splitting and can therefore alter state ordering, mixing, and optical selection rules.

For the current GaAs/AlGaAs system this may be small or absent, but it is valuable to record whether strain was included.

---

## 23. Piezoelectric potential / field, if applicable

Save piezoelectric fields if the material system and solver model generate them.

**Why it helps:** Internal polarization fields can shift carrier localization and optical transition energies, although this is likely secondary for the present GaAs/AlGaAs structure.

---

## 24. Spin-resolved state information

Save spin splitting and spin character at finite `k` if the kp8 solver reports them.

**Why it helps:** It allows future verification that spin splitting is negligible or identifies cases where separate spin branches affect the optical spectrum.

---

## 25. Density of states / subband DOS information

Save or calculate DOS information for the retained subbands.

**Why it helps:** DOS helps quantify how many in-plane states contribute near a resonance and can be useful when extending the model beyond the current simplified weighting.

---

## 26. Transition-energy table for every plausible electron-hole pair

Precompute and save `DeltaE_nm(k)` for all retained electron-hole combinations.

**Why it helps:** Future resonance searches can be performed entirely in Python without rerunning nextnano.

---

## 27. Raw solver eigenvectors before heavy post-processing

Preserve the most complete raw eigenvector/state output that is practical.

**Why it helps:** Raw eigenvectors are the most reusable asset because many later observables can potentially be reconstructed from them even if the original demo did not anticipate the analysis.

---

# 3. Physics worth considering later, but not necessary to add to Demo 25

The following are important possible sources of disagreement with the paper, but they introduce genuinely new physics or substantially larger calculations. They should normally be deferred until Demo 25 establishes whether the simpler missing-physics hypotheses are sufficient.

## 28. Full 2D `kx, ky` integration

Replace the radial/isotropic approximation with explicit two-dimensional in-plane integration.

**Why it helps:** This directly tests whether anisotropy or angular dependence changes the normalized spectral shape.

---

## 29. Multiple crystallographic directions

Calculate equivalent dispersions and optical quantities along several in-plane directions.

**Why it helps:** This tests whether the radial approximation hides direction-dependent HH/LH mixing or optical coupling.

---

## 30. Exact paper-geometry reconstruction

Build the precise nominal/experimental layer structure represented by the paper's comparison curve.

**Why it helps:** If the required approximately 2.296 eV transition does not exist in the current structure, a geometry/material mismatch becomes a leading explanation.

---

## 31. Interface grading / roughness models

Introduce physically motivated graded interfaces or roughness rather than an ideal abrupt profile.

**Why it helps:** Interface structure changes confinement energies, localization, matrix elements, and linewidths, potentially reshaping the spectrum.

---

## 32. Temperature dependence

Repeat the calculation at selected temperatures with temperature-dependent material parameters.

**Why it helps:** Band gaps, offsets, occupations, and linewidths change with temperature and shift resonance positions.

---

## 33. Energy- or state-dependent broadening `Gamma(E,k)`

Replace the constant 5 meV linewidth with a physically motivated state/energy-dependent model.

**Why it helps:** Different resonances may have different lifetimes and widths, which can alter peak shape and cancellation depth.

---

## 34. Excitonic effects

Include electron-hole Coulomb interaction near interband resonances.

**Why it helps:** Excitons can shift resonance energies, enhance optical strength, and reshape interband optical spectra beyond independent-particle kp predictions.

---

## 35. Continuum-state contributions

Include physically meaningful unbound or quasi-continuum electron/hole states in the optical response where justified.

**Why it helps:** High-energy paper features may involve transitions that are not represented by a bound-state-only truncation.

---

## 36. Many-body / carrier-population effects

Include state filling, screening, or carrier-dependent corrections when relevant to the experimental conditions.

**Why it helps:** At high carrier density, occupations and interactions can change both resonance energies and optical amplitudes.

---

## 37. k-dependent microscopic Bloch interband matrix element `r_e,hh(k)`

Test whether the microscopic unit-cell interband coupling can truly be treated as constant with `k` and state mixing.

**Why it helps:** Demo 25 tests finite-k envelope matrix elements, but the Bloch-scale interband strength may also vary as HH/LH character changes.

This may require a careful kp optical-matrix-element treatment or additional DFT rather than only nextnano output.

---

## 38. Independent DFT validation of Bloch-scale optical matrix elements

Use first-principles calculations to validate interband matrix elements and their dependence on composition or band character.

**Why it helps:** This checks one of the microscopic inputs to Equation 2 independently of the envelope-function calculation.

---

## 39. Self-consistent Schrödinger-Poisson physics

Add Poisson self-consistency when carrier density, doping, built-in fields, or experimental bias make it physically necessary.

**Why it helps:** Electrostatic redistribution can move wavefunctions and transition energies compared with the current flat-band calculation.

---

## 40. External electric-field / bias dependence

Apply controlled fields across the coupled wells.

**Why it helps:** The quantum-confined Stark effect shifts levels and localization and provides a strong diagnostic of how sensitive the nonlinear response is to the wavefunction positions.

---

# 4. Recommended Demo 25 capture package

For the upcoming targeted Professional calculation, the recommended strategy is to save the following if the pilot proves nextnano can export them at finite `k`:

### Essential

- Extended electron and hole state energies
- Finite-k CB/HH/LH/SO character
- Finite-k wavefunctions / envelopes
- Electron-hole overlaps `O_nm(k)`
- Electron `z_e,nl(k)` matrix elements
- Heavy-hole `z_hh,ml(k)` matrix elements
- Localization / confinement metrics
- Band-edge profiles
- Transition energies for all retained state pairs

### Strongly preferred

- Full kp8 spinor components
- Optical momentum/dipole matrix elements
- Oscillator strengths
- Polarization-resolved optical strengths
- Full pairwise z-matrix elements
- Full pairwise electron-hole optical strengths
- Raw solver eigenvectors

### Save if essentially free

- Exact composition profile
- Electrostatic potential, if computed
- Strain, if computed
- Piezoelectric field, if computed
- Spin-resolved information
- DOS / curvature diagnostics

---

# 5. What not to expand Demo 25 into

Demo 25 should remain focused on:

1. obtaining finite-k matrix-element-capable output;
2. testing `M(k) = M(0)`;
3. searching for additional optically relevant states near the missing approximately 2.296 eV transition;
4. diagnosing HH/LH mixing and confinement.

Do **not** automatically turn Demo 25 into:

- a geometry optimization;
- a full 2D-k campaign;
- a temperature study;
- an interface-roughness study;
- an exciton calculation;
- a DFT campaign;
- a broadening-fit exercise.

Those should be separate, controlled demos if Demo 25 shows they are necessary.

---

# 6. Quick-reference priority table

| Physics / output | Capture now? | Main use |
|---|---|---|
| Higher electron/hole states | **Yes** | Search missing 2.296 eV transition |
| Finite-k wavefunctions | **Yes** | Calculate finite-k overlaps and z elements |
| CB/HH/LH/SO fractions | **Yes** | Track mixing and state identity |
| Localization / confinement | **Yes** | Reject unbound / continuum artifacts |
| Optical matrix elements | **Yes, if available** | Cross-check Equation 2 numerator physics |
| Oscillator strengths | **Yes, if available** | Identify optically bright transitions |
| Pairwise z matrix elements | **Yes** | Future expanded Equation 2 models |
| Raw eigenvectors | **Yes, if storage allows** | Maximum future reuse |
| Exact band edges / composition | **Yes** | Reproducibility and geometry audit |
| Full 2D kx-ky | Later | Test anisotropy/radial approximation |
| Exact paper geometry | Later if needed | Resolve structural mismatch |
| Temperature sweep | Later | Test thermal spectral shifts |
| Excitons | Later | Improve interband resonance physics |
| Energy-dependent Gamma | Later | Improve linewidth / shape physics |
| r_e,hh(k) / DFT | Later | Test microscopic interband coupling |
| Schrödinger-Poisson | Later if needed | Include electrostatic redistribution |

---

# 7. Core rule for future Professional runs

Before every expensive nextnano++ Professional calculation, ask two questions:

1. **What physical question is this run intended to answer?**
2. **What low-overhead raw outputs can I save now that may prevent another Professional run later?**

The goal is not to calculate every possible model at once. The goal is to preserve enough high-quality raw physics that future controlled analyses can often be performed entirely in Python.
