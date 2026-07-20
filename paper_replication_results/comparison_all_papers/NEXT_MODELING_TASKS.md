# Next Modeling Tasks

This file turns the roadmap into implementation-ready tasks. Each task is labeled
as `actionable now` or `blocked`, and each is tied to existing repo evidence.

## Task 1 - Quantum-Well-Metasurface chi^(2) cancellation decomposition

| Field | Plan |
| --- | --- |
| Status | Actionable now |
| Scientific question | Where exactly does the coherent Eq. 2 chi^(2) cancellation occur: electron versus hole channel, diagonal versus off-diagonal terms, or specific [m,n,l] pathways? |
| Existing evidence | `../../replication/qw_metasurface/phase4_chi2/DISCREPANCY.md`; `../../replication/qw_metasurface/phase4_chi2/compute_chi2_spectrum.py`; `../../git/aestimo/paper/chi2_micro_audit.py` |
| Inputs | Phase 2 graded Aestimo states, current x = 0.55 config, current Eq. 2 implementation, pump wavelengths at the coherent peak and 1.57 um. |
| Proposed output | `replication/qw_metasurface/phase4_chi2/results/chi2_cancellation_ledger.csv`, `chi2_cancellation_summary.md`, and a waterfall/bar figure. |
| Success criterion | A table and figure that show electron terms, heavy-hole terms, diagonal pairs, off-diagonal residuals, and the final coherent residual without changing physical parameters. |
| Stop condition | Stop if the existing term ledger cannot reconstruct the saved coherent value within a small numerical tolerance. |

### Implementation sketch

1. Add a small script near Phase 4, for example
   `replication/qw_metasurface/phase4_chi2/build_cancellation_ledger.py`.
2. Load `paper_params.yaml` and solve or load the graded Phase 2 state.
3. Use `chi2_micro_audit.enumerate_eq2_terms` at two photon energies:
   the Aestimo-graded peak wavelength and 1570 nm.
4. Export:
   - full term ledger with channel, m, n, l, diagonal/off-diagonal flag,
     complex contribution, magnitude, phase;
   - paired diagonal electron/hole residuals from `build_cancellation_pair_ledger`;
   - grouped pathway reconstruction from `group_eq2_terms_by_pathway`;
   - summary rows comparing electron sum, hole sum, off-diagonal sum, coherent sum.
5. Plot a waterfall or diverging bar chart so an expert can see cancellation
   without reading complex-number tables.

## Task 2A - 2602.23246v1 target-manifest extraction

| Field | Plan |
| --- | --- |
| Status | Actionable now |
| Scientific question | What exact paper-reported targets must a standalone 2602.23246 reproduction compare against? |
| Existing evidence | `../../2602.23246v1.pdf`; `../02_enhanced_interband_nonlinearities_2602_23246/SUMMARY.md`; `../02_enhanced_interband_nonlinearities_2602_23246/ARTIFACT_INDEX.md`; `../../replication/qw_metasurface/config/paper_params.yaml` |
| Inputs | Local PDF, existing clean summary/artifact index, shared metasurface parameter file, and any already-documented Ref38 anchors. |
| Proposed output | A paper-specific target manifest draft, for example `replication/enhanced_interband_2602/config/target_manifest_2602.md` or `.yaml`, listing structures, E11/E22 anchors, interface-grading statements, chi^(2) targets, and explicit `not found` fields. |
| Success criterion | The manifest cleanly separates paper-reported targets from values inherited from the shared ACQW stack and marks missing targets as unknown/not found. |
| Stop condition | Stop before creating a full pipeline if the manifest cannot identify enough paper-specific targets to make the run independently meaningful. |

## Task 2B - 2602.23246v1 standalone ACQW pipeline

| Field | Plan |
| --- | --- |
| Status | Blocked until Task 2A target manifest exists |
| Scientific question | Can the 2602.23246 material paper be reproduced and discussed independently of the metasurface replication? |
| Existing evidence | Task 2A manifest; `../../replication/qw_metasurface/phase2_aestimo/`; `../../replication/qw_metasurface/phase4_chi2/`; `../../git/aestimo/paper/reference_data/acqw_solver_consensus_v1/` |
| Inputs | Same 18.2/7.1/1.8/2.9 nm, x = 0.55 ACQW stack; existing Aestimo/kdotpy/chi^(2) functions; paper target values from Task 2A. |
| Proposed output | A standalone `replication/enhanced_interband_2602/` pipeline with `config/paper_params_2602.yaml`, phase scripts or wrappers, checkpoints, and `REPORT.md`. |
| Success criterion | Running the standalone pipeline produces E11/E22, localization, Delta z, chi^(2) peak position, channel/coherent magnitude table, and explicit paper-vs-repo comparison without referring to metasurface phases as the primary provenance. |
| Stop condition | Stop before claiming independent chi^(2) magnitude reproduction unless author state/intermediate data are available. |

### Scripts/configs to create after Task 2A

| File | Purpose |
| --- | --- |
| `replication/enhanced_interband_2602/config/paper_params_2602.yaml` | Paper-specific target manifest and physical parameters. |
| `replication/enhanced_interband_2602/phase1_structure/build_structure.py` | Wrapper or copy adapted from the metasurface structure phase. |
| `replication/enhanced_interband_2602/phase2_aestimo/run_states.py` | Paper-specific Aestimo state run and localization table. |
| `replication/enhanced_interband_2602/phase3_kdotpy/run_kdotpy.py` | Optional energy cross-check using the existing validated bridge. |
| `replication/enhanced_interband_2602/phase4_chi2/compute_chi2_spectrum.py` | Paper-specific chi^(2) spectrum and cancellation diagnostics. |
| `replication/enhanced_interband_2602/REPORT.md` | Standalone reproduction report. |

### Currently inherited from the shared ACQW stack

- The x = 0.55 barrier composition.
- The 18.2/7.1/1.8/2.9 nm stack and 16-period context.
- Aestimo and kdotpy E11/E22 values.
- Graded/abrupt localization results.
- chi^(2) peak-position reproduction and coherent-magnitude failure.
- BNN/deep-ensemble design-space context.

## Task 3 - APL 2023 Fig. 5a sensitivity closure

| Field | Plan |
| --- | --- |
| Status | Actionable now |
| Scientific question | Is the Fig. 5a barrier-optimum mismatch mostly a material band-offset sensitivity, and how far can current public data support that claim? |
| Existing evidence | `../03_apl2023_interband_chi2_acqw/SUMMARY.md`; `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/docs/APL_2023_RELATIVE_CHI2_ATTRIBUTION.md`; diagnostic tables in `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/tables/` |
| Inputs | Existing frozen baseline and Qc/Qv diagnostic tables. |
| Proposed output | One expert-facing sensitivity note/table/plot that compares frozen baseline, Qc=0.625/Qv=0.375, Qc=0.60/Qv=0.40, and BDD baseline if available. |
| Success criterion | Clearly show that Fig. 5a is the most current-data-solvable mismatch, while stating that no offset variant is adopted as baseline without author evidence. |
| Stop condition | Do not tune additional parameters to force agreement. |

### Exact remaining APL mismatches

| Mismatch | Current status | Most likely path |
| --- | --- | --- |
| Fig. 2a peak positions | Model peaks are late by about +0.04 to +0.07 in asymmetry s | Likely requires author state/intermediate data; current diagnostics can attribute but not solve. |
| Fig. 5a optimum | Frozen baseline optimum is 3.0 nm versus paper about 1-1.25 nm; Qc=0.60/Qv=0.40 diagnostic moves toward 1.25 nm but is not adopted | Most solvable with current data as a sensitivity explanation, not as a final reproduction. |
| Fig. 5b width trend | Not reproduced under either printed/prose interpretation; paper figure marked suspect | Likely requires raw author figure data and plotted variable definition. |
| Absolute chi^(2) | Frozen/not audited | Requires relative architecture closure plus `Nz`, k weights, normalization, and raw intermediate quantities. |

## Task 4 - Schaefer 2024 evidence reconciliation and author-data gate

| Field | Plan |
| --- | --- |
| Status | Actionable for evidence reconciliation; new modeling blocked |
| Scientific question | What Schaefer work already exists in the repo, and is any new modeling justified? |
| Existing evidence | Clean layer: `../04_schaefer2024_type_ii_aqw/SUMMARY.md`; broader release: `../../git/aestimo/paper/schaefer_2024/releases/schaefer2024_public_reproduction_final_v1/docs/acqw_reproduction/schaefer_2024/SCHAEFER_2024_FINAL_PUBLIC_REPRODUCTION_STATUS.md` |
| Inputs | Existing Schaefer release docs, source manifest, Table I state results, BDD/Aestimo/kdotpy gate reports. |
| Proposed output | A correction note or future update to the clean Schaefer summary saying older Tier-1 artifacts exist and were closed as not testable/not reproduced from public information. |
| Success criterion | The planning layer no longer suggests redundant first-pass modeling when a prior Tier-1 attempt already exists. |
| Stop condition | Do not start Schaefer chi^(2) or new parameter sweeps without new author data. |

### Minimal checklist before any future Schaefer code

1. Confirm exact T2 layer sequence and widths for every Table I target.
2. Confirm InP, Al0.38Ga0.10In0.52As, and Al0.48In0.52As band edges, electron
   mass, HH/LH masses, Kane potential, lattice constants, and temperature.
3. Confirm alloy interpolation and bowing rules for AlGaInAs and AlInAs.
4. Decide whether strain is included; if yes, obtain orientation, substrate,
   elastic constants, deformation potentials, and strain-shift convention.
5. Decide model tier:
   - BDD is enough for a scalar smoke test and state/intermediate table.
   - Aestimo requires repaired common-case alignment and custom material records.
   - kdotpy/8-band is not required for first smoke test, but is required if the
     target depends on multiband valence mixing or strain.
6. Confirm signed-overlap phase convention.
7. Stop before relative or absolute chi^(2) unless the state/intermediate table
   is reproduced or author data explains the mismatch.
