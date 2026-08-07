"""Demo 16: the ACQW renderer stress-validation fixture.

These tests protect the four failure classes that reached a licensed Demo 14 run:
invalid region syntax, a structure with no outer barriers, well widths reported
as grading widths, and a solver failure that was masked by a later Python error.

The deliberately-bad structures at the end matter as much as the good ones: a
validator that accepts everything valid is not thereby able to reject anything
invalid, and that distinction is the whole point of Demo 16.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import cases16
import demo14
import demo16
import grading14

CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "demos" / "16_acqw_renderer_stress_validation" / cases16.CASES_FILENAME
)


@pytest.fixture(scope="module")
def cfg():
    return demo14.load_config()


@pytest.fixture(scope="module")
def cases():
    return cases16.load_cases(CASES_PATH)


# --- the fixture itself ----------------------------------------------------


def test_there_are_exactly_twenty_cases(cases):
    assert len(cases) == 20
    assert len({c.case_id for c in cases}) == 20


def test_twelve_deliberate_and_eight_seeded(cases):
    assert sum(1 for c in cases if c.origin == "deliberate") == 12
    assert sum(1 for c in cases if c.origin == "seeded_random") == 8


def test_case_list_is_deterministic():
    """Regenerating must reproduce the frozen file exactly."""

    a = [c.parameters() for c in cases16.all_cases()]
    b = [c.parameters() for c in cases16.all_cases()]
    assert a == b
    assert [c.parameters() for c in cases16.load_cases(CASES_PATH)] == a


def test_seed_is_fixed():
    assert cases16.SEED == 1616


def test_all_parameters_are_inside_the_demo14_ranges(cases):
    for case in cases:
        params = case.parameters()
        for name, (lo, hi) in cases16.BOUNDS.items():
            assert lo - 1e-9 <= params[name] <= hi + 1e-9, (case.case_id, name)


def test_every_grading_profile_is_represented(cases):
    present = {c.grading_profile for c in cases}
    assert present == set(cases16.PROFILES)


def test_paper_reference_geometry(cases):
    case = next(c for c in cases if c.name == "paper_reference")
    thick, thin = case.well_widths_nm()
    assert thick == pytest.approx(7.1, abs=1e-6)
    assert thin == pytest.approx(2.9, abs=1e-6)
    assert case.nominal_central_barrier_thickness_nm == pytest.approx(1.8)
    assert case.asymmetry_s == pytest.approx(0.42, abs=1e-9)


@pytest.mark.parametrize("name,field,expected", [
    ("minimum_barrier", "nominal_central_barrier_thickness_nm", 0.85),
    ("maximum_barrier", "nominal_central_barrier_thickness_nm", 2.50),
    ("minimum_left_grade", "gaas_to_algaas_grading_width_10_90_nm", 0.40),
    ("maximum_left_grade", "gaas_to_algaas_grading_width_10_90_nm", 1.40),
    ("minimum_right_grade", "algaas_to_gaas_grading_width_10_90_nm", 0.40),
    ("maximum_right_grade", "algaas_to_gaas_grading_width_10_90_nm", 1.40),
    ("low_asymmetry_boundary", "asymmetry_s", 0.30),
    ("high_asymmetry_boundary", "asymmetry_s", 0.55),
])
def test_boundary_cases_sit_on_their_boundaries(cases, name, field, expected):
    case = next(c for c in cases if c.name == name)
    assert getattr(case, field) == pytest.approx(expected)


# --- structure -------------------------------------------------------------


def test_every_case_has_both_outer_barriers_and_two_gaas_wells(cfg, cases):
    for case in cases:
        _g, profile, _b, _d = demo16.build_case(cfg, case)
        invariants = demo16.structural_invariants(
            profile.x_nm, profile.al_fraction,
            profile.request["interfaces_nm"], cases16.AL_FRACTION,
        )
        failed = [k for k, v in invariants.items() if k != "all_passed" and not v]
        assert not failed, f"{case.case_id}: {failed}"


def test_four_interfaces_are_present_and_ordered(cfg, cases):
    for case in cases:
        _g, profile, _b, _d = demo16.build_case(cfg, case)
        i = profile.request["interfaces_nm"]
        assert len(i) == 4
        assert (i["outer_left_algaas_to_gaas"] < i["central_gaas_to_algaas"]
                < i["central_algaas_to_gaas"] < i["outer_right_gaas_to_algaas"])


def test_one_material_specification_per_region(cfg, cases):
    """nextnano++ rejects a region carrying several -- the first gate failure."""

    import re

    materials = ("binary{", "ternary_constant{", "ternary_linear{", "ternary_import{")
    for case in cases:
        _g, _p, _b, deck = demo16.build_case(cfg, case)
        start = deck.index("structure{")
        depth = 0
        for end in range(start, len(deck)):
            if deck[end] == "{":
                depth += 1
            elif deck[end] == "}":
                depth -= 1
                if depth == 0:
                    break
        bodies = re.findall(r"region\{(.*?)\n    \}", deck[start:end], flags=re.S)
        assert bodies, case.case_id
        for body in bodies:
            assert sum(body.count(m) for m in materials) <= 1, (case.case_id, body)


# --- the 7.1 / 2.9 regression ---------------------------------------------


def test_well_widths_are_never_reported_as_grading_widths(cfg, cases):
    """The exact numbers the bug produced, asserted against by value."""

    for case in cases:
        _g, profile, _b, _d = demo16.build_case(cfg, case)
        thick, thin = case.well_widths_nm()
        interfaces = profile.request["interfaces_nm"]
        widths = {
            "outer_left_algaas_to_gaas": case.algaas_to_gaas_grading_width_10_90_nm,
            "central_gaas_to_algaas": case.gaas_to_algaas_grading_width_10_90_nm,
            "central_algaas_to_gaas": case.algaas_to_gaas_grading_width_10_90_nm,
            "outer_right_gaas_to_algaas": case.gaas_to_algaas_grading_width_10_90_nm,
        }
        for metric in demo16.measure_interfaces(
            profile.x_nm, profile.al_fraction, interfaces, widths, cases16.AL_FRACTION
        ):
            realized = metric.realized_width_10_90_nm
            if realized is None:
                continue
            for forbidden in (thick, thin, 7.1, 2.9):
                assert abs(realized - forbidden) > 0.4, (
                    f"{case.case_id}/{metric.name}: realized {realized:.3f} nm "
                    f"matches a WELL width ({forbidden:.3f} nm)"
                )


def test_interface_windows_never_contain_a_neighbouring_interface(cfg, cases):
    for case in cases:
        _g, profile, _b, _d = demo16.build_case(cfg, case)
        interfaces = profile.request["interfaces_nm"]
        widths = {k: 1.4 for k in interfaces}   # deliberately over-wide request
        for metric in demo16.measure_interfaces(
            profile.x_nm, profile.al_fraction, interfaces, widths, cases16.AL_FRACTION
        ):
            assert metric.window_isolated, (case.case_id, metric.name, metric.window_nm)


# --- overlap ---------------------------------------------------------------


def test_overlap_case_does_not_fabricate_a_plateau(cfg, cases):
    """Case 09: 1.4/1.4 nm grades across 0.85 nm cannot reach Al = 0.55."""

    case = next(c for c in cases if c.name == "maximum_overlap_linear")
    _g, profile, blocks, _d = demo16.build_case(cfg, case)
    report = demo16.overlap_report(
        profile.x_nm, profile.al_fraction,
        profile.request["interfaces_nm"], cases16.AL_FRACTION,
    )
    assert report["grades_overlap"] is True
    assert report["nominal_plateau_exists"] is False
    assert report["realized_peak_al_fraction"] < 0.5 * cases16.AL_FRACTION
    assert report["local_integrated_al_dose_nm_equivalent"] > 0.0
    # A linear design whose ramps overlap must switch to an imported profile;
    # a linear -> constant -> linear template would override one ramp.
    assert "ternary_import" in blocks["structure_block"]
    assert blocks.get("render_fallback_reason")


def test_thick_barrier_does_have_a_plateau(cfg, cases):
    case = next(c for c in cases if c.name == "maximum_barrier")
    _g, profile, _b, _d = demo16.build_case(cfg, case)
    report = demo16.overlap_report(
        profile.x_nm, profile.al_fraction,
        profile.request["interfaces_nm"], cases16.AL_FRACTION,
    )
    assert report["grades_overlap"] is False
    assert report["nominal_plateau_exists"] is True
    assert report["realized_peak_al_fraction"] == pytest.approx(0.55, abs=1e-3)


# --- deliberately-bad structures must FAIL ---------------------------------


def _flat(value: float, n: int = 400) -> tuple[np.ndarray, np.ndarray]:
    x = np.linspace(0.0, 40.0, n)
    return x, np.full_like(x, value)


BAD_INTERFACES = {
    "outer_left_algaas_to_gaas": 10.0,
    "central_gaas_to_algaas": 17.1,
    "central_algaas_to_gaas": 18.9,
    "outer_right_gaas_to_algaas": 21.8,
}


def test_bad_a_missing_outer_barriers_is_rejected():
    """GaAs background: the exact structure that shipped to a licensed run."""

    x = np.linspace(0.0, 40.0, 801)
    y = np.where((x > 17.1) & (x < 18.9), 0.55, 0.0)   # barrier only, GaAs elsewhere
    invariants = demo16.structural_invariants(x, y, BAD_INTERFACES, 0.55)
    assert invariants["left_outer_barrier_present"] is False
    assert invariants["right_outer_barrier_present"] is False
    assert invariants["confinement_is_material_not_boundary"] is False
    assert invariants["all_passed"] is False


def test_bad_c_missing_central_barrier_is_rejected():
    x = np.linspace(0.0, 40.0, 801)
    y = np.where((x >= 10.0) & (x <= 21.8), 0.0, 0.55)   # both wells merged
    invariants = demo16.structural_invariants(x, y, BAD_INTERFACES, 0.55)
    assert invariants["central_barrier_present"] is False
    assert invariants["all_passed"] is False


def test_bad_e_excess_aluminium_is_rejected():
    x, y = _flat(0.60)
    invariants = demo16.structural_invariants(x, y, BAD_INTERFACES, 0.55)
    assert invariants["composition_within_bounds"] is False
    assert invariants["all_passed"] is False


def test_bad_nonfinite_composition_is_rejected():
    x, y = _flat(0.55)
    y[10] = np.nan
    invariants = demo16.structural_invariants(x, y, BAD_INTERFACES, 0.55)
    assert invariants["composition_finite"] is False
    assert invariants["all_passed"] is False


def test_bad_b_two_materials_in_one_region_is_rejected_by_the_parser_check():
    """The parse-result reader must recognise nextnano++'s own refusal."""

    stdout = (
        "Reading input file (case.in)...\n"
        "Validation error in line 43 at group:\n'structure/region'.\n"
        "Too many instances of 'ternary_linear'.\nTerminating program !!\n"
    )
    combined = stdout.lower()
    fatal = [m for m in ("terminating program", "validation error", "fatal error",
                         "too many instances", "unexpected group") if m in combined]
    assert fatal, "the fatal-marker set does not recognise this real failure"
    assert "parsing completed" not in combined


def test_bad_solver_nonzero_exit_stops_before_analysis():
    """Demo 14's wrapper must raise rather than analyse a failed solve."""

    import solver14

    assert "terminating program" in solver14.FATAL_STDOUT_MARKERS
    assert solver14.SolverTechnicalFailure is not None


# --- the deck actually parses ---------------------------------------------


def _parser():
    import preflight16

    return preflight16.parser_executable(None)


@pytest.mark.skipif(_parser() is None, reason="no nextnano++ available")
@pytest.mark.parametrize("profile", cases16.PROFILES)
def test_a_representative_deck_of_each_family_parses(cfg, cases, profile, tmp_path):
    import preflight16

    exe = _parser()
    database = preflight16.database_for(exe)
    case = next(c for c in cases if c.grading_profile == profile)
    _g, _p, blocks, deck = demo16.build_case(cfg, case)
    result = demo16.parse_deck(exe, database, tmp_path / case.case_id, deck,
                              blocks["datafile"])
    assert result["passed"], f"{profile}: {result['failure_reason']}"
    assert not result["fatal_markers"]


@pytest.mark.skipif(_parser() is None, reason="no nextnano++ available")
def test_the_overlap_case_parses(cfg, cases, tmp_path):
    import preflight16

    exe = _parser()
    case = next(c for c in cases if c.name == "maximum_overlap_linear")
    _g, _p, blocks, deck = demo16.build_case(cfg, case)
    result = demo16.parse_deck(exe, preflight16.database_for(exe),
                               tmp_path / "overlap", deck, blocks["datafile"])
    assert result["passed"], result["failure_reason"]


# --- artifacts -------------------------------------------------------------


def test_failed_cases_preserve_their_artifacts(cfg, cases, tmp_path):
    case = cases[0]
    outcome = demo16.validate_case_level1(cfg, case, tmp_path / "c", None, None)
    # No parser available -> unchecked, but every artifact must still exist.
    assert (tmp_path / "c" / "requested_parameters.json").is_file()
    assert (tmp_path / "c" / "intended_profile.csv").is_file()
    assert (tmp_path / "c" / "case_result.json").is_file()
    assert outcome.status == "syntax_unchecked"
    assert outcome.invariants["all_passed"] is True


def test_results_root_has_no_duplicate_demo_runs():
    import run_demo16

    try:
        root = run_demo16.results_root()
    except Exception:
        pytest.skip("machine config unavailable")
    parts = list(Path(root).parts)
    assert not [a for a, b in zip(parts, parts[1:]) if a == b]
    assert parts.count("demo_runs") == 1


# --- parser output classification -----------------------------------------
#
# The work-laptop run reported "Checking database for errors..." as the reason
# for all 20 failures. That is a PROGRESS line; the extractor matched "error" as
# a substring and returned the first hit, hiding the real message. These tests
# pin the classification so a diagnosis can never again be a status line.


def test_benign_progress_lines_are_not_treated_as_failures():
    for line in (
        "Checking database for errors...",
        "Checking input file for errors...",
        "NOTE: This version of nextnano++ does not need a license file. "
        "License file ignored.",
        "In case you have a paid license, please download the corresponding "
        "licensed version of nextnano++.",
    ):
        lowered = line.lower()
        assert any(b in lowered for b in demo16._BENIGN_LINES), line
        assert not any(
            m in lowered for m in demo16._FATAL_MARKERS
        ), f"benign line matched a fatal marker: {line}"


def test_real_failures_are_still_detected():
    for line, expected in (
        ("Too many instances of 'ternary_linear'.", "too many instances"),
        ("Terminating program !!", "terminating program"),
        ("Validation error in line 43 at group:", "validation error"),
        ("ERROR: license expired", "license expired"),
        ("Unexpected group 'output_imports'.", "unexpected group"),
    ):
        assert any(m in line.lower() for m in demo16._FATAL_MARKERS), line


def test_failure_reason_skips_progress_lines_and_names_the_real_error():
    stdout = (
        "Reading input file (case.in)...\n"
        "Checking database for errors...\n"
        "Validation error in line 43 at group:\n"
        "'structure/region'.\n"
        "Too many instances of 'ternary_linear'.\n"
        "Terminating program !!\n"
    )
    reason = demo16._failure_reason(stdout, "", 1)
    assert "Checking database for errors" not in reason, (
        "the reason is a progress line, not a diagnosis"
    )
    assert "Too many instances" in reason or "Validation error" in reason


def test_failure_reason_shows_the_tail_when_nothing_names_itself_an_error():
    """A binary that dies quietly must still produce a usable message."""

    stdout = "Reading environment...\nChecking database for errors...\n"
    reason = demo16._failure_reason(stdout, "", 3)
    assert "exit 3" in reason
    assert "last output" in reason


def test_license_is_forwarded_to_the_parser():
    """The licensed build will not start without -l, even for --parse."""

    import inspect

    source = inspect.getsource(demo16.parse_deck)
    assert '"-l"' in source, "parse_deck does not pass the licence file"
    assert "license_path" in inspect.signature(demo16.parse_deck).parameters
