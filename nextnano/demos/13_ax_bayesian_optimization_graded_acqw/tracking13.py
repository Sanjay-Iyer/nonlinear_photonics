"""Physical-state tracking for scattered Bayesian-optimization trials.

Demos 11 and 12 track states along a *sweep*: neighbouring points differ by one
small step, so "the previous point" is well defined.  A Bayesian optimizer does
not produce a sweep.  It jumps around the design space, and the trial evaluated
just before this one may be nowhere near it.

So Demo 13 keeps the same physics -- normalized envelope overlap, one-to-one
assignment, sign alignment, energy continuity as a secondary criterion, best and
second-best overlap, an explicit confidence -- and changes only what "previous"
means: each new design is assigned against its **nearest already-completed
neighbour in normalized parameter space**, not against the previous trial index
and never against raw energy order.

Why this matters for the optimizer
==================================

Demo 11's 2026-07-31 licensed run produced an 8.5x jump in chi(2) across one
asymmetry step, caused by two states swapping which one is "state 2" through an
avoided crossing.  A discontinuity like that is exactly what an acquisition
function chases: it looks like an enormous local gain.  Tracking states by
overlap, and refusing the trial when the assignment is ambiguous, is what stops
Demo 13 from optimizing a labelling artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO11_DIR = DEMO_DIR.parent / "11_paper_validation_interband_chi2_acqw"
for _path in (str(SHARED), str(DEMO11_DIR), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import tracking11  # noqa: E402

import design13  # noqa: E402

BANDS: tuple[str, ...] = ("electron", "heavy_hole")


@dataclass(frozen=True)
class TrialStates:
    """Everything the tracker needs from one completed trial."""

    trial_index: int
    parameters: Mapping[str, Any]
    z_nm: np.ndarray
    electron_energies_eV: np.ndarray
    electron_envelopes: np.ndarray
    heavy_hole_energies_eV: np.ndarray
    heavy_hole_envelopes: np.ndarray

    def band(self, name: str) -> tuple[np.ndarray, np.ndarray]:
        if name == "electron":
            return self.electron_energies_eV, self.electron_envelopes
        return self.heavy_hole_energies_eV, self.heavy_hole_envelopes


def _settings(cfg: Mapping[str, Any]) -> dict[str, float]:
    tracking = cfg.get("state_tracking") or {}
    return {
        "minimum_confidence": float(tracking.get("minimum_confidence", 0.60)),
        "minimum_margin": float(tracking.get("minimum_assignment_margin", 0.15)),
        "energy_continuity_weight": float(tracking.get("energy_continuity_weight", 0.05)),
    }


def track_against(
    current: TrialStates,
    reference: TrialStates | None,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    """Assign ``current``'s states to ``reference``'s, band by band.

    With no reference -- the very first completed trial -- the labelling is
    *defined* here.  That is reported as an anchor with confidence 1.0 and the
    method recorded, so a downstream reader can tell "nothing to compare against"
    apart from "compared and matched perfectly".
    """

    settings = _settings(cfg)
    record: dict[str, Any] = {
        "trial_index": current.trial_index,
        "reference_trial": None if reference is None else reference.trial_index,
        "method": "anchor_defines_labelling"
        if reference is None
        else "nearest_neighbour_overlap_assignment",
        "rows": [],
        "diagnostics": {},
        "ambiguous": False,
    }
    if reference is None:
        record.update(
            {
                "state_tracking_confidence": 1.0,
                "assignment_margin": 1.0,
                "tracked_labels": {
                    band: list(range(1, int(current.band(band)[0].size) + 1))
                    for band in BANDS
                },
                "raw_indices": {
                    band: list(range(1, int(current.band(band)[0].size) + 1))
                    for band in BANDS
                },
                "design_distance": 0.0,
                "note": "first completed trial; its raw solver order defines the labels",
            }
        )
        return record

    distance = design13.design_distance(current.parameters, reference.parameters, cfg)
    confidences: list[float] = []
    margins: list[float] = []
    tracked_labels: dict[str, list[int]] = {}
    raw_indices: dict[str, list[int]] = {}
    ambiguous = False
    for band in BANDS:
        reference_energies, reference_envelopes = reference.band(band)
        current_energies, current_envelopes = current.band(band)
        points = [
            tracking11.SweepPoint(
                case_id=f"t{reference.trial_index:04d}",
                sweep_value=0.0,
                z_nm=np.asarray(reference.z_nm, dtype=float),
                energies_eV=np.asarray(reference_energies, dtype=float),
                envelopes=np.asarray(reference_envelopes, dtype=float),
            ),
            tracking11.SweepPoint(
                case_id=f"t{current.trial_index:04d}",
                # A positive sweep value keeps the reference first in the chain;
                # the number itself is the normalized design distance, which is
                # what "how far did we jump" means for scattered trials.
                sweep_value=max(float(distance), 1e-9),
                z_nm=np.asarray(current.z_nm, dtype=float),
                energies_eV=np.asarray(current_energies, dtype=float),
                envelopes=np.asarray(current_envelopes, dtype=float),
            ),
        ]
        states, diagnostics = tracking11.track_band(
            points,
            band=band,
            minimum_confidence=settings["minimum_confidence"],
            minimum_margin=settings["minimum_margin"],
            energy_continuity_weight=settings["energy_continuity_weight"],
        )
        rows = [
            {
                **state.row(),
                "trial_index": current.trial_index,
                "reference_trial": reference.trial_index,
                "design_distance": float(distance),
            }
            for state in states
            if state.case_id == f"t{current.trial_index:04d}"
        ]
        record["rows"].extend(rows)
        record["diagnostics"][band] = diagnostics
        tracked_labels[band] = [int(row["tracked_label"]) for row in rows]
        raw_indices[band] = [int(row["raw_index"]) for row in rows]
        for row in rows:
            if row.get("overlap_with_previous") is not None:
                confidences.append(float(row["overlap_with_previous"]))
            if row.get("assignment_margin") is not None:
                margins.append(float(row["assignment_margin"]))
            ambiguous = ambiguous or bool(row.get("ambiguous"))

    record.update(
        {
            "state_tracking_confidence": min(confidences) if confidences else None,
            "assignment_margin": min(margins) if margins else None,
            "tracked_labels": tracked_labels,
            "raw_indices": raw_indices,
            "design_distance": float(distance),
            "ambiguous": ambiguous,
            "label_reordering_detected": any(
                tracked_labels[band] != raw_indices[band] for band in BANDS
            ),
        }
    )
    return record


def choose_reference(
    current_parameters: Mapping[str, Any],
    history: Sequence[TrialStates],
    cfg: Mapping[str, Any],
) -> TrialStates | None:
    """The completed trial whose design is closest to this one."""

    if not history:
        return None
    match = design13.nearest_neighbour(
        current_parameters, [point.parameters for point in history], cfg
    )
    if match is None:
        return None
    index, _ = match
    return history[index]


def track_sequence(
    points: Sequence[TrialStates], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Track a whole experiment: each trial against its nearest predecessor.

    Trials are processed in the order they completed, so a trial is only ever
    matched against designs that already existed when it ran.  Re-running this
    over a finished experiment therefore reproduces exactly what the closed loop
    saw, which is what makes the recorded confidences auditable.
    """

    ordered = sorted(points, key=lambda point: point.trial_index)
    history: list[TrialStates] = []
    records: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for point in ordered:
        reference = choose_reference(point.parameters, history, cfg)
        record = track_against(point, reference, cfg)
        records.append(record)
        rows.extend(record["rows"])
        history.append(point)
    confidences = [
        float(record["state_tracking_confidence"])
        for record in records
        if record.get("state_tracking_confidence") is not None
    ]
    return {
        "records": records,
        "rows": rows,
        "minimum_confidence": min(confidences) if confidences else None,
        "ambiguous_trials": [
            int(record["trial_index"]) for record in records if record.get("ambiguous")
        ],
        "method": str(
            (cfg.get("state_tracking") or {}).get(
                "method", "nearest_neighbour_overlap_assignment"
            )
        ),
        "tracked_trials": len(records),
    }


def load_trial_states(
    trial_index: int, parameters: Mapping[str, Any], extracted_dir: Path
) -> TrialStates | None:
    """Read one trial's envelopes from the artifacts Demo 11 already wrote.

    ``envelopes.csv`` is written by ``demo11.analyse_case`` as
    ``z_nm, psi_e1..psi_eN, psi_hh1..psi_hhM``. Reading it back rather than
    re-parsing the solver output keeps the tracker on exactly the arrays the
    chi(2) evaluation used.
    """

    path = Path(extracted_dir) / "envelopes.csv"
    if not path.is_file():
        return None
    header = path.read_text(encoding="utf-8").splitlines()[:1]
    if not header:
        return None
    names = [name.strip() for name in header[0].split(",")]
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    if data.ndim != 2 or data.shape[0] < 2:
        return None
    electron_columns = [i for i, name in enumerate(names) if name.startswith("psi_e")]
    hole_columns = [i for i, name in enumerate(names) if name.startswith("psi_hh")]
    if not electron_columns or not hole_columns:
        return None

    energies_path = Path(extracted_dir) / "electron_states.csv"
    electron_energies = _energies_from_state_table(energies_path, len(electron_columns))
    hole_energies = np.arange(len(hole_columns), dtype=float)
    return TrialStates(
        trial_index=int(trial_index),
        parameters=dict(parameters),
        z_nm=data[:, 0],
        electron_energies_eV=electron_energies,
        electron_envelopes=data[:, electron_columns],
        heavy_hole_energies_eV=hole_energies,
        heavy_hole_envelopes=data[:, hole_columns],
    )


def _energies_from_state_table(path: Path, count: int) -> np.ndarray:
    """Electron energies, falling back to an index when the table is absent.

    The energy term is only a tie-breaker in the assignment cost, so a missing
    table degrades tracking to pure overlap rather than failing the trial. The
    fallback is deliberately an increasing sequence, which contributes no
    information and cannot fake continuity.
    """

    if not path.is_file():
        return np.arange(count, dtype=float)
    import csv

    values: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                values.append(float(row["energy_eV"]))
            except (KeyError, TypeError, ValueError):
                continue
    if len(values) < count:
        return np.arange(count, dtype=float)
    return np.asarray(values[:count], dtype=float)
