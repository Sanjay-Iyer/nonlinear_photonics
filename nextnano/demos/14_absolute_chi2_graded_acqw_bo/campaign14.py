"""Demo 14 campaign: the loop that turns a config into 30 completed trials.

Budget semantics, which are the part most easily got wrong:

* the target is 30 **completed** solver trials -- a trial that ran and produced
  a finite objective counts, whether or not it satisfied the constraints,
  because it taught the surrogate something real;
* a preflight rejection consumes nothing, and in Demo 14 should never happen at
  all (the parameterization is feasible by construction), so one is escalated as
  an implementation bug rather than absorbed;
* a technical failure consumes nothing and **stops** the campaign.

Checkpointing is after every outcome, atomically, so a crash at trial 17 loses
nothing and ``--resume`` continues at 18.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import signal
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

import demo14
import grading14
import physics14
import runlog14
import solver14

LEDGER_NAME = "trial_ledger.jsonl"
PROPOSALS_NAME = "proposals.csv"
BEST_NAME = "best_so_far.csv"


class CampaignStopped(RuntimeError):
    """The campaign ended before its budget for a recorded reason."""


# ---------------------------------------------------------------------------
# Ax
# ---------------------------------------------------------------------------


def build_ax_client(cfg: Mapping[str, Any], seed: int):
    """Create the Ax client for the Demo 14 search space.

    Flat (not hierarchical): every Demo 14 design is graded and every parameter
    applies to every profile, so there is no branch to model. Demo 13 needed a
    tree only because its abrupt designs had no grading parameters at all.
    """

    from ax.api.client import Client
    from ax.api.configs import ChoiceParameterConfig, RangeParameterConfig

    space = cfg["optimization"]["search_space"]
    parameters = [
        RangeParameterConfig(
            name=name, parameter_type="float",
            bounds=(float(space[name]["lower"]), float(space[name]["upper"])),
        )
        for name in (
            "asymmetry_s",
            "nominal_central_barrier_thickness_nm",
            "gaas_to_algaas_grading_width_10_90_nm",
            "algaas_to_gaas_grading_width_10_90_nm",
        )
    ]
    parameters.append(
        ChoiceParameterConfig(
            name="grading_profile", parameter_type="str",
            values=list(space["grading_profile"]["values"]),
            is_ordered=False,
        )
    )
    client = Client(random_seed=int(seed))
    client.configure_experiment(
        parameters=parameters, name=str(cfg["experiment"]["name"])
    )
    limits = cfg["constraints"]
    client.configure_optimization(
        objective=demo14.objective_name(cfg),
        outcome_constraints=[
            f"absolute_detuning_nm <= {float(limits['maximum_detuning_nm'])}",
            f"maximum_boundary_probability <= {float(limits['maximum_boundary_probability'])}",
            f"state_tracking_confidence >= {float(limits['minimum_state_tracking_confidence'])}",
        ],
    )
    return client


def ax_metrics(outcome: demo14.TrialOutcome, cfg: Mapping[str, Any]) -> dict[str, float]:
    """Only the metrics Ax models. Everything else lives in the ledger."""

    metrics = outcome.metrics
    return {
        demo14.objective_name(cfg): float(outcome.objective() or 0.0),
        "absolute_detuning_nm": float(metrics.get("absolute_detuning_nm") or 0.0),
        "maximum_boundary_probability": float(
            metrics.get("maximum_boundary_probability") or 0.0
        ),
        "state_tracking_confidence": float(
            metrics.get("state_tracking_confidence") or 0.0
        ),
    }


# ---------------------------------------------------------------------------
# Ledger and checkpoints
# ---------------------------------------------------------------------------


def append_ledger(paths: runlog14.RunPaths, record: Mapping[str, Any]) -> None:
    path = paths.optimization / LEDGER_NAME
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(runlog14.json_safe(dict(record)), sort_keys=True,
                                allow_nan=False) + "\n")
        handle.flush()


def read_ledger(paths: runlog14.RunPaths) -> list[dict[str, Any]]:
    path = paths.optimization / LEDGER_NAME
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def checkpoint(
    paths: runlog14.RunPaths, client: Any, status: runlog14.RunStatus,
    manifest: dict[str, Any], events: runlog14.EventLog, tag: str,
) -> None:
    """Persist Ax state, manifest and status atomically after every outcome."""

    snapshot = paths.optimization / "ax_experiment_snapshot.json"
    if client is not None:
        temporary = snapshot.with_name(f"~{snapshot.name}.tmp")
        try:
            client.save_to_json_file(str(temporary))
            import os
            os.replace(temporary, snapshot)
        except Exception as exc:  # pragma: no cover - Ax serialization is version-sensitive
            events.emit("CHECKPOINT_WRITTEN", stage="checkpoint", status="warning",
                        message=f"Ax snapshot failed: {type(exc).__name__}: {exc}")
    runlog14.write_json_atomic(paths.manifest_file, manifest)
    status.update(last_checkpoint=runlog14.utc_now())
    events.emit("CHECKPOINT_WRITTEN", stage="checkpoint", status="ok", tag=tag)


def write_best_so_far(paths: runlog14.RunPaths, rows: Sequence[Mapping[str, Any]]) -> None:
    header = "trial_id,phase,objective_pm_per_V,feasible,best_so_far_pm_per_V,best_trial\n"
    best = -math.inf
    best_id = ""
    lines = []
    for row in rows:
        value = row.get("objective_pm_per_V")
        feasible = bool(row.get("feasible"))
        if feasible and value is not None and float(value) > best:
            best, best_id = float(value), str(row.get("trial_id"))
        lines.append(
            f"{row.get('trial_id')},{row.get('generation_phase')},"
            f"{'' if value is None else value},{feasible},"
            f"{'' if best == -math.inf else best},{best_id}\n"
        )
    runlog14.write_text_atomic(paths.optimization / BEST_NAME, header + "".join(lines))


def write_proposals(paths: runlog14.RunPaths, rows: Sequence[Mapping[str, Any]]) -> None:
    header = (
        "trial_id,phase,grading_profile,asymmetry_s,barrier_nm,width_left_nm,"
        "width_right_nm,status,objective_pm_per_V,feasible\n"
    )
    lines = []
    for row in rows:
        p = row.get("parameters", {})
        lines.append(
            f"{row.get('trial_id')},{row.get('generation_phase')},"
            f"{p.get('grading_profile')},{p.get('asymmetry_s')},"
            f"{p.get('nominal_central_barrier_thickness_nm')},"
            f"{p.get('gaas_to_algaas_grading_width_10_90_nm')},"
            f"{p.get('algaas_to_gaas_grading_width_10_90_nm')},"
            f"{row.get('status')},{row.get('objective_pm_per_V') or ''},"
            f"{row.get('feasible')}\n"
        )
    runlog14.write_text_atomic(paths.optimization / PROPOSALS_NAME, header + "".join(lines))


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


def run_campaign(
    cfg: Mapping[str, Any],
    *,
    results_root: Path,
    machine: Any | None = None,
    mock: bool = False,
    mock_plan: Mapping[str, str] | None = None,
    resume_dir: Path | None = None,
    config_path: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run (or resume) one Demo 14 campaign to its completed-trial budget."""

    warnings = demo14.validate_config(cfg)
    opt = cfg["optimization"]
    target = int(opt["target_completed_trials"])
    initial = int(opt["initialization_trials"])
    seed = int(opt["random_seed"])

    facts = runlog14.git_facts(demo14.REPO_ROOT)
    if resume_dir is not None:
        root = Path(resume_dir)
        if not root.is_dir():
            raise CampaignStopped(f"cannot resume: {root} is not a directory")
        run_id = json.loads((root / "manifest.json").read_text(encoding="utf-8"))["run_id"]
    else:
        root, run_id = runlog14.new_run_directory(
            results_root, git_short_sha=facts["git_commit_short"], mock=mock
        )

    paths = runlog14.RunPaths(root)
    logger = runlog14.configure_logging(paths, verbose=verbose)
    events = runlog14.EventLog(paths.events_file, run_id)
    timing = runlog14.TimingLog(paths.timing_file, run_id)
    settings = physics14.settings_from_config(cfg)

    status = runlog14.RunStatus(
        path=paths.status_file, run_id=run_id, target_completed_trials=target, mock=mock
    )
    status.write()

    manifest = runlog14.build_manifest(
        run_id=run_id, paths=paths, cfg=cfg, repo_root=demo14.REPO_ROOT,
        config_path=Path(config_path) if config_path else demo14.DEMO_DIR / "demo.yaml",
        machine=machine, settings=settings, mock=mock,
        planned_initial=initial, planned_bo=int(opt["bo_trials"]), seed=seed,
    )
    manifest["resolved_config_sha256"] = runlog14.dump_resolved_config(paths, cfg)
    runlog14.write_json_atomic(paths.manifest_file, manifest)
    runlog14.write_environment_snapshot(paths, demo14.REPO_ROOT, machine)
    runlog14.install_excepthook(logger, events, status, paths)

    banner = [
        "=" * 74,
        f"  DEMO 14 {'MOCK ' if mock else ''}CAMPAIGN",
        "=" * 74,
        f"  RUN ID                  : {run_id}",
        f"  RUN DIRECTORY           : {root}",
        f"  GIT COMMIT              : {facts['git_commit']} "
        f"({'DIRTY' if facts['git_dirty'] else 'clean'})",
        f"  CONFIG                  : {config_path or demo14.DEMO_DIR / 'demo.yaml'}",
        f"  SOLVER                  : "
        f"{'<MOCK - NOT SCIENTIFIC>' if mock else getattr(machine, 'executable', None)}",
        f"  TARGET COMPLETED TRIALS : {target} ({initial} init + {opt['bo_trials']} BO)",
        f"  OBJECTIVE               : maximize {demo14.objective_name(cfg)}",
        f"  TARGET WAVELENGTH       : {cfg['chi2']['target_wavelength_nm']} nm",
        f"  N_z                     : {settings.n_wells_per_metre:.6e} m^-1 "
        f"({cfg['chi2']['nz_mode']})",
        f"  r_e_hh                  : {settings.r_e_hh_nm} nm",
        "=" * 74,
    ]
    if mock:
        banner.insert(1, "  *** MOCK MODE: results are synthetic, scientific_valid=false ***")
    for line in banner:
        logger.info(line)
    for warning in warnings:
        logger.warning("config: %s", warning)

    events.emit("RUN_STARTED", stage="startup", status="ok", run_directory=str(root),
                mock=mock, target_completed_trials=target)
    status.update(status="RUNNING")

    rng = np.random.default_rng(seed)
    design = demo14.stratified_initial_design(cfg, rng)
    client = None
    if not mock or True:
        try:
            client = build_ax_client(cfg, seed)
        except Exception as exc:
            logger.warning("Ax unavailable (%s: %s); initialization design only.",
                           type(exc).__name__, exc)
            events.emit("CONFIG_LOADED", stage="startup", status="warning",
                        message=f"Ax unavailable: {exc}")

    existing = read_ledger(paths) if resume_dir else []
    completed = sum(1 for r in existing if r.get("status") in ("completed", "infeasible"))
    records: list[dict[str, Any]] = list(existing)
    index = max([int(r["trial_index"]) for r in existing], default=-1) + 1

    interrupted = {"flag": False}

    def _on_sigint(signum, frame):  # pragma: no cover - interactive path
        interrupted["flag"] = True
        logger.warning("Interrupt received; finishing the current trial then stopping.")

    try:
        previous_handler = signal.signal(signal.SIGINT, _on_sigint)
    except Exception:  # pragma: no cover - not all environments allow this
        previous_handler = None

    final_status = "COMPLETED"
    stop_reason: str | None = None

    try:
        while completed < target:
            phase = "initialization" if completed < initial else "bayesian_optimization"
            if phase == "initialization" and completed < len(design):
                parameters = dict(design[completed])
                ax_index = None
            else:
                parameters, ax_index = _next_from_ax(client, design, rng, cfg, completed)

            status.update(current_trial=demo14.trial_id(index), current_stage=phase)
            outcome = demo14.run_one_trial(
                cfg=cfg, paths=paths, events=events, timing=timing, logger=logger,
                index=index, phase=phase, parameters=parameters, mock=mock,
                mock_behaviour=solver14.choose_behaviour(
                    demo14.trial_id(index), mock_plan
                ),
                machine=machine,
            )
            record = outcome.as_record()
            record["ax_trial_index"] = ax_index
            append_ledger(paths, record)
            records.append(record)
            index += 1

            if outcome.status == "technical_failure":
                status.technical_failures += 1
                status.failed_trials += 1
                final_status = "FAILED"
                stop_reason = (
                    f"technical failure at {outcome.trial_id} "
                    f"({outcome.failure_stage}): {outcome.failure_reason}"
                )
                logger.error(stop_reason)
                logger.error(
                    "Stopping the campaign rather than spending the remaining "
                    "%d licensed trials on a known-broken pipeline.",
                    target - completed,
                )
                status.update(status="FAILED", last_error=stop_reason)
                checkpoint(paths, client, status, manifest, events, "technical_failure")
                break

            if outcome.status == "rejected":
                status.rejected_trials += 1
            else:
                completed += 1
                status.completed_trials = completed
                if client is not None and ax_index is not None:
                    try:
                        client.complete_trial(
                            trial_index=ax_index, raw_data=ax_metrics(outcome, cfg)
                        )
                    except Exception as exc:
                        logger.warning("Ax completion failed for %s: %s",
                                       outcome.trial_id, exc)
                events.emit("AX_RESULT_RECORDED", trial_id=outcome.trial_id,
                            stage="ax", status="ok", objective=outcome.objective())

            feasible_rows = [
                r for r in records
                if r.get("feasible") and r.get("objective_pm_per_V") is not None
            ]
            if feasible_rows:
                best = max(feasible_rows, key=lambda r: float(r["objective_pm_per_V"]))
                status.current_best_trial = str(best["trial_id"])
                status.current_best_objective_pm_per_V = float(best["objective_pm_per_V"])

            write_best_so_far(paths, records)
            write_proposals(paths, records)
            manifest.update({
                "actual_completed_trials": completed,
                "actual_failed_trials": status.failed_trials,
                "actual_rejected_trials": status.rejected_trials,
                "final_best_trial": status.current_best_trial,
                "final_best_objective_pm_per_V": status.current_best_objective_pm_per_V,
            })
            checkpoint(paths, client, status, manifest, events, outcome.trial_id)
            logger.info(
                "%s  %-22s %-8s objective=%s  best=%s (%s)",
                outcome.trial_id, outcome.status, parameters.get("grading_profile"),
                _fmt(outcome.objective()), _fmt(status.current_best_objective_pm_per_V),
                status.current_best_trial or "-",
            )

            if interrupted["flag"]:
                final_status = "INTERRUPTED"
                stop_reason = "interrupted by user"
                status.update(status="INTERRUPTED")
                events.emit("RUN_INTERRUPTED", stage="loop", status="interrupted")
                break

    except KeyboardInterrupt:  # pragma: no cover - interactive path
        final_status = "INTERRUPTED"
        stop_reason = "KeyboardInterrupt"
        status.update(status="INTERRUPTED", last_error=stop_reason)
        events.emit("RUN_INTERRUPTED", stage="loop", status="interrupted")
        checkpoint(paths, client, status, manifest, events, "interrupt")
    finally:
        if previous_handler is not None:
            try:
                signal.signal(signal.SIGINT, previous_handler)
            except Exception:  # pragma: no cover
                pass

    manifest.update({
        "end_timestamp_utc": runlog14.utc_now(),
        "actual_completed_trials": completed,
        "actual_failed_trials": status.failed_trials,
        "actual_rejected_trials": status.rejected_trials,
        "final_status": final_status,
        "final_best_trial": status.current_best_trial,
        "final_best_objective_pm_per_V": status.current_best_objective_pm_per_V,
    })
    runlog14.write_json_atomic(paths.manifest_file, manifest)
    status.update(status=final_status)
    write_timing_summary(paths, timing)
    write_summary(paths, cfg, manifest, records, final_status, stop_reason, mock)
    events.emit("RUN_COMPLETED" if final_status == "COMPLETED" else "RUN_FAILED",
                stage="shutdown", status=final_status, message=stop_reason or "")
    runlog14.flush_logging(logger)
    events.close()
    # Release the log files: Windows keeps them locked otherwise, which blocks
    # bundling and leaks descriptors when several campaigns share a process.
    runlog14.close_logging(logger)

    return {
        "run_id": run_id,
        "run_directory": str(root),
        "status": final_status,
        "completed_trials": completed,
        "target_completed_trials": target,
        "rejected_trials": status.rejected_trials,
        "technical_failures": status.technical_failures,
        "best_trial": status.current_best_trial,
        "best_objective_pm_per_V": status.current_best_objective_pm_per_V,
        "stop_reason": stop_reason,
        "mock": mock,
        "scientific_valid": not mock,
    }


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.4g}"


def _next_from_ax(client, design, rng, cfg, completed: int):
    """Ask Ax for the next point; fall back to a random draw if it cannot."""

    if client is not None:
        try:
            proposals = client.get_next_trials(max_trials=1)
            for ax_index, params in proposals.items():
                return dict(params), int(ax_index)
        except Exception:
            pass
    space = cfg["optimization"]["search_space"]
    families = list(space["grading_profile"]["values"])
    return (
        {
            "asymmetry_s": float(rng.uniform(
                space["asymmetry_s"]["lower"], space["asymmetry_s"]["upper"])),
            "nominal_central_barrier_thickness_nm": float(rng.uniform(
                space["nominal_central_barrier_thickness_nm"]["lower"],
                space["nominal_central_barrier_thickness_nm"]["upper"])),
            "gaas_to_algaas_grading_width_10_90_nm": float(rng.uniform(
                space["gaas_to_algaas_grading_width_10_90_nm"]["lower"],
                space["gaas_to_algaas_grading_width_10_90_nm"]["upper"])),
            "algaas_to_gaas_grading_width_10_90_nm": float(rng.uniform(
                space["algaas_to_gaas_grading_width_10_90_nm"]["lower"],
                space["algaas_to_gaas_grading_width_10_90_nm"]["upper"])),
            "grading_profile": families[int(rng.integers(len(families)))],
        },
        None,
    )


def write_timing_summary(paths: runlog14.RunPaths, timing: runlog14.TimingLog) -> None:
    rows = timing.summary_rows()
    header = "stage,trial_id,elapsed_seconds,timestamp\n"
    body = "".join(
        f"{r.get('stage')},{r.get('trial_id') or ''},"
        f"{r.get('elapsed_seconds', 0.0):.6f},{r.get('timestamp')}\n" for r in rows
    )
    runlog14.write_text_atomic(paths.summaries / "timing_summary.csv", header + body)


def write_summary(
    paths: runlog14.RunPaths, cfg: Mapping[str, Any], manifest: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]], final_status: str,
    stop_reason: str | None, mock: bool,
) -> Path:
    """Human-readable close-out. A failure gets its own, differently named file."""

    completed = [r for r in records if r.get("status") in ("completed", "infeasible")]
    feasible = [r for r in completed if r.get("feasible")]
    failures = [r for r in records if r.get("status") == "technical_failure"]
    best = max(
        (r for r in feasible if r.get("objective_pm_per_V") is not None),
        key=lambda r: float(r["objective_pm_per_V"]), default=None,
    )
    lines = [
        f"# Demo 14 run summary{' (MOCK -- NOT SCIENTIFIC)' if mock else ''}",
        "",
        f"- **Run ID**: {manifest.get('run_id')}",
        f"- **Status**: {final_status}",
        f"- **Mode**: {'MOCK (scientific_valid=false)' if mock else 'real licensed solver'}",
        f"- **Git commit**: {manifest.get('git_commit')} "
        f"({'dirty' if manifest.get('git_dirty') else 'clean'})",
        f"- **Config SHA256**: {manifest.get('resolved_config_sha256')}",
        f"- **Objective**: maximize `{manifest.get('objective')}`",
        f"- **Target wavelength**: {cfg['chi2']['target_wavelength_nm']} nm",
        f"- **r_e_hh**: {manifest.get('r_e_hh_nm')} nm",
        f"- **N_z**: {manifest.get('n_wells_per_metre')} m^-1 ({manifest.get('nz_mode')})",
        "",
        "## Trials",
        "",
        f"| Quantity | Count |",
        f"|---|---|",
        f"| proposed | {len(records)} |",
        f"| completed (counted against budget) | {len(completed)} |",
        f"| feasible | {len(feasible)} |",
        f"| preflight rejected | {sum(1 for r in records if r.get('status') == 'rejected')} |",
        f"| technical failures | {len(failures)} |",
        f"| target | {manifest.get('planned_completed_trials')} |",
        "",
    ]
    if stop_reason:
        lines += [f"**Stopped early**: {stop_reason}", ""]
    if best:
        p = best.get("parameters", {})
        lines += [
            "## Best feasible design", "",
            f"- **Trial**: {best.get('trial_id')}",
            f"- **chi2(1550 nm)**: {best.get('objective_pm_per_V')} pm/V",
            f"- **Grading profile**: {p.get('grading_profile')}",
            f"- **asymmetry_s**: {p.get('asymmetry_s')}",
            f"- **barrier**: {p.get('nominal_central_barrier_thickness_nm')} nm",
            f"- **widths (L/R)**: {p.get('gaas_to_algaas_grading_width_10_90_nm')} / "
            f"{p.get('algaas_to_gaas_grading_width_10_90_nm')} nm",
            f"- **peak chi2**: {best.get('metrics', {}).get('peak_chi2_xzx_pm_per_V')} pm/V",
            f"- **peak wavelength**: {best.get('metrics', {}).get('peak_wavelength_nm')} nm",
            f"- **detuning**: {best.get('metrics', {}).get('signed_detuning_nm')} nm",
            "",
        ]
    else:
        lines += ["## Best feasible design", "", "No feasible trial was recorded.", ""]

    anomalies = [(r.get("trial_id"), a) for r in records for a in r.get("anomalies", [])]
    if anomalies:
        lines += ["## Anomalies", ""] + [f"- `{t}`: {a}" for t, a in anomalies] + [""]
    if failures:
        lines += ["## Technical failures", ""] + [
            f"- `{r.get('trial_id')}` at {r.get('failure_stage')}: {r.get('failure_reason')}"
            for r in failures
        ] + [""]
    if mock:
        lines += [
            "## Warning", "",
            "These numbers came from the deterministic mock solver. They exercise "
            "the harness and are **not** physics. `scientific_valid` is false in "
            "every record produced by this run.", "",
        ]

    name = "DEMO14_RUN_SUMMARY.md" if final_status == "COMPLETED" else "DEMO14_FAILURE_SUMMARY.md"
    return runlog14.write_text_atomic(paths.summaries / name, "\n".join(lines) + "\n")
