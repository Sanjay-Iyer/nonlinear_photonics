"""Demo 23 target-state classification and Demo 22 tracking reuse."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from config23 import DEMO_DIR, Demo23Error


DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
if str(DEMO22) not in sys.path:
    sys.path.insert(0, str(DEMO22))
import kp8io22  # noqa: E402
import state_tracking22  # noqa: E402


TARGETS = ("e1", "e2", "hh1", "hh2")


@dataclass(frozen=True)
class TrackedSubbands:
    k_per_nm: np.ndarray
    energies_eV: Mapping[str, np.ndarray]
    k0_raw_identity: Mapping[str, int]
    tracking: state_tracking22.TrackingResult
    rows: tuple[dict[str, Any], ...]


def _component_index(names: tuple[str, ...], token: str) -> int | None:
    target = token.lower()
    for index, name in enumerate(names):
        normalized = name.lower().replace("heavy_hole", "hh").replace("light_hole", "lh")
        if target in normalized:
            return index
    return None


def classify_k0(grid: kp8io22.RawStateGrid) -> dict[str, int]:
    """Identify target states by CB character, then order within each family."""

    cb = _component_index(grid.component_names, "cb")
    if cb is None:
        raise Demo23Error("CB-resolved spinor composition is required for state classification")
    cb_fraction = grid.spinor_components[0, :, cb]
    electron = np.flatnonzero(cb_fraction >= 0.5)
    holes = np.flatnonzero(cb_fraction < 0.5)
    if len(electron) < 2 or len(holes) < 3:
        raise Demo23Error(
            f"k=0 classification found {len(electron)} electron-like and {len(holes)} hole-like states"
        )
    electron = electron[np.argsort(grid.energies_eV[0, electron])]
    holes = holes[np.argsort(grid.energies_eV[0, holes])[::-1]]
    return {
        "e1": int(electron[0]),
        "e2": int(electron[1]),
        "hh1": int(holes[0]),
        "hh2": int(holes[1]),
        "hh3": int(holes[2]),
    }


def validate_radial_path(grid: kp8io22.RawStateGrid, *, angular_tolerance: float = 1e-7) -> None:
    k = np.asarray(grid.k_per_nm, dtype=float)
    if abs(k[0]) > 1e-10 or np.any(np.diff(k) <= 0):
        raise Demo23Error("production data must be a unique, strictly increasing path beginning at k=0")
    vectors = np.asarray(grid.k_vector_per_nm, dtype=float)
    nonzero = np.linalg.norm(vectors, axis=1) > 1e-12
    directions = vectors[nonzero] / np.linalg.norm(vectors[nonzero], axis=1)[:, None]
    if len(directions) and np.max(np.linalg.norm(np.cross(directions, directions[0]), axis=1)) > angular_tolerance:
        raise Demo23Error("radial production input contains multiple k directions; use direct 2D analysis")


def track_targets(grid: kp8io22.RawStateGrid, cfg: Mapping[str, Any]) -> TrackedSubbands:
    validate_radial_path(grid)
    labels = classify_k0(grid)
    settings = cfg["state_tracking"]
    result = state_tracking22.track_states(
        grid.energies_eV,
        np.sqrt(np.clip(grid.spinor_components, 0.0, None)),
        ntrack=grid.energies_eV.shape[1],
        minimum_overlap=float(settings["minimum_overlap_score"]),
        minimum_margin=float(settings["minimum_assignment_margin"]),
        energy_tie_break_weight=float(settings["energy_tie_break_weight"]),
    )
    energies: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    ambiguous: list[str] = []
    for label in TARGETS:
        identity = labels[label]
        raw_at_k = result.tracked_raw_indices[:, identity]
        energies[label] = np.asarray([
            grid.energies_eV[ik, raw] for ik, raw in enumerate(raw_at_k)
        ])
        for ik, raw in enumerate(raw_at_k):
            confidence = str(result.confidence[ik, identity])
            if confidence == "ambiguous":
                ambiguous.append(f"{label}@k={grid.k_per_nm[ik]:.6g}")
            rows.append({
                "k_per_nm": float(grid.k_per_nm[ik]),
                "raw_solver_index": int(grid.raw_state_index[raw]),
                "assigned_physical_state": label,
                "energy_eV": float(grid.energies_eV[ik, raw]),
                "tracking_score": float(result.overlap_scores[ik, identity]),
                "assignment_margin": float(result.assignment_margins[ik, identity]),
                "confidence": confidence,
                "dominant_spinor_character": grid.component_names[
                    int(np.argmax(grid.spinor_components[ik, raw]))
                ],
            })
    if ambiguous and bool(settings.get("fail_on_ambiguous_target", True)):
        preview = ", ".join(ambiguous[:8])
        raise Demo23Error(
            f"ambiguous target-state tracking ({preview}); refusing dispersion fitting"
        )
    return TrackedSubbands(
        np.asarray(grid.k_per_nm), energies, labels, result, tuple(rows)
    )


def load_and_track(raw_root: Path, inventory_csv: Path, cfg: Mapping[str, Any]) -> TrackedSubbands:
    grid = kp8io22.extract_state_grid(Path(raw_root), Path(inventory_csv))
    return track_targets(grid, cfg)

