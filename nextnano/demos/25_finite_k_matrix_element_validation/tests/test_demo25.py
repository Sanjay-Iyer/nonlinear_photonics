"""Demo 25 tests.

These validate the machinery and the fail-loud contracts. They deliberately do
not assert any physics conclusion, because the Professional data that would
settle it does not exist until the pilot and production runs have happened.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest


DEMO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_DIR.parents[2]
DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
DEMO23 = DEMO_DIR.parent / "23_k_resolved_dispersion_validation"
DEMO24 = DEMO_DIR.parent / "24_equation2_spectral_shape_audit"
# Only Demo 25's own directory goes on the path here. config25 and
# finite_k_matrices add what they need, and they deliberately append Demo 24
# rather than inserting it, so Demo 23's generically named modules are not
# shadowed when several demo suites run in one interpreter.
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

import config25  # noqa: E402
import deck25  # noqa: E402
import finite_k_matrices as fkm  # noqa: E402
import kp8_finite_k_io as kio  # noqa: E402
import pilot_audit  # noqa: E402
import progress as progress_mod  # noqa: E402
import state_tracking25 as tracking  # noqa: E402
import transition_search as tsearch  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return config25.load_config()


# --- configuration and inheritance -----------------------------------------

def test_structure_blocks_are_inherited_not_restated(cfg):
    raw = DEMO_DIR / "demo25_config.yaml"
    text = raw.read_text(encoding="utf-8")
    for block in ("geometry:", "materials:", "mesh:"):
        assert not any(line.startswith(block) for line in text.splitlines()), (
            f"{block} must be inherited from Demo 23, not restated in demo25_config.yaml")
    cfg23 = cfg["_demo23_config"]
    for block in cfg["inherit"]["frozen_blocks"]:
        assert cfg[block] == cfg23[block]


def test_demo25_never_reduces_the_state_count(cfg):
    cfg23 = cfg["_demo23_config"]
    for key in ("number_of_electron_states", "number_of_hole_states", "output_state_count"):
        assert int(cfg["kp8"][key]) >= int(cfg23["kp8"][key])


def test_extended_states_actually_extend(cfg):
    cfg23 = cfg["_demo23_config"]
    assert int(cfg["kp8"]["output_state_count"]) > int(cfg23["kp8"]["output_state_count"]), (
        "the ~2.296 eV search needs strictly more states than Demo 23 solved")


# --- decks ------------------------------------------------------------------

def test_pilot_covers_the_candidate_explanations(cfg):
    specs = deck25.pilot_specs(cfg)
    assert any(s.k_integration for s in specs)
    assert any(not s.k_integration for s in specs), "a Demo 23-style control is required"
    assert any(s.k_point_subdirectories for s in specs)
    assert any(not s.no_density for s in specs), "the no_density hypothesis must be tested"


def test_pilot_decks_keep_the_demo23_structure(cfg):
    import deck23  # noqa: PLC0415

    cfg23 = cfg["_demo23_config"]
    reference = deck23.render(cfg23, next(s for s in deck23.deck_specs(cfg23) if s.role == "production"))
    for spec in deck25.pilot_specs(cfg):
        deck25.assert_structure_matches_demo23(cfg, deck25.render(cfg, spec), reference)


def test_structure_drift_is_detected(cfg):
    import deck23  # noqa: PLC0415

    cfg23 = cfg["_demo23_config"]
    reference = deck23.render(cfg23, next(s for s in deck23.deck_specs(cfg23) if s.role == "production"))
    tampered = reference.replace("temperature = 300", "temperature = 77")
    with pytest.raises(config25.Demo25Error, match="drifted"):
        deck25.assert_structure_matches_demo23(cfg, tampered, reference)


def test_k_integration_block_replaces_the_disabled_one(cfg):
    spec = next(s for s in deck25.pilot_specs(cfg) if s.k_integration)
    text = deck25.render(cfg, spec)
    assert "k_integration{" in text
    assert "k_integration_disabled" not in text
    assert "all_k_points = yes" in text


def test_control_variant_reproduces_the_demo23_k_block(cfg):
    spec = next(s for s in deck25.pilot_specs(cfg) if not s.k_integration)
    text = deck25.render(cfg, spec)
    assert "k_integration_disabled{}" in text


def test_production_spec_uses_the_pilot_discovered_settings(cfg):
    spec = deck25.production_spec(cfg, num_points=51, settings={
        "k_integration": True, "no_density": False,
        "k_point_subdirectories": True, "symmetry": "C4", "keep_dispersion_path": True})
    assert spec.num_points == 51 and spec.symmetry == "C4" and not spec.no_density
    text = deck25.render(cfg, spec)
    assert "symmetry = C4" in text and "k_point_subdirectories = yes" in text
    assert "no_density" not in text.split("quantum{")[1].split("kp_8band")[0]


# --- pilot gate -------------------------------------------------------------

def _summary(**kwargs):
    base = {"variant": "v", "k_points_with_evidence": 1, "k_points_usable": 1,
            "finite_k_state_output": False, "k_vectors_found": True,
            "total_files": 10, "total_bytes": 1000, "seconds": 60.0}
    base.update(kwargs)
    return base


def test_gate_fails_when_only_k0_is_present():
    verdict = pilot_audit.gate([_summary()])
    assert verdict["status"] == "FAIL"
    assert "k00000" in verdict["reason"]


def test_gate_fails_without_k_vectors():
    verdict = pilot_audit.gate([_summary(k_points_usable=5, finite_k_state_output=True,
                                         k_vectors_found=False)])
    assert verdict["status"] == "FAIL"
    assert "k-vector" in verdict["reason"]


def test_gate_passes_and_picks_the_richest_variant():
    verdict = pilot_audit.gate([
        _summary(variant="a", k_points_usable=1),
        _summary(variant="b", k_points_usable=5, finite_k_state_output=True),
        _summary(variant="c", k_points_usable=3, finite_k_state_output=True)])
    assert verdict["status"] == "PASS" and verdict["recommended_variant"] == "b"


def test_production_sizing_respects_time_and_disk_budgets():
    cost = pilot_audit.cost_model(_summary(k_points_usable=4, total_bytes=4_000_000_000), 400.0)
    assert cost["seconds_per_k"] == pytest.approx(100.0)
    sizing = pilot_audit.recommend_k_points(cost, requested=301, max_hours=2.0, max_gb=10.0)
    assert not sizing["within_budget"]
    assert sizing["recommended_k_points"] < 301
    assert "binding budget" in sizing["reason"]


def test_production_sizing_accepts_a_cheap_run():
    cost = pilot_audit.cost_model(_summary(k_points_usable=4, total_bytes=4_000_000), 20.0)
    sizing = pilot_audit.recommend_k_points(cost, requested=301, max_hours=12.0, max_gb=60.0)
    assert sizing["within_budget"] and sizing["recommended_k_points"] == 301


def test_audit_case_refuses_a_missing_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        pilot_audit.audit_case(tmp_path / "nope", "v")


# --- finite-k IO and matrix elements ---------------------------------------

def _states(n_states=4, n_z=101, k_index=0):
    z = np.linspace(0.0, 20.0, n_z)
    spinor = np.zeros((n_states, 8, n_z), dtype=complex)
    for s in range(n_states):
        mode = np.sqrt(2.0 / 20.0) * np.sin((s + 1) * np.pi * z / 20.0)
        component = 0 if s < 2 else 2          # first two CB-like, rest HH-like
        spinor[s, component, :] = mode
    energies = np.array([2.95, 3.09, 1.44, 1.41])[:n_states]
    return kio.KPointStates(k_index, None, z, energies, spinor, kio.COMPONENT_TAGS)


def test_spinor_states_are_normalized():
    assert np.allclose(kio.normalization(_states()), 1.0, atol=1e-3)


def test_overlap_is_conjugate_symmetric():
    states = _states()
    for a in range(states.n_states):
        for b in range(states.n_states):
            assert kio.overlap(states, a, b) == pytest.approx(np.conj(kio.overlap(states, b, a)), abs=1e-9)


def test_position_matrix_is_hermitian():
    states = _states()
    z = np.array([[kio.position_matrix_element(states, a, b) for b in range(states.n_states)]
                  for a in range(states.n_states)])
    assert kio.hermiticity_error(z) < 1e-9


def test_band_fractions_sum_to_one():
    assert np.allclose(_states().band_fractions().sum(axis=1), 1.0)


def test_missing_finite_k_data_raises_instead_of_falling_back(tmp_path):
    with pytest.raises(pilot_audit.FiniteKDataUnavailable, match="does not substitute"):
        kio.load_k_point(tmp_path, 7)


def _matrices(nk=5, vary=True):
    k = np.linspace(0.0, 0.5, nk)
    o = np.zeros((2, 2, nk), dtype=complex)
    ze = np.zeros((2, 2, nk), dtype=complex)
    zh = np.zeros((2, 2, nk), dtype=complex)
    scale = (1.0 - 0.4 * k) if vary else np.ones(nk)
    o[0, 0], o[0, 1], o[1, 0], o[1, 1] = 0.98 * scale, 0.015 * scale, -0.083 * scale, 0.383 * scale
    ze[0, 0], ze[0, 1], ze[1, 0], ze[1, 1] = 12.7 * scale, 1.02 * scale, 1.02 * scale, 18.7 * scale
    zh[0, 0], zh[0, 1], zh[1, 0], zh[1, 1] = 12.65 * scale, 1.43 * scale, 1.43 * scale, 12.73 * scale
    return fkm.FiniteKMatrices(k, o, ze, zh, np.ones((2, nk)), np.ones((2, nk)))


def test_pathway_numerators_match_the_production_expressions():
    matrices = _matrices(vary=False)
    numerators = fkm.pathway_numerators(matrices)
    assert numerators.shape == (16, matrices.k_per_nm.size)
    o, ze, zh = matrices.at_zero()
    for item in fkm.PATHWAYS:
        m, n, l = item.m - 1, item.n - 1, item.ell - 1
        expected = (o[n, m] * ze[n, l] * o[l, m] if item.side == "electron_side"
                    else -o[n, m] * zh[m, l] * o[n, l])
        assert numerators[item.index, 0] == pytest.approx(expected)


def test_ratio_is_unity_when_matrices_do_not_vary():
    rows = fkm.numerator_ratios(_matrices(vary=False))
    for row in rows:
        if not row["negligible_at_k0"]:
            assert row["max_fractional_deviation"] == pytest.approx(0.0, abs=1e-12)
            assert not row["varies_more_than_5pct"]
            assert not row["sign_change_vs_k"]


def test_ratio_flags_real_variation():
    rows = fkm.numerator_ratios(_matrices(vary=True))
    assert any(row["varies_more_than_10pct"] for row in rows)


def test_finite_k_engine_reduces_to_the_frozen_engine_when_m_is_constant():
    """A constant M(k) must reproduce the M(k)=M(0) spectrum exactly."""
    import physics23  # noqa: PLC0415

    cfg23 = config25.load_demo23_config()
    settings = physics23.settings_from_config(cfg23)
    matrices = _matrices(nk=41, vary=False)
    k = matrices.k_per_nm
    lam = np.linspace(700.0, 1600.0, 121)
    e = np.vstack([2.94 + 0.35 * k ** 2, 3.06 + 0.30 * k ** 2])
    h = np.vstack([1.448 - 0.17 * k ** 2, 1.413 - 0.15 * k ** 2])
    a = fkm.spectrum_with_finite_k(lam, k, e, h, matrices, settings=settings, broadening_meV=5.0)
    b = fkm.spectrum_with_frozen_matrices(lam, k, e, h, matrices, settings=settings, broadening_meV=5.0)
    assert np.allclose(a.chi2, b.chi2, rtol=0, atol=1e-12)


def test_varying_matrices_change_the_spectrum():
    import physics23  # noqa: PLC0415

    settings = physics23.settings_from_config(config25.load_demo23_config())
    matrices = _matrices(nk=41, vary=True)
    k = matrices.k_per_nm
    lam = np.linspace(700.0, 1600.0, 121)
    e = np.vstack([2.94 + 0.35 * k ** 2, 3.06 + 0.30 * k ** 2])
    h = np.vstack([1.448 - 0.17 * k ** 2, 1.413 - 0.15 * k ** 2])
    a = fkm.spectrum_with_finite_k(lam, k, e, h, matrices, settings=settings, broadening_meV=5.0)
    b = fkm.spectrum_with_frozen_matrices(lam, k, e, h, matrices, settings=settings, broadening_meV=5.0)
    assert not np.allclose(a.chi2, b.chi2)


def test_interpolation_refuses_to_extrapolate():
    matrices = _matrices(nk=5)
    with pytest.raises(ValueError, match="refusing to extrapolate"):
        fkm.interpolate_onto(matrices, np.linspace(0.0, 0.9, 11))


def test_interpolation_preserves_values_on_shared_nodes():
    matrices = _matrices(nk=5)
    dense = fkm.interpolate_onto(matrices, np.linspace(0.0, 0.5, 9))
    assert np.allclose(dense.overlap[:, :, 0], matrices.overlap[:, :, 0])
    assert np.allclose(dense.overlap[:, :, -1], matrices.overlap[:, :, -1])


# --- state tracking ---------------------------------------------------------

def test_tracking_follows_character_not_energy_order():
    """Two states swap energy order; labels must follow the wavefunction."""
    a = _states(n_states=2)
    swapped = kio.KPointStates(1, None, a.z_nm, np.array([3.09, 2.95]),
                               a.spinor[::-1].copy(), a.component_tags)
    labels = tracking.track([a, swapped], barrier_conduction_edge_eV=3.32,
                            barrier_valence_edge_eV=1.18)
    first = {s.label: s.state_index for s in labels[0].values()}
    second = {s.label: s.state_index for s in labels[1].values()}
    assert first["e1"] != second["e1"], "the label should follow the swapped wavefunction"


def test_unconfined_states_are_flagged():
    states = _states(n_states=2)
    high = kio.KPointStates(0, None, states.z_nm, np.array([3.90, 4.10]),
                            states.spinor.copy(), states.component_tags)
    seeded = tracking.seed_labels(high, barrier_conduction_edge_eV=3.3244,
                                  barrier_valence_edge_eV=1.1795)
    assert all(not s.confined for s in seeded.values())
    events = tracking.detect_events([seeded])
    assert any(e["event"] == "loss of confinement" for e in events)


def test_tracking_rows_expose_character_and_confidence():
    states = _states()
    rows = tracking.rows(tracking.track([states], barrier_conduction_edge_eV=3.32,
                                        barrier_valence_edge_eV=1.18), [0.0])
    for key in ("CB fraction", "HH fraction", "LH fraction", "SO fraction",
                "tracking_score", "assignment_margin", "confined"):
        assert key in rows[0]


# --- transition search ------------------------------------------------------

def _entry(delta, *, bound=True, overlap=0.9, strength=1.0):
    return {"k_index": 0, "k_per_nm": 0.0, "states": [
        {"label": "e1", "energy_eV": 1.4 + delta, "dominant_band": "CB", "confined": bound,
         "fractions": {"CB": 0.99}, "overlap": {"hh1": overlap},
         "oscillator_strength": {"hh1": strength}},
        {"label": "hh1", "energy_eV": 1.4, "dominant_band": "HH", "confined": True,
         "fractions": {"HH": 0.98, "LH": 0.01}}]}


def test_search_finds_a_transition_within_tolerance():
    rows = tsearch.search([_entry(2.30)], target_eV=2.296, tolerance_eV=0.05,
                          barrier_conduction_edge_eV=3.3244, barrier_valence_edge_eV=1.1795)
    assert len(rows) == 1
    assert rows[0]["one_photon_nm"] == pytest.approx(tsearch.HC_EV_NM / 2.30)
    assert rows[0]["two_photon_nm"] == pytest.approx(2 * tsearch.HC_EV_NM / 2.30)


def test_search_ignores_transitions_outside_tolerance():
    assert tsearch.search([_entry(2.10)], target_eV=2.296, tolerance_eV=0.05,
                          barrier_conduction_edge_eV=3.3244,
                          barrier_valence_edge_eV=1.1795) == []


def test_energy_match_without_optical_weight_does_not_explain_p1_p3():
    rows = tsearch.search([_entry(2.30, overlap=1e-6, strength=1e-6)], target_eV=2.296,
                          tolerance_eV=0.05, barrier_conduction_edge_eV=3.3244,
                          barrier_valence_edge_eV=1.1795)
    scored = tsearch.score_optical_relevance(rows, min_overlap_fraction=0.05,
                                             min_oscillator_fraction=0.01,
                                             reference_overlap=1.0, reference_oscillator=1.0)
    assert scored[0]["verdict"].startswith("ENERGY MATCH ONLY")
    verdict = tsearch.conclusion(scored, target_eV=2.296, ceiling_eV=2.1449)
    assert not verdict["found"]


def test_unbound_candidate_is_not_a_physical_explanation():
    rows = tsearch.search([_entry(2.30, bound=False)], target_eV=2.296, tolerance_eV=0.05,
                          barrier_conduction_edge_eV=3.3244, barrier_valence_edge_eV=1.1795)
    scored = tsearch.score_optical_relevance(rows, min_overlap_fraction=0.05,
                                             min_oscillator_fraction=0.01,
                                             reference_overlap=1.0, reference_oscillator=1.0)
    assert "UNBOUND" in scored[0]["verdict"]
    assert tsearch.conclusion(scored, target_eV=2.296, ceiling_eV=2.1449)["class"] == "unbound_only"


def test_bound_optically_strong_candidate_is_accepted():
    rows = tsearch.search([_entry(2.30)], target_eV=2.296, tolerance_eV=0.05,
                          barrier_conduction_edge_eV=3.3244, barrier_valence_edge_eV=1.1795)
    scored = tsearch.score_optical_relevance(rows, min_overlap_fraction=0.05,
                                             min_oscillator_fraction=0.01,
                                             reference_overlap=1.0, reference_oscillator=1.0)
    verdict = tsearch.conclusion(scored, target_eV=2.296, ceiling_eV=2.1449)
    assert verdict["found"] and verdict["class"] == "bound_and_optically_relevant"


def test_bound_bound_ceiling_is_the_barrier_gap():
    assert tsearch.bound_bound_ceiling(3.3244, 1.1795) == pytest.approx(2.1449, abs=1e-4)


def test_ceiling_exceedance_is_flagged():
    rows = tsearch.search([_entry(2.30)], target_eV=2.296, tolerance_eV=0.05,
                          barrier_conduction_edge_eV=3.3244, barrier_valence_edge_eV=1.1795)
    assert rows[0]["exceeds_bound_bound_ceiling"]


# --- progress tracker -------------------------------------------------------

def test_tracker_persists_and_reloads(tmp_path, cfg):
    path = tmp_path / "progress.json"
    track = progress_mod.Tracker(path, progress_mod.default_plan(cfg))
    track.start("audit")
    track.finish("audit")
    assert progress_mod.Tracker(path).stage("audit").status == progress_mod.DONE


def test_gate_failure_blocks_later_stages(tmp_path, cfg):
    path = tmp_path / "progress.json"
    track = progress_mod.Tracker(path, progress_mod.default_plan(cfg))
    track.finish("pilot_audit", progress_mod.FAILED, note="no finite-k output")
    assert track.stage("production_run").status == progress_mod.BLOCKED
    assert track.stage("chi2").status == progress_mod.BLOCKED


def test_fraction_is_weighted_and_monotonic(tmp_path, cfg):
    path = tmp_path / "progress.json"
    track = progress_mod.Tracker(path, progress_mod.default_plan(cfg))
    assert track.fraction == 0.0
    track.finish("audit")
    first = track.fraction
    track.finish("decks_pilot")
    assert 0.0 < first < track.fraction < 1.0


def test_render_contains_every_stage(tmp_path, cfg):
    track = progress_mod.Tracker(tmp_path / "p.json", progress_mod.default_plan(cfg))
    text = track.render(color=False)
    for stage in track.stages:
        assert stage.title in text


def test_unmeasured_eta_is_reported_as_unknown():
    assert progress_mod.humanize(None) == "unknown"


# --- fail-loud contracts ----------------------------------------------------

def test_no_module_substitutes_frozen_matrices_for_finite_k():
    """Demo 25 must never quietly fall back to M(k)=M(0) in the finite-k path."""
    source = (DEMO_DIR / "finite_k_matrices.py").read_text(encoding="utf-8")
    assert "spectrum_with_frozen_matrices" in source
    body = source.split("def spectrum_with_finite_k")[1].split("def ")[0]
    assert "at_zero" not in body, "the finite-k spectrum must not read the k=0 matrices"


def test_production_is_refused_without_a_passing_gate(tmp_path, monkeypatch, cfg):
    import run_demo25  # noqa: PLC0415

    monkeypatch.setattr(run_demo25, "outputs_root", lambda _cfg: tmp_path)
    (tmp_path / "PILOT_GATE.json").write_text(
        json.dumps({"status": "FAIL", "reason": "only k00000"}), encoding="utf-8")
    track = progress_mod.Tracker(tmp_path / "p.json", progress_mod.default_plan(cfg))
    with pytest.raises(config25.Demo25Error, match="pilot gate is FAIL"):
        run_demo25.stage_production(cfg, track, {"exe": "x", "database": "y", "license": "z",
                                                 "threads": 1})


def test_free_build_is_rejected_for_physics():
    import run_demo25  # noqa: PLC0415

    with pytest.raises(config25.Demo25Error, match="Free build"):
        run_demo25.assert_professional({
            "exe": Path(r"C:/Program Files/nextnano/2026_07_03/nextnano++/bin 32bit/"
                        r"nextnano++_Microsoft_32bit_free.exe"),
            "database": Path("db"), "license": Path("lic"), "threads": 1})


def test_demo23_and_demo24_sources_are_untouched():
    watched = sorted(DEMO23.glob("*.py")) + sorted(DEMO24.glob("*.py")) + \
        sorted(DEMO23.glob("*.yaml")) + sorted(DEMO24.glob("*.yaml"))
    assert watched
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    config25.load_config()
    deck25.pilot_specs(config25.load_config())
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    assert before == after


def test_no_demo25_module_launches_a_solver_outside_the_runner():
    for name in ("config25.py", "deck25.py", "pilot_audit.py", "kp8_finite_k_io.py",
                 "state_tracking25.py", "transition_search.py", "finite_k_matrices.py",
                 "progress.py"):
        source = (DEMO_DIR / name).read_text(encoding="utf-8")
        code = "\n".join(line for line in source.splitlines()
                         if not line.strip().startswith("#"))
        for forbidden in ("subprocess", "Popen", "os.system", "execute_real"):
            assert forbidden not in code, f"{name} must not be able to launch the solver"
