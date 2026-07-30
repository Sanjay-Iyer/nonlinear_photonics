"""Physical analysis of nextnano++ quantum states.

Everything here is a pure function of arrays that were parsed from solver
output, so the whole module is testable at home against fixtures.  The rules the
demos rely on:

* a state is never called "bound", "symmetric", or "heavy-hole-like" because of
  its eigenvalue index -- always because of an integrated, thresholded quantity;
* wavefunction amplitude, probability density, and energy are kept in separate
  quantities with separate units and are never added together except explicitly
  for display;
* tracking a state across a sweep uses envelope overlap first and physical
  features second, and always reports a confidence that can fail a run.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

try:  # optimal assignment when SciPy is present (it is in the pinned env)
    from scipy.optimize import linear_sum_assignment as _linear_sum_assignment
except Exception:  # pragma: no cover - exercised only without SciPy
    _linear_sum_assignment = None


class AnalysisError(RuntimeError):
    """Raised when parsed states cannot be interpreted physically."""


def _check_grid(x: np.ndarray) -> np.ndarray:
    grid = np.asarray(x, dtype=float)
    if grid.ndim != 1 or grid.size < 3:
        raise AnalysisError("position axis must be a 1D array with >= 3 samples.")
    if not np.all(np.diff(grid) > 0):
        raise AnalysisError("position axis must be strictly increasing.")
    return grid


def integrate(x: np.ndarray, values: np.ndarray) -> float:
    """Trapezoidal integral, used everywhere so normalisation is consistent."""

    return float(np.trapezoid(np.asarray(values, dtype=float), _check_grid(x)))


def normalise_density(
    x: np.ndarray, density: np.ndarray
) -> tuple[np.ndarray, float]:
    """Return ``(normalised_density, raw_integral)`` for a |psi|^2 column."""

    grid = _check_grid(x)
    raw = np.asarray(density, dtype=float)
    if raw.shape != grid.shape:
        raise AnalysisError("density and position arrays must have the same length.")
    clipped = np.maximum(raw, 0.0)
    integral = float(np.trapezoid(clipped, grid))
    if not math.isfinite(integral) or integral <= 0:
        raise AnalysisError(f"probability density has invalid norm {integral!r}.")
    return clipped / integral, integral


def normalise_envelope(x: np.ndarray, envelope: np.ndarray) -> tuple[np.ndarray, float]:
    """Return ``(normalised_envelope, raw_integral_of_square)``.

    The sign of the envelope is preserved: parity and overlap-based tracking both
    need it.  The sign convention is fixed by making the largest-magnitude sample
    positive, so that an arbitrary solver-side sign flip between two sweep points
    cannot be mistaken for a physical change.
    """

    grid = _check_grid(x)
    raw = np.asarray(envelope, dtype=float)
    if raw.shape != grid.shape:
        raise AnalysisError("envelope and position arrays must have the same length.")
    integral = float(np.trapezoid(raw**2, grid))
    if not math.isfinite(integral) or integral <= 0:
        raise AnalysisError(f"envelope has invalid squared norm {integral!r}.")
    normalised = raw / math.sqrt(integral)
    peak = int(np.argmax(np.abs(normalised)))
    if normalised[peak] < 0:
        normalised = -normalised
    return normalised, integral


def region_probability(
    x: np.ndarray, density: np.ndarray, start_nm: float, end_nm: float
) -> float:
    """Integrated probability inside ``[start_nm, end_nm]``.

    Interpolating onto the exact interval edges matters: with a coarse grid a
    plain mask can miss or double-count a well edge by a full cell.
    """

    grid = _check_grid(x)
    values = np.asarray(density, dtype=float)
    low, high = float(min(start_nm, end_nm)), float(max(start_nm, end_nm))
    low = max(low, float(grid[0]))
    high = min(high, float(grid[-1]))
    if high <= low:
        return 0.0
    inside = (grid > low) & (grid < high)
    nodes = np.concatenate(([low], grid[inside], [high]))
    sampled = np.concatenate(
        ([float(np.interp(low, grid, values))], values[inside], [float(np.interp(high, grid, values))])
    )
    return float(np.trapezoid(sampled, nodes))


def centroid_nm(x: np.ndarray, density: np.ndarray) -> float:
    """<z> of a normalised probability density, in nm."""

    grid = _check_grid(x)
    values = np.asarray(density, dtype=float)
    norm = float(np.trapezoid(values, grid))
    if not math.isfinite(norm) or norm <= 0:
        raise AnalysisError("cannot take a centroid of a non-positive density.")
    return float(np.trapezoid(grid * values, grid) / norm)


def boundary_probability(
    x: np.ndarray, density: np.ndarray, *, edge_fraction: float = 0.05
) -> float:
    """Probability within ``edge_fraction`` of each end of the domain."""

    grid = _check_grid(x)
    if not 0 < edge_fraction < 0.5:
        raise AnalysisError("edge_fraction must lie in (0, 0.5).")
    span = float(grid[-1] - grid[0])
    left = region_probability(grid, density, grid[0], grid[0] + edge_fraction * span)
    right = region_probability(grid, density, grid[-1] - edge_fraction * span, grid[-1])
    return float(left + right)


def overlap(x: np.ndarray, psi_a: np.ndarray, psi_b: np.ndarray) -> float:
    """<psi_a|psi_b> for two real envelopes sampled on the same grid."""

    grid = _check_grid(x)
    a = np.asarray(psi_a, dtype=float)
    b = np.asarray(psi_b, dtype=float)
    if a.shape != grid.shape or b.shape != grid.shape:
        raise AnalysisError("envelopes must share the position grid.")
    return float(np.trapezoid(a * b, grid))


def position_matrix_element_nm(
    x: np.ndarray, psi_i: np.ndarray, psi_j: np.ndarray
) -> float:
    """z_ij = <psi_i| z |psi_j> in nm, for real normalised envelopes.

    This is the envelope-derived cross-check of the solver's own
    ``dipole_moment_matrix_elements`` output.  Both are reported; a large
    disagreement is a defect, not a detail.
    """

    grid = _check_grid(x)
    a = np.asarray(psi_i, dtype=float)
    b = np.asarray(psi_j, dtype=float)
    if a.shape != grid.shape or b.shape != grid.shape:
        raise AnalysisError("envelopes must share the position grid.")
    return float(np.trapezoid(a * grid * b, grid))


def parity(
    x: np.ndarray, envelope: np.ndarray, *, centre_nm: float
) -> tuple[str, float]:
    """Classify an envelope about ``centre_nm`` as symmetric/antisymmetric.

    Returns ``(label, confidence)``.  ``confidence`` is |<psi|P psi>| where P is
    reflection about the centre; it degrades smoothly for an asymmetric
    structure, and the label becomes ``"mixed"`` below 0.5.
    """

    grid = _check_grid(x)
    values = np.asarray(envelope, dtype=float)
    reflected = np.interp(
        2.0 * float(centre_nm) - grid, grid, values, left=0.0, right=0.0
    )
    # reflected[k] = psi(2*centre - x_k), so this is <psi|P psi> on the same grid.
    projection = float(np.trapezoid(values * reflected, grid))
    norm = float(np.trapezoid(values**2, grid))
    if norm <= 0:
        raise AnalysisError("cannot classify parity of a zero envelope.")
    value = projection / norm
    confidence = abs(value)
    if confidence < 0.5:
        return "mixed", confidence
    return ("symmetric" if value > 0 else "antisymmetric"), confidence


@dataclass
class StateObservables:
    """Everything the demos record about one quantum state."""

    index: int
    energy_eV: float
    raw_probability_integral: float
    normalised: bool
    centroid_nm: float
    boundary_probability: float
    region_probabilities: dict[str, float] = field(default_factory=dict)
    parity_label: str | None = None
    parity_confidence: float | None = None
    bound: bool | None = None
    bound_reason: str = ""
    character: str | None = None
    component_weights: dict[str, float] = field(default_factory=dict)

    def as_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "state": self.index,
            "energy_eV": self.energy_eV,
            "raw_probability_integral": self.raw_probability_integral,
            "normalised": self.normalised,
            "centroid_nm": self.centroid_nm,
            "boundary_probability": self.boundary_probability,
            "parity_label": self.parity_label,
            "parity_confidence": self.parity_confidence,
            "bound": self.bound,
            "bound_reason": self.bound_reason,
            "character": self.character,
        }
        row.update(
            {f"probability_{name}": value for name, value in self.region_probabilities.items()}
        )
        row.update(
            {f"weight_{name}": value for name, value in self.component_weights.items()}
        )
        return row


def analyse_states(
    x: np.ndarray,
    energies: Sequence[float],
    densities: np.ndarray,
    *,
    regions: Mapping[str, tuple[float, float]],
    envelopes: np.ndarray | None = None,
    barrier_edge_eV: float | None = None,
    minimum_bound_probability: float = 0.5,
    normalisation_tolerance: float = 1e-3,
    boundary_edge_fraction: float = 0.05,
    symmetry_centre_nm: float | None = None,
) -> list[StateObservables]:
    """Turn parsed columns into per-state physical observables.

    ``densities`` and ``envelopes`` are ``(n_points, n_states)`` arrays.  Bound
    classification requires *both* an energy below ``barrier_edge_eV`` and enough
    probability inside the confining layers; when the barrier edge is unknown the
    energy half of the test is skipped and the reason records that.
    """

    grid = _check_grid(x)
    density_matrix = np.atleast_2d(np.asarray(densities, dtype=float))
    if density_matrix.shape[0] != grid.size:
        density_matrix = density_matrix.T
    if density_matrix.shape[0] != grid.size:
        raise AnalysisError("probability array does not match the position grid.")
    envelope_matrix: np.ndarray | None = None
    if envelopes is not None:
        envelope_matrix = np.atleast_2d(np.asarray(envelopes, dtype=float))
        if envelope_matrix.shape[0] != grid.size:
            envelope_matrix = envelope_matrix.T
        if envelope_matrix.shape[0] != grid.size:
            raise AnalysisError("envelope array does not match the position grid.")

    confining = [
        name for name in regions if "well" in name or "core" in name or "wire" in name
    ] or list(regions)

    results: list[StateObservables] = []
    count = min(len(energies), density_matrix.shape[1])
    for index in range(count):
        normalised, raw_integral = normalise_density(grid, density_matrix[:, index])
        region_probabilities = {
            name: region_probability(grid, normalised, *bounds)
            for name, bounds in regions.items()
        }
        confined = sum(region_probabilities[name] for name in confining)
        energy = float(energies[index])
        reasons: list[str] = []
        energy_ok = True
        if barrier_edge_eV is not None:
            energy_ok = energy < float(barrier_edge_eV)
            if not energy_ok:
                reasons.append("energy is above the barrier edge")
        else:
            reasons.append("barrier edge unknown; energy criterion skipped")
        probability_ok = confined >= minimum_bound_probability
        if not probability_ok:
            reasons.append(
                f"confined probability {confined:.4f} < {minimum_bound_probability}"
            )
        parity_label: str | None = None
        parity_confidence: float | None = None
        if envelope_matrix is not None and symmetry_centre_nm is not None:
            parity_label, parity_confidence = parity(
                grid, envelope_matrix[:, index], centre_nm=symmetry_centre_nm
            )
        results.append(
            StateObservables(
                index=index + 1,
                energy_eV=energy,
                raw_probability_integral=raw_integral,
                normalised=abs(raw_integral - 1.0) <= normalisation_tolerance,
                centroid_nm=centroid_nm(grid, normalised),
                boundary_probability=boundary_probability(
                    grid, normalised, edge_fraction=boundary_edge_fraction
                ),
                region_probabilities=region_probabilities,
                parity_label=parity_label,
                parity_confidence=parity_confidence,
                bound=bool(energy_ok and probability_ok),
                bound_reason="; ".join(reasons) or "energy below barrier and well-confined",
            )
        )
    return results


def energy_splittings_meV(energies: Sequence[float]) -> dict[str, float]:
    """Adjacent and 1-3 splittings in meV, keyed ``E21``, ``E32``, ``E31``."""

    values = [float(value) for value in energies]
    result: dict[str, float] = {}
    if len(values) >= 2:
        result["E21_meV"] = 1000.0 * (values[1] - values[0])
    if len(values) >= 3:
        result["E32_meV"] = 1000.0 * (values[2] - values[1])
        result["E31_meV"] = 1000.0 * (values[2] - values[0])
    return result


# --------------------------------------------------------------------------
# state tracking across a sweep
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TrackingResult:
    """Assignment of this sweep point's states onto the previous point's."""

    assignment: tuple[int, ...]
    confidence: tuple[float, ...]
    method: str
    minimum_confidence: float
    ambiguous: tuple[int, ...]
    similarity_matrix: tuple[tuple[float, ...], ...] = ()

    @property
    def is_confident(self) -> bool:
        return not self.ambiguous


def _assign(cost: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if _linear_sum_assignment is not None:
        return _linear_sum_assignment(cost)
    # Deterministic greedy fallback over globally sorted pairs.
    rows, cols = cost.shape
    order = np.dstack(np.unravel_index(np.argsort(cost, axis=None), cost.shape))[0]
    used_rows: set[int] = set()
    used_cols: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for row, col in order:
        if int(row) in used_rows or int(col) in used_cols:
            continue
        used_rows.add(int(row))
        used_cols.add(int(col))
        pairs.append((int(row), int(col)))
        if len(pairs) == min(rows, cols):
            break
    pairs.sort()
    return (
        np.asarray([pair[0] for pair in pairs]),
        np.asarray([pair[1] for pair in pairs]),
    )


def track_states(
    *,
    x: np.ndarray | None = None,
    previous_envelopes: np.ndarray | None = None,
    current_envelopes: np.ndarray | None = None,
    previous_features: Sequence[Sequence[float]] | None = None,
    current_features: Sequence[Sequence[float]] | None = None,
    minimum_confidence: float = 0.6,
) -> TrackingResult:
    """Map current states onto previous states; never trust the index alone.

    Preferred similarity is |<psi_prev|psi_cur>|, which is exactly 1 for an
    unchanged state and drops through an avoided crossing.  When envelopes are
    unavailable the fallback is a normalised distance in a physical feature
    vector (centroid, per-well probabilities, energy).  Either way the caller
    receives per-state confidences and the indices that fell below the
    threshold, so an ambiguous point can be flagged instead of silently
    reordered.
    """

    if previous_envelopes is not None and current_envelopes is not None and x is not None:
        grid = _check_grid(x)
        previous = np.atleast_2d(np.asarray(previous_envelopes, dtype=float))
        current = np.atleast_2d(np.asarray(current_envelopes, dtype=float))
        if previous.shape[0] != grid.size:
            previous = previous.T
        if current.shape[0] != grid.size:
            current = current.T
        # Both sets are normalised first. Without that the "confidence" is not a
        # bounded overlap at all -- it can exceed 1 and sail past any threshold,
        # which would defeat the whole point of reporting a confidence.
        previous = np.column_stack(
            [normalise_envelope(grid, previous[:, i])[0] for i in range(previous.shape[1])]
        )
        current = np.column_stack(
            [normalise_envelope(grid, current[:, j])[0] for j in range(current.shape[1])]
        )
        similarity = np.zeros((previous.shape[1], current.shape[1]), dtype=float)
        for i in range(previous.shape[1]):
            for j in range(current.shape[1]):
                similarity[i, j] = min(
                    1.0, abs(overlap(grid, previous[:, i], current[:, j]))
                )
        method = "envelope_overlap"
    elif previous_features is not None and current_features is not None:
        previous_array = np.atleast_2d(np.asarray(previous_features, dtype=float))
        current_array = np.atleast_2d(np.asarray(current_features, dtype=float))
        if previous_array.shape[1] != current_array.shape[1]:
            raise AnalysisError("feature vectors must have the same dimension.")
        scale = np.maximum(
            np.abs(np.concatenate([previous_array, current_array])).max(axis=0), 1e-12
        )
        distance = np.linalg.norm(
            (previous_array[:, None, :] - current_array[None, :, :]) / scale, axis=2
        )
        similarity = 1.0 / (1.0 + distance)
        method = "feature_distance"
    else:
        raise AnalysisError(
            "state tracking needs either envelopes with a grid, or feature vectors."
        )

    rows, cols = _assign(-similarity)
    n_current = similarity.shape[1]
    assignment = [-1] * n_current
    confidence = [0.0] * n_current
    for row, col in zip(rows, cols):
        assignment[int(col)] = int(row)
        confidence[int(col)] = float(similarity[int(row), int(col)])
    ambiguous = tuple(
        index for index, value in enumerate(confidence) if value < minimum_confidence
    )
    return TrackingResult(
        assignment=tuple(assignment),
        confidence=tuple(confidence),
        method=method,
        minimum_confidence=float(minimum_confidence),
        ambiguous=ambiguous,
        similarity_matrix=tuple(
            tuple(float(value) for value in row) for row in similarity
        ),
    )


def detect_avoided_crossings(
    parameter_values: Sequence[float],
    branch_energies: Sequence[Sequence[float]],
    *,
    minimum_gap_meV: float = 1.0,
    relative_curvature: float = 0.25,
) -> list[dict[str, Any]]:
    """Flag sweep points where two tracked branches approach and repel.

    A point is flagged when the gap between two branches is a local minimum
    along the sweep, is at most ``minimum_gap_meV``, and both neighbouring gaps
    are at least ``(1 + relative_curvature)`` times as large -- i.e. the gap
    rises by at least that relative amount on each side.  A larger
    ``relative_curvature`` demands a sharper dip.

    This is a *flag for human inspection*, not a proof.  A genuine avoided
    crossing has to be confirmed by looking at the envelopes there: both states
    should be delocalised across the structure at the minimum.
    """

    values = np.asarray(parameter_values, dtype=float)
    energies = np.asarray(branch_energies, dtype=float)
    if energies.ndim != 2 or energies.shape[0] != values.size:
        raise AnalysisError("branch_energies must be (n_points, n_branches).")
    order = np.argsort(values)
    values = values[order]
    energies = energies[order]
    flags: list[dict[str, Any]] = []
    for lower in range(energies.shape[1] - 1):
        for upper in range(lower + 1, energies.shape[1]):
            gaps = np.abs(energies[:, upper] - energies[:, lower]) * 1000.0
            for point in range(1, len(gaps) - 1):
                gap = float(gaps[point])
                neighbours = (float(gaps[point - 1]), float(gaps[point + 1]))
                if gap > minimum_gap_meV:
                    continue
                if not (gap < neighbours[0] and gap < neighbours[1]):
                    continue
                if min(neighbours) < (1.0 + relative_curvature) * gap:
                    continue
                flags.append(
                    {
                        "parameter_value": float(values[point]),
                        "branch_lower": lower + 1,
                        "branch_upper": upper + 1,
                        "minimum_gap_meV": gap,
                        "neighbour_gaps_meV": list(neighbours),
                    }
                )
    return flags


# --------------------------------------------------------------------------
# 2D cross-section diagnostics (Demo 10)
# --------------------------------------------------------------------------


def _check_2d(
    x_nm: np.ndarray, y_nm: np.ndarray, values: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = _check_grid(x_nm)
    y = _check_grid(y_nm)
    array = np.asarray(values, dtype=float)
    if array.shape == (y.size, x.size):
        return x, y, array
    if array.shape == (x.size, y.size):
        return x, y, array.T
    raise AnalysisError(
        f"2D field shape {array.shape} matches neither (ny, nx) = "
        f"({y.size}, {x.size}) nor its transpose."
    )


def normalise_density_2d(
    x_nm: np.ndarray, y_nm: np.ndarray, values: np.ndarray
) -> tuple[np.ndarray, float]:
    """Normalise a 2D probability density to unit integral over the section."""

    x, y, array = _check_2d(x_nm, y_nm, values)
    clipped = np.maximum(array, 0.0)
    integral = float(np.trapezoid(np.trapezoid(clipped, x, axis=1), y))
    if not math.isfinite(integral) or integral <= 0:
        raise AnalysisError(f"2D density has invalid norm {integral!r}.")
    return clipped / integral, integral


def centroid_2d(
    x_nm: np.ndarray, y_nm: np.ndarray, values: np.ndarray
) -> tuple[float, float]:
    """(<x>, <y>) of a 2D density, in nm."""

    x, y, array = _check_2d(x_nm, y_nm, values)
    total = float(np.trapezoid(np.trapezoid(array, x, axis=1), y))
    if total <= 0:
        raise AnalysisError("cannot take a centroid of a non-positive 2D density.")
    mean_x = float(np.trapezoid(np.trapezoid(array * x[None, :], x, axis=1), y) / total)
    mean_y = float(np.trapezoid(np.trapezoid(array, x, axis=1) * y, y) / total)
    return mean_x, mean_y


def boundary_probability_2d(
    x_nm: np.ndarray,
    y_nm: np.ndarray,
    values: np.ndarray,
    *,
    edge_fraction: float = 0.05,
) -> float:
    """Probability inside a frame of relative width ``edge_fraction``."""

    x, y, array = _check_2d(x_nm, y_nm, values)
    if not 0 < edge_fraction < 0.5:
        raise AnalysisError("edge_fraction must lie in (0, 0.5).")
    span_x = float(x[-1] - x[0])
    span_y = float(y[-1] - y[0])
    interior = (
        (x >= x[0] + edge_fraction * span_x)
        & (x <= x[-1] - edge_fraction * span_x)
    )[None, :] & (
        (y >= y[0] + edge_fraction * span_y)
        & (y <= y[-1] - edge_fraction * span_y)
    )[
        :, None
    ]
    total = float(np.trapezoid(np.trapezoid(array, x, axis=1), y))
    inside = np.where(interior, array, 0.0)
    inner = float(np.trapezoid(np.trapezoid(inside, x, axis=1), y))
    if total <= 0:
        raise AnalysisError("cannot measure boundary probability of an empty density.")
    return float(max(0.0, (total - inner) / total))


def symmetry_error(
    x_nm: np.ndarray, y_nm: np.ndarray, values: np.ndarray, *, axis: str
) -> float:
    """Relative reflection asymmetry about the centre of one axis.

    Returns ``max|f - Pf| / max|f|``.  For a geometry that is symmetric by
    construction, a value well above the numerical noise floor means the *mesh*
    broke the symmetry, not the physics.
    """

    x, y, array = _check_2d(x_nm, y_nm, values)
    if axis == "x":
        flipped = array[:, ::-1]
        centred = np.allclose(x - x[0], x[-1] - x[::-1], atol=1e-9)
    elif axis == "y":
        flipped = array[::-1, :]
        centred = np.allclose(y - y[0], y[-1] - y[::-1], atol=1e-9)
    else:
        raise AnalysisError("axis must be 'x' or 'y'.")
    if not centred:
        raise AnalysisError(
            f"the {axis} grid is not symmetric about its centre, so a reflection "
            "asymmetry cannot be separated from a non-uniform mesh."
        )
    peak = float(np.max(np.abs(array)))
    if peak <= 0:
        raise AnalysisError("cannot measure symmetry of an empty density.")
    return float(np.max(np.abs(array - flipped)) / peak)


def slice_2d(
    x_nm: np.ndarray,
    y_nm: np.ndarray,
    values: np.ndarray,
    *,
    axis: str,
    position_nm: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Take a horizontal or vertical cut through a 2D field.

    ``axis='x'`` returns the profile along x at fixed y (a horizontal cut).
    ``position_nm`` defaults to the centre of the other axis.
    """

    x, y, array = _check_2d(x_nm, y_nm, values)
    if axis == "x":
        target = 0.5 * (y[0] + y[-1]) if position_nm is None else float(position_nm)
        index = int(np.argmin(np.abs(y - target)))
        return x, array[index, :]
    if axis == "y":
        target = 0.5 * (x[0] + x[-1]) if position_nm is None else float(position_nm)
        index = int(np.argmin(np.abs(x - target)))
        return y, array[:, index]
    raise AnalysisError("axis must be 'x' or 'y'.")


def classify_character(
    weights: Mapping[str, float], *, dominant_threshold: float = 0.6
) -> tuple[str, float]:
    """Label a multiband state from its component weights.

    ``("mixed", w)`` is returned whenever no component reaches
    ``dominant_threshold``.  Calling a state "HH1" because it is the first hole
    eigenstate is exactly the mistake this replaces.
    """

    if not weights:
        raise AnalysisError("component weights are required to classify a state.")
    total = sum(float(value) for value in weights.values())
    if not math.isfinite(total) or total <= 0:
        raise AnalysisError(f"component weights must sum to a positive value, got {total!r}.")
    normalised = {name: float(value) / total for name, value in weights.items()}
    label, fraction = max(normalised.items(), key=lambda item: item[1])
    if fraction < dominant_threshold:
        return "mixed", fraction
    return f"{label}-like", fraction


def normalise_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Component weights rescaled to sum to one."""

    total = sum(float(value) for value in weights.values())
    if not math.isfinite(total) or total <= 0:
        raise AnalysisError("component weights must sum to a positive value.")
    return {name: float(value) / total for name, value in weights.items()}


def charge_balance(
    x_nm: np.ndarray,
    *,
    electron_density_cm3: np.ndarray,
    ionized_donor_density_cm3: np.ndarray,
    hole_density_cm3: np.ndarray | None = None,
    ionized_acceptor_density_cm3: np.ndarray | None = None,
) -> dict[str, float]:
    """Sheet densities and net charge, in cm^-2, from volume densities in cm^-3.

    The nm position axis is converted explicitly (1 nm = 1e-7 cm) so the unit of
    every reported number is unambiguous.
    """

    grid = _check_grid(x_nm) * 1e-7  # nm -> cm
    def sheet(values: np.ndarray | None) -> float:
        if values is None:
            return 0.0
        return float(np.trapezoid(np.asarray(values, dtype=float), grid))

    electrons = sheet(electron_density_cm3)
    donors = sheet(ionized_donor_density_cm3)
    holes = sheet(hole_density_cm3)
    acceptors = sheet(ionized_acceptor_density_cm3)
    net = donors + holes - electrons - acceptors
    reference = max(abs(donors), abs(electrons), 1e-30)
    return {
        "electron_sheet_density_cm2": electrons,
        "hole_sheet_density_cm2": holes,
        "ionized_donor_sheet_density_cm2": donors,
        "ionized_acceptor_sheet_density_cm2": acceptors,
        "net_sheet_charge_cm2": net,
        "relative_charge_imbalance": abs(net) / reference,
    }


def classify_convergence(
    iterations: Sequence[float],
    residuals: Mapping[str, Sequence[float]],
    *,
    tolerance: float,
    maximum_iterations: int,
    reference_scales: Mapping[str, float] | None = None,
    solver_reported_failure: bool = False,
) -> dict[str, Any]:
    """Decide whether a self-consistent loop actually converged.

    Three independent facts are combined, in decreasing authority:

    1. **The solver's own verdict.** nextnano++ writes
       "WARNING: ... failed to converge." to ``summary.log`` while still exiting
       successfully and writing ``job_done.txt``. If it says it failed, it
       failed -- no residual arithmetic here overrides that.
    2. **The iteration cap.** Stopping at ``maximum_iterations`` is reported as
       ``max_iterations_reached``, never as ``converged``.
    3. **The residuals.** Compared against ``tolerance``, but each residual is
       first divided by its own ``reference_scales`` entry where one is given.
       A density residual in cm^-2 sits at ~1e12 in absolute terms, so testing
       it against a 1e-6 potential tolerance is a unit error, not a convergence
       criterion.
    """

    steps = [int(value) for value in iterations]
    if not steps:
        return {
            "status": "no_iteration_history",
            "converged": False,
            "iterations_run": 0,
            "final_residuals": {},
            "final_relative_residuals": {},
        }
    scales = dict(reference_scales or {})
    finals: dict[str, float] = {}
    relatives: dict[str, float] = {}
    for name, values in residuals.items():
        series = [float(value) for value in values]
        if not series:
            continue
        finals[name] = series[-1]
        scale = float(scales.get(name, 1.0))
        relatives[name] = abs(series[-1]) / (abs(scale) if scale else 1.0)
    within = bool(relatives) and all(value <= tolerance for value in relatives.values())
    last = max(steps)

    if solver_reported_failure:
        status = "solver_reported_not_converged"
    elif last >= int(maximum_iterations):
        status = "max_iterations_reached"
    elif within:
        status = "converged"
    else:
        status = "stopped_without_meeting_tolerance"
    monotonic = {
        name: bool(np.all(np.diff(np.abs(np.asarray([float(v) for v in values]))) <= 1e-12))
        for name, values in residuals.items()
        if len(list(values)) > 1
    }
    return {
        "status": status,
        "converged": status == "converged",
        "iterations_run": last,
        "maximum_iterations": int(maximum_iterations),
        "tolerance": float(tolerance),
        "reference_scales": scales,
        "final_residuals": finals,
        "final_relative_residuals": relatives,
        "residuals_within_tolerance": within,
        "residual_monotonic": monotonic,
        "solver_reported_failure": bool(solver_reported_failure),
    }
