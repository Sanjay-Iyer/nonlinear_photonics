"""Generate Demo 23 Professional kp8 decks by reusing Demo 22's renderer."""

from __future__ import annotations

import copy
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from config23 import DEMO_DIR, Demo23Error, kmax_per_nm


DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
if str(DEMO22) not in sys.path:
    sys.path.insert(0, str(DEMO22))
import deck22  # noqa: E402


@dataclass(frozen=True)
class DeckSpec:
    name: str
    direction: str
    points: int
    fraction_of_bz: float
    kmax_per_nm: float
    role: str


def deck_specs(cfg: Mapping[str, Any]) -> tuple[DeckSpec, ...]:
    integration = cfg["integration"]
    production_points = int(integration["production_points"])
    nominal = float(integration["fraction_of_bz"])
    direction = str(cfg["kp8"]["production_direction"])
    specs = [DeckSpec(
        f"production_{direction}_n{production_points}_k0100", direction,
        production_points, nominal, kmax_per_nm(cfg, nominal), "production"
    )]
    for points in integration["grid_convergence_points"]:
        points = int(points)
        if points != production_points:
            specs.append(DeckSpec(
                f"grid_{direction}_n{points}_k0100", direction, points, nominal,
                kmax_per_nm(cfg, nominal), "grid_convergence"
            ))
    for fraction in integration["kmax_convergence_fractions"]:
        fraction = float(fraction)
        if math.isclose(fraction, nominal, abs_tol=1e-12):
            continue
        tag = f"{int(round(1000 * fraction)):04d}"
        specs.append(DeckSpec(
            f"kmax_{direction}_n{production_points}_k{tag}", direction,
            production_points, fraction, kmax_per_nm(cfg, fraction), "kmax_convergence"
        ))
    for other in cfg["kp8"]["directions"]:
        if other != direction:
            specs.append(DeckSpec(
                f"isotropy_{other}_n{production_points}_k0100", str(other),
                production_points, nominal, kmax_per_nm(cfg, nominal), "isotropy"
            ))
    return tuple(specs)


def _demo22_shape(cfg: Mapping[str, Any], spec: DeckSpec) -> dict[str, Any]:
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
            "dispersion_points": int(spec.points),
        },
    }


def render(cfg: Mapping[str, Any], spec: DeckSpec) -> str:
    """Render one path deck; only the k endpoint differs from Demo 22."""

    text = deck22.render(
        _demo22_shape(cfg, spec), interface_model=str(cfg["geometry"]["interface_model"]),
        calculation="dispersion",
    )
    vector = [float(value) for value in cfg["kp8"]["directions"][spec.direction]]
    if len(vector) != 3 or not math.isclose(sum(value * value for value in vector), 1.0, rel_tol=1e-9):
        raise Demo23Error(f"direction {spec.direction} must be a normalized three-vector")
    endpoint = [value * spec.kmax_per_nm for value in vector]
    replacement = "point{ k = [%s] }" % ", ".join(f"{value:.12g}" for value in endpoint)
    original = f"point{{ k = [0, {spec.kmax_per_nm:.9g}, 0] }}"
    count = text.count(original)
    text = text.replace(original, replacement, 1)
    if count != 1:
        raise Demo23Error("could not replace the Demo 22 k-path endpoint")
    text = text.replace("name = \"inplane_Gamma_to_y\"", f"name = \"Gamma_to_{spec.direction}\"")
    text = text.replace("# Demo 22:", "# Demo 23:")
    text = text.replace("edit demo22_config.yaml or deck22.py", "edit Demo 23 configuration or deck23.py")
    return text


def write_decks(cfg: Mapping[str, Any], directory: Path) -> tuple[tuple[DeckSpec, Path], ...]:
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for spec in deck_specs(cfg):
        path = destination / f"{spec.name}.in"
        path.write_text(render(cfg, spec), encoding="utf-8", newline="\n")
        written.append((spec, path))
    return tuple(written)
