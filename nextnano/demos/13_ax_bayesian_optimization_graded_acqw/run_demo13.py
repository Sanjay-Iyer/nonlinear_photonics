"""Run Demo 13 from demo.yaml; ordinary scientific settings need no CLI flags.

    python run_demo13.py            # run the mode configured in demo.yaml
    python run_demo13.py --check    # report environment and budget, run nothing
"""

from pathlib import Path
import sys

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for path in (str(SHARED), str(DEMO_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import demo13  # noqa: E402
from sweeps import demo_cli  # noqa: E402


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        raise SystemExit(demo_cli(DEMO_DIR, demo13.check))
    raise SystemExit(demo_cli(DEMO_DIR, demo13.main))
