"""The variant ladder, and an independent chi2 evaluator to walk it with.

One row per convention change, each with the source that requires it. The ladder
is cumulative on purpose: every row differs from the one above it by exactly one
decision, so the table reads as a budget rather than as a set of unrelated runs
and no row's effect can be confused with another's.

The evaluator here is a **second implementation** of Eq. 2, built on
:mod:`kspace16f` and :mod:`eq16f` rather than on the shared ``chi2`` module. That
is deliberate. When the ``legacy`` row reproduces the number Demo 16E already
recorded, two independently written evaluators agree and the production
``chi2.py`` is corroborated; when it does not, one of them is wrong and the audit
has found something. Reusing ``chi2.py`` here would have made that check
impossible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np

import conventions16f as conv
import eq16f
import kspace16f as kspace

#: Photon energy of a wavelength, and back. hc in eV nm.
HC_EV_NM = 1239.841984

#: In-plane masses, taken from the shared chi2 module's defaults so the two
#: evaluators differ only where this demo intends them to.
ELECTRON_MASS_M0 = 0.067
HEAVY_HOLE_INPLANE_MASS_M0 = 0.112

#: Quadrature resolution per method. The radial route matches the shared chi2
#: module's 96 points so the ``legacy`` rung is comparable with Demo 16E's
#: recorded number rather than differing from it by quadrature. The Cartesian
#: route needs a genuine 2D grid; 601 puts a few hundred thousand points in the
#: plane, which resolves the circular boundary to about 0.7% -- inside the 1%
#: agreement tolerance and small enough to hold in memory once the integrand is
#: vectorised over k.
DEFAULT_K_POINTS: dict[str, int] = {"radial": 96, "cartesian": 601}


def photon_energy_eV(wavelength_nm: float) -> float:
    return HC_EV_NM / float(wavelength_nm)


def reduced_mass_kg() -> float:
    reduced = 1.0 / (1.0 / ELECTRON_MASS_M0 + 1.0 / HEAVY_HOLE_INPLANE_MASS_M0)
    return reduced * kspace.ELECTRON_MASS_KG


def kinetic_shift_eV(k_per_nm: np.ndarray) -> np.ndarray:
    """``hbar^2 k^2 / (2 m_reduced)`` in eV, for in-plane k in nm^-1.

    Electrons disperse up and holes down on the single electron-energy scale
    nextnano++ reports, so an interband transition energy *rises* with in-plane
    k by exactly this amount.
    """

    k_per_m = np.asarray(k_per_nm, dtype=float) * 1.0e9
    joules = (kspace.REDUCED_PLANCK_J_S**2) * k_per_m**2 / (2.0 * reduced_mass_kg())
    return joules / kspace.ELEMENTARY_CHARGE_C


# ---------------------------------------------------------------------------
# The evaluator
# ---------------------------------------------------------------------------


def chi2_at(
    states: eq16f.StateSet,
    convention: conv.Convention,
    wavelength_nm: float,
    *,
    broadening_eV: float = 5.0e-3,
    k_points: int | None = None,
) -> complex:
    """chi2_xzx at one wavelength, under one set of conventions, in pm/V.

    Every factor passes through :func:`kspace16f.dimensional_ledger`'s vocabulary
    -- N_z in m^-1, r^2 in m^2, the k integral in m^-2, the position matrix
    element in m, the denominators in J^-2 -- so the returned number closes on
    m/V by construction rather than by a conversion constant someone remembered.
    """

    hw = photon_energy_eV(wavelength_nm)

    def integrand(k_per_nm: np.ndarray) -> np.ndarray:
        return np.asarray(
            eq16f.eq2_state_sum(
                states, hw, broadening_eV=broadening_eV,
                transition_shift_eV=kinetic_shift_eV(k_per_nm),
            ),
            dtype=complex,
        )

    k_sum = kspace.k_integral(
        integrand,
        k_max_per_nm=convention.k_max_per_nm,
        method=convention.k_method,
        domain=convention.k_domain,
        spin_degeneracy=2,
        points=k_points or DEFAULT_K_POINTS[convention.k_method],
    )

    r_m = float(states.r_e_hh_nm) * 1.0e-9
    # nm -> m on <z> (inside the state sum), nm^-2 -> m^-2 on the k integral,
    # eV^-2 -> J^-2 on the denominators, m/V -> pm/V at the end.
    unit_conversion = 1.0e-9 * 1.0e18 / (kspace.ELEMENTARY_CHARGE_C**2)
    prefactor = (
        convention.n_wells_per_metre
        * kspace.ELEMENTARY_CHARGE_C**3
        * r_m**2
        / (eq16f.EQ2_PREFACTOR_DENOMINATOR * kspace.VACUUM_PERMITTIVITY_F_PER_M)
    ) * unit_conversion * 1.0e12
    return complex(prefactor * k_sum * convention.heavy_hole_mj_factor)


def spectrum(
    states: eq16f.StateSet,
    convention: conv.Convention,
    wavelengths_nm: Sequence[float],
    *,
    broadening_eV: float = 5.0e-3,
) -> np.ndarray:
    """|chi2_xzx| over a wavelength grid, pm/V."""

    return np.array([
        abs(chi2_at(states, convention, float(nm), broadening_eV=broadening_eV))
        for nm in wavelengths_nm
    ])


# ---------------------------------------------------------------------------
# The ladder
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Variant:
    """One rung: what changed, why it is allowed to change, and what it costs."""

    name: str
    convention: conv.Convention
    changed: str
    because: str

    def as_record(self) -> dict[str, Any]:
        return {
            "variant": self.name,
            "changed": self.changed,
            "because": self.because,
            **self.convention.as_record(),
        }


#: Cumulative, one decision per rung. ``legacy`` is what Demo 14/16E production
#: computed and exists so the first row of every table is a number already on
#: record. ``independent_cartesian`` changes no physics at all -- it swaps the k
#: integral for its independent implementation, so it must reproduce the row
#: above it exactly. A difference there would be the normalisation bug the whole
#: audit is looking for.
def ladder() -> tuple[Variant, ...]:
    legacy = conv.LEGACY
    paper_nz = conv.Convention(
        nz="well_density", zone_edge="legacy_pi_over_a",
        k_domain="disc", k_method="radial",
    )
    paper_nz_and_zone = conv.FAITHFUL
    independent = conv.Convention(
        nz="well_density", zone_edge="gamma_to_x_2pi_over_a",
        k_domain="disc", k_method="cartesian",
    )
    square = conv.Convention(
        nz="well_density", zone_edge="gamma_to_x_2pi_over_a",
        k_domain="square", k_method="radial",
    )
    with_mj = conv.Convention(
        nz="well_density", zone_edge="gamma_to_x_2pi_over_a",
        k_domain="disc", k_method="radial", heavy_hole_mj_applied=True,
    )
    return (
        Variant(
            "legacy", legacy,
            "nothing; Demo 14/16E production settings",
            "the number already on record, so the ladder starts from a known "
            "value rather than a re-derivation",
        ),
        Variant(
            "paper_Nz", paper_nz,
            "N_z: period density -> well density (x2)",
            conv.NZ_DEFINITIONS["well_density"].source,
        ),
        Variant(
            "paper_Nz_and_zone", paper_nz_and_zone,
            "Brillouin-zone edge: pi/a -> 2 pi/a (k_max x2)",
            conv.ZONE_EDGES["gamma_to_x_2pi_over_a"].source,
        ),
        Variant(
            "independent_cartesian", independent,
            "k integral: radial -> Cartesian (kx, ky); no physics changes",
            "a control, not a correction: an independent implementation of the "
            "same integral must reproduce the row above exactly, which is the "
            "test for a missing or duplicated 2*pi, spin or area factor",
        ),
        Variant(
            "square_domain", square,
            "k domain: disc -> square (area x 4/pi)",
            "the alternative reading of 'one-tenth of the Brillouin zone'; "
            "reported as a sensitivity, not promoted -- the paper's saturation "
            "argument is isotropic and therefore describes a radius",
        ),
        Variant(
            "open_hh_mj_factor", with_mj,
            "heavy-hole m_j = +/-3/2 multiplicity applied (x2)",
            "an OPEN factor the paper does not state. Reported so its size is "
            "visible; never promoted on the grounds that it improves agreement",
        ),
    )


#: Rows the audit is allowed to call production. A variant is promotable only if
#: every one of its choices has a source that requires it.
def promotable(variant: Variant) -> bool:
    return variant.convention.fully_faithful and not (
        variant.convention.heavy_hole_mj_applied
    )


def evaluate_ladder(
    states: eq16f.StateSet,
    *,
    wavelength_nm: float = conv.TARGET_WAVELENGTH_NM,
    broadening_eV: float = 5.0e-3,
) -> dict[str, Any]:
    """Walk every rung and report chi2(1550) against the paper's stated target."""

    target = conv.PRIMARY_TARGET
    rows: list[dict[str, Any]] = []
    previous: float | None = None
    for variant in ladder():
        value = abs(chi2_at(
            states, variant.convention, wavelength_nm,
            broadening_eV=broadening_eV,
        ))
        rows.append({
            **variant.as_record(),
            "chi2_at_1550_pm_per_V": value,
            "factor_vs_previous": (
                None if previous in (None, 0.0) else value / previous
            ),
            "factor_vs_legacy": (
                None if not rows else value / rows[0]["chi2_at_1550_pm_per_V"]
            ),
            "shortfall_vs_target": (
                None if value == 0.0 else target.value_pm_per_V / value
            ),
            "promotable": promotable(variant),
        })
        previous = value

    control = next(
        (row for row in rows if row["variant"] == "independent_cartesian"), None
    )
    reference = next(
        (row for row in rows if row["variant"] == "paper_Nz_and_zone"), None
    )
    control_ratio = (
        None if control is None or reference is None
        or not reference["chi2_at_1550_pm_per_V"]
        else control["chi2_at_1550_pm_per_V"] / reference["chi2_at_1550_pm_per_V"]
    )
    return {
        "wavelength_nm": float(wavelength_nm),
        "tensor_quantity": conv.TENSOR_QUANTITY,
        "tensor_declaration": conv.TENSOR_DECLARATION,
        "target": {
            "name": target.name,
            "value_pm_per_V": target.value_pm_per_V,
            "source": target.source,
        },
        "held_fixed": dict(conv.HELD_FIXED),
        "rows": rows,
        "independent_implementation_ratio": control_ratio,
        "independent_implementations_agree": (
            control_ratio is not None
            and abs(control_ratio - 1.0) <= kspace.K_METHOD_AGREEMENT_TOLERANCE
        ),
        "best_promotable_pm_per_V": max(
            (row["chi2_at_1550_pm_per_V"] for row in rows if row["promotable"]),
            default=None,
        ),
    }
