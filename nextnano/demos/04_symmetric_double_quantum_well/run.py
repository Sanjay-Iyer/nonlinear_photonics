"""Run Demo 4 from its YAML configuration."""

from pathlib import Path
import sys

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for path in (str(SHARED), str(DEMO_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import demo04  # noqa: E402
from sweeps import demo_cli  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(demo_cli(DEMO_DIR, demo04.main))
