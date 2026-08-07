"""CLI for Demo 16D. Only ``--physics`` can launch licensed full solves."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import subprocess
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

import cases16d  # noqa: E402
import demo14  # noqa: E402
import demo16d  # noqa: E402
import preflight16d  # noqa: E402
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
    machine = _machine_or_none()
    if machine is not None and getattr(machine, "results_root", None):
        return Path(machine.results_root)
    return DEMOS.parents[0] / "results" / "demo_runs"


def new_run_dir() -> tuple[Path, str]:
    facts = runlog14.git_facts(DEMO_DIR.parents[2])
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo16d_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = results_root() / demo16d.DEMO_ID / run_id
    for sub in ("cases", "plots", "summaries"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def _seed_run(root: Path, run_id: str, mode: str, machine, exe, database, licence,
              case_count: int) -> dict:
    environment = {
        "run_id": run_id,
        "timestamp_utc": runlog14.utc_now(),
        "demo_id": demo16d.DEMO_ID,
        "demo16d_version": demo16d.DEMO_VERSION,
        "mode": mode,
        "nextnano_executable": str(exe) if exe else None,
        "nextnano_database": str(database) if database else None,
        "nextnano_license": str(licence) if licence else None,
        "machine_config_source": str(getattr(machine, "source_path", "")) or None,
        "run_solver_enabled": bool(getattr(machine, "run_solver", False)),
    }
    runlog14.write_json_atomic(
        root / "RUN_STATUS.json",
        {**environment, "status": "running", "cases_total": case_count},
    )
    runlog14.write_text_atomic(
        root / cases16d.CASES_FILENAME,
        (DEMO_DIR / cases16d.CASES_FILENAME).read_text(encoding="utf-8"),
    )
    return environment


def run_levels(*, do_parse: bool, do_structure: bool, mode: str,
               selected_cases=None, verbose: bool = False):
    from preflight16 import database_for, license_for, parser_executable

    cfg = demo14.load_config()
    cases = list(selected_cases if selected_cases is not None else
                 cases16d.load_cases(DEMO_DIR / cases16d.CASES_FILENAME))
    machine = _machine_or_none()
    exe = parser_executable(machine)
    database = database_for(exe) if exe else None
    licence = license_for(machine)
    root, run_id = new_run_dir()
    environment = _seed_run(
        root, run_id, mode, machine, exe, database, licence, len(cases)
    )

    print(RULE)
    print(f"  DEMO 16D -- {mode.upper()}")
    print(RULE)
    print(f"  RUN DIR    : {root}")
    print(f"  EXECUTABLE : {exe or '<none found>'}")
    print(f"  CASES      : {len(cases)} (fixed, deterministic, linear only)")
    if mode == "physics":
        print("  NOTE       : parser + realized-composition gates precede every full solve.")
    elif do_structure:
        print("  NOTE       : composition construction only; no quantum solve.")
    else:
        print("  NOTE       : syntax parsing only; no quantum solve.")
    print(RULE)

    outcomes = []
    for case in cases:
        case_dir = root / "cases" / case.case_id
        outcome = demo16d.run_case(
            cfg, case, case_dir, exe=exe, database=database,
            license_path=licence, do_parse=do_parse, do_structure=do_structure,
        )
        outcomes.append(outcome)
        comparison = (outcome.structure or {}).get("comparison") or {}
        error = ""
        if comparison:
            error = (
                f" max|dx|={comparison['max_absolute_al_fraction_difference']:.2e}"
                f" rms={comparison['rms_al_fraction_difference']:.2e}"
            )
        w1, w2 = case.well_widths_nm()
        print(
            f"  [{outcome.status:<18}] {case.case_id} "
            f"{w1:.2f}/{case.central_barrier_nm:.2f}/{w2:.2f} nm "
            f"grades={case.left_grading_width_nm:.2f}/{case.right_grading_width_nm:.2f}"
            f"{' OVERLAP' if case.overlap else ''}{error}"
        )
        if outcome.failure_reason and verbose:
            print(f"                         {outcome.failure_reason}")

    _write_structure_plots(root, cfg, cases, outcomes)
    passed_states = {"structure_passed"} if do_structure else {"parser_passed"}
    passed = sum(outcome.status in passed_states for outcome in outcomes)
    summary = {
        **environment, "cases_total": len(outcomes), "cases_passed": passed,
        "cases_failed": len(outcomes) - passed,
        "cases": [outcome.as_record() for outcome in outcomes],
    }
    runlog14.write_json_atomic(root / "summary.json", summary)
    _write_structure_summary(root / "summaries" / "structure_summary.csv", cases, outcomes)
    runlog14.write_json_atomic(
        root / "RUN_STATUS.json",
        {**environment, "status": "completed", "cases_total": len(outcomes),
         "cases_passed": passed, "cases_failed": len(outcomes) - passed},
    )
    _write_run_readme(root, environment, cases, outcomes)
    print(RULE)
    print(f"  {'PRE-PHYSICS GATE' if mode == 'physics' else 'RESULT'}: {passed}/{len(outcomes)} passed")
    print(f"  FILES : {root}")
    print(RULE)
    return (0 if passed == len(outcomes) else 1), root, outcomes


def _fmt(value, spec=".6f") -> str:
    return "" if value is None else format(value, spec)


def _write_structure_summary(path: Path, cases, outcomes) -> None:
    fields = [
        "case_id", "status", "asymmetry_s", "requested_well_1_nm",
        "realized_well_1_nm", "requested_barrier_nm", "realized_barrier_nm",
        "requested_well_2_nm", "realized_well_2_nm", "realized_total_well_nm",
        "left_grading_nm", "right_grading_nm", "overlap", "render_method",
        "expected_peak_al", "realized_peak_al", "max_abs_al_error", "rms_al_error",
    ]
    lines = [",".join(fields) + "\n"]
    for case, outcome in zip(cases, outcomes):
        metric = (outcome.structure or {}).get("comparison") or {}
        geometry = metric.get("geometry") or {}
        w1, w2 = case.well_widths_nm()
        lines.append(",".join([
            case.case_id, outcome.status, _fmt(case.asymmetry_s), _fmt(w1),
            _fmt(geometry.get("realized_well_1_nm")), _fmt(case.central_barrier_nm),
            _fmt(geometry.get("realized_central_barrier_nm")), _fmt(w2),
            _fmt(geometry.get("realized_well_2_nm")),
            _fmt(geometry.get("realized_total_gaas_well_nm")),
            _fmt(case.left_grading_width_nm), _fmt(case.right_grading_width_nm),
            str(case.overlap).lower(), outcome.render_method,
            _fmt(metric.get("expected_peak_al_fraction")),
            _fmt(metric.get("realized_peak_al_fraction")),
            _fmt(metric.get("max_absolute_al_fraction_difference"), ".3e"),
            _fmt(metric.get("rms_al_fraction_difference"), ".3e"),
        ]) + "\n")
    runlog14.write_text_atomic(path, "".join(lines))


def _read_realized_csv(path: Path):
    import numpy as np
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0], data[:, 1]


def _write_structure_plots(root: Path, cfg, cases, outcomes) -> None:
    import plots
    import plots16d

    if not plots.plotting_available():
        print(f"  NOTE: plots skipped: {plots.unavailable_reason()}")
        return
    entries = []
    for case, outcome in zip(cases, outcomes):
        if outcome.status == "render_failed":
            continue
        _geometry, profile, _blocks, _deck = demo16d.build_case(cfg, case)
        entry = {
            "case": case, "x_nm": profile.x_nm,
            "al_fraction": profile.al_fraction,
            "interfaces": profile.request["interfaces_nm"],
            "overlap": demo16d.overlap_geometry(profile, case),
        }
        entries.append(entry)
        realized_x = realized_al = None
        realized_path = (outcome.structure or {}).get("realized_profile_path")
        if realized_path and Path(realized_path).is_file():
            realized_x, realized_al = _read_realized_csv(Path(realized_path))
        plots16d.composition_figure(
            root / "cases" / case.case_id / "plots" / "composition.png",
            title=(f"{case.case_id}: {case.name}, linear grades "
                   f"{case.left_grading_width_nm:.2f}/{case.right_grading_width_nm:.2f} nm"),
            interfaces=profile.request["interfaces_nm"],
            intended_x_nm=profile.x_nm, intended_al=profile.al_fraction,
            realized_x_nm=realized_x, realized_al=realized_al,
            max_al_fraction=cases16d.AL_FRACTION,
            note="realized profile unavailable" if realized_x is None else "nextnano++ realized composition",
            overlap_region=(entry["overlap"]["overlap_start_nm"],
                            entry["overlap"]["overlap_end_nm"]) if case.overlap else None,
        )
    by_id = {entry["case"].case_id: entry for entry in entries}
    if all(key in by_id for key in ("case_02", "case_01", "case_03")):
        plots16d.barrier_comparison(
            root / "plots" / "barrier_comparison.png",
            [by_id[key] for key in ("case_02", "case_01", "case_03")],
        )
    if all(key in by_id for key in ("case_04", "case_01", "case_05")):
        plots16d.asymmetry_comparison(
            root / "plots" / "asymmetry_comparison.png",
            [by_id[key] for key in ("case_04", "case_01", "case_05")],
        )
    if "case_07" in by_id:
        plots16d.overlap_comparison(
            root / "plots" / "overlap_profile.png", by_id["case_07"]
        )


def _write_run_readme(root: Path, environment: dict, cases, outcomes) -> None:
    rows = [
        "| case | wells/barrier (nm) | grades (nm) | overlap | status |",
        "|---|---:|---:|:---:|---|",
    ]
    for case, outcome in zip(cases, outcomes):
        w1, w2 = case.well_widths_nm()
        rows.append(
            f"| {case.case_id} | {w1:.2f} / {case.central_barrier_nm:.2f} / {w2:.2f} | "
            f"{case.left_grading_width_nm:.2f} / {case.right_grading_width_nm:.2f} | "
            f"{'yes' if case.overlap else 'no'} | {outcome.status} |"
        )
    runlog14.write_text_atomic(root / "README_RUN.md", "\n".join([
        f"# Demo 16D run {environment['run_id']}", "",
        "Seven fixed GaAs/AlGaAs geometry-validation cases; linear grading only.",
        "No parameter search or optimization is performed.", "", *rows, "",
        "Only --physics launches full licensed calculations. Raw quantum output uses",
        "short run-root paths p01, p02, p05 and p07.", "",
    ]))


def _physics_row(case, record) -> dict:
    analysis = record.get("analysis") or {}
    optical = record.get("optical") or {}
    w1, w2 = case.well_widths_nm()
    gate = (record.get("preanalysis_gate") or {}).get("quantum_outputs") or {}
    return {
        "case": case.case_id, "case_id": case.case_id,
        "description": case.name, "well_1_nm": w1,
        "central_barrier_nm": case.central_barrier_nm, "well_2_nm": w2,
        "left_grading_nm": case.left_grading_width_nm,
        "right_grading_nm": case.right_grading_width_nm,
        "overlap": case.overlap,
        "E1_eV": analysis.get("E_e1_eV"), "E2_eV": analysis.get("E_e2_eV"),
        "HH1_eV": analysis.get("E_hh1_eV"), "HH2_eV": analysis.get("E_hh2_eV"),
        "chi2_at_1550": optical.get("chi2_at_1550"),
        "chi2_units": optical.get("chi2_units"),
        "peak_wavelength_nm": optical.get("spectral_peak_wavelength_nm"),
        "detuning_from_1550_nm": optical.get("detuning_from_1550_nm"),
        "spectrum_path": optical.get("spectrum_path"),
        "input_deck_path": record.get("deck_path"),
        "raw_output_dir": record.get("raw_output_dir"),
        "quantum_output_paths": gate.get("resolved_artifacts"),
        "optical_settings_path": optical.get("analysis_settings_path"),
        "selected_states_path": optical.get("selected_states_path"),
    }


def _write_physics_optical_summary(root: Path, rows: list[dict]) -> None:
    import plots16d

    json_path = root / "summaries" / "physics_optical_summary.json"
    csv_path = root / "summaries" / "physics_optical_summary.csv"
    runlog14.write_json_atomic(json_path, {
        "target_wavelength_nm": 1550.0,
        "detuning_sign_convention": "peak_wavelength_nm - 1550_nm",
        "optimization_performed": False,
        "cases": rows,
    })
    fields = [
        "case", "description", "well_1_nm", "central_barrier_nm", "well_2_nm",
        "left_grading_nm", "right_grading_nm", "overlap", "E1_eV", "E2_eV",
        "HH1_eV", "HH2_eV", "chi2_at_1550", "chi2_units",
        "peak_wavelength_nm", "detuning_from_1550_nm", "spectrum_path",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    complete = [row for row in rows if row.get("chi2_at_1550") is not None]
    if complete:
        plots16d.physics_energy_summary(root / "plots" / "physics_summary.png", complete)
        plots16d.optical_comparison(
            root / "plots" / "chi2_wavelength_comparison.png", complete
        )
        plots16d.optical_at_1550(
            root / "plots" / "chi2_at_1550_comparison.png", complete
        )


def run_physics(verbose: bool = False) -> int:
    selected = cases16d.physics_cases()
    machine = _machine_or_none()
    if machine is None or not getattr(machine, "run_solver", False):
        print("Demo 16D physics was not run: this machine is not configured for licensed nextnano++ solves.")
        return 3
    gate_status, root, outcomes = run_levels(
        do_parse=True, do_structure=True, mode="physics",
        selected_cases=selected, verbose=verbose,
    )
    cfg = demo14.load_config()
    records = []
    rows = []
    for case, outcome in zip(selected, outcomes):
        case_dir = root / "cases" / case.case_id
        if outcome.status != "structure_passed":
            record = {
                "case_id": case.case_id, "passed": False, "skipped": True,
                "failure_stage": "structure_gate", "failure_reason": outcome.failure_reason,
            }
        else:
            command = demo16d.full_physics_command(cfg, case, case_dir, machine=machine)
            print(f"  [FULL-SOLVE] {case.case_id}")
            print(f"               command={subprocess.list2cmdline(command)}")
            record = demo16d.solve_case(cfg, case, case_dir, machine=machine)
            record["reported_full_physics_command"] = command
            if record.get("passed"):
                try:
                    record["optical"] = demo16d.analyse_optics(
                        cfg, case, case_dir, Path(record["raw_output_dir"])
                    )
                except Exception as exc:  # noqa: BLE001
                    record["passed"] = False
                    record["failure_stage"] = "optical_analysis"
                    record["failure_reason"] = f"{type(exc).__name__}: {exc}"
            outcome.physics = record
            runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
            runlog14.write_json_atomic(case_dir / "physics" / "physics_result.json", record)
        records.append(record)
        if record.get("passed"):
            rows.append(_physics_row(case, record))
        analysis = record.get("analysis") or {}
        optical = record.get("optical") or {}
        return_code = (record.get("solver") or {}).get("solver_return_code")
        state = "PHYS-OK" if record.get("passed") else "PHYS-FAIL"
        print(
            f"  [{state:<9}] {case.case_id} rc={return_code} "
            f"E1={analysis.get('E_e1_eV')} E2={analysis.get('E_e2_eV')} "
            f"HH1={analysis.get('E_hh1_eV')} HH2={analysis.get('E_hh2_eV')} "
            f"chi2(1550)={optical.get('chi2_at_1550')}"
        )
        if not record.get("passed"):
            print(f"               stage={record.get('failure_stage', 'unknown')}")
            print(f"               reason={record.get('failure_reason', 'not recorded')}")
    solved = sum(bool(record.get("passed")) for record in records)
    runlog14.write_json_atomic(root / "physics_summary.json", {
        "selected_cases": [case.case_id for case in selected],
        "cases": records, "passed": solved,
    })
    _write_physics_optical_summary(root, rows)
    runlog14.write_json_atomic(root / "RUN_STATUS.json", {
        "run_id": root.name, "demo_id": demo16d.DEMO_ID, "mode": "physics",
        "status": "completed", "cases_total": 4, "cases_passed": solved,
        "cases_failed": 4 - solved,
    })
    print(RULE)
    print(f"  PHYSICS + OPTICAL RESULT: {solved}/4 solved, gated and analysed")
    print(f"  SUMMARY: {root / 'summaries' / 'physics_optical_summary.csv'}")
    print(RULE)
    return 0 if gate_status == 0 and solved == 4 else 1


def analyze_existing(path: Path) -> int:
    """Reanalyse existing full-solver trees only; this function never invokes a solver."""

    root = Path(path).resolve()
    physics_path = root / "physics_summary.json"
    if not physics_path.is_file():
        summary = root / "summary.json"
        if not summary.is_file():
            print(f"No Demo 16D summary at {root}")
            return 1
        payload = json.loads(summary.read_text(encoding="utf-8"))
        print(f"Demo 16D {payload['run_id']}: {payload['cases_passed']}/{payload['cases_total']} validation cases passed")
        return 0
    cfg = demo14.load_config()
    cases = {case.case_id: case for case in cases16d.physics_cases()}
    payload = json.loads(physics_path.read_text(encoding="utf-8"))
    rows = []
    changed = False
    for record in payload.get("cases", []):
        case = cases.get(record.get("case_id"))
        if case is None or not record.get("passed"):
            continue
        if not record.get("optical"):
            record["optical"] = demo16d.analyse_optics(
                cfg, case, root / "cases" / case.case_id, Path(record["raw_output_dir"])
            )
            changed = True
        rows.append(_physics_row(case, record))
    if changed:
        runlog14.write_json_atomic(physics_path, payload)
    _write_physics_optical_summary(root, rows)
    print(f"Demo 16D existing run: {len(rows)}/4 physics cases available for optical comparison")
    print(f"Summary: {root / 'summaries' / 'physics_optical_summary.csv'}")
    return 0 if len(rows) == 4 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Demo 16D: incremental ACQW geometry and linear-grading validation"
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
        print(cases16d.write_cases_file(DEMO_DIR / cases16d.CASES_FILENAME))
        return 0
    if args.syntax:
        return run_levels(do_parse=True, do_structure=False, mode="syntax", verbose=args.verbose)[0]
    if args.structure:
        return run_levels(do_parse=False, do_structure=True, mode="structure", verbose=args.verbose)[0]
    if args.validate:
        return run_levels(do_parse=True, do_structure=True, mode="validate", verbose=args.verbose)[0]
    if args.physics:
        return run_physics(verbose=args.verbose)
    if args.analyze_existing:
        return analyze_existing(Path(args.analyze_existing))
    return preflight16d.run_preflight(verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
