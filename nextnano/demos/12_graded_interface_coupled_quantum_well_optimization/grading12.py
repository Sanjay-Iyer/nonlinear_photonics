"""Pure, solver-free grading and optimization tools for Demo 12.

The functions in this module contain no nextnano or filesystem dependencies.
They are intentionally small enough to test with synthetic data on the home
laptop and are also used unchanged by the licensed workflow.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np


class GradingError(ValueError):
    """A requested composition profile or design is not physically valid."""


def _u(value: float | np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(value, dtype=float), 0.0, 1.0)


def profile_fraction(
    u: float | np.ndarray,
    shape: str,
    *,
    sigmoid_steepness: float = 10.0,
    erf_span_sigma: float = 3.0,
    staircase_steps: int = 16,
) -> np.ndarray:
    """Return a normalized monotone ramp ``f(0)=0, f(1)=1``.

    ``sigmoid`` and ``erf`` are endpoint-normalized truncated functions; this
    avoids the common error of requesting a nominal endpoint that the smooth
    profile never actually reaches. ``staircase_linear`` is a standalone
    solver-free midpoint staircase; the deck renderer uses endpoint-preserving
    ``j/(N-1)`` sublayer samples and validates that realized profile separately.
    """

    x = _u(u)
    key = str(shape).lower().replace("-", "_")
    if key in {"abrupt", "step"}:
        return np.where(x < 0.5, 0.0, 1.0)
    if key in {"linear", "native_linear"}:
        return x
    if key in {"sigmoid", "logistic"}:
        k = float(sigmoid_steepness)
        if k <= 0:
            raise GradingError("sigmoid_steepness must be positive")
        raw = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
        lo = 1.0 / (1.0 + math.exp(k / 2.0))
        hi = 1.0 / (1.0 + math.exp(-k / 2.0))
        return (raw - lo) / (hi - lo)
    if key in {"erf", "error_function"}:
        span = float(erf_span_sigma)
        if span <= 0:
            raise GradingError("erf_span_sigma must be positive")
        erf = np.vectorize(math.erf)
        raw = erf(span * (x - 0.5))
        lo, hi = math.erf(-span / 2.0), math.erf(span / 2.0)
        return (raw - lo) / (hi - lo)
    if key in {"cosine", "cosine_smoothed"}:
        return 0.5 - 0.5 * np.cos(np.pi * x)
    if key in {"staircase", "staircase_linear"}:
        steps = int(staircase_steps)
        if steps < 2:
            raise GradingError("staircase_steps must be at least 2")
        result = (np.floor(x * steps) + 0.5) / steps
        result = np.clip(result, 0.0, 1.0)
        result = np.where(x <= 0.0, 0.0, result)
        return np.where(x >= 1.0, 1.0, result)
    raise GradingError(f"unsupported grading profile {shape!r}")


def composition_profile(
    z_nm: Sequence[float] | np.ndarray,
    *,
    start_nm: float,
    end_nm: float,
    start_x: float,
    end_x: float,
    shape: str,
    **profile_options: Any,
) -> np.ndarray:
    """Evaluate one alloy ramp, constant outside its finite interval."""

    z = np.asarray(z_nm, dtype=float)
    if end_nm <= start_nm:
        raise GradingError("a graded interval must have positive thickness")
    if not (0.0 <= start_x <= 1.0 and 0.0 <= end_x <= 1.0):
        raise GradingError("alloy endpoints must lie in [0, 1]")
    u = (z - float(start_nm)) / (float(end_nm) - float(start_nm))
    f = profile_fraction(u, shape, **profile_options)
    return float(start_x) + (float(end_x) - float(start_x)) * f


def integrated_composition(z_nm: Sequence[float], alloy_x: Sequence[float]) -> float:
    """Return ``integral x_Al dz`` in nm (an areal-composition measure)."""

    z, x = np.asarray(z_nm, dtype=float), np.asarray(alloy_x, dtype=float)
    if z.ndim != 1 or x.shape != z.shape or z.size < 2 or np.any(np.diff(z) <= 0):
        raise GradingError("composition integration needs equal, increasing 1-D arrays")
    return float(np.trapezoid(x, z))


def profile_validation(
    z_nm: Sequence[float],
    alloy_x: Sequence[float],
    *,
    expected_start_x: float,
    expected_end_x: float,
    direction: int,
    endpoint_tolerance: float = 1e-9,
) -> dict[str, Any]:
    """Validate endpoints, range, finiteness and requested monotonic direction."""

    z, x = np.asarray(z_nm, dtype=float), np.asarray(alloy_x, dtype=float)
    finite = bool(np.all(np.isfinite(z)) and np.all(np.isfinite(x)))
    endpoints = bool(
        finite
        and abs(float(x[0]) - expected_start_x) <= endpoint_tolerance
        and abs(float(x[-1]) - expected_end_x) <= endpoint_tolerance
    )
    delta = np.diff(x)
    monotone = bool(np.all(delta >= -endpoint_tolerance)) if direction >= 0 else bool(
        np.all(delta <= endpoint_tolerance)
    )
    in_range = bool(np.all((x >= -endpoint_tolerance) & (x <= 1 + endpoint_tolerance)))
    return {
        "finite": finite,
        "endpoints_preserved": endpoints,
        "monotone": monotone,
        "composition_in_range": in_range,
        "passed": finite and endpoints and monotone and in_range,
    }


def mesh_resolution(thickness_nm: float, spacing_nm: float) -> int:
    """Conservative number of mesh intervals spanning a grade."""

    if thickness_nm <= 0:
        return 0
    if spacing_nm <= 0:
        raise GradingError("mesh spacing must be positive")
    return int(math.floor(float(thickness_nm) / float(spacing_nm) + 1e-12))


def required_grade_spacing_nm(thickness_nm: float, minimum_points: int) -> float:
    if thickness_nm <= 0:
        return math.inf
    if int(minimum_points) < 2:
        raise GradingError("minimum grid points per grade must be at least 2")
    return float(thickness_nm) / int(minimum_points)


def compare_profiles(
    z_nm: Sequence[float], reference_x: Sequence[float], candidate_x: Sequence[float]
) -> dict[str, float]:
    ref, candidate = np.asarray(reference_x, float), np.asarray(candidate_x, float)
    if ref.shape != candidate.shape or ref.shape != np.asarray(z_nm).shape:
        raise GradingError("profile comparison arrays must have the same shape")
    difference = candidate - ref
    return {
        "maximum_composition_difference": float(np.max(np.abs(difference))),
        "rms_composition_difference": float(np.sqrt(np.mean(difference**2))),
        "integrated_composition_difference_nm": integrated_composition(z_nm, candidate)
        - integrated_composition(z_nm, ref),
    }


def finite_difference_sensitivity(
    minus: float, nominal: float, plus: float, step: float
) -> dict[str, float]:
    """Central slope plus normalized drift measures for one perturbation pair."""

    if step <= 0:
        raise GradingError("finite-difference step must be positive")
    slope = (float(plus) - float(minus)) / (2.0 * float(step))
    scale = abs(float(nominal))
    return {
        "slope_per_unit": slope,
        "percent_change_per_0p1_unit": (100.0 * slope * 0.1 / scale) if scale else math.inf,
        "standard_deviation": float(np.std([minus, nominal, plus], ddof=0)),
        "worst_case_change": max(abs(float(minus) - nominal), abs(float(plus) - nominal)),
    }


def constraint_filter(
    rows: Sequence[Mapping[str, Any]], constraints: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Annotate candidates with transparent hard-constraint results."""

    tests: tuple[tuple[str, str, Callable[[float, float], bool]], ...] = (
        ("maximum_target_detuning_nm", "target_detuning_nm", lambda v, c: abs(v) <= c),
        ("maximum_boundary_probability", "boundary_probability", lambda v, c: v <= c),
        ("minimum_state_tracking_overlap", "state_tracking_confidence", lambda v, c: v >= c),
        ("maximum_origin_independence_error", "origin_independence_error", lambda v, c: v <= c),
    )
    output: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        failures: list[str] = []
        for constraint, column, predicate in tests:
            if constraint not in constraints:
                continue
            value = row.get(column)
            if value is None or not predicate(float(value), float(constraints[constraint])):
                failures.append(constraint)
        if bool(constraints.get("require_bound_states", False)) and not bool(
            row.get("bound_states_accepted", False)
        ):
            failures.append("require_bound_states")
        row["constraint_status"] = "satisfied" if not failures else "violated"
        row["constraint_failures"] = failures
        output.append(row)
    return output


def pareto_front(
    rows: Sequence[Mapping[str, Any]], objectives: Mapping[str, str]
) -> list[dict[str, Any]]:
    """Return nondominated rows for explicitly named max/min objectives."""

    valid = [dict(row) for row in rows if all(row.get(name) is not None for name in objectives)]
    front: list[dict[str, Any]] = []
    for i, row in enumerate(valid):
        dominated = False
        for j, other in enumerate(valid):
            if i == j:
                continue
            weak, strict = True, False
            for name, direction in objectives.items():
                a, b = float(row[name]), float(other[name])
                if direction == "maximize":
                    weak &= b >= a
                    strict |= b > a
                elif direction == "minimize":
                    weak &= b <= a
                    strict |= b < a
                else:
                    raise GradingError(f"objective direction must be maximize/minimize, got {direction!r}")
            if weak and strict:
                dominated = True
                break
        if not dominated:
            row["pareto_optimal"] = True
            front.append(row)
    return front


def optimum(rows: Sequence[Mapping[str, Any]], metric: str) -> Mapping[str, Any] | None:
    candidates = [row for row in rows if row.get(metric) is not None]
    return max(candidates, key=lambda row: abs(float(row[metric]))) if candidates else None


@dataclass(frozen=True)
class Interface:
    name: str
    position_nm: float
    start_x: float
    end_x: float
    groups: tuple[str, ...]


def select_interfaces(interfaces: Sequence[Interface], mode: str) -> list[Interface]:
    if mode in {"none", "abrupt"}:
        return []
    if mode == "all":
        return list(interfaces)
    key = mode.removesuffix("_only")
    return [interface for interface in interfaces if key in interface.groups]
