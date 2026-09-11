"""Run 28F using cached data; never invokes nextnano."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chi2.causality import cli
if __name__=='__main__': raise SystemExit(cli())
