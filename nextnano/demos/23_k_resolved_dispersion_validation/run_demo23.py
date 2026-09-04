"""Run Demo 23: controlled Equation 2 dispersion validation with real kp8 data."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from config23 import DEMO_DIR, REPO_ROOT, Demo23Error, load_config, result_root
import analysis23
import deck23
import physics23
import reporting


DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
if str(DEMO22) not in sys.path:
    sys.path.insert(0, str(DEMO22))
import run_demo22  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _syntax_check(decks: tuple[tuple[deck23.DeckSpec, Path], ...]) -> list[dict[str, Any]]:
    parser = run_demo22._free_parser()  # Same syntax-only discovery used by Demo 22.
    log_root = DEMO_DIR / "inputs" / "syntax_logs"
    log_root.mkdir(parents=True, exist_ok=True)
    rows = []
    if parser is None:
        return [{"deck": path.name, "status": "NOT_RUN", "return_code": "",
                 "parser_edition": "none", "notes": "free syntax parser not installed"}
                for _, path in decks]
    executable, database, licence = parser
    for _, path in decks:
        argv = [str(executable), "--parse", "-d", str(database)]
        if licence:
            argv += ["-l", str(licence)]
        argv.append(str(path))
        run = subprocess.run(argv, cwd=DEMO_DIR, text=True, capture_output=True,
                             timeout=120, check=False)
        log = log_root / f"{path.stem}.txt"
        log.write_text(run.stdout + "\n--- STDERR ---\n" + run.stderr, encoding="utf-8")
        rows.append({"deck": path.name, "status": "PASS" if run.returncode == 0 else "FAIL",
                     "return_code": run.returncode, "parser_edition": "LIMITED FREE; syntax only",
                     "notes": "No physics was executed."})
    return rows


def preflight(cfg: Mapping[str, Any], machine_path: Path | None = None) -> tuple[
    tuple[tuple[deck23.DeckSpec, Path], ...], Any | None, dict[str, Any]
]:
    decks = deck23.write_decks(cfg, DEMO_DIR / "inputs")
    syntax = _syntax_check(decks)
    reporting.write_csv(DEMO_DIR / "inputs" / "syntax_validation.csv", syntax)
    frozen = physics23.load_frozen_k0_inputs(cfg)
    machine, probe = run_demo22.professional_probe(machine_path)
    manifest = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": sys.version,
        "repository_root": str(REPO_ROOT),
        "configuration": cfg,
        "professional_probe": probe,
        "frozen_k0_source": str(frozen.source),
        "synthetic_production_fallback_allowed": False,
        "decks": [{
            **spec.__dict__, "path": str(path.relative_to(DEMO_DIR)), "sha256": _sha256(path)
        } for spec, path in decks],
        "syntax_validation": syntax,
    }
    reporting.write_json(DEMO_DIR / "inputs" / "PREFLIGHT_MANIFEST.json", manifest)
    failures = [row for row in syntax if row["status"] == "FAIL"]
    if failures:
        raise Demo23Error("nextnano syntax validation failed: " + ", ".join(row["deck"] for row in failures))
    return decks, machine, probe


def require_professional(machine: Any | None, probe: Mapping[str, Any]) -> Any:
    if machine is None or not bool(probe.get("available")):
        raise Demo23Error(
            "--physics requires nextnano++ Professional executable, database, and license: "
            + str(probe.get("reason", "unavailable"))
        )
    return machine


def run_physics(
    cfg: Mapping[str, Any], decks: tuple[tuple[deck23.DeckSpec, Path], ...],
    machine: Any, *, selected_mode: str | None = None,
) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = result_root(cfg) / f"demo23_{stamp}"
    run_root.mkdir(parents=True, exist_ok=False)
    copied_inputs = run_root / "inputs"
    copied_inputs.mkdir(parents=True)
    records = []
    for index, (spec, deck) in enumerate(decks, start=1):
        copied = copied_inputs / deck.name
        shutil.copy2(deck, copied)
        print(f"[{index}/{len(decks)}] Running {spec.name} ({spec.role})...", flush=True)
        try:
            invocation = run_demo22.solver14.execute_real(
                executable=Path(machine.executable),
                database=Path(machine.database),
                license_path=Path(machine.license),
                deck=copied,
                output_dir=run_root / "raw" / spec.name,
                threads=int(cfg["solver"]["threads"]),
                timeout_seconds=float(cfg["solver"]["timeout_seconds_per_deck"]),
                logs_dir=run_root / "logs" / spec.name,
            )
        except Exception as exc:
            reporting.write_json(run_root / "PHYSICS_RUN_FAILED.json", {
                "failed_deck": spec.name,
                "completed_invocations": records,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "spectrum_generated": False,
            })
            raise Demo23Error(
                f"Professional solve failed for {spec.name}; no chi2 spectrum was generated: {exc}"
            ) from exc
        records.append({**spec.__dict__, **invocation.as_record()})
        reporting.write_json(run_root / "solver_invocations.json", records)
    print("All Professional kp8 decks completed. Starting gated 23A-D analysis...", flush=True)
    analysis23.analyze_run(cfg, run_root, run_root / "analysis", selected_mode=selected_mode)
    return run_root


def run_tests() -> int:
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(DEMO_DIR / "tests"), "-q"],
        cwd=REPO_ROOT, check=False,
    ).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--preflight", action="store_true", help="validate configuration, decks, inputs, and solver availability")
    actions.add_argument("--tests", action="store_true", help="run Demo 23 automated tests")
    actions.add_argument("--generate-inputs", action="store_true", help="render all shared Professional kp8 decks")
    actions.add_argument("--physics", action="store_true", help="run all required Professional kp8 decks and analyze")
    actions.add_argument("--analyze", "--analyse-existing", type=Path, help="analyze a completed Demo 23 run root")
    actions.add_argument("--plots-only", type=Path, help="regenerate analysis tables, report, and plots from a completed run")
    parser.add_argument("--mode", choices=("23A", "23B", "23C", "23D"), help="report only this mode (23A gate always runs)")
    parser.add_argument("--machine", type=Path, help="explicit nextnano machine YAML")
    parser.add_argument("--output", type=Path, help="analysis output directory for --analyze/--plots-only")
    args = parser.parse_args(argv)
    cfg = load_config(args.mode)

    if args.tests:
        return run_tests()
    if args.generate_inputs:
        written = deck23.write_decks(cfg, DEMO_DIR / "inputs")
        print(f"Generated {len(written)} shared Demo 23 decks in {DEMO_DIR / 'inputs'}")
        return 0
    if args.analyze or args.plots_only:
        source = (args.analyze or args.plots_only).resolve()
        destination = args.output.resolve() if args.output else source / "analysis"
        summary = analysis23.analyze_run(cfg, source, destination, selected_mode=args.mode)
        print(json.dumps(summary, indent=2, default=str))
        return 0

    decks, machine, probe = preflight(cfg, args.machine)
    if not args.physics:
        print(f"Demo 23 preflight complete: {DEMO_DIR}")
        print(f"Professional available: {probe.get('available')} ({probe.get('reason', '')})")
        print(f"Generated {len(decks)} decks; no physics was run.")
        return 0
    run_root = run_physics(cfg, decks, require_professional(machine, probe), selected_mode=args.mode)
    print(f"Demo 23 complete: {run_root}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Demo23Error as exc:
        print(f"DEMO 23 ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)

