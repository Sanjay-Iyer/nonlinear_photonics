"""Demo 16B command line: simple ACQW + linear grading validation.

    python run_demo16b.py --preflight                # solver-free self-test
    python run_demo16b.py --syntax                   # Level 1: render + --parse
    python run_demo16b.py --structure                # Level 2: realized x_Al(z)
    python run_demo16b.py --validate                 # Levels 1 + 2
    python run_demo16b.py --physics                  # Level 3: 3 licensed solves
    python run_demo16b.py --analyze-existing DIR     # re-read, no solver calls

No default launches a licensed solve; ``--physics`` is the only command that
runs the solver, and it refuses to solve a case whose structure has not been
verified first.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import uuid

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO11 = DEMO_DIR.parent / "11_paper_validation_interband_chi2_acqw"
DEMO14 = DEMO_DIR.parent / "14_absolute_chi2_graded_acqw_bo"
DEMO16 = DEMO_DIR.parent / "16_acqw_renderer_stress_validation"
for path in (str(SHARED), str(DEMO14), str(DEMO11), str(DEMO16), str(DEMO_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import cases16b  # noqa: E402
import demo14  # noqa: E402
import demo16b  # noqa: E402
import preflight16b  # noqa: E402
import runlog14  # noqa: E402

RULE = "=" * 78


def resolve_machine():
    """The same resolver Demo 14 and Demo 16 use. No demo-local path logic."""

    import demo_workflow as workflow

    return workflow.load_machine_config()


def results_root() -> Path:
    """``machine.results_root`` already ends in ``demo_runs``.

    Appending another one produced the ``demo_runs/demo_runs`` tree in the first
    Demo 14 gate. Demo 16B must not repeat it, and preflight checks that it has
    not.
    """

    return Path(resolve_machine().results_root)


def new_run_dir() -> tuple[Path, str]:
    facts = runlog14.git_facts(DEMO_DIR.parents[2])
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"demo16b_{stamp}_{facts['git_commit_short']}_{uuid.uuid4().hex[:6]}"
    root = results_root() / demo16b.DEMO_ID / run_id
    for sub in ("cases", "summaries", "plots"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root, run_id


def _machine_or_none():
    try:
        return resolve_machine()
    except Exception:  # noqa: BLE001 - absence is a reportable state, not a crash
        return None


def _environment(machine, exe, database, licence, run_id: str) -> dict:
    facts = runlog14.git_facts(DEMO_DIR.parents[2])
    return {
        "run_id": run_id,
        "timestamp_utc": runlog14.utc_now(),
        "demo_id": demo16b.DEMO_ID,
        "demo16b_version": demo16b.DEMO16B_VERSION,
        "git_commit": facts.get("git_commit"),
        "git_commit_short": facts.get("git_commit_short"),
        "git_dirty": facts.get("git_dirty"),
        "nextnano_executable": str(exe) if exe else None,
        "nextnano_database": str(database) if database else None,
        "nextnano_license": str(licence) if licence else None,
        "machine_config_source": str(getattr(machine, "source_path", "")) or None,
        "run_solver_enabled": bool(getattr(machine, "run_solver", False)),
        "demo14_config": str(demo14.DEMO_DIR / "demo.yaml"),
        "validation_cases": str(DEMO_DIR / cases16b.CASES_FILENAME),
    }


def _seed_run(root: Path, run_id: str, cfg, machine, exe, database, licence,
              mode: str) -> dict:
    """Write the inputs a reader needs before anything is executed."""

    import yaml

    environment = _environment(machine, exe, database, licence, run_id)
    environment["mode"] = mode
    runlog14.write_json_atomic(root / "RUN_STATUS.json", {
        **environment, "status": "running", "cases_total": 8,
    })
    runlog14.write_text_atomic(
        root / "resolved_config.yaml",
        yaml.safe_dump(runlog14.json_safe(dict(cfg)), sort_keys=False),
    )
    runlog14.write_text_atomic(
        root / cases16b.CASES_FILENAME,
        (DEMO_DIR / cases16b.CASES_FILENAME).read_text(encoding="utf-8"),
    )
    return environment


# ---------------------------------------------------------------------------
# Levels 1 and 2
# ---------------------------------------------------------------------------


def run_levels(*, do_structure: bool, only_parse: bool = False,
               verbose: bool = False, cases=None, mode: str = "validate"
               ) -> tuple[int, Path, list]:
    """Level 1 and, when asked, Level 2 over the fixed cases."""

    import preflight16

    cfg = demo14.load_config()
    cases = list(cases if cases is not None else
                 cases16b.load_cases(DEMO_DIR / cases16b.CASES_FILENAME))
    machine = _machine_or_none()
    exe = preflight16.parser_executable(machine)
    database = preflight16.database_for(exe) if exe else None
    licence = preflight16.license_for(machine)

    root, run_id = new_run_dir()
    environment = _seed_run(root, run_id, cfg, machine, exe, database, licence, mode)

    title = {
        "syntax": "LEVEL 1 -- PARSER VALIDATION",
        "structure": "LEVEL 2 -- STRUCTURE / Al COMPOSITION VALIDATION",
        "validate": "LEVELS 1 + 2 -- PARSER AND STRUCTURE VALIDATION",
    }.get(mode, mode.upper())
    print(RULE)
    print(f"  DEMO 16B  {title}")
    print(RULE)
    print(f"  RUN ID     : {run_id}")
    print(f"  RUN DIR    : {root}")
    print(f"  PARSER     : {exe or '<none found>'}")
    print(f"  DATABASE   : {database or '<none>'}")
    print(f"  LICENSE    : {licence or '<none needed>'}")
    print(f"  CASES      : {len(cases)}  (linear grading only)")
    if do_structure:
        print("  NOTE       : --structure builds the structure and quits; it does")
        print("               not solve. A production deck is ~440 grid points, so")
        print("               the free build (max 100) cannot run this level.")
    else:
        print("  NOTE       : --parse performs no physics and consumes no licence.")
    print(RULE)

    outcomes = []
    for case in cases:
        case_dir = root / "cases" / f"{case.case_id}_{case.name}"
        outcome = demo16b.run_case(
            cfg, case, case_dir, exe=exe, database=database,
            license_path=licence, do_structure=do_structure,
        )
        outcomes.append(outcome)
        _print_case_line(outcome, do_structure=do_structure, verbose=verbose)

    _write_plots(root, cfg, cases, outcomes)
    passed = _summarise(root, run_id, environment, outcomes,
                        do_structure=do_structure, mode=mode)
    return (0 if passed == len(cases) else 1), root, outcomes


_MARKS = {
    "parser_passed": "PARSE-OK",
    "structure_passed": "STRUCT-OK",
    "parser_failed": "PARSE-FAIL",
    "structure_failed": "STRUCT-FAIL",
    "render_failed": "RENDER-FAIL",
    "unsupported_geometry": "UNSUPPORTED",
    "intended_structure_failed": "INTENDED-FAIL",
    "parser_unavailable": "NO-PARSER",
}


def _print_case_line(outcome, *, do_structure: bool, verbose: bool) -> None:
    mark = _MARKS.get(outcome.status, outcome.status)
    peak = outcome.grading.get("realized_peak_al_fraction")
    line = (
        f"  [{mark:<13}] {outcome.case_id} {outcome.name:<22} "
        f"intended peak x_Al={peak:.4f}" if peak is not None else
        f"  [{mark:<13}] {outcome.case_id} {outcome.name:<22}"
    )
    comparison = (outcome.level2 or {}).get("comparison") or {}
    if comparison:
        line += (
            f"  max|dx|={comparison['max_absolute_al_fraction_error']:.2e}"
            f"  rms={comparison['rms_al_fraction_error']:.2e}"
        )
    print(line)
    if outcome.failure_reason and (verbose or "fail" in outcome.status
                                   or outcome.status == "unsupported_geometry"):
        print(f"                  {outcome.failure_reason}")


def _summarise(root: Path, run_id: str, environment: dict, outcomes, *,
               do_structure: bool, mode: str) -> int:
    good = {"structure_passed"} if do_structure else {"parser_passed", "structure_passed"}
    passed = sum(1 for o in outcomes if o.status in good)
    summary = {
        **environment,
        "level": 2 if do_structure else 1,
        "total_cases": len(outcomes),
        "passed": passed,
        "failed": len(outcomes) - passed,
        "cases": [o.as_record() for o in outcomes],
    }
    runlog14.write_json_atomic(
        root / "summaries" / ("level2_structure.json" if do_structure
                              else "level1_parser.json"), summary)
    _write_case_matrix(root / "summaries" / "case_matrix.csv", outcomes)
    runlog14.write_json_atomic(root / "RUN_STATUS.json", {
        **environment, "status": "completed", "mode": mode,
        "cases_total": len(outcomes), "cases_passed": passed,
        "cases_failed": len(outcomes) - passed,
    })
    _write_run_readme(root, environment, outcomes, do_structure=do_structure)

    print(RULE)
    print(f"  DEMO 16B {'LEVEL 2' if do_structure else 'LEVEL 1'}: "
          f"{passed}/{len(outcomes)} cases passed")
    for outcome in outcomes:
        if outcome.status not in good:
            print(f"    - {outcome.case_id}: {outcome.status}: {outcome.failure_reason}")
    print(RULE)
    print(f"  Results: {root}")
    return passed


def _write_case_matrix(path: Path, outcomes) -> None:
    header = (
        "case_id,name,status,render_method,graded_regions_disjoint,"
        "intended_peak_al,parser_passed,parser_return_code,"
        "max_abs_al_error,rms_al_error,realized_peak_al,"
        "well_1_nm,barrier_nm,well_2_nm,"
        "left_outer_barrier,right_outer_barrier,structure_passed\n"
    )
    lines = []
    for o in outcomes:
        c = (o.level2 or {}).get("comparison") or {}
        layers = c.get("realized_layer_widths_nm") or {}

        def fmt(value, spec: str = ".6f") -> str:
            return "" if value is None else format(value, spec)

        lines.append(",".join([
            o.case_id, o.name, o.status,
            str(o.grading_regions.get("render_method", "")),
            str(o.grading_regions.get("graded_regions_disjoint", "")),
            fmt(o.grading.get("realized_peak_al_fraction"), ".6f"),
            str(o.level1.get("passed", "")),
            str(o.level1.get("return_code", "")),
            fmt(c.get("max_absolute_al_fraction_error"), ".3e"),
            fmt(c.get("rms_al_fraction_error"), ".3e"),
            fmt(c.get("peak_realized_al_fraction"), ".6f"),
            fmt(layers.get("well_1_width_nm"), ".4f"),
            fmt(layers.get("central_barrier_width_nm"), ".4f"),
            fmt(layers.get("well_2_width_nm"), ".4f"),
            str(c.get("left_outer_barrier_present", "")),
            str(c.get("right_outer_barrier_present", "")),
            str((o.level2 or {}).get("passed", "")),
        ]) + "\n")
    runlog14.write_text_atomic(path, header + "".join(lines))


def _write_run_readme(root: Path, environment: dict, outcomes, *,
                      do_structure: bool) -> None:
    rows = ["| case | status | intended peak x_Al | parse | max abs dx_Al | RMS dx_Al |",
            "|---|---|---|---|---|---|"]
    for o in outcomes:
        c = (o.level2 or {}).get("comparison") or {}
        peak = o.grading.get("realized_peak_al_fraction")
        rows.append(
            f"| {o.case_id} {o.name} | {o.status} | "
            f"{'' if peak is None else format(peak, '.4f')} | "
            f"{o.level1.get('passed', '')} | "
            f"{format(c['max_absolute_al_fraction_error'], '.2e') if c else '-'} | "
            f"{format(c['rms_al_fraction_error'], '.2e') if c else '-'} |"
        )
    runlog14.write_text_atomic(root / "README_RUN.md", "\n".join([
        f"# Demo 16B run {environment['run_id']}",
        "",
        f"- mode: `{environment.get('mode')}`",
        f"- timestamp (UTC): {environment['timestamp_utc']}",
        f"- git commit: {environment.get('git_commit_short')} "
        f"(dirty: {environment.get('git_dirty')})",
        f"- nextnano++ executable: `{environment.get('nextnano_executable')}`",
        f"- database: `{environment.get('nextnano_database')}`",
        f"- level reached: {'2 (structure)' if do_structure else '1 (parser)'}",
        "",
        "Eight fixed cases, linear grading only, no optimization and no random draw.",
        "",
        *rows,
        "",
        "`cases/<case>/` holds the requested parameters, the intended profile, the",
        "generated deck, the parser transcript and -- when Level 2 ran -- the",
        "realized composition and its comparison metrics.",
        "",
    ]))


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def _write_plots(root: Path, cfg, cases, outcomes) -> None:
    import plots

    import plots16b

    if not plots.plotting_available():
        print(f"  NOTE: plotting unavailable ({plots.unavailable_reason()}); "
              "figures skipped, results unaffected.")
        return
    by_id = {o.case_id: o for o in outcomes}
    for case in cases:
        outcome = by_id.get(case.case_id)
        if outcome is None or outcome.status in ("render_failed",):
            continue
        try:
            _g, profile, _b, _d = demo16b.build_case(cfg, case)
        except Exception:  # noqa: BLE001 - a figure must never end a run
            continue
        realized_x = realized_y = None
        note = "nextnano++ realized profile not available (Level 2 not run)"
        comparison = (outcome.level2 or {}).get("comparison")
        table = (outcome.level2 or {}).get("alloy_composition_path")
        if comparison and table and Path(table).is_file():
            try:
                realized_x, realized_y = demo16b.read_alloy_composition(Path(table))
                note = (
                    f"max |dx_Al| = {comparison['max_absolute_al_fraction_error']:.2e}, "
                    f"RMS = {comparison['rms_al_fraction_error']:.2e}, "
                    f"{comparison['comparison_points']} points"
                )
            except Exception:  # noqa: BLE001
                realized_x = realized_y = None
        plots16b.composition_figure(
            root / "plots" / f"{case.case_id}_{case.name}_composition.png",
            title=(f"{case.case_id}  {case.name}  --  "
                   f"s={case.asymmetry_s:.2f}, b={case.nominal_central_barrier_thickness_nm:.2f} nm, "
                   f"linear 10-90 = {case.gaas_to_algaas_grading_width_10_90_nm:.2f} nm"),
            interfaces=profile.request["interfaces_nm"],
            intended_x_nm=profile.x_nm, intended_al=profile.al_fraction,
            realized_x_nm=realized_x, realized_al=realized_y,
            max_al_fraction=cases16b.AL_FRACTION, note=note,
        )


# ---------------------------------------------------------------------------
# Level 3
# ---------------------------------------------------------------------------


def run_physics(verbose: bool = False) -> int:
    """The three selected licensed solves, gated on Levels 1 and 2."""

    selected = [
        c for c in cases16b.load_cases(DEMO_DIR / cases16b.CASES_FILENAME)
        if c.physics
    ]
    if len(selected) != 3:
        print(f"Demo 16B solves exactly 3 cases; the case file selects {len(selected)}.")
        return 2

    machine = _machine_or_none()
    if machine is None or not getattr(machine, "run_solver", False):
        print(RULE)
        print("  DEMO 16B LEVEL 3 -- NOT RUN")
        print(RULE)
        print("  This machine does not resolve a runnable licensed nextnano++.")
        print("  Level 3 solves the real structure; there is nothing to fabricate")
        print("  in its place. Run --syntax here and --physics on the licensed")
        print("  work laptop.")
        print(RULE)
        return 3

    print(RULE)
    print("  DEMO 16B LEVEL 3 -- PHYSICS (LICENSED)")
    print(RULE)
    print("  Levels 1 and 2 run first for the three selected cases. A case whose")
    print("  structure nextnano++ did not build as requested is NOT solved.")
    print(RULE)

    status, root, outcomes = run_levels(
        do_structure=True, verbose=verbose, cases=selected, mode="physics",
    )
    cfg = demo14.load_config()
    by_id = {o.case_id: o for o in outcomes}

    records = []
    for case in selected:
        outcome = by_id[case.case_id]
        case_dir = root / "cases" / f"{case.case_id}_{case.name}"
        if outcome.status != "structure_passed":
            print(f"  [SKIPPED     ] {case.case_id} {case.name}: "
                  f"{outcome.status} -- not solved")
            records.append({
                "case_id": case.case_id, "physics_label": case.physics_label,
                "passed": False, "skipped": True,
                "failure_stage": "pre_physics_gate",
                "failure_reason": outcome.failure_reason,
            })
            continue
        print(f"  [SOLVING     ] {case.case_id} {case.name} "
              f"(physics case {case.physics_label}) ...")
        record = demo16b.solve_case(cfg, case, case_dir, machine=machine)
        records.append(record)
        _print_physics_line(case, record)
        outcome.level3 = record
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())

    _write_physics_plots(root, cfg, selected, records)
    solved = sum(1 for r in records if r.get("passed"))
    runlog14.write_json_atomic(root / "summaries" / "level3_physics.json", {
        "total_selected": len(selected), "passed": solved,
        "failed": len(selected) - solved, "cases": records,
    })
    _write_physics_table(root / "summaries" / "physics_states.csv", selected, records)

    print(RULE)
    print(f"  DEMO 16B LEVEL 3: {solved}/{len(selected)} cases solved and verified")
    for record in records:
        if not record.get("passed"):
            print(f"    - {record['case_id']}: {record.get('failure_stage')}: "
                  f"{record.get('failure_reason')}")
    print(RULE)
    print(f"  Results: {root}")
    return 0 if (solved == len(selected) and status == 0) else 1


def _print_physics_line(case, record) -> None:
    analysis = record.get("analysis") or {}
    if not analysis:
        print(f"  [SOLVE-FAIL  ] {case.case_id}: {record.get('failure_reason')}")
        return
    transitions = analysis.get("transitions", {})

    def fmt(value, spec=".5f"):
        return "n/a" if value is None else format(value, spec)

    print(
        f"  [{'PHYS-OK' if record.get('passed') else 'PHYS-FAIL':<13}] "
        f"{case.case_id} E1={fmt(analysis.get('E_e1_eV'))} "
        f"E2={fmt(analysis.get('E_e2_eV'))} "
        f"HH1={fmt(analysis.get('E_hh1_eV'))} "
        f"HH2={fmt(analysis.get('E_hh2_eV'))} "
        f"E1-HH1={fmt(transitions.get('transition_e1_hh1_eV'), '.4f')} eV "
        f"({fmt(transitions.get('transition_e1_hh1_one_photon_nm'), '.1f')} nm, "
        f"2-photon {fmt(transitions.get('transition_e1_hh1_two_photon_nm'), '.1f')} nm)"
    )


def _write_physics_table(path: Path, cases, records) -> None:
    header = (
        "case_id,physics_label,passed,solver_return_code,"
        "E1_eV,E2_eV,HH1_eV,HH2_eV,"
        "transition_e1_hh1_eV,transition_e1_hh1_one_photon_nm,"
        "transition_e1_hh1_two_photon_nm,transition_e2_hh2_eV,"
        "maximum_boundary_probability\n"
    )
    lines = []
    for case, record in zip(cases, records):
        a = record.get("analysis") or {}
        t = a.get("transitions", {})

        def fmt(value, spec=".8f"):
            return "" if value is None else format(value, spec)

        lines.append(",".join([
            case.case_id, case.physics_label, str(record.get("passed")),
            str((record.get("solver") or {}).get("solver_return_code", "")),
            fmt(a.get("E_e1_eV")), fmt(a.get("E_e2_eV")),
            fmt(a.get("E_hh1_eV")), fmt(a.get("E_hh2_eV")),
            fmt(t.get("transition_e1_hh1_eV")),
            fmt(t.get("transition_e1_hh1_one_photon_nm"), ".3f"),
            fmt(t.get("transition_e1_hh1_two_photon_nm"), ".3f"),
            fmt(t.get("transition_e2_hh2_eV")),
            fmt(a.get("maximum_boundary_probability"), ".3e"),
        ]) + "\n")
    runlog14.write_text_atomic(path, header + "".join(lines))


def _write_physics_plots(root: Path, cfg, cases, records) -> None:
    import numpy as np
    import outputs
    import plots
    import quantum1d

    import plots16b

    if not plots.plotting_available():
        return
    for case, record in zip(cases, records):
        if not record.get("analysis"):
            continue
        try:
            _g, profile, _b, _d = demo16b.build_case(cfg, case)
            parser_profile = outputs.load_profile(str(cfg["nextnano"]["parser_profile"]))
            raw = Path(record["raw_output_dir"])
            run = quantum1d.parse_one_band_run(
                raw, profile=parser_profile,
                region_name=str(cfg["nextnano"]["quantum_region_name"]),
                bandedge_columns=cfg["nextnano"]["bandedge_columns"],
            )
            hole = outputs.resolve_outputs(
                parser_profile, raw, ["energy_spectrum_hh", "probabilities_hh"],
                substitutions={"region": str(cfg["nextnano"]["quantum_region_name"])},
            )
            hole_energies = outputs.read_state_table(hole.one("energy_spectrum_hh"))[1]
            hole_densities = outputs.read_profile_table(hole.one("probabilities_hh"))[1]
            plots16b.physics_figure(
                root / "plots" / f"{case.case_id}_{case.name}_physics.png",
                title=f"{case.case_id}  {case.name}  --  physics case "
                      f"{case.physics_label}",
                interfaces=profile.request["interfaces_nm"],
                intended_x_nm=profile.x_nm, intended_al=profile.al_fraction,
                position_nm=run.position_nm, band_edges=run.band_edges,
                state_x_nm=run.state_position_nm,
                electron_energies_eV=np.asarray(run.energies_eV).tolist(),
                electron_densities=run.densities,
                hole_energies_eV=np.asarray(hole_energies).tolist(),
                hole_densities=hole_densities,
                max_al_fraction=cases16b.AL_FRACTION,
            )
        except Exception as exc:  # noqa: BLE001 - a figure must never end a run
            print(f"  NOTE: physics figure for {case.case_id} skipped: "
                  f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Re-analysis
# ---------------------------------------------------------------------------


def analyze_existing(run_dir: Path) -> int:
    """Re-read a finished run. Reads files; never calls nextnano++."""

    target = Path(run_dir)
    if not target.is_dir():
        print(f"No such run directory: {target}")
        return 1
    summaries = target / "summaries"
    found = [p for p in ("level2_structure.json", "level1_parser.json")
             if (summaries / p).is_file()]
    if not found:
        print(f"No Demo 16B summary under {summaries}")
        return 1
    payload = json.loads((summaries / found[0]).read_text(encoding="utf-8"))
    print(RULE)
    print(f"  DEMO 16B RE-ANALYSIS -- {payload.get('run_id')}  (no solver calls)")
    print(RULE)
    print(f"  source     : {summaries / found[0]}")
    print(f"  level      : {payload.get('level')}")
    print(f"  executable : {payload.get('nextnano_executable')}")
    print(f"  result     : {payload.get('passed')}/{payload.get('total_cases')} passed")
    print(RULE)
    for case in payload.get("cases", []):
        comparison = (case.get("level2_structure") or {}).get("comparison") or {}
        extra = ""
        if comparison:
            extra = (f"  max|dx|={comparison['max_absolute_al_fraction_error']:.2e}"
                     f"  rms={comparison['rms_al_fraction_error']:.2e}")
        print(f"  [{case['status']:<22}] {case['case_id']} {case['name']}{extra}")
        if case.get("failure_reason"):
            print(f"                          {case['failure_reason']}")
    physics = summaries / "level3_physics.json"
    if physics.is_file():
        record = json.loads(physics.read_text(encoding="utf-8"))
        print(RULE)
        print(f"  LEVEL 3: {record['passed']}/{record['total_selected']} solved")
        for entry in record["cases"]:
            analysis = entry.get("analysis") or {}
            transitions = analysis.get("transitions", {})
            print(f"    {entry['case_id']}: passed={entry.get('passed')} "
                  f"E1={analysis.get('E_e1_eV')} HH1={analysis.get('E_hh1_eV')} "
                  f"E1-HH1={transitions.get('transition_e1_hh1_eV')} eV")
    print(RULE)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_demo16b.py",
        description="Demo 16B: simple GaAs/AlGaAs ACQW + linear grading validation",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true",
                       help="solver-free self-test")
    group.add_argument("--syntax", action="store_true",
                       help="Level 1: render every case and run --parse")
    group.add_argument("--structure", action="store_true",
                       help="Level 2: realized Al composition (licensed build)")
    group.add_argument("--validate", action="store_true",
                       help="Levels 1 + 2")
    group.add_argument("--physics", action="store_true",
                       help="Level 3: the three selected licensed solves")
    group.add_argument("--analyze-existing", metavar="RUN_DIR",
                       dest="analyze_existing")
    group.add_argument("--write-cases", action="store_true",
                       help="regenerate validation_cases.yaml (deliberate act)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.write_cases:
        path = cases16b.write_cases_file(DEMO_DIR / cases16b.CASES_FILENAME)
        print(f"wrote {path}")
        return 0
    if args.preflight:
        return preflight16b.run_preflight(verbose=args.verbose)
    if args.syntax:
        return run_levels(do_structure=False, verbose=args.verbose, mode="syntax")[0]
    if args.structure:
        return run_levels(do_structure=True, verbose=args.verbose, mode="structure")[0]
    if args.validate:
        return run_levels(do_structure=True, verbose=args.verbose, mode="validate")[0]
    if args.physics:
        return run_physics(verbose=args.verbose)
    if args.analyze_existing:
        return analyze_existing(Path(args.analyze_existing))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
