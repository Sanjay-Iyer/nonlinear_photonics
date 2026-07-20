# Prioritized Replication Roadmap

This roadmap moves from documentation cleanup to scientific gap closure. It uses
`paper_replication_results/` as the organizing source of truth, and it points
back to existing artifacts for every proposed modeling task. One caveat is
important: while preparing this roadmap, a broader repo search found an older
`git/aestimo/paper/schaefer_2024/` evidence subtree that is not represented in
the clean Schaefer summary. That mismatch is treated here as an immediate
evidence-reconciliation task, not as permission to reorganize the repo.

## Priority order

| Priority | Paper | Next useful scientific result | Actionability | Why this is first |
| ---: | --- | --- | --- | --- |
| 1 | Quantum-Well-Metasurface | Channel- and term-resolved chi^(2) cancellation ledger at the peak and at 1.57 um | Actionable now | The main reproduction gap is the low coherent chi^(2); existing Eq. 2 code already has term-ledger utilities. |
| 2 | 2602.23246v1 | Extract a standalone target manifest from the existing PDF and current summary/artifact index | Actionable now | Current results are inherited from the shared ACQW stack; the first missing object is a paper-specific target manifest. |
| 3 | 2602.23246v1 | Build the standalone ACQW reproduction pipeline/report | Blocked until the target manifest exists | The pipeline needs explicit paper targets before it can be independently reproducible. |
| 4 | APL 2023 | Focused Fig. 5a band-offset sensitivity closure figure/table, without adopting a fitted baseline | Actionable now | Existing diagnostics show the barrier optimum is parameter-sensitive and most tractable with current data. |
| 5 | Schaefer 2024 | Reconcile clean layer with the existing Schaefer public-information release; then stop or request author data | Actionable as documentation/evidence reconciliation; new modeling blocked | The clean layer says no artifacts, but an older Tier-1 release exists and says further modeling is not justified without author data. |

## 1. Documentation complete

| Paper | Status | Evidence |
| --- | --- | --- |
| Quantum-Well-Metasurface | Complete for current documentation layer | `../01_quantum_well_metasurface/SUMMARY.md`, `../01_quantum_well_metasurface/ARTIFACT_INDEX.md` |
| 2602.23246v1 | Complete as a companion/shared-stack summary | `../02_enhanced_interband_nonlinearities_2602_23246/SUMMARY.md`, `../02_enhanced_interband_nonlinearities_2602_23246/ARTIFACT_INDEX.md` |
| APL 2023 | Complete as a summary of the older release | `../03_apl2023_interband_chi2_acqw/SUMMARY.md`, `../03_apl2023_interband_chi2_acqw/ARTIFACT_INDEX.md` |
| Schaefer 2024 | Clean layer complete but incomplete relative to broader repo evidence | `../04_schaefer2024_type_ii_aqw/SUMMARY.md`; broader evidence at `../../git/aestimo/paper/schaefer_2024/releases/schaefer2024_public_reproduction_final_v1/` |

## 2. Results already reproduced

| Paper | Reproduced result | Evidence |
| --- | --- | --- |
| Quantum-Well-Metasurface | Band structure/localization for the realistic graded ACQW; E11/E22 solver agreement; chi^(2) peak position; GMR resonance and angle splitting; Q-corrected field enhancement | `../../replication/qw_metasurface/REPORT.md`, phases 2-7 |
| 2602.23246v1 | Shared x = 0.55 ACQW stack, E11/E22 internal Aestimo/kdotpy agreement, near-1500 nm material chi^(2) peak position | `../02_enhanced_interband_nonlinearities_2602_23246/SUMMARY.md`; `../../replication/qw_metasurface/REPORT.md` |
| APL 2023 | Electronic-state architecture, HH2 relocation near s about 0.45, CB2 thin-well character, pathway bookkeeping, qualitative pairwise cancellation | `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/docs/APL_2023_FINAL_PUBLIC_REPRODUCTION_STATUS.md` |
| Schaefer 2024 | Clean layer says none. Broader repo evidence says a T2 BDD state calculation executed and e1-hh1 was approximately reproduced | Clean layer: `../04_schaefer2024_type_ii_aqw/SUMMARY.md`; broader release: `../../git/aestimo/paper/schaefer_2024/releases/schaefer2024_public_reproduction_final_v1/docs/acqw_reproduction/schaefer_2024/SCHAEFER_2024_FINAL_PUBLIC_REPRODUCTION_STATUS.md` |

## 3. Results partially reproduced

| Paper | Partial result | What remains |
| --- | --- | --- |
| Quantum-Well-Metasurface | chi^(2) spectral peak position and individual channel magnitudes | Full coherent chi^(2) is about 7-20x low; combined MQW+MS chi^(2) inherits the gap. |
| 2602.23246v1 | Shared ACQW electronic and chi^(2) quantities | Results are not isolated in a standalone paper-specific pipeline. |
| APL 2023 | Relative chi^(2) trends, Fig. 5a barrier behavior, Fig. 5c spectral resonances | Fig. 2a peaks remain late; Fig. 5a baseline optimum differs; Fig. 5b trend fails. |
| Schaefer 2024 | Broader release: structure reconstruction and ground-state transition approximately reproduced | Excited transitions, overlaps, centroid separations, dipole definitions, relative chi^(2), and absolute chi^(2) are not reproduced or not testable. |

## 4. Results not reproduced yet

| Paper | Not reproduced |
| --- | --- |
| Quantum-Well-Metasurface | Coherent MQW chi^(2) magnitude; final MQW+metasurface effective chi^(2) around 14 nm/V. |
| 2602.23246v1 | Standalone full-paper reproduction; coherent chi^(2) magnitude at paper scale. |
| APL 2023 | Fig. 2a total asymmetry peak positions under frozen baseline; Fig. 5a complete benchmark under frozen baseline; Fig. 5b width trend; absolute chi^(2). |
| Schaefer 2024 | Clean layer: all modeling not reproduced. Broader release: Tier 1 state reproduction not reproduced beyond limited ground-state behavior; relative/absolute chi^(2) not attempted. |

## 5. Results blocked by missing paper or author input files

| Paper | Blocked result | Missing input |
| --- | --- | --- |
| Quantum-Well-Metasurface | Resolve the about 10x coherent chi^(2) magnitude gap definitively | Authors' Nextnano input deck/version, exact material database, DFT/HSE06-corrected states/dipoles, normalized CB/HH wavefunctions, centroids, overlaps, separated electron/hole pathway terms, k-grid/density conventions, and broadening conventions. |
| 2602.23246v1 | Independent validation of the grown ACQW chi^(2) magnitude and grading effect | Raw state files, realistic interface profile, material database, exact DFT/HSE06 corrections, measured/simulated source data for chi^(2) spectra. |
| APL 2023 | Full Fig. 2a/Fig. 5b/absolute chi^(2) closure | Nextnano input files, material parameters, raw figure data, electron/hole [2,2,2] terms, S22, `<z>CB2`, `<z>HH2`, Delta z22, state energies, normalized wavefunctions, `Nz`, k-space weights, and phase conventions. |
| Schaefer 2024 | Defensible continuation beyond public-information Tier 1 | Exact T2 layer stack used for Table I, full multiband material database, alloy interpolation/bowing rules, strain/orientation convention, elastic/deformation-potential parameters, finite-difference domain/grid, signed-overlap convention, raw states, and Table I intermediate data. |

## 6. Results blocked by solver or model limitations

| Paper | Solver/model limitation |
| --- | --- |
| Quantum-Well-Metasurface | kdotpy centroids are unreliable with the approximate material bridge, so kdotpy chi^(2) is hybrid; envelope-function solvers may over-cancel electron and hole channels relative to the paper's DFT/HSE06-corrected Nextnano states. |
| 2602.23246v1 | Same ACQW solver limitation as the metasurface paper; no isolated pipeline means model provenance is shared rather than paper-specific. |
| APL 2023 | Aestimo and BDD agree on several discrepancies, so remaining failures are not likely Aestimo-only; absolute chi^(2) is not meaningful until relative pathway architecture and normalization conventions are resolved. |
| Schaefer 2024 | Aestimo adapter failed strict BDD-Aestimo alignment; kdotpy requires custom eight-band, strain, and alloy parameters not sufficiently specified; scalar BDD lacks HH/LH/SO multiband mixing and strain. |

## 7. Results that can be attempted now with the current repo

| Paper | Attempt now | Output to create |
| --- | --- | --- |
| Quantum-Well-Metasurface | Use `chi2_micro_audit.enumerate_eq2_terms`, `build_cancellation_pair_ledger`, and `group_eq2_terms_by_pathway` on the existing graded route at 1475 nm and 1570 nm | CSV/Markdown ledger plus waterfall/bar figure showing electron, hole, diagonal, off-diagonal, and residual contributions. |
| 2602.23246v1 | Extract a paper-specific target manifest from `../../2602.23246v1.pdf`, `../02_enhanced_interband_nonlinearities_2602_23246/SUMMARY.md`, and `../02_enhanced_interband_nonlinearities_2602_23246/ARTIFACT_INDEX.md` | A target-manifest Markdown/YAML draft listing paper-reported structures, E11/E22 anchors, grading, chi^(2) targets, and missing values. |
| 2602.23246v1 | After the target manifest exists, create a standalone paper-specific wrapper around existing Phase 1-4 ACQW scripts with its own config, report, and checkpoints | Blocked pipeline task: `replication/enhanced_interband_2602/` and a report that explicitly separates paper targets from metasurface inherited quantities. |
| APL 2023 | Turn existing Fig. 5a offset diagnostics into a clean expert-facing sensitivity table/plot and decision note | A focused "what current data can and cannot solve" artifact; no new fitted baseline. |
| Schaefer 2024 | Reconcile `paper_replication_results` with the existing Schaefer release, then prepare an author request rather than new simulations | Updated planning note or future documentation fix; author request based on existing `SCHAEFER_2024_TARGETED_AUTHOR_REQUEST.md`. |

## Best next concrete modeling task by paper

| Paper | Next concrete modeling task | Rationale |
| --- | --- | --- |
| Quantum-Well-Metasurface | Add a Phase 4 cancellation-decomposition script that exports per-channel and per-[m,n,l] Eq. 2 contributions for `aestimo_graded` at peak and operating wavelengths | This directly attacks the main low-coherent-chi^(2) gap and can be done with existing states and code. |
| 2602.23246v1 | First extract a target manifest; then build a standalone ACQW reproduction skeleton only after that manifest exists | The manifest is immediately actionable; the full pipeline is blocked until paper-specific targets are explicit. |
| APL 2023 | Package the Fig. 5a Qc/Qv sensitivity into a single non-adopted diagnostic result and compare against the frozen baseline | It is the mismatch most likely to yield new insight with current public data. |
| Schaefer 2024 | First reconcile the clean documentation with the older Schaefer Tier-1 release; if modeling resumes, do not go beyond author-data request until missing multiband/strain/alloy inputs arrive | Existing broader repo evidence already says further Schaefer simulations are underconstrained without author data. |
