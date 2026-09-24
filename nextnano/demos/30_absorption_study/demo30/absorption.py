"""Absorption coefficients from chi1, with the field/intensity convention explicit.

Almogy and Yariv (1994) Eq. 2a defines alpha_w = (w / 2 n c) Im chi1. Their Eq. 3b,
dE_w/dz = -alpha_w E_w, makes it a FIELD (amplitude) coefficient:

    E(z) = E0 exp(-alpha_E z),   I(z) = I0 exp(-alpha_I z),   alpha_I = 2 alpha_E.

alpha_I is the usual Beer-Lambert coefficient (the one quoted in cm^-1 in the
literature). All names below carry _E or _I.

Sign. The 1994 paper uses 1/(Delta - i) (e^(-i w t) convention), so Im chi1 > 0 means
loss. Eq. 2 and Demo 30's chi1 use +i*Gamma (e^(+i w t) convention), so Im chi1 < 0
means loss. The one convention-aware formula is

    alpha_E = (w / 2 n c) * (-gamma_sign) * Im chi1,

which is positive for a passive medium in either convention (tested for both signs).
"""
from __future__ import annotations

import numpy as np

HBAR_C_EV_M = 1.973269804e-7    # hbar*c in eV*m (CODATA 2018)
HC_EV_NM = 1239.841984          # h*c in eV*nm (same constant as equation2.py)


def omega_over_c(photon_energy_eV) -> np.ndarray:
    """w/c in m^-1 for a photon energy in eV."""
    return np.asarray(photon_energy_eV, float) / HBAR_C_EV_M


def alpha_E(chi1, photon_energy_eV, n: float, gamma_sign: int) -> np.ndarray:
    """Field attenuation coefficient (m^-1), first order in chi1/n^2 (1994 Eq. 2a)."""
    if gamma_sign not in (-1, 1):
        raise ValueError("gamma_sign must be +1 or -1")
    return omega_over_c(photon_energy_eV) * (-gamma_sign) * np.imag(chi1) / (2.0 * n)


def alpha_I(chi1, photon_energy_eV, n: float, gamma_sign: int) -> np.ndarray:
    """Intensity (Beer-Lambert) attenuation coefficient (m^-1): 2 * alpha_E."""
    return 2.0 * alpha_E(chi1, photon_energy_eV, n, gamma_sign)


def alpha_E_exact(chi1, photon_energy_eV, n: float, gamma_sign: int) -> np.ndarray:
    """(w/c) Im sqrt(n^2 + chi1), written in the e^(-i w t) convention; checks the first-order form."""
    chi_phys = np.conj(chi1) if gamma_sign == 1 else np.asarray(chi1)
    return omega_over_c(photon_energy_eV) * np.imag(np.sqrt(n ** 2 + chi_phys))


def per_cm(alpha_per_m) -> np.ndarray:
    return np.asarray(alpha_per_m) / 100.0


def length_um(alpha_per_m) -> np.ndarray:
    """1/alpha in micrometres (inf where alpha <= 0)."""
    a = np.asarray(alpha_per_m, float)
    return np.divide(1e6, a, out=np.full_like(a, np.inf), where=a > 0)
