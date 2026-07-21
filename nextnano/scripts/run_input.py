"""Run one or more nextnano++ input decks via nextnanopy.

Usage (on the work laptop, with nextnano Standard installed and
config/paths.local.yaml filled in):

    python run_input.py ../inputs/hello_01_bulk_gaas.in
    python run_input.py ../inputs/hello_*.in

Applies per-machine config, executes each deck, times it, and prints a
pass/fail summary. Exits nonzero if any run fails, so it is CI/script safe.
"""

import argparse
import glob
import sys
import time
import traceback
from pathlib import Path

from nn_config import load_config


def _expand(patterns):
    """Expand each argument as a glob.

    Windows shells (cmd.exe and PowerShell) do NOT expand wildcards for
    native executables, so `run_input.py ../inputs/hello_*.in` would arrive
    as the literal string. Expand here so the documented multi-deck form
    works identically on every platform. A pattern with no magic characters
    is passed through unchanged (so a genuinely-missing plain path still
    reports as not-found rather than vanishing).
    """
    expanded = []
    for pat in patterns:
        pat = str(pat)
        if any(ch in pat for ch in "*?[") and (matches := sorted(glob.glob(pat))):
            expanded.extend(Path(m) for m in matches)
        else:
            expanded.append(Path(pat))
    return expanded


def _run_one(path: Path):
    """Execute a single deck. Returns (ok, seconds, message)."""
    import nextnanopy as nn

    start = time.perf_counter()
    try:
        input_file = nn.InputFile(str(path))
        input_file.execute()
    except Exception as exc:  # noqa: BLE001 - we want the summary to survive
        elapsed = time.perf_counter() - start
        traceback.print_exc()
        return False, elapsed, f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - start
    return True, elapsed, "ok"


def _fmt_runtime(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:6.2f} s"
    m, s = divmod(seconds, 60)
    return f"{int(m):d}m{s:04.1f}s"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run nextnano++ input decks and report pass/fail."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more .in deck paths. Globs (e.g. hello_*.in) are "
        "expanded by this script, so they work even on Windows shells "
        "that don't expand wildcards themselves.",
    )
    args = parser.parse_args(argv)
    inputs = _expand(args.inputs)

    # Fail fast with an actionable message if paths.local.yaml is missing.
    applied = load_config()
    print("nextnano++ config:")
    for k, v in applied.items():
        print(f"  {k:16s} = {v}")
    print()

    results = []
    for path in inputs:
        if not path.is_file():
            print(f"[skip] not found: {path}")
            results.append((path, False, 0.0, "file not found"))
            continue
        print(f"[run ] {path}")
        ok, elapsed, message = _run_one(path)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {path}  ({_fmt_runtime(elapsed)})\n")
        results.append((path, ok, elapsed, message))

    # Summary table.
    name_w = max((len(p.name) for p, *_ in results), default=4)
    name_w = max(name_w, len("input"))
    print("=" * (name_w + 30))
    print(f"{'input':<{name_w}}  {'result':<6}  {'runtime':>9}  notes")
    print("-" * (name_w + 30))
    n_fail = 0
    for path, ok, elapsed, message in results:
        if not ok:
            n_fail += 1
        status = "PASS" if ok else "FAIL"
        note = "" if ok else message
        print(f"{path.name:<{name_w}}  {status:<6}  {_fmt_runtime(elapsed):>9}  {note}")
    print("=" * (name_w + 30))
    total = len(results)
    print(f"{total - n_fail}/{total} passed")

    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
