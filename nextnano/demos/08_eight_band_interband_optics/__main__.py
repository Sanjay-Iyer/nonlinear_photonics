"""Allow ``python nextnano/demos/08_eight_band_interband_optics``."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run.py"), run_name="__main__")
