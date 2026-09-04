"""Generalized k-resolved adapter around the validated Demo 20 Eq. 2 algebra."""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np


DEMO_DIR = Path(__file__).resolve().parent
DEMO20 = DEMO_DIR.parent / "20_quantum_well_interface_grading_scaled"
if str(DEMO20) not in sys.path:
    sys.path.insert(0, str(DEMO20))
import s06_chi2 as validated  # noqa: E402


@dataclass(frozen=True)
class KResolvedSpectrum:
    wavelength_nm: np.ndarray
    chi2: np.ndarray
    terms: np.ndarray
    term_labels: tuple[str, ...]
    summed_integrand: np.ndarray
    k_weights: np.ndarray


def radial_weights(k_per_nm: np.ndarray, spin_degeneracy: int = 2) -> np.ndarray:
    k = np.asarray(k_per_nm, dtype=float)
    if k.ndim != 1 or len(k) < 2 or np.any(np.diff(k) <= 0) or k[0] < 0:
        raise ValueError("k must be a strictly increasing nonnegative radial grid")
    # Nonuniform trapezoid integration of g_s*k/(2pi) f(k).
    xweight = np.empty_like(k)
    xweight[0] = 0.5 * (k[1] - k[0])
    xweight[-1] = 0.5 * (k[-1] - k[-2])
    xweight[1:-1] = 0.5 * (k[2:] - k[:-2])
    return int(spin_degeneracy) * k / (2.0 * math.pi) * xweight


def _as_k_matrix(value: np.ndarray, shape: tuple[int, int], nk: int) -> np.ndarray:
    array = np.asarray(value, dtype=complex)
    if array.shape == shape:
        return np.repeat(array[:, :, None], nk, axis=2)
    if array.shape == (*shape, nk):
        return array
    raise ValueError(f"matrix must have shape {shape} or {(*shape, nk)}, got {array.shape}")


def chi2_from_k_inputs(
    wavelengths_nm: np.ndarray,
    k_per_nm: np.ndarray,
    electron_energies_eV: np.ndarray,
    hole_energies_eV: np.ndarray,
    overlap_eh: np.ndarray,
    z_e_nm: np.ndarray,
    z_h_nm: np.ndarray,
    *,
    broadening_meV: float = 5.0,
    settings: validated.Chi2Settings | None = None,
) -> KResolvedSpectrum:
    """Evaluate the validated 16 pathways with energy/matrix inputs versus k.

    Energies are ``(2,nk)`` on one nextnano electron-energy reference. Matrix
    inputs may be constant ``(2,2)`` or k dependent ``(2,2,nk)``.  All complex
    phases survive until the final caller chooses an observable.
    """
    k = np.asarray(k_per_nm, dtype=float)
    ee = np.asarray(electron_energies_eV, dtype=float)
    eh = np.asarray(hole_energies_eV, dtype=float)
    if ee.shape != (2, len(k)) or eh.shape != (2, len(k)):
        raise ValueError("electron/hole energies must each have shape (2,nk)")
    transition = ee[:, None, :] - eh[None, :, :]
    if np.any(transition <= 0) or not np.all(np.isfinite(transition)):
        raise ValueError("all Ee-Eh transition energies must be finite and positive")
    o = _as_k_matrix(overlap_eh, (2, 2), len(k))
    ze = _as_k_matrix(z_e_nm, (2, 2), len(k))
    zh = _as_k_matrix(z_h_nm, (2, 2), len(k))
    config = settings or validated.Chi2Settings(broadening_meV=float(broadening_meV))
    if abs(config.broadening_meV - float(broadening_meV)) > 1e-15:
        config = validated.replace_settings(config, broadening_meV=float(broadening_meV))
    weights = radial_weights(k, config.spin_degeneracy)
    prefactor = validated.absolute_prefactor(config)
    lam = np.asarray(wavelengths_nm, dtype=float)
    terms = []
    labels = []
    summed = np.zeros((len(lam), len(k)), dtype=complex)
    hw = validated.HC_EV_NM / lam
    gamma = float(broadening_meV) * 1e-3
    for m in range(2):
        for n in range(2):
            d2 = transition[n, m][None, :] - 2 * hw[:, None] + 1j * gamma
            for ell in range(2):
                numerator = o[n, m] * ze[n, ell] * o[ell, m]
                d1 = transition[ell, m][None, :] - hw[:, None] + 1j * gamma
                value = numerator / (d2 * d1)
                summed += value
                terms.append(prefactor * (value @ weights))
                labels.append(f"C_m{m+1}_n{n+1}_l{ell+1}")
            for ell in range(2):
                numerator = -o[n, m] * zh[m, ell] * o[n, ell]
                d1 = transition[n, ell][None, :] - hw[:, None] + 1j * gamma
                value = numerator / (d2 * d1)
                summed += value
                terms.append(prefactor * (value @ weights))
                labels.append(f"V_m{m+1}_n{n+1}_l{ell+1}")
    return KResolvedSpectrum(lam, prefactor * (summed @ weights), np.asarray(terms),
                             tuple(labels), summed, weights)


def validate_against_demo20() -> float:
    """Return max complex error against Demo 20 for its own parabolic inputs."""
    docs = DEMO_DIR.parents[2] / "docs" / "demo21"
    if str(docs) not in sys.path:
        sys.path.insert(0, str(docs))
    import compare_demo21_hybrid_spectra as cached  # noqa: PLC0415
    e, h, o, ze, zh = cached.read_demo21_inputs()
    settings = validated.Chi2Settings()
    states = validated.CaseStates("04", e, h, o, ze, zh, "cached licensed")
    k, _ = validated.k_grid(settings)
    transition = validated.transition_energies_eV(states, k, settings)
    # Decompose the common parabolic transition shift between electron/hole
    # curves without changing any Ee-Eh value.
    shift = transition[0, 0] - (e[0] - h[0])
    ee = np.vstack([e[0] + shift, e[1] + shift])
    hh = np.vstack([np.full_like(k, h[0]), np.full_like(k, h[1])])
    wavelength = np.arange(400.0, 1851.0, 1.0)
    reference = validated.chi2_spectrum(states, wavelength, settings).chi2
    adapted = chi2_from_k_inputs(wavelength, k, ee, hh, o, ze, zh,
                                 broadening_meV=5.0, settings=settings).chi2
    return float(np.max(np.abs(reference - adapted)))

