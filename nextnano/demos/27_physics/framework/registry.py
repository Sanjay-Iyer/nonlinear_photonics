"""Sub-demo discovery, configuration resolution and prerequisite enforcement.

The registry is the single place that knows what the Demo 27 sub-demos are.
It resolves each one against the frozen Demo 23 baseline, checks that the
sub-demo declares every field it changes, and refuses to hand back a
configuration that would silently drift.
"""

from __future__ import annotations

import copy
import math
import re
import sys
from dataclasses import dataclass, fields as dataclass_fields
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import Demo27Error
from .decks import DeckSpec, Doping

DEMO_DIR = Path(__file__).resolve().parents[1]
DEMOS_DIR = DEMO_DIR.parent
REPO_ROOT = DEMO_DIR.parents[2]
DEMO23_DIR = DEMOS_DIR / "23_k_resolved_dispersion_validation"
PARENT_CONFIG = DEMO_DIR / "demo27_config.yaml"

SUB_DEMO_PATTERN = re.compile(r"^27[A-Z]_")

#: Statuses the campaign may record. Anything else is a bug.
STATUSES = ("NOT RUN", "READY", "RUNNING", "PASS", "FAIL", "BLOCKED", "COMPLETE", "NOT NEEDED")
#: Statuses that satisfy a prerequisite.
SATISFYING = ("PASS", "COMPLETE", "NOT NEEDED")

STAGE_KINDS = ("generate_and_parse", "professional", "delegated", "python", "none", "external")

#: DeckSpec fields that carry no physics and are therefore never a controlled change.
NON_PHYSICS_FIELDS = frozenset({"name", "question", "harvest"})


# ---------------------------------------------------------------------------
# parent configuration and the frozen baseline
# ---------------------------------------------------------------------------

def load_parent_config() -> dict:
    cfg = yaml.safe_load(PARENT_CONFIG.read_text(encoding="utf-8"))
    required = ("demo", "inherit", "policy", "tiers", "harvest", "paths",
                "reuse_sources", "outputs")
    missing = [key for key in required if key not in cfg]
    if missing:
        raise Demo27Error("demo27_config.yaml is missing block(s): %s" % missing)
    return cfg


def load_demo23_config() -> dict:
    """Load Demo 23's configuration through Demo 23's own loader.

    Imported rather than copied so the Brillouin-zone convention, geometry and
    mesh can never drift between the two demos.
    """
    if str(DEMO23_DIR) not in sys.path:
        sys.path.insert(0, str(DEMO23_DIR))
    import config23  # noqa: PLC0415

    return config23.load_config()


def k_bz_per_nm(cfg23: Mapping) -> float:
    if str(DEMO23_DIR) not in sys.path:
        sys.path.insert(0, str(DEMO23_DIR))
    import config23  # noqa: PLC0415

    return float(config23.k_bz_per_nm(cfg23))


#: How a "fraction of the Brillouin zone" may be read. Demo 27G exists because
#: the paper does not say which of these it means.
BZ_CONVENTIONS = {
    "pi_over_a": (1.0, "k_BZ = pi/a (the Demo 20-23 legacy convention)"),
    "gamma_x": (2.0, "k_BZ = |Gamma-X| = 2pi/a for zincblende along [010]"),
    "reciprocal_lattice_vector": (2.0, "k_BZ = |G| = 2pi/a"),
}


def kmax_per_nm(cfg23: Mapping, fraction: float, convention: str = "pi_over_a") -> float:
    if convention not in BZ_CONVENTIONS:
        raise Demo27Error("unknown BZ convention %r; known: %s"
                          % (convention, sorted(BZ_CONVENTIONS)))
    multiplier = BZ_CONVENTIONS[convention][0]
    return float(fraction) * multiplier * k_bz_per_nm(cfg23)


def baseline_spec(parent: Mapping, cfg23: Mapping) -> DeckSpec:
    """The Demo 23 production deck expressed as a :class:`DeckSpec`.

    Every sub-demo deck is built by applying its declared overrides to this,
    which is what makes "one controlled change" mechanically checkable.
    """
    geometry, materials, mesh = cfg23["geometry"], cfg23["materials"], cfg23["mesh"]
    kp8, integration = cfg23["kp8"], cfg23["integration"]
    interface = str(geometry["interface_model"])
    if interface not in ("linear_1nm", "abrupt"):
        raise Demo27Error("Demo 23 interface_model %r is not understood" % interface)
    direction_name = str(kp8["production_direction"])
    direction = tuple(float(v) for v in kp8["directions"][direction_name])
    fraction = float(integration["fraction_of_bz"])
    return DeckSpec(
        name="baseline_demo23",
        question="frozen Demo 23 baseline; not a Demo 27 question",
        thick_well_nm=float(geometry["thick_well_nm"]),
        tunnel_barrier_nm=float(geometry["tunnel_barrier_nm"]),
        thin_well_nm=float(geometry["thin_well_nm"]),
        period_barrier_nm=float(geometry["period_barrier_nm"]),
        interface_model="linear_graded" if interface == "linear_1nm" else "abrupt",
        grade_width_nm=float(geometry["grade_width_nm"]),
        quantum_region_padding_nm=float(geometry["quantum_region_padding_nm"]),
        barrier_al_fraction=float(materials["barrier_al_fraction"]),
        well_al_fraction=float(materials["well_al_fraction"]),
        temperature_K=float(materials["temperature_K"]),
        active_spacing_nm=float(mesh["active_spacing_nm"]),
        outer_spacing_nm=float(mesh["outer_spacing_nm"]),
        band_model="kp8",
        num_electrons=int(kp8["number_of_electron_states"]),
        num_holes=int(kp8["number_of_hole_states"]),
        output_state_count=int(kp8["output_state_count"]),
        k_mode="dispersion",
        k_points=int(integration["production_points"]),
        kmax_per_nm=kmax_per_nm(cfg23, fraction),
        relative_size=fraction,
        direction_name=direction_name,
        direction=direction,
        harvest=dict(parent["harvest"]),
    )


# ---------------------------------------------------------------------------
# sub-demos
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubDemo:
    demo_id: str
    slug: str
    directory: Path
    title: str
    question: str
    tier: int
    priority: int | None
    professional_required: bool
    prerequisites: tuple
    unlocks: tuple
    pass_condition: str
    cost: dict
    stages: dict
    delegate: dict
    controlled_change: dict
    raw: dict

    @property
    def outputs_dir(self) -> Path:
        return self.directory / "outputs"

    @property
    def inputs_dir(self) -> Path:
        return self.directory / "inputs"

    def stage_kind(self, stage: str) -> str:
        block = self.stages.get(stage) or {}
        return str(block.get("kind", "none"))

    def runtime_range(self) -> tuple:
        low, high = (self.cost.get("runtime_hours") or [None, None])[:2]
        return low, high

    def runtime_text(self) -> str:
        low, high = self.runtime_range()
        if low is None or high is None:
            return str(self.cost.get("runtime_note", "unestimated"))
        return "%s - %s" % (_hours(low), _hours(high))


def _hours(value: float) -> str:
    value = float(value)
    if value < 1.0 / 60.0:
        return "seconds"
    if value < 1.0:
        return "%d min" % round(value * 60)
    if value < 48.0:
        return "%.3g h" % value
    return "%.2g days" % (value / 24.0)


def discover(parent: Mapping | None = None) -> tuple:
    """Load every sub-demo config, in id order."""
    parent = parent or load_parent_config()
    subs = []
    for directory in sorted(DEMO_DIR.iterdir()):
        if not directory.is_dir() or not SUB_DEMO_PATTERN.match(directory.name):
            continue
        config_path = directory / "config.yaml"
        if not config_path.is_file():
            raise Demo27Error("sub-demo directory %s has no config.yaml" % directory.name)
        subs.append(_load_sub_demo(config_path, directory))
    if not subs:
        raise Demo27Error("no Demo 27 sub-demos found under %s" % DEMO_DIR)
    _validate_graph(subs)
    return tuple(subs)


def _load_sub_demo(config_path: Path, directory: Path) -> SubDemo:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for key in ("demo", "pass_condition", "cost", "stages", "controlled_change"):
        if key not in cfg:
            raise Demo27Error("%s is missing the %r block" % (config_path, key))
    block = cfg["demo"]
    demo_id = str(block["id"])
    if not directory.name.startswith(demo_id + "_"):
        raise Demo27Error("sub-demo id %r does not match directory %r"
                          % (demo_id, directory.name))
    tier = int(block["tier"])
    if tier not in range(0, 6):
        raise Demo27Error("%s: tier %d is outside 0-5" % (demo_id, tier))
    for stage in ("preflight", "physics", "analyze"):
        kind = str((cfg["stages"].get(stage) or {}).get("kind", "none"))
        if kind not in STAGE_KINDS:
            raise Demo27Error("%s: stage %s kind %r is not one of %s"
                              % (demo_id, stage, kind, STAGE_KINDS))
    return SubDemo(
        demo_id=demo_id,
        slug=str(block["slug"]),
        directory=directory,
        title=str(block["title"]),
        question=str(block["question"]),
        tier=tier,
        priority=(None if block.get("priority") is None else int(block["priority"])),
        professional_required=bool(block.get("professional_required", False)),
        prerequisites=tuple(str(p) for p in (block.get("prerequisites") or [])),
        unlocks=tuple(str(p) for p in (block.get("unlocks") or [])),
        pass_condition=str(cfg["pass_condition"]),
        cost=dict(cfg["cost"]),
        stages=dict(cfg["stages"]),
        delegate=dict(cfg.get("delegate") or {}),
        controlled_change=dict(cfg["controlled_change"]),
        raw=cfg,
    )


def _validate_graph(subs) -> None:
    known = {sub.demo_id for sub in subs}
    for sub in subs:
        for prerequisite in sub.prerequisites:
            if prerequisite not in known:
                raise Demo27Error("%s lists unknown prerequisite %r"
                                  % (sub.demo_id, prerequisite))
        for unlocked in sub.unlocks:
            if unlocked not in known:
                raise Demo27Error("%s claims to unlock unknown sub-demo %r"
                                  % (sub.demo_id, unlocked))
    # A cycle would make the campaign unrunnable; detect it now rather than at
    # the moment somebody tries to run a sub-demo.
    graph = {sub.demo_id: set(sub.prerequisites) for sub in subs}
    resolved: set = set()
    while True:
        ready = {name for name, needs in graph.items() if needs <= resolved}
        if ready <= resolved:
            break
        resolved |= ready
    unresolved = set(graph) - resolved
    if unresolved:
        raise Demo27Error("the Demo 27 prerequisite graph has a cycle involving %s"
                          % sorted(unresolved))


def find(demo_id: str, subs=None) -> SubDemo:
    subs = subs or discover()
    wanted = str(demo_id).strip().upper()
    if not wanted.startswith("27"):
        wanted = "27" + wanted
    for sub in subs:
        if sub.demo_id.upper() == wanted:
            return sub
    raise Demo27Error("unknown sub-demo %r; known: %s"
                      % (demo_id, ", ".join(s.demo_id for s in subs)))


# ---------------------------------------------------------------------------
# resolved configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResolvedDeck:
    spec: DeckSpec
    changes: dict            # field -> (baseline value, this deck's value)
    question: str


@dataclass(frozen=True)
class Resolved:
    sub: SubDemo
    parent: dict
    cfg23: dict
    baseline: DeckSpec
    decks: tuple

    @property
    def results_root(self) -> Path:
        path = Path(str(self.parent["paths"]["results_root"]))
        root = path if path.is_absolute() else REPO_ROOT / path
        return root / self.sub.demo_id


_SPEC_FIELDS = {f.name for f in dataclass_fields(DeckSpec)}


def _coerce(field_name: str, value: Any, cfg23: Mapping) -> Any:
    """Turn a YAML override into the type DeckSpec expects."""
    if field_name == "direction":
        return tuple(float(v) for v in value)
    if field_name == "doping":
        return tuple(Doping(**dict(entry)) for entry in (value or []))
    if field_name == "harvest":
        return dict(value or {})
    return value


def resolve(sub: SubDemo, parent: Mapping | None = None,
            cfg23: Mapping | None = None) -> Resolved:
    """Build every deck for one sub-demo and record its controlled changes.

    Raises if a deck changes a physics field the sub-demo did not declare in
    ``controlled_change.fields``. That is the mechanical form of the campaign
    rule: ONE QUESTION, ONE CONTROLLED CHANGE.
    """
    parent = dict(parent or load_parent_config())
    cfg23 = dict(cfg23 or load_demo23_config())
    baseline = baseline_spec(parent, cfg23)
    declared = set(sub.controlled_change.get("fields") or [])
    unknown = declared - _SPEC_FIELDS
    if unknown:
        raise Demo27Error("%s declares controlled changes to unknown deck fields: %s"
                          % (sub.demo_id, sorted(unknown)))

    resolved_decks = []
    for entry in (sub.raw.get("decks") or []):
        overrides = dict(entry.get("overrides") or {})
        # A sub-demo may express kmax as a BZ fraction plus a convention rather
        # than as a raw number, so the zone definition stays explicit.
        if "fraction_of_bz" in overrides:
            fraction = float(overrides.pop("fraction_of_bz"))
            convention = str(overrides.pop("bz_convention", "pi_over_a"))
            overrides["relative_size"] = fraction
            overrides["kmax_per_nm"] = kmax_per_nm(cfg23, fraction, convention)
        bad = set(overrides) - _SPEC_FIELDS
        if bad:
            raise Demo27Error("%s deck %r overrides unknown deck fields: %s"
                              % (sub.demo_id, entry.get("name"), sorted(bad)))
        harvest = dict(parent["harvest"])
        harvest.update(dict(sub.raw.get("harvest_overrides") or {}))
        harvest.update(dict(overrides.pop("harvest", {}) or {}))
        prepared = {key: _coerce(key, value, cfg23) for key, value in overrides.items()}
        spec = baseline.with_changes(
            name=str(entry["name"]),
            question=str(entry.get("question", sub.question)),
            harvest=harvest,
            **prepared)
        changes = _changed_fields(baseline, spec)
        undeclared = sorted(set(changes) - declared)
        if undeclared:
            raise Demo27Error(
                "%s deck %r changes %s but %s only declares %s as its controlled "
                "change. Add the field to controlled_change.fields with a physical "
                "justification, or remove the override."
                % (sub.demo_id, spec.name, undeclared, sub.demo_id, sorted(declared)))
        # A sub-demo may own several knobs, but ONE DECK must isolate ONE change,
        # otherwise a difference in the result cannot be attributed. Fields that
        # are physically inseparable (raising output_state_count needs more solved
        # states; widening kmax at fixed spacing needs more k points) are what the
        # per-sub-demo limit above one exists for.
        limit = sub.controlled_change.get("max_fields_per_deck")
        if limit is not None and len(changes) > int(limit):
            raise Demo27Error(
                "%s deck %r changes %d fields (%s) but %s allows at most %d per deck. "
                "Split it into separate decks so the result is attributable."
                % (sub.demo_id, spec.name, len(changes), sorted(changes),
                   sub.demo_id, int(limit)))
        resolved_decks.append(ResolvedDeck(spec=spec, changes=changes, question=spec.question))
    return Resolved(sub=sub, parent=parent, cfg23=cfg23, baseline=baseline,
                    decks=tuple(resolved_decks))


def _changed_fields(baseline: DeckSpec, spec: DeckSpec) -> dict:
    changes = {}
    for entry in dataclass_fields(DeckSpec):
        if entry.name in NON_PHYSICS_FIELDS:
            continue
        before = getattr(baseline, entry.name)
        after = getattr(spec, entry.name)
        if isinstance(before, float) and isinstance(after, float):
            if math.isclose(before, after, rel_tol=1e-12, abs_tol=1e-12):
                continue
        elif before == after:
            continue
        changes[entry.name] = (before, after)
    return changes


# ---------------------------------------------------------------------------
# prerequisites
# ---------------------------------------------------------------------------

def blocking_prerequisites(sub: SubDemo, statuses: Mapping) -> list:
    """Prerequisites that are not yet satisfied, as ``(id, status)`` pairs."""
    blocking = []
    for prerequisite in sub.prerequisites:
        status = str(statuses.get(prerequisite, "NOT RUN"))
        if status not in SATISFYING:
            blocking.append((prerequisite, status))
    return blocking


def derived_status(sub: SubDemo, statuses: Mapping) -> str:
    """The status to display: recorded status, or BLOCKED if a prerequisite is not met."""
    recorded = str(statuses.get(sub.demo_id, "NOT RUN"))
    if recorded in ("NOT RUN", "READY") and blocking_prerequisites(sub, statuses):
        return "BLOCKED"
    return recorded
