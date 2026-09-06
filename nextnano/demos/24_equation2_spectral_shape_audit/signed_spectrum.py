"""Signed, complex, peak, minimum, and cancellation diagnostics."""

from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks


def normalize(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    scale = float(np.max(np.abs(array))) if array.size else 0.0
    return np.abs(array) / scale if scale > 0 else np.zeros_like(array, dtype=float)


def peak_indices(wavelength_nm: np.ndarray, values: np.ndarray, *, prominence_fraction: float = 0.04,
                 minimum_distance_nm: float = 70.0) -> np.ndarray:
    x = np.asarray(wavelength_nm, dtype=float)
    y = normalize(np.asarray(values))
    spacing = float(np.median(np.diff(x)))
    distance = max(1, int(round(float(minimum_distance_nm) / spacing)))
    peaks, _ = find_peaks(y, prominence=float(prominence_fraction), distance=distance)
    return peaks


def window_minimum(wavelength_nm: np.ndarray, values: np.ndarray, window_nm: tuple[float, float]) -> dict[str, float]:
    x = np.asarray(wavelength_nm, dtype=float)
    y = normalize(np.asarray(values))
    mask = (x >= window_nm[0]) & (x <= window_nm[1])
    if not np.any(mask):
        raise ValueError(f"window {window_nm} has no samples")
    local = np.flatnonzero(mask)
    index = int(local[np.argmin(y[mask])])
    return {"wavelength_nm": float(x[index]), "normalized_amplitude": float(y[index]), "index": index}


def sign_crossings(wavelength_nm: np.ndarray, component: np.ndarray, window_nm: tuple[float, float] | None = None) -> list[float]:
    x = np.asarray(wavelength_nm, dtype=float)
    y = np.asarray(component, dtype=float)
    result: list[float] = []
    for i in range(len(x) - 1):
        if window_nm and not (window_nm[0] <= x[i] <= window_nm[1] or window_nm[0] <= x[i + 1] <= window_nm[1]):
            continue
        if y[i] == 0:
            result.append(float(x[i]))
        elif y[i] * y[i + 1] < 0:
            result.append(float(x[i] - y[i] * (x[i + 1] - x[i]) / (y[i + 1] - y[i])))
    return result


def complex_zero_diagnostic(wavelength_nm: np.ndarray, chi: np.ndarray, window_nm: tuple[float, float],
                            threshold_fraction: float = 0.02) -> dict[str, object]:
    minimum = window_minimum(wavelength_nm, chi, window_nm)
    real_cross = sign_crossings(wavelength_nm, np.real(chi), window_nm)
    imag_cross = sign_crossings(wavelength_nm, np.imag(chi), window_nm)
    x0 = float(minimum["wavelength_nm"])
    nearest_real = min(real_cross, key=lambda v: abs(v - x0)) if real_cross else None
    nearest_imag = min(imag_cross, key=lambda v: abs(v - x0)) if imag_cross else None
    return {
        **minimum,
        "real_crossings_nm": real_cross,
        "imag_crossings_nm": imag_cross,
        "nearest_real_crossing_nm": nearest_real,
        "nearest_imag_crossing_nm": nearest_imag,
        "full_complex_zero": bool(float(minimum["normalized_amplitude"]) <= threshold_fraction),
        "threshold_fraction": float(threshold_fraction),
    }


def cancellation_metric(electron: complex, heavy_hole_signed: complex) -> float:
    denominator = abs(electron) + abs(heavy_hole_signed)
    return float(abs(electron + heavy_hole_signed) / denominator) if denominator else 0.0


def phase_difference_deg(first: complex, second: complex) -> float:
    return float(np.degrees(np.angle(first) - np.angle(second) + np.pi) % 360.0 - 180.0)


def normalized_rmse(reference: np.ndarray, candidate: np.ndarray) -> float:
    a, b = normalize(reference), normalize(candidate)
    return float(np.sqrt(np.mean((a - b) ** 2)))
