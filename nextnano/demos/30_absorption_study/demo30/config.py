"""Load config/demo30.json and turn it into the objects the physics code needs."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .equation2 import Settings
from .paths import CONFIG


def load_config(path: Path = CONFIG) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if cfg.get("schema") != 1:
        raise ValueError(f"{path}: unsupported config schema")
    if cfg["baseline_chi2"]["model"] != "demo26-baseline":
        raise ValueError("Demo 30's control must be the unchanged Demo 28A (demo26-baseline) model")
    return cfg


def settings(cfg: dict) -> Settings:
    return Settings(**cfg["baseline_chi2"]["settings"])


def wavelength_grid(cfg: dict) -> np.ndarray:
    w = cfg["baseline_chi2"]["wavelength_nm"]
    if not 0 < w["min"] < w["max"] or w["step"] <= 0:
        raise ValueError("invalid fundamental wavelength grid")
    return np.arange(w["min"], w["max"] + w["step"] / 2, w["step"])


def background_index(cfg: dict) -> dict:
    """Effective in-plane (TE) background index of the MQW stack at 1550 nm and 775 nm.

    eps_eff = f*n_well^2 + (1-f)*n_barrier^2 (layer average for fields parallel to the
    layers). Used only in alpha = omega*Im(chi1)/(2 n c) and the coherence-length estimate.
    """
    b = cfg["background_index"]
    f = b["well_fraction"]
    well, barrier = b["values"]["GaAs"], b["values"]["Al0.55Ga0.45As"]
    out = {}
    for key, name in (("1550nm", "n_omega"), ("775nm", "n_2omega")):
        eps = f * well[key]["n"] ** 2 + (1 - f) * barrier[key]["n"] ** 2
        out[name] = float(np.sqrt(eps))
    out["well_fraction"] = f
    return out
