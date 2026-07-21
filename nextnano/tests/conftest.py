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
