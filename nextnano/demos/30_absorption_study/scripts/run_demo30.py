"""Demo 30 entry point: regenerate every output and figure from the locked raw data.

    <python> nextnano/demos/30_absorption_study/scripts/run_demo30.py
    <python> nextnano/demos/30_absorption_study/scripts/run_demo30.py --raw-root D:/nextnano_raw
    <python> nextnano/demos/30_absorption_study/scripts/run_demo30.py --check-stale

No nextnano solver is run. The raw data are verified against inputs/raw_data.lock.json
before anything is parsed. If they are missing, the error says which run to download
and where to put it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))

from demo30 import pipeline, rawdata  # noqa: E402
from demo30.meta import code_manifest, sha256_bytes  # noqa: E402
from demo30.paths import CONFIG, LOCK, OUTPUTS  # noqa: E402


def check_stale() -> int:
    """Outputs are stale if the config, lock or code changed since they were written."""
    current = {"config_sha256": sha256_bytes(CONFIG), "lock_sha256": sha256_bytes(LOCK), "code_sha256": code_manifest()}
    stale = []
    for meta in sorted(OUTPUTS.glob("30*/metadata.json")):
        recorded = json.loads(meta.read_text(encoding="utf-8"))
        for key, value in current.items():
            if recorded.get(key) != value:
                stale.append(f"{meta.parent.name}: {key} changed")
    print("outputs are current" if not stale else "STALE outputs (rerun run_demo30.py):\n  " + "\n  ".join(stale))
    return 1 if stale else 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-root", help="raw-data store (default: NEXTNANO_RAW_ROOT or <repo>/nextnano_raw)")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--check-stale", action="store_true", help="only report whether outputs are out of date")
    args = parser.parse_args(argv)
    if args.check_stale:
        return check_stale()
    try:
        status = pipeline.run_all(raw_root=args.raw_root, make_plots=not args.no_plots)
    except (rawdata.RawDataMissing, rawdata.RawDataMismatch) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("Demo 30:", ", ".join(f"{k} {v}" for k, v in status.items()))
    required_ok = all(v == "PASS" for k, v in status.items() if "optional" not in k)
    return 0 if required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
