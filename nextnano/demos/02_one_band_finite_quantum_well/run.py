"""Run Demo 2 from its YAML configuration."""

from pathlib import Path
import sys

SHARED = Path(__file__).resolve().parents[1] / "_shared"
sys.path.insert(0, str(SHARED))

from demo_workflow import cli  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(cli(Path(__file__).resolve().parent))

