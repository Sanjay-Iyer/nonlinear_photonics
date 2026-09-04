"""End-to-end analysis for real Demo 23 Professional kp8 output."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import deck23
import dispersion_models
import k_integration
import physics23
import plotting
import paper_comparison
import reporting
import state_tracking
from config23 import Demo23Error, k_bz_per_nm, kmax_per_nm


MODES = ("23A", "23B", "23C", "23D")


def _aligned_to_demo21(
    tracked: state_tracking.TrackedSubbands,
    frozen: physics23.FrozenK0Inputs,
) -> dict[str, np.ndarray]:
    anchors = {
        "e1": float(frozen.states.electron_energies_eV[0]),
        "e2": float(frozen.states.electron_energies_eV[1]),
        "hh1": float(frozen.states.hole_energies_eV[0]),
        "hh2": float(frozen.states.hole_energies_eV[1]),
    }
    return {
        state: anchors[state] + np.asarray(tracked.energies_eV[state])
        - float(tracked.energies_eV[state][0])
        for state in dispersion_models.SUBBANDS
    }


def _load_spec(
    run_root: Path,
    spec: deck23.DeckSpec,
    cfg: Mapping[str, Any],
    table_root: Path,
) -> state_tracking.TrackedSubbands:
    raw = run_root / "raw" / spec.name
    if not raw.is_dir():
        raise Demo23Error(f"required real solver output is missing: {raw}")
    inventory = table_root / "inventories" / f"{spec.name}.csv"
    return state_tracking.load_and_track(raw, inventory, cfg)


def _settings_for_spec(
    base: physics23.validated.Chi2Settings,
    spec: deck23.DeckSpec,
) -> physics23.validated.Chi2Settings:
    return physics23.validated.replace_settings(
        base,
        k_parallel_points=int(spec.points),
        k_parallel_fraction_of_bz=float(spec.fraction_of_bz),
    )


def _models_for(
    tracked: state_tracking.TrackedSubbands,
    frozen: physics23.FrozenK0Inputs,
    settings: physics23.validated.Chi2Settings,
) -> tuple[dict[str, dispersion_models.SubbandDispersion], dict[str, dispersion_models.ParabolicFit], dict[str, np.ndarray]]:
    aligned = _aligned_to_demo21(tracked, frozen)
    models, fits = dispersion_models.build_models(
        raw_k_per_nm=tracked.k_per_nm,
        raw_energies_eV=aligned,
        electron_k0_eV=frozen.states.electron_energies_eV,
        heavy_hole_k0_eV=frozen.states.hole_energies_eV,
        reduced_mass_kg=settings.reduced_mass_kg(),
    )
    return models, fits, aligned


def _evaluate_spec(
    tracked: state_tracking.TrackedSubbands,
    frozen: physics23.FrozenK0Inputs,
    settings: physics23.validated.Chi2Settings,
    wavelengths: np.ndarray,
    cfg: Mapping[str, Any],
    modes: tuple[str, ...],
) -> tuple[dict[str, physics23.ModeResult], dict[str, dispersion_models.ParabolicFit], dict[str, np.ndarray]]:
    models, fits, aligned = _models_for(tracked, frozen, settings)
    k, _ = physics23.validated.k_grid(settings)
    tolerance = 1e-11 * max(1.0, settings.k_max_per_nm)
    if tracked.k_per_nm[0] > tolerance or tracked.k_per_nm[-1] < k[-1] - tolerance:
        raise Demo23Error(
            f"solver path [{tracked.k_per_nm[0]:.9g}, {tracked.k_per_nm[-1]:.9g}] does not cover "
            f"integration grid [0, {k[-1]:.9g}] nm^-1"
        )
    results = {
        mode: physics23.evaluate_mode(
            mode, models[mode], k, wavelengths, frozen, settings,
            k0_tolerance_eV=float(cfg["validation"]["k0_transition_tolerance_eV"]),
        )
        for mode in modes
    }
    return results, fits, aligned


def _write_primary_tables(
    output: Path,
    tracked: state_tracking.TrackedSubbands,
    aligned: Mapping[str, np.ndarray],
    fits: Mapping[str, dispersion_models.ParabolicFit],
    results: Mapping[str, physics23.ModeResult],
    *,
    target_wavelength_nm: float,
    broadening_meV: float,
) -> list[dict[str, Any]]:
    reporting.write_csv(output / "tables" / "state_tracking.csv", tracked.rows)
    dispersion_rows = []
    for ik, k in enumerate(tracked.k_per_nm):
        for state in dispersion_models.SUBBANDS:
            dispersion_rows.append({
                "k_per_nm": float(k),
                "state": state,
                "raw_kp8_energy_eV": float(tracked.energies_eV[state][ik]),
                "demo21_aligned_energy_eV": float(aligned[state][ik]),
                "parabolic_fit_eV": float(fits[state].evaluate(np.asarray([k]))[0]),
                "parabolic_residual_meV": 1000.0 * float(
                    aligned[state][ik] - fits[state].evaluate(np.asarray([k]))[0]
                ),
            })
    reporting.write_csv(output / "tables" / "tracked_dispersions_and_fits.csv", dispersion_rows)
    raw_transitions = (
        np.vstack([aligned["e1"], aligned["e2"]])[:, None, :]
        - np.vstack([aligned["hh1"], aligned["hh2"]])[None, :, :]
    )
    two_photon_eV = 2.0 * physics23.validated.HC_EV_NM / float(target_wavelength_nm)
    detuning_gate_eV = 5.0 * float(broadening_meV) * 1.0e-3
    fit_rows = []
    for state in dispersion_models.SUBBANDS:
        fit = fits[state]
        residual_meV = 1000.0 * (aligned[state] - fit.evaluate(tracked.k_per_nm))
        if state == "e1":
            involved = raw_transitions[0]
        elif state == "e2":
            involved = raw_transitions[1]
        elif state == "hh1":
            involved = raw_transitions[:, 0]
        else:
            involved = raw_transitions[:, 1]
        relevant = np.any(np.abs(involved - two_photon_eV) <= detuning_gate_eV, axis=0)
        record = fit.as_record()
        record.update({
            "resonance_relevant_definition": (
                f"any involved transition within {detuning_gate_eV * 1000:.6g} meV "
                f"of 2hc/{target_wavelength_nm:.6g}nm"
            ),
            "resonance_relevant_point_count": int(np.count_nonzero(relevant)),
            "resonance_relevant_max_abs_residual_meV": (
                float(np.max(np.abs(residual_meV[relevant]))) if np.any(relevant) else float("nan")
            ),
        })
        fit_rows.append(record)
    reporting.write_csv(output / "tables" / "parabolic_fit_report.csv", fit_rows)

    for mode, result in results.items():
        transition_rows = []
        values = result.transitions.as_dict()
        for ik, k in enumerate(result.transitions.k_per_nm):
            transition_rows.append({"k_per_nm": float(k), **{
                label: float(array[ik]) for label, array in values.items()
            }})
        reporting.write_csv(output / "tables" / f"{mode}_transition_energies.csv", transition_rows)
        spectrum_rows = [{
            "wavelength_nm": float(wavelength),
            "real_chi2_pm_per_V": float(value.real),
            "imag_chi2_pm_per_V": float(value.imag),
            "abs_chi2_pm_per_V": float(abs(value)),
        } for wavelength, value in zip(result.spectrum.wavelength_nm, result.spectrum.chi2)]
        reporting.write_csv(output / "spectra" / f"{mode}_chi2.csv", spectrum_rows)
    return fit_rows


def _convergence_rows(
    cfg: Mapping[str, Any], run_root: Path, output: Path,
    frozen: physics23.FrozenK0Inputs, base_settings: physics23.validated.Chi2Settings,
    wavelengths: np.ndarray, modes: tuple[str, ...], role: str,
    production_cache: tuple[state_tracking.TrackedSubbands, dict[str, physics23.ModeResult]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    spectra: dict[tuple[str, float], np.ndarray] = {}
    specs = [spec for spec in deck23.deck_specs(cfg) if spec.role == role]
    if role == "grid_convergence":
        specs.append(next(spec for spec in deck23.deck_specs(cfg) if spec.role == "production"))
    if role == "kmax_convergence":
        specs.append(next(spec for spec in deck23.deck_specs(cfg) if spec.role == "production"))
    for spec in sorted(specs, key=lambda value: (value.points, value.fraction_of_bz)):
        if spec.role == "production" and production_cache is not None:
            tracked, result_map = production_cache
            settings = _settings_for_spec(base_settings, spec)
            results = {mode: result_map[mode] for mode in modes}
        else:
            tracked = _load_spec(run_root, spec, cfg, output / "tables")
            settings = _settings_for_spec(base_settings, spec)
            results, _, _ = _evaluate_spec(tracked, frozen, settings, wavelengths, cfg, modes)
        for mode, result in results.items():
            metric = physics23.spectrum_metrics(result)
            coordinate = float(spec.points if role == "grid_convergence" else spec.fraction_of_bz)
            spectra[(mode, coordinate)] = result.spectrum.chi2
            rows.append({
                **metric,
                "N_k": int(spec.points),
                "fraction_of_bz": float(spec.fraction_of_bz),
                "kmax_per_nm": float(spec.kmax_per_nm),
                "role": role,
            })
    coordinate_key = "N_k" if role == "grid_convergence" else "fraction_of_bz"
    for mode in modes:
        coordinates = sorted(float(row[coordinate_key]) for row in rows if row["mode"] == mode)
        reference_coordinate = max(coordinates)
        reference = spectra[(mode, reference_coordinate)]
        for row in rows:
            if row["mode"] != mode:
                continue
            value = spectra[(mode, float(row[coordinate_key]))]
            relative = float(np.max(np.abs(value - reference)) / max(np.max(np.abs(reference)), 1e-300))
            row["max_complex_relative_change_vs_finest"] = relative
            row["converged_vs_finest"] = relative <= float(cfg["validation"]["convergence_relative_tolerance"])
    return rows


def _isotropy(
    cfg: Mapping[str, Any], run_root: Path, output: Path,
    primary: state_tracking.TrackedSubbands,
    frozen: physics23.FrozenK0Inputs,
) -> tuple[list[dict[str, Any]], dict[str, np.ndarray], np.ndarray]:
    candidates = [spec for spec in deck23.deck_specs(cfg) if spec.role == "isotropy"]
    if not candidates:
        return [], {}, np.asarray([])
    other = _load_spec(run_root, candidates[0], cfg, output / "tables")
    primary_aligned = _aligned_to_demo21(primary, frozen)
    other_aligned = _aligned_to_demo21(other, frozen)
    stop = min(float(primary.k_per_nm[-1]), float(other.k_per_nm[-1]))
    count = min(len(primary.k_per_nm), len(other.k_per_nm))
    k = np.linspace(0.0, stop, count)
    differences: dict[str, np.ndarray] = {}
    rows = []
    tolerance = float(cfg["validation"]["isotropy_absolute_tolerance_meV"])
    for state in dispersion_models.SUBBANDS:
        first = np.interp(k, primary.k_per_nm, primary_aligned[state])
        second = np.interp(k, other.k_per_nm, other_aligned[state])
        difference = 1000.0 * (first - second)
        differences[state] = difference
        scale = max(1000.0 * float(np.ptp(first)), 1e-12)
        rows.append({
            "state": state,
            "direction_1": str(cfg["kp8"]["production_direction"]),
            "direction_2": candidates[0].direction,
            "max_absolute_anisotropy_meV": float(np.max(np.abs(difference))),
            "relative_to_band_excursion": float(np.max(np.abs(difference)) / scale),
            "radial_assumption_pass": float(np.max(np.abs(difference))) <= tolerance,
            "tolerance_meV": tolerance,
        })
    return rows, differences, k


def analyze_run(
    cfg: Mapping[str, Any], run_root: Path, output: Path, *, selected_mode: str | None = None,
) -> dict[str, Any]:
    """Analyze a complete real run. No synthetic production path exists."""

    run_root = Path(run_root).resolve()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    frozen = physics23.load_frozen_k0_inputs(cfg)
    base_settings = physics23.settings_from_config(cfg)
    wavelengths = physics23.wavelength_grid(cfg)
    production = next(spec for spec in deck23.deck_specs(cfg) if spec.role == "production")
    tracked = _load_spec(run_root, production, cfg, output / "tables")
    modes = ("23A", str(selected_mode).upper()) if selected_mode and str(selected_mode).upper() != "23A" else (
        ("23A",) if selected_mode else MODES
    )
    results, fits, aligned = _evaluate_spec(
        tracked, frozen, base_settings, wavelengths, cfg, tuple(dict.fromkeys(modes))
    )
    error = physics23.baseline_regression_error(results["23A"], frozen, wavelengths, base_settings)
    tolerance = float(cfg["validation"]["baseline_complex_absolute_tolerance_pm_per_V"])
    if error > tolerance:
        reporting.write_json(output / "BASELINE_GATE_FAILED.json", {
            "max_complex_error_pm_per_V": error, "tolerance_pm_per_V": tolerance,
            "status": "STOPPED_BEFORE_23B_23C_23D",
        })
        raise Demo23Error(
            f"23A failed Demo 20/21 regression: {error:.6g} pm/V > {tolerance:.6g}; "
            "B/C/D were not interpreted"
        )

    fit_rows = _write_primary_tables(
        output, tracked, aligned, fits, results,
        target_wavelength_nm=float(cfg["chi2"]["target_wavelength_nm"]),
        broadening_meV=float(cfg["chi2"]["broadening_meV"]),
    )
    near_fraction = float(cfg["dispersion"]["near_zone_center_fit_fraction"])
    near_rows = []
    for state in dispersion_models.SUBBANDS:
        near = dispersion_models.fit_anchored_parabola(
            state, tracked.k_per_nm, aligned[state],
            fit_kmax_per_nm=near_fraction * float(tracked.k_per_nm[-1]),
        )
        near_rows.append({
            **near.as_record(),
            "fit_scope": f"near_zone_center_{near_fraction:.6g}_of_production_kmax",
            "mass_change_vs_full_fit_fraction": (
                (near.effective_mass_m0 - fits[state].effective_mass_m0)
                / fits[state].effective_mass_m0
            ),
        })
    reporting.write_csv(output / "tables" / "near_zone_center_fit_sensitivity.csv", near_rows)
    reference = results.get("23D")
    summary_rows = [physics23.spectrum_metrics(result, reference) for result in results.values()]
    paper_path = Path(__file__).resolve().parent / str(cfg["paper_comparison"]["digitized_simulation_csv"])
    paper_curve = paper_comparison.load_digitized_curve(paper_path)
    paper_rows = [paper_comparison.comparison_metrics(result, paper_curve) for result in results.values()]
    paper_by_mode = {str(row["mode"]): row for row in paper_rows}
    for row in summary_rows:
        paper_row = paper_by_mode[str(row["mode"])]
        row["RMSE_vs_digitized_paper_pm_per_V"] = paper_row["RMSE_vs_digitized_paper_pm_per_V"]
        row["normalized_RMSE_vs_digitized_paper"] = paper_row["normalized_RMSE_vs_digitized_paper"]
    pathway_rows = [physics23.pathway_summary(result, float(cfg["chi2"]["target_wavelength_nm"]))
                    for result in results.values()]
    reporting.write_csv(output / "tables" / "mode_summary.csv", summary_rows)
    reporting.write_csv(output / "tables" / "pathway_summary_1550nm.csv", pathway_rows)
    reporting.write_csv(output / "tables" / "paper_comparison_metrics.csv", paper_rows)
    reporting.write_csv(
        output / "tables" / "paper_reference_values.csv",
        paper_comparison.reference_rows(cfg, paper_curve),
    )
    detailed_pathways = []
    for result in results.values():
        detailed_pathways.extend(physics23.pathway_rows(
            result, float(cfg["chi2"]["target_wavelength_nm"]), "1550_nm"
        ))
        peak_nm = float(result.spectrum.wavelength_nm[int(np.argmax(result.magnitude))])
        detailed_pathways.extend(physics23.pathway_rows(result, peak_nm, "mode_spectral_peak"))
    reporting.write_csv(output / "tables" / "pathway_contributions_1550_and_peaks.csv", detailed_pathways)

    prefactor = physics23.validated.absolute_prefactor(base_settings)
    integrand_rows = []
    for result in results.values():
        target_nm = float(cfg["chi2"]["target_wavelength_nm"])
        iw = int(np.argmin(np.abs(result.spectrum.wavelength_nm - target_nm)))
        per_node = prefactor * result.spectrum.summed_integrand[iw] * result.spectrum.k_weights
        absolute_cumulative = np.cumsum(np.abs(per_node))
        fraction = absolute_cumulative / max(float(absolute_cumulative[-1]), 1e-300)
        integrand_rows.append({
            "mode": result.mode,
            "wavelength_nm": float(result.spectrum.wavelength_nm[iw]),
            "k_at_max_absolute_node_per_nm": float(result.transitions.k_per_nm[int(np.argmax(np.abs(per_node)))]),
            "k_at_10pct_absolute_weight_per_nm": float(result.transitions.k_per_nm[int(np.searchsorted(fraction, 0.10))]),
            "k_at_50pct_absolute_weight_per_nm": float(result.transitions.k_per_nm[int(np.searchsorted(fraction, 0.50))]),
            "k_at_90pct_absolute_weight_per_nm": float(result.transitions.k_per_nm[int(np.searchsorted(fraction, 0.90))]),
            "coherence_ratio": float(abs(np.sum(per_node)) / max(float(np.sum(np.abs(per_node))), 1e-300)),
        })
    reporting.write_csv(output / "tables" / "k_integrand_summary_1550nm.csv", integrand_rows)

    grid_rows = _convergence_rows(
        cfg, run_root, output, frozen, base_settings, wavelengths, tuple(results),
        "grid_convergence", (tracked, results),
    )
    kmax_rows = _convergence_rows(
        cfg, run_root, output, frozen, base_settings, wavelengths, tuple(results),
        "kmax_convergence", (tracked, results),
    )
    reporting.write_csv(output / "tables" / "k_grid_convergence.csv", grid_rows)
    reporting.write_csv(output / "tables" / "kmax_convergence.csv", kmax_rows)
    isotropy_rows, anisotropy, anisotropy_k = _isotropy(cfg, run_root, output, tracked, frozen)
    reporting.write_csv(output / "tables" / "isotropy.csv", isotropy_rows)

    interpolation_rows = []
    raw_model = dispersion_models.RawKp8(tracked.k_per_nm, aligned)
    at_nodes = raw_model.evaluate(tracked.k_per_nm)
    for state in dispersion_models.SUBBANDS:
        interpolation_rows.append({
            "state": state,
            "interpolation": str(cfg["dispersion"]["interpolation"]),
            "max_node_residual_eV": float(np.max(np.abs(at_nodes[state] - aligned[state]))),
            "extrapolation_allowed": False,
            "validated_kmin_per_nm": float(tracked.k_per_nm[0]),
            "validated_kmax_per_nm": float(tracked.k_per_nm[-1]),
        })
    reporting.write_csv(output / "tables" / "interpolation_validation.csv", interpolation_rows)

    production_weights = k_integration.radial_weights(
        results["23A"].transitions.k_per_nm,
        spin_degeneracy=base_settings.spin_degeneracy,
        convention="d2k_over_2pi_squared",
    )
    bare_weights = k_integration.radial_weights(
        results["23A"].transitions.k_per_nm,
        spin_degeneracy=base_settings.spin_degeneracy,
        convention="bare_d2k",
    )
    ratio = float(np.sum(bare_weights) / np.sum(production_weights))
    normalization_rows = [
        {"convention": "d2k_over_2pi_squared", "status": "PRODUCTION",
         "weight_sum_per_nm2": float(np.sum(production_weights)), "factor_vs_production": 1.0},
        {"convention": "bare_d2k", "status": "DIAGNOSTIC_ONLY",
         "weight_sum_per_nm2": float(np.sum(bare_weights)), "factor_vs_production": ratio},
    ]
    reporting.write_csv(output / "tables" / "normalization_audit.csv", normalization_rows)
    radial_error = k_integration.synthetic_radial_vs_cartesian_error(base_settings.k_max_per_nm, points=501)
    reporting.write_csv(output / "tables" / "radial_vs_cartesian_synthetic.csv", [{
        "test_function": "exp(-(k/kmax)^2) inside circular domain",
        "relative_error": radial_error,
        "note": "quadrature implementation diagnostic; physical isotropy is assessed separately",
    }])
    reporting.write_csv(output / "tables" / "nz_audit.csv", [{
        "main_semantics": cfg["chi2"]["nz_semantics"],
        "period_thickness_nm": float(cfg["geometry"]["total_period_nm"]),
        "production_Nz_per_m": float(cfg["chi2"]["n_periods_per_metre"]),
        "alternative_individual_wells_per_m": float(cfg["chi2"]["n_periods_per_metre"])
        * int(cfg["chi2"]["wells_per_period_diagnostic"]),
        "alternative_factor": int(cfg["chi2"]["wells_per_period_diagnostic"]),
        "status": "production unchanged; alternative diagnostic only",
    }])

    grid_counts = sorted({int(row["N_k"]) for row in grid_rows})
    grid_check_count = grid_counts[-2] if len(grid_counts) >= 2 else grid_counts[-1]
    grid_converged = all(
        bool(row["converged_vs_finest"]) for row in grid_rows if int(row["N_k"]) == grid_check_count
    )
    nominal_fraction = float(cfg["integration"]["fraction_of_bz"])
    kmax_converged = all(
        bool(row["converged_vs_finest"]) for row in kmax_rows
        if math.isclose(float(row["fraction_of_bz"]), nominal_fraction, abs_tol=1e-12)
    )
    radial_validated = bool(isotropy_rows) and all(
        bool(row["radial_assumption_pass"]) for row in isotropy_rows
    )
    boss_tolerance = float(cfg["validation"]["boss_hybrid_relative_spectrum_tolerance"])
    summary_by_mode = {str(row["mode"]): row for row in summary_rows}
    boss_validated = (
        "23C" in summary_by_mode and "23D" in summary_by_mode
        and float(summary_by_mode["23C"]["relative_spectrum_RMSE_vs_23D"]) <= boss_tolerance
        and grid_converged and kmax_converged and radial_validated
    )

    master_rows = []
    descriptions = {
        "23A": "shared parabola", "23B": "4 parabolas",
        "23C": "e parabola + nonparabolic hh", "23D": "raw kp8 all states",
    }
    for row in summary_rows:
        master_rows.append({"Mode": row["mode"], "Dispersion": descriptions[str(row["mode"])], **row})
    reporting.write_csv(output / "tables" / "demo23_master_mode_comparison.csv", master_rows)

    min_tracking_score = min(float(row["tracking_score"]) for row in tracked.rows)
    min_tracking_margin = min(float(row["assignment_margin"]) for row in tracked.rows)
    interpolation_max = max(float(row["max_node_residual_eV"]) for row in interpolation_rows)
    fit_by_state = {str(row["state"]): row for row in fit_rows}
    electron_fit_tol = float(cfg["validation"]["electron_fit_rmse_tolerance_meV"])
    validation_rows = [
        {"Check": "23A regression", "Result": error, "Threshold": f"<= {tolerance:g} pm/V", "PASS/FAIL": "PASS" if error <= tolerance else "FAIL"},
        {"Check": "state tracking", "Result": f"min score {min_tracking_score:.6g}; min margin {min_tracking_margin:.6g}", "Threshold": f"score >= {cfg['state_tracking']['minimum_overlap_score']}; margin >= {cfg['state_tracking']['minimum_assignment_margin']}; no ambiguous", "PASS/FAIL": "PASS"},
        {"Check": "e1 fit", "Result": f"RMSE {float(fit_by_state['e1']['RMSE_meV']):.6g} meV", "Threshold": f"<= {electron_fit_tol:g} meV", "PASS/FAIL": "PASS" if float(fit_by_state['e1']['RMSE_meV']) <= electron_fit_tol else "FAIL"},
        {"Check": "e2 fit", "Result": f"RMSE {float(fit_by_state['e2']['RMSE_meV']):.6g} meV", "Threshold": f"<= {electron_fit_tol:g} meV", "PASS/FAIL": "PASS" if float(fit_by_state['e2']['RMSE_meV']) <= electron_fit_tol else "FAIL"},
        {"Check": "23C-vs-23D spectral RMSE", "Result": float(summary_by_mode["23C"]["relative_spectrum_RMSE_vs_23D"]) if "23C" in summary_by_mode and "23D" in summary_by_mode else "not run", "Threshold": f"<= {boss_tolerance:g}", "PASS/FAIL": ("PASS" if float(summary_by_mode["23C"]["relative_spectrum_RMSE_vs_23D"]) <= boss_tolerance else "FAIL") if "23C" in summary_by_mode and "23D" in summary_by_mode else "NOT RUN"},
        {"Check": "k-grid convergence", "Result": f"N={grid_check_count} vs {max(grid_counts)}", "Threshold": f"max complex relative change <= {cfg['validation']['convergence_relative_tolerance']}", "PASS/FAIL": "PASS" if grid_converged else "FAIL"},
        {"Check": "kmax convergence", "Result": f"nominal fraction {nominal_fraction:g}", "Threshold": f"max complex relative change <= {cfg['validation']['convergence_relative_tolerance']}", "PASS/FAIL": "PASS" if kmax_converged else "FAIL"},
        {"Check": "isotropy", "Result": max((float(row["max_absolute_anisotropy_meV"]) for row in isotropy_rows), default=float("nan")), "Threshold": f"<= {cfg['validation']['isotropy_absolute_tolerance_meV']} meV", "PASS/FAIL": "PASS" if radial_validated else "FAIL"},
        {"Check": "interpolation bounds", "Result": interpolation_max, "Threshold": f"node residual <= {cfg['validation']['interpolation_node_tolerance_eV']} eV; no extrapolation", "PASS/FAIL": "PASS" if interpolation_max <= float(cfg["validation"]["interpolation_node_tolerance_eV"]) else "FAIL"},
        {"Check": "normalization consistency", "Result": ratio, "Threshold": f"bare/production = (2pi)^2 = {(2*math.pi)**2:.12g}", "PASS/FAIL": "PASS" if math.isclose(ratio, (2 * math.pi) ** 2, rel_tol=1e-12) else "FAIL"},
    ]
    reporting.write_csv(output / "tables" / "demo23_validation_table.csv", validation_rows)

    if bool(cfg["plots"]["enabled"]):
        dpi = int(cfg["plots"]["dpi"])
        plots = output / "plots"
        plotting.raw_dispersions(plots / "figure01_raw_kp8_dispersions.png", tracked.k_per_nm, aligned, dpi)
        plotting.fit_plot(plots / "figure02_electron_parabolic_fits.png", tracked.k_per_nm, aligned, fits,
                          ("e1", "e2"), "Electron parabolic fits", dpi)
        plotting.residual_plot(plots / "figure03_electron_fit_residuals.png", tracked.k_per_nm, aligned, fits,
                               ("e1", "e2"), "Electron parabolic-fit residuals", dpi)
        plotting.fit_plot(plots / "figure04_heavy_hole_parabolic_failure.png", tracked.k_per_nm, aligned, fits,
                          ("hh1", "hh2"), "Heavy-hole parabolic-fit diagnostic", dpi)
        plotting.residual_plot(plots / "figure05_heavy_hole_residuals.png", tracked.k_per_nm, aligned, fits,
                               ("hh1", "hh2"), "Heavy-hole parabolic-fit residuals", dpi)
        plotting.local_curvature(plots / "figure05b_heavy_hole_local_curvature.png", tracked.k_per_nm, aligned, dpi)
        k = results["23A"].transitions.k_per_nm
        target_nm = float(cfg["chi2"]["target_wavelength_nm"])
        for mode, result in results.items():
            plotting.transition_mode_detail(plots / f"figure06_{mode}_transition_energies.png", k, result,
                                            target_nm, physics23.validated.HC_EV_NM, dpi)
        plotting.transition_modes(plots / "figure07_transition_model_comparison.png", k, results,
                                  target_nm, physics23.validated.HC_EV_NM, dpi)
        plotting.spectra(plots / "figure08_chi2_comparison.png", results, summary_rows, target_nm, dpi)
        plotting.differences(plots / "figure09_difference_from_23D.png", results, summary_rows,
                             boss_tolerance, dpi)
        plotting.k_integrand(plots / "figure10_k_integrand_1550nm.png", k, results,
                             prefactor, target_nm, dpi)
        plotting.cumulative_k(plots / "figure11_cumulative_k_contribution_1550nm.png", k, results,
                              prefactor, target_nm, dpi)
        for mode, result in results.items():
            plotting.pathway_contributions(plots / f"figure12_{mode}_pathways_1550nm.png",
                                           result, target_nm, "1550 nm", dpi)
            peak_nm = float(result.spectrum.wavelength_nm[int(np.argmax(result.magnitude))])
            plotting.pathway_contributions(plots / f"figure12_{mode}_pathways_peak.png",
                                           result, peak_nm, "mode spectral peak", dpi)
        plotting.major_pathway_changes(plots / "figure13_major_pathway_changes_1550nm.png",
                                       results, target_nm, dpi)
        plotting.convergence(plots / "figure14_k_grid_convergence.png", grid_rows, "N_k",
                             "Figure 14 — k-grid convergence", float(cfg["validation"]["convergence_relative_tolerance"]),
                             float(grid_check_count), dpi)
        plotting.convergence(plots / "figure15_kmax_convergence.png", kmax_rows, "fraction_of_bz",
                             "Figure 15 — kmax convergence", float(cfg["validation"]["convergence_relative_tolerance"]),
                             nominal_fraction, dpi)
        plotting.isotropy(plots / "figure16_isotropy.png", anisotropy_k, anisotropy, isotropy_rows, dpi)
        paper_plots = output / "paper_comparison_plots"
        paper_block = cfg["paper_comparison"]
        plotting.paper_full_overlay(paper_plots / "paper_P1_full_spectrum_overlay.png", results, paper_curve,
                                    float(paper_block["simulated_peak_nm"]), float(paper_block["measured_peak_nm"]), dpi)
        plotting.paper_normalized(paper_plots / "paper_P2_normalized_spectral_shape.png", results, paper_curve, dpi)
        plotting.paper_peaks(paper_plots / "paper_P3_peak_location_comparison.png", summary_rows,
                             float(paper_block["simulated_peak_nm"]), float(paper_block["measured_peak_nm"]), dpi)
        plotting.paper_1550(paper_plots / "paper_P4_chi2_1550_comparison.png", summary_rows,
                            float(paper_block["ideal_abrupt_chi2_1550_pm_per_V"]), dpi)
        plotting.paper_errors(paper_plots / "paper_P5_error_to_digitized_spectrum.png", paper_rows, dpi)
    resolved = {
        "broadening_meV": base_settings.broadening_meV,
        "r_e_hh_nm": base_settings.r_e_hh_nm,
        "n_periods_per_metre": base_settings.n_wells_per_metre,
        "nz_semantics": cfg["chi2"]["nz_semantics"],
        "spin_degeneracy": base_settings.spin_degeneracy,
        "kspace_convention": base_settings.kspace_convention,
        "lattice_constant_nm": base_settings.lattice_constant_nm,
        "k_BZ_per_nm": k_bz_per_nm(cfg),
        "kmax_per_nm": kmax_per_nm(cfg),
        "bz_definition": cfg["integration"]["bz_definition"],
        "wavelength_min_nm": float(wavelengths[0]),
        "wavelength_max_nm": float(wavelengths[-1]),
        "wavelength_points": int(len(wavelengths)),
        "state_count_per_band": 2,
        "kp_model": "nextnano++ Professional 8-band k.p",
        "matrix_approximation": "M(k)=M(0)",
        "interpolation": cfg["dispersion"]["interpolation"],
        "frozen_input_source": str(frozen.source),
        "grid_convergence_check_N_k": grid_check_count,
        "k_grid_converged": grid_converged,
        "kmax_converged": kmax_converged,
        "radial_assumption_validated": radial_validated,
        "boss_hybrid_relative_spectrum_tolerance": boss_tolerance,
        "boss_hybrid_validated": boss_validated,
        "paper_curve_label": paper_curve.label,
        "paper_curve_source_type": paper_curve.source_type,
        "paper_curve_points": int(len(paper_curve.wavelength_nm)),
    }
    unresolved = [
        "The residual 1/hbar on the boss derivation slide remains dimensionally unresolved and was not implemented.",
        "Nz remains one coupled-well period per 30 nm; counting two individual wells is only a factor-two diagnostic.",
        "Full finite-k complex matrix elements and their gauge consistency remain future work, not Demo 23 physics.",
        "A direct physical 2D kp-grid susceptibility is needed if the two-direction isotropy gate fails.",
    ]
    reporting.write_json(output / "resolved_configuration.json", resolved)
    reporting.write_final_report(
        output / "DEMO23_FINAL_REPORT.md", baseline_error=error, tolerance=tolerance,
        summary_rows=summary_rows, fit_rows=fit_rows, isotropy_rows=isotropy_rows,
        grid_rows=grid_rows, kmax_rows=kmax_rows, resolved=resolved, unresolved=unresolved,
        validation_rows=validation_rows, pathway_rows=pathway_rows,
        integrand_rows=integrand_rows, paper_rows=paper_rows,
        paper_reference_rows=paper_comparison.reference_rows(cfg, paper_curve),
    )
    summary = {
        "status": "COMPLETE",
        "baseline_error_pm_per_V": error,
        "modes": summary_rows,
        "fits": fit_rows,
        "isotropy": isotropy_rows,
        "resolved_configuration": resolved,
        "output": str(output),
    }
    reporting.write_json(output / "analysis_summary.json", summary)
    return summary
