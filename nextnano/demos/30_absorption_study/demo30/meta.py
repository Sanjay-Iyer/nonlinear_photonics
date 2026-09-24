"""Provenance recorded next to every Demo 30 output: code hashes, git state, inputs."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np

from .paths import CONFIG, DEMO_ROOT, LOCK


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_manifest() -> dict:
    """SHA-256 of every Demo 30 source file (captures uncommitted edits too)."""
    files = sorted((DEMO_ROOT / "demo30").glob("*.py")) + sorted((DEMO_ROOT / "scripts").glob("*.py"))
    return {p.relative_to(DEMO_ROOT).as_posix(): sha256_bytes(p) for p in files}


def git_state() -> dict:
    """Commit and dirty flag of the Demo 30 directory (best effort; git may be absent)."""
    def git(*args):
        try:
            return subprocess.run(["git", "-C", str(DEMO_ROOT), *args], capture_output=True,
                                  text=True, check=False, timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    head = git("rev-parse", "HEAD")
    return {"head": head or None, "demo30_uncommitted_changes": bool(git("status", "--porcelain", "--", "."))
            if head else None}


def run_metadata(study: str, runs_provenance: dict, extra: dict | None = None) -> dict:
    return {"study": study, "config_sha256": sha256_bytes(CONFIG), "lock_sha256": sha256_bytes(LOCK),
            "raw_runs": runs_provenance, "code_sha256": code_manifest(), "git": git_state(),
            "python": platform.python_version(), "numpy": np.__version__,
            "licensed_solver_executed": False, **(extra or {})}


def write_csv(path: Path, header: list[str], columns: list) -> None:
    """Columns of equal length -> CSV with full float precision (%.17g) and LF endings."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.column_stack([np.asarray(c, float) for c in columns])
    np.savetxt(path, data, delimiter=",", header=",".join(header), comments="", fmt="%.17g")


def dump(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=_default) + "\n", encoding="utf-8")


def _default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)
