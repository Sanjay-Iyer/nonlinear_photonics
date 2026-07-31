"""Tests for Demo 11 and the paper's chi(2) equation.

The physics tests are the point. Eq. 2 has three properties that must hold
regardless of the structure, and each of them catches a different class of
error:

* a symmetric structure gives **identically** zero, by parity;
* the result is independent of where the z origin is placed, but only for an
  orthonormal envelope basis;
* the resonances sit at ``2*hbar*omega = E`` and ``hbar*omega = E``.

The reproduction tests then run the real paper structure through the whole
pipeline using genuine nextnano++ 3.0.0 output committed as a fixture.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

import chi2 as chi2mod
import demo_workflow as workflow
import sweeps

import demo11
import report11

DEMOS = Path(__file__).resolve().parents[1] / "demos"
DEMO11 = DEMOS / "11_paper_validation_interband_chi2_acqw"
FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "nextnano_pp_3_0_0"
    / "demo11_acqw_paper"
)

#: The reduced-grid settings the committed fixture was produced with.
FIXTURE_NUMERICS = {
    "active_region_grid_spacing_nm": 0.4,
    "exterior_grid_spacing_nm": 0.6,
    "number_of_electron_states": 2,
    "number_of_hole_states": 2,
    "quantum_region_padding_nm": 6.0,
}


def _fixture_cfg() -> dict:
    cfg = workflow.load_demo_config(DEMO11)
    cfg["numerical"].update(FIXTURE_NUMERICS)
    return cfg


def _machine_yaml(path: Path, results_root: Path) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "portable_root": None,
                "executable": None,
                "database": None,
                "license": None,
                "threads": 2,
                "run_solver": False,
                "results_root": str(results_root),
            }
        ),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Eq. 2: properties that must hold for any structure
# ---------------------------------------------------------------------------


def _well_states(z, centre, width, energies):
    columns = []
    for index in range(1, len(energies) + 1):
        psi = np.zeros_like(z)
        inside = (z >= centre - width / 2) & (z <= centre + width / 2)
        psi[inside] = np.sin(
            index * np.pi * (z[inside] - (centre - width / 2)) / width
        )
        columns.append(psi)
    return chi2mod.BandStates(z, np.asarray(energies), np.column_stack(columns))


def test_symmetric_structure_gives_identically_zero_chi2():
    """Parity forbids a second-order response in a symmetric structure.

    This is the paper's own stated limit at both ends of the asymmetry sweep,
    and it must come out as a hard zero rather than merely a small number.
    """

    z = np.linspace(-25.0, 25.0, 2001)
    electron = _well_states(z, 0.0, 10.0, [1.50, 1.56])
    hole = _well_states(z, 0.0, 10.0, [0.01, 0.04])
    spectrum = chi2mod.chi2_spectrum(
        electron, hole, np.linspace(0.6, 0.95, 51)
    )
    assert float(np.max(np.abs(spectrum.chi2))) < 1e-15


def test_asymmetric_structure_gives_a_nonzero_response():
    z = np.linspace(-25.0, 25.0, 2001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    spectrum = chi2mod.chi2_spectrum(electron, hole, np.linspace(0.6, 0.95, 51))
    assert float(np.max(np.abs(spectrum.chi2))) > 0.0


def test_chi2_is_independent_of_the_z_origin():
    """Eq. 2 contains diagonal dipoles, which individually are origin dependent.

    The dependence cancels between the two terms -- but only for orthonormal
    envelopes. Verifying it end to end confirms both the reading of Eq. 2 and
    the implementation.
    """

    z = np.linspace(-25.0, 25.0, 2001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    error = chi2mod.origin_independence_error(
        electron, hole, np.linspace(0.6, 0.95, 51), shift_nm=137.0
    )
    assert error < 1e-9


def test_non_orthonormal_envelopes_are_refused():
    z = np.linspace(-25.0, 25.0, 1001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    # Deliberately non-orthogonal: both columns overlap heavily.
    bad = chi2mod.BandStates(z, np.array([1.50, 1.56]),
                             np.column_stack([left, left + 0.5 * right]), "e")
    good = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left, right]), "hh")
    )
    with pytest.raises(chi2mod.Chi2Error, match="not orthonormal"):
        chi2mod.chi2_spectrum(bad, good, [0.8])


def test_resonances_sit_at_the_two_photon_and_one_photon_energies():
    resonances = chi2mod.resonance_wavelengths_nm([1.49, 1.62])
    assert resonances["two_photon_resonance_nm"][1] == pytest.approx(1530.7, abs=1.0)
    assert resonances["one_photon_resonance_nm"][1] == pytest.approx(765.3, abs=1.0)
    # A peak of |chi2| really lands at the two-photon resonance.
    z = np.linspace(-25.0, 25.0, 2001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    grid = np.linspace(1450.0, 1750.0, 1201)
    spectrum = chi2mod.chi2_spectrum(
        electron, hole, chi2mod.photon_energy_eV(grid)
    )
    transitions = (electron.energies_eV[:, None] - hole.energies_eV[None, :]).ravel()
    expected = [2.0 * chi2mod.HC_EV_NM / value for value in transitions]
    assert min(abs(spectrum.peak()["wavelength_nm"] - e) for e in expected) < 6.0


def test_narrower_broadening_sharpens_the_resonance():
    z = np.linspace(-25.0, 25.0, 1501)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    grid = chi2mod.photon_energy_eV(np.linspace(1450.0, 1750.0, 1501))
    broad = chi2mod.chi2_spectrum(
        electron, hole, grid, chi2mod.Chi2Settings(broadening_meV=20.0)
    )
    narrow = chi2mod.chi2_spectrum(
        electron, hole, grid, chi2mod.Chi2Settings(broadening_meV=2.0)
    )
    assert narrow.peak()["magnitude"] > broad.peak()["magnitude"]


# ---------------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------------


def test_absolute_mode_refuses_without_the_unpublished_inputs():
    with pytest.raises(chi2mod.Chi2Error, match="r_e_hh_nm"):
        chi2mod.Chi2Settings(mode="absolute")
    with pytest.raises(chi2mod.Chi2Error, match="n_wells_per_metre"):
        chi2mod.Chi2Settings(mode="absolute", r_e_hh_nm=0.3)
    # Supplying both is what unlocks it.
    settings = chi2mod.Chi2Settings(
        mode="absolute", r_e_hh_nm=0.3, n_wells_per_metre=3.33e7
    )
    assert settings.units == chi2mod.ABSOLUTE_UNITS


def test_relative_mode_never_claims_pm_per_V():
    settings = chi2mod.Chi2Settings(mode="relative")
    assert "pm/V" not in settings.units
    assert "arbitrary" in settings.units


def test_calibrated_mode_needs_a_named_source_and_fits_one_factor():
    z = np.linspace(-25.0, 25.0, 1501)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    grid = chi2mod.photon_energy_eV(np.linspace(1400.0, 1800.0, 401))
    relative = chi2mod.chi2_spectrum(electron, hole, grid)
    with pytest.raises(chi2mod.Chi2Error, match="source"):
        chi2mod.calibrate(relative, target_pm_per_V=2340.0,
                          wavelength_nm_value=1550.0, source="")
    calibrated = chi2mod.calibrate(
        relative, target_pm_per_V=2340.0, wavelength_nm_value=1550.0,
        source="paper Section 3.1",
    )
    # It hits the target exactly, by construction -- which is why the label says so.
    assert abs(calibrated.at_wavelength(1550.0)) == pytest.approx(2340.0, rel=1e-9)
    assert "calibrated" in calibrated.units
    assert "not an independent prediction" in calibrated.diagnostics["calibration_warning"]
    # Only ONE factor is fitted: the shape is untouched.
    ratio = np.abs(calibrated.chi2) / np.abs(relative.chi2)
    assert float(np.std(ratio)) < 1e-9


def test_absolute_scale_is_linear_in_Nz_and_quadratic_in_r():
    z = np.linspace(-25.0, 25.0, 1001)
    left = np.exp(-((z + 3.0) / 2.0) ** 2)
    right = np.exp(-((z - 3.0) / 1.2) ** 2)
    electron = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([1.50, 1.56]),
                           np.column_stack([left + 0.35 * right, right - 0.35 * left]), "e")
    )
    hole = chi2mod.orthonormalise(
        chi2mod.BandStates(z, np.array([0.01, 0.04]),
                           np.column_stack([left + 0.15 * right, right - 0.15 * left]), "hh")
    )
    grid = [0.8]

    def magnitude(r_nm, n_z):
        settings = chi2mod.Chi2Settings(
            mode="absolute", r_e_hh_nm=r_nm, n_wells_per_metre=n_z
        )
        return abs(chi2mod.chi2_spectrum(electron, hole, grid, settings).chi2[0])

    base = magnitude(0.3, 3.33e7)
    assert magnitude(0.3, 6.66e7) == pytest.approx(2.0 * base, rel=1e-9)
    assert magnitude(0.6, 3.33e7) == pytest.approx(4.0 * base, rel=1e-9)


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def test_asymmetry_round_trips_and_matches_the_paper():
    assert chi2mod.structural_asymmetry(7.1, 2.9) == pytest.approx(0.42)
    thick, thin = chi2mod.well_widths_from_asymmetry(0.42, 10.0)
    assert thick == pytest.approx(7.1)
    assert thin == pytest.approx(2.9)
    # The symmetric limits the paper names.
    assert chi2mod.well_widths_from_asymmetry(0.0, 10.0) == (5.0, 5.0)
    assert chi2mod.well_widths_from_asymmetry(1.0, 10.0) == (10.0, 0.0)


def test_demo11_geometry_matches_the_published_structure():
    cfg = workflow.load_demo_config(DEMO11)
    stack = demo11.build_stack(cfg)
    intervals = stack.intervals()
    assert intervals["left_well"][1] - intervals["left_well"][0] == pytest.approx(7.1)
    assert intervals["right_well"][1] - intervals["right_well"][0] == pytest.approx(2.9)
    assert (
        intervals["centre_barrier"][1] - intervals["centre_barrier"][0]
    ) == pytest.approx(1.8)
    # One period is exactly 30 nm: 10 nm of well, 1.8 nm tunnel, 18.2 nm barrier.
    assert stack.total_thickness_nm == pytest.approx(30.0)


def test_paper_targets_file_is_complete_and_sourced():
    targets = demo11.paper_targets(DEMO11)
    published = targets["targets"]
    for name in (
        "thick_well_nm", "thin_well_nm", "tunnel_barrier_nm", "aluminium_fraction",
        "ground_interband_transition_eV", "excited_interband_transition_eV",
        "simulated_resonance_nm", "chi2_ideal_abrupt_pm_per_V",
    ):
        assert name in published, name
        assert published[name].get("source"), f"{name} has no source"
        assert published[name].get("kind") in {
            "structural", "spectral", "simulated", "measured", "qualitative", "reference"
        }
    # The unpublished inputs must be recorded as such.
    missing = targets["missing_for_absolute_scale"]
    assert "r_e_hh_nm" in missing and "n_wells_per_metre" in missing


def test_demo11_deck_is_complete_and_deterministic():
    cfg = workflow.load_demo_config(DEMO11)
    template = (DEMO11 / cfg["template"]).read_text(encoding="utf-8")
    first = workflow.render_template(template, demo11.render_values(cfg))
    second = workflow.render_template(template, demo11.render_values(cfg))
    assert first == second
    assert "{{" not in first
    for expected in ("simulate1D{}", "Gamma{ num_ev", "HH{    num_ev",
                     "transition_energies{ Gamma_HH{} }",
                     "overlap_integrals{ Gamma_HH{} }",
                     "dipole_moment_matrix_elements{"):
        assert expected in first, expected


def test_graded_model_adds_linear_ramps_at_every_interface():
    cfg = workflow.load_demo_config(DEMO11)
    cfg["scientific"]["interface_grading_nm"] = 1.0
    template = (DEMO11 / cfg["template"]).read_text(encoding="utf-8")
    graded = workflow.render_template(template, demo11.render_values(cfg))
    # Count inside the structure block only; the deck header mentions the
    # keyword in a comment.
    structure = graded.split("structure{", 1)[1].split("\nclassical{", 1)[0]
    assert structure.count("ternary_linear{") == 4
    assert "alloy_x = [0.55, 0]" in structure
    assert "alloy_x = [0, 0.55]" in structure
    # The abrupt model has none.
    cfg["scientific"]["interface_grading_nm"] = 0.0
    abrupt = workflow.render_template(template, demo11.render_values(cfg))
    abrupt_structure = abrupt.split("structure{", 1)[1].split("\nclassical{", 1)[0]
    assert "ternary_linear{" not in abrupt_structure


def test_demo11_requires_two_bound_states_per_band():
    cfg = workflow.load_demo_config(DEMO11)
    cfg["numerical"]["number_of_electron_states"] = 1
    with pytest.raises(workflow.DemoError, match="two bound states"):
        demo11.render_values(cfg)


# ---------------------------------------------------------------------------
# reproduction, against real nextnano++ output for the published structure
# ---------------------------------------------------------------------------


def test_reproduces_the_published_transition_energies(tmp_path):
    """The headline physics check, on genuine solver output.

    No material parameter was adjusted to obtain this.
    """

    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, validation = demo11.analyse_case(
        _fixture_cfg(), FIXTURE, extracted, plots
    )
    # Paper: ground states separated by 1.49 eV, excited states by 1.62 eV.
    assert observables["transition_e1_hh1_eV"] == pytest.approx(1.49, abs=0.010)
    assert observables["transition_e2_hh2_eV"] == pytest.approx(1.62, abs=0.020)
    assert observables["asymmetry"] == pytest.approx(0.42)
    assert validation["envelopes_orthonormal"] is True
    assert validation["chi2_origin_independent"] is True
    assert validation["two_bound_electron_states"] is True


def test_reproduces_the_published_resonance_wavelengths(tmp_path):
    """The paper's "peaks around 760 nm and 1520 nm" are one statement."""

    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, _ = demo11.analyse_case(_fixture_cfg(), FIXTURE, extracted, plots)
    two_photon = observables["predicted_two_photon_resonances_nm"]
    one_photon = observables["predicted_one_photon_resonances_nm"]
    assert min(abs(value - 1520.0) for value in two_photon) < 15.0
    assert min(abs(value - 760.0) for value in one_photon) < 10.0
    # And the end-to-end Eq. 2 scan peaks there too, not just the bare energies.
    assert observables["chi2_peak_wavelength_nm"] == pytest.approx(1520.0, abs=25.0)


def test_states_localise_in_opposite_wells(tmp_path):
    """The coupled-well character the paper's Fig. 1c shows."""

    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, _ = demo11.analyse_case(_fixture_cfg(), FIXTURE, extracted, plots)
    assert observables["electron1_thick_well_probability"] > 0.8
    assert observables["electron2_thin_well_probability"] > 0.6
    # e1 in the thick well, e2 in the thin one -- the asymmetry is real.
    assert (
        observables["electron1_thick_well_probability"]
        > observables["electron1_thin_well_probability"]
    )
    assert (
        observables["electron2_thin_well_probability"]
        > observables["electron2_thick_well_probability"]
    )


def test_analysis_writes_the_artifacts_stage5_needs(tmp_path):
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    demo11.analyse_case(_fixture_cfg(), FIXTURE, extracted, plots)
    for name in ("envelopes.csv", "matrix_elements.json", "chi2_settings.json",
                 "chi2_focused.csv", "electron_states.csv"):
        assert (extracted / name).is_file(), name
    settings = json.loads((extracted / "chi2_settings.json").read_text(encoding="utf-8"))
    assert settings["mode"] == "relative"
    assert settings["r_e_hh_nm"] is None
    assert settings["assumptions"]


# ---------------------------------------------------------------------------
# stage plumbing and the report
# ---------------------------------------------------------------------------


def test_case_construction_covers_every_solver_stage():
    cfg = workflow.load_demo_config(DEMO11)
    cases = demo11.build_cases(cfg)
    stages = {case.metadata["stage"] for case in cases}
    assert {"stage1", "stage2", "stage3", "stage4", "stage7"} <= stages
    assert len({case.case_id for case in cases}) == len(cases)
    analysis_cfg = cfg["analysis"]
    assert sum(1 for c in cases if c.metadata["stage"] == "stage3") == len(
        analysis_cfg["asymmetry_sweep"]
    )
    assert sum(1 for c in cases if c.metadata["stage"] == "stage4") == len(
        analysis_cfg["barrier_sweep_nm"]
    )


def test_asymmetry_sweep_holds_the_total_well_thickness_fixed():
    cfg = workflow.load_demo_config(DEMO11)
    total = float(cfg["scientific"]["thick_well_nm"]) + float(
        cfg["scientific"]["thin_well_nm"]
    )
    for case in demo11.build_cases(cfg):
        if case.metadata["stage"] != "stage3":
            continue
        scientific = case.config["scientific"]
        assert (
            float(scientific["thick_well_nm"]) + float(scientific["thin_well_nm"])
        ) == pytest.approx(total)


def test_case_ids_fit_the_windows_path_budget():
    cfg = workflow.load_demo_config(DEMO11)
    work_root = Path(
        r"C:\Code\optics\nextnano\nonlinear_photonics\nextnano\results\demo_runs"
    )
    for case in demo11.build_cases(cfg):
        run_dir = (
            work_root / cfg["demo_id"] / "20260731T000000Z_deadbeef" / "runs" / case.case_id
        )
        assert sweeps.check_path_budget(run_dir) is None, case.case_id


def test_dry_run_produces_the_paper_comparison_artifacts(tmp_path):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    assert demo11.main(DEMO11, machine) == 0
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    for name in (
        "paper_comparison_report.md",
        "assumptions_and_unknowns.yaml",
        "comparison.json",
        "sweep_manifest.json",
        "validation_report.md",
    ):
        assert (parent / name).is_file(), name
    for name in ("paper_targets.csv", "our_results.csv", "comparison_metrics.csv"):
        assert (parent / "tables" / name).is_file(), name

    report = (parent / "paper_comparison_report.md").read_text(encoding="utf-8")
    # The honest headline must lead, not be buried.
    assert "not independently reproducible" in report
    assert "r_e_hh" in report
    # Nothing may be claimed as physically validated on a dry run.
    validation = (parent / "validation_report.md").read_text(encoding="utf-8")
    assert "Physically validated: **False**" in validation

    produced = {path.name for path in (parent / "plots").glob("*.png")}
    for filename, _ in demo11.PLOT_SET:
        assert filename in produced, filename


def test_report_classifies_measured_values_as_out_of_scope(tmp_path):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    demo11.main(DEMO11, machine)
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    comparison = json.loads((parent / "comparison.json").read_text(encoding="utf-8"))
    by_name = {entry["quantity"]: entry for entry in comparison["entries"]}
    # Measured multi-period values depend on band bending, standing waves, and a
    # fitted extraction parameter. They are not electronic-structure predictions.
    for name in (
        "chi2_4_period_pm_per_V",
        "chi2_80_period_pm_per_V",
        "chi2_12_and_16_period_pm_per_V",
        "chi2_growth_interrupted_pm_per_V",
    ):
        assert by_name[name]["classification"] == report11.OUT_OF_SCOPE
        assert by_name[name]["our_value"] is None
    # And the unpublished matrix element is flagged as needing the authors.
    assert (
        by_name["r_e_hh_unit_cell_matrix_element"]["classification"]
        == report11.NEEDS_AUTHORS
    )


def test_absolute_chi2_is_not_reproducible_without_the_missing_inputs(tmp_path):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    demo11.main(DEMO11, machine)
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    manifest = json.loads((parent / "sweep_manifest.json").read_text(encoding="utf-8"))
    absolute = manifest["stage5_chi2_modes"]["modes"].get("absolute", {})
    # demo.yaml leaves r_e_hh_nm and n_wells_per_metre null, so absolute mode
    # must decline rather than invent a scale.
    assert absolute.get("available") is False
    assert "r_e_hh_nm" in absolute.get("reason", "")
    assert "not independently reproducible" in manifest["absolute_scale_disclaimer"].lower() or (
        "cannot be reproduced independently" in manifest["absolute_scale_disclaimer"]
    )


def test_assumptions_file_records_every_unknown(tmp_path):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    demo11.main(DEMO11, machine)
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    data = yaml.safe_load(
        (parent / "assumptions_and_unknowns.yaml").read_text(encoding="utf-8")
    )
    unknowns = data["not_published_by_the_paper"]
    for name in ("r_e_hh_nm", "n_wells_per_metre", "k_parallel_quadrature"):
        assert name in unknowns
    assert any("k" in text and "2" in text for text in data["assumptions"])


def test_a_dry_run_never_reads_as_a_successful_reproduction(tmp_path):
    """`classification` is the kind of comparison; `outcome` is whether it ran.

    Without that split a dry run -- which computes nothing -- would report every
    structural and spectral entry as `directly_reproduced`.
    """

    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    demo11.main(DEMO11, machine)
    demo_id = workflow.load_demo_config(DEMO11)["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    comparison = json.loads((parent / "comparison.json").read_text(encoding="utf-8"))
    by_name = {entry["quantity"]: entry for entry in comparison["entries"]}

    # Nothing was solved, so every physics comparison must be pending.
    for name in (
        "ground_interband_transition",
        "excited_interband_transition",
        "focused_scan_peak_wavelength",
        "asymmetry_of_maximum_chi2",
    ):
        assert by_name[name]["outcome"] == "pending", name
        assert by_name[name]["evaluated"] is False
        assert by_name[name]["our_value"] is None

    # Structural transcription IS checkable without a solver, so it evaluates.
    assert by_name["thick_well_nm"]["outcome"] == "within_tolerance"
    assert by_name["thick_well_nm"]["evaluated"] is True

    # The summary counts only evaluated comparisons.
    summary = comparison["summary"]
    assert summary["evaluated"] == sum(
        1 for e in comparison["entries"] if e["evaluated"]
    )
    assert summary["pending"] > 0
    report = (parent / "paper_comparison_report.md").read_text(encoding="utf-8")
    assert "Pending (nothing computed yet)" in report
