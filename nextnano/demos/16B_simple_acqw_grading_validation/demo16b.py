"""Demo 16B: the simple GaAs/AlGaAs ACQW + linear grading core workflow.

One question, asked in three steps of increasing cost:

* **Level 1 -- parser.** Python renders the deck with Demo 14's *production*
  renderer and the installed ``nextnano++ --parse`` accepts it. No licence, no
  physics.
* **Level 2 -- structure.** ``nextnano++ --structure`` builds the structure and
  writes ``Structure/alloy_composition.dat``; that realized ``x_Al(z)`` is
  compared point by point against the authoritative Python profile. Still no
  physics -- the solver never runs -- but a production deck is ~440 grid points
  and the free build refuses anything over 100, so this needs the licensed build.
* **Level 3 -- physics.** Three selected cases through the real solver, checked
  for band edges, electron states, heavy-hole states, wavefunctions and
  transition energies. Explicitly requested; never a default.

Nothing here reimplements physics. Geometry comes from ``demo14.geometry_for``,
composition from ``demo14.build_grading`` (i.e. ``grading14``), the deck from
``demo14.render_deck``, the parser wrapper and the interface/invariant measures
from ``demo16``, the solver from ``solver14`` and the output parsing from the
shared ``outputs`` / ``quantum1d`` modules. Demo 16B contributes the case list,
the intended-vs-realized comparison, and the refusal to proceed past a failure.

Two rules are load-bearing:

*No overlapping grading regions.* The production renderer writes one
``ternary_linear{}`` region per interface and a later region overrides an earlier
one, so two ramps that touch would silently corrupt the profile. Demo 16B audits
the emitted region spans for disjointness and rejects the case if they are not.
Demo 16 covers the overlapped regime through an imported table; excluding it here
is what keeps 16B simple.

*Nothing is fabricated after a failure.* A parser failure stops the case before
Level 2. A structure failure stops it before Level 3. A nonzero solver exit
raises out of ``solver14`` and no analysis runs on the wreckage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import numpy as np

import cases16b
import chi2 as chi2mod
import demo14
import demo16
import grading14
import runlog14
import solver14

DEMO_ID = "16B_simple_acqw_grading_validation"
DEMO_DIR = Path(__file__).resolve().parent
DEMO16B_VERSION = "demo16b-1.0.0"

#: Composition agreement Demo 16B requires between Python and nextnano++.
#: Both profiles are evaluated at the *same* cell centres and the linear ramp is
#: analytically identical on both sides, so the expected disagreement is
#: round-off. The allowance is set at ~1% of the nominal 0.55 to absorb a single
#: cell whose centre lands on a region boundary, and the achieved values are
#: always recorded so a run near the limit is visible rather than merely passing.
MAX_ABS_COMPOSITION_ERROR = 5.0e-3
MAX_RMS_COMPOSITION_ERROR = 1.0e-3

#: How far a realized layer width or interface position may sit from the request.
#: One mesh cell is 0.05 nm; two cells of slack covers the cell-centre sampling
#: of ``alloy_composition.dat`` without hiding a real geometry error.
MAX_INTERFACE_POSITION_ERROR_NM = 0.10
MAX_LAYER_WIDTH_ERROR_NM = 0.15

#: Realized 10-90 widths must land near the request. Linear grading is exact by
#: construction; the tolerance covers mesh discretisation only.
MAX_GRADING_WIDTH_ERROR_NM = 0.10

#: Lengths that must never be reported as a grading width. These are the two
#: paper well widths, and reporting either as an interface width is the exact
#: historical regression this demo carries protection against.
FORBIDDEN_GRADING_WIDTHS_NM = (7.1, 2.9)

#: A realized width within this distance of a forbidden length is treated as the
#: regression, not as a coincidence.
FORBIDDEN_WIDTH_MARGIN_NM = 0.40

#: Interface names in growth order, as ``grading14`` labels them.
INTERFACE_ORDER = (
    "outer_left_algaas_to_gaas",
    "central_gaas_to_algaas",
    "central_algaas_to_gaas",
    "outer_right_gaas_to_algaas",
)


class Demo16BError(RuntimeError):
    """A Demo 16B infrastructure failure, distinct from a case failing."""


# ---------------------------------------------------------------------------
# Geometry and rendering -- all production code
# ---------------------------------------------------------------------------


def build_case(cfg: Mapping[str, Any], case: cases16b.SimpleCase):
    """Geometry, authoritative profile, deck blocks and deck.

    Every step is Demo 14's. Demo 16B chooses the parameters and nothing else.
    """

    params = case.parameters()
    geometry = demo14.geometry_for(cfg, params)
    profile = demo14.build_grading(cfg, params, geometry)
    blocks = grading14.render_structure_blocks(profile)
    deck = demo14.render_deck(cfg, geometry, profile, blocks)
    return geometry, profile, blocks, deck


def interface_widths(case: cases16b.SimpleCase) -> dict[str, float]:
    """Requested 10-90 width per interface.

    Growth direction decides which of the two widths an interface takes: where Al
    rises with z it is a GaAs->AlGaAs interface, where it falls, AlGaAs->GaAs.
    """

    return {
        "outer_left_algaas_to_gaas": case.algaas_to_gaas_grading_width_10_90_nm,
        "central_gaas_to_algaas": case.gaas_to_algaas_grading_width_10_90_nm,
        "central_algaas_to_gaas": case.algaas_to_gaas_grading_width_10_90_nm,
        "outer_right_gaas_to_algaas": case.gaas_to_algaas_grading_width_10_90_nm,
    }


# ``alloy_x`` precedes the spatial ``x`` in the emitted ternary block.  A bare
# ``x\s*=`` pattern therefore captures the alloy endpoints (0..0.55) and makes
# all four valid ramps appear to overlap at the origin.  Require that the
# spatial key is not the suffix of ``alloy_x``.
_RAMP_SPAN = re.compile(
    r"(?<!alloy_)x\s*=\s*\[\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\]"
)
_RAMP_ALLOY = re.compile(r"alloy_x\s*=\s*\[\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\]")


def grading_regions_report(
    profile: grading14.CompositionProfile, blocks: Mapping[str, Any]
) -> dict[str, Any]:
    """Audit the graded regions the renderer actually emitted.

    Section C of the Demo 16B brief: every grade records its requested width, its
    interface centre, its start and end position and its requested Al endpoints,
    and **no grade may silently overwrite another**. The numbers are read back
    out of the emitted region text rather than recomputed, so this checks the
    renderer's output rather than agreeing with its input by construction.

    A pair of ramps that share any span is a rejection, not a warning: the deck
    lists regions in order and a later one overrides an earlier one, so the
    realized profile would be neither of the two grades requested.
    """

    request = profile.request
    interfaces = request["interfaces_nm"]
    method = str(request.get("render_method", ""))
    native = method == "ternary_linear" and not blocks.get("datafile")

    grades: list[dict[str, Any]] = []
    for entry in blocks.get("regions", ()):
        material = str(entry.get("material", ""))
        if "ternary_linear{" not in material:
            continue
        span = _RAMP_SPAN.search(material)
        alloy = _RAMP_ALLOY.search(material)
        if span is None or alloy is None:
            raise Demo16BError(
                f"emitted ternary_linear region is unreadable: {material!r}"
            )
        start, end = float(span.group(1)), float(span.group(2))
        centre = 0.5 * (start + end)
        # Attach the ramp to the interface it is centred on. A ramp that matches
        # none of the four would mean the renderer invented an interface.
        name = min(interfaces, key=lambda k: abs(float(interfaces[k]) - centre))
        grades.append({
            "interface": name,
            "requested_interface_centre_nm": float(interfaces[name]),
            "emitted_start_nm": start,
            "emitted_end_nm": end,
            "emitted_centre_nm": centre,
            "emitted_span_nm": end - start,
            "requested_al_start": float(alloy.group(1)),
            "requested_al_end": float(alloy.group(2)),
        })

    grades.sort(key=lambda g: g["emitted_start_nm"])
    overlaps: list[dict[str, Any]] = []
    for left, right in zip(grades, grades[1:]):
        if right["emitted_start_nm"] < left["emitted_end_nm"] - 1e-9:
            overlaps.append({
                "left": left["interface"], "right": right["interface"],
                "overlap_nm": left["emitted_end_nm"] - right["emitted_start_nm"],
            })

    covered = {g["interface"] for g in grades}
    return {
        "render_method": method,
        "native_linear_regions": bool(native),
        "graded_region_count": len(grades),
        "grades": grades,
        "all_four_interfaces_graded": covered == set(INTERFACE_ORDER),
        "graded_regions_disjoint": not overlaps,
        "overlaps": overlaps,
        "supported_by_demo16b": bool(
            native and not overlaps and covered == set(INTERFACE_ORDER)
        ),
    }


# ---------------------------------------------------------------------------
# Level 2 -- the composition nextnano++ actually built
# ---------------------------------------------------------------------------


def find_alloy_composition(root: Path) -> Path:
    """Locate ``Structure/alloy_composition.dat`` beneath a structure run.

    Deliberately unambiguous: more than one match means the search reached
    another run's output and the comparison would be against the wrong deck.
    """

    root = Path(root)
    matches = sorted(
        p for p in root.rglob("alloy_composition.dat")
        if p.is_file() and p.parent.name.lower() == "structure"
    )
    if len(matches) == 1:
        return matches[0]
    present = sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*") if p.is_file()
    )[:30]
    raise Demo16BError(
        f"expected exactly one Structure/alloy_composition.dat beneath {root}, "
        f"found {len(matches)}. Files present: {present or 'none'}"
    )


def read_alloy_composition(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """``x[nm]`` and ``Alloy_x[]`` from a nextnano++ structure output.

    nextnano++ writes this table on the **cell-centre** grid, one composition per
    cell, not on the node grid -- so the positions are not the mesh lines from
    the deck and the intended profile has to be evaluated at these coordinates
    rather than at the requested ones.
    """

    rows: list[list[float]] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            values = [float(token) for token in line.replace(",", " ").split()]
        except ValueError:
            continue
        if len(values) >= 2:
            rows.append(values[:2])
    if len(rows) < 2:
        raise Demo16BError(f"{path} has fewer than two numeric rows.")
    data = np.asarray(rows, dtype=float)
    x, al = data[:, 0], data[:, 1]
    if not np.all(np.diff(x) > 0):
        raise Demo16BError(f"{path} positions are not strictly ascending.")
    if not np.all(np.isfinite(al)):
        raise Demo16BError(f"{path} contains a non-finite alloy fraction.")
    return x, al


def intended_on(profile: grading14.CompositionProfile, x_nm: np.ndarray) -> np.ndarray:
    """The authoritative Python ``x_Al(z)`` sampled at arbitrary positions.

    ``al_fraction_continuous`` is the same analytic profile on a 20x-oversampled
    grid (0.0025 nm at the production mesh). It is piecewise linear, so linear
    interpolation onto the solver's cell centres is exact everywhere except
    within one fine cell of a kink, where it is bounded by a quarter of the
    slope change times the fine spacing -- under 3e-4 in Al fraction, two orders
    below the comparison tolerance.
    """

    return np.interp(
        np.asarray(x_nm, dtype=float),
        np.asarray(profile.x_nm_continuous, dtype=float),
        np.asarray(profile.al_fraction_continuous, dtype=float),
    )


def compare_compositions(
    profile: grading14.CompositionProfile,
    case: cases16b.SimpleCase,
    x_real: np.ndarray,
    al_real: np.ndarray,
) -> dict[str, Any]:
    """Intended vs realized ``x_Al(z)``, plus the geometry read back out of it.

    Every interface metric is measured in a **local window around that
    interface** using Demo 16's own measurement code. A crossing search over a
    whole well is what once reported the 7.1 nm well width as a grading width,
    and a local window makes that impossible rather than merely unlikely.
    """

    x_real = np.asarray(x_real, dtype=float)
    al_real = np.asarray(al_real, dtype=float)
    intended = intended_on(profile, x_real)
    residual = al_real - intended

    max_al = float(profile.request["max_al_fraction"])
    interfaces = dict(profile.request["interfaces_nm"])
    widths = interface_widths(case)

    metrics = demo16.measure_interfaces(x_real, al_real, interfaces, widths, max_al)
    by_name = {m.name: m for m in metrics}

    def realized_centre(name: str) -> float | None:
        return by_name[name].realized_centre_nm if name in by_name else None

    z = [realized_centre(name) for name in INTERFACE_ORDER]

    def gap(a: int, b: int) -> float | None:
        return None if (z[a] is None or z[b] is None) else float(z[b] - z[a])

    thick_requested, thin_requested = case.well_widths_nm()
    realized_layers = {
        "well_1_width_nm": gap(0, 1),
        "central_barrier_width_nm": gap(1, 2),
        "well_2_width_nm": gap(2, 3),
    }
    requested_layers = {
        "well_1_width_nm": thick_requested,
        "central_barrier_width_nm": case.nominal_central_barrier_thickness_nm,
        "well_2_width_nm": thin_requested,
    }

    invariants = demo16.structural_invariants(x_real, al_real, interfaces, max_al)

    # --- the regression guard, evaluated on the REALIZED profile -------------
    forbidden_hits: list[str] = []
    for name, metric in by_name.items():
        realized = metric.realized_width_10_90_nm
        if realized is None:
            continue
        for forbidden in (*FORBIDDEN_GRADING_WIDTHS_NM, thick_requested, thin_requested):
            if abs(realized - float(forbidden)) <= FORBIDDEN_WIDTH_MARGIN_NM:
                forbidden_hits.append(
                    f"{name}: realized 10-90 width {realized:.3f} nm is the "
                    f"{float(forbidden):.3f} nm WELL width"
                )

    width_errors = [
        abs(m.width_error_nm) for m in metrics if m.width_error_nm is not None
    ]
    centre_errors = [
        abs(m.centre_error_nm) for m in metrics if m.centre_error_nm is not None
    ]
    layer_errors = [
        abs(realized_layers[k] - requested_layers[k])
        for k in requested_layers if realized_layers[k] is not None
    ]

    max_abs = float(np.max(np.abs(residual)))
    rms = float(np.sqrt(np.mean(residual**2)))
    checks = {
        "max_absolute_al_error_within_tolerance": bool(
            max_abs <= MAX_ABS_COMPOSITION_ERROR),
        "rms_al_error_within_tolerance": bool(rms <= MAX_RMS_COMPOSITION_ERROR),
        "all_four_interfaces_located": all(v is not None for v in z),
        "interface_positions_within_tolerance": bool(
            centre_errors and max(centre_errors) <= MAX_INTERFACE_POSITION_ERROR_NM),
        "layer_widths_within_tolerance": bool(
            len(layer_errors) == 3
            and max(layer_errors) <= MAX_LAYER_WIDTH_ERROR_NM),
        "grading_widths_within_tolerance": bool(
            len(width_errors) == 4
            and max(width_errors) <= MAX_GRADING_WIDTH_ERROR_NM),
        "no_well_width_reported_as_grading_width": not forbidden_hits,
        "all_windows_isolated": all(m.window_isolated for m in metrics),
        "structural_invariants_passed": bool(invariants["all_passed"]),
    }
    checks["passed"] = all(checks.values())

    return {
        "comparison_points": int(x_real.size),
        "position_range_nm": [float(x_real[0]), float(x_real[-1])],
        # --- the metrics section E asks for, in its order --------------------
        "max_absolute_al_fraction_error": max_abs,
        "rms_al_fraction_error": rms,
        "peak_expected_al_fraction": float(np.max(intended)),
        "peak_realized_al_fraction": float(np.max(al_real)),
        "min_realized_al_fraction": float(np.min(al_real)),
        "requested_layer_widths_nm": requested_layers,
        "realized_layer_widths_nm": realized_layers,
        "layer_width_errors_nm": {
            k: (None if realized_layers[k] is None
                else abs(realized_layers[k] - requested_layers[k]))
            for k in requested_layers
        },
        "requested_interface_positions_nm": {
            name: float(interfaces[name]) for name in INTERFACE_ORDER
        },
        "realized_interface_positions_nm": {
            name: realized_centre(name) for name in INTERFACE_ORDER
        },
        "left_outer_barrier_present": bool(invariants["left_outer_barrier_present"]),
        "right_outer_barrier_present": bool(invariants["right_outer_barrier_present"]),
        # --- grading, requested vs realized ----------------------------------
        "interface_metrics": [m.as_record() for m in metrics],
        "requested_grading_widths_nm": widths,
        "realized_grading_widths_nm": {
            name: by_name[name].realized_width_10_90_nm for name in INTERFACE_ORDER
        },
        # --- verdicts ---------------------------------------------------------
        "structural_invariants": invariants,
        "forbidden_width_hits": forbidden_hits,
        "tolerances": {
            "max_absolute_al_fraction_error": MAX_ABS_COMPOSITION_ERROR,
            "rms_al_fraction_error": MAX_RMS_COMPOSITION_ERROR,
            "interface_position_nm": MAX_INTERFACE_POSITION_ERROR_NM,
            "layer_width_nm": MAX_LAYER_WIDTH_ERROR_NM,
            "grading_width_nm": MAX_GRADING_WIDTH_ERROR_NM,
        },
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Level 3 -- real physics
# ---------------------------------------------------------------------------


def _region_map(profile: grading14.CompositionProfile) -> dict[str, tuple[float, float]]:
    """Layer intervals for the state analyser.

    ``quantum1d.state_table`` treats every region whose name contains "well" as
    confining, so the two wells must be named accordingly and the barrier must
    not be.
    """

    i = profile.request["interfaces_nm"]
    return {
        "thick_well": (float(i["outer_left_algaas_to_gaas"]),
                       float(i["central_gaas_to_algaas"])),
        "central_barrier": (float(i["central_gaas_to_algaas"]),
                            float(i["central_algaas_to_gaas"])),
        "thin_well": (float(i["central_algaas_to_gaas"]),
                      float(i["outer_right_gaas_to_algaas"])),
    }


def analyse_physics(
    cfg: Mapping[str, Any], raw: Path, profile: grading14.CompositionProfile
) -> dict[str, Any]:
    """Band edges, electron and heavy-hole states, and transition energies.

    Parsing is the shared production path: ``quantum1d.parse_one_band_run`` for
    band edges, electron energies, probabilities and envelopes, and Demo 11's own
    heavy-hole reader for the HH band. Demo 11's reader is used rather than a
    fresh one because it carries the convention that matters -- nextnano++ lists
    hole states with *decreasing* electron-scale energy, so index order is
    confinement order and HH1 is the most confined hole, not the lowest number on
    the page.

    No chi(2), no k-parallel integration, no convergence study. Demo 16B asks
    only whether real quantum states come out of a correctly rendered structure.
    """

    import outputs
    import quantum1d

    import demo11  # heavy: pulled in only when a licensed solve has happened

    parser_profile = outputs.load_profile(str(cfg["nextnano"]["parser_profile"]))
    region = str(cfg["nextnano"]["quantum_region_name"])

    run = quantum1d.parse_one_band_run(
        raw, profile=parser_profile, region_name=region,
        bandedge_columns=cfg["nextnano"]["bandedge_columns"],
    )
    hole_z, hole_energies, hole_envelopes = demo11._hole_states(
        parser_profile, raw, region
    )

    regions = _region_map(profile)
    lo, hi = profile.request["domain_nm"]
    padding = float(cfg["geometry"]["quantum_region_padding_nm"])
    window = (
        max(float(lo), float(profile.request["active_start_nm"]) - padding),
        min(float(hi), float(profile.request["active_end_nm"]) + padding),
    )
    electron_states = quantum1d.state_table(run, regions=regions, quantum_window_nm=window)

    e = np.asarray(run.energies_eV, dtype=float)
    h = np.asarray(hole_energies, dtype=float)

    def at(values: np.ndarray, index: int) -> float | None:
        return float(values[index]) if values.size > index else None

    record: dict[str, Any] = {
        "grid_points": int(run.position_nm.size),
        "state_grid_points": int(run.state_position_nm.size),
        "band_edges_present": bool(run.position_nm.size > 1),
        "band_edge_names": sorted(run.band_edges),
        "electron_state_count": int(e.size),
        "heavy_hole_state_count": int(h.size),
        "electron_energies_eV": e.tolist(),
        "heavy_hole_energies_eV": h.tolist(),
        "E_e1_eV": at(e, 0), "E_e2_eV": at(e, 1),
        "E_hh1_eV": at(h, 0), "E_hh2_eV": at(h, 1),
        "wavefunctions_present": bool(run.envelopes is not None and run.envelopes.size),
        "heavy_hole_wavefunctions_present": bool(np.asarray(hole_envelopes).size > 0),
        "state_energies_finite": bool(
            np.all(np.isfinite(e)) and np.all(np.isfinite(h))),
        "wavefunctions_finite": bool(
            (run.envelopes is None or np.all(np.isfinite(run.envelopes)))
            and np.all(np.isfinite(np.asarray(hole_envelopes, dtype=float)))),
        "envelope_grids_match": bool(
            np.asarray(hole_z).shape == run.state_position_nm.shape
            and np.allclose(np.asarray(hole_z), run.state_position_nm)),
        "maximum_boundary_probability": (
            max((s.boundary_probability for s in electron_states), default=None)),
        "electron_states": [s.as_row() for s in electron_states[:4]],
    }

    transitions: dict[str, Any] = {}
    for label, i_e, i_h in (("e1_hh1", 0, 0), ("e2_hh2", 1, 1)):
        if e.size > i_e and h.size > i_h:
            energy = float(e[i_e] - h[i_h])
            transitions[f"transition_{label}_eV"] = energy
            if energy > 0:
                resonances = chi2mod.resonance_wavelengths_nm([energy])
                transitions[f"transition_{label}_one_photon_nm"] = (
                    resonances["one_photon_resonance_nm"][0])
                transitions[f"transition_{label}_two_photon_nm"] = (
                    resonances["two_photon_resonance_nm"][0])
    record["transitions"] = transitions
    record["transition_energies_calculated"] = bool(transitions)

    target = float(cfg["chi2"]["target_wavelength_nm"])
    fundamental = transitions.get("transition_e1_hh1_two_photon_nm")
    record["target_wavelength_nm"] = target
    record["e1_hh1_two_photon_detuning_nm"] = (
        None if fundamental is None else float(fundamental - target))

    record["parser_provenance"] = (
        run.resolved.provenance(Path(raw)) if run.resolved else {}
    )
    record["completion_evidence"] = outputs.completion_evidence(Path(raw))
    record["log_markers"] = outputs.scan_log_markers(
        outputs.solver_log_text(Path(raw)),
        completion_markers=("DONE",),
        fatal_markers=solver14.FATAL_STDOUT_MARKERS,
    )

    checks = {
        "band_edge_output_exists": record["band_edges_present"],
        "electron_energies_exist": record["electron_state_count"] > 0,
        "heavy_hole_energies_exist": record["heavy_hole_state_count"] > 0,
        "wavefunctions_exist": record["wavefunctions_present"]
        and record["heavy_hole_wavefunctions_present"],
        "state_energies_finite": record["state_energies_finite"],
        "wavefunctions_finite": record["wavefunctions_finite"],
        "transition_energies_calculated": record["transition_energies_calculated"],
        "completion_marker_exists": bool(
            record["completion_evidence"]["job_done_file_present"]),
        "no_stale_job_running_file": bool(
            record["completion_evidence"]["no_stale_job_running_file"]),
        "simulation_information_exists": bool(
            list(Path(raw).rglob("simulation_info.txt"))),
        "no_fatal_marker_in_log": bool(record["log_markers"]["no_fatal_marker"]),
    }
    checks["passed"] = all(checks.values())
    record["checks"] = checks
    return record


# ---------------------------------------------------------------------------
# Per-case orchestration
# ---------------------------------------------------------------------------


@dataclass
class CaseOutcome:
    """One case's verdict at every level it reached."""

    case_id: str
    name: str
    status: str = "pending"
    geometry: dict[str, Any] = field(default_factory=dict)
    grading: dict[str, Any] = field(default_factory=dict)
    grading_regions: dict[str, Any] = field(default_factory=dict)
    intended_invariants: dict[str, Any] = field(default_factory=dict)
    level1: dict[str, Any] = field(default_factory=dict)
    level2: dict[str, Any] = field(default_factory=dict)
    level3: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "status": self.status,
            "demo16b_version": DEMO16B_VERSION,
            "geometry": self.geometry,
            "grading": self.grading,
            "grading_regions": self.grading_regions,
            "intended_structural_invariants": self.intended_invariants,
            "level1_parser": self.level1,
            "level2_structure": self.level2,
            "level3_physics": self.level3,
            "failure_reason": self.failure_reason,
        }


def write_intended_profile(case_dir: Path, profile: grading14.CompositionProfile) -> Path:
    """The authoritative Python profile, written before anything is executed."""

    rows = profile.as_rows()
    return runlog14.write_text_atomic(
        case_dir / "intended_profile.csv",
        "x_nm,al_fraction_requested_continuous,al_fraction_rendered\n"
        + "".join(
            f"{r['x_nm']:.6f},{r['al_fraction_requested_continuous']:.8f},"
            f"{r['al_fraction_rendered']:.8f}\n" for r in rows
        ),
    )


def run_case(
    cfg: Mapping[str, Any],
    case: cases16b.SimpleCase,
    case_dir: Path,
    *,
    exe: Path | None,
    database: Path | None,
    license_path: Path | None = None,
    do_parse: bool = True,
    do_structure: bool = False,
) -> CaseOutcome:
    """Level 1, and -- only if it passed and was asked for -- Level 2.

    Level 2 never runs after a parser failure. A deck nextnano++ refused has no
    realized composition, and reporting one would mean reporting a number that
    does not exist.

    ``do_parse=False`` is for ``--structure`` alone, which is Level 2 by itself:
    the ``--structure`` runmode parses the deck before building it, so a separate
    ``--parse`` pass would run the same grammar check twice. ``--validate`` keeps
    both, because a standalone Level 1 transcript is what makes a Level 2 failure
    attributable to the structure rather than to the syntax.
    """

    outcome = CaseOutcome(case_id=case.case_id, name=case.name)
    case_dir = Path(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    runlog14.write_json_atomic(
        case_dir / "requested_parameters.json",
        {**case.as_record(), "demo16b_version": DEMO16B_VERSION},
    )

    try:
        geometry, profile, blocks, deck = build_case(cfg, case)
    except Exception as exc:  # noqa: BLE001 - recorded in full, never swallowed
        outcome.status = "render_failed"
        outcome.failure_reason = f"{type(exc).__name__}: {exc}"
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        return outcome

    outcome.geometry = geometry.as_record()
    outcome.grading = dict(profile.diagnostics)
    outcome.grading_regions = grading_regions_report(profile, blocks)
    outcome.intended_invariants = demo16.structural_invariants(
        profile.x_nm, profile.al_fraction, profile.request["interfaces_nm"],
        cases16b.AL_FRACTION,
    )
    write_intended_profile(case_dir, profile)

    if not outcome.grading_regions["supported_by_demo16b"]:
        outcome.status = "unsupported_geometry"
        outcome.failure_reason = (
            "graded regions overlap or the renderer did not take the native "
            f"linear path: {outcome.grading_regions['overlaps'] or outcome.grading_regions}"
        )
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        return outcome

    if not outcome.intended_invariants["all_passed"]:
        failed = [k for k, v in outcome.intended_invariants.items()
                  if k != "all_passed" and not v]
        outcome.status = "intended_structure_failed"
        outcome.failure_reason = f"intended profile fails invariants: {failed}"
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        return outcome

    if exe is None:
        outcome.status = "parser_unavailable"
        outcome.failure_reason = "no nextnano++ executable resolved to parse the deck"
        outcome.level1 = {"passed": False, "failure_reason": outcome.failure_reason}
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        return outcome

    outcome.level1 = demo16.parse_deck(
        exe, database, case_dir, deck, blocks["datafile"],
        license_path=license_path,
    )
    if not outcome.level1["passed"]:
        outcome.status = "parser_failed"
        outcome.failure_reason = outcome.level1.get("failure_reason")
        runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
        return outcome
    outcome.status = "parser_passed"

    if do_structure:
        outcome.level2 = run_structure(
            cfg, case, case_dir, profile, blocks, deck,
            exe=exe, database=database, license_path=license_path,
        )
        if outcome.level2.get("passed"):
            outcome.status = "structure_passed"
        else:
            outcome.status = "structure_failed"
            outcome.failure_reason = outcome.level2.get("failure_reason")

    runlog14.write_json_atomic(case_dir / "case_result.json", outcome.as_record())
    return outcome


def run_structure(
    cfg: Mapping[str, Any],
    case: cases16b.SimpleCase,
    case_dir: Path,
    profile: grading14.CompositionProfile,
    blocks: Mapping[str, Any],
    deck: str,
    *,
    exe: Path,
    database: Path | None,
    license_path: Path | None = None,
) -> dict[str, Any]:
    """``--structure``, then compare the realized composition with Python's.

    ``--structure`` parses the deck, builds the grid and the material stack,
    writes the structure output and quits without solving. It is the cheapest
    nextnano++ mechanism that can answer "what did you actually build?".
    """

    invocation = demo16.parse_deck(
        exe, database, case_dir, deck, blocks["datafile"],
        license_path=license_path, runmode="--structure", stage="structure",
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
        table = find_alloy_composition(Path(invocation["output_dir"]))
        x_real, al_real = read_alloy_composition(table)
        comparison = compare_compositions(profile, case, x_real, al_real)
    except Exception as exc:  # noqa: BLE001
        result["failure_reason"] = f"{type(exc).__name__}: {exc}"
        return result

    result["alloy_composition_path"] = str(table)
    result["comparison"] = comparison
    result["passed"] = bool(comparison["checks"]["passed"])
    if not result["passed"]:
        failed = [k for k, v in comparison["checks"].items()
                  if k != "passed" and not v]
        result["failure_reason"] = f"composition comparison failed: {failed}"
    else:
        result["failure_reason"] = None

    intended = intended_on(profile, x_real)
    runlog14.write_text_atomic(
        case_dir / "structure" / "composition_comparison.csv",
        "x_nm,al_fraction_intended,al_fraction_realized,difference\n"
        + "".join(
            f"{a:.6f},{b:.8f},{c:.8f},{c - b:.8e}\n"
            for a, b, c in zip(x_real, intended, al_real)
        ),
    )
    runlog14.write_json_atomic(
        case_dir / "structure" / "comparison_metrics.json", comparison
    )
    return result


def solve_case(
    cfg: Mapping[str, Any],
    case: cases16b.SimpleCase,
    case_dir: Path,
    *,
    machine: Any,
    raw_output_dir: Path | None = None,
) -> dict[str, Any]:
    """Level 3: one real licensed solve and the core physics checks.

    ``solver14.execute_real`` raises on a nonzero exit, a timeout, a fatal stdout
    marker or an empty output tree, so nothing below this line can run on a
    failed solve.
    """

    geometry, profile, blocks, deck_text = build_case(cfg, case)
    physics_dir = Path(case_dir) / "physics"
    input_dir = physics_dir / "nextnano_input"
    input_dir.mkdir(parents=True, exist_ok=True)
    deck = input_dir / "case.in"
    runlog14.write_text_atomic(deck, deck_text)
    imported: dict[str, Path] = {}
    if blocks["datafile"]:
        name = str(cfg["grading"].get("import_name", "al_profile"))
        data_path = input_dir / f"{name}.dat"
        runlog14.write_text_atomic(data_path, blocks["datafile"])
        imported[name] = data_path

    raw = Path(raw_output_dir) if raw_output_dir is not None else physics_dir / "raw"
    required_deck_markers = (
        "output_bandedges", "quantum{", "Gamma{", "HH{", "output_states{",
        "envelopes = yes", "probabilities = yes", "run{ quantum{} }",
    )
    compact_deck = " ".join(deck_text.split())
    missing_markers = [marker for marker in required_deck_markers
                       if marker not in compact_deck]
    record: dict[str, Any] = {
        "case_id": case.case_id,
        "physics_label": case.physics_label,
        "deck_path": str(deck),
        "raw_output_dir": str(raw),
        "requested_quantum_outputs": {
            "band_edges": True,
            "electron_states": True,
            "heavy_hole_states": True,
            "electron_envelopes": True,
            "heavy_hole_envelopes": True,
            "probabilities": True,
        },
        "passed": False,
    }
    if missing_markers:
        record["failure_reason"] = (
            f"full-physics deck is missing required markers: {missing_markers}"
        )
        record["failure_stage"] = "deck_output_request"
        runlog14.write_json_atomic(physics_dir / "physics_result.json", record)
        return record
    try:
        invocation = solver14.execute_real(
            executable=Path(machine.executable),
            database=Path(machine.database) if getattr(machine, "database", None) else None,
            license_path=Path(machine.license) if getattr(machine, "license", None) else None,
            deck=deck, output_dir=raw,
            threads=int(cfg["nextnano"].get("threads", 1)),
            timeout_seconds=float(cfg["nextnano"]["solver_timeout_seconds"]),
            imported_files=imported, logs_dir=physics_dir / "logs",
        )
    except Exception as exc:  # noqa: BLE001 - solver verdict, recorded verbatim
        failed_invocation = getattr(exc, "invocation", None)
        record["solver"] = (
            failed_invocation.as_record() if failed_invocation is not None else {
                "solver_argv": solver14.real_argv(
                    executable=Path(machine.executable),
                    database=(Path(machine.database)
                              if getattr(machine, "database", None) else None),
                    license_path=(Path(machine.license)
                                  if getattr(machine, "license", None) else None),
                    deck=deck, output_dir=raw,
                    threads=int(cfg["nextnano"].get("threads", 1)),
                ),
                "solver_return_code": None,
            }
        )
        record["solver"]["failed"] = True
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
        record["failure_stage"] = "solver"
        runlog14.write_json_atomic(physics_dir / "physics_result.json", record)
        return record

    record["solver"] = invocation.as_record()
    try:
        record["preanalysis_gate"] = verify_quantum_outputs(cfg, raw)
    except Exception as exc:  # noqa: BLE001
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
        record["failure_stage"] = "quantum_output_gate"
        runlog14.write_json_atomic(physics_dir / "physics_result.json", record)
        return record
    try:
        record["analysis"] = analyse_physics(cfg, raw, profile)
    except Exception as exc:  # noqa: BLE001
        record["failure_reason"] = f"{type(exc).__name__}: {exc}"
        record["failure_stage"] = "analysis"
        runlog14.write_json_atomic(physics_dir / "physics_result.json", record)
        return record

    record["passed"] = bool(record["analysis"]["checks"]["passed"])
    if not record["passed"]:
        failed = [k for k, v in record["analysis"]["checks"].items()
                  if k != "passed" and not v]
        record["failure_reason"] = f"physics checks failed: {failed}"
        record["failure_stage"] = "physics_checks"
    runlog14.write_json_atomic(physics_dir / "physics_result.json", record)
    return record


def verify_quantum_outputs(cfg: Mapping[str, Any], raw: Path) -> dict[str, Any]:
    """Require solver completion and every state artifact before analysis."""

    import outputs

    raw = Path(raw)
    completion = outputs.completion_evidence(raw)
    if not completion["job_done_file_present"]:
        raise Demo16BError(f"no job_done.txt beneath full-solver output {raw}")
    if not completion["no_stale_job_running_file"]:
        raise Demo16BError(f"stale job_running.txt beneath full-solver output {raw}")

    profile = outputs.load_profile(str(cfg["nextnano"]["parser_profile"]))
    region = str(cfg["nextnano"]["quantum_region_name"])
    keys = (
        "bandedges",
        "energy_spectrum_gamma", "probabilities_gamma", "envelopes_gamma",
        "energy_spectrum_hh", "probabilities_hh", "envelopes_hh",
    )
    resolved = outputs.resolve_outputs(
        profile, raw, keys, substitutions={"region": region}
    )
    outputs.require_or_diagnose(
        resolved, raw, keys,
        why=("the Demo 16C full-physics deck requests Gamma and HH states, "
             "envelopes, probabilities, and band edges"),
    )
    log_markers = outputs.scan_log_markers(
        outputs.solver_log_text(raw), fatal_markers=solver14.FATAL_STDOUT_MARKERS
    )
    if not log_markers["no_fatal_marker"]:
        raise Demo16BError(
            f"fatal marker(s) in completed solver logs: "
            f"{log_markers['fatal_markers_found']}"
        )
    return {
        "passed": True,
        "solver_return_code_is_zero": True,
        "completion_evidence": completion,
        "log_markers": log_markers,
        "quantum_outputs": resolved.provenance(raw),
    }
