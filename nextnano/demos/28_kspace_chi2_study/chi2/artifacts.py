"""Save each data stage explicitly; raw files are never rewritten here."""
from dataclasses import asdict
import hashlib
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
from .equation2 import photon_energy,expand_matrices
from .k_integration import radial_weights


def serial(value):
    if isinstance(value,np.ndarray): return value.tolist()
    if isinstance(value,np.generic): return value.item()
    if isinstance(value,Path): return str(value)
    if isinstance(value,complex): return {'real':value.real,'imag':value.imag}
    raise TypeError(type(value).__name__)


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.name=='metadata.json' and isinstance(value,dict):
        value={'timestamp_utc':datetime.now(timezone.utc).isoformat(),
               'equation_implementation_sha256':hashlib.sha256((Path(__file__).parent/'equation2.py').read_bytes()).hexdigest(),
               **value}
    path.write_text(json.dumps(value,indent=2,default=serial)+'\n',encoding='utf-8')


def csv(path,data,header):
    np.savetxt(path,data,delimiter=',',header=header,comments='',fmt='%.17g')


def manifest(raw_root):
    root=Path(raw_root)
    return [{'file':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(root.rglob('*')) if p.is_file()]


def save_parsed(out,parsed):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    csv(out/'kp8_energies.csv',np.column_stack([parsed['k_per_nm'],parsed['all_kp8_energies_eV']]),
        'k_per_nm,'+','.join(f'state_{i+1}_eV' for i in range(parsed['all_kp8_energies_eV'].shape[1])))
    csv(out/'selected_pair_energies.csv',np.column_stack([parsed['k_per_nm'],parsed['selected_pair_mean_energies_eV'].T]),
        'k_per_nm,e1_raw_eV,e2_raw_eV,h1_raw_eV,h2_raw_eV')
    csv(out/'normalized_singleband_envelopes.csv',np.column_stack([parsed['z_nm'],parsed['electron_env'],parsed['hole_env']]),
        'z_nm,e1_nm_minus_half,e2_nm_minus_half,h1_nm_minus_half,h2_nm_minus_half')
    csv(out/'singleband_k0_energies.csv',np.column_stack([np.arange(1,3),parsed['electron_eV'],parsed['hole_eV']]),
        'state_index,electron_energy_eV,valence_electron_energy_eV')
    np.save(out/'k0_spinor_composition.npy',parsed['composition'])
    write_json(out/'metadata.json',{'stage':'parsed raw energies + explicitly unit-normalized envelopes',
       'energy_units':'eV; common nextnano electron-energy reference','envelope_units':'nm^-1/2','z_units':'nm',
       'composition_columns':['cb1','cb2','hh1','hh2','lh1','lh2','so1','so2']})


def save_inputs(out,inputs,settings,wl):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    k=np.asarray(inputs['k_per_nm'])
    weights=radial_weights(k,settings.spin_degeneracy)
    csv(out/'k_per_nm.csv',np.column_stack([k,weights]),'k_per_nm,integration_weight_nm_minus2')
    for key,name in [('electron_eV','electron_energies.csv'),('valence_eV','hole_energies.csv')]:
        csv(out/name,np.column_stack([k,np.asarray(inputs[key]).T]),'k_per_nm,state_1_eV,state_2_eV')
    transition=np.asarray(inputs['electron_eV'])[:,None,:]-np.asarray(inputs['valence_eV'])[None,:,:]
    csv(out/'transition_energies.csv',np.column_stack([k,transition.reshape(4,len(k)).T]),'k_per_nm,E11_eV,E12_eV,E21_eV,E22_eV')
    matrices=expand_matrices(inputs,len(k))
    for name,m in zip(['overlap_eh.npy','z_e.npy','z_h.npy'],matrices): np.save(out/name,m)
    meta={'stage':'derived chi2 inputs (not raw nextnano)', 'settings':asdict(settings),'gamma_eV':settings.gamma_eV,
          'shapes':{'energies':[2,len(k)],'transitions':[2,2,len(k)],'matrices':[2,2,len(k)],'wavelength':[len(wl)]},
          'units':{'energies':'eV','k':'nm^-1','weights':'nm^-2','overlap':'dimensionless','z':'nm','wavelength':'fundamental nm'},
          'matrix_treatment':'constant matrices broadcast to every k; no finite-k matrices fabricated',
          'state_order':['e1','e2','h1','h2'],'kp8_pair_ids':inputs['kp8_pair_ids'],
          'selection':inputs.get('selection'),'model':inputs['model'],'limitations':inputs['limitations']}
    write_json(out/'metadata.json',meta)


def save_spectrum(out,result,save_integrand=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    wl,c=result.wavelength_nm,result.chi2_complex
    csv(out/'chi2_spectrum.csv',np.column_stack([wl,photon_energy(wl),c.real,c.imag,abs(c.real),abs(c)]),
        'wavelength_nm,photon_energy_eV,chi2_real_pm_per_V,chi2_imag_pm_per_V,chi2_abs_real_pm_per_V,chi2_abs_pm_per_V')
    np.save(out/'chi2_complex.npy',c)
    np.savez_compressed(out/'pathways.npz',values=result.pathways_complex,labels=np.array(result.pathway_labels))
    if save_integrand:
        np.savez_compressed(out/'chi2_k_lambda_integrand.npz',summed_integrand=result.summed_integrand,
                            k_weights_nm_minus2=result.k_weights_nm_minus2,wavelength_nm=wl)
