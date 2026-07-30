"""Per-demo tests for Demos 4-10.

Three kinds, none needing a licence:

* **generation** — the deck a demo renders is complete, deterministic, and says
  what the configuration says;
* **real-output analysis** — Demos 4, 5, 6, and 9 are exercised against genuine
  nextnano++ 3.0.0 output committed under ``fixtures/`` (see PROVENANCE.md);
* **dry run** — the whole ``main`` produces every promised artifact with no
  solver present, and never fabricates a result.

Demos 7, 8, and 10 have no real-output fixture: the Free edition refuses strain,
k·p, and 2D execution. Their analysis is covered by generation tests and by the
shared unit tests instead, and their READMEs and registry entries say so.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

import analysis
import demo_workflow as workflow
import layers
import nlo
import outputs
import sweeps

import demo04
import demo05
import demo06
import demo07
import demo08
import demo09
import demo10

DEMOS = Path(__file__).resolve().parents[1] / "demos"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "nextnano_pp_3_0_0"

DEMO_DIRS = {
    "04": DEMOS / "04_symmetric_double_quantum_well",
    "05": DEMOS / "05_asymmetric_coupled_quantum_well_field",
    "06": DEMOS / "06_self_consistent_doped_coupled_well",
    "07": DEMOS / "07_strained_ingaas_gaas_6band",
    "08": DEMOS / "08_eight_band_interband_optics",
    "09": DEMOS / "09_three_level_nonlinear_optics_sweep",
    "10": DEMOS / "10_first_2d_quantum_confinement",
}
MODULES = {
    "04": demo04,
    "05": demo05,
    "06": demo06,
    "07": demo07,
    "08": demo08,
    "09": demo09,
    "10": demo10,
}


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


def _render(key: str, **overrides) -> str:
    cfg = workflow.load_demo_config(DEMO_DIRS[key])
    for section, values in overrides.items():
        cfg[section].update(values)
    template = (DEMO_DIRS[key] / cfg["template"]).read_text(encoding="utf-8")
    return workflow.render_template(template, MODULES[key].render_values(cfg))


def _active_deck(deck: str) -> str:
    """Remove full-line comments before asserting which physics is enabled."""

    return "\n".join(
        line for line in deck.splitlines() if not line.lstrip().startswith("#")
    )


def _has_block(deck: str, name: str) -> bool:
    return any(line.strip() == f"{name}{{" for line in deck.splitlines())


# ---------------------------------------------------------------------------
# generation: shared expectations for every new demo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", sorted(DEMO_DIRS))
def test_demo_yaml_is_strictly_valid(key):
    cfg = workflow.load_demo_config(DEMO_DIRS[key])
    assert cfg["demo_id"].startswith(key)
    assert (DEMO_DIRS[key] / cfg["template"]).is_file()


@pytest.mark.parametrize("key", sorted(DEMO_DIRS))
def test_rendered_deck_is_complete_and_deterministic(key):
    first = _render(key)
    second = _render(key)
    assert first == second
    assert "{{" not in first and "}}" not in first
    for block in ("global{", "contacts{", "structure{", "grid{", "classical{", "run{"):
        assert block in first, f"{key}: rendered deck is missing {block}"


@pytest.mark.parametrize("key", sorted(DEMO_DIRS))
def test_rendered_deck_loads_as_a_nextnano_input(tmp_path, key):
    nn = pytest.importorskip("nextnanopy")
    deck = tmp_path / f"{key}.in"
    deck.write_text(_render(key), encoding="utf-8")
    assert nn.InputFile(str(deck)).product == "nextnano++"


@pytest.mark.parametrize("key", sorted(DEMO_DIRS))
def test_every_demo_has_a_readme_and_a_runner(key):
    assert (DEMO_DIRS[key] / "README.md").is_file()
    assert (DEMO_DIRS[key] / "run.py").is_file()
    assert (DEMO_DIRS[key] / "__main__.py").is_file()


# ---------------------------------------------------------------------------
# Demo 4
# ---------------------------------------------------------------------------


def test_demo4_geometry_matches_the_yaml():
    cfg = workflow.load_demo_config(DEMO_DIRS["04"])
    stack = demo04.build_stack(cfg)
    well = float(cfg["scientific"]["well_width_nm"])
    barrier = float(cfg["scientific"]["center_barrier_nm"])
    left = stack.interval("left_well")
    right = stack.interval("right_well")
    assert left[1] - left[0] == pytest.approx(well)
    assert right[1] - right[0] == pytest.approx(well)
    assert stack.interval("centre_barrier")[1] - stack.interval("centre_barrier")[0] == (
        pytest.approx(barrier)
    )


def test_demo4_deck_contains_both_wells_and_no_forbidden_physics():
    deck = _render("04")
    assert deck.count('binary{ name = "GaAs" }') == 2
    assert "# left_well" in deck and "# right_well" in deck
    for forbidden in ("poisson{", "impurities{", "strain{", "kp_6band", "kp_8band"):
        assert forbidden not in deck, f"Demo 4 must not enable {forbidden}"
    assert "run{\n    quantum{}\n}" in deck


def test_demo4_barrier_sweep_moves_the_wells_but_keeps_them_identical():
    cfg = workflow.load_demo_config(DEMO_DIRS["04"])
    for barrier in (1.0, 20.0):
        modified = sweeps.apply_override(cfg, "center_barrier_nm", barrier)
        stack = demo04.build_stack(modified)
        left = stack.interval("left_well")
        right = stack.interval("right_well")
        assert (left[1] - left[0]) == pytest.approx(right[1] - right[0])
        assert stack.interval("centre_barrier")[1] - stack.interval(
            "centre_barrier"
        )[0] == pytest.approx(barrier)


def test_demo4_analysis_on_real_solver_output(tmp_path):
    cfg = workflow.load_demo_config(DEMO_DIRS["04"])
    cfg["numerical"].update(
        active_region_grid_spacing_nm=1.0,
        exterior_grid_spacing_nm=1.0,
        number_of_states=4,
        quantum_region_padding_nm=10.0,
    )
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, validation = demo04.analyse_case(
        cfg, FIXTURES / "demo04_symmetric_dqw", extracted, plots
    )
    # Two identical wells: the lowest pair must be balanced and have definite,
    # opposite parity. Neither is inferred from the state index.
    assert observables["parity_state1"] == "symmetric"
    assert observables["parity_state2"] == "antisymmetric"
    assert observables["maximum_well_imbalance"] < 1e-6
    assert observables["E21_meV"] > 0
    assert observables["centroid_state1_nm"] == pytest.approx(
        observables["structure_centre_nm"], abs=0.1
    )
    # Orthogonality of distinct eigenstates.
    assert abs(observables["overlap_state1_state2"]) < 1e-6
    assert validation["lowest_pair_is_symmetric_then_antisymmetric"] is True
    assert validation["lowest_pair_balanced_between_identical_wells"] is True
    assert validation["lowest_pair_boundary_probability_small"] is True
    assert validation["completion_marker_found"] is True
    assert (extracted / "states.csv").is_file()
    assert (extracted / "band_profile.csv").is_file()
    assert (extracted / "envelopes.csv").is_file()
    assert (extracted / "probability_densities.csv").is_file()
    assert (plots / "wavefunctions.png").is_file()
    assert (plots / "probability_densities.png").is_file()


def test_demo4_splitting_table_and_tracking_survive_missing_solver_data():
    # A dry run has no observables at all; the tracking must say so rather than
    # inventing an assignment.
    empty = sweeps.CaseResult(
        spec=sweeps.CaseSpec("c1", "c1", {"center_barrier_nm": 1.0}, {}),
        run_dir=Path("."),
        status="skipped_no_solver",
    )
    rows = demo04.track_across_sweep([empty], 0.6)
    assert rows[0]["tracking_available"] is False


# ---------------------------------------------------------------------------
# Demo 5
# ---------------------------------------------------------------------------


def test_demo5_field_unit_conversion_is_the_measured_one():
    # Measured at home: strength = 1e7 V/m produced 100 kV/cm.
    import quantum1d

    assert quantum1d.kv_per_cm_to_volts_per_metre(100.0) == pytest.approx(1.0e7)
    assert quantum1d.kv_per_cm_to_volts_per_metre(-50.0) == pytest.approx(-5.0e6)


def test_demo5_field_sign_and_direction_reach_the_deck():
    positive = _render("05", scientific={"electric_field_kV_cm": 50.0})
    assert "strength  = 5000000" in positive
    assert "direction = [1, 0, 0]" in positive
    negative = _render("05", scientific={"electric_field_kV_cm": -50.0})
    assert "strength  = -5000000" in negative
    reversed_direction = _render(
        "05", scientific={"electric_field_kV_cm": 50.0, "field_direction": "-x"}
    )
    assert "direction = [-1, 0, 0]" in reversed_direction


def test_demo5_rejects_an_unknown_field_direction():
    cfg = workflow.load_demo_config(DEMO_DIRS["05"])
    cfg["scientific"]["field_direction"] = "sideways"
    with pytest.raises(workflow.DemoError, match="field_direction"):
        demo05.render_values(cfg)


def test_demo5_run_block_has_no_poisson_step():
    # With poisson{} in run{} the solver replaces the imposed tilt with the
    # contact-pinned solution. Measured at home; this guards the regression.
    deck = _render("05")
    assert "poisson{" in deck  # the block that DEFINES the field
    run_block = deck.split("run{")[-1]
    assert "poisson{}" not in run_block
    assert "quantum{}" in run_block


def test_demo5_contact_is_a_slab_not_the_whole_domain():
    deck = _render("05")
    fill = deck.split("# Mandatory contact")[0]
    assert "everywhere{}" in fill
    assert "contact{ name = qw_contact }" not in fill


def test_demo5_field_sweep_generates_both_polarities():
    cfg = workflow.load_demo_config(DEMO_DIRS["05"])
    values = cfg["sweeps"]["electric_field_kV_cm"]
    cases = sweeps.single_variable_cases(cfg, "electric_field_kV_cm", values)
    fields = [case.config["scientific"]["electric_field_kV_cm"] for case in cases]
    assert min(fields) < 0 < max(fields)
    assert 0.0 in fields
    assert len({case.case_id for case in cases}) == len(cases)


def test_demo5_analysis_on_real_solver_output(tmp_path):
    cfg = workflow.load_demo_config(DEMO_DIRS["05"])
    cfg["numerical"].update(
        active_region_grid_spacing_nm=1.0,
        exterior_grid_spacing_nm=1.0,
        number_of_states=4,
        quantum_region_padding_nm=10.0,
    )
    cfg["scientific"]["electric_field_kV_cm"] = 50.0
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, validation = demo05.analyse_case(
        cfg, FIXTURES / "demo05_field_cqw", extracted, plots
    )
    # Three independent routes to the field must agree.
    assert observables["measured_field_kV_cm"] == pytest.approx(50.0, rel=1e-6)
    assert observables["field_from_potential_slope_kV_cm"] == pytest.approx(50.0, rel=1e-6)
    # Positive field along +x tilts the conduction band upward with x, and the
    # slope is eF: 50 kV/cm = 5e-3 eV/nm.
    assert observables["conduction_band_tilt_eV_per_nm"] == pytest.approx(5.0e-3, rel=0.05)
    assert validation["solver_field_matches_request"] is True
    assert validation["potential_slope_matches_request"] is True
    assert validation["band_tilt_sign_matches_convention"] is True
    assert validation["lowest_pair_boundary_probability_small"] is True
    # Field-induced localisation: the two states sit in different wells.
    assert observables["probability_wide_well_state1"] > 0.8
    assert observables["probability_narrow_well_state2"] > 0.6
    assert (extracted / "band_profile.csv").is_file()
    assert (extracted / "envelopes.csv").is_file()
    assert (extracted / "probability_densities.csv").is_file()
    assert (extracted / "potential.csv").is_file()
    assert (extracted / "electric_field.csv").is_file()


def test_demo5_tracking_uses_envelope_overlap_and_flags_ambiguity(tmp_path):
    # Two field points whose envelopes are the same states in swapped order.
    x = np.linspace(0.0, 40.0, 201)
    a = np.exp(-(((x - 15.0) / 3.0) ** 2))
    b = np.exp(-(((x - 25.0) / 3.0) ** 2))
    results = []
    for index, columns in enumerate(([a, b], [b, a])):
        run_dir = tmp_path / f"case{index}"
        (run_dir / "extracted").mkdir(parents=True)
        np.savetxt(
            run_dir / "extracted" / "envelopes.csv",
            np.column_stack([x, *columns]),
            delimiter=",",
            header="position_nm,psi_1,psi_2",
            comments="",
        )
        result = sweeps.CaseResult(
            spec=sweeps.CaseSpec(
                f"c{index}", f"c{index}", {"electric_field_kV_cm": float(index)}, {}
            ),
            run_dir=run_dir,
            status="completed",
            observables={
                "electron_energies_eV": [1.0, 1.1],
                "state_rows": [
                    {
                        "energy_eV": 1.0,
                        "centroid_nm": 15.0,
                        "probability_left_well": 0.9,
                        "probability_right_well": 0.1,
                    },
                    {
                        "energy_eV": 1.1,
                        "centroid_nm": 25.0,
                        "probability_left_well": 0.1,
                        "probability_right_well": 0.9,
                    },
                ],
            },
        )
        results.append(result)
    rows, branches = demo05.track_across_field(results, 0.6)
    assert rows[1]["assignment"] == "2;1"
    assert rows[1]["is_confident"] is True
    assert rows[1]["solver_state_to_branch"] == [1, 0]
    assert np.asarray(rows[1]["overlap_matrix"]).shape == (2, 2)
    assert len(branches) == 2
    tracked = demo05.tracked_state_rows(results, rows)
    second_field = [row for row in tracked if row["electric_field_kV_cm"] == 1.0]
    assert second_field[0]["branch"] == 2
    assert second_field[1]["branch"] == 1


def test_demo5_avoided_crossing_flags_use_the_configured_thresholds():
    cfg = workflow.load_demo_config(DEMO_DIRS["05"])
    settings = cfg["analysis"]
    fields = np.linspace(-40.0, 40.0, 17)
    gap = np.sqrt((fields / 8.0) ** 2 + 0.25) / 1000.0
    flags = analysis.detect_avoided_crossings(
        fields,
        np.column_stack([-gap / 2, gap / 2]),
        minimum_gap_meV=float(settings["avoided_crossing_minimum_gap_meV"]),
        relative_curvature=float(settings["avoided_crossing_relative_curvature"]),
    )
    assert flags
    assert flags[0]["parameter_value"] == pytest.approx(0.0, abs=5.0)


# ---------------------------------------------------------------------------
# Demo 6
# ---------------------------------------------------------------------------


def test_demo6_stage_decks_enable_exactly_one_new_mechanism_each():
    cfg = workflow.load_demo_config(DEMO_DIRS["06"])
    decks = {}
    for model in cfg["models"]:
        staged = sweeps.copy_config(cfg)
        staged["models"] = [model]
        decks[model["name"]] = workflow.render_template(
            (DEMO_DIRS["06"] / cfg["template"]).read_text(encoding="utf-8"),
            demo06.render_values(staged),
        )
    a = _active_deck(decks["A_undoped_no_poisson"])
    b = _active_deck(decks["B_doped_classical_poisson"])
    c = _active_deck(decks["C_quantum_on_poisson_potential"])
    d = _active_deck(decks["D_self_consistent"])

    assert not _has_block(a, "impurities")
    assert not _has_block(a, "poisson")
    assert _has_block(a, "quantum")
    assert _has_block(b, "impurities")
    assert _has_block(b, "poisson")
    assert not _has_block(b, "quantum")
    assert "run{\n    poisson{}\n    quantum{}\n}" in c
    assert "no_density = yes" in c
    assert "quantum_poisson{" in d
    assert "no_density" not in d.split("quantum{")[-1]
    assert "output_quantum_densities{}" in d


def test_demo6_doping_region_reaches_the_deck_with_the_right_species():
    cfg = workflow.load_demo_config(DEMO_DIRS["06"])
    staged = sweeps.copy_config(cfg)
    staged["models"] = [
        model for model in cfg["models"] if model["name"] == "D_self_consistent"
    ]
    deck = workflow.render_template(
        (DEMO_DIRS["06"] / cfg["template"]).read_text(encoding="utf-8"),
        demo06.render_values(staged),
    )
    start = cfg["scientific"]["donor_region_start_nm"]
    end = cfg["scientific"]["donor_region_end_nm"]
    assert f"line{{ x = [{start:.9g}, {end:.9g}] }}" in deck
    assert 'doping{ constant{ name = "si_donor"' in deck
    assert 'donor{ name = "si_donor"' in deck


def test_demo6_rejects_a_donor_layer_that_overlaps_a_well():
    cfg = workflow.load_demo_config(DEMO_DIRS["06"])
    cfg["scientific"]["donor_region_end_nm"] = 31.0  # first well starts at 30 nm
    with pytest.raises(workflow.DemoError, match="overlaps the first well"):
        demo06.check_doping_geometry(cfg)


def test_demo6_rejects_a_spacer_that_disagrees_with_the_geometry():
    cfg = workflow.load_demo_config(DEMO_DIRS["06"])
    cfg["scientific"]["spacer_thickness_nm"] = 3.0
    with pytest.raises(workflow.DemoError, match="spacer_thickness_nm"):
        demo06.check_doping_geometry(cfg)


def test_demo6_doping_sweep_stays_in_the_documented_range():
    cfg = workflow.load_demo_config(DEMO_DIRS["06"])
    values = cfg["sweeps"]["donor_density_cm3"]
    # The basis recorded in demo.yaml is the vendor examples' 1e18-1e19 band.
    assert min(values) >= 1.0e17
    assert max(values) <= 2.0e19


def test_demo6_analysis_on_real_non_converged_run(tmp_path):
    cfg = workflow.load_demo_config(DEMO_DIRS["06"])
    cfg["numerical"].update(
        active_region_grid_spacing_nm=1.0,
        exterior_grid_spacing_nm=1.0,
        number_of_states=4,
        quantum_region_padding_nm=10.0,
    )
    cfg["models"] = [
        model for model in cfg["models"] if model["name"] == "D_self_consistent"
    ]
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, validation = demo06.analyse_case(
        cfg, FIXTURES / "demo06_doped_scf", extracted, plots
    )
    # The solver exited successfully AND warned that it had not converged.
    assert validation["completion_marker_found"] is True
    assert validation["job_done_file_present"] is True
    assert validation["no_convergence_warning"] is False
    assert observables["convergence_state"] == "solver_reported_not_converged"
    assert validation["self_consistent_loop_converged"] is False
    # Charge balance and band bending are still measured and reported.
    assert observables["relative_charge_imbalance"] < 1e-6
    assert observables["conduction_band_bending_meV"] > 1.0
    assert observables["occupied_subband_count"] >= 1
    assert observables["electron_fermi_level_eV"] == pytest.approx(0.0)
    assert (extracted / "fermi_levels.csv").is_file()
    assert (extracted / "designed_donor_density.csv").is_file()
    assert (extracted / "iteration_history.csv").is_file()
    assert (extracted / "convergence.json").is_file()


def test_demo6_iteration_history_columns_are_read_by_name():
    table = outputs.read_table(
        FIXTURES / "demo06_doped_scf" / "bias_00000" / "iteration_quantum_poisson.dat"
    )
    names = [name for name, _ in table.header]
    assert names[0] == "Iteration"
    assert "Residual_Potential" in names
    assert "Residual_EDensity" in names
    units = {name: unit for name, unit in table.header}
    assert units["Residual_Potential"] == "V"


# ---------------------------------------------------------------------------
# Demo 7
# ---------------------------------------------------------------------------


def _demo7_deck(model_name: str) -> str:
    cfg = workflow.load_demo_config(DEMO_DIRS["07"])
    staged = sweeps.copy_config(cfg)
    staged["models"] = [m for m in cfg["models"] if m["name"] == model_name]
    return workflow.render_template(
        (DEMO_DIRS["07"] / cfg["template"]).read_text(encoding="utf-8"),
        demo07.render_values(staged),
    )


def test_demo7_strain_toggle_is_explicit_in_both_directions():
    baseline = _demo7_deck("M1_classical_unstrained")
    strained = _demo7_deck("M2_classical_strained")
    assert "no_strain{}" in baseline
    assert "pseudomorphic_strain{}" not in baseline
    assert "strain{}" not in baseline.split("run{")[-1]
    assert "pseudomorphic_strain{}" in strained
    assert "strain{}" in strained.split("run{")[-1]


def test_demo7_valence_model_selection():
    one_band = _active_deck(_demo7_deck("M3_oneband_electron_hh"))
    six_band = _active_deck(_demo7_deck("M4_sixband_valence"))
    assert "HH{ num_ev" in one_band and "kp_6band" not in one_band
    assert "kp_6band{" in six_band and "HH{ num_ev" not in six_band
    # Component weights are the whole point of the 6-band stage.
    assert "spinor_composition" in six_band
    assert "spinor_composition" not in one_band


def test_demo7_uses_ingaas_on_a_gaas_substrate():
    deck = _demo7_deck("M2_classical_strained")
    assert 'substrate{ name = "GaAs" }' in deck
    assert 'name    = "In(x)Ga(1-x)As"' in deck
    assert deck.count('binary{ name = "GaAs" }') == 2  # the two barriers


def test_demo7_mixed_states_are_not_given_a_single_band_name():
    label, fraction = analysis.classify_character(
        {"HH": 0.52, "LH": 0.45, "SO": 0.03},
        dominant_threshold=float(
            workflow.load_demo_config(DEMO_DIRS["07"])["analysis"][
                "character_dominant_threshold"
            ]
        ),
    )
    assert label == "mixed"
    assert fraction == pytest.approx(0.52)


def test_demo7_hole_spectrum_order_is_preserved_not_sorted():
    # nextnano++ lists hole states with DECREASING energy; sorting them would
    # silently relabel physical states.
    descending = np.asarray([1.45, 1.42, 1.39])
    path = FIXTURES / "demo04_symmetric_dqw" / "bias_00000" / "Quantum" / "dqw" / "Gamma"
    _, energies = outputs.read_state_table(path / "energy_spectrum_k00000.dat")
    assert np.all(np.diff(energies) > 0)  # electrons ascend
    # read_state_table must not reorder whatever it is given.
    assert list(descending) == sorted(descending, reverse=True)


# ---------------------------------------------------------------------------
# Demo 8
# ---------------------------------------------------------------------------


def _demo8_deck(model_name: str, **overrides) -> str:
    cfg = workflow.load_demo_config(DEMO_DIRS["08"])
    for section, values in overrides.items():
        cfg[section].update(values)
    staged = sweeps.copy_config(cfg)
    staged["models"] = [m for m in cfg["models"] if m["name"] == model_name]
    return workflow.render_template(
        (DEMO_DIRS["08"] / cfg["template"]).read_text(encoding="utf-8"),
        demo08.render_values(staged),
    )


def test_demo8_model_progression_reaches_the_deck():
    one_band = _active_deck(_demo8_deck("M1_oneband_e_h"))
    six_band = _active_deck(_demo8_deck("M2_sixband_valence"))
    eight_band = _active_deck(_demo8_deck("M3_eightband_zone_centre"))
    k_resolved = _active_deck(_demo8_deck("M4_eightband_k_resolved"))
    assert "kp_8band" not in one_band and "Gamma_HH{}" in one_band
    assert "kp_6band{" in six_band
    assert "kp_8band{" in eight_band
    assert "k_integration_disabled{}" in eight_band
    assert "k_integration{" in k_resolved and "k_integration_disabled" not in k_resolved


def test_demo8_polarizations_are_named_and_labelled():
    deck = _demo8_deck("M4_eightband_k_resolved")
    assert 'polarization{ name = "TM_growth"  re = [1, 0, 0] }' in deck
    assert 'polarization{ name = "TE_inplane"  re = [0, 1, 0] }' in deck
    assert "output_oscillator_strengths = yes" in deck
    assert "optics{" in deck
    assert "quantum_spectra{" in deck
    assert "enable_electron_hole = yes" in deck
    assert "absorption_coeff = yes" in deck
    assert "energy_broadening_lorentzian = 0.008" in deck
    assert "run{\n    strain{}\n    quantum{}\n    optics{}" in deck


def test_demo8_non_kp8_stages_do_not_request_quantum_spectra():
    one_band = _active_deck(_demo8_deck("M1_oneband_e_h"))
    six_band = _active_deck(_demo8_deck("M2_sixband_valence"))
    assert "quantum_spectra" not in one_band
    assert "quantum_spectra" not in six_band
    assert "\n    optics{}\n" not in one_band
    assert "\n    optics{}\n" not in six_band


def test_demo8_licensed_300_headers_resolve_units_and_real_directory_case():
    root = FIXTURES / "demo08_licensed_headers"
    profile = outputs.load_profile("nextnano_pp_3_0_0")
    resolved = outputs.resolve_outputs(
        profile,
        root,
        [
            "transition_energies_gamma_hh",
            "transition_energies_gamma_kp6",
            "overlap_integrals_gamma_kp6",
            "transition_energies_kp8",
            "momentum_matrix_elements_kp8",
        ],
        substitutions={"region": "qw", "polarization": "TM_growth"},
    )
    kp6_path = resolved.one("transition_energies_gamma_kp6")
    assert kp6_path.parent.name == "Gamma_kp6"
    for key in (
        "transition_energies_gamma_hh",
        "transition_energies_gamma_kp6",
        "transition_energies_kp8",
    ):
        path = resolved.one(key)
        elements = outputs.read_matrix_elements(path)
        energy_column = outputs.value_column_with_unit(path, unit="eV")
        assert energy_column in next(iter(elements.values()))
        assert "[eV]" not in energy_column
    momentum_path = resolved.one("momentum_matrix_elements_kp8")
    assert outputs.magnitude_column(momentum_path, unit="hbar/nm").startswith("|<")


def test_demo8_licensed_kp8_all_pairs_require_absorption_orientation():
    root = (
        FIXTURES
        / "demo08_licensed_headers"
        / "bias_00000"
        / "Quantum"
        / "qw"
        / "kp8_kp8"
    )
    transitions_path = root / "transition_energies_k00000.txt"
    transitions = outputs.read_matrix_elements(transitions_path)
    energy_column = outputs.value_column_with_unit(transitions_path, unit="eV")
    strengths = outputs.read_matrix_elements(
        root / "oscillator_strengths_k00000_TM_growth.txt"
    )
    strength_column = outputs.first_value_column(strengths, contains="f(")
    assert transitions[(7, 1)][energy_column] == pytest.approx(1.29471)
    assert transitions[(1, 7)][energy_column] == pytest.approx(-1.29471)
    # For absorption the initial valence state is first. The reverse row has
    # the opposite sign and must not be used as a positive absorption strength.
    assert strengths[(1, 7)][strength_column] > 0.0
    assert strengths[(7, 1)][strength_column] < 0.0


def test_demo8_symmetry_breaking_adds_a_higher_indium_step():
    cfg = workflow.load_demo_config(DEMO_DIRS["08"])
    symmetric = demo08.build_stack(cfg, symmetry_broken=False)
    broken = demo08.build_stack(cfg, symmetry_broken=True)
    assert "well_step" not in symmetric.intervals()
    assert "well_step" in broken.intervals()
    # Total well thickness is preserved; only its composition profile changes.
    step = broken.interval("well_step")
    well = broken.interval("well")
    assert (step[1] - step[0]) + (well[1] - well[0]) == pytest.approx(
        float(cfg["scientific"]["well_width_nm"])
    )


def test_demo8_field_uses_the_measured_unit():
    deck = _demo8_deck("M4_eightband_k_resolved", scientific={"electric_field_kV_cm": 25.0})
    assert "strength  = 2500000" in deck
    zero = _active_deck(
        _demo8_deck(
            "M4_eightband_k_resolved",
            scientific={"electric_field_kV_cm": 0.0},
        )
    )
    assert "poisson{" not in zero


def test_demo8_spectrum_is_a_lorentzian_sum_with_the_configured_broadening():
    grid, spectrum = demo08.lorentzian_spectrum(
        [1.40, 1.50],
        [1.0, 0.5],
        minimum_eV=1.30,
        maximum_eV=1.60,
        points=3001,
        broadening_meV=5.0,
    )
    peak_index = int(np.argmax(spectrum))
    assert grid[peak_index] == pytest.approx(1.40, abs=2e-3)
    # FWHM is 5 meV, so the half-maximum lies 2.5 meV from line centre.
    at_centre = float(np.interp(1.40, grid, spectrum))
    at_hwhm = float(np.interp(1.4025, grid, spectrum))
    assert at_hwhm == pytest.approx(0.5 * at_centre, rel=0.05)
    # Strength ratio survives.
    assert float(np.interp(1.50, grid, spectrum)) == pytest.approx(
        0.5 * at_centre, rel=0.1
    )


def test_demo8_spectrum_rejects_invalid_broadening_or_range():
    with pytest.raises(workflow.DemoError, match="broadening"):
        demo08.lorentzian_spectrum([1.4], [1.0], minimum_eV=1.0, maximum_eV=1.8,
                                   points=101, broadening_meV=0.0)
    with pytest.raises(workflow.DemoError, match="spectral_energy_max_eV"):
        demo08.lorentzian_spectrum([1.4], [1.0], minimum_eV=1.8, maximum_eV=1.0,
                                   points=101, broadening_meV=5.0)


def test_demo8_momentum_and_dipole_units_are_kept_apart():
    base = FIXTURES / "demo09_dipole" / "bias_00000" / "Quantum" / "cqw" / "Gamma_Gamma"
    dipole_units = outputs.matrix_element_units(
        base / "dipole_moment_matrix_elements_k00000_growth_x.txt"
    )
    momentum_units = outputs.matrix_element_units(
        base / "momentum_matrix_elements_k00000_growth_x.txt"
    )
    assert "e*nm" in dipole_units.values()
    assert "hbar/nm" in momentum_units.values()
    assert set(dipole_units.values()).isdisjoint(momentum_units.values())


def test_demo8_intersubband_selection_rule_holds_in_real_output():
    # Growth-polarised intersubband transitions are allowed; in-plane ones are
    # not. Confirmed against real nextnano++ output.
    path = (
        FIXTURES
        / "demo09_dipole"
        / "bias_00000"
        / "Quantum"
        / "cqw"
        / "Gamma_Gamma"
        / "oscillator_strengths_k00000_growth_x.txt"
    )
    elements = outputs.read_matrix_elements(path)
    column = outputs.first_value_column(elements, contains="f(")
    assert abs(elements[(1, 2)][column]) > 1e-3
    assert abs(elements[(1, 1)][column]) < 1e-9


# ---------------------------------------------------------------------------
# Demo 9
# ---------------------------------------------------------------------------


def test_demo9_case_generation_matches_the_declared_count():
    cfg = workflow.load_demo_config(DEMO_DIRS["09"])
    sweep_cfg = cfg["sweeps"]
    analysis_cfg = cfg["analysis"]
    expected = sweeps.expected_case_count(
        single={
            "center_barrier_nm": sweep_cfg["center_barrier_nm"],
            "electric_field_kV_cm": sweep_cfg["electric_field_kV_cm"],
        },
        grid=analysis_cfg["grid_axes"],
        designs=analysis_cfg["designs"],
    )
    produced = (
        len(sweeps.single_variable_cases(cfg, "center_barrier_nm", sweep_cfg["center_barrier_nm"]))
        + len(sweeps.single_variable_cases(cfg, "electric_field_kV_cm", sweep_cfg["electric_field_kV_cm"], prefix="f_"))
        + len(sweeps.grid_cases(cfg, analysis_cfg["grid_axes"]))
        + len(sweeps.design_list_cases(cfg, analysis_cfg["designs"]))
    )
    assert produced == expected == 5 + 5 + 9 + 3


def test_demo9_design_list_applies_every_named_override():
    cfg = workflow.load_demo_config(DEMO_DIRS["09"])
    cases = sweeps.design_list_cases(cfg, cfg["analysis"]["designs"])
    first = next(case for case in cases if case.label == "thin_barrier_detuned")
    assert first.config["scientific"]["center_barrier_nm"] == 2.0
    assert first.config["scientific"]["narrow_well_width_nm"] == 4.5
    assert first.config["scientific"]["electric_field_kV_cm"] == 15.0


def test_demo9_requires_at_least_three_states():
    cfg = workflow.load_demo_config(DEMO_DIRS["09"])
    cfg["numerical"]["number_of_states"] = 2
    with pytest.raises(workflow.DemoError, match="three-level"):
        demo09.render_values(cfg)


def test_demo9_deck_requests_dipole_matrix_elements_along_growth():
    deck = _render("09")
    assert "dipole_moment_matrix_elements{" in deck
    assert 'polarization{ name = "growth_x"  re = [1, 0, 0] }' in deck


def test_demo9_analysis_on_real_solver_output(tmp_path):
    cfg = workflow.load_demo_config(DEMO_DIRS["09"])
    cfg["numerical"].update(
        active_region_grid_spacing_nm=1.0,
        exterior_grid_spacing_nm=1.0,
        number_of_states=4,
        quantum_region_padding_nm=10.0,
    )
    cfg["scientific"]["electric_field_kV_cm"] = 20.0
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, validation = demo09.analyse_case(
        cfg, FIXTURES / "demo09_dipole", extracted, plots
    )
    # Two independent routes to z_ij must agree.
    cross_check = observables["matrix_element_cross_check"]
    assert cross_check["compared"] is True
    assert cross_check["max_absolute_difference_nm"] < 1e-4
    assert validation["dipole_sources_agree"] is True
    assert observables["z_source"] == "solver_dipole"
    assert validation["three_bound_states"] is True
    # The metric is present, finite, and correctly labelled.
    assert observables["relative_metric"] > 0
    assert observables["metric_name"] == nlo.METRIC_NAME
    assert observables["metric_units"] == "arbitrary relative units"
    assert (extracted / "metric.json").is_file()
    assert (extracted / "matrix_elements.json").is_file()


def test_demo9_metric_is_never_presented_as_a_susceptibility(tmp_path):
    cfg = workflow.load_demo_config(DEMO_DIRS["09"])
    cfg["numerical"].update(
        active_region_grid_spacing_nm=1.0,
        exterior_grid_spacing_nm=1.0,
        number_of_states=4,
        quantum_region_padding_nm=10.0,
    )
    cfg["scientific"]["electric_field_kV_cm"] = 20.0
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, _ = demo09.analyse_case(cfg, FIXTURES / "demo09_dipole", extracted, plots)
    encoded = json.dumps(observables, default=str).lower()
    assert "pm/v" not in encoded
    metric = json.loads((extracted / "metric.json").read_text(encoding="utf-8"))
    nlo.assert_not_labelled_as_chi2(metric["metric_name"])
    assert any("not chi" in text.lower() or "arbitrary" in text.lower()
               for text in metric["assumptions"])


def test_demo9_metric_can_be_disabled_from_yaml(tmp_path):
    cfg = workflow.load_demo_config(DEMO_DIRS["09"])
    cfg["metric"]["enabled"] = False
    settings = demo09.metric_settings(cfg)
    assert settings.enabled is False
    result = nlo.three_level_metric(
        nlo.ThreeLevelInputs(0.0, 0.1, 0.2, 1.0, 1.0, 1.0), settings
    )
    assert result.value is None


def test_demo9_top_candidate_rerun_selection_skips_excluded_candidates():
    rows = [
        {"case_id": "bad", "solver_success": False, "relative_metric": 10.0},
        {"case_id": "good", "solver_success": True, "relative_metric": 1.0,
         "all_states_bound": True, "convergence_status": True},
    ]
    ranked, excluded = nlo.rank_candidates(rows)
    assert [row["case_id"] for row in ranked[:1]] == ["good"]
    assert [row["case_id"] for row in excluded] == ["bad"]


# ---------------------------------------------------------------------------
# Demo 10
# ---------------------------------------------------------------------------


def test_demo10_2d_regions_and_grids_reach_the_deck():
    deck = _active_deck(_render("10"))
    assert "simulate2D{}" in deck
    assert "ygrid{" in deck
    assert "rectangle{" in deck
    assert "boundary{ x = dirichlet  y = dirichlet }" in deck
    assert deck.count("rectangle{") == 2  # matrix and core


def test_demo10_core_sits_inside_the_matrix():
    cfg = workflow.load_demo_config(DEMO_DIRS["10"])
    wire = demo10.build_wire(cfg)
    assert wire.domain_x_nm[0] < wire.core_x_nm[0] < wire.core_x_nm[1] < wire.domain_x_nm[1]
    assert wire.domain_y_nm[0] < wire.core_y_nm[0] < wire.core_y_nm[1] < wire.domain_y_nm[1]


def test_demo10_mesh_anisotropy_is_reported_for_every_case():
    cfg = workflow.load_demo_config(DEMO_DIRS["10"])
    wire = demo10.build_wire(cfg)
    for dx, dy in cfg["analysis"]["anisotropy_cases"]:
        ratio = wire.mesh_anisotropy(grid_spacing_x_nm=dx, grid_spacing_y_nm=dy)
        assert ratio >= 1.0


def test_demo10_refuses_an_absurdly_expensive_mesh():
    cfg = workflow.load_demo_config(DEMO_DIRS["10"])
    cfg["numerical"]["grid_spacing_x_nm"] = 0.01
    cfg["numerical"]["grid_spacing_y_nm"] = 0.01
    with pytest.raises(workflow.DemoError, match="grid points"):
        demo10.render_values(cfg)


def test_demo10_geometry_offset_shifts_the_core_only():
    cfg = workflow.load_demo_config(DEMO_DIRS["10"])
    centred = demo10.build_wire(cfg)
    cfg["numerical"]["geometry_offset_x_nm"] = 0.5
    shifted = demo10.build_wire(cfg)
    assert shifted.domain_x_nm == centred.domain_x_nm
    assert shifted.core_x_nm[0] == pytest.approx(centred.core_x_nm[0] + 0.5)


def test_demo10_reads_the_real_2d_probability_field():
    """The text-table reader could never have read this: it is binary AVS."""

    fixture = FIXTURES / "demo10_wire_2d"
    x_text = outputs.read_table(fixture / "grid_x.dat").column(0)
    y_text = outputs.read_table(fixture / "grid_y.dat").column(0)
    path = (
        fixture / "bias_00000" / "Quantum" / "wire" / "Gamma" / "probabilities_k00000.fld"
    )
    fields = demo10.read_2d_fields(path, x_text, y_text)
    assert fields.shape == (4, y_text.size, x_text.size)
    labels, units = demo10.field_labels(path)
    assert labels[0].startswith("Psi^2_1") and units[0] == "nm^-2"


def test_demo10_field_axes_are_cross_checked_against_the_grid_files():
    fixture = FIXTURES / "demo10_wire_2d"
    path = (
        fixture / "bias_00000" / "Quantum" / "wire" / "Gamma" / "probabilities_k00000.fld"
    )
    x_text = outputs.read_table(fixture / "grid_x.dat").column(0)
    y_text = outputs.read_table(fixture / "grid_y.dat").column(0)
    # Swapping the axes must be caught, not silently transposed.
    with pytest.raises(outputs.ParserError, match="dim1|coord"):
        demo10.read_2d_fields(path, y_text, x_text)


def test_demo10_native_axes_are_full_precision_unlike_the_text_grid():
    fixture = FIXTURES / "demo10_wire_2d"
    path = (
        fixture / "bias_00000" / "Quantum" / "wire" / "Gamma" / "probabilities_k00000.fld"
    )
    x_native, y_native, fields = demo10.read_2d_fields_native(path)
    x_text = outputs.read_table(fixture / "grid_x.dat").column(0)
    # grid_x.dat is rounded to about six significant figures.
    assert 0.0 < float(np.max(np.abs(x_native - x_text))) < 1e-3
    # Only the full-precision axis is mirror-symmetric enough for the symmetry
    # diagnostic; the rounded one is refused, which is what masked a perfectly
    # symmetric result on the first licensed run.
    assert analysis.symmetry_error(x_native, y_native, fields[0], axis="x") < 1e-12
    with pytest.raises(analysis.AnalysisError, match="not symmetric"):
        analysis.symmetry_error(x_text, y_native, fields[0], axis="x")


def test_demo10_analysis_on_real_2d_output(tmp_path):
    cfg = workflow.load_demo_config(DEMO_DIRS["10"])
    extracted = tmp_path / "extracted"
    plots = tmp_path / "plots"
    extracted.mkdir()
    plots.mkdir()
    observables, validation = demo10.analyse_case(
        cfg, FIXTURES / "demo10_wire_2d", extracted, plots
    )
    # A symmetric wire gives a symmetric ground state, to machine precision.
    assert observables["symmetry_error_x"] < 1e-12
    assert observables["symmetry_error_y"] < 1e-12
    assert validation["symmetric_geometry_gives_symmetric_state"] is True
    # The state sits exactly at the centre of the core.
    assert observables["ground_state_centroid_x_nm"] == pytest.approx(40.0, abs=1e-6)
    assert observables["ground_state_centroid_y_nm"] == pytest.approx(34.0, abs=1e-6)
    assert observables["ground_state_raw_integral"] == pytest.approx(1.0, abs=1e-9)
    assert observables["ground_state_boundary_probability"] < 1e-6
    # The band-edge map is on its own doubled grid, and that is recorded.
    assert observables["band_map_on_quantum_grid"] is False
    assert observables["band_map_grid_points_x"] == 124
    # The material legend travels with the map so the integers mean something.
    assert observables["material_indices_present"] == [27, 43]
    assert any("GaAs" in line for line in observables["material_index_legend"])
    assert (plots / "ground_state_density.png").is_file()
    assert (plots / "material_map.png").is_file()


def test_demo10_symmetry_and_slices_on_a_synthetic_wire_state():
    x = np.linspace(0.0, 60.0, 61)
    y = np.linspace(0.0, 40.0, 41)
    xx, yy = np.meshgrid(x, y)
    values = np.exp(-(((xx - 30.0) / 8.0) ** 2) - (((yy - 20.0) / 4.0) ** 2))
    normalised, _ = analysis.normalise_density_2d(x, y, values)
    assert analysis.symmetry_error(x, y, normalised, axis="x") < 1e-9
    assert analysis.symmetry_error(x, y, normalised, axis="y") < 1e-9
    assert analysis.boundary_probability_2d(x, y, normalised) < 1e-3
    axis, cut = analysis.slice_2d(x, y, normalised, axis="x")
    assert float(axis[int(np.argmax(cut))]) == pytest.approx(30.0, abs=1.0)


def test_demo10_one_dimensional_reference_is_a_real_one_band_deck():
    cfg = workflow.load_demo_config(DEMO_DIRS["10"])
    rendered = workflow.render_template(
        (DEMO_DIRS["10"] / "wire_1d_reference.in.j2").read_text(
            encoding="utf-8"
        ),
        demo10.render_values_1d(cfg),
    )
    assert "simulate1D{}" in rendered
    assert "simulate2D{}" not in rendered
    assert 'name = "well1d"' in rendered
    assert "run{\n    quantum{}\n}" in rendered


# ---------------------------------------------------------------------------
# dry runs: the whole main() with no solver present
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", sorted(DEMO_DIRS))
def test_dry_run_produces_every_promised_artifact(tmp_path, key):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    assert MODULES[key].main(DEMO_DIRS[key], machine) == 0
    demo_id = workflow.load_demo_config(DEMO_DIRS[key])["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())

    for name in (
        "demo_resolved.yaml",
        "machine_summary.json",
        "run_manifest.json",
        "sweep_manifest.json",
        "validation_report.md",
        "console.log",
    ):
        assert (parent / name).is_file(), f"{key}: missing {name}"
    for name in ("sweep_summary.csv", "sweep_summary.json", "failed_runs.csv",
                 "suspicious_runs.csv"):
        assert (parent / "extracted" / name).is_file(), f"{key}: missing {name}"

    manifest = json.loads((parent / "sweep_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "dry_run_complete"
    expected_counts = {
        "04": 11,
        "05": 21,
        "06": 11,
        "07": 14,
        "08": 13,
        "09": 22,
        "10": 25,
    }
    assert manifest["case_count"] == expected_counts[key]
    assert manifest["solver_success_count"] == 0
    assert manifest["skipped_count"] == manifest["case_count"]
    if key in {"04", "05"}:
        assert manifest["state_tracking_confident"] is None
    # Dependency status travels with every run.
    if key == "04":
        assert manifest["dependency_status"]["declared_status"] == "physically_validated"
    else:
        assert manifest["dependency_status"]["declared_status"] != "physically_validated"

    generated = list(parent.glob("runs/*/generated_input/*.in"))
    assert len(generated) == manifest["case_count"]
    for deck in generated:
        assert deck.name == "case.in"
        assert "{{" not in deck.read_text(encoding="utf-8")

    # The complete promised plot set exists, as placeholders where necessary.
    produced = {path.name for path in (parent / "plots").glob("*.png")}
    for filename, _ in MODULES[key].PLOT_SET:
        assert filename in produced, f"{key}: missing plot {filename}"

    # Nothing may claim a physical result without a solver.
    report = (parent / "validation_report.md").read_text(encoding="utf-8")
    expected_physical = "True" if key == "04" else "False"
    assert f"Physically validated: **{expected_physical}**" in report
    assert "PASS" not in report.split("## Criteria")[1].split("|---|")[1].replace(
        "not evaluated", ""
    ) or "not evaluated" in report


@pytest.mark.parametrize("key", ["04", "05", "06", "09"])
def test_dry_run_case_ids_stay_inside_the_windows_path_budget(tmp_path, key):
    machine = _machine_yaml(tmp_path / "machine.yaml", tmp_path / "results")
    MODULES[key].main(DEMO_DIRS[key], machine)
    demo_id = workflow.load_demo_config(DEMO_DIRS[key])["demo_id"]
    parent = next((tmp_path / "results" / demo_id).iterdir())
    for run_dir in (parent / "runs").iterdir():
        # Measured against the real repository root, not the temporary one.
        realistic = (
            workflow.DEFAULT_RESULTS_ROOT / demo_id / parent.name / "runs" / run_dir.name
        )
        assert sweeps.check_path_budget(realistic) is None, run_dir.name


def test_failed_case_is_preserved_with_its_reason(tmp_path, monkeypatch):
    cfg = workflow.load_demo_config(DEMO_DIRS["04"])
    fake = tmp_path / "asset"
    fake.write_text("x", encoding="utf-8")
    machine = workflow.MachineConfig(
        portable_root=tmp_path,
        executable=fake,
        database=fake,
        license=fake,
        threads=1,
        run_solver=True,
        results_root=tmp_path,
        source_path=tmp_path / "machine.yaml",
        discovery_notes=(),
    )
    monkeypatch.setattr(
        workflow, "execute_solver", lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("simulated solver failure")
        )
    )
    spec = sweeps.CaseSpec("c1", "c1", {"center_barrier_nm": 4.0}, cfg)
    run_dir = tmp_path / "failed_case"
    result = sweeps.execute_case(
        demo_dir=DEMO_DIRS["04"],
        spec=spec,
        machine=machine,
        run_dir=run_dir,
        render_values=demo04.render_values,
        analyse=demo04.analyse_case,
    )
    assert result.status == "failed"
    assert "simulated solver failure" in result.failure_reason
    # The generated input survives so the failure can be reproduced.
    assert list((run_dir / "generated_input").glob("*.in"))
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["completion_status"] == "failed"
    assert manifest["generated_input_sha256"]
