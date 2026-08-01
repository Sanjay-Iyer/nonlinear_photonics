# Ax / BoTorch audit — Demo 13 hardening pass, 2026-08-01

Reviewer role: Ax/BoTorch Bayesian-optimization engineer.
Environment: `ax-platform 1.3.1`, `botorch 0.18.1`, `torch 2.12.1+cpu`,
Python 3.11.15, numpy 2.4.6.

**Verdict: PASS WITH WARNINGS.**

---

## 1. Predictive adapter reconstruction

**PASS.** The root cause was correctly diagnosed rather than worked around.

`Client.load_from_json_file` restores the `Experiment` and the
`GenerationStrategy` but **not** a fitted adapter:
`GenerationStrategy.adapter` returns `self._curr._fitted_adapter`, which is
populated during `gen()` and is not serialized. On the reloaded v2 client it is
`None`. `Client.predict` then calls `none_throws(...)`, which raises
`AssertionError`, which `predict` catches and re-raises as `UnsupportedError`
with the misleading text "the current GenerationNode is not predictive". The
node *is* predictive (MBM); it simply has not been fitted. That misleading
message is why the defect was originally read as a node-progression problem.

The chosen fix is the right one and I checked the alternatives:

| Option | Verdict |
|---|---|
| `GenerationStrategy.fit(experiment, data)` | **Rejected.** Its first act is `_maybe_transition_to_next_node(...)`. On a terminal MBM node that is a no-op today, but relying on that is relying on an implementation detail of Ax's transition criteria. |
| `node._fit(experiment, data)` on the live client | **Rejected.** It sets `self._generator_spec_to_gen_from = None` and stores a fitted adapter on the node, mutating the object the rest of the run holds. |
| `node._fit` on a **separately loaded** client | **Adopted.** No transition, and the mutation lands on a throwaway object. |
| `Generators.BOTORCH_MODULAR(experiment, data)` | **Adopted as fallback only**, for a study that never left Sobol. Correctly labelled in the record as not necessarily the model Ax generated with. |

Verified empirically against a real 16-trial snapshot: `fit_status =
refitted_current_generation_node`, `model_class = TorchAdapter`,
`generation_node_before == generation_node_after == "MBM"`, snapshot SHA-256
unchanged, trial count unchanged.

## 2. Search-space hierarchy

**PASS.** The space is a two-valued root `interface_mode ∈ {abrupt, graded}`
with `dependents={'abrupt': [], 'graded': ['grading_fraction_of_feasible_max',
'grading_profile']}` — the tree shape required by Ax 1.3.1, which rejects a DAG
with `UserInputError: Hierarchical search space contains a cycle`.

`check_membership(..., check_all_parameters_present=True)` is strict in both
directions, and both failures are now exercised:

- abrupt **with** the grading children → `ValueError`, prediction refused;
- graded **without** them → `RuntimeError`, prediction refused.

Both produce a reason naming the search space, never the solver.

## 3. Active / inactive parameters

**PASS.** `demo13._encode_search_point` imposes the branch structure on any
point handed to the model. This replaced the genuinely serious bug (audit A1)
where `axsearch13.ax_parameters` — which expects a *canonical* design with a
realized thickness — was fed *search-space* points carrying only a fraction,
defaulted the thickness to 0.0, and emitted `interface_mode: "abrupt"` for
every one of 625 slice points. The surrogate was being queried at one point.

## 4. Transformed versus realized parameters

**PASS.** Predictions are made in Ax coordinates, as they must be — the model
was trained on them. The realized geometry is attached to each row as extra
columns via `design13.canonicalize`, so a CSV carries both without the figure
axis pretending to be a length.

⚠️ **Warning:** `maximum_feasible_grading_nm` varies per candidate, so a fixed
fraction does **not** correspond to a fixed thickness across a slice. A
horizontal line on a surrogate surface is a line of constant *fraction*, not of
constant nanometres. The CSV makes this visible; a reader looking only at the
figure could still miss it. The axis label at least no longer claims otherwise.

## 5. Objective and constraints

**PASS.** Single objective `relative_chi2_at_target_wavelength_abs`
(maximize). Three modelled outcome constraints: `absolute_detuning_nm <= 15`,
`maximum_boundary_probability <= 0.001`, `state_tracking_confidence >= 0.8`.
Confirmed from the deserialized `optimization_config`, not from the YAML.

Correct choices, verified:
- the **absolute** detuning is constrained; the signed value appears in no
  constraint anywhere (searched);
- binary validity flags (`physical_qc_valid`, `origin_independence_valid`,
  `required_states_valid`) are in `constraints_enforced_outside_ax` and are
  **not** GP outcomes. Modelling a 0/1 flag as a Gaussian outcome is exactly
  the mistake that produced the earlier all-infeasible pathology;
- `orthonormality_error` is in `never_model` for the documented reason (constant
  at ~3e-7 against a 1e-3 bound).

⚠️ **Warning:** `maximum_boundary_probability` is *also* effectively constant in
the observations — Ax logs `Outcome maximum_boundary_probability is constant,
within tolerance` on every fit. It is a modelled constraint that carries no
information and cannot be resolved by the surrogate; `feasibility13` already
warns about exactly this class of constraint. It should join `never_model` in
v3. Not changed here because that alters the modelled outcome set, which would
make v2's checkpoint inconsistent with the configuration.

## 6. Feasibility classification

**PASS.** Feasibility is computed from the recorded metrics against the full
constraint set (`feasibility13.build_constraints`), independently of Ax's own
view — the fix from commit `3df57e8`. Ax's opinion of feasibility is used for
generation; the reports use the repository's.

## 7. Posterior prediction validity

**PASS.** All four metrics (objective + three constraints) return finite means
and finite standard errors at valid points on both branches. Standard errors are
taken as `covariance[m][m][i] ** 0.5` with a negative-variance guard.

⚠️ **Warning — over-confidence.** With 16 observations over a 4-dimensional
mixed space including a categorical, the posterior standard error will look
small in the interior of the sampled region and is not trustworthy at that face
value. This is a property of a GP with few points, not a defect. The
uncertainty surfaces should be read as "where the model has and has not seen
data", not as calibrated error bars.

## 8. Partial-dependence assumptions

**PASS WITH WARNINGS.** What is produced is a **one-dimensional slice** with the
other coordinates held at configured fixed values — not a true partial
dependence, which would marginalize over the data distribution.

This is the *right* choice for a hierarchical space: a genuine PD average would
have to average across the abrupt and graded branches, which are not
commensurable — the abrupt branch has no grading coordinate to average over.
Each row now carries a `holding_note` saying it is a slice and that it does not
mix branches.

⚠️ **Warning:** the curve is only as representative as the held-fixed point.
`asymmetry_s: 0.46`, `central_barrier_thickness_nm: 1.8` is *not* near the
optimum (which is at barrier 0.5), so the grading curve is drawn through a
region the optimizer abandoned. Worth revisiting for v3.

## 9. Acquisition-surface interpretation

**PASS.** `_expected_improvement` computes analytic EI from the posterior mean
and standard error. Every row carries `expected_improvement_method` stating it
is "not a replay of Ax's Monte-Carlo acquisition", and the figure is labelled
"Expected improvement", not "Acquisition function value".

This is honest and important: Ax generated with **qLogNoisyExpectedImprovement**
(the BoTorch warning `When all training points are infeasible, it is better to
use q(Log)ProbabilityOfFeasibility` confirms the LogEI family), which is a
Monte-Carlo, constraint-weighted, noisy-observation acquisition. Analytic EI on
the objective alone is a *different function*. It is a reasonable illustration
of where the model expects improvement; it is not what Ax optimized. Actual
per-proposal acquisition values are reported separately from
`gen_metadata[Keys.EXPECTED_ACQF_VAL]`, and Sobol trials correctly have none.

## 10. Parameter-importance reliability with 16 observations

**PASS WITH WARNINGS — this is the output most likely to be over-read.**

Implementation is correct: `ax_parameter_sens(adapter, order="first")`, with
Ax's `<name>_OH_PARAM_<k>` one-hot columns folded back onto the parent
categorical by summing (the standard aggregation for jointly-varying variables).
Metrics whose indices are non-finite — `maximum_boundary_probability`, because
it is constant — are reported as `metrics_without_defined_importance` with the
reason, not as zero.

⚠️ **Warnings:**
1. Sixteen observations over four parameters. These indices describe **the
   fitted surrogate**, not the physics, and they are not a significance test.
   The `interpretation_caveat` now says so and quotes the **trial** count.
2. Observed indices are sometimes **negative** (e.g. −0.11). First-order Sobol
   indices are non-negative by definition; negatives are estimator noise at
   this sample size and are direct evidence that the estimates are not
   converged. They are reported as-is rather than clipped, which is honest, but
   a reader must not rank parameters by them.
3. `observations_used` now counts **trials**, not the 64 metric rows
   `lookup_data()` returns. Quoting 64 would have inflated the apparent evidence
   fourfold in the caveat text itself.

## 11. Checkpoint compatibility

**PASS.** `_check_schema_compatible` refuses to resume a snapshot whose stored
`experiment_schema.json` differs from the configuration, which is what stops a
v2 checkpoint being loaded under a v3 search space. v3 is specified to use a
**new directory**, so the two never meet.

## 12. No hidden advancement of the GenerationStrategy

**PASS.** Three independent guarantees:
1. reconstruction operates on a separately loaded client;
2. it uses `node._fit`, which does not transition, and asserts
   `current_node_name` is unchanged, raising `ReconstructionError` if it ever
   moves;
3. `Experiment(read_only=True).generate()` raises before reaching Ax.

Recorded per run as `generation_strategy_advanced` and `new_trials_generated`
in `analysis_model_reconstruction.json`.

---

## Answers to the specific risks raised

| # | Risk | Finding |
|---|---|---|
| 1 | Wrong adapter reconstructed | No — the study's own MBM node is refitted; fallback is labelled |
| 2 | Reanalysis advances the strategy | No — asserted, and recorded per run |
| 3 | Reanalysis generates a candidate | No — `generate()` raises under read-only |
| 4 | Checkpoint modified | No — SHA-256 compared before/after |
| 6 | Model fitted with failed observations | No — completed-only, finite-only, counts recorded |
| 7 | Binary QC flags as GP constraints | No — enforced outside Ax |
| 8 | Signed detuning constrained | No — absolute only; verified by search |
| 9/10 | Hierarchical branch errors | Rejected with a truthful reason, both directions |
| 18 | Importance claims significance | Caveated; negative indices flagged as estimator noise |
| 19 | PD averages invalid combinations | It is a slice, not an average; branches never mixed |
| 20 | Acquisition presented as Ax's | Explicitly denied in every row and in the guide |
| 21 | Unrealistic surrogate confidence | Flagged as a warning; not a code defect |
| 22 | Categorical effects from one observation | `profile_ranking_supportable` gate in `grading13` |
| 32 | State tracking depends on evaluation order | **Real, unresolved** — physics audit §4, Stage 5 item |

**Signed: PASS WITH WARNINGS.**
