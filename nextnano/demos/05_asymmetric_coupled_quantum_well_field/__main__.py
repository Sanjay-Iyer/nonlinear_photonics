"""Allow ``python nextnano/demos/05_asymmetric_coupled_quantum_well_field``."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run.py"), run_name="__main__")
