"""Focused tests for Demo 16C's one-question grading experiment."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

DEMOS = Path(__file__).resolve().parents[1] / "demos"
for relative in (
    "_shared",
    "11_paper_validation_interband_chi2_acqw",
    "14_absolute_chi2_graded_acqw_bo",
    "16_acqw_renderer_stress_validation",
    "16B_simple_acqw_grading_validation",
    "16C_minimal_linear_grading_validation",
):
    path = str(DEMOS / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

import cases16c  # noqa: E402
import demo14  # noqa: E402
import demo16  # noqa: E402
import demo16b  # noqa: E402
import demo16c  # noqa: E402
import run_demo16c  # noqa: E402

CASES_PATH = DEMOS / "16C_minimal_linear_grading_validation" / "validation_cases.yaml"


@pytest.fixture(scope="module")
def cfg():
    return demo14.load_config()


@pytest.fixture(scope="module")
def cases():
    return cases16c.load_cases(CASES_PATH)


def test_exactly_four_fixed_cases(cases):
    assert len(cases) == 4
    assert [c.case_id for c in cases] == ["case_01", "case_02", "case_03", "case_04"]


def test_case_list_is_deterministic(cases):
    assert [c.as_record() for c in cases16c.all_cases()] == [c.as_record() for c in cases]
    assert [c.as_record() for c in cases16c.all_cases()] == [
        c.as_record() for c in cases16c.all_cases()
    ]


def test_linear_grading_only(cases):
    assert {c.grading_profile for c in cases} == {"linear"}


def test_fixed_paper_geometry(cases):
    for case in cases:
        assert np.allclose(case.well_widths_nm(), (7.1, 2.9))
        assert case.nominal_central_barrier_thickness_nm == 1.8
        assert case.asymmetry_s == pytest.approx(0.42)


def test_only_grading_widths_vary(cases):
    records = [c.parameters() for c in cases]
    varying = {key for key in records[0]
               if len({record[key] for record in records}) > 1}
    assert varying == {
        "gaas_to_algaas_grading_width_10_90_nm",
        "algaas_to_gaas_grading_width_10_90_nm",
    }


def test_expected_profiles_stay_between_zero_and_point_55(cfg, cases):
    for case in cases:
        _g, profile, _b, _d = demo16c.build_case(cfg, case)
        assert profile.al_fraction.min() >= -1e-9
        assert profile.al_fraction.max() <= 0.55 + 1e-9


def _central_widths(cfg, case):
    _g, profile, _b, _d = demo16c.build_case(cfg, case)
    metrics = demo16.measure_interfaces(
        profile.x_nm, profile.al_fraction, profile.request["interfaces_nm"],
        demo16c.interface_widths(case), cases16c.AL_FRACTION,
    )
    by_name = {m.name: m for m in metrics}
    return (by_name[demo16c.INTERFACE_LEFT], by_name[demo16c.INTERFACE_RIGHT])


def test_sharper_request_produces_sharper_intended_profile(cfg, cases):
    sharp = _central_widths(cfg, cases[0])
    medium = _central_widths(cfg, cases[1])
    assert all(a.realized_width_10_90_nm < b.realized_width_10_90_nm
               for a, b in zip(sharp, medium))


def test_wider_request_produces_wider_intended_profile(cfg, cases):
    medium = _central_widths(cfg, cases[1])
    wide = _central_widths(cfg, cases[2])
    assert all(a.realized_width_10_90_nm < b.realized_width_10_90_nm
               for a, b in zip(medium, wide))


def test_asymmetric_case_has_independent_widths(cases):
    case = cases[3]
    assert case.left_grading_width_nm == 0.40
    assert case.right_grading_width_nm == 1.00
    assert not case.is_symmetric()


def test_outer_barriers_exist(cfg, cases):
    for case in cases:
        _g, profile, _b, _d = demo16c.build_case(cfg, case)
        checks = demo16.structural_invariants(
            profile.x_nm, profile.al_fraction,
            profile.request["interfaces_nm"], cases16c.AL_FRACTION,
        )
        assert checks["left_outer_barrier_present"]
        assert checks["right_outer_barrier_present"]


def test_two_gaas_wells_exist(cfg, cases):
    for case in cases:
        _g, profile, _b, _d = demo16c.build_case(cfg, case)
        checks = demo16.structural_invariants(
            profile.x_nm, profile.al_fraction,
            profile.request["interfaces_nm"], cases16c.AL_FRACTION,
        )
        assert checks["thick_well_is_gaas"] and checks["thin_well_is_gaas"]


def test_grading_width_finder_remains_local(cfg, cases):
    for case in cases:
        assert all(metric.window_isolated for metric in _central_widths(cfg, case))
        _g, profile, blocks, _d = demo16c.build_case(cfg, case)
        report = demo16b.grading_regions_report(profile, blocks)
        assert report["graded_region_count"] == 4
        assert report["all_four_interfaces_graded"]
        assert report["graded_regions_disjoint"]


def test_7_point_1_nm_is_not_returned_as_a_grading_width(cfg, cases):
    for case in cases:
        assert all(abs(metric.realized_width_10_90_nm - 7.1) > 0.4
                   for metric in _central_widths(cfg, case))


def test_2_point_9_nm_is_not_returned_as_a_grading_width(cfg, cases):
    for case in cases:
        assert all(abs(metric.realized_width_10_90_nm - 2.9) > 0.4
                   for metric in _central_widths(cfg, case))


def test_parser_failure_stops_before_structure(tmp_path, monkeypatch, cfg, cases):
    calls = []

    def refused(*args, **kwargs):
        calls.append(kwargs.get("runmode", "--parse"))
        return {"passed": False, "return_code": 1, "failure_reason": "bad deck"}

    monkeypatch.setattr(demo16, "parse_deck", refused)
    outcome = demo16c.run_case(
        cfg, cases[0], tmp_path / "case_01",
        exe=Path("nextnano++.exe"), database=None,
        do_parse=True, do_structure=True,
    )
    assert outcome.status == "parser_failed"
    assert calls == ["--parse"]
    assert not outcome.structure


def test_solver_failure_stops_analysis(tmp_path, monkeypatch, cfg, cases):
    analysed = []

    def failed_solver(**kwargs):
        raise RuntimeError("solver refused")

    def analysis_must_not_run(*args, **kwargs):
        analysed.append(True)
        raise AssertionError("analysis ran after solver failure")

    monkeypatch.setattr(demo16b.solver14, "execute_real", failed_solver)
    monkeypatch.setattr(demo16b, "analyse_physics", analysis_must_not_run)
    machine = SimpleNamespace(executable="nextnano++.exe", database=None, license=None)
    record = demo16c.solve_case(cfg, cases[0], tmp_path / "case_01", machine=machine)
    assert not record["passed"]
    assert record["failure_stage"] == "solver"
    assert not analysed


def test_intended_vs_realized_comparison_works(cfg, cases):
    case = cases[3]
    _g, profile, _b, _d = demo16c.build_case(cfg, case)
    result = demo16c.compare_compositions(
        profile, case, profile.x_nm.copy(), profile.al_fraction.copy()
    )
    assert result["checks"]["passed"]
    assert result["max_absolute_al_fraction_difference"] < 1e-12
    assert result["realized_left_10_90_grading_width_nm"] == pytest.approx(0.4)
    assert result["realized_right_10_90_grading_width_nm"] == pytest.approx(1.0)


def test_duplicate_demo_runs_path_cannot_occur(monkeypatch, tmp_path):
    fake = SimpleNamespace(results_root=tmp_path / "demo_runs")
    monkeypatch.setattr(run_demo16c, "_machine_or_none", lambda: fake)
    root = run_demo16c.results_root() / demo16c.DEMO_ID
    assert list(root.parts).count("demo_runs") == 1
    assert not [a for a, b in zip(root.parts, root.parts[1:]) if a == b]
