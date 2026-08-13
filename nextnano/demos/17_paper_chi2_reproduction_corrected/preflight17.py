"""Twenty preflight checks for Demo 17.

Everything that can be established without a licensed solve is established here,
so a licensed run either starts from a known-good state or does not start. Six
of the twenty exist only in this demo: they are the ones that prove the three
corrections are actually in force, numerically, on the objects that will reach
the solver and the evaluator -- not merely written down in ``demo.yaml``.

Correction A and correction B are both checked against a value computed here
from first principles (2 wells / 30 nm, and 0.10 * 2*pi/a) rather than against a
constant copied out of the config, because a check that reads its expectation
from the thing it is checking cannot fail.
"""

from __future__ import annotations

import math
from pathlib import Path
import tempfile
from typing import Any, Callable

import numpy as np

import adapter14
import cases17
import chi2 as chi2mod
import demo14
import demo16
import demo16b
import demo16e
import demo17
import grading14
import physics14
import sweeps
from preflight16 import database_for, license_for, parser_executable

PASS, FAIL = "PASS", "FAIL"
CHECK_COUNT = 20

#: Computed here, independently of demo.yaml, so the checks have their own
#: source of truth.
EXPECTED_N_Z_PER_M = 2.0 / 30.0e-9
EXPECTED_K_MAX_PER_NM = 0.10 * 2.0 * math.pi / 0.565325


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"check": name, "status": PASS, "detail": str(fn())}
    except Exception as exc:  # noqa: BLE001
        return {"check": name, "status": FAIL,
                "detail": f"{type(exc).__name__}: {exc}"}


def _synthetic_bands(z_nm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two orthonormal, asymmetric envelopes per band, on the given grid.

    Only used to exercise the ablation plumbing end to end without a solver.
    Deliberately NOT physical: the point is that the conventions reach the
    evaluator, and a factor that must come out at exactly 2.0 does not care
    what the wavefunctions look like.
    """

    def pair(centre_a: float, centre_b: float, width: float) -> np.ndarray:
        first = np.exp(-((z_nm - centre_a) ** 2) / (2.0 * width**2))
        second = (z_nm - centre_b) * np.exp(
            -((z_nm - centre_b) ** 2) / (2.0 * width**2)
        )
        return np.column_stack([first, second])

    return pair(24.0, 29.0, 2.0), pair(23.6, 23.8, 1.8)


def run_preflight(verbose: bool = False) -> int:
    demo_dir = Path(__file__).resolve().parent
    cfg = demo17.load_config()
    loaded = cases17.load_cases(demo_dir / cases17.CASES_FILENAME)

    # ---- the ten fixed structures ---------------------------------------
    def cases_load() -> str:
        expected = [f"case_{i:02d}" for i in range(1, cases17.CASE_COUNT + 1)]
        assert [case.case_id for case in loaded] == expected
        assert [case.as_record() for case in cases17.all_cases()] == [
            case.as_record() for case in loaded
        ]
        return "case_01 .. case_10, identical to the frozen list"

    def structures_match_demo16e() -> str:
        note = cases17.assert_matches_baseline(loaded)
        target = cases17.paper_target_case()
        assert target.is_abrupt, "the paper target must be the abrupt structure"
        return f"{note}; paper target = {target.case_id} (abrupt)"

    def geometry_resolves() -> str:
        for case in loaded:
            geometry, _profile, _blocks, _deck = demo17.build_case(cfg, case)
            assert abs(geometry.thick_well_nm + geometry.thin_well_nm - 10.0) < 1e-12
        geometry, _p, _b, _d = demo17.build_case(cfg, loaded[0])
        assert np.allclose(
            (geometry.thick_well_nm, geometry.barrier_nm, geometry.thin_well_nm),
            (7.1, 1.8, 2.9),
        )
        return "authoritative Demo 14 geometry; fixed 10 nm GaAs total"

    def ranges_hold() -> str:
        cases17.validate_cases(loaded)
        return "s=[0.30,0.55], barrier=[0.85,2.50], grade=0 or [0.40,1.40] nm"

    # ---- CORRECTION A ----------------------------------------------------
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
                f"exactly {ratio:.1f}x the {legacy.n_wells_per_metre:.6e} baseline")

    # ---- CORRECTION B ----------------------------------------------------
    def correction_b_zincblende_zone_edge() -> str:
        k_max = demo17.verify_k_space_convention(cfg)
        assert math.isclose(k_max, EXPECTED_K_MAX_PER_NM, rel_tol=1e-12), (
            k_max, EXPECTED_K_MAX_PER_NM
        )
        settings = demo17.chi2_settings(cfg)
        assert math.isclose(settings.k_max_per_nm, EXPECTED_K_MAX_PER_NM, rel_tol=1e-12)
        legacy = demo17.legacy_chi2_settings(cfg)
        assert math.isclose(settings.k_max_per_nm / legacy.k_max_per_nm, 2.0,
                            rel_tol=1e-12)
        # The physics14 helper implements both conventions explicitly; agreeing
        # with it means the fraction trick reproduces the real 2*pi/a edge and
        # is not merely internally consistent.
        independent = physics14.k_max_per_nm(
            fraction_of_bz=float(
                cfg["k_parallel"]["fraction_of_brillouin_zone_physical"]
            ),
            lattice_constant_nm=float(cfg["k_parallel"]["lattice_constant_nm"]),
            convention="crystallographic_two_pi_over_a",
        )
        assert math.isclose(independent, k_max, rel_tol=1e-12), (independent, k_max)
        return (f"k_max = {k_max:.6f} nm^-1 = 0.10 * 2*pi/a, 2.000x the legacy "
                f"{legacy.k_max_per_nm:.6f} nm^-1; matches physics14 independently")

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

    # ---- CORRECTION C ----------------------------------------------------
    def correction_c_dirichlet_box() -> str:
        record = demo17.verify_domain_convention(cfg)
        assert record["domain_padding_nm"] == 35.0, record
        assert record["quantum_region_padding_nm"] == 30.0, record
        assert record["algaas_beyond_dirichlet_wall_nm"] > 0.0, record
        # adapter14 must be able to rebuild Demo 11's stack from this padding.
        padding_11 = adapter14._outer_padding_nm(cfg)
        assert padding_11 >= 0.0, padding_11
        return (f"cladding {record['domain_padding_nm']:.1f} nm, Dirichlet wall "
                f"{record['quantum_region_padding_nm']:.1f} nm out, "
                f"{record['algaas_beyond_dirichlet_wall_nm']:.1f} nm of AlGaAs "
                f"beyond it; Demo 11 padding {padding_11:.1f} nm")

    def correction_c_reaches_every_deck() -> str:
        widths = []
        for case in loaded:
            record = demo17.deck_geometry_record(cfg, case)
            assert not record["quantum_region_clamped_by_domain"], record
            assert record["dirichlet_clearance_left_nm"] >= 30.0 - 1e-9, record
            assert record["dirichlet_clearance_right_nm"] >= 30.0 - 1e-9, record
            widths.append(record["quantum_region_width_nm"])
        return (f"all {len(loaded)} quantum regions {min(widths):.1f}-"
                f"{max(widths):.1f} nm wide, none clamped, >=30 nm clearance")

    # ---- the deck --------------------------------------------------------
    def demo17_template_is_used() -> str:
        template = demo_dir / str(cfg["nextnano"]["template"])
        assert template.name == "graded_acqw17.in.j2", template
        assert template.is_file(), template
        geometry, _profile, _blocks, deck = demo17.build_case(cfg, loaded[0])
        start, end = demo17.quantum_region_nm(cfg, geometry)
        assert f"x = [{start:.6f}, {end:.6f}]" in deck, (start, end)
        assert "boundary{ x = dirichlet }" in deck
        assert "envelopes = yes" in deck and "probabilities = yes" in deck
        assert "{{" not in deck and "}}" not in deck
        return (f"{template.name}; quantum region [{start:.2f}, {end:.2f}] nm, "
                f"domain {geometry.domain_nm[1]:.1f} nm")

    def profiles_build_and_bound() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo17.build_case(cfg, case)
            assert np.all(np.isfinite(profile.al_fraction))
            assert profile.al_fraction.min() >= -1e-9
            assert profile.al_fraction.max() <= cases17.AL_FRACTION + 1e-9
        return f"{len(loaded)} authoritative profiles remain in [0, 0.55]"

    def physical_stack() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo17.build_case(cfg, case)
            checks = demo16.structural_invariants(
                profile.x_nm, profile.al_fraction,
                profile.request["interfaces_nm"], cases17.AL_FRACTION,
            )
            assert checks["all_passed"], (case.case_id, checks)
        return "outer barriers and two GaAs wells in all ten cases"

    def representations_are_as_declared() -> str:
        seen: dict[str, list[str]] = {}
        for case in loaded:
            _geometry, _profile, blocks, _deck = demo17.build_case(cfg, case)
            realized = demo17.representation_of(blocks, case)
            assert realized == case.expected_representation, (
                case.case_id, realized, case.expected_representation
            )
            seen.setdefault(realized, []).append(case.case_id)
        assert set(seen) == set(cases17.REPRESENTATIONS), seen
        return ", ".join(f"{key}={len(value)}" for key, value in sorted(seen.items()))

    def abrupt_deck_has_no_ramps() -> str:
        case = cases17.paper_target_case()
        _geometry, _profile, blocks, deck = demo17.build_case(cfg, case)
        statements = "\n".join(
            line for line in deck.splitlines() if not line.lstrip().startswith("#")
        )
        assert "ternary_linear" not in statements
        assert "ternary_import" not in statements
        assert not blocks["datafile"] and not blocks["import_block"]
        assert statements.count('binary{ name = "GaAs" }') == 2
        assert statements.count("ternary_constant") == 1
        return f"{case.case_id}: two GaAs wells in the Al0.55 matrix, no ramps"

    def localization_regions_cover_the_stack() -> str:
        for case in loaded:
            _geometry, profile, _blocks, _deck = demo17.build_case(cfg, case)
            regions = demo16b._region_map(profile)
            assert set(regions) == {"thick_well", "central_barrier", "thin_well"}
            spans = [regions[name] for name in
                     ("thick_well", "central_barrier", "thin_well")]
            assert all(hi > lo for lo, hi in spans)
            total = spans[2][1] - spans[0][0]
            expected = 10.0 + float(case.central_barrier_nm)
            assert abs(total - expected) < 1e-9, (case.case_id, total, expected)
        return "left | barrier | right partition the active region with no gaps"

    # ---- the optical path ------------------------------------------------
    def optical_pipeline_carries_the_corrections() -> str:
        geometry, profile, _blocks, _deck = demo17.build_case(cfg, loaded[0])
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
            float(derived["numerical"]["quantum_region_padding_nm"]), 30.0
        )
        # The state-selection policy is read from cfg["validation"], and the
        # same key under any other section would be silently ignored while
        # looking live. Check it arrives rather than that it was written.
        policy = derived["validation"]["quasi_bound_state_policy"]
        assert policy == str(cfg["validation"]["quasi_bound_state_policy"]), (
            f"demo.yaml asks for {cfg['validation']['quasi_bound_state_policy']!r} "
            f"but the derived Demo 11 config got {policy!r}; the key is in the "
            "wrong section and is dead config."
        )
        return ("Demo 17 -> Demo 11 absolute chi2 with N_z="
                f"{metric['n_wells_per_metre']:.4e} m^-1, k_max="
                f"{metric['k_max_per_nm']:.4f} nm^-1, 30.0 nm quantum padding, "
                f"quasi-bound policy '{policy}'")

    def ablation_runs_end_to_end() -> str:
        """Exercise the real ablation path on synthetic states, no solver."""

        z_nm = np.linspace(0.0, 60.0, 1201)
        e_raw, h_raw = _synthetic_bands(z_nm)
        electron = chi2mod.orthonormalise(
            chi2mod.BandStates(z_nm, np.array([2.940621, 3.058949]), e_raw, "e")
        )
        heavy_hole = chi2mod.orthonormalise(
            chi2mod.BandStates(z_nm, np.array([1.447962, 1.413366]), h_raw, "hh")
        )
        metrics = {
            "electron_energies_eV": electron.energies_eV.tolist(),
            "heavy_hole_energies_eV": heavy_hole.energies_eV.tolist(),
        }
        with tempfile.TemporaryDirectory(prefix="demo17_pre_") as temp:
            extracted = Path(temp)
            np.savetxt(
                extracted / "envelopes.csv",
                np.column_stack([z_nm, electron.envelopes, heavy_hole.envelopes]),
                delimiter=",",
                header="z_nm,psi_e1,psi_e2,psi_hh1,psi_hh2",
                comments="",
            )
            back_e, back_h = demo17.band_states_from_extracted(extracted, metrics)
            assert back_e.count == 2 and back_h.count == 2
            assert np.allclose(back_e.envelopes, electron.envelopes, atol=1e-9)
            ablation = demo17.correction_ablation(cfg, extracted, metrics)
        factor_a = ablation["factor_A_well_density_Nz"]
        factor_b = ablation["factor_B_zincblende_zone_edge"]
        assert math.isclose(factor_a, 2.0, rel_tol=1e-9), factor_a
        assert factor_b is not None and factor_b > 1.0, factor_b
        assert ablation["correction_C_measured_here"] is False
        return (f"three rungs evaluate; A = {factor_a:.4f}x exactly, "
                f"B = {factor_b:.4f}x on synthetic states")

    def baseline_is_available() -> str:
        baseline = demo17.load_baseline_chi2()
        if not baseline:
            return ("no committed Demo 16E summary found; correction C's factor "
                    "will be reported as unavailable rather than estimated")
        missing = [case.case_id for case in loaded if case.case_id not in baseline]
        target = cases17.PAPER_TARGET_CASE_ID
        return (f"{len(baseline)} Demo 16E values"
                + (f", missing {missing}" if missing else ", all ten present")
                + f"; {target} baseline = {baseline.get(target, float('nan')):.3f} pm/V")

    # ---- machine-dependent ----------------------------------------------
    try:
        import run_demo17
        machine = run_demo17.resolve_machine()
    except Exception:  # noqa: BLE001
        machine = None
    exe = parser_executable(machine)

    def executable_resolves() -> str:
        assert exe is not None and Path(exe).is_file()
        return str(exe)

    def output_and_paths_resolve() -> str:
        import run_demo17
        root = run_demo17.results_root() / demo17.DEMO_ID
        assert list(root.parts).count("demo_runs") <= 1
        sample = root / "demo17_20260813T235959Z_12345678_abcdef"
        names = []
        for case in loaded:
            raw = demo17.physics_raw_output_dir(sample / "cases" / case.case_id, case)
            assert sweeps.check_path_budget(raw) is None, raw
            names.append(raw.name)
        assert names == [f"p{i:02d}" for i in range(1, cases17.CASE_COUNT + 1)], names
        return f"{root}; raw {names[0]}..{names[-1]} within the path budget"

    def representative_decks_parse() -> str:
        assert exe is not None
        by_id = {case.case_id: case for case in loaded}
        checked = []
        # One case per representation: the graded reference, the abrupt paper
        # target and the deliberately imported one.
        for case_id in ("case_01", "case_02", "case_10"):
            case = by_id[case_id]
            _geometry, _profile, blocks, deck = demo17.build_case(cfg, case)
            with tempfile.TemporaryDirectory(prefix="demo17_pre_") as temp:
                result = demo16.parse_deck(
                    exe, database_for(exe), Path(temp) / case_id,
                    deck, blocks["datafile"], license_path=license_for(machine),
                )
            assert result["passed"], (
                case_id, result["return_code"], result.get("failure_reason")
            )
            checked.append(f"{case_id}({case.expected_representation})")
        return ", ".join(checked) + " accepted with --parse"

    checks = (
        ("ten fixed cases load", cases_load),
        ("structures identical to Demo 16E", structures_match_demo16e),
        ("authoritative geometry resolves", geometry_resolves),
        ("parameters lie inside intended ranges", ranges_hold),
        ("CORRECTION A: N_z is the per-well density", correction_a_well_density_nz),
        ("CORRECTION B: k_max is 0.10 of the 2*pi/a edge",
         correction_b_zincblende_zone_edge),
        ("CORRECTION B: the zone-edge guard rejects a revert",
         correction_b_guard_catches_drift),
        ("CORRECTION C: Dirichlet box clears the active region",
         correction_c_dirichlet_box),
        ("CORRECTION C: every deck gets the wider box",
         correction_c_reaches_every_deck),
        ("Demo 17's own template renders", demo17_template_is_used),
        ("authoritative profiles build and stay bounded", profiles_build_and_bound),
        ("outer barriers and two wells exist", physical_stack),
        ("three representations render as declared", representations_are_as_declared),
        ("abrupt paper-target deck contains no ramps", abrupt_deck_has_no_ramps),
        ("localization regions partition the stack",
         localization_regions_cover_the_stack),
        ("optical config carries all three corrections",
         optical_pipeline_carries_the_corrections),
        ("correction ablation runs end to end", ablation_runs_end_to_end),
        ("Demo 16E baseline for correction C", baseline_is_available),
        ("nextnano++ executable resolves", executable_resolves),
        ("output and raw physics paths resolve", output_and_paths_resolve),
    )
    if len(checks) != CHECK_COUNT:  # pragma: no cover - guards the printed count
        raise RuntimeError(f"expected {CHECK_COUNT} checks, defined {len(checks)}")
    if exe is not None:
        checks = checks + (
            ("one deck per representation parses", representative_decks_parse),
        )

    results = [_check(name, fn) for name, fn in checks]
    width = max(len(row["check"]) for row in results) + 2
    total = len(results)
    print("=" * (width + 52))
    print("  DEMO 17 PREFLIGHT -- corrected absolute chi(2) reproduction")
    print("=" * (width + 52))
    for row in results:
        print(f"  [{row['status']:4}] {row['check']:<{width}} {row['detail']}")
    failed = [row for row in results if row["status"] == FAIL]
    print("=" * (width + 52))
    print(f"  DEMO 17 PREFLIGHT: {'FAIL' if failed else 'PASS'} "
          f"({total - len(failed)}/{total} checks)")
    if exe is None:
        print("  NOTE: no nextnano++ executable on this machine, so the licensed "
              "deck-parse check did not run.")
    if verbose:
        for row in failed:
            print(f"    - {row['check']}: {row['detail']}")
    return 1 if failed else 0
