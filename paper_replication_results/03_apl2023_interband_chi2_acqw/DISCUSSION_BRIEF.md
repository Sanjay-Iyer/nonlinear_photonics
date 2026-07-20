# Expert Discussion Brief - APL 2023 Interband chi^(2) ACQW

## 5-sentence plain-English summary

This paper is the theory benchmark for asymmetric GaAs/AlGaAs coupled quantum wells. The repo's older APL-2023 release reproduces the main electronic-state story: heavy-hole relocation, conduction-state localization, and pathway bookkeeping are internally consistent. The relative chi^(2) trends are only partially reproduced. The biggest remaining mismatches are the Fig. 2a asymmetry peak positions, Fig. 5a barrier optimum under the frozen baseline, Fig. 5b width trend, and absolute chi^(2), which was intentionally not audited. The best meeting summary is that the state physics is validated, but the full relative and absolute nonlinear response is author-data limited.

## Expert-level technical summary

The APL 2023 benchmark uses GaAs wells and Al0.4Ga0.6As barriers with d1 = D(1+s)/2, d2 = D(1-s)/2, D = 5, 7.5, 10, and 12.5 nm, and a 1 nm baseline coupling barrier. The repo models the electronic states with Aestimo and an independent BDD solver, preserving energy-order labels, overlap tracking, well probabilities, centroids, and HH/LH character diagnostics. HH2 relocation near s about 0.45 is reproduced: the documented crossovers are s = 0.44070 for BDD and s = 0.44486 for Aestimo, and CB2 remains thin-well dominated near the optimum region. Relative Eq. 3 pathway bookkeeping and pairwise cancellation mechanisms are validated qualitatively, but the full relative chi^(2) architecture is not fully reproduced. The APL release closes local public-information modeling and keeps absolute chi^(2) frozen until author intermediate data or an independent benchmark is available.

## What the paper reported

| Quantity | Reported target or context |
| --- | --- |
| Material system | GaAs / Al0.4Ga0.6As ACQW |
| Geometry | d1 = D(1+s)/2, d2 = D(1-s)/2 |
| Width families | D = 5, 7.5, 10, 12.5 nm |
| Baseline coupling barrier | 1 nm |
| Formalism | Dipole-matrix chi^(2) with two bound electron and two bound heavy-hole states |
| Key figures | chi^(2) versus asymmetry, pathways, pairwise cancellation, barrier thickness, total width, and spectra |

## What we reproduced

| Result | Repo status |
| --- | --- |
| HH2 relocation | Reproduced near s about 0.45 with Aestimo and BDD |
| CB2 thin-well character | Reproduced near the optimum region |
| E22 near s = 0.45, D = 10 nm | Internal solver agreement: BDD about 1.61678 eV and Aestimo about 1.61814 eV |
| Pathway bookkeeping | Eq. 3 ledger reconstruction closes |
| Pairwise cancellation mechanism | Qualitatively validated |
| Test suite | Final diagnostics report 35 passed tests |

## What partially matched

- Fig. 2a chi^(2) versus asymmetry has endpoint behavior, intermediate maxima, and some family ordering, but peak positions are late.
- Fig. 5a barrier trend has useful sensitivity diagnostics, especially to Qc/Qv band-offset split.
- Fig. 5c spectral resonances are approximately reproduced in count and location.
- The [2,2,2] pathway is correctly identified as a major contributor, but not enough to close every figure.

## What did not match

- Fig. 2a model peaks are late by about +0.04 to +0.07 in asymmetry s.
- Fig. 5a frozen-baseline optimum is about 3.0 nm rather than about 1-1.25 nm.
- Fig. 5b width trend is not reproduced under either printed-axis or prose/caption interpretation.
- Absolute chi^(2) was not audited and should not be claimed.

## What is blocked or missing

- Nextnano input deck/version and material database.
- Exact band offsets, masses, Luttinger parameters, temperature, and boundary conventions.
- Raw Fig. 2/3/4/5 data and the exact Fig. 5b plotted width variable.
- State energies, normalized wavefunctions, centroids, overlaps, and separated [2,2,2] electron/hole terms.
- `Nz`, k-space weights, angular degeneracy, spin/HH projection, and absolute normalization convention.

## How I would explain this in a meeting

"For APL 2023, I would separate the electronic-state benchmark from the nonlinear figure benchmark. The state benchmark is strong: Aestimo and BDD both reproduce the HH2 relocation and CB2 localization story. The relative chi^(2) curves are more complicated: pathway bookkeeping and cancellation mechanisms work, but the exact peak locations and barrier/width trends do not fully match the paper. The most current-data-solvable piece is Fig. 5a band-offset sensitivity; the rest likely needs author simulation inputs or raw intermediate quantities."

## 5 likely expert questions and concise answers

| Question | Answer |
| --- | --- |
| Did the APL reproduction pass? | The electronic-state part passed; the relative chi^(2) figure reproduction is partial; absolute chi^(2) is frozen. |
| Is Aestimo the problem? | Probably not solely. BDD agrees on key state behavior and some discrepancy mechanisms. |
| Which mismatch is most tractable now? | Fig. 5a barrier optimum, as a non-adopted band-offset sensitivity explanation. |
| Which mismatch most needs author data? | Fig. 2a peak positions, Fig. 5b width trend, and absolute chi^(2). |
| Can we adopt Qc=0.60/Qv=0.40? | No. It is a diagnostic variant that improves Fig. 5a, not an adopted baseline without author evidence. |

## Key terms I need to know

| Term | Meeting-ready meaning |
| --- | --- |
| E11 / E22 | Interband transition energies between HH and CB subbands. |
| HH1 / HH2 | Heavy-hole confined states whose relocation drives the APL story. |
| CB1 / CB2 | Conduction confined states; CB2 staying thin-well localized matters near optimum. |
| Oscillator strength | Optical transition strength from overlaps and dipoles. |
| Wavefunction localization | Probability distribution between wide and thin wells. |
| Centroid asymmetry | Difference in electron and hole z-centroids. |
| chi^(2) | Nonlinear susceptibility calculated from pathway sums. |
| Electron-hole cancellation | Opposing electron and hole pathway terms reduce total response. |
| BDD | Independent scalar solver validating state behavior. |
| Aestimo | Main local envelope solver. |
| kdotpy | Considered but not counted as an APL reproducing solver. |
| GRCWA / GMR / Q factor / modal overlap | Not central to APL; these are metasurface-paper terms. |
| Type-I vs type-II AQW | APL uses GaAs/AlGaAs coupled wells; Schaefer focuses on type-II separation. |
| Band-offset sensitivity | Central to Fig. 5a; Qc/Qv changes can move the optimum. |
