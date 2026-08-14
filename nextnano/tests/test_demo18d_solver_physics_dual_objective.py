from __future__ import annotations

import csv
from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
DEMOS = ROOT / "nextnano" / "demos"
DEMO = DEMOS / "18D_solver_physics_dual_objective_reproduction"
for dependency in (
    DEMO, DEMOS / "18C_paper_missing_parameter_ensemble",
    DEMOS / "18B_absolute_chi2_reproduction_audit",
    DEMOS / "18_absolute_chi2_scale_audit", DEMOS / "16F_paper_absolute_chi2_reproduction_audit",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "16_acqw_renderer_stress_validation", DEMOS / "14_absolute_chi2_graded_acqw_bo",
    DEMOS / "11_paper_validation_interband_chi2_acqw", DEMOS / "_shared",
):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import analysis18d
import cases18d
import config18d
import run_demo18d


def test_frozen_design_is_20_unique_real_solver_cases() -> None:
    rows = config18d.load_cases()
    assert rows == cases18d.generate_cases(1804)
    assert len(rows) == len({row.solver_key() for row in rows}) == 20
    assert all(row.requires_licensed_solve for row in rows)


def test_forbidden_postprocessing_knobs_are_fixed() -> None:
    for row in config18d.load_cases():
        assert row.hh_relative_weight == 1.0
        assert row.spin_degeneracy == 2
        assert row.wells_per_period_for_Nz == 2
        assert row.r_e_hh_primary_nm == 0.751


def test_anchor_selection_records_physical_18c_cases() -> None:
    anchors = [row.source_18c_combo_id for row in config18d.load_cases()[1:5]]
    assert anchors == ["Combo_07", "Combo_18", "Combo_01", "Combo_02"]


@pytest.mark.parametrize("case_id", ["Case_00", "Case_01", "Case_02", "Case_19"])
def test_decks_inherit_converged_abrupt_quantum_only_physics(case_id: str) -> None:
    cfg = config18d.load_config()
    case = next(row for row in config18d.load_cases() if row.case_id == case_id)
    solver_cfg, _rendered, geometry, _profile, blocks, deck = run_demo18d.build_case(cfg, case)
    compact = " ".join(deck.split())
    assert "no_density = yes" in compact and "run{ quantum{} }" in compact
    assert "poisson{ electric_field{" in compact
    assert "ternary_linear{" not in blocks["structure_block"]
    assert solver_cfg["mesh"]["active_region_grid_spacing_nm"] == 0.025
    assert solver_cfg["geometry"]["domain_padding_nm"] == 60.0
    assert geometry.thick_well_nm + geometry.thin_well_nm + geometry.barrier_nm \
        + solver_cfg["geometry"]["period_barrier_nm"] == pytest.approx(30.0)


def test_local_peak_detection_finds_both_competing_features() -> None:
    wavelength = np.arange(1400.0, 1801.0)
    magnitude = np.exp(-((wavelength - 1520) / 5) ** 2) + 2 * np.exp(-((wavelength - 1663) / 6) ** 2)
    peaks = analysis18d._local_peaks(wavelength, magnitude)
    assert peaks[0][0] == 1663.0
    assert peaks[1][0] == 1520.0


def test_dual_score_penalizes_the_1663_amplitude_only_match() -> None:
    rows = [
        {"case_id": "amplitude", "physical_valid": True, "spectral_window_pass": False,
         "combined_score": np.hypot(.03, 103 / 40)},
        {"case_id": "physical", "physical_valid": True, "spectral_window_pass": True,
         "combined_score": 0.50},
    ]
    assert [row["case_id"] for row in analysis18d.rank(rows)] == ["physical", "amplitude"]


def test_outcome_requires_correct_spectral_window() -> None:
    amplitude_only = [{"spectral_window_pass": False, "amplitude_relative_error": .01,
                       "chi2_1550_pm_per_V": 2340.0}]
    assert analysis18d.outcome(amplitude_only)["outcome"] == "A"
    physical = [{"spectral_window_pass": True, "amplitude_relative_error": .09,
                 "chi2_1550_pm_per_V": 2300.0}]
    assert analysis18d.outcome(physical)["outcome"] == "E"


def test_csv_headers_are_case_insensitive_unique() -> None:
    for name in ("demo18d_parameter_ranges.csv", "demo18d_combinations.csv"):
        with (DEMO / name).open("r", encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream))
        assert len(header) == len({key.casefold() for key in header})


def test_cli_and_pyexpat_preload() -> None:
    with pytest.raises(run_demo18d.Runner18DError):
        run_demo18d._validate_cli(19, 1804)
    source = (DEMO / "run_demo18d.py").read_text(encoding="utf-8")
    assert source.index("import pyexpat") < source.index("import numpy as np")


def test_archived_18c_config_is_bridged_to_demo18b_audit_schema() -> None:
    old_cfg = {
        "bound_state_criteria": {"minimum_binding_energy_meV": 7.0},
        "chi2": {"k_points": 768},
    }
    bridged = run_demo18d._audit_config_for_18c(old_cfg)
    assert bridged["chi2"]["primary_k_points"] == 384
    assert bridged["bound_state_criteria"]["minimum_binding_energy_meV"] == 7.0


def test_combinations_hash_is_independent_of_windows_line_endings(tmp_path: Path) -> None:
    lf = tmp_path / "lf.csv"
    crlf = tmp_path / "crlf.csv"
    lf.write_bytes(b"a,b\n1,2\n")
    crlf.write_bytes(b"a,b\r\n1,2\r\n")
    assert cases18d.combinations_sha256(lf) == cases18d.combinations_sha256(crlf)
