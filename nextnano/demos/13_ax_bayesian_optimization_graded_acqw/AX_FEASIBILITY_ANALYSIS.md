# Demo 13 — why Ax called every observation infeasible

Diagnosis of the 2026-07-31 licensed run. Reproduced on the home laptop with no
solver; every claim below is checked by
`nextnano/tests/test_demo13_ax_feasibility.py`.

## The symptom

Every model-based iteration logged:

```
BotorchWarning: When all training points are infeasible, it is better to use
q(Log)ProbabilityOfFeasibility.
```

The warning began at **trial 7** and never stopped. That timing is the whole
clue: trial 7 is the *first genuinely feasible design in the run*. Feasible data
made the warning start, not stop.

| phase | trials | signed detuning (nm) | feasible by hand |
|---|---|---|---|
| Sobol | 0–6 | −46, −40, −28, −40, −16, −41 | none |
| MBM | 7–9 | **+3, −13, −10** | all three |

So the reading "the Sobol points were all off-target" explains the first six
trials and nothing after them.

## The reproduction

`test_constant_flag_constraints_make_every_point_infeasible` replays the run's
own metric values into a fresh Ax client and toggles one constraint at a time.

| constraint | observed spread | triggers the warning alone? |
|---|---|---|
| `absolute_detuning_nm <= 15` | 3 … 46 | no |
| `maximum_boundary_probability <= 1e-3` | 2e-5 … 4e-3 | no |
| `state_tracking_confidence >= 0.80` | 0.99 (constant) | no |
| `orthonormality_error <= 1e-3` | 3e-7 (constant) | **yes** |
| `origin_independence_valid >= 1` | 1 (constant) | **yes** |
| `required_states_valid >= 1` | 1 (constant) | **yes** |
| `physical_qc_valid >= 1` | 0/1 | **yes** |

Each of the bottom four is *individually sufficient*. Removing any one alone
does not cure it; removing all four does.

## The mechanism

Ax standardizes every modelled outcome before fitting, then evaluates
constraints probabilistically against the surrogate posterior. A point is
feasible only if it satisfies the constraint *with confidence*.

What matters is therefore the **standardized slack** — the gap between the
observation and the threshold, measured in units of the surrogate's predictive
uncertainty. Not whether the metric is constant:

- `state_tracking_confidence` is constant at 0.99 against a 0.80 bound. Slack
  0.19, comfortably resolvable. **Does not trigger it.** Constancy alone is not
  the problem.
- `orthonormality_error` is constant at 3e-7 against a 1e-3 bound. It passes by
  four orders of magnitude *physically*, but the standardized slack is ~1e-3
  against a posterior standard deviation of order one — indistinguishable from
  zero.
- The 0/1 flags sit **exactly on** their own threshold (value 1, bound `>= 1`).
  Slack is identically zero. No confidence level is ever attainable.

A constraint nothing can satisfy makes every point infeasible, which is exactly
what BoTorch reported. It was right.

## What was fixed

`feasibility13.build_constraints` now decides *where* each configured constraint
is enforced, and only continuous, meaningfully-varying metrics reach the
surrogate:

| constraint | enforcement |
|---|---|
| `absolute_detuning_nm` | Ax outcome constraint |
| `maximum_boundary_probability` | Ax outcome constraint |
| `state_tracking_confidence` | Ax outcome constraint |
| `orthonormality_error` | post-processing QC (`bo.outcome_modelling.never_model`) |
| `origin_independence_valid` | post-processing QC (binary flag) |
| `required_states_valid` | post-processing QC (binary flag) |
| `physical_qc_valid` | post-processing QC (binary flag) |

**Nothing is dropped.** Every configured constraint is still evaluated on every
trial and written to `bo_constraint_feasibility_audit.csv`. The only change is
which of them Ax is *told about*.

Two record fields now exist where one did before:

- `trial_valid` — satisfies **every** configured constraint. The scientific
  verdict, and what the ranked tables filter on.
- `feasible_under_ax_constraints` — satisfies the subset Ax was given. What the
  optimizer was actually asked, and what its own feasibility logic sees.

## The guard against recurrence

`feasibility13.constraint_spread` computes the standardized slack of every
constraint from the observed data and flags any modelled constraint whose best
observation sits within `MINIMUM_STANDARDIZED_SLACK` (0.05) of its threshold.
`unresolvable_modelled_constraints` returns those names. This is the check that
would have caught the bug on the first run rather than the second.

One subtlety worth recording, because it produced a wrong answer during
development: "constant" must be judged *relative to the values*. Nine identical
readings of 3e-7 have a floating-point standard deviation near 1e-23, and
dividing a 1e-3 slack by that reports the single worst constraint in the study as
the safest one, by nineteen orders of magnitude. The comparison is now relative.

## Signed versus absolute detuning

The run recorded signed detunings (−46, −13, −7). A "within 15 nm of target"
constraint must bind the **absolute** value: a design 13 nm red of target is
exactly as close as one 13 nm blue of it, and constraining the signed quantity
silently forbids half the design space.

These are now two metrics with two jobs:

- `signed_detuning_nm = peak_wavelength_nm − target_wavelength_nm` — reported
  everywhere, alongside `detuning_side` (`red_of_target` / `blue_of_target` /
  `on_target`). **Never constrained.**
- `absolute_detuning_nm = |signed_detuning_nm|` — the only detuning a target
  proximity constraint may bind.

Verified for the run's own cases: 1537 nm → signed −13, absolute 13, **passes**
a 15 nm bound; 1522 nm → absolute 28, **fails**; 1553 nm → absolute 3,
**passes**.

Note that a trial can pass the detuning constraint and still be rejected — trial
6 is 41 nm off target *and* fails boundary probability. The audit table
separates those reasons per trial.

## All-infeasible initial designs

That the six Sobol points were all outside the detuning window is a real and
legitimate outcome, not a bug. `feasibility13.feasibility_summary` now reports it
explicitly:

- `initial_design_all_infeasible` — true for this run;
- `first_feasible_trial` — 7;
- `interpretation` — states in words that improvement among infeasible designs
  is not progress toward a usable one.

No constraint is relaxed to manufacture feasibility. If a study genuinely cannot
reach its constraints, the honest options are a warm-start point from Demo 12, a
wider search range, or a threshold changed **on the record** — and any configured
relaxation is written into the run manifest.

Whether `qLogProbabilityOfFeasibility` would help is now a separate and much
smaller question, and it should only be revisited on data where the constraint
encoding is known to be sound. It was never the fix here.

## Trial 6 and the redundant threshold

Trial 6 failed `bound_state_boundary_probability_small` while being marked Ax
`COMPLETED`. Both statements were true and the reporting was inconsistent, which
is fixed by the five-way outcome vocabulary in `metrics13`
(`valid`, `valid_with_warning`, `scientifically_invalid`, `mechanically_failed`,
`not_evaluated`) and the `physical_qc.bound_state_policy` setting.

While testing those policies a redundancy surfaced: the bound-state QC test and
the continuous `maximum_boundary_probability` constraint use **the same
threshold** (1e-3), so they can never disagree. No policy can rescue trial 6,
because the continuous constraint rejects it independently. That is recorded in
`test_bound_state_qc_and_the_continuous_constraint_share_a_threshold`, and it is
a good argument for `bound_state_policy: constraint` as the eventual default —
one voice for one piece of physics. The shipped default remains `warn` as
specified, and a warn-policy trial is reported as `valid_with_warning` with the
failing test still named. It is never presented as a clean pass.

**Still open:** whether trial 6's 4e-3 boundary probability is physically real or
an extraction artifact. That needs the state-resolved diagnostics and a padding
check on the licensed machine; the 1e-3 threshold itself has never been
justified against a converged calculation.
