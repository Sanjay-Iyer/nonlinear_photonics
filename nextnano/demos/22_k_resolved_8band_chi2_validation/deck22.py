"""Render the four controlled Demo 22 nextnano++ decks."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined

from config22 import TEMPLATE_PATH, Demo22Error


def interfaces(cfg: dict[str, Any]) -> tuple[float, float, float, float]:
    g = cfg["geometry"]
    outer = float(g["period_barrier_nm"]) / 2.0
    i1 = outer
    i2 = i1 + float(g["thick_well_nm"])
    i3 = i2 + float(g["tunnel_barrier_nm"])
    i4 = i3 + float(g["thin_well_nm"])
    return i1, i2, i3, i4


def structure_regions(cfg: dict[str, Any], interface_model: str) -> str:
    g, m = cfg["geometry"], cfg["materials"]
    i1, i2, i3, i4 = interfaces(cfg)
    al = float(m["barrier_al_fraction"])
    lines = [
        "    region{ everywhere{} ternary_constant{ name = \"Al(x)Ga(1-x)As\" alloy_x = %.9g } }" % al,
        "    region{ line{ x = [0, 30] } contact{ name = qw_contact } }",
        f"    region{{ line{{ x = [{i1:.9g}, {i2:.9g}] }} binary{{ name = \"GaAs\" }} }}",
        f"    region{{ line{{ x = [{i3:.9g}, {i4:.9g}] }} binary{{ name = \"GaAs\" }} }}",
    ]
    if interface_model == "linear_1nm":
        width = float(g["secondary_grade_width_nm"])
        directions = ((i1, al, 0.0), (i2, 0.0, al), (i3, al, 0.0), (i4, 0.0, al))
        for center, left, right in directions:
            lo, hi = center - width / 2.0, center + width / 2.0
            lines.append(
                f"    region{{ line{{ x = [{lo:.9g}, {hi:.9g}] }} "
                f"ternary_linear{{ name = \"Al(x)Ga(1-x)As\" alloy_x = [{left:.9g}, {right:.9g}] "
                f"x = [{lo:.9g}, {hi:.9g}] }} }}"
            )
    elif interface_model != "abrupt":
        raise Demo22Error(f"unknown interface model {interface_model}")
    return "\n".join(lines)


def k_block(cfg: dict[str, Any], calculation: str) -> str:
    kp = cfg["kp8"]
    if calculation == "integration":
        return (
            "            k_integration{\n"
            f"                num_points = {int(kp['integration_points'])}\n"
            f"                relative_size = {float(kp['integration_relative_size']):.9g}\n"
            f"                symmetry = {kp['integration_symmetry']}\n"
            "                force_k0_subspace = yes\n"
            "            }"
        )
    if calculation == "dispersion":
        maximum = float(kp["dispersion_kmax_per_nm"])
        return (
            "            k_integration_disabled{}\n"
            "            dispersion{\n"
            "                path{\n"
            "                    name = \"inplane_Gamma_to_y\"\n"
            "                    point{ k = [0, 0, 0] }\n"
            f"                    point{{ k = [0, {maximum:.9g}, 0] }}\n"
            f"                    num_points = {int(kp['dispersion_points'])}\n"
            "                }\n"
            "                output_k_vectors{}\n"
            f"                output_dispersions{{ max_num = {int(kp['output_state_count'])} }}\n"
            "                output_masses{ max_num = 14 }\n"
            "            }"
        )
    raise Demo22Error(f"unknown calculation {calculation}")


def render(cfg: dict[str, Any], *, interface_model: str, calculation: str) -> str:
    g, mesh, kp = cfg["geometry"], cfg["mesh"], cfg["kp8"]
    i1, i2, i3, i4 = interfaces(cfg)
    active, outer = float(mesh["active_spacing_nm"]), float(mesh["outer_spacing_nm"])
    grid_lines = "\n".join([
        f"        line{{ pos = 0 spacing = {outer:.9g} }}",
        f"        line{{ pos = {i1:.9g} spacing = {active:.9g} }}",
        f"        line{{ pos = {i2:.9g} spacing = {active:.9g} }}",
        f"        line{{ pos = {i3:.9g} spacing = {active:.9g} }}",
        f"        line{{ pos = {i4:.9g} spacing = {active:.9g} }}",
        f"        line{{ pos = 30 spacing = {outer:.9g} }}",
    ])
    pad = float(g["quantum_region_padding_nm"])
    values = {
        "temperature_K": float(cfg["materials"]["temperature_K"]),
        "grid_lines": grid_lines,
        "structure_regions": structure_regions(cfg, interface_model),
        "quantum_start_nm": i1 - pad,
        "quantum_end_nm": i4 + pad,
        "num_electrons": int(kp["number_of_electron_states"]),
        "num_holes": int(kp["number_of_hole_states"]),
        "output_state_count": int(kp["output_state_count"]),
        "k_block": k_block(cfg, calculation),
    }
    env = Environment(undefined=StrictUndefined, keep_trailing_newline=True)
    return env.from_string(TEMPLATE_PATH.read_text(encoding="utf-8")).render(**values)


def write_decks(cfg: dict[str, Any], directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for interface_model in ("abrupt", "linear_1nm"):
        for calculation in ("integration", "dispersion"):
            path = directory / f"{interface_model}_{calculation}.in"
            path.write_text(render(cfg, interface_model=interface_model, calculation=calculation),
                            encoding="utf-8", newline="\n")
            paths.append(path)
    production = int(cfg["kp8"]["integration_points"])
    for count in cfg["kp8"]["integration_convergence_points"]:
        count = int(count)
        if count == production:
            continue
        probe = copy.deepcopy(cfg)
        probe["kp8"]["integration_points"] = count
        path = directory / f"abrupt_integration_k{count:03d}.in"
        path.write_text(render(probe, interface_model="abrupt", calculation="integration"),
                        encoding="utf-8", newline="\n")
        paths.append(path)
    return paths
