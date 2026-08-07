"""Demo 14 licensed startup gate: the two things only the work laptop can prove.

**Gate A -- import equivalence.** Three of the four grading families reach
nextnano++ through ``ternary_import``, a path no nextnano++ instance in this
project has ever executed: the free build parses import decks and then refuses
them outright ("does not allow importing files or analytical functions"). If the
solver interprets an imported profile differently from what we intend --
coordinate origin, region-relative versus absolute ``x``, interpolation between
samples -- then 24 of 30 campaign trials silently solve the wrong material and
still produce plausible pm/V numbers. Nothing downstream would catch it.

The test builds the *same physical linear profile* twice, natively via
``ternary_linear`` and as a high-resolution imported table, and requires the two
solves to agree. Two licensed runs to de-risk twenty-four.

**Gate B -- paper reference.** The nominal Ramesh structure, solved and compared
against published values. A miss is recorded, not corrected; the gate fails only
on results that are technically invalid or wildly unphysical, because the whole
point of a beta campaign is to find out where we actually stand.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml

import demo14
import grading14
import physics14
import runlog14
import solver14

GATE_RESULT_NAME = "demo14_startup_gate_result.json"
GATE_DIR_NAME = "demo14_startup_gate"


def latest_gate_verdict(results_root: Path) -> bool | None:
    """``True`` only when a recorded gate passed. Anything else blocks the run."""

    directory = Path(results_root) / demo14.DEMO_DIR.name / GATE_DIR_NAME
    path = directory / GATE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    verdict = payload.get("gate_passed")
    # Explicitly `is True`: a null verdict means the gate could not be evaluated
    # and must never read as a pass.
    return True if verdict is True else verdict


def _equivalence_parameters(cfg: Mapping[str, Any]) -> dict[str, Any]:
    spec = cfg["startup_gate"]["import_equivalence"]
    return {
        "asymmetry_s": float(cfg["paper_reference"]["structure"]["asymmetry_s"]),
        "nominal_central_barrier_thickness_nm": float(spec["barrier_thickness_nm"]),
        "gaas_to_algaas_grading_width_10_90_nm": float(spec["grading_width_10_90_nm"]),
        "algaas_to_gaas_grading_width_10_90_nm": float(spec["grading_width_10_90_nm"]),
        "grading_profile": str(spec.get("profile", "linear")),
    }


def build_equivalence_decks(cfg: Mapping[str, Any], destination: Path) -> dict[str, Any]:
    """Render the native and imported decks for the same linear profile.

    Solver-free, so the home laptop can verify that the two decks really do
    describe the same composition before the licensed machine spends time on
    them. That check is what makes a disagreement downstream attributable to
    nextnano++ rather than to us.
    """

    destination = Path(destination)
    parameters = _equivalence_parameters(cfg)
    geometry = demo14.geometry_for(cfg, parameters)
    profile = demo14.build_grading(cfg, parameters, geometry)

    native_blocks = grading14.render_structure_blocks(profile)
    if native_blocks["structure_block"].count("ternary_linear{") == 0:
        raise RuntimeError("gate A requires the linear family to render natively")

    # Force the same profile down the import path by rendering it as if it were
    # a non-native family. The composition array is identical, so any difference
    # in the solved result is attributable to import handling alone.
    import_blocks = {
        "import_block": (
            "import{\n"
            '    file{ name = "al_profile"  filename = "al_profile.dat"  '
            "format = DAT  number_of_dimensions = 1 }\n"
            "    output_imports{}\n"
            "}\n"
        ),
        "structure_block": (
            '        ternary_import{ name = "Al(x)Ga(1-x)As"  '
            'import_from = "al_profile" }\n'
        ),
        "datafile": grading14.import_datafile(profile),
    }

    cases: dict[str, Any] = {}
    for name, blocks in (("gate_a_native_linear", native_blocks),
                         ("gate_b_imported_linear", import_blocks)):
        case_dir = destination / name
        (case_dir / "nextnano_input").mkdir(parents=True, exist_ok=True)
        (case_dir / "nextnano_output").mkdir(parents=True, exist_ok=True)
        (case_dir / "logs").mkdir(parents=True, exist_ok=True)
        deck = case_dir / "nextnano_input" / "case.in"
        runlog14.write_text_atomic(deck, demo14.render_deck(cfg, geometry, profile, blocks))
        if blocks["datafile"]:
            runlog14.write_text_atomic(
                case_dir / "nextnano_input" / "al_profile.dat", blocks["datafile"]
            )
        cases[name] = {
            "directory": str(case_dir),
            "deck": str(deck),
            "render_method": "ternary_linear" if "native" in name else "ternary_import",
        }
    runlog14.write_json_atomic(
        destination / "equivalence_profile.json",
        {"request": dict(profile.request), "realized": dict(profile.diagnostics),
         "parameters": parameters, "geometry": geometry.as_record()},
    )
    return {"cases": cases, "profile": profile, "geometry": geometry,
            "parameters": parameters}


def compare_equivalence(
    native: Mapping[str, Any], imported: Mapping[str, Any], tolerances: Mapping[str, Any]
) -> dict[str, Any]:
    """Field-by-field comparison of the two solves, with an explicit verdict."""

    rows: list[dict[str, Any]] = []

    def compare(field: str, tolerance_key: str, relative: bool = False) -> None:
        a, b = native.get(field), imported.get(field)
        if a is None or b is None:
            rows.append({"field": field, "native": a, "imported": b,
                         "difference": None, "passed": False,
                         "note": "missing on one side"})
            return
        if isinstance(a, (list, tuple)):
            a_arr, b_arr = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
            if a_arr.shape != b_arr.shape:
                rows.append({"field": field, "native": a, "imported": b,
                             "difference": None, "passed": False,
                             "note": "shape mismatch"})
                return
            difference = float(np.max(np.abs(a_arr - b_arr)))
        else:
            difference = abs(float(a) - float(b))
            if relative and float(a) != 0.0:
                difference /= abs(float(a))
        bound = float(tolerances[tolerance_key])
        rows.append({"field": field, "native": a, "imported": b,
                     "difference": difference, "tolerance": bound,
                     "passed": bool(difference <= bound)})

    compare("electron_energies_eV", "electron_energy_eV")
    compare("heavy_hole_energies_eV", "hole_energy_eV")
    compare("chi2_xzx_abs_at_1550_pm_per_V", "chi2_relative", relative=True)
    compare("peak_wavelength_nm", "chi2_relative", relative=True)
    compare("maximum_boundary_probability", "overlap_absolute")

    passed = bool(rows) and all(row["passed"] for row in rows)
    return {
        "rows": rows,
        "passed": passed,
        "failed_fields": [r["field"] for r in rows if not r["passed"]],
    }


def run_startup_gate(
    cfg: Mapping[str, Any], *, results_root: Path, machine: Any | None,
    config_path: Path | None = None,
) -> int:
    """Execute both gates on the licensed machine and record a verdict."""

    destination = Path(results_root) / demo14.DEMO_DIR.name / GATE_DIR_NAME
    destination.mkdir(parents=True, exist_ok=True)
    paths = runlog14.RunPaths(destination)
    for sub in runlog14.RUN_SUBDIRS:
        (destination / sub).mkdir(parents=True, exist_ok=True)
    logger = runlog14.configure_logging(paths)

    logger.info("=" * 74)
    logger.info("  DEMO 14 LICENSED STARTUP GATE")
    logger.info("=" * 74)
    logger.info("  Destination : %s", destination)
    # Echoed in full so the gate log records exactly which licensed installation
    # produced the result, and so it can be compared against --preflight.
    logger.info("  Machine cfg : %s", getattr(machine, "source_path", None))
    logger.info("  Executable  : %s", getattr(machine, "executable", None))
    logger.info("  License     : %s", getattr(machine, "license", None))
    logger.info("  Database    : %s", getattr(machine, "database", None))
    logger.info("  Threads     : %s", getattr(machine, "threads", None))
    logger.info("  run_solver  : %s", getattr(machine, "run_solver", None))
    logger.info("  Paid solver calls : 2 (native linear, imported linear)")
    logger.info("=" * 74)

    prepared = build_equivalence_decks(cfg, destination)
    tolerances = cfg["startup_gate"]["import_equivalence"]["tolerances"]

    if machine is None or not getattr(machine, "run_solver", False):
        payload = {
            "gate_passed": None,
            "gate_unavailable_reason": (
                "no licensed nextnano++ on this machine; the decks were rendered "
                "and verified but neither was executed."
            ),
            "cases": prepared["cases"],
            "solver_calls_planned": 2,
            "generated_utc": runlog14.utc_now(),
        }
        runlog14.write_json_atomic(destination / GATE_RESULT_NAME, payload)
        logger.error("GATE NOT EVALUATED: %s", payload["gate_unavailable_reason"])
        logger.info("Decks written to %s for inspection.", destination)
        return 3

    results: dict[str, Any] = {}
    for name, case in prepared["cases"].items():
        case_dir = Path(case["directory"])
        logger.info("Running %s ...", name)
        try:
            invocation = solver14.execute_real(
                executable=Path(machine.executable),
                database=Path(machine.database) if getattr(machine, "database", None) else None,
                license_path=Path(machine.license) if getattr(machine, "license", None) else None,
                deck=Path(case["deck"]),
                output_dir=case_dir / "nextnano_output",
                threads=int(cfg["nextnano"].get("threads", 1)),
                timeout_seconds=float(cfg["nextnano"]["solver_timeout_seconds"]),
                logs_dir=case_dir / "logs",
            )
            metrics = demo14.analyse_real_trial(
                cfg, {
                    "root": case_dir,
                    "nextnano_output": case_dir / "nextnano_output",
                    "parsed": case_dir / "parsed",
                    "plots": case_dir / "plots",
                }, prepared["geometry"], prepared["profile"],
            )
            results[name] = {"metrics": metrics, "solver": invocation.as_record()}
        except Exception as exc:
            logger.exception("%s failed", name)
            payload = {
                "gate_passed": None,
                "gate_unavailable_reason": f"{name} failed: {type(exc).__name__}: {exc}",
                "cases": prepared["cases"],
                "results": results,
                "generated_utc": runlog14.utc_now(),
            }
            runlog14.write_json_atomic(destination / GATE_RESULT_NAME, payload)
            return 4

    comparison = compare_equivalence(
        results["gate_a_native_linear"]["metrics"],
        results["gate_b_imported_linear"]["metrics"],
        tolerances,
    )
    paper = _paper_reference_check(cfg, results["gate_a_native_linear"]["metrics"])

    gate_passed = bool(comparison["passed"] and paper["technically_valid"])
    payload = {
        "gate_passed": gate_passed,
        "gate_unavailable_reason": None,
        "import_equivalence": comparison,
        "paper_reference": paper,
        "cases": prepared["cases"],
        "results": results,
        "solver_calls_planned": 2,
        "generated_utc": runlog14.utc_now(),
    }
    runlog14.write_json_atomic(destination / GATE_RESULT_NAME, payload)

    logger.info("=" * 74)
    for row in comparison["rows"]:
        logger.info("  %-38s native=%-14s imported=%-14s diff=%-12s %s",
                    row["field"], _short(row["native"]), _short(row["imported"]),
                    _short(row.get("difference")), "PASS" if row["passed"] else "FAIL")
    logger.info("-" * 74)
    logger.info("  Paper reference plausible : %s", paper["plausible"])
    logger.info("  Paper reference valid     : %s", paper["technically_valid"])
    logger.info("=" * 74)
    if gate_passed:
        logger.info("  GATE PASSED -- the 30-trial campaign may be launched.")
        logger.info("  Next:  python run_demo14.py --run")
    else:
        logger.error("  GATE FAILED -- do NOT launch the campaign.")
        logger.error("  Failed fields: %s", comparison["failed_fields"])
    logger.info("=" * 74)
    runlog14.flush_logging(logger)
    return 0 if gate_passed else 5


def _short(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (list, tuple)):
        return f"[{len(value)} values]"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _paper_reference_check(
    cfg: Mapping[str, Any], metrics: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare against published values without ever fitting to them."""

    band = cfg["paper_reference"].get("plausibility_band_pm_per_V", [50.0, 50000.0])
    value = metrics.get("chi2_xzx_abs_at_1550_pm_per_V")
    finite = value is not None and math.isfinite(float(value))
    plausible = bool(finite and float(band[0]) <= float(value) <= float(band[1]))
    expectations = dict(cfg["paper_reference"].get("expectations") or {})
    comparisons = [
        {
            "target": name,
            "published_pm_per_V": published,
            "ours_pm_per_V": value,
            "ratio_ours_over_published": (
                float(value) / float(published) if finite and published else None
            ),
        }
        for name, published in expectations.items()
        if name.startswith("chi2_")
    ]
    return {
        "chi2_xzx_abs_at_1550_pm_per_V": value,
        "peak_wavelength_nm": metrics.get("peak_wavelength_nm"),
        "plausibility_band_pm_per_V": list(band),
        "plausible": plausible,
        # A disagreement with the paper is a scientific finding, not a gate
        # failure; only a technically invalid result blocks the campaign.
        "technically_valid": bool(finite and metrics.get("physical_qc_valid", False)),
        "comparisons": comparisons,
        "fitted": False,
    }
