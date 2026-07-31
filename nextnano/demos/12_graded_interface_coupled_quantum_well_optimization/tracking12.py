"""Two-dimensional physical-state tracking for Demo 12.

Each row is tracked along grading thickness and each column along asymmetry.
Both traversals are retained. A disagreement is an ambiguity diagnostic, not a
reason to smooth or silently relabel the solver data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

DEMO11_DIR = Path(__file__).resolve().parent.parent / "11_paper_validation_interband_chi2_acqw"
if str(DEMO11_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO11_DIR))
import tracking11


@dataclass(frozen=True)
class GridPoint:
    case_id: str
    asymmetry: float
    grading_thickness_nm: float
    z_nm: np.ndarray
    electron_energies_eV: np.ndarray
    electron_envelopes: np.ndarray
    heavy_hole_energies_eV: np.ndarray
    heavy_hole_envelopes: np.ndarray


def _track_line(
    points: Sequence[GridPoint], *, coordinate: str, band: str, settings: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if band == "electron":
        get_energy = lambda point: point.electron_energies_eV
        get_envelope = lambda point: point.electron_envelopes
    else:
        get_energy = lambda point: point.heavy_hole_energies_eV
        get_envelope = lambda point: point.heavy_hole_envelopes
    sweep = [
        tracking11.SweepPoint(
            point.case_id, float(getattr(point, coordinate)), point.z_nm,
            np.asarray(get_energy(point), float), np.asarray(get_envelope(point), float),
        )
        for point in points
    ]
    states, diagnostics = tracking11.track_band(
        sweep, band=band,
        minimum_confidence=float(settings.get("minimum_confidence", 0.60)),
        minimum_margin=float(settings.get("minimum_assignment_margin", 0.15)),
        energy_continuity_weight=float(settings.get("energy_continuity_weight", 0.05)),
    )
    return [state.row() for state in states], diagnostics


def track_grid(points: Sequence[GridPoint], settings: Mapping[str, Any]) -> dict[str, Any]:
    """Track both bands in both grid directions and expose every assignment."""

    rows: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {"asymmetry_rows": {}, "grading_columns": {}}
    for asymmetry in sorted({point.asymmetry for point in points}):
        line = sorted((p for p in points if p.asymmetry == asymmetry), key=lambda p: p.grading_thickness_nm)
        for band in ("electron", "heavy_hole"):
            records, detail = _track_line(line, coordinate="grading_thickness_nm", band=band, settings=settings)
            for record in records:
                record.update({"traversal": "grading_at_fixed_asymmetry", "fixed_asymmetry": asymmetry})
            rows.extend(records)
            diagnostics["asymmetry_rows"][f"s={asymmetry:g}:{band}"] = detail
    for thickness in sorted({point.grading_thickness_nm for point in points}):
        line = sorted((p for p in points if p.grading_thickness_nm == thickness), key=lambda p: p.asymmetry)
        for band in ("electron", "heavy_hole"):
            records, detail = _track_line(line, coordinate="asymmetry", band=band, settings=settings)
            for record in records:
                record.update({"traversal": "asymmetry_at_fixed_grading", "fixed_grading_thickness_nm": thickness})
            rows.extend(records)
            diagnostics["grading_columns"][f"g={thickness:g}:{band}"] = detail
    ambiguous = [row for row in rows if row.get("ambiguous")]
    return {
        "rows": rows,
        "diagnostics": diagnostics,
        "ambiguous_assignments": len(ambiguous),
        "minimum_confidence": min(
            (float(row["overlap_with_previous"]) for row in rows if row.get("overlap_with_previous") is not None),
            default=None,
        ),
        "method": "bidirectional_overlap_assignment_with_energy_secondary",
    }
