"""Calculate one same-temperature mixed-model control spectrum."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.mixed_control import main

if __name__ == "__main__":
    raise SystemExit(main())
