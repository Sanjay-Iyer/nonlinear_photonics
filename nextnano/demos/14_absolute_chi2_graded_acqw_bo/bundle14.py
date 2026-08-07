"""Demo 14 debug bundle: everything an analyst needs, in one uploadable zip.

The bundle is text-sized evidence only. Raw solver trees can be hundreds of
megabytes, so they are represented by an inventory with sizes and hashes, and a
second archive carries them in full when it is actually wanted. What is *not*
included is stated explicitly in ``CONTENTS.md`` -- an omission a reader cannot
see is indistinguishable from evidence that never existed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
import zipfile

import runlog14

#: Files copied verbatim, relative to the run root. Globs are expanded.
TEXT_PATTERNS = (
    "README_RUN.md",
    "RUN_STATUS.json",
    "manifest.json",
    "resolved_config.yaml",
    "logs/*.log",
    "logs/*.jsonl",
    "logs/*.txt",
    "environment/*",
    "optimization/*.json",
    "optimization/*.jsonl",
    "optimization/*.csv",
    "summaries/*",
    "validation/**/*",
    "plots/*.json",
    "trials/*/trial_manifest.json",
    "trials/*/trial_result.json",
    "trials/*/preflight.json",
    "trials/*/parameters_requested.yaml",
    "trials/*/parameters_realized.yaml",
    "trials/*/grading_profile_metadata.json",
    "trials/*/grading_profile.csv",
    "trials/*/physics/*.json",
    "trials/*/physics/*.csv",
    "trials/*/qc/*.json",
    "trials/*/parsed/*.json",
    "trials/*/logs/*.txt",
    "trials/*/nextnano_input/*.in",
    "trials/*/nextnano_input/*.dat",
)

#: Never copied verbatim; inventoried instead.
RAW_PATTERNS = ("trials/*/nextnano_output/**/*",)

#: A single file larger than this is inventoried rather than copied, so one
#: unexpectedly large artifact cannot make the bundle unusable.
MAX_EMBEDDED_BYTES = 4 * 1024 * 1024


def _iter_matches(root: Path, patterns: Iterable[str]) -> list[Path]:
    seen: dict[Path, None] = {}
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                seen.setdefault(path, None)
    return list(seen)


def raw_inventory(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in _iter_matches(root, RAW_PATTERNS):
        try:
            stat = path.stat()
            rows.append({
                "relative_path": str(path.relative_to(root)).replace("\\", "/"),
                "size_bytes": stat.st_size,
                "modified_utc": runlog14._dt.datetime.fromtimestamp(
                    stat.st_mtime, runlog14._dt.timezone.utc
                ).isoformat(),
                "sha256": runlog14.sha256_file(path) if stat.st_size <= MAX_EMBEDDED_BYTES
                else None,
            })
        except OSError:
            continue
    return rows


def build_debug_bundle(run_root: Path, *, output: Path | None = None) -> Path:
    """Create ``debug_bundle/demo14_<run_id>_debug_bundle.zip``."""

    run_root = Path(run_root)
    manifest_path = run_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    run_id = manifest.get("run_id", run_root.name)
    mock = bool(manifest.get("mode") == "mock" or manifest.get("scientific_valid") is False)
    prefix = "demo14MOCK" if mock else "demo14"
    target = Path(output) if output else (
        run_root / "debug_bundle" / f"{prefix}_{run_id}_debug_bundle.zip"
    )
    target.parent.mkdir(parents=True, exist_ok=True)

    included = _iter_matches(run_root, TEXT_PATTERNS)
    embedded: list[str] = []
    oversized: list[dict[str, Any]] = []
    inventory = raw_inventory(run_root)

    contents = _contents_markdown(run_id, mock, included, inventory, run_root)
    runlog14.write_text_atomic(run_root / "debug_bundle" / "CONTENTS.md", contents)

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in included:
            relative = str(path.relative_to(run_root)).replace("\\", "/")
            if path.stat().st_size > MAX_EMBEDDED_BYTES:
                oversized.append({
                    "relative_path": relative, "size_bytes": path.stat().st_size,
                    "sha256": runlog14.sha256_file(path),
                })
                continue
            archive.write(path, arcname=relative)
            embedded.append(relative)
        archive.writestr(
            "raw_output_inventory.json",
            json.dumps({"raw_files": inventory, "oversized_text_files": oversized},
                       indent=2, sort_keys=True),
        )
        archive.writestr("CONTENTS.md", contents)
        archive.writestr(
            "BUNDLE_MANIFEST.json",
            json.dumps({
                "run_id": run_id,
                "mock": mock,
                "scientific_valid": not mock,
                "built_utc": runlog14.utc_now(),
                "embedded_file_count": len(embedded),
                "embedded_files": embedded,
                "raw_files_inventoried": len(inventory),
                "raw_bytes_inventoried": sum(r["size_bytes"] for r in inventory),
                "oversized_text_files": oversized,
            }, indent=2, sort_keys=True),
        )
    return target


def build_full_raw_bundle(run_root: Path, *, output: Path | None = None) -> Path:
    """The optional companion archive holding the complete raw solver tree."""

    run_root = Path(run_root)
    manifest_path = run_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    run_id = manifest.get("run_id", run_root.name)
    target = Path(output) if output else (
        run_root / "debug_bundle" / f"demo14_{run_id}_full_raw_bundle.zip"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in _iter_matches(run_root, RAW_PATTERNS):
            archive.write(path, arcname=str(path.relative_to(run_root)).replace("\\", "/"))
    return target


def _contents_markdown(
    run_id: str, mock: bool, included: list[Path], inventory: list[dict[str, Any]],
    run_root: Path,
) -> str:
    raw_bytes = sum(r["size_bytes"] for r in inventory)
    lines = [
        f"# Demo 14 debug bundle -- {run_id}",
        "",
    ]
    if mock:
        lines += [
            "> **MOCK RUN.** Every number in this bundle came from the deterministic",
            "> mock solver. It exercises the harness and is not physics.",
            "",
        ]
    lines += [
        "## What IS included",
        "",
        "- run manifest, status, resolved configuration (with SHA256)",
        "- every log stream: `run.log`, `run_debug.log`, `warnings.log`, "
        "`errors.log`, `events.jsonl`, `timing.jsonl`",
        "- environment snapshot (packages, git status/log/diff, system info) "
        "with secrets redacted",
        "- the full trial ledger, proposal table and best-so-far table",
        "- Ax experiment snapshot where it serialized",
        "- for every trial: manifest, result, preflight, requested and realized "
        "parameters, grading metadata and profile CSV, chi(2) summary, QC and "
        "constraint records, solver stdout/stderr, tracebacks",
        "- **the exact nextnano++ deck and any imported `.dat` alloy profile "
        "for every trial**",
        "- run summary and, when the campaign stopped early, the failure summary",
        "",
        f"Total text files embedded: {len(included)}",
        "",
        "## What is NOT included",
        "",
        f"- the raw nextnano++ output tree ({len(inventory)} files, "
        f"{raw_bytes / 1e6:.1f} MB). It is inventoried in "
        "`raw_output_inventory.json` with relative path, size and SHA256.",
        "- any file larger than "
        f"{MAX_EMBEDDED_BYTES // (1024 * 1024)} MB, listed under "
        "`oversized_text_files` with its hash.",
        "- environment variables outside the allowlist, and anything whose name "
        "suggests a credential. These read `<redacted>` or `<not recorded>`.",
        "",
        "Run `python run_demo14.py --full-raw-bundle <run_directory>` for the "
        "complete raw tree as a separate archive.",
        "",
        "## Where to start",
        "",
        "1. `summaries/DEMO14_RUN_SUMMARY.md` (or `DEMO14_FAILURE_SUMMARY.md`)",
        "2. `RUN_STATUS.json` for the final state",
        "3. `logs/errors.log` and any `trials/*/logs/traceback.txt`",
        "4. `optimization/trial_ledger.jsonl` for per-trial numbers",
        "5. `trials/<id>/nextnano_input/case.in` for exactly what was solved",
        "",
    ]
    return "\n".join(lines)
