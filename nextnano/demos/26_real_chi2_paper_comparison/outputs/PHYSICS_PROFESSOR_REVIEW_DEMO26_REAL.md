# Independent physics-professor review of Demo 26_real

## Scope of this review

I reviewed Demo 26_real as an independent assessment of the observable question, rather than as an endorsement of the primary report. The materials inspected were the main three-trace overlay (Figure 1), the two zero-region zooms (Figures 5 and 6), the feature-correspondence summary (Figure 10), the spectra, metrics, zero-crossing, feature-comparison, paper-audit, and Demo 24 reassessment files, the relevant Demo 24 conclusions, and the published source `2602.23246v1.pdf` (Figure 2d on PDF page 7 and Methods on pages 11-12). No nextnano Professional calculation was run.

## Independent verdict

The colleague's proposed reinterpretation is **not supported**. The paper explicitly labels the simulated trace as `Simulated |chi^(2)| (pm/V)`, plots it against a nonnegative axis, and reports an intensity-based SHG experiment rather than a phase-sensitive measurement. Demo 26_real then supplies the decisive model-side test: the only two zero crossings of the preserved Demo 23D real part occur at 714.029 and 1437.480 nm, approximately 109 and 107 nm away from the paper's apparent minima at 605 and 1330 nm. Thus, even if the paper label were ignored, the calculated signed real part does not generate the proposed sign changes at the relevant wavelengths.

The main numerical comparison points the same way. Over 400-1850 nm, the normalized RMSE is 0.3834 for the signed real part and 0.2624 for the magnitude; normalized MAE is 0.3050 and 0.2066, respectively. The real-part comparison therefore has about 46% larger RMSE, while the magnitude reduces RMSE by about 32% relative to the signed-real comparison. Neither trace is a satisfactory reproduction of the paper, but signed Re[chi^(2)] is not the improvement proposed by the hypothesis.

My exact rerun verdict is:

**DEMO 25 STILL REQUIRED**

Here "required" means required to resolve the still-open scientific questions if reproducing Figure 2d remains the objective. It does not mean that finite-k matrix elements have already been proved to be the cause, and it does not authorize running nextnano Professional on this home laptop.

## Answers to the nine professor questions

### 1. Is comparing the paper to Re[chi^(2)] physically justified?

**As a falsification diagnostic, yes; as the primary interpretation of Figure 2d, no.**

Equation 2 is complex because both resonant denominators contain `+ i Gamma`, so inspecting Re, Im, and magnitude is physically informative. A zero of Re[chi^(2)] need not be a zero of the complex susceptibility. That is exactly why Demo 26_real is a worthwhile diagnostic.

However, ordinary SHG intensity is proportional to the squared modulus of a coherent nonlinear field. Without interferometric or heterodyne phase information, an intensity spectrum does not separately determine Re[chi^(2)]. The paper describes intensity-based SHG measurements and labels its simulated quantity as |chi^(2)|. The physically appropriate like-for-like comparison is therefore the magnitude (or, at the detected-power level, the properly propagated field intensity), not signed Re alone.

There is also a convention issue: the global sign of a calculated tensor component depends on coordinate and phase conventions unless referenced experimentally. This does not affect the present rejection, because multiplying Re by -1 would not move its zero crossings; it would only exchange positive and negative lobes.

### 2. Does the paper appear to show signed Re[chi] rather than magnitude?

**No.** Three independent observations agree:

- The left axis of Figure 2d explicitly reads `Simulated |chi^(2)| (pm/V)`.
- The simulated curve and its axis are nonnegative; there is no negative branch and no signed zero axis through the plot.
- The Methods define a complex susceptibility but never state that Figure 2d plots its real part. The use of complex broadening in the formula does not itself determine which observable is graphed.

I find no affirmative evidence of a mislabeled axis. Reconciling the colleague's interpretation with the printed figure would require at least two unsupported assumptions: that the modulus bars are erroneous and that negative real-part lobes were folded upward or clipped. The source provides evidence for neither.

### 3. Are the approximately 605 and 1330 nm features better interpreted as Re[chi] sign crossings?

**No, not for the preserved Demo 23D calculation, and not from the published figure alone.**

At the two paper wavelengths the model values are:

| Paper feature | Re[chi] (pm/V) | Im[chi] (pm/V) | |chi| (pm/V) | Nearest Re zero | Offset |
|---|---:|---:|---:|---:|---:|
| Z1, 605 nm | 3.3119 | 0.0611 | 3.3124 | 714.029 nm | +109.029 nm |
| Z2, 1330 nm | -25.2086 | -1.0318 | 25.2298 | 1437.480 nm | +107.480 nm |

Both calculated roots are genuine sign reversals of Re, but they are not near the paper minima. Moreover, Im and |chi| remain large at the roots: approximately 27.279 pm/V at 714.029 nm and 52.997 pm/V at 1437.480 nm. Those roots are therefore not complex-susceptibility nodes.

The converse logical point is also important. A nonnegative magnitude trace that visually touches its baseline does not establish an exact analytic zero, much less a sign reversal of one component. The two zero-valued repository samples come from an eye digitization of a printed dashed curve, not raw author data with uncertainties. They should be called apparent deep minima unless author data establish exact zeros.

### 4. Do the four major paper features line up better with Re[chi]?

**No.** P1 and P3 have no significant corresponding interior extremum in either signed Re or |chi|. P2 and P4 occur near model features in both observables:

| Feature | Paper | Signed-Re extremum | Magnitude maximum | Physical reading |
|---|---:|---:|---:|---|
| P1 | 540 nm | none | none | missing in both |
| P2 | 760 nm | 753 nm | 752 nm | both close in wavelength; Re is negative while the paper trace is positive |
| P3 | 1080 nm | none | none | missing in both |
| P4 | 1520 nm | 1505 nm | 1503 nm | both close in wavelength |

The feature CSV labels signed Re as the wavelength winner for P2 and P4 because its absolute errors are smaller by 1 and 2 nm. I do **not** regard those differences as meaningful given the 1 nm model grid and, more importantly, the coarse eye digitization of the published curve. At P2 the chosen signed-Re "peak" is actually a negative extremum (normalized value -0.542 against a positive paper value 0.620), so wavelength-only matching overstates agreement. The robust result is that the same P2/P4 resonance pair appears in both observables, while P1/P3 are missing from both.

### 5. Does Re[chi] substantially outperform |chi| quantitatively?

**No. The principal error metrics favor |chi|, although the metric evidence is not unanimous.**

| Metric, full overlap | Paper vs signed Re | Paper vs |chi| | Better |
|---|---:|---:|---|
| normalized RMSE | 0.3834 | 0.2624 | |chi| |
| normalized MAE | 0.3050 | 0.2066 | |chi| |
| correlation coefficient | 0.3643 | 0.2476 | signed Re |
| matched peak count | 2 | 2 | tie |
| matched-peak wavelength MAE | 11.0 nm | 12.5 nm | effectively tied |

The higher signed-Re correlation should be reported rather than hidden. It reflects some common broad spectral ordering, but it is outweighed here by the much larger signed amplitude residual, extensive sign disagreement, absent P1/P3 features, and misplaced zeros. Regionally, |chi| has lower RMSE in 700-900, 950-1200, and 1200-1450 nm; signed Re is slightly lower in 500-700 nm and lower around the main 1420-1620 nm resonance. In the particularly diagnostic 700-900 nm region, signed Re is anticorrelated with the paper (-0.864), whereas |chi| is positively correlated (0.627).

As an additional check, the secondary |Re| envelope has a full-range normalized RMSE of approximately 0.2379, modestly below the 0.2624 magnitude result. This does not rescue the stated hypothesis: |Re| is not signed Re, is not what the paper labels, and taking the absolute value does not move the calculated Re zeros from 714 and 1437 nm to 605 and 1330 nm. It does show that a single independently normalized RMSE must not be treated as proof of the physical observable.

### 6. Which Demo 24 conclusions survive?

My classifications are:

| Demo 24 conclusion | Independent classification | Assessment |
|---|---|---|
| missing P1/P3 | **STILL VALID** | Neither Re nor magnitude supplies either feature. |
| missing 605 node | **STILL VALID** | The current complex model is finite there and the nearest Re root is 714 nm. "Node" should be read as the paper's apparent deep magnitude minimum, not a demonstrated exact zero. |
| missing 1330 node | **STILL VALID** | The current complex model is finite there and the nearest Re root is 1437 nm, with the same terminology caveat. |
| 2.296 eV missing transition | **STILL VALID** | The 540/1080 nm 2:1 pair remains absent from the current four-state bound model. This is a reachability diagnosis, not yet proof of the physical remedy. |
| kmax artifact | **UNRELATED TO REAL-vs-MAGNITUDE ISSUE** | Its movement with the integration boundary is component-independent evidence of a truncated sum. It survives this demo. |
| finite-k M(k) required | **WEAKENED** | Finite-k matrices are required for a converged test, but current perturbations show only that nodes are reachable in numerator space, not that physical M(k) will create them. This agrees with the revised Demo 26 reassessment CSV. |
| additional states required | **WEAKENED** | Extra states and oscillator strengths should be retained diagnostically, but the paper explicitly says its Eq. 2 sum used the first two bound states per band. Adding states is not yet an established repair. |
| geometry mismatch | **UNRELATED TO REAL-vs-MAGNITUDE ISSUE** | The paper-structure versus Demo 23 structure difference remains a separate model-consistency question. |
| need for Demo 25 Professional run | **STILL VALID** | Reinterpretation does not resolve the mismatch; a targeted discriminating run remains justified. |

The strongest surviving conclusions are the observable-independent ones: P1/P3 are absent, the 2.296 eV channel is outside the present model space, and the long-wavelength structure moves with kmax. The weakest causal claim remains that finite-k M(k) itself will restore the paper nodes. That outcome is plausible but unproved.

### 7. Was the previous missing-physics diagnosis partly caused by comparing the wrong observable?

**No, not in the material sense tested here.** The observable check is valuable because it prevents an invalid statement that every Re zero must be a |chi| zero. But the principal Demo 24 discrepancies survive: P1/P3 remain absent, neither model component crosses at 605 or 1330 nm, and the current long-wavelength feature remains cutoff-sensitive. The prior diagnosis may have used the word "node" too literally for two eye-digitized baseline contacts, but it was not generated by using |chi| instead of Re.

### 8. Is a Professional nextnano rerun still scientifically justified?

**Yes. DEMO 25 STILL REQUIRED.**

The run is justified because the present files cannot answer the remaining causal questions: they contain E(k) but not self-consistent finite-k complex overlaps and intraband dipoles. The rerun should be targeted, not a broad parameter campaign, and should be performed only on the authorized work-laptop environment.

### 9. What specifically remains unresolved?

The targeted Professional calculation must distinguish among three live possibilities:

1. **Finite-k numerator physics and convergence.** Export complex `O_nm(k)`, `z_e,nl(k)`, and `z_hh,ml(k)` (or equivalent complex matrix data) on an extended k range. This tests whether physical, correlated M(k) variation damps the high-k tail and produces deep minima. A single-pathway scale perturbation is not a substitute because real matrix elements constrain several pathways simultaneously.
2. **State identity and model space.** Export per-k CB/HH/LH/SO character and retain enough additional states, energies, and oscillator strengths to determine whether any optically relevant channel approaches 2.296 eV. If none does before loss of confinement, P1/P3 are a structure/model-identification problem rather than an M(k) correction.
3. **Geometry consistency.** Calculate the exact abrupt Figure 2d structure and, if resources permit, the current graded Demo 23 structure as a controlled comparison. Otherwise geometry and finite-k effects remain confounded.

The scientifically relevant output remains |chi^(2)| for comparison with Figure 2d, with Re and Im retained as diagnostics. Extending kmax while keeping M(k) frozen would only move the truncation edge and would not answer the question.

## Agreements and disagreements with the primary Demo 26_real analysis

I agree that Figure 2d is explicitly a magnitude plot, that the two calculated Re zeros are far from 605 and 1330 nm, that signed Re has worse full-range RMSE/MAE, that P1/P3 remain missing, and that a targeted Professional calculation is still warranted.

I qualify or disagree with four narrower statements:

- Calling signed Re the better P2/P4 feature match is too strong. Its 1-2 nm wavelength advantage is below the credibility of the eye digitization, and the P2 Re extremum has the wrong sign.
- The correlation result favors Re even though RMSE and MAE favor magnitude. The proper conclusion is not that every shape statistic favors magnitude, but that Re clearly does not substantially outperform it.
- `finite-k M(k) required` is established as a requirement for the next *test*, not as the demonstrated cause of the missing paper features.
- The digitized zero samples are not proof that the published theoretical curve has exact zeros. The report's main conclusion survives if they are merely deep minima.

## Uncertainty and confidence

- **High confidence (0.97)** that Figure 2d is intended to show |chi^(2)|, based on its explicit label, nonnegative axis, and measurement context.
- **High confidence (0.98)** that the preserved Demo 23D Re spectrum does not cross zero near 605 or 1330 nm; its only roots on the analyzed interval are 714.029 and 1437.480 nm.
- **High confidence (0.92)** that signed Re does not resolve the central mismatch. This conclusion uses label, zero position, missing features, and error metrics together rather than RMSE alone.
- **Moderate confidence (0.60)** about the physical origin of the remaining discrepancy. Finite-k M(k), state/model-space limitations, and geometry consistency are not separable with the existing data.
- **Low confidence** that the printed baseline contacts are exact mathematical nodes, because the available paper curve is a sparse eye digitization without author uncertainties or phase data.

## Final professor conclusion

The most important plot answers the requested question quickly and correctly: normalized signed Re[chi^(2)] changes the story in detail, but not in the colleague's proposed direction. It introduces broad negative lobes not present in the paper, misses both proposed sign-change wavelengths by roughly 0.11 micrometers, and does not restore P1 or P3. The published label and experimental context independently favor |chi^(2)|. Demo 24's main discrepancy findings therefore remain materially intact, with the important qualification that finite-k M(k) is a hypothesis to test rather than an already proven cure.

**Final exact verdict: DEMO 25 STILL REQUIRED.**
