"""Layer 1 - configuration and path resolution for Demo 20.

One YAML file (``demo20_config.yaml``) is the only place Demo 20 reads settings
from. This module loads it, applies command-line overrides for the current
execution only, and resolves every path against the *repository root* so that
nothing depends on the current working directory, the machine, or a username.

Path convention follows Demo 19 and the rest of the repository: repo-relative
strings in YAML, absolute :class:`Path` objects in Python, and licensed-solver
locations resolved separately through ``demo_workflow.load_machine_config``
(see :mod:`s04_solver`) rather than being written down here.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

DEMO_DIR = Path(__file__).resolve().parent
DEMOS_DIR = DEMO_DIR.parent
NEXTNANO_DIR = DEMOS_DIR.parent
REPO_ROOT = NEXTNANO_DIR.parent
CONFIG_PATH = DEMO_DIR / "demo20_config.yaml"

#: (2*pi)^2. Written out rather than computed so the YAML value can be checked
#: against it; :func:`s06_chi2.two_pi_squared` is the computed authority.
TWO_PI_SQUARED_REFERENCE = 39.47841760435743


class Config20Error(ValueError):
    """The Demo 20 configuration is missing something or is self-inconsistent."""


@dataclass(frozen=True)
class Paths:
    """Every output location, all beneath one results root."""

    root: Path
    tables: Path
    plots: Path
    data: Path
    qc: Path
    logs: Path
    inputs: Path

    def mkdirs(self) -> "Paths":
        for path in (self.root, self.tables, self.plots, self.data, self.qc,
                     self.logs, self.inputs):
            path.mkdir(parents=True, exist_ok=True)
        return self


def repo_path(value: str | Path) -> Path:
    """Resolve a repo-relative configuration string to an absolute path."""

    path = Path(value)
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def load(config_path: Path | None = None) -> dict[str, Any]:
    """Read and validate ``demo20_config.yaml``."""

    source = Path(config_path) if config_path else CONFIG_PATH
    if not source.is_file():
        raise Config20Error(f"Demo 20 configuration not found: {source}")
    cfg = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(cfg, Mapping):
        raise Config20Error(f"{source}: top level must be a mapping.")
    cfg = copy.deepcopy(dict(cfg))
    cfg["_config_path"] = str(source)
    validate(cfg)
    return cfg


REQUIRED_SECTIONS = (
    "demo", "geometry", "materials", "mesh", "grading", "solver", "states",
    "chi2", "k_parallel", "qc", "analysis", "paper", "plots", "paths",
)


def validate(cfg: Mapping[str, Any]) -> None:
    """Fail with a named field rather than a KeyError three layers down."""

    missing = [name for name in REQUIRED_SECTIONS if name not in cfg]
    if missing:
        raise Config20Error("demo20_config.yaml is missing section(s): "
                            + ", ".join(missing))
    chi2 = cfg["chi2"]
    for field in ("apply_kspace_2pi_squared_scaling", "kspace_scaling_factor",
                  "r_e_hh_nm", "nz_mode", "reference_period_nm",
                  "broadening_meV", "target_wavelength_nm"):
        if field not in chi2:
            raise Config20Error(f"chi2.{field} is required.")
    flag = chi2["apply_kspace_2pi_squared_scaling"]
    if not isinstance(flag, bool):
        # A YAML "true"/"false" string here would silently read as truthy.
        raise Config20Error(
            "chi2.apply_kspace_2pi_squared_scaling must be a YAML boolean "
            f"(true / false), got {flag!r} of type {type(flag).__name__}."
        )
    factor = float(chi2["kspace_scaling_factor"])
    if abs(factor - TWO_PI_SQUARED_REFERENCE) > 1.0e-9:
        raise Config20Error(
            f"chi2.kspace_scaling_factor is {factor!r}; Demo 20's experiment is "
            f"defined as (2*pi)^2 = {TWO_PI_SQUARED_REFERENCE}. Change the "
            "definition deliberately in the YAML comment block if this is "
            "intended, not by editing the number alone."
        )
    if int(cfg["states"]["max_states_per_band"]) < 2:
        raise Config20Error(
            "states.max_states_per_band must be at least 2: the second term of "
            "the susceptibility needs a second state in each band."
        )
    if str(cfg["analysis"]["source"]) not in ("master_table", "nextnano_output"):
        raise Config20Error(
            "analysis.source must be 'master_table' or 'nextnano_output'."
        )


def apply_overrides(
    cfg: dict[str, Any],
    *,
    kspace_scale: str | None = None,
    master_table: str | Path | None = None,
    source: str | None = None,
    results_root: str | Path | None = None,
    plots: bool | None = None,
) -> dict[str, Any]:
    """Apply command-line overrides to one execution only.

    ``kspace_scale`` accepts ``"on"`` / ``"off"`` (and the obvious synonyms).
    The YAML file on disk is never rewritten, and every override is recorded in
    ``cfg["_overrides"]`` so the run's own artifacts say what was changed.
    """

    cfg = copy.deepcopy(cfg)
    recorded: dict[str, Any] = {}
    if kspace_scale is not None:
        text = str(kspace_scale).strip().lower()
        truthy = {"on", "true", "yes", "1", "enabled"}
        falsy = {"off", "false", "no", "0", "disabled"}
        if text in truthy:
            value = True
        elif text in falsy:
            value = False
        else:
            raise Config20Error(
                f"--kspace-scale must be on or off, got {kspace_scale!r}."
            )
        cfg["chi2"]["apply_kspace_2pi_squared_scaling"] = value
        recorded["chi2.apply_kspace_2pi_squared_scaling"] = value
    if source is not None:
        cfg["analysis"]["source"] = str(source)
        recorded["analysis.source"] = str(source)
    if master_table is not None:
        cfg["analysis"]["master_table"] = str(master_table)
        recorded["analysis.master_table"] = str(master_table)
    if results_root is not None:
        cfg["paths"]["results_root"] = str(results_root)
        recorded["paths.results_root"] = str(results_root)
    if plots is not None:
        cfg["plots"]["enabled"] = bool(plots)
        recorded["plots.enabled"] = bool(plots)
    cfg["_overrides"] = recorded
    validate(cfg)
    return cfg


def paths(cfg: Mapping[str, Any]) -> Paths:
    """Absolute output paths for this configuration."""

    root = repo_path(cfg["paths"]["results_root"])
    subdirs = cfg["paths"]["subdirs"]
    return Paths(
        root=root,
        tables=root / subdirs["tables"],
        plots=root / subdirs["plots"],
        data=root / subdirs["data"],
        qc=root / subdirs["qc"],
        logs=root / subdirs["logs"],
        inputs=root / subdirs["inputs"],
    )


def master_table_path(cfg: Mapping[str, Any]) -> Path:
    return repo_path(cfg["analysis"]["master_table"])


def scaling_enabled(cfg: Mapping[str, Any]) -> bool:
    return bool(cfg["chi2"]["apply_kspace_2pi_squared_scaling"])


def as_record(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The configuration as it will be stamped into every output artifact."""

    return {
        "config_path": cfg.get("_config_path"),
        "command_line_overrides": cfg.get("_overrides") or {},
        "demo": dict(cfg["demo"]),
        "geometry": dict(cfg["geometry"]),
        "materials": dict(cfg["materials"]),
        "mesh": dict(cfg["mesh"]),
        "grading": dict(cfg["grading"]),
        "states": dict(cfg["states"]),
        "chi2": dict(cfg["chi2"]),
        "k_parallel": dict(cfg["k_parallel"]),
        "qc": dict(cfg["qc"]),
        "analysis": dict(cfg["analysis"]),
        "paper": dict(cfg["paper"]),
        "solver_enabled": bool(cfg["solver"]["enabled"]),
    }
