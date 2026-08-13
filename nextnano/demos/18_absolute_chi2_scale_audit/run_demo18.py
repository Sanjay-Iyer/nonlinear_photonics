"""CLI for Demo 18: one licensed solve, many explicit scale conventions."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import shutil
import sys
import traceback
import uuid
from typing import Any, Mapping, Sequence

DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
REPO_ROOT = DEMO_DIR.parents[2]
for dependency in (
    DEMO_DIR,
    DEMOS / "_shared",
    DEMOS / "11_paper_validation_interband_chi2_acqw",
    DEMOS / "14_absolute_chi2_graded_acqw_bo",
    DEMOS / "16_acqw_renderer_stress_validation",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import numpy as np
import yaml

import cases18
import config18
import demo18
import demo16b
import demo16e
import demo_workflow
import runlog14
import solver14

RULE = "=" * 78


class DebugLog:
    """Append-only, immediately flushed diagnostic record for work-laptop runs."""

    def __init__(self, path: Path, *, verbose: bool = False):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        self.path.write_text("", encoding="utf-8")

    def line(self, text: object = "") -> None:
        value = str(text)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(value + "\n")
        if self.verbose:
            print(value)

    def section(self, title: str) -> None:
        self.line("")
        self.line(RULE)
        self.line(title)
        self.line(RULE)

    def json(self, value: object) -> None:
        self.line(json.dumps(runlog14.json_safe(value), indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Demo 18: audit absolute chi2 conventions with one fixed licensed "
            "nextnano++ solve"
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--physics", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def results_root(machine: Any | None) -> Path:
    if machine is not None and getattr(machine, "results_root", None):
        return Path(machine.results_root)
    return REPO_ROOT / "nextnano" / "results" / "demo_runs"


def new_run_directory(machine: Any | None) -> tuple[Path, str]:
    facts = runlog14.git_facts(REPO_ROOT)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo18_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = results_root(machine) / cases18.DEMO_ID / run_id
    for name in (
        "inputs", "solver", "logs", "summaries", "summaries/spectra",
        "plots", "config_snapshot", "reference_case",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root, run_id


def _write_json(path: Path, payload: object) -> Path:
    return runlog14.write_json_atomic(Path(path), runlog14.json_safe(payload))


def _write_yaml(path: Path, payload: object) -> Path:
    return runlog14.write_text_atomic(
        Path(path), yaml.safe_dump(runlog14.json_safe(payload), sort_keys=False)
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return path
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _copy_solver_logs(case_dir: Path, run_root: Path) -> None:
    source = Path(case_dir) / "physics" / "logs"
    if not source.is_dir():
        return
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, run_root / "logs" / f"solver_{item.name}")


def _output_inventory(raw: Path, limit: int = 500) -> list[dict[str, Any]]:
    raw = Path(raw)
    if not raw.exists():
        return []
    rows = []
    for item in sorted(path for path in raw.rglob("*") if path.is_file())[:limit]:
        rows.append({
            "path": str(item.relative_to(raw)),
            "bytes": item.stat().st_size,
        })
    return rows


def _save_spectrum(root: Path, item: demo18.EvaluatedCase) -> Path:
    path = root / "summaries" / "spectra" / f"{item.row['case_id']}_chi2.csv"
    np.savetxt(
        path,
        np.column_stack(
            [item.wavelength_nm, item.chi2.real, item.chi2.imag, np.abs(item.chi2)]
        ),
        delimiter=",",
        header="wavelength_nm,chi2_real,chi2_imag,chi2_magnitude",
        comments="",
    )
    return path


def _log_state_quantities(log: DebugLog, quantities: Mapping[str, Any]) -> None:
    log.section("PARSED STATES")
    for key in (
        "Ee1_eV", "Ee2_eV", "Ehh1_eV", "Ehh2_eV",
        "E1_minus_HH1_eV", "E2_minus_HH2_eV",
        "electron_orthonormality_error", "heavy_hole_orthonormality_error",
    ):
        log.line(f"{key} = {quantities[key]}")
    log.section("MATRIX ELEMENTS")
    log.line("electron-hole overlap matrix")
    log.json(quantities["electron_hole_overlap_matrix"])
    log.line("electron z matrix (nm)")
    log.json(quantities["electron_z_matrix_nm"])
    log.line("heavy-hole z matrix (nm)")
    log.json(quantities["heavy_hole_z_matrix_nm"])


def _final_terminal_summary(
    root: Path,
    rows: Sequence[Mapping[str, Any]],
    convergence: Sequence[Mapping[str, Any]],
    prefactor_residual: float,
) -> None:
    by_id = {row["case_id"]: row for row in rows}
    a = by_id["A_baseline"]
    b = by_id["B_two_wells_Nz"]
    c = by_id["C_large_kmax"]
    d = by_id["D_Nz_plus_large_kmax"]
    print(RULE)
    print("DEMO 18 COMPLETE")
    print(RULE)
    print("\nReference structure:\n  7.1 / 1.8 / 2.9 nm abrupt ACQW")
    print("\nSolver:\n  PASS")
    print("\nBaseline:")
    print(f"  chi2(1550) = {a['chi2_at_1550_pm_per_V']:.6g} pm/V")
    print(f"  peak        = {a['peak_chi2_pm_per_V']:.6g} pm/V @ "
          f"{a['peak_wavelength_nm']:.1f} nm")
    print("\nNz = 2/30 nm:")
    print(f"  chi2(1550) = {b['chi2_at_1550_pm_per_V']:.6g} pm/V")
    print(f"  ratio       = {b['chi2_at_1550_pm_per_V']/a['chi2_at_1550_pm_per_V']:.6f}")
    print(f"\nLarge kmax:\n  chi2(1550) = {c['chi2_at_1550_pm_per_V']:.6g} pm/V")
    print(f"\nNz + large kmax:\n  chi2(1550) = {d['chi2_at_1550_pm_per_V']:.6g} pm/V")
    print("\nk-grid convergence:")
    for row in convergence:
        print(f"  {row['k_points']:<3} = {row['chi2_at_1550_pm_per_V']:.6g}")
    print("\nPrefactor cross-check:")
    print("  PASS")
    print(f"  relative error = {prefactor_residual:.3e}")
    print("\nr_ehh:\n  default = 0.751 nm\n  sensitivity test PASS")
    print(f"\nRESULT DIRECTORY:\n{root}")
    print(f"\nDEBUG LOG:\n{root / 'demo18_debug.log'}")
    print(f"\nMASTER SUMMARY:\n{root / 'summaries' / 'demo18_master_summary.csv'}")


def run_preflight(verbose: bool = False) -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        cfg = config18.load_config()
        checks.append(("YAML parsing and validation", True, str(config18.CONFIG_PATH)))
        solver_cfg = config18.solver_config(cfg)
        case = cases18.reference_solver_case()
        geometry, profile, blocks, deck = demo16e.build_case(solver_cfg, case)
        required = (
            "simulate1D", "quantum{", "Gamma{", "HH{", "envelopes = yes",
            "probabilities = yes", "run{ quantum{} }",
        )
        missing = [marker for marker in required if marker not in " ".join(deck.split())]
        checks.append(("reference case and abrupt deck rendering", not missing,
                       f"representation={demo16e.representation_of(blocks, case)}; missing={missing}"))
        checks.append(("fixed geometry", bool(
            abs(geometry.thick_well_nm - 7.1) < 1e-12
            and abs(geometry.barrier_nm - 1.8) < 1e-12
            and abs(geometry.thin_well_nm - 2.9) < 1e-12
        ), "7.1/1.8/2.9 nm abrupt"))
        audit = demo18.preflight_audits(cfg)
        for name, passed in audit["checks"].items():
            if name != "passed":
                checks.append((name, bool(passed), "solver-free synthetic states"))
        parser = build_parser()
        parsed = parser.parse_args(["--preflight"])
        checks.append(("CLI argument parsing", bool(parsed.preflight and not parsed.physics),
                       "--preflight"))
        prospective = results_root(None) / cases18.DEMO_ID / "demo18_<timestamp>_<id>"
        checks.append(("output directory logic", cases18.DEMO_ID in str(prospective),
                       str(prospective)))
    except Exception as exc:  # noqa: BLE001
        checks.append(("preflight execution", False, f"{type(exc).__name__}: {exc}"))
        if verbose:
            traceback.print_exc()
    print(RULE)
    print("DEMO 18 PREFLIGHT")
    print(RULE)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        if verbose or not passed:
            print(f"       {detail}")
    passed = bool(checks) and all(row[1] for row in checks)
    print(RULE)
    print("CODE READY TO COMMIT" if passed else "PREFLIGHT FAILED")
    print(RULE)
    return 0 if passed else 1


def run_physics(verbose: bool = False) -> int:
    cfg = config18.load_config()
    solver_cfg = config18.solver_config(cfg)
    machine = demo_workflow.load_machine_config()
    root, run_id = new_run_directory(machine)
    log = DebugLog(root / "demo18_debug.log", verbose=verbose)
    warnings: list[str] = []
    status_path = root / "RUN_STATUS.json"
    _write_json(status_path, {
        "run_id": run_id, "demo_id": cases18.DEMO_ID, "status": "running",
        "timestamp_utc": runlog14.utc_now(),
    })
    case_dir = root / "reference_case"
    try:
        import plots18

        facts = runlog14.git_facts(REPO_ROOT)
        log.section("DEMO 18 START")
        log.line(f"RUN DIRECTORY = {root}")
        log.line("GIT / VERSION INFO")
        log.json({**facts, "demo18_version": demo18.DEMO_VERSION})
        log.line("MACHINE CONFIG")
        log.json(demo_workflow.machine_summary(machine))
        log.line(f"NEXTNANO EXECUTABLE = {machine.executable}")
        log.line("REFERENCE STRUCTURE = 7.1 / 1.8 / 2.9 nm abrupt ACQW")

        snapshot = config18.resolved_snapshot(
            cfg, machine=machine, solver_cfg=solver_cfg
        )
        _write_yaml(root / "resolved_demo18_config.yaml", snapshot)
        shutil.copy2(config18.CONFIG_PATH, root / "config_snapshot" / "demo18.yaml")
        if Path(machine.source_path).is_file():
            shutil.copy2(
                machine.source_path,
                root / "config_snapshot" / f"machine_config{Path(machine.source_path).suffix}",
            )

        case = cases18.reference_solver_case()
        _geometry, _profile, _blocks, deck = demo16e.build_case(solver_cfg, case)
        generated = root / "inputs" / "reference_abrupt.in"
        runlog14.write_text_atomic(generated, deck)
        log.line(f"GENERATED INPUT FILE = {generated}")

        if not machine.run_solver:
            raise Demo18Error(
                "--physics requires a complete licensed machine configuration; "
                "run --preflight on the home laptop"
            )

        log.section("NEXTNANO SOLVER")
        command = solver14.real_argv(
            executable=Path(machine.executable),
            database=Path(machine.database) if machine.database else None,
            license_path=Path(machine.license) if machine.license else None,
            deck=case_dir / "physics" / "nextnano_input" / "case.in",
            output_dir=root / "solver",
            threads=int(solver_cfg["nextnano"].get("threads", 1)),
        )
        log.line("COMMAND")
        log.line(" ".join(str(part) for part in command))
        record = demo16b.solve_case(
            solver_cfg,
            case,
            case_dir,
            machine=machine,
            raw_output_dir=root / "solver",
            build=demo16e.build_case,
        )
        _copy_solver_logs(case_dir, root)
        _write_json(root / "solver_record.json", record)
        solver = record.get("solver") or {}
        log.line(f"RETURN CODE = {solver.get('solver_return_code')}")
        log.line(f"STDOUT LOCATION = {solver.get('stdout_path')}")
        log.line(f"STDERR LOCATION = {solver.get('stderr_path')}")
        inventory = _output_inventory(root / "solver")
        _write_json(root / "solver_output_inventory.json", inventory)
        log.line(f"OUTPUT FILES FOUND = {len(inventory)}")
        log.json(inventory)
        if not record.get("preanalysis_gate", {}).get("passed"):
            raise Demo18Error(
                f"solver/output gate failed at {record.get('failure_stage')}: "
                f"{record.get('failure_reason')}"
            )
        if not record.get("passed"):
            warning = (
                "Demo 16B physical checks did not all pass, but complete solver "
                "states are preserved and the scale audit will continue: "
                f"{record.get('failure_reason')}"
            )
            warnings.append(warning)
            log.line(f"WARNING = {warning}")

        electron, heavy_hole = demo18.load_band_states(solver_cfg, root / "solver")
        quantities = demo18.solver_quantities(electron, heavy_hole)
        _write_json(root / "summaries" / "solver_quantities.json", quantities)
        _log_state_quantities(log, quantities)

        evaluated, scaling, convergence = demo18.evaluate_matrix(
            cfg, electron, heavy_hole
        )
        for item in evaluated:
            item.row["spectrum_path"] = str(_save_spectrum(root, item))
        rows = [item.row for item in evaluated]
        r_rows = demo18.r_sensitivity(cfg, electron, heavy_hole)
        _write_csv(root / "summaries" / "demo18_master_summary.csv", rows)
        _write_csv(root / "summaries" / "kgrid_convergence.csv", convergence)
        _write_csv(root / "summaries" / "r_ehh_sensitivity.csv", r_rows)

        log.section("ABSOLUTE SCALE AUDIT")
        log.line("Nz conventions")
        log.json(cases18.NZ_CONVENTIONS)
        log.line("kmax conventions")
        log.json(cases18.KMAX_CONVENTIONS)
        log.line("spin factor is a separate Chi2Settings field in every case")
        log.line(f"r_ehh default = {cfg['chi2']['r_e_hh_nm']} nm")
        log.line("production/independent prefactors")
        log.json([
            {
                "case_id": row["case_id"],
                "production": row["production_prefactor"],
                "independent": row["independent_si_prefactor"],
                "relative_difference": row["prefactor_relative_difference"],
                "passed": row["prefactor_cross_check_passed"],
            }
            for row in rows
        ])
        log.section("CASE RESULTS")
        log.json(rows)

        plots18.convention_spectra(
            root / "plots" / "demo18_absolute_chi2_convention_comparison.png",
            evaluated,
        )
        plots18.chi2_at_1550(
            root / "plots" / "demo18_chi2_at_1550.png", rows
        )
        plots18.kgrid_convergence(
            root / "plots" / "demo18_kgrid_convergence.png", convergence
        )

        all_checks = {
            "prefactor_cross_checks": bool(scaling["prefactor_checks_passed"]),
            "Nz_scaling": abs(float(scaling["Nz_ratio_B_over_A"]) - 2.0) <= 1.0e-12,
            "spin_scaling": abs(float(scaling["spin_ratio_H_over_G"]) - 2.0) <= 1.0e-12,
            "r_squared_scaling": all(row["passed"] for row in r_rows),
        }
        all_checks["passed"] = all(all_checks.values())
        summary = {
            "demo_id": cases18.DEMO_ID,
            "demo18_version": demo18.DEMO_VERSION,
            "run_id": run_id,
            "status": "completed" if all_checks["passed"] else "invalid",
            "one_solver_run": True,
            "reference_structure": cfg["reference_structure"],
            "solver_quantities": quantities,
            "cases": rows,
            "kgrid_convergence": convergence,
            "r_ehh_sensitivity": r_rows,
            "scaling_audits": scaling,
            "checks": all_checks,
            "warnings": warnings,
            "debug_log": str(log.path),
        }
        _write_json(root / "summaries" / "demo18_summary.json", summary)
        _write_json(status_path, {
            "run_id": run_id,
            "demo_id": cases18.DEMO_ID,
            "status": summary["status"],
            "warnings": warnings,
            "result_directory": str(root),
        })
        log.section("FINAL STATUS")
        log.line("PASS" if all_checks["passed"] else "FAIL")
        log.line("warnings")
        log.json(warnings)
        log.line("output paths")
        log.json({
            "result_directory": root,
            "debug_log": log.path,
            "resolved_config": root / "resolved_demo18_config.yaml",
            "generated_input": root / "inputs" / "reference_abrupt.in",
            "solver_output": root / "solver",
            "solver_record": root / "solver_record.json",
            "master_summary": root / "summaries" / "demo18_master_summary.csv",
            "json_summary": root / "summaries" / "demo18_summary.json",
            "solver_quantities": root / "summaries" / "solver_quantities.json",
            "kgrid_convergence": root / "summaries" / "kgrid_convergence.csv",
            "r_ehh_sensitivity": root / "summaries" / "r_ehh_sensitivity.csv",
            "spectra": root / "summaries" / "spectra",
            "plots": root / "plots",
        })
        residual = max(float(row["prefactor_relative_difference"]) for row in rows)
        if all_checks["passed"]:
            _final_terminal_summary(root, rows, convergence, residual)
            return 0
        print("Demo 18 completed, but one or more scale audits failed.", file=sys.stderr)
        print(f"Result directory: {root}", file=sys.stderr)
        print(f"Debug log: {log.path}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        _copy_solver_logs(case_dir, root)
        trace = traceback.format_exc()
        log.section("FINAL STATUS")
        log.line("FAIL")
        log.line(f"{type(exc).__name__}: {exc}")
        log.line("FULL PYTHON TRACEBACK")
        log.line(trace)
        log.line(f"PRESERVED RESULT DIRECTORY = {root}")
        log.line(f"PRESERVED GENERATED INPUT = {root / 'inputs' / 'reference_abrupt.in'}")
        log.line(f"PRESERVED SOLVER OUTPUT = {root / 'solver'}")
        _write_json(status_path, {
            "run_id": run_id,
            "demo_id": cases18.DEMO_ID,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "debug_log": str(log.path),
            "result_directory": str(root),
        })
        print(f"Demo 18 failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"Result directory: {root}", file=sys.stderr)
        print(f"Debug log: {log.path}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.physics:
        return run_physics(verbose=args.verbose)
    return run_preflight(verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
