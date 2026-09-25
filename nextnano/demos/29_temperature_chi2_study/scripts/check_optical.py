"""Fail closed unless the 8-band optical/spin mapping is actually approved."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.full8 import optical_gate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] /
                   "config/optical_operator.json")
    args = p.parse_args(argv)
    try:
        setting = optical_gate(args.config)
        print(json.dumps({"status": "PASS", "operator_source": setting["operator_source"],
                          "spin_reduction": setting["spin_reduction"]}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
