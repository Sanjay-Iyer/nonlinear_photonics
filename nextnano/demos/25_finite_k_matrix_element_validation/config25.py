"""Demo 25 configuration: inherits the Demo 23 structure, never restates it."""

from __future__ import annotations

import copy
import math
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml


DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[2]
DEMO23 = DEMO_DIR.parent / "23_k_resolved_dispersion_validation"
DEMO24 = DEMO_DIR.parent / "24_equation2_spectral_shape_audit"
DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
for module_dir in (DEMO22, DEMO23):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

CONFIG_PATH = DEMO_DIR / "demo25_config.yaml"


class Demo25Error(RuntimeError):
    """Raised for any Demo 25 configuration or contract violation."""


def load_demo23_config() -> dict[str, Any]:
    from config23 import load_config as _load23  # noqa: PLC0415

    return _load23()


def load_config() -> dict[str, Any]:
    """Load Demo 25 config and splice in the frozen Demo 23 structure blocks."""
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    required = ("demo", "inherit", "kp8", "pilot", "production",
                "transition_search", "analysis", "paths", "outputs")
    missing = [key for key in required if key not in cfg]
    if missing:
        raise Demo25Error(f"demo25_config.yaml is missing block(s): {missing}")

    cfg23 = load_demo23_config()
    inherit = cfg["inherit"]
    for block in inherit["frozen_blocks"]:
        if block not in cfg23:
            raise Demo25Error(f"Demo 23 config has no '{block}' block to inherit")
        if block in cfg:
            raise Demo25Error(
                f"'{block}' is inherited from Demo 23 and must not be restated in demo25_config.yaml")
        cfg[block] = copy.deepcopy(cfg23[block])
    cfg.setdefault("kp8", {})
    for key in inherit["frozen_kp8_keys"]:
        if key in cfg["kp8"]:
            raise Demo25Error(f"kp8.{key} is inherited from Demo 23 and must not be restated")
        cfg["kp8"][key] = copy.deepcopy(cfg23["kp8"][key])
    cfg["_demo23_config"] = cfg23
    _validate(cfg)
    return cfg


def _validate(cfg: Mapping[str, Any]) -> None:
    kp = cfg["kp8"]
    cfg23kp = cfg["_demo23_config"]["kp8"]
    for key in ("number_of_electron_states", "number_of_hole_states", "output_state_count"):
        if int(kp[key]) < int(cfg23kp[key]):
            raise Demo25Error(
                f"Demo 25 must not reduce kp8.{key} below Demo 23 "
                f"({kp[key]} < {cfg23kp[key]}); the extended-state search needs more states")
    if int(kp["output_state_count"]) > int(kp["number_of_electron_states"]) + int(kp["number_of_hole_states"]):
        raise Demo25Error("output_state_count exceeds the number of states the solver will produce")
    pilot = cfg["pilot"]
    if not pilot["variants"]:
        raise Demo25Error("the pilot must define at least one variant")
    names = [str(v["name"]) for v in pilot["variants"]]
    if len(names) != len(set(names)):
        raise Demo25Error("pilot variant names must be unique")
    if not any(bool(v["k_integration"]) for v in pilot["variants"]):
        raise Demo25Error("at least one pilot variant must enable k_integration")
    if not any(not bool(v["k_integration"]) for v in pilot["variants"]):
        raise Demo25Error("the pilot needs the Demo 23-style control variant to interpret the result")
    prod = cfg["production"]
    if float(prod["fraction_of_bz"]) <= 0:
        raise Demo25Error("production.fraction_of_bz must be positive")
    if int(prod["requested_k_points"]) < 2:
        raise Demo25Error("production.requested_k_points must be at least 2")


def kmax_per_nm(cfg: Mapping[str, Any], fraction: float) -> float:
    """Reuse Demo 23's Brillouin-zone convention exactly."""
    from config23 import kmax_per_nm as _kmax23  # noqa: PLC0415

    return _kmax23(cfg["_demo23_config"], float(fraction))


def production_direction_vector(cfg: Mapping[str, Any]) -> list[float]:
    name = str(cfg["kp8"]["production_direction"])
    vector = [float(v) for v in cfg["kp8"]["directions"][name]]
    if len(vector) != 3 or not math.isclose(sum(v * v for v in vector), 1.0, rel_tol=1e-9):
        raise Demo25Error(f"direction {name} must be a normalized three-vector")
    return vector


def results_root(cfg: Mapping[str, Any]) -> Path:
    path = Path(str(cfg["paths"]["results_root"]))
    return path if path.is_absolute() else REPO_ROOT / path


def outputs_root(cfg: Mapping[str, Any]) -> Path:
    path = Path(str(cfg["outputs"]["root"]))
    return path if path.is_absolute() else REPO_ROOT / path


def repo_path(value: str) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else REPO_ROOT / path
