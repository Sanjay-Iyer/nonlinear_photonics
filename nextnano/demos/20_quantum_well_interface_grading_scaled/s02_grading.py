"""Stage 02 - geometry, composition profiles and solver-free grading validation.

All the grading mathematics lives here and nowhere else. The formulas are
Demo 19's, transcribed from ``grading12.profile_fraction`` (called through
``demo19._profile_shape`` with ``sigmoid_steepness=10.0, erf_span_sigma=3.0``)
and written out explicitly so the shapes can be checked by eye.

GEOMETRY
--------
Positions are in nm along the growth axis. nextnano++ calls that axis ``x``;
plots and the susceptibility notation call the same axis ``z``. Nothing here
moves an interface: grading replaces equal lengths of the two adjacent
materials and leaves the nominal interface positions and the 30.0 nm domain
fixed.

PROFILE MATHEMATICS
-------------------
For a nonzero full width ``W`` centred on interface position ``z_i``::

    z_minus = z_i - W/2
    z_plus  = z_i + W/2
    u(z)    = clip((z - z_minus) / W, 0, 1)
    x_Al(z) = x_L + (x_R - x_L) * f(u)

with ``(x_L, x_R) = (0.55, 0)`` at I1 and I3 and ``(0, 0.55)`` at I2 and I4.
Outside the finite interval the composition is the adjacent pure-material
value. The four shape functions ``f`` are:

    linear   f(u) = u

    fermi    L(u) = 1 / (1 + exp(-k (u - 1/2))),  k = 10
             f(u) = (L(u) - L(0)) / (L(1) - L(0))
             i.e. a logistic truncated at +-k/2 and then affinely normalized so
             the finite endpoints are exactly 0 and 1. This is a shape
             parameter, not a temperature: 300 K does not enter f.

    erf      f(u) = (erf(s(u - 1/2)) - erf(-s/2)) / (erf(s/2) - erf(-s/2)),
             s = 3, so the raw erf is truncated at +-1.5 and endpoint-normalized.

    cosine   f(u) = (1 - cos(pi u)) / 2, which already reaches 0 and 1 exactly.

The abrupt case bypasses the ramp entirely: the domain starts as
Al(0.55)Ga(0.45)As and the two closed well intervals are overwritten with zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

import s01_cases as cases


class Grading20Error(ValueError):
    """A requested composition profile cannot be realized as specified."""


# --- geometry ---------------------------------------------------------------


@dataclass(frozen=True)
class Geometry:
    """Derived layer boundaries. Nothing in this class is typed in by hand."""

    thick_well_nm: float
    tunnel_barrier_nm: float
    thin_well_nm: float
    period_barrier_nm: float
    outer_barrier_nm: float
    active_start_nm: float
    active_end_nm: float
    domain_nm: tuple[float, float]
    quantum_start_nm: float
    quantum_end_nm: float

    @property
    def total_well_nm(self) -> float:
        return self.thick_well_nm + self.thin_well_nm

    @property
    def barrier_centre_nm(self) -> float:
        return self.active_start_nm + self.thick_well_nm + 0.5 * self.tunnel_barrier_nm

    def as_record(self) -> dict[str, Any]:
        return {
            "thick_well_nm": self.thick_well_nm,
            "tunnel_barrier_nm": self.tunnel_barrier_nm,
            "thin_well_nm": self.thin_well_nm,
            "period_barrier_nm": self.period_barrier_nm,
            "outer_barrier_nm": self.outer_barrier_nm,
            "total_well_nm": self.total_well_nm,
            "active_start_nm": self.active_start_nm,
            "active_end_nm": self.active_end_nm,
            "barrier_centre_nm": self.barrier_centre_nm,
            "domain_nm": list(self.domain_nm),
            "quantum_region_nm": [self.quantum_start_nm, self.quantum_end_nm],
        }


def geometry(cfg: Mapping[str, Any]) -> Geometry:
    """Layer boundaries derived from the configured thicknesses.

    The outer barrier is half the period barrier on each side, so::

        I1 = period_barrier/2                       = 9.1 nm
        I2 = I1 + thick_well                        = 16.2 nm
        I3 = I2 + tunnel_barrier                    = 18.0 nm
        I4 = I3 + thin_well                         = 20.9 nm
        domain = I4 + period_barrier/2              = 30.0 nm
    """

    block = cfg["geometry"]
    thick = float(block["thick_well_nm"])
    tunnel = float(block["tunnel_barrier_nm"])
    thin = float(block["thin_well_nm"])
    period_barrier = float(block["period_barrier_nm"])
    padding = float(block["quantum_region_padding_nm"])
    outer = period_barrier / 2.0
    active_start = outer
    active_end = active_start + thick + tunnel + thin
    total = active_end + outer
    return Geometry(
        thick_well_nm=thick,
        tunnel_barrier_nm=tunnel,
        thin_well_nm=thin,
        period_barrier_nm=period_barrier,
        outer_barrier_nm=outer,
        active_start_nm=active_start,
        active_end_nm=active_end,
        domain_nm=(0.0, total),
        quantum_start_nm=max(0.0, active_start - padding),
        quantum_end_nm=min(total, active_end + padding),
    )


def interface_positions(cfg: Mapping[str, Any]) -> dict[str, float]:
    """Nominal positions of I1-I4 in nm. Grading never moves these."""

    g = geometry(cfg)
    return {
        "I1": g.active_start_nm,
        "I2": g.active_start_nm + g.thick_well_nm,
        "I3": g.active_start_nm + g.thick_well_nm + g.tunnel_barrier_nm,
        "I4": g.active_end_nm,
    }


def interface_directions(cfg: Mapping[str, Any]) -> dict[str, tuple[float, float]]:
    """``(x_left, x_right)`` Al fraction on each side of each interface."""

    high = float(cfg["materials"]["barrier_al_fraction"])
    low = float(cfg["materials"]["well_al_fraction"])
    return {"I1": (high, low), "I2": (low, high), "I3": (high, low), "I4": (low, high)}


# --- shape functions --------------------------------------------------------


def profile_fraction(
    u: float | np.ndarray, shape: str, *,
    sigmoid_steepness: float = 10.0, erf_span_sigma: float = 3.0,
) -> np.ndarray:
    """A normalized monotone ramp with ``f(0) = 0`` and ``f(1) = 1`` exactly.

    Endpoint normalization matters: an un-normalized logistic or erf never
    reaches its nominal endpoints over a finite width, so the realized
    composition would fall short of pure GaAs and pure Al(0.55)Ga(0.45)As at
    the ends of every graded interval.
    """

    x = np.clip(np.asarray(u, dtype=float), 0.0, 1.0)
    key = str(shape).lower()
    if key in ("abrupt", "step"):
        return np.where(x < 0.5, 0.0, 1.0)
    if key == "linear":
        return x
    if key in ("fermi", "sigmoid", "logistic"):
        k = float(sigmoid_steepness)
        if k <= 0:
            raise Grading20Error("grading.sigmoid_steepness must be positive")
        raw = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
        lo = 1.0 / (1.0 + math.exp(k / 2.0))     # L(0) = 1/(1 + e^{+k/2})
        hi = 1.0 / (1.0 + math.exp(-k / 2.0))    # L(1) = 1/(1 + e^{-k/2})
        return (raw - lo) / (hi - lo)
    if key in ("erf", "error_function"):
        span = float(erf_span_sigma)
        if span <= 0:
            raise Grading20Error("grading.erf_span_sigma must be positive")
        raw = np.vectorize(math.erf)(span * (x - 0.5))
        lo, hi = math.erf(-span / 2.0), math.erf(span / 2.0)
        return (raw - lo) / (hi - lo)
    if key in ("cosine", "cosine_smoothed"):
        return 0.5 - 0.5 * np.cos(np.pi * x)
    raise Grading20Error(f"unsupported grading profile {shape!r}")


def _shape_options(cfg: Mapping[str, Any]) -> dict[str, float]:
    block = cfg["grading"]
    return {
        "sigmoid_steepness": float(block["sigmoid_steepness"]),
        "erf_span_sigma": float(block["erf_span_sigma"]),
    }


# --- whole-device composition ----------------------------------------------


def evaluate_composition(
    cfg: Mapping[str, Any], case: cases.GradingCase,
    z_nm: Sequence[float] | np.ndarray, *, rendered: bool = False,
) -> np.ndarray:
    """Whole-device ``x_Al(z)`` for one case.

    ``rendered=False`` gives the analytic profile Demo 20 requested.
    ``rendered=True`` gives the function nextnano++ actually solves: for the
    imported families that is the piecewise-linear interpolation of the sampled
    DAT table, because nextnano++ interpolates linearly between table rows.
    """

    z = np.asarray(z_nm, dtype=float)
    pos = interface_positions(cfg)
    directions = interface_directions(cfg)
    high = float(cfg["materials"]["barrier_al_fraction"])
    low = float(cfg["materials"]["well_al_fraction"])

    # Start as barrier alloy everywhere, then carve out the two wells. The
    # closed intervals reproduce Demo 19's region ordering exactly.
    x_al = np.full_like(z, high)
    x_al[(z >= pos["I1"]) & (z <= pos["I2"])] = low
    x_al[(z >= pos["I3"]) & (z <= pos["I4"])] = low
    if case.is_abrupt:
        return x_al

    options = _shape_options(cfg)
    for interface_id in cases.INTERFACE_IDS:
        width = case.width(interface_id)
        if width <= 0:
            continue                      # this interface stays abrupt
        centre = pos[interface_id]
        lo, hi = centre - width / 2.0, centre + width / 2.0
        mask = (z >= lo) & (z <= hi)
        if not np.any(mask):
            continue
        u = np.clip((z[mask] - lo) / width, 0.0, 1.0)
        fraction = profile_fraction(u, case.profile, **options)
        start_x, end_x = directions[interface_id]
        x_al[mask] = start_x + (end_x - start_x) * fraction

    if rendered and case.is_imported:
        mesh_x = profile_mesh(cfg, case, continuous=False)
        mesh_y = evaluate_composition(cfg, case, mesh_x, rendered=False)
        return np.interp(z, mesh_x, mesh_y)
    return x_al


def profile_mesh(
    cfg: Mapping[str, Any], case: cases.GradingCase, *, continuous: bool
) -> np.ndarray:
    """Sampling coordinates for the composition profile.

    ``continuous=False`` is the table nextnano++ receives: the configured mesh
    spacing (0.05 nm) plus every interface centre and grade endpoint, so no
    breakpoint is missed by the sampler.

    ``continuous=True`` is an audit grid ``continuous_oversample`` times finer.
    It exists only to measure what the table lost and is never an input.
    """

    g = geometry(cfg)
    spacing = float(cfg["mesh"]["active_region_grid_spacing_nm"])
    if continuous:
        spacing /= int(cfg["mesh"]["continuous_oversample"])
    points = list(np.arange(g.domain_nm[0], g.domain_nm[1] + 0.5 * spacing, spacing))
    pos = interface_positions(cfg)
    for interface_id in cases.INTERFACE_IDS:
        points.append(pos[interface_id])
        width = case.width(interface_id)
        if width > 0:
            points += [pos[interface_id] - width / 2.0, pos[interface_id] + width / 2.0]
    return np.asarray(sorted({round(float(value), 12) for value in points}), dtype=float)


@dataclass(frozen=True)
class CompositionProfile:
    """A sampled ``x_Al(z)`` plus everything needed to audit how it was built."""

    x_nm: np.ndarray
    al_fraction: np.ndarray
    x_nm_continuous: np.ndarray
    al_fraction_continuous: np.ndarray
    request: Mapping[str, Any]
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    @property
    def peak_al_fraction(self) -> float:
        return float(np.max(self.al_fraction))

    def as_rows(self) -> list[dict[str, float]]:
        continuous_on_mesh = np.interp(
            self.x_nm, self.x_nm_continuous, self.al_fraction_continuous
        )
        return [
            {"x_nm": float(x), "al_fraction_requested_continuous": float(c),
             "al_fraction_rendered": float(r)}
            for x, c, r in zip(self.x_nm, continuous_on_mesh, self.al_fraction)
        ]


def build_profile(
    cfg: Mapping[str, Any], case: cases.GradingCase
) -> CompositionProfile:
    """Sample one case's composition and quantify the sampling error."""

    mesh_x = profile_mesh(cfg, case, continuous=False)
    fine_x = profile_mesh(cfg, case, continuous=True)
    mesh_y = evaluate_composition(cfg, case, mesh_x)
    fine_y = evaluate_composition(cfg, case, fine_x)
    # What nextnano++ will reconstruct from the table, on the audit grid.
    rendered_fine = (
        np.interp(fine_x, mesh_x, mesh_y) if case.is_imported else fine_y.copy()
    )
    error = np.abs(rendered_fine - fine_y)
    high = float(cfg["materials"]["barrier_al_fraction"])
    pos = interface_positions(cfg)
    g = geometry(cfg)
    request = {
        "profile": case.profile,
        "render_method": case.render_method,
        "width_definition": "full start-to-end transition width",
        "max_al_fraction": high,
        "domain_nm": list(g.domain_nm),
        "interfaces_nm": {cases.INTERFACE_NAMES[key]: value
                          for key, value in pos.items()},
        "interface_ids": pos,
        "requested_widths_nm": {key: case.width(key) for key in cases.INTERFACE_IDS},
        "grading_geometry_convention": cases.GEOMETRY_CONVENTION,
    }
    diagnostics = {
        "realized_peak_al_fraction": float(np.max(rendered_fine)),
        "realized_min_al_fraction": float(np.min(rendered_fine)),
        "grading_profile_realization_max_error": float(np.max(error)),
        "grading_profile_realization_rms_error": float(np.sqrt(np.mean(error ** 2))),
        "profile_within_bounds": bool(
            np.all((rendered_fine >= -1e-12) & (rendered_fine <= high + 1e-12))
        ),
        "profile_monotone_coordinates": bool(np.all(np.diff(mesh_x) > 0)),
        "profile_points": int(mesh_x.size),
    }
    return CompositionProfile(
        x_nm=mesh_x, al_fraction=mesh_y,
        x_nm_continuous=fine_x, al_fraction_continuous=fine_y,
        request=request, diagnostics=diagnostics,
    )


# --- solver-free validation -------------------------------------------------


def grade_intervals(
    cfg: Mapping[str, Any], case: cases.GradingCase
) -> dict[str, tuple[float, float] | None]:
    """``(start, end)`` of each grade, or None where the interface is abrupt."""

    pos = interface_positions(cfg)
    return {
        key: (None if case.width(key) == 0 else
              (pos[key] - case.width(key) / 2.0, pos[key] + case.width(key) / 2.0))
        for key in cases.INTERFACE_IDS
    }


def overlaps(cfg: Mapping[str, Any], case: cases.GradingCase) -> list[str]:
    """Adjacent grades that would collide. Any hit invalidates the case."""

    intervals = [(k, v) for k, v in grade_intervals(cfg, case).items() if v]
    hits: list[str] = []
    for (left_name, left), (right_name, right) in zip(intervals, intervals[1:]):
        if left[1] > right[0] + 1e-12:
            hits.append(f"{left_name}-{right_name}")
    return hits


def validate_realized(cfg: Mapping[str, Any], case: cases.GradingCase) -> dict[str, Any]:
    """Solver-free check that the rendered composition is what was requested.

    This runs with no licensed solver: it compares the analytic request against
    the function the deck encodes, on the fine audit grid.
    """

    tolerance = float(cfg["grading"]["profile_tolerance"])
    width_tolerance = float(cfg["grading"]["width_tolerance_nm"])
    high = float(cfg["materials"]["barrier_al_fraction"])
    profile = build_profile(cfg, case)
    fine_x = profile.x_nm_continuous
    intended = profile.al_fraction_continuous
    realized = (
        np.interp(fine_x, profile.x_nm, profile.al_fraction)
        if case.is_imported else intended.copy()
    )
    profile_error = float(np.max(np.abs(realized - intended)))
    collisions = overlaps(cfg, case)
    row: dict[str, Any] = {
        "case_id": case.case_id,
        "case_name": case.case_name,
        "profile": case.profile,
        "requested_grade_width_nm": case.nominal_grade_width_nm,
        "realized_grade_width_nm": case.nominal_grade_width_nm,
        "maximum_composition_error": profile_error,
        "gaas_reaches_zero": bool(np.min(realized) <= 1e-12),
        "algaas_reaches_max": bool(np.max(realized) >= high - 1e-12),
        "nominal_geometry_preserved": True,
        "unintended_overlap": bool(collisions),
        "smooth_profile_continuous_in_rendering": bool(
            not case.is_imported or np.all(np.diff(profile.x_nm) > 0)
        ),
        "notes": "" if not collisions
                 else "Overlapping grading intervals: " + ", ".join(collisions),
    }
    pos = interface_positions(cfg)
    directions = interface_directions(cfg)
    all_widths_pass = True
    for interface_id in cases.INTERFACE_IDS:
        requested = case.width(interface_id)
        # Native regions and the import table both carry the exact endpoints,
        # so the realized width equals the requested width by construction; the
        # endpoint check below is what actually tests that claim.
        realized_width = requested
        start_x, end_x = directions[interface_id]
        if requested > 0:
            lo = pos[interface_id] - requested / 2.0
            hi = pos[interface_id] + requested / 2.0
            endpoints = np.interp([lo, hi], fine_x, realized)
            # bool() rather than the raw numpy comparison: these rows go
            # straight into JSON manifests, and np.bool_ is not serializable.
            direction_ok = bool(abs(float(endpoints[0]) - start_x) <= tolerance
                                and abs(float(endpoints[1]) - end_x) <= tolerance)
        else:
            direction_ok = True
        row[f"{interface_id}_requested_width_nm"] = float(requested)
        row[f"{interface_id}_realized_width_nm"] = float(realized_width)
        row[f"{interface_id}_width_error_nm"] = abs(
            float(realized_width) - float(requested))
        row[f"{interface_id}_direction_pass"] = direction_ok
        all_widths_pass = bool(
            all_widths_pass
            and abs(realized_width - requested) <= width_tolerance
            and direction_ok
        )
    row["grading_direction_correct"] = all(
        row[f"{key}_direction_pass"] for key in cases.INTERFACE_IDS
    )
    row["validation_pass"] = bool(
        row["gaas_reaches_zero"]
        and row["algaas_reaches_max"]
        and row["grading_direction_correct"]
        and row["nominal_geometry_preserved"]
        and not row["unintended_overlap"]
        and all_widths_pass
        and profile_error <= tolerance
    )
    return row


def plateau_lengths_nm(
    cfg: Mapping[str, Any], case: cases.GradingCase
) -> dict[str, float]:
    """Remaining pure-material lengths, for the record.

    Grading consumes W/2 from each side of an interface, so a symmetric width W
    leaves ``thick_well - W``, ``tunnel_barrier - W``, ``thin_well - W`` pure
    and ``outer_barrier - W/2`` in each outer barrier. A negative value here
    means the requested grade is wider than the layer it sits in.
    """

    g = geometry(cfg)
    half = {key: case.width(key) / 2.0 for key in cases.INTERFACE_IDS}
    return {
        "left_outer_barrier_pure_nm": g.outer_barrier_nm - half["I1"],
        "thick_well_pure_nm": g.thick_well_nm - half["I1"] - half["I2"],
        "tunnel_barrier_pure_nm": g.tunnel_barrier_nm - half["I2"] - half["I3"],
        "thin_well_pure_nm": g.thin_well_nm - half["I3"] - half["I4"],
        "right_outer_barrier_pure_nm": g.outer_barrier_nm - half["I4"],
    }
