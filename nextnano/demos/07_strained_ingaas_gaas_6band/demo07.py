"""Demo 7 — strained InGaAs/GaAs: one-band versus 6-band valence states.

An InGaAs well grown coherently on GaAs is compressed in the growth plane and
stretched along the growth axis.  The hydrostatic part of that strain moves the
average band positions; the biaxial part splits the heavy- and light-hole bands,
which are degenerate at the zone centre in the unstrained bulk.

A one-band hole model cannot represent that mixing at all -- it assigns each
state to one band by construction.  A 6-band k.p Hamiltonian can, so its hole
states carry HH/LH/SO component weights.  Those weights, not the eigenvalue
index, are what this demo uses to name a state.

STATUS: the home laptop's Free nextnano++ refuses both strain and every k.p
model, so the decks here are syntax-validated only and the strain / 6-band
output patterns in the parser profile are marked unconfirmed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import analysis
import layers
import outputs
import plots as plotting
import quantum1d
import sweeps
from demo_workflow import DemoError, write_csv, write_json_atomically

PLOT_SET: tuple[tuple[str, str], ...] = (
    ("strained_vs_unstrained_bandedges.png", "Strained versus unstrained band edges"),
    ("strain_profile.png", "Hydrostatic and biaxial strain versus position"),
    ("oneband_vs_sixband_holes.png", "One-band versus 6-band hole energies"),
    ("state_character.png", "HH/LH/SO composition of each hole state"),
    ("probability_densities.png", "Electron and hole probability densities"),
    ("transitions_vs_indium.png", "Transition energies versus indium fraction"),
    ("transitions_vs_width.png", "Transition energies versus well width"),
    ("character_vs_parameter.png", "State character across the parameter sweep"),
    ("grid_sensitivity.png", "Multiband grid sensitivity"),
)

UNVALIDATED_SYNTAX: tuple[str, ...] = (
    "strain{ output_strain_tensor{} } output file name and component column order",
    "quantum{ region{ kp_6band{} } } output sub-directory name",
    "output_states{ spinor_composition = yes } file name and column order",
)


def build_stack(cfg: Mapping[str, Any]) -> layers.LayerStack:
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    return layers.strained_single_well(
        well_width_nm=float(scientific["well_width_nm"]),
        barrier_width_nm=float(scientific["barrier_width_nm"]),
        indium_fraction=float(scientific["indium_fraction"]),
        active_grid_spacing_nm=float(numerical["active_region_grid_spacing_nm"]),
        exterior_grid_spacing_nm=float(numerical["exterior_grid_spacing_nm"]),
    )


def region_name(cfg: Mapping[str, Any]) -> str:
    return str((cfg.get("analysis") or {}).get("quantum_region_name", "qw"))


def active_model(cfg: Mapping[str, Any]) -> dict[str, Any]:
    models = cfg.get("models") or []
    if not models:
        raise DemoError("demo.yaml must declare at least one model stage.")
    return dict(models[0])


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    model = active_model(cfg)
    stack = build_stack(cfg)
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(float(numerical["quantum_region_padding_nm"]))

    if model.get("strain"):
        strain_block = (
            "\nstrain{\n"
            "    pseudomorphic_strain{}\n"
            "    output_strain_tensor{ simulation_system = yes  crystal_system = yes }\n"
            "    output_hydrostatic_strain{}\n"
            "    output_lattice_constants{}\n"
            "}\n"
        )
    else:
        # Explicitly disabled rather than merely omitted, so the baseline says
        # what it is doing.
        strain_block = "\nstrain{\n    no_strain{}\n}\n"

    quantum_block = "\n# Classical stage: no quantum{} block at all.\n"
    if model.get("quantum"):
        electrons = int(numerical["number_of_electron_states"])
        holes = int(numerical["number_of_hole_states"])
        valence = str(model.get("valence_model", "one_band"))
        if valence == "one_band":
            valence_lines = (
                f"        HH{{ num_ev = {holes} }}\n"
                f"        LH{{ num_ev = {holes} }}\n"
            )
            extra_output = ""
        elif valence == "kp6":
            valence_lines = (
                "        kp_6band{\n"
                f"            num_ev = {holes}\n"
                "            k_integration_disabled{}\n"
                "        }\n"
            )
            # Component weights are the whole point of the 6-band stage.
            extra_output = (
                "            spinor_composition            = yes\n"
                "            spinor_composition_CB_HH_LH_SO = yes\n"
            )
        else:
            raise DemoError(f"unsupported valence_model {valence!r}.")
        quantum_block = (
            "\nquantum{\n"
            "    region{\n"
            f"        name = \"{region_name(cfg)}\"\n"
            f"        x = [{start:.9g}, {end:.9g}]\n"
            "        no_density = yes\n"
            "        boundary{ x = dirichlet }\n"
            f"        Gamma{{ num_ev = {electrons} }}\n"
            f"{valence_lines}"
            "        output_states{\n"
            f"            max_num       = {max(electrons, holes)}\n"
            "            envelopes     = yes\n"
            "            probabilities = yes\n"
            f"{extra_output}"
            "        }\n"
            "    }\n"
            "}\n"
        )

    run_parts = []
    if model.get("strain"):
        run_parts.append("    strain{}")
    if model.get("quantum"):
        run_parts.append("    quantum{}")
    run_block = "run{\n" + ("\n".join(run_parts) + "\n" if run_parts else "") + "}\n"

    return {
        "temperature_K": scientific["temperature_K"],
        "substrate_material": str(scientific["substrate_material"]),
        "growth_direction_vector": str(scientific["growth_direction"]),
        "grid_lines": stack.grid_lines(),
        "structure_regions": stack.structure_regions(contact_name="qw_contact"),
        "strain_block": strain_block,
        "quantum_block": quantum_block,
        "run_block": run_block,
    }


def _hole_states(
    profile: outputs.ParserProfile,
    raw: Path,
    region: str,
    valence: str,
) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None, Path | None]:
    """Hole energies and densities for whichever valence model ran."""

    key_energy = "energy_spectrum_hh" if valence == "one_band" else "energy_spectrum_kp6"
    key_probability = (
        "probabilities_hh" if valence == "one_band" else "probabilities_kp6"
    )
    resolved = outputs.resolve_outputs(
        profile, raw, [key_energy, key_probability], substitutions={"region": region}
    )
    outputs.require_or_diagnose(
        resolved,
        raw,
        [key_energy],
        why=f"the {valence} valence model was enabled",
    )
    _, energies = outputs.read_state_table(resolved.one(key_energy))
    density_x = None
    densities = None
    if resolved.many(key_probability):
        density_x, densities = outputs.read_profile_table(resolved.one(key_probability))
    return energies, density_x, densities, resolved.one(key_energy)


def _component_weights(
    profile: outputs.ParserProfile, raw: Path, region: str
) -> list[dict[str, float]] | None:
    """HH/LH/SO weights per 6-band state, if the solver wrote them."""

    resolved = outputs.resolve_outputs(
        profile, raw, ["spinor_composition_kp6"], substitutions={"region": region}
    )
    paths = resolved.many("spinor_composition_kp6")
    if not paths:
        return None
    table = outputs.read_table(paths[0])
    names = [name for name, _ in table.header][1:] or [
        f"component_{index}" for index in range(table.n_columns - 1)
    ]
    weights: list[dict[str, float]] = []
    for row in table.data:
        weights.append(
            {names[index]: float(row[index + 1]) for index in range(len(names))}
        )
    return weights


def analyse_case(
    cfg: Mapping[str, Any], raw: Path, extracted: Path, plots_dir: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    model = active_model(cfg)
    validation_cfg = cfg["validation"]
    analysis_cfg = cfg.get("analysis") or {}
    stack = build_stack(cfg)
    regions = quantum1d.region_map(stack.intervals())
    window = stack.quantum_region_nm(float(cfg["numerical"]["quantum_region_padding_nm"]))
    profile = outputs.load_profile(
        str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
    )
    region = region_name(cfg)

    observables: dict[str, Any] = {
        "model": model.get("name"),
        "strain_enabled": bool(model.get("strain")),
        "valence_model": str(model.get("valence_model", "none")),
        "indium_fraction": float(cfg["scientific"]["indium_fraction"]),
        "well_width_nm": float(cfg["scientific"]["well_width_nm"]),
        "substrate_material": str(cfg["scientific"]["substrate_material"]),
        "growth_direction": str(cfg["scientific"]["growth_direction"]),
        "active_region_grid_spacing_nm": float(
            cfg["numerical"]["active_region_grid_spacing_nm"]
        ),
    }
    validation: dict[str, Any] = {}

    band_path = outputs.resolve_outputs(profile, raw, ["bandedges"]).one("bandedges")
    band = outputs.read_table(band_path).select(dict(cfg["outputs"]["bandedge_columns"]))
    write_csv(extracted / "band_edges.csv", band)
    position = band["position_nm"]
    well_start, well_end = stack.interval("well")
    inside = (position >= well_start) & (position <= well_end)
    for name, key in (
        ("conduction", "conduction_eV"),
        ("heavy_hole", "heavy_hole_eV"),
        ("light_hole", "light_hole_eV"),
        ("split_off", "split_off_eV"),
    ):
        if key in band:
            observables[f"well_{name}_edge_eV"] = float(np.median(band[key][inside]))
            observables[f"barrier_{name}_edge_eV"] = float(np.median(band[key][~inside]))
    if "heavy_hole_eV" in band and "light_hole_eV" in band:
        observables["hh_lh_splitting_meV"] = float(
            1000.0
            * (
                np.median(band["heavy_hole_eV"][inside])
                - np.median(band["light_hole_eV"][inside])
            )
        )

    # --- strain ---------------------------------------------------------------
    if model.get("strain"):
        resolved = outputs.resolve_outputs(
            profile, raw, ["hydrostatic_strain", "strain_tensor"]
        )
        outputs.require_or_diagnose(
            resolved,
            raw,
            ["hydrostatic_strain", "strain_tensor"],
            why="pseudomorphic strain was enabled and its outputs were requested",
        )
        hydrostatic = outputs.read_table(resolved.one("hydrostatic_strain"))
        tensor = outputs.read_table(resolved.one("strain_tensor"))
        np.savetxt(
            extracted / "hydrostatic_strain.csv",
            hydrostatic.data,
            delimiter=",",
            header=",".join(name for name, _ in hydrostatic.header),
            comments="",
        )
        np.savetxt(
            extracted / "strain_tensor.csv",
            tensor.data,
            delimiter=",",
            header=",".join(name for name, _ in tensor.header),
            comments="",
        )
        strain_x = hydrostatic.column(0)
        strain_value = hydrostatic.column(1)
        strain_inside = (strain_x >= well_start) & (strain_x <= well_end)
        observables["hydrostatic_strain_in_well"] = float(
            np.median(strain_value[strain_inside])
        )
        observables["hydrostatic_strain_in_barrier"] = float(
            np.median(strain_value[~strain_inside])
        )
        # Biaxial strain: the difference between the in-plane and growth-axis
        # components. Column order is UNCONFIRMED for this build, so it is
        # reported with its header names rather than assumed.
        observables["strain_tensor_columns"] = [name for name, _ in tensor.header]
        validation["strain_nonzero_in_well"] = bool(
            abs(observables["hydrostatic_strain_in_well"]) > 1e-6
        )
        validation["barrier_is_lattice_matched"] = bool(
            abs(observables["hydrostatic_strain_in_barrier"]) < 1e-6
        )
    else:
        validation["strain_disabled_in_baseline"] = True

    # --- quantum states -------------------------------------------------------
    if model.get("quantum"):
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
            normalisation_tolerance=float(
                validation_cfg.get("normalization_tolerance", 1e-3)
            ),
            boundary_edge_fraction=float(analysis_cfg.get("boundary_edge_fraction", 0.05)),
            quantum_window_nm=window,
        )
        electron_energies = [state.energy_eV for state in electron_states]
        observables["electron_energies_eV"] = electron_energies
        observables["E1_electron_eV"] = electron_energies[0] if electron_energies else None

        valence = str(model.get("valence_model", "one_band"))
        hole_energies, hole_x, hole_densities, hole_source = _hole_states(
            profile, raw, region, valence
        )
        if hole_energies is not None:
            # Hole spectra are listed with DECREASING electron-scale energy, so
            # index order is confinement order. Sorting here would relabel them.
            observables["hole_energies_eV"] = [float(v) for v in hole_energies]
            observables["hole_energy_source"] = str(hole_source)
            observables["E1_hole_eV"] = float(hole_energies[0])
            if electron_energies:
                observables["interband_transition_e1_h1_eV"] = float(
                    electron_energies[0] - hole_energies[0]
                )
                observables["interband_transitions_eV"] = [
                    [
                        float(electron - hole)
                        for hole in hole_energies[:4]
                    ]
                    for electron in electron_energies[:3]
                ]
            validation["hole_energies_finite"] = bool(np.all(np.isfinite(hole_energies)))
            write_csv(
                extracted / "hole_states.csv",
                {
                    "state": np.arange(1, hole_energies.size + 1),
                    "energy_eV": hole_energies,
                },
            )

        characters: list[dict[str, Any]] = []
        weights = _component_weights(profile, raw, region) if valence == "kp6" else None
        if weights:
            threshold = float(analysis_cfg.get("character_dominant_threshold", 0.6))
            for index, entry in enumerate(weights, start=1):
                label, fraction = analysis.classify_character(
                    entry, dominant_threshold=threshold
                )
                characters.append(
                    {
                        "state": index,
                        "character": label,
                        "dominant_fraction": fraction,
                        **analysis.normalise_weights(entry),
                    }
                )
            observables["hole_characters"] = characters
            observables["mixed_state_count"] = sum(
                1 for entry in characters if entry["character"] == "mixed"
            )
            validation["component_weights_normalised"] = all(
                abs(sum(float(v) for k, v in entry.items()
                        if k not in {"state", "character", "dominant_fraction"}) - 1.0)
                <= 1e-6
                for entry in characters
            )
            write_json_atomically(extracted / "hole_characters.json", characters)
        elif valence == "kp6":
            observables["hole_characters"] = None
            observables["character_unavailable_reason"] = (
                "spinor-composition output was not located; hole states are NOT "
                "labelled HH-like or LH-like on the basis of their index"
            )
        else:
            observables["character_unavailable_reason"] = (
                "a one-band hole model assigns each state to a band by "
                "construction; there is no mixing to measure"
            )

        rows = [state.as_row() for state in electron_states]
        if rows:
            write_csv(
                extracted / "electron_states.csv",
                {key: np.asarray([row.get(key) for row in rows]) for key in rows[0]},
            )
        write_csv(
            extracted / "electron_densities.csv",
            {
                "position_nm": run.state_position_nm,
                **{
                    f"probability_density_{index + 1}_nm^-1": run.densities[:, index]
                    for index in range(run.densities.shape[1])
                },
            },
        )
        validation.update(
            {
                "electron_energies_finite_and_ordered": bool(
                    np.all(np.isfinite(electron_energies))
                    and np.all(np.diff(electron_energies) > 0)
                ),
                "probability_normalized": all(state.normalised for state in electron_states),
                "at_least_one_bound_electron": any(
                    state.bound for state in electron_states
                ),
            }
        )
        if hole_densities is not None and hole_x is not None:
            write_csv(
                extracted / "hole_densities.csv",
                {
                    "position_nm": hole_x,
                    **{
                        f"probability_density_{index + 1}_nm^-1": hole_densities[
                            :, index
                        ]
                        for index in range(hole_densities.shape[1])
                    },
                },
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
    _per_case_plots(cfg, model, extracted, plots_dir)
    return observables, validation


def _per_case_plots(
    cfg: Mapping[str, Any], model: Mapping[str, Any], extracted: Path, plots_dir: Path
) -> None:
    if not cfg["outputs"].get("write_plots", True):
        return
    label = str(model.get("name"))
    band = extracted / "band_edges.csv"
    if band.is_file():
        header = band.read_text(encoding="utf-8").splitlines()[0].split(",")
        data = np.loadtxt(band, delimiter=",", skiprows=1)
        series = {
            header[index]: (data[:, 0], data[:, index])
            for index in range(1, data.shape[1])
        }
        plotting.line_plot(
            plots_dir / "band_edges.png",
            title=f"Band edges ({label})",
            xlabel="Position (nm)",
            ylabel="Energy (eV)",
            series=series,
            markers=False,
        )
    strain = extracted / "hydrostatic_strain.csv"
    if strain.is_file():
        data = np.loadtxt(strain, delimiter=",", skiprows=1, ndmin=2)
        plotting.line_plot(
            plots_dir / "strain_profile.png",
            title=f"Hydrostatic strain ({label})",
            xlabel="Position (nm)",
            ylabel="Hydrostatic strain",
            series={"hydrostatic": (data[:, 0], data[:, 1])},
            markers=False,
        )
    density_series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    for prefix, filename in (
        ("electron", "electron_densities.csv"),
        ("hole", "hole_densities.csv"),
    ):
        path = extracted / filename
        if not path.is_file():
            continue
        data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
        for index in range(1, min(data.shape[1], 4)):
            density_series[f"{prefix} state {index}"] = (data[:, 0], data[:, index])
    plotting.line_plot(
        plots_dir / "probability_densities.png",
        title=f"Electron and hole probability densities ({label})",
        xlabel="Position (nm)",
        ylabel="Probability density (nm$^{-1}$)",
        series=density_series,
        markers=False,
    )


def model_case(
    cfg: Mapping[str, Any], model: Mapping[str, Any], case_id: str, **overrides: Any
) -> sweeps.CaseSpec:
    config = (
        sweeps.apply_overrides(cfg, overrides) if overrides else sweeps.copy_config(cfg)
    )
    config["models"] = [dict(model)]
    return sweeps.CaseSpec(
        case_id=case_id,
        label=str(model.get("name")) + (f" ({overrides})" if overrides else ""),
        swept=dict(overrides),
        config=config,
        metadata={"sweep_kind": "model_stage", "model": str(model.get("name"))},
    )


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    models = cfg.get("models") or []
    sweep_cfg = cfg.get("sweeps") or {}
    analysis_cfg = cfg.get("analysis") or {}
    sweep_model_name = str(analysis_cfg.get("sweep_model", models[-1]["name"]))
    sweep_model = next(
        (m for m in models if str(m["name"]) == sweep_model_name), models[-1]
    )

    cases = [
        model_case(cfg, model, f"model_{index}_{str(model['name'])[:2]}")
        for index, model in enumerate(models, start=1)
    ]
    model_count = len(cases)
    for index, value in enumerate(sweep_cfg.get("indium_fraction", []), start=1):
        cases.append(
            model_case(cfg, sweep_model, f"x_{index:02d}_{sweeps.safe_token(value)}",
                       indium_fraction=value)
        )
    indium_count = len(cases) - model_count
    for index, value in enumerate(sweep_cfg.get("well_width_nm", []), start=1):
        cases.append(
            model_case(cfg, sweep_model, f"w_{index:02d}_{sweeps.safe_token(value)}",
                       well_width_nm=value)
        )
    width_count = len(cases) - model_count - indium_count
    # Multiband Hamiltonians are more grid-sensitive than one-band ones; a
    # refined rerun of the 6-band stage measures that instead of assuming it.
    refinement = float(analysis_cfg.get("grid_refinement_factor", 0.5))
    cases.append(
        model_case(
            cfg,
            sweep_model,
            "grid_fine",
            active_region_grid_spacing_nm=float(
                cfg["numerical"]["active_region_grid_spacing_nm"]
            )
            * refinement,
        )
    )

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
    model_results = results[:model_count]
    indium_results = results[model_count : model_count + indium_count]
    width_results = results[model_count + indium_count : model_count + indium_count + width_count]
    grid_results = results[model_count + indium_count + width_count :]

    sweeps.write_sweep_summary(context.parent, results)
    failed, suspicious = sweeps.write_failed_and_suspicious(context.parent, results)
    sweeps.write_table(
        context.parent,
        "model_comparison",
        [
            {
                "model": result.observables.get("model") or result.spec.case_id,
                "strain": result.observables.get("strain_enabled"),
                "valence_model": result.observables.get("valence_model"),
                "well_conduction_edge_eV": result.observables.get("well_conduction_edge_eV"),
                "well_heavy_hole_edge_eV": result.observables.get("well_heavy_hole_edge_eV"),
                "well_light_hole_edge_eV": result.observables.get("well_light_hole_edge_eV"),
                "hh_lh_splitting_meV": result.observables.get("hh_lh_splitting_meV"),
                "hydrostatic_strain_in_well": result.observables.get(
                    "hydrostatic_strain_in_well"
                ),
                "E1_electron_eV": result.observables.get("E1_electron_eV"),
                "E1_hole_eV": result.observables.get("E1_hole_eV"),
                "interband_transition_e1_h1_eV": result.observables.get(
                    "interband_transition_e1_h1_eV"
                ),
                "mixed_state_count": result.observables.get("mixed_state_count"),
                "status": result.status,
            }
            for result in model_results
        ],
    )
    sweeps.write_table(
        context.parent,
        "state_character",
        [
            {
                "case": result.spec.case_id,
                "swept": ";".join(f"{k}={v}" for k, v in result.spec.swept.items()),
                **{f"state_{entry['state']}": entry["character"] for entry in
                   (result.observables.get("hole_characters") or [])},
                "character_unavailable_reason": result.observables.get(
                    "character_unavailable_reason"
                ),
            }
            for result in results
        ],
    )
    _sweep_plots(
        context.parent,
        model_results,
        indium_results,
        width_results,
        grid_results,
    )
    plotting.ensure_plot_set(
        context.parent / "plots",
        PLOT_SET,
        reason=(
            "Per-case figure or licensed-only physics: strain and k·p are "
            "Standard-only, so no home run can produce this."
        ),
    )

    grid_shift_meV: float | None = None
    baseline = next(
        (r for r in model_results if str(r.observables.get("model")) == sweep_model_name),
        None,
    )
    if (
        baseline is not None
        and grid_results
        and baseline.observables.get("E1_electron_eV") is not None
        and grid_results[0].observables.get("E1_electron_eV") is not None
    ):
        grid_shift_meV = abs(
            1000.0
            * (
                float(baseline.observables["E1_electron_eV"])
                - float(grid_results[0].observables["E1_electron_eV"])
            )
        )

    manifest = sweeps.write_sweep_manifest(
        context.parent,
        cfg=cfg,
        machine=context.machine,
        results=results,
        dependency_report=context.dependency_report,
        parser_provenance={
            "profile": cfg["outputs"].get("parser_profile"),
            "unconfirmed_patterns": list(UNVALIDATED_SYNTAX),
        },
        extra={
            "model_count": model_count,
            "grid_refinement_shift_meV": grid_shift_meV,
            "substrate_material": cfg["scientific"]["substrate_material"],
            "growth_direction": cfg["scientific"]["growth_direction"],
        },
    )
    sweeps.write_validation_report(
        context.parent,
        cfg=cfg,
        manifest=manifest,
        registry_record=context.registry_record,
        dependency_report=context.dependency_report,
        criteria=[
            (
                "all four models produced a generated input",
                model_count >= 4,
                "M1 unstrained classical → M4 6-band valence",
            ),
            (
                "no case was discarded",
                len(results) == len(cases),
                f"{len(failed)} failed/skipped and {len(suspicious)} suspicious rows retained",
            ),
            (
                "strain is genuinely disabled in the baseline",
                _all_true(results, "strain_disabled_in_baseline"),
                "M1 uses strain{ no_strain{} } and omits run{ strain{} }",
            ),
            (
                "strain is nonzero in the InGaAs well",
                _all_true(results, "strain_nonzero_in_well"),
                "hydrostatic strain measured in the well layer",
            ),
            (
                "the GaAs barrier is lattice-matched and unstrained",
                _all_true(results, "barrier_is_lattice_matched"),
                "confirms the substrate and growth convention",
            ),
            (
                "hole states carry normalised component weights",
                _all_true(results, "component_weights_normalised"),
                "required before any state may be called HH-like or LH-like",
            ),
            (
                "electron energies finite and ordered",
                _all_true(results, "electron_energies_finite_and_ordered"),
                "hole spectra are NOT sorted: nextnano++ lists them descending",
            ),
            (
                "multiband grid sensitivity measured",
                (grid_shift_meV is not None) or None,
                f"E1 shift on halving the mesh: "
                f"{'not evaluated' if grid_shift_meV is None else f'{grid_shift_meV:.3f} meV'}",
            ),
        ],
        notes=[
            "Substrate is GaAs and growth is along the simulation x axis; the "
            "barrier being unstrained is the check that this convention holds.",
            "Hole spectra from nextnano++ are listed with decreasing "
            "electron-scale energy. The parser preserves that order; sorting "
            "would silently relabel physical states.",
            "No hole state is called HH1 or LH1 on the basis of its index. "
            "Without a spinor-composition file no character label is assigned "
            "at all, and the reason is recorded in the state_character table.",
            "A 6-band Hamiltonian is more grid-sensitive than a one-band one; "
            "the refined rerun measures that rather than assuming it.",
        ],
        unvalidated_syntax=UNVALIDATED_SYNTAX,
    )
    return sweeps.finish_run(context, results=results, manifest=manifest)


def _series(
    results: Sequence[sweeps.CaseResult], parameter: str, observable: str
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for result in results:
        value = result.observables.get(observable)
        swept = result.spec.swept.get(parameter)
        if value is None or swept is None:
            continue
        xs.append(float(swept))
        ys.append(float(value))
    return xs, ys


def _sweep_plots(
    parent: Path,
    model_results: Sequence[sweeps.CaseResult],
    indium_results: Sequence[sweeps.CaseResult],
    width_results: Sequence[sweeps.CaseResult],
    grid_results: Sequence[sweeps.CaseResult],
) -> None:
    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    by_model = {
        str(result.observables.get("model")): result
        for result in model_results
        if result.solver_success
    }

    def band_series(name: str, column: int) -> tuple[list[float], list[float]]:
        result = by_model.get(name)
        if result is None:
            return ([], [])
        path = result.run_dir / "extracted" / "band_edges.csv"
        if not path.is_file():
            return ([], [])
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        if data.shape[1] <= column:
            return ([], [])
        return (data[:, 0].tolist(), data[:, column].tolist())

    plotting.line_plot(
        plots_dir / "strained_vs_unstrained_bandedges.png",
        title="Band edges with strain disabled and enabled",
        xlabel="Position (nm)",
        ylabel="Energy (eV)",
        series={
            "unstrained Γ": band_series("M1_classical_unstrained", 1),
            "strained Γ": band_series("M2_classical_strained", 1),
            "unstrained HH": band_series("M1_classical_unstrained", 2),
            "strained HH": band_series("M2_classical_strained", 2),
            "unstrained LH": band_series("M1_classical_unstrained", 3),
            "strained LH": band_series("M2_classical_strained", 3),
        },
        markers=False,
    )
    strained = by_model.get("M2_classical_strained")
    strain_series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    if strained is not None:
        path = strained.run_dir / "extracted" / "hydrostatic_strain.csv"
        if path.is_file():
            data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
            strain_series["hydrostatic strain"] = (data[:, 0], data[:, 1])
    plotting.line_plot(
        plots_dir / "strain_profile.png",
        title="Hydrostatic strain in the strained classical reference",
        xlabel="Position (nm)",
        ylabel="Hydrostatic strain",
        series=strain_series,
        markers=False,
    )
    one_band = by_model.get("M3_oneband_electron_hh")
    six_band = by_model.get("M4_sixband_valence")
    series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    for label, result in (("one-band holes", one_band), ("6-band holes", six_band)):
        if result is None:
            continue
        energies = result.observables.get("hole_energies_eV") or []
        if energies:
            series[label] = (list(range(1, len(energies) + 1)), [float(e) for e in energies])
    plotting.line_plot(
        plots_dir / "oneband_vs_sixband_holes.png",
        title="Hole energies: one-band versus 6-band valence k·p",
        xlabel="State index (confinement order, not ascending eV)",
        ylabel="Energy (eV)",
        series=series,
    )
    plotting.line_plot(
        plots_dir / "transitions_vs_indium.png",
        title="e1–h1 transition energy versus indium fraction",
        xlabel="Indium fraction x",
        ylabel="Transition energy (eV)",
        series={
            "e1–h1": _series(indium_results, "indium_fraction", "interband_transition_e1_h1_eV")
        },
    )
    plotting.line_plot(
        plots_dir / "transitions_vs_width.png",
        title="e1–h1 transition energy versus well width",
        xlabel="Well width (nm)",
        ylabel="Transition energy (eV)",
        series={
            "e1–h1": _series(width_results, "well_width_nm", "interband_transition_e1_h1_eV")
        },
    )
    density_series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    if six_band is not None:
        for prefix, filename in (
            ("electron", "electron_densities.csv"),
            ("6-band hole", "hole_densities.csv"),
        ):
            path = six_band.run_dir / "extracted" / filename
            if not path.is_file():
                continue
            data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
            for index in range(1, min(data.shape[1], 3)):
                density_series[f"{prefix} state {index}"] = (
                    data[:, 0],
                    data[:, index],
                )
    plotting.line_plot(
        plots_dir / "probability_densities.png",
        title="Representative electron and 6-band hole probability densities",
        xlabel="Position (nm)",
        ylabel="Probability density (nm$^{-1}$)",
        series=density_series,
        markers=False,
    )
    characters = [
        (result.spec.case_id, result.observables.get("mixed_state_count"))
        for result in [*indium_results, *width_results]
        if result.observables.get("mixed_state_count") is not None
    ]
    plotting.bar_plot(
        plots_dir / "character_vs_parameter.png",
        title="Number of hole states with ambiguous (mixed) character",
        xlabel="Case",
        ylabel="Mixed-character state count",
        labels=[name for name, _ in characters],
        values=[float(value) for _, value in characters],
    )
    _state_character_plot(plots_dir, six_band)

    grid_labels: list[str] = []
    grid_values: list[float] = []
    for label, result in (("production mesh", six_band), ("refined mesh", grid_results[0] if grid_results else None)):
        if result is None or result.observables.get("E1_electron_eV") is None:
            continue
        grid_labels.append(label)
        grid_values.append(float(result.observables["E1_electron_eV"]))
    plotting.bar_plot(
        plots_dir / "grid_sensitivity.png",
        title="Six-band reference electron E1 under mesh refinement",
        xlabel="Mesh",
        ylabel="E1 electron (eV)",
        labels=grid_labels,
        values=grid_values,
    )


def _state_character_plot(
    plots_dir: Path, result: sweeps.CaseResult | None
) -> None:
    import json
    import matplotlib.pyplot as plt

    target = plots_dir / "state_character.png"
    if result is None:
        plotting.placeholder(target, "HH/LH/SO composition of each hole state")
        return
    path = result.run_dir / "extracted" / "hole_characters.json"
    if not path.is_file():
        plotting.placeholder(target, "HH/LH/SO composition of each hole state")
        return
    rows = json.loads(path.read_text(encoding="utf-8"))
    components = sorted(
        {
            key
            for row in rows
            for key in row
            if key not in {"state", "character", "dominant_fraction"}
        }
    )
    if not rows or not components:
        plotting.placeholder(target, "HH/LH/SO composition of each hole state")
        return
    states = np.asarray([int(row["state"]) for row in rows])
    bottom = np.zeros(len(rows), dtype=float)
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    for component in components:
        values = np.asarray([float(row.get(component, 0.0)) for row in rows])
        ax.bar(states, values, bottom=bottom, label=component)
        bottom += values
    ax.set(
        title="Six-band hole-state composition",
        xlabel="Hole state (confinement order)",
        ylabel="Normalised component weight",
        ylim=(0.0, 1.05),
    )
    ax.legend(fontsize=8, ncol=3)
    plotting.save_figure(fig, target)


def _all_true(results: Sequence[sweeps.CaseResult], key: str) -> bool | None:
    values = [
        result.validation.get(key)
        for result in results
        if result.solver_success and key in result.validation
    ]
    if not values:
        return None
    return all(bool(value) for value in values)
