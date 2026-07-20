# Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells

## Paper identity

- Source PDF: `../../2602.23246v1.pdf`
- Paper: Ramesh et al., arXiv:2602.23246v1 (2026)
- Title: "Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells"
- Main repo evidence: `../../replication/qw_metasurface/REPORT.md`
- Shared parameter source: `../../replication/qw_metasurface/config/paper_params.yaml`
- Older solver consensus: `../../git/aestimo/paper/reference_data/acqw_solver_consensus_v1/`

## What the original paper studied

This paper reports enhanced interband second-order nonlinearities in coupled
GaAs/AlGaAs quantum wells. In the local repo, it is treated as the main
documentary anchor for the ACQW material stack used in the metasurface paper:
the same 16-period structure, the Al fraction, transition-energy anchors, and
graded-interface chi^(2) context.

## Quantum-well structure and key parameters

| Item | Paper/repo value |
| --- | --- |
| Material system | GaAs / Al0.55Ga0.45As |
| Reported/used stack | AlGaAs 18.2 nm / GaAs 7.1 nm / AlGaAs 1.8 nm / GaAs 2.9 nm |
| Number of periods | 16 |
| Asymmetry | 0.42 from the 7.1 and 2.9 nm wells |
| Interface grading | Repo uses a 1 nm graded-interface variant because the companion materials evidence describes roughly linear interface gradients |
| Key reported anchors used by repo | E11 about 1.49 eV, E22 about 1.62 eV, graded-interface chi^(2) around the 1.2-1.36 nm/V class |

## Physical quantities tracked

The repo tracks this paper mainly through the same electronic-structure and
chi^(2) quantities used in the metasurface replication:

| Quantity | Status in repo |
| --- | --- |
| E11 | Reproduced close to the paper anchor with Aestimo and kdotpy context |
| E22 | Aestimo/kdotpy agree internally; value is above a literal 1.58 eV operating target but consistent with a near-1500 nm material resonance |
| Band edges and localization | Tested in abrupt and graded ACQW variants |
| Wavefunction localization | Graded structure reproduces the paper-style localization claims used downstream |
| Delta z(HH2,CB2) | Evaluated; large in the graded variant |
| Interband overlaps and dipoles | Evaluated as inputs to Eq. (2)/(3)-style chi^(2) |
| chi^(2) spectral peak position | Reproduced near the expected material-resonance region |
| chi^(2) magnitude | Full coherent value not reproduced; individual channel magnitude is close to paper scale |

## Models used in the repo

| Model | Contribution |
| --- | --- |
| Aestimo | Main ACQW band structure, wavefunction, centroid, and chi^(2) route |
| kdotpy | 8-band k dot p energy cross-check for the same x = 0.55 stack |
| BDD | Independent scalar solver in the older consensus snapshot |
| Deep ensemble surrogate | Trained over geometric/material variations that include this nominal stack |

## Numerical results achieved in the repo

| Quantity | Paper-reported or referenced value | Repo result | Agreement |
| --- | ---: | ---: | --- |
| E11 | about 1.49 eV | Aestimo 1.496 eV ideal; 1.499 eV graded; kdotpy 1.507 eV | Good |
| E22 | about 1.62 eV in the paper context | Aestimo 1.657 eV ideal; 1.674 eV graded; kdotpy 1.669 eV | Reasonable but high by tens of meV |
| chi^(2) peak pump wavelength | around 1500-1520 nm class | Aestimo graded about 1475 nm; kdotpy hybrid about 1438 nm | Peak position broadly reproduced |
| chi^(2) film/material magnitude | repo report cites paper anchors around 1.2-3 nm/V depending convention | Full coherent Aestimo graded peak about 0.167 nm/V; electron-channel diagnostic about 2.34 nm/V | Coherent sum not reproduced; channel scale close |
| Interface grading effect | Paper context says realistic grading affects chi^(2) | Repo finds grading changes localization and increases Delta z in this envelope model | Qualitatively informative; not a complete match |

## What matched

- The repo used the paper as the basis for `x = 0.55` and the exact 16-period
  18.2/7.1/1.8/2.9 nm structure.
- Aestimo and kdotpy independently agree on E11/E22 to about 12 meV for the
  nominal x = 0.55 structure.
- The material chi^(2) spectral peak lands in the near-1500 nm pump region.
- Individual electron-channel chi^(2) magnitude is in the same nm/V scale as
  the paper's reported simulated magnitude.

## What did not match

- The full coherent chi^(2) is much smaller than the paper-scale magnitude
  because the local envelope-function states produce strong electron-hole
  cancellation.
- The repo does not contain a standalone, paper-specific 2602.23246 replication
  tree separate from the metasurface replication. Its results are embedded in
  `replication/qw_metasurface` and the older ACQW consensus snapshot.

## Missing, blocked, or uncertain items

- No author Nextnano inputs or raw state files were found.
- No standalone reproduction report dedicated only to arXiv:2602.23246 existed
  before this documentation layer.
- The exact relationship between the paper's DFT/HSE06-corrected states and the
  repo's envelope-function cancellation remains unresolved.

## Key artifact paths

- Shared metasurface/ACQW report: `../../replication/qw_metasurface/REPORT.md`
- Shared parameters: `../../replication/qw_metasurface/config/paper_params.yaml`
- Aestimo ACQW checkpoints: `../../replication/qw_metasurface/phase2_aestimo/checkpoints/`
- chi^(2) discrepancy: `../../replication/qw_metasurface/phase4_chi2/DISCREPANCY.md`
- Solver consensus: `../../git/aestimo/paper/reference_data/acqw_solver_consensus_v1/`
