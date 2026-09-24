"""1994 Eq. 5 absorption factor: limits, stability, and agreement with numerical integration."""
import numpy as np
import pytest

from demo30 import propagation as pr

L80 = 80 * 30e-9  # 2.4 um


def test_no_absorption_is_the_transparent_result():
    assert pr.absorption_factor(0.0, 0.0, L80) == 1.0
    tiny = pr.absorption_factor(1e-3, 2e-3, L80)
    assert tiny == pytest.approx(1.0, abs=1e-8)


def test_alpha_2w_equal_to_twice_alpha_w_is_stable():
    a1 = 2.0e5
    exact = np.exp(-2 * a1 * L80)  # limit of Eq. 5 when alpha_2w = 2 alpha_w: A = exp(-alpha_2w L)
    assert pr.absorption_factor(a1, 2 * a1, L80) == pytest.approx(exact, rel=1e-14)
    for eps in (1e-12, 1e-9, 1e-7, 1e-5):
        for sign in (1, -1):
            val = pr.absorption_factor(a1, 2 * a1 * (1 + sign * eps), L80)
            assert val == pytest.approx(exact, rel=10 * eps + 1e-12)


def test_thick_slab_with_transparent_pump():
    a2 = 50 / L80
    assert pr.absorption_factor(0.0, a2, L80) == pytest.approx((1 - np.exp(-50)) / 50, rel=1e-13)


@pytest.mark.parametrize("a1,a2", [(0.0, 3.3e5), (1.2e2, 3.3e5), (2.0e5, 1.0e5), (3.0e5, 6.0e5), (5e4, 5e4)])
def test_closed_form_matches_ode_and_overlap_integral(a1, a2):
    closed = float(pr.absorption_factor(a1, a2, L80))
    assert pr.absorption_factor_ode(a1, a2, L80) == pytest.approx(closed, rel=1e-8)
    assert pr.absorption_factor_overlap(a1, a2, L80) == pytest.approx(closed, rel=1e-8)


def test_transparent_sh_field_grows_linearly_with_length():
    t1 = pr.sh_transfer_m_per_V(30.0, 0.8, 3.44, L80, 1.0)
    t2 = pr.sh_transfer_m_per_V(30.0, 0.8, 3.44, 2 * L80, 1.0)
    assert t2 == pytest.approx(2 * t1, rel=1e-14)
    by_hand = (0.8 / 1.973269804e-7) / 3.44 * 30e-12 * L80  # (w/(n c)) |chi2| L
    assert t1 == pytest.approx(by_hand, rel=1e-12)


def test_coherence_length():
    c = pr.coherence_length(1550.0, 3.2, 3.44, L80)
    assert c["coherence_length_um"] == pytest.approx(1.550 / (4 * 0.24), rel=1e-12)
    assert 0 < c["sinc2_suppression_if_transparent"] < 1
