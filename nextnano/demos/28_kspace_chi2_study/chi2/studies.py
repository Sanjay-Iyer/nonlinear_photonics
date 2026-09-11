"""Shared study orchestration. Configurations vary inputs, never Eq2 algebra."""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import platform
import numpy as np
from .input_builder import build_inputs
from .equation2 import Settings,calculate_chi2,prefactor
from .k_integration import select_range
from .artifacts import write_json,save_parsed,save_inputs,save_spectrum,manifest
from .diagnostics import features,paper_metrics
from . import plotting

ROOT=Path(__file__).resolve().parents[1]


def load_configuration(config):
    cfg=json.loads(Path(config).read_text())
    if cfg.get('model')!='demo26-baseline': raise ValueError('28A/28B currently preserve only the historical demo26-baseline model')
    wave=cfg['wavelength_nm']
    if not all(np.isfinite(wave[k]) for k in ('min','max','step')) or not 0<wave['min']<wave['max'] or wave['step']<=0:
        raise ValueError('Invalid fundamental wavelength min/max/step')
    wl=np.arange(wave['min'],wave['max']+wave['step']/2,wave['step'])
    return cfg,Settings(**cfg['settings']),wl


def setup(config,raw_root,out):
    cfg,settings,wl=load_configuration(config)
    raw=Path(raw_root) if raw_root else ROOT/cfg['raw_input']
    inputs,parsed=build_inputs(raw)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    save_parsed(out/'parsed_data',parsed)
    provenance=manifest(raw)
    write_json(out/'raw_manifest.json',provenance)
    code_manifest=manifest(ROOT/'chi2')
    write_json(out/'code_manifest.json',[p for p in code_manifest if p['file'].endswith('.py')])
    meta={'configuration':cfg,'settings':asdict(settings),'gamma_eV':settings.gamma_eV,
          'raw_root':str(raw.resolve()),'raw_manifest':'raw_manifest.json','python':platform.python_version(),
          'code_version':'source SHA256 manifest (includes uncommitted code)','code_manifest':'code_manifest.json',
          'k_units':'nm^-1','BZ_conversion':'f*pi/a with a=0.565325 nm; radial disk approximation, not full BZ geometry',
          'numpy':np.__version__,'licensed_solver_executed':False,'model':inputs['model'],
          'state_pairs':inputs['kp8_pair_ids'],'limitations':inputs['limitations'],
          'wavelength_points':len(wl),'wavelength_min_nm':float(wl[0]),'wavelength_max_nm':float(wl[-1]),
          'integration_measure':'g_s*k*dk/(2*pi), trapezoidal; isotropic in-plane approximation',
          'prefactor':prefactor(settings),'prefactor_units':'maps nm/eV^2 times nm^-2 to historical pm/V convention',
          'pathway_count':16,'normalization':'signed Re/Im and all sweep plots unnormalized; optional paper comparison uses own maxima'}
    return cfg,settings,wl,inputs,meta


def numerical_checks(result,settings):
    reconstructed=prefactor(settings)*(result.summed_integrand@result.k_weights_nm_minus2)
    error=float(np.max(abs(reconstructed-result.chi2_complex)))
    return {'integrand_reintegration_error_pm_per_V':error,'integrand_reintegration_tolerance_pm_per_V':1e-9,
            'integrand_reintegration_PASS':error<1e-9,
            'modulus_identity_error':float(np.max(abs(abs(result.chi2_complex)-np.hypot(result.chi2_complex.real,result.chi2_complex.imag)))),
            'pathways':len(result.pathway_labels),'finite':bool(np.isfinite(result.chi2_complex).all())}


def run_baseline(config=ROOT/'config/baseline.json',raw_root=None,out=ROOT/'outputs/28A_baseline',make_plots=True):
    out=Path(out)
    cfg,settings,wl,inputs,meta=setup(config,raw_root,out)
    save_inputs(out/'chi2_inputs',inputs,settings,wl)  # BEFORE evaluating Equation 2
    result=calculate_chi2(wl,inputs,settings)
    save_spectrum(out/'chi2_results',result,cfg['save_integrand'])
    evaluator=lambda w:calculate_chi2(w,inputs,settings).chi2_complex
    f=features(wl,result.chi2_complex,evaluator)
    paper=np.loadtxt(ROOT/'validation/paper_fig2d.csv',delimiter=',',skiprows=1)
    old=np.loadtxt(ROOT/'validation/demo26_baseline_reference.csv',delimiter=',',skiprows=1)
    prior=json.loads((ROOT/'validation/prior_condensed_baseline_summary.json').read_text())
    if np.array_equal(wl,old[:,0]):
        err=float(np.max(abs(result.chi2_complex-(old[:,1]+1j*old[:,2]))))
        ref={'status':'PASS' if err<=cfg['reference_tolerance_pm_per_V'] else 'FAIL','max_complex_error_pm_per_V':err,
             'tolerance_pm_per_V':cfg['reference_tolerance_pm_per_V'],'source':'validation/demo26_baseline_reference.csv'}
    else: ref={'status':'NOT_COMPARABLE','reason':'wavelength grid changed'}
    prior_roots=np.array([r['wavelength_nm'] for r in prior['features']['re_zero_crossings']])
    roots=np.array([r['wavelength_nm'] for r in f['Re_zero_crossings']])
    zero_err=float(max(abs(prior_roots-roots))) if roots.shape==prior_roots.shape else None
    checks=numerical_checks(result,settings)
    meta.update(study='28A_baseline',features=f,reference_validation=ref,
                reference_zero_max_error_nm=zero_err,reference_zero_tolerance_nm=cfg['feature_zero_tolerance_nm'],
                checks=checks,k_points=len(inputs['k_per_nm']),k_max_per_nm=float(inputs['k_per_nm'][-1]),
                paper_metrics=paper_metrics(wl,result.chi2_complex,paper))
    passed=ref['status']=='PASS' and zero_err is not None and zero_err<=cfg['feature_zero_tolerance_nm'] and checks['finite'] and checks['integrand_reintegration_PASS']
    meta['validation_status']='PASS' if passed else 'FAIL'
    write_json(out/'metadata.json',meta)
    if make_plots: plotting.baseline(out/'plots',wl,result.chi2_complex,paper)
    print(f"28A: {meta['validation_status']}; {len(inputs['k_per_nm'])} k points; Gamma={settings.gamma_meV} meV; 16 pathways; {out}")
    print(f"  complex reference error: {ref.get('max_complex_error_pm_per_V')}; Re zeros nm: {roots.tolist()}")
    return meta


def run_sweep(config=ROOT/'config/kspace_sweeps.json',raw_root=None,out=ROOT/'outputs/28B_kspace_cutoff',make_plots=True):
    out=Path(out);sweep=json.loads(Path(config).read_text())
    if sweep['integration_method']!='native_grid_trapezoid': raise ValueError('Only native_grid_trapezoid is implemented; no silent method substitution')
    fractions=np.asarray(sweep['k_cutoffs_pi_over_a'],float)
    if not len(fractions) or not np.all(np.isfinite(fractions)) or np.any(fractions<=0) or np.any(np.diff(fractions)<=0):
        raise ValueError('k_cutoffs_pi_over_a must be strictly increasing positive values')
    if any(not np.any(np.isclose(fractions,f,rtol=0,atol=1e-12)) for f in sweep['selected_cutoffs_pi_over_a']):
        raise ValueError('Selected overlay cutoffs must belong to the sweep')
    lattice=sweep['lattice_constant_nm']
    if not np.isfinite(lattice) or lattice<=0: raise ValueError('lattice_constant_nm must be positive finite')
    boundary_tolerance=sweep['boundary_rounding_tolerance_per_nm']
    if not np.isfinite(boundary_tolerance) or not 0<=boundary_tolerance<=1e-8:
        raise ValueError('boundary_rounding_tolerance_per_nm must be between 0 and 1e-8; it is only for file roundoff')
    cfg,settings,wl,inputs,meta=setup(ROOT/sweep['baseline_config'],raw_root,out)
    full=calculate_chi2(wl,inputs,settings).chi2_complex
    cases=[];rows=[];valid=True;full_error=None
    for fraction in fractions:
        requested=float(fraction*np.pi/lattice)
        # Clamp only roundoff at the solved upper boundary, never extend data.
        if requested>inputs['k_per_nm'][-1]+sweep['boundary_rounding_tolerance_per_nm']:
            raise ValueError(f'Cutoff {fraction} pi/a exceeds available raw data. Run nextnano on work laptop for larger k.')
        effective=min(requested,float(inputs['k_per_nm'][-1]))
        selected=select_range(inputs,effective,sweep['lower_cutoff_per_nm'])
        name=f"kmax_{fraction:.5f}".replace('.','p')
        dest=out/'cases'/name
        save_inputs(dest/'chi2_inputs',selected,settings,wl)
        result=calculate_chi2(wl,selected,settings)
        save_spectrum(dest/'chi2_results',result,sweep['save_integrand_each_case'])
        evaluator=lambda w:calculate_chi2(w,selected,settings).chi2_complex
        f=features(wl,result.chi2_complex,evaluator,sweep['target_wavelength_nm'])
        check=numerical_checks(result,settings)
        actual=float(selected['k_per_nm'][-1])
        within=bool(np.all(selected['k_per_nm']<=requested))
        same_grid=np.array_equal(selected['k_per_nm'],inputs['k_per_nm'])
        error=float(np.max(abs(full-result.chi2_complex))) if same_grid else None
        if same_grid: full_error=error
        valid=valid and within and check['finite'] and check['integrand_reintegration_PASS']
        info={**meta,'study':'28B_kspace_cutoff','sweep_configuration':sweep,'cutoff_pi_over_a':float(fraction),
              'requested_kmax_per_nm':requested,'actual_kmax_per_nm':actual,'selection':selected['selection'],
              'number_of_k_points':len(selected['k_per_nm']),'features':f,'checks':check,
              'no_samples_above_requested_cutoff':within,'full_baseline_error_pm_per_V':error}
        info['raw_manifest']='../../raw_manifest.json'
        info['code_manifest']='../../code_manifest.json'
        write_json(dest/'metadata.json',info)
        roots=f['Re_zero_crossings']
        rows.append({'kmax_pi_over_a':fraction,'requested_kmax_per_nm':requested,'actual_kmax_per_nm':actual,
                     'number_of_k_points':len(selected['k_per_nm']),
                     **{key:f[key] for key in ['dominant_abs_Re_wavelength_nm','dominant_abs_Im_wavelength_nm','max_abs_Re_pm_per_V','max_abs_Im_pm_per_V','Re_at_target_pm_per_V','Im_at_target_pm_per_V']},
                     'Re_zero_count':len(roots),'Re_zero_1_nm':roots[0]['wavelength_nm'] if roots else '',
                     'Re_zero_2_nm':roots[1]['wavelength_nm'] if len(roots)>1 else '',
                     'no_points_above_cutoff':within})
        cases.append({'fraction':float(fraction),'features':f,'chi':result.chi2_complex})
        print(f"28B: kmax={fraction:.3g} pi/a, actual={actual:.9g} nm^-1, nk={len(selected['k_per_nm'])}, Gamma={settings.gamma_meV} meV")
    with (out/'kspace_sweep.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    valid=bool(valid and (full_error is None or full_error<=sweep['full_cutoff_tolerance_pm_per_V']))
    meta.update(study='28B_kspace_cutoff',sweep_configuration=sweep,case_count=len(cases),
                validation_status='PASS' if valid else 'FAIL',all_cases_within_cutoffs=bool(all(r['no_points_above_cutoff'] for r in rows)),
                full_cutoff_vs_baseline_error_pm_per_V=full_error,
                full_cutoff_check='NOT_APPLICABLE: full solved range not requested' if full_error is None else 'PASS' if full_error<=sweep['full_cutoff_tolerance_pm_per_V'] else 'FAIL')
    write_json(out/'metadata.json',meta)
    if make_plots: plotting.sweep(out/'plots',wl,cases,sweep['selected_cutoffs_pi_over_a'])
    print(f"28B: {meta['validation_status']}; full-cutoff baseline error {full_error}; {out}")
    return meta


def cli(study,argv=None):
    parser=argparse.ArgumentParser(description=f'Run Demo {study} using cached raw nextnano data; no solver launch')
    parser.add_argument('--input',type=Path)
    parser.add_argument('--config',type=Path,default=ROOT/'config'/('baseline.json' if study=='28A' else 'kspace_sweeps.json'))
    parser.add_argument('--output',type=Path,default=ROOT/'outputs'/('28A_baseline' if study=='28A' else '28B_kspace_cutoff'))
    parser.add_argument('--no-plots',action='store_true')
    args=parser.parse_args(argv)
    try:
        result=(run_baseline if study=='28A' else run_sweep)(args.config,args.input,args.output,not args.no_plots)
        return 0 if result['validation_status']=='PASS' else 2
    except (ValueError,OSError,KeyError) as exc:
        print(f'ERROR: {exc}');return 1
