"""CLI for Demo 16G. Six modes, kept separate so one failure is debuggable.

``--plan``             what will run, and every resolved path, without a solver
``--nnp-comparison``   Group 1 only: the two supplied .nnp files
``--paper-benchmark``  Group 3 only: the paper's ideal-abrupt structure
``--sweep``            Group 2 only: the 20 generated structures
``--analyze``          rebuild every summary and plot from completed results
``--all``              all three groups then the analysis, in one go

The three solve modes are separate on purpose: if the ``.nnp`` comparison fails
on the work laptop it can be debugged without launching twenty more licensed
solves behind it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import uuid

DEMO_DIR = Path(__file__).resolve().parent
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

import cases16g  # noqa: E402
import deck16g  # noqa: E402
import demo16g  # noqa: E402
import grading16g  # noqa: E402
import nnp16g  # noqa: E402
import plots16g  # noqa: E402
import report16g  # noqa: E402
import runners16g  # noqa: E402

RULE = "=" * 78
REPOSITORY_ROOT = DEMO_DIR.parents[2]


def _run_dir(cfg: dict, machine=None, existing: Path | None = None) -> Path:
    """A fresh run directory under the machine's short results root."""

    if existing:
        return Path(existing)
    root = Path(getattr(machine, "results_root", "") or "") if machine else Path()
    if not str(root):
        root = REPOSITORY_ROOT / "nextnano" / "results" / "demo_runs"
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(root) / cfg["demo_id"] / f"demo16g_{stamp}_{uuid.uuid4().hex[:6]}"
    for sub in ("cases", "summaries", "plots"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    return path


def _latest_run(cfg: dict, machine=None) -> Path:
    root = Path(getattr(machine, "results_root", "") or "") if machine else Path()
    if not str(root):
        root = REPOSITORY_ROOT / "nextnano" / "results" / "demo_runs"
    base = Path(root) / cfg["demo_id"]
    if not base.is_dir():
        raise SystemExit(f"no Demo 16G results under {base}")
    runs = sorted((p for p in base.iterdir() if p.is_dir()), reverse=True)
    if not runs:
        raise SystemExit(f"no Demo 16G run directories under {base}")
    return runs[0]


def _load_records(run_dir: Path) -> list[dict]:
    """Every case's provenance.json, for --analyze."""

    records = []
    for path in sorted((Path(run_dir) / "cases").rglob("provenance.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def run_plan(cfg: dict, nnp_overrides, verbose: bool) -> int:
    groups = cases16g.all_cases(cfg, REPOSITORY_ROOT, nnp_overrides)
    print(RULE)
    print("  DEMO 16G -- PLAN (no solver is launched)")
    print(RULE)
    print(f"  config          : {cfg['_config_path']}")
    print(f"  repository root : {REPOSITORY_ROOT}")
    print(f"  tensor          : {cfg['optics']['tensor']}   units pm/V")
    print(f"  scale factor    : {cfg['optics']['absolute_scale_factor']} (must stay null)")
    try:
        machine = demo16g.resolve_machine(require_solver=False)
        for key, value in demo16g.machine_record(machine).items():
            print(f"  {key:<22}: {value}")
    except Exception as exc:  # noqa: BLE001
        print(f"  machine          : NOT RESOLVED -- {exc}")

    note = grading16g.convention_note(cfg["grading"]["definition"])
    print(f"\n  GRADING CONVENTION: {note['definition']}")
    print(f"    {note['meaning']}")
    print(f"    source: {note['source']}")
    print(f"    WARNING: {note['warning']}")

    print(f"\n  GROUP 1 -- supplied .nnp files")
    for case in groups[cases16g.GROUP_NNP]:
        print(f"    {case.case_id:<26} {case.source_path}")
        if not case.source_path.is_file():
            print(f"      MISSING: this path does not exist")
            continue
        inspection = nnp16g.inspect(case.source_path)
        print(f"      sha256 {inspection.sha256_source}")
        print(f"      hole model {inspection.hole_model}   "
              f"computes chi2 itself: {inspection.computes_chi2}")
        summary = nnp16g.structure_summary(inspection)
        print(f"      {summary.get('thick_well_nm')} / {summary.get('barrier_nm')} / "
              f"{summary.get('thin_well_nm')} nm, grade "
              f"{summary.get('left_grade_nm')} nm "
              f"(full ramp {summary.get('left_full_linear_ramp_width_nm')}, "
              f"10-90 {summary.get('left_10_90_width_nm')})")
        for warning in inspection.warnings:
            print(f"      WARNING {warning}")

    design = groups["sweep_design"]
    print(f"\n  GROUP 2 -- {design['count']} structures, seed {design['seed']}, "
          f"maximin over {design['candidates_evaluated']} LHS designs")
    print(f"    minimum pairwise distance {design['selected_minimum_pairwise_distance']:.4f} "
          f"(mean candidate {design['candidate_distance_mean']:.4f})")
    header = (f"    {'case':<12}{'thick':>7}{'barr':>7}{'thin':>7}"
              f"{'gradeL':>8}{'gradeR':>8}{'ramp L':>8}{'ramp R':>8}{'s':>7}  repr")
    print(header)
    for case in groups[cases16g.GROUP_SWEEP]:
        try:
            _deck, provenance = deck16g.render(case, cfg)
            representation = provenance["representation"]
        except deck16g.Deck16GError as exc:
            representation = f"REFUSED ({exc})"
        print(f"    {case.case_id:<12}{case.thick_well_nm:>7.2f}"
              f"{case.tunnel_barrier_nm:>7.2f}{case.thin_well_nm:>7.2f}"
              f"{case.left_grade_nm:>8.2f}{case.right_grade_nm:>8.2f}"
              f"{case.left_grade.full_linear_ramp_width_nm:>8.2f}"
              f"{case.right_grade.full_linear_ramp_width_nm:>8.2f}"
              f"{case.asymmetry_s:>7.3f}  {representation}")
    if design["abrupt_cases"]:
        print(f"    abrupt cases: {design['abrupt_cases']}")

    print(f"\n  GROUP 3 -- paper benchmark")
    benchmark = groups[cases16g.GROUP_PAPER][0]
    for key, value in benchmark.as_record().items():
        if key in ("notes", "label", "source", "source_kind"):
            continue
        print(f"    {key:<32} {value}")
    targets = cfg["paper_benchmark"]["targets_pm_per_V"]
    print(f"    PRIMARY TARGET                   "
          f"{targets['ideal_abrupt_at_1550']:g} pm/V at 1550 nm (stated in words)")
    for name, value in targets.items():
        if name != "ideal_abrupt_at_1550":
            print(f"    also recorded: {name:<18} {value:g} pm/V")
    print(f"    Fig. 2d peak {cfg['paper_benchmark']['figure2d_peak_visual_reference_pm_per_V']}"
          " pm/V is a VISUAL REFERENCE ONLY, never a target")
    print(RULE)
    return 0


# ---------------------------------------------------------------------------
# Solve modes
# ---------------------------------------------------------------------------


def run_groups(
    cfg: dict, selected: list[str], nnp_overrides, verbose: bool,
    run_dir: Path | None = None,
) -> tuple[int, Path, list[dict]]:
    machine = demo16g.resolve_machine(require_solver=True)
    groups = cases16g.all_cases(cfg, REPOSITORY_ROOT, nnp_overrides)
    root = _run_dir(cfg, machine, run_dir)
    print(RULE)
    print(f"  DEMO 16G -- {'/'.join(selected).upper()}")
    print(RULE)
    print(f"  RUN DIR    : {root}")
    for key, value in demo16g.machine_record(machine).items():
        print(f"  {key:<22}: {value}")
    print(f"  SCALE      : none. Every chi2 is computed from the physics.")
    print(RULE)

    demo16g.write_json(root / "summaries" / "sweep_design.json",
                       groups["sweep_design"])
    demo16g.write_json(root / "summaries" / "grading_convention.json",
                       groups["grading_convention"])

    records: list[dict] = []
    for group in selected:
        records.extend(runners16g.run_group(
            group, groups[group], cfg, root, machine, verbose=verbose,
        ))
    demo16g.write_json(
        root / "summaries" / f"records_{'_'.join(selected)}.json",
        [{k: v for k, v in r.items() if not str(k).startswith("_")} for r in records],
    )
    print()
    print(report16g.console_table(records))
    passed = sum(1 for r in records if r.get("passed"))
    print(f"\n  {passed}/{len(records)} cases produced a result")
    print(f"  RUN DIR: {root}")
    print(RULE)
    return (0 if passed == len(records) else 1), root, records


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------


def run_analyze(cfg: dict, run_dir: Path | None, verbose: bool) -> int:
    try:
        machine = demo16g.resolve_machine(require_solver=False)
    except Exception:  # noqa: BLE001 - analysis must work without a licence
        machine = None
    root = Path(run_dir) if run_dir else _latest_run(cfg, machine)
    records = _load_records(root)
    if not records:
        raise SystemExit(f"no case records under {root / 'cases'}")

    print(RULE)
    print(f"  DEMO 16G -- ANALYZE  {root}")
    print(RULE)
    written = report16g.write_master(
        root / "summaries", records, cfg,
        extra={"comparison_against_paper":
               report16g.comparison_against_paper(records, cfg)},
    )
    figures = plots16g.write_all(root / "plots", records, cfg)
    print(report16g.console_table(records))
    comparison = report16g.comparison_against_paper(records, cfg)
    if comparison.get("available"):
        print(f"\n  paper benchmark chi2(1550) : "
              f"{comparison['our_chi2_1550_pm_per_V']:.2f} pm/V")
        print(f"  paper stated target        : "
              f"{comparison['primary_target_pm_per_V']:g} pm/V")
        print(f"  remaining factor           : "
              f"{comparison['remaining_factor_vs_primary_target']:.1f}x  "
              "(reported, never applied)")
    print(f"\n  CSV   : {written['csv']}")
    print(f"  JSON  : {written['json']}")
    for name, path in sorted(figures.items()):
        print(f"  PLOT  : {path}")
    if not figures:
        print("  PLOTS : none written (matplotlib unavailable)")
    print(RULE)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Demo 16G: the two supplied .nnp files, 20 varied ACQW structures "
            "and the paper benchmark, through one chi2 evaluator. No fitting."
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--plan", action="store_true")
    group.add_argument("--nnp-comparison", action="store_true")
    group.add_argument("--paper-benchmark", action="store_true")
    group.add_argument("--sweep", action="store_true")
    group.add_argument("--analyze", action="store_true")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--config", metavar="YAML")
    parser.add_argument("--nnp-file", action="append", metavar="PATH",
                        help="override a supplied .nnp path, positionally; "
                             "repeatable")
    parser.add_argument("--run-dir", metavar="DIR",
                        help="reuse or analyze this run directory")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    cfg = cases16g.load_config(Path(args.config) if args.config else None)
    run_dir = Path(args.run_dir) if args.run_dir else None

    if args.plan:
        return run_plan(cfg, args.nnp_file, args.verbose)
    if args.analyze:
        return run_analyze(cfg, run_dir, args.verbose)
    if args.nnp_comparison:
        return run_groups(cfg, [cases16g.GROUP_NNP], args.nnp_file,
                          args.verbose, run_dir)[0]
    if args.paper_benchmark:
        return run_groups(cfg, [cases16g.GROUP_PAPER], args.nnp_file,
                          args.verbose, run_dir)[0]
    if args.sweep:
        return run_groups(cfg, [cases16g.GROUP_SWEEP], args.nnp_file,
                          args.verbose, run_dir)[0]
    if args.all:
        status, root, _ = run_groups(
            cfg,
            [cases16g.GROUP_NNP, cases16g.GROUP_PAPER, cases16g.GROUP_SWEEP],
            args.nnp_file, args.verbose, run_dir,
        )
        analyze = run_analyze(cfg, root, args.verbose)
        return status or analyze
    return run_plan(cfg, args.nnp_file, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
