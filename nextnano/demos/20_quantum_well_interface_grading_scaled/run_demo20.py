"""Demo 20 command-line entry point.

Three modes, and only one of them can touch a licence:

    python run_demo20.py --preflight        solver-free: cases, decks, profiles
    python run_demo20.py --analysis-only    solver-free: chi2, plots, reports
    python run_demo20.py --physics          LICENSED: 13 nextnano++ solves

``--analysis-only`` is the home-laptop path. It re-runs the chi2 postprocessing
against real licensed solver output read from a results table, so nothing is
fabricated and no licence is needed.

The k-space convention can be overridden per execution without editing the YAML:

    python run_demo20.py --analysis-only --kspace-scale off
    python run_demo20.py --analysis-only --kspace-scale on

Both conventions are always computed and always written to the output tables;
``--kspace-scale`` only selects which one is labelled "reported".

Stage order, matching the module numbering:

    s01 cases -> s02 grading profiles -> s03 nextnano inputs
      -> s04 solver (licensed only) -> s05 extract states
      -> s06 chi2 physics -> s07 analysis -> s08 QC
      -> s09 plots -> s10 reports
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any, Mapping

DEMO_DIR = Path(__file__).resolve().parent
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

import config20                       # noqa: E402
import s01_cases as cases             # noqa: E402
import s03_inputs as inputs           # noqa: E402
import s04_solver as solver           # noqa: E402
import s05_extract as extract         # noqa: E402
import s06_chi2 as chi2mod            # noqa: E402
import s07_analysis as analysis       # noqa: E402
import s08_qc as qc                   # noqa: E402
import s09_plots as plots             # noqa: E402
import s10_report as report           # noqa: E402


def _stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _print_header(cfg: Mapping[str, Any], mode: str) -> None:
    print("=" * 74)
    print(f"DEMO 20 - {cfg['demo']['name']}  [{mode}]")
    print("=" * 74)
    print(f"config          : {cfg.get('_config_path')}")
    overrides = cfg.get("_overrides") or {}
    if overrides:
        for key, value in overrides.items():
            print(f"cli override    : {key} = {value}")
    print(f"scaling enabled : {config20.scaling_enabled(cfg)}")
    print(f"utc             : {_stamp()}")


# --- preflight ---------------------------------------------------------------


def run_preflight(cfg: Mapping[str, Any], *, verbose: bool = False) -> int:
    """Every solver-free gate, plus the decks and the two profile figures."""

    paths = config20.paths(cfg).mkdirs()
    _print_header(cfg, "preflight, no solver")
    preflight = inputs.preflight_report(cfg)
    tables = report.write_case_tables(cfg, paths.tables)
    inputs.write_case_inputs(cfg, paths.inputs)
    examples = inputs.write_input_examples(
        cfg, paths.tables / "demo20_nextnano_input_examples.md")
    report.write_json(paths.qc / "demo20_preflight_report.json", preflight)
    figures = plots.input_plots(cfg, paths.plots) if cfg["plots"]["enabled"] else []

    machine = solver.machine_status()
    print()
    print(f"cases                    : {preflight['case_count']}")
    print(f"grading valid            : "
          f"{sum(v['validation_pass'] for v in preflight['validations'])}"
          f"/{preflight['case_count']}")
    print(f"decks complete           : {preflight['all_decks_complete']}")
    print(f"imported tables present  : {preflight['all_imported_tables_present']}")
    print(f"overlapping grades       : {preflight['overlap_cases'] or 'none'}")
    print(f"licensed solves performed: 0")
    print(f"licensed solver available: {machine.available} ({machine.reason})")
    print()
    print(f"case table      : {tables['cases']}")
    print(f"validation      : {tables['validation']}")
    print(f"implementation  : {tables['audit']}")
    print(f"input examples  : {examples}")
    print(f"decks           : {paths.inputs}")
    for figure in figures:
        print(f"figure          : {figure}")
    if verbose:
        for deck in preflight["decks"]:
            print(f"  case_{deck['case_id']}: method={deck['render_method']} "
                  f"complete={deck['deck_complete']} "
                  f"dat_rows={deck['datafile_rows']}")
    ok = (preflight["all_grading_valid"] and preflight["all_decks_complete"]
          and preflight["all_imported_tables_present"])
    return 0 if ok else 1


# --- analysis ---------------------------------------------------------------


def run_analysis(cfg: Mapping[str, Any], *, verbose: bool = False,
                 solver_ran_here: bool = False,
                 extracted: Mapping[str, extract.ExtractedCase] | None = None,
                 wavefunction_data: Mapping[str, Path] | None = None) -> int:
    """chi2 under both conventions, QC, plots and reports. No licence needed."""

    paths = config20.paths(cfg).mkdirs()
    if extracted is None:
        _print_header(cfg, "analysis only, no solver")
        source_path = config20.master_table_path(cfg)
        if str(cfg["analysis"]["source"]) != extract.SOURCE_MASTER_TABLE:
            raise SystemExit(
                "--analysis-only needs analysis.source: master_table. To parse a "
                "raw licensed run directory, use --physics on the licensed machine."
            )
        print(f"states source   : {source_path}")
        extracted = extract.from_master_table(
            source_path,
            max_states_per_band=int(cfg["states"]["max_states_per_band"]),
        )
    else:
        source_path = None

    settings = chi2mod.settings_from_config(cfg)

    # --- the normalization audit, before any number is reported --------------
    audit = qc.normalization_audit(
        settings, scaling_enabled=config20.scaling_enabled(cfg))
    audit_text = qc.format_normalization_audit(audit)
    print()
    print(audit_text)

    # --- stage 07: both conventions for every case --------------------------
    results = analysis.analyse_cases(cfg, extracted)
    pairs = [result.pair for result in results if result.has_spectrum]
    with_spectra = [result for result in results if result.has_spectrum]
    if not with_spectra:
        print("\nNo case produced a spectrum. Nothing was fabricated; see the "
              "failure columns in the master table.")

    # --- stage 08: QC -------------------------------------------------------
    status = qc.status_summary([result.row for result in results])
    convergence = None
    if with_spectra:
        convergence = chi2mod.k_convergence_report(
            extracted[with_spectra[0].case_id].states,
            float(cfg["chi2"]["target_wavelength_nm"]),
            settings,
            point_counts=tuple(cfg["k_parallel"]["convergence_probe_points"]),
            tolerance=float(cfg["k_parallel"]["convergence_tolerance"]),
        )
    numeric_checks = qc.numerics_checks(settings, convergence)
    invariance_checks = qc.scaling_invariance_checks(pairs, cfg) if pairs else []
    print()
    print(qc.format_checks("NUMERICS CHECKS", numeric_checks))
    if invariance_checks:
        print()
        print(qc.format_checks("SCALING INVARIANCE CHECKS", invariance_checks))

    # --- stage 07 (paper) + stage 10: reports -------------------------------
    paper = analysis.paper_comparison(cfg, results)
    numerics_ok = all(check.passed for check in numeric_checks) and all(
        check.passed for check in invariance_checks)
    validation = qc.validation_status(
        code_tests_passed=True,
        numerics_checks_passed=numerics_ok,
        solver_ran_here=solver_ran_here,
        all_physical_valid=status["all_physical_valid"],
        paper_ratio=(paper.get("scaled_ratio_to_paper")
                     if paper.get("evaluated") else None),
    )
    master = report.write_master_table(paths.tables, results)
    presentation = report.write_presentation_table(paths.tables, results)
    scaling_table = (report.write_scaling_table(paths.tables, results)
                     if with_spectra else None)
    report.write_case_tables(cfg, paths.tables)
    normalization_files = report.write_normalization_audit(
        paths.qc, audit, audit_text)
    report.write_qc_report(paths.qc, {
        "generated_utc": _stamp(),
        "status_summary": status,
        "validation_status": validation,
        "numerics_checks": [check.as_record() for check in numeric_checks],
        "scaling_invariance_checks": [check.as_record()
                                      for check in invariance_checks],
        "k_convergence": convergence,
        "chi2_settings": settings.as_record(),
    })
    figures = plots.all_plots(cfg, paths.plots, results,
                              wavefunction_data=wavefunction_data)
    report.write_json(paths.data / "demo20_spectra_index.json", {
        "note": "Full spectra are written per case beside this index.",
        "cases": _write_spectra(paths.data, results),
    })
    summary = report.write_summary(paths.tables, cfg, results, audit, status,
                                   paper, validation)
    report.write_run_record(paths.root, {
        "generated_utc": _stamp(),
        "configuration": config20.as_record(cfg),
        "source": extract.describe_source(cfg, source_path),
        "solver_ran_in_this_execution": solver_ran_here,
        "figures": figures,
        "validation_status": validation,
        "paper_comparison": paper,
    })

    print()
    print(report.terminal_summary(cfg, results, paper, status))
    print(f"MASTER TABLE        : {master}")
    print(f"PRESENTATION TABLE  : {presentation}")
    if scaling_table:
        print(f"SCALING COMPARISON  : {scaling_table}")
    print(f"NORMALIZATION AUDIT : {normalization_files['text']}")
    print(f"SUMMARY             : {summary}")
    print(f"FIGURES             : {len(figures.get('made', []))} written to "
          f"{paths.plots}")
    for name in figures.get("skipped", []):
        print(f"  skipped {name}: {figures['skip_reasons'][name]}")
    print(f"RESULTS ROOT        : {paths.root}")
    if verbose:
        for result in results:
            print(f"  case {result.case_id}: spectrum="
                  f"{result.has_spectrum} solver_pass={result.row['solver_pass']} "
                  f"physical_valid={result.row['physical_valid']}")
    return 0 if with_spectra and numerics_ok else 1


def _write_spectra(destination: Path,
                   results) -> list[dict[str, Any]]:
    """One CSV per case with both conventions' spectra, side by side."""

    import numpy as np

    index: list[dict[str, Any]] = []
    for result in results:
        if not result.has_spectrum:
            continue
        pair = result.pair
        path = destination / f"case_{result.case_id}_chi2_spectrum.csv"
        columns = np.column_stack([
            pair.raw.wavelength_nm, pair.raw.photon_energy_eV,
            pair.raw.chi2.real, pair.raw.chi2.imag, pair.raw.magnitude,
            pair.scaled.chi2.real, pair.scaled.chi2.imag, pair.scaled.magnitude,
        ])
        np.savetxt(
            path, columns, delimiter=",",
            header=("wavelength_nm,photon_energy_eV,"
                    "chi2_raw_real_pm_per_V,chi2_raw_imag_pm_per_V,"
                    "chi2_raw_abs_pm_per_V,"
                    "chi2_scaled_real_pm_per_V,chi2_scaled_imag_pm_per_V,"
                    "chi2_scaled_abs_pm_per_V"),
            comments="",
        )
        index.append({"case_id": result.case_id, "path": str(path),
                      "points": int(pair.raw.wavelength_nm.size)})
    return index


# --- licensed physics -------------------------------------------------------


def run_physics(cfg: Mapping[str, Any], *, verbose: bool = False) -> int:
    """13 licensed nextnano++ solves, then the same analysis stages.

    The complete solver-free gate runs first, so a bad deck is caught before a
    licence is consumed.
    """

    _print_header(cfg, "LICENSED PHYSICS")
    preflight = inputs.preflight_report(cfg)
    if not (preflight["all_grading_valid"] and preflight["all_decks_complete"]):
        raise SystemExit("Demo 20 preflight failed; refusing licensed physics.")
    machine = solver.require_machine()
    paths = config20.paths(cfg).mkdirs()
    print(f"executable      : {machine.executable}")
    print(f"database        : {machine.database}")

    extracted: dict[str, extract.ExtractedCase] = {}
    wavefunction_data: dict[str, Path] = {}
    for case in cases.all_cases():
        case_dir = paths.data / f"case_{case.case_id}"
        raw_dir = case_dir / "nextnano_output"
        print(f"[SOLVE {case.case_id}/12] {case.case_name}")
        try:
            invocation = solver.solve_case(
                cfg, case, machine, case_dir=case_dir, raw_output_dir=raw_dir)
            metrics, matrix_elements = solver.parse_case(
                cfg, case, raw_dir, case_dir)
            states = extract.states_from_nextnano_metrics(
                case.case_id, metrics, matrix_elements,
                provenance=f"nextnano_output:{raw_dir}",
            )
            physical_valid = bool(metrics.get("physical_qc_valid", False))
            extracted[case.case_id] = extract.ExtractedCase(
                case_id=case.case_id, states=states,
                solver_pass=invocation.solver_pass, physical_valid=physical_valid,
                source=extract.SOURCE_NEXTNANO_OUTPUT, source_detail=str(raw_dir),
                failure_stage="" if physical_valid else "physical_validation",
                failure_reason=("" if physical_valid else
                                "Demo 11/14 physical QC did not pass"),
                extras={"solver_return_code": invocation.return_code},
            )
            report.write_json(case_dir / "case_result.json", {
                "case": case.as_case_row(cfg),
                "solver": invocation.as_record(),
                "physical_qc_valid": physical_valid,
                "metrics_keys": sorted(metrics),
            })
        except Exception as exc:                       # keep every failure visible
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            extracted[case.case_id] = extract.ExtractedCase(
                case_id=case.case_id, states=None, solver_pass=False,
                physical_valid=False, source=extract.SOURCE_NEXTNANO_OUTPUT,
                source_detail=str(raw_dir),
                failure_stage="solver_or_analysis",
                failure_reason=f"{type(exc).__name__}: {exc}",
                extras={},
            )
    return run_analysis(cfg, verbose=verbose, solver_ran_here=True,
                        extracted=extracted, wavefunction_data=wavefunction_data)


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Demo 20 - interface grading with a configurable (2*pi)^2 "
                    "k-space normalization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true",
                     help="solver-free: cases, decks, composition profiles")
    mode.add_argument("--analysis-only", action="store_true",
                     help="solver-free: chi2, QC, plots and reports from a "
                          "results table (default)")
    mode.add_argument("--physics", action="store_true",
                     help="run 13 licensed nextnano++ solves, then analyse")
    parser.add_argument("--kspace-scale", choices=["on", "off"], default=None,
                        help="override chi2.apply_kspace_2pi_squared_scaling for "
                             "this execution only")
    parser.add_argument("--master-table", default=None,
                        help="override analysis.master_table (repo-relative ok)")
    parser.add_argument("--results-root", default=None,
                        help="override paths.results_root (repo-relative ok)")
    parser.add_argument("--no-plots", action="store_true",
                        help="skip figure generation")
    parser.add_argument("--config", default=None, help="alternative config YAML")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    cfg = config20.load(Path(args.config) if args.config else None)
    cfg = config20.apply_overrides(
        cfg,
        kspace_scale=args.kspace_scale,
        master_table=args.master_table,
        results_root=args.results_root,
        plots=False if args.no_plots else None,
    )
    if args.physics:
        try:
            return run_physics(cfg, verbose=args.verbose)
        except solver.Solver20Error as exc:
            # An unavailable licence is an expected outcome on the home laptop,
            # not a bug. Report it as a message rather than a traceback.
            print(f"\n{exc}", file=sys.stderr)
            return 2
    if args.preflight:
        return run_preflight(cfg, verbose=args.verbose)
    try:
        return run_analysis(cfg, verbose=args.verbose)
    except extract.Extract20Error as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
