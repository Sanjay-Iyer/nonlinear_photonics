"""Assess five-point matrix interpolation before requesting a denser run."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.sampling import analyze


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analysis", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        report = analyze(args.analysis, args.output)
        print(json.dumps({"five_point_interpolation_accepted": report["five_point_interpolation_accepted"],
                          "reasons": report["reasons_for_dense_validation"],
                          "same_band_max_linear_relative_error": {
                              key: report["blocks"][key]["max_linear_relative_error"]
                              for key in ("e1-e2", "hh1-hh2")}}, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
