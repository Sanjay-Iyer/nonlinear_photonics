"""Scientific core for Demo 18's one-solve absolute-scale audit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import cases18
import chi2 as chi2mod

DEMO_VERSION = "demo18-1.0.0"
PREFAC_DENOMINATOR = 6.0

# Independent CODATA declarations. These intentionally do not alias the shared
# module's constants: Demo 18 uses them to reconstruct the energy-form absolute
# conversion independently and compares that number with Chi2Result.scale_factor.
SI_ELEMENTARY_CHARGE_C = 1.602176634e-19
SI_VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
SI_REDUCED_PLANCK_J_S = 1.054571817e-34


class Demo18Error(RuntimeError):
    pass


@dataclass(frozen=True)
class EvaluatedCase:
    row: dict[str, Any]
    wavelength_nm: np.ndarray
    chi2: np.ndarray


def wavelength_grid(cfg: Mapping[str, Any]) -> np.ndarray:
    chi = cfg["chi2"]
    return np.linspace(
        float(chi["wavelength_start_nm"]),
        float(chi["wavelength_stop_nm"]),
        int(chi["wavelength_points"]),
    )


def settings_for_case(
    cfg: Mapping[str, Any], case: cases18.ScaleCase
) -> chi2mod.Chi2Settings:
    chi = cfg["chi2"]
    kdef = cases18.KMAX_CONVENTIONS[case.kmax_convention]
    return chi2mod.Chi2Settings(
        mode="absolute",
        broadening_meV=float(chi["broadening_meV"]),
        k_parallel_fraction_of_bz=float(kdef["fraction_for_chi2_settings"]),
        k_parallel_points=int(case.k_points),
        lattice_constant_nm=float(chi["lattice_constant_nm"]),
        electron_mass_m0=float(chi["electron_mass_m0"]),
        heavy_hole_inplane_mass_m0=float(chi["heavy_hole_inplane_mass_m0"]),
        spin_degeneracy=int(case.spin_degeneracy),
        max_states_per_band=2,
        r_e_hh_nm=float(chi["r_e_hh_nm"]) * float(case.r_scale),
        n_wells_per_metre=float(cases18.NZ_CONVENTIONS[case.nz_convention]),
    )


def independent_energy_form_prefactor(
    *, n_wells_per_metre: float, r_e_hh_nm: float
) -> float:
    """Rebuild production's per-summand scale independently, in pm/V.

    The state sum used by ``chi2.py`` carries nm from <psi|z|psi>, nm^-2 from
    the radial k measure, and eV^-2 from its two energy denominators. Therefore:

      nm -> m       : 1e-9
      nm^-2 -> m^-2 : 1e18
      eV^-2 -> J^-2 : 1/e^2
      m/V -> pm/V   : 1e12

    In the paper's angular-frequency form each denominator is DeltaE/hbar, so
    their inverse product contributes hbar^2/DeltaE^2 and exactly cancels the
    explicit 1/hbar^2 prefactor. No hbar belongs in this energy-form scalar.
    """

    nz = float(n_wells_per_metre)
    r_m = float(r_e_hh_nm) * 1.0e-9
    nm_to_m = 1.0e-9
    inverse_square_nm_to_inverse_square_m = 1.0e18
    inverse_square_eV_to_inverse_square_J = 1.0 / SI_ELEMENTARY_CHARGE_C**2
    metre_per_volt_to_pm_per_volt = 1.0e12
    return (
        nz
        * SI_ELEMENTARY_CHARGE_C**3
        * r_m**2
        / (PREFAC_DENOMINATOR * SI_VACUUM_PERMITTIVITY_F_PER_M)
        * nm_to_m
        * inverse_square_nm_to_inverse_square_m
        * inverse_square_eV_to_inverse_square_J
        * metre_per_volt_to_pm_per_volt
    )


def prefactor_cross_check(
    production_prefactor: float,
    settings: chi2mod.Chi2Settings,
    *,
    tolerance: float,
) -> dict[str, Any]:
    independent = independent_energy_form_prefactor(
        n_wells_per_metre=float(settings.n_wells_per_metre),
        r_e_hh_nm=float(settings.r_e_hh_nm),
    )
    denominator = abs(independent) if independent else 1.0
    residual = abs(float(production_prefactor) - independent) / denominator
    return {
        "production_prefactor": float(production_prefactor),
        "independent_si_prefactor": float(independent),
        "relative_difference": float(residual),
        "tolerance": float(tolerance),
        "passed": bool(residual <= float(tolerance)),
        "production_sum_units": "nm * nm^-2 * eV^-2",
        "conversion_nm_to_m": 1.0e-9,
        "conversion_nm^-2_to_m^-2": 1.0e18,
        "conversion_eV^-2_to_J^-2": 1.0 / SI_ELEMENTARY_CHARGE_C**2,
        "conversion_m_per_V_to_pm_per_V": 1.0e12,
        "angular_frequency_hbar_statement": (
            "Each inverse angular-frequency denominator contributes hbar; the "
            "pair contributes hbar^2 and cancels the paper prefactor's 1/hbar^2."
        ),
        "hbar_J_s_used_for_documented_equivalence": SI_REDUCED_PLANCK_J_S,
    }


def load_band_states(
    solver_cfg: Mapping[str, Any], raw_output: Path
) -> tuple[chi2mod.BandStates, chi2mod.BandStates]:
    """Parse the same Gamma/HH artifacts used by Demo 11."""

    import demo11
    import outputs
    import quantum1d

    profile = outputs.load_profile(str(solver_cfg["nextnano"]["parser_profile"]))
    region = str(solver_cfg["nextnano"]["quantum_region_name"])
    run = quantum1d.parse_one_band_run(
        Path(raw_output),
        profile=profile,
        region_name=region,
        bandedge_columns=solver_cfg["nextnano"]["bandedge_columns"],
    )
    if run.envelopes is None:
        raise Demo18Error("Gamma electron envelopes are missing")
    hole_z, hole_energies, hole_envelopes = demo11._hole_states(
        profile, Path(raw_output), region
    )
    if hole_z.shape != run.state_position_nm.shape or not np.allclose(
        hole_z, run.state_position_nm
    ):
        raise Demo18Error("electron and heavy-hole envelope grids do not match")
    return (
        chi2mod.BandStates(
            run.state_position_nm, run.energies_eV, run.envelopes, "e"
        ),
        chi2mod.BandStates(hole_z, hole_energies, hole_envelopes, "hh"),
    )


def solver_quantities(
    electron: chi2mod.BandStates, heavy_hole: chi2mod.BandStates
) -> dict[str, Any]:
    overlap = chi2mod.overlap_matrix(electron, heavy_hole)
    z_e = chi2mod.position_matrix(electron)
    z_h = chi2mod.position_matrix(heavy_hole)
    if electron.count < 2 or heavy_hole.count < 2:
        raise Demo18Error("Demo 18 needs at least two states in each band")
    return {
        "Ee1_eV": float(electron.energies_eV[0]),
        "Ee2_eV": float(electron.energies_eV[1]),
        "Ehh1_eV": float(heavy_hole.energies_eV[0]),
        "Ehh2_eV": float(heavy_hole.energies_eV[1]),
        "E1_minus_HH1_eV": float(
            electron.energies_eV[0] - heavy_hole.energies_eV[0]
        ),
        "E2_minus_HH2_eV": float(
            electron.energies_eV[1] - heavy_hole.energies_eV[1]
        ),
        "electron_hole_overlap_matrix": overlap[:2, :2].tolist(),
        "electron_z_matrix_nm": z_e[:2, :2].tolist(),
        "heavy_hole_z_matrix_nm": z_h[:2, :2].tolist(),
        "electron_orthonormality_error": electron.orthonormality_error(),
        "heavy_hole_orthonormality_error": heavy_hole.orthonormality_error(),
        "electron_states_available": electron.count,
        "heavy_hole_states_available": heavy_hole.count,
    }


def evaluate_case(
    cfg: Mapping[str, Any],
    case: cases18.ScaleCase,
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
    wavelengths_nm: Sequence[float] | np.ndarray,
) -> EvaluatedCase:
    settings = settings_for_case(cfg, case)
    wavelengths = np.asarray(wavelengths_nm, dtype=float)
    spectrum = chi2mod.chi2_spectrum(
        electron,
        heavy_hole,
        chi2mod.photon_energy_eV(wavelengths),
        settings,
    )
    target_nm = float(cfg["chi2"]["target_wavelength_nm"])
    target = chi2mod.chi2_spectrum(
        electron,
        heavy_hole,
        [float(chi2mod.photon_energy_eV(target_nm))],
        settings,
    )
    target_value = complex(target.chi2[0])
    peak_index = int(np.argmax(np.abs(spectrum.chi2)))
    check = prefactor_cross_check(
        spectrum.scale_factor,
        settings,
        tolerance=float(cfg["chi2"]["prefactor_relative_tolerance"]),
    )
    if not check["passed"]:
        raise Demo18Error(
            f"{case.case_id}: production/independent prefactors disagree: "
            f"{check['relative_difference']:.3e}"
        )
    row = {
        **case.as_record(),
        "chi2_real_at_1550_pm_per_V": float(target_value.real),
        "chi2_imag_at_1550_pm_per_V": float(target_value.imag),
        "chi2_magnitude_at_1550_pm_per_V": float(abs(target_value)),
        "chi2_at_1550_pm_per_V": float(abs(target_value)),
        "peak_chi2_pm_per_V": float(abs(spectrum.chi2[peak_index])),
        "peak_wavelength_nm": float(wavelengths[peak_index]),
        "Nz_per_metre": float(settings.n_wells_per_metre),
        "Nz_convention": case.nz_convention,
        "kmax_per_nm": float(settings.k_max_per_nm),
        "kmax_convention": case.kmax_convention,
        "k_space_normalization": "integral d^2k/(2*pi)^2; radial k/(2*pi) dk",
        "k_points": int(case.k_points),
        "spin_degeneracy": int(settings.spin_degeneracy),
        "r_e_hh_nm": float(settings.r_e_hh_nm),
        "broadening_meV": float(settings.broadening_meV),
        "production_prefactor": check["production_prefactor"],
        "independent_si_prefactor": check["independent_si_prefactor"],
        "prefactor_relative_difference": check["relative_difference"],
        "prefactor_cross_check_passed": check["passed"],
        "chi2_units": settings.units,
    }
    return EvaluatedCase(row, wavelengths, np.asarray(spectrum.chi2, complex))


def evaluate_matrix(
    cfg: Mapping[str, Any],
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
) -> tuple[list[EvaluatedCase], dict[str, Any], list[dict[str, Any]]]:
    wavelengths = wavelength_grid(cfg)
    evaluated = [
        evaluate_case(cfg, case, electron, heavy_hole, wavelengths)
        for case in cases18.audit_cases()
    ]
    by_id = {result.row["case_id"]: result.row for result in evaluated}
    convergence_rows: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for case_id in ("D_Nz_plus_large_kmax", "E_kgrid_192", "F_kgrid_384"):
        row = by_id[case_id]
        value = float(row["chi2_at_1550_pm_per_V"])
        entry = {
            "case_id": case_id,
            "kmax_convention": row["kmax_convention"],
            "k_points": row["k_points"],
            "chi2_at_1550_pm_per_V": value,
            "peak_chi2_pm_per_V": row["peak_chi2_pm_per_V"],
            "peak_wavelength_nm": row["peak_wavelength_nm"],
            "relative_change_from_previous": (
                None
                if previous is None or not previous["chi2_at_1550_pm_per_V"]
                else abs(value - previous["chi2_at_1550_pm_per_V"])
                / abs(previous["chi2_at_1550_pm_per_V"])
            ),
        }
        convergence_rows.append(entry)
        previous = entry
    scaling = {
        "Nz_ratio_B_over_A": (
            by_id["B_two_wells_Nz"]["chi2_at_1550_pm_per_V"]
            / by_id["A_baseline"]["chi2_at_1550_pm_per_V"]
        ),
        "spin_ratio_H_over_G": (
            by_id["H_spin2"]["chi2_at_1550_pm_per_V"]
            / by_id["G_spin1"]["chi2_at_1550_pm_per_V"]
        ),
        "prefactor_checks_passed": all(
            row["prefactor_cross_check_passed"] for row in by_id.values()
        ),
    }
    return evaluated, scaling, convergence_rows


def r_sensitivity(
    cfg: Mapping[str, Any],
    electron: chi2mod.BandStates,
    heavy_hole: chi2mod.BandStates,
) -> list[dict[str, Any]]:
    base = next(row for row in cases18.audit_cases() if row.case_id == "H_spin2")
    target_nm = float(cfg["chi2"]["target_wavelength_nm"])
    rows: list[dict[str, Any]] = []
    baseline: float | None = None
    scales = [float(v) for v in cfg["audits"]["r_sensitivity_scales"]]
    for scale in scales:
        probe = cases18.ScaleCase(
            f"r_{scale:.2f}", f"r x {scale:.2f}", base.nz_convention,
            base.kmax_convention, base.k_points, base.spin_degeneracy, scale,
        )
        result = evaluate_case(
            cfg, probe, electron, heavy_hole, np.asarray([target_nm])
        ).row
        value = float(result["chi2_at_1550_pm_per_V"])
        if abs(scale - 1.0) < 1.0e-12:
            baseline = value
        rows.append({
            "r_scale": scale,
            "r_e_hh_nm": result["r_e_hh_nm"],
            "chi2_at_1550_pm_per_V": value,
            "expected_ratio": scale**2,
        })
    if baseline is None or baseline == 0.0:
        raise Demo18Error("r sensitivity baseline is zero or missing")
    for row in rows:
        row["measured_ratio"] = row["chi2_at_1550_pm_per_V"] / baseline
        row["relative_scaling_error"] = abs(
            row["measured_ratio"] - row["expected_ratio"]
        ) / row["expected_ratio"]
        row["passed"] = bool(row["relative_scaling_error"] <= 1.0e-12)
    return rows


def synthetic_states() -> tuple[chi2mod.BandStates, chi2mod.BandStates]:
    """Small asymmetric, orthonormal solver-free fixture for preflight/tests."""

    z = np.linspace(0.0, 10.0, 1001)
    e1 = np.sqrt(2.0 / 10.0) * np.sin(np.pi * z / 10.0)
    e2 = np.sqrt(2.0 / 10.0) * np.sin(2.0 * np.pi * z / 10.0)
    theta = 0.31
    h1 = np.cos(theta) * e1 + np.sin(theta) * e2
    h2 = -np.sin(theta) * e1 + np.cos(theta) * e2
    return (
        chi2mod.BandStates(z, np.asarray([2.95, 3.08]), np.column_stack([e1, e2]), "e"),
        chi2mod.BandStates(z, np.asarray([1.45, 1.40]), np.column_stack([h1, h2]), "hh"),
    )


def preflight_audits(cfg: Mapping[str, Any]) -> dict[str, Any]:
    electron, heavy_hole = synthetic_states()
    target = np.asarray([float(cfg["chi2"]["target_wavelength_nm"])])
    rows = {
        case.case_id: evaluate_case(cfg, case, electron, heavy_hole, target).row
        for case in cases18.audit_cases()
    }
    nz_ratio = rows["B_two_wells_Nz"]["chi2_at_1550_pm_per_V"] / rows[
        "A_baseline"
    ]["chi2_at_1550_pm_per_V"]
    spin_ratio = rows["H_spin2"]["chi2_at_1550_pm_per_V"] / rows[
        "G_spin1"
    ]["chi2_at_1550_pm_per_V"]
    r_rows = r_sensitivity(cfg, electron, heavy_hole)
    grid_checks = []
    for points in (96, 192, 384):
        probe = cases18.ScaleCase(
            f"grid_{points}", "grid", "two_wells_per_period",
            "bz_2pi_over_a", points, 2,
        )
        settings = settings_for_case(cfg, probe)
        k, _weights = chi2mod._k_grid(settings)
        grid_checks.append({
            "points": points,
            "count": int(k.size),
            "last_k_per_nm": float(k[-1]),
            "expected_kmax_per_nm": float(settings.k_max_per_nm),
            "passed": bool(k.size == points and k[-1] == settings.k_max_per_nm),
        })
    checks = {
        "Nz_scaling_is_two": bool(abs(nz_ratio - 2.0) <= 1.0e-12),
        "spin_scaling_is_two": bool(abs(spin_ratio - 2.0) <= 1.0e-12),
        "r_squared_scaling": all(row["passed"] for row in r_rows),
        "prefactor_cross_checks": all(
            row["prefactor_cross_check_passed"] for row in rows.values()
        ),
        "k_grids_reach_cutoff": all(row["passed"] for row in grid_checks),
    }
    checks["passed"] = all(checks.values())
    return {
        "checks": checks,
        "Nz_ratio": nz_ratio,
        "spin_ratio": spin_ratio,
        "r_sensitivity": r_rows,
        "k_grids": grid_checks,
    }

