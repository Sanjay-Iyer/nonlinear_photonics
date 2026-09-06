# Existing-data evidence inventory — Demo 26 Exhaustive Home Audit

Read-only search performed 2026-09-05. No nextnano executable or solver workflow was invoked. Paths below resolve from `C:/code/nonlinear_photonics/` unless absolute. Inventory JSON lists the actual raw file paths. A file/deck name is not proof that a calculation ran.

## Search scope and result

Searched all `demo_results`, `nextnano` (including test fixtures), `C:/nn_results`, `output`, `paper_replication_results`, `replication`, `hello_well`, `sample_1qw_barrierdope_ingaas`, and `debug_chi2_spectral_shape`. The repository-wide rg traversal encountered access-denied files under `tmp/demo26_ext_deps` (Python package cache); the scientific source/output roots were searched separately. No claim is made about arbitrary unlisted disks or folders.

`demo_results` file counts at inspection: demo_16E 19, demo_17 4, demo_17b 1, demo_17c 3, demo_17d 3, demo18 3, demo18b 2, demo18c 11, demo18d 11, demo19 17, demo20 83, demo20_license 21, demo23 5198, demo24 86, demo25 7. The only full Professional kp8 raw trees found were the seven Demo23 trees below.

## Reusable Professional dispersion data

All seven folders have 738 files. Each contains its copied input, job_done.txt, summary.log, simulation_database.txt, composition readback, 14-band dispersion, explicit k vectors, k=0 energies, spinor character, envelopes, transition and dipole/momentum matrices. All use the same 1nm graded structure; misleading input header says primary ideal abrupt but actual four ternary_linear regions establish grading.

| Raw dataset under demo_results/demo23/raw/ | Independent grid | Cutoff in pi/a | Reuse |
|---|---:|---:|---|
| grid_y_n101_k0100 | 101 | 0.10 | grid convergence |
| grid_y_n201_k0100 | 201 | 0.10 | grid convergence |
| production_y_n301_k0100 | 301 | 0.10 | baseline dispersion |
| kmax_y_n301_k0050 | 301 | 0.05 | real cutoff dataset |
| kmax_y_n301_k0075 | 301 | 0.075 | real cutoff dataset |
| kmax_y_n301_k0125 | 301 | 0.125 | real cutoff dataset, beyond previous audit |
| isotropy_yz45_n301_k0100 | 301 | 0.10 | angular direction sensitivity |

The path pattern is `<dataset>/<dataset>/bias_00000/QuantumDispersions/acqw/kp8/{dispersion,kVectors}_Gamma_to_y.dat`, with direction-specific filename for isotropy. Exact paths are in EXISTING_RAW_DATA_INVENTORY.json. 0.025 can be formed by truncation within real data but is not a separate solve. Largest actual cutoff is 0.125 pi/a; 0.20 pi/a unavailable.

Prior statement that data stop at 0.10 pi/a is superseded by this inventory. Prior results can be preserved while extending with the actual 0.125 output.

No nonzero-k envelope/spinor/matrix file was found in any tree: actual state-resolved filenames are k00000 only despite all_k_points=yes in the requested input. Finite-k M(k), wavefunction-overlap tracking and character continuity cannot be certified. Fixed energy-column continuity is only a limited diagnostic, especially near avoided crossings.

Reusable processed evidence: `demo_results/demo23/tables/tables/{tracked_dispersions_and_fits,state_tracking,k_grid_convergence,kmax_convergence}.csv`; Demo24 outputs `KGRID_SENSITIVITY.csv`, `KMAX_SENSITIVITY.csv`, `ISOTROPY_SPECTRAL_SENSITIVITY.csv`, `ENERGY_FEATURE_SENSITIVITY.csv`, `PATHWAY_AMPLITUDE_SENSITIVITY.csv`, `NODE_CANCELLATION_SENSITIVITY.csv` under `nextnano/demos/24_equation2_spectral_shape_audit/outputs/`.

## Abrupt and alternative grading actually available

`demo_results/demo19/tables/demo19_master_results.csv` contains 13 real solver-derived scalar energy/O/z records, including case00 abrupt and case04 linear1nm. `demo_results/demo19/tables/demo19_grading_cases.csv` defines all interface widths. All rows have solver_pass=True and physical_valid=False; exact recorded reason is 'Demo 11/14 physical QC did not pass'. The copied table does not identify which physical QC sub-check failed. Do not speculate that it was a particular confinement/overlap threshold.

Case00 abrupt has E1=2.937946127708eV, E2=3.047809856454eV, HH1=1.448520856461eV, HH2=1.415463602981eV, and all twelve O/z entries. It supports a self-contained scalar/parabolic abrupt spectrum diagnostic. It is not a matching abrupt kp8 dispersion dataset. Never combine its matrices with graded 23D dispersions without explicitly calling that cross-geometry diagnostic.

The table points to `C:/nn_results/19_quantum_well_interface_grading_showcase/demo19_20260814T150258Z_38f64513_ba3c80/cases/case_00/optical/parsed/chi2_focused.csv`; that original licensed tree is absent. C:/nn_results contains only Demo17 and17e syntax/preflight trees with run_solver_enabled=false. Demo19 raw scalar envelopes cannot be independently re-integrated from its master table alone.

`demo_results/demo20/data/case_00_chi2_spectrum.csv` through case12 contain real/imag/magnitude raw and scaled scalar spectra but the saved window starts1400nm; full 400–1850 comparison requires cheap Eq2 recalculation from the legitimate case matrices. Demo20 has no new eigenstates. `demo_results/demo20_license/tables/demo20_master_results.csv` explicitly reports states_provenance=master_table:demo19_master_results.csv and analysis_source=master_table. Its license-sounding folder name does not establish an independent solve.

## Other potentially confusing datasets

Demo21 is derivation/postprocessing of Demo20, not a new raw solve. Demo22 `00_setup_and_provenance/RUN_MANIFEST.json` contains abrupt/k integration input plans but run_solver=false; requested kmax1.2/nm is not available physical data. Demo25 contains preparatory material, not finite-k wavefunction output.

`nextnano/tests/fixtures/nextnano_pp_3_0_0/demo11_acqw_paper/` contains genuine abrupt scalar Free-edition nextnano energies/envelopes/O/dipoles. `demo06_doped_scf/` contains a genuine quantum_poisson example with potential, occupations, iteration trace. PROVENANCE.md explicitly says coarse1nm mesh, <=100points,300K,Gamma/HH only, adequate for plumbing and not converged physics. These cannot establish matching Professional abrupt or self-consistent reproduction. They can be reused for parser/integral tests with their limitations.

`sample_1qw_barrierdope_ingaas/` has Aestimo states, potentials and wavefunctions for a different doped InGaAs well; `hello_well`, `output`, and `replication/qw_metasurface/phase2_aestimo`/`phase3_kdotpy` have other-code outputs. Do not substitute these for nextnano Professional or the exact baseline geometry. Paper-replication reports and debug spectra are already postprocessed/diagnostic data, not additional Professional eigenstates.

## Raw state identity and energy-only inventory

RAW_K0_STATE_CHARACTER.csv extracts all14 actual k0 states. e1 pair11+12 is96.2603697%CB; e2 pair13+14 is93.0981035%CB. hh1 pair5+6 is100%HH. The tracked hh2 pair3+4 is0%HH,97.5756719%LH,1.9573136%CB,0.4670144%SO. Calling it merely 'some LH character' understates the raw result. Pure-HH pair1+2 exists at1.397694253080eV; it is a physically motivated alternative HH assignment to inspect, not a free permutation fit. A susceptibility using the alternate state must reconstruct every matrix involving that state consistently.

Pair7+8 at2.339066931019eV and pair9+10 at2.339098894737eV are only56.3092473% and56.2919366%CB, respectively, with substantial LH/SO components. They are not established higher electron bound states. Raw numbering is energy order and not a physical certification.

EXISTING_HIGHER_STATE_K0_TRANSITIONS.csv computes12 energy-only pair transitions from the four CB-containing pairs and three valence pairs. Largest k0 gap is1.693454198935eV (pair13+14 to1+2;732.14/1464.28nm), not2.296eV. This does not exclude finite-k resonances or interference features. No higher-state chi was fabricated.

Important baseline provenance: `tracked_dispersions_and_fits.csv` distinguishes raw_kp8_energy_eV from demo21_aligned_energy_eV. At k0 raw e1=2.9525116792099eV becomes2.9411581380879994eV, and raw e2=3.09114845201545 becomes3.0610228581580006. Production resonance maps must use the anchored energies; raw higher-state maps must remain labeled unanchored. These are state-specific offsets, not one global energy reference shift.

## Electrostatics evidence

Actual production deck includes `no_density=yes`, `k_integration_disabled{}`, and `run{quantum{}}`; there is no quantum_poisson loop. Donor/acceptor/fixed charge values are zero, but `bias_00000/total_charges.txt` reports holes9.376333e15e/cm2, electrons-1.357081e-37e/cm2. This is not evidence of a matched self-consistent carrier solution. Occupations should not be inferred solely from fixed charge. Paper-equivalent Poisson requires specified electrostatic/occupation conditions and a converged matching run. The existing coarse different-geometry fixture does not resolve it.

## Home/Pro boundary and recommendation

Home-completable: reuse all seven dispersions, all thirteen scalar matrix/energy cases as qualified diagnostics, raw k0 state character, consistently reconstructed k0 branch matrices, scalar versus kp8 provenance comparison, and existing Demo24 sensitivities. Distinguish mode23D energy anchoring from raw solver energies explicitly.

New eigenstates required, if friend's files do not already supply them: matched abrupt kp8 grid; new grading profile/temperature/material parameters; k up to0.20pi/a; finite-k spinors/matrices and certified state tracking; matching converged Poisson conditions. Existing abrupt scalar and coarse Poisson outputs exist but are insufficient to claim those exact alternatives already solved.

Ask friend for the exact input deck plus spectrum-generation/postprocessing script and the accompanying raw output/run version/database identifiers. This settles geometry, state pairing, energy anchoring, matrices and BZ/occupation conventions together before an expensive solve.
