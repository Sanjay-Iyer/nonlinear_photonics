"""Per-case orchestration: workspace, solve, discover, parse, QC, optics.

Built for debugging on a machine this code has never run on. Every case gets its
own ``logs/ input/ raw/ parsed/ plots/``, keeps ``solver_stdout.log``,
``solver_stderr.log``, ``command.txt``, ``resolved_config.yaml`` and
``provenance.json``, and records what it *expected* to find next to what it
*actually* found. A failure is written down with its traceback and the run
continues; nothing is swallowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import traceback
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import yaml

DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
for _relative in (
    "_shared",
    "11_paper_validation_interband_chi2_acqw",
    "14_absolute_chi2_graded_acqw_bo",
    "16_acqw_renderer_stress_validation",
    "16B_simple_acqw_grading_validation",
    "16E_acqw_structure_physics_optical_comparison",
    "16F_paper_absolute_chi2_reproduction_audit",
):
    _path = str(DEMOS / _relative)
    if _path not in sys.path:
        sys.path.insert(0, _path)
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

import cases16g  # noqa: E402
import deck16g  # noqa: E402
import grading16g  # noqa: E402
import nnp16g  # noqa: E402
import optics16g  # noqa: E402

DEMO_ID = cases16g.load_config.__module__  # placeholder replaced below
DEMO_ID = "16G_paper_nnp_and_structure_sweep_comparison"
DEMO_VERSION = "demo16g-1.0.0"

#: Output artifacts every solved case is expected to produce. Recorded as
#: *expected* and compared against what the raw tree actually contains, because
#: "the solver returned 0" and "the outputs I need exist" are different claims.
EXPECTED_OUTPUT_PATTERNS = (
    "**/*energy_spectrum*",
    "**/*probabilities*",
    "**/*envelope*",
    "**/*bandedge*",
    "**/*alloy*",
)


class Demo16GError(RuntimeError):
    """A Demo 16G step that failed in a way worth naming."""


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class CaseLog:
    """Console + file logging for one case. Verbose prints everything."""

    def __init__(self, path: Path, *, verbose: bool = False, echo: bool = True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.verbose = bool(verbose)
        self.echo = bool(echo)
        self._lines: list[str] = []

    def __call__(self, message: str, *, always: bool = False) -> None:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        self._lines.append(line)
        if self.echo and (self.verbose or always):
            print(f"      {message}")

    def field(self, name: str, value: Any) -> None:
        self(f"{name:<28} {value}")

    def flush(self) -> None:
        self.path.write_text("\n".join(self._lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


@dataclass
class Workspace:
    """One case's directory tree. Created up front so a failure still has a home."""

    root: Path
    logs: Path
    input: Path
    raw: Path
    parsed: Path
    plots: Path

    @classmethod
    def create(cls, run_root: Path, group: str, case_id: str) -> "Workspace":
        root = Path(run_root) / "cases" / group / case_id
        spaces = {
            name: root / name
            for name in ("logs", "input", "raw", "parsed", "plots")
        }
        for path in spaces.values():
            path.mkdir(parents=True, exist_ok=True)
        return cls(root=root, **spaces)

    def as_record(self) -> dict[str, str]:
        return {
            "case_dir": str(self.root), "logs": str(self.logs),
            "input": str(self.input), "raw": str(self.raw),
            "parsed": str(self.parsed), "plots": str(self.plots),
        }


def write_json(path: Path, payload: Any) -> Path:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(payload, indent=1, default=str), encoding="utf-8"
    )
    return Path(path)


# ---------------------------------------------------------------------------
# Machine
# ---------------------------------------------------------------------------


def resolve_machine(require_solver: bool = True) -> Any:
    """The authoritative machine configuration. Never invents one."""

    import demo_workflow as workflow

    machine = workflow.load_machine_config()
    if machine is None:
        raise Demo16GError(
            "no machine configuration found. Set NEXTNANO_MACHINE_CONFIG to the "
            "licensed configuration, e.g. "
            "nextnano/config/machines/nextnano_machine.work.yaml"
        )
    if require_solver and not getattr(machine, "run_solver", False):
        raise Demo16GError(
            "the selected machine configuration is not enabled for licensed "
            f"solves (run_solver is false): {getattr(machine, 'source_path', '?')}"
        )
    return machine


def machine_record(machine: Any) -> dict[str, Any]:
    return {
        "machine_config_source": str(getattr(machine, "source_path", "")) or None,
        "solver_executable": str(getattr(machine, "executable", "")) or None,
        "database": str(getattr(machine, "database", "")) or None,
        "license": str(getattr(machine, "license", "")) or None,
        "results_root": str(getattr(machine, "results_root", "")) or None,
        "run_solver": bool(getattr(machine, "run_solver", False)),
    }


def solver_command(
    machine: Any, deck: Path, output_dir: Path, threads: int = 1
) -> list[str]:
    """The licensed invocation, built by the same helper Demo 16E/16F use."""

    import solver14

    return solver14.real_argv(
        executable=Path(machine.executable),
        database=Path(machine.database) if getattr(machine, "database", None) else None,
        license_path=Path(machine.license) if getattr(machine, "license", None) else None,
        deck=Path(deck),
        output_dir=Path(output_dir),
        threads=int(threads),
    )


# ---------------------------------------------------------------------------
# Solve
# ---------------------------------------------------------------------------


def run_solver(
    command: Sequence[str], workspace: Workspace, log: CaseLog, *,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Invoke nextnano++ and keep everything it said."""

    stdout_path = workspace.logs / "solver_stdout.log"
    stderr_path = workspace.logs / "solver_stderr.log"
    (workspace.logs / "command.txt").write_text(
        subprocess.list2cmdline(list(command)) + "\n", encoding="utf-8"
    )
    log.field("solver command", subprocess.list2cmdline(list(command)))
    started = dt.datetime.now(dt.timezone.utc)
    try:
        completed = subprocess.run(
            list(command), capture_output=True, text=True,
            timeout=int(timeout_seconds), check=False,
        )
        stdout, stderr, code, timed_out = (
            completed.stdout, completed.stderr, completed.returncode, False
        )
    except subprocess.TimeoutExpired as expired:
        stdout = expired.stdout or ""
        stderr = (expired.stderr or "") + f"\nTIMEOUT after {timeout_seconds}s\n"
        code, timed_out = None, True
    finished = dt.datetime.now(dt.timezone.utc)
    stdout_path.write_text(stdout or "", encoding="utf-8")
    stderr_path.write_text(stderr or "", encoding="utf-8")
    log.field("solver return code", code)
    log.field("solver elapsed s", (finished - started).total_seconds())
    log.field("stdout log", stdout_path)
    log.field("stderr log", stderr_path)
    return {
        "command": list(command),
        "return_code": code,
        "timed_out": timed_out,
        "elapsed_seconds": (finished - started).total_seconds(),
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "succeeded": bool(code == 0 and not timed_out),
    }


def discover_outputs(raw: Path, log: CaseLog) -> dict[str, Any]:
    """What the raw tree actually contains, against what was expected."""

    raw = Path(raw)
    found: dict[str, list[str]] = {}
    for pattern in EXPECTED_OUTPUT_PATTERNS:
        matches = sorted(str(p.relative_to(raw)) for p in raw.glob(pattern)
                         if p.is_file())
        found[pattern] = matches
        log.field(f"found {pattern}", f"{len(matches)} file(s)")
    everything = sorted(str(p.relative_to(raw)) for p in raw.rglob("*") if p.is_file())
    log.field("total output files", len(everything))
    return {
        "raw_dir": str(raw),
        "expected_patterns": list(EXPECTED_OUTPUT_PATTERNS),
        "matches_by_pattern": found,
        "all_files": everything,
        "file_count": len(everything),
        "patterns_with_no_match": [p for p, m in found.items() if not m],
    }


# ---------------------------------------------------------------------------
# Parse + analyse
# ---------------------------------------------------------------------------


def analyse_states(
    cfg: Mapping[str, Any], workspace: Workspace, log: CaseLog,
    *, geometry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Route the raw output through Demo 11's analysis, then Demo 16F's evaluator.

    Demo 11's ``analyse_case`` is what writes ``envelopes.csv`` and
    ``quasi_bound_states.json`` into ``parsed/``, and it is the same routine
    Demos 12-16F use, so every group's states are extracted identically.
    """

    import adapter14
    import demo11
    import demo14

    demo14_cfg = demo14.load_config()
    demo11_cfg = adapter14.build_demo11_analysis_config_from_demo14(
        demo14_cfg, geometry["geometry"], geometry["profile"]
    ) if geometry else None
    if demo11_cfg is None:
        raise Demo16GError(
            "state analysis needs a Demo 14 geometry/profile pair to build the "
            "Demo 11 analysis config; none was supplied for this case"
        )
    log.field("analysis config", "adapter14.build_demo11_analysis_config_from_demo14")
    observables, validation = demo11.analyse_case(
        demo11_cfg, workspace.raw, workspace.parsed, workspace.plots
    )
    log.field("parsed E states", observables.get("number_of_electron_states"))
    log.field("physical_qc_valid", validation.get("passed"))
    return {
        "observables": dict(observables),
        "validation": dict(validation),
        "physical_qc_valid": bool(validation.get("passed", False)),
    }


def optical_from_parsed(
    cfg: Mapping[str, Any], workspace: Workspace, observables: Mapping[str, Any],
    log: CaseLog,
) -> dict[str, Any]:
    """Feed solved envelopes into the single shared chi2 evaluator."""

    states, diagnostics = optics16g.state_set_from_parsed(
        workspace.parsed,
        electron_energies_eV=observables["electron_energies_eV"],
        hole_energies_eV=observables["heavy_hole_energies_eV"],
        r_e_hh_nm=float(cfg["optics"]["r_e_hh_nm"]),
    )
    elements = optics16g.matrix_element_record(states)
    log.field("E1 / E2 (eV)", f"{elements['E1_eV']:.6f} / {elements['E2_eV']:.6f}")
    log.field("HH1 / HH2 (eV)", f"{elements['HH1_eV']:.6f} / {elements['HH2_eV']:.6f}")
    log.field("E1-HH1 (eV)", f"{elements['E1_minus_HH1_eV']:.6f}")
    log.field("E2-HH2 (eV)", f"{elements['E2_minus_HH2_eV']:.6f}")
    optical = optics16g.evaluate_all_methods(states, cfg)
    log.field("chi2(1550) pm/V", f"{optical['chi2_1550_pm_per_V']:.4f}")
    log.field("peak chi2 pm/V", f"{optical['peak_chi2_pm_per_V']:.4f}")
    log.field("peak wavelength nm", f"{optical['peak_wavelength_nm']:.2f}")
    log.field("detuning nm", f"{optical['detuning_nm']:+.2f}")
    gate = optics16g.bound_state_gate(workspace.parsed)
    log.field("bound-state gate", f"{gate.get('passed')} -- {gate.get('reason')}")

    spectra = {
        name: {
            "wavelength_nm": result.wavelength_nm.tolist(),
            "magnitude_pm_per_V": result.magnitude_pm_per_V.tolist(),
        }
        for name, result in optical["results"].items()
    }
    write_json(workspace.parsed / "chi2_spectra.json", {
        "tensor": cfg["optics"]["tensor"],
        "units": "pm/V",
        "scale_factor_applied": None,
        "spectra": spectra,
    })
    primary = optical["results"][optical["primary_method"]]
    np.savetxt(
        workspace.parsed / "chi2_spectrum.csv",
        np.column_stack([primary.wavelength_nm, primary.magnitude_pm_per_V]),
        delimiter=",", header="wavelength_nm,chi2_magnitude_pm_per_V", comments="",
    )
    return {
        "state_diagnostics": diagnostics,
        "matrix_elements": elements,
        "optical": {k: v for k, v in optical.items() if k != "results"},
        "bound_state_gate": gate,
        "spectrum_csv": str(workspace.parsed / "chi2_spectrum.csv"),
        "_spectrum": (primary.wavelength_nm, primary.magnitude_pm_per_V),
    }


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def write_case_provenance(
    workspace: Workspace, cfg: Mapping[str, Any], payload: Mapping[str, Any]
) -> None:
    (workspace.root / "resolved_config.yaml").write_text(
        yaml.safe_dump(
            {k: v for k, v in cfg.items() if not str(k).startswith("_")},
            sort_keys=False, default_flow_style=False,
        ),
        encoding="utf-8",
    )
    write_json(workspace.root / "provenance.json", {
        "demo_id": DEMO_ID,
        "demo16g_version": DEMO_VERSION,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config_path": cfg.get("_config_path"),
        "scale_factor_applied": None,
        **{k: v for k, v in payload.items() if not str(k).startswith("_")},
    })


def failure_record(exc: BaseException, stage: str) -> dict[str, Any]:
    """A failure, written down in full. Never swallowed, never re-raised blindly."""

    return {
        "passed": False,
        "failure_stage": stage,
        "failure_type": type(exc).__name__,
        "failure_reason": str(exc),
        "traceback": traceback.format_exc(),
    }
