"""Simple diagnostic plots for Demo 18C."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _finish(fig: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _scatter(
    rows: Sequence[Mapping[str, Any]], x_name: str, xlabel: str, path: Path,
) -> Path:
    valid = [row for row in rows if bool(row.get("physical_valid"))]
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ax.scatter([float(row[x_name]) for row in valid],
               [float(row["chi2_1550_pm_per_V"]) for row in valid], s=34)
    ax.axhline(2340.0, color="black", linestyle="--", linewidth=1, label="Paper")
    ax.set(xlabel=xlabel, ylabel=r"$|\chi^{(2)}(1550)|$ (pm/V)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    return _finish(fig, path)


def generate_all(
    output_dir: Path, rows: Sequence[Mapping[str, Any]],
    ranked: Sequence[Mapping[str, Any]], spectra: Mapping[str, Mapping[str, np.ndarray]],
    selected_spectrum_ids: Sequence[str],
) -> list[Path]:
    output_dir = Path(output_dir)
    labels = [str(row["combo_id"]).replace("Combo_", "") for row in rows]
    values = [float(row["chi2_1550_pm_per_V"]) if bool(row.get("physical_valid")) else np.nan
              for row in rows]
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    ax.bar(labels, values, color="#4472C4")
    ax.axhline(2340.0, color="black", linestyle="--", linewidth=1.2, label="Paper")
    ax.set(xlabel="Combination", ylabel=r"$|\chi^{(2)}(1550)|$ (pm/V)", title="Demo 18C ensemble")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    paths.append(_finish(fig, output_dir / "01_combo_results.png"))

    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    rank_labels = [str(row["combo_id"]).replace("Combo_", "") for row in ranked]
    ax.bar(rank_labels, [float(row["chi2_1550_pm_per_V"]) for row in ranked], color="#70AD47")
    ax.axhline(2340.0, color="black", linestyle="--", linewidth=1.2, label="Paper")
    ax.set(xlabel="Best to worst", ylabel=r"$|\chi^{(2)}(1550)|$ (pm/V)", title="Closeness to paper")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    paths.append(_finish(fig, output_dir / "02_ranked_closeness.png"))

    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(10.0, 4.8))
    ax.plot(x, [float(row.get("chi_e_real", np.nan)) for row in rows], "o-", label="Electron")
    ax.plot(x, [float(row.get("chi_hh_weighted_real", np.nan)) for row in rows], "o-", label="Weighted HH")
    ax.plot(x, [float(row.get("chi_total_real", np.nan)) for row in rows], "o-", label="Net")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set(xticks=x, xticklabels=labels, xlabel="Combination",
           ylabel="Real contribution (pm/V)", title="Electron-HH cancellation")
    ax.legend(frameon=False, ncol=3)
    ax.grid(alpha=0.2)
    paths.append(_finish(fig, output_dir / "03_electron_hh_net.png"))

    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    ax.bar(labels, [float(row.get("cancellation_factor", np.nan)) for row in rows], color="#ED7D31")
    ax.set(xlabel="Combination", ylabel="Cancellation factor", title="Branch cancellation")
    ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.2)
    paths.append(_finish(fig, output_dir / "04_cancellation_factor.png"))

    paths.append(_scatter(rows, "r_e_hh_nm", r"$r_{e,hh}$ (nm)",
                          output_dir / "05_r_e_hh_vs_chi2.png"))
    paths.append(_scatter(rows, "electrostatic_field_kV_per_cm", "Electric field (kV/cm)",
                          output_dir / "06_field_vs_chi2.png"))
    paths.append(_scatter(rows, "hh_relative_weight", "HH relative weight",
                          output_dir / "07_hh_weight_vs_chi2.png"))
    paths.append(_scatter(rows, "tunneling_barrier_nm", "Tunneling barrier (nm)",
                          output_dir / "08_barrier_vs_chi2.png"))

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for combo_id in selected_spectrum_ids:
        spectrum = spectra[combo_id]
        label = "Demo 18B baseline" if combo_id == "Combo_00" else combo_id.replace("Combo_", "Combo ")
        ax.plot(spectrum["wavelength_nm"], np.abs(spectrum["chi_total"]), label=label)
    ax.scatter([1550.0], [2340.0], marker="*", s=90, color="black", label="Paper at 1550 nm")
    ax.set(xlabel="Wavelength (nm)", ylabel=r"$|\chi^{(2)}|$ (pm/V)", title="Best spectra")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(alpha=0.2)
    paths.append(_finish(fig, output_dir / "09_best_spectra.png"))
    return paths

