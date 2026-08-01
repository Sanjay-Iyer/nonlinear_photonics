# Experiment v3 — work-laptop verification sequence

**Status: prepared, not launched.** Nothing here runs automatically. Each tier
is a gate: the next one is enabled only when the previous passes.

Prerequisites, all of them:

1. the v2 reanalysis checklist has passed (`WORK_LAPTOP_REANALYSIS.md`);
2. Stage 5 has run and has decided the barrier lower bound
   (`STAGE5_VALIDATION_PLAN.md` §2.1, §2.5);
3. the v3 configuration exists with `experiment_state_dir:
   demo13_ax_experiment_v3` — a **new** directory, never v2's;
4. the git working tree is clean.

Total cost if every tier runs: **5 + 7 + 26 = 38 licensed evaluations**, plus
the 12-run paired grading comparison.

---

## Tier 1 — deterministic premium cases

Five fixed decks, no Bayesian optimization, no proposal machinery. This tier
tests **geometry realization and the deck→solver→extraction path under the v3
bounds**, nothing else.

| Case | Design | What it proves |
|---|---|---|
| **T1-a** | Demo 11 abrupt reference (`s1_ref`) | The reference still reproduces under v3 numerics (0.05 nm mesh). Any change here invalidates every comparison. |
| **T1-b** | v2 trial 12 geometry: s ≈ 0.4603, barrier 0.5 nm, abrupt | Bridges v2 and v3. Run at **both** meshes. If the objective differs between 0.10 and 0.05 nm, v2's observations are not comparable to v3's and warm-starting is definitively ruled out. |
| **T1-c** | Thinner-barrier abrupt at the new lower bound (0.85 nm, or 0.565 nm if Stage 5 licensed it) | The new bound is constructible and numerically resolved. Count the mesh cells across the barrier explicitly. |
| **T1-d** | Genuinely non-zero **linear** grade, realized width ≥ 0.80 nm, verified | A grade that survives mesh snapping actually gets built. Check `realized_grading_thickness_nm` in the ledger, not the requested value. |
| **T1-e** | Genuinely non-zero **sigmoid** (or cosine) grade, same width | A non-native profile realizes through the staircase fallback. Demo 12's native-vs-staircase agreement check applies. |

**Acceptance for Tier 1:**

- 5/5 complete with no mechanical solver failure;
- every realized alloy profile matches its requested profile within
  `native_staircase_composition_rms_tolerance: 0.02`;
- T1-d and T1-e report `realized_grading_thickness_nm >= 0.80` and
  `collapsed_to_abrupt: false` — **if either collapses, the minimum-resolvable
  derivation in `EXPERIMENT_V3_DESIGN.md` is wrong and must be redone before
  Tier 2**;
- T1-c reports ≥ 10 mesh cells across the barrier;
- T1-b either matches its v2 value within 2 % or is recorded as not comparable.

## Tier 2 — short Bayesian optimization

```yaml
bo:
  num_initial_trials: 4
  num_iterations: 3
  batch_size: 1
```

Seven evaluations. This tests **the loop**, not the science: proposal,
preflight, deduplication, Sobol → MBM transition, checkpointing, ledger,
reporting.

Stratification must be forced even at this size: **2 abrupt and 2 graded**
initial trials, so the graded branch is exercised before the model takes over.

**Acceptance for Tier 2 — every item, not a majority:**

| Requirement | How to check |
|---|---|
| Valid abrupt **and** graded evaluations completed | ledger: ≥ 1 of each with `status: completed` |
| Genuine non-zero grading | ≥ 2 trials with `realized_grading_thickness_nm >= 0.80` and `collapsed_to_abrupt: false` |
| Sub-resolution grades rejected before the solver | any rejection carries `rejection_reason` naming the minimum resolvable width, and `solver_launched: false` |
| Transition to MBM | `generation_method` is `Sobol` for trials 0–3 and `MBM` for 4–6 |
| No duplicate | `duplicate_proposals: 0`, or duplicates rejected without a solver call |
| No invalid geometry reaching nextnano | `preflight_invalid_proposals` all have `solver_launched: false` |
| Finite objectives | every completed trial has a finite `relative_chi2_at_target_wavelength_abs` |
| Correct feasibility | `feasibility_summary.json` agrees with a hand-check of the four constraints on at least one trial |
| State-tracking confidence | ≥ 0.8 on every completed trial; investigate any `ambiguous: true` |
| Correct reporting | all nine surrogate outputs populated with finite values; `analysis_model_reconstruction.json` reports a fitted adapter |
| No BO iteration consumed by a rejection | `invalid_preflight_counts_as_bo_iteration: false` honoured in `budget_accounting.json` |

**A Tier 2 run that produces zero genuinely graded trials is a FAILURE**, even
if every trial completes. That outcome is exactly what v2 did, and repeating it
would waste the campaign.

## Tier 3 — the full campaign

Enable **only** after Tiers 1 and 2 pass in full.

```yaml
bo:
  num_initial_trials: 12    # stratified: 6 abrupt, 6 genuinely graded
  num_iterations: 14
  batch_size: 1
```

26 evaluations, then the **paired abrupt/graded comparison stage**: the top 3
abrupt geometries re-run with each of the 4 profiles at a genuine non-zero
grade (12 runs). That paired stage is the only part of the whole programme that
can answer whether grading helps, because it is the only part that changes one
variable at a time.

**Do not draw a grading conclusion from the BO campaign alone**, however many
graded trials it contains. A scattered search varies four things at once.

## Stop conditions — abandon the tier and re-plan

- any mechanical solver failure in Tier 1;
- a realized profile that fails Demo 12's composition validation;
- a graded proposal that reaches nextnano with a sub-resolution width;
- Sobol→MBM transition not occurring by the configured iteration;
- state-tracking confidence below 0.8 on more than one trial, or any label
  permutation against the fixed anchor;
- the v3 experiment directory turning out to be v2's — check before starting:

```powershell
Get-ChildItem .\nextnano\results\demo_runs\13_ax_bayesian_optimization_graded_acqw\ -Directory | Select-Object Name
```
