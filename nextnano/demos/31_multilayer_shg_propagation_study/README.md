# Demo 31 — multilayer SHG propagation (RESERVED PLACEHOLDER)

**Status:** scope reserved on 2026-09-24. **Nothing is implemented.** No solver, no
analysis, no results.

## Question

Once χ(2) and absorption are known, how do the real multilayer optical fields, phase
mismatch, standing waves and interfaces change the measured SHG?

## Why it exists (numbers from Demo 30)

Demo 30 treats the 80-period Fig. 2d sample (2.4 µm) as a uniform, phase-matched,
reflection-free absorbing slab (Almogy and Yariv 1994, Eq. 5).

| | Value at 1550 nm |
|---|---|
| SH intensity kept after absorption (Demo 30) | about 0.44–0.47 |
| Coherence length from background indices (not applied in Demo 30) | about 1.6 µm, versus 2.4 µm of sample |
| Suppression a transparent slab of that thickness would show from phase mismatch | about 0.10 |

Phase mismatch is therefore at least as large an effect as absorption for the 80-period
sample. Standing waves in the thin film on sapphire can also reshape the measured spectrum.
The 2026 paper's effective-χ(2) extraction (Methods 5.5, Eq. 3) already uses simulated
standing-wave fields. Demo 31 exists to model all of these consistently.

## Inputs expected from Demo 30 (copied into Demo 31 when it starts, never imported)

| Quantity | Demo 30 source |
|---|---|
| complex χ(1) of the MQW at ω and 2ω | `outputs/30C_chi1_absorption/chi1_spectra.csv` |
| absorption / complex index of the MQW layer | `outputs/30C_chi1_absorption/absorption.csv` plus `config/demo30.json` → `background_index` |
| complex χ(2)_xzx | `outputs/30B_chi2_baseline/chi2_results/chi2_spectrum.csv` |
| wavelength grid, validity windows | `config/demo30.json`, `outputs/summary.json` |
| measured Fig. 2d (80 periods + controls) | `reference/paper_fig2d_measured.csv` |
| homogeneous-slab limit to reproduce | Demo 30's A (1994 Eq. 5) = the reflection-free limit of Eq. 3 |

## Deferred physics (all intentionally excluded from Demo 30)

- wavelength-dependent refractive indices of every layer (GaAs, AlGaAs, cap, sapphire, epoxy);
- phase mismatch Δk(λ) (1994 Eq. 2b; β with Re χ(1));
- Fresnel coefficients at every interface;
- transfer-matrix fields and layer-by-layer standing waves at ω and 2ω;
- oblique incidence (45°), p polarization, E_x and E_z components, and the χ_xzx tensor geometry;
- SH contributions from bulk GaAs and AlGaAs, and their coherent interference with the MQW term;
- the full sample stack: sapphire, epoxy, cap, bulk AlGaAs layer, MQW;
- comparison with the paper's field-overlap extraction (Methods 5.5, Eq. 3), including its
  factor of 1/2 on the MQW term and its calibration constant (named "α" in the paper; it is
  not an absorption coefficient).

See `PLAN.md` for the draft structure. Demo 31 will follow `nextnano/docs/DEMO_WORKFLOW.md`:
self-contained, package `demo31`, copied inputs with provenance.
