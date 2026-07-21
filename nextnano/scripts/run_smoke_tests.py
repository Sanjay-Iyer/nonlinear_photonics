"""Run a smoke-test stage (or range) by number -- thin wrapper over run_input.

    python nextnano/scripts/run_smoke_tests.py --test 1     # bulk GaAs          (1D)
    python nextnano/scripts/run_smoke_tests.py --test 2     # AlGaAs QW          (1D)
    python nextnano/scripts/run_smoke_tests.py --test 3     # 2D + 3D            (3A,3B)
    python nextnano/scripts/run_smoke_tests.py --test 4     # T!=300 + 6/8-band  (4A,4B,4C)
    python nextnano/scripts/run_smoke_tests.py --test 5     # strain + polariz.  (5A,5B)
    python nextnano/scripts/run_smoke_tests.py --test 6     # device + optical   (6A,6B,6C)
    python nextnano/scripts/run_smoke_tests.py --test 4-6   # stages 4 through 6
    python nextnano/scripts/run_smoke_tests.py --test all

Maps a stage (or inclusive range like 4-6) to its deck(s), runs them in
filename order via run_input, stops on the first failure, and returns a nonzero
exit code if any deck fails. All config loading, path validation, and execution
live in run_input -- this adds no orchestration of its own.
"""

from __future__ import annotations

import argparse
import sys

import run_input
from nn_config import NEXTNANO_ROOT

_SMOKE = NEXTNANO_ROOT / "inputs" / "01_smoke_tests"
_DIM = _SMOKE / "03_standard_dimensions"
_TMB = _SMOKE / "04_temperature_and_multiband"
_STP = _SMOKE / "05_strain_and_polarization"
_DEV = _SMOKE / "06_device_and_optical"

# Ordered decks per stage (filename order within a stage).
STAGES = {
    "1": [_SMOKE / "hello_01_bulk_gaas.in"],
    "2": [_SMOKE / "hello_02_algaas_qw.in"],
    "3": [
        _DIM / "hello_03a_gaas_rectangle_2d.in",
        _DIM / "hello_03b_gaas_cuboid_3d.in",
    ],
    "4": [
        _TMB / "hello_04a_qw_77K_oneband.in",
        _TMB / "hello_04b_qw_6band_kp.in",
        _TMB / "hello_04c_qw_8band_kp.in",
    ],
    "5": [
        _STP / "hello_05a_inGaAs_GaAs_strain.in",
        _STP / "hello_05b_GaN_AlN_piezo_pyro.in",
    ],
    "6": [
        _DEV / "hello_06a_GaAs_pn_current_recombination.in",
        _DEV / "hello_06b_GaAs_AlGaAs_qw_absorption.in",
        _DEV / "hello_06c_pin_qw_schrodinger_current_poisson.in",
    ],
}
_ORDER = ["1", "2", "3", "4", "5", "6"]


def parse_stages(test: str) -> list[str]:
    """Resolve a --test value into an ordered list of stage keys.

    Accepts a single stage ('4'), an inclusive range ('4-6'), or 'all'.
    Raises ValueError on anything unknown.
    """
    test = test.strip().lower()
    if test == "all":
        return list(_ORDER)
    if "-" in test:
        lo, _, hi = test.partition("-")
        if lo not in _ORDER or hi not in _ORDER or int(lo) > int(hi):
            raise ValueError(f"invalid stage range: {test!r}")
        return [s for s in _ORDER if int(lo) <= int(s) <= int(hi)]
    if test not in _ORDER:
        raise ValueError(f"unknown stage: {test!r} (expected one of {_ORDER}, a range, or 'all')")
    return [test]


def decks_for(test: str) -> list:
    """Return the ordered deck paths for a stage, range, or 'all'."""
    return [deck for stage in parse_stages(test) for deck in STAGES[stage]]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a nextnano++ smoke-test stage or range (wrapper over run_input.py)."
    )
    parser.add_argument(
        "--test",
        required=True,
        help="Stage 1-6, an inclusive range like 4-6, or 'all'. "
        "1 bulk(1D) | 2 QW(1D) | 3 2D+3D | 4 T!=300 & 6/8-band | "
        "5 strain & polarization | 6 device & optical.",
    )
    args = parser.parse_args(argv)

    try:
        stages = parse_stages(args.test)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

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
