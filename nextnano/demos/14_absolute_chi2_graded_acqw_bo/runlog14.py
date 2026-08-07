"""Demo 14 run directory, logging, manifest and status.

A licensed 30-trial campaign runs unattended for hours and its failures have to
be diagnosable weeks later on a different machine from a zip file. That rules
out console output as the primary record, so everything here writes to disk:
six log streams, a structured event journal, an atomically-updated status file,
and a manifest that names every input that shaped the science.

Two invariants this module exists to enforce:

* **A new run never resumes an old one.** Each campaign gets a fresh, uniquely
  named directory; resuming is possible only by naming a directory explicitly.
  Demo 13 lost sixteen licensed trials to a run that wrote where it should not
  have, and the fix there was a guard rather than a structure.
* **Nothing is lost to a crash.** Status and checkpoints are written temp-then-
  rename, so an interrupted write leaves the previous good file rather than a
  truncated one.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import datetime as _dt
import getpass
import hashlib
import json
import logging
import logging.handlers
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
import time
import traceback
from typing import Any, Iterator, Mapping
import uuid

import numpy as np
import yaml

DEMO_ID = "14_absolute_chi2_graded_acqw_bo"
DEMO14_VERSION = "demo14-1.0.0-beta"

#: Directories every run owns. Created up front so a failure at any stage still
#: lands in a predictable place.
RUN_SUBDIRS = (
    "environment",
    "logs",
    "optimization",
    "optimization/checkpoints",
    "trials",
    "plots",
    "summaries",
    "validation",
    "debug_bundle",
)

#: Environment variables that may be recorded verbatim. Everything else is
#: reported as present-but-redacted: an allowlist cannot be defeated by a
#: variable named in a way a denylist did not anticipate.
_ENV_ALLOWLIST = (
    "CONDA_DEFAULT_ENV", "CONDA_PREFIX", "COMPUTERNAME", "NUMBER_OF_PROCESSORS",
    "OS", "PROCESSOR_ARCHITECTURE", "PYTHONHASHSEED", "PYTHONIOENCODING",
    "USERDOMAIN", "VIRTUAL_ENV", "LANG", "LC_ALL", "TZ", "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
)
_SECRET_HINT = re.compile(
    r"(key|token|secret|password|passwd|credential|licence|license|auth|api)", re.I
)


class Runlog14Error(RuntimeError):
    """A run-infrastructure failure, distinct from a physics failure."""


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _run_command(args: list[str], cwd: Path | None = None) -> str:
    """Best-effort text capture; never raises, so provenance cannot break a run."""

    try:
        completed = subprocess.run(
            args, cwd=str(cwd) if cwd else None, capture_output=True,
            text=True, timeout=30, check=False,
        )
        return (completed.stdout or "") + (completed.stderr or "")
    except Exception as exc:  # pragma: no cover - provenance is never fatal
        return f"<unavailable: {type(exc).__name__}: {exc}>"


def git_facts(repo_root: Path) -> dict[str, Any]:
    branch = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root).strip()
    commit = _run_command(["git", "rev-parse", "HEAD"], repo_root).strip()
    status = _run_command(["git", "status", "--porcelain"], repo_root)
    dirty_lines = [ln for ln in status.splitlines() if ln.strip() and "warning:" not in ln]
    diff = _run_command(["git", "diff", "HEAD"], repo_root)
    return {
        "git_branch": branch or None,
        "git_commit": commit or None,
        "git_commit_short": (commit[:8] if commit else "nogit"),
        "git_dirty": bool(dirty_lines),
        "git_dirty_files": dirty_lines[:200],
        "git_diff_sha256": hashlib.sha256(diff.encode("utf-8", "replace")).hexdigest()
        if diff.strip() else None,
    }


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception:
        return None


def json_safe(value: Any) -> Any:
    """Make NumPy and non-finite floats safe for strict JSON.

    ``json.dump`` writes bare ``NaN``/``Infinity`` by default, which is invalid
    JSON that many parsers -- including some the debug bundle will meet -- reject
    outright. Turning them into ``None`` with the fact recorded elsewhere keeps
    the record loadable.
    """

    if isinstance(value, Mapping):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, complex):
        return {"real": json_safe(value.real), "imag": json_safe(value.imag)}
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return value
    if isinstance(value, Path):
        return str(value)
    return value


def write_json_atomic(path: Path, payload: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"~{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    temporary.write_text(
        json.dumps(json_safe(payload), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8", newline="\n",
    )
    os.replace(temporary, path)
    return path


def write_text_atomic(path: Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"~{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    return path


# ---------------------------------------------------------------------------


@dataclass
class RunPaths:
    root: Path

    def __getattr__(self, name: str) -> Path:
        if name in {d.replace("/", "_") for d in RUN_SUBDIRS}:
            return self.root / name.replace("_", "/", 1) if "_" in name else self.root / name
        raise AttributeError(name)

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def trials(self) -> Path:
        return self.root / "trials"

    @property
    def optimization(self) -> Path:
        return self.root / "optimization"

    @property
    def checkpoints(self) -> Path:
        return self.root / "optimization" / "checkpoints"

    @property
    def environment(self) -> Path:
        return self.root / "environment"

    @property
    def summaries(self) -> Path:
        return self.root / "summaries"

    @property
    def validation(self) -> Path:
        return self.root / "validation"

    @property
    def plots(self) -> Path:
        return self.root / "plots"

    @property
    def debug_bundle(self) -> Path:
        return self.root / "debug_bundle"

    @property
    def status_file(self) -> Path:
        return self.root / "RUN_STATUS.json"

    @property
    def manifest_file(self) -> Path:
        return self.root / "manifest.json"

    @property
    def events_file(self) -> Path:
        return self.logs / "events.jsonl"

    @property
    def timing_file(self) -> Path:
        return self.logs / "timing.jsonl"


def new_run_directory(
    results_root: Path, *, git_short_sha: str, mock: bool, run_id: str | None = None
) -> tuple[Path, str]:
    """Create a fresh, uniquely-named campaign directory.

    A mock run is named so it cannot be mistaken for science at a glance, in a
    directory listing, or in a bundle filename.
    """

    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    identifier = run_id or uuid.uuid4().hex[:6]
    prefix = "demo14MOCK" if mock else "demo14"
    root = Path(results_root) / DEMO_ID / f"{prefix}_{stamp}_{git_short_sha}_{identifier}"
    if root.exists():
        raise Runlog14Error(f"run directory already exists, refusing to reuse: {root}")
    for sub in RUN_SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, identifier


# ---------------------------------------------------------------------------


class EventLog:
    """Append-only structured journal (``logs/events.jsonl``)."""

    def __init__(self, path: Path, run_id: str) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8", newline="\n")

    def emit(
        self, event_type: str, *, stage: str = "", status: str = "",
        message: str = "", trial_id: str | None = None, **metadata: Any,
    ) -> dict[str, Any]:
        record = json_safe({
            "timestamp": utc_now(),
            "run_id": self.run_id,
            "event_type": event_type,
            "trial_id": trial_id,
            "stage": stage,
            "status": status,
            "message": message,
            **metadata,
        })
        self._handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        # Flushed on every event: an unflushed journal is worthless after a crash,
        # which is the case it exists for.
        self._handle.flush()
        os.fsync(self._handle.fileno())
        return record

    def close(self) -> None:
        try:
            self._handle.close()
        except Exception:  # pragma: no cover
            pass


class TimingLog:
    """Per-stage wall-clock journal (``logs/timing.jsonl``)."""

    def __init__(self, path: Path, run_id: str) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.rows: list[dict[str, Any]] = []

    @contextmanager
    def stage(self, name: str, trial_id: str | None = None) -> Iterator[dict[str, Any]]:
        started = time.perf_counter()
        holder: dict[str, Any] = {"stage": name, "trial_id": trial_id}
        try:
            yield holder
        finally:
            holder["elapsed_seconds"] = time.perf_counter() - started
            holder["run_id"] = self.run_id
            holder["timestamp"] = utc_now()
            self.rows.append(holder)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(json_safe(holder), sort_keys=True, allow_nan=False) + "\n")

    def summary_rows(self) -> list[dict[str, Any]]:
        return list(self.rows)


def configure_logging(paths: RunPaths, *, verbose: bool = False) -> logging.Logger:
    """Console plus four files. Handlers are replaced, never stacked."""

    logger = logging.getLogger("demo14")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console)

    detailed = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s %(module)s.%(funcName)s:%(lineno)d | %(message)s"
    )
    for filename, level, fmt in (
        ("run.log", logging.INFO, logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")),
        ("run_debug.log", logging.DEBUG, detailed),
        ("warnings.log", logging.WARNING, detailed),
        ("errors.log", logging.ERROR, detailed),
    ):
        handler = logging.FileHandler(paths.logs / filename, encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    # Route warnings.warn() into the same files rather than to stderr, where an
    # unattended run would lose them.
    logging.captureWarnings(True)
    py_warnings = logging.getLogger("py.warnings")
    py_warnings.handlers = [
        h for h in logger.handlers if isinstance(h, logging.FileHandler)
    ]
    py_warnings.setLevel(logging.WARNING)
    return logger


def flush_logging(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        try:
            handler.flush()
        except Exception:  # pragma: no cover
            pass


def close_logging(logger: logging.Logger) -> None:
    """Flush and release every file handler.

    Windows keeps an open file locked, so leaving handlers attached makes the
    run directory undeletable and leaks descriptors across repeated campaigns in
    one process. Always paired with :func:`configure_logging`.
    """

    flush_logging(logger)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # pragma: no cover
            pass
    py_warnings = logging.getLogger("py.warnings")
    py_warnings.handlers = []


# ---------------------------------------------------------------------------


@dataclass
class RunStatus:
    """``RUN_STATUS.json``: small, atomic, inspectable while the run is live."""

    path: Path
    run_id: str
    target_completed_trials: int
    status: str = "INITIALIZING"
    current_trial: str | None = None
    current_stage: str | None = None
    completed_trials: int = 0
    failed_trials: int = 0
    rejected_trials: int = 0
    technical_failures: int = 0
    current_best_trial: str | None = None
    current_best_objective_pm_per_V: float | None = None
    last_checkpoint: str | None = None
    last_error: str | None = None
    mock: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def update(self, **changes: Any) -> None:
        for key, value in changes.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra[key] = value
        self.write()

    def write(self) -> None:
        write_json_atomic(self.path, {
            "run_id": self.run_id,
            "status": self.status,
            "mock": self.mock,
            "scientific_valid": not self.mock,
            "current_trial": self.current_trial,
            "current_stage": self.current_stage,
            "completed_trials": self.completed_trials,
            "failed_trials": self.failed_trials,
            "rejected_trials": self.rejected_trials,
            "technical_failures": self.technical_failures,
            "target_completed_trials": self.target_completed_trials,
            "current_best_trial": self.current_best_trial,
            "current_best_objective_pm_per_V": self.current_best_objective_pm_per_V,
            "last_checkpoint": self.last_checkpoint,
            "last_error": self.last_error,
            "updated_utc": utc_now(),
            **self.extra,
        })


# ---------------------------------------------------------------------------


def package_versions() -> dict[str, str | None]:
    names = (
        "ax-platform", "botorch", "gpytorch", "torch", "numpy", "scipy",
        "pandas", "pyyaml", "matplotlib", "nextnanopy",
    )
    import importlib.metadata as md

    out: dict[str, str | None] = {}
    for name in names:
        try:
            out[name] = md.version(name)
        except Exception:
            out[name] = None
    return out


def redacted_environment() -> dict[str, str]:
    """Allowlisted variables verbatim; everything else acknowledged but hidden."""

    out: dict[str, str] = {}
    for key, value in sorted(os.environ.items()):
        if key in _ENV_ALLOWLIST and not _SECRET_HINT.search(key):
            out[key] = value
        else:
            out[key] = "<redacted>" if _SECRET_HINT.search(key) else "<not recorded>"
    return out


def write_environment_snapshot(
    paths: RunPaths, repo_root: Path, machine: Any | None = None
) -> None:
    env = paths.environment
    write_text_atomic(env / "python_version.txt", f"{sys.version}\n{sys.executable}\n")
    write_text_atomic(env / "pip_freeze.txt", _run_command([sys.executable, "-m", "pip", "freeze"]))
    write_text_atomic(env / "git_status.txt", _run_command(["git", "status"], repo_root))
    write_text_atomic(env / "git_log.txt", _run_command(["git", "log", "-25", "--oneline"], repo_root))
    write_text_atomic(env / "git_diff.patch", _run_command(["git", "diff", "HEAD"], repo_root))
    write_text_atomic(env / "system_info.txt", "\n".join([
        f"hostname: {socket.gethostname()}",
        f"platform: {platform.platform()}",
        f"machine: {platform.machine()}",
        f"processor: {platform.processor()}",
        f"python: {platform.python_version()}",
        f"cpu_count: {os.cpu_count()}",
        f"user: <redacted>" if getpass else "",
    ]) + "\n")
    write_text_atomic(env / "paths.txt", "\n".join([
        f"repo_root: {repo_root}", f"run_root: {paths.root}", f"cwd: {Path.cwd()}",
        "sys.path:", *[f"  {p}" for p in sys.path],
    ]) + "\n")
    exe = getattr(machine, "executable", None) if machine else None
    write_text_atomic(env / "nextnano_version.txt", "\n".join([
        f"executable: {exe}",
        f"database: {getattr(machine, 'database', None) if machine else None}",
        f"exists: {Path(exe).is_file() if exe else False}",
        f"run_solver: {getattr(machine, 'run_solver', None) if machine else None}",
        f"threads: {getattr(machine, 'threads', None) if machine else None}",
    ]) + "\n")
    write_json_atomic(env / "environment_variables_redacted.json", redacted_environment())
    write_json_atomic(env / "packages.json", package_versions())


def build_manifest(
    *, run_id: str, paths: RunPaths, cfg: Mapping[str, Any], repo_root: Path,
    config_path: Path, machine: Any | None, settings: Any, mock: bool,
    planned_initial: int, planned_bo: int, seed: int,
) -> dict[str, Any]:
    facts = git_facts(repo_root)
    optimization = dict(cfg.get("optimization") or {})
    constraints = dict(cfg.get("constraints") or {})
    return {
        "run_id": run_id,
        "experiment_name": str(cfg.get("experiment", {}).get("name", "demo14")),
        "demo_id": DEMO_ID,
        "demo14_version": DEMO14_VERSION,
        "absolute_chi2_model_version": getattr(
            __import__("chi2"), "EXTRACTION_VERSION", "demo14-absolute-1"
        ),
        "mode": "mock" if mock else "real",
        "scientific_valid": not mock,
        "start_timestamp_utc": utc_now(),
        "end_timestamp_utc": None,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "repository_path": str(repo_root),
        **facts,
        "packages": package_versions(),
        "random_seed": int(seed),
        "resolved_config_path": str(paths.root / "resolved_config.yaml"),
        "source_config_path": str(config_path),
        "resolved_config_sha256": None,
        "nextnano_executable": str(getattr(machine, "executable", None)) if machine else None,
        "nextnano_database": str(getattr(machine, "database", None)) if machine else None,
        "nextnano_run_solver": bool(getattr(machine, "run_solver", False)) if machine else False,
        "search_space": dict(cfg.get("optimization", {}).get("search_space", {})),
        "objective": optimization.get("objective"),
        "constraints": constraints,
        "target_wavelength_nm": cfg.get("chi2", {}).get("target_wavelength_nm"),
        "broadening_meV": cfg.get("chi2", {}).get("broadening_meV"),
        "mesh_nm": cfg.get("mesh", {}).get("active_region_grid_spacing_nm"),
        "r_e_hh_nm": getattr(settings, "r_e_hh_nm", None),
        "r_e_hh_provenance": __import__("physics14").R_E_HH_PROVENANCE,
        "n_wells_per_metre": getattr(settings, "n_wells_per_metre", None),
        "nz_mode": cfg.get("chi2", {}).get("nz_mode"),
        "spin_degeneracy": getattr(settings, "spin_degeneracy", None),
        "k_parallel": dict(cfg.get("k_parallel") or {}),
        "planned_initialization_trials": int(planned_initial),
        "planned_bo_trials": int(planned_bo),
        "planned_completed_trials": int(planned_initial + planned_bo),
        "actual_completed_trials": 0,
        "actual_failed_trials": 0,
        "actual_rejected_trials": 0,
        "final_best_trial": None,
        "final_best_objective_pm_per_V": None,
        "final_status": "INITIALIZING",
    }


def install_excepthook(
    logger: logging.Logger, events: EventLog, status: RunStatus, paths: RunPaths
) -> None:
    """Guarantee a traceback reaches disk even on an unhandled exception."""

    previous = sys.excepthook

    def handler(exc_type, exc, tb):  # pragma: no cover - exercised via subprocess
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            logger.error("UNHANDLED EXCEPTION\n%s", text)
            write_text_atomic(paths.logs / "unhandled_traceback.txt", text)
            events.emit(
                "RUN_FAILED", stage="unhandled", status="error",
                message=f"{exc_type.__name__}: {exc}", traceback=text,
            )
            status.update(status="FAILED", last_error=f"{exc_type.__name__}: {exc}")
            flush_logging(logger)
        finally:
            previous(exc_type, exc, tb)

    sys.excepthook = handler


def dump_resolved_config(paths: RunPaths, cfg: Mapping[str, Any]) -> str:
    """Write the resolved YAML and return its SHA256."""

    text = yaml.safe_dump(json_safe(dict(cfg)), sort_keys=True, allow_unicode=True)
    write_text_atomic(paths.root / "resolved_config.yaml", text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
