"""Demo 6 — doped coupled well, staged to a self-consistent solution.

Electrons and the potential they sit in determine each other, so neither can be
computed first.  The demo walks the coupling on in four stages so that every
change in the answer is attributable to exactly one newly enabled mechanism,
then repeats the final stage across doping.

The recurring trap this demo is built around: ``run{ quantum_poisson{} }``
finishes with ``DONE.`` and writes ``job_done.txt`` even when it has not
converged.  Completion is read from one place and convergence from another, and
a run that hits the iteration cap is reported as ``max_iterations_reached``.
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
    ("undoped_vs_doped_bandedges.png", "Undoped versus doped conduction band"),
    ("classical_vs_selfconsistent.png", "Classical Poisson versus self-consistent"),
    ("densities.png", "Electron density and ionized donors"),
    ("electrostatic_potential.png", "Electrostatic potential"),
    ("electric_field.png", "Electric field"),
    ("subband_energies_vs_doping.png", "Subband energies versus doping"),
    ("population_vs_doping.png", "Electron population versus doping"),
    ("iteration_residuals.png", "Residual versus iteration"),
    ("potential_change_vs_iteration.png", "Potential change versus iteration"),
    ("convergence_status.png", "Convergence status of every case"),
    ("charge_balance.png", "Integrated charge balance versus doping"),
)

DONOR_NAME = "si_donor"


def build_stack(cfg: Mapping[str, Any]) -> layers.LayerStack:
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    return layers.asymmetric_double_well(
        left_well_width_nm=float(scientific["wide_well_width_nm"]),
        right_well_width_nm=float(scientific["narrow_well_width_nm"]),
        centre_barrier_nm=float(scientific["center_barrier_nm"]),
        left_outer_barrier_nm=float(scientific["left_outer_barrier_nm"]),
        right_outer_barrier_nm=float(scientific["right_outer_barrier_nm"]),
        aluminum_fraction=float(scientific["aluminum_fraction"]),
        active_grid_spacing_nm=float(numerical["active_region_grid_spacing_nm"]),
        exterior_grid_spacing_nm=float(numerical["exterior_grid_spacing_nm"]),
    )


def region_name(cfg: Mapping[str, Any]) -> str:
    return str((cfg.get("analysis") or {}).get("quantum_region_name", "cqw"))


def active_model(cfg: Mapping[str, Any]) -> dict[str, Any]:
    models = cfg.get("models") or []
    if not models:
        raise DemoError("demo.yaml must declare at least one model stage.")
    return dict(models[0])


def check_doping_geometry(cfg: Mapping[str, Any]) -> float:
    """Confirm the donor layer really is separated from the first well.

    Returns the actual spacer thickness. Modulation doping is the whole point of
    the stage; a donor layer that overlaps a well would bend the bands for a
    different reason and the demo would teach the wrong lesson.
    """

    scientific = cfg["scientific"]
    start = float(scientific["donor_region_start_nm"])
    end = float(scientific["donor_region_end_nm"])
    first_well_start = float(scientific["left_outer_barrier_nm"])
    if end <= start:
        raise DemoError("donor_region_end_nm must exceed donor_region_start_nm.")
    if end > first_well_start:
        raise DemoError(
            f"the donor layer [{start}, {end}] nm overlaps the first well, which "
            f"starts at {first_well_start} nm. Modulation doping requires a spacer."
        )
    actual_spacer = first_well_start - end
    requested = float(scientific["spacer_thickness_nm"])
    if abs(actual_spacer - requested) > 1e-6:
        raise DemoError(
            f"spacer_thickness_nm is {requested} nm but the geometry gives "
            f"{actual_spacer} nm (donor layer ends at {end} nm, first well starts "
            f"at {first_well_start} nm). Fix one of them rather than letting the "
            "recorded parameter disagree with the deck."
        )
    return actual_spacer


def render_values(cfg: Mapping[str, Any]) -> dict[str, Any]:
    model = active_model(cfg)
    stack = build_stack(cfg)
    scientific = cfg["scientific"]
    numerical = cfg["numerical"]
    start, end = stack.quantum_region_nm(float(numerical["quantum_region_padding_nm"]))
    doped = bool(model.get("doping"))
    if doped:
        check_doping_geometry(cfg)

    doping = (
        [
            (
                DONOR_NAME,
                float(scientific["donor_region_start_nm"]),
                float(scientific["donor_region_end_nm"]),
                float(scientific["donor_density_cm3"]),
            )
        ]
        if doped
        else []
    )
    impurities = (
        "\nimpurities{\n"
        f"    donor{{ name = \"{DONOR_NAME}\"  degeneracy = "
        f"{int(scientific['donor_degeneracy'])}  "
        f"energy = {float(scientific['donor_ionization_energy_eV']):.6g} }}\n"
        "}\n"
        if doped
        else "\n# Stage without doping: no impurities{} block at all.\n"
    )
    poisson = (
        "\npoisson{\n    output_potential{}\n    output_electric_field{}\n}\n"
        if model.get("poisson")
        else "\n# Stage without electrostatics: no poisson{} block at all.\n"
    )

    quantum = "\n# Stage without a Schrodinger equation: no quantum{} block.\n"
    if model.get("quantum"):
        density_lines = ""
        no_density = "        no_density = yes\n"
        if model.get("quantum_density"):
            no_density = ""
            density_lines = (
                "        output_subband_densities{}\n"
                "        output_quantum_densities{}\n"
            )
        quantum = (
            "\nquantum{\n"
            "    region{\n"
            f"        name = \"{region_name(cfg)}\"\n"
            f"        x = [{start:.9g}, {end:.9g}]\n"
            f"{no_density}"
            "        boundary{ x = dirichlet }\n"
            f"        Gamma{{ num_ev = {int(numerical['number_of_states'])} }}\n"
            "        output_states{\n"
            f"            max_num       = {int(numerical['number_of_states'])}\n"
            "            envelopes     = yes\n"
            "            probabilities = yes\n"
            "        }\n"
            f"{density_lines}"
            "    }\n"
            "}\n"
        )

    run_mode = str(model.get("run_mode", "quantum"))
    if run_mode == "quantum":
        run_block = "run{\n    quantum{}\n}\n"
    elif run_mode == "poisson":
        run_block = "run{\n    poisson{}\n}\n"
    elif run_mode == "poisson_quantum":
        run_block = "run{\n    poisson{}\n    quantum{}\n}\n"
    elif run_mode == "quantum_poisson":
        run_block = (
            "run{\n"
            "    quantum_poisson{\n"
            f"        iterations      = {int(numerical['maximum_iterations'])}\n"
            f"        residual        = {float(numerical['poisson_tolerance']):.6g}\n"
            f"        alpha_potential = {float(numerical['potential_mixing_alpha']):.6g}\n"
            "        output_log      = yes\n"
            "    }\n"
            "}\n"
        )
    else:
        raise DemoError(f"unsupported run_mode {run_mode!r} in models.")

    return {
        "temperature_K": scientific["temperature_K"],
        "contact_bias_V": f"{float(scientific['contact_bias_V']):.9g}",
        "grid_lines": stack.grid_lines(),
        "structure_regions": stack.structure_regions(
            contact_name="qw_contact",
            contact_thickness_nm=float(scientific["contact_thickness_nm"]),
            doping=doping,
        ),
        "impurities_block": impurities,
        "poisson_block": poisson,
        "quantum_block": quantum,
        "run_block": run_block,
    }


def _read_optional(
    profile: outputs.ParserProfile, raw: Path, key: str, region: str
) -> Path | None:
    found = outputs.resolve_outputs(profile, raw, [key], substitutions={"region": region})
    paths = found.many(key)
    return paths[0] if paths else None


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
        "run_mode": model.get("run_mode"),
        "doping_enabled": bool(model.get("doping")),
        "poisson_enabled": bool(model.get("poisson")),
        "quantum_enabled": bool(model.get("quantum")),
        "quantum_density_enabled": bool(model.get("quantum_density")),
        "donor_density_cm3": float(cfg["scientific"]["donor_density_cm3"]),
        "quantum_region_padding_nm": float(cfg["numerical"]["quantum_region_padding_nm"]),
    }
    validation: dict[str, Any] = {}

    band_path = outputs.resolve_outputs(profile, raw, ["bandedges"]).one("bandedges")
    band_table = outputs.read_table(band_path)
    band_edges = band_table.select(dict(cfg["outputs"]["bandedge_columns"]))
    position = band_edges["position_nm"]
    conduction = band_edges["conduction_eV"]
    write_csv(extracted / "band_edges.csv", band_edges)
    observables["grid_points"] = int(position.size)
    observables["conduction_band_min_eV"] = float(np.min(conduction))
    observables["conduction_band_max_eV"] = float(np.max(conduction))
    observables["conduction_band_bending_meV"] = float(
        1000.0 * (np.max(conduction) - np.min(conduction))
    )
    write_csv(
        extracted / "conduction_band.csv",
        {"position_nm": position, "conduction_eV": conduction},
    )
    if band_table.n_columns >= 7:
        electron_fermi = band_table.column(5)
        hole_fermi = band_table.column(6)
        write_csv(
            extracted / "fermi_levels.csv",
            {
                "position_nm": band_table.column(0),
                "electron_fermi_level_eV": electron_fermi,
                "hole_fermi_level_eV": hole_fermi,
            },
        )
        observables["electron_fermi_level_eV"] = float(np.median(electron_fermi))
        observables["hole_fermi_level_eV"] = float(np.median(hole_fermi))

    if model.get("poisson"):
        potential_path = _read_optional(profile, raw, "potential", region)
        field_path = _read_optional(profile, raw, "electric_field", region)
        if potential_path is None:
            raise DemoError("Poisson was enabled but no potential.dat was written.")
        potential_table = outputs.read_table(potential_path)
        potential_x, potential = potential_table.column(0), potential_table.column(1)
        np.savetxt(
            extracted / "potential.csv",
            np.column_stack([potential_x, potential]),
            delimiter=",",
            header="position_nm,potential_V",
            comments="",
        )
        observables["potential_swing_V"] = float(np.max(potential) - np.min(potential))
        if field_path is not None:
            field_table = outputs.read_table(field_path)
            np.savetxt(
                extracted / "electric_field.csv",
                np.column_stack([field_table.column(0), field_table.column(1)]),
                delimiter=",",
                header="position_nm,electric_field_kV_cm",
                comments="",
            )
            observables["peak_electric_field_kV_cm"] = float(
                np.max(np.abs(field_table.column(1)))
            )

    # --- densities and charge balance ---------------------------------------
    if model.get("doping"):
        designed_path = _read_optional(profile, raw, "designed_donor_density", region)
        if designed_path is not None:
            designed_table = outputs.read_table(designed_path)
            write_csv(
                extracted / "designed_donor_density.csv",
                {
                    "position_nm": designed_table.column(0),
                    "designed_donor_density_cm3": designed_table.column(1)
                    * 1.0e18,
                },
            )
        electron_path = _read_optional(profile, raw, "electron_density", region)
        donor_path = _read_optional(profile, raw, "ionized_donor_density", region)
        hole_path = _read_optional(profile, raw, "hole_density", region)
        acceptor_path = _read_optional(profile, raw, "ionized_acceptor_density", region)
        if electron_path is not None and donor_path is not None:
            electron_table = outputs.read_table(electron_path)
            donor_table = outputs.read_table(donor_path)
            grid = electron_table.column(0)
            # nextnano++ reports these in units of 1e18 cm^-3 (header-declared).
            scale = 1.0e18
            electrons = electron_table.column(1) * scale
            donors = donor_table.column(1) * scale
            holes = (
                outputs.read_table(hole_path).column(1) * scale
                if hole_path is not None
                else None
            )
            acceptors = (
                outputs.read_table(acceptor_path).column(1) * scale
                if acceptor_path is not None
                else None
            )
            np.savetxt(
                extracted / "densities.csv",
                np.column_stack(
                    [grid, electrons, donors]
                    + ([holes] if holes is not None else [])
                ),
                delimiter=",",
                header="position_nm,electron_density_cm3,ionized_donor_density_cm3"
                + (",hole_density_cm3" if holes is not None else ""),
                comments="",
            )
            balance = analysis.charge_balance(
                grid,
                electron_density_cm3=electrons,
                ionized_donor_density_cm3=donors,
                hole_density_cm3=holes,
                ionized_acceptor_density_cm3=acceptors,
            )
            observables.update(balance)
            validation["charge_balanced"] = bool(
                balance["relative_charge_imbalance"]
                <= float(
                    analysis_cfg.get(
                        "maximum_charge_imbalance",
                        validation_cfg.get("maximum_charge_imbalance", 0.05),
                    )
                )
            )

    # --- quantum states ------------------------------------------------------
    if model.get("quantum"):
        run = quantum1d.parse_one_band_run(
            raw,
            profile=profile,
            region_name=region,
            bandedge_columns=cfg["outputs"]["bandedge_columns"],
            want_potential=bool(model.get("poisson")),
        )
        states = quantum1d.state_table(
            run,
            regions=regions,
            minimum_confined_probability=float(
                validation_cfg.get("minimum_confined_probability", 0.4)
            ),
            normalisation_tolerance=float(
                validation_cfg.get("normalization_tolerance", 1e-3)
            ),
            boundary_edge_fraction=float(analysis_cfg.get("boundary_edge_fraction", 0.05)),
            quantum_window_nm=window,
        )
        if not states:
            raise DemoError("quantum was enabled but no states were parsed.")
        rows = [state.as_row() for state in states]
        write_csv(
            extracted / "states.csv",
            {key: np.asarray([row.get(key) for row in rows]) for key in rows[0]},
        )
        energies = [state.energy_eV for state in states]
        observables.update(
            {
                "electron_energies_eV": energies,
                "E1_eV": energies[0],
                "E2_eV": energies[1] if len(energies) > 1 else None,
                "E3_eV": energies[2] if len(energies) > 2 else None,
                **analysis.energy_splittings_meV(energies),
                "bound_state_count": sum(1 for state in states if state.bound),
                "maximum_boundary_probability_bound_states": max(
                    [state.boundary_probability for state in states if state.bound] or [0.0]
                ),
                "state_rows": rows,
            }
        )
        validation.update(
            {
                "energies_finite_and_ordered": bool(
                    np.all(np.isfinite(energies)) and np.all(np.diff(energies) > 0)
                ),
                "probability_normalized": all(state.normalised for state in states),
                "at_least_one_bound_state": any(state.bound for state in states),
                "bound_state_boundary_probability_small": bool(
                    observables["maximum_boundary_probability_bound_states"]
                    <= float(validation_cfg.get("maximum_boundary_probability", 1e-3))
                ),
            }
        )

        occupation_path = _read_optional(profile, raw, "occupation_gamma", region)
        if occupation_path is not None:
            occupation_table = outputs.read_table(occupation_path)
            occupations = occupation_table.column(1)
            np.savetxt(
                extracted / "occupations.csv",
                np.column_stack([occupation_table.column(0), occupations]),
                delimiter=",",
                header="state,occupation_cm2",
                comments="",
            )
            total = float(np.sum(occupations))
            observables["total_electron_sheet_density_cm2"] = total
            observables["subband_occupations_cm2"] = occupations.tolist()
            observables["occupied_subband_count"] = int(
                np.sum(occupations > 0.01 * max(total, 1e-30))
            )

    log_checks = outputs.scan_log_markers(
        outputs.solver_log_text(raw),
        completion_markers=validation_cfg.get("completion_markers", ()),
        fatal_markers=validation_cfg.get("fatal_markers", ()),
        warning_markers=validation_cfg.get("convergence_warning_markers", ()),
    )
    log_checks.update(outputs.completion_evidence(raw))

    # --- self-consistency ----------------------------------------------------
    if str(model.get("run_mode")) == "quantum_poisson":
        iteration_path = _read_optional(profile, raw, "iteration_quantum_poisson", region)
        if iteration_path is None:
            raise DemoError(
                "the self-consistent stage wrote no iteration_quantum_poisson.dat; "
                "convergence cannot be judged."
            )
        table = outputs.read_table(iteration_path)
        names = [name for name, _ in table.header]
        history = {
            names[index] if index < len(names) else f"column_{index}": table.data[:, index]
            for index in range(table.n_columns)
        }
        np.savetxt(
            extracted / "iteration_history.csv",
            table.data,
            delimiter=",",
            header=",".join(names) if names else "",
            comments="",
        )
        residual_columns = {
            name: values for name, values in history.items() if "Residual" in name
        }
        # Density residuals are absolute sheet densities in cm^-2 and sit near
        # 1e12; only the potential residual shares units with the solver's own
        # `residual` parameter. Each is therefore scaled by its own magnitude
        # before being compared with the tolerance.
        sheet_reference = abs(
            float(observables.get("electron_sheet_density_cm2") or 0.0)
        ) or abs(float(observables.get("ionized_donor_sheet_density_cm2") or 0.0))
        scales = {
            name: (sheet_reference or 1.0)
            for name in residual_columns
            if "Density" in name
        }
        convergence = analysis.classify_convergence(
            table.data[:, 0],
            residual_columns,
            tolerance=float(cfg["numerical"]["poisson_tolerance"]),
            maximum_iterations=int(cfg["numerical"]["maximum_iterations"]),
            reference_scales=scales,
            solver_reported_failure=bool(log_checks.get("warning_markers_found")),
        )
        write_json_atomically(extracted / "convergence.json", convergence)
        observables["convergence"] = convergence
        observables["convergence_state"] = convergence["status"]
        observables["iterations_run"] = convergence["iterations_run"]
        observables["final_potential_residual_V"] = convergence["final_residuals"].get(
            "Residual_Potential"
        )
        observables["final_relative_residuals"] = convergence["final_relative_residuals"]
        validation["self_consistent_loop_converged"] = bool(convergence["converged"])
        validation["iteration_cap_not_reached"] = bool(
            convergence["status"] != "max_iterations_reached"
        )

    observables["solver_warnings"] = log_checks.get("warning_markers_found", [])
    validation.update(
        {key: value for key, value in log_checks.items() if isinstance(value, bool)}
    )

    _per_case_plots(cfg, model, extracted, plots_dir)
    return observables, validation


def _per_case_plots(
    cfg: Mapping[str, Any],
    model: Mapping[str, Any],
    extracted: Path,
    plots_dir: Path,
) -> None:
    if not cfg["outputs"].get("write_plots", True):
        return
    label = str(model.get("name"))
    band = extracted / "conduction_band.csv"
    if band.is_file():
        data = np.loadtxt(band, delimiter=",", skiprows=1)
        plotting.line_plot(
            plots_dir / "conduction_band.png",
            title=f"Conduction band ({label})",
            xlabel="Position (nm)",
            ylabel="Ec (eV)",
            series={"Ec": (data[:, 0], data[:, 1])},
            markers=False,
        )
    densities = extracted / "densities.csv"
    if densities.is_file():
        data = np.loadtxt(densities, delimiter=",", skiprows=1)
        plotting.line_plot(
            plots_dir / "densities.png",
            title=f"Electron and ionized-donor densities ({label})",
            xlabel="Position (nm)",
            ylabel="Density (cm$^{-3}$)",
            series={
                "electrons": (data[:, 0], data[:, 1]),
                "ionized donors": (data[:, 0], data[:, 2]),
            },
            markers=False,
        )
    potential = extracted / "potential.csv"
    if potential.is_file():
        data = np.loadtxt(potential, delimiter=",", skiprows=1)
        plotting.line_plot(
            plots_dir / "potential.png",
            title=f"Electrostatic potential ({label})",
            xlabel="Position (nm)",
            ylabel="φ (V)",
            series={"φ": (data[:, 0], data[:, 1])},
            markers=False,
        )
    history = extracted / "iteration_history.csv"
    if history.is_file():
        data = np.loadtxt(history, delimiter=",", skiprows=1, ndmin=2)
        header = history.read_text(encoding="utf-8").splitlines()[0].split(",")
        series = {
            header[index]: (data[:, 0], np.abs(data[:, index]))
            for index in range(1, data.shape[1])
            if "Residual" in header[index]
        }
        plotting.line_plot(
            plots_dir / "iteration_residuals.png",
            title=f"Self-consistency residuals ({label})",
            xlabel="Iteration",
            ylabel="Residual (see legend for units)",
            series=series,
            logy=True,
        )


def model_case(
    cfg: Mapping[str, Any], model: Mapping[str, Any], case_id: str, **overrides: Any
) -> sweeps.CaseSpec:
    """Build one staged case; the resolved YAML records the single active stage."""

    config = (
        sweeps.apply_overrides(cfg, overrides) if overrides else sweeps.copy_config(cfg)
    )
    config["models"] = [dict(model)]
    return sweeps.CaseSpec(
        case_id=case_id,
        label=f"{model.get('name')}"
        + (f" ({overrides})" if overrides else ""),
        swept=dict(overrides),
        config=config,
        metadata={"sweep_kind": "model_stage", "model": str(model.get("name"))},
    )


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    models = cfg.get("models") or []
    if not models:
        raise DemoError("demo.yaml must declare the staged models for Demo 6.")
    sweep_cfg = cfg.get("sweeps") or {}
    analysis_cfg = cfg.get("analysis") or {}
    sweep_model_name = str(analysis_cfg.get("sweep_model", models[-1]["name"]))
    sweep_model = next(
        (model for model in models if str(model["name"]) == sweep_model_name), models[-1]
    )

    cases: list[sweeps.CaseSpec] = []
    for index, model in enumerate(models, start=1):
        cases.append(
            model_case(cfg, model, f"stage_{index:02d}_{str(model['name'])[:1]}")
        )
    stage_count = len(cases)
    for index, value in enumerate(sweep_cfg.get("donor_density_cm3", []), start=1):
        cases.append(
            model_case(
                cfg,
                sweep_model,
                f"nd_{index:02d}_{sweeps.safe_token(value)}",
                donor_density_cm3=value,
            )
        )
    doping_count = len(cases) - stage_count
    for index, value in enumerate(sweep_cfg.get("quantum_region_padding_nm", []), start=1):
        cases.append(
            model_case(
                cfg,
                sweep_model,
                f"pad_{index:02d}_{sweeps.safe_token(value)}",
                quantum_region_padding_nm=value,
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
    stage_results = results[:stage_count]
    doping_results = results[stage_count : stage_count + doping_count]
    padding_results = results[stage_count + doping_count :]

    sweeps.write_sweep_summary(context.parent, results)
    failed, suspicious = sweeps.write_failed_and_suspicious(context.parent, results)
    sweeps.write_table(
        context.parent,
        "stage_comparison",
        [
            {
                "stage": result.observables.get("model") or result.spec.case_id,
                "run_mode": result.observables.get("run_mode"),
                "doping": result.observables.get("doping_enabled"),
                "poisson": result.observables.get("poisson_enabled"),
                "quantum": result.observables.get("quantum_enabled"),
                "self_consistent": result.observables.get("quantum_density_enabled"),
                "band_bending_meV": result.observables.get("conduction_band_bending_meV"),
                "E1_eV": result.observables.get("E1_eV"),
                "E2_eV": result.observables.get("E2_eV"),
                "total_sheet_density_cm2": result.observables.get(
                    "total_electron_sheet_density_cm2"
                ),
                "convergence_state": result.observables.get("convergence_state"),
                "status": result.status,
            }
            for result in stage_results
        ],
    )
    sweeps.write_table(
        context.parent,
        "doping_sweep",
        [
            {
                "donor_density_cm3": result.spec.swept.get("donor_density_cm3"),
                "E1_eV": result.observables.get("E1_eV"),
                "E2_eV": result.observables.get("E2_eV"),
                "E21_meV": result.observables.get("E21_meV"),
                "occupied_subband_count": result.observables.get("occupied_subband_count"),
                "total_sheet_density_cm2": result.observables.get(
                    "total_electron_sheet_density_cm2"
                ),
                "electron_sheet_density_cm2": result.observables.get(
                    "electron_sheet_density_cm2"
                ),
                "ionized_donor_sheet_density_cm2": result.observables.get(
                    "ionized_donor_sheet_density_cm2"
                ),
                "relative_charge_imbalance": result.observables.get(
                    "relative_charge_imbalance"
                ),
                "convergence_state": result.observables.get("convergence_state"),
                "iterations_run": result.observables.get("iterations_run"),
                "status": result.status,
            }
            for result in doping_results
        ],
    )
    sweeps.write_convergence_summary(
        context.parent,
        title="Demo 6 — self-consistency status of every case",
        rows=[
            {
                "case": result.spec.case_id,
                "model": result.observables.get("model"),
                "status": result.status,
                "convergence_state": result.observables.get("convergence_state"),
                "iterations_run": result.observables.get("iterations_run"),
                "final_potential_residual_V": result.observables.get(
                    "final_potential_residual_V"
                ),
                "solver_warnings": ";".join(result.observables.get("solver_warnings") or []),
            }
            for result in results
        ],
        commentary=[
            "`converged` requires the final residuals to be at or below "
            "numerical.poisson_tolerance BEFORE the iteration cap.",
            "`max_iterations_reached` is reported separately and is never counted "
            "as convergence, even though nextnano++ still exits successfully and "
            "writes job_done.txt.",
            "If a case fails to converge, check the physical setup first — donor "
            "placement, spacer, contact, quantum-region size. Only then consider "
            "numerical.potential_mixing_alpha.",
            "Raising the tolerance or lowering the iteration count to obtain a "
            "'converged' label is not a fix.",
        ],
    )
    _sweep_plots(context.parent, stage_results, doping_results)
    plotting.ensure_plot_set(
        context.parent / "plots",
        PLOT_SET,
        reason=(
            "Per-case figure: produced inside each runs/<case>/plots directory once "
            "a licensed solver has run. No solver output on this machine."
        ),
    )

    padding_differences_meV: dict[str, float] = {}
    for state_key in ("E1_eV", "E2_eV"):
        values = [
            float(result.observables[state_key])
            for result in padding_results
            if result.observables.get(state_key) is not None
        ]
        if len(values) >= 2:
            padding_differences_meV[state_key] = 1000.0 * (
                max(values) - min(values)
            )
    padding_stable: bool | None = None
    if len(padding_differences_meV) == 2:
        padding_stable = all(
            difference
            <= float(cfg["validation"].get("absolute_energy_tolerance_meV", 1.0))
            for difference in padding_differences_meV.values()
        )
    bending = {
        str(result.observables.get("model")): result.observables.get(
            "conduction_band_bending_meV"
        )
        for result in stage_results
    }
    doping_bends_bands: bool | None = None
    undoped = bending.get("A_undoped_no_poisson")
    doped = bending.get("B_doped_classical_poisson")
    if undoped is not None and doped is not None:
        doping_bends_bands = bool(float(doped) > float(undoped) + 1.0)

    manifest = sweeps.write_sweep_manifest(
        context.parent,
        cfg=cfg,
        machine=context.machine,
        results=results,
        dependency_report=context.dependency_report,
        parser_provenance={"profile": cfg["outputs"].get("parser_profile")},
        extra={
            "stage_count": stage_count,
            "doping_sweep_count": doping_count,
            "converged_case_count": sum(
                1
                for result in results
                if result.observables.get("convergence_state") == "converged"
            ),
            "max_iteration_case_count": sum(
                1
                for result in results
                if result.observables.get("convergence_state") == "max_iterations_reached"
            ),
            "doping_bends_bands": doping_bends_bands,
            "energies_stable_under_padding": padding_stable,
            "padding_energy_range_meV": padding_differences_meV,
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
                "all five stages produced a generated input",
                len(stage_results) == stage_count and stage_count >= 4,
                "Stages A–D plus the Stage-E doping sweep",
            ),
            (
                "no case was discarded",
                len(results) == len(cases),
                f"{len(failed)} failed/skipped and {len(suspicious)} suspicious rows retained",
            ),
            (
                "doping bends the conduction band",
                doping_bends_bands,
                "Stage B band bending exceeds Stage A by more than 1 meV",
            ),
            (
                "self-consistent loop converged below tolerance",
                _all_true(results, "self_consistent_loop_converged"),
                "final residuals at or below numerical.poisson_tolerance",
            ),
            (
                "no case merely hit the iteration cap",
                _all_true(results, "iteration_cap_not_reached"),
                "reaching numerical.maximum_iterations is not convergence",
            ),
            (
                "solver reported no convergence warning",
                _all_true(results, "no_convergence_warning"),
                "'failed to converge' in summary.log while still exiting DONE",
            ),
            (
                "integrated charge balances",
                _all_true(results, "charge_balanced"),
                "electron sheet density against ionized donors, in cm^-2",
            ),
            (
                "at least one bound state in every quantum stage",
                _all_true(results, "at_least_one_bound_state"),
                "physical bound test, not eigenvalue index",
            ),
            (
                "energies stable under larger quantum-region padding",
                padding_stable,
                "band bending must come from charge, not from the box",
            ),
        ],
        notes=[
            "Doping range basis: the vendor examples shipped with nextnano++ 3.0.0 "
            "(basics_1D_doping_heterostructure.nnp, 1e18–1e19 cm^-3) and this "
            "repository's hello_06c p-i-n deck (1e18 cm^-3). The sweep stays inside "
            "that band; it was not invented.",
            "The contact is a thin slab, not everywhere{}. A domain-wide contact "
            "pins the potential once Poisson runs and no band bending can appear.",
            "Doping is never increased in order to populate a desired subband. The "
            "sweep exists to show what doping does, not to manufacture an outcome.",
            "Densities are reported by nextnano++ in units of 1e18 cm^-3; the "
            "parser rescales them to cm^-3 before any integration, and the sheet "
            "densities are in cm^-2.",
        ],
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
    stage_results: Sequence[sweeps.CaseResult],
    doping_results: Sequence[sweeps.CaseResult],
) -> None:
    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    by_model = {
        str(result.observables.get("model")): result
        for result in stage_results
        if result.solver_success
    }

    def band_series(name: str) -> tuple[list[float], list[float]]:
        result = by_model.get(name)
        if result is None:
            return ([], [])
        path = result.run_dir / "extracted" / "conduction_band.csv"
        if not path.is_file():
            return ([], [])
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        return (data[:, 0].tolist(), data[:, 1].tolist())

    plotting.line_plot(
        plots_dir / "undoped_vs_doped_bandedges.png",
        title="Conduction band: undoped baseline versus doped with Poisson",
        xlabel="Position (nm)",
        ylabel="Ec (eV)",
        series={
            "A: undoped, no Poisson": band_series("A_undoped_no_poisson"),
            "B: doped, classical Poisson": band_series("B_doped_classical_poisson"),
        },
        markers=False,
    )
    plotting.line_plot(
        plots_dir / "classical_vs_selfconsistent.png",
        title="Conduction band: classical Poisson versus self-consistent",
        xlabel="Position (nm)",
        ylabel="Ec (eV)",
        series={
            "C: quantum on the classical potential": band_series(
                "C_quantum_on_poisson_potential"
            ),
            "D: self-consistent": band_series("D_self_consistent"),
        },
        markers=False,
    )
    plotting.line_plot(
        plots_dir / "subband_energies_vs_doping.png",
        title="Subband energies versus donor density",
        xlabel="Donor density (cm$^{-3}$)",
        ylabel="Energy (eV)",
        series={
            "E1": _series(doping_results, "donor_density_cm3", "E1_eV"),
            "E2": _series(doping_results, "donor_density_cm3", "E2_eV"),
            "E3": _series(doping_results, "donor_density_cm3", "E3_eV"),
        },
    )
    plotting.line_plot(
        plots_dir / "population_vs_doping.png",
        title="Electron sheet density versus donor density",
        xlabel="Donor density (cm$^{-3}$)",
        ylabel="Sheet density (cm$^{-2}$)",
        series={
            "total": _series(
                doping_results, "donor_density_cm3", "total_electron_sheet_density_cm2"
            ),
            "integrated electron density": _series(
                doping_results, "donor_density_cm3", "electron_sheet_density_cm2"
            ),
        },
    )
    plotting.line_plot(
        plots_dir / "charge_balance.png",
        title="Charge balance versus donor density",
        xlabel="Donor density (cm$^{-3}$)",
        ylabel="Relative |net charge| / donor sheet density",
        series={
            "relative imbalance": _series(
                doping_results, "donor_density_cm3", "relative_charge_imbalance"
            )
        },
    )
    statuses = [
        (result.spec.case_id, result.observables.get("convergence_state") or result.status)
        for result in [*stage_results, *doping_results]
    ]
    order = {
        "converged": 3.0,
        "stopped_without_meeting_tolerance": 2.0,
        "max_iterations_reached": 1.0,
        "no_iteration_history": 0.0,
    }
    plotting.bar_plot(
        plots_dir / "convergence_status.png",
        title="Convergence status (3 = converged, 1 = only hit the iteration cap)",
        xlabel="Case",
        ylabel="Status code",
        labels=[name for name, _ in statuses],
        values=[order.get(str(status), 0.0) for _, status in statuses],
        excluded=[order.get(str(status), 0.0) < 3.0 for _, status in statuses],
    )
    _residual_plots(plots_dir, [*stage_results, *doping_results])


def _residual_plots(plots_dir: Path, results: Sequence[sweeps.CaseResult]) -> None:
    usable = [
        result
        for result in results
        if (result.run_dir / "extracted" / "iteration_history.csv").is_file()
    ]
    if not usable:
        plotting.placeholder(plots_dir / "iteration_residuals.png", "Residual versus iteration")
        plotting.placeholder(
            plots_dir / "potential_change_vs_iteration.png",
            "Potential change versus iteration",
        )
        return
    residual_series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    potential_series: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    for result in usable:
        path = result.run_dir / "extracted" / "iteration_history.csv"
        header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
        data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
        for index, name in enumerate(header):
            if "Residual_EDensity" in name:
                residual_series[f"{result.spec.case_id}: e-density"] = (
                    data[:, 0],
                    np.abs(data[:, index]),
                )
            if "Residual_Potential" in name:
                potential_series[f"{result.spec.case_id}: potential"] = (
                    data[:, 0],
                    np.abs(data[:, index]),
                )
    plotting.line_plot(
        plots_dir / "iteration_residuals.png",
        title="Electron-density residual versus iteration",
        xlabel="Iteration",
        ylabel="|Residual_EDensity| (cm$^{-2}$)",
        series=residual_series,
        markers=False,
        logy=True,
    )
    plotting.line_plot(
        plots_dir / "potential_change_vs_iteration.png",
        title="Potential residual versus iteration",
        xlabel="Iteration",
        ylabel="|Residual_Potential| (V)",
        series=potential_series,
        markers=False,
        logy=True,
    )


def _all_true(results: Sequence[sweeps.CaseResult], key: str) -> bool | None:
    values = [
        result.validation.get(key)
        for result in results
        if result.solver_success and key in result.validation
    ]
    if not values:
        return None
    return all(bool(value) for value in values)
