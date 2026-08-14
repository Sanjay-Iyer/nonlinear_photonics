"""Presentation-ready diagnostic plots for Demo 18D."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _save(fig: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def generate_all(
    output: Path, rows: Sequence[Mapping[str, Any]], ranked: Sequence[Mapping[str, Any]],
    spectra: Mapping[str, Mapping[str, np.ndarray]], selected_ids: Sequence[str],
    best_solved: Mapping[str, Any] | None,
) -> list[Path]:
    output = Path(output)
    valid = [row for row in rows if bool(row.get("physical_valid"))]
    labels = [str(row["case_id"]).replace("Case_", "") for row in rows]
    x = np.arange(len(rows))
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(9.4, 4.4))
    ax.bar(labels, [float(row.get("chi2_1550_pm_per_V", np.nan)) for row in rows])
    ax.axhline(2340.0, color="black", linestyle="--", label="Paper")
    ax.set(xlabel="Case", ylabel=r"$|\chi^{(2)}(1550)|$ (pm/V)", title="Demo 18D amplitude")
    ax.legend(frameon=False); ax.grid(axis="y", alpha=.2)
    paths.append(_save(fig, output / "01_chi2_1550_all_cases.png"))

    fig, ax = plt.subplots(figsize=(9.4, 4.4))
    ax.bar(labels, [float(row.get("peak_wavelength_nm", np.nan)) for row in rows])
    ax.axhspan(1520, 1560, alpha=.2, color="green", label="Target window")
    ax.set(xlabel="Case", ylabel="Dominant peak (nm)", title="Dominant spectral peak")
    ax.legend(frameon=False); ax.grid(axis="y", alpha=.2)
    paths.append(_save(fig, output / "02_peak_wavelength_all_cases.png"))

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    colors = ["#2ca02c" if bool(row["spectral_window_pass"]) else "#d62728" for row in valid]
    ax.scatter([float(row["peak_wavelength_nm"]) for row in valid],
               [float(row["chi2_1550_pm_per_V"]) for row in valid], c=colors)
    ax.axvspan(1520, 1560, alpha=.15, color="green"); ax.axhline(2340, color="black", linestyle="--")
    ax.set(xlabel="Dominant peak wavelength (nm)", ylabel=r"$|\chi^{(2)}(1550)|$ (pm/V)",
           title="Amplitude and spectral location")
    ax.grid(alpha=.2)
    paths.append(_save(fig, output / "03_amplitude_vs_peak_wavelength.png"))

    fig, ax = plt.subplots(figsize=(9.4, 4.4))
    ax.bar(labels, [float(row.get("combined_score", np.nan)) for row in rows], color="#9467bd")
    ax.set(xlabel="Case", ylabel="Combined score", title="Dual-objective score")
    ax.grid(axis="y", alpha=.2)
    paths.append(_save(fig, output / "04_combined_score.png"))

    fig, ax = plt.subplots(figsize=(10, 4.7))
    ax.plot(x, [float(row.get("chi_e_real", np.nan)) for row in rows], "o-", label="Electron")
    ax.plot(x, [float(row.get("chi_hh_real", np.nan)) for row in rows], "o-", label="HH")
    ax.plot(x, [float(row.get("chi_total_real", np.nan)) for row in rows], "o-", label="Net")
    ax.axhline(0, color="black", linewidth=.8)
    ax.set(xticks=x, xticklabels=labels, xlabel="Case", ylabel="Real contribution (pm/V)",
           title="Unweighted electron-HH contributions")
    ax.legend(frameon=False, ncol=3); ax.grid(alpha=.2)
    paths.append(_save(fig, output / "05_electron_hh_contributions.png"))

    fig, ax = plt.subplots(figsize=(9.4, 4.4))
    ax.bar(labels, [float(row.get("cancellation_factor", np.nan)) for row in rows], color="#ff7f0e")
    ax.set_yscale("log"); ax.set(xlabel="Case", ylabel="Cancellation factor", title="Electron-HH cancellation")
    ax.grid(axis="y", alpha=.2)
    paths.append(_save(fig, output / "06_cancellation_factor.png"))

    for index, key, label, filename in (
        (7, "electrostatic_field_kV_per_cm", "Field (kV/cm)", "07_field_vs_chi2.png"),
        (8, "tunneling_barrier_nm", "Tunneling barrier (nm)", "08_barrier_vs_chi2.png"),
    ):
        fig, ax = plt.subplots(figsize=(6.6, 4.4))
        ax.scatter([float(row[key]) for row in valid], [float(row["chi2_1550_pm_per_V"]) for row in valid])
        ax.axhline(2340, color="black", linestyle="--")
        ax.set(xlabel=label, ylabel=r"$|\chi^{(2)}(1550)|$ (pm/V)")
        ax.grid(alpha=.2)
        paths.append(_save(fig, output / filename))

    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    scatter = ax.scatter([float(row["well1_nm"]) for row in valid],
                         [float(row["well2_nm"]) for row in valid],
                         c=[float(row["chi2_1550_pm_per_V"]) for row in valid], cmap="viridis")
    fig.colorbar(scatter, ax=ax, label=r"$|\chi^{(2)}(1550)|$ (pm/V)")
    ax.set(xlabel="Thick well (nm)", ylabel="Thin well (nm)", title="Well geometry and amplitude")
    ax.grid(alpha=.2)
    paths.append(_save(fig, output / "09_well_geometry_vs_chi2.png"))

    fig, ax = plt.subplots(figsize=(7.3, 4.8))
    for case_id in selected_ids:
        sp = spectra[case_id]
        label = "Demo 18B baseline" if case_id == "Case_00" else case_id.replace("Case_", "Case ")
        ax.plot(sp["wavelength_nm"], np.abs(sp["chi_total"]), label=label)
    ax.scatter([1550], [2340], marker="*", s=90, color="black", label="Paper")
    ax.axvspan(1520, 1560, color="green", alpha=.08)
    ax.set(xlabel="Wavelength (nm)", ylabel=r"$|\chi^{(2)}|$ (pm/V)", title="Best physical spectra")
    ax.legend(frameon=False, fontsize=8); ax.grid(alpha=.2)
    paths.append(_save(fig, output / "10_best_spectra.png"))

    if best_solved is not None:
        data = best_solved["data"]
        fig, ax = plt.subplots(figsize=(8.2, 4.8))
        z_band = data.band_position_nm
        for key, color in (("conduction_eV", "black"), ("heavy_hole_eV", "gray")):
            if key in data.band_edges:
                ax.plot(z_band, data.band_edges[key], color=color, linewidth=1, label=key)
        scale = .035
        for index in range(2):
            ax.plot(data.electron.z_nm,
                    data.electron.energies_eV[index] + scale * data.electron.envelopes[:, index],
                    label=f"E{index + 1}")
            ax.plot(data.heavy_hole.z_nm,
                    data.heavy_hole.energies_eV[index] + scale * data.heavy_hole.envelopes[:, index],
                    label=f"HH{index + 1}")
        ax.set(xlabel="Growth coordinate (nm)", ylabel="Energy (eV)", title="Best candidate states")
        ax.legend(frameon=False, fontsize=8, ncol=3); ax.grid(alpha=.2)
        paths.append(_save(fig, output / "11_best_wavefunctions_and_bands.png"))
    return paths

