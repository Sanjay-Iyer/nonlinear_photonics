"""Compatibility entry point matching Demos 4-11."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run_demo12.py"), run_name="__main__")

