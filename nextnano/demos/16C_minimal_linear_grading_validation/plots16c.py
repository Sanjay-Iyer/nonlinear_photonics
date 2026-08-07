"""The two composition figures Demo 16C needs, and no physics dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import plots
import plots16b


def case_composition_figure(path: Path, **kwargs: Any) -> Path | None:
    """Reuse Demo 16B's intended-vs-realized composition figure."""

    return plots16b.composition_figure(Path(path), **kwargs)


def all_intended_profiles_figure(
    path: Path,
    profiles: Sequence[Mapping[str, Any]],
) -> Path | None:
    """Overlay the four intended profiles so the width change is immediate."""

    if not plots.plotting_available():
        plots.SKIPPED_FIGURES.append(Path(path).name)
        return None

    import matplotlib.pyplot as plt

    colours = ("#1f4e79", "#2e7d32", "#c77700", "#9b2c2c")
    styles = ("-", "--", "-.", ":")
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    for index, entry in enumerate(profiles):
        case = entry["case"]
        label = (
            f"{case.case_id}: left {case.left_grading_width_nm:.2f} nm, "
            f"right {case.right_grading_width_nm:.2f} nm"
        )
        ax.plot(
            entry["x_nm"], entry["al_fraction"],
            color=colours[index % len(colours)],
            ls=styles[index % len(styles)], lw=1.8, label=label,
        )

    interfaces = profiles[0]["interfaces"]
    z1 = float(interfaces["outer_left_algaas_to_gaas"])
    z2 = float(interfaces["central_gaas_to_algaas"])
    z3 = float(interfaces["central_algaas_to_gaas"])
    z4 = float(interfaces["outer_right_gaas_to_algaas"])
    for name, lo, hi, colour in (
        ("well 1", z1, z2, "#dbe9f6"),
        ("central barrier", z2, z3, "#f5e2c8"),
        ("well 2", z3, z4, "#dbe9f6"),
    ):
        ax.axvspan(lo, hi, color=colour, alpha=0.55, zorder=0)
        ax.annotate(name, xy=((lo + hi) / 2, 0.985),
                    xycoords=("data", "axes fraction"), ha="center",
                    va="top", fontsize=8, color="#444444")

    margin = max(3.0, 0.35 * (z4 - z1))
    ax.set_xlim(z1 - margin, z4 + margin)
    ax.set_ylim(-0.01, 0.61)
    ax.set_xlabel("Position (nm)")
    ax.set_ylabel("Al fraction")
    ax.set_title("Demo 16C: changing only the linear grading width")
    ax.legend(loc="center right", fontsize=8, framealpha=0.92)
    return plots.save_figure(fig, Path(path))
