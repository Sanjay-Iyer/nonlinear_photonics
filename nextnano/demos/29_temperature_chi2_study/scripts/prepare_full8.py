"""Validate and prepare full-8-band states and finite-k matrices."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.full8 import main

if __name__ == "__main__":
    raise SystemExit(main())
