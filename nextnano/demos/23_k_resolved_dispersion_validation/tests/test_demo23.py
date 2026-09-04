from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

import numpy as np
import pytest


DEMO = Path(__file__).resolve().parents[1]
if str(DEMO) not in sys.path:
    sys.path.insert(0, str(DEMO))

import config23
import deck23
import dispersion_models
import k_integration
import physics23
import run_demo23
import state_tracking
import transition_energies


@pytest.fixture
def cfg():
    return config23.load_config()


@pytest.fixture
def frozen(cfg):
    return physics23.load_frozen_k0_inputs(cfg)


def test_01_23a_reproduces_demo20_21_complex_spectrum(cfg, frozen):
    settings = physics23.settings_from_config(cfg)
    k, _ = physics23.validated.k_grid(settings)
    model = dispersion_models.BaselineSharedParabola(
        "23A", frozen.states.electron_energies_eV, frozen.states.hole_energies_eV,
        settings.reduced_mass_kg(),
    )
    wavelength = np.asarray([1400.0, 1550.0, 1800.0])
    result = physics23.evaluate_mode(
        "23A", model, k, wavelength, frozen, settings, k0_tolerance_eV=1e-12
    )
    assert physics23.baseline_regression_error(result, frozen, wavelength, settings) < 1e-9


def test_02_transition_k0_matches_demo20_known_values(cfg, frozen):
    settings = physics23.settings_from_config(cfg)
    model = dispersion_models.BaselineSharedParabola(
        "23A", frozen.states.electron_energies_eV, frozen.states.hole_energies_eV,
        settings.reduced_mass_kg(),
    )
    transitions = transition_energies.build_transition_energies(
        np.asarray([0.0, 0.1]), model.evaluate(np.asarray([0.0, 0.1]))
    )
    assert transition_energies.assert_k0_matches(
        transitions, frozen.states.electron_energies_eV, frozen.states.hole_energies_eV,
        tolerance_eV=1e-12,
    ) == pytest.approx(0.0)


def test_03_all_four_transitions_use_same_k_index():
    k = np.asarray([0.0, 1.0, 2.0])
    bands = {
        "e1": np.asarray([10.0, 20.0, 30.0]),
        "e2": np.asarray([40.0, 50.0, 60.0]),
        "hh1": np.asarray([1.0, 2.0, 3.0]),
        "hh2": np.asarray([4.0, 5.0, 6.0]),
    }
    values = transition_energies.build_transition_energies(k, bands).as_dict()
    np.testing.assert_array_equal(values["DeltaE_11"], [9.0, 18.0, 27.0])
    np.testing.assert_array_equal(values["DeltaE_12"], [6.0, 15.0, 24.0])
    np.testing.assert_array_equal(values["DeltaE_21"], [39.0, 48.0, 57.0])
    np.testing.assert_array_equal(values["DeltaE_22"], [36.0, 45.0, 54.0])


def test_04_parabolic_fit_recovers_synthetic_effective_mass():
    expected_mass = 0.081
    mass_kg = expected_mass * dispersion_models.ELECTRON_MASS_KG
    coefficient = (
        dispersion_models.REDUCED_PLANCK_J_S ** 2
        / (2.0 * mass_kg * dispersion_models.ELEMENTARY_CHARGE_C * 1e-18)
    )
    k = np.linspace(0.0, 0.6, 101)
    energy = 1.2 + coefficient * k ** 2
    fit = dispersion_models.fit_anchored_parabola("e1", k, energy)
    assert fit.effective_mass_m0 == pytest.approx(expected_mass, rel=1e-12)
    assert fit.rmse_meV < 1e-10


def _raw_bands(k):
    return {
        "e1": 2.0 + 0.1 * k ** 2 + 0.01 * k ** 4,
        "e2": 2.2 + 0.12 * k ** 2 + 0.02 * k ** 4,
        "hh1": 0.5 - 0.04 * k ** 2 - 0.03 * k ** 4,
        "hh2": 0.4 - 0.05 * k ** 2 - 0.04 * k ** 4,
    }


def test_05_pchip_reproduces_every_raw_kp8_node():
    k = np.linspace(0.0, 0.6, 21)
    raw = _raw_bands(k)
    reconstructed = dispersion_models.RawKp8(k, raw).evaluate(k)
    for state in dispersion_models.SUBBANDS:
        np.testing.assert_allclose(reconstructed[state], raw[state], rtol=0, atol=1e-14)


def test_06_pchip_refuses_extrapolation():
    k = np.linspace(0.0, 0.6, 21)
    model = dispersion_models.RawKp8(k, _raw_bands(k))
    with pytest.raises(ValueError, match="refusing dispersion extrapolation"):
        model.evaluate(np.asarray([0.0, 0.61]))


def test_07_radial_path_rejects_nonmonotonic_k_coordinate():
    grid = state_tracking.kp8io22.RawStateGrid(
        np.asarray([[0, 0, 0], [0, 0.2, 0], [0, 0.1, 0]], float),
        np.asarray([0.0, 0.2, 0.1]), np.arange(5), np.ones((3, 5)),
        np.ones((3, 5, 2)) / 2, ("CB", "HH"), (), (),
    )
    with pytest.raises(config23.Demo23Error, match="strictly increasing"):
        state_tracking.validate_radial_path(grid)


def test_08_ambiguous_state_tracking_stops_fitting(cfg):
    vectors = np.asarray([[0, 0, 0], [0, 0.1, 0]], float)
    energies = np.asarray([[2.0, 2.2, 0.5, 0.4, 0.3], [2.01, 2.21, 0.49, 0.39, 0.29]])
    spinor = np.asarray([
        [[1, 0], [1, 0], [0, 1], [0, 1], [0, 1]],
        [[0.5, 0.5]] * 5,
    ], float)
    grid = state_tracking.kp8io22.RawStateGrid(
        vectors, np.asarray([0.0, 0.1]), np.arange(5), energies, spinor,
        ("CB", "HH"), (), (),
    )
    with pytest.raises(config23.Demo23Error, match="ambiguous target-state tracking"):
        state_tracking.track_targets(grid, cfg)


def test_09_transition_energy_units_remain_eV():
    k = np.asarray([0.0, 0.1])
    bands = {"e1": np.asarray([2.0, 2.1]), "e2": np.asarray([2.2, 2.3]),
             "hh1": np.asarray([0.5, 0.49]), "hh2": np.asarray([0.4, 0.38])}
    transitions = transition_energies.build_transition_energies(k, bands)
    assert transitions.values_eV[0, 0, 1] == pytest.approx(1.61)


def test_10_gamma_is_one_central_energy_domain_value(cfg):
    settings = physics23.settings_from_config(cfg)
    assert settings.broadening_meV == pytest.approx(5.0)
    assert settings.broadening_eV == pytest.approx(0.005)


def test_11_radial_weights_match_analytic_disc_measure(cfg):
    kmax = config23.kmax_per_nm(cfg)
    k = np.linspace(0.0, kmax, 301)
    weights = k_integration.radial_weights(k)
    assert np.sum(weights) == pytest.approx(k_integration.analytic_disc_measure(kmax), rel=1e-14)


def test_12_radial_agrees_with_cartesian_for_synthetic_isotropic_function(cfg):
    error = k_integration.synthetic_radial_vs_cartesian_error(config23.kmax_per_nm(cfg), points=401)
    assert error < 5e-3


def test_13_normalization_conventions_are_exactly_labeled_and_scaled(cfg):
    k = np.linspace(0.0, config23.kmax_per_nm(cfg), 301)
    normalized = k_integration.radial_weights(k, convention="d2k_over_2pi_squared")
    bare = k_integration.radial_weights(k, convention="bare_d2k")
    np.testing.assert_allclose(bare[1:] / normalized[1:], (2 * math.pi) ** 2, rtol=1e-14)


def test_14_missing_professional_configuration_is_hard_failure():
    with pytest.raises(config23.Demo23Error, match=r"requires nextnano\+\+ Professional"):
        run_demo23.require_professional(None, {"available": False, "reason": "test missing"})


def test_15_solver_failure_writes_no_spectrum(monkeypatch, tmp_path, cfg):
    local = copy.deepcopy(cfg)
    local["paths"]["results_root"] = str(tmp_path / "results")
    deck = tmp_path / "one.in"
    deck.write_text("test", encoding="utf-8")
    spec = deck23.DeckSpec("one", "y", 3, 0.1, 0.5, "production")
    class Machine:
        executable = database = license = tmp_path / "present"
    Machine.executable.write_text("x", encoding="utf-8")
    monkeypatch.setattr(run_demo23.run_demo22.solver14, "execute_real",
                        lambda **_: (_ for _ in ()).throw(RuntimeError("solver failed")))
    called = {"analysis": False}
    monkeypatch.setattr(run_demo23.analysis23, "analyze_run",
                        lambda *args, **kwargs: called.__setitem__("analysis", True))
    with pytest.raises(config23.Demo23Error, match="no chi2 spectrum was generated"):
        run_demo23.run_physics(local, ((spec, deck),), Machine())
    assert called["analysis"] is False
    failure = next((tmp_path / "results").rglob("PHYSICS_RUN_FAILED.json"))
    assert '"spectrum_generated": false' in failure.read_text(encoding="utf-8")


def test_16_all_modes_receive_identical_frozen_matrices(monkeypatch, cfg, frozen):
    settings = physics23.validated.replace_settings(
        physics23.settings_from_config(cfg), k_parallel_points=21
    )
    k, _ = physics23.validated.k_grid(settings)
    raw = _raw_bands(k)
    # Align synthetic k=0 anchors to the real frozen inputs.
    for state, anchor in zip(dispersion_models.SUBBANDS, [
        *frozen.states.electron_energies_eV, *frozen.states.hole_energies_eV
    ]):
        raw[state] = float(anchor) + raw[state] - raw[state][0]
    models, _ = dispersion_models.build_models(
        raw_k_per_nm=k, raw_energies_eV=raw,
        electron_k0_eV=frozen.states.electron_energies_eV,
        heavy_hole_k0_eV=frozen.states.hole_energies_eV,
        reduced_mass_kg=settings.reduced_mass_kg(),
    )
    original = physics23.chi2_22.chi2_from_k_inputs
    observed = []
    def capture(wavelength, kvals, ee, hh, overlap, ze, zhh, **kwargs):
        observed.append((overlap.copy(), ze.copy(), zhh.copy()))
        return original(wavelength, kvals, ee, hh, overlap, ze, zhh, **kwargs)
    monkeypatch.setattr(physics23.chi2_22, "chi2_from_k_inputs", capture)
    for mode in ("23A", "23B", "23C", "23D"):
        physics23.evaluate_mode(mode, models[mode], k, np.asarray([1550.0]), frozen,
                                settings, k0_tolerance_eV=1e-12)
    for overlap, ze, zhh in observed[1:]:
        np.testing.assert_array_equal(overlap, observed[0][0])
        np.testing.assert_array_equal(ze, observed[0][1])
        np.testing.assert_array_equal(zhh, observed[0][2])


def test_17_raw_kp8_mode_never_uses_parabolic_reconstruction():
    k = np.linspace(0.0, 0.6, 21)
    raw = _raw_bands(k)
    raw_mode = dispersion_models.RawKp8(k, raw).evaluate(k)
    parabolic = {state: dispersion_models.fit_anchored_parabola(state, k, raw[state]).evaluate(k)
                 for state in dispersion_models.SUBBANDS}
    for state in dispersion_models.SUBBANDS:
        np.testing.assert_allclose(raw_mode[state], raw[state], atol=1e-14, rtol=0)
    assert any(np.max(np.abs(raw_mode[state] - parabolic[state])) > 1e-7
               for state in dispersion_models.SUBBANDS)


def test_18_decks_share_geometry_and_define_all_convergence_roles(cfg):
    specs = deck23.deck_specs(cfg)
    assert len(specs) == 7
    assert {spec.role for spec in specs} == {
        "production", "grid_convergence", "kmax_convergence", "isotropy"
    }
    for spec in specs:
        text = deck23.render(cfg, spec)
        assert "line{ x = [9.1, 16.2] }" in text
        assert "line{ x = [18, 20.9] }" in text
        assert f"num_points = {spec.points}" in text
        assert "all_k_points = yes" in text
