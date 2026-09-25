"""Package a successful 29A3 work run as a lossless, checksummed raw ZIP."""
import argparse
import json
from pathlib import Path
import sys

from package_pilot import main as package


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    args = p.parse_args()
    try:
        meta = json.loads((args.input / "run_metadata.json").read_text(encoding="utf-8"))
        run_id = meta["run_id"]
        if not all(ch.isalnum() or ch in "_-" for ch in run_id):
            raise ValueError("Unsafe run ID")
        destination = (Path(__file__).resolve().parents[1] / "nextnano/transfer" /
                       f"demo29_29A3_300K_full8_raw_{run_id}.zip")
        return package(["--input", str(args.input), "--zip", str(destination), "--dense"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
