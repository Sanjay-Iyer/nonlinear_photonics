"""Controlled-response diagnostics and authoritative-pathway tests."""
import json
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from chi2.input_builder import build_inputs
from chi2.equation2 import calculate_chi2, pathway_definitions, Settings, HC_EV_NM
from chi2.response_audit import (safe_ratio,resonance_detuning,region_metrics,
                                 cancellation_metrics,sampled_lobe_width,validate_configuration)


@pytest.fixture(scope='module')
def inputs():
    return build_inputs(ROOT/'nextnano/raw_results')[0]


def test_authoritative_pathway_shapes(inputs):
    terms=list(pathway_definitions(inputs))
    assert len(terms)==16
    assert len(set(p['label'] for p in terms))==16
    for p in terms:
        assert p['numerator'].shape==(301,)
        assert p['one_transition_eV'].shape==(301,)
        assert p['two_transition_eV'].shape==(301,)
        assert np.max(abs(p['numerator'].imag))==0


def test_electron_hole_sum(inputs):
    s=calculate_chi2(np.array([540.,760.,1080.,1520.,1550.]),inputs)
    c=sum(v for v,l in zip(s.pathways_complex,s.pathway_labels) if l.startswith('C_'))
    h=sum(v for v,l in zip(s.pathways_complex,s.pathway_labels) if l.startswith('V_'))
    np.testing.assert_allclose(c+h,s.chi2_complex,atol=1e-10,rtol=1e-12)


def test_coordinate_origin_cancels_in_total(inputs):
    moved={**inputs,'ze_nm':inputs['ze_nm']+12*np.eye(2),'zh_nm':inputs['zh_nm']+12*np.eye(2)}
    wl=np.array([550.,755.,1500.,1550.])
    np.testing.assert_allclose(calculate_chi2(wl,inputs).chi2_complex,
                               calculate_chi2(wl,moved).chi2_complex,atol=1e-10,rtol=1e-11)


def test_small_gamma_reduces_off_resonance_imaginary(inputs):
    wl=np.array([450.,500.,1000.,1100.,1800.])
    base=calculate_chi2(wl,inputs,Settings(gamma_meV=5)).chi2_complex
    small=calculate_chi2(wl,inputs,Settings(gamma_meV=.1)).chi2_complex
    assert np.all(abs(small.imag)<abs(base.imag)*.021)


def test_ratio_masks_zeros_instead_of_reporting_infinity():
    ratio,valid,floor=safe_ratio(np.array([0+5j,1+2j,1e-5+1j]),1e-3)
    assert valid.tolist()==[False,True,False]
    assert np.isnan(ratio[0]) and ratio[1]==2 and np.isnan(ratio[2])
    assert floor==.001


def test_objective_resonance_uses_one_and_two_photon(inputs):
    transition=inputs['electron_eV'][0,0]-inputs['valence_eV'][0,0]
    wl=np.array([HC_EV_NM/transition,2*HC_EV_NM/transition])
    np.testing.assert_allclose(resonance_detuning(wl,inputs),0,atol=1e-14)


def test_cancellation_norm():
    terms=np.array([[1+2j,3+1j],[-1-2j,-3-1j]])
    assert cancellation_metrics(terms)['cancellation_fraction']==1


def test_empty_region_is_explicit():
    assert region_metrics(np.ones(3,complex),np.zeros(3,bool),np.ones(3),np.ones(3,bool))['status']=='NO_SAMPLES'


def test_width_of_edge_peak_is_not_invented():
    assert sampled_lobe_width(np.arange(4),np.arange(4))['width_nm'] is None


def test_response_config_loading():
    cfg=json.loads((ROOT/'config/response_audit.json').read_text())
    assert validate_configuration(cfg)['gamma_meV']==[.1,.5,1.,2.,5.,10.,20.]
    with pytest.raises(ValueError): validate_configuration({**cfg,'gamma_meV':[0,5]})


def test_saved_response_metadata():
    d=json.loads((ROOT/'outputs/28D_imaginary_source/metadata.json').read_text())
    assert d['numerator_max_abs_imag_nm']==0
    assert d['full_vs_real_numerator_max_error_pm_per_V']==0
    assert d['electron_hole_sum_max_error_pm_per_V']<1e-9
    for study in ('28D_imaginary_source','28E_linewidth','28G_pathways'):
        out=ROOT/'outputs'/study
        meta=json.loads((out/'metadata.json').read_text())
        assert (out/meta['raw_manifest']).is_file()
        assert (out/meta['code_manifest']).is_file()
