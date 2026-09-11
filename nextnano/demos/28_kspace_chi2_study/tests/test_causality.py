import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chi2.causality import uniform_energy_grid, kk_reconstruct, analytic_shg, error_metrics

@pytest.mark.parametrize('sign',[-1,1])
def test_analytic_shg_kk(sign):
    x=uniform_energy_grid(16,.002)
    f=analytic_shg(x,gamma_sign=sign)
    re,im=kk_reconstruct(x,f,sign)
    mask=(x>.1)&(x<3.2)
    assert error_metrics(f.real,re,mask)['relative_rms_error']<1e-5
    assert error_metrics(f.imag,im,mask)['relative_rms_error']<1e-5
    assert np.max(abs(f[::-1]-f.conj()))<1e-10

def test_wrong_sign_detected():
    x=uniform_energy_grid(8,.002);f=analytic_shg(x)
    re,_=kk_reconstruct(x,f,-1)
    assert error_metrics(f.real,re,(x>0)&(x<3))['relative_rms_error']>1.9

def test_kk_rejects_wavelength_grid():
    x=np.geomspace(.5,3,100)
    with pytest.raises(ValueError,match='uniform'): kk_reconstruct(x,analytic_shg(x))

@pytest.mark.parametrize('width,step',[(0,.1),(1,0),(1,.3)])
def test_bad_grid(width,step):
    with pytest.raises(ValueError): uniform_energy_grid(width,step)

def test_bandwidth_error_reduces():
    errors=[]
    for width in (4,16):
        x=uniform_energy_grid(width,.002);f=analytic_shg(x)
        re,im=kk_reconstruct(x,f)
        errors.append(error_metrics(f.imag,im,(x>0)&(x<3))['relative_rms_error'])
    assert errors[1]<errors[0]

def test_configuration():
    import json
    cfg=json.loads((Path(__file__).resolve().parents[1]/'config/causality.json').read_text())
    assert cfg['energy_step_eV']<=.001
    assert len(cfg['energy_half_widths_eV'])>=2
