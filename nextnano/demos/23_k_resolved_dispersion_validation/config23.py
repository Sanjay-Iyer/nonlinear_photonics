"""Configuration loading and validation for Demo 23."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any, Mapping

import yaml


DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[2]
COMMON_CONFIG = DEMO_DIR / "demo23_config.yaml"
MODE_CONFIGS = {
    "23A": DEMO_DIR / "configs" / "23A_baseline_shared_parabola.yaml",
    "23B": DEMO_DIR / "configs" / "23B_separate_parabolas.yaml",
    "23C": DEMO_DIR / "configs" / "23C_boss_hybrid.yaml",
    "23D": DEMO_DIR / "configs" / "23D_raw_kp8.yaml",
}


class Demo23Error(RuntimeError):
    """A fail-loudly Demo 23 configuration, solver, or analysis error."""


def _merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge(dict(result[key]), value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(mode: str | None = None) -> dict[str, Any]:
    """Load the common configuration and optionally one A-D mode overlay."""

    cfg = yaml.safe_load(COMMON_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise Demo23Error(f"invalid configuration: {COMMON_CONFIG}")
    if mode is not None:
        name = str(mode).upper()
        if name not in MODE_CONFIGS:
            raise Demo23Error(f"mode must be one of {tuple(MODE_CONFIGS)}, got {mode!r}")
        overlay = yaml.safe_load(MODE_CONFIGS[name].read_text(encoding="utf-8"))
        cfg = _merge(cfg, overlay or {})
    validate(cfg)
    return cfg


def validate(cfg: Mapping[str, Any]) -> None:
    required = {
        "demo", "geometry", "materials", "mesh", "kp8", "solver",
        "state_tracking", "chi2", "integration", "dispersion", "paths",
    }
    missing = sorted(required - set(cfg))
    if missing:
        raise Demo23Error("missing configuration blocks: " + ", ".join(missing))

    geometry = cfg["geometry"]
    total = sum(float(geometry[name]) for name in (
        "thick_well_nm", "tunnel_barrier_nm", "thin_well_nm", "period_barrier_nm"
    ))
    if not math.isclose(total, float(geometry["total_period_nm"]), abs_tol=1e-12):
        raise Demo23Error(f"geometry thicknesses total {total}, not total_period_nm")
    if str(geometry["interface_model"]) != "linear_1nm":
        raise Demo23Error("Demo 23 regression geometry must remain Demo 21 Case 04 linear_1nm")

    integration = cfg["integration"]
    if integration["production_convention"] != "d2k_over_2pi_squared":
        raise Demo23Error("production normalization must remain Demo 20/21 d2k/(2pi)^2")
    if integration["bz_edge_convention"] != "legacy_pi_over_a":
        raise Demo23Error("baseline regression requires legacy_pi_over_a")
    if int(integration["spin_degeneracy"]) != 2:
        raise Demo23Error("baseline spin degeneracy must remain 2")
    points = int(integration["production_points"])
    grid_points = [int(value) for value in integration["grid_convergence_points"]]
    if grid_points != sorted(set(grid_points)) or grid_points[-1] != points:
        raise Demo23Error("grid convergence points must be increasing and end at production")
    fractions = [float(value) for value in integration["kmax_convergence_fractions"]]
    if float(integration["fraction_of_bz"]) not in fractions:
        raise Demo23Error("nominal kmax must be present in kmax convergence ladder")

    chi2 = cfg["chi2"]
    frozen = {
        "broadening_meV": 5.0,
        "r_e_hh_nm": 0.751,
        "n_periods_per_metre": 1.0 / 30.0e-9,
        "max_states_per_band": 2,
    }
    for key, expected in frozen.items():
        if not math.isclose(float(chi2[key]), expected, rel_tol=1e-12, abs_tol=1e-12):
            raise Demo23Error(f"{key} must remain the validated value {expected}")

    if "mode" in cfg:
        mode = cfg["mode"]
        expected = {
            "23A": "shared_reduced_mass",
            "23B": "separate_parabolic",
            "23C": "boss_hybrid",
            "23D": "raw_kp8",
        }
        if expected.get(str(mode.get("id"))) != mode.get("backend"):
            raise Demo23Error("mode id/backend pairing is invalid")


def k_bz_per_nm(cfg: Mapping[str, Any]) -> float:
    """Legacy Demo 20 zone reference, pi/a, in nm^-1."""

    return math.pi / float(cfg["integration"]["lattice_constant_nm"])


def kmax_per_nm(cfg: Mapping[str, Any], fraction: float | None = None) -> float:
    value = float(cfg["integration"]["fraction_of_bz"] if fraction is None else fraction)
    return value * k_bz_per_nm(cfg)


def result_root(cfg: Mapping[str, Any]) -> Path:
    path = Path(str(cfg["paths"]["results_root"]))
    return path if path.is_absolute() else REPO_ROOT / path

