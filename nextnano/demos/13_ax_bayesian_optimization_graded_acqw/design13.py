"""Design-space definition for Demo 13: pure, solver-free, and Ax-free.

Everything here is a function of a parameterization and a configuration.  No
nextnano, no Ax, and no filesystem, so the whole mapping from "what the
optimizer proposed" to "what physical structure that is" can be tested on the
home laptop and reused unchanged by the licensed loop.

The one rule this module exists to enforce: **one physical structure has exactly
one canonical parameterization.**  An abrupt interface is abrupt whatever
profile label a categorical parameter happens to carry, and paying for the same
nextnano run five times because five labels describe it is a bug, not a search.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO12_DIR = DEMO_DIR.parent / "12_graded_interface_coupled_quantum_well_optimization"
for _path in (str(SHARED), str(DEMO12_DIR), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import chi2 as chi2mod  # noqa: E402
from demo_workflow import DemoError  # noqa: E402


#: Grading shapes Demo 13 may propose. A subset of Demo 12's vocabulary: the
#: two Demo 12 shapes left out (``staircase_linear`` and ``asymmetric``) are
#: implementation/robustness studies rather than independent design choices, and
#: including them would put two labels on one physical structure again.
GRADING_PROFILES: tuple[str, ...] = ("abrupt", "linear", "sigmoid", "erf", "cosine")

#: Shapes nextnano++ renders with its native ``ternary_linear`` grammar; the
#: rest use Demo 12's documented constant-composition sublayer fallback.
NATIVE_PROFILES: frozenset[str] = frozenset({"abrupt", "linear"})

#: Continuous search dimensions, in the order used for every table and every
#: normalized distance in this demo.
RANGE_PARAMETERS: tuple[str, ...] = (
    "asymmetry_s",
    "central_barrier_thickness_nm",
    "grading_thickness_nm",
)

#: The optional Section 5 extensions, and where each one lands in the resolved
#: Demo 12 configuration. Disabled by default; see ``bo.optional_parameters``.
OPTIONAL_PARAMETER_TARGETS: Mapping[str, str] = {
    "grading_location": "grading.location_mode",
    "outer_interface_grading_thickness_nm": "grading.outer_thickness_nm",
    "central_interface_grading_thickness_nm": "grading.central_thickness_nm",
    "grading_asymmetry_ratio": "grading.asymmetry_ratio",
    "maximum_aluminum_fraction": "scientific.aluminum_fraction",
    "narrow_well_nm": "scientific.thin_well_nm",
    "wide_well_nm": "scientific.thick_well_nm",
}


class DesignError(DemoError):
    """A proposed parameterization cannot be turned into a valid structure."""


# ---------------------------------------------------------------------------
# canonicalization
# ---------------------------------------------------------------------------


def canonicalize(parameters: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Collapse a raw Ax parameterization onto the structure it really means.

    Two collapses happen here and nowhere else:

    * ``grading_profile == "abrupt"`` forces the realized grading thickness to
      exactly 0 nm, because an abrupt interface has no transition width;
    * a grading thickness at or below ``minimum_graded_thickness_nm`` is an
      abrupt interface whatever shape was requested, because a ramp thinner than
      the mesh can resolve is not a ramp.

    The hierarchical encoding's ``interface_mode`` is folded in first, so both
    encodings produce the same canonical dictionary and the deduplication key
    below is comparable across them.
    """

    space = _search_space(cfg)
    minimum = float(space.get("minimum_graded_thickness_nm", 0.0))
    values = dict(parameters)

    mode = values.pop("interface_mode", None)
    if mode is not None:
        if str(mode) == "abrupt":
            values["grading_profile"] = "abrupt"
            values["grading_thickness_nm"] = 0.0
        else:
            values.setdefault("grading_profile", "linear")
            values.setdefault("grading_thickness_nm", max(minimum, 0.0))

    profile = str(values.get("grading_profile", "abrupt"))
    if profile not in GRADING_PROFILES:
        raise DesignError(
            f"unsupported grading profile {profile!r}; expected one of "
            + ", ".join(GRADING_PROFILES)
        )
    thickness = float(values.get("grading_thickness_nm", 0.0))
    if thickness < 0:
        raise DesignError("grading_thickness_nm cannot be negative")

    if profile == "abrupt" or thickness <= minimum:
        profile, thickness = "abrupt", 0.0

    canonical = {
        "asymmetry_s": float(values["asymmetry_s"]),
        "central_barrier_thickness_nm": float(values["central_barrier_thickness_nm"]),
        "grading_thickness_nm": thickness,
        "grading_profile": profile,
    }
    for name in OPTIONAL_PARAMETER_TARGETS:
        if name in values:
            canonical[name] = values[name]
    return canonical


def _search_space(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    bo = cfg.get("bo")
    if not isinstance(bo, Mapping):
        raise DesignError("demo.yaml: bo must be a mapping")
    space = bo.get("search_space")
    if not isinstance(space, Mapping):
        raise DesignError("demo.yaml: bo.search_space must be a mapping")
    return space


def design_key(
    parameters: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[Any, ...]:
    """A hashable identity for the *structure*, at the configured tolerances.

    Two parameterizations that round to the same key would generate the same
    nextnano input, so running both would buy nothing but solver time.
    """

    canonical = canonicalize(parameters, cfg)
    tolerances = dict(_search_space(cfg).get("duplicate_tolerance") or {})
    key: list[Any] = [canonical["grading_profile"]]
    for name in RANGE_PARAMETERS:
        tolerance = float(tolerances.get(name, 1e-9))
        if tolerance <= 0:
            raise DesignError(f"duplicate_tolerance.{name} must be positive")
        key.append(int(round(float(canonical[name]) / tolerance)))
    for name in sorted(OPTIONAL_PARAMETER_TARGETS):
        if name in canonical:
            value = canonical[name]
            tolerance = float(tolerances.get(name, 0.0))
            key.append(
                int(round(float(value) / tolerance))
                if tolerance > 0 and isinstance(value, (int, float))
                else value
            )
    return tuple(key)


def is_duplicate(
    parameters: Mapping[str, Any], seen: Iterable[tuple[Any, ...]], cfg: Mapping[str, Any]
) -> bool:
    """Whether this parameterization repeats a structure already in ``seen``."""

    if not bool(_search_space(cfg).get("deduplicate_canonical_designs", True)):
        return False
    return design_key(parameters, cfg) in set(seen)


# ---------------------------------------------------------------------------
# parameterization -> resolved Demo 12 configuration
# ---------------------------------------------------------------------------


def _set(config: dict[str, Any], dotted: str, value: Any) -> None:
    cursor: Any = config
    parts = dotted.split(".")
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def total_well_thickness_nm(cfg: Mapping[str, Any]) -> float:
    scientific = cfg["scientific"]
    return float(scientific["thick_well_nm"]) + float(scientific["thin_well_nm"])


def resolve_config(parameters: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Build the fully resolved configuration one trial will be rendered from.

    The asymmetry is converted to well widths at fixed total well material,
    exactly as Demo 12 Stage 5 does, so the two studies place the same point in
    the same place.
    """

    canonical = canonicalize(parameters, cfg)
    resolved = copy.deepcopy(dict(cfg))

    total = total_well_thickness_nm(cfg)
    thick, thin = chi2mod.well_widths_from_asymmetry(canonical["asymmetry_s"], total)
    _set(resolved, "scientific.thick_well_nm", round(float(thick), 9))
    _set(resolved, "scientific.thin_well_nm", round(float(thin), 9))
    _set(
        resolved,
        "scientific.tunnel_barrier_nm",
        float(canonical["central_barrier_thickness_nm"]),
    )

    profile = str(canonical["grading_profile"])
    thickness = float(canonical["grading_thickness_nm"])
    _set(resolved, "grading.profile", profile)
    _set(resolved, "grading.selected_thickness_nm", thickness)
    _set(
        resolved,
        "grading.implementation",
        "native" if profile in NATIVE_PROFILES else "staircase",
    )
    # Demo 11 carries a scalar grading field for backward compatibility; keeping
    # it in step means a Demo 13 row and a Demo 11 row never disagree about how
    # abrupt the same structure was.
    _set(resolved, "scientific.interface_grading_nm", thickness)

    for name, target in OPTIONAL_PARAMETER_TARGETS.items():
        if name in canonical:
            _set(resolved, target, canonical[name])

    _validate_geometry(resolved, canonical, cfg)
    return resolved


def _validate_geometry(
    resolved: Mapping[str, Any], canonical: Mapping[str, Any], cfg: Mapping[str, Any]
) -> None:
    """Reject geometrically impossible designs before any solver time is spent."""

    scientific = resolved["scientific"]
    thick = float(scientific["thick_well_nm"])
    thin = float(scientific["thin_well_nm"])
    barrier = float(scientific["tunnel_barrier_nm"])
    if thin <= 0 or thick <= 0:
        raise DesignError(
            f"asymmetry_s={canonical['asymmetry_s']:.4g} leaves a non-positive well width"
        )
    if barrier <= 0:
        raise DesignError("central_barrier_thickness_nm must be positive")
    thickness = float(canonical["grading_thickness_nm"])
    if thickness <= 0:
        return
    # Every grade is centered on its interface and consumes half its width from
    # each side, so the narrowest adjacent layer sets the ceiling. Demo 12
    # flags overlapping grades; Demo 13 refuses to propose them at all.
    narrowest = min(thin, thick, barrier)
    if thickness > narrowest:
        raise DesignError(
            f"grading_thickness_nm={thickness:.4g} exceeds the narrowest adjacent "
            f"layer ({narrowest:.4g} nm); centered grades would overlap"
        )


def parameters_from_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Inverse mapping: what parameterization does this configuration describe?

    Used to place a Demo 12 case, a validation perturbation, or a resumed
    trial back into Demo 13's coordinates.
    """

    scientific = cfg["scientific"]
    grading = cfg.get("grading") or {}
    thickness = float(grading.get("selected_thickness_nm", 0.0))
    profile = str(grading.get("profile", "abrupt"))
    if profile not in GRADING_PROFILES:
        # Demo 12's implementation-study shapes carry no Demo 13 identity.
        profile = "linear" if thickness > 0 else "abrupt"
    return {
        "asymmetry_s": chi2mod.structural_asymmetry(
            float(scientific["thick_well_nm"]), float(scientific["thin_well_nm"])
        ),
        "central_barrier_thickness_nm": float(scientific["tunnel_barrier_nm"]),
        "grading_thickness_nm": thickness,
        "grading_profile": profile,
    }


def reference_parameters(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The Demo 11 / Demo 12 abrupt reference expressed in Demo 13 coordinates."""

    return canonicalize(parameters_from_config(cfg), cfg)


# ---------------------------------------------------------------------------
# normalized coordinates (state tracking, nearest neighbours, plots)
# ---------------------------------------------------------------------------


def normalized_point(
    parameters: Mapping[str, Any], cfg: Mapping[str, Any]
) -> dict[str, float]:
    """Scale the continuous parameters onto comparable ranges.

    Distances between designs are meaningless while asymmetry is measured in
    units of 0.2 and barrier thickness in units of 2 nm.  Scales are explicit
    in ``state_tracking.parameter_scales`` rather than derived from the sampled
    data, so a distance computed early in a run means the same thing later.
    """

    canonical = canonicalize(parameters, cfg)
    scales = dict((cfg.get("state_tracking") or {}).get("parameter_scales") or {})
    point: dict[str, float] = {}
    for name in RANGE_PARAMETERS:
        scale = float(scales.get(name, 1.0))
        if scale <= 0:
            raise DesignError(f"state_tracking.parameter_scales.{name} must be positive")
        point[name] = float(canonical[name]) / scale
    return point


def design_distance(
    a: Mapping[str, Any], b: Mapping[str, Any], cfg: Mapping[str, Any]
) -> float:
    """Normalized Euclidean distance, with a fixed penalty for a profile change.

    The profile term keeps a same-shape neighbour preferred over a different
    shape at equal geometric distance, which is what state tracking wants: the
    envelope evolves continuously along a shape, and jumps between shapes.
    """

    left, right = normalized_point(a, cfg), normalized_point(b, cfg)
    squared = sum((left[name] - right[name]) ** 2 for name in RANGE_PARAMETERS)
    same_profile = canonicalize(a, cfg)["grading_profile"] == canonicalize(b, cfg)[
        "grading_profile"
    ]
    return math.sqrt(squared + (0.0 if same_profile else 0.25**2))


def nearest_neighbour(
    parameters: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> tuple[int, float] | None:
    """Index of the closest candidate design, and its distance."""

    if not candidates:
        return None
    distances = [design_distance(parameters, other, cfg) for other in candidates]
    best = min(range(len(distances)), key=distances.__getitem__)
    return best, distances[best]


# ---------------------------------------------------------------------------
# search-space description (shared by Ax construction, tables and reports)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RangeSpec:
    name: str
    lower: float
    upper: float

    def as_row(self) -> dict[str, Any]:
        return {
            "parameter": self.name,
            "type": "range",
            "lower": self.lower,
            "upper": self.upper,
            "values": None,
        }


@dataclass(frozen=True)
class ChoiceSpec:
    name: str
    values: tuple[str, ...]

    def as_row(self) -> dict[str, Any]:
        return {
            "parameter": self.name,
            "type": "choice",
            "lower": None,
            "upper": None,
            "values": ";".join(self.values),
        }


def search_space_specs(cfg: Mapping[str, Any]) -> list[RangeSpec | ChoiceSpec]:
    """The active search space, including any enabled optional parameters."""

    space = _search_space(cfg)
    specs: list[RangeSpec | ChoiceSpec] = []
    for name in RANGE_PARAMETERS:
        entry = space.get(name)
        if not isinstance(entry, Mapping):
            raise DesignError(f"bo.search_space.{name} must be a mapping")
        lower, upper = float(entry["lower"]), float(entry["upper"])
        if not upper > lower:
            raise DesignError(f"bo.search_space.{name} needs upper > lower")
        specs.append(RangeSpec(name, lower, upper))
    profiles = (space.get("grading_profile") or {}).get("values")
    if not isinstance(profiles, list) or not profiles:
        raise DesignError("bo.search_space.grading_profile.values must be a non-empty list")
    unknown = sorted(set(map(str, profiles)) - set(GRADING_PROFILES))
    if unknown:
        raise DesignError(f"unsupported grading profiles: {', '.join(unknown)}")
    specs.append(ChoiceSpec("grading_profile", tuple(str(value) for value in profiles)))

    for name, entry in ((cfg.get("bo") or {}).get("optional_parameters") or {}).items():
        if not isinstance(entry, Mapping) or not bool(entry.get("enabled", False)):
            continue
        if name not in OPTIONAL_PARAMETER_TARGETS:
            raise DesignError(f"unknown optional BO parameter {name!r}")
        if str(entry.get("type")) == "choice":
            specs.append(
                ChoiceSpec(name, tuple(str(value) for value in entry.get("values", [])))
            )
        else:
            specs.append(RangeSpec(name, float(entry["lower"]), float(entry["upper"])))
    return specs


def enabled_optional_parameters(cfg: Mapping[str, Any]) -> list[str]:
    return [
        name
        for name, entry in ((cfg.get("bo") or {}).get("optional_parameters") or {}).items()
        if isinstance(entry, Mapping) and bool(entry.get("enabled", False))
    ]


def graded_thickness_bounds(cfg: Mapping[str, Any]) -> tuple[float, float]:
    """Bounds for the *graded* branch of the hierarchical encoding.

    The lower bound is lifted off zero because a zero-thickness graded design is
    an abrupt design, and the hierarchical encoding already has a branch for
    that one.
    """

    space = _search_space(cfg)
    entry = space["grading_thickness_nm"]
    lower = max(
        float(entry["lower"]), float(space.get("minimum_graded_thickness_nm", 0.0))
    )
    upper = float(entry["upper"])
    if not upper > lower:
        raise DesignError(
            "bo.search_space.grading_thickness_nm.upper must exceed "
            "minimum_graded_thickness_nm"
        )
    return lower, upper


def graded_profiles(cfg: Mapping[str, Any]) -> tuple[str, ...]:
    """Profile choices minus ``abrupt``, for the hierarchical graded branch."""

    space = _search_space(cfg)
    values = [str(value) for value in space["grading_profile"]["values"]]
    graded = tuple(value for value in values if value != "abrupt")
    if not graded:
        raise DesignError(
            "the hierarchical encoding needs at least one non-abrupt grading profile"
        )
    return graded


def expected_evaluation_counts(cfg: Mapping[str, Any]) -> dict[str, int]:
    """Section 20's arithmetic, in one place, derived only from the YAML."""

    bo = cfg["bo"]
    initial = int(bo["num_initial_trials"])
    iterations = int(bo["num_iterations"])
    batch = int(bo["batch_size"])
    return {
        "num_initial_trials": initial,
        "num_iterations": iterations,
        "batch_size": batch,
        "expected_maximum_new_solver_runs": initial + iterations * batch,
    }
