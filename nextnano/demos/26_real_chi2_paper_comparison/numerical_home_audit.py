"""Solver-free additional numerical diagnostics. Never changes earlier audit products."""
from dataclasses import replace
import json
import numpy as np
import matplotlib.pyplot as plt
import extended_implementation_audit as a

OUT=a.HERE/'outputs/HOME_EXHAUSTIVE_AUDIT'
WINDOWS={'P1':(490,580),'Z1':(575,650),'P2':(690,820),'P3':(990,1170),'Z2':(1240,1400),'P4':(1450,1610)}

def obs(v,name):
    return {'magnitude':lambda:abs(v),'Re':lambda:v.real,'abs_Re':lambda:abs(v.real),'Im':lambda:v.imag,'abs_Im':lambda:abs(v.imag),'Re_squared':lambda:v.real**2,'magnitude_squared':lambda:abs(v)**2}[name]()

def extrema(x,y,peak=True):
    z=y if peak else -y
    return np.flatnonzero((z[1:-1]>z[:-2])&(z[1:-1]>=z[2:]))+1

def metrics(inp,v,name='magnitude',paper=None):
    x=inp.wavelength; y=a.norm(obs(v,name),signed=True)
    p=a.norm(np.interp(x,inp.paper_x,inp.paper_y)) if paper is None else a.norm(paper)
    out={'normalized_RMSE':a.rmse(y,p),'correlation':a.corr(y,p)}
    for f,(lo,hi) in WINDOWS.items():
        mask=(x>=lo)&(x<=hi); ids=extrema(x,y,f.startswith('P')); ids=ids[(x[ids]>=lo)&(x[ids]<=hi)]
        chosen=ids[np.argmin(abs(x[ids]-a.FEATURES[f]))] if len(ids) else None
        out[f+'_nm']=float(x[chosen]) if chosen is not None else None
        out[f+'_norm']=float(y[chosen]) if chosen is not None else None
        out[f+'_local_RMSE']=a.rmse(y[mask],p[mask])
        out[f+'_at_target_norm']=float(np.interp(a.FEATURES[f],x,y))
    ids=extrema(x,y); mins=extrema(x,y,False)
    out['all_peaks_nm']=';'.join(str(float(x[i])) for i in ids)
    out['all_minima_nm']=';'.join(str(float(x[i])) for i in mins)
    out['peak_count']=len(ids);out['minimum_count']=len(mins)
    out['derivative_sign_changes']=len(ids)+len(mins)
    # Local prominence and half-prominence width, explicitly relative to adjacent troughs.
    detail=[]
    for i in ids:
        left=max([0]+[int(j) for j in mins if j<i]);right=min([len(x)-1]+[int(j) for j in mins if j>i])
        base=max(y[left],y[right]);prom=float(y[i]-base);half=y[i]-prom/2
        l=i;r=i
        while l>left and y[l]>half:l-=1
        while r<right and y[r]>half:r+=1
        detail.append({'nm':float(x[i]),'local_prominence':prom,'half_prominence_width_nm':float(x[r]-x[l])})
    out['topology_json']=json.dumps(detail)
    return out

def hermite(x,y,q):
    """Shape preserving cubic Hermite, harmonic interior slopes; no extrapolation."""
    if min(q)<min(x) or max(q)>max(x):raise ValueError('no extrapolation')
    h=np.diff(x);d=np.diff(y)/h;m=np.zeros(len(x));m[0]=d[0];m[-1]=d[-1]
    for i in range(1,len(x)-1):
        if d[i-1]*d[i]>0:
            w1=2*h[i]+h[i-1];w2=h[i]+2*h[i-1];m[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])
    j=np.clip(np.searchsorted(x,q)-1,0,len(x)-2);t=(q-x[j])/h[j]
    return (2*t**3-3*t**2+1)*y[j]+(t**3-2*t**2+t)*h[j]*m[j]+(-2*t**3+3*t**2)*y[j+1]+(t**3-t**2)*h[j]*m[j+1]

def evaluate_weights(inp,weights):
    # Preserve independent engine while replacing only integration weights temporarily.
    original=a.integration_weights
    try:
        a.integration_weights=lambda k,convention='production':weights
        return a.independent_eq2(inp)
    finally:a.integration_weights=original

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inp=a.load_inputs();base=a.independent_eq2(inp);rows=[];spectra={}; checks=[]
    baseline=metrics(inp,base.total);baseline_rmse=baseline['normalized_RMSE']
    def add(family,variant,v=None,name='magnitude',method='',interpretation='',plausible='NO',status=None,extra=None,paper=None):
        met=metrics(inp,v,name,paper) if v is not None else {}
        improved=met.get('normalized_RMSE',float('inf'))<baseline_rmse-1e-8
        row={'family':family,'variant':variant,'question':f'Does {variant} explain the paper discrepancy?', 'method':method,'input_data':str(a.MODEL)+'; '+str(a.DISP)+'; '+str(a.MATRIX),'result':('lower RMSE; reproduction not established' if improved else 'does not establish reproduction') if v is not None else 'see quantitative evidence','status':status or 'FAIL','improved':'YES' if improved else 'NO','evidence':json.dumps(extra or {},default=str),'interpretation':interpretation or 'Diagnostic sensitivity does not validate this choice as paper physics. Missing or displaced features must also be assessed.','possible_reason':'Changed poles, cancellation or display can reduce aggregate error without matching topology.','plausible':plausible,'pro_required':'NO',**met}
        rows.append(row)
        if v is not None:spectra[variant+'__'+name]=a.norm(obs(v,name),signed=True)
        return row
    for name in ('magnitude','Re','abs_Re','Im','abs_Im','Re_squared','magnitude_squared'):
        add('A','observable '+name,base.total,name,method='Normalize over original complete 400–1850 nm grid; same physical chi. Non-magnitude observables DIAGNOSTIC ONLY.',status='PASS' if name=='magnitude' else 'FAIL')
    # Reuse saved sweep curves when present; calculations here add missing feature/local metrics.
    for gamma in (0,.25,.5,1,2.5,5,7.5,10):
        ev=base if gamma==5 else a.independent_eq2(inp,gamma)
        for name in ('magnitude','Re','abs_Re'):
            add('B',f'Gamma {gamma:g} meV {name}',ev.total,name,method='Single prescribed Gamma; 2.5 meV tests paper 5 meV as FWHM; 5 meV tests HWHM. Zero Gamma is off-pole sampled diagnostic only.')
    for subset in ('full16','electron_diagonal','hh_diagonal','both_diagonal','offdiagonal_only','electron_family','hh_family'):
        v=base.electron if subset=='electron_family' else base.hole if subset=='hh_family' else a.subset_total(base,subset)
        add('E',subset,v,method='Sum named original pathways; all other inputs fixed. DIAGNOSTIC ONLY; terms are not removed from production.')
    cancel=[];dominance=[]
    for f,target in a.FEATURES.items():
        idx=int(np.argmin(abs(inp.wavelength-target)));e,h=base.electron[idx],base.hole[idx]
        ratio=abs(e+h)/(abs(e)+abs(h));order=sorted(base.pathways,key=lambda k:abs(base.pathways[k][idx]),reverse=True)
        cancel.append({'feature':f,'wavelength_nm':target,'electron_real':e.real,'electron_imag':e.imag,'signed_hh_real':h.real,'signed_hh_imag':h.imag,'total_real':(e+h).real,'total_imag':(e+h).imag,'phase_difference_deg':float(np.angle(e*np.conj(h),deg=True)),'cancellation_ratio':ratio})
        for rank,key in enumerate(order,1):
            v=base.pathways[key][idx];dominance.append({'feature':f,'rank':rank,'pathway':key,'real':v.real,'imag':v.imag,'magnitude':abs(v)})
        add('F','cancellation '+f,method='Signed electron and hole subtotals at target, ratio |e+h|/(|e|+|h|).',status='PASS',extra=cancel[-1],interpretation='Destructive interference is present; a small ratio is not an exact complex zero. Dominance table ranks all 16 pathways.')
    a.write_csv(OUT/'numerical_cancellation.csv',cancel);a.write_csv(OUT/'numerical_dominant_pathways.csv',dominance)
    for conv in ('production','radial_kdk','bare_2pi_kdk','equal_points','k0_only'):
        ev=base if conv=='production' else a.independent_eq2(inp,convention=conv)
        shape_delta=float(np.max(abs(a.norm(abs(ev.total))-a.norm(abs(base.total)))))
        add('G',conv,ev.total,method='Existing independent integration convention.',status='PASS' if conv in ('production','radial_kdk','bare_2pi_kdk') else 'FAIL',extra={'max_normalized_shape_difference':shape_delta})
        if conv in ('radial_kdk','bare_2pi_kdk'):checks.append((conv,shape_delta<1e-10))
    k=inp.k;h=np.diff(k);assert np.allclose(h,h[0]);assert len(k)%2==1
    sw=np.ones(len(k));sw[1:-1:2]=4;sw[2:-1:2]=2;sw*=h[0]/3*k/np.pi
    for label,w in [('Simpson',sw),('left_rectangle',np.r_[h,0]*k/np.pi),('right_rectangle',np.r_[0,h]*k/np.pi)]:
        ev=evaluate_weights(inp,w);add('G',label,ev.total,method='Uniform raw grid; Simpson composite 1/3 or diagnostic one-sided endpoints.')
    for frac in (.025,.05,.075,.1):
        ids=np.flatnonzero(inp.k<=inp.k[-1]*frac/.1+1e-12)
        sub=replace(inp,k=k[ids],ee=inp.ee[:,ids],hh=inp.hh[:,ids]);ev=a.independent_eq2(sub)
        old=a.independent_eq2(inp,cutoff=float(sub.k[-1]))
        add('H',f'correct truncated trapezoid {frac}',ev.total,method='Slice existing data first, then recompute half endpoint weights; .025 has 76 points.',extra={'old_mask_RMSE':metrics(inp,old.total)['normalized_RMSE'],'old_mask_vs_correct_max_abs_pm_V':float(np.max(abs(old.total-ev.total)))},interpretation='Earlier masked full-grid truncation retained excess half endpoint weight. This corrects truncated diagnostic only; full production integral unchanged.')
    # Distinct from genuinely independent raw grid tests in existing Demo24 tables.
    for step in (2,3,5):
        ix=np.arange(0,len(k),step);sub=replace(inp,k=k[ix],ee=inp.ee[:,ix],hh=inp.hh[:,ix]);ev=a.independent_eq2(sub)
        add('J',f'downsample existing grid stride {step}',ev.total,method='No new physics: retained direct samples only; compare all pathway sums.',extra={'max_pathway_abs_delta_pm_V':max(float(np.max(abs(ev.pathways[key]-base.pathways[key]))) for key in base.pathways)})
        for interp in ('linear','shape_preserving_cubic'):
            fun=(lambda x,y,q:np.interp(q,x,y)) if interp=='linear' else hermite
            dense=replace(inp,ee=np.array([fun(sub.k,y,k) for y in sub.ee]),hh=np.array([fun(sub.k,y,k) for y in sub.hh]));e=a.independent_eq2(dense)
            add('J',f'{interp} stride {step}',e.total,method='Interpolate downsampled energies strictly inside measured endpoints; compare with retained 301-point data.',extra={'max_energy_interpolation_error_eV':float(max(np.max(abs(dense.ee-inp.ee)),np.max(abs(dense.hh-inp.hh))))})
    rawroot=a.ROOT/'demo_results/demo23/raw'
    higher=[];raw_production=None
    for case in ('grid_y_n101_k0100','grid_y_n201_k0100','production_y_n301_k0100','kmax_y_n301_k0050','kmax_y_n301_k0075','kmax_y_n301_k0125','isotropy_yz45_n301_k0100'):
        files=list((rawroot/case).rglob('dispersion_*.dat'));assert len(files)==1
        data=np.loadtxt(files[0],skiprows=1);rk=data[:,0]
        # Same pair-mean tracking and per-state k0 anchor as saved production.
        energies=np.array([data[:,[11,12]].mean(axis=1),data[:,[13,14]].mean(axis=1),data[:,[5,6]].mean(axis=1),data[:,[3,4]].mean(axis=1)])
        aligned=energies-energies[:,[0]]+np.r_[inp.ee[:,0],inp.hh[:,0]][:,None]
        ri=replace(inp,k=rk,ee=aligned[:2],hh=aligned[2:]);ev=a.independent_eq2(ri)
        if case=='production_y_n301_k0100':
            raw_production=float(np.max(abs(ev.total-base.total)));checks.append(('raw_production_rebuild',raw_production<1e-7))
        add('H' if case.startswith('kmax') else 'J','independent raw '+case,ev.total,method='Actual separately run Professional dispersion; static adjacent Kramers pair means, same per-state k0 anchoring as production; frozen scalar matrices.',extra={'source':str(files[0]),'Nk':len(rk),'kmax_inverse_nm':float(max(rk)),'max_pathway_abs_delta_pm_V':max(float(np.max(abs(ev.pathways[key]-base.pathways[key]))) for key in base.pathways)},interpretation='Existing raw output reused, no solver. Comparing cutoff changes tests truncation sensitivity, not convergence with larger physical BZ. Raw finite-k identity uses fixed paired band labels because spinors are absent.')
        if case=='kmax_y_n301_k0125':
            for epair in ((7,8),(9,10),(11,12),(13,14)):
                for hpair in ((1,2),(3,4),(5,6)):
                    tr=data[:,list(epair)].mean(axis=1)-data[:,list(hpair)].mean(axis=1)
                    for target in (a.HC/540,2*a.HC/1080):
                        j=int(np.argmin(abs(tr-target)))
                        higher.append({'electron_pair':str(epair),'hole_pair':str(hpair),'source':str(files[0]),'energy_reference':'raw unaligned kp8; not mixed with Demo21 anchors','min_gap_eV':float(min(tr)),'max_gap_eV':float(max(tr)),'target_eV':target,'minimum_detuning_eV':float(abs(tr[j]-target)),'nearest_k_inverse_nm':float(rk[j]),'target_bracketed':bool(min(tr)<=target<=max(tr)),'limitation':'ENERGY ONLY; lower CB-mixed pairs not certified bound electron states; finite-k character unavailable'})
    a.write_csv(OUT/'numerical_higher_state_ranges.csv',higher)
    add('N','existing candidate higher-state raw energy ranges',method='All 4 CB-candidate pairs versus 3 hole pairs over existing .125 pi/a raw grid; raw energy reference kept separate.',status='INCONCLUSIVE',plausible='YES',extra={'table':'numerical_higher_state_ranges.csv'},interpretation='Energy-only screening; no higher-state chi without valid matrix elements; k0 mixed character cannot certify finite-k identity or boundness.')
    matrices=[]
    for branch in ('A','B'):
        o,ze,zh=a.reconstruct_branch(branch);matrices.append((o,ze,zh));ev=a.independent_eq2(inp,overlap=o,ze=ze,zh=zh)
        add('L','projected kp8 branch '+branch,ev.total,method='Normalize each dominant component separately; rebuild overlap and z; DIAGNOSTIC cross-method mixing with aligned dispersion.',status='INCONCLUSIVE',plausible='YES',interpretation='Not a full multiband optical matrix or equivalent scalar calculation. Large changes prove sensitivity, not a production matrix bug.')
    mean=tuple((x+y)/2 for x,y in zip(*matrices));ev=a.independent_eq2(inp,overlap=mean[0],ze=mean[1],zh=mean[2])
    add('L','projected branch matrix mean',ev.total,method='Mean phase-aligned component matrices BEFORE evaluation; diagnostic only, no justified spinor averaging claim.',status='INCONCLUSIVE',plausible='YES')
    reson=[]
    for n in range(2):
        for m in range(2):
            tr=inp.ee[n]-inp.hh[m]
            for f,lam in a.FEATURES.items():
                for photons in (1,2):
                    det=tr-photons*a.HC/lam;j=int(np.argmin(abs(det)))
                    reson.append({'transition':f'e{n+1}-h{m+1}','feature':f,'photons':photons,'k0_energy_eV':tr[0],'k0_wavelength_nm':photons*a.HC/tr[0],'min_detuning_eV':float(abs(det[j])),'nearest_k_nm_inverse':k[j],'target_bracketed':bool(min(det)<=0<=max(det)),'transition_min_eV':min(tr),'transition_max_eV':max(tr)})
    a.write_csv(OUT/'numerical_resonance_across_k.csv',reson)
    add('O','four-state resonances across measured k',method='Every four-state transition and both photon denominators; no inferred pole from an extremum.',status='PASS',extra={'table':'numerical_resonance_across_k.csv'},interpretation='Pole proximity is necessary for a literal resonance assignment, not proof of a peak or node.')
    for state in ('e1','e2','hh1','hh2'):
        for shift in (-5,5):
            ee=inp.ee.copy();hh=inp.hh.copy();arr=ee if state.startswith('e') else hh;arr[int(state[-1])-1]+=shift/1000
            ev=a.independent_eq2(replace(inp,ee=ee,hh=hh));add('Q',f'{state} {shift:+} meV',ev.total,method='Uniform single-subband diagnostic shift over k, frozen numerator; extends Demo24N with strict extrema windows.')
    dom=set()
    for f in ('Z1','Z2'):dom.update(r['pathway'] for r in dominance if r['feature']==f and r['rank']<=3)
    for key in sorted(dom):
        for delta in (-.1,.1):
            add('R',f'{key} numerator {delta:+.0%}',base.total+delta*base.pathways[key],method='Change exactly one dominant pathway numerator ±10%; diagnostic only. No claim of achievable physical matrix perturbation.')
    for shift in (-.10,-.05,-.02,0,.02,.05,.10):
        ev=base if shift==0 else a.independent_eq2(replace(inp,ee=inp.ee+shift))
        add('global_energy','global transition offset '+str(shift)+' eV',ev.total,method='NONPHYSICAL SENSITIVITY DIAGNOSTIC: same offset to all four transition energies, no peak-specific fit.')
    for scale in (.9,.95,1,1.05,1.1):
        ev=base if scale==1 else a.independent_eq2(replace(inp,ee=inp.ee*scale,hh=inp.hh*scale))
        add('global_energy','global transition scale '+str(scale),ev.total,method='NONPHYSICAL SENSITIVITY DIAGNOSTIC: scale all energies and hence all differences; Gamma fixed.')
    # Mapping diagnostics compare only true overlapping domain and use original normalization.
    for label,xx in [('lambda_half',inp.wavelength/2),('lambda_double',inp.wavelength*2)]+[(f'wavelength shift {s}',inp.wavelength+s) for s in (-100,-50,50,100)]+[(f'wavelength scale {s}',inp.wavelength*s) for s in (.9,.95,1.05,1.1)]:
        mask=(inp.wavelength>=xx[0])&(inp.wavelength<=xx[-1]);yn=np.interp(inp.wavelength[mask],xx,a.norm(abs(base.total)));pn=a.norm(np.interp(inp.wavelength,inp.paper_x,inp.paper_y))[mask]
        rm=a.rmse(yn,pn);base_common=a.rmse(a.norm(abs(base.total))[mask],pn)
        row=add('W',label,method='Final-axis diagnostic; compare shared support only; original full-grid normalization preserved. NO extrapolation.',extra={'shared_min_nm':inp.wavelength[mask][0],'shared_max_nm':inp.wavelength[mask][-1],'common_domain_RMSE':rm,'baseline_same_domain_RMSE':base_common},interpretation='Common-domain metric is not ranked against full-domain baseline; coordinate remapping cannot invent additional extrema.')
        row['improved']='YES' if rm<base_common-1e-8 else 'NO'
    for method in ('linear','shape_preserving_cubic','direct_paper_points'):
        if method=='direct_paper_points':
            yy=np.interp(inp.paper_x,inp.wavelength,a.norm(abs(base.total)));valid=(inp.paper_x>=min(inp.wavelength))&(inp.paper_x<=max(inp.wavelength));err=a.rmse(yy[valid],a.norm(inp.paper_y)[valid])
            add('X',method,method='Sample model at digitized points; original model normalization. Distinct sampling measure.',status='PASS',extra={'direct_point_RMSE':err,'point_count':int(sum(valid))})
        else:
            p=np.interp(inp.wavelength,inp.paper_x,inp.paper_y) if method=='linear' else hermite(inp.paper_x,inp.paper_y,inp.wavelength)
            add('X','paper '+method,base.total,method='Interpolation-method robustness, not experimental error bars.',paper=p,status='PASS',extra={'paper_feature_metrics':metrics(inp,p.astype(complex),paper=p)})
    checks.extend([('independent_baseline_matches_stored',float(np.max(abs(base.total-inp.stored)))<1e-8),('pathway_subtotal',np.allclose(sum(base.pathways.values()),base.total)),('strict_P1_does_not_alias_P2',baseline['P1_nm'] is None),('all_metrics_finite',all(np.isfinite(r['normalized_RMSE']) for r in rows if 'normalized_RMSE' in r))])
    # Verify interpolation cannot overshoot each interval for monotone sample data.
    tx=np.array([0.,1.,2.,3.]);ty=np.array([0.,1.,1.1,2.]);q=np.linspace(0,3,301);yy=hermite(tx,ty,q)
    checks.append(('cubic_monotone_no_invented_extrema',bool(np.all(np.diff(yy)>=-1e-12))))
    a.write_csv(OUT/'numerical_test_checks.csv',[{'check':n,'passed':bool(v)} for n,v in checks]);assert all(v for _,v in checks)
    for filename in ('numerical_rows.json','numerical_test_rows.json'):
        (OUT/filename).write_text(json.dumps(rows,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v)),encoding='utf-8')
    keys=list(dict.fromkeys(k for row in rows for k in row));a.write_csv(OUT/'numerical_metrics.csv',[{k:r.get(k,'') for k in keys} for r in rows])
    a.write_csv(OUT/'numerical_spectra.csv',[{'wavelength_nm':float(x),**{key:float(y[i]) for key,y in spectra.items()}} for i,x in enumerate(inp.wavelength)])
    fig,axs=plt.subplots(2,2,figsize=(14,9));paper=a.norm(np.interp(inp.wavelength,inp.paper_x,inp.paper_y))
    groups=[('Observable diagnostics',[k for k in spectra if k.startswith('observable')]),('Broadening magnitude',[k for k in spectra if k.startswith('Gamma') and k.endswith('magnitude')]),('Matrix-source diagnostic',[k for k in spectra if k.startswith('projected')]),('Global energy diagnostic',[k for k in spectra if k.startswith('global transition offset')])]
    for ax,(title,keys) in zip(axs.flat,groups):
        ax.plot(inp.wavelength,paper,'k--',label='paper');ax.plot(inp.wavelength,a.norm(abs(base.total)),color='grey',lw=2,label='baseline')
        for key in keys:ax.plot(inp.wavelength,spectra[key],label=key.split('__')[0],alpha=.8,lw=1)
        ax.set(title=title,xlabel='Fundamental wavelength (nm)',ylabel='Normalized observable');ax.legend(fontsize=6)
    fig.tight_layout();fig.savefig(OUT/'numerical_comparison.png',dpi=170);plt.close(fig)
    print(json.dumps({'rows':len(rows),'checks':len(checks),'baseline':baseline,'best':sorted([r for r in rows if 'normalized_RMSE' in r],key=lambda r:r['normalized_RMSE'])[:5]},default=str))

if __name__=='__main__':main()
