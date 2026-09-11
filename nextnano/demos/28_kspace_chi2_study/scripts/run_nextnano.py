"""Optional work-laptop launcher. Preflight is safe at home."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chi2.nextnano_runner import main

if __name__=='__main__': raise SystemExit(main())
