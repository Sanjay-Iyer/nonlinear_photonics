"""Stage 03 - render nextnano++ input decks and imported composition tables.

This stage produces solver *inputs* only. It never runs a solver, so it is
fully exercisable on a machine with no licence, which is what makes the deck
generation testable at home.

Two rendering paths, chosen by profile family:

``abrupt`` and ``linear`` - native nextnano++ grammar
    The domain is initialized as ``ternary_constant`` Al(0.55)Ga(0.45)As, two
    ``binary{ GaAs }`` regions overwrite the wells, and each nonzero linear
    grade becomes one ``ternary_linear{}`` region. Later regions override
    earlier ones, so the ramps are written over the well edges.

``fermi``, ``erf``, ``cosine`` - imported table
    nextnano++ 3.0.0 has no native keyword for these shapes. The sampled
    ``x_Al(z)`` is written as a two-column ``format = DAT`` file (position in
    nm, dimensionless Al fraction) and applied over the whole domain with
    ``ternary_import{}``. nextnano++ interpolates linearly between rows, which
    is why ``s02_grading`` measures the interpolation error.

``ternary_pyramid`` is never emitted; :func:`render_deck` refuses a deck that
contains it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import s01_cases as cases
import s02_grading as grading

DEMO_DIR = Path(__file__).resolve().parent
IMPORT_NAME = "al_profile"
MATERIAL_TERNARY = "Al(x)Ga(1-x)As"
MATERIAL_BINARY = "GaAs"

#: Markers a complete Demo 20 deck must contain. Checked before any solve.
REQUIRED_DECK_MARKERS = (
    "output_alloy_composition", "output_bandedges", "Gamma{", "HH{",
    "envelopes = yes", "run{ quantum{} }",
)


class Inputs20Error(ValueError):
    """A deck or imported table cannot be rendered as configured."""


def template_path(cfg: Mapping[str, Any]) -> Path:
    return DEMO_DIR / str(cfg["solver"]["template"])


# --- imported DAT table -----------------------------------------------------


def import_datafile(profile: grading.CompositionProfile) -> str:
    """The ``format = DAT`` payload: position in nm, then Al fraction.

    Precision is chosen so a 0.05 nm mesh is represented exactly rather than
    being re-quantized by the formatter.
    """

    x = np.asarray(profile.x_nm, dtype=float)
    y = np.asarray(profile.al_fraction, dtype=float)
    if x.size != y.size:
        raise Inputs20Error("profile coordinate and value arrays differ in length.")
    if x.size == 0:
        raise Inputs20Error("refusing to write a zero-length imported profile.")
    if not np.all(np.diff(x) > 0):
        raise Inputs20Error(
            "imported profile coordinates must be strictly ascending; a duplicate "
            "or unsorted row makes nextnano++ interpolate a different function."
        )
    if not np.all(np.isfinite(y)):
        raise Inputs20Error("imported profile contains a non-finite Al fraction.")
    return "".join(f"{xi:.6f} {yi:.8f}\n" for xi, yi in zip(x, y))


def _imported_blocks(
    cfg: Mapping[str, Any], profile: grading.CompositionProfile
) -> dict[str, Any]:
    domain = grading.geometry(cfg).domain_nm
    return {
        "import_block": (
            "import{\n"
            f'    file{{ name = "{IMPORT_NAME}"  filename = "{IMPORT_NAME}.dat"  '
            "format = DAT  number_of_dimensions = 1 }\n"
            "    output_imports{}\n"
            "}\n"
        ),
        "regions": [{
            "x": (float(domain[0]), float(domain[1])),
            "material": (f'ternary_import{{ name = "{MATERIAL_TERNARY}"  '
                         f'import_from = "{IMPORT_NAME}" }}'),
        }],
        "datafile": import_datafile(profile),
    }


# --- native regions ---------------------------------------------------------


def _native_blocks(cfg: Mapping[str, Any], case: cases.GradingCase) -> dict[str, Any]:
    pos = grading.interface_positions(cfg)
    directions = grading.interface_directions(cfg)
    regions: list[dict[str, Any]] = [
        {"x": (pos["I1"], pos["I2"]), "material": f'binary{{ name = "{MATERIAL_BINARY}" }}'},
        {"x": (pos["I3"], pos["I4"]), "material": f'binary{{ name = "{MATERIAL_BINARY}" }}'},
    ]
    if case.profile == "linear":
        for interface_id in cases.INTERFACE_IDS:
            width = case.width(interface_id)
            if width <= 0:
                continue
            lo = pos[interface_id] - width / 2.0
            hi = pos[interface_id] + width / 2.0
            start_x, end_x = directions[interface_id]
            regions.append({
                "x": (lo, hi),
                "material": (
                    f'ternary_linear{{ name = "{MATERIAL_TERNARY}"  '
                    f"alloy_x = [{start_x:.6f}, {end_x:.6f}]  "
                    f"x = [{lo:.6f}, {hi:.6f}] }}"
                ),
                "interface_id": interface_id,
            })
    return {"import_block": "", "regions": regions, "datafile": ""}


def render_blocks(
    cfg: Mapping[str, Any], case: cases.GradingCase,
    profile: grading.CompositionProfile,
) -> dict[str, Any]:
    """The structure blocks for one case, by render method."""

    if case.is_imported:
        return _imported_blocks(cfg, profile)
    return _native_blocks(cfg, case)


def _structure_regions(cfg: Mapping[str, Any], blocks: Mapping[str, Any]) -> str:
    g = grading.geometry(cfg)
    high = float(cfg["materials"]["barrier_al_fraction"])
    parts = [
        "    region{",
        "        everywhere{}",
        f'        ternary_constant{{ name = "{MATERIAL_TERNARY}"  alloy_x = {high:.6f} }}',
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
    """Substitute the template placeholders and gate the result."""

    g = grading.geometry(cfg)
    mesh = float(cfg["mesh"]["active_region_grid_spacing_nm"])
    outer = float(cfg["mesh"]["outer_grid_spacing_nm"])
    # Grid control lines: fine spacing across the active stack, coarse outside.
    # These are control points; nextnano++ realizes the node list between them.
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
        "structure_regions": _structure_regions(cfg, blocks),
        "quantum_region_name": cfg["solver"]["quantum_region_name"],
        "quantum_start_nm": f"{g.quantum_start_nm:.6f}",
        "quantum_end_nm": f"{g.quantum_end_nm:.6f}",
        "number_of_electron_states": cfg["states"]["number_of_electron_states"],
        "number_of_hole_states": cfg["states"]["number_of_hole_states"],
        "output_state_count": cfg["states"]["output_state_count"],
        "dipole_polarization_name": cfg["solver"]["dipole_polarization_name"],
    }
    text = template_path(cfg).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    leftovers = [token for token in values if "{{" + token + "}}" in text]
    if leftovers:
        raise Inputs20Error(f"unresolved template placeholders: {leftovers}")
    if "ternary_pyramid" in text:
        raise Inputs20Error("Demo 20 must never render ternary_pyramid")
    return text


def build_case(
    cfg: Mapping[str, Any], case: cases.GradingCase
) -> tuple[grading.Geometry, grading.CompositionProfile, dict[str, Any], str]:
    """Everything one case needs before a solve: geometry, profile, blocks, deck."""

    collisions = grading.overlaps(cfg, case)
    if collisions:
        raise Inputs20Error(
            f"case {case.case_id}: overlapping grading regions {collisions}"
        )
    profile = grading.build_profile(cfg, case)
    blocks = render_blocks(cfg, case, profile)
    return grading.geometry(cfg), profile, blocks, render_deck(cfg, blocks)


def deck_is_complete(deck: str) -> bool:
    return (all(marker in deck for marker in REQUIRED_DECK_MARKERS)
            and "ternary_pyramid" not in deck)


def write_case_inputs(cfg: Mapping[str, Any], destination: Path) -> list[dict[str, Any]]:
    """Write ``case.in`` (+ ``al_profile.dat``) and a manifest for all 13 cases."""

    destination = Path(destination)
    records: list[dict[str, Any]] = []
    for case in cases.all_cases():
        case_dir = destination / f"case_{case.case_id}"
        case_dir.mkdir(parents=True, exist_ok=True)
        g, profile, blocks, deck = build_case(cfg, case)
        (case_dir / "case.in").write_text(deck, encoding="utf-8", newline="\n")
        if blocks["datafile"]:
            (case_dir / f"{IMPORT_NAME}.dat").write_text(
                blocks["datafile"], encoding="utf-8", newline="\n"
            )
        _write_profile_csv(case_dir / "requested_composition_profile.csv", profile)
        payload = {
            "case": case.as_case_row(cfg),
            "geometry": g.as_record(),
            "profile_request": dict(profile.request),
            "profile_diagnostics": dict(profile.diagnostics),
            "plateau_lengths_nm": grading.plateau_lengths_nm(cfg, case),
            "grade_intervals_nm": {
                key: (list(value) if value else None)
                for key, value in grading.grade_intervals(cfg, case).items()
            },
            "validation": grading.validate_realized(cfg, case),
            "deck_complete": deck_is_complete(deck),
            "datafile_rows": len(blocks["datafile"].splitlines()),
        }
        (case_dir / "grading_manifest.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8", newline="\n"
        )
        records.append(payload)
    return records


def _write_profile_csv(path: Path, profile: grading.CompositionProfile) -> None:
    rows = profile.as_rows()
    header = "x_nm,al_fraction_requested_continuous,al_fraction_rendered\n"
    body = "".join(
        f"{r['x_nm']:.6f},{r['al_fraction_requested_continuous']:.10f},"
        f"{r['al_fraction_rendered']:.10f}\n" for r in rows
    )
    path.write_text(header + body, encoding="utf-8", newline="\n")


def preflight_report(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Every solver-free gate, evaluated before a licence is ever touched."""

    all_cases = cases.all_cases()
    validations = [grading.validate_realized(cfg, case) for case in all_cases]
    decks = []
    for case in all_cases:
        _g, _profile, blocks, deck = build_case(cfg, case)
        decks.append({
            "case_id": case.case_id,
            "render_method": case.render_method,
            "deck_complete": deck_is_complete(deck),
            "datafile_required": case.is_imported,
            "datafile_present": bool(blocks["datafile"]),
            "datafile_rows": len(blocks["datafile"].splitlines()),
            "uses_ternary_pyramid": "ternary_pyramid" in deck,
        })
    return {
        "demo_id": cases.DEMO_ID,
        "case_count": len(all_cases),
        "all_grading_valid": all(row["validation_pass"] for row in validations),
        "overlap_cases": [row["case_id"] for row in validations
                          if row["unintended_overlap"]],
        "all_decks_complete": all(
            row["deck_complete"] and not row["uses_ternary_pyramid"] for row in decks
        ),
        "all_imported_tables_present": all(
            row["datafile_present"] == row["datafile_required"] for row in decks
        ),
        "licensed_solver_run": False,
        "validations": validations,
        "decks": decks,
    }


def write_input_examples(cfg: Mapping[str, Any], path: Path) -> Path:
    """A short markdown file showing the actual generated nextnano++ syntax."""

    lookup = cases.by_id()
    parts = [
        "# Demo 20 - Generated nextnano++ Input Examples", "",
        "The growth coordinate is `x` in nextnano++ and is reported as `z` in "
        "plots. Every width below is a full start-to-end transition width "
        "centred on I1-I4.", "",
    ]
    for case_id, heading in (("00", "Abrupt"), ("03", "Linear 0.7 nm"),
                             ("10", "Fermi-like 0.7 nm")):
        case = lookup[case_id]
        _g, _profile, blocks, deck = build_case(cfg, case)
        widths = dict(zip(cases.INTERFACE_IDS, case.widths_nm))
        parts += [
            f"## {heading}", "", "Requested by Python:", "", "```json",
            json.dumps({"profile": case.profile, "widths_nm": widths}, indent=2),
            "```", "", "Actual generated nextnano++ syntax:", "", "```text",
            _deck_excerpt(case, deck), "```", "",
        ]
        if blocks["datafile"]:
            sample = blocks["datafile"].splitlines()
            parts += ["Imported DAT sample (first/last rows):", "", "```text",
                      *sample[:4], "...", *sample[-4:], "```", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return path


def _deck_excerpt(case: cases.GradingCase, deck: str) -> str:
    """The ``structure{}`` block (and ``import{}`` when present), brace-balanced."""

    lines = deck.splitlines()
    targets = {"structure{"}
    if case.is_imported:
        targets.add("import{")
    wanted: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() not in targets:
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
