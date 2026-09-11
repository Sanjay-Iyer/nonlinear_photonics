import argparse
import json
import re
import numpy as np
import pytest
from chi2 import extended8band as ext
from chi2.finite8band import matrix_data,assign,eq2_inputs
from chi2.extended8band_plots import meeting_spectra


def test_dense_deck_contract():
    c=ext.load_config();deck=ext.render(c)
    assert c['k_points']==601 and c['kmax_pi_over_a']==.2
    assert 'energy_shift = not_shifted' in deck
    assert 'envelopes = no' in deck and 'envelopes_CB_HH_LH_SO = yes' in deck
    assert 'probabilities = no' in deck
    assert re.search(r'num_holes\s*=\s*16',deck)
    for text in ('num_electrons = 8','all_k_points = yes','k_point_subdirectories = yes','output_energies_on_grid','k_integration_disabled{}'):
        assert text in deck
    assert 'single_band' not in deck
    assert set([.1,.125,.15,.175,.2])<=set(c['analysis_cutoffs_pi_over_a'])


def test_preflight_never_solves(tmp_path,monkeypatch):
    monkeypatch.setattr(ext,'PLAN',tmp_path/'plan')
    monkeypatch.setattr(ext,'discover_parser',lambda:(None,None))
    monkeypatch.setattr(ext.subprocess,'run',lambda *a,**k:pytest.fail('Unexpected subprocess'))
    r=ext.prepare(ext.load_config(),no_parse=True)
    assert not r['professional_execution_performed']
    assert r['requested_Nk']==601


def test_free_rejected(tmp_path):
    exe=tmp_path/'free.exe';exe.touch();db=tmp_path/'db';db.touch();lic=tmp_path/'lic';lic.touch()
    a=argparse.Namespace(exe=str(exe),database=str(db),license=str(lic),output=tmp_path/'result')
    with pytest.raises(ValueError,match='Free'):ext.run(ext.load_config(),a)
    assert not a.output.exists()


def test_missing_return_fails(tmp_path):
    r=ext.inventory(tmp_path,ext.load_config());assert r['status']=='FAIL'
    assert any('missing' in x for x in r['problems'])


def test_checksum_coverage_cannot_be_empty(tmp_path):
    (tmp_path/'checksums.json').write_text('[]');(tmp_path/'unlisted').write_text('x')
    r=ext.inventory(tmp_path,ext.load_config())
    assert any('manifest does not cover' in x for x in r['problems'])


def test_component_tensor_not_full_state_overlap():
    z=np.linspace(0,1,11);psi=np.zeros((2,8,11),complex);psi[0,0]=1;psi[1,2]=1
    _,t,zm,norm=matrix_data(z,psi)
    np.testing.assert_allclose(np.einsum('abmm->ab',t),np.eye(2))
    assert t[0,1,0,2]==pytest.approx(1)
    np.testing.assert_allclose(zm,np.eye(2)*.5)


def test_tracking_follows_swap_and_phase():
    z=np.linspace(0,1,11);p=np.zeros((2,8,11),complex);p[0,0]=1;p[1,2]=1
    w=np.full(11,.1);w[[0,-1]]=.05
    order,score,gap,flag=assign(p,p[::-1]*1j,w)
    np.testing.assert_array_equal(order,[1,0]);assert not flag.any()
    np.testing.assert_allclose(score,1)


def test_mixed_degenerate_tracking_flagged():
    p=np.zeros((2,8,2),complex);p[0,0]=1;p[1,2]=1
    q=np.array([p[0]+p[1],p[0]-p[1]])/np.sqrt(2)
    assert assign(p,q,np.array([.5,.5]))[-1].all()


def test_no_implicit_optical_mapping():
    with pytest.raises(ValueError,match='Reviewed'):eq2_inputs([], [0,1],[2,3],np.eye(8),{})


def test_plotting_rejects_unreviewed_inputs(tmp_path):
    with pytest.raises(ValueError,match='review'):meeting_spectra({},[],None,{},tmp_path/'plots',{})
    assert not (tmp_path/'plots').exists()


def test_invalid_cutoff_config(tmp_path):
    c=ext.load_config();c['analysis_cutoffs_pi_over_a']=[.21]
    path=tmp_path/'bad.json';path.write_text(json.dumps(c))
    with pytest.raises(ValueError,match='Cutoff'):ext.load_config(path)


def test_complete_inventory_and_corruption(tmp_path,monkeypatch):
    c=ext.load_config();c.update(k_points=2,num_electrons=4,num_holes=4)
    k=np.array([0,c['kmax_pi_over_a']*np.pi/c['lattice_constant_nm']]);energy=np.tile(np.arange(8),(2,1))
    raw=tmp_path/'raw';raw.mkdir();(tmp_path/'decks').mkdir()
    (tmp_path/'decks/extended_8band.in').write_text(ext.render(c))
    (tmp_path/'run_configuration.json').write_text(json.dumps(c))
    (tmp_path/'run_metadata.json').write_text(json.dumps({'professional_execution_performed':True,'return_code':0}))
    (tmp_path/'solver.log').write_text('synthetic unit fixture, not a solve')
    for i in range(2):
        for name in [f'energy_spectrum_k{i:05d}.dat',f'spinor_composition_k{i:05d}_CbHhLhSo.dat']:
            (raw/name).touch()
        for s in range(1,9):
            for tag in ext.io.KP8_COMPONENTS:(raw/f'envelope_k{i:05d}_{s:04d}_{tag}.dat').touch()
    monkeypatch.setattr(ext.io,'read_dispersion',lambda p:(k,energy,{'direction':[0,1,0]}))
    monkeypatch.setattr(ext.io,'read_energy_spectrum',lambda p:np.arange(8))
    monkeypatch.setattr(ext.io,'read_composition',lambda p:{tag:np.full(8,.125) for tag in ext.io.KP8_COMPONENTS})
    (tmp_path/'checksums.json').write_text(json.dumps(ext.manifest(tmp_path)))
    assert ext.inventory(tmp_path,c)['status']=='PASS'
    (raw/'envelope_k00001_0008_so2.dat').write_text('corrupt')
    assert any('checksum mismatch' in x for x in ext.inventory(tmp_path,c)['problems'])


def test_reviewed_adapter_finite_k(tmp_path):
    blocks=[]
    for i in range(2):
        path=tmp_path/f'k{i}.npz';tensor=np.zeros((4,4,8,8),complex)
        tensor[:2,2:,0,2]=i+1
        np.savez(path,k_per_nm=i*.1,energy_eV=[3,4,1,2],branch_to_solver=[1,2,3,4],
                 component_overlap=tensor,z_nm=np.eye(4),ambiguous=np.zeros(4,bool))
        blocks.append(path)
    operator=np.zeros((8,8));operator[0,2]=1
    review={key:'synthetic test only' for key in ('operator_source','basis_convention','branch_selection','spin_convention','model_scope')};review['approved']=True
    inputs=eq2_inputs(blocks,[0,1],[2,3],operator,review)
    assert inputs['overlap'].shape==(2,2,2)
    np.testing.assert_allclose(inputs['overlap'][:,:,0],1)
    np.testing.assert_allclose(inputs['overlap'][:,:,1],2)
    np.testing.assert_array_equal(inputs['electron_eV'],[[3,3],[4,4]])


def test_future_plots_synthetic_only(tmp_path):
    from chi2.equation2 import Settings
    c=ext.load_config();k=np.linspace(0,c['kmax_pi_over_a']*np.pi/c['lattice_constant_nm'],1201)
    inputs={'k_per_nm':k,'electron_eV':np.tile([[3],[3.1]],(1,len(k))),
            'valence_eV':np.tile([[1.4],[1.3]],(1,len(k)))}
    for key,m in [('overlap',[[1,.2],[.3,1]]),('ze_nm',[[.1,.2],[.2,-.1]]),('zh_nm',[[.2,.1],[.1,-.2]])]:
        inputs[key]=np.repeat(np.array(m)[:,:,None],len(k),axis=2)
    out=tmp_path/'SYNTHETIC_NOT_PHYSICS'
    meeting_spectra(inputs,np.linspace(1400,1700,61),Settings(),c,out,{'approved':True,'model_scope':'synthetic software fixture only'})
    assert len(list((out/'plots').glob('*.png')))==4
    table=np.loadtxt(out/'cutoff_diagnostics.csv',delimiter=',',skiprows=1)
    assert np.all(table[:,1]<=table[:,0]*np.pi/c['lattice_constant_nm'])
    assert len(table)==13
