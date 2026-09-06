# Independent physics review — Demo 26 home exhaustive audit

Reviewed 2026-09-06 in a separate agent reasoning pass. This is an independent computational physics critique, not an external human professor's certification. No nextnano solver was invoked and no production physics file was changed by this review.

## Verdict

**B. NEED FRIEND'S FILES BEFORE RUNNING PRO.**

The 176 numbered tests provide a substantial, useful audit of the requested families, but neither a paper reproduction nor literal exhaustion of all possible home analysis. The evidence supports postponing a new Professional campaign. The most immediate uncertainty is whether the colleague used the same states, matrices, energy anchoring and integration domain. The demonstrated complex-input bug must be corrected before production use with complex matrices, but it does not explain the current real-matrix baseline discrepancy. Thus A would be misleading if interpreted as finding the cause of the missing paper features; B is the best overall decision.

## Review basis and independent checks

I inspected the complete numbered-test collection and summary, the final report, all 31 added alternative-data rows (TEST 146–176), the existing-data inventory, literal-equation and units notes, raw-state-character CSV, cancellation table, direct-engine numerical evidence, and the actual implementations in `chi2_22.py`, `extended_implementation_audit.py`, `numerical_home_audit.py`, and `close_data_tests.py`. I checked the numerator conjugation algebra independently under general state phases and checked that the reported scalar alternative computations keep each case's energies and matrices together. I did not independently rerun every spectral calculation or re-render every paper page; the source-page transcription audit is supplied evidence, whereas the code algebra and interpretation here are independently examined.

The count is 176 variants/checks, not 176 independent scientific hypotheses: 52 lower-RMSE comparisons, 96 without improvement, 28 without a fit comparison; 25 PASS, 102 FAIL, 43 INCONCLUSIVE, 6 NOT TESTABLE. These two classifications overlap. Tiny numerical decreases and repeated controls do not represent distinct physical successes. FAIL in a fitting row means failure to establish reproduction, not a failed numerical implementation test. A tested variant's insufficiency does not exclude a contribution from its underlying hypothesis.

## Answers to the eleven requested questions

### 1. Have we exhausted the useful home-laptop tests?

**No, in the literal sense.** The declared numerical test families have broad coverage, including the previously overlooked 0.125 pi/a data, scalar abrupt alternatives, genuine independent denominators, continuous phases and pure-HH alternatives. No further cheap parameter sweep is presently compelled by these results. Useful home work remains: reconcile the multiband-to-scalar optical reduction, validate production complex-input behavior after a deliberate fix, and compare the friend's actual files. Existing k=0 multiband data may support more careful optical-operator work, but simply normalizing selected components is not that derivation. Do not turn a bounded audit into a theorem that all home physics is exhausted.

### 2. Which results are actually physically meaningful?

The strongest results are invariants, provenance facts and controlled numerical comparisons. TEST 117–120 independently support the real-input implementation: denominator error zero, pathway error about 4.69e-13 pm/V, final error about 8.76e-13 pm/V. This is shared-input algebra agreement, not independent model validation. TEST 122/124–126 verify the appropriate sign, continuous-phase, origin and real-numerator time-convention invariants in their stated scope. TEST 136 establishes that the retained hh2 pair is 97.5757% LH and 0% HH at k=0. TEST 138 establishes a geometry mismatch. TEST 66–72 use genuine separate dispersion grids/cutoffs and constrain ordinary quadrature sensitivity.

The cancellation table is also physically informative within the assumed model. The total is only about 2.8–4.9% of the sum of electron and signed-hole subtotal magnitudes at the six targets. At Z1 and Z2 the residuals are approximately 3.312+0.061i and -25.209-1.032i pm/V. Strong destructive interference is present, but it does not yield the paper's apparent minima at those wavelengths. Cancellation sensitivity makes internally consistent numerators particularly important.

### 3. Which improved fits are merely numerical fitting?

Absolute real (TEST 03, RMSE 0.237873), selected pathways (TEST 36, 0.221494), arbitrary global phase (TEST 127, approximately 0.2297), freely chosen global shifts/scales, and individual numerator perturbations are diagnostic fit changes. They do not identify a physical correction. Broadening and cutoff changes are physically interpretable only after their conventions are independently established; selecting them by lowest RMSE is still fitting. Projected branch matrices (TEST 74–76) are a method sensitivity study, not a validated multiband susceptibility.

Topology must accompany RMSE. Baseline TEST 01 has P2/P4 at 752/1503 nm but lacks interior P1/P3/Z1/Z2 in the declared target windows. It also has extra structure, including peaks near 688/1376 nm and a tiny 837 nm feature. Raw extrema counts include tiny shoulders; use prominence and wavelength ordering rather than treating every derivative sign change as an equally meaningful paper peak. Gamma=0 finiteness on a finite sampling grid does not establish a converged zero-linewidth continuum response.

### 4. What is most likely different in the friend's reproduction?

My first priority is the state/matrix/energy construction: pure HH versus LH-like selected bands, scalar versus spinor optical matrix definitions, and whether state-specific anchoring was applied. Next are actual interface grading, integration domain/BZ definition, and electrostatic conditions. This is a ranking of diagnostic priority, not quantified posterior probabilities. The friend's report of reproduction is not yet independently verified, and M(k)=M(0) does not specify what M(0) was.

### 5. Is abrupt-versus-graded now the leading cause?

**Not demonstrated.** It is a real discrepancy and a reasonable controlled future test, but matrix/state provenance is at least as concerning. TEST 146 gives scalar abrupt RMSE 0.279932 versus same-method graded 1 nm TEST 154 at 0.291360: abrupt helps that scalar comparison by about 3.9%, while both remain worse than hybrid baseline 0.262391 and lack P1/P3. The abrupt peaks at 759/1517 nm align P2/P4 well; they do not repair the missing topology. All scalar source records have physical_valid=False, so these are explicitly qualified diagnostics. This evidence neither proves nor rules out a larger effect in a consistent kp8 calculation.

### 6. Is BZ convention still important?

**Yes.** Constant radial prefactors cannot change normalized shape (TEST 45–47), but integration bounds can. Existing output reaches 0.125 pi/a; it does not cover the 0.20 pi/a candidate (TEST 133–134). A crystallographic direction, a circular radial domain and a fraction of BZ area are different definitions. The reported 45-degree result also means angular isotropy should remain an approximation under scrutiny. Do not extrapolate the available ray or equate convergence in point count with convergence in physical integration domain.

### 7. Are matrix provenance/state identity more concerning?

**Yes, as a model-consistency concern; not yet as a proved cause.** A nominal HH-only reduced expression paired with an almost purely LH second valence state requires justification. The frozen scalar matrices and statewise-anchored kp8 dispersions are not one raw self-contained multiband dataset. TEST 172 removing anchoring gives RMSE 0.287878, so unanchoring alone is not a fix. The physically motivated pure-HH alternatives TEST 173–176 give roughly 0.3099–0.3153 and still lack P1/P3. These negative results rule against the particular replacement recipe as a cure; they do not validate the original labels or the normalized-component reduction. Kramers branch averaging before evaluating a nonlinear matrix expression is not automatically the physical sum over degenerate states.

### 8. Is Schrodinger–Poisson a serious mismatch?

It is a serious unresolved setup discrepancy, with **unestablished spectral importance**. The recorded quantum-only/no-density deck does not establish the same self-consistent calculation as the paper. Zero doping does not by itself prove electrostatic equivalence; conversely the mere word Poisson does not prove a large field or band bending. The unusual reported charge output should not be treated as a validated physical carrier density without its conventions. Obtain boundary conditions, occupations and carrier assumptions first. A coarse different-geometry Poisson fixture cannot settle this question (TEST 140–141).

### 9. Is finite-k M(k) necessary for reproduction, or future physics?

**Necessity is not established.** It is useful future physics and could matter greatly for cancellation. The colleague's unverified M0 claim and unresolved input differences make a full Demo 25 campaign premature as a required reproduction step. No finite-k wavefunctions were found; energy-column continuity alone cannot certify eigenstate continuity or avoided-crossing identities (TEST 137/142). Do not manufacture M(k) from the energy dispersions.

### 10. What ONE thing from the friend resolves most uncertainty?

Request **the exact runnable reproduction package**: the nextnano input deck and the exact spectrum-generation script, with its selected raw output or precise output-file references and version/database identifiers. Treat this as one archived reproducibility package, not a screenshot. If only one individual file is immediately obtainable, the spectrum-generation script is the most revealing first item because it exposes state indices, matrix definitions, anchoring, k weights and plotted observable; it does not eliminate the need for the deck and data.

### 11. What is the smallest justified new Pro calculation?

**None is justified as the immediate next action before the file comparison.** If files remain unavailable and a controlled geometry discriminator is chosen, run only the abrupt counterpart of the existing graded structure: same nominal 7.1/1.8/2.9 nm structure, outer barriers, material database, temperature, k direction, 301 points and 0.10 pi/a, changing grading alone. Export full k=0 spinors, energies and appropriate optical operators, plus per-k character/overlap information needed to identify states. Reconcile the existing matrix reduction and energy convention before comparing chi. If the friend instead demonstrates a different cutoff or electrostatic setting, that specific controlled change takes priority. A 0.20 pi/a test, a Poisson change and a geometry change should not be bundled into one uninterpretable experiment.

## Implementation finding that must not be hidden

TEST 123 is a real production bug for advertised general complex inputs. With O[n,m]=<e_n|hh_m>, phase cancellation requires conj(O[n,m])*ze[n,l]*O[l,m] and O[n,m]*zh[m,l]*conj(O[n,l]). Production omits the conjugates; the independent engine includes them. The observed magnitude variation reaches about 4.518 pm/V under arbitrary state phases while the independent engine remains invariant within 4.59e-13 pm/V. Real sign flips cannot detect this error. Therefore answer 'Is there an obvious code bug?' with **YES — latent complex-input conjugation bug**, immediately adding **not a demonstrated cause of the frozen-real baseline mismatch**. Correct and regress it in a deliberate future production change before complex use; preserving historical outputs during this audit was appropriate.

## Acceptance and remaining limits

I accept decision B and the conclusion that no tested variant establishes a defensible full reproduction. I do not accept a claim that geometry is proved to be the principal cause, that low RMSE validates altered physics, that real-input agreement validates complex algebra, that all home analysis is exhausted, or that new Professional data are always necessary when the friend may already possess them.

The 2.296 eV inference remains weak as a unique missing-state diagnosis (TEST 129): extrema are not necessarily poles, the paper digitization is approximate, and interference can shift features. Tests based on sample spacing/interpolation quantify robustness, not experimental uncertainty. Absolute normalization and paper-version density notation remain outside a demonstrated normalized-shape reproduction.

The audit is reviewable and the previously missing independent review is now supplied. Its practical next step is provenance reconciliation with the colleague, followed by one controlled calculation only if the comparison identifies a missing eigenstate dataset. This review does not authorize or invoke that calculation.
