"""Demo 16C: one ACQW geometry and four linear grading-width cases.

This module contains no renderer and no nextnano++ output parser of its own.
It selects four inputs, calls the Demo 14 production geometry/grading/deck path,
uses Demo 16's parser and local interface metrology, and uses Demo 16B's tested
``Structure/alloy_composition.dat`` reader and optional physics analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import cases16c
import demo14
import demo16
import demo16b
import grading14
import runlog14

DEMO_ID = "16C_minimal_linear_grading_validation"
DEMO_VERSION = "demo16c-1.0.0"

INTERFACE_LEFT = "central_gaas_to_algaas"
INTERFACE_RIGHT = "central_algaas_to_gaas"

MAX_ABS_COMPOSITION_ERROR = 5.0e-3
MAX_RMS_COMPOSITION_ERROR = 1.0e-3
MAX_GRADING_WIDTH_ERROR_NM = 0.10
MAX_INTERFACE_POSITION_ERROR_NM = 0.10
FORBIDDEN_GRADING_WIDTHS_NM = (7.1, 2.9)
FORBIDDEN_WIDTH_MARGIN_NM = 0.40


def build_case(cfg: Mapping[str, Any], case: cases16c.GradingCase):
    """Build through Demo 14's authoritative production path."""

    params = case.parameters()
    geometry = demo14.geometry_for(cfg, params)
    profile = demo14.build_grading(cfg, params, geometry)
    blocks = grading14.render_structure_blocks(profile)
    deck = demo14.render_deck(cfg, geometry, profile, blocks)
    return geometry, profile, blocks, deck


def interface_widths(case: cases16c.GradingCase) -> dict[str, float]:
    """Requested width at all four interfaces in the production convention."""

    return {
        "outer_left_algaas_to_gaas": case.right_grading_width_nm,
        INTERFACE_LEFT: case.left_grading_width_nm,
        INTERFACE_RIGHT: case.right_grading_width_nm,
        "outer_right_gaas_to_algaas": case.left_grading_width_nm,
    }


def write_intended_profile(case_dir: Path, profile: grading14.CompositionProfile) -> Path:
    """Save the authoritative Python profile requested by the brief."""

    return runlog14.write_text_atomic(
        Path(case_dir) / "intended_profile.csv",
        "position_nm,expected_al_fraction\n"
        + "".join(
            f"{x:.6f},{al:.8f}\n"
            for x, al in zip(profile.x_nm, profile.al_fraction)
        ),
    )


def compare_compositions(
    profile: grading14.CompositionProfile,
    case: cases16c.GradingCase,
    x_real: np.ndarray,
    al_real: np.ndarray,
) -> dict[str, Any]:
    """The intentionally small Demo 16C comparison metric set.

    Widths and 50% crossings are measured only in windows local to the two
    central-barrier interfaces.  A whole-well crossing search cannot therefore
    return either the 7.1 nm or 2.9 nm well width.
    """

    x_real = np.asarray(x_real, dtype=float)
    al_real = np.asarray(al_real, dtype=float)
    intended = demo16b.intended_on(profile, x_real)
    residual = al_real - intended
    interfaces = profile.request["interfaces_nm"]
    measured = demo16.measure_interfaces(
        x_real,
        al_real,
        interfaces,
        interface_widths(case),
        cases16c.AL_FRACTION,
    )
    by_name = {item.name: item for item in measured}
    left = by_name[INTERFACE_LEFT]
    right = by_name[INTERFACE_RIGHT]
    invariants = demo16.structural_invariants(
        x_real, al_real, interfaces, cases16c.AL_FRACTION
    )

    realized_widths = [left.realized_width_10_90_nm, right.realized_width_10_90_nm]
    forbidden_hits = [
        {"interface": metric.name, "realized_width_nm": metric.realized_width_10_90_nm,
         "well_width_nm": forbidden}
        for metric in (left, right)
        if metric.realized_width_10_90_nm is not None
        for forbidden in FORBIDDEN_GRADING_WIDTHS_NM
        if abs(metric.realized_width_10_90_nm - forbidden) <= FORBIDDEN_WIDTH_MARGIN_NM
    ]

    max_abs = float(np.max(np.abs(residual)))
    rms = float(np.sqrt(np.mean(residual ** 2)))
    checks = {
        "max_absolute_error_within_tolerance": max_abs <= MAX_ABS_COMPOSITION_ERROR,
        "rms_error_within_tolerance": rms <= MAX_RMS_COMPOSITION_ERROR,
        "both_central_interfaces_found": all(
            value is not None
            for value in (left.realized_centre_nm, right.realized_centre_nm, *realized_widths)
        ),
        "grading_widths_within_tolerance": all(
            value is not None and abs(value - requested) <= MAX_GRADING_WIDTH_ERROR_NM
            for value, requested in zip(
                realized_widths,
                (case.left_grading_width_nm, case.right_grading_width_nm),
            )
        ),
        "interface_positions_within_tolerance": all(
            value is not None and value <= MAX_INTERFACE_POSITION_ERROR_NM
            for value in (left.centre_error_nm, right.centre_error_nm)
        ),
        "measurement_windows_are_local": left.window_isolated and right.window_isolated,
        "well_widths_not_reported_as_grading_widths": not forbidden_hits,
        "outer_barriers_and_two_wells_present": invariants["all_passed"],
    }
    checks["passed"] = all(checks.values())

    return {
        "comparison_points": int(x_real.size),
        "max_absolute_al_fraction_difference": max_abs,
        "rms_al_fraction_difference": rms,
        "expected_peak_al_fraction": float(np.max(intended)),
        "realized_peak_al_fraction": float(np.max(al_real)),
        "requested_left_grading_width_nm": float(case.left_grading_width_nm),
        "realized_left_10_90_grading_width_nm": left.realized_width_10_90_nm,
        "requested_right_grading_width_nm": float(case.right_grading_width_nm),
        "realized_right_10_90_grading_width_nm": right.realized_width_10_90_nm,
        "requested_left_interface_center_nm": float(interfaces[INTERFACE_LEFT]),
        "realized_left_interface_50_percent_crossing_nm": left.realized_centre_nm,
        "requested_right_interface_center_nm": float(interfaces[INTERFACE_RIGHT]),
        "realized_right_interface_50_percent_crossing_nm": right.realized_centre_nm,
        "left_interface_position_error_nm": left.centre_error_nm,
        "right_interface_position_error_nm": right.centre_error_nm,
        "left_outer_barrier_present": invariants["left_outer_barrier_present"],
        "right_outer_barrier_present": invariants["right_outer_barrier_present"],
        "well_1_is_gaas": invariants["thick_well_is_gaas"],
        "well_2_is_gaas": invariants["thin_well_is_gaas"],
        "forbidden_width_hits": forbidden_hits,
        "local_interface_metrics": [left.as_record(), right.as_record()],
        "checks": checks,
        "tolerances": {
            "max_absolute_al_fraction_difference": MAX_ABS_COMPOSITION_ERROR,
            "rms_al_fraction_difference": MAX_RMS_COMPOSITION_ERROR,
            "grading_width_nm": MAX_GRADING_WIDTH_ERROR_NM,
            "interface_position_nm": MAX_INTERFACE_POSITION_ERROR_NM,
        },
    }


@dataclass
class CaseOutcome:
    case_id: str
    name: str
    status: str = "pending"
    geometry: dict[str, Any] = field(default_factory=dict)
    intended_invariants: dict[str, Any] = field(default_factory=dict)
    grading_regions: dict[str, Any] = field(default_factory=dict)
    parser: dict[str, Any] = field(default_factory=dict)
    structure: dict[str, Any] = field(default_factory=dict)
    physics: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "status": self.status,
            "demo16c_version": DEMO_VERSION,
            "geometry": self.geometry,
            "intended_structural_invariants": self.intended_invariants,
            "grading_regions": self.grading_regions,
            "parser": self.parser,
            "structure": self.structure,
            "physics": self.physics,
            "failure_reason": self.failure_reason,
        }


def run_structure(
    cfg: Mapping[str, Any],
    case: cases16c.GradingCase,
    case_dir: Path,
    profile: grading14.CompositionProfile,
    blocks: Mapping[str, Any],
    deck: str,
    *,
    exe: Path,
    database: Path | None,
    license_path: Path | None,
) -> dict[str, Any]:
    """Run nextnano++ ``--structure`` and save its realized Al profile."""

    invocation = demo16.parse_deck(
        exe,
        database,
        case_dir,
        deck,
        blocks["datafile"],
        license_path=license_path,
        runmode="--structure",
        stage="structure",
        timeout=float(cfg["nextnano"].get("solver_timeout_seconds", 600)),
    )
    result: dict[str, Any] = {
        "passed": False,
        "invocation": invocation,
        "failure_reason": invocation.get("failure_reason"),
    }
    if not invocation["passed"]:
        return result
    try:
        source = demo16b.find_alloy_composition(Path(invocation["output_dir"]))
        x_real, al_real = demo16b.read_alloy_composition(source)
        intended = demo16b.intended_on(profile, x_real)
        comparison = compare_compositions(profile, case, x_real, al_real)
    except Exception as exc:  # noqa: BLE001 - preserved in the case result
        result["failure_reason"] = f"{type(exc).__name__}: {exc}"
        return result

    realized_path = runlog14.write_text_atomic(
        Path(case_dir) / "realized_profile.csv",
        "position_nm,realized_al_fraction\n"
        + "".join(f"{x:.6f},{al:.8f}\n" for x, al in zip(x_real, al_real)),
    )
    runlog14.write_text_atomic(
        Path(case_dir) / "structure" / "composition_comparison.csv",
        "position_nm,expected_al_fraction,realized_al_fraction,difference\n"
        + "".join(
            f"{x:.6f},{expected:.8f},{realized:.8f},{realized - expected:.8e}\n"
            for x, expected, realized in zip(x_real, intended, al_real)
        ),
    )
    metrics_path = runlog14.write_json_atomic(
        Path(case_dir) / "comparison_metrics.json", comparison
    )
    result.update({
        "passed": bool(comparison["checks"]["passed"]),
        "source_alloy_composition_path": str(source),
        "realized_profile_path": str(realized_path),
        "comparison_metrics_path": str(metrics_path),
        "comparison": comparison,
        "failure_reason": None,
    })
    if not result["passed"]:
        failed = [name for name, value in comparison["checks"].items()
                  if name != "passed" and not value]
        result["failure_reason"] = f"composition comparison failed: {failed}"
    return result


def run_case(
    cfg: Mapping[str, Any],
    case: cases16c.GradingCase,
    case_dir: Path,
    *,
    exe: Path | None,
    database: Path | None,
    license_path: Path | None = None,
    do_parse: bool = True,
    do_structure: bool = False,
) -> CaseOutcome:
    """Run one case, stopping immediately after any failed stage."""

    case_dir = Path(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    outcome = CaseOutcome(case.case_id, case.name)
    runlog14.write_json_atomic(
        case_dir / "requested_parameters.json",
        {**case.as_record(), "demo16c_version": DEMO_VERSION},
    )
    try:
        geometry, profile, blocks, deck = build_case(cfg, case)
    except Exception as exc:  # noqa: BLE001
        outcome.status = "render_failed"
        outcome.failure_reason = f"{type(exc).__name__}: {exc}"
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        return outcome

    outcome.geometry = geometry.as_record()
    outcome.intended_invariants = demo16.structural_invariants(
        profile.x_nm,
        profile.al_fraction,
        profile.request["interfaces_nm"],
        cases16c.AL_FRACTION,
    )
    outcome.grading_regions = demo16b.grading_regions_report(profile, blocks)
    write_intended_profile(case_dir, profile)

    if not outcome.intended_invariants["all_passed"]:
        outcome.status = "intended_structure_failed"
        outcome.failure_reason = "authoritative intended profile failed structural checks"
    elif not outcome.grading_regions["supported_by_demo16b"]:
        outcome.status = "unsupported_geometry"
        outcome.failure_reason = "linear grading regions overlap or were not rendered natively"
    elif exe is None:
        outcome.status = "parser_unavailable"
        outcome.failure_reason = "no nextnano++ executable resolved"
    else:
        if do_parse:
            outcome.parser = demo16.parse_deck(
                exe, database, case_dir, deck, blocks["datafile"],
                license_path=license_path,
            )
            if not outcome.parser["passed"]:
                outcome.status = "parser_failed"
                outcome.failure_reason = outcome.parser.get("failure_reason")
                runlog14.write_json_atomic(
                    case_dir / "case_result.json", outcome.as_record()
                )
                return outcome
            outcome.status = "parser_passed"
        if do_structure:
            outcome.structure = run_structure(
                cfg, case, case_dir, profile, blocks, deck,
                exe=exe, database=database, license_path=license_path,
            )
            if outcome.structure["passed"]:
                outcome.status = "structure_passed"
            else:
                outcome.status = "structure_failed"
                outcome.failure_reason = outcome.structure.get("failure_reason")

    runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
    return outcome


def solve_case(cfg: Mapping[str, Any], case: cases16c.GradingCase,
               case_dir: Path, *, machine: Any) -> dict[str, Any]:
    """Use Demo 16B's thin production-solver/output-analysis wrapper."""

    return demo16b.solve_case(cfg, case, case_dir, machine=machine)
