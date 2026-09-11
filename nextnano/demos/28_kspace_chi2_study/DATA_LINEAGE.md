# Data lineage: source → transformation → artifact → consumer

Paths are relative to Demo 28. `outputs/28A_baseline/` is abbreviated **A** below. Each study preserves its actual configuration and raw-file SHA256 manifest; no old demo folder is needed to evaluate Eq2.

## 1. Raw nextnano (not NumPy checkpoints)

The reproducible inputs are `nextnano/inputs/kp8_dispersion.in` and `singleband_case04_graded.in`. Original archived decks and `simulation_info.txt` are also retained with raw results. These describe historical runs, not runs performed on this laptop.

`nextnano/raw_results/kp8/` contains the raw 14-state dispersion and k-vector files, k=0 energy spectrum, composition and envelopes. `nextnano/raw_results/singleband_case04_graded/` contains the raw Gamma and HH single-band spectra/envelopes. Exact nested filenames and hashes are enumerated in `A/raw_manifest.json`. The parser requires a unique matching file, rather than silently picking an arbitrary result.

Additional datasets are separate: `nextnano/raw_extended/` (301 points through 0.125 pi/a), `nextnano/raw_results/grid_n101/`, `grid_n201/`. These are copied original solver files, not fitted/extrapolated curves. The raw archives provide only k=0 wavefunction/composition coverage, even though dispersion covers all k.

## 2. Parsed quantities

| Source → parser | Saved output under A/parsed_data | Shape / units | Next consumer |
|---|---|---|---|
| `kp8/.../dispersion_Gamma_to_y.dat` + associated `kVectors_*.dat` → `read_dispersion` | `kp8_energies.csv` | table (nk,1+14); nm^-1 and eV | `input_builder.build_inputs` |
| k=0 `kp8/energy_spectrum_k00000.dat` + composition → pair classification | `k0_spinor_composition.npy` | (14,8), normalized component fractions | historical pair assignment |
| Selected raw doublets → pair means | `selected_pair_energies.csv` | table (nk,5), unaligned eV | dispersion-shift alignment |
| Single-band `Gamma/energy_spectrum_k00000.dat`, `HH/energy_spectrum_k00000.dat` | `singleband_k0_energies.csv` | 2 rows, state/electron/valence energies eV | anchors |
| Single-band `envelopes_k00000.dat` → parse and unit-normalize | `normalized_singleband_envelopes.csv` | (nz,5), z[nm], four envelopes[nm^-1/2] | spatial integrals |

Normalization is a processing step; the saved envelopes are explicitly labeled parsed-and-normalized rather than byte-identical raw output. Baseline nk=301. Raw state IDs are one-based; internal arrays are zero-based.

## 3. Derived Equation 2 inputs, saved before evaluation

| Quantity | Source/transformation | Artifact under A/chi2_inputs | In-memory shape / units | Eq2 consumer |
|---|---|---|---|---|
| k_parallel | explicit raw vector convention → magnitude | `k_per_nm.csv` column1 | (nk,), nm^-1 | `inputs['k_per_nm']` |
| Ee_n(k) | single-band anchor + raw paired Ee(k)-Ee(0) | `electron_energies.csv` | (2,nk), eV | `electron_eV` |
| Ev_m(k) | single-band anchor + raw paired Ev(k)-Ev(0) | `hole_energies.csv` | (2,nk), eV, electron reference | `valence_eV` |
| T_nm | Ee[:,None,:]-Ev[None,:,:] | `transition_energies.csv` | (2,2,nk), eV; table columns11,12,21,22 | one/two-transition arrays |
| O_nm | integral e_n* h_m dz | `overlap_eh.npy` | (2,2,nk), dimensionless | `o` in `pathway_definitions` |
| ze_nell | integral e_n* z e_ell dz | `z_e.npy` | (2,2,nk), nm | C numerator |
| zh_mell | integral h_m* z h_ell dz | `z_h.npy` | (2,2,nk), nm | V numerator |
| Gamma | configured5meV x1e-3 | `metadata.json` settings/gamma_eV | scalar eV | `g=1j*sign*gamma_eV` |
| k weights | selected native nodes → radial trapezoid | `k_per_nm.csv` column2 | (nk,), nm^-2 | `value @ weights` |

CSV files display one k point per row; energy arrays used by the engine have state on the first axis. O's axes are electron, valence, k; ze electron, electron, k; zh valence, valence, k. Constant 2x2 matrices are broadcast to (2,2,nk), explicitly indicating M(k)=M(0). No finite-k matrix data is invented.

Anchors [e1,e2,h1,h2] are [2.941158138088,3.061022858158,1.447805442384,1.412791422186] eV. Solver doublets are [[11,12],[13,14],[5,6],[3,4]]. h2 is LH-dominated in the 8-band source, a documented mismatch rather than an implicit HH claim.

## 4. Configured constants and intermediate algebra

| Quantity | Source | Storage / computation |
|---|---|---|
| Fundamental lambda | `config/baseline.json`,400–1850nm step1 | output spectrum wavelength column |
| hbar omega | hc/lambda, hc=1239.841984 eV nm | spectrum photon-energy column; `photon_energy` |
| Nz | 1/(period_nm x1e-9), period30nm | settings and `prefactor` |
| r_e,hh | literature7.51angstrom=.751nm | settings; `PAPER_AUDIT.md`; not raw nextnano |
| Spin degeneracy | configured2 | settings, radial weights |
| Prefactor | explicit constants/unit conversions | study metadata; `equation2.prefactor` |
| Numerators | complete phase-invariant products | `outputs/28G_pathways/` pathway tables/NPZ; `pathway_definitions` |
| Denominators | T-2hw+iGamma, T-hw+iGamma | engine `d2`, `d1`; transitions and settings suffice to reconstruct; resonance arrays in28G |

The per-k quantity saved in A's NPZ is an **unweighted integrand**, not a susceptibility already in pm/V. It becomes the integrated susceptibility only after multiplying weights and prefactor. The 28B shell table includes both operations, so each shell is in pm/V.

## 5. Final results

`A/chi2_results/chi2_spectrum.csv` contains wavelength, photon energy, Re, Im, abs(Re), abs(chi). Complex values are also in `chi2_complex.npy`. `pathways.npz` has (16,nlambda) values and labels; summing its first axis reproduces chi. `chi2_k_lambda_integrand.npz` has integrand(nlambda,nk), weights(nk), wavelength(nlambda). Baseline nlambda=1451.

`chi2/studies.py` saves these artifacts and `chi2/plotting.py` reads numerical arrays for plots. It does not create an imaginary component during plotting. The complex arithmetic already occurred in Equation 2.

28B repeats derived inputs/results per cutoff under `cases/`. Each case records requested and actual endpoints and source indices. `cumulative_and_shells.csv` stores exact adjacent-trapezoid shell and cumulative values at540/760/1080/1520/1550nm. 28H records fixed-endpoint sampling comparisons. 28C records nested cutoffs on one coarser extended grid and the separate same-endpoint comparison in28H.

## 6. Provenance boundaries

The copies in `validation/` are historical regression/paper references, never electronic-structure inputs. Their use is explicit in 28A and28J. The source audit names older code only to explain provenance. Production functions import only this package and installed scientific Python dependencies. The isolated dependency audit blocks old-demo access while rerunning A/B.

Numerical metadata records source manifests and the current Eq2 SHA256, since a git commit alone would miss uncommitted work. A later edit changes that hash; rerun a study to regenerate its output metadata rather than claiming an old plot came from new code.
