"""Find and verify the raw nextnano++ runs pinned in inputs/raw_data.lock.json.

Selection is explicit: ``<raw root>/<expected_dir>`` for each locked run, where the raw
root is the ``--raw-root`` argument, else ``NEXTNANO_RAW_ROOT``, else
``<repo>/nextnano_raw``. The run record, the deck and every pinned file are hashed
before anything is parsed. This module only reads; it never writes to a raw folder.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

from .paths import DEFAULT_RAW_ROOT, DEMO_ROOT, LOCK

ENV_VAR = "NEXTNANO_RAW_ROOT"


class RawDataMissing(RuntimeError):
    """A locked run folder is not present in the raw store."""


class RawDataMismatch(RuntimeError):
    """A locked run folder exists but differs from the lock (hash, ID or status)."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_lock(path: Path = LOCK) -> dict:
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    if lock.get("schema") != 1 or not isinstance(lock.get("runs"), dict):
        raise ValueError(f"{path}: unsupported lock format")
    return lock


def raw_root(cli: str | Path | None = None) -> tuple[Path, str]:
    """(raw store, how it was chosen): --raw-root > NEXTNANO_RAW_ROOT > default."""
    if cli:
        return Path(cli), "--raw-root"
    if os.environ.get(ENV_VAR):
        return Path(os.environ[ENV_VAR]), ENV_VAR
    return DEFAULT_RAW_ROOT, "default <repository>/nextnano_raw"


@dataclass(frozen=True)
class ResolvedRun:
    role: str
    run_id: str
    folder: Path       # the run folder: RUN_RECORD.json, SHA256SUMS.txt, data/
    parser_root: Path  # the folder handed to the parsers
    entry: dict        # the lock entry
    verified_files: int


def _missing_message(role: str, entry: dict, folder: Path, base: Path, how: str) -> str:
    demo_dir = entry["expected_dir"].split("/")[0]
    lines = [f"Raw dataset not found for '{role}': {entry['run_id']}",
             f"  {entry.get('model', '')}; {entry.get('k_max', '')}; {entry.get('temperature_K')} K",
             f"  expected folder: {folder}",
             f"  raw store:       {base}  ({how})",
             "To fix, EITHER",
             f"  (a) download {entry['run_id']}.zip from Google Drive (folder nextnano_raw/{demo_dir}/),",
             f"      unzip it into {base / demo_dir}, then verify it with",
             f"      python nextnano/scripts/raw_data.py verify \"{folder}\""]
    if entry.get("historical_source"):
        record = DEMO_ROOT / entry["registration_record"]
        lines += ["  (b) re-register the historical copy that is tracked in this repository:",
                  f"      python nextnano/scripts/raw_data.py register --demo {entry['originating_demo']} "
                  f"--run-id {entry['run_id']} --source {entry['historical_source']} --record \"{record}\""]
    lines.append(f"Or point Demo 30 at another raw store with --raw-root DIR or {ENV_VAR}.")
    return "\n".join(lines)


def resolve(role: str, lock: dict | None = None, root: str | Path | None = None,
            allowed_status: tuple[str, ...] = ("valid",)) -> ResolvedRun:
    """Locate one locked run and verify it; raise with instructions if it is not usable."""
    lock = lock or load_lock()
    if role not in lock["runs"]:
        raise KeyError(f"role {role!r} is not in the lock file")
    entry = lock["runs"][role]
    base, how = raw_root(root)
    folder = base / entry["expected_dir"]
    if not folder.is_dir():
        raise RawDataMissing(_missing_message(role, entry, folder, base, how))
    record_path = folder / "RUN_RECORD.json"
    if not record_path.is_file():
        raise RawDataMismatch(f"{folder} has no RUN_RECORD.json; it is not a registered run folder")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    problems = []
    if record.get("run_id") != entry["run_id"]:
        problems.append(f"RUN_RECORD run_id {record.get('run_id')!r} != locked {entry['run_id']!r}")
    for status in (record.get("status"), entry.get("status")):
        if status not in allowed_status:
            problems.append(f"status {status!r} is not in {allowed_status}")
    pinned = {entry["deck"]["path"]: entry["deck"]["sha256"], **entry["files"]}
    for rel, digest in pinned.items():
        path = folder / rel
        if not path.is_file():
            problems.append(f"missing file: {rel}")
        elif sha256(path) != digest:
            problems.append(f"hash differs from lock: {rel}")
    sums = folder / "SHA256SUMS.txt"
    if entry.get("sha256sums_sha256") and (not sums.is_file() or sha256(sums) != entry["sha256sums_sha256"]):
        problems.append("SHA256SUMS.txt is missing or differs from the locked digest (a different package)")
    if problems:
        raise RawDataMismatch(f"Raw dataset {entry['run_id']} at {folder} does not match the lock:\n  "
                              + "\n  ".join(problems))
    return ResolvedRun(role, entry["run_id"], folder, folder / entry["parser_root"], entry, len(pinned))


def resolve_required(root: str | Path | None = None, lock: dict | None = None) -> dict[str, ResolvedRun]:
    """Every run marked required in the lock, verified; missing ones are reported together."""
    lock = lock or load_lock()
    resolved, missing = {}, []
    for role, entry in lock["runs"].items():
        if not entry.get("required"):
            continue
        try:
            resolved[role] = resolve(role, lock, root)
        except RawDataMissing as exc:
            missing.append(str(exc))
    if missing:
        raise RawDataMissing("\n\n".join(missing))
    return resolved


def verify_package(folder: Path) -> dict:
    """Re-hash EVERY file listed in the run folder's SHA256SUMS.txt (not just the pinned ones)."""
    folder = Path(folder)
    problems, listed = [], 0
    for line in (folder / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        listed += 1
        path = folder / name
        if not path.is_file():
            problems.append(f"missing: {name}")
        elif sha256(path) != digest:
            problems.append(f"changed: {name}")
    return {"files_listed": listed, "problems": problems, "result": "PASS" if not problems else "FAIL"}


def provenance(runs: dict[str, ResolvedRun]) -> dict:
    """Compact record of which raw data an output was computed from."""
    return {role: {"run_id": r.run_id, "folder": str(r.folder), "verified_files": r.verified_files,
                   "sha256sums_sha256": r.entry.get("sha256sums_sha256"),
                   "deck_sha256": r.entry["deck"]["sha256"]} for role, r in runs.items()}
