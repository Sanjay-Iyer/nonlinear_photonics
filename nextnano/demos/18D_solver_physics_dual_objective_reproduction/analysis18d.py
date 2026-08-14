"""Unweighted dual-objective physics analysis for Demo 18D."""

from __future__ import annotations

import cmath
import math
from typing import Any, Mapping, Sequence

import numpy as np

import audit18b
import cases18d


HC_EV_NM = 1239.841984


def settings(cfg: Mapping[str, Any]):
    fixed, spectrum = cfg["fixed_physics"], cfg["spectrum"]
    if float(fixed["hh_relative_weight"]) != 1.0:
        raise ValueError("Demo 18D forbids artificial HH weighting")
    return audit18b.production_chi2.Chi2Settings(
        mode="absolute", broadening_meV=float(fixed["broadening_meV"]),
        k_parallel_fraction_of_bz=2.0 * float(spectrum["kmax_fraction_2pi_over_a"]),
        k_parallel_points=int(spectrum["k_points"]),
        lattice_constant_nm=float(spectrum["lattice_constant_nm"]),
        electron_mass_m0=float(spectrum["electron_inplane_mass_m0"]),
        heavy_hole_inplane_mass_m0=float(spectrum["heavy_hole_inplane_mass_m0"]),
        spin_degeneracy=2, max_states_per_band=2,
        r_e_hh_nm=0.751, n_wells_per_metre=2.0 / (30.0e-9),
    )


def complete_spectrum(
    cfg: Mapping[str, Any], electron: Any, heavy_hole: Any,
) -> dict[str, np.ndarray]:
    spectrum = cfg["spectrum"]
    wavelengths = np.linspace(float(spectrum["wavelength_start_nm"]),
                              float(spectrum["wavelength_stop_nm"]),
                              int(spectrum["wavelength_points"]))
    electron_values = np.empty(wavelengths.size, complex)
    hh_values = np.empty(wavelengths.size, complex)
    eq_settings = settings(cfg)
    for index, wavelength in enumerate(wavelengths):
        _, _, branches = audit18b.independent_eq2(
            electron, heavy_hole, HC_EV_NM / float(wavelength), eq_settings
        )
        electron_values[index] = branches["electron"]
        hh_values[index] = branches["heavy_hole"]
    return {
        "wavelength_nm": wavelengths, "chi_e": electron_values,
        "chi_hh": hh_values, "chi_total": electron_values + hh_values,
    }


def _complex(prefix: str, value: complex) -> dict[str, float]:
    return {f"{prefix}_real": float(value.real), f"{prefix}_imag": float(value.imag),
            f"{prefix}_abs": float(abs(value))}


def _local_peaks(wavelengths: np.ndarray, magnitude: np.ndarray) -> list[tuple[float, float]]:
    candidates = [index for index in range(1, magnitude.size - 1)
                  if magnitude[index] > magnitude[index - 1]
                  and magnitude[index] >= magnitude[index + 1]]
    if not candidates:
        candidates = [int(np.argmax(magnitude))]
    peaks = [(float(wavelengths[index]), float(magnitude[index])) for index in candidates]
    peaks.sort(key=lambda pair: pair[1], reverse=True)
    return peaks


def _localization_fields(solved: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    prefix = {"electron": "e", "heavy_hole": "hh"}
    selected = {
        "electron": set(int(v) for v in solved["row"]["selected_electron_states"]),
        "heavy_hole": set(int(v) for v in solved["row"]["selected_heavy_hole_states"]),
    }
    order = {band: {state: rank + 1 for rank, state in enumerate(sorted(states))}
             for band, states in selected.items()}
    for row in solved["localization"]:
        band, state = str(row["band"]), int(row["state"])
        if state not in selected.get(band, set()):
            continue
        label = f"{prefix[band]}{order[band][state]}"
        result.update({
            f"{label}_centroid_nm": float(row["centroid_nm"]),
            f"{label}_left_well_probability": float(row["left_well_probability"]),
            f"{label}_right_well_probability": float(row["right_well_probability"]),
            f"{label}_barrier_probability": float(row["central_barrier_probability"]),
        })
    return result


def analyze_case(
    cfg: Mapping[str, Any], case: cases18d.PhysicsCase,
    solved: Mapping[str, Any], *, solver_pass: bool,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    if case.hh_relative_weight != 1.0:
        raise ValueError(f"{case.case_id}: hh_relative_weight must be 1.0")
    spectrum = complete_spectrum(cfg, solved["electron"], solved["heavy_hole"])
    wavelengths = spectrum["wavelength_nm"]
    magnitude = np.abs(spectrum["chi_total"])
    target_nm = float(cfg["spectrum"]["target_wavelength_nm"])
    target_index = int(np.argmin(np.abs(wavelengths - target_nm)))
    electron = complex(spectrum["chi_e"][target_index])
    hh = complex(spectrum["chi_hh"][target_index])
    total = electron + hh
    chi_abs = abs(total)
    target_chi = float(cfg["spectrum"]["target_chi2_pm_per_V"])
    amplitude_error = abs(chi_abs - target_chi) / target_chi
    peaks = _local_peaks(wavelengths, magnitude)
    first = peaks[0]
    second = peaks[1] if len(peaks) > 1 else (float("nan"), float("nan"))
    low, high = (float(v) for v in cfg["spectrum"]["desired_peak_window_nm"])
    peak_nm = first[0]
    spectral_pass = low <= peak_nm <= high
    spectral_distance = 0.0 if spectral_pass else min(abs(peak_nm - low), abs(peak_nm - high))
    spectral_penalty = spectral_distance / float(cfg["spectrum"]["spectral_penalty_scale_nm"])
    combined_score = math.hypot(amplitude_error, spectral_penalty)
    desired_mask = (wavelengths >= low) & (wavelengths <= high)
    comp_low, comp_high = (float(v) for v in cfg["spectrum"]["competing_peak_window_nm"])
    competing_mask = (wavelengths >= comp_low) & (wavelengths <= comp_high)
    desired_max = float(np.max(magnitude[desired_mask]))
    competing_max = float(np.max(magnitude[competing_mask]))
    desired_ratio = desired_max / max(competing_max, 1.0e-30)
    within20, within10 = amplitude_error <= 0.20, amplitude_error <= 0.10
    if spectral_pass and within10:
        classification = "STRONG_AMPLITUDE_AND_SPECTRUM_MATCH"
    elif spectral_pass and within20:
        classification = "AMPLITUDE_AND_SPECTRUM_MATCH"
    elif spectral_pass:
        classification = "SPECTRAL_MATCH_ONLY"
    elif within20:
        classification = "AMPLITUDE_MATCH_BUT_SPECTRAL_MISMATCH"
    else:
        classification = "NEITHER_MATCH"
    base = solved["row"]
    orth_limit = float(cfg["bound_state_criteria"]["maximum_orthonormality_error"])
    bound_pass = bool(base["strict_selected_states_bound_pass"])
    orth_pass = (float(base["electron_orthonormality_error"]) <= orth_limit
                 and float(base["heavy_hole_orthonormality_error"]) <= orth_limit)
    physical_valid = bool(solver_pass and bound_pass and orth_pass)
    r_required = 0.751 * math.sqrt(target_chi / chi_abs) if chi_abs > 0 else float("inf")
    overlap, z_e, z_h = audit18b.matrices(solved["electron"], solved["heavy_hole"])
    row = {
        **case.as_record(),
        "period_barrier_nm": 30.0 - case.well1_nm - case.well2_nm - case.tunneling_barrier_nm,
        "r_e_hh_primary_nm": 0.751,
        "chi2_1550_pm_per_V": float(chi_abs),
        "chi2_at_r_0p65_pm_per_V": float(chi_abs * (0.65 / 0.751) ** 2),
        "chi2_at_r_0p751_pm_per_V": float(chi_abs),
        "chi2_at_r_1p00_pm_per_V": float(chi_abs * (1.0 / 0.751) ** 2),
        "r_required_nm": float(r_required),
        "r_required_inside_allowed_range": bool(0.65 <= r_required <= 1.0),
        "paper_target_pm_per_V": target_chi,
        "amplitude_relative_error": float(amplitude_error),
        "amplitude_percent_error": float(100.0 * amplitude_error),
        "peak_wavelength_nm": peak_nm, "peak_chi2_pm_per_V": first[1],
        "strongest_peak_wavelength_nm": peak_nm, "strongest_peak_chi2_pm_per_V": first[1],
        "second_peak_wavelength_nm": second[0], "second_peak_chi2_pm_per_V": second[1],
        "spectral_window_pass": bool(spectral_pass),
        "spectral_distance_nm": float(spectral_distance),
        "spectral_penalty": float(spectral_penalty),
        "combined_score": float(combined_score),
        "desired_window_max_chi2_pm_per_V": desired_max,
        "competing_1665_window_max_chi2_pm_per_V": competing_max,
        "desired_peak_ratio": float(desired_ratio),
        "classification": classification,
        **_complex("chi_e", electron), **_complex("chi_hh", hh), **_complex("chi_total", total),
        "phase_difference_e_hh_rad": float(abs(cmath.phase(electron / hh))) if abs(hh) else float("nan"),
        "phase_difference_e_hh_deg": float(math.degrees(abs(cmath.phase(electron / hh))))
        if abs(hh) else float("nan"),
        "cancellation_factor": float((abs(electron) + abs(hh)) / max(abs(total), 1e-30)),
        "E1_eV": float(solved["electron"].energies_eV[0]),
        "E2_eV": float(solved["electron"].energies_eV[1]),
        "HH1_eV": float(solved["heavy_hole"].energies_eV[0]),
        "HH2_eV": float(solved["heavy_hole"].energies_eV[1]),
        "z_e11_nm": float(z_e[0, 0]), "z_e12_nm": float(z_e[0, 1]),
        "z_e21_nm": float(z_e[1, 0]), "z_e22_nm": float(z_e[1, 1]),
        "z_hh11_nm": float(z_h[0, 0]), "z_hh12_nm": float(z_h[0, 1]),
        "z_hh21_nm": float(z_h[1, 0]), "z_hh22_nm": float(z_h[1, 1]),
        "delta_z_e_nm": float(z_e[1, 1] - z_e[0, 0]),
        "delta_z_hh_nm": float(z_h[1, 1] - z_h[0, 0]),
        "O11": float(overlap[0, 0]), "O12": float(overlap[0, 1]),
        "O21": float(overlap[1, 0]), "O22": float(overlap[1, 1]),
        "transition_e1_hh1_eV": float(base["transition_e1_hh1_eV"]),
        "transition_e1_hh2_eV": float(base["transition_e1_hh2_eV"]),
        "transition_e2_hh1_eV": float(base["transition_e2_hh1_eV"]),
        "transition_e2_hh2_eV": float(base["transition_e2_hh2_eV"]),
        **_localization_fields(solved),
        "solver_pass": bool(solver_pass), "bound_state_pass": bool(bound_pass),
        "orthonormality_pass": bool(orth_pass), "physical_valid": bool(physical_valid),
        "electron_orthonormality_error": float(base["electron_orthonormality_error"]),
        "hh_orthonormality_error": float(base["heavy_hole_orthonormality_error"]),
    }
    return row, spectrum


def rank(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    valid = [dict(row) for row in rows if bool(row.get("physical_valid"))]
    valid.sort(key=lambda row: float(row["combined_score"]))
    for index, row in enumerate(valid, 1):
        row["dual_objective_rank"] = index
    return valid


def spectral_window_rank(ranked: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in ranked if bool(row["spectral_window_pass"])]
    rows.sort(key=lambda row: float(row["combined_score"]))
    for index, row in enumerate(rows, 1):
        row["spectral_window_rank"] = index
    return rows


def outcome(ranked: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    spectral = [row for row in ranked if bool(row["spectral_window_pass"])]
    if any(float(row["amplitude_relative_error"]) <= 0.10 for row in spectral):
        return {"outcome": "E", "label": "very strong reproduction"}
    if any(float(row["amplitude_relative_error"]) <= 0.20 for row in spectral):
        return {"outcome": "D", "label": "strong reproduction"}
    if any(1170.0 <= float(row["chi2_1550_pm_per_V"]) <= 3510.0 for row in spectral):
        return {"outcome": "C", "label": "plausible reproduction"}
    if any(float(row["chi2_1550_pm_per_V"]) > 500.0 for row in spectral):
        return {"outcome": "B", "label": "meaningful solver-physics increase"}
    return {"outcome": "A", "label": "solver physics still far too small"}
