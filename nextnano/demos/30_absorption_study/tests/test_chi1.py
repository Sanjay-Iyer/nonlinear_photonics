"""chi1: prefactor units, a closed-form parabolic case, the tail, and use of the Eq. 2 inputs."""
import numpy as np
import pytest

from demo30 import chi1 as c1
from demo30.equation2 import Settings

S = Settings()  # Gamma 5 meV, gamma_sign +1, spin 2, period 30 nm, r_e,hh 0.751 nm


def test_prefactor_from_constants():
    e, eps0 = 1.602176634e-19, 8.8541878128e-12
    nz, r = 1 / 30e-9, 0.751e-9
    expected = nz * e ** 2 * r ** 2 / eps0 * 1e18 / e  # N_z e^2 r^2/eps0, w in nm^-2, E in eV
    assert c1.chi1_prefactor(S) == pytest.approx(expected, rel=1e-12)
    assert c1.chi1_prefactor(S) == pytest.approx(0.340189, rel=1e-5)


def _parabola(e0=1.5, slope=0.6, kmax=0.5557, nk=4001, o2=0.8):
    k = np.linspace(0, kmax, nk)
    return k, c1.Pair("synthetic", e0 + slope * k ** 2, np.full(nk, o2), "test")


def test_strict_parabolic_band_matches_closed_form():
    k, pair = _parabola()
    e = np.linspace(1.40, 1.80, 81)
    got = c1.strict_terms(e, [pair], k, S)[0]
    top = pair.transition_eV[-1]
    jdos = S.spin_degeneracy / (4 * np.pi * 0.6)
    pref = c1.chi1_prefactor(S) * 0.8 * jdos
    g = S.gamma_eV
    im = -pref * (np.arctan((top - e) / g) - np.arctan((1.5 - e) / g))
    re = pref * 0.5 * np.log(((top - e) ** 2 + g ** 2) / ((1.5 - e) ** 2 + g ** 2))
    scale = pref * np.pi
    assert np.max(np.abs(got.imag - im)) / scale < 2e-4
    assert np.max(np.abs(got.real - re)) / scale < 2e-4


def test_tail_completes_the_infinite_parabola():
    """strict (to k_max) + analytical tail = the exact broadened 2D step of an infinite parabola."""
    k, pair = _parabola()
    e = np.linspace(1.40, 1.95, 111)
    res = c1.evaluate(e, [pair], k, S, fit_fraction=0.1)
    assert res.tail_slopes[0] == pytest.approx(0.6, rel=1e-10)
    jdos = S.spin_degeneracy / (4 * np.pi * 0.6)
    exact_im = -c1.chi1_prefactor(S) * 0.8 * jdos * (np.pi / 2 + np.arctan((e - 1.5) / S.gamma_eV))
    scale = c1.chi1_prefactor(S) * 0.8 * jdos * np.pi
    assert np.max(np.abs(res.tail.imag - exact_im)) / scale < 2e-4
    assert np.array_equal(res.tail.real, res.strict.real)  # the tail never changes Re


def test_tail_rejects_non_increasing_dispersion():
    k = np.linspace(0, 0.5, 101)
    flat = c1.Pair("flat", 1.5 - 0.1 * k ** 2, np.ones(101), "test")
    with pytest.raises(ValueError, match="non-positive"):
        c1.tail_slope(flat, k, 0.1)


def test_pairs_2x2_are_the_eq2_energies_and_overlaps():
    k = np.linspace(0, 0.5, 11)
    inputs = {"k_per_nm": k, "electron_eV": np.array([2.9 + 0.1 * k ** 2, 3.0 + 0.1 * k ** 2]),
              "valence_eV": np.array([1.45 - 0.2 * k ** 2, 1.40 - 0.1 * k ** 2]),
              "overlap": np.array([[0.98, 0.02], [-0.08, 0.38]])}
    pairs = c1.pairs_2x2(inputs)
    assert [p.label for p in pairs] == ["e1-hh1", "e1-hh2", "e2-hh1", "e2-hh2"]
    for p, (n, m) in zip(pairs, [(0, 0), (0, 1), (1, 0), (1, 1)]):
        np.testing.assert_array_equal(p.transition_eV, inputs["electron_eV"][n] - inputs["valence_eV"][m])
        np.testing.assert_allclose(p.overlap_sq, inputs["overlap"][n, m] ** 2)


def test_real_data_expanded_set_contains_the_2x2_block(state):
    from demo30 import absorption_study as a, bound_states as bs
    sets = a.pair_sets(state)
    o = bs.overlaps(sets["states"])
    np.testing.assert_array_equal(o[:2, :2], np.real(state["inputs"]["overlap"]))
    labels = [p.label for p in sets["expanded_bound_states"]]
    assert labels[:4] == ["e1-hh1", "e1-hh2", "e2-hh1", "e2-hh2"]
    assert len(labels) == 18 and "e2-hh3" in labels and "e3-hh2" in labels
