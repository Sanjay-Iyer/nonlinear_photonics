"""Live progress monitor for a running Demo 22 Professional solve.

Run this in a second terminal while ``run_demo22.py --physics`` works. It never
touches the run: it only reads directory listings below the results root.

The solver's stdout is buffered by ``solver14.execute_real`` until a deck exits,
so the log is useless while a deck is running. nextnano++ does write one set of
``*_kNNNNN.*`` files per k point as it goes, so the highest k index present on
disk is the progress counter used here.

Standard library only, so it runs under any Python on the work laptop.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import deque
from pathlib import Path

K_INDEX_RE = re.compile(r"_k(\d+)", re.I)

# Deck order is fixed by deck22.write_decks: the four production/control decks
# first, then the integration-convergence probes.
DECK_PLAN = (
    ("abrupt_integration", "integration", 96),
    ("abrupt_dispersion", "dispersion", 301),
    ("linear_1nm_integration", "integration", 96),
    ("linear_1nm_dispersion", "dispersion", 301),
    ("abrupt_integration_k048", "integration", 48),
    ("abrupt_integration_k072", "integration", 72),
)

# nextnano++ documents that the number of Schroedinger solves grows
# quadratically with num_points in 1D, but not the constant. c=1 is a
# placeholder; the monitor overwrites it the moment a real deck finishes.
DEFAULT_C = 1.0


def deck_k_total(kind: str, points: int, c: float) -> int:
    return points if kind == "dispersion" else max(1, round(c * points * points))


def find_run_root(results_root: Path, explicit: Path | None) -> Path:
    if explicit:
        return explicit
    runs = sorted((p for p in results_root.glob("demo22_*") if p.is_dir()),
                  key=lambda p: p.stat().st_mtime)
    if not runs:
        raise SystemExit(f"no demo22_* run directory under {results_root}")
    return runs[-1]


class DeckScanner:
    """Finds the flat directories holding *_kNNNNN.* files, then rescans only those.

    A full rglob over a finished deck means walking ~600k files, which is slow
    enough to matter when polling. The directory set is discovered once and
    cached; new directories are picked up on a slow re-discovery cycle.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.dirs: list[Path] = []
        self._last_discovery = 0.0

    def _discover(self) -> None:
        found = []
        for dirpath, _dirnames, filenames in os.walk(self.root):
            if any(K_INDEX_RE.search(name) for name in filenames[:50]):
                found.append(Path(dirpath))
        self.dirs = found
        self._last_discovery = time.monotonic()

    def scan(self) -> tuple[int, int]:
        """Return (highest k index seen + 1, file count) without stat calls."""
        if not self.dirs or time.monotonic() - self._last_discovery > 300:
            self._discover()
        max_k = -1
        files = 0
        for directory in self.dirs:
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if not entry.is_file():
                            continue
                        files += 1
                        match = K_INDEX_RE.search(entry.name)
                        if match:
                            index = int(match.group(1))
                            if index > max_k:
                                max_k = index
            except OSError:
                continue
        return max_k + 1, files


def human_time(seconds: float | None) -> str:
    if seconds is None or seconds != seconds or seconds < 0:
        return "--:--:--"
    seconds = int(seconds)
    return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def bar(fraction: float | None, width: int = 26) -> str:
    if fraction is None:
        return "?" * width
    fraction = min(max(fraction, 0.0), 1.0)
    filled = int(round(fraction * width))
    return "#" * filled + "." * (width - filled)


def load_calibration(path: Path, default: float) -> float:
    try:
        return float(json.loads(path.read_text(encoding="utf-8"))["c"])
    except Exception:
        return default


def save_calibration(path: Path, c: float, evidence: str) -> None:
    try:
        path.write_text(json.dumps({"c": c, "evidence": evidence}, indent=2),
                        encoding="utf-8")
    except OSError:
        pass


def render(rows, history, c, calibrated, run_root, elapsed, files_all, bytes_all,
           totals_done, totals_all, active, deck_timeout):
    out = []
    flag = "" if calibrated else " (provisional)"
    out.append(f"Demo 22 - {run_root.name}    elapsed {human_time(elapsed)}"
               f"    c={c:.3f}{flag}")
    out.append("")
    for index, (name, kind, points, done, files, _size, total) in enumerate(rows, 1):
        if done is None:
            out.append(f"[{index}/6] {name:<26} {bar(0.0)}   queued")
            continue
        fraction = min(done / total, 1.0) if total else None
        samples = history[name]
        rate = None
        if len(samples) >= 2:
            span = samples[-1][0] - samples[0][0]
            grew = samples[-1][1] - samples[0][1]
            if span > 0 and grew > 0:
                rate = grew / span
        eta = ((total - done) / rate) if (rate and total and done < total) else None
        rate_text = f"{rate:6.2f} k/s" if rate else "     -    "
        percent = (fraction * 100) if fraction is not None else 0.0
        out.append(
            f"[{index}/6] {name:<26} {bar(fraction)} {percent:5.1f}%"
            f"  {done:>7,} / {total:>7,} k  {rate_text}  ETA {human_time(eta)}"
        )

    overall = totals_done / totals_all if totals_all else 0.0
    run_rate = totals_done / elapsed if elapsed > 0 else 0.0
    run_eta = ((totals_all - totals_done) / run_rate) if run_rate > 0 else None
    out.append("")
    out.append(f"overall {bar(overall)} {overall * 100:5.1f}%"
               f"   {totals_done:>8,.0f} / {totals_all:>8,.0f} k   ETA {human_time(run_eta)}")
    out.append(f"output  {files_all:,} files observed")

    if active:
        name, kind, points, _done = active
        samples = history[name]
        if len(samples) >= 2:
            span = samples[-1][0] - samples[0][0]
            grew = samples[-1][1] - samples[0][1]
            total = deck_k_total(kind, points, c)
            if span > 0 and grew > 0:
                projected = total / (grew / span)
                if projected > deck_timeout:
                    out.append(
                        f"WARNING {name} projects {human_time(projected)} "
                        f"> {human_time(deck_timeout)} per-deck timeout - it will be killed"
                    )
    return out, overall, run_eta


def poll_once(raw_root, scanners, history, now):
    """Scan every deck directory. Totals are deliberately not computed here.

    The quadratic constant can be learned from this very poll, so totals are
    derived afterwards in tally() -- otherwise the first frame after
    calibration reports a new c against stale per-deck totals.
    """
    scanned = []
    files_all = 0
    bytes_all = 0
    for name, kind, points in DECK_PLAN:
        if not (raw_root / name).is_dir():
            scanned.append((name, kind, points, None, 0, 0))
            continue
        done, files = scanners[name].scan()
        size = 0
        files_all += files
        bytes_all += size
        history[name].append((now, done))
        scanned.append((name, kind, points, done, files, size))
    return scanned, files_all, bytes_all


def tally(scanned, c):
    rows = []
    totals_done = 0.0
    totals_all = 0.0
    for name, kind, points, done, files, size in scanned:
        total = deck_k_total(kind, points, c)
        totals_all += total
        if done is not None:
            totals_done += min(done, total)
        rows.append((name, kind, points, done, files, size, total))
    return rows, totals_done, totals_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path,
                        default=Path("demo_results/demo22"),
                        help="directory holding demo22_<stamp> run folders")
    parser.add_argument("--run", type=Path, help="explicit demo22_<stamp> directory")
    parser.add_argument("--interval", type=float, default=30.0,
                        help="seconds between polls (default 30)")
    parser.add_argument("--c", type=float, default=None,
                        help="k points per num_points^2; learned from a finished deck if omitted")
    parser.add_argument("--deck-timeout", type=float, default=14400.0,
                        help="solver.timeout_seconds_per_deck, for the overrun warning")
    parser.add_argument("--plain", action="store_true",
                        help="append each frame instead of redrawing in place (for logging)")
    parser.add_argument("--once", action="store_true",
                        help="print a single snapshot and exit")
    parser.add_argument("--embedded", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    run_root = find_run_root(args.results_root, args.run)
    raw_root = run_root / "raw"
    calib_path = run_root / "progress_calibration.json"
    c = args.c if args.c is not None else load_calibration(calib_path, DEFAULT_C)
    calibrated = args.c is not None or calib_path.is_file()

    scanners = {name: DeckScanner(raw_root / name) for name, _, _ in DECK_PLAN}
    history: dict[str, deque] = {name: deque(maxlen=12) for name, _, _ in DECK_PLAN}
    start = time.monotonic()
    live = not args.plain and sys.stdout.isatty() and not args.once
    lines_drawn = 0

    print(f"watching {run_root}")
    if args.embedded:
        print(f"poll every {args.interval:.0f}s   Ctrl+C stops the Demo 22 run\n")
    else:
        print(f"poll every {args.interval:.0f}s   Ctrl+C stops only this tracker\n")

    while True:
        now = time.monotonic()
        scanned, files_all, bytes_all = poll_once(raw_root, scanners, history, now)

        active = None
        for name, kind, points, done, _f, _s in scanned:
            if done:
                active = (name, kind, points, done)

        # A deck is finished once a later deck has started producing files. Its
        # observed k count is ground truth for the quadratic constant.
        if not calibrated:
            producing = [row for row in scanned if row[3]]
            if len(producing) >= 2:
                name, kind, points, done = producing[-2][:4]
                if kind == "integration" and done > 0:
                    c = done / float(points * points)
                    calibrated = True
                    save_calibration(calib_path, c,
                                     f"{name}: {done} k at num_points={points}")

        rows, totals_done, totals_all = tally(scanned, c)

        out, _overall, _eta = render(
            rows, history, c, calibrated, run_root, now - start,
            files_all, bytes_all, totals_done, totals_all, active, args.deck_timeout)

        if live:
            if lines_drawn:
                sys.stdout.write(f"\x1b[{lines_drawn}A")
            for line in out:
                sys.stdout.write("\x1b[2K" + line + "\n")
            sys.stdout.flush()
            lines_drawn = len(out)
        else:
            for line in out:
                print(line)
            print("", flush=True)

        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nstopped watching (the solve is unaffected)")
        raise SystemExit(0)
