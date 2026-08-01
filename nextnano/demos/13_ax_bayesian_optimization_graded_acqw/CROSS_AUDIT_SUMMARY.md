# Cross-audit summary — Demo 13 hardening pass, 2026-08-01

Independent review comparing `PHYSICS_AUDIT.md`, `SOFTWARE_AUDIT.md` and
`AX_BO_AUDIT.md`, looking for contradictions between them and for anything all
three missed.

| Auditor | Verdict |
|---|---|
| Physics and materials | PASS WITH WARNINGS |
| Python / software | PASS WITH WARNINGS |
| Ax / BoTorch | PASS WITH WARNINGS |
| **Combined** | **PASS WITH WARNINGS** — no FAIL, so the phase may close |

---

## 1. Contradictions found and resolved

### C-1. "Is the boundary constraint fine or broken?" — RESOLVED

The Ax audit (§5) calls `maximum_boundary_probability` an uninformative modelled
constraint that should be dropped from the GP. The physics audit (§5) calls the
metric correctly defined and correctly interpreted. Read side by side these look
opposed.

**Resolution: both are right about different things, and neither statement was
precise enough on its own.** The *metric* is physically correct and correctly
distinguished from a total-over-states quantity. Its use as a **modelled**
constraint is what is wrong, and only because it happens to be constant across
these particular observations. Both audits have been read as agreeing that: the
metric stays, the constraint stays enforced outside Ax, and only its GP
membership changes in v3. No code change in this pass — altering the modelled
outcome set would make v2's checkpoint inconsistent with the configuration that
produced it.

### C-2. "Is the code safe against zero solver calls, or is that unproven?" — RESOLVED

The software audit (§12) originally marked zero-solver-calls **PASS** on purely
structural grounds and then warned it was not tested end-to-end, which read as
stronger than it was.

**Resolution: the gap was closed rather than argued about.** A full
`analyze_existing_results` run was executed on the home laptop against a
16-trial experiment: exit 0, zero `Executing` lines, zero `Generated new trial`
lines, `experiment_state_unchanged: true`. All three documents now say the same
thing, including the one remaining qualification — the run used the *synthetic*
16-trial experiment, because v2 is not on this machine, so the identical check
must still be repeated against v2 on the work laptop.

### C-3. Grading evidence — three different thresholds — RESOLVED

The physics audit rejects profile rankings from single samples. The Ax audit
flags risk #22 as handled by `profile_ranking_supportable`. The v3 design sets a
threshold of ≥ 3 genuine trials for ≥ 2 profiles.

**Resolution: consistent, and the code is the authority.**
`grading13.evidence_counts` implements exactly the threshold the v3 design
assumes, and the physics audit's rejection is the same rule stated in prose. No
divergence.

## 2. Agreements worth recording

All three audits independently reached the same conclusion on three points,
which raises confidence that they are real rather than one reviewer's hobby-horse:

1. **The slice-encoding bug (A1) is the most serious finding of the pass.** The
   software audit found it as a type-confusion between canonical designs and
   search points; the Ax audit found it as "the surrogate was queried at one
   point 625 times"; the physics audit found it as "a reader would conclude the
   surrogate saw no grading dependence". Same defect, three symptoms. It was
   *silently wrong output*, not missing output, which makes it worse than the
   defect the brief was written to fix.

2. **0.5 nm is a bound, not an optimum.** Physics §6 (1.77 monolayers, 5 mesh
   cells, below the interdiffusion scale); Ax §7 (an optimizer at a bound is
   reporting a binding constraint); v3 design Limitation A.

3. **Parameter importance is the output most likely to be over-read.** Physics
   (it is not physics), Ax §10 (negative Sobol indices prove non-convergence),
   software §5 (the caveat must quote trials, not metric rows).

## 3. What no single auditor caught alone

**The `observations_used = 64` inflation (A17).** The Ax auditor spotted that
`lookup_data()` returns one row per (trial, metric) and that 16 trials × 4
metrics is 64. The software auditor spotted that this number is interpolated
into the parameter-importance caveat text. Neither alone would have mattered
much; together they meant the report would have said "with 64 observations this
ranks what the model leans on" about a 16-trial study — a fourfold overstatement
of the evidence, in the very sentence written to prevent overstatement.

Fixed before release: `observations_used` counts trials,
`observation_rows_used` counts rows.

## 4. The final-audit trap, checked deliberately

The brief's risk #47 — *"the final AI audit accepts implementation tests but
misses a physics flaw"* — is the one this document exists to catch. The tests
prove the code does what it claims. They cannot prove the claims are the right
ones. Three places where green tests coexist with an unresolved physics problem:

| Green test | Unresolved physics |
|---|---|
| `test_predictive_adapter_is_reconstructed...` passes | The surrogate is fitted to 16 points over 4 mixed dimensions. It is *reconstructible*, not *trustworthy*. Its uncertainty is not calibrated. |
| `test_best_trial_is_included_and_ranked_first` passes | Ranking t0012 first is correct **given the objective**. Whether the objective is converged with respect to mesh and state count is untested and, per Demo 11's own registry entry, doubtful. |
| `test_graded_proposal_that_snaps_to_zero_is_physically_abrupt` passes | Correctly excludes collapsed trials from profile evidence — which leaves v2 with too few genuine graded trials to answer the grading question at all. The test makes the ignorance visible; it does not remove it. |

None of these is a code defect. All three are reasons the demo is
`licensed_optimization_completed_validation_pending` and not
`physically_validated`.

## 5. Required before the next phase

No auditor reported FAIL, so this phase closes. Carried forward:

| # | Item | Owner | Blocks |
|---|---|---|---|
| 1 | Confirm the v2 directory name on the work laptop | work laptop | reanalysis |
| 2 | Repeat the zero-solver-call `console.log` check against v2 itself | work laptop | Stage 5 |
| 3 | ~~Clamp grading perturbations at zero; report barrier sensitivity separately~~ — **done in this pass**: `robustness_cases` no longer perturbs the grading of a design that realizes none, and `perturbation_fraction` exposes the ±40 % thin-barrier change separately from the ±3 % well change | code | — |
| 4 | Mesh convergence on design A before spending the other 88 runs | work laptop | Stage 5 gate |
| 5 | Decide the v3 barrier lower bound **from** Stage 5, not before | — | v3 |
| 6 | Move `maximum_boundary_probability` to `never_model` | v3 config | v3 |
| 7 | ~~Extend `tables13.UNITS` to the new semantic columns~~ — **done in this pass**, with a test that fails on any future column emitted without a unit | code | — |
| 8 | Fix the `metrics13.build_record` provenance leak | v3 only | v3 |

## 6. Standing judgement

The reporting path is now honest: it distinguishes an optimizer coordinate from
a physical length, a proposal from a realized structure, a missing model from a
missing solver, and a completed licensed campaign from a validated physical
result.

What it still cannot do is tell you whether t0012 is a real optimum. That is
Stage 5's job, and until Stage 5 runs, the strongest supportable statement
remains: **the search completed, it preferred abrupt designs, and its best
design sits on a search bound at a barrier thickness of under two monolayers.**
