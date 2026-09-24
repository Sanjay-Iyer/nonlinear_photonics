"""Small temperature overlays from completed numerical spectra only."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .acquisition import ROOT


def series(root: Path, temperatures=(100, 300, 500)):
    result = {}
    for t in temperatures:
        path = root / f"{t}K/chi2_results/chi2_spectrum.csv"
        if not path.is_file():
            raise ValueError(f"Missing {path}; no comparison plotted from incomplete data")
        values = np.loadtxt(path, delimiter=",", skiprows=1)
        if values.ndim != 2 or values.shape[1] != 6 or not np.isfinite(values).all():
            raise ValueError(f"Malformed spectrum: {path}")
        result[t] = values
    if not all(np.array_equal(result[300][:, 0], value[:, 0]) for value in result.values()):
        raise ValueError("Temperature spectra have different wavelength grids")
    return result


def plot(root: Path, out: Path, model: str) -> None:
    data = series(root)
    if out.exists():
        raise ValueError("Refusing to overwrite comparison output")
    out.mkdir(parents=True)
    for name, col in (("real", 2), ("imag", 3), ("abs_real", 4)):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for t, values in data.items():
            ax.plot(values[:, 0], values[:, col], label=f"{t} K", lw=1.5)
        ax.set(xlabel="fundamental wavelength (nm)", ylabel=r"$\chi^{(2)}$ (pm/V)", title=model)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(out / f"{name}.png", dpi=200)
        fig.savefig(out / f"{name}.svg")
        plt.close(fig)
    with (out / "temperature_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["temperature_K", "Re_1550_pm_per_V", "Im_1550_pm_per_V",
                         "abs_Re_1550_pm_per_V", "dominant_abs_Re_wavelength_nm",
                         "dominant_abs_Im_wavelength_nm"])
        for t, v in data.items():
            target = np.flatnonzero(v[:, 0] == 1550)
            if len(target) != 1:
                raise ValueError("1550 nm absent from wavelength grid")
            j = int(target[0])
            writer.writerow([t, v[j, 2], v[j, 3], v[j, 4],
                             v[np.argmax(abs(v[:, 2])), 0], v[np.argmax(abs(v[:, 3])), 0]])
    fig, ax = plt.subplots(figsize=(6, 4))
    for col, label in ((2, "Re"), (3, "Im"), (4, "|Re|")):
        ax.plot(list(data), [v[v[:, 0] == 1550, col][0] for v in data.values()], "-o", label=label)
    ax.set(xlabel="solver temperature (K)", ylabel=r"$\chi^{(2)}$ at 1550 nm (pm/V)", title=model)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "at_1550_nm.png", dpi=200)
    plt.close(fig)


def compare_models(full_root: Path, mixed_root: Path, out: Path) -> None:
    """A compact like-for-like trend table; spectra need not agree in amplitude."""
    if out.exists():
        raise ValueError("Refusing to overwrite model-comparison output")
    full, mixed = series(full_root), series(mixed_root)
    out.mkdir(parents=True)
    with (out / "model_temperature_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "temperature_K", "Re_1550_pm_per_V", "Im_1550_pm_per_V",
                         "dominant_abs_Re_wavelength_nm"])
        for model, data in (("full8", full), ("mixed", mixed)):
            for t, v in data.items():
                j = np.flatnonzero(v[:,0] == 1550)
                if len(j) != 1:
                    raise ValueError("1550 nm absent")
                writer.writerow([model, t, v[j[0],2], v[j[0],3], v[np.argmax(abs(v[:,2])),0]])


def compare_historical(full_300K: Path, out: Path) -> None:
    """Descriptive 29A model-change plot; no numerical-agreement gate."""
    historical = ROOT / "validation/historical_demo28_mixed_300K.csv"
    new = np.loadtxt(full_300K, delimiter=",", skiprows=1)
    old = np.loadtxt(historical, delimiter=",", skiprows=1)
    if new.shape != old.shape or not np.array_equal(new[:,0], old[:,0]):
        raise ValueError("Historical and new 300 K spectra need a common wavelength grid")
    if not np.isfinite(new).all():
        raise ValueError("Nonfinite new 300 K spectrum")
    if out.exists():
        raise ValueError("Refusing to overwrite historical comparison")
    out.mkdir(parents=True)
    for name, col in (("real",2),("imag",3),("abs_real",4)):
        fig, ax = plt.subplots(figsize=(8,4.5))
        ax.plot(old[:,0], old[:,col], label="historical mixed 300 K")
        ax.plot(new[:,0], new[:,col], label="new full 8-band 300 K")
        ax.set(xlabel="fundamental wavelength (nm)", ylabel=r"$\chi^{(2)}$ (pm/V)")
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(out / f"historical_vs_full8_{name}.png", dpi=200)
        plt.close(fig)
    with (out / "model_change_300K.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["observable", "historical_1550_pm_per_V", "full8_1550_pm_per_V",
                         "difference_1550_pm_per_V", "maximum_absolute_spectral_difference_pm_per_V"])
        target = np.flatnonzero(new[:,0] == 1550)
        if len(target) != 1:
            raise ValueError("1550 nm absent from comparison grid")
        j = int(target[0])
        for name, col in (("Re",2),("Im",3),("abs_Re",4)):
            writer.writerow([name, old[j,col], new[j,col], new[j,col]-old[j,col],
                             np.max(abs(new[:,col]-old[:,col]))])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", choices=("mixed", "full8", "both", "historical"), required=True)
    p.add_argument("--input", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args(argv)
    try:
        if a.model == "historical":
            compare_historical(a.input or ROOT / "outputs/29B_temperature_full8band/300K/chi2_results/chi2_spectrum.csv",
                               a.output or ROOT / "outputs/comparison/historical_300K")
        elif a.model == "both":
            compare_models(ROOT / "outputs/29B_temperature_full8band",
                           ROOT / "outputs/29C_mixed_control",
                           a.output or ROOT / "outputs/comparison/models")
        else:
            default = ROOT / ("outputs/29C_mixed_control" if a.model == "mixed" else "outputs/29B_temperature_full8band")
            plot(a.input or default, a.output or ROOT / "outputs/comparison" / a.model, a.model)
        print(f"Wrote {a.model} temperature comparison")
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
