# Missing Inputs and Author Requests

This file lists the specific missing files, parameters, and conventions needed
to turn partial public-information replications into full scientific
reproductions. Unknowns are explicitly marked unknown; no numerical result is
invented here.

## Summary by blocker type

| Blocker type | Papers affected | Why it matters |
| --- | --- | --- |
| Raw solver input decks | Quantum-Well-Metasurface, 2602.23246v1, APL 2023, Schaefer 2024 | Without the exact Nextnano/custom solver inputs, material conventions and state labeling cannot be uniquely reconstructed. |
| Material database and band offsets | All four | chi^(2) depends sensitively on transition energies, centroids, overlaps, and cancellation balance. |
| Raw wavefunctions/states | All four | Needed to compare envelope localization, overlaps, dipoles, and electron-hole cancellation directly. |
| k-space and density conventions | GaAs/AlGaAs chi^(2) papers, Schaefer 2024 | Needed for absolute chi^(2), spectral linewidths, and normalization. |
| Multiband/strain conventions | Schaefer 2024, kdotpy routes | Needed to decide whether scalar BDD, Aestimo, or kdotpy should be trusted for type-II and valence-mixed structures. |

## Quantum-Well-Metasurface and 2602.23246v1

### Needed author files or tables

| Needed input | Resolves |
| --- | --- |
| Nextnano input deck and version for the ACQW structure | Exact band edges, grid, boundary conditions, material database, state labels. |
| DFT/HSE06-corrected interband dipoles and state corrections | Whether paper's states reduce the envelope-solver electron/hole cancellation. |
| Normalized CB1/CB2/HH1/HH2/HH3 wavefunctions or density tables | Direct comparison of localization, centroids, overlaps, and state ordering. |
| State energies E11/E22 and nearby excited levels | Whether the local E22 offset is due to material parameters, grading, or labeling. |
| Centroids `<z>CB2`, `<z>HH2`, Delta z22, and interband overlaps | Direct check of the chi^(2)-driving matrix elements. |
| Separated electron and hole Eq. 2 pathway terms, especially [2,2,2] | Determines whether the paper has incomplete cancellation or a different sign/normalization convention. |
| Interface profile used in realistic simulations | Tests whether the 1 nm linear grading assumption is sufficient. |
| k-space quadrature, state density `Nz`, broadening, and tensor reporting convention | Needed for absolute chi^(2) and film-average conversion. |
| Ellipsometry index file for MQW at pump and second harmonic | Would remove the calibrated-index caveat in the metasurface simulation. |

### Author request draft content

Please provide the ACQW simulation input deck and the intermediate quantities used
to compute the interband chi^(2): normalized envelope functions for CB1/CB2 and
HH1/HH2/HH3, transition energies, centroids, interband overlaps, z matrix
elements, separated electron and hole pathway terms, k-space grid/density
conventions, broadening, and the exact interface grading profile. The specific
goal is to determine why local Aestimo/kdotpy/BDD envelope calculations reproduce
the transition energies and peak wavelength but over-cancel the coherent
electron/hole chi^(2) by roughly one order of magnitude.

## APL 2023

### Needed author files or tables

| Needed input | Resolves |
| --- | --- |
| Nextnano input deck/version for the APL sweeps | Exact geometry, material, Poisson, and boundary conventions. |
| Material database: band offsets, masses, Luttinger parameters, temperature | Fig. 2a peak positions and Fig. 5a barrier optimum sensitivity. |
| Raw Fig. 2/3/4/5 data | Removes digitization uncertainty and Fig. 5b axis ambiguity. |
| State energies, normalized wavefunctions, centroids, and overlaps versus asymmetry/barrier/width | Tests whether remaining mismatches come from state physics or postprocessing. |
| Separated electron/hole [2,2,2] terms, S22, `<z>CB2`, `<z>HH2`, Delta z22 | Directly tests pathway timing and cancellation. |
| `Nz`, k-space weights, angular degeneracy, spin/HH projection, and absolute normalization convention | Needed before absolute chi^(2) can be audited. |
| Exact Fig. 5b plotted width variable | Needed because current docs classify the printed figure/prose as internally inconsistent. |

### Author request draft content

Please provide the raw numerical data and simulation inputs for the APL 2023 ACQW
figures, especially the Fig. 2a asymmetry curves, Fig. 5a barrier sweep, and
Fig. 5b width sweep. The local reproduction validates the electronic-state
architecture and pathway bookkeeping, but cannot resolve the late Fig. 2a peaks,
baseline 3 nm Fig. 5a optimum, Fig. 5b width-axis ambiguity, or absolute chi^(2)
normalization without the intermediate state and pathway quantities.

## Schaefer 2024

The clean `paper_replication_results` layer currently labels Schaefer as having
no artifacts, but a broader evidence subtree exists at
`../../git/aestimo/paper/schaefer_2024/releases/schaefer2024_public_reproduction_final_v1/`.
That release classifies Schaefer Tier 1 as not testable/not reproduced from
public information and says no further Schaefer simulations are justified without
new author data.

### Required material and model parameters

| Required input | Why needed |
| --- | --- |
| Exact T2 layer stack and all Table I structures | The local release reconstructed nominal T2, but solver-relevant conventions remain unpublished. |
| InP / Al0.38Ga0.10In0.52As / Al0.48In0.52As material records | Needed for band edges, offsets, masses, Kane potential, and confinement. |
| Alloy interpolation and bowing rules for AlGaInAs and AlInAs | The paper/supplement do not uniquely fix all solver-relevant alloy conventions. |
| Electron mass, HH/LH masses, Luttinger parameters, spin-orbit splitting, Kane Ep | Needed to decide whether scalar BDD, Aestimo, or kdotpy can represent the intended Hamiltonian. |
| Strain orientation, substrate convention, elastic constants, deformation potentials, and strain-shift formula | Required before any 8-band or strained-valence calculation can be called faithful. |
| Finite-difference domain, grid, boundary conditions, and phase convention | Needed for signed overlaps and centroids. |
| Raw Table I states, transition energies, overlaps, centroid separations, and dipoles | Needed to diagnose why excited-state quantities were not reproduced. |
| `Nz`, k cutoff, broadening, tensor component, and absolute-unit convention | Needed before relative or absolute chi^(2) should be attempted. |

### Author request draft content

Please provide the exact material parameter table and solver setup used for the
Schaefer 2024 T2 Table I calculation: layer sequence, layer widths, band-edge
reference convention, alloy interpolation/bowing rules, electron/HH/LH masses,
Kane potential, Luttinger/8-band parameters if used, strain model, domain/grid,
phase convention, and raw state/intermediate values. Local public-information
BDD/Aestimo/kdotpy checks could not reproduce excited-state transitions,
overlaps, or centroid separations, and chi^(2) was not attempted because the
state benchmark did not pass.
