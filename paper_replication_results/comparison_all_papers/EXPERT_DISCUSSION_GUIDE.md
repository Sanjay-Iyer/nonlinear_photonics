# Expert Discussion Guide

## One-minute cross-paper story

The repo is strongest on the GaAs/AlGaAs metasurface paper's electromagnetic and transition-energy story, but not on the coherent material chi^(2) magnitude. The 2602.23246 paper is currently a companion material anchor rather than a standalone replication. The APL 2023 paper has a solid electronic-state reproduction but only partial relative chi^(2) agreement, with absolute chi^(2) intentionally frozen. Schaefer 2024 is a cautionary type-II benchmark: an older Tier-1 attempt exists, but it closed as not testable/not reproduced from public information. Across all four papers, the recurring limitation is missing author-level intermediate data: raw states, material databases, band offsets, centroids, overlaps, pathway terms, and normalization conventions.

## Cross-paper status table

| Paper | Best thing to say | Main caveat |
| --- | --- | --- |
| Quantum-Well-Metasurface | "We reproduce the metasurface optics and transition-energy placement well." | "We do not reproduce coherent MQW chi^(2) magnitude because electron and hole pathways nearly cancel." |
| 2602.23246v1 | "We use it as the structural/material anchor for the shared x = 0.55 ACQW stack." | "It still needs a standalone target manifest and pipeline." |
| APL 2023 | "The electronic-state architecture is reproduced with Aestimo and BDD." | "Relative chi^(2) is only partial, and absolute chi^(2) is frozen." |
| Schaefer 2024 | "Type-II enhancement is scientifically interesting, but local reproduction is not ready." | "Older Tier-1 evidence says further modeling is blocked without author data." |

## Verbal answer to "what actually worked?"

- Electronic-state calculations worked best when the material system was well specified and cross-checkable with Aestimo and BDD/kdotpy.
- The metasurface electromagnetic model worked well enough to recover resonance placement, angular behavior, and corrected enhancement factors.
- The BNN/deep ensemble worked for robust quantities such as E22, but not for fragile cancellation-dominated chi^(2).
- APL pathway bookkeeping worked internally, even when figure-level agreement remained partial.
- Schaefer scalar state calculations could be run, but public information was not enough for full reproduction.

## Verbal answer to "what failed?"

- The coherent material chi^(2) magnitude in the x = 0.55 GaAs/AlGaAs stack remains low because electron and heavy-hole channels cancel.
- APL Fig. 2a peaks are late, Fig. 5a baseline optimum differs, Fig. 5b is not reproduced, and absolute chi^(2) is not audited.
- 2602.23246 is not standalone yet; its current evidence is inherited from the metasurface ACQW pipeline.
- Schaefer type-II excited-state quantities, overlaps, centroid separations, and chi^(2) are not reproduced or not testable from public information.

## How to frame uncertainty without sounding vague

Say: "The uncertainty is not just numerical noise; it is about missing microscopic intermediate quantities." Then name them: state wavefunctions, centroids, overlaps, separated electron/hole pathway terms, material database, band offsets, strain conventions, k-space weights, and absolute normalization. For the metasurface paper, emphasize that the next repo-internal test is a cancellation ledger; for APL, a Fig. 5a band-offset sensitivity closure; for 2602, a target manifest; for Schaefer, author-data reconciliation.

## Likely expert questions across all papers

| Question | Short answer |
| --- | --- |
| Are you comparing coherent chi^(2) or channel magnitudes? | Coherent chi^(2) is the physical observable; channel magnitudes are diagnostics. |
| Is the metasurface result independent of the material chi^(2) problem? | Mostly yes: resonance placement and field enhancement are reproduced, but the final effective chi^(2) inherits the low material value. |
| Why trust Aestimo? | Where possible, Aestimo is checked against BDD or kdotpy. Some failures persist across solvers, so they are not simply Aestimo artifacts. |
| Why not fit band offsets until the figures match? | That would become underconstrained fitting. Diagnostic variants are allowed, but baseline adoption needs author evidence. |
| What one file would help most? | The authors' solver input deck plus raw state/intermediate table for each benchmark. |

## Meeting script by paper

### Quantum-Well-Metasurface

"For Fathi et al., the metasurface half is a strong replication: GMR B, angular splitting, beta symmetry, and Q-corrected enhancement all line up. The ACQW transition energies and peak placement also look reasonable. The problem is coherent chi^(2): electron and heavy-hole pathways are individually large but cancel in our envelope-function calculation. The next thing I want to show is a term-resolved cancellation figure at the peak and operating wavelength."

### 2602.23246v1

"For the 2602 paper, we currently use it as a materials anchor for the same x = 0.55 ACQW stack. The shared Aestimo/kdotpy results support the transition-energy scale and peak placement. But I would not call it standalone yet. The next action is a target manifest from the PDF, then a paper-specific wrapper around the existing ACQW phases."

### APL 2023

"For APL 2023, the electronic states are the strongest piece: HH2 relocation and CB2 localization are reproduced by Aestimo and BDD. The relative chi^(2) curves are only partial: Fig. 2a peaks are late, Fig. 5a is band-offset sensitive, and Fig. 5b remains unresolved. Absolute chi^(2) is intentionally frozen. The most productive current-data discussion is Fig. 5a sensitivity, not a claim of full reproduction."

### Schaefer 2024

"For Schaefer, the clean summary needs to be reconciled with an older Tier-1 release. That release says a BDD state calculation ran and got limited ground-state agreement, but excited transitions, overlaps, centroid separations, and chi^(2) did not reproduce. Because type-II AQWs depend strongly on offsets, strain, and multiband parameters, I would not do more sweeps without author data. This is a request-author-input case."

## Key terms glossary

| Term | Definition |
| --- | --- |
| E11 | Interband transition energy from HH1 to CB1, or analogous first electron-hole transition. |
| E22 | Interband transition energy from HH2 to CB2; often tied to the resonant chi^(2) peak. |
| HH1 / HH2 | First and second heavy-hole confined states. |
| CB1 / CB2 | First and second conduction-band confined states. |
| Oscillator strength | A measure of optical transition strength from wavefunction overlap and dipole matrix elements. |
| Wavefunction localization | Where a confined state sits spatially: wide well, narrow well, barrier, electron well, or hole well. |
| Centroid asymmetry | Difference between electron and hole average positions along the growth axis; key for broken inversion symmetry. |
| chi^(2) | Second-order nonlinear susceptibility; the coefficient driving SHG, optical rectification, and related second-order effects. |
| Electron-hole cancellation | Destructive interference between electron-channel and hole-channel susceptibility contributions. |
| BDD | BenDaniel-Duke scalar finite-difference envelope solver; useful independent check. |
| Aestimo | 1D quantum-well Schrodinger-Poisson/envelope solver used for states and matrix elements. |
| kdotpy | Multiband k dot p solver; useful for transition-energy and valence-mixing checks when material inputs are reliable. |
| GRCWA | Rigorous coupled-wave analysis for periodic optical structures. |
| GMR | Guided-mode resonance; a leaky resonance used for field enhancement. |
| Q factor | Resonance wavelength divided by linewidth; high Q means narrow resonance. |
| Modal overlap | Spatial overlap of optical field components and nonlinear material volume. |
| Type-I AQW | Electron and hole tend to be confined in the same material region. |
| Type-II AQW | Electron and hole tend to be spatially separated across different material regions. |
| Band-offset sensitivity | The tendency for state energies, localization, and chi^(2) to change strongly with conduction/valence band offset assumptions. |

## Files to open during discussion

| Need | File |
| --- | --- |
| Per-paper speaking briefs | `../01_quantum_well_metasurface/DISCUSSION_BRIEF.md`, `../02_enhanced_interband_nonlinearities_2602_23246/DISCUSSION_BRIEF.md`, `../03_apl2023_interband_chi2_acqw/DISCUSSION_BRIEF.md`, `../04_schaefer2024_type_ii_aqw/DISCUSSION_BRIEF.md` |
| Roadmap | `PRIORITIZED_REPLICATION_ROADMAP.md` |
| Missing inputs | `MISSING_INPUTS_AND_AUTHOR_REQUESTS.md` |
| Next modeling tasks | `NEXT_MODELING_TASKS.md` |
| Compact status | `REPLICATION_STATUS_TABLE.md` |
