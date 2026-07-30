"""pytest configuration for the nextnano workflow tests.

Puts the scripts/ directory on sys.path so the tests can import the workflow
modules (nn_config, run_input) the same way run_input.py does when launched
directly, without turning the workflow into an installable package.
"""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

DEMO_SHARED_DIR = Path(__file__).resolve().parents[1] / "demos" / "_shared"
if str(DEMO_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_SHARED_DIR))

# Each Demo 4-10 directory holds its own orchestration module, uniquely named
# (demo04 ... demo10) so several can be imported in one pytest session without
# shadowing each other.
DEMOS_DIR = Path(__file__).resolve().parents[1] / "demos"
for _demo_dir in sorted(DEMOS_DIR.glob("[0-9][0-9]_*")):
    if _demo_dir.is_dir() and str(_demo_dir) not in sys.path:
        sys.path.insert(0, str(_demo_dir))
