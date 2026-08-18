"""Stage 07 - run the susceptibility over all 13 cases and assemble result rows.

This is the driver that sits between the physics (:mod:`s06_chi2`) and the
output stages. It owns no equations. Its jobs are:

* evaluate every case under BOTH k-space conventions, always;
* keep raw and scaled values side by side, never overwriting either;
* normalize each case against the abrupt reference;
* compare against the published target without ever fitting to it.

The reported value is selected, not computed differently: ``chi2_reported_*`` is
literally one of ``chi2_raw_*`` or ``chi2_scaled_*`` depending on the config
switch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

import config20
import s01_cases as cases
import s02_grading as grading
import s05_extract as extract
import s06_chi2 as chi2mod

#: The master table's columns. Every Demo 19 field is retained; Demo 20's new
#: fields are appended rather than replacing anything.
DEMO19_FIELDS = [
    "case_id", "case_name", "profile",
    "I1_width_nm", "I2_width_nm", "I3_width_nm", "I4_width_nm",
    "nominal_grade_width_nm",
    "E1_HH1_eV", "E1_HH2_eV", "E2_HH1_eV", "E2_HH2_eV",
    "z_e12_nm", "z_hh12_nm", "delta_z_e_nm", "delta_z_hh_nm",
    "O11", "O12", "O21", "O22",
    "chi2_1550_pm_per_V", "chi2_1550_relative_to_abrupt",
    "peak_chi2_pm_per_V", "peak_chi2_relative_to_abrupt", "peak_wavelength_nm",
    "grading_validation_pass", "solver_pass", "physical_valid",
    "E1_eV", "E2_eV", "HH1_eV", "HH2_eV",
    "z_e11_nm", "z_e21_nm", "z_e22_nm",
    "z_hh11_nm", "z_hh21_nm", "z_hh22_nm",
    "electron_E1_centroid_nm", "electron_E2_centroid_nm",
    "HH1_centroid_nm", "HH2_centroid_nm",
    "solver_return_code", "failure_stage", "failure_reason", "spectrum_path",
]

DEMO20_FIELDS = [
    "kspace_scaling_enabled", "kspace_scaling_factor",
    "kspace_convention_raw", "kspace_convention_scaled",
    "chi2_raw_1550_pm_per_V", "chi2_scaled_1550_pm_per_V",
    "chi2_reported_1550_pm_per_V",
    "raw_peak_chi2_pm_per_V", "scaled_peak_chi2_pm_per_V",
    "reported_peak_chi2_pm_per_V",
    "raw_peak_wavelength_nm", "scaled_peak_wavelength_nm",
    "peak_wavelength_shift_nm", "spectral_shape_max_difference",
    "chi2_raw_1550_relative_to_reference", "chi2_scaled_1550_relative_to_reference",
    "raw_peak_relative_to_reference", "scaled_peak_relative_to_reference",
    "paper_target_pm_per_V", "raw_ratio_to_paper", "scaled_ratio_to_paper",
    "raw_error_percent", "scaled_error_percent",
    "demo19_recorded_chi2_1550_pm_per_V",
    "chi2_reproduces_demo19", "chi2_demo19_relative_difference",
    "states_provenance", "analysis_source",
]

MASTER_FIELDS = DEMO19_FIELDS + DEMO20_FIELDS

PRESENTATION_FIELDS = [
    "Case", "Profile", "I1", "I2", "I3", "I4",
    "chi2_1550_raw", "chi2_1550_scaled", "chi2_1550_reported",
    "Relative_to_abrupt", "Peak_nm", "Ratio_to_paper",
]


@dataclass
class CaseAnalysis:
    """One case's row, its two spectra, and its status."""

    case: cases.GradingCase
    row: dict[str, Any]
    pair: chi2mod.ConventionPair | None

    @property
    def case_id(self) -> str:
        return self.case.case_id

    @property
    def has_spectrum(self) -> bool:
        return self.pair is not None


def _blank_row() -> dict[str, Any]:
    return {field: "" for field in MASTER_FIELDS}


def _base_row(cfg: Mapping[str, Any], case: cases.GradingCase) -> dict[str, Any]:
    row = _blank_row()
    validation = grading.validate_realized(cfg, case)
    row.update({
        "case_id": case.case_id,
        "case_name": case.case_name,
        "profile": case.profile,
        "nominal_grade_width_nm": case.nominal_grade_width_nm,
        "grading_validation_pass": validation["validation_pass"],
        "solver_pass": False,
        "physical_valid": False,
        "kspace_scaling_enabled": config20.scaling_enabled(cfg),
        "kspace_scaling_factor": chi2mod.two_pi_squared(),
        "kspace_convention_raw": chi2mod.CONVENTION_DEMO19,
        "kspace_convention_scaled": chi2mod.CONVENTION_SCALED,
        "paper_target_pm_per_V": float(cfg["paper"]["target_chi2_pm_per_V"]),
        "analysis_source": str(cfg["analysis"]["source"]),
    })
    for interface_id in cases.INTERFACE_IDS:
        row[f"{interface_id}_width_nm"] = case.width(interface_id)
    return row


def _fill_state_columns(row: dict[str, Any], states: chi2mod.CaseStates) -> None:
    """The solver-derived quantum numbers, in Demo 19's own column names."""

    e = np.asarray(states.electron_energies_eV, dtype=float)
    h = np.asarray(states.hole_energies_eV, dtype=float)
    overlap = np.asarray(states.overlap_electron_hole, dtype=float)
    z_e = np.asarray(states.position_matrix_electron_nm, dtype=float)
    z_h = np.asarray(states.position_matrix_hole_nm, dtype=float)
    row.update({
        "E1_eV": e[0], "E2_eV": e[1], "HH1_eV": h[0], "HH2_eV": h[1],
        "E1_HH1_eV": e[0] - h[0], "E1_HH2_eV": e[0] - h[1],
        "E2_HH1_eV": e[1] - h[0], "E2_HH2_eV": e[1] - h[1],
        "O11": overlap[0, 0], "O12": overlap[0, 1],
        "O21": overlap[1, 0], "O22": overlap[1, 1],
        "z_e11_nm": z_e[0, 0], "z_e12_nm": z_e[0, 1],
        "z_e21_nm": z_e[1, 0], "z_e22_nm": z_e[1, 1],
        "z_hh11_nm": z_h[0, 0], "z_hh12_nm": z_h[0, 1],
        "z_hh21_nm": z_h[1, 0], "z_hh22_nm": z_h[1, 1],
        "delta_z_e_nm": z_e[1, 1] - z_e[0, 0],
        "delta_z_hh_nm": z_h[1, 1] - z_h[0, 0],
        "states_provenance": states.provenance,
    })


def _fill_chi2_columns(
    row: dict[str, Any], pair: chi2mod.ConventionPair, cfg: Mapping[str, Any]
) -> None:
    target = float(cfg["chi2"]["target_wavelength_nm"])
    raw_at_target = pair.raw.at_wavelength(target)
    scaled_at_target = pair.scaled.at_wavelength(target)
    raw_peak = pair.raw.peak()
    scaled_peak = pair.scaled.peak()
    reported = pair.reported
    reported_at_target = reported.at_wavelength(target)
    reported_peak = reported.peak()
    paper = float(cfg["paper"]["target_chi2_pm_per_V"])
    row.update({
        # Demo 19's own column names carry the REPORTED value, so a Demo 20 run
        # with scaling off is directly comparable to a Demo 19 table.
        "chi2_1550_pm_per_V": reported_at_target,
        "peak_chi2_pm_per_V": reported_peak["magnitude_pm_per_V"],
        "peak_wavelength_nm": reported_peak["wavelength_nm"],
        # Both conventions, always retained.
        "chi2_raw_1550_pm_per_V": raw_at_target,
        "chi2_scaled_1550_pm_per_V": scaled_at_target,
        "chi2_reported_1550_pm_per_V": reported_at_target,
        "raw_peak_chi2_pm_per_V": raw_peak["magnitude_pm_per_V"],
        "scaled_peak_chi2_pm_per_V": scaled_peak["magnitude_pm_per_V"],
        "reported_peak_chi2_pm_per_V": reported_peak["magnitude_pm_per_V"],
        "raw_peak_wavelength_nm": raw_peak["wavelength_nm"],
        "scaled_peak_wavelength_nm": scaled_peak["wavelength_nm"],
        "peak_wavelength_shift_nm": abs(scaled_peak["wavelength_nm"]
                                        - raw_peak["wavelength_nm"]),
        "spectral_shape_max_difference": float(np.max(np.abs(
            pair.scaled.normalized_magnitude() - pair.raw.normalized_magnitude()
        ))),
        "raw_ratio_to_paper": raw_at_target / paper,
        "scaled_ratio_to_paper": scaled_at_target / paper,
        "raw_error_percent": 100.0 * abs(raw_at_target - paper) / paper,
        "scaled_error_percent": 100.0 * abs(scaled_at_target - paper) / paper,
    })


def _fill_demo19_reproduction(
    row: dict[str, Any], extracted: extract.ExtractedCase, raw_at_target: float
) -> None:
    """Compare Demo 20's raw value against the value Demo 19 recorded.

    The source table already contains Demo 19's own ``chi2_1550_pm_per_V``. With
    scaling off this must reproduce it, and the relative difference is written
    down rather than asserted, so a regression is visible in the output table.
    """

    extras = extracted.extras or {}
    previous = extras.get("chi2_1550_pm_per_V")
    if previous in (None, ""):
        row["chi2_reproduces_demo19"] = ""
        row["chi2_demo19_relative_difference"] = ""
        return
    try:
        reference = float(previous)
    except (TypeError, ValueError):
        row["chi2_reproduces_demo19"] = ""
        row["chi2_demo19_relative_difference"] = ""
        return
    relative = abs(raw_at_target - reference) / max(abs(reference), 1e-30)
    row["demo19_recorded_chi2_1550_pm_per_V"] = reference
    row["chi2_demo19_relative_difference"] = relative
    row["chi2_reproduces_demo19"] = bool(relative <= 1.0e-9)


def analyse_cases(
    cfg: Mapping[str, Any],
    extracted: Mapping[str, extract.ExtractedCase],
    *, window: str = "focused",
) -> list[CaseAnalysis]:
    """Evaluate both conventions for every case that has solver data."""

    settings = chi2mod.settings_from_config(cfg)
    wavelengths = chi2mod.wavelength_grid(cfg, window=window)
    scaling_on = config20.scaling_enabled(cfg)
    target = float(cfg["chi2"]["target_wavelength_nm"])
    results: list[CaseAnalysis] = []
    for case in cases.all_cases():
        row = _base_row(cfg, case)
        found = extracted.get(case.case_id)
        if found is None:
            row["failure_stage"] = "no_source_row"
            row["failure_reason"] = (
                f"case {case.case_id} is absent from "
                f"{cfg['analysis']['master_table']}"
            )
            results.append(CaseAnalysis(case, row, None))
            continue
        row["solver_pass"] = bool(found.solver_pass)
        row["physical_valid"] = bool(found.physical_valid)
        row["failure_stage"] = found.failure_stage
        row["failure_reason"] = found.failure_reason
        for key, value in (found.extras or {}).items():
            # Carried solver-derived fields that Demo 20 does not recompute.
            if key in ("electron_E1_centroid_nm", "electron_E2_centroid_nm",
                       "HH1_centroid_nm", "HH2_centroid_nm",
                       "solver_return_code", "spectrum_path"):
                row[key] = value
        if not found.has_states:
            results.append(CaseAnalysis(case, row, None))
            continue
        _fill_state_columns(row, found.states)
        pair = chi2mod.chi2_both_conventions(
            found.states, wavelengths, settings, scaling_enabled=scaling_on
        )
        _fill_chi2_columns(row, pair, cfg)
        _fill_demo19_reproduction(row, found, pair.raw.at_wavelength(target))
        results.append(CaseAnalysis(case, row, pair))
    _normalize_to_reference(cfg, results)
    return results


def _normalize_to_reference(
    cfg: Mapping[str, Any], results: Sequence[CaseAnalysis]
) -> None:
    """Fill the relative-to-reference columns.

    Two gates, on purpose:

    * ``chi2_1550_relative_to_abrupt`` and ``peak_chi2_relative_to_abrupt`` are
      Demo 19's own columns and keep Demo 19's own gate - they are filled only
      when the reference case is ``physical_valid``. Demo 19's copied run is
      physical_valid=False throughout, so these stay empty there too. That is
      preserved deliberately rather than fixed.
    * ``*_relative_to_reference`` are Demo 20 columns, filled whenever the
      reference case has a finite chi2. The comparison plots use these, so they
      have data without any unvalidated physics being relabelled as validated.
    """

    reference_id = str(cfg["analysis"]["reference_case_id"])
    strict = bool(cfg["analysis"]["strict_relative_requires_physical_valid"])
    reference = next((r for r in results if r.case_id == reference_id), None)
    if reference is None or not reference.has_spectrum:
        return
    raw_reference = reference.row["chi2_raw_1550_pm_per_V"]
    scaled_reference = reference.row["chi2_scaled_1550_pm_per_V"]
    raw_peak_reference = reference.row["raw_peak_chi2_pm_per_V"]
    scaled_peak_reference = reference.row["scaled_peak_chi2_pm_per_V"]
    reported_reference = reference.row["chi2_reported_1550_pm_per_V"]
    reported_peak_reference = reference.row["reported_peak_chi2_pm_per_V"]
    reference_physical = bool(reference.row["physical_valid"])

    for result in results:
        if not result.has_spectrum:
            continue
        row = result.row
        if raw_reference:
            row["chi2_raw_1550_relative_to_reference"] = (
                row["chi2_raw_1550_pm_per_V"] / raw_reference)
        if scaled_reference:
            row["chi2_scaled_1550_relative_to_reference"] = (
                row["chi2_scaled_1550_pm_per_V"] / scaled_reference)
        if raw_peak_reference:
            row["raw_peak_relative_to_reference"] = (
                row["raw_peak_chi2_pm_per_V"] / raw_peak_reference)
        if scaled_peak_reference:
            row["scaled_peak_relative_to_reference"] = (
                row["scaled_peak_chi2_pm_per_V"] / scaled_peak_reference)
        # Demo 19's own columns, under Demo 19's own gate.
        gate_open = (not strict) or (reference_physical and row["physical_valid"])
        if gate_open and reported_reference:
            row["chi2_1550_relative_to_abrupt"] = (
                row["chi2_reported_1550_pm_per_V"] / reported_reference)
        if gate_open and reported_peak_reference:
            row["peak_chi2_relative_to_abrupt"] = (
                row["reported_peak_chi2_pm_per_V"] / reported_peak_reference)


def presentation_rows(results: Sequence[CaseAnalysis]) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        row = result.row
        rows.append({
            "Case": row["case_name"], "Profile": row["profile"],
            "I1": row["I1_width_nm"], "I2": row["I2_width_nm"],
            "I3": row["I3_width_nm"], "I4": row["I4_width_nm"],
            "chi2_1550_raw": row.get("chi2_raw_1550_pm_per_V", ""),
            "chi2_1550_scaled": row.get("chi2_scaled_1550_pm_per_V", ""),
            "chi2_1550_reported": row.get("chi2_reported_1550_pm_per_V", ""),
            "Relative_to_abrupt": row.get("chi2_raw_1550_relative_to_reference", ""),
            "Peak_nm": row.get("raw_peak_wavelength_nm", ""),
            "Ratio_to_paper": row.get("raw_ratio_to_paper", ""),
        })
    return rows


def paper_comparison(
    cfg: Mapping[str, Any], results: Sequence[CaseAnalysis]
) -> dict[str, Any]:
    """Raw and scaled values against the published target. Never fitted to it."""

    paper = float(cfg["paper"]["target_chi2_pm_per_V"])
    reference_id = str(cfg["analysis"]["reference_case_id"])
    with_spectra = [r for r in results if r.has_spectrum]
    if not with_spectra:
        return {"paper_target_pm_per_V": paper, "evaluated": False,
                "reason": "no case produced a spectrum"}
    reference = next((r for r in with_spectra if r.case_id == reference_id),
                     with_spectra[0])
    raw = float(reference.row["chi2_raw_1550_pm_per_V"])
    scaled = float(reference.row["chi2_scaled_1550_pm_per_V"])
    best_raw = max(with_spectra, key=lambda r: float(r.row["chi2_raw_1550_pm_per_V"]))
    best_scaled = max(with_spectra,
                      key=lambda r: float(r.row["chi2_scaled_1550_pm_per_V"]))
    return {
        "paper_target_pm_per_V": paper,
        "paper_target_wavelength_nm": float(cfg["paper"]["target_wavelength_nm"]),
        "paper_source": str(cfg["paper"]["source"]).strip(),
        "evaluated": True,
        "reference_case_id": reference.case_id,
        "reference_case_name": reference.row["case_name"],
        "demo19_recorded_pm_per_V": reference.row.get(
            "demo19_recorded_chi2_1550_pm_per_V", ""),
        "demo20_reproduces_demo19": reference.row.get("chi2_reproduces_demo19", ""),
        "demo20_vs_demo19_relative_difference": reference.row.get(
            "chi2_demo19_relative_difference", ""),
        "demo20_raw_pm_per_V": raw,
        "demo20_scaled_pm_per_V": scaled,
        "raw_ratio_to_paper": raw / paper,
        "scaled_ratio_to_paper": scaled / paper,
        "raw_error_percent": 100.0 * abs(raw - paper) / paper,
        "scaled_error_percent": 100.0 * abs(scaled - paper) / paper,
        "remaining_factor_after_scaling": paper / scaled if scaled else None,
        "largest_raw_case": {
            "case_id": best_raw.case_id, "case_name": best_raw.row["case_name"],
            "chi2_pm_per_V": float(best_raw.row["chi2_raw_1550_pm_per_V"]),
        },
        "largest_scaled_case": {
            "case_id": best_scaled.case_id,
            "case_name": best_scaled.row["case_name"],
            "chi2_pm_per_V": float(best_scaled.row["chi2_scaled_1550_pm_per_V"]),
            "ratio_to_paper": float(best_scaled.row["scaled_ratio_to_paper"]),
        },
        "residual_analysis": _residual_analysis(cfg, scaled, paper),
        "interpretation": (
            "Neither convention reproduces the published target. The (2*pi)^2 "
            "convention closes most of the gap but is not a fit and is not "
            "evidence that the scaled convention is the paper's. The residual "
            "factor is recorded as remaining_factor_after_scaling."
        ),
    }


def _residual_analysis(
    cfg: Mapping[str, Any], scaled: float, paper: float
) -> dict[str, Any]:
    """What is left over after scaling, and which known ambiguity is that size.

    Recorded because it is a lead worth following, NOT a result. The N_z
    counting convention is a genuine documented ambiguity in this model
    (``s06_chi2.n_z_for``: one coupled pair per period vs its two individual
    wells) and it is exactly a factor of two. Reporting that the residual is
    close to two is an observation; combining conventions until a number
    matches would be fitting, which Demo 20 does not do.
    """

    if not scaled:
        return {"evaluated": False}
    residual = paper / scaled
    alternative_nz = float(cfg["chi2"]["wells_per_period"])
    return {
        "evaluated": True,
        "remaining_factor": residual,
        "nz_alternative_convention": "well_density",
        "nz_alternative_multiplier": alternative_nz,
        "chi2_if_scaled_and_well_density_pm_per_V": scaled * alternative_nz,
        "ratio_to_paper_if_both": scaled * alternative_nz / paper,
        "note": (
            "The residual is close to the N_z counting ambiguity, which is a "
            "factor of exactly "
            f"{alternative_nz:g}. This is recorded as a lead only: two "
            "independent convention changes that happen to multiply to roughly "
            "the published number is not evidence that either is the paper's "
            "choice. Confirming it requires the paper's own k-space measure and "
            "its own N_z definition, neither of which this checkout can "
            "establish."
        ),
    }


def spectra_by_case(
    results: Sequence[CaseAnalysis], *, convention: str = "raw"
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """``{case_id: (wavelength_nm, |chi2|)}`` for plotting."""

    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for result in results:
        if not result.has_spectrum:
            continue
        pair = result.pair
        spectrum = {"raw": pair.raw, "scaled": pair.scaled,
                    "reported": pair.reported}[convention]
        out[result.case_id] = (spectrum.wavelength_nm, spectrum.magnitude)
    return out
