"""Allow ``python nextnano/demos/06_self_consistent_doped_coupled_well``."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run.py"), run_name="__main__")
