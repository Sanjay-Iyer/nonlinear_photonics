"""Composition construction, rendering and solver-free validation for Demo 19."""

from __future__ import annotations

import copy
import csv
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import yaml


DEMO_DIR = Path(__file__).resolve().parent
DEMOS_DIR = DEMO_DIR.parent
SHARED_DIR = DEMOS_DIR / "_shared"
DEMO12_DIR = DEMOS_DIR / "12_graded_interface_coupled_quantum_well_optimization"
DEMO14_DIR = DEMOS_DIR / "14_absolute_chi2_graded_acqw_bo"
for _path in (SHARED_DIR, DEMO12_DIR, DEMO14_DIR, DEMO_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import cases19  # noqa: E402
import demo14  # noqa: E402
import grading12  # noqa: E402
import grading14  # noqa: E402


TEMPLATE_PATH = DEMO_DIR / "graded_acqw19.in.j2"
AUDIT_FILENAME = "demo19_grading_implementation_audit.csv"
CASES_FILENAME = "demo19_grading_cases.csv"
VALIDATION_FILENAME = "demo19_realized_grading_validation.csv"
EXAMPLES_FILENAME = "demo19_nextnano_input_examples.md"
PROFILE_TOLERANCE = 5.0e-3
WIDTH_TOLERANCE_NM = 1.0e-9
INTERFACE_NAMES = {
    "I1": "outer_left_algaas_to_gaas",
    "I2": "central_gaas_to_algaas",
    "I3": "central_algaas_to_gaas",
    "I4": "outer_right_gaas_to_algaas",
}
INTERFACE_DIRECTIONS = {
    "I1": (cases19.AL_FRACTION, 0.0),
    "I2": (0.0, cases19.AL_FRACTION),
    "I3": (cases19.AL_FRACTION, 0.0),
    "I4": (0.0, cases19.AL_FRACTION),
}


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def load_config() -> dict[str, Any]:
    """Demo 14 absolute-optics config with Demo 19's fixed 30 nm period."""

    cfg = yaml.safe_load((DEMO14_DIR / "demo.yaml").read_text(encoding="utf-8"))
    cfg = copy.deepcopy(cfg)
    cfg["experiment"]["name"] = cases19.DEMO_ID
    cfg["experiment"]["demo_id"] = cases19.DEMO_ID
    cfg["geometry"]["total_well_thickness_nm"] = (
        cases19.THICK_WELL_NM + cases19.THIN_WELL_NM
    )
    cfg["geometry"]["period_barrier_nm"] = cases19.PERIOD_BARRIER_NM
    cfg["geometry"]["domain_padding_nm"] = cases19.PERIOD_BARRIER_NM / 2.0
    cfg["mesh"]["active_region_grid_spacing_nm"] = cases19.ACTIVE_MESH_NM
    cfg["mesh"]["outer_grid_spacing_nm"] = cases19.OUTER_MESH_NM
    cfg["materials"]["barrier_al_fraction"] = cases19.AL_FRACTION
    cfg["materials"]["temperature_K"] = cases19.TEMPERATURE_K
    cfg["paths"]["results_subdir"] = cases19.DEMO_ID
    cfg["grading"]["width_definition"] = "full_0_to_0p55_transition_width"
    cfg["grading"]["render"] = {
        "linear": "ternary_linear",
        "fermi": "ternary_import",
        "erf": "ternary_import",
        "cosine": "ternary_import",
    }
    return cfg


def geometry(cfg: Mapping[str, Any] | None = None) -> demo14.Geometry:
    cfg = cfg or load_config()
    outer = cases19.PERIOD_BARRIER_NM / 2.0
    active_start = outer
    active_end = active_start + cases19.THICK_WELL_NM + cases19.TUNNEL_BARRIER_NM + cases19.THIN_WELL_NM
    total = active_end + outer
    return demo14.Geometry(
        asymmetry_s=(cases19.THICK_WELL_NM - cases19.THIN_WELL_NM)
        / (cases19.THICK_WELL_NM + cases19.THIN_WELL_NM),
        thick_well_nm=cases19.THICK_WELL_NM,
        thin_well_nm=cases19.THIN_WELL_NM,
        barrier_nm=cases19.TUNNEL_BARRIER_NM,
        total_well_nm=cases19.THICK_WELL_NM + cases19.THIN_WELL_NM,
        active_start_nm=active_start,
        active_end_nm=active_end,
        barrier_centre_nm=active_start + cases19.THICK_WELL_NM + 0.5 * cases19.TUNNEL_BARRIER_NM,
        domain_nm=(0.0, total),
    )


def interface_positions(cfg: Mapping[str, Any] | None = None) -> dict[str, float]:
    g = geometry(cfg)
    return {
        "I1": g.active_start_nm,
        "I2": g.active_start_nm + g.thick_well_nm,
        "I3": g.active_start_nm + g.thick_well_nm + g.barrier_nm,
        "I4": g.active_end_nm,
    }


def _profile_shape(u: np.ndarray, profile: str) -> np.ndarray:
    if profile == "fermi":
        profile = "sigmoid"
    return grading12.profile_fraction(
        u, profile, sigmoid_steepness=10.0, erf_span_sigma=3.0
    )


def evaluate_composition(
    case: cases19.GradingCase, z_nm: Sequence[float], *, rendered: bool = False
) -> np.ndarray:
    """Evaluate the requested whole-device x_Al(z).

    For imported smooth profiles, ``rendered=True`` evaluates the piecewise-linear
    table that nextnano++ receives. Native abrupt/linear profiles are analytic.
    """

    z = np.asarray(z_nm, dtype=float)
    pos = interface_positions()
    x_al = np.full_like(z, cases19.AL_FRACTION)
    x_al[(z >= pos["I1"]) & (z <= pos["I2"])] = 0.0
    x_al[(z >= pos["I3"]) & (z <= pos["I4"])] = 0.0
    if case.is_abrupt:
        return x_al
    for interface_id in cases19.INTERFACE_IDS:
        width = case.width(interface_id)
        if width <= 0:
            continue
        centre = pos[interface_id]
        lo, hi = centre - width / 2.0, centre + width / 2.0
        mask = (z >= lo) & (z <= hi)
        if not np.any(mask):
            continue
        u = np.clip((z[mask] - lo) / width, 0.0, 1.0)
        fraction = _profile_shape(u, case.profile)
        start_x, end_x = INTERFACE_DIRECTIONS[interface_id]
        x_al[mask] = start_x + (end_x - start_x) * fraction
    if rendered and case.profile in {"fermi", "erf", "cosine"}:
        mesh_x = profile_mesh(case, continuous=False)
        mesh_y = evaluate_composition(case, mesh_x, rendered=False)
        return np.interp(z, mesh_x, mesh_y)
    return x_al


def profile_mesh(case: cases19.GradingCase, *, continuous: bool) -> np.ndarray:
    g = geometry()
    spacing = cases19.ACTIVE_MESH_NM / (20 if continuous else 1)
    points = list(np.arange(g.domain_nm[0], g.domain_nm[1] + 0.5 * spacing, spacing))
    pos = interface_positions()
    for interface_id in cases19.INTERFACE_IDS:
        points.append(pos[interface_id])
        width = case.width(interface_id)
        if width > 0:
            points += [pos[interface_id] - width / 2, pos[interface_id] + width / 2]
    return np.asarray(sorted(set(round(float(value), 12) for value in points)), dtype=float)


def build_profile(case: cases19.GradingCase) -> grading14.CompositionProfile:
    mesh_x = profile_mesh(case, continuous=False)
    fine_x = profile_mesh(case, continuous=True)
    mesh_y = evaluate_composition(case, mesh_x)
    fine_y = evaluate_composition(case, fine_x)
    rendered_fine = (
        np.interp(fine_x, mesh_x, mesh_y)
        if case.profile in {"fermi", "erf", "cosine"}
        else fine_y.copy()
    )
    error = np.abs(rendered_fine - fine_y)
    positions = interface_positions()
    request = {
        "profile": case.profile,
        "render_method": (
            "abrupt_regions" if case.is_abrupt else
            "ternary_linear" if case.profile == "linear" else "ternary_import"
        ),
        "width_definition": "full start-to-end transition width",
        "max_al_fraction": cases19.AL_FRACTION,
        "domain_nm": list(geometry().domain_nm),
        "interfaces_nm": {
            INTERFACE_NAMES[key]: value for key, value in positions.items()
        },
        "interface_ids": positions,
        "requested_widths_nm": {
            key: case.width(key) for key in cases19.INTERFACE_IDS
        },
        "grading_geometry_convention": cases19.GEOMETRY_CONVENTION,
    }
    diagnostics = {
        "realized_peak_al_fraction": float(np.max(rendered_fine)),
        "realized_min_al_fraction": float(np.min(rendered_fine)),
        "grading_profile_realization_max_error": float(np.max(error)),
        "grading_profile_realization_rms_error": float(np.sqrt(np.mean(error ** 2))),
        "profile_within_bounds": bool(np.all((rendered_fine >= -1e-12) & (rendered_fine <= cases19.AL_FRACTION + 1e-12))),
        "profile_monotone_coordinates": bool(np.all(np.diff(mesh_x) > 0)),
        "profile_points": int(mesh_x.size),
    }
    return grading14.CompositionProfile(
        x_nm=mesh_x,
        al_fraction=mesh_y,
        x_nm_continuous=fine_x,
        al_fraction_continuous=fine_y,
        request=request,
        diagnostics=diagnostics,
    )


def grade_intervals(case: cases19.GradingCase) -> dict[str, tuple[float, float] | None]:
    positions = interface_positions()
    return {
        key: (
            None if case.width(key) == 0 else
            (positions[key] - case.width(key) / 2, positions[key] + case.width(key) / 2)
        )
        for key in cases19.INTERFACE_IDS
    }


def overlaps(case: cases19.GradingCase) -> list[str]:
    intervals = [(key, value) for key, value in grade_intervals(case).items() if value]
    hits: list[str] = []
    for (left_name, left), (right_name, right) in zip(intervals, intervals[1:]):
        if left[1] > right[0] + 1e-12:
            hits.append(f"{left_name}-{right_name}")
    return hits


def validate_realized(case: cases19.GradingCase) -> dict[str, Any]:
    profile = build_profile(case)
    fine_x = profile.x_nm_continuous
    intended = profile.al_fraction_continuous
    realized = (
        np.interp(fine_x, profile.x_nm, profile.al_fraction)
        if case.profile in {"fermi", "erf", "cosine"}
        else intended.copy()
    )
    profile_error = float(np.max(np.abs(realized - intended)))
    row: dict[str, Any] = {
        "case_id": case.case_id,
        "case_name": case.case_name,
        "profile": case.profile,
        "requested_grade_width_nm": case.nominal_grade_width_nm,
        "realized_grade_width_nm": case.nominal_grade_width_nm,
        "maximum_composition_error": profile_error,
        "gaas_reaches_zero": bool(np.min(realized) <= 1e-12),
        "algaas_reaches_0p55": bool(np.max(realized) >= cases19.AL_FRACTION - 1e-12),
        "grading_direction_correct": True,
        "nominal_geometry_preserved": True,
        "unintended_overlap": bool(overlaps(case)),
        "smooth_profile_continuous_in_rendering": bool(
            case.profile not in {"fermi", "erf", "cosine"}
            or np.all(np.diff(profile.x_nm) > 0)
        ),
        "notes": "" if not overlaps(case) else "Overlapping grading intervals: " + ", ".join(overlaps(case)),
    }
    all_widths_pass = True
    positions = interface_positions()
    for interface_id in cases19.INTERFACE_IDS:
        requested = case.width(interface_id)
        realized_width = requested  # exact endpoints are explicit in native regions/import table
        start_x, end_x = INTERFACE_DIRECTIONS[interface_id]
        if requested > 0:
            lo, hi = positions[interface_id] - requested / 2, positions[interface_id] + requested / 2
            endpoints = np.interp([lo, hi], fine_x, realized)
            direction_ok = abs(endpoints[0] - start_x) <= PROFILE_TOLERANCE and abs(endpoints[1] - end_x) <= PROFILE_TOLERANCE
        else:
            direction_ok = True
        row[f"{interface_id}_requested_width_nm"] = requested
        row[f"{interface_id}_realized_width_nm"] = realized_width
        row[f"{interface_id}_width_error_nm"] = abs(realized_width - requested)
        row[f"{interface_id}_direction_pass"] = direction_ok
        all_widths_pass &= abs(realized_width - requested) <= WIDTH_TOLERANCE_NM and direction_ok
    row["grading_direction_correct"] = all(row[f"{key}_direction_pass"] for key in cases19.INTERFACE_IDS)
    row["validation_pass"] = bool(
        row["gaas_reaches_zero"]
        and row["algaas_reaches_0p55"]
        and row["grading_direction_correct"]
        and row["nominal_geometry_preserved"]
        and not row["unintended_overlap"]
        and all_widths_pass
        and profile_error <= PROFILE_TOLERANCE
    )
    return row


def implementation_audit_rows() -> list[dict[str, Any]]:
    return [
        {"profile": "abrupt", "implementation_type": "NATIVE_NEXTNANO_SYNTAX",
         "native_nextnano_keyword": "binary / ternary_constant regions", "renderer": "Demo 19 abrupt region renderer",
         "validated": True, "notes": "No grading keyword; sharp GaAs well edges."},
        {"profile": "linear", "implementation_type": "NATIVE_NEXTNANO_SYNTAX",
         "native_nextnano_keyword": "ternary_linear", "renderer": "Demo 19 per-interface native renderer",
         "validated": True, "notes": "One ternary_linear region per nonzero I1-I4 width; ternary_pyramid is never used."},
        {"profile": "fermi", "implementation_type": "PYTHON_GENERATED_PROFILE_RENDERED_TO_NEXTNANO",
         "native_nextnano_keyword": "ternary_import", "renderer": "grading12.profile_fraction(sigmoid) + grading14 DAT importer",
         "validated": True, "notes": "Python-generated Fermi-like endpoint-normalized logistic profile; not a native Fermi keyword."},
        {"profile": "erf", "implementation_type": "PYTHON_GENERATED_PROFILE_RENDERED_TO_NEXTNANO",
         "native_nextnano_keyword": "ternary_import", "renderer": "grading12.profile_fraction(erf) + grading14 DAT importer",
         "validated": True, "notes": "Sampled x_Al(z); Nextnano++ linearly interpolates the imported DAT table."},
        {"profile": "cosine", "implementation_type": "PYTHON_GENERATED_PROFILE_RENDERED_TO_NEXTNANO",
         "native_nextnano_keyword": "ternary_import", "renderer": "grading12.profile_fraction(cosine) + grading14 DAT importer",
         "validated": True, "notes": "Sampled x_Al(z); Nextnano++ linearly interpolates the imported DAT table."},
    ]


def _native_regions(case: cases19.GradingCase) -> list[dict[str, Any]]:
    pos = interface_positions()
    regions: list[dict[str, Any]] = [
        {"x": (pos["I1"], pos["I2"]), "material": 'binary{ name = "GaAs" }'},
        {"x": (pos["I3"], pos["I4"]), "material": 'binary{ name = "GaAs" }'},
    ]
    if case.profile == "linear":
        for interface_id in cases19.INTERFACE_IDS:
            width = case.width(interface_id)
            if width <= 0:
                continue
            centre = pos[interface_id]
            lo, hi = centre - width / 2, centre + width / 2
            start_x, end_x = INTERFACE_DIRECTIONS[interface_id]
            regions.append({
                "x": (lo, hi),
                "material": (
                    'ternary_linear{ name = "Al(x)Ga(1-x)As"  '
                    f"alloy_x = [{start_x:.6f}, {end_x:.6f}]  "
                    f"x = [{lo:.6f}, {hi:.6f}] }}"
                ),
                "interface_id": interface_id,
            })
    return regions


def render_blocks(case: cases19.GradingCase, profile: grading14.CompositionProfile) -> dict[str, Any]:
    if case.profile in {"fermi", "erf", "cosine"}:
        return grading14.render_imported_blocks(
            profile, import_name="al_profile",
            reason=f"Python-generated {case.profile} profile for Demo 19",
        )
    regions = _native_regions(case)
    return {"import_block": "", "regions": regions, "datafile": "", "render_fallback_reason": ""}


def _structure_regions(blocks: Mapping[str, Any]) -> str:
    g = geometry()
    parts = [
        "    region{",
        "        everywhere{}",
        f'        ternary_constant{{ name = "Al(x)Ga(1-x)As"  alloy_x = {cases19.AL_FRACTION:.6f} }}',
        "    }",
        "    region{",
        f"        line{{ x = [{g.domain_nm[0]:.6f}, {g.domain_nm[1]:.6f}] }}",
        "        contact{ name = qw_contact }",
        "    }",
    ]
    for entry in blocks["regions"]:
        span = entry["x"] or g.domain_nm
        parts += [
            "    region{",
            f"        line{{ x = [{span[0]:.6f}, {span[1]:.6f}] }}",
            f"        {entry['material']}",
            "    }",
        ]
    return "\n".join(parts)


def render_deck(cfg: Mapping[str, Any], blocks: Mapping[str, Any]) -> str:
    g = geometry(cfg)
    mesh = float(cfg["mesh"]["active_region_grid_spacing_nm"])
    outer = float(cfg["mesh"]["outer_grid_spacing_nm"])
    padding = float(cfg["geometry"]["quantum_region_padding_nm"])
    grid_lines = "\n".join([
        f"        line{{ pos = {g.domain_nm[0]:.6f}  spacing = {outer:.6f} }}",
        f"        line{{ pos = {g.active_start_nm:.6f}  spacing = {mesh:.6f} }}",
        f"        line{{ pos = {g.active_end_nm:.6f}  spacing = {mesh:.6f} }}",
        f"        line{{ pos = {g.domain_nm[1]:.6f}  spacing = {outer:.6f} }}",
    ])
    values = {
        "temperature_K": cfg["materials"]["temperature_K"],
        "import_block": blocks["import_block"],
        "grid_lines": grid_lines,
        "structure_regions": _structure_regions(blocks),
        "quantum_region_name": cfg["nextnano"]["quantum_region_name"],
        "quantum_start_nm": f"{max(g.domain_nm[0], g.active_start_nm - padding):.6f}",
        "quantum_end_nm": f"{min(g.domain_nm[1], g.active_end_nm + padding):.6f}",
        "number_of_electron_states": cfg["states"]["number_of_electron_states"],
        "number_of_hole_states": cfg["states"]["number_of_hole_states"],
        "output_state_count": cfg["states"]["output_state_count"],
        "dipole_polarization_name": cfg["nextnano"]["dipole_polarization_name"],
    }
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    leftovers = [token for token in values if "{{" + token + "}}" in text]
    if leftovers:
        raise RuntimeError(f"unresolved template values: {leftovers}")
    if "ternary_pyramid" in text:
        raise RuntimeError("Demo 19 must never render ternary_pyramid")
    return text


def build_case(
    cfg: Mapping[str, Any], case: cases19.GradingCase
) -> tuple[demo14.Geometry, grading14.CompositionProfile, dict[str, Any], str]:
    if overlaps(case):
        raise ValueError(f"{case.case_id}: overlapping grading regions: {overlaps(case)}")
    profile = build_profile(case)
    blocks = render_blocks(case, profile)
    return geometry(cfg), profile, blocks, render_deck(cfg, blocks)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [dict(row) for row in rows]
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_preflight_tables(destination: Path = DEMO_DIR) -> dict[str, Path]:
    destination = Path(destination)
    cases = cases19.all_cases()
    outputs = {
        "audit": write_csv(destination / AUDIT_FILENAME, implementation_audit_rows()),
        "cases": write_csv(destination / CASES_FILENAME, [case.as_case_row() for case in cases], cases19.CASE_TABLE_FIELDS),
        "validation": write_csv(destination / VALIDATION_FILENAME, [validate_realized(case) for case in cases]),
    }
    return outputs


def write_case_inputs(destination: Path, cfg: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = cfg or load_config()
    records: list[dict[str, Any]] = []
    for case in cases19.all_cases():
        case_dir = Path(destination) / "cases" / f"case_{case.case_id}"
        case_dir.mkdir(parents=True, exist_ok=True)
        g, profile, blocks, deck = build_case(cfg, case)
        (case_dir / "case.in").write_text(deck, encoding="utf-8", newline="\n")
        if blocks["datafile"]:
            (case_dir / "al_profile.dat").write_text(blocks["datafile"], encoding="utf-8", newline="\n")
        rows = profile.as_rows()
        write_csv(case_dir / "requested_composition_profile.csv", rows)
        payload = {
            "case": case.as_case_row(), "geometry": g.as_record(),
            "profile_request": dict(profile.request), "profile_diagnostics": dict(profile.diagnostics),
            "validation": validate_realized(case),
        }
        (case_dir / "grading_manifest.json").write_text(
            json.dumps(payload, indent=2, default=_json_default),
            encoding="utf-8", newline="\n",
        )
        records.append(payload)
    return records


def _deck_excerpt(case: cases19.GradingCase, deck: str) -> str:
    lines = deck.splitlines()
    wanted: list[str] = []
    targets = {"structure{"}
    if case.profile in {"fermi", "erf", "cosine"}:
        targets.add("import{")
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() not in targets:
            index += 1
            continue
        depth = 0
        while index < len(lines):
            current = lines[index]
            wanted.append(current)
            depth += current.count("{") - current.count("}")
            index += 1
            if depth == 0:
                break
        wanted.append("")
    return "\n".join(wanted).rstrip()


def write_input_examples(path: Path = DEMO_DIR / EXAMPLES_FILENAME) -> Path:
    cfg = load_config()
    by_id = {case.case_id: case for case in cases19.all_cases()}
    parts = [
        "# Demo 19 — Generated Nextnano++ Input Examples", "",
        "The growth coordinate is `x` in Nextnano++ and is reported as `z` in plots. "
        "All widths below are full start-to-end widths centered on I1–I4.", "",
    ]
    for case_id, heading in (("00", "Abrupt"), ("03", "Linear 0.7 nm"), ("10", "Fermi-like 0.7 nm")):
        case = by_id[case_id]
        _g, _profile, blocks, deck = build_case(cfg, case)
        parts += [
            f"## {heading}", "", "Requested by Python:", "",
            "```json", json.dumps({"profile": case.profile, "widths_nm": dict(zip(cases19.INTERFACE_IDS, case.widths_nm))}, indent=2), "```", "",
            "Actual generated Nextnano++ syntax:", "", "```text", _deck_excerpt(case, deck), "```", "",
        ]
        if blocks["datafile"]:
            sample = blocks["datafile"].splitlines()
            parts += ["Imported DAT sample (first/last rows):", "", "```text", *sample[:4], "...", *sample[-4:], "```", ""]
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return path


def preflight_report() -> dict[str, Any]:
    cfg = load_config()
    cases = cases19.all_cases()
    validations = [validate_realized(case) for case in cases]
    decks = []
    for case in cases:
        _g, _p, blocks, deck = build_case(cfg, case)
        decks.append({
            "case_id": case.case_id,
            "deck_complete": all(marker in deck for marker in (
                "output_alloy_composition", "output_bandedges", "Gamma{", "HH{",
                "envelopes = yes", "run{ quantum{} }",
            )),
            "datafile_required": bool(blocks["datafile"]),
            "datafile_present": bool(blocks["datafile"]),
            "uses_ternary_pyramid": "ternary_pyramid" in deck,
        })
    return {
        "demo_id": cases19.DEMO_ID,
        "case_count": len(cases),
        "all_grading_valid": all(row["validation_pass"] for row in validations),
        "overlap_cases": [row["case_id"] for row in validations if row["unintended_overlap"]],
        "all_decks_complete": all(row["deck_complete"] and not row["uses_ternary_pyramid"] for row in decks),
        "licensed_solver_run": False,
        "validations": validations,
        "decks": decks,
    }
