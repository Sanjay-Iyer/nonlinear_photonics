"""Centralized radial and diagnostic k-space integration conventions."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np


KConvention = Literal["d2k_over_2pi_squared", "bare_d2k"]


def trapezoid_node_widths(x: np.ndarray) -> np.ndarray:
    values = np.asarray(x, dtype=float)
    if values.ndim != 1 or len(values) < 2 or np.any(np.diff(values) <= 0):
        raise ValueError("integration coordinate must be strictly increasing")
    widths = np.empty_like(values)
    widths[0] = 0.5 * (values[1] - values[0])
    widths[-1] = 0.5 * (values[-1] - values[-2])
    widths[1:-1] = 0.5 * (values[2:] - values[:-2])
    return widths


def radial_weights(
    k_per_nm: np.ndarray,
    *,
    spin_degeneracy: int = 2,
    convention: KConvention = "d2k_over_2pi_squared",
) -> np.ndarray:
    """Return radial weights in nm^-2 without silently changing convention."""

    k = np.asarray(k_per_nm, dtype=float)
    if k[0] < 0:
        raise ValueError("radial k grid must be nonnegative")
    dk = trapezoid_node_widths(k)
    if convention == "d2k_over_2pi_squared":
        radial = k / (2.0 * math.pi)
    elif convention == "bare_d2k":
        radial = 2.0 * math.pi * k
    else:
        raise ValueError(f"unknown k-space convention {convention!r}")
    return float(spin_degeneracy) * radial * dk


def analytic_disc_measure(
    kmax_per_nm: float,
    *,
    spin_degeneracy: int = 2,
    convention: KConvention = "d2k_over_2pi_squared",
) -> float:
    if convention == "d2k_over_2pi_squared":
        return float(spin_degeneracy) * float(kmax_per_nm) ** 2 / (4.0 * math.pi)
    if convention == "bare_d2k":
        return float(spin_degeneracy) * math.pi * float(kmax_per_nm) ** 2
    raise ValueError(f"unknown k-space convention {convention!r}")


def integrate_radial(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    w = np.asarray(weights, dtype=float)
    if array.shape[-1] != len(w):
        raise ValueError("last value dimension must match k weights")
    return array @ w


def synthetic_radial_vs_cartesian_error(kmax_per_nm: float, points: int = 801) -> float:
    """Compare radial and direct Cartesian quadrature for exp[-(k/kmax)^2]."""

    k = np.linspace(0.0, float(kmax_per_nm), int(points))
    radial = float(np.dot(radial_weights(k), np.exp(-(k / kmax_per_nm) ** 2)))
    axis = np.linspace(-kmax_per_nm, kmax_per_nm, int(points))
    step = axis[1] - axis[0]
    kx, ky = np.meshgrid(axis, axis, indexing="ij")
    radius = np.sqrt(kx * kx + ky * ky)
    values = np.where(radius <= kmax_per_nm, np.exp(-(radius / kmax_per_nm) ** 2), 0.0)
    cartesian = 2.0 * float(np.sum(values)) * step * step / (2.0 * math.pi) ** 2
    return abs(radial - cartesian) / abs(radial)

