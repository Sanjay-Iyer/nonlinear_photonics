"""Demo 30 tests: put the demo on sys.path; share one verified control state.

Tests that need the raw nextnano data are skipped, with the resolver's download or
registration instructions as the reason, when the locked runs are not on this machine.
The demo's own entry command fails loudly in the same situation.
"""
from pathlib import Path
import sys

import pytest

DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))


@pytest.fixture(scope="session")
def state():
    from demo30 import baseline, rawdata
    try:
        return baseline.compute()
    except rawdata.RawDataMissing as exc:
        pytest.skip(f"raw nextnano data not available:\n{exc}")
