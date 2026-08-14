"""Boss-facing plots for Demo 19. Every plotted physics point is solver-derived."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import cases19
import demo19


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _finish(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    _plt().close(fig)
    return path


def input_plots(destination: Path) -> list[Path]:
    plt = _plt()
    destination = Path(destination)
    by_id = {case.case_id: case for case in cases19.all_cases()}
    z = np.linspace(7.5, 22.5, 6001)

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    for case_id, label in (("00", "Abrupt"), ("02", "0.4 nm"), ("03", "0.7 nm"),
                           ("04", "1.0 nm"), ("05", "1.4 nm")):
        ax.plot(z, demo19.evaluate_composition(by_id[case_id], z, rendered=True), label=label, lw=1.8)
    ax.set(xlabel="Position z (nm)", ylabel="Al fraction $x_{Al}$", title="Interface Grading Profiles")
    ax.set_ylim(-0.025, 0.575)
    ax.legend(frameon=False, ncol=3)
    ax.grid(alpha=0.18)
    first = _finish(fig, destination / "01_grading_composition_profiles.png")

    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    u = np.linspace(-0.55, 0.55, 2001)
    centre = demo19.interface_positions()["I2"]
    for case_id, label in (("00", "Abrupt"), ("03", "Linear"), ("10", "Fermi"),
                           ("11", "erf"), ("12", "Cosine")):
        ax.plot(u, demo19.evaluate_composition(by_id[case_id], centre + u, rendered=True), label=label, lw=2)
    ax.set(xlabel="Position relative to interface (nm)", ylabel="Al fraction $x_{Al}$", title="Grading Profile Shape")
    ax.set_ylim(-0.025, 0.575)
    ax.legend(frameon=False)
    ax.grid(alpha=0.18)
    second = _finish(fig, destination / "02_grading_profile_shapes.png")
    return [first, second]


def _read_rows(path: Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _number(row: Mapping[str, Any], key: str) -> float:
    value = row.get(key)
    return float(value) if value not in (None, "") else float("nan")


def _bar(path: Path, labels: Sequence[str], values: Sequence[float], title: str, ylabel: str) -> Path:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    ax.bar(np.arange(len(labels)), values, color="#3b73a8")
    ax.set_xticks(np.arange(len(labels)), labels, rotation=20, ha="right")
    ax.set(title=title, ylabel=ylabel)
    ax.grid(axis="y", alpha=0.18)
    return _finish(fig, path)


def physics_plots(root: Path, rows: list[dict[str, Any]], spectra: Mapping[str, tuple[np.ndarray, np.ndarray]]) -> list[Path]:
    plt = _plt()
    root = Path(root)
    plots = root / "plots"
    by_id = {str(row["case_id"]): row for row in rows}
    made: list[Path] = []

    # 03 is produced only when the runner persisted the two wavefunction bundles.
    wave_paths = [root / "cases" / f"case_{case_id}" / "wavefunctions_plot_data.csv" for case_id in ("00", "03")]
    if all(path.is_file() for path in wave_paths):
        fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True, sharey=True)
        for ax, path, label in zip(axes, wave_paths, ("Abrupt", "0.7 nm")):
            data = np.genfromtxt(path, delimiter=",", names=True)
            ax.plot(data["z_nm"], data["conduction_eV"], color="black", lw=1.2)
            ax.plot(data["z_nm"], data["heavy_hole_eV"], color="0.35", lw=1.2)
            for key, color in (("E1", "#1f77b4"), ("E2", "#4fa3df"), ("HH1", "#d62728"), ("HH2", "#ff7f7f")):
                ax.plot(data["z_nm"], data[key], color=color, lw=1.0, label=key)
            ax.text(0.01, 0.90, label, transform=ax.transAxes)
            ax.grid(alpha=0.15)
        axes[0].legend(frameon=False, ncol=4)
        axes[-1].set_xlabel("Position z (nm)")
        fig.supylabel("Energy / scaled probability (eV)")
        fig.suptitle("Abrupt vs 0.7 nm Grading")
        made.append(_finish(fig, plots / "03_abrupt_vs_graded_wavefunctions.png"))

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for case_id, label in (("00", "Abrupt"), ("02", "0.4 nm"), ("03", "0.7 nm"),
                           ("04", "1.0 nm"), ("05", "1.4 nm")):
        if case_id in spectra:
            ax.plot(*spectra[case_id], label=label, lw=1.8)
    ax.axvline(1550, color="black", ls="--", lw=1)
    ax.set(xlabel="Wavelength (nm)", ylabel="$|\\chi^{(2)}|$ (pm/V)", title="Grading Dependence of $\\chi^2$")
    ax.legend(frameon=False)
    ax.grid(alpha=0.18)
    made.append(_finish(fig, plots / "04_chi2_spectra_linear_grading.png"))

    sequence = ["00", "01", "02", "03", "04", "05"]
    widths = [_number(by_id[c], "nominal_grade_width_nm") for c in sequence]
    chi = [_number(by_id[c], "chi2_1550_pm_per_V") for c in sequence]
    relative = [_number(by_id[c], "chi2_1550_relative_to_abrupt") for c in sequence]
    peaks = [_number(by_id[c], "peak_wavelength_nm") for c in sequence]
    for filename, values, ylabel, title in (
        ("05_grade_width_vs_chi2_1550.png", chi, "$|\\chi^2(1550)|$ (pm/V)", "$\\chi^2$ vs Grading Width"),
        ("06_grade_width_relative_to_abrupt.png", relative, "$\\chi^2(1550)$ / Abrupt $\\chi^2(1550)$", "Relative Response to Abrupt"),
        ("07_grade_width_vs_peak_wavelength.png", peaks, "Peak wavelength (nm)", "Peak Wavelength vs Grading"),
    ):
        fig, ax = plt.subplots(figsize=(7.2, 4.5))
        ax.plot(widths, values, marker="o", lw=1.8)
        if filename.startswith("06_"):
            ax.axhline(1.0, color="black", ls="--", lw=1)
        ax.set(xlabel="Grading width (nm)", ylabel=ylabel, title=title)
        ax.grid(alpha=0.18)
        made.append(_finish(fig, plots / filename))

    loc_ids = ["00", "08", "09", "06", "07"]
    loc_labels = ["Abrupt", "Inner-only", "Outer-only", "I2=.4 / I3=.8", "I2=.8 / I3=.4"]
    made.append(_bar(plots / "08_grading_location_comparison.png", loc_labels,
                     [_number(by_id[c], "chi2_1550_pm_per_V") for c in loc_ids],
                     "Effect of Grading Location", "$|\\chi^2(1550)|$ (pm/V)"))

    shape_ids = ["03", "10", "11", "12"]
    made.append(_bar(plots / "09_profile_shape_chi2_comparison.png",
                     ["Linear 0.7", "Fermi 0.7", "erf 0.7", "Cosine 0.7"],
                     [_number(by_id[c], "chi2_1550_pm_per_V") for c in shape_ids],
                     "Effect of Grading Profile", "$|\\chi^2(1550)|$ (pm/V)"))

    heat_keys = ("E2_HH2_eV", "O22", "z_e12_nm", "z_hh12_nm", "chi2_1550_pm_per_V", "peak_wavelength_nm")
    matrix = np.asarray([[_number(row, key) for key in heat_keys] for row in rows], dtype=float)
    if matrix.size and np.all(np.isfinite(matrix)):
        span = np.ptp(matrix, axis=0)
        normalized = (matrix - np.min(matrix, axis=0)) / np.where(span == 0, 1, span)
        fig, ax = plt.subplots(figsize=(8.2, 6.0))
        image = ax.imshow(normalized, aspect="auto", cmap="viridis")
        ax.set_xticks(range(len(heat_keys)), ["E2-HH2", "O22", "z_e12", "z_hh12", "chi2", "peak nm"])
        ax.set_yticks(range(len(rows)), [row["case_id"] for row in rows])
        ax.set(title="Grading Summary")
        fig.colorbar(image, ax=ax, label="Column-normalized value")
        made.append(_finish(fig, plots / "10_grading_summary_heatmap.png"))
    return made
