"""Linear interband susceptibility chi1_xx from the SAME electronic structure as Eq. 2.

    chi1(hw) = C1 * sum_k w_k * sum_(n,m) |O_nm|^2 / (T_nm(k) - hw + i*s*Gamma)

Every ingredient is the one Eq. 2 uses (demo30/equation2.py):

- T_nm(k) = Ee_n(k) - Ev_m(k): the Eq. 2 transition energies (eV), on the stored k grid;
- O_nm = <e_n|hh_m>: the Eq. 2 interband envelope overlaps (frozen at k = 0 in the model);
- w_k = g_s k dk / (2 pi): the Eq. 2 radial weights (nm^-2), i.e. g_s * integral d^2k/(2 pi)^2;
- Gamma and s = Settings.gamma_sign (+1: Eq. 2's +i*Gamma, the e^(+i omega t) convention,
  in which a passive medium has Im chi1 < 0);
- the interband unit-cell dipole r_e,hh and the stack density N_z = 1/period.

Prefactor. For N_z carriers-per-length of coupled wells, the interband dipole of pair
(n,m) is e*r_e,hh*O_nm, the same factorization Eq. 2 applies to each interband leg. The
standard density-matrix result (filled valence band, resonant term) is

    chi1 = (N_z e^2 r^2 / eps0) * g_s * integral d^2k/(2 pi)^2 * sum |O|^2 / (E_nm(k) - hw + i s Gamma).

Units: N_z [m^-1] * e^2 [C^2] * r^2 [m^2] / eps0 [C^2 J^-1 m^-1] * integral d^2k [m^-2] / E [J]
is dimensionless. With w in nm^-2 (x 1e18 -> m^-2) and energies in eV (x e -> J):

    C1 = N_z * e * r^2 * 1e18 / eps0   [volts; multiplies sum w[nm^-2] / E[eV]]

For N_z = 1/(30 nm) and r = 0.751 nm, C1 = 0.34019. Only the resonant term is kept. That
matches Eq. 2 (which has no antiresonant terms) and 1994 Eq. 1a.

Strict vs tail. The strict value sums only the stored k nodes through k_max (0.1·π/a).
The tail value adds an analytical continuation of Im chi1 beyond k_max. There, each
transition continues as T(k^2) = T(k_max^2) + slope*(k^2 - k_max^2), with the slope fitted
to the last nodes. That gives the constant 2D joint density of states g_s/(4 pi slope), and

    Im chi1_tail = C1 * |O|^2 * g_s/(4 pi slope) * (-s) * [pi/2 - arctan((T(k_max) - hw)/Gamma)].

Re chi1 has no finite continuation of this kind (it diverges logarithmically), so tail
results change Im only and keep the strict Re. The tail is an ANALYTICAL APPROXIMATION,
always reported next to the strict numerical result, never instead of it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .equation2 import E_C, EPS0, Settings
from .k_integration import radial_weights


def chi1_prefactor(settings: Settings) -> float:
    """C1 = N_z e r_e,hh^2 1e18 / eps0 (V); see the module docstring for units."""
    nz = 1.0 / (settings.period_nm * 1e-9)
    return nz * E_C * (settings.r_e_hh_nm * 1e-9) ** 2 * 1e18 / EPS0


@dataclass(frozen=True)
class Pair:
    """One interband transition e_n -> hh_m on the stored k grid."""
    label: str
    transition_eV: np.ndarray   # (nk,)
    overlap_sq: np.ndarray      # (nk,) |O_nm(k)|^2
    dispersion: str             # 'kp8 (tracked)' or 'parabolic (assumed slope)'


def pairs_2x2(inputs: dict) -> list[Pair]:
    """The four e_n-hh_m pairs of the Eq. 2 model, with Eq. 2's own energies and overlaps."""
    k = np.asarray(inputs["k_per_nm"], float)
    ee, vv = np.asarray(inputs["electron_eV"], float), np.asarray(inputs["valence_eV"], float)
    o = np.asarray(inputs["overlap"], complex)
    if o.shape == (2, 2):
        o = np.repeat(o[:, :, None], len(k), axis=2)
    return [Pair(f"e{n + 1}-hh{m + 1}", ee[n] - vv[m], np.abs(o[n, m]) ** 2, "kp8 (tracked)")
            for n in range(2) for m in range(2)]


def strict_terms(photon_energy_eV, pairs: list[Pair], k_per_nm, settings: Settings) -> np.ndarray:
    """(n_pairs, n_E) complex chi1 contributions from the stored k nodes only."""
    e = np.asarray(photon_energy_eV, float)[:, None]
    w = radial_weights(np.asarray(k_per_nm, float), settings.spin_degeneracy)
    g = 1j * settings.gamma_sign * settings.gamma_eV
    c1 = chi1_prefactor(settings)
    out = []
    for p in pairs:
        if p.transition_eV.shape != w.shape or np.any(p.transition_eV <= 0):
            raise ValueError(f"{p.label}: transition energies must be positive on the k grid")
        out.append(c1 * ((p.overlap_sq / (p.transition_eV[None, :] - e + g)) @ w))
    return np.asarray(out)


def tail_slope(pair: Pair, k_per_nm, fit_fraction: float) -> float:
    """dT/d(k^2) fitted to the last fit_fraction of the k nodes (eV nm^2)."""
    k = np.asarray(k_per_nm, float)
    last = k >= (1 - fit_fraction) * k[-1]
    if last.sum() < 3:
        raise ValueError("too few k nodes for the tail slope fit")
    slope = np.polyfit(k[last] ** 2, pair.transition_eV[last], 1)[0]
    if not slope > 0:
        raise ValueError(f"{pair.label}: non-positive high-k slope {slope}; the tail continuation does not apply")
    return float(slope)


def tail_im_terms(photon_energy_eV, pairs: list[Pair], k_per_nm, settings: Settings,
                  fit_fraction: float) -> tuple[np.ndarray, list[float]]:
    """(n_pairs, n_E) Im chi1 of the analytical continuation beyond k_max, and the slopes."""
    e = np.asarray(photon_energy_eV, float)
    c1, gamma, s = chi1_prefactor(settings), settings.gamma_eV, settings.gamma_sign
    terms, slopes = [], []
    for p in pairs:
        slope = tail_slope(p, k_per_nm, fit_fraction)
        jdos = settings.spin_degeneracy / (4 * np.pi * slope)  # nm^-2 eV^-1
        edge = p.transition_eV[-1]
        terms.append(c1 * p.overlap_sq[-1] * jdos * (-s) * (np.pi / 2 - np.arctan((edge - e) / gamma)))
        slopes.append(slope)
    return np.asarray(terms), slopes


@dataclass
class Chi1:
    """chi1 at one set of photon energies for one state set: strict and tail variants."""
    photon_energy_eV: np.ndarray
    labels: list
    strict_terms: np.ndarray     # (n_pairs, n_E) complex
    tail_im_terms: np.ndarray    # (n_pairs, n_E) real, Im part beyond k_max
    tail_slopes: list

    @property
    def strict(self) -> np.ndarray:
        return self.strict_terms.sum(axis=0)

    @property
    def tail(self) -> np.ndarray:
        """Strict Re, strict + continued Im (the analytical tail changes Im only)."""
        return self.strict + 1j * self.tail_im_terms.sum(axis=0)


def evaluate(photon_energy_eV, pairs: list[Pair], k_per_nm, settings: Settings, fit_fraction: float) -> Chi1:
    tail, slopes = tail_im_terms(photon_energy_eV, pairs, k_per_nm, settings, fit_fraction)
    return Chi1(np.asarray(photon_energy_eV, float), [p.label for p in pairs],
                strict_terms(photon_energy_eV, pairs, k_per_nm, settings), tail, slopes)
