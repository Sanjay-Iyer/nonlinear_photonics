"""Traceable Ramesh et al. comparison data and diagnostic metrics."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np


LABEL = "Digitized from Ramesh et al. Fig. 2d"


@dataclass(frozen=True)
class PaperCurve:
    wavelength_nm: np.ndarray
    chi2_pm_per_V: np.ndarray
    label: str
    source_type: str
    source: Path


def load_digitized_curve(path: Path) -> PaperCurve:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    wavelength = np.asarray([float(row["wavelength_nm"]) for row in rows])
    values = np.asarray([float(row["digitized_simulated_chi2_pm_per_V"]) for row in rows])
    if len(wavelength) < 3 or np.any(np.diff(wavelength) <= 0) or np.any(values < 0):
        raise ValueError("paper digitization must be monotonic in wavelength and nonnegative")
    return PaperCurve(wavelength, values, LABEL, "eye-digitized published figure", Path(path))


def normalized(values: np.ndarray) -> np.ndarray:
    magnitude = np.abs(np.asarray(values, dtype=float))
    maximum = float(np.max(magnitude)) if len(magnitude) else 0.0
    return magnitude / maximum if maximum else magnitude


def comparison_metrics(result: Any, paper: PaperCurve) -> dict[str, Any]:
    wavelength = np.asarray(result.spectrum.wavelength_nm, dtype=float)
    magnitude = np.asarray(result.magnitude, dtype=float)
    mask = (wavelength >= paper.wavelength_nm[0]) & (wavelength <= paper.wavelength_nm[-1])
    common_wavelength = wavelength[mask]
    if len(common_wavelength) < 3:
        raise ValueError("Demo 23 and paper digitization do not have enough wavelength overlap")
    demo = magnitude[mask]
    digitized = np.interp(common_wavelength, paper.wavelength_nm, paper.chi2_pm_per_V)
    demo_peak = int(np.argmax(demo))
    paper_peak = int(np.argmax(digitized))
    target = 1550.0
    return {
        "mode": result.mode,
        "paper_curve_label": paper.label,
        "paper_source_type": paper.source_type,
        "comparison_wavelength_min_nm": float(common_wavelength[0]),
        "comparison_wavelength_max_nm": float(common_wavelength[-1]),
        "comparison_points": int(len(common_wavelength)),
        "RMSE_vs_digitized_paper_pm_per_V": float(np.sqrt(np.mean((demo - digitized) ** 2))),
        "normalized_RMSE_vs_digitized_paper": float(
            np.sqrt(np.mean((normalized(demo) - normalized(digitized)) ** 2))
        ),
        "demo_peak_wavelength_nm": float(common_wavelength[demo_peak]),
        "digitized_paper_peak_wavelength_nm": float(common_wavelength[paper_peak]),
        "peak_wavelength_error_nm": float(common_wavelength[demo_peak] - common_wavelength[paper_peak]),
        "demo_peak_pm_per_V": float(demo[demo_peak]),
        "digitized_paper_peak_pm_per_V": float(digitized[paper_peak]),
        "peak_magnitude_error_pm_per_V": float(demo[demo_peak] - digitized[paper_peak]),
        "demo_chi2_1550_pm_per_V": float(np.interp(target, wavelength, magnitude)),
        "digitized_paper_chi2_1550_pm_per_V": float(
            np.interp(target, paper.wavelength_nm, paper.chi2_pm_per_V)
        ),
        "chi2_1550_error_pm_per_V": float(
            np.interp(target, wavelength, magnitude)
            - np.interp(target, paper.wavelength_nm, paper.chi2_pm_per_V)
        ),
        "metric_status": "DIAGNOSTIC_ONLY_EYE_DIGITIZATION",
    }


def reference_rows(cfg: Mapping[str, Any], paper: PaperCurve) -> list[dict[str, Any]]:
    block = cfg["paper_comparison"]
    return [
        {
            "reference": "Fig. 2d simulated spectrum",
            "value": f"{len(paper.wavelength_nm)} points, {paper.wavelength_nm[0]:g}-{paper.wavelength_nm[-1]:g} nm",
            "category": "paper simulation",
            "source_type": paper.source_type,
            "use": "shape/peak/diagnostic error comparison",
        },
        {
            "reference": "simulated resonance",
            "value": f"~{float(block['simulated_peak_nm']):g} nm",
            "category": "paper simulation",
            "source_type": "paper text",
            "use": "peak-location comparison",
        },
        {
            "reference": "measured resonance",
            "value": f"~{float(block['measured_peak_nm']):g} nm",
            "category": "paper experiment",
            "source_type": "paper text",
            "use": "separate peak-location marker only",
        },
        {
            "reference": "ideal abrupt chi2 at 1550 nm",
            "value": f"~{float(block['ideal_abrupt_chi2_1550_pm_per_V']):g} pm/V",
            "category": "paper simulation",
            "source_type": "paper text, growth-interruption discussion",
            "use": "1550-nm point comparison with geometry caveat",
        },
    ]
