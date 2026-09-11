"""Cached extended-k diagnostic using the single authoritative Eq2."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from chi2.studies import setup
from chi2.equation2 import calculate_chi2
from chi2.k_integration import select_range
from chi2.artifacts import save_inputs,save_spectrum,write_json,csv
from chi2.diagnostics import features
from chi2 import plotting


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--config',type=Path,default=ROOT/'config/extended_k.json');ap.add_argument('--input',type=Path);ap.add_argument('--output',type=Path,default=ROOT/'outputs/28C_extended_k')
    args=ap.parse_args(argv);cfg=json.loads(args.config.read_text());out=args.output
    _,settings,wl,inputs,meta=setup(ROOT/cfg['baseline_config'],args.input or ROOT/cfg['raw_input'],out)
    cases=[];rows=[];tracked=[];probes=[]
    for fraction in cfg['k_cutoffs_pi_over_a']:
        requested=fraction*np.pi/cfg['lattice_constant_nm']
        if requested>inputs['k_per_nm'][-1]+5e-10: raise ValueError('Requested cutoff outside solved extended data')
        chosen=select_range(inputs,min(requested,float(inputs['k_per_nm'][-1])))
        dest=out/'cases'/f'kmax_{fraction:.4f}'
        save_inputs(dest/'chi2_inputs',chosen,settings,wl)
        spectrum=calculate_chi2(wl,chosen,settings);save_spectrum(dest/'chi2_results',spectrum,False)
        feat=features(wl,spectrum.chi2_complex,lambda w:calculate_chi2(w,chosen,settings).chi2_complex)
        case=dict(fraction=fraction,actual_kmax_per_nm=chosen['k_per_nm'][-1],k_points=len(chosen['k_per_nm']),features=feat,
                  all_samples_within_requested_cutoff=bool(np.all(chosen['k_per_nm']<=requested)),
                  physical_status=cfg['physical_status'],licensed_solver_executed=False,settings=meta['settings'])
        write_json(dest/'metadata.json',{**meta,**case,'study':'28C','extended_config':cfg,
                  'raw_manifest':'../../raw_manifest.json','code_manifest':'../../code_manifest.json',
                  'requested_kmax_per_nm':requested,'selection':chosen['selection']});cases.append((case,spectrum.chi2_complex))
        probe=calculate_chi2(np.array(cfg['probe_wavelengths_nm'],float),chosen,settings).chi2_complex
        probes.append([fraction,chosen['k_per_nm'][-1],len(chosen['k_per_nm']),*np.column_stack([probe.real,probe.imag]).ravel()])
        rows.append([fraction,chosen['k_per_nm'][-1],len(chosen['k_per_nm']),feat['dominant_abs_Re_wavelength_nm'],feat['dominant_abs_Im_wavelength_nm'],feat['Re_at_target_pm_per_V'],feat['Im_at_target_pm_per_V']])
        for feature_id,(name,window) in enumerate(cfg['feature_windows_nm'].items()):
            values=spectrum.chi2_complex.real if name.startswith('Re') else spectrum.chi2_complex.imag
            candidates=np.flatnonzero((wl>=window[0])&(wl<=window[1]))
            local=np.argmax(values[candidates]) if 'positive' in name else np.argmin(values[candidates])
            i=candidates[local]
            tracked.append([fraction,feature_id,wl[i],values[i],int(0<local<len(candidates)-1)])
    for component,label in [('real','Re'),('imag','Im')]:
        fig,ax=plotting.axes(ylabel=rf'{label} $\chi^{{(2)}}$ (pm/V)')
        for case,chi in cases: ax.plot(wl,getattr(chi,component),lw=1.5,label=rf"{case['fraction']:g} $\pi/a$")
        ax.set_xlim(wl[0],wl[-1]);plotting.save(fig,ax,out/'plots',f'28C_{component}_extended_cutoffs')
    csv(out/'extended_cutoffs.csv',rows,'cutoff_pi_over_a,actual_kmax_per_nm,k_points,dominant_abs_Re_nm,dominant_abs_Im_nm,Re1550_pm_per_V,Im1550_pm_per_V')
    csv(out/'windowed_features.csv',tracked,'cutoff_pi_over_a,feature_id,wavelength_nm,signed_amplitude_pm_per_V,interior_extremum')
    csv(out/'probe_convergence.csv',probes,'cutoff_pi_over_a,kmax_nm_minus1,Nk,'+','.join(f'{part}_{w:g}_pm_per_V' for w in cfg['probe_wavelengths_nm'] for part in ['Re','Im']))
    for comp,label,col in [('real','Re',0),('imag','Im',1)]:
        fig,ax=plotting.axes(xlabel=r'$k_{max}/(\pi/a)$',ylabel=rf'{label} $\chi^{{(2)}}$ (pm/V)')
        for j,w in enumerate(cfg['probe_wavelengths_nm']):ax.plot(np.array(probes)[:,0],np.array(probes)[:,3+2*j+col],'-o',ms=3,label=f'{w:g} nm')
        plotting.save(fig,ax,out/'plots',f'28C_{comp}_probe_convergence')
    change=cases[-1][1]-cases[0][1]
    meta.update(study='28C',timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),extended_config=cfg,
                k_max_per_nm=float(inputs['k_per_nm'][-1]),k_points=len(inputs['k_per_nm']),cases=[c for c,_ in cases],
                max_complex_change_first_to_last_pm_per_V=float(max(abs(change))),
                interpretation='Cutoffs within one extended native grid; do not conflate its 301-point density with baseline301 at smaller kmax',
                feature_tracking='Named fixed windows only, sampled 1nm extrema; interior flag must be true. Global Im maximum switches lobes, not a continuously shifting branch.',
                high_k_validity='UNRESOLVED; historical h2 is LH dominated and finite-k spinors unavailable in cached data')
    write_json(out/'metadata.json',meta);print('28C cached diagnostic complete:',out)
    return meta


if __name__=='__main__': main()
