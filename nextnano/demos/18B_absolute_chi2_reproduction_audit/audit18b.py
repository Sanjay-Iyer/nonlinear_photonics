"""Numerical and scientific audits for Demo 18B.

This module never launches nextnano++.  It consumes one completed raw tree and
keeps every convention visible in machine-readable records.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import cases18
import chi2 as production_chi2
import config18
import demo18
import eq16f
import outputs
import quantum1d


E_CHARGE_C = 1.602176634e-19
EPSILON_0_F_M = 8.8541878128e-12
HBAR_J_S = 1.054571817e-34
ELECTRON_MASS_KG = 9.1093837015e-31
HC_EV_NM = 1239.841984


class Audit18BError(RuntimeError):
    pass


@dataclass(frozen=True)
class SolvedData:
    electron: production_chi2.BandStates
    heavy_hole: production_chi2.BandStates
    electron_density: np.ndarray
    heavy_hole_density: np.ndarray
    band_position_nm: np.ndarray
    band_edges: Mapping[str, np.ndarray]
    raw_dir: Path


def _normalise_density(z: np.ndarray, density: np.ndarray) -> np.ndarray:
    columns = []
    for index in range(density.shape[1]):
        values = np.maximum(np.asarray(density[:, index], float), 0.0)
        norm = float(np.trapezoid(values, z))
        if not math.isfinite(norm) or norm <= 0:
            raise Audit18BError(f"state {index + 1} has invalid probability norm {norm}")
        columns.append(values / norm)
    return np.column_stack(columns)


def load_solved_data(solver_cfg: Mapping[str, Any], raw_dir: Path) -> SolvedData:
    """Load and physically order every available Gamma and HH state."""

    profile = outputs.load_profile(str(solver_cfg["nextnano"]["parser_profile"]))
    region = str(solver_cfg["nextnano"]["quantum_region_name"])
    raw_dir = Path(raw_dir)
    electron_run = quantum1d.parse_one_band_run(
        raw_dir,
        profile=profile,
        region_name=region,
        bandedge_columns=solver_cfg["nextnano"]["bandedge_columns"],
        dipole_polarizations=(str(solver_cfg["nextnano"]["dipole_polarization_name"]),),
    )
    if electron_run.envelopes is None:
        raise Audit18BError("Gamma envelope output is missing")
    resolved = outputs.resolve_outputs(
        profile,
        raw_dir,
        ["energy_spectrum_hh", "probabilities_hh", "envelopes_hh"],
        substitutions={"region": region},
    )
    outputs.require_or_diagnose(
        resolved, raw_dir,
        ["energy_spectrum_hh", "probabilities_hh", "envelopes_hh"],
        why="Demo 18B audits heavy-hole state identity and confinement",
    )
    _, h_energy = outputs.read_state_table(resolved.one("energy_spectrum_hh"))
    h_z, h_density = outputs.read_profile_table(resolved.one("probabilities_hh"))
    h_env_z, h_env = outputs.read_profile_table(resolved.one("envelopes_hh"))
    e_z = np.asarray(electron_run.state_position_nm, float)
    if not (
        h_z.shape == h_env_z.shape == e_z.shape
        and np.allclose(h_z, h_env_z)
        and np.allclose(h_z, e_z)
    ):
        raise Audit18BError("Gamma and HH probability/envelope grids do not match")

    e_count = min(
        electron_run.energies_eV.size,
        electron_run.envelopes.shape[1], electron_run.densities.shape[1],
    )
    h_count = min(h_energy.size, h_env.shape[1], h_density.shape[1])
    e_order = np.argsort(np.asarray(electron_run.energies_eV[:e_count], float))
    # On nextnano's common electron-energy scale the first physical HH state is
    # the highest energy.  The paper's HH1/HH2 therefore require descending sort.
    h_order = np.argsort(np.asarray(h_energy[:h_count], float))[::-1]
    electron = production_chi2.BandStates(
        e_z,
        np.asarray(electron_run.energies_eV[:e_count], float)[e_order],
        np.asarray(electron_run.envelopes[:, :e_count], float)[:, e_order],
        "electron",
    )
    heavy_hole = production_chi2.BandStates(
        h_z,
        np.asarray(h_energy[:h_count], float)[h_order],
        np.asarray(h_env[:, :h_count], float)[:, h_order],
        "heavy_hole",
    )
    return SolvedData(
        electron=electron,
        heavy_hole=heavy_hole,
        electron_density=_normalise_density(
            e_z, np.asarray(electron_run.densities[:, :e_count], float)[:, e_order]
        ),
        heavy_hole_density=_normalise_density(
            h_z, np.asarray(h_density[:, :h_count], float)[:, h_order]
        ),
        band_position_nm=np.asarray(electron_run.position_nm, float),
        band_edges={key: np.asarray(value, float) for key, value in electron_run.band_edges.items()},
        raw_dir=raw_dir,
    )


def _integral_on_interval(
    z: np.ndarray, values: np.ndarray, lo: float, hi: float
) -> float:
    mask = (z >= float(lo)) & (z <= float(hi))
    if np.count_nonzero(mask) < 2:
        return 0.0
    return float(np.trapezoid(values[mask], z[mask]))


def _outer_edge(
    data: SolvedData, key: str, active_start: float, active_end: float,
    quantum_start: float, quantum_end: float,
) -> tuple[float, float, float]:
    z = data.band_position_nm
    values = np.asarray(data.band_edges[key], float)
    left = values[(z >= quantum_start) & (z < active_start)]
    right = values[(z > active_end) & (z <= quantum_end)]
    if not left.size or not right.size:
        raise Audit18BError(f"cannot measure outer {key} edge in both padding regions")
    left_edge, right_edge = float(np.median(left)), float(np.median(right))
    # The least confining side is the strict barrier for each carrier type.
    strict = min(left_edge, right_edge) if key == "conduction_eV" else max(left_edge, right_edge)
    return left_edge, right_edge, strict


def state_audit(
    data: SolvedData,
    geometry: Any,
    quantum_padding_nm: float,
    criteria: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Classify all states and expose every input to the bound verdict."""

    active_start = float(geometry.active_start_nm)
    active_end = float(geometry.active_end_nm)
    q_start = max(float(geometry.domain_nm[0]), active_start - float(quantum_padding_nm))
    q_end = min(float(geometry.domain_nm[1]), active_end + float(quantum_padding_nm))
    boundary_window = float(criteria["boundary_window_nm"])
    rows: list[dict[str, Any]] = []
    for band_name, band, density, edge_key in (
        ("electron", data.electron, data.electron_density, "conduction_eV"),
        ("heavy_hole", data.heavy_hole, data.heavy_hole_density, "heavy_hole_eV"),
    ):
        left_edge, right_edge, strict_edge = _outer_edge(
            data, edge_key, active_start, active_end, q_start, q_end
        )
        for index in range(band.count):
            z = band.z_nm
            rho = density[:, index]
            psi = np.asarray(band.envelopes[:, index], float)
            energy = float(band.energies_eV[index])
            binding_eV = (
                strict_edge - energy if band_name == "electron" else energy - strict_edge
            )
            active = _integral_on_interval(z, rho, active_start, active_end)
            left_padding = _integral_on_interval(z, rho, q_start, active_start)
            right_padding = _integral_on_interval(z, rho, active_end, q_end)
            left_boundary = _integral_on_interval(
                z, rho, q_start, min(q_end, q_start + boundary_window)
            )
            right_boundary = _integral_on_interval(
                z, rho, max(q_start, q_end - boundary_window), q_end
            )
            # Amplitude at the grid points nearest the actual Dirichlet walls.
            # The separate probability metrics integrate a full boundary window;
            # taking the amplitude maximum over that same window would reach the
            # active well when the historical padding is only 2 nm and would no
            # longer measure the boundary condition.
            left_index = int(np.argmin(np.abs(z - q_start)))
            right_index = int(np.argmin(np.abs(z - q_end)))
            left_amp = float(abs(psi[left_index]))
            right_amp = float(abs(psi[right_index]))
            centroid = float(np.trapezoid(rho * z, z))
            rms = float(np.sqrt(np.trapezoid(rho * (z - centroid) ** 2, z)))
            checks = {
                "binding": binding_eV * 1000.0 >= float(criteria["minimum_binding_energy_meV"]),
                "active_probability": active >= float(criteria["minimum_active_region_probability"]),
                "left_boundary_probability": left_boundary <= float(
                    criteria["maximum_each_boundary_probability"]
                ),
                "right_boundary_probability": right_boundary <= float(
                    criteria["maximum_each_boundary_probability"]
                ),
                "left_boundary_amplitude": left_amp <= float(
                    criteria["maximum_each_boundary_amplitude_nm_minus_half"]
                ),
                "right_boundary_amplitude": right_amp <= float(
                    criteria["maximum_each_boundary_amplitude_nm_minus_half"]
                ),
            }
            rows.append({
                "band": band_name,
                "state": index + 1,
                "energy_eV": energy,
                "left_barrier_edge_eV": left_edge,
                "right_barrier_edge_eV": right_edge,
                "barrier_edge_eV": strict_edge,
                "binding_energy_meV": binding_eV * 1000.0,
                "bound_pass": all(checks.values()),
                "bound_checks": checks,
                "centroid_nm": centroid,
                "rms_width_nm": rms,
                "active_region_probability": active,
                "left_padding_probability": left_padding,
                "right_padding_probability": right_padding,
                "left_boundary_probability": left_boundary,
                "right_boundary_probability": right_boundary,
                "left_boundary_amplitude_nm_minus_half": left_amp,
                "right_boundary_amplitude_nm_minus_half": right_amp,
                "quantum_start_nm": q_start,
                "quantum_end_nm": q_end,
            })
    return rows


def first_bound_states(
    data: SolvedData, rows: Sequence[Mapping[str, Any]], count: int
) -> tuple[production_chi2.BandStates, production_chi2.BandStates, dict[str, Any]]:
    selected: dict[str, list[int]] = {}
    for band_name in ("electron", "heavy_hole"):
        selected[band_name] = [
            int(row["state"]) - 1 for row in rows
            if row["band"] == band_name and row["bound_pass"]
        ][:count]
    if any(len(selected[name]) < count for name in selected):
        raise Audit18BError(
            f"strict selection needs {count} bound states per band; found {selected}"
        )

    def subset(band: production_chi2.BandStates, indices: list[int], label: str):
        return production_chi2.BandStates(
            band.z_nm, band.energies_eV[indices], band.envelopes[:, indices], label
        )

    return (
        subset(data.electron, selected["electron"], "electron"),
        subset(data.heavy_hole, selected["heavy_hole"], "heavy_hole"),
        {key: [index + 1 for index in value] for key, value in selected.items()},
    )


def matrices(
    electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Independent trapezoidal overlap and z integrals."""

    if electron.z_nm.shape != heavy_hole.z_nm.shape or not np.allclose(
        electron.z_nm, heavy_hole.z_nm
    ):
        raise Audit18BError("electron and HH matrices require a common grid")
    z = electron.z_nm
    overlap = np.empty((electron.count, heavy_hole.count), float)
    z_e = np.empty((electron.count, electron.count), float)
    z_h = np.empty((heavy_hole.count, heavy_hole.count), float)
    for i in range(electron.count):
        for j in range(heavy_hole.count):
            overlap[i, j] = float(np.trapezoid(
                electron.envelopes[:, i] * heavy_hole.envelopes[:, j], z
            ))
        for j in range(electron.count):
            z_e[i, j] = float(np.trapezoid(
                electron.envelopes[:, i] * z * electron.envelopes[:, j], z
            ))
    for i in range(heavy_hole.count):
        for j in range(heavy_hole.count):
            z_h[i, j] = float(np.trapezoid(
                heavy_hole.envelopes[:, i] * z * heavy_hole.envelopes[:, j], z
            ))
    return overlap, z_e, z_h


def matrix_rows(
    case_id: str, electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
) -> list[dict[str, Any]]:
    overlap, z_e, z_h = matrices(electron, heavy_hole)
    rows: list[dict[str, Any]] = []
    for name, matrix, row_band, column_band, unit in (
        ("overlap", overlap, "electron", "heavy_hole", "dimensionless"),
        ("z", z_e, "electron", "electron", "nm"),
        ("z", z_h, "heavy_hole", "heavy_hole", "nm"),
    ):
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                rows.append({
                    "case_id": case_id, "quantity": name,
                    "row_band": row_band, "row_state": i + 1,
                    "column_band": column_band, "column_state": j + 1,
                    "value": float(matrix[i, j]), "absolute_value": float(abs(matrix[i, j])),
                    "unit": unit, "source": "python_trapezoidal_envelope_integral",
                })
    return rows


def _native_paths(raw_dir: Path) -> dict[str, Path]:
    patterns = {
        "overlap": "**/Gamma_HH/overlap_integrals_k00000.txt",
        "electron_z": "**/Gamma_Gamma/dipole_moment_matrix_elements_k00000_growth_z.txt",
        "heavy_hole_z": "**/HH_HH/dipole_moment_matrix_elements_k00000_growth_z.txt",
    }
    found: dict[str, Path] = {}
    for key, pattern in patterns.items():
        matches = sorted(Path(raw_dir).glob(pattern))
        if len(matches) != 1:
            raise Audit18BError(f"native {key} output matched {len(matches)} files")
        found[key] = matches[0]
    return found


def native_matrix_comparison(
    raw_dir: Path,
    electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compare only quantities whose nextnano definitions and units match.

    The solver's dipole table reports |e z_ij| in e*nm.  After factoring out
    the elementary charge this is |z_ij| in nm.  Diagonal rows are zero by the
    solver's transition-dipole convention and are deliberately not equated to
    origin-dependent <i|z|i>.  Overlap signs are phase-convention dependent, so
    magnitudes are compared.
    """

    overlap, z_e, z_h = matrices(electron, heavy_hole)
    paths = _native_paths(raw_dir)
    native_overlap = outputs.read_matrix_elements(paths["overlap"])
    overlap_column = next(
        key for key in next(iter(native_overlap.values()))
        if key.startswith("|<") and "^2" not in key
    )
    rows: list[dict[str, Any]] = []
    for (i, j), values in native_overlap.items():
        if i <= overlap.shape[0] and j <= overlap.shape[1]:
            py = float(abs(overlap[i - 1, j - 1]))
            nn = float(values[overlap_column])
            diff = abs(py - nn)
            rows.append({
                "quantity": "overlap_magnitude", "band": "electron_heavy_hole",
                "row_state": i, "column_state": j, "python_value": py,
                "nextnano_value": nn, "unit": "dimensionless",
                "absolute_difference": diff,
                "relative_difference": diff / max(abs(nn), 1.0e-30),
                "comparable": True,
                "definition": "absolute envelope overlap; sign excluded because eigenstate phase is arbitrary",
            })
    for key, matrix, band in (
        ("electron_z", z_e, "electron"), ("heavy_hole_z", z_h, "heavy_hole")
    ):
        path = paths[key]
        native = outputs.read_matrix_elements(path)
        column = outputs.magnitude_column(path, unit="e*nm")
        for (i, j), values in native.items():
            if i > matrix.shape[0] or j > matrix.shape[1]:
                continue
            py = float(abs(matrix[i - 1, j - 1]))
            nn = float(values[column])
            comparable = i != j
            diff = abs(py - nn) if comparable else None
            rows.append({
                "quantity": "position_magnitude", "band": band,
                "row_state": i, "column_state": j, "python_value": py,
                "nextnano_value": nn, "unit": "nm_after_factoring_out_e",
                "absolute_difference": diff,
                "relative_difference": (
                    diff / max(abs(nn), 1.0e-30) if comparable else None
                ),
                "comparable": comparable,
                "definition": (
                    "off-diagonal |<i|z|j>|" if comparable else
                    "not comparable: nextnano transition-dipole diagonal is zero, Python <i|z|i> is origin dependent"
                ),
            })
    comparable = [row for row in rows if row["comparable"]]
    return rows, {
        "paths": {key: str(value) for key, value in paths.items()},
        "overlap_definition": "nextnano |<Gamma_i|HH_j>|, dimensionless",
        "dipole_definition": "nextnano |<i|eps.d|j>| in e*nm; e factored out gives nm",
        "diagonal_dipoles_comparable": False,
        "max_absolute_overlap_difference": max(
            (row["absolute_difference"] for row in comparable if row["quantity"] == "overlap_magnitude"),
            default=None,
        ),
        "max_absolute_dipole_difference_nm": max(
            (row["absolute_difference"] for row in comparable if row["quantity"] == "position_magnitude"),
            default=None,
        ),
    }


def primary_settings(cfg: Mapping[str, Any], *, states: int = 2) -> production_chi2.Chi2Settings:
    chi = cfg["chi2"]
    return production_chi2.Chi2Settings(
        mode="absolute",
        broadening_meV=float(chi["broadening_meV"]),
        # Shared production defines the edge as pi/a; 0.20*pi/a is 0.10*2pi/a.
        k_parallel_fraction_of_bz=0.20,
        k_parallel_points=int(chi["primary_k_points"]),
        lattice_constant_nm=float(chi["lattice_constant_nm"]),
        electron_mass_m0=float(chi["electron_mass_m0"]),
        heavy_hole_inplane_mass_m0=float(chi["heavy_hole_inplane_mass_m0"]),
        spin_degeneracy=int(chi["primary_spin_degeneracy"]),
        max_states_per_band=int(states),
        r_e_hh_nm=float(chi["r_e_hh_nm"]),
        n_wells_per_metre=2.0 / (30.0e-9),
    )


def independent_prefactor(settings: production_chi2.Chi2Settings) -> float:
    r_m = float(settings.r_e_hh_nm) * 1.0e-9
    return (
        float(settings.n_wells_per_metre) * E_CHARGE_C**3 * r_m**2
        / (6.0 * EPSILON_0_F_M)
        * 1.0e-9 * 1.0e18 / E_CHARGE_C**2 * 1.0e12
    )


def _independent_grid(settings: production_chi2.Chi2Settings) -> tuple[np.ndarray, np.ndarray]:
    kmax = float(settings.k_parallel_fraction_of_bz) * math.pi / float(
        settings.lattice_constant_nm
    )
    k = np.linspace(0.0, kmax, int(settings.k_parallel_points))
    step = k[1] - k[0]
    trapezoid = np.full(k.size, step)
    trapezoid[[0, -1]] *= 0.5
    weights = (
        k / (2.0 * math.pi) * trapezoid * float(settings.spin_degeneracy)
    )
    return k, weights


def _transition_grid(
    electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
    k_per_nm: np.ndarray,
    settings: production_chi2.Chi2Settings,
) -> np.ndarray:
    inverse_mass = 1.0 / float(settings.electron_mass_m0) + 1.0 / float(
        settings.heavy_hole_inplane_mass_m0
    )
    reduced_mass = ELECTRON_MASS_KG / inverse_mass
    kinetic = HBAR_J_S**2 * (k_per_nm * 1.0e9) ** 2 / (2.0 * reduced_mass) / E_CHARGE_C
    zero = electron.energies_eV[:, None] - heavy_hole.energies_eV[None, :]
    return zero[:, :, None] + kinetic[None, None, :]


def independent_eq2(
    electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
    photon_energy_eV: float,
    settings: production_chi2.Chi2Settings,
    *,
    decompose: bool = False,
) -> tuple[complex, list[dict[str, Any]], dict[str, complex]]:
    """A from-scratch energy-form Eq. 2 sum, independent of chi2_spectrum."""

    count = int(settings.max_states_per_band)
    if electron.count < count or heavy_hole.count < count:
        raise Audit18BError(f"independent Eq. 2 needs {count} states per band")
    electron = production_chi2.BandStates(
        electron.z_nm, electron.energies_eV[:count], electron.envelopes[:, :count], "e"
    )
    heavy_hole = production_chi2.BandStates(
        heavy_hole.z_nm, heavy_hole.energies_eV[:count],
        heavy_hole.envelopes[:, :count], "hh"
    )
    overlap, z_e, z_h = matrices(electron, heavy_hole)
    k, weights = _independent_grid(settings)
    transitions = _transition_grid(electron, heavy_hole, k, settings)
    gamma = float(settings.broadening_meV) * 1.0e-3
    hw = float(photon_energy_eV)
    prefactor = independent_prefactor(settings)
    total = 0.0j
    electron_total = 0.0j
    hole_total = 0.0j
    rows: list[dict[str, Any]] = []
    for m in range(count):
        for n in range(count):
            first = transitions[n, m] - 2.0 * hw + 1j * gamma
            for path, partners in (("electron", range(count)), ("heavy_hole", range(count))):
                for l in partners:
                    if path == "electron":
                        overlap_product = overlap[n, m] * overlap[l, m]
                        z_value = z_e[n, l]
                        numerator = overlap_product * z_value
                        second = transitions[l, m] - hw + 1j * gamma
                        sign = 1.0
                    else:
                        overlap_product = overlap[n, m] * overlap[n, l]
                        z_value = z_h[m, l]
                        numerator = overlap_product * z_value
                        second = transitions[n, l] - hw + 1j * gamma
                        sign = -1.0
                    integrand = sign * numerator / (first * second)
                    integrated = complex(np.dot(weights, integrand))
                    contribution = prefactor * integrated
                    total += contribution
                    if path == "electron":
                        electron_total += contribution
                    else:
                        hole_total += contribution
                    if decompose:
                        rows.append({
                            "path": path, "m_hh_state": m + 1,
                            "n_electron_state": n + 1, "l_partner_state": l + 1,
                            "z_kind": "diagonal" if (
                                (path == "electron" and n == l)
                                or (path == "heavy_hole" and m == l)
                            ) else "off_diagonal",
                            "overlap_product": float(overlap_product),
                            "z_matrix_element_nm": float(z_value),
                            "numerator_nm": float(numerator), "sign": sign,
                            "first_denominator_k0_eV_real": float(first[0].real),
                            "first_denominator_k0_eV_imag": float(first[0].imag),
                            "second_denominator_k0_eV_real": float(second[0].real),
                            "second_denominator_k0_eV_imag": float(second[0].imag),
                            "integrated_term_before_prefactor_real": integrated.real,
                            "integrated_term_before_prefactor_imag": integrated.imag,
                            "contribution_pm_per_V_real": contribution.real,
                            "contribution_pm_per_V_imag": contribution.imag,
                            "contribution_pm_per_V_magnitude": abs(contribution),
                        })
    rows.sort(key=lambda row: float(row["contribution_pm_per_V_magnitude"]), reverse=True)
    for rank, row in enumerate(rows, 1):
        row["magnitude_rank"] = rank
    return total, rows, {"electron": electron_total, "heavy_hole": hole_total}


def eq2_cross_check(
    electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
    settings: production_chi2.Chi2Settings,
    target_wavelength_nm: float,
) -> dict[str, Any]:
    hw = HC_EV_NM / float(target_wavelength_nm)
    independent, terms, parts = independent_eq2(
        electron, heavy_hole, hw, settings, decompose=True
    )
    production = production_chi2.chi2_spectrum(
        electron, heavy_hole, [hw], settings
    )
    prod = complex(production.chi2[0])
    residual = abs(independent - prod) / max(abs(prod), 1.0e-30)
    checks: list[dict[str, Any]] = []
    for points, label in ((8, "small_artificial_grid"), (settings.k_parallel_points, "full_grid")):
        probe = production_chi2.Chi2Settings(
            mode="absolute", broadening_meV=settings.broadening_meV,
            k_parallel_fraction_of_bz=settings.k_parallel_fraction_of_bz,
            k_parallel_points=int(points), lattice_constant_nm=settings.lattice_constant_nm,
            electron_mass_m0=settings.electron_mass_m0,
            heavy_hole_inplane_mass_m0=settings.heavy_hole_inplane_mass_m0,
            spin_degeneracy=settings.spin_degeneracy,
            max_states_per_band=settings.max_states_per_band,
            r_e_hh_nm=settings.r_e_hh_nm,
            n_wells_per_metre=settings.n_wells_per_metre,
        )
        ind, _, _ = independent_eq2(electron, heavy_hole, hw, probe)
        prod_probe = complex(production_chi2.chi2_spectrum(
            electron, heavy_hole, [hw], probe
        ).chi2[0])
        checks.append({
            "grid": label, "k_points": int(points),
            "production_real": prod_probe.real, "production_imag": prod_probe.imag,
            "independent_real": ind.real, "independent_imag": ind.imag,
            "relative_difference": abs(ind - prod_probe) / max(abs(prod_probe), 1.0e-30),
        })
    # A one-k state-sum comparison excludes quadrature because radial k=0 has zero weight.
    overlap, z_e, z_h = matrices(electron, heavy_hole)
    transition0 = electron.energies_eV[:2, None] - heavy_hole.energies_eV[None, :2]
    gamma = settings.broadening_meV * 1.0e-3
    one_k_sum = 0.0j
    for m in range(2):
        for n in range(2):
            first = transition0[n, m] - 2 * hw + 1j * gamma
            for l in range(2):
                one_k_sum += overlap[n, m] * z_e[n, l] * overlap[l, m] / (
                    first * (transition0[l, m] - hw + 1j * gamma)
                )
                one_k_sum -= overlap[n, m] * z_h[m, l] * overlap[n, l] / (
                    first * (transition0[n, l] - hw + 1j * gamma)
                )
    one_k_control = eq16f.eq2_state_sum(
        eq16f.StateSet(
            electron_energies_eV=np.asarray(electron.energies_eV[:2], float),
            hole_energies_eV=np.asarray(heavy_hole.energies_eV[:2], float),
            overlap_eh=overlap, z_e_nm=z_e, z_h_nm=z_h,
            r_e_hh_nm=float(settings.r_e_hh_nm),
        ),
        hw, broadening_eV=gamma,
    )
    return {
        "production_chi2": prod,
        "independent_chi2": independent,
        "relative_difference": residual,
        "grid_checks": checks,
        "single_k0_state_sum_nm_per_eV2": one_k_sum,
        "single_k0_control_state_sum_nm_per_eV2": one_k_control,
        "single_k0_relative_difference": abs(one_k_sum - one_k_control)
        / max(abs(one_k_control), 1.0e-30),
        "term_rows": terms,
        "electron_contribution": parts["electron"],
        "heavy_hole_contribution": parts["heavy_hole"],
        "cancellation_factor": (
            (abs(parts["electron"]) + abs(parts["heavy_hole"])) / max(abs(independent), 1e-30)
        ),
        "prefactor_production": float(production.scale_factor),
        "prefactor_independent": independent_prefactor(settings),
    }


def optical_summary(
    cfg: Mapping[str, Any],
    electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
    *,
    states: int = 2,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    settings = primary_settings(cfg, states=states)
    wavelengths = np.linspace(
        float(cfg["chi2"]["wavelength_start_nm"]),
        float(cfg["chi2"]["wavelength_stop_nm"]),
        int(cfg["chi2"]["wavelength_points"]),
    )
    result = production_chi2.chi2_spectrum(
        electron, heavy_hole, HC_EV_NM / wavelengths, settings, max_states=states
    )
    target = production_chi2.chi2_spectrum(
        electron, heavy_hole,
        [HC_EV_NM / float(cfg["chi2"]["target_wavelength_nm"])],
        settings, max_states=states,
    )
    index = int(np.argmax(np.abs(result.chi2)))
    row = {
        "states_per_band": states,
        "chi2_1550_real_pm_per_V": float(target.chi2[0].real),
        "chi2_1550_imag_pm_per_V": float(target.chi2[0].imag),
        "chi2_1550_pm_per_V": float(abs(target.chi2[0])),
        "peak_chi2_pm_per_V": float(abs(result.chi2[index])),
        "peak_wavelength_nm": float(wavelengths[index]),
        "prefactor": float(result.scale_factor),
        "nz_convention": "two_wells_per_period",
        "nz_per_metre": float(settings.n_wells_per_metre),
        "kmax_convention": "0.1_times_2pi_over_a",
        "kmax_per_nm": float(settings.k_max_per_nm),
        "k_points": int(settings.k_parallel_points),
        "spin_degeneracy": int(settings.spin_degeneracy),
        "r_e_hh_nm": float(settings.r_e_hh_nm),
        "broadening_meV": float(settings.broadening_meV),
    }
    return row, wavelengths, np.asarray(result.chi2, complex)


def localization_rows(
    case_id: str, data: SolvedData, geometry: Any
) -> list[dict[str, Any]]:
    z = data.electron.z_nm
    a0 = float(geometry.active_start_nm)
    a1 = a0 + float(geometry.thick_well_nm)
    a2 = a1 + float(geometry.barrier_nm)
    a3 = float(geometry.active_end_nm)
    rows: list[dict[str, Any]] = []
    for band_name, band, density in (
        ("electron", data.electron, data.electron_density),
        ("heavy_hole", data.heavy_hole, data.heavy_hole_density),
    ):
        for index in range(band.count):
            rho = density[:, index]
            left = _integral_on_interval(z, rho, a0, a1)
            barrier = _integral_on_interval(z, rho, a1, a2)
            right = _integral_on_interval(z, rho, a2, a3)
            centroid = float(np.trapezoid(rho * z, z))
            normalization_check = float(np.trapezoid(rho, z))
            rows.append({
                "case_id": case_id, "band": band_name, "state": index + 1,
                "energy_eV": float(band.energies_eV[index]),
                "centroid_nm": centroid, "left_well_probability": left,
                "central_barrier_probability": barrier,
                "right_well_probability": right,
                "outside_active_probability": max(0.0, 1.0 - left - barrier - right),
                "localization_left_minus_right": left - right,
                "node_count": int(np.count_nonzero(
                    np.diff(np.signbit(band.envelopes[:, index]))
                )),
                "character": (
                    "left_localized" if left - right > 0.25 else
                    "right_localized" if right - left > 0.25 else
                    "delocalized_bonding_or_antibonding"
                ),
                "normalization_check": normalization_check,
            })
    return rows


def origin_audit(
    cfg: Mapping[str, Any], electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
) -> list[dict[str, Any]]:
    settings = primary_settings(cfg)
    hw = HC_EV_NM / float(cfg["chi2"]["target_wavelength_nm"])
    tolerance = float(cfg["convergence_tolerances"]["origin_relative"])
    rows = []
    for shift in cfg["diagnostics"]["origin_shifts_nm"]:
        check = production_chi2.origin_independence(
            electron, heavy_hole, [hw], settings,
            shift_nm=float(shift), relative_tolerance=tolerance,
        )
        rows.append({
            "shift_nm": float(shift), "absolute_residual_pm_per_V": check.absolute_residual,
            "relative_residual": check.relative_residual,
            "tolerance": tolerance, "passed": bool(check.passed),
        })
    return rows


def state_count_audit(
    cfg: Mapping[str, Any], electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
    state_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for count in cfg["diagnostics"]["state_counts"]:
        count = int(count)
        selected_e, selected_h = electron, heavy_hole
        selected_record: dict[str, Any] | None = None
        if state_rows is not None:
            data = SolvedData(
                electron, heavy_hole,
                np.column_stack([electron.envelopes[:, i] ** 2 for i in range(electron.count)]),
                np.column_stack([heavy_hole.envelopes[:, i] ** 2 for i in range(heavy_hole.count)]),
                electron.z_nm, {}, Path("state_count_selection"),
            )
            try:
                selected_e, selected_h, selected_record = first_bound_states(
                    data, state_rows, count
                )
            except Audit18BError as exc:
                rows.append({
                    "states_per_band": count, "available": False,
                    "reason": str(exc), "role": "diagnostic_extension_only",
                })
                continue
        if selected_e.count < count or selected_h.count < count:
            rows.append({
                "states_per_band": count, "available": False,
                "reason": f"available electron={selected_e.count}, HH={selected_h.count}",
            })
            continue
        row, _, _ = optical_summary(cfg, selected_e, selected_h, states=count)
        rows.append({**row, "available": True, "role": (
            "paper_primary" if count == 2 else "diagnostic_extension_only"
        ), "selected_bound_states": selected_record})
    baseline = next(
        (row for row in rows if row.get("available") and row["states_per_band"] == 2), None
    )
    if baseline:
        for row in rows:
            if row.get("available"):
                row["ratio_to_two_state"] = row["chi2_1550_pm_per_V"] / max(
                    baseline["chi2_1550_pm_per_V"], 1.0e-30
                )
    return rows


def r_ehh_audit(cfg: Mapping[str, Any], reproduced_chi2: float) -> dict[str, Any]:
    target = float(cfg["diagnostics"]["paper_target_pm_per_V"])
    current = float(cfg["chi2"]["r_e_hh_nm"])
    chi_factor = target / float(reproduced_chi2)
    r_factor = math.sqrt(chi_factor)
    return {
        "paper_2026_published_numeric_r_e_hh": None,
        "paper_2026_method": "VASP with HSE06 hybrid orbitals",
        "repository_assumed_r_e_hh_nm": current,
        "repository_provenance": (
            "Ramesh et al., Applied Physics Letters 123, 251111 (2023), "
            "VASP/HSE06; repository physics14.py records 0.751 nm"
        ),
        "comparison_chi2_pm_per_V": float(reproduced_chi2),
        "paper_target_pm_per_V": target,
        "required_chi2_factor": chi_factor,
        "required_r_factor": r_factor,
        "hypothetical_fitted_r_e_hh_nm": current * r_factor,
        "classification": "fitted_hypothetical_not_a_paper_value",
        "plausibility": (
            "not remotely plausible as a GaAs unit-cell position matrix element"
            if current * r_factor > 2.0 else "requires independent first-principles verification"
        ),
    }


def convention_audit(
    cfg: Mapping[str, Any], electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
) -> list[dict[str, Any]]:
    base = cases18.ScaleCase(
        "reference", "reference", "two_wells_per_period", "bz_2pi_over_a",
        int(cfg["chi2"]["primary_k_points"]), int(cfg["chi2"]["primary_spin_degeneracy"]),
    )
    cfg18 = config18.load_config()
    cfg18["chi2"].update({key: cfg["chi2"][key] for key in (
        "broadening_meV", "r_e_hh_nm", "wavelength_start_nm", "wavelength_stop_nm",
        "wavelength_points", "target_wavelength_nm", "lattice_constant_nm",
        "electron_mass_m0", "heavy_hole_inplane_mass_m0",
    )})
    cases = (
        cases18.ScaleCase("legacy", "legacy", "pair_per_period", "legacy_pi_over_a", 384, 2),
        cases18.ScaleCase("paper_nz", "paper Nz", "two_wells_per_period", "legacy_pi_over_a", 384, 2),
        base,
        cases18.ScaleCase("spin1", "spin 1", "two_wells_per_period", "bz_2pi_over_a", 384, 1),
    )
    rows = [demo18.evaluate_case(
        cfg18, case, electron, heavy_hole,
        np.asarray([float(cfg["chi2"]["target_wavelength_nm"])])
    ).row for case in cases]
    reference = next(row for row in rows if row["case_id"] == "reference")
    for row in rows:
        row["ratio_to_reference"] = row["chi2_at_1550_pm_per_V"] / max(
            reference["chi2_at_1550_pm_per_V"], 1e-30
        )
        row.pop("Nz_convention", None)  # unique, case-safe CSV headers
    return rows


def k_saturation_audit(
    cfg: Mapping[str, Any], electron: production_chi2.BandStates,
    heavy_hole: production_chi2.BandStates,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    hw = HC_EV_NM / float(cfg["chi2"]["target_wavelength_nm"])
    for fraction in cfg["diagnostics"]["kmax_fractions_of_2pi_over_a"]:
        settings = primary_settings(cfg)
        settings = production_chi2.Chi2Settings(
            mode="absolute", broadening_meV=settings.broadening_meV,
            k_parallel_fraction_of_bz=2.0 * float(fraction),
            k_parallel_points=int(cfg["diagnostics"]["k_points"]),
            lattice_constant_nm=settings.lattice_constant_nm,
            electron_mass_m0=settings.electron_mass_m0,
            heavy_hole_inplane_mass_m0=settings.heavy_hole_inplane_mass_m0,
            spin_degeneracy=settings.spin_degeneracy,
            max_states_per_band=2, r_e_hh_nm=settings.r_e_hh_nm,
            n_wells_per_metre=settings.n_wells_per_metre,
        )
        value = complex(production_chi2.chi2_spectrum(
            electron, heavy_hole, [hw], settings
        ).chi2[0])
        rows.append({
            "fraction_of_2pi_over_a": float(fraction),
            "kmax_per_nm": float(settings.k_max_per_nm),
            "k_points": int(settings.k_parallel_points),
            "chi2_1550_real_pm_per_V": value.real,
            "chi2_1550_imag_pm_per_V": value.imag,
            "chi2_1550_pm_per_V": abs(value),
            "role": "paper_limit" if abs(float(fraction) - 0.10) < 1e-12 else "diagnostic_only",
        })
    final = rows[-1]["chi2_1550_pm_per_V"]
    for index, row in enumerate(rows):
        row["relative_to_largest_cutoff"] = row["chi2_1550_pm_per_V"] / max(final, 1e-30)
        row["incremental_relative_change"] = (
            None if index == 0 else
            abs(row["chi2_1550_pm_per_V"] - rows[index - 1]["chi2_1550_pm_per_V"])
            / max(abs(row["chi2_1550_pm_per_V"]), 1e-30)
        )

    # Independently refine the radial grid at the largest diagnostic cutoff.
    final_fraction = float(rows[-1]["fraction_of_2pi_over_a"])
    base = primary_settings(cfg)
    refined_settings = production_chi2.Chi2Settings(
        mode="absolute", broadening_meV=base.broadening_meV,
        k_parallel_fraction_of_bz=2.0 * final_fraction,
        k_parallel_points=2 * int(cfg["diagnostics"]["k_points"]),
        lattice_constant_nm=base.lattice_constant_nm,
        electron_mass_m0=base.electron_mass_m0,
        heavy_hole_inplane_mass_m0=base.heavy_hole_inplane_mass_m0,
        spin_degeneracy=base.spin_degeneracy,
        max_states_per_band=2, r_e_hh_nm=base.r_e_hh_nm,
        n_wells_per_metre=base.n_wells_per_metre,
    )
    refined = complex(production_chi2.chi2_spectrum(
        electron, heavy_hole, [hw], refined_settings
    ).chi2[0])
    rows[-1]["grid_refinement_points"] = int(refined_settings.k_parallel_points)
    rows[-1]["grid_refinement_chi2_1550_pm_per_V"] = abs(refined)
    rows[-1]["grid_refinement_relative_change"] = abs(abs(refined) - final) / max(
        abs(refined), 1e-30
    )
    return rows


def degeneracy_ledger() -> list[dict[str, Any]]:
    return [
        {"factor": "electron_spin", "value": 2, "included": True,
         "location": "radial k weights", "status": "explicit convention"},
        {"factor": "kx_ky_angular_integral", "value": "2*pi",
         "included": True, "location": "d2k/(2*pi)^2 -> k dk/(2*pi)",
         "status": "isotropic radial reduction"},
        {"factor": "positive_negative_k", "value": "full plane",
         "included": True, "location": "angular integral around radial k>=0",
         "status": "not an extra factor of two"},
        {"factor": "heavy_hole_mj", "value": 2, "included": False,
         "location": "nowhere", "status": "paper does not state whether r_e_hh/Nz sum includes both branches"},
        {"factor": "quantum_well_density", "value": "2/(30 nm)", "included": True,
         "location": "Nz prefactor", "status": "literal paper wording: wells per unit length"},
        {"factor": "eq2_prefactor", "value": "1/6", "included": True,
         "location": "absolute prefactor", "status": "Eq. 2 as printed; Eq. 1 has open factor-of-3 discrepancy"},
        {"factor": "tensor_input_permutation", "value": 1, "included": True,
         "location": "chi_xzx only", "status": "chi_xzx != chi_xxz; no silent permutation factor"},
        {"factor": "chi_vs_d", "value": 1, "included": True,
         "location": "reported quantity is chi_xzx", "status": "not d=chi/2 and not d_eff"},
    ]


def analyze_case(
    cfg: Mapping[str, Any], case_id: str, data: SolvedData, geometry: Any,
    quantum_padding_nm: float,
) -> dict[str, Any]:
    audits = state_audit(
        data, geometry, quantum_padding_nm, cfg["bound_state_criteria"]
    )
    participating = [
        row for row in audits if row["state"] <= 2 and row["band"] in ("electron", "heavy_hole")
    ]
    strict_all_four = len(participating) == 4 and all(row["bound_pass"] for row in participating)
    try:
        selected_e, selected_h, selected = first_bound_states(data, audits, 2)
        selection_status = "first_two_strictly_bound_states"
    except Audit18BError as exc:
        # Preserve and diagnose the historical first-two-eigenstate calculation,
        # but never label it the paper reproduction.
        selected_e = production_chi2.BandStates(
            data.electron.z_nm, data.electron.energies_eV[:2], data.electron.envelopes[:, :2], "e"
        )
        selected_h = production_chi2.BandStates(
            data.heavy_hole.z_nm, data.heavy_hole.energies_eV[:2],
            data.heavy_hole.envelopes[:, :2], "hh"
        )
        selected = {"electron": [1, 2], "heavy_hole": [1, 2]}
        selection_status = f"fallback_first_two_eigenstates_not_certified: {exc}"
    optical, wavelengths, spectrum = optical_summary(cfg, selected_e, selected_h)
    overlap, z_e, z_h = matrices(selected_e, selected_h)
    energies = {
        "e1_eV": float(selected_e.energies_eV[0]),
        "e2_eV": float(selected_e.energies_eV[1]),
        "hh1_eV": float(selected_h.energies_eV[0]),
        "hh2_eV": float(selected_h.energies_eV[1]),
    }
    transitions = {
        f"transition_e{i+1}_hh{j+1}_eV": float(
            selected_e.energies_eV[i] - selected_h.energies_eV[j]
        )
        for i in range(2) for j in range(2)
    }
    row = {
        "case_id": case_id, **energies, **transitions,
        "overlap_e1_hh1": float(overlap[0, 0]),
        "overlap_e1_hh2": float(overlap[0, 1]),
        "overlap_e2_hh1": float(overlap[1, 0]),
        "overlap_e2_hh2": float(overlap[1, 1]),
        "z_e11_nm": float(z_e[0, 0]), "z_e12_nm": float(z_e[0, 1]),
        "z_e21_nm": float(z_e[1, 0]), "z_e22_nm": float(z_e[1, 1]),
        "z_hh11_nm": float(z_h[0, 0]), "z_hh12_nm": float(z_h[0, 1]),
        "z_hh21_nm": float(z_h[1, 0]), "z_hh22_nm": float(z_h[1, 1]),
        "delta_z_e_nm": float(z_e[1, 1] - z_e[0, 0]),
        "delta_z_hh_nm": float(z_h[1, 1] - z_h[0, 0]),
        **optical,
        "strict_first_two_bound_pass": strict_all_four,
        "strict_selected_states_bound_pass": selection_status == "first_two_strictly_bound_states",
        "state_selection": selection_status,
        "selected_electron_states": selected["electron"],
        "selected_heavy_hole_states": selected["heavy_hole"],
        "electron_orthonormality_error": selected_e.orthonormality_error(),
        "heavy_hole_orthonormality_error": selected_h.orthonormality_error(),
    }
    return {
        "row": row, "state_audit": audits,
        "localization": localization_rows(case_id, data, geometry),
        "matrix_rows": matrix_rows(case_id, data.electron, data.heavy_hole),
        "electron": selected_e, "heavy_hole": selected_h,
        "wavelength_nm": wavelengths, "chi2": spectrum,
        "data": data, "geometry": geometry,
    }


def convergence_rows(
    analyses: Mapping[str, Mapping[str, Any]], case_ids: Sequence[str],
    *, reference_case: str,
) -> list[dict[str, Any]]:
    reference = analyses[reference_case]["row"]
    rows: list[dict[str, Any]] = []
    relative_fields = (
        "z_e11_nm", "z_e12_nm", "z_e21_nm", "z_e22_nm",
        "z_hh11_nm", "z_hh12_nm", "z_hh21_nm", "z_hh22_nm",
        "delta_z_e_nm", "delta_z_hh_nm", "chi2_1550_pm_per_V", "peak_chi2_pm_per_V",
    )
    absolute_fields = (
        "e1_eV", "e2_eV", "hh1_eV", "hh2_eV",
        "transition_e1_hh1_eV", "transition_e1_hh2_eV",
        "transition_e2_hh1_eV", "transition_e2_hh2_eV",
        "overlap_e1_hh1", "overlap_e1_hh2", "overlap_e2_hh1", "overlap_e2_hh2",
        "peak_wavelength_nm",
    )
    for case_id in case_ids:
        source = analyses[case_id]["row"]
        row = dict(source)
        row["convergence_reference_case"] = reference_case
        for field in relative_fields:
            row[f"{field}_relative_change"] = abs(
                float(source[field]) - float(reference[field])
            ) / max(abs(float(reference[field])), 1.0e-30)
        for field in absolute_fields:
            row[f"{field}_absolute_change"] = abs(
                float(source[field]) - float(reference[field])
            )
        rows.append(row)
    return rows


def convergence_verdict(
    rows: Sequence[Mapping[str, Any]], tolerances: Mapping[str, Any]
) -> dict[str, Any]:
    non_reference = list(rows[:-1]) if len(rows) > 1 else list(rows)
    latest = non_reference[-1] if non_reference else rows[-1]
    energy_fields = ("e1_eV", "e2_eV", "hh1_eV", "hh2_eV")
    matrix_fields = (
        "z_e12_nm", "z_hh12_nm", "delta_z_e_nm", "delta_z_hh_nm",
    )
    overlap_fields = (
        "overlap_e1_hh1", "overlap_e1_hh2", "overlap_e2_hh1", "overlap_e2_hh2",
    )
    checks = {
        "energies": max(latest[f"{field}_absolute_change"] * 1000.0 for field in energy_fields)
        <= float(tolerances["energy_meV"]),
        "matrices": max(latest[f"{field}_relative_change"] for field in matrix_fields)
        <= float(tolerances["matrix_relative"]),
        "overlaps": max(latest[f"{field}_absolute_change"] for field in overlap_fields)
        <= float(tolerances["overlap_absolute"]),
        "chi2": latest["chi2_1550_pm_per_V_relative_change"]
        <= float(tolerances["chi2_relative"]),
        "peak_wavelength": latest["peak_wavelength_nm_absolute_change"]
        <= float(tolerances["peak_wavelength_nm"]),
    }
    return {"passed": all(checks.values()), "checks": checks, "comparison_row": latest}


def classify(
    *, bound_pass: bool, domain_converged: bool, mesh_converged: bool,
    k_converged: bool, native_pass: bool, independent_pass: bool, best_chi2: float,
    paper_target: float,
) -> dict[str, str]:
    if not bound_pass or not domain_converged or not mesh_converged or not k_converged:
        category = "A"
        diagnosis = (
            "A numerical convergence or state-selection problem remains; inspect the "
            "bound-state, domain, mesh, and k-space verdicts."
        )
    elif not native_pass or not independent_pass:
        category = "B"
        diagnosis = "Matrix extraction or Eq. 2 implementation failed independent validation."
    elif best_chi2 >= 0.5 * paper_target:
        category = "E"
        diagnosis = "Reproduction approaches the paper scale without an empirical fit."
    else:
        category = "C"
        diagnosis = (
            "Numerics and implementation are internally consistent, while the paper's "
            "numerical HSE06 r_e_hh, heavy-hole multiplicity, and Schrödinger-Poisson "
            "charge/boundary setup remain unpublished or unresolved."
        )
    return {"category": category, "primary_diagnosis": diagnosis}


def poisson_audit() -> dict[str, Any]:
    return {
        "current_deck_setting": "no_density = yes",
        "current_equation": "one-band Schrodinger eigenproblem without carrier-density feedback",
        "paper_statement": "envelopes determined using Schrodinger-Poisson methods with Nextnano",
        "missing_from_paper": [
            "doping profile", "carrier density or quasi-Fermi level",
            "electrostatic boundary conditions", "fixed/interface charge",
        ],
        "licensed_comparison_run": False,
        "reason": (
            "A nontrivial Poisson solution cannot be reproduced uniquely without charge and "
            "boundary data. An undoped zero-charge Poisson solve would be physically equivalent "
            "to the present flat electrostatic solution and would not test the paper's unknown setup."
        ),
        "status": "scientifically_underdetermined_not_fabricated",
    }
