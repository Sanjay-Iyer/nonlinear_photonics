"""Complete Eq. 2 post-processing and exploratory analysis for Demo 18C."""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Any, Mapping, Sequence

import numpy as np

import audit18b
import cases18c


HC_EV_NM = 1239.841984
CONTINUOUS_PARAMETERS = (
    "r_e_hh_nm", "electrostatic_field_kV_per_cm", "hh_relative_weight",
    "kmax_fraction_2pi_over_a", "well1_nm", "well2_nm",
    "tunneling_barrier_nm", "electron_mass_scale", "hh_mass_scale",
    "cb_offset_scale", "hh_offset_scale",
)


def chi2_settings(cfg: Mapping[str, Any], combo: cases18c.Combination):
    chi = cfg["chi2"]
    baseline_e = float(chi["electron_inplane_mass_m0"])
    baseline_hh = float(chi["heavy_hole_inplane_mass_m0"])
    return audit18b.production_chi2.Chi2Settings(
        mode="absolute",
        broadening_meV=float(chi["broadening_meV"]),
        # Shared production uses pi/a as its edge; f*(2pi/a) is 2f in this field.
        k_parallel_fraction_of_bz=2.0 * combo.kmax_fraction_2pi_over_a,
        k_parallel_points=int(chi["k_points"]),
        lattice_constant_nm=float(chi["lattice_constant_nm"]),
        electron_mass_m0=baseline_e * combo.electron_mass_scale,
        heavy_hole_inplane_mass_m0=baseline_hh * combo.hh_mass_scale,
        spin_degeneracy=combo.spin_degeneracy,
        max_states_per_band=2,
        r_e_hh_nm=combo.r_e_hh_nm,
        n_wells_per_metre=combo.wells_per_period_for_Nz / (30.0e-9),
    )


def branch_spectrum(
    cfg: Mapping[str, Any], combo: cases18c.Combination,
    electron: Any, heavy_hole: Any,
) -> dict[str, np.ndarray]:
    wavelengths = np.linspace(
        float(cfg["chi2"]["wavelength_start_nm"]),
        float(cfg["chi2"]["wavelength_stop_nm"]),
        int(cfg["chi2"]["wavelength_points"]),
    )
    settings = chi2_settings(cfg, combo)
    electron_values = np.empty(wavelengths.size, dtype=complex)
    hh_raw_values = np.empty(wavelengths.size, dtype=complex)
    for index, wavelength in enumerate(wavelengths):
        _, _, branches = audit18b.independent_eq2(
            electron, heavy_hole, HC_EV_NM / float(wavelength), settings
        )
        electron_values[index] = branches["electron"]
        hh_raw_values[index] = branches["heavy_hole"]
    hh_weighted = combo.hh_relative_weight * hh_raw_values
    return {
        "wavelength_nm": wavelengths,
        "chi_e": electron_values,
        "chi_hh_raw": hh_raw_values,
        "chi_hh_weighted": hh_weighted,
        "chi_total": electron_values + hh_weighted,
        "chi_total_raw_unweighted": electron_values + hh_raw_values,
    }


def _complex_fields(prefix: str, value: complex) -> dict[str, float]:
    return {
        f"{prefix}_real": float(value.real),
        f"{prefix}_imag": float(value.imag),
        f"{prefix}_abs": float(abs(value)),
    }


def analyze_combo(
    cfg: Mapping[str, Any], combo: cases18c.Combination,
    solved: Mapping[str, Any], *, solver_pass: bool,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Run complete, branch-resolved Eq. 2 for one predefined combination."""

    base_row = dict(solved["row"])
    spectra = branch_spectrum(cfg, combo, solved["electron"], solved["heavy_hole"])
    wavelengths = spectra["wavelength_nm"]
    target_nm = float(cfg["chi2"]["target_wavelength_nm"])
    target_index = int(np.argmin(np.abs(wavelengths - target_nm)))
    if abs(float(wavelengths[target_index]) - target_nm) > 1.0e-9:
        raise ValueError("the wavelength grid must contain 1550 nm exactly")
    electron = complex(spectra["chi_e"][target_index])
    hh_raw = complex(spectra["chi_hh_raw"][target_index])
    hh_weighted = complex(spectra["chi_hh_weighted"][target_index])
    total = complex(spectra["chi_total"][target_index])
    total_raw = electron + hh_raw
    magnitude = abs(total)
    target = float(cfg["chi2"]["paper_target_pm_per_V"])
    baseline = float(cfg["chi2"]["demo18b_baseline_pm_per_V"])
    peak_index = int(np.argmax(np.abs(spectra["chi_total"])))
    peak_nm = float(wavelengths[peak_index])
    spectral_cfg = cfg["spectral_gate"]
    shifted = abs(peak_nm - float(spectral_cfg["baseline_peak_wavelength_nm"])) > float(
        spectral_cfg["maximum_peak_shift_from_baseline_nm"]
    )
    at_edge = peak_index in (0, wavelengths.size - 1)
    spectral_mismatch = shifted or (bool(spectral_cfg["edge_peak_is_mismatch"]) and at_edge)
    amplitude_match = target / 2.0 <= magnitude <= target * 1.5
    if spectral_mismatch and amplitude_match:
        spectral_flag = "AMPLITUDE_MATCH_BUT_SPECTRAL_MISMATCH"
    elif spectral_mismatch:
        spectral_flag = "SPECTRAL_MISMATCH"
    else:
        spectral_flag = "SPECTRAL_MATCH"

    orth_limit = float(cfg["bound_state_criteria"]["maximum_orthonormality_error"])
    bound_pass = bool(base_row["strict_selected_states_bound_pass"])
    orth_pass = (
        float(base_row["electron_orthonormality_error"]) <= orth_limit
        and float(base_row["heavy_hole_orthonormality_error"]) <= orth_limit
    )
    valid = bool(solver_pass and bound_pass and orth_pass)
    row = {
        **combo.as_record(),
        "period_barrier_nm": 30.0 - combo.well1_nm - combo.well2_nm
        - combo.tunneling_barrier_nm,
        "broadening_meV": float(cfg["chi2"]["broadening_meV"]),
        "states_per_band": 2,
        "target_wavelength_nm": target_nm,
        "chi2_1550_pm_per_V": float(magnitude),
        "paper_target_pm_per_V": target,
        "absolute_error_pm_per_V": float(abs(magnitude - target)),
        "percent_error": float(100.0 * abs(magnitude - target) / target),
        "ratio_to_paper": float(magnitude / target),
        "ratio_to_demo18b": float(magnitude / baseline),
        **_complex_fields("chi_e", electron),
        **_complex_fields("chi_e_raw", electron),
        **_complex_fields("chi_hh_raw", hh_raw),
        "hh_relative_weight": combo.hh_relative_weight,
        **_complex_fields("chi_hh_weighted", hh_weighted),
        **_complex_fields("chi_total", total),
        **_complex_fields("chi_total_after_weight", total),
        **_complex_fields("chi_total_raw_unweighted", total_raw),
        "cancellation_factor": float(
            (abs(electron) + abs(hh_weighted)) / max(abs(total), 1.0e-30)
        ),
        "raw_cancellation_factor": float(
            (abs(electron) + abs(hh_raw)) / max(abs(total_raw), 1.0e-30)
        ),
        "delta_z_e_nm": float(base_row["delta_z_e_nm"]),
        "delta_z_hh_nm": float(base_row["delta_z_hh_nm"]),
        "O11": float(base_row["overlap_e1_hh1"]),
        "O12": float(base_row["overlap_e1_hh2"]),
        "O21": float(base_row["overlap_e2_hh1"]),
        "O22": float(base_row["overlap_e2_hh2"]),
        "z_e11_nm": float(base_row["z_e11_nm"]),
        "z_e12_nm": float(base_row["z_e12_nm"]),
        "z_e21_nm": float(base_row["z_e21_nm"]),
        "z_e22_nm": float(base_row["z_e22_nm"]),
        "z_hh11_nm": float(base_row["z_hh11_nm"]),
        "z_hh12_nm": float(base_row["z_hh12_nm"]),
        "z_hh21_nm": float(base_row["z_hh21_nm"]),
        "z_hh22_nm": float(base_row["z_hh22_nm"]),
        "transition_e1_hh1_eV": float(base_row["transition_e1_hh1_eV"]),
        "transition_e1_hh2_eV": float(base_row["transition_e1_hh2_eV"]),
        "transition_e2_hh1_eV": float(base_row["transition_e2_hh1_eV"]),
        "transition_e2_hh2_eV": float(base_row["transition_e2_hh2_eV"]),
        "peak_chi2_pm_per_V": float(abs(spectra["chi_total"][peak_index])),
        "peak_wavelength_nm": peak_nm,
        "electron_orthonormality_error": float(base_row["electron_orthonormality_error"]),
        "hh_orthonormality_error": float(base_row["heavy_hole_orthonormality_error"]),
        "orthonormality_pass": bool(orth_pass),
        "bound_state_pass": bool(bound_pass),
        "solver_pass": bool(solver_pass),
        "physical_valid": bool(valid),
        "spectral_match_flag": spectral_flag,
        "selected_electron_states": base_row["selected_electron_states"],
        "selected_heavy_hole_states": base_row["selected_heavy_hole_states"],
    }
    return row, spectra


def failed_combo_row(
    cfg: Mapping[str, Any], combo: cases18c.Combination, reason: str,
) -> dict[str, Any]:
    nan = float("nan")
    row = {
        **combo.as_record(), "paper_target_pm_per_V": float(cfg["chi2"]["paper_target_pm_per_V"]),
        "solver_pass": False, "bound_state_pass": False,
        "orthonormality_pass": False, "physical_valid": False,
        "spectral_match_flag": "NOT_EVALUATED", "failure_reason": reason,
    }
    for name in (
        "chi2_1550_pm_per_V", "absolute_error_pm_per_V", "percent_error",
        "ratio_to_paper", "ratio_to_demo18b", "chi_e_abs", "chi_hh_raw_abs",
        "chi_hh_weighted_abs", "cancellation_factor", "delta_z_e_nm",
        "delta_z_hh_nm", "O11", "O12", "O21", "O22",
        "transition_e1_hh1_eV", "transition_e1_hh2_eV",
        "transition_e2_hh1_eV", "transition_e2_hh2_eV",
        "peak_chi2_pm_per_V", "peak_wavelength_nm",
    ):
        row[name] = nan
    return row


def rank_valid(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    valid = [dict(row) for row in rows if bool(row.get("physical_valid"))]
    valid.sort(key=lambda row: float(row["percent_error"]))
    for rank, row in enumerate(valid, 1):
        row["closeness_rank"] = rank
    return valid


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=float)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def _correlation(x: np.ndarray, y: np.ndarray, *, ranks: bool = False) -> float:
    if x.size < 3 or np.ptp(x) == 0.0 or np.ptp(y) == 0.0:
        return float("nan")
    if ranks:
        x, y = _average_ranks(x), _average_ranks(y)
    return float(np.corrcoef(x, y)[0, 1])


def parameter_importance(ranked: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = list(ranked)
    if not rows:
        return []
    best5, worst5 = rows[:5], rows[-5:]
    log_chi = np.log(np.asarray([max(float(row["chi2_1550_pm_per_V"]), 1e-30) for row in rows]))
    errors = np.asarray([float(row["percent_error"]) for row in rows])
    result: list[dict[str, Any]] = []
    for parameter in CONTINUOUS_PARAMETERS:
        x = np.asarray([float(row[parameter]) for row in rows])
        pearson = _correlation(x, log_chi)
        spearman = _correlation(x, log_chi, ranks=True)
        pearson_error = _correlation(x, errors)
        spearman_error = _correlation(x, errors, ranks=True)
        score = max(abs(value) for value in (pearson, spearman) if math.isfinite(value)) \
            if any(math.isfinite(value) for value in (pearson, spearman)) else float("nan")
        if not math.isfinite(score):
            qualitative = "fixed_not_estimable"
        elif score >= 0.7:
            qualitative = "strong_exploratory_association"
        elif score >= 0.4:
            qualitative = "moderate_exploratory_association"
        elif score >= 0.2:
            qualitative = "weak_exploratory_association"
        else:
            qualitative = "little_exploratory_association"
        result.append({
            "parameter": parameter, "pearson_r": pearson,
            "spearman_rho": spearman, "pearson_error_r": pearson_error,
            "spearman_error_rho": spearman_error,
            "best5_mean": float(np.mean([float(row[parameter]) for row in best5])),
            "all_mean": float(np.mean(x)),
            "worst5_mean": float(np.mean([float(row[parameter]) for row in worst5])),
            "qualitative_importance": qualitative,
        })
    return result


def classify_outcome(ranked: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    if not ranked:
        return {"outcome": "A", "label": "no physically valid combinations"}
    best = float(ranked[0]["chi2_1550_pm_per_V"])
    if 2106.0 <= best <= 2574.0:
        return {"outcome": "D", "label": "very strong numerical match"}
    if 1872.0 <= best <= 2808.0:
        return {"outcome": "C", "label": "strong approximate reproduction"}
    if 1170.0 <= best <= 3510.0:
        return {"outcome": "B", "label": "paper scale becomes plausible"}
    return {"outcome": "A", "label": "paper scale cannot be reached"}


def detailed_comparison(
    baseline: Mapping[str, Any], case: Mapping[str, Any]
) -> list[dict[str, Any]]:
    categories = {
        "r_e_hh_nm": "UNCERTAIN", "electrostatic_field_kV_per_cm": "DIAGNOSTIC PROXY",
        "hh_relative_weight": "DIAGNOSTIC PROXY", "wells_per_period_for_Nz": "CONVENTION",
        "spin_degeneracy": "CONVENTION", "kmax_fraction_2pi_over_a": "CONVENTION",
        "well1_nm": "UNCERTAIN", "well2_nm": "UNCERTAIN",
        "tunneling_barrier_nm": "UNCERTAIN", "electron_mass_scale": "UNCERTAIN",
        "hh_mass_scale": "UNCERTAIN", "cb_offset_scale": "UNCERTAIN",
        "hh_offset_scale": "UNCERTAIN", "chi_e_abs": "CALCULATED EFFECT",
        "chi_hh_raw_abs": "CALCULATED EFFECT", "chi_hh_weighted_abs": "CALCULATED EFFECT",
        "chi_total_abs": "CALCULATED EFFECT", "cancellation_factor": "CALCULATED EFFECT",
    }
    rows = []
    for parameter, category in categories.items():
        old, new = float(baseline[parameter]), float(case[parameter])
        percent = 0.0 if old == new else (float("nan") if old == 0 else 100.0 * (new - old) / abs(old))
        rows.append({
            "parameter": parameter, "demo18b_value": old, "demo18c_value": new,
            "percent_change": percent, "effect_classification": category,
        })
    return rows
