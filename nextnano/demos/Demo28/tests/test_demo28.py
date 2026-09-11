"""Portable-package regression; historical spectra are read-only references."""
from pathlib import Path
import json
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src import runner, decks
from src.equation2 import Settings, photon_energy, radial_weights, evaluate
from src.raw_inputs import load_inputs


@pytest.fixture(scope="module")
def baseline():
    return load_inputs(ROOT/"cached_raw","demo26-baseline")


def test_units_and_fundamental_wavelength():
    assert Settings().gamma_eV == .005
    assert photon_energy(np.array([1239.841984]))[0] == 1
    assert photon_energy(np.array([1550.]))[0] == pytest.approx(.7998980541935484)


@pytest.mark.parametrize("k",[[0,0],[.1,0],[0,float('nan')]])
def test_bad_k_rejected(k):
    with pytest.raises(ValueError): radial_weights(k)


def test_radial_disc_measure():
    k=np.array([0.,.03,.1,.2,.55])
    assert radial_weights(k).sum()==pytest.approx(2*k[-1]**2/(4*np.pi),rel=1e-14)


def test_cached_baseline_matches_independent_historical_spectrum(baseline):
    ref=np.loadtxt(ROOT/"validation/baseline_reference.csv",delimiter=",",skiprows=1)
    chi,terms,labels,_=evaluate(ref[:,0],baseline)
    assert np.max(abs(chi-(ref[:,1]+1j*ref[:,2])))<1e-8
    assert len(labels)==len(terms)==16
    assert np.allclose(terms.sum(axis=0),chi,rtol=0,atol=1e-12)


def test_imaginary_survives_and_gamma_sign_conjugates(baseline):
    wavelength=np.array([700.,1000.,1400.,1550.])
    positive=evaluate(wavelength,baseline)[0]
    negative=evaluate(wavelength,baseline,Settings(gamma_sign=-1))[0]
    assert np.max(abs(positive.imag))>1
    assert np.max(abs(abs(positive)-abs(positive.real)))>1
    assert np.allclose(negative,np.conj(positive),atol=1e-11)
    assert np.allclose(abs(positive),np.hypot(positive.real,positive.imag))


def test_continuous_phase_invariance(baseline):
    se=np.exp(1j*np.array([.3,.8])); sh=np.exp(1j*np.array([1.2,-.4]))
    changed={**baseline,"overlap":se.conj()[:,None]*sh[None,:]*baseline['overlap'],
             "ze_nm":se.conj()[:,None]*se[None,:]*baseline['ze_nm'],
             "zh_nm":sh.conj()[:,None]*sh[None,:]*baseline['zh_nm']}
    wavelength=np.array([540.,760.,1080.,1520.])
    assert np.max(abs(evaluate(wavelength,changed)[0]-evaluate(wavelength,baseline)[0]))<1e-9


def test_deck_physics_preserved():
    config=json.loads((ROOT/"config/runner.json").read_text())
    generated=decks.render_kp8(config['kp8'])
    assert decks.same_deck(generated,(ROOT/"decks/kp8_dispersion.in").read_text())


def test_preflight_never_launches(monkeypatch,tmp_path):
    def forbidden(*args,**kwargs):
        raise AssertionError("preflight tried launching an external process")
    monkeypatch.setattr(runner.subprocess,"run",forbidden)
    assert runner.main(["--preflight","--no-parse","--output",str(tmp_path/"preflight")])==0
    manifest=json.loads((tmp_path/"preflight/preflight_manifest.json").read_text())
    assert manifest['professional_execution_performed'] is False


def test_source_has_no_runtime_previous_demo_paths():
    for p in (ROOT/"src").glob('*.py'):
        source=p.read_text(encoding='utf-8')
        assert "sys.path.insert" not in source
        assert "C:\\code" not in source and "C:/code" not in source
        assert 'DEMO26_RAW_OUTPUT' not in source


def test_cached_kp8_state_selection():
    data=load_inputs(ROOT/"cached_raw","kp8")
    assert len(data['k_per_nm'])==301
    assert data['electron_eV'].shape==(2,301)
    assert data['valence_eV'].shape==(2,301)
    assert np.isfinite(data['overlap']).all()
