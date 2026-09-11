"""Run cached state evidence audit; never calls a solver."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chi2.state_audit import main
if __name__=='__main__': main()
