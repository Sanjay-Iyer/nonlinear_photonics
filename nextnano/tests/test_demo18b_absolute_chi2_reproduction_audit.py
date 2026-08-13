"""Focused solver-free contracts for Demo 18B."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest

DEMOS = Path(__file__).resolve().parents[1] / "demos"
for dependency in (
    DEMOS / "18B_absolute_chi2_reproduction_audit",
    DEMOS / "18_absolute_chi2_scale_audit",
    DEMOS / "16F_paper_absolute_chi2_reproduction_audit",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "16_acqw_renderer_stress_validation",
    DEMOS / "14_absolute_chi2_graded_acqw_bo",
    DEMOS / "11_paper_validation_interband_chi2_acqw",
    DEMOS / "_shared",
):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import audit18b
import cases18b
import config18b
import demo18
import run_demo18b


@pytest.fixture(scope="module")
def cfg():
    return config18b.load_config()


@pytest.fixture(scope="module")
def states():
    return demo18.synthetic_states()


def test_fixed_six_deck_matrix_and_mesh_alias(cfg):
    rows = cases18b.solve_cases()
    assert len(rows) == 6
    assert len({(r.domain_padding_nm, r.quantum_padding_nm, r.mesh_nm) for r in rows}) == 6
    assert cases18b.mesh_cases_with_alias() == (
        ("M0_0p10nm", 0.10), ("D3_plus40", 0.05), ("M2_0p025nm", 0.025)
    )
    for row in rows:
        solver_cfg, _case, _geometry, _profile, _blocks, deck = run_demo18b._case_geometry(cfg, row)
        assert "no_density = yes" in deck
        assert solver_cfg["geometry"]["period_barrier_nm"] == pytest.approx(18.2)


def test_independent_eq2_matches_production_full_and_small_grid(cfg, states):
    cross = audit18b.eq2_cross_check(*states, audit18b.primary_settings(cfg), 1550.0)
    assert cross["relative_difference"] < 1e-12
    assert all(row["relative_difference"] < 1e-12 for row in cross["grid_checks"])
    assert cross["single_k0_relative_difference"] < 1e-13
    assert len(cross["term_rows"]) == 16


def test_eq2_decomposition_is_ranked_and_closes(cfg, states):
    cross = audit18b.eq2_cross_check(*states, audit18b.primary_settings(cfg), 1550.0)
    rows = cross["term_rows"]
    assert [row["magnitude_rank"] for row in rows] == list(range(1, 17))
    assert {row["path"] for row in rows} == {"electron", "heavy_hole"}
    assert {row["z_kind"] for row in rows} == {"diagonal", "off_diagonal"}
    assert cross["electron_contribution"] + cross["heavy_hole_contribution"] == pytest.approx(
        cross["independent_chi2"], rel=1e-13
    )


def test_origin_invariance_at_both_requested_shifts(cfg, states):
    rows = audit18b.origin_audit(cfg, *states)
    assert [row["shift_nm"] for row in rows] == [10.0, 50.0]
    assert all(row["passed"] for row in rows)


def test_matrix_translation_law_on_nonuniform_grid():
    u = np.linspace(0.0, 1.0, 3001)
    z = 8.0 * u**1.2
    p1 = np.sqrt(2 / 8) * np.sin(np.pi * z / 8)
    p2 = np.sqrt(2 / 8) * np.sin(2 * np.pi * z / 8)
    e = audit18b.production_chi2.BandStates(z, [2.9, 3.1], np.column_stack((p1, p2)), "e")
    _, matrix, _ = audit18b.matrices(e, e)
    shifted = audit18b.production_chi2.BandStates(
        z + 17.0, e.energies_eV, e.envelopes, "e"
    )
    _, shifted_matrix, _ = audit18b.matrices(shifted, shifted)
    assert shifted_matrix[0, 1] == pytest.approx(matrix[0, 1], abs=2e-6)
    assert shifted_matrix[0, 0] - matrix[0, 0] == pytest.approx(17.0, abs=2e-6)


def test_analytic_box_position_integral_on_nonuniform_grid():
    u = np.linspace(0.0, 1.0, 4001)
    length = 10.0
    z = length * u**1.3
    p1 = np.sqrt(2 / length) * np.sin(np.pi * z / length)
    p2 = np.sqrt(2 / length) * np.sin(2 * np.pi * z / length)
    states = audit18b.production_chi2.BandStates(
        z, [1.0, 2.0], np.column_stack((p1, p2)), "box"
    )
    overlap, matrix, _ = audit18b.matrices(states, states)
    assert overlap[0, 0] == pytest.approx(1.0, abs=2e-10)
    assert overlap[1, 1] == pytest.approx(1.0, abs=2e-10)
    assert overlap[0, 1] == pytest.approx(0.0, abs=1e-8)
    assert overlap[1, 0] == pytest.approx(0.0, abs=1e-8)
    assert abs(matrix[0, 1]) == pytest.approx(16 * length / (9 * np.pi**2), rel=2e-7)
    assert matrix[0, 0] == pytest.approx(length / 2, abs=2e-7)


def test_native_nextnano_overlap_and_dipole_agree_with_fixture(cfg):
    fixture = (
        Path(__file__).resolve().parent / "fixtures" / "nextnano_pp_3_0_0"
        / "demo11_acqw_paper"
    )
    solver_cfg = config18b.solver_config(cfg, cases18b.solve_cases()[0])
    data = audit18b.load_solved_data(solver_cfg, fixture)
    rows, summary = audit18b.native_matrix_comparison(fixture, data.electron, data.heavy_hole)
    assert rows
    assert summary["max_absolute_overlap_difference"] < 1e-6
    assert summary["max_absolute_dipole_difference_nm"] < 1e-5
    assert not summary["diagonal_dipoles_comparable"]


def _confined_solved_data():
    z = np.linspace(0.0, 20.0, 4001)
    raw = np.column_stack((
        np.exp(-0.5 * ((z - 7.0) / 1.0) ** 2),
        (z - 10.0) * np.exp(-0.5 * ((z - 10.0) / 1.3) ** 2),
    ))
    electron = audit18b.production_chi2.BandStates(z, [2.9, 3.05], raw, "electron")
    hole_raw = np.column_stack((
        np.exp(-0.5 * ((z - 7.5) / 0.9) ** 2),
        (z - 11.0) * np.exp(-0.5 * ((z - 11.0) / 1.1) ** 2),
    ))
    hole = audit18b.production_chi2.BandStates(z, [1.5, 1.4], hole_raw, "heavy_hole")
    density_e = np.column_stack([electron.envelopes[:, i] ** 2 for i in range(2)])
    density_h = np.column_stack([hole.envelopes[:, i] ** 2 for i in range(2)])
    return audit18b.SolvedData(
        electron, hole, density_e, density_h, z,
        {"position_nm": z, "conduction_eV": np.full_like(z, 3.4),
         "heavy_hole_eV": np.full_like(z, 1.0)}, Path("synthetic"),
    )


def test_strict_bound_state_audit_reports_all_metrics(cfg):
    data = _confined_solved_data()
    geometry = SimpleNamespace(active_start_nm=4.0, active_end_nm=16.0, domain_nm=(0.0, 20.0))
    rows = audit18b.state_audit(data, geometry, 4.0, cfg["bound_state_criteria"])
    assert len(rows) == 4
    required = {
        "energy_eV", "barrier_edge_eV", "binding_energy_meV", "bound_pass",
        "centroid_nm", "rms_width_nm", "active_region_probability",
        "left_padding_probability", "right_padding_probability",
        "left_boundary_probability", "right_boundary_probability",
        "left_boundary_amplitude_nm_minus_half", "right_boundary_amplitude_nm_minus_half",
    }
    assert all(required <= set(row) for row in rows)
    assert all(row["bound_pass"] for row in rows)


def test_first_bound_selection_fails_closed_when_state_is_unbound(cfg):
    data = _confined_solved_data()
    geometry = SimpleNamespace(active_start_nm=4.0, active_end_nm=16.0, domain_nm=(0.0, 20.0))
    rows = audit18b.state_audit(data, geometry, 4.0, cfg["bound_state_criteria"])
    rows[1]["bound_pass"] = False
    with pytest.raises(audit18b.Audit18BError):
        audit18b.first_bound_states(data, rows, 2)


def test_r_ehh_required_value_is_explicitly_hypothetical(cfg):
    row = audit18b.r_ehh_audit(cfg, 84.13778453632841)
    assert row["required_chi2_factor"] == pytest.approx(2340 / 84.13778453632841)
    assert row["required_r_factor"] == pytest.approx(np.sqrt(row["required_chi2_factor"]))
    assert row["hypothetical_fitted_r_e_hh_nm"] == pytest.approx(3.9607, rel=1e-3)
    assert row["paper_2026_published_numeric_r_e_hh"] is None
    assert row["classification"].startswith("fitted_hypothetical")


def test_convention_table_has_case_safe_headers(cfg, states):
    rows = audit18b.convention_audit(cfg, *states)
    headers = {key for row in rows for key in row}
    assert len({key.casefold() for key in headers}) == len(headers)
    assert "nz_convention" in headers
    assert "Nz_convention" not in headers


def test_k_saturation_extends_beyond_paper_limit(cfg, states):
    rows = audit18b.k_saturation_audit(cfg, *states)
    assert [row["fraction_of_2pi_over_a"] for row in rows] == [0.05, 0.10, 0.15, 0.20]
    assert next(row for row in rows if row["role"] == "paper_limit")["fraction_of_2pi_over_a"] == 0.10


def test_poisson_audit_does_not_invent_missing_charge_inputs():
    audit = audit18b.poisson_audit()
    assert audit["current_deck_setting"] == "no_density = yes"
    assert not audit["licensed_comparison_run"]
    assert "doping profile" in audit["missing_from_paper"]
    assert audit["status"] == "scientifically_underdetermined_not_fabricated"


def test_csv_writer_rejects_case_insensitive_duplicate_headers(tmp_path):
    with pytest.raises(run_demo18b.Runner18BError):
        run_demo18b._write_csv(
            tmp_path / "bad.csv", [{"nz_convention": "a", "Nz_convention": "a"}]
        )


def test_degeneracy_ledger_keeps_open_hh_factor_unapplied():
    ledger = {row["factor"]: row for row in audit18b.degeneracy_ledger()}
    assert ledger["electron_spin"]["included"]
    assert not ledger["heavy_hole_mj"]["included"]
    assert ledger["tensor_input_permutation"]["value"] == 1


def test_preflight_contract():
    assert run_demo18b.run_preflight() == 0
