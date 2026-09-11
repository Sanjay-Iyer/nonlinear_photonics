from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chi2.numerical_audit import subsample,shell_contributions
from chi2.input_builder import build_inputs
from chi2.equation2 import calculate_chi2,calculate_chi2_energy,Settings,photon_energy,pathway_definitions
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def inputs(): return build_inputs(ROOT/'nextnano/raw_results')[0]

def test_energy_wrapper_identical(inputs):
    wl=np.array([540.,760.,1080.,1520.,1550.])
    assert np.array_equal(calculate_chi2(wl,inputs).chi2_complex,calculate_chi2_energy(photon_energy(wl),inputs).chi2_complex)

def test_shell_integral_exact(inputs):
    r=calculate_chi2(np.array([540.,760.,1080.,1520.,1550.]),inputs)
    s=shell_contributions(r,inputs['k_per_nm'],Settings())
    assert max(abs(s.sum(axis=1)-r.chi2_complex))<1e-10

@pytest.mark.parametrize('stride',[10,6,3,2,1])
def test_native_grid_subsample(inputs,stride):
    s=subsample(inputs,stride)
    assert s['k_per_nm'][0]==inputs['k_per_nm'][0]
    assert s['k_per_nm'][-1]==inputs['k_per_nm'][-1]
    assert s['electron_eV'].shape==(2,len(s['k_per_nm']))
    assert np.all(np.isin(s['k_per_nm'],inputs['k_per_nm']))

def test_pathway_definitions_shapes(inputs):
    p=list(pathway_definitions(inputs))
    assert len(p)==16 and len(set(r['label'] for r in p))==16
    assert sum(r['kind']=='C' for r in p)==8
    assert all(r['numerator'].shape==(301,) for r in p)
