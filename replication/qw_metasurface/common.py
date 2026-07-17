"""Shared utilities for the qw_metasurface replication.

Every phase script imports from here so that logging, checkpointing, and
config access follow one convention:
  - all physical parameters come from config/paper_params.yaml (never hardcode)
  - every run logs to logs/ with timestamp, git commit, package versions, seed
  - checkpoints are versioned directories ckpt_YYYYMMDD_HHMM_<desc>/ with a
    manifest.json; existing checkpoints are never overwritten
  - plots are saved as both .png and .svg
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

REPL_ROOT = Path(__file__).resolve().parent          # replication/qw_metasurface
REPO_ROOT = REPL_ROOT.parent.parent                  # C:\code\nonlinear_photonics
AESTIMO_ROOT = REPO_ROOT / "git" / "aestimo"
DEFAULT_CONFIG = REPL_ROOT / "config" / "paper_params.yaml"


def load_config(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_CONFIG
    with open(p, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["_config_path"] = str(p)
    cfg["_config_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return cfg


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True,
            stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "NO_GIT"


def package_versions() -> dict:
    vers = {"python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("numpy", "scipy", "matplotlib", "yaml", "torch", "kdotpy",
                "grcwa", "h5py", "pandas"):
        try:
            m = __import__(mod)
            vers[mod] = getattr(m, "__version__", "?")
        except Exception:
            vers[mod] = "not importable"
    return vers


def start_run_log(phase: str, seed: int | None = None, extra: dict | None = None) -> Path:
    """Create logs/<ts>_<phase>.log recording env + seed; returns its path."""
    logs = REPL_ROOT / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs / f"{ts}_{phase}.log"
    if seed is not None:
        np.random.seed(seed)
    payload = {
        "phase": phase,
        "timestamp": ts,
        "git_commit": git_commit(),
        "seed": seed,
        "argv": sys.argv,
        "versions": package_versions(),
    }
    if extra:
        payload.update(extra)
    log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return log_path


def append_log(log_path: Path, message: str):
    stamp = _dt.datetime.now().strftime("%H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n[{stamp}] {message}")


class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, complex):
            return {"re": o.real, "im": o.imag}
        return super().default(o)


def new_checkpoint(phase_dir: Path, shortdesc: str) -> Path:
    """Create a fresh versioned checkpoint dir; never reuses an existing one."""
    ck_root = phase_dir / "checkpoints"
    ck_root.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M")
    base = f"ckpt_{stamp}_{shortdesc}"
    path = ck_root / base
    n = 1
    while path.exists():                     # never overwrite a checkpoint
        n += 1
        path = ck_root / f"{base}_v{n}"
    path.mkdir()
    return path


def write_manifest(ckpt_dir: Path, cfg: dict, inputs: dict, outputs: dict):
    manifest = {
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "config_path": cfg.get("_config_path"),
        "config_sha256": cfg.get("_config_sha256"),
        "inputs": inputs,
        "key_outputs": outputs,
        "versions": package_versions(),
    }
    with open(ckpt_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, cls=NumpyJSONEncoder)


def save_plot(fig, out_dir: Path, stem: str):
    """Save a matplotlib figure as both .png and .svg (plan requirement)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(out_dir / f"{stem}.{ext}", dpi=200, bbox_inches="tight")


def import_prior_paper_modules():
    """Make the prior-session analysis modules under git/aestimo importable."""
    for p in (str(AESTIMO_ROOT), str(AESTIMO_ROOT / "paper")):
        if p not in sys.path:
            sys.path.insert(0, p)
