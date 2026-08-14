# Demo 18C best-five interpretation

These are sensitivity cases, not inferred author inputs. A close diagnostic-proxy case only demonstrates reachability within the tested envelope.

## 1. Combo_16

chi2(1550) = 2264.457 pm/V; paper = 2340 pm/V; error = 3.23%.

Changed relative to Demo 18B:

- hh_relative_weight: 1.0 -> 0.6 (DIAGNOSTIC PROXY)

Cancellation:

- Demo 18B electron / HH weighted / net: 5594.044 / 5550.485 / 84.911 pm/V
- Electron: 5594.044 pm/V
- HH raw: 5550.485 pm/V
- HH weighted: 3330.291 pm/V
- Net: 2264.457 pm/V
- Cancellation factor: 131.250 -> 3.941

Physical checks:

- Bound states: PASS
- Orthonormality: PASS
- Transitions E1-HH1 / E1-HH2 / E2-HH1 / E2-HH2: 1.4890 / 1.5220 / 1.5965 / 1.6295 eV
- Spectrum: AMPLITUDE_MATCH_BUT_SPECTRAL_MISMATCH (peak 1663.0 nm)

Interpretation: the electron/HH residual changed through the complete Eq. 2 calculation. DIAGNOSTIC PROXY values must not be reported as paper inputs.

## 2. Combo_17

chi2(1550) = 2178.342 pm/V; paper = 2340 pm/V; error = 6.91%.

Changed relative to Demo 18B:

- hh_relative_weight: 1.0 -> 1.4 (DIAGNOSTIC PROXY)

Cancellation:

- Demo 18B electron / HH weighted / net: 5594.044 / 5550.485 / 84.911 pm/V
- Electron: 5594.044 pm/V
- HH raw: 5550.485 pm/V
- HH weighted: 7770.679 pm/V
- Net: 2178.342 pm/V
- Cancellation factor: 131.250 -> 6.135

Physical checks:

- Bound states: PASS
- Orthonormality: PASS
- Transitions E1-HH1 / E1-HH2 / E2-HH1 / E2-HH2: 1.4890 / 1.5220 / 1.5965 / 1.6295 eV
- Spectrum: AMPLITUDE_MATCH_BUT_SPECTRAL_MISMATCH (peak 1663.0 nm)

Interpretation: the electron/HH residual changed through the complete Eq. 2 calculation. DIAGNOSTIC PROXY values must not be reported as paper inputs.

## 3. Combo_08

chi2(1550) = 1974.204 pm/V; paper = 2340 pm/V; error = 15.63%.

Changed relative to Demo 18B:

- r_e_hh_nm: 0.751 -> 0.941406 (UNCERTAIN)
- electrostatic_field_kV_per_cm: 0.0 -> -18.418271 (DIAGNOSTIC PROXY)
- hh_relative_weight: 1.0 -> 0.765384 (DIAGNOSTIC PROXY)
- well1_nm: 7.1 -> 7.096001 (UNCERTAIN)
- well2_nm: 2.9 -> 2.858181 (UNCERTAIN)
- tunneling_barrier_nm: 1.8 -> 1.805476 (UNCERTAIN)

Cancellation:

- Demo 18B electron / HH weighted / net: 5594.044 / 5550.485 / 84.911 pm/V
- Electron: 8326.975 pm/V
- HH raw: 8300.663 pm/V
- HH weighted: 6353.195 pm/V
- Net: 1974.204 pm/V
- Cancellation factor: 131.250 -> 7.436

Physical checks:

- Bound states: PASS
- Orthonormality: PASS
- Transitions E1-HH1 / E1-HH2 / E2-HH1 / E2-HH2: 1.4885 / 1.5219 / 1.5872 / 1.6206 eV
- Spectrum: AMPLITUDE_MATCH_BUT_SPECTRAL_MISMATCH (peak 1664.0 nm)

Interpretation: the electron/HH residual changed through the complete Eq. 2 calculation. DIAGNOSTIC PROXY values must not be reported as paper inputs.

## 4. Combo_07

chi2(1550) = 1954.474 pm/V; paper = 2340 pm/V; error = 16.48%.

Changed relative to Demo 18B:

- r_e_hh_nm: 0.751 -> 0.767897 (UNCERTAIN)
- electrostatic_field_kV_per_cm: 0.0 -> 0.582619 (DIAGNOSTIC PROXY)
- hh_relative_weight: 1.0 -> 0.68318 (DIAGNOSTIC PROXY)
- well1_nm: 7.1 -> 7.034685 (UNCERTAIN)
- well2_nm: 2.9 -> 2.88371 (UNCERTAIN)
- tunneling_barrier_nm: 1.8 -> 1.740274 (UNCERTAIN)

Cancellation:

- Demo 18B electron / HH weighted / net: 5594.044 / 5550.485 / 84.911 pm/V
- Electron: 6034.697 pm/V
- HH raw: 5974.523 pm/V
- HH weighted: 4081.675 pm/V
- Net: 1954.474 pm/V
- Cancellation factor: 131.250 -> 5.176

Physical checks:

- Bound states: PASS
- Orthonormality: PASS
- Transitions E1-HH1 / E1-HH2 / E2-HH1 / E2-HH2: 1.4899 / 1.5235 / 1.5982 / 1.6317 eV
- Spectrum: AMPLITUDE_MATCH_BUT_SPECTRAL_MISMATCH (peak 1662.0 nm)

Interpretation: the electron/HH residual changed through the complete Eq. 2 calculation. DIAGNOSTIC PROXY values must not be reported as paper inputs.

## 5. Combo_03

chi2(1550) = 1817.252 pm/V; paper = 2340 pm/V; error = 22.34%.

Changed relative to Demo 18B:

- r_e_hh_nm: 0.751 -> 0.670296 (UNCERTAIN)
- electrostatic_field_kV_per_cm: 0.0 -> 11.496125 (DIAGNOSTIC PROXY)
- hh_relative_weight: 1.0 -> 1.249622 (DIAGNOSTIC PROXY)
- kmax_fraction_2pi_over_a: 0.1 -> 0.2 (CONVENTION)
- well1_nm: 7.1 -> 7.086018 (UNCERTAIN)
- well2_nm: 2.9 -> 2.921867 (UNCERTAIN)
- tunneling_barrier_nm: 1.8 -> 1.757685 (UNCERTAIN)

Cancellation:

- Demo 18B electron / HH weighted / net: 5594.044 / 5550.485 / 84.911 pm/V
- Electron: 7070.030 pm/V
- HH raw: 7111.942 pm/V
- HH weighted: 8887.239 pm/V
- Net: 1817.252 pm/V
- Cancellation factor: 131.250 -> 8.781

Physical checks:

- Bound states: PASS
- Orthonormality: PASS
- Transitions E1-HH1 / E1-HH2 / E2-HH1 / E2-HH2: 1.4890 / 1.5166 / 1.6020 / 1.6296 eV
- Spectrum: SPECTRAL_MATCH (peak 1518.0 nm)

Interpretation: the electron/HH residual changed through the complete Eq. 2 calculation. DIAGNOSTIC PROXY values must not be reported as paper inputs.

