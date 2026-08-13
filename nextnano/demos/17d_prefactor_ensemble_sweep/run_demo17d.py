"""CLI for Demo 17d -- prefactor estimation ensemble sweep.

Reads Demo 17's saved artifacts and compounds ten declared multiplier
combinations across the 1400-1800 nm window. No solver, no licence, no network.

    python nextnano/demos/17d_prefactor_ensemble_sweep/run_demo17d.py
    ... --targets-profile demo17c    score against Demo 17c's reading of the paper
    ... --cross-overlaps zero        rebuild the curves with nothing fitted at all
    ... --results-dir <dir>          read another hand-off or a raw run tree

Nothing here is fitted to a published number. The exit status is 0 when at least
one combination lands inside the configured match threshold and 1 when none
does -- a miss is a result, so it is reported either way rather than suppressed.
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

import ensemble17d as ens  # noqa: E402
import prefactor_audit17b as audit17b  # noqa: E402

RULE = "=" * 112
THIN = "-" * 112
CONFIG_FILENAME = "demo17d.yaml"

STATUS_LEGEND = {
    "established": "a cited source requires it",
    "reported": "Demo 17b computed it and declined to promote it",
    "speculative": "no source in this repository establishes it",
    "contradicted": "a measurement in this repository points the other way",
}


def load_config(path: Path | None = None) -> dict:
    target = Path(path) if path else DEMO_DIR / CONFIG_FILENAME
    if not target.is_file():
        raise ens.Ensemble17dError(f"Demo 17d configuration not found: {target}")
    cfg = yaml.safe_load(target.read_text(encoding="utf-8"))
    for section in ("experiment", "source", "spectrum", "factors",
                    "combinations", "targets", "scoring", "reporting"):
        if section not in cfg:
            raise ens.Ensemble17dError(f"demo17d.yaml is missing '{section}'.")
    return dict(cfg)


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


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------


def print_source_block(results_dir: Path, spectra, profile: str) -> None:
    print("  STEP A -- WHAT DEMO 17 HANDED OVER")
    print(THIN)
    print(f"    source          {results_dir}")
    print(f"    solver runs     none")
    print(f"    targets profile {profile}")
    print()
    print(f"    {'case':10}{'role':11}{'chi2@1550':>11}{'peak':>10}{'peak nm':>9}"
          f"{'peak/1550':>11}  curve")
    for spectrum in spectra:
        print(f"    {spectrum.case_id:10}{spectrum.label:11}"
              f"{spectrum.stored_at_target:>11.2f}{spectrum.stored_peak:>10.2f}"
              f"{spectrum.stored_peak_nm:>9.0f}"
              f"{spectrum.peak_over_target_contrast:>11.3f}  {spectrum.provenance}")
    print()
    for spectrum in spectra:
        if spectrum.provenance == "stored_anchors_only":
            reason = spectrum.diagnostics.get("rebuild_declined", "not available")
            print(f"    {spectrum.case_id}: no curve. {reason}")
            continue
        if spectrum.provenance != "eq2_rebuilt_from_recorded_matrix_elements":
            continue
        fidelity = spectrum.fidelity
        print(f"    {spectrum.case_id}: lineshape rebuilt from the matrix elements "
              f"Demo 17 recorded, tier "
              f"'{spectrum.diagnostics.get('loading_tier', '?')}'.")
        print(f"      cross overlaps   {fidelity.get('model')}"
              f"  <e1|hh2> = {fidelity.get('fitted_overlap_e1_hh2', 0.0):+.4f}"
              f"  <e2|hh1> = {fidelity.get('fitted_overlap_e2_hh1', 0.0):+.4f}")
        print(f"      vs stored anchors  1550 nm {fidelity['at_1550_error_percent']:+.2f} %"
              f"   peak {fidelity['peak_error_percent']:+.2f} %"
              f"   peak position {fidelity['peak_wavelength_error_nm']:+.0f} nm")
        origin = spectrum.diagnostics.get("origin_independence") or {}
        kernel = spectrum.diagnostics.get("kernel_agreement") or {}
        print(f"      origin independence {origin.get('relative_error', float('nan')):.1e}"
              f" ({'PASS' if origin.get('passed') else 'FAIL'})"
              f"    vs Demo 17b's kernel "
              f"{kernel.get('max_relative_deviation', float('nan')):.1e}"
              f" ({'PASS' if kernel.get('agrees') else 'FAIL'})")
    print()
    print("    The two numbers this demo REPORTS per case are the stored ones above.")
    print("    The rebuilt curve is drawn, never reported -- so the table below is")
    print("    exact even where the lineshape is a reconstruction.")
    print()


def print_matrix_block(combos) -> None:
    print("  STEP B -- THE ENSEMBLE MATRIX")
    print(THIN)
    print(f"  | {'ID':2} | {'combination':<36} | {'N_z':>5} | {'perm':>5} | "
          f"{'tensor':>6} | {'dipole':>6} | {'total':>7} | {'evidence':<14} |")
    print(f"  |{'-'*4}|{'-'*38}|{'-'*7}|{'-'*7}|{'-'*8}|{'-'*8}|{'-'*9}|{'-'*16}|")
    for combo in combos:
        factors = combo.by_key
        print(f"  | {combo.combo_id:2} | {combo.name[:36]:<36} | "
              f"{factors['n_z'].multiplier:>5.1f} | "
              f"{factors['permutation'].multiplier:>5.1f} | "
              f"{factors['tensor'].multiplier:>6.1f} | "
              f"{factors['dipole'].multiplier:>6.1f} | "
              f"{combo.multiplier:>6.2f}x | "
              f"{combo.status_mark} {combo.weakest_status:<12} |")
    print()
    print("  evidence = the WEAKEST status among the factors this row actually raises:")
    for status, meaning in STATUS_LEGEND.items():
        print(f"    {ens.STATUS_MARK[status]} {status:<13} {meaning}")
    print()


def print_results_table(outcomes, spectra, targets, ranking) -> None:
    primary = next((s for s in spectra if s.role == "primary"), spectra[0])
    secondary = next((s for s in spectra if s.case_id != primary.case_id), None)
    best_id = ranking["closest_overall"]["combo_id"]
    per_target = ranking["closest_per_target"]
    target_by_key = {t.key: t for t in targets}

    print("  STEP C -- THE TEN COMBINATIONS AGAINST THE PUBLISHED SCALE")
    print(THIN)
    head = (f"  | {'ID':2} | {'combination':<34} | {'mult':>7} | "
            f"{'abrupt@1550':>11} | {'abrupt peak':>11} | {'graded peak':>11} | "
            f"{'RMS err':>8} |")
    print(head)
    print(f"  |{'-'*4}|{'-'*36}|{'-'*9}|{'-'*13}|{'-'*13}|{'-'*13}|{'-'*10}|")
    for outcome in outcomes:
        mark = " *" if outcome.combo.combo_id == best_id else "  "
        graded = (f"{outcome.value(secondary.case_id, 'peak'):>11.1f}"
                  if secondary else f"{'n/a':>11}")
        print(f"  | {outcome.combo.combo_id:2} | "
              f"{(outcome.combo.name[:32] + mark):<34} | "
              f"{outcome.combo.multiplier:>6.2f}x | "
              f"{outcome.value(primary.case_id, 'at_target_wavelength'):>11.1f} | "
              f"{outcome.value(primary.case_id, 'peak'):>11.1f} | "
              f"{graded} | "
              f"{outcome.aggregate_percent:>7.1f}% |")
    print()
    print(f"  Values are pm/V. '*' marks the smallest RMS error across all "
          f"{len(targets)} published numbers.")
    print(f"  Peaks sit at {primary.stored_peak_nm:.0f} nm ({primary.label})"
          + (f" and {secondary.stored_peak_nm:.0f} nm ({secondary.label})."
             if secondary else "."))
    print()

    print("  CLOSEST TO EACH PUBLISHED NUMBER")
    print(THIN)
    print(f"  | {'published target':<28} | {'value':>7} | {'combo':<26} | "
          f"{'got':>9} | {'error':>8} |")
    print(f"  |{'-'*30}|{'-'*9}|{'-'*28}|{'-'*11}|{'-'*10}|")
    for key, entry in per_target.items():
        target = target_by_key[key]
        print(f"  | {target.label[:28]:<28} | {target.value_pm_per_V:>7.0f} | "
              f"{(entry['combo_id'] + ' ' + entry['combo_name'])[:26]:<26} | "
              f"{entry['value_pm_per_V']:>9.1f} | "
              f"{entry['error_percent']:>7.1f}% |")
    print()

    best = ranking["closest_overall"]
    if ranking["targets_agree_on_a_single_combination"]:
        print(f"  All {len(targets)} published numbers pick the same combination: "
              f"{best['combo_id']} {best['combo_name']}.")
    else:
        winners = ", ".join(ranking["combinations_winning_at_least_one_target"])
        print(f"  The published numbers do NOT agree on one combination: "
              f"{winners} each win at least one.")
        print("  That disagreement is a result. It is reported rather than broken "
              "by a tie-break,")
        print("  because a scalar sweep cannot satisfy targets whose ratio it "
              "cannot change.")
    print()
    verdict = "INSIDE" if best["inside_threshold"] else "OUTSIDE"
    print(f"  CLOSEST OVERALL: Combo {best['combo_id']} {best['combo_name']} at "
          f"{best['multiplier']:.2f}x")
    print(f"    RMS error {best['aggregate_error_percent']:.1f} % -- {verdict} the "
          f"{ranking['match_threshold_percent']:.0f} % match threshold.")
    print(f"    Weakest factor it rests on: {best['weakest_active_status']} "
          f"({STATUS_LEGEND.get(best['weakest_active_status'], '')}).")
    print()


def print_shape_block(shape: dict) -> None:
    comparisons = shape.get("comparisons") or []
    if not comparisons:
        return
    print("  STEP D -- THE PART NO MULTIPLIER IN THIS ENSEMBLE CAN FIX")
    print(THIN)
    for line in _wrap(shape["why_it_matters"], 104):
        print(f"    {line}")
    print()
    print(f"    {'case':10}{'ours':>9}{'published':>12}{'mismatch':>11}"
          f"{'floor on both':>15}")
    for entry in comparisons:
        print(f"    {entry['case_id']:10}{entry['our_peak_over_1550']:>9.3f}"
              f"{entry['published_peak_over_1550']:>12.3f}"
              f"{entry['mismatch_percent']:>10.1f}%"
              f"{entry['best_possible_split_error_percent']:>14.1f}%")
    print()
    print("    'floor on both' is the error a PERFECTLY chosen scalar still leaves "
          "on each of the")
    print("    two quantities, having split the difference between them. No "
          "combination in this")
    print("    ensemble beats it, and no combination of pure scalars ever could.")
    print()


def print_epilogue(report: dict, ranking: dict) -> None:
    print(RULE)
    print("  WHAT THIS DEMO DOES AND DOES NOT SHOW")
    print(RULE)
    print("  It maps what each prefactor hypothesis WOULD imply across the "
          "spectrum. It does not")
    print("  identify the scale gap, and three specific things stop it from doing "
          "so:")
    print()
    print("    1. It resolves the PRODUCT of four factors, never the factors. "
          "Combos 07 and 08")
    print("       total 8.40x by different routes and produce identical spectra -- "
          "they are in the")
    print("       ensemble as a control on exactly this point.")
    print()
    print("    2. Combo 10's factors multiply to 27.72 against a measured residual "
          "of 27.63, so it")
    print("       was constructed from the answer. Landing on 2340 pm/V is "
          "arithmetic, the same")
    print("       arithmetic as Demo 17c's fitted K, and is not evidence.")
    print()
    print("    3. Of the four factors, only the baselines are 'established'. The "
          "2.8x tensor")
    print("       inversion has no source in this repository, and the 1.1x dipole "
          "tweak runs")
    print("       against Demo 17b's Kane measurement, which put r_e,hh at 0.96x, "
          "not 1.1x.")
    print()
    best = ranking["closest_overall"]
    print(f"  The honest reading: Combo {best['combo_id']} "
          f"({best['multiplier']:.2f}x) is closest at "
          f"{best['aggregate_error_percent']:.1f} % RMS, and it gets there while "
          "leaving")
    print("  the contradicted dipole tweak at 1.0x -- but it still rests on a "
          "speculative 2.8x.")
    print("  What survives independently of all of it is Demo 17's converged "
          "lineshape, and the")
    print("  shape mismatch in STEP D, which the whole ensemble is powerless "
          "against.")
    print(RULE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Demo 17d: compound ten declared prefactor estimation "
                     "combinations across the 1400-1800 nm spectrum and measure "
                     "each one against every published absolute value.")
    )
    parser.add_argument("--config", metavar="YAML")
    parser.add_argument("--results-dir", metavar="DIR",
                        help="Demo 17 hand-off or raw run tree")
    parser.add_argument("--targets-profile", default="paper", metavar="NAME",
                        help="'paper' (default) or 'demo17c' for the reading "
                             "Demo 17c anchored on")
    parser.add_argument("--cross-overlaps", choices=("zero", "fit_to_stored_anchors"),
                        help="how the rebuilt lineshape treats the two overlaps "
                             "Demo 17 did not record (affects the drawn curve "
                             "only, never a reported number)")
    parser.add_argument("--out", metavar="DIR", help="output directory")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config) if args.config else None)
    results_dir = audit17b.resolve_results_dir(
        Path(args.results_dir) if args.results_dir
        else (Path(cfg["source"]["results_dir"]) if cfg["source"].get("results_dir")
              else None)
    )

    print(RULE)
    print("  DEMO 17d -- PREFACTOR ESTIMATION ENSEMBLE SWEEP")
    print(RULE)
    print(f"  {cfg['experiment']['description'].strip()}")
    print()

    combos = ens.load_combos(cfg)
    targets, headline = ens.load_targets(cfg, args.targets_profile)
    spectra = [
        ens.load_case_spectrum(results_dir, case_cfg, cfg,
                               cross_overlap_model=args.cross_overlaps)
        for case_cfg in cfg["source"]["cases"]
    ]

    print_source_block(results_dir, spectra, args.targets_profile)
    print_matrix_block(combos)

    outcomes = ens.evaluate_ensemble(combos, spectra, targets, headline, cfg)
    ranking = ens.rank_ensemble(outcomes, targets, cfg)
    shape = ens.shape_versus_scale(spectra, targets)
    exclusions = ens.exclusion_report(combos, cfg["factors"])

    print_results_table(outcomes, spectra, targets, ranking)
    print_shape_block(shape)

    report = ens.build_report(
        outcomes, spectra, targets, headline, ranking, shape, exclusions,
        cfg, results_dir, args.targets_profile,
    )

    reporting = cfg["reporting"]
    out_dir = Path(args.out) if args.out else REPO_ROOT / reporting["output_subdir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = ens.write_summary_csv(
        out_dir / reporting["csv_filename"], outcomes, spectra, targets, headline,
        decimals=int(reporting.get("decimal_places", 2)),
    )
    json_path = out_dir / reporting["json_filename"]
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    plot_path = None
    if not args.no_plot:
        plot_path = ens.write_ensemble_figure(
            out_dir / reporting["plot_filename"], outcomes, spectra, targets, cfg
        )

    print("  ARTIFACTS")
    print(THIN)
    print(f"  CSV   : {csv_path}")
    print(f"  JSON  : {json_path}")
    print(f"  PLOT  : {plot_path if plot_path else 'skipped'}")
    print()

    print_epilogue(report, ranking)

    return 0 if ranking["closest_overall"]["inside_threshold"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
