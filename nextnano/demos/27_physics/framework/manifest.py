"""Manifests for every Professional invocation.

A Demo 27 physics stage that runs the solver and does not leave a manifest is a
bug, and a test enforces it. The manifest records what was actually executed --
the deck's hash, the argv, the machine, the harvest requested, the wall time and
the files that appeared -- so a result can be traced back to its inputs long
after the run.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
from pathlib import Path
from typing import Mapping

from .report import write_json

MANIFEST_NAME = "PROFESSIONAL_RUN_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_outputs(directory: Path) -> dict:
    """Count and size what the solver actually wrote, without reading contents."""
    directory = Path(directory)
    if not directory.is_dir():
        return {"files": 0, "bytes": 0, "extensions": {}}
    files = 0
    total = 0
    extensions: dict = {}
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        files += 1
        size = path.stat().st_size
        total += size
        extensions[path.suffix or "<none>"] = extensions.get(path.suffix or "<none>", 0) + 1
    return {"files": files, "bytes": total, "extensions": dict(sorted(extensions.items()))}


def build(*, sub_demo: str, stage: str, deck: Path, output_dir: Path,
          machine: Mapping, spec_summary: Mapping, changes: Mapping,
          seconds: float, returncode, argv=None, cost_statement: Mapping | None = None) -> dict:
    deck = Path(deck)
    return {
        "sub_demo": sub_demo,
        "stage": stage,
        "recorded": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "deck": {"path": str(deck), "name": deck.name,
                 "sha256": sha256(deck) if deck.is_file() else None},
        "machine": {"executable": str(machine.get("executable", machine.get("exe", ""))),
                    "database": str(machine.get("database", "")),
                    "license": str(machine.get("license", "")),
                    "threads": int(machine.get("threads", 1))},
        "argv": list(argv or []),
        "deck_spec": dict(spec_summary),
        "controlled_changes": {key: {"baseline": before, "deck": after}
                               for key, (before, after) in dict(changes).items()},
        "cost_statement": dict(cost_statement or {}),
        "wall_seconds": float(seconds),
        "returncode": returncode,
        "output_dir": str(output_dir),
        "outputs": scan_outputs(output_dir),
    }


def write(directory: Path, manifests: list) -> Path:
    return write_json(Path(directory) / MANIFEST_NAME,
                      {"schema": 1, "runs": list(manifests)})


def spec_summary(spec) -> dict:
    """The physics-bearing fields of a DeckSpec, flattened for the manifest."""
    return {
        "band_model": spec.band_model,
        "interface_model": spec.interface_model,
        "grade_width_nm": spec.grade_width_nm,
        "thick_well_nm": spec.thick_well_nm,
        "tunnel_barrier_nm": spec.tunnel_barrier_nm,
        "thin_well_nm": spec.thin_well_nm,
        "period_barrier_nm": spec.period_barrier_nm,
        "barrier_al_fraction": spec.barrier_al_fraction,
        "temperature_K": spec.temperature_K,
        "active_spacing_nm": spec.active_spacing_nm,
        "outer_spacing_nm": spec.outer_spacing_nm,
        "quantum_region_padding_nm": spec.quantum_region_padding_nm,
        "boundary": spec.boundary,
        "num_electrons": spec.num_electrons,
        "num_holes": spec.num_holes,
        "output_state_count": spec.output_state_count,
        "k_mode": spec.k_mode,
        "k_points": spec.k_points,
        "kmax_per_nm": spec.kmax_per_nm,
        "relative_size": spec.relative_size,
        "symmetry": spec.symmetry,
        "direction_name": spec.direction_name,
        "direction": list(spec.direction),
        "electrostatics": spec.electrostatics,
        "doping": [d.__dict__ for d in spec.doping],
        "harvest": dict(spec.harvest),
    }
