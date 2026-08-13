"""CLI for Demo 17. Only ``--physics`` can launch licensed full solves.

Ten fixed structures -- Demo 16E's ten, unchanged -- solved once each with three
named corrections applied to the absolute chi(2) scale, then compared against
Demo 16E case by case and against the paper's 2340 pm/V for the abrupt one. No
optimizer runs at any point and nothing in this file reads a result in order to
choose a parameter.

Everything structural is Demo 16E's, reused rather than copied: the same case
ladder, the same parser and realized-composition gates, the same figures. What
Demo 17 supplies is its own config, its own deck template, and the correction
measurement layered on top.
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
DEMO16E = DEMOS / "16E_acqw_structure_physics_optical_comparison"
for path in (SHARED, DEMO14, DEMO11, DEMO16, DEMO16B, DEMO16E, DEMO_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cases17  # noqa: E402
import demo16e  # noqa: E402
import demo17  # noqa: E402
import plots16e  # noqa: E402
import preflight17  # noqa: E402
import runlog14  # noqa: E402

RULE = "=" * 78
CASE_COUNT = cases17.CASE_COUNT
MASTER_CSV = "demo17_master_summary.csv"
MASTER_JSON = "demo17_master_summary.json"
CORRECTIONS_MANIFEST = "corrections_applied.yaml"

#: The bound-state verdict is tri-state on purpose: "could not tell" is a
#: different outcome from "passed", and printing them the same way is exactly
#: how a NOT CERTIFIED result gets read as a pass.
BOUND_LABEL = {True: "PASS", False: "FAIL", None: "NOT CERTIFIED"}

#: Master-summary column order: Demo 16E's columns, then Demo 17's correction
#: budget. Written explicitly so the CSV is stable across runs and so a Demo 17
#: table can be diffed against a Demo 16E one column for column.
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
for _state in demo17.STATE_LABELS:
    MASTER_FIELDS += [
        f"{_state}_left_probability", f"{_state}_barrier_probability",
        f"{_state}_right_probability", f"{_state}_outside_probability",
        f"{_state}_localization",
    ]
MASTER_FIELDS += [
    "chi2_at_1550", "peak_chi2", "peak_wavelength_nm", "detuning_from_1550_nm",
    "chi2_units",
    # --- Demo 17's correction budget -------------------------------------
    "is_paper_target_case",
    "chi2_legacy_settings_pm_per_V", "chi2_demo16e_recorded_pm_per_V",
    "factor_A_well_density_Nz", "factor_B_zincblende_zone_edge",
    "factor_A_times_B", "factor_C_wider_dirichlet_box", "factor_total_vs_demo16e",
    "bound_states_certified", "bound_states_failing", "max_boundary_probability",
    "quantum_region_width_nm", "dirichlet_clearance_nm",
    "paper_target_pm_per_V", "paper_remaining_factor",
    "reference_case", "spectrum_path", "wavefunction_csv_path", "raw_output_dir",
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
    run_id = f"demo17_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = results_root() / demo17.DEMO_ID / run_id
    for sub in ("cases", "plots", "summaries"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def _seed_run(root: Path, run_id: str, mode: str, machine, exe, database, licence,
              case_count: int, cfg) -> dict:
    environment = {
        "run_id": run_id,
        "timestamp_utc": runlog14.utc_now(),
        "demo_id": demo17.DEMO_ID,
        "demo17_version": demo17.DEMO_VERSION,
        "structural_engine": demo16e.DEMO_VERSION,
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
        root / cases17.CASES_FILENAME,
        (DEMO_DIR / cases17.CASES_FILENAME).read_text(encoding="utf-8"),
    )
    # Stamped before anything is solved, so the corrections a run claims cannot
    # be edited into it afterwards.
    demo17.write_corrections_manifest(root / CORRECTIONS_MANIFEST, cfg)
    return environment


def _print_corrections(cfg) -> None:
    record = demo17.corrections_record(cfg)
    a, b, c = record["A_n_wells_per_metre"], record["B_k_max_per_nm"], record["C_domain"]
    print(f"  CORRECTION A : N_z {a['legacy']:.4e} -> {a['corrected']:.4e} m^-1 "
          f"({a['ratio']:.3f}x, exact)")
    print(f"  CORRECTION B : k_max {b['legacy']:.4f} -> {b['corrected']:.4f} nm^-1 "
          f"({b['zone_edge_convention']})")
    print(f"  CORRECTION C : cladding {c['domain_padding_nm']:.1f} nm, Dirichlet "
          f"wall {c['quantum_region_padding_nm']:.1f} nm clear of the wells")
    print("  HELD FIXED   : r_e_hh = "
          f"{record['held_fixed']['r_e_hh_nm']} nm, Gamma = "
          f"{record['held_fixed']['broadening_meV']} meV, "
          f"{record['held_fixed']['max_states_per_band']} states/band, "
          "no fitted scale factor")


# ---------------------------------------------------------------------------
# Structure levels
# ---------------------------------------------------------------------------


def run_levels(*, do_parse: bool, do_structure: bool, mode: str,
               selected_cases=None, verbose: bool = False):
    from preflight16 import database_for, license_for, parser_executable

    cfg = demo17.load_config()
    cases = list(selected_cases if selected_cases is not None else
                 cases17.load_cases(DEMO_DIR / cases17.CASES_FILENAME))
    machine = _machine_or_none()
    exe = parser_executable(machine)
    database = database_for(exe) if exe else None
    licence = license_for(machine)
    root, run_id = new_run_dir()
    environment = _seed_run(
        root, run_id, mode, machine, exe, database, licence, len(cases), cfg
    )

    print(RULE)
    print(f"  DEMO 17 -- {mode.upper()}  (corrected absolute chi(2) reproduction)")
    print(RULE)
    print(f"  RUN DIR    : {root}")
    print(f"  EXECUTABLE : {exe or '<none found>'}")
    print(f"  CASES      : {len(cases)} (fixed, deterministic, no optimization)")
    print(f"  STRUCTURES : identical to Demo 16E; only the calculation changed")
    _print_corrections(cfg)
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
        outcome = demo17.run_case(
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
            f"{' TARGET' if case.is_paper_target else ''}"
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
        "corrections": demo17.corrections_record(cfg),
        "cases": [outcome.as_record() for outcome in outcomes],
    }
    runlog14.write_json_atomic(root / "summary.json", summary)
    _write_structure_summary(
        root / "summaries" / "structure_summary.csv", cfg, cases, outcomes
    )
    runlog14.write_json_atomic(
        root / "RUN_STATUS.json",
        {**environment, "status": "completed", "cases_total": len(outcomes),
         "cases_passed": passed, "cases_failed": len(outcomes) - passed},
    )
    _write_run_readme(root, environment, cfg, cases, outcomes)
    print(RULE)
    label = "PRE-PHYSICS GATE" if mode == "physics" else "RESULT"
    print(f"  {label}: {passed}/{len(outcomes)} passed")
    print(f"  FILES : {root}")
    print(RULE)
    return (0 if passed == len(outcomes) else 1), root, outcomes


def _fmt(value, spec=".6f") -> str:
    return "" if value is None else format(value, spec)


def _write_structure_summary(path: Path, cfg, cases, outcomes) -> None:
    """Demo 16E's structure table, plus the correction-C deck geometry."""

    fields = [
        "case_id", "name", "status", "representation", "asymmetry_s",
        "requested_well_1_nm", "realized_well_1_nm",
        "requested_barrier_nm", "realized_barrier_nm",
        "requested_well_2_nm", "realized_well_2_nm", "realized_total_well_nm",
        "requested_left_grading_nm", "requested_right_grading_nm",
        "realized_left_grading_nm", "realized_right_grading_nm",
        "overlap", "render_method", "expected_peak_al", "realized_peak_al",
        "max_abs_al_error", "rms_al_error", "gated_max_abs_al_error",
        "domain_width_nm", "quantum_region_width_nm",
        "dirichlet_clearance_left_nm", "dirichlet_clearance_right_nm",
    ]
    lines = [",".join(fields) + "\n"]
    for case, outcome in zip(cases, outcomes):
        metric = (outcome.structure or {}).get("comparison") or {}
        geometry = metric.get("geometry") or {}
        realized = {
            row["interface"]: row.get("realized_width_10_90_nm")
            for row in metric.get("realized_interface_metrics") or []
        }
        deck = demo17.deck_geometry_record(cfg, case)
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
            _fmt(deck.get("domain_width_nm"), ".3f"),
            _fmt(deck.get("quantum_region_width_nm"), ".3f"),
            _fmt(deck.get("dirichlet_clearance_left_nm"), ".3f"),
            _fmt(deck.get("dirichlet_clearance_right_nm"), ".3f"),
        ]) + "\n")
    runlog14.write_text_atomic(path, "".join(lines))


def _read_two_column_csv(path: Path):
    import numpy as np
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0], data[:, 1]


def _profile_entries(cfg, cases, outcomes) -> list[dict]:
    entries = []
    for case, outcome in zip(cases, outcomes):
        if outcome.status == "render_failed":
            continue
        _geometry, profile, _blocks, _deck = demo17.build_case(cfg, case)
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
            "overlap": demo17.overlap_geometry(profile, case),
        })
    return entries


def _write_structure_plots(root: Path, cfg, cases, outcomes) -> None:
    import plots

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
            max_al_fraction=cases17.AL_FRACTION,
            note=("realized profile unavailable" if entry["realized_x_nm"] is None
                  else f"nextnano++ realized composition ({case.expected_representation})"),
        )
    if entries:
        plots16e.composition_all_cases(root / "plots" / "composition_all_cases.png",
                                       entries)


def _write_run_readme(root: Path, environment: dict, cfg, cases, outcomes) -> None:
    record = demo17.corrections_record(cfg)
    rows = [
        "| case | name | wells/barrier (nm) | grades (nm) | representation | target | status |",
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
            f"{'**2340 pm/V**' if case.is_paper_target else ''} | {outcome.status} |"
        )
    runlog14.write_text_atomic(root / "README_RUN.md", "\n".join([
        f"# Demo 17 run {environment['run_id']}", "",
        "Demo 16E's ten fixed GaAs/AlGaAs structures, re-solved with three named",
        "corrections to the absolute chi(2) scale. The structures are unchanged,",
        "so the per-case ratio against Demo 16E measures the corrections.", "",
        "## Corrections applied", "",
        f"- **A** N_z {record['A_n_wells_per_metre']['legacy']:.4e} -> "
        f"{record['A_n_wells_per_metre']['corrected']:.4e} m^-1 "
        f"({record['A_n_wells_per_metre']['ratio']:.3f}x, exact)",
        f"- **B** k_max {record['B_k_max_per_nm']['legacy']:.4f} -> "
        f"{record['B_k_max_per_nm']['corrected']:.4f} nm^-1 "
        f"({record['B_k_max_per_nm']['zone_edge_convention']})",
        f"- **C** cladding {record['C_domain']['domain_padding_nm']:.1f} nm, "
        f"Dirichlet wall {record['C_domain']['quantum_region_padding_nm']:.1f} nm "
        "clear of the active region", "",
        "No scale factor was fitted. r_e_hh, Gamma, the 0.10 zone fraction and the",
        "two-states-per-band truncation are published values and are unchanged.", "",
        *rows, "",
        "Only --physics launches full licensed calculations. Raw quantum output",
        "uses the short run-root paths p01 .. p10.", "",
    ]))


# ---------------------------------------------------------------------------
# Physics + comparison
# ---------------------------------------------------------------------------


def _write_master_summary(root: Path, cfg, rows: list[dict], reports: dict) -> None:
    summaries = root / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    payload = {
        "demo_id": demo17.DEMO_ID,
        "demo17_version": demo17.DEMO_VERSION,
        "target_wavelength_nm": demo17.TARGET_WAVELENGTH_NM,
        "detuning_sign_convention": "peak_wavelength_nm - 1550_nm",
        "localization_convention": demo17.LOCALIZATION_CONVENTION,
        "hole_energy_convention": demo17.HOLE_ENERGY_CONVENTION,
        "reference_case": cases17.REFERENCE_CASE_ID,
        "paper_target_case": cases17.PAPER_TARGET_CASE_ID,
        "optimization_performed": False,
        "cases_reported": len(rows),
        "study_summary": demo17.study_summary(cfg, rows),
        "cases": rows,
        **reports,
    }
    runlog14.write_json_atomic(summaries / MASTER_JSON, payload)
    with (summaries / MASTER_CSV).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=MASTER_FIELDS, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
    for name, report in reports.items():
        if report:
            runlog14.write_json_atomic(summaries / f"{name}.json", report)


def _comparison_reports(cfg, rows: list[dict]) -> dict:
    by_case = {row["case"]: row for row in rows}
    reports: dict = {}

    graded_id, abrupt_id = cases17.abrupt_vs_graded_pair()
    if graded_id in by_case and abrupt_id in by_case:
        reports["abrupt_vs_graded"] = demo17.abrupt_vs_graded_report(
            by_case[graded_id], by_case[abrupt_id]
        )

    native_id, imported_id = cases17.equivalence_pair()
    if native_id in by_case and imported_id in by_case:
        cases = {case.case_id: case for case in cases17.all_cases()}
        _g, native_profile, _b, _d = demo17.build_case(cfg, cases[native_id])
        _g, imported_profile, _b, _d = demo17.build_case(cfg, cases[imported_id])
        reports["native_vs_imported_equivalence"] = demo17.equivalence_report(
            by_case[native_id], by_case[imported_id],
            demo17.composition_difference(native_profile, imported_profile),
        )
    return reports


def correction_budget_figure(path: Path, rows: list[dict]) -> Path | None:
    """Question: what was each correction actually worth, per case?

    A grouped bar per case on a log axis: Demo 16E's recorded value, this run's
    value under Demo 16E's own settings (correction C alone), and this run's
    corrected value (C then A then B). The paper's 2340 pm/V is drawn as a line
    so the remaining gap is read off the same axis rather than described.
    """

    import numpy as np
    import plots

    usable = [row for row in rows if row.get("chi2_at_1550") is not None]
    if not plots.plotting_available() or not usable:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    labels = [row["case"] for row in usable]
    positions = np.arange(len(usable), dtype=float)
    series = (
        ("Demo 16E recorded", "chi2_demo16e_recorded_pm_per_V", "#9aa5b1"),
        ("Demo 17, 16E settings (C only)", "chi2_legacy_settings_pm_per_V", "#d45500"),
        ("Demo 17 corrected (C x A x B)", "chi2_at_1550", "#1f4e79"),
    )
    width = 0.26
    fig, ax = plt.subplots(figsize=(11.0, 6.0))
    for index, (label, key, colour) in enumerate(series):
        values = [row.get(key) for row in usable]
        drawn = [v if v else np.nan for v in values]
        ax.bar(positions + (index - 1) * width, drawn, width, label=label,
               color=colour, edgecolor="white", linewidth=0.6)
    target = next(
        (row.get("paper_target_pm_per_V") for row in usable
         if row.get("paper_target_pm_per_V")), None
    )
    if target:
        ax.axhline(float(target), color="#c0392b", ls="--", lw=1.6)
        ax.annotate(f"paper: {float(target):.0f} pm/V",
                    xy=(0.995, float(target)), xycoords=("axes fraction", "data"),
                    xytext=(0, 5), textcoords="offset points",
                    ha="right", fontsize=9, color="#c0392b")
    for index, row in enumerate(usable):
        if row.get("is_paper_target_case"):
            ax.annotate("paper target", xy=(positions[index], 0),
                        xytext=(0, -34), textcoords="offset points",
                        ha="center", fontsize=8, color="#c0392b", rotation=0)
    ax.set_yscale("log")
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel(r"$|\chi^{(2)}_{xzx}|$ at 1550 nm (pm/V)")
    ax.set_title("What each correction was worth, per structure")
    ax.legend(fontsize=8.5, framealpha=0.92)
    ax.grid(alpha=0.2, axis="y", which="both")
    return plots.save_figure(fig, Path(path))


def _write_comparison_plots(root: Path, cfg, rows: list[dict], reports: dict) -> None:
    import plots

    if not plots.plotting_available():
        print(f"  NOTE: plots skipped: {plots.unavailable_reason()}")
        return
    plots_dir = root / "plots"
    plots16e.energy_levels_all_cases(plots_dir / "energy_levels_all_cases.png", rows)
    plots16e.energy_shifts_vs_reference(
        plots_dir / "energy_shifts_vs_reference.png", rows,
        cases17.REFERENCE_CASE_ID,
    )
    plots16e.localization_all_cases(
        plots_dir / "wavefunction_localization_all_cases.png", rows
    )
    plots16e.chi2_wavelength_all_cases(
        plots_dir / "chi2_wavelength_all_cases.png", rows
    )
    plots16e.chi2_wavelength_grouped(plots_dir / "chi2_wavelength_grouped.png", rows)
    plots16e.chi2_at_1550_all_cases(plots_dir / "chi2_at_1550_all_cases.png", rows)
    plots16e.peak_wavelength_and_detuning(
        plots_dir / "peak_wavelength_and_detuning.png", rows
    )
    correction_budget_figure(plots_dir / "correction_budget.png", rows)

    by_case = {row["case"]: row for row in rows}
    graded_id, abrupt_id = cases17.abrupt_vs_graded_pair()
    if reports.get("abrupt_vs_graded"):
        cases = {case.case_id: case for case in cases17.all_cases()}
        profiles = {}
        for case_id in (graded_id, abrupt_id):
            _g, profile, _b, _d = demo17.build_case(cfg, cases[case_id])
            profiles[case_id] = {
                "x_nm": profile.x_nm, "al_fraction": profile.al_fraction,
                "interfaces": profile.request["interfaces_nm"],
            }
        plots16e.abrupt_vs_graded(
            plots_dir / "abrupt_vs_graded_comparison.png",
            by_case[graded_id], by_case[abrupt_id], profiles,
        )
    native_id, imported_id = cases17.equivalence_pair()
    if reports.get("native_vs_imported_equivalence"):
        plots16e.native_vs_imported(
            plots_dir / "native_vs_imported_equivalence.png",
            reports["native_vs_imported_equivalence"],
            by_case[native_id], by_case[imported_id],
        )


def _write_wavefunction_plots(root: Path, cfg, case, record) -> None:
    import plots

    waves = record.pop("_wavefunctions", None)
    if waves is None or not plots.plotting_available():
        return
    _geometry, profile, _blocks, _deck = demo17.build_case(cfg, case)
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
        max_al_fraction=cases17.AL_FRACTION,
    )


def _post_solve_analysis(cfg, case, case_dir: Path, record: dict, baseline) -> dict:
    """Localization and optics for one completed solve; both or neither."""

    raw = Path(record["raw_output_dir"])
    try:
        localization, waves = demo17.localization(
            cfg, raw, demo17.build_case(cfg, case)[1]
        )
    except Exception as exc:  # noqa: BLE001
        record["passed"] = False
        record["failure_stage"] = "localization"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
        return record
    record["localization"] = localization
    record["_wavefunctions"] = waves
    record["wavefunction_csv_path"] = str(demo17.write_wavefunction_csv(
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
        record["optical"] = demo17.analyse_optics(
            cfg, case, case_dir, raw, baseline_chi2=baseline
        )
    except Exception as exc:  # noqa: BLE001
        record["passed"] = False
        record["failure_stage"] = "optical_analysis"
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
    return record


def run_physics(verbose: bool = False, baseline_path: Path | None = None) -> int:
    cases = cases17.load_cases(DEMO_DIR / cases17.CASES_FILENAME)
    machine = _machine_or_none()
    if machine is None or not getattr(machine, "run_solver", False):
        print(
            "Demo 17 physics was not run: this machine is not configured for "
            "licensed nextnano++ solves."
        )
        return 3
    gate_status, root, outcomes = run_levels(
        do_parse=True, do_structure=True, mode="physics",
        selected_cases=cases, verbose=verbose,
    )
    cfg = demo17.load_config()
    baseline = demo17.load_baseline_chi2(baseline_path)
    if not baseline:
        print("  NOTE: no Demo 16E baseline found; correction C's factor will be "
              "reported as unavailable rather than estimated.")
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
            command = demo17.full_physics_command(cfg, case, case_dir, machine=machine)
            print(f"  [FULL-SOLVE] {case.case_id} ({case.expected_representation})")
            print(f"               command={subprocess.list2cmdline(command)}")
            record = demo17.solve_case(cfg, case, case_dir, machine=machine)
            record["reported_full_physics_command"] = command
            if record.get("passed"):
                record = _post_solve_analysis(cfg, case, case_dir, record, baseline)
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
            rows.append(demo17.master_row(
                case, record, comparison,
                outcome.representation or case.expected_representation,
            ))
        analysis = record.get("analysis") or {}
        optical = record.get("optical") or {}
        against = (optical.get("versus_demo16e_baseline") or {})
        return_code = (record.get("solver") or {}).get("solver_return_code")
        state = "PHYS-OK" if record.get("passed") else "PHYS-FAIL"
        print(
            f"  [{state:<9}] {case.case_id} rc={return_code} "
            f"E1={analysis.get('E_e1_eV')} E2={analysis.get('E_e2_eV')} "
            f"HH1={analysis.get('E_hh1_eV')} HH2={analysis.get('E_hh2_eV')} "
            f"chi2(1550)={optical.get('chi2_at_1550')}"
        )
        if record.get("passed"):
            total = against.get("factor_total")
            verdict = (optical.get("bound_state_verdict") or {}).get("certified")
            ratio = "n/a" if total is None else f"{total:.2f}x"
            print(f"               vs 16E: {ratio}  bound-states={BOUND_LABEL[verdict]}")
        else:
            print(f"               stage={record.get('failure_stage', 'unknown')}")
            print(f"               reason={record.get('failure_reason', 'not recorded')}")

    solved = sum(bool(record.get("passed")) for record in records)
    runlog14.write_json_atomic(root / "physics_summary.json", {
        "selected_cases": [case.case_id for case in cases],
        "corrections": demo17.corrections_record(cfg),
        "cases": records, "passed": solved,
    })
    rows = demo17.add_reference_shifts(rows)
    reports = _comparison_reports(cfg, rows)
    _write_master_summary(root, cfg, rows, reports)
    _write_comparison_plots(root, cfg, rows, reports)
    runlog14.write_json_atomic(root / "RUN_STATUS.json", {
        "run_id": root.name, "demo_id": demo17.DEMO_ID, "mode": "physics",
        "status": "completed", "cases_total": CASE_COUNT, "cases_passed": solved,
        "cases_failed": CASE_COUNT - solved,
    })
    _print_physics_epilogue(root, cfg, rows, reports, solved)
    return 0 if gate_status == 0 and solved == CASE_COUNT else 1


def _print_physics_epilogue(root: Path, cfg, rows, reports, solved: int) -> None:
    summary = demo17.study_summary(cfg, rows)
    print(RULE)
    print(f"  PHYSICS + OPTICAL RESULT: {solved}/{CASE_COUNT} solved, gated and analysed")
    for label, key in (
        ("A x B (post-processing conventions)", "factor_A_times_B"),
        ("C     (wider Dirichlet box)", "factor_C_wider_dirichlet_box"),
        ("TOTAL vs Demo 16E", "factor_total_vs_demo16e"),
    ):
        block = summary[key]
        if block["cases"]:
            print(f"  FACTOR {label:<38} median {block['median']:.3f}x "
                  f"(min {block['min']:.3f}, max {block['max']:.3f}, "
                  f"n={block['cases']})")
        else:
            print(f"  FACTOR {label:<38} not computable (no baseline)")
    bound = summary["bound_states_certified"]
    print(f"  BOUND STATES: {bound['true']} certified, {bound['false']} failing, "
          f"{bound['not_certified']} not certified")
    target = summary["paper_target"]
    if target["computed_pm_per_V"] is not None:
        remaining = target["remaining_factor"]
        print(f"  PAPER TARGET ({target['case_id']}, abrupt): "
              f"{target['computed_pm_per_V']:.1f} pm/V computed against "
              f"{target['target_pm_per_V']:.0f} pm/V stated"
              + (f" -- remaining factor {remaining:.1f}x"
                 if remaining is not None else ""))
        print("  Open factors identified but NOT applied: "
              + ", ".join(f"{k}={v}" for k, v in
                          (summary["known_open_factors_not_applied"] or {}).items()))
    print(f"  SUMMARY: {root / 'summaries' / MASTER_CSV}")
    print(f"  PLOTS  : {root / 'plots'}")
    print(RULE)


# ---------------------------------------------------------------------------
# Reanalysis
# ---------------------------------------------------------------------------


def analyze_existing(path: Path, baseline_path: Path | None = None) -> int:
    """Rebuild every table and figure from an existing run; never runs a solver."""

    root = Path(path).resolve()
    physics_path = root / "physics_summary.json"
    if not physics_path.is_file():
        summary = root / "summary.json"
        if not summary.is_file():
            print(f"No Demo 17 summary at {root}")
            return 1
        payload = json.loads(summary.read_text(encoding="utf-8"))
        print(f"Demo 17 {payload['run_id']}: "
              f"{payload['cases_passed']}/{payload['cases_total']} validation cases passed")
        return 0
    cfg = demo17.load_config()
    baseline = demo17.load_baseline_chi2(baseline_path)
    cases = {case.case_id: case for case in
             cases17.load_cases(DEMO_DIR / cases17.CASES_FILENAME)}
    payload = json.loads(physics_path.read_text(encoding="utf-8"))
    rows, changed = [], False
    for record in payload.get("cases", []):
        case = cases.get(record.get("case_id"))
        if case is None or not record.get("passed"):
            continue
        case_dir = root / "cases" / case.case_id
        if not record.get("localization") or not record.get("optical"):
            record = _post_solve_analysis(cfg, case, case_dir, record, baseline)
            _write_wavefunction_plots(root, cfg, case, record)
            record.pop("_wavefunctions", None)
            changed = True
        comparison = _stored_comparison(case_dir)
        representation = _stored_representation(case_dir, case)
        rows.append(demo17.master_row(case, record, comparison, representation))
    if changed:
        runlog14.write_json_atomic(physics_path, payload)
    rows = demo17.add_reference_shifts(rows)
    reports = _comparison_reports(cfg, rows)
    _write_master_summary(root, cfg, rows, reports)
    _write_comparison_plots(root, cfg, rows, reports)
    print(f"Demo 17 existing run: {len(rows)}/{CASE_COUNT} physics cases "
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


def show_corrections() -> int:
    """Print the three corrections and exit. No solver, no run directory."""

    import yaml

    cfg = demo17.load_config()
    print(yaml.safe_dump(demo17.corrections_record(cfg), sort_keys=False,
                         default_flow_style=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Demo 17: Demo 16E's ten ACQW structures re-solved with a per-well "
            "N_z, a zincblende 2*pi/a zone edge and a Dirichlet box moved clear "
            "of the wells, against the paper's 2340 pm/V ideal-abrupt value"
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--corrections", action="store_true",
                       help="print the three corrections and exit")
    group.add_argument("--syntax", action="store_true")
    group.add_argument("--structure", action="store_true")
    group.add_argument("--validate", action="store_true")
    group.add_argument("--physics", action="store_true")
    group.add_argument("--write-cases", action="store_true")
    group.add_argument("--analyze-existing", metavar="RUN_DIR")
    parser.add_argument("--baseline", metavar="PHYSICS_SUMMARY_JSON",
                        help="Demo 16E physics_summary.json for correction C")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    baseline = Path(args.baseline) if args.baseline else None
    if args.write_cases:
        print(cases17.write_cases_file(DEMO_DIR / cases17.CASES_FILENAME))
        return 0
    if args.corrections:
        return show_corrections()
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
        return run_physics(verbose=args.verbose, baseline_path=baseline)
    if args.analyze_existing:
        return analyze_existing(Path(args.analyze_existing), baseline)
    return preflight17.run_preflight(verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
