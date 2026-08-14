"""Compact required figures for Demo 18E."""

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
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_all(
    root: Path,
    selection_rows: Sequence[Mapping[str, Any]],
    rotation_rows: Sequence[Mapping[str, Any]],
    spectra: Mapping[str, Mapping[str, np.ndarray]],
    term_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    raw_state_data: Mapping[str, Any] | None,
) -> list[Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    labels = [str(row["state_selection"]) for row in selection_rows]
    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.15), 4.8))
    ax.plot(x, [float(r["chi_e_real"]) for r in selection_rows], "o-", label="electron")
    ax.plot(x, [float(r["chi_hh_real"]) for r in selection_rows], "o-", label="HH")
    ax.plot(x, [float(r["chi_total_real"]) for r in selection_rows], "o-", label="total")
    ax.axhline(0, color="black", lw=.7); ax.set_xticks(x, labels, rotation=28, ha="right")
    ax.set_ylabel("Real contribution at 1550 nm (pm/V)"); ax.legend()
    paths.append(_save(fig, root / "01_state_selection_branches.png"))

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.15), 4.8))
    ax.bar(x, [float(r["chi2_1550_pm_per_V"]) for r in selection_rows])
    ax.axhline(2340, color="black", ls="--", label="paper target")
    ax.set_xticks(x, labels, rotation=28, ha="right"); ax.set_ylabel("|chi2(1550)| (pm/V)")
    ax.legend(); paths.append(_save(fig, root / "02_chi2_1550_vs_state_selection.png"))

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.15), 4.8))
    ax.bar(x, [float(r["cancellation_factor"]) for r in selection_rows])
    ax.set_xticks(x, labels, rotation=28, ha="right"); ax.set_ylabel("Cancellation factor")
    paths.append(_save(fig, root / "03_cancellation_vs_state_selection.png"))

    fig, ax = plt.subplots(figsize=(8, 4.8))
    if raw_state_data is not None:
        z = np.asarray(raw_state_data["z_nm"], float)
        edges = raw_state_data.get("heavy_hole_edge_eV")
        if edges is not None:
            ax.plot(z, edges, color="black", lw=1.1, label="HH band edge")
        for label, energy, envelope in raw_state_data["hh23"]:
            env = np.asarray(envelope, float)
            scale = .08 / max(np.max(np.abs(env)), 1e-30)
            ax.plot(z, float(energy) + scale * env, label=label)
            ax.axhline(float(energy), lw=.5, alpha=.4)
        ax.set_xlabel("z (nm)"); ax.set_ylabel("Energy + scaled envelope (eV)"); ax.legend()
    else:
        ax.text(.5, .5, "Raw Case_19 envelope tree required\n(available on licensed work laptop)",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    paths.append(_save(fig, root / "04_hh2_hh3_wavefunctions.png"))

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for role, group in _groups(rotation_rows, "calculation").items():
        ax.plot([float(r["theta_deg"]) for r in group],
                [float(r["chi2_1550_pm_per_V"]) for r in group], "o-", label=role)
    ax.set_xlabel("HH2/HH3 rotation angle (degrees)"); ax.set_ylabel("|chi2(1550)| (pm/V)")
    ax.legend(); paths.append(_save(fig, root / "05_rotation_chi2.png"))

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for role, group in _groups(rotation_rows, "calculation").items():
        ax.plot([float(r["theta_deg"]) for r in group],
                [float(r["cancellation_factor"]) for r in group], "o-", label=role)
    ax.set_xlabel("HH2/HH3 rotation angle (degrees)"); ax.set_ylabel("Cancellation factor")
    ax.legend(); paths.append(_save(fig, root / "06_rotation_cancellation.png"))

    fig, ax = plt.subplots(figsize=(8, 4.8))
    for label, data in spectra.items():
        ax.plot(data["wavelength_nm"], np.abs(data["chi_total"]), label=label)
    ax.scatter([1550], [2340], marker="*", s=100, color="black", label="paper marker")
    ax.set_xlabel("Fundamental wavelength (nm)"); ax.set_ylabel("|chi2| (pm/V)")
    ax.legend(fontsize=8); paths.append(_save(fig, root / "07_selected_spectra.png"))

    top_e = [r for r in term_rows if r["pathway"] == "electron-mediated"][:10]
    top_h = [r for r in term_rows if r["pathway"] == "HH-mediated"][:10]
    rows = top_e + top_h
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#2166ac"] * len(top_e) + ["#b2182b"] * len(top_h)
    ax.barh(np.arange(len(rows)), [float(r["final_pm_per_V_abs"]) for r in rows], color=colors)
    ax.set_yticks(np.arange(len(rows)), [f"{r['term_id']} {r['pathway']}" for r in rows], fontsize=8)
    ax.invert_yaxis(); ax.set_xlabel("Term magnitude (pm/V)")
    paths.append(_save(fig, root / "08_top_eq2_terms.png"))

    fig, ax = plt.subplots(figsize=(7, 5))
    sc = ax.scatter([float(r["electron_abs"]) for r in pair_rows],
                    [float(r["hh_abs"]) for r in pair_rows],
                    c=[float(r["percent_cancellation"]) for r in pair_rows], cmap="viridis")
    max_value = max([1.0, *[float(r["electron_abs"]) for r in pair_rows],
                     *[float(r["hh_abs"]) for r in pair_rows]])
    ax.plot([0, max_value], [0, max_value], "k--", lw=.8)
    ax.set_xlabel("Electron-term magnitude (pm/V)"); ax.set_ylabel("Matched HH-term magnitude (pm/V)")
    fig.colorbar(sc, ax=ax, label="Pair cancellation (%)")
    paths.append(_save(fig, root / "09_pairwise_cancellation_map.png"))
    return paths


def _groups(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        result.setdefault(str(row[key]), []).append(row)
    return result

