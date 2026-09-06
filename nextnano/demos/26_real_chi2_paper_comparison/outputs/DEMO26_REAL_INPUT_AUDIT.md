# Demo 26_real input audit

Demo 26_real uses the shortest reliable route: the existing Demo 23D complex-spectrum CSV. No complex susceptibility is reconstructed because the real and imaginary parts are already preserved and their quadrature exactly reproduces the stored magnitude.

| Data item | Available? | Path | How it is used | Limitation |
|---|---|---|---|---|
| Complex total chi spectrum | YES | `C:\code\nonlinear_photonics\demo_results\demo24\demo23_reanalysis\spectra\23D_chi2.csv` | Primary input; reads Re, Im, and magnitude on the 400-1850 nm, 1-nm grid | Analysis product generated from copied Professional data, not a native nextnano chi export |
| Complex 16-pathway spectra | YES | `C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\PATHWAY_SPECTRA.csv` | Audit trail confirming the 16 complex contributions exist | Not needed for the shortest-route observable test |
| Complex k-resolved integrands | PARTIAL | Demo 23 tables contain 1550-nm k-integrand summaries; the full in-memory array was not exported as a wavelength-by-k CSV | Confirms integration diagnostics; not used here | A full stored 2D integrand is unavailable, but is unnecessary because total complex chi is present |
| Tracked full kp8 E(k), e1/e2/hh1/hh2 | YES | `C:\code\nonlinear_photonics\demo_results\demo23\raw\production_y_n301_k0100\production_y_n301_k0100\bias_00000\QuantumDispersions\acqw\kp8\dispersion_Gamma_to_y.dat` plus Demo 23 state-tracking tables | Source used by Demo 23D to produce the preserved complex spectrum | Raw nextnano output does not itself contain chi |
| M(0), Equation-2 inputs | YES | `C:\code\nonlinear_photonics\demo_results\demo19\tables\demo19_master_results.csv` and `C:\code\nonlinear_photonics\nextnano\demos\23_k_resolved_dispersion_validation\demo23_config.yaml` | Existing Demo 23D numerator and physical configuration | M(k)=M(0) approximation; finite-k matrices were not exported |
| Finite-k O(k), z_e(k), z_hh(k) | NO | `C:\code\nonlinear_photonics\nextnano\demos\24_equation2_spectral_shape_audit\outputs\FINITE_K_DATA_INVENTORY.md` | Not used | Would require a new Professional export; deliberately not fabricated |
| Exact paper digitization | YES | `C:\code\nonlinear_photonics\nextnano\demos\23_k_resolved_dispersion_validation\paper_figure2d_digitized_simulation.csv` | Unchanged 45-point paper comparison | Eye digitization, not raw/tabulated author data |

Input hashes:

- Demo 23D spectrum SHA-256: `cd2afab14c96b874314c011535d2a116799ca3416be54ce764695aa70605d469`
- Paper digitization SHA-256: `87f4b624ff576eca7ed1293674f95ceba8846ae271b95989313083ecc3cd99cb`

The available files are sufficient to answer the Re-vs-magnitude question. No nextnano calculation is required or performed.
