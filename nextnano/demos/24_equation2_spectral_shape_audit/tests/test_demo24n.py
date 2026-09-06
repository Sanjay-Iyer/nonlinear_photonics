"""Tests for Demo 24N, the spectral-feature causal sensitivity debugger.

These cover the machinery, not the physics conclusions: the instrumented
mirror must reproduce the production engine, perturbations must be strictly
one-at-a-time, and no routine may invent finite-k data or touch Demo 23.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest


DEMO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_DIR.parents[2]
DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
DEMO23 = DEMO_DIR.parent / "23_k_resolved_dispersion_validation"
for module_dir in (DEMO22, DEMO23, DEMO_DIR):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

import causal_sensitivity as cs  # noqa: E402
import chi2_22  # noqa: E402
from physics23 import validated  # noqa: E402


def _inputs(nk: int = 41, nlam: int = 121):
    """A small, self-contained Equation-2 input set with the real structure."""
    k = np.linspace(0.0, 0.55, nk)
    e1 = 2.9412 + 0.35 * k ** 2
    e2 = 3.0610 + 0.30 * k ** 2
    hh1 = 1.4478 - 0.17 * k ** 2
    hh2 = 1.4128 - 0.15 * k ** 2
    overlap = np.asarray([[0.9823, 0.0154], [-0.0835, 0.3831]])
    z_e = np.asarray([[12.7245, 1.0252], [1.0252, 18.6612]])
    z_hh = np.asarray([[12.6514, 1.4324], [1.4324, 12.7301]])
    lam = np.linspace(500.0, 1700.0, nlam)
    settings = validated.Chi2Settings(broadening_meV=5.0)
    return {
        "wavelengths_nm": lam, "k_per_nm": k,
        "electron_energies_eV": np.vstack([e1, e2]),
        "hole_energies_eV": np.vstack([hh1, hh2]),
        "overlap_eh": overlap, "z_e_nm": z_e, "z_h_nm": z_hh,
        "subbands": {"e1": e1, "e2": e2, "hh1": hh1, "hh2": hh2},
        "settings": settings,
    }


def _build(data, **kwargs):
    return cs.instrumented_spectrum(
        data["wavelengths_nm"], data["k_per_nm"], data["electron_energies_eV"],
        data["hole_energies_eV"], data["overlap_eh"], data["z_e_nm"], data["z_h_nm"],
        broadening_meV=data["settings"].broadening_meV, settings=data["settings"], **kwargs)


SPECS = [
    {"name": "P1", "type": "peak", "wavelength_nm": 540.0, "window_nm": [500.0, 575.0]},
    {"name": "Z1", "type": "minimum", "wavelength_nm": 605.0, "window_nm": [550.0, 650.0]},
    {"name": "P2", "type": "peak", "wavelength_nm": 760.0, "window_nm": [680.0, 830.0]},
    {"name": "P4", "type": "peak", "wavelength_nm": 1520.0, "window_nm": [1420.0, 1620.0]},
]


# --- the mirror must be the production engine ------------------------------

def test_instrumented_mirror_reproduces_production_engine():
    data = _inputs()
    production = chi2_22.chi2_from_k_inputs(
        data["wavelengths_nm"], data["k_per_nm"], data["electron_energies_eV"],
        data["hole_energies_eV"], data["overlap_eh"], data["z_e_nm"], data["z_h_nm"],
        broadening_meV=5.0, settings=data["settings"])
    mirror = _build(data, keep_k_integrand=True)
    error = cs.assert_matches_production(mirror, production)
    assert error / np.max(np.abs(production.chi2)) < 1e-12


def test_pathway_order_and_metadata_match_production_labels():
    data = _inputs()
    production = chi2_22.chi2_from_k_inputs(
        data["wavelengths_nm"], data["k_per_nm"], data["electron_energies_eV"],
        data["hole_energies_eV"], data["overlap_eh"], data["z_e_nm"], data["z_h_nm"],
        broadening_meV=5.0, settings=data["settings"])
    assert tuple(item.label for item in cs.PATHWAYS) == tuple(production.term_labels)
    assert len(cs.PATHWAYS) == 16
    assert sum(1 for p in cs.PATHWAYS if p.side == "electron_side") == 8


def test_k_integrand_sums_back_to_pathway_terms():
    mirror = _build(_inputs(), keep_k_integrand=True)
    assert np.allclose(mirror.k_integrand.sum(axis=2), mirror.terms, rtol=0, atol=1e-12)


def test_sixteen_terms_sum_to_total():
    mirror = _build(_inputs())
    assert np.allclose(mirror.terms.sum(axis=0), mirror.chi2, rtol=0, atol=1e-12)


def test_electron_and_signed_hole_subtotals_reproduce_total():
    mirror = _build(_inputs())
    electron = sum(mirror.terms[p.index] for p in cs.PATHWAYS if p.side == "electron_side")
    hole = sum(mirror.terms[p.index] for p in cs.PATHWAYS if p.side != "electron_side")
    assert np.allclose(electron + hole, mirror.chi2, rtol=0, atol=1e-12)


# --- perturbations must be one-at-a-time and correctly scoped ---------------

def test_amplitude_scaling_touches_only_the_named_pathway():
    data = _inputs()
    base = _build(data)
    scaled = _build(data, amplitude_scale={"C_m1_n1_l1": 0.9})
    target = cs.PATHWAY_BY_LABEL["C_m1_n1_l1"].index
    assert np.allclose(scaled.terms[target], 0.9 * base.terms[target], rtol=0, atol=1e-12)
    for item in cs.PATHWAYS:
        if item.index != target:
            assert np.allclose(scaled.terms[item.index], base.terms[item.index], rtol=0, atol=1e-12)


def test_phase_rotation_preserves_pathway_magnitude():
    data = _inputs()
    base = _build(data)
    rotated = _build(data, phase_shift_rad={"V_m1_n1_l1": np.radians(10.0)})
    index = cs.PATHWAY_BY_LABEL["V_m1_n1_l1"].index
    assert np.allclose(np.abs(rotated.terms[index]), np.abs(base.terms[index]), rtol=1e-12, atol=0)
    assert not np.allclose(rotated.terms[index], base.terms[index])


def test_unknown_pathway_label_is_rejected():
    with pytest.raises(ValueError, match="unknown pathway"):
        _build(_inputs(), amplitude_scale={"C_m9_n9_l9": 1.1})


def test_energy_perturbation_shifts_exactly_one_subband():
    data = _inputs()
    shifted = cs.perturbed_subbands(data["subbands"], "e2", 10.0)
    assert np.allclose(shifted["e2"] - data["subbands"]["e2"], 0.010)
    for key in ("e1", "hh1", "hh2"):
        assert np.array_equal(shifted[key], data["subbands"][key])
    # the source dict must not be mutated
    assert np.allclose(data["subbands"]["e2"][0], 3.0610)


def test_energy_perturbation_rejects_unknown_state():
    with pytest.raises(ValueError, match="state must be one of"):
        cs.perturbed_subbands(_inputs()["subbands"], "lh1", 5.0)


def test_only_energy_differences_enter_equation_2():
    """A common shift of all four subbands must leave the spectrum untouched."""
    data = _inputs()
    bands = data["subbands"]
    for state in cs.STATE_KEYS:
        bands = cs.perturbed_subbands(bands, state, 25.0)
    shifted = _build({**data, "electron_energies_eV": np.vstack([bands["e1"], bands["e2"]]),
                      "hole_energies_eV": np.vstack([bands["hh1"], bands["hh2"]])})
    assert np.allclose(shifted.chi2, _build(data).chi2, rtol=1e-12, atol=0)


def test_shifting_e2_and_hh2_oppositely_moves_only_the_shared_transition():
    """+d on e2 and -d on hh2 both raise DeltaE_22, but touch different partners."""
    data = _inputs()
    up = cs.perturbed_subbands(data["subbands"], "e2", 10.0)
    down = cs.perturbed_subbands(data["subbands"], "hh2", -10.0)
    a = _build({**data, "electron_energies_eV": np.vstack([up["e1"], up["e2"]]),
                "hole_energies_eV": np.vstack([up["hh1"], up["hh2"]])})
    b = _build({**data, "electron_energies_eV": np.vstack([down["e1"], down["e2"]]),
                "hole_energies_eV": np.vstack([down["hh1"], down["hh2"]])})
    assert np.allclose(a.transition_eV[1, 1], b.transition_eV[1, 1], rtol=1e-12, atol=0)
    assert not np.allclose(a.transition_eV[1, 0], b.transition_eV[1, 0])
    assert not np.allclose(a.chi2, b.chi2)


# --- feature and diagnostic bookkeeping ------------------------------------

def test_window_edge_hits_are_flagged_as_non_extrema():
    x = np.linspace(500.0, 1700.0, 1201)
    rising = np.linspace(1.0, 5.0, len(x)).astype(complex)   # monotone: no interior peak
    matched = cs.match_features(x, rising, SPECS)
    assert matched["P1"]["at_window_edge"] == 1.0
    bump = (np.exp(-((x - 760.0) / 20.0) ** 2) + 0.01).astype(complex)
    matched = cs.match_features(x, bump, SPECS)
    assert matched["P2"]["at_window_edge"] == 0.0
    assert matched["P2"]["wavelength_nm"] == pytest.approx(760.0, abs=2.0)


def test_normalized_feature_amplitudes_are_invariant_to_global_scaling():
    x = np.linspace(500.0, 1700.0, 1201)
    chi = (np.exp(-((x - 760.0) / 20.0) ** 2) + 0.01).astype(complex)
    a = cs.match_features(x, chi, SPECS)
    b = cs.match_features(x, 137.0 * chi, SPECS)
    for name in a:
        assert a[name]["normalized_amplitude"] == pytest.approx(b[name]["normalized_amplitude"])
        assert a[name]["wavelength_nm"] == pytest.approx(b[name]["wavelength_nm"])


def test_band_edges_label_k0_as_physical_and_kmax_as_artifact():
    mirror = _build(_inputs())
    edges = cs.band_edges_of_transitions(mirror)
    assert len(edges) == 16
    for row in edges:
        expected = "physical" if row["edge"] == "k=0" else "artifact"
        assert expected in row["origin"]
    # a one-photon edge is always at half the wavelength of its two-photon partner
    for row in edges:
        if row["order"] != "one-photon":
            continue
        partner = next(other for other in edges if other["order"] == "two-photon"
                       and other["transition"] == row["transition"] and other["edge"] == row["edge"])
        assert partner["wavelength_nm"] == pytest.approx(2.0 * row["wavelength_nm"])


def test_reachability_rejects_energies_below_as_well_as_above_the_band():
    """A required energy under the k=0 transition is as unreachable as one over the limit."""
    mirror = _build(_inputs())
    lo = float(np.min(mirror.transition_eV))
    hi = float(np.max(mirror.transition_eV))
    edges = {"barrier_conduction_edge_eV": 3.40, "barrier_gap_eV": 2.10}
    inside = validated.HC_EV_NM / (0.5 * (lo + hi))
    too_long = 4.0 * validated.HC_EV_NM / lo        # both 1- and 2-photon needs fall below lo
    specs = [{"name": "inside", "type": "peak", "wavelength_nm": inside, "window_nm": [inside - 5, inside + 5]},
             {"name": "below", "type": "peak", "wavelength_nm": too_long, "window_nm": [too_long - 5, too_long + 5]}]
    rows = {str(r["Feature"]): r for r in cs.resonance_reachability(mirror, specs, 0.1, edges)}
    assert rows["inside"]["reachable"] == "yes"
    assert rows["below"]["reachable"] == "no"
    assert str(rows["below"]["reachable_with_bound_states_at_any_k"]).startswith("no")


def test_cutoff_artifact_test_separates_moving_from_stationary_peaks():
    x = np.linspace(500.0, 1700.0, 1201)
    fractions = {"a": 0.05, "b": 0.075, "c": 0.10, "d": 0.125}
    moving = {"a": 1500.0, "b": 1430.0, "c": 1375.0, "d": 1320.0}
    spectra = {}
    for name, centre in moving.items():
        spectra[name] = (np.exp(-((x - 760.0) / 12.0) ** 2)
                         + np.exp(-((x - centre) / 12.0) ** 2)).astype(complex)
    # transition energies chosen so 2hc/E lands on the moving peak
    transition_max = {name: 2.0 * validated.HC_EV_NM / moving[name] for name in moving}
    rows = {round(float(r["peak_wavelength_at_largest_kmax_nm"])): r
            for r in cs.cutoff_artifact_test(x, spectra, fractions, transition_max)}
    stationary = next(r for w, r in rows.items() if abs(w - 760) < 15)
    marching = next(r for w, r in rows.items() if abs(w - 1320) < 15)
    assert "STABLE" in str(stationary["classification"])
    assert "TRACKS_CUTOFF" in str(marching["classification"])
    assert str(marching["best_match_to_cutoff_resonance"]) == "two-photon at kmax"
    assert float(marching["mean_abs_error_vs_two_photon_at_kmax_nm"]) < 10.0


def test_numerator_phase_is_reported_as_not_a_free_parameter_for_real_inputs():
    report = cs.numerator_phase_content(_build(_inputs()))
    assert report["numerator_phase_is_a_free_parameter"] is False
    assert report["max_abs_imaginary_numerator"] == 0.0


# --- no fabrication, no writes to Demo 23 ----------------------------------

def test_band_edges_reader_refuses_to_invent_missing_professional_data(tmp_path):
    with pytest.raises(FileNotFoundError, match="bandedges.dat"):
        cs.band_edges(tmp_path)


def test_causal_module_never_invokes_a_solver():
    """The module may discuss nextnano, but must never be able to launch it."""
    source = (DEMO_DIR / "causal_sensitivity.py").read_text(encoding="utf-8")
    code = chr(10).join(line for line in source.splitlines() if not line.strip().startswith("#"))
    for forbidden in ("subprocess", "os.system", "Popen", "nextnanopy", "run_deck", "execute("):
        assert forbidden not in code, f"{forbidden} must not appear in executable code"


def test_demo23_sources_are_not_modified_by_the_causal_stage():
    """Demo 24N is read-only with respect to Demo 23."""
    watched = sorted((DEMO23).glob("*.py")) + sorted((DEMO23 / "configs").glob("*.yaml"))
    assert watched, "expected Demo 23 sources to exist"
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    data = _inputs()
    _build(data, keep_k_integrand=True)
    cs.energy_sensitivity(
        data["subbands"], data["k_per_nm"], data["wavelengths_nm"],
        type("F", (), {"overlap_eh": data["overlap_eh"], "z_e_nm": data["z_e_nm"],
                       "z_hh_nm": data["z_h_nm"]})(),
        data["settings"], np.abs(_build(data).chi2), SPECS, [-5.0, 0.0, 5.0])
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    assert before == after
