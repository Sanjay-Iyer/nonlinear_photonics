"""Demo 14 alloy-composition profiles: x_Al(x) as the canonical representation.

Demo 13 described a graded interface by a *width in nanometres* whose meaning
depended on the profile family, and rendered every non-linear family as a
16-sublayer staircase. Demo 14 replaces both decisions:

* the optimizer-facing quantity is a **10-90% transition width**, so
  ``1.0 nm linear``, ``1.0 nm fermi``, ``1.0 nm erf`` and ``1.0 nm cosine`` all
  describe approximately the same physical interface;
* the canonical representation inside Python is the composition function
  ``x_Al(x)`` itself, and the renderer turns that into either a native
  ``ternary_linear{}`` block or an imported profile for ``ternary_import{}``.

Everything here is bounded **by construction**. The barrier is built as a
product of two monotone factors,

    x_Al(x) = x_max * F_left(x) * F_right(x)

with ``F_left`` rising 0 -> 1 across the left interface and ``F_right`` falling
1 -> 0 across the right one. Both factors live in [0, 1], so their product lives
in [0, x_max] for *every* combination of barrier thickness and interface widths,
including thin barriers whose two interfaces overlap. There is no parameter
combination that produces an unbuildable geometry, which is the whole point:
Demo 13's ``subresolution_grade`` refusals cannot recur here, and if one ever
does it is a bug rather than an expected outcome.

A difference form ``C_left - C_right`` would be the exact interdiffusion result
for the erf family, but it can go **negative** when the two widths differ
sharply (a very wide right interface can outrun a very narrow left one before
the left has risen). The product form has no such failure mode, and reduces to
the same shape whenever the interfaces are well separated.

Realized widths are always **measured from the sampled profile**, never inferred
from the analytic parameter that was requested. Two references are reported,
because they answer different questions and one of them is not always defined:

``peakref``
    thresholds at 10% and 90% of the profile's own achieved maximum. Always
    defined, and it is what an experimentalist reading a STEM/EDS line scan
    measures.
``nominalref``
    thresholds at 10% and 90% of the *nominal* 0 -> x_max transition, i.e.
    0.055 and 0.495 for x_max = 0.55. **Null** whenever an overlapped barrier
    never reaches 0.495 -- which is ~19% of the Demo 14 beta search space, and
    concentrates exactly at the ~1 nm barrier the reference paper calls optimal.
    A null here is a physically meaningful statement, not a failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np

#: Nominal barrier composition for the Demo 14 material system.
NOMINAL_AL_FRACTION = 0.55

#: Families the optimizer may choose between. There is no ``abrupt``: Demo 14 is
#: a grading study, and an abrupt branch would reintroduce the duplicate-geometry
#: problem the hierarchical Demo 13 search space existed to solve.
PROFILE_FAMILIES: tuple[str, ...] = ("linear", "fermi", "erf", "cosine")

#: How each family is handed to nextnano++. ``ternary_linear`` is native; the
#: rest have no native keyword in nextnano++ (verified against keywords_nnp.xml
#: for the 3.0.0 build -- there is no ternary_fermi/erf/cosine) and go through an
#: imported profile.
RENDER_METHOD: Mapping[str, str] = {
    "linear": "ternary_linear",
    "fermi": "ternary_import",
    "erf": "ternary_import",
    "cosine": "ternary_import",
}


class Grading14Error(ValueError):
    """A grading request that is malformed rather than merely unusual."""


# ---------------------------------------------------------------------------
# Profile families
#
# Each family is a monotone "CDF" C(u) rising 0 -> 1 in a natural unit u. The
# 10-90 width in that natural unit is a pure number per family, so converting a
# requested physical 10-90 width into the family's own scale is one division.
# Keeping that number here -- rather than inline at each call site -- is what
# makes "1.0 nm" mean the same interface across all four families.
# ---------------------------------------------------------------------------


def _cdf_linear(u: np.ndarray) -> np.ndarray:
    """Ramp over u in [-1/2, 1/2]. 10-90 width = 0.8 natural units."""

    return np.clip(u + 0.5, 0.0, 1.0)


def _cdf_fermi(u: np.ndarray) -> np.ndarray:
    """Logistic. 10-90 width = 2*ln(9) natural units.

    ``np.logaddexp`` keeps this finite for large |u| instead of overflowing in
    ``exp`` and producing a NaN that would only surface much later as a bad
    composition profile.
    """

    return np.exp(-np.logaddexp(0.0, -u))


def _cdf_erf(u: np.ndarray) -> np.ndarray:
    """Normal CDF in units of sigma. 10-90 width = 2*sqrt(2)*erfinv(0.8)."""

    from scipy.special import erf  # local: keeps import cost off module load

    return 0.5 * (1.0 + erf(u / math.sqrt(2.0)))


def _cdf_cosine(u: np.ndarray) -> np.ndarray:
    """Raised cosine over u in [-1/2, 1/2]; sin^2 form. Compact support."""

    v = np.clip(u + 0.5, 0.0, 1.0)
    return np.sin(0.5 * math.pi * v) ** 2


def _width_10_90_linear() -> float:
    return 0.8


def _width_10_90_fermi() -> float:
    return 2.0 * math.log(9.0)


def _width_10_90_erf() -> float:
    from scipy.special import erfinv

    return 2.0 * math.sqrt(2.0) * float(erfinv(0.8))


def _width_10_90_cosine() -> float:
    # C(v) = sin^2(pi v / 2); C = p  =>  v = (2/pi) arcsin(sqrt(p)).
    lo = (2.0 / math.pi) * math.asin(math.sqrt(0.1))
    hi = (2.0 / math.pi) * math.asin(math.sqrt(0.9))
    return hi - lo


@dataclass(frozen=True)
class ProfileFamily:
    """One interface shape and the constant that anchors its 10-90 width."""

    name: str
    cdf: Callable[[np.ndarray], np.ndarray]
    #: 10-90 width expressed in the family's own natural unit.
    width_10_90_natural: float
    #: True when the shape reaches exactly 0 and 1 at finite u.
    compact_support: bool

    def scale_for(self, width_10_90_nm: float) -> float:
        """Natural-unit scale that realizes ``width_10_90_nm`` in nanometres."""

        if not math.isfinite(width_10_90_nm) or width_10_90_nm <= 0:
            raise Grading14Error(
                f"{self.name}: 10-90 width must be finite and > 0, got "
                f"{width_10_90_nm!r}."
            )
        return float(width_10_90_nm) / self.width_10_90_natural


FAMILIES: Mapping[str, ProfileFamily] = {
    "linear": ProfileFamily("linear", _cdf_linear, _width_10_90_linear(), True),
    "fermi": ProfileFamily("fermi", _cdf_fermi, _width_10_90_fermi(), False),
    "erf": ProfileFamily("erf", _cdf_erf, _width_10_90_erf(), False),
    "cosine": ProfileFamily("cosine", _cdf_cosine, _width_10_90_cosine(), True),
}


def family(name: str) -> ProfileFamily:
    try:
        return FAMILIES[str(name)]
    except KeyError:
        raise Grading14Error(
            f"unknown grading profile {name!r}; Demo 14 supports "
            f"{', '.join(PROFILE_FAMILIES)} and has no abrupt branch."
        ) from None


# ---------------------------------------------------------------------------
# Composition profile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompositionProfile:
    """A sampled ``x_Al(x)`` plus everything needed to audit how it was built."""

    x_nm: np.ndarray
    al_fraction: np.ndarray
    #: The same profile evaluated analytically on a much finer grid, used only
    #: to quantify what the simulation mesh lost.
    x_nm_continuous: np.ndarray
    al_fraction_continuous: np.ndarray
    request: Mapping[str, Any]
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    @property
    def peak_al_fraction(self) -> float:
        return float(np.max(self.al_fraction))

    def as_rows(self) -> list[dict[str, float]]:
        """Rows for ``grading_profile.csv`` (spec section 18)."""

        continuous_on_mesh = np.interp(
            self.x_nm, self.x_nm_continuous, self.al_fraction_continuous
        )
        return [
            {
                "x_nm": float(x),
                "al_fraction_requested_continuous": float(c),
                "al_fraction_rendered": float(r),
            }
            for x, c, r in zip(self.x_nm, continuous_on_mesh, self.al_fraction)
        ]


def build_structure_profile(
    *,
    profile: str,
    thick_well_nm: float,
    thin_well_nm: float,
    barrier_thickness_nm: float,
    gaas_to_algaas_width_10_90_nm: float,
    algaas_to_gaas_width_10_90_nm: float,
    active_start_nm: float,
    domain_nm: tuple[float, float],
    mesh_nm: float,
    max_al_fraction: float = NOMINAL_AL_FRACTION,
    continuous_oversample: int = 20,
) -> CompositionProfile:
    """``x_Al(x)`` for the WHOLE structure, outer barriers included.

    The stack is AlGaAs | thick GaAs | AlGaAs | thin GaAs | AlGaAs, which is the
    layout of the reference nextnano++ decks: the matrix is the barrier alloy and
    the wells are carved out of it. Modelling only the central barrier -- an
    AlGaAs slab in bulk GaAs -- leaves the wells unbounded, so nothing confines
    them and the computed states belong to the quantum region's Dirichlet walls
    rather than to any quantum well.

    Composition is built as the barrier alloy minus two GaAs "occupancies":

        x_Al(z) = x_max * (1 - G_thick(z) - G_thin(z))

    with each ``G`` a product of two monotone factors, so the result stays in
    [0, x_max] for every input, exactly as in :func:`build_profile`.

    There are four interfaces, and the growth direction decides which width each
    takes: an interface where Al rises with increasing z is a GaAs->AlGaAs one,
    and where it falls, AlGaAs->GaAs. The two outer interfaces are graded with
    the same respective widths as the central pair -- one growth process grades
    every interface it makes, and leaving the outer ones abrupt while the inner
    ones are graded would be a structure nobody could grow.
    """

    fam = family(profile)
    for name, value in (
        ("thick_well_nm", thick_well_nm), ("thin_well_nm", thin_well_nm),
        ("barrier_thickness_nm", barrier_thickness_nm), ("mesh_nm", mesh_nm),
    ):
        if not math.isfinite(value) or value <= 0:
            raise Grading14Error(f"{name} must be finite and > 0, got {value!r}.")
    if not 0.0 < max_al_fraction <= 1.0:
        raise Grading14Error(f"max_al_fraction must lie in (0, 1], got {max_al_fraction!r}.")
    lo, hi = float(domain_nm[0]), float(domain_nm[1])
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        raise Grading14Error(f"domain must be an increasing finite pair, got {domain_nm!r}.")

    scale_rise = fam.scale_for(gaas_to_algaas_width_10_90_nm)   # Al rises with z
    scale_fall = fam.scale_for(algaas_to_gaas_width_10_90_nm)   # Al falls with z

    z1 = float(active_start_nm)                       # AlGaAs -> GaAs (Al falls)
    z2 = z1 + float(thick_well_nm)                    # GaAs -> AlGaAs (Al rises)
    z3 = z2 + float(barrier_thickness_nm)             # AlGaAs -> GaAs (Al falls)
    z4 = z3 + float(thin_well_nm)                     # GaAs -> AlGaAs (Al rises)

    def evaluate(x: np.ndarray) -> np.ndarray:
        # Each well opens where Al falls and closes where Al rises.
        thick = fam.cdf((x - z1) / scale_fall) * (1.0 - fam.cdf((x - z2) / scale_rise))
        thin = fam.cdf((x - z3) / scale_fall) * (1.0 - fam.cdf((x - z4) / scale_rise))
        return np.clip(max_al_fraction * (1.0 - thick - thin), 0.0, max_al_fraction)

    n_mesh = int(round((hi - lo) / float(mesh_nm))) + 1
    x_mesh = lo + np.arange(n_mesh, dtype=float) * float(mesh_nm)
    x_fine = np.linspace(lo, hi, (n_mesh - 1) * int(continuous_oversample) + 1)

    request = {
        "profile": fam.name,
        "render_method": RENDER_METHOD[fam.name],
        "structure": "algaas_matrix_with_two_gaas_wells",
        "thick_well_nm": float(thick_well_nm),
        "thin_well_nm": float(thin_well_nm),
        "barrier_thickness_nm": float(barrier_thickness_nm),
        "barrier_centre_nm": 0.5 * (z2 + z3),
        "requested_gaas_to_algaas_grading_width_10_90_nm": float(
            gaas_to_algaas_width_10_90_nm
        ),
        "requested_algaas_to_gaas_grading_width_10_90_nm": float(
            algaas_to_gaas_width_10_90_nm
        ),
        "max_al_fraction": float(max_al_fraction),
        "mesh_nm": float(mesh_nm),
        "domain_nm": [lo, hi],
        "natural_scale_rise_nm": scale_rise,
        "natural_scale_fall_nm": scale_fall,
        "interfaces_nm": {
            "outer_left_algaas_to_gaas": z1,
            "central_gaas_to_algaas": z2,
            "central_algaas_to_gaas": z3,
            "outer_right_gaas_to_algaas": z4,
        },
        "active_start_nm": z1,
        "active_end_nm": z4,
    }
    built = CompositionProfile(
        x_nm=x_mesh, al_fraction=evaluate(x_mesh),
        x_nm_continuous=x_fine, al_fraction_continuous=evaluate(x_fine),
        request=request,
    )
    return CompositionProfile(
        x_nm=built.x_nm, al_fraction=built.al_fraction,
        x_nm_continuous=built.x_nm_continuous,
        al_fraction_continuous=built.al_fraction_continuous,
        request=request,
        diagnostics=measure_structure(built, max_al_fraction=max_al_fraction),
    )


def measure_structure(
    profile: CompositionProfile, *, max_al_fraction: float = NOMINAL_AL_FRACTION
) -> dict[str, Any]:
    """Realized diagnostics for a full-structure profile.

    The central barrier is the Al peak *between* the two wells, so it is located
    within the well interval rather than by taking a global maximum -- the outer
    barriers are equally tall and a global argmax would land in one of them.
    """

    x = np.asarray(profile.x_nm, dtype=float)
    y = np.asarray(profile.al_fraction, dtype=float)
    interfaces = profile.request["interfaces_nm"]
    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])

    # The measurement window runs from the bottom of one well to the bottom of
    # the other, NOT across the whole active region. Spanning the active region
    # puts the outer barriers inside the scan, and the crossing search then finds
    # the outer interface before the central one -- which reports the *well
    # width* as the interface width.
    def _minimum_index(lo: float, hi: float) -> int:
        window = np.where((x >= lo) & (x <= hi))[0]
        if window.size == 0:
            raise Grading14Error(f"no mesh points between {lo} and {hi} nm.")
        return int(window[int(np.argmin(y[window]))])

    left_floor = _minimum_index(z1, z2)     # bottom of the thick well
    right_floor = _minimum_index(z3, z4)    # bottom of the thin well
    if right_floor <= left_floor:
        raise Grading14Error("the two wells could not be separated on this mesh.")

    central = y[left_floor : right_floor + 1]
    central_x = x[left_floor : right_floor + 1]
    peak = float(np.max(central))
    peak_index = int(np.argmax(central))

    low, high = 0.10 * peak, 0.90 * peak
    left = _interface_width(central_x, central, peak_index, low, high, side="left")
    right = _interface_width(central_x, central, peak_index, low, high, side="right")

    nominal_high = 0.90 * max_al_fraction
    reached = bool(peak >= nominal_high)
    nominal_low = 0.10 * max_al_fraction
    left_nom = right_nom = None
    if reached:
        left_nom = _interface_width(
            central_x, central, peak_index, nominal_low, nominal_high, side="left")
        right_nom = _interface_width(
            central_x, central, peak_index, nominal_low, nominal_high, side="right")

    half = 0.5 * peak
    a = _crossing_nm(central_x[: peak_index + 1], central[: peak_index + 1], half, rising=True)
    b = _crossing_nm(central_x[peak_index:], central[peak_index:], half, rising=False)
    fwhm = abs(b - a) if (a is not None and b is not None) else None

    dose = float(np.trapezoid(central, central_x) / max_al_fraction)
    slope = np.gradient(central, central_x) if central.size > 2 else np.zeros_like(central)
    rendered_on_fine = np.interp(profile.x_nm_continuous, x, y)
    residual = np.abs(rendered_on_fine - profile.al_fraction_continuous)

    return {
        "realized_peak_al_fraction": peak,
        "realized_min_al_fraction": float(np.min(central)),
        "realized_gaas_to_algaas_grading_width_10_90_peakref_nm": left,
        "realized_algaas_to_gaas_grading_width_10_90_peakref_nm": right,
        "realized_gaas_to_algaas_grading_width_10_90_nominalref_nm": left_nom,
        "realized_algaas_to_gaas_grading_width_10_90_nominalref_nm": right_nom,
        "nominal_90pct_threshold_reached": reached,
        "nominal_90pct_threshold_al_fraction": nominal_high,
        "grading_interfaces_overlap": bool(peak < 0.995 * max_al_fraction),
        "realized_barrier_fwhm_nm": fwhm,
        "integrated_al_dose_nm_equivalent": dose,
        "grading_slope_max_left_per_nm": float(
            np.max(np.abs(slope[: peak_index + 1]))) if peak_index > 0 else 0.0,
        "grading_slope_max_right_per_nm": float(
            np.max(np.abs(slope[peak_index:]))) if peak_index < central.size - 1 else 0.0,
        "grading_profile_realization_max_error": float(np.max(residual)) if residual.size else 0.0,
        "grading_profile_realization_rms_error": float(
            np.sqrt(np.mean(residual**2))) if residual.size else 0.0,
        "profile_within_bounds": bool(
            np.all(y >= -1e-12) and np.all(y <= max_al_fraction + 1e-12)),
        "profile_points": int(x.size),
        "profile_monotone_coordinates": bool(np.all(np.diff(x) > 0)),
        "outer_barrier_present": bool(y[0] >= 0.99 * max_al_fraction
                                      and y[-1] >= 0.99 * max_al_fraction),
    }


def build_profile(
    *,
    profile: str,
    barrier_thickness_nm: float,
    gaas_to_algaas_width_10_90_nm: float,
    algaas_to_gaas_width_10_90_nm: float,
    barrier_centre_nm: float,
    domain_nm: tuple[float, float],
    mesh_nm: float,
    max_al_fraction: float = NOMINAL_AL_FRACTION,
    continuous_oversample: int = 20,
) -> CompositionProfile:
    """Construct ``x_Al(x)`` for one graded central barrier.

    ``gaas_to_algaas_width_10_90_nm`` is the **left** (growth-direction leading)
    interface and ``algaas_to_gaas_width_10_90_nm`` the **right** one. They are
    deliberately independent: the two growth-direction interfaces of a real
    structure are not equally sharp, and forcing them equal would hide that.

    Bounded for every input by construction -- see the module docstring.
    """

    fam = family(profile)
    if not math.isfinite(barrier_thickness_nm) or barrier_thickness_nm <= 0:
        raise Grading14Error(
            f"barrier thickness must be finite and > 0, got {barrier_thickness_nm!r}."
        )
    if not math.isfinite(mesh_nm) or mesh_nm <= 0:
        raise Grading14Error(f"mesh spacing must be finite and > 0, got {mesh_nm!r}.")
    if not 0.0 < max_al_fraction <= 1.0:
        raise Grading14Error(
            f"max_al_fraction must lie in (0, 1], got {max_al_fraction!r}."
        )
    lo, hi = (float(domain_nm[0]), float(domain_nm[1]))
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        raise Grading14Error(f"domain must be an increasing finite pair, got {domain_nm!r}.")

    scale_left = fam.scale_for(gaas_to_algaas_width_10_90_nm)
    scale_right = fam.scale_for(algaas_to_gaas_width_10_90_nm)
    edge_left = float(barrier_centre_nm) - 0.5 * float(barrier_thickness_nm)
    edge_right = float(barrier_centre_nm) + 0.5 * float(barrier_thickness_nm)

    def evaluate(x: np.ndarray) -> np.ndarray:
        rising = fam.cdf((x - edge_left) / scale_left)
        falling = 1.0 - fam.cdf((x - edge_right) / scale_right)
        # Both factors are in [0, 1] so the product cannot leave [0, x_max].
        # The clip is defensive only: it guards against a future family whose
        # CDF overshoots, rather than against anything the current four do.
        return np.clip(max_al_fraction * rising * falling, 0.0, max_al_fraction)

    n_mesh = int(round((hi - lo) / float(mesh_nm))) + 1
    x_mesh = lo + np.arange(n_mesh, dtype=float) * float(mesh_nm)
    x_fine = np.linspace(lo, hi, (n_mesh - 1) * int(continuous_oversample) + 1)

    profile_mesh = evaluate(x_mesh)
    profile_fine = evaluate(x_fine)

    request = {
        "profile": fam.name,
        "render_method": RENDER_METHOD[fam.name],
        "barrier_thickness_nm": float(barrier_thickness_nm),
        "barrier_centre_nm": float(barrier_centre_nm),
        "requested_gaas_to_algaas_grading_width_10_90_nm": float(
            gaas_to_algaas_width_10_90_nm
        ),
        "requested_algaas_to_gaas_grading_width_10_90_nm": float(
            algaas_to_gaas_width_10_90_nm
        ),
        "max_al_fraction": float(max_al_fraction),
        "mesh_nm": float(mesh_nm),
        "domain_nm": [lo, hi],
        "natural_scale_left_nm": scale_left,
        "natural_scale_right_nm": scale_right,
        "nominal_edge_left_nm": edge_left,
        "nominal_edge_right_nm": edge_right,
    }
    built = CompositionProfile(
        x_nm=x_mesh,
        al_fraction=profile_mesh,
        x_nm_continuous=x_fine,
        al_fraction_continuous=profile_fine,
        request=request,
    )
    return CompositionProfile(
        x_nm=built.x_nm,
        al_fraction=built.al_fraction,
        x_nm_continuous=built.x_nm_continuous,
        al_fraction_continuous=built.al_fraction_continuous,
        request=request,
        diagnostics=measure(built, max_al_fraction=max_al_fraction),
    )


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def _crossing_nm(
    x: np.ndarray, y: np.ndarray, level: float, *, rising: bool
) -> float | None:
    """First crossing of ``level``, linearly interpolated. ``None`` if absent.

    Scanning direction matters: the left interface is found by walking forward
    from the domain edge, the right one by walking backward, so each width is
    measured on its own interface even when the two overlap.
    """

    seq = range(len(x) - 1) if rising else range(len(x) - 1, 0, -1)
    for i in seq:
        a, b = (i, i + 1) if rising else (i, i - 1)
        ya, yb = y[a], y[b]
        if (ya < level <= yb) or (ya >= level > yb):
            if yb == ya:
                return float(x[a])
            t = (level - ya) / (yb - ya)
            return float(x[a] + t * (x[b] - x[a]))
    return None


def _interface_width(
    x: np.ndarray,
    y: np.ndarray,
    peak_index: int,
    low: float,
    high: float,
    *,
    side: str,
) -> float | None:
    """10-90 width on one side of the peak, or ``None`` if a level is unreached."""

    if side == "left":
        xs, ys = x[: peak_index + 1], y[: peak_index + 1]
        rising = True
    else:
        xs, ys = x[peak_index:], y[peak_index:]
        rising = False
    if len(xs) < 2:
        return None
    x_low = _crossing_nm(xs, ys, low, rising=rising)
    x_high = _crossing_nm(xs, ys, high, rising=rising)
    if x_low is None or x_high is None:
        return None
    return abs(x_high - x_low)


def measure(
    profile: CompositionProfile, *, max_al_fraction: float = NOMINAL_AL_FRACTION
) -> dict[str, Any]:
    """Every realized-geometry diagnostic Demo 14 records for a trial.

    Measured from the sampled profile, never from the requested analytic
    parameters -- that distinction is the entire point of storing both.
    """

    x = np.asarray(profile.x_nm, dtype=float)
    y = np.asarray(profile.al_fraction, dtype=float)
    peak = float(np.max(y))
    peak_index = int(np.argmax(y))

    # --- peak-referenced: always defined for a profile with any Al at all ---
    peak_low, peak_high = 0.10 * peak, 0.90 * peak
    left_peakref = _interface_width(x, y, peak_index, peak_low, peak_high, side="left")
    right_peakref = _interface_width(x, y, peak_index, peak_low, peak_high, side="right")

    # --- nominal-referenced: null when an overlapped barrier never reaches 90% ---
    nominal_low = 0.10 * max_al_fraction
    nominal_high = 0.90 * max_al_fraction
    reached = bool(peak >= nominal_high)
    if reached:
        left_nominal = _interface_width(
            x, y, peak_index, nominal_low, nominal_high, side="left"
        )
        right_nominal = _interface_width(
            x, y, peak_index, nominal_low, nominal_high, side="right"
        )
    else:
        left_nominal = right_nominal = None

    half = 0.5 * peak
    fwhm_left = _crossing_nm(x[: peak_index + 1], y[: peak_index + 1], half, rising=True)
    fwhm_right = _crossing_nm(x[peak_index:], y[peak_index:], half, rising=False)
    fwhm = (
        abs(fwhm_right - fwhm_left)
        if (fwhm_left is not None and fwhm_right is not None)
        else None
    )

    # Al "dose" as an equivalent thickness of fully-composed barrier material:
    # integral of x_Al dz divided by the nominal fraction. Comparable across
    # designs in a way that neither peak nor width alone is.
    dose = float(np.trapezoid(y, x) / max_al_fraction) if len(x) > 1 else 0.0

    slope = np.gradient(y, x) if len(x) > 2 else np.zeros_like(y)
    slope_left = float(np.max(np.abs(slope[: peak_index + 1]))) if peak_index > 0 else 0.0
    slope_right = (
        float(np.max(np.abs(slope[peak_index:]))) if peak_index < len(y) - 1 else 0.0
    )

    # Mesh fidelity. This must be measured on the FINE grid, not at the mesh
    # points: a DAT import is piecewise-linear *between* its samples, so the
    # error nextnano++ actually sees lives between mesh points. Comparing at the
    # mesh points instead comes out identically zero -- the profile is exact
    # where it was sampled -- which would report perfect fidelity for every
    # trial at every mesh, exactly the false signal this diagnostic exists to
    # prevent.
    rendered_on_fine = np.interp(profile.x_nm_continuous, x, y)
    residual = np.abs(rendered_on_fine - profile.al_fraction_continuous)
    max_error = float(np.max(residual)) if residual.size else 0.0
    rms_error = float(np.sqrt(np.mean(residual**2))) if residual.size else 0.0

    return {
        "realized_peak_al_fraction": peak,
        "realized_min_al_fraction": float(np.min(y)),
        "realized_gaas_to_algaas_grading_width_10_90_peakref_nm": left_peakref,
        "realized_algaas_to_gaas_grading_width_10_90_peakref_nm": right_peakref,
        "realized_gaas_to_algaas_grading_width_10_90_nominalref_nm": left_nominal,
        "realized_algaas_to_gaas_grading_width_10_90_nominalref_nm": right_nominal,
        "nominal_90pct_threshold_reached": reached,
        "nominal_90pct_threshold_al_fraction": nominal_high,
        "grading_interfaces_overlap": bool(peak < 0.995 * max_al_fraction),
        "realized_barrier_fwhm_nm": fwhm,
        "integrated_al_dose_nm_equivalent": dose,
        "grading_slope_max_left_per_nm": slope_left,
        "grading_slope_max_right_per_nm": slope_right,
        "grading_profile_realization_max_error": max_error,
        "grading_profile_realization_rms_error": rms_error,
        "profile_within_bounds": bool(
            np.all(y >= -1e-12) and np.all(y <= max_al_fraction + 1e-12)
        ),
        "profile_points": int(len(x)),
        "profile_monotone_coordinates": bool(np.all(np.diff(x) > 0)),
    }


# ---------------------------------------------------------------------------
# nextnano++ rendering
# ---------------------------------------------------------------------------


def import_datafile(profile: CompositionProfile) -> str:
    """The ``format = DAT`` payload for ``import{ file{} }``.

    Two columns, position in nm and Al fraction, strictly ascending in position.
    Written with enough precision that a 0.05 nm mesh is represented exactly
    rather than being re-quantized by the formatter.
    """

    x = np.asarray(profile.x_nm, dtype=float)
    y = np.asarray(profile.al_fraction, dtype=float)
    if x.size != y.size:
        raise Grading14Error("profile coordinate and value arrays differ in length.")
    if x.size == 0:
        raise Grading14Error("refusing to write a zero-length imported profile.")
    if not np.all(np.diff(x) > 0):
        raise Grading14Error(
            "imported profile coordinates must be strictly ascending; duplicate or "
            "unsorted coordinates are one of the failure modes this check exists for."
        )
    if not np.all(np.isfinite(y)):
        raise Grading14Error("imported profile contains a non-finite Al fraction.")
    return "".join(f"{xi:.6f} {yi:.8f}\n" for xi, yi in zip(x, y))


def _imported_regions(
    profile: CompositionProfile, *, import_name: str, material_name: str,
    reason: str = "",
) -> dict[str, Any]:
    """One imported-table region covering the whole domain."""

    domain = profile.request.get("domain_nm")
    return {
        "import_block": (
            "import{\n"
            f'    file{{ name = "{import_name}"  filename = "{import_name}.dat"  '
            "format = DAT  number_of_dimensions = 1 }\n"
            "    output_imports{}\n"
            "}\n"
        ),
        "regions": [
            {
                "x": (float(domain[0]), float(domain[1])) if domain else None,
                "material": (
                    f'ternary_import{{ name = "{material_name}"  '
                    f'import_from = "{import_name}" }}'
                ),
            }
        ],
        "structure_block": (
            f'        ternary_import{{ name = "{material_name}"  '
            f'import_from = "{import_name}" }}\n'
        ),
        "datafile": import_datafile(profile),
        "render_fallback_reason": reason,
    }


def render_imported_blocks(
    profile: CompositionProfile,
    *,
    import_name: str = "al_profile",
    material_name: str = "Al(x)Ga(1-x)As",
    reason: str = "",
) -> dict[str, Any]:
    """The imported-table rendering of ``profile``, whatever family it came from.

    :func:`render_structure_blocks` already chooses this path for fermi/erf/cosine
    and for overlapped linear grades. This exposes the *same* renderer
    unconditionally, so a linear profile that would natively use
    ``ternary_linear{}`` can also be handed to nextnano++ as a table.

    That is not an alternative implementation -- it is the production importer,
    called deliberately. Demo 17's native-vs-imported equivalence experiment needs
    both renderings of one profile, and generating the second one anywhere else
    would compare Demo 17's importer against nextnano++ rather than Demo 14's.
    """

    return _imported_regions(
        profile, import_name=import_name, material_name=material_name, reason=reason
    )


def render_structure_blocks(
    profile: CompositionProfile,
    *,
    import_name: str = "al_profile",
    material_name: str = "Al(x)Ga(1-x)As",
) -> dict[str, str]:
    """nextnano++ blocks for this profile.

    ``linear`` uses the native ``ternary_linear{}`` grammar; the other three have
    no native keyword in nextnano++ 3.0.0 and are handed over as an imported
    profile. The growth coordinate is ``x``, confirmed against
    ``keywords_nnp.xml`` and the existing validated Demo 13 deck rather than
    inferred from an example.
    """

    fam = family(profile.request["profile"])
    method = RENDER_METHOD[fam.name]
    req = profile.request
    if method == "ternary_linear" and "interfaces_nm" in req:
        # Full-structure profile: AlGaAs matrix, two GaAs wells, four graded
        # interfaces. Wells first, then the ramps written over their edges --
        # later regions override earlier ones, exactly as the reference decks do.
        interfaces = req["interfaces_nm"]
        z1 = float(interfaces["outer_left_algaas_to_gaas"])
        z2 = float(interfaces["central_gaas_to_algaas"])
        z3 = float(interfaces["central_algaas_to_gaas"])
        z4 = float(interfaces["outer_right_gaas_to_algaas"])
        s_rise = float(req["natural_scale_rise_nm"])
        s_fall = float(req["natural_scale_fall_nm"])
        x_max = float(req["max_al_fraction"])

        # If the central barrier's two ramps overlap, a linear -> constant ->
        # linear region template cannot represent the intended composition: the
        # later region simply overrides the earlier one across the overlap, which
        # fabricates a profile nobody asked for. An imported table reproduces
        # x_Al(x) exactly, so the renderer switches to it rather than emitting a
        # structure that merely looks plausible.
        central_rise_end = z2 + 0.5 * s_rise
        central_fall_start = z3 - 0.5 * s_fall
        if central_rise_end > central_fall_start + 1e-9:
            return _imported_regions(
                profile, import_name=import_name, material_name=material_name,
                reason="central linear ramps overlap; a region template would "
                       "override one grade with the other",
            )

        regions: list[dict[str, Any]] = [
            {"x": (z1, z2), "material": f'binary{{ name = "GaAs" }}'},
            {"x": (z3, z4), "material": f'binary{{ name = "GaAs" }}'},
        ]
        for centre, scale, lo_hi in (
            (z1, s_fall, (x_max, 0.0)),   # AlGaAs -> GaAs
            (z2, s_rise, (0.0, x_max)),   # GaAs -> AlGaAs
            (z3, s_fall, (x_max, 0.0)),   # AlGaAs -> GaAs
            (z4, s_rise, (0.0, x_max)),   # GaAs -> AlGaAs
        ):
            start, end = centre - 0.5 * scale, centre + 0.5 * scale
            if end - start <= 1e-9:
                continue
            regions.append({
                "x": (start, end),
                "material": (
                    f'ternary_linear{{ name = "{material_name}"  '
                    f"alloy_x = [{lo_hi[0]:.6f}, {lo_hi[1]:.6f}]  "
                    f"x = [{start:.6f}, {end:.6f}] }}"
                ),
            })
        return {
            "import_block": "",
            "regions": regions,
            "structure_block": "\n".join(f"        {r['material']}" for r in regions) + "\n",
            "datafile": "",
        }

    if method == "ternary_linear":
        edge_l = float(req["nominal_edge_left_nm"])
        edge_r = float(req["nominal_edge_right_nm"])
        scale_l = float(req["natural_scale_left_nm"])
        scale_r = float(req["natural_scale_right_nm"])
        x_max = float(req["max_al_fraction"])
        # The linear family has compact support: the full 0 -> 1 transition spans
        # exactly one natural scale, centred on the nominal edge.
        rise_start, rise_end = edge_l - 0.5 * scale_l, edge_l + 0.5 * scale_l
        fall_start, fall_end = edge_r - 0.5 * scale_r, edge_r + 0.5 * scale_r
        # ONE material per region. nextnano++ rejects a region carrying several
        # with "Too many instances of 'ternary_linear'", which is exactly what
        # terminated the first licensed gate run: three materials were emitted
        # into a single region and the solver refused the deck before solving.
        regions = [
            {
                "x": (rise_start, rise_end),
                "material": (
                    f'ternary_linear{{ name = "{material_name}"  '
                    f"alloy_x = [0.0, {x_max:.6f}]  "
                    f"x = [{rise_start:.6f}, {rise_end:.6f}] }}"
                ),
            },
            {
                "x": (rise_end, fall_start),
                "material": (
                    f'ternary_constant{{ name = "{material_name}"  '
                    f"alloy_x = {x_max:.6f} }}"
                ),
            },
            {
                "x": (fall_start, fall_end),
                "material": (
                    f'ternary_linear{{ name = "{material_name}"  '
                    f"alloy_x = [{x_max:.6f}, 0.0]  "
                    f"x = [{fall_start:.6f}, {fall_end:.6f}] }}"
                ),
            },
        ]
        # A barrier narrower than its own two ramps leaves no plateau; emitting a
        # zero- or negative-width region would be rejected, so drop it.
        regions = [r for r in regions if r["x"][1] - r["x"][0] > 1e-9]
        return {
            "import_block": "",
            "regions": regions,
            "structure_block": "\n".join(f"        {r['material']}" for r in regions)
            + "\n",
            "datafile": "",
        }

    import_block = (
        "import{\n"
        f'    file{{ name = "{import_name}"  filename = "{import_name}.dat"  '
        "format = DAT  number_of_dimensions = 1 }\n"
        "    output_imports{}\n"
        "}\n"
    )
    # The imported table spans the entire domain and already encodes the outer
    # barriers, both wells and every graded interface, so one region covering
    # everything is both sufficient and the only self-consistent choice.
    domain = req.get("domain_nm")
    regions = [
        {
            "x": (float(domain[0]), float(domain[1])) if domain else None,
            "material": (
                f'ternary_import{{ name = "{material_name}"  '
                f'import_from = "{import_name}" }}'
            ),
        }
    ]
    return {
        "import_block": import_block,
        "regions": regions,
        "structure_block": f"        {regions[0]['material']}\n",
        "datafile": import_datafile(profile),
    }


def sample_search_space(
    rng: np.random.Generator,
    n: int,
    *,
    barrier_nm: tuple[float, float] = (0.85, 2.50),
    width_nm: tuple[float, float] = (0.40, 1.40),
) -> list[dict[str, Any]]:
    """Random draws from the Demo 14 beta grading ranges, for bulk testing."""

    families = list(PROFILE_FAMILIES)
    return [
        {
            "profile": families[int(rng.integers(len(families)))],
            "barrier_thickness_nm": float(rng.uniform(*barrier_nm)),
            "gaas_to_algaas_width_10_90_nm": float(rng.uniform(*width_nm)),
            "algaas_to_gaas_width_10_90_nm": float(rng.uniform(*width_nm)),
        }
        for _ in range(int(n))
    ]
