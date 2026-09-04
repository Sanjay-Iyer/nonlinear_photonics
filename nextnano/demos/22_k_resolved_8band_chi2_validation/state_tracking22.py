"""Overlap-first physical-state tracking for Demo 22.

Energy order is never used as state identity.  It enters only as a small tie
breaker after adjacent-k state overlap and spinor-character similarity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass(frozen=True)
class TrackingResult:
    tracked_raw_indices: np.ndarray  # (nk, ntrack)
    overlap_scores: np.ndarray       # (nk, ntrack), k0=1
    assignment_margins: np.ndarray   # (nk, ntrack), k0=1
    confidence: np.ndarray           # strings


def _normalise_rows(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=complex)
    norm = np.linalg.norm(values, axis=-1, keepdims=True)
    if np.any(norm == 0):
        raise ValueError("state feature/envelope vectors must have nonzero norm")
    return values / norm


def track_states(
    energies_eV: np.ndarray,
    state_vectors: np.ndarray,
    *,
    ntrack: int,
    minimum_overlap: float = 0.60,
    minimum_margin: float = 0.15,
    energy_tie_break_weight: float = 0.05,
) -> TrackingResult:
    """Track the k=0 identities using a globally optimal adjacent-k assignment.

    ``state_vectors[k, raw_state, feature]`` may be the full complex multiband
    envelope (preferred) or normalized spinor/localization features.  The
    returned overlap is |<u_i(k)|u_j(k+dk)>|^2.
    """
    energies = np.asarray(energies_eV, dtype=float)
    vectors = _normalise_rows(state_vectors)
    if energies.ndim != 2 or vectors.ndim != 3 or energies.shape != vectors.shape[:2]:
        raise ValueError("energies (nk,nstate) and state_vectors (nk,nstate,nfeature) disagree")
    nk, nstates = energies.shape
    if not 1 <= ntrack <= nstates:
        raise ValueError("ntrack must be between one and nstates")
    index = np.empty((nk, ntrack), dtype=int)
    score = np.ones((nk, ntrack), dtype=float)
    margin = np.ones((nk, ntrack), dtype=float)
    confidence = np.full((nk, ntrack), "high", dtype=object)
    index[0] = np.arange(ntrack)
    scale = max(float(np.ptp(energies)), 1e-9)
    for ik in range(1, nk):
        previous = vectors[ik - 1, index[ik - 1]]
        overlap = np.abs(previous.conj() @ vectors[ik].T) ** 2
        energy_delta = np.abs(energies[ik - 1, index[ik - 1], None] - energies[ik][None, :]) / scale
        merit = overlap - float(energy_tie_break_weight) * energy_delta
        rows, cols = linear_sum_assignment(-merit)
        ordered = cols[np.argsort(rows)]
        index[ik] = ordered
        for tracked, raw in enumerate(ordered):
            this = float(overlap[tracked, raw])
            alternatives = np.delete(overlap[tracked], raw)
            this_margin = this - (float(np.max(alternatives)) if alternatives.size else 0.0)
            score[ik, tracked] = this
            margin[ik, tracked] = this_margin
            if this < minimum_overlap or this_margin < minimum_margin:
                confidence[ik, tracked] = "ambiguous"
            elif this < 0.85 or this_margin < 0.30:
                confidence[ik, tracked] = "medium"
    return TrackingResult(index, score, margin, confidence)


def reorder(values: np.ndarray, tracking: TrackingResult) -> np.ndarray:
    values = np.asarray(values)
    return np.stack([values[k, tracking.tracked_raw_indices[k]] for k in range(values.shape[0])])

