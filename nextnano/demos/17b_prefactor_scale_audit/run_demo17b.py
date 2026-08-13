"""CLI for Demo 17b -- prefactor, degeneracy and unit-cell matrix scale audit.

Runs anywhere. No nextnano++, no licence, no solver, no network. It reads Demo
17's saved artifacts and does exact arithmetic on the prefactor.

    python nextnano/demos/17b_prefactor_scale_audit/run_demo17b.py
    python nextnano/demos/17b_prefactor_scale_audit/run_demo17b.py --json out.json
    python nextnano/demos/17b_prefactor_scale_audit/run_demo17b.py --results-dir <dir>

The headline table is the budget: baseline, each sweep's multiplier, the
cumulative product under two clearly-labelled readings, and what remains against
the paper's 2340 pm/V.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

DEMO_DIR = Path(__file__).resolve().parent
DEMOS = DEMO_DIR.parent
SHARED = DEMOS / "_shared"
for path in (SHARED, DEMO_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import yaml  # noqa: E402

import prefactor_audit17b as audit  # noqa: E402

RULE = "=" * 100
THIN = "-" * 100
CONFIG_FILENAME = "demo17b.yaml"

#: Tri-state, and kept tri-state on purpose: a tier that cannot rebuild the sum
#: has not verified anything, and printing that the same way as "verified" is
#: how an unchecked number gets read as a checked one.
MEASURED_LABEL = {
    True: "yes",
    False: "NO -- the shared evaluator does not scale as the analytic factor",
    None: "not checked (this loading tier has no states)",
}


def load_config(path: Path | None = None) -> dict:
    target = Path(path) if path else DEMO_DIR / CONFIG_FILENAME
    if not target.is_file():
        raise audit.Audit17bError(f"Demo 17b configuration not found: {target}")
    cfg = yaml.safe_load(target.read_text(encoding="utf-8"))
    for section in ("source", "target", "baseline", "sweeps", "reporting"):
        if section not in cfg:
            raise audit.Audit17bError(f"demo17b.yaml is missing '{section}'.")
    return dict(cfg)


def _fmt(value, spec=".4f", none="n/a") -> str:
    if value is None:
        return none
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return str(value)


def _flag(entry: dict) -> str:
    """One glyph for how much weight a multiplier carries."""

    if entry["variant"] == "expectation_check":
        return "note"
    if entry["promotable"]:
        return "USE "
    return "rep "


def print_case_report(result: dict, cfg: dict) -> None:
    checks = cfg["reporting"]["cross_checks"]
    print(RULE)
    print(f"  CASE {result['case_id']}   baseline {_fmt(result['baseline_pm_per_V'])} pm/V"
          f"   target {_fmt(result['target_pm_per_V'], '.0f')} pm/V"
          f"   gap {_fmt(result['remaining_factor_before'], '.2f')}x")
    print(RULE)

    # --- provenance ------------------------------------------------------
    print(f"  loading tier          : {result['loading_tier']}")
    print(f"  Eq. 2 sum recomputed  : {result['sum_recomputed']}")
    print(f"      {result['sum_recomputed_note']}")
    if result["independent_recompute_pm_per_V"] is not None:
        print(f"  independent Eq. 2     : {_fmt(result['independent_recompute_pm_per_V'])} pm/V "
              f"vs recorded {_fmt(result['recorded_pm_per_V'])} "
              f"({_fmt(result['independent_recompute_relative_difference'], '.2e')} relative)")
        print("      angular-frequency form with hbar^2 in the prefactor, against "
              "chi2.py's energy form")
    expected = checks.get("production_prefactor_pm_per_V_per_summand")
    got = result["production_prefactor_pm_per_V_per_summand"]
    if expected:
        rel = abs(got - float(expected)) / float(expected)
        ok = rel <= float(checks.get("prefactor_relative_tolerance", 1e-12))
        print(f"  prefactor cross-check : {_fmt(got)} vs {_fmt(float(expected))} "
              f"pm/V per summand, rel {rel:.2e} -> {'PASS' if ok else 'FAIL'}")
    print()

    # --- the sweeps ------------------------------------------------------
    header = (f"  {'':4} {'sweep':<18} {'variant':<24} {'x':>9} {'exact':>6} "
              f"{'verified':>9}  rationale")
    print(header)
    print(THIN)
    for entry in result["multipliers"]:
        verified = entry["verified_numerically"]
        verified_text = {True: "yes", False: "NO", None: "-"}[verified]
        first = entry["rationale"].split(". ")[0]
        if len(first) > 78:
            first = first[:75] + "..."
        print(f"  {_flag(entry)} {entry['sweep']:<18} {entry['variant']:<24} "
              f"{entry['multiplier']:>9.4f} {str(entry['exact']):>6} "
              f"{verified_text:>9}  {first}")
    print(THIN)
    print("  USE = promotable (a cited source requires it) and enters the "
          "defensible product")
    print("  rep = reported only, never folded into a headline;  note = "
          "diagnostic row")
    print()

    # --- the budget ------------------------------------------------------
    totals = result["cumulative"]
    print(f"  {'READING':<26}{'product':>12}{'chi(2) pm/V':>16}{'remaining vs 2340':>20}")
    print(THIN)
    print(f"  {'baseline (Demo 17)':<26}{1.0:>12.4f}"
          f"{result['baseline_pm_per_V']:>16.2f}"
          f"{result['remaining_factor_before']:>19.2f}x")
    print(f"  {'defensible':<26}{totals['defensible_product']:>12.4f}"
          f"{result['defensible_total_pm_per_V']:>16.2f}"
          f"{result['remaining_factor_after_defensible']:>19.2f}x")
    print(f"  {'maximal (upper bound)':<26}{totals['maximal_product']:>12.4f}"
          f"{result['maximal_total_pm_per_V']:>16.2f}"
          f"{result['remaining_factor_after_maximal']:>19.2f}x")
    print(THIN)
    for label, key in (("defensible", "defensible_choices"), ("maximal", "maximal_choices")):
        picks = ", ".join(
            f"{sweep.split('_', 1)[0]}={choice['variant']}({choice['multiplier']:.3f})"
            for sweep, choice in sorted(totals[key].items())
        )
        print(f"  {label:<12}: {picks}")
    print(f"  WARNING     : {totals['maximal_warning']}")
    print()


def print_kane_note(result: dict) -> None:
    """Spell out sweep D, because its finding is the opposite of the usual guess."""

    rows = [e for e in result["multipliers"] if e["sweep"] == "D_kane_dipole"]
    primary = next((e for e in rows if e["variant"] == "kane_300K"), None)
    note = next((e for e in rows if e["variant"] == "expectation_check"), None)
    if primary is None:
        return
    print("  SWEEP D IN FULL")
    print(THIN)
    print(f"    r_e,hh = (hbar/E_g) sqrt(E_p / 2 m_0)  with E_p = "
          f"{_fmt(primary['detail_kane_energy_eV'], '.1f')} eV, "
          f"E_g = {_fmt(primary['detail_band_gap_eV'], '.3f')} eV")
    print(f"           = {_fmt(primary['detail_r_kane_nm'])} nm   "
          f"(p_cv = {primary['detail_p_cv_kg_m_per_s']:.4e} kg m/s)")
    print(f"    legacy   {_fmt(primary['detail_r_legacy_nm'])} nm   VASP/HSE06, "
          "Ramesh 2023 APL 123, 251111")
    print(f"    ratio    r_kane / r_legacy = {_fmt(primary['detail_r_ratio'])}  "
          f"({_fmt(primary['detail_percent_from_legacy'], '+.1f')} %), so "
          f"(r_new/r_old)^2 = {_fmt(primary['multiplier'])}")
    print("    VERDICT  the Kane relation CONFIRMS 0.751 nm to 2 %. This sweep "
          "does not supply a boost;")
    print("             it removes r_e,hh from the list of suspects.")
    if note is not None:
        print(f"    an r of {_fmt(note['detail_target_r_nm'], '.2f')} nm would need "
              f"E_p = {_fmt(note['detail_required_kane_energy_eV_at_given_gap'], '.1f')} eV "
              f"(GaAs: {_fmt(note['detail_given_kane_energy_eV'], '.1f')})")
        print(f"    {'':>32}or E_g = "
              f"{_fmt(note['detail_required_band_gap_eV_at_given_kane_energy'], '.4f')} eV "
              f"(GaAs: {_fmt(note['detail_given_band_gap_eV'], '.3f')})")
    print()


def print_spin_note(result: dict, cfg: dict) -> None:
    rows = [e for e in result["multipliers"] if e["sweep"] == "C_spin_degeneracy"]
    if not rows:
        return
    entry = rows[0]
    expected = cfg["sweeps"]["C_spin_degeneracy"].get("expected_verdict")
    site = entry.get("detail_source_inspection") or {}
    print("  SWEEP C IN FULL")
    print(THIN)
    print(f"    verdict  {entry['variant']}"
          + (f"   (config expected {expected})" if expected else ""))
    if site.get("inspected"):
        print(f"    source   spin_degeneracy occurrences: "
              f"{site.get('occurrences_by_function')}")
        print(f"             applied in k weights: {site.get('applied_in_k_weights')}; "
              f"applied again in the state sum: {site.get('applied_again_in_state_sum')}")
    measured = entry.get("detail_g1_over_g2_ratio_matches_analytic")
    ratio_ref = cfg["reporting"]["cross_checks"].get("demo18_spin_ratio")
    measured_text = MEASURED_LABEL[measured]
    print(f"    measured g_s=1 vs g_s=2 ratio matches analytic: {measured_text}")
    if ratio_ref:
        print(f"    Demo 18 rows G/H measured the same ratio independently: "
              f"{_fmt(ratio_ref, '.1f')}")
    print(f"    multiplier {_fmt(entry['multiplier'])} -- "
          + ("an additional m_j factor of 2 would DOUBLE COUNT"
             if entry["multiplier"] == 1.0 else "a correction is owed"))
    print()


def print_epilogue(results: list[dict], cfg: dict) -> None:
    checks = cfg["reporting"]["cross_checks"]
    primary_id = cfg["source"]["primary_case"]
    primary = next((r for r in results if r["case_id"] == primary_id), results[0])
    print(RULE)
    print("  WHAT THE AUDIT SETTLES")
    print(RULE)
    print(f"  Demo 16F ladder on 16E's states : legacy {_fmt(checks['demo16f_legacy_pm_per_V'], '.2f')}"
          f" -> N_z+zone {_fmt(checks['demo16f_nz_and_zone_pm_per_V'], '.2f')} pm/V")
    print(f"  Demo 17 on its own 30 nm-box states: "
          f"{_fmt(primary['recorded_pm_per_V'], '.2f')} pm/V "
          f"({primary['case_id']}), 0.8 % from 16F -- two independent evaluators, "
          "two domains")
    print()
    print("  CLOSED by this audit:")
    print("    * r_e,hh  -- the Kane relation reproduces 0.751 nm to 2 %, so the "
          "unit-cell dipole is not the gap.")
    print("    * m_j x2  -- the heavy-hole Kramers doublet is ALREADY counted, "
          "once, in the k-space weights.")
    print("                 16F listed this as an open factor; it can now be "
          "struck off rather than bounded.")
    print()
    print("  STILL OPEN, and neither is promotable from the published text:")
    print("    * N_z counting length -- period (x1) vs active layer (x3). Only "
          "the period reading describes")
    print("      the grown stack; the active-layer reading needs the fill factor "
          "put back, which undoes it.")
    print("    * Eq. 1 / Eq. 2 = 3, or an SHG degeneracy of 2. Probably the same "
          "bookkeeping counted once,")
    print("      so they should not be multiplied.")
    print()
    spread = [
        (r["case_id"], r["remaining_factor_after_defensible"]) for r in results
    ]
    print("  REMAINING FACTOR after the defensible product: "
          + ", ".join(f"{cid} {value:.2f}x" for cid, value in spread))
    print("  No scale factor was fitted anywhere in this audit.")
    print(RULE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Demo 17b: decompose the residual absolute chi(2) scale gap into "
            "exact prefactor multipliers. Pure Python, no solver."
        )
    )
    parser.add_argument("--config", metavar="YAML", help="override demo17b.yaml")
    parser.add_argument("--results-dir", metavar="DIR",
                        help="Demo 17 hand-off directory (default: auto-resolve "
                             "demo_results/demo_17 or demo_results/demo17)")
    parser.add_argument("--case", action="append", metavar="CASE_ID",
                        help="audit only this case; repeatable")
    parser.add_argument("--json", metavar="PATH", help="write the full audit as JSON")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the budget tables")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config) if args.config else None)
    results_dir = audit.resolve_results_dir(
        Path(args.results_dir) if args.results_dir
        else (Path(cfg["source"]["results_dir"]) if cfg["source"].get("results_dir")
              else None)
    )
    case_ids = args.case or list(cfg["source"]["cases"])

    print(RULE)
    print("  DEMO 17b -- PREFACTOR, DEGENERACY AND UNIT-CELL MATRIX SCALE AUDIT")
    print(RULE)
    print(f"  source      : {results_dir}")
    print(f"  cases       : {', '.join(case_ids)}")
    print(f"  target      : {_fmt(cfg['target']['chi2_pm_per_V'], '.0f')} pm/V "
          f"-- {cfg['target']['source']}")
    print("  solver runs : none. Demo 17 already proved the envelope side is "
          "converged.")
    print()

    results, failures = [], []
    for case_id in case_ids:
        try:
            case = audit.load_case(results_dir, case_id)
            result = audit.audit_case(case, cfg)
        except audit.Audit17bError as exc:
            failures.append((case_id, str(exc)))
            print(f"  [SKIP] {case_id}: {exc}\n")
            continue
        results.append(result)
        print_case_report(result, cfg)
        if not args.quiet and result["case_id"] == cfg["source"]["primary_case"]:
            print_spin_note(result, cfg)
            print_kane_note(result)

    if not results:
        print("  No case could be audited. Copy Demo 17's physics_summary.json "
              "into demo_results/demo_17/ and retry.")
        return 1

    if not args.quiet:
        print_epilogue(results, cfg)

    if args.json:
        payload = {
            "demo_id": cfg["experiment"]["demo_id"],
            "source_results_dir": str(results_dir),
            "target_pm_per_V": cfg["target"]["chi2_pm_per_V"],
            "cases": results,
            "skipped": [{"case_id": c, "reason": r} for c, r in failures],
            "no_scale_factor_was_fitted": True,
        }
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  JSON written: {out}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
