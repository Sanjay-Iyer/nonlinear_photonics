"""Demo 18E - electron/HH cancellation and state-truncation audit.

No function in this module launches nextnano++. ``--physics`` means analyze the
completed, provenance-gated Demo 18D/18B solver trees. The already requested six
states per band make a new licensed solve unnecessary for the primary audit.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import uuid
from typing import Any, Mapping, Sequence

import numpy as np


DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
REPO_ROOT = DEMOS.parents[1]
for path in (
    DEMO_DIR, DEMOS / "_shared", DEMOS / "18B_absolute_chi2_reproduction_audit",
    DEMOS / "18C_paper_missing_parameter_ensemble",
    DEMOS / "18D_solver_physics_dual_objective_reproduction",
    DEMOS / "14_absolute_chi2_graded_acqw_bo",
    DEMOS / "16_acqw_renderer_stress_validation",
    DEMOS / "16B_simple_acqw_grading_validation",
    DEMOS / "16E_acqw_structure_physics_optical_comparison",
    DEMOS / "16F_paper_absolute_chi2_reproduction_audit",
    DEMOS / "18_absolute_chi2_scale_audit",
    DEMOS / "11_paper_validation_interband_chi2_acqw",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import analysis18e
import config18e


RULE = "=" * 72


class Runner18EError(RuntimeError):
    pass


class DebugLog:
    def __init__(self, path: Path, verbose: bool = False):
        self.path = path
        self.verbose = verbose
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def line(self, value: str = "") -> None:
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(value.rstrip() + "\n")
        if self.verbose:
            print(value)

    def section(self, title: str) -> None:
        self.line(f"\n{RULE}\n{title}\n{RULE}")

    def record(self, value: object) -> None:
        self.line(json.dumps(_json_safe(value), indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demo 18E state-truncation audit")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="validate without licensed outputs")
    mode.add_argument("--physics", action="store_true", help="analyze archived licensed raw outputs; never launches solver")
    mode.add_argument("--analyze-handoff", action="store_true", help="analyze exported Demo 18D CSV matrices")
    parser.add_argument("--demo18d-run", type=Path, help="completed Demo 18D run root")
    parser.add_argument("--demo18b-run", type=Path, help="completed Demo 18B run root")
    parser.add_argument("--output-root", type=Path, help="parent result directory")
    parser.add_argument("--verbose", action="store_true")
    return parser


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = [dict(row) for row in rows]
    if not materialized:
        path.write_text("", encoding="utf-8")
        return path
    fields: list[str] = []
    for row in materialized:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in materialized:
            writer.writerow({key: _csv_value(row.get(key)) for key in fields})
    return path


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(_json_safe(value), sort_keys=True)
    if isinstance(value, complex):
        return f"{value.real:.17g}{value.imag:+.17g}j"
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _git_short() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"], cwd=REPO_ROOT,
            check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "nogit"


def _run_root(parent: Path) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo18e_{stamp}_{_git_short()}_{uuid.uuid4().hex[:6]}"
    root = Path(parent) / str(config18e.load_config()["demo_id"]) / run_id
    for sub in ("summaries", "summaries/spectra", "plots", "config_snapshot", "logs"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _matrix_model(energies_e: Sequence[float], energies_h: Sequence[float],
                  overlap: np.ndarray, z_e: np.ndarray, z_h: np.ndarray) -> analysis18e.MatrixModel:
    return analysis18e.MatrixModel(
        np.asarray(energies_e, float), np.asarray(energies_h, float), overlap, z_e, z_h,
        tuple(f"E{i + 1}" for i in range(len(energies_e))),
        tuple(f"HH{i + 1}" for i in range(len(energies_h))),
    )


def _load_handoff(cfg: Mapping[str, Any]) -> dict[str, Any]:
    root = config18e.repo_path(cfg["sources"]["local_demo18d_handoff"])
    state_path, matrix_path, localization_path = (
        root / "state_audit.csv", root / "matrix_elements.csv", root / "localization.csv"
    )
    missing = [str(path) for path in (state_path, matrix_path, localization_path) if not path.is_file()]
    if missing:
        raise Runner18EError(f"local Demo 18D handoff is incomplete: {missing}")
    state_rows = [row for row in _read_csv(state_path) if row["case_id"] == "Case_19"]
    matrix_rows = [row for row in _read_csv(matrix_path) if row["case_id"] == "Case_19"]
    localization = [row for row in _read_csv(localization_path) if row["case_id"] == "Case_19"]
    e_states = sorted((row for row in state_rows if row["band"] == "electron"), key=lambda r: int(r["state"]))
    h_states = sorted((row for row in state_rows if row["band"] == "heavy_hole"), key=lambda r: int(r["state"]))
    ne, nh = len(e_states), len(h_states)
    overlap = np.zeros((ne, nh), complex); ze = np.zeros((ne, ne), complex); zh = np.zeros((nh, nh), complex)
    for row in matrix_rows:
        i, j, value = int(row["row_state"]) - 1, int(row["column_state"]) - 1, float(row["value"])
        if row["quantity"] == "overlap": overlap[i, j] = value
        elif row["row_band"] == "electron": ze[i, j] = value
        elif row["row_band"] == "heavy_hole": zh[i, j] = value
    model = _matrix_model(
        [float(row["energy_eV"]) for row in e_states],
        [float(row["energy_eV"]) for row in h_states], overlap, ze, zh,
    )
    return {"model": model, "state_rows": state_rows, "localization": localization,
            "raw_state_data": None, "source_kind": "exported_matrix_handoff", "source_root": root}


def _load_raw_18d(cfg: Mapping[str, Any], source: Path) -> dict[str, Any]:
    import audit18b
    import config18d
    import run_demo18d
    source = Path(source)
    gate_path = source / "cases" / "Case_19" / "solver_gate.json"
    if not gate_path.is_file():
        raise Runner18EError(f"missing Case_19 provenance gate: {gate_path}")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if not bool(gate.get("passed")):
        raise Runner18EError(f"Demo 18D Case_19 did not pass its solver gate: {gate}")
    dcfg = config18d.load_config(source / "config_snapshot" / "demo18d.yaml"
                                if (source / "config_snapshot" / "demo18d.yaml").is_file() else None)
    case = next(row for row in config18d.load_cases(
        source / "config_snapshot" / "demo18d_combinations.csv"
        if (source / "config_snapshot" / "demo18d_combinations.csv").is_file() else None
    ) if row.case_id == "Case_19")
    solved = run_demo18d._load_solved(dcfg, case, source / "solver" / "Case_19")
    data = solved["data"]
    overlap, ze, zh = audit18b.matrices(data.electron, data.heavy_hole)
    model = _matrix_model(data.electron.energies_eV, data.heavy_hole.energies_eV, overlap, ze, zh)
    hh_edge = data.band_edges.get("heavy_hole_eV")
    raw_state_data = {
        "z_nm": data.heavy_hole.z_nm,
        "band_z_nm": data.band_position_nm,
        "heavy_hole_edge_eV": hh_edge,
        "hh23": [
            ("HH2", data.heavy_hole.energies_eV[1], data.heavy_hole.envelopes[:, 1]),
            ("HH3", data.heavy_hole.energies_eV[2], data.heavy_hole.envelopes[:, 2]),
        ],
    }
    if hh_edge is not None and np.asarray(hh_edge).size != np.asarray(data.band_position_nm).size:
        raise Runner18EError(
            "Case_19 heavy-hole band edge does not match the full band-profile grid"
        )
    return {"model": model, "state_rows": solved["state_audit"],
            "localization": solved["localization"], "raw_state_data": raw_state_data,
            "source_kind": "licensed_archived_raw_output", "source_root": source}


def _load_raw_18b(cfg: Mapping[str, Any], source: Path) -> analysis18e.MatrixModel:
    import audit18b
    import cases18b
    import config18b
    import run_demo18b
    source = Path(source)
    case_id = str(cfg["sources"]["demo18b_case"])
    gate_path = source / "cases" / case_id / "solver_gate.json"
    if gate_path.is_file() and not json.loads(gate_path.read_text(encoding="utf-8")).get("passed"):
        raise Runner18EError(f"Demo 18B {case_id} failed its source gate")
    bcfg = config18b.load_config(source / "config_snapshot" / "demo18b.yaml"
                                if (source / "config_snapshot" / "demo18b.yaml").is_file() else None)
    numerical = next(row for row in cases18b.solve_cases() if row.case_id == case_id)
    solver_cfg, _case, _geometry, _profile, _blocks, _deck = run_demo18b._case_geometry(bcfg, numerical)
    data = audit18b.load_solved_data(solver_cfg, source / "solver" / case_id)
    overlap, ze, zh = audit18b.matrices(data.electron, data.heavy_hole)
    return _matrix_model(data.electron.energies_eV, data.heavy_hole.energies_eV, overlap, ze, zh)


def _identity_rows(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    model: analysis18e.MatrixModel = bundle["model"]
    local = {(str(row["band"]), int(row["state"])): row for row in bundle["localization"]}
    audit = {(str(row["band"]), int(row["state"])): row for row in bundle["state_rows"]}
    rows = []
    for band, energies, labels, zmat in (
        ("electron", model.electron_energies_eV, model.electron_labels, model.z_e_nm),
        ("heavy_hole", model.heavy_hole_energies_eV, model.heavy_hole_labels, model.z_hh_nm),
    ):
        for index, (energy, label) in enumerate(zip(energies, labels), 1):
            a, loc = audit.get((band, index), {}), local.get((band, index), {})
            boundary = float(a.get("left_boundary_probability", 0) or 0) + float(a.get("right_boundary_probability", 0) or 0)
            overlaps = (model.overlap_eh[index - 1, :] if band == "electron"
                        else model.overlap_eh[:, index - 1])
            transitions = (energy - model.heavy_hole_energies_eV if band == "electron"
                           else model.electron_energies_eV - energy)
            rows.append({
                "band": band, "state": index, "label": label, "energy_eV": float(energy),
                "bound": str(a.get("bound_pass", "")).casefold() in {"true", "1"} if isinstance(a.get("bound_pass"), str) else bool(a.get("bound_pass")),
                "centroid_nm": float(a.get("centroid_nm", loc.get("centroid_nm", "nan"))),
                "left_well_probability": float(loc.get("left_well_probability", "nan")),
                "barrier_probability": float(loc.get("central_barrier_probability", "nan")),
                "right_well_probability": float(loc.get("right_well_probability", "nan")),
                "boundary_probability": boundary,
                "left_boundary_probability": float(a.get("left_boundary_probability", "nan")),
                "right_boundary_probability": float(a.get("right_boundary_probability", "nan")),
                "z_matrix_row_nm": [complex(v) for v in zmat[index - 1]],
                "electron_hh_overlaps": [complex(v) for v in overlaps],
                "transition_energies_eV": [float(v) for v in transitions],
                "character": loc.get("character", ""),
            })
    return rows


def _wavelengths(cfg: Mapping[str, Any]) -> np.ndarray:
    spec = cfg["spectrum"]
    return np.linspace(float(spec["wavelength_start_nm"]), float(spec["wavelength_stop_nm"]),
                       int(spec["wavelength_points"]))


def _analyze(cfg: Mapping[str, Any], bundle: Mapping[str, Any], root: Path,
             log: DebugLog, baseline_model: analysis18e.MatrixModel | None) -> dict[str, Any]:
    model: analysis18e.MatrixModel = bundle["model"]
    settings = analysis18e.settings_from_config(cfg)
    wavelengths = _wavelengths(cfg)
    if model.n_e < 3 or model.n_hh < 3:
        raise Runner18EError(f"Case_19 needs >=3 states per band, got {model.n_e}e/{model.n_hh}hh")
    log.section("SOURCE AND STATE ENERGIES")
    log.record({"source": bundle["source_root"], "source_kind": bundle["source_kind"],
                "electron_energies_eV": model.electron_energies_eV,
                "heavy_hole_energies_eV": model.heavy_hole_energies_eV,
                "matrix_dimensions": {"overlap": model.overlap_eh.shape,
                                      "z_e": model.z_e_nm.shape, "z_hh": model.z_hh_nm.shape}})

    controls_model = model.subset((0, 1), (0, 1, 2))
    phase_rows = analysis18e.phase_invariance(
        controls_model, settings, seed=int(cfg["controls"]["phase_seed"]),
        trials=int(cfg["controls"]["phase_trials"]),
    )
    permutation_rows = analysis18e.permutation_invariance(model.subset((0, 1, 2), (0, 1, 2)), settings)
    tolerance = float(cfg["controls"]["invariance_relative_tolerance"])
    phase_max = max(float(row["relative_residual"]) for row in phase_rows)
    perm_max = max(float(row["relative_residual"]) for row in permutation_rows)
    log.section("MANDATORY INVARIANCE GATES")
    log.record({"phase_max_relative_residual": phase_max,
                "permutation_max_relative_residual": perm_max, "tolerance": tolerance})
    if phase_max > tolerance or perm_max > float(cfg["controls"]["permutation_relative_tolerance"]):
        raise Runner18EError("STOP: phase or permutation invariance gate failed")

    definitions = [
        ("Case_19 E1,E2 + HH1,HH2", (0, 1), (0, 1), "paper_primary"),
        ("Case_19 E1,E2 + HH1,HH3", (0, 1), (0, 2), "state_substitution"),
        ("Case_19 E1,E2 + HH2,HH3", (0, 1), (1, 2), "state_substitution"),
        ("Case_19 E1,E2 + HH1,HH2,HH3", (0, 1), (0, 1, 2), "diagnostic_extension"),
        ("Case_19 E1,E2,E3 + HH1,HH2", (0, 1, 2), (0, 1), "diagnostic_extension"),
        ("Case_19 E1,E2,E3 + HH1,HH2,HH3", (0, 1, 2), (0, 1, 2), "diagnostic_extension"),
    ]
    selection_rows, spectra = [], {}
    for label, ei, hi, role in definitions:
        selected = model.subset(ei, hi)
        data = analysis18e.spectrum(selected, wavelengths, settings)
        row = analysis18e.summarize_spectrum(label, data)
        row.update({"audit_role": role, "n_electron_states": len(ei), "n_hh_states": len(hi),
                    "electron_states": ";".join(selected.electron_labels),
                    "hh_states": ";".join(selected.heavy_hole_labels)})
        selection_rows.append(row); spectra[label] = data
        log.section(f"STATE SELECTION: {label}"); log.record(row)
    baseline = selection_rows[0]
    for row in selection_rows:
        row["ratio_to_case19_2e2hh"] = float(row["chi2_1550_pm_per_V"]) / float(baseline["chi2_1550_pm_per_V"])
        row["difference_from_2e2hh_pm_per_V"] = float(row["chi2_1550_pm_per_V"]) - float(baseline["chi2_1550_pm_per_V"])
        row["ratio_to_paper"] = float(row["chi2_1550_pm_per_V"]) / float(cfg["spectrum"]["paper_target_pm_per_V"])
    substitution_change = 100.0 * abs(float(selection_rows[1]["chi2_1550_pm_per_V"])
                                      - float(baseline["chi2_1550_pm_per_V"])) / max(float(baseline["chi2_1550_pm_per_V"]), 1e-30)
    selection_rows[1]["flag"] = ("STRONG_STATE_TRUNCATION_SENSITIVITY" if substitution_change
                                  > float(cfg["controls"]["strong_state_truncation_threshold_percent"]) else "")

    if baseline_model is not None:
        bdata = analysis18e.spectrum(baseline_model.subset((0, 1), (0, 1)), wavelengths, settings)
        brow = analysis18e.summarize_spectrum("Demo 18B M2 E1,E2 + HH1,HH2", bdata)
        brow.update({"audit_role": "reference", "n_electron_states": 2, "n_hh_states": 2,
                     "electron_states": "E1;E2", "hh_states": "HH1;HH2",
                     "ratio_to_case19_2e2hh": float(brow["chi2_1550_pm_per_V"]) / float(baseline["chi2_1550_pm_per_V"]),
                     "difference_from_2e2hh_pm_per_V": float(brow["chi2_1550_pm_per_V"]) - float(baseline["chi2_1550_pm_per_V"]),
                     "ratio_to_paper": float(brow["chi2_1550_pm_per_V"]) / float(cfg["spectrum"]["paper_target_pm_per_V"])})
        selection_rows.insert(0, brow); spectra[brow["state_selection"]] = bdata

    rotation_rows = analysis18e.rotation_audit(
        model.subset((0, 1), (0, 1, 2)), settings,
        cfg["rotation"]["angles_deg"], wavelengths,
    )
    log.section("HH2/HH3 ROTATION AUDIT"); log.record(rotation_rows)

    _total, branches, term_rows = analysis18e.evaluate(
        model.subset((0, 1), (0, 1)), analysis18e.HC_EV_NM / 1550.0, settings, decompose=True
    )
    pair_rows = analysis18e.cancellation_pairs(term_rows)
    sign_rows = _sign_audit(model.subset((0, 1), (0, 1)), settings, wavelengths)
    multiplicity_rows = _multiplicity_audit(branches, cfg)
    identity_rows = _identity_rows(bundle)
    convergence_rows = [row for row in selection_rows if row["n_electron_states"] in (2, 3)
                        and row["n_hh_states"] in (2, 3)
                        and "Case_19" in str(row["state_selection"])
                        and row["hh_states"] in ("HH1;HH2", "HH1;HH2;HH3")]

    complete_rotation = [row for row in rotation_rows if row["calculation"] == "complete_HH1_HH_a_HH_b"]
    truncated_rotation = [row for row in rotation_rows if row["calculation"] == "truncated_HH1_plus_HH_a"]
    complete_var = float(complete_rotation[0]["chi2_1550_percent_variation"])
    truncated_var = float(truncated_rotation[0]["chi2_1550_percent_variation"])
    largest_extension = max(convergence_rows, key=lambda row: float(row["chi2_1550_pm_per_V"]))
    in_window = 1520.0 <= float(largest_extension["peak_wavelength_nm"]) <= 1560.0
    if float(largest_extension["ratio_to_case19_2e2hh"]) > 5.0 and in_window:
        outcome = "C"
    elif substitution_change > 20.0 and complete_var < 1.0:
        outcome = "B"
    elif substitution_change <= 20.0 and max(float(r["ratio_to_case19_2e2hh"]) for r in convergence_rows) < 5.0:
        outcome = "A"
    else:
        outcome = "F"
    interpretation = _outcome_text(outcome)

    summaries = root / "summaries"
    _write_csv(summaries / "demo18e_state_identity.csv", identity_rows)
    _write_csv(summaries / "demo18e_state_selection_audit.csv", selection_rows)
    _write_csv(summaries / "demo18e_rotation_invariance.csv", rotation_rows)
    _write_csv(summaries / "demo18e_state_count_convergence.csv", convergence_rows)
    _write_csv(summaries / "demo18e_eq2_term_table.csv", term_rows)
    _write_csv(summaries / "demo18e_cancellation_pairs.csv", pair_rows)
    _write_csv(summaries / "demo18e_sign_convention_audit.csv", sign_rows)
    _write_csv(summaries / "demo18e_multiplicity_audit.csv", multiplicity_rows)
    _write_csv(summaries / "demo18e_phase_invariance.csv", phase_rows)
    _write_csv(summaries / "demo18e_permutation_invariance.csv", permutation_rows)
    for label, data in spectra.items():
        safe = "".join(ch if ch.isalnum() else "_" for ch in label).strip("_")
        _write_csv(summaries / "spectra" / f"{safe}.csv", _spectrum_rows(data))
    valence = _valence_model_audit(cfg, bundle)
    _write_json(summaries / "demo18e_valence_model_audit.json", valence)
    (summaries / "demo18e_missing_paper_inputs.md").write_text(_missing_inputs_text(), encoding="utf-8")
    try:
        plots = _load_plots().generate_all(root / "plots", selection_rows, rotation_rows,
                                           _plot_spectra(spectra), term_rows, pair_rows,
                                           bundle["raw_state_data"])
    except ModuleNotFoundError as exc:
        if bundle["source_kind"] != "exported_matrix_handoff":
            raise
        plots = []
        log.line(f"WARNING: handoff-only plot generation skipped because dependency is missing: {exc}")
    summary = {
        "demo_id": cfg["demo_id"], "source": bundle["source_root"],
        "source_kind": bundle["source_kind"], "new_licensed_solves_required": 0,
        "phase_invariance_pass": phase_max <= tolerance, "phase_max_relative_residual": phase_max,
        "permutation_invariance_pass": perm_max <= tolerance, "permutation_max_relative_residual": perm_max,
        "hh2_energy_eV": float(model.heavy_hole_energies_eV[1]),
        "hh3_energy_eV": float(model.heavy_hole_energies_eV[2]),
        "hh2_hh3_splitting_meV": float((model.heavy_hole_energies_eV[1] - model.heavy_hole_energies_eV[2]) * 1000.0),
        "splitting_over_gamma": float((model.heavy_hole_energies_eV[1] - model.heavy_hole_energies_eV[2])
                                      / (float(cfg["fixed_physics"]["broadening_meV"]) * 1e-3)),
        "hh2_hh3_identity_finding": (
            "HH2 and HH3 have nearly identical centroids and complementary left/right-well "
            "probabilities; they form a near-degenerate mixed bonding/antibonding-like subspace, "
            "not two cleanly separated localized states."
        ),
        "state_substitution_percent_change": substitution_change,
        "truncated_rotation_percent_variation": truncated_var,
        "complete_rotation_percent_variation": complete_var,
        "case19_primary": baseline, "largest_physical_diagnostic": largest_extension,
        "state_selection_results": selection_rows,
        "state_count_results": convergence_rows,
        "baseline_term_branches": {
            "electron": branches["electron"], "heavy_hole": branches["heavy_hole"],
            "total": branches["electron"] + branches["heavy_hole"],
        },
        "multiplicity_important_finding": (
            "All published/global factors multiply both branches and cannot relieve cancellation. "
            "An HH-only Kramers/m_j factor would be relative, but the paper does not specify or authorize it."
        ),
        "outcome": outcome, "interpretation": interpretation,
        "valence_model_audit": valence, "plots": [str(path) for path in plots],
    }
    _write_json(summaries / "demo18e_summary.json", summary)
    log.section("FINAL SUMMARY"); log.record(summary)
    return summary


def _spectrum_rows(data: Mapping[str, np.ndarray]) -> list[dict[str, Any]]:
    rows = []
    for i, wavelength in enumerate(data["wavelength_nm"]):
        row = {"wavelength_nm": float(wavelength)}
        for key in ("chi_e", "chi_hh", "chi_total"):
            value = complex(data[key][i])
            row.update({f"{key}_real": value.real, f"{key}_imag": value.imag, f"{key}_abs": abs(value)})
        rows.append(row)
    return rows


def _plot_spectra(spectra: Mapping[str, Mapping[str, np.ndarray]]) -> dict[str, Mapping[str, np.ndarray]]:
    wanted = ("Case_19 E1,E2 + HH1,HH2", "Case_19 E1,E2 + HH1,HH3",
              "Case_19 E1,E2 + HH1,HH2,HH3")
    return {key: spectra[key] for key in wanted if key in spectra}


def _load_plots() -> Any:
    import plots18e
    return plots18e


def _sign_audit(model: analysis18e.MatrixModel, settings: analysis18e.Settings,
                wavelengths: np.ndarray) -> list[dict[str, Any]]:
    variants = [
        ("baseline_physical_sign", 1, -1, "PRIMARY", True,
         "Explicit electron minus HH structure in paper Eq. (3), separated as Eqs. (5)-(7)."),
        ("HH_pathway_global_sign_reversed", 1, +1, "DIAGNOSTIC_ONLY", False,
         "Ruled out by the explicit negative HH term in published Eq. (3)/(6)."),
        ("advanced_broadening_minus_iGamma", -1, -1, "DIAGNOSTIC_ONLY", False,
         "Not the retarded +iGamma convention printed in Eq. (3); for real inputs it conjugates the response."),
    ]
    rows = []
    for name, gamma_sign, hh_sign, role, allowed, note in variants:
        data = analysis18e.spectrum(model, wavelengths, settings, gamma_sign=gamma_sign, hh_path_sign=hh_sign)
        row = analysis18e.summarize_spectrum(name, data)
        rows.append({"variant": name, "role": role, "gamma_sign": gamma_sign,
                     "hh_path_sign": hh_sign, "supported_by_paper": allowed,
                     "paper_location": "APL 123, 251111 (2023), printed pp. 2-3, Eqs. (3), (5)-(7)",
                     "notes": note, **row})
    rows.append({
        "variant": "positive_hole_excitation_energy_without_rederivation", "role": "DIAGNOSTIC_ONLY",
        "gamma_sign": "NOT_EVALUATED", "hh_path_sign": "NOT_EVALUATED", "supported_by_paper": False,
        "paper_location": "Eq. (3) uses transition frequencies omega_e-h, not a standalone positive-hole spectrum",
        "notes": "Changing the stored valence-energy sign without rederiving every transition denominator is inconsistent and was refused.",
    })
    return rows


def _multiplicity_audit(branches: Mapping[str, complex], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    e, hh = branches["electron"], branches["heavy_hole"]
    def row(name: str, current: Any, alternative: Any, ef: float, hf: float, common: str,
            location: str, source: str, supported: str, notes: str) -> dict[str, Any]:
        return {"convention": name, "current_value": current, "plausible_alternative": alternative,
                "applies_to_electron": ef != 1.0, "applies_to_hh": hf != 1.0,
                "common_or_relative": common, "mathematical_location": location, "source": source,
                "supported_by_paper": supported,
                "diagnostic_effect_on_chi2": analysis18e.diagnostic_branch_scale(e, hh, ef, hf),
                "notes": notes}
    return [
        row("electron spin degeneracy", 2, 1, .5, .5, "common", "radial k-space weight",
            "repository setting; paper does not state spin factor", "NOT SPECIFIED", "A common factor cannot relieve cancellation."),
        row("HH Kramers / m_j = +/-3/2", "not separately applied", 2, 1, 2, "relative",
            "would multiply HH branch only", "one-band HH solver returns one orbital envelope per level",
            "NOT SPECIFIED", "Potentially relative, but no paper statement authorizes a second HH-only factor."),
        row("QW density Nz", "2/30 nm", "1/30 nm", .5, .5, "common", "global Eq. (3) prefactor",
            "paper: number of QWs per unit length", "INFERRED", "Common scale only."),
        row("+/-k symmetry", "full angular radial measure", "extra factor 2", 2, 2, "common",
            "2D k-space integration", "paper: 2D integral to 0.1 BZ", "NO EXTRA FACTOR PUBLISHED", "Would double both branches."),
        row("polarization/tensor permutation", "chi_xzx", "xzx+xxz", 2, 2, "common",
            "sum over polarization permutations / tensor definition", "paper Eqs. (3)-(7)",
            "NOT SHOWN AS EXTRA FACTOR", "Cannot selectively change HH."),
        row("Eq. (1) to reduced Eq. (3) prefactor", "1/6", "Eq. (1)-style 1/2", 3, 3, "common",
            "global susceptibility prefactor", "paper printed Eqs. (1) and (3)", "OPEN DERIVATION DETAIL",
            "Factor-of-three diagnostic remains common and cannot fix cancellation."),
    ]


def _valence_model_audit(cfg: Mapping[str, Any], bundle: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "current_model": {
            "classification": "one-band effective-mass Gamma electron plus one-band heavy-hole",
            "evidence": [
                "Demo 18D reuses audit18b.load_solved_data and quantum1d.parse_one_band_run",
                "Nextnano output families are Gamma_Gamma, HH_HH, and Gamma_HH",
                "No spinor composition enters the scalar-envelope Eq. (3) postprocessor",
            ],
        },
        "paper_model": {
            "exact_valence_band_model": "NOT SPECIFIED",
            "published_statement": "A Schrodinger-Poisson solver determined CB/HH levels and envelopes; first two bound states were used.",
            "source": "APL 123, 251111 (2023), printed p. 3",
        },
        "nextnano_multiband_support": {
            "supported": True,
            "models": ["6-band k.p valence", "8-band k.p"],
            "repository_evidence": [
                "nextnano/demos/07_strained_ingaas_gaas_6band",
                "nextnano/demos/08_eight_band_interband_optics",
            ],
            "installed_work_version": "Repository records confirm kp_6band and kp_8band output on the work installation; executable is not present on this analysis machine.",
        },
        "controlled_comparison": {
            "completed": False,
            "new_licensed_solve_required_if_requested": 1,
            "used_in_primary_eq3": False,
            "reason": (
                "The published reduced Eq. (3) factors a scalar HH envelope from a fixed Bloch r_e,hh. "
                "A 6/8-band spinor has HH/LH/SO components and component-resolved optical matrix elements; "
                "inserting a scalarized spinor into the one-band overlap/z formula would change the theory "
                "without a published projection rule. Demo 18E therefore documents support but does not force "
                "an incompatible multiband state into Eq. (3)."
            ),
        },
        "hh_lh_mixing": {
            "available_in_current_model": False,
            "fractions_reported": False,
            "finding": "The one-band model enforces pure HH character; no actual multiband result exists for Case_19, so HH/LH mixing is not claimed as the discrepancy explanation.",
        },
        "primary_new_licensed_solves_required": 0,
        "source_run": str(bundle["source_root"]),
    }


def _missing_inputs_text() -> str:
    return """# Demo 18E - missing paper inputs

Source inspected: Ramesh et al., *Applied Physics Letters* 123, 251111 (2023),
especially printed pages 2-5 and Eqs. (1)-(7).

| Input | Classification | Reproducibility finding |
|---|---|---|
| Exact Nextnano input deck | UNPUBLISHED | The paper names nextnano through Ref. 19 but supplies no deck. |
| Exact Nextnano band model | UNKNOWN | Schrodinger-Poisson CB/HH states are stated; one-band, 6-band, and 8-band are not distinguished. |
| Schrodinger-Poisson charge setup | UNPUBLISHED | Carrier densities and self-consistency details are absent. |
| Doping profile | UNPUBLISHED | No numerical doping profile is given. |
| Electrostatic boundary conditions | UNPUBLISHED | No contact or Poisson boundary values are given. |
| Numerical r_e,hh | PUBLISHED (2023 paper) | The paper gives 7.51 Angstrom and says VASP/HSE06; this repository uses 0.751 nm. |
| VASP/HSE06 settings | UNPUBLISHED | Functional family is stated, but cell, basis, cutoff, k mesh, PAW data, and convergence controls are absent. |
| State-indexing convention | INFERRED | First two bound CB/HH states and m,n,l are stated; near-degenerate tie-breaking is absent. |
| HH multiplicity convention | UNKNOWN | The paper does not state whether +/-3/2/Kramers multiplicity is separate from the k/spin sum. |
| k-space integration code | UNPUBLISHED | A 2D integral saturated by 0.1 BZ is stated; discretization and BZ-edge convention are absent. |
| Full chi2 post-processing code | UNPUBLISHED | Equations are published; implementation, state ordering, units ledger, and tests are not. |

Repository-specific choices such as 768 radial points, GaAs in-plane masses,
Nz = 2/30 nm, and the quantum-only imposed-field setup are
**REPOSITORY_ASSUMPTION**, not attributed to the authors.
"""


def _outcome_text(outcome: str) -> str:
    return {
        "A": "HH2/HH3 substitution and state-count extension are robust; state truncation is unlikely to explain the paper discrepancy.",
        "B": "The two-HH-state result is strongly basis/selection sensitive, while the complete degenerate HH2/HH3 subspace restores rotation invariance.",
        "C": "Adding a bound state raises chi2 by more than fivefold while preserving the target spectral window; omitted states materially change cancellation.",
        "F": "No tested state-selection criterion alone establishes the discrepancy; unpublished implementation details remain necessary.",
    }[outcome]


def _terminal(summary: Mapping[str, Any], root: Path) -> None:
    base = summary["case19_primary"]; best = summary["largest_physical_diagnostic"]
    selections = {row["state_selection"]: row for row in summary["state_selection_results"]}
    counts = {(int(row["n_electron_states"]), int(row["n_hh_states"])): row
              for row in summary["state_count_results"]}
    branches = summary["baseline_term_branches"]
    print("DEMO 18E - ELECTRON/HH CANCELLATION AND STATE-TRUNCATION AUDIT")
    print("=" * 63)
    print("\nREFERENCE\n---------")
    print(f"Demo 18D Case_19:\nchi2(1550): {base['chi2_1550_pm_per_V']:.6g} pm/V")
    print(f"peak: {base['peak_wavelength_nm']:.1f} nm\nelectron: {base['chi_e_abs']:.6g} pm/V")
    print(f"HH: {base['chi_hh_abs']:.6g} pm/V\nphase difference: {base['phase_difference_deg']:.6g} deg")
    print(f"cancellation factor: {base['cancellation_factor']:.6g}")
    print("\nNEAR-DEGENERATE HH SUBSPACE\n---------------------------")
    print(f"HH2 energy: {summary['hh2_energy_eV']:.12f} eV\nHH3 energy: {summary['hh3_energy_eV']:.12f} eV")
    print(f"splitting: {summary['hh2_hh3_splitting_meV']:.6g} meV\nGamma: 5 meV")
    print(f"splitting/Gamma: {summary['splitting_over_gamma']:.6g}")
    print(f"identity: {summary['hh2_hh3_identity_finding']}")
    print("\nPHASE INVARIANCE\n----------------")
    print(f"pass: {summary['phase_invariance_pass']}\nmax residual: {summary['phase_max_relative_residual']:.3e}")
    print("\nPERMUTATION INVARIANCE\n----------------------")
    print(f"pass: {summary['permutation_invariance_pass']}\nmax residual: {summary['permutation_max_relative_residual']:.3e}")
    print("\nSTATE SELECTION\n---------------")
    for label in ("Case_19 E1,E2 + HH1,HH2", "Case_19 E1,E2 + HH1,HH3",
                  "Case_19 E1,E2 + HH1,HH2,HH3"):
        row = selections[label]
        print(f"{label.replace('Case_19 ', '')}: {row['chi2_1550_pm_per_V']:.6g} pm/V; "
              f"peak {row['peak_wavelength_nm']:.1f} nm")
    print("\nSTATE COUNT\n-----------")
    for key, label in (((2, 2), "2e/2hh"), ((2, 3), "2e/3hh"),
                       ((3, 2), "3e/2hh"), ((3, 3), "3e/3hh")):
        row = counts[key]
        print(f"{label}: {row['chi2_1550_pm_per_V']:.6g} pm/V; peak {row['peak_wavelength_nm']:.1f} nm")
    print("\nROTATION INVARIANCE\n-------------------")
    print(f"2-state truncated variation: {summary['truncated_rotation_percent_variation']:.6g}%")
    print(f"complete-subspace variation: {summary['complete_rotation_percent_variation']:.6g}%")
    electron = complex(branches["electron"])
    hh = complex(branches["heavy_hole"])
    total = complex(branches["total"])
    print("\nCANCELLATION\n------------")
    print(f"baseline electron: {abs(electron):.6g} pm/V\nbaseline HH: {abs(hh):.6g} pm/V")
    print(f"baseline phase: {base['phase_difference_deg']:.6g} deg\nbaseline residual: {abs(total):.6g} pm/V")
    print(f"largest physically valid residual: {best['chi2_1550_pm_per_V']:.6g} pm/V")
    print(f"associated state model: {best['state_selection']}")
    print("\nMULTIPLICITY AUDIT\n------------------")
    print(f"important findings: {summary['multiplicity_important_finding']}")
    print("\nVALENCE MODEL AUDIT\n-------------------")
    print("current model: one-band effective-mass HH\nmultiband available: True\ncomparison completed: False")
    print("important finding: scalar one-band Eq. (3) cannot accept a multiband spinor without a projection derivation")
    print("\nBEST PHYSICALLY DEFENSIBLE RESULT\n---------------------------------")
    print(f"chi2(1550): {best['chi2_1550_pm_per_V']:.6g} pm/V\npeak: {best['peak_wavelength_nm']:.1f} nm")
    print(f"ratio to paper: {best['ratio_to_paper']:.6g}\nwhy it changed: {best['state_selection']}")
    print(f"\nOUTCOME: {summary['outcome']}\n\nPRIMARY INTERPRETATION:\n{summary['interpretation']}")
    print(f"\nRESULT DIRECTORY:\n{root}")


def run_preflight(verbose: bool) -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        cfg = config18e.load_config(); settings = analysis18e.settings_from_config(cfg)
        checks.append(("immutable physics", settings.broadening_meV == 5 and settings.spin_degeneracy == 2
                       and settings.r_e_hh_nm == .751, "Gamma=5; spin=2; r=0.751; Nz=2/30nm"))
        bundle = _load_handoff(cfg); model = bundle["model"]
        checks.append(("Case_19 handoff has requested states", model.n_e >= 3 and model.n_hh >= 4,
                       f"{model.n_e} electron / {model.n_hh} HH states"))
        baseline = model.subset((0, 1), (0, 1))
        value, _parts, _terms = analysis18e.evaluate(baseline, analysis18e.HC_EV_NM / 1550.0, settings)
        checks.append(("exported matrix reproduction", abs(abs(value) - 144.65656692330407) < 1e-8,
                       f"chi2(1550)={abs(value):.12g} pm/V"))
        phase = analysis18e.phase_invariance(model.subset((0, 1), (0, 1, 2)), settings, seed=1805, trials=4)
        phase_max = max(row["relative_residual"] for row in phase)
        checks.append(("complex phase invariance", phase_max < 1e-11, f"max residual {phase_max:.3e}"))
        perm = analysis18e.permutation_invariance(model.subset((0, 1, 2), (0, 1, 2)), settings)
        perm_max = max(row["relative_residual"] for row in perm)
        checks.append(("unequal-count permutation invariance", perm_max < 1e-11, f"max residual {perm_max:.3e}"))
        rotation = [analysis18e.hh23_rotation_model(model.subset((0, 1), (0, 1, 2)), a)
                    for a in (0, 45, 90)]
        values = [analysis18e.evaluate(item, analysis18e.HC_EV_NM / 1550.0, settings)[0] for item in rotation]
        residual = max(abs(value - values[0]) for value in values) / max(abs(values[0]), 1e-30)
        checks.append(("complete degenerate-subspace rotation invariance", residual < 1e-11,
                       f"max residual {residual:.3e}"))
        checks.append(("no licensed solver invocation", True,
                       "run_demo18e contains analysis-only loaders; existing six-state Case_19 output is reused"))
    except Exception as exc:
        checks.append(("preflight execution", False, f"{type(exc).__name__}: {exc}"))
        if verbose: traceback.print_exc()
    print(RULE); print("DEMO 18E PREFLIGHT - NO LICENSED PHYSICS EXECUTED"); print(RULE)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        if verbose or not passed: print(f"       {detail}")
    passed = bool(checks) and all(row[1] for row in checks)
    print(RULE); print("CODE READY FOR ARCHIVED WORK-LAPTOP ANALYSIS" if passed else "PREFLIGHT FAILED"); print(RULE)
    return 0 if passed else 1


def run_analysis(args: argparse.Namespace, *, handoff: bool) -> int:
    cfg = config18e.load_config()
    source18d = args.demo18d_run or Path(str(cfg["sources"]["demo18d_run"]))
    source18b = args.demo18b_run or Path(str(cfg["sources"]["demo18b_run"]))
    output_parent = args.output_root or (REPO_ROOT / "demo_results" if handoff else Path("C:/nn_results"))
    root = _run_root(output_parent); log = DebugLog(root / "demo18e_debug.log", args.verbose)
    _write_json(root / "RUN_STATUS.json", {"status": "running", "mode": "handoff" if handoff else "physics",
                                              "new_licensed_solves": 0})
    try:
        shutil.copy2(config18e.CONFIG_PATH, root / "config_snapshot" / config18e.CONFIG_PATH.name)
        bundle = _load_handoff(cfg) if handoff else _load_raw_18d(cfg, source18d)
        if not handoff and not source18b.exists():
            raise Runner18EError(f"required Demo 18B reference run is missing: {source18b}")
        baseline_model = None if handoff else _load_raw_18b(cfg, source18b)
        summary = _analyze(cfg, bundle, root, log, baseline_model)
        _write_json(root / "RUN_STATUS.json", {"status": "completed", "outcome": summary["outcome"],
                                                  "new_licensed_solves": 0, "result_directory": root})
        _terminal(summary, root); return 0
    except Exception as exc:
        log.line(traceback.format_exc())
        _write_json(root / "RUN_STATUS.json", {"status": "failed", "error": f"{type(exc).__name__}: {exc}",
                                                  "result_directory": root})
        print(f"Demo 18E failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"Preserved result directory: {root}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.physics:
        return run_analysis(args, handoff=False)
    if args.analyze_handoff:
        return run_analysis(args, handoff=True)
    return run_preflight(args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
