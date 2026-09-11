"""28B shells, 28H native-grid convergence and 28J observable comparison.

No extra susceptibility algebra: every spectrum calls equation2.calculate_chi2.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
from .studies import ROOT,setup
from .input_builder import build_inputs
from .equation2 import calculate_chi2,prefactor
from .k_integration import radial_weights,select_range
from .artifacts import csv,write_json,save_inputs,save_spectrum,manifest
from .diagnostics import paper_metrics
from .plotting import axes,save


def subsample(inputs,stride):
    """Retain true solved nodes, including both endpoints; no interpolation."""
    if not isinstance(stride,int) or stride<1: raise ValueError('stride must be positive integer')
    nk=len(inputs['k_per_nm']);ix=np.unique(np.r_[np.arange(0,nk,stride),nk-1])
    out={**inputs,'k_per_nm':inputs['k_per_nm'][ix]}
    for key in ['electron_eV','valence_eV']: out[key]=inputs[key][:,ix]
    for key in ['overlap','ze_nm','zh_nm']:
        out[key]=inputs[key][:,:,ix] if inputs[key].ndim==3 else inputs[key].copy()
    out['selection']={'source_indices':ix.tolist(),'stride':stride,'endpoint_policy':'both retained'}
    return out


def shell_contributions(result,k,settings):
    """Each adjacent trapezoid exactly integrates that shell of the radial disk."""
    f=result.summed_integrand*k[None,:]*settings.spin_degeneracy/(2*np.pi)
    return prefactor(settings)*.5*(f[:,1:]+f[:,:-1])*np.diff(k)[None,:]


def cutoff_diagnostics(cfg,settings,inputs,meta):
    out=ROOT/'outputs/28B_kspace_cutoff';plots=out/'plots'
    target=np.array(cfg['target_wavelengths_nm'],float);k=inputs['k_per_nm']
    r=calculate_chi2(target,inputs,settings)
    shell=shell_contributions(r,k,settings)
    cumulative=np.column_stack([np.zeros(len(target),complex),np.cumsum(shell,axis=1)])
    np.savez_compressed(out/'cumulative_and_shells.npz',wavelength_nm=target,k_per_nm=k,
                        cumulative_pm_per_V=cumulative,shell_pm_per_V=shell)
    rows=[]
    for j,w in enumerate(target):
        for i in range(len(k)):
            rows.append([w,k[i],k[i]*.565325/np.pi,cumulative[j,i].real,cumulative[j,i].imag,
                         shell[j,i-1].real if i else 0,shell[j,i-1].imag if i else 0])
    csv(out/'cumulative_and_shells.csv',rows,'wavelength_nm,k_per_nm,k_fraction_pi_over_a,Re_cumulative,Im_cumulative,Re_shell_ending_here,Im_shell_ending_here')
    for comp,label in [('real','Re'),('imag','Im')]:
        for name,values,x,ylabel in [('cumulative',getattr(cumulative,comp),k,rf'{label} $\chi^{{(2)}}$ (pm/V)'),
                                   ('shell',getattr(shell,comp),k[1:],rf'{label} $\Delta\chi^{{(2)}}$ per shell (pm/V)')]:
            fig,ax=axes(xlabel=r'$k_{max}$ (nm$^{-1}$)' if name=='cumulative' else r'shell upper $k$ (nm$^{-1}$)',ylabel=ylabel)
            for w,y in zip(target,values): ax.plot(x,y,lw=1.4,label=f'{w:g} nm')
            save(fig,ax,plots,f'28B_{comp}_{name}')
    tail_start=np.searchsorted(k,k[-1]*(1-cfg['tail_fraction']))
    change=cumulative[:,-1]-cumulative[:,tail_start]
    scale=np.maximum(np.max(abs(cumulative),axis=1),np.finfo(float).eps)
    checks={'shell_sum_vs_core_max_error_pm_per_V':float(max(abs(shell.sum(axis=1)-r.chi2_complex))),
            'tail_start_per_nm':float(k[tail_start]),'tail_fraction':cfg['tail_fraction'],
            'tail_relative_tolerance':cfg['tail_relative_tolerance'],
            'targets':[{'wavelength_nm':float(w),'tail_Re_pm_per_V':float(d.real),'tail_Im_pm_per_V':float(d.imag),
                        'tail_change_over_max_cumulative_modulus':float(abs(d)/s),
                        'tail_small_on_this_grid':bool(abs(d)/s<=cfg['tail_relative_tolerance'])} for w,d,s in zip(target,change,scale)],
            'interpretation':'Finite-range tail diagnostic, not proof of infinite-cutoff convergence. Shells include radial k measure and signed cancellation.'}
    write_json(out/'shell_metadata.json',{**meta,'study':'28B_shells','audit_configuration':cfg,**checks})
    return checks


def grid_diagnostics(cfg,settings,wl,inputs,meta):
    out=ROOT/'outputs/28H_grid_convergence';out.mkdir(parents=True,exist_ok=True)
    full=calculate_chi2(wl,inputs,settings);cases=[];rows=[]
    for stride in cfg['subsample_strides']:
        selected=subsample(inputs,stride)
        dest=out/f'stride_{stride}'
        save_inputs(dest/'chi2_inputs',selected,settings,wl)
        r=calculate_chi2(wl,selected,settings)
        save_spectrum(dest/'chi2_results',r)
        error=r.chi2_complex-full.chi2_complex
        row=[len(selected['k_per_nm']),stride,selected['k_per_nm'][-1],max(abs(error.real)),max(abs(error.imag)),
             np.sqrt(np.mean(abs(error)**2)),radial_weights(selected['k_per_nm'],settings.spin_degeneracy).sum()]
        rows.append(row);cases.append((len(selected['k_per_nm']),r.chi2_complex))
        write_json(dest/'metadata.json',{**meta,'study':'28H','configuration':cfg,'stride':stride,
                   'raw_manifest':'../raw_manifest.json','code_manifest':'../code_manifest.json',
                   'k_points':len(selected['k_per_nm']),'k_min_per_nm':float(selected['k_per_nm'][0]),
                   'k_max_per_nm':float(selected['k_per_nm'][-1]),'sampling':'subset of solved301; no new solver run'})
    csv(out/'grid_convergence.csv',rows,'k_points,stride,kmax_per_nm,max_Re_error_pm_per_V,max_Im_error_pm_per_V,complex_RMS_error_pm_per_V,sum_weights_nm_minus2')
    for comp,label in [('real','Re'),('imag','Im')]:
        fig,ax=axes()
        for n,c in cases: ax.plot(wl,getattr(c,comp),lw=1.3,label=f'{n} points')
        save(fig,ax,out/'plots',f'28H_grid_density_convergence_{comp}')
        fig,ax=axes(xlabel='number of k points',ylabel=f'max {label} error vs 301 points (pm/V)',zero_line=False)
        ax.plot([r[0] for r in rows[:-1]],[r[3 if comp=='real' else 4] for r in rows[:-1]],'-o',ms=3)
        save(fig,ax,out/'plots',f'28H_{comp}_error',False)
    metadata={**meta,'study':'28H','audit_configuration':cfg,'rows':rows,
       'fixed_kmax_per_nm':float(inputs['k_per_nm'][-1]),
       'constant_integrand_area_error_nm_minus2':float(abs(radial_weights(inputs['k_per_nm'],settings.spin_degeneracy).sum()-settings.spin_degeneracy*inputs['k_per_nm'][-1]**2/(4*np.pi))),
       'conclusion':'Subsampling tests convergence towards the finest available grid; they cannot certify accuracy beyond301 or extended-cutoff convergence.'}
    independent=[]
    for source in cfg.get('independent_grid_datasets',[]):
        fresh,_=build_inputs(ROOT/source);dest=out/Path(source).name
        if not np.isclose(fresh['k_per_nm'][-1],inputs['k_per_nm'][-1],rtol=0,atol=1e-10):
            raise ValueError('Independent grid endpoint differs: cannot call this fixed-cutoff convergence')
        save_inputs(dest/'chi2_inputs',fresh,settings,wl)
        result=calculate_chi2(wl,fresh,settings);save_spectrum(dest/'chi2_results',result)
        error=result.chi2_complex-full.chi2_complex
        info={**meta,'study':'28H_independent_solver_grid','source_dataset':source,'k_points':len(fresh['k_per_nm']),
              'k_max_per_nm':float(fresh['k_per_nm'][-1]),'max_Re_error_pm_per_V':float(max(abs(error.real))),
              'max_Im_error_pm_per_V':float(max(abs(error.imag))),'complex_RMS_error_pm_per_V':float(np.sqrt(np.mean(abs(error)**2)))}
        write_json(dest/'raw_manifest.json',manifest(ROOT/source));info['code_manifest']='../code_manifest.json'
        write_json(dest/'metadata.json',info);independent.append(info)
    metadata['independent_solver_grid_checks']=independent
    extended,_=build_inputs(ROOT/'nextnano/raw_extended')
    controlled=select_range(extended,inputs['k_per_nm'][-1])
    coarse=calculate_chi2(wl,controlled,settings).chi2_complex
    err=coarse-full.chi2_complex
    metadata['extended_grid_at_same_cutoff']={'baseline_Nk':len(inputs['k_per_nm']),'extended_Nk':len(controlled['k_per_nm']),
         'kmax_nm_minus1':float(inputs['k_per_nm'][-1]),'max_Re_error_pm_per_V':float(max(abs(err.real))),
         'max_Im_error_pm_per_V':float(max(abs(err.imag))),'complex_RMS_error_pm_per_V':float(np.sqrt(np.mean(abs(err)**2))),
         'interpretation':'Same endpoint; independently solved301 vs241 native nodes. No interpolated electronic energies.'}
    target=np.array(cfg['target_wavelengths_nm'],float);ek=extended['k_per_nm']
    result=calculate_chi2(target,extended,settings)
    shells=shell_contributions(result,ek,settings)
    cumul=np.column_stack([np.zeros(len(target),complex),np.cumsum(shells,axis=1)])
    np.savez_compressed(out/'extended_cumulative.npz',k_per_nm=ek,wavelength_nm=target,cumulative_pm_per_V=cumul,shell_pm_per_V=shells)
    start=np.searchsorted(ek,ek[-1]*(1-cfg['tail_fraction']))
    metadata['extended_tail']=[{'wavelength_nm':float(w),'tail_change_pm_per_V':complex(cumul[i,-1]-cumul[i,start]),
            'relative_to_max_cumulative_modulus':float(abs(cumul[i,-1]-cumul[i,start])/max(abs(cumul[i])))} for i,w in enumerate(target)]
    for comp,label in [('real','Re'),('imag','Im')]:
        fig,ax=axes(xlabel=r'$k_{max}$ (nm$^{-1}$)',ylabel=rf'{label} $\chi^{{(2)}}$ (pm/V)')
        for w,v in zip(target,getattr(cumul,comp)):ax.plot(ek,v,lw=1.3,label=f'{w:g} nm')
        save(fig,ax,out/'plots',f'28H_{comp}_cutoff_convergence')
    csv(out/'extended_grid_same_cutoff.csv',np.column_stack([wl,full.chi2_complex.real,coarse.real,err.real,full.chi2_complex.imag,coarse.imag,err.imag]),
        'wavelength_nm,Re_dense,Re_coarse,Re_error,Im_dense,Im_coarse,Im_error')
    for comp,label in [('real','Re'),('imag','Im')]:
        fig,ax=axes()
        ax.plot(wl,getattr(full.chi2_complex,comp),lw=1.6,label='301 points, baseline grid')
        ax.plot(wl,getattr(coarse,comp),ls='--',lw=1.2,label='241 points, extended grid')
        save(fig,ax,out/'plots',f'28H_{comp}_matched_cutoff')
    write_json(out/'metadata.json',metadata)
    return metadata


def observable_diagnostics(cfg,settings,wl,inputs,meta):
    out=ROOT/'outputs/28J_paper_comparison';out.mkdir(parents=True,exist_ok=True)
    meta={**meta,'raw_manifest':'../28H_grid_convergence/raw_manifest.json','code_manifest':'../28H_grid_convergence/code_manifest.json'}
    paper=np.loadtxt(ROOT/'validation/paper_fig2d.csv',delimiter=',',skiprows=1)
    paper[:,1]/=max(paper[:,1]);c=calculate_chi2(wl,inputs,settings).chi2_complex
    for name,values,label in [('abs_real',abs(c.real),r'$|\mathrm{Re}\,\chi^{(2)}|$'),('magnitude',abs(c),r'$|\chi^{(2)}|$')]:
        fig,ax=axes(ylabel='normalized susceptibility')
        ax.plot(paper[:,0],paper[:,1],'ko--',ms=3,lw=1,label='paper Fig. 2d')
        ax.plot(wl,values/max(values),color='crimson',lw=1.7,label=label)
        save(fig,ax,out/'plots',f'28J_paper_vs_{name}')
    for comp,label in [('real','Re'),('imag','Im')]:
        fig,ax=axes();ax.plot(wl,getattr(c,comp),color='crimson' if comp=='real' else 'steelblue',label=label)
        save(fig,ax,out/'plots',f'28J_{comp}')
    # Signed components share ONE model reference, never separate Re/Im scaling.
    fig,ax=axes(ylabel='normalized susceptibility')
    ax.plot(paper[:,0],paper[:,1],'ko--',ms=3,lw=1,label='paper Fig. 2d')
    scale=max(abs(c.real))
    ax.plot(wl,c.real/scale,color='crimson',label='Re / max |Re|')
    ax.plot(wl,c.imag/scale,color='steelblue',label='Im / max |Re|')
    save(fig,ax,out/'plots','28J_signed_shared_scale')
    pk=find_peaks(paper[:,1],prominence=cfg['paper_peak_prominence'])[0]
    mn=find_peaks(-paper[:,1],prominence=cfg['paper_peak_prominence'])[0]
    details=[];rows=[]
    current_sweep=json.loads((ROOT/'outputs/28B_kspace_cutoff/metadata.json').read_text())
    fractions=current_sweep['sweep_configuration']['k_cutoffs_pi_over_a']
    folders=[ROOT/'outputs/28B_kspace_cutoff/cases'/f'kmax_{f:.5f}'.replace('.','p') for f in fractions]
    for folder in folders:
        info=json.loads((folder/'metadata.json').read_text());arr=np.loadtxt(folder/'chi2_results/chi2_spectrum.csv',delimiter=',',skiprows=1)
        cc=arr[:,2]+1j*arr[:,3];metrics=paper_metrics(arr[:,0],cc,paper)
        # Nearest prominent feature distances are diagnostics, NOT tracked branches.
        per={}
        for name,v in [('abs_real',abs(cc.real)),('magnitude',abs(cc))]:
            norm=v/max(v);cp=find_peaks(norm,prominence=cfg['paper_peak_prominence'])[0];cm=find_peaks(-norm,prominence=cfg['paper_peak_prominence'])[0]
            per[name]={'nearest_peak_errors_nm':[float(min(abs(arr[cp,0]-paper[i,0]))) if len(cp) else None for i in pk],
                       'nearest_minimum_errors_nm':[float(min(abs(arr[cm,0]-paper[i,0]))) if len(cm) else None for i in mn]}
        row=[info['cutoff_pi_over_a'],metrics['abs_real']['nRMSE'],metrics['magnitude']['nRMSE']]
        for name in ['abs_real','magnitude']:
            for key in ['nearest_peak_errors_nm','nearest_minimum_errors_nm']:
                vv=per[name][key];row.append(float(np.mean(vv)) if vv and None not in vv else np.nan)
        rows.append(row);details.append({'cutoff_pi_over_a':row[0],'metrics':metrics,'features':per})
    csv(out/'paper_agreement_vs_kmax.csv',rows,'kmax_pi_over_a,nRMSE_abs_real,nRMSE_magnitude,mean_nearest_peak_error_abs_real_nm,mean_nearest_min_error_abs_real_nm,mean_nearest_peak_error_magnitude_nm,mean_nearest_min_error_magnitude_nm')
    fig,ax=axes(xlabel=r'$k_{max}/(\pi/a)$',ylabel='normalized RMSE',zero_line=False)
    a=np.array(rows);ax.plot(a[:,0],a[:,1],'-o',ms=3,label='|Re|');ax.plot(a[:,0],a[:,2],'-o',ms=3,label='|chi|')
    save(fig,ax,out/'plots','28J_paper_error_vs_cutoff')
    metadata={**meta,'study':'28J','audit_configuration':cfg,'baseline_metrics':paper_metrics(wl,c,paper),
              'paper_peaks_nm':paper[pk,0],'paper_minima_nm':paper[mn,0],'cutoff_metrics':details,
              'best_abs_real_cutoff_pi_over_a':float(a[np.argmin(a[:,1]),0]),
              'best_magnitude_cutoff_pi_over_a':float(a[np.argmin(a[:,2]),0]),
              'physically_converged_cutoff':'NOT ESTABLISHED; fit error is not a convergence test',
              'normalization':'own maximum for paper and each absolute observable; signed Re/Im plot uses one max|Re| factor',
              'feature_policy':'nearest prominent features, no one-to-one assignment; digitized-paper sample spacing limits precision'}
    extended_meta=json.loads((ROOT/'outputs/28C_extended_k/metadata.json').read_text())
    extended_rows=[]
    for fraction in extended_meta['extended_config']['k_cutoffs_pi_over_a']:
        folder=ROOT/'outputs/28C_extended_k/cases'/f'kmax_{fraction:.4f}'
        table=np.loadtxt(folder/'chi2_results/chi2_spectrum.csv',delimiter=',',skiprows=1)
        metric=paper_metrics(table[:,0],table[:,2]+1j*table[:,3],paper)
        extended_rows.append([fraction,metric['abs_real']['nRMSE'],metric['magnitude']['nRMSE']])
    csv(out/'extended_paper_agreement.csv',extended_rows,'extended_grid_cutoff_pi_over_a,nRMSE_abs_real,nRMSE_magnitude')
    metadata['extended_grid_metrics']=extended_rows
    metadata['extended_grid_best_abs_real_cutoff']=min(extended_rows,key=lambda r:r[1])[0]
    metadata['extended_grid_best_magnitude_cutoff']=min(extended_rows,key=lambda r:r[2])[0]
    write_json(out/'metadata.json',metadata)
    return metadata


def main(argv=None):
    p=argparse.ArgumentParser(description='Cached28B/H/J numerical audits; no solver')
    p.add_argument('--config',type=Path,default=ROOT/'config/numerical_audit.json')
    args=p.parse_args(argv);cfg=json.loads(args.config.read_text())
    _,settings,wl,inputs,meta=setup(ROOT/cfg['baseline_config'],None,ROOT/'outputs/28H_grid_convergence')
    b=cutoff_diagnostics(cfg,settings,inputs,meta)
    h=grid_diagnostics(cfg,settings,wl,inputs,meta)
    j=observable_diagnostics(cfg,settings,wl,inputs,meta)
    print('28B shell error:',b['shell_sum_vs_core_max_error_pm_per_V'])
    print('28H nodes:',[r[0] for r in h['rows']])
    print('28J best |Re| cutoff:',j['best_abs_real_cutoff_pi_over_a'])
    return 0
