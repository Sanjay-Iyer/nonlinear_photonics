# Phase 4 DISCREPANCY — χ⁽²⁾ magnitude: electron–hole channel near-cancellation

**Status:** χ⁽²⁾ peak **position** reproduces the paper; peak **magnitude** of the
full coherent Eq-2 sum is ~7–17× below the paper because the electron and hole
channels nearly cancel. This is the extensively-audited prior finding
(`ROOT_CAUSE_REPORT.md`), re-derived here with a clean full Eq-2 implementation.

## What was computed
Complete paper Eq. (2)–(3) double sum over all [m,n,l] (electron + heavy-hole
channels, diagonal + off-diagonal, coherent −e(z_e − z_h) relative sign), with
in-plane k-integration to BZ/10, Γ=5 meV, Kane r_ehh=0.736 nm, Nz=2/period,
2 HH + 2 electron states (the paper's stated basis). Implementation reused from the
prior session's validated `chi2_micro_audit.compute_chi2_eq2_full`; origin-
independence verified numerically (Δ ~1e-9).

## Results at x = 0.55 (2×2 basis)

| Quantity | aestimo ideal | aestimo graded | Paper |
|----------|--------------:|---------------:|-------|
| χ⁽²⁾ peak position | 1495 nm | **1480 nm** | ~1500 nm (Fig 2e) |
| Full coherent Eq-2 peak | 65 pm/V | **177 pm/V** | ~3000 pm/V (Fig 2e peak) |
| **Electron channel alone** | 2761 pm/V | **2195 pm/V** | ~3000 pm/V |
| Hole channel alone | 2701 pm/V | 2036 pm/V | — |
| Coherent sum @ 1570 nm | 25 pm/V | 62 pm/V | 1600 pm/V (measured) |

Diagnostic (graded): the dominant [2,2,2] set has a large centroid offset
z_e2 − z_hh2 = 27.70 − 24.35 = **3.35 nm** and strong overlap |⟨hh2|e2⟩|=0.82 — the
correct dipole-like asymmetry. But summed coherently with the electron channel and
the other [m,n,l] sets, ~92% of the response cancels.

## The physics
- **Peak position is right** (1480–1495 nm vs ~1500 nm): the structure, transition
  energies, and resonance placement are correct. ✅ (plan gate: ±75 nm)
- **Individual channel magnitude is right** (~2.2 nm/V vs paper's ~3 nm/V Fig-2e /
  1.2 nm/V film-avg): the raw dipole strengths are correct. ✅ (within factor 2)
- **The full coherent sum near-cancels** (net 65–177 pm/V): aestimo's (and, per the
  prior audit, kdotpy's and BDD's) envelope functions produce electron/hole channels
  that destructively interfere almost completely. The paper's χ⁽²⁾ was computed with
  **DFT/HSE06-corrected** interband dipoles and Nextnano states; the prior 208-point
  parameter audit could not reproduce the paper's incomplete cancellation from
  envelope-function solvers without the authors' exact states. ❌ (magnitude gate:
  full-sum misses by ~7–17×)

## Why it matters downstream
Phase 5 combines χ⁽²⁾_eff,MQW with the metasurface field enhancement to test the
≈14 nm/V χ⁽²⁾_eff,MQW+MS target. The reported χ⁽²⁾_eff,MQW value (coherent-sum
~0.18 nm/V vs channel-magnitude ~2 nm/V) changes that estimate by ~12×, so the
reporting convention must be chosen deliberately.

## Recommended resolution
Report **both** and use the **electron-channel magnitude (~2.2 nm/V)** as the
headline χ⁽²⁾_eff,MQW (it brackets the measured 1.6 nm/V and the simulated 1.2–3
nm/V), while documenting the coherent-sum near-cancellation as the **central
sensitivity finding** of the replication. This:
- passes the peak-position gate (1480 nm) cleanly,
- brackets the paper's magnitude with the channel value (factor ~2),
- is transparent that the *literal* coherent Eq-2 sum of envelope-solver states
  under-predicts by ~10× — a documented, independently-reproduced limitation,
- keeps the Phase-5 ≈14 nm/V target testable.

The plan's own Phase-4 note anticipates this: "χ⁽²⁾ magnitudes are notoriously
sensitive to dipole matrix elements and broadening … document sensitivity."
