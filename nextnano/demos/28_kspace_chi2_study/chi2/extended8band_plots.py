"""Small future meeting-plot set. Called only with returned, reviewed inputs.

No spectra or images are created at import time. Eq2 remains unchanged.
"""
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
from .equation2 import calculate_chi2
from .k_integration import select_range
from . import plotting
from .artifacts import csv,write_json


def meeting_spectra(inputs,wavelength_nm,settings,config,out,review,historical=None,peak_window_nm=None):
    if not review.get('approved'):raise ValueError('Optical mapping review required')
    out=Path(out)
    if out.exists():raise ValueError('Refusing existing output')
    w=np.asarray(wavelength_nm)
    if not np.all(np.diff(w)>0) or not w[0]<=1550<=w[-1]:raise ValueError('Increasing wavelength grid must include 1550 nm')
    out.mkdir(parents=True)
    np.savez_compressed(out/'chi2_inputs.npz',**inputs)
    cases=[];rows=[];selections=[]
    for fraction in config['analysis_cutoffs_pi_over_a']:
        limit=fraction*np.pi/config['lattice_constant_nm']
        # A rounded solver endpoint can be just below the mathematical endpoint.
        if limit>inputs['k_per_nm'][-1] and limit-inputs['k_per_nm'][-1]<5e-10:limit=inputs['k_per_nm'][-1]
        selected=select_range(inputs,limit)
        s=calculate_chi2(w,selected,settings);cases.append((fraction,s.chi2_complex))
        stem=f'cutoff_{fraction:.6f}'
        csv(out/(stem+'.csv'),np.column_stack([w,s.chi2_complex.real,s.chi2_complex.imag,abs(s.chi2_complex.real),abs(s.chi2_complex)]),
            'wavelength_nm,real_pm_per_V,imag_pm_per_V,abs_real_pm_per_V,abs_complex_pm_per_V')
        csv(out/(stem+'_weights.csv'),np.column_stack([selected['k_per_nm'],s.k_weights_nm_minus2]),'k_per_nm,weight_nm_minus2')
        peak=np.nan
        if peak_window_nm is not None:
            mask=(w>=peak_window_nm[0])&(w<=peak_window_nm[1]);x=w[mask];y=abs(s.chi2_complex[mask])
            peaks,_=find_peaks(y,prominence=.1*y.max() if len(y) else 0)
            # Do not connect switched/competing peaks into a purported trajectory.
            if len(peaks)==1:peak=x[peaks[0]]
        rows.append([fraction,selected['k_per_nm'][-1],len(selected['k_per_nm']),np.interp(1550,w,s.chi2_complex.real),np.interp(1550,w,s.chi2_complex.imag),peak])
        selections.append(selected['selection'])
    table=np.array(rows);csv(out/'cutoff_diagnostics.csv',table,'kmax_pi_over_a,actual_kmax_per_nm,Nk,real_1550_pm_per_V,imag_1550_pm_per_V,isolated_abs_complex_peak_nm')
    for component,label,col in [('real','Re',3),('imag','Im',4)]:
        fig,ax=plotting.axes(ylabel=label+' chi2 (pm/V; stated Eq2 convention)')
        for f,s in cases:
            if any(np.isclose(f,x) for x in config['presentation_cutoffs_pi_over_a']):ax.plot(w,getattr(s,component),lw=1.5,label=f'{f:g} pi/a')
        plotting.save(fig,ax,out/'plots','28K_'+component+'_selected')
        fig,ax=plotting.axes(xlabel='kmax (pi/a)',ylabel=label+' chi2 at 1550 nm (pm/V)')
        ax.plot(table[:,0],table[:,col],'o-');plotting.save(fig,ax,out/'plots','28K_'+component+'_1550',legend=False)
        if historical is not None:
            # Caller supplies reference only; never used to construct new inputs.
            fig,ax=plotting.axes(ylabel=label+' chi2 (pm/V; stated Eq2 convention)')
            ax.plot(historical[:,0],historical[:,1 if component=='real' else 2],'k--',label='historical mixed reference')
            match=next((s for f,s in cases if np.isclose(f,.1)),None)
            if match is not None:ax.plot(w,getattr(match,component),label='8-band inputs, 0.10 pi/a')
            plotting.save(fig,ax,out/'plots','28M_reference_'+component)
    # Only plot the whole peak trajectory when every window has a single peak.
    if np.isfinite(table[:,5]).all():
        fig,ax=plotting.axes(xlabel='kmax (pi/a)',ylabel='isolated |chi2| peak wavelength (nm)',zero_line=False)
        ax.plot(table[:,0],table[:,5],'o-');plotting.save(fig,ax,out/'plots','28K_isolated_peak',legend=False)
    write_json(out/'metadata.json',{'study':'28K_28M','review':review,'settings':vars(settings),'selections':selections,
        'peak_window_nm':peak_window_nm,'peak_policy':'single prominent interior |chi2| peak in user-reviewed window; not proof of physical branch identity',
        'historical_reference_only':True,'inputs_source':'reviewed finite8band adapter; no historical builder'})


def meeting_states(tracked_csv,branches,out):
    """Selected candidate IDs are one-based; gaps show unresolved assignments."""
    data=np.genfromtxt(tracked_csv,delimiter=',',names=True)
    fig,ax=plotting.axes(xlabel='k (nm^-1)',ylabel='8-band energy (eV)',zero_line=False)
    for branch in branches:
        d=data[data['candidate_branch']==branch];y=d['energy_eV'].copy();y[d['ambiguous']!=0]=np.nan
        ax.plot(d['k_per_nm'],y,label=f'candidate {branch}')
    plotting.save(fig,ax,out,'28L_tracked_energy')
    fig,ax=plotting.axes(xlabel='k (nm^-1)',ylabel='component probability',zero_line=False)
    for branch in branches:
        d=data[data['candidate_branch']==branch]
        for band,style in [('HH','-'),('LH','--')]:
            y=d[band].copy();y[d['ambiguous']!=0]=np.nan;ax.plot(d['k_per_nm'],y,style,label=f'candidate {branch} {band}')
    ax.set_ylim(0,1);plotting.save(fig,ax,out,'28L_HH_LH')
