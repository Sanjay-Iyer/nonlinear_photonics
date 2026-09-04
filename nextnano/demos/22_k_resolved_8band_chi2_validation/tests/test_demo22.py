from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


DEMO = Path(__file__).resolve().parents[1]
if str(DEMO) not in sys.path:
    sys.path.insert(0, str(DEMO))

import chi2_22
import config22
import deck22
import kp8io22
import run_demo22
import state_tracking22


def test_exact_primary_geometry_and_interfaces():
    cfg = config22.load_config()
    assert cfg["geometry"]["primary_interface_model"] == "abrupt"
    assert deck22.interfaces(cfg) == pytest.approx((9.1, 16.2, 18.0, 20.9))
    assert sum((9.1, 7.1, 1.8, 2.9, 9.1)) == pytest.approx(30.0)


@pytest.mark.parametrize("interface_model", ["abrupt", "linear_1nm"])
@pytest.mark.parametrize("calculation", ["integration", "dispersion"])
def test_decks_request_true_all_k_kp8(interface_model, calculation):
    text = deck22.render(config22.load_config(), interface_model=interface_model,
                         calculation=calculation)
    assert "kp_8band{" in text
    assert "all_k_points = yes" in text
    assert "spinor_composition_CB_HH_LH_SO = yes" in text
    assert "dipole_moment_matrix_elements" in text
    assert "momentum_matrix_elements" in text
    assert "line{ x = [9.1, 16.2] }" in text
    assert "line{ x = [18, 20.9] }" in text
    assert "num_points = 96" in text if calculation == "integration" else "num_points = 301" in text


def test_controlled_and_convergence_decks(tmp_path):
    paths = deck22.write_decks(config22.load_config(), tmp_path)
    assert {p.name for p in paths} == {
        "abrupt_integration.in", "abrupt_dispersion.in",
        "linear_1nm_integration.in", "linear_1nm_dispersion.in",
        "abrupt_integration_k048.in", "abrupt_integration_k072.in",
    }


def test_overlap_tracker_follows_character_through_energy_crossing():
    # Synthetic arrays are a unit test only; no production analysis path accepts them.
    energy = np.array([[0.0, 1.0], [0.6, 0.4], [1.0, 0.0]])
    vectors = np.array([[[1, 0], [0, 1]], [[1, 0], [0, 1]], [[1, 0], [0, 1]]], float)
    result = state_tracking22.track_states(energy, vectors, ntrack=2)
    assert np.array_equal(result.tracked_raw_indices, np.array([[0, 1], [0, 1], [0, 1]]))


def test_generalized_chi2_reproduces_validated_demo20():
    assert chi2_22.validate_against_demo20() < 1e-9


def test_parser_refuses_filename_index_as_k(tmp_path):
    kp8 = tmp_path / "run" / "kp8"
    kp8.mkdir(parents=True)
    for index in range(2):
        (kp8 / f"energy_spectrum_k{index:03d}.dat").write_text(
            "0 0.1\n1 0.2\n2 1.0\n3 1.1\n", encoding="utf-8")
    with pytest.raises(config22.Demo22Error, match="explicit k vectors"):
        kp8io22.extract_state_grid(tmp_path, tmp_path / "inventory.csv")


def test_professional_gate_rejects_explicit_free_paths(monkeypatch, tmp_path):
    exe = tmp_path / "nextnano++_free.exe"; exe.write_text("x")
    db = tmp_path / "database_free.nnp"; db.write_text("x")
    lic = tmp_path / "License_free.lic"; lic.write_text("x")
    class Machine:
        executable, database, license = exe, db, lic
        run_solver, results_root, source_path, discovery_notes = True, tmp_path, tmp_path / "machine.yaml", ()
    monkeypatch.setattr(run_demo22.demo_workflow, "load_machine_config", lambda _=None: Machine())
    _, record = run_demo22.professional_probe()
    assert record["available"] is False
    assert record["edition"] == "free"
