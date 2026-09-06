"""Shared spectrum metrics for Gamma, grid, kmax, and direction ladders."""

from __future__ import annotations

from typing import Mapping

import numpy as np

from signed_spectrum import normalize, normalized_rmse, peak_indices, window_minimum


def spectrum_metrics(label: str, wavelength_nm: np.ndarray, chi: np.ndarray,
                     paper_on_grid: np.ndarray, zero_windows: Mapping[str, tuple[float, float]],
                     *, prominence: float = 0.04, distance_nm: float = 70.0) -> dict[str, object]:
    norm = normalize(chi)
    peaks = peak_indices(wavelength_nm, chi, prominence_fraction=prominence,
                         minimum_distance_nm=distance_nm)
    ordered = sorted(peaks, key=lambda i: norm[i], reverse=True)
    row: dict[str, object] = {
        "case": label, "major_peak_count": len(peaks),
        "peak_wavelengths_nm": ";".join(f"{wavelength_nm[i]:.1f}" for i in peaks),
        "dominant_peak_nm": float(wavelength_nm[int(np.argmax(norm))]),
        "normalized_RMSE": normalized_rmse(paper_on_grid, chi),
        "spectral_correlation": float(np.corrcoef(normalize(paper_on_grid), norm)[0, 1]),
    }
    for rank, i in enumerate(ordered[:4], start=1):
        row[f"rank{rank}_peak_nm"] = float(wavelength_nm[i])
        row[f"rank{rank}_peak_norm"] = float(norm[i])
    for name, window in zero_windows.items():
        minimum = window_minimum(wavelength_nm, chi, window)
        row[f"{name}_minimum_nm"] = minimum["wavelength_nm"]
        row[f"{name}_minimum_norm"] = minimum["normalized_amplitude"]
    return row
