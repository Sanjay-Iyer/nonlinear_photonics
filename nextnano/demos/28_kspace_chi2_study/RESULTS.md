# Demo 28 scientific results

## Status and scope

28A–28J have cached-data implementations and numerical outputs. 28I is necessarily partial: only k=0 spinors/composition were archived. No new Professional solve was launched. A denser provisional work-machine extension is prepared, not physically approved or executed.

The resumed work retained the existing architecture and numerical baseline. Existing A/B results were rerun, then the already-partial response/causality/state work was checked and completed with extended probes, grid controls, provenance checks, figures and documentation. The package is untracked in the current repository, so `git diff` alone does not enumerate it; source manifests capture its actual code. Historical demos were not edited.

## 28A — confirmed by calculation

Settings: Gamma5meV, two electron/two historical valence branches,16pathways,301native k nodes through0.555714439232nm^-1,400–1850nm at1nm, frozen single-band matrices,8-band dispersion shifts, spin2, period30nm,r=.751nm.

| Check | Result |
|---|---:|
| Max complex error against saved historical spectrum | 6.9711344e-10 pm/V |
| Regression tolerance | 1e-8 pm/V |
| Full28B cutoff versus28A | exactly0 pm/V |
| Re zero1 | 714.0283286 nm |
| Im at zero1 | +27.2789914 pm/V |
| Re zero2 | 1437.4792785 nm |
| Im at zero2 | -52.9968366 pm/V |
| Integrand reintegration discrepancy | 7.00e-13 pm/V |

**Supported interpretation:** cleanup preserved the historical complex calculation. **Not established:** agreement with every paper modeling assumption or absolute experimental scale.

## 28B — native-range cutoff and shells

Tested f=0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.10 in kmax=f*pi/a, a=.565325nm. Included counts are31,61,91,121,151,181,211,241,271,301. Actual upper limit spans0.0555714439–0.555714439232nm^-1. Every case verifies all samples<=request; endpoint weights are recalculated.

Increasing the cutoff changes signed amplitudes and the separation of spectral features. Re zeros move from752.0269/1504.0793nm at0.01 to714.0283/1437.4793nm at0.10. The global absolute-Re maximum is not a reliable branch label (it switches between nearby extrema at small cutoffs). Global absolute-Im maximum moves1504→1496nm over this range; this alone hides the movement of the other lobe.

At1550nm, Re changes0.60623→26.47024pm/V and Im -0.055998→+0.797334pm/V. Im changes sign as competing shell/pathway contributions are added; it is not simply a monotonically growing absorption curve.

The cumulative diagnostic uses adjacent radial trapezoids, not sliced full-grid weights. Shells sum to the direct response with error2.37e-13pm/V at the five probes. For the last10% of baseline k range (0.09→0.10pi/a), define tail ratio=abs(complex tail change)/max_k abs(cumulative chi). With a stated1% diagnostic threshold:

| Wavelength nm | Tail deltaRe pm/V | Tail deltaIm pm/V | Tail ratio | Below1%? |
|---:|---:|---:|---:|---|
|540|+0.33147|+0.003900|21.77%|No|
|760|-1.53010|-0.053120|5.87%|No|
|1080|-1.42369|-0.003306|19.23%|No|
|1520|+2.36894|+0.031612|5.17%|No|
|1550|+2.19591|-0.049519|8.29%|No|

**Confirmed:** saturation is not demonstrated in this model at the retained endpoint. **Supported mechanism:** matrices are frozen, so matrix growth is excluded here; radial measure and changing detunings produce continuing signed shell contributions. The shell curves show sign changes and resonant enhancements at some probes, whereas off-resonant Re tails continue accumulating. This is more specific than assuming all high-k change has one cause.

## 28C — actual extended cached data

`nextnano/raw_extended/` contains a successful Professional archive with301points through0.125pi/a=0.69464304904nm^-1, spacing0.00231547683013nm^-1. Baseline spacing is0.00185238146411nm^-1. No extrapolated dispersion is substituted.

Nested cutoffs on the **same extended grid** are0.05,0.10,0.1125,0.125pi/a, with121,241,271,301nodes. This isolates cutoff effects on that fixed sampling lattice. The table shows0.10→0.125 on that grid:

| Probe nm | Re at0.10 | Re at0.125 | Im at0.10 | Im at0.125 |
|---:|---:|---:|---:|---:|
|540|1.52254|2.64699|0.016318|0.031003|
|760|-26.01048|-30.25628|1.634072|1.696695|
|1080|-7.40516|-11.77790|-0.002811|-0.020879|
|1520|45.73757|51.57522|-3.052318|-3.191271|
|1550|26.47017|31.57391|0.797340|0.679070|

Units are pm/V. The last0.1125→0.125 increment still changes Re1550 by+2.46661pm/V and Im1550 by-0.05494pm/V. There is no demonstrated physical convergence at0.125 either. Full continuous extended-grid cumulative/shell arrays are saved in28H, separate from baseline28B arrays.

The last10%-of-k tail ratios at the extended endpoint are23.50%,7.00%,19.90%,5.44%,7.81% at540/760/1080/1520/1550nm. All exceed1%; this quantifies continuing response without asserting behavior beyond the archived range.

Fixed, named feature windows with interior-extremum checks show:

| Feature |0.10pi/a|0.125pi/a|Shift|
|---|---:|---:|---:|
|short-wave positive Re maximum|687nm,30.699pm/V|658nm,35.062pm/V|-29nm|
|long-wave negative Re minimum|1374nm,-65.855pm/V|1316nm,-76.786pm/V|-58nm|
|moving negative Im lobe|1398nm,-54.853pm/V|1353nm,-58.993pm/V|-45nm|

These are sampled1nm extrema, not sub-nm peak fits. The global absolute-Im maximum switches from the1496nm lobe to the1353nm lobe: calling that a single143nm continuous shift would be misleading. Window tracking distinguishes this switch. Full zero locations and Im at zeros remain in each case's metadata.

## 28H — sampling versus physical range

At fixed0.10pi/a, native-node subsampling gives:

|Nk|Max Re error vs301 pm/V|Max Im error vs301 pm/V|
|---:|---:|---:|
|31|7.9033|7.4996|
|51|2.5151|1.9474|
|101|0.51389|0.33752|
|151|0.18823|0.12506|
|301|0|0|

The independently solved201node archive differs from301 by0.077847(Re),0.051871(Im)pm/V maximum; its complex RMS difference is0.005341pm/V. Comparing the extended-grid241node truncation at the same endpoint against baseline301 yields max errors0.034934(Re),0.023299(Im)pm/V, complex RMS0.002400pm/V.

**Confirmed:** finite-grid differences at this endpoint are small compared with the many-pm/V cutoff/feature changes. **Not established:** an infinite-density bound, particularly for0.1meV linewidth or newly extended resonances. No spline-refined energies are passed off as new solver samples.

The constant-integrand radial area is g_s*kmax^2/(4pi), verified to roundoff. Weights carry nm^-2; endpoint dk factors are halves. The angular2pi from isotropy cancels one factor in(2pi)^2. The actual electronic data is a one-direction path, not a solved2Dangular integral.

## 28D/E — source of Im and linewidth behavior

All baseline O,ze,zh and complete invariant pathway numerators have exactly zero imaginary part. Real-representation control changes chi by0pm/V. Electron+hole versus total error is3.39e-13pm/V. Thus iGamma explains the source of complex response in this baseline; interference controls its resultant shape.

AtGamma5meV max absolute Im of electron/hole/total groups is888.029/831.540/57.898pm/V. These maxima do not necessarily occur at the same wavelength. Groups depend on the chosen growth-coordinate origin; the full sum is origin-invariant. They are not separately measurable absorption coefficients.

Gamma cases0.1,0.5,1,2,5,10,20meV retain the same energies/matrices. For each wavelength, the smallest actual one-/two-photon detuning over the retained transitions and k is calculated. Near<=25meV and off>=100meV masks stay fixed acrossGamma. Ratio plots mask Re<=0.001maxabs(Re) before division.

|Expectation at5meV|Quantitative evidence|Outcome|
|---|---|---|
|Re dominates off resonance|L2(Im)/L2(Re)=0.014384;100% of736off samples Re-dominant|SUPPORTED on defined domain|
|Im dominates near resonance|L2 ratio1.155858, but only35.4% of500near samples Im-dominant; safe median ratio0.122503|PARTIAL, not pointwise universal|

At0.1meV, off-resonance L2 ratio falls to0.000287816 (~50x smaller). Near-pole spikes become poorly resolved on the existing grid. **Supported:** Im diminishes away from poles asGamma decreases. **Unresolved:** the converged zero-linewidth distributional limit. The apparent sampled lobe widths in CSV are not universal Lorentzian linewidths of a many-pathway response.

The initial filled-valence occupation assumption is compatible with perturbative complex response without propagating carrier populations. This does not establish measured nonlinear absorption. See `PAPER_AUDIT.md` and `PHYSICS_GUIDE.md`.

## 28G — pathways and resonances

All16pathways are saved. The largest raw norms belong to C111,V111,C222,V222. Define cancellation=1-||sum terms||_2/sum||individual terms||_2 over the stated wavelength grid. Overall cancellation is about97.19%; C111/V111 cancel99.7118%, C222/V22281.1061% by that metric. This is a norm diagnostic, not an absorbed-power fraction.

The diagonal-z summed contribution has norm1.0293times the total, and off-diagonal sum0.14768times the total. Diagonal terms dominate this baseline but off-diagonal terms are not identically zero; cancellation claims are wavelength/model-dependent. Coordinate-origin dependence of individual terms prevents treating their large magnitudes as independent observables.

The resonance map plots hc/T_nm(k) and2hc/T_nm(k), explicitly using the same transition arrays as Eq2 denominators. Resonance curves move to shorter wavelength as these retained transitions increase with k, explaining why adding higher-k shells can move a lobe's edge/peak. The final sum also depends on interference, so a denominator map does not uniquely assign every summed peak.

## 28F — exact scope of KK conclusions

Analytic causal-oscillator benchmark: PASS. Uniform signed energy, dE=.001eV, half-width8/16/32eV; positive-iGamma convention corresponds to inverse exp(+iomega t). Same-direction degenerate SHG path permits the documented1Drelation; no wavelength Hilbert transform was used.

The rational Eq2 expression passes the central full-line KK test: broadest-domain relative RMS errors1.61672e-5(Re),1.33379e-5(Im), below.001. Edge relative errors are poor and explicitly reported. Direct unchanged continuation violates real-field F(-E)=F(E)* with normalized maximum defect0.99717.

**Mathematical expression:** PASS at stated tolerance. **Complete physical real-field susceptibility:** INCONCLUSIVE. Missing negative-frequency/completion and paper sign conventions must be resolved; do not relabel the successful mathematical transform as absorption validation or proof that all physical terms are present. Details and primary sources: `CAUSALITY_AUDIT.md`.

## 28I — available state evidence

k=0 e1/e2 CB fractions96.26%/93.10%; h1 HH100%; historical h2 LH97.58%, HH0%. Thus the historical8-band source is not the paper's stated two-HH truncation. Only1of301k nodes has archived composition/envelopes; zero adjacent-k overlap comparisons are possible. Smooth fixed-column energies do not establish physical branch identity, bound character or model validity at high k. No certified high-k validity interval is claimed.

## 28J — comparison, not convergence

|Model/cutoff|nRMSE abs(Re)|nRMSE abs(chi)|
|---|---:|---:|
|baseline0.10|0.237873|0.262391|
|extended grid0.10|0.237871|0.262388|
|extended grid0.1125|0.234574|0.271850|
|extended grid0.125|0.226310|0.279161|

Each absolute curve and paper is normalized to its own maximum. The signedRe/Im plot instead shares one model factor. Baseline correlations are0.30963(absRe),0.24756(magnitude); both show significant disagreement. Among native28Bcases, absRe fits best at0.10; magnitude at0.07(nRMSE0.251241). Across the additional tested extended-grid cases, best absRe is0.125. **No physically converged cutoff has been established.**

The baseline nearest-prominent-paper-feature mean errors are115.75nm(peaks),106.33nm(minima) forabsRe, versus133.25/192nm for magnitude. These are nearest-neighbor diagnostics, not one-to-one physical assignments; digitization and sparse paper minima limit precision. The manuscript's exact plotted observable cannot be deduced from this comparison alone.

The previous0.066nRMSE cutoff plot is a different extrapolated calculation, not this native mixed-model baseline. Better fit under a different cutoff is not proof of saturation.

## Verification and limitations

See `VALIDATION.md` for exact tests/commands and visual QA. Generated PNG/SVG plots use the saved numerical arrays; all major figures were visually inspected, including the unresolved narrowGamma spikes and KK symmetry failure. Raw and code manifests make their origins explicit. The isolated runtime dependency audit passes forA/B and static imports are package-local/installed dependencies.

Independent specialist work checked primary paper claims, causality and state/response evidence; those agents saved code/results but were interrupted by account limits before a final end-to-end reviewer signoff. Final integration checks were performed in this task. Do not represent that as an external scientific peer review.

The next licensed-machine calculation is a provisional0.15pi/a,901node run with retained finite-k state outputs. It is a data-acquisition proposal, not approval of the model at that endpoint. See `WORK_LAPTOP_RUN.md` and the specific unresolved questions in `NEXT_QUESTIONS.md`.
