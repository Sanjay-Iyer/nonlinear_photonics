"""Demo 12 ingestion: warm-start observations (Section 10) and replay (Stage 2).

Both jobs read the same thing -- completed Demo 12 cases -- and both refuse to
guess.  A Demo 12 case only becomes a Demo 13 observation when its physics
configuration matches on every key the two demos must share; otherwise it is
recorded as rejected, with the reason, and never silently imported.

Stage 2 (replay) then asks the question that decides whether Bayesian
optimization is worth licensed solver time at all: *given the same finite set of
already-evaluated designs, how many evaluations does each search method need to
reach the best one?*  Replay uses only completed Demo 12 results and calls
nextnano exactly zero times.
"""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
import random
import sys
from typing import Any, Mapping, Sequence

import yaml

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import DemoError  # noqa: E402

import design13  # noqa: E402
import synthetic13  # noqa: E402

DEMO12_ID = "12_graded_interface_coupled_quantum_well_optimization"


@dataclass(frozen=True)
class Demo12Case:
    """One completed Demo 12 case, as read from its own artifacts."""

    case_id: str
    stage: str
    run_dir: Path
    config: Mapping[str, Any]
    observables: Mapping[str, Any]
    validation: Mapping[str, Any]
    status: str


# ---------------------------------------------------------------------------
# reading Demo 12
# ---------------------------------------------------------------------------


def find_demo12_run(cfg: Mapping[str, Any], results_root: Path | None) -> Path | None:
    """Newest Demo 12 run directory, unless the YAML names one explicitly."""

    configured = ((cfg.get("bo") or {}).get("warm_start") or {}).get("source_run_dir")
    if configured:
        path = Path(str(configured)).expanduser()
        return path if path.is_dir() else None
    if results_root is None:
        return None
    demo_root = Path(results_root) / DEMO12_ID
    if not demo_root.is_dir():
        return None
    runs = sorted((path for path in demo_root.iterdir() if path.is_dir()), reverse=True)
    return runs[0] if runs else None


def load_demo12_cases(run_dir: Path) -> list[Demo12Case]:
    """Read every case of one Demo 12 run from its per-case manifests."""

    run_dir = Path(run_dir)
    runs = run_dir / "runs"
    if not runs.is_dir():
        return []
    cases: list[Demo12Case] = []
    for case_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        manifest_path = case_dir / "run_manifest.json"
        config_path = case_dir / "demo_resolved.yaml"
        if not manifest_path.is_file() or not config_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise DemoError(f"unreadable Demo 12 case {case_dir.name}: {exc}") from exc
        cases.append(
            Demo12Case(
                case_id=str(manifest.get("case_id", case_dir.name)),
                stage=str((manifest.get("swept_parameters") or {}).get("stage", ""))
                or str(_stage_from_case_id(case_dir.name)),
                run_dir=case_dir,
                config=config,
                observables=dict(manifest.get("observables") or {}),
                validation=dict(manifest.get("validation") or {}),
                status=str(manifest.get("completion_status", "unknown")),
            )
        )
    return cases


def _stage_from_case_id(case_id: str) -> str:
    """Demo 12 encodes its stage in the case-id prefix."""

    prefixes = {"v": "stage1", "t": "stage2", "p": "stage3", "l": "stage4", "j": "stage5", "r": "stage6"}
    return prefixes.get(case_id[:1], "unknown")


def _value_at(config: Mapping[str, Any], dotted: str) -> Any:
    cursor: Any = config
    for part in str(dotted).split("."):
        if not isinstance(cursor, Mapping) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


# ---------------------------------------------------------------------------
# compatibility and warm-start ingestion
# ---------------------------------------------------------------------------


def compatibility(
    case: Demo12Case, cfg: Mapping[str, Any]
) -> tuple[bool, list[str]]:
    """Whether one Demo 12 case can be reused, and every reason it cannot."""

    warm = (cfg.get("bo") or {}).get("warm_start") or {}
    reasons: list[str] = []
    if case.status != "completed":
        reasons.append(f"case status is {case.status!r}, not 'completed'")
    stages = [str(name) for name in (warm.get("compatible_stages") or [])]
    if stages and case.stage not in stages:
        reasons.append(f"stage {case.stage!r} is not in compatible_stages")
    for key in warm.get("require_matching_physics_keys") or []:
        mine, theirs = _value_at(cfg, str(key)), _value_at(case.config, str(key))
        if mine is None or theirs is None:
            reasons.append(f"{key} missing on one side")
        elif isinstance(mine, (int, float)) and isinstance(theirs, (int, float)):
            if not math.isclose(float(mine), float(theirs), rel_tol=1e-9, abs_tol=1e-12):
                reasons.append(f"{key} differs ({theirs!r} vs {mine!r})")
        elif mine != theirs:
            reasons.append(f"{key} differs ({theirs!r} vs {mine!r})")
    profile = str(_value_at(case.config, "grading.profile") or "abrupt")
    if profile not in design13.GRADING_PROFILES:
        reasons.append(f"grading profile {profile!r} has no Demo 13 equivalent")
    implementation = str(_value_at(case.config, "grading.implementation") or "")
    thickness = float(_value_at(case.config, "grading.selected_thickness_nm") or 0.0)
    expected = "native" if profile in design13.NATIVE_PROFILES else "staircase"
    if thickness > 0 and implementation and implementation != expected:
        reasons.append(
            f"grading implementation {implementation!r} differs from the Demo 13 "
            f"mapping for {profile!r} ({expected!r})"
        )
    if str(_value_at(case.config, "grading.location_mode") or "all") != str(
        _value_at(cfg, "grading.location_mode") or "all"
    ):
        reasons.append("grading location_mode differs")
    for name in ("center_shift_nm", "interface_shift_nm"):
        if float(_value_at(case.config, f"grading.{name}") or 0.0) != 0.0:
            reasons.append(f"grading.{name} is nonzero; not a Demo 13 design point")
    if bool(warm.get("require_valid_qc", True)) and case.validation.get("passed") is False:
        reasons.append("Demo 12 validation did not pass")
    try:
        parameters = design13.parameters_from_config(case.config)
        design13.resolve_config(parameters, cfg)
    except DemoError as exc:
        reasons.append(f"parameters outside the Demo 13 design space: {exc}")
    else:
        for spec in design13.search_space_specs(cfg):
            if isinstance(spec, design13.RangeSpec) and spec.name in parameters:
                value = float(parameters[spec.name])
                if not spec.lower - 1e-9 <= value <= spec.upper + 1e-9:
                    reasons.append(
                        f"{spec.name}={value:g} lies outside the search range "
                        f"[{spec.lower:g}, {spec.upper:g}]"
                    )
    return (not reasons), reasons


def ingest(cases: Sequence[Demo12Case], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Map Demo 12 cases into Demo 13 observations, recording every decision.

    Section 10 asks for source demo, case id, source file, parameter mapping,
    metric mapping, QC status and whether Ax used it -- for *every* candidate,
    including the rejected ones.  That provenance is the table returned here.
    """

    warm = (cfg.get("bo") or {}).get("warm_start") or {}
    enabled = bool(warm.get("use_demo12_warm_start", False))
    maximum = int(warm.get("maximum_observations", 0) or 0)
    rows: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for case in cases:
        compatible, reasons = compatibility(case, cfg)
        parameters: dict[str, Any] | None = None
        metrics: dict[str, Any] = {}
        if compatible:
            parameters = design13.canonicalize(
                design13.parameters_from_config(case.config), cfg
            )
            metrics = map_metrics(case.observables, cfg, validation=case.validation)
        row = {
            "source_demo": DEMO12_ID,
            "source_case_id": case.case_id,
            "source_stage": case.stage,
            "source_file": str(case.run_dir / "run_manifest.json"),
            "source_config_file": str(case.run_dir / "demo_resolved.yaml"),
            "compatible": compatible,
            "incompatibility_reasons": "; ".join(reasons),
            "qc_status": "passed"
            if case.validation.get("passed") is True
            else ("failed" if case.validation.get("passed") is False else "not evaluated"),
            "solver_status": case.status,
            **{
                f"parameter_{name}": (None if parameters is None else parameters.get(name))
                for name in ("asymmetry_s", "central_barrier_thickness_nm",
                             "grading_thickness_nm", "grading_profile")
            },
            **{f"metric_{name}": value for name, value in metrics.items()},
            "parameter_mapping": "asymmetry_s<-structural_asymmetry(thick,thin); "
            "central_barrier_thickness_nm<-scientific.tunnel_barrier_nm; "
            "grading_thickness_nm<-grading.selected_thickness_nm; "
            "grading_profile<-grading.profile",
            "metric_mapping": "chi2_at_target_wavelength_abs<-|chi2_relative_at_reference|; "
            "peak_chi2_abs<-chi2_peak_magnitude; "
            "detuning_nm<-chi2_peak_wavelength_nm - reference_wavelength_nm",
            "used_by_ax": False,
            "not_used_reason": "" if compatible else "incompatible",
        }
        if compatible and not enabled:
            row["not_used_reason"] = "use_demo12_warm_start is false"
        elif compatible:
            accepted.append({"parameters": parameters, "metrics": metrics, "row": row})
        rows.append(row)

    used = 0
    for entry in accepted:
        if maximum and used >= maximum:
            entry["row"]["not_used_reason"] = (
                f"warm-start budget of {maximum} observations already filled"
            )
            continue
        if entry["metrics"].get("chi2_at_target_wavelength_abs") is None:
            entry["row"]["not_used_reason"] = "no usable target-wavelength metric"
            continue
        entry["row"]["used_by_ax"] = True
        used += 1
    return {
        "enabled": enabled,
        "provenance_rows": rows,
        "observations": [
            {"parameters": entry["parameters"], "metrics": entry["metrics"]}
            for entry in accepted
            if entry["row"]["used_by_ax"]
        ],
        "candidate_count": len(cases),
        "compatible_count": sum(1 for row in rows if row["compatible"]),
        "used_count": used,
    }


def ingest_warm_start(
    cfg: Mapping[str, Any], results_root: Path | None
) -> dict[str, Any]:
    """Read Demo 12 and decide what may be reused -- and nothing more.

    Deliberately separate from :func:`efficiency_comparison`: warm starting is a
    cheap file read that every mode may do, while the Stage 2 replay fits Ax
    models over a whole archive and belongs only to ``demo12_replay``.
    """

    run_dir = find_demo12_run(cfg, results_root)
    cases = load_demo12_cases(run_dir) if run_dir else []
    ingested = ingest(cases, cfg)
    ingested["demo12_run_dir"] = str(run_dir) if run_dir else None
    return ingested


def map_metrics(
    observables: Mapping[str, Any],
    cfg: Mapping[str, Any],
    *,
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Demo 12 observables in Demo 13's metric names.

    The three 0/1 validity flags Demo 13 constrains on are taken from Demo 12's
    own validation dictionary where it recorded them, and left as ``None``
    where it did not.  A missing flag is never filled in with a permissive
    default: a constraint that cannot be evaluated must visibly not be
    evaluated.
    """

    target = float((cfg.get("chi2") or {}).get("reference_wavelength_nm", 1550.0))
    checks = dict(validation or {})

    def number(value: Any) -> float | None:
        try:
            result = float(value)
        except (TypeError, ValueError):
            return None
        return result if math.isfinite(result) else None

    peak_wavelength = number(observables.get("chi2_peak_wavelength_nm"))
    at_target = number(observables.get("chi2_relative_at_reference"))
    peak = number(observables.get("chi2_peak_magnitude"))
    detuning = None if peak_wavelength is None else peak_wavelength - target
    boundary = number(observables.get("maximum_boundary_probability_bound_states"))
    confidence = number(observables.get("state_tracking_confidence"))
    orthonormality = max(
        number(observables.get("orthonormality_error_electron")) or 0.0,
        number(observables.get("orthonormality_error_heavy_hole")) or 0.0,
    )
    flags: dict[str, Any] = {}
    if "chi2_origin_independent" in checks:
        flags["origin_independence_valid"] = int(bool(checks["chi2_origin_independent"]))
    if "chi2_state_window_as_configured" in checks:
        flags["required_states_valid"] = int(
            bool(checks["chi2_state_window_as_configured"])
        )
    if "passed" in checks:
        flags["physical_qc_valid"] = int(bool(checks["passed"]))
    return {
        "chi2_at_target_wavelength_abs": None if at_target is None else abs(at_target),
        "peak_chi2_abs": None if peak is None else abs(peak),
        "peak_wavelength_nm": peak_wavelength,
        "detuning_nm": detuning,
        "detuning_nm_abs": None if detuning is None else abs(detuning),
        "maximum_boundary_probability": boundary,
        "state_tracking_confidence": confidence,
        "orthonormality_error": orthonormality,
        **flags,
    }


# ---------------------------------------------------------------------------
# Stage 2 replay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolPoint:
    """One already-evaluated design available for replay."""

    identifier: str
    parameters: Mapping[str, Any]
    metrics: Mapping[str, Any]
    valid: bool


def pool_from_ingest(ingested: Mapping[str, Any], cfg: Mapping[str, Any]) -> list[PoolPoint]:
    """Replay pool built from compatible Demo 12 rows."""

    points: list[PoolPoint] = []
    for row in ingested["provenance_rows"]:
        if not row.get("compatible"):
            continue
        parameters = {
            name: row.get(f"parameter_{name}")
            for name in ("asymmetry_s", "central_barrier_thickness_nm",
                         "grading_thickness_nm", "grading_profile")
        }
        if any(value is None for value in parameters.values()):
            continue
        metrics = {
            key[len("metric_"):]: value
            for key, value in row.items()
            if str(key).startswith("metric_")
        }
        if metrics.get("chi2_at_target_wavelength_abs") is None:
            continue
        points.append(
            PoolPoint(
                identifier=str(row["source_case_id"]),
                parameters=parameters,
                metrics=metrics,
                valid=row.get("qc_status") != "failed",
            )
        )
    return points


def synthetic_pool(cfg: Mapping[str, Any], *, points_per_dimension: int = 4) -> list[PoolPoint]:
    """A Demo-12-shaped pool from the synthetic surface, for plumbing tests.

    Used only when no licensed Demo 12 run exists.  Every row it produces is
    labelled synthetic and is never presented as a Demo 12 result.
    """

    rows = synthetic13.grid_search(cfg, points_per_dimension=points_per_dimension)
    points: list[PoolPoint] = []
    for index, row in enumerate(rows):
        if row.get("status") != "completed":
            continue
        parameters = {
            key[len("parameter_"):]: value
            for key, value in row.items()
            if str(key).startswith("parameter_")
        }
        points.append(
            PoolPoint(
                identifier=f"synthetic_{index:04d}",
                parameters=parameters,
                metrics={
                    name: row.get(name)
                    for name in (
                        "chi2_at_target_wavelength_abs", "peak_chi2_abs",
                        "peak_wavelength_nm", "detuning_nm", "detuning_nm_abs",
                        "maximum_boundary_probability", "state_tracking_confidence",
                        "orthonormality_error", "origin_independence_valid",
                        "required_states_valid", "physical_qc_valid",
                    )
                },
                valid=bool(row.get("trial_valid", True)),
            )
        )
    return points


def _snap(
    parameters: Mapping[str, Any], pool: Sequence[PoolPoint], cfg: Mapping[str, Any]
) -> int:
    distances = [
        design13.design_distance(parameters, point.parameters, cfg) for point in pool
    ]
    return min(range(len(distances)), key=distances.__getitem__)


def replay_random(
    pool: Sequence[PoolPoint], *, evaluations: int, seed: int
) -> list[dict[str, Any]]:
    """Random sampling without replacement over the replay pool."""

    rng = random.Random(int(seed))
    order = list(range(len(pool)))
    rng.shuffle(order)
    return [
        _replay_row(pool[index], position, "random_search")
        for position, index in enumerate(order[: int(evaluations)])
    ]


def replay_grid(pool: Sequence[PoolPoint], *, evaluations: int | None = None) -> list[dict[str, Any]]:
    """The pool in its own traversal order -- what the Demo 12 grid actually did."""

    limit = len(pool) if evaluations is None else int(evaluations)
    return [
        _replay_row(point, position, "grid_search")
        for position, point in enumerate(pool[:limit])
    ]


def replay_configuration(
    cfg: Mapping[str, Any], pool: Sequence[PoolPoint]
) -> tuple[dict[str, Any], list[str]]:
    """Drop the outcome constraints the replay pool cannot evaluate.

    A replay can only apply a constraint whose metric every pool point carries.
    Silently supplying a permissive default would let replayed Bayesian
    optimization accept designs the live loop would reject, which would make the
    efficiency comparison flattering and wrong.  The dropped constraints are
    returned so they can be reported instead.
    """

    available = {
        name
        for name in (pool[0].metrics if pool else {})
        if all(point.metrics.get(name) is not None for point in pool)
    }
    constraint_keys = {
        "maximum_detuning_nm": "detuning_nm_abs",
        "maximum_boundary_probability": "maximum_boundary_probability",
        "minimum_state_tracking_confidence": "state_tracking_confidence",
        "maximum_orthonormality_error": "orthonormality_error",
        "require_origin_independence": "origin_independence_valid",
        "require_expected_states": "required_states_valid",
        "require_physical_qc": "physical_qc_valid",
    }
    reduced = copy.deepcopy(dict(cfg))
    constraints = dict((reduced.get("bo") or {}).get("outcome_constraints") or {})
    dropped: list[str] = []
    for key, metric in constraint_keys.items():
        if key in constraints and metric not in available:
            constraints.pop(key)
            dropped.append(f"{key} (no {metric} in the replay pool)")
    reduced["bo"]["outcome_constraints"] = constraints
    return reduced, dropped


def replay_bayesian(
    pool: Sequence[PoolPoint],
    cfg: Mapping[str, Any],
    *,
    evaluations: int,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Run Ax over the replay pool, snapping each proposal to its nearest point.

    Ax proposes in the continuous space; the pool is discrete, so each proposal
    is answered with the closest already-evaluated design.  Snapping is the
    standard way to replay an archive, and its one distortion is recorded per
    evaluation as ``snap_distance`` so a reader can see how far the answer was
    from the question.
    """

    import axsearch13

    if not pool:
        return []
    reduced, dropped = replay_configuration(cfg, pool)
    if seed is not None:
        reduced["bo"]["random_seed"] = int(seed)
    spec = axsearch13.build_optimization_spec(reduced)
    client = axsearch13.create_client(reduced, spec)
    cfg = reduced
    rows: list[dict[str, Any]] = []
    used: set[str] = set()
    for position in range(int(evaluations)):
        try:
            proposals = client.get_next_trials(max_trials=1)
        except Exception:
            break
        for trial_index, parameters in proposals.items():
            values = {str(key): value for key, value in parameters.items()}
            canonical = design13.canonicalize(values, cfg)
            index = _snap(canonical, pool, cfg)
            point = pool[index]
            row = _replay_row(point, position, "bayesian_optimization")
            row["snap_distance"] = design13.design_distance(
                canonical, point.parameters, cfg
            )
            row["repeat_of_earlier_pool_point"] = point.identifier in used
            row["constraints_dropped_for_replay"] = "; ".join(dropped)
            used.add(point.identifier)
            rows.append(row)
            raw = {
                name: float(point.metrics[name])
                for name in spec.reported_metrics
                if point.metrics.get(name) is not None
            }
            missing = set(spec.reported_metrics) - set(raw)
            if missing:
                client.mark_trial_failed(
                    int(trial_index),
                    failed_reason="replay pool has no value for " + ", ".join(sorted(missing)),
                )
            else:
                client.complete_trial(int(trial_index), raw_data=raw)
    return rows


def _replay_row(point: PoolPoint, position: int, method: str) -> dict[str, Any]:
    return {
        "evaluation_index": position,
        "search_method": method,
        "pool_point_id": point.identifier,
        "status": "completed",
        "trial_valid": bool(point.valid),
        **{f"parameter_{name}": value for name, value in point.parameters.items()},
        **{str(name): value for name, value in point.metrics.items()},
    }


def efficiency_comparison(
    pool: Sequence[PoolPoint],
    cfg: Mapping[str, Any],
    *,
    evaluations: int,
    seed: int,
    metric: str = "chi2_at_target_wavelength_abs",
    fraction_of_best: float = 0.95,
) -> dict[str, Any]:
    """How many evaluations each method needs to reach the best known design."""

    values = [
        float(point.metrics[metric])
        for point in pool
        if point.valid and point.metrics.get(metric) is not None
    ]
    if not values:
        return {"available": False, "reason": "replay pool has no valid metric values"}
    best_known = max(values)
    threshold = float(fraction_of_best) * best_known
    _reduced, dropped = replay_configuration(cfg, pool)
    methods = {
        "bayesian_optimization": replay_bayesian(
            pool, cfg, evaluations=evaluations, seed=seed
        ),
        "random_search": replay_random(pool, evaluations=evaluations, seed=seed),
        "grid_search": replay_grid(pool, evaluations=evaluations),
    }
    summary: list[dict[str, Any]] = []
    traces: dict[str, list[dict[str, Any]]] = {}
    for name, rows in methods.items():
        trace = synthetic13.best_so_far(rows, metric=metric, require_valid=True)
        traces[name] = trace
        summary.append(
            {
                "search_method": name,
                "evaluations_run": len(rows),
                "best_found": trace[-1]["best_so_far"] if trace else None,
                "best_known_in_pool": best_known,
                "threshold_fraction_of_best": fraction_of_best,
                "threshold_value": threshold,
                "evaluations_to_threshold": synthetic13.evaluations_to_reach(
                    trace, threshold
                ),
                "reached_threshold": synthetic13.evaluations_to_reach(trace, threshold)
                is not None,
                "constraints_dropped_for_replay": "; ".join(dropped),
            }
        )
    return {
        "available": True,
        "metric": metric,
        "pool_size": len(pool),
        "best_known_in_pool": best_known,
        "constraints_dropped_for_replay": dropped,
        "summary": summary,
        "traces": traces,
        "evaluations": {name: rows for name, rows in methods.items()},
    }
