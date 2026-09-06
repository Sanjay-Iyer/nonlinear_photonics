# Demo 24N per-feature causal statements

DIAGNOSTIC PERTURBATION - NOT A PHYSICAL/FITTED MODEL

```
P1 (paper 540 nm):
    NOTE: the model has no extremum in this window; the quoted model wavelength is the window edge, not a feature
    dominant pathway = C_m1_n1_l1 (electron_side)
    dominant k = 0.5539 /nm (1.00 of kmax; 50% band 0.4075-0.5539 /nm; TRUNCATED - integrand peaks at the k cutoff)
    controlling transition = none within 30 nm (feature is not at a resonance band edge) (nearest edge 687 nm, 112 nm away; k-truncation edge (artifact))
    most sensitive state energy = e1 (dLambda/dE = -7.19e-15 nm/meV)
    most sensitive numerator/pathway = V_m1_n1_l1
    mechanism = off-resonant tail of a strongly cancelling sum
    likely cause of wavelength mismatch = MISSING PHYSICS / MODEL SPACE: the required transition energy exceeds the largest transition any pair of bound subbands in this structure can reach, even extrapolated to the k where the electron leaves the barrier. No k cutoff, energy shift, pathway amplitude, sign, broadening or normalization change can create this feature
    confidence = high

Z1 (paper 605 nm):
    NOTE: the model has no extremum in this window; the quoted model wavelength is the window edge, not a feature
    dominant pathway = C_m1_n1_l1 (electron_side)
    dominant k = 0.5539 /nm (1.00 of kmax; 50% band 0.4186-0.5539 /nm; TRUNCATED - integrand peaks at the k cutoff)
    controlling transition = none within 30 nm (feature is not at a resonance band edge) (nearest edge 687 nm, 137 nm away; k-truncation edge (artifact))
    most sensitive state energy = e1 (dLambda/dE = -7.19e-15 nm/meV)
    most sensitive numerator/pathway = C_m1_n1_l1
    mechanism = off-resonant tail of a strongly cancelling sum
    energy-sensitive? NO
    amplitude-sensitive? YES
    phase-sensitive? YES (robustness probe; numerator phase is not a free parameter)
    electron/heavy-hole cancellation ratio = 0.04283, phase difference -180.0 deg
    likely cause of wavelength mismatch = MISSING PHYSICS / MODEL SPACE: the required transition energy exceeds the largest transition any pair of bound subbands in this structure can reach, even extrapolated to the k where the electron leaves the barrier. No k cutoff, energy shift, pathway amplitude, sign, broadening or normalization change can create this feature
    confidence = high

P2 (paper 760 nm):
    dominant pathway = C_m1_n1_l1 (electron_side)
    dominant k = 0.1871 /nm (0.34 of kmax; 50% band 0.1167-0.3334 /nm; CONVERGED - integrand peaks inside the grid)
    controlling transition = DeltaE_22 one-photon k=0 edge (nearest edge 752 nm, 0 nm away; physical joint-density edge)
    most sensitive state energy = e2 (dLambda/dE = -0.46 nm/meV)
    most sensitive numerator/pathway = C_m1_n1_l1
    mechanism = resonance-driven inside a strongly cancelling sum
    likely cause of wavelength mismatch = ENERGY / DENOMINATOR: the feature tracks a tracked subband energy (e2 at -0.46 nm/meV)
    confidence = high

P3 (paper 1080 nm):
    NOTE: the model has no extremum in this window; the quoted model wavelength is the window edge, not a feature
    dominant pathway = C_m1_n1_l1 (electron_side)
    dominant k = 0.5539 /nm (1.00 of kmax; 50% band 0.3927-0.5539 /nm; TRUNCATED - integrand peaks at the k cutoff)
    controlling transition = none within 30 nm (feature is not at a resonance band edge) (nearest edge 1374 nm, 214 nm away; k-truncation edge (artifact))
    most sensitive state energy = e1 (dLambda/dE = -1.44e-14 nm/meV)
    most sensitive numerator/pathway = C_m1_n1_l1
    mechanism = off-resonant tail of a strongly cancelling sum
    likely cause of wavelength mismatch = MISSING PHYSICS / MODEL SPACE: the required transition energy exceeds the largest transition any pair of bound subbands in this structure can reach, even extrapolated to the k where the electron leaves the barrier. No k cutoff, energy shift, pathway amplitude, sign, broadening or normalization change can create this feature
    confidence = high

Z2 (paper 1330 nm):
    NOTE: the model has no extremum in this window; the quoted model wavelength is the window edge, not a feature
    dominant pathway = C_m1_n1_l1 (electron_side)
    dominant k = 0.5539 /nm (1.00 of kmax; 50% band 0.4446-0.5557 /nm; TRUNCATED - integrand peaks at the k cutoff)
    controlling transition = none within 30 nm (feature is not at a resonance band edge) (nearest edge 1374 nm, 124 nm away; k-truncation edge (artifact))
    most sensitive state energy = e1 (dLambda/dE = -1.44e-14 nm/meV)
    most sensitive numerator/pathway = C_m1_n1_l1
    mechanism = off-resonant tail of a strongly cancelling sum
    energy-sensitive? NO
    amplitude-sensitive? YES
    phase-sensitive? YES (robustness probe; numerator phase is not a free parameter)
    electron/heavy-hole cancellation ratio = 0.0486, phase difference -179.9 deg
    likely cause of wavelength mismatch = k CUTOFF: the wavelength lies outside every one- and two-photon resonance band the four tracked subbands produce over the computed k range, but a bound-subband pair does reach it beyond the cutoff; the integrand is still peaking at the k cutoff, so the sum is truncated
    confidence = high

P4 (paper 1520 nm):
    dominant pathway = C_m1_n1_l1 (electron_side)
    dominant k = 0.1537 /nm (0.28 of kmax; 50% band 0.09818-0.3056 /nm; CONVERGED - integrand peaks inside the grid)
    controlling transition = DeltaE_22 two-photon k=0 edge (nearest edge 1504 nm, 1 nm away; physical joint-density edge)
    most sensitive state energy = e2 (dLambda/dE = -0.92 nm/meV)
    most sensitive numerator/pathway = C_m1_n1_l1
    mechanism = resonance-driven inside a strongly cancelling sum
    likely cause of wavelength mismatch = ENERGY / DENOMINATOR: the feature tracks a tracked subband energy (e2 at -0.92 nm/meV)
    confidence = high
```
