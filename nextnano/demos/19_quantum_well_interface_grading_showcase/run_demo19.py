"""CLI for Demo 19. Only ``--physics`` may launch licensed Nextnano++ solves."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import sys
import uuid
from typing import Any, Mapping

import numpy as np


DEMO_DIR = Path(__file__).resolve().parent
DEMOS_DIR = DEMO_DIR.parent
PATHS = (
    DEMOS_DIR / "_shared",
    DEMOS_DIR / "11_paper_validation_interband_chi2_acqw",
    DEMOS_DIR / "12_graded_interface_coupled_quantum_well_optimization",
    DEMOS_DIR / "14_absolute_chi2_graded_acqw_bo",
    DEMOS_DIR / "16_acqw_renderer_stress_validation",
    DEMOS_DIR / "16B_simple_acqw_grading_validation",
    DEMOS_DIR / "16E_acqw_structure_physics_optical_comparison",
    DEMO_DIR,
)
for _path in PATHS:
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import cases19  # noqa: E402
import demo14  # noqa: E402
import demo16b  # noqa: E402
import demo16e  # noqa: E402
import demo19  # noqa: E402
import demo_workflow  # noqa: E402
import plots19  # noqa: E402
import runlog14  # noqa: E402
import solver14  # noqa: E402


MASTER_FILENAME = "demo19_master_results.csv"
PRESENTATION_FILENAME = "demo19_presentation_table.csv"
BOSS_SUMMARY_FILENAME = "demo19_boss_summary.md"
MASTER_FIELDS = [
    "case_id", "case_name", "profile",
    "I1_width_nm", "I2_width_nm", "I3_width_nm", "I4_width_nm",
    "nominal_grade_width_nm",
    "E1_HH1_eV", "E1_HH2_eV", "E2_HH1_eV", "E2_HH2_eV",
    "z_e12_nm", "z_hh12_nm", "delta_z_e_nm", "delta_z_hh_nm",
    "O11", "O12", "O21", "O22",
    "chi2_1550_pm_per_V", "chi2_1550_relative_to_abrupt",
    "peak_chi2_pm_per_V", "peak_chi2_relative_to_abrupt", "peak_wavelength_nm",
    "grading_validation_pass", "solver_pass", "physical_valid",
    "E1_eV", "E2_eV", "HH1_eV", "HH2_eV",
    "z_e11_nm", "z_e21_nm", "z_e22_nm",
    "z_hh11_nm", "z_hh21_nm", "z_hh22_nm",
    "electron_E1_centroid_nm", "electron_E2_centroid_nm",
    "HH1_centroid_nm", "HH2_centroid_nm",
    "solver_return_code", "failure_stage", "failure_reason", "spectrum_path",
]


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _pending_rows() -> list[dict[str, Any]]:
    rows = []
    for case in cases19.all_cases():
        row = {field: "" for field in MASTER_FIELDS}
        row.update({
            "case_id": case.case_id, "case_name": case.case_name, "profile": case.profile,
            "nominal_grade_width_nm": case.nominal_grade_width_nm,
            "grading_validation_pass": demo19.validate_realized(case)["validation_pass"],
            "solver_pass": False, "physical_valid": False,
            "failure_stage": "licensed_physics_pending",
            "failure_reason": "No solver output: run --physics on the configured licensed work laptop.",
        })
        for interface_id in cases19.INTERFACE_IDS:
            row[f"{interface_id}_width_nm"] = case.width(interface_id)
        rows.append(row)
    return rows


def _presentation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "Case": row["case_name"], "Profile": row["profile"],
        "I1": row["I1_width_nm"], "I2": row["I2_width_nm"],
        "I3": row["I3_width_nm"], "I4": row["I4_width_nm"],
        "chi2_1550": row.get("chi2_1550_pm_per_V", ""),
        "Relative_to_abrupt": row.get("chi2_1550_relative_to_abrupt", ""),
        "Peak_nm": row.get("peak_wavelength_nm", ""),
    } for row in rows]


def write_boss_summary(path: Path, rows: list[dict[str, Any]]) -> Path:
    valid = [row for row in rows if row.get("physical_valid") in (True, "True", "true", 1)]
    if not valid:
        key_results = [
            "- The 13 requested grading definitions and all four named interfaces passed solver-free realization checks.",
            "- No requested grading intervals overlap.",
            "- Licensed band-structure and susceptibility results are pending; no synthetic physics is substituted.",
        ]
        takeaway = "The controlled input workflow is ready. Quantitative conclusions require the 13 licensed solves."
    else:
        abrupt = next(row for row in valid if row["case_id"] == "00")
        farthest = max(valid, key=lambda row: abs(float(row["chi2_1550_relative_to_abrupt"]) - 1.0))
        key_results = [
            f"- Abrupt |χ²(1550)|: {float(abrupt['chi2_1550_pm_per_V']):.4g} pm/V.",
            f"- Abrupt spectral peak: {float(abrupt['peak_wavelength_nm']):.1f} nm.",
            f"- Largest 1550 nm change: {farthest['case_name']} at {float(farthest['chi2_1550_relative_to_abrupt']):.3f}× abrupt.",
            f"- {len(valid)}/{len(rows)} cases passed all composition, solver, state, matrix and optical gates.",
        ]
        takeaway = (
            f"Within this model, {farthest['case_name']} differs most from the abrupt reference at 1550 nm. "
            "The comparison changes interface grading only; it is not a claim of absolute experimental agreement."
        )
    text = "\n".join([
        "# Demo 19 — Interface Grading Showcase", "",
        "## What was changed", "",
        "The same 7.1 / 1.8 / 2.9 nm coupled-QW structure was used in every case. Only interface grading was varied.", "",
        "## How grading was specified", "",
        "The Al fraction x_Al changes from 0 to 0.55 across a controlled full transition width centered on each nominal interface. A 0.7 nm linear grade ramps between GaAs and Al0.55Ga0.45As over exactly 0.7 nm.", "",
        "## What Nextnano calculated", "",
        "Band edges, wavefunctions, electron and heavy-hole energy levels, overlaps, dipoles and centroids.", "",
        "## What Python calculated afterward", "",
        "The 1400–1800 nm χ² spectrum, |χ²| at 1550 nm, peak wavelength, and normalized comparisons with abrupt.", "",
        "## Key results", "", *key_results, "",
        "## Main takeaway", "", takeaway, "",
    ])
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def run_preflight(verbose: bool = False) -> int:
    report = demo19.preflight_report()
    tables = demo19.write_preflight_tables(DEMO_DIR)
    examples = demo19.write_input_examples()
    output = DEMO_DIR / "preflight_output"
    output.mkdir(parents=True, exist_ok=True)
    demo19.write_case_inputs(output)
    plots = plots19.input_plots(output / "plots")
    rows = _pending_rows()
    master = _write_csv(DEMO_DIR / MASTER_FILENAME, rows, MASTER_FIELDS)
    presentation = _write_csv(
        DEMO_DIR / PRESENTATION_FILENAME, _presentation_rows(rows),
        ["Case", "Profile", "I1", "I2", "I3", "I4", "chi2_1550", "Relative_to_abrupt", "Peak_nm"],
    )
    boss = write_boss_summary(DEMO_DIR / BOSS_SUMMARY_FILENAME, rows)
    (output / "preflight_report.json").write_text(
        json.dumps(report, indent=2, default=_json_default),
        encoding="utf-8", newline="\n",
    )
    status = 0 if report["all_grading_valid"] and report["all_decks_complete"] else 1
    print("DEMO 19 — PREFLIGHT")
    print("=" * 78)
    print(f"Cases: {report['case_count']}  grading-valid: {sum(v['validation_pass'] for v in report['validations'])}")
    print(f"Overlap cases: {report['overlap_cases'] or 'none'}")
    print("Licensed solves performed: 0")
    print(f"Case table: {tables['cases']}")
    print(f"Validation: {tables['validation']}")
    print(f"Input examples: {examples}")
    print(f"Input plots: {', '.join(str(p) for p in plots)}")
    print(f"Pending master table: {master}")
    print(f"Presentation table: {presentation}")
    print(f"Boss summary: {boss}")
    if verbose:
        for deck in report["decks"]:
            print(f"  case_{deck['case_id']}: deck={deck['deck_complete']} imported={deck['datafile_required']}")
    return status


def _machine():
    machine = demo_workflow.load_machine_config()
    missing = [
        str(path) for path in (Path(machine.executable), Path(machine.database), Path(machine.license))
        if not path.is_file()
    ]
    if missing:
        raise RuntimeError("licensed machine configuration resolves missing file(s): " + "; ".join(missing))
    if not machine.run_solver:
        raise RuntimeError("machine configuration has run_solver disabled")
    return machine


def _new_run(machine) -> Path:
    facts = runlog14.git_facts(DEMO_DIR.parents[2])
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo19_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = Path(machine.results_root) / cases19.DEMO_ID / run_id
    for child in ("cases", "plots", "tables", "inputs"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def _base_row(case: cases19.GradingCase) -> dict[str, Any]:
    row = {field: "" for field in MASTER_FIELDS}
    row.update({
        "case_id": case.case_id, "case_name": case.case_name, "profile": case.profile,
        "nominal_grade_width_nm": case.nominal_grade_width_nm,
        "grading_validation_pass": demo19.validate_realized(case)["validation_pass"],
        "solver_pass": False, "physical_valid": False,
    })
    for interface_id in cases19.INTERFACE_IDS:
        row[f"{interface_id}_width_nm"] = case.width(interface_id)
    return row


def _matrix(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        np.asarray(payload["position_matrix_electron_nm"], float),
        np.asarray(payload["position_matrix_heavy_hole_nm"], float),
        np.asarray(payload["overlap_electron_hole"], float),
    )


def _populate_physics_row(
    row: dict[str, Any], metrics: Mapping[str, Any], matrix_path: Path,
    localization: Mapping[str, Any], optical: Mapping[str, Any], invocation: Any,
) -> None:
    e = np.asarray(metrics["electron_energies_eV"], float)
    h = np.asarray(metrics["heavy_hole_energies_eV"], float)
    z_e, z_h, overlap = _matrix(matrix_path)
    row.update({
        "E1_eV": e[0], "E2_eV": e[1], "HH1_eV": h[0], "HH2_eV": h[1],
        "E1_HH1_eV": e[0] - h[0], "E1_HH2_eV": e[0] - h[1],
        "E2_HH1_eV": e[1] - h[0], "E2_HH2_eV": e[1] - h[1],
        "z_e11_nm": z_e[0, 0], "z_e12_nm": z_e[0, 1], "z_e21_nm": z_e[1, 0], "z_e22_nm": z_e[1, 1],
        "z_hh11_nm": z_h[0, 0], "z_hh12_nm": z_h[0, 1], "z_hh21_nm": z_h[1, 0], "z_hh22_nm": z_h[1, 1],
        "delta_z_e_nm": z_e[1, 1] - z_e[0, 0], "delta_z_hh_nm": z_h[1, 1] - z_h[0, 0],
        "O11": overlap[0, 0], "O12": overlap[0, 1], "O21": overlap[1, 0], "O22": overlap[1, 1],
        "chi2_1550_pm_per_V": optical["chi2_at_1550"],
        "peak_chi2_pm_per_V": optical["spectral_peak_chi2"],
        "peak_wavelength_nm": optical["spectral_peak_wavelength_nm"],
        "spectrum_path": optical["spectrum_path"],
        "solver_return_code": invocation.return_code,
    })
    states = localization["by_state"]
    row.update({
        "electron_E1_centroid_nm": states["E1"]["centroid_nm"],
        "electron_E2_centroid_nm": states["E2"]["centroid_nm"],
        "HH1_centroid_nm": states["HH1"]["centroid_nm"],
        "HH2_centroid_nm": states["HH2"]["centroid_nm"],
    })


def _write_wave_plot_data(path: Path, waves: Any) -> None:
    z = waves.position_nm
    band_z = waves.band_position_nm
    edges = waves.band_edges
    conduction = next((edges[k] for k in ("conduction_eV", "conduction", "Gamma", "gamma", "electron") if k in edges), None)
    heavy = next((edges[k] for k in ("heavy_hole_eV", "heavy_hole", "HH", "hh", "valence") if k in edges), None)
    if conduction is None or heavy is None:
        return
    conduction = np.interp(z, band_z, conduction)
    heavy = np.interp(z, band_z, heavy)
    columns = [z, conduction, heavy]
    for energy, density, sign in (
        (waves.electron_energies_eV[0], waves.electron_densities[:, 0], 1),
        (waves.electron_energies_eV[1], waves.electron_densities[:, 1], 1),
        (waves.hole_energies_eV[0], waves.hole_densities[:, 0], -1),
        (waves.hole_energies_eV[1], waves.hole_densities[:, 1], -1),
    ):
        scale = np.max(np.abs(density)) or 1.0
        columns.append(float(energy) + sign * 0.08 * density / scale)
    np.savetxt(path, np.column_stack(columns), delimiter=",",
               header="z_nm,conduction_eV,heavy_hole_eV,E1,E2,HH1,HH2", comments="")


def _optics(cfg, case, case_dir: Path, raw: Path, g, profile) -> tuple[dict[str, Any], dict[str, Any]]:
    optical_root = case_dir / "optical"
    parsed, plot_dir = optical_root / "parsed", optical_root / "plots"
    parsed.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)
    metrics = demo14.analyse_real_trial(
        cfg, {"nextnano_output": raw, "parsed": parsed, "plots": plot_dir}, g, profile
    )
    spectrum = np.loadtxt(parsed / "chi2_focused.csv", delimiter=",", skiprows=1)
    magnitude = np.asarray(spectrum[:, 3], float)
    wavelengths = np.asarray(spectrum[:, 0], float)
    peak = int(np.argmax(magnitude))
    optical = {
        "chi2_at_1550": float(np.interp(1550.0, wavelengths, magnitude)),
        "spectral_peak_chi2": float(magnitude[peak]),
        "spectral_peak_wavelength_nm": float(wavelengths[peak]),
        "spectrum_path": str(parsed / "chi2_focused.csv"),
        "chi2_units": metrics.get("chi2_units"),
    }
    (optical_root / "optical_result.json").write_text(json.dumps(optical, indent=2), encoding="utf-8", newline="\n")
    return metrics, optical


def _normalize(rows: list[dict[str, Any]]) -> None:
    abrupt = next((row for row in rows if row["case_id"] == "00" and row["physical_valid"]), None)
    if abrupt is None:
        return
    c0, p0 = float(abrupt["chi2_1550_pm_per_V"]), float(abrupt["peak_chi2_pm_per_V"])
    for row in rows:
        if row["physical_valid"]:
            row["chi2_1550_relative_to_abrupt"] = float(row["chi2_1550_pm_per_V"]) / c0
            row["peak_chi2_relative_to_abrupt"] = float(row["peak_chi2_pm_per_V"]) / p0


def run_physics(verbose: bool = False) -> int:
    # The complete solver-free gate happens before resolving or launching the solver.
    report = demo19.preflight_report()
    if not report["all_grading_valid"] or not report["all_decks_complete"]:
        raise RuntimeError("Demo 19 preflight failed; refusing licensed physics")
    machine = _machine()
    cfg = demo19.load_config()
    root = _new_run(machine)
    demo19.write_preflight_tables(root / "tables")
    demo19.write_input_examples(root / demo19.EXAMPLES_FILENAME)
    demo19.write_case_inputs(root / "inputs", cfg)
    plots19.input_plots(root / "plots")
    rows: list[dict[str, Any]] = []
    spectra: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for case in cases19.all_cases():
        row = _base_row(case)
        case_dir = root / "cases" / f"case_{case.case_id}"
        input_dir = case_dir / "nextnano_input"
        logs = case_dir / "logs"
        input_dir.mkdir(parents=True, exist_ok=True)
        try:
            g, profile, blocks, deck_text = demo19.build_case(cfg, case)
            deck = input_dir / "case.in"
            deck.write_text(deck_text, encoding="utf-8", newline="\n")
            imported: dict[str, Path] = {}
            if blocks["datafile"]:
                data = input_dir / "al_profile.dat"
                data.write_text(blocks["datafile"], encoding="utf-8", newline="\n")
                imported["al_profile"] = data
            raw = root / case.physics_label
            print(f"[SOLVE {case.case_id}/12] {case.case_name}")
            invocation = solver14.execute_real(
                executable=Path(machine.executable), database=Path(machine.database),
                license_path=Path(machine.license), deck=deck, output_dir=raw,
                threads=int(cfg["nextnano"]["threads"]),
                timeout_seconds=float(cfg["nextnano"]["solver_timeout_seconds"]),
                imported_files=imported, logs_dir=logs,
            )
            demo16b.verify_quantum_outputs(cfg, raw)
            alloy_path = demo16b.find_alloy_composition(raw)
            x_real, al_real = demo16b.read_alloy_composition(alloy_path)
            intended_real = np.interp(x_real, profile.x_nm_continuous, profile.al_fraction_continuous)
            composition_error = float(np.max(np.abs(al_real - intended_real)))
            if composition_error > demo19.PROFILE_TOLERANCE:
                raise RuntimeError(f"solver-realized composition error {composition_error:.6g} exceeds tolerance")
            metrics, optical = _optics(cfg, case, case_dir, raw, g, profile)
            localization, waves = demo16e.localization(cfg, raw, profile)
            if not localization["checks"]["passed"]:
                raise RuntimeError(f"wavefunction/localization checks failed: {localization['checks']}")
            matrix_path = case_dir / "optical" / "parsed" / "matrix_elements.json"
            _populate_physics_row(row, metrics, matrix_path, localization, optical, invocation)
            row["solver_pass"] = True
            row["physical_valid"] = bool(metrics.get("physical_qc_valid", False))
            if not row["physical_valid"]:
                row["failure_stage"] = "physical_validation"
                row["failure_reason"] = "Demo 11/14 physical QC did not pass"
            if case.case_id in {"00", "03"}:
                _write_wave_plot_data(case_dir / "wavefunctions_plot_data.csv", waves)
            spectrum = np.loadtxt(optical["spectrum_path"], delimiter=",", skiprows=1)
            spectra[case.case_id] = (spectrum[:, 0], spectrum[:, 3])
            (case_dir / "case_result.json").write_text(json.dumps({
                "case": case.as_case_row(), "solver": invocation.as_record(),
                "grading_validation": demo19.validate_realized(case),
                "solver_composition_max_error": composition_error,
                "localization": localization, "optical": optical, "master_row": row,
            }, indent=2, default=_json_default), encoding="utf-8", newline="\n")
        except Exception as exc:  # every failure remains in the summary
            row["failure_stage"] = row.get("failure_stage") or "solver_or_analysis"
            row["failure_reason"] = f"{type(exc).__name__}: {exc}"
            if verbose:
                print(f"  FAILED: {row['failure_reason']}")
        rows.append(row)
    _normalize(rows)
    master = _write_csv(root / "tables" / MASTER_FILENAME, rows, MASTER_FIELDS)
    presentation = _write_csv(
        root / "tables" / PRESENTATION_FILENAME, _presentation_rows(rows),
        ["Case", "Profile", "I1", "I2", "I3", "I4", "chi2_1550", "Relative_to_abrupt", "Peak_nm"],
    )
    boss = write_boss_summary(root / BOSS_SUMMARY_FILENAME, rows)
    plots19.physics_plots(root, rows, spectra)
    _terminal_summary(root, rows)
    print(f"MASTER TABLE: {master}")
    print(f"PRESENTATION TABLE: {presentation}")
    print(f"BOSS SUMMARY: {boss}")
    return 0 if all(row["physical_valid"] for row in rows) else 1


def _fmt(row: Mapping[str, Any] | None, key: str, spec: str = ".5g") -> str:
    if not row or row.get(key) in (None, ""):
        return "n/a"
    return format(float(row[key]), spec)


def _terminal_summary(root: Path, rows: list[dict[str, Any]]) -> None:
    by_id = {row["case_id"]: row for row in rows}
    valid = [row for row in rows if row["physical_valid"]]
    abrupt = by_id.get("00")
    changed = max(valid, key=lambda r: abs(float(r["chi2_1550_relative_to_abrupt"]) - 1.0)) if valid and abrupt and abrupt["physical_valid"] else None
    print("\nDEMO 19 — QUANTUM-WELL INTERFACE GRADING SHOWCASE")
    print("=" * 58)
    print("\nREFERENCE STRUCTURE\n-------------------")
    print("Well 1:        7.1 nm\nBarrier:       1.8 nm\nWell 2:        2.9 nm\nBarrier Al:    0.55")
    print(f"\nCASES\n-----\nTotal: {len(rows)}\nValid: {len(valid)}\nFailed: {len(rows)-len(valid)}")
    print("\nABRUPT REFERENCE\n----------------")
    print(f"chi2(1550): {_fmt(abrupt, 'chi2_1550_pm_per_V')} pm/V")
    print(f"Peak wavelength: {_fmt(abrupt, 'peak_wavelength_nm', '.1f')} nm")
    print(f"Peak chi2: {_fmt(abrupt, 'peak_chi2_pm_per_V')} pm/V")
    print("\nLINEAR GRADING SERIES\n---------------------\nWidth     chi2(1550)     vs Abrupt     Peak λ")
    for case_id in ("00", "01", "02", "03", "04", "05"):
        row = by_id[case_id]
        print(f"{_fmt(row, 'nominal_grade_width_nm', '.1f'):>4}      {_fmt(row, 'chi2_1550_pm_per_V'):>10}     {_fmt(row, 'chi2_1550_relative_to_abrupt', '.3f'):>8}     {_fmt(row, 'peak_wavelength_nm', '.1f'):>7}")
    print("\nGRADING LOCATION\n----------------")
    for case_id, label in (("08", "Inner-only"), ("09", "Outer-only"), ("06", "Asymmetric A"), ("07", "Asymmetric B")):
        print(f"{label}: {_fmt(by_id[case_id], 'chi2_1550_pm_per_V')} pm/V")
    print("\nPROFILE SHAPES\n--------------")
    for case_id, label in (("03", "Linear"), ("10", "Fermi"), ("11", "erf"), ("12", "Cosine")):
        print(f"{label}: {_fmt(by_id[case_id], 'chi2_1550_pm_per_V')} pm/V")
    print("\nLARGEST CHANGE FROM ABRUPT\n--------------------------")
    print(f"Case: {changed['case_name'] if changed else 'n/a'}")
    print(f"Profile: {changed['profile'] if changed else 'n/a'}")
    print(f"chi2(1550): {_fmt(changed, 'chi2_1550_pm_per_V')} pm/V")
    print(f"Ratio to abrupt: {_fmt(changed, 'chi2_1550_relative_to_abrupt', '.3f')}")
    print(f"Peak wavelength: {_fmt(changed, 'peak_wavelength_nm', '.1f')} nm")
    print("\nPRIMARY INTERPRETATION\n----------------------")
    print("Within this model, grading comparisons are made only against the otherwise identical abrupt case.")
    print("Absolute agreement with an experiment or paper is outside Demo 19's claim.")
    print(f"\nRESULT DIRECTORY:\n{root}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Demo 19 — Quantum-Well Interface Grading Showcase")
    parser.add_argument("--physics", action="store_true", help="run exactly 13 licensed Nextnano++ solves")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    if args.physics:
        return run_physics(verbose=args.verbose)
    return run_preflight(verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
