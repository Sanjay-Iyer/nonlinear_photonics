import numpy as np
from chi2.state_audit import pair_subspace_fidelity,ROOT
from chi2.input_builder import build_inputs
from chi2 import decks


def test_subspace_rotation_invariance():
    rng=np.random.default_rng(19);x=rng.normal(size=(2,8,12))+1j*rng.normal(size=(2,8,12))
    u=np.array([[1,1j],[1j,1]])/np.sqrt(2)
    y=np.einsum('ij,jcz->icz',u,x)
    assert abs(pair_subspace_fidelity(x,y,np.ones(12))-1)<1e-12


def test_historical_second_valence_is_lh_not_hh():
    inputs,parsed=build_inputs(ROOT/'nextnano/raw_results')
    ids=np.array(inputs['kp8_pair_ids'][3])-1
    assert parsed['composition'][ids,4:6].sum(axis=1).mean()>.9


def test_extended_raw_is_genuine_and_larger():
    a,_=build_inputs(ROOT/'nextnano/raw_results');b,_=build_inputs(ROOT/'nextnano/raw_extended')
    assert b['k_per_nm'][-1]>a['k_per_nm'][-1]
    assert a['kp8_pair_ids']==b['kp8_pair_ids']
    assert np.allclose(a['anchors_eV'],b['anchors_eV'])
    raw=ROOT/'nextnano/raw_extended/kp8'
    assert 'successfully completed' in (raw/'job_done.txt').read_text()


def test_extended_deck_only_changes_k_sampling():
    a=decks.render_kp8();b=decks.render_kp8({'k_max_per_nm':.69464304904})
    raw=(ROOT/'nextnano/raw_extended/kp8/kmax_y_n301_k0125.in').read_text()
    assert decks.same_deck(b,raw)
    assert not decks.same_deck(a,raw)
