"""Allow ``python nextnano/demos/11_paper_validation_interband_chi2_acqw``."""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "run.py"), run_name="__main__")
