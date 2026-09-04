# Home-laptop chi(2) spectral-shape debug report

## Overall conclusion

The two-state chi(2) implementation is algebraically correct, sign-consistent, Hermitian, phase-invariant, and numerically converged for its stated 5 meV grid. The hybrid polynomial dispersion improves resemblance but is not a self-consistent 8-band calculation: it reuses k=0 scalar envelopes/matrix elements and produces the wrong dominant resonance. The paper is more consistent with a signed/dispersive real response plotted as a positive envelope (approximately |Re chi2|) than with |complex chi2|, but even the best local diagnostic does not put all features correctly. A true k-resolved 8-band Professional run is scientifically justified.

Best diagnostic candidate: **Hybrid |Re|, Gamma=10 meV**. Node-window minima are 578 nm (depth 0.0007) and 1269 nm (depth 0.0001); dominant peak 1044 nm; normalized RMSE 0.10998. This is a diagnostic selection, not a validated final observable.

## Ranked findings

| Rank | Experiment | Main finding | Node 1 effect | Node 2 effect | 1520 nm effect | RMSE change | Interpretation | Keep/reject | Work-laptop follow-up? |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | 01_COMPLEX_COMPONENTS | Hybrid Re has sign changes; Im fills \|chi2\|. | 577 nm crossing | 1268 nm crossing | dominant peak still 1045 nm | 0.2038 -> 0.1126 for \|Re\| | IMPORTANT | Keep as observable diagnostic | Confirm paper observable |
| 2 | 15_DISPERSION_LADDER | e2 creates a wrong 913 nm peak; h2 shifts it to 1045 nm and moves both nodes. | h2: 558 -> 584 | h2: 1201 -> 1269 | e2: 1503 -> 913; h2: 913 -> 1045 | magnitude 0.2456 -> 0.2038 after h2 | POSSIBLE PHYSICS EFFECT | Keep diagnostic only | True kp8 bands/states |
| 3 | 13_KMAX | Cutoff materially changes shape and peak. | cutoff-dependent | cutoff-dependent | 1497 -> 1045 across sweep | 0.2697 to 0.2038 | POSSIBLE PHYSICS EFFECT | Inconclusive | Justify k domain |
| 4 | 10_EQUATION_AUDIT | Literal term01-term16 exactly match the loop. | none | none | none | none | NO MEANINGFUL EFFECT | Keep validation | No |
| 5 | 12_K_RESOLVED_CANCELLATION | Coherent cross-k cancellation is strong near nodes. | coherence ratio 0.301 at 600 | coherence ratio 0.310 at 1330 | ratio 0.988 at 1520 | none | IMPORTANT | Keep coherent integral | Use kp8 integrands |
| 6 | 08_BROADENING | Gamma changes Im and depth but cannot jointly fix nodes and peak. | \|Re\| near 607 at 1 meV | \|Re\| near 1333 at 1 meV | peak remains near 1045 | best diagnostic 0.1100 at 10 meV | POSSIBLE PHYSICS EFFECT | Do not tune as fix | Use physical linewidth |
| 7 | 03_CONDUCTION_VALENCE | Large C/V contributions cancel correctly but leave finite Im. | opposed C/V | opposed C/V | C/V Im cancel strongly | none | IMPORTANT | Keep | No |
| 8 | 04_16_TERM_DECOMPOSITION | Dominant C/V pathway pairs cancel; no isolated anomalous term. | distributed cancellation | distributed cancellation | resonant pathway families | none | IMPORTANT | Keep audit tables | Use kp8 matrices |
| 9 | 14_KGRID | Nk convergence is adequate at 5 meV. | 584 nm at Nk=768 | 1269 nm at Nk=768 | 1045 nm | fine-grid 0.20236 | NUMERICAL EFFECT | Keep Nk>=384 for checks | No |
| 10 | 16_GEOMETRY_ASSESSMENT | Correct 30 nm scalar geometry exists; k-resolved kp8 does not. | no local fix | no local fix | no local fix | none | IMPORTANT | Use cached k0 states only | Yes |
| 11 | 02_ABS_ORDER | Early abs destroys coherent interference. | more filled | more filled | distorted | A remains 0.2038 | IMPORTANT | Keep A; reject B-D | No |
| 12 | 09_REAL_ZERO_GAMMA | Near-zero Gamma reveals grid-sensitive poles and displaced crossings. | not robustly 605 | not robustly 1330 | wrong peak | 0.3358 in diagnostic limit | NUMERICAL EFFECT | Reject as final | No |
| 13 | 05_MATRIX_ELEMENT_SIGNS | Negative overlap sign is preserved; strict complex use is identical. | none | none | none | none | NO MEANINGFUL EFFECT | Keep current | No |
| 14 | 06_WAVEFUNCTION_PHASE | All four consistent state sign flips are exactly invariant. | none | none | none | none | NO MEANINGFUL EFFECT | Keep current | No |
| 15 | 07_COMPLEX_CONJUGATION | Direct integrals pass Hermiticity; correction is negligible. | none | none | none | none | NO MEANINGFUL EFFECT | Keep current | No |
| 16 | 11_ENERGY_CONVENTION | Ee-Eh on one nextnano reference is correct. | none | none | none | none | NO MEANINGFUL EFFECT | Keep current | No |
| 17 | 17_NORMALIZATION_CHECK | 1/6, spin, 2pi, Nz, period, and units are constant scales. | none | none | none | none | AMPLITUDE ONLY | Does not fix shape | No |
| 18 | 00_BASELINE | Frozen licensed-state reference established. | Demo none; hybrid 584 | Demo none; hybrid 1269 | Demo 1502; hybrid 1045 | 0.2912 / 0.2038 | IMPORTANT | Keep frozen | No |
| 19 | 18_HOME_LAPTOP_SUMMARY | Best diagnostic is Hybrid \|Re\|, Gamma=10 meV. | 578 / 0.0007282 | 1269 / 0.0001015 | 1044 nm | 0.10998 | IMPORTANT | Diagnostic, not validation | Yes |

## Final decisions

1. **Missing zero mainly plotting-observable?** Partly. |Re chi2| exposes sign-change zeros that |chi2| fills, but wavelengths still disagree.
2. **Is |chi2| wrong for the paper comparison?** Likely yes; evidence favors a real/dispersive quantity, probably |Re chi2| if the published curve is shown nonnegative.
3. **Real-part sign flips at correct wavelengths?** Hybrid flips near 577 and 1268 nm at 5 meV, not 605 and 1330 nm.
4. **Remaining disagreement mainly Im?** Im explains filled magnitude nodes, but not shifted nodes or the wrong dominant peak.
5. **Missing 16-term signs?** No.
6. **C/V cancellation correct?** Yes, strong and coherent, with finite residual Im.
7. **Matrix signs/phases preserved?** Yes.
8. **Global wavefunction phase invariant?** Yes to numerical precision.
9. **Does Gamma explain filled nodes?** Partly, not fully; it does not repair feature positions.
10. **Does k integration explain nodes?** Cross-k cancellation is important and correctly coherent, but current dispersions do not reproduce paper nodes.
11. **Are kmax/Nk converged?** Nk is converged at 5 meV; kmax is a physically unresolved model choice and materially changes shape.
12. **Most influential non-parabolic band?** e2 creates the wrong 913 nm dominant resonance; h2 then moves that peak to 1045 nm and moves both node regions, producing the largest RMSE improvement. e1 is nearly neutral and h1 is a modest correction.
13. **Reproduce ~605 nm node?** No robust complex-magnitude node.
14. **Reproduce ~1330 nm node?** No robust complex-magnitude node.
15. **Reproduce dominant ~1520 nm resonance?** No.
16. **Final normalized RMSE?** 0.10998 for the best diagnostic |Re| candidate; original |chi2| values remain Demo 21 0.29124 and hybrid 0.20377.
17. **Single largest discrepancy?** The finite-k band/state model puts dominant oscillator strength near 1045 nm instead of 1520 nm.
18. **New nextnano++ Professional run justified?** Yes: use the exact 30 nm geometry and obtain tracked k-resolved 8-band states/spinors and preferably k-dependent matrix elements.
