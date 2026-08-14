"""Licensed workflow for Demo 18D's unweighted dual-objective search."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from dataclasses import replace
import hashlib
import importlib
import json
import math
from pathlib import Path
import shutil
import sys
import traceback
import uuid
from typing import Any, Mapping, Sequence

# Windows DLL load-order safeguard; keep before scientific imports.
import pyexpat  # noqa: F401


DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
REPO_ROOT = DEMO_DIR.parents[2]
for dependency in (
    DEMO_DIR, DEMOS / "_shared", DEMOS / "11_paper_validation_interband_chi2_acqw",
    DEMOS / "14_absolute_chi2_graded_acqw_bo", DEMOS / "16_acqw_renderer_stress_validation",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
    DEMOS / "16F_paper_absolute_chi2_reproduction_audit",
    DEMOS / "18_absolute_chi2_scale_audit",
    DEMOS / "18B_absolute_chi2_reproduction_audit",
    DEMOS / "18C_paper_missing_parameter_ensemble",
):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import numpy as np
import yaml

import analysis18c
import analysis18d
import audit18b
import cases18c
import cases18d
import config18b
import config18c
import config18d
import demo16b
import demo_workflow
import outputs
import run_demo18c
import runlog14


RULE = "=" * 78


class Runner18DError(RuntimeError):
    pass


class DebugLog:
    def __init__(self, path: Path, verbose: bool):
        self.path, self.verbose = Path(path), verbose
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def line(self, value: object = "") -> None:
        text = str(value)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(text + "\n")
        if self.verbose:
            print(text)

    def section(self, title: str) -> None:
        self.line(); self.line(RULE); self.line(title); self.line(RULE)

    def record(self, value: object) -> None:
        self.line(json.dumps(runlog14.json_safe(value), indent=2, sort_keys=True))


def _load_plots18d() -> Any:
    try:
        return importlib.import_module("plots18d")
    except Exception as exc:
        raise Runner18DError(
            "Demo 18D plotting is unavailable; no licensed physics was started. "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demo 18D solver-physics dual objective")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--physics", action="store_true")
    mode.add_argument("--analyze-existing", type=Path, metavar="RUN_DIR")
    parser.add_argument("--n-cases", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1804)
    parser.add_argument("--demo18c-run", type=Path, default=None,
                        help="completed Demo 18C run containing solver outputs")
    parser.add_argument("--verbose", action="store_true")
    return parser


def _validate_cli(n_cases: int, seed: int) -> None:
    if n_cases != 20 or seed != 1804:
        raise Runner18DError("Demo 18D is exactly 20 frozen cases with seed 1804")


def _write_json(path: Path, value: object) -> Path:
    return runlog14.write_json_atomic(path, runlog14.json_safe(value))


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8"); return path
    fields: list[str] = []
    folded: dict[str, str] = {}
    for row in rows:
        for key0 in row:
            key = str(key0); fold = key.casefold()
            if fold in folded and folded[fold] != key:
                raise Runner18DError(f"CSV header collision: {folded[fold]!r} and {key!r}")
            folded[fold] = key
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value) if isinstance(value, (dict, list)) else value
                             for key, value in row.items()})
    return path


def _run_root(machine: Any) -> tuple[Path, str]:
    facts = runlog14.git_facts(REPO_ROOT)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo18d_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = Path(machine.results_root) / cases18d.DEMO_ID / run_id
    for sub in ("inputs", "solver", "logs", "summaries", "summaries/spectra",
                "plots", "config_snapshot", "cases"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def build_case(cfg: Mapping[str, Any], case: cases18d.PhysicsCase):
    if case.hh_relative_weight != 1.0:
        raise Runner18DError("hh_relative_weight must be exactly 1.0")
    combo = config18d.as_demo18c_combination(case)
    return run_demo18c.build_case(config18d.cfg_for_18c(cfg), combo)


def _field_gate(raw: Path, requested: float) -> dict[str, Any]:
    paths = list(Path(raw).rglob("electric_field.dat"))
    if len(paths) != 1:
        return {"passed": False, "reason": f"expected one electric_field.dat, found {len(paths)}"}
    table = outputs.read_table(paths[0])
    measured = float(np.median(np.asarray(table.column(1), float)))
    tolerance = max(.05, .01 * abs(requested))
    return {"passed": bool(math.isfinite(measured) and abs(measured - requested) <= tolerance),
            "requested_kV_per_cm": requested, "measured_kV_per_cm": measured,
            "tolerance_kV_per_cm": tolerance, "source": str(paths[0])}


def _copy_logs(case_dir: Path, root: Path, case_id: str) -> None:
    source = case_dir / "physics" / "logs"
    if source.is_dir():
        for item in source.iterdir():
            if item.is_file():
                shutil.copy2(item, root / "logs" / f"{case_id}_{item.name}")


def _solve_all(cfg: Mapping[str, Any], cases: Sequence[cases18d.PhysicsCase],
               machine: Any, root: Path, log: DebugLog) -> None:
    for index, case in enumerate(cases, 1):
        solver_cfg, rendered_case, geometry, profile, blocks, deck = build_case(cfg, case)
        case_dir, raw = root / "cases" / case.case_id, root / "solver" / case.case_id
        runlog14.write_text_atomic(root / "inputs" / f"{case.case_id}.in", deck)
        _write_json(case_dir / "case_definition.json", {
            **case.as_record(), **geometry.as_record(),
            "derived_period_barrier_nm": solver_cfg["geometry"]["period_barrier_nm"],
        })
        log.section(f"LICENSED SOLVE {index}/20: {case.case_id}")
        try:
            built = (geometry, profile, blocks, deck)
            record = demo16b.solve_case(
                solver_cfg, rendered_case, case_dir, machine=machine, raw_output_dir=raw,
                build=lambda _cfg, _case, value=built: value,
            )
            solver_code = (record.get("solver") or {}).get("solver_return_code")
            quantum = bool((record.get("preanalysis_gate") or {}).get("passed"))
            field = _field_gate(raw, case.electrostatic_field_kV_per_cm) if solver_code == 0 and quantum \
                else {"passed": False, "reason": "solver/quantum gate failed"}
            gate = {"passed": bool(solver_code == 0 and quantum and field["passed"]),
                    "solver_return_code_zero": solver_code == 0,
                    "quantum_output_completion_gate": quantum, "field_gate": field,
                    "failure_reason": record.get("failure_reason")}
        except Exception as exc:
            record = {"passed": False, "failure_reason": f"{type(exc).__name__}: {exc}"}
            gate = {"passed": False, "failure_reason": record["failure_reason"]}
            log.line(traceback.format_exc())
        _copy_logs(case_dir, root, case.case_id)
        _write_json(case_dir / "solver_record.json", record)
        _write_json(case_dir / "solver_gate.json", gate)
        log.record(gate)


def _audit_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    audit_cfg = config18b.load_config()
    audit_cfg["bound_state_criteria"] = dict(cfg["bound_state_criteria"])
    return audit_cfg


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_solved(cfg: Mapping[str, Any], case: cases18d.PhysicsCase, raw: Path) -> dict[str, Any]:
    solver_cfg, _rendered, geometry, _profile, _blocks, _deck = build_case(cfg, case)
    data = audit18b.load_solved_data(solver_cfg, raw)
    return audit18b.analyze_case(
        _audit_config(cfg), case.case_id, data, geometry,
        float(cfg["solver"]["quantum_region_padding_nm"]),
    )


def _reanalyse_18c(source: Path, destination: Path, log: DebugLog) -> list[dict[str, Any]]:
    """Recompute every unique 18C state with common, unweighted postprocessing."""

    source = Path(source)
    required = (source / "solver", source / "config_snapshot" / "demo18c_combinations.csv",
                source / "config_snapshot" / "demo18c.yaml",
                source / "summaries" / "demo18c_combo_results.csv")
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise Runner18DError(f"Demo 18C source run is incomplete; missing {missing}")
    old_cfg = config18c.load_config(source / "config_snapshot" / "demo18c.yaml")
    old_combos = config18c.load_combinations(source / "config_snapshot" / "demo18c_combinations.csv")
    with (source / "summaries" / "demo18c_combo_results.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as stream:
        original_results = list(csv.DictReader(stream))
    original_by_combo = {row["combo_id"]: row for row in original_results}
    rows: list[dict[str, Any]] = []
    for original in (row for row in old_combos if row.requires_new_nextnano_solve):
        raw = source / "solver" / original.solver_case_id
        source_gate_path = source / "cases" / original.solver_case_id / "solver_gate.json"
        if not source_gate_path.is_file():
            raise Runner18DError(f"missing Demo 18C solver provenance gate {source_gate_path}")
        source_gate = _read_json(source_gate_path)
        if not bool(source_gate.get("passed")):
            raise Runner18DError(
                f"Demo 18C {original.solver_case_id} did not pass its original solver gate"
            )
        solver_cfg, _case, geometry, _profile, _blocks, _deck = run_demo18c.build_case(old_cfg, original)
        data = audit18b.load_solved_data(solver_cfg, raw)
        solved = audit18b.analyze_case(
            old_cfg, original.solver_case_id, data, geometry,
            float(old_cfg["solver"].get("quantum_region_padding_nm", 42.0)),
        )
        normalized_case = cases18d.PhysicsCase(
            case_id=original.solver_case_id, design_role="demo18c_reanalysis",
            source_18c_combo_id=original.combo_id,
            electrostatic_field_kV_per_cm=original.electrostatic_field_kV_per_cm,
            tunneling_barrier_nm=original.tunneling_barrier_nm,
            well1_nm=original.well1_nm, well2_nm=original.well2_nm,
        )
        normalized_cfg = config18d.load_config()
        computed, spectrum = analysis18d.analyze_case(normalized_cfg, normalized_case, solved,
                                                       solver_pass=True)
        old = original_by_combo[original.combo_id]
        rows.append({
            "original_combo_id": original.combo_id, "solver_case_id": original.solver_case_id,
            "field_kV_per_cm": original.electrostatic_field_kV_per_cm,
            "tunneling_barrier_nm": original.tunneling_barrier_nm,
            "well1_nm": original.well1_nm, "well2_nm": original.well2_nm,
            "original_r_e_hh_nm": original.r_e_hh_nm, "normalized_r_e_hh_nm": 0.751,
            "original_hh_relative_weight": original.hh_relative_weight,
            "forced_hh_relative_weight": 1.0,
            "original_reported_chi2_1550": float(old["chi2_1550_pm_per_V"]),
            "raw_chi2_1550_at_hh_weight_1": float(old["chi_total_raw_unweighted_abs"]),
            "normalized_chi2_1550_at_r_0p751": computed["chi2_1550_pm_per_V"],
            "original_peak_wavelength_nm": float(old["peak_wavelength_nm"]),
            "recomputed_unweighted_peak_wavelength_nm": computed["peak_wavelength_nm"],
            "recomputed_unweighted_peak_chi2_pm_per_V": computed["peak_chi2_pm_per_V"],
            "chi_e_real": computed["chi_e_real"], "chi_e_imag": computed["chi_e_imag"],
            "chi_e_abs": computed["chi_e_abs"], "chi_hh_real": computed["chi_hh_real"],
            "chi_hh_imag": computed["chi_hh_imag"], "chi_hh_abs": computed["chi_hh_abs"],
            "cancellation_factor": computed["cancellation_factor"],
            "spectral_window_pass": computed["spectral_window_pass"],
            "desired_peak_ratio": computed["desired_peak_ratio"],
            "source_solver_gate_passed": True,
            "source_combinations_sha256": cases18c.combinations_sha256(
                source / "config_snapshot" / "demo18c_combinations.csv"
            ),
        })
    rows.sort(key=lambda row: float(row["normalized_chi2_1550_at_r_0p751"]), reverse=True)
    for rank, row in enumerate(rows, 1):
        row["unweighted_amplitude_rank"] = rank
    _write_csv(destination / "demo18d_reanalysis_of_18c.csv", rows)
    log.section("DEMO 18C UNWEIGHTED REANALYSIS")
    log.record(rows)
    return rows


def _spectrum_rows(spectrum: Mapping[str, np.ndarray]) -> list[dict[str, float]]:
    rows = []
    for i, wavelength in enumerate(spectrum["wavelength_nm"]):
        row = {"wavelength_nm": float(wavelength)}
        for key in ("chi_e", "chi_hh", "chi_total"):
            value = complex(spectrum[key][i])
            row.update({f"{key}_real": value.real, f"{key}_imag": value.imag,
                        f"{key}_abs": abs(value)})
        rows.append(row)
    return rows


def _failed(case: cases18d.PhysicsCase, reason: str) -> dict[str, Any]:
    return {**case.as_record(), "solver_pass": False, "bound_state_pass": False,
            "orthonormality_pass": False, "physical_valid": False,
            "classification": "FAILED_PHYSICS", "failure_reason": reason,
            "chi2_1550_pm_per_V": float("nan"), "combined_score": float("nan"),
            "peak_wavelength_nm": float("nan"), "spectral_window_pass": False}


def _analyze_all(cfg: Mapping[str, Any], cases: Sequence[cases18d.PhysicsCase],
                 root: Path, log: DebugLog) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    spectra: dict[str, Mapping[str, np.ndarray]] = {}
    solved_by_case: dict[str, Mapping[str, Any]] = {}
    all_states: list[dict[str, Any]] = []
    all_matrices: list[dict[str, Any]] = []
    all_localization: list[dict[str, Any]] = []
    for case in cases:
        gate_path = root / "cases" / case.case_id / "solver_gate.json"
        gate = _read_json(gate_path) if gate_path.is_file() else {"passed": False, "failure_reason": "missing gate"}
        if not bool(gate.get("passed")):
            results.append(_failed(case, str(gate.get("failure_reason") or gate))); continue
        try:
            solved = _load_solved(cfg, case, root / "solver" / case.case_id)
            row, spectrum = analysis18d.analyze_case(cfg, case, solved, solver_pass=True)
            results.append(row); spectra[case.case_id] = spectrum; solved_by_case[case.case_id] = solved
            all_states.extend({"case_id": case.case_id, **r} for r in solved["state_audit"])
            all_matrices.extend({"case_id": case.case_id, **r} for r in solved["matrix_rows"])
            all_localization.extend({"case_id": case.case_id, **r} for r in solved["localization"])
        except Exception as exc:
            results.append(_failed(case, f"{type(exc).__name__}: {exc}")); log.line(traceback.format_exc())
    ranked = analysis18d.rank(results)
    spectral_ranked = analysis18d.spectral_window_rank(ranked)
    outcome = analysis18d.outcome(ranked)
    selected = []
    for case_id in ["Case_00", *[str(row["case_id"]) for row in ranked[:3]]]:
        if case_id in spectra and case_id not in selected:
            selected.append(case_id)
    for case_id, spectrum in spectra.items():
        _write_csv(root / "summaries" / "spectra" / f"{case_id}.csv", _spectrum_rows(spectrum))
    best = spectral_ranked[0] if spectral_ranked else (ranked[0] if ranked else None)
    best_solved = solved_by_case.get(str(best["case_id"])) if best else None
    plot_paths = _load_plots18d().generate_all(
        root / "plots", results, ranked, spectra, selected, best_solved
    )
    summaries = root / "summaries"
    _write_csv(summaries / "demo18d_results.csv", results)
    _write_csv(summaries / "demo18d_ranked_results.csv", ranked)
    _write_csv(summaries / "demo18d_spectral_window_ranked_results.csv", spectral_ranked)
    _write_csv(summaries / "state_audit.csv", all_states)
    _write_csv(summaries / "matrix_elements.csv", all_matrices)
    _write_csv(summaries / "localization.csv", all_localization)
    master_keys = ("case_id", "dual_objective_rank", "chi2_1550_pm_per_V",
                   "amplitude_percent_error", "peak_wavelength_nm", "spectral_window_pass",
                   "combined_score", "desired_peak_ratio", "cancellation_factor",
                   "classification", "physical_valid")
    ranks = {row["case_id"]: row.get("dual_objective_rank") for row in ranked}
    _write_csv(summaries / "demo18d_master_summary.csv", [
        {key: ranks.get(row["case_id"]) if key == "dual_objective_rank" else row.get(key)
         for key in master_keys} for row in results
    ])
    summary = {
        "demo_id": cases18d.DEMO_ID, "total_cases": 20, "valid_cases": len(ranked),
        "failed_cases": 20 - len(ranked), "best_physical_match": best,
        "top5": ranked[:5], "outcome": outcome,
        "plots": [str(path) for path in plot_paths],
        "interpretation": (
            "Primary results use actual solver states with hh_relative_weight=1, r_e_hh=0.751 nm, "
            "spin=2 and Nz=2/30 nm; amplitude-only or spectral-only agreement is not reproduction."
        ),
    }
    _write_json(summaries / "demo18d_summary.json", summary)
    return summary


def _terminal(summary: Mapping[str, Any], root: Path) -> None:
    print("DEMO 18D - SOLVER PHYSICS DUAL-OBJECTIVE REPRODUCTION")
    print("=" * 60)
    print("Demo 18B baseline:\n    chi2(1550): 84.91 pm/V\n    peak: 1520 nm")
    print("Paper target:\n    chi2(1550): 2340 pm/V\n    desired peak: 1520-1560 nm")
    print(f"Cases:\n    total: 20\n    valid: {summary['valid_cases']}\n    failed: {summary['failed_cases']}")
    best = summary.get("best_physical_match")
    if best:
        print("\nBEST PHYSICAL MATCH\n-------------------")
        print(f"Case: {best['case_id']}\nchi2(1550): {float(best['chi2_1550_pm_per_V']):.3f} pm/V")
        print(f"percent amplitude error: {float(best['amplitude_percent_error']):.2f}%")
        print(f"peak wavelength: {float(best['peak_wavelength_nm']):.1f} nm")
        print(f"spectral window pass: {best['spectral_window_pass']}\ncombined score: {float(best['combined_score']):.4f}")
        print("\nPARAMETERS\n----------")
        print(f"field: {best['electrostatic_field_kV_per_cm']} kV/cm\nbarrier: {best['tunneling_barrier_nm']} nm")
        print(f"well1: {best['well1_nm']} nm\nwell2: {best['well2_nm']} nm")
        print("\nCANCELLATION\n------------")
        print(f"electron contribution: {float(best['chi_e_abs']):.3f} pm/V\nHH contribution: {float(best['chi_hh_abs']):.3f} pm/V")
        print(f"net: {float(best['chi_total_abs']):.3f} pm/V\ncancellation factor: {float(best['cancellation_factor']):.3f}")
        print("\nMATRIX PHYSICS\n--------------")
        print(f"delta_z_e: {float(best['delta_z_e_nm']):.6f} nm\ndelta_z_hh: {float(best['delta_z_hh_nm']):.6f} nm")
        print(f"O11: {float(best['O11']):.6f}\nO22: {float(best['O22']):.6f}")
        print("\nr_e_hh SENSITIVITY\n------------------")
        print(f"primary r: 0.751 nm\nrequired r for exact paper amplitude: {float(best['r_required_nm']):.6f} nm")
        print(f"required r inside allowed range: {best['r_required_inside_allowed_range']}")
    print("\nTOP 5 DUAL-OBJECTIVE CASES\n--------------------------")
    for index, row in enumerate(summary["top5"], 1):
        print(f"{index}. {row['case_id']}: {float(row['chi2_1550_pm_per_V']):.2f} pm/V, "
              f"peak {float(row['peak_wavelength_nm']):.1f} nm, score {float(row['combined_score']):.4f}")
    print(f"\nFINAL OUTCOME: {summary['outcome']['outcome']} - {summary['outcome']['label']}")
    print(f"\nPRIMARY INTERPRETATION:\n{summary['interpretation']}\n\nRESULT DIRECTORY:\n{root}")


def run_preflight(n_cases: int, seed: int, verbose: bool) -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        _validate_cli(n_cases, seed); cfg = config18d.load_config(); cases = config18d.load_cases()
        digest = cases18d.combinations_sha256(config18d.COMBINATIONS_PATH)
        checks.append(("frozen 20-case design", len(cases) == 20, f"SHA256 {digest}"))
        checks.append(("all cases are real solver physics", len({c.solver_key() for c in cases}) == 20
                       and all(c.requires_licensed_solve for c in cases), "20 unique solver decks"))
        checks.append(("forbidden postprocessors fixed", all(c.hh_relative_weight == 1.0
                       and c.spin_degeneracy == 2 and c.wells_per_period_for_Nz == 2
                       and c.r_e_hh_primary_nm == .751 for c in cases), "weight=1; spin=2; Nz=2; r=0.751"))
        hashes = set()
        for case in cases:
            solver_cfg, _rendered, geometry, _profile, blocks, deck = build_case(cfg, case)
            compact = " ".join(deck.split())
            if "no_density = yes" not in compact or "run{ quantum{} }" not in compact:
                raise Runner18DError(f"{case.case_id}: validated quantum-only mode missing")
            if "ternary_linear{" in blocks["structure_block"]:
                raise Runner18DError(f"{case.case_id}: abrupt deck contains grading")
            if abs(geometry.thick_well_nm + geometry.thin_well_nm + geometry.barrier_nm
                   + float(solver_cfg["geometry"]["period_barrier_nm"]) - 30.0) > 1e-10:
                raise Runner18DError(f"{case.case_id}: period is not 30 nm")
            hashes.add(hashlib.sha256(deck.encode()).hexdigest())
        checks.append(("20 distinct solver decks", len(hashes) == 20, f"found {len(hashes)}"))
        checks.append(("Demo 18C reanalysis configured", bool(cfg["design"]["demo18c_source_run"]),
                       str(cfg["design"]["demo18c_source_run"])))
        parsed = build_parser().parse_args(["--physics", "--n-cases", "20", "--seed", "1804"])
        checks.append(("CLI", parsed.physics, "frozen physics command accepted"))
    except Exception as exc:
        checks.append(("preflight execution", False, f"{type(exc).__name__}: {exc}"))
        if verbose: traceback.print_exc()
    print(RULE); print("DEMO 18D PREFLIGHT - NO LICENSED PHYSICS EXECUTED"); print(RULE)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        if verbose or not passed: print(f"       {detail}")
    passed = bool(checks) and all(row[1] for row in checks)
    print(RULE); print("CODE READY FOR LICENSED DEMO 18D RUN" if passed else "PREFLIGHT FAILED"); print(RULE)
    return 0 if passed else 1


def run_physics(n_cases: int, seed: int, source_18c: Path | None, verbose: bool) -> int:
    _validate_cli(n_cases, seed); cfg = config18d.load_config(); cases = config18d.load_cases()
    _load_plots18d()
    machine = demo_workflow.load_machine_config()
    if not machine.run_solver:
        raise Runner18DError("--physics requires the licensed work-laptop machine configuration")
    source = source_18c or Path(str(cfg["design"]["demo18c_source_run"]))
    root, run_id = _run_root(machine); log = DebugLog(root / "demo18d_debug.log", verbose)
    digest = cases18d.combinations_sha256(config18d.COMBINATIONS_PATH)
    print(f"demo18d_combinations.csv SHA256: {digest}")
    _write_json(root / "RUN_STATUS.json", {"run_id": run_id, "status": "running",
                                              "combinations_sha256": digest})
    try:
        for source_file in (config18d.CONFIG_PATH, config18d.RANGES_PATH, config18d.COMBINATIONS_PATH):
            shutil.copy2(source_file, root / "config_snapshot" / source_file.name)
        if Path(machine.source_path).is_file():
            shutil.copy2(machine.source_path, root / "config_snapshot" / Path(machine.source_path).name)
        runlog14.write_text_atomic(root / "resolved_demo18d_config.yaml",
            yaml.safe_dump(runlog14.json_safe({**cfg, "demo18c_source_run_resolved": str(source),
                                                "combinations_sha256": digest,
                                                "machine": demo_workflow.machine_summary(machine)}), sort_keys=False))
        # Required first task: complete unweighted 18C reanalysis before any 18D solve.
        _reanalyse_18c(source, root / "summaries", log)
        _solve_all(cfg, cases, machine, root, log)
        summary = _analyze_all(cfg, cases, root, log)
        _write_json(root / "RUN_STATUS.json", {"run_id": run_id, "status": "completed",
                                                  "outcome": summary["outcome"], "result_directory": root})
        _terminal(summary, root); return 0
    except Exception as exc:
        log.line(traceback.format_exc())
        _write_json(root / "RUN_STATUS.json", {"run_id": run_id, "status": "failed",
                                                  "error": f"{type(exc).__name__}: {exc}",
                                                  "result_directory": root})
        print(f"Demo 18D failed before completion: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"Preserved result directory: {root}", file=sys.stderr); return 1


def analyze_existing(root: Path, n_cases: int, seed: int, verbose: bool) -> int:
    _validate_cli(n_cases, seed); root = Path(root).resolve()
    for sub in ("summaries", "summaries/spectra", "plots", "logs"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    summary = _analyze_all(config18d.load_config(), config18d.load_cases(), root,
                           DebugLog(root / "demo18d_reanalysis.log", verbose))
    _terminal(summary, root); return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.physics:
        return run_physics(args.n_cases, args.seed, args.demo18c_run, args.verbose)
    if args.analyze_existing:
        return analyze_existing(args.analyze_existing, args.n_cases, args.seed, args.verbose)
    return run_preflight(args.n_cases, args.seed, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
