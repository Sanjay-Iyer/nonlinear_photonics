"""Demo 21 tests. Every one runs without a licensed nextnano++.

Demo 21 is a teaching layer, so its tests answer two questions:

1. Does the educational material still describe the production code correctly?
   (Every ``EDUCATIONAL REPRODUCTION`` matches production; every ``file:line``
   citation still points at the function it claims; the worked case is still
   case 04.)
2. Does the trace still reproduce the stored Demo 20 result?

Anything that drifts in Demo 20 should fail a test here rather than quietly
turn this walkthrough into a description of a calculation that no longer exists.

Run with:
    python -m pytest nextnano/demos/21_demo20_mathematical_walkthrough/tests -q
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

DEMO21_DIR = Path(__file__).resolve().parents[1]
DEMOS_DIR = DEMO21_DIR.parent
DEMO20_DIR = DEMOS_DIR / "20_quantum_well_interface_grading_scaled"
REPO_ROOT = DEMOS_DIR.parent.parent
if str(DEMO21_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO21_DIR))

import demo20_math_physics_reference as ref     # noqa: E402
import trace_demo20_linear_1nm as trace         # noqa: E402

config20 = ref.config20
cases = ref.cases
grading = ref.grading
chi2mod = ref.chi2mod
extract = ref.extract

WALKTHROUGH = DEMO21_DIR / "DEMO20_MATH_WALKTHROUGH_LINEAR_1NM.md"


@pytest.fixture(scope="module")
def cfg():
    return config20.load()


@pytest.fixture(scope="module")
def case():
    return cases.by_id()[ref.WORKED_CASE_ID]


@pytest.fixture(scope="module")
def settings(cfg):
    return chi2mod.settings_from_config(
        cfg, convention=chi2mod.CONVENTION_DEMO19)


@pytest.fixture(scope="module")
def states(cfg, settings):
    path = config20.master_table_path(cfg)
    if not path.is_file():
        pytest.skip(f"no source results table at {path}")
    found = extract.from_master_table(path)[ref.WORKED_CASE_ID]
    if not found.has_states:
        pytest.skip("case 04 has no solver states in the source table")
    return found.states.truncated(int(settings.max_states_per_band))


# --- 1. the material still describes the right thing -------------------------


def test_worked_case_is_the_one_nm_linear_case(case):
    """The whole walkthrough is written around case 04. Pin it."""

    assert case.case_id == "04"
    assert case.case_name == "Linear 1.0 nm"
    assert case.profile == "linear"
    assert case.widths_nm == (1.0, 1.0, 1.0, 1.0)
    assert case.nominal_grade_width_nm == 1.0
    assert case.render_method == "ternary_linear"
    assert case.implementation_type == "NATIVE_NEXTNANO_SYNTAX"


def test_reference_module_imports_production_not_a_copy():
    """The re-exported names must be the production objects themselves."""

    assert ref.profile_fraction is grading.profile_fraction
    assert ref.evaluate_composition is grading.evaluate_composition
    assert ref.build_profile is grading.build_profile
    assert ref.geometry is grading.geometry
    assert ref.interface_positions is grading.interface_positions
    assert ref.k_grid is chi2mod.k_grid
    assert ref.chi2_spectrum is chi2mod.chi2_spectrum
    assert ref.absolute_prefactor is chi2mod.absolute_prefactor
    assert ref.transition_energies_eV is chi2mod.transition_energies_eV
    assert ref.overlap_matrix is ref.shared_chi2.overlap_matrix
    assert ref.position_matrix is ref.shared_chi2.position_matrix


def test_every_educational_reproduction_matches_production(cfg):
    """The self-check is the contract that makes this file trustworthy."""

    records = ref.self_check(cfg)
    assert len(records) >= 8
    assert all(row["passed"] for row in records)
    # Only the two float-reassociation checks may carry any tolerance at all.
    tolerated = [row["check"] for row in records if row["relative_tolerance"]]
    assert set(tolerated) <= {"absolute_prefactor", "triple_sum_unrolled_vs_direct"}
    for row in records:
        assert row["relative_tolerance"] <= 1.0e-15


def test_dft_constant_matches_the_configured_value(cfg):
    """r_e,hh is quoted in the walkthrough; it must still be what Demo 20 uses."""

    assert ref.R_E_HH_NM_DFT == float(cfg["chi2"]["r_e_hh_nm"]) == 0.751


def test_constants_are_aliases_not_second_copies():
    assert ref.ELEMENTARY_CHARGE_C is chi2mod.ELEMENTARY_CHARGE_C
    assert ref.VACUUM_PERMITTIVITY_F_PER_M is chi2mod.VACUUM_PERMITTIVITY_F_PER_M
    assert ref.REDUCED_PLANCK_J_S is chi2mod.REDUCED_PLANCK_J_S
    assert ref.HC_EV_NM is chi2mod.HC_EV_NM


# --- 2. the cited source locations still exist -------------------------------


CITED_LOCATIONS = [
    ("20_quantum_well_interface_grading_scaled/s01_cases.py", 133, "def all_cases"),
    ("20_quantum_well_interface_grading_scaled/s02_grading.py", 103, "def geometry"),
    ("20_quantum_well_interface_grading_scaled/s02_grading.py", 139,
     "def interface_positions"),
    ("20_quantum_well_interface_grading_scaled/s02_grading.py", 151,
     "def interface_directions"),
    ("20_quantum_well_interface_grading_scaled/s02_grading.py", 162,
     "def profile_fraction"),
    ("20_quantum_well_interface_grading_scaled/s02_grading.py", 211,
     "def evaluate_composition"),
    ("20_quantum_well_interface_grading_scaled/s02_grading.py", 312,
     "def build_profile"),
    ("20_quantum_well_interface_grading_scaled/s02_grading.py", 362,
     "def grade_intervals"),
    ("20_quantum_well_interface_grading_scaled/s03_inputs.py", 107,
     "def _native_blocks"),
    ("20_quantum_well_interface_grading_scaled/s03_inputs.py", 169, "def render_deck"),
    ("20_quantum_well_interface_grading_scaled/s03_inputs.py", 207, "def build_case"),
    ("20_quantum_well_interface_grading_scaled/s04_solver.py", 191, "def solve_case"),
    ("20_quantum_well_interface_grading_scaled/s04_solver.py", 272, "def parse_case"),
    ("20_quantum_well_interface_grading_scaled/s05_extract.py", 111,
     "def from_master_table"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 157,
     "def photon_energy_eV"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 289, "def n_z_for"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 346, "def k_grid"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 398,
     "def analytic_disc_measure"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 490, "def truncated"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 514,
     "def absolute_prefactor"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 537,
     "def transition_energies_eV"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 573,
     "def at_wavelength"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 604,
     "def wavelength_grid"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 612, "def chi2_spectrum"),
    ("20_quantum_well_interface_grading_scaled/s06_chi2.py", 745,
     "def k_convergence_report"),
    ("_shared/chi2.py", 120, "class BandStates"),
    ("_shared/chi2.py", 134, "def __post_init__"),
    ("_shared/chi2.py", 188, "def orthonormality_error"),
    ("_shared/chi2.py", 204, "def overlap_matrix"),
    ("_shared/chi2.py", 220, "def position_matrix"),
    ("11_paper_validation_interband_chi2_acqw/demo11.py", 431, "def analyse_case"),
    ("14_absolute_chi2_graded_acqw_bo/demo14.py", 852, "def analyse_real_trial"),
]


@pytest.mark.parametrize("relative_path,line_number,expected", CITED_LOCATIONS)
def test_cited_line_numbers_still_point_at_the_named_definition(
    relative_path, line_number, expected
):
    """Every ``file:line`` in the walkthrough must still resolve.

    A stale citation is the main way a document like this rots, so the
    citations are executable rather than decorative.
    """

    path = DEMOS_DIR / relative_path
    assert path.is_file(), path
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= line_number, f"{relative_path} is shorter than {line_number}"
    assert lines[line_number - 1].lstrip().startswith(expected), (
        f"{relative_path}:{line_number} is {lines[line_number - 1]!r}, "
        f"expected it to start with {expected!r}")


def test_cited_statement_lines_still_say_what_is_quoted():
    """Line citations that name a statement rather than a definition."""

    chi2_lines = (DEMO20_DIR / "s06_chi2.py").read_text(
        encoding="utf-8").splitlines()
    assert "np.dot(weights, accumulated)" in chi2_lines[660]     # :661, the k sum
    assert "two_photon = transitions - 2.0" in chi2_lines[642]   # :643
    assert "one_photon = transitions - 1.0" in chi2_lines[643]   # :644
    assert "for m in range(n_h)" in chi2_lines[645]              # :646
    assert "chi2=total * prefactor" in chi2_lines[689]           # :690

    shared_lines = (DEMOS_DIR / "_shared" / "chi2.py").read_text(
        encoding="utf-8").splitlines()
    # The normalization block is cited as :155-162.
    assert "normalised = np.empty_like(envelopes)" in shared_lines[154]       # :155
    assert "np.trapezoid(envelopes[:, index] ** 2, z)" in shared_lines[156]   # :157
    assert "/ math.sqrt(norm)" in shared_lines[161]                           # :162
    assert "np.trapezoid(a.envelopes[:, i] * b.envelopes[:, j]" in shared_lines[211]
    assert "band.envelopes[:, i] * band.z_nm * band.envelopes[:, j]" in shared_lines[227]


# --- 3. the physics of the worked case has not moved -------------------------


def test_interface_positions_are_the_documented_ones(cfg):
    positions = grading.interface_positions(cfg)
    assert positions == pytest.approx(
        {"I1": 9.1, "I2": 16.2, "I3": 18.0, "I4": 20.9})
    assert grading.geometry(cfg).domain_nm == (0.0, 30.0)


def test_linear_grading_endpoints_and_midpoint(cfg, case):
    """The worked table in section 5 of the walkthrough, checked."""

    z = np.array([8.60, 8.85, 9.10, 9.35, 9.60])
    expected = np.array([0.550, 0.4125, 0.275, 0.1375, 0.000])
    assert grading.evaluate_composition(cfg, case, z) == pytest.approx(expected)
    # The tunnel barrier keeps only 0.8 nm of pure alloy - the claim in section 5.
    plateaus = grading.plateau_lengths_nm(cfg, case)
    assert plateaus["tunnel_barrier_pure_nm"] == pytest.approx(0.8)


def test_native_linear_rendering_has_zero_sampling_error(cfg, case):
    """Section 6 claims the composition error is exactly 0 for a linear case."""

    row = grading.validate_realized(cfg, case)
    assert row["validation_pass"] is True
    assert row["maximum_composition_error"] == 0.0
    assert not case.is_imported


def test_deck_contains_the_four_documented_ternary_linear_regions(cfg, case):
    _g, _profile, _blocks, deck = ref.build_case(cfg, case)
    for span, alloy in ((("8.600000", "9.600000"), ("0.550000", "0.000000")),
                        (("15.700000", "16.700000"), ("0.000000", "0.550000")),
                        (("17.500000", "18.500000"), ("0.550000", "0.000000")),
                        (("20.400000", "21.400000"), ("0.000000", "0.550000"))):
        expected = (f'ternary_linear{{ name = "Al(x)Ga(1-x)As"  '
                    f"alloy_x = [{alloy[0]}, {alloy[1]}]  "
                    f"x = [{span[0]}, {span[1]}] }}")
        assert expected in deck, expected
    assert "ternary_pyramid" not in deck
    assert ref.deck_is_complete(deck)


def test_k_measure_matches_its_closed_form_in_both_conventions(settings):
    for convention in (chi2mod.CONVENTION_DEMO19, chi2mod.CONVENTION_SCALED):
        probe = settings.with_convention(convention)
        assert chi2mod.k_measure_total(probe) == pytest.approx(
            chi2mod.analytic_disc_measure(probe), rel=1e-12)
    audit = chi2mod.scaling_is_exact_constant(settings)
    assert audit["is_exact_constant"] is True
    assert audit["expected_factor"] == pytest.approx((2 * np.pi) ** 2)


def test_unrolled_terms_are_the_sixteen_the_walkthrough_lists(states, settings):
    energy = float(chi2mod.photon_energy_eV(trace.TARGET_NM))
    terms = ref.chi2_summand_terms(states, 40, energy, settings)
    assert len(terms) == 16
    assert sum(1 for t in terms if t["term"] == "conduction") == 8
    assert sum(1 for t in terms if t["term"] == "valence") == 8
    assert not any(t["skipped_zero_numerator"] for t in terms)
    # The near-cancellation the walkthrough calls out (section 19).
    conduction = sum(t["contribution"] for t in terms if t["term"] == "conduction")
    total = sum(t["contribution"] for t in terms)
    assert abs(conduction) / abs(total) > 10.0


def test_intermediate_quantities_are_finite_and_dimensionally_sane(
    cfg, case, states, settings
):
    profile = grading.build_profile(cfg, case)
    assert np.all(np.isfinite(profile.al_fraction))
    assert profile.al_fraction.min() >= 0.0
    assert profile.al_fraction.max() <= float(cfg["materials"]["barrier_al_fraction"])

    k, weights = chi2mod.k_grid(settings)
    assert np.all(np.isfinite(k)) and np.all(np.isfinite(weights))
    assert weights[0] == 0.0 and np.all(weights >= 0.0)
    assert k[-1] == pytest.approx(settings.k_max_per_nm)

    transitions = chi2mod.transition_energies_eV(states, k, settings)
    assert transitions.shape == (2, 2, int(settings.k_parallel_points))
    assert np.all(transitions > 0.0)                 # interband, so positive
    assert np.all(np.diff(transitions, axis=2) > 0)  # rises monotonically with k

    prefactor = chi2mod.absolute_prefactor(settings)
    assert np.isfinite(prefactor) and prefactor > 0.0

    spectrum = chi2mod.chi2_spectrum(states, chi2mod.wavelength_grid(cfg), settings)
    assert np.all(np.isfinite(spectrum.chi2))
    assert np.all(spectrum.magnitude > 0.0)


def test_1550nm_is_a_grid_node_so_interpolation_is_exact(cfg, states, settings):
    """Section 22's claim about how the reported number is selected."""

    grid = chi2mod.wavelength_grid(cfg)
    node = int(np.argmin(np.abs(grid - trace.TARGET_NM)))
    assert grid[node] == trace.TARGET_NM
    spectrum = chi2mod.chi2_spectrum(states, grid, settings)
    assert spectrum.at_wavelength(trace.TARGET_NM) == spectrum.magnitude[node]


# --- 4. the trace still reproduces the stored Demo 20 result -----------------


def test_traced_value_matches_the_stored_demo20_result(cfg, states, settings):
    """The headline check, run directly rather than through the CLI."""

    stored = trace._stored_row(trace.DEMO20_TABLE, ref.WORKED_CASE_ID)
    if stored is None:
        pytest.skip(f"no stored Demo 20 table at {trace.DEMO20_TABLE}")
    grid = chi2mod.wavelength_grid(cfg)
    raw = chi2mod.chi2_spectrum(states, grid, settings)
    scaled = chi2mod.chi2_spectrum(
        states, grid, settings.with_convention(chi2mod.CONVENTION_SCALED))
    # Same production function on the same inputs: bit-identical, not merely close.
    assert raw.at_wavelength(trace.TARGET_NM) == float(
        stored["chi2_raw_1550_pm_per_V"])
    assert scaled.at_wavelength(trace.TARGET_NM) == float(
        stored["chi2_scaled_1550_pm_per_V"])


def test_traced_value_matches_demo19_recorded_value(cfg, states, settings):
    path = config20.master_table_path(cfg)
    with path.open(encoding="utf-8", newline="") as stream:
        rows = {row["case_id"]: row for row in csv.DictReader(stream)}
    recorded = rows[ref.WORKED_CASE_ID].get("chi2_1550_pm_per_V")
    if recorded in (None, ""):
        pytest.skip("Demo 19 recorded no chi2 for case 04")
    spectrum = chi2mod.chi2_spectrum(
        states, chi2mod.wavelength_grid(cfg), settings)
    assert spectrum.at_wavelength(trace.TARGET_NM) == pytest.approx(
        float(recorded), rel=1e-15)


def test_hand_reconstruction_agrees_with_production(cfg, states, settings):
    """The independent path: rebuild chi2 from the unrolled terms."""

    energy = float(chi2mod.photon_energy_eV(trace.TARGET_NM))
    k, weights = chi2mod.k_grid(settings)
    accumulated = np.array(
        [sum(t["contribution"]
             for t in ref.chi2_summand_terms(states, i, energy, settings))
         for i in range(k.size)], dtype=complex)
    reconstructed = abs(np.dot(weights, accumulated)
                        * chi2mod.absolute_prefactor(settings))
    production = chi2mod.chi2_spectrum(
        states, chi2mod.wavelength_grid(cfg), settings).at_wavelength(
            trace.TARGET_NM)
    assert reconstructed == pytest.approx(production, rel=1e-14)


def test_demo20_production_still_runs_unchanged(cfg):
    """Demo 21 must not have perturbed Demo 20. Re-run its analysis stage."""

    import s07_analysis as analysis  # noqa: PLC0415 - Demo 20's own driver

    path = config20.master_table_path(cfg)
    if not path.is_file():
        pytest.skip("no source results table")
    extracted = extract.from_master_table(path)
    results = analysis.analyse_cases(cfg, extracted)
    assert len(results) == cases.CASE_COUNT
    case04 = next(r for r in results if r.case_id == ref.WORKED_CASE_ID)
    assert case04.has_spectrum
    assert case04.row["chi2_reproduces_demo19"] is True


# --- 4b. STEP 08: the Case 04 envelope path ----------------------------------


def test_case04_parsed_path_is_repo_relative():
    """The brief requires REPO_ROOT resolution, not an absolute Windows path."""

    assert trace.CASE04_PARSED == (
        trace.REPO_ROOT / "demo_results/demo20/data/case_04/optical/parsed")
    # Must be inside the repo, and must not have been hardcoded per machine.
    assert trace.CASE04_PARSED.relative_to(trace.REPO_ROOT) == Path(
        "demo_results/demo20/data/case_04/optical/parsed")
    source = (DEMO21_DIR / "trace_demo20_linear_1nm.py").read_text(encoding="utf-8")
    assert "C:\\\\Code" not in source and "C:/Code" not in source
    assert 'REPO_ROOT / "demo_results/demo20/data/case_04/optical/parsed"' in source


def test_envelope_columns_are_the_four_chi2_uses():
    assert trace.ENVELOPE_COLUMNS == ("z_nm", "psi_e1", "psi_e2", "psi_hh1", "psi_hh2")


def _write_thirteen_column_fixture(directory: Path) -> dict[str, np.ndarray]:
    """A 13-column envelopes.csv + 6x6 matrix_elements.json, for the LOADER only.

    THIS IS NOT CASE 04 PHYSICS and is never presented as such. Case 04's own
    parsed run is not in this checkout, so the numbers here are borrowed from
    the one real licensed envelope table that is (Demo 11 s1_ref) and padded out
    to the 13-column / 6-state shape a Demo 20 parsed run has. Its only job is
    to prove that the STEP 08 reader selects the right columns by name, slices
    the recorded matrices correctly, and would fail loudly if it did not.
    """

    source = trace.AUX_ENVELOPES
    if not (source / "envelopes.csv").is_file():
        pytest.skip("no real licensed envelope table available to build a fixture")
    z, psi_e, psi_h, _ = trace._read_envelope_table(source / "envelopes.csv")
    recorded = json.loads((source / "matrix_elements.json").read_text(encoding="utf-8"))

    # 6 states per band; states 3-6 are filler the reader must IGNORE. They are
    # deliberately given values that would wreck every matrix element if the
    # reader sliced by position instead of by name.
    n = z.size
    filler = [np.full(n, 7.0 + i) for i in range(4)]
    columns = [z, psi_e[:, 0], psi_e[:, 1], *filler,
               psi_h[:, 0], psi_h[:, 1], *filler]
    header = ("z_nm,psi_e1,psi_e2,psi_e3,psi_e4,psi_e5,psi_e6,"
              "psi_hh1,psi_hh2,psi_hh3,psi_hh4,psi_hh5,psi_hh6")
    directory.mkdir(parents=True, exist_ok=True)
    np.savetxt(directory / "envelopes.csv", np.column_stack(columns),
               delimiter=",", header=header, comments="")

    # 6x6 recorded matrices whose LEADING 2x2 blocks are the real ones.
    def expand(block):
        big = np.full((6, 6), -999.0)
        big[:2, :2] = np.asarray(block, dtype=float)[:2, :2]
        return big.tolist()

    (directory / "matrix_elements.json").write_text(json.dumps({
        "overlap_electron_hole": expand(recorded["overlap_electron_hole"]),
        "position_matrix_electron_nm": expand(recorded["position_matrix_electron_nm"]),
        "position_matrix_heavy_hole_nm": expand(
            recorded["position_matrix_heavy_hole_nm"]),
        "units": "nm",
    }, indent=2), encoding="utf-8")
    return {"z": z, "psi_e": psi_e, "psi_h": psi_h}


def test_step08_reads_thirteen_columns_by_name_and_verifies_all_12_elements(
    tmp_path, monkeypatch
):
    """The full STEP 08 contract, on a 13-column / 6-state table."""

    fixture = tmp_path / "parsed"
    truth = _write_thirteen_column_fixture(fixture)
    monkeypatch.setattr(trace, "CASE04_PARSED", fixture)

    out_csv = tmp_path / "06_case04_envelopes.csv"
    result = trace.case04_envelope_demo(out_csv)
    assert result is not None, "the Case 04 path did not engage"
    assert result["is_case04"] is True
    assert result["source"] == "Demo 20 Case 04 licensed envelopes"

    # (1) loaded, (2) raw arrays recorded, ignoring the 8 filler columns
    assert len(result["columns_present"]) == 13
    assert result["grid_points"] == truth["z"].size

    # (5) norms before and after, for all four states
    assert set(result["norm_before"]) == {"psi_e1", "psi_e2", "psi_hh1", "psi_hh2"}
    assert set(result["norm_after"]) == {"psi_e1", "psi_e2", "psi_hh1", "psi_hh2"}
    for value in result["norm_after"].values():
        assert value == pytest.approx(1.0, abs=1e-12)

    # (6) orthonormality of both bands
    for value in result["orthonormality_error"].values():
        assert value < 1e-9

    # (11) every element compared, (12) every one asserted
    assert len(result["element_comparisons"]) == 12
    assert {row["symbol"] for row in result["element_comparisons"]} == {"O", "z_e", "z_hh"}
    assert result["max_absolute_difference"] < 1e-12
    for row in result["element_comparisons"]:
        assert row["absolute_difference"] <= row["allowed"]

    # the checkpoint CSV, with exactly the columns the brief specifies
    assert out_csv.is_file()
    with out_csv.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == [
            "z_nm", "psi_e1_raw", "psi_e2_raw", "psi_hh1_raw", "psi_hh2_raw",
            "psi_e1_normalized", "psi_e2_normalized",
            "psi_hh1_normalized", "psi_hh2_normalized",
            "psi_e1_times_psi_hh1", "psi_e1_z_psi_e1"]
        rows = list(reader)
    assert len(rows) == truth["z"].size
    # the two integrand columns must be the products they claim to be
    first = rows[1]
    assert float(first["psi_e1_times_psi_hh1"]) == pytest.approx(
        float(first["psi_e1_normalized"]) * float(first["psi_hh1_normalized"]), rel=1e-15)
    assert float(first["psi_e1_z_psi_e1"]) == pytest.approx(
        float(first["psi_e1_normalized"]) ** 2 * float(first["z_nm"]), rel=1e-15)


def test_step08_reader_is_not_fooled_by_column_order(tmp_path, monkeypatch):
    """Shuffle the header; name-based selection must still pick the right four."""

    fixture = tmp_path / "parsed"
    _write_thirteen_column_fixture(fixture)
    straight = trace._read_envelope_table(fixture / "envelopes.csv")

    text = (fixture / "envelopes.csv").read_text(encoding="utf-8").splitlines()
    names = text[0].split(",")
    order = [names.index(n) for n in
             ["psi_hh2", "z_nm", "psi_e5", "psi_e1", "psi_hh1", "psi_e2"]]
    order += [i for i in range(len(names)) if i not in order]
    shuffled = [",".join(names[i] for i in order)]
    for line in text[1:]:
        cells = line.split(",")
        shuffled.append(",".join(cells[i] for i in order))
    (fixture / "envelopes.csv").write_text("\n".join(shuffled) + "\n", encoding="utf-8")

    reshuffled = trace._read_envelope_table(fixture / "envelopes.csv")
    for a, b in zip(straight[:3], reshuffled[:3]):
        assert np.array_equal(a, b), "column selection depends on order"


def test_step08_rejects_a_table_missing_a_required_column(tmp_path):
    path = tmp_path / "envelopes.csv"
    path.write_text("z_nm,psi_e1,psi_e2,psi_hh1\n0,1,1,1\n1,1,1,1\n2,1,1,1\n",
                    encoding="utf-8")
    with pytest.raises(trace.Extract20EnvelopeError, match="psi_hh2"):
        trace._read_envelope_table(path)


def test_step08_assertion_fires_when_stored_and_recomputed_disagree(
    tmp_path, monkeypatch
):
    """The guard must actually guard - corrupt one element and expect a failure."""

    fixture = tmp_path / "parsed"
    _write_thirteen_column_fixture(fixture)
    payload = json.loads((fixture / "matrix_elements.json").read_text(encoding="utf-8"))
    payload["overlap_electron_hole"][0][0] += 1.0e-6      # far above the tolerance
    (fixture / "matrix_elements.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(trace, "CASE04_PARSED", fixture)
    with pytest.raises(AssertionError, match=r"O\[e1,hh1\]"):
        trace.case04_envelope_demo(None)


def test_step08_falls_back_only_when_case04_is_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(trace, "CASE04_PARSED", tmp_path / "nothing_here")
    assert trace.case04_envelope_demo(None) is None
    fallback = trace.demo11_fallback_demo(None)
    if fallback is not None:
        assert fallback["is_case04"] is False
        assert "fallback" in fallback["source"].lower()


def test_leading_block_slices_a_six_by_six_correctly():
    big = np.arange(36, dtype=float).reshape(6, 6)
    assert np.array_equal(trace._leading_block(big),
                          np.array([[0.0, 1.0], [6.0, 7.0]]))
    small = [[1.0, 2.0], [3.0, 4.0]]
    assert np.array_equal(trace._leading_block(small), np.asarray(small))


# --- 5. the scripts run end to end -------------------------------------------


def test_trace_script_runs_and_writes_every_checkpoint(tmp_path):
    """The deliverable the brief names: `python trace_demo20_linear_1nm.py`."""

    completed = subprocess.run(
        [sys.executable, str(DEMO21_DIR / "trace_demo20_linear_1nm.py"),
         "--outdir", str(tmp_path)],
        capture_output=True, text=True, timeout=900,
    )
    assert completed.returncode == 0, completed.stdout[-4000:] + completed.stderr[-4000:]
    assert "All 5 verification checks PASSED." in completed.stdout

    expected = {
        "01_inputs.json", "02_geometry.csv", "03_grading_profile.csv",
        "04_nextnano_input_summary.txt", "05_subband_energies.csv",
        "07_matrix_elements.csv", "08_transition_energies_zero_k.csv",
        "09_k_grid.csv", "10_transition_energies_vs_k.csv",
        "11_triple_sum_terms_at_1550nm.csv", "12_k_contributions.csv",
        "13_chi2_spectrum.csv", "14_final_result.json",
    }
    written = {path.name for path in tmp_path.iterdir()}
    assert expected <= written, expected - written

    final = json.loads((tmp_path / "14_final_result.json").read_text(encoding="utf-8"))
    assert final["case_id"] == "04"
    assert final["target_wavelength_nm"] == 1550.0
    assert len(final["verification"]) == 5
    # Status flags stay separate and honest.
    assert final["solver_pass"] is True
    assert final["physical_valid"] is False

    k_rows = list(csv.DictReader(
        (tmp_path / "12_k_contributions.csv").open(encoding="utf-8")))
    assert len(k_rows) == 96
    spectrum_rows = list(csv.DictReader(
        (tmp_path / "13_chi2_spectrum.csv").open(encoding="utf-8")))
    assert len(spectrum_rows) == 401
    term_rows = list(csv.DictReader(
        (tmp_path / "11_triple_sum_terms_at_1550nm.csv").open(encoding="utf-8")))
    assert len(term_rows) == 16


def test_reference_module_tour_runs():
    completed = subprocess.run(
        [sys.executable, str(DEMO21_DIR / "demo20_math_physics_reference.py")],
        capture_output=True, text=True, timeout=600,
    )
    assert completed.returncode == 0, completed.stdout[-4000:] + completed.stderr[-4000:]
    assert "All educational reproductions agree with production" in completed.stdout


# --- 6. the walkthrough document itself --------------------------------------


def test_walkthrough_quotes_the_current_result(states, cfg, settings):
    """The headline number in the Markdown must still be the computed one."""

    text = WALKTHROUGH.read_text(encoding="utf-8")
    spectrum = chi2mod.chi2_spectrum(
        states, chi2mod.wavelength_grid(cfg), settings)
    assert repr(spectrum.at_wavelength(trace.TARGET_NM)) != ""
    assert f"{spectrum.at_wavelength(trace.TARGET_NM):.15f}" in text
    assert f"{spectrum.peak()['magnitude_pm_per_V']!r}" in text


def test_walkthrough_labels_background_theory_and_the_dft_scalar():
    text = WALKTHROUGH.read_text(encoding="utf-8")
    assert "BACKGROUND THEORY — not directly evaluated in Python" in text
    assert "0.751" in text
    assert "physical_valid" in text and "solver_pass" in text
    # Every section the brief asks for is present.
    for heading in ("## 1. What are we calculating?",
                    "## 8. What nextnano solves",
                    "## 20. Integrating over k-space",
                    "## 25. Where to modify the math",
                    "## 29. Verification against the existing Demo 20 result",
                    "## Glossary"):
        assert heading in text, heading


def test_walkthrough_file_citations_resolve():
    """Every `file.py:NNN` in the Markdown must name a real line."""

    text = WALKTHROUGH.read_text(encoding="utf-8")
    pattern = re.compile(r"`?([A-Za-z0-9_/]+\.py):(\d+)`?")
    checked = 0
    for name, number in pattern.findall(text):
        candidates = [
            DEMOS_DIR / name,
            DEMO20_DIR / Path(name).name,
            DEMOS_DIR / "_shared" / Path(name).name,
            DEMOS_DIR / "11_paper_validation_interband_chi2_acqw" / Path(name).name,
            DEMOS_DIR / "14_absolute_chi2_graded_acqw_bo" / Path(name).name,
            REPO_ROOT / name,
        ]
        path = next((c for c in candidates if c.is_file()), None)
        if path is None:
            continue
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert int(number) <= line_count, (
            f"{name}:{number} is past the end of {path} ({line_count} lines)")
        checked += 1
    assert checked >= 20, f"only {checked} citations resolved to a file"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
