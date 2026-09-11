from pathlib import Path
import json
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from chi2.equation2 import Settings,photon_energy,prefactor,calculate_chi2
from chi2.k_integration import radial_weights,select_range
from chi2.input_builder import build_inputs
from chi2.artifacts import save_inputs
from chi2 import nextnano_runner as runner,decks


@pytest.fixture(scope='module')
def inputs(): return build_inputs(ROOT/'nextnano/raw_results')[0]


def test_mev_conversion_and_input_wavelength():
    assert Settings().gamma_eV==.005
    assert photon_energy(np.array([1239.841984]))[0]==1.
    assert photon_energy(np.array([1550.]))[0]==pytest.approx(.7998980541935484)


@pytest.mark.parametrize('k',[[0.,0.],[.1,0.],[0.,np.nan],[-.1,.1]])
def test_invalid_k(k):
    with pytest.raises(ValueError):radial_weights(k)


def test_trapezoid_disc_area():
    k=np.array([0.,.001,.013,.2,.4])
    assert radial_weights(k).sum()==pytest.approx(2*k[-1]**2/(4*np.pi),rel=1e-14)


def test_raw_state_order_and_matrix_normalization(inputs):
    assert inputs['kp8_pair_ids']==[[11,12],[13,14],[5,6],[3,4]]
    assert inputs['electron_eV'].shape==(2,301)
    assert inputs['valence_eV'].shape==(2,301)
    assert inputs['gram_error']<1e-12
    assert inputs['anchors_eV']==pytest.approx([2.941158138088,3.061022858158,1.447805442384,1.412791422186],abs=1e-12)


def test_historical_complex_spectrum_and_saved_integrand(inputs):
    old=np.loadtxt(ROOT/'validation/demo26_baseline_reference.csv',delimiter=',',skiprows=1)
    r=calculate_chi2(old[:,0],inputs)
    assert max(abs(r.chi2_complex-(old[:,1]+1j*old[:,2])))<1e-8
    assert r.pathways_complex.shape==(16,1451)
    assert r.summed_integrand.shape==(1451,301)
    assert max(abs(prefactor(Settings())*(r.summed_integrand@r.k_weights_nm_minus2)-r.chi2_complex))<1e-9


def test_imaginary_and_sign_convention(inputs):
    wl=np.array([700.,1000.,1400.,1550.])
    p=calculate_chi2(wl,inputs).chi2_complex
    n=calculate_chi2(wl,inputs,Settings(gamma_sign=-1)).chi2_complex
    assert max(abs(p.imag))>1
    assert max(abs(abs(p)-abs(p.real)))>1
    assert max(abs(n-np.conj(p)))<1e-10


def test_phase_invariant_numerators(inputs):
    se=np.exp(1j*np.array([.3,.8]));sh=np.exp(1j*np.array([1.2,-.4]))
    changed={**inputs,'overlap':se.conj()[:,None]*sh[None,:]*inputs['overlap'],
             'ze_nm':se.conj()[:,None]*se[None,:]*inputs['ze_nm'],
             'zh_nm':sh.conj()[:,None]*sh[None,:]*inputs['zh_nm']}
    wl=np.array([540.,760.,1080.,1520.])
    assert max(abs(calculate_chi2(wl,changed).chi2_complex-calculate_chi2(wl,inputs).chi2_complex))<1e-9


@pytest.mark.parametrize('fraction',[.01,.02,.03,.04,.05,.06,.07,.08,.09,.10])
def test_native_cutoff_and_correct_endpoint_weights(inputs,fraction):
    requested=fraction*np.pi/.565325
    selected=select_range(inputs,min(requested,inputs['k_per_nm'][-1]))
    k=selected['k_per_nm']
    assert np.all(k<=requested)
    assert len(k)==round(fraction*3000)+1
    assert radial_weights(k).sum()==pytest.approx(2*k[-1]**2/(4*np.pi),rel=1e-14)
    if len(k)<301:
        assert radial_weights(k)[-1]<radial_weights(inputs['k_per_nm'])[len(k)-1]


def test_between_grid_cutoff_and_lower_limit(inputs):
    k=inputs['k_per_nm']
    selection=select_range(inputs,(k[42]+k[43])/2,k[10])
    assert np.array_equal(selection['k_per_nm'],k[10:43])


def test_out_of_range_rejected(inputs):
    with pytest.raises(ValueError):select_range(inputs,2*inputs['k_per_nm'][-1])
    with pytest.raises(ValueError):select_range(inputs,inputs['k_per_nm'][1]/2)


def test_full_range_identical_and_small_range_changes(inputs):
    wl=np.array([700.,1000.,1400.,1550.]);k=inputs['k_per_nm']
    full=calculate_chi2(wl,inputs).chi2_complex
    assert np.array_equal(full,calculate_chi2(wl,select_range(inputs,k[-1])).chi2_complex)
    small=calculate_chi2(wl,select_range(inputs,k[len(k)//2])).chi2_complex
    assert max(abs(full-small))>1


def test_intermediate_arrays_and_metadata(inputs,tmp_path):
    s=select_range(inputs,inputs['k_per_nm'][30])
    save_inputs(tmp_path,s,Settings(),np.array([1550.]))
    assert np.load(tmp_path/'overlap_eh.npy').shape==(2,2,31)
    meta=json.loads((tmp_path/'metadata.json').read_text())
    assert meta['gamma_eV']==.005 and meta['shapes']['energies']==[2,31]
    assert meta['selection']['points']==31


def test_preflight_never_launches(monkeypatch,tmp_path):
    def forbidden(*a,**k):raise AssertionError('No subprocess may launch in no-parse preflight')
    monkeypatch.setattr(runner.subprocess,'run',forbidden)
    assert runner.main(['--preflight','--no-parse','--output',str(tmp_path/'dry')])==0
    meta=json.loads((tmp_path/'dry/preflight_manifest.json').read_text())
    assert meta['professional_execution_performed'] is False
    assert meta['script2_parser_self_test_on_shipped_cached_raw']['baseline_parser']=='PASS'


def test_deck_and_self_containment():
    cfg=json.loads((ROOT/'config/runner.json').read_text())
    assert decks.same_deck(decks.render_kp8(cfg['kp8']),(ROOT/'nextnano/inputs/kp8_dispersion.in').read_text())
    for p in (ROOT/'chi2').glob('*.py'):
        text=p.read_text()
        assert 'sys.path.insert' not in text
        assert 'C:/code' not in text and 'C:\\code' not in text


def test_generated_study_validation_and_full_case():
    a=json.loads((ROOT/'outputs/28A_baseline/metadata.json').read_text())
    b=json.loads((ROOT/'outputs/28B_kspace_cutoff/metadata.json').read_text())
    assert a['validation_status']==b['validation_status']=='PASS'
    assert b['full_cutoff_vs_baseline_error_pm_per_V']==0
    assert b['case_count']==10 and b['all_cases_within_cutoffs']
    reference=np.load(ROOT/'outputs/28A_baseline/chi2_results/chi2_complex.npy')
    full=np.load(ROOT/'outputs/28B_kspace_cutoff/cases/kmax_0p10000/chi2_results/chi2_complex.npy')
    assert np.array_equal(reference,full)
