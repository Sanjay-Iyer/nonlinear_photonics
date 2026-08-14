"""Generalized Eq. 3 state-sum and invariance audits for Demo 18E.

The paper calls its reduced susceptibility expression Eq. (3). Earlier demos
called the same reduced expression Eq. 2; output filenames retain that historical
repository name. Unlike the shared production routine, this implementation allows
independent electron and HH state counts and complex, consistently transformed
matrix elements.
"""

from __future__ import annotations

from dataclasses import dataclass
import cmath
import itertools
import math
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


E_CHARGE_C = 1.602176634e-19
EPSILON_0_F_M = 8.8541878128e-12
HBAR_J_S = 1.054571817e-34
ELECTRON_MASS_KG = 9.1093837015e-31
HC_EV_NM = 1239.841984


@dataclass(frozen=True)
class Settings:
    broadening_meV: float = 5.0
    k_points: int = 768
    kmax_fraction_2pi_over_a: float = 0.10
    lattice_constant_nm: float = 0.565325
    electron_mass_m0: float = 0.067
    heavy_hole_mass_m0: float = 0.112
    spin_degeneracy: int = 2
    r_e_hh_nm: float = 0.751
    n_wells_per_metre: float = 2.0 / 30.0e-9


@dataclass(frozen=True)
class MatrixModel:
    electron_energies_eV: np.ndarray
    heavy_hole_energies_eV: np.ndarray
    overlap_eh: np.ndarray
    z_e_nm: np.ndarray
    z_hh_nm: np.ndarray
    electron_labels: tuple[str, ...]
    heavy_hole_labels: tuple[str, ...]

    def __post_init__(self) -> None:
        ee = np.asarray(self.electron_energies_eV, float)
        hh = np.asarray(self.heavy_hole_energies_eV, float)
        overlap = np.asarray(self.overlap_eh, complex)
        ze = np.asarray(self.z_e_nm, complex)
        zh = np.asarray(self.z_hh_nm, complex)
        if overlap.shape != (ee.size, hh.size):
            raise ValueError(f"overlap shape {overlap.shape} != {(ee.size, hh.size)}")
        if ze.shape != (ee.size, ee.size) or zh.shape != (hh.size, hh.size):
            raise ValueError("position-matrix dimensions do not match energy counts")
        if len(self.electron_labels) != ee.size or len(self.heavy_hole_labels) != hh.size:
            raise ValueError("state labels do not match energy counts")
        if not np.allclose(ze, ze.conj().T, rtol=0.0, atol=1e-10):
            raise ValueError("electron position matrix is not Hermitian")
        if not np.allclose(zh, zh.conj().T, rtol=0.0, atol=1e-10):
            raise ValueError("HH position matrix is not Hermitian")
        object.__setattr__(self, "electron_energies_eV", ee)
        object.__setattr__(self, "heavy_hole_energies_eV", hh)
        object.__setattr__(self, "overlap_eh", overlap)
        object.__setattr__(self, "z_e_nm", ze)
        object.__setattr__(self, "z_hh_nm", zh)

    @property
    def n_e(self) -> int:
        return int(self.electron_energies_eV.size)

    @property
    def n_hh(self) -> int:
        return int(self.heavy_hole_energies_eV.size)

    def subset(self, electron_indices: Sequence[int], hh_indices: Sequence[int]) -> "MatrixModel":
        ei = np.asarray(electron_indices, int)
        hi = np.asarray(hh_indices, int)
        return MatrixModel(
            self.electron_energies_eV[ei], self.heavy_hole_energies_eV[hi],
            self.overlap_eh[np.ix_(ei, hi)], self.z_e_nm[np.ix_(ei, ei)],
            self.z_hh_nm[np.ix_(hi, hi)],
            tuple(self.electron_labels[i] for i in ei),
            tuple(self.heavy_hole_labels[i] for i in hi),
        )


def settings_from_config(cfg: Mapping[str, Any]) -> Settings:
    fixed = cfg["fixed_physics"]
    return Settings(
        broadening_meV=float(fixed["broadening_meV"]),
        k_points=int(fixed["k_points"]),
        kmax_fraction_2pi_over_a=float(fixed["kmax_fraction_2pi_over_a"]),
        lattice_constant_nm=float(fixed["lattice_constant_nm"]),
        electron_mass_m0=float(fixed["electron_inplane_mass_m0"]),
        heavy_hole_mass_m0=float(fixed["heavy_hole_inplane_mass_m0"]),
        spin_degeneracy=int(fixed["spin_degeneracy"]),
        r_e_hh_nm=float(fixed["r_e_hh_nm"]),
        n_wells_per_metre=float(fixed["wells_per_period_for_Nz"])
        / (float(fixed["nominal_period_nm"]) * 1.0e-9),
    )


def prefactor(settings: Settings) -> float:
    r_m = settings.r_e_hh_nm * 1.0e-9
    return (
        settings.n_wells_per_metre * E_CHARGE_C**3 * r_m**2
        / (6.0 * EPSILON_0_F_M)
        * 1.0e-9 * 1.0e18 / E_CHARGE_C**2 * 1.0e12
    )


def _grid(settings: Settings) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    kmax = 2.0 * settings.kmax_fraction_2pi_over_a * math.pi / settings.lattice_constant_nm
    k = np.linspace(0.0, kmax, settings.k_points)
    step = k[1] - k[0]
    trap = np.full(k.size, step)
    trap[[0, -1]] *= 0.5
    weights = k / (2.0 * math.pi) * trap * settings.spin_degeneracy
    inverse_mass = 1.0 / settings.electron_mass_m0 + 1.0 / settings.heavy_hole_mass_m0
    reduced_mass_kg = ELECTRON_MASS_KG / inverse_mass
    kinetic_eV = HBAR_J_S**2 * (k * 1.0e9) ** 2 / (2.0 * reduced_mass_kg) / E_CHARGE_C
    return k, weights, kinetic_eV


def _complex_string(value: complex) -> str:
    return f"{value.real:.17g}{value.imag:+.17g}j"


def evaluate(
    model: MatrixModel,
    photon_energy_eV: float,
    settings: Settings,
    *,
    decompose: bool = False,
    gamma_sign: int = 1,
    hh_path_sign: int = -1,
) -> tuple[complex, dict[str, complex], list[dict[str, Any]]]:
    """Evaluate the unequal-state paper sum with phase-correct bra/ket products."""

    if gamma_sign not in (-1, 1) or hh_path_sign not in (-1, 1):
        raise ValueError("sign controls must be +/-1")
    _k, weights, kinetic = _grid(settings)
    transitions = (
        model.electron_energies_eV[:, None, None]
        - model.heavy_hole_energies_eV[None, :, None]
        + kinetic[None, None, :]
    )
    hw = float(photon_energy_eV)
    gamma = gamma_sign * float(settings.broadening_meV) * 1.0e-3
    scale = prefactor(settings)
    electron_total = 0.0j
    hh_total = 0.0j
    rows: list[dict[str, Any]] = []
    term_id = 0
    for m in range(model.n_hh):
        for n in range(model.n_e):
            first = transitions[n, m] - 2.0 * hw + 1j * gamma
            for l in range(model.n_e):
                term_id += 1
                overlap_1 = np.conj(model.overlap_eh[n, m])  # <hh_m|e_n>
                z_value = model.z_e_nm[n, l]
                overlap_2 = model.overlap_eh[l, m]           # <e_l|hh_m>
                numerator = overlap_1 * z_value * overlap_2
                second = transitions[l, m] - hw + 1j * gamma
                integrated = complex(np.dot(weights, numerator / (first * second)))
                contribution = scale * integrated
                electron_total += contribution
                if decompose:
                    rows.append(_term_row(
                        term_id, "electron-mediated", m, n, l, model,
                        overlap_1, z_value, overlap_2, numerator, first, second,
                        integrated, contribution, +1,
                    ))
            for l in range(model.n_hh):
                term_id += 1
                overlap_1 = model.overlap_eh[n, m]           # <e_n|hh_m>
                z_value = model.z_hh_nm[m, l]
                overlap_2 = np.conj(model.overlap_eh[n, l]) # <hh_l|e_n>
                numerator = overlap_1 * z_value * overlap_2
                second = transitions[n, l] - hw + 1j * gamma
                integrated = complex(np.dot(
                    weights, hh_path_sign * numerator / (first * second)
                ))
                contribution = scale * integrated
                hh_total += contribution
                if decompose:
                    rows.append(_term_row(
                        term_id, "HH-mediated", m, n, l, model,
                        overlap_1, z_value, overlap_2, numerator, first, second,
                        integrated, contribution, hh_path_sign,
                    ))
    rows.sort(key=lambda row: float(row["final_pm_per_V_abs"]), reverse=True)
    for rank, row in enumerate(rows, 1):
        row["magnitude_rank"] = rank
    branches = {"electron": electron_total, "heavy_hole": hh_total}
    return electron_total + hh_total, branches, rows


def _term_row(
    term_id: int, pathway: str, m: int, n: int, l: int, model: MatrixModel,
    overlap_1: complex, z_value: complex, overlap_2: complex, numerator: complex,
    first: np.ndarray, second: np.ndarray, integrated: complex,
    contribution: complex, sign: int,
) -> dict[str, Any]:
    electron_state = model.electron_labels[n]
    hh_state = model.heavy_hole_labels[m]
    partner = model.electron_labels[l] if pathway == "electron-mediated" else model.heavy_hole_labels[l]
    return {
        "term_id": f"T{term_id:03d}", "pathway": pathway,
        "m": m + 1, "n": n + 1, "l": l + 1,
        "electron_state": electron_state, "hh_state": hh_state,
        "partner_state": partner,
        "overlap_1": _complex_string(overlap_1),
        "overlap_1_real": float(overlap_1.real), "overlap_1_imag": float(overlap_1.imag),
        "z_matrix_element": _complex_string(z_value),
        "z_matrix_element_real": float(z_value.real), "z_matrix_element_imag": float(z_value.imag),
        "overlap_2": _complex_string(overlap_2),
        "overlap_2_real": float(overlap_2.real), "overlap_2_imag": float(overlap_2.imag),
        "numerator": _complex_string(numerator),
        "numerator_real": float(numerator.real), "numerator_imag": float(numerator.imag),
        "denominator_1_real": float(first[0].real),
        "denominator_1_imag": float(first[0].imag),
        "denominator_2_real": float(second[0].real),
        "denominator_2_imag": float(second[0].imag),
        "complex_term_real": float((sign * numerator / (first[0] * second[0])).real),
        "complex_term_imag": float((sign * numerator / (first[0] * second[0])).imag),
        "term_abs": float(abs(sign * numerator / (first[0] * second[0]))),
        "integrated_real": float(integrated.real), "integrated_imag": float(integrated.imag),
        "integrated_abs": float(abs(integrated)),
        "final_pm_per_V_real": float(contribution.real),
        "final_pm_per_V_imag": float(contribution.imag),
        "final_pm_per_V_abs": float(abs(contribution)), "sign": sign,
    }


def spectrum(
    model: MatrixModel, wavelengths_nm: Sequence[float], settings: Settings,
    *, gamma_sign: int = 1, hh_path_sign: int = -1,
) -> dict[str, np.ndarray]:
    wavelengths = np.asarray(wavelengths_nm, float)
    electron = np.empty(wavelengths.size, complex)
    hh = np.empty(wavelengths.size, complex)
    for index, wavelength in enumerate(wavelengths):
        _total, branches, _rows = evaluate(
            model, HC_EV_NM / wavelength, settings,
            gamma_sign=gamma_sign, hh_path_sign=hh_path_sign,
        )
        electron[index] = branches["electron"]
        hh[index] = branches["heavy_hole"]
    return {"wavelength_nm": wavelengths, "chi_e": electron,
            "chi_hh": hh, "chi_total": electron + hh}


def summarize_spectrum(label: str, data: Mapping[str, np.ndarray], target_nm: float = 1550.0) -> dict[str, Any]:
    wavelengths = np.asarray(data["wavelength_nm"], float)
    target_index = int(np.argmin(np.abs(wavelengths - target_nm)))
    magnitude = np.abs(data["chi_total"])
    peak_index = int(np.argmax(magnitude))
    electron = complex(data["chi_e"][target_index])
    hh = complex(data["chi_hh"][target_index])
    total = electron + hh
    phase = math.degrees(abs(cmath.phase(electron / hh))) if abs(hh) else float("nan")
    return {
        "state_selection": label,
        "chi2_1550_pm_per_V": float(abs(total)),
        "peak_wavelength_nm": float(wavelengths[peak_index]),
        "peak_chi2_pm_per_V": float(magnitude[peak_index]),
        "chi_e_real": float(electron.real), "chi_e_imag": float(electron.imag),
        "chi_e_abs": float(abs(electron)),
        "chi_hh_real": float(hh.real), "chi_hh_imag": float(hh.imag),
        "chi_hh_abs": float(abs(hh)),
        "chi_total_real": float(total.real), "chi_total_imag": float(total.imag),
        "chi_total_abs": float(abs(total)),
        "phase_difference_deg": float(phase),
        "cancellation_factor": float((abs(electron) + abs(hh)) / max(abs(total), 1e-30)),
    }


def transform(model: MatrixModel, electron_u: np.ndarray, hh_u: np.ndarray,
              electron_energies_eV: Sequence[float] | None = None,
              hh_energies_eV: Sequence[float] | None = None,
              electron_labels: Sequence[str] | None = None,
              hh_labels: Sequence[str] | None = None) -> MatrixModel:
    """Transform every matrix consistently for |new> = |old> U."""

    ue = np.asarray(electron_u, complex)
    uh = np.asarray(hh_u, complex)
    if not np.allclose(ue.conj().T @ ue, np.eye(model.n_e), atol=1e-12):
        raise ValueError("electron transform is not unitary")
    if not np.allclose(uh.conj().T @ uh, np.eye(model.n_hh), atol=1e-12):
        raise ValueError("HH transform is not unitary")
    return MatrixModel(
        np.asarray(electron_energies_eV if electron_energies_eV is not None
                   else model.electron_energies_eV, float),
        np.asarray(hh_energies_eV if hh_energies_eV is not None
                   else model.heavy_hole_energies_eV, float),
        ue.conj().T @ model.overlap_eh @ uh,
        ue.conj().T @ model.z_e_nm @ ue,
        uh.conj().T @ model.z_hh_nm @ uh,
        tuple(electron_labels or model.electron_labels),
        tuple(hh_labels or model.heavy_hole_labels),
    )


def phase_invariance(model: MatrixModel, settings: Settings, *, seed: int, trials: int,
                     wavelength_nm: float = 1550.0) -> list[dict[str, Any]]:
    baseline, _parts, _terms = evaluate(model, HC_EV_NM / wavelength_nm, settings)
    rng = np.random.default_rng(seed)
    rows = []
    for trial in range(trials):
        e_phase = rng.uniform(-math.pi, math.pi, model.n_e)
        h_phase = rng.uniform(-math.pi, math.pi, model.n_hh)
        rotated = transform(model, np.diag(np.exp(1j * e_phase)), np.diag(np.exp(1j * h_phase)))
        value, _branches, _rows = evaluate(rotated, HC_EV_NM / wavelength_nm, settings)
        rows.append({
            "trial": trial, "seed": seed,
            "electron_phases_rad": ";".join(f"{v:.17g}" for v in e_phase),
            "hh_phases_rad": ";".join(f"{v:.17g}" for v in h_phase),
            "baseline_real": float(baseline.real), "baseline_imag": float(baseline.imag),
            "transformed_real": float(value.real), "transformed_imag": float(value.imag),
            "absolute_residual": float(abs(value - baseline)),
            "relative_residual": float(abs(value - baseline) / max(abs(baseline), 1e-30)),
        })
    return rows


def permutation_invariance(model: MatrixModel, settings: Settings,
                           wavelength_nm: float = 1550.0) -> list[dict[str, Any]]:
    baseline, _parts, _terms = evaluate(model, HC_EV_NM / wavelength_nm, settings)
    e_orders = [tuple(range(model.n_e)), tuple(reversed(range(model.n_e)))]
    h_orders = [tuple(range(model.n_hh))]
    if model.n_hh >= 3:
        h_orders.extend([(2, 0, 1), (1, 2, 0)])
    elif model.n_hh == 2:
        h_orders.append((1, 0))
    rows = []
    for e_order, h_order in itertools.product(e_orders, h_orders):
        permuted = model.subset(e_order, h_order)
        value, _branches, _terms = evaluate(permuted, HC_EV_NM / wavelength_nm, settings)
        rows.append({
            "electron_order": ";".join(permuted.electron_labels),
            "hh_order": ";".join(permuted.heavy_hole_labels),
            "chi_real": float(value.real), "chi_imag": float(value.imag),
            "absolute_residual": float(abs(value - baseline)),
            "relative_residual": float(abs(value - baseline) / max(abs(baseline), 1e-30)),
        })
    return rows


def hh23_rotation_model(model3: MatrixModel, theta_deg: float) -> MatrixModel:
    """Rotate HH2/HH3 in the exact-degenerate control Hamiltonian."""

    if model3.n_hh != 3:
        raise ValueError("HH2/HH3 rotation requires exactly HH1, HH2, HH3")
    theta = math.radians(theta_deg)
    uh = np.eye(3, dtype=complex)
    uh[1:, 1:] = np.array([[math.cos(theta), -math.sin(theta)],
                           [math.sin(theta), math.cos(theta)]], complex)
    mean = float(np.mean(model3.heavy_hole_energies_eV[1:3]))
    energies = np.array([model3.heavy_hole_energies_eV[0], mean, mean])
    return transform(
        model3, np.eye(model3.n_e), uh, hh_energies_eV=energies,
        hh_labels=("HH1", f"HH_a({theta_deg:g})", f"HH_b({theta_deg:g})"),
    )


def rotation_audit(model3: MatrixModel, settings: Settings, angles_deg: Iterable[float],
                   wavelengths_nm: Sequence[float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for theta in angles_deg:
        rotated = hh23_rotation_model(model3, float(theta))
        for role, selected in (("truncated_HH1_plus_HH_a", rotated.subset(range(rotated.n_e), (0, 1))),
                               ("complete_HH1_HH_a_HH_b", rotated)):
            result = summarize_spectrum(role, spectrum(selected, wavelengths_nm, settings))
            rows.append({"theta_deg": float(theta), "rotation_protocol": "exact_degenerate_subspace_control",
                         "calculation": role, **result})
    for role in {str(row["calculation"]) for row in rows}:
        subset = [row for row in rows if row["calculation"] == role]
        values = [float(row["chi2_1550_pm_per_V"]) for row in subset]
        variation = 100.0 * (max(values) - min(values)) / max(abs(np.mean(values)), 1e-30)
        classification = ("strongly invariant" if variation < 1.0 else
                          "mildly sensitive" if variation < 5.0 else
                          "significant basis sensitivity" if variation <= 20.0 else
                          "severe basis/truncation sensitivity")
        for row in subset:
            row["chi2_1550_max_min_ratio"] = max(values) / max(min(values), 1e-30)
            row["chi2_1550_percent_variation"] = variation
            row["invariance_classification"] = classification
    return rows


def cancellation_pairs(term_rows: Sequence[Mapping[str, Any]], top: int = 10) -> list[dict[str, Any]]:
    electron = [row for row in term_rows if row["pathway"] == "electron-mediated"][:top]
    hh = [row for row in term_rows if row["pathway"] == "HH-mediated"]
    pairs = []
    for erow in electron:
        evalue = complex(float(erow["final_pm_per_V_real"]), float(erow["final_pm_per_V_imag"]))
        def score(hrow: Mapping[str, Any]) -> float:
            hvalue = complex(float(hrow["final_pm_per_V_real"]), float(hrow["final_pm_per_V_imag"]))
            magnitude = abs(math.log(max(abs(evalue), 1e-30) / max(abs(hvalue), 1e-30)))
            phase = abs(math.pi - abs(cmath.phase(evalue / hvalue))) / math.pi if abs(hvalue) else 1e6
            denom = abs(float(erow["denominator_1_real"]) - float(hrow["denominator_1_real"]))
            return magnitude + phase + denom
        hrow = min(hh, key=score)
        hvalue = complex(float(hrow["final_pm_per_V_real"]), float(hrow["final_pm_per_V_imag"]))
        residual = abs(evalue + hvalue)
        phase = math.degrees(abs(cmath.phase(evalue / hvalue))) if abs(hvalue) else float("nan")
        pairs.append({
            "electron_term_id": erow["term_id"], "hh_term_id": hrow["term_id"],
            "electron_abs": abs(evalue), "hh_abs": abs(hvalue),
            "magnitude_ratio": abs(evalue) / max(abs(hvalue), 1e-30),
            "phase_difference_deg": phase, "combined_residual": residual,
            "percent_cancellation": 100.0 * (1.0 - residual / max(abs(evalue) + abs(hvalue), 1e-30)),
            "electron_states": f"{erow['electron_state']}/{erow['hh_state']}/{erow['partner_state']}",
            "hh_states": f"{hrow['electron_state']}/{hrow['hh_state']}/{hrow['partner_state']}",
            "matching_basis": "magnitude + opposition phase + shared two-photon denominator",
        })
    return pairs


def diagnostic_branch_scale(electron: complex, hh: complex, e_factor: float, hh_factor: float) -> float:
    return float(abs(e_factor * electron + hh_factor * hh))

