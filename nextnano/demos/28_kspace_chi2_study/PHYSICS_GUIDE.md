# Understanding the calculation before a meeting

## The short version

nextnano calculates electronic states for a layered quantum-well structure. Python uses their energies and wavefunctions to construct the quantities in the paper's Equation 2. It evaluates all allowed terms in the retained two-electron/two-valence-state model, adds their complex contributions over in-plane momentum, and only then separates the answer into real and imaginary parts.

A safe description is: **“We followed Equation 2, including its broadening terms, to reproduce the historical calculation. The imaginary component is part of that complex response; we have not independently calculated a nonlinear absorption measurement or propagated photoexcited carrier populations.”**

The baseline is historical, not assumption-free. Its energy alignment, frozen matrices, radial approximation, selected states, linewidth and prefactor all matter. One historical valence branch is LH-like rather than HH-like. Reproducing a saved result verifies implementation continuity; it does not remove those model limitations.

## What the four curves mean

The second-order susceptibility chi^(2) relates a second-order polarization to products of electric fields. In a scalar SHG shorthand, P(2omega) is proportional to epsilon0 chi^(2)(-2omega;omega,omega) E(omega)^2. Tensor direction and complex-amplitude conventions affect the exact expression; this package preserves the paper-engine convention rather than refitting it.

Write chi = A+iB.

| Curve | Meaning | Can be negative? |
|---|---|---|
| Re chi = A | Real component in the chosen phase/Fourier convention | Yes |
| Im chi = B | Quadrature component in that convention | Yes |
| abs(Re chi) = abs(A) | Real component with its sign removed | No |
| abs(chi) = sqrt(A^2+B^2) | Full complex magnitude | No |

For example, chi=3+4i has Re=3, Im=4, abs(Re)=3 and abs(chi)=5. If Re crosses zero while Im remains 4, abs(Re) vanishes but abs(chi) remains 4. An absolute-value plot alone hides the sign crossing. This is why we retain both signed components throughout the calculation.

The absolute signed-component plots use pm/V under the retained prefactor convention. Paper overlays are explicitly normalized shape comparisons, not absolute-unit validation. Do not independently normalize Re and Im if comparing their relative size; use one common scale or retain pm/V.

## States, envelopes and matrix elements

An envelope wavefunction psi describes the slowly varying spatial amplitude of an electronic state across the layered structure. Its square magnitude is a probability density after normalization. Electron conduction states are labeled e1,e2. HH and LH denote heavy-hole and light-hole band character; those labels describe components of the valence-band model, not tracked populations of actual holes.

The code stores valence states on the **electron-energy reference**. Transition energies are Ee-Ev, not Ee plus a positive hole-excitation energy. The historic variables `valence_eV` / `hole_energies.csv` must be interpreted accordingly.

The growth coordinate is called z in the envelope integrals and Eq2 notation. The one-dimensional nextnano deck uses its x coordinate along growth. A name change is not a physical rotation of the calculated state.

An overlap O_nm = integral psi_e,n* psi_h,m dz measures how two normalized envelopes spatially overlap. It is dimensionless, can have a sign/phase, and is not a carrier density. A z matrix element is integral psi_a* z psi_b dz, measured in nm. The z operator multiplies a wavefunction by its position. A diagonal z element is a mean position; an off-diagonal element describes a position-coupling amplitude between states.

The baseline envelopes are real single-band functions. `matrix_elements.py` integrates them spatially with trapezoidal weights. O, ze and zh are (2,2) and are then explicitly repeated across k. No finite-k matrix-element evolution is measured by that repetition.

Individual state phases are arbitrary. Rephasing a state changes individual overlaps, but the complete products entering Eq2 must not change. `pathway_definitions` forms conjugated gauge-invariant products; tests verify rephasing leaves the spectrum unchanged. Do not interpret the phase of one overlap as an observable.

## Equation 2, term by term

The code expresses the paper's frequency denominators in energy units. Let T_nm(k)=Ee,n(k)-Ev,m(k) and h=hc/lambda= hbar omega. Then the retained model is

```text
chi(lambda) = prefactor * sum_k weights(k) * sum_m,n,ell [
    conj(O_nm) ze_nell O_ell,m / [(T_nm-2h+iGamma)(T_ell,m-h+iGamma)]
  - O_nm zh_mell conj(O_nell) / [(T_nm-2h+iGamma)(T_nell-h+iGamma)]
]
```

The first line has an intermediate electron state; the second an intermediate valence state. Each has 2 x 2 x 2 = 8 pathways. The second line includes the explicit minus sign. “Electron contribution” and “hole contribution” here name groups of response pathways, not populations or independent absorption channels.

| Symbol | Python variable / entry | Meaning and source |
|---|---|---|
| m | `pathway['m']` | valence index, zero-based |
| n | `pathway['n']` | electron index, zero-based |
| ell | `pathway['ell']` | intermediate electron in C, valence in V |
| O | `inputs['overlap']`, local `o` | dimensionless envelope overlap |
| ze | `inputs['ze_nm']`, local `ze` | electron position matrix, nm |
| zh | `inputs['zh_nm']`, local `zh` | valence position matrix, nm |
| T | `transition` in `pathway_definitions` | Ee-Ev, eV |
| hbar omega | `hw`, from `photon_energy` | 1239.841984 / wavelength_nm, eV |
| 2 hbar omega | `2*hw` | second-harmonic photon energy |
| Gamma | `Settings.gamma_eV` | `gamma_meV*1e-3`, eV |
| iGamma | `g` | `1j*gamma_sign*gamma_eV`; default positive |
| two-photon denominator | `d2` | T_nm-2hw+g |
| one-photon denominator | `d1` | relevant intermediate transition-hw+g |
| pathway numerator | `pathway['numerator']` | complete product including V minus sign, nm |
| k weight | `weights` | radial integration area, nm^-2 |
| Nz | `nz` in `prefactor` | retained 1/period, m^-1 |
| r_e,hh | `settings.r_e_hh_nm` | fixed literature unit-cell dipole length, 0.751 nm |
| chi(k,lambda) before measure | `summed_integrand` | unweighted pathway sum, nm/eV^2; not yet pm/V |
| chi(lambda) | `Spectrum.chi2_complex` | weighted, prefactored complex response, pm/V |

All algebra above is in `chi2/equation2.py`. `calculate_chi2` accepts positive fundamental wavelengths. `calculate_chi2_energy` exposes the same loop on signed energies for the causality audit; it does not add new physical terms.

### What does 1e-3 mean?

It converts millielectronvolts to electronvolts: 1 meV = 0.001 eV, so 5 meV = 0.005 eV. Since the other denominator terms are in eV, Gamma must be too. It is a unit conversion, not an extra fitted physics parameter.

### Resonance and broadening

A denominator becomes small when T approximately equals hw (one-photon condition) or 2hw (two-photon condition). Each transition has its own dispersion, so adding k states can add resonances at other wavelengths. A peak of the final sum is not necessarily exactly at one denominator's minimum: several pathways interfere and cancel.

For one simple factor,

```text
1/(Delta+iGamma) = (Delta-iGamma)/(Delta^2+Gamma^2).
```

It is complex even if its numerator is real. Far from its pole its imaginary part is relatively small; near the pole it can be important. Eq2 contains products of factors and a signed sum, so this example is intuition, not a theorem that Im must dominate at every resonance or that Re cannot vanish elsewhere.

The baseline's complete numerators are real to machine representation. Making them explicitly real changes chi by zero. Thus the imaginary response in **this baseline** is quantitatively explained by the broadened denominators; the pathway sum determines the final shape and cancellation. This does not establish the same fact for an arbitrary finite-k spinor model.

As Gamma becomes small, off-resonant Im decreases. Near poles the response can become narrow and require much finer k and frequency grids. Our 0.1 meV case is a sensitivity experiment, not proof of a converged Gamma→0 limit. We never evaluate Gamma=0 at a pole.

## Why no dynamic carrier populations are needed here

The paper derives a perturbative response using a filled initial valence-state assumption (occupation factor unity). That is an occupation assumption, even though no time-dependent population equation is integrated in our Python code. A weak-field response coefficient can include damping and phase delay under such a fixed initial state.

This is different from calculating how an optical pulse injects carriers, how their populations change, and how those carriers relax or modify the bands. Neither the baseline nextnano decks nor Eq2 implement that dynamic simulation. See the verified paper passages in `PAPER_AUDIT.md`.

An imaginary nonlinear coefficient should not automatically be called a measured nonlinear absorption coefficient. Relating it to absorbed power requires the appropriate frequencies, fields, tensor components and response convention. The present calculation alone does not perform that conversion or validate it experimentally.

## k space and the cutoff

k_parallel is in-plane crystal momentum, with components kx and ky in the theoretical integral (not necessarily the deck's Cartesian names). The Gamma point is k=0; it is unrelated to the linewidth Gamma. A Brillouin zone is a primitive reciprocal-space cell. Calling a distance “0.1 BZ” is incomplete unless the direction, length scale and integration geometry are specified.

The cached solver samples a crystallographic Gamma-to-y path. Python treats that radial dispersion as representative of all in-plane angles:

```text
g_s integral d^2k/(2pi)^2 f(k)
  = g_s/(2pi) integral_0^kmax k f(k) dk    [isotropic assumption]
```

The factor k accounts for the increasing area of a ring in two dimensions. Many modest contributions can therefore accumulate at larger k. Frozen matrices cannot themselves grow with k in this baseline; changing denominators and the radial measure, together with signed cancellation, drive its cutoff dependence.

For nonuniform nodes, the trapezoidal dk factors are half the first/last adjacent interval at endpoints and half the distance between neighboring nodes internally. `radial_weights` multiplies these by g_s*k/(2pi). A constant integrand gives g_s*kmax^2/(4pi); tests verify this exactly to roundoff. Units are nm^-2.

Cutoff selection occurs **before** recomputing weights. Simply slicing full-grid weights would wrongly retain an interior endpoint weight. Shell contributions use adjacent trapezoids and sum back to the integrated response. See the CSV and NPZ in 28B.

Grid-density convergence holds the endpoint fixed while refining samples. Cutoff convergence adds new physical rings at controlled density. These are different limits. The cached 0.125 pi/a run has 301 points just like the baseline but a 25% larger spacing; 28H compares its 241-point truncation with the dense301 baseline at the same endpoint.

## Prefactor and what does not come from nextnano

`prefactor(settings)` retains Nz e^3 r^2/(6 epsilon0), with the hbar factors cancelled when frequency denominators are converted to energy denominators. It explicitly converts z[nm], k-area[nm^-2], energies[eV^2], and the final m/V to pm/V. Its default numerical value is 56.69816882497043 multiplying the saved weighted nm/eV^2 integrand.

Nz=1/(30 nm) is the inherited period-density convention; whether the authors count individual wells or coupled pairs needs clarification for absolute-scale comparison. r=0.751 nm is the 7.51 angstrom value reported in the preceding HSE06/VASP publication, **not** an envelope overlap and **not** a new DFT result calculated by us. Gamma, spin factor, isotropic reduction, wavelength grid and chosen truncation are modeling/numerical inputs, not raw solver outputs.

## Causality: what can safely be said

With inverse exp(+i omega t), positive-iGamma denominators place poles above the real axis and give the lower-half-plane analyticity appropriate to that convention. The degenerate SHG path moves both input frequencies in the same direction, permitting a justified one-dimensional dispersion relation under the stated response assumptions. The numerical check operates on signed, uniform photon energy, not wavelength.

The full-line rational-expression KK test passes its numerical tolerance, but unchanged negative-frequency continuation fails real-field conjugation symmetry. Therefore the audit does not certify a complete real-field material susceptibility. `CAUSALITY_AUDIT.md` gives the derivation, analytic benchmark, edge errors, and precise distinction between mathematical PASS and physical INCONCLUSIVE.
