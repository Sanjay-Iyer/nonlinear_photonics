"""Demo 14 solver invocation: real nextnano++ with a timeout, and a mock.

The shared ``demo_workflow._execute_solver`` drives nextnano++ through
``nextnanopy`` and has **no timeout** -- fine for Demo 11-13, where a human was
watching, but not for an unattended 30-trial campaign where one hung process
would stall the run indefinitely and leave an orphan behind. This module wraps
it with a finite, configurable timeout and kills the whole process tree on
expiry.

It also provides a deterministic **mock** solver. The home laptop's free
nextnano++ cannot execute a production structure (100 grid points) or an
imported alloy profile at all, so the mock is the only way to exercise the
orchestration end to end before the work laptop sees it. Mock output is marked
at every level that a reader or a program might look -- run directory name,
manifest, status file, and each trial record -- because a mock number that got
mistaken for physics would be worse than no test at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping

import numpy as np

MOCK_MARKER = "DEMO14_MOCK_RESULT_NOT_SCIENTIFIC"

#: nextnano++ prints one of these and stops. Matched case-insensitively against
#: stdout, mirroring Demo 11's own ``validation.fatal_markers``.
FATAL_STDOUT_MARKERS = (
    "terminating program",
    "fatal error",
    "validation error",
    "license expired",
)


class SolverTimeout(RuntimeError):
    """The solver exceeded its configured wall-clock budget."""

    def __init__(self, message: str, invocation: "SolverInvocation | None" = None):
        super().__init__(message)
        self.invocation = invocation


class SolverTechnicalFailure(RuntimeError):
    """Infrastructure failed, as distinct from the physics being unfavourable."""

    def __init__(self, message: str, invocation: "SolverInvocation | None" = None):
        super().__init__(message)
        self.invocation = invocation


@dataclass
class SolverInvocation:
    """Everything needed to reproduce or audit one solver call."""

    executable: str | None
    argv: list[str]
    working_directory: str
    input_path: str
    input_sha256: str | None
    imported_files: list[dict[str, Any]] = field(default_factory=list)
    started_utc: str | None = None
    finished_utc: str | None = None
    elapsed_seconds: float | None = None
    return_code: int | None = None
    timed_out: bool = False
    timeout_seconds: float | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    mode: str = "real"

    def as_record(self) -> dict[str, Any]:
        return {
            "solver_executable": self.executable,
            "solver_argv": list(self.argv),
            "working_directory": self.working_directory,
            "input_path": self.input_path,
            "input_sha256": self.input_sha256,
            "imported_files": list(self.imported_files),
            "solver_started_utc": self.started_utc,
            "solver_finished_utc": self.finished_utc,
            "solver_elapsed_seconds": self.elapsed_seconds,
            "solver_return_code": self.return_code,
            "solver_timed_out": self.timed_out,
            "solver_timeout_seconds": self.timeout_seconds,
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "solver_mode": self.mode,
        }


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception:
        return None


def real_argv(
    *, executable: Path, database: Path | None, license_path: Path | None,
    deck: Path, output_dir: Path, threads: int = 1,
) -> list[str]:
    """The authoritative full-solver command, shared by execution/reporting."""

    argv = [str(executable)]
    if database is not None:
        argv += ["-d", str(database)]
    if license_path is not None:
        argv += ["-l", str(license_path)]
    argv += ["--threads", str(int(threads)), "-o", str(output_dir), str(deck)]
    return argv


def _terminate_tree(process: subprocess.Popen) -> None:
    """Kill the solver and its children; nextnano++ spawns workers.

    ``taskkill /T`` is the only reliable way to reach the whole tree on Windows;
    the POSIX path is kept so the module stays testable on any platform.
    """

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True, timeout=30, check=False,
            )
        else:  # pragma: no cover - repo is Windows-first
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    except Exception:  # pragma: no cover
        pass
    finally:
        try:
            process.wait(timeout=10)
        except Exception:  # pragma: no cover
            pass


def execute_real(
    *,
    executable: Path,
    database: Path | None,
    license_path: Path | None,
    deck: Path,
    output_dir: Path,
    threads: int = 1,
    timeout_seconds: float = 3600.0,
    imported_files: Mapping[str, Path] | None = None,
    logs_dir: Path | None = None,
) -> SolverInvocation:
    """Run nextnano++ directly, with stdout/stderr split and a finite timeout.

    Invoked without ``shell=True`` and with an explicit working directory, so a
    path containing a space or an ampersand cannot change what is executed.
    """

    from runlog14 import utc_now

    deck = Path(deck)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logs = Path(logs_dir) if logs_dir else deck.parent
    logs.mkdir(parents=True, exist_ok=True)

    argv = real_argv(
        executable=executable, database=database, license_path=license_path,
        deck=deck, output_dir=output_dir, threads=threads,
    )

    invocation = SolverInvocation(
        executable=str(executable),
        argv=argv,
        working_directory=str(deck.parent),
        input_path=str(deck),
        input_sha256=_sha256(deck),
        imported_files=[
            {"name": name, "path": str(path), "sha256": _sha256(Path(path))}
            for name, path in sorted((imported_files or {}).items())
        ],
        timeout_seconds=float(timeout_seconds),
        stdout_path=str(logs / "stdout.txt"),
        stderr_path=str(logs / "stderr.txt"),
        mode="real",
    )

    started = time.perf_counter()
    invocation.started_utc = utc_now()
    process = subprocess.Popen(
        argv, cwd=str(deck.parent), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    try:
        out, err = process.communicate(timeout=float(timeout_seconds))
        invocation.return_code = int(process.returncode)
    except subprocess.TimeoutExpired:
        _terminate_tree(process)
        out, err = "", f"TIMEOUT after {timeout_seconds} s; process tree terminated.\n"
        invocation.timed_out = True
        invocation.return_code = None
    finally:
        invocation.elapsed_seconds = time.perf_counter() - started
        invocation.finished_utc = utc_now()
        # Written even on timeout: partial solver output is often the only clue.
        Path(invocation.stdout_path).write_text(out or "", encoding="utf-8", newline="\n")
        Path(invocation.stderr_path).write_text(err or "", encoding="utf-8", newline="\n")

    if invocation.timed_out:
        raise SolverTimeout(
            f"nextnano++ exceeded {timeout_seconds} s and was terminated. Partial "
            f"output preserved under {output_dir}.", invocation,
        )
    if invocation.return_code != 0:
        # Previously this returned normally and analysis ran on the wreckage of a
        # failed solve, so a solver failure surfaced later as an unrelated parser
        # error. The exit code is the solver's own verdict and is believed here.
        raise SolverTechnicalFailure(
            f"nextnano++ exited with code {invocation.return_code}. "
            f"stdout: {invocation.stdout_path}  stderr: {invocation.stderr_path}. "
            f"Raw output preserved under {output_dir}.", invocation,
        )

    # The exit code is not the only verdict. nextnano++ prints an explicit fatal
    # marker before it stops, and a validation error can leave a zero-length
    # output tree behind -- which is exactly what the first licensed gate
    # produced. Both are checked so a refused deck can never be mistaken for a
    # completed calculation.
    lowered = (out or "").lower()
    for marker in FATAL_STDOUT_MARKERS:
        if marker in lowered:
            raise SolverTechnicalFailure(
                f"nextnano++ reported '{marker}' and did not complete. See "
                f"{invocation.stdout_path}. Raw output under {output_dir}.", invocation,
            )
    produced = [p for p in Path(output_dir).rglob("*") if p.is_file()]
    if not produced:
        raise SolverTechnicalFailure(
            f"nextnano++ exited 0 but wrote no output files under {output_dir}. "
            f"See {invocation.stdout_path}.", invocation,
        )
    return invocation


# ---------------------------------------------------------------------------
# Mock solver
# ---------------------------------------------------------------------------

#: Behaviours the mock can be asked to produce, so the harness's failure paths
#: are exercised rather than assumed.
MOCK_BEHAVIOURS = (
    "success",
    "qc_failure",
    "nonzero_exit",
    "missing_output",
    "parser_failure",
    "timeout",
    "nan_objective",
)


@dataclass
class MockOutcome:
    """A deterministic stand-in for one parsed, analysed trial."""

    behaviour: str
    chi2_abs_at_target_pm_per_V: float | None
    peak_chi2_pm_per_V: float | None
    peak_wavelength_nm: float | None
    maximum_boundary_probability: float
    state_tracking_confidence: float
    orthonormality_error: float
    record: dict[str, Any] = field(default_factory=dict)


def _stable_unit(seed_text: str) -> float:
    """Deterministic [0, 1) from a string, so mock runs replay identically."""

    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(1 << 64)


def choose_behaviour(trial_id: str, plan: Mapping[str, str] | None) -> str:
    if plan and trial_id in plan:
        return plan[trial_id]
    return "success"


def execute_mock(
    *,
    trial_id: str,
    parameters: Mapping[str, Any],
    deck: Path,
    output_dir: Path,
    logs_dir: Path,
    behaviour: str = "success",
    target_wavelength_nm: float = 1550.0,
    imported_files: Mapping[str, Path] | None = None,
) -> tuple[SolverInvocation, MockOutcome]:
    """Produce a deterministic fake solver result and its artifacts.

    The physics is a smooth surrogate, not a simulation: a Lorentzian whose
    centre and height depend on the geometry so that the optimizer has a real
    surface to climb and the convergence plot is meaningful. It is **not** a
    prediction of anything, which is why every artifact it touches carries
    :data:`MOCK_MARKER`.
    """

    from runlog14 import utc_now, write_text_atomic

    if behaviour not in MOCK_BEHAVIOURS:
        raise ValueError(f"unknown mock behaviour {behaviour!r}; expected {MOCK_BEHAVIOURS}")

    output_dir = Path(output_dir)
    logs_dir = Path(logs_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    invocation = SolverInvocation(
        executable="<mock>",
        argv=["<mock>", str(deck)],
        working_directory=str(Path(deck).parent),
        input_path=str(deck),
        input_sha256=_sha256(Path(deck)),
        imported_files=[
            {"name": n, "path": str(p), "sha256": _sha256(Path(p))}
            for n, p in sorted((imported_files or {}).items())
        ],
        started_utc=utc_now(),
        timeout_seconds=None,
        stdout_path=str(logs_dir / "stdout.txt"),
        stderr_path=str(logs_dir / "stderr.txt"),
        mode="mock",
    )

    if behaviour == "timeout":
        invocation.timed_out = True
        invocation.finished_utc = utc_now()
        invocation.elapsed_seconds = 0.0
        write_text_atomic(Path(invocation.stdout_path), f"{MOCK_MARKER}\npartial output\n")
        write_text_atomic(Path(invocation.stderr_path), f"{MOCK_MARKER}\nmock timeout\n")
        raise SolverTimeout(f"{MOCK_MARKER}: mock solver timeout for {trial_id}")

    if behaviour == "nonzero_exit":
        invocation.return_code = 3
        invocation.finished_utc = utc_now()
        invocation.elapsed_seconds = 0.0
        write_text_atomic(Path(invocation.stdout_path), f"{MOCK_MARKER}\n")
        write_text_atomic(
            Path(invocation.stderr_path), f"{MOCK_MARKER}\nmock solver failed (exit 3)\n"
        )
        raise SolverTechnicalFailure(f"{MOCK_MARKER}: mock solver exit code 3 for {trial_id}")

    invocation.return_code = 0
    invocation.finished_utc = utc_now()
    invocation.elapsed_seconds = 0.001
    write_text_atomic(
        Path(invocation.stdout_path),
        f"{MOCK_MARKER}\nmock solve for {trial_id}\nbehaviour={behaviour}\n",
    )
    write_text_atomic(Path(invocation.stderr_path), "")

    if behaviour == "missing_output":
        # Deliberately writes nothing the parser needs.
        raise SolverTechnicalFailure(
            f"{MOCK_MARKER}: expected output files absent for {trial_id}"
        )

    if behaviour == "parser_failure":
        write_text_atomic(output_dir / "energies.dat", "not a number at all\n")
        raise SolverTechnicalFailure(
            f"{MOCK_MARKER}: mock parser failure for {trial_id}"
        )

    # --- surrogate physics -------------------------------------------------
    s = float(parameters.get("asymmetry_s", 0.42))
    barrier = float(parameters.get("nominal_central_barrier_thickness_nm", 1.8))
    wl = float(parameters.get("gaas_to_algaas_grading_width_10_90_nm", 0.9))
    wr = float(parameters.get("algaas_to_gaas_grading_width_10_90_nm", 0.9))
    family = str(parameters.get("grading_profile", "erf"))

    # Peak wavelength drifts with asymmetry and barrier; grading pulls it down.
    peak_nm = 1450.0 + 320.0 * (s - 0.30) + 55.0 * (barrier - 0.85) - 30.0 * (wl + wr) / 2.0
    # Height peaks near a ~1 nm barrier, as the reference paper reports, and is
    # reduced by wide (interdiffused) interfaces.
    height = 2400.0 * math.exp(-((barrier - 1.05) ** 2) / 0.55) * math.exp(-0.35 * (wl + wr) / 2.0)
    height *= 1.0 + 0.12 * {"linear": 0.0, "fermi": 0.4, "erf": 1.0, "cosine": 0.6}[family]
    height *= 0.85 + 0.3 * _stable_unit(f"{trial_id}:{family}")

    if behaviour == "nan_objective":
        value = float("nan")
    else:
        gamma = 60.0
        value = height * gamma**2 / ((target_wavelength_nm - peak_nm) ** 2 + gamma**2)

    boundary = 3.0e-5 + 2.0e-3 * max(0.0, 0.95 - barrier)
    confidence = 0.62 if behaviour == "qc_failure" else 0.90 + 0.08 * _stable_unit(trial_id)

    write_text_atomic(
        output_dir / "mock_result.json",
        f'{{"{MOCK_MARKER}": true, "trial_id": "{trial_id}", "behaviour": "{behaviour}"}}\n',
    )

    return invocation, MockOutcome(
        behaviour=behaviour,
        chi2_abs_at_target_pm_per_V=value,
        peak_chi2_pm_per_V=height,
        peak_wavelength_nm=peak_nm,
        maximum_boundary_probability=boundary,
        state_tracking_confidence=min(confidence, 0.999),
        orthonormality_error=3.0e-7,
        record={
            MOCK_MARKER: True,
            "scientific_valid": False,
            "surrogate": "lorentzian; not a simulation",
        },
    )
