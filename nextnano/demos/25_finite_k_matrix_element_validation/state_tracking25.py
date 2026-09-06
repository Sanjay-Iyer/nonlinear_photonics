"""Character-based state tracking across k for Demo 25.

Demo 23 tracked states largely by energy order. That is exactly what produced
the Demo 24 finding that the selected `hh2` was 97.6% light-hole: an ordering
rule cannot tell HH from LH. Demo 25 therefore assigns identity from spinor
character and wavefunction overlap first, and uses energy only to break ties.

Nothing here invents data. When the finite-k spinors for a k point are absent
the caller gets an exception from ``kp8_finite_k_io``; this module never
extrapolates a label across a gap it cannot see.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from kp8_finite_k_io import KPointStates, overlap


BANDS = ("CB", "HH", "LH", "SO")


@dataclass(frozen=True)
class TrackedState:
    label: str                 # e1, e2, hh1, hh2, lh1, ...
    k_index: int
    state_index: int
    energy_eV: float
    fractions: dict[str, float]
    overlap_with_previous: float
    assignment_margin: float
    dominant_band: str
    confined: bool
    note: str = ""

    @property
    def score(self) -> float:
        """Tracking confidence: overlap continuity weighted by character purity."""
        return float(self.overlap_with_previous * self.fractions.get(self.dominant_band, 0.0))


def classify(states: KPointStates, index: int) -> tuple[str, dict[str, float], float]:
    """Dominant band, all four fractions, and the margin over the runner-up."""
    fractions = states.band_fractions()[index]
    order = np.argsort(fractions)[::-1]
    dominant = BANDS[int(order[0])]
    margin = float(fractions[order[0]] - fractions[order[1]])
    return dominant, {b: float(f) for b, f in zip(BANDS, fractions)}, margin


def is_confined(energy_eV: float, band: str, *, barrier_conduction_edge_eV: float,
                barrier_valence_edge_eV: float) -> bool:
    """Bound if the state sits inside the barrier gap on its own side.

    Electron-like states must lie below the barrier conduction edge; hole-like
    states must lie above the barrier valence edge. A state outside its own
    limit is barrier- or continuum-like and, with Dirichlet walls, is a box
    state whose energy is set partly by the quantum-region width.
    """
    if band == "CB":
        return float(energy_eV) < float(barrier_conduction_edge_eV)
    return float(energy_eV) > float(barrier_valence_edge_eV)


def _label_pool(dominant: str, used: dict[str, int]) -> str:
    prefix = {"CB": "e", "HH": "hh", "LH": "lh", "SO": "so"}[dominant]
    used[prefix] = used.get(prefix, 0) + 1
    return f"{prefix}{used[prefix]}"


def seed_labels(states: KPointStates, *, barrier_conduction_edge_eV: float,
                barrier_valence_edge_eV: float) -> dict[int, TrackedState]:
    """Label the k=0 states by character, then by energy within each character.

    Electron-like states are numbered upward in energy; hole-like states are
    numbered downward, which is the usual subband convention and the one Demo
    23/24 used.
    """
    fractions = states.band_fractions()
    dominant = [BANDS[int(np.argmax(row))] for row in fractions]
    order_electron = sorted((i for i, b in enumerate(dominant) if b == "CB"),
                            key=lambda i: states.energies_eV[i])
    holes = [i for i, b in enumerate(dominant) if b in ("HH", "LH", "SO")]
    order_hole = sorted(holes, key=lambda i: -states.energies_eV[i])
    used: dict[str, int] = {}
    tracked: dict[int, TrackedState] = {}
    for index in list(order_electron) + list(order_hole):
        band, values, margin = classify(states, index)
        tracked[index] = TrackedState(
            label=_label_pool(band, used), k_index=states.k_index, state_index=index,
            energy_eV=float(states.energies_eV[index]), fractions=values,
            overlap_with_previous=1.0, assignment_margin=margin, dominant_band=band,
            confined=is_confined(states.energies_eV[index], band,
                                 barrier_conduction_edge_eV=barrier_conduction_edge_eV,
                                 barrier_valence_edge_eV=barrier_valence_edge_eV),
            note="seeded at the first k point")
    return tracked


def propagate(previous_states: KPointStates, previous: Mapping[int, TrackedState],
              states: KPointStates, *, barrier_conduction_edge_eV: float,
              barrier_valence_edge_eV: float,
              energy_tie_break_eV: float = 0.01) -> dict[int, TrackedState]:
    """Carry labels to the next k by maximum spinor overlap, not by energy order.

    The cost matrix is |<prev|next>| with a small energy-proximity bonus, and
    the assignment is greedy on the strongest match. The runner-up gap is kept
    as ``assignment_margin`` so an ambiguous hand-off is visible rather than
    silently resolved.
    """
    labels = sorted(previous, key=lambda i: previous[i].label)
    cost = np.zeros((len(labels), states.n_states))
    for row, prev_index in enumerate(labels):
        for col in range(states.n_states):
            value = abs(_cross_overlap(previous_states, prev_index, states, col))
            gap = abs(float(states.energies_eV[col]) - previous[prev_index].energy_eV)
            cost[row, col] = value - energy_tie_break_eV * gap
    tracked: dict[int, TrackedState] = {}
    taken: set[int] = set()
    for row in np.argsort(-cost.max(axis=1)):
        prev_index = labels[int(row)]
        candidates = [c for c in np.argsort(-cost[row]) if int(c) not in taken]
        if not candidates:
            continue
        best = int(candidates[0])
        runner = float(cost[row, candidates[1]]) if len(candidates) > 1 else 0.0
        taken.add(best)
        band, values, purity_margin = classify(states, best)
        tracked[best] = TrackedState(
            label=previous[prev_index].label, k_index=states.k_index, state_index=best,
            energy_eV=float(states.energies_eV[best]), fractions=values,
            overlap_with_previous=float(abs(_cross_overlap(previous_states, prev_index, states, best))),
            assignment_margin=float(cost[row, best] - runner), dominant_band=band,
            confined=is_confined(states.energies_eV[best], band,
                                 barrier_conduction_edge_eV=barrier_conduction_edge_eV,
                                 barrier_valence_edge_eV=barrier_valence_edge_eV),
            note=("character changed from "
                  f"{previous[prev_index].dominant_band} to {band}"
                  if band != previous[prev_index].dominant_band else ""))
    return tracked


def _cross_overlap(a_states: KPointStates, a: int, b_states: KPointStates, b: int) -> complex:
    """<a(k_i) | b(k_j)> on the shared z grid."""
    if len(a_states.z_nm) != len(b_states.z_nm):
        raise ValueError("state tracking needs a common z grid across k points")
    components = min(a_states.spinor.shape[1], b_states.spinor.shape[1])
    integrand = np.sum(np.conj(a_states.spinor[a, :components, :])
                       * b_states.spinor[b, :components, :], axis=0)
    return complex(np.trapezoid(integrand, a_states.z_nm))


def track(series: Sequence[KPointStates], *, barrier_conduction_edge_eV: float,
          barrier_valence_edge_eV: float) -> list[dict[int, TrackedState]]:
    """Track every state across an ordered series of k points."""
    if not series:
        return []
    out = [seed_labels(series[0], barrier_conduction_edge_eV=barrier_conduction_edge_eV,
                       barrier_valence_edge_eV=barrier_valence_edge_eV)]
    for previous, current in zip(series, series[1:]):
        out.append(propagate(previous, out[-1], current,
                             barrier_conduction_edge_eV=barrier_conduction_edge_eV,
                             barrier_valence_edge_eV=barrier_valence_edge_eV))
    return out


def rows(tracked: Sequence[Mapping[int, TrackedState]],
         k_per_nm: Sequence[float] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step, mapping in enumerate(tracked):
        k = float(k_per_nm[step]) if k_per_nm is not None and step < len(k_per_nm) else float("nan")
        for state in sorted(mapping.values(), key=lambda s: s.label):
            out.append({
                "k_index": state.k_index, "k_per_nm": k, "state": state.label,
                "solver_index": state.state_index, "energy_eV": state.energy_eV,
                "CB fraction": state.fractions["CB"], "HH fraction": state.fractions["HH"],
                "LH fraction": state.fractions["LH"], "SO fraction": state.fractions["SO"],
                "dominant_band": state.dominant_band,
                "overlap_with_previous_k": state.overlap_with_previous,
                "assignment_margin": state.assignment_margin,
                "tracking_score": state.score, "confined": state.confined,
                "note": state.note,
            })
    return out


def detect_events(tracked: Sequence[Mapping[int, TrackedState]], *,
                  min_score: float = 0.60, min_margin: float = 0.15) -> list[dict[str, Any]]:
    """Crossings, avoided crossings, character changes and loss of confinement."""
    events: list[dict[str, Any]] = []
    for step, mapping in enumerate(tracked):
        for state in mapping.values():
            if state.note.startswith("character changed"):
                events.append({"k_index": state.k_index, "state": state.label,
                               "event": "character change", "detail": state.note,
                               "score": state.score})
            if state.overlap_with_previous < min_score and step > 0:
                events.append({"k_index": state.k_index, "state": state.label,
                               "event": "weak continuity (possible crossing)",
                               "detail": f"overlap {state.overlap_with_previous:.3f} < {min_score}",
                               "score": state.score})
            if state.assignment_margin < min_margin and step > 0:
                events.append({"k_index": state.k_index, "state": state.label,
                               "event": "ambiguous assignment (avoided crossing)",
                               "detail": f"margin {state.assignment_margin:.3f} < {min_margin}",
                               "score": state.score})
            if not state.confined:
                events.append({"k_index": state.k_index, "state": state.label,
                               "event": "loss of confinement",
                               "detail": f"{state.dominant_band}-like state outside the barrier gap",
                               "score": state.score})
    return events
