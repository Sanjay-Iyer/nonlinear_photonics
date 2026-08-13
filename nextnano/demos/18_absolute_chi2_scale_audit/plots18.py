"""Three deliberately simple figures for Demo 18."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


MAJOR_CASES = (
    "A_baseline",
    "B_two_wells_Nz",
    "C_large_kmax",
    "D_Nz_plus_large_kmax",
)


def convention_spectra(path: Path, evaluated: Sequence[object]) -> Path:
    by_id = {item.row["case_id"]: item for item in evaluated}
    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    for case_id in MAJOR_CASES:
        item = by_id[case_id]
        ax.plot(
            item.wavelength_nm,
            np.abs(item.chi2),
            linewidth=1.7,
            label=item.row["label"],
        )
    ax.axvline(1550.0, color="0.35", linestyle="--", linewidth=1.0)
    ax.set_title(r"Demo 18 Absolute $\chi^{(2)}$ Convention Comparison")
    ax.set_xlabel("Fundamental Wavelength (nm)")
    ax.set_ylabel(r"$|\chi^{(2)}|$ (pm/V)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def chi2_at_1550(path: Path, rows: Sequence[Mapping[str, object]]) -> Path:
    labels = [str(row["case_id"]).split("_", 1)[0] for row in rows]
    values = [float(row["chi2_at_1550_pm_per_V"]) for row in rows]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.bar(labels, values, color="#4776a8")
    ax.set_title(r"$\chi^{(2)}$ at 1550 nm")
    ax.set_xlabel("Post-processing case")
    ax.set_ylabel(r"$|\chi^{(2)}|$ (pm/V)")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def kgrid_convergence(path: Path, rows: Sequence[Mapping[str, object]]) -> Path:
    points = [int(row["k_points"]) for row in rows]
    values = [float(row["chi2_at_1550_pm_per_V"]) for row in rows]
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    ax.plot(points, values, marker="o", linewidth=1.6, color="#b24b3f")
    ax.set_title(r"$k_\parallel$-grid Convergence")
    ax.set_xlabel("Radial k points")
    ax.set_ylabel(r"$|\chi^{(2)}(1550\,\mathrm{nm})|$ (pm/V)")
    ax.set_xticks(points)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
