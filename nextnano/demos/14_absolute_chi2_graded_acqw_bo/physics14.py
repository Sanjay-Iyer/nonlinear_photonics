"""Demo 14 absolute chi(2): configuration, diagnostics, and independent checks.

The susceptibility model itself lives in ``_shared/chi2.py`` and is not
reimplemented here -- it already carries the Ramesh Eq. 2/3 triple sum, the
radial in-plane integral and an ``absolute`` mode that emits pm/V. What this
module adds is everything Demo 14 needs *around* it:

* the two unpublished constants, with provenance attached to the value rather
  than to a comment (:data:`R_E_HH_NM`, :func:`n_z_for`);
* an **independent** angular-frequency implementation of the same equation, so
  the shipped energy-form result is checked against a second derivation rather
  than against itself;
* an **independent** Cartesian (kx, ky) quadrature, so the radial reduction is
  checked the same way;
* the convergence and sensitivity reports the spec requires before any absolute
  number is called validated.

Nothing here fits a scale factor. Every multiplicative constant traces to a
source recorded in ``docs/demo14_physics_sources.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np

import chi2 as chi2mod

# --- constants, with provenance -------------------------------------------

#: Bloch interband position matrix element <u_e|r|u_hh>, Ramesh et al.,
#: Appl. Phys. Lett. 123, 251111 (2023), from VASP/HSE06. Verified verbatim
#: against the PDF in the repository root.
#:
#: This is a POSITION matrix element. Eq. (3) already carries e^3, so it must
#: never be multiplied by the electron charge on the way in.
R_E_HH_NM: float = 0.751
R_E_HH_PROVENANCE: str = (
    "Ramesh et al., Appl. Phys. Lett. 123, 251111 (2023), doi 10.1063/5.0168596: "
    "'the interband matrix element of the unit cell wavefunctions was determined "
    "to be r_e,hh = 7.51 Angstrom using density functional theory (DFT) performed "
    "with the Vienna Ab initio Simulation Package using HSE06 hybrid functionals'. "
    "Position matrix element, not e*r."
)

#: Reference period of the Ramesh 2026 structure: 18.2 + 7.1 + 1.8 + 2.9 nm.
#: The body text's "20 nm" contradicts both the figure caption and this sum and
#: is treated as a typo; see paper_targets.yaml.
REFERENCE_PERIOD_NM: float = 30.0

NZ_MODES: tuple[str, ...] = ("period_density", "well_density")


def n_z_for(mode: str, period_nm: float, wells_per_period: int = 2) -> float:
    """N_z in m^-1 for a named counting convention.

    Ramesh 2023 says only "the number of QWs per unit length", which does not
    distinguish a coupled *pair* from its two individual wells. Both readings are
    implemented so the ambiguity can be measured (:func:`n_z_sensitivity`)
    instead of being buried in a constant.
    """

    if mode not in NZ_MODES:
        raise ValueError(f"N_z mode must be one of {NZ_MODES}, got {mode!r}.")
    if not math.isfinite(period_nm) or period_nm <= 0:
        raise ValueError(f"period must be finite and > 0, got {period_nm!r}.")
    per_period = 1.0 if mode == "period_density" else float(wells_per_period)
    return per_period / (float(period_nm) * 1.0e-9)


#: Brillouin-zone edge conventions. The papers state "one-tenth of the Brillouin
#: zone" without saying which edge, and the choice is a direct multiplier on the
#: k measure, so it is named rather than embedded.
BZ_EDGE_CONVENTIONS: Mapping[str, float] = {
    "legacy_pi_over_a": math.pi,
    "crystallographic_two_pi_over_a": 2.0 * math.pi,
}


def k_max_per_nm(
    *, fraction_of_bz: float, lattice_constant_nm: float, convention: str
) -> float:
    try:
        numerator = BZ_EDGE_CONVENTIONS[convention]
    except KeyError:
        raise ValueError(
            f"unknown zone-edge convention {convention!r}; "
            f"supported: {', '.join(BZ_EDGE_CONVENTIONS)}"
        ) from None
    return float(fraction_of_bz) * numerator / float(lattice_constant_nm)


def settings_from_config(cfg: Mapping[str, Any]) -> chi2mod.Chi2Settings:
    """Build ``Chi2Settings`` in absolute mode from the Demo 14 YAML."""

    metric = dict(cfg.get("chi2") or {})
    kpar = dict(cfg.get("k_parallel") or {})
    mode = str(metric.get("nz_mode", "period_density"))
    period = float(metric.get("reference_period_nm", REFERENCE_PERIOD_NM))
    n_z = metric.get("n_wells_per_metre")
    if n_z is None:
        n_z = n_z_for(mode, period, int(metric.get("wells_per_period", 2)))
    return chi2mod.Chi2Settings(
        mode=str(metric.get("mode", "absolute")),
        broadening_meV=float(metric.get("broadening_meV", 5.0)),
        k_parallel_fraction_of_bz=float(kpar.get("fraction_of_bz", 0.10)),
        k_parallel_points=int(kpar.get("points", 96)),
        lattice_constant_nm=float(kpar.get("lattice_constant_nm", 0.565325)),
        electron_mass_m0=float(kpar.get("electron_mass_m0", 0.067)),
        heavy_hole_inplane_mass_m0=float(kpar.get("heavy_hole_inplane_mass_m0", 0.112)),
        spin_degeneracy=int(kpar.get("spin_degeneracy", 2)),
        max_states_per_band=int(metric.get("max_states_per_band", 2)),
        r_e_hh_nm=float(metric.get("r_e_hh_nm", R_E_HH_NM)),
        n_wells_per_metre=float(n_z),
    )


# --- independent angular-frequency implementation --------------------------
#
# The shipped model writes the two denominators in ENERGY, which cancels the
# hbar^2 that Eq. (3) carries explicitly. That is a legitimate rewriting, but it
# is exactly the kind of step that hides a factor. Re-deriving the same number
# with the published angular-frequency denominators -- where Gamma must be
# converted to rad/s and the hbar^2 stays in the prefactor -- is the check.

HBAR_J_S = chi2mod.REDUCED_PLANCK_J_S
Q_E = chi2mod.ELEMENTARY_CHARGE_C
EPS0 = chi2mod.VACUUM_PERMITTIVITY_F_PER_M


@dataclass(frozen=True)
class Chi2Comparison:
    energy_form: complex
    angular_frequency_form: complex

    @property
    def relative_difference(self) -> float:
        scale = max(abs(self.energy_form), abs(self.angular_frequency_form))
        if scale == 0.0:
            return 0.0
        return abs(self.energy_form - self.angular_frequency_form) / scale


def chi2_angular_frequency_form(
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    photon_energy_eV: float,
    settings: chi2mod.Chi2Settings,
) -> complex:
    """Ramesh Eq. (3) with rad/s denominators and an explicit ``1/hbar^2``.

    Deliberately written from the published form rather than by rescaling the
    energy-form result: a cross-check that shares code proves nothing.
    """

    n_e = min(int(settings.max_states_per_band), electron.count)
    n_h = min(int(settings.max_states_per_band), heavy_hole.count)
    overlap = chi2mod.overlap_matrix(electron, heavy_hole)
    z_e = chi2mod.position_matrix(electron)          # nm
    z_h = chi2mod.position_matrix(heavy_hole)        # nm

    k, weights = chi2mod._k_grid(settings)           # nm^-1, nm^-2
    transitions_eV = chi2mod._transition_energies_eV(electron, heavy_hole, k, settings)
    # eV -> rad/s
    omega = transitions_eV * Q_E / HBAR_J_S
    w = float(photon_energy_eV) * Q_E / HBAR_J_S
    gamma_rad_s = (float(settings.broadening_meV) * 1.0e-3 * Q_E) / HBAR_J_S

    two_photon = omega - 2.0 * w + 1j * gamma_rad_s
    one_photon = omega - w + 1j * gamma_rad_s

    accumulated = np.zeros(k.size, dtype=complex)
    for m in range(n_h):
        for n in range(n_e):
            for l in range(n_e):
                num = overlap[n, m] * z_e[n, l] * overlap[l, m]
                if num:
                    accumulated += num / (two_photon[n, m] * one_photon[l, m])
            for l in range(n_h):
                num = overlap[n, m] * z_h[m, l] * overlap[n, l]
                if num:
                    accumulated -= num / (two_photon[n, m] * one_photon[n, l])
    total = complex(np.dot(weights, accumulated))

    # Units in the sum: z in nm, weights in nm^-2, denominators in (rad/s)^-2.
    # Convert length nm->m and the k measure nm^-2 -> m^-2.
    total *= 1.0e-9 * 1.0e18
    r_m = float(settings.r_e_hh_nm) * 1.0e-9
    prefactor = (
        float(settings.n_wells_per_metre)
        * Q_E**3
        * r_m**2
        / (6.0 * EPS0 * HBAR_J_S**2)
    )
    return complex(prefactor * total * 1.0e12)       # m/V -> pm/V


def compare_formulations(
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    photon_energy_eV: float,
    settings: chi2mod.Chi2Settings,
) -> Chi2Comparison:
    """Same physics, two derivations. They must agree."""

    energy = chi2mod.chi2_spectrum(
        electron, heavy_hole, [photon_energy_eV], settings
    ).chi2[0]
    angular = chi2_angular_frequency_form(
        electron, heavy_hole, photon_energy_eV, settings
    )
    return Chi2Comparison(complex(energy), angular)


# --- independent Cartesian k quadrature ------------------------------------


def k_measure_radial(settings: chi2mod.Chi2Settings) -> float:
    """``sum of weights`` for the shipped radial grid, in nm^-2."""

    _, weights = chi2mod._k_grid(settings)
    return float(np.sum(weights))


def k_measure_cartesian(settings: chi2mod.Chi2Settings, points_per_axis: int = 601) -> float:
    """The same measure by direct 2D (kx, ky) quadrature over the disc.

    ``(1/A) sum_k -> int d^2k/(2 pi)^2`` restricted to ``|k| <= k_max``. For a
    constant integrand this must equal the radial result, which is what makes it
    a check on the ``k/(2 pi)`` reduction rather than a restatement of it.
    """

    k_max = settings.k_max_per_nm
    axis = np.linspace(-k_max, k_max, int(points_per_axis))
    kx, ky = np.meshgrid(axis, axis, indexing="ij")
    inside = (kx**2 + ky**2) <= k_max**2
    cell = (axis[1] - axis[0]) ** 2
    area = float(np.count_nonzero(inside)) * cell
    return area / (2.0 * math.pi) ** 2 * float(settings.spin_degeneracy)


def k_convergence_report(
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    photon_energy_eV: float,
    settings: chi2mod.Chi2Settings,
    point_counts: Sequence[int] = (48, 96, 192, 384),
    tolerance: float = 1.0e-3,
) -> dict[str, Any]:
    """Objective versus in-plane grid density, and whether it has converged.

    Convergence is judged against the *finest* grid, not against the neighbour,
    so a slowly drifting integral cannot pass by taking small steps.
    """

    values: dict[int, complex] = {}
    for count in point_counts:
        probe = with_settings(settings, k_parallel_points=int(count))
        values[int(count)] = complex(
            chi2mod.chi2_spectrum(electron, heavy_hole, [photon_energy_eV], probe).chi2[0]
        )
    finest = values[max(values)]
    production = values.get(int(settings.k_parallel_points), finest)
    denominator = abs(finest) if abs(finest) else 1.0
    relative = abs(production - finest) / denominator
    return {
        "k_parallel_cutoff_used": settings.k_max_per_nm,
        "k_parallel_cutoff_fraction_bz": settings.k_parallel_fraction_of_bz,
        "k_parallel_points_production": int(settings.k_parallel_points),
        "k_parallel_points_tested": [int(c) for c in point_counts],
        "chi2_abs_by_point_count": {str(c): abs(v) for c, v in values.items()},
        "k_parallel_relative_error": float(relative),
        "k_parallel_integration_converged": bool(relative <= float(tolerance)),
        "k_parallel_tolerance": float(tolerance),
        "k_weight_sum_radial_per_nm2": k_measure_radial(settings),
    }


def _settings_with(settings: chi2mod.Chi2Settings, **changes: Any) -> dict[str, Any]:
    """Field dict for a modified copy; ``Chi2Settings`` is frozen."""

    base = {
        "mode": settings.mode,
        "broadening_meV": settings.broadening_meV,
        "k_parallel_fraction_of_bz": settings.k_parallel_fraction_of_bz,
        "k_parallel_points": settings.k_parallel_points,
        "lattice_constant_nm": settings.lattice_constant_nm,
        "electron_mass_m0": settings.electron_mass_m0,
        "heavy_hole_inplane_mass_m0": settings.heavy_hole_inplane_mass_m0,
        "spin_degeneracy": settings.spin_degeneracy,
        "max_states_per_band": settings.max_states_per_band,
        "r_e_hh_nm": settings.r_e_hh_nm,
        "n_wells_per_metre": settings.n_wells_per_metre,
    }
    base.update(changes)
    return base


def with_settings(settings: chi2mod.Chi2Settings, **changes: Any) -> chi2mod.Chi2Settings:
    return chi2mod.Chi2Settings(**_settings_with(settings, **changes))


# --- sensitivity reports ---------------------------------------------------


def n_z_sensitivity(
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    photon_energy_eV: float,
    settings: chi2mod.Chi2Settings,
    period_nm: float = REFERENCE_PERIOD_NM,
) -> dict[str, Any]:
    """chi(2) under each supported N_z reading.

    Reported so the reader can see how much of the absolute number rests on an
    ambiguity in one sentence of the source paper. Never used to select the
    reading that best matches a published value.
    """

    rows = []
    for mode in NZ_MODES:
        n_z = n_z_for(mode, period_nm)
        probe = with_settings(settings, n_wells_per_metre=n_z)
        value = chi2mod.chi2_spectrum(
            electron, heavy_hole, [photon_energy_eV], probe
        ).chi2[0]
        rows.append(
            {"nz_mode": mode, "n_wells_per_metre": n_z, "chi2_abs_pm_per_V": abs(value)}
        )
    return {"period_nm": period_nm, "readings": rows, "fitted": False}


def cutoff_sensitivity(
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    photon_energy_eV: float,
    settings: chi2mod.Chi2Settings,
) -> dict[str, Any]:
    """chi(2) under each zone-edge convention, measured rather than assumed.

    The naive expectation is that doubling the cutoff scales the answer by the
    4x change in disc area, but the integrand is not constant over the disc, so
    the real ratio is whatever the integral says. This reports the integral.
    """

    rows = []
    for convention in BZ_EDGE_CONVENTIONS:
        k_max = k_max_per_nm(
            fraction_of_bz=settings.k_parallel_fraction_of_bz,
            lattice_constant_nm=settings.lattice_constant_nm,
            convention=convention,
        )
        # Chi2Settings defines k_max = fraction * pi / a, so emulating a
        # 2*pi/a convention means scaling the fraction by that ratio.
        equivalent_fraction = settings.k_parallel_fraction_of_bz * (
            BZ_EDGE_CONVENTIONS[convention] / math.pi
        )
        probe = with_settings(settings, k_parallel_fraction_of_bz=equivalent_fraction)
        value = chi2mod.chi2_spectrum(
            electron, heavy_hole, [photon_energy_eV], probe
        ).chi2[0]
        rows.append(
            {
                "convention": convention,
                "k_max_per_nm": k_max,
                "chi2_abs_pm_per_V": abs(value),
            }
        )
    return {"conventions": rows, "measured_not_assumed": True}


def constants_record(settings: chi2mod.Chi2Settings) -> dict[str, Any]:
    """Every constant that entered an absolute number, for the trial record."""

    return {
        "r_e_hh_nm": settings.r_e_hh_nm,
        "r_e_hh_m": None if settings.r_e_hh_nm is None else settings.r_e_hh_nm * 1e-9,
        "r_e_hh_provenance": R_E_HH_PROVENANCE,
        "r_e_hh_is_position_matrix_element": True,
        "n_wells_per_metre": settings.n_wells_per_metre,
        "spin_degeneracy": settings.spin_degeneracy,
        "broadening_meV": settings.broadening_meV,
        "vacuum_permittivity_F_per_m": EPS0,
        "elementary_charge_C": Q_E,
        "reduced_planck_J_s": HBAR_J_S,
        "unit_formulation": "energy_form (hbar^2 cancels against energy denominators)",
        "k_parallel_fraction_of_bz": settings.k_parallel_fraction_of_bz,
        "k_parallel_points": settings.k_parallel_points,
        "k_max_per_nm": settings.k_max_per_nm,
        "max_states_per_band": settings.max_states_per_band,
        "scale_factor_fitted": False,
    }
