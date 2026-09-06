"""Bounded existing-data diagnostics; no solver or production-file mutation."""
import json
from dataclasses import replace
import numpy as np
import extended_implementation_audit as a
from numerical_home_audit import metrics, OUT

def main():
    inp=a.load_inputs(); baseline=metrics(inp,a.independent_eq2(inp).total)['normalized_RMSE']; rows=[]; spectra={}
    def add(family,variant,trial,method,evidence,convention='production'):
        ev=a.independent_eq2(trial,convention=convention); met=metrics(inp,ev.total)
        rows.append(dict(family=family,variant=variant,question='Can this existing-data alternative explain the discrepancy?',method=method,input_data=evidence.get('source',''),result='method-limited diagnostic; paper reproduction not established',status='INCONCLUSIVE',improved='YES' if met['normalized_RMSE']<baseline else 'NO',evidence=json.dumps(evidence),interpretation='No new solver data. Physical validity is not established; aggregate RMSE does not replace strict feature matching.',possible_reason='Changes in poles and numerator cancellation',plausible='YES',pro_required='NO',physical_valid=False,**met))
        spectra[variant]=abs(ev.total)/max(abs(ev.total))
    for row in a.read_rows(a.MATRIX):
        o=np.array([[float(row[f'O{n}{m}']) for m in (1,2)] for n in (1,2)],complex)
        ze=np.array([[float(row[f'z_e{n}{m}_nm']) for m in (1,2)] for n in (1,2)],complex)
        zh=np.array([[float(row[f'z_hh{n}{m}_nm']) for m in (1,2)] for n in (1,2)],complex)
        # Same geometry supplies ALL k0 energies and matrices; Demo20 parabolic masses.
        ee=np.array([float(row['E1_eV']),float(row['E2_eV'])])[:,None]+.0380998212/.067*inp.k**2
        hh=np.array([float(row['HH1_eV']),float(row['HH2_eV'])])[:,None]-.0380998212/.112*inp.k**2
        trial=replace(inp,ee=ee,hh=hh,overlap=o,ze=ze,zh=zh)
        for conv in ('production','k0_only'):
            add('K','consistent scalar '+row['case_name']+' '+conv,trial,'Same-case scalar energies and matrices; parabolic me=.067, mhh=.112 m0 from Demo20; k cutoff retained for matched comparison.',{'source':str(a.MATRIX),'case_id':row['case_id'],'source_physical_valid':row['physical_valid'],'source_failure':row['failure_reason'],'geometry':row['case_name'],'mass_reference':'Demo21 demo20_math_physics_reference.py lines375-390'},conv)
    rawfile=next((a.ROOT/'demo_results/demo23/raw/production_y_n301_k0100').rglob('dispersion_*.dat'))
    data=np.loadtxt(rawfile,skiprows=1)
    ee=np.array([data[:,[11,12]].mean(axis=1),data[:,[13,14]].mean(axis=1)])
    hh=np.array([data[:,[5,6]].mean(axis=1),data[:,[3,4]].mean(axis=1)])
    add('Q','raw unanchored production labels frozen matrices',replace(inp,k=data[:,0],ee=ee,hh=hh),'Remove statewise k0 anchoring only; intentionally cross-method frozen scalar numerator, diagnostic only.',{'source':str(rawfile),'k0_energy_offsets_raw_minus_anchored_eV':(np.r_[ee[:,0],hh[:,0]]-np.r_[inp.ee[:,0],inp.hh[:,0]]).tolist()})
    for branch,spec in [('A',[(11,'cb1'),(13,'cb1'),(6,'hh1'),(2,'hh1')]),('B',[(12,'cb2'),(14,'cb2'),(5,'hh2'),(1,'hh2')])]:
        wf=[a.raw_envelope(*p) for p in spec];x=wf[0][0];assert all(np.allclose(x,w[0]) for w in wf)
        e=[w[1] for w in wf[:2]];h=[w[1] for w in wf[2:]]
        o=np.array([[np.trapezoid(np.conj(v)*w,x) for w in h] for v in e]);ze=np.array([[np.trapezoid(np.conj(v)*x*w,x) for w in e] for v in e]);zh=np.array([[np.trapezoid(np.conj(v)*x*w,x) for w in h] for v in h])
        trial=replace(inp,k=data[:,0],ee=np.array([data[:,s] for s,c in spec[:2]]),hh=np.array([data[:,s] for s,c in spec[2:]]),overlap=o,ze=ze,zh=zh)
        for conv in ('k0_only','production'):
            add('M','pureHH alternative branch '+branch+' '+conv,trial,'Same raw branch energies and normalized dominant-component envelopes; HH pair1/2 replaces LH-dominated pair3/4. No branch averaging; projected-component approximation, not full multiband optical matrix. Finite-k labels uncertified.',{'source':str(rawfile)+'; '+str(a.RAW_ENV),'state_component_spec':spec,'overlap_real':o.real.tolist(),'ze_real_nm':ze.real.tolist(),'zh_real_nm':zh.real.tolist(),'limitation':'Method-limited projected-envelope diagnostic, even for pureHH states; finite-k spinors absent.'},conv)
    (OUT/'additional_data_rows.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    a.write_csv(OUT/'additional_data_spectra.csv',[{'wavelength_nm':float(x),**{k:float(v[i]) for k,v in spectra.items()}} for i,x in enumerate(inp.wavelength)])
    assert all(np.isfinite(r['normalized_RMSE']) for r in rows)
    print(json.dumps([{k:r[k] for k in ('variant','normalized_RMSE','P1_nm','P3_nm','Z1_nm','Z2_nm')} for r in rows],indent=2))

if __name__=='__main__':main()
