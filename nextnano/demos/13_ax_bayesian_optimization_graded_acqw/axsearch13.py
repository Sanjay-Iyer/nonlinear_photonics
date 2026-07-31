"""The Ax layer of Demo 13, and the immutable trial ledger beside it.

Ax API used
===========

``ax-platform`` **1.3.1**, through the supported service client
``ax.api.client.Client``:

* :meth:`Client.configure_experiment` with ``RangeParameterConfig`` /
  ``ChoiceParameterConfig``, including hierarchical ``dependent_parameters``;
* :meth:`Client.configure_optimization` with a string objective (comma
  separated and ``-``-prefixed for multi-objective) and string outcome
  constraints;
* :meth:`Client.configure_generation_strategy` for the initialization budget
  and seed;
* :meth:`Client.get_next_trials`, :meth:`Client.complete_trial`,
  :meth:`Client.mark_trial_failed`;
* :meth:`Client.save_to_json_file` / :meth:`Client.load_from_json_file` for
  checkpoint and resume;
* :meth:`Client.predict`, :meth:`Client.get_pareto_frontier`,
  :meth:`Client.summarize`.

No deprecated ``AxClient`` / ``ax.service`` entry point is used.

Why there is a ledger as well as a snapshot
===========================================

The Ax snapshot is Ax's state.  It holds what Ax needs to keep optimizing, not
what a physicist needs to defend a result: which nextnano input produced a
number, which QC test rejected a design, why a trial failed, how long it took.
The ledger is an append-only record of that, one immutable JSON file per trial
plus a JSONL index, and it is what every table in this demo is built from.  A
trial record is written once and never rewritten, so resuming a run cannot
quietly rewrite history.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import DemoError, write_json_atomically  # noqa: E402

import design13  # noqa: E402

#: The Ax release this module's API usage was written and tested against.
TESTED_AX_VERSION = "1.3.1"

#: Metric names Demo 13 may use in an Ax objective or outcome constraint.
#: Everything else lives in the ledger; keeping Ax's data model to the metrics
#: it actually optimizes over avoids silently modelling a metric that is only
#: ever reported.
OPTIMIZABLE_METRICS: tuple[str, ...] = (
    "chi2_at_target_wavelength_abs",
    "peak_chi2_abs",
    "detuning_nm_abs",
    "integrated_chi2_abs",
    "robustness_score",
    "weighted_score",
    "maximum_boundary_probability",
    "state_tracking_confidence",
    "orthonormality_error",
    "origin_independence_valid",
    "required_states_valid",
    "physical_qc_valid",
)

OPTIMIZATION_MODES: frozenset[str] = frozenset(
    {"target_wavelength", "intrinsic_peak", "multi_objective", "weighted_score"}
)


class AxUnavailableError(DemoError):
    """``ax-platform`` is not importable in this interpreter."""


def ax_version() -> str:
    try:
        import ax
    except Exception as exc:  # pragma: no cover - environment specific
        raise AxUnavailableError(
            "ax-platform is not installed in this interpreter; "
            "install the pinned version from requirements.txt "
            f"(ax-platform=={TESTED_AX_VERSION}). Original error: {exc}"
        ) from exc
    return str(getattr(ax, "__version__", "unknown"))


def _version_tuple(text: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in str(text).split("."):
        digits = "".join(char for char in chunk if char.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) or (0,)


def check_ax_version(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Compare the installed Ax against the pinned and minimum versions."""

    bo = cfg["bo"]
    installed = ax_version()
    required = str(bo.get("required_ax_version", TESTED_AX_VERSION))
    minimum = str(bo.get("minimum_ax_version", "1.0.0"))
    if _version_tuple(installed) < _version_tuple(minimum):
        raise DemoError(
            f"Demo 13 needs the Ax 1.x Client API; found ax-platform {installed}, "
            f"minimum {minimum}. The pre-1.0 AxClient API is deprecated and is "
            "deliberately not supported here."
        )
    return {
        "ax_version_installed": installed,
        "ax_version_pinned": required,
        "ax_version_minimum": minimum,
        "ax_version_matches_pin": installed == required,
        "ax_api": str(bo.get("api", "ax.api.client.Client")),
        "tested_against": TESTED_AX_VERSION,
    }


# ---------------------------------------------------------------------------
# objective and constraint construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OptimizationSpec:
    """The objective and constraints handed to Ax, in Ax's own string form."""

    mode: str
    objective: str
    outcome_constraints: tuple[str, ...]
    objective_metrics: tuple[str, ...]
    minimized_metrics: tuple[str, ...]
    constraint_metrics: tuple[str, ...]
    dropped_constraints: tuple[str, ...]
    weights: Mapping[str, float] = field(default_factory=dict)

    @property
    def is_multi_objective(self) -> bool:
        return len(self.objective_metrics) > 1

    @property
    def reported_metrics(self) -> tuple[str, ...]:
        seen: list[str] = []
        for name in (*self.objective_metrics, *self.constraint_metrics):
            if name not in seen:
                seen.append(name)
        return tuple(seen)

    def as_record(self) -> dict[str, Any]:
        return {
            "optimization_mode": self.mode,
            "ax_objective_string": self.objective,
            "ax_outcome_constraints": list(self.outcome_constraints),
            "objective_metrics": list(self.objective_metrics),
            "minimized_metrics": list(self.minimized_metrics),
            "constraint_metrics": list(self.constraint_metrics),
            "constraints_dropped_because_they_name_an_objective": list(
                self.dropped_constraints
            ),
            "weights": dict(self.weights),
            "multi_objective": self.is_multi_objective,
        }


def build_optimization_spec(cfg: Mapping[str, Any]) -> OptimizationSpec:
    """Translate the YAML objective mode and constraints into Ax strings."""

    bo = cfg["bo"]
    mode = str(bo.get("optimization_mode", "target_wavelength"))
    if mode not in OPTIMIZATION_MODES:
        raise DemoError(
            f"bo.optimization_mode must be one of {sorted(OPTIMIZATION_MODES)}, got {mode!r}"
        )
    objectives = (bo.get("objectives") or {}).get(mode)
    if not isinstance(objectives, Mapping):
        raise DemoError(f"bo.objectives.{mode} is missing")
    maximize = [str(name) for name in (objectives.get("maximize") or [])]
    minimize = [str(name) for name in (objectives.get("minimize") or [])]
    if not maximize and not minimize:
        raise DemoError(f"bo.objectives.{mode} names no metric to optimize")
    unknown = sorted(set(maximize + minimize) - set(OPTIMIZABLE_METRICS))
    if unknown:
        raise DemoError(f"unsupported objective metric(s): {', '.join(unknown)}")
    terms = [name for name in maximize] + [f"-{name}" for name in minimize]
    objective = ", ".join(terms)

    constraints_cfg = bo.get("outcome_constraints") or {}
    objective_metrics = tuple(maximize + minimize)
    constraints: list[str] = []
    constraint_metrics: list[str] = []
    dropped: list[str] = []

    def add(metric: str, operator: str, bound: float) -> None:
        # Ax rejects a constraint on a metric that is already an objective, and
        # so should we: "minimize detuning" and "keep detuning under 15 nm" are
        # the same statement made twice, and Ax must see only one of them.
        if metric in objective_metrics:
            dropped.append(f"{metric} {operator} {bound:g}")
            return
        constraints.append(f"{metric} {operator} {bound:g}")
        constraint_metrics.append(metric)

    if constraints_cfg.get("maximum_detuning_nm") is not None:
        add("detuning_nm_abs", "<=", float(constraints_cfg["maximum_detuning_nm"]))
    if constraints_cfg.get("maximum_boundary_probability") is not None:
        add(
            "maximum_boundary_probability",
            "<=",
            float(constraints_cfg["maximum_boundary_probability"]),
        )
    if constraints_cfg.get("minimum_state_tracking_confidence") is not None:
        add(
            "state_tracking_confidence",
            ">=",
            float(constraints_cfg["minimum_state_tracking_confidence"]),
        )
    if constraints_cfg.get("maximum_orthonormality_error") is not None:
        add(
            "orthonormality_error",
            "<=",
            float(constraints_cfg["maximum_orthonormality_error"]),
        )
    if bool(constraints_cfg.get("require_origin_independence", False)):
        add("origin_independence_valid", ">=", 1.0)
    if bool(constraints_cfg.get("require_expected_states", False)):
        add("required_states_valid", ">=", 1.0)
    if bool(constraints_cfg.get("require_physical_qc", False)):
        add("physical_qc_valid", ">=", 1.0)

    weights = dict((objectives.get("weights") or {})) if mode == "weighted_score" else {}
    return OptimizationSpec(
        mode=mode,
        objective=objective,
        outcome_constraints=tuple(constraints),
        objective_metrics=objective_metrics,
        minimized_metrics=tuple(minimize),
        constraint_metrics=tuple(constraint_metrics),
        dropped_constraints=tuple(dropped),
        weights=weights,
    )


def weighted_score(
    metrics: Mapping[str, Any], spec: OptimizationSpec, *, normalizers: Mapping[str, float] | None = None
) -> float | None:
    """Optional single number for ``weighted_score`` mode.

    Deliberately a *derived* metric: every physical quantity that feeds it stays
    in the ledger and in every table, so no individual metric ever disappears
    behind the score.
    """

    if not spec.weights:
        return None
    scale = dict(normalizers or {})
    total = 0.0
    for name, weight in spec.weights.items():
        value = metrics.get(name)
        if value is None or not math.isfinite(float(value)):
            return None
        reference = float(scale.get(name, 1.0)) or 1.0
        normalized = float(value) / reference
        # Smaller is better for detuning; everything else is larger-is-better.
        total += float(weight) * (-normalized if name.endswith("_abs") and "detuning" in name else normalized)
    return float(total)


# ---------------------------------------------------------------------------
# the experiment
# ---------------------------------------------------------------------------


def _parameter_configs(cfg: Mapping[str, Any]) -> list[Any]:
    """Build the Ax parameter configs for the configured encoding.

    ``hierarchical`` (the default) makes the abrupt/graded distinction
    structural: an abrupt trial simply has no grading parameters, so Ax cannot
    propose the same abrupt structure once per profile label.  Ax 1.3.1 requires
    a hierarchical space to be a *tree* -- a dependent parameter reachable from
    two parents raises ``UserInputError`` -- which is why the tree branches on a
    two-valued ``interface_mode`` rather than directly on ``grading_profile``.

    ``flat`` is the four-parameter form; there, duplicate abrupt structures are
    prevented by canonicalization and the deduplication key in
    :mod:`design13` instead.
    """

    from ax.api.configs import ChoiceParameterConfig, RangeParameterConfig

    space = cfg["bo"]["search_space"]
    encoding = str(space.get("encoding", "hierarchical"))
    if encoding not in {"hierarchical", "flat"}:
        raise DemoError("bo.search_space.encoding must be 'hierarchical' or 'flat'")

    configs: list[Any] = []
    for name in ("asymmetry_s", "central_barrier_thickness_nm"):
        entry = space[name]
        configs.append(
            RangeParameterConfig(
                name=name,
                bounds=(float(entry["lower"]), float(entry["upper"])),
                parameter_type="float",
            )
        )

    if encoding == "hierarchical":
        lower, upper = design13.graded_thickness_bounds(cfg)
        configs.insert(
            0,
            ChoiceParameterConfig(
                name="interface_mode",
                values=["abrupt", "graded"],
                parameter_type="str",
                dependent_parameters={
                    "abrupt": [],
                    "graded": ["grading_thickness_nm", "grading_profile"],
                },
            ),
        )
        configs.append(
            RangeParameterConfig(
                name="grading_thickness_nm",
                bounds=(lower, upper),
                parameter_type="float",
            )
        )
        configs.append(
            ChoiceParameterConfig(
                name="grading_profile",
                values=list(design13.graded_profiles(cfg)),
                parameter_type="str",
            )
        )
    else:
        entry = space["grading_thickness_nm"]
        configs.append(
            RangeParameterConfig(
                name="grading_thickness_nm",
                bounds=(float(entry["lower"]), float(entry["upper"])),
                parameter_type="float",
            )
        )
        configs.append(
            ChoiceParameterConfig(
                name="grading_profile",
                values=[str(value) for value in space["grading_profile"]["values"]],
                parameter_type="str",
            )
        )

    for name in design13.enabled_optional_parameters(cfg):
        entry = cfg["bo"]["optional_parameters"][name]
        if str(entry.get("type")) == "choice":
            configs.append(
                ChoiceParameterConfig(
                    name=name,
                    values=[str(value) for value in entry["values"]],
                    parameter_type="str",
                )
            )
        else:
            configs.append(
                RangeParameterConfig(
                    name=name,
                    bounds=(float(entry["lower"]), float(entry["upper"])),
                    parameter_type="float",
                )
            )
    return configs


def ax_parameters(
    canonical: Mapping[str, Any], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Express a canonical design in the *encoding Ax is using*.

    Needed wherever Demo 13 hands Ax a point it did not itself propose --
    surrogate slices, partial-dependence lines, warm-start observations -- since
    the hierarchical encoding's abrupt branch must not carry grading parameters
    at all, and its graded branch must always carry both.
    """

    space = cfg["bo"]["search_space"]
    values: dict[str, Any] = {
        "asymmetry_s": float(canonical["asymmetry_s"]),
        "central_barrier_thickness_nm": float(canonical["central_barrier_thickness_nm"]),
    }
    thickness = float(canonical.get("grading_thickness_nm", 0.0))
    profile = str(canonical.get("grading_profile", "abrupt"))
    for name in design13.enabled_optional_parameters(cfg):
        if name in canonical:
            values[name] = canonical[name]
    if str(space.get("encoding", "hierarchical")) != "hierarchical":
        values["grading_thickness_nm"] = thickness
        values["grading_profile"] = profile
        return values
    if profile == "abrupt" or thickness <= 0:
        values["interface_mode"] = "abrupt"
        return values
    lower, upper = design13.graded_thickness_bounds(cfg)
    values["interface_mode"] = "graded"
    values["grading_thickness_nm"] = min(max(thickness, lower), upper)
    values["grading_profile"] = (
        profile if profile in design13.graded_profiles(cfg) else design13.graded_profiles(cfg)[0]
    )
    return values


def create_client(cfg: Mapping[str, Any], spec: OptimizationSpec) -> Any:
    """A fresh, fully configured Ax ``Client``."""

    from ax.api.client import Client

    bo = cfg["bo"]
    client = Client(random_seed=int(bo.get("random_seed", 0)))
    client.configure_experiment(
        parameters=_parameter_configs(cfg),
        name=str((cfg.get("workflow") or {}).get("experiment_name", "demo13")),
        description=str(cfg.get("title", "Demo 13")),
    )
    client.configure_optimization(
        objective=spec.objective,
        outcome_constraints=list(spec.outcome_constraints) or None,
    )
    client.configure_generation_strategy(
        method=str(bo.get("generation_method", "fast")),
        initialization_budget=int(bo["num_initial_trials"]),
        initialization_random_seed=int(bo.get("random_seed", 0)),
        initialize_with_center=bool(bo.get("initialize_with_center", False)),
        # Warm-start observations inform the surrogate but must not consume the
        # initial-trial budget: `bo.num_initial_trials` is a promise about how
        # many new quasi-random designs this study will evaluate, and a Demo 12
        # import silently eating three of them would break that promise.
        use_existing_trials_for_initialization=False,
    )
    return client


def attach_warm_start(
    client: Any,
    cfg: Mapping[str, Any],
    spec: OptimizationSpec,
    observations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach already-computed observations to a *new* experiment.

    Each observation must supply every metric Ax models, objective and
    constraint alike; one that cannot is skipped with its reason recorded rather
    than completed with an invented value.
    """

    attached: list[dict[str, Any]] = []
    for observation in observations:
        parameters = ax_parameters(dict(observation["parameters"]), cfg)
        metrics = dict(observation["metrics"])
        missing = [
            name
            for name in spec.reported_metrics
            if metrics.get(name) is None
            or not isinstance(metrics.get(name), (int, float))
            or not math.isfinite(float(metrics[name]))
        ]
        if missing:
            attached.append(
                {
                    "parameters": parameters,
                    "ax_trial_index": None,
                    "attached": False,
                    "reason": "missing metric(s): " + ", ".join(sorted(missing)),
                }
            )
            continue
        try:
            index = client.attach_trial(parameters=parameters)
            client.complete_trial(
                index,
                raw_data={name: float(metrics[name]) for name in spec.reported_metrics},
            )
        except Exception as exc:
            attached.append(
                {
                    "parameters": parameters,
                    "ax_trial_index": None,
                    "attached": False,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        attached.append(
            {
                "parameters": parameters,
                "ax_trial_index": int(index),
                "attached": True,
                "reason": "",
            }
        )
    return attached


def load_client(path: Path) -> Any:
    from ax.api.client import Client

    return Client.load_from_json_file(str(path))


#: Attempts and initial backoff for the checkpoint rename. Six attempts with
#: doubling backoff spans about three seconds, which covers the window a
#: Windows antivirus or indexing service holds a freshly written file.
REPLACE_ATTEMPTS = 6
REPLACE_BACKOFF_SECONDS = 0.05


def save_client(client: Any, path: Path) -> Path:
    """Checkpoint Ax's state as safely as this filesystem allows.

    ``save_to_json_file`` writes in place. A power cut halfway through would
    leave a truncated snapshot and destroy the optimization history, which is
    exactly the failure this demo exists to survive, so the write goes to a
    sibling temporary file and is then renamed over the target.

    Two Windows realities complicate that:

    * the rename fails with ``PermissionError`` (WinError 5) while an antivirus
      scanner or indexing service still holds a handle on the file it has just
      seen appear -- a transient condition, observed on the work laptop at the
      fifth checkpoint of a run that had already checkpointed four times;
    * checkpoints happen after every generated and every completed trial, so a
      fixed temporary name means consecutive writes contend for one path.

    So the temporary name is unique per write, the rename is retried with
    backoff, and a rename that will not succeed degrades to a direct write
    rather than aborting.  Losing a licensed nextnano trial -- minutes of solver
    time already spent -- because a virus scanner was reading a JSON file would
    be an absurd way to end a run.  A direct write is less crash-safe for that
    one checkpoint; it is not less safe than not checkpointing at all.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    client.save_to_json_file(str(temporary))

    last_error: OSError | None = None
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(temporary, path)
            return path
        except OSError as exc:
            last_error = exc
            if attempt < REPLACE_ATTEMPTS - 1:
                time.sleep(REPLACE_BACKOFF_SECONDS * (2**attempt))

    try:
        path.write_text(temporary.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as exc:
        raise DemoError(
            f"could not checkpoint the Ax experiment to {path}: {type(exc).__name__}: "
            f"{exc}. The last rename error was {type(last_error).__name__}: "
            f"{last_error}. Optimization history cannot be preserved on this "
            "filesystem; check permissions, and exclude the results directory "
            "from real-time antivirus scanning."
        ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:  # pragma: no cover - best-effort cleanup
            pass
    return path


# ---------------------------------------------------------------------------
# generation metadata
# ---------------------------------------------------------------------------


def generation_metadata(client: Any, trial_index: int) -> dict[str, Any]:
    """Which generator proposed this trial, and at what acquisition value.

    Ax exposes the generation node through ``summarize()``; the acquisition
    value only lives on the generator run.  Both are read defensively: a missing
    field is reported as ``None``, never guessed, and never allowed to abort a
    licensed run.
    """

    record: dict[str, Any] = {
        "generation_method": None,
        "generator": None,
        "expected_acquisition_value": None,
        "model_predictions_available": False,
    }
    try:
        trial = client._experiment.trials[int(trial_index)]
        runs = list(getattr(trial, "generator_runs", []) or [])
        if not runs:
            return record
        run = runs[0]
        record["generation_method"] = getattr(run, "_generation_node_name", None)
        record["generator"] = str(getattr(run, "_generator_key", None) or "")or None
        metadata = dict(getattr(run, "gen_metadata", None) or {})
        for key, value in metadata.items():
            if str(getattr(key, "value", key)) == "expected_acquisition_value":
                record["expected_acquisition_value"] = (
                    float(value) if isinstance(value, (int, float)) else None
                )
        record["model_predictions_available"] = (
            getattr(run, "best_arm_predictions", None) is not None
        )
    except Exception as exc:  # pragma: no cover - defensive by design
        record["generation_metadata_error"] = f"{type(exc).__name__}: {exc}"
    return record


def surrogate_predictions(
    client: Any, points: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Surrogate mean and standard error at explicit points, or an explanation.

    Predictions are only meaningful once Ax has fitted a model; during the Sobol
    initialization phase this returns rows carrying the reason instead of
    numbers, so a surrogate plot can never be drawn from a model that does not
    exist yet.
    """

    rows: list[dict[str, Any]] = []
    try:
        predictions = client.predict(points=list(points))
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        return [
            {**dict(point), "prediction_available": False, "reason": reason}
            for point in points
        ]
    for point, prediction in zip(points, predictions):
        row: dict[str, Any] = {**dict(point), "prediction_available": True, "reason": ""}
        for metric, value in prediction.items():
            mean, sem = value if isinstance(value, tuple) else (value, None)
            row[f"{metric}_predicted_mean"] = float(mean)
            row[f"{metric}_predicted_standard_error"] = (
                None if sem is None else float(sem)
            )
        rows.append(row)
    return rows


def parameter_importance(client: Any) -> dict[str, Any]:
    """First-order Sobol sensitivity of the fitted Ax surrogate.

    This is a property of the *model*, not of the physics: it says how much the
    fitted GP's prediction moves with each parameter over the search space.  It
    is only as good as the model fit, it is undefined before a model exists, and
    it is reported with that caveat attached rather than as a physical ranking.
    """

    record: dict[str, Any] = {
        "method": "first-order Sobol indices of the fitted Ax surrogate "
        "(ax.utils.sensitivity.sobol_measures.ax_parameter_sens)",
        "available": False,
        "reason": "",
        "importance": {},
    }
    try:
        from ax.utils.sensitivity.sobol_measures import ax_parameter_sens

        adapter = client._generation_strategy.adapter
        if adapter is None:
            record["reason"] = "no fitted surrogate yet (still in the initialization phase)"
            return record
        sensitivity = ax_parameter_sens(adapter, order="first")
        record["available"] = True
        record["importance"] = {
            str(metric): _merge_one_hot({str(name): float(value) for name, value in values.items()})
            for metric, values in sensitivity.items()
        }
    except Exception as exc:
        record["reason"] = f"{type(exc).__name__}: {exc}"
    return record


def _merge_one_hot(values: Mapping[str, float]) -> dict[str, float]:
    """Fold Ax's one-hot columns back onto the parameter they came from.

    Ax models a categorical parameter as several ``<name>_OH_PARAM_<k>``
    columns, and leaving those in a results table reports an internal encoding
    detail as if it were a design parameter. First-order Sobol indices of the
    components of one categorical are summed, which is the standard aggregation
    for a group of variables that vary together.
    """

    merged: dict[str, float] = {}
    for name, value in values.items():
        base = name.split("_OH_PARAM_")[0] if "_OH_PARAM_" in name else name
        merged[base] = merged.get(base, 0.0) + float(value)
    return merged


def pareto_frontier(client: Any) -> list[dict[str, Any]]:
    """Ax's Pareto frontier over observed data, or an empty list with a reason."""

    try:
        frontier = client.get_pareto_frontier(use_model_predictions=False)
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for parameters, metrics, trial_index, arm_name in frontier:
        row: dict[str, Any] = {
            "trial_index": int(trial_index),
            "arm_name": str(arm_name),
            **{str(key): value for key, value in parameters.items()},
        }
        for metric, value in metrics.items():
            mean = value[0] if isinstance(value, tuple) else value
            row[str(metric)] = None if mean is None else float(mean)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# the immutable ledger
# ---------------------------------------------------------------------------


TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed", "rejected"})


@dataclass
class Ledger:
    """Append-only trial history on disk.

    One JSON file per trial under ``trials/``, plus ``trial_ledger.jsonl`` as an
    ordered index.  A terminal record is never overwritten: attempting it raises
    rather than losing history, which is what makes "resume" safe to run twice.
    """

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        (self.root / "trials").mkdir(parents=True, exist_ok=True)

    @property
    def index_path(self) -> Path:
        return self.root / "trial_ledger.jsonl"

    def _path(self, trial_index: int) -> Path:
        return self.root / "trials" / f"trial_{int(trial_index):04d}.json"

    def records(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted((self.root / "trials").glob("trial_*.json")):
            try:
                rows.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                raise DemoError(f"corrupt ledger record {path}: {exc}") from exc
        return sorted(rows, key=lambda row: int(row.get("trial_index", -1)))

    def record(self, trial_index: int) -> dict[str, Any] | None:
        path = self._path(trial_index)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, record: Mapping[str, Any], *, allow_update: bool = False) -> Path:
        trial_index = int(record["trial_index"])
        path = self._path(trial_index)
        existing = self.record(trial_index)
        if existing is not None and not allow_update:
            if str(existing.get("status")) in TERMINAL_STATUSES:
                raise DemoError(
                    f"trial {trial_index} already has a terminal ledger record "
                    f"({existing.get('status')}); Demo 13 never rewrites completed "
                    "trial history"
                )
        payload = dict(record)
        payload.setdefault("recorded_utc", dt.datetime.now(dt.timezone.utc).isoformat())
        write_json_atomically(path, payload)
        with self.index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str, sort_keys=True) + "\n")
        return path

    def terminal_records(self) -> list[dict[str, Any]]:
        return [row for row in self.records() if str(row.get("status")) in TERMINAL_STATUSES]

    def completed_records(self) -> list[dict[str, Any]]:
        return [row for row in self.records() if str(row.get("status")) == "completed"]

    def design_keys(self, cfg: Mapping[str, Any]) -> list[tuple[Any, ...]]:
        keys: list[tuple[Any, ...]] = []
        for row in self.records():
            parameters = row.get("parameters")
            if isinstance(parameters, Mapping):
                try:
                    keys.append(design13.design_key(parameters, cfg))
                except DemoError:
                    continue
        return keys


# ---------------------------------------------------------------------------
# iteration accounting
# ---------------------------------------------------------------------------


def iteration_of(trial_ordinal: int, cfg: Mapping[str, Any]) -> int:
    """Which BO round a trial belongs to; ``0`` is the initial design."""

    counts = design13.expected_evaluation_counts(cfg)
    initial = counts["num_initial_trials"]
    batch = max(1, counts["batch_size"])
    if trial_ordinal < initial:
        return 0
    return 1 + (trial_ordinal - initial) // batch


def plan(cfg: Mapping[str, Any], ledger: Ledger) -> dict[str, Any]:
    """Section 20's pre-run report, recomputed from the YAML on every run.

    Changing ``bo.num_iterations`` changes these numbers and nothing else has to
    be edited: the iteration count is read here and nowhere is it hardcoded.
    """

    counts = design13.expected_evaluation_counts(cfg)
    records = ledger.records()
    terminal = [row for row in records if str(row.get("status")) in TERMINAL_STATUSES]
    completed = [row for row in records if str(row.get("status")) == "completed"]
    failed = [row for row in records if str(row.get("status")) == "failed"]
    pending = [row for row in records if str(row.get("status")) not in TERMINAL_STATUSES]

    initial, batch = counts["num_initial_trials"], max(1, counts["batch_size"])
    done = len(terminal)
    completed_initial = min(done, initial)
    completed_iterations = max(0, (done - initial + batch - 1) // batch)
    remaining_initial = max(0, initial - completed_initial)
    remaining_iterations = max(0, counts["num_iterations"] - completed_iterations)

    runtimes = [
        float(row["runtime_seconds"])
        for row in completed
        if isinstance(row.get("runtime_seconds"), (int, float))
        and float(row["runtime_seconds"]) > 0
    ]
    mean_runtime = float(sum(runtimes) / len(runtimes)) if runtimes else None
    remaining_trials = remaining_initial + remaining_iterations * batch
    return {
        **counts,
        "total_expected_evaluations": counts["expected_maximum_new_solver_runs"],
        "evaluation_formula": "initial_trials + num_iterations * batch_size",
        "recorded_trials": len(records),
        "completed_trials": len(completed),
        "failed_trials": len(failed),
        "pending_trials": len(pending),
        "pending_trial_indices": [int(row["trial_index"]) for row in pending],
        "completed_initial_trials": completed_initial,
        "remaining_initial_trials": remaining_initial,
        "completed_bo_iterations": completed_iterations,
        "remaining_bo_iterations": remaining_iterations,
        "remaining_trials": remaining_trials,
        "mean_completed_runtime_seconds": mean_runtime,
        "estimated_remaining_runtime_seconds": (
            None if mean_runtime is None else mean_runtime * remaining_trials
        ),
        "estimated_runtime_basis": (
            "mean wall-clock time of completed licensed trials in this experiment"
            if mean_runtime is not None
            else "no completed licensed trial yet; runtime cannot be estimated"
        ),
    }


def plan_report_lines(plan_record: Mapping[str, Any]) -> list[str]:
    """The human-readable case-count block printed before a run starts."""

    # Deliberately ASCII: this block is printed to a Windows console, which
    # defaults to cp1252 and turns an em dash into a replacement character.
    estimate = plan_record.get("estimated_remaining_runtime_seconds")
    return [
        "Demo 13 - planned Bayesian-optimization budget",
        f"  initial trials              : {plan_record['num_initial_trials']}",
        f"  BO iterations               : {plan_record['num_iterations']}",
        f"  batch size                  : {plan_record['batch_size']}",
        f"  expected max new solver runs: {plan_record['expected_maximum_new_solver_runs']}"
        f"  ({plan_record['evaluation_formula']})",
        f"  completed trials            : {plan_record['completed_trials']}",
        f"  failed trials               : {plan_record['failed_trials']}",
        f"  pending trials              : {plan_record['pending_trials']}",
        f"  remaining trials            : {plan_record['remaining_trials']}",
        f"  completed BO iterations     : {plan_record['completed_bo_iterations']}",
        f"  remaining BO iterations     : {plan_record['remaining_bo_iterations']}",
        "  estimated remaining runtime : "
        + ("unknown - " + str(plan_record["estimated_runtime_basis"]) if estimate is None
           else f"{float(estimate) / 60.0:.1f} min ({plan_record['estimated_runtime_basis']})"),
    ]


# ---------------------------------------------------------------------------
# candidate generation with deduplication
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    """One Ax proposal, before anything has been simulated."""

    trial_index: int
    parameters: dict[str, Any]
    canonical: dict[str, Any]
    iteration: int
    generation: dict[str, Any]
    duplicate_of: int | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "trial_index": self.trial_index,
            "iteration": self.iteration,
            "candidate_id": f"t{self.trial_index:04d}",
            "parameters": dict(self.parameters),
            "canonical_parameters": dict(self.canonical),
            "duplicate_of_trial": self.duplicate_of,
            **{key: value for key, value in self.generation.items()},
        }


def generate_candidates(
    client: Any,
    cfg: Mapping[str, Any],
    ledger: Ledger,
    *,
    count: int,
    trial_ordinal: int,
) -> list[Candidate]:
    """Ask Ax for ``count`` candidates and annotate them.

    A proposal that canonicalizes onto a structure already in the ledger is
    marked as a duplicate here rather than silently rerun; the caller decides
    whether to abandon it.  This is where "abrupt with five different profile
    labels" stops being five nextnano runs.
    """

    try:
        proposals = client.get_next_trials(max_trials=int(count))
    except Exception as exc:
        raise DemoError(
            f"Ax could not generate the next candidate(s): {type(exc).__name__}: {exc}"
        ) from exc
    seen = ledger.design_keys(cfg)
    by_key = {}
    for row in ledger.records():
        parameters = row.get("parameters")
        if isinstance(parameters, Mapping):
            try:
                by_key.setdefault(design13.design_key(parameters, cfg), int(row["trial_index"]))
            except DemoError:
                continue
    candidates: list[Candidate] = []
    for offset, (trial_index, parameters) in enumerate(sorted(proposals.items())):
        values = {str(key): value for key, value in parameters.items()}
        try:
            canonical = design13.canonicalize(values, cfg)
        except DemoError:
            canonical = {}
        key = design13.design_key(values, cfg) if canonical else None
        duplicate = (
            by_key.get(key)
            if key is not None
            and bool(cfg["bo"]["search_space"].get("deduplicate_canonical_designs", True))
            else None
        )
        candidate = Candidate(
            trial_index=int(trial_index),
            parameters=values,
            canonical=canonical,
            iteration=iteration_of(trial_ordinal + offset, cfg),
            generation=generation_metadata(client, int(trial_index)),
            duplicate_of=duplicate,
        )
        if key is not None:
            by_key.setdefault(key, int(trial_index))
            seen.append(key)
        candidates.append(candidate)
    return candidates
