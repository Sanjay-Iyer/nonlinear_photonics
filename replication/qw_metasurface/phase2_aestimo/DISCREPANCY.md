# Phase 2 DISCREPANCY — Al-fraction calibration target and HH2 localization

**Status:** Phase 2 gate cannot be passed as literally written. Two coupled issues,
one recommended resolution. Raised per the plan's "stop and ask" rule.

---

## Issue A — E(HH2→CB2) = 1.58 eV is unreachable in the physical x range, and
## forcing it destroys the χ⁽²⁾ asymmetry

The aestimo solver reproduces the frozen `acqw_solver_consensus_v1` benchmark
almost exactly (validation of the machinery):

| Quantity | This run (x=0.55, abrupt) | Frozen consensus (Aestimo) |
|----------|--------------------------:|---------------------------:|
| E11 (HH1→CB1) | 1.4960 eV | 1.4955 eV |
| E22 (HH2→CB2) | 1.6571 eV | 1.6557 eV |

Calibration scan of E22 vs barrier Al fraction (ideal/abrupt structure):

| x | 0.30 | 0.35 | 0.40 | 0.45 | 0.50 | 0.55 | 0.60 |
|---|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| E22 (eV) | 1.5975 | 1.6117 | 1.6247 | 1.6365 | 1.6473 | 1.6571 | 1.6661 |
| Δz(HH2,CB2) (nm) | −0.059 | +0.074 | +0.214 | +0.372 | +0.567 | +0.828 | — |

Two facts:
1. **1.58 eV is below the entire achievable range** (min 1.5975 eV at x=0.30). To
   reach it, x must drop below 0.30 — a shallower barrier than any GaAs/AlGaAs
   design in the source papers.
2. **The centroid offset Δz(HH2,CB2) — the dipole-like asymmetry that *is* the
   χ⁽²⁾ driver (Ref38 Eq. 4: χ_xzx ∝ ⟨e2|x|hh2⟩⟨hh2|z|hh2⟩⟨hh2|x|e2⟩) — collapses
   toward zero exactly where the 1.58 eV target lives** (Δz ≈ 0 at x≈0.30). It
   grows monotonically with x. So calibrating x downward to hit 1.58 eV would
   yield a structure with almost no second-order nonlinearity, contradicting the
   paper's central result.

### Root cause: the 1.58 eV target conflates two different resonances
- **Material χ⁽²⁾ resonance** (Fig. 2e): the plan itself states the peak is near
  **~1500 nm pump**. 1500 nm pump → SH 750 nm → **1.653 eV** SH photon energy,
  which is resonant with **E22 = 1.657 eV at x = 0.55**. Ref38 (same structure)
  independently reports its χ⁽²⁾ peak at ~1520 nm and E22 ≈ 1.62 eV.
- **Metasurface GMR operating wavelength** (Fig. 3, Phase 5): the device is
  *operated* at **1.58 µm pump**, on the shoulder of the material resonance,
  where the measured χ⁽²⁾_eff = 1.6 nm/V. SH there is 785 nm = 1.579 eV.

The plan's Phase 1/2 instruction ("calibrate so HH2→CB2 lands at ~1.58 eV,
resonance near 785 nm SH / 1.57 µm pump") used the **GMR operating** energy as
the **material calibration** target. These are ~75 meV apart. Ref38 fixes the
material's Al fraction at **x = 0.55** for this exact 18.2/7.1/1.8/2.9 nm stack.

### Recommended resolution
Adopt **x = 0.55** (Ref38's documented value), and reinterpret the calibration
target as **reproducing the Fig. 2e χ⁽²⁾ peak position (~1500 nm pump, E22 ≈
1.65 eV)** rather than the literal 1.58 eV. This:
- matches the independently-documented growth composition (Ref38),
- reproduces the frozen solver consensus (E22 = 1.657 eV),
- preserves the physical Δz asymmetry that drives χ⁽²⁾ (0.83 nm),
- and — verified in Phase 4 — places the χ⁽²⁾ spectral peak at ~1500 nm, matching
  Fig. 2e, with the 1.57 µm operating point on the resonance shoulder.

The literal 1.58 eV gate is treated as **not met (E22=1.657 eV, +77 meV)** with the
above documented physical justification, rather than forced by an unphysical x.

---

## Issue B — Energy-ordered HH2 is narrow-localized, not wide as Fig. 2a depicts

The paper's Fig. 2a states HH2 is confined in the **wider** well. The solver (and
the three-solver consensus: aestimo 3×3, single-band BDD, kdotpy 8-band) find the
**energy-ordered** HH2 is **narrow**-dominated at every x in [0.30, 0.55]:

| x | HH1 wide% | HH2 wide% | HH2 narrow% | CB2 narrow% |
|---|----------:|----------:|------------:|------------:|
| 0.30 | 97 | 15 | 70 | 60 |
| 0.55 | 99 | 19 | 73 | 76 |

CB2-narrow and HH1-wide **match** the paper; HH2 does not.

This is the pre-existing, extensively-audited finding in
`git/aestimo/paper/reference_data/acqw_solver_consensus_v1/docs/ROOT_CAUSE_REPORT.md`.
Its conclusions (unchanged here):
- The wide-localized HH branch exists but is **energy-ordered HH3** at baseline,
  a few meV above the narrow HH2; the two exchange labels through an
  HH2/HH3 anticrossing as VBO / HH mass vary.
- The companion paper's Fig. 1c shows **signed, scaled amplitudes**, not
  normalized probability densities, so a visual "HH2 in the wide well" there is
  not a localization measurement.
- The **operative χ⁽²⁾ quantity is the centroid offset**, which is large and
  correctly signed at x=0.55 (0.83 nm) regardless of the wide/narrow label.

Phase 2 therefore reports **both** the energy-ordered assignment (used for the
gate) and the branch/well-character view, and does not silently substitute HH3
for HH2 in the Phase 4 χ⁽²⁾ pipeline.

---

## Question for the user
Proceed with **x = 0.55** and the Fig-2e-peak calibration interpretation
(recommended), or hold for a different instruction? See the AskUserQuestion prompt.
