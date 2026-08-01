# v3 cross-audit summary

Agent 2 (independent auditor) comparing `V3_PHYSICS_AUDIT.md`,
`V3_SOFTWARE_AUDIT.md`, `V3_AX_BO_AUDIT.md` and `V3_PLOT_FUNCTION_AUDIT.md`,
looking for contradictions and for anything all four missed.

| Auditor | Verdict |
|---|---|
| Physics / materials | PASS WITH WARNINGS |
| Software | PASS WITH WARNINGS |
| Ax / BoTorch | PASS WITH WARNINGS |
| Plot functions | PASS WITH WARNINGS |
| **Combined** | **PASS WITH WARNINGS** — no FAIL, phases may close |

---

## Phase verdicts

| Phase | Agent 1 result | Agent 2 |
|---|---|---|
| 1 — evidence inventory | 23/7/16/6/10/3 recomputed; 5 defects reproduced | **PASS** |
| 2 — lifecycle & accounting | one accounting function; all 10 required numbers | **PASS** |
| 3 — rejection history & generation | 7 rows from the ledger; interval mapping opt-in | **PASS** |
| 4 — iteration semantics | MBM 1–10; refusals excluded | **PASS** |
| 5 — proposed vs realized | 5 graded + 11 abrupt = 16; 7 not_realized | **PASS** |
| 6 — surrogate grids | 350/625 withheld with branch reasons | **PASS** |
| 7 — acquisition & feasibility | probabilities + constrained proxy | **PASS WITH WARNINGS** (residual F4) |
| 8 — profile & importance | honest counts; no ranking | **PASS WITH WARNINGS** (residual F5) |
| 9 — stale text | registry rewritten; chi2 units fixed | **PASS** |
| 10 — raw bundling | commands prepared; nothing verified yet | **PASS WITH WARNINGS** |
| 11 — reanalysis | hashes identical; 0 solver calls | **PASS** |
| 12 — Stage 5 prep | 42 runs, gated, thresholds pre-stated | **PASS WITH WARNINGS** (isolation gap) |

---

## Contradictions found and resolved

### X-1. "Is the surrogate usable?" — RESOLVED

The Ax audit reports a successfully refitted `TorchAdapter` predicting all four
metrics (PASS). The physics audit says the surrogate cannot support any claim
about grading. The plot audit says 56 % of one surface was physically
meaningless.

**Resolution: all three are true of different things, and the earlier drafts
were imprecise.** The adapter is *reconstructible and correct*. The *predictions*
are valid at valid points. The *plotted surfaces* were partly meaningless
because invalid points were fed to a valid model. And the *scientific reach* is
limited by 16 observations and 3 feasible ones regardless of any of that. All
four documents now separate model availability, point validity, and evidential
weight rather than using "the surrogate works" to mean all three.

### X-2. "Is the boundary constraint fine or broken?" — RESOLVED, carried from v2

Ax audit: `maximum_boundary_probability` is uninformative and should leave the
modelled set. Physics audit: the metric is correctly defined and t0021 is a
factor of 29 inside it.

**Resolution: the metric stays, its GP membership goes.** Unchanged in v3
because altering the modelled outcome set would make the checkpoint inconsistent
with its own configuration. Queued for v4. Both documents now say this in the
same words.

### X-3. "Was the 7-rejection behaviour a success or a defect?" — RESOLVED

The Ax audit treats the seven refusals as the guard **working** — no unbuildable
geometry reached the solver. The brief lists "candidate generation still
proposes many sub-resolution grades" as defect 14.

**Resolution: both, and they are different layers.** Refusing was correct;
*needing* to refuse 7 of 23 proposals is a generation weakness. Refusal is kept
as the safety net and the interval mapping addresses the waste — opt-in, because
turning it on for v3 would reinterpret recorded observations. The distinction is
now explicit in `V3_AX_BO_AUDIT.md` §7.

---

## What no single auditor caught alone

**The schema-field trap.** The software auditor added
`grading_fraction_spans_feasible_interval` to the experiment schema — correct,
since it changes what a stored fraction means. The Ax auditor then found the v3
snapshot **would no longer load**, because a key absent from the stored schema
compared unequal to the configured value. Every future identity field would have
invalidated every existing checkpoint.

Neither alone would have caught it: one added the field, the other tried to load
real data. Fixed with `SCHEMA_FIELD_DEFAULTS` and
`test_a_snapshot_predating_a_schema_field_stays_loadable`.

**Two of the four Phase-2 defects were regressions from the previous hardening
pass**, which shipped to a licensed campaign with a green suite. The root cause
was three copies of rejection-classification logic. That is now one copy plus a
test that iterates the reason constants, so the *next* new reason fails the
suite instead of counting as nothing.

---

## The falsification trap, checked deliberately

Agent 2's job is to falsify Agent 1. Three places where green tests coexist with
an unresolved problem:

| Green | Unresolved |
|---|---|
| accounting reports 23/7/16 exactly | the numbers are *consistent*; nothing here says the campaign explored a useful region. 3 of 16 feasible. |
| 5 graded trials correctly identified as genuinely graded | **no alloy profile has ever been checked.** The claim rests on geometry arithmetic, not solver output. |
| t0021 ranked first, deterministically | ranking is correct *given the objective*; whether the objective is mesh-converged is untested, and Demo 11's window convergence is on record as FAILED. |

None is a code defect. All three are why the demo stays
`licensed_optimization_completed_validation_pending`.

---

## Carried forward

| # | Item | Blocks |
|---|---|---|
| 1 | Alloy-profile verification for the 5 graded trials | any grading realization claim |
| 2 | Stage 5 mesh gate on t0021 | everything downstream |
| 3 | Stage 5 directory isolation from the v3 experiment | Stage 5 launch |
| 4 | Plot constrained-EI, not unconstrained EI, on the acquisition figure | — |
| 5 | Print n per group on the profile boxplot | — |
| 6 | `maximum_boundary_probability` → `never_model` | v4 |
| 7 | Work-laptop tree was dirty when v3 ran | provenance of v3's numbers |

## Standing judgement

The v3 reporting path is now honest: it counts proposals correctly, distinguishes
a refused proposal from a built structure, numbers BO iterations by completed
model-based evaluations, withholds surrogate points whose branch is physically
invalid, and refuses to rank grading profiles from one sample each.

What it still cannot tell you is whether t0021 is a real optimum, or whether
grading helps. The strongest supportable statement remains: **the campaign
completed, three of sixteen designs were feasible, the best of them sits on the
barrier lower bound, and no graded design satisfied the detuning constraint.**
