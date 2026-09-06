"""Paper-curve provenance and feature matching."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from signed_spectrum import normalize, peak_indices, window_minimum


def load_curve(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return (np.asarray([float(r["wavelength_nm"]) for r in rows]),
            np.asarray([float(r["digitized_simulated_chi2_pm_per_V"]) for r in rows]))


def paper_feature_table(wavelength_nm: np.ndarray, values: np.ndarray,
                        config: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    norm = normalize(values)
    auto = peak_indices(wavelength_nm, values,
                        prominence_fraction=float(config["peak_prominence_fraction"]),
                        minimum_distance_nm=float(config["minimum_peak_distance_nm"]))
    auto_peaks = [float(wavelength_nm[i]) for i in auto]
    uncertainty = float(config["digitization_uncertainty_nm"])
    for feature in config["expected"]:
        window = tuple(map(float, feature["window_nm"]))
        mask = (wavelength_nm >= window[0]) & (wavelength_nm <= window[1])
        local = np.flatnonzero(mask)
        if feature["type"] == "peak":
            index = int(local[np.argmax(norm[mask])])
        else:
            index = int(window_minimum(wavelength_nm, values, window)["index"])
        rows.append({
            "Feature": feature["name"],
            "Paper wavelength nm": float(wavelength_nm[index]),
            "Normalized amplitude": float(norm[index]),
            "Feature type": feature["type"],
            "Confidence": feature["confidence"],
            "Digitization uncertainty nm": uncertainty,
            "Configured nominal nm": float(feature["wavelength_nm"]),
            "Search window nm": f"{window[0]:g}-{window[1]:g}",
            "Automatic peak detected": bool(any(window[0] <= p <= window[1] for p in auto_peaks)) if feature["type"] == "peak" else "n/a",
        })
    return rows


def interpolate_paper(model_wavelength_nm: np.ndarray, paper_wavelength_nm: np.ndarray,
                      paper_values: np.ndarray) -> np.ndarray:
    return np.interp(model_wavelength_nm, paper_wavelength_nm, paper_values)
