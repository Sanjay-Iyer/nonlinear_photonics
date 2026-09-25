"""Package a validated 29B 100/500 K run into a lossless, checksummed raw ZIP."""
import argparse
import json
from pathlib import Path
import sys

from package_pilot import main as package


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        metadata = json.loads((args.input / "run_metadata.json").read_text(encoding="utf-8"))
        temperature, run_id = metadata["temperature_K"], metadata["run_id"]
        if temperature not in (100, 500) or not all(ch.isalnum() or ch in "_-" for ch in run_id):
            raise ValueError("Expected a safe 29B 100/500 K run ID")
        destination = (Path(__file__).resolve().parents[1] / "nextnano/transfer" /
                       f"demo29_29B_{temperature}K_full8_raw_{run_id}.zip")
        return package(["--input", str(args.input), "--zip", str(destination), "--temperature-study"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
