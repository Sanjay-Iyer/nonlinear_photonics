# Quantum-Well-Metasurface to Maximize Nonlinear Polarization

## Paper identity

- Source PDF: `../../Quantum-Well-Metasurface to Maximize Nonlinear Polarization.pdf`
- Paper: Fathi et al., arXiv:2604.15476v1 (2026)
- Main repo evidence: `../../replication/qw_metasurface/REPORT.md`
- Parameter file: `../../replication/qw_metasurface/config/paper_params.yaml`
- Comparison table: `../../replication/qw_metasurface/phase7_comparison/results/comparison.md`

## What the original paper studied

The paper combines two enhancement mechanisms for second-harmonic generation:

1. A GaAs/AlGaAs asymmetric coupled quantum well (ACQW) engineered to produce a
   large interband chi^(2) tensor element.
2. A dielectric TiO2 metasurface patterned above the multi-quantum-well (MQW)
   film to access the useful tensor component and increase local optical fields.

In plain terms, the ACQW supplies the nonlinear polarization, while the
metasurface reshapes the optical modes so that the free-space beam can drive the
otherwise hard-to-access nonlinear tensor component.

## Quantum-well and metasurface structure

| Item | Paper/repo value |
| --- | --- |
| MQW material system | GaAs wells and AlGaAs barriers |
| Period stack used in repo | AlGaAs 18.2 nm / GaAs 7.1 nm / AlGaAs 1.8 nm / GaAs 2.9 nm |
| Number of periods | 16 |
| Active asymmetry | `(7.1 - 2.9) / (7.1 + 2.9) = 0.42` |
| Barrier Al fraction used in repo | `x = 0.55`, adopted from the companion 2602.23246 paper |
| Interface variants | Abrupt and 1 nm graded interfaces |
| Optical MQW thickness used for metasurface | 595 nm |
| Metasurface | TiO2 cylinders, height 390 nm, radius 230 nm |
| Periods | 891 nm by 650 nm |
| Pump region | Near 1.57 um |

Important nuance: 16 periods times 30 nm gives 480 nm, but the paper reports a
595 nm film. The repo treats the missing thickness as cap/buffer/terminating
material for the optical model and solves the electronic problem on one period.

## Physical quantities tracked

| Quantity | Paper-relevant role | Repo status |
| --- | --- | --- |
| Band structure and wavefunction localization | Confirms the asymmetric well design and state placement | Reproduced for the realistic graded variant |
| E11, E22 | Interband transition energies; E22 sets the material resonance | Aestimo and kdotpy agree to about 12 meV |
| Delta z(HH2,CB2) | Electron-hole centroid shift driving interband nonlinearity | Large in the graded structure |
| Interband overlaps and transition dipoles | Set oscillator strength and chi^(2) pathways | Evaluated through envelope matrix elements and Kane/DFT dipole anchors |
| chi^(2) spectral peak position | Resonant nonlinear response versus pump wavelength | Peak position reproduced near 1.45-1.50 um |
| chi^(2) magnitude | Absolute nonlinear susceptibility | Not reproduced in the coherent sum; electron/hole channels nearly cancel |
| GMR wavelengths and Q | Metasurface resonance placement and linewidth | Reproduced within stated tolerance/order |
| Field enhancement and overlap factor beta | Determines effective nonlinear response with metasurface | Reproduced after pump-bandwidth averaging and Q correction |
| BNN uncertainty | Surrogate confidence for design quantities | E22 well learned; chi^(2) uncertainty large, as expected |

## Models used in the repo

| Model | Contribution |
| --- | --- |
| Aestimo | Main envelope-function electronic structure, band edges, states, matrix elements, chi^(2) route |
| kdotpy | Independent 8-band k dot p transition-energy check; chi^(2) route uses kdotpy energies with Aestimo envelopes and is explicitly marked hybrid |
| BDD | Older solver-consensus context showing the ACQW state behavior is not Aestimo-only |
| grcwa / GRCWA | Metasurface transmission, resonance splitting, Q, modal overlap, and field enhancement |
| Deep ensemble surrogate | Bayesian-style surrogate trained on Aestimo-route and kdotpy-shifted samples |

## Numerical replication results found in repo

| Quantity | Paper / companion-reported value | Repo value | Agreement |
| --- | ---: | ---: | --- |
| E11 | about 1.49 eV in companion reference | Aestimo 1.496 eV ideal, 1.499 eV graded; kdotpy 1.507 eV | Good |
| E22 | about 1.62 eV in companion reference; operating SH energy near 1.58 eV | Aestimo 1.657 eV ideal, 1.674 eV graded; kdotpy 1.669 eV | Solver agreement good; literal 1.58 eV target not met |
| chi^(2) peak pump wavelength | about 1500 nm simulated, about 1570 nm experimental operating region | Aestimo graded peak about 1475 nm; kdotpy hybrid about 1438 nm; BNN about 1482 nm | Peak position broadly reproduced |
| chi^(2)_eff,MQW at 1.57 um | 1.6 nm/V measured | Aestimo coherent value about 0.062 nm/V; diagnostic electron channel about 2.34 nm/V | Coherent magnitude not reproduced |
| Resonance B wavelength | 1567 nm experimental, 1580 nm simulated | 1574 nm | Good |
| Q factor | 1124 measured | 2862 lossless simulation | Same order; higher as expected for lossless model |
| ExEz enhancement versus 45 degree bare film | about 57x | 195x effective, about 76x after Q correction | Good after Q correction |
| ExEz versus normal ExEx | about 11.5x | 36x effective, about 14x after Q correction | Good after Q correction |
| chi^(2)_eff,MQW+MS | about 14 nm/V, 17 nm/V without absorption correction | 2.23 nm/V using coherent MQW chi^(2); about 0.9 nm/V after Q correction | Not reproduced because material chi^(2) is low |

## What matched

- Coupled-well band-edge structure and realistic graded localization.
- HH2->CB2 transition energy consistency between Aestimo and kdotpy.
- chi^(2) spectral peak position near the paper's simulated peak.
- Selection-rule sign structure.
- Three guided-mode resonances and angular splitting behavior.
- Resonance B wavelength and order-of-magnitude Q.
- Modal-overlap symmetry: beta nearly zero at normal incidence and large at small tilt.
- Field-enhancement factors after accounting for pump bandwidth and measured-Q correction.

## What did not match

- The full coherent chi^(2) magnitude is about 7-20 times below the paper. The
  repo attributes this to destructive cancellation between electron and hole
  pathways in envelope-function states.
- The combined MQW plus metasurface effective chi^(2) remains low because it
  inherits the MQW material chi^(2) deficit.
- The literal calibration target E22 = 1.58 eV was not adopted because it was
  documented as physically inconsistent with the x = 0.55 companion-paper stack.

## Missing, blocked, or uncertain items

- Authors' exact Nextnano input deck, material database, state wavefunctions, and
  DFT/HSE06-corrected intermediate quantities are not present.
- kdotpy centroids are not trusted quantitatively with the approximate material
  bridge, so the kdotpy chi^(2) route is hybrid rather than fully independent.
- The repo has no ellipsometry file; the MQW index at 1550 nm was calibrated
  within a plausible literature band.

## Key artifact paths

- Main report: `../../replication/qw_metasurface/REPORT.md`
- Phase 2 Aestimo states: `../../replication/qw_metasurface/phase2_aestimo/`
- Phase 3 kdotpy check: `../../replication/qw_metasurface/phase3_kdotpy/`
- Phase 4 chi^(2): `../../replication/qw_metasurface/phase4_chi2/`
- Phase 5 metasurface: `../../replication/qw_metasurface/phase5_metasurface/`
- Phase 6 surrogate: `../../replication/qw_metasurface/phase6_bnn/`
- Phase 7 comparison: `../../replication/qw_metasurface/phase7_comparison/`
