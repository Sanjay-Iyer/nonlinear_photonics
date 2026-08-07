"""Demo 17 reference structures and the controlled-variant machinery.

Demo 17 is not a sweep. It runs a handful of structures and then asks what
happens when exactly one thing about them changes. That makes the *variant*, not
the structure, the unit of scientific work, and it puts the burden of proof on
the claim "only X changed".

So a :class:`Variant` does not merely carry an overlay -- it declares which
configuration keys it is allowed to touch, and :func:`resolve_variant` refuses to
build one whose actual effect differs from its declaration. A variant that
silently perturbs the mesh while claiming to change the temperature cannot be
constructed, rather than being caught later by a reviewer noticing an odd number.

The five reference structures are lifted from Demo 16's frozen case table by
name. Demo 17 never invents a geometry: if a structure is worth validating it is
already a Demo 16 regression case, and if it is not in that table then a Demo 17
pass would be protecting something no other demo tests.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

import cases16
import demo14
import grading14

DEMO_ID = "17_acqw_physics_numerical_validation"
DEMO_DIR = Path(__file__).resolve().parent
DEMO17_VERSION = "demo17-1.0.0"

#: Demo 16's frozen case file. Demo 17 reads it; it never writes it.
CASES_PATH = (
    DEMO_DIR.parent / "16_acqw_renderer_stress_validation" / cases16.CASES_FILENAME
)

#: Reference structures, by the Demo 16 case *name* they are drawn from.
#: Names, not indices: reordering Demo 16's table must not silently repoint a
#: Demo 17 reference at a different structure.
REFERENCE_SOURCES: Mapping[str, dict[str, str]] = {
    "REF01": {
        "case_name": "paper_reference",
        "role": "paper_like_acqw",
        "purpose": "7.1 / 1.8 / 2.9 nm, Al 0.55, 1.0 nm linear grades. The "
                   "primary Demo 17 reference and the only structure with an "
                   "external literature comparison.",
    },
    "REF02": {
        "case_name": "maximum_overlap_linear",
        "role": "thin_barrier_overlap_linear",
        "purpose": "0.85 nm barrier with 1.40 nm grades. The grades genuinely "
                   "overlap, the barrier never reaches nominal composition, and "
                   "the native linear renderer cannot represent it.",
    },
    "REF03": {
        "case_name": "seeded_interior_01_fermi",
        "role": "nonlinear_fermi",
        "purpose": "Interior Fermi-graded structure; a non-compact-support "
                   "family rendered through an imported table.",
    },
    "REF04": {
        "case_name": "seeded_interior_02_erf",
        "role": "nonlinear_erf",
        "purpose": "Second nonlinear family, so a grading-width conclusion "
                   "cannot rest on one shape.",
    },
    "REF05": {
        "case_name": "high_asymmetry_boundary",
        "role": "strongly_asymmetric",
        "purpose": "s = 0.55, the top of the Demo 14 range: 7.75 / 2.25 nm "
                   "wells. The most asymmetric structure the campaign can "
                   "propose, and the sharpest test of a left/right indexing "
                   "error.",
    },
}

#: Production mesh under test. Demo 17 reports on it; it never changes it.
PRODUCTION_MESH_NM = 0.05

#: Mesh spacings for the convergence study, coarse -> fine.
MESH_LADDER_NM: tuple[float, ...] = (0.10, 0.05, 0.025)

#: (domain padding, quantum-region padding) in nm, small -> large.
#: The *quantum* padding is the scientifically decisive one: the Dirichlet wall
#: in ``quantum{ region{ boundary{ x = dirichlet } } }`` is the artificial
#: boundary this experiment exists to rule out. Domain padding grows with it so
#: the wall always sits deep inside AlGaAs rather than near vacuum.
DOMAIN_LADDER_NM: tuple[tuple[float, float], ...] = ((10.0, 1.0), (20.0, 2.0), (40.0, 4.0))

#: Temperatures, K. 300 K is the Demo 14 production value.
TEMPERATURE_LADDER_K: tuple[float, ...] = (77.0, 300.0)

#: Electric fields, kV/cm. Sign convention is measured, not assumed -- see
#: ``solve17.FIELD_SIGN_CONVENTION``.
FIELD_LADDER_KV_CM: tuple[float, ...] = (-50.0, 0.0, +50.0)

#: Broadenings, meV, for the analysis-only isolation test.
BROADENING_LADDER_MEV: tuple[float, ...] = (2.0, 5.0, 10.0)


class Refs17Error(RuntimeError):
    """A malformed reference or variant, as distinct from a failing experiment."""


# ---------------------------------------------------------------------------
# Reference structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferenceStructure:
    """One Demo 16 case promoted to a Demo 17 reference."""

    ref_id: str
    role: str
    purpose: str
    case: cases16.ValidationCase

    @property
    def name(self) -> str:
        return f"{self.ref_id}_{self.role}"

    def parameters(self) -> dict[str, Any]:
        return self.case.parameters()

    def well_widths_nm(self) -> tuple[float, float]:
        return self.case.well_widths_nm()

    def as_record(self) -> dict[str, Any]:
        thick, thin = self.well_widths_nm()
        return {
            "ref_id": self.ref_id,
            "role": self.role,
            "purpose": self.purpose,
            "demo16_case_id": self.case.case_id,
            "demo16_case_name": self.case.name,
            "parameters": self.parameters(),
            "derived_thick_well_nm": thick,
            "derived_thin_well_nm": thin,
        }


def load_references(path: Path | None = None) -> list[ReferenceStructure]:
    """The five references, resolved from Demo 16's frozen table."""

    cases = {c.name: c for c in cases16.load_cases(Path(path or CASES_PATH))}
    refs: list[ReferenceStructure] = []
    for ref_id, spec in REFERENCE_SOURCES.items():
        case_name = spec["case_name"]
        if case_name not in cases:
            raise Refs17Error(
                f"{ref_id} names Demo 16 case {case_name!r}, which is not in "
                f"{Path(path or CASES_PATH).name}. Demo 17 must not invent a "
                "structure to replace it."
            )
        refs.append(ReferenceStructure(
            ref_id=ref_id, role=spec["role"], purpose=spec["purpose"],
            case=cases[case_name],
        ))
    return refs


def reference(ref_id: str, path: Path | None = None) -> ReferenceStructure:
    for ref in load_references(path):
        if ref.ref_id == ref_id:
            return ref
    raise Refs17Error(f"unknown reference {ref_id!r}")


# ---------------------------------------------------------------------------
# Controlled variants
# ---------------------------------------------------------------------------


def _flatten(mapping: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """``{'mesh': {'a': 1}}`` -> ``{'mesh.a': 1}``, for exact diffing."""

    out: dict[str, Any] = {}
    for key, value in mapping.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            out.update(_flatten(value, prefix=f"{path}."))
        else:
            out[path] = value
    return out


def config_diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Every leaf key whose value differs, with both values."""

    flat_a, flat_b = _flatten(before), _flatten(after)
    changed: dict[str, Any] = {}
    for key in sorted(set(flat_a) | set(flat_b)):
        a, b = flat_a.get(key, "<absent>"), flat_b.get(key, "<absent>")
        if isinstance(a, float) and isinstance(b, float):
            if a == b or (np.isnan(a) and np.isnan(b)):
                continue
        elif a == b:
            continue
        changed[key] = {"before": a, "after": b}
    return changed


def _set_path(target: dict[str, Any], dotted: str, value: Any) -> None:
    node = target
    parts = dotted.split(".")
    for part in parts[:-1]:
        if part not in node or not isinstance(node[part], dict):
            raise Refs17Error(f"config has no mapping at {dotted!r}")
        node = node[part]
    if parts[-1] not in node:
        raise Refs17Error(
            f"config has no key {dotted!r}; a variant may only change settings "
            "that already exist, so a typo cannot invent a silently-ignored one"
        )
    node[parts[-1]] = value


@dataclass(frozen=True)
class Variant:
    """One controlled change to a reference structure.

    ``config_overlay`` changes the resolved Demo 14 configuration;
    ``parameter_overlay`` changes the structure parameters. ``declared_changes``
    is the contract: exactly these dotted keys may differ, and
    :func:`resolve_variant` enforces it.
    """

    variant_id: str
    ref_id: str
    experiment: str
    #: What this variant is testing, in one sentence.
    hypothesis: str
    config_overlay: Mapping[str, Any] = field(default_factory=dict)
    parameter_overlay: Mapping[str, Any] = field(default_factory=dict)
    declared_changes: tuple[str, ...] = ()
    #: Extra rendering instructions consumed by ``solve17``, e.g. the field.
    render_options: Mapping[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "ref_id": self.ref_id,
            "experiment": self.experiment,
            "hypothesis": self.hypothesis,
            "config_overlay": dict(self.config_overlay),
            "parameter_overlay": dict(self.parameter_overlay),
            "declared_changes": list(self.declared_changes),
            "render_options": dict(self.render_options),
        }


@dataclass(frozen=True)
class ResolvedVariant:
    """A variant with its config, geometry, profile and rendering realized."""

    variant: Variant
    ref: ReferenceStructure
    cfg: Mapping[str, Any]
    parameters: Mapping[str, Any]
    geometry: demo14.Geometry
    profile: grading14.CompositionProfile
    blocks: Mapping[str, Any]
    deck: str
    #: Actual config keys that differ from the baseline, for the record.
    observed_config_changes: Mapping[str, Any] = field(default_factory=dict)
    observed_parameter_changes: Mapping[str, Any] = field(default_factory=dict)

    @property
    def render_method(self) -> str:
        return (
            "ternary_import"
            if "ternary_import" in self.blocks["structure_block"]
            else "ternary_linear"
        )

    def as_record(self) -> dict[str, Any]:
        return {
            **self.variant.as_record(),
            "render_method": self.render_method,
            "observed_config_changes": dict(self.observed_config_changes),
            "observed_parameter_changes": dict(self.observed_parameter_changes),
            "geometry": self.geometry.as_record(),
            "grading_diagnostics": dict(self.profile.diagnostics),
            "mesh_nm": float(self.cfg["mesh"]["active_region_grid_spacing_nm"]),
            "temperature_K": float(self.cfg["materials"]["temperature_K"]),
            "domain_padding_nm": float(self.cfg["geometry"]["domain_padding_nm"]),
            "quantum_region_padding_nm": float(
                self.cfg["geometry"]["quantum_region_padding_nm"]
            ),
        }


def baseline_variant(ref: ReferenceStructure, experiment: str = "baseline") -> Variant:
    return Variant(
        variant_id=f"{ref.ref_id}_baseline",
        ref_id=ref.ref_id,
        experiment=experiment,
        hypothesis="Production settings, unchanged. The control for every other "
                   "variant of this reference.",
    )


def resolve_variant(
    base_cfg: Mapping[str, Any],
    variant: Variant,
    *,
    references: Sequence[ReferenceStructure] | None = None,
    render_options_are_deck_level: bool = True,
) -> ResolvedVariant:
    """Apply a variant and prove it changed exactly what it said it would.

    The check runs against the *resolved* configuration, so a declaration that
    happens to be a no-op (setting the mesh to the value it already had) fails
    just as loudly as one that changes something undeclared. Both are bugs in an
    experiment that claims to isolate a single cause.
    """

    refs = list(references) if references is not None else load_references()
    ref = next((r for r in refs if r.ref_id == variant.ref_id), None)
    if ref is None:
        raise Refs17Error(f"variant {variant.variant_id} names unknown reference "
                          f"{variant.ref_id!r}")

    cfg = copy.deepcopy(dict(base_cfg))
    for dotted, value in variant.config_overlay.items():
        _set_path(cfg, dotted, value)

    parameters = dict(ref.parameters())
    parameter_changes: dict[str, Any] = {}
    for key, value in variant.parameter_overlay.items():
        if key not in parameters:
            raise Refs17Error(
                f"{variant.variant_id}: parameter {key!r} is not part of the Demo "
                "14 parameterization"
            )
        if parameters[key] != value:
            parameter_changes[key] = {"before": parameters[key], "after": value}
        parameters[key] = value

    observed = config_diff(base_cfg, cfg)
    declared = set(variant.declared_changes)
    actual = set(observed) | {f"parameters.{k}" for k in parameter_changes}
    if actual != declared:
        undeclared = sorted(actual - declared)
        unrealized = sorted(declared - actual)
        raise Refs17Error(
            f"{variant.variant_id} declared changes {sorted(declared)} but "
            f"actually changed {sorted(actual)}"
            + (f"; undeclared: {undeclared}" if undeclared else "")
            + (f"; declared but had no effect: {unrealized}" if unrealized else "")
        )

    geometry = demo14.geometry_for(cfg, parameters)
    profile = demo14.build_grading(cfg, parameters, geometry)
    render = str(variant.render_options.get("render_method", "auto"))
    if render == "imported":
        blocks = grading14.render_imported_blocks(
            profile,
            reason="Demo 17 native-vs-imported equivalence: the imported "
                   "rendering of a profile the native renderer can also express",
        )
    elif render == "auto":
        blocks = grading14.render_structure_blocks(profile)
    else:
        raise Refs17Error(f"unknown render_method {render!r}")
    deck = demo14.render_deck(cfg, geometry, profile, blocks)

    return ResolvedVariant(
        variant=variant, ref=ref, cfg=cfg, parameters=parameters,
        geometry=geometry, profile=profile, blocks=blocks, deck=deck,
        observed_config_changes=observed,
        observed_parameter_changes=parameter_changes,
    )


# ---------------------------------------------------------------------------
# Variant families
# ---------------------------------------------------------------------------


def mesh_variants(ref: ReferenceStructure) -> list[Variant]:
    """The mesh ladder. Nothing but the grid spacing moves."""

    key = "mesh.active_region_grid_spacing_nm"
    out = []
    for mesh in MESH_LADDER_NM:
        declared = () if mesh == PRODUCTION_MESH_NM else (key,)
        out.append(Variant(
            variant_id=f"{ref.ref_id}_mesh_{mesh:g}".replace(".", "p"),
            ref_id=ref.ref_id,
            experiment="mesh_convergence",
            hypothesis=(
                f"At {mesh:g} nm the discretization changes; the converged "
                "physical answer must not."
            ),
            config_overlay={key: float(mesh)},
            declared_changes=declared,
        ))
    return out


def domain_variants(ref: ReferenceStructure) -> list[Variant]:
    """The outer-domain ladder.

    Two keys move together and both describe the environment *outside* the
    active ACQW: the simulation domain and the quantum region's Dirichlet walls.
    Growing the domain while leaving the walls where they are would test nothing,
    because the walls are the artificial boundary in question.
    """

    domain_key = "geometry.domain_padding_nm"
    quantum_key = "geometry.quantum_region_padding_nm"
    out = []
    for domain_nm, quantum_nm in DOMAIN_LADDER_NM:
        declared = tuple(
            k for k, v, base in (
                (domain_key, domain_nm, 20.0), (quantum_key, quantum_nm, 2.0)
            ) if v != base
        )
        out.append(Variant(
            variant_id=f"{ref.ref_id}_domain_{domain_nm:g}_{quantum_nm:g}".replace(".", "p"),
            ref_id=ref.ref_id,
            experiment="domain_convergence",
            hypothesis=(
                f"With {domain_nm:g} nm of outer AlGaAs and Dirichlet walls "
                f"{quantum_nm:g} nm beyond the active region, a state bound by "
                "the heterostructure must not care where the walls are."
            ),
            config_overlay={domain_key: float(domain_nm), quantum_key: float(quantum_nm)},
            declared_changes=declared,
        ))
    return out


def temperature_variants(ref: ReferenceStructure) -> list[Variant]:
    key = "materials.temperature_K"
    out = []
    for temperature in TEMPERATURE_LADDER_K:
        declared = () if temperature == 300.0 else (key,)
        out.append(Variant(
            variant_id=f"{ref.ref_id}_T{temperature:g}K",
            ref_id=ref.ref_id,
            experiment="temperature",
            hypothesis=(
                f"At {temperature:g} K geometry and composition are untouched; "
                "band parameters and therefore state energies may move."
            ),
            config_overlay={key: float(temperature)},
            declared_changes=declared,
        ))
    return out


def field_variants(ref: ReferenceStructure) -> list[Variant]:
    """Electric field, applied as a deck transform rather than a config key.

    The field is deliberately *not* a Demo 14 configuration setting: Demo 14's
    production model has no field, and adding one to its config would change what
    the production campaign computes. It is a Demo 17 render option, and the
    resulting decks are classified as an independent capability demonstration.
    """

    out = []
    for field_kV_cm in FIELD_LADDER_KV_CM:
        sign = "m" if field_kV_cm < 0 else ("p" if field_kV_cm > 0 else "0")
        out.append(Variant(
            variant_id=f"{ref.ref_id}_field_{sign}{abs(field_kV_cm):g}",
            ref_id=ref.ref_id,
            experiment="electric_field",
            hypothesis=(
                f"At {field_kV_cm:+g} kV/cm the composition and geometry are "
                "identical; the potential tilts and the states respond."
            ),
            render_options={"electric_field_kV_cm": float(field_kV_cm)},
        ))
    return out


def mirror_parameters(ref: ReferenceStructure) -> dict[str, Any]:
    """Parameters whose profile is the exact spatial mirror of ``ref``'s.

    Under ``z -> L - z`` the layer order reverses, so the thick and thin wells
    swap; and every interface where Al *rose* with z now *falls*, so the two
    grading widths swap with them.

    The well swap cannot be expressed by negating ``asymmetry_s`` -- Demo 14
    bounds it to [0.30, 0.55] and a negative value is outside the parameterized
    space. The mirror is therefore built at the profile level, by handing
    ``build_structure_profile`` the swapped widths directly. That is the same
    production function, called with mirrored arguments; it is not a second
    implementation of the geometry.
    """

    params = dict(ref.parameters())
    thick, thin = ref.well_widths_nm()
    return {
        "profile": params["grading_profile"],
        "thick_well_nm": thin,       # swapped
        "thin_well_nm": thick,       # swapped
        "barrier_thickness_nm": params["nominal_central_barrier_thickness_nm"],
        # An interface that rose with z now falls, and vice versa.
        "gaas_to_algaas_width_10_90_nm": params[
            "algaas_to_gaas_grading_width_10_90_nm"],
        "algaas_to_gaas_width_10_90_nm": params[
            "gaas_to_algaas_grading_width_10_90_nm"],
    }


def build_mirrored_profile(
    cfg: Mapping[str, Any], ref: ReferenceStructure
) -> tuple[grading14.CompositionProfile, demo14.Geometry]:
    """The mirrored structure's authoritative profile, on the same domain."""

    geometry = demo14.geometry_for(cfg, ref.parameters())
    mirror = mirror_parameters(ref)
    profile = grading14.build_structure_profile(
        profile=mirror["profile"],
        thick_well_nm=mirror["thick_well_nm"],
        thin_well_nm=mirror["thin_well_nm"],
        barrier_thickness_nm=mirror["barrier_thickness_nm"],
        gaas_to_algaas_width_10_90_nm=mirror["gaas_to_algaas_width_10_90_nm"],
        algaas_to_gaas_width_10_90_nm=mirror["algaas_to_gaas_width_10_90_nm"],
        active_start_nm=geometry.active_start_nm,
        domain_nm=geometry.domain_nm,
        mesh_nm=float(cfg["mesh"]["active_region_grid_spacing_nm"]),
        max_al_fraction=float(cfg["materials"]["barrier_al_fraction"]),
        continuous_oversample=int(cfg["grading"].get("continuous_oversample", 20)),
    )
    return profile, geometry


def mirror_coordinate(x_nm: np.ndarray, domain_nm: Sequence[float]) -> np.ndarray:
    """``z -> (lo + hi) - z``, the reflection this demo means by "mirror"."""

    lo, hi = float(domain_nm[0]), float(domain_nm[1])
    return (lo + hi) - np.asarray(x_nm, dtype=float)


# ---------------------------------------------------------------------------
# Frozen reference table
# ---------------------------------------------------------------------------


def write_reference_file(path: Path, cfg: Mapping[str, Any] | None = None) -> Path:
    """Freeze the resolved reference table with explicit numbers."""

    import yaml

    cfg = cfg or demo14.load_config()
    refs = load_references()
    payload = {
        "demo17_version": DEMO17_VERSION,
        "source_case_file": str(CASES_PATH.name),
        "production_mesh_nm": PRODUCTION_MESH_NM,
        "ladders": {
            "mesh_nm": list(MESH_LADDER_NM),
            "domain_padding_and_quantum_padding_nm": [list(p) for p in DOMAIN_LADDER_NM],
            "temperature_K": list(TEMPERATURE_LADDER_K),
            "electric_field_kV_cm": list(FIELD_LADDER_KV_CM),
            "broadening_meV": list(BROADENING_LADDER_MEV),
        },
        "references": [],
    }
    for ref in refs:
        record = ref.as_record()
        geometry = demo14.geometry_for(cfg, ref.parameters())
        profile = demo14.build_grading(cfg, ref.parameters(), geometry)
        record["geometry"] = geometry.as_record()
        record["interfaces_nm"] = dict(profile.request["interfaces_nm"])
        record["render_method"] = (
            "ternary_import"
            if "ternary_import" in grading14.render_structure_blocks(
                profile)["structure_block"]
            else "ternary_linear"
        )
        # The CENTRAL barrier peak, from measure_structure. profile.peak_al_fraction
        # is the global maximum, which is the outer barrier at nominal composition
        # for every structure and therefore says nothing about the barrier.
        record["realized_central_peak_al_fraction"] = float(
            profile.diagnostics["realized_peak_al_fraction"])
        record["global_max_al_fraction"] = float(profile.peak_al_fraction)
        record["grades_overlap"] = bool(
            profile.diagnostics["grading_interfaces_overlap"])
        record["mirror_parameters"] = mirror_parameters(ref)
        payload["references"].append(record)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8", newline="\n",
    )
    return path


def expected_licensed_solves(modes: Iterable[str]) -> dict[str, int]:
    """How many licensed nextnano++ calls each mode will make.

    Printed before any physics mode starts. Deck-level caching means the true
    number is at most this; it is never more.
    """

    counts = {
        "native_import_equivalence": 4,   # 2 structures x {native, imported}
        "overlap_physics": 1,             # REF02, imported
        "core_physics": 5,                # REF01..REF05 baselines
        "mesh_convergence": 9,            # 3 structures x 3 meshes
        "domain_convergence": 3,          # REF01 x 3 domains
        "mirror_invariance": 2,           # original + mirrored
        "electric_field": 3,              # -50 / 0 / +50 kV/cm
        "temperature": 2,                 # 77 K / 300 K
        "broadening": 0,                  # analysis-only, reuses a solve
        "energy_wavelength": 0,           # analysis-only
        "grading_width_definition": 0,    # solver-free
        "interface_accuracy": 0,          # needs a solve, reuses core_physics
        "mesh_snapping": 0,               # solver-free
    }
    return {mode: counts.get(mode, 0) for mode in modes}
