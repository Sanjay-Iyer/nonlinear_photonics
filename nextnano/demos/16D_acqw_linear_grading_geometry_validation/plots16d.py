"""Small, descriptive plot set for Demo 16D."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import plots
import plots16b


def composition_figure(path: Path, *, overlap_region=None, **kwargs: Any) -> Path | None:
    result = plots16b.composition_figure(Path(path), **kwargs)
    if result is None or not overlap_region:
        return result
    # The shared plot already carries both scientifically relevant curves. The
    # overlap interval is additionally retained in comparison_metrics.json and
    # is made unmistakable in the dedicated comparison plot below.
    return result


def _shade_stack(ax, interfaces: Mapping[str, float]) -> None:
    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])
    for label, lo, hi, colour in (
        ("well 1", z1, z2, "#dbe9f6"),
        ("barrier", z2, z3, "#f5e2c8"),
        ("well 2", z3, z4, "#dbe9f6"),
    ):
        ax.axvspan(lo, hi, color=colour, alpha=0.42, zorder=0)
        ax.annotate(label, ((lo + hi) / 2, 0.98), xycoords=("data", "axes fraction"),
                    ha="center", va="top", fontsize=8, color="#555555")


def barrier_comparison(path: Path, profiles: Sequence[Mapping[str, Any]]) -> Path | None:
    if not plots.plotting_available():
        return None
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    colours = ("#2878b5", "#d45500", "#2f855a")
    for colour, entry in zip(colours, profiles):
        case = entry["case"]
        ax.plot(entry["x_nm"], entry["al_fraction"], lw=2, color=colour,
                label=f"{case.case_id}: {case.central_barrier_nm:.2f} nm")
    _shade_stack(ax, profiles[1]["interfaces"])
    z2 = min(float(entry["interfaces"]["central_gaas_to_algaas"]) for entry in profiles)
    z3 = max(float(entry["interfaces"]["central_algaas_to_gaas"]) for entry in profiles)
    ax.set_xlim(z2 - 2.0, z3 + 2.0)
    ax.set_ylim(-0.01, 0.59)
    ax.set_xlabel("Position (nm)")
    ax.set_ylabel("Al fraction")
    ax.set_title("Demo 16D: central-barrier thickness comparison")
    ax.legend()
    return plots.save_figure(fig, Path(path))


def asymmetry_comparison(path: Path, profiles: Sequence[Mapping[str, Any]]) -> Path | None:
    if not plots.plotting_available():
        return None
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    colours = ("#2878b5", "#d45500", "#7b3f98")
    for colour, entry in zip(colours, profiles):
        case = entry["case"]
        w1, w2 = case.well_widths_nm()
        ax.plot(entry["x_nm"], entry["al_fraction"], lw=2, color=colour,
                label=f"{case.case_id}: s={case.asymmetry_s:.2f}, wells {w1:.2f}/{w2:.2f} nm")
    ax.set_xlim(2.0, max(float(p["interfaces"]["outer_right_gaas_to_algaas"]) for p in profiles) + 2.0)
    ax.set_ylim(-0.01, 0.59)
    ax.set_xlabel("Position (nm)")
    ax.set_ylabel("Al fraction")
    ax.set_title("Demo 16D: fixed-total well-asymmetry comparison")
    ax.legend(fontsize=8)
    return plots.save_figure(fig, Path(path))


def overlap_comparison(path: Path, entry: Mapping[str, Any]) -> Path | None:
    if not plots.plotting_available():
        return None
    import matplotlib.pyplot as plt

    case = entry["case"]
    overlap = entry["overlap"]
    interfaces = entry["interfaces"]
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    ax.plot(entry["x_nm"], entry["al_fraction"], color="#7b3f98", lw=2.2,
            label="authoritative linear-overlap profile")
    ax.axhline(0.55, color="#555555", ls=":", label="nominal Al fraction 0.55")
    ax.axhline(0.90 * 0.55, color="#999999", ls="--", label="90% of nominal")
    ax.axvspan(overlap["overlap_start_nm"], overlap["overlap_end_nm"],
               color="#f3bf4f", alpha=0.28, label="overlapping ramp interval")
    ax.axvline(z2, color="#555555", lw=0.8)
    ax.axvline(z3, color="#555555", lw=0.8)
    ax.scatter([overlap["peak_position_nm"]], [overlap["expected_peak_al_fraction"]],
               color="#b22222", zorder=5, label=f"peak {overlap['expected_peak_al_fraction']:.3f}")
    ax.set_xlim(z2 - 1.4, z3 + 1.4)
    ax.set_ylim(-0.01, 0.59)
    ax.set_xlabel("Position (nm)")
    ax.set_ylabel("Al fraction")
    ax.set_title(f"{case.case_id}: overlap without a fabricated Al0.55 plateau")
    ax.legend(fontsize=8)
    return plots.save_figure(fig, Path(path))


def physics_energy_summary(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path | None:
    if not plots.plotting_available() or not rows:
        return None
    import matplotlib.pyplot as plt

    labels = [row["case_id"] for row in rows]
    x = np.arange(len(labels), dtype=float)
    width = 0.19
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for offset, key, label, colour in (
        (-1.5, "E1_eV", "E1", "#2878b5"),
        (-0.5, "E2_eV", "E2", "#6baed6"),
        (0.5, "HH1_eV", "HH1", "#d45500"),
        (1.5, "HH2_eV", "HH2", "#f4a261"),
    ):
        ax.bar(x + offset * width, [row[key] for row in rows], width, label=label, color=colour)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Energy (eV)")
    ax.set_title("Demo 16D: verified nextnano++ quantum energies")
    ax.legend(ncol=4)
    return plots.save_figure(fig, Path(path))


def optical_comparison(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path | None:
    if not plots.plotting_available() or not rows:
        return None
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    colours = ("#2878b5", "#d45500", "#2f855a", "#7b3f98")
    units = rows[0].get("chi2_units") or "production units"
    for colour, row in zip(colours, rows):
        data = np.loadtxt(row["spectrum_path"], delimiter=",", skiprows=1)
        ax.plot(data[:, 0], data[:, 3], lw=2, color=colour,
                label=f"{row['case_id']} — {row['description']}")
        ax.scatter([1550.0], [row["chi2_at_1550"]], color=colour, s=28, zorder=5)
    ax.axvline(1550.0, color="#222222", ls="--", lw=1.4, label="1550 nm")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel(f"Absolute chi2 response ({units})")
    ax.set_title("Demo 16D: fixed-case optical response near 1550 nm")
    ax.legend(fontsize=8)
    return plots.save_figure(fig, Path(path))


def optical_at_1550(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path | None:
    if not plots.plotting_available() or not rows:
        return None
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    labels = [row["case_id"] for row in rows]
    values = [row["chi2_at_1550"] for row in rows]
    ax.bar(labels, values, color=("#2878b5", "#d45500", "#2f855a", "#7b3f98"))
    ax.set_xlabel("Fixed validation case")
    ax.set_ylabel(f"Absolute chi2 at 1550 nm ({rows[0].get('chi2_units') or 'production units'})")
    ax.set_title("Demo 16D: descriptive 1550 nm comparison")
    return plots.save_figure(fig, Path(path))
