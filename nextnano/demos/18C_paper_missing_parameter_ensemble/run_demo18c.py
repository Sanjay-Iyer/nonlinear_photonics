"""CLI, licensed solve orchestration, and reporting for Demo 18C."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
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
    DEMO_DIR, DEMOS / "_shared",
    DEMOS / "11_paper_validation_interband_chi2_acqw",
    DEMOS / "14_absolute_chi2_graded_acqw_bo",
    DEMOS / "16_acqw_renderer_stress_validation",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
    DEMOS / "16F_paper_absolute_chi2_reproduction_audit",
    DEMOS / "18_absolute_chi2_scale_audit",
    DEMOS / "18B_absolute_chi2_reproduction_audit",
):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import numpy as np
import yaml

import analysis18c
import audit18b
import cases18c
import config18b
import config18c
import demo16b
import demo16e
import demo_workflow
import outputs
import plots18c
import runlog14


RULE = "=" * 76


class Runner18CError(RuntimeError):
    pass


class DebugLog:
    def __init__(self, path: Path, verbose: bool):
        self.path = Path(path)
        self.verbose = verbose
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def line(self, value: object = "") -> None:
        text = str(value)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(text + "\n")
        if self.verbose:
            print(text)

    def section(self, title: str) -> None:
        self.line()
        self.line(RULE)
        self.line(title)
        self.line(RULE)

    def record(self, value: object) -> None:
        self.line(json.dumps(runlog14.json_safe(value), indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demo 18C missing-parameter ensemble")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--physics", action="store_true")
    group.add_argument("--analyze-existing", type=Path, metavar="RUN_DIR")
    parser.add_argument("--n-combos", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1803)
    parser.add_argument("--verbose", action="store_true")
    return parser


def _write_json(path: Path, value: object) -> Path:
    return runlog14.write_json_atomic(path, runlog14.json_safe(value))


def _write_yaml(path: Path, value: object) -> Path:
    return runlog14.write_text_atomic(
        path, yaml.safe_dump(runlog14.json_safe(value), sort_keys=False)
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return path
    fields: list[str] = []
    folded: dict[str, str] = {}
    for row in rows:
        for key in row:
            key = str(key)
            lowered = key.casefold()
            if lowered in folded and folded[lowered] != key:
                raise Runner18CError(
                    f"CSV header collision: {folded[lowered]!r} and {key!r}"
                )
            folded[lowered] = key
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(value) if isinstance(value, (dict, list)) else value
                for key, value in row.items()
            })
    return path


def _validate_cli(n_combos: int, seed: int) -> None:
    if n_combos != cases18c.COMBO_COUNT:
        raise Runner18CError("Demo 18C is exactly 20 predefined combinations")
    if seed != cases18c.SEED:
        raise Runner18CError("Demo 18C's checked-in design is frozen to seed 1803")


def _run_root(machine: Any) -> tuple[Path, str]:
    facts = runlog14.git_facts(REPO_ROOT)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo18c_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = Path(machine.results_root) / cases18c.DEMO_ID / run_id
    for sub in (
        "inputs", "solver", "logs", "summaries", "summaries/spectra",
        "plots", "config_snapshot", "cases",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def _field_block(field_kV_cm: float) -> str:
    strength = field_kV_cm * 1.0e5
    return (
        "\n# Demo 18C diagnostic proxy: imposed electrostatic tilt.\n"
        "# This is not a claimed paper input. The run remains quantum-only.\n"
        "poisson{\n"
        "    electric_field{\n"
        "        direction = [1, 0, 0]\n"
        f"        strength = {strength:.12g}  # V/m; {field_kV_cm:.12g} kV/cm\n"
        "    }\n"
        "    output_potential{}\n"
        "    output_electric_field{}\n"
        "}\n"
    )


def build_case(cfg: Mapping[str, Any], combo: cases18c.Combination):
    solver_cfg = config18c.solver_config(cfg, combo)
    asymmetry = (combo.well1_nm - combo.well2_nm) / (combo.well1_nm + combo.well2_nm)
    case = demo16e.cases16e.GeometryCase(
        case_id=combo.solver_case_id,
        name=f"demo18c_{combo.solver_case_id}",
        description=f"Predefined state solve first used by {combo.combo_id}",
        asymmetry_s=asymmetry,
        central_barrier_nm=combo.tunneling_barrier_nm,
        left_grading_width_nm=0.0,
        right_grading_width_nm=0.0,
        interface_mode="abrupt",
    )
    geometry, profile, blocks, deck = demo16e.build_case(solver_cfg, case)
    marker = "\nquantum{\n"
    if deck.count(marker) != 1:
        raise Runner18CError(f"{combo.combo_id}: cannot locate unique quantum block")
    deck = deck.replace(marker, _field_block(combo.electrostatic_field_kV_per_cm) + marker)
    return solver_cfg, case, geometry, profile, blocks, deck


def _field_gate(raw: Path, requested: float) -> dict[str, Any]:
    paths = list(Path(raw).rglob("electric_field.dat"))
    if len(paths) != 1:
        return {
            "passed": False, "requested_kV_per_cm": requested,
            "reason": f"expected one electric_field.dat, found {len(paths)}",
        }
    table = outputs.read_table(paths[0])
    measured = float(np.median(np.asarray(table.column(1), dtype=float)))
    tolerance = max(0.05, 0.01 * abs(requested))
    passed = math.isfinite(measured) and abs(measured - requested) <= tolerance
    return {
        "passed": bool(passed), "requested_kV_per_cm": requested,
        "measured_median_kV_per_cm": measured, "tolerance_kV_per_cm": tolerance,
        "source": str(paths[0]),
    }


def _copy_logs(case_dir: Path, root: Path, solve_id: str) -> None:
    source = case_dir / "physics" / "logs"
    if source.is_dir():
        for item in source.iterdir():
            if item.is_file():
                shutil.copy2(item, root / "logs" / f"{solve_id}_{item.name}")


def _solve_all(
    cfg: Mapping[str, Any], combos: tuple[cases18c.Combination, ...],
    machine: Any, root: Path, log: DebugLog,
) -> None:
    unique = config18c.unique_solver_combinations(combos)
    for index, combo in enumerate(unique, 1):
        solver_cfg, case, geometry, profile, blocks, deck = build_case(cfg, combo)
        solve_id = combo.solver_case_id
        input_path = root / "inputs" / f"{solve_id}.in"
        runlog14.write_text_atomic(input_path, deck)
        case_dir = root / "cases" / solve_id
        _write_json(case_dir / "case_definition.json", {
            **combo.as_record(), **geometry.as_record(),
            "derived_period_barrier_nm": solver_cfg["geometry"]["period_barrier_nm"],
        })
        log.section(f"LICENSED SOLVE {index}/{len(unique)}: {solve_id}")
        log.record({"first_combo": combo.combo_id, "input": input_path,
                    "field_kV_per_cm": combo.electrostatic_field_kV_per_cm})
        raw = root / "solver" / solve_id
        try:
            built = (geometry, profile, blocks, deck)
            record = demo16b.solve_case(
                solver_cfg, case, case_dir, machine=machine, raw_output_dir=raw,
                build=lambda _cfg, _case, value=built: value,
            )
            quantum_gate = bool((record.get("preanalysis_gate") or {}).get("passed"))
            solver_code = (record.get("solver") or {}).get("solver_return_code")
            field = _field_gate(raw, combo.electrostatic_field_kV_per_cm) \
                if quantum_gate and solver_code == 0 else {
                    "passed": False, "reason": "solver/quantum gate did not pass",
                    "requested_kV_per_cm": combo.electrostatic_field_kV_per_cm,
                }
            gate = {
                "passed": bool(quantum_gate and solver_code == 0 and field["passed"]),
                "solver_return_code_zero": solver_code == 0,
                "quantum_output_and_completion_gate": quantum_gate,
                "field_gate": field,
                "demo16b_physics_checks_passed": bool(record.get("passed")),
                "failure_reason": record.get("failure_reason"),
            }
        except Exception as exc:  # keep the frozen failed case; continue the ensemble
            record = {"passed": False, "failure_reason": f"{type(exc).__name__}: {exc}"}
            gate = {
                "passed": False, "solver_return_code_zero": False,
                "quantum_output_and_completion_gate": False,
                "field_gate": {"passed": False, "reason": "exception before field check"},
                "failure_reason": record["failure_reason"],
            }
            log.line(traceback.format_exc())
        _copy_logs(case_dir, root, solve_id)
        _write_json(case_dir / "solver_record.json", record)
        _write_json(case_dir / "solver_gate.json", gate)
        log.record(gate)


def _read_gate(root: Path, solve_id: str) -> dict[str, Any]:
    path = root / "cases" / solve_id / "solver_gate.json"
    if not path.is_file():
        return {"passed": False, "failure_reason": f"missing {path}"}
    return json.loads(path.read_text(encoding="utf-8"))


def _spectrum_rows(spectrum: Mapping[str, np.ndarray]) -> list[dict[str, float]]:
    rows = []
    for index, wavelength in enumerate(spectrum["wavelength_nm"]):
        row: dict[str, float] = {"wavelength_nm": float(wavelength)}
        for name in ("chi_e", "chi_hh_raw", "chi_hh_weighted", "chi_total"):
            value = complex(spectrum[name][index])
            row[f"{name}_real"] = float(value.real)
            row[f"{name}_imag"] = float(value.imag)
            row[f"{name}_abs"] = float(abs(value))
        rows.append(row)
    return rows


def _best5_markdown(
    ranked: Sequence[Mapping[str, Any]], baseline: Mapping[str, Any],
) -> str:
    lines = [
        "# Demo 18C best-five interpretation", "",
        "These are sensitivity cases, not inferred author inputs. A close diagnostic-proxy case "
        "only demonstrates reachability within the tested envelope.", "",
    ]
    parameters = (
        "r_e_hh_nm", "electrostatic_field_kV_per_cm", "hh_relative_weight",
        "wells_per_period_for_Nz", "spin_degeneracy", "kmax_fraction_2pi_over_a",
        "well1_nm", "well2_nm", "tunneling_barrier_nm", "electron_mass_scale",
        "hh_mass_scale", "cb_offset_scale", "hh_offset_scale",
    )
    categories = {
        "r_e_hh_nm": "UNCERTAIN", "electrostatic_field_kV_per_cm": "DIAGNOSTIC PROXY",
        "hh_relative_weight": "DIAGNOSTIC PROXY", "wells_per_period_for_Nz": "CONVENTION",
        "spin_degeneracy": "CONVENTION", "kmax_fraction_2pi_over_a": "CONVENTION",
        "well1_nm": "UNCERTAIN", "well2_nm": "UNCERTAIN",
        "tunneling_barrier_nm": "UNCERTAIN", "electron_mass_scale": "UNCERTAIN",
        "hh_mass_scale": "UNCERTAIN", "cb_offset_scale": "UNCERTAIN",
        "hh_offset_scale": "UNCERTAIN",
    }
    for rank, row in enumerate(ranked[:5], 1):
        lines.extend((
            f"## {rank}. {row['combo_id']}", "",
            f"chi2(1550) = {float(row['chi2_1550_pm_per_V']):.3f} pm/V; paper = "
            f"2340 pm/V; error = {float(row['percent_error']):.2f}%.", "",
            "Changed relative to Demo 18B:", "",
        ))
        changed = [name for name in parameters if row[name] != baseline[name]]
        lines.extend(f"- {name}: {baseline[name]} -> {row[name]} ({categories[name]})"
                     for name in changed)
        if not changed:
            lines.append("- None (baseline).")
        lines.extend((
            "", "Cancellation:", "",
            f"- Demo 18B electron / HH weighted / net: "
            f"{float(baseline['chi_e_abs']):.3f} / {float(baseline['chi_hh_weighted_abs']):.3f} / "
            f"{float(baseline['chi_total_abs']):.3f} pm/V",
            f"- Electron: {float(row['chi_e_abs']):.3f} pm/V",
            f"- HH raw: {float(row['chi_hh_raw_abs']):.3f} pm/V",
            f"- HH weighted: {float(row['chi_hh_weighted_abs']):.3f} pm/V",
            f"- Net: {float(row['chi_total_abs']):.3f} pm/V",
            f"- Cancellation factor: {float(baseline['cancellation_factor']):.3f} -> "
            f"{float(row['cancellation_factor']):.3f}",
            "", "Physical checks:", "",
            f"- Bound states: {'PASS' if row['bound_state_pass'] else 'FAIL'}",
            f"- Orthonormality: {'PASS' if row['orthonormality_pass'] else 'FAIL'}",
            f"- Transitions E1-HH1 / E1-HH2 / E2-HH1 / E2-HH2: "
            f"{float(row['transition_e1_hh1_eV']):.4f} / "
            f"{float(row['transition_e1_hh2_eV']):.4f} / "
            f"{float(row['transition_e2_hh1_eV']):.4f} / "
            f"{float(row['transition_e2_hh2_eV']):.4f} eV",
            f"- Spectrum: {row['spectral_match_flag']} (peak {float(row['peak_wavelength_nm']):.1f} nm)",
            "", "Interpretation: the electron/HH residual changed through the complete Eq. 2 "
            "calculation. DIAGNOSTIC PROXY values must not be reported as paper inputs.", "",
        ))
    return "\n".join(lines) + "\n"


def _analyze_all(
    cfg: Mapping[str, Any], combos: tuple[cases18c.Combination, ...],
    root: Path, log: DebugLog,
) -> dict[str, Any]:
    solved_by_id: dict[str, Mapping[str, Any]] = {}
    failure_by_id: dict[str, str] = {}
    all_states: list[dict[str, Any]] = []
    all_matrices: list[dict[str, Any]] = []
    audit_cfg = config18b.load_config()
    audit_cfg["bound_state_criteria"] = dict(cfg["bound_state_criteria"])
    for combo in config18c.unique_solver_combinations(combos):
        solve_id = combo.solver_case_id
        gate = _read_gate(root, solve_id)
        raw = root / "solver" / solve_id
        if not bool(gate.get("passed")):
            failure_by_id[solve_id] = str(gate.get("failure_reason") or gate)
            continue
        try:
            solver_cfg, _case, geometry, _profile, _blocks, _deck = build_case(cfg, combo)
            data = audit18b.load_solved_data(solver_cfg, raw)
            solved = audit18b.analyze_case(
                audit_cfg, solve_id, data, geometry,
                float(cfg["solver"]["quantum_region_padding_nm"]),
            )
            solved_by_id[solve_id] = solved
            for row in solved["state_audit"]:
                all_states.append({"solver_case_id": solve_id, **row})
            all_matrices.extend({"solver_case_id": solve_id, **row}
                                for row in solved["matrix_rows"])
        except Exception as exc:
            failure_by_id[solve_id] = f"{type(exc).__name__}: {exc}"
            log.line(traceback.format_exc())

    results: list[dict[str, Any]] = []
    spectra: dict[str, Mapping[str, np.ndarray]] = {}
    for combo in combos:
        solved = solved_by_id.get(combo.solver_case_id)
        if solved is None:
            results.append(analysis18c.failed_combo_row(
                cfg, combo, failure_by_id.get(combo.solver_case_id, "solver state unavailable")
            ))
            continue
        try:
            row, spectrum = analysis18c.analyze_combo(
                cfg, combo, solved, solver_pass=True
            )
            results.append(row)
            spectra[combo.combo_id] = spectrum
            log.section(f"ANALYSIS: {combo.combo_id}")
            log.record(row)
        except Exception as exc:
            results.append(analysis18c.failed_combo_row(
                cfg, combo, f"analysis failed: {type(exc).__name__}: {exc}"
            ))
            log.line(traceback.format_exc())

    ranked = analysis18c.rank_valid(results)
    importance = analysis18c.parameter_importance(ranked)
    outcome = analysis18c.classify_outcome(ranked)
    baseline = next(row for row in results if row["combo_id"] == "Combo_00")
    top3_nonbaseline = [
        str(row["combo_id"]) for row in ranked if row["combo_id"] != "Combo_00"
    ][:3]
    selected_store: list[str] = []
    for combo_id in ["Combo_00", *top3_nonbaseline]:
        if combo_id in spectra and combo_id not in selected_store:
            selected_store.append(combo_id)
    poor = next((str(row["combo_id"]) for row in reversed(ranked)
                 if str(row["combo_id"]) not in selected_store), None)
    if poor:
        selected_store.append(poor)
    for combo_id in selected_store:
        _write_csv(root / "summaries" / "spectra" / f"{combo_id}.csv",
                   _spectrum_rows(spectra[combo_id]))
    plot_ids = [combo_id for combo_id in ["Combo_00", *top3_nonbaseline]
                if combo_id in spectra]
    plot_paths = plots18c.generate_all(root / "plots", results, ranked, spectra, plot_ids)

    summaries = root / "summaries"
    _write_csv(summaries / "demo18c_combo_results.csv", results)
    _write_csv(summaries / "demo18c_ranked_results.csv", ranked)
    _write_csv(summaries / "demo18c_parameter_importance.csv", importance)
    _write_csv(summaries / "state_audit_by_solver_case.csv", all_states)
    _write_csv(summaries / "matrix_elements_by_solver_case.csv", all_matrices)
    master_fields = (
        "combo_id", "closeness_rank", "chi2_1550_pm_per_V", "percent_error",
        "ratio_to_paper", "ratio_to_demo18b", "chi_e_abs", "chi_hh_raw_abs",
        "chi_hh_weighted_abs", "cancellation_factor", "peak_wavelength_nm",
        "bound_state_pass", "solver_pass", "physical_valid", "spectral_match_flag",
    )
    rank_by_id = {row["combo_id"]: row["closeness_rank"] for row in ranked}
    master = [{key: (rank_by_id.get(row["combo_id"]) if key == "closeness_rank" else row.get(key))
               for key in master_fields} for row in results]
    _write_csv(summaries / "demo18c_master_summary.csv", master)

    within20 = [row for row in ranked if float(row["percent_error"]) <= 20.0]
    comparisons: list[dict[str, Any]] = []
    for row in within20:
        comparisons.extend({"combo_id": row["combo_id"], **item}
                           for item in analysis18c.detailed_comparison(baseline, row))
    if comparisons:
        _write_csv(summaries / "demo18c_within20_comparisons.csv", comparisons)
    runlog14.write_text_atomic(
        summaries / "demo18c_best5_analysis.md", _best5_markdown(ranked, baseline)
    )
    summary = {
        "demo_id": cases18c.DEMO_ID,
        "combination_count": len(combos),
        "unique_licensed_solve_count": len(config18c.unique_solver_combinations(combos)),
        "valid_physics_count": len(ranked),
        "failed_physics_count": len(combos) - len(ranked),
        "paper_target_pm_per_V": cfg["chi2"]["paper_target_pm_per_V"],
        "demo18b_baseline_pm_per_V": cfg["chi2"]["demo18b_baseline_pm_per_V"],
        "best": ranked[0] if ranked else None,
        "top5": ranked[:5], "outcome": outcome,
        "parameter_importance": importance, "stored_spectra": selected_store,
        "plots": [str(path) for path in plot_paths],
        "interpretation": (
            "A close case demonstrates only that paper-scale susceptibility is reachable within "
            "the tested uncertainty envelope. It does not identify the authors' unpublished inputs."
        ),
    }
    _write_json(summaries / "demo18c_summary.json", summary)
    return summary


def _terminal_summary(summary: Mapping[str, Any], root: Path) -> None:
    print("DEMO 18C - PAPER MISSING-PARAMETER ENSEMBLE")
    print("=" * 48)
    print(f"Demo 18B baseline : {float(summary['demo18b_baseline_pm_per_V']):11.2f} pm/V")
    print(f"Paper target      : {float(summary['paper_target_pm_per_V']):11.2f} pm/V")
    print(f"Combinations      : {int(summary['combination_count']):11d}")
    print(f"Valid physics     : {int(summary['valid_physics_count']):11d}")
    print(f"Failed physics    : {int(summary['failed_physics_count']):11d}")
    best = summary.get("best")
    if not best:
        print("\nBEST MATCH\n----------\nNone")
    else:
        print("\nBEST MATCH\n----------")
        print(f"Combo: {best['combo_id']}")
        print(f"chi2(1550): {float(best['chi2_1550_pm_per_V']):.3f} pm/V")
        print(f"Paper error: {float(best['percent_error']):.2f}%")
        print(f"Ratio to Demo18B: {float(best['ratio_to_demo18b']):.3f}")
        print(f"Peak wavelength: {float(best['peak_wavelength_nm']):.1f} nm")
        print(f"Peak chi2: {float(best['peak_chi2_pm_per_V']):.3f} pm/V")
        print("\nKEY PARAMETERS\n--------------")
        for label, key in (
            ("r_e_hh", "r_e_hh_nm"), ("electrostatic field", "electrostatic_field_kV_per_cm"),
            ("HH relative weight", "hh_relative_weight"), ("Nz convention", "wells_per_period_for_Nz"),
            ("spin", "spin_degeneracy"), ("kmax", "kmax_fraction_2pi_over_a"),
            ("well1", "well1_nm"), ("well2", "well2_nm"),
            ("barrier", "tunneling_barrier_nm"), ("electron mass scale", "electron_mass_scale"),
            ("HH mass scale", "hh_mass_scale"), ("CB offset scale", "cb_offset_scale"),
            ("HH offset scale", "hh_offset_scale"),
        ):
            print(f"{label}: {best[key]}")
        print("\nCANCELLATION\n------------")
        print(f"Electron contribution: {float(best['chi_e_abs']):.3f} pm/V")
        print(f"HH raw contribution: {float(best['chi_hh_raw_abs']):.3f} pm/V")
        print(f"HH weighted contribution: {float(best['chi_hh_weighted_abs']):.3f} pm/V")
        print(f"Net: {float(best['chi_total_abs']):.3f} pm/V")
        print(f"Cancellation factor: {float(best['cancellation_factor']):.3f}")
    print("\nTOP 5\n-----")
    for index, row in enumerate(summary["top5"], 1):
        print(f"{index}. {row['combo_id']}: {float(row['chi2_1550_pm_per_V']):.2f} pm/V "
              f"({float(row['percent_error']):.2f}% error)")
    estimable = [row for row in summary["parameter_importance"]
                 if math.isfinite(float(row["spearman_rho"]))]
    estimable.sort(key=lambda row: abs(float(row["spearman_rho"])), reverse=True)
    print("\nPARAMETERS MOST ASSOCIATED WITH LARGE CHI2\n------------------------------------------")
    for index, row in enumerate(estimable[:5], 1):
        print(f"{index}. {row['parameter']} (Spearman {float(row['spearman_rho']):+.3f})")
    print(f"\nOUTCOME: {summary['outcome']['outcome']} - {summary['outcome']['label']}")
    print("\nPRIMARY INTERPRETATION:")
    print(summary["interpretation"])
    print(f"\nRESULT DIRECTORY:\n{root}")


def run_preflight(n_combos: int = 20, seed: int = 1803, verbose: bool = False) -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        _validate_cli(n_combos, seed)
        cfg = config18c.load_config()
        combos = config18c.load_combinations()
        digest = cases18c.combinations_sha256(config18c.COMBINATIONS_PATH)
        checks.append(("configuration", True, str(config18c.CONFIG_PATH)))
        checks.append(("frozen combinations", len(combos) == 20,
                       f"SHA256 {digest}"))
        checks.append(("licensed solve deduplication",
                       len(config18c.unique_solver_combinations(combos)) == 17,
                       "20 combinations -> 17 unique solver-level states"))
        deck_hashes = set()
        for combo in config18c.unique_solver_combinations(combos):
            solver_cfg, _case, geometry, _profile, blocks, deck = build_case(cfg, combo)
            compact = " ".join(deck.split())
            if "no_density = yes" not in compact or "run{ quantum{} }" not in compact:
                raise Runner18CError(f"{combo.combo_id}: quantum-only no-density mode missing")
            if "poisson{ electric_field{" not in compact:
                raise Runner18CError(f"{combo.combo_id}: imposed field block missing")
            if "ternary_linear{" in blocks["structure_block"]:
                raise Runner18CError(f"{combo.combo_id}: abrupt structure contains grading")
            if abs(sum((geometry.thick_well_nm, geometry.thin_well_nm, geometry.barrier_nm,
                        float(solver_cfg["geometry"]["period_barrier_nm"]))) - 30.0) > 1e-10:
                raise Runner18CError(f"{combo.combo_id}: period is not 30 nm")
            deck_hashes.add(hashlib.sha256(deck.encode("utf-8")).hexdigest())
        checks.append(("17 distinct solver decks", len(deck_hashes) == 17,
                       f"found {len(deck_hashes)} distinct deck hashes"))
        with config18c.RANGES_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
            range_rows = list(csv.DictReader(stream))
        categories = {row["category"] for row in range_rows}
        checks.append(("parameter classification ledger",
                       {"PUBLISHED", "UNCERTAIN", "CONVENTION", "DIAGNOSTIC PROXY"} <= categories,
                       f"{len(range_rows)} parameters; categories {sorted(categories)}"))
        checks.append(("material override safeguard", all(
            getattr(row, name) == 1.0 for row in combos for name in (
                "electron_mass_scale", "hh_mass_scale", "cb_offset_scale", "hh_offset_scale"
            )), "unsupported overrides fixed at 1.0"))
        parsed = build_parser().parse_args(["--physics", "--n-combos", "20", "--seed", "1803"])
        checks.append(("CLI", parsed.physics and parsed.n_combos == 20 and parsed.seed == 1803,
                       "physics CLI accepts only the frozen experiment values"))
    except Exception as exc:
        checks.append(("preflight execution", False, f"{type(exc).__name__}: {exc}"))
        if verbose:
            traceback.print_exc()
    print(RULE)
    print("DEMO 18C PREFLIGHT - NO LICENSED PHYSICS EXECUTED")
    print(RULE)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        if verbose or not passed:
            print(f"       {detail}")
    passed = bool(checks) and all(row[1] for row in checks)
    print(RULE)
    print("CODE READY FOR LICENSED DEMO 18C RUN" if passed else "PREFLIGHT FAILED")
    print(RULE)
    return 0 if passed else 1


def run_physics(n_combos: int, seed: int, verbose: bool = False) -> int:
    _validate_cli(n_combos, seed)
    cfg = config18c.load_config()
    combos = config18c.load_combinations()
    machine = demo_workflow.load_machine_config()
    if not machine.run_solver:
        raise Runner18CError("--physics requires a licensed machine configuration")
    root, run_id = _run_root(machine)
    log = DebugLog(root / "demo18c_debug.log", verbose)
    status = root / "RUN_STATUS.json"
    digest = cases18c.combinations_sha256(config18c.COMBINATIONS_PATH)
    print(f"demo18c_combinations.csv SHA256: {digest}")
    _write_json(status, {"run_id": run_id, "status": "running", "combinations_sha256": digest})
    try:
        log.section("DEMO 18C START")
        log.record({"run_id": run_id, "git": runlog14.git_facts(REPO_ROOT),
                    "machine": demo_workflow.machine_summary(machine),
                    "combinations_sha256": digest})
        for source in (config18c.CONFIG_PATH, config18c.RANGES_PATH, config18c.COMBINATIONS_PATH):
            shutil.copy2(source, root / "config_snapshot" / source.name)
        if Path(machine.source_path).is_file():
            shutil.copy2(machine.source_path, root / "config_snapshot" / Path(machine.source_path).name)
        _write_yaml(root / "resolved_demo18c_config.yaml", {
            **cfg, "combinations_sha256": digest,
            "machine": demo_workflow.machine_summary(machine),
        })
        _solve_all(cfg, combos, machine, root, log)
        summary = _analyze_all(cfg, combos, root, log)
        _write_json(status, {"run_id": run_id, "status": "completed",
                             "outcome": summary["outcome"], "result_directory": root})
        _terminal_summary(summary, root)
        return 0
    except Exception as exc:
        log.section("FINAL STATUS")
        log.line(traceback.format_exc())
        _write_json(status, {"run_id": run_id, "status": "failed",
                             "error": f"{type(exc).__name__}: {exc}",
                             "result_directory": root})
        print(f"Demo 18C failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"Preserved result directory: {root}", file=sys.stderr)
        return 1


def analyze_existing(
    root: Path, n_combos: int, seed: int, verbose: bool = False,
) -> int:
    _validate_cli(n_combos, seed)
    root = Path(root).resolve()
    if not (root / "solver").is_dir():
        raise Runner18CError(f"{root} has no solver directory")
    for sub in ("summaries", "summaries/spectra", "plots", "logs"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    log = DebugLog(root / "demo18c_reanalysis.log", verbose)
    summary = _analyze_all(config18c.load_config(), config18c.load_combinations(), root, log)
    _terminal_summary(summary, root)
    _write_json(root / "RUN_STATUS.json", {
        "run_id": root.name, "status": "completed",
        "completion_mode": "reanalyzed_existing_solver_outputs",
        "outcome": summary["outcome"], "result_directory": root,
    })
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.physics:
        return run_physics(args.n_combos, args.seed, args.verbose)
    if args.analyze_existing:
        return analyze_existing(args.analyze_existing, args.n_combos, args.seed, args.verbose)
    return run_preflight(args.n_combos, args.seed, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
