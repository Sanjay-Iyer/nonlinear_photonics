"""Run a smoke-test stage by number (thin wrapper over run_input.py).

    python nextnano/scripts/run_smoke_tests.py --test 1     # bulk GaAs         (1D)
    python nextnano/scripts/run_smoke_tests.py --test 2     # AlGaAs QW         (1D)
    python nextnano/scripts/run_smoke_tests.py --test 3     # 2D + 3D Standard  (3A then 3B)
    python nextnano/scripts/run_smoke_tests.py --test all

This only maps a stage number to its deck(s) and calls run_input for each, in
order, stopping on the first failure and returning a nonzero exit code if any
deck fails. All config loading, path validation, and execution live in
run_input -- this adds no orchestration of its own.
"""

from __future__ import annotations

import argparse
import sys

import run_input
from nn_config import NEXTNANO_ROOT

_SMOKE = NEXTNANO_ROOT / "inputs" / "01_smoke_tests"
_DIM = _SMOKE / "03_standard_dimensions"

# Ordered decks per stage. Stage 3 runs the 2D rectangle first, then the 3D
# cuboid, matching the documented work-laptop sequence.
STAGES = {
    "1": [_SMOKE / "hello_01_bulk_gaas.in"],
    "2": [_SMOKE / "hello_02_algaas_qw.in"],
    "3": [
        _DIM / "hello_03a_gaas_rectangle_2d.in",
        _DIM / "hello_03b_gaas_cuboid_3d.in",
    ],
}
_ORDER = ["1", "2", "3"]


def decks_for(test: str) -> list:
    """Return the ordered deck paths for a stage ('1'/'2'/'3') or 'all'."""
    if test == "all":
        return [deck for stage in _ORDER for deck in STAGES[stage]]
    return list(STAGES[test])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a nextnano++ smoke-test stage (wrapper over run_input.py)."
    )
    parser.add_argument(
        "--test",
        required=True,
        choices=[*_ORDER, "all"],
        help="Stage: 1 (bulk 1D), 2 (QW 1D), 3 (2D+3D Standard), or all.",
    )
    args = parser.parse_args(argv)

    stages = _ORDER if args.test == "all" else [args.test]
    for stage in stages:
        for deck in STAGES[stage]:
            print(f"\n=== smoke test {stage}: {deck.name} ===")
            rc = run_input.main([str(deck)])
            if rc != 0:
                print(
                    f"\nStage {stage} FAILED at {deck.name} (exit {rc}). Stopping.",
                    file=sys.stderr,
                )
                return rc
    print(f"\nAll requested smoke tests passed (--test {args.test}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
