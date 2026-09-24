"""Absorption: positive for passive media in both time conventions; alpha_I = 2 alpha_E."""
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from demo30 import absorption as ab
from demo30 import chi1 as c1
from demo30.equation2 import Settings


def _chi(sign):
    k = np.linspace(0, 0.5557, 1201)
    pair = c1.Pair("synthetic", 1.5 + 0.6 * k ** 2, np.full(k.size, 0.9), "test")
    e = np.linspace(1.3, 1.9, 121)
    return e, c1.strict_terms(e, [pair], k, Settings(gamma_sign=sign))[0]


def test_passive_absorption_is_positive_in_both_conventions():
    e, chi_plus = _chi(+1)   # Eq. 2 convention (+i Gamma): Im chi1 < 0 for loss
    _, chi_minus = _chi(-1)  # 1994 convention (1/(Delta - i)): Im chi1 > 0 for loss
    np.testing.assert_allclose(chi_minus, np.conj(chi_plus), rtol=0, atol=1e-15)
    assert np.all(chi_plus.imag < 0) and np.all(chi_minus.imag > 0)
    a_plus, a_minus = ab.alpha_E(chi_plus, e, 3.4, +1), ab.alpha_E(chi_minus, e, 3.4, -1)
    assert np.all(a_plus > 0)
    np.testing.assert_allclose(a_plus, a_minus, rtol=1e-14)


def test_intensity_coefficient_is_twice_the_field_coefficient():
    e, chi = _chi(+1)
    np.testing.assert_allclose(ab.alpha_I(chi, e, 3.4, 1), 2 * ab.alpha_E(chi, e, 3.4, 1), rtol=0)
    # propagate a field numerically with dE/dz = -alpha_E E (1994 Eq. 3b without coupling)
    a_e, length = 4.0e5, 2.4e-6  # m^-1, m
    sol = solve_ivp(lambda z, y: -a_e * y, (0, length), [1.0], rtol=1e-12, atol=1e-14)
    field = sol.y[0, -1]
    assert field == pytest.approx(np.exp(-a_e * length), rel=1e-9)            # E(z) = E0 exp(-alpha_E z)
    assert field ** 2 == pytest.approx(np.exp(-2 * a_e * length), rel=1e-9)   # I(z) = I0 exp(-alpha_I z)


def test_alpha_units_by_hand():
    e, n, im = np.array([1.6]), 3.4, -0.3
    by_hand = (1.6 / 1.973269804e-7) * 0.3 / (2 * 3.4)  # (w/c) * (-Im chi1) / (2n), m^-1
    assert ab.alpha_E(np.array([1j * im]), e, n, +1)[0] == pytest.approx(by_hand, rel=1e-12)
    assert ab.per_cm(by_hand) == pytest.approx(by_hand / 100)
    assert ab.length_um(np.array([1e6]))[0] == pytest.approx(1.0)


def test_first_order_alpha_matches_the_exact_index():
    e, chi = _chi(+1)
    approx, exact = ab.alpha_E(chi, e, 3.44, 1), ab.alpha_E_exact(chi, e, 3.44, 1)
    assert np.all(exact > 0)
    assert np.max(np.abs(approx - exact) / exact) < 0.03
