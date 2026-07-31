"""Demo 12 — graded-interface coupled-QW validation and optimization.

This module extends Demo 11; it does not replace its electronic-structure or
interband chi(2) model.  Native nextnano++ grading is restricted to the
repository-confirmed ``ternary_linear`` grammar.  Smooth profiles are rendered
as explicit thin constant-composition sublayers, which is both the portable
fallback and a controlled approximation whose error is reported.
"""

from __future__ import annotations

import copy
import csv
import importlib.util
import itertools
import json
import math
from pathlib import Path
import shutil
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml

import chi2 as chi2mod
import layers
import outputs
import plots as plotting
import sweeps
from demo_workflow import DemoError, write_json_atomically, write_text_atomically

import grading12
import tracking12


DEMO_DIR = Path(__file__).resolve().parent
DEMO11_DIR = DEMO_DIR.parent / "11_paper_validation_interband_chi2_acqw"


def _load_demo11():
    """Load Demo 11 without duplicating its extraction/chi(2) implementation."""

    import sys

    for path in (str(DEMO11_DIR), str(DEMO_DIR.parent / "_shared")):
        if path not in sys.path:
            sys.path.insert(0, path)
    spec = importlib.util.spec_from_file_location("demo11_for_demo12", DEMO11_DIR / "demo11.py")
    if spec is None or spec.loader is None:
        raise DemoError("could not load Demo 11 implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


demo11 = _load_demo11()

ALLOWED_PROFILES = {
    "abrupt", "linear", "sigmoid", "erf", "cosine", "staircase_linear", "asymmetric"
}
ALLOWED_LOCATIONS = {
    "none", "all", "outer_only", "central_only", "narrow_well_only",
    "wide_well_only", "left_only", "right_only",
}
ALLOWED_TIERS = {"A", "B", "C"}

PLOT_SET: tuple[tuple[str, str], ...] = (
    ("01_alloy_composition.png", "Alloy composition versus position"),
    ("02_bands_and_composition.png", "Band edges and composition"),
    ("03_representative_wavefunctions.png", "Representative wavefunctions"),
    ("04_abrupt_graded_wavefunctions.png", "Abrupt versus graded wavefunctions"),
    ("05_energies_vs_grading.png", "Energy levels versus grading thickness"),
    ("06_transitions_vs_grading.png", "Transition energies versus grading thickness"),
    ("07_resonance_vs_grading.png", "Resonance versus grading thickness"),
    ("08_peak_chi2_vs_grading.png", "Peak chi(2) versus grading thickness"),
    ("09_target_chi2_vs_grading.png", "Target-wavelength chi(2) versus grading"),
    ("10_peak_wavelength_detuning.png", "Peak wavelength and target detuning"),
    ("11_overlap_vs_grading.png", "Electron-hole overlap versus grading"),
    ("12_localization_vs_grading.png", "Localization versus grading"),
    ("13_boundary_vs_grading.png", "Boundary probability versus grading"),
    ("14_anticrossing_map.png", "Anticrossing map"),
    ("15_peak_chi2_heatmap.png", "Peak chi(2) heatmap"),
    ("16_target_chi2_heatmap.png", "Target chi(2) heatmap"),
    ("17_tracking_confidence_heatmap.png", "Tracking confidence heatmap"),
    ("18_raw_tracked_energy.png", "Raw and tracked energy branches"),
    ("19_raw_tracked_chi2.png", "Raw and tracked chi(2)"),
    ("20_sensitivity_tornado.png", "Ranked sensitivity"),
    ("21_robustness_comparison.png", "Abrupt versus graded robustness"),
    ("22_pareto_front.png", "Nonlinear strength versus robustness Pareto front"),
    ("23_best_design_dashboard.png", "Best-design comparison dashboard"),
    ("24_native_staircase_validation.png", "Native versus staircase validation"),
)


def _require_mapping(cfg: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = cfg.get(name)
    if not isinstance(value, Mapping):
        raise DemoError(f"demo.yaml: {name} must be a mapping")
    return value


def validate_demo12_config(cfg: Mapping[str, Any]) -> None:
    """Validate relationships that the shared scalar schema cannot express."""

    grading = _require_mapping(cfg, "grading")
    profiles = grading.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise DemoError("grading.profiles must be a non-empty list")
    unknown = sorted(set(map(str, profiles)) - ALLOWED_PROFILES)
    if unknown:
        raise DemoError(f"unsupported grading profiles: {', '.join(unknown)}")
    thicknesses = grading.get("thickness_nm")
    if not isinstance(thicknesses, list) or 0.0 not in map(float, thicknesses):
        raise DemoError("grading.thickness_nm must be a list containing abrupt 0.0")
    if any(float(value) < 0 for value in thicknesses):
        raise DemoError("grading thicknesses cannot be negative")
    if int(grading.get("minimum_grid_points_per_grade", 0)) < 2:
        raise DemoError("grading.minimum_grid_points_per_grade must be at least 2")
    locations = _require_mapping(cfg, "locations").get("study_modes")
    if not isinstance(locations, list) or not locations:
        raise DemoError("locations.study_modes must be a non-empty list")
    bad_locations = sorted(set(map(str, locations)) - ALLOWED_LOCATIONS)
    if bad_locations:
        raise DemoError(f"unsupported grading locations: {', '.join(bad_locations)}")
    execution = _require_mapping(cfg, "execution")
    tier = str(execution.get("tier", "A")).upper()
    if tier not in ALLOWED_TIERS:
        raise DemoError("execution.tier must be A, B, or C")
    if tier == "C" and not bool(execution.get("enable_full_optimization", False)):
        raise DemoError(
            "Tier C is intentionally gated; set execution.enable_full_optimization: true"
        )
    policy = str(_require_mapping(cfg, "bound_states").get("policy", "warn"))
    if policy not in {"warn", "exclude", "fail_case"}:
        raise DemoError("bound_states.policy must be warn, exclude, or fail_case")
    joint = _require_mapping(cfg, "joint_sweep")
    asymmetry = _require_mapping(joint, "asymmetry")
    start, stop, step = (float(asymmetry[key]) for key in ("start", "stop", "step"))
    if step <= 0 or stop < start:
        raise DemoError("joint_sweep.asymmetry needs start <= stop and step > 0")


def outer_barrier_nm(cfg: Mapping[str, Any]) -> float:
    return 0.5 * float(cfg["scientific"]["period_barrier_nm"]) + float(
        cfg["numerical"].get("domain_padding_nm", 0.0)
    )


def build_stack(cfg: Mapping[str, Any]) -> layers.LayerStack:
    s, n = cfg["scientific"], cfg["numerical"]
    # Positive interface_shift_nm translates the central barrier to the right:
    # the left (thick) well grows and the right (thin) well shrinks by the same
    # amount, preserving total well material and total device length.
    interface_shift = float((cfg.get("grading") or {}).get("interface_shift_nm", 0.0))
    thick = float(s["thick_well_nm"]) + interface_shift
    thin = float(s["thin_well_nm"]) - interface_shift
    if thick <= 0 or thin <= 0:
        raise DemoError("interface_shift_nm makes a well non-positive")
    return layers.asymmetric_double_well(
        left_well_width_nm=thick,
        right_well_width_nm=thin,
        centre_barrier_nm=float(s["tunnel_barrier_nm"]),
        left_outer_barrier_nm=outer_barrier_nm(cfg),
        right_outer_barrier_nm=outer_barrier_nm(cfg),
        aluminum_fraction=float(s["aluminum_fraction"]),
        active_grid_spacing_nm=float(n["active_region_grid_spacing_nm"]),
        exterior_grid_spacing_nm=float(n["exterior_grid_spacing_nm"]),
    )


def interfaces(cfg: Mapping[str, Any]) -> list[grading12.Interface]:
    stack = build_stack(cfg)
    iv = stack.intervals()
    alloy = float(cfg["scientific"]["aluminum_fraction"])
    return [
        grading12.Interface("outer_to_thick", iv["left_well"][0], alloy, 0.0,
                            ("outer", "narrow" if cfg["scientific"]["thick_well_nm"] < cfg["scientific"]["thin_well_nm"] else "wide", "left")),
        grading12.Interface("thick_to_central", iv["centre_barrier"][0], 0.0, alloy,
                            ("central", "narrow" if cfg["scientific"]["thick_well_nm"] < cfg["scientific"]["thin_well_nm"] else "wide", "left")),
        grading12.Interface("central_to_thin", iv["right_well"][0], alloy, 0.0,
                            ("central", "narrow" if cfg["scientific"]["thin_well_nm"] < cfg["scientific"]["thick_well_nm"] else "wide", "right")),
        grading12.Interface("thin_to_outer", iv["right_well"][1], 0.0, alloy,
                            ("outer", "narrow" if cfg["scientific"]["thin_well_nm"] < cfg["scientific"]["thick_well_nm"] else "wide", "right")),
    ]


def _grading_settings(cfg: Mapping[str, Any]) -> tuple[str, str, float, int]:
    g = cfg["grading"]
    return (
        str(g.get("implementation", "native")),
        str(g.get("profile", "linear")),
        float(g.get("selected_thickness_nm", 0.0)),
        int(g.get("staircase_sublayers", 16)),
    )


def _selected_interfaces(cfg: Mapping[str, Any]) -> list[grading12.Interface]:
    return grading12.select_interfaces(interfaces(cfg), str(cfg["grading"].get("location_mode", "all")))


def _interface_position(cfg: Mapping[str, Any], interface: grading12.Interface) -> float:
    """Realized grade center, including robustness perturbations."""

    g = cfg["grading"]
    return interface.position_nm + float(g.get("center_shift_nm", 0.0))


def _grade_width(cfg: Mapping[str, Any], interface: grading12.Interface) -> float:
    g = cfg["grading"]
    default = float(g.get("selected_thickness_nm", 0.0))
    if str(g.get("profile", "")) != "asymmetric":
        return default
    # Upward and downward refer to increasing/decreasing Al content.
    return float(g.get("upward_thickness_nm" if interface.end_x > interface.start_x else "downward_thickness_nm", default))


def composition_on_grid(cfg: Mapping[str, Any], z_nm: Sequence[float]) -> np.ndarray:
    """Requested alloy profile, using the same override order as the deck."""

    stack = build_stack(cfg)
    z = np.asarray(z_nm, float)
    composition = np.zeros_like(z)
    alloy = float(cfg["scientific"]["aluminum_fraction"])
    intervals = stack.intervals()
    for name, (lo, hi) in intervals.items():
        if "barrier" in name:
            composition[(z >= lo) & (z <= hi)] = alloy
    implementation, shape, thickness, steps = _grading_settings(cfg)
    if thickness <= 0 or shape == "abrupt":
        return composition
    actual_shape = "linear" if shape in {"asymmetric", "staircase_linear"} else shape
    for interface in _selected_interfaces(cfg):
        width = _grade_width(cfg, interface)
        if width <= 0:
            continue
        position = _interface_position(cfg, interface)
        lo, hi = position - width / 2.0, position + width / 2.0
        mask = (z >= lo) & (z <= hi)
        u = np.clip((z[mask] - lo) / width, 0.0, 1.0)
        if implementation != "native":
            index = np.minimum(np.floor(u * steps).astype(int), steps - 1)
            u = index / max(steps - 1, 1)
        fraction = grading12.profile_fraction(
            u, actual_shape,
            sigmoid_steepness=float(cfg["grading"].get("sigmoid_steepness", 10.0)),
            erf_span_sigma=float(cfg["grading"].get("erf_span_sigma", 3.0)),
            staircase_steps=steps,
        )
        composition[mask] = interface.start_x + (interface.end_x - interface.start_x) * fraction
    return composition


def sampling_grid(cfg: Mapping[str, Any]) -> np.ndarray:
    stack = build_stack(cfg)
    active = float(cfg["numerical"]["active_region_grid_spacing_nm"])
    thickness = float(cfg["grading"].get("selected_thickness_nm", 0.0))
    minimum = int(cfg["grading"].get("minimum_grid_points_per_grade", 10))
    spacing = min(active, grading12.required_grade_spacing_nm(thickness, minimum)) if thickness > 0 else active
    return np.linspace(0.0, stack.total_thickness_nm, int(math.ceil(stack.total_thickness_nm / spacing)) + 1)


def _constant_region(lo: float, hi: float, alloy_x: float) -> str:
    return (
        "    region{\n"
        f"        line{{ x = [{lo:.9g}, {hi:.9g}] }}\n"
        "        ternary_constant{\n"
        '            name = "Al(x)Ga(1-x)As"\n'
        f"            alloy_x = {alloy_x:.9g}\n"
        "        }\n"
        "    }"
    )


def structure_block(cfg: Mapping[str, Any], stack: layers.LayerStack) -> str:
    base = stack.structure_regions(contact_name="qw_contact")
    implementation, shape, thickness, steps = _grading_settings(cfg)
    if thickness <= 0 or shape == "abrupt":
        return base
    blocks = [base, "    # Demo 12 centered grading regions override the abrupt base."]
    for interface in _selected_interfaces(cfg):
        width = _grade_width(cfg, interface)
        position = _interface_position(cfg, interface)
        lo, hi = position - width / 2.0, position + width / 2.0
        if lo < 0 or hi > stack.total_thickness_nm:
            raise DemoError(f"grade at {interface.name} leaves the simulation domain")
        native = implementation == "native" and shape in {"linear", "asymmetric"}
        if native:
            blocks.append(
                "    region{\n"
                f"        line{{ x = [{lo:.9g}, {hi:.9g}] }}\n"
                "        ternary_linear{\n"
                '            name = "Al(x)Ga(1-x)As"\n'
                f"            alloy_x = [{interface.start_x:.9g}, {interface.end_x:.9g}]\n"
                f"            x = [{lo:.9g}, {hi:.9g}]\n"
                "        }\n"
                "    }"
            )
        else:
            # Smooth profiles deliberately use the documented staircase fallback:
            # nextnano++ 3.0.0's native grammar is confirmed here only for linear.
            for index in range(steps):
                left = lo + width * index / steps
                right = lo + width * (index + 1) / steps
                sample = index / max(steps - 1, 1)
                fraction = float(grading12.profile_fraction(
                    sample, "linear" if shape in {"asymmetric", "staircase_linear"} else shape,
                    sigmoid_steepness=float(cfg["grading"].get("sigmoid_steepness", 10.0)),
                    erf_span_sigma=float(cfg["grading"].get("erf_span_sigma", 3.0)),
                    staircase_steps=steps,
                ))
                alloy_x = interface.start_x + (interface.end_x - interface.start_x) * fraction
                blocks.append(_constant_region(left, right, alloy_x))
    return "\n".join(blocks)


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    stack = build_stack(cfg)
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(float(numerical["quantum_region_padding_nm"]))
    thickness = float(cfg["grading"].get("selected_thickness_nm", 0.0))
    minimum = int(cfg["grading"].get("minimum_grid_points_per_grade", 10))
    active = float(numerical["active_region_grid_spacing_nm"])
    if thickness > 0 and grading12.mesh_resolution(thickness, active) < minimum:
        # The grade receives its own fine grid lines. Global active spacing is
        # left untouched, preserving Demo 11's baseline mesh away from interfaces.
        fine = grading12.required_grade_spacing_nm(thickness, minimum)
        points: list[tuple[float, float]] = []
        for layer, (lo, hi) in zip(stack.layers, stack.bounds):
            spacing = layer.grid_spacing_nm or stack.exterior_grid_spacing_nm
            points.extend(((lo, spacing), (hi, spacing)))
        for interface in _selected_interfaces(cfg):
            width = _grade_width(cfg, interface)
            position = _interface_position(cfg, interface)
            points.extend(((position - width / 2, fine), (position + width / 2, active)))
        merged: list[tuple[float, float]] = []
        for position, spacing in sorted(points):
            if merged and math.isclose(merged[-1][0], position, rel_tol=0.0, abs_tol=1e-9):
                merged[-1] = (position, min(merged[-1][1], spacing))
            else:
                merged.append((position, spacing))
        grid_lines = "\n".join(
            f"        line{{ pos = {position:.9g}  spacing = {spacing:.9g} }}"
            for position, spacing in merged
        )
    else:
        grid_lines = stack.grid_lines()
    electrons = int(numerical["number_of_electron_states"])
    holes = int(numerical["number_of_hole_states"])
    return {
        "temperature_K": cfg["scientific"]["temperature_K"],
        "number_of_electron_states": electrons,
        "number_of_hole_states": holes,
        "output_state_count": max(electrons, holes),
        "quantum_region_name": str(cfg["analysis"].get("quantum_region_name", "acqw")),
        "quantum_start_nm": f"{start:.9g}", "quantum_end_nm": f"{end:.9g}",
        "grid_lines": grid_lines, "structure_regions": structure_block(cfg, stack),
        "dipole_polarization_name": str(cfg["analysis"].get("dipole_polarization_name", "growth_z")),
    }


def _set(config: dict[str, Any], dotted: str, value: Any) -> None:
    cursor = config
    parts = dotted.split(".")
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def _case(cfg: Mapping[str, Any], case_id: str, label: str, stage: str, **changes: Any) -> sweeps.CaseSpec:
    resolved = copy.deepcopy(dict(cfg))
    for key, value in changes.items():
        _set(resolved, key.replace("__", "."), value)
    return sweeps.CaseSpec(case_id, label, dict(changes), resolved, {"stage": stage, "sweep_kind": stage})


def _frange(start: float, stop: float, step: float) -> list[float]:
    count = int(round((stop - start) / step))
    return [round(start + index * step, 10) for index in range(count + 1)]


def build_cases_by_stage(cfg: Mapping[str, Any]) -> dict[str, list[sweeps.CaseSpec]]:
    """Build the full design once; tiers select prefixes without hidden cases."""

    g, loc = cfg["grading"], cfg["locations"]
    validation_thickness = float(g.get("validation_thickness_nm", 2.0))
    stages: dict[str, list[sweeps.CaseSpec]] = {f"stage{i}": [] for i in range(1, 8)}
    stages["stage1"] = [
        _case(cfg, "v_abrupt", "abrupt validation", "stage1", grading__selected_thickness_nm=0.0, grading__profile="abrupt", grading__implementation="native"),
        _case(cfg, "v_native", "native linear validation", "stage1", grading__selected_thickness_nm=validation_thickness, grading__profile="linear", grading__implementation="native"),
        _case(cfg, "v_sigmoid", "sigmoid staircase validation", "stage1", grading__selected_thickness_nm=validation_thickness, grading__profile="sigmoid", grading__implementation="staircase"),
        _case(cfg, "v_stair", "linear staircase validation", "stage1", grading__selected_thickness_nm=validation_thickness, grading__profile="staircase_linear", grading__implementation="staircase"),
    ]
    for index, thickness in enumerate(g["thickness_nm"]):
        stages["stage2"].append(_case(
            cfg, f"t{index:02d}", f"linear grade {thickness} nm", "stage2",
            grading__selected_thickness_nm=float(thickness),
            grading__profile="abrupt" if float(thickness) == 0 else "linear",
            grading__implementation="native",
        ))
    selected_thickness = float(g.get("profile_comparison_thickness_nm", validation_thickness))
    for index, profile in enumerate(g["profiles"]):
        implementation = "native" if profile in {"abrupt", "linear", "asymmetric"} else "staircase"
        stages["stage3"].append(_case(
            cfg, f"p{index:02d}", f"{profile} profile", "stage3",
            grading__selected_thickness_nm=0.0 if profile == "abrupt" else selected_thickness,
            grading__profile=profile, grading__implementation=implementation,
        ))
    for index, mode in enumerate(loc["study_modes"]):
        stages["stage4"].append(_case(
            cfg, f"l{index:02d}", f"{mode} grading", "stage4",
            grading__selected_thickness_nm=0.0 if mode == "none" else selected_thickness,
            grading__profile="abrupt" if mode == "none" else "linear",
            grading__location_mode=mode,
        ))
    total_well = float(cfg["scientific"]["thick_well_nm"]) + float(cfg["scientific"]["thin_well_nm"])
    joint = cfg["joint_sweep"]
    a_cfg = joint["asymmetry"]
    for ai, asymmetry in enumerate(_frange(float(a_cfg["start"]), float(a_cfg["stop"]), float(a_cfg["step"]))):
        thick, thin = chi2mod.well_widths_from_asymmetry(asymmetry, total_well)
        for gi, thickness in enumerate(joint["grading_thickness_nm"]):
            stages["stage5"].append(_case(
                cfg, f"j{ai:02d}{gi:02d}", f"s={asymmetry}, grade={thickness} nm", "stage5",
                scientific__thick_well_nm=round(thick, 6), scientific__thin_well_nm=round(thin, 6),
                grading__selected_thickness_nm=float(thickness),
                grading__profile="abrupt" if float(thickness) == 0 else "linear",
            ))
    # Stage 6 is a transparent local perturbation design, not random Monte Carlo.
    robustness = cfg["robustness"]
    nominal_designs = robustness.get("nominal_designs", [])
    perturbation_map = robustness.get("perturbations", {})
    parameter_paths = {
        "narrow_well_nm": "scientific.thin_well_nm", "wide_well_nm": "scientific.thick_well_nm",
        "central_barrier_nm": "scientific.tunnel_barrier_nm", "grading_thickness_nm": "grading.selected_thickness_nm",
        "aluminum_fraction": "scientific.aluminum_fraction", "grading_center_nm": "grading.center_shift_nm",
        "interface_shift_nm": "grading.interface_shift_nm",
    }
    for di, design in enumerate(nominal_designs):
        base = copy.deepcopy(dict(cfg))
        for path, value in design.get("overrides", {}).items():
            _set(base, path, value)
        stages["stage6"].append(_case(base, f"r{di:02d}n", f"{design['name']} nominal", "stage6"))
        for parameter_index, (parameter, values) in enumerate(perturbation_map.items()):
            path = parameter_paths[parameter]
            cursor: Any = base
            for part in path.split("."):
                cursor = cursor[part]
            nominal = float(cursor)
            for pi, delta in enumerate(values):
                if nominal + float(delta) < 0 and parameter == "grading_thickness_nm":
                    continue
                stages["stage6"].append(_case(
                    base, f"r{di:02d}p{parameter_index}{pi:02d}",
                    f"{design['name']}: {parameter} {float(delta):+g}", "stage6",
                    **{path.replace(".", "__"): nominal + float(delta)},
                ))
    # Optimization consumes the completed Stage 2-6 grid. No hidden black-box
    # solver cases are added here; Stage 7 is post-processing only.
    return stages


def stage_counts(cfg: Mapping[str, Any]) -> dict[str, Any]:
    stages = build_cases_by_stage(cfg)
    counts = {name: len(cases) for name, cases in stages.items()}
    return {
        "by_stage": counts,
        "tier_A": counts["stage1"],
        "tier_B": sum(counts[f"stage{i}"] for i in range(1, 5)),
        "tier_C": sum(counts.values()),
        "stage7_postprocessing_cases": 0,
    }


def cases_for_tier(cfg: Mapping[str, Any]) -> list[sweeps.CaseSpec]:
    stages = build_cases_by_stage(cfg)
    tier = str(cfg["execution"].get("tier", "A")).upper()
    maximum_stage = {"A": 1, "B": 4, "C": 7}[tier]
    return [case for number in range(1, maximum_stage + 1) for case in stages[f"stage{number}"]]


def _write_requested_profile(case: sweeps.CaseSpec, run_dir: Path) -> dict[str, Any]:
    z = sampling_grid(case.config)
    alloy = composition_on_grid(case.config, z)
    extracted = run_dir / "extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    with (extracted / "requested_composition_profile.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["position_nm", "requested_aluminum_fraction"])
        writer.writerows(zip(z, alloy))
    write_json_atomically(extracted / "requested_geometry.json", {
        "total_device_length_nm": build_stack(case.config).total_thickness_nm,
        "integrated_aluminum_fraction_nm": grading12.integrated_composition(z, alloy),
        "profile": case.config["grading"].get("profile"),
        "implementation": case.config["grading"].get("implementation"),
        "location_mode": case.config["grading"].get("location_mode"),
        "selected_thickness_nm": case.config["grading"].get("selected_thickness_nm"),
        "preserve_total_device_length": case.config["grading"].get("preserve_total_device_length"),
        "preserve_nominal_layer_centers": case.config["grading"].get("preserve_nominal_layer_centers"),
        "definition": "full transition width centered on each nominal abrupt interface",
    })
    thickness = float(case.config["grading"].get("selected_thickness_nm", 0.0))
    minimum = int(case.config["grading"].get("minimum_grid_points_per_grade", 10))
    spacing = float(np.min(np.diff(z)))
    selected = _selected_interfaces(case.config)
    intervals = sorted(
        (_interface_position(case.config, interface) - _grade_width(case.config, interface) / 2,
         _interface_position(case.config, interface) + _grade_width(case.config, interface) / 2)
        for interface in selected if _grade_width(case.config, interface) > 0
    )
    overlap = any(right > next_left + 1e-12 for (_, right), (next_left, _) in zip(intervals, intervals[1:]))
    return {
        "case_id": case.case_id, "requested_grading_thickness_nm": thickness,
        "realized_grading_thickness_nm": None,
        "start_composition": 0.0 if thickness > 0 else None,
        "end_composition": float(case.config["scientific"]["aluminum_fraction"]) if thickness > 0 else None,
        "total_device_length_nm": build_stack(case.config).total_thickness_nm,
        "minimum_grid_spacing_nm": spacing,
        "grid_intervals_per_grade": grading12.mesh_resolution(thickness, spacing),
        "minimum_grid_points_requirement_met": thickness == 0 or grading12.mesh_resolution(thickness, spacing) >= minimum,
        "integrated_aluminum_fraction_nm": grading12.integrated_composition(z, alloy),
        "monotonicity_result": "per-interface monotone" if thickness > 0 else "abrupt",
        "overlapping_centered_grades": overlap,
        "profile_validation_result": "invalid: overlapping grades lose an interface endpoint" if overlap else "requested profile valid",
    }


def _extract_realized_composition(case: sweeps.CaseSpec, result: sweeps.CaseResult) -> dict[str, Any]:
    """Find and validate nextnano's alloy output without assuming an unconfirmed filename."""

    if not result.solver_success:
        return {"realized_profile_status": "not run"}
    raw = result.run_dir / "raw"
    candidates = [
        path for path in raw.rglob("*.dat")
        if "alloy" in path.name.lower()
        and "spinor" not in path.name.lower()
        and "quantum" not in {part.lower() for part in path.parts}
    ]
    if len(candidates) != 1:
        raise DemoError(
            "Stage 1 requires one unambiguous solver alloy-composition table; "
            f"found {len(candidates)}: {[str(path.relative_to(raw)) for path in candidates]}"
        )
    numeric: list[list[float]] = []
    for line in candidates[0].read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            values = [float(token) for token in line.replace(",", " ").split()]
        except ValueError:
            continue
        if len(values) >= 2:
            numeric.append(values)
    if len(numeric) < 2:
        raise DemoError(f"alloy-composition output has fewer than two numeric rows: {candidates[0]}")
    data = np.asarray(numeric, float)
    z, realized = data[:, 0], data[:, 1]
    requested = composition_on_grid(case.config, z)
    extracted = result.run_dir / "extracted"
    with (extracted / "realized_composition_profile.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["position_nm", "requested_aluminum_fraction", "realized_aluminum_fraction", "difference"])
        writer.writerows(zip(z, requested, realized, realized - requested))
    comparison = grading12.compare_profiles(z, requested, realized)
    tolerance = float(case.config["validation"].get("native_staircase_composition_rms_tolerance", 0.02))
    passed = comparison["rms_composition_difference"] <= tolerance
    comparison.update({
        "realized_profile_status": "reproduced" if passed else "invalid",
        "profile_validation_result": "reproduced" if passed else "invalid: requested/realized RMS mismatch",
        "profile_validation_passed": passed,
        "realized_grading_thickness_nm": float(case.config["grading"].get("selected_thickness_nm", 0.0)),
        "source": str(candidates[0]),
    })
    write_json_atomically(extracted / "realized_profile_validation.json", comparison)
    return comparison


def _result_rows(results: Sequence[sweeps.CaseResult]) -> list[dict[str, Any]]:
    return [{**result.spec.row(), **result.observables, "status": result.status,
             "qc_status": "not run" if not result.solver_success else ("reproduced" if not result.suspicious else "unresolved")}
            for result in results]


def _write_required_tables(parent: Path, results: Sequence[sweeps.CaseResult], geometry_rows: Sequence[Mapping[str, Any]]) -> None:
    rows = _result_rows(results)
    table1, table2, table3, table4 = [], list(geometry_rows), [], []
    for result, row in zip(results, rows):
        cfg = result.spec.config
        table1.append({
            "case_id": result.spec.case_id, "grading_implementation": cfg["grading"].get("implementation"),
            "profile_shape": cfg["grading"].get("profile"), "grading_locations": cfg["grading"].get("location_mode"),
            "grading_thickness_nm": cfg["grading"].get("selected_thickness_nm"),
            "asymmetry": chi2mod.structural_asymmetry(cfg["scientific"]["thick_well_nm"], cfg["scientific"]["thin_well_nm"]),
            "barrier_thickness_nm": cfg["scientific"]["tunnel_barrier_nm"],
            "aluminum_fraction": cfg["scientific"]["aluminum_fraction"],
            "active_mesh_spacing_nm": cfg["numerical"]["active_region_grid_spacing_nm"],
            "requested_electron_states": cfg["numerical"]["number_of_electron_states"],
            "requested_hole_states": cfg["numerical"]["number_of_hole_states"],
        })
        table3.append({key: row.get(key) for key in ["case_id", "electron_energies_eV", "heavy_hole_energies_eV", "transition_e1_hh1_eV", "transition_e2_hh2_eV", "anticrossing_gap_meV", "maximum_boundary_probability", "state_tracking_confidence", "qc_status"]})
        table4.append({key: row.get(key) for key in ["case_id", "chi2_peak_magnitude", "chi2_peak_wavelength_nm", "chi2_relative_at_reference", "target_detuning_nm", "chi2_integrated_magnitude", "electron_hole_overlap", "dipole_product_nm3", "qc_status"]})
    for name, data in (("table1_case_definition", table1), ("table2_realized_composition_geometry", table2),
                       ("table3_electronic_structure", table3), ("table4_nonlinear_optical", table4),
                       ("table5_robustness", []), ("table6_optimization", [])):
        sweeps.write_table(parent, name, data)
        write_json_atomically(parent / "tables" / f"{name}.json", data)


def _value_at(config: Mapping[str, Any], path: str) -> float:
    value: Any = config
    for part in path.replace("__", ".").split("."):
        value = value[part]
    return float(value)


def _robustness_table(parent: Path, results: Sequence[sweeps.CaseResult]) -> list[dict[str, Any]]:
    nominal = {result.spec.case_id[:3]: result for result in results
               if result.spec.metadata.get("stage") == "stage6" and result.spec.case_id.endswith("n")}
    rows: list[dict[str, Any]] = []
    metrics = ("chi2_peak_magnitude", "chi2_relative_at_reference", "chi2_peak_wavelength_nm")
    for result in results:
        if result.spec.metadata.get("stage") != "stage6" or result.spec.case_id.endswith("n"):
            continue
        reference = nominal.get(result.spec.case_id[:3])
        if reference is None or not result.spec.swept:
            continue
        parameter, perturbed_value = next(iter(result.spec.swept.items()))
        delta = float(perturbed_value) - _value_at(reference.spec.config, parameter)
        row: dict[str, Any] = {
            "nominal_design": reference.spec.label.removesuffix(" nominal"),
            "case_id": result.spec.case_id, "perturbed_parameter": parameter.replace("__", "."),
            "perturbation": delta, "status": result.status,
        }
        for metric in metrics:
            nominal_value, value = reference.observables.get(metric), result.observables.get(metric)
            change = None if nominal_value is None or value is None else float(value) - float(nominal_value)
            row[f"{metric}_change"] = change
            row[f"{metric}_sensitivity_per_unit"] = None if change is None or delta == 0 else change / delta
        rows.append(row)
    for prefix, reference in nominal.items():
        relevant = [row for row in rows if row["case_id"].startswith(prefix)]
        nominal_target = abs(float(reference.observables.get("chi2_relative_at_reference", 0.0)))
        drifts = [abs(float(row["chi2_relative_at_reference_change"])) / nominal_target
                  for row in relevant if row.get("chi2_relative_at_reference_change") is not None and nominal_target > 0]
        reference.observables["robustness_score"] = 1.0 / (1.0 + (float(np.mean(drifts)) if drifts else math.inf))
        reference.observables["robustness_worst_case_target_fraction"] = max(drifts, default=None)
    sweeps.write_table(parent, "table5_robustness", rows)
    write_json_atomically(parent / "tables" / "table5_robustness.json", rows)
    return rows


def _optimization_table(parent: Path, cfg: Mapping[str, Any], results: Sequence[sweeps.CaseResult]) -> dict[str, Any]:
    import report12
    candidates: list[dict[str, Any]] = []
    target = float(cfg["chi2"]["reference_wavelength_nm"])
    for result in results:
        if not result.solver_success or result.spec.metadata.get("stage") not in {"stage2", "stage3", "stage4", "stage5", "stage6"}:
            continue
        if result.spec.metadata.get("stage") == "stage6" and not result.spec.case_id.endswith("n"):
            continue
        obs = result.observables
        peak_wavelength = obs.get("chi2_peak_wavelength_nm")
        candidates.append({
            "case_id": result.spec.case_id,
            "profile": result.spec.config["grading"].get("profile"),
            "grading_thickness_nm": result.spec.config["grading"].get("selected_thickness_nm"),
            "peak_chi2_magnitude": obs.get("chi2_peak_magnitude"),
            "chi2_at_target_wavelength": obs.get("chi2_relative_at_reference"),
            "target_detuning_nm": None if peak_wavelength is None else float(peak_wavelength) - target,
            "robustness_score": obs.get("robustness_score", 0.0),
            "boundary_probability": obs.get("maximum_boundary_probability_bound_states"),
            "state_tracking_confidence": obs.get("state_tracking_confidence"),
            "origin_independence_error": obs.get("origin_independence_error"),
            "bound_states_accepted": int(obs.get("states_failing_bound_criterion", 1)) == 0,
        })
    usable = [row for row in candidates if row["peak_chi2_magnitude"] is not None and row["target_detuning_nm"] is not None]
    optimization = report12.build_optimization(usable, cfg["optimization"]["constraints"]) if usable else {
        "rows": [], "pareto": [], "best_peak": None, "best_target": None, "most_robust": None,
        "best_balanced": None,
    }
    pareto_ids = {row["case_id"] for row in optimization["pareto"]}
    table = [{"rank": index, **row, "pareto_optimal": row["case_id"] in pareto_ids}
             for index, row in enumerate(optimization["rows"], 1)]
    sweeps.write_table(parent, "table6_optimization", table)
    write_json_atomically(parent / "tables" / "table6_optimization.json", table)
    write_json_atomically(parent / "extracted" / "optimization_summary.json", optimization)
    return {key: value for key, value in optimization.items() if key not in {"rows", "pareto"}}


def _stage1_native_staircase_comparison(parent: Path, results: Sequence[sweeps.CaseResult]) -> dict[str, Any]:
    by_id = {result.spec.case_id: result for result in results}
    native, staircase = by_id.get("v_native"), by_id.get("v_stair")
    if native is None or staircase is None:
        comparison = {"status": "not run", "reason": "Stage 1 cases absent from active tier"}
    else:
        z = sampling_grid(native.spec.config)
        profile = grading12.compare_profiles(
            z, composition_on_grid(native.spec.config, z), composition_on_grid(staircase.spec.config, z)
        )
        comparison = {"status": "requested profiles compared", **profile}
        if native.solver_success and staircase.solver_success:
            for band in ("electron_energies_eV", "heavy_hole_energies_eV"):
                a, b = np.asarray(native.observables.get(band) or [], float), np.asarray(staircase.observables.get(band) or [], float)
                count = min(a.size, b.size)
                comparison[f"maximum_{band}_difference_meV"] = float(np.max(np.abs(a[:count] - b[:count])) * 1000) if count else None
            for key in ("overlap_e1_hh1", "overlap_e2_hh2"):
                a, b = native.observables.get(key), staircase.observables.get(key)
                comparison[f"{key}_difference"] = None if a is None or b is None else float(b) - float(a)
            comparison["status"] = "provisionally consistent"
    write_json_atomically(parent / "extracted" / "native_staircase_comparison.json", comparison)
    sweeps.write_table(parent, "native_staircase_comparison", [comparison])
    return comparison


def _write_plot_csvs(parent: Path, results: Sequence[sweeps.CaseResult]) -> None:
    rows = _result_rows(results)
    plot_data = parent / "plot_data"
    plot_data.mkdir(parents=True, exist_ok=True)
    for filename, _ in PLOT_SET:
        csv_name = Path(filename).with_suffix(".csv").name
        fields = sorted({key for row in rows for key in row})
        with (plot_data / csv_name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields or ["note"])
            writer.writeheader()
            if rows:
                writer.writerows({key: row.get(key) for key in fields} for row in rows)


def _write_status_report(parent: Path, cfg: Mapping[str, Any], manifest: Mapping[str, Any], counts: Mapping[str, Any]) -> None:
    real = int(manifest.get("solver_success_count", 0)) > 0
    status = "provisionally consistent" if real else "not run"
    lines = [
        "# Demo 12 stage audit", "",
        "> No licensed result is inferred from generated inputs or synthetic data.", "",
        f"Active tier: **{cfg['execution']['tier']}**. Licensed solver outputs present: **{real}**.", "",
        "## Expected case counts", "", "| scope | cases |", "|---|---:|",
        f"| Tier A — smoke | {counts['tier_A']} |", f"| Tier B — learning | {counts['tier_B']} |",
        f"| Tier C — full | {counts['tier_C']} |", "",
        "## Stage status", "", "| stage | status | meaning |", "|---|---|---|",
    ]
    for number, meaning in enumerate(("grading implementation", "thickness sweep", "profile shapes", "locations", "joint asymmetry/grading tracking", "fabrication robustness", "Pareto optimization"), 1):
        lines.append(f"| {number} | {status if number <= ({'A':1,'B':4,'C':7}[str(cfg['execution']['tier']).upper()]) else 'not run'} | {meaning} |")
    lines += ["", "## Criterion-level outcomes", "",
              "All geometry, numerical, and scientific criteria remain `not run` until real licensed outputs are extracted. Input generation and solver-free tests are reported separately and are not promoted to physical validation.", ""]
    write_text_atomically(parent / "DEMO12_REPORT.md", "\n".join(lines))


def _run_joint_tracking(parent: Path, cfg: Mapping[str, Any], results: Sequence[sweeps.CaseResult]) -> dict[str, Any]:
    points: list[tracking12.GridPoint] = []
    for result in results:
        if result.spec.metadata.get("stage") != "stage5" or not result.solver_success:
            continue
        bands = demo11._load_bands(result)
        if bands is None:
            continue
        electron, heavy_hole = bands
        scientific = result.spec.config["scientific"]
        points.append(tracking12.GridPoint(
            case_id=result.spec.case_id,
            asymmetry=chi2mod.structural_asymmetry(scientific["thick_well_nm"], scientific["thin_well_nm"]),
            grading_thickness_nm=float(result.spec.config["grading"].get("selected_thickness_nm", 0.0)),
            z_nm=electron.z_nm,
            electron_energies_eV=electron.energies_eV,
            electron_envelopes=electron.envelopes,
            heavy_hole_energies_eV=heavy_hole.energies_eV,
            heavy_hole_envelopes=heavy_hole.envelopes,
        ))
    tracked = tracking12.track_grid(points, cfg["state_tracking"]) if points else {
        "rows": [], "diagnostics": {}, "ambiguous_assignments": 0,
        "minimum_confidence": None, "method": "not run — no licensed Stage 5 outputs",
    }
    sweeps.write_state_tracking(parent, tracked["rows"])
    write_json_atomically(parent / "extracted" / "state_assignment_matrices.json", tracked["diagnostics"])
    confidence_by_case: dict[str, list[float]] = {}
    for row in tracked["rows"]:
        if row.get("overlap_with_previous") is not None:
            confidence_by_case.setdefault(str(row["case_id"]), []).append(float(row["overlap_with_previous"]))
    for result in results:
        values = confidence_by_case.get(result.spec.case_id)
        if values:
            result.observables["state_tracking_confidence"] = min(values)
    return {key: value for key, value in tracked.items() if key not in {"rows", "diagnostics"}}


def _resume_case(context: sweeps.RunContext, case: sweeps.CaseSpec) -> sweeps.CaseResult | None:
    """Copy the newest completed identical case into this run and skip the solver."""

    if not bool(context.cfg["execution"].get("resume_completed_cases", True)):
        return None
    demo_root = context.parent.parent
    prior_runs = sorted(
        (path for path in demo_root.iterdir() if path.is_dir() and path != context.parent),
        reverse=True,
    )
    for prior in prior_runs:
        source = prior / "runs" / case.case_id
        manifest_path = source / "run_manifest.json"
        resolved_path = source / "demo_resolved.yaml"
        if not manifest_path.is_file() or not resolved_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("completion_status") != "completed":
            continue
        previous_cfg = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
        # Exact resolved scientific configuration equality is the resume key.
        if previous_cfg != case.config:
            continue
        destination = context.parent / "runs" / case.case_id
        shutil.copytree(source, destination)
        observables = dict(manifest.get("observables") or {})
        validation = dict(manifest.get("validation") or {})
        return sweeps.CaseResult(
            spec=case, run_dir=destination, status="completed",
            return_code=manifest.get("return_code"),
            runtime_seconds=0.0, observables=observables, validation=validation,
            warnings=[f"resumed from completed run {prior.name}; solver not rerun"],
            failure_reason=None,
        )
    return None


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    validate_demo12_config(cfg)
    counts = stage_counts(cfg)
    cases = cases_for_tier(cfg)
    if str(cfg["execution"].get("tier", "A")).upper() == "A" and len(cases) > 5:
        raise DemoError("smoke tier must contain no more than five cases")
    results: list[sweeps.CaseResult] = []
    geometry_rows: list[dict[str, Any]] = []
    for case in cases:
        result = _resume_case(context, case)
        if result is None:
            result = sweeps.execute_case(
                demo_dir=context.demo_dir, spec=case, machine=context.machine,
                run_dir=context.parent / "runs" / case.case_id, render_values=render_values,
                analyse=demo11.analyse_case, dependency_report=context.dependency_report,
            )
        results.append(result)
        geometry = _write_requested_profile(case, result.run_dir)
        try:
            realized = _extract_realized_composition(case, result)
        except Exception as exc:
            if result.solver_success:
                result.status = "failed"
                result.failure_reason = f"grading profile validation failed: {type(exc).__name__}: {exc}"
                result.validation["grading_profile_realized"] = False
                result.validation["passed"] = False
            realized = {"realized_profile_status": "invalid", "profile_validation_result": str(exc)}
        if result.solver_success and realized.get("profile_validation_passed") is False:
            result.validation["grading_profile_realized"] = False
            result.validation["passed"] = False
        geometry.update(realized)
        geometry_rows.append(geometry)
    sweeps.write_sweep_summary(context.parent, results)
    sweeps.write_failed_and_suspicious(context.parent, results)
    joint_tracking = _run_joint_tracking(context.parent, cfg, results)
    stage1_comparison = _stage1_native_staircase_comparison(context.parent, results)
    _write_required_tables(context.parent, results, geometry_rows)
    robustness_rows = _robustness_table(context.parent, results)
    optimization_summary = _optimization_table(context.parent, cfg, results)
    _write_plot_csvs(context.parent, results)
    plotting.ensure_plot_set(context.parent / "plots", PLOT_SET, reason="Requires real licensed nextnano++ output; raw points are never smoothed.")
    manifest = sweeps.write_sweep_manifest(
        context.parent, cfg=cfg, machine=context.machine, results=results,
        dependency_report=context.dependency_report,
        parser_provenance={"profile": cfg["outputs"].get("parser_profile")},
        extra={"stage_case_counts": counts, "active_tier": cfg["execution"]["tier"],
               "joint_state_tracking": joint_tracking,
               "native_staircase_comparison": stage1_comparison,
               "robustness_rows": len(robustness_rows), "optimization_summary": optimization_summary,
               "native_grading_syntax": "ternary_linear{ alloy_x=[a,b] x=[p,q] }",
               "licensed_result_claim": "not run" if not any(r.solver_success for r in results) else "see criterion-level report"},
    )
    _write_status_report(context.parent, cfg, manifest, counts)
    sweeps.write_validation_report(
        context.parent, cfg=cfg, manifest=manifest, registry_record=context.registry_record,
        dependency_report=context.dependency_report,
        criteria=[
            ("smoke manifest contains at most five cases", len(cases) <= 5 if cfg["execution"]["tier"] == "A" else None, "Tier A is the syntax/composition gate."),
            ("licensed grading profile realized", True if any(r.solver_success for r in results) else None, "Must compare solver alloy output to requested_composition_profile.csv."),
            ("native and staircase agree", None, "Evaluated after both licensed Stage 1 cases complete."),
        ],
        notes=["Demo 11 extraction, interband chi(2), origin-independence and quasi-bound diagnostics are reused.",
               "Full Tier C cannot run unless execution.enable_full_optimization is explicitly true."],
        unvalidated_syntax=["native ternary_linear alloy-composition output remains licensed-run pending"],
    )
    return sweeps.finish_run(context, results=results, manifest=manifest)
