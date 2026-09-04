"""Publication-quality diagnostic plots for Demo 23."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import matplotlib.pyplot as plt
import numpy as np


COLORS = {"23A": "#6b7280", "23B": "#d97706", "23C": "#15803d", "23D": "#2563eb"}


def _finish(path: Path, *, xlabel: str, ylabel: str, title: str, dpi: int = 220) -> None:
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(alpha=0.25)
    handles, _ = plt.gca().get_legend_handles_labels()
    if handles:
        plt.legend(fontsize=8)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=int(dpi))
    plt.close()


def raw_dispersions(path: Path, k: np.ndarray, bands: Mapping[str, np.ndarray], dpi: int) -> None:
    plt.figure(figsize=(8.5, 5.0))
    for state in ("e1", "e2", "hh1", "hh2"):
        plt.plot(k, bands[state], label=state)
    _finish(path, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Energy (eV)",
            title="Tracked and k=0-aligned 8-band dispersions", dpi=dpi)


def fit_plot(path: Path, k: np.ndarray, raw: Mapping[str, np.ndarray], fits: Mapping[str, Any],
             states: tuple[str, ...], title: str, dpi: int) -> None:
    plt.figure(figsize=(8.5, 5.0))
    for state in states:
        plt.plot(k, raw[state], label=f"{state} kp8")
        plt.plot(k, fits[state].evaluate(k), "--", label=f"{state} parabola")
    _finish(path, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Energy (eV)", title=title, dpi=dpi)


def residual_plot(path: Path, k: np.ndarray, raw: Mapping[str, np.ndarray], fits: Mapping[str, Any],
                  states: tuple[str, ...], title: str, dpi: int) -> None:
    plt.figure(figsize=(8.5, 4.6))
    for state in states:
        plt.plot(k, 1000.0 * (raw[state] - fits[state].evaluate(k)), label=state)
    plt.axhline(0.0, color="black", linewidth=0.7)
    _finish(path, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Residual (meV)", title=title, dpi=dpi)


def transition_modes(path: Path, k: np.ndarray, mode_results: Mapping[str, Any], dpi: int) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    for axis, label in zip(axes.flat, ("DeltaE_11", "DeltaE_12", "DeltaE_21", "DeltaE_22")):
        for mode, result in mode_results.items():
            axis.plot(k, result.transitions.as_dict()[label], label=mode, color=COLORS[mode])
        axis.set_title(label.replace("DeltaE", r"$\Delta E$"))
        axis.grid(alpha=0.25)
    axes[1, 0].set_xlabel(r"$k_\parallel$ (nm$^{-1}$)")
    axes[1, 1].set_xlabel(r"$k_\parallel$ (nm$^{-1}$)")
    axes[0, 0].set_ylabel("Transition energy (eV)")
    axes[1, 0].set_ylabel("Transition energy (eV)")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Same-k transition-energy comparison")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)
    plt.close(fig)


def transition_mode_detail(path: Path, k: np.ndarray, result: Any, dpi: int) -> None:
    plt.figure(figsize=(8.5, 5.0))
    for label, values in result.transitions.as_dict().items():
        plt.plot(k, values, label=label)
    _finish(path, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Transition energy (eV)",
            title=f"{result.mode}: four same-k transitions", dpi=dpi)


def spectra(path: Path, results: Mapping[str, Any], dpi: int) -> None:
    plt.figure(figsize=(9.5, 5.2))
    for mode, result in results.items():
        plt.plot(result.spectrum.wavelength_nm, result.magnitude, label=mode, color=COLORS[mode])
    _finish(path, xlabel="Fundamental wavelength (nm)", ylabel=r"$|\chi^{(2)}|$ (pm/V)",
            title="Demo 23 controlled dispersion ladder", dpi=dpi)


def differences(path: Path, results: Mapping[str, Any], dpi: int) -> None:
    if "23D" not in results:
        return
    reference = results["23D"]
    plt.figure(figsize=(9.5, 5.2))
    denominator = np.maximum(reference.magnitude, 1e-12 * np.max(reference.magnitude))
    for mode, result in results.items():
        if mode == "23D":
            continue
        relative = 100.0 * (result.magnitude - reference.magnitude) / denominator
        plt.plot(result.spectrum.wavelength_nm, relative, label=f"{mode} - 23D", color=COLORS[mode])
    _finish(path, xlabel="Fundamental wavelength (nm)", ylabel="Relative magnitude error (%)",
            title="Difference from raw-kp8 energy-only reference", dpi=dpi)


def k_integrand(path: Path, k: np.ndarray, results: Mapping[str, Any], prefactor: float, dpi: int) -> None:
    plt.figure(figsize=(8.5, 5.0))
    for mode, result in results.items():
        iw = int(np.argmin(np.abs(result.spectrum.wavelength_nm - 1550.0)))
        contribution = prefactor * result.spectrum.summed_integrand[iw] * result.spectrum.k_weights
        plt.plot(k, np.abs(contribution), label=mode, color=COLORS[mode])
    _finish(path, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Per-node |contribution| (pm/V)",
            title=r"Weighted $k$ integrand at 1550 nm", dpi=dpi)


def convergence(path: Path, rows: list[dict[str, Any]], key: str, title: str, dpi: int) -> None:
    if not rows:
        return
    plt.figure(figsize=(8.5, 5.0))
    for mode in sorted({str(row["mode"]) for row in rows}):
        selected = sorted((row for row in rows if row["mode"] == mode), key=lambda row: float(row[key]))
        plt.plot([float(row[key]) for row in selected],
                 [float(row["chi2_1550_pm_per_V"]) for row in selected], "o-",
                 label=mode, color=COLORS[mode])
    _finish(path, xlabel=key.replace("_", " "), ylabel=r"$|\chi^{(2)}(1550)|$ (pm/V)",
            title=title, dpi=dpi)


def isotropy(path: Path, k: np.ndarray, differences_meV: Mapping[str, np.ndarray], dpi: int) -> None:
    if not differences_meV:
        return
    plt.figure(figsize=(8.5, 5.0))
    for state, values in differences_meV.items():
        plt.plot(k, values, label=state)
    _finish(path, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel=r"$E_y-E_{45^\circ}$ (meV)",
            title="In-plane dispersion anisotropy diagnostic", dpi=dpi)

