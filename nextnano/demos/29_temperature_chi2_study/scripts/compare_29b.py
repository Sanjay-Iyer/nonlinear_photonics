"""Create the 29B 100/300/500 K full-8-band electronic-structure comparison."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.compare_29b import main

if __name__ == "__main__":
    raise SystemExit(main())
