"""Configuration and source provenance for Demo 18E."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

try:
    import yaml
except ModuleNotFoundError:  # Bundled artifact runtime; the file is JSON-compatible YAML.
    yaml = None


DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[2]
CONFIG_PATH = DEMO_DIR / "demo18e.yaml"


class Config18EError(ValueError):
    pass


def load_config(path: Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else CONFIG_PATH
    text = source.read_text(encoding="utf-8")
    if yaml is None:
        import json
        payload = json.loads(text)
    else:
        payload = yaml.safe_load(text)
    if not isinstance(payload, Mapping):
        raise Config18EError(f"{source} did not parse to a mapping")
    cfg = dict(payload)
    validate(cfg)
    return cfg


def validate(cfg: Mapping[str, Any]) -> None:
    required = {"sources", "fixed_physics", "spectrum", "rotation", "controls",
                "case19_geometry"}
    missing = required - set(cfg)
    if missing:
        raise Config18EError(f"missing sections: {sorted(missing)}")
    fixed = cfg["fixed_physics"]
    expected = {
        "broadening_meV": 5.0,
        "spin_degeneracy": 2,
        "wells_per_period_for_Nz": 2,
        "nominal_period_nm": 30.0,
        "r_e_hh_nm": 0.751,
        "hh_relative_weight": 1.0,
    }
    for key, value in expected.items():
        if fixed.get(key) != value:
            raise Config18EError(f"fixed_physics.{key} must be {value!r}")
    if str(cfg["sources"]["demo18d_case"]) != "Case_19":
        raise Config18EError("Demo 18E primary source must be Demo 18D Case_19")
    if str(cfg["rotation"]["protocol"]) != "exact_degenerate_subspace_control":
        raise Config18EError("rotation protocol must preserve the exact-degenerate limit")
    angles = [float(value) for value in cfg["rotation"]["angles_deg"]]
    if angles != list(range(0, 91, 5)):
        raise Config18EError("rotation angles must be the deterministic 0:5:90 grid")
    if int(cfg["fixed_physics"]["k_points"]) < 2:
        raise Config18EError("k_points must be at least two")


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path
