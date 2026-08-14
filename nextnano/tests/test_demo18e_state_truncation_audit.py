"""Solver-free contracts for Demo 18E."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
DEMOS = ROOT / "nextnano" / "demos"
DEMO = DEMOS / "18E_electron_hh_cancellation_state_truncation_audit"
for dependency in (DEMO,):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import analysis18e
import config18e
import run_demo18e


@pytest.fixture(scope="module")
def cfg():
    return config18e.load_config()


@pytest.fixture(scope="module")
def case19(cfg):
    return run_demo18e._load_handoff(cfg)["model"]


def test_primary_physics_is_immutable(cfg) -> None:
    fixed = cfg["fixed_physics"]
    assert fixed["broadening_meV"] == 5.0
    assert fixed["spin_degeneracy"] == 2
    assert fixed["wells_per_period_for_Nz"] == 2
    assert fixed["nominal_period_nm"] == 30.0
    assert fixed["r_e_hh_nm"] == 0.751
    assert fixed["hh_relative_weight"] == 1.0


def test_exported_case19_matrices_reproduce_demo18d(case19, cfg) -> None:
    settings = analysis18e.settings_from_config(cfg)
    value, branches, rows = analysis18e.evaluate(
        case19.subset((0, 1), (0, 1)), analysis18e.HC_EV_NM / 1550.0,
        settings, decompose=True,
    )
    assert abs(value) == pytest.approx(144.65656692330407, abs=1e-8)
    assert abs(branches["electron"]) == pytest.approx(7171.0257454792645, abs=1e-8)
    assert abs(branches["heavy_hole"]) == pytest.approx(7066.891782875193, abs=1e-8)
    assert len(rows) == 16


@pytest.mark.parametrize("n_e,n_hh", [(2, 2), (2, 3), (3, 2), (3, 3)])
def test_unequal_state_count_has_complete_independent_sums(case19, cfg, n_e, n_hh) -> None:
    settings = analysis18e.settings_from_config(cfg)
    selected = case19.subset(range(n_e), range(n_hh))
    _value, _branches, rows = analysis18e.evaluate(
        selected, analysis18e.HC_EV_NM / 1550.0, settings, decompose=True
    )
    assert len(rows) == n_hh * n_e * n_e + n_hh * n_e * n_hh


def test_random_complex_phases_cancel_from_bra_ket_products(case19, cfg) -> None:
    settings = analysis18e.settings_from_config(cfg)
    rows = analysis18e.phase_invariance(
        case19.subset((0, 1), (0, 1, 2)), settings, seed=1805, trials=8
    )
    assert max(row["relative_residual"] for row in rows) < 1e-11


def test_complete_state_set_is_permutation_invariant(case19, cfg) -> None:
    settings = analysis18e.settings_from_config(cfg)
    rows = analysis18e.permutation_invariance(case19.subset((0, 1, 2), (0, 1, 2)), settings)
    assert max(row["relative_residual"] for row in rows) < 1e-11


def test_complete_exact_degenerate_hh23_subspace_is_rotation_invariant(case19, cfg) -> None:
    settings = analysis18e.settings_from_config(cfg)
    model = case19.subset((0, 1), (0, 1, 2))
    values = []
    for theta in range(0, 91, 5):
        rotated = analysis18e.hh23_rotation_model(model, theta)
        value, _branches, _rows = analysis18e.evaluate(
            rotated, analysis18e.HC_EV_NM / 1550.0, settings
        )
        values.append(value)
    assert max(abs(value - values[0]) for value in values) / abs(values[0]) < 1e-11


def test_rotation_control_does_not_silently_change_actual_hh_energies(case19) -> None:
    model = case19.subset((0, 1), (0, 1, 2))
    original = model.heavy_hole_energies_eV.copy()
    rotated = analysis18e.hh23_rotation_model(model, 45)
    assert np.array_equal(model.heavy_hole_energies_eV, original)
    assert rotated.heavy_hole_energies_eV[1] == rotated.heavy_hole_energies_eV[2]
    assert rotated.heavy_hole_energies_eV[1] == pytest.approx(np.mean(original[1:]))


def test_runner_never_launches_a_licensed_solver() -> None:
    source = (DEMO / "run_demo18e.py").read_text(encoding="utf-8")
    assert "solve_case(" not in source
    assert "subprocess.run(" in source  # git provenance only
    assert "new_licensed_solves_required\": 0" in source

