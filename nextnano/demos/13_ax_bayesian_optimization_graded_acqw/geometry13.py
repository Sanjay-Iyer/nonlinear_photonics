"""The single authority on whether a graded design can physically be built.

Every caller that needs to know "is this geometry constructible?" -- YAML
validation, Ax candidate preflight, nextnano input generation, reporting and the
tests -- goes through :func:`evaluate`.  There is deliberately no second
implementation: the 2026-07-31 licensed run spent two of sixteen premium trials
discovering geometries that a deterministic check already knew were impossible,
and it did so because the check lived only at input-generation time.

The geometry, as Demo 12 defines it
===================================

The stack is, in growth order::

    left_outer_barrier | left_well | centre_barrier | right_well | right_outer_barrier

with four named interfaces between them::

    outer_to_thick    left_outer_barrier | left_well
    thick_to_central  left_well          | centre_barrier
    central_to_thin   centre_barrier     | right_well
    thin_to_outer     right_well         | right_outer_barrier

A grade of width ``g`` is **centered** on its interface, so it eats ``g/2`` from
the layer on each side.  A layer therefore loses ``g/2`` for every *graded*
interface that bounds it, and must retain at least ``minimum_flat_region_nm`` of
unmodified material:

.. math::

    \\tfrac{1}{2} g \\cdot n_\\text{graded interfaces bounding the layer}
    + \\text{minimum flat} \\le \\text{layer thickness}

Why the count matters
=====================

``grading.location_mode`` decides which interfaces are graded, and that changes
how many grades bound each layer:

==============  ===================================================
location_mode   graded interfaces per layer (outer, well, barrier, well, outer)
==============  ===================================================
``all``         1, 2, 2, 2, 1
``outer_only``  1, 1, 0, 1, 1
``central_only``0, 1, 2, 1, 0
``left_only``   1, 2, 1, 0, 0
``right_only``  0, 0, 1, 2, 1
==============  ===================================================

So the naive rule "grading must not exceed the narrowest layer" is right only for
``all``.  Under ``central_only`` the wells are bounded by a single grade each and
can take twice as much; under ``outer_only`` the centre barrier is not graded at
all and never constrains anything.  Applying one formula to every mode would
reject valid designs and accept impossible ones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO12_DIR = DEMO_DIR.parent / "12_graded_interface_coupled_quantum_well_optimization"
for _path in (str(SHARED), str(DEMO12_DIR), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import DemoError  # noqa: E402

#: Layer order of the Demo 12 stack, and the interfaces bounding each layer.
LAYER_ORDER: tuple[str, ...] = (
    "left_outer_barrier",
    "left_well",
    "centre_barrier",
    "right_well",
    "right_outer_barrier",
)

#: ``layer -> (interface on its low-x side, interface on its high-x side)``.
LAYER_INTERFACES: Mapping[str, tuple[str | None, str | None]] = {
    "left_outer_barrier": (None, "outer_to_thick"),
    "left_well": ("outer_to_thick", "thick_to_central"),
    "centre_barrier": ("thick_to_central", "central_to_thin"),
    "right_well": ("central_to_thin", "thin_to_outer"),
    "right_outer_barrier": ("thin_to_outer", None),
}

#: Which interfaces each ``grading.location_mode`` actually grades. Mirrors
#: ``grading12.select_interfaces`` and is asserted equal to it by a test, so the
#: two can never drift.
LOCATION_INTERFACES: Mapping[str, tuple[str, ...]] = {
    "none": (),
    "abrupt": (),
    "all": ("outer_to_thick", "thick_to_central", "central_to_thin", "thin_to_outer"),
    "outer_only": ("outer_to_thick", "thin_to_outer"),
    "central_only": ("thick_to_central", "central_to_thin"),
    "left_only": ("outer_to_thick", "thick_to_central"),
    "right_only": ("central_to_thin", "thin_to_outer"),
    "narrow_well_only": ("central_to_thin", "thin_to_outer"),
    "wide_well_only": ("outer_to_thick", "thick_to_central"),
}

#: Absolute tolerance for the layer-budget comparison, in nm. A candidate that
#: misses by less than a picometre is a floating-point artefact, not a design.
FEASIBILITY_TOLERANCE_NM = 1e-9


@dataclass(frozen=True)
class LayerBudget:
    """How much of one layer a proposed grade would consume."""

    layer: str
    thickness_nm: float
    graded_interfaces: tuple[str, ...]
    consumed_nm: float
    minimum_flat_nm: float
    remaining_flat_nm: float
    feasible: bool
    maximum_grading_nm: float

    def as_record(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "layer_thickness_nm": self.thickness_nm,
            "graded_interface_count": len(self.graded_interfaces),
            "graded_interfaces": ";".join(self.graded_interfaces),
            "consumed_nm": self.consumed_nm,
            "minimum_flat_region_nm": self.minimum_flat_nm,
            "remaining_flat_nm": self.remaining_flat_nm,
            "layer_feasible": self.feasible,
            "layer_maximum_grading_nm": self.maximum_grading_nm,
        }


@dataclass(frozen=True)
class GeometryVerdict:
    """The complete answer for one proposed geometry."""

    feasible: bool
    reason: str
    requested_grading_nm: float
    realized_grading_nm: float
    maximum_feasible_grading_nm: float
    minimum_flat_region_nm: float
    location_mode: str
    layer_thicknesses_nm: Mapping[str, float]
    budgets: tuple[LayerBudget, ...] = ()
    binding_layer: str | None = None
    snapped: bool = False

    def as_record(self) -> dict[str, Any]:
        return {
            "geometry_feasible": self.feasible,
            "geometry_reason": self.reason,
            "requested_grading_thickness_nm": self.requested_grading_nm,
            "realized_grading_thickness_nm": self.realized_grading_nm,
            "maximum_feasible_grading_thickness_nm": self.maximum_feasible_grading_nm,
            "minimum_flat_region_nm": self.minimum_flat_region_nm,
            "grading_location_mode": self.location_mode,
            "binding_layer": self.binding_layer,
            "grading_snapped_to_mesh": self.snapped,
            **{f"layer_{name}_nm": value for name, value in self.layer_thicknesses_nm.items()},
        }


def graded_interfaces_for(location_mode: str) -> tuple[str, ...]:
    mode = str(location_mode)
    if mode not in LOCATION_INTERFACES:
        raise DemoError(
            f"unknown grading location_mode {mode!r}; expected one of "
            f"{sorted(LOCATION_INTERFACES)}"
        )
    return LOCATION_INTERFACES[mode]


def layer_thicknesses(cfg: Mapping[str, Any]) -> dict[str, float]:
    """Physical layer thicknesses of one resolved configuration."""

    scientific = cfg["scientific"]
    interface_shift = float((cfg.get("grading") or {}).get("interface_shift_nm", 0.0))
    outer = 0.5 * float(scientific["period_barrier_nm"]) + float(
        (cfg.get("numerical") or {}).get("domain_padding_nm", 0.0)
    )
    return {
        "left_outer_barrier": outer,
        "left_well": float(scientific["thick_well_nm"]) + interface_shift,
        "centre_barrier": float(scientific["tunnel_barrier_nm"]),
        "right_well": float(scientific["thin_well_nm"]) - interface_shift,
        "right_outer_barrier": outer,
    }


def minimum_flat_region_nm(cfg: Mapping[str, Any]) -> float:
    grading = cfg.get("grading") or {}
    configured = grading.get("minimum_flat_region_nm")
    if configured is not None:
        value = float(configured)
        if value < 0:
            raise DemoError("grading.minimum_flat_region_nm cannot be negative")
        return value
    # Default to one active-mesh cell: a "layer" thinner than the grid cannot be
    # resolved by the solver, so leaving less than that is not a real layer.
    return float((cfg.get("numerical") or {}).get("active_region_grid_spacing_nm", 0.1))


def mesh_snap_nm(cfg: Mapping[str, Any]) -> float:
    grading = cfg.get("grading") or {}
    configured = grading.get("mesh_snap_nm")
    if configured is not None:
        value = float(configured)
        if value < 0:
            raise DemoError("grading.mesh_snap_nm cannot be negative")
        return value
    return 0.0


def snap_to_mesh(thickness_nm: float, snap_nm: float) -> float:
    """Round a grade width onto the mesh, never upward past feasibility."""

    if snap_nm <= 0:
        return float(thickness_nm)
    return math.floor(float(thickness_nm) / snap_nm + 1e-9) * snap_nm


def maximum_feasible_grading_nm(cfg: Mapping[str, Any]) -> tuple[float, str | None]:
    """Largest constructible centred grade, and which layer limits it.

    Returns ``0.0`` when no grading is possible at all, which happens when some
    layer is already thinner than the minimum flat region.
    """

    graded = graded_interfaces_for(str((cfg.get("grading") or {}).get("location_mode", "all")))
    if not graded:
        return 0.0, None
    thicknesses = layer_thicknesses(cfg)
    minimum_flat = minimum_flat_region_nm(cfg)
    limit = math.inf
    binding: str | None = None
    for layer in LAYER_ORDER:
        low, high = LAYER_INTERFACES[layer]
        count = sum(1 for interface in (low, high) if interface in graded)
        if count == 0:
            continue
        available = thicknesses[layer] - minimum_flat
        # consumed = 0.5 * g * count  <=  thickness - minimum_flat
        layer_limit = 2.0 * available / count
        if layer_limit < limit:
            limit, binding = layer_limit, layer
    if not math.isfinite(limit):
        return 0.0, None
    return max(0.0, limit), binding


def evaluate(
    cfg: Mapping[str, Any], grading_thickness_nm: float | None = None
) -> GeometryVerdict:
    """The authoritative verdict for one resolved configuration.

    ``grading_thickness_nm`` overrides ``grading.selected_thickness_nm`` so a
    candidate can be checked before its configuration is built.
    """

    grading = cfg.get("grading") or {}
    location_mode = str(grading.get("location_mode", "all"))
    requested = float(
        grading.get("selected_thickness_nm", 0.0)
        if grading_thickness_nm is None
        else grading_thickness_nm
    )
    thicknesses = layer_thicknesses(cfg)
    minimum_flat = minimum_flat_region_nm(cfg)
    maximum, binding = maximum_feasible_grading_nm(cfg)

    for layer, thickness in thicknesses.items():
        if thickness <= 0:
            return GeometryVerdict(
                feasible=False,
                reason=f"{layer} has non-positive thickness {thickness:.4g} nm",
                requested_grading_nm=requested,
                realized_grading_nm=0.0,
                maximum_feasible_grading_nm=0.0,
                minimum_flat_region_nm=minimum_flat,
                location_mode=location_mode,
                layer_thicknesses_nm=thicknesses,
            )

    if requested < 0:
        return GeometryVerdict(
            feasible=False,
            reason=f"grading thickness {requested:.4g} nm is negative",
            requested_grading_nm=requested,
            realized_grading_nm=0.0,
            maximum_feasible_grading_nm=maximum,
            minimum_flat_region_nm=minimum_flat,
            location_mode=location_mode,
            layer_thicknesses_nm=thicknesses,
        )

    snap = mesh_snap_nm(cfg)
    realized = snap_to_mesh(requested, snap) if requested > 0 else 0.0
    snapped = bool(snap > 0 and abs(realized - requested) > 1e-12)

    # An abrupt design is trivially constructible; nothing is consumed.
    if realized <= 0:
        return GeometryVerdict(
            feasible=True,
            reason="abrupt interfaces; no material consumed",
            requested_grading_nm=requested,
            realized_grading_nm=0.0,
            maximum_feasible_grading_nm=maximum,
            minimum_flat_region_nm=minimum_flat,
            location_mode=location_mode,
            layer_thicknesses_nm=thicknesses,
            binding_layer=binding,
            snapped=snapped,
        )

    graded = graded_interfaces_for(location_mode)
    budgets: list[LayerBudget] = []
    failures: list[str] = []
    for layer in LAYER_ORDER:
        low, high = LAYER_INTERFACES[layer]
        bounding = tuple(
            name for name in (low, high) if name is not None and name in graded
        )
        consumed = 0.5 * realized * len(bounding)
        remaining = thicknesses[layer] - consumed
        feasible = remaining + FEASIBILITY_TOLERANCE_NM >= minimum_flat
        layer_maximum = (
            math.inf
            if not bounding
            else max(0.0, 2.0 * (thicknesses[layer] - minimum_flat) / len(bounding))
        )
        budgets.append(
            LayerBudget(
                layer=layer,
                thickness_nm=thicknesses[layer],
                graded_interfaces=bounding,
                consumed_nm=consumed,
                minimum_flat_nm=minimum_flat,
                remaining_flat_nm=remaining,
                feasible=feasible,
                maximum_grading_nm=layer_maximum,
            )
        )
        if not feasible:
            failures.append(
                f"{layer} is {thicknesses[layer]:.4g} nm and is bounded by "
                f"{len(bounding)} graded interface(s), which consume "
                f"{consumed:.4g} nm and leave {remaining:.4g} nm of flat material "
                f"(minimum {minimum_flat:.4g} nm)"
            )

    feasible = not failures
    reason = (
        f"constructible; {binding} limits grading to {maximum:.4g} nm"
        if feasible
        else "; ".join(failures)
    )
    return GeometryVerdict(
        feasible=feasible,
        reason=reason,
        requested_grading_nm=requested,
        realized_grading_nm=realized,
        maximum_feasible_grading_nm=maximum,
        minimum_flat_region_nm=minimum_flat,
        location_mode=location_mode,
        layer_thicknesses_nm=thicknesses,
        budgets=tuple(budgets),
        binding_layer=binding,
        snapped=snapped,
    )


def realize_from_fraction(
    cfg: Mapping[str, Any],
    fraction: float,
    *,
    minimum_nm: float = 0.0,
    fraction_bounds: tuple[float, float] | None = None,
) -> tuple[float, float]:
    """Turn a feasible-max fraction into a realized thickness.

    This is the parameterization that makes an infeasible grade unproposable:
    the optimizer chooses *how much of the available room to use*, and the
    available room is recomputed from the barrier and well thicknesses of the
    very design being proposed. Returns ``(realized_nm, maximum_nm)``.

    **Default (``minimum_nm = 0``): the v3 mapping.** The fraction spans
    ``[0, maximum]``, so a low fraction at a narrow barrier lands below the
    mesh-resolvable minimum and the proposal is refused.  Six of v3's seven
    refusals were exactly this, all of them ``erf`` proposals the model kept
    returning to.

    **``minimum_nm > 0``: the interval mapping.** The fraction spans
    ``[minimum_nm, maximum]`` instead, so every value the optimizer can choose
    builds a resolvable grade and the graded branch is valid *by construction*.
    Only a geometry with no room at all (``maximum < minimum_nm``) is refused.

    The mapping is opt-in because it changes what a stored fraction *means*.
    Reinterpreting v3's recorded fractions under it would silently redescribe
    designs that have already been simulated, so it is gated by configuration
    and recorded in the experiment schema.
    """

    lower, upper = fraction_bounds if fraction_bounds else (0.0, 1.0)
    if not lower <= float(fraction) <= upper:
        raise DemoError(
            f"grading_fraction_of_feasible_max must lie in [{lower}, {upper}], "
            f"got {fraction!r}"
        )
    maximum, _binding = maximum_feasible_grading_nm(cfg)
    if maximum <= 0:
        return 0.0, 0.0
    snap = mesh_snap_nm(cfg)

    if minimum_nm > 0.0:
        if maximum < minimum_nm:
            # No resolvable grade exists here at all. Returning 0 lets the
            # caller refuse it with an accurate reason rather than building
            # something narrower than the mesh.
            return 0.0, maximum
        span = upper - lower
        position = 0.0 if span <= 0 else (float(fraction) - lower) / span
        realized = minimum_nm + position * (maximum - minimum_nm)
        if snap > 0:
            # Snapping rounds *down*, which at the lower endpoint would drop the
            # width just below the minimum and have it collapsed to abrupt --
            # making the mapping's own lower bound unreachable. Step up one
            # increment when that happens, unless there is no room to.
            snapped = snap_to_mesh(realized, snap)
            if snapped < minimum_nm:
                snapped = snap_to_mesh(minimum_nm + snap, snap)
                if snapped > maximum:
                    return 0.0, maximum
            realized = snapped
        return min(realized, maximum), maximum

    realized = float(fraction) * maximum
    return (snap_to_mesh(realized, snap) if snap > 0 else realized), maximum


def budget_rows(verdict: GeometryVerdict) -> list[dict[str, Any]]:
    return [budget.as_record() for budget in verdict.budgets]
