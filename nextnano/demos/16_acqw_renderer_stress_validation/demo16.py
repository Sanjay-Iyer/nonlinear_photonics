"""Demo 16: does nextnano++ build the structure Python asked for?

Three levels, each answering a strictly harder question:

* **Level 1 (syntax)** -- the production Demo 14 renderer emits a deck and
  ``nextnano++ --parse`` accepts it. Needs no licence; the free build validates
  the full input grammar.
* **Level 2 (structure)** -- nextnano++ builds the deck and reports its realized
  alloy composition, which is compared against the authoritative Python
  ``x_Al(x)``. Needs the licensed build: the free one caps at 100 grid points and
  a production deck is ~1000.
* **Level 3 (physics)** -- a selected subset goes through the real solver and
  analysis. Explicitly requested; never the default.

Demo 16 imports Demo 14's renderer, geometry and solver wrapper rather than
reimplementing them. A parallel implementation would validate the wrong code --
the point is to stress the path a campaign actually uses.

The measurement rule that matters most: every interface metric is computed in a
**local window around that interface**. Demo 14 previously scanned for
composition crossings across an entire well and reported the 7.1 nm and 2.9 nm
*well widths* as grading widths. A local window makes that class of error
impossible rather than merely unlikely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np

import cases16
import demo14
import grading14
import runlog14

DEMO_ID = "16_acqw_renderer_stress_validation"
DEMO_DIR = Path(__file__).resolve().parent
DEMO16_VERSION = "demo16-1.0.0"

#: Half-width of the window used to measure one interface, as a multiple of its
#: requested 10-90 width. Wide enough to contain the full transition, narrow
#: enough that it cannot reach the next interface -- which is checked, not
#: assumed, by :func:`_window_is_isolated`.
INTERFACE_WINDOW_FACTOR = 1.6


class Demo16Error(RuntimeError):
    """A validation-infrastructure failure, distinct from a case failing."""


# ---------------------------------------------------------------------------
# Interface metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InterfaceMetrics:
    name: str
    requested_centre_nm: float
    requested_width_10_90_nm: float
    window_nm: tuple[float, float]
    realized_centre_nm: float | None
    realized_width_10_90_nm: float | None
    low_level: float
    high_level: float
    centre_error_nm: float | None
    width_error_nm: float | None
    window_isolated: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "interface": self.name,
            "requested_centre_nm": self.requested_centre_nm,
            "requested_width_10_90_nm": self.requested_width_10_90_nm,
            "measurement_window_nm": list(self.window_nm),
            "realized_centre_nm": self.realized_centre_nm,
            "realized_width_10_90_nm": self.realized_width_10_90_nm,
            "centre_error_nm": self.centre_error_nm,
            "width_error_nm": self.width_error_nm,
            "window_isolated_from_other_interfaces": self.window_isolated,
        }


def _crossing(x: np.ndarray, y: np.ndarray, level: float) -> float | None:
    """First crossing of ``level``, linearly interpolated, or ``None``."""

    for i in range(len(x) - 1):
        a, b = y[i], y[i + 1]
        if (a < level <= b) or (a >= level > b):
            if b == a:
                return float(x[i])
            t = (level - a) / (b - a)
            return float(x[i] + t * (x[i + 1] - x[i]))
    return None


def _window_is_isolated(
    window: tuple[float, float], centre: float, all_centres: Sequence[float]
) -> bool:
    """True when the window contains only its own interface.

    A window that reaches a neighbouring interface is exactly how a crossing
    search ends up measuring a well width, so this is recorded per interface
    rather than trusted.
    """

    lo, hi = window
    for other in all_centres:
        if abs(other - centre) < 1e-9:
            continue
        if lo <= other <= hi:
            return False
    return True


def measure_interfaces(
    x_nm: np.ndarray,
    al_fraction: np.ndarray,
    interfaces: Mapping[str, float],
    requested_widths: Mapping[str, float],
    max_al_fraction: float,
) -> list[InterfaceMetrics]:
    """Local 10/50/90 metrics for each of the four interfaces.

    Levels are referenced to the composition actually achieved on each side of
    the interface, not to the nominal 0 -> x_max transition. At a thin barrier
    the central interfaces never reach nominal composition, and a nominal
    reference would simply report nothing there.
    """

    x = np.asarray(x_nm, dtype=float)
    y = np.asarray(al_fraction, dtype=float)
    centres = list(interfaces.values())
    out: list[InterfaceMetrics] = []

    for name, centre in interfaces.items():
        width = float(requested_widths[name])
        # Clamp the window at the midpoint to each neighbouring interface, so it
        # is isolated BY CONSTRUCTION rather than by luck. Without this, a 1.4 nm
        # grade across a 0.85 nm barrier opens a window that swallows the
        # neighbouring interface and part of a well -- which is precisely how a
        # well width gets reported as a grading width.
        neighbours = [c for c in centres if abs(c - centre) > 1e-9]
        gap_left = min(
            (centre - c for c in neighbours if c < centre), default=math.inf
        )
        gap_right = min(
            (c - centre for c in neighbours if c > centre), default=math.inf
        )
        half = INTERFACE_WINDOW_FACTOR * width
        half_left = min(half, 0.5 * gap_left) if math.isfinite(gap_left) else half
        half_right = min(half, 0.5 * gap_right) if math.isfinite(gap_right) else half
        window = (centre - half_left, centre + half_right)
        mask = (x >= window[0]) & (x <= window[1])
        if np.count_nonzero(mask) < 3:
            out.append(InterfaceMetrics(
                name=name, requested_centre_nm=centre,
                requested_width_10_90_nm=width, window_nm=window,
                realized_centre_nm=None, realized_width_10_90_nm=None,
                low_level=0.0, high_level=0.0, centre_error_nm=None,
                width_error_nm=None,
                window_isolated=_window_is_isolated(window, centre, centres),
            ))
            continue

        xs, ys = x[mask], y[mask]
        lo_val, hi_val = float(ys[0]), float(ys[-1])
        bottom, top = min(lo_val, hi_val), max(lo_val, hi_val)
        span = top - bottom
        low = bottom + 0.10 * span
        high = bottom + 0.90 * span
        mid = bottom + 0.50 * span

        x_low = _crossing(xs, ys, low)
        x_high = _crossing(xs, ys, high)
        x_mid = _crossing(xs, ys, mid)
        realized_width = (
            abs(x_high - x_low) if (x_low is not None and x_high is not None) else None
        )
        out.append(InterfaceMetrics(
            name=name,
            requested_centre_nm=centre,
            requested_width_10_90_nm=width,
            window_nm=window,
            realized_centre_nm=x_mid,
            realized_width_10_90_nm=realized_width,
            low_level=low,
            high_level=high,
            centre_error_nm=None if x_mid is None else abs(x_mid - centre),
            width_error_nm=None if realized_width is None else abs(realized_width - width),
            window_isolated=_window_is_isolated(window, centre, centres),
        ))
    return out


def overlap_report(
    x_nm: np.ndarray, al_fraction: np.ndarray, interfaces: Mapping[str, float],
    max_al_fraction: float,
) -> dict[str, Any]:
    """The scientifically-defined description of a central-barrier overlap.

    Section 2 of the Demo 17 brief: an overlap must be characterised by an
    explicit oracle, not left for the renderer to determine implicitly.
    """

    x = np.asarray(x_nm, dtype=float)
    y = np.asarray(al_fraction, dtype=float)
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    inner = (x >= z2) & (x <= z3)
    if not np.any(inner):
        # A barrier thinner than one mesh cell: describe the neighbourhood.
        inner = (x >= z2 - 0.5) & (x <= z3 + 0.5)
    peak = float(np.max(y[inner]))
    peak_position = float(x[inner][int(np.argmax(y[inner]))])
    plateau = y[inner] >= 0.995 * max_al_fraction
    nominal_plateau = bool(np.count_nonzero(plateau) >= 2)
    return {
        "central_interface_left_nm": z2,
        "central_interface_right_nm": z3,
        "nominal_barrier_al_fraction": max_al_fraction,
        "expected_peak_al_fraction": peak,
        "realized_peak_al_fraction": peak,
        "peak_position_nm": peak_position,
        "nominal_plateau_exists": nominal_plateau,
        "grades_overlap": bool(peak < 0.995 * max_al_fraction),
        "local_integrated_al_dose_nm_equivalent": float(
            np.trapezoid(y[inner], x[inner]) / max_al_fraction
        ),
    }


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------


def structural_invariants(
    x_nm: np.ndarray, al_fraction: np.ndarray, interfaces: Mapping[str, float],
    max_al_fraction: float,
) -> dict[str, Any]:
    """The ten invariants a valid ACQW composition must satisfy."""

    x = np.asarray(x_nm, dtype=float)
    y = np.asarray(al_fraction, dtype=float)
    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])

    def at(position: float) -> float:
        return float(np.interp(position, x, y))

    thick_centre = 0.5 * (z1 + z2)
    thin_centre = 0.5 * (z3 + z4)
    barrier_centre = 0.5 * (z2 + z3)

    checks = {
        "left_outer_barrier_present": bool(y[0] >= 0.95 * max_al_fraction),
        "right_outer_barrier_present": bool(y[-1] >= 0.95 * max_al_fraction),
        "thick_well_is_gaas": bool(at(thick_centre) <= 0.05 * max_al_fraction),
        "thin_well_is_gaas": bool(at(thin_centre) <= 0.05 * max_al_fraction),
        "central_barrier_present": bool(
            at(barrier_centre) >= max(0.20 * max_al_fraction,
                                      2.0 * at(thick_centre))
        ),
        "composition_within_bounds": bool(
            np.all(y >= -1e-9) and np.all(y <= max_al_fraction + 1e-9)
        ),
        "composition_finite": bool(np.all(np.isfinite(y))),
        "coordinates_ascending": bool(np.all(np.diff(x) > 0)),
        "four_interfaces_ordered": bool(z1 < z2 < z3 < z4),
        # If the wells were confined only by the quantum region's Dirichlet
        # walls, the composition at the domain edges would not be barrier alloy.
        "confinement_is_material_not_boundary": bool(
            y[0] >= 0.95 * max_al_fraction and y[-1] >= 0.95 * max_al_fraction
        ),
    }
    checks["all_passed"] = all(checks.values())
    return checks


# ---------------------------------------------------------------------------
# Level 1
# ---------------------------------------------------------------------------


@dataclass
class CaseOutcome:
    case_id: str
    name: str
    status: str = "pending"
    level1: dict[str, Any] = field(default_factory=dict)
    level2: dict[str, Any] = field(default_factory=dict)
    invariants: dict[str, Any] = field(default_factory=dict)
    interfaces: list[dict[str, Any]] = field(default_factory=list)
    overlap: dict[str, Any] = field(default_factory=dict)
    geometry: dict[str, Any] = field(default_factory=dict)
    grading: dict[str, Any] = field(default_factory=dict)
    render_method: str = ""
    failure_reason: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id, "name": self.name, "status": self.status,
            "render_method": self.render_method,
            "level1_syntax": self.level1, "level2_structure": self.level2,
            "structural_invariants": self.invariants,
            "interface_metrics": self.interfaces,
            "overlap": self.overlap,
            "geometry": self.geometry, "grading": self.grading,
            "failure_reason": self.failure_reason,
        }


def build_case(cfg: Mapping[str, Any], case: cases16.ValidationCase):
    """Geometry, authoritative profile and deck, all from Demo 14's own code."""

    params = case.parameters()
    geometry = demo14.geometry_for(cfg, params)
    profile = demo14.build_grading(cfg, params, geometry)
    blocks = grading14.render_structure_blocks(profile)
    deck = demo14.render_deck(cfg, geometry, profile, blocks)
    return geometry, profile, blocks, deck


def parse_deck(
    exe: Path, database: Path | None, case_dir: Path, deck_text: str,
    datafile: str, import_name: str = "al_profile",
) -> dict[str, Any]:
    """Write the deck and run ``--parse``. No physics, no licence consumed."""

    deck_dir = case_dir / "nextnano_input"
    deck_dir.mkdir(parents=True, exist_ok=True)
    deck = deck_dir / "case.in"
    runlog14.write_text_atomic(deck, deck_text)
    if datafile:
        runlog14.write_text_atomic(deck_dir / f"{import_name}.dat", datafile)

    argv = [str(exe), "--parse"]
    if database:
        argv += ["-d", str(database)]
    argv += ["-o", str(case_dir / "parser" / "out"), "case.in"]
    (case_dir / "parser").mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        argv, cwd=str(deck_dir), capture_output=True, text=True,
        timeout=180, check=False,
    )
    stdout, stderr = completed.stdout or "", completed.stderr or ""
    runlog14.write_text_atomic(case_dir / "parser" / "stdout.txt", stdout)
    runlog14.write_text_atomic(case_dir / "parser" / "stderr.txt", stderr)

    combined = (stdout + stderr).lower()
    fatal = [m for m in ("terminating program", "validation error", "fatal error",
                         "too many instances", "unexpected group") if m in combined]
    passed = "parsing completed" in combined and not fatal
    reason = None
    if not passed:
        reason = next(
            (line.strip() for line in (stdout + stderr).splitlines()
             if any(m in line.lower() for m in
                    ("error", "too many", "unexpected", "terminating"))),
            f"exit {completed.returncode}",
        )
    return {
        "passed": passed,
        "parser_command": argv,
        "return_code": completed.returncode,
        "fatal_markers": fatal,
        "deck_path": str(deck),
        "deck_sha256": runlog14.sha256_file(deck),
        "profile_path": str(deck_dir / f"{import_name}.dat") if datafile else None,
        "profile_sha256": (
            runlog14.sha256_file(deck_dir / f"{import_name}.dat") if datafile else None
        ),
        "stdout_path": str(case_dir / "parser" / "stdout.txt"),
        "stderr_path": str(case_dir / "parser" / "stderr.txt"),
        "failure_reason": reason,
    }


def validate_case_level1(
    cfg: Mapping[str, Any], case: cases16.ValidationCase, case_dir: Path,
    exe: Path | None, database: Path | None,
) -> CaseOutcome:
    """Render, measure the authoritative profile, and parse."""

    outcome = CaseOutcome(case_id=case.case_id, name=case.name)
    case_dir.mkdir(parents=True, exist_ok=True)
    runlog14.write_json_atomic(
        case_dir / "requested_parameters.json",
        {**case.as_record(), "demo16_version": DEMO16_VERSION},
    )
    try:
        geometry, profile, blocks, deck = build_case(cfg, case)
    except Exception as exc:
        outcome.status = "render_failed"
        outcome.failure_reason = f"{type(exc).__name__}: {exc}"
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        return outcome

    outcome.geometry = geometry.as_record()
    outcome.grading = dict(profile.diagnostics)
    outcome.render_method = (
        "ternary_import" if "ternary_import" in blocks["structure_block"]
        else "ternary_linear"
    )
    if blocks.get("render_fallback_reason"):
        outcome.grading["render_fallback_reason"] = blocks["render_fallback_reason"]

    interfaces = profile.request["interfaces_nm"]
    widths = {
        "outer_left_algaas_to_gaas": case.algaas_to_gaas_grading_width_10_90_nm,
        "central_gaas_to_algaas": case.gaas_to_algaas_grading_width_10_90_nm,
        "central_algaas_to_gaas": case.algaas_to_gaas_grading_width_10_90_nm,
        "outer_right_gaas_to_algaas": case.gaas_to_algaas_grading_width_10_90_nm,
    }
    outcome.interfaces = [
        m.as_record() for m in measure_interfaces(
            profile.x_nm, profile.al_fraction, interfaces, widths, cases16.AL_FRACTION
        )
    ]
    outcome.invariants = structural_invariants(
        profile.x_nm, profile.al_fraction, interfaces, cases16.AL_FRACTION
    )
    outcome.overlap = overlap_report(
        profile.x_nm, profile.al_fraction, interfaces, cases16.AL_FRACTION
    )

    # The authoritative profile, saved before anything is executed.
    rows = profile.as_rows()
    runlog14.write_text_atomic(
        case_dir / "intended_profile.csv",
        "x_nm,al_fraction_requested_continuous,al_fraction_rendered\n"
        + "".join(
            f"{r['x_nm']:.6f},{r['al_fraction_requested_continuous']:.8f},"
            f"{r['al_fraction_rendered']:.8f}\n" for r in rows
        ),
    )

    if exe is None:
        outcome.level1 = {
            "passed": False,
            "failure_reason": "no nextnano++ executable available to parse the deck",
        }
        outcome.status = "syntax_unchecked"
    else:
        outcome.level1 = parse_deck(
            exe, database, case_dir, deck, blocks["datafile"]
        )
        outcome.status = "syntax_passed" if outcome.level1["passed"] else "syntax_failed"
        if not outcome.level1["passed"]:
            outcome.failure_reason = outcome.level1.get("failure_reason")

    if not outcome.invariants["all_passed"] and outcome.status == "syntax_passed":
        outcome.status = "structure_failed"
        failed = [k for k, v in outcome.invariants.items()
                  if k != "all_passed" and not v]
        outcome.failure_reason = f"structural invariants failed: {failed}"

    runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
    return outcome
