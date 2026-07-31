"""Sweep execution and artifact writing shared by Demos 4-10.

One rule shapes this module: **no sweep point ever disappears.**  A case that
fails to render, fails in the solver, or fails a physical check still gets its
own directory, its own generated input, its own preserved logs, and its own row
in every summary table -- flagged, never dropped.  Ranking may exclude it;
reporting may not hide it.
"""

from __future__ import annotations

import csv
import datetime as dt
import itertools
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import yaml

import demo_workflow as workflow
import plots as _plots
import registry as registry_module
from demo_workflow import DemoError, MachineConfig


@dataclass(frozen=True)
class RunContext:
    """Everything a demo's ``main`` needs before it starts generating cases."""

    demo_dir: Path
    cfg: dict[str, Any]
    machine: MachineConfig
    parent: Path
    registry_record: dict[str, Any]
    dependency_report: dict[str, Any]

    @property
    def demo_id(self) -> str:
        return str(self.cfg["demo_id"])


def prepare_run(demo_dir: Path, machine_path: Path | None = None) -> RunContext:
    """Load configuration, resolve the machine, and open a fresh run directory."""

    demo_dir = demo_dir.resolve()
    cfg = workflow.load_demo_config(demo_dir)
    machine = workflow.load_machine_config(machine_path)
    parent = machine.results_root / str(cfg["demo_id"]) / workflow.make_run_id()
    parent.mkdir(parents=True, exist_ok=False)
    registry = registry_module.load_registry()
    record = registry.record(str(cfg["demo_id"]))
    _plots.reset_skipped()
    workflow.write_text_atomically(
        parent / "demo_resolved.yaml", yaml.safe_dump(cfg, sort_keys=True)
    )
    workflow.write_json_atomically(
        parent / "machine_summary.json", workflow.machine_summary(machine)
    )
    return RunContext(
        demo_dir=demo_dir,
        cfg=cfg,
        machine=machine,
        parent=parent,
        registry_record=record.as_dict(),
        dependency_report=registry.dependency_report(str(cfg["demo_id"])),
    )


def finish_run(
    context: RunContext,
    *,
    results: Sequence[CaseResult],
    manifest: Mapping[str, Any],
) -> int:
    """Common tail: gather logs, print the artifact location, pick an exit code."""

    collect_console_logs(context.parent, results)
    workflow.write_text_atomically(
        context.parent / "console.log",
        "\n".join(
            [
                f"Demo: {context.demo_id}",
                f"Status: {manifest.get('status')}",
                f"Cases: {manifest.get('case_count')}",
                f"Solver successes: {manifest.get('solver_success_count')}",
                f"Skipped (no solver): {manifest.get('skipped_count')}",
                f"Failed: {manifest.get('failed_count')}",
                f"Suspicious: {manifest.get('suspicious_count')}",
            ]
        )
        + "\n",
    )
    print(f"{context.demo_id} artifacts: {context.parent}")
    status = manifest.get("status")
    return 0 if status in {"completed", "dry_run_complete"} else 1


def demo_cli(demo_dir: Path, main: Callable[[Path], int]) -> int:
    """Entry point wrapper shared by every Demo 4-10 ``run.py``."""

    try:
        return main(demo_dir)
    except DemoError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # surface the class so the cause is never hidden
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


@dataclass(frozen=True)
class CaseSpec:
    """One point of a sweep: what varies, and what it renders to."""

    case_id: str
    label: str
    swept: Mapping[str, Any]
    config: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def row(self) -> dict[str, Any]:
        row: dict[str, Any] = {"case_id": self.case_id, "label": self.label}
        row.update({str(name): value for name, value in self.swept.items()})
        row.update({str(name): value for name, value in self.metadata.items()})
        return row


@dataclass
class CaseResult:
    """Outcome of one case, whether or not it succeeded."""

    spec: CaseSpec
    run_dir: Path
    status: str
    return_code: int | None = None
    runtime_seconds: float = 0.0
    observables: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    failure_reason: str | None = None

    @property
    def solver_success(self) -> bool:
        return self.status == "completed"

    @property
    def suspicious(self) -> bool:
        """Ran, but something in the physics or numerics does not add up."""

        if self.status != "completed":
            return False
        return self.validation.get("passed") is False

    def row(self) -> dict[str, Any]:
        row = self.spec.row()
        row.update(
            {
                "status": self.status,
                "solver_success": self.solver_success,
                "return_code": self.return_code,
                "runtime_seconds": self.runtime_seconds,
                "validation_passed": self.validation.get("passed"),
                "failure_reason": self.failure_reason,
                "run_dir": str(self.run_dir),
            }
        )
        for key, value in self.observables.items():
            if isinstance(value, (int, float, str, bool)) or value is None:
                row[key] = value
        return row


def safe_token(value: Any) -> str:
    """Filesystem-safe rendering of a parameter value, sign preserved."""

    text = f"{value}"
    return (
        text.replace("-", "m")
        .replace("+", "p")
        .replace(".", "p")
        .replace(" ", "")
        .replace("/", "_")
    )


#: Unit suffixes stripped before abbreviating a parameter name.
_UNIT_WORDS = frozenset({"nm", "cm", "cm3", "ev", "mev", "k", "kv", "v", "kv_cm"})


def abbreviate(name: str) -> str:
    """Compact, deterministic abbreviation of a parameter name.

    ``center_barrier_nm`` becomes ``cb`` and ``quantum_region_padding_nm``
    becomes ``qrp``.  Case directory names feed directly into the path that
    nextnano++ appends its own nested output tree to, and Windows still enforces
    a 260-character limit on ordinary file APIs, so long descriptive directory
    names silently break real runs.  The full parameter name is preserved in
    every manifest, summary table, and plot label.
    """

    words = [
        word
        for word in str(name).lower().split("_")
        if word and word not in _UNIT_WORDS
    ]
    if not words:
        return str(name)[:4]
    return "".join(word[0] for word in words)


#: Longest relative path nextnano++ appends below a run directory, measured on
#: the licensed laptop on 2026-07-30. The worst artifact is the dipole
#: matrix-element table:
#:
#:   /raw_output/case/bias_00000/Quantum/<region>/Gamma_Gamma/   36 + region + 13
#:   dipole_moment_matrix_elements_k00000_<polarization>.txt     37 + pol + 4
#:
#: With a three-character region name and a ten-character polarization name that
#: is 103 characters; one is kept in hand.
SOLVER_OUTPUT_TAIL_LENGTH = 104

#: Windows refuses paths at 260 characters *including* the terminating NUL, so
#: the last usable length is 259.
WINDOWS_MAX_PATH = 259

#: Beyond this, a run directory leaves too little room for that tree.
MAX_RUN_DIR_LENGTH = WINDOWS_MAX_PATH - SOLVER_OUTPUT_TAIL_LENGTH  # 160


def check_path_budget(run_dir: Path) -> str | None:
    """Warn before a path that Windows will later refuse mid-run.

    This is not hypothetical. On 2026-07-30 twelve of Demo 9's twenty-four
    licensed cases died with exit code 4294967295 partway through writing their
    output: the Gamma_Gamma dipole file crossed 259 characters while the shorter
    single-variable case names stayed under it. The solver left ``job_running.txt``
    behind and wrote no matrix elements. Nothing about the physics differed --
    one of the failing cases had parameters identical to a case that succeeded.
    """

    length = len(str(run_dir))
    if length < MAX_RUN_DIR_LENGTH:
        return None
    return (
        f"run directory path is {length} characters ({run_dir}); nextnano++ appends "
        f"up to {SOLVER_OUTPUT_TAIL_LENGTH} more for its own output tree and Windows "
        f"refuses paths beyond {WINDOWS_MAX_PATH}. The solver will fail partway "
        "through writing results. Set a short results_root (for example "
        "'C:/nn_results') in nextnano_machine.local.yaml, or move the repository "
        "closer to the drive root."
    )


def copy_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Deep copy of a demo configuration, safe to mutate per case."""

    return json.loads(json.dumps(config))


_deep_copy = copy_config


#: Configuration sections a sweep may override a value in. ``metric`` is here
#: because post-processing conventions -- how many states an equation sums over,
#: what broadening it uses -- are swept in exactly the same way as geometry, and
#: they belong in YAML rather than in a hardcoded keyword argument.
OVERRIDABLE_SECTIONS: tuple[str, ...] = ("scientific", "numerical", "metric")


def apply_override(config: Mapping[str, Any], name: str, value: Any) -> dict[str, Any]:
    """Return a copy of ``config`` with one swept value replaced.

    The parameter must already exist in exactly one of
    :data:`OVERRIDABLE_SECTIONS`, so a sweep can never silently introduce a key
    the schema would have rejected, and can never quietly write to the wrong
    section when two of them happen to share a name.
    """

    copied = _deep_copy(config)
    present = [
        section
        for section in OVERRIDABLE_SECTIONS
        if name in (copied.get(section) or {})
    ]
    if len(present) > 1:
        raise DemoError(
            f"parameter {name!r} is ambiguous: it appears in "
            + " and ".join(present)
            + "."
        )
    if not present:
        raise DemoError(
            f"cannot sweep {name!r}: it is not declared under "
            + ", ".join(OVERRIDABLE_SECTIONS)
            + "."
        )
    copied[present[0]][name] = value
    return copied


def apply_overrides(
    config: Mapping[str, Any], overrides: Mapping[str, Any]
) -> dict[str, Any]:
    result = _deep_copy(config)
    for name, value in overrides.items():
        result = apply_override(result, name, value)
    return result


def single_variable_cases(
    config: Mapping[str, Any], name: str, values: Sequence[Any], *, prefix: str = ""
) -> list[CaseSpec]:
    """One case per value of a single parameter."""

    cases: list[CaseSpec] = []
    for index, value in enumerate(values, start=1):
        case_id = f"{prefix}{index:02d}_{abbreviate(name)}{safe_token(value)}"
        cases.append(
            CaseSpec(
                case_id=case_id,
                label=f"{name} = {value}",
                swept={name: value},
                config=apply_override(config, name, value),
                metadata={"sweep_kind": "single_variable", "sweep_parameter": name},
            )
        )
    return cases


def grid_cases(
    config: Mapping[str, Any], axes: Mapping[str, Sequence[Any]], *, prefix: str = "g"
) -> list[CaseSpec]:
    """Full Cartesian product of two or more parameter axes."""

    names = list(axes)
    if len(names) < 2:
        raise DemoError("a grid sweep needs at least two axes.")
    cases: list[CaseSpec] = []
    for index, combination in enumerate(
        itertools.product(*(list(axes[name]) for name in names)), start=1
    ):
        overrides = dict(zip(names, combination))
        # Only the index goes in the directory name. A grid over two parameters
        # produced names like `grid_007_www10p0_efm20p0`, which pushed the
        # licensed run past the Windows path limit and killed the solver
        # mid-write. The swept values are in every manifest, in parameters.csv,
        # and in the label.
        cases.append(
            CaseSpec(
                case_id=f"{prefix}{index:03d}",
                label=", ".join(f"{name} = {value}" for name, value in overrides.items()),
                swept=overrides,
                config=apply_overrides(config, overrides),
                metadata={"sweep_kind": "grid", "sweep_parameter": "+".join(names)},
            )
        )
    return cases


def design_list_cases(
    config: Mapping[str, Any],
    designs: Sequence[Mapping[str, Any]],
    *,
    prefix: str = "d",
) -> list[CaseSpec]:
    """Explicit multi-variable candidates that are not a product grid."""

    cases: list[CaseSpec] = []
    for index, design in enumerate(designs, start=1):
        overrides = {str(name): value for name, value in design.items() if name != "name"}
        name = str(design.get("name", f"design_{index}"))
        # Index only, for the Windows path budget. `design_02_wide_pair_` was
        # long enough to kill the solver on the licensed laptop; the full design
        # name survives in the label, the manifest, and every table.
        cases.append(
            CaseSpec(
                case_id=f"{prefix}{index:02d}",
                label=name,
                swept=overrides,
                config=apply_overrides(config, overrides),
                metadata={"sweep_kind": "design_list", "design_name": name},
            )
        )
    return cases


def expected_case_count(
    *,
    single: Mapping[str, Sequence[Any]] | None = None,
    grid: Mapping[str, Sequence[Any]] | None = None,
    designs: Sequence[Mapping[str, Any]] | None = None,
) -> int:
    """How many cases a sweep configuration will produce, before running it."""

    total = sum(len(values) for values in (single or {}).values())
    if grid:
        product = 1
        for values in grid.values():
            product *= len(values)
        total += product
    total += len(designs or ())
    return total


AnalyseFn = Callable[..., tuple[dict[str, Any], dict[str, Any]]]


def execute_case(
    *,
    demo_dir: Path,
    spec: CaseSpec,
    machine: MachineConfig,
    run_dir: Path,
    render_values: Callable[[Mapping[str, Any]], dict[str, Any]],
    analyse: AnalyseFn,
    template_name: str | None = None,
    dependency_report: Mapping[str, Any] | None = None,
) -> CaseResult:
    """Render, optionally execute, parse, validate, and preserve one case.

    ``render_values`` maps the case configuration to template substitutions.
    ``analyse`` is called only after a successful solver exit and receives
    ``(cfg, raw_dir, extracted_dir, plots_dir)``; it returns
    ``(observables, validation)``.  Any exception at any stage is captured into
    the manifest with the artifacts intact.
    """

    layout = workflow.create_run_layout(run_dir)
    logger = workflow.run_logger(run_dir)
    cfg = dict(spec.config)
    template = demo_dir / str(template_name or cfg["template"])
    warnings: list[str] = []
    budget_warning = check_path_budget(run_dir)
    if budget_warning:
        warnings.append(budget_warning)
        logger.warning(budget_warning)
    failure_reason: str | None = None
    observables: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    return_code: int | None = None
    runtime = 0.0
    status = "failed"
    generated: Path | None = None

    try:
        if not template.is_file():
            raise DemoError(f"input template not found: {template}")
        values = render_values(cfg)
        rendered = workflow.render_template(template.read_text(encoding="utf-8"), values)
        # nextnano++ repeats the input stem below its output directory.  A fixed,
        # short name leaves enough path budget for licensed runs on Windows.
        generated = layout["generated"] / "case.in"
        workflow.write_text_atomically(generated, rendered)
        workflow.write_text_atomically(
            run_dir / "demo_resolved.yaml", yaml.safe_dump(cfg, sort_keys=True)
        )
        workflow.write_json_atomically(
            run_dir / "machine_summary.json", workflow.machine_summary(machine)
        )
        validation["input_generation"] = True
    except Exception as exc:
        failure_reason = f"{type(exc).__name__}: {exc}"
        validation["input_generation"] = False
        logger.exception("Input generation failed: %s", exc)

    if failure_reason is None and not machine.run_solver:
        status = "skipped_no_solver"
        warnings.append(
            "Input generation and configuration validation succeeded. Solver "
            "execution was skipped: no complete licensed nextnano++ setup is "
            "available on this machine."
        )
        logger.info(warnings[-1])
    elif failure_reason is None:
        logger.info("Executing %s", generated)
        try:
            try:
                return_code, runtime = workflow.execute_solver(
                    machine, generated, layout["raw"]
                )
            finally:
                redacted = workflow.sanitize_solver_logs(layout["raw"])
                if redacted:
                    logger.info(
                        "Redacted licensed-user/key fields from %d solver log(s).",
                        redacted,
                    )
            if return_code not in (0, None):
                # A run that was already over the path budget and then died is
                # almost certainly a path-length failure, not a physics one.
                # Saying so here saves re-deriving it from an opaque exit code.
                hint = ""
                if budget_warning:
                    stalled = list(layout["raw"].rglob("job_running.txt"))
                    hint = (
                        " This case exceeded the Windows path budget before it "
                        "started"
                        + (
                            " and the solver left job_running.txt behind, so it "
                            "died partway through writing output."
                            if stalled
                            else "."
                        )
                        + " Treat the path length as the primary suspect: "
                        + budget_warning
                    )
                raise DemoError(
                    f"nextnano++ returned nonzero exit code {return_code}.{hint}"
                )
            parsed_observables, parsed_validation = analyse(
                cfg, layout["raw"], layout["extracted"], layout["plots"]
            )
            observables.update(parsed_observables)
            validation.update(parsed_validation)
            validation["passed"] = all(
                bool(value)
                for key, value in validation.items()
                if key not in {"passed"} and isinstance(value, bool)
            )
            status = "completed"
            logger.info("Case %s completed in %.3f s.", spec.case_id, runtime)
            if not validation["passed"]:
                logger.warning(
                    "Case %s completed but did not pass every check; it is retained "
                    "and flagged as suspicious.",
                    spec.case_id,
                )
        except Exception as exc:
            status = "failed"
            failure_reason = f"{type(exc).__name__}: {exc}"
            logger.exception("Case %s failed: %s", spec.case_id, exc)

    manifest: dict[str, Any] = {
        "schema": 1,
        "demo_id": cfg.get("demo_id"),
        "case_id": spec.case_id,
        "case_label": spec.label,
        "swept_parameters": dict(spec.swept),
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "template_path": str(template),
        "generated_input_path": str(generated) if generated else None,
        "generated_input_sha256": (
            workflow.sha256_of(generated) if generated and generated.is_file() else None
        ),
        "scientific_parameters": cfg.get("scientific"),
        "numerical_parameters": cfg.get("numerical"),
        "machine": workflow.machine_summary(machine),
        "solver_execution_status": status,
        "completion_status": status,
        "return_code": return_code,
        "runtime_seconds": runtime,
        "warnings": warnings,
        "observables": observables,
        "validation": validation,
        "failure_reason": failure_reason,
    }
    commit, dirty = workflow.git_state()
    manifest["git_commit"] = commit
    manifest["git_dirty"] = dirty
    if dependency_report is not None:
        manifest["dependency_status"] = dict(dependency_report)
    workflow.write_json_atomically(run_dir / "run_manifest.json", manifest)
    return CaseResult(
        spec=spec,
        run_dir=run_dir,
        status=status,
        return_code=return_code,
        runtime_seconds=runtime,
        observables=observables,
        validation=validation,
        warnings=warnings,
        failure_reason=failure_reason,
    )


# ---------------------------------------------------------------------------
# artifact writers
# ---------------------------------------------------------------------------


def _write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(str(key))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or ["note"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_sweep_summary(parent: Path, results: Sequence[CaseResult]) -> list[dict[str, Any]]:
    """Write ``sweep_summary.csv`` / ``.json`` covering every case."""

    rows = [result.row() for result in results]
    extracted = parent / "extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    _write_rows(extracted / "sweep_summary.csv", rows)
    workflow.write_json_atomically(extracted / "sweep_summary.json", rows)
    return rows


def write_failed_and_suspicious(
    parent: Path, results: Sequence[CaseResult]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Write the failed-run and suspicious-run tables (always, even if empty)."""

    extracted = parent / "extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    failed = [
        {
            **result.spec.row(),
            "status": result.status,
            "failure_reason": result.failure_reason
            or ("no licensed execution on this machine" if result.status != "completed" else ""),
            "run_dir": str(result.run_dir),
        }
        for result in results
        if result.status != "completed"
    ]
    suspicious = [
        {
            **result.spec.row(),
            "status": result.status,
            "failed_checks": ";".join(
                sorted(
                    key
                    for key, value in result.validation.items()
                    if isinstance(value, bool) and not value and key != "passed"
                )
            ),
            "run_dir": str(result.run_dir),
        }
        for result in results
        if result.suspicious
    ]
    _write_rows(extracted / "failed_runs.csv", failed or [{"note": "none"}])
    _write_rows(extracted / "suspicious_runs.csv", suspicious or [{"note": "none"}])
    return failed, suspicious


def write_state_tracking(parent: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write ``state_tracking.csv`` for sweeps that follow states between points."""

    extracted = parent / "extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    _write_rows(
        extracted / "state_tracking.csv",
        list(rows) or [{"note": "no state tracking data (no licensed solver output)"}],
    )


def write_table(parent: Path, name: str, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write one extra machine-readable table under ``tables/``."""

    tables = parent / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    _write_rows(tables / f"{name}.csv", list(rows) or [{"note": "no data"}])


def write_sweep_manifest(
    parent: Path,
    *,
    cfg: Mapping[str, Any],
    machine: MachineConfig,
    results: Sequence[CaseResult],
    dependency_report: Mapping[str, Any] | None = None,
    parser_provenance: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``sweep_manifest.json`` and the parent ``run_manifest.json``."""

    commit, dirty = workflow.git_state()
    completed = sum(1 for result in results if result.solver_success)
    skipped = sum(1 for result in results if result.status == "skipped_no_solver")
    failed = sum(1 for result in results if result.status == "failed")
    if not machine.run_solver:
        status = "dry_run_complete"
    elif failed == 0 and completed == len(results):
        status = "completed"
    else:
        status = "failed"
    manifest: dict[str, Any] = {
        "schema": 1,
        "demo_id": cfg.get("demo_id"),
        "title": cfg.get("title"),
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": commit,
        "git_dirty": dirty,
        "machine": workflow.machine_summary(machine),
        "status": status,
        "case_count": len(results),
        "solver_success_count": completed,
        "skipped_count": skipped,
        "failed_count": failed,
        "suspicious_count": sum(1 for result in results if result.suspicious),
        "cases": [
            {
                "case_id": result.spec.case_id,
                "label": result.spec.label,
                "swept": dict(result.spec.swept),
                "status": result.status,
                "runtime_seconds": result.runtime_seconds,
                "run_dir": str(result.run_dir),
                "failure_reason": result.failure_reason,
            }
            for result in results
        ],
    }
    if dependency_report is not None:
        manifest["dependency_status"] = dict(dependency_report)
    if parser_provenance is not None:
        manifest["parser_provenance"] = dict(parser_provenance)
    manifest["plotting"] = _plots.status()
    if extra:
        manifest.update(dict(extra))
    workflow.write_json_atomically(parent / "sweep_manifest.json", manifest)
    workflow.write_json_atomically(parent / "run_manifest.json", manifest)
    return manifest


def write_validation_report(
    parent: Path,
    *,
    cfg: Mapping[str, Any],
    manifest: Mapping[str, Any],
    registry_record: Mapping[str, Any] | None,
    dependency_report: Mapping[str, Any] | None,
    criteria: Sequence[tuple[str, bool | None, str]],
    notes: Sequence[str] = (),
    unvalidated_syntax: Sequence[str] = (),
) -> Path:
    """Write the human-readable ``validation_report.md``.

    ``criteria`` entries are ``(name, passed_or_None, explanation)``; ``None``
    means "not evaluated on this machine", which is reported as such and never
    as a pass.

    A plotting criterion is appended automatically. Figures degrade to a
    recorded skip when matplotlib is unavailable so a broken installation cannot
    abort a licensed run, and this is where that shows up as an explicit FAIL
    rather than as a quietly missing file.
    """

    plotting = _plots.status()
    criteria = list(criteria)
    if not plotting["available"]:
        criteria.append(
            (
                "all requested figures were produced",
                False,
                f"plotting is unavailable in this interpreter "
                f"({plotting['unavailable_reason']}); "
                f"{plotting['skipped_figure_count']} figure(s) were skipped. "
                "Numerical results are unaffected.",
            )
        )
    elif plotting["skipped_figure_count"]:
        criteria.append(
            (
                "all requested figures were produced",
                False,
                f"{plotting['skipped_figure_count']} figure(s) were skipped.",
            )
        )

    lines: list[str] = [
        f"# Validation report — {cfg.get('demo_id')}",
        "",
        f"- Title: {cfg.get('title')}",
        f"- Run status: `{manifest.get('status')}`",
        f"- Cases: {manifest.get('case_count')} "
        f"(completed {manifest.get('solver_success_count')}, "
        f"skipped {manifest.get('skipped_count')}, "
        f"failed {manifest.get('failed_count')}, "
        f"suspicious {manifest.get('suspicious_count')})",
        f"- Git commit: `{manifest.get('git_commit')}`"
        + (" (working tree dirty)" if manifest.get("git_dirty") else ""),
        "",
    ]
    if registry_record is not None:
        lines += [
            "## Declared validation status",
            "",
            f"- Registry status: `{registry_record.get('status')}`",
            f"- Home syntax check: {registry_record.get('home_syntax_check')}",
            f"- Home solver check: {registry_record.get('home_solver_check')}",
            f"- Physically validated: **{registry_record.get('physically_validated')}**",
            "",
        ]
        pending = registry_record.get("pending_licensed_checks") or []
        if pending:
            lines.append("Pending licensed checks:")
            lines.append("")
            lines += [f"- {item}" for item in pending]
            lines.append("")
    if dependency_report is not None:
        lines += ["## Dependencies", ""]
        for name, status in (dependency_report.get("depends_on") or {}).items():
            lines.append(f"- `{name}`: `{status}`")
        lines += ["", dependency_report.get("interpretation", ""), ""]
    lines += ["## Criteria", "", "| criterion | result | notes |", "|---|---|---|"]
    for name, passed, explanation in criteria:
        if passed is None:
            verdict = "not evaluated"
        else:
            verdict = "PASS" if passed else "FAIL"
        lines.append(f"| {name} | {verdict} | {explanation} |")
    lines.append("")
    if unvalidated_syntax:
        lines += [
            "## Input syntax still unvalidated",
            "",
            "These constructs have been accepted by a nextnano++ parser but their "
            "*output* has never been seen by this repository. Confirm them on the "
            "licensed laptop before trusting any number that depends on them.",
            "",
        ]
        lines += [f"- {item}" for item in unvalidated_syntax]
        lines.append("")
    if notes:
        lines += ["## Notes", ""]
        lines += [f"- {note}" for note in notes]
        lines.append("")
    path = parent / "validation_report.md"
    workflow.write_text_atomically(path, "\n".join(lines) + "\n")
    return path


def write_convergence_summary(
    parent: Path, *, title: str, rows: Sequence[Mapping[str, Any]], commentary: Sequence[str]
) -> Path:
    """Write ``convergence_summary.md`` for demos with refinement reruns."""

    lines = [f"# {title}", ""]
    if rows:
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(str(key))
        lines.append("| " + " | ".join(fieldnames) + " |")
        lines.append("|" + "---|" * len(fieldnames))
        for row in rows:
            cells = []
            for key in fieldnames:
                value = row.get(key)
                if isinstance(value, float) and math.isfinite(value):
                    cells.append(f"{value:.8g}")
                else:
                    cells.append("—" if value is None else str(value))
            lines.append("| " + " | ".join(cells) + " |")
    else:
        lines.append("_No convergence data: no licensed solver ran on this machine._")
    lines += ["", "## Interpretation", ""]
    lines += [f"- {item}" for item in commentary] or ["- None."]
    path = parent / "convergence_summary.md"
    workflow.write_text_atomically(path, "\n".join(lines) + "\n")
    return path


def collect_console_logs(parent: Path, results: Iterable[CaseResult]) -> None:
    """Gather every case's console log under ``console_logs/`` for quick review."""

    target = parent / "console_logs"
    target.mkdir(parents=True, exist_ok=True)
    for result in results:
        source = result.run_dir / "console.log"
        if source.is_file():
            workflow.write_text_atomically(
                target / f"{result.spec.case_id}.log",
                source.read_text(encoding="utf-8", errors="replace"),
            )
