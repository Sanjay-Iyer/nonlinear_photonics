"""Units, conventions and Equation 2 algebra."""
import json

import numpy as np
import pytest

from src.equation2 import (HC_EV_NM, Settings, analytic_integral, evaluate, evaluate_parabolic,
                           photon_energy, prefactor, radial_weights)
from src.reporting import observables


def toy_inputs(k=None, complex_phase=None, rng=np.random.default_rng(7)):
    k = np.linspace(0.0, 0.5, 51) if k is None else k
    o = rng.normal(size=(2, 2))
    ze = rng.normal(size=(2, 2)); ze = ze + ze.T + 12 * np.eye(2)
    zh = rng.normal(size=(2, 2)); zh = zh + zh.T + 12 * np.eye(2)
    return {"k_per_nm": k,
            "electron_eV": np.vstack([2.94 + 0.52 * k ** 2, 3.06 + 0.45 * k ** 2]),
            "valence_eV": np.vstack([1.448 - 0.096 * k ** 2, 1.413 - 0.054 * k ** 2]),
            "overlap": o, "ze_nm": ze, "zh_nm": zh}


def test_gamma_meV_to_eV():
    assert Settings(gamma_meV=5.0).gamma_eV == pytest.approx(0.005, abs=1e-18)
    with pytest.raises(ValueError):
        Settings(gamma_meV=0.0)


def test_photon_energy_convention():
    assert photon_energy(np.array([HC_EV_NM]))[0] == pytest.approx(1.0)
    assert photon_energy(np.array([1550.0]))[0] == pytest.approx(0.7998980541935484)
    with pytest.raises(ValueError):
        photon_energy(np.array([0.0]))


def test_wavelength_is_fundamental():
    """One flat transition dE: the two-photon pole sits at 2hc/dE on the fundamental axis."""
    k = np.linspace(0, 1e-3, 3)
    dE = 1.6
    inputs = {"k_per_nm": k, "electron_eV": np.full((2, 3), dE + 1.0), "valence_eV": np.full((2, 3), 1.0),
              "overlap": np.eye(2), "ze_nm": np.diag([2.0, 0.0]), "zh_nm": np.zeros((2, 2))}
    wl = np.arange(600.0, 1700.0, 0.25)
    chi = evaluate(wl, inputs)[0]
    assert abs(wl[np.argmax(np.abs(chi))] - 2 * HC_EV_NM / dE) < 1.0


def test_shapes_and_pathway_census():
    wl = np.linspace(500, 1700, 61)
    chi, terms, labels, weights = evaluate(wl, toy_inputs())
    assert chi.shape == (61,) and terms.shape == (16, 61) and len(set(labels)) == 16
    assert sum(l.startswith("C_") for l in labels) == 8 and sum(l.startswith("V_") for l in labels) == 8
    assert np.allclose(terms.sum(axis=0), chi, atol=1e-12, rtol=0)
    assert weights.shape == (51,)


def test_imaginary_part_survives_and_sign_convention():
    wl = np.linspace(500, 1700, 61)
    inp = toy_inputs()
    plus = evaluate(wl, inp, Settings(gamma_sign=1))[0]
    minus = evaluate(wl, inp, Settings(gamma_sign=-1))[0]
    assert np.iscomplexobj(plus) and np.max(np.abs(plus.imag)) > 1e-3
    assert np.allclose(minus, np.conj(plus), rtol=0, atol=1e-10)  # real inputs: -i Gamma is the conjugate


def test_abs_real_is_not_magnitude_when_imag_nonzero():
    wl = np.linspace(500, 1700, 61)
    ob = observables(evaluate(wl, toy_inputs())[0])
    mask = np.abs(ob["imag"]) > 1e-9
    assert mask.any()
    assert np.all(ob["abs"][mask] > ob["abs_real"][mask])
    assert np.allclose(ob["abs"], np.sqrt(ob["real"] ** 2 + ob["imag"] ** 2), rtol=0, atol=1e-12)


def test_real_inputs_equal_literal_demo22_algebra():
    wl = np.linspace(500, 1700, 61)
    inp = toy_inputs()
    k, ee, hh = inp["k_per_nm"], inp["electron_eV"], inp["valence_eV"]
    o, ze, zh = inp["overlap"], inp["ze_nm"], inp["zh_nm"]
    tr = ee[:, None, :] - hh[None, :, :]
    hw = HC_EV_NM / wl
    g = 0.005
    summed = np.zeros((len(wl), len(k)), complex)
    for m in range(2):
        for n in range(2):
            d2 = tr[n, m][None, :] - 2 * hw[:, None] + 1j * g
            for ell in range(2):
                summed += o[n, m] * ze[n, ell] * o[ell, m] / (d2 * (tr[ell, m][None, :] - hw[:, None] + 1j * g))
            for ell in range(2):
                summed += -o[n, m] * zh[m, ell] * o[n, ell] / (d2 * (tr[n, ell][None, :] - hw[:, None] + 1j * g))
    literal = prefactor(Settings()) * (summed @ radial_weights(k, 2))
    assert np.allclose(evaluate(wl, inp)[0], literal, rtol=1e-12, atol=1e-10)


def test_state_phase_gauge_invariance_for_complex_inputs():
    wl = np.linspace(500, 1700, 41)
    inp = toy_inputs()
    base = evaluate(wl, inp)[0]
    a, b = np.array([0.7, -1.9]), np.array([2.3, 0.4])
    ph = {"overlap": np.exp(-1j * a)[:, None] * np.exp(1j * b)[None, :],
          "ze_nm": np.exp(-1j * a)[:, None] * np.exp(1j * a)[None, :],
          "zh_nm": np.exp(-1j * b)[:, None] * np.exp(1j * b)[None, :]}
    rotated = {**inp, **{key: inp[key] * ph[key] for key in ph}}
    assert np.allclose(evaluate(wl, rotated)[0], base, rtol=1e-12, atol=1e-10)


def test_origin_invariance_for_orthonormal_basis():
    wl = np.linspace(500, 1700, 41)
    inp = toy_inputs()
    shifted = {**inp, "ze_nm": inp["ze_nm"] + 37.0 * np.eye(2), "zh_nm": inp["zh_nm"] + 37.0 * np.eye(2)}
    assert np.allclose(evaluate(wl, shifted)[0], evaluate(wl, inp)[0], rtol=0, atol=1e-9)


def test_prefactor_matches_demo21(root):
    ref = json.loads((root / "validation/reference_demo26.json").read_text())
    value = next(c["value"] for c in ref["modes"]["kp8"] if c["id"] == "prefactor_pm_per_V")
    assert prefactor(Settings()) == pytest.approx(value, rel=1e-12)


@pytest.mark.parametrize("k", [np.linspace(0, 0.5557, 301), np.sort(np.r_[0, np.random.default_rng(1).uniform(0, 1.1, 99), 1.1])])
def test_radial_weights_are_the_disc_measure(k):
    w = radial_weights(k, 2)
    assert w.sum() == pytest.approx(2 * k[-1] ** 2 / (4 * np.pi), rel=1e-12)


def test_analytic_integral_matches_quadrature():
    a = np.array([1.5 - 2 * 0.9 + 0.005j, 1.5 - 2 * 0.6 + 0.005j])  # one resonant, one not
    b = np.array([1.6 - 0.9 + 0.005j, 1.6 - 0.6 + 0.005j])
    k = np.linspace(0, 1.1, 400001)
    f = 2 * np.pi * k[None, :] / ((0.6 * k ** 2 + a[:, None]) * (0.55 * k ** 2 + b[:, None]))
    quad = np.trapezoid(f, k, axis=1)
    assert np.allclose(analytic_integral(0.6, a, 0.55, b, 1.1), quad, rtol=1e-6)


def test_trapezoid_and_analytic_paths_agree():
    k = np.linspace(0, 0.5, 20001)
    base = toy_inputs(k)
    e0, a = np.array([2.94, 3.06, 1.448, 1.413]), np.array([0.52, 0.45, -0.096, -0.054])
    para = {"energy_eV": e0, "curvature_eV_nm2": a, "overlap": base["overlap"], "ze_nm": base["ze_nm"], "zh_nm": base["zh_nm"]}
    wl = np.arange(700.0, 1600.0, 10.0)
    trap = evaluate(wl, base)[0]
    anal = evaluate_parabolic(wl, para, 0.5)[0]
    assert np.max(np.abs(trap - anal)) / np.max(np.abs(anal)) < 1e-4
