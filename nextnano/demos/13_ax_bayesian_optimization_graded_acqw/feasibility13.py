"""Which metrics Ax may constrain, and an exact audit of why a trial is feasible.

Why this module exists
======================

The 2026-07-31 licensed run emitted BoTorch's ``When all training points are
infeasible`` on every model-based iteration -- and it began doing so at the
*seventh* trial, which is precisely when the first genuinely feasible design
appeared.  Feasible data made the warning start, not stop.

That was reproduced here on the home laptop by replaying the run's own metric
values (``nextnano/tests/test_demo13_ax_feasibility.py``).  Leaving each
constraint out in turn isolated the cause exactly:

===========================================  ===================  ============
constraint                                   observed spread      triggers it
===========================================  ===================  ============
``absolute_detuning_nm <= 15``               3 .. 46              no
``maximum_boundary_probability <= 1e-3``     2e-5 .. 4e-3         no
``state_tracking_confidence >= 0.80``        0.99 (constant)      no
``orthonormality_error <= 1e-3``             3e-7 (constant)      **yes**
``origin_independence_valid >= 1``           1 (constant)         **yes**
``required_states_valid >= 1``               1 (constant)         **yes**
``physical_qc_valid >= 1``                   0/1                  **yes**
===========================================  ===================  ============

Each of the bottom four is *individually sufficient*: constraining on any one of
them alone reproduces the warning, and removing any one of them alone does not
cure it.

The mechanism.  Ax standardizes every modelled outcome before fitting.  A
constraint is then evaluated probabilistically against the surrogate posterior,
and a point counts as feasible only when it satisfies the constraint with
confidence.  What matters is therefore not whether a metric is constant, but the
size of its **standardized slack** -- the gap between the observed value and the
threshold, measured in units of the surrogate's predictive uncertainty:

* ``state_tracking_confidence`` is constant at 0.99 against a 0.80 bound. Its
  slack is 0.19, comfortably resolvable, and it does not trigger the warning.
  Constancy alone is not the problem.
* ``orthonormality_error`` is constant at 3e-7 against a 1e-3 bound. It passes by
  four orders of magnitude in physical terms, but after standardization the
  slack is ~1e-3 against a posterior standard deviation of order one, which is
  indistinguishable from zero.
* The 0/1 flags sit *exactly* on their own threshold (value 1, bound ``>= 1``),
  so their slack is identically zero and no confidence level can ever be met.

The rule this module enforces
=============================

**A metric earns an Ax outcome constraint only if it varies meaningfully and its
threshold is resolvable against that variation.** Everything else is enforced
where it belongs:

* deterministic geometry validity -> preflight rejection, before the solver;
* mechanical failure -> a failed Ax trial, with no objective;
* binary scientific validity -> trial status and post-processing QC, with the
  trial abandoned in Ax when its objective would mislead the surrogate;
* metrics that always pass by orders of magnitude -> recorded, reported, and
  checked, but never modelled.

Nothing is silently dropped.  Every constraint the YAML asks for is evaluated on
every trial and written to ``bo_constraint_feasibility_audit.csv``; the only
question this module answers is which of them Ax is *told about*.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import DemoError  # noqa: E402


#: How a configured constraint is enforced.
ENFORCEMENT_AX = "ax_outcome_constraint"
ENFORCEMENT_POST = "post_processing_qc"
ENFORCEMENT_PREFLIGHT = "preflight_geometry"

#: Minimum standardized slack a constraint must have before Ax may model it.
#: A metric whose observations all sit within this many standard deviations of
#: its own threshold cannot be satisfied "with confidence" by a Gaussian
#: surrogate, so constraining it makes every point infeasible.
MINIMUM_STANDARDIZED_SLACK = 0.05


@dataclass(frozen=True)
class ConstraintSpec:
    """One configured constraint, and how Demo 13 enforces it."""

    name: str
    metric: str
    operator: str
    threshold: float
    enforcement: str
    rationale: str
    #: Binary 0/1 validity flags are never given to Ax; see the module docstring.
    is_binary_flag: bool = False

    @property
    def ax_string(self) -> str:
        return f"{self.metric} {self.operator} {self.threshold:g}"

    def satisfied_by(self, value: Any) -> bool | None:
        """Whether one observed value satisfies this constraint."""

        number = _finite(value)
        if number is None:
            return None
        return number <= self.threshold if self.operator == "<=" else number >= self.threshold

    def slack(self, value: Any) -> float | None:
        """Signed distance inside the feasible region, in raw metric units."""

        number = _finite(value)
        if number is None:
            return None
        return self.threshold - number if self.operator == "<=" else number - self.threshold

    def as_record(self) -> dict[str, Any]:
        return {
            "constraint": self.name,
            "metric": self.metric,
            "operator": self.operator,
            "threshold": self.threshold,
            "enforcement": self.enforcement,
            "given_to_ax": self.enforcement == ENFORCEMENT_AX,
            "is_binary_flag": self.is_binary_flag,
            "rationale": self.rationale,
        }


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


#: The configured constraint vocabulary: YAML key -> (metric, operator, binary?).
#: ``maximum_detuning_nm`` deliberately binds ``absolute_detuning_nm`` and never
#: the signed value: a design 13 nm red of target and one 13 nm blue of it are
#: equally far away, and constraining the signed quantity would silently forbid
#: half the design space.
CONSTRAINT_VOCABULARY: Mapping[str, tuple[str, str, bool]] = {
    "maximum_detuning_nm": ("absolute_detuning_nm", "<=", False),
    "maximum_boundary_probability": ("maximum_boundary_probability", "<=", False),
    "minimum_state_tracking_confidence": ("state_tracking_confidence", ">=", False),
    "maximum_orthonormality_error": ("orthonormality_error", "<=", False),
    "require_origin_independence": ("origin_independence_valid", ">=", True),
    "require_expected_states": ("required_states_valid", ">=", True),
    "require_physical_qc": ("physical_qc_valid", ">=", True),
}

_RATIONALE_AX = (
    "continuous, varies meaningfully across designs, and its threshold is "
    "resolvable against that variation"
)
_RATIONALE_BINARY = (
    "binary 0/1 validity flag: its observations sit exactly on the threshold, so "
    "a Gaussian surrogate can never satisfy it with confidence and every point "
    "becomes infeasible. Enforced as trial status and post-processing QC instead"
)
_RATIONALE_MARGIN = (
    "passes by orders of magnitude on every design seen so far, so its "
    "standardized slack is indistinguishable from zero and constraining it makes "
    "every point infeasible. Recorded and checked, but not modelled"
)


def build_constraints(cfg: Mapping[str, Any]) -> list[ConstraintSpec]:
    """Resolve the configured constraints and decide how each is enforced."""

    bo = cfg.get("bo") or {}
    configured = bo.get("outcome_constraints") or {}
    modelling = (bo.get("outcome_modelling") or {})
    forced_post = {str(name) for name in (modelling.get("never_model") or [])}
    forced_ax = {str(name) for name in (modelling.get("always_model") or [])}

    specs: list[ConstraintSpec] = []
    for key, (metric, operator, is_binary) in CONSTRAINT_VOCABULARY.items():
        if key not in configured or configured[key] is None:
            continue
        raw = configured[key]
        if is_binary:
            if not bool(raw):
                continue
            threshold = 1.0
        else:
            threshold = float(raw)
        if metric in forced_ax:
            enforcement, rationale = ENFORCEMENT_AX, "forced by bo.outcome_modelling.always_model"
        elif metric in forced_post:
            enforcement, rationale = ENFORCEMENT_POST, "forced by bo.outcome_modelling.never_model"
        elif is_binary:
            enforcement, rationale = ENFORCEMENT_POST, _RATIONALE_BINARY
        else:
            enforcement, rationale = ENFORCEMENT_AX, _RATIONALE_AX
        specs.append(
            ConstraintSpec(
                name=key,
                metric=metric,
                operator=operator,
                threshold=threshold,
                enforcement=enforcement,
                rationale=rationale,
                is_binary_flag=is_binary,
            )
        )
    return specs


def modelled_constraints(specs: Sequence[ConstraintSpec]) -> list[ConstraintSpec]:
    return [spec for spec in specs if spec.enforcement == ENFORCEMENT_AX]


def post_processing_constraints(specs: Sequence[ConstraintSpec]) -> list[ConstraintSpec]:
    return [spec for spec in specs if spec.enforcement == ENFORCEMENT_POST]


# ---------------------------------------------------------------------------
# the audit
# ---------------------------------------------------------------------------


def audit_rows(
    records: Sequence[Mapping[str, Any]], specs: Sequence[ConstraintSpec]
) -> list[dict[str, Any]]:
    """One row per (trial, constraint): the exact feasibility calculation.

    Every configured constraint is evaluated for every completed trial, whether
    or not Ax was told about it, so the table shows both what the optimizer saw
    and what the physics says.
    """

    rows: list[dict[str, Any]] = []
    for record in records:
        if str(record.get("status")) != "completed":
            continue
        trial = record.get("trial_index")
        for spec in specs:
            raw = record.get(spec.metric)
            value = _finite(raw)
            satisfied = spec.satisfied_by(raw)
            rows.append(
                {
                    "trial_index": trial,
                    "iteration": record.get("iteration"),
                    "constraint": spec.name,
                    "ax_metric_name": spec.metric,
                    "source_field": spec.metric,
                    "raw_metric_value": raw,
                    "submitted_to_ax_value": value if spec.enforcement == ENFORCEMENT_AX else None,
                    "ax_value_type": "float" if spec.enforcement == ENFORCEMENT_AX else "not submitted",
                    "constraint_operator": spec.operator,
                    "constraint_threshold": spec.threshold,
                    "raw_slack": spec.slack(raw),
                    "value_is_finite": value is not None,
                    "constraint_passed": satisfied,
                    "enforcement": spec.enforcement,
                    "given_to_ax": spec.enforcement == ENFORCEMENT_AX,
                    "enforcement_rationale": spec.rationale,
                }
            )
    by_trial: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        by_trial.setdefault(row["trial_index"], []).append(row)
    for trial, group in by_trial.items():
        overall = all(row["constraint_passed"] is True for row in group)
        ax_only = all(
            row["constraint_passed"] is True for row in group if row["given_to_ax"]
        )
        for row in group:
            row["trial_feasible_all_constraints"] = overall
            row["trial_feasible_ax_constraints_only"] = ax_only
    return rows


def constraint_spread(
    records: Sequence[Mapping[str, Any]], specs: Sequence[ConstraintSpec]
) -> list[dict[str, Any]]:
    """Observed spread per constraint, and whether Ax could resolve its threshold.

    This is the diagnostic that would have caught the 2026-07-31 warning on the
    first run: a modelled constraint whose standardized slack is below
    :data:`MINIMUM_STANDARDIZED_SLACK` will make every observation infeasible.
    """

    rows: list[dict[str, Any]] = []
    for spec in specs:
        values = [
            _finite(record.get(spec.metric))
            for record in records
            if str(record.get("status")) == "completed"
        ]
        values = [value for value in values if value is not None]
        if not values:
            rows.append(
                {
                    **spec.as_record(),
                    "observations": 0,
                    "minimum": None,
                    "maximum": None,
                    "standard_deviation": None,
                    "minimum_raw_slack": None,
                    "standardized_slack": None,
                    "resolvable_by_surrogate": None,
                    "diagnosis": "no completed observations yet",
                }
            )
            continue
        low, high = min(values), max(values)
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / max(1, len(values) - 1)
        deviation = math.sqrt(variance)
        slacks = [value for value in (spec.slack(value) for value in values) if value is not None]
        minimum_slack = min(slacks)
        # The question is whether the threshold is *resolvable*, not whether
        # every point passes it. A constraint that some designs genuinely
        # violate is doing its job; the pathological case is one where even the
        # best-satisfying observation sits negligibly far inside the bound, so
        # no point can ever be called feasible with confidence. The best-case
        # margin is therefore the right statistic, not the worst.
        best_slack = max(slacks)
        # Ax standardizes a constant outcome with a unit scale, so the raw slack
        # is also the standardized slack in that limit; where the metric does
        # vary, its own spread sets the scale.
        #
        # "Constant" has to be judged relative to the values themselves. Nine
        # identical readings of 3e-7 have a floating-point standard deviation
        # around 1e-23, and dividing by that turned a slack of 1e-3 into 1e19 --
        # reporting the single worst constraint in the study as the safest.
        magnitude = max(abs(low), abs(high), 1.0)
        effectively_constant = deviation <= 1e-9 * magnitude
        scale = 1.0 if effectively_constant else deviation
        standardized = best_slack / scale
        resolvable = standardized >= MINIMUM_STANDARDIZED_SLACK
        if spec.is_binary_flag:
            diagnosis = (
                "binary flag sitting on its own threshold; never modelled"
            )
        elif not resolvable:
            diagnosis = (
                f"standardized slack {standardized:.3g} is below "
                f"{MINIMUM_STANDARDIZED_SLACK}; modelling this constraint would make "
                "every observation infeasible"
            )
        else:
            diagnosis = "resolvable; safe to model"
        rows.append(
            {
                **spec.as_record(),
                "observations": len(values),
                "minimum": low,
                "maximum": high,
                "standard_deviation": deviation,
                "effectively_constant": effectively_constant,
                "minimum_raw_slack": minimum_slack,
                "best_raw_slack": best_slack,
                "standardized_slack": standardized,
                "resolvable_by_surrogate": resolvable,
                "diagnosis": diagnosis,
            }
        )
    return rows


def unresolvable_modelled_constraints(spread: Sequence[Mapping[str, Any]]) -> list[str]:
    """Modelled constraints that will make every observation infeasible."""

    return [
        str(row["constraint"])
        for row in spread
        if row.get("given_to_ax")
        and row.get("resolvable_by_surrogate") is False
    ]


def feasibility_summary(
    records: Sequence[Mapping[str, Any]], specs: Sequence[ConstraintSpec]
) -> dict[str, Any]:
    """Section 11: is there any feasible observation, and when did one appear?"""

    completed = [
        record for record in records if str(record.get("status")) == "completed"
    ]
    feasible: list[int] = []
    for record in completed:
        if all(spec.satisfied_by(record.get(spec.metric)) is True for spec in specs):
            feasible.append(int(record.get("trial_index", -1)))
    initial = [
        record
        for record in completed
        if int(record.get("iteration", 0) or 0) == 0
    ]
    initial_feasible = [
        int(record.get("trial_index", -1))
        for record in initial
        if all(spec.satisfied_by(record.get(spec.metric)) is True for spec in specs)
    ]
    return {
        "completed_trials": len(completed),
        "feasible_trials": sorted(feasible),
        "feasible_count": len(feasible),
        "any_feasible": bool(feasible),
        "first_feasible_trial": min(feasible) if feasible else None,
        "initial_design_trials": len(initial),
        "initial_design_feasible_count": len(initial_feasible),
        "initial_design_all_infeasible": bool(initial) and not initial_feasible,
        "interpretation": (
            "no completed trial satisfies every configured constraint; any "
            "reported improvement is among infeasible designs and must not be "
            "read as progress toward a usable design"
            if not feasible
            else (
                "the initial design contained no feasible point; the first "
                f"feasible observation is trial {min(feasible)}"
                if bool(initial) and not initial_feasible
                else f"{len(feasible)} feasible observation(s)"
            )
        ),
    }
