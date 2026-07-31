"""Stage 1: a solver-free synthetic study with a known optimum.

Nothing in this module is physics.  It is a deterministic, analytically-known
test surface shaped *like* the Demo 12 response so that the whole Demo 13
machine -- search space, objective, outcome constraints, failed trials,
iteration counting, checkpointing, resume, tables, plots -- can be exercised end
to end on a laptop with no nextnano licence, and so that a broken optimizer is
caught by a failing recovery test rather than by a wasted licensed run.

Every number this module produces is labelled synthetic wherever it is written.
It is never mixed with, compared against, or promoted to a licensed result.

The surface
===========

A separable product of three smooth bumps and a per-profile factor::

    f = A(s) * B(b) * G(g) * P(profile)

with a single interior maximum at the parameters in :data:`SYNTHETIC_OPTIMUM`.
Three regions are deliberately awkward, because a test surface with no awkward
regions tests nothing:

* a **crash corner** (thin barrier *and* thick grade) raises, standing in for a
  solver that dies -- it must become a *failed* Ax trial, never a zero;
* a **leaky band** (very thick grades) returns a large boundary probability --
  it must be rejected by an outcome constraint while keeping its metrics;
* a **flat edge** (lowest asymmetries) returns a genuinely near-zero response --
  it must stay a valid observation, distinguishable from both of the above.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import DemoError  # noqa: E402

import design13  # noqa: E402

#: The maximum the Stage 1 smoke test must recover.
SYNTHETIC_OPTIMUM: Mapping[str, Any] = {
    "asymmetry_s": 0.46,
    "central_barrier_thickness_nm": 1.30,
    "grading_thickness_nm": 1.40,
    "grading_profile": "cosine",
}

#: Relative weight of each grading shape at the same thickness. ``cosine`` is
#: best by a margin a well-behaved optimizer can find, and ``abrupt`` is worst,
#: so recovering the categorical parameter is a real test and not a coin flip.
PROFILE_FACTOR: Mapping[str, float] = {
    "abrupt": 0.55,
    "linear": 0.82,
    "sigmoid": 0.88,
    "erf": 0.90,
    "cosine": 1.00,
}

#: Widths of the three bumps, in each parameter's own units.
_WIDTHS: Mapping[str, float] = {
    "asymmetry_s": 0.055,
    "central_barrier_thickness_nm": 0.65,
    "grading_thickness_nm": 0.85,
}

SYNTHETIC_LABEL = "SYNTHETIC — NOT LICENSED NEXTNANO OUTPUT"


class SyntheticFailure(RuntimeError):
    """Stands in for a mechanically failed solver run."""


def _bump(value: float, centre: float, width: float) -> float:
    return math.exp(-0.5 * ((float(value) - centre) / width) ** 2)


def objective_value(parameters: Mapping[str, Any], cfg: Mapping[str, Any]) -> float:
    """The synthetic ``chi2_at_target_wavelength_abs`` surface."""

    canonical = design13.canonicalize(parameters, cfg)
    value = 1.0
    for name, centre in (
        ("asymmetry_s", SYNTHETIC_OPTIMUM["asymmetry_s"]),
        ("central_barrier_thickness_nm", SYNTHETIC_OPTIMUM["central_barrier_thickness_nm"]),
        ("grading_thickness_nm", SYNTHETIC_OPTIMUM["grading_thickness_nm"]),
    ):
        value *= _bump(float(canonical[name]), float(centre), _WIDTHS[name])
    value *= PROFILE_FACTOR[str(canonical["grading_profile"])]
    # The flat edge: the lowest asymmetries are a genuinely weak, genuinely
    # valid structure rather than a failure.
    if float(canonical["asymmetry_s"]) < 0.365:
        value *= 1e-14
    return float(value)


def crashes(parameters: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    """The synthetic crash corner: a thin barrier under a thick grade."""

    canonical = design13.canonicalize(parameters, cfg)
    return (
        float(canonical["central_barrier_thickness_nm"]) < 0.60
        and float(canonical["grading_thickness_nm"]) > 2.60
    )


def evaluate(parameters: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """A synthetic trial record with the same field names as a real one.

    Raises :class:`SyntheticFailure` inside the crash corner so the caller has to
    take the same ``mark_trial_failed`` path a real solver crash takes.
    """

    if crashes(parameters, cfg):
        raise SyntheticFailure(
            "synthetic solver crash: barrier below 0.60 nm under a grade above 2.60 nm"
        )
    canonical = design13.canonicalize(parameters, cfg)
    target = float((cfg.get("chi2") or {}).get("reference_wavelength_nm", 1550.0))
    at_target = objective_value(parameters, cfg)
    grading = float(canonical["grading_thickness_nm"])
    asymmetry = float(canonical["asymmetry_s"])
    barrier = float(canonical["central_barrier_thickness_nm"])

    # Peak response and resonance position are deliberately *not* proportional
    # to the target-wavelength response: the two modes must be able to disagree
    # about which design wins, or Mode A and Mode B would be the same study.
    peak = at_target * (1.0 + 0.35 * _bump(grading, 2.1, 1.1))
    detuning = 26.0 * (asymmetry - SYNTHETIC_OPTIMUM["asymmetry_s"]) / 0.10 - 4.0 * (
        grading - SYNTHETIC_OPTIMUM["grading_thickness_nm"]
    )
    # The leaky band: thick grades push probability onto the domain boundary.
    # The coefficient is chosen so the default 1e-3 constraint bites somewhere
    # inside the search range (around 2.72 nm), not beyond its upper edge --
    # a constraint that no reachable design can violate tests nothing.
    boundary = 2.0e-5 + 2.0e-2 * max(0.0, grading - 2.50) ** 2
    confidence = 0.99 - 0.30 * max(0.0, 1.0 - abs(barrier - 1.05) / 0.12)

    record: dict[str, Any] = {
        **{f"parameter_{name}": value for name, value in canonical.items()},
        "target_wavelength_nm": target,
        "chi2_at_target_wavelength_abs": at_target,
        "peak_chi2_abs": peak,
        "peak_wavelength_nm": target + detuning,
        "detuning_nm": detuning,
        "detuning_nm_abs": abs(detuning),
        "integrated_chi2_abs": at_target * 180.0,
        "bandwidth_above_fraction_nm": 40.0 + 25.0 * _bump(grading, 1.8, 1.2),
        "maximum_boundary_probability": boundary,
        "left_boundary_probability": 0.5 * boundary,
        "right_boundary_probability": 0.5 * boundary,
        "total_boundary_probability": boundary,
        "state_tracking_confidence": confidence,
        "state_tracking_margin": max(0.02, 0.6 * (confidence - 0.5)),
        "state_tracking_ambiguous": bool(confidence < 0.70),
        "orthonormality_error": 3.0e-7,
        "origin_independence_valid": 1,
        "required_states_valid": 1,
        "physical_qc_valid": 1,
        "robustness_score": 0.55 + 0.35 * _bump(grading, 2.2, 1.4),
        "wide_well_probability": 0.62,
        "narrow_well_probability": 0.28,
        "central_barrier_probability": 0.07,
        "outer_barrier_probability": 0.03,
        "solver_completed": True,
        "expected_outputs_available": True,
        "synthetic": True,
        "data_label": SYNTHETIC_LABEL,
        "runtime_seconds": 0.0,
    }

    constraints = (cfg.get("bo") or {}).get("outcome_constraints") or {}
    violations: list[str] = []
    maximum_boundary = constraints.get("maximum_boundary_probability")
    if maximum_boundary is not None and boundary > float(maximum_boundary):
        violations.append("boundary_probability")
    minimum_confidence = constraints.get("minimum_state_tracking_confidence")
    if minimum_confidence is not None and confidence < float(minimum_confidence):
        violations.append("state_tracking_confidence")
    maximum_detuning = constraints.get("maximum_detuning_nm")
    if maximum_detuning is not None and abs(detuning) > float(maximum_detuning):
        violations.append("detuning")
    record["constraint_violations"] = violations
    record["trial_valid"] = not violations
    record["objective_available"] = True
    record["trial_outcome_class"] = "valid" if not violations else "physically_invalid"
    record["rejection_reason"] = "; ".join(violations)
    record["valid_low_response"] = bool(not violations and at_target < 1e-12)
    return record


def recovery_error(
    parameters: Mapping[str, Any], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """How far a proposed best design is from the known synthetic optimum."""

    canonical = design13.canonicalize(parameters, cfg)
    errors = {
        name: abs(float(canonical[name]) - float(SYNTHETIC_OPTIMUM[name]))
        for name in design13.RANGE_PARAMETERS
    }
    return {
        **{f"{name}_absolute_error": value for name, value in errors.items()},
        "grading_profile_recovered": canonical["grading_profile"]
        == SYNTHETIC_OPTIMUM["grading_profile"],
        "normalized_distance_to_optimum": design13.design_distance(
            canonical, SYNTHETIC_OPTIMUM, cfg
        ),
        "objective_at_proposed": objective_value(canonical, cfg),
        "objective_at_known_optimum": objective_value(SYNTHETIC_OPTIMUM, cfg),
    }


# ---------------------------------------------------------------------------
# baseline searches, for the efficiency comparison
# ---------------------------------------------------------------------------


def _sample(spec: Any, rng: random.Random) -> Any:
    if isinstance(spec, design13.ChoiceSpec):
        return rng.choice(list(spec.values))
    return rng.uniform(spec.lower, spec.upper)


def random_search(
    cfg: Mapping[str, Any], *, evaluations: int, seed: int
) -> list[dict[str, Any]]:
    """Uniform random sampling of the same search space, same evaluation budget.

    The honest control for "did Bayesian optimization help?".  It uses the same
    objective, the same constraints and the same budget, and its failures fail
    the same way.
    """

    rng = random.Random(int(seed))
    specs = design13.search_space_specs(cfg)
    rows: list[dict[str, Any]] = []
    for index in range(int(evaluations)):
        parameters = {spec.name: _sample(spec, rng) for spec in specs}
        rows.append(_evaluate_for_comparison(parameters, cfg, index, "random_search"))
    return rows


def grid_search(
    cfg: Mapping[str, Any], *, points_per_dimension: int = 4
) -> list[dict[str, Any]]:
    """A full factorial grid, evaluated in the traversal order Demo 12 uses."""

    specs = design13.search_space_specs(cfg)
    axes: list[list[Any]] = []
    names: list[str] = []
    for spec in specs:
        names.append(spec.name)
        if isinstance(spec, design13.ChoiceSpec):
            axes.append(list(spec.values))
        else:
            count = max(2, int(points_per_dimension))
            step = (spec.upper - spec.lower) / (count - 1)
            axes.append([spec.lower + step * index for index in range(count)])
    rows: list[dict[str, Any]] = []
    index = 0
    for combination in _product(axes):
        parameters = dict(zip(names, combination))
        rows.append(_evaluate_for_comparison(parameters, cfg, index, "grid_search"))
        index += 1
    return rows


def _product(axes: Sequence[Sequence[Any]]) -> Iterable[tuple[Any, ...]]:
    import itertools

    return itertools.product(*axes)


def _evaluate_for_comparison(
    parameters: Mapping[str, Any], cfg: Mapping[str, Any], index: int, method: str
) -> dict[str, Any]:
    base = {"evaluation_index": index, "search_method": method}
    try:
        record = evaluate(parameters, cfg)
    except (SyntheticFailure, DemoError) as exc:
        return {
            **base,
            **{f"parameter_{name}": value for name, value in dict(parameters).items()},
            "status": "failed",
            "failure_reason": str(exc),
            "chi2_at_target_wavelength_abs": None,
            "trial_valid": False,
            "synthetic": True,
            "data_label": SYNTHETIC_LABEL,
        }
    return {**base, **record, "status": "completed"}


def best_so_far(
    rows: Sequence[Mapping[str, Any]],
    *,
    metric: str = "chi2_at_target_wavelength_abs",
    require_valid: bool = True,
) -> list[dict[str, Any]]:
    """Running best over an evaluation sequence, with the raw points kept.

    Only valid, completed evaluations may improve the running best.  That is the
    whole point of the comparison: a method is not credited for finding a large
    number that fails quality control.
    """

    best: float | None = None
    trace: list[dict[str, Any]] = []
    for position, row in enumerate(rows, start=1):
        value = row.get(metric)
        usable = (
            value is not None
            and str(row.get("status", "completed")) == "completed"
            and (not require_valid or bool(row.get("trial_valid", True)))
        )
        if usable and (best is None or float(value) > best):
            best = float(value)
        trace.append(
            {
                "evaluations": position,
                "search_method": row.get("search_method"),
                "evaluation_value": None if value is None else float(value),
                "counted": bool(usable),
                "best_so_far": best,
            }
        )
    return trace


def evaluations_to_reach(
    trace: Sequence[Mapping[str, Any]], threshold: float
) -> int | None:
    """How many evaluations a method needed to reach ``threshold``."""

    for row in trace:
        best = row.get("best_so_far")
        if best is not None and float(best) >= float(threshold):
            return int(row["evaluations"])
    return None
