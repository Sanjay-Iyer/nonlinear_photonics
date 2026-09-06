# Independent physics review prompt - Demo 25

Act as an independent professor of semiconductor quantum wells, 8-band k.p theory, nonlinear
optics, second-harmonic generation and optical matrix elements. Do not defer to the primary
analysis. This review runs **after** the Demo 25 production run and analysis have completed; it
must not be written from the plan alone.

## Evidence to read

From `outputs/`:

- `PILOT_FINITE_K_OUTPUT_AUDIT.md`, `PILOT_VARIANT_SUMMARY.csv`, `PILOT_GATE.json`
- `PROFESSIONAL_RUN_MANIFEST.csv`
- `STATE_TRACKING.csv`, `TRACKING_EVENTS.csv`, `EXTENDED_STATE_ENERGIES.csv`
- `EXTENDED_TRANSITION_SEARCH.csv`, `P1_P3_RESONANCE_CANDIDATES.md`, `P1_P3_VERDICT.json`
- `FINITE_K_OVERLAPS.csv`, `FINITE_K_ELECTRON_Z.csv`, `FINITE_K_HOLE_Z.csv`
- `FINITE_K_PATHWAY_NUMERATORS.csv`
- `DEMO25_FEATURE_SCORECARD.csv`, `DEMO25_SPECTRUM_SUMMARY.json`
- `figures/figure01` through `figure16`

Carry forward the Demo 24 conclusions in
`../24_equation2_spectral_shape_audit/outputs/DEMO24_FINAL_REPORT.md` and both Demo 24 professor
reviews, and say explicitly where Demo 25's data confirms or overturns them.

## Questions to answer independently

1. Is the finite-k matrix-element reconstruction physically valid?
2. Is the kp8 spinor treatment correct? In particular: is summing the inner product over all
   eight components the right operation, and is restricting it to CB-dominated and HH-dominated
   states a defensible bridge to the paper's one-band Equation 2, given the reported purities?
3. Are the state assignments defensible? Check the tracking scores, assignment margins and every
   flagged character change and avoided crossing.
4. Is any ~2.296 eV candidate physically meaningful, or is it a Dirichlet box state of the
   quantum region?
5. Can it explain P1/P3?
6. Does finite-k M(k) plausibly explain Z1/Z2?
7. Is HH/LH mixing important here?
8. Is a geometry mismatch now the leading remaining explanation?
9. What is the next minimum calculation required?

## Specific things to be sceptical about

- **Interpolated M(k).** If the production run used a coarser matrix grid than the energy grid,
  judge whether the interpolation is safe over the k range where the pathway numerators actually
  vary, and whether anything sharp was smoothed away.
- **Unbound states.** Any state above the barrier conduction edge or below the barrier valence
  edge is box-quantized by the Dirichlet walls at the quantum-region boundary. Its energy is a
  function of the region width. Say plainly whether any conclusion leans on such a state.
- **Optical relevance.** Confirm the overlap and oscillator-strength thresholds are not doing
  hidden work, and that no candidate is accepted on an energy match alone.
- **Sign changes.** A pathway numerator that changes sign across k is the single most consequential
  finding for the Z1/Z2 cancellation, because the electron and heavy-hole subtotals are antiphase
  to within 0.1 degree and cancel to about 4-5%. Check whether any reported sign change is real or
  an artifact of dividing by a numerator that is near zero at k=0.
- **Scope.** Demo 25 changed only the k block, the state count and the per-k outputs. Confirm from
  `PROFESSIONAL_RUN_MANIFEST.csv` and the deck that no geometry, mesh, material or temperature
  drifted, and that the M(k)=M(0) control differs from the finite-k result in exactly one input.

## Output

Write `PHYSICS_PROFESSOR_REVIEW_DEMO25.md` containing an independent verdict, explicit agreement
or disagreement with the primary Demo 25 analysis and with Demo 24, a ranked list of remaining
causes, the specific next calculation, whether Demo 26 is required and exactly why, and a
confidence level for each major claim. Do not merge this into the primary report; both
perspectives stay visible.
