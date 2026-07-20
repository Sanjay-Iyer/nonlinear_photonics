# Enhanced second-order nonlinear susceptibility in type-II asymmetric quantum well structures

## Paper identity

- Source PDF: `../../193105_1_5.0174179.pdf`
- Paper: Schaefer et al., Journal of Applied Physics 135, 193105 (2024)
- DOI: 10.1063/5.0174179
- Title: "Enhanced second-order nonlinear susceptibility in type-II asymmetric quantum well structures"
- Local source note: `SOURCE_NOTE.md`

## What the original paper studied

The paper studies asymmetric quantum wells with type-II band alignment. Type-II
alignment spatially separates electron and hole states more strongly than
type-I alignment, which can increase the interband charge shift and therefore
enhance second-order nonlinear susceptibility.

The source note records a first-page/abstract extraction from the local PDF. From
that source, the paper analyzes three type-I and type-II asymmetric quantum-well
designs in lattice-matched InP/AlGaInAs material systems using an
envelope-wavefunction approximation. It reports calculated interband
second-order susceptibility tensor elements in the range of about 20 to
1.60e3 pm/V for nearly resonant optical rectification and
difference-frequency-generation applications at near-infrared and terahertz
wavelengths.

## Quantum-well structure and key parameters

Detailed layer-by-layer structures, alloy fractions, masses, band offsets, and
solver settings were not found in existing repo artifacts. They are expected to
be in the PDF, but no repo implementation or parsed parameter manifest exists
yet.

| Item | Status |
| --- | --- |
| Material system | InP/AlGaInAs lattice-matched family, from PDF text |
| Band alignment | Type-I and type-II AQW designs, from PDF text |
| Well/barrier geometry | Not found in repo documentation or configs |
| Alloy compositions | Not found in repo documentation or configs |
| E11/E22 values | Not found in repo |
| Wavefunction localization | Not found in repo |
| Oscillator strengths / transition dipoles | Not found in repo |
| chi^(2) tensor elements | Paper text mentions about 20 to 1.60e3 pm/V; repo reproduction not found |
| Spectral peak positions | Not found in repo |

## Repo replication status

No replication artifacts were found for this paper. Searches for `Schaefer`,
`type-II`, `0174179`, `Enhanced second-order`, `InP`, and `AlGaInAs` did not find
scripts, reports, configs, logs, or generated results in the repo.

## Models used in the repo

| Model | Status for this paper |
| --- | --- |
| Aestimo | Not yet used for this paper |
| BDD | Not yet used for this paper |
| kdotpy | Not yet used for this paper |
| GRCWA | Not applicable unless a metasurface or photonic structure is added; not used |
| BNN/deep ensemble | Not yet used |

## What matched

Not yet reproduced. No paper-specific model outputs were found.

## What did not match

No mismatch can be assessed because there is no repo replication yet.

## Missing, blocked, or uncertain items

- A paper-specific parameter extraction pass is needed.
- Layer structures, alloy compositions, band offsets, effective masses, and
  target wavelengths need to be parsed from the PDF and converted into a
  machine-readable config.
- Aestimo may not directly cover the full InP/AlGaInAs type-II material system
  without database extension or careful material-parameter injection.
- A BDD or custom envelope-function solver may be a better first baseline
  because it can accept explicit band edges and effective masses.
- No chi^(2) implementation has been adapted to the type-II tensor elements and
  optical-rectification/difference-frequency-generation cases from this paper.

## Recommended next actions

1. Extract a target manifest from the PDF: designs, material compositions, band
   offsets, effective masses, transition energies, dipoles, and reported chi^(2)
   values.
2. Build a paper-specific config under a new modeling directory, without changing
   the existing GaAs/AlGaAs ACQW artifacts.
3. Start with a scalar BDD envelope-function reproduction of band edges and
   localization for each design.
4. Add or validate an Aestimo material database path only after the explicit
   InP/AlGaInAs parameters are available.
5. Implement the paper's reported chi^(2) tensor calculation in a small,
   auditable script and compare against the reported 20 to 1.60e3 pm/V range.

## Key artifact paths

- Source PDF: `../../193105_1_5.0174179.pdf`
- Source note: `SOURCE_NOTE.md`
- No existing repo results found.
