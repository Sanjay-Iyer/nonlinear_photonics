"""Plot helpers shared by Demos 4-10.

Two conventions are enforced here rather than left to each demo:

* every requested figure is written even when there is no solver data yet, as a
  clearly labelled placeholder, so a missing plot always means a bug and never
  "this machine has no licence";
* a wavefunction amplitude, a probability density, and an energy are never
  silently mixed.  The one figure that draws densities on an energy axis states
  in the axis label *and* on the figure that the offset is for display only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PLACEHOLDER_TEXT = "No licensed solver data on this machine yet"
DISPLAY_OFFSET_NOTE = (
    "Curves are scaled |psi|^2 shifted onto each eigenenergy for display only; "
    "the vertical offset is a visualisation choice, not an energy of the state."
)


def _finish(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def save_figure(fig: plt.Figure, path: Path) -> Path:
    """Save a custom demo figure with the same layout and DPI conventions."""

    return _finish(fig, path)


def placeholder(path: Path, title: str, *, reason: str = PLACEHOLDER_TEXT) -> Path:
    """A labelled empty figure, so the plot set is always complete."""

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.text(0.5, 0.5, reason, ha="center", va="center", transform=ax.transAxes, wrap=True)
    ax.set(title=title, xticks=[], yticks=[])
    return _finish(fig, path)


def line_plot(
    path: Path,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    series: Mapping[str, tuple[Sequence[float], Sequence[float]]],
    markers: bool = True,
    axhline: float | None = None,
    logy: bool = False,
) -> Path:
    """One or more x/y series; falls back to a placeholder when all are empty."""

    usable = {
        name: (list(x), list(y))
        for name, (x, y) in series.items()
        if len(x) and len(y) and len(x) == len(y)
    }
    if not usable:
        return placeholder(path, title)
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    for name, (x, y) in usable.items():
        order = np.argsort(np.asarray(x, dtype=float))
        ax.plot(
            np.asarray(x, dtype=float)[order],
            np.asarray(y, dtype=float)[order],
            "o-" if markers else "-",
            label=name,
        )
    if axhline is not None:
        ax.axhline(axhline, color="0.6", linewidth=0.8, linestyle="--")
    if logy:
        ax.set_yscale("log")
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    if len(usable) > 1:
        ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.25)
    return _finish(fig, path)


def band_diagram(
    path: Path,
    *,
    title: str,
    position_nm: Sequence[float],
    conduction_eV: Sequence[float],
    energies_eV: Sequence[float] = (),
    regions: Mapping[str, tuple[float, float]] | None = None,
    extra_bands: Mapping[str, Sequence[float]] | None = None,
) -> Path:
    """Conduction-band profile with horizontal eigenenergy lines."""

    if not len(position_nm) or not len(conduction_eV):
        return placeholder(path, title)
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    for name, bounds in (regions or {}).items():
        if "well" in name or "core" in name:
            ax.axvspan(bounds[0], bounds[1], color="0.90", zorder=-2)
    ax.plot(position_nm, conduction_eV, color="black", linewidth=1.4, label="Γ conduction edge")
    for name, values in (extra_bands or {}).items():
        if len(values) == len(position_nm):
            ax.plot(position_nm, values, linewidth=1.0, alpha=0.8, label=name)
    for index, energy in enumerate(energies_eV, start=1):
        ax.axhline(float(energy), color="tab:blue", linewidth=0.9, alpha=0.75)
        ax.annotate(
            f"E{index}",
            xy=(float(position_nm[0]), float(energy)),
            xytext=(2, 2),
            textcoords="offset points",
            fontsize=7,
            color="tab:blue",
        )
    ax.set(xlabel="Position (nm)", ylabel="Energy (eV)", title=title)
    ax.legend(fontsize=8)
    return _finish(fig, path)


def envelope_plot(
    path: Path,
    *,
    title: str,
    position_nm: Sequence[float],
    envelopes: np.ndarray,
    regions: Mapping[str, tuple[float, float]] | None = None,
) -> Path:
    """Signed envelope amplitudes psi_i(z), in nm^-1/2. Not a probability."""

    array = np.atleast_2d(np.asarray(envelopes, dtype=float))
    if array.size == 0 or not len(position_nm):
        return placeholder(path, title)
    if array.shape[0] != len(position_nm):
        array = array.T
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    for name, bounds in (regions or {}).items():
        if "well" in name or "core" in name:
            ax.axvspan(bounds[0], bounds[1], color="0.90", zorder=-2)
    for index in range(array.shape[1]):
        ax.plot(position_nm, array[:, index], label=f"ψ{index + 1}")
    ax.axhline(0.0, color="0.5", linewidth=0.7)
    ax.set(
        xlabel="Position (nm)",
        ylabel="Envelope amplitude ψ (nm$^{-1/2}$)",
        title=title,
    )
    ax.legend(fontsize=8, ncol=2)
    return _finish(fig, path)


def density_plot(
    path: Path,
    *,
    title: str,
    position_nm: Sequence[float],
    densities: np.ndarray,
    regions: Mapping[str, tuple[float, float]] | None = None,
) -> Path:
    """Normalised probability densities |psi_i|^2, in 1/nm."""

    array = np.atleast_2d(np.asarray(densities, dtype=float))
    if array.size == 0 or not len(position_nm):
        return placeholder(path, title)
    if array.shape[0] != len(position_nm):
        array = array.T
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    for name, bounds in (regions or {}).items():
        if "well" in name or "core" in name:
            ax.axvspan(bounds[0], bounds[1], color="0.90", zorder=-2)
    for index in range(array.shape[1]):
        ax.plot(position_nm, array[:, index], label=f"|ψ{index + 1}|²")
    ax.set(
        xlabel="Position (nm)",
        ylabel="Normalised probability density (nm$^{-1}$)",
        title=title,
    )
    ax.legend(fontsize=8, ncol=2)
    return _finish(fig, path)


def band_with_display_offsets(
    path: Path,
    *,
    title: str,
    position_nm: Sequence[float],
    conduction_eV: Sequence[float],
    energies_eV: Sequence[float],
    densities: np.ndarray,
    regions: Mapping[str, tuple[float, float]] | None = None,
) -> Path:
    """Band edge with |psi|^2 drawn on top of each eigenenergy, clearly labelled."""

    array = np.atleast_2d(np.asarray(densities, dtype=float))
    if array.size == 0 or not len(position_nm) or not len(energies_eV):
        return placeholder(path, title)
    if array.shape[0] != len(position_nm):
        array = array.T
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    for name, bounds in (regions or {}).items():
        if "well" in name or "core" in name:
            ax.axvspan(bounds[0], bounds[1], color="0.90", zorder=-2)
    ax.plot(position_nm, conduction_eV, color="black", linewidth=1.4, label="Γ conduction edge")
    span = float(np.nanmax(conduction_eV) - np.nanmin(conduction_eV))
    height = max(0.02, 0.18 * span)
    for index, energy in enumerate(energies_eV[: array.shape[1]]):
        density = array[:, index]
        peak = float(np.max(np.abs(density))) or 1.0
        ax.plot(
            position_nm,
            float(energy) + height * density / peak,
            linewidth=1.0,
            label=f"E{index + 1} + display-scaled |ψ|²",
        )
        ax.axhline(float(energy), color="0.7", linewidth=0.6)
    ax.set(
        xlabel="Position (nm)",
        ylabel="Energy (eV) — density curves carry a display offset",
        title=title,
    )
    ax.text(0.01, 0.015, DISPLAY_OFFSET_NOTE, transform=ax.transAxes, fontsize=6.5, wrap=True)
    ax.legend(fontsize=7, ncol=2)
    return _finish(fig, path)


def heatmap(
    path: Path,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    x_values: Sequence[float],
    y_values: Sequence[float],
    values: np.ndarray,
    colorbar_label: str = "",
    annotate: bool = False,
) -> Path:
    """2D map of a scalar over two swept parameters, or a matrix-element table."""

    array = np.asarray(values, dtype=float)
    if array.size == 0 or not len(x_values) or not len(y_values):
        return placeholder(path, title)
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    mesh = ax.imshow(
        array,
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        extent=(
            float(np.min(x_values)),
            float(np.max(x_values)),
            float(np.min(y_values)),
            float(np.max(y_values)),
        ),
    )
    bar = fig.colorbar(mesh, ax=ax)
    if colorbar_label:
        bar.set_label(colorbar_label)
    if annotate and array.size <= 64:
        xs = np.linspace(float(np.min(x_values)), float(np.max(x_values)), array.shape[1])
        ys = np.linspace(float(np.min(y_values)), float(np.max(y_values)), array.shape[0])
        for row in range(array.shape[0]):
            for column in range(array.shape[1]):
                value = array[row, column]
                if np.isfinite(value):
                    ax.text(
                        xs[column],
                        ys[row],
                        f"{value:.3g}",
                        ha="center",
                        va="center",
                        fontsize=6,
                        color="white",
                    )
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    return _finish(fig, path)


def matrix_heatmap(
    path: Path,
    *,
    title: str,
    matrix: np.ndarray,
    labels: Sequence[str],
    colorbar_label: str,
) -> Path:
    """Square state-to-state matrix (overlaps, |z_ij|, transition strengths)."""

    array = np.asarray(matrix, dtype=float)
    if array.size == 0:
        return placeholder(path, title)
    fig, ax = plt.subplots(figsize=(5.6, 4.8))
    mesh = ax.imshow(array, origin="upper", interpolation="nearest")
    fig.colorbar(mesh, ax=ax).set_label(colorbar_label)
    ax.set_xticks(range(len(labels)), labels, fontsize=8)
    ax.set_yticks(range(len(labels)), labels, fontsize=8)
    for row in range(array.shape[0]):
        for column in range(array.shape[1]):
            value = array[row, column]
            if np.isfinite(value):
                ax.text(
                    column,
                    row,
                    f"{value:.3g}",
                    ha="center",
                    va="center",
                    fontsize=6.5,
                    color="white",
                )
    ax.set(title=title)
    return _finish(fig, path)


def rectangular_heatmap(
    path: Path,
    *,
    title: str,
    matrix: np.ndarray,
    xlabels: Sequence[str],
    ylabels: Sequence[str],
    xlabel: str,
    ylabel: str,
    colorbar_label: str,
) -> Path:
    """Heat map whose row and column labels represent different state sets."""

    array = np.asarray(matrix, dtype=float)
    if array.size == 0:
        return placeholder(path, title)
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    mesh = ax.imshow(array, origin="upper", interpolation="nearest", aspect="auto")
    fig.colorbar(mesh, ax=ax).set_label(colorbar_label)
    ax.set_xticks(range(len(xlabels)), xlabels, fontsize=8)
    ax.set_yticks(range(len(ylabels)), ylabels, fontsize=8)
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    for row in range(array.shape[0]):
        for column in range(array.shape[1]):
            value = array[row, column]
            if np.isfinite(value):
                ax.text(
                    column,
                    row,
                    f"{value:.3g}",
                    ha="center",
                    va="center",
                    fontsize=6.5,
                    color="white",
                )
    return _finish(fig, path)


def bar_plot(
    path: Path,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    labels: Sequence[str],
    values: Sequence[float],
    excluded: Sequence[bool] | None = None,
) -> Path:
    """Ranking bar chart; excluded candidates are drawn hatched, never removed."""

    if not len(labels) or not len(values):
        return placeholder(path, title)
    fig, ax = plt.subplots(figsize=(max(6.4, 0.45 * len(labels)), 4.4))
    flags = list(excluded or [False] * len(labels))
    colors = ["tab:red" if flag else "tab:blue" for flag in flags]
    bars = ax.bar(range(len(labels)), [float(value) for value in values], color=colors)
    for bar, flag in zip(bars, flags):
        if flag:
            bar.set_hatch("//")
    ax.set_xticks(range(len(labels)), labels, rotation=70, fontsize=6.5, ha="right")
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    if any(flags):
        ax.text(
            0.99,
            0.97,
            "hatched red = excluded from ranking (see exclusion_reasons)",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=7,
        )
    return _finish(fig, path)


def map_2d(
    path: Path,
    *,
    title: str,
    x_nm: Sequence[float],
    y_nm: Sequence[float],
    values: np.ndarray,
    colorbar_label: str,
    contours: Mapping[str, tuple[tuple[float, float], tuple[float, float]]] | None = None,
) -> Path:
    """A 2D cross-section map, optionally outlining named rectangles."""

    array = np.asarray(values, dtype=float)
    if array.size == 0 or not len(x_nm) or not len(y_nm):
        return placeholder(path, title)
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    mesh = ax.pcolormesh(np.asarray(x_nm, dtype=float), np.asarray(y_nm, dtype=float), array)
    fig.colorbar(mesh, ax=ax).set_label(colorbar_label)
    for name, (xs, ys) in (contours or {}).items():
        ax.plot(
            [xs[0], xs[1], xs[1], xs[0], xs[0]],
            [ys[0], ys[0], ys[1], ys[1], ys[0]],
            color="white",
            linewidth=1.1,
            label=name,
        )
    ax.set(xlabel="x (nm)", ylabel="y (nm)", title=title, aspect="equal")
    if contours:
        ax.legend(fontsize=7, loc="upper right")
    return _finish(fig, path)


def write_all(
    plots_dir: Path, specs: Sequence[tuple[str, str]], *, reason: str = PLACEHOLDER_TEXT
) -> list[Path]:
    """Emit placeholders for a demo's full figure set in one call."""

    return [
        placeholder(plots_dir / filename, title, reason=reason) for filename, title in specs
    ]


def ensure_plot_set(
    plots_dir: Path, specs: Sequence[tuple[str, str]], *, reason: str = PLACEHOLDER_TEXT
) -> list[str]:
    """Fill in any figure of a demo's declared set that was not produced.

    A demo's README promises a specific list of figures. Emitting a labelled
    placeholder for the missing ones means a truly absent file is always a bug,
    never "no licence on this machine".
    """

    plots_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for filename, title in specs:
        target = plots_dir / filename
        if not target.is_file():
            placeholder(target, title, reason=reason)
            created.append(filename)
    return created


def summarise_plots(plots_dir: Path) -> dict[str, Any]:
    """Manifest fragment describing which figures a run produced."""

    files = sorted(path.name for path in plots_dir.glob("*.png"))
    return {"plot_count": len(files), "plots": files}
