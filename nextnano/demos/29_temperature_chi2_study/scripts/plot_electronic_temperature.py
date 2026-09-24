"""Plot temperature dependence of tracked k=0 transition energies."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.electronic_temperature import main

if __name__ == "__main__":
    raise SystemExit(main())
