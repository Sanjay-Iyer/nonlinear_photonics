"""28D/E/G: controlled response diagnostics; all susceptibilities use equation2.

No independent Equation 2 evaluator is defined here. Resonance windows use the
actual transition-energy arrays; they are diagnostics, not fitted physics.
"""
import argparse
import csv as csv_module
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from scipy.signal import find_peaks, peak_widths
from .equation2 import calculate_chi2, photon_energy, expand_matrices, HC_EV_NM
from .artifacts import write_json, save_inputs, save_spectrum, csv
from .diagnostics import features
from .studies import ROOT, setup
from .plotting import axes, save, plt


def validate_configuration(cfg):
    gamma=np.asarray(cfg['gamma_meV'],float)
    if gamma.ndim!=1 or not len(gamma) or not np.isfinite(gamma).all() or np.any(gamma<=0) or np.any(np.diff(gamma)<=0):
        raise ValueError('gamma_meV must be positive finite strictly increasing values')
    if not all(g in gamma for g in cfg['selected_gamma_meV']):
        raise ValueError('Selected gamma values must be in gamma_meV')
    near,off=(float(cfg[k]) for k in ('near_resonance_detuning_meV','off_resonance_detuning_meV'))
    if not 0<near<off or not np.isfinite(off): raise ValueError('Require 0 < near < off detuning')
    if not 0<cfg['ratio_real_floor_fraction']<1: raise ValueError('Invalid ratio floor')
    if not 1<=cfg['top_pathways']<=8: raise ValueError('Show only 1 to 8 top pathways')
    return cfg


def resonance_detuning(wl,inputs):
    """Minimum |E_nm(k)-p*hw|, p=1 or 2, over existing solved k nodes."""
    transitions=np.asarray(inputs['electron_eV'])[:,None,:]-np.asarray(inputs['valence_eV'])[None,:,:]
    energy=photon_energy(wl)
    delta=np.full(len(energy),np.inf)
    for transition in transitions.reshape(4,-1):
        for factor in (1,2):
            delta=np.minimum(delta,np.min(abs(transition[None,:]-factor*energy[:,None]),axis=1))
    return delta


def safe_ratio(chi,floor_fraction):
    """Mask rather than regularize ratios where Re is too small for stability."""
    floor=floor_fraction*np.max(abs(chi.real))
    valid=abs(chi.real)>max(floor,np.finfo(float).tiny)
    ratio=np.full(len(chi),np.nan)
    ratio[valid]=abs(chi.imag[valid])/abs(chi.real[valid])
    return ratio,valid,float(floor)


def region_metrics(chi,mask,ratio,valid):
    n=int(mask.sum()); chosen=mask&valid
    if not n: return {'samples':0,'status':'NO_SAMPLES'}
    re=np.linalg.norm(chi.real[mask]);im=np.linalg.norm(chi.imag[mask])
    return {'samples':n,'safe_ratio_samples':int(chosen.sum()),
            'l2_abs_Im_over_Re':float(im/re) if re else None,
            'median_safe_abs_Im_over_Re':float(np.median(ratio[chosen])) if chosen.any() else None,
            'fraction_Im_dominant':float(np.mean(abs(chi.imag[mask])>abs(chi.real[mask]))),
            'fraction_Re_dominant':float(np.mean(abs(chi.real[mask])>abs(chi.imag[mask])))}


def sampled_lobe_width(wl,component):
    """Half-prominence width of dominant absolute lobe, not fitted lifetime."""
    y=abs(component); dominant=int(np.argmax(y));peaks=find_peaks(y)[0]
    if dominant not in peaks: return {'status':'EDGE_MAXIMUM','width_nm':None}
    widths,_,left,right=peak_widths(y,[dominant],rel_height=.5)
    axis=np.arange(len(wl))
    return {'status':'SAMPLED_HALF_PROMINENCE_LOBE','width_nm':float(np.interp(right[0],axis,wl)-np.interp(left[0],axis,wl)),
            'points_across_width':float(widths[0]),'peak_nm':float(wl[dominant])}


def cancellation_metrics(pathways,indices=None):
    values=pathways if indices is None else pathways[indices]
    individual=float(np.sum(np.linalg.norm(values,axis=1)))
    coherent=float(np.linalg.norm(values.sum(axis=0)))
    return {'sum_individual_l2_pm_per_V':individual,'summed_l2_pm_per_V':coherent,
            'retained_l2_fraction':coherent/individual if individual else None,
            'cancellation_fraction':1-coherent/individual if individual else None}


def write_rows(path,rows):
    with Path(path).open('w',newline='',encoding='utf-8') as handle:
        writer=csv_module.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def code_provenance():
    try:
        commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    except (OSError,subprocess.CalledProcessError): commit=None
    return {'timestamp_utc':datetime.now(timezone.utc).isoformat(),'git_commit':commit,
            'code_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'chi2').glob('*.py'))},
            'equation_implementation':'chi2/equation2.py::calculate_chi2',
            'code_note':'Source hashes identify working-tree code even if Git commit is unavailable or dirty.'}


def component_plot(out,name,wl,curves,component):
    fig,ax=axes(ylabel=rf'{"Re" if component=="real" else "Im"} $\chi^{{(2)}}$ (pm/V)')
    for label,chi in curves: ax.plot(wl,getattr(chi,component),lw=1.5,label=label)
    ax.set_xlim(wl[0],wl[-1]);save(fig,ax,out,name)


def run(config=ROOT/'config/response_audit.json',raw_root=None,output_root=ROOT/'outputs',make_plots=True):
    cfg=validate_configuration(json.loads(Path(config).read_text()))
    output_root=Path(output_root);d=output_root/'28D_imaginary_source';e=output_root/'28E_linewidth';g=output_root/'28G_pathways'
    for directory in (d,e,g): directory.mkdir(parents=True,exist_ok=True)
    _,settings,wl,inputs,meta=setup(ROOT/cfg['baseline_config'],raw_root,d)
    save_inputs(d/'chi2_inputs',inputs,settings,wl)
    meta.update(code_provenance(),response_configuration=cfg,k_units='nm^-1',k_points=len(inputs['k_per_nm']),
                k_min_per_nm=float(inputs['k_per_nm'][0]),k_max_per_nm=float(inputs['k_per_nm'][-1]),
                BZ_conversion='q = k/(pi/a); radial isotropic disk approximation, not an asserted exact BZ geometry',
                lattice_constant_nm=cfg['lattice_constant_nm'],input_arrays='../28D_imaginary_source/chi2_inputs',
                numerical_warning='Small Gamma on fixed 301-point k and 1 nm wavelength grids is not a converged Gamma-to-zero limit.')
    baseline=calculate_chi2(wl,inputs,settings)
    save_spectrum(d/'baseline',baseline,True)
    labels=baseline.pathway_labels
    electron=np.array([i for i,label in enumerate(labels) if label.startswith('C_')]);hole=np.array([i for i,label in enumerate(labels) if label.startswith('V_')])
    ce=baseline.pathways_complex[electron].sum(axis=0);ch=baseline.pathways_complex[hole].sum(axis=0)
    group_error=float(np.max(abs(ce+ch-baseline.chi2_complex)))
    csv(d/'electron_hole_total.csv',np.column_stack([wl,ce.real,ce.imag,ch.real,ch.imag,baseline.chi2_complex.real,baseline.chi2_complex.imag]),
        'wavelength_nm,electron_Re_pm_per_V,electron_Im_pm_per_V,hole_Re_pm_per_V,hole_Im_pm_per_V,total_Re_pm_per_V,total_Im_pm_per_V')
    # Numerators and transition definitions are provided by the same authoritative
    # core used to compute the spectrum; no second Equation 2 is implemented here.
    from .equation2 import pathway_definitions
    definitions=list(pathway_definitions(inputs))
    numerators=np.asarray([p['numerator'] for p in definitions])
    np.savez_compressed(g/'numerators.npz',labels=np.asarray(labels),numerators_nm=numerators,k_per_nm=inputs['k_per_nm'],
                        one_transition_eV=np.asarray([p['one_transition_eV'] for p in definitions]),
                        two_transition_eV=np.asarray([p['two_transition_eV'] for p in definitions]))
    matrices=expand_matrices(inputs,len(inputs['k_per_nm']))
    numerator_imag=float(np.max(abs(numerators.imag)))
    # This cached baseline has real matrices, so the real-numerator variant is
    # exactly the same mathematical input. Never strip arbitrary complex phases
    # in a future complex dataset (that would not isolate invariant products).
    if any(np.any(m.imag!=0) for m in matrices):
        raise ValueError('D5 requires the currently real cached matrices; a complex dataset needs product-level core support')
    real_inputs={**inputs,**dict(zip(('overlap','ze_nm','zh_nm'),[m.real for m in matrices]))}
    real_variant=calculate_chi2(wl,real_inputs,settings)
    real_error=float(np.max(abs(real_variant.chi2_complex-baseline.chi2_complex)))
    save_spectrum(d/'real_numerators',real_variant)
    delta=resonance_detuning(wl,inputs)
    near=delta<=cfg['near_resonance_detuning_meV']*1e-3
    off=delta>=cfg['off_resonance_detuning_meV']*1e-3
    gamma_cases=[];gamma_rows=[]
    for gamma in cfg['gamma_meV']:
        setting=replace(settings,gamma_meV=float(gamma))
        result=baseline if gamma==settings.gamma_meV else calculate_chi2(wl,inputs,setting)
        name=f'gamma_{gamma:g}_meV'.replace('.','p');dest=e/'cases'/name
        save_spectrum(dest,result)
        ec=result.pathways_complex[[label.startswith('C_') for label in result.pathway_labels]].sum(axis=0)
        hc=result.pathways_complex[[label.startswith('V_') for label in result.pathway_labels]].sum(axis=0)
        cancellation=1-abs(result.chi2_complex)/np.maximum(abs(ec)+abs(hc),np.finfo(float).eps)
        csv(dest/'electron_hole_total.csv',np.column_stack([wl,ec.real,ec.imag,hc.real,hc.imag,result.chi2_complex.real,result.chi2_complex.imag,cancellation]),
            'wavelength_nm,Re_electron,Im_electron,Re_hole,Im_hole,Re_total,Im_total,cancellation_fraction_modulus')
        ratio,valid,floor=safe_ratio(result.chi2_complex,cfg['ratio_real_floor_fraction'])
        f=features(wl,result.chi2_complex,lambda w:calculate_chi2(w,inputs,setting).chi2_complex)
        near_metrics=region_metrics(result.chi2_complex,near,ratio,valid);off_metrics=region_metrics(result.chi2_complex,off,ratio,valid)
        widths={field:sampled_lobe_width(wl,getattr(result.chi2_complex,component)) for field,component in [('Re','real'),('Im','imag')]}
        record={**meta,'study':'28E_linewidth','settings':asdict(setting),'gamma_eV':setting.gamma_eV,
                'raw_manifest':'../../../28D_imaginary_source/raw_manifest.json',
                'code_manifest':'../../../28D_imaginary_source/code_manifest.json',
                'input_arrays':'../../../28D_imaginary_source/chi2_inputs','features':f,'near_resonance':near_metrics,'off_resonance':off_metrics,
                'ratio_real_floor_pm_per_V':floor,'apparent_lobe_width':widths,
                'resonance_definition':'min over solved k, n,m and p=1,2 of |E_nm(k)-p*hc/lambda|; fixed energy masks across all Gamma',
                'wavelength_energy_step_max_eV':float(np.max(abs(np.diff(photon_energy(wl)))))}
        write_json(dest/'metadata.json',record)
        csv(dest/'ratio_resonance.csv',np.column_stack([wl,delta,near,off,ratio,valid]),'wavelength_nm,min_detuning_eV,near_mask,off_mask,abs_Im_over_Re,ratio_valid')
        gamma_cases.append((gamma,result.chi2_complex,record))
        gamma_rows.append({'gamma_meV':gamma,'Re_peak_nm':f['dominant_abs_Re_wavelength_nm'],'Im_peak_nm':f['dominant_abs_Im_wavelength_nm'],
                           'max_abs_Re_pm_per_V':f['max_abs_Re_pm_per_V'],'max_abs_Im_pm_per_V':f['max_abs_Im_pm_per_V'],
                           'Re_zero_nm':json.dumps([r['wavelength_nm'] for r in f['Re_zero_crossings']]),
                           'Re_lobe_width_nm':widths['Re']['width_nm'],'Im_lobe_width_nm':widths['Im']['width_nm'],
                           'near_l2_Im_over_Re':near_metrics.get('l2_abs_Im_over_Re'),'off_l2_Im_over_Re':off_metrics.get('l2_abs_Im_over_Re'),
                           'near_fraction_Im_dominant':near_metrics.get('fraction_Im_dominant'),'off_fraction_Im_dominant':off_metrics.get('fraction_Im_dominant')})
    write_rows(e/'gamma_summary.csv',gamma_rows)
    small=gamma_cases[0];base_ratio,base_valid,_=safe_ratio(baseline.chi2_complex,cfg['ratio_real_floor_fraction'])
    dmeta={**meta,'study':'28D_imaginary_source','matrix_max_abs_imag':dict(zip(['overlap','z_e_nm','z_h_nm'],[float(np.max(abs(m.imag))) for m in matrices])),
           'numerator_max_abs_imag_nm':numerator_imag,'full_vs_real_numerator_max_error_pm_per_V':real_error,
           'electron_hole_sum_max_error_pm_per_V':group_error,
           'electron_peak_abs_Im_pm_per_V':float(max(abs(ce.imag))),'hole_peak_abs_Im_pm_per_V':float(max(abs(ch.imag))),
           'total_peak_abs_Im_pm_per_V':float(max(abs(baseline.chi2_complex.imag))),
           'near_resonance_baseline':region_metrics(baseline.chi2_complex,near,base_ratio,base_valid),
           'off_resonance_baseline':region_metrics(baseline.chi2_complex,off,base_ratio,base_valid),
           'small_gamma_meV':small[0],'small_gamma_off_resonance':small[2]['off_resonance'],
           'interpretation':'Current gauge-invariant pathway numerators are real. Nonzero Im comes from complex denominators, then pathway addition/cancellation. No excited populations propagated; not a calibrated nonlinear-absorption measurement.'}
    write_json(d/'metadata.json',dmeta)
    write_json(e/'metadata.json',{**meta,'study':'28E_linewidth','raw_manifest':'../28D_imaginary_source/raw_manifest.json',
                                'code_manifest':'../28D_imaginary_source/code_manifest.json','gamma_cases':gamma_rows,
                                'near_samples':int(near.sum()),'off_samples':int(off.sum()),'ratio_masked_samples_baseline':int((~base_valid).sum())})
    # All sixteen integrated contributions are retained, even though plots show four.
    save_spectrum(g/'chi2_results',baseline)
    rows=[];resonance_rows=[]
    diagonal=[];offdiag=[]
    for i,p in enumerate(definitions):
        m,n,ell=p['m'],p['n'],p['ell'];kind=p['kind']
        is_diagonal=(n==ell if kind=='C' else m==ell)
        (diagonal if is_diagonal else offdiag).append(i)
        value=baseline.pathways_complex[i]
        rows.append({'label':labels[i],'kind':kind,'m_1based':m+1,'n_1based':n+1,'ell_1based':ell+1,'diagonal_z':is_diagonal,
                     'numerator_real_min_nm':float(numerators[i].real.min()),'numerator_real_max_nm':float(numerators[i].real.max()),
                     'numerator_imag_abs_max_nm':float(max(abs(numerators[i].imag))),
                     'one_photon_denominator':f'E_transition_one(k)-hc/lambda+i*{settings.gamma_eV:g} eV',
                     'two_photon_denominator':f'E_transition_two(k)-2hc/lambda+i*{settings.gamma_eV:g} eV',
                     'one_photon_resonance_min_nm':float(min(HC_EV_NM/p['one_transition_eV'])),
                     'one_photon_resonance_max_nm':float(max(HC_EV_NM/p['one_transition_eV'])),
                     'two_photon_resonance_min_nm':float(min(2*HC_EV_NM/p['two_transition_eV'])),
                     'two_photon_resonance_max_nm':float(max(2*HC_EV_NM/p['two_transition_eV'])),
                     'max_abs_Re_pm_per_V':float(max(abs(value.real))),'max_abs_Im_pm_per_V':float(max(abs(value.imag))),
                     'l2_complex_pm_per_V':float(np.linalg.norm(value))})
    write_rows(g/'pathway_table.csv',rows)
    csv(g/'pathway_spectra.csv',np.column_stack([wl]+[a for value in baseline.pathways_complex for a in (value.real,value.imag)]),
        'wavelength_nm,'+','.join(f'{label}_{field}_pm_per_V' for label in labels for field in ('Re','Im')))
    pair_rows=[]
    for i in range(16):
        for j in range(i+1,16):
            metric=cancellation_metrics(baseline.pathways_complex,[i,j])
            pair_rows.append({'pathway_1':labels[i],'pathway_2':labels[j],**metric})
    pair_rows.sort(key=lambda r:r['retained_l2_fraction'])
    write_rows(g/'pairwise_cancellation.csv',pair_rows)
    target_rows=[]
    measured_features=features(wl,baseline.chi2_complex)
    target_wavelengths=np.unique(cfg['feature_wavelengths_nm']+[p['wavelength_nm'] for key in ('Re_peaks','Im_peaks') for p in measured_features[key]])
    targets=calculate_chi2(target_wavelengths,inputs,settings)
    for j,w in enumerate(target_wavelengths):
        ranking=np.argsort(abs(targets.pathways_complex[:,j]))[::-1]
        for rank,i in enumerate(ranking):
            c=targets.pathways_complex[i,j]
            target_rows.append({'wavelength_nm':w,'source':'configured target' if w in cfg['feature_wavelengths_nm'] else 'measured absolute-component peak',
                                'rank_by_abs':rank+1,'label':labels[i],'Re_pm_per_V':c.real,'Im_pm_per_V':c.imag,'abs_pm_per_V':abs(c)})
    write_rows(g/'feature_pathway_ranking.csv',target_rows)
    transition=inputs['electron_eV'][:,None,:]-inputs['valence_eV'][None,:,:]
    for n in range(2):
        for m in range(2):
            for j,k in enumerate(inputs['k_per_nm']):
                resonance_rows.append({'n_1based':n+1,'m_1based':m+1,'k_per_nm':k,'k_pi_over_a':k*cfg['lattice_constant_nm']/np.pi,
                                      'transition_eV':transition[n,m,j],'one_photon_nm':HC_EV_NM/transition[n,m,j],'two_photon_nm':2*HC_EV_NM/transition[n,m,j]})
    write_rows(g/'resonance_map.csv',resonance_rows)
    rank=np.argsort(np.linalg.norm(baseline.pathways_complex,axis=1))[::-1]
    gmeta={**meta,'study':'28G_pathways','raw_manifest':'../28D_imaginary_source/raw_manifest.json',
           'code_manifest':'../28D_imaginary_source/code_manifest.json','pathway_table':'pathway_table.csv',
           'all_pathways_sum_error_pm_per_V':float(np.max(abs(baseline.pathways_complex.sum(axis=0)-baseline.chi2_complex))),
           'electron_hole_sum_error_pm_per_V':group_error,'all_pathway_cancellation':cancellation_metrics(baseline.pathways_complex),
           'diagonal_cancellation':cancellation_metrics(baseline.pathways_complex,diagonal),
           'offdiagonal_cancellation':cancellation_metrics(baseline.pathways_complex,offdiag),
           'offdiagonal_to_total_l2_ratio':float(np.linalg.norm(baseline.pathways_complex[offdiag].sum(axis=0))/np.linalg.norm(baseline.chi2_complex)),
           'diagonal_to_total_l2_ratio':float(np.linalg.norm(baseline.pathways_complex[diagonal].sum(axis=0))/np.linalg.norm(baseline.chi2_complex)),
           'dominant_by_l2':[labels[i] for i in rank[:cfg['top_pathways']]],'strongest_cancelling_pairs':pair_rows[:6],
           'cancellation_metric':'1 - ||sum contributions||_2 / sum ||individual contributions||_2 on fixed wavelength grid; NOT a fraction of absorbed power',
           'coordinate_origin_caution':'Individual diagonal-z pathways and electron/hole groups depend on the chosen z origin; total is invariant under a common origin shift. Their large cancelling magnitudes are not independent observables.'}
    write_json(g/'metadata.json',gmeta)
    if make_plots:
        groups=[('electron',ce),('hole',ch),('total',baseline.chi2_complex)]
        for component in ('real','imag'):
            component_plot(d/'plots',f'28D_{component}_electron_hole',wl,groups,component)
            component_plot(d/'plots',f'28D_{component}_gamma_to_zero',wl,[(rf'$\Gamma={gamma:g}$ meV',c) for gamma,c,_ in gamma_cases if gamma<=5],component)
            component_plot(e/'plots',f'28E_{component}_gamma_sweep',wl,[(rf'$\Gamma={gamma:g}$ meV',c) for gamma,c,_ in gamma_cases],component)
            component_plot(e/'plots',f'28E_{component}_gamma_selected',wl,[(rf'$\Gamma={gamma:g}$ meV',c) for gamma,c,_ in gamma_cases if gamma in cfg['selected_gamma_meV']],component)
            component_plot(g/'plots',f'28G_{component}_top_pathways',wl,[(labels[i],baseline.pathways_complex[i]) for i in rank[:cfg['top_pathways']]],component)
            component_plot(g/'plots',f'28G_{component}_diagonal',wl,[('diagonal z',baseline.pathways_complex[diagonal].sum(axis=0)),('off-diagonal z',baseline.pathways_complex[offdiag].sum(axis=0)),('total',baseline.chi2_complex)],component)
        fig,ax=axes(ylabel=r'$|\mathrm{Im}\,\chi^{(2)}|/|\mathrm{Re}\,\chi^{(2)}|$',zero_line=False)
        for gamma,c,_ in gamma_cases:
            if gamma in cfg['selected_gamma_meV']:
                ratio,_,_=safe_ratio(c,cfg['ratio_real_floor_fraction']);ax.plot(wl,ratio,lw=1.1,label=rf'$\Gamma={gamma:g}$ meV')
        ax.set_yscale('log');ax.axhline(1,lw=.7,color='.6');ax.set_xlim(wl[0],wl[-1]);save(fig,ax,e/'plots','28E_ratio_selected')
        fig,ax=axes(xlabel=r'$k_\parallel$ (nm$^{-1}$)',ylabel='fundamental resonance wavelength (nm)',zero_line=False)
        colors=plt.cm.tab10(np.arange(4))
        for i,(n,m) in enumerate([(n,m) for n in range(2) for m in range(2)]):
            ax.plot(inputs['k_per_nm'],HC_EV_NM/transition[n,m],color=colors[i],ls='--',lw=1.4,label=f'e{n+1}-h{m+1}, 1 photon')
            ax.plot(inputs['k_per_nm'],2*HC_EV_NM/transition[n,m],color=colors[i],lw=1.4,label=f'e{n+1}-h{m+1}, 2 photon')
        ax.legend(frameon=False,fontsize=8,ncol=2);save(fig,ax,g/'plots','28G_resonance_map',legend=False)
    print(f'28D/G electron+hole error {group_error:.4g} pm/V; numerator Im {numerator_imag:.4g} nm; full-vs-real error {real_error:.4g} pm/V')
    print(f'28E Gamma {cfg["gamma_meV"]}; near samples {near.sum()}, off samples {off.sum()}')
    return {'28D':dmeta,'28G':gmeta,'28E':gamma_rows}


def cli(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'config/response_audit.json')
    parser.add_argument('--input',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs')
    parser.add_argument('--no-plots',action='store_true')
    args=parser.parse_args(argv)
    run(args.config,args.input,args.output,not args.no_plots)
    return 0
