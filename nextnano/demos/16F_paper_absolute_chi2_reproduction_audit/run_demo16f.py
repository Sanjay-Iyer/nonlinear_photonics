"""CLI for Demo 16F. No optimizer, no search, no free scale factor.

Four entry points, in the order they are meant to be used:

``--audit``
    The mathematics, with no solver and no licence. Checks that the two
    independent k-space implementations agree with each other and with the
    closed form, that the dimensional ledger closes on m/V, that Eq. 1 and Eq. 2
    are consistent, and that the tensor component is declared. Runs anywhere,
    including the home laptop.

``--from-run RUN_DIR``
    Walk the variant ladder using the envelopes an existing licensed run already
    wrote. **This needs no new solve**: a completed Demo 16E run directory
    already contains everything Eq. 2 needs for ``case_02``, so the variant table
    can be produced from work already done.

``--converge RUN_DIRS...``
    The outer-domain convergence verdict across runs at different outer barrier
    widths, checking the position matrix elements and not only the eigenvalues.

``--plan``
    Print the licensed work this audit still needs and the exact settings each
    piece requires. Emitted rather than executed so the overrides are reviewed
    before a solver runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys

DEMO_DIR = Path(__file__).resolve().parent
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

import conventions16f as conv  # noqa: E402
import demo16f  # noqa: E402
import eq16f  # noqa: E402
import kspace16f as kspace  # noqa: E402
import variants16f as variants  # noqa: E402

RULE = "=" * 78
DEFAULT_CASE = "case_02"


# ---------------------------------------------------------------------------
# Solver-free audit
# ---------------------------------------------------------------------------


def run_audit(verbose: bool = False) -> tuple[int, dict]:
    """Everything that can be settled with arithmetic alone."""

    faithful = conv.FAITHFUL
    legacy = conv.LEGACY

    k_legacy = kspace.k_normalisation_audit(legacy.k_max_per_nm)
    k_faithful = kspace.k_normalisation_audit(faithful.k_max_per_nm)
    equations = eq16f.equation_consistency(
        n_wells_per_metre=faithful.n_wells_per_metre,
        k_integral_per_nm2=kspace.analytic_disc_constant(faithful.k_max_per_nm),
    )
    ledger = kspace.dimensional_ledger(
        n_wells_per_metre=faithful.n_wells_per_metre,
        r_e_hh_nm=0.751,
        k_integral_per_nm2=kspace.analytic_disc_constant(faithful.k_max_per_nm),
        position_matrix_nm=1.0,
        denominator_product_eV2=1.0,
    )

    print(RULE)
    print("  DEMO 16F -- SOLVER-FREE REPRODUCTION AUDIT")
    print(RULE)
    print(f"  PAPER  : {conv.PAPER}")
    print(f"  TARGET : {conv.PRIMARY_TARGET.value_pm_per_V:g} pm/V at "
          f"{conv.PRIMARY_TARGET.wavelength_nm:g} nm ({conv.PRIMARY_TARGET.interfaces})")
    print(f"  TENSOR : {conv.TENSOR_QUANTITY}")
    print(RULE)

    print("\n  [1] k-space normalisation: two independent implementations")
    for label, report in (("legacy pi/a", k_legacy),
                          ("faithful 2pi/a", k_faithful)):
        print(f"    {label:<16} k_max = {report['k_max_per_nm']:.6f} /nm")
        for row in report["comparisons"]:
            status = "OK  " if row["agrees"] else "FAIL"
            print(f"      {status} {row['domain']:<7} {row['integrand']:<20} "
                  f"radial={row['radial']:.6e}  cartesian={row['cartesian']:.6e}  "
                  f"rel={row['relative_difference']:.2e}")
        print(f"      methods agree      : {report['all_methods_agree']}")
        print(f"      closed form matched: {report['closed_form_reproduced']}")
        print(f"      square/disc        : "
              f"{report['square_over_disc_area_ratio']:.6f} "
              f"(expected {report['square_over_disc_expected']:.6f})")

    print("\n  [2] dimensional ledger (faithful conventions, unit matrix elements)")
    for line in ledger.render().splitlines():
        print(f"      {line}")

    print("\n  [3] Eq. 1 vs Eq. 2")
    for row in equations["comparisons"]:
        flag = "  <- mixes tensor components" if row["mixes_tensor_components"] else ""
        print(f"      {row['permutation_set']:<28} terms={row['terms']}  "
              f"Eq1/Eq2 = {row['eq1_over_eq2']:.6f}{flag}")
    print(f"      sets reproducing Eq. 2: "
          f"{equations['permutation_sets_reproducing_eq2'] or 'none'}")
    print(f"      FINDING: {equations['finding']}")

    print("\n  [4] tensor component")
    print(f"      {conv.TENSOR_DECLARATION}")
    print(f"      must never be compared against: "
          f"{', '.join(conv.FORBIDDEN_TENSOR_COMPARISONS)}")

    print("\n  [5] held fixed (not tunable by this audit)")
    for name, reason in conv.HELD_FIXED.items():
        print(f"      {name:<32} {reason}")

    payload = {
        "demo_id": conv.DEMO_ID,
        "demo16f_version": conv.DEMO_VERSION,
        "paper": conv.PAPER,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "k_normalisation_legacy": k_legacy,
        "k_normalisation_faithful": k_faithful,
        "dimensional_ledger": ledger.as_record(),
        "equation_consistency": equations,
        "tensor_declaration": conv.TENSOR_DECLARATION,
        "held_fixed": dict(conv.HELD_FIXED),
    }
    passed = (
        k_legacy["all_methods_agree"] and k_legacy["closed_form_reproduced"]
        and k_faithful["all_methods_agree"] and k_faithful["closed_form_reproduced"]
        and ledger.closes_on()
    )
    payload["k_space_implementation_verified"] = bool(passed)
    payload["equations_consistent"] = bool(equations["resolved"])

    print(f"\n{RULE}")
    print(f"  k-space implementation verified : {payload['k_space_implementation_verified']}")
    print(f"  dimensional ledger closes       : {ledger.closes_on()}")
    print(f"  Eq. 1 / Eq. 2 resolved          : {payload['equations_consistent']}")
    print(RULE)
    return (0 if passed else 1), payload


# ---------------------------------------------------------------------------
# Variant ladder from an existing run
# ---------------------------------------------------------------------------


def _recorded_metrics(run_dir: Path, case_id: str) -> dict:
    """The producing run's own numbers for this case, for cross-checking."""

    summary = Path(run_dir) / "physics_summary.json"
    if summary.is_file():
        payload = json.loads(summary.read_text(encoding="utf-8"))
        for record in payload.get("cases", []):
            if record.get("case_id") == case_id:
                return (record.get("optical") or {}).get("production_metrics") or {}
    per_case = Path(run_dir) / "cases" / case_id / "physics" / "physics_result.json"
    if per_case.is_file():
        payload = json.loads(per_case.read_text(encoding="utf-8"))
        return (payload.get("optical") or {}).get("production_metrics") or {}
    raise demo16f.Demo16FError(
        f"no recorded metrics for {case_id} under {run_dir}; expected "
        "physics_summary.json or cases/<case>/physics/physics_result.json"
    )


def _parsed_dir(run_dir: Path, case_id: str) -> Path:
    candidate = Path(run_dir) / "cases" / case_id / "physics" / "optical" / "parsed"
    if candidate.is_dir():
        return candidate
    raise demo16f.Demo16FError(
        f"no parsed optical directory at {candidate}. The variant ladder needs "
        "the envelopes.csv that Demo 11's analyse_case writes."
    )


def run_from_run(run_dir: Path, case_id: str, output: Path | None) -> tuple[int, dict]:
    run_dir = Path(run_dir).resolve()
    parsed = _parsed_dir(run_dir, case_id)
    recorded = _recorded_metrics(run_dir, case_id)

    states, diagnostics = demo16f.state_set_from_run(
        parsed,
        electron_energies_eV=recorded["electron_energies_eV"],
        hole_energies_eV=recorded["heavy_hole_energies_eV"],
    )
    cross_check = demo16f.cross_check_recorded(diagnostics, recorded)
    bound = demo16f.bound_state_gate(parsed)
    ladder = variants.evaluate_ladder(states)

    print(RULE)
    print(f"  DEMO 16F -- VARIANT LADDER from {run_dir.name} / {case_id}")
    print(RULE)
    print(f"  STRUCTURE : {demo16f.PAPER_STRUCTURE.thick_well_nm:g} / "
          f"{demo16f.PAPER_STRUCTURE.tunnel_barrier_nm:g} / "
          f"{demo16f.PAPER_STRUCTURE.thin_well_nm:g} nm, "
          f"{demo16f.PAPER_STRUCTURE.interfaces}")
    print(f"  TARGET    : {conv.PRIMARY_TARGET.value_pm_per_V:g} pm/V "
          f"({conv.PRIMARY_TARGET.source})")
    print(RULE)

    print("\n  matrix elements vs the producing run")
    for row in cross_check["comparisons"]:
        if row["agrees"] is None:
            print(f"    {row['quantity']:<16} ours={row['ours']:+.6f}  "
                  f"recorded=<not persisted>")
            continue
        print(f"    {'OK  ' if row['agrees'] else 'DIFF'} {row['quantity']:<16} "
              f"ours={row['ours']:+.6f}  recorded={row['recorded']:+.6f}  "
              f"rel={row['relative_difference']:.2e}")
    print(f"    independent recomputation agrees: {cross_check['all_agree']}")

    print("\n  bound-state gate (strict; the paper uses bound states only)")
    if not bound["available"]:
        print(f"    UNAVAILABLE: {bound['reason']}")
    else:
        print(f"    policy in producing run : {bound['policy_in_source_run']}")
        print(f"    states in the chi2 sum  : {bound['states_in_chi2_sum']}")
        for row in bound["failing_states"]:
            print(f"    FAILING {row['state']}: boundary probability "
                  f"{row['boundary_probability']} (left {row['left_boundary_probability']}, "
                  f"right {row['right_boundary_probability']}) -- {row['reason']}")
        print(f"    gate passed             : {bound['passed']}")

    print("\n  variant ladder, chi2_xzx at 1550 nm")
    header = (f"    {'variant':<24}{'N_z':<12}{'zone':<24}{'domain':<8}"
              f"{'method':<11}{'chi2':>10}{'x prev':>9}{'x legacy':>10}  promotable")
    print(header)
    print("    " + "-" * (len(header) - 4))
    for row in ladder["rows"]:
        previous = row["factor_vs_previous"]
        legacy = row["factor_vs_legacy"]
        print(f"    {row['variant']:<24}{row['nz_definition']:<12}"
              f"{row['zone_edge']:<24}{row['k_domain']:<8}{row['k_method']:<11}"
              f"{row['chi2_at_1550_pm_per_V']:>10.2f}"
              f"{'-' if previous is None else format(previous, '>9.3f')}"
              f"{'-' if legacy is None else format(legacy, '>10.3f')}"
              f"  {'yes' if row['promotable'] else 'no'}")

    best = ladder["best_promotable_pm_per_V"]
    print(f"\n    independent k implementations agree: "
          f"{ladder['independent_implementations_agree']} "
          f"(ratio {ladder['independent_implementation_ratio']})")
    if best:
        print(f"    best promotable value             : {best:.2f} pm/V")
        print(f"    remaining shortfall vs {conv.PRIMARY_TARGET.value_pm_per_V:g} pm/V : "
              f"{conv.PRIMARY_TARGET.value_pm_per_V / best:.1f}x")
    print(RULE)

    payload = {
        "demo_id": conv.DEMO_ID,
        "demo16f_version": conv.DEMO_VERSION,
        "source_run": str(run_dir),
        "case_id": case_id,
        "structure": demo16f.PAPER_STRUCTURE.as_record(),
        "state_diagnostics": diagnostics,
        "matrix_element_cross_check": cross_check,
        "bound_state_gate": bound,
        "variant_ladder": ladder,
        "optimization_performed": False,
    }
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"  WROTE: {output}")
    status = 0 if (cross_check["all_agree"] and bound.get("passed")) else 1
    return status, payload


# ---------------------------------------------------------------------------
# Domain convergence across runs
# ---------------------------------------------------------------------------


def run_converge(run_dirs: list[str], case_id: str) -> tuple[int, dict]:
    entries = []
    for spec in run_dirs:
        if "=" not in spec:
            raise SystemExit(
                f"--converge takes OUTER_NM=RUN_DIR pairs; got {spec!r}"
            )
        width, _, path = spec.partition("=")
        parsed = _parsed_dir(Path(path), case_id)
        recorded = _recorded_metrics(Path(path), case_id)
        states, _ = demo16f.state_set_from_run(
            parsed,
            electron_energies_eV=recorded["electron_energies_eV"],
            hole_energies_eV=recorded["heavy_hole_energies_eV"],
        )
        entries.append({"outer_barrier_nm": float(width), "states": states,
                        "run_dir": str(path)})
    report = demo16f.domain_convergence(entries)
    print(RULE)
    print("  DEMO 16F -- OUTER-DOMAIN CONVERGENCE")
    print(RULE)
    for row in report["rows"]:
        print(f"  outer {row['outer_barrier_nm']:>6.2f} nm   "
              f"max |dE| = {row['max_energy_shift_meV']:.3f} meV   "
              f"max relative d<z> = {row['max_dipole_relative_shift']:.3e}")
    print(f"\n  energies converged at the paper domain : "
          f"{report['paper_domain_energies_converged']}")
    print(f"  dipoles  converged at the paper domain : "
          f"{report['paper_domain_dipoles_converged']}")
    if report.get("diagnostic"):
        print(f"  DIAGNOSTIC: {report['diagnostic']}")
    print(RULE)
    return (0 if report.get("converged") else 1), report


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def run_plan() -> int:
    structure = demo16f.PAPER_STRUCTURE.as_record()
    print(RULE)
    print("  DEMO 16F -- LICENSED WORK REQUIRED")
    print(RULE)
    print("\n  A. Variant ladder -- NEEDS NO NEW SOLVE.")
    print("     A completed Demo 16E run already contains case_02's envelopes.")
    print("     python run_demo16f.py --from-run <16E_run_dir> --case case_02")
    print("\n  B. Strict bound-state diagnosis. Demo 16E ran with")
    print("     quasi_bound_state_policy: warn and every case reported")
    print("     physical_qc_valid = False with one state in the chi2 sum failing.")
    print("     Re-run the producing demo with, in its demo.yaml validation block:")
    print("         quasi_bound_state_policy: fail_case")
    print("     so the run stops on the failing state instead of recording it, and")
    print("     the per-state quasi_bound_states.json names which state and why.")
    print("\n  C. Outer-domain convergence. Solve the same structure at three")
    print("     outer AlGaAs widths and compare position matrix elements, not")
    print("     only eigenvalues:")
    for width in demo16f.DOMAIN_SWEEP_NM:
        marker = "  <- the paper's own period barrier" if abs(
            width - conv.PAPER_PERIOD_BARRIER_NM
        ) < 1e-9 else ""
        print(f"         outer barrier {width:>5.1f} nm{marker}")
    print("     then:")
    print("     python run_demo16f.py --converge 18.2=<run1> 25=<run2> 35=<run3>")
    print("\n  D. The structure this audit is about:")
    for key in ("thick_well_nm", "tunnel_barrier_nm", "thin_well_nm",
                "period_barrier_nm", "period_nm", "asymmetry_s", "interfaces"):
        print(f"         {key:<20} {structure[key]}")
    print(f"\n  TARGETS (all at 1550 nm, all quoted in words by the paper):")
    for target in conv.TARGETS:
        print(f"         {target.name:<16} {target.value_pm_per_V:>7.0f} pm/V   "
              f"{target.interfaces}")
    print(RULE)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Demo 16F: absolute chi2 reproduction audit against "
            "arXiv:2602.23246. One structure, no optimization, no free scale."
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--audit", action="store_true",
                       help="solver-free mathematics; runs anywhere")
    group.add_argument("--from-run", metavar="RUN_DIR",
                       help="walk the variant ladder using an existing run")
    group.add_argument("--converge", nargs="+", metavar="OUTER_NM=RUN_DIR",
                       help="outer-domain convergence across runs")
    group.add_argument("--plan", action="store_true",
                       help="print the licensed work still required")
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--output", metavar="JSON")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.from_run:
        status, payload = run_from_run(Path(args.from_run), args.case,
                                       Path(args.output) if args.output else None)
        return status
    if args.converge:
        status, _ = run_converge(list(args.converge), args.case)
        return status
    if args.plan:
        return run_plan()
    status, payload = run_audit(verbose=args.verbose)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"  WROTE: {args.output}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
