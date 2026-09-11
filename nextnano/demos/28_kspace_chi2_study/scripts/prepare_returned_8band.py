"""Validate and prepare finite-k candidate tracking/operator blocks, not spectra."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chi2.finite8band import main
if __name__=='__main__':main()
