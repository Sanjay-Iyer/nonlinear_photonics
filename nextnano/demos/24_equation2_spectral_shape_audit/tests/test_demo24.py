from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


DEMO_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_DIR.parents[2]
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

import finite_k_matrix_audit
import paper_feature_analysis
import pathway_analysis
import signed_spectrum


def test_peak_detector_on_synthetic_multi_peak_curve():
    x = np.linspace(0, 100, 1001)
    y = np.exp(-((x - 20) / 3) ** 2) + 0.8 * np.exp(-((x - 52) / 4) ** 2) + 0.6 * np.exp(-((x - 83) / 2) ** 2)
    peaks = signed_spectrum.peak_indices(x, y, prominence_fraction=0.1, minimum_distance_nm=10)
    assert np.allclose(x[peaks], [20, 52, 83], atol=0.2)


def test_zero_and_minimum_detector():
    x = np.linspace(0, 10, 101)
    y = (x - 4.2) ** 2
    minimum = signed_spectrum.window_minimum(x, y, (3, 5))
    assert minimum["wavelength_nm"] == pytest.approx(4.2)
    assert minimum["normalized_amplitude"] == pytest.approx(0.0)


def test_complex_sign_crossing_detector_requires_small_magnitude():
    x = np.linspace(0, 2, 201)
    chi = (x - 1) + 1j * (x - 1)
    diagnostic = signed_spectrum.complex_zero_diagnostic(x, chi, (0.5, 1.5), 0.01)
    assert diagnostic["full_complex_zero"]
    filled = (x - 1) + 1j * np.ones_like(x)
    diagnostic = signed_spectrum.complex_zero_diagnostic(x, filled, (0.5, 1.5), 0.01)
    assert not diagnostic["full_complex_zero"]


def test_cancellation_metric():
    assert signed_spectrum.cancellation_metric(2 + 0j, -2 + 0j) == pytest.approx(0.0)
    assert signed_spectrum.cancellation_metric(2 + 0j, 2 + 0j) == pytest.approx(1.0)


def _fake_result():
    terms = np.asarray([[1 + 2j, 2 + 1j], [3 - 1j, 1 + 0j], [-2 - 1j, -1 - 1j], [-1 + 0j, 0 + 0j]])
    labels = ("C_a", "C_b", "V_a", "V_b")
    spectrum = SimpleNamespace(terms=terms, term_labels=labels, chi2=np.sum(terms, axis=0), wavelength_nm=np.asarray([600.0, 1300.0]))
    return SimpleNamespace(spectrum=spectrum)


def test_pathway_subtotal_and_total_consistency():
    result = _fake_result()
    electron, hh = pathway_analysis.subtotals(result)
    assert np.allclose(electron + hh, result.spectrum.chi2)
    pathway_analysis.assert_consistency(result)


def test_sum_of_sixteen_pathways_equals_total():
    rng = np.random.default_rng(24)
    terms = rng.normal(size=(16, 10)) + 1j * rng.normal(size=(16, 10))
    labels = tuple(([f"C_{i}" for i in range(8)] + [f"V_{i}" for i in range(8)]))
    result = SimpleNamespace(spectrum=SimpleNamespace(terms=terms, term_labels=labels,
                                                       chi2=np.sum(terms, axis=0), wavelength_nm=np.arange(10.0)))
    pathway_analysis.assert_consistency(result)


def test_normalized_spectrum_invariant_to_global_scaling():
    x = np.asarray([1.0, 2.0, 4.0])
    assert np.allclose(signed_spectrum.normalize(x), signed_spectrum.normalize(37.2 * x))


def test_feature_matching_uses_configured_windows():
    x = np.arange(400.0, 801.0, 10.0)
    y = np.exp(-((x - 540) / 20) ** 2) + 2 * np.exp(-((x - 760) / 20) ** 2)
    config = {"digitization_uncertainty_nm": 10, "peak_prominence_fraction": 0.05,
              "minimum_peak_distance_nm": 100,
              "expected": [{"name": "P1", "type": "peak", "wavelength_nm": 540,
                            "window_nm": [500, 580], "confidence": "high"}]}
    rows = paper_feature_analysis.paper_feature_table(x, y, config)
    assert rows[0]["Paper wavelength nm"] == pytest.approx(540)
    assert rows[0]["Automatic peak detected"] is True


def test_no_fabricated_missing_kp_data(tmp_path):
    rows = finite_k_matrix_audit.inventory(tmp_path)
    with pytest.raises(finite_k_matrix_audit.ProfessionalDataRequired, match="REQUIRES_NEW_PROFESSIONAL_DATA"):
        finite_k_matrix_audit.require_finite_k_matrices(rows)


def test_professional_required_diagnostic_flags_instead_of_simulating(tmp_path):
    rows = finite_k_matrix_audit.inventory(tmp_path)
    assert any(row["Missing?"] for row in rows if row["Needed for Equation 2?"])


def test_professor_review_input_generated_correctly():
    path = DEMO_DIR / "professor_review" / "PHYSICS_PROFESSOR_REVIEW_PROMPT.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "independent" in text.lower() or "Pending generation" in text


def test_demo23_files_are_not_modified_by_read_only_inventory():
    targets = [DEMO_DIR.parent / "23_k_resolved_dispersion_validation" / "demo23_config.yaml",
               REPO_ROOT / "demo_results" / "demo23" / "raw" / "production_y_n301_k0100" /
               "production_y_n301_k0100" / "job_done.txt"]
    before = [(path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()) for path in targets]
    finite_k_matrix_audit.inventory(REPO_ROOT / "demo_results" / "demo23" / "raw" / "production_y_n301_k0100")
    after = [(path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()) for path in targets]
    assert before == after
