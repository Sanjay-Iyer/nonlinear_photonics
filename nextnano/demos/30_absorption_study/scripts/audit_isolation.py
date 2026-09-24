"""Isolation audit: run the Demo 30 pipeline while blocking every read outside Demo 30.

Adapted from Demo 28's scripts/audit_dependencies.py (same audit-hook method; see
PROVENANCE.md). Inside the repository, only these may be opened or listed:

    nextnano/demos/30_absorption_study/**                (the demo itself)
    the run folders pinned in inputs/raw_data.lock.json  (under the raw store)

Any other path inside the repository (another demo, demo_results/, docs/, other raw
runs, ...) raises and fails the audit. Paths outside the repository (the Python
installation, temporary folders) are allowed. The audit also checks that every imported
module inside the repository comes from Demo 30, and statically scans demo30/*.py for
imports of other demos' packages.

    <python> nextnano/demos/30_absorption_study/scripts/audit_isolation.py
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import shutil
import sys

DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))

from demo30 import rawdata  # noqa: E402
from demo30.paths import OUTPUTS  # noqa: E402

REPO = DEMO_ROOT.parents[2]
ALLOWED_THIRD_PARTY = {"numpy", "scipy", "matplotlib"}


def norm(path) -> str:
    return str(Path(path).resolve()).casefold()


def inside(p: str, root: str) -> bool:
    return p == root or p.startswith(root + "\\") or p.startswith(root + "/")


def allowed_roots(lock=None) -> list[str]:
    """Demo 30 itself plus exactly the run folders named in the lock (required and optional)."""
    lock = lock or rawdata.load_lock()
    base, _ = rawdata.raw_root(None)
    return [norm(DEMO_ROOT)] + [norm(base / e["expected_dir"]) for e in lock["runs"].values()]


def make_guard(allowed: list[str], blocked: list[str]):
    """Audit hook that raises on any read inside the repository outside the allowed roots."""
    repo = norm(REPO)

    def guard(event, args):
        if event not in ("open", "os.listdir", "os.scandir") or not args or not isinstance(args[0], (str, bytes, Path)):
            return
        raw = args[0].decode() if isinstance(args[0], bytes) else str(args[0])
        p = norm(raw)
        if inside(p, repo) and not any(inside(p, a) for a in allowed):
            blocked.append(p)
            raise RuntimeError(f"Demo 30 isolation: forbidden read of {raw}")
    return guard


def main(argv=None) -> int:
    lock = rawdata.load_lock()
    allowed = allowed_roots(lock)
    repo = norm(REPO)
    blocked = []
    guard = make_guard(allowed, blocked)

    # static scan: absolute imports in demo30/*.py
    imported = set()
    for path in (DEMO_ROOT / "demo30").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(n.name.split(".")[0] for n in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names)
    unexpected = sorted(m for m in imported if m not in stdlib and m not in ALLOWED_THIRD_PARTY)

    scratch = OUTPUTS / "_scratch_isolation"
    shutil.rmtree(scratch, ignore_errors=True)
    sys.addaudithook(guard)
    error = None
    try:
        from demo30 import pipeline
        stages = pipeline.run_all(scratch, make_plots=True)
    except Exception as exc:  # the audit reports failures instead of crashing
        stages, error = None, f"{type(exc).__name__}: {exc}"
    external = sorted({(name, getattr(m, "__file__", None)) for name, m in list(sys.modules.items())
                       if getattr(m, "__file__", None) and inside(norm(m.__file__), repo)
                       and not inside(norm(m.__file__), norm(DEMO_ROOT))})
    report = {"status": "PASS" if not blocked and not external and not unexpected and error is None else "FAIL",
              "pipeline_stages": stages, "pipeline_error": error,
              "blocked_reads": blocked, "repository_modules_outside_demo30": external,
              "unexpected_absolute_imports": unexpected, "absolute_imports": sorted(imported),
              "allowed_roots_inside_repository": ["nextnano/demos/30_absorption_study",
                                                  *[e["expected_dir"] for e in lock["runs"].values()]],
              "method": "sys.addaudithook on open/os.listdir/os.scandir during a full pipeline run into outputs/_scratch_isolation"}
    shutil.rmtree(scratch, ignore_errors=True)
    (OUTPUTS / "isolation_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Demo 30 isolation audit: {report['status']}")
    for key in ("pipeline_error", "blocked_reads", "repository_modules_outside_demo30", "unexpected_absolute_imports"):
        if report[key]:
            print(f"  {key}: {report[key]}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
