"""Plot complete three-temperature spectra from one model."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.comparison import main

if __name__ == "__main__":
    raise SystemExit(main())
