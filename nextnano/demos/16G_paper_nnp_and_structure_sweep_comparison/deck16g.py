"""Decks for Groups 2 and 3, written in the supplied ``.nnp`` files' own style.

Demo 16E's renderer could not be reused here, and the reason matters. Its
``grading14.build_structure_profile`` treats a grading width as a **10-90%**
span and **centres** the ramp on the interface; the supplied files treat it as
the **full** ramp and place it **outside** the well. Building Group 2 with 16E's
renderer would have produced structures that are not comparable with Group 1 --
different ramp widths and different GaAs well widths for the same input number.

So the generated decks are the supplied deck with different numbers: the same
region ordering, the same ``ternary_linear{}`` grammar, the same grid strategy
and the same output requests. That makes Group 1, Group 2 and Group 3 differ in
their structures and in nothing else.

``ternary_linear{}`` is used whenever the profile is a non-overlapping linear
ramp, which is every case this demo generates: the grades sit outside the wells
by construction, so two of them can only meet if the barrier is thinner than the
sum of its two grades. That case is detected and refused rather than rendered
into a deck whose later region silently overwrites the earlier one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import cases16g
import grading16g


class Deck16GError(ValueError):
    """A structure that cannot be rendered exactly as native linear regions."""


@dataclass(frozen=True)
class Layout:
    """Growth-axis coordinates, in nm, in the order the deck lays them down."""

    domain_start: float
    domain_end: float
    left_grade_start: float
    well1_start: float
    well1_end: float
    barrier_start: float
    barrier_end: float
    well2_start: float
    well2_end: float
    right_grade_end: float
    quantum_start: float
    quantum_end: float

    def as_record(self) -> dict[str, float]:
        return {name: float(getattr(self, name)) for name in self.__annotations__}


def layout_for(case: cases16g.StructureCase, cfg: Mapping[str, Any]) -> Layout:
    """Place every layer edge, with the grades outside the wells.

    The wells keep exactly their requested widths -- that is what
    ``outside_well`` placement means -- so a grade widens the *structure*, never
    narrows a well. The outer AlGaAs is the configured period barrier on each
    side, and the quantum region is inset from the domain by its own padding so
    the Dirichlet walls are not the confining potential.
    """

    outer = float(
        case.period_barrier_nm
        if case.period_barrier_nm is not None
        else cfg["numerics"]["domain_padding_nm"]
    )
    left = case.left_grade
    right = case.right_grade

    # The two central grades face each other across the barrier.
    central_reach = left.full_linear_ramp_width_nm + right.full_linear_ramp_width_nm
    if central_reach > case.tunnel_barrier_nm + 1.0e-12:
        raise Deck16GError(
            f"{case.case_id}: the two central grades reach "
            f"{central_reach:.4f} nm across a {case.tunnel_barrier_nm:.4f} nm "
            "barrier, so they overlap. A region template cannot represent that "
            "exactly -- the later region would overwrite the earlier one and "
            "invent a composition nobody asked for. Refusing to render it."
        )

    start = 0.0
    left_grade_start = start + outer
    well1_start = left_grade_start + left.full_linear_ramp_width_nm
    well1_end = well1_start + case.thick_well_nm
    barrier_start = well1_end
    barrier_end = barrier_start + case.tunnel_barrier_nm
    well2_start = barrier_end
    well2_end = well2_start + case.thin_well_nm
    right_grade_end = well2_end + right.full_linear_ramp_width_nm
    domain_end = right_grade_end + outer

    padding = float(cfg["numerics"]["quantum_region_padding_nm"])
    return Layout(
        domain_start=start,
        domain_end=domain_end,
        left_grade_start=left_grade_start,
        well1_start=well1_start,
        well1_end=well1_end,
        barrier_start=barrier_start,
        barrier_end=barrier_end,
        well2_start=well2_start,
        well2_end=well2_end,
        right_grade_end=right_grade_end,
        quantum_start=max(start, left_grade_start - padding),
        quantum_end=min(domain_end, right_grade_end + padding),
    )


def _linear_region(start: float, end: float, alloy_start: float,
                   alloy_end: float, comment: str) -> str:
    return (
        "    region{\n"
        f"        line{{ x = [{start:.6f}, {end:.6f}] }}   # {comment}\n"
        "        ternary_linear{\n"
        '            name    = "Al(x)Ga(1-x)As"\n'
        f"            alloy_x = [{alloy_start:.6f}, {alloy_end:.6f}]\n"
        f"            x       = [{start:.6f}, {end:.6f}]\n"
        "        }\n"
        "    }\n"
    )


def _binary_region(start: float, end: float, comment: str) -> str:
    return (
        "    region{\n"
        f"        line{{ x = [{start:.6f}, {end:.6f}] }}   # {comment}\n"
        '        binary{ name = "GaAs" }\n'
        "    }\n"
    )


def render(
    case: cases16g.StructureCase, cfg: Mapping[str, Any]
) -> tuple[str, dict[str, Any]]:
    """The deck text and a provenance record describing exactly what it contains."""

    layout = layout_for(case, cfg)
    al = float(cfg["materials"]["al_fraction"])
    mesh = float(cfg["numerics"]["mesh_nm"])
    outer_spacing = float(cfg["numerics"]["outer_grid_spacing_nm"])
    temperature = float(cfg["materials"]["temperature_K"])
    electron_states = int(cfg["numerics"]["number_of_electron_states"])
    hole_states = int(cfg["numerics"]["number_of_hole_states"])
    hole_model = str(cfg.get("quantum", {}).get("hole_model", "single_band_hh"))

    regions = [
        "    region{\n"
        "        everywhere{}\n"
        "        contact{ name = fermi_zero }\n"
        "        ternary_constant{\n"
        '            name    = "Al(x)Ga(1-x)As"\n'
        f"            alloy_x = {al:.6f}\n"
        "        }\n"
        "    }\n",
        _binary_region(layout.well1_start, layout.well1_end, "thick GaAs well"),
        _binary_region(layout.well2_start, layout.well2_end, "thin GaAs well"),
    ]
    representation = "abrupt"
    if not case.left_grade.is_abrupt:
        representation = "native_ternary_linear"
        regions.append(_linear_region(
            layout.left_grade_start, layout.well1_start, al, 0.0,
            "left outer grade: AlGaAs -> GaAs",
        ))
        regions.append(_linear_region(
            layout.barrier_start,
            layout.barrier_start + case.left_grade.full_linear_ramp_width_nm,
            0.0, al, "central grade after the thick well: GaAs -> AlGaAs",
        ))
    if not case.right_grade.is_abrupt:
        representation = "native_ternary_linear"
        regions.append(_linear_region(
            layout.barrier_end - case.right_grade.full_linear_ramp_width_nm,
            layout.barrier_end, al, 0.0,
            "central grade before the thin well: AlGaAs -> GaAs",
        ))
        regions.append(_linear_region(
            layout.well2_end, layout.right_grade_end, 0.0, al,
            "right outer grade: GaAs -> AlGaAs",
        ))

    if hole_model == "kp_6band":
        hole_block = (
            f"        kp_6band{{ num_ev = {hole_states}\n"
            "            k_integration_disabled{}\n"
            "        }\n"
        )
    elif hole_model == "single_band_hh":
        hole_block = f"        HH{{ num_ev = {hole_states} }}\n"
    else:
        raise Deck16GError(
            f"unknown quantum.hole_model {hole_model!r}; known: kp_6band, "
            "single_band_hh"
        )

    deck = (
        f"# Demo 16G generated deck -- {case.case_id} ({case.group})\n"
        f"# {case.label}\n"
        "# Grading convention: "
        f"{case.grading_definition} (full ramp outside the well).\n"
        "# Generated by deck16g.render; do not edit by hand.\n"
        "\n"
        "global{\n"
        "    simulate1D{}\n"
        "    crystal_zb{ x_hkl = [1, 0, 0]  y_hkl = [0, 1, 0] }\n"
        '    substrate{ name = "GaAs" }\n'
        f"    temperature = {temperature:.4f}\n"
        "}\n\n"
        "contacts{\n"
        "    fermi{ name = fermi_zero  bias = 0 }\n"
        "}\n\n"
        "structure{\n"
        "    output_region_index{ boxes = no }\n"
        "    output_material_index{ boxes = no }\n"
        "    output_alloy_composition{ boxes = no }\n"
        + "".join(regions)
        + "}\n\n"
        "grid{\n"
        "    xgrid{\n"
        f"        line{{ pos = {layout.domain_start:.6f}      spacing = {outer_spacing:.4f} }}\n"
        f"        line{{ pos = {layout.left_grade_start:.6f}  spacing = {mesh:.4f} }}\n"
        f"        line{{ pos = {layout.right_grade_end:.6f}   spacing = {mesh:.4f} }}\n"
        f"        line{{ pos = {layout.domain_end:.6f}        spacing = {outer_spacing:.4f} }}\n"
        "    }\n"
        "}\n\n"
        "classical{\n"
        "    Gamma{ output_bandedge{ averaged = no } }\n"
        "    HH{}\n"
        "    LH{}\n"
        "    SO{}\n"
        "    output_bandedges{ averaged = no }\n"
        "}\n\n"
        "poisson{\n"
        "    between_fermi_levels{}\n"
        "}\n\n"
        "quantum{\n"
        "    region{\n"
        '        name = "quantum_region"\n'
        f"        x = [{layout.quantum_start:.6f}, {layout.quantum_end:.6f}]\n"
        "        no_density = yes\n"
        "        boundary{ x = dirichlet }\n"
        f"        Gamma{{ num_ev = {electron_states} }}\n"
        + hole_block
        + "        output_states{\n"
        "            max_num       = 8\n"
        "            all_k_points  = yes\n"
        "            envelopes     = yes\n"
        "            probabilities = yes\n"
        "        }\n"
        "    }\n"
        "}\n"
    )

    provenance = {
        "case_id": case.case_id,
        "group": case.group,
        "representation": representation,
        "hole_model": hole_model,
        "grading_definition": case.grading_definition,
        "layout_nm": layout.as_record(),
        "full_ramp_coordinates_nm": {
            "left_outer": [layout.left_grade_start, layout.well1_start],
            "central_after_thick_well": [
                layout.barrier_start,
                layout.barrier_start + case.left_grade.full_linear_ramp_width_nm,
            ],
            "central_before_thin_well": [
                layout.barrier_end - case.right_grade.full_linear_ramp_width_nm,
                layout.barrier_end,
            ],
            "right_outer": [layout.well2_end, layout.right_grade_end],
        },
        "mesh_nm": mesh,
        "outer_grid_spacing_nm": outer_spacing,
        "quantum_model": {
            "electrons": f"Gamma num_ev = {electron_states}",
            "holes": hole_model,
            "requested_electron_states": electron_states,
            "requested_hole_states": hole_states,
        },
        "well_widths_preserved": True,
        "well_width_note": (
            "grades sit outside the wells, so the GaAs well widths in the deck "
            "are exactly the requested ones"
        ),
        **case.left_grade.as_record("left"),
        **case.right_grade.as_record("right"),
    }
    return deck, provenance
