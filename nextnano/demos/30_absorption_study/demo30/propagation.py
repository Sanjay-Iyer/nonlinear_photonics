"""Almogy and Yariv (1994) Eq. 5: SH generated in an absorbing slab.

The equation assumes phase matching (beta = 0) and no pump depletion. With alpha_w and
alpha_2w FIELD coefficients (1994 Eq. 3; E ~ exp(-alpha_E z)):

    E_2w(L) = -i (w / n c) chi2 E_w(0)^2 [exp(-2 alpha_w L) - exp(-alpha_2w L)] / (alpha_2w - 2 alpha_w)
            = -i (w / n c) chi2 E_w(0)^2 * L * A

    A(L) = exp(-2 alpha_w L) * (1 - exp(-d L)) / (d L),   d = alpha_2w - 2 alpha_w

- A = 1 without absorption (the transparent result). |A|^2 is the factor by which
  absorption suppresses the SH intensity. The factor 2 in exp(-2 alpha_w z) arises because
  the SH source is E_w^2; it is not an intensity conversion.
- The expm1 form is stable as d -> 0 (alpha_2w -> 2 alpha_w) and as alpha -> 0.
- A equals the homogeneous, reflection-free limit of the 2026 paper's Eq. 3 field overlap,
  A = (1/L) * integral_0^L exp(-2 alpha_w z) exp(-alpha_2w (L - z)) dz. Demo 31 replaces
  these exponentials with multilayer (transfer-matrix) fields.
- Phase mismatch is NOT part of the Demo 30 propagated model. coherence_length() only
  estimates its size, as a stated limitation.
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp

from .absorption import omega_over_c


def absorption_factor(alpha_E_w, alpha_E_2w, length_m) -> np.ndarray:
    """A = exp(-2 a_w L) (1 - exp(-(a_2w - 2 a_w) L)) / ((a_2w - 2 a_w) L); stable for all limits."""
    a1, a2 = np.asarray(alpha_E_w, float), np.asarray(alpha_E_2w, float)
    length = np.asarray(length_m, float)
    x = (a2 - 2.0 * a1) * length
    safe = np.where(np.abs(x) < 1e-6, 1.0, x)
    ratio = np.where(np.abs(x) < 1e-6, 1.0 - x / 2.0 + x * x / 6.0, -np.expm1(-safe) / safe)
    return np.exp(-2.0 * a1 * length) * ratio


def absorption_factor_ode(alpha_E_w: float, alpha_E_2w: float, length_m: float) -> float:
    """Numerical check: integrate 1994 Eq. 3a, dy/dz = -a_2w y + exp(-2 a_w z), y(0) = 0; A = y(L)/L.

    (The constant -i (w/nc) chi2 E_w(0)^2 is divided out; Eq. 3b without depletion gives
    E_w(z) = E_w(0) exp(-a_w z).)
    """
    sol = solve_ivp(lambda z, y: -alpha_E_2w * y + np.exp(-2.0 * alpha_E_w * z), (0.0, length_m), [0.0],
                    method="DOP853", rtol=1e-12, atol=1e-18)
    return float(sol.y[0, -1] / length_m)


def absorption_factor_overlap(alpha_E_w: float, alpha_E_2w: float, length_m: float, points: int = 20001) -> float:
    """Numerical check: the reciprocity/field-overlap form (2026 Eq. 3, homogeneous slab), Simpson rule."""
    from scipy.integrate import simpson
    z = np.linspace(0.0, length_m, points)
    return float(simpson(np.exp(-2.0 * alpha_E_w * z) * np.exp(-alpha_E_2w * (length_m - z)), x=z) / length_m)


def sh_transfer_m_per_V(chi2_pm_per_V, photon_energy_w_eV, n_2w: float, length_m, factor) -> np.ndarray:
    """|E_2w(L)| / |E_w(0)|^2 = (w / n c) |chi2| L |A| in m/V (1994 Eq. 5 prefactor)."""
    return omega_over_c(photon_energy_w_eV) / n_2w * np.abs(np.asarray(chi2_pm_per_V)) * 1e-12 * length_m * np.abs(factor)


def coherence_length(wavelength_w_nm, n_w: float, n_2w: float, length_m: float) -> dict:
    """Size of the phase mismatch that Demo 30 does NOT model (limitation estimate only).

    dk = k_2w - 2 k_w = 4 pi (n_2w - n_w) / lambda_w;  L_c = pi / dk = lambda_w / (4 (n_2w - n_w));
    a phase-matched SH intensity would be reduced by sinc^2(dk L / 2) for a transparent slab.
    """
    lam = float(wavelength_w_nm) * 1e-9
    dk = 4.0 * np.pi * (n_2w - n_w) / lam
    x = dk * length_m / 2.0
    return {"wavelength_nm": float(wavelength_w_nm), "n_w": n_w, "n_2w": n_2w, "delta_k_per_um": dk * 1e-6,
            "coherence_length_um": np.pi / dk * 1e6, "sample_length_um": length_m * 1e6,
            "sinc2_suppression_if_transparent": float((np.sin(x) / x) ** 2)}
