# Demo 30 sources

Papers are cited here, not copied into the demo. Local PDFs at the repository root are
listed for convenience only. **The 1994 paper must not be committed by this demo.**

## 1. Ramesh et al. 2026 — the paper being reproduced

R. Ramesh, M. Brown, A. Ricks, …, J. B. Khurgin, S. R. Bank, *Enhanced Interband Optical
Nonlinearities from Coupled Quantum Wells*, arXiv:2602.23246v1 [physics.optics]
(26 Feb 2026). Local copy: `2602.23246v1.pdf`.

| Where | What Demo 30 uses |
|---|---|
| Eq. 2 (Methods 5.1, p. 11) | χ(2)_xzx with (ω − … + iΓ) denominators, N_z, r_e,hh, first two conduction and heavy-hole states, Γ = 5 meV. Implemented unchanged in `demo30/equation2.py`. |
| Methods 5.1 (p. 11) | "summed to one-tenth of the Brillouin zone". Demo 28 and Demo 30 use 0.1·π/a (see PLAN.md, decision 1). |
| Fig. 1 caption (p. 5) | 30 nm period: 7.1 nm and 2.9 nm GaAs wells, 1.8 nm tunnel barrier, 18.2 nm period barrier, Al0.55Ga0.45As. |
| Section 2.2 text (p. 5–6) | "Each period is 20 nm (10 nm total QW thickness, 1.8 nm barrier, and 18.2 nm period barrier)". The layers add to 30 nm, so 30 nm is used. |
| Section 2.2 (p. 6) and Fig. 2d (p. 7) | Wavelength dependence measured on the **80-period** sample, 1400–1800 nm fundamental. Measured peak ≈ 1560 nm, simulated ≈ 1520 nm. Left axis "Simulated \|χ(2)\| (pm/V)"; right axis "Normalized SH Intensity (arb. u.)". |
| Section 2.3 and Fig. 3c (p. 6–9) | Effective χ(2) at 1550 nm: ≈ 1170 pm/V (12 and 16 periods), 1730 pm/V (80), 2750 pm/V (4). Samples are transferred to sapphire; SH is measured in transmission at 45° incidence. |
| Methods 5.5, Eq. 3 (p. 13–14) | Effective χ(2) from reciprocity-weighted field overlaps, SH ∝ \|Σ χ ∫ E(2ω)(E(ω))² dv\|², with standing waves included. Its symbol **α is a fitted calibration constant, not absorption**; Demo 30 never uses that name for it. The full field treatment is Demo 31. |
| Conclusion (p. 10) | Names "low linear loss, α(2ω)" as a design target. |

## 2. Ramesh et al. 2023 — the precursor paper (reference [38] of the 2026 paper)

R. Ramesh, T. Hsieh, A. M. Skipper, Q. Meng, K. C. Wen, F. Shafiei, M. A. Wistey,
M. C. Downer, J. B. Khurgin, S. R. Bank, *Interband second-order nonlinear optical
susceptibility of asymmetric coupled quantum wells*, Appl. Phys. Lett. **123**, 251111
(2023). Local copy: `Interband second-order nonlinear optical susceptibility of asymmetric
coupled quantum wells.pdf`.

What Demo 30 uses:

- **r_e,hh.** r_e,hh = 7.51 Å from DFT (HSE06).
- **Linewidth.** Γ = 5 meV.
- **k range.** The 0.1-Brillouin-zone limit is described as allowing the effective-mass
  approximation.
- **Detuning.** That paper chose the SH photon energy 75 meV below the e1–hh1 transition
  to avoid absorbing the second harmonic, and noted that the resonant SH energy lies above
  the gap. The 2026 Fig. 2d resonance lies above that edge, which motivates Demo 30.

## 3. Almogy and Yariv 1994 — absorptive propagation

G. Almogy and A. Yariv, *Second-harmonic generation in absorptive media*, Optics Letters
**19**(22), 1828–1830 (1994). Local copies `ol-19-22-1828.pdf` and
`ol-19-22-1828 (1).pdf` are identical. **Not to be committed by this demo.**

| Equation (page) | Content | Demo 30 use |
|---|---|---|
| 1a, 1b (p. 1828) | resonant χ(1) at ω and 2ω, ∝ 1/(Δω − i) | template for the resonant χ(1); the 1994 paper uses the opposite time convention to Eq. 2 (see §5) |
| 1c (p. 1828) | three-level χ(2) | **not used.** Demo 30 keeps the 2026 Eq. 2. |
| 2a (p. 1828) | α_ω ≡ (ω/2nc) Im χ(1)(ω,ω) | the absorption coefficient; applied at ω and at 2ω |
| 2b (p. 1828) | phase-mismatch coefficient β_2ω | coherence-length estimate only; not applied |
| 3a, 3b (p. 1828) | dE_2ω/dz = −(α_2ω + iβ_2ω)E_2ω − i(ω/nc)χ(2)E_ω²; dE_ω/dz = −α_ω E_ω − … | shows α is a **field** coefficient: α_I = 2α_E |
| 5 (p. 1829) | E_2ω(z) = −i(ω/nc)χ(2)·[e^(−2α_ω z) − e^(−α_2ω z)]/(α_2ω − 2α_ω)·E_ω(0)², assuming phase matching and no depletion | the propagation factor A (`demo30/propagation.py`) |
| 6a, 6b, 7 (p. 1829) | optimum length and maximum efficiency | not needed. The PDF text layer of Eq. 7 shows Re[χ(1)] where Eq. 2a implies Im; Demo 30 does not depend on it. |

## 4. Refractive-index data (background index only)

Read from the refractiveindex.info database (github.com/polyanskiy/refractiveindex.info-database)
on 2026-09-24. Values and interpolations are in `config/demo30.json` → `background_index`.

- T. Skauli et al., J. Appl. Phys. **94**, 6447 (2003): GaAs Sellmeier, 0.97–17 µm.
- D. E. Aspnes, S. M. Kelso, R. A. Logan, R. Bhat, J. Appl. Phys. **60**, 754 (1986):
  GaAs and AlxGa1−xAs (x = 0.491, 0.590) n,k tables.
- R. E. Fern and A. Onton, J. Appl. Phys. **42**, 3499 (1971): AlAs Sellmeier, 0.56–2.2 µm.

## 5. Sign convention (how the two papers are combined)

- **2026 Eq. 2 uses +iΓ.** Its denominators are (ω_nm − ω + iΓ), which corresponds to
  e^(+iωt) fields (Demo 28's causality audit, 28F). In that convention a passive medium
  has Im χ(1) < 0.
- **1994 Eq. 1a uses 1/(Δω − i).** That is the e^(−iωt) convention, in which a passive
  medium has Im χ(1) > 0.
- **Demo 30 keeps Eq. 2's convention** (`gamma_sign = +1`) for χ(1) as well. It computes
  α = (ω/2nc)·(−gamma_sign)·Im χ(1), which is positive for a passive medium in either
  convention. `tests/test_absorption_conventions.py` checks both signs.
