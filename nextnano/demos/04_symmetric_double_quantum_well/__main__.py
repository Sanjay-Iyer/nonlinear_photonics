"""Allow ``python nextnano/demos/04_symmetric_double_quantum_well``."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run.py"), run_name="__main__")
