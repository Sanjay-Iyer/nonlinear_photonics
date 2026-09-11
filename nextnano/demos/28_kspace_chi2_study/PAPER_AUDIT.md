# Paper claims and differences from the retained baseline

## Primary sources actually inspected

1. Ramesh et al., *Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells*, [arXiv:2602.23246v1, full text](https://arxiv.org/html/2602.23246v1), particularly Sections 2.1, 2.2, 3.2 and 5.1.
2. The preceding publication cited there: Ramesh et al., *Interband second-order nonlinear optical susceptibility of asymmetric coupled quantum wells*, [Applied Physics Letters 123, 251111 (2023), DOI 10.1063/5.0168596](https://doi.org/10.1063/5.0168596). The repository's `Interband second-order nonlinear optical susceptibility of asymmetric coupled quantum wells.pdf` was read directly (7 PDF pages, including its cover). PDF page 4 / printed page 251111-3 contains the DFT matrix-element value.

These are references for auditing; neither paper nor an old demo is imported or needed at calculation runtime. The requested supplementary information is mentioned in the 2026 manuscript, but no separate clearly identified 2026 supplement was located in the inspected repository source inventory. We do not treat previous AI-generated reports or code as substitutes for the missing supplement.

## Claim checklist against the 2026 primary text

| Requested claim | Primary-text location | Result |
|---|---|---|
| Dipole/density-matrix formalism | 2.1 and 5.1, Eqs. 1-2 | Confirmed |
| Two conduction and two HH bound states | 5.1, before Eq. 2 | Confirmed |
| Filled starting valence states, occupation unity | 5.1, after Eq. 1 | Confirmed |
| Gamma = 5 meV | 5.1, after Eq. 2 | Confirmed |
| Convert k sum to kx,ky integral | 5.1, before Eq. 2 | Confirmed |
| Saturation and cutoff at one-tenth BZ | Same paragraph | Authors' stated finding; not independently proven by that sentence |
| Nextnano envelope calculation | 5.1, final paragraph | Schrödinger-Poisson stated |
| Unit-cell matrix element from HSE06/VASP | Same paragraph | Confirmed |
| Diagonal dominance and pairwise cancellations | 3.2 | Claimed; test separately in 28G |
| Simulated resonances near 760 and 1520 nm | 2.2 | Confirmed |

The checklist reports the paper's claims, not a certification that our implementation matches every modeling detail. [2026 primary manuscript](https://arxiv.org/html/2602.23246v1)

## r_e,hh is a fixed, sourced literature input

The 2023 paper reports `r_e,hh = 7.51 angstrom` from VASP/HSE06 on printed page 251111-3. Therefore

```text
7.51 angstrom = 0.751 nm
```

matches `settings.r_e_hh_nm = 0.751` in Demo 28. This value does **not** come from our nextnano output, an envelope overlap, or a DFT calculation performed in this workflow. It is a bulk unit-cell dipole-length constant adopted from the earlier publication. The historical code retained that same value. Reproducing the authors' DFT independently, including wavefunctions and computational settings, remains outside this cached-data package. [2023 publication](https://doi.org/10.1063/5.0168596)

The earlier paper also expressly associates its restricted k range with use of the effective-mass approximation. It does not supply, in that paragraph, a numerical disk-versus-square integration rule. Its cancellation illustrations concern an asymmetry sweep at the specified geometry/detuning; they are not a general theorem guaranteeing cancellation at every wavelength of our different baseline. [2023 publication, printed pp. 251111-3 to 251111-5](https://doi.org/10.1063/5.0168596)

## Schrödinger-Poisson is not another name for 8-band k.p

These descriptions answer different questions. A band Hamiltonian determines which electronic degrees of freedom are represented. A Poisson solve determines the electrostatic potential from charges and boundary conditions. An 8-band envelope Hamiltonian can, in principle, be embedded in a self-consistent Schrödinger-Poisson workflow; specifying one does not imply the other.

Our **actual inspected decks** (`nextnano/inputs/kp8_dispersion.in` and `singleband_case04_graded.in`) request `no_density = yes` and `run{ quantum{} }`, not a self-consistent Poisson solve. The kp8 deck requests six electron and eight hole solutions. Python later selects only four Kramers-paired branches for the two-by-two Equation 2 state subspace.

More importantly, the current historical baseline is not even a pure eight-band matrix-element calculation:

```text
single-band raw k=0 energies -> four absolute energy anchors
single-band raw envelopes  -> O, z_e, z_h matrices held fixed at k=0
eight-band raw dispersion  -> selected E(k)-E(0) shifts
anchors + shifts          -> Equation 2 transition energies
```

`chi2/input_builder.py` implements that mixed-model construction. At k=0 the anchors reproduce the single-band states; away from k=0 the eight-band dispersion replaces a simple single-band dispersion while the matrices stay frozen. This is a **hybrid replacement/extension of the dispersion model**, not evidence of exact equivalence to the authors' original Schrödinger-Poisson calculation. Matching the same types of quantities (energies and matrix elements) is not enough to establish numerical or physical equivalence.

There is a further explicit mismatch: the historically selected second valence pair `[3,4]` is light-hole dominated, although its arrays inherit a heavy-hole label. The builder documents this instead of silently relabeling or correcting it. For this reason, 28A establishes historical computational reproduction, not successful validation of the paper's two-heavy-hole physical truncation. 28I examines the available state-character evidence. A corrected HH-only study would have to be a labeled model change with its own comparison.

## What remains unresolved after reading these sources

- The exact geometric domain and normalization meant by the authors' one-tenth-BZ cutoff, and their numerical saturation tolerance.
- Whether their envelope matrices were recomputed at every in-plane k, and the exact dispersion/state-tracking method and parameter set.
- The full electrostatic settings and whether any nontrivial charge-induced band bending entered the plotted theoretical structure.
- The definition of the simulated plotted observable in Figure 2d: agreement with an absolute real-part shape alone cannot establish that definition.
- The Fourier convention and full negative-frequency/counter-rotating completion accompanying Eq. 2. See `CAUSALITY_AUDIT.md`.
- Whether `N_z` counts one coupled pair per 30 nm or individual wells under the authors' normalization; our retained convention is `1/(30 nm)`.

These are explicit reproduction uncertainties. We did not adjust them to improve the paper fit. The precise value `r_e,hh=0.751 nm` is **not** on the unresolved list: its prior-publication source was found.
