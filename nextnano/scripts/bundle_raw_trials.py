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

#: Files whose absence makes a downstream check impossible, and the check each
#: one blocks.  Reported per trial whether or not they were found, because the
#: whole point of this bundle is to establish what is *missing*: a manifest that
#: lists only what it copied cannot tell you the alloy profiles never arrived.
REQUIRED_FILES: Mapping[str, str] = {
    "extracted/envelopes.csv": "fixed-anchor state tracking",
    "extracted/electron_states.csv": "electron state energies for tracking",
    "extracted/heavy_hole_states.csv": "heavy-hole state energies for tracking",
    "demo_resolved.yaml": "trial-to-source verification",
}

#: Files that would be useful but that Demo 13 does not emit, listed separately
#: so their absence is reported as *structural* rather than as a solver failure.
#: `requested_composition_profile.csv` is written by ``demo12._write_requested_profile``;
#: Demo 13 analyses every trial with ``demo11.analyse_case``, which does not
#: write it. Reporting it as "required" made every bundle on every machine --
#: including the licensed one -- print a missing-file line that an operator would
#: reasonably read as the solver having failed.
KNOWN_ABSENT_FILES: Mapping[str, str] = {
    "extracted/requested_composition_profile.csv": (
        "not written by Demo 13 (demo11.analyse_case does not emit it); the "
        "realized alloy profile must come from the native solver output instead"
    ),
}

#: Geometry the run directory's resolved config must agree with the ledger on
#: before its files are accepted as that trial's output.
VERIFIED_GEOMETRY: Mapping[str, str] = {
    "scientific.thick_well_nm": "resolved_wide_well_nm",
    "scientific.thin_well_nm": "resolved_narrow_well_nm",
    "scientific.tunnel_barrier_nm": "resolved_central_barrier_nm",
}

GEOMETRY_TOLERANCE_NM = 1e-6

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


def _source_fingerprint(root: Path) -> dict[str, tuple[int, int]]:
    """Path -> (size, mtime_ns) for everything under ``root``.

    Cheap enough to run twice around a copy, and enough to detect any write:
    a new file, a removed one, or a changed one.
    """

    root = Path(root)
    if not root.is_dir():
        return {}
    fingerprint: dict[str, tuple[int, int]] = {}
    for path in sorted(root.rglob("*")):
        try:
            info = path.stat()
        except OSError:
            continue
        fingerprint[str(path)] = (info.st_size, info.st_mtime_ns)
    return fingerprint


def ledger_records(state_dir: Path) -> dict[str, dict[str, Any]]:
    """Latest ledger record per candidate id. Read-only."""

    ledger = Path(state_dir) / "trial_ledger.jsonl"
    if not ledger.is_file():
        return {}
    latest: dict[str, dict[str, Any]] = {}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidate = record.get("candidate_id")
        if candidate:
            latest[str(candidate)] = record
    return latest


def _dotted(mapping: Mapping[str, Any], path: str) -> Any:
    cursor: Any = mapping
    for part in path.split("."):
        if not isinstance(cursor, Mapping) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def verify_trial_source(
    run_dir: Path, record: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Check this run directory really holds *this* trial's output.

    A directory named ``t0021`` is not proof that it contains trial 21: a
    re-run, a partial copy or a rename produces the same name over different
    physics, and a bundle built from the wrong directory would be worse than no
    bundle at all. The resolved geometry is compared against the ledger, which
    is the immutable record of what that trial actually was.
    """

    verdict: dict[str, Any] = {
        "verified": False,
        "reason": "",
        "compared": {},
    }
    if record is None:
        verdict["reason"] = "no ledger record for this trial id"
        return verdict
    config_path = Path(run_dir) / "demo_resolved.yaml"
    if not config_path.is_file():
        verdict["reason"] = f"no demo_resolved.yaml in {run_dir}"
        return verdict
    try:
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover - defensive
        verdict["reason"] = f"unreadable demo_resolved.yaml: {exc}"
        return verdict

    mismatches: list[str] = []
    for dotted, ledger_key in VERIFIED_GEOMETRY.items():
        found = _dotted(config, dotted)
        expected = record.get(ledger_key)
        verdict["compared"][dotted] = {"run_dir": found, "ledger": expected}
        if found is None or expected is None:
            mismatches.append(f"{dotted}: missing on one side")
            continue
        try:
            if abs(float(found) - float(expected)) > GEOMETRY_TOLERANCE_NM:
                mismatches.append(
                    f"{dotted}: run dir {float(found):g} nm vs ledger "
                    f"{float(expected):g} nm"
                )
        except (TypeError, ValueError):
            mismatches.append(f"{dotted}: non-numeric")
    verdict["verified"] = not mismatches
    verdict["reason"] = "; ".join(mismatches) if mismatches else "geometry matches ledger"
    return verdict


def required_file_report(run_dir: Path) -> list[dict[str, Any]]:
    """Presence of every file a downstream check needs, present or not."""

    rows = [
        {
            "relative_path": relative,
            "blocks": blocks,
            "present": (Path(run_dir) / relative).is_file(),
            "expected": True,
        }
        for relative, blocks in REQUIRED_FILES.items()
    ]
    rows += [
        {
            "relative_path": relative,
            "blocks": reason,
            "present": (Path(run_dir) / relative).is_file(),
            "expected": False,
        }
        for relative, reason in KNOWN_ABSENT_FILES.items()
    ]
    return rows


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
        # Measured below, not asserted. As a literal this field published what
        # looked like evidence of read-only behaviour and proved nothing -- a
        # test asserting it would have passed while the script scribbled over
        # the campaign.
        "source_modified": None,
    }
    source_before = _source_fingerprint(runs_root)
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

    records = ledger_records(state_dir)
    for trial in trials:
        run_dir = runs_root / trial
        if not run_dir.is_dir():
            manifest["unavailable"].append(
                {"what": trial, "reason": f"no run directory at {run_dir}"}
            )
            continue
        verification = verify_trial_source(run_dir, records.get(trial))
        required = required_file_report(run_dir)
        for item in required:
            if item["present"] or not item.get("expected", True):
                # A file Demo 13 never writes is not a missing result, and
                # listing it as one reads as a solver failure.
                continue
            manifest["unavailable"].append(
                {
                    "what": f"{trial}/{item['relative_path']}",
                    "reason": f"required for {item['blocks']}",
                }
            )
        if not verification["verified"]:
            manifest["unavailable"].append(
                {
                    "what": f"{trial} (source verification)",
                    "reason": verification["reason"],
                }
            )
        found = _matches(run_dir, categories)
        entry: dict[str, Any] = {
            "files": [],
            "empty_categories": [],
            "source_verification": verification,
            "required_files": required,
        }
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

    manifest["source_modified"] = _source_fingerprint(runs_root) != source_before

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
    for trial, entry in manifest["trials"].items():
        verification = entry.get("source_verification") or {}
        mark = "OK " if verification.get("verified") else "!! "
        print(f"  {mark}{trial} source: {verification.get('reason', 'not checked')}")
    for item in manifest["unavailable"]:
        print(f"  UNAVAILABLE {item['what']}: {item['reason']}")
    if manifest.get("size_warning"):
        print(f"  WARNING {manifest['size_warning']}")
    if args.dry_run:
        print("dry run: nothing was written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
