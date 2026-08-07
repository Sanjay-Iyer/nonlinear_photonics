"""Focused tests for Demo 16D's incremental fixed-case geometry validation."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

DEMOS = Path(__file__).resolve().parents[1] / "demos"
for relative in (
    "_shared", "11_paper_validation_interband_chi2_acqw",
    "14_absolute_chi2_graded_acqw_bo", "16_acqw_renderer_stress_validation",
    "16B_simple_acqw_grading_validation", "16D_acqw_linear_grading_geometry_validation",
):
    path = str(DEMOS / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

import adapter14  # noqa: E402
import cases16d  # noqa: E402
import demo14  # noqa: E402
import demo16  # noqa: E402
import demo16b  # noqa: E402
import demo16d  # noqa: E402
import run_demo16d  # noqa: E402
import solver14  # noqa: E402
import sweeps  # noqa: E402

CASES_PATH = DEMOS / "16D_acqw_linear_grading_geometry_validation" / "validation_cases.yaml"


@pytest.fixture(scope="module")
def cfg():
    return demo14.load_config()


@pytest.fixture(scope="module")
def cases():
    return cases16d.load_cases(CASES_PATH)


def test_fixed_deterministic_case_list(cases):
    assert [case.case_id for case in cases] == [f"case_{i:02d}" for i in range(1, 8)]
    assert [case.as_record() for case in cases16d.all_cases()] == [case.as_record() for case in cases]


def test_linear_grading_only(cases):
    assert {case.grading_profile for case in cases} == {"linear"}


def test_reference_geometry_is_7_point_1_1_point_8_2_point_9(cases):
    assert cases[0].well_widths_nm() == pytest.approx((7.1, 2.9))
    assert cases[0].central_barrier_nm == pytest.approx(1.8)


def test_thin_and_thick_barrier_cases(cases):
    assert cases[1].central_barrier_nm == pytest.approx(0.85)
    assert cases[2].central_barrier_nm == pytest.approx(2.50)
    assert not cases[1].overlap
    assert not cases[2].overlap


def test_low_and_high_asymmetry_cases(cases):
    assert cases[3].asymmetry_s == pytest.approx(0.30)
    assert cases[3].well_widths_nm() == pytest.approx((6.5, 3.5))
    assert cases[4].asymmetry_s == pytest.approx(0.55)
    assert cases[4].well_widths_nm() == pytest.approx((7.75, 2.25))


def test_total_gaas_well_thickness_remains_10_nm(cases):
    assert all(sum(case.well_widths_nm()) == pytest.approx(10.0) for case in cases)


def test_outer_barriers_and_two_wells_exist(cfg, cases):
    for case in cases:
        _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
        checks = demo16.structural_invariants(
            profile.x_nm, profile.al_fraction,
            profile.request["interfaces_nm"], cases16d.AL_FRACTION,
        )
        assert checks["left_outer_barrier_present"]
        assert checks["right_outer_barrier_present"]
        assert checks["thick_well_is_gaas"]
        assert checks["thin_well_is_gaas"]


def test_intended_profiles_are_bounded(cfg, cases):
    for case in cases:
        _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
        assert np.min(profile.al_fraction) >= -1e-12
        assert np.max(profile.al_fraction) <= 0.55 + 1e-12


def test_exactly_one_overlap_is_detected_and_imported(cfg, cases):
    detected = []
    for case in cases:
        _geometry, profile, blocks, _deck = demo16d.build_case(cfg, case)
        report = demo16d.overlap_geometry(profile, case)
        if report["overlap"]:
            detected.append(case.case_id)
            assert demo16d.render_method(blocks) == "ternary_import"
        else:
            assert demo16d.render_method(blocks) == "ternary_linear"
    assert detected == ["case_07"]


def test_overlap_does_not_fabricate_false_point_55_plateau(cfg, cases):
    case = cases[-1]
    _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
    report = demo16d.overlap_geometry(profile, case)
    assert report["overlap_width_nm"] == pytest.approx(0.90)
    assert report["expected_peak_al_fraction"] < 0.90 * 0.55
    assert not report["reaches_90_percent_of_nominal"]
    assert not report["true_flat_central_plateau_exists"]


def test_local_grading_measurement_never_returns_well_widths(cfg, cases):
    for case in cases:
        _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
        records = demo16d._interface_records(profile.x_nm, profile.al_fraction, profile, case)
        assert all(row["window_isolated_from_other_interfaces"] for row in records)
        widths = [row["realized_width_10_90_nm"] for row in records if row["realized_width_10_90_nm"]]
        assert all(abs(width - 7.1) > 0.4 for width in widths)
        assert all(abs(width - 2.9) > 0.4 for width in widths)


def test_intended_vs_realized_comparison_identity_passes(cfg, cases):
    for case in cases:
        _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
        result = demo16d.compare_compositions(
            profile, case, profile.x_nm.copy(), profile.al_fraction.copy()
        )
        assert result["checks"]["passed"], (case.case_id, result["checks"])
        assert result["max_absolute_al_fraction_difference"] < 1e-12
        assert result["rms_al_fraction_difference"] < 1e-12


def test_realized_geometry_metrics_follow_interface_centres(cfg, cases):
    for case in cases[:-1]:
        _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
        result = demo16d.compare_compositions(profile, case, profile.x_nm, profile.al_fraction)
        geometry = result["geometry"]
        w1, w2 = case.well_widths_nm()
        assert geometry["realized_well_1_nm"] == pytest.approx(w1, abs=0.1)
        assert geometry["realized_central_barrier_nm"] == pytest.approx(case.central_barrier_nm, abs=0.1)
        assert geometry["realized_well_2_nm"] == pytest.approx(w2, abs=0.1)
        assert geometry["realized_total_gaas_well_nm"] == pytest.approx(10.0, abs=0.15)


def test_parser_failure_stops_structure(tmp_path, monkeypatch, cfg, cases):
    structure_calls = []

    def refused(*args, **kwargs):
        return {"passed": False, "return_code": 1, "failure_reason": "bad deck"}

    def structure_must_not_run(*args, **kwargs):
        structure_calls.append(True)

    monkeypatch.setattr(demo16, "parse_deck", refused)
    monkeypatch.setattr(demo16d, "run_structure", structure_must_not_run)
    outcome = demo16d.run_case(
        cfg, cases[0], tmp_path / "case_01", exe=Path("nextnano++.exe"),
        database=None, do_parse=True, do_structure=True,
    )
    assert outcome.status == "parser_failed"
    assert not structure_calls


def test_structure_failure_stops_full_solver(tmp_path, monkeypatch, cases):
    outcomes = [
        demo16d.CaseOutcome(case.case_id, case.name, status="structure_failed",
                            failure_reason="composition mismatch")
        for case in cases16d.physics_cases()
    ]
    for sub in ("summaries", "plots", "cases"):
        (tmp_path / sub).mkdir()
    monkeypatch.setattr(run_demo16d, "_machine_or_none", lambda: SimpleNamespace(run_solver=True))
    monkeypatch.setattr(run_demo16d, "run_levels", lambda **kwargs: (1, tmp_path, outcomes))
    called = []
    monkeypatch.setattr(demo16d, "solve_case", lambda *args, **kwargs: called.append(True))
    assert run_demo16d.run_physics() == 1
    assert not called


def test_solver_failure_stops_optical_analysis(tmp_path, monkeypatch, cases):
    selected = cases16d.physics_cases()
    outcomes = [demo16d.CaseOutcome(c.case_id, c.name, status="structure_passed") for c in selected]
    for sub in ("summaries", "plots", "cases"):
        (tmp_path / sub).mkdir()
    monkeypatch.setattr(
        run_demo16d, "_machine_or_none",
        lambda: SimpleNamespace(run_solver=True, executable="nextnano++.exe", database=None, license=None),
    )
    monkeypatch.setattr(run_demo16d, "run_levels", lambda **kwargs: (0, tmp_path, outcomes))
    monkeypatch.setattr(demo16d, "full_physics_command", lambda *args, **kwargs: ["solver"])
    monkeypatch.setattr(
        demo16d, "solve_case",
        lambda *args, **kwargs: {"case_id": args[1].case_id, "passed": False,
                                 "failure_stage": "solver", "failure_reason": "refused"},
    )
    optical_calls = []
    monkeypatch.setattr(demo16d, "analyse_optics", lambda *args, **kwargs: optical_calls.append(True))
    assert run_demo16d.run_physics() == 1
    assert not optical_calls


def test_missing_quantum_outputs_stop_analysis(tmp_path, monkeypatch, cfg, cases):
    analysed = []
    invocation = solver14.SolverInvocation(
        executable="nextnano++.exe", argv=["nextnano++.exe"],
        working_directory=str(tmp_path), input_path=str(tmp_path / "case.in"),
        input_sha256="test", return_code=0,
    )
    monkeypatch.setattr(demo16b.solver14, "execute_real", lambda **kwargs: invocation)
    monkeypatch.setattr(
        demo16b, "verify_quantum_outputs",
        lambda *args, **kwargs: (_ for _ in ()).throw(demo16b.Demo16BError("missing HH envelopes")),
    )
    monkeypatch.setattr(demo16b, "analyse_physics", lambda *args, **kwargs: analysed.append(True))
    machine = SimpleNamespace(executable="nextnano++.exe", database=None, license=None)
    record = demo16d.solve_case(cfg, cases[0], tmp_path / "case_01", machine=machine)
    assert record["failure_stage"] == "quantum_output_gate"
    assert not analysed


def test_short_physics_output_roots_fit_budget(cases):
    run_root = Path(
        r"C:\code\nonlinear_photonics\nextnano\results\demo_runs"
        r"\16D_acqw_linear_grading_geometry_validation"
        r"\demo16d_20260807T201711Z_3f837abc_c90082"
    )
    expected = {"case_01": "p01", "case_02": "p02", "case_05": "p05", "case_07": "p07"}
    for case in cases16d.physics_cases():
        raw = demo16d.physics_raw_output_dir(run_root / "cases" / case.case_id, case)
        assert raw.name == expected[case.case_id]
        assert sweeps.check_path_budget(raw) is None


def test_exactly_four_physics_cases_selected():
    assert [case.case_id for case in cases16d.physics_cases()] == [
        "case_01", "case_02", "case_05", "case_07"
    ]


def test_full_solver_command_is_not_parse_or_structure(cfg, cases):
    machine = SimpleNamespace(
        executable=Path(r"C:\nextnano\nextnano++_Intel_64bit.exe"),
        database=Path(r"C:\nextnano\database.nnp"), license=Path(r"C:\nextnano\license.lic"),
    )
    case_dir = Path(r"C:\work\run\cases\case_01")
    command = demo16d.full_physics_command(cfg, cases[0], case_dir, machine=machine)
    assert command == solver14.real_argv(
        executable=machine.executable, database=machine.database,
        license_path=machine.license,
        deck=case_dir / "physics" / "nextnano_input" / "case.in",
        output_dir=Path(r"C:\work\run\p01"), threads=1,
    )
    assert "--parse" not in command and "--structure" not in command


def test_full_physics_decks_request_all_required_quantum_outputs(cfg, cases):
    for case in cases16d.physics_cases():
        _geometry, _profile, _blocks, deck = demo16d.build_case(cfg, case)
        compact = " ".join(deck.split())
        for marker in (
            "output_bandedges", "Gamma{ num_ev", "HH{ num_ev", "output_states{",
            "envelopes = yes", "probabilities = yes", "run{ quantum{} }",
        ):
            assert marker in compact


def test_optical_config_reuses_absolute_demo14_demo11_pipeline(cfg, cases):
    geometry, profile, _blocks, _deck = demo16d.build_case(cfg, cases[0])
    derived = adapter14.build_demo11_analysis_config_from_demo14(cfg, geometry, profile)
    assert derived["metric"]["mode"] == "absolute"
    assert derived["metric"]["reference_wavelength_nm"] == 1550.0
    assert derived["metric"]["focused_wavelength_nm"] == [1400.0, 1800.0]
    assert derived["metric"]["broadening_meV"] == pytest.approx(5.0)
    assert derived["metric"]["max_states_per_band"] == 2


def test_analyse_optics_uses_exact_1550_value_and_signed_detuning(tmp_path, monkeypatch, cfg, cases):
    def production(cfg_arg, layout, geometry, profile):
        parsed = Path(layout["parsed"])
        parsed.mkdir(parents=True, exist_ok=True)
        wavelengths = np.array([1500.0, 1550.0, 1600.0])
        magnitude = np.array([1.0, 3.0, 2.0])
        np.savetxt(
            parsed / "chi2_focused.csv",
            np.column_stack([wavelengths, magnitude, np.zeros(3), magnitude]),
            delimiter=",", header="wavelength_nm,chi2_real,chi2_imag,chi2_magnitude", comments="",
        )
        (parsed / "chi2_settings.json").write_text("{}", encoding="utf-8")
        (parsed / "state_count_audit.json").write_text("{}", encoding="utf-8")
        return {"chi2_relative_at_reference": 3.0, "chi2_units": "pm/V"}

    monkeypatch.setattr(demo14, "analyse_real_trial", production)
    result = demo16d.analyse_optics(cfg, cases[0], tmp_path / "case_01", tmp_path / "p01")
    assert result["chi2_at_1550"] == pytest.approx(3.0)
    assert result["spectral_peak_wavelength_nm"] == pytest.approx(1550.0)
    assert result["detuning_from_1550_nm"] == pytest.approx(0.0)
    assert result["chi2_units"] == "pm/V"


def test_analyze_existing_never_calls_solver(tmp_path, monkeypatch):
    runlog = {
        "run_id": "demo16d_test", "cases_passed": 7,
        "cases_total": 7, "cases": [],
    }
    (tmp_path / "summary.json").write_text(json.dumps(runlog), encoding="utf-8")
    monkeypatch.setattr(
        demo16d, "solve_case",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("solver called")),
    )
    assert run_demo16d.analyze_existing(tmp_path) == 0


def test_demo_runs_path_cannot_be_duplicated(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_demo16d, "_machine_or_none",
        lambda: SimpleNamespace(results_root=tmp_path / "demo_runs"),
    )
    root = run_demo16d.results_root() / demo16d.DEMO_ID
    assert list(root.parts).count("demo_runs") == 1
    assert not [a for a, b in zip(root.parts, root.parts[1:]) if a == b]
