# Paper Replication Results Index

This directory is a clean documentation/results layer for the nonlinear photonics
replication work in this repository. It does not move, overwrite, or delete the
original source PDFs, scripts, logs, checkpoints, figures, or reports. Each page
below points back to the original artifacts that support its claims.

## Directory map

| Directory | Paper | Current repo status |
| --- | --- | --- |
| `01_quantum_well_metasurface/` | Fathi et al., "Quantum-Well-Metasurface to Maximize Nonlinear Polarization" | Main completed replication track. Aestimo, kdotpy, GRCWA, and deep-ensemble surrogate artifacts exist. |
| `02_enhanced_interband_nonlinearities_2602_23246/` | Ramesh et al., arXiv:2602.23246v1, "Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells" | Used as a companion materials/reference paper and partially tested through the same ACQW structure. |
| `03_apl2023_interband_chi2_acqw/` | Ramesh et al., APL 123, 251111 (2023), "Interband second-order nonlinear optical susceptibility of asymmetric coupled quantum wells" | Separate older public-information replication suite exists; electronic states reproduced, relative chi2 partially reproduced, absolute chi2 frozen. |
| `04_schaefer2024_type_ii_aqw/` | Schaefer et al., JAP 135, 193105 (2024), "Enhanced second-order nonlinear susceptibility in type-II asymmetric quantum well structures" | Source PDF exists. No repo replication artifacts were found. |
| `comparison_all_papers/` | Cross-paper comparison | Side-by-side status, quantities, discrepancies, and next actions. |

## Modeling vocabulary used in these notes

| Term | Short meaning |
| --- | --- |
| `Aestimo` | A 1D Schrodinger-Poisson/envelope-function quantum-well solver used here for band edges, subband energies, envelope wavefunctions, centroids, and matrix elements. |
| `BDD` | Independent scalar BenDaniel-Duke finite-difference solver. It is useful as a check that Aestimo-specific implementation details are not driving a result. |
| `kdotpy` | Multiband k dot p solver used as an independent electronic-structure cross-check, especially for transition energies and valence-band mixing. |
| `GRCWA` / `grcwa` | Rigorous coupled-wave analysis used for metasurface transmission, guided-mode resonances, modal overlap, and field-enhancement estimates. |
| `BNN` / deep ensemble | A Bayesian-style surrogate model implemented as an ensemble of neural networks with uncertainty estimates. In this repo it predicts robust quantities such as E22 better than cancellation-sensitive chi^(2). |
| `E11`, `E22` | Interband transition energies, usually HH1->CB1 and HH2->CB2. |
| `chi^(2)` | Second-order nonlinear susceptibility. In these papers it is enhanced by asymmetric quantum-well envelope functions and resonant interband transitions. |
| `Delta z` | Electron-hole centroid separation along the growth direction. It is a key measure of broken inversion symmetry and contributes to interband chi^(2). |
| `GMR` | Guided-mode resonance in the metasurface. It can enhance local pump and second-harmonic fields inside the MQW region. |

## Primary source artifacts

- Source PDFs in the repository root:
  - `Quantum-Well-Metasurface to Maximize Nonlinear Polarization.pdf`
  - `2602.23246v1.pdf`
  - `Interband second-order nonlinear optical susceptibility of asymmetric coupled quantum wells.pdf`
  - `193105_1_5.0174179.pdf`
- Main metasurface replication report: `../replication/qw_metasurface/REPORT.md`
- Main metasurface single-source parameter file: `../replication/qw_metasurface/config/paper_params.yaml`
- APL-2023 final public reproduction release:
  `../git/aestimo/paper/apl_2023/releases/apl2023_public_reproduction_final_v1/`
- ACQW three-solver consensus snapshot:
  `../git/aestimo/paper/reference_data/acqw_solver_consensus_v1/`

Note: the `git/aestimo/...` subtree is an evidence subtree used by this
documentation layer. It contains older replication releases, diagnostics, and
reference-data snapshots that are not moved into `paper_replication_results/`.

## How to read this layer

Start with `comparison_all_papers/ALL_PAPERS_COMPARISON.md` for the broad story.
Then open the paper-specific `SUMMARY.md` files for details, evidence paths, and
known blockers. Claims are labeled as paper-reported, repo-reproduced, partially
reproduced, not reproduced, or not found in repo.
