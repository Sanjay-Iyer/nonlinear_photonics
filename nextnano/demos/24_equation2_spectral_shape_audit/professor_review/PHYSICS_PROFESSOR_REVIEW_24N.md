# Independent professor review of Demo 24N (causal sensitivity study)

This is a second, separate review covering only the Demo 24N causal-sensitivity results. It does
not replace `PHYSICS_PROFESSOR_REVIEW.md`, which reviewed the primary Demo 24 analysis before
24N existed. Where 24N contradicts that earlier review, both positions are left standing and the
disagreement is stated explicitly.

---

## Independent verdict

The causal study is sound in method and, in its central claim, correct. The reviewer's own
arithmetic reproduces the decisive numbers, and the single most important result is an
**exclusion**, which is a much stronger form of evidence than the sensitivity demonstrations that
surround it.

The central result is this. The digitized paper curve carries two peak pairs whose wavelengths
stand in exact 2:1 ratio: 540/1080 nm and 760/1520 nm. In a second-order susceptibility with
one-photon and two-photon denominators, a single transition energy `E` necessarily produces
features at both `hc/E` and `2hc/E`. Two exact 2:1 pairs is therefore the signature of exactly
two transition energies, `hc/540 = 2.296 eV` and `hc/760 = 1.631 eV`. Demo 23D contains the
second (its `DeltaE_22` is 1.648 eV) and reproduces its pair to 8 and 17 nm. It does not contain
anything near the first, and cannot: the largest `Ee - Ehh` available from any bound-subband pair
in this structure, evaluated where the electron subband reaches the Al(0.55)Ga(0.45)As
conduction-band edge at 3.3244 eV, is about 1.93-1.97 eV. That is 330-370 meV short.

I regard this as established, not merely suggested, for three reasons.

1. It does not depend on the perturbation machinery at all. It follows from the copied
   dispersion file and `bandedges.dat` by direct arithmetic.
2. The parabolic extrapolation that carries it - a 1.25x reach in k - was checked against the
   0.125 pi/a case that actually exists, and predicts those energies to 2-12 meV.
3. The error runs in the safe direction. Both electron bands *flatten* with k (`a` falls from
   0.517 to 0.500 for e1 and 0.446 to 0.434 for e2), which is ordinary 8-band non-parabolicity.
   A flattening band means the parabola *over*-estimates the transition energy at large k, so the
   true bound-state ceiling is lower than quoted and the gap to 2.296 eV is wider, not narrower.

The corollary matters as much as the result: no perturbation of the four subband energies, no
pathway amplitude or sign, no broadening, no k-grid density, no radial weighting and no
normalization can put a feature at 540 or 1080 nm. The measured `dLambda/dE` of order 1e-14
nm/meV for those features is not a small sensitivity; it is the arithmetic statement that the
model has no feature there to move. The primary analysis is right to report the quoted model
wavelengths for P1, Z1, P3 and Z2 as search-window edges rather than extrema.

## The cutoff-artifact result is the second solid finding

I did not expect this and I accept it. A peak that moves 1502 -> 1431 -> 1376 -> 1318 nm as the
integration limit moves, while tracking `2hc/DeltaE(kmax)` to a 9 nm mean error, is the edge of a
truncated sum and nothing else. That the two peaks matching the paper stay within 1 nm across all
four cutoffs is the necessary control, and it is present.

This has a consequence the earlier review did not draw, and it is the point on which I now
correct my own previous position. I previously recommended extending the k range as the single
most informative next calculation. Demo 24N shows that is not sufficient and is arguably
misleading on its own: with the numerator frozen at `M(k) = M(0)` there is nothing to damp the
high-k integrand, so a longer grid relocates the artifact rather than removing it. The physical
content of a converged calculation is that envelope overlaps fall away as the states delocalise;
freezing them guarantees a sharp spurious band edge wherever the sum is stopped. **Extend the k
range and supply `M(k)` together, or the result will be as hard to interpret as the present one.**

## Where I think the study overreaches

The amplitude scan is the weakest limb, and I would not let it stand as written without the
following qualification.

Scaling a *single* pathway numerator by 0.90 is not a model of what a real finite-k `M(k)` does.
The overlaps and dipole matrix elements are not independent knobs: `O_nm(k)`, `z_e,nl(k)` and
`z_hh,ml(k)` enter several of the sixteen pathways at once, and they are constrained by
orthonormality and by sum rules that a single-pathway rescaling violates. Because the electron
and heavy-hole subtotals here cancel to 4-5%, breaking that structure in one term is close to the
most efficient possible way to manufacture a residual - and therefore close to the least
representative. The honest reading of "a -10% scaling of `C_m1_n1_l1` opens a node at 573 nm with
normalized amplitude 0.0001" is: *the node is not far away in numerator space*. It is not: *a 10%
error in M(k) exists, and would produce this node*. A coherent, sum-rule-respecting `M(k)`
variation could easily need to be much larger, or could move the residual the other way.

The study's own limitation section says most of this, and the ranking does not lean on the
amplitude result for its top entry, so this is a qualification rather than an objection. But the
report should not let a reader come away thinking the node has been explained. It has been shown
to be reachable.

Two smaller cautions:

- The phase scan is correctly labelled as a robustness probe, and the module correctly reports
  that the numerator phase is pinned to 0 or pi by real matrix elements. I would go further and
  say the phase scan carries almost no diagnostic weight here, precisely because there is no free
  phase to be wrong about. It should not appear in any summary of causes.
- The 2:1 pair argument would be weak on one pair alone; eye-digitised extrema rounded to the
  nearest 5 nm will occasionally fall in a 2:1 ratio by chance. It is strong here because *both*
  pairs do, and because one of the two is independently confirmed by the model's own band edges
  at 752.2 and 1504.5 nm. That confirmation is what converts a numerical coincidence into a
  physical reading, and it should be stated that way.

## Answers to the eight Demo 24N questions

**1. Are the claimed causal relationships supported by the perturbation results?**
Yes for P2 and P4, and yes for the negative claims about P1, Z1, P3 and Z2. The `dLambda/dE`
values are unambiguous in both directions. The amplitude-to-node claim is supported as a
statement of reachability only, as discussed above.

**2. Is each peak truly associated with the identified transition and pathway?**
For P2 and P4, yes, and the identification is better than the study initially claimed. Both sit
on the `DeltaE_22` k=0 band edge - 752.2 nm one-photon and 1504.5 nm two-photon - to within 0.2
and 1.5 nm. The study's first-pass answer, which named the largest single pathway, was wrong in a
way worth recording: in an integrated spectrum the features live at *band edges*, where the
resonant k reaches the end of the range, not at the largest term. Inside a band every wavelength
is resonant at some k and the result is smooth. The correction is now applied, and it is what
makes the energy derivatives and the pathway identification agree.

**3. Are the left/right peak shifts consistent with the identified transition-energy error?**
Yes, and the internal consistency check is the convincing part. `dLambda/dE` is -0.46 nm/meV for
P2 and -0.92 nm/meV for P4 against e2, an exact factor of two. That is required if the two
features are the one-photon and two-photon edge of the same transition, and it is not something
a bookkeeping error would reproduce. Both close on the paper with the same -17 to -18 meV shift.
A 17 meV discrepancy in a computed subband separation is well inside what band parameters,
interface grading and temperature convention can account for, and I would not treat it as a fault.

**4. Are the 605 and 1330 nm nodes truly cancellation-controlled?**
In the model, unambiguously: the electron and signed heavy-hole subtotals are antiphase to within
0.1 degree and cancel to 4.3% and 4.9%, giving a 21-24x amplification of any numerator error. In
the *paper*, this is an inference, not a measurement. The paper plots a non-negative magnitude,
so a visually zero point is consistent with a sign change but does not prove one. The study is
careful about this distinction elsewhere and should stay careful here.

**5. Is any perturbation being overinterpreted?**
The single-pathway amplitude scan, as set out above. Nothing else. The reachability and
cutoff-artifact results are exclusions and are not vulnerable to this criticism.

**6. Which result most strongly identifies the actual missing physics?**
The reachability exclusion, by a wide margin. It is the only result that rules out an entire
class of explanations rather than demonstrating that one explanation is possible. Second is the
cutoff-artifact test, which invalidates the model's own structure in the 1250-1450 nm window and
therefore removes the apparent "Z2 disagreement" as a thing needing explanation - one cannot
meaningfully compare a truncation edge with a physical node.

**7. Does the sensitivity study reduce or increase the need for a new Professional run?**
It increases the *specificity* and reduces the *scope*. Before 24N, four hypotheses were live and
a rerun would have been exploratory. Now the rerun has one primary job - deliver `M(k)` over an
extended k range - and one secondary job - reveal whether any state in this structure carries
oscillator strength near 2.296 eV. That is a single deck, not a campaign. I endorse category B.

**8. If a Pro rerun is needed, which missing quantity is now specifically implicated?**
Complex `O_nm(k)`, `z_e,nl(k)` and `z_hh,ml(k)` versus k, with per-k spinor composition for state
tracking, on a grid reaching about 0.20 pi/a. I would add one requirement the study lists but
does not emphasise enough: **retain and report more states than the four, with their oscillator
strengths.** If nothing in the extended solve reaches 2.296 eV, the conclusion is not about
matrix elements at all - it is that the compared curve is not this structure, and the question
becomes a geometry question. That branch should be decided by the same run, not by a later one.

## Independent top five

1. **Model-space truncation - the 2.296 eV transition is absent** (high confidence). Excluded
   everything else for four of six features.
2. **Frozen `M(k)` combined with a hard k cutoff** (high confidence for the artifact, moderate
   for the nodes). Jointly responsible for the spurious 1250-1450 nm structure; plausibly
   responsible for the missing nodes, not demonstrated.
3. **Structure mismatch between the paper's Fig. 2d and the Demo 23 stack** (moderate). A
   structure with a second dominant transition at 2.296 eV, 151 meV above this barrier's 2.145 eV
   gap, is not obviously the same structure.
4. **A small coherent subband-energy offset, about 17 meV in `DeltaE_22`** (moderate, and benign).
   Explains the entire residual on the two features that do match.
5. **HH/LH assignment of the `hh2` pair** (low as an explanation, though the observation is real).

On the fifth point I record a direct disagreement with the first-pass primary analysis, which
ranked it first at 0.98. The 24N derivatives settle it: moving `hh2` to the pure-HH pair lowers
its energy by 19 meV, and with `dLambda/dE_hh2` of +0.46 and +0.92 nm/meV that drives P2 and P4
*away* from the paper, which the state-corrected scorecard confirms. The k=0 spinor observation
stands on its own merits and should be resolved in the rerun; it is not the explanation for the
shape mismatch.

## Pro rerun required

**YES - category B, one targeted deck**, with the extended k range and finite-k matrices in the
same calculation rather than in sequence, and with extra states retained.

## Confidence

**High (0.90) in the exclusion**: the paper's P1/P3 pair cannot be produced by this four-state
bound model in this structure, and no parameter in the present calculation can create it.

**High (0.88) in the cutoff-artifact identification**, given the 9 nm tracking of
`2hc/DeltaE(kmax)` across four cutoffs and the stationary controls.

**Moderate (0.55) that finite-k `M(k)` is what opens the paper's nodes.** Reachable is not
demonstrated, and the single-pathway scan overstates the ease.

**Moderate (0.50) on whether the remaining discrepancy is a matrix-element problem or a structure
problem.** The same rerun distinguishes them, which is why it is worth doing.
