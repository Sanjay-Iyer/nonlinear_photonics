"""Fixed locations inside the Demo 30 directory. Nothing here points at other demos."""
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = DEMO_ROOT / "config" / "demo30.json"
LOCK = DEMO_ROOT / "inputs" / "raw_data.lock.json"
REFERENCE = DEMO_ROOT / "reference"
OUTPUTS = DEMO_ROOT / "outputs"
PLOTS = DEMO_ROOT / "plots"
# <repo>/nextnano/demos/30_absorption_study -> <repo>/nextnano_raw (the default raw store)
DEFAULT_RAW_ROOT = DEMO_ROOT.parents[2] / "nextnano_raw"
