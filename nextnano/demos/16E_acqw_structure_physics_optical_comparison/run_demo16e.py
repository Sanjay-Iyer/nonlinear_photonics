"""CLI for Demo 16E. Only ``--physics`` can launch licensed full solves.

Ten fixed structures, solved once each, then compared. No optimizer runs at any
point and nothing in this file reads a result in order to choose a parameter.
"""

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

import cases16e  # noqa: E402
import demo14  # noqa: E402
import demo16e  # noqa: E402
import preflight16e  # noqa: E402
import runlog14  # noqa: E402

RULE = "=" * 78
CASE_COUNT = cases16e.CASE_COUNT
MASTER_CSV = "demo16e_master_summary.csv"
MASTER_JSON = "demo16e_master_summary.json"

#: Master-summary column order. Written explicitly so the CSV is stable across
#: runs and readable top to bottom: structure, then composition, then states,
#: then localization, then optics.
MASTER_FIELDS = [
    "case", "description", "representation",
    "well_1_nm", "central_barrier_nm", "well_2_nm", "asymmetry_s",
    "left_grading_nm", "right_grading_nm", "overlap",
    "realized_peak_xAl", "max_composition_error", "rms_composition_error",
    "E1_eV", "E2_eV", "HH1_eV", "HH2_eV",
    "E2_minus_E1_meV", "HH1_minus_HH2_meV",
    "transition_e1_hh1_eV", "transition_e2_hh2_eV",
    "delta_E1_meV_vs_reference", "delta_E2_meV_vs_reference",
    "delta_HH1_meV_vs_reference", "delta_HH2_meV_vs_reference",
]
for _state in demo16e.STATE_LABELS:
    MASTER_FIELDS += [
        f"{_state}_left_probability", f"{_state}_barrier_probability",
        f"{_state}_right_probability", f"{_state}_outside_probability",
        f"{_state}_localization",
    ]
MASTER_FIELDS += [
    "chi2_at_1550", "peak_chi2", "peak_wavelength_nm", "detuning_from_1550_nm",
    "chi2_units", "reference_case", "spectrum_path", "wavefunction_csv_path",
    "raw_output_dir",
]


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
    run_id = f"demo16e_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = results_root() / demo16e.DEMO_ID / run_id
    for sub in ("cases", "plots", "summaries"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def _seed_run(root: Path, run_id: str, mode: str, machine, exe, database, licence,
              case_count: int) -> dict:
    environment = {
        "run_id": run_id,
        "timestamp_utc": runlog14.utc_now(),
        "demo_id": demo16e.DEMO_ID,
        "demo16e_version": demo16e.DEMO_VERSION,
        "mode": mode,
        "optimization_performed": False,
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
        root / cases16e.CASES_FILENAME,
        (DEMO_DIR / cases16e.CASES_FILENAME).read_text(encoding="utf-8"),
    )
    return environment


# ---------------------------------------------------------------------------
# Structure levels
# ---------------------------------------------------------------------------


def run_levels(*, do_parse: bool, do_structure: bool, mode: str,
               selected_cases=None, verbose: bool = False):
    from preflight16 import database_for, license_for, parser_executable

    cfg = demo14.load_config()
    cases = list(selected_cases if selected_cases is not None else
                 cases16e.load_cases(DEMO_DIR / cases16e.CASES_FILENAME))
    machine = _machine_or_none()
    exe = parser_executable(machine)
    database = database_for(exe) if exe else None
    licence = license_for(machine)
    root, run_id = new_run_dir()
    environment = _seed_run(
        root, run_id, mode, machine, exe, database, licence, len(cases)
    )

    print(RULE)
    print(f"  DEMO 16E -- {mode.upper()}")
    print(RULE)
    print(f"  RUN DIR    : {root}")
    print(f"  EXECUTABLE : {exe or '<none found>'}")
    print(f"  CASES      : {len(cases)} (fixed, deterministic, no optimization)")
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
        outcome = demo16e.run_case(
            cfg, case, case_dir, exe=exe, database=database,
            license_path=licence, do_parse=do_parse, do_structure=do_structure,
        )
        outcomes.append(outcome)
        comparison = (outcome.structure or {}).get("comparison") or {}
        error = ""
        if comparison:
            error = (
                f" max|dx|={comparison['gated_max_absolute_al_fraction_difference']:.2e}"
                f" rms={comparison['gated_rms_al_fraction_difference']:.2e}"
            )
        w1, w2 = case.well_widths_nm()
        print(
            f"  [{outcome.status:<22}] {case.case_id} "
            f"{w1:.2f}/{case.central_barrier_nm:.2f}/{w2:.2f} nm "
            f"grades={case.left_grading_width_nm:.2f}/{case.right_grading_width_nm:.2f} "
            f"{outcome.representation or case.expected_representation}"
            f"{' OVERLAP' if case.overlap else ''}{error}"
        )
        if outcome.failure_reason and verbose:
            print(f"                           {outcome.failure_reason}")

    _write_structure_plots(root, cfg, cases, outcomes)
    passed_states = {"structure_passed"} if do_structure else {"parser_passed"}
    passed = sum(outcome.status in passed_states for outcome in outcomes)
    summary = {
        **environment, "cases_total": len(outcomes), "cases_passed": passed,
        "cases_failed": len(outcomes) - passed,
        "cases": [outcome.as_record() for outcome in outcomes],
    }
    runlog14.write_json_atomic(root / "summary.json", summary)
    _write_structure_summary(
        root / "summaries" / "structure_summary.csv", cases, outcomes
    )
    runlog14.write_json_atomic(
        root / "RUN_STATUS.json",
        {**environment, "status": "completed", "cases_total": len(outcomes),
         "cases_passed": passed, "cases_failed": len(outcomes) - passed},
    )
    _write_run_readme(root, environment, cases, outcomes)
    print(RULE)
    label = "PRE-PHYSICS GATE" if mode == "physics" else "RESULT"
    print(f"  {label}: {passed}/{len(outcomes)} passed")
    print(f"  FILES : {root}")
    print(RULE)
    return (0 if passed == len(outcomes) else 1), root, outcomes


def _fmt(value, spec=".6f") -> str:
    return "" if value is None else format(value, spec)


def _write_structure_summary(path: Path, cases, outcomes) -> None:
    fields = [
        "case_id", "name", "status", "representation", "asymmetry_s",
        "requested_well_1_nm", "realized_well_1_nm",
        "requested_barrier_nm", "realized_barrier_nm",
        "requested_well_2_nm", "realized_well_2_nm", "realized_total_well_nm",
        "requested_left_grading_nm", "requested_right_grading_nm",
        "realized_left_grading_nm", "realized_right_grading_nm",
        "overlap", "render_method", "expected_peak_al", "realized_peak_al",
        "max_abs_al_error", "rms_al_error", "gated_max_abs_al_error",
    ]
    lines = [",".join(fields) + "\n"]
    for case, outcome in zip(cases, outcomes):
        metric = (outcome.structure or {}).get("comparison") or {}
        geometry = metric.get("geometry") or {}
        realized = {
            row["interface"]: row.get("realized_width_10_90_nm")
            for row in metric.get("realized_interface_metrics") or []
        }
        w1, w2 = case.well_widths_nm()
        lines.append(",".join([
            case.case_id, case.name, outcome.status,
            outcome.representation or case.expected_representation,
            _fmt(case.asymmetry_s), _fmt(w1),
            _fmt(geometry.get("realized_well_1_nm")), _fmt(case.central_barrier_nm),
            _fmt(geometry.get("realized_central_barrier_nm")), _fmt(w2),
            _fmt(geometry.get("realized_well_2_nm")),
            _fmt(geometry.get("realized_total_gaas_well_nm")),
            _fmt(case.left_grading_width_nm), _fmt(case.right_grading_width_nm),
            _fmt(realized.get("central_gaas_to_algaas")),
            _fmt(realized.get("central_algaas_to_gaas")),
            str(case.overlap).lower(), outcome.render_method,
            _fmt(metric.get("expected_peak_al_fraction")),
            _fmt(metric.get("realized_peak_al_fraction")),
            _fmt(metric.get("max_absolute_al_fraction_difference"), ".3e"),
            _fmt(metric.get("rms_al_fraction_difference"), ".3e"),
            _fmt(metric.get("gated_max_absolute_al_fraction_difference"), ".3e"),
        ]) + "\n")
    runlog14.write_text_atomic(path, "".join(lines))


def _read_two_column_csv(path: Path):
    import numpy as np
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0], data[:, 1]


def _profile_entries(cfg, cases, outcomes) -> list[dict]:
    """Intended profile plus realized profile per case, for every figure."""

    entries = []
    for case, outcome in zip(cases, outcomes):
        if outcome.status == "render_failed":
            continue
        _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
        realized_x = realized_al = None
        realized_path = (outcome.structure or {}).get("realized_profile_path")
        if realized_path and Path(realized_path).is_file():
            realized_x, realized_al = _read_two_column_csv(Path(realized_path))
        entries.append({
            "case": case,
            "x_nm": profile.x_nm,
            "al_fraction": profile.al_fraction,
            "interfaces": profile.request["interfaces_nm"],
            "realized_x_nm": realized_x,
            "realized_al": realized_al,
            "overlap": demo16e.overlap_geometry(profile, case),
        })
    return entries


def _write_structure_plots(root: Path, cfg, cases, outcomes) -> None:
    import plots
    import plots16e

    if not plots.plotting_available():
        print(f"  NOTE: plots skipped: {plots.unavailable_reason()}")
        return
    entries = _profile_entries(cfg, cases, outcomes)
    for entry in entries:
        case = entry["case"]
        plots16e.composition_figure(
            root / "cases" / case.case_id / "plots" / "composition.png",
            title=plots16e.case_title(case, "Composition"),
            interfaces=entry["interfaces"],
            intended_x_nm=entry["x_nm"], intended_al=entry["al_fraction"],
            realized_x_nm=entry["realized_x_nm"], realized_al=entry["realized_al"],
            max_al_fraction=cases16e.AL_FRACTION,
            note=("realized profile unavailable" if entry["realized_x_nm"] is None
                  else f"nextnano++ realized composition ({case.expected_representation})"),
        )
    if entries:
        plots16e.composition_all_cases(root / "plots" / "composition_all_cases.png",
                                       entries)


def _write_run_readme(root: Path, environment: dict, cases, outcomes) -> None:
    rows = [
        "| case | name | wells/barrier (nm) | grades (nm) | representation | overlap | status |",
        "|---|---|---:|---:|---|:---:|---|",
    ]
    for case, outcome in zip(cases, outcomes):
        w1, w2 = case.well_widths_nm()
        grades = ("abrupt" if case.is_abrupt else
                  f"{case.left_grading_width_nm:.2f} / {case.right_grading_width_nm:.2f}")
        rows.append(
            f"| {case.case_id} | {case.name} | "
            f"{w1:.2f} / {case.central_barrier_nm:.2f} / {w2:.2f} | {grades} | "
            f"{outcome.representation or case.expected_representation} | "
            f"{'yes' if case.overlap else 'no'} | {outcome.status} |"
        )
    runlog14.write_text_atomic(root / "README_RUN.md", "\n".join([
        f"# Demo 16E run {environment['run_id']}", "",
        "Ten fixed GaAs/AlGaAs structures compared through composition, quantum",
        "states, wavefunction localization and the production absolute chi2",
        "response near 1550 nm. No optimization is performed and no case is",
        "selected as best.", "", *rows, "",
        "Only --physics launches full licensed calculations. Raw quantum output",
        "uses the short run-root paths p01 .. p10.", "",
    ]))


# ---------------------------------------------------------------------------
# Physics + comparison
# ---------------------------------------------------------------------------


def _summary_payload(rows: list[dict], reports: dict) -> dict:
    return {
        "demo_id": demo16e.DEMO_ID,
        "demo16e_version": demo16e.DEMO_VERSION,
        "target_wavelength_nm": demo16e.TARGET_WAVELENGTH_NM,
        "detuning_sign_convention": "peak_wavelength_nm - 1550_nm",
        "localization_convention": demo16e.LOCALIZATION_CONVENTION,
        "hole_energy_convention": demo16e.HOLE_ENERGY_CONVENTION,
        "reference_case": cases16e.REFERENCE_CASE_ID,
        "optimization_performed": False,
        "cases_reported": len(rows),
        "cases": rows,
        **reports,
    }


def _write_master_summary(root: Path, rows: list[dict], reports: dict) -> None:
    summaries = root / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    runlog14.write_json_atomic(summaries / MASTER_JSON, _summary_payload(rows, reports))
    with (summaries / MASTER_CSV).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=MASTER_FIELDS, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
    for name, payload in reports.items():
        if payload:
            runlog14.write_json_atomic(summaries / f"{name}.json", payload)


def _comparison_reports(cfg, rows: list[dict]) -> dict:
    """Abrupt-vs-graded and native-vs-imported, when both members are present."""

    by_case = {row["case"]: row for row in rows}
    reports: dict = {}

    graded_id, abrupt_id = cases16e.abrupt_vs_graded_pair()
    if graded_id in by_case and abrupt_id in by_case:
        reports["abrupt_vs_graded"] = demo16e.abrupt_vs_graded_report(
            by_case[graded_id], by_case[abrupt_id]
        )

    native_id, imported_id = cases16e.equivalence_pair()
    if native_id in by_case and imported_id in by_case:
        cases = {case.case_id: case for case in cases16e.all_cases()}
        _g, native_profile, _b, _d = demo16e.build_case(cfg, cases[native_id])
        _g, imported_profile, _b, _d = demo16e.build_case(cfg, cases[imported_id])
        reports["native_vs_imported_equivalence"] = demo16e.equivalence_report(
            by_case[native_id], by_case[imported_id],
            demo16e.composition_difference(native_profile, imported_profile),
        )
    return reports


def _write_comparison_plots(root: Path, cfg, rows: list[dict], reports: dict) -> None:
    import plots
    import plots16e

    if not plots.plotting_available():
        print(f"  NOTE: plots skipped: {plots.unavailable_reason()}")
        return
    plots_dir = root / "plots"
    plots16e.energy_levels_all_cases(plots_dir / "energy_levels_all_cases.png", rows)
    plots16e.energy_shifts_vs_reference(
        plots_dir / "energy_shifts_vs_reference.png", rows,
        cases16e.REFERENCE_CASE_ID,
    )
    plots16e.localization_all_cases(
        plots_dir / "wavefunction_localization_all_cases.png", rows
    )
    plots16e.chi2_wavelength_all_cases(
        plots_dir / "chi2_wavelength_all_cases.png", rows
    )
    plots16e.chi2_wavelength_grouped(
        plots_dir / "chi2_wavelength_grouped.png", rows
    )
    plots16e.chi2_at_1550_all_cases(plots_dir / "chi2_at_1550_all_cases.png", rows)
    plots16e.peak_wavelength_and_detuning(
        plots_dir / "peak_wavelength_and_detuning.png", rows
    )

    by_case = {row["case"]: row for row in rows}
    graded_id, abrupt_id = cases16e.abrupt_vs_graded_pair()
    if reports.get("abrupt_vs_graded"):
        cases = {case.case_id: case for case in cases16e.all_cases()}
        profiles = {}
        for case_id in (graded_id, abrupt_id):
            _g, profile, _b, _d = demo16e.build_case(cfg, cases[case_id])
            profiles[case_id] = {
                "x_nm": profile.x_nm, "al_fraction": profile.al_fraction,
                "interfaces": profile.request["interfaces_nm"],
            }
        plots16e.abrupt_vs_graded(
            plots_dir / "abrupt_vs_graded_comparison.png",
            by_case[graded_id], by_case[abrupt_id], profiles,
        )
    native_id, imported_id = cases16e.equivalence_pair()
    if reports.get("native_vs_imported_equivalence"):
        plots16e.native_vs_imported(
            plots_dir / "native_vs_imported_equivalence.png",
            reports["native_vs_imported_equivalence"],
            by_case[native_id], by_case[imported_id],
        )


def _write_wavefunction_plots(root: Path, cfg, case, record) -> None:
    import plots
    import plots16e

    waves = record.pop("_wavefunctions", None)
    if waves is None or not plots.plotting_available():
        return
    _geometry, profile, _blocks, _deck = demo16e.build_case(cfg, case)
    localization = (record.get("localization") or {}).get("by_state") or {}
    plots16e.wavefunction_figure(
        root / "cases" / case.case_id / "plots" / "wavefunctions.png",
        title=plots16e.case_title(case, "Band Edges and Wavefunctions"),
        interfaces=profile.request["interfaces_nm"],
        intended_x_nm=profile.x_nm, intended_al=profile.al_fraction,
        band_position_nm=waves.band_position_nm, band_edges=waves.band_edges,
        state_x_nm=waves.position_nm,
        electron_energies_eV=waves.electron_energies_eV,
        electron_densities=waves.electron_densities,
        hole_energies_eV=waves.hole_energies_eV,
        hole_densities=waves.hole_densities,
        localization=localization,
        max_al_fraction=cases16e.AL_FRACTION,
    )


def _post_solve_analysis(cfg, case, case_dir: Path, record: dict) -> dict:
    """Localization and optics for one completed solve; both or neither."""

    raw = Path(record["raw_output_dir"])
    try:
        localization, waves = demo16e.localization(cfg, raw, demo16e.build_case(cfg, case)[1])
    except Exception as exc:  # noqa: BLE001
        record["passed"] = False
        record["failure_stage"] = "localization"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
        return record
    record["localization"] = localization
    record["_wavefunctions"] = waves
    record["wavefunction_csv_path"] = str(demo16e.write_wavefunction_csv(
        Path(case_dir) / "physics" / "wavefunctions.csv", waves
    ))
    if not localization["checks"]["passed"]:
        failed = [key for key, value in localization["checks"].items()
                  if key != "passed" and not value]
        record["passed"] = False
        record["failure_stage"] = "localization_checks"
        record["failure_reason"] = f"localization checks failed: {failed}"
        return record
    try:
        record["optical"] = demo16e.analyse_optics(cfg, case, case_dir, raw)
    except Exception as exc:  # noqa: BLE001
        record["passed"] = False
        record["failure_stage"] = "optical_analysis"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
    return record


def run_physics(verbose: bool = False) -> int:
    cases = cases16e.load_cases(DEMO_DIR / cases16e.CASES_FILENAME)
    machine = _machine_or_none()
    if machine is None or not getattr(machine, "run_solver", False):
        print(
            "Demo 16E physics was not run: this machine is not configured for "
            "licensed nextnano++ solves."
        )
        return 3
    gate_status, root, outcomes = run_levels(
        do_parse=True, do_structure=True, mode="physics",
        selected_cases=cases, verbose=verbose,
    )
    cfg = demo14.load_config()
    records, rows = [], []
    for case, outcome in zip(cases, outcomes):
        case_dir = root / "cases" / case.case_id
        if outcome.status != "structure_passed":
            record = {
                "case_id": case.case_id, "passed": False, "skipped": True,
                "failure_stage": "structure_gate",
                "failure_reason": outcome.failure_reason,
            }
        else:
            command = demo16e.full_physics_command(cfg, case, case_dir, machine=machine)
            print(f"  [FULL-SOLVE] {case.case_id} ({case.expected_representation})")
            print(f"               command={subprocess.list2cmdline(command)}")
            record = demo16e.solve_case(cfg, case, case_dir, machine=machine)
            record["reported_full_physics_command"] = command
            if record.get("passed"):
                record = _post_solve_analysis(cfg, case, case_dir, record)
                _write_wavefunction_plots(root, cfg, case, record)
            outcome.physics = {k: v for k, v in record.items()
                               if not k.startswith("_")}
            runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
            runlog14.write_json_atomic(
                case_dir / "physics" / "physics_result.json", outcome.physics
            )
        record.pop("_wavefunctions", None)
        records.append(record)
        if record.get("passed"):
            comparison = (outcome.structure or {}).get("comparison") or {}
            rows.append(demo16e.master_row(
                case, record, comparison,
                outcome.representation or case.expected_representation,
            ))
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
        "selected_cases": [case.case_id for case in cases],
        "cases": records, "passed": solved,
    })
    rows = demo16e.add_reference_shifts(rows)
    reports = _comparison_reports(cfg, rows)
    _write_master_summary(root, rows, reports)
    _write_comparison_plots(root, cfg, rows, reports)
    runlog14.write_json_atomic(root / "RUN_STATUS.json", {
        "run_id": root.name, "demo_id": demo16e.DEMO_ID, "mode": "physics",
        "status": "completed", "cases_total": CASE_COUNT, "cases_passed": solved,
        "cases_failed": CASE_COUNT - solved,
    })
    _print_physics_epilogue(root, rows, reports, solved)
    return 0 if gate_status == 0 and solved == CASE_COUNT else 1


def _print_physics_epilogue(root: Path, rows, reports, solved: int) -> None:
    print(RULE)
    print(f"  PHYSICS + OPTICAL RESULT: {solved}/{CASE_COUNT} solved, gated and analysed")
    equivalence = reports.get("native_vs_imported_equivalence")
    if equivalence:
        verdict = "PASS" if equivalence["checks"]["passed"] else "FAIL"
        failed = [key for key, value in equivalence["checks"].items()
                  if key != "passed" and not value]
        print(f"  NATIVE vs IMPORTED EQUIVALENCE: {verdict}"
              + (f" -- {failed}" if failed else ""))
    pair = reports.get("abrupt_vs_graded")
    if pair:
        shifts = pair["energy_shifts_graded_minus_abrupt_meV"]
        print("  ABRUPT vs GRADED (graded - abrupt): "
              + ", ".join(f"{k.replace('delta_', '').replace('_meV', '')}="
                          f"{'n/a' if v is None else format(v, '+.2f')} meV"
                          for k, v in shifts.items()))
    print(f"  SUMMARY: {root / 'summaries' / MASTER_CSV}")
    print(f"  PLOTS  : {root / 'plots'}")
    print(RULE)


# ---------------------------------------------------------------------------
# Reanalysis
# ---------------------------------------------------------------------------


def analyze_existing(path: Path) -> int:
    """Rebuild every table and figure from an existing run; never runs a solver."""

    root = Path(path).resolve()
    physics_path = root / "physics_summary.json"
    if not physics_path.is_file():
        summary = root / "summary.json"
        if not summary.is_file():
            print(f"No Demo 16E summary at {root}")
            return 1
        payload = json.loads(summary.read_text(encoding="utf-8"))
        print(f"Demo 16E {payload['run_id']}: "
              f"{payload['cases_passed']}/{payload['cases_total']} validation cases passed")
        return 0
    cfg = demo14.load_config()
    cases = {case.case_id: case for case in
             cases16e.load_cases(DEMO_DIR / cases16e.CASES_FILENAME)}
    payload = json.loads(physics_path.read_text(encoding="utf-8"))
    rows, changed = [], False
    for record in payload.get("cases", []):
        case = cases.get(record.get("case_id"))
        if case is None or not record.get("passed"):
            continue
        case_dir = root / "cases" / case.case_id
        if not record.get("localization") or not record.get("optical"):
            record = _post_solve_analysis(cfg, case, case_dir, record)
            _write_wavefunction_plots(root, cfg, case, record)
            record.pop("_wavefunctions", None)
            changed = True
        comparison = _stored_comparison(case_dir)
        representation = _stored_representation(case_dir, case)
        rows.append(demo16e.master_row(case, record, comparison, representation))
    if changed:
        runlog14.write_json_atomic(physics_path, payload)
    rows = demo16e.add_reference_shifts(rows)
    reports = _comparison_reports(cfg, rows)
    _write_master_summary(root, rows, reports)
    _write_comparison_plots(root, cfg, rows, reports)
    print(f"Demo 16E existing run: {len(rows)}/{CASE_COUNT} physics cases "
          "available for comparison")
    print(f"Summary: {root / 'summaries' / MASTER_CSV}")
    return 0 if len(rows) == CASE_COUNT else 1


def _stored_comparison(case_dir: Path) -> dict:
    path = Path(case_dir) / "comparison_metrics.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _stored_representation(case_dir: Path, case) -> str:
    path = Path(case_dir) / "case_result.json"
    if path.is_file():
        stored = json.loads(path.read_text(encoding="utf-8")).get("representation")
        if stored:
            return str(stored)
    return case.expected_representation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Demo 16E: ten fixed ACQW structures compared through composition, "
            "quantum states, localization and absolute chi2 near 1550 nm"
        )
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
        print(cases16e.write_cases_file(DEMO_DIR / cases16e.CASES_FILENAME))
        return 0
    if args.syntax:
        return run_levels(do_parse=True, do_structure=False, mode="syntax",
                          verbose=args.verbose)[0]
    if args.structure:
        return run_levels(do_parse=False, do_structure=True, mode="structure",
                          verbose=args.verbose)[0]
    if args.validate:
        return run_levels(do_parse=True, do_structure=True, mode="validate",
                          verbose=args.verbose)[0]
    if args.physics:
        return run_physics(verbose=args.verbose)
    if args.analyze_existing:
        return analyze_existing(Path(args.analyze_existing))
    return preflight16e.run_preflight(verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
