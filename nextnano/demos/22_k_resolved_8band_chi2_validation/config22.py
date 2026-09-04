"""Strict configuration and paths for Demo 22."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[2]
CONFIG_PATH = DEMO_DIR / "demo22_config.yaml"
TEMPLATE_PATH = DEMO_DIR / "kp8_acqw22.in.j2"


class Demo22Error(RuntimeError):
    pass


def load_config() -> dict[str, Any]:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    required = {"demo", "geometry", "materials", "mesh", "kp8", "solver", "state_tracking",
                "chi2", "paper", "validation", "paths"}
    missing = sorted(required - set(cfg or {}))
    if missing:
        raise Demo22Error(f"missing top-level config blocks: {', '.join(missing)}")
    g = cfg["geometry"]
    total = float(g["thick_well_nm"]) + float(g["tunnel_barrier_nm"]) + float(
        g["thin_well_nm"]) + float(g["period_barrier_nm"])
    if abs(total - float(g["total_period_nm"])) > 1e-12 or abs(total - 30.0) > 1e-12:
        raise Demo22Error(f"geometry must be exactly 30 nm; got {total}")
    if g["primary_interface_model"] != "abrupt":
        raise Demo22Error("primary Demo 22 paper comparison must remain ideal-abrupt")
    if int(cfg["kp8"]["number_of_hole_states"]) < 3:
        raise Demo22Error("request at least h1/h2/h3: prior work found hh2-hh3 mixing")
    if float(cfg["kp8"]["integration_relative_size"]) != 0.10:
        raise Demo22Error("the primary integration domain is paper-anchored at 0.10 BZ")
    points = int(cfg["kp8"]["integration_points"])
    if not 2 <= points <= 100:
        raise Demo22Error("nextnano++ 3.0.0 requires k_integration num_points in [2, 100]")
    convergence = [int(value) for value in cfg["kp8"]["integration_convergence_points"]]
    if convergence != sorted(set(convergence)) or convergence[-1] != points:
        raise Demo22Error("k-integration convergence points must be unique, increasing, and end at production")
    return cfg


def result_root(cfg: dict[str, Any]) -> Path:
    raw = Path(str(cfg["paths"]["results_root"]))
    return raw if raw.is_absolute() else REPO_ROOT / raw
