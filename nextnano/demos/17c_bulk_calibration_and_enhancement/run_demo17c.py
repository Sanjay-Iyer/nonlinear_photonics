"""CLI for Demo 17c -- bulk control calibration and enhancement analysis.

Reads Demo 17's saved artifacts and fits ONE global scalar to ONE published
number. No solver, no licence, no network. Runs in about a second.

    python nextnano/demos/17c_bulk_calibration_and_enhancement/run_demo17c.py
    ... --anchor-peak            anchor on the Fig. 2d peak instead of 1550 nm
    ... --results-dir <run_dir>  read a raw run tree, which also carries spectra

The anchor case reproduces its target by construction and is labelled as such in
every table. The evidence is the rows that were not fitted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
REPO_ROOT = DEMOS.parents[1]
for _path in (DEMOS / "_shared", DEMOS / "17b_prefactor_scale_audit", DEMO_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import yaml  # noqa: E402

import calibration17c as calib  # noqa: E402
import prefactor_audit17b as audit17b  # noqa: E402

RULE = "=" * 104
THIN = "-" * 104
CONFIG_FILENAME = "demo17c.yaml"

VERDICT = {True: "PASS", False: "MISS", None: "n/a"}


def load_config(path: Path | None = None) -> dict:
    target = Path(path) if path else DEMO_DIR / CONFIG_FILENAME
    if not target.is_file():
        raise calib.Calibration17cError(f"Demo 17c configuration not found: {target}")
    cfg = yaml.safe_load(target.read_text(encoding="utf-8"))
    for section in ("experiment", "source", "bulk_reference", "calibration",
                    "predictions", "enhancement", "reporting"):
        if section not in cfg:
            raise calib.Calibration17cError(f"demo17c.yaml is missing '{section}'.")
    return dict(cfg)


def _f(value, spec=".1f", none="n/a") -> str:
    if value is None:
        return none
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return str(value)


def print_bulk_block(bulk: calib.BulkReference) -> None:
    print("  STEP A -- BULK CONTROL REFERENCE")
    print(THIN)
    print(f"    bulk GaAs            {bulk.gaas_pm_per_V:.0f} pm/V")
    print(f"    bulk Al0.55Ga0.45As  {bulk.algaas_pm_per_V:.0f} pm/V")
    print(f"    source               {bulk.source}")
    print(f"    Eq. 2 can evaluate bulk? {bulk.evaluator_can_compute_bulk}")
    if not bulk.evaluator_can_compute_bulk:
        for line in _wrap(bulk.reason, 96):
            print(f"      {line}")
        print("    -> 377/290 are used as the ENHANCEMENT DENOMINATOR and the "
              "plot's reference lines,")
        print("       which is the role they can support. The anchor comes from "
              "the paper's own")
        print("       same-equation, same-structure value instead.")
    print()


def _wrap(text: str, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines


def print_calibration_block(calibration: calib.Calibration) -> None:
    print("  STEP B -- THE SINGLE FITTED SCALAR")
    print(THIN)
    print(f"    K = {calibration.anchor_target_pm_per_V:.1f} / "
          f"{calibration.anchor_raw_pm_per_V:.4f} = {calibration.factor:.4f}")
    print(f"    anchored on          {calibration.anchor_case_id} "
          f"({calibration.anchor_quantity})")
    print(f"    anchor source        {calibration.anchor_source.strip()}")
    print(f"    degrees of freedom   1  (one real positive scalar, nothing else)")
    print("    K absorbs            every unstated prefactor convention at once: "
          "the N_z volume")
    print("                         definition, the Eq.1/Eq.2 counting, the "
          "permutation multiplicity,")
    print("                         and any residual unit or hbar^2 bookkeeping. "
          "It cannot separate")
    print("                         them -- that is what Demo 17b is for.")
    print()


def print_cases_table(calibrated, target_nm: float) -> None:
    print("  STEP C -- CALIBRATED ABSOLUTE SUSCEPTIBILITY")
    print(THIN)
    print(f"  {'case':9}{'name':<26}{'raw@1550':>10}{'cal@1550':>11}"
          f"{'raw peak':>10}{'cal peak':>11}{'peak nm':>9}{'enh@peak':>10}  ")
    print(THIN)
    for case in calibrated:
        mark = " <- anchor" if case.is_anchor else ""
        print(f"  {case.row.case_id:9}{case.row.name[:25]:<26}"
              f"{case.row.raw_at_target_pm_per_V:>10.2f}"
              f"{case.calibrated_at_target:>11.1f}"
              f"{case.row.raw_peak_pm_per_V:>10.2f}"
              f"{case.calibrated_peak:>11.1f}"
              f"{case.row.peak_wavelength_nm:>9.0f}"
              f"{case.enhancement_peak:>9.2f}x{mark}")
    print(THIN)
    print(f"  cal = K x raw. Units: pm/V, calibrated reproduction. "
          f"enh = calibrated / bulk GaAs.")
    print()


def print_predictions(predictions) -> None:
    print("  WHAT THE CALIBRATION DID NOT FIT")
    print(THIN)
    print(f"  {'':5}{'published quantity':<44}{'predicted':>11}{'published':>18}"
          f"{'error':>9}{'':>7}")
    print(THIN)
    for entry in predictions:
        published = entry.published_pm_per_V
        published_text = (f"{min(published):.0f}-{max(published):.0f}"
                          if isinstance(published, (list, tuple))
                          else f"{float(published):.0f}")
        if entry.is_anchor:
            print(f"  {'--':5}{entry.label[:43]:<44}"
                  f"{entry.predicted_pm_per_V:>11.1f}{published_text:>18}"
                  f"{'fitted':>9}{'':>7}")
            continue
        error = entry.relative_error
        print(f"  {VERDICT[entry.within_tolerance]:5}{entry.label[:43]:<44}"
              f"{entry.predicted_pm_per_V:>11.1f}{published_text:>18}"
              f"{error * 100:>8.1f}%"
              f"{'  (+-' + _f(entry.tolerance_percent, '.0f') + '%)':>7}")
    print(THIN)
    print("  '--' marks the anchor: it reproduces its target by construction and "
          "is NOT evidence.")
    print()


def print_enhancement(summary: dict) -> None:
    print("  STEP D -- ENHANCEMENT OVER BULK GaAs")
    print(THIN)
    print(f"    {summary['definition']}")
    for line in _wrap(summary["note"], 96):
        print(f"    {line}")
    print()
    band = summary.get("expected_band")
    print(f"    published points, expressed as enhancement:")
    for name, value in sorted(summary["published_points_as_enhancement"].items(),
                              key=lambda kv: -kv[1]):
        flag = "   <- the paper's '>7x' claim" if "four_period" in name else ""
        print(f"      {name:28} {value:6.2f}x{flag}")
    print()
    if band:
        inside = summary["cases_in_expected_band_at_peak"]
        print(f"    cases whose PEAK enhancement lands in {band[0]:.0f}-{band[1]:.0f}x: "
              + (", ".join(inside) if inside else "none"))
    print(f"    {'case':10}{'enh @1550':>12}{'enh @peak':>12}")
    for row in summary["per_case"]:
        print(f"    {row['case']:10}{row['enhancement_at_1550']:>11.2f}x"
              f"{row['enhancement_peak']:>11.2f}x")
    print()


def print_epilogue(report: dict) -> None:
    print(RULE)
    print("  WHAT THIS DEMO DOES AND DOES NOT SHOW")
    print(RULE)
    predictions = [p for p in report["predictions"] if not p["is_anchor_not_evidence"]]
    hits = [p for p in predictions if p["within_tolerance"]]
    print(f"  ONE scalar fitted. {len(hits)}/{len(predictions)} unfitted published "
          "numbers reproduced inside tolerance.")
    print()
    print("  This is a CALIBRATED REPRODUCTION, not an absolute prediction. The "
          "absolute scale rests")
    print("  on the fitted K; what the physics supplies is every RATIO -- between "
          "structures, between")
    print("  wavelengths, and against bulk. Those ratios were already correct "
          "before calibration and")
    print("  are unchanged by it.")
    print()
    print("  The enhancement over bulk is the strongest number here precisely "
          "because K cancels out")
    print("  of it: it is what the raw evaluator already said, expressed against "
          "the 377 pm/V")
    print("  reference.")
    print()
    print(f"  Still unexplained: the {report['calibration']['calibration_factor_K']:.1f}x "
          "K itself. Demo 17b bounded the candidates -- N_z counting")
    print("  length (x3) and the Eq.1/Eq.2 or permutation factor (x3, probably "
          "one factor not two),")
    print("  with r_e_hh and the m_j doublet both closed. Calibration removes the "
          "offset; it does")
    print("  not identify it.")
    print(RULE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Demo 17c: anchor the converged Eq. 2 evaluator to one "
                     "published value, then report every other case as a "
                     "prediction and measure the enhancement over bulk GaAs.")
    )
    parser.add_argument("--config", metavar="YAML")
    parser.add_argument("--results-dir", metavar="DIR",
                        help="Demo 17 hand-off or raw run tree (a run tree also "
                             "carries the 1400-1800 nm spectra)")
    parser.add_argument("--anchor-peak", action="store_true",
                        help="anchor on the peak instead of the 1550 nm value")
    parser.add_argument("--anchor-target", type=float, metavar="PM_PER_V",
                        help="override the anchor target value")
    parser.add_argument("--out", metavar="DIR", help="output directory")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config) if args.config else None)
    if args.anchor_peak:
        cfg["calibration"]["anchor_quantity"] = "at_peak"
    if args.anchor_target is not None:
        cfg["calibration"]["anchor_target_pm_per_V"] = float(args.anchor_target)

    results_dir = audit17b.resolve_results_dir(
        Path(args.results_dir) if args.results_dir
        else (Path(cfg["source"]["results_dir"]) if cfg["source"].get("results_dir")
              else None)
    )
    target_nm = float(cfg["source"]["target_wavelength_nm"])

    print(RULE)
    print("  DEMO 17c -- BULK CONTROL CALIBRATION AND ENHANCEMENT ANALYSIS")
    print(RULE)
    print(f"  source      : {results_dir}")
    print(f"  solver runs : none (bulk_solve.enabled = "
          f"{bool((cfg.get('bulk_solve') or {}).get('enabled'))})")
    print()

    bulk = calib.bulk_reference_evaluation(cfg)
    print_bulk_block(bulk)

    rows = calib.load_cases(results_dir, cfg)
    calibration = calib.calibration_factor(rows, cfg, bulk)
    print_calibration_block(calibration)

    calibrated = calib.apply_calibration(rows, calibration, bulk)
    print_cases_table(calibrated, target_nm)

    predictions = calib.validate_predictions(calibrated, calibration, cfg)
    print_predictions(predictions)

    enhancement = calib.enhancement_summary(calibrated, cfg, bulk)
    print_enhancement(enhancement)

    report = calib.build_report(
        calibrated, calibration, bulk, predictions, enhancement, cfg, results_dir
    )

    out_dir = Path(args.out) if args.out else REPO_ROOT / cfg["reporting"]["output_subdir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = calib.write_calibrated_csv(
        out_dir / cfg["reporting"]["csv_filename"], calibrated
    )
    json_path = out_dir / cfg["reporting"]["json_filename"]
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    plot_path = None
    if not args.no_plot:
        plot_path = calib.write_calibrated_spectrum_plot(
            out_dir / cfg["reporting"]["plot_filename"], calibrated, bulk,
            calibration, target_nm,
        )

    spectra = report["spectra_available"]
    print(f"  CSV   : {csv_path}")
    print(f"  JSON  : {json_path}")
    print(f"  PLOT  : {plot_path if plot_path else 'skipped'}")
    if spectra == 0:
        print(f"  NOTE  : no chi2_focused.csv in this hand-off, so the plot shows "
              f"per-case peak and {target_nm:.0f} nm markers rather than curves.")
        print("          Point --results-dir at the raw run tree, or copy the "
              "spectra, for full curves.")
    else:
        print(f"  NOTE  : {spectra}/{len(calibrated)} cases carried full spectra.")
    print()

    print_epilogue(report)

    missed = [p for p in predictions
              if not p.is_anchor and p.within_tolerance is False]
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main())
