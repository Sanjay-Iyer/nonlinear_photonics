"""Demo 14 pre-run self-test (spec section 33).

Everything here runs without the licensed solver, so it can be executed on the
home laptop and again on the work laptop before any paid trial. The point is to
convert "it will probably work" into a list of named checks with a verdict, and
to fail on this machine's time rather than on the licensed machine's.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping

import numpy as np

import demo14
import grading14
import physics14
import runlog14
import solver14

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


def miniature_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """A 5-trial version of the campaign for harness testing.

    3 initialization + 2 BO. Small enough to run in seconds, large enough to
    exercise proposal, evaluation, checkpointing and the phase transition.
    """

    import copy

    small = copy.deepcopy(dict(cfg))
    small["optimization"] = dict(small["optimization"])
    small["optimization"].update({
        "target_completed_trials": 5,
        "initialization_trials": 3,
        "bo_trials": 2,
        "minimum_initial_per_profile": 0,
        "stratify_initialization_by_profile": False,
    })
    small["workflow"] = dict(small["workflow"])
    small["workflow"]["mock_solver"] = True
    return small


def _check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        detail = fn()
        return {"check": name, "status": PASS, "detail": detail}
    except AssertionError as exc:
        return {"check": name, "status": FAIL, "detail": str(exc)}
    except Exception as exc:  # noqa: BLE001 - a failing check must not abort the rest
        return {"check": name, "status": FAIL,
                "detail": f"{type(exc).__name__}: {exc}"}


def run_preflight(
    cfg: Mapping[str, Any], *, config_path: Path | None = None,
    machine: Any | None = None, machine_error: str | None = None,
) -> int:
    """Run every solver-free check and print a verdict. 0 on success."""

    results: list[dict[str, Any]] = []

    def config_loads() -> str:
        warnings = demo14.validate_config(cfg)
        return f"valid; {len(warnings)} warning(s)"

    def budget_resolves() -> str:
        opt = cfg["optimization"]
        i, b, t = (int(opt["initialization_trials"]), int(opt["bo_trials"]),
                   int(opt["target_completed_trials"]))
        assert i + b == t, f"{i} + {b} != {t}"
        return f"{i} init + {b} BO = {t} completed trials"

    def stratification_covers_every_profile() -> str:
        rng = np.random.default_rng(int(cfg["optimization"]["random_seed"]))
        design = demo14.stratified_initial_design(cfg, rng)
        families = list(cfg["optimization"]["search_space"]["grading_profile"]["values"])
        counts = {f: sum(1 for d in design if d["grading_profile"] == f) for f in families}
        minimum = int(cfg["optimization"].get("minimum_initial_per_profile", 2))
        missing = [f for f, c in counts.items() if c < minimum]
        assert not missing, f"profiles under-sampled: {missing} (counts {counts})"
        return f"{counts}"

    def grading_generators_work() -> str:
        rng = np.random.default_rng(7)
        bad = 0
        for case in grading14.sample_search_space(rng, 500):
            profile = grading14.build_profile(
                profile=case["profile"],
                barrier_thickness_nm=case["barrier_thickness_nm"],
                gaas_to_algaas_width_10_90_nm=case["gaas_to_algaas_width_10_90_nm"],
                algaas_to_gaas_width_10_90_nm=case["algaas_to_gaas_width_10_90_nm"],
                barrier_centre_nm=20.0, domain_nm=(0.0, 40.0), mesh_nm=0.05,
            )
            if not profile.diagnostics["profile_within_bounds"]:
                bad += 1
        assert bad == 0, f"{bad}/500 profiles left the allowed composition range"
        return "500/500 sampled geometries bounded and buildable"

    def no_preflight_rejection_exists() -> str:
        rng = np.random.default_rng(11)
        space = cfg["optimization"]["search_space"]
        rejected = 0
        for _ in range(300):
            params = {
                "asymmetry_s": rng.uniform(space["asymmetry_s"]["lower"],
                                           space["asymmetry_s"]["upper"]),
                "nominal_central_barrier_thickness_nm": rng.uniform(
                    space["nominal_central_barrier_thickness_nm"]["lower"],
                    space["nominal_central_barrier_thickness_nm"]["upper"]),
                "gaas_to_algaas_grading_width_10_90_nm": rng.uniform(
                    space["gaas_to_algaas_grading_width_10_90_nm"]["lower"],
                    space["gaas_to_algaas_grading_width_10_90_nm"]["upper"]),
                "algaas_to_gaas_grading_width_10_90_nm": rng.uniform(
                    space["algaas_to_gaas_grading_width_10_90_nm"]["lower"],
                    space["algaas_to_gaas_grading_width_10_90_nm"]["upper"]),
                "grading_profile": str(rng.choice(
                    space["grading_profile"]["values"])),
            }
            if not demo14.preflight(cfg, params)["accepted"]:
                rejected += 1
        assert rejected == 0, (
            f"{rejected}/300 candidates were rejected; Demo 14 is supposed to be "
            "feasible by construction, so this is an implementation bug"
        )
        return "300/300 candidates accepted (feasible by construction)"

    def chi2_absolute_mode_configures() -> str:
        settings = physics14.settings_from_config(cfg)
        assert settings.mode == "absolute", settings.mode
        assert settings.r_e_hh_nm is not None
        assert settings.n_wells_per_metre is not None
        return (f"r_e_hh={settings.r_e_hh_nm} nm, "
                f"N_z={settings.n_wells_per_metre:.6e} m^-1, "
                f"spin={settings.spin_degeneracy}")

    def formulations_agree() -> str:
        import chi2 as chi2mod

        z = np.linspace(0.0, 10.0, 401)
        env = np.zeros((401, 2))
        for i in range(2):
            raw = np.sin((i + 1) * np.pi * z / 10.0)
            env[:, i] = raw / np.sqrt(np.trapezoid(raw**2, z))
        electron = chi2mod.BandStates(z, np.array([1.5, 1.63]), env, "e")
        hole = chi2mod.BandStates(z, np.array([0.01, -0.011]), env, "hh")
        settings = physics14.settings_from_config(cfg)
        comparison = physics14.compare_formulations(electron, hole, 0.8, settings)
        assert comparison.relative_difference < 1e-9, comparison.relative_difference
        return f"energy vs angular-frequency agree to {comparison.relative_difference:.2e}"

    def k_measures_agree() -> str:
        settings = physics14.settings_from_config(cfg)
        radial = physics14.k_measure_radial(settings)
        cartesian = physics14.k_measure_cartesian(settings, points_per_axis=601)
        relative = abs(radial - cartesian) / radial
        assert relative < 5e-3, f"radial {radial} vs cartesian {cartesian}"
        return f"radial vs Cartesian k measure agree to {relative:.2e}"

    def template_renders() -> str:
        params = {
            "asymmetry_s": 0.42, "nominal_central_barrier_thickness_nm": 1.8,
            "gaas_to_algaas_grading_width_10_90_nm": 1.0,
            "algaas_to_gaas_grading_width_10_90_nm": 1.0,
            "grading_profile": "erf",
        }
        geometry = demo14.geometry_for(cfg, params)
        profile = demo14.build_grading(cfg, params, geometry)
        blocks = grading14.render_structure_blocks(profile)
        deck = demo14.render_deck(cfg, geometry, profile, blocks)
        assert "{{" not in deck, "template left unsubstituted placeholders"
        assert "ternary_import{" in deck
        assert "import{" in deck
        for required in ("global{", "contacts{", "grid{", "structure{", "classical{",
                         "quantum{", "run{"):
            assert required in deck, f"deck is missing {required}"
        return f"{len(deck.splitlines())}-line deck, erf via ternary_import"

    def linear_template_renders_natively() -> str:
        params = {
            "asymmetry_s": 0.42, "nominal_central_barrier_thickness_nm": 1.8,
            "gaas_to_algaas_grading_width_10_90_nm": 1.0,
            "algaas_to_gaas_grading_width_10_90_nm": 1.0,
            "grading_profile": "linear",
        }
        geometry = demo14.geometry_for(cfg, params)
        profile = demo14.build_grading(cfg, params, geometry)
        blocks = grading14.render_structure_blocks(profile)
        deck = demo14.render_deck(cfg, geometry, profile, blocks)
        # Compare against the deck's directives only: the template's comment
        # header names every render method, so a raw substring search would
        # match the documentation rather than the structure.
        directives = "\n".join(
            line for line in deck.splitlines() if not line.lstrip().startswith("#")
        )
        assert "ternary_linear{" in directives, "linear did not render natively"
        assert "ternary_import{" not in directives, "linear should not use an import"
        assert "import{" not in directives, "linear should emit no import block"
        return "linear uses native ternary_linear, no import"

    def run_directory_is_creatable_and_unique() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            a, id_a = runlog14.new_run_directory(Path(tmp), git_short_sha="abc123", mock=True)
            b, id_b = runlog14.new_run_directory(Path(tmp), git_short_sha="abc123", mock=True)
            assert a != b and id_a != id_b, "two runs collided"
            assert "MOCK" in a.name, "mock run directory is not marked"
            for sub in runlog14.RUN_SUBDIRS:
                assert (a / sub).is_dir(), f"missing {sub}"
        return "unique, marked, fully laid out"

    def logging_and_events_work() -> str:
        with tempfile.TemporaryDirectory() as tmp:
            root, run_id = runlog14.new_run_directory(
                Path(tmp), git_short_sha="abc123", mock=True
            )
            paths = runlog14.RunPaths(root)
            logger = runlog14.configure_logging(paths)
            logger.info("info line")
            logger.warning("warning line")
            logger.error("error line")
            runlog14.flush_logging(logger)
            events = runlog14.EventLog(paths.events_file, run_id)
            events.emit("RUN_STARTED", stage="test", status="ok")
            events.close()
            for name in ("run.log", "run_debug.log", "warnings.log", "errors.log"):
                assert (paths.logs / name).is_file(), f"missing {name}"
            assert "warning line" in (paths.logs / "warnings.log").read_text(encoding="utf-8")
            assert "error line" in (paths.logs / "errors.log").read_text(encoding="utf-8")
            rows = [json.loads(l) for l in
                    paths.events_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            assert rows and rows[0]["event_type"] == "RUN_STARTED"
            # Windows locks open files; release them or the directory cannot be
            # removed and descriptors leak across successive campaigns.
            runlog14.close_logging(logger)
        return "4 log files + events.jsonl written and populated"

    def json_serialization_is_strict() -> str:
        payload = {
            "numpy_int": np.int64(3), "numpy_float": np.float64(1.5),
            "numpy_bool": np.bool_(True), "array": np.array([1.0, 2.0]),
            "nan": float("nan"), "inf": float("inf"), "complex": complex(1, 2),
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = runlog14.write_json_atomic(Path(tmp) / "x.json", payload)
            loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["nan"] is None and loaded["inf"] is None, "non-finite leaked"
        assert loaded["numpy_int"] == 3 and loaded["array"] == [1.0, 2.0]
        return "NumPy types and non-finite floats serialize to strict JSON"

    def mock_solver_covers_every_behaviour() -> str:
        assert set(solver14.MOCK_BEHAVIOURS) >= {
            "success", "qc_failure", "nonzero_exit", "missing_output",
            "parser_failure", "timeout", "nan_objective",
        }
        return f"{len(solver14.MOCK_BEHAVIOURS)} behaviours available"

    def solver_timeout_is_finite() -> str:
        timeout = float(cfg["nextnano"]["solver_timeout_seconds"])
        assert 0 < timeout < 86400, timeout
        return f"{timeout:.0f} s"

    checks = [
        ("configuration loads and validates", config_loads),
        ("trial budget resolves", budget_resolves),
        ("initialization covers every grading profile", stratification_covers_every_profile),
        ("grading generators stay bounded", grading_generators_work),
        ("no preflight rejection is reachable", no_preflight_rejection_exists),
        ("absolute chi(2) configures", chi2_absolute_mode_configures),
        ("energy and angular-frequency forms agree", formulations_agree),
        ("radial and Cartesian k measures agree", k_measures_agree),
        ("imported-profile deck renders", template_renders),
        ("native linear deck renders", linear_template_renders_natively),
        ("run directory is unique and complete", run_directory_is_creatable_and_unique),
        ("logging and event journal work", logging_and_events_work),
        ("JSON serialization is strict", json_serialization_is_strict),
        ("mock solver covers every failure mode", mock_solver_covers_every_behaviour),
        ("solver timeout is finite", solver_timeout_is_finite),
    ]
    for name, fn in checks:
        results.append(_check(name, fn))

    if machine_error is not None:
        # The machine config exists but is wrong -- a missing path, a bad key.
        # Reported as one failed check rather than a traceback, because the
        # remaining checks above are still meaningful and still ran.
        results.append({
            "check": "machine configuration resolves", "status": FAIL,
            "detail": machine_error,
        })

    if machine is not None:
        # All four are resolved and verified independently. A licensed run needs
        # every one of them, and a missing licence or database fails deep inside
        # the solver with a message that looks like a physics problem.
        def machine_source() -> str:
            source = getattr(machine, "source_path", None)
            notes = list(getattr(machine, "discovery_notes", ()) or ())
            detail = str(source)
            if notes:
                detail += f"  [{'; '.join(notes)}]"
            return detail

        def solver_executable() -> str:
            exe = getattr(machine, "executable", None)
            assert exe, (
                "no nextnano++ executable resolved. On the licensed machine create "
                "nextnano/config/machines/nextnano_machine.local.yaml (it is "
                "gitignored, so git pull never supplies it)."
            )
            assert Path(exe).is_file(), f"nextnano++ executable not found: {exe}"
            return str(exe)

        def solver_license() -> str:
            path = getattr(machine, "license", None)
            assert path, "no nextnano++ license path resolved"
            assert Path(path).is_file(), f"nextnano++ license not found: {path}"
            return str(path)

        def solver_database() -> str:
            path = getattr(machine, "database", None)
            assert path, "no nextnano++ database resolved"
            assert Path(path).is_file(), f"nextnano++ database not found: {path}"
            return str(path)

        def solver_threads() -> str:
            threads = getattr(machine, "threads", None)
            assert threads is not None, "no thread count resolved"
            threads = int(threads)
            assert threads >= 1, f"thread count must be >= 1, got {threads}"
            return str(threads)

        def solver_enabled() -> str:
            enabled = bool(getattr(machine, "run_solver", False))
            assert enabled, (
                "run_solver resolved false: this machine will DRY-RUN, not "
                "execute. --gate and --run would report success without solving."
            )
            return "true (this machine will execute nextnano++)"

        results.append(_check("machine configuration source", machine_source))
        results.append(_check("nextnano++ executable", solver_executable))
        results.append(_check("nextnano++ license", solver_license))
        results.append(_check("nextnano++ database", solver_database))
        results.append(_check("nextnano++ threads", solver_threads))
        results.append(_check("nextnano++ solver enabled", solver_enabled))

    width = max(len(r["check"]) for r in results) + 2
    print("=" * (width + 30))
    print("  DEMO 14 REAL RUN PREFLIGHT")
    print("=" * (width + 30))
    for row in results:
        print(f"  [{row['status']:4}] {row['check']:<{width}} {row['detail']}")
    failed = [r for r in results if r["status"] == FAIL]
    print("=" * (width + 30))
    if failed:
        print(f"  DEMO 14 REAL RUN PREFLIGHT: FAIL ({len(failed)} of {len(results)})")
        for row in failed:
            print(f"    - {row['check']}: {row['detail']}")
        return 1
    print(f"  DEMO 14 REAL RUN PREFLIGHT: PASS ({len(results)} checks)")
    print("=" * (width + 30))
    return 0
