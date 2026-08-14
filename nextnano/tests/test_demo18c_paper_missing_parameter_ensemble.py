from __future__ import annotations

import csv
from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
DEMOS = ROOT / "nextnano" / "demos"
DEMO = DEMOS / "18C_paper_missing_parameter_ensemble"
for dependency in (
    DEMO, DEMOS / "_shared", DEMOS / "11_paper_validation_interband_chi2_acqw",
    DEMOS / "14_absolute_chi2_graded_acqw_bo", DEMOS / "16_acqw_renderer_stress_validation",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
    DEMOS / "16F_paper_absolute_chi2_reproduction_audit",
    DEMOS / "18_absolute_chi2_scale_audit",
    DEMOS / "18B_absolute_chi2_reproduction_audit",
):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import analysis18c
import audit18b
import cases18c
import config18c
import run_demo18c


def test_frozen_design_has_exactly_20_rows_and_17_solves() -> None:
    generated = cases18c.generate_combinations(1803)
    checked_in = config18c.load_combinations()
    assert generated == checked_in
    assert len(checked_in) == 20
    assert len(config18c.unique_solver_combinations(checked_in)) == 17
    assert sum(row.wells_per_period_for_Nz == 2 for row in checked_in) == 16
    assert sum(row.spin_degeneracy == 2 for row in checked_in) == 16


def test_material_model_scales_are_explicitly_fixed() -> None:
    for row in config18c.load_combinations():
        assert row.electron_mass_scale == 1.0
        assert row.hh_mass_scale == 1.0
        assert row.cb_offset_scale == 1.0
        assert row.hh_offset_scale == 1.0


@pytest.mark.parametrize("combo_id", ["Combo_00", "Combo_01", "Combo_08", "Combo_18"])
def test_decks_are_abrupt_field_tilted_and_keep_30_nm_period(combo_id: str) -> None:
    cfg = config18c.load_config()
    combo = next(row for row in config18c.load_combinations() if row.combo_id == combo_id)
    solver_cfg, _case, geometry, _profile, blocks, deck = run_demo18c.build_case(cfg, combo)
    compact = " ".join(deck.split())
    assert "poisson{ electric_field{" in compact
    assert "run{ quantum{} }" in compact
    assert "no_density = yes" in compact
    assert "ternary_linear{" not in blocks["structure_block"]
    assert solver_cfg["mesh"]["active_region_grid_spacing_nm"] == 0.025
    assert solver_cfg["geometry"]["domain_padding_nm"] == 60.0
    assert solver_cfg["geometry"]["quantum_region_padding_nm"] == 42.0
    period = (geometry.thick_well_nm + geometry.thin_well_nm + geometry.barrier_nm
              + solver_cfg["geometry"]["period_barrier_nm"])
    assert period == pytest.approx(30.0)


def test_diagnostic_weight_combines_complete_complex_branches() -> None:
    cfg = config18c.load_config()
    cfg["chi2"] = dict(cfg["chi2"])
    cfg["chi2"].update({"wavelength_start_nm": 1550.0, "wavelength_stop_nm": 1552.0,
                         "wavelength_points": 3, "k_points": 16})
    z = np.linspace(0.0, 10.0, 1001)
    psi1 = np.sqrt(2.0 / 10.0) * np.sin(np.pi * z / 10.0)
    psi2 = np.sqrt(2.0 / 10.0) * np.sin(2.0 * np.pi * z / 10.0)
    electron = audit18b.production_chi2.BandStates(
        z, np.asarray([2.95, 3.08]), np.column_stack((psi1, psi2)), "e"
    )
    hh = audit18b.production_chi2.BandStates(
        z, np.asarray([1.45, 1.38]), np.column_stack((psi1, psi2)), "hh"
    )
    combo = next(row for row in config18c.load_combinations() if row.combo_id == "Combo_16")
    spectrum = analysis18c.branch_spectrum(cfg, combo, electron, hh)
    assert np.allclose(
        spectrum["chi_total"],
        spectrum["chi_e"] + combo.hh_relative_weight * spectrum["chi_hh_raw"],
    )


def test_required_csv_headers_are_unique_case_insensitively() -> None:
    for name in ("demo18c_parameter_ranges.csv", "demo18c_combinations.csv"):
        with (DEMO / name).open("r", encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream))
        assert len(header) == len({value.casefold() for value in header})


def test_failed_cases_are_not_ranked() -> None:
    rows = [
        {"combo_id": "ok", "physical_valid": True, "percent_error": 5.0},
        {"combo_id": "failed", "physical_valid": False, "percent_error": 0.0},
    ]
    ranked = analysis18c.rank_valid(rows)
    assert [row["combo_id"] for row in ranked] == ["ok"]


def test_cli_rejects_any_non_frozen_ensemble() -> None:
    with pytest.raises(run_demo18c.Runner18CError):
        run_demo18c._validate_cli(19, 1803)
    with pytest.raises(run_demo18c.Runner18CError):
        run_demo18c._validate_cli(20, 7)


def test_plotting_is_lazy_and_reports_environment_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    source = (DEMO / "run_demo18c.py").read_text(encoding="utf-8")
    assert "\nimport plots18c\n" not in source
    assert source.index("import pyexpat") < source.index("import numpy as np")

    def broken_import(name: str):
        assert name == "plots18c"
        raise ImportError("DLL load failed while importing pyexpat")

    monkeypatch.setattr(run_demo18c.importlib, "import_module", broken_import)
    with pytest.raises(run_demo18c.Runner18CError, match="licensed physics was not started"):
        run_demo18c._load_plots18c()
