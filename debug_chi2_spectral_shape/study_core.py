"""Shared numerical core for the solver-free chi(2) debugging experiments.

Only cached, licensed Demo 21 Case 04 state data are accepted.  This module
does not invoke nextnano++ and deliberately contains no fallback-state path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import run_phase1 as phase1


WL = phase1.WAVELENGTHS
HC = phase1.production.HC_EV_NM
PREF = phase1.production.absolute_prefactor(phase1.production.Chi2Settings())
HBAR = phase1.production.REDUCED_PLANCK_J_S
M0 = phase1.production.ELECTRON_MASS_KG
Q = phase1.production.ELEMENTARY_CHARGE_C


@dataclass
class Evaluation:
    k: np.ndarray
    weights: np.ndarray
    transitions: np.ndarray
    term_labels: list[str]
    term_groups: list[str]
    term_spectra: np.ndarray
    conduction: np.ndarray
    valence: np.ndarray
    total: np.ndarray
    abs_orders: dict[str, np.ndarray]
    summed_integrand: np.ndarray | None = None


def inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return phase1.comparison.read_demo21_inputs()


def k_weights(k: np.ndarray, *, spin: int = 2, bare_d2k: bool = False) -> np.ndarray:
    """Trapezoid weights for g_s/(2pi) integral k dk, or bare d2k."""
    if len(k) < 2:
        raise ValueError("k grid needs at least two points")
    dk = float(k[1] - k[0])
    radial = spin * k / (2.0 * math.pi)
    if bare_d2k:
        radial *= (2.0 * math.pi) ** 2
    weights = radial * dk
    weights[[0, -1]] *= 0.5
    return weights


def band_curves(
    k: np.ndarray,
    electron: np.ndarray,
    hole: np.ndarray,
    replaced: tuple[str, ...] = (),
) -> dict[str, np.ndarray]:
    """Individual parabolic curves with optional hybrid-polynomial replacements."""
    alpha = HBAR**2 * 1.0e18 / (2.0 * M0 * Q)
    curves = {
        "e1": electron[0] + alpha * k**2 / 0.067,
        "e2": electron[1] + alpha * k**2 / 0.067,
        "h1": hole[0] - alpha * k**2 / 0.112,
        "h2": hole[1] - alpha * k**2 / 0.112,
    }
    ka = 0.1 * k
    hybrid = {
        "e1": electron[0] + 54.492 * ka**2 - 851.1 * ka**4,
        "e2": electron[1] + 50.864 * ka**2 - 732.61 * ka**4,
        "h1": hole[0] - 6.9771 * ka**2 - 716.47 * ka**4 + 36809.0 * ka**6,
        "h2": hole[1] - 10.165 * ka**2,
    }
    for name in replaced:
        curves[name] = hybrid[name]
    return curves


def make_transitions(
    model: str,
    *,
    kmax: float | None = None,
    nk: int | None = None,
    replaced: tuple[str, ...] = (),
) -> tuple[np.ndarray, np.ndarray]:
    electron, hole, _, _, _ = inputs()
    if model == "demo21":
        kmax = float(kmax if kmax is not None else 0.1 * math.pi / 0.565325)
        nk = int(nk if nk is not None else 96)
        k = np.linspace(0.0, kmax, nk)
        curves = band_curves(k, electron, hole)
    elif model in {"hybrid", "ladder"}:
        kmax = float(kmax if kmax is not None else 1.2)
        nk = int(nk if nk is not None else 300)
        k = np.linspace(0.0, kmax, nk)
        use = ("e1", "e2", "h1", "h2") if model == "hybrid" else replaced
        curves = band_curves(k, electron, hole, use)
    else:
        raise ValueError(f"unknown model {model!r}")
    transitions = np.empty((2, 2, nk), dtype=float)
    for n, ename in enumerate(("e1", "e2")):
        for m, hname in enumerate(("h1", "h2")):
            transitions[n, m] = np.abs(curves[ename] - curves[hname])
    return k, transitions


def evaluate(
    model: str,
    *,
    wavelengths: np.ndarray = WL,
    gamma_meV: float = 5.0,
    kmax: float | None = None,
    nk: int | None = None,
    replaced: tuple[str, ...] = (),
    overlap: np.ndarray | None = None,
    z_e: np.ndarray | None = None,
    z_h: np.ndarray | None = None,
    retain_integrand: bool = False,
    abs_orders: bool = False,
    spin: int = 2,
    bare_d2k: bool = False,
) -> Evaluation:
    """Evaluate every one of the eight C and eight V pathways explicitly."""
    _, _, o0, ze0, zh0 = inputs()
    overlap = np.asarray(o0 if overlap is None else overlap, dtype=complex)
    z_e = np.asarray(ze0 if z_e is None else z_e, dtype=complex)
    z_h = np.asarray(zh0 if z_h is None else z_h, dtype=complex)
    k, transitions = make_transitions(model, kmax=kmax, nk=nk, replaced=replaced)
    weights = k_weights(k, spin=spin, bare_d2k=bare_d2k)
    hw = HC / np.asarray(wavelengths, dtype=float)
    gamma = float(gamma_meV) * 1.0e-3
    summed = np.zeros((len(hw), len(k)), dtype=complex)
    abs_term_sum = np.zeros((len(hw), len(k)), dtype=float) if abs_orders else None
    labels: list[str] = []
    groups: list[str] = []
    spectra: list[np.ndarray] = []

    for m in range(2):
        for n in range(2):
            d2 = transitions[n, m][None, :] - 2.0 * hw[:, None] + 1j * gamma
            for ell in range(2):
                numerator = overlap[n, m] * z_e[n, ell] * overlap[ell, m]
                d1 = transitions[ell, m][None, :] - hw[:, None] + 1j * gamma
                term = numerator / (d2 * d1)
                labels.append(f"C_m{m+1}_n{n+1}_l{ell+1}")
                groups.append("conduction")
                spectra.append(PREF * (term @ weights))
                summed += term
                if abs_term_sum is not None:
                    abs_term_sum += np.abs(term)
            for ell in range(2):
                numerator = -overlap[n, m] * z_h[m, ell] * overlap[n, ell]
                d1 = transitions[n, ell][None, :] - hw[:, None] + 1j * gamma
                term = numerator / (d2 * d1)
                labels.append(f"V_m{m+1}_n{n+1}_l{ell+1}")
                groups.append("valence")
                spectra.append(PREF * (term @ weights))
                summed += term
                if abs_term_sum is not None:
                    abs_term_sum += np.abs(term)

    term_spectra = np.asarray(spectra)
    group_array = np.asarray(groups)
    conduction = np.sum(term_spectra[group_array == "conduction"], axis=0)
    valence = np.sum(term_spectra[group_array == "valence"], axis=0)
    total = PREF * (summed @ weights)
    orders: dict[str, np.ndarray] = {}
    if abs_orders:
        orders = {
            "A_abs_integral_sum": np.abs(total),
            "B_integral_abs_sum": PREF * (np.abs(summed) @ weights),
            "C_sum_abs_integral_term": np.sum(np.abs(term_spectra), axis=0),
            "D_integral_sum_abs_term": PREF * (abs_term_sum @ weights),
        }
    return Evaluation(
        k=k,
        weights=weights,
        transitions=transitions,
        term_labels=labels,
        term_groups=groups,
        term_spectra=term_spectra,
        conduction=conduction,
        valence=valence,
        total=total,
        abs_orders=orders,
        summed_integrand=summed if retain_integrand else None,
    )


def normalized(values: np.ndarray) -> np.ndarray:
    values = np.abs(np.asarray(values))
    maximum = float(np.max(values))
    return values / maximum if maximum else values


def paper_norm() -> np.ndarray:
    paper = np.interp(WL, phase1.PAPER_POINTS[:, 0], phase1.PAPER_POINTS[:, 1])
    return paper / float(np.max(paper))


def curve_metrics(values: np.ndarray) -> dict[str, float]:
    curve = normalized(values)
    n1 = phase1.window_minimum(curve, phase1.NODE1)
    n2 = phase1.window_minimum(curve, phase1.NODE2)
    peak = phase1.dominant_peak(curve)
    return {
        "node1_nm": n1[0], "node1_depth": n1[1],
        "node2_nm": n2[0], "node2_depth": n2[1],
        "peak_nm": peak[0], "peak_norm": peak[1],
        "rmse": float(np.sqrt(np.mean((curve - paper_norm()) ** 2))),
    }


def crossing_rows(values: np.ndarray) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    y = np.asarray(values, dtype=float)
    for i in range(len(WL) - 1):
        y0, y1 = float(y[i]), float(y[i + 1])
        if y0 == 0 or y0 * y1 < 0:
            x = float(WL[i] if y0 == 0 else WL[i] - y0 / (y1 - y0))
            nearest = 605.0 if abs(x - 605.0) <= abs(x - 1330.0) else 1330.0
            rows.append({
                "crossing_nm": x,
                "direction": "negative_to_positive" if y1 > y0 else "positive_to_negative",
                "nearest_paper_node_nm": nearest,
                "distance_from_nearest_paper_node_nm": x - nearest,
            })
    return rows


def cumulative_integral(k: np.ndarray, integrand: np.ndarray) -> np.ndarray:
    """Cumulative spin-2 radial Eq. 2 integral, including the absolute prefactor."""
    radial = k[None, :] / math.pi * integrand
    increments = 0.5 * (radial[:, 1:] + radial[:, :-1]) * np.diff(k)[None, :]
    out = np.zeros_like(integrand, dtype=complex)
    out[:, 1:] = np.cumsum(increments, axis=1)
    return PREF * out

