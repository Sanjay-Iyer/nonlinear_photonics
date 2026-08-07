"""Fifteen concise preflight checks for Demo 16D."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any, Callable

import numpy as np

import adapter14
import cases16d
import demo14
import demo16
import demo16d
import grading14
import sweeps
from preflight16 import database_for, license_for, parser_executable

PASS, FAIL = "PASS", "FAIL"


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"check": name, "status": PASS, "detail": str(fn())}
    except Exception as exc:  # noqa: BLE001
        return {"check": name, "status": FAIL,
                "detail": f"{type(exc).__name__}: {exc}"}


def run_preflight(verbose: bool = False) -> int:
    demo_dir = Path(__file__).resolve().parent
    cfg = demo14.load_config()
    loaded = cases16d.load_cases(demo_dir / cases16d.CASES_FILENAME)

    def cases_load() -> str:
        assert [case.case_id for case in loaded] == [f"case_{i:02d}" for i in range(1, 8)]
        return "case_01 .. case_07"

    def geometry_resolves() -> str:
        records = []
        for case in loaded:
            geometry, _profile, _blocks, _deck = demo16d.build_case(cfg, case)
            records.append(geometry.as_record())
            assert abs(geometry.thick_well_nm + geometry.thin_well_nm - 10.0) < 1e-12
        assert np.allclose(
            (records[0]["thick_well_nm"], records[0]["nominal_central_barrier_thickness_nm"],
             records[0]["thin_well_nm"]),
            (7.1, 1.8, 2.9),
        )
        return "authoritative Demo 14 geometry; fixed 10 nm GaAs total"

    def ranges_hold() -> str:
        cases16d.validate_cases(loaded)
        return "s=[0.30,0.55], barrier=[0.85,2.50], grade=[0.40,1.40] nm"

    def linear_only() -> str:
        assert {case.grading_profile for case in loaded} == {"linear"}
        return "linear only"

    def production_imports() -> str:
        assert callable(demo14.geometry_for) and callable(demo14.build_grading)
        assert callable(grading14.render_structure_blocks) and callable(demo16.parse_deck)
        return "Demo 14 renderer + Demo 16 parser/structure invocation"

    def profiles_build_and_bound() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
            assert np.all(np.isfinite(profile.al_fraction))
            assert profile.al_fraction.min() >= -1e-9
            assert profile.al_fraction.max() <= 0.55 + 1e-9
        return "7 authoritative profiles remain in [0,0.55]"

    def physical_stack() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
            checks = demo16.structural_invariants(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"], cases16d.AL_FRACTION,
            )
            assert checks["all_passed"], (case.case_id, checks)
        return "outer barriers and two GaAs wells in all cases"

    def overlap_is_controlled() -> str:
        for case in loaded:
            _geometry, profile, blocks, _deck = demo16d.build_case(cfg, case)
            report = demo16d.overlap_geometry(profile, case)
            assert report["overlap"] == case.overlap
            expected = "ternary_import" if case.overlap else "ternary_linear"
            assert demo16d.render_method(blocks) == expected
            if case.overlap:
                assert not report["true_flat_central_plateau_exists"]
                assert not report["reaches_90_percent_of_nominal"]
        return "one overlap; production import; no false Al0.55 plateau"

    def local_metrology() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
            records = demo16d._interface_records(
                profile.x_nm, profile.al_fraction, profile, case
            )
            assert all(row["window_isolated_from_other_interfaces"] for row in records)
            widths = [row["realized_width_10_90_nm"] for row in records if row["realized_width_10_90_nm"]]
            assert all(abs(width - forbidden) > 0.4 for width in widths for forbidden in (7.1, 2.9))
        return "local windows; 7.1/2.9 nm cannot be grading widths"

    def optical_pipeline() -> str:
        geometry, profile, _blocks, _deck = demo16d.build_case(cfg, loaded[0])
        derived = adapter14.build_demo11_analysis_config_from_demo14(cfg, geometry, profile)
        assert derived["metric"]["mode"] == "absolute"
        assert derived["metric"]["reference_wavelength_nm"] == 1550.0
        assert derived["metric"]["focused_wavelength_nm"] == [1400.0, 1800.0]
        return "Demo 14 -> Demo 11 absolute chi2, 1400-1800 nm, target 1550 nm"

    try:
        import run_demo16d
        machine = run_demo16d.resolve_machine()
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
        import run_demo16d
        root = run_demo16d.results_root() / demo16d.DEMO_ID
        assert list(root.parts).count("demo_runs") <= 1
        assert not [a for a, b in zip(root.parts, root.parts[1:]) if a == b]
        return str(root)

    def short_physics_paths() -> str:
        import run_demo16d
        sample = run_demo16d.results_root() / demo16d.DEMO_ID / (
            "demo16d_20260807T235959Z_12345678_abcdef"
        )
        for case in cases16d.physics_cases():
            raw = demo16d.physics_raw_output_dir(sample / "cases" / case.case_id, case)
            assert raw.name in {"p01", "p02", "p05", "p07"}
            assert sweeps.check_path_budget(raw) is None
        return "p01/p02/p05/p07 within Windows path budget"

    def representative_parses() -> str:
        assert exe is not None
        case = loaded[0]
        _geometry, _profile, blocks, deck = demo16d.build_case(cfg, case)
        with tempfile.TemporaryDirectory(prefix="demo16d_pre_") as temp:
            result = demo16.parse_deck(
                exe, database_for(exe), Path(temp) / case.case_id,
                deck, blocks["datafile"], license_path=license_for(machine),
            )
        assert result["passed"], f"rc={result['return_code']} {result.get('failure_reason')}"
        return "case_01 production deck accepted with --parse"

    checks = (
        ("seven fixed cases load", cases_load),
        ("authoritative geometry resolves", geometry_resolves),
        ("parameters lie inside intended ranges", ranges_hold),
        ("linear grading only", linear_only),
        ("production renderer imports", production_imports),
        ("authoritative profiles build and stay bounded", profiles_build_and_bound),
        ("outer barriers and two wells exist", physical_stack),
        ("single overlap uses authoritative production behavior", overlap_is_controlled),
        ("grading metrology remains local", local_metrology),
        ("validated optical analysis config resolves", optical_pipeline),
        ("nextnano++ executable resolves", executable_resolves),
        ("nextnano++ database resolves", database_resolves),
        ("output directory resolves", output_resolves),
        ("short physics paths fit path budget", short_physics_paths),
        ("representative deck parses", representative_parses),
    )
    results = [_check(name, fn) for name, fn in checks]
    width = max(len(row["check"]) for row in results) + 2
    print("=" * (width + 45))
    print("  DEMO 16D PREFLIGHT -- incremental ACQW geometry validation")
    print("=" * (width + 45))
    for row in results:
        print(f"  [{row['status']:4}] {row['check']:<{width}} {row['detail']}")
    failed = [row for row in results if row["status"] == FAIL]
    print("=" * (width + 45))
    print(f"  DEMO 16D PREFLIGHT: {'FAIL' if failed else 'PASS'} ({15-len(failed)}/15 checks)")
    if verbose:
        for row in failed:
            print(f"    - {row['check']}: {row['detail']}")
    return 1 if failed else 0
