"""CLI and licensed workflow for Demo 18B."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from dataclasses import replace
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
    DEMO_DIR, DEMOS / "_shared",
    DEMOS / "11_paper_validation_interband_chi2_acqw",
    DEMOS / "14_absolute_chi2_graded_acqw_bo",
    DEMOS / "16_acqw_renderer_stress_validation",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
    DEMOS / "16F_paper_absolute_chi2_reproduction_audit",
    DEMOS / "18_absolute_chi2_scale_audit",
):
    if str(dependency) not in sys.path:
        sys.path.insert(0, str(dependency))

import numpy as np
import yaml

import audit18b
import cases18b
import config18b
import demo16b
import demo16e
import demo_workflow
import runlog14


RULE = "=" * 78


class Runner18BError(RuntimeError):
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
    parser = argparse.ArgumentParser(description="Demo 18B absolute chi2 reproduction audit")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--physics", action="store_true")
    group.add_argument("--analyze-existing", type=Path, metavar="RUN_DIR")
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
            lowered = str(key).casefold()
            if lowered in folded and folded[lowered] != key:
                raise Runner18BError(
                    f"CSV header collision: {folded[lowered]!r} and {key!r}"
                )
            folded[lowered] = str(key)
            if key not in fields:
                fields.append(str(key))
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
    run_id = f"demo18b_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = Path(machine.results_root) / cases18b.DEMO_ID / run_id
    for sub in (
        "inputs", "solver", "logs", "summaries", "summaries/spectra",
        "plots", "config_snapshot", "cases",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def _case_geometry(cfg: Mapping[str, Any], numerical: cases18b.NumericalCase):
    solver_cfg = config18b.solver_config(cfg, numerical)
    base = demo16e.cases16e.GeometryCase(
        case_id=numerical.case_id,
        name="paper_like_abrupt",
        description=numerical.description,
        asymmetry_s=(7.1 - 2.9) / (7.1 + 2.9),
        central_barrier_nm=1.8,
        left_grading_width_nm=0.0,
        right_grading_width_nm=0.0,
        interface_mode="abrupt",
    )
    geometry, profile, blocks, deck = demo16e.build_case(solver_cfg, base)
    return solver_cfg, base, geometry, profile, blocks, deck


def _copy_logs(case_dir: Path, root: Path, case_id: str) -> None:
    source = case_dir / "physics" / "logs"
    if source.is_dir():
        for item in source.iterdir():
            if item.is_file():
                shutil.copy2(item, root / "logs" / f"{case_id}_{item.name}")


def _solve_all(cfg: Mapping[str, Any], machine: Any, root: Path, log: DebugLog) -> None:
    for index, numerical in enumerate(cases18b.solve_cases(), 1):
        solver_cfg, case, geometry, _profile, _blocks, deck = _case_geometry(cfg, numerical)
        case_dir = root / "cases" / numerical.case_id
        input_path = root / "inputs" / f"{numerical.case_id}.in"
        runlog14.write_text_atomic(input_path, deck)
        _write_json(case_dir / "case_definition.json", numerical.as_record())
        log.section(f"LICENSED SOLVE {index}/{len(cases18b.solve_cases())}: {numerical.case_id}")
        log.record({**numerical.as_record(), "domain_nm": geometry.domain_nm,
                    "generated_input": input_path})
        raw = root / "solver" / numerical.case_id
        record = demo16b.solve_case(
            solver_cfg, case, case_dir, machine=machine,
            raw_output_dir=raw, build=demo16e.build_case,
        )
        _copy_logs(case_dir, root, numerical.case_id)
        _write_json(case_dir / "solver_record.json", record)
        solver = record.get("solver") or {}
        log.record({
            "return_code": solver.get("solver_return_code"),
            "stdout": solver.get("stdout_path"), "stderr": solver.get("stderr_path"),
            "raw_output": raw, "preanalysis_gate": record.get("preanalysis_gate"),
            "physical_gate_passed": record.get("passed"),
            "physical_gate_reason": record.get("failure_reason"),
        })
        if not record.get("preanalysis_gate", {}).get("passed"):
            raise Runner18BError(
                f"{numerical.case_id} solver/output gate failed: {record.get('failure_reason')}"
            )


def _analyze_all(cfg: Mapping[str, Any], root: Path, log: DebugLog) -> dict[str, Any]:
    analyses: dict[str, dict[str, Any]] = {}
    all_states: list[dict[str, Any]] = []
    all_matrices: list[dict[str, Any]] = []
    all_localization: list[dict[str, Any]] = []
    master: list[dict[str, Any]] = []
    for numerical in cases18b.solve_cases():
        solver_cfg, _case, geometry, _profile, _blocks, _deck = _case_geometry(cfg, numerical)
        raw = root / "solver" / numerical.case_id
        if not raw.is_dir():
            raise Runner18BError(f"missing raw solver directory {raw}")
        data = audit18b.load_solved_data(solver_cfg, raw)
        analysis = audit18b.analyze_case(
            cfg, numerical.case_id, data, geometry, numerical.quantum_padding_nm
        )
        analysis["row"].update(numerical.as_record())
        for row in analysis["state_audit"]:
            row["case"] = numerical.case_id
            row["case_id"] = numerical.case_id
        analyses[numerical.case_id] = analysis
        all_states.extend(analysis["state_audit"])
        all_matrices.extend(analysis["matrix_rows"])
        all_localization.extend(analysis["localization"])
        master.append(analysis["row"])
        np.savetxt(
            root / "summaries" / "spectra" / f"{numerical.case_id}.csv",
            np.column_stack((analysis["wavelength_nm"], analysis["chi2"].real,
                             analysis["chi2"].imag, np.abs(analysis["chi2"]))),
            delimiter=",", header="wavelength_nm,chi2_real,chi2_imag,chi2_magnitude",
            comments="",
        )
        log.section(f"ANALYSIS: {numerical.case_id}")
        log.record(analysis["row"])
        log.line("BOUND STATES")
        log.record([row for row in analysis["state_audit"] if row["state"] <= 2])

    domain_ids = ("D0_reference", "D1_plus10", "D2_plus20", "D3_plus40")
    mesh_ids = tuple(case_id for case_id, _ in cases18b.mesh_cases_with_alias())
    domain_rows = audit18b.convergence_rows(
        analyses, domain_ids, reference_case="D3_plus40"
    )
    mesh_rows = audit18b.convergence_rows(
        analyses, mesh_ids, reference_case="M2_0p025nm"
    )
    domain_verdict = audit18b.convergence_verdict(
        domain_rows, cfg["convergence_tolerances"]
    )
    mesh_verdict = audit18b.convergence_verdict(
        mesh_rows, cfg["convergence_tolerances"]
    )
    best = analyses["M2_0p025nm"]
    e, h = best["electron"], best["heavy_hole"]
    native_rows, native_summary = audit18b.native_matrix_comparison(
        best["data"].raw_dir, best["data"].electron, best["data"].heavy_hole
    )
    eq2 = audit18b.eq2_cross_check(
        e, h, audit18b.primary_settings(cfg), float(cfg["chi2"]["target_wavelength_nm"])
    )
    origin = audit18b.origin_audit(cfg, e, h)
    state_counts = audit18b.state_count_audit(
        cfg, best["data"].electron, best["data"].heavy_hole, best["state_audit"]
    )
    conventions = audit18b.convention_audit(cfg, e, h)
    k_rows = audit18b.k_saturation_audit(cfg, e, h)
    k_cutoff_relative_change = float(k_rows[-1]["incremental_relative_change"])
    k_grid_relative_change = float(k_rows[-1]["grid_refinement_relative_change"])
    k_tolerance = float(cfg["convergence_tolerances"]["chi2_relative"])
    k_convergence = {
        "passed": k_cutoff_relative_change <= k_tolerance
        and k_grid_relative_change <= k_tolerance,
        "cutoff_comparison": (
            f"{k_rows[-2]['fraction_of_2pi_over_a']:.2f} to "
            f"{k_rows[-1]['fraction_of_2pi_over_a']:.2f} times 2pi/a"
        ),
        "cutoff_relative_change": k_cutoff_relative_change,
        "grid_comparison": (
            f"{k_rows[-1]['k_points']} to {k_rows[-1]['grid_refinement_points']} points"
        ),
        "grid_relative_change": k_grid_relative_change,
        "tolerance": k_tolerance,
    }
    converged_k_settings = replace(
        audit18b.primary_settings(cfg),
        k_parallel_fraction_of_bz=2.0 * float(k_rows[-1]["fraction_of_2pi_over_a"]),
        k_parallel_points=int(k_rows[-1]["grid_refinement_points"]),
    )
    eq2_converged_k = audit18b.eq2_cross_check(
        e, h, converged_k_settings, float(cfg["chi2"]["target_wavelength_nm"])
    )
    r_audit = audit18b.r_ehh_audit(cfg, best["row"]["chi2_1550_pm_per_V"])
    ledger = audit18b.degeneracy_ledger()
    native_pass = (
        native_summary["max_absolute_overlap_difference"]
        <= float(cfg["convergence_tolerances"]["native_overlap_absolute"])
        and native_summary["max_absolute_dipole_difference_nm"]
        <= float(cfg["convergence_tolerances"]["native_matrix_absolute_nm"])
    )
    independent_pass = (
        eq2["relative_difference"]
        <= float(cfg["convergence_tolerances"]["independent_eq2_relative"])
        and eq2_converged_k["relative_difference"]
        <= float(cfg["convergence_tolerances"]["independent_eq2_relative"])
    )
    bound_pass = bool(best["row"]["strict_selected_states_bound_pass"])
    classification = audit18b.classify(
        bound_pass=bound_pass, domain_converged=domain_verdict["passed"],
        mesh_converged=mesh_verdict["passed"], k_converged=k_convergence["passed"],
        native_pass=native_pass,
        independent_pass=independent_pass,
        best_chi2=float(best["row"]["chi2_1550_pm_per_V"]),
        paper_target=float(cfg["diagnostics"]["paper_target_pm_per_V"]),
    )
    diagonal_groups: dict[str, complex] = {}
    for row in eq2["term_rows"]:
        key = f"{row['path']}_{row['z_kind']}"
        diagonal_groups[key] = diagonal_groups.get(key, 0.0j) + complex(
            float(row["contribution_pm_per_V_real"]),
            float(row["contribution_pm_per_V_imag"]),
        )
    hh_delta_reference = float(analyses["D0_reference"]["row"]["delta_z_hh_nm"])
    hh_delta_best = float(best["row"]["delta_z_hh_nm"])
    hh_delta_relative_change = abs(hh_delta_best - hh_delta_reference) / max(
        abs(hh_delta_best), 1.0e-30
    )
    selected_hh = [int(value) for value in best["row"]["selected_heavy_hole_states"]]
    if not domain_verdict["passed"]:
        hh_delta_diagnosis = "unresolved_domain_truncation_or_boundary_sensitivity"
    elif hh_delta_relative_change > float(cfg["convergence_tolerances"]["matrix_relative"]):
        hh_delta_diagnosis = "reference_domain_was_boundary_sensitive_but_large_domain_converged"
    elif selected_hh != [1, 2]:
        hh_delta_diagnosis = "state_ordering_or_wrong_heavy_hole_state_identity"
    elif native_pass:
        hh_delta_diagnosis = "physically_stable_for_the_selected_one_band_states"
    else:
        hh_delta_diagnosis = "matrix_extraction_requires_resolution"
    diagonal_physics = {
        "delta_z_e_nm": best["row"]["delta_z_e_nm"],
        "delta_z_hh_nm": hh_delta_best,
        "delta_z_hh_reference_nm": hh_delta_reference,
        "delta_z_hh_domain_relative_change": hh_delta_relative_change,
        "diagnosis": hh_delta_diagnosis,
        "term_group_sums_pm_per_V": diagonal_groups,
        "term_group_magnitudes_pm_per_V": {
            key: abs(value) for key, value in diagonal_groups.items()
        },
        "interpretation": (
            "A material domain effect is indicated if delta_z_hh changes materially "
            "across the domain ladder; otherwise the small value is stable for this "
            "solved state identity and points to state/model physics rather than extraction."
        ),
    }
    dominant_terms = {
        path: next(row for row in eq2["term_rows"] if row["path"] == path)
        for path in ("electron", "heavy_hole")
    }

    _write_csv(root / "summaries" / "state_audit.csv", all_states)
    _write_csv(root / "summaries" / "matrix_elements.csv", all_matrices)
    _write_csv(root / "summaries" / "state_localization.csv", all_localization)
    _write_csv(root / "summaries" / "domain_convergence.csv", domain_rows)
    _write_csv(root / "summaries" / "mesh_convergence.csv", mesh_rows)
    _write_csv(root / "summaries" / "eq2_terms.csv", eq2["term_rows"])
    _write_csv(root / "summaries" / "convention_audit.csv", conventions)
    _write_csv(root / "summaries" / "native_matrix_comparison.csv", native_rows)
    _write_csv(root / "summaries" / "state_count_convergence.csv", state_counts)
    _write_csv(root / "summaries" / "origin_invariance.csv", origin)
    _write_csv(root / "summaries" / "k_saturation.csv", k_rows)
    _write_csv(root / "summaries" / "degeneracy_ledger.csv", ledger)
    _write_csv(root / "summaries" / "demo18b_master_summary.csv", master)

    from plots18b import generate_all
    plot_paths = generate_all(
        root / "plots", best, domain_rows, mesh_rows, k_rows,
        eq2["term_rows"], eq2, float(cfg["diagnostics"]["paper_target_pm_per_V"]),
    )
    reference_ratio = analyses["D0_reference"]["row"]["chi2_1550_pm_per_V"] / float(
        cfg["diagnostics"]["demo18_adjusted_pm_per_V"]
    )
    summary = {
        "demo_id": cases18b.DEMO_ID,
        "reference_reproduction": {
            "demo18_expected_pm_per_V": cfg["diagnostics"]["demo18_adjusted_pm_per_V"],
            "demo18b_reference_pm_per_V": analyses["D0_reference"]["row"]["chi2_1550_pm_per_V"],
            "ratio": reference_ratio,
        },
        "best_reproduction": best["row"],
        "paper_target_pm_per_V": cfg["diagnostics"]["paper_target_pm_per_V"],
        "remaining_ratio": float(cfg["diagnostics"]["paper_target_pm_per_V"])
        / max(float(best["row"]["chi2_1550_pm_per_V"]), 1e-30),
        "bound_state_audit_passed": bound_pass,
        "domain_convergence": domain_verdict,
        "mesh_convergence": mesh_verdict,
        "native_matrix_validation": {**native_summary, "passed": native_pass},
        "independent_eq2": {key: value for key, value in eq2.items() if key != "term_rows"},
        "independent_eq2_converged_k": {
            key: value for key, value in eq2_converged_k.items() if key != "term_rows"
        },
        "independent_eq2_passed": independent_pass,
        "origin_invariance": origin,
        "state_count_convergence": state_counts,
        "k_convergence": k_convergence,
        "r_e_hh_audit": r_audit,
        "dominant_terms": dominant_terms,
        "diagonal_matrix_physics": diagonal_physics,
        "poisson_audit": audit18b.poisson_audit(),
        "classification": classification,
        "plots": plot_paths,
    }
    _write_json(root / "summaries" / "demo18b_summary.json", summary)
    log.section("FINAL AUDIT SUMMARY")
    log.record(summary)
    return summary


def run_preflight(verbose: bool = False) -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        cfg = config18b.load_config()
        checks.append(("configuration", True, str(config18b.CONFIG_PATH)))
        decks = []
        fingerprints = set()
        for numerical in cases18b.solve_cases():
            solver_cfg, _case, geometry, _profile, _blocks, deck = _case_geometry(cfg, numerical)
            decks.append(deck)
            fingerprints.add((geometry.domain_nm, numerical.quantum_padding_nm, numerical.mesh_nm))
            if "no_density = yes" not in deck:
                raise Runner18BError(f"{numerical.case_id}: current equation mode not visible")
            if float(solver_cfg["geometry"]["period_barrier_nm"]) != 18.2:
                raise Runner18BError("physical period barrier changed")
        checks.append((
            "six unique convergence decks", len(fingerprints) == 6,
            "four domains; largest 0.05 nm deck reused in mesh ladder",
        ))
        checks.append((
            "Schrodinger-only mode documented", all("no_density = yes" in deck for deck in decks),
            "paper Poisson charge/boundary inputs are unavailable",
        ))

        # Analytic integration on a deliberately nonuniform grid.
        u = np.linspace(0.0, 1.0, 2001)
        z = 10.0 * u**1.35
        psi1 = np.sqrt(2.0 / 10.0) * np.sin(np.pi * z / 10.0)
        psi2 = np.sqrt(2.0 / 10.0) * np.sin(2.0 * np.pi * z / 10.0)
        e = audit18b.production_chi2.BandStates(
            z, np.asarray([2.95, 3.08]), np.column_stack((psi1, psi2)), "e"
        )
        h1 = 0.96 * psi1 + np.sqrt(1.0 - 0.96**2) * psi2
        h2 = -np.sqrt(1.0 - 0.96**2) * psi1 + 0.96 * psi2
        h = audit18b.production_chi2.BandStates(
            z, np.asarray([1.45, 1.40]), np.column_stack((h1, h2)), "hh"
        )
        overlap, z_e, _z_h = audit18b.matrices(e, h)
        analytic_z12 = -16.0 * 10.0 / (9.0 * np.pi**2)
        checks.append((
            "analytic/nonuniform matrix integrals",
            abs(abs(z_e[0, 1]) - abs(analytic_z12)) < 2.0e-5
            and abs(float(np.trapezoid(e.envelopes[:, 0] ** 2, z)) - 1.0) < 1e-12
            and np.isfinite(overlap).all(),
            f"z12={z_e[0,1]:.9g} nm, analytic={analytic_z12:.9g} nm",
        ))
        settings = audit18b.primary_settings(cfg)
        cross = audit18b.eq2_cross_check(e, h, settings, 1550.0)
        checks.append((
            "independent Eq. 2", cross["relative_difference"] <= 1e-12,
            f"relative residual={cross['relative_difference']:.3e}",
        ))
        origin_e, origin_h = audit18b.demo18.synthetic_states()
        origin = audit18b.origin_audit(cfg, origin_e, origin_h)
        checks.append((
            "coordinate-origin invariance", all(row["passed"] for row in origin),
            ", ".join(f"{row['shift_nm']:g} nm: {row['relative_residual']:.3e}" for row in origin),
        ))

        fixture = (
            REPO_ROOT / "nextnano" / "tests" / "fixtures" / "nextnano_pp_3_0_0"
            / "demo11_acqw_paper"
        )
        ref_case = cases18b.solve_cases()[0]
        solver_cfg = config18b.solver_config(cfg, ref_case)
        fixture_data = audit18b.load_solved_data(solver_cfg, fixture)
        native_rows, native = audit18b.native_matrix_comparison(
            fixture, fixture_data.electron, fixture_data.heavy_hole
        )
        checks.append((
            "native nextnano matrix parser/comparison", bool(native_rows)
            and native["max_absolute_dipole_difference_nm"] < 0.01
            and native["max_absolute_overlap_difference"] < 0.01,
            json.dumps(native, sort_keys=True),
        ))
        r_audit = audit18b.r_ehh_audit(
            cfg, float(cfg["diagnostics"]["demo18_adjusted_pm_per_V"])
        )
        checks.append((
            "r_e_hh fitted-value labeling",
            r_audit["classification"] == "fitted_hypothetical_not_a_paper_value",
            f"hypothetical only: {r_audit['hypothetical_fitted_r_e_hh_nm']:.4g} nm",
        ))
        temp = DEMO_DIR / ".preflight_csv.tmp"
        try:
            _write_csv(temp, [{"nz_convention": "explicit", "chi2_1550": 1.0}])
            header = temp.read_text(encoding="utf-8").splitlines()[0].split(",")
            unique = len({name.casefold() for name in header}) == len(header)
        finally:
            temp.unlink(missing_ok=True)
        checks.append(("case-insensitive CSV headers", unique, str(header)))
        parsed = build_parser().parse_args(["--preflight"])
        checks.append(("CLI", parsed.preflight and not parsed.physics, "--preflight"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("preflight execution", False, f"{type(exc).__name__}: {exc}"))
        if verbose:
            traceback.print_exc()
    print(RULE)
    print("DEMO 18B PREFLIGHT")
    print(RULE)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        if verbose or not passed:
            print(f"       {detail}")
    passed = bool(checks) and all(row[1] for row in checks)
    print(RULE)
    print("CODE READY FOR LICENSED DEMO 18B RUN" if passed else "PREFLIGHT FAILED")
    print(RULE)
    return 0 if passed else 1


def _terminal_summary(summary: Mapping[str, Any], root: Path) -> None:
    best = summary["best_reproduction"]
    native = summary["native_matrix_validation"]
    independent = summary["independent_eq2"]
    terms_path = root / "summaries" / "eq2_terms.csv"
    state_rows = list(csv.DictReader((root / "summaries" / "state_audit.csv").open(
        encoding="utf-8", newline=""
    )))
    best_state_rows = [row for row in state_rows if row["case_id"] == "M2_0p025nm"]
    print("DEMO 18B - ABSOLUTE CHI2 REPRODUCTION AUDIT")
    print("=" * 48)
    print(f"\nReference Demo18 chi2(1550): {summary['reference_reproduction']['demo18b_reference_pm_per_V']:.6g} pm/V")
    print(f"Best reproduction chi2(1550): {best['chi2_1550_pm_per_V']:.6g} pm/V")
    print(f"Paper abrupt target: {summary['paper_target_pm_per_V']:.6g} pm/V")
    print(f"Remaining ratio: {summary['remaining_ratio']:.6g}x")
    print("\nBOUND STATE AUDIT")
    for band, prefix, key in (
        ("electron", "E", "selected_electron_states"),
        ("heavy_hole", "HH", "selected_heavy_hole_states"),
    ):
        for paper_index, solver_index in enumerate(best[key], 1):
            row = next(r for r in best_state_rows if r["band"] == band and int(r["state"]) == int(solver_index))
            print(f"{prefix}{paper_index} (solver state {solver_index}): "
                  f"{'PASS' if row['bound_pass'] == 'True' else 'FAIL'}")
    print("\nCONVERGENCE")
    print(f"Domain converged: {summary['domain_convergence']['passed']}")
    print(f"Mesh converged: {summary['mesh_convergence']['passed']}")
    print(f"k cutoff converged ({summary['k_convergence']['cutoff_comparison']}): "
          f"{summary['k_convergence']['passed']} "
          f"(cutoff change {summary['k_convergence']['cutoff_relative_change']:.3e}, "
          f"grid change {summary['k_convergence']['grid_relative_change']:.3e})")
    print("\nMATRIX VALIDATION")
    print(f"Python vs Nextnano overlap max abs: {native['max_absolute_overlap_difference']:.3e}")
    print(f"Python vs Nextnano dipole max abs: {native['max_absolute_dipole_difference_nm']:.3e} nm")
    print(f"Independent Eq2 relative residual: {independent['relative_difference']:.3e}")
    def magnitude(value: Any) -> float:
        if isinstance(value, Mapping):
            return abs(complex(float(value["real"]), float(value["imag"])))
        return abs(complex(value))

    print("\nDOMINANT TERMS")
    for path, label in (("electron", "Largest electron term"), ("heavy_hole", "Largest HH term")):
        row = summary["dominant_terms"][path]
        print(f"{label}: m={row['m_hh_state']}, n={row['n_electron_state']}, "
              f"l={row['l_partner_state']}, |term|="
              f"{row['contribution_pm_per_V_magnitude']:.6g} pm/V")
    print(f"Net electron contribution: {magnitude(independent['electron_contribution']):.6g} pm/V")
    print(f"Net HH contribution: {magnitude(independent['heavy_hole_contribution']):.6g} pm/V")
    print(f"Cancellation factor: {independent['cancellation_factor']:.6g}")
    print(f"Small HH diagonal diagnosis: {summary['diagonal_matrix_physics']['diagnosis']}")
    print("\nCONVENTIONS")
    print("Nz: two wells per 30 nm period")
    print("kmax: 0.10(2pi/a), 384 points primary")
    print("spin: 2, explicit in radial weights")
    print(f"r_ehh: {best['r_e_hh_nm']} nm repository assumption")
    print(f"\nPRIMARY DIAGNOSIS:\n{summary['classification']['category']} - {summary['classification']['primary_diagnosis']}")
    print(f"\nRESULT DIRECTORY:\n{root}")
    print(f"\nMASTER SUMMARY:\n{root / 'summaries' / 'demo18b_master_summary.csv'}")
    print(f"\nTERM TABLE:\n{terms_path}")


def run_physics(verbose: bool = False) -> int:
    cfg = config18b.load_config()
    machine = demo_workflow.load_machine_config()
    if not machine.run_solver:
        raise Runner18BError("--physics requires a licensed machine configuration")
    root, run_id = _run_root(machine)
    log = DebugLog(root / "demo18b_debug.log", verbose)
    status = root / "RUN_STATUS.json"
    _write_json(status, {"run_id": run_id, "status": "running"})
    try:
        log.section("DEMO 18B START")
        log.record({"run_id": run_id, "git": runlog14.git_facts(REPO_ROOT),
                    "machine": demo_workflow.machine_summary(machine)})
        snapshot = config18b.resolved_snapshot(cfg, machine)
        _write_yaml(root / "resolved_demo18b_config.yaml", snapshot)
        shutil.copy2(config18b.CONFIG_PATH, root / "config_snapshot" / "demo18b.yaml")
        if Path(machine.source_path).is_file():
            shutil.copy2(machine.source_path, root / "config_snapshot" / Path(machine.source_path).name)
        _solve_all(cfg, machine, root, log)
        summary = _analyze_all(cfg, root, log)
        _write_json(status, {"run_id": run_id, "status": "completed",
                             "classification": summary["classification"],
                             "result_directory": root})
        log.section("FINAL STATUS")
        log.line("COMPLETED")
        log.record({"classification": summary["classification"],
                    "master_summary": root / "summaries" / "demo18b_master_summary.csv"})
        _terminal_summary(summary, root)
        return 0
    except Exception as exc:  # noqa: BLE001
        trace = traceback.format_exc()
        log.section("FINAL STATUS")
        log.line("FAILED")
        log.line(trace)
        _write_json(status, {"run_id": run_id, "status": "failed",
                             "error": f"{type(exc).__name__}: {exc}",
                             "result_directory": root, "debug_log": log.path})
        print(f"Demo 18B failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"Preserved result directory: {root}", file=sys.stderr)
        print(f"Debug log: {log.path}", file=sys.stderr)
        return 1


def analyze_existing(root: Path, verbose: bool = False) -> int:
    root = Path(root).resolve()
    if not (root / "solver").is_dir():
        raise Runner18BError(f"{root} has no solver/ directory")
    for sub in ("summaries", "summaries/spectra", "plots", "logs"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    log = DebugLog(root / "demo18b_reanalysis.log", verbose)
    summary = _analyze_all(config18b.load_config(), root, log)
    _terminal_summary(summary, root)
    _write_json(root / "RUN_STATUS.json", {
        "run_id": root.name,
        "status": "completed",
        "completion_mode": "reanalyzed_existing_solver_outputs",
        "classification": summary["classification"],
        "result_directory": root,
    })
    log.section("FINAL STATUS")
    log.line("COMPLETED FROM PRESERVED SOLVER OUTPUTS")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.physics:
        return run_physics(args.verbose)
    if args.analyze_existing:
        return analyze_existing(args.analyze_existing, args.verbose)
    return run_preflight(args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
