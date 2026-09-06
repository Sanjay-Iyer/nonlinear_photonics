# Independent professor review of Demo 24

## Independent verdict

Demo 23D is not yet a faithful test of the Ramesh et al. Figure 2d calculation. The most likely reason for the missing spectral topology is not the global normalization, broadening, or the density of the radial grid. It is the **in-plane cutoff convention**. Demo 23 calls (0.1\pi/a=0.5557\ \mathrm{nm^{-1}}) "0.1 BZ," whereas for zincblende GaAs along an in-plane \(\langle100\rangle\) direction the crystallographic \(\Gamma\)-to-X distance is (2\pi/a). The paper's stated cutoff of one tenth of the Brillouin zone therefore naturally corresponds to (0.2\pi/a=1.1114\ \mathrm{nm^{-1}}), twice the production range.

This is not merely a prefactor issue. The cutoff changes the *locations and number* of resonant features. At (0.125\pi/a), Demo 24 already develops a paired 659/1318-nm feature. The missing paper peaks are an exact one-/two-photon pair at approximately 540/1080 nm. From the Demo 23B fitted transition,

\[
\Delta E_{22}(k) \simeq 1.648231 + 0.503038 k^2\quad\text{eV},
\]

the condition \(\Delta E_{22}=2hc/(1080\ \mathrm{nm})=2.296004\ \mathrm{eV}\) occurs at

\[
k=1.13478\ \mathrm{nm^{-1}}=0.20420\pi/a=0.10210(2\pi/a).
\]

The same transition then has its one-photon resonance at 540 nm and two-photon resonance at 1080 nm. This numerical coincidence is too specific to ignore and elevates the BZ-edge/cutoff convention above all other hypotheses. It also explains why the existing (0.05\)-(0.125\pi/a) sweep cannot settle the paper comparison: its largest case reaches only (0.0625\) of the physical \(\Gamma\)-X distance.

There is a second, independent validity problem. The selected Demo 23 `hh2` pair 3+4 is 97.6% LH at (k=0), while pair 1+2 is 100% HH. Moreover, Demo 23D uses the *shape* of the 8-band dispersions but shifts every branch to the earlier Demo 19 single-band (k=0) energies and retains the earlier real (M(0)) matrices. Thus the LH-like denominator branch is combined with a matrix set intended for two HH states. The pair-1+2 diagnostic does not repair that inconsistency: it changes the dispersion shape only, while preserving the old anchor and matrices. Its worse normalized RMSE (0.2803 versus 0.2624) therefore does not exonerate the state-assignment error.

The paper's dashed Figure 2d curve is explicitly nonnegative \(|\chi^{(2)}|\). A zero of \(\operatorname{Re}\chi\) is not what is plotted. The present model has neither a real nor an imaginary crossing in the configured windows, and its magnitude is not zero there. The electron and signed-heavy-hole terms are nearly antiparallel at 605 and 1330 nm, but leave finite residuals.

My overall conclusion is: **the literal real-envelope Equation-2 summation appears internally correct, but the sampled (k) domain and the physical identity/consistency of the states and matrix elements are not. A small, targeted Professional calculation is necessary; a full campaign is not.**

## Agreements and disagreements with the primary analysis

### Agreements

- Figure 2d must be compared with \(|\chi^{(2)}|\), not with a signed real component.
- Neither modeled minimum is a full complex zero. Strong cancellation is present, but it is incomplete.
- The (N_k=101,201,301) comparison rules out radial quadrature density as the main cause on the existing interval.
- Varying \(\Gamma\) from 2.5 to 10 meV changes widths and fills minima but never restores the four-peak topology.
- A global normalization factor cannot repair a normalized shape or create nodes.
- Four states are the appropriate first reproduction target because the paper explicitly says it retained the first two conduction and first two HH bound states.
- The copied output lacks finite-(k) spinors/envelopes and finite-(k) matrix elements despite the input requesting them. No finite-(k\) numerator should be fabricated.
- A targeted Professional rerun is justified.

### Disagreements and qualifications

- I do **not** rank HH/LH assignment first. I rank the (\pi/a\) versus (2\pi/a) cutoff convention first because it quantitatively predicts the missing 540/1080-nm resonance pair.
- The primary report treats the paper's 0.1-BZ statement as evidence *against* a cutoff problem. It is instead evidence *for* one once the zincblende \(\Gamma\)-X distance is used.
- Extending only to (0.125\pi/a) is not an adequate next run. The decisive interval is approximately (0.2\pi/a\), and 601 points preserve the current \(\Delta k\) of the 301-point, (0.1\pi/a) calculation.
- The worse pair-1+2 diagnostic is not a clean test of HH2 identity because its (k=0) energy and all numerator matrices remain anchored to another calculation.
- Missing finite-(k\) (M(k)) is physically plausible, especially for delicate nodes, but it is not proven to be part of the authors' Figure 2d model. In printed Eq. 2, (k_\parallel) is explicit in the denominators but not in the envelope matrix elements, consistent with a frozen-envelope implementation. It is nevertheless required for a self-consistent 8-band extension.
- The current alternate-direction spectrum differs from production by only 1.99% complex RMSE, shifts the 1376-nm peak by 3 nm, and leaves the 752/1503-nm peaks unchanged. This makes anisotropy a lower-priority explanation on the sampled interval than the primary rank suggests. It may become more important over the doubled interval.
- A single ideal-abrupt deck would combine a geometry change with a cutoff change. For causal diagnosis, the first extended-(k) deck should retain the current graded geometry; an ideal-abrupt deck should then be the controlled paper-geometry comparison.

## Independent top-five root causes

| Rank | Hypothesis | Independent confidence | Why it is ranked here |
|---:|---|---:|---|
| 1 | Wrong BZ-edge/cutoff convention and truncated resonance domain | 0.96 | The (0.125\pi/a) calculation produces a 659/1318-nm one-/two-photon pair; the missing paper features are 540/1080 nm. The fitted \(\Delta E_{22}\) reaches exactly that pair at (0.1021\,\Gamma X\), essentially the paper's stated 0.1 BZ. |
| 2 | HH2 state-identity error and inconsistent denominator/numerator pairing | 0.90 | The selected pair is 97.6% LH while an available pair is 100% HH. Its energy dispersion is nevertheless multiplied by a two-HH matrix set from another run. This invalidates pathway identification even if some peak positions happen to agree. |
| 3 | Paper/model structural and Hamiltonian mismatch | 0.74 | Figure 2d is most plausibly the ideal abrupt design, whereas Demo 23 uses four 1-nm linear interfaces. Temperature for the paper calculation is unstated. The paper itself shows nanometer-scale grading changes energies and matrix elements substantially. |
| 4 | Frozen, non-self-consistent (M(k)=M(0)) numerator | 0.66 | The nodes are residuals of 95-97% cancellation, so modest pathway-dependent changes in overlaps, centroids, or phase can create or fill them. However, the printed paper equation may itself use (k)-independent envelopes, so this ranks below the domain/state problems for reproducing Figure 2d. |
| 5 | Radial/isotropic reduction over the extended domain | 0.34 | A radial disc is correct only for an isotropic integrand. The present second ray causes only a 1.99% complex-spectrum change, so it is unlikely to be primary at (0.1\pi/a); it must be rechecked at (0.2\pi/a), where HH/LH warping should be stronger. |

Broadening, (N_k), global normalization, extra states, digitization, and a simple overall electron/HH sign error are all lower-priority causes.

## Explicit answers to the 17 review questions

### 1. Is the paper-vs-model comparison apples-to-apples?

No. The nominal 7.1/1.8/2.9-nm coupled wells, Al fraction 0.55, 5-meV broadening, \(\chi_{xzx}^{(2)}\), and two-state-per-band truncation agree. The interface model does not: Figure 2d appears to use the ideal design, while Demo 23 is linearly graded over 1 nm at each interface. The paper temperature is not stated. More importantly, Demo 23's (0.1\pi/a) is not the physical (0.1\,\Gamma X) cutoff for zincblende, and Demo 23 mixes 8-band dispersion shapes with earlier single-band anchors and matrices. This is not one self-consistent realization of the paper model.

### 2. Are the four peak correspondences physically sensible?

Only two of the baseline correspondences are presently established. The modeled 752-nm and 1503-nm peaks are the one- and two-photon resonances of the (e2\)-`hh2` transition near (k=0), consistent with the paper's discussion of approximately 760 and 1520 nm. The paper's 540- and 1080-nm peaks form another exact one-/two-photon wavelength pair. They are physically consistent with the same \(\Delta E_{22}\) transition at (k\simeq1.135\ \mathrm{nm^{-1}}\), near (0.1\,\Gamma X). Calling the scorecard's window-edge values at 575 and 1160 nm model peaks is not physically meaningful; those entries indicate missing peaks, not valid correspondences.

### 3. Are the approximately 605- and 1330-nm minima consistent with sign-flip/cancellation physics?

They are consistent with *cancellation* physics, but the paper provides only the magnitude and therefore does not establish a signed flip. In Demo 23D the electron and signed-HH subtotals differ in phase by approximately 179.98 degrees at 605 nm and 179.88 degrees at 1330 nm. The cancellation ratios are 0.0428 and 0.0486. Those are strong cancellations, but not nodes. The paper eye trace touching zero should be treated as a deep minimum with finite plotting/digitization uncertainty, not proof of an exact analytic zero.

### 4. Does the calculated complex susceptibility actually flip sign there?

No. In the 550-650 and 1250-1400-nm windows the audit finds no real-part crossing and no imaginary-part crossing. At 605 nm, \(\chi\approx3.3119+0.0611i\) pm/V. At 1330 nm, \(\chi\approx-25.2086-1.0318i\) pm/V. A full complex node would require both components to vanish at the same wavelength; neither does.

### 5. Which Equation-2 pathways should cancel?

The dominant cancellation is pairwise between the conduction-side and valence-side diagonal terms with the same optical transition: `C_m1_n1_l1` versus `V_m1_n1_l1`, and `C_m2_n2_l2` versus `V_m2_n2_l2`. For real envelopes their common-denominator residual is proportional to (O_{nm}^2(z^e_{nn}-z^{hh}_{mm})).

At 605 nm, the first pair leaves approximately (0.1733+0.0023i) pm/V and the second leaves (3.2322+0.0590i) pm/V; the total is (3.3119+0.0611i) pm/V after small off-diagonal corrections. At 1330 nm, the corresponding residuals are approximately (-1.1196-0.0131i) and (-24.5932-0.9851i) pm/V, accounting for almost the entire total. This agrees with the paper's statement that most pathways cancel pairwise and diagonal intersubband moments dominate the surviving response.

### 6. Is the current electron-minus-heavy-hole subtraction physically correct?

Yes for the literal printed Eq. 2 evaluated with real scalar envelopes: the relative minus sign, the (m,n,l) denominators, and the 16-term enumeration are correct, and independent summations agree. It is not sufficient validation for complex finite-(k) 8-band objects. The present adapter accepts complex matrices but multiplies overlaps without enforcing their bra-ket orientation. For complex spinors, the conduction numerator should contain the appropriate conjugate of \(\langle e_n|hh_m\rangle\), and the valence numerator should contain the conjugate corresponding to \(\langle hh_l|e_n\rangle\). A finite-(k) implementation must use explicitly oriented Hermitian matrix elements, not reuse the real-envelope products blindly.

### 7. Could (M(k)=M(0)) plausibly destroy these nodes?

Yes. The residual magnitude is only about 4-5% of the sum of the two large subtotals at the candidate minima. Pathway-dependent changes of a few percent in overlaps, diagonal centroids, or relative phase can therefore move, create, or erase a minimum. The 97.6% LH character assigned to `hh2` makes large finite-(k) evolution plausible. Nonetheless, the paper's printed Eq. 2 shows (k\) explicitly only in the transition frequencies, so frozen envelopes may be part of the authors' approximation. (M(k)) is essential for a self-consistent 8-band calculation, but it is not yet proven to be required to reproduce the authors' own curve.

### 8. Could HH/LH mixing explain the missing spectral structure?

It could, and the present state label is demonstrably wrong at (k=0): pair 3+4 is LH-like, not HH2. This can alter both the denominators and selection rules. However, the available data do not show finite-(k) character or avoided-crossing exchange, and the pair-1+2 diagnostic retains mismatched anchors and matrices. Therefore HH/LH mixing is a serious model-validity defect, not yet a demonstrated explanation of the missing nodes or peaks.

### 9. Could four-state truncation be responsible?

It is unlikely to be the reason for disagreement with Figure 2d because the paper explicitly states that only the first two conduction and first two HH bound states were used. Adding (e3\), HH3, or LH pathways would change the model rather than reproduce it. Extra states matter only for robust tracking through crossings and for constructing the correct low-energy subspace; they should not be added to the optical sum without a separate physical justification.

### 10. Are the resonance denominators located correctly?

The algebra is correct and the near-zone-center resonances are well located. At (k=0), \(\Delta E_{22}=1.6482\) eV gives 752.2-nm one-photon and 1504.5-nm two-photon resonances, close to the paper's 760/1520-nm pair. The current map is incomplete because it stops at 0.5557 \(\mathrm{nm^{-1}}\); within that range it cannot reach the 2.296-eV transition needed for 540/1080 nm. The fitted (e2\)-HH2 denominator reaches that energy at (0.1021\,\Gamma X). Thus the denominator formula is likely right, but the integration domain and state identity used to populate it are not.

### 11. Could broadening explain the mismatch?

No. From 2.5 to 10 meV, all calculations retain three major peaks; the peak shifts are only a few nanometers and the minima become progressively shallower. Broadening cannot generate the missing 540/1080-nm pair and is already fixed to the paper's stated 5 meV.

### 12. Could radial (k) integration explain the mismatch?

The radial weight (g_s k\,dk/(2\pi)) is correct for an isotropic circular integral. The current two-direction test provides evidence *against* anisotropy being the primary cause on the sampled interval: the alternate ray changes the complex spectrum by 1.99% RMSE, shifts the 1376-nm feature to 1379 nm, and leaves the 752/1503-nm features fixed. Two rays are not a full 2D integral, however, and anisotropy should be re-evaluated at the physically larger cutoff, where valence-band warping and HH/LH mixing are stronger.

### 13. Is there a likely indexing, sign, or conjugation error in Equation 2?

There is no evidence of an indexing or overall electron-minus-HH sign error for the present real (M(0)) calculation. All 16 pathways sum to the reported total, the literal independent implementation agrees, and phase/sign audits pass. There are two important concerns:

1. A future complex finite-(k) implementation must restore the Hermitian conjugates implied by the bra-ket order. The current generalized adapter's plain products are valid only when the relevant matrix elements are real in a common gauge.
2. Equation 1 contains a polarization-permutation sum, while Eq. 2 is a specialized \(\chi_{xzx}^{(2)}\) expression. The paper later explicitly argues that \(\chi_{xzx}\ne\chi_{xxz}\) for this QW process and introduces a factor of 1/2 in the optical extraction. Therefore adding an ad hoc permutation or factor of two would be unjustified. The safest test is against the authors' code/data, not a guessed symmetrization. The sign of (i\Gamma) changes the sign convention of the imaginary part but not \(|\chi|\), so it cannot explain Figure 2d's magnitude shape.

### 14. Which hypothesis is most likely?

The wrong BZ-edge/cutoff convention is most likely. It uniquely and quantitatively connects the two missing paper peaks to the same \(\Delta E_{22}\) resonance at the paper's stated cutoff. HH/LH misassignment is the next most serious defect, but the current diagnostic does not isolate it cleanly.

### 15. What is the single most informative next calculation?

Calculate the existing graded structure on the [010] ray from \(\Gamma\) to (0.1\,\Gamma X=0.2\pi/a=1.11143\ \mathrm{nm^{-1}}), using 601 points so that \(\Delta k\) matches the current 301-point production run. Export enough finite-(k) state information to track the two HH-like Kramers pairs and form a self-consistent Equation-2 numerator. Then compare the resulting complex spectrum with the current (0.1\pi/a) baseline while changing *only* the cutoff. This is more informative than another calculation at (0.125\pi/a).

### 16. Is a new Professional nextnano run necessary?

**YES - a targeted run is necessary.** Existing data end at (0.125\pi/a), below the decisive (0.2\pi/a) range, and lack finite-(k) spinors/matrices. Extrapolating 8-band branches across the missing half of the domain would not be reliable, particularly with unresolved HH/LH mixing. A full seven-deck campaign is not justified.

### 17. If yes, exactly what should it calculate?

The minimum production sequence should be:

1. **Controlled cutoff deck:** retain the Demo 23 1-nm-linear structure and all material/temperature settings; compute the 8-band spectrum along [010] from (k=0) to (1.11143\ \mathrm{nm^{-1}}) ((0.2\pi/a=0.1\,\Gamma X)) with 601 points and at least the existing 14 output states. This isolates the cutoff convention.
2. **Paper-geometry deck:** repeat the identical calculation for the ideal abrupt 7.1-nm GaAs / 1.8-nm Al0.55Ga0.45As / 2.9-nm GaAs / 18.2-nm Al0.55Ga0.45As period. This isolates the interface model and supplies the apples-to-apples Figure 2d candidate.

For every (k) point, copy back: the explicit (k) vector; all relevant eigenenergies; CB/HH/LH/SO fractions; complex eight-component envelopes or spinor coefficients for each state; Kramers-pair identifiers; and either directly exported, *complex and oriented* (O_{nm}(k)), (z^e_{nl}(k)), and (z^{hh}_{ml}(k)), or sufficient complex spinors to calculate them. Record the exact input deck, resolved material database/version, solver logs, and completion marker. Because Demo 23 requested `all_k_points = yes` but received only `k00000` state/matrix files, first validate the output syntax with a very small pilot grid before launching the 601-point jobs. One [010] ray is sufficient for this first causal test; add [011] or a 2D mesh only if extended-range directional sensitivity becomes material.

If compute time permits only one production deck, run the controlled graded extended-(k) deck first. It tests the leading hypothesis without conflating it with a structural change. The two-deck sequence is still far smaller than a full campaign.

## Equation-2-specific concerns

- The present real-envelope term ordering and electron-minus-HH sign agree with printed Eq. 2.
- The diagonal-pair cancellation is the correct dominant physics; the residual is governed chiefly by (z^e_{nn}-z^{hh}_{mm}) and pathway denominators.
- Demo 23D is not self-consistent because 8-band dispersion shapes are re-anchored to, and multiplied by matrices from, an earlier scalar calculation.
- The `chi2_22` complex-matrix interface is not yet gauge-safe: overlap conjugation must follow the bra-ket orientation explicitly.
- An extra SHG frequency permutation must not be inserted without the authors' convention or code. The paper's own discussion of \(\chi_{xzx}\) versus \(\chi_{xxz}\) indicates that this specialization was intentional.
- The current magnitude comparison cannot establish the sign of the paper susceptibility.

## Pro-rerun decision and confidence

**Professional rerun required: YES, TARGETED (not a full campaign).**

**Confidence in the leading cutoff diagnosis: high (0.96).**

**Confidence in the overall causal ranking: moderately high (0.85).** The principal uncertainty is whether the authors used (2\pi/a) exactly as the crystallographic edge and whether their numerator was frozen at (k=0). The exact 540/1080-nm resonance-pair correspondence makes the cutoff conclusion substantially stronger than a generic convergence concern.

## Evidence reviewed

- `2602.23246v1.pdf`, especially Figure 2d and Methods Eq. 2 on pages 7 and 11-12, plus the tensor-permutation discussion on page 14.
- Demo 24 feature, signed-zero, cancellation, pathway, resonance, broadening, (N_k), (k_{max}), direction, state-character, and finite-(k) inventory outputs.
- Demo 23 `physics23.py`, `analysis23.py`, `dispersion_models.py`, `chi2_22.py`, the production deck, the (k=0) spinor table, and the earlier frozen matrix record.
- Repository convention audit noting that `legacy_pi_over_a` is inherited from a simple-cubic assumption and that zincblende \(\Gamma\)-X is (2\pi/a).
