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

``--solve`` (alias ``--licensed``)
    **Run the licensed experiment.** Solves the paper's ideal-abrupt structure at
    three outer AlGaAs widths on the authoritative machine configuration, applies
    the strict per-state bound gate, compares dipole convergence separately from
    energy convergence, walks the convention ladder on the newly solved
    wavefunctions and prints one final report. Licensed machine only.

``--converge RUN_DIRS...``
    The outer-domain convergence verdict across runs that already exist, for
    comparing solves this demo did not produce.

``--plan``
    Print what the licensed run will do before doing it.
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


def _print_bound_gate(bound: dict, indent: str = "    ") -> None:
    """Per-state bound verdict. An uncertified gate is never printed as a pass."""

    print(f"{indent}bound-state gate (strict; the paper uses bound states only)")
    if not bound.get("available"):
        print(f"{indent}  UNAVAILABLE: {bound.get('reason')}")
        print(f"{indent}  verdict: NOT CERTIFIED (absence of evidence is not a pass)")
        return
    print(f"{indent}  policy in producing run : {bound.get('policy_in_source_run')}"
          f"   required: {bound.get('policy_required')}")
    print(f"{indent}  {'state':<6}{'verdict':<12}{'E (eV)':>10}"
          f"{'P_boundary':>13}{'in Eq.2':>9}  criterion")
    for label in bound.get("required_states", []):
        row = (bound.get("by_state") or {}).get(label)
        if row is None:
            print(f"{indent}  {label:<6}{'MISSING':<12}{'-':>10}{'-':>13}{'-':>9}  "
                  "no record in the per-state table")
            continue
        energy = row.get("energy_eV")
        boundary = row.get("boundary_probability")
        detail = (row.get("bound_criterion_detail") or "")[:64]
        if not row.get("energy_half_of_test_applied"):
            detail = f"probability-only test; {detail}"
        # Pre-formatted so a missing value prints a dash instead of crashing the
        # report. A verdict printer that dies on incomplete data is the last
        # thing anyone wants when the data is incomplete because something failed.
        energy_text = "-" if energy is None else f"{float(energy):.4f}"
        boundary_text = "-" if boundary is None else f"{float(boundary):.3e}"
        window_text = str(row.get("within_chi2_state_window"))
        print(f"{indent}  {label:<6}{row['verdict']:<12}{energy_text:>10}"
              f"{boundary_text:>13}{window_text:>9}  {detail}")
    verdict = bound.get("passed")
    label = {True: "PASS", False: "FAIL"}.get(verdict, "NOT CERTIFIED")
    print(f"{indent}  verdict: {label} -- {bound.get('reason')}")


def _print_regression(check: dict, indent: str = "    ") -> None:
    print(f"{indent}regression against the validated ladder")
    for row in check["comparisons"]:
        if row["agrees"] is None:
            print(f"{indent}  {row['variant']:<24} expected {row['expected']:>8.2f}  "
                  "not present in this ladder")
            continue
        print(f"{indent}  {'OK  ' if row['agrees'] else 'DRIFT'} "
              f"{row['variant']:<24} expected {row['expected']:>8.2f}  "
              f"observed {row['observed']:>8.2f}  "
              f"rel {row['relative_difference']:.3e}")
    print(f"{indent}  all agree: {check['all_agree']}")
    if check["all_agree"] is False:
        print(f"{indent}  NOTE: {check['interpretation']}")


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

    _print_bound_gate(bound)

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

    regression = conv.check_ladder_regression(ladder["rows"])
    print()
    _print_regression(regression)
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
        "ladder_regression": regression,
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
# Licensed solves
# ---------------------------------------------------------------------------


def _print_domain(record: dict) -> None:
    marker = "  <- the paper's own period barrier" if record.get("is_paper_domain") else ""
    print(f"\n  --- outer AlGaAs {record['outer_barrier_nm']:g} nm{marker}")
    if not record.get("passed"):
        print(f"      FAILED at {record.get('failure_stage')}: "
              f"{record.get('failure_reason')}")
        if record.get("bound_state_gate"):
            _print_bound_gate(record["bound_state_gate"], indent="      ")
        return

    elements = record["matrix_elements"]
    print("      energies (eV) and separations")
    print(f"        E1  = {elements['E1_eV']:.6f}   E2  = {elements['E2_eV']:.6f}"
          f"   E2-E1   = {elements['E2_minus_E1_meV']:8.3f} meV")
    print(f"        HH1 = {elements['HH1_eV']:.6f}   HH2 = {elements['HH2_eV']:.6f}"
          f"   HH1-HH2 = {elements['HH1_minus_HH2_meV']:8.3f} meV")
    print(f"        E1-HH1 = {elements['transition_E1_HH1_eV']:.6f} eV     "
          f"E2-HH2 = {elements['transition_E2_HH2_eV']:.6f} eV")
    print("      overlaps <psi_e|psi_hh>")
    print(f"        e1-hh1 = {elements['overlap_e1_hh1']:+.6f}   "
          f"e1-hh2 = {elements['overlap_e1_hh2']:+.6f}")
    print(f"        e2-hh1 = {elements['overlap_e2_hh1']:+.6f}   "
          f"e2-hh2 = {elements['overlap_e2_hh2']:+.6f}")
    print("      position matrix elements <psi|z|psi> (nm)")
    print(f"        z_e1e1 = {elements['z_e1_e1_nm']:+.6f}  "
          f"z_e1e2 = {elements['z_e1_e2_nm']:+.6f}  "
          f"z_e2e2 = {elements['z_e2_e2_nm']:+.6f}")
    print(f"        z_h1h1 = {elements['z_hh1_hh1_nm']:+.6f}  "
          f"z_h1h2 = {elements['z_hh1_hh2_nm']:+.6f}  "
          f"z_h2h2 = {elements['z_hh2_hh2_nm']:+.6f}")
    print(f"        electron diagonal difference = "
          f"{elements['electron_diagonal_difference_nm']:+.6f} nm   "
          f"hole = {elements['hole_diagonal_difference_nm']:+.6f} nm")
    _print_bound_gate(record["bound_state_gate"], indent="      ")

    ladder = record["variant_ladder"]
    print("      variant ladder, chi2_xzx at 1550 nm (pm/V)")
    for row in ladder["rows"]:
        print(f"        {row['variant']:<24}{row['chi2_at_1550_pm_per_V']:>10.2f}"
              f"   promotable={'yes' if row['promotable'] else 'no'}")
    print(f"        production chi2.py value : "
          f"{record.get('production_chi2_at_1550_pm_per_V')}")
    regression = conv.check_ladder_regression(ladder["rows"])
    _print_regression(regression, indent="      ")


def run_solve(
    domains: list[float] | None, strict_abort: bool, verbose: bool
) -> tuple[int, dict]:
    """The licensed experiment: three domains, gates, ladder, final verdict."""

    import solve16f  # imported here; it pulls in the whole demo tree

    print(RULE)
    print("  DEMO 16F -- LICENSED SOLVES (paper ideal-abrupt ACQW)")
    print(RULE)
    print(f"  STRUCTURE : {conv.PAPER_THICK_WELL_NM:g} nm GaAs / "
          f"{conv.PAPER_TUNNEL_BARRIER_NM:g} nm Al{conv.PAPER_AL_FRACTION:g}GaAs / "
          f"{conv.PAPER_THIN_WELL_NM:g} nm GaAs, s = 0.42, abrupt")
    print(f"  DOMAINS   : "
          f"{', '.join(f'{w:g} nm' for w in (domains or demo16f.DOMAIN_SWEEP_NM))}")
    print(f"  TARGET    : {conv.PRIMARY_TARGET.value_pm_per_V:g} pm/V "
          f"({conv.PRIMARY_TARGET.source})")
    print("  SCALE     : none. Demo 16F fits nothing.")
    print(RULE)

    root, report = solve16f.run_solves(
        domains=domains, strict_abort=strict_abort, verbose=verbose,
    )
    for record in report["domains"]:
        _print_domain(record)

    convergence = report["domain_convergence"]
    print(f"\n{RULE}")
    print("  DOMAIN CONVERGENCE")
    print(RULE)
    for row in convergence.get("rows", []):
        print(f"    outer {row['outer_barrier_nm']:>6.2f} nm   "
              f"max |dE| = {row['max_energy_shift_meV']:8.4f} meV   "
              f"max relative d<z> = {row['max_dipole_relative_shift']:.3e}")
    print(f"\n    energies converged at the paper domain : "
          f"{convergence.get('paper_domain_energies_converged')}")
    print(f"    dipoles  converged at the paper domain : "
          f"{convergence.get('paper_domain_dipoles_converged')}")
    print(f"    CONVERGED                              : {convergence.get('converged')}")
    if convergence.get("diagnostic"):
        print(f"    DIAGNOSTIC: {convergence['diagnostic']}")

    print(f"\n{RULE}")
    print("  FINAL REPORT")
    print(RULE)
    print(f"    domains converged        : {convergence.get('converged')}")
    print(f"    bound-state verdicts     : {report['bound_state_verdicts']}")
    if report["non_bound_states"]:
        print(f"    NON-BOUND STATES         : {report['non_bound_states']}")
    else:
        print("    non-bound states         : none identified")
    if report["domains_without_a_certified_bound_gate"]:
        print(f"    NOT CERTIFIED            : "
              f"{report['domains_without_a_certified_bound_gate']}")
    best = report["best_physically_justified"]
    print(f"\n    best physically justified chi2_xzx(1550):")
    print(f"      value      : {best['chi2_at_1550_pm_per_V']} pm/V")
    print(f"      variant    : {best['variant']}")
    print(f"      conventions: {best['conventions']}")
    print(f"      bound gate : {best['certified_by_bound_gate']}")
    print(f"\n    paper target : {report['target']['value_pm_per_V']:g} pm/V "
          f"({report['target']['source']})")
    factor = report["remaining_factor_vs_target"]
    print(f"    REMAINING FACTOR VS TARGET : "
          f"{'n/a' if factor is None else format(factor, '.1f') + 'x'}")
    print("\n    unresolved published ambiguities (reported, NOT applied):")
    for item in report["unresolved_published_ambiguities"]:
        print(f"      {item['name']:<28} x{item['size']:g}  applied={item['applied']}")
    print(f"\n    {report['no_empirical_scaling_note']}")
    print(f"\n  RUN DIR: {root}")
    print(f"  REPORT : {root / 'summaries' / 'demo16f_report.json'}")
    print(RULE)

    solved = sum(bool(r.get("passed")) for r in report["domains"])
    certified = not report["domains_without_a_certified_bound_gate"]
    status = 0 if (solved == len(report["domains"]) and certified
                   and convergence.get("converged")) else 1
    return status, report


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def run_plan() -> int:
    structure = demo16f.PAPER_STRUCTURE.as_record()
    print(RULE)
    print("  DEMO 16F -- LICENSED WORK REQUIRED")
    print(RULE)
    print("\n  Demo 16F performs all of the following itself:")
    print("     python run_demo16f.py --solve")
    print("\n  A. Three licensed solves of one structure, at outer AlGaAs widths:")
    for width in demo16f.DOMAIN_SWEEP_NM:
        marker = "  <- the paper's own period barrier" if abs(
            width - conv.PAPER_PERIOD_BARRIER_NM
        ) < 1e-9 else ""
        print(f"         outer barrier {width:>5.1f} nm{marker}")
    print("     Each uses Demo 16E's renderer, parser gate, realized-composition")
    print("     gate, required-output gate and solver, unchanged.")
    print("\n  B. Strict per-state bound gate for E1, E2, HH1 and HH2. The verdict")
    print("     is fail_case: a non-bound state in the Eq. 2 sum is a failure, and")
    print("     a missing or untested state is NOT CERTIFIED, never a pass.")
    print("     Demo 11 itself runs under warn so envelopes.csv is written before")
    print("     any abort; --strict-abort switches it to fail_case instead.")
    print("\n  C. Convergence of the position matrix elements checked SEPARATELY")
    print("     from the eigenenergies, because absolute chi2 rides on <psi|z|psi>.")
    print("\n  D. The convention ladder on the newly solved wavefunctions, with")
    print("     well_density, gamma_to_x_2pi_over_a, and both radial and")
    print("     independent Cartesian k integration; then the regression check")
    print("     against the validated values:")
    for name, value in conv.LADDER_REGRESSION_PM_PER_V.items():
        print(f"         {name:<24}{value:>8.2f} pm/V")
    print("\n  E. Without a licensed machine, the ladder alone still runs from an")
    print("     existing Demo 16E run, with no new solve:")
    print("     python run_demo16f.py --from-run <16E_run_dir> --case case_02")
    print("\n  F. The structure this audit is about:")
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
    group.add_argument("--solve", "--licensed", dest="solve", action="store_true",
                       help="run the licensed nextnano++ domain sweep, gates, "
                            "ladder and final report (licensed machine only)")
    group.add_argument("--from-run", metavar="RUN_DIR",
                       help="walk the variant ladder using an existing run")
    group.add_argument("--converge", nargs="+", metavar="OUTER_NM=RUN_DIR",
                       help="outer-domain convergence across runs")
    group.add_argument("--plan", action="store_true",
                       help="print the licensed work still required")
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--domains", nargs="+", type=float, metavar="NM",
                        help="outer AlGaAs widths for --solve "
                             "(default 18.2 25 35)")
    parser.add_argument("--strict-abort", action="store_true",
                        help="run Demo 11 under quasi_bound_state_policy=fail_case "
                             "so a non-bound state aborts the case. Off by "
                             "default because the abort precedes envelopes.csv, "
                             "and 16F applies the same verdict either way")
    parser.add_argument("--output", metavar="JSON")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.solve:
        status, payload = run_solve(args.domains, args.strict_abort, args.verbose)
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(json.dumps(payload, indent=1),
                                         encoding="utf-8")
            print(f"  WROTE: {args.output}")
        return status
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
