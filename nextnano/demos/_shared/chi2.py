"""Interband second-order susceptibility of a coupled quantum well.

This implements Eq. 2 of *Enhanced Interband Optical Nonlinearities from
Coupled Quantum Wells* (arXiv:2602.23246v1):

.. math::

    \\chi^{(2)}_{xzx}(\\omega_1,\\omega_2) =
      \\frac{N_z e^3 r_{e,hh}^2}{6\\epsilon_0\\hbar^2}
      \\sum_{k_\\parallel}\\sum_{m,n}\\sum_l\\Bigl[
        \\frac{\\langle\\psi_{hh,m}|\\psi_{e,n}\\rangle
               \\langle\\psi_{e,n}|z|\\psi_{e,l}\\rangle
               \\langle\\psi_{e,l}|\\psi_{hh,m}\\rangle}
             {(\\omega^{e,n}_{hh,m}-\\omega_1-\\omega_2+i\\Gamma)
              (\\omega^{e,l}_{hh,m}-\\omega_1+i\\Gamma)}
      - \\frac{\\langle\\psi_{e,n}|\\psi_{hh,m}\\rangle
               \\langle\\psi_{hh,m}|z|\\psi_{hh,l}\\rangle
               \\langle\\psi_{hh,l}|\\psi_{e,n}\\rangle}
             {(\\omega^{e,n}_{hh,m}-\\omega_1-\\omega_2+i\\Gamma)
              (\\omega^{e,n}_{hh,l}-\\omega_1+i\\Gamma)}\\Bigr]

THIS IS NOT ``nlo.py``
======================

``nlo.py`` holds a deliberately *relative* three-level design metric that must
never be called a susceptibility. This module is the opposite: it computes the
paper's actual susceptibility, and it may legitimately be reported in pm/V --
but **only** in ``absolute`` mode, and only when every quantity the absolute
scale depends on has been supplied explicitly. There is no default value for
any of them, because the paper does not publish them.

THREE MODES
===========

``relative``
    Uses only nextnano energies and envelope matrix elements. Returns the
    lineshape and relative magnitude in arbitrary units. This is the default,
    and it is the only mode that needs nothing beyond the solver output. Its
    resonance positions and its asymmetry / barrier / wavelength *trends* are
    fully meaningful; its overall scale is not.

``absolute``
    Requires ``r_e_hh_nm`` (the HSE06 unit-cell interband matrix element) and
    ``n_wells_per_metre`` (:math:`N_z`). The paper publishes neither number, so
    this mode refuses to run until they are supplied from another source. It
    returns pm/V.

``calibrated``
    Fits ONE global real scale factor to ONE published value, then predicts
    everything else without further fitting. Every artifact is stamped
    ``calibrated reproduction``; it is not an independent absolute prediction.

WHAT THE PAPER DOES NOT SPECIFY
===============================

Recorded here because they set the absolute scale and cannot be recovered from
the text:

* the numerical value of :math:`r_{e,hh}` from the HSE06 calculation;
* whether :math:`N_z` counts coupled-well *pairs* or individual wells per unit
  length (the paper's own text says "each period is 20 nm" while its Fig. 1
  caption and its layer arithmetic both give 30 nm);
* the normalisation of :math:`\\sum_{k_\\parallel}`. Dimensional analysis fixes
  it: only :math:`\\frac{1}{A}\\sum \\to \\int d^2k/(2\\pi)^2` makes the
  right-hand side come out in m/V, and that is what is used here;
* whether the spin degeneracy factor is folded into that sum;
* the in-plane effective masses used for :math:`\\omega(k_\\parallel)`.

Every one of these is an explicit, named setting rather than a buried constant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

import numpy as np

# --- physical constants (CODATA 2018), in SI unless the name says otherwise ---
ELEMENTARY_CHARGE_C = 1.602176634e-19
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
REDUCED_PLANCK_J_S = 1.054571817e-34
ELECTRON_MASS_KG = 9.1093837015e-31
SPEED_OF_LIGHT_M_PER_S = 299792458.0
#: hc in eV*nm, for photon-energy <-> wavelength conversion.
HC_EV_NM = 1239.841984

MODES = ("relative", "absolute", "calibrated")
Mode = Literal["relative", "absolute", "calibrated"]

RELATIVE_UNITS = "arbitrary (relative lineshape and trend; absolute scale not set)"
ABSOLUTE_UNITS = "pm/V"
CALIBRATED_UNITS = "pm/V (calibrated to one published value, not independent)"


class Chi2Error(ValueError):
    """Raised when the requested calculation is not defensible as configured."""


def photon_energy_eV(wavelength_nm: float | np.ndarray) -> np.ndarray:
    """Photon energy in eV for a vacuum wavelength in nm."""

    values = np.asarray(wavelength_nm, dtype=float)
    if np.any(values <= 0):
        raise Chi2Error("wavelength must be positive.")
    return HC_EV_NM / values


def wavelength_nm(photon_energy_eV: float | np.ndarray) -> np.ndarray:
    """Vacuum wavelength in nm for a photon energy in eV."""

    values = np.asarray(photon_energy_eV, dtype=float)
    if np.any(values <= 0):
        raise Chi2Error("photon energy must be positive.")
    return HC_EV_NM / values


@dataclass(frozen=True)
class BandStates:
    """Bound envelope states of one band, on a shared position grid.

    ``energies_eV`` are on nextnano's single electron-energy scale, so an
    interband transition is simply ``E_electron - E_hole``. ``envelopes`` is
    ``(n_points, n_states)``; it is normalised on construction so that
    ``int |psi|^2 dz = 1`` for every state.
    """

    z_nm: np.ndarray
    energies_eV: np.ndarray
    envelopes: np.ndarray
    label: str = ""

    def __post_init__(self) -> None:
        z = np.asarray(self.z_nm, dtype=float)
        energies = np.asarray(self.energies_eV, dtype=float)
        envelopes = np.atleast_2d(np.asarray(self.envelopes, dtype=float))
        if z.ndim != 1 or z.size < 3:
            raise Chi2Error(f"{self.label or 'band'}: z_nm must be a 1D grid.")
        if not np.all(np.diff(z) > 0):
            raise Chi2Error(f"{self.label or 'band'}: z_nm must increase strictly.")
        if envelopes.shape[0] != z.size:
            envelopes = envelopes.T
        if envelopes.shape[0] != z.size:
            raise Chi2Error(
                f"{self.label or 'band'}: envelopes do not match the position grid."
            )
        if envelopes.shape[1] != energies.size:
            raise Chi2Error(
                f"{self.label or 'band'}: {envelopes.shape[1]} envelope(s) for "
                f"{energies.size} energies."
            )
        if not np.isfinite(energies).all() or not np.isfinite(envelopes).all():
            raise Chi2Error(f"{self.label or 'band'}: non-finite input.")
        normalised = np.empty_like(envelopes)
        for index in range(envelopes.shape[1]):
            norm = float(np.trapezoid(envelopes[:, index] ** 2, z))
            if not math.isfinite(norm) or norm <= 0:
                raise Chi2Error(
                    f"{self.label or 'band'}: state {index + 1} has zero norm."
                )
            normalised[:, index] = envelopes[:, index] / math.sqrt(norm)
        object.__setattr__(self, "z_nm", z)
        object.__setattr__(self, "energies_eV", energies)
        object.__setattr__(self, "envelopes", normalised)

    @property
    def count(self) -> int:
        return int(self.energies_eV.size)

    def gram_matrix(self) -> np.ndarray:
        """``<psi_i | psi_j>`` within this band; should be the identity."""

        return np.array(
            [
                [
                    float(
                        np.trapezoid(
                            self.envelopes[:, i] * self.envelopes[:, j], self.z_nm
                        )
                    )
                    for j in range(self.count)
                ]
                for i in range(self.count)
            ]
        )

    def orthonormality_error(self) -> float:
        """``max |<psi_i|psi_j> - delta_ij|``.

        This is not housekeeping. Eq. 2 contains *diagonal* position matrix
        elements ``<psi_i|z|psi_i>``, which individually depend on where the
        origin of z is placed. The origin dependence cancels between the two
        terms of Eq. 2 -- but only if the envelopes within each band are
        orthonormal. With a non-orthogonal basis the computed chi2 depends on an
        arbitrary coordinate choice and is therefore meaningless, so this is
        checked before any spectrum is produced.
        """

        gram = self.gram_matrix()
        return float(np.max(np.abs(gram - np.eye(self.count))))


def overlap_matrix(a: BandStates, b: BandStates) -> np.ndarray:
    """``<psi_a,i | psi_b,j>`` for two bands on the same grid."""

    if a.z_nm.shape != b.z_nm.shape or not np.allclose(a.z_nm, b.z_nm):
        raise Chi2Error("bands must share the same position grid.")
    return np.array(
        [
            [
                float(np.trapezoid(a.envelopes[:, i] * b.envelopes[:, j], a.z_nm))
                for j in range(b.count)
            ]
            for i in range(a.count)
        ]
    )


def position_matrix(band: BandStates) -> np.ndarray:
    """``<psi_i | z | psi_j>`` within one band, in nm."""

    return np.array(
        [
            [
                float(
                    np.trapezoid(
                        band.envelopes[:, i] * band.z_nm * band.envelopes[:, j],
                        band.z_nm,
                    )
                )
                for j in range(band.count)
            ]
            for i in range(band.count)
        ]
    )


@dataclass(frozen=True)
class Chi2Settings:
    """Every convention the calculation depends on, named and explicit."""

    mode: Mode = "relative"
    #: Line broadening. The paper states 5 meV.
    broadening_meV: float = 5.0
    #: In-plane integration limit, as a fraction of the Brillouin-zone edge.
    #: The paper integrates to one-tenth of the zone.
    k_parallel_fraction_of_bz: float = 0.1
    k_parallel_points: int = 96
    #: Brillouin-zone edge is taken as pi/a. GaAs a = 0.565325 nm.
    lattice_constant_nm: float = 0.565325
    #: In-plane effective masses for omega(k_par). The paper does not state
    #: which values it used; these are the standard GaAs ones and are recorded
    #: with every result.
    electron_mass_m0: float = 0.067
    heavy_hole_inplane_mass_m0: float = 0.112
    #: Folded into the k-sum. The paper does not say whether it did this.
    spin_degeneracy: int = 2
    #: --- absolute mode only; no defaults, because the paper publishes none ---
    r_e_hh_nm: float | None = None
    n_wells_per_metre: float | None = None
    #: --- calibrated mode only ---
    calibration_target_pm_per_V: float | None = None
    calibration_wavelength_nm: float | None = None
    calibration_source: str = ""

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise Chi2Error(f"mode must be one of {MODES}, got {self.mode!r}.")
        for name in (
            "broadening_meV",
            "k_parallel_fraction_of_bz",
            "lattice_constant_nm",
            "electron_mass_m0",
            "heavy_hole_inplane_mass_m0",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0:
                raise Chi2Error(f"{name} must be finite and > 0.")
        if int(self.k_parallel_points) < 2:
            raise Chi2Error("k_parallel_points must be at least 2.")
        if int(self.spin_degeneracy) not in (1, 2):
            raise Chi2Error("spin_degeneracy must be 1 or 2.")
        if self.mode == "absolute":
            missing = [
                name
                for name in ("r_e_hh_nm", "n_wells_per_metre")
                if getattr(self, name) is None
            ]
            if missing:
                raise Chi2Error(
                    "absolute mode needs " + " and ".join(missing) + ", and the "
                    "paper publishes neither. Supply them from a documented "
                    "source, or use mode='relative' (trends and resonance "
                    "positions) or mode='calibrated' (one fitted scale factor)."
                )
        if self.mode == "calibrated":
            if self.calibration_target_pm_per_V is None or (
                self.calibration_wavelength_nm is None
            ):
                raise Chi2Error(
                    "calibrated mode needs calibration_target_pm_per_V and "
                    "calibration_wavelength_nm."
                )
            if not self.calibration_source.strip():
                raise Chi2Error(
                    "calibrated mode needs calibration_source naming exactly which "
                    "published value is being fitted."
                )

    @property
    def units(self) -> str:
        return {
            "relative": RELATIVE_UNITS,
            "absolute": ABSOLUTE_UNITS,
            "calibrated": CALIBRATED_UNITS,
        }[self.mode]

    @property
    def k_max_per_nm(self) -> float:
        """Upper in-plane integration limit, in nm^-1."""

        zone_edge = math.pi / float(self.lattice_constant_nm)
        return float(self.k_parallel_fraction_of_bz) * zone_edge

    def reduced_mass_kg(self) -> float:
        """In-plane reduced mass for the interband transition."""

        inverse = 1.0 / float(self.electron_mass_m0) + 1.0 / float(
            self.heavy_hole_inplane_mass_m0
        )
        return ELECTRON_MASS_KG / inverse

    def as_record(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "units": self.units,
            "broadening_meV": self.broadening_meV,
            "k_parallel_fraction_of_bz": self.k_parallel_fraction_of_bz,
            "k_parallel_points": self.k_parallel_points,
            "k_max_per_nm": self.k_max_per_nm,
            "lattice_constant_nm": self.lattice_constant_nm,
            "electron_mass_m0": self.electron_mass_m0,
            "heavy_hole_inplane_mass_m0": self.heavy_hole_inplane_mass_m0,
            "spin_degeneracy": self.spin_degeneracy,
            "r_e_hh_nm": self.r_e_hh_nm,
            "n_wells_per_metre": self.n_wells_per_metre,
            "calibration_target_pm_per_V": self.calibration_target_pm_per_V,
            "calibration_wavelength_nm": self.calibration_wavelength_nm,
            "calibration_source": self.calibration_source or None,
        }


#: Assumptions carried into every artifact this module produces.
ASSUMPTIONS: tuple[str, ...] = (
    "Envelope wavefunctions are taken to be independent of in-plane k; only the "
    "transition energies disperse. This follows the paper, which pulls the "
    "unit-cell matrix element out of the k sum.",
    "In-plane dispersion is parabolic with the reduced electron/heavy-hole mass. "
    "The paper does not state which masses it used.",
    "The sum over in-plane k is read as (1/A) * sum -> integral d^2k/(2*pi)^2. "
    "Dimensional analysis leaves no other choice that yields m/V.",
    "Spin degeneracy is applied as an explicit multiplicative factor; the paper "
    "does not say whether it folded one in.",
    "Only the first two bound states of each band are used, as the paper states.",
    "The Fermi factor is unity: the valence band is full and the conduction band "
    "empty, as the paper states.",
)


@dataclass(frozen=True)
class Chi2Result:
    """Spectrum plus every intermediate that produced it."""

    photon_energy_eV: np.ndarray
    chi2: np.ndarray
    settings: Chi2Settings
    units: str
    scale_factor: float
    assumptions: tuple[str, ...] = ASSUMPTIONS
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    @property
    def magnitude(self) -> np.ndarray:
        return np.abs(self.chi2)

    def at_wavelength(self, wavelength: float) -> complex:
        """Interpolated complex value at one fundamental wavelength."""

        energy = float(photon_energy_eV(wavelength))
        order = np.argsort(self.photon_energy_eV)
        grid = self.photon_energy_eV[order]
        if not grid[0] <= energy <= grid[-1]:
            raise Chi2Error(
                f"{wavelength} nm is outside the computed range "
                f"{wavelength_nm(grid[-1]):.1f}-{wavelength_nm(grid[0]):.1f} nm."
            )
        real = np.interp(energy, grid, self.chi2[order].real)
        imag = np.interp(energy, grid, self.chi2[order].imag)
        return complex(real, imag)

    def peak(self) -> dict[str, float]:
        """Location and height of the largest |chi2| in the computed range."""

        index = int(np.argmax(self.magnitude))
        return {
            "photon_energy_eV": float(self.photon_energy_eV[index]),
            "wavelength_nm": float(wavelength_nm(self.photon_energy_eV[index])),
            "magnitude": float(self.magnitude[index]),
        }


def _k_grid(settings: Chi2Settings) -> tuple[np.ndarray, np.ndarray]:
    """In-plane radial grid and its ``(1/A) sum`` weights, both in nm units.

    ``(1/A) sum_k -> int d^2k/(2*pi)^2 = (1/2*pi) int k dk`` for an isotropic
    integrand. The weights returned already include ``k/(2*pi)``, the radial
    measure, and the spin degeneracy, so a plain dot product performs the sum.
    """

    k_max = settings.k_max_per_nm
    k = np.linspace(0.0, k_max, int(settings.k_parallel_points))
    radial = k / (2.0 * math.pi)
    weights = np.empty_like(k)
    if k.size > 1:
        # Trapezoidal weights for int f(k) * k/(2 pi) dk.
        step = k[1] - k[0]
        weights[:] = step
        weights[0] = weights[-1] = 0.5 * step
    else:  # pragma: no cover - guarded by Chi2Settings
        weights[:] = 1.0
    return k, radial * weights * float(settings.spin_degeneracy)


def _transition_energies_eV(
    electron: BandStates,
    heavy_hole: BandStates,
    k_per_nm: np.ndarray,
    settings: Chi2Settings,
) -> np.ndarray:
    """``E_e,n(k) - E_hh,m(k)`` as ``(n_electron, n_hole, n_k)`` in eV.

    Electrons disperse upward and holes downward on the single electron-energy
    scale nextnano reports, so the transition energy rises with in-plane k by
    ``hbar^2 k^2 / (2 m_reduced)``.
    """

    k_per_m = np.asarray(k_per_nm, dtype=float) * 1.0e9
    kinetic_J = (REDUCED_PLANCK_J_S**2) * k_per_m**2 / (2.0 * settings.reduced_mass_kg())
    kinetic_eV = kinetic_J / ELEMENTARY_CHARGE_C
    zero_k = electron.energies_eV[:, None] - heavy_hole.energies_eV[None, :]
    return zero_k[:, :, None] + kinetic_eV[None, None, :]


def chi2_spectrum(
    electron: BandStates,
    heavy_hole: BandStates,
    photon_energies_eV: Sequence[float] | np.ndarray,
    settings: Chi2Settings | None = None,
    *,
    max_states: int = 2,
    orthonormality_tolerance: float = 1.0e-3,
) -> Chi2Result:
    """Evaluate the paper's Eq. 2 for second-harmonic generation.

    ``photon_energies_eV`` are *fundamental* photon energies; SHG sets
    ``omega_1 = omega_2 = omega``, so the two-photon denominator resonates at
    ``2 hbar omega = E_transition`` and the one-photon denominator at
    ``hbar omega = E_transition``.
    """

    settings = settings or Chi2Settings()
    if electron.count < 1 or heavy_hole.count < 1:
        raise Chi2Error("both bands need at least one bound state.")
    n_e = min(int(max_states), electron.count)
    n_h = min(int(max_states), heavy_hole.count)
    if n_e < max_states or n_h < max_states:
        raise Chi2Error(
            f"the paper's Eq. 2 uses the first {max_states} bound states of each "
            f"band; only {electron.count} electron and {heavy_hole.count} "
            "heavy-hole states are available. A structure that cannot bind them "
            "is outside the reproduction, and truncating silently would change "
            "the physics."
        )

    electron = BandStates(
        electron.z_nm, electron.energies_eV[:n_e], electron.envelopes[:, :n_e], "e"
    )
    heavy_hole = BandStates(
        heavy_hole.z_nm, heavy_hole.energies_eV[:n_h], heavy_hole.envelopes[:, :n_h], "hh"
    )
    # Eq. 2 is only origin-independent for an orthonormal envelope basis; see
    # BandStates.orthonormality_error. Refuse rather than return a number that
    # depends on where z = 0 was put.
    for band in (electron, heavy_hole):
        error = band.orthonormality_error()
        if error > float(orthonormality_tolerance):
            raise Chi2Error(
                f"the {band.label or 'band'} envelopes are not orthonormal "
                f"(max |<i|j> - delta_ij| = {error:.3e} > "
                f"{orthonormality_tolerance:.1e}). Eq. 2 contains diagonal "
                "position matrix elements, so a non-orthogonal basis makes chi2 "
                "depend on the arbitrary choice of the z origin. Check the grid "
                "resolution and that both states come from the same quantum "
                "region before trusting any susceptibility."
            )

    # Matrix elements are k-independent (see ASSUMPTIONS).
    overlap_eh = overlap_matrix(electron, heavy_hole)      # <psi_e,n | psi_hh,m>
    z_e = position_matrix(electron)                        # <psi_e,n | z | psi_e,l>
    z_h = position_matrix(heavy_hole)                      # <psi_hh,m| z | psi_hh,l>

    k, weights = _k_grid(settings)
    transitions = _transition_energies_eV(electron, heavy_hole, k, settings)
    gamma = float(settings.broadening_meV) * 1.0e-3

    energies = np.atleast_1d(np.asarray(photon_energies_eV, dtype=float))
    if np.any(energies <= 0) or not np.isfinite(energies).all():
        raise Chi2Error("photon energies must be finite and positive.")

    total = np.zeros(energies.size, dtype=complex)
    for index, hw in enumerate(energies):
        # Two-photon denominator, shared by both terms: E^{e,n}_{hh,m} - 2*hw.
        two_photon = transitions - 2.0 * hw + 1j * gamma           # (n, m, k)
        one_photon = transitions - hw + 1j * gamma                 # (n, m, k)
        accumulated = np.zeros(k.size, dtype=complex)
        for m in range(n_h):            # heavy-hole state of the pair
            for n in range(n_e):        # electron state
                for l in range(n_e):    # intra-conduction partner
                    numerator = overlap_eh[n, m] * z_e[n, l] * overlap_eh[l, m]
                    if numerator == 0.0:
                        continue
                    accumulated += numerator / (two_photon[n, m] * one_photon[l, m])
                for l in range(n_h):    # intra-valence partner
                    numerator = overlap_eh[n, m] * z_h[m, l] * overlap_eh[n, l]
                    if numerator == 0.0:
                        continue
                    accumulated -= numerator / (two_photon[n, m] * one_photon[n, l])
        total[index] = np.dot(weights, accumulated)

    # --- assemble the prefactor -------------------------------------------
    # chi2 = Nz e^3 r^2 / (6 eps0) * sum, with lengths in m and energies in J.
    # The hbar^2 in the paper's prefactor cancels against the two frequency
    # denominators once those are written in energy rather than angular
    # frequency, which is how they are evaluated above.
    #
    # Bookkeeping of the units actually used above:
    #   matrix elements  nm   * nm^0   -> the z factor carries nm
    #   denominators     eV^2
    #   k weights        nm^-2
    scale = 1.0
    diagnostics: dict[str, Any] = {
        "electron_energies_eV": electron.energies_eV.tolist(),
        "heavy_hole_energies_eV": heavy_hole.energies_eV.tolist(),
        "transition_energies_zero_k_eV": (
            electron.energies_eV[:, None] - heavy_hole.energies_eV[None, :]
        ).tolist(),
        "overlap_electron_hole": overlap_eh.tolist(),
        "position_matrix_electron_nm": z_e.tolist(),
        "position_matrix_heavy_hole_nm": z_h.tolist(),
        "k_max_per_nm": settings.k_max_per_nm,
        "reduced_mass_m0": settings.reduced_mass_kg() / ELECTRON_MASS_KG,
    }

    if settings.mode == "absolute":
        # nm -> m for the z matrix element; nm^-2 -> m^-2 for the k weights;
        # eV^2 -> J^2 for the denominators.
        unit_conversion = 1.0e-9 * 1.0e18 / (ELEMENTARY_CHARGE_C**2)
        r_m = float(settings.r_e_hh_nm) * 1.0e-9
        scale = (
            float(settings.n_wells_per_metre)
            * ELEMENTARY_CHARGE_C**3
            * r_m**2
            / (6.0 * VACUUM_PERMITTIVITY_F_PER_M)
        ) * unit_conversion
        # m/V -> pm/V
        scale *= 1.0e12
        diagnostics["prefactor_m_per_V_per_summand"] = scale / 1.0e12

    return Chi2Result(
        photon_energy_eV=energies,
        chi2=total * scale,
        settings=settings,
        units=settings.units,
        scale_factor=scale,
        diagnostics=diagnostics,
    )


def calibrate(
    result: Chi2Result, *, target_pm_per_V: float, wavelength_nm_value: float, source: str
) -> Chi2Result:
    """Rescale a relative spectrum so one wavelength matches one published value.

    Exactly one real, positive, global factor is fitted. Nothing else is
    adjusted, and the result is labelled a calibrated reproduction so it cannot
    be mistaken for an independent absolute prediction.
    """

    if result.settings.mode != "relative":
        raise Chi2Error("only a relative spectrum may be calibrated.")
    if not source.strip():
        raise Chi2Error("calibration needs a source naming the value being fitted.")
    reference = abs(result.at_wavelength(wavelength_nm_value))
    if not math.isfinite(reference) or reference <= 0:
        raise Chi2Error(
            f"the relative spectrum is zero at {wavelength_nm_value} nm; there is "
            "nothing to calibrate against."
        )
    factor = float(target_pm_per_V) / reference
    calibrated_settings = Chi2Settings(
        mode="calibrated",
        broadening_meV=result.settings.broadening_meV,
        k_parallel_fraction_of_bz=result.settings.k_parallel_fraction_of_bz,
        k_parallel_points=result.settings.k_parallel_points,
        lattice_constant_nm=result.settings.lattice_constant_nm,
        electron_mass_m0=result.settings.electron_mass_m0,
        heavy_hole_inplane_mass_m0=result.settings.heavy_hole_inplane_mass_m0,
        spin_degeneracy=result.settings.spin_degeneracy,
        calibration_target_pm_per_V=float(target_pm_per_V),
        calibration_wavelength_nm=float(wavelength_nm_value),
        calibration_source=source,
    )
    return Chi2Result(
        photon_energy_eV=result.photon_energy_eV,
        chi2=result.chi2 * factor,
        settings=calibrated_settings,
        units=CALIBRATED_UNITS,
        scale_factor=factor,
        diagnostics={
            **dict(result.diagnostics),
            "calibration_factor": factor,
            "calibration_reference_magnitude": reference,
            "calibration_source": source,
            "calibration_warning": (
                "One global scale factor was fitted to a single published value. "
                "Absolute magnitudes elsewhere in this spectrum are a calibrated "
                "reproduction, not an independent prediction."
            ),
        },
    )


def structural_asymmetry(thick_nm: float, thin_nm: float) -> float:
    """The paper's ``s = (d1 - d2) / (d1 + d2)``."""

    total = float(thick_nm) + float(thin_nm)
    if total <= 0:
        raise Chi2Error("well thicknesses must sum to a positive value.")
    return (float(thick_nm) - float(thin_nm)) / total


def well_widths_from_asymmetry(
    asymmetry: float, total_thickness_nm: float
) -> tuple[float, float]:
    """Inverse of :func:`structural_asymmetry` at fixed total thickness.

    ``d_thick = D (1 + s) / 2`` and ``d_thin = D (1 - s) / 2``. At ``s = 1`` the
    thin well vanishes, which is the symmetric single-well limit where the
    paper expects the structural response to return to zero.
    """

    if not 0.0 <= float(asymmetry) <= 1.0:
        raise Chi2Error("asymmetry must lie in [0, 1].")
    if float(total_thickness_nm) <= 0:
        raise Chi2Error("total_thickness_nm must be positive.")
    total = float(total_thickness_nm)
    return (
        total * (1.0 + float(asymmetry)) / 2.0,
        total * (1.0 - float(asymmetry)) / 2.0,
    )


def resonance_wavelengths_nm(
    transition_energies_eV: Sequence[float],
) -> dict[str, list[float]]:
    """Where SHG resonances are expected for given interband transitions.

    The two-photon denominator resonates when ``2 hbar omega = E``, i.e. at a
    fundamental wavelength of ``2 hc / E``; the one-photon denominator at
    ``hc / E``. Reporting both is what lets the paper's "peaks around 760 nm and
    1520 nm" be checked as one physical statement rather than two coincidences.
    """

    energies = [float(value) for value in transition_energies_eV if float(value) > 0]
    return {
        "two_photon_resonance_nm": [2.0 * HC_EV_NM / value for value in energies],
        "one_photon_resonance_nm": [HC_EV_NM / value for value in energies],
    }


def origin_independence_error(
    electron: BandStates,
    heavy_hole: BandStates,
    photon_energies_eV: Sequence[float] | np.ndarray,
    settings: Chi2Settings | None = None,
    *,
    shift_nm: float = 100.0,
) -> float:
    """Relative change in |chi2| when the z origin is translated.

    Eq. 2's diagonal position matrix elements are individually origin
    dependent, and the dependence cancels between its two terms only for an
    orthonormal envelope basis. Measuring the residual is therefore a direct,
    end-to-end check that the states handed in are usable -- it catches a
    too-coarse grid or mismatched quantum regions in a way that inspecting a
    single number cannot.
    """

    settings = settings or Chi2Settings()
    reference = chi2_spectrum(electron, heavy_hole, photon_energies_eV, settings)
    shifted = chi2_spectrum(
        BandStates(
            electron.z_nm + float(shift_nm), electron.energies_eV, electron.envelopes
        ),
        BandStates(
            heavy_hole.z_nm + float(shift_nm),
            heavy_hole.energies_eV,
            heavy_hole.envelopes,
        ),
        photon_energies_eV,
        settings,
    )
    scale = float(np.max(np.abs(reference.chi2)))
    if scale <= 0:
        return 0.0
    return float(np.max(np.abs(shifted.chi2 - reference.chi2)) / scale)


def orthonormalise(band: BandStates) -> BandStates:
    """Gram-Schmidt a band's envelopes.

    Provided for *tests and synthetic fixtures only*. Real solver eigenstates of
    one Hermitian Hamiltonian are already orthogonal; if they are not, that is a
    numerical defect to diagnose, not something to paper over here.
    """

    z = band.z_nm
    columns: list[np.ndarray] = []
    for index in range(band.count):
        vector = band.envelopes[:, index].astype(float).copy()
        for previous in columns:
            vector -= float(np.trapezoid(previous * vector, z)) * previous
        norm = float(np.trapezoid(vector**2, z))
        if norm <= 0:
            raise Chi2Error(
                f"state {index + 1} is linearly dependent on the earlier states."
            )
        columns.append(vector / math.sqrt(norm))
    return BandStates(z, band.energies_eV, np.column_stack(columns), band.label)
