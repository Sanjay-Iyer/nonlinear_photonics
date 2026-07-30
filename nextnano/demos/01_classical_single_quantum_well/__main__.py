"""Allow ``python path/to/01_classical_single_quantum_well``."""

from pathlib import Path
import sys

SHARED = Path(__file__).resolve().parents[1] / "_shared"
sys.path.insert(0, str(SHARED))

from demo_workflow import cli  # noqa: E402


raise SystemExit(cli(Path(__file__).resolve().parent))
