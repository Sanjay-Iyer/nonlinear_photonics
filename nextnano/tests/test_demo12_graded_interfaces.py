"""Home-laptop tests for Demo 12; no nextnano executable is invoked."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "nextnano" / "demos" / "12_graded_interface_coupled_quantum_well_optimization"
SHARED = DEMO.parent / "_shared"
DEMO11 = DEMO.parent / "11_paper_validation_interband_chi2_acqw"
for path in (str(DEMO), str(SHARED), str(DEMO11)):
    if path not in sys.path:
        sys.path.insert(0, path)

import demo12  # noqa: E402
import demo_workflow  # noqa: E402
import grading12  # noqa: E402
import report12  # noqa: E402
import sweeps  # noqa: E402
import tracking12  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


@pytest.mark.parametrize("shape", ["linear", "sigmoid", "erf", "cosine"])
def test_smooth_profiles_are_monotone_and_preserve_endpoints(shape):
    u = np.linspace(0, 1, 1001)
    values = grading12.profile_fraction(u, shape)
    assert values[0] == pytest.approx(0.0, abs=1e-12)
    assert values[-1] == pytest.approx(1.0, abs=1e-12)
    assert np.all(np.diff(values) >= -1e-14)


def test_linear_composition_generation():
    z = np.linspace(2, 4, 21)
    x = grading12.composition_profile(z, start_nm=2, end_nm=4, start_x=0, end_x=0.55, shape="linear")
    assert x[10] == pytest.approx(0.275)


def test_staircase_approximation_and_endpoints():
    u = np.linspace(0, 1, 101)
    values = grading12.profile_fraction(u, "staircase_linear", staircase_steps=10)
    assert values[0] == 0 and values[-1] == 1
    assert len(np.unique(values)) <= 12


def test_integrated_composition_equal_area_profiles():
    z = np.linspace(0, 2, 10001)
    for shape in ("linear", "sigmoid", "erf", "cosine"):
        x = grading12.composition_profile(z, start_nm=0, end_nm=2, start_x=0, end_x=0.55, shape=shape)
        assert grading12.integrated_composition(z, x) == pytest.approx(0.55, rel=2e-5)


def test_profile_validation_detects_nonmonotone():
    result = grading12.profile_validation([0, 1, 2], [0, 0.7, 0.55], expected_start_x=0, expected_end_x=0.55, direction=1)
    assert not result["monotone"] and not result["passed"]


def test_total_geometry_and_layer_centers_preserved(cfg):
    abrupt = copy.deepcopy(cfg); abrupt["grading"]["selected_thickness_nm"] = 0
    graded = copy.deepcopy(cfg); graded["grading"]["selected_thickness_nm"] = 2
    assert demo12.build_stack(abrupt).total_thickness_nm == demo12.build_stack(graded).total_thickness_nm
    assert demo12.build_stack(abrupt).intervals() == demo12.build_stack(graded).intervals()


def test_mesh_resolution_validation():
    assert grading12.mesh_resolution(1.0, 0.1) == 10
    assert grading12.required_grade_spacing_nm(0.25, 10) == pytest.approx(0.025)


def _grid_point(case_id, a, g, z, e, h, ee=(0.1, 0.2), he=(-0.2, -0.1)):
    return tracking12.GridPoint(case_id, a, g, z, np.asarray(ee), np.asarray(e), np.asarray(he), np.asarray(h))


def test_state_tracking_through_synthetic_avoided_crossing():
    z = np.linspace(-5, 5, 401)
    left = np.exp(-((z + 2) / 0.8) ** 2); right = np.exp(-((z - 2) / 0.8) ** 2)
    left /= np.sqrt(np.trapezoid(left**2, z)); right /= np.sqrt(np.trapezoid(right**2, z))
    points = [
        _grid_point("a", 0.4, 0, z, np.column_stack([left, right]), np.column_stack([left, right])),
        _grid_point("b", 0.4, 1, z, np.column_stack([-right, left]), np.column_stack([-right, left]), ee=(0.15, 0.16)),
    ]
    tracked = tracking12.track_grid(points, {"minimum_confidence": 0.6, "minimum_assignment_margin": 0.15})
    rows = [row for row in tracked["rows"] if row["case_id"] == "b" and row["band"] == "electron"]
    assert any(row["raw_index"] != row["tracked_label"] for row in rows)
    assert any(row["sign_flip_applied"] for row in rows)


def test_arbitrary_sign_alignment_is_not_state_switching():
    import tracking11
    reference = np.eye(3)
    aligned, flips = tracking11.align_signs(reference, -reference, [0, 1, 2])
    assert np.allclose(aligned, reference) and all(flips)


def test_ambiguous_assignment_detection():
    z = np.linspace(0, 1, 101)
    a = np.sin(np.pi * z); b = np.sin(2 * np.pi * z)
    a /= np.sqrt(np.trapezoid(a*a, z)); b /= np.sqrt(np.trapezoid(b*b, z))
    mixed1 = (a+b)/np.sqrt(2); mixed2 = (a-b)/np.sqrt(2)
    points = [_grid_point("a", .4, 0, z, np.column_stack([a,b]), np.column_stack([a,b])),
              _grid_point("b", .4, 1, z, np.column_stack([mixed1,mixed2]), np.column_stack([mixed1,mixed2]))]
    tracked = tracking12.track_grid(points, {"minimum_confidence": .6, "minimum_assignment_margin": .2})
    assert tracked["ambiguous_assignments"] > 0


def test_peak_and_target_optima_are_distinct():
    rows = report12.synthetic_rows()
    assert grading12.optimum(rows, "peak_chi2_magnitude")["case_id"] != grading12.optimum(rows, "chi2_at_target_wavelength")["case_id"]


def test_robustness_finite_difference_calculation():
    metrics = grading12.finite_difference_sensitivity(0.9, 1.0, 1.05, 0.1)
    assert metrics["slope_per_unit"] == pytest.approx(0.75)
    assert metrics["worst_case_change"] == pytest.approx(0.1)


def test_pareto_front_extraction():
    rows = [{"id": "a", "strength": 2, "robustness": 1}, {"id": "b", "strength": 1, "robustness": 2}, {"id": "c", "strength": 1, "robustness": 1}]
    ids = {row["id"] for row in grading12.pareto_front(rows, {"strength": "maximize", "robustness": "maximize"})}
    assert ids == {"a", "b"}


def test_constraint_filter_excludes_quasibound_candidate(cfg):
    result = report12.build_optimization(report12.synthetic_rows(), cfg["optimization"]["constraints"])
    rejected = next(row for row in result["rows"] if row["case_id"] == "synthetic_quasibound")
    assert rejected["constraint_status"] == "violated"
    assert "require_bound_states" in rejected["constraint_failures"]


def test_yaml_validation_and_full_tier_gate(cfg):
    demo12.validate_demo12_config(cfg)
    bad = copy.deepcopy(cfg); bad["execution"].update({"tier": "C", "enable_full_optimization": False})
    with pytest.raises(DemoErrorLike()):
        demo12.validate_demo12_config(bad)


def DemoErrorLike():
    return demo12.DemoError


def test_missing_output_handling_is_explicit(cfg, tmp_path):
    case = demo12.cases_for_tier(cfg)[0]
    result = sweeps.CaseResult(case, tmp_path, "skipped_no_solver", None, 0.0, {}, {}, [], None)
    assert demo12._extract_realized_composition(case, result)["realized_profile_status"] == "not run"


def test_report_generation_from_synthetic_data(cfg, tmp_path):
    report = report12.write_report(tmp_path, cfg, report12.synthetic_rows(), synthetic=True)
    assert report.is_file()
    assert "SYNTHETIC" in report.read_text(encoding="utf-8")
    assert (tmp_path / "optimization_results.csv").is_file()
    assert len(list((tmp_path / "figures").glob("*.png"))) == 24
    assert len(list((tmp_path / "plot_data").glob("*.csv"))) == 24


def test_native_and_staircase_decks_are_distinct(cfg):
    cases = {case.case_id: case for case in demo12.cases_for_tier(cfg)}
    native = demo12.structure_block(cases["v_native"].config, demo12.build_stack(cases["v_native"].config))
    staircase = demo12.structure_block(cases["v_stair"].config, demo12.build_stack(cases["v_stair"].config))
    assert "ternary_linear" in native
    assert "ternary_constant" in staircase


def test_expected_case_counts_and_smoke_manifest(cfg):
    counts = demo12.stage_counts(cfg)
    assert counts == {"by_stage": {"stage1": 4, "stage2": 8, "stage3": 7, "stage4": 8, "stage5": 66, "stage6": 153, "stage7": 0}, "tier_A": 4, "tier_B": 27, "tier_C": 246, "stage7_postprocessing_cases": 0}
    smoke = yaml.safe_load((DEMO / "manifests" / "smoke_test.yaml").read_text(encoding="utf-8"))
    assert smoke["case_count"] == len(smoke["cases"]) <= 5


def test_fine_grade_mesh_lines_are_sorted_and_use_pos(cfg):
    import re
    thin_grade = demo12.build_cases_by_stage(cfg)["stage2"][1].config
    rendered = demo12.render_values(thin_grade)["grid_lines"]
    assert "line{ pos =" in rendered and "line{ x =" not in rendered
    positions = [float(value) for value in re.findall(r"pos = ([0-9.]+)", rendered)]
    assert positions == sorted(positions)


def test_every_plot_has_csv_contract():
    assert len(demo12.PLOT_SET) == 24
    assert all(Path(filename).suffix == ".png" for filename, _ in demo12.PLOT_SET)
