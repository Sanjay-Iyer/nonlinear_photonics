"""Demo 11 — validating this repository against a published paper.

Target: *Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells*,
Ramesh et al., arXiv:2602.23246v1.

This is a **validation** demo, not a discovery demo. Its job is to say, for each
claim in the paper, whether this repository reproduces it -- and, where it does
not, whether that is a defect here, a genuine physical difference, or something
the paper does not publish enough information to check.

The eight stages are run in order and each is allowed to fail independently:

    1  electronic structure of the published design
    2  numerical convergence of everything Stage 5 will consume
    3  asymmetry sweep at fixed total well thickness
    4  tunnelling-barrier sweep
    5  chi(2) via the paper's Eq. 2, in three clearly separated modes
    6  wavelength dependence, broad and telecom-focused
    7  abrupt versus graded interfaces
    8  the formal comparison report

The honest headline, stated here and in every report this demo writes: the
absolute chi(2) magnitude cannot be reproduced independently, because the paper
does not publish the HSE06 unit-cell matrix element, N_z, or the k-space
conventions. Energies, wavefunctions, resonance positions, and the asymmetry,
barrier and interface *trends* can be, and those are the real targets.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

import analysis
import chi2 as chi2mod
import layers
import outputs
import plots as plotting
import quantum1d
import report11
import sweeps
import tracking11
from demo_workflow import DemoError, write_csv, write_json_atomically

PAPER = "arXiv:2602.23246v1"

#: Stages whose cases vary the structural asymmetry. Stage 3 is the original
#: coarse sweep, kept for context; stage 3b resolves the discontinuity it found.
#: Defined in report11 so the report and the demo cannot drift apart.
ASYMMETRY_STAGES = report11.ASYMMETRY_STAGES

PLOT_SET: tuple[tuple[str, str], ...] = (
    ("composition_profile.png", "Layer composition profile"),
    ("band_edges_and_wavefunctions.png", "Paper-style band edges and wavefunctions"),
    ("transition_energy_comparison.png", "Transition energies versus the paper"),
    ("chi2_vs_asymmetry.png", "chi(2) versus structural asymmetry"),
    ("localization_vs_asymmetry.png", "State localisation versus asymmetry"),
    ("chi2_vs_barrier.png", "chi(2) versus tunnelling-barrier thickness"),
    ("chi2_broad_wavelength.png", "Broad wavelength response"),
    ("chi2_focused_wavelength.png", "Focused 1400-1800 nm response"),
    ("abrupt_vs_graded_composition.png", "Abrupt versus graded composition"),
    ("abrupt_vs_graded_bands.png", "Abrupt versus graded band structure"),
    ("paper_vs_simulation_chi2.png", "Paper versus simulation chi(2)"),
    ("convergence_summary.png", "Numerical convergence"),
    ("sensitivity.png", "Sensitivity of chi(2) to the unknown inputs"),
    ("validation_scorecard.png", "Final validation scorecard"),
    ("figure2d_comparison.png", "Paper Fig. 2d with this work overlaid"),
    ("figure2d_comparison_broad.png", "Paper Fig. 2d, full 400-1800 nm range"),
    # --- refined sweep and state tracking (Stage 3b) ------------------------
    ("chi2_metrics_vs_asymmetry.png", "Both chi(2) metrics versus asymmetry"),
    ("resonance_vs_asymmetry.png", "Resonance wavelength versus asymmetry"),
    ("refined_raw_index_branches.png", "Energy branches by raw solver index"),
    ("refined_tracked_branches.png", "Energy branches by tracked physical state"),
    ("refined_localization.png", "Tracked-state localisation versus asymmetry"),
    ("refined_assignment_overlap.png", "Adjacent-point assignment overlap"),
    ("refined_boundary_probability.png", "Boundary probability versus asymmetry"),
    ("refined_chi2_raw_vs_tracked.png", "Peak chi(2): raw index versus tracked states"),
)

#: How each comparison is classified in the report (Stage 8).
CLASSIFICATIONS = (
    "directly_reproduced",
    "qualitatively_reproduced",
    "calibrated_reproduction",
    "not_reproducible_from_available_information",
    "outside_nextnano_scope",
    "requires_author_data_or_code",
)


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def paper_targets(demo_dir: Path) -> dict[str, Any]:
    """Published values, kept apart from the simulation inputs on purpose."""

    path = demo_dir / "paper_targets.yaml"
    if not path.is_file():
        raise DemoError(f"paper_targets.yaml not found beside the demo: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if "targets" not in data:
        raise DemoError(f"{path} must contain a 'targets' mapping.")
    return data


def target_value(targets: Mapping[str, Any], name: str) -> float:
    try:
        return float(targets["targets"][name]["value"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DemoError(f"paper target {name!r} is missing or not numeric.") from exc


def outer_barrier_nm(cfg: Mapping[str, Any]) -> float:
    """Half the period barrier, plus any convergence padding."""

    return 0.5 * float(cfg["scientific"]["period_barrier_nm"]) + float(
        cfg["numerical"]["domain_padding_nm"]
    )


def build_stack(cfg: Mapping[str, Any]) -> layers.LayerStack:
    """AlGaAs / thick GaAs / AlGaAs / thin GaAs / AlGaAs, grown left to right."""

    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    return layers.asymmetric_double_well(
        left_well_width_nm=float(scientific["thick_well_nm"]),
        right_well_width_nm=float(scientific["thin_well_nm"]),
        centre_barrier_nm=float(scientific["tunnel_barrier_nm"]),
        left_outer_barrier_nm=outer_barrier_nm(cfg),
        right_outer_barrier_nm=outer_barrier_nm(cfg),
        aluminum_fraction=float(scientific["aluminum_fraction"]),
        active_grid_spacing_nm=float(numerical["active_region_grid_spacing_nm"]),
        exterior_grid_spacing_nm=float(numerical["exterior_grid_spacing_nm"]),
    )


def region_name(cfg: Mapping[str, Any]) -> str:
    return str((cfg.get("analysis") or {}).get("quantum_region_name", "acqw"))


def interface_positions_nm(stack: layers.LayerStack) -> list[tuple[float, float, float]]:
    """``(position, alloy_before, alloy_after)`` at each heterointerface."""

    intervals = stack.intervals()
    thick = intervals["left_well"]
    barrier = intervals["centre_barrier"]
    thin = intervals["right_well"]
    return [
        (thick[0], 1.0, 0.0),    # AlGaAs -> GaAs
        (barrier[0], 0.0, 1.0),  # GaAs   -> AlGaAs
        (thin[0], 1.0, 0.0),     # AlGaAs -> GaAs
        (thin[1], 0.0, 1.0),     # GaAs   -> AlGaAs
    ]


def structure_block(cfg: Mapping[str, Any], stack: layers.LayerStack) -> str:
    """Structure regions, with optional linear grading at each interface.

    Abrupt is the paper's ideal design. The graded model replaces each
    heterointerface with a ``ternary_linear`` ramp of width
    ``interface_grading_nm``, matching the paper's report that the measured EDS
    gradients were "mostly linear across 1 nm". Regions written later override
    earlier ones, so the ramps are laid over the abrupt structure rather than
    the layer widths being recomputed.
    """

    alloy = float(cfg["scientific"]["aluminum_fraction"])
    grading = float(cfg["scientific"]["interface_grading_nm"])
    base = stack.structure_regions(contact_name="qw_contact")
    if grading <= 0.0:
        return base

    domain = stack.total_thickness_nm
    blocks = [base]
    blocks.append(
        "    # Linear composition ramps replacing the abrupt heterointerfaces.\n"
        f"    # Width {grading:g} nm, matching the paper's EDS gradients."
    )
    for position, before, after in interface_positions_nm(stack):
        low = position - 0.5 * grading
        high = position + 0.5 * grading
        if low < 0.0 or high > domain:
            raise DemoError(
                f"a {grading} nm grading ramp at {position} nm leaves the "
                f"{domain} nm domain; widen the period barrier or reduce the grading."
            )
        blocks.append(
            "    region{\n"
            f"        line{{ x = [{low:.9g}, {high:.9g}] }}\n"
            "        ternary_linear{\n"
            '            name    = "Al(x)Ga(1-x)As"\n'
            f"            alloy_x = [{before * alloy:.9g}, {after * alloy:.9g}]\n"
            f"            x       = [{low:.9g}, {high:.9g}]\n"
            "        }\n"
            "    }"
        )
    return "\n".join(blocks)


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    stack = build_stack(cfg)
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(float(numerical["quantum_region_padding_nm"]))
    electrons = int(numerical["number_of_electron_states"])
    holes = int(numerical["number_of_hole_states"])
    if electrons < 2 or holes < 2:
        raise DemoError(
            "the paper's Eq. 2 uses the first two bound states of each band, so "
            "at least two electron and two heavy-hole states must be requested."
        )
    return {
        "temperature_K": cfg["scientific"]["temperature_K"],
        "number_of_electron_states": electrons,
        "number_of_hole_states": holes,
        "output_state_count": max(electrons, holes),
        "quantum_region_name": region_name(cfg),
        "quantum_start_nm": f"{start:.9g}",
        "quantum_end_nm": f"{end:.9g}",
        "grid_lines": stack.grid_lines(),
        "structure_regions": structure_block(cfg, stack),
        "dipole_polarization_name": str(
            (cfg.get("analysis") or {}).get("dipole_polarization_name", "growth_z")
        ),
    }


# ---------------------------------------------------------------------------
# per-case analysis
# ---------------------------------------------------------------------------


def _band_states(
    z_nm: np.ndarray, energies: np.ndarray, envelopes: np.ndarray, label: str
) -> chi2mod.BandStates:
    return chi2mod.BandStates(z_nm, energies, envelopes, label)


def _hole_states(
    profile: outputs.ParserProfile, raw: Path, region: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Heavy-hole energies and envelopes.

    nextnano++ lists hole states with DECREASING electron-scale energy, so index
    order is confinement order. That order is preserved: HH1 is the most
    confined hole, which is what the paper's ground interband transition uses.
    """

    resolved = outputs.resolve_outputs(
        profile,
        raw,
        ["energy_spectrum_hh", "envelopes_hh"],
        substitutions={"region": region},
    )
    outputs.require_or_diagnose(
        resolved,
        raw,
        ["energy_spectrum_hh", "envelopes_hh"],
        why="the heavy-hole band was requested in the quantum region",
    )
    _, energies = outputs.read_state_table(resolved.one("energy_spectrum_hh"))
    z_nm, envelopes = outputs.read_profile_table(resolved.one("envelopes_hh"))
    return z_nm, energies, envelopes


def chi2_settings(cfg: Mapping[str, Any], *, mode: str | None = None) -> chi2mod.Chi2Settings:
    metric = cfg.get("metric") or {}
    requested = str(mode or metric.get("mode", "relative"))
    kwargs: dict[str, Any] = {
        "mode": requested,
        "broadening_meV": float(metric.get("broadening_meV", 5.0)),
        "k_parallel_fraction_of_bz": float(
            metric.get("k_parallel_fraction_of_bz", 0.10)
        ),
        "k_parallel_points": int(metric.get("k_parallel_points", 96)),
        "lattice_constant_nm": float(metric.get("lattice_constant_nm", 0.565325)),
        "electron_mass_m0": float(metric.get("electron_mass_m0", 0.067)),
        "heavy_hole_inplane_mass_m0": float(
            metric.get("heavy_hole_inplane_mass_m0", 0.112)
        ),
        "spin_degeneracy": int(metric.get("spin_degeneracy", 2)),
        "max_states_per_band": int(metric.get("max_states_per_band", 2)),
    }
    if requested == "absolute":
        kwargs["r_e_hh_nm"] = metric.get("r_e_hh_nm")
        kwargs["n_wells_per_metre"] = metric.get("n_wells_per_metre")
    if requested == "calibrated":
        kwargs["calibration_target_pm_per_V"] = metric.get("calibration_target_pm_per_V")
        kwargs["calibration_wavelength_nm"] = metric.get("calibration_wavelength_nm")
        kwargs["calibration_source"] = str(metric.get("calibration_source", ""))
    return chi2mod.Chi2Settings(**kwargs)


def _quasi_bound_records(
    electron_states: Sequence[Any],
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    *,
    regions: Mapping[str, tuple[float, float]],
    states_in_sum: int,
    edge_fraction: float,
    maximum_boundary_probability: float,
    policy: str,
) -> dict[str, Any]:
    """Per-state confinement diagnostics for both bands.

    The bound-state test differs between the two bands, and pretending it does
    not would be the more misleading choice. Electrons get the full test from
    ``quantum1d.state_table``: energy below the enclosing barrier maximum *and*
    enough probability inside the wells. Heavy holes are solved here without a
    matching valence barrier-edge profile, so only the probability half is
    available, and each hole record says so rather than implying it passed a
    test that was never run.
    """

    if policy not in {"warn", "exclude", "fail_case"}:
        raise DemoError(
            f"unknown quasi_bound_state_policy {policy!r}; expected warn, exclude, "
            "or fail_case."
        )

    bound_by_index = {state.index: state for state in electron_states}
    records: list[dict[str, Any]] = []

    for band, label in ((electron, "electron"), (heavy_hole, "heavy_hole")):
        for index in range(band.count):
            density = band.envelopes[:, index] ** 2
            split = analysis.boundary_probability_split(
                band.z_nm, density, edge_fraction=edge_fraction
            )
            region_probabilities = {
                name: analysis.region_probability(band.z_nm, density, *bounds)
                for name, bounds in regions.items()
            }
            in_sum = index < states_in_sum
            exclusion: list[str] = []
            if not in_sum:
                exclusion.append(
                    f"state {index + 1} is beyond max_states_per_band="
                    f"{states_in_sum}, so Eq. 2 never sees it"
                )
            if label == "electron":
                state = bound_by_index.get(index + 1)
                passes = bool(state.bound) if state is not None else None
                criterion = state.bound_reason if state is not None else "not analysed"
            else:
                confined = sum(
                    value for name, value in region_probabilities.items() if "well" in name
                )
                passes = bool(confined >= 0.5)
                criterion = (
                    f"confined probability {confined:.4f}; no valence barrier-edge "
                    "profile is parsed for this band, so the energy half of the "
                    "bound-state test was not applied"
                )
            boundary_ok = split["boundary_probability"] <= maximum_boundary_probability
            if not boundary_ok:
                exclusion.append(
                    f"boundary probability {split['boundary_probability']:.3e} > "
                    f"{maximum_boundary_probability:.1e}"
                )
            if passes is False:
                exclusion.append(f"fails the bound-state criterion: {criterion}")
            fails = (passes is False) or (not boundary_ok)
            included = in_sum and not (fails and policy == "exclude")
            records.append(
                {
                    "band": label,
                    "state": index + 1,
                    "energy_eV": float(band.energies_eV[index]),
                    **split,
                    **{f"probability_{n}": v for n, v in region_probabilities.items()},
                    "passes_bound_criterion": passes,
                    "bound_criterion_detail": criterion,
                    "boundary_probability_within_threshold": bool(boundary_ok),
                    "within_chi2_state_window": bool(in_sum),
                    "included_in_chi2": bool(included),
                    "exclusion_reason": "; ".join(exclusion) or "",
                }
            )

    failing = [r for r in records if (r["passes_bound_criterion"] is False)
               or not r["boundary_probability_within_threshold"]]
    failing_in_sum = [r for r in failing if r["within_chi2_state_window"]]
    return {
        "policy": policy,
        "policy_effect": {
            "warn": "states are retained in Eq. 2 and the case is flagged",
            "exclude": "failing states are dropped from Eq. 2 and recorded",
            "fail_case": "the case is marked invalid",
        }[policy],
        "maximum_boundary_probability": float(maximum_boundary_probability),
        "boundary_edge_fraction": float(edge_fraction),
        "max_states_per_band": int(states_in_sum),
        "records": records,
        "failing_count": len(failing),
        "failing_in_sum_count": len(failing_in_sum),
        "failing_in_sum_reasons": [
            f"{r['band']} state {r['state']}: {r['exclusion_reason']}"
            for r in failing_in_sum
        ],
        "maximum_left": max([r["left_boundary_probability"] for r in records] or [0.0]),
        "maximum_right": max([r["right_boundary_probability"] for r in records] or [0.0]),
    }


def _excluded_band(
    band: chi2mod.BandStates, records: Sequence[Mapping[str, Any]], label: str
) -> chi2mod.BandStates:
    """Drop states the ``exclude`` policy rejected, preserving order."""

    keep = [
        r["state"] - 1
        for r in records
        if r["band"] == label and r["within_chi2_state_window"] and r["included_in_chi2"]
    ]
    if len(keep) == band.count or not keep:
        return band
    return chi2mod.BandStates(
        band.z_nm, band.energies_eV[keep], band.envelopes[:, keep], band.label
    )


def analyse_case(
    cfg: Mapping[str, Any], raw: Path, extracted: Path, plots_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse one run and evaluate everything Eq. 2 needs from it."""

    validation_cfg = cfg["validation"]
    analysis_cfg = cfg.get("analysis") or {}
    metric_cfg = cfg.get("metric") or {}
    stack = build_stack(cfg)
    regions = quantum1d.region_map(stack.intervals())
    window = stack.quantum_region_nm(float(cfg["numerical"]["quantum_region_padding_nm"]))
    profile = outputs.load_profile(
        str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
    )
    region = region_name(cfg)

    run = quantum1d.parse_one_band_run(
        raw,
        profile=profile,
        region_name=region,
        bandedge_columns=cfg["outputs"]["bandedge_columns"],
    )
    electron_states = quantum1d.state_table(
        run,
        regions=regions,
        minimum_confined_probability=float(
            validation_cfg.get("minimum_confined_probability", 0.5)
        ),
        normalisation_tolerance=float(validation_cfg.get("normalization_tolerance", 1e-3)),
        boundary_edge_fraction=float(analysis_cfg.get("boundary_edge_fraction", 0.05)),
        quantum_window_nm=window,
    )
    if run.envelopes is None:
        raise DemoError("electron envelopes are required for the Eq. 2 evaluation.")
    hole_z, hole_energies, hole_envelopes = _hole_states(profile, raw, region)

    if hole_z.shape != run.state_position_nm.shape or not np.allclose(
        hole_z, run.state_position_nm
    ):
        raise DemoError(
            "electron and heavy-hole envelopes are on different grids; the "
            "overlap integrals of Eq. 2 would be meaningless."
        )

    electron = _band_states(
        run.state_position_nm, run.energies_eV, run.envelopes, "e"
    )
    heavy_hole = _band_states(hole_z, hole_energies, hole_envelopes, "hh")

    observables: dict[str, Any] = {
        "thick_well_nm": float(cfg["scientific"]["thick_well_nm"]),
        "thin_well_nm": float(cfg["scientific"]["thin_well_nm"]),
        "tunnel_barrier_nm": float(cfg["scientific"]["tunnel_barrier_nm"]),
        "interface_grading_nm": float(cfg["scientific"]["interface_grading_nm"]),
        "aluminum_fraction": float(cfg["scientific"]["aluminum_fraction"]),
        "asymmetry": chi2mod.structural_asymmetry(
            float(cfg["scientific"]["thick_well_nm"]),
            float(cfg["scientific"]["thin_well_nm"]),
        ),
        "active_region_grid_spacing_nm": float(
            cfg["numerical"]["active_region_grid_spacing_nm"]
        ),
        "domain_padding_nm": float(cfg["numerical"]["domain_padding_nm"]),
        "quantum_region_padding_nm": float(cfg["numerical"]["quantum_region_padding_nm"]),
        "number_of_electron_states": int(cfg["numerical"]["number_of_electron_states"]),
        "grid_points": int(run.position_nm.size),
    }
    validation: dict[str, Any] = {}

    # --- Stage 1 observables ------------------------------------------------
    e_energies = electron.energies_eV
    h_energies = heavy_hole.energies_eV
    observables["electron_energies_eV"] = e_energies.tolist()
    observables["heavy_hole_energies_eV"] = h_energies.tolist()
    observables["E_e1_eV"] = float(e_energies[0])
    observables["E_e2_eV"] = float(e_energies[1]) if e_energies.size > 1 else None
    observables["E_hh1_eV"] = float(h_energies[0])
    observables["E_hh2_eV"] = float(h_energies[1]) if h_energies.size > 1 else None
    observables["transition_e1_hh1_eV"] = float(e_energies[0] - h_energies[0])
    if e_energies.size > 1 and h_energies.size > 1:
        observables["transition_e2_hh2_eV"] = float(e_energies[1] - h_energies[1])

    # --- orthonormality and origin independence -----------------------------
    observables["orthonormality_error_electron"] = electron.orthonormality_error()
    observables["orthonormality_error_heavy_hole"] = heavy_hole.orthonormality_error()
    tolerance = float(analysis_cfg.get("orthonormality_tolerance", 1e-3))
    validation["envelopes_orthonormal"] = bool(
        max(
            observables["orthonormality_error_electron"],
            observables["orthonormality_error_heavy_hole"],
        )
        <= tolerance
    )

    # --- matrix elements ----------------------------------------------------
    settings = chi2_settings(cfg)
    overlap_eh = chi2mod.overlap_matrix(electron, heavy_hole)
    z_e = chi2mod.position_matrix(electron)
    z_h = chi2mod.position_matrix(heavy_hole)
    observables["overlap_e1_hh1"] = float(overlap_eh[0, 0])
    if overlap_eh.shape[0] > 1 and overlap_eh.shape[1] > 1:
        observables["overlap_e2_hh2"] = float(overlap_eh[1, 1])
    observables["z_e1_e1_nm"] = float(z_e[0, 0])
    observables["z_hh1_hh1_nm"] = float(z_h[0, 0])
    if z_e.shape[0] > 1:
        observables["z_e1_e2_nm"] = float(z_e[0, 1])
        observables["z_e2_e2_nm"] = float(z_e[1, 1])
    if z_h.shape[0] > 1:
        observables["z_hh1_hh2_nm"] = float(z_h[0, 1])
        observables["z_hh2_hh2_nm"] = float(z_h[1, 1])
    # The paper's structural asymmetry shows up directly as a difference between
    # the electron and hole centroids.
    observables["electron_hole_centroid_separation_nm"] = float(z_e[0, 0] - z_h[0, 0])

    # --- localisation -------------------------------------------------------
    for index, state in enumerate(electron_states[:2], start=1):
        observables[f"electron{index}_thick_well_probability"] = (
            state.region_probabilities.get("left_well")
        )
        observables[f"electron{index}_thin_well_probability"] = (
            state.region_probabilities.get("right_well")
        )
    observables["maximum_boundary_probability_bound_states"] = max(
        [state.boundary_probability for state in electron_states if state.bound] or [0.0]
    )

    # --- state-resolved quasi-bound diagnostics ------------------------------
    # A single maximum across all states cannot say WHICH state is leaking or
    # which way, and those are different defects with different fixes. Every
    # state used by Eq. 2 is recorded individually, including the ones that
    # pass.
    quasi_bound = _quasi_bound_records(
        electron_states,
        electron,
        heavy_hole,
        regions=regions,
        states_in_sum=int(settings.max_states_per_band),
        edge_fraction=float(analysis_cfg.get("boundary_edge_fraction", 0.05)),
        maximum_boundary_probability=float(
            validation_cfg.get("maximum_boundary_probability", 1e-3)
        ),
        policy=str(validation_cfg.get("quasi_bound_state_policy", "warn")),
    )
    observables["quasi_bound_policy"] = quasi_bound["policy"]
    observables["states_failing_bound_criterion"] = quasi_bound["failing_count"]
    observables["states_failing_bound_criterion_in_chi2_sum"] = quasi_bound[
        "failing_in_sum_count"
    ]
    observables["maximum_left_boundary_probability"] = quasi_bound["maximum_left"]
    observables["maximum_right_boundary_probability"] = quasi_bound["maximum_right"]
    write_json_atomically(extracted / "quasi_bound_states.json", quasi_bound)
    if quasi_bound["records"]:
        write_csv(
            extracted / "quasi_bound_states.csv",
            {
                key: np.asarray([row.get(key) for row in quasi_bound["records"]])
                for key in quasi_bound["records"][0]
            },
        )
    if quasi_bound["policy"] == "fail_case" and quasi_bound["failing_in_sum_count"]:
        raise DemoError(
            "quasi_bound_state_policy is 'fail_case' and "
            f"{quasi_bound['failing_in_sum_count']} state(s) entering Eq. 2 fail the "
            "bound-state criterion: "
            + "; ".join(quasi_bound["failing_in_sum_reasons"])
        )

    # --- Eq. 2 at the reference wavelength ----------------------------------
    reference_nm = float(metric_cfg.get("reference_wavelength_nm", 1550.0))
    # A symmetric structure has chi(2) = 0 by parity, so both the reference and
    # the origin-shifted spectrum are rounding noise there. The check picks the
    # comparison that is defensible for the magnitude actually present and
    # records which one it used; it never divides by a near-zero chi(2), and it
    # never lets a near-zero case through without an absolute check.
    try:
        origin_check = chi2mod.origin_independence(
            electron,
            heavy_hole,
            [float(chi2mod.photon_energy_eV(reference_nm))],
            settings,
            shift_nm=float(analysis_cfg.get("origin_independence_shift_nm", 100.0)),
            absolute_tolerance=float(
                analysis_cfg.get(
                    "origin_independence_absolute_tolerance",
                    chi2mod.DEFAULT_ORIGIN_ABSOLUTE_TOLERANCE,
                )
            ),
            relative_tolerance=float(
                analysis_cfg.get("maximum_origin_dependence", 1e-6)
            ),
            scale_floor=float(
                analysis_cfg.get(
                    "origin_independence_scale_floor",
                    chi2mod.DEFAULT_ORIGIN_SCALE_FLOOR,
                )
            ),
        )
    except chi2mod.Chi2Error as exc:
        observables["origin_independence_reason"] = str(exc)
        observables["origin_independence_error"] = float("nan")
        observables["origin_independence_comparison_mode"] = "not_evaluated"
        validation["chi2_origin_independent"] = False
    else:
        observables.update(origin_check.as_record())
        # Kept under its historical name so older tables stay comparable: the
        # relative residual where one is defined, the absolute one where it is
        # not. The comparison mode alongside it says which.
        observables["origin_independence_error"] = (
            origin_check.relative_residual
            if origin_check.relative_residual is not None
            else origin_check.absolute_residual
        )
        validation["chi2_origin_independent"] = bool(origin_check.passed)

    focused = metric_cfg.get("focused_wavelength_nm", [1400.0, 1800.0])
    focused_grid = np.linspace(
        float(focused[0]),
        float(focused[1]),
        int(metric_cfg.get("focused_wavelength_points", 401)),
    )
    chi2_electron, chi2_heavy_hole = electron, heavy_hole
    if quasi_bound["policy"] == "exclude":
        chi2_electron = _excluded_band(electron, quasi_bound["records"], "electron")
        chi2_heavy_hole = _excluded_band(heavy_hole, quasi_bound["records"], "heavy_hole")
    spectrum = chi2mod.chi2_spectrum(
        chi2_electron,
        chi2_heavy_hole,
        chi2mod.photon_energy_eV(focused_grid),
        settings,
        orthonormality_tolerance=tolerance,
    )
    observables["chi2_mode"] = spectrum.settings.mode
    observables["chi2_units"] = spectrum.units
    observables["chi2_relative_at_reference"] = float(
        abs(spectrum.at_wavelength(reference_nm))
    )
    peak = spectrum.peak()
    observables["chi2_peak_wavelength_nm"] = peak["wavelength_nm"]
    observables["chi2_peak_magnitude"] = peak["magnitude"]

    # --- state-count propagation audit ---------------------------------------
    # Requesting more states from nextnano++ and widening Eq. 2's sums are two
    # different things, and the 2026-07-31 run showed why that has to be
    # measured rather than assumed: chi(2) agreed to ~1e-13 across 3, 4, and 6
    # requested states because the sum is capped at max_states_per_band
    # independently of what the solver returned. Every layer of the path is
    # recorded so a future convergence claim can be checked instead of believed.
    rendered = render_values(cfg)
    audit = {
        "case_layer_yaml": {
            "numerical.number_of_electron_states": int(
                cfg["numerical"]["number_of_electron_states"]
            ),
            "numerical.number_of_hole_states": int(
                cfg["numerical"]["number_of_hole_states"]
            ),
            "metric.max_states_per_band": int(settings.max_states_per_band),
        },
        "rendered_input_layer": {
            "number_of_electron_states": rendered["number_of_electron_states"],
            "number_of_hole_states": rendered["number_of_hole_states"],
            "output_state_count": rendered["output_state_count"],
        },
        "extracted_layer": {
            "electron_energy_rows": int(run.energies_eV.size),
            "electron_envelope_columns": int(run.envelopes.shape[1]),
            "electron_state_table_rows": len(electron_states),
            "heavy_hole_energy_rows": int(hole_energies.size),
            "heavy_hole_envelope_columns": int(hole_envelopes.shape[1]),
        },
        "bound_filter_layer": {
            "electron_states_passing_bound_criterion": sum(
                1 for state in electron_states if state.bound
            ),
            "quasi_bound_policy": quasi_bound["policy"],
            "electron_states_after_policy": int(chi2_electron.count),
            "heavy_hole_states_after_policy": int(chi2_heavy_hole.count),
        },
        "supplied_to_chi2_layer": {
            "electron_states_supplied": int(chi2_electron.count),
            "heavy_hole_states_supplied": int(chi2_heavy_hole.count),
        },
        "summation_layer": {
            key: value
            for key, value in spectrum.diagnostics.items()
            if key.startswith(("triple_sum", "electron_states", "heavy_hole_states",
                               "max_states", "overlap_electron_hole_shape",
                               "position_matrix", "electron_envelope_shape",
                               "heavy_hole_envelope_shape", "electron_energy_count",
                               "heavy_hole_energy_count", "largest_numerator",
                               "significance_floor"))
        },
        "exclusion_reasons": [
            {
                "band": r["band"],
                "state": r["state"],
                "included_in_chi2": r["included_in_chi2"],
                "reason": r["exclusion_reason"],
            }
            for r in quasi_bound["records"]
            if r["exclusion_reason"]
        ],
    }
    audit["solver_states_not_reaching_the_sum"] = int(
        max(0, chi2_electron.count - int(spectrum.diagnostics["electron_states_used"]))
        + max(0, chi2_heavy_hole.count - int(spectrum.diagnostics["heavy_hole_states_used"]))
    )
    write_json_atomically(extracted / "state_count_audit.json", audit)
    observables["chi2_max_states_per_band"] = int(settings.max_states_per_band)
    observables["chi2_electron_states_used"] = int(
        spectrum.diagnostics["electron_states_used"]
    )
    observables["chi2_heavy_hole_states_used"] = int(
        spectrum.diagnostics["heavy_hole_states_used"]
    )
    observables["chi2_triple_sum_terms_evaluated"] = int(
        spectrum.diagnostics["triple_sum_terms_evaluated"]
    )
    observables["chi2_triple_sum_terms_significant"] = int(
        spectrum.diagnostics["triple_sum_terms_significant"]
    )
    observables["solver_states_not_reaching_the_sum"] = audit[
        "solver_states_not_reaching_the_sum"
    ]

    predicted = chi2mod.resonance_wavelengths_nm(
        [
            value
            for value in (
                observables.get("transition_e1_hh1_eV"),
                observables.get("transition_e2_hh2_eV"),
            )
            if value
        ]
    )
    observables["predicted_two_photon_resonances_nm"] = predicted["two_photon_resonance_nm"]
    observables["predicted_one_photon_resonances_nm"] = predicted["one_photon_resonance_nm"]

    # --- artifacts ----------------------------------------------------------
    rows = [state.as_row() for state in electron_states]
    if rows:
        write_csv(
            extracted / "electron_states.csv",
            {key: np.asarray([row.get(key) for row in rows]) for key in rows[0]},
        )
    np.savetxt(
        extracted / "envelopes.csv",
        np.column_stack(
            [electron.z_nm, electron.envelopes, heavy_hole.envelopes]
        ),
        delimiter=",",
        header="z_nm,"
        + ",".join(f"psi_e{i + 1}" for i in range(electron.count))
        + ","
        + ",".join(f"psi_hh{i + 1}" for i in range(heavy_hole.count)),
        comments="",
    )
    write_json_atomically(
        extracted / "matrix_elements.json",
        {
            "overlap_electron_hole": overlap_eh.tolist(),
            "position_matrix_electron_nm": z_e.tolist(),
            "position_matrix_heavy_hole_nm": z_h.tolist(),
            "units": "nm",
        },
    )
    write_json_atomically(
        extracted / "chi2_settings.json",
        {**settings.as_record(), "assumptions": list(chi2mod.ASSUMPTIONS)},
    )
    np.savetxt(
        extracted / "chi2_focused.csv",
        np.column_stack(
            [focused_grid, spectrum.chi2.real, spectrum.chi2.imag, np.abs(spectrum.chi2)]
        ),
        delimiter=",",
        header="wavelength_nm,chi2_real,chi2_imag,chi2_magnitude",
        comments="",
    )

    log_checks = outputs.scan_log_markers(
        outputs.solver_log_text(raw),
        completion_markers=validation_cfg.get("completion_markers", ()),
        fatal_markers=validation_cfg.get("fatal_markers", ()),
        warning_markers=validation_cfg.get("convergence_warning_markers", ()),
    )
    log_checks.update(outputs.completion_evidence(raw))
    validation.update(
        {key: value for key, value in log_checks.items() if isinstance(value, bool)}
    )
    validation.update(
        {
            "electron_energies_ordered": bool(np.all(np.diff(e_energies) > 0)),
            "two_bound_electron_states": sum(
                1 for state in electron_states if state.bound
            )
            >= 2,
            "probability_normalized": all(state.normalised for state in electron_states),
            "bound_state_boundary_probability_small": bool(
                observables["maximum_boundary_probability_bound_states"]
                <= float(validation_cfg.get("maximum_boundary_probability", 1e-3))
            ),
            # Under the `exclude` policy the offending states are gone from the
            # sum, so what matters is whether anything that FAILED still made it
            # in. Under `warn` this is the same statement as the line above,
            # restricted to the states Eq. 2 actually uses.
            "chi2_states_pass_bound_criterion": bool(
                quasi_bound["failing_in_sum_count"] == 0
                or quasi_bound["policy"] == "exclude"
            ),
            # The sum must use exactly the configured window. If these ever
            # disagree, a convergence sweep is measuring something other than
            # what its label claims.
            "chi2_state_window_as_configured": bool(
                int(spectrum.diagnostics["electron_states_used"])
                == int(settings.max_states_per_band)
                and int(spectrum.diagnostics["heavy_hole_states_used"])
                == int(settings.max_states_per_band)
            ),
        }
    )

    _per_case_plots(cfg, run, electron, heavy_hole, regions, plots_dir)
    return observables, validation


def _per_case_plots(
    cfg: Mapping[str, Any],
    run: quantum1d.OneBandRun,
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    regions: Mapping[str, tuple[float, float]],
    plots_dir: Path,
) -> None:
    if not cfg["outputs"].get("write_plots", True):
        return
    plotting.band_diagram(
        plots_dir / "band_edges_and_wavefunctions.png",
        title=f"Coupled QW band edges and states ({PAPER})",
        position_nm=run.position_nm,
        conduction_eV=run.conduction_eV,
        energies_eV=electron.energies_eV[:2].tolist(),
        regions=regions,
        extra_bands={
            name: values
            for name, values in run.band_edges.items()
            if name in {"heavy_hole_eV", "light_hole_eV"}
        },
    )
    plotting.envelope_plot(
        plots_dir / "electron_envelopes.png",
        title="Electron envelopes",
        position_nm=electron.z_nm,
        envelopes=electron.envelopes,
        regions=regions,
    )
    plotting.envelope_plot(
        plots_dir / "heavy_hole_envelopes.png",
        title="Heavy-hole envelopes",
        position_nm=heavy_hole.z_nm,
        envelopes=heavy_hole.envelopes,
        regions=regions,
    )


# ---------------------------------------------------------------------------
# case construction
# ---------------------------------------------------------------------------


def _case(cfg: Mapping[str, Any], case_id: str, label: str, stage: str, **overrides: Any) -> sweeps.CaseSpec:
    config = (
        sweeps.apply_overrides(cfg, overrides) if overrides else sweeps.copy_config(cfg)
    )
    return sweeps.CaseSpec(
        case_id=case_id,
        label=label,
        swept=dict(overrides),
        config=config,
        metadata={"sweep_kind": stage, "stage": stage},
    )


def build_cases(cfg: Mapping[str, Any]) -> list[sweeps.CaseSpec]:
    """Every solver case, in stage order. Case IDs stay short for Windows."""

    analysis_cfg = cfg.get("analysis") or {}
    convergence = analysis_cfg.get("convergence") or {}
    total_well = float(cfg["scientific"]["thick_well_nm"]) + float(
        cfg["scientific"]["thin_well_nm"]
    )
    cases: list[sweeps.CaseSpec] = [
        _case(cfg, "s1_ref", "Stage 1: published design, abrupt interfaces", "stage1")
    ]

    # Stage 2: numerical convergence of the solver-side quantities.
    for index, value in enumerate(convergence.get("active_region_grid_spacing_nm", []), 1):
        cases.append(
            _case(cfg, f"s2g{index}", f"grid {value} nm", "stage2",
                  active_region_grid_spacing_nm=value)
        )
    for index, value in enumerate(convergence.get("domain_padding_nm", []), 1):
        cases.append(
            _case(cfg, f"s2d{index}", f"domain padding {value} nm", "stage2",
                  domain_padding_nm=value)
        )
    for index, value in enumerate(convergence.get("quantum_region_padding_nm", []), 1):
        cases.append(
            _case(cfg, f"s2q{index}", f"quantum padding {value} nm", "stage2",
                  quantum_region_padding_nm=value)
        )
    for index, value in enumerate(convergence.get("number_of_electron_states", []), 1):
        cases.append(
            _case(cfg, f"s2n{index}", f"{value} electron states", "stage2",
                  number_of_electron_states=value, number_of_hole_states=value)
        )
    # Widening Eq. 2's m,n,l sums is a different experiment from asking the
    # solver for more states, and needs enough solver states to draw on.
    for index, value in enumerate(convergence.get("chi2_max_states_per_band", []), 1):
        requested = max(int(value), int(cfg["numerical"]["number_of_electron_states"]))
        cases.append(
            _case(cfg, f"s2m{index}", f"Eq. 2 over {value} states per band", "stage2",
                  max_states_per_band=int(value),
                  number_of_electron_states=requested,
                  number_of_hole_states=requested)
        )
    # Padding convergence repeated where Stage 3 misbehaved, not only at 0.42.
    padding_probe = convergence.get("padding_at_asymmetry") or {}
    if padding_probe.get("enabled"):
        for a_index, asymmetry in enumerate(padding_probe.get("asymmetry_values", []), 1):
            thick, thin = chi2mod.well_widths_from_asymmetry(
                float(asymmetry), total_well
            )
            for p_index, padding in enumerate(
                padding_probe.get("quantum_region_padding_nm", []), 1
            ):
                cases.append(
                    _case(
                        cfg,
                        f"s2p{a_index}{p_index}",
                        f"s = {asymmetry}, quantum padding {padding} nm",
                        "stage2_padding",
                        thick_well_nm=round(thick, 6),
                        thin_well_nm=round(thin, 6),
                        quantum_region_padding_nm=float(padding),
                    )
                )

    # Stage 3: asymmetry at fixed total well thickness.
    for index, value in enumerate(analysis_cfg.get("asymmetry_sweep", []), 1):
        thick, thin = chi2mod.well_widths_from_asymmetry(float(value), total_well)
        if thin <= 0.0:
            raise DemoError(
                f"asymmetry {value} gives a zero-thickness thin well. s = 1 is the "
                "single-well limit, a different geometry; the paper's claim that "
                "chi(2) vanishes there is checked analytically instead."
            )
        cases.append(
            _case(cfg, f"s3a{index:02d}", f"s = {value}", "stage3",
                  thick_well_nm=round(thick, 6), thin_well_nm=round(thin, 6))
        )

    # Stage 3b: the refined sweep across the discontinuity. Separate stage, so
    # the coarse sweep it was derived from stays intact and comparable.
    for index, value in enumerate(analysis_cfg.get("asymmetry_sweep_refined", []), 1):
        thick, thin = chi2mod.well_widths_from_asymmetry(float(value), total_well)
        if thin <= 0.0:
            raise DemoError(
                f"refined asymmetry {value} gives a zero-thickness thin well."
            )
        cases.append(
            _case(cfg, f"s3r{index:02d}", f"s = {value}", "stage3_refined",
                  thick_well_nm=round(thick, 6), thin_well_nm=round(thin, 6))
        )

    # Stage 4: tunnelling barrier at fixed asymmetry.
    for index, value in enumerate(analysis_cfg.get("barrier_sweep_nm", []), 1):
        cases.append(
            _case(cfg, f"s4b{index:02d}", f"barrier {value} nm", "stage4",
                  tunnel_barrier_nm=value)
        )

    # Stage 7: interface abruptness.
    for index, model in enumerate(analysis_cfg.get("interface_models", []), 1):
        cases.append(
            _case(cfg, f"s7i{index}", str(model.get("name", f"model{index}")), "stage7",
                  interface_grading_nm=float(model.get("interface_grading_nm", 0.0)))
        )
    return cases


def _stage(results: Sequence[sweeps.CaseResult], stage: str) -> list[sweeps.CaseResult]:
    return [r for r in results if r.spec.metadata.get("stage") == stage]


# ---------------------------------------------------------------------------
# Stage 5/6: chi(2) post-processing on a completed reference case
# ---------------------------------------------------------------------------


def _load_bands(result: sweeps.CaseResult) -> tuple[chi2mod.BandStates, chi2mod.BandStates] | None:
    """Rebuild the two bands from a case's committed envelope CSV."""

    path = result.run_dir / "extracted" / "envelopes.csv"
    if not path.is_file():
        return None
    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 3:
        return None
    z = data[:, 0]
    e_cols = [i for i, name in enumerate(header) if name.startswith("psi_e")]
    h_cols = [i for i, name in enumerate(header) if name.startswith("psi_hh")]
    if len(e_cols) < 2 or len(h_cols) < 2:
        return None
    e_energies = np.asarray(result.observables.get("electron_energies_eV") or [])
    h_energies = np.asarray(result.observables.get("heavy_hole_energies_eV") or [])
    if e_energies.size < 2 or h_energies.size < 2:
        return None
    return (
        chi2mod.BandStates(z, e_energies[: len(e_cols)], data[:, e_cols], "e"),
        chi2mod.BandStates(z, h_energies[: len(h_cols)], data[:, h_cols], "hh"),
    )


def stage5_modes(
    cfg: Mapping[str, Any], reference: sweeps.CaseResult | None, parent: Path
) -> dict[str, Any]:
    """Evaluate Eq. 2 in each of the three modes, and say what each may claim."""

    metric_cfg = cfg.get("metric") or {}
    reference_nm = float(metric_cfg.get("reference_wavelength_nm", 1550.0))
    record: dict[str, Any] = {
        "reference_wavelength_nm": reference_nm,
        "modes": {},
        "assumptions": list(chi2mod.ASSUMPTIONS),
    }
    # Mode *availability* is a property of the configuration, not of the solver
    # output, so it is reported even on a dry run: knowing before a long
    # licensed run that absolute mode will decline is more useful than finding
    # out afterwards.
    for name in ("relative", "absolute", "calibrated"):
        try:
            chi2_settings(cfg, mode=name)
        except chi2mod.Chi2Error as exc:
            # `configured` says the settings permit this mode; `available` says
            # numbers were actually produced. They differ on a dry run.
            record["modes"][name] = {
                "configured": False,
                "available": False,
                "reason": str(exc),
            }
        else:
            record["modes"][name] = {
                "configured": True,
                "available": False,
                "reason": "no completed reference case yet",
            }

    bands = _load_bands(reference) if reference is not None else None
    if bands is None:
        record["available"] = False
        record["reason"] = (
            "no completed reference case; Eq. 2 needs both bands' envelopes. "
            "Mode availability above still reflects the configuration."
        )
        return record
    electron, heavy_hole = bands
    record["available"] = True

    focused = metric_cfg.get("focused_wavelength_nm", [1400.0, 1800.0])
    grid = np.linspace(
        float(focused[0]), float(focused[1]),
        int(metric_cfg.get("focused_wavelength_points", 401)),
    )
    photons = chi2mod.photon_energy_eV(grid)

    # relative -- always available
    relative = chi2mod.chi2_spectrum(
        electron, heavy_hole, photons, chi2_settings(cfg, mode="relative")
    )
    record["modes"]["relative"] = {
        "configured": True,
        "available": True,
        "units": relative.units,
        "magnitude_at_reference": float(abs(relative.at_wavelength(reference_nm))),
        "peak": relative.peak(),
        "claim": (
            "Lineshape, resonance positions, and every trend are meaningful. The "
            "absolute scale is not set and must not be quoted."
        ),
    }

    # absolute -- only with the values the paper does not publish
    try:
        absolute_settings = chi2_settings(cfg, mode="absolute")
    except chi2mod.Chi2Error as exc:
        record["modes"]["absolute"] = {
            "configured": False,
            "available": False,
            "reason": str(exc),
            "claim": (
                "Refused. An absolute pm/V value requires r_e_hh and N_z, neither "
                "of which the paper publishes."
            ),
        }
    else:
        absolute = chi2mod.chi2_spectrum(electron, heavy_hole, photons, absolute_settings)
        record["modes"]["absolute"] = {
            "configured": True,
            "available": True,
            "units": absolute.units,
            "magnitude_at_reference": float(abs(absolute.at_wavelength(reference_nm))),
            "peak": absolute.peak(),
            "claim": "Absolute prediction using the supplied r_e_hh and N_z.",
        }
        np.savetxt(
            parent / "extracted" / "chi2_absolute.csv",
            np.column_stack([grid, absolute.chi2.real, absolute.chi2.imag,
                             np.abs(absolute.chi2)]),
            delimiter=",",
            header="wavelength_nm,chi2_real_pm_per_V,chi2_imag_pm_per_V,chi2_magnitude_pm_per_V",
            comments="",
        )

    # calibrated -- one global factor against one published number
    target = metric_cfg.get("calibration_target_pm_per_V")
    calibration_nm = metric_cfg.get("calibration_wavelength_nm")
    if target is None or calibration_nm is None:
        record["modes"]["calibrated"] = {
            "configured": False,
            "available": False,
            "reason": "no calibration target configured",
        }
    else:
        try:
            calibrated = chi2mod.calibrate(
                relative,
                target_pm_per_V=float(target),
                wavelength_nm_value=float(calibration_nm),
                source=str(metric_cfg.get("calibration_source", "")),
            )
        except chi2mod.Chi2Error as exc:
            record["modes"]["calibrated"] = {
                "configured": True, "available": False, "reason": str(exc)
            }
        else:
            record["modes"]["calibrated"] = {
                "configured": True,
                "available": True,
                "units": calibrated.units,
                "scale_factor": calibrated.scale_factor,
                "magnitude_at_reference": float(
                    abs(calibrated.at_wavelength(reference_nm))
                ),
                "peak": calibrated.peak(),
                "claim": (
                    "CALIBRATED REPRODUCTION. One global factor was fitted to "
                    f"{target} pm/V at {calibration_nm} nm. Magnitudes elsewhere "
                    "are a consequence of that fit, not an independent prediction."
                ),
            }
            np.savetxt(
                parent / "extracted" / "chi2_calibrated.csv",
                np.column_stack([grid, calibrated.chi2.real, calibrated.chi2.imag,
                                 np.abs(calibrated.chi2)]),
                delimiter=",",
                header="wavelength_nm,chi2_real_pm_per_V,chi2_imag_pm_per_V,chi2_magnitude_pm_per_V",
                comments="",
            )
    return record


def stage3b_state_tracking(
    cfg: Mapping[str, Any], results: Sequence[sweeps.CaseResult], parent: Path
) -> dict[str, Any]:
    """Follow physical states across the refined asymmetry sweep.

    This is the stage that answers whether the Stage 3 cliff is a crossing being
    mislabelled or something physical. It recomputes chi(2) twice per point --
    once with the solver's energy ordering, once with the tracked ordering -- so
    the two curves can be laid side by side. Where tracking changes nothing the
    curves coincide, and that is a real answer too.
    """

    analysis_cfg = cfg.get("analysis") or {}
    tracking_cfg = analysis_cfg.get("state_tracking") or {}
    record: dict[str, Any] = {
        "available": False,
        "enabled": bool(tracking_cfg.get("enabled", False)),
        "bands": {},
        "rows": [],
    }
    if not tracking_cfg.get("enabled", False):
        record["reason"] = "analysis.state_tracking.enabled is false"
        return record

    refined = [
        r
        for r in results
        if r.spec.metadata.get("stage") == "stage3_refined" and r.solver_success
    ]
    if len(refined) < 2:
        record["reason"] = (
            f"state tracking needs at least two completed refined-sweep cases; "
            f"{len(refined)} available. No licensed solver output on this machine "
            "produces none, which is reported rather than substituted."
        )
        return record

    metric_cfg = cfg.get("metric") or {}
    reference_nm = float(metric_cfg.get("reference_wavelength_nm", 1550.0))
    focused = metric_cfg.get("focused_wavelength_nm", [1400.0, 1800.0])
    grid = np.linspace(
        float(focused[0]), float(focused[1]),
        int(metric_cfg.get("focused_wavelength_points", 401)),
    )
    photons = chi2mod.photon_energy_eV(grid)
    settings = chi2_settings(cfg, mode="relative")
    tolerance = float(analysis_cfg.get("orthonormality_tolerance", 1e-3))

    points: dict[str, list[tracking11.SweepPoint]] = {"electron": [], "heavy_hole": []}
    bands_by_case: dict[str, tuple[chi2mod.BandStates, chi2mod.BandStates]] = {}
    for result in sorted(refined, key=lambda r: float(r.observables.get("asymmetry", 0.0))):
        bands = _load_bands(result)
        if bands is None:
            continue
        electron, heavy_hole = bands
        bands_by_case[result.spec.case_id] = bands
        value = float(result.observables.get("asymmetry", 0.0))
        points["electron"].append(
            tracking11.SweepPoint(
                result.spec.case_id, value, electron.z_nm,
                electron.energies_eV, electron.envelopes,
            )
        )
        points["heavy_hole"].append(
            tracking11.SweepPoint(
                result.spec.case_id, value, heavy_hole.z_nm,
                heavy_hole.energies_eV, heavy_hole.envelopes,
            )
        )
    if not bands_by_case:
        record["reason"] = "no refined case committed the envelopes tracking needs"
        return record

    rows: list[dict[str, Any]] = []
    tracked_by_band: dict[str, list[tracking11.TrackedState]] = {}
    for band in tracking_cfg.get("bands", ["electron", "heavy_hole"]):
        tracked, diagnostics = tracking11.track_band(
            points.get(band, []),
            band=band,
            minimum_confidence=float(tracking_cfg.get("minimum_confidence", 0.60)),
            minimum_margin=float(tracking_cfg.get("minimum_assignment_margin", 0.15)),
            energy_continuity_weight=float(
                tracking_cfg.get("energy_continuity_weight", 0.05)
            ),
        )
        tracked_by_band[band] = tracked
        record["bands"][band] = diagnostics
        rows.extend(state.row() for state in tracked)

    # chi(2) under both labellings, point by point.
    comparison_rows: list[dict[str, Any]] = []
    for case_id, (electron, heavy_hole) in bands_by_case.items():
        result = next(r for r in refined if r.spec.case_id == case_id)
        value = float(result.observables.get("asymmetry", 0.0))
        row: dict[str, Any] = {"case_id": case_id, "asymmetry": value}
        for label, (e_band, h_band) in (
            ("raw_index", (electron, heavy_hole)),
            (
                "tracked",
                (
                    tracking11.reorder_to_tracked_labels(
                        electron,
                        [s for s in tracked_by_band.get("electron", [])
                         if s.case_id == case_id],
                    ),
                    tracking11.reorder_to_tracked_labels(
                        heavy_hole,
                        [s for s in tracked_by_band.get("heavy_hole", [])
                         if s.case_id == case_id],
                    ),
                ),
            ),
        ):
            try:
                spectrum = chi2mod.chi2_spectrum(
                    e_band, h_band, photons, settings,
                    orthonormality_tolerance=tolerance,
                )
            except chi2mod.Chi2Error as exc:
                row[f"chi2_peak_magnitude_{label}"] = None
                row[f"chi2_error_{label}"] = str(exc)
                continue
            peak = spectrum.peak()
            row[f"chi2_peak_magnitude_{label}"] = peak["magnitude"]
            row[f"chi2_peak_wavelength_nm_{label}"] = peak["wavelength_nm"]
            row[f"chi2_at_reference_{label}"] = float(
                abs(spectrum.at_wavelength(reference_nm))
            )
        raw_peak = row.get("chi2_peak_magnitude_raw_index")
        tracked_peak = row.get("chi2_peak_magnitude_tracked")
        row["tracking_changes_chi2"] = bool(
            raw_peak is not None
            and tracked_peak is not None
            and abs(tracked_peak - raw_peak) > 1e-12 * max(abs(raw_peak), 1.0)
        )
        comparison_rows.append(row)

    extracted = parent / "extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    sweeps.write_state_tracking(parent, rows)
    write_json_atomically(
        extracted / "state_tracking_assignments.json",
        {
            "sweep": "stage3_refined",
            "assignment_backend": analysis.assignment_backend(),
            "bands": record["bands"],
        },
    )
    if comparison_rows:
        write_csv(
            extracted / "chi2_raw_vs_tracked.csv",
            {
                key: np.asarray([row.get(key) for row in comparison_rows])
                for key in comparison_rows[0]
            },
        )

    ambiguous = [row for row in rows if row.get("ambiguous")]
    record.update(
        {
            "available": True,
            "rows": rows,
            "comparison": comparison_rows,
            "points": len(bands_by_case),
            "ambiguous_assignments": len(ambiguous),
            "ambiguous_at": sorted({row["case_id"] for row in ambiguous}),
            "reordering_detected": any(
                diagnostics.get("label_reordering_detected")
                for diagnostics in record["bands"].values()
            ),
            "tracking_changes_chi2_at": [
                row["case_id"] for row in comparison_rows if row["tracking_changes_chi2"]
            ],
        }
    )
    return record


def stage6_wavelength(
    cfg: Mapping[str, Any], reference: sweeps.CaseResult | None, parent: Path
) -> dict[str, Any]:
    """Broad and focused wavelength scans, with resonance positions."""

    metric_cfg = cfg.get("metric") or {}
    bands = _load_bands(reference) if reference is not None else None
    if bands is None:
        return {"available": False, "reason": "no completed reference case"}
    electron, heavy_hole = bands
    settings = chi2_settings(cfg, mode="relative")
    result: dict[str, Any] = {"available": True}

    for name, key_range, key_points in (
        ("broad", "broad_wavelength_nm", "broad_wavelength_points"),
        ("focused", "focused_wavelength_nm", "focused_wavelength_points"),
    ):
        span = metric_cfg.get(key_range)
        if not span:
            continue
        grid = np.linspace(float(span[0]), float(span[1]), int(metric_cfg.get(key_points, 401)))
        spectrum = chi2mod.chi2_spectrum(
            electron, heavy_hole, chi2mod.photon_energy_eV(grid), settings
        )
        np.savetxt(
            parent / "extracted" / f"chi2_{name}_wavelength.csv",
            np.column_stack([grid, spectrum.chi2.real, spectrum.chi2.imag,
                             np.abs(spectrum.chi2)]),
            delimiter=",",
            header="wavelength_nm,chi2_real,chi2_imag,chi2_magnitude",
            comments="",
        )
        result[f"{name}_peak"] = spectrum.peak()
        result[f"{name}_range_nm"] = [float(span[0]), float(span[1])]
    transitions = [
        value
        for value in (
            reference.observables.get("transition_e1_hh1_eV"),
            reference.observables.get("transition_e2_hh2_eV"),
        )
        if value
    ]
    result["predicted_resonances_nm"] = chi2mod.resonance_wavelengths_nm(transitions)
    return result


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    targets = paper_targets(context.demo_dir)
    cases = build_cases(cfg)

    results: list[sweeps.CaseResult] = []
    for case in cases:
        results.append(
            sweeps.execute_case(
                demo_dir=context.demo_dir,
                spec=case,
                machine=context.machine,
                run_dir=context.parent / "runs" / case.case_id,
                render_values=render_values,
                analyse=analyse_case,
                dependency_report=context.dependency_report,
            )
        )

    (context.parent / "extracted").mkdir(parents=True, exist_ok=True)
    reference = next(
        (r for r in results if r.spec.case_id == "s1_ref" and r.solver_success), None
    )
    stage5 = stage5_modes(cfg, reference, context.parent)
    stage6 = stage6_wavelength(cfg, reference, context.parent)
    stage3b = stage3b_state_tracking(cfg, results, context.parent)

    comparison = report11.build(
        cfg=cfg,
        targets=targets,
        results=results,
        reference=reference,
        stage5=stage5,
        stage6=stage6,
        stage3b=stage3b,
        parent=context.parent,
    )

    sweeps.write_sweep_summary(context.parent, results)
    failed, suspicious = sweeps.write_failed_and_suspicious(context.parent, results)
    report11.write_tables(context.parent, targets, results, comparison)
    report11.write_plots(
        context.parent, cfg, results, reference, stage5, stage6, comparison, stage3b
    )
    plotting.ensure_plot_set(
        context.parent / "plots",
        PLOT_SET,
        reason=(
            "Produced once a licensed solver has run this stage. No solver output "
            "on this machine."
        ),
    )

    manifest = sweeps.write_sweep_manifest(
        context.parent,
        cfg=cfg,
        machine=context.machine,
        results=results,
        dependency_report=context.dependency_report,
        parser_provenance={"profile": cfg["outputs"].get("parser_profile")},
        extra={
            "paper": PAPER,
            "stage5_chi2_modes": stage5,
            "stage6_wavelength": stage6,
            "stage3b_state_tracking": {
                key: value
                for key, value in stage3b.items()
                # The per-state rows and every assignment matrix are already in
                # extracted/; repeating them here would bloat the manifest.
                if key not in {"rows", "bands", "comparison"}
            },
            "comparison_summary": comparison["summary"],
            "reproduction_status": comparison["status"],
            "chi2_assumptions": list(chi2mod.ASSUMPTIONS),
            "absolute_scale_disclaimer": (
                "The absolute chi(2) magnitude cannot be reproduced independently: "
                "the paper does not publish the HSE06 unit-cell matrix element "
                "r_e_hh, the wells-per-unit-length N_z, or the k-space quadrature "
                "conventions. Energies, resonance positions, and the asymmetry, "
                "barrier and interface trends are the defensible targets."
            ),
        },
    )
    report11.write_report(
        context.parent, cfg, targets, comparison, stage5, stage6, manifest, stage3b
    )
    sweeps.write_validation_report(
        context.parent,
        cfg=cfg,
        manifest=manifest,
        registry_record=context.registry_record,
        dependency_report=context.dependency_report,
        criteria=comparison["criteria"],
        notes=[
            f"Reproduction target: {PAPER}.",
            "The absolute chi(2) scale is NOT independently reproducible from the "
            "paper; see assumptions_and_unknowns.yaml.",
            "Published values live in paper_targets.yaml with their provenance and "
            "are never mixed with the simulation inputs in demo.yaml.",
            "Material parameters were not adjusted to improve agreement. Any "
            "difference from the paper is reported, not tuned away.",
            "Sweep optima are reported under TWO metrics. `peak_chi2_magnitude` is "
            "the intrinsic maximum of |chi(2)| over the scanned band and is the "
            "primary metric for the paper's optimum claims. "
            "`chi2_at_reference_wavelength` is the response at "
            f"{(cfg.get('metric') or {}).get('reference_wavelength_nm', 1550.0)} nm "
            "and is application-specific: across the asymmetry sweep the resonance "
            "itself moves ~100 nm against a 5 meV linewidth, so a fixed-wavelength "
            "comparison ranks structures partly by detuning.",
            "Quasi-bound-state policy in force: "
            f"{(cfg.get('validation') or {}).get('quasi_bound_state_policy', 'warn')}.",
            "Eq. 2 sums over "
            f"{(cfg.get('metric') or {}).get('max_states_per_band', 2)} state(s) per "
            "band, independently of how many states the solver was asked for. "
            "Requesting more solver states does not widen the sum; see "
            "extracted/state_count_audit.json in each case.",
        ],
        unvalidated_syntax=[
            "structure/region/ternary_linear{} graded-alloy composition output",
        ],
    )
    return sweeps.finish_run(context, results=results, manifest=manifest)
