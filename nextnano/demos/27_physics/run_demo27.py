"""Demo 27 master runner: a staged physics campaign, one question at a time.

Demo 27 is NOT one simulation. It is a set of small, independent sub-demos, each
answering a single physics question with a single controlled change. This runner
selects exactly one of them and runs exactly one of its stages.

    python run_demo27.py --list
    python run_demo27.py --status
    python run_demo27.py --reuse-audit
    python run_demo27.py --demo 27A --preflight
    python run_demo27.py --demo 27A --physics
    python run_demo27.py --demo 27B --analyze
    python run_demo27.py --demo 27A --record PASS --conclusion "..."
    python run_demo27.py --tests

There is deliberately NO flag that launches every Professional calculation.
``--all-physics`` and its synonyms are refused before argument parsing, so the
refusal cannot be bypassed by argparse abbreviation matching.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[2]
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from framework import Demo27Error  # noqa: E402
from framework import analyze as analyze_module  # noqa: E402
from framework import physics as physics_module  # noqa: E402
from framework import preflight as preflight_module  # noqa: E402
from framework import registry, reuse, solver, status  # noqa: E402
from framework.report import markdown_table, write_csv, write_text  # noqa: E402


# ---------------------------------------------------------------------------
# execution policy
# ---------------------------------------------------------------------------

def enforce_policy(argv: list, parent) -> None:
    """Refuse any 'run everything' invocation, before argparse sees it.

    argparse abbreviates unknown long options against known ones, so a check
    performed inside argparse could be defeated by a prefix. This runs first and
    matches on the raw token.
    """
    forbidden = [str(f) for f in parent["policy"]["forbidden_batch_flags"]]
    lowered = {token.split("=", 1)[0].lower() for token in argv}
    hit = sorted(lowered & {f.lower() for f in forbidden})
    if hit:
        raise SystemExit(
            "REFUSED: %s does not exist and will not be added.\n\n"
            "Demo 27 answers one physics question per run. A flag that launches every\n"
            "Professional calculation would spend days of solver time on questions whose\n"
            "answers depend on each other, and would make a failure impossible to\n"
            "attribute. Select one sub-demo:\n\n"
            "    python run_demo27.py --list\n"
            "    python run_demo27.py --demo 27A --preflight\n"
            % ", ".join(hit))


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def command_list(parent, subs) -> int:
    recorded = status.statuses(parent)
    rows = []
    for sub in subs:
        rows.append({
            "Demo": sub.demo_id,
            "Tier": sub.tier,
            "Pro": "yes" if sub.professional_required else "no",
            "Runtime": sub.runtime_text(),
            "Status": registry.derived_status(sub, recorded),
            "Prereq": ", ".join(sub.prerequisites) or "-",
            "Question": sub.question,
        })
    print("Demo 27 sub-demos (run ONE at a time):\n")
    print(markdown_table(rows, ["Demo", "Tier", "Pro", "Runtime", "Status",
                                "Prereq", "Question"]))
    ordered = [s for s in subs if s.priority is not None]
    ordered.sort(key=lambda s: s.priority)
    if ordered:
        print("\nRecommended order for paper reproduction:")
        for sub in ordered:
            print("  %d. %s  %s" % (sub.priority, sub.demo_id, sub.title))
    runnable = [s for s in subs
                if registry.derived_status(s, recorded) in ("NOT RUN", "READY")
                and not registry.blocking_prerequisites(s, recorded)]
    if runnable:
        runnable.sort(key=lambda s: (s.priority if s.priority is not None else 99, s.tier))
        print("\nRunnable now: %s" % ", ".join(s.demo_id for s in runnable))
        print("  python run_demo27.py --demo %s --preflight" % runnable[0].demo_id)
    return 0


def command_status(parent, subs) -> int:
    path = status.render(parent, subs)
    print(markdown_table(status.rows(parent, subs),
                         ["Demo", "Question", "Tier", "Status", "Pro required?",
                          "Runtime estimate", "Prerequisite", "Main conclusion"],
                         alignments={"Tier": "right"}))
    print("\nWritten: %s" % path.relative_to(REPO_ROOT))
    return 0


def command_reuse_audit(parent, subs) -> int:
    reuse.assert_no_writes_outside_demo27(parent)
    result = reuse.audit(parent)
    write_csv(DEMO_DIR / "REUSE_AUDIT.csv", result["rows"])
    text = "\n".join([
        "# Demo 27 reuse audit",
        "",
        "What Demo 27 takes from Demos 23-26 instead of recomputing it, and whether",
        "those artifacts are still byte-identical to when Demo 27 first read them.",
        "",
        "Demo 27 reads these and never writes to them.",
        "",
        markdown_table(result["rows"], ["artifact", "exists", "integrity", "entries",
                                        "bytes", "reusable_for", "provides"]),
        "",
        "## Reuse rules",
        "",
        markdown_table(result["rows"], ["artifact", "reuse_rule"]),
        "",
    ])
    if result["missing"]:
        text += "\n> MISSING: %s\n" % ", ".join(result["missing"])
    if result["drifted"]:
        text += ("\n> **INTEGRITY WARNING**: %s changed since Demo 27 baselined them. "
                 "Either an earlier demo was rerun, or something modified its output. "
                 "Resolve this before trusting any Demo 27 comparison against them.\n"
                 % ", ".join(result["drifted"]))
    write_text(DEMO_DIR / "REUSE_AUDIT.md", text)
    print(markdown_table(result["rows"], ["artifact", "exists", "integrity",
                                          "reusable_for"]))
    if result["missing"]:
        print("\nMISSING: %s" % ", ".join(result["missing"]))
    if result["drifted"]:
        print("\nINTEGRITY WARNING: %s changed since baseline." % ", ".join(result["drifted"]))
    print("\nWritten: %s" % (DEMO_DIR / "REUSE_AUDIT.md").relative_to(REPO_ROOT))
    return 1 if result["drifted"] else 0


def command_preflight(parent, subs, sub, machine) -> int:
    resolved = registry.resolve(sub, parent)
    result = preflight_module.run(sub, resolved, machine)
    print("%s preflight: %s" % (sub.demo_id, result["status"]))
    if result["decks"]:
        print(markdown_table(result["decks"], ["deck", "band_model", "k_mode", "k_points",
                                               "states_out", "changed_fields"]))
    if result.get("parse_status") == "SKIPPED":
        print("\nnextnano++ is not configured here, so deck grammar was NOT validated.")
    elif result.get("parse_status") == "FAIL":
        for row in result["parse"]:
            if not row["parse_ok"]:
                print("  PARSE FAIL %s: %s" % (row["deck"], row["message"]))
    print()
    print((sub.outputs_dir / "COST_STATEMENT.md").read_text(encoding="utf-8"))
    if result["status"] != "PASS":
        status.record(parent, sub.demo_id, "FAIL", note="preflight failed")
        return 1
    recorded = status.statuses(parent)
    blocking = registry.blocking_prerequisites(sub, recorded)
    new_status = "BLOCKED" if blocking else "READY"
    if new_status == "READY":
        status.record(parent, sub.demo_id, "READY", note="preflight passed")
        print("Next:  python run_demo27.py --demo %s --%s"
              % (sub.demo_id,
                 "physics" if sub.stage_kind("physics") in ("professional", "delegated")
                 else "analyze"))
    else:
        print("Prerequisites not satisfied: %s"
              % ", ".join("%s=%s" % pair for pair in blocking))
    return 0


def command_physics(parent, subs, sub, machine, args) -> int:
    if parent["policy"]["enforce_prerequisites"]:
        recorded = status.statuses(parent)
        blocking = registry.blocking_prerequisites(sub, recorded)
        if blocking:
            print("REFUSED: %s is blocked by %s.\n"
                  % (sub.demo_id, ", ".join("%s=%s" % pair for pair in blocking)),
                  file=sys.stderr)
            print("Run the prerequisite first. Demo 27 does not run a sub-demo whose\n"
                  "inputs have not been established; the result would not be attributable.",
                  file=sys.stderr)
            return 3
    resolved = registry.resolve(sub, parent)
    cost = preflight_module.cost_statement(sub, resolved)
    statement = sub.outputs_dir / "COST_STATEMENT.md"
    if not statement.is_file():
        print("REFUSED: %s has not passed preflight. Run:\n"
              "    python run_demo27.py --demo %s --preflight"
              % (sub.demo_id, sub.demo_id), file=sys.stderr)
        return 4
    print(statement.read_text(encoding="utf-8"))
    if not args.yes:
        print("This will launch nextnano++ Professional with the burden stated above.")
        print("Re-run with --yes to proceed:")
        print("    python run_demo27.py --demo %s --physics --yes" % sub.demo_id)
        return 0
    status.record(parent, sub.demo_id, "RUNNING", note="physics stage launched")
    try:
        result = physics_module.run(sub, resolved, machine, cost,
                                    timeout_seconds=float(args.timeout))
    except Demo27Error:
        status.record(parent, sub.demo_id, "FAIL", note="physics stage refused or failed")
        raise
    status.record(parent, sub.demo_id, "RUNNING",
                  note="physics stage finished; run --analyze to decide PASS/FAIL")
    print("\n%s physics stage finished (%s)." % (sub.demo_id, result["kind"]))
    print("Next:  python run_demo27.py --demo %s --analyze" % sub.demo_id)
    return 0


def command_analyze(parent, subs, sub) -> int:
    resolved = registry.resolve(sub, parent)
    result = analyze_module.run(sub, resolved)
    print("%s analysis: %s" % (sub.demo_id, result["status"]))
    if result["status"] == "NO DATA":
        print("\n" + result["message"])
        print("\nNothing was written beyond the audit. Demo 27 does not invent raw physics.")
        return 1
    print("\nWritten: %s" % (sub.outputs_dir / "ANALYSIS.md").relative_to(REPO_ROOT))
    print("\nRecord the verdict when you have read it:")
    print('    python run_demo27.py --demo %s --record PASS --conclusion "..."' % sub.demo_id)
    return 0


def command_record(parent, sub, args) -> int:
    entry = status.record(parent, sub.demo_id, args.record,
                          conclusion=args.conclusion, note=args.note)
    print("%s -> %s" % (sub.demo_id, entry["status"]))
    if args.conclusion:
        print("  conclusion: %s" % args.conclusion)
    if args.record in registry.SATISFYING and sub.unlocks:
        print("  unlocks: %s" % ", ".join(sub.unlocks))
    return 0


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_demo27.py",
        description="Demo 27 staged physics campaign. One sub-demo, one stage, per run.",
        epilog="There is no flag that runs every Professional calculation.")
    parser.add_argument("--demo", help="which sub-demo to act on, e.g. 27A")
    parser.add_argument("--list", action="store_true", help="list the sub-demos and their state")
    parser.add_argument("--status", action="store_true", help="regenerate and print MASTER_STATUS")
    parser.add_argument("--reuse-audit", action="store_true",
                        help="audit what Demo 27 reuses from Demos 23-26 and verify integrity")
    parser.add_argument("--preflight", action="store_true",
                        help="resolve config, generate decks, --parse them, state the cost")
    parser.add_argument("--physics", action="store_true",
                        help="run this sub-demo's Professional calculation (needs --yes)")
    parser.add_argument("--analyze", "--analyse", dest="analyze", action="store_true",
                        help="post-process this sub-demo (never launches a solver)")
    parser.add_argument("--record", choices=list(registry.STATUSES),
                        help="record this sub-demo's outcome in MASTER_STATUS")
    parser.add_argument("--conclusion", default=None, help="one-line conclusion for --record")
    parser.add_argument("--note", default=None, help="free-text note for --record")
    parser.add_argument("--yes", action="store_true",
                        help="confirm the stated solver cost and actually launch --physics")
    parser.add_argument("--timeout", type=float, default=86400.0,
                        help="per-deck solver timeout in seconds (default 86400)")
    parser.add_argument("--machine", type=Path, help="explicit nextnano paths.local.yaml")
    parser.add_argument("--tests", action="store_true", help="run the Demo 27 test suite")
    return parser


def main(argv: list | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parent = registry.load_parent_config()
    enforce_policy(argv, parent)

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.tests:
        return subprocess.run([sys.executable, "-m", "pytest", str(DEMO_DIR / "tests"),
                               "-q", "-p", "no:cacheprovider"],
                              cwd=str(REPO_ROOT), check=False).returncode

    subs = registry.discover(parent)

    if args.list:
        return command_list(parent, subs)
    if args.status:
        return command_status(parent, subs)
    if args.reuse_audit:
        return command_reuse_audit(parent, subs)

    stages = [name for name, chosen in (("preflight", args.preflight),
                                        ("physics", args.physics),
                                        ("analyze", args.analyze),
                                        ("record", bool(args.record))) if chosen]
    if not stages:
        parser.print_help()
        print("\nNothing selected. Start with:  python run_demo27.py --list")
        return 0
    if len(stages) > 1:
        print("REFUSED: pick one stage per run, not %s. Each stage has a different cost "
              "and a different failure mode." % ", ".join(stages), file=sys.stderr)
        return 2
    if not args.demo:
        print("REFUSED: --%s needs --demo. Demo 27 never acts on every sub-demo at once."
              % stages[0], file=sys.stderr)
        return 2
    if "," in args.demo or " " in args.demo.strip():
        print("REFUSED: --demo takes exactly one sub-demo, not %r. Run them one at a time "
              "so a failure is attributable." % args.demo, file=sys.stderr)
        return 2

    sub = registry.find(args.demo, subs)

    machine = None
    try:
        machine = solver.machine_config(args.machine)
    except Demo27Error as exc:
        if args.physics:
            print("ERROR: %s" % exc, file=sys.stderr)
            return 2
        print("note: %s\n" % exc)

    if stages[0] == "preflight":
        return command_preflight(parent, subs, sub, machine)
    if stages[0] == "physics":
        return command_physics(parent, subs, sub, machine, args)
    if stages[0] == "analyze":
        return command_analyze(parent, subs, sub)
    return command_record(parent, sub, args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Demo27Error as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        raise SystemExit(2)
