"""Generate Demo 25 pilot and production decks.

The structure comes from Demo 22's validated renderer with Demo 23's geometry,
so no layer width, composition, interface model, mesh or temperature is
restated here. Demo 25 only changes the k block, the state count, and which
per-k outputs are requested.
"""

from __future__ import annotations

import copy
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from config25 import DEMO22, Demo25Error, kmax_per_nm, production_direction_vector

if str(DEMO22) not in sys.path:
    sys.path.insert(0, str(DEMO22))
import deck22  # noqa: E402


@dataclass(frozen=True)
class Demo25DeckSpec:
    name: str
    role: str                    # pilot | production
    k_integration: bool
    no_density: bool
    k_point_subdirectories: bool
    symmetry: str
    keep_dispersion_path: bool
    num_points: int
    relative_size: float
    kmax_per_nm: float
    question: str = ""


def _shape(cfg: Mapping[str, Any], spec: Demo25DeckSpec) -> dict[str, Any]:
    geometry = cfg["geometry"]
    return {
        "geometry": {
            **copy.deepcopy(dict(geometry)),
            "primary_interface_model": "abrupt",
            "secondary_interface_model": "linear_1nm",
            "secondary_grade_width_nm": float(geometry["grade_width_nm"]),
        },
        "materials": copy.deepcopy(dict(cfg["materials"])),
        "mesh": copy.deepcopy(dict(cfg["mesh"])),
        "kp8": {
            "number_of_electron_states": int(cfg["kp8"]["number_of_electron_states"]),
            "number_of_hole_states": int(cfg["kp8"]["number_of_hole_states"]),
            "output_state_count": int(cfg["kp8"]["output_state_count"]),
            "dispersion_kmax_per_nm": float(spec.kmax_per_nm),
            "dispersion_points": int(spec.num_points),
        },
    }


def pilot_specs(cfg: Mapping[str, Any]) -> tuple[Demo25DeckSpec, ...]:
    pilot = cfg["pilot"]
    fraction = float(pilot["relative_size"])
    specs = []
    for variant in pilot["variants"]:
        specs.append(Demo25DeckSpec(
            name=str(variant["name"]), role="pilot",
            k_integration=bool(variant["k_integration"]),
            no_density=bool(variant["no_density"]),
            k_point_subdirectories=bool(variant["k_point_subdirectories"]),
            symmetry=str(variant["symmetry"]),
            keep_dispersion_path=bool(variant["keep_dispersion_path"]),
            num_points=int(pilot["num_points"]), relative_size=fraction,
            kmax_per_nm=kmax_per_nm(cfg, fraction),
            question=str(variant.get("question", "")),
        ))
    return tuple(specs)


def production_spec(cfg: Mapping[str, Any], *, num_points: int | None = None,
                    settings: Mapping[str, Any] | None = None) -> Demo25DeckSpec:
    """Build the production spec.

    ``settings`` carries the pilot-discovered configuration, so the production
    deck is assembled from measured facts rather than from assumptions.
    """
    prod = cfg["production"]
    fraction = float(prod["fraction_of_bz"])
    points = int(num_points if num_points is not None else
                 (prod["matrix_k_points"] or prod["requested_k_points"]))
    resolved = dict(settings or {})
    return Demo25DeckSpec(
        name=f"production_finitek_n{points}_k{int(round(1000 * fraction)):04d}",
        role="production",
        k_integration=bool(resolved.get("k_integration", True)),
        no_density=bool(resolved.get("no_density", True)),
        k_point_subdirectories=bool(resolved.get("k_point_subdirectories", True)),
        symmetry=str(resolved.get("symmetry", "none")),
        keep_dispersion_path=bool(resolved.get("keep_dispersion_path", True)),
        num_points=points, relative_size=fraction,
        kmax_per_nm=kmax_per_nm(cfg, fraction),
        question="finite-k M(k) and extended-state acquisition",
    )


def _k_block(cfg: Mapping[str, Any], spec: Demo25DeckSpec) -> str:
    lines: list[str] = []
    if spec.k_integration:
        lines += [
            "            k_integration{",
            f"                num_points = {int(spec.num_points)}",
            f"                relative_size = {float(spec.relative_size):.9g}",
            f"                symmetry = {spec.symmetry}",
            "                force_k0_subspace = no",
            "            }",
        ]
    else:
        lines.append("            k_integration_disabled{}")
    if spec.keep_dispersion_path:
        vector = production_direction_vector(cfg)
        endpoint = ", ".join(f"{v * spec.kmax_per_nm:.12g}" for v in vector)
        name = str(cfg["kp8"]["production_direction"])
        lines += [
            "            dispersion{",
            "                path{",
            f"                    name = \"Gamma_to_{name}\"",
            "                    point{ k = [0, 0, 0] }",
            f"                    point{{ k = [{endpoint}] }}",
            f"                    num_points = {int(spec.num_points)}",
            "                }",
            "                output_k_vectors{}",
            f"                output_dispersions{{ max_num = {int(cfg['kp8']['output_state_count'])} }}",
            f"                output_masses{{ max_num = {int(cfg['kp8']['output_state_count'])} }}",
            "            }",
        ]
    return "\n".join(lines)


def render(cfg: Mapping[str, Any], spec: Demo25DeckSpec) -> str:
    """Render one Demo 25 deck from the Demo 22 template."""
    text = deck22.render(_shape(cfg, spec),
                         interface_model=str(cfg["geometry"]["interface_model"]),
                         calculation="dispersion")

    # Swap Demo 22's k block for the Demo 25 one.
    start = text.index("            k_integration_disabled{}")
    end = text.index("            classify_by_energy{}")
    text = text[:start] + _k_block(cfg, spec) + "\n" + text[end:]

    if not spec.no_density:
        text = text.replace("        no_density = yes\n", "", 1)
    if spec.k_point_subdirectories:
        text = text.replace('        boundary{ x = dirichlet }',
                            '        boundary{ x = dirichlet }\n'
                            '        k_point_subdirectories = yes', 1)

    header = "\n".join([
        f"# Demo 25 ({spec.role}): {spec.name}",
        f"# Question: {spec.question}" if spec.question else "# Demo 25 deck",
        "# Structure is inherited unchanged from Demo 23; only the k block, the",
        "# state count and the per-k output requests differ.",
        "# Generated file. Do not hand-edit: edit demo25_config.yaml or deck25.py.",
        "",
    ])
    text = re.sub(r"\A# Demo 22:.*?\n\n", "", text, count=1, flags=re.S)
    return header + text


def write_decks(cfg: Mapping[str, Any], specs: tuple[Demo25DeckSpec, ...],
                directory: Path) -> tuple[tuple[Demo25DeckSpec, Path], ...]:
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for spec in specs:
        path = destination / f"{spec.name}.in"
        path.write_text(render(cfg, spec), encoding="utf-8", newline="\n")
        written.append((spec, path))
    return tuple(written)


def assert_structure_matches_demo23(cfg: Mapping[str, Any], demo25_text: str,
                                    demo23_text: str) -> None:
    """Fail if any structural line drifted from the Demo 23 deck.

    Only the quantum block may differ: everything from `global{` through the
    end of `classical{` must be identical, which is what guarantees Demo 25
    did not silently change geometry, mesh, materials or temperature.
    """
    def physics_lines(text: str) -> list[str]:
        # Start at `global{` so header comments, which are cosmetic, are ignored,
        # and stop at `quantum{`, the one block Demo 25 is allowed to change.
        body = text[text.index("global{"):text.index("quantum{")]
        return [line.rstrip() for line in body.splitlines()
                if line.strip() and not line.strip().startswith("#")]

    a, b = physics_lines(demo25_text), physics_lines(demo23_text)
    if a != b:
        first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        detail = ""
        if first < min(len(a), len(b)):
            detail = (f" first difference at structural line {first + 1}: "
                      f"demo25={a[first]!r} demo23={b[first]!r}")
        elif len(a) != len(b):
            detail = f" line counts differ: demo25={len(a)} demo23={len(b)}"
        raise Demo25Error("Demo 25 deck structure drifted from Demo 23." + detail)
