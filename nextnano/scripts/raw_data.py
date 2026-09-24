"""Local raw nextnano++ data store (nextnano_raw/): register, verify, list.

Policy: nextnano/docs/DEMO_WORKFLOW.md section 3. Raw data never go to Git; this
tool only copies, hashes and checks local files.

    python nextnano/scripts/raw_data.py register --demo 23 --run-id D023_2026-09-04_kp8-... \
        --source demo_results/demo23/raw/production_y_n301_k0100 --record meta.json
    python nextnano/scripts/raw_data.py verify nextnano_raw/demo_023/D023_2026-09-04_kp8-...
    python nextnano/scripts/raw_data.py list

``register`` COPIES (never moves) an existing solver-output directory into
``<raw root>/demo_NNN/<run_id>/data/``, checks the copy byte for byte, and writes
``SHA256SUMS.txt`` (sha256sum format, sorted, LF) and ``RUN_RECORD.json``. It refuses
to touch an existing run folder. ``verify`` re-hashes every listed file and reports
missing, changed and unlisted files. Neither command edits anything under ``data/``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_ROOT = REPO_ROOT / "nextnano_raw"
RUN_ID = re.compile(r"^D(?P<demo>\d{3})_(?P<date>\d{4}-\d{2}-\d{2})_(?P<desc>[A-Za-z0-9][A-Za-z0-9.-]*)$")
REQUIRED_RECORD_KEYS = ("date", "machine", "licensed", "solver", "deck", "physics",
                        "structure", "status", "provenance")
STATUSES = ("valid", "failed", "partial", "superseded")


class RawDataError(RuntimeError):
    """A run folder is missing, malformed, or does not match its hashes."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tree_hashes(root: Path, prefix: str = "") -> dict[str, str]:
    """{posix relative path (with prefix): sha256} for every file below root."""
    root = Path(root)
    return {prefix + p.relative_to(root).as_posix(): sha256(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


def write_sums(path: Path, hashes: dict[str, str]) -> None:
    text = "".join(f"{digest}  {name}\n" for name, digest in sorted(hashes.items()))
    Path(path).write_bytes(text.encode("utf-8"))


def read_sums(path: Path) -> dict[str, str]:
    out = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        digest, sep, name = line.partition("  ")
        if not sep or not re.fullmatch(r"[0-9a-f]{64}", digest) or not name:
            raise RawDataError(f"{path}:{n}: not a sha256sum line")
        out[name] = digest
    return out


def run_folder(raw_root: Path, run_id: str) -> Path:
    m = RUN_ID.match(run_id)
    if not m:
        raise RawDataError(f"run ID {run_id!r} does not match D<NNN>_<YYYY-MM-DD>_<descriptor>")
    return Path(raw_root) / f"demo_{m['demo']}" / run_id


def git_provenance(source: Path) -> dict:
    """Commit and cleanliness of a source path inside this repository (best effort)."""
    try:
        rel = Path(source).resolve().relative_to(REPO_ROOT)
    except ValueError:
        return {"inside_repository": False}
    def git(*args):
        return subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True,
                              text=True, check=False).stdout.strip()
    tracked = git("ls-files", "--", rel.as_posix())
    return {"inside_repository": True, "source_path": rel.as_posix(),
            "head_commit": git("rev-parse", "HEAD"),
            "last_commit_touching_source": git("log", "-1", "--format=%H", "--", rel.as_posix()),
            "source_tracked_files": len(tracked.splitlines()) if tracked else 0,
            "source_uncommitted_changes": bool(git("status", "--porcelain", "--", rel.as_posix()))}


def register(demo: int, run_id: str, source: Path, record: dict, raw_root: Path = DEFAULT_RAW_ROOT) -> Path:
    m = RUN_ID.match(run_id)
    if not m or int(m["demo"]) != int(demo):
        raise RawDataError(f"run ID {run_id!r} must start with D{int(demo):03d}_")
    missing = [k for k in REQUIRED_RECORD_KEYS if k not in record]
    if missing:
        raise RawDataError(f"record lacks required keys {missing}")
    if record["date"] != m["date"]:
        raise RawDataError(f"record date {record['date']} differs from run-ID date {m['date']}")
    if record["status"] not in STATUSES:
        raise RawDataError(f"status must be one of {STATUSES}")
    source = Path(source)
    if not source.is_dir():
        raise RawDataError(f"source directory not found: {source}")
    target = run_folder(raw_root, run_id)
    if target.exists():
        raise RawDataError(f"refusing to overwrite existing run folder {target}")
    deck = record["deck"].get("path") if isinstance(record["deck"], dict) else None
    if not deck or not (source / Path(deck).relative_to("data")).is_file():
        raise RawDataError(f"deck {deck!r} (path under data/) not found in the source")
    source_hashes = tree_hashes(source, "data/")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(target.name + ".partial")
    if staging.exists():
        raise RawDataError(f"leftover staging folder {staging}; inspect and remove it first")
    try:
        shutil.copytree(source, staging / "data")
        copied = tree_hashes(staging / "data", "data/")
        if copied != source_hashes:
            raise RawDataError("copy is not byte-identical to the source")
        write_sums(staging / "SHA256SUMS.txt", copied)
        full = {"run_id": run_id, "originating_demo": int(demo), **record}
        full["deck"] = {**record["deck"], "sha256": copied[deck]}
        full["files"] = {"count": len(copied),
                         "total_bytes": sum(p.stat().st_size for p in (staging / "data").rglob("*") if p.is_file())}
        full["sha256sums_sha256"] = sha256(staging / "SHA256SUMS.txt")
        full["registration"] = {"registered_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "tool": "nextnano/scripts/raw_data.py register",
                                "source": str(source.resolve()), "git": git_provenance(source)}
        (staging / "RUN_RECORD.json").write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return target


def verify(folder: Path) -> dict:
    """Check RUN_RECORD.json and every SHA256SUMS.txt entry of one run folder."""
    folder = Path(folder)
    problems = []
    record_path, sums_path = folder / "RUN_RECORD.json", folder / "SHA256SUMS.txt"
    if not record_path.is_file() or not sums_path.is_file():
        raise RawDataError(f"{folder} lacks RUN_RECORD.json or SHA256SUMS.txt")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("run_id") != folder.name:
        problems.append(f"RUN_RECORD run_id {record.get('run_id')!r} differs from folder name")
    listed = read_sums(sums_path)
    for name, digest in listed.items():
        path = folder / name
        if not path.is_file():
            problems.append(f"missing: {name}")
        elif sha256(path) != digest:
            problems.append(f"changed: {name}")
    present = set(tree_hashes(folder / "data", "data/")) if (folder / "data").is_dir() else set()
    problems += [f"unlisted: {name}" for name in sorted(present - set(listed))]
    if record.get("sha256sums_sha256") and sha256(sums_path) != record["sha256sums_sha256"]:
        problems.append("SHA256SUMS.txt differs from the digest recorded in RUN_RECORD.json")
    return {"run_id": folder.name, "status": record.get("status"), "files": len(listed),
            "result": "PASS" if not problems else "FAIL", "problems": problems}


def runs(raw_root: Path = DEFAULT_RAW_ROOT) -> list[dict]:
    out = []
    for record_path in sorted(Path(raw_root).glob("demo_*/D*/RUN_RECORD.json")):
        r = json.loads(record_path.read_text(encoding="utf-8"))
        phys = r.get("physics", {})
        out.append({"run_id": r.get("run_id"), "status": r.get("status"), "model": phys.get("model"),
                    "temperature_K": phys.get("temperature_K"), "k_max": phys.get("k_max_label"),
                    "k_points": phys.get("k_points"), "files": r.get("files", {}).get("count")})
    return out


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):  # records contain "π"; Windows consoles default to cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register", help="copy an existing solver-output directory into the store")
    reg.add_argument("--demo", type=int, required=True, help="number of the demo that generated the data")
    reg.add_argument("--run-id", required=True)
    reg.add_argument("--source", type=Path, required=True)
    reg.add_argument("--record", type=Path, required=True, help="JSON file with the RUN_RECORD metadata")
    ver = sub.add_parser("verify", help="re-check a run folder against SHA256SUMS.txt")
    ver.add_argument("folder", type=Path)
    sub.add_parser("list", help="list run folders on this machine")
    args = parser.parse_args(argv)
    try:
        if args.command == "register":
            record = json.loads(args.record.read_text(encoding="utf-8"))
            target = register(args.demo, args.run_id, args.source, record, args.raw_root)
            report = verify(target)
            print(f"registered {target} ({report['files']} files): verify {report['result']}")
            return 0 if report["result"] == "PASS" else 1
        if args.command == "verify":
            report = verify(args.folder)
            print(f"{report['run_id']}: {report['result']} ({report['files']} files, status {report['status']})")
            for problem in report["problems"]:
                print("  " + problem)
            return 0 if report["result"] == "PASS" else 1
        rows = runs(args.raw_root)
        if not rows:
            print(f"no run folders under {args.raw_root}")
        for row in rows:
            print(f"{row['run_id']}  [{row['status']}]  {row['model']}; T={row['temperature_K']} K; "
                  f"k_max={row['k_max']}; k points={row['k_points']}; files={row['files']}")
        return 0
    except (RawDataError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
