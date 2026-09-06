"""nextnano++ machine resolution and the Professional gate.

The gate exists because a Free build silently cannot do Demo 27's physics: it
caps at 100 grid points and the production decks are far larger. Discovering
that here costs a second; discovering it after a queued run costs the run.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Mapping

import yaml

from . import Demo27Error
from .registry import REPO_ROOT

DEFAULT_MACHINE_YAML = REPO_ROOT / "nextnano" / "config" / "paths.local.yaml"


def machine_config(explicit: Path | None = None) -> dict:
    """Resolve the per-machine nextnano++ paths, or explain what is missing."""
    path = Path(explicit) if explicit else DEFAULT_MACHINE_YAML
    if not path.is_file():
        raise Demo27Error(
            "per-machine nextnano configuration is absent: %s\n"
            "  copy paths.local.yaml.example to paths.local.yaml on this machine and "
            "fill in the nextnano++ executable, database and license paths." % path)
    blob = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    block = blob.get("nextnano++") or {}
    resolved = {"source": str(path)}
    for key in ("exe", "database", "license"):
        value = block.get(key)
        if not value or str(value).startswith("PATH_TO_"):
            raise Demo27Error("paths.local.yaml does not set nextnano++.%s" % key)
        resolved[key] = Path(str(value)).expanduser()
    resolved["threads"] = int(block.get("threads", 1))
    return resolved


def is_free_build(machine: Mapping) -> bool:
    exe = Path(machine["exe"]).name.lower()
    lic = Path(machine["license"]).name.lower()
    return "free" in exe or "free" in lic


def assert_professional(machine: Mapping) -> dict:
    """Fail loudly unless a Professional-capable executable and license exist."""
    exe = Path(machine["exe"])
    problems = []
    if not exe.is_file():
        problems.append("executable not found: %s" % exe)
    elif "free" in exe.name.lower():
        problems.append(
            "the configured executable is a Free build (%s); Demo 27 physics stages need "
            "nextnano++ Professional. The Free build caps at 100 grid points and cannot "
            "run these decks." % exe.name)
    for key in ("database", "license"):
        if not Path(machine[key]).is_file():
            problems.append("%s not found: %s" % (key, machine[key]))
    license_path = Path(machine["license"])
    if license_path.is_file() and "free" in license_path.name.lower():
        problems.append("the configured license is a Free license (%s)" % license_path.name)
    if problems:
        raise Demo27Error("nextnano++ Professional is not available on this machine:\n  - "
                          + "\n  - ".join(problems))
    return {"executable": str(exe), "database": str(machine["database"]),
            "license": str(machine["license"]), "threads": int(machine["threads"])}


def parse_deck(machine: Mapping, deck: Path, scratch: Path, timeout: float = 300.0) -> dict:
    """Run ``--parse`` over one deck. Grammar only; no physics, no license class needed."""
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    argv = [str(machine["exe"]), "--parse",
            "-d", str(machine["database"]), "-l", str(machine["license"]),
            "-o", str(scratch), str(deck)]
    try:
        done = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
        blob = (done.stdout or "") + (done.stderr or "")
        ok = done.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        blob, ok = str(exc), False
    return {"deck": Path(deck).name, "parse_ok": ok,
            "message": "parsed" if ok else _first_error(blob)}


def _first_error(blob: str) -> str:
    for line in blob.splitlines():
        if "error" in line.lower():
            return line.strip()[:300]
    lines = blob.strip().splitlines()
    return (lines[-1] if lines else "no output")[:300]
