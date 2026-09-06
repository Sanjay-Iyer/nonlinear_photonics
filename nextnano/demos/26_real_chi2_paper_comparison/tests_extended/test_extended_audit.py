"""Automated gates for the Demo 26 extended implementation audit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).resolve().parents[1] / "extended_implementation_audit.py"
SPEC = importlib.util.spec_from_file_location("demo26_extended", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def inputs():
    return audit.load_inputs()


def test_abs_real_calculation():
    inp = inputs()
    ev = audit.independent_eq2(inp)
    actual = audit.norm(np.abs(ev.total.real))
    assert np.all(actual >= 0)
    assert np.isclose(actual.max(), 1)


def test_gamma_zero_diagnostic_handling():
    ev = audit.independent_eq2(inputs(), 0)
    assert np.all(np.isfinite(ev.total))


def test_independent_equation2_engine_matches_preserved_engine():
    inp = inputs()
    ev = audit.independent_eq2(inp)
    assert np.max(np.abs(ev.total - inp.stored)) < 1e-8


def test_pathway_sum_consistency():
    ev = audit.independent_eq2(inputs())
    assert np.allclose(sum(ev.pathways.values()), ev.total, rtol=2e-13, atol=2e-12)
    assert np.allclose(ev.electron + ev.hole, ev.total, rtol=2e-13, atol=2e-12)


def test_k_integration_variants():
    inp = inputs()
    p = audit.independent_eq2(inp, convention="production").total
    r = audit.independent_eq2(inp, convention="radial_kdk").total
    b = audit.independent_eq2(inp, convention="bare_2pi_kdk").total
    assert np.allclose(audit.norm(np.abs(p)), audit.norm(np.abs(r)), atol=2e-13)
    assert np.allclose(audit.norm(np.abs(p)), audit.norm(np.abs(b)), atol=2e-13)
    assert np.all(np.isfinite(audit.independent_eq2(inp, convention="equal_points").total))
    assert np.all(np.isfinite(audit.independent_eq2(inp, convention="k0_only").total))


def test_wavefunction_sign_invariance():
    inp = inputs(); ref = audit.independent_eq2(inp).total
    for signs in ((-1,1,1,1),(1,-1,1,1),(1,1,-1,1),(1,1,1,-1),(-1,-1,-1,-1)):
        se=np.array(signs[:2]); sh=np.array(signs[2:])
        o=np.conj(se)[:,None]*sh[None,:]*inp.overlap
        ze=np.conj(se)[:,None]*se[None,:]*inp.ze
        zh=np.conj(sh)[:,None]*sh[None,:]*inp.zh
        assert np.allclose(audit.independent_eq2(inp,overlap=o,ze=ze,zh=zh).total,ref,atol=2e-12)


def test_z_origin_translation_invariance():
    inp=inputs(); ref=audit.independent_eq2(inp).total
    for z0 in (-15,-5,5,15):
        shifted=audit.independent_eq2(inp,ze=inp.ze+z0*np.eye(2),zh=inp.zh+z0*np.eye(2)).total
        assert np.allclose(shifted,ref,rtol=2e-13,atol=3e-12)


def test_i_gamma_sign_is_complex_conjugation():
    inp=inputs()
    plus=audit.independent_eq2(inp,5,gamma_sign=1).total
    minus=audit.independent_eq2(inp,5,gamma_sign=-1).total
    assert np.allclose(minus,np.conj(plus),rtol=2e-13,atol=2e-12)
    assert np.allclose(np.abs(minus),np.abs(plus),rtol=2e-13,atol=2e-12)


def test_global_phase_transformation():
    values=audit.independent_eq2(inputs()).total
    assert np.allclose(np.exp(-1j*0)*values,values)
    assert np.allclose(np.abs(np.exp(-1j*np.pi/2)*values),np.abs(values))


def test_peak_matching_finds_preserved_major_peaks():
    inp=inputs(); pos=audit.feature_positions(inp,audit.independent_eq2(inp).total)
    assert abs(pos["P2"]-752) <= 2
    assert abs(pos["P4"]-1503) <= 2


def test_paper_digitization_integrity():
    inp=inputs()
    assert len(inp.paper_x)==45
    assert np.all(np.diff(inp.paper_x)>0)
    assert np.all(inp.paper_y>=0)
    assert inp.paper_y[np.where(inp.paper_x==605)[0][0]]==0
    assert inp.paper_y[np.where(inp.paper_x==1330)[0][0]]==0


def test_no_professional_invocation():
    source=MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "subprocess" not in source
    assert "nextnano.exe" not in source
    assert "nextnano professional" not in source


def test_demo23_demo24_and_existing_demo26_are_unchanged():
    for name,expected in audit.BASELINE_HASHES.items():
        path=audit.ROOT/"nextnano/demos"/name
        count,digest=audit.directory_fingerprint(path,demo26=name.startswith("26_"))
        assert count in (41,96,22)
        assert digest==expected
