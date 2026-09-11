import json
from pathlib import Path
import numpy as np
from chi2.studies import load_configuration
ROOT=Path(__file__).resolve().parents[1]

def test_config_loads_original_baseline():
    cfg,s,wl=load_configuration(ROOT/'config/baseline.json')
    assert s.gamma_eV==.005 and len(wl)==1451

def test_all_extended_cutoffs_exclude_higher_samples():
    cfg=json.loads((ROOT/'config/extended_k.json').read_text())
    for f in cfg['k_cutoffs_pi_over_a']:
        folder=ROOT/'outputs/28C_extended_k/cases'/f'kmax_{f:.4f}'
        meta=json.loads((folder/'metadata.json').read_text())
        k=np.loadtxt(folder/'chi2_inputs/k_per_nm.csv',delimiter=',',skiprows=1)[:,0]
        assert np.all(k<=f*np.pi/cfg['lattice_constant_nm'])
        assert meta['all_samples_within_requested_cutoff']

def test_metadata_reference_paths_resolve():
    for path in (ROOT/'outputs').glob('28*/**/metadata.json'):
        meta=json.loads(path.read_text())
        assert 'timestamp_utc' in meta
        for key in ['raw_manifest','code_manifest']:
            if key in meta: assert (path.parent/meta[key]).exists(),(path,key,meta[key])

def test_gamma_components_and_complex_identity():
    for p in (ROOT/'outputs/28E_linewidth/cases').glob('*/chi2_spectrum.csv'):
        a=np.loadtxt(p,delimiter=',',skiprows=1)
        assert np.allclose(a[:,5],np.hypot(a[:,2],a[:,3]))
        assert np.any(a[:,5]>a[:,4])

def test_generated_resonance_map_has_finite_data():
    path=ROOT/'outputs/28G_pathways/resonance_map.csv'
    a=np.loadtxt(path,delimiter=',',skiprows=1)
    assert np.isfinite(a).all()

def test_same_cutoff_density_error_is_small_but_nonzero():
    meta=json.loads((ROOT/'outputs/28H_grid_convergence/metadata.json').read_text())
    e=meta['extended_grid_at_same_cutoff']
    assert e['extended_Nk']==241 and e['baseline_Nk']==301
    assert 0<e['max_Re_error_pm_per_V']<.04
