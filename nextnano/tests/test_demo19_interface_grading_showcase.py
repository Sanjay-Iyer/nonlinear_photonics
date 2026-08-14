"""Solver-free tests for Demo 19's fixed grading showcase."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


DEMO = Path(__file__).resolve().parents[1] / "demos" / "19_quantum_well_interface_grading_showcase"
for path in (
    DEMO,
    DEMO.parent / "_shared",
    DEMO.parent / "12_graded_interface_coupled_quantum_well_optimization",
    DEMO.parent / "14_absolute_chi2_graded_acqw_bo",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cases19  # noqa: E402
import demo19  # noqa: E402


def test_case_list_is_exact_and_nonrandom():
    cases = cases19.all_cases()
    assert len(cases) == 13
    assert [case.case_id for case in cases] == [f"{i:02d}" for i in range(13)]
    assert cases[0].case_name == "Abrupt reference"
    assert cases[3].widths_nm == (0.7, 0.7, 0.7, 0.7)
    assert cases[6].widths_nm == (0, 0.4, 0.8, 0)
    assert cases[7].widths_nm == (0, 0.8, 0.4, 0)


def test_fixed_geometry_and_interface_names():
    positions = demo19.interface_positions()
    assert list(positions) == ["I1", "I2", "I3", "I4"]
    assert np.allclose(list(positions.values()), [9.1, 16.2, 18.0, 20.9])
    assert demo19.geometry().domain_nm == (0.0, 30.0)


def test_all_profiles_realize_and_do_not_overlap():
    for case in cases19.all_cases():
        row = demo19.validate_realized(case)
        assert row["validation_pass"], (case.case_id, row)
        assert not row["unintended_overlap"]
        assert row["maximum_composition_error"] <= demo19.PROFILE_TOLERANCE


def test_renderer_uses_only_supported_syntax():
    cfg = demo19.load_config()
    for case in cases19.all_cases():
        _geometry, _profile, blocks, deck = demo19.build_case(cfg, case)
        assert "ternary_pyramid" not in deck
        assert "output_alloy_composition" in deck
        if case.profile == "linear":
            assert deck.count("ternary_linear{") == sum(width > 0 for width in case.widths_nm)
        elif case.profile in {"fermi", "erf", "cosine"}:
            assert "ternary_import{" in deck
            assert blocks["datafile"]
        else:
            assert "ternary_linear{" not in deck


def test_preflight_report_passes_all_thirteen():
    report = demo19.preflight_report()
    assert report["case_count"] == 13
    assert report["all_grading_valid"]
    assert report["all_decks_complete"]
    assert report["overlap_cases"] == []
    assert report["licensed_solver_run"] is False
