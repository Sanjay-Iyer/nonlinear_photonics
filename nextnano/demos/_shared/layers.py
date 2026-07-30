"""Deterministic layer-stack geometry for the nextnano++ learning demos.

Demos 4-9 all describe a 1D growth stack of zincblende layers; Demo 10 adds a
2D cross-section.  This module turns explicit, unit-suffixed layer descriptions
into three things:

1. named position intervals used by every scientific analysis (which well is
   "left", where the centre barrier sits, ...);
2. the ``structure{ region{...} }`` text of the generated deck;
3. the ``grid{ xgrid{ line{...} } }`` text of the generated deck.

Keeping this in Python rather than in the templates means the well boundaries
used by the analysis are *by construction* the same numbers written into the
input deck.  A geometry that cannot be expressed exactly (negative thickness,
zero-width layer, interfaces off the grid) raises before any solver runs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


class GeometryError(ValueError):
    """Raised when a requested layer stack is not physically constructible."""


def _format_nm(value: float) -> str:
    """Render a coordinate deterministically, without float noise."""

    return f"{round(float(value), 9):.9g}"


@dataclass(frozen=True)
class Layer:
    """One grown layer.

    ``role`` is the analysis handle (``left_well``, ``centre_barrier``, ...).
    ``material`` is a nextnano++ database name; ``alloy_x`` must be given for
    ternaries and omitted for binaries.
    """

    role: str
    material: str
    thickness_nm: float
    alloy_x: float | None = None
    grid_spacing_nm: float | None = None

    def __post_init__(self) -> None:
        if not self.role:
            raise GeometryError("every layer needs a non-empty role name.")
        if not math.isfinite(self.thickness_nm) or self.thickness_nm <= 0:
            raise GeometryError(
                f"layer {self.role!r} needs a finite positive thickness_nm, "
                f"got {self.thickness_nm!r}."
            )
        is_ternary = "(x)" in self.material
        if is_ternary and self.alloy_x is None:
            raise GeometryError(f"ternary layer {self.role!r} needs alloy_x.")
        if not is_ternary and self.alloy_x is not None:
            raise GeometryError(
                f"binary layer {self.role!r} must not define alloy_x."
            )
        if self.alloy_x is not None and not 0.0 <= float(self.alloy_x) < 1.0:
            raise GeometryError(
                f"layer {self.role!r}: alloy_x must lie in [0, 1), got {self.alloy_x}."
            )
        if self.grid_spacing_nm is not None and (
            not math.isfinite(self.grid_spacing_nm) or self.grid_spacing_nm <= 0
        ):
            raise GeometryError(
                f"layer {self.role!r}: grid_spacing_nm must be finite and > 0."
            )

    @property
    def is_ternary(self) -> bool:
        return "(x)" in self.material

    def material_block(self, indent: str) -> str:
        if self.is_ternary:
            return (
                f"{indent}ternary_constant{{\n"
                f"{indent}    name    = \"{self.material}\"\n"
                f"{indent}    alloy_x = {self.alloy_x}\n"
                f"{indent}}}"
            )
        return f"{indent}binary{{ name = \"{self.material}\" }}"


@dataclass(frozen=True)
class LayerStack:
    """A resolved 1D stack with absolute coordinates for every layer."""

    layers: tuple[Layer, ...]
    bounds: tuple[tuple[float, float], ...]
    exterior_grid_spacing_nm: float

    @property
    def total_thickness_nm(self) -> float:
        return self.bounds[-1][1]

    def interval(self, role: str) -> tuple[float, float]:
        """Return ``(start_nm, end_nm)`` of the single layer with ``role``."""

        matches = [
            bound
            for layer, bound in zip(self.layers, self.bounds)
            if layer.role == role
        ]
        if not matches:
            raise GeometryError(f"no layer with role {role!r} in this stack.")
        if len(matches) > 1:
            raise GeometryError(f"role {role!r} is not unique in this stack.")
        return matches[0]

    def intervals(self) -> dict[str, tuple[float, float]]:
        """All ``role -> (start_nm, end_nm)`` pairs, ordered by growth."""

        seen: dict[str, tuple[float, float]] = {}
        for layer, bound in zip(self.layers, self.bounds):
            if layer.role in seen:
                raise GeometryError(f"duplicate layer role {layer.role!r}.")
            seen[layer.role] = bound
        return seen

    def quantum_region_nm(self, padding_nm: float) -> tuple[float, float]:
        """Quantum region covering every non-outer layer plus ``padding_nm``.

        The region is clipped to the simulation domain, so an over-large
        padding degrades to "the whole domain" instead of producing an invalid
        deck.
        """

        if not math.isfinite(padding_nm) or padding_nm < 0:
            raise GeometryError("quantum_region_padding_nm must be finite and >= 0.")
        inner = [
            bound
            for layer, bound in zip(self.layers, self.bounds)
            if not layer.role.endswith("outer_barrier")
        ]
        if not inner:
            inner = list(self.bounds)
        start = min(bound[0] for bound in inner) - padding_nm
        end = max(bound[1] for bound in inner) + padding_nm
        return (max(0.0, start), min(self.total_thickness_nm, end))

    def structure_regions(
        self,
        *,
        contact_name: str,
        contact_thickness_nm: float | None = None,
        doping: Sequence[tuple[str, float, float, float]] = (),
        indent: str = "    ",
    ) -> str:
        """Render the ``structure{}`` body.

        The first region fills the domain with the first layer's material and
        every later layer overwrites its own interval, which is the pattern used
        by the repository's validated decks and by the vendor examples.

        ``contact_thickness_nm`` restricts the mandatory contact to a thin slab
        at the left edge.  That matters as soon as Poisson is actually solved:
        a contact attached to ``everywhere{}`` makes the entire domain a
        Dirichlet region, so the potential is pinned everywhere and no band
        bending from doping can appear.  Measured on nextnano++ 3.0.0 (home,
        2026-07-30): with ``run{ poisson{} }`` and a domain-wide contact the
        potential came out flat to 1e-10 kV/cm despite an imposed 100 kV/cm.
        Passing ``None`` reproduces the Demo 1-3 behaviour of attaching the
        contact to the fill region, which is safe only when ``run{}`` contains
        no Poisson step.

        ``doping`` entries are ``(impurity_name, start_nm, end_nm, conc_cm3)``.
        """

        blocks: list[str] = []
        fill = self.layers[0]
        fill_contact = (
            f"\n{indent}    contact{{ name = {contact_name} }}"
            if contact_thickness_nm is None
            else ""
        )
        blocks.append(
            f"{indent}region{{\n"
            f"{indent}    everywhere{{}}\n"
            f"{fill.material_block(indent + '    ')}"
            f"{fill_contact}\n"
            f"{indent}}}"
        )
        if contact_thickness_nm is not None:
            if (
                not math.isfinite(contact_thickness_nm)
                or contact_thickness_nm <= 0
                or contact_thickness_nm >= self.total_thickness_nm
            ):
                raise GeometryError(
                    "contact_thickness_nm must be finite, > 0, and thinner than "
                    f"the {self.total_thickness_nm} nm domain."
                )
            blocks.append(
                f"{indent}# Mandatory contact confined to a thin slab at x = 0 so that it\n"
                f"{indent}# supplies the electrostatic reference without pinning the whole domain.\n"
                f"{indent}region{{\n"
                f"{indent}    line{{ x = [0, {_format_nm(contact_thickness_nm)}] }}\n"
                f"{fill.material_block(indent + '    ')}\n"
                f"{indent}    contact{{ name = {contact_name} }}\n"
                f"{indent}}}"
            )
        for layer, (start, end) in zip(self.layers[1:], self.bounds[1:]):
            blocks.append(
                f"{indent}# {layer.role}\n"
                f"{indent}region{{\n"
                f"{indent}    line{{ x = [{_format_nm(start)}, {_format_nm(end)}] }}\n"
                f"{layer.material_block(indent + '    ')}\n"
                f"{indent}}}"
            )
        for name, start, end, concentration in doping:
            if end <= start:
                raise GeometryError(
                    f"doping region {name!r} needs end_nm > start_nm, got "
                    f"[{start}, {end}]."
                )
            if start < 0 or end > self.total_thickness_nm:
                raise GeometryError(
                    f"doping region {name!r} [{start}, {end}] nm leaves the "
                    f"{self.total_thickness_nm} nm domain."
                )
            if not math.isfinite(concentration) or concentration <= 0:
                raise GeometryError(
                    f"doping region {name!r} needs a finite positive concentration."
                )
            blocks.append(
                f"{indent}region{{\n"
                f"{indent}    line{{ x = [{_format_nm(start)}, {_format_nm(end)}] }}\n"
                f"{indent}    doping{{ constant{{ name = \"{name}\"  conc = {concentration:.6g} }} }}\n"
                f"{indent}}}"
            )
        return "\n".join(blocks)

    def grid_lines(self, indent: str = "        ") -> str:
        """Render ``xgrid{}`` lines that force a grid point on every interface."""

        points: list[tuple[float, float]] = []
        for layer, (start, end) in zip(self.layers, self.bounds):
            spacing = layer.grid_spacing_nm or self.exterior_grid_spacing_nm
            points.append((start, spacing))
            points.append((end, spacing))
        merged: list[tuple[float, float]] = []
        for position, spacing in points:
            if merged and math.isclose(
                merged[-1][0], position, rel_tol=0.0, abs_tol=1e-9
            ):
                merged[-1] = (merged[-1][0], min(merged[-1][1], spacing))
            else:
                merged.append((position, spacing))
        return "\n".join(
            f"{indent}line{{ pos = {_format_nm(position)}  spacing = {spacing:.9g} }}"
            for position, spacing in merged
        )

    def estimated_grid_points(self) -> int:
        """Cheap grid-size estimate used for runtime/cost reporting."""

        total = 1
        for layer, (start, end) in zip(self.layers, self.bounds):
            spacing = layer.grid_spacing_nm or self.exterior_grid_spacing_nm
            total += max(1, int(math.ceil((end - start) / spacing)))
        return total


def build_stack(
    layers: Iterable[Layer], *, exterior_grid_spacing_nm: float
) -> LayerStack:
    """Stack layers from x = 0 and resolve absolute coordinates."""

    resolved = tuple(layers)
    if not resolved:
        raise GeometryError("a layer stack needs at least one layer.")
    if not math.isfinite(exterior_grid_spacing_nm) or exterior_grid_spacing_nm <= 0:
        raise GeometryError("exterior_grid_spacing_nm must be finite and > 0.")
    bounds: list[tuple[float, float]] = []
    cursor = 0.0
    for layer in resolved:
        start = round(cursor, 9)
        cursor = round(cursor + float(layer.thickness_nm), 9)
        bounds.append((start, cursor))
    return LayerStack(
        layers=resolved,
        bounds=tuple(bounds),
        exterior_grid_spacing_nm=float(exterior_grid_spacing_nm),
    )


def algaas(alloy_x: float) -> str:
    """Database name of the AlGaAs ternary (kept in one place on purpose)."""

    if not 0.0 <= float(alloy_x) < 1.0:
        raise GeometryError("aluminium fraction must lie in [0, 1).")
    return "Al(x)Ga(1-x)As"


INGAAS = "In(x)Ga(1-x)As"
GAAS = "GaAs"
ALGAAS = "Al(x)Ga(1-x)As"


def symmetric_double_well(
    *,
    well_width_nm: float,
    centre_barrier_nm: float,
    left_outer_barrier_nm: float,
    right_outer_barrier_nm: float,
    aluminum_fraction: float,
    active_grid_spacing_nm: float,
    exterior_grid_spacing_nm: float,
) -> LayerStack:
    """AlGaAs / GaAs / AlGaAs / GaAs / AlGaAs with two identical wells."""

    return asymmetric_double_well(
        left_well_width_nm=well_width_nm,
        right_well_width_nm=well_width_nm,
        centre_barrier_nm=centre_barrier_nm,
        left_outer_barrier_nm=left_outer_barrier_nm,
        right_outer_barrier_nm=right_outer_barrier_nm,
        aluminum_fraction=aluminum_fraction,
        active_grid_spacing_nm=active_grid_spacing_nm,
        exterior_grid_spacing_nm=exterior_grid_spacing_nm,
    )


def asymmetric_double_well(
    *,
    left_well_width_nm: float,
    right_well_width_nm: float,
    centre_barrier_nm: float,
    left_outer_barrier_nm: float,
    right_outer_barrier_nm: float,
    aluminum_fraction: float,
    active_grid_spacing_nm: float,
    exterior_grid_spacing_nm: float,
) -> LayerStack:
    """Coupled well pair; ``left_well`` is grown first, so it sits at low x."""

    material = algaas(aluminum_fraction)
    return build_stack(
        [
            Layer(
                "left_outer_barrier",
                material,
                left_outer_barrier_nm,
                aluminum_fraction,
                exterior_grid_spacing_nm,
            ),
            Layer(
                "left_well", GAAS, left_well_width_nm, None, active_grid_spacing_nm
            ),
            Layer(
                "centre_barrier",
                material,
                centre_barrier_nm,
                aluminum_fraction,
                active_grid_spacing_nm,
            ),
            Layer(
                "right_well", GAAS, right_well_width_nm, None, active_grid_spacing_nm
            ),
            Layer(
                "right_outer_barrier",
                material,
                right_outer_barrier_nm,
                aluminum_fraction,
                exterior_grid_spacing_nm,
            ),
        ],
        exterior_grid_spacing_nm=exterior_grid_spacing_nm,
    )


def strained_single_well(
    *,
    well_width_nm: float,
    barrier_width_nm: float,
    indium_fraction: float,
    active_grid_spacing_nm: float,
    exterior_grid_spacing_nm: float,
) -> LayerStack:
    """GaAs / InGaAs / GaAs, the pseudomorphic stack used by Demos 7 and 8."""

    return build_stack(
        [
            Layer(
                "left_outer_barrier",
                GAAS,
                barrier_width_nm,
                None,
                exterior_grid_spacing_nm,
            ),
            Layer(
                "well", INGAAS, well_width_nm, indium_fraction, active_grid_spacing_nm
            ),
            Layer(
                "right_outer_barrier",
                GAAS,
                barrier_width_nm,
                None,
                exterior_grid_spacing_nm,
            ),
        ],
        exterior_grid_spacing_nm=exterior_grid_spacing_nm,
    )


@dataclass(frozen=True)
class Rectangle2D:
    """One axis-aligned material rectangle of a 2D cross-section."""

    role: str
    material: str
    x_nm: tuple[float, float]
    y_nm: tuple[float, float]
    alloy_x: float | None = None

    def __post_init__(self) -> None:
        for name, span in (("x_nm", self.x_nm), ("y_nm", self.y_nm)):
            low, high = span
            if not (math.isfinite(low) and math.isfinite(high)) or high <= low:
                raise GeometryError(
                    f"rectangle {self.role!r} needs {name} = [low, high] with high > low."
                )

    def region_block(self, indent: str = "    ") -> str:
        if "(x)" in self.material:
            if self.alloy_x is None:
                raise GeometryError(f"ternary rectangle {self.role!r} needs alloy_x.")
            material = (
                f"{indent}    ternary_constant{{\n"
                f"{indent}        name    = \"{self.material}\"\n"
                f"{indent}        alloy_x = {self.alloy_x}\n"
                f"{indent}    }}"
            )
        else:
            material = f"{indent}    binary{{ name = \"{self.material}\" }}"
        return (
            f"{indent}# {self.role}\n"
            f"{indent}region{{\n"
            f"{indent}    rectangle{{ x = [{_format_nm(self.x_nm[0])}, {_format_nm(self.x_nm[1])}]"
            f"  y = [{_format_nm(self.y_nm[0])}, {_format_nm(self.y_nm[1])}] }}\n"
            f"{material}\n"
            f"{indent}}}"
        )


@dataclass(frozen=True)
class Wire2D:
    """A rectangular GaAs core embedded in an AlGaAs matrix.

    Coordinates follow nextnano++'s 2D convention used by the repository's
    validated ``hello_03a`` deck: ``x`` and ``y`` span the cross-section and the
    remaining direction is the invariant (free-electron) wire axis.
    """

    core_width_nm: float
    core_height_nm: float
    barrier_x_nm: float
    barrier_y_nm: float
    aluminum_fraction: float
    offset_x_nm: float = 0.0
    offset_y_nm: float = 0.0

    @property
    def domain_x_nm(self) -> tuple[float, float]:
        return (0.0, round(self.core_width_nm + 2.0 * self.barrier_x_nm, 9))

    @property
    def domain_y_nm(self) -> tuple[float, float]:
        return (0.0, round(self.core_height_nm + 2.0 * self.barrier_y_nm, 9))

    @property
    def core_x_nm(self) -> tuple[float, float]:
        low = round(self.barrier_x_nm + self.offset_x_nm, 9)
        return (low, round(low + self.core_width_nm, 9))

    @property
    def core_y_nm(self) -> tuple[float, float]:
        low = round(self.barrier_y_nm + self.offset_y_nm, 9)
        return (low, round(low + self.core_height_nm, 9))

    def __post_init__(self) -> None:
        for name, value in (
            ("core_width_nm", self.core_width_nm),
            ("core_height_nm", self.core_height_nm),
            ("barrier_x_nm", self.barrier_x_nm),
            ("barrier_y_nm", self.barrier_y_nm),
        ):
            if not math.isfinite(value) or value <= 0:
                raise GeometryError(f"{name} must be finite and > 0, got {value!r}.")
        if not 0.0 <= float(self.aluminum_fraction) < 1.0:
            raise GeometryError("aluminum_fraction must lie in [0, 1).")
        for name, offset, barrier in (
            ("offset_x_nm", self.offset_x_nm, self.barrier_x_nm),
            ("offset_y_nm", self.offset_y_nm, self.barrier_y_nm),
        ):
            if not math.isfinite(offset) or abs(offset) >= barrier:
                raise GeometryError(
                    f"{name} must be finite and keep the core inside the domain "
                    f"(|offset| < barrier = {barrier})."
                )

    def rectangles(self) -> tuple[Rectangle2D, ...]:
        return (
            Rectangle2D(
                "algaas_matrix",
                ALGAAS,
                self.domain_x_nm,
                self.domain_y_nm,
                self.aluminum_fraction,
            ),
            Rectangle2D("gaas_core", GAAS, self.core_x_nm, self.core_y_nm),
        )

    def structure_regions(self, *, contact_name: str, indent: str = "    ") -> str:
        rectangles = self.rectangles()
        matrix = rectangles[0].region_block(indent)
        matrix = matrix.replace(
            f"\n{indent}}}",
            f"\n{indent}    contact{{ name = {contact_name} }}\n{indent}}}",
        )
        return "\n".join([matrix, *(r.region_block(indent) for r in rectangles[1:])])

    def grid_lines(
        self,
        axis: str,
        *,
        core_spacing_nm: float,
        exterior_spacing_nm: float,
        indent: str = "        ",
    ) -> str:
        if axis not in {"x", "y"}:
            raise GeometryError("axis must be 'x' or 'y'.")
        domain = self.domain_x_nm if axis == "x" else self.domain_y_nm
        core = self.core_x_nm if axis == "x" else self.core_y_nm
        points = [
            (domain[0], exterior_spacing_nm),
            (core[0], core_spacing_nm),
            (core[1], core_spacing_nm),
            (domain[1], exterior_spacing_nm),
        ]
        merged: list[tuple[float, float]] = []
        for position, spacing in points:
            if merged and math.isclose(
                merged[-1][0], position, rel_tol=0.0, abs_tol=1e-9
            ):
                merged[-1] = (merged[-1][0], min(merged[-1][1], spacing))
            else:
                merged.append((position, spacing))
        return "\n".join(
            f"{indent}line{{ pos = {_format_nm(position)}  spacing = {spacing:.9g} }}"
            for position, spacing in merged
        )

    def estimated_grid_points(
        self, *, grid_spacing_x_nm: float, grid_spacing_y_nm: float
    ) -> int:
        nx = int(math.ceil((self.domain_x_nm[1] - self.domain_x_nm[0]) / grid_spacing_x_nm)) + 1
        ny = int(math.ceil((self.domain_y_nm[1] - self.domain_y_nm[0]) / grid_spacing_y_nm)) + 1
        return nx * ny

    def mesh_anisotropy(
        self, *, grid_spacing_x_nm: float, grid_spacing_y_nm: float
    ) -> float:
        """max/min spacing ratio; 1.0 is isotropic."""

        low, high = sorted((float(grid_spacing_x_nm), float(grid_spacing_y_nm)))
        if low <= 0:
            raise GeometryError("grid spacings must be > 0.")
        return high / low
