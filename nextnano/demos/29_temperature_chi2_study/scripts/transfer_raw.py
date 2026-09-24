"""Pack, unpack, or validate a Demo 29 temperature dataset."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.transfer import main

if __name__ == "__main__":
    raise SystemExit(main())
