"""Demo 16B preflight: everything checkable before a licensed machine is touched.

The rule it enforces is the same one Demo 16 enforces, for the same reason: a
preflight PASS must mean the production renderer really can produce a deck
nextnano++ accepts, not merely that the case file loaded. Demo 14's first
licensed gate died on a deck nothing had ever parsed. So if a nextnano++ binary
is present and the paper-reference deck does not parse, this reports FAIL.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Callable

import numpy as np

import cases16b
import demo14
import demo16
import demo16b
import grading14
import runlog14
import solver14

PASS, FAIL = "PASS", "FAIL"

#: Free builds that can validate syntax without a licence. Demo 16 owns the
#: resolution helpers; they are imported rather than duplicated.
from preflight16 import (  # noqa: E402  (after the local imports, deliberately)
    database_for,
    license_for,
    parser_executable,
)


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"check": name, "status": PASS, "detail": fn()}
    except AssertionError as exc:
        return {"check": name, "status": FAIL, "detail": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"check": name, "status": FAIL, "detail": f"{type(exc).__name__}: {exc}"}


def run_preflight(verbose: bool = False) -> int:
    demo_dir = Path(__file__).resolve().parent
    cases_path = demo_dir / cases16b.CASES_FILENAME
    cfg = demo14.load_config()
    results: list[dict[str, Any]] = []

    # --- 1-6: the case fixture ---------------------------------------------

    def cases_file_loads() -> str:
        assert cases_path.is_file(), f"missing {cases_path}"
        cases = cases16b.load_cases(cases_path)
        assert cases, "validation_cases.yaml contains no cases"
        return f"{len(cases)} cases from {cases_path.name}"

    def exactly_eight_cases() -> str:
        cases = cases16b.load_cases(cases_path)
        assert len(cases) == 8, f"expected 8 cases, found {len(cases)}"
        ids = [c.case_id for c in cases]
        assert len(set(ids)) == 8, f"duplicate case ids in {ids}"
        assert ids == [f"case_{i:02d}" for i in range(1, 9)], ids
        return "case_01 .. case_08"

    def cases_are_deterministic() -> str:
        a = [c.as_record() for c in cases16b.all_cases()]
        b = [c.as_record() for c in cases16b.all_cases()]
        assert a == b, "case generation is not deterministic"
        stored = [c.parameters() for c in cases16b.load_cases(cases_path)]
        assert stored == [c.parameters() for c in cases16b.all_cases()], (
            "validation_cases.yaml does not match the generator; regenerate it "
            "deliberately with --write-cases if that change is intended"
        )
        return "generator and frozen file agree; no seed, no random draw"

    def parameters_are_in_bounds() -> str:
        for case in cases16b.load_cases(cases_path):
            params = case.parameters()
            for name, (lo, hi) in cases16b.BOUNDS.items():
                value = params[name]
                assert lo - 1e-9 <= value <= hi + 1e-9, (
                    f"{case.case_id}.{name} = {value} outside [{lo}, {hi}]"
                )
        return "all 8 cases inside the Demo 14 production ranges"

    def linear_grading_only() -> str:
        profiles = {c.grading_profile for c in cases16b.load_cases(cases_path)}
        assert profiles == {"linear"}, f"non-linear grading present: {profiles}"
        assert cases16b.GRADING_PROFILE == "linear"
        # A linear profile must take the NATIVE nextnano++ path. If it fell back
        # to an imported table the case would be an overlap case, which 16B does
        # not support.
        for case in cases16b.load_cases(cases_path):
            _g, profile, blocks, _d = demo16b.build_case(cfg, case)
            assert grading14.RENDER_METHOD[profile.request["profile"]] == "ternary_linear"
            assert not blocks["datafile"], (
                f"{case.case_id} fell back to an imported profile"
            )
        return "linear only, rendered natively as ternary_linear{}"

    def paper_reference_resolves() -> str:
        case = next(c for c in cases16b.load_cases(cases_path)
                    if c.name == "paper_reference")
        thick, thin = case.well_widths_nm()
        assert abs(thick - 7.1) < 1e-6, thick
        assert abs(thin - 2.9) < 1e-6, thin
        assert abs(case.nominal_central_barrier_thickness_nm - 1.8) < 1e-9
        return f"{thick:.3f} / {case.nominal_central_barrier_thickness_nm:.1f} / {thin:.3f} nm"

    # --- 7-10: production code really is what is being validated ------------

    def production_geometry_imports() -> str:
        import chi2 as chi2mod

        assert callable(demo14.geometry_for)
        assert callable(chi2mod.well_widths_from_asymmetry)
        thick, thin = chi2mod.well_widths_from_asymmetry(0.42, 10.0)
        assert abs(thick - 7.1) < 1e-9 and abs(thin - 2.9) < 1e-9
        return "demo14.geometry_for + chi2.well_widths_from_asymmetry"

    def production_renderer_imports() -> str:
        source = (demo_dir / "demo16b.py").read_text(encoding="utf-8")
        for banned in ("ternary_constant{", "def render_deck", "def build_structure_profile"):
            assert banned not in source, (
                f"demo16b.py appears to carry its own renderer ({banned!r}); it "
                "must call Demo 14's production code"
            )
        assert callable(grading14.render_structure_blocks)
        assert callable(demo14.render_deck)
        assert callable(demo14.build_grading)
        return "grading14 + demo14 render path, no local duplicate"

    def production_parser_wrapper_imports() -> str:
        import inspect

        assert callable(demo16.parse_deck)
        params = inspect.signature(demo16.parse_deck).parameters
        assert "runmode" in params and "license_path" in params
        return "demo16.parse_deck (--parse and --structure)"

    def production_solver_wrapper_imports() -> str:
        assert callable(solver14.execute_real)
        assert "terminating program" in solver14.FATAL_STDOUT_MARKERS
        assert solver14.SolverTechnicalFailure is not None
        return "solver14.execute_real with fatal-marker and exit-code checks"

    # --- 11-14: the structure Python builds ---------------------------------

    def authoritative_profile_builds() -> str:
        for case in cases16b.load_cases(cases_path):
            _g, profile, _b, _d = demo16b.build_case(cfg, case)
            y = profile.al_fraction
            assert np.all(np.isfinite(y)), case.case_id
            assert y.min() >= -1e-9, case.case_id
            assert y.max() <= cases16b.AL_FRACTION + 1e-9, (
                f"{case.case_id}: peak x_Al {y.max():.6f} exceeds "
                f"{cases16b.AL_FRACTION}"
            )
        return "8 authoritative x_Al(z) profiles built, all within [0, 0.55]"

    def outer_barriers_and_two_wells() -> str:
        for case in cases16b.load_cases(cases_path):
            _g, profile, _b, _d = demo16b.build_case(cfg, case)
            invariants = demo16.structural_invariants(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"], cases16b.AL_FRACTION,
            )
            failed = [k for k, v in invariants.items()
                      if k != "all_passed" and not v]
            assert not failed, f"{case.case_id}: {failed}"
        return "left + right AlGaAs outer barriers and two GaAs wells everywhere"

    def four_interfaces_exist() -> str:
        for case in cases16b.load_cases(cases_path):
            _g, profile, _b, _d = demo16b.build_case(cfg, case)
            i = profile.request["interfaces_nm"]
            assert set(i) == set(demo16b.INTERFACE_ORDER), sorted(i)
            positions = [float(i[name]) for name in demo16b.INTERFACE_ORDER]
            assert all(a < b for a, b in zip(positions, positions[1:])), positions
        return "four ordered interfaces per case"

    def graded_regions_do_not_overlap() -> str:
        """16B's load-bearing rule: no grade may overwrite another."""

        for case in cases16b.load_cases(cases_path):
            _g, profile, blocks, _d = demo16b.build_case(cfg, case)
            report = demo16b.grading_regions_report(profile, blocks)
            assert report["graded_region_count"] == 4, (
                f"{case.case_id}: {report['graded_region_count']} graded regions"
            )
            assert report["graded_regions_disjoint"], (
                f"{case.case_id}: {report['overlaps']}"
            )
            assert report["supported_by_demo16b"], case.case_id
            assert case.non_overlap_margin_nm() > 0, case.case_id
        return "4 disjoint ternary_linear regions per case; smallest margin " + (
            f"{min(c.non_overlap_margin_nm() for c in cases16b.all_cases()):.3f} nm"
        )

    def grading_windows_stay_local() -> str:
        """The guard against reporting a well width as a grading width."""

        offenders: list[str] = []
        for case in cases16b.load_cases(cases_path):
            _g, profile, _b, _d = demo16b.build_case(cfg, case)
            thick, thin = case.well_widths_nm()
            for metric in demo16.measure_interfaces(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"],
                demo16b.interface_widths(case), cases16b.AL_FRACTION,
            ):
                if not metric.window_isolated:
                    offenders.append(
                        f"{case.case_id}/{metric.name}: window {metric.window_nm} "
                        "reaches another interface"
                    )
                realized = metric.realized_width_10_90_nm
                assert realized is not None, f"{case.case_id}/{metric.name}"
                for forbidden in (7.1, 2.9, thick, thin):
                    if abs(realized - float(forbidden)) <= (
                        demo16b.FORBIDDEN_WIDTH_MARGIN_NM
                    ):
                        offenders.append(
                            f"{case.case_id}/{metric.name}: {realized:.3f} nm is "
                            f"the {float(forbidden):.3f} nm WELL width"
                        )
        assert not offenders, "; ".join(offenders[:6])
        return "all windows isolated; 7.1 and 2.9 nm never reported as a grade"

    # --- 15-18: the machine ------------------------------------------------

    try:
        import run_demo16b

        machine = run_demo16b.resolve_machine()
    except Exception:  # noqa: BLE001 - reported by the checks below
        machine = None
    exe = parser_executable(machine)

    def executable_resolves() -> str:
        assert exe is not None, (
            "no nextnano++ binary found; a preflight PASS could not mean the "
            "renderer produces parseable decks"
        )
        assert Path(exe).is_file(), exe
        return str(exe)

    def machine_configuration_resolves() -> str:
        assert machine is not None, "machine configuration could not be resolved"
        database = database_for(exe)
        licence = license_for(machine)
        assert database is not None and Path(database).is_file(), (
            f"no nextnano++ database beside {exe}"
        )
        return (
            f"database={Path(database).name} licence="
            f"{Path(licence).name if licence else '<none needed>'} "
            f"run_solver={getattr(machine, 'run_solver', None)}"
        )

    def output_path_is_valid() -> str:
        import run_demo16b

        root = run_demo16b.results_root()
        parts = list(Path(root).parts)
        duplicates = [a for a, b in zip(parts, parts[1:]) if a == b]
        assert not duplicates, f"duplicated path component(s) {duplicates} in {root}"
        assert parts.count("demo_runs") <= 1, f"demo_runs repeated in {root}"
        assert Path(root).parent.is_dir() or Path(root).is_dir(), (
            f"results root parent does not exist: {root}"
        )
        return str(root / demo16b.DEMO_ID)

    def strict_json_works() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            path = runlog14.write_json_atomic(
                Path(tmp) / "x.json",
                {"nan": float("nan"), "arr": np.array([1.0, 2.0]),
                 "i": np.int64(3), "b": np.bool_(True), "p": Path(tmp)},
            )
            loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["nan"] is None and loaded["arr"] == [1.0, 2.0]
        assert loaded["i"] == 3 and loaded["b"] is True
        return "NumPy, Path and non-finite values serialize to strict JSON"

    for name, fn in (
        ("validation_cases.yaml loads", cases_file_loads),
        ("exactly 8 fixed cases", exactly_eight_cases),
        ("cases are deterministic and frozen", cases_are_deterministic),
        ("parameters inside the Demo 14 ranges", parameters_are_in_bounds),
        ("linear grading only", linear_grading_only),
        ("paper reference is 7.1 / 1.8 / 2.9 nm", paper_reference_resolves),
        ("production geometry functions import", production_geometry_imports),
        ("production renderer imports", production_renderer_imports),
        ("production parser wrapper imports", production_parser_wrapper_imports),
        ("production solver wrapper imports", production_solver_wrapper_imports),
        ("authoritative x_Al(z) builds for all cases", authoritative_profile_builds),
        ("outer barriers and two GaAs wells exist", outer_barriers_and_two_wells),
        ("four ordered interfaces exist", four_interfaces_exist),
        ("graded regions never overlap", graded_regions_do_not_overlap),
        ("grading search windows remain local", grading_windows_stay_local),
        ("nextnano++ executable resolves", executable_resolves),
        ("database / machine configuration resolves", machine_configuration_resolves),
        ("output path is valid", output_path_is_valid),
        ("strict JSON serialization works", strict_json_works),
    ):
        results.append(_check(name, fn))

    # --- the decisive check -------------------------------------------------

    def paper_reference_deck_parses() -> str:
        assert exe is not None, "no nextnano++ binary available to parse the deck"
        database = database_for(exe)
        licence = license_for(machine)
        case = next(c for c in cases16b.load_cases(cases_path)
                    if c.name == "paper_reference")
        _g, _p, blocks, deck = demo16b.build_case(cfg, case)
        with tempfile.TemporaryDirectory(prefix="demo16b_pre_") as tmp:
            result = demo16.parse_deck(
                exe, database, Path(tmp) / case.case_id, deck, blocks["datafile"],
                license_path=licence,
            )
            assert result["passed"], (
                f"{case.case_id}: rc={result['return_code']} "
                f"{result['failure_reason']}"
            )
        return f"paper-reference production deck parsed by {Path(exe).name}"

    results.append(_check("paper-reference deck parses", paper_reference_deck_parses))

    width = max(len(r["check"]) for r in results) + 2
    print("=" * (width + 40))
    print("  DEMO 16B PREFLIGHT -- simple ACQW + linear grading")
    print("=" * (width + 40))
    for row in results:
        print(f"  [{row['status']:4}] {row['check']:<{width}} {row['detail']}")
    failed = [r for r in results if r["status"] == FAIL]
    print("=" * (width + 40))
    if failed:
        print(f"  DEMO 16B PREFLIGHT: FAIL ({len(failed)} of {len(results)})")
        for row in failed:
            print(f"    - {row['check']}: {row['detail']}")
        return 1
    print(f"  DEMO 16B PREFLIGHT: PASS ({len(results)} checks)")
    print("=" * (width + 40))
    return 0
