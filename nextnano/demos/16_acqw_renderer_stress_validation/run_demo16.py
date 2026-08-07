"""Demo 16 command line: ACQW renderer stress validation.

    python run_demo16.py --preflight    # solver-free self-test
    python run_demo16.py --syntax       # Level 1: render + --parse, all 20
    python run_demo16.py --structure    # Level 2: realized composition (licensed)
    python run_demo16.py --validate     # Levels 1 + 2
    python run_demo16.py --physics      # Level 3: selected cases (licensed)
    python run_demo16.py --analyze DIR  # re-analyse without solving

No default launches a licensed solve. ``--syntax`` runs anywhere nextnano++ is
installed, licensed or free, because ``--parse`` performs no physics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO14 = DEMO_DIR.parent / "14_absolute_chi2_graded_acqw_bo"
DEMO11 = DEMO_DIR.parent / "11_paper_validation_interband_chi2_acqw"
for path in (str(SHARED), str(DEMO14), str(DEMO11), str(DEMO_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import cases16  # noqa: E402
import demo14  # noqa: E402
import demo16  # noqa: E402
import preflight16  # noqa: E402
import runlog14  # noqa: E402


def resolve_machine():
    """Same resolver Demo 14 uses; no argument, or local config is ignored."""

    import demo_workflow as workflow

    return workflow.load_machine_config()


def results_root() -> Path:
    """``machine.results_root`` already ends in ``demo_runs``.

    Appending another one is what produced the ``demo_runs/demo_runs`` tree in
    the first Demo 14 gate; Demo 16 must not repeat it.
    """

    return Path(resolve_machine().results_root)


def new_run_dir() -> tuple[Path, str]:
    import datetime as dt
    import uuid

    facts = runlog14.git_facts(DEMO_DIR.parents[2])
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = uuid.uuid4().hex[:6]
    root = results_root() / demo16.DEMO_ID / f"demo16_{stamp}_{facts['git_commit_short']}_{run_id}"
    for sub in ("environment", "logs", "cases", "plots", "summaries"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def run_syntax(verbose: bool = False) -> int:
    """Level 1 over all 20 cases."""

    cfg = demo14.load_config()
    cases = cases16.load_cases(DEMO_DIR / cases16.CASES_FILENAME)
    try:
        machine = resolve_machine()
    except Exception:
        machine = None
    exe = preflight16.parser_executable(machine)
    database = preflight16.database_for(exe) if exe else None

    root, run_id = new_run_dir()
    print("=" * 78)
    print("  DEMO 16 LEVEL 1 -- SYNTAX VALIDATION")
    print("=" * 78)
    print(f"  RUN ID     : {run_id}")
    print(f"  RUN DIR    : {root}")
    print(f"  PARSER     : {exe or '<none found>'}")
    print(f"  CASES      : {len(cases)}")
    print("  NOTE       : --parse performs no physics and consumes no licence.")
    print("=" * 78)

    outcomes = []
    for case in cases:
        case_dir = root / "cases" / f"{case.case_id}_{case.name}"
        outcome = demo16.validate_case_level1(cfg, case, case_dir, exe, database)
        outcomes.append(outcome)
        mark = {"syntax_passed": "PASS", "syntax_failed": "FAIL",
                "structure_failed": "STRUCT-FAIL", "render_failed": "RENDER-FAIL",
                "syntax_unchecked": "SKIP"}.get(outcome.status, outcome.status)
        overlap = outcome.overlap.get("grades_overlap")
        print(f"  [{mark:<11}] {case.case_id} {case.name:<34} "
              f"{outcome.render_method:<15} peak_Al="
              f"{outcome.overlap.get('realized_peak_al_fraction', float('nan')):.4f}"
              f"{'  OVERLAP' if overlap else ''}")
        if outcome.failure_reason and verbose:
            print(f"                {outcome.failure_reason}")

    passed = sum(1 for o in outcomes if o.status == "syntax_passed")
    summary = {
        "run_id": run_id, "level": 1, "total_cases": len(cases),
        "passed": passed, "failed": len(cases) - passed,
        "cases": [o.as_record() for o in outcomes],
    }
    runlog14.write_json_atomic(root / "summaries" / "level1_syntax.json", summary)
    _write_summary_csv(root / "summaries" / "case_matrix.csv", outcomes)

    print("=" * 78)
    print(f"  DEMO 16 LEVEL 1: {passed}/{len(cases)} cases passed")
    for outcome in outcomes:
        if outcome.status != "syntax_passed":
            print(f"    - {outcome.case_id}: {outcome.status}: {outcome.failure_reason}")
    print("=" * 78)
    print(f"  Results: {root}")
    return 0 if passed == len(cases) else 1


def _write_summary_csv(path: Path, outcomes) -> None:
    header = (
        "case_id,name,status,render_method,peak_al_fraction,grades_overlap,"
        "nominal_plateau_exists,outer_barriers_present,four_interfaces_ordered,"
        "invariants_passed,parse_passed\n"
    )
    lines = []
    for o in outcomes:
        inv = o.invariants
        lines.append(
            f"{o.case_id},{o.name},{o.status},{o.render_method},"
            f"{o.overlap.get('realized_peak_al_fraction', '')},"
            f"{o.overlap.get('grades_overlap', '')},"
            f"{o.overlap.get('nominal_plateau_exists', '')},"
            f"{inv.get('left_outer_barrier_present') and inv.get('right_outer_barrier_present')},"
            f"{inv.get('four_interfaces_ordered', '')},"
            f"{inv.get('all_passed', '')},"
            f"{o.level1.get('passed', '')}\n"
        )
    runlog14.write_text_atomic(path, header + "".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_demo16.py",
        description="Demo 16 ACQW renderer / structure validation",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--syntax", action="store_true", help="Level 1")
    group.add_argument("--structure", action="store_true", help="Level 2 (licensed)")
    group.add_argument("--validate", action="store_true", help="Levels 1 + 2")
    group.add_argument("--physics", action="store_true", help="Level 3 (licensed)")
    group.add_argument("--analyze", metavar="RUN_DIR")
    group.add_argument("--write-cases", action="store_true",
                       help="regenerate validation_cases.yaml (deliberate act)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.write_cases:
        path = cases16.write_cases_file(DEMO_DIR / cases16.CASES_FILENAME)
        print(f"wrote {path}")
        return 0

    if args.preflight:
        return preflight16.run_preflight(verbose=args.verbose)

    if args.syntax:
        return run_syntax(verbose=args.verbose)

    if args.structure or args.validate or args.physics:
        print(
            "Level 2 and Level 3 require the licensed nextnano++ build.\n"
            "  The free build caps at 100 grid points; a Demo 16 production deck\n"
            "  is ~1000, and it cannot execute imported profiles at all.\n"
            "  Run --syntax here; run --structure/--physics on the work laptop."
        )
        try:
            machine = resolve_machine()
        except Exception as exc:
            print(f"  machine config: {type(exc).__name__}: {exc}")
            return 3
        if not getattr(machine, "run_solver", False):
            print("  This machine resolves run_solver=false, so nothing was run.")
            return 3
        print("  NOT YET IMPLEMENTED: Level 2/3 execution.")
        return 3

    if args.analyze:
        target = Path(args.analyze)
        summary = target / "summaries" / "level1_syntax.json"
        if not summary.is_file():
            print(f"No Demo 16 summary under {target}")
            return 1
        payload = json.loads(summary.read_text(encoding="utf-8"))
        print(f"Run {payload['run_id']}: {payload['passed']}/{payload['total_cases']} passed")
        for case in payload["cases"]:
            if case["status"] != "syntax_passed":
                print(f"  - {case['case_id']}: {case['status']}: {case['failure_reason']}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
