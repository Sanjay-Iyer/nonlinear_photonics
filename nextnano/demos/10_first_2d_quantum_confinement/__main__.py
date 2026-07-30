"""Allow ``python nextnano/demos/10_first_2d_quantum_confinement``."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run.py"), run_name="__main__")
