# Demo 26_real — Independent Reproduction / Implementation Audit

## 1. Executive summary

The home-laptop audit found **no Equation 2 transcription, pathway summation, gauge, coordinate-origin, time-convention, or constant radial-normalization bug** in the existing implementation. An independently written evaluator reproduces every stored pathway and subtotal and matches the final complex spectrum to `5.33e-10 pm/V` maximum absolute error.

Taking `|Re chi|` does help: normalized RMSE improves from **0.262391** for `|chi|` to **0.237873**. That is a 9.34% RMSE reduction, but the paper's missing P1/P3 structure and 605/1330-nm minima are still not reproduced. The best constrained diagnostic was the off-diagonal-only subset (RMSE **0.221494**), but the paper does not justify discarding the other pathways, so this is not a physical reproduction.

The most credible differences to resolve are: (1) the paper's ideal/abrupt structure versus Demo 23's 1-nm grading, (2) an unresolved factor-of-two interpretation of “0.1 BZ”, (3) matrix/state provenance—the production calculation uses frozen scalar Demo 19 matrices rather than matrices reconstructed from the same 8-band states as the saved dispersions, and (4) an undemonstrated Schrödinger-Poisson match. These should be compared with the colleague's exact deck and plotting script before commissioning Demo 25.

Decision: **DEMO 25 SHOULD WAIT — NEED FRIEND'S REPRODUCTION DETAILS FIRST**.

## 2. Why the audit was extended

Demo 26 established that signed `Re chi` is worse than the paper magnitude trace (RMSE 0.383379 versus 0.262391). A reported nextnano reproduction using approximately `M(k)=M(0)` makes implementation and convention differences the correct next target before attributing disagreement to missing finite-k matrix physics.

## 3. Friend reproduction hypothesis

The colleague may have used a different structure, electrostatic model, BZ definition, state mapping, matrix source, pathway subset, or plotted observable. “nextnano plus M(0)” is not enough to establish an identical calculation. The decisive comparison artifact is the colleague's runnable deck together with the exact post-processing script.

## 4. `|Re chi|` test

| Observable | Normalized RMSE | Correlation |
|---|---:|---:|
| signed `Re chi` | 0.383379 | 0.364306 |
| `|Re chi|` | **0.237873** | 0.309630 |
| `|chi|` | 0.262391 | 0.247555 |

`|Re chi|` materially improves global RMSE but does not restore the missing features. It is plausible as a plotting convention only if the colleague confirms it; Figure 2d itself is explicitly labeled `|chi^(2)|`.

## 5. Gamma sweep

The complete 0, 0.25, 0.5, 1, 2.5, 5, 7.5, and 10-meV sweep is in `GAMMA_OBSERVABLE_SWEEP.csv`. The best `|Re chi|` result is 7.5 meV (RMSE 0.235071), only a small change from 5 meV. For `|chi|`, the best tested value is 2.5 meV (0.257014). Gamma=0 is finite on the sampled grid but is diagnostic only and worsens RMSE to 0.333033. Broadening does not explain the paper.

## 6. Independent Equation 2 implementation

The independent code uses explicit `m,n,l` loops, saved aligned electron/HH dispersions, explicitly oriented complex bra/ket products, and a separately reconstructed energy-domain prefactor. It does not import `physics23.py`, `analysis23.py`, or the Demo 22 pathway evaluator. It compares 23,216 pathway samples plus 4,353 subtotal/final samples. Maximum final disagreement is `5.33e-10 pm/V`, well below the audit tolerance.

## 7. Equation 2 transcription audit

The common two-photon denominator, both one-photon denominator indices, relative electron-minus-HH sign, frequency permutation, Gamma placement, energy conversion, and cancellation of the printed `hbar^-2` in the energy-domain form all match. The independent implementation adds explicit conjugation according to bra/ket orientation; because the frozen matrices are real, it produces the same values as the stored evaluator. See `EQUATION2_TERM_BY_TERM_AUDIT.md` and `INDEPENDENT_DENOMINATOR_AUDIT.csv`.

## 8. Pathway subset analysis

| Subset | RMSE | Correlation |
|---|---:|---:|
| all 16 | 0.262391 | 0.247555 |
| electron diagonal only | 0.228760 | 0.441450 |
| HH diagonal only | 0.228201 | 0.454763 |
| both diagonal families | 0.257341 | 0.246232 |
| off-diagonal only | **0.221494** | **0.526603** |

Several reduced subsets resemble the digitized trace more closely, showing that numerator cancellation is central. None is established as the paper's intended equation; the result is diagnostic, not permission to remove terms.

## 9. k-integration audit

Production `g_s k dk/(2pi)`, `k dk`, and `2pi k dk` differ only by constants and become identical after normalization, as required. Equal-point weighting improves RMSE to 0.251566 and k=0-only gives 0.289887; both are unphysical diagnostics. Cumulative physical integration gives RMSE 0.287007, 0.262193, 0.250859, and 0.262391 at 0.025, 0.05, 0.075, and 0.1 `pi/a`, respectively. Relative k-region weighting changes shape, but the production measure itself is not erroneous.

## 10. BZ convention audit

Demo 23 defines `k_BZ=pi/a`, so 0.1 BZ is 0.1 `pi/a`. A conventional [010] Gamma-X distance is 2 `pi/a`, making “0.1 of Gamma-X” equal to 0.2 `pi/a`. Existing production data do not reach that alternative. Demo24's separate 0.125 `pi/a` case changed the spectrum appreciably, so the ambiguity is **POSSIBLE** and 0.2 `pi/a` is **REQUIRES_PROFESSIONAL_DATA**. No extrapolation was used.

## 11. Exact paper geometry audit

Nominal wells (7.1/2.9 nm GaAs), 1.8-nm Al0.55Ga0.45As central barrier, and period arithmetic broadly agree. The comparison is not like-for-like at the interfaces: the paper's Figure 2d calculation appears to be the ideal design, whereas Demo 23 uses 1-nm linear grading at all four interfaces. Temperature and exact electrostatic assumptions for Figure 2d are not fully specified. Grading can shift resonances and change matrix cancellations.

## 12. Independent k=0 matrix elements

Raw k=0 8-band components were phase-aligned, normalized, and integrated for both Kramers-related branches. Diagonal elements such as O11 and z11 agree at about 1%, but O12, O22, electron z12, and HH z12 differ strongly. This is **not a proven matrix bug**: the raw audit projects one dominant 8-band component per state, while the frozen values came from a scalar Demo 19 envelope construction. In particular, the tracked `hh2` state is strongly LH-like. The discrepancy is a strong provenance/state-identity warning and could materially change cancellation; a like-for-like matrix export is needed.

## 13. Gauge invariance

All 16 independent sign combinations of e1, e2, hh1, and hh2 leave the final susceptibility unchanged to exact floating-point equality in this calculation. No wavefunction-sign bug was found.

## 14. z-origin invariance

Shifts of -15, -5, 0, +5, and +15 nm produce a maximum complex difference of `1.62e-12 pm/V` (relative `1.98e-14`). The diagonal electron and HH origin terms cancel as required. No origin bug was found.

## 15. k=0 resonance assignments

| Transition | Energy (eV) | one-photon (nm) | two-photon (nm) |
|---|---:|---:|---:|
| DeltaE11 | 1.493353 | 830.24 | 1660.48 |
| DeltaE12 | 1.528367 | 811.22 | 1622.44 |
| DeltaE21 | 1.613217 | 768.55 | 1537.10 |
| DeltaE22 | 1.648231 | 752.23 | 1504.45 |

The DeltaE22 poles naturally lie near P2/P4, but proximity alone is not a pathway assignment.

## 16. P1/P3 2.296-eV reassessment

The 540/1080 arithmetic does give about 2.296 eV, but the paper does not assign both extrema to one transition, and coherent pathway sums can displace extrema from poles. The exact 2:1 pair comes from an eye digitization rather than author-tabulated peak coordinates. Conclusion: **WEAKENED, not invalidated**. A 2.296-eV channel remains a hypothesis, not proof of a missing state or higher-state requirement.

## 17. Schrödinger-Poisson audit

The paper Methods says Schrödinger-Poisson with nextnano. Demo 23 records zero fixed charge and does not document a matching self-consistent charge/doping/occupation setup. The match is therefore **UNCERTAIN / not demonstrated**. This could shift subbands and wavefunctions, but quantification needs the colleague's settings or a future Professional run.

## 18. Wavelength convention

Figure 2d explicitly plots **Fundamental Wavelength (nm)**. The production `E=hc/lambda` mapping is correct. Diagnostic remappings produce RMSE 0.303213 for `2lambda` and 0.259692 for `lambda/2` on their overlap domains; neither supports relabeling the data.

## 19. Global complex phase test

A full 0-360-degree scan gives the best `|Re(exp(-i phi)chi)|` RMSE of 0.229700 at 161 or 341 degrees. This modest diagnostic improvement does not explain an explicitly magnitude-labeled paper curve and is not a fitted physical result.

## 20. iGamma/time convention

Changing `+iGamma` to `-iGamma` complex-conjugates chi. `|chi|` is invariant to numerical precision. No inconsistent time-convention implementation was found.

## 21. Paper digitization audit

The 45 points are ordered, nonnegative, correctly labeled, and retain zeros at 605 and 1330 nm. The simulated curve—not the experimental points—was used. The interpolation does not modify the source file. `plots/paper_digitization_overlay.png` directly checks the points against the rendered Figure 2d panel. The trace remains approximate eye-digitized data.

## 22. Feature-by-feature diagnosis

P2/P4 remain close to the DeltaE22 resonances. P1/P3 are not produced as corresponding local peaks, and the paper minima do not align with the model minima/real-part roots. Reduced pathways and `|Re|` improve global shape but do not create a defensible full reproduction. See `EXTENDED_FEATURE_DIAGNOSIS.csv`; absent extrema are reported as `nan`, not forced to window boundaries.

## 23. Root-cause ranking

The leading actionable hypotheses are geometry mismatch, BZ-cutoff convention, matrix/state provenance, and Schrödinger-Poisson mismatch. Finite-k `M(k)` remains scientifically useful but is no longer the only or automatically highest-priority explanation given the colleague report. Equation transcription, gauge, origin, wavelength mapping, and digitization corruption rank low or are ruled out by direct tests.

## 24. Professor review

The required independent review is saved separately as `PHYSICS_PROFESSOR_REVIEW_DEMO26_EXTENDED.md`. It was asked to challenge every major conclusion and answer all 16 specified questions.

## 25. Friend information needed

The checklist is in `FRIEND_REPRODUCTION_CHECKLIST.md`. The most decisive item is the exact runnable input deck **plus the exact spectrum-generation/post-processing script**. A screenshot or list of headline settings is insufficient.

## 26. Demo 25 decision

**DEMO 25 SHOULD WAIT — NEED FRIEND'S REPRODUCTION DETAILS FIRST.** Demo 25 remains useful for finite-k matrix physics, but a reproduction using M(0) would mean that a less expensive apples-to-apples convention/structure/provenance comparison should come first. If the colleague's deck and code match ours in all audited respects and the discrepancy remains, Demo 25 becomes the next justified calculation.

## 27. Final conclusion

The implementation is internally and independently consistent with the printed Eq.2 under its declared inputs. `|Re chi|` helps quantitatively but does not change the qualitative reproduction failure. No single home-laptop diagnostic recovers the paper without using an unjustified pathway reduction or convention fit. The audit shifts the immediate priority from “run more physics” to “obtain an exact reproducibility package from the colleague and reconcile structure, BZ, electrostatics, states, and matrices.”
