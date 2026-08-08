"""Focused tests for Demo 16E's ten-structure physics and optical comparison."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

DEMOS = Path(__file__).resolve().parents[1] / "demos"
for relative in (
    "_shared", "11_paper_validation_interband_chi2_acqw",
    "14_absolute_chi2_graded_acqw_bo", "16_acqw_renderer_stress_validation",
    "16B_simple_acqw_grading_validation",
    "16E_acqw_structure_physics_optical_comparison",
):
    path = str(DEMOS / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

import adapter14  # noqa: E402
import cases16e  # noqa: E402
import demo14  # noqa: E402
import demo16  # noqa: E402
import demo16b  # noqa: E402
import demo16e  # noqa: E402
import grading14  # noqa: E402
import run_demo16e  # noqa: E402
import runlog14  # noqa: E402
import solver14  # noqa: E402
import sweeps  # noqa: E402

DEMO_DIR = DEMOS / "16E_acqw_structure_physics_optical_comparison"
CASES_PATH = DEMO_DIR / cases16e.CASES_FILENAME


@pytest.fixture(scope="module")
def cfg():
    return demo14.load_config()


@pytest.fixture(scope="module")
def cases():
    return cases16e.load_cases(CASES_PATH)


# ---------------------------------------------------------------------------
# The fixed case matrix
# ---------------------------------------------------------------------------


def test_ten_fixed_deterministic_cases(cases):
    assert [case.case_id for case in cases] == [f"case_{i:02d}" for i in range(1, 11)]
    assert [case.as_record() for case in cases16e.all_cases()] == [
        case.as_record() for case in cases
    ]


def test_case_matrix_is_the_intended_one(cases):
    expected = {
        "case_01": (7.10, 1.80, 2.90, 0.70, 0.70, "native_linear"),
        "case_02": (7.10, 1.80, 2.90, 0.00, 0.00, "abrupt"),
        "case_03": (7.10, 0.85, 2.90, 0.40, 0.40, "native_linear"),
        "case_04": (7.10, 2.50, 2.90, 0.70, 0.70, "native_linear"),
        "case_05": (6.50, 1.80, 3.50, 0.70, 0.70, "native_linear"),
        "case_06": (7.75, 1.80, 2.25, 0.70, 0.70, "native_linear"),
        "case_07": (7.10, 2.50, 2.90, 0.40, 1.40, "native_linear"),
        "case_08": (7.10, 0.85, 2.90, 1.40, 1.40, "imported_profile"),
        "case_09": (7.10, 1.80, 2.90, 1.00, 1.00, "native_linear"),
        "case_10": (7.10, 1.80, 2.90, 1.00, 1.00, "imported_profile"),
    }
    for case in cases:
        w1, barrier, w2, left, right, representation = expected[case.case_id]
        assert case.well_widths_nm() == pytest.approx((w1, w2))
        assert case.central_barrier_nm == pytest.approx(barrier)
        assert case.left_grading_width_nm == pytest.approx(left)
        assert case.right_grading_width_nm == pytest.approx(right)
        assert case.expected_representation == representation


def test_total_gaas_well_thickness_remains_10_nm(cases):
    assert all(sum(case.well_widths_nm()) == pytest.approx(10.0) for case in cases)


def test_linear_grading_only_and_one_overlap(cases):
    assert {case.grading_profile for case in cases} == {"linear"}
    assert [case.case_id for case in cases if case.overlap] == ["case_08"]
    assert [case.case_id for case in cases if case.is_abrupt] == ["case_02"]


def test_case_list_rejects_a_second_overlap():
    broken = list(cases16e.all_cases())
    broken[2] = cases16e.GeometryCase(
        "case_03", "thin_barrier", "forced overlap", cases16e.PAPER_ASYMMETRY,
        0.85, 1.40, 1.40, overlap=True,
    )
    with pytest.raises(cases16e.Cases16EError):
        cases16e.validate_cases(broken)


def test_abrupt_case_must_declare_zero_grading_width():
    broken = list(cases16e.all_cases())
    broken[1] = cases16e.GeometryCase(
        "case_02", "abrupt_reference", "bad", cases16e.PAPER_ASYMMETRY,
        1.80, 0.70, 0.70, interface_mode="abrupt",
    )
    with pytest.raises(cases16e.Cases16EError):
        cases16e.validate_cases(broken)


# ---------------------------------------------------------------------------
# Representations
# ---------------------------------------------------------------------------


def test_every_case_renders_the_declared_representation(cfg, cases):
    seen = {}
    for case in cases:
        _geometry, _profile, blocks, _deck = demo16e.build_case(cfg, case)
        realized = demo16e.representation_of(blocks, case)
        assert realized == case.expected_representation, case.case_id
        seen.setdefault(realized, []).append(case.case_id)
    assert seen["abrupt"] == ["case_02"]
    assert seen["imported_profile"] == ["case_08", "case_10"]
    assert len(seen["native_linear"]) == 7


def test_abrupt_deck_contains_no_grading_ramps(cfg, cases):
    case = cases[1]
    _geometry, _profile, blocks, deck = demo16e.build_case(cfg, case)
    statements = "\n".join(
        line for line in deck.splitlines() if not line.lstrip().startswith("#")
    )
    assert "ternary_linear" not in statements
    assert "ternary_import" not in statements
    assert statements.count('binary{ name = "GaAs" }') == 2
    assert not blocks["datafile"] and not blocks["import_block"]
    assert len(blocks["regions"]) == 2


def test_abrupt_well_regions_are_the_production_layer_edges(cfg, cases):
    case = cases[1]
    geometry, profile, blocks, _deck = demo16e.build_case(cfg, case)
    interfaces = profile.request["interfaces_nm"]
    spans = [tuple(region["x"]) for region in blocks["regions"]]
    assert spans[0] == pytest.approx((
        interfaces["outer_left_algaas_to_gaas"], interfaces["central_gaas_to_algaas"]
    ))
    assert spans[1] == pytest.approx((
        interfaces["central_algaas_to_gaas"], interfaces["outer_right_gaas_to_algaas"]
    ))
    assert spans[0][1] - spans[0][0] == pytest.approx(geometry.thick_well_nm)
    assert spans[1][1] - spans[1][0] == pytest.approx(geometry.thin_well_nm)


def test_abrupt_profile_is_a_step_at_solver_cell_centres(cfg, cases):
    case = cases[1]
    geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
    centres = np.arange(0.0, geometry.domain_nm[1], cases16e.MESH_NM) + 0.5 * cases16e.MESH_NM
    values = demo16b.intended_on(profile, centres)
    assert set(np.unique(np.round(values, 9))) == {0.0, cases16e.AL_FRACTION}


def test_abrupt_and_graded_pair_share_one_layer_geometry(cfg, cases):
    graded_id, abrupt_id = cases16e.abrupt_vs_graded_pair()
    by_id = {case.case_id: case for case in cases}
    geometries = {}
    for case_id in (graded_id, abrupt_id):
        geometry, _profile, _blocks, _deck = demo16e.build_case(cfg, by_id[case_id])
        geometries[case_id] = geometry.as_record()
    assert geometries[graded_id] == geometries[abrupt_id]


def test_overlap_case_imports_and_never_fabricates_a_plateau(cfg, cases):
    case = next(case for case in cases if case.overlap)
    _geometry, profile, blocks, _deck = demo16e.build_case(cfg, case)
    report = demo16e.overlap_geometry(profile, case)
    assert demo16e.render_method(blocks) == "ternary_import"
    assert report["overlap_width_nm"] == pytest.approx(0.90)
    assert report["expected_peak_al_fraction"] < 0.90 * cases16e.AL_FRACTION
    assert not report["true_flat_central_plateau_exists"]


def test_equivalence_pair_is_one_profile_two_encodings(cfg, cases):
    native_id, imported_id = cases16e.equivalence_pair()
    by_id = {case.case_id: case for case in cases}
    built = {}
    for case_id in (native_id, imported_id):
        _geometry, profile, blocks, deck = demo16e.build_case(cfg, by_id[case_id])
        built[case_id] = (profile, blocks, deck)
    difference = demo16e.composition_difference(
        built[native_id][0], built[imported_id][0]
    )
    assert difference["max_abs_xAl_difference"] == 0.0
    assert difference["rms_xAl_difference"] == 0.0
    assert demo16e.render_method(built[native_id][1]) == "ternary_linear"
    assert demo16e.render_method(built[imported_id][1]) == "ternary_import"
    assert built[native_id][2] != built[imported_id][2]


def test_imported_table_contains_every_mesh_sample_and_every_breakpoint(cfg, cases):
    case = next(case for case in cases if case.render_request == "imported")
    _geometry, profile, blocks, _deck = demo16e.build_case(cfg, case)
    table = np.array(
        [[float(v) for v in line.split()]
         for line in blocks["datafile"].strip().splitlines()],
        dtype=float,
    )
    positions = table[:, 0]
    assert np.all(np.diff(positions) > 0)
    for sample in profile.x_nm:
        assert np.min(np.abs(positions - sample)) <= 1e-6
    knots = profile.request["breakpoints_nm"]
    assert len(knots) == 8
    for knot in knots:
        assert np.min(np.abs(positions - knot)) <= 1e-6
    assert table.shape[0] == profile.x_nm.size + len(knots)


def test_imported_table_reproduces_the_analytic_profile_where_the_solver_reads_it(
    cfg, cases
):
    """The defect this guards: a table sampled only on the mesh cuts every corner.

    nextnano++ interpolates the table linearly, so a knot sitting half a mesh
    cell from the nearest row was reproduced with an error of d(h-d)/h times the
    slope change -- 5.5e-3 in Al fraction for the 1.00 nm grades of case_10, an
    order above the composition tolerance, while native case_09 was exact.
    """

    native_id, imported_id = cases16e.equivalence_pair()
    by_id = {case.case_id: case for case in cases}
    _geometry, native_profile, _blocks, _deck = demo16e.build_case(
        cfg, by_id[native_id]
    )
    _geometry, _profile, blocks, _deck = demo16e.build_case(cfg, by_id[imported_id])
    table = np.array(
        [[float(v) for v in line.split()]
         for line in blocks["datafile"].strip().splitlines()],
        dtype=float,
    )
    domain_end = float(native_profile.request["domain_nm"][1])
    centres = np.arange(0.0, domain_end, cases16e.MESH_NM) + 0.5 * cases16e.MESH_NM
    centres = centres[(centres >= table[0, 0]) & (centres <= table[-1, 0])]
    residual = np.interp(centres, table[:, 0], table[:, 1]) - demo16b.intended_on(
        native_profile, centres
    )
    assert np.max(np.abs(residual)) <= 1e-9
    assert np.sqrt(np.mean(residual**2)) <= 1e-9


def test_overlap_case_keeps_the_untouched_production_import(cfg, cases):
    """case_08 exercises production's automatic fallback and must not be altered."""

    case = next(case for case in cases if case.overlap)
    _geometry, profile, blocks, _deck = demo16e.build_case(cfg, case)
    assert blocks["datafile"] == grading14.import_datafile(profile)
    table = np.array(
        [[float(v) for v in line.split()]
         for line in blocks["datafile"].strip().splitlines()],
        dtype=float,
    )
    assert table.shape[0] == profile.x_nm.size
    assert np.max(np.abs(table[:, 0] - profile.x_nm)) <= 1e-6


def test_default_importer_output_is_unchanged(cfg, cases):
    """Demos 13, 14 and 17 must keep emitting exactly the tables they recorded."""

    for case in cases:
        _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
        legacy = "".join(
            f"{x:.6f} {y:.8f}\n"
            for x, y in zip(np.asarray(profile.x_nm, dtype=float),
                            np.asarray(profile.al_fraction, dtype=float))
        )
        assert grading14.import_datafile(profile) == legacy, case.case_id


def test_breakpoints_are_recorded_only_for_compact_support_families(cfg):
    recorded = {}
    for family in ("linear", "fermi", "erf", "cosine"):
        parameters = {
            "asymmetry_s": 0.42,
            "nominal_central_barrier_thickness_nm": 1.80,
            "gaas_to_algaas_grading_width_10_90_nm": 1.00,
            "algaas_to_gaas_grading_width_10_90_nm": 1.00,
            "grading_profile": family,
        }
        geometry = demo14.geometry_for(cfg, parameters)
        profile = demo14.build_grading(cfg, parameters, geometry)
        recorded[family] = profile.request.get("breakpoints_nm")
    assert len(recorded["linear"]) == 8
    assert len(recorded["cosine"]) == 8
    assert recorded["fermi"] is None
    assert recorded["erf"] is None


def test_imported_rendering_comes_from_production_grading14(cfg, cases):
    case = next(case for case in cases if case.render_request == "imported")
    _geometry, profile, blocks, _deck = demo16e.build_case(cfg, case)
    assert blocks == grading14.render_imported_blocks(
        profile, reason=blocks["render_fallback_reason"], include_breakpoints=True,
    )


# ---------------------------------------------------------------------------
# Composition validation
# ---------------------------------------------------------------------------


def test_every_interface_is_located_including_the_abrupt_case(cfg, cases):
    for case in cases:
        _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
        records = demo16e._interface_records(
            profile.x_nm, profile.al_fraction, profile, case
        )
        assert len(records) == 4
        assert all(row["realized_centre_nm"] is not None for row in records), case.case_id
        assert all(row["window_isolated_from_other_interfaces"] for row in records)
        widths = [row["realized_width_10_90_nm"] for row in records
                  if row["realized_width_10_90_nm"]]
        assert all(abs(width - 7.1) > 0.4 for width in widths)
        assert all(abs(width - 2.9) > 0.4 for width in widths)


def test_metrology_window_widens_only_for_the_abrupt_case(cases):
    for case in cases:
        windows = demo16e.metrology_widths(case)
        requested = demo16e.requested_widths(case)
        if case.is_abrupt:
            assert set(windows.values()) == {demo16e.MIN_METROLOGY_WINDOW_NM}
            assert set(requested.values()) == {0.0}
        else:
            assert windows == requested


def test_identity_comparison_passes_for_all_ten_cases(cfg, cases):
    for case in cases:
        _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
        result = demo16e.compare_compositions(
            profile, case, profile.x_nm.copy(), profile.al_fraction.copy()
        )
        assert result["checks"]["passed"], (case.case_id, result["checks"])
        assert result["gated_max_absolute_al_fraction_difference"] < 1e-12


def test_realized_geometry_metrics_recover_the_requested_layers(cfg, cases):
    for case in cases:
        if case.overlap:
            continue  # an overlapped barrier has no 50% crossing of its own
        _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
        result = demo16e.compare_compositions(
            profile, case, profile.x_nm, profile.al_fraction
        )
        geometry = result["geometry"]
        w1, w2 = case.well_widths_nm()
        assert geometry["realized_well_1_nm"] == pytest.approx(w1, abs=0.1)
        assert geometry["realized_central_barrier_nm"] == pytest.approx(
            case.central_barrier_nm, abs=0.1)
        assert geometry["realized_well_2_nm"] == pytest.approx(w2, abs=0.1)
        assert geometry["realized_total_gaas_well_nm"] == pytest.approx(10.0, abs=0.15)


def test_overlapping_barrier_positions_are_measured_but_not_gated(cfg, cases):
    case = next(case for case in cases if case.overlap)
    _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
    result = demo16e.compare_compositions(
        profile, case, profile.x_nm, profile.al_fraction
    )
    assert not result["central_interface_positions_gated"]
    assert result["gated_interface_positions"] == [
        "outer_left_algaas_to_gaas", "outer_right_gaas_to_algaas"
    ]
    central = [row for row in result["realized_interface_metrics"]
               if row["interface"].startswith("central")]
    # Measured and recorded: an overlapped barrier's ramps have no 50% crossing
    # of their own, and the number says so instead of being suppressed.
    assert all(row["centre_error_nm"] > demo16e.MAX_INTERFACE_POSITION_ERROR_NM
               for row in central)
    assert result["checks"]["interface_positions_within_tolerance"]
    assert result["checks"]["passed"]


def test_abrupt_gate_excludes_interface_cells_and_reports_both_maxima(cfg, cases):
    case = cases[1]
    _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
    x = np.asarray(profile.x_nm, dtype=float)
    realized = demo16b.intended_on(profile, x)
    # A one-cell disagreement exactly at an interface: the grid convention this
    # exclusion exists for. Away from the steps the two profiles are identical.
    z2 = float(profile.request["interfaces_nm"]["central_gaas_to_algaas"])
    index = int(np.argmin(np.abs(x - z2)))
    realized[index] = cases16e.AL_FRACTION
    result = demo16e.compare_compositions(profile, case, x, realized)
    assert result["interface_exclusion_applied"]
    assert result["points_excluded_near_interfaces"] > 0
    assert result["max_absolute_al_fraction_difference"] > 0.1
    assert result["max_absolute_al_fraction_difference_off_interface"] == 0.0
    assert result["checks"]["passed"]


def test_graded_case_is_not_given_the_abrupt_exclusion(cfg, cases):
    case = cases[0]
    _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
    x = np.asarray(profile.x_nm, dtype=float)
    realized = demo16b.intended_on(profile, x)
    z2 = float(profile.request["interfaces_nm"]["central_gaas_to_algaas"])
    realized[int(np.argmin(np.abs(x - z2)))] += 0.2
    result = demo16e.compare_compositions(profile, case, x, realized)
    assert not result["interface_exclusion_applied"]
    assert not result["checks"]["max_absolute_error_within_tolerance"]
    assert not result["checks"]["passed"]


# ---------------------------------------------------------------------------
# Licensed-run plumbing
# ---------------------------------------------------------------------------


def test_short_physics_output_roots_fit_budget(cases):
    run_root = Path(
        r"C:\nn_results\16E_acqw_structure_physics_optical_comparison"
        r"\demo16e_20260807T201711Z_3f837abc_c90082"
    )
    names = []
    for case in cases:
        raw = demo16e.physics_raw_output_dir(run_root / "cases" / case.case_id, case)
        assert raw.parent == run_root
        assert sweeps.check_path_budget(raw) is None
        names.append(raw.name)
    assert names == [f"p{i:02d}" for i in range(1, 11)]


def test_full_solver_command_is_not_parse_or_structure(cfg, cases):
    machine = SimpleNamespace(
        executable=Path(r"C:\nextnano\nextnano++_Intel_64bit.exe"),
        database=Path(r"C:\nextnano\database.nnp"),
        license=Path(r"C:\nextnano\license.lic"),
    )
    case_dir = Path(r"C:\nn_results\run\cases\case_10")
    command = demo16e.full_physics_command(cfg, cases[9], case_dir, machine=machine)
    assert command == solver14.real_argv(
        executable=machine.executable, database=machine.database,
        license_path=machine.license,
        deck=case_dir / "physics" / "nextnano_input" / "case.in",
        output_dir=Path(r"C:\nn_results\run\p10"), threads=1,
    )
    assert "--parse" not in command and "--structure" not in command


def test_full_physics_decks_request_all_required_quantum_outputs(cfg, cases):
    for case in cases:
        _geometry, _profile, _blocks, deck = demo16e.build_case(cfg, case)
        compact = " ".join(deck.split())
        for marker in (
            "output_bandedges", "Gamma{ num_ev", "HH{ num_ev", "output_states{",
            "envelopes = yes", "probabilities = yes", "run{ quantum{} }",
        ):
            assert marker in compact, (case.case_id, marker)


def test_optical_config_reuses_absolute_demo14_demo11_pipeline(cfg, cases):
    geometry, profile, _blocks, _deck = demo16e.build_case(cfg, cases[0])
    derived = adapter14.build_demo11_analysis_config_from_demo14(cfg, geometry, profile)
    assert derived["metric"]["mode"] == "absolute"
    assert derived["metric"]["reference_wavelength_nm"] == 1550.0
    assert derived["metric"]["focused_wavelength_nm"] == [1400.0, 1800.0]
    assert derived["metric"]["broadening_meV"] == pytest.approx(5.0)
    assert derived["metric"]["max_states_per_band"] == 2


def test_solve_case_renders_this_demos_deck_not_demo16bs(tmp_path, cfg, cases,
                                                         monkeypatch):
    """The abrupt case must reach the solver as an abrupt deck."""

    written: dict[str, str] = {}

    def capture(**kwargs):
        written["deck"] = Path(kwargs["deck"]).read_text(encoding="utf-8")
        raise RuntimeError("stop after the deck is written")

    monkeypatch.setattr(demo16b.solver14, "execute_real", capture)
    machine = SimpleNamespace(executable="nextnano++.exe", database=None, license=None)
    record = demo16e.solve_case(cfg, cases[1], tmp_path / "case_02", machine=machine)
    assert record["failure_stage"] == "solver"
    statements = "\n".join(
        line for line in written["deck"].splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "ternary_linear" not in statements
    assert statements.count('binary{ name = "GaAs" }') == 2


def test_demo16b_solve_case_still_defaults_to_its_own_builder(tmp_path, cfg):
    """Regression for the shared hook: Demo 16B's own behaviour is unchanged."""

    import cases16b

    written: dict[str, str] = {}

    def capture(**kwargs):
        written["deck"] = Path(kwargs["deck"]).read_text(encoding="utf-8")
        raise RuntimeError("stop after the deck is written")

    case = cases16b.all_cases()[0]
    expected = demo16b.build_case(cfg, case)[3]
    import pytest as _pytest  # local alias keeps the monkeypatch scope obvious

    _pytest.MonkeyPatch().setattr(demo16b.solver14, "execute_real", capture)
    try:
        demo16b.solve_case(
            cfg, case, tmp_path / case.case_id,
            machine=SimpleNamespace(executable="nextnano++.exe", database=None,
                                    license=None),
        )
    finally:
        _pytest.MonkeyPatch().undo()
    assert written["deck"] == expected


def test_parser_failure_stops_structure(tmp_path, monkeypatch, cfg, cases):
    structure_calls = []
    monkeypatch.setattr(
        demo16, "parse_deck",
        lambda *args, **kwargs: {"passed": False, "return_code": 1,
                                 "failure_reason": "bad deck"},
    )
    monkeypatch.setattr(
        demo16e, "run_structure", lambda *args, **kwargs: structure_calls.append(True)
    )
    outcome = demo16e.run_case(
        cfg, cases[0], tmp_path / "case_01", exe=Path("nextnano++.exe"),
        database=None, do_parse=True, do_structure=True,
    )
    assert outcome.status == "parser_failed"
    assert not structure_calls


def test_structure_failure_stops_full_solver(tmp_path, monkeypatch, cases):
    outcomes = [
        demo16e.CaseOutcome(case.case_id, case.name, status="structure_failed",
                            failure_reason="composition mismatch")
        for case in cases
    ]
    for sub in ("summaries", "plots", "cases"):
        (tmp_path / sub).mkdir()
    monkeypatch.setattr(
        run_demo16e, "_machine_or_none", lambda: SimpleNamespace(run_solver=True)
    )
    monkeypatch.setattr(run_demo16e, "run_levels", lambda **kwargs: (1, tmp_path, outcomes))
    called = []
    monkeypatch.setattr(demo16e, "solve_case", lambda *a, **k: called.append(True))
    assert run_demo16e.run_physics() == 1
    assert not called


def test_solver_failure_stops_localization_and_optics(tmp_path, monkeypatch, cases):
    outcomes = [
        demo16e.CaseOutcome(case.case_id, case.name, status="structure_passed")
        for case in cases
    ]
    for sub in ("summaries", "plots", "cases"):
        (tmp_path / sub).mkdir()
    monkeypatch.setattr(
        run_demo16e, "_machine_or_none",
        lambda: SimpleNamespace(run_solver=True, executable="nextnano++.exe",
                                database=None, license=None),
    )
    monkeypatch.setattr(run_demo16e, "run_levels", lambda **kwargs: (0, tmp_path, outcomes))
    monkeypatch.setattr(demo16e, "full_physics_command", lambda *a, **k: ["solver"])
    monkeypatch.setattr(
        demo16e, "solve_case",
        lambda *args, **kwargs: {"case_id": args[1].case_id, "passed": False,
                                 "failure_stage": "solver", "failure_reason": "refused"},
    )
    calls = []
    monkeypatch.setattr(demo16e, "localization", lambda *a, **k: calls.append("local"))
    monkeypatch.setattr(demo16e, "analyse_optics", lambda *a, **k: calls.append("optics"))
    assert run_demo16e.run_physics() == 1
    assert not calls


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
        lambda *a, **k: (_ for _ in ()).throw(demo16b.Demo16BError("missing HH envelopes")),
    )
    monkeypatch.setattr(demo16b, "analyse_physics", lambda *a, **k: analysed.append(True))
    machine = SimpleNamespace(executable="nextnano++.exe", database=None, license=None)
    record = demo16e.solve_case(cfg, cases[0], tmp_path / "case_01", machine=machine)
    assert record["failure_stage"] == "quantum_output_gate"
    assert not analysed


def test_analyze_existing_never_calls_solver(tmp_path, monkeypatch):
    (tmp_path / "summary.json").write_text(
        json.dumps({"run_id": "demo16e_test", "cases_passed": 10, "cases_total": 10,
                    "cases": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        demo16e, "solve_case",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("solver called")),
    )
    assert run_demo16e.analyze_existing(tmp_path) == 0


def test_results_root_uses_the_short_configured_root(monkeypatch):
    monkeypatch.setattr(
        run_demo16e, "_machine_or_none",
        lambda: SimpleNamespace(results_root=Path(r"C:\nn_results")),
    )
    root = run_demo16e.results_root() / demo16e.DEMO_ID
    assert root == Path(r"C:\nn_results") / demo16e.DEMO_ID
    assert not [a for a, b in zip(root.parts, root.parts[1:]) if a == b]


# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------


def _write_columns(path: Path, header: list[str], columns: list[np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.column_stack(columns)
    lines = ["".join(f"{name:<24}" for name in header)]
    lines += ["".join(f"{value:<24.12g}" for value in row) for row in data]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _synthetic_run(root: Path, regions, *, offset_nm: float = 0.0) -> Path:
    """A minimal nextnano++ output tree with states in known wells."""

    left, barrier, right = regions
    z = np.linspace(left[0] - 4.0, right[1] + 4.0, 501)
    quantum = root / "bias_00000" / "Quantum" / "acqw"

    def gaussian(centre: float, width: float) -> np.ndarray:
        return np.exp(-0.5 * ((z - centre) / width) ** 2)

    def density(values: np.ndarray) -> np.ndarray:
        return values**2 / float(np.trapezoid(values**2, z))

    left_centre = 0.5 * (left[0] + left[1])
    right_centre = 0.5 * (right[0] + right[1])
    e1 = density(gaussian(left_centre + offset_nm, 1.4))
    e2 = density(gaussian(right_centre, 0.9))
    hh1 = density(gaussian(left_centre, 1.0))
    hh2 = density(gaussian(right_centre, 0.7))

    _write_columns(root / "bias_00000" / "bandedges.dat",
                   ["x[nm]", "Gamma[eV]", "HH[eV]", "LH[eV]", "SO[eV]"],
                   [z, np.full_like(z, 3.3), np.full_like(z, 1.18),
                    np.full_like(z, 1.18), np.full_like(z, 0.87)])
    _write_columns(quantum / "Gamma" / "energy_spectrum_k00000.dat",
                   ["no.", "Energy[eV]"],
                   [np.array([1.0, 2.0]), np.array([2.9381, 3.0467])])
    _write_columns(quantum / "Gamma" / "probabilities_k00000.dat",
                   ["x[nm]", "Psi^2_1[nm^-1]", "Psi^2_2[nm^-1]"], [z, e1, e2])
    _write_columns(quantum / "Gamma" / "envelopes_k00000.dat",
                   ["x[nm]", "Psi_1[nm^-1/2]", "Psi_2[nm^-1/2]"],
                   [z, np.sqrt(e1), np.sqrt(e2)])
    _write_columns(quantum / "HH" / "energy_spectrum_k00000.dat",
                   ["no.", "Energy[eV]"],
                   [np.array([1.0, 2.0]), np.array([1.4484, 1.4151])])
    _write_columns(quantum / "HH" / "probabilities_k00000.dat",
                   ["x[nm]", "Psi^2_1[nm^-1]", "Psi^2_2[nm^-1]"], [z, hh1, hh2])
    (root / "job_done.txt").write_text("done\n", encoding="utf-8")
    return root


@pytest.fixture()
def synthetic(tmp_path, cfg, cases):
    _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, cases[0])
    regions = demo16b._region_map(profile)
    ordered = (regions["thick_well"], regions["central_barrier"], regions["thin_well"])
    root = _synthetic_run(tmp_path / "p01", ordered)
    return root, profile


def test_localization_probabilities_are_complete_and_signed(cfg, synthetic):
    raw, profile = synthetic
    record, waves = demo16e.localization(cfg, raw, profile)
    assert record["checks"]["passed"]
    assert [row["state"] for row in record["states"]] == list(demo16e.STATE_LABELS)
    for row in record["states"]:
        total = (row["left_probability"] + row["barrier_probability"]
                 + row["right_probability"] + row["outside_probability"])
        assert total == pytest.approx(1.0, abs=1e-9)
        assert row["localization"] == pytest.approx(
            row["left_probability"] - row["right_probability"]
        )
    by_state = record["by_state"]
    assert by_state["E1"]["localization"] > 0.5
    assert by_state["E2"]["localization"] < -0.5
    assert by_state["HH1"]["localization"] > 0.5
    assert by_state["HH2"]["localization"] < -0.5
    assert waves.electron_densities.shape[1] >= 2
    assert waves.hole_densities.shape[1] >= 2


def test_localization_reports_the_outer_barrier_tail(cfg, synthetic):
    raw, profile = synthetic
    record, _waves = demo16e.localization(cfg, raw, profile)
    assert all(row["outside_probability"] >= 0.0 for row in record["states"])
    assert any(row["outside_probability"] > 0.0 for row in record["states"])


def test_localization_refuses_mismatched_electron_and_hole_grids(
    tmp_path, cfg, cases, monkeypatch
):
    _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, cases[0])
    regions = demo16b._region_map(profile)
    root = _synthetic_run(
        tmp_path / "p01",
        (regions["thick_well"], regions["central_barrier"], regions["thin_well"]),
    )
    hh = root / "bias_00000" / "Quantum" / "acqw" / "HH" / "probabilities_k00000.dat"
    lines = hh.read_text(encoding="utf-8").splitlines()
    hh.write_text("\n".join(lines[:-40]) + "\n", encoding="utf-8")
    with pytest.raises(demo16e.Demo16EError):
        demo16e.localization(cfg, root, profile)


def test_wavefunction_csv_carries_all_four_states(tmp_path, cfg, synthetic):
    raw, profile = synthetic
    _record, waves = demo16e.localization(cfg, raw, profile)
    path = demo16e.write_wavefunction_csv(tmp_path / "wavefunctions.csv", waves)
    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header[0] == "position_nm"
    for label in demo16e.STATE_LABELS:
        assert f"{label}_probability_density" in header
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    assert data.shape[1] == 5


# ---------------------------------------------------------------------------
# Cross-case comparisons
# ---------------------------------------------------------------------------


def _row(case_id: str, **overrides) -> dict:
    row = {
        "case": case_id, "name": case_id, "well_1_nm": 7.1, "well_2_nm": 2.9,
        "central_barrier_nm": 1.8, "left_grading_nm": 0.7, "right_grading_nm": 0.7,
        "realized_peak_xAl": 0.55,
        "E1_eV": 2.9381, "E2_eV": 3.0467, "HH1_eV": 1.4484, "HH2_eV": 1.4151,
        "chi2_at_1550": 1200.0, "peak_chi2": 1500.0, "peak_wavelength_nm": 1540.0,
        "detuning_from_1550_nm": -10.0, "chi2_units": "pm/V",
    }
    for label in demo16e.STATE_LABELS:
        row.update({
            f"{label}_left_probability": 0.7, f"{label}_barrier_probability": 0.1,
            f"{label}_right_probability": 0.15,
            f"{label}_outside_probability": 0.05,
            f"{label}_localization": 0.55,
        })
    row.update(overrides)
    return row


def test_energy_shifts_are_meV_against_the_reference():
    rows = [_row("case_01"), _row("case_03", E1_eV=2.9481, HH1_eV=1.4464)]
    filled = demo16e.add_reference_shifts(rows)
    assert filled[0]["delta_E1_meV_vs_reference"] == pytest.approx(0.0)
    assert filled[1]["delta_E1_meV_vs_reference"] == pytest.approx(10.0, abs=1e-6)
    assert filled[1]["delta_HH1_meV_vs_reference"] == pytest.approx(-2.0, abs=1e-6)
    assert all(row["reference_case"] == "case_01" for row in filled)


def test_derived_energies_use_the_documented_hole_convention():
    derived = demo16e.derived_energies(_row("case_01"))
    assert derived["E2_minus_E1_meV"] == pytest.approx(108.6, abs=1e-3)
    assert derived["HH1_minus_HH2_meV"] == pytest.approx(33.3, abs=1e-3)
    assert derived["transition_e1_hh1_eV"] == pytest.approx(2.9381 - 1.4484)


def test_equivalence_report_passes_for_identical_solves():
    native, imported = _row("case_09"), _row("case_10")
    report = demo16e.equivalence_report(
        native, imported,
        {"points": 10, "max_abs_xAl_difference": 0.0, "rms_xAl_difference": 0.0},
    )
    assert report["checks"]["passed"]
    assert report["max_abs_energy_difference_meV"] == pytest.approx(0.0)
    assert report["chi2_at_1550_relative_difference"] == pytest.approx(0.0)


def test_equivalence_report_reports_a_real_disagreement():
    native = _row("case_09")
    imported = _row("case_10", E1_eV=2.9481, chi2_at_1550=1500.0,
                    peak_wavelength_nm=1546.0)
    report = demo16e.equivalence_report(
        native, imported,
        {"points": 10, "max_abs_xAl_difference": 0.0, "rms_xAl_difference": 0.0},
    )
    assert not report["checks"]["passed"]
    assert not report["checks"]["state_energies_agree"]
    assert not report["checks"]["chi2_at_1550_agrees"]
    assert not report["checks"]["peak_wavelength_agrees"]
    assert report["energy_differences_meV"]["delta_E1_meV"] == pytest.approx(10.0, abs=1e-6)


def test_abrupt_vs_graded_report_is_descriptive_only():
    graded = _row("case_01")
    abrupt = _row("case_02", E1_eV=2.9200, chi2_at_1550=900.0,
                  peak_wavelength_nm=1520.0, left_grading_nm=0.0,
                  right_grading_nm=0.0)
    report = demo16e.abrupt_vs_graded_report(graded, abrupt)
    assert report["energy_shifts_graded_minus_abrupt_meV"]["delta_E1_meV"] == (
        pytest.approx(18.1, abs=1e-6)
    )
    assert report["chi2_at_1550"]["graded_minus_abrupt"] == pytest.approx(300.0)
    assert report["chi2_at_1550"]["graded_over_abrupt"] == pytest.approx(1200.0 / 900.0)
    assert report["peak_wavelength_nm"]["graded_minus_abrupt_nm"] == pytest.approx(20.0)
    assert "checks" not in report


def test_master_row_covers_every_summary_field(cfg, cases):
    record = {
        "analysis": {"E_e1_eV": 2.9, "E_e2_eV": 3.0, "E_hh1_eV": 1.45,
                     "E_hh2_eV": 1.41},
        "optical": {"chi2_at_1550": 1200.0, "chi2_units": "pm/V",
                    "spectral_peak_chi2": 1500.0,
                    "spectral_peak_wavelength_nm": 1540.0,
                    "detuning_from_1550_nm": -10.0,
                    "spectrum_path": "chi2_focused.csv"},
        "localization": {"by_state": {
            label: {"left_probability": 0.6, "barrier_probability": 0.1,
                    "right_probability": 0.25, "outside_probability": 0.05,
                    "localization": 0.35}
            for label in demo16e.STATE_LABELS
        }},
        "raw_output_dir": r"C:\nn_results\run\p01",
        "wavefunction_csv_path": "wavefunctions.csv",
    }
    comparison = {"realized_peak_al_fraction": 0.55,
                  "max_absolute_al_fraction_difference": 1e-4,
                  "rms_al_fraction_difference": 1e-5}
    rows = demo16e.add_reference_shifts(
        [demo16e.master_row(cases[0], record, comparison, "native_linear")]
    )
    missing = [field for field in run_demo16e.MASTER_FIELDS if field not in rows[0]]
    assert not missing, missing
    assert rows[0]["representation"] == "native_linear"
    assert rows[0]["E1_localization"] == pytest.approx(0.35)
    assert rows[0]["detuning_from_1550_nm"] == pytest.approx(-10.0)


def test_master_summary_writes_csv_and_json(tmp_path, cfg, cases):
    rows = demo16e.add_reference_shifts([_row("case_01"), _row("case_02")])
    reports = {
        "abrupt_vs_graded": demo16e.abrupt_vs_graded_report(rows[0], rows[1]),
    }
    run_demo16e._write_master_summary(tmp_path, rows, reports)
    csv_path = tmp_path / "summaries" / run_demo16e.MASTER_CSV
    json_path = tmp_path / "summaries" / run_demo16e.MASTER_JSON
    assert csv_path.is_file() and json_path.is_file()
    header = csv_path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header == run_demo16e.MASTER_FIELDS
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["optimization_performed"] is False
    assert payload["reference_case"] == "case_01"
    assert payload["detuning_sign_convention"] == "peak_wavelength_nm - 1550_nm"
    assert (tmp_path / "summaries" / "abrupt_vs_graded.json").is_file()


# ---------------------------------------------------------------------------
# Atomic writes on Windows
#
# Shared Demo 14 infrastructure, tested here because this is where the failure
# was seen: a licensed Demo 16E run lost a case at os.replace with
# PermissionError (WinError 5), on case_06 in one run and case_04 in another.
# ---------------------------------------------------------------------------


def test_atomic_write_retries_a_transient_windows_lock(tmp_path, monkeypatch):
    real_replace = os.replace
    attempts, slept = [], []

    def flaky(src, dst):
        attempts.append((src, dst))
        if len(attempts) <= 3:
            raise PermissionError(5, "Access is denied")
        return real_replace(src, dst)

    monkeypatch.setattr(runlog14.os, "replace", flaky)
    monkeypatch.setattr(runlog14.time, "sleep", slept.append)

    target = tmp_path / "physics_result.json"
    assert runlog14.write_json_atomic(target, {"case_id": "case_06"}) == target
    assert json.loads(target.read_text(encoding="utf-8")) == {"case_id": "case_06"}
    assert len(attempts) == 4
    assert slept == list(runlog14.REPLACE_RETRY_DELAYS_S[:3])
    assert slept == sorted(slept), "delays must back off, not shrink"
    # Only the rename is retried; the payload is serialised once.
    assert not list(tmp_path.glob("~*.tmp"))


def test_atomic_write_reports_both_paths_when_every_retry_fails(tmp_path, monkeypatch):
    def always_denied(src, dst):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(runlog14.os, "replace", always_denied)
    monkeypatch.setattr(runlog14.time, "sleep", lambda _delay: None)

    target = tmp_path / "case_result.json"
    with pytest.raises(runlog14.Runlog14Error) as raised:
        runlog14.write_json_atomic(target, {"case_id": "case_04"})
    message = str(raised.value)
    assert str(target) in message
    leftover = list(tmp_path.glob("~case_result.json.*.tmp"))
    assert len(leftover) == 1
    assert str(leftover[0]) in message
    assert f"{len(runlog14.REPLACE_RETRY_DELAYS_S) + 1} attempts" in message


def test_atomic_text_write_shares_the_retry(tmp_path, monkeypatch):
    real_replace = os.replace
    attempts = []

    def flaky(src, dst):
        attempts.append(dst)
        if len(attempts) == 1:
            raise PermissionError(5, "Access is denied")
        return real_replace(src, dst)

    monkeypatch.setattr(runlog14.os, "replace", flaky)
    monkeypatch.setattr(runlog14.time, "sleep", lambda _delay: None)

    target = tmp_path / "realized_profile.csv"
    runlog14.write_text_atomic(target, "position_nm,realized_al_fraction\n")
    assert target.read_text(encoding="utf-8") == "position_nm,realized_al_fraction\n"
    assert len(attempts) == 2


def test_atomic_write_does_not_retry_when_the_rename_succeeds(tmp_path, monkeypatch):
    slept = []
    monkeypatch.setattr(runlog14.time, "sleep", slept.append)
    runlog14.write_json_atomic(tmp_path / "summary.json", {"ok": True})
    assert not slept


def test_no_optimization_vocabulary_in_the_demo_sources():
    """Demo 16E must not acquire a search loop by accident."""

    banned = ("import ax", "ax_client", "AxClient", "acquisition_function",
              "BayesOpt", "best_design", "winner")
    for path in sorted(DEMO_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, (path.name, token)
