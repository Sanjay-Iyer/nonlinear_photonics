"""Demo 20 local tests. Every one runs without a licensed nextnano++.

Three groups:

* **Tests 1-7** are the checks the Demo 20 brief asks for by number.
* **Equivalence tests** prove Demo 20 is a reorganization of Demo 19 rather than
  a new model: identical cases, identical composition profiles, byte-identical
  decks, and exact reproduction of Demo 19's own recorded chi2 value.
* **Normalization tests** pin down what the (2*pi)^2 factor actually is,
  including the independent Cartesian cross-check of the k measure.

Run with:
    python -m pytest nextnano/demos/20_quantum_well_interface_grading_scaled/tests -q
or standalone:
    python nextnano/demos/20_quantum_well_interface_grading_scaled/tests/test_demo20.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
import pytest

DEMO_DIR = Path(__file__).resolve().parents[1]
DEMOS_DIR = DEMO_DIR.parent
DEMO19_DIR = DEMOS_DIR / "19_quantum_well_interface_grading_showcase"
for _path in (DEMO_DIR,):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import config20                       # noqa: E402
import s01_cases as cases             # noqa: E402
import s02_grading as grading         # noqa: E402
import s03_inputs as inputs           # noqa: E402
import s05_extract as extract         # noqa: E402
import s06_chi2 as chi2mod            # noqa: E402
import s07_analysis as analysis       # noqa: E402
import s08_qc as qc                   # noqa: E402

TWO_PI_SQUARED = 39.47841760435743


@pytest.fixture(scope="module")
def cfg():
    return config20.load()


@pytest.fixture(scope="module")
def states(cfg):
    """Real licensed solver states, read from the Demo 19 results table."""

    path = config20.master_table_path(cfg)
    if not path.is_file():
        pytest.skip(f"no source results table at {path}")
    extracted = extract.from_master_table(path)
    usable = {k: v for k, v in extracted.items() if v.has_states}
    if not usable:
        pytest.skip(f"{path} contains no solver states (pending run)")
    return usable


@pytest.fixture(scope="module")
def settings(cfg):
    return chi2mod.settings_from_config(cfg)


# =============================================================================
# Test 1 - the constant
# =============================================================================


def test_1_two_pi_squared_value():
    assert chi2mod.two_pi_squared() == pytest.approx(TWO_PI_SQUARED, rel=0, abs=1e-13)
    # And the identity the brief spells out: (2 pi)^2 = 4 pi^2.
    assert chi2mod.two_pi_squared() == pytest.approx(4.0 * math.pi ** 2, abs=1e-13)


def test_1_config_factor_matches_computed_value(cfg):
    assert float(cfg["chi2"]["kspace_scaling_factor"]) == pytest.approx(
        chi2mod.two_pi_squared(), abs=1e-9
    )


# =============================================================================
# Test 2 - scaling disabled reproduces the raw value
# =============================================================================


def test_2_reported_equals_raw_when_disabled(cfg, states, settings):
    case = next(iter(states.values()))
    grid = chi2mod.wavelength_grid(cfg)
    pair = chi2mod.chi2_both_conventions(case.states, grid, settings,
                                         scaling_enabled=False)
    assert pair.reported is pair.raw
    np.testing.assert_array_equal(pair.reported.chi2, pair.raw.chi2)


# =============================================================================
# Test 3 - scaling enabled multiplies by exactly (2*pi)^2
# =============================================================================


def test_3_reported_equals_raw_times_factor_when_enabled(cfg, states, settings):
    case = next(iter(states.values()))
    grid = chi2mod.wavelength_grid(cfg)
    pair = chi2mod.chi2_both_conventions(case.states, grid, settings,
                                         scaling_enabled=True)
    assert pair.reported is pair.scaled
    np.testing.assert_allclose(
        pair.scaled.chi2, pair.raw.chi2 * TWO_PI_SQUARED, rtol=1e-12, atol=0.0
    )


def test_3_ratio_is_exactly_the_factor_at_every_wavelength(cfg, states, settings):
    grid = chi2mod.wavelength_grid(cfg)
    for case in states.values():
        pair = chi2mod.chi2_both_conventions(case.states, grid, settings,
                                             scaling_enabled=True)
        ratio = pair.magnitude_ratio()
        np.testing.assert_allclose(ratio, TWO_PI_SQUARED, rtol=1e-12)


# =============================================================================
# Test 4 - scaling must not move a wavelength
# =============================================================================


def test_4_peak_wavelength_unchanged(cfg, states, settings):
    grid = chi2mod.wavelength_grid(cfg)
    for case in states.values():
        pair = chi2mod.chi2_both_conventions(case.states, grid, settings,
                                             scaling_enabled=True)
        assert pair.raw.peak()["wavelength_nm"] == pair.scaled.peak()["wavelength_nm"]
        np.testing.assert_array_equal(pair.raw.wavelength_nm,
                                      pair.scaled.wavelength_nm)


# =============================================================================
# Test 5 - scaling must not reorder the cases
# =============================================================================


def test_5_case_ranking_unchanged(cfg, states, settings):
    grid = chi2mod.wavelength_grid(cfg)
    target = float(cfg["chi2"]["target_wavelength_nm"])
    pairs = [chi2mod.chi2_both_conventions(case.states, grid, settings,
                                           scaling_enabled=True)
             for case in states.values()]
    raw_order = [p.case_id for p in
                 sorted(pairs, key=lambda p: p.raw.at_wavelength(target))]
    scaled_order = [p.case_id for p in
                    sorted(pairs, key=lambda p: p.scaled.at_wavelength(target))]
    assert raw_order == scaled_order


# =============================================================================
# Test 6 - scaling must not change the normalized lineshape
# =============================================================================


def test_6_normalized_spectral_shape_unchanged(cfg, states, settings):
    grid = chi2mod.wavelength_grid(cfg)
    for case in states.values():
        pair = chi2mod.chi2_both_conventions(case.states, grid, settings,
                                             scaling_enabled=True)
        np.testing.assert_allclose(pair.scaled.normalized_magnitude(),
                                   pair.raw.normalized_magnitude(),
                                   rtol=1e-12, atol=1e-12)


# =============================================================================
# Test 7 - configuration parsing recognises both boolean values
# =============================================================================


@pytest.mark.parametrize("flag,expected_convention", [
    (True, chi2mod.CONVENTION_SCALED),
    (False, chi2mod.CONVENTION_DEMO19),
])
def test_7_config_flag_selects_convention(cfg, flag, expected_convention):
    local = dict(cfg)
    local["chi2"] = dict(cfg["chi2"])
    local["chi2"]["apply_kspace_2pi_squared_scaling"] = flag
    assert config20.scaling_enabled(local) is flag
    assert chi2mod.settings_from_config(local).kspace_convention == expected_convention


@pytest.mark.parametrize("value,expected", [
    ("on", True), ("off", False), ("true", True), ("false", False),
    ("yes", True), ("no", False), ("1", True), ("0", False),
])
def test_7_cli_override_parsing(cfg, value, expected):
    updated = config20.apply_overrides(dict_copy(cfg), kspace_scale=value)
    assert config20.scaling_enabled(updated) is expected
    assert updated["_overrides"]["chi2.apply_kspace_2pi_squared_scaling"] is expected


def test_7_non_boolean_yaml_flag_is_rejected(cfg):
    local = dict_copy(cfg)
    local["chi2"]["apply_kspace_2pi_squared_scaling"] = "true"   # a string
    with pytest.raises(config20.Config20Error, match="must be a YAML boolean"):
        config20.validate(local)


def test_7_bad_cli_value_is_rejected(cfg):
    with pytest.raises(config20.Config20Error, match="must be on or off"):
        config20.apply_overrides(dict_copy(cfg), kspace_scale="maybe")


def dict_copy(cfg):
    import copy
    return copy.deepcopy(dict(cfg))


# =============================================================================
# Equivalence with Demo 19
# =============================================================================


def _demo19_module(name):
    for path in (DEMO19_DIR, DEMOS_DIR / "_shared",
                 DEMOS_DIR / "12_graded_interface_coupled_quantum_well_optimization",
                 DEMOS_DIR / "14_absolute_chi2_graded_acqw_bo"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    try:
        return __import__(name)
    except Exception as exc:                       # pragma: no cover
        pytest.skip(f"Demo 19 module {name} unavailable: {exc}")


def test_cases_match_demo19():
    """Demo 20's 13 cases are Demo 19's 13 cases, field for field."""

    cases19 = _demo19_module("cases19")
    theirs = cases19.all_cases()
    ours = cases.all_cases()
    assert len(ours) == len(theirs) == 13
    for mine, other in zip(ours, theirs):
        assert mine.case_id == other.case_id
        assert mine.case_name == other.case_name
        assert mine.profile == other.profile
        assert tuple(float(w) for w in mine.widths_nm) == tuple(
            float(w) for w in other.widths_nm)
        assert mine.nominal_grade_width_nm == other.nominal_grade_width_nm
        assert mine.implementation_type == other.implementation_type


def test_geometry_matches_demo19(cfg):
    """Interface positions and the domain are Demo 19's, derived not typed."""

    demo19 = _demo19_module("demo19")
    theirs = demo19.interface_positions()
    ours = grading.interface_positions(cfg)
    for key in cases.INTERFACE_IDS:
        assert ours[key] == pytest.approx(theirs[key], abs=1e-12)
    assert grading.geometry(cfg).domain_nm == pytest.approx(
        demo19.geometry().domain_nm, abs=1e-12)
    # The values the brief names explicitly.
    assert ours["I1"] == pytest.approx(9.1)
    assert ours["I2"] == pytest.approx(16.2)
    assert ours["I3"] == pytest.approx(18.0)
    assert ours["I4"] == pytest.approx(20.9)
    assert grading.geometry(cfg).domain_nm[1] == pytest.approx(30.0)


def test_composition_profiles_match_demo19(cfg):
    """Every case's x_Al(z) equals Demo 19's, analytically and as rendered."""

    demo19 = _demo19_module("demo19")
    cases19 = _demo19_module("cases19")
    theirs = {case.case_id: case for case in cases19.all_cases()}
    z = np.linspace(0.0, 30.0, 12001)
    for case in cases.all_cases():
        for rendered in (False, True):
            mine = grading.evaluate_composition(cfg, case, z, rendered=rendered)
            other = demo19.evaluate_composition(theirs[case.case_id], z,
                                                rendered=rendered)
            np.testing.assert_allclose(
                mine, other, rtol=0.0, atol=1e-14,
                err_msg=f"case {case.case_id} rendered={rendered}",
            )


def test_shape_functions_match_demo19_grading12():
    """The four ramp functions are grading12's, with Demo 19's parameters."""

    grading12 = _demo19_module("grading12")
    u = np.linspace(0.0, 1.0, 501)
    for mine, theirs in (("linear", "linear"), ("fermi", "sigmoid"),
                         ("erf", "erf"), ("cosine", "cosine")):
        np.testing.assert_allclose(
            grading.profile_fraction(u, mine, sigmoid_steepness=10.0,
                                     erf_span_sigma=3.0),
            grading12.profile_fraction(u, theirs, sigmoid_steepness=10.0,
                                       erf_span_sigma=3.0),
            rtol=0.0, atol=1e-15, err_msg=mine,
        )


def test_endpoints_are_exact(cfg):
    """Endpoint normalization: every family reaches exactly 0 and exactly 0.55."""

    high = float(cfg["materials"]["barrier_al_fraction"])
    for family in ("linear", "fermi", "erf", "cosine"):
        f = grading.profile_fraction(np.array([0.0, 1.0]), family)
        assert f[0] == pytest.approx(0.0, abs=1e-15)
        assert f[1] == pytest.approx(1.0, abs=1e-15)
    for case in cases.all_cases():
        if case.is_abrupt:
            continue
        profile = grading.build_profile(cfg, case)
        assert profile.diagnostics["realized_min_al_fraction"] == pytest.approx(
            0.0, abs=1e-12)
        assert profile.diagnostics["realized_peak_al_fraction"] == pytest.approx(
            high, abs=1e-12)


def test_decks_match_demo19(cfg):
    """Rendered decks and DAT tables are byte-identical to Demo 19's."""

    demo19 = _demo19_module("demo19")
    cases19 = _demo19_module("cases19")
    demo19_cfg = demo19.load_config()
    theirs = {case.case_id: case for case in cases19.all_cases()}
    for case in cases.all_cases():
        _g, _p, my_blocks, my_deck = inputs.build_case(cfg, case)
        _g2, _p2, their_blocks, their_deck = demo19.build_case(
            demo19_cfg, theirs[case.case_id])
        # The template header comment is the one intentional difference.
        my_body = my_deck.split("global{", 1)[1]
        their_body = their_deck.split("global{", 1)[1]
        assert my_body == their_body, f"deck body differs for case {case.case_id}"
        assert my_blocks["datafile"] == their_blocks["datafile"], (
            f"imported DAT differs for case {case.case_id}")


def test_grading_validation_matches_demo19(cfg):
    demo19 = _demo19_module("demo19")
    cases19 = _demo19_module("cases19")
    theirs = {case.case_id: case for case in cases19.all_cases()}
    for case in cases.all_cases():
        mine = grading.validate_realized(cfg, case)
        other = demo19.validate_realized(theirs[case.case_id])
        assert mine["validation_pass"] == other["validation_pass"]
        assert mine["maximum_composition_error"] == pytest.approx(
            other["maximum_composition_error"], abs=1e-15)


def test_chi2_reproduces_demo19_recorded_value(cfg, states, settings):
    """THE reproduction check: raw chi2 must equal Demo 19's own recorded number.

    The source table carries both the matrix elements Demo 19 fed to its
    susceptibility and the chi2 it got out. Recomputing the second from the
    first, with scaling off, must return the recorded value.
    """

    path = config20.master_table_path(cfg)
    with path.open(encoding="utf-8", newline="") as stream:
        recorded = {row["case_id"]: row for row in csv.DictReader(stream)}
    grid = chi2mod.wavelength_grid(cfg)
    target = float(cfg["chi2"]["target_wavelength_nm"])
    compared = 0
    for case_id, case in states.items():
        previous = recorded[case_id].get("chi2_1550_pm_per_V")
        if previous in (None, ""):
            continue
        spectrum = chi2mod.chi2_spectrum(
            case.states, grid, settings.with_convention(chi2mod.CONVENTION_DEMO19))
        assert spectrum.at_wavelength(target) == pytest.approx(
            float(previous), rel=1e-9), f"case {case_id}"
        compared += 1
    assert compared >= 1, "no Demo 19 chi2 values were available to compare"


def test_peak_reproduces_demo19_recorded_value(cfg, states, settings):
    path = config20.master_table_path(cfg)
    with path.open(encoding="utf-8", newline="") as stream:
        recorded = {row["case_id"]: row for row in csv.DictReader(stream)}
    grid = chi2mod.wavelength_grid(cfg)
    for case_id, case in states.items():
        row = recorded[case_id]
        if row.get("peak_wavelength_nm") in (None, ""):
            continue
        spectrum = chi2mod.chi2_spectrum(
            case.states, grid, settings.with_convention(chi2mod.CONVENTION_DEMO19))
        peak = spectrum.peak()
        assert peak["wavelength_nm"] == pytest.approx(
            float(row["peak_wavelength_nm"]), abs=1e-9), f"case {case_id}"
        assert peak["magnitude_pm_per_V"] == pytest.approx(
            float(row["peak_chi2_pm_per_V"]), rel=1e-9), f"case {case_id}"


# =============================================================================
# The k-space normalization itself
# =============================================================================


def test_demo19_convention_contains_one_over_two_pi_squared(settings):
    """The default weights are g_s * k/(2 pi) * dk, i.e. int d2k/(2 pi)^2."""

    probe = settings.with_convention(chi2mod.CONVENTION_DEMO19)
    k, weights = chi2mod.k_grid(probe)
    dk = k[1] - k[0]
    expected = k / (2.0 * math.pi) * dk * probe.spin_degeneracy
    expected[0] *= 0.5
    expected[-1] *= 0.5
    np.testing.assert_allclose(weights, expected, rtol=1e-15, atol=0.0)


def test_k_measure_matches_closed_form(settings):
    """Trapezoidal measure equals g_s kmax^2/(4 pi), and g_s pi kmax^2 scaled."""

    for convention in (chi2mod.CONVENTION_DEMO19, chi2mod.CONVENTION_SCALED):
        probe = settings.with_convention(convention)
        assert chi2mod.k_measure_total(probe) == pytest.approx(
            chi2mod.analytic_disc_measure(probe), rel=1e-13
        )


def test_k_measure_matches_independent_cartesian_quadrature(settings):
    """A 2D (kx, ky) quadrature that never uses isotropy lands on the same value.

    This is the check that the k/(2 pi) reduction is a reduction and not a
    restatement: it integrates dkx dky/(2 pi)^2 over the disc directly.
    """

    probe = settings.with_convention(chi2mod.CONVENTION_DEMO19)
    k_max = probe.k_max_per_nm
    axis = np.linspace(-k_max, k_max, 1201)
    kx, ky = np.meshgrid(axis, axis, indexing="ij")
    inside = (kx ** 2 + ky ** 2) <= k_max ** 2
    cell = (axis[1] - axis[0]) ** 2
    area = float(np.count_nonzero(inside)) * cell
    cartesian = area / (2.0 * math.pi) ** 2 * probe.spin_degeneracy
    # A pixelated disc converges to the analytic area from either side, so a
    # loose tolerance is correct here; the point is the (2 pi)^2, not the area.
    assert chi2mod.k_measure_total(probe) == pytest.approx(cartesian, rel=2e-3)


def test_two_conventions_differ_by_exactly_the_factor_pointwise(settings):
    exactness = chi2mod.scaling_is_exact_constant(settings)
    assert exactness["is_exact_constant"]
    assert exactness["total_measure_ratio"] == pytest.approx(TWO_PI_SQUARED, rel=1e-12)
    assert exactness["pointwise_ratio_min"] == pytest.approx(TWO_PI_SQUARED, rel=1e-12)
    assert exactness["pointwise_ratio_max"] == pytest.approx(TWO_PI_SQUARED, rel=1e-12)


def test_normalization_audit_reports_the_factor_as_present(settings):
    audit = qc.normalization_audit(settings, scaling_enabled=False)
    assert audit["explicit_one_over_2pi_squared_present"] is True
    assert audit["k_measure_matches_closed_form"] is True
    assert "ALREADY PRESENT" in audit["finding"]
    assert "REMOVES an existing denominator" in audit["finding"]
    text = qc.format_normalization_audit(audit)
    assert "k-SPACE NORMALIZATION AUDIT" in text


def test_scaling_placement_is_equivalent_to_post_multiplication(cfg, states, settings):
    """Applying the factor in the k measure == multiplying chi2 afterwards.

    True only because the factor is k-independent, which is exactly why the
    equivalence is tested rather than assumed.
    """

    case = next(iter(states.values()))
    grid = chi2mod.wavelength_grid(cfg)
    in_measure = chi2mod.chi2_spectrum(
        case.states, grid, settings.with_convention(chi2mod.CONVENTION_SCALED))
    post_multiplied = chi2mod.chi2_spectrum(
        case.states, grid, settings.with_convention(chi2mod.CONVENTION_DEMO19)
    ).chi2 * TWO_PI_SQUARED
    np.testing.assert_allclose(in_measure.chi2, post_multiplied, rtol=1e-12)


def test_k_grid_is_converged_at_production_point_count(cfg, states, settings):
    case = next(iter(states.values()))
    convergence = chi2mod.k_convergence_report(
        case.states, float(cfg["chi2"]["target_wavelength_nm"]), settings,
        point_counts=tuple(cfg["k_parallel"]["convergence_probe_points"]),
        tolerance=float(cfg["k_parallel"]["convergence_tolerance"]),
    )
    assert convergence["k_parallel_integration_converged"], convergence


# =============================================================================
# Status separation and end-to-end analysis
# =============================================================================


def test_solver_pass_and_physical_valid_stay_separate(cfg, states):
    """A zero return code is never promoted to a physical verdict."""

    extracted = extract.from_master_table(config20.master_table_path(cfg))
    results = analysis.analyse_cases(cfg, extracted)
    rows = [result.row for result in results]
    status = qc.status_summary(rows)
    assert status["case_count"] == 13
    for row in rows:
        if row["solver_pass"] and not row["physical_valid"]:
            assert row["failure_reason"], (
                "a solver_pass / physical_valid mismatch must carry a reason"
            )
    # The two flags must be independent fields, not aliases.
    assert "solver_pass" in analysis.MASTER_FIELDS
    assert "physical_valid" in analysis.MASTER_FIELDS


def test_master_table_keeps_every_demo19_field():
    """No Demo 19 column was dropped when the Demo 20 columns were added."""

    sys.path.insert(0, str(DEMO19_DIR))
    run_demo19 = _demo19_module("run_demo19")
    missing = [f for f in run_demo19.MASTER_FIELDS if f not in analysis.MASTER_FIELDS]
    assert not missing, f"Demo 20 dropped Demo 19 field(s): {missing}"


def test_analysis_retains_both_values_for_every_case(cfg):
    extracted = extract.from_master_table(config20.master_table_path(cfg))
    results = analysis.analyse_cases(cfg, extracted)
    with_spectra = [r for r in results if r.has_spectrum]
    assert with_spectra, "no case produced a spectrum"
    for result in with_spectra:
        row = result.row
        raw = float(row["chi2_raw_1550_pm_per_V"])
        scaled = float(row["chi2_scaled_1550_pm_per_V"])
        reported = float(row["chi2_reported_1550_pm_per_V"])
        assert scaled == pytest.approx(raw * TWO_PI_SQUARED, rel=1e-12)
        assert reported in (pytest.approx(raw, rel=1e-12),
                           pytest.approx(scaled, rel=1e-12))


def test_scaling_invariance_checks_all_pass(cfg):
    extracted = extract.from_master_table(config20.master_table_path(cfg))
    results = analysis.analyse_cases(cfg, extracted)
    pairs = [r.pair for r in results if r.has_spectrum]
    checks = qc.scaling_invariance_checks(pairs, cfg)
    failed = [check.name for check in checks if not check.passed]
    assert not failed, f"invariance checks failed: {failed}"
    assert len(checks) == 5


def test_preflight_passes_without_a_solver(cfg):
    report = inputs.preflight_report(cfg)
    assert report["case_count"] == 13
    assert report["all_grading_valid"]
    assert report["all_decks_complete"]
    assert report["all_imported_tables_present"]
    assert report["overlap_cases"] == []
    assert report["licensed_solver_run"] is False


def test_no_overlapping_grades_in_any_case(cfg):
    for case in cases.all_cases():
        assert grading.overlaps(cfg, case) == [], case.case_id


def test_plateau_lengths_stay_positive(cfg):
    """A requested grade must never be wider than the layer it sits in."""

    for case in cases.all_cases():
        for name, value in grading.plateau_lengths_nm(cfg, case).items():
            assert value > 0, f"case {case.case_id}: {name} = {value}"


def test_imported_dat_has_expected_row_count(cfg):
    """The symmetric 0.7 nm smooth profiles land on the 0.05 nm grid exactly."""

    lookup = cases.by_id()
    for case_id in ("10", "11", "12"):
        _g, _p, blocks, _deck = inputs.build_case(cfg, lookup[case_id])
        assert len(blocks["datafile"].splitlines()) == 601, case_id


def test_paper_comparison_does_not_fit(cfg):
    """The paper target is a comparison only: no scale factor is fitted to it."""

    extracted = extract.from_master_table(config20.master_table_path(cfg))
    results = analysis.analyse_cases(cfg, extracted)
    paper = analysis.paper_comparison(cfg, results)
    assert paper["evaluated"]
    # Nothing lands exactly on the target; if it did, something was fitted.
    assert paper["raw_ratio_to_paper"] != pytest.approx(1.0, abs=1e-6)
    assert paper["scaled_ratio_to_paper"] != pytest.approx(1.0, abs=1e-6)
    assert paper["remaining_factor_after_scaling"] is not None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
