"""Demo 16E figures. Each one answers a stated question and none are decorative.

The set is deliberately small and repetitive: the same ten cases, the same ten
colours, the same growth axis, so a reader can move between composition,
localization and optical response without re-learning the picture each time.

Plotting goes through the shared ``plots`` module, so a broken matplotlib
degrades to a recorded skip rather than destroying a licensed run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import plots
import plots16b

TARGET_NM = 1550.0

#: One colour per case, fixed for the whole demo.
CASE_COLOURS = (
    "#1f4e79", "#c0392b", "#2f855a", "#d45500", "#7b3f98",
    "#0f7b8a", "#8a6d1f", "#b5316a", "#3a6ea5", "#5c8a2f",
)
#: Cycled with the colours so ten curves stay separable in print and greyscale.
CASE_STYLES = ("-", "--", "-", "--", "-", "--", "-", "--", "-", ":")

STATE_COLOURS = {
    "E1": "#c0392b", "E2": "#e08214", "HH1": "#2e7d32", "HH2": "#5fa85f",
}
REGION_COLOURS = {
    "left": "#4a90c4", "barrier": "#e0a458", "right": "#7ec4a4", "outside": "#c9c9c9",
}


def _style(index: int) -> dict[str, Any]:
    return {
        "color": CASE_COLOURS[index % len(CASE_COLOURS)],
        "linestyle": CASE_STYLES[index % len(CASE_STYLES)],
    }


def _label(row: Mapping[str, Any]) -> str:
    return f"{row['case']} {row.get('name', '')}".strip()


def case_title(case: Any, subject: str) -> str:
    """``Case 07 - Asymmetric Grading: Composition``.

    One place so the per-case composition and wavefunction figures are titled the
    same way, and so ``case_07``/``asymmetric_grading`` read as prose.
    """

    number = case.case_id.rsplit("_", 1)[-1]
    name = case.name.replace("_", " ").title()
    return f"Case {number} - {name}: {subject}"


def _finite(rows: Sequence[Mapping[str, Any]], key: str) -> list[Mapping[str, Any]]:
    return [row for row in rows if row.get(key) is not None]


def _units(rows: Sequence[Mapping[str, Any]]) -> str:
    for row in rows:
        if row.get("chi2_units"):
            return str(row["chi2_units"])
    return "production units"


# ---------------------------------------------------------------------------
# Per-case figures
# ---------------------------------------------------------------------------


def composition_figure(path: Path, **kwargs: Any) -> Path | None:
    """Intended vs realized ``x_Al(z)`` for one case; the shared Demo 16B figure."""

    return plots16b.composition_figure(Path(path), **kwargs)


def wavefunction_figure(
    path: Path,
    *,
    title: str,
    interfaces: Mapping[str, float],
    intended_x_nm: Sequence[float],
    intended_al: Sequence[float],
    band_position_nm: Sequence[float],
    band_edges: Mapping[str, Sequence[float]],
    state_x_nm: Sequence[float],
    electron_energies_eV: Sequence[float],
    electron_densities: Any,
    hole_energies_eV: Sequence[float],
    hole_densities: Any,
    localization: Mapping[str, Mapping[str, Any]] | None = None,
    max_al_fraction: float = 0.55,
) -> Path | None:
    """Composition and band edges, then electrons, then heavy holes.

    Three stacked panels rather than one. Electron and heavy-hole eigenvalues sit
    about 1.5 eV apart on nextnano++'s scale, so drawing both on one energy axis
    compresses each band's 100 meV of structure into invisibility -- which is
    exactly the structure the figure exists to show.
    """

    if not plots.plotting_available():
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])
    margin = max(2.5, 0.30 * (z4 - z1))
    lo, hi = z1 - margin, z4 + margin

    fig, (top, mid, low) = plt.subplots(
        3, 1, figsize=(7.8, 9.4), sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.15, 1.15]},
    )

    plots16b._shade_layers(top, interfaces)
    top.plot(intended_x_nm, intended_al, color="#1f4e79", lw=1.8,
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
            edge_ax.plot(band_position_nm, values, color=colour, lw=1.5, label=label)
    edge_ax.set_ylabel("band edge (eV)")
    handles = top.get_legend_handles_labels()[0] + edge_ax.get_legend_handles_labels()[0]
    labels = top.get_legend_handles_labels()[1] + edge_ax.get_legend_handles_labels()[1]
    edge_ax.legend(handles, labels, loc="center right", fontsize=7.5, framealpha=0.9)
    top.set_title(title, pad=20)

    x = np.asarray(state_x_nm, dtype=float)

    def band_panel(ax, energies, densities, prefix: str, band_title: str) -> None:
        plots16b._shade_layers(ax, interfaces, label=False)
        values = np.asarray(densities, dtype=float)
        count = min(2, len(energies), values.shape[1] if values.ndim == 2 else 0)
        if count <= 0:
            ax.annotate("no states available", xy=(0.5, 0.5),
                        xycoords="axes fraction", ha="center", fontsize=9)
            return
        levels = [float(energies[i]) for i in range(count)]
        peak = float(np.max(np.abs(values[:, :count]))) or 1.0
        span = abs(max(levels) - min(levels))
        scale = 0.55 * (span if span > 1e-4 else 0.05) / peak
        for index in range(count):
            label = f"{prefix}{index + 1}"
            colour = STATE_COLOURS[label]
            ax.axhline(levels[index], color=colour, lw=0.7, ls=":", alpha=0.7)
            ax.plot(x, levels[index] + scale * values[:, index], color=colour, lw=1.6)
            annotation = label
            if localization and label in localization:
                state = localization[label]
                annotation = (
                    f"{label}  L={state['localization']:+.2f}  "
                    f"({state['left_probability']:.2f}/"
                    f"{state['barrier_probability']:.2f}/"
                    f"{state['right_probability']:.2f})"
                )
            ax.annotate(annotation, xy=(lo + 0.3, levels[index]), fontsize=7.5,
                        color=colour, va="bottom")
        pad = 0.30 * (span if span > 1e-4 else 0.05)
        ax.set_ylim(min(levels) - pad, max(levels) + 1.1 * pad + 0.55 * (span or 0.05))
        ax.set_ylabel(f"{band_title} energy (eV)")

    band_panel(mid, list(electron_energies_eV), electron_densities, "E", "electron")
    band_panel(low, list(hole_energies_eV), hole_densities, "HH", "heavy-hole")
    low.set_xlim(lo, hi)
    low.set_xlabel("position $z$ (nm)")
    fig.subplots_adjust(bottom=0.10, top=0.93, hspace=0.14)
    fig.text(
        0.5, 0.015,
        plots.DISPLAY_OFFSET_NOTE + "  L = P_left - P_right; the bracket is "
        "(P_left / P_barrier / P_right).",
        ha="center", fontsize=7, color="#444444", wrap=True,
    )
    return plots.save_figure(fig, Path(path), tight=False)


# ---------------------------------------------------------------------------
# Combined structural figures
# ---------------------------------------------------------------------------


def composition_all_cases(
    path: Path, entries: Sequence[Mapping[str, Any]]
) -> Path | None:
    """All ten intended profiles on one growth axis.

    Question: how differently is aluminium distributed across the ten structures?
    """

    if not plots.plotting_available() or not entries:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9.6, 8.6), gridspec_kw={"height_ratios": [1.0, 1.0]}
    )
    handles = []
    for index, entry in enumerate(entries):
        case = entry["case"]
        style = _style(index)
        for ax in (top, bottom):
            line, = ax.plot(entry["x_nm"], entry["al_fraction"], lw=1.7, alpha=0.9,
                            label=f"{case.case_id} {case.name}", **style)
        handles.append(line)
    reference = entries[0]["interfaces"]
    z1 = float(reference["outer_left_algaas_to_gaas"])
    z4 = float(reference["outer_right_gaas_to_algaas"])
    top.set_xlim(z1 - 2.0, z4 + 2.0)
    top.set_ylim(-0.01, 0.59)
    top.set_ylabel("aluminium fraction $x_{Al}$")
    top.set_title("Aluminium Composition of All Ten Structures")

    centre = float(reference["central_gaas_to_algaas"])
    other = float(reference["central_algaas_to_gaas"])
    bottom.set_xlim(centre - 2.6, other + 2.6)
    bottom.set_ylim(-0.01, 0.59)
    bottom.set_xlabel("position $z$ (nm)")
    bottom.set_ylabel("aluminium fraction $x_{Al}$")
    bottom.set_title("Central Barrier, Magnified", fontsize=10)
    # A legend inside either panel lands on top of a curve: ten profiles leave no
    # empty corner. It goes under the figure instead.
    fig.legend(handles, [line.get_label() for line in handles], fontsize=8,
               ncol=4, loc="lower center", framealpha=0.92)
    fig.subplots_adjust(bottom=0.16, hspace=0.30, top=0.94)
    return plots.save_figure(fig, Path(path), tight=False)


# ---------------------------------------------------------------------------
# Energy figures
# ---------------------------------------------------------------------------


def energy_levels_all_cases(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> Path | None:
    """Question: where do the four state energies sit in each structure?"""

    rows = _finite(rows, "E1_eV")
    if not plots.plotting_available() or not rows:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    labels = [row["case"] for row in rows]
    x = np.arange(len(labels), dtype=float)
    fig, (electrons, holes) = plt.subplots(2, 1, figsize=(9.4, 6.8), sharex=True)
    width = 0.36
    for offset, key, label in ((-0.5, "E1_eV", "E1"), (0.5, "E2_eV", "E2")):
        electrons.bar(x + offset * width, [row[key] for row in rows], width,
                      label=label, color=STATE_COLOURS[label])
    for offset, key, label in ((-0.5, "HH1_eV", "HH1"), (0.5, "HH2_eV", "HH2")):
        holes.bar(x + offset * width, [row.get(key) for row in rows], width,
                  label=label, color=STATE_COLOURS[label])
    for ax, title in (
        (electrons, "Electron States"), (holes, "Heavy-Hole States"),
    ):
        ax.set_ylabel("energy (eV)")
        ax.set_title(title, fontsize=10)
        ax.legend(ncol=2, fontsize=8)
        ax.grid(axis="y", alpha=0.25)
    lowest = min(min(row["E1_eV"], row["E2_eV"]) for row in rows)
    highest = max(max(row["E1_eV"], row["E2_eV"]) for row in rows)
    electrons.set_ylim(lowest - 0.05, highest + 0.05)
    hole_values = [row[k] for row in rows for k in ("HH1_eV", "HH2_eV")
                   if row.get(k) is not None]
    if hole_values:
        holes.set_ylim(min(hole_values) - 0.05, max(hole_values) + 0.05)
    holes.set_xticks(x, labels, rotation=30, ha="right")
    # A figure-level title, so both panels keep their own: the electron panel's
    # title used to be overwritten by the figure's and was never visible.
    fig.suptitle("Quantum State Energies by Case", fontsize=11)
    return plots.save_figure(fig, Path(path))


def energy_shifts_vs_reference(
    path: Path, rows: Sequence[Mapping[str, Any]], reference_case: str
) -> Path | None:
    """Question: how far does each structure move the states from the reference?"""

    rows = [row for row in rows
            if row.get("delta_E1_meV_vs_reference") is not None]
    if not plots.plotting_available() or not rows:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    labels = [row["case"] for row in rows]
    x = np.arange(len(labels), dtype=float)
    width = 0.2
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    for offset, label in ((-1.5, "E1"), (-0.5, "E2"), (0.5, "HH1"), (1.5, "HH2")):
        values = [row.get(f"delta_{label}_meV_vs_reference") or 0.0 for row in rows]
        ax.bar(x + offset * width, values, width, label=label,
               color=STATE_COLOURS[label])
    ax.axhline(0.0, color="#222222", lw=1.0)
    ax.set_xticks(x, labels, rotation=30, ha="right")
    ax.set_ylabel(f"energy shift vs {reference_case} (meV)")
    ax.set_title(f"State-Energy Shifts Relative to {reference_case}")
    ax.legend(ncol=4, fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    return plots.save_figure(fig, Path(path))


# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------


def localization_all_cases(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> Path | None:
    """Question: which well does each state live in, in each structure?"""

    rows = _finite(rows, "E1_localization")
    if not plots.plotting_available() or not rows:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    labels = [row["case"] for row in rows]
    y = np.arange(len(labels), dtype=float)
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 8.0), sharey=True)
    for ax, state in zip(axes.ravel(), ("E1", "E2", "HH1", "HH2")):
        left = np.array([row.get(f"{state}_left_probability") or 0.0 for row in rows])
        barrier = np.array([row.get(f"{state}_barrier_probability") or 0.0 for row in rows])
        right = np.array([row.get(f"{state}_right_probability") or 0.0 for row in rows])
        outside = np.array([row.get(f"{state}_outside_probability") or 0.0 for row in rows])
        base = np.zeros_like(left)
        for values, key, label in (
            (left, "left", "well 1 (left)"), (barrier, "barrier", "central barrier"),
            (right, "right", "well 2 (right)"), (outside, "outside", "outer barriers"),
        ):
            ax.barh(y, values, left=base, height=0.62, color=REGION_COLOURS[key],
                    label=label, edgecolor="white", linewidth=0.5)
            base = base + values
        for index, row in enumerate(rows):
            value = row.get(f"{state}_localization")
            if value is not None:
                ax.annotate(f"L={value:+.2f}", xy=(1.015, y[index]),
                            xycoords=("axes fraction", "data"), va="center",
                            fontsize=7.5, color="#333333")
        ax.set_xlim(0.0, 1.0)
        ax.set_title(state, fontsize=11)
    axes[0, 0].set_yticks(y, labels, fontsize=8)
    # Once, not per axis: the four panels share one y axis, so four inversions
    # would cancel and case_01 would end up at the bottom.
    axes[0, 0].invert_yaxis()
    for ax in axes[1]:
        ax.set_xlabel("probability")
    handles, labels_text = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles[:4], labels_text[:4], fontsize=8, ncol=4,
               loc="lower center", framealpha=0.92)
    fig.suptitle("Wavefunction Localization by Layer", fontsize=11)
    fig.subplots_adjust(left=0.08, right=0.92, top=0.90, bottom=0.13, wspace=0.34,
                        hspace=0.30)
    return plots.save_figure(fig, Path(path), tight=False)


# ---------------------------------------------------------------------------
# Optical figures
# ---------------------------------------------------------------------------


def _spectrum(row: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
    path = row.get("spectrum_path")
    if not path or not Path(path).is_file():
        return None
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return np.asarray(data[:, 0], dtype=float), np.asarray(data[:, 3], dtype=float)


def chi2_wavelength_all_cases(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> Path | None:
    """Question: what does each structure's calculated chi2 spectrum look like?

    No normalisation: the actual computed magnitudes are drawn, because how far
    apart the ten responses are is one of the things being compared.
    """

    rows = _finite(rows, "chi2_at_1550")
    if not plots.plotting_available() or not rows:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10.6, 6.0))
    drawn = 0
    for index, row in enumerate(rows):
        spectrum = _spectrum(row)
        if spectrum is None:
            continue
        wavelength, magnitude = spectrum
        style = _style(index)
        ax.plot(wavelength, magnitude, lw=1.8, alpha=0.95, label=_label(row), **style)
        ax.scatter([TARGET_NM], [row["chi2_at_1550"]], s=30, zorder=5,
                   color=style["color"], edgecolor="white", linewidth=0.6)
        peak_nm = row.get("peak_wavelength_nm")
        peak_value = row.get("peak_chi2")
        if peak_nm is not None and peak_value is not None:
            ax.scatter([peak_nm], [peak_value], s=26, marker="^", zorder=5,
                       color=style["color"], alpha=0.75)
        drawn += 1
    if not drawn:
        plt.close(fig)
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None
    ax.axvline(TARGET_NM, color="#222222", ls="--", lw=1.5)
    ax.annotate("1550 nm", xy=(TARGET_NM, 1.0), xycoords=("data", "axes fraction"),
                xytext=(4, -12), textcoords="offset points", fontsize=9,
                color="#222222")
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel(f"absolute $|\\chi^{{(2)}}|$ ({_units(rows)})")
    ax.set_title("Nonlinear Optical Response Near 1550 nm")
    ax.legend(fontsize=7.5, ncol=2, framealpha=0.92)
    ax.grid(alpha=0.2)
    return plots.save_figure(fig, Path(path))


#: Three readable groups for the crowded ten-curve comparison. Each group holds
#: the reference plus the cases that vary one thing away from it.
SPECTRUM_GROUPS = (
    ("Central Barrier and Interfaces", ("case_01", "case_02", "case_03", "case_04")),
    ("Well Asymmetry", ("case_01", "case_05", "case_06")),
    ("Grading Width and Representation",
     ("case_01", "case_07", "case_08", "case_09", "case_10")),
)


def chi2_wavelength_grouped(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> Path | None:
    """The same spectra, split into three legible panels."""

    rows = _finite(rows, "chi2_at_1550")
    if not plots.plotting_available() or not rows:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    order = {row["case"]: index for index, row in enumerate(rows)}
    by_case = {row["case"]: row for row in rows}
    fig, axes = plt.subplots(len(SPECTRUM_GROUPS), 1, figsize=(9.4, 10.4), sharex=True)
    for ax, (title, case_ids) in zip(np.atleast_1d(axes), SPECTRUM_GROUPS):
        for case_id in case_ids:
            row = by_case.get(case_id)
            if row is None:
                continue
            spectrum = _spectrum(row)
            if spectrum is None:
                continue
            style = _style(order[case_id])
            ax.plot(spectrum[0], spectrum[1], lw=1.8, label=_label(row), **style)
            ax.scatter([TARGET_NM], [row["chi2_at_1550"]], s=28, zorder=5,
                       color=style["color"], edgecolor="white", linewidth=0.6)
        ax.axvline(TARGET_NM, color="#222222", ls="--", lw=1.3)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(f"$|\\chi^{{(2)}}|$ ({_units(rows)})")
        ax.legend(fontsize=7.5, framealpha=0.92)
        ax.grid(alpha=0.2)
    np.atleast_1d(axes)[-1].set_xlabel("wavelength (nm)")
    fig.suptitle(
        "Nonlinear Optical Response by Structural Variation", fontsize=11
    )
    return plots.save_figure(fig, Path(path))


def chi2_at_1550_all_cases(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> Path | None:
    """Question: how large is the calculated response at exactly 1550 nm?"""

    rows = _finite(rows, "chi2_at_1550")
    if not plots.plotting_available() or not rows:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    labels = [row["case"] for row in rows]
    values = [float(row["chi2_at_1550"]) for row in rows]
    colours = [CASE_COLOURS[index % len(CASE_COLOURS)] for index in range(len(rows))]
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    bars = ax.bar(labels, values, color=colours)
    for bar, row in zip(bars, rows):
        ax.annotate(f"{row['chi2_at_1550']:.3g}",
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=7.5, color="#333333")
    ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
    ax.set_ylabel(f"absolute $|\\chi^{{(2)}}|$ at 1550 nm ({_units(rows)})")
    ax.set_title("Nonlinear Optical Response at 1550 nm")
    ax.grid(axis="y", alpha=0.25)
    return plots.save_figure(fig, Path(path))


def peak_wavelength_and_detuning(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> Path | None:
    """Question: where does each structure's spectral peak sit relative to 1550 nm?"""

    rows = _finite(rows, "peak_wavelength_nm")
    if not plots.plotting_available() or not rows:
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    labels = [row["case"] for row in rows]
    peaks = [float(row["peak_wavelength_nm"]) for row in rows]
    detunings = [float(row.get("detuning_from_1550_nm") or 0.0) for row in rows]
    colours = [CASE_COLOURS[index % len(CASE_COLOURS)] for index in range(len(rows))]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(9.4, 7.4), sharex=True)
    top.scatter(range(len(labels)), peaks, s=70, color=colours, zorder=4)
    top.axhline(TARGET_NM, color="#222222", ls="--", lw=1.4, label="1550 nm")
    top.set_ylabel("spectral peak wavelength (nm)")
    top.legend(fontsize=8)
    top.grid(axis="y", alpha=0.25)
    bottom.bar(labels, detunings, color=colours)
    bottom.axhline(0.0, color="#222222", lw=1.2)
    bottom.set_ylabel("detuning (nm)")
    bottom.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
    bottom.grid(axis="y", alpha=0.25)
    fig.suptitle(
        "Spectral Peak Position and Detuning from 1550 nm", fontsize=11
    )
    return plots.save_figure(fig, Path(path))


# ---------------------------------------------------------------------------
# Pairwise comparison figures
# ---------------------------------------------------------------------------


def abrupt_vs_graded(
    path: Path, graded: Mapping[str, Any], abrupt: Mapping[str, Any],
    profiles: Mapping[str, Mapping[str, Any]],
) -> Path | None:
    """Question: what does grading a fixed layer stack actually change?"""

    if not plots.plotting_available():
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.6))
    composition, energies, localization, spectra = axes.ravel()

    entry = profiles.get(graded["case"]) or profiles.get(abrupt["case"])
    if entry is not None:
        plots16b._shade_layers(composition, entry["interfaces"], label=False)
    for row, colour, label in (
        (graded, "#1f4e79", "graded"), (abrupt, "#c0392b", "abrupt"),
    ):
        profile = profiles.get(row["case"])
        if profile is None:
            continue
        composition.plot(profile["x_nm"], profile["al_fraction"], lw=1.9,
                         color=colour, label=f"{row['case']} {label}")
    if entry is not None:
        z1 = float(entry["interfaces"]["outer_left_algaas_to_gaas"])
        z4 = float(entry["interfaces"]["outer_right_gaas_to_algaas"])
        composition.set_xlim(z1 - 1.6, z4 + 1.6)
    composition.set_ylim(-0.01, 0.59)
    composition.set_xlabel("position $z$ (nm)")
    composition.set_ylabel("$x_{Al}$")
    composition.set_title("Composition", fontsize=10)
    composition.legend(fontsize=8)

    states = ("E1", "E2", "HH1", "HH2")
    x = np.arange(len(states), dtype=float)
    shifts = [
        (float(graded[f"{s}_eV"]) - float(abrupt[f"{s}_eV"])) * 1000.0
        if graded.get(f"{s}_eV") is not None and abrupt.get(f"{s}_eV") is not None
        else 0.0
        for s in states
    ]
    energies.bar(x, shifts, 0.55, color=[STATE_COLOURS[s] for s in states])
    energies.axhline(0.0, color="#222222", lw=1.0)
    energies.set_xticks(x, states)
    energies.set_ylabel("graded - abrupt (meV)")
    energies.set_title("State-Energy Shift from Grading", fontsize=10)
    energies.grid(axis="y", alpha=0.25)

    width = 0.36
    for offset, row, colour, label in (
        (-0.5, graded, "#1f4e79", "graded"), (0.5, abrupt, "#c0392b", "abrupt"),
    ):
        localization.bar(
            x + offset * width,
            [row.get(f"{s}_localization") or 0.0 for s in states],
            width, color=colour, label=label,
        )
    localization.axhline(0.0, color="#222222", lw=1.0)
    localization.set_xticks(x, states)
    localization.set_ylabel("L = $P_{left} - P_{right}$")
    localization.set_title("Localization", fontsize=10)
    localization.legend(fontsize=8)
    localization.grid(axis="y", alpha=0.25)

    for row, colour, label in (
        (graded, "#1f4e79", "graded"), (abrupt, "#c0392b", "abrupt"),
    ):
        spectrum = _spectrum(row)
        if spectrum is None:
            continue
        spectra.plot(spectrum[0], spectrum[1], lw=1.8, color=colour,
                     label=f"{row['case']} {label}")
        if row.get("chi2_at_1550") is not None:
            spectra.scatter([TARGET_NM], [row["chi2_at_1550"]], s=30, color=colour,
                            zorder=5, edgecolor="white", linewidth=0.6)
    spectra.axvline(TARGET_NM, color="#222222", ls="--", lw=1.3)
    spectra.set_xlabel("wavelength (nm)")
    spectra.set_ylabel(f"$|\\chi^{{(2)}}|$ ({_units([graded, abrupt])})")
    spectra.set_title("Optical Response", fontsize=10)
    spectra.legend(fontsize=8)
    spectra.grid(alpha=0.2)

    fig.suptitle(
        f"Abrupt vs Graded Interfaces: {abrupt['case']} vs {graded['case']}",
        fontsize=11,
    )
    return plots.save_figure(fig, Path(path))


def native_vs_imported(
    path: Path, report: Mapping[str, Any], native: Mapping[str, Any],
    imported: Mapping[str, Any],
) -> Path | None:
    """Question: do two encodings of one profile give one answer?

    Every bar is drawn against its own tolerance line, so passing and failing are
    visible rather than asserted.
    """

    if not plots.plotting_available():
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(12.4, 4.6))
    energy_ax, local_ax, optical_ax = axes

    states = ("E1", "E2", "HH1", "HH2")
    x = np.arange(len(states), dtype=float)

    def budget_panel(ax, deltas, budget: float, ylabel: str, title: str) -> None:
        ax.bar(x, deltas, 0.55, color=[STATE_COLOURS[s] for s in states])
        for sign in (1.0, -1.0):
            ax.axhline(sign * budget, color="#b22222", ls=":", lw=1.2)
        ax.axhline(0.0, color="#222222", lw=1.0)
        ax.set_xticks(x, states)
        ax.set_ylabel(ylabel)
        # The limit follows the data when a difference exceeds its budget, so a
        # failure is read off the figure rather than clipped out of it.
        reach = max(1.6 * budget, 1.25 * max(abs(value) for value in deltas or [0.0]))
        ax.set_ylim(-reach, reach)
        ax.set_title(title, fontsize=10)

    budget_panel(
        energy_ax,
        [report["energy_differences_meV"].get(f"delta_{s}_meV") or 0.0 for s in states],
        report["tolerances"]["energy_eV"] * 1000.0,
        "imported - native (meV)",
        f"State Energies (Budget {report['tolerances']['energy_eV'] * 1000.0:g} meV)",
    )
    budget_panel(
        local_ax,
        [report["localization_differences"].get(f"delta_{s}_localization") or 0.0
         for s in states],
        report["tolerances"]["localization_probability"],
        "imported - native",
        f"Localization (Budget {report['tolerances']['localization_probability']:g})",
    )

    for row, colour, label in (
        (native, "#1f4e79", "native ternary_linear"),
        (imported, "#c0392b", "imported table"),
    ):
        spectrum = _spectrum(row)
        if spectrum is None:
            continue
        optical_ax.plot(spectrum[0], spectrum[1], lw=2.0 if colour == "#1f4e79" else 1.2,
                        ls="-" if colour == "#1f4e79" else "--", color=colour,
                        label=f"{row['case']} {label}")
    optical_ax.axvline(TARGET_NM, color="#222222", ls="--", lw=1.2)
    optical_ax.set_xlabel("wavelength (nm)")
    optical_ax.set_ylabel(f"$|\\chi^{{(2)}}|$ ({_units([native, imported])})")
    relative = report.get("chi2_at_1550_relative_difference")
    optical_ax.set_title(
        "$\\chi^{(2)}$ Spectra"
        + ("" if relative is None else f" (1550 nm Differs by {relative:.2%})"),
        fontsize=10,
    )
    optical_ax.legend(fontsize=8)

    verdict = "PASS" if report["checks"]["passed"] else "FAIL"
    fig.suptitle(
        f"Native vs Imported Rendering: Equivalence {verdict}", fontsize=11
    )
    return plots.save_figure(fig, Path(path))
