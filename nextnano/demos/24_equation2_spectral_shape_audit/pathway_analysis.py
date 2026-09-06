"""Equation-2 pathway subtotal and feature breakdown helpers."""

from __future__ import annotations

from typing import Iterable, Mapping

import numpy as np

from signed_spectrum import cancellation_metric, phase_difference_deg


def subtotals(result) -> tuple[np.ndarray, np.ndarray]:
    electron_mask = np.asarray([label.startswith("C_") for label in result.spectrum.term_labels])
    electron = np.sum(result.spectrum.terms[electron_mask], axis=0)
    heavy_hole_signed = np.sum(result.spectrum.terms[~electron_mask], axis=0)
    return electron, heavy_hole_signed


def cancellation_rows(result, feature_rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    e, h = subtotals(result)
    x = result.spectrum.wavelength_nm
    rows = []
    for feature in feature_rows:
        target = float(feature["Paper wavelength nm"])
        i = int(np.argmin(np.abs(x - target)))
        rows.append({
            "Feature": feature["Feature"], "wavelength_nm": float(x[i]),
            "electron_real": float(e[i].real), "electron_imag": float(e[i].imag),
            "electron_abs": float(abs(e[i])),
            "heavy_hole_signed_real": float(h[i].real), "heavy_hole_signed_imag": float(h[i].imag),
            "heavy_hole_signed_abs": float(abs(h[i])),
            "total_real": float((e[i] + h[i]).real), "total_imag": float((e[i] + h[i]).imag),
            "total_abs": float(abs(e[i] + h[i])),
            "phase_difference_deg": phase_difference_deg(e[i], h[i]),
            "cancellation_ratio": cancellation_metric(e[i], h[i]),
        })
    return rows


def feature_breakdown(result, feature_rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    x = result.spectrum.wavelength_nm
    rows: list[dict[str, object]] = []
    for feature in feature_rows:
        i = int(np.argmin(np.abs(x - float(feature["Paper wavelength nm"]))))
        values = result.spectrum.terms[:, i]
        group_totals = {
            "electron": sum(abs(v) for label, v in zip(result.spectrum.term_labels, values) if label.startswith("C_")),
            "heavy_hole_signed": sum(abs(v) for label, v in zip(result.spectrum.term_labels, values) if label.startswith("V_")),
        }
        order = np.argsort(np.abs(values))[::-1]
        rank = {int(index): position + 1 for position, index in enumerate(order)}
        for j, (label, value) in enumerate(zip(result.spectrum.term_labels, values)):
            group = "electron" if label.startswith("C_") else "heavy_hole_signed"
            denominator = max(float(group_totals[group]), 1e-300)
            rows.append({
                "Feature": feature["Feature"], "Wavelength": float(x[i]), "Pathway": label,
                "Real": float(value.real), "Imag": float(value.imag), "Magnitude": float(abs(value)),
                "Fraction of subtotal": float(abs(value) / denominator),
                "Sign": "positive" if value.real > 0 else "negative" if value.real < 0 else "zero",
                "Rank": rank[j], "Group": group,
            })
    return rows


def assert_consistency(result, atol: float = 1e-9) -> None:
    summed = np.sum(result.spectrum.terms, axis=0)
    if not np.allclose(summed, result.spectrum.chi2, rtol=1e-10, atol=atol):
        raise AssertionError("sum of 16 pathways does not equal total chi")
    e, h = subtotals(result)
    if not np.allclose(e + h, result.spectrum.chi2, rtol=1e-10, atol=atol):
        raise AssertionError("electron plus signed HH subtotal does not equal total chi")
