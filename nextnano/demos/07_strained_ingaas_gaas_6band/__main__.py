"""Allow ``python nextnano/demos/07_strained_ingaas_gaas_6band``."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run.py"), run_name="__main__")
