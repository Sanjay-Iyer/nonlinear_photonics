"""Run 28A: raw nextnano -> saved chi2 inputs -> baseline spectrum."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chi2.studies import cli

if __name__=='__main__': raise SystemExit(cli('28A'))
