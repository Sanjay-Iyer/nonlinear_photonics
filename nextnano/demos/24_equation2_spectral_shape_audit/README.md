# Demo 24 - Equation 2 spectral-shape audit

Demo 24 is a solver-free diagnostic of the copied Demo 23 Professional results. It keeps Demo 23D's tracked energy dispersions, `M(k)=M(0)`, 5 meV broadening, 16 pathways, electron-minus-heavy-hole sign, `Nz=1/(30 nm)`, spin degeneracy, wavelength grid, and radial measure unchanged for the baseline.

The analysis compares the complex spectrum and its magnitude with the existing 45-point eye digitization of Ramesh et al. Fig. 2d. The digitized curve is not author data and the paper plot is explicitly `|chi^(2)|`, so a real-part sign crossing is not called a paper-like complex node unless the imaginary part is also small.

No function in this directory launches nextnano. Missing finite-k matrix data raise `ProfessionalDataRequired` and are recorded as `REQUIRES_NEW_PROFESSIONAL_DATA`.

Run on the home laptop with the repository's NMIP environment:

```powershell
& 'C:\Users\iyer95\miniconda3\envs\NMIP\python.exe' .\nextnano\demos\24_equation2_spectral_shape_audit\run_demo24.py
& 'C:\Users\iyer95\miniconda3\envs\NMIP\python.exe' .\nextnano\demos\24_equation2_spectral_shape_audit\run_demo24.py --tests
```

Outputs are written only to `outputs/` and `demo_results/demo24/`; the copied Demo 23 raw data remain read-only inputs.

## Demo 24N - spectral-feature causal sensitivity debugger

`causal_sensitivity.py` adds controlled one-at-a-time perturbations that ask which physical
quantity actually controls each paper feature. Every perturbed spectrum is labelled
`DIAGNOSTIC PERTURBATION - NOT A PHYSICAL/FITTED MODEL`. Nothing here is fitted to the paper and
nothing changes Demo 23 production physics.

The perturbations run through an **instrumented mirror** of the production adapter
`chi2_22.chi2_from_k_inputs`, needed because the production engine cannot scale a single pathway
numerator or retain the k-resolved integrand per pathway. `assert_matches_production` proves the
mirror reproduces the production spectrum to about 1e-14 relative before any perturbation is
trusted, and the same check runs as a test.

What it measures:

| Test | Output |
|---|---|
| feature traceback: dominant pathway, k region, denominators, mechanism | `FEATURE_CAUSAL_TRACEBACK.csv` |
| resonance reachability, including the bound-state ceiling at the barrier edge | `RESONANCE_REACHABILITY.csv`, `BAND_EDGES.json` |
| one- and two-photon resonance band edges, physical vs truncation | `RESONANCE_BAND_EDGES.csv` |
| subband energy ladder, +/-10 meV, one state at a time | `ENERGY_FEATURE_SENSITIVITY.csv` |
| `dLambda/dE` and node-depth derivatives, with direction statements | `ENERGY_FEATURE_DERIVATIVES.csv`, `ENERGY_SHIFT_DIRECTION_STATEMENTS.csv` |
| single-pathway numerator scaling, 0.90-1.10 | `PATHWAY_AMPLITUDE_SENSITIVITY.csv` |
| opposing contributions and cancellation ratio at each paper node | `NODE_CANCELLATION_SENSITIVITY.csv` |
| complex phase robustness probe | `PHASE_SENSITIVITY.csv`, `NUMERATOR_PHASE_CONTENT.json` |
| dominant k region and whether the integrand is truncated | `FEATURE_K_REGION_SENSITIVITY.csv` |
| does a model peak track the k cutoff? | `CUTOFF_ARTIFACT_TEST.csv` |
| does the parabolic extrapolation survive the longer 0.125 pi/a case? | `EXTRAPOLATION_VALIDATION.csv` |
| assembled per-feature diagnosis and statements | `SPECTRAL_FEATURE_CAUSAL_DIAGNOSIS.csv`, `FEATURE_CAUSAL_STATEMENTS.md` |

Figures 21-26 cover peak and zero energy sensitivity, node depth versus pathway amplitude at both
paper zeros, the feature-to-parameter heatmap, and the per-feature causal traceback diagram.

### Two cautions when reading these results

The perturbations measure **sensitivity**, not proof. That a 10% change in one pathway numerator
opens a node shows the node is reachable in numerator space; it does not show that `M(k)` is
wrong by 10%. A single-pathway rescaling also breaks orthonormality and sum rules that a real
`M(k)` would respect, so it is an efficient but unrepresentative way to manufacture a residual.
The reachability and cutoff-artifact results are stronger, because they are exclusions.

The numerator **phase is not a free parameter** in this implementation: overlaps and z matrix
elements are real, so every pathway numerator phase is pinned to 0 or pi. The phase scan is kept
only as a robustness probe and carries little diagnostic weight.

## Reviews

Two independent reviews are kept separate rather than merged:

- `professor_review/PHYSICS_PROFESSOR_REVIEW.md` - review of the primary Demo 24 analysis, written before 24N existed.
- `professor_review/PHYSICS_PROFESSOR_REVIEW_24N.md` - review of the causal study, which corrects the first review's "extend kmax" recommendation and disagrees with the primary analysis's top-ranked cause.

`outputs/DEMO24_FINAL_REPORT.md` section 23 records the disagreements without resolving them silently.

## Tests

```powershell
& 'C:\Users\iyer95\miniconda3\envs\NMIP\python.exe' -m pytest .\nextnano\demos\24_equation2_spectral_shape_audit\tests -q
```

`tests/test_demo24n.py` covers the mirror-versus-production equality, pathway ordering, k-integrand
closure, one-at-a-time perturbation scoping, window-edge detection, band-edge bookkeeping,
cutoff-artifact classification, and the guarantees that no routine invents finite-k data, launches
a solver, or writes to Demo 23.
