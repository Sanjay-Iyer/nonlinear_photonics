"""Demo 16 preflight: everything checkable before a deck is written.

The rule this enforces: a preflight PASS must mean the production renderer really
can produce parseable decks, not that the case list loaded. Demo 14's first
licensed gate died on a deck nothing had ever parsed, so if nextnano++ is
available and a representative deck does not parse, this reports FAIL.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any, Callable

import numpy as np

import cases16
import demo14
import demo16
import grading14

PASS, FAIL = "PASS", "FAIL"

#: Free builds that can validate syntax without a licence.
FREE_PARSER_CANDIDATES = (
    Path(r"C:\Program Files\nextnano\2026_07_03\nextnano++\bin 32bit"
         r"\nextnano++_Microsoft_32bit_free.exe"),
)


def database_for(exe: Path | None) -> Path | None:
    if exe is None:
        return None
    exe = Path(exe)
    for candidate in (
        exe.parent.parent / "database" / "database.nnp",
        exe.parent.parent / "database" / "database_free.nnp",
    ):
        if candidate.is_file():
            return candidate
    return None


def parser_executable(machine: Any | None) -> Path | None:
    configured = getattr(machine, "executable", None) if machine else None
    if configured and Path(configured).is_file():
        return Path(configured)
    for candidate in FREE_PARSER_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"check": name, "status": PASS, "detail": fn()}
    except AssertionError as exc:
        return {"check": name, "status": FAIL, "detail": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"check": name, "status": FAIL, "detail": f"{type(exc).__name__}: {exc}"}


def run_preflight(verbose: bool = False) -> int:
    demo_dir = Path(__file__).resolve().parent
    cases_path = demo_dir / cases16.CASES_FILENAME
    cfg = demo14.load_config()
    results: list[dict[str, Any]] = []

    def cases_file_loads() -> str:
        assert cases_path.is_file(), f"missing {cases_path}"
        cases = cases16.load_cases(cases_path)
        assert len(cases) == 20, f"expected 20 cases, found {len(cases)}"
        return f"{len(cases)} cases from {cases_path.name}"

    def case_composition_is_correct() -> str:
        cases = cases16.load_cases(cases_path)
        deliberate = [c for c in cases if c.origin == "deliberate"]
        seeded = [c for c in cases if c.origin == "seeded_random"]
        assert len(deliberate) == 12, f"{len(deliberate)} deliberate cases"
        assert len(seeded) == 8, f"{len(seeded)} seeded cases"
        ids = [c.case_id for c in cases]
        assert len(set(ids)) == 20, "duplicate case ids"
        return f"12 deliberate + 8 seeded (seed {cases16.SEED})"

    def cases_are_deterministic() -> str:
        a = [c.parameters() for c in cases16.all_cases()]
        b = [c.parameters() for c in cases16.all_cases()]
        assert a == b, "case generation is not deterministic"
        stored = [c.parameters() for c in cases16.load_cases(cases_path)]
        assert stored == a, (
            "validation_cases.yaml does not match the generator; regenerate it "
            "deliberately with --write-cases if this change is intended"
        )
        return "generator and frozen file agree"

    def parameters_are_in_bounds() -> str:
        for case in cases16.load_cases(cases_path):
            params = case.parameters()
            for name, (lo, hi) in cases16.BOUNDS.items():
                value = params[name]
                assert lo - 1e-9 <= value <= hi + 1e-9, (
                    f"{case.case_id}.{name} = {value} outside [{lo}, {hi}]"
                )
            assert params["grading_profile"] in cases16.PROFILES, case.case_id
        return "all 20 cases inside the Demo 14 ranges"

    def every_profile_is_represented() -> str:
        counts: dict[str, int] = {}
        for case in cases16.load_cases(cases_path):
            counts[case.grading_profile] = counts.get(case.grading_profile, 0) + 1
        missing = sorted(set(cases16.PROFILES) - set(counts))
        assert not missing, f"profiles absent: {missing}"
        return str(counts)

    def paper_reference_resolves() -> str:
        case = next(c for c in cases16.load_cases(cases_path)
                    if c.name == "paper_reference")
        thick, thin = case.well_widths_nm()
        assert abs(thick - 7.1) < 1e-6, thick
        assert abs(thin - 2.9) < 1e-6, thin
        assert abs(case.nominal_central_barrier_thickness_nm - 1.8) < 1e-9
        return f"{thick:.3f} / {case.nominal_central_barrier_thickness_nm:.1f} / {thin:.3f} nm"

    def production_renderer_is_reused() -> str:
        # Demo 16 must not carry its own renderer.
        source = (demo_dir / "demo16.py").read_text(encoding="utf-8")
        for banned in ("ternary_linear{", "ternary_constant{", "def render_deck"):
            assert banned not in source, (
                f"demo16.py appears to contain its own renderer ({banned!r}); it "
                "must call Demo 14's production code"
            )
        assert grading14.render_structure_blocks is not None
        assert demo14.render_deck is not None
        return "grading14 + demo14 render path imported, no local duplicate"

    def authoritative_profile_builds() -> str:
        cases = cases16.load_cases(cases_path)
        for case in cases:
            geometry, profile, _blocks, _deck = demo16.build_case(cfg, case)
            y = profile.al_fraction
            assert np.all(np.isfinite(y)), case.case_id
            assert y.min() >= -1e-9 and y.max() <= cases16.AL_FRACTION + 1e-9, case.case_id
        return f"{len(cases)} authoritative profiles built and bounded"

    def outer_barriers_present_everywhere() -> str:
        for case in cases16.load_cases(cases_path):
            _g, profile, _b, _d = demo16.build_case(cfg, case)
            invariants = demo16.structural_invariants(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"], cases16.AL_FRACTION,
            )
            assert invariants["left_outer_barrier_present"], case.case_id
            assert invariants["right_outer_barrier_present"], case.case_id
            assert invariants["all_passed"], (
                case.case_id,
                [k for k, v in invariants.items() if k != "all_passed" and not v],
            )
        return "all 20 cases satisfy every structural invariant"

    def interface_windows_are_local() -> str:
        """The guard against reporting a well width as a grading width."""

        offenders: list[str] = []
        for case in cases16.load_cases(cases_path):
            _g, profile, _b, _d = demo16.build_case(cfg, case)
            interfaces = profile.request["interfaces_nm"]
            widths = {
                "outer_left_algaas_to_gaas": case.algaas_to_gaas_grading_width_10_90_nm,
                "central_gaas_to_algaas": case.gaas_to_algaas_grading_width_10_90_nm,
                "central_algaas_to_gaas": case.algaas_to_gaas_grading_width_10_90_nm,
                "outer_right_gaas_to_algaas": case.gaas_to_algaas_grading_width_10_90_nm,
            }
            for metric in demo16.measure_interfaces(
                profile.x_nm, profile.al_fraction, interfaces, widths,
                cases16.AL_FRACTION,
            ):
                # Isolation is the invariant that matters. A width can legitimately
                # be undefined where two grades overlap -- there is then no single
                # monotone transition to measure, and the overlap oracle describes
                # the barrier instead. A window that reaches a NEIGHBOURING
                # interface is never legitimate.
                if not metric.window_isolated:
                    offenders.append(
                        f"{case.case_id}/{metric.name}: window "
                        f"{metric.window_nm} contains another interface"
                    )
                realized = metric.realized_width_10_90_nm
                if realized is not None and realized > 3.0:
                    offenders.append(
                        f"{case.case_id}/{metric.name}: {realized:.3f} nm looks "
                        "like a well width, not an interface width"
                    )
        assert not offenders, "; ".join(offenders[:6])
        return "all four interface windows isolated from their neighbours"

    def well_widths_are_never_grading_widths() -> str:
        case = next(c for c in cases16.load_cases(cases_path)
                    if c.name == "paper_reference")
        _g, profile, _b, _d = demo16.build_case(cfg, case)
        interfaces = profile.request["interfaces_nm"]
        widths = {k: 1.0 for k in interfaces}
        for metric in demo16.measure_interfaces(
            profile.x_nm, profile.al_fraction, interfaces, widths, cases16.AL_FRACTION
        ):
            realized = metric.realized_width_10_90_nm
            assert realized is not None
            for forbidden in (7.1, 2.9):
                assert abs(realized - forbidden) > 0.5, (
                    f"{metric.name} realized {realized:.3f} nm, which is the "
                    f"{forbidden} nm WELL width -- the regression this exists to "
                    "prevent"
                )
        return "7.1 nm and 2.9 nm well widths are not reported as grading widths"

    def output_root_has_no_duplicate_component() -> str:
        import run_demo16

        try:
            root = run_demo16.results_root()
        except Exception as exc:
            return f"machine config unavailable ({type(exc).__name__}); skipped"
        parts = list(Path(root).parts)
        duplicates = [a for a, b in zip(parts, parts[1:]) if a == b]
        assert not duplicates, f"duplicated path component(s) {duplicates} in {root}"
        assert parts.count("demo_runs") <= 1, f"demo_runs repeated in {root}"
        return str(root)

    def strict_json_works() -> str:
        import runlog14

        with tempfile.TemporaryDirectory() as tmp:
            path = runlog14.write_json_atomic(
                Path(tmp) / "x.json",
                {"nan": float("nan"), "arr": np.array([1.0, 2.0]),
                 "i": np.int64(3), "b": np.bool_(True)},
            )
            import json

            loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["nan"] is None and loaded["arr"] == [1.0, 2.0]
        return "NumPy and non-finite values serialize to strict JSON"

    for name, fn in (
        ("validation_cases.yaml loads", cases_file_loads),
        ("exactly 12 deliberate + 8 seeded cases", case_composition_is_correct),
        ("case list is deterministic and frozen", cases_are_deterministic),
        ("all parameters inside Demo 14 ranges", parameters_are_in_bounds),
        ("all four grading profiles represented", every_profile_is_represented),
        ("paper reference resolves to 7.1/1.8/2.9 nm", paper_reference_resolves),
        ("production Demo 14 renderer is reused", production_renderer_is_reused),
        ("authoritative x_Al(x) builds for every case", authoritative_profile_builds),
        ("outer barriers and invariants hold", outer_barriers_present_everywhere),
        ("interface windows are local and isolated", interface_windows_are_local),
        ("well widths are never grading widths", well_widths_are_never_grading_widths),
        ("output root has no duplicated component", output_root_has_no_duplicate_component),
        ("strict JSON output works", strict_json_works),
    ):
        results.append(_check(name, fn))

    # The decisive check: a representative deck of every family must parse.
    try:
        import run_demo16

        machine = run_demo16.resolve_machine()
    except Exception:
        machine = None
    exe = parser_executable(machine)

    def representative_decks_parse() -> str:
        assert exe is not None, (
            "no nextnano++ binary found to validate deck syntax; a preflight PASS "
            "would not mean the renderer produces parseable decks"
        )
        database = database_for(exe)
        cases = cases16.load_cases(cases_path)
        picked = [next(c for c in cases if c.grading_profile == p)
                  for p in cases16.PROFILES]
        picked.append(next(c for c in cases if c.name == "maximum_overlap_linear"))
        with tempfile.TemporaryDirectory(prefix="demo16_pre_") as tmp:
            for case in picked:
                _g, profile, blocks, deck = demo16.build_case(cfg, case)
                result = demo16.parse_deck(
                    exe, database, Path(tmp) / case.case_id, deck, blocks["datafile"]
                )
                assert result["passed"], (
                    f"{case.case_id} ({case.grading_profile}): "
                    f"{result['failure_reason']}"
                )
        return f"{len(picked)} representative decks parsed by {exe.name}"

    results.append(_check("representative decks parse", representative_decks_parse))

    width = max(len(r["check"]) for r in results) + 2
    print("=" * (width + 34))
    print("  DEMO 16 PREFLIGHT")
    print("=" * (width + 34))
    for row in results:
        print(f"  [{row['status']:4}] {row['check']:<{width}} {row['detail']}")
    failed = [r for r in results if r["status"] == FAIL]
    print("=" * (width + 34))
    if failed:
        print(f"  DEMO 16 PREFLIGHT: FAIL ({len(failed)} of {len(results)})")
        for row in failed:
            print(f"    - {row['check']}: {row['detail']}")
        return 1
    print(f"  DEMO 16 PREFLIGHT: PASS ({len(results)} checks)")
    print("=" * (width + 34))
    return 0
