"""Package or verify one Demo 29C historical mixed temperature control."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2.mixed_transfer import main

if __name__ == "__main__":
    raise SystemExit(main())
