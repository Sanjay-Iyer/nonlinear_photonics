"""Twenty-seven preflight checks for Demo 17E. No solver is called by any of them.

Twenty-one licensed solves on an 81.8 nm domain with a 71.8 nm quantum box is
hours of work, so everything establishable without one is established here and a
licensed run either starts from a known-good state or does not start.

Six of the checks exist only in this demo, and they are the ones that make the
statistical claim auditable rather than asserted:

    * the frozen case list is REGENERATED from the seed and compared record for
      record, so "seed-locked" is a property that is tested rather than a word;
    * the 0.05 nm mesh is shown to resolve the narrowest ramp any realization
      draws, per case, in mesh cells;
    * no realization overlaps its two central grades, so all twenty are rendered
      the same way and none silently falls back to an imported table;
    * every case except the reference is shown to differ from the reference in
      grading and in NOTHING ELSE;
    * the deck template is shown to be Demo 17's own file, not a copy;
    * both declared prefactor multipliers are shown to equal the product of
      their own stated factors.

The three inherited corrections are checked against values computed here from
first principles -- 2 wells / 30 nm, and 0.10 * 2*pi/a -- rather than against
constants read out of the config, because a check that reads its expectation
from the thing it is checking cannot fail.
"""

from __future__ import annotations

import math
from pathlib import Path
import tempfile
from typing import Any, Callable

import numpy as np

import adapter14
import cases17e
import demo16
import demo16b
import demo17
import demo17e
import physics14
import sweeps
from preflight16 import database_for, license_for, parser_executable

PASS, FAIL = "PASS", "FAIL"

#: Offline checks. Two more run only where a licensed executable resolves, and
#: the printed total says which set actually ran.
CHECK_COUNT = 27

#: Computed here, independently of demo17e.yaml, so the checks have their own
#: source of truth.
EXPECTED_N_Z_PER_M = 2.0 / 30.0e-9
EXPECTED_K_MAX_PER_NM = 0.10 * 2.0 * math.pi / 0.565325

#: Demo 17's quantum-region padding, in nm. Correction C's whole content.
EXPECTED_QUANTUM_PADDING_NM = 30.0
EXPECTED_DOMAIN_PADDING_NM = 35.0


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"check": name, "status": PASS, "detail": str(fn())}
    except Exception as exc:  # noqa: BLE001
        return {"check": name, "status": FAIL,
                "detail": f"{type(exc).__name__}: {exc}"}


def run_preflight(verbose: bool = False, calibration: str | None = None) -> int:
    demo_dir = Path(__file__).resolve().parent
    cfg = demo17e.load_config()
    plan = cases17e.sampling_plan_from_config(cfg)
    frozen_path = demo_dir / cases17e.CASES_FILENAME
    loaded = cases17e.load_cases(frozen_path, plan)
    scale = demo17e.active_calibration(cfg, calibration)
    graded = [case for case in loaded if not case.is_abrupt]
    reference = cases17e.reference_case(loaded)

    # ---- the 21 frozen structures ---------------------------------------
    def cases_load() -> str:
        expected = [cases17e.REFERENCE_CASE_ID] + [
            f"case_{i:02d}" for i in range(1, plan.realizations + 1)
        ]
        assert [case.case_id for case in loaded] == expected, (
            [case.case_id for case in loaded]
        )
        assert len(loaded) == cases17e.CASE_COUNT, len(loaded)
        return (f"{expected[0]} .. {expected[-1]}, {len(loaded)} cases "
                f"(1 abrupt reference + {len(graded)} realizations)")

    def seed_reproduces_the_frozen_list() -> str:
        """The load-bearing reproducibility claim, tested rather than asserted.

        Regenerating from the seed and comparing record for record is the only
        thing that distinguishes a seed-locked study from one that happened to
        write a file once.
        """

        assert cases17e.regenerates_frozen_list(frozen_path, plan), (
            "the frozen validation_cases.yaml is NOT what seed "
            f"{plan.seed} produces today. Either the file was hand-edited or the "
            "sampler changed; re-run --write-cases deliberately, or restore the "
            "file. Do not solve against a case list whose provenance is unclear."
        )
        widths = [case.mean_interface_width_nm() for case in graded]
        return (f"seed {plan.seed} regenerates all {len(loaded)} records exactly; "
                f"mean widths span {min(widths):.4f}-{max(widths):.4f} nm")

    def sampling_plan_is_bounded() -> str:
        for case in graded:
            for key, value in case.sampled_widths_nm.items():
                assert plan.minimum_nm - 1e-12 <= float(value) <= plan.maximum_nm + 1e-12, (
                    case.case_id, key, value
                )
        drawn = [
            float(value) for case in graded for value in case.sampled_widths_nm.values()
        ]
        assert len(drawn) == len(graded) * len(cases17e.SAMPLED_INTERFACES), len(drawn)
        return (f"{len(drawn)} draws from a {plan.distribution} "
                f"(mu={plan.mean_nm} nm, sd={plan.standard_deviation_nm} nm) all "
                f"inside [{plan.minimum_nm}, {plan.maximum_nm}] nm")

    def reference_matches_demo17() -> str:
        note = cases17e.assert_matches_demo17_reference(loaded)
        assert reference.is_abrupt, "the reference must be the abrupt structure"
        assert reference.is_paper_target, (
            "the paper's 2340 pm/V is quoted for ideal abrupt interfaces, so the "
            "abrupt reference must be the paper target"
        )
        return note

    def only_grading_varies() -> str:
        """Every case must differ from the reference in grading and nothing else."""

        for case in loaded:
            for field_name in (
                "asymmetry_s", "central_barrier_nm", "grading_profile",
                "render_request", "overlap",
            ):
                assert getattr(case, field_name) == getattr(reference, field_name), (
                    case.case_id, field_name, getattr(case, field_name),
                    getattr(reference, field_name),
                )
            assert case.well_widths_nm() == reference.well_widths_nm(), case.case_id
        return (f"all {len(loaded)} cases share s={reference.asymmetry_s:.6f}, "
                f"barrier={reference.central_barrier_nm:.2f} nm, wells "
                f"{reference.well_widths_nm()[0]:.2f}/"
                f"{reference.well_widths_nm()[1]:.2f} nm, linear family")

    def ranges_hold() -> str:
        cases17e.validate_cases(loaded, plan)
        return (f"grading in [{plan.minimum_nm}, {plan.maximum_nm}] nm, one abrupt "
                "reference, no overlapping realization")

    def mesh_resolves_every_grade() -> str:
        """The narrowest ramp any realization draws, in 0.05 nm mesh cells."""

        mesh = float(cfg["mesh"]["active_region_grid_spacing_nm"])
        cells = [case.ramp_cells(mesh) for case in graded]
        assert min(cells) >= cases17e.MINIMUM_RAMP_CELLS, (
            f"the narrowest ramp spans {min(cells):.2f} cells at a {mesh} nm mesh, "
            f"below the {cases17e.MINIMUM_RAMP_CELLS} a transition needs. A "
            "sub-resolution grade is a bug, not a result."
        )
        narrowest = min(graded, key=lambda case: case.ramp_cells(mesh))
        return (f"narrowest ramp {narrowest.narrowest_ramp_span_nm():.4f} nm = "
                f"{min(cells):.1f} cells at {mesh} nm ({narrowest.case_id}); "
                f"widest {max(cells):.1f}")

    def no_realization_overlaps() -> str:
        """All twenty must stay native ternary_linear.

        An overlapping barrier switches production's renderer to an imported
        table. One case rendered differently from the other nineteen would make
        this a rendering comparison as well as a roughness one, and neither would
        then be clean.
        """

        widest = max(graded, key=lambda case: case.ramp_span_nm())
        for case in graded:
            assert not case.overlap, case.case_id
            assert case.overlap_width_nm() == 0.0, (case.case_id,
                                                    case.overlap_width_nm())
            assert case.expected_representation == "native_linear", case.case_id
        headroom = float(reference.central_barrier_nm) - widest.ramp_span_nm()
        assert headroom > 0.0, headroom
        return (f"widest ramp pair {widest.ramp_span_nm():.4f} nm inside the "
                f"{reference.central_barrier_nm:.2f} nm barrier "
                f"({headroom:.4f} nm of headroom, {widest.case_id})")

    def severity_bands_cover_the_ensemble() -> str:
        bands = cfg.get("severity_bands") or cases17e.DEFAULT_SEVERITY_BANDS
        grouped = cases17e.by_severity(loaded, bands)
        assigned = sum(len(members) for members in grouped.values())
        assert assigned == len(graded), (assigned, len(graded))
        assert reference.severity == cases17e.SEVERITY_ABRUPT, reference.severity
        populated = [key for key, members in grouped.items() if members]
        assert len(populated) >= 2, (
            f"only {populated} is populated; a grouped figure with one band is "
            "the ungrouped figure with extra axes"
        )
        return ", ".join(f"{key}={len(value)}" for key, value in grouped.items())

    # ---- the three inherited corrections ---------------------------------
    def correction_a_well_density_nz() -> str:
        derived = demo17.verify_nz_convention(cfg)
        assert math.isclose(derived, EXPECTED_N_Z_PER_M, rel_tol=1e-12), (
            derived, EXPECTED_N_Z_PER_M
        )
        settings = demo17.chi2_settings(cfg)
        assert math.isclose(
            settings.n_wells_per_metre, EXPECTED_N_Z_PER_M, rel_tol=1e-12
        )
        legacy = demo17.legacy_chi2_settings(cfg)
        ratio = settings.n_wells_per_metre / legacy.n_wells_per_metre
        assert math.isclose(ratio, 2.0, rel_tol=1e-12), ratio
        return (f"N_z = {settings.n_wells_per_metre:.6e} m^-1 (2 wells / 30 nm), "
                f"exactly {ratio:.1f}x the legacy period density")

    def correction_b_zincblende_zone_edge() -> str:
        k_max = demo17.verify_k_space_convention(cfg)
        assert math.isclose(k_max, EXPECTED_K_MAX_PER_NM, rel_tol=1e-12), (
            k_max, EXPECTED_K_MAX_PER_NM
        )
        settings = demo17.chi2_settings(cfg)
        assert math.isclose(settings.k_max_per_nm, EXPECTED_K_MAX_PER_NM, rel_tol=1e-12)
        independent = physics14.k_max_per_nm(
            fraction_of_bz=float(
                cfg["k_parallel"]["fraction_of_brillouin_zone_physical"]
            ),
            lattice_constant_nm=float(cfg["k_parallel"]["lattice_constant_nm"]),
            convention="crystallographic_two_pi_over_a",
        )
        assert math.isclose(independent, k_max, rel_tol=1e-12), (independent, k_max)
        return (f"k_max = {k_max:.6f} nm^-1 = 0.10 * 2*pi/a; matches physics14 "
                "independently of the fraction encoding")

    def correction_b_guard_catches_drift() -> str:
        """The guard must actually fire; a check that cannot fail is not one."""

        broken = {**cfg, "k_parallel": {**cfg["k_parallel"], "fraction_of_bz": 0.10}}
        try:
            demo17.verify_k_space_convention(broken)
        except demo17.Demo17Error:
            pass
        else:  # pragma: no cover - the guard is the thing under test
            raise AssertionError(
                "verify_k_space_convention accepted a fraction that encodes the "
                "legacy pi/a cutoff; the guard is not guarding anything."
            )
        return "reverting fraction_of_bz to 0.10 is rejected, as it must be"

    def correction_c_dirichlet_box() -> str:
        record = demo17.verify_domain_convention(cfg)
        assert record["domain_padding_nm"] == EXPECTED_DOMAIN_PADDING_NM, record
        assert record["quantum_region_padding_nm"] == EXPECTED_QUANTUM_PADDING_NM, record
        assert record["algaas_beyond_dirichlet_wall_nm"] > 0.0, record
        padding_11 = adapter14._outer_padding_nm(cfg)
        assert padding_11 >= 0.0, padding_11
        return (f"cladding {record['domain_padding_nm']:.1f} nm, Dirichlet wall "
                f"{record['quantum_region_padding_nm']:.1f} nm out, "
                f"{record['algaas_beyond_dirichlet_wall_nm']:.1f} nm of AlGaAs "
                f"beyond it; Demo 11 padding {padding_11:.1f} nm")

    def correction_c_reaches_every_deck() -> str:
        widths, domains = [], []
        for case in loaded:
            record = demo17e.deck_geometry_record(cfg, case)
            assert not record["quantum_region_clamped_by_domain"], record
            assert record["dirichlet_clearance_left_nm"] >= (
                EXPECTED_QUANTUM_PADDING_NM - 1e-9
            ), record
            assert record["dirichlet_clearance_right_nm"] >= (
                EXPECTED_QUANTUM_PADDING_NM - 1e-9
            ), record
            widths.append(record["quantum_region_width_nm"])
            domains.append(record["domain_width_nm"])
        # Every case has the same layer stack, so every box must be the same box.
        assert max(widths) - min(widths) < 1e-9, (min(widths), max(widths))
        return (f"all {len(loaded)} quantum boxes {widths[0]:.2f} nm wide inside a "
                f"{domains[0]:.2f} nm domain, none clamped, >= "
                f"{EXPECTED_QUANTUM_PADDING_NM:.0f} nm clearance")

    # ---- the deck --------------------------------------------------------
    def template_is_demo17s_own_file() -> str:
        """Not a copy of Demo 17's template -- Demo 17's template."""

        path = demo17e.template_path(cfg)
        assert path.is_file(), path
        assert path.name == "graded_acqw17.in.j2", path
        assert path.parent.name == "17_paper_chi2_reproduction_corrected", path
        assert path.parent.parent == demo_dir.parent, (path, demo_dir)
        try:
            import demo17 as _demo17  # noqa: PLC0415
            expected = (
                Path(_demo17.DEMO_DIR) / str(
                    _demo17.load_config()["nextnano"]["template"]
                )
            ).resolve()
            assert path == expected, (path, expected)
            shared = "; identical path to the one Demo 17 solved with"
        except Exception:  # noqa: BLE001 - Demo 17 optional in a split bundle
            shared = "; Demo 17 config not loadable here, path check only"
        text = path.read_text(encoding="utf-8")
        assert "boundary{ x = dirichlet }" in text
        assert "{{quantum_start_nm}}" in text and "{{quantum_end_nm}}" in text
        return f"{path.parent.name}/{path.name}{shared}"

    def decks_render() -> str:
        for case in loaded:
            geometry, _profile, _blocks, deck = demo17e.build_case(cfg, case)
            start, end = demo17e.quantum_region_nm(cfg, geometry)
            assert f"x = [{start:.6f}, {end:.6f}]" in deck, (case.case_id, start, end)
            assert "boundary{ x = dirichlet }" in deck, case.case_id
            assert "envelopes = yes" in deck and "probabilities = yes" in deck
            assert "{{" not in deck and "}}" not in deck, case.case_id
        geometry, _p, _b, _d = demo17e.build_case(cfg, reference)
        start, end = demo17e.quantum_region_nm(cfg, geometry)
        return (f"{len(loaded)} decks render; quantum region [{start:.2f}, "
                f"{end:.2f}] nm, domain {geometry.domain_nm[1]:.2f} nm")

    def geometry_resolves() -> str:
        for case in loaded:
            geometry, _profile, _blocks, _deck = demo17e.build_case(cfg, case)
            assert abs(geometry.thick_well_nm + geometry.thin_well_nm - 10.0) < 1e-12
        geometry, _p, _b, _d = demo17e.build_case(cfg, reference)
        assert np.allclose(
            (geometry.thick_well_nm, geometry.barrier_nm, geometry.thin_well_nm),
            (7.1, 1.8, 2.9),
        ), (geometry.thick_well_nm, geometry.barrier_nm, geometry.thin_well_nm)
        return "authoritative Demo 14 geometry 7.10 / 1.80 / 2.90 nm; 10 nm GaAs total"

    def profiles_build_and_bound() -> str:
        peaks = []
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo17e.build_case(cfg, case)
            assert np.all(np.isfinite(profile.al_fraction)), case.case_id
            assert profile.al_fraction.min() >= -1e-9, case.case_id
            assert profile.al_fraction.max() <= cases17e.AL_FRACTION + 1e-9, case.case_id
            peaks.append(float(profile.al_fraction.max()))
        # No realization may fail to reach nominal in the barrier: that is what
        # an overlapping grade looks like in composition space, and it would mean
        # the tunnelling barrier is not the barrier the study says it is.
        assert min(peaks) >= 0.999 * cases17e.AL_FRACTION, min(peaks)
        return (f"{len(loaded)} profiles in [0, {cases17e.AL_FRACTION}]; every "
                f"barrier reaches nominal (min peak {min(peaks):.6f})")

    def physical_stack() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo17e.build_case(cfg, case)
            checks = demo16.structural_invariants(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"], cases17e.AL_FRACTION,
            )
            assert checks["all_passed"], (case.case_id, checks)
        return f"outer barriers and two GaAs wells in all {len(loaded)} cases"

    def representations_are_as_declared() -> str:
        seen: dict[str, list[str]] = {}
        for case in loaded:
            _geometry, _profile, blocks, _deck = demo17e.build_case(cfg, case)
            realized = demo17e.representation_of(blocks, case)
            assert realized == case.expected_representation, (
                case.case_id, realized, case.expected_representation
            )
            seen.setdefault(realized, []).append(case.case_id)
        assert set(seen) == {"abrupt", "native_linear"}, seen
        assert len(seen["abrupt"]) == 1, seen["abrupt"]
        return ", ".join(f"{key}={len(value)}" for key, value in sorted(seen.items()))

    def abrupt_reference_deck_has_no_ramps() -> str:
        _geometry, _profile, blocks, deck = demo17e.build_case(cfg, reference)
        statements = "\n".join(
            line for line in deck.splitlines() if not line.lstrip().startswith("#")
        )
        assert "ternary_linear" not in statements
        assert "ternary_import" not in statements
        assert not blocks["datafile"] and not blocks["import_block"]
        assert statements.count('binary{ name = "GaAs" }') == 2
        assert statements.count("ternary_constant") == 1
        return f"{reference.case_id}: two GaAs wells in the Al0.55 matrix, no ramps"

    def localization_regions_cover_the_stack() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo17e.build_case(cfg, case)
            regions = demo16b._region_map(profile)
            assert set(regions) == {"thick_well", "central_barrier", "thin_well"}
            spans = [regions[name] for name in
                     ("thick_well", "central_barrier", "thin_well")]
            assert all(hi > lo for lo, hi in spans), case.case_id
            total = spans[2][1] - spans[0][0]
            expected = 10.0 + float(case.central_barrier_nm)
            assert abs(total - expected) < 1e-9, (case.case_id, total, expected)
        return "left | barrier | right partition the active region with no gaps"

    # ---- the optical path ------------------------------------------------
    def optical_pipeline_carries_the_corrections() -> str:
        geometry, profile, _blocks, _deck = demo17e.build_case(cfg, reference)
        derived = adapter14.build_demo11_analysis_config_from_demo14(
            cfg, geometry, profile
        )
        metric = derived["metric"]
        assert metric["mode"] == "absolute", metric["mode"]
        assert metric["reference_wavelength_nm"] == 1550.0
        assert metric["broadening_meV"] == 5.0
        assert metric["max_states_per_band"] == 2
        assert math.isclose(
            float(metric["n_wells_per_metre"]), EXPECTED_N_Z_PER_M, rel_tol=1e-12
        ), metric["n_wells_per_metre"]
        assert math.isclose(
            float(metric["k_max_per_nm"]), EXPECTED_K_MAX_PER_NM, rel_tol=1e-12
        ), metric["k_max_per_nm"]
        assert math.isclose(
            float(derived["numerical"]["quantum_region_padding_nm"]),
            EXPECTED_QUANTUM_PADDING_NM,
        )
        # Read from cfg["validation"]; the same key under any other section would
        # be silently ignored while looking live.
        policy = derived["validation"]["quasi_bound_state_policy"]
        assert policy == str(cfg["validation"]["quasi_bound_state_policy"]), (
            f"demo17e.yaml asks for {cfg['validation']['quasi_bound_state_policy']!r} "
            f"but the derived Demo 11 config got {policy!r}; the key is in the "
            "wrong section and is dead config."
        )
        return ("Demo 17E -> Demo 11 absolute chi2 with N_z="
                f"{metric['n_wells_per_metre']:.4e} m^-1, k_max="
                f"{metric['k_max_per_nm']:.4f} nm^-1, "
                f"{EXPECTED_QUANTUM_PADDING_NM:.1f} nm quantum padding, "
                f"quasi-bound policy '{policy}'")

    def wavelength_grid_is_one_nanometre() -> str:
        grid = demo17e.verify_wavelength_grid(cfg)
        step = float(grid[1] - grid[0])
        assert math.isclose(step, 1.0, rel_tol=1e-12), step
        assert grid.size == 401, grid.size
        return (f"{grid[0]:.0f}-{grid[-1]:.0f} nm, {grid.size} points, "
                f"{step:.3f} nm step -- one grid for all {len(loaded)} spectra")

    # ---- the dual reporting scale ---------------------------------------
    def prefactor_arithmetic_closes() -> str:
        """Every declared multiplier must equal the product of its own factors."""

        scales = demo17e.load_calibrations(cfg)
        assert scales["raw"].multiplier == 1.0, scales["raw"].multiplier
        described = []
        for key, entry in sorted(scales.items()):
            if entry.is_raw:
                continue
            assert entry.factors, f"{key} declares no factors to check against"
            product = 1.0
            for value in entry.factors.values():
                product *= float(value)
            assert math.isclose(product, entry.multiplier, rel_tol=1e-9), (
                key, product, entry.multiplier
            )
            described.append(f"{key}={entry.multiplier:g}x[{entry.status}]")
        assert scale.scale_id in scales, scale.scale_id
        return ("raw=1.00x[established], " + ", ".join(described)
                + f"; active={scale.scale_id}")

    def calibration_never_reaches_a_gate() -> str:
        """The calibrated column must be presentation, not physics.

        Applied to a probe value and checked to be a pure multiplication, and the
        stamped record checked to declare its own status honestly. Nothing in
        this demo's gates reads a calibrated number, and this is where that stays
        true when someone edits the config.
        """

        record = demo17e.calibration_record(cfg, scale)
        assert record["raw_column_is_fitted"] is False
        assert record["calibration_used_in_any_gate_or_check"] is False
        assert record["calibrated_column_is_declared_not_derived"] is True
        assert scale.status in ("established", "reported", "speculative",
                               "contradicted"), scale.status
        probe = {"chi2_at_1550": 100.0, "spectral_peak_chi2": 200.0,
                 "spectral_peak_wavelength_nm": 1520.0,
                 "detuning_from_1550_nm": -30.0}
        scaled = demo17e.scaled_optics(probe, scale)
        assert math.isclose(
            scaled["chi2_1550_calibrated_pm_per_V"], 100.0 * scale.multiplier,
            rel_tol=1e-12,
        )
        # A multiplier moves an amplitude and cannot move a peak position. If
        # this ever fails, the calibration has stopped being a scale.
        assert scaled["peak_wavelength_nm"] == 1520.0, scaled["peak_wavelength_nm"]
        assert math.isclose(scaled["peak_over_1550_contrast"], 2.0, rel_tol=1e-12)
        return (f"{scale.scale_id} ({scale.multiplier:g}x, {scale.status}) scales "
                "amplitudes only; peak position and contrast unchanged")

    # ---- paths and machine ----------------------------------------------
    def output_and_paths_resolve() -> str:
        import run_demo17e  # noqa: PLC0415

        root = run_demo17e.results_root() / demo17e.DEMO_ID
        assert list(root.parts).count("demo_runs") <= 1, root
        sample = root / "demo17e_20260813T235959Z_12345678_abcdef"
        names = []
        for case in loaded:
            raw = demo17e.physics_raw_output_dir(sample / "cases" / case.case_id, case)
            assert sweeps.check_path_budget(raw) is None, raw
            names.append(raw.name)
        expected = ["p00"] + [f"p{i:02d}" for i in range(1, plan.realizations + 1)]
        assert names == expected, names
        return f"{root}; raw {names[0]}..{names[-1]} within the path budget"

    try:
        import run_demo17e
        machine = run_demo17e.resolve_machine()
    except Exception:  # noqa: BLE001
        machine = None
    exe = parser_executable(machine)

    def executable_resolves() -> str:
        assert exe is not None and Path(exe).is_file(), (
            "no nextnano++ executable resolved; --physics cannot run on this "
            "machine. This is expected on the authoring laptop."
        )
        return str(exe)

    def representative_decks_parse() -> str:
        """One deck per representation and per severity band, through --parse."""

        assert exe is not None
        chosen = {reference.case_id: reference}
        for band in cfg.get("severity_bands") or cases17e.DEFAULT_SEVERITY_BANDS:
            members = [c for c in graded if c.severity == str(band["key"])]
            if members:
                chosen.setdefault(members[0].case_id, members[0])
        checked = []
        for case_id, case in chosen.items():
            _geometry, _profile, blocks, deck = demo17e.build_case(cfg, case)
            with tempfile.TemporaryDirectory(prefix="demo17e_pre_") as temp:
                result = demo16.parse_deck(
                    exe, database_for(exe), Path(temp) / case_id,
                    deck, blocks["datafile"], license_path=license_for(machine),
                )
            assert result["passed"], (
                case_id, result["return_code"], result.get("failure_reason")
            )
            checked.append(f"{case_id}({case.severity})")
        return ", ".join(checked) + " accepted with --parse"

    checks = (
        ("21 frozen cases load", cases_load),
        ("the seed regenerates the frozen list", seed_reproduces_the_frozen_list),
        ("every sampled width is inside its bounds", sampling_plan_is_bounded),
        ("abrupt reference identical to Demo 17 case_02", reference_matches_demo17),
        ("grading is the only thing that varies", only_grading_varies),
        ("parameters lie inside intended ranges", ranges_hold),
        ("the 0.05 nm mesh resolves every grade", mesh_resolves_every_grade),
        ("no realization overlaps its central grades", no_realization_overlaps),
        ("severity bands cover the ensemble", severity_bands_cover_the_ensemble),
        ("CORRECTION A: N_z is the per-well density", correction_a_well_density_nz),
        ("CORRECTION B: k_max is 0.10 of the 2*pi/a edge",
         correction_b_zincblende_zone_edge),
        ("CORRECTION B: the zone-edge guard rejects a revert",
         correction_b_guard_catches_drift),
        ("CORRECTION C: Dirichlet box clears the active region",
         correction_c_dirichlet_box),
        ("CORRECTION C: every deck gets the same wider box",
         correction_c_reaches_every_deck),
        ("the deck template is Demo 17's own file", template_is_demo17s_own_file),
        ("all 21 decks render with no placeholders left", decks_render),
        ("authoritative geometry resolves", geometry_resolves),
        ("profiles build, stay bounded and reach nominal", profiles_build_and_bound),
        ("outer barriers and two wells exist", physical_stack),
        ("representations render as declared", representations_are_as_declared),
        ("abrupt reference deck contains no ramps", abrupt_reference_deck_has_no_ramps),
        ("localization regions partition the stack",
         localization_regions_cover_the_stack),
        ("optical config carries all three corrections",
         optical_pipeline_carries_the_corrections),
        ("the 1400-1800 nm grid steps exactly 1 nm",
         wavelength_grid_is_one_nanometre),
        ("declared prefactor multipliers close arithmetically",
         prefactor_arithmetic_closes),
        ("calibration scales amplitudes and nothing else",
         calibration_never_reaches_a_gate),
        ("output and raw physics paths resolve", output_and_paths_resolve),
    )
    if len(checks) != CHECK_COUNT:  # pragma: no cover - guards the printed count
        raise RuntimeError(f"expected {CHECK_COUNT} checks, defined {len(checks)}")
    if exe is not None:
        checks = checks + (
            ("nextnano++ executable resolves", executable_resolves),
            ("representative decks parse", representative_decks_parse),
        )

    results = [_check(name, fn) for name, fn in checks]
    width = max(len(row["check"]) for row in results) + 2
    total = len(results)
    rule = "=" * (width + 58)
    print(rule)
    print("  DEMO 17E PREFLIGHT -- statistical interface roughness sweep")
    print(rule)
    for row in results:
        print(f"  [{row['status']:4}] {row['check']:<{width}} {row['detail']}")
    failed = [row for row in results if row["status"] == FAIL]
    print(rule)
    print(f"  DEMO 17E PREFLIGHT: {'FAIL' if failed else 'PASS'} "
          f"({total - len(failed)}/{total} checks)")
    print(f"  CASES  : {len(loaded)} (1 abrupt reference + {len(graded)} "
          f"realizations, seed {plan.seed})")
    print(f"  SCALES : raw 1.00x  |  calibrated {scale.scale_id} "
          f"{scale.multiplier:g}x ({scale.status})")
    if exe is None:
        print("  NOTE: no nextnano++ executable on this machine, so the licensed "
              "deck-parse checks did not run. --physics needs the work laptop.")
    if verbose:
        for row in failed:
            print(f"    - {row['check']}: {row['detail']}")
    return 1 if failed else 0
