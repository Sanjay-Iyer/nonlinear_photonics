"""The in-plane k sum, derived twice, plus a dimensional ledger with no gaps.

This is where Demo 16F spends most of its effort, because the k-space
normalisation is the one factor in the absolute prefactor with enough headroom
to explain a 75-85x discrepancy. The paper says only that

    "the summation over in-plane k states was converted to an integral over
     (kx, ky)"

and never writes the normalisation down.

Two things are done about that:

**Two independent implementations.** :func:`radial_integral` reduces the
integral analytically using isotropy and quadratures in ``k``;
:func:`cartesian_integral` never uses isotropy and quadratures the genuine
``(kx, ky)`` plane. For an isotropic integrand on the same domain they must
agree. If they do not, a ``2*pi``, a radial measure ``k``, a spin factor or an
area normalisation has been dropped or applied twice -- which is exactly the
class of error that produces a large, structure-independent amplitude offset.

**A dimensional ledger.** :func:`dimensional_ledger` multiplies every factor of
the prefactor together *with its units* and asserts the product closes on m/V.
There is no "dimensionless sum" anywhere: the k integral carries nm^-2, the
position matrix element carries nm, the denominators carry eV^-2, and each is
converted explicitly. A missing area normalisation cannot hide in a quantity
that has no declared unit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Mapping, Sequence

import numpy as np

#: CODATA values, identical to the shared ``chi2`` module's so the two cannot
#: drift apart. Imported by value rather than by reference because this module
#: must stay runnable with no solver and no demo path set up.
ELEMENTARY_CHARGE_C = 1.602176634e-19
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
REDUCED_PLANCK_J_S = 1.054571817e-34
ELECTRON_MASS_KG = 9.1093837015e-31

#: Agreement tolerance between the two k implementations on the disc. Set by
#: quadrature, not by physics: the Cartesian route resolves the circular
#: boundary only to one cell, so its error falls like h/k_max. At the default
#: 1201 points that is a few parts per thousand. Anything this test is meant to
#: catch -- a stray 2*pi (6.28x), a spin factor (2x), a disc/square area ratio
#: (1.27x) -- is orders of magnitude larger.
K_METHOD_AGREEMENT_TOLERANCE = 0.01


class KSpace16FError(ValueError):
    """A k-space request this module does not define."""


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Unit:
    """Exponents of the SI base quantities this calculation actually uses.

    Deliberately not a general unit library. Four exponents are enough to prove
    that ``chi2`` closes on m/V, and a four-field dataclass is auditable by
    reading it, which a general library is not.
    """

    m: float = 0.0
    C: float = 0.0
    J: float = 0.0
    s: float = 0.0

    def __mul__(self, other: "Unit") -> "Unit":
        return Unit(self.m + other.m, self.C + other.C,
                    self.J + other.J, self.s + other.s)

    def __str__(self) -> str:
        parts = [
            f"{name}^{value:g}"
            for name, value in (("m", self.m), ("C", self.C),
                                ("J", self.J), ("s", self.s))
            if value
        ]
        return " ".join(parts) if parts else "dimensionless"


#: chi^(2) is a length per volt. V = J/C, so m/V = m * C * J^-1.
CHI2_UNIT = Unit(m=1.0, C=1.0, J=-1.0)
DIMENSIONLESS = Unit()


@dataclass
class LedgerRow:
    label: str
    value: float
    unit: Unit
    note: str = ""


@dataclass
class Ledger:
    """Every factor of the prefactor, with units, and the closing check."""

    rows: list[LedgerRow] = field(default_factory=list)

    def add(self, label: str, value: float, unit: Unit, note: str = "") -> "Ledger":
        self.rows.append(LedgerRow(label, float(value), unit, note))
        return self

    @property
    def product(self) -> float:
        result = 1.0
        for row in self.rows:
            result *= row.value
        return result

    @property
    def unit(self) -> Unit:
        result = DIMENSIONLESS
        for row in self.rows:
            result = result * row.unit
        return result

    def closes_on(self, expected: Unit = CHI2_UNIT) -> bool:
        return self.unit == expected

    def render(self) -> str:
        width = max(len(row.label) for row in self.rows) if self.rows else 10
        lines = [f"{'factor'.ljust(width)}  {'value':>14}  unit"]
        lines.append("-" * (width + 34))
        for row in self.rows:
            lines.append(f"{row.label.ljust(width)}  {row.value:14.6e}  {row.unit}")
        lines.append("-" * (width + 34))
        lines.append(f"{'product'.ljust(width)}  {self.product:14.6e}  {self.unit}")
        lines.append(
            f"closes on chi2 [{CHI2_UNIT}]: "
            f"{'YES' if self.closes_on() else 'NO'}"
        )
        return "\n".join(lines)

    def as_record(self) -> dict[str, Any]:
        return {
            "rows": [
                {"factor": r.label, "value": r.value, "unit": str(r.unit),
                 "note": r.note}
                for r in self.rows
            ],
            "product": self.product,
            "product_unit": str(self.unit),
            "expected_unit": str(CHI2_UNIT),
            "closes": self.closes_on(),
        }


def dimensional_ledger(
    *,
    n_wells_per_metre: float,
    r_e_hh_nm: float,
    k_integral_per_nm2: float,
    position_matrix_nm: float,
    denominator_product_eV2: float,
    heavy_hole_mj_factor: float = 1.0,
) -> Ledger:
    """Assemble chi2 factor by factor, each carrying its unit.

    Written out rather than collapsed into one expression so that a reader can
    check every conversion against Eq. 2 by eye. The ``hbar^2`` of the paper's
    prefactor does not appear because the two frequency denominators are
    evaluated in energy: ``1/(hbar^2 * omega_a * omega_b) == 1/(E_a * E_b)``
    identically, and both routes carry J^-2, which the ledger shows.
    """

    ledger = Ledger()
    ledger.add("N_z", n_wells_per_metre, Unit(m=-1.0),
               "number of quantum wells per unit length")
    ledger.add("e^3", ELEMENTARY_CHARGE_C**3, Unit(C=3.0),
               "Eq. 2 prefactor; r_e,hh is a position, never multiplied by e")
    ledger.add("r_e,hh^2", (float(r_e_hh_nm) * 1.0e-9) ** 2, Unit(m=2.0),
               "unit-cell interband position matrix element, squared")
    ledger.add("1/(6 eps0)", 1.0 / (6.0 * VACUUM_PERMITTIVITY_F_PER_M),
               Unit(J=1.0, m=1.0, C=-2.0),
               "eps0 = C^2 J^-1 m^-1; the 1/6 is Eq. 2's, absorbing Eq. 1's "
               "permutation sum")
    ledger.add("k integral", float(k_integral_per_nm2) * 1.0e18, Unit(m=-2.0),
               "(g_s/(2 pi)^2) * int d^2k over the stated domain; nm^-2 -> m^-2")
    ledger.add("<psi|z|psi>", float(position_matrix_nm) * 1.0e-9, Unit(m=1.0),
               "envelope position matrix element; nm -> m")
    ledger.add("1/(E_2ph * E_1ph)",
               1.0 / (float(denominator_product_eV2)
                      * ELEMENTARY_CHARGE_C**2),
               Unit(J=-2.0),
               "two-photon x one-photon denominators; eV^2 -> J^2. This is "
               "where the paper's 1/hbar^2 has gone: 1/(hbar^2 w_a w_b) = "
               "1/(E_a E_b)")
    if heavy_hole_mj_factor != 1.0:
        ledger.add("hh m_j = +/-3/2", float(heavy_hole_mj_factor), DIMENSIONLESS,
                   "explicit open factor; the paper does not state it")
    return ledger


# ---------------------------------------------------------------------------
# The two implementations
# ---------------------------------------------------------------------------


def _square_radius(theta: np.ndarray, k_max: float) -> np.ndarray:
    """Distance from the origin to the edge of the square at angle ``theta``."""

    return k_max / np.maximum(np.abs(np.cos(theta)), np.abs(np.sin(theta)))


def radial_integral(
    integrand: Callable[[np.ndarray], np.ndarray],
    *,
    k_max_per_nm: float,
    points: int = 96,
    spin_degeneracy: int = 2,
    domain: str = "disc",
    angular_points: int = 361,
) -> complex:
    """``(g_s/(2 pi)^2) * int d^2k f(|k|)``, reduced using isotropy.

    On the disc the angular integral is exactly ``2 pi`` and the result collapses
    to ``(g_s/(2 pi)) int_0^kmax f(k) k dk`` -- the form the production code
    uses. On the square the outer radius depends on angle, so the angular
    integral is done numerically; that path exists so the disc/square comparison
    is like for like rather than one shape being handled by a different method.
    """

    k_max = float(k_max_per_nm)
    if not math.isfinite(k_max) or k_max <= 0:
        raise KSpace16FError("k_max_per_nm must be finite and > 0.")
    if int(points) < 2:
        raise KSpace16FError("points must be at least 2.")
    g_s = float(spin_degeneracy)

    if domain == "disc":
        k = np.linspace(0.0, k_max, int(points))
        values = np.asarray(integrand(k))
        # int_0^kmax f(k) k dk, then the exact 2*pi from the angular integral
        # divided by (2 pi)^2.
        radial = np.trapezoid(values * k, k)
        return complex(g_s * radial / (2.0 * math.pi))

    if domain == "square":
        # Only one octant is independent, but integrating the full circle costs
        # nothing and removes a symmetry assumption from the check.
        theta = np.linspace(0.0, 2.0 * math.pi, int(angular_points))
        outer = _square_radius(theta, k_max)
        inner = np.empty(theta.size, dtype=complex)
        for index, radius in enumerate(outer):
            k = np.linspace(0.0, float(radius), int(points))
            values = np.asarray(integrand(k))
            inner[index] = np.trapezoid(values * k, k)
        total = np.trapezoid(inner, theta)
        return complex(g_s * total / (2.0 * math.pi) ** 2)

    raise KSpace16FError(f"unknown domain {domain!r}; known: disc, square")


def cartesian_integral(
    integrand: Callable[[np.ndarray], np.ndarray],
    *,
    k_max_per_nm: float,
    points: int = 1201,
    spin_degeneracy: int = 2,
    domain: str = "disc",
) -> complex:
    """``(g_s/(2 pi)^2) * int dkx dky f(sqrt(kx^2 + ky^2))``, no isotropy used.

    A genuine tensor-product grid over the ``(kx, ky)`` plane. Nothing here
    knows that the integrand is radial; the disc is imposed by zeroing the
    integrand outside it, which is why this route resolves the circular boundary
    only to one cell and why the agreement tolerance is a few parts per
    thousand rather than machine precision.
    """

    k_max = float(k_max_per_nm)
    if not math.isfinite(k_max) or k_max <= 0:
        raise KSpace16FError("k_max_per_nm must be finite and > 0.")
    if int(points) < 3:
        raise KSpace16FError("points must be at least 3.")
    if domain not in ("disc", "square"):
        raise KSpace16FError(f"unknown domain {domain!r}; known: disc, square")

    axis = np.linspace(-k_max, k_max, int(points))
    kx, ky = np.meshgrid(axis, axis, indexing="ij")
    magnitude = np.sqrt(kx**2 + ky**2)
    values = np.asarray(integrand(magnitude.ravel())).reshape(magnitude.shape)
    values = np.asarray(values, dtype=complex)
    if domain == "disc":
        values = np.where(magnitude <= k_max, values, 0.0)
    inner = np.trapezoid(values, axis, axis=1)
    total = np.trapezoid(inner, axis)
    return complex(float(spin_degeneracy) * total / (2.0 * math.pi) ** 2)


def k_integral(
    integrand: Callable[[np.ndarray], np.ndarray],
    *,
    k_max_per_nm: float,
    method: str = "radial",
    domain: str = "disc",
    spin_degeneracy: int = 2,
    points: int | None = None,
) -> complex:
    """Dispatch to one implementation. Units: whatever ``integrand`` returns, nm^-2."""

    if method == "radial":
        return radial_integral(
            integrand, k_max_per_nm=k_max_per_nm, domain=domain,
            spin_degeneracy=spin_degeneracy, points=points or 96,
        )
    if method == "cartesian":
        return cartesian_integral(
            integrand, k_max_per_nm=k_max_per_nm, domain=domain,
            spin_degeneracy=spin_degeneracy, points=points or 1201,
        )
    raise KSpace16FError(f"unknown method {method!r}; known: {('radial', 'cartesian')}")


# ---------------------------------------------------------------------------
# The audit itself
# ---------------------------------------------------------------------------


#: Integrands the equivalence test is run on. The constant one isolates pure
#: normalisation; the Lorentzian is the shape Eq. 2 actually produces, peaked at
#: k = 0 and falling on the scale the broadening sets, which is the regime where
#: a mistaken measure would be easiest to miss.
def _probe_integrands(k_max: float) -> Mapping[str, Callable[[np.ndarray], np.ndarray]]:
    width = 0.15 * k_max
    return {
        "constant": lambda k: np.ones_like(np.asarray(k, dtype=float)),
        "gaussian": lambda k: np.exp(-(np.asarray(k, dtype=float) / width) ** 2),
        "lorentzian_resonant": (
            lambda k: 1.0 / (1.0 + (np.asarray(k, dtype=float) / width) ** 2)
        ),
    }


def analytic_disc_constant(k_max: float, spin_degeneracy: int = 2) -> float:
    """``(g_s/(2 pi)^2) * area`` for ``f = 1`` on the disc: ``g_s k^2/(4 pi)``.

    A closed form the numerics are checked against, so "the two agree" cannot be
    two implementations sharing one wrong constant.
    """

    return float(spin_degeneracy) * k_max**2 / (4.0 * math.pi)


def analytic_square_constant(k_max: float, spin_degeneracy: int = 2) -> float:
    """Same for the square: ``g_s (2 k)^2 / (2 pi)^2 = g_s k^2 / pi^2``.

    The ratio to the disc is then ``4/pi``, the ratio of the two areas -- which
    is the assertion in :func:`k_normalisation_audit`. Writing ``pi`` here
    instead of ``pi**2`` was the first thing this audit caught, in its own code.
    """

    return float(spin_degeneracy) * k_max**2 / math.pi**2


def k_normalisation_audit(
    k_max_per_nm: float, *, spin_degeneracy: int = 2
) -> dict[str, Any]:
    """Do the two implementations agree, and do both match the closed form?

    Returns a record rather than raising, so a failure is reported with its
    numbers instead of only its traceback.
    """

    results: list[dict[str, Any]] = []
    for domain in ("disc", "square"):
        analytic = (
            analytic_disc_constant(k_max_per_nm, spin_degeneracy)
            if domain == "disc"
            else analytic_square_constant(k_max_per_nm, spin_degeneracy)
        )
        for name, function in _probe_integrands(k_max_per_nm).items():
            radial = radial_integral(
                function, k_max_per_nm=k_max_per_nm, domain=domain,
                spin_degeneracy=spin_degeneracy, points=2001,
            )
            cartesian = cartesian_integral(
                function, k_max_per_nm=k_max_per_nm, domain=domain,
                spin_degeneracy=spin_degeneracy, points=1201,
            )
            scale = max(abs(radial), abs(cartesian))
            relative = abs(radial - cartesian) / scale if scale else 0.0
            row = {
                "domain": domain,
                "integrand": name,
                "radial": float(radial.real),
                "cartesian": float(cartesian.real),
                "relative_difference": float(relative),
                "agrees": bool(relative <= K_METHOD_AGREEMENT_TOLERANCE),
            }
            if name == "constant":
                row["analytic"] = float(analytic)
                row["radial_vs_analytic"] = float(
                    abs(radial.real - analytic) / analytic
                )
                row["cartesian_vs_analytic"] = float(
                    abs(cartesian.real - analytic) / analytic
                )
                # Only one of these four numbers is exact arithmetic: on the disc
                # the radial route's angular integral is the closed form 2*pi, so
                # a constant integrand must reproduce the analytic area to
                # machine precision. The Cartesian route resolves a curved
                # boundary on a square grid, and the radial route on the square
                # quadratures an angle-dependent outer radius; both are numerical
                # and are held to the quadrature tolerance.
                row["radial_is_exact_path"] = domain == "disc"
                radial_budget = (
                    1.0e-12 if domain == "disc" else K_METHOD_AGREEMENT_TOLERANCE
                )
                row["matches_closed_form"] = bool(
                    row["radial_vs_analytic"] <= radial_budget
                    and row["cartesian_vs_analytic"] <= K_METHOD_AGREEMENT_TOLERANCE
                )
            results.append(row)

    disc = analytic_disc_constant(k_max_per_nm, spin_degeneracy)
    square = analytic_square_constant(k_max_per_nm, spin_degeneracy)
    return {
        "k_max_per_nm": float(k_max_per_nm),
        "spin_degeneracy": int(spin_degeneracy),
        "tolerance": K_METHOD_AGREEMENT_TOLERANCE,
        "tolerance_note": (
            "set by the Cartesian route resolving the circular boundary to one "
            "cell, not by physics; every factor this test screens for (2*pi, "
            "spin, 4/pi) is far larger"
        ),
        "comparisons": results,
        "square_over_disc_area_ratio": float(square / disc),
        "square_over_disc_expected": 4.0 / math.pi,
        "all_methods_agree": all(row["agrees"] for row in results),
        "closed_form_reproduced": all(
            row.get("matches_closed_form", True) for row in results
        ),
    }
