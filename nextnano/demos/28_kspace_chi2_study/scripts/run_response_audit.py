"""Run 28D, 28E and 28G using cached nextnano output, never a licensed solve."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.response_audit import cli
if __name__ == '__main__':
    raise SystemExit(cli())
