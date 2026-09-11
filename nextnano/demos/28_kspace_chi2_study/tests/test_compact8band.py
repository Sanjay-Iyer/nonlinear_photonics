"""Synthetic file fixtures only: never invoke a licensed executable."""
import json
from pathlib import Path
import numpy as np
import pytest
from chi2 import extended8band as ext
from chi2.compact8band import pack,source_frames,validate_compact
from chi2.finite8band import ingest


@pytest.fixture
def raw_run(tmp_path):
    root=tmp_path/'raw_run';raw=root/'raw';raw.mkdir(parents=True);(root/'decks').mkdir()
    c=ext.load_config();c.update(k_points=2,num_electrons=4,num_holes=4)
    (root/'run_configuration.json').write_text(json.dumps(c))
    (root/'decks/extended_8band.in').write_text(ext.render(c))
    (root/'run_metadata.json').write_text(json.dumps({'professional_execution_performed':True,'return_code':0,'note':'SYNTHETIC SOFTWARE TEST'}))
    (root/'solver.log').write_text('SYNTHETIC fixture; no actual solve')
    (root/'requested_k_grid.csv').write_text('synthetic provenance fixture')
    k=np.linspace(0,c['kmax_pi_over_a']*np.pi/c['lattice_constant_nm'],2)
    e=np.tile(np.arange(8,dtype=float),(2,1));e[1]+=.1
    def table(path,data,header):np.savetxt(path,data,header=header,comments='',fmt='%.18e')
    table(raw/'dispersion_test.dat',np.column_stack([k,e]),'k '+' '.join(f'e{s}' for s in range(8)))
    table(raw/'kVectors_test.dat',np.column_stack([np.arange(2),np.zeros(2),k,np.zeros(2)]),'index kx ky kz')
    z=np.linspace(0,1,7)
    for i in range(2):
        table(raw/f'energy_spectrum_k{i:05d}.dat',np.column_stack([np.arange(1,9),e[i]]),'state energy')
        table(raw/f'spinor_composition_k{i:05d}_CbHhLhSo.dat',np.column_stack([np.arange(1,9),np.eye(8)]),'state '+' '.join(ext.io.KP8_COMPONENTS))
        for s in range(8):
            for mu,tag in enumerate(ext.io.KP8_COMPONENTS):
                v=np.full(len(z),np.exp(1j*(i+s/10)) if mu==s else 0,dtype=complex)
                table(raw/f'envelope_k{i:05d}_{s+1:04d}_{tag}.dat',np.column_stack([z,v.real,v.imag]),'z real imag')
    (root/'checksums.json').write_text(json.dumps(ext.manifest(root)))
    return root,c


def test_lossless_compact_and_ingest(raw_run,tmp_path):
    raw,c=raw_run
    assert ext.inventory(raw,c)['status']=='PASS'
    out=pack(raw,tmp_path/'transfer')
    assert ext.inventory(out,c)['status']=='PASS'
    for a,b in zip(source_frames(raw),source_frames(out)):
        for left,right in zip(a,b):np.testing.assert_array_equal(left,right)
    ingest(raw,tmp_path/'raw_analysis',c);ingest(out,tmp_path/'packed_analysis',c)
    for i in range(2):
        with np.load(tmp_path/'raw_analysis/operator_blocks'/f'k{i:05d}.npz') as a,np.load(tmp_path/'packed_analysis/operator_blocks'/f'k{i:05d}.npz') as b:
            for key in a.files:np.testing.assert_array_equal(a[key],b[key])
    assert (raw/'raw/envelope_k00001_0008_so2.dat').exists()


def test_pack_does_not_change_original(raw_run,tmp_path):
    raw,c=raw_run;before=ext.manifest(raw)
    out=pack(raw,tmp_path/'transfer')
    assert before==ext.manifest(raw)
    assert not (out/'raw').exists()
    with pytest.raises(ValueError,match='new transfer'):pack(raw,out)
    with pytest.raises(ValueError,match='outside'):pack(raw,raw/'transfer')


def test_compact_missing_frame_fails(raw_run,tmp_path):
    raw,c=raw_run;out=pack(raw,tmp_path/'transfer')
    # Rename one fixture file, without deleting data.
    (out/'frames/k00001.npz').rename(out/'frames/wrong.npz')
    assert validate_compact(out,c)['status']=='FAIL'


def test_compact_corruption_fails(raw_run,tmp_path):
    raw,c=raw_run;out=pack(raw,tmp_path/'transfer')
    (out/'frames/k00001.npz').write_bytes(b'not an npz')
    assert validate_compact(out,c)['status']=='FAIL'


def test_budget_no_silent_truncation(raw_run,tmp_path):
    raw,c=raw_run;c['transfer_limit_bytes']=1
    (raw/'run_configuration.json').write_text(json.dumps(c))
    (raw/'checksums.json').write_text(json.dumps([r for r in ext.manifest(raw) if r['file']!='checksums.json']))
    with pytest.raises(ValueError,match='budget'):pack(raw,tmp_path/'over_budget')
    assert (raw/'raw/envelope_k00001_0008_so2.dat').exists()
    assert len(list((tmp_path/'over_budget/frames').glob('*.npz')))==2


def test_cli_validation_uses_bundle_config(raw_run,tmp_path):
    raw,_=raw_run;out=pack(raw,tmp_path/'transfer')
    assert ext.main(['--validate',str(out)])==0  # two-point fixture, not current 601-point config


def test_pilot_preflight_only(tmp_path,monkeypatch):
    monkeypatch.setattr(ext,'PLAN',tmp_path/'plan')
    monkeypatch.setattr(ext,'machine_paths',lambda args:(None,None,None))
    monkeypatch.setattr(ext,'discover_parser',lambda:(None,None))
    monkeypatch.setattr(ext.subprocess,'Popen',lambda *args,**kwargs:pytest.fail('No solver during preflight'))
    assert ext.main(['--preflight','--pilot','--no-parse'])==0
    c=json.loads((tmp_path/'plan/pilot/runner.json').read_text())
    assert c['k_points']==3 and c['pilot'] and c['num_holes']==16
    assert not (tmp_path/'plan/runner.json').exists()


def test_legacy_render_preserved():
    c=ext.load_config();c.pop('output_profile');c['k_points']=1201
    deck=ext.render(c)
    assert 'envelopes = yes' in deck and 'energy_shift = not_shifted' not in deck


def test_pilot_not_production(tmp_path):
    c=ext.load_config();c['pilot']=True
    with pytest.raises(ValueError,match='Pilot'):ingest(tmp_path,tmp_path/'analysis',c)


def test_runner_auto_packs_with_fake_solver(raw_run,tmp_path,monkeypatch):
    import argparse
    import shutil
    raw,c=raw_run
    exe=tmp_path/'professional_test.exe';exe.touch()
    db=tmp_path/'db';db.touch();lic=tmp_path/'lic';lic.touch()
    monkeypatch.setattr(ext,'PLAN',tmp_path/'plan')
    monkeypatch.setattr(ext,'parse_check',lambda *args,**kwargs:{'status':'PASS','parser':'synthetic','errors':[]})
    monkeypatch.setattr(ext,'machine_paths',lambda args:(str(exe),str(db),str(lic)))
    monkeypatch.setattr(ext.subprocess,'Popen',lambda *args,**kwargs:pytest.fail('Real process forbidden'))
    def fake(argv,result,config,interval):
        shutil.copytree(raw/'raw',result/'raw')
        (result/'solver.log').write_text('synthetic output contract fixture, NOT a Professional solve')
        return 0
    monkeypatch.setattr(ext,'watch_solver',fake)
    args=argparse.Namespace(output=tmp_path/'newrun',progress_interval=60)
    assert ext.run(c,args)==0
    assert validate_compact(tmp_path/'newrun_transfer',c)['status']=='PASS'
    assert (tmp_path/'newrun/raw').is_dir()


def test_changed_state_id_refused(raw_run,tmp_path):
    raw,c=raw_run
    path=raw/'raw/energy_spectrum_k00001.dat'
    data=np.loadtxt(path,skiprows=1);data[0,0]=8
    np.savetxt(path,data,header='state energy',comments='')
    (raw/'checksums.json').write_text(json.dumps([r for r in ext.manifest(raw) if r['file']!='checksums.json']))
    with pytest.raises(ValueError,match='state IDs'):pack(raw,tmp_path/'transfer')
