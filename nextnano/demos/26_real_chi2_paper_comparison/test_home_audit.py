"""Artifact and scientific-regression checks for the additive exhaustive audit."""
import csv,json,hashlib
from pathlib import Path
import numpy as np
import numerical_home_audit as n
HERE=Path(__file__).resolve().parent
OUT=HERE/'outputs/HOME_EXHAUSTIVE_AUDIT'

def test_numbered_rows_have_required_fields_and_all_families():
    rows=json.loads((OUT/'numbered_tests.json').read_text())
    keys=('question','method','input_data','result','status','improved','evidence','interpretation','possible_reason','plausible','pro_required')
    for i,row in enumerate(rows,1):
        assert row['test_number']==f'TEST {i:02d}'
        assert all(str(row.get(k,'')).strip() for k in keys)
        assert row['status'] in ('PASS','FAIL','INCONCLUSIVE','NOT TESTABLE')
    assert set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')<=set(r['family'] for r in rows)

def test_report_counts_are_reproducible():
    r=json.loads((OUT/'numbered_tests.json').read_text());s=json.loads((OUT/'audit_counts.json').read_text())
    assert s['total_tests']==len(r)
    assert sum(s['status_counts'].values())==len(r)
    assert s['improved_agreement']+s['did_not_improve']+s['fit_not_applicable']==len(r)

def test_actual_engine_and_gauge_evidence():
    e=json.loads((OUT/'engine_verification.json').read_text())
    assert e['denominator_max_error_eV']==0
    assert e['baseline_final_max_error_pm_per_V']<1e-8
    assert all(r['independent_max_complex_change_pm_per_V']<1e-8 for r in e['continuous_gauge_tests'])
    assert max(r['production_max_magnitude_change_pm_per_V'] for r in e['continuous_gauge_tests'])>1

def test_old_output_manifest_preserved():
    for r in json.loads((OUT/'PRIOR_OUTPUT_HASHES.json').read_text()):
        assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']

def test_review_and_report_are_present_without_pending_placeholder():
    review=(OUT/'PHYSICS_PROFESSOR_REVIEW_HOME_EXHAUSTIVE.md').read_text(encoding='utf-8')
    report=(OUT/'DEMO26_HOME_EXHAUSTIVE_FINAL_REPORT.md').read_text(encoding='utf-8')
    assert len(review)>2000 and review in report
    assert 'PENDING — independent review not yet delivered' not in report

def test_no_false_baseline_peak_recovery():
    r=json.loads((OUT/'numbered_tests.json').read_text())[0]
    assert r['P1_nm'] is None and r['P3_nm'] is None
    assert abs(r['P2_nm']-752)<2 and abs(r['P4_nm']-1503)<2

def test_saved_numerical_checks_pass():
    with (OUT/'numerical_test_checks.csv').open() as f:r=list(csv.DictReader(f))
    assert len(r)==8 and all(x['passed']=='True' for x in r)

def test_monotone_cubic_is_bounded_on_nonuniform_grid():
    x=np.array([0.,.1,.8,2.,3.]);y=np.array([0.,.01,.9,1.,1.001])
    for i in range(len(x)-1):
        q=np.linspace(x[i],x[i+1],51);z=n.hermite(x,y,q)
        assert np.min(z)>=y[i]-1e-12 and np.max(z)<=y[i+1]+1e-12
