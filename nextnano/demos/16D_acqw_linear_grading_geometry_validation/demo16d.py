"""Demo 16D scientific core, incrementally extending the proven Demo 16C path."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import cases16d
import demo14
import demo16
import demo16b
import grading14
import runlog14
import solver14
import sweeps

DEMO_ID = cases16d.DEMO_ID
DEMO_VERSION = "demo16d-1.0.0"
INTERFACE_NAMES = (
    "outer_left_algaas_to_gaas",
    "central_gaas_to_algaas",
    "central_algaas_to_gaas",
    "outer_right_gaas_to_algaas",
)
MAX_ABS_COMPOSITION_ERROR = 5.0e-3
MAX_RMS_COMPOSITION_ERROR = 1.0e-3
MAX_INTERFACE_POSITION_ERROR_NM = 0.10
FORBIDDEN_GRADING_WIDTHS_NM = (7.1, 2.9)
FORBIDDEN_WIDTH_MARGIN_NM = 0.40
TARGET_WAVELENGTH_NM = 1550.0


def build_case(cfg: Mapping[str, Any], case: cases16d.GeometryCase):
    """Use the authoritative Demo 14 geometry, profile and production renderer."""

    geometry = demo14.geometry_for(cfg, case.parameters())
    profile = demo14.build_grading(cfg, case.parameters(), geometry)
    blocks = grading14.render_structure_blocks(profile)
    deck = demo14.render_deck(cfg, geometry, profile, blocks)
    return geometry, profile, blocks, deck


def interface_widths(case: cases16d.GeometryCase) -> dict[str, float]:
    return {
        INTERFACE_NAMES[0]: case.right_grading_width_nm,
        INTERFACE_NAMES[1]: case.left_grading_width_nm,
        INTERFACE_NAMES[2]: case.right_grading_width_nm,
        INTERFACE_NAMES[3]: case.left_grading_width_nm,
    }


def render_method(blocks: Mapping[str, Any]) -> str:
    return "ternary_import" if "ternary_import" in blocks["structure_block"] else "ternary_linear"


def overlap_geometry(
    profile: grading14.CompositionProfile,
    case: cases16d.GeometryCase,
) -> dict[str, Any]:
    """Describe the one production-defined linear-ramp overlap explicitly."""

    interfaces = profile.request["interfaces_nm"]
    z2 = float(interfaces[INTERFACE_NAMES[1]])
    z3 = float(interfaces[INTERFACE_NAMES[2]])
    half_left = 0.5 * float(profile.request["natural_scale_rise_nm"])
    half_right = 0.5 * float(profile.request["natural_scale_fall_nm"])
    overlap_start = z3 - half_right
    overlap_end = z2 + half_left
    overlap_width = max(0.0, overlap_end - overlap_start)
    report = demo16.overlap_report(
        profile.x_nm, profile.al_fraction, interfaces, cases16d.AL_FRACTION
    )
    return {
        **report,
        "overlap": bool(overlap_width > 1e-12),
        "overlap_start_nm": overlap_start if overlap_width else None,
        "overlap_end_nm": overlap_end if overlap_width else None,
        "overlap_width_nm": overlap_width,
        "reaches_90_percent_of_nominal": bool(
            report["expected_peak_al_fraction"] >= 0.90 * cases16d.AL_FRACTION
        ),
        "true_flat_central_plateau_exists": bool(report["nominal_plateau_exists"]),
        "case_declares_overlap": bool(case.overlap),
    }


def _interface_records(
    x_nm: np.ndarray,
    al_fraction: np.ndarray,
    profile: grading14.CompositionProfile,
    case: cases16d.GeometryCase,
) -> list[dict[str, Any]]:
    return [
        metric.as_record()
        for metric in demo16.measure_interfaces(
            x_nm,
            al_fraction,
            profile.request["interfaces_nm"],
            interface_widths(case),
            cases16d.AL_FRACTION,
        )
    ]


def _geometry_metrics(
    records: list[dict[str, Any]], case: cases16d.GeometryCase
) -> dict[str, Any]:
    by_name = {row["interface"]: row for row in records}
    centres = [by_name[name].get("realized_centre_nm") for name in INTERFACE_NAMES]
    well_1, well_2 = case.well_widths_nm()

    def extent(a: int, b: int) -> float | None:
        if centres[a] is None or centres[b] is None:
            return None
        return float(centres[b] - centres[a])

    realized_well_1 = extent(0, 1)
    realized_barrier = extent(1, 2)
    realized_well_2 = extent(2, 3)
    realized_total = (
        None
        if realized_well_1 is None or realized_well_2 is None
        else realized_well_1 + realized_well_2
    )
    return {
        "requested_well_1_nm": well_1,
        "realized_well_1_nm": realized_well_1,
        "requested_central_barrier_nm": case.central_barrier_nm,
        "realized_central_barrier_nm": realized_barrier,
        "requested_well_2_nm": well_2,
        "realized_well_2_nm": realized_well_2,
        "requested_total_gaas_well_nm": cases16d.TOTAL_WELL_NM,
        "realized_total_gaas_well_nm": realized_total,
    }


def compare_compositions(
    profile: grading14.CompositionProfile,
    case: cases16d.GeometryCase,
    x_real: np.ndarray,
    al_real: np.ndarray,
) -> dict[str, Any]:
    """Compare authoritative and realized profiles, retaining local metrology."""

    x_real = np.asarray(x_real, dtype=float)
    al_real = np.asarray(al_real, dtype=float)
    intended = demo16b.intended_on(profile, x_real)
    residual = al_real - intended
    intended_interfaces = _interface_records(
        profile.x_nm, profile.al_fraction, profile, case
    )
    realized_interfaces = _interface_records(x_real, al_real, profile, case)
    geometry = _geometry_metrics(realized_interfaces, case)
    invariants = demo16.structural_invariants(
        x_real, al_real, profile.request["interfaces_nm"], cases16d.AL_FRACTION
    )
    intended_overlap = overlap_geometry(profile, case)
    realized_overlap = demo16.overlap_report(
        x_real, al_real, profile.request["interfaces_nm"], cases16d.AL_FRACTION
    )
    realized_overlap.update({
        "overlap": realized_overlap["grades_overlap"],
        "reaches_90_percent_of_nominal": bool(
            realized_overlap["realized_peak_al_fraction"]
            >= 0.90 * cases16d.AL_FRACTION
        ),
        "true_flat_central_plateau_exists": bool(
            realized_overlap["nominal_plateau_exists"]
        ),
    })
    forbidden_hits = [
        {"interface": row["interface"], "realized_width_nm": row.get("realized_width_10_90_nm"),
         "well_width_nm": forbidden}
        for row in realized_interfaces
        if row.get("realized_width_10_90_nm") is not None
        for forbidden in FORBIDDEN_GRADING_WIDTHS_NM
        if abs(row["realized_width_10_90_nm"] - forbidden) <= FORBIDDEN_WIDTH_MARGIN_NM
    ]
    max_abs = float(np.max(np.abs(residual)))
    rms = float(np.sqrt(np.mean(residual**2)))
    checks = {
        "max_absolute_error_within_tolerance": max_abs <= MAX_ABS_COMPOSITION_ERROR,
        "rms_error_within_tolerance": rms <= MAX_RMS_COMPOSITION_ERROR,
        "measurement_windows_are_local": all(
            row["window_isolated_from_other_interfaces"] for row in realized_interfaces
        ),
        "well_widths_not_reported_as_grading_widths": not forbidden_hits,
        "outer_barriers_and_two_wells_present": bool(invariants["all_passed"]),
        "overlap_classification_matches_request": bool(
            realized_overlap["overlap"] == case.overlap
        ),
        "overlap_peak_matches_authoritative_profile": bool(
            abs(
                realized_overlap["realized_peak_al_fraction"]
                - intended_overlap["expected_peak_al_fraction"]
            )
            <= MAX_ABS_COMPOSITION_ERROR
        ),
        "overlap_does_not_fabricate_nominal_plateau": bool(
            not case.overlap or not realized_overlap["true_flat_central_plateau_exists"]
        ),
    }
    checks["passed"] = all(checks.values())
    return {
        "comparison_points": int(x_real.size),
        "max_absolute_al_fraction_difference": max_abs,
        "rms_al_fraction_difference": rms,
        "expected_peak_al_fraction": intended_overlap["expected_peak_al_fraction"],
        "realized_peak_al_fraction": realized_overlap["realized_peak_al_fraction"],
        "geometry": geometry,
        "requested_asymmetry_s": case.asymmetry_s,
        "intended_interface_metrics": intended_interfaces,
        "realized_interface_metrics": realized_interfaces,
        "intended_overlap": intended_overlap,
        "realized_overlap": realized_overlap,
        "structural_invariants": invariants,
        "forbidden_width_hits": forbidden_hits,
        "checks": checks,
        "tolerances": {
            "max_absolute_al_fraction_difference": MAX_ABS_COMPOSITION_ERROR,
            "rms_al_fraction_difference": MAX_RMS_COMPOSITION_ERROR,
            "interface_position_nm": MAX_INTERFACE_POSITION_ERROR_NM,
        },
    }


@dataclass
class CaseOutcome:
    case_id: str
    name: str
    status: str = "pending"
    geometry: dict[str, Any] = field(default_factory=dict)
    grading: dict[str, Any] = field(default_factory=dict)
    render_method: str = ""
    intended_invariants: dict[str, Any] = field(default_factory=dict)
    overlap: dict[str, Any] = field(default_factory=dict)
    parser: dict[str, Any] = field(default_factory=dict)
    structure: dict[str, Any] = field(default_factory=dict)
    physics: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id, "name": self.name, "status": self.status,
            "demo16d_version": DEMO_VERSION, "geometry": self.geometry,
            "grading": self.grading, "render_method": self.render_method,
            "intended_structural_invariants": self.intended_invariants,
            "overlap": self.overlap, "parser": self.parser,
            "structure": self.structure, "physics": self.physics,
            "failure_reason": self.failure_reason,
        }


def write_intended_profile(case_dir: Path, profile: grading14.CompositionProfile) -> Path:
    return runlog14.write_text_atomic(
        Path(case_dir) / "intended_profile.csv",
        "position_nm,expected_al_fraction\n" + "".join(
            f"{x:.6f},{al:.10f}\n" for x, al in zip(profile.x_nm, profile.al_fraction)
        ),
    )


def run_structure(
    cfg: Mapping[str, Any], case: cases16d.GeometryCase, case_dir: Path,
    profile: grading14.CompositionProfile, blocks: Mapping[str, Any], deck: str,
    *, exe: Path, database: Path | None, license_path: Path | None,
) -> dict[str, Any]:
    invocation = demo16.parse_deck(
        exe, database, case_dir, deck, blocks["datafile"],
        license_path=license_path, runmode="--structure", stage="structure",
        timeout=float(cfg["nextnano"].get("solver_timeout_seconds", 600)),
    )
    result: dict[str, Any] = {
        "passed": False, "invocation": invocation,
        "failure_reason": invocation.get("failure_reason"),
    }
    if not invocation["passed"]:
        return result
    try:
        source = demo16b.find_alloy_composition(Path(invocation["output_dir"]))
        x_real, al_real = demo16b.read_alloy_composition(source)
        intended = demo16b.intended_on(profile, x_real)
        comparison = compare_compositions(profile, case, x_real, al_real)
    except Exception as exc:  # noqa: BLE001
        result["failure_reason"] = f"{type(exc).__name__}: {exc}"
        return result
    realized_path = runlog14.write_text_atomic(
        Path(case_dir) / "realized_profile.csv",
        "position_nm,realized_al_fraction\n" + "".join(
            f"{x:.6f},{al:.10f}\n" for x, al in zip(x_real, al_real)
        ),
    )
    runlog14.write_text_atomic(
        Path(case_dir) / "structure" / "composition_comparison.csv",
        "position_nm,expected_al_fraction,realized_al_fraction,difference\n"
        + "".join(
            f"{x:.6f},{expected:.10f},{realized:.10f},{realized-expected:.8e}\n"
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
        "comparison": comparison, "failure_reason": None,
    })
    if not result["passed"]:
        failed = [key for key, value in comparison["checks"].items()
                  if key != "passed" and not value]
        result["failure_reason"] = f"composition comparison failed: {failed}"
    return result


def run_case(
    cfg: Mapping[str, Any], case: cases16d.GeometryCase, case_dir: Path,
    *, exe: Path | None, database: Path | None, license_path: Path | None = None,
    do_parse: bool = True, do_structure: bool = False,
) -> CaseOutcome:
    """Render, parse and validate in order, stopping after the first failure."""

    case_dir = Path(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    outcome = CaseOutcome(case.case_id, case.name)
    runlog14.write_json_atomic(
        case_dir / "requested_parameters.json",
        {**case.as_record(), "demo16d_version": DEMO_VERSION},
    )
    try:
        geometry, profile, blocks, deck = build_case(cfg, case)
    except Exception as exc:  # noqa: BLE001
        outcome.status = "render_failed"
        outcome.failure_reason = f"{type(exc).__name__}: {exc}"
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        return outcome
    outcome.geometry = geometry.as_record()
    outcome.grading = dict(profile.diagnostics)
    outcome.render_method = render_method(blocks)
    outcome.overlap = overlap_geometry(profile, case)
    outcome.intended_invariants = demo16.structural_invariants(
        profile.x_nm, profile.al_fraction,
        profile.request["interfaces_nm"], cases16d.AL_FRACTION,
    )
    write_intended_profile(case_dir, profile)
    expected_render = "ternary_import" if case.overlap else "ternary_linear"
    if not outcome.intended_invariants["all_passed"]:
        outcome.status = "intended_structure_failed"
        outcome.failure_reason = "authoritative intended profile failed structural checks"
    elif outcome.overlap["overlap"] != case.overlap:
        outcome.status = "overlap_classification_failed"
        outcome.failure_reason = "authoritative overlap classification disagrees with case"
    elif outcome.render_method != expected_render:
        outcome.status = "render_method_failed"
        outcome.failure_reason = f"expected {expected_render}, got {outcome.render_method}"
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
                runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
                return outcome
            outcome.status = "parser_passed"
        if do_structure:
            outcome.structure = run_structure(
                cfg, case, case_dir, profile, blocks, deck,
                exe=exe, database=database, license_path=license_path,
            )
            outcome.status = "structure_passed" if outcome.structure["passed"] else "structure_failed"
            outcome.failure_reason = outcome.structure.get("failure_reason")
    runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
    return outcome


def physics_raw_output_dir(case_dir: Path, case: cases16d.GeometryCase) -> Path:
    case_dir = Path(case_dir)
    run_root = case_dir.parent.parent if case_dir.parent.name == "cases" else case_dir.parent
    suffix = case.case_id.rsplit("_", 1)[-1]
    raw = run_root / f"p{suffix}"
    warning = sweeps.check_path_budget(raw)
    if warning:
        raise RuntimeError(warning)
    return raw


def full_physics_command(
    cfg: Mapping[str, Any], case: cases16d.GeometryCase, case_dir: Path, *, machine: Any
) -> list[str]:
    return solver14.real_argv(
        executable=Path(machine.executable),
        database=Path(machine.database) if getattr(machine, "database", None) else None,
        license_path=Path(machine.license) if getattr(machine, "license", None) else None,
        deck=Path(case_dir) / "physics" / "nextnano_input" / "case.in",
        output_dir=physics_raw_output_dir(case_dir, case),
        threads=int(cfg["nextnano"].get("threads", 1)),
    )


def solve_case(
    cfg: Mapping[str, Any], case: cases16d.GeometryCase, case_dir: Path, *, machine: Any
) -> dict[str, Any]:
    """Run Demo 16B's gated full solve; never analyse failed or incomplete output."""

    raw_output = physics_raw_output_dir(case_dir, case)
    record = demo16b.solve_case(
        cfg, case, case_dir, machine=machine, raw_output_dir=raw_output
    )
    if not record.get("passed"):
        record.setdefault("diagnostics", {})["raw_output_dir"] = str(raw_output)
        runlog14.write_json_atomic(
            Path(case_dir) / "physics" / "physics_result.json", record
        )
    return record


def analyse_optics(
    cfg: Mapping[str, Any], case: cases16d.GeometryCase, case_dir: Path,
    raw_output: Path,
) -> dict[str, Any]:
    """Evaluate the established Demo 11/14 absolute chi2 spectrum on real states."""

    geometry, profile, _blocks, _deck = build_case(cfg, case)
    optical_root = Path(case_dir) / "physics" / "optical"
    parsed = optical_root / "parsed"
    plots_dir = optical_root / "plots"
    parsed.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)
    metrics = demo14.analyse_real_trial(
        cfg,
        {"nextnano_output": Path(raw_output), "parsed": parsed, "plots": plots_dir},
        geometry,
        profile,
    )
    spectrum_path = parsed / "chi2_focused.csv"
    if not spectrum_path.is_file():
        raise RuntimeError(f"production optical analysis did not write {spectrum_path}")
    spectrum = np.loadtxt(spectrum_path, delimiter=",", skiprows=1)
    wavelength = np.asarray(spectrum[:, 0], dtype=float)
    magnitude = np.asarray(spectrum[:, 3], dtype=float)
    chi2_1550 = float(np.interp(TARGET_WAVELENGTH_NM, wavelength, magnitude))
    peak_index = int(np.argmax(magnitude))
    peak_nm = float(wavelength[peak_index])
    peak_magnitude = float(magnitude[peak_index])
    production_value = metrics.get("chi2_relative_at_reference")
    if production_value is not None and not np.isclose(
        chi2_1550, float(production_value), rtol=1e-10, atol=1e-12
    ):
        raise RuntimeError(
            "1550 nm spectrum interpolation disagrees with production evaluation: "
            f"{chi2_1550} versus {production_value}"
        )
    result = {
        "passed": True,
        "case_id": case.case_id,
        "target_wavelength_nm": TARGET_WAVELENGTH_NM,
        "chi2_at_1550": chi2_1550,
        "chi2_units": metrics.get("chi2_units"),
        "spectral_peak_wavelength_nm": peak_nm,
        "spectral_peak_chi2": peak_magnitude,
        "detuning_from_1550_nm": peak_nm - TARGET_WAVELENGTH_NM,
        "detuning_sign_convention": "peak_wavelength_nm - 1550_nm",
        "spectrum_path": str(spectrum_path),
        "analysis_settings_path": str(parsed / "chi2_settings.json"),
        "selected_states_path": str(parsed / "state_count_audit.json"),
        "production_metrics": metrics,
    }
    runlog14.write_json_atomic(optical_root / "optical_result.json", result)
    return result
