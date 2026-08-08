"""Nineteen concise preflight checks for Demo 16E.

Everything that can be established without a licensed solve is established here,
so a licensed run either starts from a known-good state or does not start.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any, Callable

import numpy as np

import adapter14
import cases16e
import demo14
import demo16
import demo16b
import demo16e
import grading14
import sweeps
from preflight16 import database_for, license_for, parser_executable

PASS, FAIL = "PASS", "FAIL"
CHECK_COUNT = 19


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"check": name, "status": PASS, "detail": str(fn())}
    except Exception as exc:  # noqa: BLE001
        return {"check": name, "status": FAIL,
                "detail": f"{type(exc).__name__}: {exc}"}


def run_preflight(verbose: bool = False) -> int:
    demo_dir = Path(__file__).resolve().parent
    cfg = demo14.load_config()
    loaded = cases16e.load_cases(demo_dir / cases16e.CASES_FILENAME)

    def cases_load() -> str:
        expected = [f"case_{i:02d}" for i in range(1, cases16e.CASE_COUNT + 1)]
        assert [case.case_id for case in loaded] == expected
        assert [case.as_record() for case in cases16e.all_cases()] == [
            case.as_record() for case in loaded
        ]
        return "case_01 .. case_10, identical to the frozen list"

    def geometry_resolves() -> str:
        records = []
        for case in loaded:
            geometry, _profile, _blocks, _deck = demo16e.build_case(cfg, case)
            records.append(geometry.as_record())
            assert abs(geometry.thick_well_nm + geometry.thin_well_nm - 10.0) < 1e-12
        assert np.allclose(
            (records[0]["thick_well_nm"],
             records[0]["nominal_central_barrier_thickness_nm"],
             records[0]["thin_well_nm"]),
            (7.1, 1.8, 2.9),
        )
        return "authoritative Demo 14 geometry; fixed 10 nm GaAs total"

    def ranges_hold() -> str:
        cases16e.validate_cases(loaded)
        return "s=[0.30,0.55], barrier=[0.85,2.50], grade=0 or [0.40,1.40] nm"

    def linear_only() -> str:
        assert {case.grading_profile for case in loaded} == {"linear"}
        return "linear family only"

    def production_imports() -> str:
        assert callable(demo14.geometry_for) and callable(demo14.build_grading)
        assert callable(grading14.render_structure_blocks)
        assert callable(grading14.render_imported_blocks)
        assert callable(demo16.parse_deck) and callable(demo16b.solve_case)
        return "Demo 14 renderer + Demo 16/16B parser, gate and solve"

    def profiles_build_and_bound() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
            assert np.all(np.isfinite(profile.al_fraction))
            assert profile.al_fraction.min() >= -1e-9
            assert profile.al_fraction.max() <= cases16e.AL_FRACTION + 1e-9
        return f"{len(loaded)} authoritative profiles remain in [0, 0.55]"

    def physical_stack() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
            checks = demo16.structural_invariants(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"], cases16e.AL_FRACTION,
            )
            assert checks["all_passed"], (case.case_id, checks)
        return "outer barriers and two GaAs wells in all ten cases"

    def representations_are_as_declared() -> str:
        seen: dict[str, list[str]] = {}
        for case in loaded:
            _geometry, _profile, blocks, _deck = demo16e.build_case(cfg, case)
            realized = demo16e.representation_of(blocks, case)
            assert realized == case.expected_representation, (
                case.case_id, realized, case.expected_representation
            )
            seen.setdefault(realized, []).append(case.case_id)
        assert set(seen) == set(cases16e.REPRESENTATIONS), seen
        return ", ".join(f"{key}={len(value)}" for key, value in sorted(seen.items()))

    def abrupt_deck_has_no_ramps() -> str:
        case = next(case for case in loaded if case.is_abrupt)
        _geometry, _profile, blocks, deck = demo16e.build_case(cfg, case)
        # The template's own header names both grammars in a comment, so the
        # check reads the executable lines rather than the file.
        statements = "\n".join(
            line for line in deck.splitlines() if not line.lstrip().startswith("#")
        )
        assert "ternary_linear" not in statements
        assert "ternary_import" not in statements
        assert not blocks["datafile"] and not blocks["import_block"]
        assert statements.count('binary{ name = "GaAs" }') == 2
        assert statements.count("ternary_constant") == 1
        return f"{case.case_id}: two GaAs wells in the Al0.55 matrix, no ramps"

    def overlap_is_controlled() -> str:
        overlapping = []
        for case in loaded:
            _geometry, profile, blocks, _deck = demo16e.build_case(cfg, case)
            report = demo16e.overlap_geometry(profile, case)
            assert report["overlap"] == case.overlap
            if case.overlap:
                overlapping.append(case.case_id)
                assert demo16e.render_method(blocks) == "ternary_import"
                assert not report["true_flat_central_plateau_exists"]
                assert not report["reaches_90_percent_of_nominal"]
        assert overlapping == ["case_08"], overlapping
        return "one overlap; production import; no fabricated Al0.55 plateau"

    def equivalence_pair_is_one_structure() -> str:
        native_id, imported_id = cases16e.equivalence_pair()
        by_id = {case.case_id: case for case in loaded}
        profiles = {}
        for case_id in (native_id, imported_id):
            _geometry, profile, blocks, _deck = demo16e.build_case(cfg, by_id[case_id])
            profiles[case_id] = (profile, blocks)
        difference = demo16e.composition_difference(
            profiles[native_id][0], profiles[imported_id][0]
        )
        assert difference["max_abs_xAl_difference"] == 0.0, difference
        assert demo16e.render_method(profiles[native_id][1]) == "ternary_linear"
        assert demo16e.render_method(profiles[imported_id][1]) == "ternary_import"
        table = np.array(
            [[float(v) for v in line.split()]
             for line in profiles[imported_id][1]["datafile"].strip().splitlines()],
            dtype=float,
        )
        # The table carries the profile's knots as well as its mesh samples, so
        # it has more rows than the profile has points. What has to agree is the
        # FUNCTION nextnano++ will interpolate out of it -- checked where the
        # solver actually samples it, at cell centres.
        native = profiles[native_id][0]
        mesh = float(native.request["mesh_nm"])
        centres = np.arange(0.0, float(native.request["domain_nm"][1]), mesh) + 0.5 * mesh
        centres = centres[(centres >= table[0, 0]) & (centres <= table[-1, 0])]
        error = float(np.max(np.abs(
            np.interp(centres, table[:, 0], table[:, 1])
            - demo16b.intended_on(native, centres)
        )))
        assert error <= 1e-9, error
        return (f"{native_id}/{imported_id} share x_Al(z) exactly; imported table "
                f"reproduces it at solver cell centres to {error:.1e}")

    def local_metrology() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
            records = demo16e._interface_records(
                profile.x_nm, profile.al_fraction, profile, case
            )
            assert all(row["window_isolated_from_other_interfaces"] for row in records)
            assert all(row["realized_centre_nm"] is not None for row in records), (
                case.case_id, records
            )
            widths = [row["realized_width_10_90_nm"] for row in records
                      if row["realized_width_10_90_nm"]]
            assert all(abs(width - forbidden) > demo16e.FORBIDDEN_WIDTH_MARGIN_NM
                       for width in widths
                       for forbidden in demo16e.FORBIDDEN_GRADING_WIDTHS_NM)
        return "every interface located locally; 7.1/2.9 nm cannot be a grading width"

    def localization_regions_cover_the_stack() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
            regions = demo16b._region_map(profile)
            assert set(regions) == {"thick_well", "central_barrier", "thin_well"}
            spans = [regions[name] for name in
                     ("thick_well", "central_barrier", "thin_well")]
            assert all(hi > lo for lo, hi in spans)
            assert spans[0][1] == spans[1][0] and spans[1][1] == spans[2][0]
            total = spans[2][1] - spans[0][0]
            expected = 10.0 + float(case.central_barrier_nm)
            assert abs(total - expected) < 1e-9, (case.case_id, total, expected)
        return "left | barrier | right partition the active region with no gaps"

    def optical_pipeline() -> str:
        geometry, profile, _blocks, _deck = demo16e.build_case(cfg, loaded[0])
        derived = adapter14.build_demo11_analysis_config_from_demo14(cfg, geometry, profile)
        assert derived["metric"]["mode"] == "absolute"
        assert derived["metric"]["reference_wavelength_nm"] == 1550.0
        assert derived["metric"]["focused_wavelength_nm"] == [1400.0, 1800.0]
        assert derived["metric"]["broadening_meV"] == 5.0
        return ("Demo 14 -> Demo 11 absolute chi2, 1400-1800 nm, 1550 nm target, "
                "5 meV broadening")

    try:
        import run_demo16e
        machine = run_demo16e.resolve_machine()
    except Exception:  # noqa: BLE001
        machine = None
    exe = parser_executable(machine)

    def executable_resolves() -> str:
        assert exe is not None and Path(exe).is_file()
        return str(exe)

    def database_resolves() -> str:
        database = database_for(exe)
        assert database is not None and Path(database).is_file()
        return str(database)

    def output_resolves() -> str:
        import run_demo16e
        root = run_demo16e.results_root() / demo16e.DEMO_ID
        assert list(root.parts).count("demo_runs") <= 1
        assert not [a for a, b in zip(root.parts, root.parts[1:]) if a == b]
        return str(root)

    def short_physics_paths() -> str:
        import run_demo16e
        sample = run_demo16e.results_root() / demo16e.DEMO_ID / (
            "demo16e_20260807T235959Z_12345678_abcdef"
        )
        names = []
        for case in loaded:
            raw = demo16e.physics_raw_output_dir(sample / "cases" / case.case_id, case)
            assert sweeps.check_path_budget(raw) is None, raw
            names.append(raw.name)
        assert names == [f"p{i:02d}" for i in range(1, cases16e.CASE_COUNT + 1)], names
        return f"{names[0]}..{names[-1]} under {sample.parent} within the path budget"

    def representative_decks_parse() -> str:
        assert exe is not None
        by_id = {case.case_id: case for case in loaded}
        checked = []
        # One case per representation: the graded reference, the abrupt deck and
        # the deliberately imported one. Parsing all ten would triple preflight
        # time to re-prove the same three grammars.
        for case_id in ("case_01", "case_02", "case_10"):
            case = by_id[case_id]
            _geometry, _profile, blocks, deck = demo16e.build_case(cfg, case)
            with tempfile.TemporaryDirectory(prefix="demo16e_pre_") as temp:
                result = demo16.parse_deck(
                    exe, database_for(exe), Path(temp) / case_id,
                    deck, blocks["datafile"], license_path=license_for(machine),
                )
            assert result["passed"], (
                case_id, result["return_code"], result.get("failure_reason")
            )
            checked.append(f"{case_id}({case.expected_representation})")
        return ", ".join(checked) + " accepted with --parse"

    checks = (
        ("ten fixed cases load", cases_load),
        ("authoritative geometry resolves", geometry_resolves),
        ("parameters lie inside intended ranges", ranges_hold),
        ("linear grading only", linear_only),
        ("production renderer and solver import", production_imports),
        ("authoritative profiles build and stay bounded", profiles_build_and_bound),
        ("outer barriers and two wells exist", physical_stack),
        ("three representations render as declared", representations_are_as_declared),
        ("abrupt deck contains no grading ramps", abrupt_deck_has_no_ramps),
        ("single overlap uses authoritative production behavior", overlap_is_controlled),
        ("equivalence pair describes one structure", equivalence_pair_is_one_structure),
        ("grading metrology remains local", local_metrology),
        ("localization regions partition the stack", localization_regions_cover_the_stack),
        ("validated optical analysis config resolves", optical_pipeline),
        ("nextnano++ executable resolves", executable_resolves),
        ("nextnano++ database resolves", database_resolves),
        ("output directory resolves", output_resolves),
        ("short physics output paths fit the budget", short_physics_paths),
        ("one deck per representation parses", representative_decks_parse),
    )
    if len(checks) != CHECK_COUNT:  # pragma: no cover - guards the printed count
        raise RuntimeError(f"expected {CHECK_COUNT} checks, defined {len(checks)}")
    results = [_check(name, fn) for name, fn in checks]
    width = max(len(row["check"]) for row in results) + 2
    total = len(results)
    print("=" * (width + 48))
    print("  DEMO 16E PREFLIGHT -- ten-structure ACQW physics and optical study")
    print("=" * (width + 48))
    for row in results:
        print(f"  [{row['status']:4}] {row['check']:<{width}} {row['detail']}")
    failed = [row for row in results if row["status"] == FAIL]
    print("=" * (width + 48))
    print(f"  DEMO 16E PREFLIGHT: {'FAIL' if failed else 'PASS'} "
          f"({total - len(failed)}/{total} checks)")
    if verbose:
        for row in failed:
            print(f"    - {row['check']}: {row['detail']}")
    return 1 if failed else 0
