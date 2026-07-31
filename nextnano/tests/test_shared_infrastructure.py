"""Unit tests for the shared Demo 4-10 infrastructure.

None of these needs a nextnano++ licence. Tests that consume solver output use
the *real* nextnano++ 3.0.0 files committed under ``tests/fixtures``; see the
PROVENANCE note there.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

import analysis
import layers
import nlo
import outputs
import plots
import registry
import schemas
import sweeps

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "nextnano_pp_3_0_0"
DEMO_ROOT = Path(__file__).resolve().parents[1] / "demos"


# ---------------------------------------------------------------------------
# layers
# ---------------------------------------------------------------------------


def test_symmetric_double_well_geometry_and_intervals():
    stack = layers.symmetric_double_well(
        well_width_nm=6.0,
        centre_barrier_nm=4.0,
        left_outer_barrier_nm=20.0,
        right_outer_barrier_nm=20.0,
        aluminum_fraction=0.3,
        active_grid_spacing_nm=0.25,
        exterior_grid_spacing_nm=0.5,
    )
    assert stack.total_thickness_nm == pytest.approx(56.0)
    assert stack.interval("left_well") == (20.0, 26.0)
    assert stack.interval("centre_barrier") == (26.0, 30.0)
    assert stack.interval("right_well") == (30.0, 36.0)
    # The two identical wells must be equidistant from the structure centre.
    centre = 0.5 * sum(stack.interval("centre_barrier"))
    left = stack.interval("left_well")
    right = stack.interval("right_well")
    assert centre - left[1] == pytest.approx(right[0] - centre)


def test_quantum_region_is_clipped_to_the_domain():
    stack = layers.symmetric_double_well(
        well_width_nm=6.0,
        centre_barrier_nm=4.0,
        left_outer_barrier_nm=5.0,
        right_outer_barrier_nm=5.0,
        aluminum_fraction=0.3,
        active_grid_spacing_nm=0.25,
        exterior_grid_spacing_nm=0.5,
    )
    start, end = stack.quantum_region_nm(100.0)
    assert start == 0.0
    assert end == stack.total_thickness_nm


def test_grid_lines_place_a_point_on_every_interface():
    stack = layers.asymmetric_double_well(
        left_well_width_nm=8.0,
        right_well_width_nm=5.0,
        centre_barrier_nm=3.0,
        left_outer_barrier_nm=20.0,
        right_outer_barrier_nm=20.0,
        aluminum_fraction=0.3,
        active_grid_spacing_nm=0.25,
        exterior_grid_spacing_nm=0.5,
    )
    text = stack.grid_lines()
    for boundary in (0.0, 20.0, 28.0, 31.0, 36.0, 56.0):
        assert f"pos = {boundary:.9g}" in text


def test_contact_slab_is_generated_only_when_requested():
    stack = layers.symmetric_double_well(
        well_width_nm=6.0,
        centre_barrier_nm=4.0,
        left_outer_barrier_nm=20.0,
        right_outer_barrier_nm=20.0,
        aluminum_fraction=0.3,
        active_grid_spacing_nm=0.25,
        exterior_grid_spacing_nm=0.5,
    )
    everywhere = stack.structure_regions(contact_name="c")
    assert everywhere.count("contact{ name = c }") == 1
    assert "everywhere{}" in everywhere.split("contact{ name = c }")[0]

    slab = stack.structure_regions(contact_name="c", contact_thickness_nm=2.0)
    assert "line{ x = [0, 2] }" in slab
    # With a slab the fill region must NOT also carry the contact.
    fill = slab.split("# Mandatory contact")[0]
    assert "contact{ name = c }" not in fill


def test_doping_region_outside_the_domain_is_rejected():
    stack = layers.symmetric_double_well(
        well_width_nm=6.0,
        centre_barrier_nm=4.0,
        left_outer_barrier_nm=20.0,
        right_outer_barrier_nm=20.0,
        aluminum_fraction=0.3,
        active_grid_spacing_nm=0.25,
        exterior_grid_spacing_nm=0.5,
    )
    with pytest.raises(layers.GeometryError, match="leaves the"):
        stack.structure_regions(contact_name="c", doping=[("d", 10.0, 900.0, 1e18)])


def test_ternary_layer_requires_an_alloy_fraction():
    with pytest.raises(layers.GeometryError, match="alloy_x"):
        layers.Layer("well", layers.ALGAAS, 5.0)
    with pytest.raises(layers.GeometryError, match="must not define alloy_x"):
        layers.Layer("well", layers.GAAS, 5.0, 0.3)


def test_wire2d_geometry_and_anisotropy():
    wire = layers.Wire2D(
        core_width_nm=20.0,
        core_height_nm=8.0,
        barrier_x_nm=30.0,
        barrier_y_nm=30.0,
        aluminum_fraction=0.3,
    )
    assert wire.domain_x_nm == (0.0, 80.0)
    assert wire.core_x_nm == (30.0, 50.0)
    assert wire.mesh_anisotropy(grid_spacing_x_nm=1.0, grid_spacing_y_nm=1.0) == 1.0
    assert wire.mesh_anisotropy(grid_spacing_x_nm=2.0, grid_spacing_y_nm=0.5) == 4.0


def test_wire2d_offset_must_keep_the_core_inside():
    with pytest.raises(layers.GeometryError, match="offset_x_nm"):
        layers.Wire2D(
            core_width_nm=20.0,
            core_height_nm=8.0,
            barrier_x_nm=5.0,
            barrier_y_nm=5.0,
            aluminum_fraction=0.3,
            offset_x_nm=6.0,
        )


# ---------------------------------------------------------------------------
# schemas
# ---------------------------------------------------------------------------


def test_every_demo_directory_has_a_registered_schema():
    for path in sorted(DEMO_ROOT.glob("[0-9][0-9]_*")):
        if (path / "demo.yaml").is_file():
            assert schemas.schema_for(path.name) is not None


def test_legacy_schema_matches_the_demo_1_to_3_key_sets():
    # Demos 1-3 were validated with exactly these keys; widening them silently
    # would let a typo through on a licensed run.
    assert "well_width_nm" in schemas.LEGACY_SCHEMA.scientific
    assert "aluminum_fraction" in schemas.LEGACY_SCHEMA.fraction
    assert "number_of_states" in schemas.LEGACY_SCHEMA.integer
    assert "electric_field_kV_cm" not in schemas.LEGACY_SCHEMA.scientific


def test_signed_parameters_accept_negative_values_and_positive_ones_do_not():
    schemas.check_value(
        schemas.DEMO5_SCHEMA, "electric_field_kV_cm", -100.0, "field"
    )
    with pytest.raises(schemas.SchemaError, match="> 0"):
        schemas.check_value(schemas.DEMO5_SCHEMA, "well_width_nm", -1.0, "width")


def test_fraction_parameters_reject_one_and_zero():
    for value in (0.0, 1.0, 1.5):
        with pytest.raises(schemas.SchemaError, match="between 0 and 1"):
            schemas.check_value(
                schemas.DEMO4_SCHEMA, "aluminum_fraction", value, "x"
            )


def test_unknown_top_level_section_is_rejected():
    with pytest.raises(schemas.SchemaError, match="unsupported key"):
        schemas.strict_keys({"mystery": 1}, schemas.BASE_TOP_LEVEL, "cfg")


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------


def test_registry_covers_every_demo_directory():
    loaded = registry.load_registry()
    assert registry.missing_from_registry(loaded) == ()


def test_only_work_laptop_validated_demos_are_declared_physically_validated():
    loaded = registry.load_registry()
    validated = [
        demo_id
        for demo_id, record in loaded.demos.items()
        if record.physically_validated
    ]
    assert validated == [
        "01_classical_single_quantum_well",
        "02_one_band_finite_quantum_well",
        "03_quantum_well_convergence",
        "04_symmetric_double_quantum_well",
    ]


def test_demo4_dependency_report_accepts_work_laptop_validated_dependencies():
    loaded = registry.load_registry()
    report = loaded.dependency_report("04_symmetric_double_quantum_well")
    assert report["all_dependencies_physically_validated"] is True
    assert "02_one_band_finite_quantum_well" in report["depends_on"]
    assert report["interpretation"] == "Every declared dependency is physically validated."


def test_dependencies_precede_their_dependents():
    loaded = registry.load_registry()
    for record in loaded.demos.values():
        for dependency in record.depends_on:
            assert dependency < record.demo_id


def test_registry_rejects_an_unknown_status(tmp_path):
    import yaml

    path = tmp_path / "registry.yaml"
    path.write_text(
        yaml.safe_dump({"demos": {"01_x": {"status": "definitely_fine"}}}),
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="allowed"):
        registry.load_registry(path)


# ---------------------------------------------------------------------------
# outputs / parsers
# ---------------------------------------------------------------------------


def test_parser_profile_loads_and_declares_its_confirmation_state():
    profile = outputs.load_profile()
    assert profile.solver_version.startswith("nextnano++ 3.0.0")
    assert profile.spec("bandedges").confirmed is True
    # Strain and Demo 8 k.p layouts are confirmed by licensed runs; the new
    # quantum-spectra absorption filename remains pending.
    assert profile.spec("strain_tensor").confirmed is True
    assert profile.spec("transition_energies_kp8").confirmed is True
    assert profile.spec("absorption_coefficient_quantum_spectra").confirmed is False
    assert profile.spec("energy_spectrum_kp8").confirmed is False
    assert "strain_tensor" not in profile.unconfirmed_keys()
    assert "absorption_coefficient_quantum_spectra" in profile.unconfirmed_keys()


def test_parser_profile_rejects_an_unknown_artifact_key():
    profile = outputs.load_profile()
    with pytest.raises(outputs.ParserError, match="has no artifact"):
        profile.spec("not_a_real_artifact")


def test_header_parsing_splits_names_and_units():
    parsed = outputs.parse_header("x[nm]   Psi^2_1[nm^-1]   Psi^2_2[nm^-1]")
    assert parsed[0] == ("x", "nm")
    assert parsed[1] == ("Psi^2_1", "nm^-1")
    assert outputs.parse_header("no.   Energy[eV]") == (("no.", ""), ("Energy", "eV"))


def test_missing_required_output_lists_what_was_written(tmp_path):
    raw = tmp_path / "raw"
    (raw / "bias_00000").mkdir(parents=True)
    (raw / "bias_00000" / "something_else.dat").write_text("1 2\n", encoding="utf-8")
    profile = outputs.load_profile()
    with pytest.raises(outputs.ParserError) as error:
        outputs.resolve_outputs(profile, raw, ["bandedges"])
    assert "Files actually present" in str(error.value)
    assert "something_else.dat" in str(error.value)


def test_ambiguous_output_is_refused_rather_than_guessed(tmp_path):
    raw = tmp_path / "raw"
    for name in ("bias_00000", "bias_00001"):
        (raw / name).mkdir(parents=True)
        (raw / name / "bandedges.dat").write_text("x[nm] G[eV]\n0 1\n1 1\n", encoding="utf-8")
    profile = outputs.load_profile()
    with pytest.raises(outputs.ParserError, match="ambiguous"):
        outputs.resolve_outputs(profile, raw, ["bandedges"])


def test_column_map_is_cross_checked_against_the_header(tmp_path):
    path = tmp_path / "bandedges.dat"
    path.write_text(
        "x[nm]  Gamma[eV]  HH[eV]  LH[eV]\n0 1.6 0.0 -0.01\n1 1.4 0.0 -0.02\n",
        encoding="utf-8",
    )
    table = outputs.read_table(path)
    assert table.select({"position_nm": 0, "conduction_eV": 1})["conduction_eV"][0] == 1.6
    # Asking for the HH column under the name of the conduction band must fail.
    with pytest.raises(outputs.ParserError, match="but the configuration calls it"):
        table.select({"conduction_eV": 2})


def test_magnitude_column_is_selected_by_unit_not_by_position():
    path = (
        FIXTURES
        / "demo09_dipole"
        / "bias_00000"
        / "Quantum"
        / "cqw"
        / "Gamma_Gamma"
        / "dipole_moment_matrix_elements_k00000_growth_x.txt"
    )
    column = outputs.magnitude_column(path, unit="e*nm")
    assert "^2" not in column
    assert not column.startswith(("Re", "Im"))
    units = outputs.matrix_element_units(path)
    assert units[column] == "e*nm"


def test_completion_evidence_distinguishes_finished_from_running(tmp_path):
    finished = tmp_path / "done"
    finished.mkdir()
    (finished / "job_done.txt").write_text("ok", encoding="utf-8")
    evidence = outputs.completion_evidence(finished)
    assert evidence["job_done_file_present"] is True
    assert evidence["no_stale_job_running_file"] is True

    stalled = tmp_path / "stalled"
    stalled.mkdir()
    (stalled / "job_running.txt").write_text("running", encoding="utf-8")
    evidence = outputs.completion_evidence(stalled)
    assert evidence["job_done_file_present"] is False
    assert evidence["no_stale_job_running_file"] is False


def test_completion_markers_match_the_real_solver_log():
    # The "DONE." banner only reaches the console; matching on it would fail
    # every real run. summary.log says "Simulation completed."
    text = (FIXTURES / "demo04_symmetric_dqw" / "summary.log").read_text(encoding="utf-8")
    checks = outputs.scan_log_markers(
        text,
        completion_markers=["simulation completed", "calculation successfully completed"],
        fatal_markers=["terminating program"],
        warning_markers=["failed to converge"],
    )
    assert checks["completion_marker_found"] is True
    assert checks["no_fatal_marker"] is True
    assert checks["no_convergence_warning"] is True


def test_convergence_warning_is_detected_in_a_real_non_converged_run():
    text = (FIXTURES / "demo06_doped_scf" / "summary.log").read_text(encoding="utf-8")
    checks = outputs.scan_log_markers(
        text,
        completion_markers=["simulation completed"],
        warning_markers=["failed to converge"],
    )
    # The solver finished AND warned. Completion must not imply convergence.
    assert checks["completion_marker_found"] is True
    assert checks["no_convergence_warning"] is False


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


def _gaussian(x: np.ndarray, centre: float, width: float = 2.0) -> np.ndarray:
    return np.exp(-(((x - centre) / width) ** 2))


def test_region_probability_interpolates_the_interval_edges():
    x = np.linspace(0.0, 10.0, 11)
    density = np.ones_like(x) / 10.0
    # A window that falls between grid points must still integrate exactly.
    assert analysis.region_probability(x, density, 2.5, 7.5) == pytest.approx(0.5)


def test_normalisation_and_centroid_of_a_known_density():
    x = np.linspace(0.0, 40.0, 401)
    raw = 3.7 * _gaussian(x, 15.0)
    normalised, integral = analysis.normalise_density(x, raw)
    assert integral == pytest.approx(float(np.trapezoid(raw, x)))
    assert float(np.trapezoid(normalised, x)) == pytest.approx(1.0)
    assert analysis.centroid_nm(x, normalised) == pytest.approx(15.0, abs=1e-6)


def test_envelope_sign_is_canonicalised():
    x = np.linspace(0.0, 10.0, 101)
    psi = _gaussian(x, 5.0)
    positive, _ = analysis.normalise_envelope(x, psi)
    negative, _ = analysis.normalise_envelope(x, -psi)
    assert np.allclose(positive, negative)


def test_parity_of_symmetric_and_antisymmetric_envelopes():
    x = np.linspace(0.0, 20.0, 401)
    symmetric = _gaussian(x, 6.0) + _gaussian(x, 14.0)
    antisymmetric = _gaussian(x, 6.0) - _gaussian(x, 14.0)
    label, confidence = analysis.parity(x, symmetric, centre_nm=10.0)
    assert label == "symmetric" and confidence == pytest.approx(1.0, abs=1e-3)
    label, confidence = analysis.parity(x, antisymmetric, centre_nm=10.0)
    assert label == "antisymmetric" and confidence == pytest.approx(1.0, abs=1e-3)


def test_parity_of_a_one_sided_state_is_mixed():
    x = np.linspace(0.0, 20.0, 401)
    label, confidence = analysis.parity(x, _gaussian(x, 6.0), centre_nm=10.0)
    assert label == "mixed"
    assert confidence < 0.5


def test_position_matrix_element_of_two_separated_states():
    x = np.linspace(0.0, 40.0, 801)
    left, _ = analysis.normalise_envelope(x, _gaussian(x, 15.0))
    right, _ = analysis.normalise_envelope(x, _gaussian(x, 25.0))
    symmetric, _ = analysis.normalise_envelope(x, left + right)
    antisymmetric, _ = analysis.normalise_envelope(x, left - right)
    # For a symmetric/antisymmetric pair, z12 is half the state separation.
    z12 = analysis.position_matrix_element_nm(x, symmetric, antisymmetric)
    assert abs(z12) == pytest.approx(5.0, rel=0.02)


def test_state_tracking_follows_a_swap_by_overlap():
    x = np.linspace(0.0, 40.0, 401)
    a = _gaussian(x, 15.0)
    b = _gaussian(x, 25.0)
    previous = np.column_stack([a, b])
    current = np.column_stack([b, a])  # the solver reordered them
    result = analysis.track_states(
        x=x, previous_envelopes=previous, current_envelopes=current
    )
    assert result.assignment == (1, 0)
    assert min(result.confidence) > 0.9
    assert result.is_confident


def test_state_tracking_flags_ambiguity_below_the_threshold():
    x = np.linspace(0.0, 40.0, 401)
    previous = np.column_stack([_gaussian(x, 15.0), _gaussian(x, 25.0)])
    hybrid_a = _gaussian(x, 15.0) + _gaussian(x, 25.0)
    hybrid_b = _gaussian(x, 15.0) - _gaussian(x, 25.0)
    current = np.column_stack([hybrid_a, hybrid_b])
    result = analysis.track_states(
        x=x,
        previous_envelopes=previous,
        current_envelopes=current,
        minimum_confidence=0.9,
    )
    assert result.ambiguous  # hybridised states cannot be matched confidently
    assert not result.is_confident


def test_feature_based_tracking_when_envelopes_are_unusable():
    previous = [[0.9, 0.1, 20.0, 1.0], [0.1, 0.9, 30.0, 1.1]]
    current = [[0.1, 0.9, 30.1, 1.1], [0.9, 0.1, 20.1, 1.0]]
    result = analysis.track_states(
        previous_features=previous, current_features=current
    )
    assert result.method == "feature_distance"
    assert result.assignment == (1, 0)


def test_avoided_crossing_is_flagged_at_the_minimum_gap():
    fields = np.linspace(-4.0, 4.0, 17)
    lower = -np.sqrt(fields**2 + 0.25) / 1000.0
    upper = +np.sqrt(fields**2 + 0.25) / 1000.0
    flags = analysis.detect_avoided_crossings(
        fields, np.column_stack([lower, upper]), minimum_gap_meV=2.0
    )
    assert flags
    assert flags[0]["parameter_value"] == pytest.approx(0.0, abs=0.6)


def test_no_avoided_crossing_flag_for_parallel_branches():
    fields = np.linspace(-4.0, 4.0, 17)
    lower = np.zeros_like(fields)
    upper = np.full_like(fields, 0.05)
    assert analysis.detect_avoided_crossings(fields, np.column_stack([lower, upper])) == []


def test_character_classification_reports_mixed_states():
    assert analysis.classify_character({"HH": 0.9, "LH": 0.1})[0] == "HH-like"
    assert analysis.classify_character({"HH": 0.55, "LH": 0.45})[0] == "mixed"
    assert analysis.classify_character({"HH": 2.0, "LH": 2.0})[0] == "mixed"


def test_component_weights_are_normalised():
    weights = analysis.normalise_weights({"HH": 3.0, "LH": 1.0})
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["HH"] == pytest.approx(0.75)


def test_charge_balance_converts_nm_to_cm_correctly():
    x_nm = np.linspace(0.0, 100.0, 101)
    density = np.full_like(x_nm, 1.0e18)
    balance = analysis.charge_balance(
        x_nm,
        electron_density_cm3=density,
        ionized_donor_density_cm3=density,
    )
    # 1e18 cm^-3 over 100 nm = 1e18 * 1e-5 cm = 1e13 cm^-2.
    assert balance["electron_sheet_density_cm2"] == pytest.approx(1.0e13, rel=1e-9)
    assert balance["relative_charge_imbalance"] == pytest.approx(0.0, abs=1e-12)


def test_convergence_is_not_claimed_at_the_iteration_cap():
    result = analysis.classify_convergence(
        [1, 2, 3], {"Residual_Potential": [1.0, 0.1, 1e-12]},
        tolerance=1e-6,
        maximum_iterations=3,
    )
    assert result["status"] == "max_iterations_reached"
    assert result["converged"] is False
    assert result["residuals_within_tolerance"] is True


def test_solver_verdict_overrides_the_residual_arithmetic():
    result = analysis.classify_convergence(
        [1, 2], {"Residual_Potential": [1.0, 0.0]},
        tolerance=1e-6,
        maximum_iterations=100,
        solver_reported_failure=True,
    )
    assert result["status"] == "solver_reported_not_converged"
    assert result["converged"] is False


def test_convergence_uses_relative_residuals_where_a_scale_is_given():
    # A density residual of 5e-4 against a 1e12 cm^-2 sheet density is converged;
    # comparing it to a 1e-6 potential tolerance directly would be a unit error.
    result = analysis.classify_convergence(
        [1, 2], {"Residual_EDensity": [1.0, 5e-4]},
        tolerance=1e-6,
        maximum_iterations=100,
        reference_scales={"Residual_EDensity": 9.3e11},
    )
    assert result["converged"] is True
    assert result["final_relative_residuals"]["Residual_EDensity"] < 1e-6


# --- 2D helpers ------------------------------------------------------------


def _wire_density(nx: int = 61, ny: int = 41, offset: float = 0.0):
    x = np.linspace(0.0, 60.0, nx)
    y = np.linspace(0.0, 40.0, ny)
    xx, yy = np.meshgrid(x, y)
    values = np.exp(-(((xx - 30.0 - offset) / 8.0) ** 2) - (((yy - 20.0) / 4.0) ** 2))
    return x, y, values


def test_2d_normalisation_and_centroid():
    x, y, values = _wire_density()
    normalised, integral = analysis.normalise_density_2d(x, y, values)
    assert integral > 0
    mean_x, mean_y = analysis.centroid_2d(x, y, normalised)
    assert mean_x == pytest.approx(30.0, abs=1e-6)
    assert mean_y == pytest.approx(20.0, abs=1e-6)


def test_2d_symmetry_error_is_zero_for_a_centred_state_and_grows_when_shifted():
    x, y, values = _wire_density()
    assert analysis.symmetry_error(x, y, values, axis="x") < 1e-9
    x, y, shifted = _wire_density(offset=4.0)
    assert analysis.symmetry_error(x, y, shifted, axis="x") > 0.1


def test_2d_boundary_probability_is_small_for_a_confined_state():
    x, y, values = _wire_density()
    normalised, _ = analysis.normalise_density_2d(x, y, values)
    assert analysis.boundary_probability_2d(x, y, normalised) < 1e-3


def test_2d_slices_cut_through_the_centre():
    x, y, values = _wire_density()
    axis, horizontal = analysis.slice_2d(x, y, values, axis="x")
    assert axis.shape == x.shape
    assert float(axis[int(np.argmax(horizontal))]) == pytest.approx(30.0, abs=1.0)
    axis, vertical = analysis.slice_2d(x, y, values, axis="y")
    assert float(axis[int(np.argmax(vertical))]) == pytest.approx(20.0, abs=1.0)


def test_avs_field_reader_on_real_2d_output():
    """The binary .fld reader, against genuine licensed 2D output."""

    path = (
        FIXTURES
        / "demo10_wire_2d"
        / "bias_00000"
        / "Quantum"
        / "wire"
        / "Gamma"
        / "probabilities_k00000.fld"
    )
    field = outputs.read_avs_field(path)
    assert field.dims == (63, 51)
    assert len(field.variables) == 4
    assert field.labels[0].startswith("Psi^2_1")
    assert field.units[0] == "nm^-2"
    # dim1 varies fastest, so each variable is (ny, nx).
    assert field.variables[0].shape == (51, 63)
    assert field.x_nm.size == 63 and field.y_nm.size == 51
    assert float(field.x_nm[0]) == 0.0 and float(field.x_nm[-1]) == 80.0
    assert float(field.y_nm[0]) == 0.0 and float(field.y_nm[-1]) == 68.0


def test_avs_storage_order_is_fixed_by_the_normalisation_not_by_assumption():
    """(ny, nx) is the only ordering under which the density integrates to 1."""

    path = (
        FIXTURES
        / "demo10_wire_2d"
        / "bias_00000"
        / "Quantum"
        / "wire"
        / "Gamma"
        / "probabilities_k00000.fld"
    )
    field = outputs.read_avs_field(path)
    x, y = field.x_nm, field.y_nm
    correct = field.variables[0]
    assert correct.shape == (y.size, x.size)
    _, integral = analysis.normalise_density_2d(x, y, correct)
    assert integral == pytest.approx(1.0, abs=1e-9)
    # The transposed reading is not merely different, it is unnormalised.
    swapped = np.frombuffer(
        path.read_bytes(), dtype="<f8", count=x.size * y.size, offset=1645
    ).reshape((x.size, y.size)).T
    _, wrong_integral = analysis.normalise_density_2d(x, y, swapped)
    assert abs(wrong_integral - 1.0) > 0.1


def test_avs_reader_rejects_a_truncated_or_inconsistent_file(tmp_path):
    source = (
        FIXTURES
        / "demo10_wire_2d"
        / "bias_00000"
        / "Quantum"
        / "wire"
        / "Gamma"
        / "probabilities_k00000.fld"
    )
    raw = source.read_bytes()
    truncated = tmp_path / "truncated.fld"
    truncated.write_bytes(raw[:-64])
    with pytest.raises(outputs.ParserError, match="byte accounting|file is"):
        outputs.read_avs_field(truncated)


def test_band_edge_map_uses_its_own_doubled_grid():
    """Not every 2D output shares the quantum grid."""

    field = outputs.read_avs_field(
        FIXTURES / "demo10_wire_2d" / "bias_00000" / "bandedges.fld"
    )
    # 2n - 2 in each direction: interfaces are drawn sharply rather than smeared.
    assert field.dims == (124, 100)
    assert field.dims != (63, 51)
    assert field.variables[0].shape == (100, 124)


def test_2d_field_shape_mismatch_is_an_error():
    x, y, _ = _wire_density()
    with pytest.raises(analysis.AnalysisError, match="matches neither"):
        analysis.normalise_density_2d(x, y, np.zeros((3, 3)))


# ---------------------------------------------------------------------------
# nonlinear-optics proxy
# ---------------------------------------------------------------------------


def _three_level(**overrides) -> nlo.ThreeLevelInputs:
    values = {
        "E1_eV": 0.0,
        "E2_eV": 0.12,
        "E3_eV": 0.24,
        "z12_nm": 2.0,
        "z23_nm": 3.0,
        "z13_nm": 1.5,
    }
    values.update(overrides)
    return nlo.ThreeLevelInputs(**values)


def test_metric_is_the_product_over_the_detuning_denominator():
    settings = nlo.MetricSettings(target_E21_meV=120.0, detuning_floor_meV=2.0)
    result = nlo.three_level_metric(_three_level(), settings)
    assert result.matrix_element_product_nm3 == pytest.approx(9.0)
    # Perfectly on target and perfectly cascaded: both detunings hit the floor.
    assert result.detuning_denominator_meV2 == pytest.approx(4.0)
    assert result.value == pytest.approx(9.0 / 4.0)


def test_metric_units_never_read_as_a_susceptibility():
    result = nlo.three_level_metric(
        _three_level(), nlo.MetricSettings(target_E21_meV=120.0)
    )
    assert result.units == "arbitrary relative units"
    assert "pm/V" not in result.value.__class__.__name__
    for forbidden in ("chi2", "chi(2)", "pm/V", "susceptibility"):
        with pytest.raises(nlo.MetricError, match="not chi"):
            nlo.assert_not_labelled_as_chi2(f"relative {forbidden} estimate")
    # A correctly named quantity passes.
    nlo.assert_not_labelled_as_chi2(nlo.METRIC_NAME)


def test_metric_refuses_unordered_or_missing_inputs():
    settings = nlo.MetricSettings(target_E21_meV=120.0)
    unordered = nlo.three_level_metric(_three_level(E3_eV=0.05), settings)
    assert unordered.value is None
    assert "strictly ordered" in unordered.excluded_reason
    missing = nlo.three_level_metric(_three_level(z23_nm=math.nan), settings)
    assert missing.value is None
    assert "missing" in missing.excluded_reason


def test_metric_can_be_disabled():
    result = nlo.three_level_metric(
        _three_level(), nlo.MetricSettings(target_E21_meV=120.0, enabled=False)
    )
    assert result.value is None
    assert result.excluded_reason == "metric disabled in configuration"


def test_detuning_floor_prevents_an_infinite_metric():
    settings = nlo.MetricSettings(target_E21_meV=120.0, detuning_floor_meV=1.0)
    exact = nlo.three_level_metric(_three_level(), settings)
    assert math.isfinite(float(exact.value))


def test_ranking_excludes_but_never_deletes_bad_candidates():
    rows = [
        {"case_id": "good", "solver_success": True, "relative_metric": 1.0,
         "all_states_bound": True, "state_tracking_confidence": 0.9,
         "convergence_status": True, "E21_meV": 120.0},
        {"case_id": "failed", "solver_success": False, "relative_metric": 99.0,
         "all_states_bound": True, "state_tracking_confidence": 0.9,
         "convergence_status": True, "E21_meV": 120.0},
        {"case_id": "unbound", "solver_success": True, "relative_metric": 98.0,
         "all_states_bound": False, "state_tracking_confidence": 0.9,
         "convergence_status": True, "E21_meV": 120.0},
        {"case_id": "ambiguous", "solver_success": True, "relative_metric": 97.0,
         "all_states_bound": True, "state_tracking_confidence": 0.1,
         "convergence_status": True, "E21_meV": 120.0},
        {"case_id": "out_of_range", "solver_success": True, "relative_metric": 96.0,
         "all_states_bound": True, "state_tracking_confidence": 0.9,
         "convergence_status": True, "E21_meV": 5.0},
    ]
    ranked, excluded = nlo.rank_candidates(
        rows, constraints={"E21_meV": (40.0, 250.0)}
    )
    assert [row["case_id"] for row in ranked] == ["good"]
    assert len(ranked) + len(excluded) == len(rows)
    reasons = {row["case_id"]: row["exclusion_reasons"] for row in excluded}
    assert reasons["failed"] == "solver_failed"
    assert reasons["unbound"] == "states_not_bound"
    assert reasons["ambiguous"] == "state_tracking_ambiguous"
    assert reasons["out_of_range"] == "constraint_violated"


# ---------------------------------------------------------------------------
# sweeps
# ---------------------------------------------------------------------------


def _minimal_config() -> dict:
    return {
        "demo_id": "04_symmetric_double_quantum_well",
        "template": "t.j2",
        "scientific": {"center_barrier_nm": 4.0, "aluminum_fraction": 0.3},
        "numerical": {"number_of_states": 6},
    }


def test_single_variable_cases_are_unique_and_carry_the_override():
    cases = sweeps.single_variable_cases(
        _minimal_config(), "center_barrier_nm", [1.0, 2.0, 20.0]
    )
    assert len(cases) == 3
    assert len({case.case_id for case in cases}) == 3
    assert cases[2].config["scientific"]["center_barrier_nm"] == 20.0
    # The base configuration must not be mutated.
    assert _minimal_config()["scientific"]["center_barrier_nm"] == 4.0


def test_grid_cases_produce_the_full_cartesian_product():
    cases = sweeps.grid_cases(
        _minimal_config(),
        {"center_barrier_nm": [2.0, 4.0], "aluminum_fraction": [0.2, 0.3, 0.4]},
    )
    assert len(cases) == 6
    assert len({case.case_id for case in cases}) == 6


def test_expected_case_count_matches_the_generators():
    single = {"center_barrier_nm": [1.0, 2.0]}
    grid = {"center_barrier_nm": [2.0, 4.0], "aluminum_fraction": [0.2, 0.3]}
    designs = [{"name": "a", "center_barrier_nm": 3.0}]
    expected = sweeps.expected_case_count(single=single, grid=grid, designs=designs)
    produced = (
        len(sweeps.single_variable_cases(_minimal_config(), "center_barrier_nm", single["center_barrier_nm"]))
        + len(sweeps.grid_cases(_minimal_config(), grid))
        + len(sweeps.design_list_cases(_minimal_config(), designs))
    )
    assert expected == produced == 2 + 4 + 1


def test_sweeping_an_undeclared_parameter_is_refused():
    with pytest.raises(Exception, match="not declared"):
        sweeps.apply_override(_minimal_config(), "mystery_nm", 1.0)


def test_negative_sweep_values_survive_the_case_id():
    cases = sweeps.single_variable_cases(
        {
            "demo_id": "05_x",
            "scientific": {"electric_field_kV_cm": 0.0},
            "numerical": {},
        },
        "electric_field_kV_cm",
        [-100.0, 100.0],
    )
    assert cases[0].config["scientific"]["electric_field_kV_cm"] == -100.0
    assert cases[0].case_id != cases[1].case_id


def test_parameter_abbreviation_is_short_and_deterministic():
    assert sweeps.abbreviate("center_barrier_nm") == "cb"
    assert sweeps.abbreviate("quantum_region_padding_nm") == "qrp"
    assert sweeps.abbreviate("electric_field_kV_cm") == "ef"
    assert sweeps.abbreviate("donor_density_cm3") == "dd"


def test_path_budget_warns_before_windows_would_refuse(tmp_path):
    assert sweeps.check_path_budget(tmp_path) is None
    long = Path("C:/" + "a" * 200)
    warning = sweeps.check_path_budget(long)
    assert warning is not None
    assert str(sweeps.WINDOWS_MAX_PATH) in warning
    assert "results_root" in warning


def test_path_budget_matches_the_measured_solver_output_tail():
    # Calibrated on the licensed run of 2026-07-30, where Demo 9's
    # Gamma_Gamma dipole file was the artifact that crossed the limit.
    tail = "/raw_output/case/bias_00000/Quantum/cqw/Gamma_Gamma/"
    filename = "dipole_moment_matrix_elements_k00000_growth_x.txt"
    assert sweeps.SOLVER_OUTPUT_TAIL_LENGTH >= len(tail) + len(filename)
    # Demo 8 uses a longer polarization name against a shorter region name.
    longest = "/raw_output/case/bias_00000/Quantum/qw/Gamma_Gamma/"
    assert sweeps.SOLVER_OUTPUT_TAIL_LENGTH >= len(longest) + len(
        "momentum_matrix_elements_k00000_TE_inplane.txt"
    )
    assert (
        sweeps.MAX_RUN_DIR_LENGTH + sweeps.SOLVER_OUTPUT_TAIL_LENGTH
        == sweeps.WINDOWS_MAX_PATH
    )


def test_the_case_that_actually_failed_on_the_work_laptop_is_now_flagged():
    # The real failing path, verbatim from the licensed run.
    failed = Path(
        r"C:\Code\optics\nextnano\nonlinear_photonics\nextnano\results\demo_runs"
        r"\09_three_level_nonlinear_optics_sweep\20260730T210612Z_52893f32\runs"
        r"\design_02_wide_pair_"
    )
    assert sweeps.check_path_budget(failed) is not None
    # ... and the shortened identifier the generator now produces fits.
    fixed = failed.parent / "d02"
    assert sweeps.check_path_budget(fixed) is None


def test_grid_and_design_case_ids_stay_short():
    config = _minimal_config()
    grid = sweeps.grid_cases(
        config,
        {"center_barrier_nm": [2.0, 4.0], "aluminum_fraction": [0.2, 0.3, 0.4]},
    )
    designs = sweeps.design_list_cases(
        config, [{"name": "a_very_long_descriptive_design_name", "center_barrier_nm": 3.0}]
    )
    for case in [*grid, *designs]:
        assert len(case.case_id) <= 6, case.case_id
    # The descriptive name is not lost, only moved off the filesystem.
    assert designs[0].label == "a_very_long_descriptive_design_name"


# ---------------------------------------------------------------------------
# plotting must never be able to abort a run
# ---------------------------------------------------------------------------


def test_plotting_is_available_in_this_environment():
    # If this fails, the environment is broken, not the code -- but the demos
    # below must still complete.
    assert plots.plotting_available() is True
    assert plots.unavailable_reason() is None


def test_every_figure_degrades_to_a_recorded_skip(tmp_path, monkeypatch):
    """A broken matplotlib must cost figures, never the run.

    Reproduces the work-laptop failure of 2026-07-30, where a corrupt expat DLL
    made `import matplotlib.pyplot` raise inside font_manager and aborted the
    demo before a single input was generated.
    """

    monkeypatch.setattr(plots, "plt", None)
    monkeypatch.setattr(
        plots,
        "MATPLOTLIB_ERROR",
        "ImportError: DLL load failed while importing pyexpat: The handle is invalid.",
    )
    plots.reset_skipped()
    assert plots.plotting_available() is False

    target = tmp_path / "figure.png"
    assert plots.line_plot(
        target, title="t", xlabel="x", ylabel="y", series={"a": ([1.0], [2.0])}
    ) is None
    assert plots.placeholder(tmp_path / "placeholder.png", "t") is None
    assert plots.band_diagram(
        tmp_path / "band.png",
        title="t",
        position_nm=[0.0, 1.0],
        conduction_eV=[1.0, 1.0],
    ) is None
    assert not target.exists()

    status = plots.status()
    assert status["available"] is False
    assert "pyexpat" in status["unavailable_reason"]
    assert status["skipped_figure_count"] == 3
    assert "figure.png" in status["skipped_figures"]
    plots.reset_skipped()


def test_skipped_figures_are_reported_as_a_failed_criterion(tmp_path, monkeypatch):
    monkeypatch.setattr(plots, "plt", None)
    monkeypatch.setattr(plots, "MATPLOTLIB_ERROR", "ImportError: broken")
    plots.reset_skipped()
    plots.placeholder(tmp_path / "a.png", "a")

    path = sweeps.write_validation_report(
        tmp_path,
        cfg={"demo_id": "04_x", "title": "t"},
        manifest={"status": "dry_run_complete", "case_count": 1},
        registry_record=None,
        dependency_report=None,
        criteria=[("something else", True, "")],
    )
    report = path.read_text(encoding="utf-8")
    # The loss is surfaced as an explicit FAIL, not a quietly missing file.
    assert "all requested figures were produced" in report
    assert "| FAIL |" in report
    assert "Numerical results are unaffected" in report
    plots.reset_skipped()
