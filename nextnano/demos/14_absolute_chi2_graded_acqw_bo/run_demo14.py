"""Demo 14 command line.

    python run_demo14.py --preflight              # self-test, no solver
    python run_demo14.py --mock-campaign          # harness test, no solver
    python run_demo14.py --gate                   # LICENSED startup gate
    python run_demo14.py --run                    # LICENSED 30-trial campaign
    python run_demo14.py --resume <run_directory>
    python run_demo14.py --analyze <run_directory>
    python run_demo14.py --plots <run_directory>
    python run_demo14.py --debug-bundle <run_directory>
    python run_demo14.py --full-raw-bundle <run_directory>

``--run`` always creates a NEW run directory. There is no invocation that
resumes implicitly; resuming requires naming the directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO11 = DEMO_DIR.parent / "11_paper_validation_interband_chi2_acqw"
for path in (str(SHARED), str(DEMO_DIR), str(DEMO11)):
    if path not in sys.path:
        sys.path.insert(0, path)

import bundle14  # noqa: E402
import campaign14  # noqa: E402
import demo14  # noqa: E402
import gate14  # noqa: E402
import preflight14  # noqa: E402


def resolve_machine():
    """The single machine resolution used by preflight, gate and run alike.

    ``load_machine_config`` must be called with **no argument**. Passing a path
    makes the loader treat it as an explicit config file, and a non-file (such as
    a demo directory) silently falls back to the tracked example *and* disables
    the `paths.local.yaml` and nextnanopy reuse that both live behind a
    ``config_path is None`` guard. The symptom on a licensed machine is a
    resolved ``executable: null`` and a campaign that dry-runs while reporting
    success -- so this is deliberately one function, called by every entry point,
    rather than three call sites that could drift apart.
    """

    import demo_workflow as workflow

    return workflow.load_machine_config()


def _results_root():
    machine = resolve_machine()
    return Path(machine.results_root) / "demo_runs", machine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_demo14.py", description="Demo 14 absolute chi(2) graded ACQW BO"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true",
                       help="self-test without the solver")
    group.add_argument("--mock-campaign", action="store_true",
                       help="miniature campaign against the mock solver")
    group.add_argument("--gate", action="store_true",
                       help="LICENSED startup gate: import equivalence + paper reference")
    group.add_argument("--run", action="store_true",
                       help="LICENSED new 30-completed-trial campaign")
    group.add_argument("--resume", metavar="RUN_DIR")
    group.add_argument("--analyze", metavar="RUN_DIR")
    group.add_argument("--plots", metavar="RUN_DIR")
    group.add_argument("--debug-bundle", metavar="RUN_DIR")
    group.add_argument("--full-raw-bundle", metavar="RUN_DIR")
    parser.add_argument("--config", default=None, help="alternate demo.yaml")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--force-no-gate", action="store_true",
                        help="launch the campaign without a passing startup gate")
    args = parser.parse_args(argv)

    config_path = Path(args.config) if args.config else DEMO_DIR / "demo.yaml"
    cfg = demo14.load_config(config_path)

    if args.preflight:
        # Resolved through the same function the licensed paths use, so a green
        # preflight is evidence about the machine --gate and --run will actually
        # get, not about a separately-derived one.
        #
        # The loader raises when a configured path is missing. For --gate and
        # --run that is exactly right -- fail loudly before spending licensed
        # time. For --preflight it would be a traceback in place of the report
        # the command exists to produce, so it is caught and shown as a failed
        # check alongside the others.
        try:
            machine = resolve_machine()
            machine_error = None
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            machine, machine_error = None, f"{type(exc).__name__}: {exc}"
        return preflight14.run_preflight(
            cfg, config_path=config_path, machine=machine,
            machine_error=machine_error,
        )

    if args.mock_campaign:
        import tempfile

        root = Path(tempfile.mkdtemp(prefix="demo14_mock_"))
        mock_cfg = preflight14.miniature_config(cfg)
        outcome = campaign14.run_campaign(
            mock_cfg, results_root=root, mock=True,
            config_path=config_path, verbose=args.verbose,
        )
        print(f"\nMock campaign: {outcome['status']}  "
              f"{outcome['completed_trials']}/{outcome['target_completed_trials']} trials")
        print(f"Run directory: {outcome['run_directory']}")
        return 0 if outcome["status"] == "COMPLETED" else 1

    if args.debug_bundle:
        path = bundle14.build_debug_bundle(Path(args.debug_bundle))
        print(f"Debug bundle: {path}")
        return 0

    if args.full_raw_bundle:
        path = bundle14.build_full_raw_bundle(Path(args.full_raw_bundle))
        print(f"Full raw bundle: {path}")
        return 0

    if args.analyze or args.plots:
        target = Path(args.analyze or args.plots)
        import analysis14

        return analysis14.analyze_run(target, plots_only=bool(args.plots))

    # --- licensed paths ----------------------------------------------------
    results_root, machine = _results_root()

    if args.gate:
        return gate14.run_startup_gate(
            cfg, results_root=results_root, machine=machine, config_path=config_path
        )

    if args.run:
        if cfg["startup_gate"].get("require_gate_before_campaign", True) and not args.force_no_gate:
            verdict = gate14.latest_gate_verdict(results_root)
            if verdict is not True:
                print(
                    "REFUSING TO START: the licensed startup gate has not passed.\n"
                    "  Run:  python run_demo14.py --gate\n"
                    "  Then re-run this command once it prints GATE PASSED.\n"
                    f"  (latest recorded verdict: {verdict!r})"
                )
                return 2
        outcome = campaign14.run_campaign(
            cfg, results_root=results_root, machine=machine, mock=False,
            config_path=config_path, verbose=args.verbose,
        )
        print(f"\n{outcome['status']}: {outcome['completed_trials']}/"
              f"{outcome['target_completed_trials']} completed trials")
        print(f"Run directory: {outcome['run_directory']}")
        bundle = bundle14.build_debug_bundle(Path(outcome["run_directory"]))
        print(f"Debug bundle: {bundle}")
        return 0 if outcome["status"] == "COMPLETED" else 1

    if args.resume:
        outcome = campaign14.run_campaign(
            cfg, results_root=results_root, machine=machine, mock=False,
            resume_dir=Path(args.resume), config_path=config_path, verbose=args.verbose,
        )
        print(f"\n{outcome['status']}: {outcome['completed_trials']}/"
              f"{outcome['target_completed_trials']} completed trials")
        return 0 if outcome["status"] == "COMPLETED" else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
