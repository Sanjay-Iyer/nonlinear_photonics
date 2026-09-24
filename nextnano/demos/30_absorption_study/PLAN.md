# Demo 30 — approved plan

Approved 2026-09-24. The review discussion is summarized here; the change log is at the
bottom.

## Question

Does linear absorption of the fundamental (ω) and of the second harmonic (2ω) change the
predicted wavelength dependence of SHG from the 2026 coupled-quantum-well sample? Does it
move the prediction toward the measured Fig. 2d response, and by how much?

## Physics chain

```text
existing raw quantum-mechanical data (D020 single-band, D023 8-band dispersion)
      |                                   |
Eq. 2 chi2 (copied, unchanged)      new chi1 from the same inputs
      |                                   |
      |                          alpha(omega), alpha(2 omega)
      |                                   |
      +------------ 1994 Eq. 5 propagation over L = N x 30 nm
                              |
                  predicted SH intensity (NOT chi2)
```

- Γ stays the microscopic linewidth, used identically in χ(1) and χ(2).
- Propagation absorption appears only in the Maxwell/propagation step.
- Eq. 2 gets no absorption term.
- Im χ(2) is not reinterpreted as absorption.
- Nothing is fitted to Fig. 2d.

## Decisions

1. **k cutoff.**
   - The control is **k_max = 0.1·π/a** (0.5557 nm⁻¹, a = 0.565325 nm), exactly Demo 28A.
   - An optional extended comparison is **0.2·π/a**, only if the data exist. It is an
     extension, not a new baseline.
   - Always write the multiple of π/a, never "0.1 BZ".
2. **Absorption k tail.** Both are computed and compared:
   - `strict`: only stored k states through 0.1·π/a;
   - `tail`: the same numerical result plus an analytical continuation of Im χ(1) beyond
     the stored cutoff, clearly labeled.

   χ(2) is never extended.
3. **States.**
   - `consistent_2x2`: 2 conduction × 2 heavy-hole states, as in the χ(2) model. This is
     the primary result.
   - `expanded_bound_states`: a sensitivity comparison that adds the other bound states
     saved in the D020 single-band run. It is **not** an upper bound, because it still
     omits light holes, the continuum, k-dependent matrix elements and full 8-band optics.
4. **Raw data never go to Git.**
   - Raw data live in the local `nextnano_raw/`.
   - The demo pins them in `inputs/raw_data.lock.json` and verifies hashes.
   - The historical copies stay where they are.
   - The failed 28K run is left untouched and unregistered.
5. **Scope.** Demo 30 is absorption only. It may report a coherence-length /
   phase-mismatch estimate as a limitation. The following all belong to Demo 31
   (`31_multilayer_shg_propagation_study`), which is reserved as a placeholder:
   - transfer matrices, standing waves, Fresnel coefficients;
   - wavelength-dependent phase matching;
   - cap / barrier / sapphire propagation;
   - bulk GaAs/AlGaAs SH.
6. **Guidance.** The canonical workflow is `nextnano/docs/DEMO_WORKFLOW.md`. `AGENTS.md`,
   `CLAUDE.md` and the Claude skill point to it.
7. **The 1994 paper** is cited in `SOURCES.md` and never committed by this demo.

## Sub-studies

| ID | Content | Output folder |
|---|---|---|
| 30A | inputs: lock verification, copied references, measured Fig. 2d digitization | `outputs/30A_inputs/` |
| 30B | control: Demo 28A χ(2) reproduced from the registered raw data; χ(2) vs the paper simulation (comparison A) | `outputs/30B_chi2_baseline/` |
| 30C | χ(1) and α_E, α_I at ω and 2ω; strict vs tail; consistent_2x2 vs expanded_bound_states; validity checks | `outputs/30C_chi1_absorption/` |
| 30D | 1994 Eq. 5 absorption factor for 80 periods (main), plus 4/12/16 at selected wavelengths; coherence-length estimate | `outputs/30D_propagation/` |
| 30E | transparent vs absorption-aware SH intensity vs measured Fig. 2d (comparison B); peak table; shape metrics | `outputs/30E_paper_comparison/` |
| 30F | optional k extension: what existing data reach; prepared WORK-laptop package for 0.2·π/a | `outputs/30F_k_extension/`, `work_laptop/` |

## Required comparisons

- CONTROL: χ(2) at 0.1·π/a, no propagation absorption.
- ABSORPTION: consistent_2x2, strict 0.1·π/a cutoff.
- ABSORPTION + TAIL: consistent_2x2, analytical high-k continuation.
- STATE SENSITIVITY: expanded_bound_states (strict and tail).
- OPTIONAL k COMPARISON: 0.2·π/a, only once real raw data exist.

## Validation (focused)

1. The baseline reproduces Demo 28A.
2. The copied `equation2.py` is unchanged.
3. Raw-data lock verification.
4. χ(1) matches a known analytic case.
5. Passive absorption is positive for both sign conventions.
6. Field vs intensity convention (α_I = 2α_E).
7. α → 0 gives the transparent limit.
8. α_2ω → 2α_ω is numerically stable.
9. The closed form agrees with numerical integration.
10. Resonance positions are sensible.
11. The strict vs tail difference is quantified.
12. The 2×2 vs expanded difference is quantified.
13. The isolation audit passes.
14. A deterministic rerun reproduces the outputs.

## Change log

- 2026-09-24: plan approved; implementation started (Phases 0, A–H).
- 2026-09-24, during implementation:
  - **Comparison window.** It gained a data-driven strict-cutoff trust limit (SH 3Γ below
    the lowest truncated 2×2 edge; 1492.7 nm). Without it, the strict variant's
    truncation artifact below about 1480 nm dominated its normalization. The measured
    points used are unchanged.
  - **Onset check.** The resonance-position check uses the dIm/dE peak, not the half
    height, because the tracked e2–hh2 dispersion is flat near k = 0.
  - **Traced simulated curve.** The paper's simulated curve was also traced at high
    resolution, for peak positions. The 45-point eye file stays the comparison-A
    reference, so Demo 28J can be reproduced.
  - **0.125·π/a extension.** The existing 0.125·π/a Demo 23 run was registered as an
    optional 30F extension and as a real-data check of the analytical tail.
  - **0.2·π/a.** A clean WORK package was prepared. Route A (registering the existing 28K
    dispersion, which matches the control to 3×10⁻¹¹ eV) awaits a decision.
