"""Demo 16B figures. Two kinds, and no more.

**Composition** -- one per case: intended ``x_Al(z)`` against nextnano++'s
realized ``x_Al(z)``, with the three layers shaded. This is the picture that
answers "did nextnano++ build what Python asked for?" and it is drawn even when
Level 2 has not run, so the intended structure can be inspected anywhere.

**Physics** -- one per solved case: band edges above, states below. Split into
two stacked panels rather than one overlay because a conduction edge in eV and a
composition in dimensionless Al fraction do not share an axis, and forcing them
onto one makes both unreadable.

Plotting goes through the shared ``plots`` module so a broken matplotlib
degrades to a recorded skip rather than destroying a licensed run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import plots

#: Layer shading. Wells light, barrier darker, so the eye reads the stack before
#: it reads the curves.
_WELL_COLOUR = "#dbe9f6"
_BARRIER_COLOUR = "#f5e2c8"


def _layer_spans(interfaces: Mapping[str, float]) -> list[tuple[str, float, float, str]]:
    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])
    return [
        ("well 1", z1, z2, _WELL_COLOUR),
        ("barrier", z2, z3, _BARRIER_COLOUR),
        ("well 2", z3, z4, _WELL_COLOUR),
    ]


def _shade_layers(ax, interfaces: Mapping[str, float], *, label: bool = True) -> None:
    for name, lo, hi, colour in _layer_spans(interfaces):
        ax.axvspan(lo, hi, color=colour, zorder=0)
        if label:
            ax.annotate(
                name, xy=(0.5 * (lo + hi), 1.02), xycoords=("data", "axes fraction"),
                ha="center", va="bottom", fontsize=8, color="#444444",
            )


def composition_figure(
    path: Path,
    *,
    title: str,
    interfaces: Mapping[str, float],
    intended_x_nm: Sequence[float],
    intended_al: Sequence[float],
    realized_x_nm: Sequence[float] | None = None,
    realized_al: Sequence[float] | None = None,
    max_al_fraction: float = 0.55,
    note: str = "",
) -> Path | None:
    """Plot type 1: intended vs realized Al fraction with the layers marked."""

    if not plots.plotting_available():
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])
    margin = max(3.0, 0.35 * (z4 - z1))

    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    _shade_layers(ax, interfaces)
    ax.plot(intended_x_nm, intended_al, color="#1f4e79", lw=2.0,
            label="Python intended $x_{Al}(z)$")
    if realized_x_nm is not None and realized_al is not None and len(realized_x_nm):
        ax.plot(realized_x_nm, realized_al, color="#c0392b", lw=1.2, ls="--",
                label="nextnano++ realized $x_{Al}(z)$")
    for _name, lo, hi, _c in _layer_spans(interfaces):
        for edge in (lo, hi):
            ax.axvline(edge, color="#888888", lw=0.6, ls=":", zorder=1)
    ax.set_xlim(z1 - margin, z4 + margin)
    ax.set_ylim(-0.02 * max_al_fraction, 1.12 * max_al_fraction)
    ax.set_xlabel("position $z$ (nm)")
    ax.set_ylabel("aluminium fraction $x_{Al}$")
    ax.set_title(title, pad=18)
    ax.legend(loc="center right", fontsize=8, framealpha=0.9)
    if note:
        ax.annotate(note, xy=(0.01, 0.02), xycoords="axes fraction",
                    fontsize=7.5, color="#333333")
    return plots.save_figure(fig, Path(path))


def physics_figure(
    path: Path,
    *,
    title: str,
    interfaces: Mapping[str, float],
    intended_x_nm: Sequence[float],
    intended_al: Sequence[float],
    position_nm: Sequence[float],
    band_edges: Mapping[str, Sequence[float]],
    state_x_nm: Sequence[float],
    electron_energies_eV: Sequence[float],
    electron_densities: Any,
    hole_energies_eV: Sequence[float],
    hole_densities: Any = None,
    max_states: int = 2,
    max_al_fraction: float = 0.55,
) -> Path | None:
    """Plot type 2: composition + band edges above, states below.

    Probability densities are scaled and shifted onto their own eigenenergies for
    display. That offset is a visualisation choice, not an energy -- the shared
    ``plots.DISPLAY_OFFSET_NOTE`` says so on the figure.
    """

    if not plots.plotting_available():
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])
    margin = max(3.0, 0.35 * (z4 - z1))
    lo, hi = z1 - margin, z4 + margin

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(7.6, 7.4), sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.35]},
    )

    # --- top: composition and band edges ------------------------------------
    _shade_layers(top, interfaces)
    top.plot(intended_x_nm, intended_al, color="#1f4e79", lw=1.6,
             label="intended $x_{Al}(z)$")
    top.set_ylabel("$x_{Al}$", color="#1f4e79")
    top.set_ylim(-0.02 * max_al_fraction, 1.12 * max_al_fraction)
    top.tick_params(axis="y", labelcolor="#1f4e79")

    edge_ax = top.twinx()
    for key, colour, label in (
        ("conduction_eV", "#c0392b", "$\\Gamma$ conduction edge"),
        ("heavy_hole_eV", "#2e7d32", "heavy-hole edge"),
    ):
        values = band_edges.get(key)
        if values is not None and len(values):
            edge_ax.plot(position_nm, values, color=colour, lw=1.6, label=label)
    edge_ax.set_ylabel("band edge (eV)")
    handles = top.get_legend_handles_labels()[0] + edge_ax.get_legend_handles_labels()[0]
    labels = top.get_legend_handles_labels()[1] + edge_ax.get_legend_handles_labels()[1]
    edge_ax.legend(handles, labels, loc="center right", fontsize=8, framealpha=0.9)
    top.set_title(title, pad=18)

    # --- bottom: states on their eigenenergies -------------------------------
    _shade_layers(bottom, interfaces, label=False)
    x = np.asarray(state_x_nm, dtype=float)

    def draw(energies: Sequence[float], densities: Any, colour: str, tag: str) -> None:
        if densities is None:
            return
        values = np.asarray(densities, dtype=float)
        if values.ndim != 2 or values.size == 0:
            return
        count = min(int(max_states), len(energies), values.shape[1])
        if count <= 0:
            return
        peak = float(np.max(np.abs(values[:, :count]))) or 1.0
        span = abs(float(np.max(energies[:count])) - float(np.min(energies[:count])))
        scale = 0.35 * (span if span > 1e-6 else 0.15) / peak
        for index in range(count):
            energy = float(energies[index])
            bottom.axhline(energy, color=colour, lw=0.6, ls=":", alpha=0.6)
            bottom.plot(x, energy + scale * values[:, index], color=colour, lw=1.4)
            bottom.annotate(f"{tag}{index + 1}", xy=(lo + 0.4, energy),
                            fontsize=8, color=colour, va="bottom")

    draw(list(electron_energies_eV), electron_densities, "#c0392b", "e")
    draw(list(hole_energies_eV), hole_densities, "#2e7d32", "hh")
    bottom.set_xlim(lo, hi)
    bottom.set_xlabel("position $z$ (nm)")
    bottom.set_ylabel("energy (eV)")
    fig.subplots_adjust(bottom=0.14, top=0.92, hspace=0.12)
    fig.text(0.5, 0.02, plots.DISPLAY_OFFSET_NOTE, ha="center", fontsize=7.5,
             color="#444444", wrap=True)
    return plots.save_figure(fig, Path(path), tight=False)
