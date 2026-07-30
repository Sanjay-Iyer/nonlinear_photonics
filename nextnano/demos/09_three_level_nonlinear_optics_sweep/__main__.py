"""Allow ``python nextnano/demos/09_three_level_nonlinear_optics_sweep``."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run.py"), run_name="__main__")
