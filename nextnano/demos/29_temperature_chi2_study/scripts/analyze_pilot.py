"""Review 29A pilot states and matrices without calculating chi2."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.pilot_analysis import main

if __name__ == "__main__":
    raise SystemExit(main())
