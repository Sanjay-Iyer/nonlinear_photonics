"""Minimal Demo 16C preflight, including one real parser invocation."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any, Callable

import numpy as np

import cases16c
import demo14
import demo16
import demo16b
import demo16c
import grading14

from preflight16 import database_for, license_for, parser_executable

PASS, FAIL = "PASS", "FAIL"


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"check": name, "status": PASS, "detail": str(fn())}
    except Exception as exc:  # noqa: BLE001 - preflight reports every failure
        return {"check": name, "status": FAIL,
                "detail": f"{type(exc).__name__}: {exc}"}


def run_preflight(verbose: bool = False) -> int:
    demo_dir = Path(__file__).resolve().parent
    case_path = demo_dir / cases16c.CASES_FILENAME
    cfg = demo14.load_config()
    loaded = cases16c.load_cases(case_path)
    results: list[dict[str, Any]] = []

    def exactly_four() -> str:
        assert len(loaded) == 4
        assert [c.case_id for c in loaded] == [f"case_{i:02d}" for i in range(1, 5)]
        return "case_01 .. case_04"

    def fixed_geometry() -> str:
        fixed = [
            (c.asymmetry_s, c.nominal_central_barrier_thickness_nm,
             c.well_widths_nm(), cases16c.AL_FRACTION)
            for c in loaded
        ]
        assert all(row == fixed[0] for row in fixed)
        assert np.allclose(fixed[0][2], (7.1, 2.9))
        assert fixed[0][1] == 1.8 and fixed[0][3] == 0.55
        return "7.1 / 1.8 / 2.9 nm, x_Al=0.55"

    def only_widths_differ() -> str:
        keys = set(loaded[0].parameters())
        variable = {key for key in keys
                    if len({c.parameters()[key] for c in loaded}) > 1}
        assert variable == {
            "gaas_to_algaas_grading_width_10_90_nm",
            "algaas_to_gaas_grading_width_10_90_nm",
        }
        return "only the two central-interface grading widths vary"

    def linear_only() -> str:
        assert {c.grading_profile for c in loaded} == {"linear"}
        return "linear only"

    def profiles_build() -> str:
        for case in loaded:
            _g, profile, _b, _d = demo16c.build_case(cfg, case)
            assert np.all(np.isfinite(profile.al_fraction))
        return "four authoritative profiles built"

    def profile_bounds() -> str:
        for case in loaded:
            _g, profile, _b, _d = demo16c.build_case(cfg, case)
            assert profile.al_fraction.min() >= -1e-9
            assert profile.al_fraction.max() <= 0.55 + 1e-9
        return "all x_Al within [0, 0.55]"

    def stack_exists() -> str:
        for case in loaded:
            _g, profile, _b, _d = demo16c.build_case(cfg, case)
            checks = demo16.structural_invariants(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"], cases16c.AL_FRACTION,
            )
            assert checks["all_passed"], (case.case_id, checks)
        return "two outer barriers and two GaAs wells in every case"

    def no_overlap() -> str:
        for case in loaded:
            _g, profile, blocks, _d = demo16c.build_case(cfg, case)
            report = demo16b.grading_regions_report(profile, blocks)
            assert report["supported_by_demo16b"], (case.case_id, report)
            assert case.non_overlap_margin_nm() > 0
        return "four disjoint native ternary_linear regions per case"

    def renderer_imports() -> str:
        assert callable(demo14.geometry_for) and callable(demo14.build_grading)
        assert callable(grading14.render_structure_blocks)
        assert callable(demo14.render_deck) and callable(demo16.parse_deck)
        return "Demo 14 renderer + Demo 16 invocation"

    def mesh_is_fixed() -> str:
        assert float(cfg["mesh"]["active_region_grid_spacing_nm"]) == 0.05
        assert all(c.as_record()["mesh_nm"] == 0.05 for c in loaded)
        return "0.05 nm active mesh"

    def local_measurement() -> str:
        for case in loaded:
            _g, profile, _b, _d = demo16c.build_case(cfg, case)
            metrics = demo16.measure_interfaces(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"],
                demo16c.interface_widths(case), cases16c.AL_FRACTION,
            )
            central = [m for m in metrics if m.name in
                       (demo16c.INTERFACE_LEFT, demo16c.INTERFACE_RIGHT)]
            assert len(central) == 2 and all(m.window_isolated for m in central)
            assert all(m.realized_width_10_90_nm is not None for m in central)
            assert all(abs(m.realized_width_10_90_nm - forbidden) > 0.4
                       for m in central for forbidden in (7.1, 2.9))
        return "central windows local; no well width can be returned"

    try:
        import run_demo16c
        machine = run_demo16c.resolve_machine()
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

    def output_path_resolves() -> str:
        import run_demo16c
        root = run_demo16c.results_root() / demo16c.DEMO_ID
        parts = list(root.parts)
        assert parts.count("demo_runs") <= 1
        assert not [a for a, b in zip(parts, parts[1:]) if a == b]
        return str(root)

    def representative_parses() -> str:
        assert exe is not None
        case = loaded[0]
        _g, _p, blocks, deck = demo16c.build_case(cfg, case)
        with tempfile.TemporaryDirectory(prefix="demo16c_pre_") as temp:
            result = demo16.parse_deck(
                exe, database_for(exe), Path(temp) / case.case_id,
                deck, blocks["datafile"], license_path=license_for(machine),
            )
        assert result["passed"], (
            f"rc={result['return_code']} {result.get('failure_reason')}"
        )
        return "case_01 production deck accepted with --parse"

    for name, fn in (
        ("exactly four fixed cases load", exactly_four),
        ("fixed paper geometry resolves", fixed_geometry),
        ("only grading widths differ", only_widths_differ),
        ("linear grading only", linear_only),
        ("authoritative profiles build", profiles_build),
        ("composition bounds hold", profile_bounds),
        ("outer barriers and two wells exist", stack_exists),
        ("grading regions do not overlap", no_overlap),
        ("production renderer imports", renderer_imports),
        ("mesh is 0.05 nm", mesh_is_fixed),
        ("grading measurement stays local", local_measurement),
        ("nextnano++ executable resolves", executable_resolves),
        ("nextnano++ database resolves", database_resolves),
        ("output directory resolves", output_path_resolves),
        ("representative deck parses", representative_parses),
    ):
        results.append(_check(name, fn))

    width = max(len(row["check"]) for row in results) + 2
    print("=" * (width + 45))
    print("  DEMO 16C PREFLIGHT -- minimal linear grading validation")
    print("=" * (width + 45))
    for row in results:
        print(f"  [{row['status']:4}] {row['check']:<{width}} {row['detail']}")
    failed = [row for row in results if row["status"] == FAIL]
    print("=" * (width + 45))
    print(f"  DEMO 16C PREFLIGHT: {'FAIL' if failed else 'PASS'} "
          f"({len(results) - len(failed)}/{len(results)} checks)")
    if verbose:
        for row in failed:
            print(f"    - {row['check']}: {row['detail']}")
    return 1 if failed else 0
