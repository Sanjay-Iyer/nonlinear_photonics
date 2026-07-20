# Interband second-order nonlinear optical susceptibility of asymmetric coupled quantum wells

## Paper identity

- Source PDF:
  `../../Interband second-order nonlinear optical susceptibility of asymmetric coupled quantum wells.pdf`
- Paper: Ramesh et al., Applied Physics Letters 123, 251111 (2023)
- DOI: 10.1063/5.0168596
- Main repo release:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/`
- Final status:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/docs/APL_2023_FINAL_PUBLIC_REPRODUCTION_STATUS.md`

## What the original paper studied

The APL 2023 paper calculates interband chi^(2) in asymmetric GaAs/AlGaAs
coupled quantum wells. It uses a dipole-matrix formalism with two bound electron
states and two bound heavy-hole states. The central idea is that structural
asymmetry and interwell coupling create non-centrosymmetric envelope functions,
which allow large second-order optical susceptibility at telecommunication-scale
frequencies.

## Quantum-well structure and key parameters

| Item | Paper/repo value |
| --- | --- |
| Material system | GaAs wells / Al0.4Ga0.6As barriers |
| Well widths | `d1 = D(1+s)/2`, `d2 = D(1-s)/2` |
| Asymmetry | `s = (d1 - d2)/(d1 + d2)` |
| Total GaAs width families | D = 5, 7.5, 10, 12.5 nm |
| Baseline coupling barrier | 1 nm |
| Broadening recorded | Gamma = 5 meV |
| Interband Bloch dipole recorded | r(e,hh) = 7.51 Angstrom |
| k-space range recorded | In-plane k integrated to 0.1 Brillouin zone |

The repo's APL work intentionally separates this APL-2023 structure from the
2026 x = 0.55 materials/metasurface stack.

## Main physical quantities tracked

| Quantity | Repo handling |
| --- | --- |
| Band structure | Evaluated with Aestimo and independent BDD for the APL geometry |
| Wavefunction localization | HH1, HH2, CB1, CB2 well probabilities and centroids tracked versus asymmetry |
| E11 and E22 | Reported in state sweeps, especially near s = 0.45 |
| HH2 relocation | Reproduced near the paper's s about 0.45 region |
| Oscillator/pathway terms | Eq. (3) pathway bookkeeping and pairwise cancellation ledgers built |
| chi^(2) versus asymmetry | Partially reproduced in relative units |
| chi^(2) versus barrier thickness | Partially reproduced; optimum location differs under baseline |
| chi^(2) versus total width | Not reproduced; paper figure/axis is marked suspect |
| Spectral response | Partially/approximately reproduced for resonance locations |
| Absolute chi^(2) normalization | Not audited; intentionally frozen |

## Models used in the repo

| Model | Contribution |
| --- | --- |
| Aestimo | Main envelope-function state solver for APL geometry |
| BDD | Independent scalar BenDaniel-Duke check for state localization and pathway balance |
| kdotpy | Considered but not counted for APL reproduction; the available bridge was not testable for the APL gate |
| Diagnostic postprocessing variants | Tested detuning, k cutoff, broadening placement, and related conventions |

## Numerical results achieved in the repo

| Quantity | Paper target or context | Repo result | Agreement |
| --- | ---: | ---: | --- |
| HH2 relocation | Near s about 0.45 | BDD crossover s = 0.44070; Aestimo crossover s = 0.44486 | Good |
| CB2 localization near optimum | Thin-well dominated | BDD/Aestimo both thin dominated near s = 0.45 | Good |
| E22 near s = 0.45, D = 10 nm | Paper does not publish exact state energy | BDD 1.61678 eV; Aestimo 1.61814 eV after 0.025 nm refinement | Internal solver agreement good |
| Fig. 2a asymmetry peaks | Digitized peaks around s = 0.44-0.58 depending D | Repo peaks systematically late by about +0.04 to +0.07 in s | Partial |
| Fig. 5a barrier optimum | Digitized optimum about 1-1.25 nm | Frozen baseline optimum 3.0 nm; Qc=0.60/Qv=0.40 diagnostic moves to 1.25 nm but is not adopted | Partial and parameter-sensitive |
| Fig. 5b total-width trend | Printed figure/prose inconsistent | Not reproduced under either interpretation | Not reproduced |
| Spectra | Resonance families in Fig. 5c | Four prominent resonances per width; mean location errors about 0.052-0.061 eV | Partial/good for positions |
| Tests | Internal repo validation | Final suite: 35 passed | Good implementation validation |

## What matched

- Electronic-state architecture: CB/HH ordering, HH2 relocation, and CB2 thin-well
  character near the reported optimum region.
- Aestimo and BDD agree qualitatively and quantitatively enough to show the main
  localization result is not Aestimo-specific.
- Eq. (3) pathway bookkeeping closes, and pairwise cancellation mechanisms are
  qualitatively reproduced.
- The [2,2,2] pathway is identified as important in the asymmetry behavior.
- Spectral resonance locations are diagnostically comparable.

## What did not match

- The total chi^(2) asymmetry peak locations are systematically later than the
  digitized paper curves.
- The baseline coupling-barrier optimum is 3.0 nm rather than about 1-1.25 nm.
- The Fig. 5b width trend is not reproduced and is also marked internally
  inconsistent in the paper.
- Absolute chi^(2) was not attempted because the relative architecture was not
  fully closed.

## Missing, blocked, or uncertain items

- Exact Nextnano input deck, material database, band offsets, masses,
  temperature, and solver settings are absent.
- Raw paper data for figures and intermediate quantities are absent.
- Needed intermediate quantities include electron/hole [2,2,2] terms, S22,
  `<z>CB2`, `<z>HH2`, Delta z22, CB2/HH2 energies, normalized wavefunctions, and
  raw Fig. 2/3/4/5 source data.
- The repo explicitly closes local public-information modeling and recommends
  author data before further full replication claims.

## Key artifact paths

- Final status:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/docs/APL_2023_FINAL_PUBLIC_REPRODUCTION_STATUS.md`
- State reproduction:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/docs/APL_2023_STATE_REPRODUCTION.md`
- Relative chi^(2) reproduction:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/docs/APL_2023_RELATIVE_CHI2_REPRODUCTION.md`
- Attribution diagnostics:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/docs/APL_2023_RELATIVE_CHI2_ATTRIBUTION.md`
- Tables:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/tables/`
- Tests:
  `../../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/tests/`
