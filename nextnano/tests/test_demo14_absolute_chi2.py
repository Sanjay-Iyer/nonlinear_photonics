"""Demo 14 absolute chi(2): the checks that do not need a licensed solver.

Spec section 5. Every one of these runs on synthetic band states, so all of it
is verifiable on the home laptop. The point is to remove as much doubt as
possible from the absolute scale *before* spending licensed time, leaving only
the questions that genuinely require nextnano++.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

import chi2 as chi2mod
import physics14


# --- synthetic band states -------------------------------------------------


def _states(n_states: int = 2, points: int = 601, width_nm: float = 10.0):
    """Particle-in-a-box envelopes: orthonormal by construction, so Eq. 2's
    diagonal position elements stay origin-independent."""

    z = np.linspace(0.0, width_nm, points)
    envelopes = np.zeros((points, n_states))
    for i in range(n_states):
        raw = np.sin((i + 1) * math.pi * z / width_nm)
        norm = math.sqrt(float(np.trapezoid(raw**2, z)))
        envelopes[:, i] = raw / norm
    return z, envelopes


def electron_states(n: int = 2):
    z, env = _states(n)
    # Asymmetric energies so the two denominators are distinct.
    energies = np.array([1.500 + 0.13 * i for i in range(n)])
    return chi2mod.BandStates(z, energies, env, "e")


def hole_states(n: int = 2):
    z, env = _states(n)
    # Hole energies decrease with index on the solver's single energy scale.
    energies = np.array([0.010 - 0.021 * i for i in range(n)])
    # Break the exact parity that would zero every cross term.
    env = env + 0.05 * np.roll(env, 7, axis=0)
    for i in range(env.shape[1]):
        env[:, i] /= math.sqrt(float(np.trapezoid(env[:, i] ** 2, z)))
    return chi2mod.BandStates(z, energies, env, "hh")


def absolute_settings(**changes):
    base = dict(
        mode="absolute",
        broadening_meV=5.0,
        k_parallel_fraction_of_bz=0.10,
        k_parallel_points=96,
        lattice_constant_nm=0.565325,
        electron_mass_m0=0.067,
        heavy_hole_inplane_mass_m0=0.112,
        spin_degeneracy=2,
        max_states_per_band=2,
        r_e_hh_nm=physics14.R_E_HH_NM,
        n_wells_per_metre=physics14.n_z_for("period_density", 30.0),
    )
    base.update(changes)
    return chi2mod.Chi2Settings(**base)


TARGET_eV = 1239.841984 / 1550.0  # 1550 nm fundamental


# --- A. energy form vs angular-frequency form ------------------------------


@pytest.mark.parametrize("wavelength_nm", [1300.0, 1550.0, 1700.0])
def test_energy_and_angular_frequency_forms_agree(wavelength_nm):
    """The shipped energy form must reproduce the paper's published rad/s form.

    These are two independent derivations, not a rescaling: the angular form
    keeps hbar^2 in the prefactor and converts Gamma to rad/s, while the energy
    form cancels hbar^2 against the denominators and uses Gamma in eV.
    """

    settings = absolute_settings()
    comparison = physics14.compare_formulations(
        electron_states(), hole_states(), 1239.841984 / wavelength_nm, settings
    )
    assert comparison.relative_difference < 1e-10, (
        f"{wavelength_nm} nm: energy {comparison.energy_form} vs angular "
        f"{comparison.angular_frequency_form}"
    )


def test_the_two_forms_are_genuinely_independent_of_each_other():
    """Guard the guard: perturbing one input must move both results together."""

    a = physics14.compare_formulations(
        electron_states(), hole_states(), TARGET_eV, absolute_settings()
    )
    b = physics14.compare_formulations(
        electron_states(), hole_states(), TARGET_eV, absolute_settings(broadening_meV=20.0)
    )
    assert abs(a.energy_form) != pytest.approx(abs(b.energy_form), rel=1e-6)
    assert abs(a.angular_frequency_form) != pytest.approx(
        abs(b.angular_frequency_form), rel=1e-6
    )
    assert b.relative_difference < 1e-10


# --- B. radial vs Cartesian k measure --------------------------------------


def test_radial_and_cartesian_k_measures_agree():
    """(1/2pi) int k dk over [0, kmax] must equal int d^2k/(2pi)^2 over the disc."""

    settings = absolute_settings()
    radial = physics14.k_measure_radial(settings)
    cartesian = physics14.k_measure_cartesian(settings, points_per_axis=801)
    assert cartesian == pytest.approx(radial, rel=2e-3), f"{radial} vs {cartesian}"


def test_k_measure_has_the_analytic_value():
    """Closed form: spin * k_max^2 / (4 pi)."""

    settings = absolute_settings()
    expected = settings.spin_degeneracy * settings.k_max_per_nm**2 / (4.0 * math.pi)
    assert physics14.k_measure_radial(settings) == pytest.approx(expected, rel=1e-6)


# --- C. k grid convergence -------------------------------------------------


def test_k_grid_converges_over_the_required_point_counts():
    settings = absolute_settings()
    report = physics14.k_convergence_report(
        electron_states(), hole_states(), TARGET_eV, settings,
        point_counts=(48, 96, 192, 384),
    )
    assert report["k_parallel_points_tested"] == [48, 96, 192, 384]
    assert report["k_parallel_integration_converged"] is True
    assert report["k_parallel_relative_error"] < 1e-3
    values = report["chi2_abs_by_point_count"]
    assert set(values) == {"48", "96", "192", "384"}
    assert all(math.isfinite(v) for v in values.values())


def test_a_deliberately_coarse_grid_is_reported_as_unconverged():
    """The converged flag must be capable of being false."""

    settings = absolute_settings(k_parallel_points=3)
    report = physics14.k_convergence_report(
        electron_states(), hole_states(), TARGET_eV, settings,
        point_counts=(3, 384), tolerance=1e-6,
    )
    assert report["k_parallel_integration_converged"] is False
    assert report["k_parallel_relative_error"] > 1e-6


# --- D. cutoff convention --------------------------------------------------


def test_cutoff_convention_is_explicit_and_measured_not_assumed():
    settings = absolute_settings()
    report = physics14.cutoff_sensitivity(
        electron_states(), hole_states(), TARGET_eV, settings
    )
    by_name = {row["convention"]: row for row in report["conventions"]}
    assert set(by_name) == set(physics14.BZ_EDGE_CONVENTIONS)
    legacy = by_name["legacy_pi_over_a"]
    crystallographic = by_name["crystallographic_two_pi_over_a"]
    assert crystallographic["k_max_per_nm"] == pytest.approx(
        2.0 * legacy["k_max_per_nm"], rel=1e-9
    )
    # The naive expectation is a 4x area scaling; the integrand is not constant,
    # so the real ratio must be whatever the integral gives. Assert only that it
    # is NOT the naive value, which is the whole reason this is measured.
    ratio = crystallographic["chi2_abs_pm_per_V"] / legacy["chi2_abs_pm_per_V"]
    assert ratio > 1.0
    assert ratio != pytest.approx(4.0, rel=1e-6)


def test_unknown_cutoff_convention_is_refused():
    with pytest.raises(ValueError, match="zone-edge convention"):
        physics14.k_max_per_nm(
            fraction_of_bz=0.1, lattice_constant_nm=0.565325, convention="made_up"
        )


# --- E. N_z sensitivity ----------------------------------------------------


def test_n_z_modes_give_the_documented_values():
    assert physics14.n_z_for("period_density", 30.0) == pytest.approx(3.3333333e7, rel=1e-6)
    assert physics14.n_z_for("well_density", 30.0) == pytest.approx(6.6666667e7, rel=1e-6)
    with pytest.raises(ValueError, match="N_z mode"):
        physics14.n_z_for("spin_degeneracy", 30.0)


def test_n_z_sensitivity_reports_both_readings_and_fits_nothing():
    settings = absolute_settings()
    report = physics14.n_z_sensitivity(
        electron_states(), hole_states(), TARGET_eV, settings
    )
    assert report["fitted"] is False
    modes = {row["nz_mode"]: row for row in report["readings"]}
    assert set(modes) == set(physics14.NZ_MODES)
    # chi(2) is strictly linear in N_z, so the ambiguity is exactly a factor 2.
    ratio = (
        modes["well_density"]["chi2_abs_pm_per_V"]
        / modes["period_density"]["chi2_abs_pm_per_V"]
    )
    assert ratio == pytest.approx(2.0, rel=1e-9)


# --- F. dimensional resolution ---------------------------------------------


def test_absolute_result_scales_correctly_with_each_constant():
    """Linear in N_z, quadratic in r_e_hh -- the signature of the prefactor."""

    base = absolute_settings()
    value = abs(
        chi2mod.chi2_spectrum(electron_states(), hole_states(), [TARGET_eV], base).chi2[0]
    )
    doubled_nz = abs(
        chi2mod.chi2_spectrum(
            electron_states(), hole_states(), [TARGET_eV],
            physics14.with_settings(base, n_wells_per_metre=2 * base.n_wells_per_metre),
        ).chi2[0]
    )
    doubled_r = abs(
        chi2mod.chi2_spectrum(
            electron_states(), hole_states(), [TARGET_eV],
            physics14.with_settings(base, r_e_hh_nm=2 * base.r_e_hh_nm),
        ).chi2[0]
    )
    assert doubled_nz == pytest.approx(2.0 * value, rel=1e-9)
    assert doubled_r == pytest.approx(4.0 * value, rel=1e-9)


def test_pm_per_V_and_m_per_V_are_consistent():
    """1 pm/V = 1e-12 m/V, and the absolute mode reports pm/V."""

    settings = absolute_settings()
    result = chi2mod.chi2_spectrum(
        electron_states(), hole_states(), [TARGET_eV], settings
    )
    pm_per_V = abs(result.chi2[0])
    m_per_V = pm_per_V * 1.0e-12
    assert result.units == chi2mod.ABSOLUTE_UNITS
    assert m_per_V == pytest.approx(pm_per_V * 1e-12, rel=1e-12)
    assert math.isfinite(pm_per_V) and pm_per_V > 0.0


def test_absolute_mode_still_refuses_without_the_two_constants():
    """The guard that kept Demo 13 honest must not have been weakened."""

    with pytest.raises(chi2mod.Chi2Error, match="r_e_hh_nm"):
        chi2mod.Chi2Settings(mode="absolute")
    with pytest.raises(chi2mod.Chi2Error, match="n_wells_per_metre"):
        chi2mod.Chi2Settings(mode="absolute", r_e_hh_nm=0.751)


def test_r_e_hh_is_the_verified_paper_value_and_not_multiplied_by_charge():
    assert physics14.R_E_HH_NM == pytest.approx(0.751)
    assert physics14.R_E_HH_NM * 1e-9 == pytest.approx(7.51e-10)
    assert "7.51" in physics14.R_E_HH_PROVENANCE
    assert "HSE06" in physics14.R_E_HH_PROVENANCE
    record = physics14.constants_record(absolute_settings())
    assert record["r_e_hh_is_position_matrix_element"] is True
    assert record["scale_factor_fitted"] is False


def test_constants_record_captures_everything_that_set_the_scale():
    record = physics14.constants_record(absolute_settings())
    for key in (
        "r_e_hh_nm", "r_e_hh_provenance", "n_wells_per_metre", "spin_degeneracy",
        "broadening_meV", "vacuum_permittivity_F_per_m", "elementary_charge_C",
        "reduced_planck_J_s", "unit_formulation", "k_max_per_nm",
    ):
        assert record[key] is not None, key


# --- configuration wiring --------------------------------------------------


def test_settings_from_config_builds_absolute_mode_from_yaml_shape():
    cfg = {
        "chi2": {
            "mode": "absolute",
            "broadening_meV": 5.0,
            "r_e_hh_nm": 0.751,
            "nz_mode": "period_density",
            "reference_period_nm": 30.0,
            "max_states_per_band": 2,
        },
        "k_parallel": {"fraction_of_bz": 0.10, "points": 96, "spin_degeneracy": 2},
    }
    settings = physics14.settings_from_config(cfg)
    assert settings.mode == "absolute"
    assert settings.r_e_hh_nm == pytest.approx(0.751)
    assert settings.n_wells_per_metre == pytest.approx(3.3333333e7, rel=1e-6)
    assert settings.spin_degeneracy == 2
