# Robert/Kurt questions: evidence and cautious answers

Read `PHYSICS_GUIDE.md` for terminology and `RESULTS.md` for full tables. Plot paths below are relative to `outputs/`. “High confidence” means confidence in the stated calculation, not certification of the underlying material model.

## 1. What does Im chi2 look like?

**Why:** it was hidden by the earlier magnitude comparison. **Test:** retain the complex sum and plot Im independently. **Plot:** `28A_baseline/plots/28A_imag.png`. **Numerical result:** main positive lobe peaks29.057pm/V near748nm; negative lobe reaches-57.898pm/V at1496nm. **Answer:** it has structured signed resonant bands, not zero or a constant background. **Confidence:** high for baseline. **Uncertain:** measured absorption interpretation and physical model completeness.

## 2. Why is there an imaginary component without tracked carriers?

**Why:** a complex response was mistaken for a population simulation. **Test:** paper occupation audit and28D numerator/denominator controls. **Plot:** `28D_imaginary_source/plots/28D_imag_electron_hole.png`. **Numerical result:** invariant numerator imaginary part0, but total Im reaches57.898pm/V in magnitude. **Answer:** the perturbative expression is complex throughiGamma; a time-dependent carrier-population solver is not required to evaluate it. **Confidence:** high algebraically. **Uncertain:** completeness of the real-field response/observable conversion.

## 3. What population assumption is actually present?

**Why:** not calculating populations is not the same as having no occupation assumption. **Test:** read paper Methods5.1 and inspect decks. **Plot:** same28D figure illustrates the resulting response, not populations. **Numerical result:** paper uses filled starting valence occupation unity; decks use no_density=yes. **Answer:** fixed initial/equilibrium occupation enters the response formalism; no photoexcited population dynamics is propagated. **Confidence:** high source/code evidence. **Uncertain:** effects of pumping, filling changes, relaxation and electrostatic feedback outside this model.

## 4. Does Im come from Gamma, numerator phases, or both?

**Why:** arbitrary state phases must not become a physical explanation. **Test:** inspect O,ze,zh and complete invariant products; real-representation control. **Plot:** `28D_imaginary_source/plots/28D_imag_gamma_to_zero.png`. **Numerical result:** every numerator Im=0; full-versus-real control error0pm/V. **Answer:** in this baseline the source is complex denominators, followed by signed pathway cancellation. **Confidence:** high. **Uncertain:** not generalized to finite-k complex spinor matrices that are not used here.

## 5. Does Re dominate away from resonance?

**Why:** tests a physical expectation objectively. **Test:** minimum actual one-/two-photon detuning>=100meV;736wavelength samples. **Plot:** `28E_linewidth/plots/28E_ratio_selected.png`. **Numerical result:** atGamma5meV L2(Im)/L2(Re)=0.014384;100% of off samples Re-dominant. **Answer:** supported in the chosen off-resonance window. **Confidence:** high within those definitions. **Uncertain:** other frequency ranges/models or occupation conditions.

## 6. Does Im dominate near resonance?

**Why:** a one-pole intuition may fail after interference. **Test:** minimum detuning<=25meV;500samples. **Plot:** `28E_linewidth/plots/28E_imag_gamma_selected.png`. **Numerical result:** L2 ratio1.155858 but only35.4% of near samples Im-dominant; median safe ratio0.122503. **Answer:** partial support in an aggregate norm, not a universal pointwise rule. **Confidence:** high for defined masks. **Uncertain:** resolved small-linewidth limits and changes to response pathways.

## 7. Why does the off-resonant response look unusual?

**Why:** shapes may reflect cancellations rather than an isolated oscillator. **Test:** electron/hole and shell decomposition, ratio metrics. **Plots:** `28D_imaginary_source/plots/28D_real_electron_hole.png`, `28B_kspace_cutoff/plots/28B_real_shell.png`. **Numerical result:** off Im/Re norm0.014384 despite large cancelling groups; overall16term cancellation about97.19%. **Answer:** the residual is a signed many-pathway integral; it need not look like one resonance. **Confidence:** high decomposition, moderate interpretation. **Uncertain:** whether all relevant states/antiresonant terms and correct electrostatic physics are present.

## 8. Why is k-cutoff sensitivity strong?

**Why:** determines whether the result is a stable material prediction. **Test:** exact shell sum with radial measure and fixed matrices. **Plots:** `28B_kspace_cutoff/plots/28B_real_shell.png`, `28B_imag_shell.png`. **Numerical result:** shell sum matches core within2.37e-13pm/V; last10% changes Re1550 by2.19591pm/V. **Answer:** changing detunings, signed cancellation and radial area continue to contribute; matrix growth is impossible under frozenM. **Confidence:** high for mechanism exclusions and arrays. **Uncertain:** behavior with trueM(k), angle dependence and valid higher states.

## 9. Does the integral saturate at the baseline cutoff?

**Why:** paper states saturation. **Test:** last10% tail normalized to max cumulative modulus. **Plots:** `28B_kspace_cutoff/plots/28B_real_cumulative.png`, `28B_imag_cumulative.png`. **Numerical result:** tail ratios21.77%,5.87%,19.23%,5.17%,8.29% at540/760/1080/1520/1550nm. **Answer:** not demonstrated; all exceed the stated1% check. **Confidence:** high numerical finding. **Uncertain:** equivalence to the paper's domain, states and saturation criterion.

## 10. Can we independently check Kurt's nonsaturation observation?

**Why:** agreement must be tested, not assumed from a comment. **Test:** rerun native cutoff/shell calculations from package-local raw files. **Plot:** same28B cumulative figures. **Numerical result:** all five tails remain appreciable; no extra solver or extrapolation used. **Answer:** independently reproduced nonsaturation for our retained historical model, not necessarily Kurt's exact implementation. **Confidence:** high for this model. **Uncertain:** Kurt's data/model settings and comparison tolerance.

## 11. What happens beyond0.1pi/a?

**Why:** directly tests the extended-range request. **Test:** cached0.125run, nested0.10/0.1125/0.125cutoffs on the same grid. **Plots:** `28C_extended_k/plots/28C_real_extended_cutoffs.png`, `28C_imag_extended_cutoffs.png`. **Numerical result:** Re1550 rises26.47017→31.57391pm/V; Im1550 falls0.79734→0.67907pm/V. **Answer:** the response continues changing. **Confidence:** high numerical; physical confidence limited. **Uncertain:** high-k branch character and further convergence.

## 12. Do both Re and Im peaks move?

**Why:** global argmax can jump between lobes. **Test:** named windows with interior extrema and1nm resolution. **Plot:**28C separate spectra; table `28C_extended_k/windowed_features.csv`. **Numerical result:** tracked Re minimum1374→1316nm, Im lobe1398→1353nm from0.10→0.125; short Re maximum687→658nm. **Answer:** yes, specified features shift. Global Im switches dominant lobes, so1496→1353 is not a single continuous branch shift. **Confidence:** high for windowed features. **Uncertain:** finer peak positions and physically validated branch assignments.

## 13. Is the change just a coarser grid artifact?

**Why:** both cached datasets have301points but different spacing. **Test:** compare dense301 and extended241 at identical0.1endpoint; separately compare nested extended cutoffs. **Plots:** `28H_grid_convergence/plots/28H_real_matched_cutoff.png`, `28H_imag_matched_cutoff.png`. **Numerical result:** max errors0.034934/0.023299pm/V forRe/Im, versus many-pm/V extension changes. **Answer:** sampling mismatch does not explain the observed large extension effect on this model. **Confidence:** high for controlled comparison. **Uncertain:** rigorous infinite-density error at allGamma/high-kresonances.

## 14. Is the complex response Kramers–Kronig consistent?

**Why:** causality and complete physical response are distinct checks. **Test:** analytically justified diagonalSHG full-line relation on signed uniform energy; analytic oscillator benchmark first. **Plots:** `28F_causality/plots/28F_re_from_im_KK.png`, `28F_reality_symmetry.png`. **Numerical result:** central relative RMS1.62e-5(Re),1.33e-5(Im); real-field symmetry defect0.99717. **Answer:** mathematical rational-expression KK PASS; complete physical response INCONCLUSIVE. **Confidence:** high numerical/algebraic; limited physical inference. **Uncertain:** full counter-rotating/negative-frequency completion and paper convention.

## 15. Does Fig.2d appear closer to abs(Re) than abs(chi)?

**Why:** an observable choice changes minima. **Test:** own-max normalized digitized comparison, same domain/metrics. **Plots:** `28J_paper_comparison/plots/28J_paper_vs_abs_real.png`, `28J_paper_vs_magnitude.png`. **Numerical result:** baseline nRMSE0.237873 vs0.262391; correlations0.30963 vs0.24756. **Answer:** absRe is closer here, but neither is a close reconstruction and this cannot identify the authors' observable. **Confidence:** high metric, limited interpretation. **Uncertain:** exact plotted definition and remaining model differences.

## 16. Is best paper fit the converged cutoff?

**Why:** fitting a cutoff is not a convergence test. **Test:** paper metrics vs cutoff and separate cumulative tails. **Plot:** `28J_paper_comparison/plots/28J_paper_error_vs_cutoff.png`. **Numerical result:** bestabsRe tested0.125 on extended grid(nRMSE0.226310); bestmagnitude native grid0.07(nRMSE0.251241). No demonstrated converged cutoff. **Answer:** these are different questions with different outcomes. **Confidence:** high within sampled choices. **Uncertain:** paper settings and convergence of a physically corrected model.

## 17. Which transitions/pathways matter?

**Why:** the final curve hides interference. **Test:** all16products/spectra, diagonal split, pairwise cancellation and transition map. **Plots:** `28G_pathways/plots/28G_real_top_pathways.png`, `28G_resonance_map.png`. **Numerical result:** largest raw termsC111,V111,C222,V222; C111/V111 cancellation99.7118%, C222/V22281.1061%; diagonal norm1.0293times total. **Answer:** diagonal terms dominate but substantially cancel; denominator resonances move withk. **Confidence:** high calculation, origin-dependent group interpretation. **Uncertain:** extra states/finite-k matrices and assignment of all observed paper features.

## 18. What exactly comes from nextnano, and what assumptions remain?

**Why:** provenance is necessary before interpreting agreement. **Test:** raw/parsed/derived lineage and state audit. **Plot:** `28I_state_character/plots/28I_k0_character.png`. **Numerical result:** h2 is97.58%LH and0%HH at0; finite-k spinor coverage1/301. **Answer:** nextnano supplies raw energies/envelopes; Python aligns energies, forms and freezes matrices, evaluates Eq2 and integrates. Gamma,r,Nz,spin/radial reduction are configured/adopted inputs. **Confidence:** high provenance evidence. **Uncertain:** two-HH mismatch, high-k identity, original Poisson/dispersion/M(k) choices, absolute normalization and observable. See `DATA_LINEAGE.md` and `NEXT_QUESTIONS.md` for the exact next actions.
