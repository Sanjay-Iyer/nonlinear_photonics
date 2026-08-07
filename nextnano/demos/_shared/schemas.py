"""Per-demo strict YAML schemas.

Each demo declares exactly which keys its ``demo.yaml`` may contain and how each
value is constrained.  Unknown keys are an error rather than a silent no-op:
a typo in ``aluminium_fraction`` must not leave the run using a default.

Demos 1-3 keep precisely the key sets and rules they were validated with; the
schema for them is a faithful transcription, not a generalisation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

BASE_TOP_LEVEL: frozenset[str] = frozenset(
    {"demo_id", "title", "template", "scientific", "numerical", "outputs", "validation", "sweeps"}
)
EXTENDED_TOP_LEVEL: frozenset[str] = BASE_TOP_LEVEL | frozenset(
    {"models", "analysis", "parser", "metric", "checks"}
)

BASE_VALIDATION: frozenset[str] = frozenset(
    {
        "completion_markers",
        "fatal_markers",
        "minimum_well_probability",
        "maximum_boundary_probability",
        "normalization_tolerance",
        "absolute_energy_tolerance_meV",
        "relative_energy_tolerance",
    }
)
EXTENDED_VALIDATION: frozenset[str] = BASE_VALIDATION | frozenset(
    {
        "convergence_warning_markers",
        "minimum_confined_probability",
        "minimum_state_tracking_confidence",
        "maximum_charge_imbalance",
        "maximum_symmetry_error",
        "maximum_matrix_element_disagreement_nm",
        "minimum_parity_confidence",
        "require_all_states_bound",
        "transition_energy_tolerance_meV",
    }
)

BASE_OUTPUTS: frozenset[str] = frozenset(
    {
        "bandedges_glob",
        "energy_spectrum_glob",
        "probability_glob",
        "bandedge_columns",
        "energy_columns",
        "write_csv",
        "write_plots",
    }
)
EXTENDED_OUTPUTS: frozenset[str] = BASE_OUTPUTS | frozenset(
    {"parser_profile", "quantum_region_name", "bandedge_column_order", "polarizations"}
)


class SchemaError(ValueError):
    """Raised for any strict-schema violation; the caller converts to DemoError."""


@dataclass(frozen=True)
class DemoSchema:
    """Allowed keys and numeric constraints for one demo's YAML."""

    top_level: frozenset[str] = BASE_TOP_LEVEL
    required: tuple[str, ...] = ("demo_id", "title", "template", "scientific", "numerical")
    scientific: frozenset[str] = frozenset()
    numerical: frozenset[str] = frozenset()
    outputs: frozenset[str] = BASE_OUTPUTS
    validation: frozenset[str] = BASE_VALIDATION
    sweeps: frozenset[str] = frozenset()
    #: keys that must be finite and strictly positive
    positive: frozenset[str] = frozenset()
    #: keys that must be finite and >= 0
    non_negative: frozenset[str] = frozenset()
    #: keys that may take any finite value, including negative
    signed: frozenset[str] = frozenset()
    #: keys that must lie strictly inside (0, 1)
    fraction: frozenset[str] = frozenset()
    #: keys whose value must be an exact integer
    integer: frozenset[str] = frozenset()
    #: keys whose value is free-form text
    text: frozenset[str] = frozenset()
    #: sweep keys whose entries may be negative
    signed_sweeps: frozenset[str] = frozenset()
    #: extra mapping-valued sections that are passed through with light checks
    passthrough: frozenset[str] = field(default_factory=frozenset)

    def numeric_kind(self, name: str) -> str:
        if name in self.text:
            return "text"
        if name in self.fraction:
            return "fraction"
        if name in self.signed:
            return "signed"
        if name in self.non_negative:
            return "non_negative"
        return "positive"


def _finite(value: Any, label: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"{label} must be a finite number, got {value!r}.") from exc
    if not math.isfinite(numeric):
        raise SchemaError(f"{label} must be finite, got {value!r}.")
    return numeric


def check_value(schema: DemoSchema, name: str, value: Any, label: str) -> None:
    """Apply the schema's constraint for one named parameter."""

    kind = schema.numeric_kind(name)
    if kind == "text":
        if not str(value).strip():
            raise SchemaError(f"{label} must be a non-empty string.")
        return
    numeric = _finite(value, label)
    if kind == "fraction":
        if not 0.0 < numeric < 1.0:
            raise SchemaError(f"{label} must lie strictly between 0 and 1, got {numeric}.")
    elif kind == "non_negative":
        if numeric < 0:
            raise SchemaError(f"{label} must be >= 0, got {numeric}.")
    elif kind == "positive":
        if numeric <= 0:
            raise SchemaError(f"{label} must be finite and > 0, got {numeric}.")
    if name in schema.integer and int(numeric) != numeric:
        raise SchemaError(f"{label} must be an integer, got {value!r}.")


def strict_keys(mapping: Any, allowed: frozenset[str], label: str) -> dict[str, Any]:
    """Reject a mapping that carries any key outside ``allowed``."""

    if not isinstance(mapping, dict):
        raise SchemaError(f"{label} must be a YAML mapping.")
    unknown = sorted(set(mapping) - set(allowed))
    if unknown:
        raise SchemaError(f"{label} has unsupported key(s): {', '.join(unknown)}")
    return mapping


# ---------------------------------------------------------------------------
# demo schemas
# ---------------------------------------------------------------------------

_COMMON_1D_SCIENTIFIC = frozenset({"aluminum_fraction", "temperature_K"})
_COMMON_NUMERICAL = frozenset(
    {
        "active_region_grid_spacing_nm",
        "exterior_grid_spacing_nm",
        "number_of_states",
        "quantum_region_padding_nm",
    }
)

#: Exact transcription of the rules Demos 1-3 were validated with.
LEGACY_SCHEMA = DemoSchema(
    top_level=BASE_TOP_LEVEL,
    scientific=frozenset(
        {
            "well_width_nm",
            "left_barrier_width_nm",
            "right_barrier_width_nm",
            "barrier_width_nm",
            "aluminum_fraction",
            "temperature_K",
        }
    ),
    numerical=_COMMON_NUMERICAL,
    sweeps=frozenset(
        {
            "grid_spacing_nm",
            "domain_padding_nm",
            "quantum_region_padding_nm",
            "number_of_states",
        }
    ),
    positive=frozenset(
        {
            "well_width_nm",
            "left_barrier_width_nm",
            "right_barrier_width_nm",
            "barrier_width_nm",
            "temperature_K",
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_states",
            "quantum_region_padding_nm",
        }
    ),
    fraction=frozenset({"aluminum_fraction"}),
    integer=frozenset({"number_of_states"}),
)

#: What a demo may do with a state that is used by an analysis but fails the
#: bound-state criterion. Kept here so the vocabulary is validated at load time
#: rather than discovered as a silent no-op halfway through a licensed run.
QUASI_BOUND_POLICIES: frozenset[str] = frozenset({"warn", "exclude", "fail_case"})

_TRACKING_KEYS = frozenset(
    {
        "state_tracking_method",
        "minimum_state_tracking_confidence",
        "boundary_edge_fraction",
        "avoided_crossing_minimum_gap_meV",
        "avoided_crossing_relative_curvature",
        "parity_dominant_threshold",
        "character_dominant_threshold",
    }
)

DEMO4_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL,
    scientific=frozenset(
        {
            "well_width_nm",
            "center_barrier_nm",
            "left_outer_barrier_nm",
            "right_outer_barrier_nm",
            "aluminum_fraction",
            "temperature_K",
        }
    ),
    numerical=_COMMON_NUMERICAL,
    sweeps=frozenset({"center_barrier_nm", "quantum_region_padding_nm"}),
    outputs=EXTENDED_OUTPUTS,
    validation=EXTENDED_VALIDATION,
    positive=frozenset(
        {
            "well_width_nm",
            "center_barrier_nm",
            "left_outer_barrier_nm",
            "right_outer_barrier_nm",
            "temperature_K",
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_states",
            "quantum_region_padding_nm",
        }
    ),
    fraction=frozenset({"aluminum_fraction"}),
    integer=frozenset({"number_of_states"}),
    passthrough=frozenset({"analysis", "parser", "checks"}),
)

DEMO5_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL,
    scientific=frozenset(
        {
            "wide_well_width_nm",
            "narrow_well_width_nm",
            "center_barrier_nm",
            "left_outer_barrier_nm",
            "right_outer_barrier_nm",
            "aluminum_fraction",
            "temperature_K",
            "electric_field_kV_cm",
            "field_direction",
            "contact_thickness_nm",
        }
    ),
    numerical=_COMMON_NUMERICAL,
    sweeps=frozenset(
        {
            "electric_field_kV_cm",
            "quantum_region_padding_nm",
            "active_region_grid_spacing_nm",
        }
    ),
    outputs=EXTENDED_OUTPUTS,
    validation=EXTENDED_VALIDATION,
    positive=frozenset(
        {
            "wide_well_width_nm",
            "narrow_well_width_nm",
            "center_barrier_nm",
            "left_outer_barrier_nm",
            "right_outer_barrier_nm",
            "temperature_K",
            "contact_thickness_nm",
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_states",
            "quantum_region_padding_nm",
        }
    ),
    signed=frozenset({"electric_field_kV_cm"}),
    fraction=frozenset({"aluminum_fraction"}),
    integer=frozenset({"number_of_states"}),
    text=frozenset({"field_direction"}),
    signed_sweeps=frozenset({"electric_field_kV_cm"}),
    passthrough=frozenset({"analysis", "parser", "checks"}),
)

DEMO6_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL,
    scientific=frozenset(
        {
            "wide_well_width_nm",
            "narrow_well_width_nm",
            "center_barrier_nm",
            "left_outer_barrier_nm",
            "right_outer_barrier_nm",
            "aluminum_fraction",
            "temperature_K",
            "electric_field_kV_cm",
            "field_direction",
            "contact_thickness_nm",
            "donor_density_cm3",
            "donor_region_start_nm",
            "donor_region_end_nm",
            "donor_ionization_energy_eV",
            "donor_degeneracy",
            "spacer_thickness_nm",
            "contact_bias_V",
        }
    ),
    numerical=_COMMON_NUMERICAL
    | frozenset(
        {
            "solver_residual_density_cm2",
            "convergence_relative_tolerance",
            "maximum_iterations",
            "potential_mixing_alpha",
        }
    ),
    sweeps=frozenset({"donor_density_cm3", "quantum_region_padding_nm"}),
    outputs=EXTENDED_OUTPUTS,
    validation=EXTENDED_VALIDATION,
    positive=frozenset(
        {
            "wide_well_width_nm",
            "narrow_well_width_nm",
            "center_barrier_nm",
            "left_outer_barrier_nm",
            "right_outer_barrier_nm",
            "temperature_K",
            "contact_thickness_nm",
            "donor_density_cm3",
            "donor_ionization_energy_eV",
            "donor_degeneracy",
            "spacer_thickness_nm",
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_states",
            "quantum_region_padding_nm",
            "solver_residual_density_cm2",
            "convergence_relative_tolerance",
            "maximum_iterations",
            "potential_mixing_alpha",
        }
    ),
    non_negative=frozenset({"donor_region_start_nm", "donor_region_end_nm"}),
    signed=frozenset({"electric_field_kV_cm", "contact_bias_V"}),
    fraction=frozenset({"aluminum_fraction"}),
    integer=frozenset({"number_of_states", "maximum_iterations", "donor_degeneracy"}),
    text=frozenset({"field_direction"}),
    passthrough=frozenset({"models", "analysis", "parser", "checks"}),
)

DEMO7_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL,
    scientific=frozenset(
        {
            "indium_fraction",
            "well_width_nm",
            "barrier_width_nm",
            "substrate_material",
            "growth_direction",
            "temperature_K",
        }
    ),
    numerical=frozenset(
        {
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_electron_states",
            "number_of_hole_states",
            "quantum_region_padding_nm",
        }
    ),
    sweeps=frozenset({"indium_fraction", "well_width_nm"}),
    outputs=EXTENDED_OUTPUTS,
    validation=EXTENDED_VALIDATION,
    positive=frozenset(
        {
            "well_width_nm",
            "barrier_width_nm",
            "temperature_K",
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_electron_states",
            "number_of_hole_states",
            "quantum_region_padding_nm",
        }
    ),
    fraction=frozenset({"indium_fraction"}),
    integer=frozenset({"number_of_electron_states", "number_of_hole_states"}),
    text=frozenset({"substrate_material", "growth_direction"}),
    passthrough=frozenset({"models", "analysis", "parser", "checks"}),
)

DEMO8_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL,
    scientific=frozenset(
        {
            "indium_fraction",
            "well_width_nm",
            "barrier_width_nm",
            "substrate_material",
            "growth_direction",
            "temperature_K",
            "electric_field_kV_cm",
            "symmetry_breaking_step_nm",
            "symmetry_breaking_indium_fraction",
            "contact_thickness_nm",
        }
    ),
    numerical=frozenset(
        {
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_electron_states",
            "number_of_hole_states",
            "quantum_region_padding_nm",
            "k_parallel_num_points",
            "k_parallel_relative_size",
            "broadening_meV",
            "spectral_energy_min_eV",
            "spectral_energy_max_eV",
            "spectral_points",
        }
    ),
    sweeps=frozenset({"well_width_nm", "electric_field_kV_cm"}),
    outputs=EXTENDED_OUTPUTS,
    validation=EXTENDED_VALIDATION,
    positive=frozenset(
        {
            "well_width_nm",
            "barrier_width_nm",
            "temperature_K",
            "contact_thickness_nm",
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_electron_states",
            "number_of_hole_states",
            "quantum_region_padding_nm",
            "k_parallel_num_points",
            "k_parallel_relative_size",
            "broadening_meV",
            "spectral_energy_min_eV",
            "spectral_energy_max_eV",
            "spectral_points",
            "symmetry_breaking_step_nm",
        }
    ),
    signed=frozenset({"electric_field_kV_cm"}),
    fraction=frozenset({"indium_fraction", "symmetry_breaking_indium_fraction"}),
    integer=frozenset(
        {
            "number_of_electron_states",
            "number_of_hole_states",
            "k_parallel_num_points",
            "spectral_points",
        }
    ),
    text=frozenset({"substrate_material", "growth_direction"}),
    signed_sweeps=frozenset({"electric_field_kV_cm"}),
    passthrough=frozenset({"models", "analysis", "parser", "metric", "checks"}),
)

DEMO9_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL,
    scientific=frozenset(
        {
            "wide_well_width_nm",
            "narrow_well_width_nm",
            "center_barrier_nm",
            "left_outer_barrier_nm",
            "right_outer_barrier_nm",
            "aluminum_fraction",
            "temperature_K",
            "electric_field_kV_cm",
            "field_direction",
            "contact_thickness_nm",
        }
    ),
    numerical=_COMMON_NUMERICAL,
    sweeps=frozenset(
        {
            "wide_well_width_nm",
            "narrow_well_width_nm",
            "center_barrier_nm",
            "aluminum_fraction",
            "electric_field_kV_cm",
        }
    ),
    outputs=EXTENDED_OUTPUTS,
    validation=EXTENDED_VALIDATION,
    positive=frozenset(
        {
            "wide_well_width_nm",
            "narrow_well_width_nm",
            "center_barrier_nm",
            "left_outer_barrier_nm",
            "right_outer_barrier_nm",
            "temperature_K",
            "contact_thickness_nm",
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_states",
            "quantum_region_padding_nm",
        }
    ),
    signed=frozenset({"electric_field_kV_cm"}),
    fraction=frozenset({"aluminum_fraction"}),
    integer=frozenset({"number_of_states"}),
    text=frozenset({"field_direction"}),
    signed_sweeps=frozenset({"electric_field_kV_cm"}),
    passthrough=frozenset({"analysis", "parser", "metric", "checks"}),
)

DEMO10_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL,
    scientific=frozenset(
        {
            "wire_width_nm",
            "wire_height_nm",
            "lateral_barrier_nm",
            "vertical_barrier_nm",
            "aluminum_fraction",
            "temperature_K",
        }
    ),
    numerical=frozenset(
        {
            "grid_spacing_x_nm",
            "grid_spacing_y_nm",
            "exterior_grid_spacing_nm",
            "number_of_states",
            "domain_padding_x_nm",
            "domain_padding_y_nm",
            "geometry_offset_x_nm",
            "geometry_offset_y_nm",
        }
    ),
    sweeps=frozenset(
        {
            "wire_width_nm",
            "grid_spacing_x_nm",
            "grid_spacing_y_nm",
            "domain_padding_x_nm",
            "domain_padding_y_nm",
        }
    ),
    outputs=EXTENDED_OUTPUTS,
    validation=EXTENDED_VALIDATION,
    positive=frozenset(
        {
            "wire_width_nm",
            "wire_height_nm",
            "lateral_barrier_nm",
            "vertical_barrier_nm",
            "temperature_K",
            "grid_spacing_x_nm",
            "grid_spacing_y_nm",
            "exterior_grid_spacing_nm",
            "number_of_states",
            "domain_padding_x_nm",
            "domain_padding_y_nm",
        }
    ),
    signed=frozenset({"geometry_offset_x_nm", "geometry_offset_y_nm"}),
    fraction=frozenset({"aluminum_fraction"}),
    integer=frozenset({"number_of_states"}),
    passthrough=frozenset({"analysis", "parser", "checks"}),
)


DEMO11_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL,
    scientific=frozenset(
        {
            "thick_well_nm",
            "thin_well_nm",
            "tunnel_barrier_nm",
            "period_barrier_nm",
            "aluminum_fraction",
            "temperature_K",
            "interface_grading_nm",
        }
    ),
    numerical=frozenset(
        {
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_electron_states",
            "number_of_hole_states",
            "quantum_region_padding_nm",
            "domain_padding_nm",
        }
    ),
    sweeps=frozenset(),
    outputs=EXTENDED_OUTPUTS,
    validation=EXTENDED_VALIDATION
    | frozenset({"transition_energy_tolerance_meV", "quasi_bound_state_policy"}),
    positive=frozenset(
        {
            "thick_well_nm",
            "thin_well_nm",
            "tunnel_barrier_nm",
            "period_barrier_nm",
            "temperature_K",
            "active_region_grid_spacing_nm",
            "exterior_grid_spacing_nm",
            "number_of_electron_states",
            "number_of_hole_states",
            "quantum_region_padding_nm",
        }
    ),
    # Grading of zero means abrupt interfaces, which is the paper's ideal case.
    non_negative=frozenset({"interface_grading_nm", "domain_padding_nm"}),
    fraction=frozenset({"aluminum_fraction"}),
    integer=frozenset({"number_of_electron_states", "number_of_hole_states"}),
    passthrough=frozenset({"analysis", "parser", "metric", "checks"}),
)


# Demo 12 deliberately keeps its study design in named YAML sections rather
# than turning dozens of scientific settings into command-line flags.  The
# baseline scientific/numerical vocabulary is inherited from Demo 11; the rich
# study sections are validated by demo12.validate_demo12_config(), where their
# relationships (profiles, locations, tiers and constraints) can be checked
# more clearly than this scalar schema can express.
DEMO12_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL
    | frozenset(
        {
            "baseline",
            "grading",
            "locations",
            "joint_sweep",
            "robustness",
            "optimization",
            "state_tracking",
            "bound_states",
            "chi2",
            "execution",
            "reporting",
        }
    ),
    scientific=DEMO11_SCHEMA.scientific,
    numerical=DEMO11_SCHEMA.numerical,
    sweeps=frozenset(),
    outputs=EXTENDED_OUTPUTS,
    validation=DEMO11_SCHEMA.validation
    | frozenset(
        {
            "grading_thickness_tolerance_nm",
            "composition_endpoint_tolerance",
            "integrated_composition_relative_tolerance",
            "native_staircase_composition_rms_tolerance",
            "native_staircase_bandedge_tolerance_meV",
        }
    ),
    positive=DEMO11_SCHEMA.positive,
    non_negative=DEMO11_SCHEMA.non_negative,
    fraction=DEMO11_SCHEMA.fraction,
    integer=DEMO11_SCHEMA.integer,
    passthrough=frozenset(
        {
            "analysis",
            "parser",
            "metric",
            "checks",
            "baseline",
            "grading",
            "locations",
            "joint_sweep",
            "robustness",
            "optimization",
            "state_tracking",
            "bound_states",
            "chi2",
            "execution",
            "reporting",
        }
    ),
)

# Demo 13 keeps Demo 12's physical vocabulary unchanged -- a Demo 13 trial and a
# Demo 12 case with the same geometry must be the same calculation -- and adds
# only the sections that describe the *search*: `demo`, `workflow`,
# `simulation`, `bo`, `validation_study` and `paper_comparison`. Their internal
# relationships (iteration counts, search-space bounds, objective modes and
# outcome constraints) are checked by demo13.validate_demo13_config(), which can
# express them far more clearly than this scalar schema can.
DEMO13_SCHEMA = DemoSchema(
    top_level=EXTENDED_TOP_LEVEL
    | frozenset(
        {
            "demo",
            "baseline",
            "workflow",
            "simulation",
            "bo",
            "validation_study",
            "grading",
            "locations",
            "state_tracking",
            "bound_states",
            "physical_qc",
            "chi2",
            "paper_comparison",
            "reporting",
        }
    ),
    scientific=DEMO11_SCHEMA.scientific,
    numerical=DEMO11_SCHEMA.numerical,
    sweeps=frozenset(),
    outputs=EXTENDED_OUTPUTS,
    validation=DEMO12_SCHEMA.validation,
    positive=DEMO11_SCHEMA.positive,
    non_negative=DEMO11_SCHEMA.non_negative,
    fraction=DEMO11_SCHEMA.fraction,
    integer=DEMO11_SCHEMA.integer,
    passthrough=frozenset(
        {
            "analysis",
            "parser",
            "metric",
            "checks",
            "demo",
            "baseline",
            "workflow",
            "simulation",
            "bo",
            "validation_study",
            "grading",
            "locations",
            "state_tracking",
            "bound_states",
            "physical_qc",
            "chi2",
            "paper_comparison",
            "reporting",
        }
    ),
)

# Demo 14 replaces Demo 13's relative merit with an absolute pm/V susceptibility
# and its staircase renderer with continuous composition profiles, so its config
# shares almost no section names with Demo 13's. The cross-section relationships
# (trial budget, absolute-mode constants, search-space bounds) are checked by
# demo14.validate_config(), which states them far more clearly than a scalar
# schema can.
DEMO14_SCHEMA = DemoSchema(
    top_level=frozenset(
        {
            "experiment",
            "materials",
            "geometry",
            "grading",
            "nextnano",
            "mesh",
            "states",
            "chi2",
            "k_parallel",
            "optimization",
            "constraints",
            "failure_policy",
            "logging",
            "checkpointing",
            "plotting",
            "paper_reference",
            "startup_gate",
            "workflow",
            "paths",
        }
    ),
)


DEMO_SCHEMAS: Mapping[str, DemoSchema] = {
    "01": LEGACY_SCHEMA,
    "02": LEGACY_SCHEMA,
    "03": LEGACY_SCHEMA,
    "04": DEMO4_SCHEMA,
    "05": DEMO5_SCHEMA,
    "06": DEMO6_SCHEMA,
    "07": DEMO7_SCHEMA,
    "08": DEMO8_SCHEMA,
    "09": DEMO9_SCHEMA,
    "10": DEMO10_SCHEMA,
    "11": DEMO11_SCHEMA,
    "12": DEMO12_SCHEMA,
    "13": DEMO13_SCHEMA,
    "14": DEMO14_SCHEMA,
}


def schema_for(demo_id: str) -> DemoSchema:
    """Look up a demo's schema by its numeric prefix."""

    prefix = str(demo_id).split("_", 1)[0]
    try:
        return DEMO_SCHEMAS[prefix]
    except KeyError as exc:
        raise SchemaError(
            f"no YAML schema is registered for demo prefix {prefix!r}; add one in "
            "_shared/schemas.py before adding the demo."
        ) from exc


def validate_config(cfg: Mapping[str, Any], schema: DemoSchema, label: str) -> dict[str, Any]:
    """Strictly validate one loaded ``demo.yaml`` against its schema."""

    data = dict(strict_keys(cfg, schema.top_level, label))
    for required in schema.required:
        if required not in data:
            raise SchemaError(f"{label}: missing required key {required!r}.")

    scientific = strict_keys(data["scientific"], schema.scientific, f"{label}: scientific")
    numerical = strict_keys(data["numerical"], schema.numerical, f"{label}: numerical")
    for name, value in scientific.items():
        check_value(schema, name, value, f"{label}: scientific.{name}")
    for name, value in numerical.items():
        check_value(schema, name, value, f"{label}: numerical.{name}")

    data["outputs"] = strict_keys(data.get("outputs", {}), schema.outputs, f"{label}: outputs")
    data["validation"] = strict_keys(
        data.get("validation", {}), schema.validation, f"{label}: validation"
    )
    for name in ("minimum_well_probability", "maximum_boundary_probability",
                 "minimum_confined_probability", "minimum_state_tracking_confidence",
                 "minimum_parity_confidence", "maximum_symmetry_error"):
        if name in data["validation"]:
            value = _finite(data["validation"][name], f"{label}: validation.{name}")
            if not 0 <= value <= 1:
                raise SchemaError(f"{label}: validation.{name} must lie in [0, 1].")
    if "quasi_bound_state_policy" in data["validation"]:
        policy = str(data["validation"]["quasi_bound_state_policy"])
        if policy not in QUASI_BOUND_POLICIES:
            raise SchemaError(
                f"{label}: validation.quasi_bound_state_policy must be one of "
                f"{', '.join(sorted(QUASI_BOUND_POLICIES))}, got {policy!r}."
            )
    for name in (
        "normalization_tolerance",
        "absolute_energy_tolerance_meV",
        "relative_energy_tolerance",
        "maximum_charge_imbalance",
        "maximum_matrix_element_disagreement_nm",
    ):
        if name in data["validation"]:
            value = _finite(data["validation"][name], f"{label}: validation.{name}")
            if value < 0:
                raise SchemaError(f"{label}: validation.{name} must be >= 0.")

    if "sweeps" in data:
        sweeps = strict_keys(data["sweeps"], schema.sweeps, f"{label}: sweeps")
        for name, values in sweeps.items():
            if not isinstance(values, list) or not values:
                raise SchemaError(f"{label}: sweeps.{name} must be a non-empty list.")
            if len(set(map(str, values))) != len(values):
                raise SchemaError(f"{label}: sweeps.{name} contains duplicate values.")
            for value in values:
                numeric = _finite(value, f"{label}: sweeps.{name}")
                if name not in schema.signed_sweeps and numeric <= 0:
                    raise SchemaError(
                        f"{label}: every sweeps.{name} value must be finite and > 0."
                    )
                if name in schema.integer and int(numeric) != numeric:
                    raise SchemaError(
                        f"{label}: every sweeps.{name} value must be an integer."
                    )

    for section in schema.passthrough:
        if section in data and not isinstance(data[section], (dict, list)):
            raise SchemaError(f"{label}: {section} must be a mapping or a list.")
    return data
