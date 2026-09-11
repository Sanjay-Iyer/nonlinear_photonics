"""Generate a provisional 0.15*pi/a work plan and static preflight; NO executable launch."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from chi2 import decks
from chi2.artifacts import write_json
from chi2.nextnano_runner import main as runner


def main():
    cfg=json.loads((ROOT/'config/extended_k.json').read_text())
    base=json.loads((ROOT/'config/runner.json').read_text())
    fraction=float(cfg['future_candidate_max_pi_over_a'])
    if not .125<fraction<=.25: raise ValueError('Provisional range must exceed cached .125 and remain <=.25; review physics before larger requests')
    base['kp8'].update(k_max_per_nm=fraction*np.pi/cfg['lattice_constant_nm'],k_points=int(cfg['future_candidate_k_points']),
                       purpose='Provisional extended-k state/model audit, NOT a validated physical extension')
    dest=ROOT/'outputs/28C_extended_k/work_laptop';dest.mkdir(parents=True,exist_ok=True)
    write_json(dest/'runner.json',base)
    deck=decks.render_kp8({k:v for k,v in base['kp8'].items() if k!='purpose'},'Demo28 provisional extended-k state audit')
    (dest/'kp8_extended.in').write_text(deck,encoding='utf-8')
    # --no-parse disables even parser subprocesses; home machine launches nothing.
    status=runner(['--preflight','--no-parse','--config',str(dest/'runner.json'),'--output',str(dest/'preflight')])
    if status: raise RuntimeError('Static preflight failed')
    return dest


if __name__=='__main__': print(main())
