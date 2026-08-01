"""Demo 13 — Ax Bayesian optimization of graded asymmetric coupled quantum wells.

This is the orchestrator.  It owns the run modes, the closed loop, the
provenance, and nothing else: the design space lives in :mod:`design13`, the Ax
layer in :mod:`axsearch13`, the metric extraction in :mod:`metrics13`, the state
tracking in :mod:`tracking13`, the tables in :mod:`tables13`, the figures in
:mod:`plots13`, and the prose in :mod:`report13`.

The physics is not reimplemented anywhere in Demo 13.  A trial is rendered by
``demo12.render_values`` and analysed by ``demo11.analyse_case`` -- the same two
functions Demo 12 uses -- so a Demo 13 trial and a Demo 12 grid case with the
same geometry are the same calculation, and the warm-start observations are
comparable by construction rather than by hope.
"""

from __future__ import annotations

import copy
import csv
import dataclasses
import datetime as dt
import importlib.util
import json
import math
import platform
from pathlib import Path
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO11_DIR = DEMO_DIR.parent / "11_paper_validation_interband_chi2_acqw"
DEMO12_DIR = DEMO_DIR.parent / "12_graded_interface_coupled_quantum_well_optimization"
for _path in (str(SHARED), str(DEMO11_DIR), str(DEMO12_DIR), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import chi2 as chi2mod  # noqa: E402
import outputs  # noqa: E402
import plots as plotting  # noqa: E402
import quantum1d  # noqa: E402
import sweeps  # noqa: E402
from demo_workflow import (  # noqa: E402
    DemoError,
    git_state,
    machine_summary,
    run_subdirectory,
    write_json_atomically,
    write_text_atomically,
)

import axsearch13  # noqa: E402
import design13  # noqa: E402
import feasibility13  # noqa: E402
import metrics13  # noqa: E402
import plots13  # noqa: E402
import replay13  # noqa: E402
import report13  # noqa: E402
import synthetic13  # noqa: E402
import tables13  # noqa: E402
import tracking13  # noqa: E402


def _load_demo(name: str, path: Path):
    """Load a sibling demo module without duplicating its implementation."""

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DemoError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


demo12 = _load_demo("demo12_for_demo13", DEMO12_DIR / "demo12.py")
demo11 = demo12.demo11

#: Extraction contract version. Bumped when the meaning of a recorded metric
#: changes, so old and new trial records can never be silently mixed.
EXTRACTION_VERSION = "demo13-metrics-1"

RUN_MODES: frozenset[str] = frozenset(
    {
        "synthetic_smoke_test",
        "demo12_replay",
        "prepare_candidates",
        "run_pending_candidates",
        "closed_loop",
        "analyze_existing_results",
        "validate_top_designs",
    }
)


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def _require_mapping(cfg: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = cfg.get(name)
    if not isinstance(value, Mapping):
        raise DemoError(f"demo.yaml: {name} must be a mapping")
    return value


def validate_demo13_config(cfg: Mapping[str, Any]) -> None:
    """Check the relationships the scalar schema cannot express."""

    workflow = _require_mapping(cfg, "workflow")
    mode = str(workflow.get("mode", "closed_loop"))
    if mode not in RUN_MODES:
        raise DemoError(
            f"workflow.mode must be one of {sorted(RUN_MODES)}, got {mode!r}"
        )
    bo = _require_mapping(cfg, "bo")
    if str(bo.get("library", "ax")) != "ax":
        raise DemoError("bo.library must be 'ax'; Demo 13 optimizes through the Ax platform")
    for name in ("num_initial_trials", "num_iterations", "batch_size"):
        value = bo.get(name)
        if not isinstance(value, int) or isinstance(value, bool):
            raise DemoError(f"bo.{name} must be an integer, got {value!r}")
    if int(bo["num_initial_trials"]) < 1:
        raise DemoError("bo.num_initial_trials must be at least 1")
    if int(bo["num_iterations"]) < 0:
        raise DemoError("bo.num_iterations cannot be negative")
    if int(bo["batch_size"]) < 1:
        raise DemoError("bo.batch_size must be at least 1")
    # Ax needs a model before it can propose anything, and a model needs data.
    if int(bo["num_initial_trials"]) < 2 and int(bo["num_iterations"]) > 0:
        raise DemoError(
            "bo.num_initial_trials must be at least 2 before any BO iteration can "
            "fit a surrogate"
        )
    axsearch13.build_optimization_spec(cfg)
    design13.search_space_specs(cfg)
    encoding = str(bo["search_space"].get("encoding", "hierarchical"))
    if encoding == "hierarchical":
        design13.graded_thickness_bounds(cfg)
        design13.graded_profiles(cfg)
    tracking = _require_mapping(cfg, "state_tracking")
    for name, value in (tracking.get("parameter_scales") or {}).items():
        if float(value) <= 0:
            raise DemoError(f"state_tracking.parameter_scales.{name} must be positive")
    if not 0.0 <= float(tracking.get("minimum_confidence", 0.6)) <= 1.0:
        raise DemoError("state_tracking.minimum_confidence must lie in [0, 1]")


def experiment_state_dir(cfg: Mapping[str, Any], results_root: Path) -> Path:
    workflow = cfg.get("workflow") or {}
    name = str(workflow.get("experiment_state_dir", "demo13_ax_experiment"))
    return Path(results_root) / str(cfg["demo_id"]) / name


# ---------------------------------------------------------------------------
# one trial
# ---------------------------------------------------------------------------


def _trial_case(
    trial_index: int, parameters: Mapping[str, Any], cfg: Mapping[str, Any], iteration: int
) -> sweeps.CaseSpec:
    canonical = design13.canonicalize(parameters, cfg)
    resolved = design13.resolve_config(parameters, cfg)
    return sweeps.CaseSpec(
        case_id=f"t{int(trial_index):04d}",
        label=(
            f"s={canonical['asymmetry_s']:.4g}, "
            f"b={canonical['central_barrier_thickness_nm']:.4g} nm, "
            f"g={canonical['grading_thickness_nm']:.4g} nm, "
            f"{canonical['grading_profile']}"
        ),
        swept=dict(canonical),
        config=resolved,
        metadata={
            "trial_index": int(trial_index),
            "iteration": int(iteration),
            "sweep_kind": "ax_trial",
        },
    )


def archive_unexecuted_run_dir(run_dir: Path) -> str | None:
    """Move a never-executed trial directory aside so the trial can be rerun.

    A pending trial already has a directory: the run that proposed it wrote the
    generated deck there and then skipped execution, because that machine had no
    licensed solver.  Executing it later has to write into the same place, and
    the shared layout builder refuses to reuse *any* run directory -- which is
    the right default, since it is what stops a rerun silently clobbering real
    results.

    So the stale attempt is renamed aside rather than deleted.  It contains no
    physics, only an input and a manifest saying the solver was skipped, but
    keeping it costs nothing and leaves the audit trail intact.  A directory
    holding a *completed* run is never touched; reaching that state would mean
    the ledger and the filesystem disagree about what has already been paid for,
    and that is worth stopping on.
    """

    run_dir = Path(run_dir)
    if not run_dir.exists():
        return None
    manifest = run_dir / "run_manifest.json"
    status: str | None = None
    if manifest.is_file():
        try:
            status = json.loads(manifest.read_text(encoding="utf-8")).get(
                "completion_status"
            )
        except (json.JSONDecodeError, OSError):
            status = None
    if status == "completed":
        raise DemoError(
            f"{run_dir} already holds a completed nextnano++ run, but this trial "
            "is not recorded as terminal in the ledger. Refusing to overwrite a "
            "licensed result; reconcile the ledger and the run directory by hand."
        )
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived = run_dir.with_name(f"{run_dir.name}.superseded-{stamp}")
    run_dir.rename(archived)
    return str(archived)


def run_trial(
    *,
    context: sweeps.RunContext,
    trial_index: int,
    parameters: Mapping[str, Any],
    iteration: int,
    state_dir: Path,
) -> tuple[sweeps.CaseResult, sweeps.CaseSpec]:
    """Render, run and analyse one candidate with the Demo 11/12 machinery."""

    cfg = context.cfg
    case = _trial_case(trial_index, parameters, cfg, iteration)
    run_dir = state_dir / "runs" / case.case_id
    archived = archive_unexecuted_run_dir(run_dir)
    result = sweeps.execute_case(
        demo_dir=context.demo_dir,
        spec=case,
        machine=context.machine,
        run_dir=run_dir,
        render_values=demo12.render_values,
        analyse=demo11.analyse_case,
        dependency_report=context.dependency_report,
    )
    # Demo 12's requested-profile artifact is what the realized alloy output is
    # validated against; writing it here keeps a Demo 13 trial directory
    # inspectable with exactly the Demo 12 procedure.
    try:
        demo12._write_requested_profile(case, result.run_dir)
    except Exception as exc:  # pragma: no cover - defensive
        result.warnings.append(f"requested composition profile not written: {exc}")
    if result.solver_success:
        try:
            realized = demo12._extract_realized_composition(case, result)
        except Exception as exc:
            result.status = "failed"
            result.failure_reason = f"grading profile validation failed: {exc}"
            result.validation["grading_profile_realized"] = False
            result.validation["passed"] = False
        else:
            if realized.get("profile_validation_passed") is False:
                result.validation["grading_profile_realized"] = False
                result.validation["passed"] = False
    return result, case


def _tracking_for(
    result: sweeps.CaseResult,
    trial_index: int,
    parameters: Mapping[str, Any],
    cfg: Mapping[str, Any],
    history: list[tracking13.TrialStates],
) -> tuple[dict[str, Any], tracking13.TrialStates | None]:
    if not result.solver_success:
        return {}, None
    states = tracking13.load_trial_states(
        trial_index, design13.canonicalize(parameters, cfg), result.run_dir / "extracted"
    )
    if states is None:
        return (
            {
                "state_tracking_confidence": None,
                "method": "unavailable: no envelopes.csv for this trial",
            },
            None,
        )
    reference = tracking13.choose_reference(states.parameters, history, cfg)
    record = tracking13.track_against(states, reference, cfg)
    return record, states


def _provenance(
    *,
    cfg: Mapping[str, Any],
    context: sweeps.RunContext,
    ax_versions: Mapping[str, Any],
    case: sweeps.CaseSpec,
    result: sweeps.CaseResult,
    generation: Mapping[str, Any],
) -> dict[str, Any]:
    """Section 18: everything needed to reconstruct one trial later."""

    commit, dirty = git_state()
    generated = result.run_dir / "generated_input" / "case.in"
    return {
        "extraction_version": EXTRACTION_VERSION,
        "git_commit": commit,
        "git_dirty": dirty,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "ax_version": ax_versions.get("ax_version_installed"),
        "ax_api": ax_versions.get("ax_api"),
        "solver_executable": machine_summary(context.machine).get("executable"),
        "solver_run_enabled": context.machine.run_solver,
        "random_seed": cfg["bo"].get("random_seed"),
        "input_file_path": str(generated) if generated.is_file() else None,
        "output_directory_path": str(result.run_dir),
        "resolved_config_path": str(result.run_dir / "demo_resolved.yaml"),
        "case_id": case.case_id,
        "case_label": case.label,
        "completion_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        **{f"generation_{key}": value for key, value in dict(generation).items()},
    }


def _geometry_fields(case: sweeps.CaseSpec) -> dict[str, Any]:
    scientific = case.config["scientific"]
    return {
        "resolved_wide_well_nm": float(scientific["thick_well_nm"]),
        "resolved_narrow_well_nm": float(scientific["thin_well_nm"]),
        "resolved_central_barrier_nm": float(scientific["tunnel_barrier_nm"]),
        "grading_implementation": case.config["grading"].get("implementation"),
    }


# ---------------------------------------------------------------------------
# the closed loop
# ---------------------------------------------------------------------------


class Experiment:
    """The Ax client, its snapshot, and the ledger beside it."""

    def __init__(
        self,
        cfg: Mapping[str, Any],
        state_dir: Path,
        *,
        warm_start: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        self.cfg = cfg
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = axsearch13.Ledger(self.state_dir)
        self.spec = axsearch13.build_optimization_spec(cfg)
        self.versions = axsearch13.check_ax_version(cfg)
        self.snapshot_path = self.state_dir / "ax_experiment_snapshot.json"
        self.warm_start_path = self.state_dir / "warm_start_attachments.json"
        self.resumed = False
        self.warm_start_attachments: list[dict[str, Any]] = []
        resume = bool((cfg.get("workflow") or {}).get("resume", True))
        if resume and self.snapshot_path.is_file():
            self.client = axsearch13.load_client(self.snapshot_path)
            self.resumed = True
            if self.warm_start_path.is_file():
                self.warm_start_attachments = json.loads(
                    self.warm_start_path.read_text(encoding="utf-8")
                )
        else:
            self.client = axsearch13.create_client(cfg, self.spec)
            # Warm-start observations may only be attached to a *new*
            # experiment. Re-attaching them on resume would duplicate them in
            # the surrogate's training data every time the study restarts.
            if warm_start:
                self.warm_start_attachments = axsearch13.attach_warm_start(
                    self.client, cfg, self.spec, warm_start
                )
                write_json_atomically(self.warm_start_path, self.warm_start_attachments)
            self.checkpoint()
        write_text_atomically(
            self.state_dir / "demo_yaml_snapshot.yaml",
            yaml.safe_dump(dict(cfg), sort_keys=True),
        )

    def checkpoint(self) -> None:
        axsearch13.save_client(self.client, self.snapshot_path)

    @property
    def plan(self) -> dict[str, Any]:
        return axsearch13.plan(self.cfg, self.ledger)

    def next_trial_ordinal(self) -> int:
        return len(self.ledger.records())

    def generate(self, count: int) -> list[axsearch13.Candidate]:
        candidates = axsearch13.generate_candidates(
            self.client,
            self.cfg,
            self.ledger,
            count=count,
            trial_ordinal=self.next_trial_ordinal(),
        )
        self.checkpoint()
        return candidates

    def complete(self, trial_index: int, raw_data: Mapping[str, float]) -> None:
        self.client.complete_trial(int(trial_index), raw_data=dict(raw_data))
        self.checkpoint()

    def fail(self, trial_index: int, reason: str) -> None:
        self.client.mark_trial_failed(int(trial_index), failed_reason=str(reason)[:400])
        self.checkpoint()

    def abandon(self, trial_index: int, reason: str) -> None:
        try:
            self.client.mark_trial_abandoned(int(trial_index))
        except Exception:  # pragma: no cover - Ax version tolerant
            self.client.mark_trial_failed(int(trial_index), failed_reason=reason[:400])
        self.checkpoint()


def _record_trial(
    experiment: Experiment,
    *,
    candidate: axsearch13.Candidate,
    record: Mapping[str, Any],
    status: str,
    reported_to_ax_as: str,
    provenance: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "trial_index": candidate.trial_index,
        "iteration": candidate.iteration,
        "candidate_id": f"t{candidate.trial_index:04d}",
        "parameters": dict(candidate.parameters),
        "canonical_parameters": dict(candidate.canonical),
        "status": status,
        "reported_to_ax_as": reported_to_ax_as,
        **{key: value for key, value in dict(candidate.generation).items()},
        **dict(record),
        **dict(provenance),
        **dict(extra or {}),
    }
    experiment.ledger.write(payload)
    return payload


def closed_loop(
    context: sweeps.RunContext,
    experiment: Experiment,
    *,
    generate: bool = True,
    run_solver_trials: bool = True,
) -> dict[str, Any]:
    """Run pending trials, then iterate until the configured budget is met."""

    cfg = context.cfg
    counts = design13.expected_evaluation_counts(cfg)
    batch = counts["batch_size"]
    history: list[tracking13.TrialStates] = []
    events: list[dict[str, Any]] = []
    stop_reason = ""

    def execute(candidate: axsearch13.Candidate) -> dict[str, Any] | None:
        started = time.monotonic()
        try:
            result, case = run_trial(
                context=context,
                trial_index=candidate.trial_index,
                parameters=candidate.parameters,
                iteration=candidate.iteration,
                state_dir=experiment.state_dir,
            )
        except DemoError as exc:
            experiment.fail(candidate.trial_index, str(exc))
            record = metrics13.build_record(
                parameters=candidate.parameters,
                cfg=cfg,
                observables={},
                validation={},
                status="failed",
                failure_reason=str(exc),
            )
            return _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="failed",
                reported_to_ax_as="failed",
                provenance={"extraction_version": EXTRACTION_VERSION},
            )
        runtime = time.monotonic() - started
        tracking_record, states = _tracking_for(
            result, candidate.trial_index, candidate.parameters, cfg, history
        )
        if states is not None:
            history.append(states)
        record = metrics13.build_record(
            parameters=candidate.parameters,
            cfg=cfg,
            observables=result.observables,
            validation=result.validation,
            status=result.status,
            failure_reason=result.failure_reason,
            extracted_dir=result.run_dir / "extracted",
            tracking=tracking_record,
            runtime_seconds=runtime,
        )
        record = {**record, **_geometry_fields(case)}
        provenance = _provenance(
            cfg=cfg,
            context=context,
            ax_versions=experiment.versions,
            case=case,
            result=result,
            generation=candidate.generation,
        )
        if result.status == "failed":
            experiment.fail(candidate.trial_index, result.failure_reason or "solver failure")
            return _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="failed",
                reported_to_ax_as="failed",
                provenance=provenance,
            )
        if result.status != "completed":
            # No licensed solver on this machine. The input exists and the trial
            # stays pending in Ax; it is neither completed nor failed, because
            # neither would be true.
            return _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="pending_no_solver",
                reported_to_ax_as="left running",
                provenance=provenance,
            )
        raw = metrics13.ax_raw_data(record, experiment.spec.reported_metrics)
        if raw is None:
            reason = (
                "completed but produced no defensible objective: "
                + (record.get("rejection_reason") or "missing metric")
            )
            experiment.fail(candidate.trial_index, reason)
            return _record_trial(
                experiment,
                candidate=candidate,
                record={**record, "failure_reason": reason},
                status="failed",
                reported_to_ax_as="failed",
                provenance=provenance,
            )
        experiment.complete(candidate.trial_index, raw)
        return _record_trial(
            experiment,
            candidate=candidate,
            record=record,
            status="completed",
            reported_to_ax_as="completed",
            provenance=provenance,
            extra={"ax_raw_data": raw},
        )

    # 1. Unfinished trials from an earlier run come first.
    for pending in experiment.ledger.records():
        if str(pending.get("status")) in axsearch13.TERMINAL_STATUSES:
            continue
        if not run_solver_trials or not context.machine.run_solver:
            continue
        candidate = axsearch13.Candidate(
            trial_index=int(pending["trial_index"]),
            parameters=dict(pending["parameters"]),
            canonical=dict(pending.get("canonical_parameters") or {}),
            iteration=int(pending.get("iteration", 0)),
            generation=axsearch13.generation_metadata(
                experiment.client, int(pending["trial_index"])
            ),
        )
        payload = execute(candidate)
        if payload is not None:
            experiment.ledger.write(payload, allow_update=True)
            events.append({"stage": "resumed_pending", "trial_index": candidate.trial_index})

    if not generate:
        return {"events": events, "stop_reason": "generation disabled for this mode"}

    # 2. Then generate and evaluate until the configured budget is spent.
    while True:
        plan = experiment.plan
        if plan["pending_trials"] > 0:
            # Candidates whose inputs exist but which have never been executed.
            # Generating more would pile up unrunnable work every time the demo
            # is run on a machine without a licence, and would ask Ax for a
            # proposal it has no new data to inform.
            stop_reason = (
                f"{plan['pending_trials']} candidate(s) already await execution "
                f"({plan['pending_trial_indices']}); run them before generating more"
            )
            break
        if plan["remaining_initial_trials"] > 0:
            wanted = min(batch, plan["remaining_initial_trials"])
        elif plan["remaining_bo_iterations"] > 0:
            wanted = batch
        else:
            stop_reason = "configured initial trials and BO iterations are complete"
            break
        try:
            candidates = experiment.generate(wanted)
        except DemoError as exc:
            stop_reason = str(exc)
            break
        if not candidates:
            stop_reason = "Ax generated no further candidates"
            break
        for candidate in candidates:
            if candidate.duplicate_of is not None:
                experiment.abandon(
                    candidate.trial_index,
                    f"canonical duplicate of trial {candidate.duplicate_of}",
                )
                _record_trial(
                    experiment,
                    candidate=candidate,
                    record=metrics13.build_record(
                        parameters=candidate.parameters,
                        cfg=cfg,
                        observables={},
                        validation={},
                        status="rejected",
                        failure_reason=(
                            f"canonical duplicate of trial {candidate.duplicate_of}; "
                            "not simulated"
                        ),
                    ),
                    status="rejected",
                    reported_to_ax_as="abandoned",
                    provenance={"extraction_version": EXTRACTION_VERSION},
                )
                events.append(
                    {"stage": "duplicate_rejected", "trial_index": candidate.trial_index}
                )
                continue
            payload = execute(candidate)
            events.append(
                {
                    "stage": "evaluated",
                    "trial_index": candidate.trial_index,
                    "iteration": candidate.iteration,
                    "status": None if payload is None else payload.get("status"),
                }
            )
            if payload is not None and payload.get("status") == "pending_no_solver":
                stop_reason = (
                    "no licensed nextnano++ solver on this machine; the candidate "
                    "input was generated and the trial is left pending"
                )
                return {"events": events, "stop_reason": stop_reason}
    return {"events": events, "stop_reason": stop_reason}


# ---------------------------------------------------------------------------
# synthetic and replay modes
# ---------------------------------------------------------------------------


def synthetic_loop(cfg: Mapping[str, Any], state_dir: Path) -> dict[str, Any]:
    """Stage 1: the same loop, with the synthetic surface standing in for nextnano."""

    experiment = Experiment(cfg, state_dir)
    counts = design13.expected_evaluation_counts(cfg)
    batch = counts["batch_size"]
    events: list[dict[str, Any]] = []
    while True:
        plan = experiment.plan
        if plan["remaining_initial_trials"] > 0:
            wanted = min(batch, plan["remaining_initial_trials"])
        elif plan["remaining_bo_iterations"] > 0:
            wanted = batch
        else:
            break
        try:
            candidates = experiment.generate(wanted)
        except DemoError:
            break
        if not candidates:
            break
        for candidate in candidates:
            if candidate.duplicate_of is not None:
                experiment.abandon(candidate.trial_index, "canonical duplicate")
                _record_trial(
                    experiment,
                    candidate=candidate,
                    record={
                        "trial_valid": False,
                        "rejection_reason": f"canonical duplicate of trial {candidate.duplicate_of}",
                        "synthetic": True,
                        "data_label": synthetic13.SYNTHETIC_LABEL,
                    },
                    status="rejected",
                    reported_to_ax_as="abandoned",
                    provenance={"extraction_version": EXTRACTION_VERSION},
                )
                continue
            try:
                record = synthetic13.evaluate(candidate.parameters, cfg)
            except (synthetic13.SyntheticFailure, DemoError) as exc:
                experiment.fail(candidate.trial_index, str(exc))
                _record_trial(
                    experiment,
                    candidate=candidate,
                    record={
                        "failure_reason": str(exc),
                        "trial_valid": False,
                        "trial_outcome_class": metrics13.OUTCOME_MECHANICAL_FAILURE,
                        "objective_available": False,
                        "synthetic": True,
                        "data_label": synthetic13.SYNTHETIC_LABEL,
                    },
                    status="failed",
                    reported_to_ax_as="failed",
                    provenance={"extraction_version": EXTRACTION_VERSION},
                )
                events.append({"stage": "synthetic_failed", "trial_index": candidate.trial_index})
                continue
            raw = metrics13.ax_raw_data(record, experiment.spec.reported_metrics)
            if raw is None:
                experiment.fail(candidate.trial_index, "synthetic record has no objective")
                continue
            experiment.complete(candidate.trial_index, raw)
            _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="completed",
                reported_to_ax_as="completed",
                provenance={"extraction_version": EXTRACTION_VERSION},
                extra={"ax_raw_data": raw},
            )
            events.append({"stage": "synthetic_completed", "trial_index": candidate.trial_index})
    records = experiment.ledger.records()
    best = _best_valid(records, experiment.spec)
    recovery = (
        synthetic13.recovery_error(
            {
                key[len("parameter_"):]: value
                for key, value in best.items()
                if str(key).startswith("parameter_")
            },
            cfg,
        )
        if best
        else {}
    )
    return {
        "experiment": experiment,
        "records": records,
        "events": events,
        "best": best,
        "recovery": recovery,
        "known_optimum": dict(synthetic13.SYNTHETIC_OPTIMUM),
    }


def _best_valid(records: Sequence[Mapping[str, Any]], spec: Any) -> dict[str, Any]:
    metric = tables13.objective_metric_name(spec)
    minimize = metric in set(spec.minimized_metrics)
    usable = [
        record
        for record in records
        if str(record.get("status")) == "completed"
        and record.get("trial_valid")
        and record.get(metric) is not None
    ]
    if not usable:
        return {}
    return dict(
        (min if minimize else max)(usable, key=lambda record: float(record[metric]))
    )


def replay_study(cfg: Mapping[str, Any], results_root: Path | None) -> dict[str, Any]:
    """Stage 2: Ax against random and grid search over completed Demo 12 data."""

    run_dir = replay13.find_demo12_run(cfg, results_root)
    cases = replay13.load_demo12_cases(run_dir) if run_dir else []
    ingested = replay13.ingest(cases, cfg)
    pool = replay13.pool_from_ingest(ingested, cfg)
    source = "demo12"
    if not pool:
        pool = replay13.synthetic_pool(cfg)
        source = "synthetic_stand_in"
    counts = design13.expected_evaluation_counts(cfg)
    comparison = replay13.efficiency_comparison(
        pool,
        cfg,
        evaluations=min(len(pool), counts["expected_maximum_new_solver_runs"]),
        seed=int(cfg["bo"].get("random_seed", 0)),
    )
    return {
        "demo12_run_dir": str(run_dir) if run_dir else None,
        "pool_source": source,
        "pool_size": len(pool),
        "ingested": ingested,
        "comparison": comparison,
    }


# ---------------------------------------------------------------------------
# surrogate slices, partial dependence, acquisition surface
# ---------------------------------------------------------------------------


def _slice_points(
    cfg: Mapping[str, Any], x_name: str, y_name: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """A 2-D grid of canonical designs and their Ax-encoded counterparts."""

    slices = (cfg["bo"].get("surrogate_slices") or {})
    count = int(slices.get("grid_points", 21))
    fixed = dict(slices.get("fixed_values") or {})
    bounds = {}
    for spec in design13.search_space_specs(cfg):
        if isinstance(spec, design13.RangeSpec):
            bounds[spec.name] = (spec.lower, spec.upper)
    canonical_points: list[dict[str, Any]] = []
    for x in np.linspace(*bounds[x_name], count):
        for y in np.linspace(*bounds[y_name], count):
            point = {
                "asymmetry_s": float(fixed.get("asymmetry_s", 0.46)),
                "central_barrier_thickness_nm": float(
                    fixed.get("central_barrier_thickness_nm", 1.8)
                ),
                "grading_thickness_nm": float(fixed.get("grading_thickness_nm", 1.5)),
                "grading_profile": str(fixed.get("grading_profile", "linear")),
            }
            point[x_name] = float(x)
            point[y_name] = float(y)
            canonical_points.append(point)
    encoded = [axsearch13.ax_parameters(point, cfg) for point in canonical_points]
    return canonical_points, encoded


def _expected_improvement(mean: float, sem: float, best: float) -> float:
    """Analytic expected improvement, for the acquisition-surface figure."""

    if sem is None or not math.isfinite(sem) or sem <= 0:
        return max(0.0, float(mean) - float(best))
    z = (float(mean) - float(best)) / float(sem)
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    pdf = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    return float((float(mean) - float(best)) * cdf + float(sem) * pdf)


def surrogate_artifacts(
    experiment: Experiment, records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Surrogate slices, partial dependence, acquisition surface and importance."""

    cfg = experiment.cfg
    metric = tables13.objective_metric_name(experiment.spec)
    best_record = _best_valid(records, experiment.spec)
    best_value = float(best_record.get(metric, 0.0) or 0.0)
    fixed = dict((cfg["bo"].get("surrogate_slices") or {}).get("fixed_values") or {})
    slices: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for name, (x_name, y_name) in (
        ("asymmetry_grading", ("asymmetry_s", "grading_thickness_nm")),
        ("barrier_grading", ("central_barrier_thickness_nm", "grading_thickness_nm")),
    ):
        canonical_points, encoded = _slice_points(cfg, x_name, y_name)
        predictions = axsearch13.surrogate_predictions(experiment.client, encoded)
        slice_rows: list[dict[str, Any]] = []
        for point, prediction in zip(canonical_points, predictions):
            row = {
                "slice": name,
                **{key: value for key, value in point.items()},
                **{
                    f"fixed_{key}": value
                    for key, value in fixed.items()
                    if key not in (x_name, y_name)
                },
                "prediction_available": prediction.get("prediction_available", False),
                "reason": prediction.get("reason", ""),
            }
            for key, value in prediction.items():
                if str(key).endswith(("_predicted_mean", "_predicted_standard_error")):
                    row[key] = value
            mean = row.get(f"{metric}_predicted_mean")
            sem = row.get(f"{metric}_predicted_standard_error")
            row["expected_improvement"] = (
                None if mean is None else _expected_improvement(float(mean), sem, best_value)
            )
            row["expected_improvement_method"] = (
                "analytic expected improvement from the Ax posterior mean and standard "
                "error on this slice; not a replay of Ax's Monte-Carlo acquisition"
            )
            slice_rows.append(row)
        slices[name] = slice_rows
        rows.extend(slice_rows)

    partial: dict[str, list[dict[str, Any]]] = {}
    for spec in design13.search_space_specs(cfg):
        if not isinstance(spec, design13.RangeSpec):
            continue
        count = int((cfg["bo"].get("surrogate_slices") or {}).get("grid_points", 21))
        points: list[dict[str, Any]] = []
        for value in np.linspace(spec.lower, spec.upper, count):
            point = {
                "asymmetry_s": float(fixed.get("asymmetry_s", 0.46)),
                "central_barrier_thickness_nm": float(
                    fixed.get("central_barrier_thickness_nm", 1.8)
                ),
                "grading_thickness_nm": float(fixed.get("grading_thickness_nm", 1.5)),
                "grading_profile": str(fixed.get("grading_profile", "linear")),
            }
            point[spec.name] = float(value)
            points.append(point)
        predictions = axsearch13.surrogate_predictions(
            experiment.client, [axsearch13.ax_parameters(point, cfg) for point in points]
        )
        partial[spec.name] = [
            {
                spec.name: point[spec.name],
                "predicted_mean": prediction.get(f"{metric}_predicted_mean"),
                "predicted_standard_error": prediction.get(
                    f"{metric}_predicted_standard_error"
                ),
                "prediction_available": prediction.get("prediction_available", False),
                "reason": prediction.get("reason", ""),
                **{f"fixed_{key}": value for key, value in fixed.items() if key != spec.name},
            }
            for point, prediction in zip(points, predictions)
        ]

    acquisition_rows = [
        {
            "trial_index": record.get("trial_index"),
            "iteration": record.get("iteration"),
            "generation_method": record.get("generation_method"),
            "expected_acquisition_value": record.get("expected_acquisition_value"),
            "status": record.get("status"),
            **{
                key: record.get(key)
                for key in (
                    "parameter_asymmetry_s", "parameter_central_barrier_thickness_nm",
                    "parameter_grading_thickness_nm", "parameter_grading_profile",
                )
            },
            "note": "Sobol proposals have no acquisition value; the field is empty for them",
        }
        for record in records
    ]
    return {
        "slices": slices,
        "slice_rows": rows,
        "partial_dependence": partial,
        "acquisition_rows": acquisition_rows,
        "importance": axsearch13.parameter_importance(experiment.client),
        "ax_frontier": axsearch13.pareto_frontier(experiment.client)
        if experiment.spec.is_multi_objective
        else [],
    }


# ---------------------------------------------------------------------------
# curves for the physics figures
# ---------------------------------------------------------------------------


def _normalized_spectrum(extracted: Path) -> tuple[list[float], list[float]] | None:
    spectrum = metrics13.read_chi2_spectrum(extracted)
    if spectrum is None:
        return None
    wavelength, magnitude = spectrum
    peak = float(np.max(np.abs(magnitude))) if magnitude.size else 0.0
    if peak <= 0:
        return list(map(float, wavelength)), [0.0] * len(wavelength)
    return list(map(float, wavelength)), list(map(float, np.abs(magnitude) / peak))


def _read_two_column_csv(path: Path) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    if not path.is_file():
        return xs, ys
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                xs.append(float(row[0]))
                ys.append(float(row[1]))
            except ValueError:
                continue
    return xs, ys


def physics_curves(
    cfg: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    state_dir: Path,
    *,
    top: int = 3,
) -> dict[str, Any]:
    """Spectra, composition, band edges and envelopes for the best designs."""

    spectra: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    band_edges: list[dict[str, Any]] = []
    envelopes: list[dict[str, Any]] = []

    ranked = sorted(
        (
            record
            for record in records
            if str(record.get("status")) == "completed"
            and record.get("trial_valid")
            and record.get("relative_chi2_at_target_wavelength_abs") is not None
        ),
        key=lambda record: -float(record["relative_chi2_at_target_wavelength_abs"]),
    )
    selected: list[tuple[str, str, Mapping[str, Any]]] = []
    reference = next(
        (record for record in records if record.get("design_role") == "reference"), None
    )
    if reference is not None:
        selected.append(("reference (abrupt)", "baseline", reference))
    for position, record in enumerate(ranked[:top]):
        role = "best" if position == 0 else "top"
        selected.append((f"trial {record.get('trial_index')}", role, record))

    for label, role, record in selected:
        directory = record.get("output_directory_path")
        if not directory:
            continue
        extracted = Path(str(directory)) / "extracted"
        spectrum = _normalized_spectrum(extracted)
        if spectrum is not None:
            spectra.append({"label": label, "role": role, "x": spectrum[0], "y": spectrum[1]})
        xs, ys = _read_two_column_csv(extracted / "requested_composition_profile.csv")
        if xs:
            profiles.append({"label": label, "x": xs, "y": ys})
        envelopes.extend(_envelope_curves(extracted, label))
        band_edges.extend(
            _band_edge_curves(cfg, run_subdirectory(Path(str(directory)), "raw"), label)
        )
    return {
        "spectra": spectra,
        "profiles": profiles,
        "band_edges": band_edges,
        "envelopes": envelopes,
    }


def _envelope_curves(extracted: Path, label: str) -> list[dict[str, Any]]:
    path = extracted / "envelopes.csv"
    if not path.is_file():
        return []
    try:
        header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
        data = np.genfromtxt(path, delimiter=",", skip_header=1)
    except (OSError, IndexError, ValueError):
        return []
    if data.ndim != 2 or data.shape[0] < 2:
        return []
    curves: list[dict[str, Any]] = []
    for index, name in enumerate(header):
        name = name.strip()
        if not name.startswith("psi_"):
            continue
        band = "heavy_hole" if name.startswith("psi_hh") else "electron"
        curves.append(
            {
                "label": f"{label}: {name}",
                "band": band,
                "x": list(map(float, data[:, 0])),
                "y": list(map(float, data[:, index])),
            }
        )
    return curves


def _band_edge_curves(cfg: Mapping[str, Any], raw: Path, label: str) -> list[dict[str, Any]]:
    """Solver band edges, parsed exactly as Demo 11 parses them."""

    if not raw.is_dir():
        return []
    try:
        profile = outputs.load_profile(
            str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
        )
        run = quantum1d.parse_one_band_run(
            raw,
            profile=profile,
            region_name=str(cfg["analysis"].get("quantum_region_name", "acqw")),
            bandedge_columns=cfg["outputs"]["bandedge_columns"],
            want_envelopes=False,
        )
    except Exception:
        return []
    curves: list[dict[str, Any]] = []
    for key, band in (("conduction_eV", "conduction"), ("heavy_hole_eV", "heavy_hole")):
        values = run.band_edges.get(key)
        if values is None:
            continue
        curves.append(
            {
                "label": label,
                "band": band,
                "x": list(map(float, run.position_nm)),
                "y": list(map(float, values)),
            }
        )
    return curves


def paper_curves(cfg: Mapping[str, Any], spectra: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    paper = cfg.get("paper_comparison") or {}
    curves = [
        {"label": curve["label"], "x": curve["x"], "y": curve["y"]}
        for curve in spectra
        if curve.get("role") in {"baseline", "best"}
    ]
    name = paper.get("digitized_simulation_csv")
    if name:
        xs, ys = _read_two_column_csv(DEMO_DIR / str(name))
        if xs:
            peak = max(ys) or 1.0
            curves.append(
                {
                    "label": "paper Fig. 2d (digitized)",
                    "x": xs,
                    "y": [value / peak for value in ys],
                }
            )
    return curves


def measured_curves(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    name = (cfg.get("paper_comparison") or {}).get("measured_intensity_csv")
    if not name:
        return []
    xs, ys = _read_two_column_csv(DEMO_DIR / str(name))
    return [{"label": "measured SH intensity", "x": xs, "y": ys}] if xs else []


# ---------------------------------------------------------------------------
# Stage 5 validation
# ---------------------------------------------------------------------------


def _set(config: dict[str, Any], dotted: str, value: Any) -> None:
    cursor: Any = config
    parts = dotted.split(".")
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def validation_cases(
    cfg: Mapping[str, Any], design: Mapping[str, Any]
) -> list[tuple[str, str, dict[str, Any]]]:
    """Local refinement, mesh, state-count and padding checks for one design."""

    study = cfg.get("validation_study") or {}
    base_parameters = {
        key[len("parameter_"):]: value
        for key, value in design.items()
        if str(key).startswith("parameter_")
    }
    cases: list[tuple[str, str, dict[str, Any]]] = []
    cases.append(("nominal", "nominal", design13.resolve_config(base_parameters, cfg)))
    for name, deltas in (study.get("local_refinement") or {}).items():
        for delta in deltas:
            parameters = dict(base_parameters)
            try:
                parameters[name] = float(parameters[name]) + float(delta)
                resolved = design13.resolve_config(parameters, cfg)
            except (KeyError, DemoError):
                continue
            cases.append((f"local_{name}{float(delta):+g}", "local_refinement", resolved))
    for spacing in study.get("mesh_convergence_nm") or []:
        resolved = design13.resolve_config(base_parameters, cfg)
        _set(resolved, "numerical.active_region_grid_spacing_nm", float(spacing))
        cases.append((f"mesh_{float(spacing):g}nm", "mesh_convergence", resolved))
    for count in study.get("state_count_convergence") or []:
        resolved = design13.resolve_config(base_parameters, cfg)
        _set(resolved, "numerical.number_of_electron_states", int(count))
        _set(resolved, "numerical.number_of_hole_states", int(count))
        cases.append((f"states_{int(count)}", "state_count_convergence", resolved))
    for padding in study.get("domain_padding_nm") or []:
        resolved = design13.resolve_config(base_parameters, cfg)
        _set(resolved, "numerical.domain_padding_nm", float(padding))
        cases.append((f"padding_{float(padding):g}nm", "domain_padding", resolved))
    return cases


def robustness_cases(
    cfg: Mapping[str, Any], design: Mapping[str, Any]
) -> list[tuple[str, str, float, dict[str, Any]]]:
    """Fabrication perturbations around one design."""

    study = (cfg.get("validation_study") or {}).get("fabrication_perturbations") or {}
    base_parameters = {
        key[len("parameter_"):]: value
        for key, value in design.items()
        if str(key).startswith("parameter_")
    }
    paths = {
        "narrow_well_nm": "scientific.thin_well_nm",
        "wide_well_nm": "scientific.thick_well_nm",
        "central_barrier_nm": "scientific.tunnel_barrier_nm",
        "grading_thickness_nm": "grading.selected_thickness_nm",
        "aluminum_fraction": "scientific.aluminum_fraction",
    }
    cases: list[tuple[str, str, float, dict[str, Any]]] = []
    for name, deltas in study.items():
        path = paths.get(str(name))
        if path is None:
            continue
        for delta in deltas:
            resolved = design13.resolve_config(base_parameters, cfg)
            cursor: Any = resolved
            for part in path.split("."):
                cursor = cursor[part]
            new_value = float(cursor) + float(delta)
            if new_value <= 0:
                continue
            _set(resolved, path, new_value)
            cases.append((f"{name}{float(delta):+g}", str(name), float(delta), resolved))
    return cases


def run_validation_study(
    context: sweeps.RunContext, experiment: Experiment, records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Stage 5: refine, converge and perturb the top designs.

    Without a licensed solver this returns the *planned* cases and says so; it
    never reports a check as passed that was not run.
    """

    cfg = context.cfg
    study = cfg.get("validation_study") or {}
    if not bool(study.get("enabled", False)):
        return {"enabled": False, "validation_rows": [], "robustness_rows": []}
    top = tables13.top_ranked_valid_designs(
        records, experiment.spec, limit=int(study.get("top_designs", 3))
    )
    validation_rows: list[dict[str, Any]] = []
    robustness_rows: list[dict[str, Any]] = []
    state_dir = experiment.state_dir / "validation"
    for design in top:
        source = next(
            (
                record
                for record in records
                if int(record.get("trial_index", -1)) == int(design.get("trial_index", -2))
            ),
            None,
        )
        if source is None:
            continue
        nominal_target = metrics13._finite(source.get("relative_chi2_at_target_wavelength_abs"))
        for case_id, kind, resolved in validation_cases(cfg, source):
            row = _run_side_case(
                context,
                state_dir,
                f"v{int(design['trial_index']):04d}_{case_id}",
                resolved,
                extra={
                    "trial_index": design["trial_index"],
                    "check_kind": kind,
                    "case_id": case_id,
                    "nominal_chi2_at_target_wavelength_abs": nominal_target,
                },
            )
            validation_rows.append(row)
        drifts: list[float] = []
        for case_id, parameter, delta, resolved in robustness_cases(cfg, source):
            row = _run_side_case(
                context,
                state_dir,
                f"r{int(design['trial_index']):04d}_{case_id}",
                resolved,
                extra={
                    "trial_index": design["trial_index"],
                    "perturbed_parameter": parameter,
                    "perturbation": delta,
                    "case_id": case_id,
                    "nominal_chi2_at_target_wavelength_abs": nominal_target,
                },
            )
            value = metrics13._finite(row.get("relative_chi2_at_target_wavelength_abs"))
            if value is not None and nominal_target:
                drift = abs(value - nominal_target) / abs(nominal_target)
                row["relative_drift"] = drift
                drifts.append(drift)
            robustness_rows.append(row)
        if drifts:
            score = 1.0 / (1.0 + float(np.mean(drifts)))
            for record in records:
                if int(record.get("trial_index", -1)) == int(design["trial_index"]):
                    record["robustness_score"] = score
                    record["robustness_worst_case_relative_drift"] = max(drifts)
    return {
        "enabled": True,
        "validation_rows": validation_rows,
        "robustness_rows": robustness_rows,
        "designs_checked": [row.get("trial_index") for row in top],
        "solver_ran": bool(context.machine.run_solver),
    }


def _run_side_case(
    context: sweeps.RunContext,
    state_dir: Path,
    case_id: str,
    resolved: Mapping[str, Any],
    *,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    """One Stage 5 case, run through exactly the same path as a trial."""

    case = sweeps.CaseSpec(
        case_id=case_id,
        label=case_id,
        swept={},
        config=dict(resolved),
        metadata={"sweep_kind": "validation"},
    )
    result = sweeps.execute_case(
        demo_dir=context.demo_dir,
        spec=case,
        machine=context.machine,
        run_dir=state_dir / case_id,
        render_values=demo12.render_values,
        analyse=demo11.analyse_case,
        dependency_report=context.dependency_report,
    )
    record = metrics13.build_record(
        parameters=design13.parameters_from_config(dict(resolved)),
        cfg=context.cfg,
        observables=result.observables,
        validation=result.validation,
        status=result.status,
        failure_reason=result.failure_reason,
        extracted_dir=result.run_dir / "extracted",
        runtime_seconds=result.runtime_seconds,
    )
    return {
        **dict(extra),
        **record,
        "status": result.status,
        "output_directory_path": str(result.run_dir),
        "checked": result.status == "completed",
        "not_checked_reason": ""
        if result.status == "completed"
        else "no licensed nextnano++ solver on this machine; case planned and generated only",
    }


# ---------------------------------------------------------------------------
# prior-demo baselines
# ---------------------------------------------------------------------------


def load_prior_demo_best(
    results_root: Path | None, demo_id: str, cfg: Mapping[str, Any], *, case_id: str | None = None
) -> dict[str, Any] | None:
    """The reference (Demo 11) or best graded (Demo 12) design, if one exists."""

    if results_root is None:
        return None
    demo_root = Path(results_root) / demo_id
    if not demo_root.is_dir():
        return None
    runs = sorted((path for path in demo_root.iterdir() if path.is_dir()), reverse=True)
    for run in runs:
        cases = replay13.load_demo12_cases(run)
        candidates = [case for case in cases if case.status == "completed"]
        if case_id is not None:
            candidates = [case for case in candidates if case.case_id == case_id]
        best: dict[str, Any] | None = None
        for case in candidates:
            metrics = replay13.map_metrics(case.observables, cfg)
            if metrics.get("relative_chi2_at_target_wavelength_abs") is None:
                continue
            parameters = design13.parameters_from_config(case.config)
            row = {
                "source_demo": demo_id,
                "case_or_trial": case.case_id,
                "wide_well_nm": float(case.config["scientific"]["thick_well_nm"]),
                "narrow_well_nm": float(case.config["scientific"]["thin_well_nm"]),
                **{f"parameter_{name}": value for name, value in parameters.items()},
                **metrics,
                "trial_valid": case.validation.get("passed") is not False,
                "note": f"from {run.name}",
            }
            if best is None or float(row["relative_chi2_at_target_wavelength_abs"]) > float(
                best["relative_chi2_at_target_wavelength_abs"]
            ):
                best = row
        if best is not None:
            return best
    return None


# ---------------------------------------------------------------------------
# reporting the whole run
# ---------------------------------------------------------------------------


def write_run_artifacts(
    context: sweeps.RunContext,
    experiment: Experiment,
    *,
    records: Sequence[Mapping[str, Any]],
    plan_record: Mapping[str, Any],
    surrogate: Mapping[str, Any],
    replay: Mapping[str, Any] | None,
    validation: Mapping[str, Any],
    synthetic: bool,
) -> dict[str, Any]:
    """Tables, figures and guides for one run bundle."""

    cfg = context.cfg
    parent = context.parent
    results_root = context.machine.results_root
    demo11_best = load_prior_demo_best(
        results_root, "11_paper_validation_interband_chi2_acqw", cfg, case_id="s1_ref"
    )
    demo12_best = load_prior_demo_best(
        results_root, replay13.DEMO12_ID, cfg
    )
    counts = design13.expected_evaluation_counts(cfg)
    comparison = report13.comparison_rows(
        demo11=demo11_best,
        demo12=demo12_best,
        demo13_records=records,
        evaluations_used={
            "demo11_abrupt_reference": 1 if demo11_best else None,
            "demo12_best_grid_graded": replay.get("pool_size") if replay else None,
            "demo13_best_target_wavelength": plan_record.get("completed_trials"),
            "demo13_best_intrinsic_peak": plan_record.get("completed_trials"),
            "demo13_most_robust": plan_record.get("completed_trials"),
            "demo13_final_validated": plan_record.get("completed_trials"),
        },
    )
    efficiency = (replay or {}).get("comparison") or {}
    tables13.write_all(
        parent,
        cfg=cfg,
        records=records,
        spec=experiment.spec,
        candidates=[
            {
                "trial_index": record.get("trial_index"),
                "iteration": record.get("iteration"),
                "candidate_id": record.get("candidate_id"),
                "generation_method": record.get("generation_method"),
                "generator": record.get("generator"),
                "expected_acquisition_value": record.get("expected_acquisition_value"),
                "lifecycle": _lifecycle(record),
                "duplicate_of_trial": record.get("duplicate_of_trial"),
                "status": record.get("status"),
                "reported_to_ax_as": record.get("reported_to_ax_as"),
                **{
                    key: record.get(key)
                    for key in (
                        "parameter_asymmetry_s",
                        "parameter_central_barrier_thickness_nm",
                        "parameter_grading_thickness_nm",
                        "parameter_grading_profile",
                    )
                },
            }
            for record in records
        ],
        surrogate_rows=surrogate.get("slice_rows", []),
        acquisition_rows=surrogate.get("acquisition_rows", []),
        importance=surrogate.get("importance"),
        ax_frontier=surrogate.get("ax_frontier", []),
        comparison_rows=comparison,
        validation_rows=validation.get("validation_rows", []),
        robustness_rows=validation.get("robustness_rows", []),
        efficiency_rows=efficiency.get("summary", []),
        warm_start_rows=((replay or {}).get("ingested") or {}).get("provenance_rows", []),
        plan_record=plan_record,
        synthetic=synthetic,
    )

    curves = physics_curves(cfg, records, experiment.state_dir)
    context_plots = plots13.PlotContext(
        cfg=cfg,
        records=records,
        objective_metric=tables13.objective_metric_name(experiment.spec),
        objective_direction=(
            "minimize"
            if tables13.objective_metric_name(experiment.spec)
            in set(experiment.spec.minimized_metrics)
            else "maximize"
        ),
        best_by_iteration=tables13.best_so_far_by_iteration(records, experiment.spec),
        surrogate_slices=surrogate.get("slices", {}),
        partial_dependence=surrogate.get("partial_dependence", {}),
        importance_rows=tables13._importance_rows(surrogate.get("importance")),
        efficiency=efficiency,
        spectra=curves["spectra"],
        profiles=curves["profiles"],
        band_edges=curves["band_edges"],
        envelopes=curves["envelopes"],
        paper_curves=paper_curves(cfg, curves["spectra"]),
        measured_curves=measured_curves(cfg),
        robustness_rows=validation.get("robustness_rows", []),
        synthetic=synthetic,
    )
    plots13.write_all(parent / "plots", context_plots)

    best = _best_valid(records, experiment.spec)
    summary = {
        "licensed_results_present": any(
            str(record.get("status")) == "completed" and not record.get("synthetic")
            for record in records
        ),
        "completed_trials": plan_record.get("completed_trials"),
        "valid_trials": sum(1 for record in records if record.get("trial_valid")),
        "failed_trials": plan_record.get("failed_trials"),
        "best_objective": best.get(tables13.objective_metric_name(experiment.spec)),
        "best_trial_index": best.get("trial_index"),
        "ax_objective_string": experiment.spec.objective,
        "stage5_validated": bool(
            validation.get("enabled") and validation.get("solver_ran")
        ),
        "best_design": {
            key: best.get(key)
            for key in (
                "parameter_asymmetry_s",
                "parameter_central_barrier_thickness_nm",
                "parameter_grading_thickness_nm",
                "parameter_grading_profile",
                "relative_peak_chi2_abs",
                "peak_wavelength_nm",
                "relative_chi2_at_target_wavelength_abs",
                "signed_detuning_nm",
                "maximum_boundary_probability",
                "state_tracking_confidence",
            )
        }
        if best
        else {},
        "verdict": report13.verdict(comparison),
    }
    report13.write_guides(parent, cfg, summary)
    return {"summary": summary, "comparison": comparison, "counts": counts}


def _lifecycle(record: Mapping[str, Any]) -> str:
    status = str(record.get("status"))
    if status == "rejected":
        return "proposed, rejected as a canonical duplicate, never simulated"
    if status == "failed":
        return "proposed, executed, failed"
    if status == "completed":
        return "proposed, executed, completed" + (
            "" if record.get("trial_valid") else ", rejected by outcome constraints"
        )
    return "proposed, input generated, execution pending"


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    validate_demo13_config(cfg)
    versions = axsearch13.check_ax_version(cfg)

    simulation = cfg.get("simulation") or {}
    if not bool(simulation.get("run_solver", False)):
        # The YAML gate can only ever disable the solver, never enable one that
        # the machine does not have.
        context = dataclasses.replace(
            context, machine=dataclasses.replace(context.machine, run_solver=False)
        )
    if simulation.get("threads") is not None:
        # Thread count is a scheduling preference, not a capability, so unlike
        # run_solver the demo's YAML may raise it as well as lower it.
        context = dataclasses.replace(
            context,
            machine=dataclasses.replace(
                context.machine, threads=int(simulation["threads"])
            ),
        )

    mode = str((cfg.get("workflow") or {}).get("mode", "closed_loop"))
    state_dir = experiment_state_dir(cfg, context.machine.results_root)
    if mode == "synthetic_smoke_test":
        state_dir = state_dir.parent / f"{state_dir.name}_synthetic"

    synthetic = mode == "synthetic_smoke_test"
    replay: dict[str, Any] | None = None
    loop_result: dict[str, Any] = {"events": [], "stop_reason": "mode did not run trials"}

    # Warm starting is a file read; the Stage 2 replay is a whole study. Only
    # demo12_replay pays for the second.
    warm_start_enabled = bool(
        (cfg["bo"].get("warm_start") or {}).get("use_demo12_warm_start", False)
    ) and not synthetic
    ingested: dict[str, Any] = (
        replay13.ingest_warm_start(cfg, context.machine.results_root)
        if warm_start_enabled
        else {"enabled": False, "provenance_rows": [], "observations": [],
              "candidate_count": 0, "compatible_count": 0, "used_count": 0}
    )

    if synthetic:
        outcome = synthetic_loop(cfg, state_dir)
        experiment = outcome["experiment"]
        write_json_atomically(
            context.parent / "extracted" / "synthetic_optimum_recovery.json",
            {
                "known_optimum": outcome["known_optimum"],
                "recovery": outcome["recovery"],
                "label": synthetic13.SYNTHETIC_LABEL,
            },
        )
        loop_result = {"events": outcome["events"], "stop_reason": "synthetic study complete"}
    else:
        experiment = Experiment(
            cfg, state_dir, warm_start=ingested.get("observations", ())
        )
        for row in ingested.get("provenance_rows", []):
            row["ax_trial_index"] = None
        for row, attachment in zip(
            [row for row in ingested.get("provenance_rows", []) if row.get("used_by_ax")],
            experiment.warm_start_attachments,
        ):
            row["ax_trial_index"] = attachment.get("ax_trial_index")
            row["used_by_ax"] = bool(attachment.get("attached"))
            if not attachment.get("attached"):
                row["not_used_reason"] = str(attachment.get("reason"))
        if mode == "demo12_replay":
            replay = replay_study(cfg, context.machine.results_root)
        elif mode == "prepare_candidates":
            loop_result = closed_loop(context, experiment, generate=True, run_solver_trials=False)
        elif mode == "run_pending_candidates":
            loop_result = closed_loop(context, experiment, generate=False, run_solver_trials=True)
        elif mode == "closed_loop":
            loop_result = closed_loop(context, experiment)
        elif mode in {"analyze_existing_results", "validate_top_designs"}:
            loop_result = {"events": [], "stop_reason": f"{mode} does not generate candidates"}

    records = experiment.ledger.records()
    if replay is None:
        replay = {
            "demo12_run_dir": ingested.get("demo12_run_dir"),
            "pool_source": "not run (warm-start ingestion only)",
            "pool_size": None,
            "ingested": ingested,
            "comparison": {},
        }
    else:
        replay.setdefault("ingested", ingested)

    plan_record = experiment.plan
    print("\n".join(axsearch13.plan_report_lines(plan_record)))
    write_json_atomically(context.parent / "extracted" / "run_plan.json", plan_record)

    # Section 11: say plainly whether anything feasible exists, and warn loudly
    # if a modelled constraint cannot be resolved by the surrogate -- the defect
    # that produced BoTorch's all-infeasible warning on 2026-07-31.
    constraint_specs = feasibility13.build_constraints(cfg)
    feasibility = feasibility13.feasibility_summary(records, constraint_specs)
    spread = feasibility13.constraint_spread(records, constraint_specs)
    unresolvable = feasibility13.unresolvable_modelled_constraints(spread)
    write_json_atomically(
        context.parent / "extracted" / "feasibility_summary.json",
        {**feasibility, "unresolvable_modelled_constraints": unresolvable,
         "constraint_modelling": [dict(row) for row in spread]},
    )
    print(f"  feasible trials             : {feasibility['feasible_count']} "
          f"of {feasibility['completed_trials']} completed")
    if feasibility["initial_design_all_infeasible"]:
        print("  NOTE: the initial design contained no feasible point; "
              "improvement among infeasible designs is not progress.")
    if unresolvable:
        print("  WARNING: modelled constraint(s) the surrogate cannot resolve, "
              "which will make every observation infeasible: "
              + ", ".join(unresolvable))

    validation = (
        run_validation_study(context, experiment, records)
        if mode == "validate_top_designs"
        else {"enabled": False, "validation_rows": [], "robustness_rows": [], "solver_ran": False}
    )
    if validation.get("enabled"):
        records = experiment.ledger.records()

    surrogate = surrogate_artifacts(experiment, records)
    artifacts = write_run_artifacts(
        context,
        experiment,
        records=records,
        plan_record=plan_record,
        surrogate=surrogate,
        replay=replay,
        validation=validation,
        synthetic=synthetic,
    )

    results = [
        sweeps.CaseResult(
            spec=sweeps.CaseSpec(
                case_id=str(record.get("candidate_id", f"t{record.get('trial_index')}")),
                label=str(record.get("candidate_id", "")),
                swept=dict(record.get("canonical_parameters") or {}),
                config={},
                metadata={"iteration": record.get("iteration")},
            ),
            run_dir=Path(str(record.get("output_directory_path") or state_dir)),
            status="completed" if str(record.get("status")) == "completed" else "failed"
            if str(record.get("status")) == "failed"
            else "skipped_no_solver",
            runtime_seconds=float(record.get("runtime_seconds") or 0.0),
            observables={
                key: value
                for key, value in record.items()
                if isinstance(value, (int, float, str, bool)) or value is None
            },
            validation={"passed": bool(record.get("trial_valid"))},
            failure_reason=record.get("failure_reason"),
        )
        for record in records
    ]
    sweeps.write_sweep_summary(context.parent, results)
    sweeps.write_failed_and_suspicious(context.parent, results)
    sweeps.write_state_tracking(
        context.parent,
        [
            {
                "trial_index": record.get("trial_index"),
                "reference_trial": record.get("state_tracking_reference_trial"),
                "state_tracking_confidence": record.get("state_tracking_confidence"),
                "assignment_margin": record.get("state_tracking_margin"),
                "ambiguous": record.get("state_tracking_ambiguous"),
                "raw_indices": record.get("raw_state_indices"),
                "tracked_labels": record.get("tracked_state_labels"),
                "method": record.get("state_tracking_method"),
            }
            for record in records
        ],
    )

    manifest = sweeps.write_sweep_manifest(
        context.parent,
        cfg=cfg,
        machine=context.machine,
        results=results,
        dependency_report=context.dependency_report,
        parser_provenance={"profile": cfg["outputs"].get("parser_profile")},
        extra={
            "workflow_mode": mode,
            "ax": versions,
            "optimization": experiment.spec.as_record(),
            "run_plan": plan_record,
            "experiment_state_dir": str(state_dir),
            "experiment_resumed": experiment.resumed,
            "loop_stop_reason": loop_result.get("stop_reason"),
            "loop_events": loop_result.get("events"),
            "extraction_version": EXTRACTION_VERSION,
            "warm_start": {
                key: value
                for key, value in ((replay or {}).get("ingested") or {}).items()
                if key != "provenance_rows"
            },
            "replay": {
                key: value
                for key, value in (replay or {}).items()
                if key not in {"ingested", "comparison"}
            },
            "validation_study": {
                key: value
                for key, value in validation.items()
                if key not in {"validation_rows", "robustness_rows"}
            },
            "summary": artifacts["summary"],
            "synthetic_study": synthetic,
            "licensed_result_claim": (
                "not run"
                if not any(result.solver_success for result in results)
                else "see criterion-level validation report"
            ),
        },
    )
    write_json_atomically(
        experiment.state_dir / "experiment_manifest.json",
        {
            "demo_id": cfg["demo_id"],
            "experiment_name": (cfg.get("workflow") or {}).get("experiment_name"),
            "ax": versions,
            "optimization": experiment.spec.as_record(),
            "run_plan": plan_record,
            "last_run_bundle": str(context.parent),
            "extraction_version": EXTRACTION_VERSION,
            "updated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
    )

    licensed = any(result.solver_success for result in results)
    sweeps.write_validation_report(
        context.parent,
        cfg=cfg,
        manifest=manifest,
        registry_record=context.registry_record,
        dependency_report=context.dependency_report,
        criteria=[
            (
                "Ax version is installed and matches the repository pin",
                bool(versions["ax_version_matches_pin"]),
                f"installed {versions['ax_version_installed']}, pinned "
                f"{versions['ax_version_pinned']}",
            ),
            (
                "the configured BO budget was produced from the YAML",
                plan_record["expected_maximum_new_solver_runs"]
                == plan_record["num_initial_trials"]
                + plan_record["num_iterations"] * plan_record["batch_size"],
                "initial + iterations x batch, recomputed on every run",
            ),
            (
                "every generated candidate has an immutable ledger record",
                len(records) == len({int(record["trial_index"]) for record in records}),
                "one JSON file per trial; terminal records are never rewritten",
            ),
            (
                "licensed trials completed",
                True if licensed else None,
                "no licensed nextnano++ solver ran on this machine"
                if not licensed
                else f"{sum(1 for r in results if r.solver_success)} completed",
            ),
            (
                "top designs passed Stage 5 validation",
                True if validation.get("solver_ran") and validation.get("enabled") else None,
                "run workflow.mode: validate_top_designs on the licensed machine",
            ),
        ],
        notes=[
            "Demo 11 extraction, interband chi(2), origin-independence and quasi-bound "
            "diagnostics are reused unchanged; Demo 12 renders every input.",
            "A mechanically failed trial is reported to Ax as failed and never as a "
            "zero objective.",
            "The highest Ax objective is a proposed optimum until Stage 5 passes.",
            f"Workflow mode for this run: {mode}.",
        ],
        unvalidated_syntax=[
            "inherits Demo 12's unvalidated ternary_linear/ternary_constant "
            "alloy-composition output layout"
        ],
    )
    return sweeps.finish_run(context, results=results, manifest=manifest)


def check(demo_dir: Path, machine_path: Path | None = None) -> int:
    """``--check``: report the environment and the planned budget, run nothing."""

    from demo_workflow import load_demo_config, load_machine_config

    cfg = load_demo_config(demo_dir)
    validate_demo13_config(cfg)
    machine = load_machine_config(machine_path)
    versions = axsearch13.check_ax_version(cfg)
    state_dir = experiment_state_dir(cfg, machine.results_root)
    ledger = axsearch13.Ledger(state_dir) if state_dir.is_dir() else None
    plan_record = (
        axsearch13.plan(cfg, ledger)
        if ledger is not None
        else {
            **design13.expected_evaluation_counts(cfg),
            "completed_trials": 0,
            "failed_trials": 0,
            "pending_trials": 0,
            "remaining_trials": design13.expected_evaluation_counts(cfg)[
                "expected_maximum_new_solver_runs"
            ],
            "completed_bo_iterations": 0,
            "remaining_bo_iterations": int(cfg["bo"]["num_iterations"]),
            "estimated_remaining_runtime_seconds": None,
            "estimated_runtime_basis": "no experiment state yet",
            "evaluation_formula": "initial_trials + num_iterations * batch_size",
        }
    )
    summary = machine_summary(machine)
    print(f"Demo:                 {cfg['demo_id']}")
    print(f"Workflow mode:        {(cfg.get('workflow') or {}).get('mode')}")
    print(f"Ax version:           {versions['ax_version_installed']} "
          f"(pinned {versions['ax_version_pinned']}, api {versions['ax_api']})")
    print(f"Solver executable:    {summary.get('executable')}")
    print(f"Solver enabled:       {machine.run_solver and bool((cfg.get('simulation') or {}).get('run_solver'))}")
    print(f"Results root:         {summary.get('results_root')}")
    print(f"Experiment state dir: {state_dir}")
    print("Search space:")
    for spec in design13.search_space_specs(cfg):
        row = spec.as_row()
        print(
            f"  {row['parameter']:<34} {row['type']:<8} "
            + (f"[{row['lower']}, {row['upper']}]" if row["type"] == "range" else str(row["values"]))
        )
    print("\n".join(axsearch13.plan_report_lines(plan_record)))
    return 0
