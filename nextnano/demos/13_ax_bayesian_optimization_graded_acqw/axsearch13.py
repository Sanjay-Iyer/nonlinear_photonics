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
import feasibility13  # noqa: E402

#: The Ax release this module's API usage was written and tested against.
TESTED_AX_VERSION = "1.3.1"

#: Metric names Demo 13 may use in an Ax objective or outcome constraint.
#: Everything else lives in the ledger; keeping Ax's data model to the metrics
#: it actually optimizes over avoids silently modelling a metric that is only
#: ever reported.
#: Every metric name Demo 13 may put in an Ax objective or constraint.
#:
#: The chi(2) metrics carry a ``relative_`` prefix because that is what they
#: are: Demo 11's Eq. 2 evaluated in relative mode, a lineshape and a trend with
#: no absolute scale. Naming them ``chi2_*`` invited exactly the reading the
#: units string spends a sentence denying.
#:
#: ``absolute_detuning_nm`` is the only detuning that may be constrained. The
#: signed value is reported everywhere and constrained nowhere: a design 13 nm
#: red of target and one 13 nm blue of it are equally far from it.
OPTIMIZABLE_METRICS: tuple[str, ...] = (
    "relative_chi2_at_target_wavelength_abs",
    "relative_peak_chi2_abs",
    "absolute_detuning_nm",
    "relative_integrated_chi2_abs",
    "robustness_score",
    "weighted_score",
    "maximum_boundary_probability",
    "state_tracking_confidence",
    "orthonormality_error",
    "origin_independence_valid",
    "required_states_valid",
    "physical_qc_valid",
)

#: Metric names that changed in the 2026-07-31 hardening pass, old -> new.
#: Experiments checkpointed before the rename are migrated on load.
RENAMED_METRICS: Mapping[str, str] = {
    # Deliberately assembled rather than written as literals: a bulk rename of
    # the old names across the tree would otherwise rewrite this table's own
    # keys and quietly turn it into an identity mapping.
    "chi2" + "_at_target_wavelength_abs": "relative_chi2_at_target_wavelength_abs",
    "peak_" + "chi2_abs": "relative_peak_chi2_abs",
    "detuning_nm" + "_abs": "absolute_detuning_nm",
    "integrated_" + "chi2_abs": "relative_integrated_chi2_abs",
}

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
    #: Configured constraints enforced outside Ax; see :mod:`feasibility13`.
    post_processing_constraints: tuple[str, ...] = ()

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
            "constraints_enforced_outside_ax": list(self.post_processing_constraints),
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

    objective_metrics = tuple(maximize + minimize)
    constraints: list[str] = []
    constraint_metrics: list[str] = []
    dropped: list[str] = []
    post_processing: list[str] = []

    # Which constraints Ax is *told about* is decided in feasibility13, from
    # whether a Gaussian surrogate can resolve each threshold at all. Every
    # configured constraint is still evaluated on every trial; see that module.
    for spec in feasibility13.build_constraints(cfg):
        if spec.enforcement != feasibility13.ENFORCEMENT_AX:
            post_processing.append(spec.ax_string)
            continue
        # Ax rejects a constraint on a metric that is already an objective, and
        # so should we: "minimize detuning" and "keep detuning under 15 nm" are
        # the same statement made twice, and Ax must see only one of them.
        if spec.metric in objective_metrics:
            dropped.append(spec.ax_string)
            continue
        constraints.append(spec.ax_string)
        constraint_metrics.append(spec.metric)

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
        post_processing_constraints=tuple(post_processing),
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

    grading_name = design13.grading_parameter_name(cfg)
    if encoding == "hierarchical":
        if grading_name == "grading_thickness_nm":
            lower, upper = design13.graded_thickness_bounds(cfg)
        else:
            lower, upper = design13.graded_fraction_bounds(cfg)
        configs.insert(
            0,
            ChoiceParameterConfig(
                name="interface_mode",
                values=["abrupt", "graded"],
                parameter_type="str",
                dependent_parameters={
                    "abrupt": [],
                    "graded": [grading_name, "grading_profile"],
                },
            ),
        )
        configs.append(
            RangeParameterConfig(
                name=grading_name,
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
        if grading_name == "grading_thickness_nm":
            entry = space["grading_thickness_nm"]
            bounds = (float(entry["lower"]), float(entry["upper"]))
        else:
            bounds = design13.graded_fraction_bounds(cfg)
        configs.append(
            RangeParameterConfig(
                name=grading_name, bounds=bounds, parameter_type="float"
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
    grading_name = design13.grading_parameter_name(cfg)
    for name in design13.enabled_optional_parameters(cfg):
        if name in canonical:
            values[name] = canonical[name]
    def _grading_value() -> float:
        if grading_name == "grading_thickness_nm":
            lower, upper = design13.graded_thickness_bounds(cfg)
            return min(max(thickness, lower), upper)
        maximum = design13.maximum_feasible_grading_for(canonical, cfg)
        lower, upper = design13.graded_fraction_bounds(cfg)
        fraction = float(canonical.get("_proposed_grading_fraction") or
                         (thickness / maximum if maximum > 0 else lower))
        return min(max(fraction, lower), upper)

    if str(space.get("encoding", "hierarchical")) != "hierarchical":
        values[grading_name] = _grading_value() if thickness > 0 else (
            0.0 if grading_name == "grading_thickness_nm"
            else design13.graded_fraction_bounds(cfg)[0]
        )
        values["grading_profile"] = profile
        return values
    if profile == "abrupt" or thickness <= 0:
        values["interface_mode"] = "abrupt"
        return values
    values["interface_mode"] = "graded"
    values[grading_name] = _grading_value()
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
    #: Opened for reanalysis: creates nothing and writes nothing.
    read_only: bool = False

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        if not self.read_only:
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
        """Append or update one trial record.

        A **terminal** record -- completed, failed or rejected -- is never
        rewritten, and ``allow_update`` does not unlock it.  History that can be
        overwritten by passing a flag is not history, and the one caller that
        passes the flag only ever means to finish a trial left *pending* by a
        machine without a licensed solver.  So the terminal check sits outside
        the ``allow_update`` branch rather than inside it, where it used to let
        a completed licensed trial be overwritten.

        Updating a non-terminal record is ordinary: that is how a pending trial
        becomes a completed one, and the JSONL index keeps both entries.
        """

        if self.read_only:
            raise DemoError(
                f"refusing to write ledger record for trial {record.get('trial_index')}: "
                "this ledger was opened read-only for analysis"
            )
        trial_index = int(record["trial_index"])
        path = self._path(trial_index)
        existing = self.record(trial_index)
        if existing is not None and str(existing.get("status")) in TERMINAL_STATUSES:
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


#: Ledger statuses that represent a proposal which never reached the solver.
NON_EVALUATION_STATUSES: frozenset[str] = frozenset({"rejected"})


def budget_accounting(cfg: Mapping[str, Any], ledger: Ledger) -> dict[str, Any]:
    """Section 3: proposals and evaluations counted separately.

    ``num_iterations`` means *valid model-based evaluations*, so a proposal
    rejected by preflight or as a duplicate is counted as a proposal and not as
    an evaluation. Conflating the two is how a study can report ten completed
    iterations having actually evaluated eight designs.
    """

    import accounting13

    records = ledger.records()
    counts = design13.expected_evaluation_counts(cfg)
    initial = counts["num_initial_trials"]

    def _is(row: Mapping[str, Any], status: str) -> bool:
        return str(row.get("status")) == status

    evaluations = [row for row in records if str(row.get("status")) not in NON_EVALUATION_STATUSES]
    sobol = [row for row in evaluations if str(row.get("generation_method")) == "Sobol"]
    model = [row for row in evaluations if str(row.get("generation_method")) == "MBM"]
    rejected = [row for row in records if _is(row, "rejected")]
    # Classification is delegated. This function used to test the reason string
    # for `geometry_preflight` or `canonical_duplicate` only, so a rejection
    # carrying any other reason -- every one of v3's seven sub-resolution
    # grades -- counted as neither, and the table reported 0 and 0 beside 7
    # abandoned trials.
    preflight_invalid = [
        row for row in rejected
        if accounting13.rejection_category(row) in accounting13.PREFLIGHT_CATEGORIES
    ]
    duplicates = [row for row in rejected if accounting13.is_duplicate(row)]
    completed = [row for row in evaluations if _is(row, "completed")]
    outcome = lambda name: [  # noqa: E731 - a local projection, not a policy
        row for row in completed if str(row.get("trial_outcome_class")) == name
    ]
    return {
        "sobol_proposals": len([r for r in records if str(r.get("generation_method")) == "Sobol"]),
        "sobol_observations_completed": len([r for r in sobol if _is(r, "completed")]),
        "model_based_proposals": len([r for r in records if str(r.get("generation_method")) == "MBM"]),
        "model_based_observations_completed": len([r for r in model if _is(r, "completed")]),
        "preflight_invalid_proposals": len(preflight_invalid),
        "duplicate_proposals": len(duplicates),
        "abandoned_ax_trials": len(rejected),
        "solver_attempts": len([r for r in evaluations if r.get("output_directory_path")]),
        "solver_completed_cases": len([r for r in evaluations if r.get("solver_completed")]),
        "ax_completed_observations": len(completed),
        "scientifically_feasible_observations": len(
            [r for r in completed if r.get("trial_valid")]
        ),
        "warning_only_observations": len(outcome(metrics_outcome_warning())),
        "rejected_observations": len(
            [r for r in completed if not r.get("trial_valid")]
        ),
        "mechanically_failed_trials": len([r for r in evaluations if _is(r, "failed")]),
        "requested_initial_trials": initial,
        "requested_bo_iterations": counts["num_iterations"],
        "batch_size": counts["batch_size"],
        "iteration_definition": (
            "one requested BO iteration = one valid model-based evaluation; "
            "preflight-invalid and duplicate proposals do not consume one"
        ),
    }


def metrics_outcome_warning() -> str:
    """Imported lazily to keep this module free of a metrics13 import cycle."""

    return "valid_with_warning"


def plan(cfg: Mapping[str, Any], ledger: Ledger) -> dict[str, Any]:
    """Section 20's pre-run report, recomputed from the YAML on every run.

    Changing ``bo.num_iterations`` changes these numbers and nothing else has to
    be edited: the iteration count is read here and nowhere is it hardcoded.
    """

    counts = design13.expected_evaluation_counts(cfg)
    bo = cfg["bo"]
    records = ledger.records()
    # A rejected proposal is a proposal, not an evaluation. Unless the YAML says
    # otherwise it must not consume one of the requested BO iterations, or a
    # study that hit a few impossible geometries would quietly run short.
    def _consumes_budget(row: Mapping[str, Any]) -> bool:
        if str(row.get("status")) != "rejected":
            return True
        reason = str(row.get("rejection_reason", ""))
        if REJECT_DUPLICATE in reason:
            return bool(bo.get("duplicate_counts_as_bo_iteration", False))
        return bool(bo.get("invalid_preflight_counts_as_bo_iteration", False))

    budgeted = [row for row in records if _consumes_budget(row)]
    terminal = [row for row in budgeted if str(row.get("status")) in TERMINAL_STATUSES]
    completed = [row for row in records if str(row.get("status")) == "completed"]
    failed = [row for row in records if str(row.get("status")) == "failed"]
    rejected = [row for row in records if str(row.get("status")) == "rejected"]
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
        "recorded_proposals": len(records),
        "budget_consuming_trials": len(budgeted),
        "rejected_proposals": len(rejected),
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
    #: Filled in by :func:`preflight` once the realized structure is known.
    design_hash: str | None = None
    preflight: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "trial_index": self.trial_index,
            "iteration": self.iteration,
            "candidate_id": f"t{self.trial_index:04d}",
            "parameters": dict(self.parameters),
            "canonical_parameters": dict(self.canonical),
            "duplicate_of_trial": self.duplicate_of,
            "design_hash": self.design_hash,
            **{key: value for key, value in self.generation.items()},
        }


#: Why a proposal never reached the solver.
REJECT_GEOMETRY = "geometry_preflight"
REJECT_DUPLICATE = "canonical_duplicate"
REJECT_UNRESOLVABLE = "canonicalization_failed"
#: A graded proposal whose realized width the mesh cannot resolve. Distinct from
#: `geometry_preflight` because the geometry is perfectly constructible -- it is
#: the *grade* that is not, and the fix is a different one.
REJECT_SUBRESOLUTION = "subresolution_grade"


def preflight(
    parameters: Mapping[str, Any],
    cfg: Mapping[str, Any],
    seen_hashes: Mapping[str, int],
) -> dict[str, Any]:
    """Decide, without touching the solver, whether a proposal may be run.

    The order is fixed and matters: canonicalize inactive parameters, realize
    the physical geometry, check that it can be built, hash the realized
    structure, then check for duplicates. Hashing before realization would let
    two proposals that build the same deck hash differently.
    """

    import geometry13

    verdict: dict[str, Any] = {
        "accepted": False,
        "rejection_reason": "",
        "canonical": {},
        "design_hash": None,
        "duplicate_of_trial": None,
        "maximum_feasible_grading_nm": None,
        "realized_grading_thickness_nm": None,
        "proposed_grading_fraction": None,
        "geometry_reason": "",
    }
    try:
        canonical = design13.canonicalize(parameters, cfg)
    except DemoError as exc:
        verdict["rejection_reason"] = f"{REJECT_UNRESOLVABLE}: {exc}"
        return verdict
    verdict["canonical"] = dict(canonical)
    verdict["proposed_grading_fraction"] = canonical.get("_proposed_grading_fraction")
    verdict["realized_grading_thickness_nm"] = canonical.get("grading_thickness_nm")
    verdict["maximum_feasible_grading_nm"] = canonical.get(
        "_maximum_feasible_grading_nm"
    ) or design13.maximum_feasible_grading_for(canonical, cfg)

    # A grade the mesh cannot resolve is not a grade. v2 quietly canonicalized
    # such a proposal to abrupt, which meant a design with no grading in it
    # entered the surrogate's training data wearing a profile label -- and is
    # why v2 cannot say whether grading helps. Rejecting instead costs one
    # regeneration attempt and no BO iteration, and keeps the graded branch's
    # observations honestly graded.
    if design13.rejects_subresolution_grades(cfg):
        minimum = design13.minimum_resolvable_grading_nm(cfg)
        realized, was_graded = design13.realized_grading_before_collapse(parameters, cfg)
        verdict["realized_grading_before_collapse_nm"] = realized if was_graded else None
        verdict["minimum_resolvable_grading_nm"] = minimum
        if was_graded and realized < minimum:
            maximum = verdict["maximum_feasible_grading_nm"] or 0.0
            unbuildable = maximum < minimum
            verdict["rejection_reason"] = (
                f"{REJECT_SUBRESOLUTION}: the graded branch proposed a realized width "
                f"of {realized:.4g} nm, below the {minimum:.4g} nm this mesh and "
                "profile implementation can resolve"
                + (
                    f"; no grade at all is constructible here, because the largest "
                    f"this geometry allows is {maximum:.4g} nm"
                    if unbuildable
                    else ""
                )
            )
            verdict["geometry_reason"] = verdict["rejection_reason"]
            return verdict

    try:
        resolved = design13.resolve_config(parameters, cfg)
    except DemoError as exc:
        verdict["rejection_reason"] = f"{REJECT_GEOMETRY}: {exc}"
        verdict["geometry_reason"] = str(exc)
        return verdict
    geometry = geometry13.evaluate(resolved)
    verdict["geometry_reason"] = geometry.reason
    if not geometry.feasible:
        verdict["rejection_reason"] = f"{REJECT_GEOMETRY}: {geometry.reason}"
        return verdict

    design_hash = design13.design_hash(parameters, cfg)
    verdict["design_hash"] = design_hash
    if bool(cfg["bo"]["search_space"].get("deduplicate_canonical_designs", True)):
        previous = seen_hashes.get(design_hash)
        if previous is not None:
            verdict["duplicate_of_trial"] = previous
            verdict["rejection_reason"] = (
                f"{REJECT_DUPLICATE}: same realized structure as trial {previous}"
            )
            return verdict
    verdict["accepted"] = True
    return verdict


def seen_design_hashes(ledger: Ledger, cfg: Mapping[str, Any]) -> dict[str, int]:
    """Realized-structure hash -> the first trial that claimed it.

    Rejected proposals are included when
    ``prevent_resuggestion_of_rejected_candidates`` is set, so Ax cannot spend
    the budget re-proposing a design already refused. Premium trial 13 was
    exactly that: trial 12's invalid geometry, proposed again.
    """

    remember_rejected = bool(
        cfg["bo"].get("prevent_resuggestion_of_rejected_candidates", True)
    )
    hashes: dict[str, int] = {}
    for row in ledger.records():
        status = str(row.get("status"))
        if status == "rejected" and not remember_rejected:
            continue
        stored = row.get("design_hash")
        if stored:
            hashes.setdefault(str(stored), int(row["trial_index"]))
            continue
        parameters = row.get("parameters")
        if isinstance(parameters, Mapping):
            try:
                hashes.setdefault(
                    design13.design_hash(parameters, cfg), int(row["trial_index"])
                )
            except DemoError:
                continue
    return hashes


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
