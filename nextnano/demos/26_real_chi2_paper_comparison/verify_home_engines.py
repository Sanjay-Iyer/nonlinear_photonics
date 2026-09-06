"""Read-only solver-independent engine audit; outputs additive verification evidence."""
from pathlib import Path
import sys, inspect, hashlib, json, itertools, ast
import numpy as np
import extended_implementation_audit as a

OUT=a.HERE/'outputs/HOME_EXHAUSTIVE_AUDIT'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.HERE.parent/'22_k_resolved_8band_chi2_validation'))
import chi2_22 as prod

def run():
    inp=a.load_inputs(); independent=a.independent_eq2(inp)
    fn=prod.chi2_from_k_inputs
    source,start=inspect.getsourcelines(fn)
    value_lines=[start+i for i,line in enumerate(source) if 'value = numerator /' in line]
    rows=[]
    def trace(frame,event,arg):
        if frame.f_code is fn.__code__ and event=='line' and frame.f_lineno in value_lines:
            loc=frame.f_locals; family='C' if frame.f_lineno==value_lines[0] else 'V'
            label=f"{family}_m{loc['m']+1}_n{loc['n']+1}_l{loc['ell']+1}"
            ref=independent.denominators[label]
            rows.append({'pathway':label,'d2_max_abs_error_eV':float(np.max(np.abs(loc['d2']-ref[0]))),'d1_max_abs_error_eV':float(np.max(np.abs(loc['d1']-ref[1]))),'samples_per_denominator':loc['d1'].size})
        return trace
    def evaluate(o=inp.overlap,ze=inp.ze,zh=inp.zh):
        return fn(inp.wavelength,inp.k,inp.ee,inp.hh,o,ze,zh)
    sys.settrace(trace)
    try: baseline=evaluate()
    finally: sys.settrace(None)
    a.write_csv(OUT/'DIRECT_ENGINE_DENOMINATOR_COMPARISON.csv',rows)
    paths=[{'pathway':label,'max_abs_error_pm_per_V':float(np.max(np.abs(independent.pathways[label]-baseline.terms[i])))} for i,label in enumerate(baseline.term_labels)]
    a.write_csv(OUT/'DIRECT_ENGINE_PATHWAY_COMPARISON.csv',paths)
    gauge=[]
    # O[n,m]=<e_n|h_m>; transform every matrix consistently.
    for phases in ([0.3,0,0,0],[0,0.7,0,0],[0,0,1.1,0],[0,0,0,1.7],[0.3,0.7,1.1,1.7]):
        se=np.exp(1j*np.array(phases[:2])); sh=np.exp(1j*np.array(phases[2:]))
        o=se.conj()[:,None]*sh[None,:]*inp.overlap
        ze=se.conj()[:,None]*se[None,:]*inp.ze
        zh=sh.conj()[:,None]*sh[None,:]*inp.zh
        pv=evaluate(o,ze,zh).chi2; iv=a.independent_eq2(inp,overlap=o,ze=ze,zh=zh).total
        gauge.append({'phases_radians':str(phases),'production_max_complex_change_pm_per_V':float(np.max(abs(pv-baseline.chi2))),'production_max_magnitude_change_pm_per_V':float(np.max(abs(abs(pv)-abs(baseline.chi2)))),'independent_max_complex_change_pm_per_V':float(np.max(abs(iv-independent.total)))})
    a.write_csv(OUT/'CONTINUOUS_COMPLEX_GAUGE_AUDIT.csv',gauge)
    # Retain original frozen baseline fingerprints, excluding only additive files.
    preserves=[]
    for name,expected in a.BASELINE_HASHES.items():
        root=a.ROOT/'nextnano/demos'/name
        excluded={'__pycache__','EXTENDED_IMPLEMENTATION_AUDIT','tests_extended','HOME_EXHAUSTIVE_AUDIT'}
        new_names={'extended_implementation_audit.py','numerical_home_audit.py','verify_home_engines.py','build_home_report.py','test_home_audit.py','close_data_tests.py'}
        files=[p for p in sorted(root.rglob('*')) if p.is_file() and not any(x in p.parts for x in excluded)]
        if name.startswith('26_'): files=[p for p in files if p.name not in new_names]
        records=''.join(f'{p.relative_to(root).as_posix()}\0{hashlib.sha256(p.read_bytes()).hexdigest()}\0{p.stat().st_size}\n' for p in files)
        digest=hashlib.sha256(records.encode()).hexdigest()
        preserves.append({'dataset':name,'file_count':len(files),'expected':expected,'actual':digest,'unchanged':digest==expected})
    a.write_csv(OUT/'ORIGINAL_ARTIFACT_PRESERVATION.csv',preserves)
    tree=ast.parse(inspect.getsource(a.independent_eq2))
    calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
    result={'baseline_final_max_error_pm_per_V':float(np.max(abs(baseline.chi2-independent.total))),
      'stored_final_max_error_pm_per_V':float(np.max(abs(inp.stored-independent.total))),
      'electron_subtotal_max_error_pm_per_V':float(np.max(abs(baseline.terms[[i for i,l in enumerate(baseline.term_labels) if l.startswith('C')]].sum(axis=0)-independent.electron))),
      'hole_subtotal_max_error_pm_per_V':float(np.max(abs(baseline.terms[[i for i,l in enumerate(baseline.term_labels) if l.startswith('V')]].sum(axis=0)-independent.hole))),
      'denominator_max_error_eV':max(max(r['d1_max_abs_error_eV'],r['d2_max_abs_error_eV']) for r in rows),
      'max_pathway_error_pm_per_V':max(r['max_abs_error_pm_per_V'] for r in paths),
      'independent_function_calls':calls,'original_artifacts_preserved':all(r['unchanged'] for r in preserves),
      'continuous_gauge_tests':gauge,
      'scope':'No solver invoked. Production complex-input conjugation limitation does not alter real frozen baseline.'}
    (OUT/'engine_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert result['denominator_max_error_eV']<1e-10
    assert result['baseline_final_max_error_pm_per_V']<1e-8
    assert all(r['independent_max_complex_change_pm_per_V']<1e-8 for r in gauge)
    print(json.dumps(result,indent=2))

if __name__=='__main__': run()
