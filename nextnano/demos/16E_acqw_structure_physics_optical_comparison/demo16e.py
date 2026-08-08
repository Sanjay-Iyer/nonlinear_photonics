"""Demo 16E scientific core: ten fixed ACQW structures, compared.

Everything physical here is Demo 14's or Demo 11's. Demo 16E chooses ten
parameter vectors, three deck representations and the comparisons that turn ten
independent solves into one readable picture:

    structure -> composition -> quantum states -> localization -> chi2(lambda)

There is no optimizer, no surrogate, no acquisition function and no ranking. A
case with a larger chi2 or a smaller detuning is described as such and nothing
follows from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import cases16e
import demo14
import demo16
import demo16b
import grading14
import runlog14
import solver14
import sweeps

DEMO_ID = cases16e.DEMO_ID
DEMO_VERSION = "demo16e-1.0.0"
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
TARGET_WAVELENGTH_NM = cases16e.TARGET_WAVELENGTH_NM

#: Narrowest window the interface metrology may open, in nanometres. Demo 16's
#: locator sizes its window from the requested 10-90 width; at an abrupt
#: interface that width is essentially zero and the window would hold fewer than
#: the three mesh points a crossing search needs, so the locator would report
#: nothing at all. 0.40 nm is the narrowest real grade in this study, it still
#: clears every neighbouring interface, and it changes nothing for the nine
#: graded cases because their own widths are already at least that large.
MIN_METROLOGY_WINDOW_NM = 0.40

#: Half-width of the region excluded around each interface when an abrupt case's
#: composition is compared point by point. A step sampled on a finite grid is
#: ambiguous within one cell: whether the boundary cell is assigned to the well
#: or to the barrier is a grid convention, not a composition error. One mesh cell
#: either side is excluded from the gated maximum, and both the all-points
#: maximum and the number of excluded points are reported beside it.
ABRUPT_INTERFACE_EXCLUSION_NM = cases16e.MESH_NM

#: Localization region labels, in growth order.
REGION_LABELS = (("left", "thick_well"), ("barrier", "central_barrier"),
                 ("right", "thin_well"))
STATE_LABELS = ("E1", "E2", "HH1", "HH2")
LOCALIZATION_CONVENTION = (
    "localization L = P_left - P_right, computed from the nextnano++ probability "
    "density of the state. L > 0 means the state sits mainly in well 1 (the "
    "thick, left well), L < 0 mainly in well 2 (the thin, right well), and "
    "L near 0 means balanced or delocalized. P_left + P_barrier + P_right + "
    "P_outside = 1 exactly; P_outside is the tail in the outer AlGaAs barriers "
    "beyond the active region and is reported rather than folded into the wells."
)
HOLE_ENERGY_CONVENTION = (
    "heavy-hole energies are nextnano++'s, on the electron energy scale, where a "
    "more strongly confined hole lies HIGHER. HH1 - HH2 > 0 is therefore the "
    "hole confinement separation, the mirror of E2 - E1."
)


class Demo16EError(RuntimeError):
    """A Demo 16E construction that is wrong rather than merely unusual."""


# ---------------------------------------------------------------------------
# Rendering: three representations of one authoritative profile
# ---------------------------------------------------------------------------


def abrupt_blocks(profile: grading14.CompositionProfile) -> dict[str, Any]:
    """The production rendering with its sub-mesh ramp regions removed.

    Demo 14's renderer emits two ``binary{ GaAs }`` well regions and then lays
    four ``ternary_linear{}`` ramps over their edges. At the abrupt sentinel
    width those ramps are a fortieth of a mesh cell wide -- narrower than
    anything the grid can carry, and not something to hand a solver. Dropping
    them leaves exactly the two GaAs wells carved out of the Al0.55 matrix, which
    IS the abrupt heterostructure.

    The well intervals themselves are still Demo 14's, so an abrupt case and its
    graded twin have the same layer edges by construction rather than by
    agreement between two separate pieces of arithmetic.
    """

    native = grading14.render_structure_blocks(profile)
    regions = [
        region for region in native["regions"]
        if "ternary_linear" not in region["material"]
    ]
    if len(regions) != 2 or not all(
        'binary{ name = "GaAs" }' in region["material"] for region in regions
    ):
        raise Demo16EError(
            "the abrupt rendering expects exactly the two GaAs well regions, got "
            f"{[region['material'] for region in regions]}"
        )
    return {
        "import_block": "",
        "regions": regions,
        "structure_block": "\n".join(f"        {r['material']}" for r in regions) + "\n",
        "datafile": "",
    }


def render_blocks(
    case: cases16e.GeometryCase, profile: grading14.CompositionProfile
) -> dict[str, Any]:
    """Deck blocks for this case's requested representation."""

    if case.is_abrupt:
        return abrupt_blocks(profile)
    if case.render_request == "imported":
        return grading14.render_imported_blocks(
            profile, reason="Demo 16E case_10 asks for the imported rendering so it "
                            "can be compared against its native twin",
        )
    return grading14.render_structure_blocks(profile)


def build_case(cfg: Mapping[str, Any], case: cases16e.GeometryCase):
    """Authoritative Demo 14 geometry and profile, then this case's rendering."""

    parameters = case.parameters()
    geometry = demo14.geometry_for(cfg, parameters)
    profile = demo14.build_grading(cfg, parameters, geometry)
    blocks = render_blocks(case, profile)
    deck = demo14.render_deck(cfg, geometry, profile, blocks)
    return geometry, profile, blocks, deck


def render_method(blocks: Mapping[str, Any]) -> str:
    return (
        "ternary_import" if "ternary_import" in blocks["structure_block"]
        else "ternary_linear"
    )


def representation_of(
    blocks: Mapping[str, Any], case: cases16e.GeometryCase
) -> str:
    """What the emitted deck actually is, read back from the deck blocks."""

    if "ternary_import" in blocks["structure_block"]:
        return "imported_profile"
    if "ternary_linear" in blocks["structure_block"]:
        return "native_linear"
    if case.is_abrupt:
        return "abrupt"
    raise Demo16EError(
        f"{case.case_id}: no recognised composition block in the rendered structure."
    )


# ---------------------------------------------------------------------------
# Composition validation
# ---------------------------------------------------------------------------


def metrology_widths(case: cases16e.GeometryCase) -> dict[str, float]:
    """Window widths for the interface locator, per interface.

    Growth direction decides which width an interface takes: Al rises with z at a
    GaAs->AlGaAs interface and falls at an AlGaAs->GaAs one. An abrupt interface
    has no width of its own, so it borrows :data:`MIN_METROLOGY_WINDOW_NM`.
    """

    left = max(float(case.left_grading_width_nm), MIN_METROLOGY_WINDOW_NM)
    right = max(float(case.right_grading_width_nm), MIN_METROLOGY_WINDOW_NM)
    return {
        INTERFACE_NAMES[0]: right,
        INTERFACE_NAMES[1]: left,
        INTERFACE_NAMES[2]: right,
        INTERFACE_NAMES[3]: left,
    }


def requested_widths(case: cases16e.GeometryCase) -> dict[str, float]:
    """The physically requested 10-90 widths; 0.0 at an abrupt interface."""

    left = float(case.left_grading_width_nm)
    right = float(case.right_grading_width_nm)
    return {
        INTERFACE_NAMES[0]: right, INTERFACE_NAMES[1]: left,
        INTERFACE_NAMES[2]: right, INTERFACE_NAMES[3]: left,
    }


def overlap_geometry(
    profile: grading14.CompositionProfile, case: cases16e.GeometryCase
) -> dict[str, Any]:
    """Describe the production-defined linear-ramp overlap explicitly."""

    interfaces = profile.request["interfaces_nm"]
    z2 = float(interfaces[INTERFACE_NAMES[1]])
    z3 = float(interfaces[INTERFACE_NAMES[2]])
    half_left = 0.5 * float(profile.request["natural_scale_rise_nm"])
    half_right = 0.5 * float(profile.request["natural_scale_fall_nm"])
    overlap_start = z3 - half_right
    overlap_end = z2 + half_left
    overlap_width = max(0.0, overlap_end - overlap_start)
    report = demo16.overlap_report(
        profile.x_nm, profile.al_fraction, interfaces, cases16e.AL_FRACTION
    )
    return {
        **report,
        "overlap": bool(overlap_width > 1e-12),
        "overlap_start_nm": overlap_start if overlap_width else None,
        "overlap_end_nm": overlap_end if overlap_width else None,
        "overlap_width_nm": overlap_width,
        "reaches_90_percent_of_nominal": bool(
            report["expected_peak_al_fraction"] >= 0.90 * cases16e.AL_FRACTION
        ),
        "true_flat_central_plateau_exists": bool(report["nominal_plateau_exists"]),
        "case_declares_overlap": bool(case.overlap),
    }


def _interface_records(
    x_nm: np.ndarray,
    al_fraction: np.ndarray,
    profile: grading14.CompositionProfile,
    case: cases16e.GeometryCase,
) -> list[dict[str, Any]]:
    return [
        metric.as_record()
        for metric in demo16.measure_interfaces(
            x_nm, al_fraction, profile.request["interfaces_nm"],
            metrology_widths(case), cases16e.AL_FRACTION,
        )
    ]


def _geometry_metrics(
    records: list[dict[str, Any]], case: cases16e.GeometryCase
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
        "requested_total_gaas_well_nm": cases16e.TOTAL_WELL_NM,
        "realized_total_gaas_well_nm": realized_total,
        "requested_interface_positions_nm": {
            name: float(value) for name, value in
            zip(INTERFACE_NAMES, [by_name[n]["requested_centre_nm"] for n in INTERFACE_NAMES])
        },
        "realized_interface_positions_nm": {
            name: centre for name, centre in zip(INTERFACE_NAMES, centres)
        },
    }


def _off_interface_mask(
    x: np.ndarray, interfaces: Mapping[str, float], exclusion_nm: float
) -> np.ndarray:
    keep = np.ones(x.shape, dtype=bool)
    for centre in interfaces.values():
        keep &= np.abs(x - float(centre)) > float(exclusion_nm)
    return keep


def compare_compositions(
    profile: grading14.CompositionProfile,
    case: cases16e.GeometryCase,
    x_real: np.ndarray,
    al_real: np.ndarray,
) -> dict[str, Any]:
    """Compare the authoritative profile with nextnano++'s realized composition."""

    x_real = np.asarray(x_real, dtype=float)
    al_real = np.asarray(al_real, dtype=float)
    intended = demo16b.intended_on(profile, x_real)
    residual = al_real - intended
    interfaces = profile.request["interfaces_nm"]
    intended_interfaces = _interface_records(
        profile.x_nm, profile.al_fraction, profile, case
    )
    realized_interfaces = _interface_records(x_real, al_real, profile, case)
    geometry = _geometry_metrics(realized_interfaces, case)
    invariants = demo16.structural_invariants(
        x_real, al_real, interfaces, cases16e.AL_FRACTION
    )
    intended_overlap = overlap_geometry(profile, case)
    realized_overlap = demo16.overlap_report(
        x_real, al_real, interfaces, cases16e.AL_FRACTION
    )
    realized_overlap.update({
        "overlap": realized_overlap["grades_overlap"],
        "reaches_90_percent_of_nominal": bool(
            realized_overlap["realized_peak_al_fraction"]
            >= 0.90 * cases16e.AL_FRACTION
        ),
        "true_flat_central_plateau_exists": bool(
            realized_overlap["nominal_plateau_exists"]
        ),
    })
    forbidden_hits = [
        {"interface": row["interface"],
         "realized_width_nm": row.get("realized_width_10_90_nm"),
         "well_width_nm": forbidden}
        for row in realized_interfaces
        if row.get("realized_width_10_90_nm") is not None
        for forbidden in FORBIDDEN_GRADING_WIDTHS_NM
        if abs(row["realized_width_10_90_nm"] - forbidden) <= FORBIDDEN_WIDTH_MARGIN_NM
    ]
    max_abs = float(np.max(np.abs(residual)))
    rms = float(np.sqrt(np.mean(residual**2)))

    # An abrupt case is gated away from its own steps; see the constant's note.
    keep = _off_interface_mask(x_real, interfaces, ABRUPT_INTERFACE_EXCLUSION_NM)
    off_interface_residual = residual[keep]
    max_abs_off_interface = (
        float(np.max(np.abs(off_interface_residual))) if off_interface_residual.size else 0.0
    )
    rms_off_interface = (
        float(np.sqrt(np.mean(off_interface_residual**2)))
        if off_interface_residual.size else 0.0
    )
    gated_max = max_abs_off_interface if case.is_abrupt else max_abs
    gated_rms = rms_off_interface if case.is_abrupt else rms

    # The two central interfaces of an overlapping barrier have no 50% crossing
    # of their own: the composition never reaches nominal between them, so the
    # local levels are referenced to a peak that belongs to both ramps together.
    # Their positions are measured and reported, but only the outer pair -- which
    # is unaffected by the overlap -- is gated.
    gated_interfaces = (
        [INTERFACE_NAMES[0], INTERFACE_NAMES[3]] if case.overlap
        else list(INTERFACE_NAMES)
    )
    position_errors = [
        row["centre_error_nm"] for row in realized_interfaces
        if row["interface"] in gated_interfaces
        and row.get("centre_error_nm") is not None
    ]
    checks = {
        "max_absolute_error_within_tolerance": gated_max <= MAX_ABS_COMPOSITION_ERROR,
        "rms_error_within_tolerance": gated_rms <= MAX_RMS_COMPOSITION_ERROR,
        "every_interface_was_located": all(
            row.get("realized_centre_nm") is not None for row in realized_interfaces
        ) and len(realized_interfaces) == len(INTERFACE_NAMES),
        "interface_positions_within_tolerance": bool(
            len(position_errors) == len(gated_interfaces)
            and max(position_errors) <= MAX_INTERFACE_POSITION_ERROR_NM
        ),
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
        "case_id": case.case_id,
        "representation": case.expected_representation,
        "comparison_points": int(x_real.size),
        "max_absolute_al_fraction_difference": max_abs,
        "rms_al_fraction_difference": rms,
        "max_absolute_al_fraction_difference_off_interface": max_abs_off_interface,
        "rms_al_fraction_difference_off_interface": rms_off_interface,
        "gated_max_absolute_al_fraction_difference": gated_max,
        "gated_rms_al_fraction_difference": gated_rms,
        "points_excluded_near_interfaces": int(x_real.size - int(np.count_nonzero(keep))),
        "interface_exclusion_applied": bool(case.is_abrupt),
        "interface_exclusion_half_width_nm": ABRUPT_INTERFACE_EXCLUSION_NM,
        "expected_peak_al_fraction": intended_overlap["expected_peak_al_fraction"],
        "realized_peak_al_fraction": realized_overlap["realized_peak_al_fraction"],
        "geometry": geometry,
        "requested_asymmetry_s": case.asymmetry_s,
        "requested_grading_widths_nm": requested_widths(case),
        "metrology_window_widths_nm": metrology_widths(case),
        "metrology_window_is_the_requested_width": not case.is_abrupt,
        "gated_interface_positions": gated_interfaces,
        "central_interface_positions_gated": not case.overlap,
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


# ---------------------------------------------------------------------------
# Per-case orchestration
# ---------------------------------------------------------------------------


@dataclass
class CaseOutcome:
    case_id: str
    name: str
    status: str = "pending"
    representation: str = ""
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
            "demo16e_version": DEMO_VERSION, "representation": self.representation,
            "geometry": self.geometry, "grading": self.grading,
            "render_method": self.render_method,
            "intended_structural_invariants": self.intended_invariants,
            "overlap": self.overlap, "parser": self.parser,
            "structure": self.structure, "physics": self.physics,
            "failure_reason": self.failure_reason,
        }


def write_intended_profile(
    case_dir: Path, profile: grading14.CompositionProfile
) -> Path:
    return runlog14.write_text_atomic(
        Path(case_dir) / "intended_profile.csv",
        "position_nm,expected_al_fraction\n" + "".join(
            f"{x:.6f},{al:.10f}\n" for x, al in zip(profile.x_nm, profile.al_fraction)
        ),
    )


def run_structure(
    cfg: Mapping[str, Any], case: cases16e.GeometryCase, case_dir: Path,
    profile: grading14.CompositionProfile, blocks: Mapping[str, Any], deck: str,
    *, exe: Path, database: Path | None, license_path: Path | None,
) -> dict[str, Any]:
    """``--structure``: build the composition without solving, then compare it."""

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
    cfg: Mapping[str, Any], case: cases16e.GeometryCase, case_dir: Path,
    *, exe: Path | None, database: Path | None, license_path: Path | None = None,
    do_parse: bool = True, do_structure: bool = False,
) -> CaseOutcome:
    """Render, parse and validate in order, stopping after the first failure."""

    case_dir = Path(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    outcome = CaseOutcome(case.case_id, case.name)
    runlog14.write_json_atomic(
        case_dir / "requested_parameters.json",
        {**case.as_record(), "demo16e_version": DEMO_VERSION},
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
    outcome.representation = representation_of(blocks, case)
    outcome.overlap = overlap_geometry(profile, case)
    outcome.intended_invariants = demo16.structural_invariants(
        profile.x_nm, profile.al_fraction,
        profile.request["interfaces_nm"], cases16e.AL_FRACTION,
    )
    write_intended_profile(case_dir, profile)
    if not outcome.intended_invariants["all_passed"]:
        outcome.status = "intended_structure_failed"
        outcome.failure_reason = "authoritative intended profile failed structural checks"
    elif outcome.overlap["overlap"] != case.overlap:
        outcome.status = "overlap_classification_failed"
        outcome.failure_reason = "authoritative overlap classification disagrees with case"
    elif outcome.representation != case.expected_representation:
        outcome.status = "representation_failed"
        outcome.failure_reason = (
            f"expected {case.expected_representation}, got {outcome.representation}"
        )
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
            outcome.status = (
                "structure_passed" if outcome.structure["passed"] else "structure_failed"
            )
            outcome.failure_reason = outcome.structure.get("failure_reason")
    runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
    return outcome


# ---------------------------------------------------------------------------
# Licensed full physics
# ---------------------------------------------------------------------------


def physics_raw_output_dir(case_dir: Path, case: cases16e.GeometryCase) -> Path:
    """``<run>/p01`` .. ``<run>/p10``, beside the case tree rather than inside it.

    Demo 16C and 16D both showed that a deeply nested raw output root is enough
    to break nextnano++ on Windows, so the raw tree hangs off the short run root
    and the budget is checked before the solver is ever told about it.
    """

    case_dir = Path(case_dir)
    run_root = case_dir.parent.parent if case_dir.parent.name == "cases" else case_dir.parent
    raw = run_root / case.physics_label
    warning = sweeps.check_path_budget(raw)
    if warning:
        raise RuntimeError(warning)
    return raw


def full_physics_command(
    cfg: Mapping[str, Any], case: cases16e.GeometryCase, case_dir: Path, *, machine: Any
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
    cfg: Mapping[str, Any], case: cases16e.GeometryCase, case_dir: Path, *, machine: Any
) -> dict[str, Any]:
    """Demo 16B's gated full solve, driven by Demo 16E's own renderer.

    ``build=build_case`` matters: Demo 16B renders every case natively, which is
    right for its own seven cases and wrong for the abrupt and imported ones
    here. Passing the builder keeps one solver path, one output gate and one
    analysis while letting the deck be this case's deck.
    """

    raw_output = physics_raw_output_dir(case_dir, case)
    record = demo16b.solve_case(
        cfg, case, case_dir, machine=machine, raw_output_dir=raw_output,
        build=build_case,
    )
    if not record.get("passed"):
        record.setdefault("diagnostics", {})["raw_output_dir"] = str(raw_output)
        runlog14.write_json_atomic(
            Path(case_dir) / "physics" / "physics_result.json", record
        )
    return record


# ---------------------------------------------------------------------------
# Wavefunction localization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Wavefunctions:
    """The arrays behind the localization numbers, kept for plots and CSV."""

    position_nm: np.ndarray
    electron_energies_eV: np.ndarray
    electron_densities: np.ndarray
    hole_energies_eV: np.ndarray
    hole_densities: np.ndarray
    band_position_nm: np.ndarray
    band_edges: Mapping[str, np.ndarray]
    regions_nm: Mapping[str, tuple[float, float]]


def _state_localization(state, label: str, band: str) -> dict[str, Any]:
    probabilities = {
        short: float(state.region_probabilities.get(region, 0.0))
        for short, region in REGION_LABELS
    }
    inside = sum(probabilities.values())
    return {
        "state": label,
        "band": band,
        "index": int(state.index),
        "energy_eV": float(state.energy_eV),
        "left_probability": probabilities["left"],
        "barrier_probability": probabilities["barrier"],
        "right_probability": probabilities["right"],
        "outside_probability": float(1.0 - inside),
        "inside_probability": float(inside),
        "localization": probabilities["left"] - probabilities["right"],
        "centroid_nm": float(state.centroid_nm),
        "boundary_probability": float(state.boundary_probability),
        "normalised": bool(state.normalised),
    }


def localization(
    cfg: Mapping[str, Any], raw: Path, profile: grading14.CompositionProfile
) -> tuple[dict[str, Any], Wavefunctions]:
    """Left/barrier/right probability for E1, E2, HH1 and HH2.

    Both bands go through ``analysis.analyse_states`` -- the same production
    routine Demo 16B already uses for electrons -- on the same three layer
    intervals, so an electron probability and a hole probability mean the same
    thing. Probability densities are read from nextnano++'s own
    ``probabilities_*`` output rather than squared from envelopes, because that
    is the quantity the solver normalises.
    """

    import analysis
    import outputs
    import quantum1d

    parser_profile = outputs.load_profile(str(cfg["nextnano"]["parser_profile"]))
    region_name = str(cfg["nextnano"]["quantum_region_name"])
    run = quantum1d.parse_one_band_run(
        raw, profile=parser_profile, region_name=region_name,
        bandedge_columns=cfg["nextnano"]["bandedge_columns"],
    )
    resolved = outputs.resolve_outputs(
        parser_profile, Path(raw),
        ["energy_spectrum_hh", "probabilities_hh"],
        substitutions={"region": region_name},
    )
    outputs.require_or_diagnose(
        resolved, Path(raw), ["energy_spectrum_hh", "probabilities_hh"],
        why="Demo 16E measures heavy-hole localization from the solver's own "
            "probability density",
    )
    _, hole_energies = outputs.read_state_table(resolved.one("energy_spectrum_hh"))
    hole_z, hole_densities = outputs.read_profile_table(
        resolved.one("probabilities_hh")
    )
    grids_match = bool(
        hole_z.shape == run.state_position_nm.shape
        and np.allclose(hole_z, run.state_position_nm)
    )
    if not grids_match:
        raise Demo16EError(
            "electron and heavy-hole probability outputs are on different grids; "
            "refusing to report them as one localization table."
        )

    regions = demo16b._region_map(profile)
    electron_states = analysis.analyse_states(
        run.state_position_nm, run.energies_eV, run.densities,
        regions=regions, envelopes=run.envelopes,
    )
    hole_states = analysis.analyse_states(
        hole_z, hole_energies, hole_densities, regions=regions,
    )
    rows: list[dict[str, Any]] = []
    for label, states, band in (
        ("E", electron_states, "electron"), ("HH", hole_states, "heavy_hole")
    ):
        for index in range(min(2, len(states))):
            rows.append(_state_localization(states[index], f"{label}{index+1}", band))

    by_state = {row["state"]: row for row in rows}
    record = {
        "states": rows,
        "by_state": by_state,
        "regions_nm": {short: list(regions[region]) for short, region in REGION_LABELS},
        "region_source": "Demo 14 interface positions (well 1 | barrier | well 2)",
        "localization_convention": LOCALIZATION_CONVENTION,
        "hole_energy_convention": HOLE_ENERGY_CONVENTION,
        "probability_source": "nextnano++ probabilities_* output, renormalised on "
                              "the quantum-region grid",
        "electron_state_count": int(run.energies_eV.size),
        "heavy_hole_state_count": int(np.asarray(hole_energies).size),
        "checks": {
            "all_four_states_present": len(rows) == len(STATE_LABELS),
            "probabilities_sum_to_one": all(
                abs(row["inside_probability"] + row["outside_probability"] - 1.0) <= 1e-9
                for row in rows
            ),
            "probabilities_are_normalised": all(row["normalised"] for row in rows),
            "electron_and_hole_grids_match": grids_match,
        },
    }
    record["checks"]["passed"] = all(
        value for key, value in record["checks"].items() if key != "passed"
    )
    wavefunctions = Wavefunctions(
        position_nm=np.asarray(run.state_position_nm, dtype=float),
        electron_energies_eV=np.asarray(run.energies_eV, dtype=float),
        electron_densities=np.asarray(run.densities, dtype=float),
        hole_energies_eV=np.asarray(hole_energies, dtype=float),
        hole_densities=np.asarray(hole_densities, dtype=float),
        band_position_nm=np.asarray(run.position_nm, dtype=float),
        band_edges={k: np.asarray(v, dtype=float) for k, v in run.band_edges.items()},
        regions_nm={short: regions[region] for short, region in REGION_LABELS},
    )
    return record, wavefunctions


def write_wavefunction_csv(path: Path, waves: Wavefunctions) -> Path:
    """Persist the four probability densities so plots survive a cleaned raw tree."""

    columns = ["position_nm"]
    stack = [waves.position_nm]
    for label, energies, densities in (
        ("E", waves.electron_energies_eV, waves.electron_densities),
        ("HH", waves.hole_energies_eV, waves.hole_densities),
    ):
        for index in range(min(2, densities.shape[1])):
            columns.append(f"{label}{index+1}_probability_density")
            stack.append(densities[:, index])
    data = np.column_stack(stack)
    body = "".join(
        ",".join(f"{value:.10g}" for value in row) + "\n" for row in data
    )
    return runlog14.write_text_atomic(Path(path), ",".join(columns) + "\n" + body)


# ---------------------------------------------------------------------------
# Optical response
# ---------------------------------------------------------------------------


def analyse_optics(
    cfg: Mapping[str, Any], case: cases16e.GeometryCase, case_dir: Path,
    raw_output: Path,
) -> dict[str, Any]:
    """Evaluate the established Demo 11/14 absolute chi2 spectrum on real states.

    The 1550 nm value is interpolated from the production spectrum and then
    checked against the production evaluation of the same quantity. A mismatch
    raises rather than being reported, because the two disagreeing would mean the
    curve and the number in the table came from different calculations.
    """

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
        "scan_window_nm": [float(wavelength[0]), float(wavelength[-1])],
        "spectrum_path": str(spectrum_path),
        "analysis_settings_path": str(parsed / "chi2_settings.json"),
        "selected_states_path": str(parsed / "state_count_audit.json"),
        "production_metrics": metrics,
    }
    runlog14.write_json_atomic(optical_root / "optical_result.json", result)
    return result


# ---------------------------------------------------------------------------
# Cross-case comparisons
# ---------------------------------------------------------------------------


EV_TO_MEV = 1000.0


def _delta_meV(value: Any, reference: Any) -> float | None:
    if value is None or reference is None:
        return None
    return (float(value) - float(reference)) * EV_TO_MEV


def energy_shifts(row: Mapping[str, Any], reference: Mapping[str, Any]) -> dict[str, Any]:
    """Shifts of one case's four state energies against the reference case."""

    return {
        f"delta_{key}_meV_vs_reference": _delta_meV(row.get(f"{key}_eV"),
                                                    reference.get(f"{key}_eV"))
        for key in STATE_LABELS
    }


def derived_energies(row: Mapping[str, Any]) -> dict[str, Any]:
    """Separations the study quotes, in meV, with the hole convention documented."""

    return {
        "E2_minus_E1_meV": _delta_meV(row.get("E2_eV"), row.get("E1_eV")),
        "HH1_minus_HH2_meV": _delta_meV(row.get("HH1_eV"), row.get("HH2_eV")),
        "transition_e1_hh1_eV": (
            None if row.get("E1_eV") is None or row.get("HH1_eV") is None
            else float(row["E1_eV"]) - float(row["HH1_eV"])
        ),
        "transition_e2_hh2_eV": (
            None if row.get("E2_eV") is None or row.get("HH2_eV") is None
            else float(row["E2_eV"]) - float(row["HH2_eV"])
        ),
        "hole_energy_convention": HOLE_ENERGY_CONVENTION,
    }


#: Equivalence budgets. The composition, energy and transition numbers are
#: Demo 17's measured tolerances for exactly this comparison
#: (``measure17.Tolerances``); the localization and optical ones are stated here
#: because Demo 17 does not evaluate chi2. A localization probability is a
#: normalised integral over a fixed interval, so it inherits the energy-level
#: agreement rather than adding to it; 5e-3 matches Demo 17's mirror-probability
#: budget. chi2 is quadratic in the dipole matrix elements and therefore roughly
#: twice as sensitive as an energy, so 2% is the same statement about the
#: underlying states -- and is the tolerance Demo 14's own licensed import
#: equivalence gate already uses.
EQUIVALENCE_TOLERANCES = {
    "composition_max": 5.0e-3,
    "composition_rms": 1.0e-3,
    "energy_eV": 1.0e-3,
    "transition_eV": 1.0e-3,
    "localization_probability": 5.0e-3,
    "chi2_relative": 0.02,
    "peak_wavelength_nm": 1.0,
}


def _relative_difference(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    scale = max(abs(float(a)), abs(float(b)))
    if scale == 0.0:
        return 0.0
    return abs(float(a) - float(b)) / scale


def composition_difference(
    native_profile: grading14.CompositionProfile,
    imported_profile: grading14.CompositionProfile,
) -> dict[str, Any]:
    """How far apart two authoritative profiles are on a common grid."""

    x = np.asarray(native_profile.x_nm, dtype=float)
    a = np.asarray(native_profile.al_fraction, dtype=float)
    b = np.interp(x, np.asarray(imported_profile.x_nm, dtype=float),
                  np.asarray(imported_profile.al_fraction, dtype=float))
    residual = a - b
    return {
        "points": int(x.size),
        "max_abs_xAl_difference": float(np.max(np.abs(residual))),
        "rms_xAl_difference": float(np.sqrt(np.mean(residual**2))),
    }


def equivalence_report(
    native: Mapping[str, Any], imported: Mapping[str, Any],
    composition: Mapping[str, Any],
) -> dict[str, Any]:
    """Is the imported rendering the same structure as its native twin?

    This is an implementation-equivalence test, not a physics comparison: the two
    decks encode one ``x_Al(z)``, so any difference beyond the budgets below is a
    rendering or parsing defect and is reported as such.
    """

    energy = {
        f"delta_{label}_meV": _delta_meV(imported.get(f"{label}_eV"),
                                         native.get(f"{label}_eV"))
        for label in STATE_LABELS
    }
    localization_delta = {
        f"delta_{label}_localization": (
            None
            if native.get(f"{label}_localization") is None
            or imported.get(f"{label}_localization") is None
            else float(imported[f"{label}_localization"])
            - float(native[f"{label}_localization"])
        )
        for label in STATE_LABELS
    }
    probability_delta = {
        f"delta_{label}_{side}_probability": (
            None
            if native.get(f"{label}_{side}_probability") is None
            or imported.get(f"{label}_{side}_probability") is None
            else float(imported[f"{label}_{side}_probability"])
            - float(native[f"{label}_{side}_probability"])
        )
        for label in STATE_LABELS for side in ("left", "barrier", "right")
    }
    chi2_relative = _relative_difference(
        native.get("chi2_at_1550"), imported.get("chi2_at_1550")
    )
    peak_delta = (
        None
        if native.get("peak_wavelength_nm") is None
        or imported.get("peak_wavelength_nm") is None
        else float(imported["peak_wavelength_nm"]) - float(native["peak_wavelength_nm"])
    )
    finite_energy = [abs(v) for v in energy.values() if v is not None]
    finite_localization = [abs(v) for v in localization_delta.values() if v is not None]
    finite_probability = [abs(v) for v in probability_delta.values() if v is not None]
    checks = {
        "composition_agrees": composition["max_abs_xAl_difference"]
        <= EQUIVALENCE_TOLERANCES["composition_max"],
        "composition_rms_agrees": composition["rms_xAl_difference"]
        <= EQUIVALENCE_TOLERANCES["composition_rms"],
        "state_energies_agree": bool(finite_energy) and max(finite_energy)
        <= EQUIVALENCE_TOLERANCES["energy_eV"] * EV_TO_MEV,
        "localization_agrees": bool(finite_localization) and max(finite_localization)
        <= EQUIVALENCE_TOLERANCES["localization_probability"],
        "region_probabilities_agree": bool(finite_probability) and max(finite_probability)
        <= EQUIVALENCE_TOLERANCES["localization_probability"],
        "chi2_at_1550_agrees": chi2_relative is not None
        and chi2_relative <= EQUIVALENCE_TOLERANCES["chi2_relative"],
        "peak_wavelength_agrees": peak_delta is not None
        and abs(peak_delta) <= EQUIVALENCE_TOLERANCES["peak_wavelength_nm"],
    }
    checks["passed"] = all(checks.values())
    return {
        "native_case": native.get("case"),
        "imported_case": imported.get("case"),
        "purpose": (
            "implementation equivalence of the native ternary_linear and imported "
            "table renderings of one x_Al(z); not a physics comparison"
        ),
        "composition": dict(composition),
        "energy_differences_meV": energy,
        "max_abs_energy_difference_meV": max(finite_energy) if finite_energy else None,
        "localization_differences": localization_delta,
        "region_probability_differences": probability_delta,
        "chi2_at_1550_native": native.get("chi2_at_1550"),
        "chi2_at_1550_imported": imported.get("chi2_at_1550"),
        "chi2_at_1550_relative_difference": chi2_relative,
        "peak_wavelength_difference_nm": peak_delta,
        "tolerances": dict(EQUIVALENCE_TOLERANCES),
        "checks": checks,
    }


def abrupt_vs_graded_report(
    graded: Mapping[str, Any], abrupt: Mapping[str, Any]
) -> dict[str, Any]:
    """The one deliberate physics comparison between two identical geometries.

    Unlike the equivalence pair, these two are *expected* to differ: grading the
    interfaces of a fixed layer stack moves the states. Nothing here is a
    tolerance; every number is a measurement.
    """

    return {
        "graded_case": graded.get("case"),
        "abrupt_case": abrupt.get("case"),
        "shared_geometry_nm": {
            "well_1_nm": graded.get("well_1_nm"),
            "central_barrier_nm": graded.get("central_barrier_nm"),
            "well_2_nm": graded.get("well_2_nm"),
        },
        "grading_widths_nm": {
            "graded": [graded.get("left_grading_nm"), graded.get("right_grading_nm")],
            "abrupt": [abrupt.get("left_grading_nm"), abrupt.get("right_grading_nm")],
        },
        "realized_peak_xAl": {
            "graded": graded.get("realized_peak_xAl"),
            "abrupt": abrupt.get("realized_peak_xAl"),
        },
        "energy_shifts_graded_minus_abrupt_meV": {
            f"delta_{label}_meV": _delta_meV(graded.get(f"{label}_eV"),
                                             abrupt.get(f"{label}_eV"))
            for label in STATE_LABELS
        },
        "localization_graded_minus_abrupt": {
            f"delta_{label}_localization": (
                None
                if graded.get(f"{label}_localization") is None
                or abrupt.get(f"{label}_localization") is None
                else float(graded[f"{label}_localization"])
                - float(abrupt[f"{label}_localization"])
            )
            for label in STATE_LABELS
        },
        "chi2_at_1550": {
            "graded": graded.get("chi2_at_1550"),
            "abrupt": abrupt.get("chi2_at_1550"),
            "graded_minus_abrupt": (
                None
                if graded.get("chi2_at_1550") is None or abrupt.get("chi2_at_1550") is None
                else float(graded["chi2_at_1550"]) - float(abrupt["chi2_at_1550"])
            ),
            "graded_over_abrupt": (
                None
                if not abrupt.get("chi2_at_1550")
                else float(graded["chi2_at_1550"]) / float(abrupt["chi2_at_1550"])
            ),
        },
        "peak_wavelength_nm": {
            "graded": graded.get("peak_wavelength_nm"),
            "abrupt": abrupt.get("peak_wavelength_nm"),
            "graded_minus_abrupt_nm": (
                None
                if graded.get("peak_wavelength_nm") is None
                or abrupt.get("peak_wavelength_nm") is None
                else float(graded["peak_wavelength_nm"])
                - float(abrupt["peak_wavelength_nm"])
            ),
        },
        "detuning_from_1550_nm": {
            "graded": graded.get("detuning_from_1550_nm"),
            "abrupt": abrupt.get("detuning_from_1550_nm"),
        },
        "interpretation_note": (
            "descriptive only: a larger chi2 or a smaller detuning is reported, "
            "never selected"
        ),
    }


def master_row(
    case: cases16e.GeometryCase,
    record: Mapping[str, Any],
    comparison: Mapping[str, Any] | None,
    representation: str,
) -> dict[str, Any]:
    """One row of the master summary, in the study's own field names."""

    analysis_record = record.get("analysis") or {}
    optical = record.get("optical") or {}
    local = (record.get("localization") or {}).get("by_state") or {}
    comparison = comparison or {}
    well_1, well_2 = case.well_widths_nm()
    row: dict[str, Any] = {
        "case": case.case_id,
        "description": case.description,
        "name": case.name,
        "representation": representation,
        "well_1_nm": well_1,
        "central_barrier_nm": float(case.central_barrier_nm),
        "well_2_nm": well_2,
        "asymmetry_s": float(case.asymmetry_s),
        "left_grading_nm": float(case.left_grading_width_nm),
        "right_grading_nm": float(case.right_grading_width_nm),
        "overlap": bool(case.overlap),
        "realized_peak_xAl": comparison.get("realized_peak_al_fraction"),
        "max_composition_error": comparison.get("max_absolute_al_fraction_difference"),
        "rms_composition_error": comparison.get("rms_al_fraction_difference"),
        "E1_eV": analysis_record.get("E_e1_eV"),
        "E2_eV": analysis_record.get("E_e2_eV"),
        "HH1_eV": analysis_record.get("E_hh1_eV"),
        "HH2_eV": analysis_record.get("E_hh2_eV"),
    }
    for label in STATE_LABELS:
        state = local.get(label) or {}
        row.update({
            f"{label}_left_probability": state.get("left_probability"),
            f"{label}_barrier_probability": state.get("barrier_probability"),
            f"{label}_right_probability": state.get("right_probability"),
            f"{label}_outside_probability": state.get("outside_probability"),
            f"{label}_localization": state.get("localization"),
        })
    row.update(derived_energies(row))
    row.update({
        "chi2_at_1550": optical.get("chi2_at_1550"),
        "chi2_units": optical.get("chi2_units"),
        "peak_chi2": optical.get("spectral_peak_chi2"),
        "peak_wavelength_nm": optical.get("spectral_peak_wavelength_nm"),
        "detuning_from_1550_nm": optical.get("detuning_from_1550_nm"),
        "spectrum_path": optical.get("spectrum_path"),
        "wavefunction_csv_path": record.get("wavefunction_csv_path"),
        "input_deck_path": record.get("deck_path"),
        "raw_output_dir": record.get("raw_output_dir"),
        "optical_settings_path": optical.get("analysis_settings_path"),
        "selected_states_path": optical.get("selected_states_path"),
    })
    return row


def add_reference_shifts(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill every row's shifts against the reference case, in place-safe order."""

    rows = [dict(row) for row in rows]
    reference = next(
        (row for row in rows if row["case"] == cases16e.REFERENCE_CASE_ID), None
    )
    for row in rows:
        row.update(
            energy_shifts(row, reference) if reference is not None
            else {f"delta_{label}_meV_vs_reference": None for label in STATE_LABELS}
        )
        row["reference_case"] = (
            cases16e.REFERENCE_CASE_ID if reference is not None else None
        )
    return rows
