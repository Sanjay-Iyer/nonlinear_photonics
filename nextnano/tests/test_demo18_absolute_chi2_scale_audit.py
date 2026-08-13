"""Focused solver-free contracts for Demo 18."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

DEMOS = Path(__file__).resolve().parents[1] / "demos"
for dependency in (
    DEMOS / "18_absolute_chi2_scale_audit",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "14_absolute_chi2_graded_acqw_bo",
    DEMOS / "16_acqw_renderer_stress_validation",
    DEMOS / "11_paper_validation_interband_chi2_acqw",
    DEMOS / "_shared",
):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import cases18
import config18
import demo18
import chi2 as chi2mod


@pytest.fixture(scope="module")
def cfg():
    return config18.load_config()


@pytest.fixture(scope="module")
def states():
    return demo18.synthetic_states()


def _value(cfg, states, case):
    return demo18.evaluate_case(cfg, case, *states, np.asarray([1550.0])).row[
        "chi2_at_1550_pm_per_V"
    ]


def test_fixed_case_and_compact_matrix():
    case = cases18.reference_solver_case()
    assert case.well_widths_nm() == pytest.approx((7.1, 2.9))
    assert case.central_barrier_nm == pytest.approx(1.8)
    assert case.is_abrupt
    assert len(cases18.audit_cases()) == 8


def test_nz_scaling_is_exactly_linear(cfg, states):
    rows = {case.case_id: case for case in cases18.audit_cases()}
    assert _value(cfg, states, rows["B_two_wells_Nz"]) / _value(
        cfg, states, rows["A_baseline"]
    ) == pytest.approx(2.0, rel=1e-12)


def test_spin_scaling_is_explicit_and_linear(cfg, states):
    rows = {case.case_id: case for case in cases18.audit_cases()}
    assert _value(cfg, states, rows["H_spin2"]) / _value(
        cfg, states, rows["G_spin1"]
    ) == pytest.approx(2.0, rel=1e-12)


def test_r_ehh_scaling_is_quadratic(cfg, states):
    base = cases18.ScaleCase(
        "base", "base", "two_wells_per_period", "bz_2pi_over_a", 96, 2, 1.0
    )
    raised = cases18.ScaleCase(
        "raised", "raised", "two_wells_per_period", "bz_2pi_over_a", 96, 2, 1.1
    )
    assert _value(cfg, states, raised) / _value(cfg, states, base) == pytest.approx(
        1.21, rel=1e-12
    )


def test_independent_prefactor_matches_production(cfg, states):
    case = cases18.audit_cases()[0]
    settings = demo18.settings_for_case(cfg, case)
    production = chi2mod.chi2_spectrum(
        *states, [float(chi2mod.photon_energy_eV(1550.0))], settings
    )
    check = demo18.prefactor_cross_check(
        production.scale_factor,
        settings,
        tolerance=float(cfg["chi2"]["prefactor_relative_tolerance"]),
    )
    assert check["passed"]
    assert check["relative_difference"] <= 1e-14


@pytest.mark.parametrize("points", [96, 192, 384])
def test_k_grid_reaches_named_large_cutoff(cfg, points):
    case = cases18.ScaleCase(
        f"grid_{points}", "grid", "two_wells_per_period",
        "bz_2pi_over_a", points, 2,
    )
    settings = demo18.settings_for_case(cfg, case)
    k, weights = chi2mod._k_grid(settings)
    assert k.size == weights.size == points
    assert k[0] == 0.0
    assert k[-1] == pytest.approx(0.1 * 2.0 * np.pi / 0.565325)
