"""Command line for Demo 16C's four-case linear-grading experiment.

With no arguments this runs preflight.  Only ``--physics`` can launch a full
licensed solve; every other command is parser/structure-only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import uuid

DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
SHARED = DEMOS / "_shared"
DEMO11 = DEMOS / "11_paper_validation_interband_chi2_acqw"
DEMO14 = DEMOS / "14_absolute_chi2_graded_acqw_bo"
DEMO16 = DEMOS / "16_acqw_renderer_stress_validation"
DEMO16B = DEMOS / "16B_simple_acqw_grading_validation"
for path in (SHARED, DEMO14, DEMO11, DEMO16, DEMO16B, DEMO_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cases16c  # noqa: E402
import demo14  # noqa: E402
import demo16c  # noqa: E402
import preflight16c  # noqa: E402
import runlog14  # noqa: E402

RULE = "=" * 78


def resolve_machine():
    import demo_workflow as workflow
    return workflow.load_machine_config()


def _machine_or_none():
    try:
        return resolve_machine()
    except Exception:  # noqa: BLE001
        return None


def results_root() -> Path:
    """Resolve the shared demo_runs root without ever appending it twice."""

    machine = _machine_or_none()
    if machine is not None and getattr(machine, "results_root", None):
        return Path(machine.results_root)
    return DEMOS.parents[0] / "results" / "demo_runs"


def new_run_dir() -> tuple[Path, str]:
    facts = runlog14.git_facts(DEMO_DIR.parents[2])
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo16c_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = results_root() / demo16c.DEMO_ID / run_id
    for sub in ("cases", "plots"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def _seed_run(root: Path, run_id: str, mode: str, machine, exe, database,
              licence) -> dict:
    source_cases = DEMO_DIR / cases16c.CASES_FILENAME
    environment = {
        "run_id": run_id,
        "timestamp_utc": runlog14.utc_now(),
        "demo_id": demo16c.DEMO_ID,
        "demo16c_version": demo16c.DEMO_VERSION,
        "mode": mode,
        "nextnano_executable": str(exe) if exe else None,
        "nextnano_database": str(database) if database else None,
        "nextnano_license": str(licence) if licence else None,
        "machine_config_source": str(getattr(machine, "source_path", "")) or None,
        "run_solver_enabled": bool(getattr(machine, "run_solver", False)),
    }
    runlog14.write_json_atomic(root / "RUN_STATUS.json", {
        **environment, "status": "running", "cases_total": 4,
    })
    runlog14.write_text_atomic(
        root / cases16c.CASES_FILENAME,
        source_cases.read_text(encoding="utf-8"),
    )
    return environment


def run_levels(*, do_parse: bool, do_structure: bool, mode: str,
               selected_cases=None, verbose: bool = False):
    from preflight16 import database_for, license_for, parser_executable

    cfg = demo14.load_config()
    cases = list(selected_cases if selected_cases is not None else
                 cases16c.load_cases(DEMO_DIR / cases16c.CASES_FILENAME))
    machine = _machine_or_none()
    exe = parser_executable(machine)
    database = database_for(exe) if exe else None
    licence = license_for(machine)
    root, run_id = new_run_dir()
    environment = _seed_run(root, run_id, mode, machine, exe, database, licence)

    print(RULE)
    print(f"  DEMO 16C -- {mode.upper()}")
    print(RULE)
    print(f"  RUN DIR    : {root}")
    print(f"  EXECUTABLE : {exe or '<none found>'}")
    print(f"  CASES      : {len(cases)} (fixed geometry, linear grading only)")
    if do_structure:
        print("  NOTE       : --structure builds composition but does not solve physics.")
    else:
        print("  NOTE       : --parse checks syntax and does not solve physics.")
    print(RULE)

    outcomes = []
    for case in cases:
        case_dir = root / "cases" / case.case_id
        outcome = demo16c.run_case(
            cfg, case, case_dir, exe=exe, database=database,
            license_path=licence, do_parse=do_parse, do_structure=do_structure,
        )
        outcomes.append(outcome)
        comparison = (outcome.structure or {}).get("comparison") or {}
        extra = ""
        if comparison:
            extra = (
                f" max|dx|={comparison['max_absolute_al_fraction_difference']:.2e}"
                f" rms={comparison['rms_al_fraction_difference']:.2e}"
            )
        print(f"  [{outcome.status:<18}] {case.case_id} "
              f"L={case.left_grading_width_nm:.2f} "
              f"R={case.right_grading_width_nm:.2f}{extra}")
        if outcome.failure_reason and verbose:
            print(f"                         {outcome.failure_reason}")

    _write_plots(root, cfg, cases, outcomes)
    passed_states = {"structure_passed"} if do_structure else {"parser_passed"}
    passed = sum(outcome.status in passed_states for outcome in outcomes)
    runlog14.write_json_atomic(root / "summary.json", {
        **environment,
        "cases_total": len(outcomes),
        "cases_passed": passed,
        "cases_failed": len(outcomes) - passed,
        "cases": [outcome.as_record() for outcome in outcomes],
    })
    _write_summary_csv(root / "summary.csv", cases, outcomes)
    runlog14.write_json_atomic(root / "RUN_STATUS.json", {
        **environment,
        "status": "completed",
        "cases_total": len(outcomes),
        "cases_passed": passed,
        "cases_failed": len(outcomes) - passed,
    })
    _write_readme(root, environment, cases, outcomes)
    print(RULE)
    print(f"  RESULT: {passed}/{len(outcomes)} passed")
    print(f"  FILES : {root}")
    print(RULE)
    return (0 if passed == len(outcomes) else 1), root, outcomes


def _write_summary_csv(path: Path, cases, outcomes) -> None:
    header = (
        "case_id,status,requested_left_nm,realized_left_nm,requested_right_nm,"
        "realized_right_nm,left_position_error_nm,right_position_error_nm,"
        "max_abs_al_error,rms_al_error,expected_peak_al,realized_peak_al\n"
    )
    lines = []

    def fmt(value, spec=".6f"):
        return "" if value is None else format(value, spec)

    for case, outcome in zip(cases, outcomes):
        metric = (outcome.structure or {}).get("comparison") or {}
        lines.append(",".join([
            case.case_id,
            outcome.status,
            fmt(case.left_grading_width_nm),
            fmt(metric.get("realized_left_10_90_grading_width_nm")),
            fmt(case.right_grading_width_nm),
            fmt(metric.get("realized_right_10_90_grading_width_nm")),
            fmt(metric.get("left_interface_position_error_nm")),
            fmt(metric.get("right_interface_position_error_nm")),
            fmt(metric.get("max_absolute_al_fraction_difference"), ".3e"),
            fmt(metric.get("rms_al_fraction_difference"), ".3e"),
            fmt(metric.get("expected_peak_al_fraction")),
            fmt(metric.get("realized_peak_al_fraction")),
        ]) + "\n")
    runlog14.write_text_atomic(path, header + "".join(lines))


def _write_plots(root: Path, cfg, cases, outcomes) -> None:
    import plots
    import plots16c

    if not plots.plotting_available():
        print(f"  NOTE: plots skipped: {plots.unavailable_reason()}")
        return
    profiles = []
    for case, outcome in zip(cases, outcomes):
        if outcome.status == "render_failed":
            continue
        _geometry, profile, _blocks, _deck = demo16c.build_case(cfg, case)
        profiles.append({
            "case": case,
            "x_nm": profile.x_nm,
            "al_fraction": profile.al_fraction,
            "interfaces": profile.request["interfaces_nm"],
        })
        realized_x = realized_al = None
        realized_path = (outcome.structure or {}).get("realized_profile_path")
        if realized_path and Path(realized_path).is_file():
            realized_x, realized_al = _read_realized_csv(Path(realized_path))
        note = ("realized profile unavailable"
                if realized_x is None else "nextnano++ --structure output")
        plots16c.case_composition_figure(
            root / "cases" / case.case_id / "plots" / "composition.png",
            title=(f"{case.case_id}: linear grade left "
                   f"{case.left_grading_width_nm:.2f} nm, right "
                   f"{case.right_grading_width_nm:.2f} nm"),
            interfaces=profile.request["interfaces_nm"],
            intended_x_nm=profile.x_nm,
            intended_al=profile.al_fraction,
            realized_x_nm=realized_x,
            realized_al=realized_al,
            max_al_fraction=cases16c.AL_FRACTION,
            note=note,
        )
    if profiles:
        plots16c.all_intended_profiles_figure(
            root / "plots" / "all_four_intended_profiles.png", profiles
        )


def _read_realized_csv(path: Path):
    import numpy as np
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0], data[:, 1]


def _write_readme(root: Path, environment: dict, cases, outcomes) -> None:
    rows = ["| case | left 10-90 (nm) | right 10-90 (nm) | status |",
            "|---|---:|---:|---|"]
    rows.extend(
        f"| {case.case_id} | {case.left_grading_width_nm:.2f} | "
        f"{case.right_grading_width_nm:.2f} | {outcome.status} |"
        for case, outcome in zip(cases, outcomes)
    )
    runlog14.write_text_atomic(root / "README_RUN.md", "\n".join([
        f"# Demo 16C run {environment['run_id']}",
        "",
        "Fixed GaAs/AlGaAs ACQW: 7.1 / 1.8 / 2.9 nm, x_Al=0.55, "
        "0.05 nm active mesh. Linear grading only.",
        "",
        *rows,
        "",
        "Each case directory contains the exact request, intended profile, deck,",
        "parser transcript, and (when available) nextnano++ realized profile and",
        "comparison metrics. No command except --physics launches a full solve.",
        "",
    ]))


def run_physics(verbose: bool = False) -> int:
    selected = cases16c.physics_cases()
    machine = _machine_or_none()
    if machine is None or not getattr(machine, "run_solver", False):
        print("Demo 16C physics was not run: this machine is not configured for "
              "licensed nextnano++ solves.")
        return 3
    status, root, outcomes = run_levels(
        do_parse=True, do_structure=True, mode="physics",
        selected_cases=selected, verbose=verbose,
    )
    cfg = demo14.load_config()
    records = []
    for case, outcome in zip(selected, outcomes):
        case_dir = root / "cases" / case.case_id
        if outcome.status != "structure_passed":
            record = {"case_id": case.case_id, "passed": False, "skipped": True,
                      "failure_reason": outcome.failure_reason}
        else:
            record = demo16c.solve_case(cfg, case, case_dir, machine=machine)
            outcome.physics = record
            runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        records.append(record)
        analysis = record.get("analysis") or {}
        print(f"  [{'PHYS-OK' if record.get('passed') else 'PHYS-FAIL':<9}] "
              f"{case.case_id} E1={analysis.get('E_e1_eV')} "
              f"E2={analysis.get('E_e2_eV')} HH1={analysis.get('E_hh1_eV')} "
              f"HH2={analysis.get('E_hh2_eV')}")
    runlog14.write_json_atomic(root / "physics_summary.json", {
        "selected_cases": [c.case_id for c in selected], "cases": records,
        "passed": sum(bool(r.get("passed")) for r in records),
    })
    return 0 if status == 0 and all(r.get("passed") for r in records) else 1


def analyze_existing(path: Path) -> int:
    summary = Path(path) / "summary.json"
    if not summary.is_file():
        print(f"No Demo 16C summary at {summary}")
        return 1
    payload = json.loads(summary.read_text(encoding="utf-8"))
    print(f"Demo 16C {payload['run_id']}: "
          f"{payload['cases_passed']}/{payload['cases_total']} passed")
    for case in payload["cases"]:
        print(f"  {case['case_id']}: {case['status']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Demo 16C: minimal linear grading validation"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--syntax", action="store_true")
    group.add_argument("--structure", action="store_true")
    group.add_argument("--validate", action="store_true")
    group.add_argument("--physics", action="store_true")
    group.add_argument("--write-cases", action="store_true")
    group.add_argument("--analyze-existing", metavar="RUN_DIR")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.write_cases:
        print(cases16c.write_cases_file(DEMO_DIR / cases16c.CASES_FILENAME))
        return 0
    if args.syntax:
        return run_levels(do_parse=True, do_structure=False,
                          mode="syntax", verbose=args.verbose)[0]
    if args.structure:
        return run_levels(do_parse=False, do_structure=True,
                          mode="structure", verbose=args.verbose)[0]
    if args.validate:
        return run_levels(do_parse=True, do_structure=True,
                          mode="validate", verbose=args.verbose)[0]
    if args.physics:
        return run_physics(verbose=args.verbose)
    if args.analyze_existing:
        return analyze_existing(Path(args.analyze_existing))
    return preflight16c.run_preflight(verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
