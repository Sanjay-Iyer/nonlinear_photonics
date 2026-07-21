"""Run, dry-run, or preflight nextnano++ input decks.

Examples (paths are relative to the repo root; run from anywhere):

    python nextnano/scripts/run_input.py --help
    python nextnano/scripts/run_input.py --check-config
    python nextnano/scripts/run_input.py nextnano/inputs/01_smoke_tests/hello_01_bulk_gaas.in
    python nextnano/scripts/run_input.py "nextnano/inputs/01_smoke_tests/hello_*.in"

Exit codes:
    0  success
    1  a solver run failed, or a required preflight check failed
    2  bad invocation: no/unmatched inputs, or invalid configuration
    3  execution requested but nextnanopy could not be imported

The runner never reads or prints license-file contents; only paths are shown.
"""

from __future__ import annotations

import argparse
import glob
import sys
import time
import traceback
from pathlib import Path

# This file is imported directly (its own directory is on sys.path[0] when run
# as a script). Tests add the scripts dir to sys.path via conftest.
from nn_config import ConfigError, resolve_config, preflight

_WILDCARD_CHARS = "*?["


def expand_inputs(patterns) -> list[Path]:
    """Resolve input arguments into an ordered, de-duplicated list of files.

    Wildcards are expanded internally (not left to the shell) so behavior is
    identical in PowerShell, cmd.exe, and POSIX shells -- Windows shells do
    not glob for native executables. An argument that matches nothing (a
    missing plain path OR an unmatched wildcard) is an explicit error.

    Ordering is preserved: matches within one wildcard are sorted; arguments
    keep their given order. Duplicates (by resolved absolute path) are removed.
    """
    resolved: list[Path] = []
    for pat in patterns:
        pat = str(pat)
        if any(ch in pat for ch in _WILDCARD_CHARS):
            matches = sorted(Path(m) for m in glob.glob(pat))
            if not matches:
                raise FileNotFoundError(f"no files match pattern: {pat}")
            resolved.extend(matches)
        else:
            path = Path(pat)
            if not path.is_file():
                raise FileNotFoundError(f"input file not found: {pat}")
            resolved.append(path)

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in resolved:
        key = path.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def build_plan(cfg, inputs: list[Path]) -> list[tuple[Path, Path]]:
    """Assign each deck its own output subdirectory (base/<deck stem>).

    Distinct subdirectories guarantee two decks cannot overwrite each other's
    results even when run together.
    """
    return [(deck, cfg.outputdirectory / deck.stem) for deck in inputs]


def _fmt_runtime(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:6.2f} s"
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes):d}m{secs:04.1f}s"


def _print_plan(plan: list[tuple[Path, Path]]) -> None:
    print("Resolved input files (in execution order):")
    for deck, out_dir in plan:
        print(f"  {deck}")
        print(f"      -> output: {out_dir}")
    print()


def _print_summary(results: list[tuple[Path, bool, float, str]]) -> int:
    name_w = max([len(p.name) for p, *_ in results] + [len("input")])
    line = "=" * (name_w + 34)
    print(line)
    print(f"{'input':<{name_w}}  {'result':<6}  {'runtime':>9}  notes")
    print("-" * (name_w + 34))
    n_fail = 0
    for path, ok, elapsed, message in results:
        if not ok:
            n_fail += 1
        status = "PASS" if ok else "FAIL"
        note = "" if ok else message
        print(f"{path.name:<{name_w}}  {status:<6}  {_fmt_runtime(elapsed):>9}  {note}")
    print(line)
    print(f"{len(results) - n_fail}/{len(results)} passed")
    return n_fail


def _do_check_config(config_path, inputs: list[Path]) -> int:
    checks, ok = preflight(config_path, inputs)
    name_w = max(len(c.name) for c in checks)
    print("Preflight (--check-config): no solver is executed.\n")
    for c in checks:
        if not c.required and c.ok:
            mark = "info"
        else:
            mark = "PASS" if c.ok else "FAIL"
        print(f"  [{mark:<4}] {c.name:<{name_w}}  {c.detail}")
    print()
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def _do_dry_run(plan: list[tuple[Path, Path]]) -> int:
    """Print the plan and validate each deck loads, without executing."""
    print("Dry run (--dry-run): decks are loaded/validated but NOT executed.\n")
    try:
        import nextnanopy as nn
    except Exception as exc:  # noqa: BLE001
        print(
            f"  note: nextnanopy not importable ({exc}); skipping load validation. "
            "Planning only."
        )
        return 0

    n_fail = 0
    for deck, _out_dir in plan:
        try:
            inp = nn.InputFile(str(deck))
            print(f"  [OK  ] loaded {deck.name}  (product={inp.product})")
        except Exception as exc:  # noqa: BLE001
            n_fail += 1
            print(f"  [FAIL] could not load {deck.name}: {type(exc).__name__}: {exc}")
    print()
    print(f"RESULT: {'PASS' if n_fail == 0 else 'FAIL'} (no execution performed)")
    return 1 if n_fail else 0


def _validate_runtime_paths(cfg) -> list[str]:
    """Existence checks required before a real run (exe/database/license)."""
    errors = []
    if not cfg.exe.is_file():
        errors.append(f"executable not found: {cfg.exe}")
    if not cfg.database.is_file():
        errors.append(f"database not found: {cfg.database}")
    if cfg.license is not None and not cfg.license.is_file():
        errors.append(f"license not found: {cfg.license}")
    return errors


def _do_execute(cfg, plan: list[tuple[Path, Path]]) -> int:
    # Fail fast with a clear message if the machine paths are wrong, before
    # touching nextnanopy or the solver.
    path_errors = _validate_runtime_paths(cfg)
    if path_errors:
        print("ERROR: cannot execute -- fix paths.local.yaml:", file=sys.stderr)
        for err in path_errors:
            print(f"  - {err}", file=sys.stderr)
        print("Run --check-config to re-verify.", file=sys.stderr)
        return 2

    try:
        import nextnanopy as nn
    except Exception as exc:  # noqa: BLE001
        print(
            f"ERROR: execution requires nextnanopy, which could not be imported: {exc}",
            file=sys.stderr,
        )
        return 3

    results: list[tuple[Path, bool, float, str]] = []
    for deck, out_dir in plan:
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"[run ] {deck}  -> {out_dir}")
        start = time.perf_counter()
        try:
            inp = nn.InputFile(str(deck))
            # Pass all paths as execute kwargs so nextnanopy's global config is
            # never consulted or written; each deck gets its own output dir.
            inp.execute(**cfg.execute_kwargs(outputdirectory=out_dir))
            ok, message = True, "ok"
        except Exception as exc:  # noqa: BLE001 - keep summary alive
            traceback.print_exc()
            ok, message = False, f"{type(exc).__name__}: {exc}"
        elapsed = time.perf_counter() - start
        print(f"[{'PASS' if ok else 'FAIL'}] {deck.name}  ({_fmt_runtime(elapsed)})\n")
        results.append((deck, ok, elapsed, message))

    n_fail = _print_summary(results)
    return 1 if n_fail else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run, dry-run, or preflight nextnano++ input decks.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="One or more .in deck paths. Wildcards (e.g. hello_*.in) are "
        "expanded by this script, so they work in PowerShell and cmd.exe too.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Run preflight checks only; execute nothing. Nonzero exit if any "
        "required check fails.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve config and inputs, print the execution plan, and load "
        "(but do not execute) each deck.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Override the path to paths.local.yaml (default: "
        "nextnano/config/paths.local.yaml). Mainly for testing.",
    )
    args = parser.parse_args(argv)

    # Expand inputs first; an unmatched path/wildcard is always an error.
    try:
        inputs = expand_inputs(args.inputs) if args.inputs else []
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.check_config:
        return _do_check_config(args.config, inputs)

    # dry-run and real execution both need a structurally valid config.
    try:
        cfg = resolve_config(args.config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not inputs:
        print("ERROR: no input files given. Pass one or more .in decks, or use "
              "--check-config.", file=sys.stderr)
        return 2

    plan = build_plan(cfg, inputs)
    _print_plan(plan)

    if args.dry_run:
        return _do_dry_run(plan)

    return _do_execute(cfg, plan)


if __name__ == "__main__":
    sys.exit(main())
