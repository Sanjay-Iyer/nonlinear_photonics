"""Follow physical states across the Demo 11 asymmetry sweep.

Why this exists
===============

The 2026-07-31 licensed run produced a chi(2)-versus-asymmetry curve with an
8.5x discontinuity between ``s = 0.38`` and ``s = 0.42``. Across that step
``<e2|hh2>`` collapses from 0.958 to 0.448 and ``E_hh2`` reverses direction.
An energy level that turns around under a monotonic change of geometry is the
signature of an avoided crossing followed by *index*: on one side "state 2" is
the lower branch, on the other it is the upper one, and the label silently
changes meaning halfway through the sweep.

Naming states by ascending energy is therefore not safe here, and the paper's
"HH2" cannot be assumed to be the second energy-ordered hole state at every
asymmetry. This module assigns each sweep point's states to the previous
point's by envelope overlap, so a branch keeps its identity through a crossing,
and reports **both** labellings side by side. It does not decide which one is
right; it makes the difference visible.

What it deliberately does not do
================================

It does not smooth, interpolate, or discard points. An ambiguous assignment is
reported as ambiguous and carried forward, because a crossing that the tracker
cannot resolve is a finding about the sweep, not noise to be suppressed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

import analysis
import chi2 as chi2mod

#: Bands this module knows how to track, and the envelope-column prefix each
#: one is written under in a case's ``extracted/envelopes.csv``.
BAND_COLUMN_PREFIX: Mapping[str, str] = {"electron": "psi_e", "heavy_hole": "psi_hh"}


@dataclass(frozen=True)
class TrackedState:
    """One state at one sweep point, with both of its identities."""

    sweep_value: float
    case_id: str
    band: str
    raw_index: int
    tracked_label: int
    energy_eV: float
    overlap_with_previous: float | None
    second_best_overlap: float | None
    assignment_margin: float | None
    sign_flip_applied: bool
    ambiguous: bool
    ambiguity_reason: str
    region_probabilities: Mapping[str, float] = field(default_factory=dict)
    left_boundary_probability: float | None = None
    right_boundary_probability: float | None = None
    boundary_probability: float | None = None

    def row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "sweep_value": self.sweep_value,
            "case_id": self.case_id,
            "band": self.band,
            "raw_index": self.raw_index,
            "tracked_label": self.tracked_label,
            "energy_eV": self.energy_eV,
            "overlap_with_previous": self.overlap_with_previous,
            "second_best_overlap": self.second_best_overlap,
            "assignment_margin": self.assignment_margin,
            "sign_flip_applied": self.sign_flip_applied,
            "ambiguous": self.ambiguous,
            "ambiguity_reason": self.ambiguity_reason,
            "left_boundary_probability": self.left_boundary_probability,
            "right_boundary_probability": self.right_boundary_probability,
            "boundary_probability": self.boundary_probability,
        }
        row.update(
            {
                f"probability_{name}": value
                for name, value in self.region_probabilities.items()
            }
        )
        return row


@dataclass(frozen=True)
class SweepPoint:
    """Everything the tracker needs from one completed case."""

    case_id: str
    sweep_value: float
    z_nm: np.ndarray
    energies_eV: np.ndarray
    envelopes: np.ndarray


def interpolate_onto(
    z_target: np.ndarray, z_source: np.ndarray, envelopes: np.ndarray
) -> np.ndarray:
    """Resample envelopes onto another grid, then renormalise.

    Grids differ between sweep points whenever the geometry changes the number
    of grid lines, and an overlap integral between two different grids is not
    an overlap at all. Interpolation is linear and the result is renormalised,
    because interpolation does not conserve the norm.
    """

    source = np.asarray(z_source, dtype=float)
    target = np.asarray(z_target, dtype=float)
    values = np.atleast_2d(np.asarray(envelopes, dtype=float))
    if values.shape[0] != source.size:
        values = values.T
    columns = []
    for index in range(values.shape[1]):
        resampled = np.interp(target, source, values[:, index], left=0.0, right=0.0)
        norm = float(np.trapezoid(resampled**2, target))
        if norm > 0:
            resampled = resampled / np.sqrt(norm)
        columns.append(resampled)
    return np.column_stack(columns)


def _energy_penalty(
    previous_energies: np.ndarray, current_energies: np.ndarray, weight: float
) -> np.ndarray:
    """Secondary, small energy-continuity term for the assignment cost.

    Overlap decides. This only separates candidates that overlap says are
    equally good, which is precisely the situation at a crossing where the two
    branches are nearly degenerate. Its weight is deliberately far below the
    overlap scale so it can never outvote a clear overlap match.
    """

    if weight <= 0 or previous_energies.size == 0 or current_energies.size == 0:
        return np.zeros((previous_energies.size, current_energies.size), dtype=float)
    spread = float(
        np.max(np.concatenate([previous_energies, current_energies]))
        - np.min(np.concatenate([previous_energies, current_energies]))
    )
    if not np.isfinite(spread) or spread <= 0:
        return np.zeros((previous_energies.size, current_energies.size), dtype=float)
    gap = np.abs(previous_energies[:, None] - current_energies[None, :]) / spread
    return float(weight) * gap


def align_signs(
    reference: np.ndarray, current: np.ndarray, assignment: Sequence[int]
) -> tuple[np.ndarray, list[bool]]:
    """Flip each matched envelope so its sign agrees with its predecessor.

    An eigenvector's global sign is arbitrary, and nextnano++ does not promise a
    consistent one between runs. Overlaps used for *matching* take an absolute
    value so the sign cannot affect the assignment, but any quantity carried
    along a branch -- an off-diagonal dipole, a signed overlap -- flips with it.
    Aligning once, after assignment, keeps the branch physically continuous.
    """

    aligned = np.array(current, dtype=float, copy=True)
    flips: list[bool] = []
    for column, previous_index in enumerate(assignment):
        if previous_index is None or previous_index < 0:
            flips.append(False)
            continue
        inner = float(np.dot(reference[:, previous_index], aligned[:, column]))
        flip = inner < 0.0
        if flip:
            aligned[:, column] = -aligned[:, column]
        flips.append(flip)
    return aligned, flips


def track_band(
    points: Sequence[SweepPoint],
    *,
    band: str,
    minimum_confidence: float = 0.60,
    minimum_margin: float = 0.15,
    energy_continuity_weight: float = 0.05,
) -> tuple[list[TrackedState], dict[str, Any]]:
    """Chain one band's states through a sweep, point by point.

    Returns the per-state records and a diagnostics mapping holding every
    assignment matrix, so the decision at each step can be re-examined without
    re-running anything.
    """

    tracked: list[TrackedState] = []
    diagnostics: dict[str, Any] = {
        "band": band,
        "method": None,
        "assignment_backend": analysis.assignment_backend(),
        "minimum_confidence": float(minimum_confidence),
        "minimum_assignment_margin": float(minimum_margin),
        "energy_continuity_weight": float(energy_continuity_weight),
        "steps": [],
        "ambiguous_steps": [],
    }
    if not points:
        diagnostics["reason"] = "no completed cases for this band"
        return tracked, diagnostics

    ordered = sorted(points, key=lambda point: point.sweep_value)
    reference_grid = ordered[0].z_nm
    previous_envelopes: np.ndarray | None = None
    previous_labels: list[int] | None = None
    previous_energies: np.ndarray | None = None

    for position, point in enumerate(ordered):
        current = interpolate_onto(reference_grid, point.z_nm, point.envelopes)
        count = current.shape[1]
        if previous_envelopes is None:
            # The first point defines the labelling; nothing to match against.
            labels = list(range(1, count + 1))
            for index in range(count):
                tracked.append(
                    TrackedState(
                        sweep_value=point.sweep_value,
                        case_id=point.case_id,
                        band=band,
                        raw_index=index + 1,
                        tracked_label=labels[index],
                        energy_eV=float(point.energies_eV[index]),
                        overlap_with_previous=None,
                        second_best_overlap=None,
                        assignment_margin=None,
                        sign_flip_applied=False,
                        ambiguous=False,
                        ambiguity_reason="first sweep point; labelling defined here",
                    )
                )
            previous_envelopes, previous_labels = current, labels
            previous_energies = np.asarray(point.energies_eV, dtype=float)
            continue

        shared = min(previous_envelopes.shape[1], count)
        result = analysis.track_states(
            x=reference_grid,
            previous_envelopes=previous_envelopes[:, :shared],
            current_envelopes=current[:, :shared],
            minimum_confidence=minimum_confidence,
        )
        diagnostics["method"] = result.method
        similarity = np.asarray(result.similarity_matrix, dtype=float)
        penalty = _energy_penalty(
            np.asarray(previous_energies, dtype=float)[:shared],
            np.asarray(point.energies_eV, dtype=float)[:shared],
            energy_continuity_weight,
        )
        if penalty.shape == similarity.shape and float(np.max(penalty)) > 0:
            # Re-solve with the tie-breaker folded in. Overlap still dominates:
            # the penalty is bounded by energy_continuity_weight, well under the
            # overlap differences that distinguish an unambiguous match.
            rows, cols = analysis.solve_assignment(-(similarity - penalty))
            assignment = [-1] * shared
            for row, col in zip(rows, cols):
                assignment[int(col)] = int(row)
        else:
            assignment = list(result.assignment)

        aligned, flips = align_signs(previous_envelopes, current, assignment)
        labels = [0] * count
        step: dict[str, Any] = {
            "case_id": point.case_id,
            "sweep_value": point.sweep_value,
            "similarity_matrix": similarity.tolist(),
            "assignment": list(assignment),
            "assignments": [],
        }
        for column in range(count):
            previous_index = assignment[column] if column < len(assignment) else -1
            if previous_index is not None and 0 <= previous_index < len(previous_labels):
                labels[column] = previous_labels[previous_index]
                best = float(similarity[previous_index, column])
                others = np.delete(similarity[:, column], previous_index)
                second = float(np.max(others)) if others.size else 0.0
            else:
                # A state with no predecessor is new to the window; give it a
                # fresh label rather than reusing one that means something else.
                labels[column] = max(previous_labels or [0]) + 1 + column
                best = None
                second = None
            margin = None if best is None or second is None else best - second
            reasons: list[str] = []
            if best is not None and best < minimum_confidence:
                reasons.append(
                    f"best overlap {best:.3f} < {minimum_confidence:.2f}"
                )
            if margin is not None and margin < minimum_margin:
                reasons.append(
                    f"margin over the runner-up {margin:.3f} < {minimum_margin:.2f}"
                )
            if best is None:
                reasons.append("no predecessor matched")
            ambiguous = bool(reasons)
            tracked.append(
                TrackedState(
                    sweep_value=point.sweep_value,
                    case_id=point.case_id,
                    band=band,
                    raw_index=column + 1,
                    tracked_label=labels[column],
                    energy_eV=float(point.energies_eV[column]),
                    overlap_with_previous=best,
                    second_best_overlap=second,
                    assignment_margin=margin,
                    sign_flip_applied=bool(flips[column]) if column < len(flips) else False,
                    ambiguous=ambiguous,
                    ambiguity_reason="; ".join(reasons) or "unambiguous",
                )
            )
            step["assignments"].append(
                {
                    "raw_index": column + 1,
                    "tracked_label": labels[column],
                    "matched_previous_index": (
                        None if previous_index is None or previous_index < 0
                        else previous_index + 1
                    ),
                    "best_overlap": best,
                    "second_best_overlap": second,
                    "margin": margin,
                    "sign_flip_applied": (
                        bool(flips[column]) if column < len(flips) else False
                    ),
                    "ambiguous": ambiguous,
                    "reason": "; ".join(reasons) or "unambiguous",
                }
            )
        if any(entry["ambiguous"] for entry in step["assignments"]):
            diagnostics["ambiguous_steps"].append(point.case_id)
        diagnostics["steps"].append(step)
        previous_envelopes, previous_labels = aligned, labels
        previous_energies = np.asarray(point.energies_eV, dtype=float)

    diagnostics["tracked_state_count"] = len(tracked)
    diagnostics["ambiguous_state_count"] = sum(1 for state in tracked if state.ambiguous)
    diagnostics["label_reordering_detected"] = any(
        state.raw_index != state.tracked_label for state in tracked
    )
    return tracked, diagnostics


def reorder_to_tracked_labels(
    band: chi2mod.BandStates, tracked: Sequence[TrackedState]
) -> chi2mod.BandStates:
    """Rebuild a band with its states in tracked-label order.

    Feeding this to Eq. 2 instead of the solver's energy ordering is what turns
    "chi(2) with raw index tracking" and "chi(2) with physical-state tracking"
    into two numbers that can be compared. Where no reordering happened the two
    are identical by construction, which is itself the useful answer.
    """

    if not tracked:
        return band
    order = sorted(range(len(tracked)), key=lambda i: tracked[i].tracked_label)
    indices = [tracked[i].raw_index - 1 for i in order]
    indices = [i for i in indices if 0 <= i < band.count]
    if len(indices) != band.count:
        return band
    return chi2mod.BandStates(
        band.z_nm,
        band.energies_eV[indices],
        band.envelopes[:, indices],
        band.label,
    )
