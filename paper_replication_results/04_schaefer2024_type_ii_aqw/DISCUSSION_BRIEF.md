# Expert Discussion Brief - Schaefer 2024 Type-II AQW

## 5-sentence plain-English summary

This paper studies type-II asymmetric quantum wells, where electrons and holes are deliberately separated to increase nonlinear response. The clean documentation layer originally found only the source PDF and no Schaefer-specific modeling artifacts. The roadmap then found an older Schaefer evidence subtree with a Tier-1 public-information attempt. That older release says a scalar BDD state calculation ran and the ground-state transition was approximately reproduced, but excited transitions, overlaps, centroid separations, and chi^(2) were not reproduced or not attempted. The safest expert-facing message is that Schaefer is not ready for new modeling claims until the clean documentation is reconciled with that older release and missing author/material inputs are obtained.

## Expert-level technical summary

Schaefer 2024 targets type-II InP/AlGaInAs-family AQWs, where spatial separation of electron and hole states should enhance centroid asymmetry and interband chi^(2). The PDF/source note says the paper compares type-I and type-II AQW designs in lattice-matched InP/AlGaInAs using an envelope-wavefunction approximation and reports tensor elements from about 20 to 1.60 x 10^3 pm/V. The clean `paper_replication_results` Schaefer summary says no paper-specific configs, scripts, or outputs were found. The later roadmap identified a broader `git/aestimo/paper/schaefer_2024` release that closed Tier 1 as not testable/not reproduced from public information: BDD ran, but excited-state transitions, overlaps, centroid separations, dipole definitions, relative chi^(2), and absolute chi^(2) were not reproduced. The most important scientific point is that scalar BDD can be a smoke test, but faithful Schaefer reproduction likely needs missing multiband, strain, alloy, band-edge, and signed-overlap conventions.

## What the paper reported

| Quantity | Reported target or context |
| --- | --- |
| Material family | Lattice-matched InP/AlGaInAs; broader release also refers to InP / Al0.38Ga0.10In0.52As / Al0.48In0.52As for T2 work |
| Band alignment | Type-I and type-II AQW designs |
| Method | Envelope-wavefunction approximation |
| Reported chi^(2) scale | About 20 to 1.60 x 10^3 pm/V from the source note |
| Mechanism | Type-II separation increases interband charge shift and centroid asymmetry |

## What we reproduced

| Result | Status |
| --- | --- |
| Clean layer | No Schaefer modeling artifacts found in the clean summary |
| Broader evidence subtree | Older release reports a validated BDD execution and approximate e1-hh1 ground-state reproduction |
| Numerical convergence in older release | Reported as validated for BDD Tier 1 |

## What partially matched

- The broader release says T2 structure reconstruction was approximately reproduced.
- The e1-hh1 ground-state transition was approximately reproduced.
- BDD produced reproducible state, transition, overlap, centroid, and plot artifacts, but those did not close the paper benchmark.

## What did not match

- Excited-state transitions e1-hh2, e2-hh1, e2-hh2, and LH-related quantities were not reproduced in the older release.
- Most excited-state overlap magnitudes and signs did not match.
- Electron-hole centroid separations were systematically insufficient relative to the published values.
- Relative chi^(2) and absolute chi^(2) were not attempted.
- Native Aestimo failed strict BDD-Aestimo common-case alignment; kdotpy was not testable without custom eight-band/strain/material inputs.

## What is blocked or missing

- Exact T2 layer stack used for Table I and all relevant structures.
- Full InP/AlGaInAs/AlInAs material database, alloy interpolation, and bowing rules.
- Multiband parameters: Luttinger, Kane, spin-orbit, remote-band, deformation-potential, and elastic constants.
- Strain/orientation/substrate conventions and strain-shift formula.
- Domain/grid/boundary conditions and signed-overlap phase convention.
- Raw Table I states, transition energies, overlaps, centroid separations, and dipoles.
- `Nz`, k cutoff, broadening, tensor-component definitions, and absolute-unit conventions.

## How I would explain this in a meeting

"Schaefer is the type-II benchmark, but it is not currently a clean reproduction story. The source paper is attractive because type-II alignment should give a larger charge shift, but the local evidence says public information was not enough to reproduce the excited-state table. A scalar BDD smoke test ran in the older subtree and got limited ground-state agreement, but Aestimo and kdotpy did not provide a validated resolution. I would say the next step is author-data acquisition and documentation reconciliation, not more parameter sweeps."

## 5 likely expert questions and concise answers

| Question | Answer |
| --- | --- |
| Has Schaefer been modeled in this repo? | The clean layer says no, but the roadmap found an older Schaefer Tier-1 release. That needs reconciliation. |
| Did the older Schaefer attempt reproduce the paper? | No. It approximately reproduced limited ground-state behavior but not excited transitions, overlaps, centroids, or chi^(2). |
| Is BDD enough? | BDD is enough for a scalar smoke test, not for a full type-II/multiband/strain-sensitive reproduction. |
| Is kdotpy required? | Not for the first scalar smoke test; likely required only if the benchmark depends on multiband valence mixing or strain, but custom material inputs are missing. |
| What should be requested from authors? | Exact layer stack, material database, alloy/strain conventions, solver grid/domain, phase convention, raw states, and Table I intermediate values. |

## Key terms I need to know

| Term | Meeting-ready meaning |
| --- | --- |
| E11 / E22 | Interband transitions; Schaefer discusses e1-hh1 and excited combinations such as e2-hh2. |
| HH1 / HH2 | Heavy-hole states; excited HH quantities were not reproduced in the older release. |
| CB1 / CB2 | Electron states e1/e2 in the conduction band. |
| Oscillator strength | Optical transition strength; depends on overlap and dipole definitions. |
| Wavefunction localization | Where electron and hole states sit in a type-II stack. |
| Centroid asymmetry | Electron-hole spatial separation; central to type-II enhancement. |
| chi^(2) | Nonlinear susceptibility; not attempted locally because state reproduction did not pass. |
| Electron-hole cancellation | Important in GaAs/AlGaAs papers; Schaefer's current blocker is earlier, at state/intermediate reproduction. |
| BDD | Scalar finite-difference smoke-test solver. |
| Aestimo | Attempted via an adapter in the older release, but strict alignment failed. |
| kdotpy | Not testable for Schaefer without custom 8-band material and strain inputs. |
| GRCWA / GMR / Q factor / modal overlap | Not relevant unless a metasurface is added; these belong to the Fathi paper. |
| Type-I vs type-II AQW | Type-I keeps electron and hole in the same region; type-II deliberately separates them. |
| Band-offset sensitivity | Especially important in type-II AQWs because offsets control localization and centroid separation. |
