"""Copy a small, selected slice of raw solver output out of an experiment.

Why this exists: the v3 results package carried tables, figures, the Ax snapshot
and the trial ledger, but **no raw solver output** -- no generated ``case.in``,
no execution logs, and no native alloy-composition profiles.  Five trials are
recorded as genuinely graded, and not one of them has ever had its *realized*
grading profile checked against what was requested.  Every statement about the
shape of a graded interface currently rests on arithmetic, not on solver output.

Copying the whole solver tree is not the answer: nextnano++ writes a deep
per-bias output hierarchy per trial and the total is large.  This copies only
the categories asked for, only for the trials asked for, and writes a manifest
that names what it copied **and what it could not find**, because a bundle that
silently omits the alloy profiles is how the gap arose in the first place.

It is strictly read-only with respect to the experiment: it opens nothing for
writing under the source directory, and refuses to write into a non-empty
destination without ``--overwrite``.

    python bundle_raw_trials.py --experiment demo13_ax_experiment_v3 --dry-run
    python bundle_raw_trials.py --experiment demo13_ax_experiment_v3
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_ID = "13_ax_bayesian_optimization_graded_acqw"
DEFAULT_RESULTS_ROOT = REPO_ROOT / "nextnano" / "results" / "demo_runs" / DEMO_ID

#: What each category means, and how its files are recognised inside a trial's
#: run directory. Globs are matched recursively.
CATEGORIES: Mapping[str, tuple[str, ...]] = {
    "inputs": ("*.in", "**/*.in"),
    "logs": ("*.log", "console*.log", "**/*.log"),
    "resolved-config": ("demo_resolved.yaml", "**/demo_resolved.yaml"),
    # The reason this script exists. nextnano++ names alloy output variously, so
    # match broadly rather than miss it.
    "alloy-profiles": (
        "**/*alloy*", "**/*composition*", "extracted/requested_composition_profile.csv",
    ),
    "extracted": ("extracted/*",),
}

#: Copied unless the caller says otherwise. Deliberately excludes the full raw
#: output tree.
DEFAULT_CATEGORIES: tuple[str, ...] = (
    "inputs", "logs", "resolved-config", "alloy-profiles", "extracted",
)

#: Trials worth having raw output for, beyond whatever the caller names:
#: the best feasible design, the near-feasible boundary case, the second
#: feasible design and the feasible Sobol reference.
PRIORITY_TRIALS: tuple[str, ...] = ("t0021", "t0022", "t0017", "t0005")

MAX_REASONABLE_BYTES = 500 * 1024 * 1024


class BundleError(RuntimeError):
    """Raised when the request cannot be satisfied safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def genuinely_graded_trials(state_dir: Path) -> list[str]:
    """Completed trials whose *realized* grade exceeded zero.

    Read from the immutable ledger, so a proposal that was refused -- or one
    that collapsed to abrupt -- is never included. Those built no grade, and
    their raw output cannot verify a grading profile.
    """

    ledger = Path(state_dir) / "trial_ledger.jsonl"
    if not ledger.is_file():
        return []
    latest: dict[int, dict[str, Any]] = {}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            latest[int(record["trial_index"])] = record
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    graded: list[str] = []
    for index, record in sorted(latest.items()):
        if str(record.get("status")) != "completed":
            continue
        canonical = record.get("canonical_parameters") or {}
        try:
            realized = float(
                canonical.get("grading_thickness_nm",
                              record.get("parameter_grading_thickness_nm", 0.0)) or 0.0
            )
        except (TypeError, ValueError):
            continue
        if realized > 0.0:
            graded.append(str(record.get("candidate_id") or f"t{index:04d}"))
    return graded


def _matches(run_dir: Path, categories: Iterable[str]) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = {}
    for category in categories:
        patterns = CATEGORIES.get(category)
        if patterns is None:
            raise BundleError(
                f"unknown category {category!r}; expected one of "
                f"{sorted(CATEGORIES)} or 'all'"
            )
        hits: list[Path] = []
        for pattern in patterns:
            hits.extend(p for p in run_dir.glob(pattern) if p.is_file())
        # Deduplicate while keeping a stable order.
        seen: set[Path] = set()
        found[category] = [p for p in sorted(hits) if not (p in seen or seen.add(p))]
    return found


def build_bundle(
    state_dir: Path,
    out_dir: Path,
    trials: Sequence[str],
    categories: Sequence[str],
    *,
    dry_run: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Copy the requested categories for the requested trials, and say what was missing."""

    state_dir, out_dir = Path(state_dir), Path(out_dir)
    if not state_dir.is_dir():
        raise BundleError(f"experiment directory does not exist: {state_dir}")
    runs_root = state_dir / "runs"
    if out_dir.exists() and any(out_dir.iterdir()) and not overwrite and not dry_run:
        raise BundleError(
            f"{out_dir} already exists and is not empty; pass --overwrite to replace it"
        )

    manifest: dict[str, Any] = {
        "source_experiment": str(state_dir),
        "destination": str(out_dir),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dry_run": bool(dry_run),
        "categories_requested": list(categories),
        "trials_requested": list(trials),
        "runs_directory_present": runs_root.is_dir(),
        "trials": {},
        "unavailable": [],
        "total_files": 0,
        "total_bytes": 0,
        "source_modified": False,
    }
    if not runs_root.is_dir():
        manifest["unavailable"].append(
            {
                "what": "runs/",
                "reason": (
                    "this experiment directory contains no raw solver output. A "
                    "results bundle does not include it; run this on the machine "
                    "that executed the campaign."
                ),
            }
        )
        return manifest

    for trial in trials:
        run_dir = runs_root / trial
        if not run_dir.is_dir():
            manifest["unavailable"].append(
                {"what": trial, "reason": f"no run directory at {run_dir}"}
            )
            continue
        found = _matches(run_dir, categories)
        entry: dict[str, Any] = {"files": [], "empty_categories": []}
        for category, paths in found.items():
            if not paths:
                entry["empty_categories"].append(category)
                manifest["unavailable"].append(
                    {
                        "what": f"{trial}/{category}",
                        "reason": "no file in this trial matched the category patterns",
                    }
                )
                continue
            for source in paths:
                relative = source.relative_to(run_dir)
                target = out_dir / trial / relative
                size = source.stat().st_size
                record = {
                    "category": category,
                    "relative_path": relative.as_posix(),
                    "bytes": size,
                }
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    record["sha256"] = _sha256(target)
                entry["files"].append(record)
                manifest["total_files"] += 1
                manifest["total_bytes"] += size
        manifest["trials"][trial] = entry

    if manifest["total_bytes"] > MAX_REASONABLE_BYTES:
        manifest["size_warning"] = (
            f"{manifest['total_bytes'] / 1e6:.0f} MB selected. That is far larger "
            "than a supplemental bundle should be; narrow --include."
        )
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "raw_bundle_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return manifest


def resolve_trials(state_dir: Path, requested: Sequence[str] | None) -> list[str]:
    """Explicit trials if given, else the priority set plus every graded trial."""

    if requested:
        return list(dict.fromkeys(requested))
    graded = genuinely_graded_trials(state_dir)
    return list(dict.fromkeys(list(PRIORITY_TRIALS) + graded))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--experiment", required=True,
                        help="experiment state directory name under the results root")
    parser.add_argument("--results-root", default=str(DEFAULT_RESULTS_ROOT))
    parser.add_argument("--trials", nargs="*", default=None,
                        help="trial ids; default is the priority set plus every "
                             "genuinely graded trial")
    parser.add_argument("--include", nargs="*", default=list(DEFAULT_CATEGORIES),
                        help=f"categories: {sorted(CATEGORIES)} or 'all'")
    parser.add_argument("--out", default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be copied; write nothing")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="required with --include all, which copies the entire "
                             "raw output tree")
    args = parser.parse_args(argv)

    categories = list(args.include)
    if "all" in categories:
        if not args.force:
            parser.error(
                "--include all copies the entire raw solver tree, which is very "
                "large. Pass --force if that is genuinely what you want."
            )
        categories = list(CATEGORIES)

    results_root = Path(args.results_root)
    state_dir = results_root / args.experiment
    out_dir = Path(args.out) if args.out else (
        REPO_ROOT / "nextnano" / "results" / "transfer" / f"{args.experiment}_raw_supplement"
    )

    try:
        trials = resolve_trials(state_dir, args.trials)
        manifest = build_bundle(
            state_dir, out_dir, trials, categories,
            dry_run=args.dry_run, overwrite=args.overwrite,
        )
    except BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    verb = "would copy" if args.dry_run else "copied"
    print(f"source     : {state_dir}")
    print(f"destination: {out_dir}")
    print(f"trials     : {', '.join(trials)}")
    print(f"categories : {', '.join(categories)}")
    print(f"{verb:11}: {manifest['total_files']} files, "
          f"{manifest['total_bytes'] / 1e6:.2f} MB")
    for item in manifest["unavailable"]:
        print(f"  UNAVAILABLE {item['what']}: {item['reason']}")
    if manifest.get("size_warning"):
        print(f"  WARNING {manifest['size_warning']}")
    if args.dry_run:
        print("dry run: nothing was written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
