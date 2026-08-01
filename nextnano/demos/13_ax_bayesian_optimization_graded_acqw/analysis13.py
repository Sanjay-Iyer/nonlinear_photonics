"""Read-only reanalysis of a finished Ax study.

Two jobs, both of which exist because reporting must never be able to damage or
misrepresent a completed licensed run.

**Protecting the experiment.**  The 2026-07-31 study cost sixteen premium
nextnano++ trials.  Its snapshot, ledger and trial directories are the record of
that spend and are immutable.  :func:`state_manifest` hashes them so a later run
can *prove* it changed nothing, and :func:`verify_state_manifest` is what turns
that proof into a test.

**Reconstructing a predictive model.**  ``Client.load_from_json_file`` restores
the experiment and the generation strategy, but *not* a fitted surrogate:
``GenerationStrategy.adapter`` is ``None`` on a freshly deserialized client
because the adapter is built during ``gen`` and is not serialized.  Every
downstream prediction therefore failed with

    UnsupportedError: Predicting with the GenerationStrategy's adapter failed
    because the current GenerationNode is not predictive.

and the surrogate plots, partial-dependence curves, acquisition surfaces and
parameter-importance tables came out empty -- while the observations they
needed were sitting in the file all along.

The fix is to refit, and the whole difficulty is doing that without disturbing
anything:

* ``GenerationStrategy.fit`` is the public entry point, but it calls
  ``_maybe_transition_to_next_node`` first, so it can *advance* the strategy;
* ``GenerationNode._fit`` does not transition, but it clears the node's
  ``_generator_spec_to_gen_from`` and stores a fitted adapter on the node, so it
  mutates the object it is called on;
* neither may touch the caller's client, because the same client object is used
  by the rest of the run.

So reconstruction always happens on a **separate client loaded from the same
file**, is fitted through the non-transitioning path, and is never saved.  The
original client keeps ``adapter is None`` and its current node unchanged, and
the snapshot on disk keeps its hash.  :func:`reconstruct_predictive_model`
returns a record of exactly that, which becomes
``analysis_model_reconstruction.json``.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

#: Files whose contents define the experiment. Hashed individually.
CRITICAL_FILES: tuple[str, ...] = (
    "ax_experiment_snapshot.json",
    "trial_ledger.jsonl",
    "experiment_schema.json",
    "demo_yaml_snapshot.yaml",
    "warm_start_attachments.json",
)

#: Directories whose file count and aggregate hash are recorded.
CRITICAL_TREES: tuple[str, ...] = ("trials", "runs")

#: Written next to the reports, never inside the protected experiment directory.
RECONSTRUCTION_FILENAME = "analysis_model_reconstruction.json"


class ReconstructionError(RuntimeError):
    """Raised only when the caller asked for a model and must not proceed."""


# ---------------------------------------------------------------------------
# Phase 1 -- proving the experiment state was not touched
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_manifest(root: Path) -> dict[str, Any]:
    """File count and a single order-independent hash for a directory tree.

    Hashing every trial directory's contents individually would make the
    manifest enormous for a sixteen-trial licensed run (each trial holds raw
    solver output).  Hashing relative paths and sizes catches the failure this
    guards against -- a reporting run deleting, adding or truncating a trial
    record -- at a cost that stays constant.
    """

    if not root.is_dir():
        return {"present": False, "file_count": 0, "total_bytes": 0, "tree_hash": None}
    entries: list[tuple[str, int]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            entries.append((path.relative_to(root).as_posix(), path.stat().st_size))
    digest = hashlib.sha256()
    for name, size in entries:
        digest.update(f"{name}:{size}\n".encode("utf-8"))
    return {
        "present": True,
        "file_count": len(entries),
        "total_bytes": sum(size for _, size in entries),
        "tree_hash": digest.hexdigest(),
    }


def state_manifest(state_dir: Path) -> dict[str, Any]:
    """Counts and hashes for everything that makes the experiment the experiment."""

    state_dir = Path(state_dir)
    files: dict[str, Any] = {}
    for name in CRITICAL_FILES:
        path = state_dir / name
        if path.is_file():
            files[name] = {
                "present": True,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        else:
            files[name] = {"present": False, "bytes": 0, "sha256": None}
    trees = {name: _tree_manifest(state_dir / name) for name in CRITICAL_TREES}
    ledger_lines = 0
    ledger = state_dir / "trial_ledger.jsonl"
    if ledger.is_file():
        ledger_lines = sum(
            1 for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    return {
        "experiment_state_dir": str(state_dir),
        "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": files,
        "trees": trees,
        "ledger_record_count": ledger_lines,
        "trial_file_count": trees["trials"]["file_count"],
    }


def verify_state_manifest(
    state_dir: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare the directory against a previously captured manifest.

    Returns a verdict rather than raising, so a caller can report the
    difference precisely instead of only that something differed.
    """

    current = state_manifest(state_dir)
    changed: list[str] = []
    for name in CRITICAL_FILES:
        was = (manifest.get("files") or {}).get(name) or {}
        now = current["files"][name]
        if was.get("sha256") != now.get("sha256") or was.get("present") != now.get("present"):
            changed.append(name)
    for name in CRITICAL_TREES:
        was = (manifest.get("trees") or {}).get(name) or {}
        now = current["trees"][name]
        if was.get("tree_hash") != now.get("tree_hash"):
            changed.append(f"{name}/")
    return {
        "unchanged": not changed,
        "changed_entries": changed,
        "expected_ledger_record_count": manifest.get("ledger_record_count"),
        "actual_ledger_record_count": current["ledger_record_count"],
        "captured_utc": manifest.get("captured_utc"),
        "verified_utc": current["captured_utc"],
    }


def terminal_ledger_fingerprint(state_dir: Path) -> dict[str, str]:
    """A hash per *terminal* ledger record, keyed by trial index.

    Terminal records -- completed, failed, rejected -- are immutable by
    contract.  This is the finest-grained protection available and is what the
    "analysis never modifies a terminal record" test compares.
    """

    ledger = Path(state_dir) / "trial_ledger.jsonl"
    fingerprints: dict[str, str] = {}
    if not ledger.is_file():
        return fingerprints
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(record.get("status")) not in {"completed", "failed", "rejected"}:
            continue
        index = str(record.get("trial_index"))
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        fingerprints[index] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return fingerprints


# ---------------------------------------------------------------------------
# Phase 2 -- rebuilding a predictive adapter from completed observations
# ---------------------------------------------------------------------------


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _completed_data(experiment: Any) -> tuple[Any, dict[str, Any]]:
    """Observations a surrogate may legitimately be fitted to.

    Excludes anything that is not a completed trial and any row whose mean is
    not finite.  A mechanically failed trial has no objective -- teaching the
    surrogate a number for it would be inventing physics -- and Ax already
    records it as failed rather than as a value, so this is belt-and-braces
    against a hand-edited or partially written snapshot.
    """

    from ax.core.base_trial import TrialStatus
    from ax.core.data import Data

    data = experiment.lookup_data()
    frame = data.df
    report: dict[str, Any] = {
        "rows_in_snapshot": int(len(frame)),
        "rows_dropped_not_completed": 0,
        "rows_dropped_non_finite": 0,
    }
    if len(frame) == 0:
        return data, report

    completed = {
        int(index)
        for index, trial in experiment.trials.items()
        if trial.status == TrialStatus.COMPLETED
    }
    kept = frame[frame["trial_index"].isin(sorted(completed))]
    report["rows_dropped_not_completed"] = int(len(frame) - len(kept))
    finite_mask = kept["mean"].map(_finite)
    filtered = kept[finite_mask]
    report["rows_dropped_non_finite"] = int(len(kept) - len(filtered))
    report["rows_used"] = int(len(filtered))
    # One trial contributes one row per modelled metric, so the row count is a
    # multiple of the trial count. Quoting rows as "observations" would inflate
    # the apparent evidence fourfold; both are reported, separately named.
    report["trials_used"] = int(filtered["trial_index"].nunique()) if len(filtered) else 0
    report["completed_trials"] = len(completed)
    report["metrics_used"] = sorted(str(name) for name in filtered["metric_name"].unique())
    report["constant_metrics"] = sorted(
        str(name)
        for name, group in filtered.groupby("metric_name")
        if float(group["mean"].std(ddof=0) or 0.0) == 0.0
    )
    if len(filtered) == len(frame):
        return data, report
    return Data(df=filtered.reset_index(drop=True)), report


@dataclass
class ReconstructedModel:
    """A refitted surrogate plus the honest story of how it was obtained."""

    adapter: Any
    search_space: Any
    optimization_config: Any
    record: dict[str, Any] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return self.adapter is not None

    @property
    def reason(self) -> str:
        return str(self.record.get("fit_status_reason", ""))

    def check_membership(self, point: Mapping[str, Any]) -> str | None:
        """``None`` when the point is a valid parameterization, else why not.

        Hierarchical search spaces are strict in both directions: the abrupt
        branch must **not** carry the grading children, and the graded branch
        must carry all of them.
        """

        try:
            self.search_space.check_membership(
                parameterization=dict(point),
                raise_error=True,
                check_all_parameters_present=True,
            )
        except Exception as exc:
            return f"{type(exc).__name__}: {exc}"
        return None

    def predict(self, points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Posterior mean and standard error per metric, or a truthful reason.

        The reason is about *this* model and *this* point.  It never claims that
        licensed output is missing, because by the time anything calls this the
        licensed output is exactly what the model was fitted to.
        """

        from ax.core.observation import ObservationFeatures

        rows: list[dict[str, Any]] = []
        if self.adapter is None:
            reason = self.reason or "predictive adapter could not be reconstructed"
            return [
                {**dict(point), "prediction_available": False, "reason": reason}
                for point in points
            ]

        valid: list[tuple[int, dict[str, Any]]] = []
        rows = [
            {**dict(point), "prediction_available": False, "reason": ""}
            for point in points
        ]
        for index, point in enumerate(points):
            problem = self.check_membership(point)
            if problem is None:
                valid.append((index, dict(point)))
            else:
                rows[index]["reason"] = (
                    "point is not a valid parameterization of the experiment's "
                    f"search space: {problem}"
                )
        if not valid:
            return rows

        try:
            mean, covariance = self.adapter.predict(
                observation_features=[
                    ObservationFeatures(parameters=point) for _, point in valid
                ]
            )
        except Exception as exc:
            reason = (
                "predictive adapter was reconstructed but prediction failed: "
                f"{type(exc).__name__}: {exc}"
            )
            for index, _ in valid:
                rows[index]["reason"] = reason
            return rows

        for position, (index, _) in enumerate(valid):
            row = rows[index]
            row["prediction_available"] = True
            row["reason"] = ""
            for metric in mean:
                variance = covariance[metric][metric][position]
                row[f"{metric}_predicted_mean"] = float(mean[metric][position])
                row[f"{metric}_predicted_standard_error"] = (
                    float(variance) ** 0.5 if float(variance) >= 0.0 else None
                )
        return rows

    def parameter_importance(self) -> dict[str, Any]:
        """First-order Sobol indices of the refitted surrogate, with caveats.

        Two things make this easy to over-read and both are reported rather
        than hidden: it describes the *fitted model*, not the physics, and with
        sixteen observations over four parameters it is an indication of what
        the surrogate leans on, not a significance test.  Indices for a metric
        that is constant in the training data are undefined; those come back as
        NaN from Ax and are reported as unavailable rather than as zero.
        """

        record: dict[str, Any] = {
            "method": "first-order Sobol indices of the refitted analysis surrogate "
            "(ax.utils.sensitivity.sobol_measures.ax_parameter_sens)",
            "available": False,
            "reason": "",
            "importance": {},
            "observations_used": self.record.get("observations_used"),
            "interpretation_caveat": (
                "A property of the fitted surrogate, not of the physics. With "
                f"{self.record.get('observations_used')} observations this ranks what the "
                "model leans on; it is not a statistical significance test, and no "
                "parameter should be called unimportant on this basis alone."
            ),
        }
        if self.adapter is None:
            record["reason"] = self.reason or "no predictive adapter was reconstructed"
            return record
        try:
            from ax.utils.sensitivity.sobol_measures import ax_parameter_sens

            sensitivity = ax_parameter_sens(self.adapter, order="first")
        except Exception as exc:
            record["reason"] = f"{type(exc).__name__}: {exc}"
            return record

        importance: dict[str, dict[str, float]] = {}
        undefined: list[str] = []
        for metric, values in sensitivity.items():
            merged = _merge_one_hot(
                {str(name): float(value) for name, value in values.items()}
            )
            if not merged or any(not math.isfinite(v) for v in merged.values()):
                undefined.append(str(metric))
                continue
            importance[str(metric)] = merged
        record["available"] = bool(importance)
        record["importance"] = importance
        if undefined:
            record["metrics_without_defined_importance"] = sorted(undefined)
            record["metrics_without_defined_importance_reason"] = (
                "sensitivity indices are undefined for a metric that is constant "
                "across the training observations"
            )
        if not importance:
            record["reason"] = (
                "sensitivity indices were undefined for every metric; this happens "
                "when the modelled outcomes do not vary across the observations"
            )
        return record


def _merge_one_hot(values: Mapping[str, float]) -> dict[str, float]:
    """Fold Ax's ``<name>_OH_PARAM_<k>`` columns back onto their parameter."""

    merged: dict[str, float] = {}
    for name, value in values.items():
        base = name.split("_OH_PARAM_")[0] if "_OH_PARAM_" in name else name
        merged[base] = merged.get(base, 0.0) + float(value)
    return merged


def _fit_without_transition(strategy: Any, experiment: Any, data: Any) -> tuple[Any, str]:
    """Fit the strategy's current node in place, without advancing it.

    ``GenerationStrategy.fit`` would transition first.  Calling the node's own
    ``_fit`` skips that, which is the whole point: reanalysis must observe the
    study exactly where it stopped, not nudge it one node further.
    """

    node = strategy._curr
    before = strategy.current_node_name
    strategy.experiment = experiment
    node._fit(experiment=experiment, data=data)
    after = strategy.current_node_name
    if before != after:  # pragma: no cover - _fit does not transition
        raise ReconstructionError(
            f"fitting moved the generation strategy from {before} to {after}"
        )
    return strategy.adapter, str(before)


def _fit_fresh_botorch(experiment: Any, data: Any) -> Any:
    """Last resort: a plain modular BoTorch adapter over the same experiment.

    Used only when the study stopped on a node that has no surrogate at all --
    a run that never left Sobol.  It preserves the search space and the
    optimization config because both come from the experiment, but it is *not*
    the model Ax generated with, and the reconstruction record says so.
    """

    from ax.adapter.registry import Generators

    return Generators.BOTORCH_MODULAR(experiment=experiment, data=data)


def reconstruct_predictive_model(
    snapshot_path: Path,
    *,
    probe_point: Mapping[str, Any] | None = None,
) -> ReconstructedModel:
    """Refit a predictive surrogate from a finished study, changing nothing.

    ``snapshot_path`` is re-loaded into a private client, so whatever the caller
    is holding is untouched, and nothing is ever written back.
    """

    from ax.api.client import Client

    snapshot_path = Path(snapshot_path)
    started = dt.datetime.now(dt.timezone.utc)
    record: dict[str, Any] = {
        "reconstruction_timestamp_utc": started.isoformat(),
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256_before": None,
        "snapshot_sha256_after": None,
        "original_experiment_state_modified": False,
        "generation_strategy_advanced": False,
        "new_trials_generated": False,
        "ax_version": None,
        "botorch_version": None,
        "observations_used": 0,
        "objective_metric": None,
        "constraint_metrics": [],
        "model_class": None,
        "generation_node": None,
        "fit_status": "not_attempted",
        "fit_status_reason": "",
        "fit_exception": None,
        "predictive_metrics": [],
    }
    try:
        import ax

        record["ax_version"] = str(ax.__version__)
        import botorch

        record["botorch_version"] = str(botorch.__version__)
    except Exception:  # pragma: no cover - version reporting is best effort
        pass

    if not snapshot_path.is_file():
        record["fit_status"] = "unavailable"
        record["fit_status_reason"] = (
            f"no Ax snapshot exists at {snapshot_path}, so there is nothing to "
            "reconstruct a model from"
        )
        return ReconstructedModel(None, None, None, record)

    record["snapshot_sha256_before"] = _sha256(snapshot_path)
    client = Client.load_from_json_file(str(snapshot_path))
    experiment = client._experiment
    strategy = client._generation_strategy
    search_space = experiment.search_space
    optimization_config = experiment.optimization_config

    record["experiment_name"] = str(getattr(experiment, "name", "") or "")
    record["trials_in_snapshot"] = len(experiment.trials)
    record["search_space_parameters"] = sorted(str(n) for n in search_space.parameters)
    record["search_space_is_hierarchical"] = any(
        getattr(parameter, "is_hierarchical", False)
        for parameter in search_space.parameters.values()
    )
    if optimization_config is not None:
        objective = optimization_config.objective
        record["objective_metric"] = sorted(
            str(name) for name in (getattr(objective, "metric_names", None) or [])
        ) or str(objective)
        record["objective_expression"] = str(getattr(objective, "expression", objective))
        # Ax 1.3.1 exposes an expression-level constraint: `metric_names` is a
        # list, and there is no single `.metric`.
        record["constraint_metrics"] = sorted(
            {
                str(name)
                for constraint in (optimization_config.outcome_constraints or [])
                for name in (getattr(constraint, "metric_names", None) or [])
            }
        )
        record["constraint_expressions"] = [
            str(constraint) for constraint in (optimization_config.outcome_constraints or [])
        ]

    data, data_report = _completed_data(experiment)
    record.update({f"data_{key}": value for key, value in data_report.items()})
    # "Observations" means trials. The metric-row count is reported separately
    # as `observation_rows_used` so nothing can quote 64 rows as 64 designs.
    record["observations_used"] = int(data_report.get("trials_used", 0))
    record["observation_rows_used"] = int(
        data_report.get("rows_used", data_report.get("rows_in_snapshot", 0))
    )
    node_before = strategy.current_node_name

    adapter: Any = None
    try:
        adapter, node = _fit_without_transition(strategy, experiment, data)
        record["generation_node"] = node
        if adapter is None:
            raise ReconstructionError(
                f"the study's current generation node ({node}) is not model-based, "
                "so it has no surrogate to refit"
            )
        record["fit_status"] = "refitted_current_generation_node"
        record["fit_status_reason"] = (
            f"refitted the study's own {node} node from its completed observations; "
            "the generation strategy was not advanced and no trial was generated"
        )
    except Exception as exc:
        record["fit_exception"] = f"{type(exc).__name__}: {exc}"
        try:
            adapter = _fit_fresh_botorch(experiment, data)
            record["fit_status"] = "fitted_fresh_botorch_adapter"
            record["fit_status_reason"] = (
                "the study's own node could not be refitted, so a fresh modular "
                "BoTorch adapter was fitted to the same experiment, search space "
                "and observations. This is a faithful surrogate of the data but "
                "not necessarily the exact model Ax generated with."
            )
        except Exception as fallback_exc:
            record["fit_status"] = "failed"
            record["fit_status_reason"] = (
                "Predictive adapter could not be reconstructed from the completed "
                f"observations: {type(fallback_exc).__name__}: {fallback_exc}"
            )
            record["fit_exception_fallback"] = f"{type(fallback_exc).__name__}: {fallback_exc}"
            adapter = None

    record["model_class"] = type(adapter).__name__ if adapter is not None else None
    record["generation_strategy_advanced"] = bool(
        strategy.current_node_name != node_before
    )
    record["generation_node_before"] = node_before
    record["generation_node_after"] = strategy.current_node_name
    record["new_trials_generated"] = len(experiment.trials) != record["trials_in_snapshot"]

    model = ReconstructedModel(adapter, search_space, optimization_config, record)

    if adapter is not None:
        probe = dict(probe_point) if probe_point else _default_probe(search_space)
        if probe is not None:
            rows = model.predict([probe])
            row = rows[0] if rows else {}
            record["probe_point"] = probe
            record["probe_prediction_available"] = bool(row.get("prediction_available"))
            record["predictive_metrics"] = sorted(
                key[: -len("_predicted_mean")]
                for key in row
                if str(key).endswith("_predicted_mean")
            )
            if not row.get("prediction_available"):
                record["probe_reason"] = str(row.get("reason", ""))

    record["snapshot_sha256_after"] = _sha256(snapshot_path)
    record["original_experiment_state_modified"] = (
        record["snapshot_sha256_after"] != record["snapshot_sha256_before"]
    )
    record["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return model


def _default_probe(search_space: Any) -> dict[str, Any] | None:
    """A cheap in-space point used only to confirm the model can predict.

    Built from the search space itself so it stays valid for a hierarchical
    space: the root choice takes its first value and only that branch's
    children are supplied.
    """

    try:
        from ax.core.parameter import ChoiceParameter, RangeParameter

        point: dict[str, Any] = {}
        dependents: dict[str, list[str]] = {}
        for name, parameter in search_space.parameters.items():
            if getattr(parameter, "is_hierarchical", False):
                dependents = dict(getattr(parameter, "dependents", {}) or {})
        active: set[str] = set()
        for name, parameter in search_space.parameters.items():
            if getattr(parameter, "is_hierarchical", False):
                chosen = list(parameter.values)[0]
                point[str(name)] = chosen
                active.update(str(child) for child in dependents.get(chosen, []))
        for name, parameter in search_space.parameters.items():
            name = str(name)
            if name in point:
                continue
            # A child of the hierarchical root belongs in the point only when
            # the chosen branch activates it.
            if dependents and any(name in children for children in dependents.values()):
                if name not in active:
                    continue
            if isinstance(parameter, RangeParameter):
                point[name] = float(parameter.lower) + 0.5 * (
                    float(parameter.upper) - float(parameter.lower)
                )
            elif isinstance(parameter, ChoiceParameter):
                point[name] = list(parameter.values)[0]
        return point or None
    except Exception:  # pragma: no cover - probing is best effort
        return None


def write_reconstruction_report(directory: Path, model: ReconstructedModel) -> Path:
    """Write ``analysis_model_reconstruction.json`` beside the run's other JSON.

    Deliberately *not* written into the experiment state directory: that
    directory is the protected record of the licensed run, and an analysis
    artifact does not belong in it.
    """

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / RECONSTRUCTION_FILENAME
    path.write_text(
        json.dumps(model.record, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return path
