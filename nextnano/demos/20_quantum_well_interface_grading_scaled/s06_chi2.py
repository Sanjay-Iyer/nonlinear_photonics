r"""Stage 06 - the second-order susceptibility, and the k-space normalization.

This module is self-contained physics. It has no solver dependency, no plotting
dependency and no file I/O, so the mathematics below can be read and tested on
its own.

=============================================================================
THE MODEL (unchanged from Demo 19)
=============================================================================

Interband SHG in a coupled quantum well, evaluated for chi2_xzx. In the
published angular-frequency notation:

    chi2_xzx(w1, w2) = Nz e^3 r_ehh^2 / (6 eps0 hbar^2)
                       * sum_kpar sum_{m,n,l} [ A - B ]

    A = O_nm z^e_nl O_lm / [(w^{e,n}_{hh,m} - w1 - w2 + i G)
                            (w^{e,l}_{hh,m} - w1 + i G)]
    B = O_nm z^hh_ml O_nl / [(w^{e,n}_{hh,m} - w1 - w2 + i G)
                            (w^{e,n}_{hh,l} - w1 + i G)]

This code evaluates the algebraically equivalent ENERGY form, which is what
Demo 19 evaluates:

    chi2_xzx(E) = Nz e^3 r_ehh^2 / (6 eps0)
                  * <k-measure> sum_{m,n,l} [ A' - B' ]

    A' = O_nm z^e_nl O_lm / {[dE_nm(k) - 2E + i g][dE_lm(k) - E + i g]}
    B' = O_nm z^hh_ml O_nl / {[dE_nm(k) - 2E + i g][dE_nl(k) - E + i g]}

with g = broadening in eV. The explicit hbar^-2 disappears because both
denominators are written in energy rather than angular frequency; the SI
conversions are then applied explicitly in :func:`absolute_prefactor`.

Transition energies disperse parabolically in the plane and the envelope matrix
elements do not:

    dE_nm(k) = (E_e,n - E_hh,m) + hbar^2 k^2 / (2 mu),
    1/mu = 1/m_e + 1/m_hh_parallel

SHG sets w1 = w2 = w, so the two-photon denominator resonates at 2E = dE and
the one-photon denominator at E = dE.

=============================================================================
THE k-SPACE NORMALIZATION - READ THIS BEFORE CHANGING ANYTHING
=============================================================================

Discrete-to-continuum conversion for a 2D system of area A:

    sum_k f(k)  ->  A / (2*pi)^2 * integral d^2k f(k)

so the per-unit-area sum that chi2 needs is

    (1/A) sum_k f(k)  ->  1/(2*pi)^2 * integral d^2k f(k).

For an isotropic integrand the angular integral is free:

    integral d^2k f(|k|) = 2*pi * integral_0^kmax k f(k) dk

Substituting collapses one factor of 2*pi:

    (1/A) sum_k f  ->  (2*pi)/(2*pi)^2 * integral k f dk
                    =  1/(2*pi) * integral_0^kmax k f(k) dk

>>> DEMO 19 IMPLEMENTS EXACTLY THAT LAST LINE. <<<
    nextnano/demos/_shared/chi2.py::_k_grid builds
        radial  = k / (2*pi)
        weights = trapezoidal dk
        total   = radial * weights * spin_degeneracy
    i.e. w_i = g_s * k_i /(2*pi) * dk_i.

So the factor 1/(2*pi)^2 IS ALREADY PRESENT in Demo 19, in its reduced
isotropic form 1/(2*pi) with the compensating 2*pi already cancelled by the
angular integral. It is not missing.

Independent confirmations, both machine-checked in tests/test_demo20.py:

  1. Analytic disc constant. For f = 1 the weights must sum to
         g_s * kmax^2 / (4*pi)
     because (g_s/(2*pi)^2) * (pi kmax^2) = g_s kmax^2/(4*pi). They do, to
     ~1e-16 relative.
  2. Cartesian cross-check. physics14.k_measure_cartesian integrates
     dkx dky/(2*pi)^2 over the disc without using isotropy at all and lands on
     the same number.

WHAT THE TOGGLE ACTUALLY DOES
-----------------------------
Multiplying by (2*pi)^2 = 39.47841760435743 therefore does NOT restore a
missing normalization. It CANCELS the existing denominator:

    convention "d2k_over_2pi_squared"  (Demo 19, default)
        w_i = g_s * k_i * dk_i / (2*pi)          <-> (1/A) sum -> int d2k/(2pi)^2
    convention "bare_d2k"              (Demo 20 experiment)
        w_i = g_s * 2*pi * k_i * dk_i            <->        sum -> g_s * int d2k

Both leave chi2 in pm/V, because the k measure has units nm^-2 either way; the
switch is a factor of exactly (2*pi)^2 in magnitude, not a change of units.
Until the source paper's own k-space measure is confirmed, "bare_d2k" is an
alternative convention under test, not a correction. Nothing in this module
labels it as physically correct.

The factor is applied in the k measure - the one place the normalization
mathematically belongs - rather than as a post-hoc multiplier on chi2. Because
it is k-independent the two placements are numerically identical, which
:func:`scaling_is_exact_constant` verifies rather than assumes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

import numpy as np

# --- physical constants (CODATA 2018), SI unless the name says otherwise ----
ELEMENTARY_CHARGE_C = 1.602176634e-19
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
REDUCED_PLANCK_J_S = 1.054571817e-34
ELECTRON_MASS_KG = 9.1093837015e-31
#: hc in eV*nm, for the photon-energy <-> wavelength conversion.
HC_EV_NM = 1239.841984

KSpaceConvention = Literal["d2k_over_2pi_squared", "bare_d2k"]

#: The Demo 19 convention. ``(1/A) sum_k -> int d^2k/(2*pi)^2``.
CONVENTION_DEMO19: KSpaceConvention = "d2k_over_2pi_squared"
#: The Demo 20 experiment. ``sum_k -> g_s * int d^2k``; a factor (2*pi)^2 larger.
CONVENTION_SCALED: KSpaceConvention = "bare_d2k"

CONVENTION_DESCRIPTIONS: Mapping[str, str] = {
    CONVENTION_DEMO19: "(1/A) sum_k -> integral d^2k/(2*pi)^2 "
                       "= (1/(2*pi)) integral k dk  [Demo 19 original]",
    CONVENTION_SCALED: "sum_k -> g_s * integral d^2k "
                       "= 2*pi * integral k dk  [Demo 20 experiment, "
                       "(2*pi)^2 larger]",
}

BZ_EDGE_CONVENTIONS: Mapping[str, float] = {
    "legacy_pi_over_a": math.pi,
    "crystallographic_two_pi_over_a": 2.0 * math.pi,
}

NZ_MODES = ("period_density", "well_density")


class Chi2_20Error(ValueError):
    """The susceptibility is not defensible as configured."""


def two_pi_squared() -> float:
    """``(2*pi)^2``, computed. The YAML value is checked against this."""

    return (2.0 * math.pi) ** 2


def photon_energy_eV(wavelength_nm: float | np.ndarray) -> np.ndarray:
    values = np.asarray(wavelength_nm, dtype=float)
    if np.any(values <= 0):
        raise Chi2_20Error("wavelength must be positive.")
    return HC_EV_NM / values


def wavelength_nm(energy_eV: float | np.ndarray) -> np.ndarray:
    values = np.asarray(energy_eV, dtype=float)
    if np.any(values <= 0):
        raise Chi2_20Error("photon energy must be positive.")
    return HC_EV_NM / values


# --- settings ---------------------------------------------------------------


@dataclass(frozen=True)
class Chi2Settings:
    """Every convention the susceptibility depends on, named and explicit."""

    broadening_meV: float = 5.0
    r_e_hh_nm: float = 0.751
    n_wells_per_metre: float = 1.0 / 30.0e-9
    nz_mode: str = "period_density"
    reference_period_nm: float = 30.0
    max_states_per_band: int = 2
    # --- in-plane integration ---
    k_parallel_fraction_of_bz: float = 0.10
    lattice_constant_nm: float = 0.565325
    bz_edge_convention: str = "legacy_pi_over_a"
    k_parallel_points: int = 96
    electron_mass_m0: float = 0.067
    heavy_hole_inplane_mass_m0: float = 0.112
    spin_degeneracy: int = 2
    #: Which discrete-to-continuum reading of ``sum_k`` to use. See the module
    #: docstring: this is the Demo 20 experiment.
    kspace_convention: KSpaceConvention = CONVENTION_DEMO19

    def __post_init__(self) -> None:
        for name in ("broadening_meV", "r_e_hh_nm", "n_wells_per_metre",
                     "k_parallel_fraction_of_bz", "lattice_constant_nm",
                     "electron_mass_m0", "heavy_hole_inplane_mass_m0"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0:
                raise Chi2_20Error(f"{name} must be finite and > 0.")
        if int(self.k_parallel_points) < 2:
            raise Chi2_20Error("k_parallel_points must be at least 2.")
        if int(self.spin_degeneracy) not in (1, 2):
            raise Chi2_20Error("spin_degeneracy must be 1 or 2.")
        if int(self.max_states_per_band) < 2:
            raise Chi2_20Error(
                "max_states_per_band must be at least 2: the second term of the "
                "triple sum needs a second state in each band."
            )
        if self.bz_edge_convention not in BZ_EDGE_CONVENTIONS:
            raise Chi2_20Error(
                f"bz_edge_convention must be one of {tuple(BZ_EDGE_CONVENTIONS)}."
            )
        if self.kspace_convention not in (CONVENTION_DEMO19, CONVENTION_SCALED):
            raise Chi2_20Error(
                f"kspace_convention must be {CONVENTION_DEMO19!r} or "
                f"{CONVENTION_SCALED!r}, got {self.kspace_convention!r}."
            )

    @property
    def k_max_per_nm(self) -> float:
        """Upper in-plane limit in nm^-1: fraction * zone edge."""

        edge = BZ_EDGE_CONVENTIONS[self.bz_edge_convention]
        return float(self.k_parallel_fraction_of_bz) * edge / float(
            self.lattice_constant_nm
        )

    @property
    def broadening_eV(self) -> float:
        return float(self.broadening_meV) * 1.0e-3

    def reduced_mass_kg(self) -> float:
        inverse = (1.0 / float(self.electron_mass_m0)
                   + 1.0 / float(self.heavy_hole_inplane_mass_m0))
        return ELECTRON_MASS_KG / inverse

    def with_convention(self, convention: KSpaceConvention) -> "Chi2Settings":
        return replace_settings(self, kspace_convention=convention)

    def as_record(self) -> dict[str, Any]:
        return {
            "broadening_meV": self.broadening_meV,
            "r_e_hh_nm": self.r_e_hh_nm,
            "n_wells_per_metre": self.n_wells_per_metre,
            "nz_mode": self.nz_mode,
            "reference_period_nm": self.reference_period_nm,
            "max_states_per_band": int(self.max_states_per_band),
            "k_parallel_fraction_of_bz": self.k_parallel_fraction_of_bz,
            "lattice_constant_nm": self.lattice_constant_nm,
            "bz_edge_convention": self.bz_edge_convention,
            "k_max_per_nm": self.k_max_per_nm,
            "k_parallel_points": int(self.k_parallel_points),
            "electron_mass_m0": self.electron_mass_m0,
            "heavy_hole_inplane_mass_m0": self.heavy_hole_inplane_mass_m0,
            "reduced_mass_m0": self.reduced_mass_kg() / ELECTRON_MASS_KG,
            "spin_degeneracy": int(self.spin_degeneracy),
            "kspace_convention": self.kspace_convention,
            "kspace_convention_description":
                CONVENTION_DESCRIPTIONS[self.kspace_convention],
        }


def replace_settings(settings: Chi2Settings, **changes: Any) -> Chi2Settings:
    """A modified copy; ``Chi2Settings`` is frozen on purpose."""

    fields = {
        "broadening_meV": settings.broadening_meV,
        "r_e_hh_nm": settings.r_e_hh_nm,
        "n_wells_per_metre": settings.n_wells_per_metre,
        "nz_mode": settings.nz_mode,
        "reference_period_nm": settings.reference_period_nm,
        "max_states_per_band": settings.max_states_per_band,
        "k_parallel_fraction_of_bz": settings.k_parallel_fraction_of_bz,
        "lattice_constant_nm": settings.lattice_constant_nm,
        "bz_edge_convention": settings.bz_edge_convention,
        "k_parallel_points": settings.k_parallel_points,
        "electron_mass_m0": settings.electron_mass_m0,
        "heavy_hole_inplane_mass_m0": settings.heavy_hole_inplane_mass_m0,
        "spin_degeneracy": settings.spin_degeneracy,
        "kspace_convention": settings.kspace_convention,
    }
    fields.update(changes)
    return Chi2Settings(**fields)


def n_z_for(mode: str, period_nm: float, wells_per_period: int = 2) -> float:
    """``N_z`` in m^-1 for a named counting convention.

    ``period_density`` counts one coupled-well *pair* per period;
    ``well_density`` counts its individual wells. The source text says only
    "quantum wells per unit length", so both readings exist and are recorded.
    """

    if mode not in NZ_MODES:
        raise Chi2_20Error(f"nz_mode must be one of {NZ_MODES}, got {mode!r}.")
    if not math.isfinite(period_nm) or period_nm <= 0:
        raise Chi2_20Error("reference_period_nm must be finite and > 0.")
    per_period = 1.0 if mode == "period_density" else float(wells_per_period)
    return per_period / (float(period_nm) * 1.0e-9)


def settings_from_config(
    cfg: Mapping[str, Any], *, convention: KSpaceConvention | None = None
) -> Chi2Settings:
    """Build :class:`Chi2Settings` from ``demo20_config.yaml``.

    When ``convention`` is None the convention is taken from
    ``chi2.apply_kspace_2pi_squared_scaling``.
    """

    chi2_cfg = cfg["chi2"]
    kpar = cfg["k_parallel"]
    mode = str(chi2_cfg["nz_mode"])
    period = float(chi2_cfg["reference_period_nm"])
    n_z = chi2_cfg.get("n_wells_per_metre")
    if n_z is None:
        n_z = n_z_for(mode, period, int(chi2_cfg.get("wells_per_period", 2)))
    if convention is None:
        convention = (CONVENTION_SCALED
                      if bool(chi2_cfg["apply_kspace_2pi_squared_scaling"])
                      else CONVENTION_DEMO19)
    return Chi2Settings(
        broadening_meV=float(chi2_cfg["broadening_meV"]),
        r_e_hh_nm=float(chi2_cfg["r_e_hh_nm"]),
        n_wells_per_metre=float(n_z),
        nz_mode=mode,
        reference_period_nm=period,
        max_states_per_band=int(cfg["states"]["max_states_per_band"]),
        k_parallel_fraction_of_bz=float(kpar["fraction_of_bz"]),
        lattice_constant_nm=float(kpar["lattice_constant_nm"]),
        bz_edge_convention=str(kpar["bz_edge_convention"]),
        k_parallel_points=int(kpar["points"]),
        electron_mass_m0=float(kpar["electron_mass_m0"]),
        heavy_hole_inplane_mass_m0=float(kpar["heavy_hole_inplane_mass_m0"]),
        spin_degeneracy=int(kpar["spin_degeneracy"]),
        kspace_convention=convention,
    )


# --- the k-space measure ----------------------------------------------------


def k_grid(settings: Chi2Settings) -> tuple[np.ndarray, np.ndarray]:
    r"""The in-plane radial grid and its measure weights, both in nm units.

    A plain ``np.dot(weights, integrand)`` performs the whole in-plane sum, so
    every normalization decision is visible in this one function.

    2D continuum convention (see the module docstring for the derivation):

        sum_k f(k)         ->  A/(2*pi)^2 * integral d^2k f(k)
        (1/A) sum_k f(k)   ->  1/(2*pi)^2 * integral d^2k f(k)

    Isotropic integrand, so the angular integral is exact and free:

        integral d^2k f(|k|) = 2*pi * integral_0^kmax k f(k) dk

    Hence the two conventions Demo 20 compares:

        d2k_over_2pi_squared   w_i = g_s * (k_i / (2*pi)) * dk_i
        bare_d2k               w_i = g_s * (2*pi * k_i)   * dk_i

    The ratio bare_d2k / d2k_over_2pi_squared is (2*pi)*(2*pi) = (2*pi)^2,
    exactly and independently of k, which is why the experiment is a pure
    magnitude scaling. dk_i are trapezoidal weights on a uniform grid including
    both endpoints.
    """

    k_max = settings.k_max_per_nm
    points = int(settings.k_parallel_points)
    k = np.linspace(0.0, k_max, points)

    # Trapezoidal dk on a uniform grid: full step inside, half step at the ends.
    step = k[1] - k[0]
    dk = np.full_like(k, step)
    dk[0] = dk[-1] = 0.5 * step

    if settings.kspace_convention == CONVENTION_DEMO19:
        # 1/(2*pi)^2 * 2*pi = 1/(2*pi). This is Demo 19, unchanged.
        radial_measure = k / (2.0 * math.pi)
    else:
        # Bare integral d^2k: keep the 2*pi from the angular integral and drop
        # the 1/(2*pi)^2 density-of-states factor. (2*pi)^2 times the above.
        radial_measure = 2.0 * math.pi * k

    return k, radial_measure * dk * float(settings.spin_degeneracy)


def k_measure_total(settings: Chi2Settings) -> float:
    """``sum of weights`` in nm^-2, i.e. the measure of a constant integrand."""

    return float(np.sum(k_grid(settings)[1]))


def analytic_disc_measure(settings: Chi2Settings) -> float:
    """The same measure in closed form, as an independent check.

    ``d2k_over_2pi_squared``:  (g_s/(2*pi)^2) * pi kmax^2 = g_s kmax^2/(4*pi)
    ``bare_d2k``:              g_s * pi kmax^2
    """

    k_max = settings.k_max_per_nm
    g_s = float(settings.spin_degeneracy)
    if settings.kspace_convention == CONVENTION_DEMO19:
        return g_s * k_max ** 2 / (4.0 * math.pi)
    return g_s * math.pi * k_max ** 2


def scaling_is_exact_constant(settings: Chi2Settings) -> dict[str, Any]:
    """Verify the two conventions differ by exactly ``(2*pi)^2``, pointwise.

    Checked on the weights themselves rather than on chi2, so it holds for any
    integrand: a k-dependent ratio would mean the factor had been placed
    somewhere it does not belong.
    """

    _, low = k_grid(settings.with_convention(CONVENTION_DEMO19))
    _, high = k_grid(settings.with_convention(CONVENTION_SCALED))
    nonzero = low != 0.0
    ratios = high[nonzero] / low[nonzero]
    expected = two_pi_squared()
    return {
        "expected_factor": expected,
        "pointwise_ratio_min": float(np.min(ratios)),
        "pointwise_ratio_max": float(np.max(ratios)),
        "max_absolute_deviation": float(np.max(np.abs(ratios - expected))),
        "total_measure_ratio": (k_measure_total(settings.with_convention(CONVENTION_SCALED))
                                / k_measure_total(settings.with_convention(CONVENTION_DEMO19))),
        "is_exact_constant": bool(
            np.max(np.abs(ratios - expected)) <= 1.0e-9 * expected
        ),
    }


# --- state data -------------------------------------------------------------


@dataclass(frozen=True)
class CaseStates:
    """The quantum-mechanical inputs to the triple sum, for one case.

    All of these are solver-derived. ``s05_extract`` builds this either by
    parsing a raw licensed run or by reading them back from a results table;
    :mod:`s06_chi2` never invents any of them.

    energies in eV on nextnano's single electron-energy scale, so an interband
    transition is simply ``E_electron - E_hole``. Position matrices in nm.
    """

    case_id: str
    electron_energies_eV: np.ndarray          # (n_e,)
    hole_energies_eV: np.ndarray              # (n_h,)
    overlap_electron_hole: np.ndarray         # (n_e, n_h)  O_nm
    position_matrix_electron_nm: np.ndarray   # (n_e, n_e)  z^e_nl
    position_matrix_hole_nm: np.ndarray       # (n_h, n_h)  z^hh_ml
    provenance: str = ""

    def __post_init__(self) -> None:
        n_e = np.asarray(self.electron_energies_eV).size
        n_h = np.asarray(self.hole_energies_eV).size
        shapes = {
            "overlap_electron_hole": (np.shape(self.overlap_electron_hole), (n_e, n_h)),
            "position_matrix_electron_nm": (
                np.shape(self.position_matrix_electron_nm), (n_e, n_e)),
            "position_matrix_hole_nm": (
                np.shape(self.position_matrix_hole_nm), (n_h, n_h)),
        }
        for name, (actual, expected) in shapes.items():
            if tuple(actual) != expected:
                raise Chi2_20Error(
                    f"case {self.case_id}: {name} has shape {tuple(actual)}, "
                    f"expected {expected}."
                )
        if not np.all(np.isfinite(self.electron_energies_eV)):
            raise Chi2_20Error(f"case {self.case_id}: non-finite electron energy.")
        if not np.all(np.isfinite(self.hole_energies_eV)):
            raise Chi2_20Error(f"case {self.case_id}: non-finite hole energy.")

    @property
    def n_electron(self) -> int:
        return int(np.asarray(self.electron_energies_eV).size)

    @property
    def n_hole(self) -> int:
        return int(np.asarray(self.hole_energies_eV).size)

    def truncated(self, max_states: int) -> "CaseStates":
        """The first ``max_states`` states of each band, as the sums require."""

        n = int(max_states)
        if self.n_electron < n or self.n_hole < n:
            raise Chi2_20Error(
                f"case {self.case_id}: the triple sum uses the first {n} bound "
                f"states of each band; only {self.n_electron} electron and "
                f"{self.n_hole} hole states are available."
            )
        return CaseStates(
            case_id=self.case_id,
            electron_energies_eV=np.asarray(self.electron_energies_eV)[:n],
            hole_energies_eV=np.asarray(self.hole_energies_eV)[:n],
            overlap_electron_hole=np.asarray(self.overlap_electron_hole)[:n, :n],
            position_matrix_electron_nm=np.asarray(self.position_matrix_electron_nm)[:n, :n],
            position_matrix_hole_nm=np.asarray(self.position_matrix_hole_nm)[:n, :n],
            provenance=self.provenance,
        )


# --- prefactor and spectrum -------------------------------------------------


def absolute_prefactor(settings: Chi2Settings) -> float:
    """The pm/V prefactor multiplying the k-weighted triple sum.

    chi2 = Nz e^3 r^2 / (6 eps0) * sum, with every quantity in SI.

    Unit bookkeeping for the sum as actually evaluated below:
        position matrix elements   nm       -> 1e-9 m
        energy denominators        eV^2     -> (e_C)^2 J^2
        k measure weights          nm^-2    -> 1e18 m^-2
    Then m/V -> pm/V is a further 1e12.
    """

    unit_conversion = 1.0e-9 * 1.0e18 / (ELEMENTARY_CHARGE_C ** 2)
    r_m = float(settings.r_e_hh_nm) * 1.0e-9
    scale = (
        float(settings.n_wells_per_metre)
        * ELEMENTARY_CHARGE_C ** 3
        * r_m ** 2
        / (6.0 * VACUUM_PERMITTIVITY_F_PER_M)
    ) * unit_conversion
    return scale * 1.0e12


def transition_energies_eV(
    states: CaseStates, k_per_nm: np.ndarray, settings: Chi2Settings
) -> np.ndarray:
    """``dE_nm(k)`` as ``(n_e, n_h, n_k)`` in eV.

    Electrons disperse upward and holes downward on nextnano's single
    electron-energy scale, so the transition energy rises with in-plane k by
    ``hbar^2 k^2 / (2 mu)`` with the reduced in-plane mass.
    """

    k_per_m = np.asarray(k_per_nm, dtype=float) * 1.0e9
    kinetic_J = (REDUCED_PLANCK_J_S ** 2) * k_per_m ** 2 / (
        2.0 * settings.reduced_mass_kg()
    )
    kinetic_eV = kinetic_J / ELEMENTARY_CHARGE_C
    zero_k = (np.asarray(states.electron_energies_eV)[:, None]
              - np.asarray(states.hole_energies_eV)[None, :])
    return zero_k[:, :, None] + kinetic_eV[None, None, :]


@dataclass(frozen=True)
class Chi2Spectrum:
    """One spectrum, its settings, and the intermediates that produced it."""

    case_id: str
    wavelength_nm: np.ndarray
    photon_energy_eV: np.ndarray
    chi2: np.ndarray                 # complex, pm/V
    settings: Chi2Settings
    prefactor_pm_per_V: float
    diagnostics: Mapping[str, Any]

    @property
    def magnitude(self) -> np.ndarray:
        return np.abs(self.chi2)

    def at_wavelength(self, target_nm: float) -> float:
        """``|chi2|`` interpolated at one fundamental wavelength, in pm/V.

        Interpolated on the wavelength grid, matching how Demo 19 reads its own
        ``chi2_focused.csv``.
        """

        order = np.argsort(self.wavelength_nm)
        grid = self.wavelength_nm[order]
        if not grid[0] <= float(target_nm) <= grid[-1]:
            raise Chi2_20Error(
                f"{target_nm} nm is outside the computed range "
                f"{grid[0]:.1f}-{grid[-1]:.1f} nm."
            )
        return float(np.interp(float(target_nm), grid, self.magnitude[order]))

    def peak(self) -> dict[str, float]:
        index = int(np.argmax(self.magnitude))
        return {
            "wavelength_nm": float(self.wavelength_nm[index]),
            "magnitude_pm_per_V": float(self.magnitude[index]),
            "photon_energy_eV": float(self.photon_energy_eV[index]),
        }

    def normalized_magnitude(self) -> np.ndarray:
        """``|chi2|`` divided by its own peak: the convention-free lineshape."""

        peak = float(np.max(self.magnitude))
        return self.magnitude / (peak if peak else 1.0)


def wavelength_grid(cfg: Mapping[str, Any], *, window: str = "focused") -> np.ndarray:
    key = "focused_wavelength_nm" if window == "focused" else "broad_wavelength_nm"
    count_key = ("focused_wavelength_points" if window == "focused"
                 else "broad_wavelength_points")
    start, end = (float(v) for v in cfg["chi2"][key])
    return np.linspace(start, end, int(cfg["chi2"][count_key]))


def chi2_spectrum(
    states: CaseStates,
    wavelengths_nm: Sequence[float] | np.ndarray,
    settings: Chi2Settings,
) -> Chi2Spectrum:
    """Evaluate the SHG susceptibility over a wavelength grid, in pm/V.

    The triple sum is written out term by term rather than vectorized so the
    two contributions stay visibly separate: the first (conduction) term uses
    the electron position matrix and the second (valence) term uses the hole
    position matrix, and they enter with opposite signs. That near-cancellation
    is a real feature of this model, so it must not be hidden behind a einsum.
    """

    states = states.truncated(int(settings.max_states_per_band))
    n_e, n_h = states.n_electron, states.n_hole
    overlap = np.asarray(states.overlap_electron_hole, dtype=float)
    z_e = np.asarray(states.position_matrix_electron_nm, dtype=float)
    z_h = np.asarray(states.position_matrix_hole_nm, dtype=float)

    lam = np.atleast_1d(np.asarray(wavelengths_nm, dtype=float))
    energies = photon_energy_eV(lam)
    k, weights = k_grid(settings)
    transitions = transition_energies_eV(states, k, settings)
    gamma = settings.broadening_eV

    conduction_terms = 0
    valence_terms = 0
    total = np.zeros(lam.size, dtype=complex)
    for index, hw in enumerate(energies):
        # Two-photon denominator, shared by both terms: dE_nm(k) - 2 hw + i g.
        two_photon = transitions - 2.0 * float(hw) + 1j * gamma      # (n_e, n_h, n_k)
        one_photon = transitions - 1.0 * float(hw) + 1j * gamma      # (n_e, n_h, n_k)
        accumulated = np.zeros(k.size, dtype=complex)
        for m in range(n_h):              # heavy-hole state of the pair
            for n in range(n_e):          # electron state
                for l in range(n_e):      # intra-conduction partner
                    numerator = overlap[n, m] * z_e[n, l] * overlap[l, m]
                    if numerator == 0.0:
                        continue
                    accumulated += numerator / (two_photon[n, m] * one_photon[l, m])
                    conduction_terms += index == 0
                for l in range(n_h):      # intra-valence partner
                    numerator = overlap[n, m] * z_h[m, l] * overlap[n, l]
                    if numerator == 0.0:
                        continue
                    accumulated -= numerator / (two_photon[n, m] * one_photon[n, l])
                    valence_terms += index == 0
        # The whole in-plane sum is this one dot product.
        total[index] = np.dot(weights, accumulated)

    prefactor = absolute_prefactor(settings)
    diagnostics = {
        "provenance": states.provenance,
        "electron_energies_eV": np.asarray(states.electron_energies_eV).tolist(),
        "hole_energies_eV": np.asarray(states.hole_energies_eV).tolist(),
        "transition_energies_zero_k_eV": (
            np.asarray(states.electron_energies_eV)[:, None]
            - np.asarray(states.hole_energies_eV)[None, :]
        ).tolist(),
        "overlap_electron_hole": overlap.tolist(),
        "position_matrix_electron_nm": z_e.tolist(),
        "position_matrix_hole_nm": z_h.tolist(),
        "electron_states_used": n_e,
        "hole_states_used": n_h,
        "triple_sum_terms_conduction_nonzero": int(conduction_terms),
        "triple_sum_terms_valence_nonzero": int(valence_terms),
        "k_parallel_points": int(k.size),
        "k_max_per_nm": settings.k_max_per_nm,
        "k_measure_total_per_nm2": float(np.sum(weights)),
        "k_measure_analytic_per_nm2": analytic_disc_measure(settings),
        "kspace_convention": settings.kspace_convention,
        "prefactor_pm_per_V_per_summand": prefactor,
    }
    return Chi2Spectrum(
        case_id=states.case_id,
        wavelength_nm=lam,
        photon_energy_eV=energies,
        chi2=total * prefactor,
        settings=settings,
        prefactor_pm_per_V=prefactor,
        diagnostics=diagnostics,
    )


@dataclass(frozen=True)
class ConventionPair:
    """The same case under both k-space conventions, plus which one is reported.

    Both are always computed and both are always retained; the configuration
    only decides which one carries the ``reported`` label.
    """

    case_id: str
    raw: Chi2Spectrum          # Demo 19 convention
    scaled: Chi2Spectrum       # (2*pi)^2 experiment
    scaling_enabled: bool

    @property
    def reported(self) -> Chi2Spectrum:
        return self.scaled if self.scaling_enabled else self.raw

    @property
    def scaling_factor(self) -> float:
        return two_pi_squared()

    def magnitude_ratio(self) -> np.ndarray:
        """``|chi2_scaled| / |chi2_raw|`` at every wavelength. Must be (2*pi)^2."""

        denominator = self.raw.magnitude
        safe = np.where(denominator == 0.0, np.nan, denominator)
        return self.scaled.magnitude / safe


def chi2_both_conventions(
    states: CaseStates,
    wavelengths_nm: Sequence[float] | np.ndarray,
    settings: Chi2Settings,
    *,
    scaling_enabled: bool,
) -> ConventionPair:
    """Evaluate both conventions for one case. Neither value is discarded."""

    raw = chi2_spectrum(states, wavelengths_nm,
                        settings.with_convention(CONVENTION_DEMO19))
    scaled = chi2_spectrum(states, wavelengths_nm,
                           settings.with_convention(CONVENTION_SCALED))
    return ConventionPair(
        case_id=states.case_id, raw=raw, scaled=scaled,
        scaling_enabled=bool(scaling_enabled),
    )


def k_convergence_report(
    states: CaseStates, wavelength_nm_value: float, settings: Chi2Settings,
    point_counts: Sequence[int] = (48, 96, 192, 384), tolerance: float = 1.0e-3,
) -> dict[str, Any]:
    """Susceptibility versus in-plane grid density, judged against the finest.

    Comparing against the finest grid rather than the neighbouring one stops a
    slowly drifting integral from passing by taking small steps.
    """

    values: dict[int, complex] = {}
    for count in point_counts:
        probe = replace_settings(settings, k_parallel_points=int(count))
        values[int(count)] = complex(
            chi2_spectrum(states, [float(wavelength_nm_value)], probe).chi2[0]
        )
    finest = values[max(values)]
    production = values.get(int(settings.k_parallel_points), finest)
    denominator = abs(finest) or 1.0
    relative = abs(production - finest) / denominator
    return {
        "case_id": states.case_id,
        "kspace_convention": settings.kspace_convention,
        "k_parallel_points_production": int(settings.k_parallel_points),
        "k_parallel_points_tested": [int(c) for c in point_counts],
        "chi2_abs_by_point_count": {str(c): abs(v) for c, v in values.items()},
        "k_parallel_relative_error": float(relative),
        "k_parallel_integration_converged": bool(relative <= float(tolerance)),
        "k_parallel_tolerance": float(tolerance),
        "k_measure_total_per_nm2": k_measure_total(settings),
    }
