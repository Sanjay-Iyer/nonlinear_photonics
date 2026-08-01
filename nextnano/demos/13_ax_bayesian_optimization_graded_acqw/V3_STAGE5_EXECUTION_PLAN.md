# v3 Stage 5 execution plan — prepared, NOT launched

**t0021 is the best feasible design found. It is not an optimum.** Nothing in
this plan assumes otherwise, and no wording anywhere may call it one until
Stage 5 passes.

Licensed execution waits until all local phases pass and the work-laptop
reanalysis checklist is green.

---

## Designs under test

| Role | Trial | Why |
|---|---|---|
| Best feasible, on the barrier bound | **t0021** | s = 0.387565, barrier 0.85 nm, abrupt, χ² 0.411027, detuning −13 nm |
| Second feasible | **t0017** | independent check that the *ranking* is stable |
| Feasible Sobol reference | **t0005** | not model-selected, so it tests the pipeline rather than the model |
| Near-feasible boundary case | **t0022** | detuning −16 nm, just outside the 15 nm bound. Resolves whether the boundary is sharp or the model is wrong |

Plus, where a graded case is needed, the five genuine graded trials
(t0003 sigmoid, t0004 cosine, t0008 erf, t0011 erf, t0019 erf) — for **alloy
profile verification only**, since none was feasible.

## Acceptance thresholds — stated before execution

| Check | Pass |
|---|---|
| mesh convergence | |Δχ²| < 2 % and |Δdetuning| < 1 nm between 0.05 and 0.025 nm |
| state identity | no label permutation; confidence ≥ 0.8; margin ≥ 0.15 |
| state-count convergence | |Δχ²| < 2 % from 4 → 6 states |
| padding convergence | |Δχ²| < 1 %; max boundary probability < 1e-3 throughout |
| local refinement | no neighbour exceeds the centre by more than the mesh-convergence tolerance |
| fabrication | < 10 % relative drift per perturbation, reported per parameter |
| alloy profile | composition RMS within `native_staircase_composition_rms_tolerance` (0.02) |

---

## A. Mesh gate — run this alone, first

**2 runs.** t0021 at 0.025 nm and 0.10 nm, compared against the recorded 0.05 nm.

At 0.85 nm the barrier spans 34 / 17 / 8 cells respectively.

**Stop the whole plan if** χ² moves > 2 %, detuning moves > 1 nm, the tracked
state labels permute, or QC changes. Everything downstream — the ranking, the
grading question, the barrier bound — is conditional on this, and it costs 2
runs to find out.

## B. Local parameter refinement — 14 runs

Around t0021, at the converged mesh:

- **barrier**: 0.85 (recorded), 0.90, 0.95, 1.05, 1.25 nm.
  ⚠️ Do **not** go below 0.85 nm. That is the justified lower physical bound
  (3 monolayers); probing below it would answer a question the model cannot be
  trusted for. If the objective still rises at 0.85 nm, that is a **finding**,
  not an invitation to extend the bound.
- **asymmetry**: 0.3775, 0.3825, 0.387565 (recorded), 0.3925, 0.3975, plus
  0.36 and 0.40 for reach.

The asymmetry spacing is deliberately fine: t0021 is at −13 nm detuning and
t0022 at −16 nm, so the feasible boundary lies within this range and a coarse
grid would step over it.

Every case carries the paired tracking diagnostic from §E.

## C. State-count convergence — 8 runs

t0021 and t0017 at 4 and 6 requested states, each at two meshes. Demo 11's
registry still records its Eq. 2 state-window convergence as **FAILED**, and
Demo 13 inherits that extraction unchanged. This is the check that says whether
v3's numbers inherit the problem.

## D. Domain-padding convergence — 6 runs

t0021, t0017, t0022 at 0 and 4 nm outer padding. Compare energies and both
boundary-probability fields — `maximum_boundary_probability` and
`total_boundary_probability` are different quantities and must not be
interchanged.

## E. State-tracking audit — no extra solver runs

Re-tracking only, on stored output:

1. re-assign every design against the **fixed anchor** (`reference_abrupt`)
   instead of the nearest completed neighbour;
2. compare with the nearest-neighbour assignment recorded during the campaign;
3. sign-align wavefunctions before overlap;
4. report confidence, margin and `ambiguous` for both strategies.

**Any label permutation invalidates that trial's metrics**, because the
extraction then summed the wrong pair of states. t0021 is the highest risk: the
thinnest barrier gives the strongest tunnel coupling and the most nearly
degenerate doublet.

## F. Fabrication perturbations — 12 runs

t0021 and t0017: barrier ±0.05 nm, wells ±0.2 nm, Al fraction ±0.01.

⚠️ **Report each perturbation with its own fractional magnitude.** ±0.05 nm is
5.9 % of a 0.85 nm barrier; ±0.2 nm is 2.8 % of a 7.1 nm well. Averaging them
into one robustness score hides the sensitivity that matters. The
`perturbation_fraction_of_nominal` and `relative_drift_per_fractional_change`
columns exist for this.

Grading perturbations are **skipped** on t0021 and t0017: both realize 0 nm, and
adding a grade changes the device, not a tolerance.

## G. Alloy-profile verification — 0 solver runs, needs the raw bundle

Required for all five genuine graded trials. Compare requested against realized
composition using Demo 12's procedure.

⚠️ **This cannot run until the supplemental raw bundle is transferred.** Until
then, "t0019 realized a 0.86 nm erf grade" rests on the geometry calculation and
has no solver evidence behind it.

---

## Cost and isolation

**42 licensed runs**, gated: 2 (mesh) → 14 (refinement) → 8 (states) → 6
(padding) → 12 (fabrication). Stop at any failed gate.

Stage 5 writes into `<experiment_state_dir>/runs/v*` and `r*` and appends
validation rows. It must **never** complete, fail or abandon an optimization
trial. Capture the state manifest before and after, and confirm all 23 terminal
records are unchanged.

⚠️ Isolation gap to close before launching: Stage 5 currently shares the v3
experiment directory. Point it at `demo13_ax_experiment_v3_stage5` — or verify
the manifest afterwards — so a Stage 5 bug cannot touch the optimization ledger.

## Questions Stage 5 must answer

1. Does the ranking t0021 > t0017 > t0005 survive mesh and state-count refinement?
2. Does t0021 remain best feasible?
3. Is 0.85 nm numerically resolved (34 vs 17 cells)?
4. Do state identities survive an order-independent anchor?
5. Where exactly is the detuning boundary between −13 and −16 nm?
6. Does the response survive fabrication-sized perturbations, reported per parameter?
7. Do the five graded trials' realized profiles match their requests?
8. How wrong was the surrogate at t0022 — the cheapest measure of model trust.
