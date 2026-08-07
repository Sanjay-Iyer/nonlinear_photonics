"""Demo 14 -> Demo 11 analysis-configuration adapter.

Demo 14 deliberately reuses Demo 11's validated parser and Eq. 2 evaluation
rather than reimplementing them, so a Demo 14 trial and a Demo 11 case of the
same structure are the same calculation with the same provenance. But the two
demos have **different YAML schemas**, and Demo 11's analyser reads its own.
This module is the single, explicit translation between them.

It exists because the first licensed Demo 14 gate run died here:

    demo11.analyse_case -> build_stack -> cfg["scientific"] -> KeyError

Demo 14's earlier inline projection invented a ``structure`` section with
plausible-looking names. Demo 11 wants ``scientific``, and several of the field
names differ in ways that read as synonyms but are not:

* ``tunnel_barrier_nm``, not ``central_barrier_thickness_nm``;
* ``aluminum_fraction`` (American), not ``aluminium_fraction``;
* ``scientific``/``numerical``/``outputs``/``validation``/``analysis``/``metric``
  as six separate sections, not a flat structure block.

**Demo 14's config stays authoritative.** Nothing here is a second source of
scientific truth: every value below is either derived from the Demo 14 config,
derived from the trial's realized geometry, or an analysis-only threshold that
Demo 11 needs and Demo 14 does not model. Where a value is analysis-only it is
marked as such, with the reason.

## Field map

| Demo 11 field | Source | Units | Fixed / per-trial |
|---|---|---|---|
| `scientific.thick_well_nm` | `Geometry.thick_well_nm`, from `D(1+s)/2` | nm | per-trial |
| `scientific.thin_well_nm` | `Geometry.thin_well_nm`, from `D(1-s)/2` | nm | per-trial |
| `scientific.tunnel_barrier_nm` | `Geometry.barrier_nm` | nm | per-trial |
| `scientific.period_barrier_nm` | `geometry.period_barrier_nm` | nm | fixed |
| `scientific.aluminum_fraction` | `materials.barrier_al_fraction` | 1 | fixed (Demo 15 frees it) |
| `scientific.temperature_K` | `materials.temperature_K` | K | fixed |
| `scientific.interface_grading_nm` | realized peak-referenced left 10-90 width | nm | per-trial, reporting only |
| `numerical.active_region_grid_spacing_nm` | `mesh.active_region_grid_spacing_nm` | nm | fixed |
| `numerical.exterior_grid_spacing_nm` | `mesh.outer_grid_spacing_nm` | nm | fixed |
| `numerical.domain_padding_nm` | **derived**, see `_outer_padding_nm` | nm | fixed |
| `numerical.quantum_region_padding_nm` | `geometry.quantum_region_padding_nm` | nm | fixed |
| `numerical.number_of_electron_states` | `states.number_of_electron_states` | count | fixed |
| `numerical.number_of_hole_states` | `states.number_of_hole_states` | count | fixed |
| `outputs.*` | `nextnano.*` | - | fixed |
| `validation.*` | Demo 14 constraints + Demo 11 analysis defaults | - | fixed |
| `analysis.*` | analysis-only thresholds | - | fixed |
| `metric.*` | `physics14.settings_from_config` + scan window | - | fixed |

`metric` carries `r_e_hh_nm`, `n_wells_per_metre`, `spin_degeneracy` and the
k-parallel settings, which is how the absolute mode reaches Demo 11's
``chi2_settings``.
"""

from __future__ import annotations

from typing import Any, Mapping

import physics14


class Adapter14Error(ValueError):
    """The Demo 14 configuration cannot be expressed in Demo 11's schema."""


#: Sections Demo 11's analysis path reads. Checked explicitly so a missing one
#: fails here, with a name, rather than as a KeyError deep inside the analyser
#: after a licensed solve has already been paid for.
REQUIRED_DEMO11_SECTIONS = (
    "scientific", "numerical", "outputs", "validation", "analysis", "metric",
)

REQUIRED_DEMO11_FIELDS: Mapping[str, tuple[str, ...]] = {
    "scientific": (
        "thick_well_nm", "thin_well_nm", "tunnel_barrier_nm", "period_barrier_nm",
        "aluminum_fraction", "temperature_K", "interface_grading_nm",
    ),
    "numerical": (
        "active_region_grid_spacing_nm", "exterior_grid_spacing_nm",
        "domain_padding_nm", "quantum_region_padding_nm",
        "number_of_electron_states", "number_of_hole_states",
    ),
    "outputs": ("parser_profile", "quantum_region_name", "bandedge_columns"),
    "validation": (
        "minimum_confined_probability", "maximum_boundary_probability",
        "normalization_tolerance",
    ),
    "analysis": (
        "quantum_region_name", "boundary_edge_fraction", "orthonormality_tolerance",
    ),
    "metric": ("mode", "broadening_meV", "max_states_per_band"),
}


def _outer_padding_nm(cfg: Mapping[str, Any]) -> float:
    """Demo 11's ``domain_padding_nm`` that reproduces Demo 14's actual deck.

    Demo 11 builds each outer barrier as ``0.5 * period_barrier_nm +
    domain_padding_nm``, while Demo 14's renderer puts a flat
    ``geometry.domain_padding_nm`` on each side of the active region. The
    LayerStack is what supplies ``region_map`` and the quantum window, so if the
    two disagree the region probabilities and the state-selection window are
    computed for a structure that was never solved. Solving for the padding that
    makes them identical:

        0.5 * period_barrier + padding_11 = padding_14
    """

    padding_14 = float(cfg["geometry"]["domain_padding_nm"])
    period_barrier = float(cfg["geometry"]["period_barrier_nm"])
    padding_11 = padding_14 - 0.5 * period_barrier
    if padding_11 < 0.0:
        raise Adapter14Error(
            f"geometry.domain_padding_nm ({padding_14} nm) is smaller than half "
            f"the period barrier ({0.5 * period_barrier} nm), so Demo 11's layer "
            "stack cannot reproduce the structure Demo 14 renders. Increase the "
            "padding or reduce geometry.period_barrier_nm."
        )
    return padding_11


def build_demo11_analysis_config_from_demo14(
    cfg: Mapping[str, Any],
    geometry: Any,
    profile: Any | None = None,
) -> dict[str, Any]:
    """Project the authoritative Demo 14 config into Demo 11's analysis schema.

    ``geometry`` is the trial's :class:`demo14.Geometry`; ``profile`` its
    :class:`grading14.CompositionProfile`, used only to report the realized
    interface width. Neither is re-derived here -- passing them in is what keeps
    the analysed structure identical to the rendered one.
    """

    for section in ("materials", "geometry", "mesh", "states", "chi2",
                    "k_parallel", "nextnano", "constraints"):
        if section not in cfg:
            raise Adapter14Error(
                f"Demo 14 configuration is missing the '{section}' section, which "
                "the Demo 11 analysis adapter needs."
            )

    settings = physics14.settings_from_config(cfg)
    limits = cfg["constraints"]
    nextnano_cfg = cfg["nextnano"]

    realized_grading_nm = 0.0
    if profile is not None:
        width = profile.diagnostics.get(
            "realized_gaas_to_algaas_grading_width_10_90_peakref_nm"
        )
        realized_grading_nm = float(width) if width is not None else 0.0

    derived: dict[str, Any] = {
        # --- structure actually solved -------------------------------------
        "scientific": {
            "thick_well_nm": float(geometry.thick_well_nm),
            "thin_well_nm": float(geometry.thin_well_nm),
            "tunnel_barrier_nm": float(geometry.barrier_nm),
            "period_barrier_nm": float(cfg["geometry"]["period_barrier_nm"]),
            "aluminum_fraction": float(cfg["materials"]["barrier_al_fraction"]),
            "temperature_K": float(cfg["materials"]["temperature_K"]),
            # Reported only. Demo 11 uses this to render ITS deck; Demo 14
            # renders its own from the composition profile, so this value never
            # feeds the solved structure -- it travels so the observable is not
            # silently zero for a graded design.
            "interface_grading_nm": realized_grading_nm,
        },
        # --- numerics -------------------------------------------------------
        "numerical": {
            "active_region_grid_spacing_nm": float(
                cfg["mesh"]["active_region_grid_spacing_nm"]
            ),
            "exterior_grid_spacing_nm": float(cfg["mesh"]["outer_grid_spacing_nm"]),
            "domain_padding_nm": _outer_padding_nm(cfg),
            "quantum_region_padding_nm": float(
                cfg["geometry"]["quantum_region_padding_nm"]
            ),
            "number_of_electron_states": int(cfg["states"]["number_of_electron_states"]),
            "number_of_hole_states": int(cfg["states"]["number_of_hole_states"]),
        },
        # --- parser ----------------------------------------------------------
        "outputs": {
            "parser_profile": str(nextnano_cfg["parser_profile"]),
            "quantum_region_name": str(nextnano_cfg["quantum_region_name"]),
            "polarizations": ["growth_z"],
            "bandedge_columns": dict(nextnano_cfg["bandedge_columns"]),
            "write_csv": True,
            "write_plots": False,
        },
        # --- validation ------------------------------------------------------
        # Demo 14's outcome constraints where they correspond; Demo 11's own
        # defaults for the parser-level thresholds Demo 14 does not model. These
        # are analysis-only and are marked as such rather than invented.
        "validation": {
            "completion_markers": [
                "simulation completed", "calculation successfully completed",
            ],
            "fatal_markers": [
                "terminating program", "fatal error", "license expired",
            ],
            "convergence_warning_markers": ["failed to converge"],
            "minimum_confined_probability": 0.5,     # analysis-only
            "maximum_boundary_probability": float(
                limits["maximum_boundary_probability"]
            ),
            "quasi_bound_state_policy": "warn",      # analysis-only
            "normalization_tolerance": float(limits["maximum_orthonormality_error"]),
            "transition_energy_tolerance_meV": 40.0,  # analysis-only
            "absolute_energy_tolerance_meV": 1.0,     # analysis-only
            "require_all_states_bound": False,        # analysis-only
        },
        # --- analysis thresholds ---------------------------------------------
        "analysis": {
            "quantum_region_name": str(nextnano_cfg["quantum_region_name"]),
            "dipole_polarization_name": str(nextnano_cfg["dipole_polarization_name"]),
            "boundary_edge_fraction": 0.05,          # analysis-only
            "orthonormality_tolerance": float(limits["maximum_orthonormality_error"]),
            "maximum_origin_dependence": 1.0e-6,     # analysis-only
            "origin_independence_absolute_tolerance": 1.0e-12,
            "origin_independence_scale_floor": 1.0e-9,
            "origin_independence_shift_nm": 100.0,
            "state_tracking": {
                "enabled": True,
                "minimum_confidence": float(
                    limits["minimum_state_tracking_confidence"]
                ),
                "minimum_assignment_margin": 0.15,
                "energy_continuity_weight": 0.05,
                "bands": ["electron", "heavy_hole"],
            },
        },
        # --- the absolute susceptibility -------------------------------------
        "metric": {
            **settings.as_record(),
            "broad_wavelength_nm": list(cfg["chi2"]["broad_wavelength_nm"]),
            "broad_wavelength_points": int(cfg["chi2"]["broad_wavelength_points"]),
            "focused_wavelength_nm": list(cfg["chi2"]["focused_wavelength_nm"]),
            "focused_wavelength_points": int(cfg["chi2"]["focused_wavelength_points"]),
            "reference_wavelength_nm": float(cfg["chi2"]["target_wavelength_nm"]),
        },
    }
    validate_demo11_config(derived)
    return derived


def validate_demo11_config(cfg: Mapping[str, Any]) -> None:
    """Fail with a named field, not a KeyError inside the analyser.

    The whole point is that this runs before a licensed solve, and that its
    failure message says which field is missing rather than which line raised.
    """

    missing_sections = [s for s in REQUIRED_DEMO11_SECTIONS if s not in cfg]
    if missing_sections:
        raise Adapter14Error(
            "the derived Demo 11 analysis config is missing section(s): "
            + ", ".join(missing_sections)
        )
    problems: list[str] = []
    for section, fields in REQUIRED_DEMO11_FIELDS.items():
        block = cfg.get(section) or {}
        for field in fields:
            if field not in block:
                problems.append(f"{section}.{field}")
    if problems:
        raise Adapter14Error(
            "the derived Demo 11 analysis config is missing field(s): "
            + ", ".join(sorted(problems))
        )
    metric = cfg["metric"]
    if str(metric.get("mode")) == "absolute":
        for field in ("r_e_hh_nm", "n_wells_per_metre"):
            if metric.get(field) is None:
                raise Adapter14Error(
                    f"absolute mode requires metric.{field}, which is None. "
                    "chi2_spectrum would refuse this and the trial would fail "
                    "after the solver had already run."
                )
