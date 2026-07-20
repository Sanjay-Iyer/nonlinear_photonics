# Next Actions for Full Replication

## Near-term documentation improvements

1. Add a machine-readable manifest for `paper_replication_results/` listing every
   source artifact used in each summary.
2. Add thumbnail/contact-sheet references for the major generated figures:
   band-edge plots, state plots, chi^(2) spectra, metasurface transmission maps,
   BNN parity/calibration plots, and APL relative overlays.
3. Add a short glossary figure or schematic for ACQW terms: wide well, narrow
   well, coupling barrier, Delta z, E11/E22, and electron-hole pathway cancellation.

## Physics/modeling next actions

| Priority | Action | Rationale |
| --- | --- | --- |
| High | Obtain exact author Nextnano/material inputs for GaAs/AlGaAs papers | The dominant unresolved discrepancies depend on material parameters, state centroids, and pathway terms not published in sufficient detail. |
| High | Preserve coherent chi^(2) as the primary physical observable while reporting channel magnitudes only as diagnostics | This avoids overstating agreement when electron and hole channels cancel. |
| Medium | Build a standalone `2602.23246` replication report if that paper will be discussed independently | Current evidence is embedded in the metasurface replication. |
| Medium | Extend kdotpy/8-band centroid validation before using kdotpy for quantitative chi^(2) | Current kdotpy chi^(2) route is hybrid because centroids are unreliable with the approximate bridge. |
| Medium | Extract the Schaefer 2024 type-II AQW target manifest from the PDF | No implementation can be trusted until the layer structures and material parameters are explicit. |
| Medium | Prototype Schaefer 2024 with a BDD/custom envelope solver | Type-II InP/AlGaInAs may require explicit band-edge and mass handling beyond the current Aestimo database. |
| Low | Package the documentation layer as a release snapshot with hashes | Useful if these notes become part of an external expert discussion. |

## Information to request from authors

For the GaAs/AlGaAs ACQW papers:

- Nextnano input files and version.
- Material database or exact band offsets, masses, Luttinger parameters, and
  temperature.
- Normalized wavefunctions or densities for CB1/CB2/HH1/HH2/HH3.
- E11/E22 values, centroids, Delta z values, overlaps, and oscillator strengths.
- Separated electron and hole pathway terms, especially [2,2,2].
- Raw data for chi^(2) spectra and figure sweeps.

For the Schaefer 2024 type-II paper:

- Layer-by-layer designs and alloy fractions for all three structures.
- Band alignment diagrams, effective masses, and band offsets.
- Target wavelengths/frequencies and tensor-component definitions.
- Raw or tabulated chi^(2) spectra and peak values.
