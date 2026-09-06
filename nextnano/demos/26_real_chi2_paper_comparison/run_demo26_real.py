"""Demo 26_real: observable-interpretation test using existing Demo 23D data.

This module is intentionally analysis-only. It reads an already exported
complex spectrum and the unchanged paper eye digitization. It never invokes a
nextnano executable or changes the underlying physics.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[2]
OUTPUT_DIR = DEMO_DIR / "outputs"
PLOT_DIR = OUTPUT_DIR / "plots"

MODEL_PATH = REPO_ROOT / "demo_results/demo24/demo23_reanalysis/spectra/23D_chi2.csv"
PAPER_PATH = REPO_ROOT / "nextnano/demos/23_k_resolved_dispersion_validation/paper_figure2d_digitized_simulation.csv"
PAPER_PDF = REPO_ROOT / "2602.23246v1.pdf"
DEMO24_REPORT = REPO_ROOT / "nextnano/demos/24_equation2_spectral_shape_audit/outputs/DEMO24_FINAL_REPORT.md"
PATHWAY_PATH = REPO_ROOT / "nextnano/demos/24_equation2_spectral_shape_audit/outputs/PATHWAY_SPECTRA.csv"
RAW_DISPERSION = REPO_ROOT / (
    "demo_results/demo23/raw/production_y_n301_k0100/production_y_n301_k0100/"
    "bias_00000/QuantumDispersions/acqw/kp8/dispersion_Gamma_to_y.dat"
)
FROZEN_MATRIX_SOURCE = REPO_ROOT / "demo_results/demo19/tables/demo19_master_results.csv"
CONFIG_PATH = REPO_ROOT / "nextnano/demos/23_k_resolved_dispersion_validation/demo23_config.yaml"
FINITE_K_AUDIT = REPO_ROOT / "nextnano/demos/24_equation2_spectral_shape_audit/outputs/FINITE_K_DATA_INVENTORY.md"

FEATURES = (
    ("P1", "peak", 540.0, (490.0, 575.0)),
    ("Z1", "zero/minimum", 605.0, (550.0, 650.0)),
    ("P2", "peak", 760.0, (680.0, 830.0)),
    ("P3", "peak", 1080.0, (950.0, 1160.0)),
    ("Z2", "zero/minimum", 1330.0, (1250.0, 1400.0)),
    ("P4", "peak", 1520.0, (1420.0, 1620.0)),
)

REGIONS = (
    ("full_overlap", 400.0, 1850.0),
    ("500_700_nm", 500.0, 700.0),
    ("700_900_nm", 700.0, 900.0),
    ("950_1200_nm", 950.0, 1200.0),
    ("1200_1450_nm", 1200.0, 1450.0),
    ("main_resonance_1420_1620_nm", 1420.0, 1620.0),
)


@dataclass(frozen=True)
class Spectrum:
    wavelength_nm: np.ndarray
    real: np.ndarray
    imag: np.ndarray
    magnitude: np.ndarray


@dataclass(frozen=True)
class PaperCurve:
    wavelength_nm: np.ndarray
    value: np.ndarray


def read_csv_columns(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return {key: np.asarray([float(row[key]) for row in rows], dtype=float) for key in rows[0]}


def load_inputs() -> tuple[Spectrum, PaperCurve]:
    model = read_csv_columns(MODEL_PATH)
    paper = read_csv_columns(PAPER_PATH)
    spectrum = Spectrum(
        model["wavelength_nm"],
        model["real_chi2_pm_per_V"],
        model["imag_chi2_pm_per_V"],
        model["abs_chi2_pm_per_V"],
    )
    curve = PaperCurve(paper["wavelength_nm"], paper["digitized_simulated_chi2_pm_per_V"])
    validate_inputs(spectrum, curve)
    return spectrum, curve


def validate_inputs(spectrum: Spectrum, paper: PaperCurve) -> None:
    arrays = (spectrum.wavelength_nm, spectrum.real, spectrum.imag, spectrum.magnitude)
    if not all(len(a) == len(arrays[0]) for a in arrays):
        raise ValueError("Demo 23D spectrum columns have inconsistent lengths")
    if len(spectrum.wavelength_nm) != 1451 or not np.allclose(np.diff(spectrum.wavelength_nm), 1.0):
        raise ValueError("expected the preserved 400-1850 nm Demo 23D 1-nm grid")
    reconstructed = np.hypot(spectrum.real, spectrum.imag)
    if not np.allclose(reconstructed, spectrum.magnitude, rtol=2e-13, atol=2e-13):
        raise ValueError("stored |chi2| is inconsistent with stored Re and Im")
    if len(paper.wavelength_nm) != 45 or np.any(np.diff(paper.wavelength_nm) <= 0):
        raise ValueError("paper digitization must be the unchanged monotonic 45-point trace")
    if np.any(paper.value < 0):
        raise ValueError("paper digitization unexpectedly contains negative values")
    for expected_zero in (605.0, 1330.0):
        idx = int(np.argmin(np.abs(paper.wavelength_nm - expected_zero)))
        if paper.wavelength_nm[idx] != expected_zero or paper.value[idx] != 0.0:
            raise ValueError(f"paper digitization no longer contains its {expected_zero:g}-nm zero")


def normalize_absmax(values: np.ndarray) -> np.ndarray:
    scale = float(np.max(np.abs(values)))
    return np.asarray(values, dtype=float) / scale if scale else np.zeros_like(values, dtype=float)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Sequence[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def linear_zero_crossings(x: np.ndarray, y: np.ndarray) -> list[dict[str, float]]:
    result: list[dict[str, float]] = []
    for i in range(len(x) - 1):
        if y[i] == 0.0:
            root = float(x[i])
        elif y[i] * y[i + 1] < 0.0:
            root = float(x[i] - y[i] * (x[i + 1] - x[i]) / (y[i + 1] - y[i]))
        else:
            continue
        result.append({"root_nm": root, "left_index": i, "right_index": i + 1})
    return result


def local_extrema_indices(y: np.ndarray, kind: str) -> np.ndarray:
    if kind == "max":
        mask = (y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:])
    elif kind == "min":
        mask = (y[1:-1] < y[:-2]) & (y[1:-1] <= y[2:])
    else:
        raise ValueError(kind)
    return np.flatnonzero(mask) + 1


def local_prominence(y: np.ndarray, index: int, half_width: int = 30) -> float:
    lo, hi = max(0, index - half_width), min(len(y), index + half_width + 1)
    if y[index] >= y[index - 1] and y[index] >= y[index + 1]:
        return float(y[index] - max(np.min(y[lo:index + 1]), np.min(y[index:hi])))
    return float(min(np.max(y[lo:index + 1]), np.max(y[index:hi])) - y[index])


def significant_extrema(x: np.ndarray, y: np.ndarray, *, include_minima: bool) -> list[int]:
    indices = list(local_extrema_indices(y, "max"))
    if include_minima:
        indices.extend(local_extrema_indices(y, "min"))
    return sorted(i for i in indices if local_prominence(y, i) >= 0.02)


def find_peak_feature(x: np.ndarray, y: np.ndarray, window: tuple[float, float], *, signed: bool) -> int | None:
    candidates = significant_extrema(x, y, include_minima=signed)
    candidates = [i for i in candidates if window[0] <= x[i] <= window[1]]
    if not candidates:
        return None
    if signed:
        return max(candidates, key=lambda i: abs(y[i]))
    return max(candidates, key=lambda i: y[i])


def nearest_extremum(x: np.ndarray, y: np.ndarray, target_nm: float, kind: str) -> int | None:
    indices = local_extrema_indices(y, kind)
    if not len(indices):
        return None
    return int(indices[np.argmin(np.abs(x[indices] - target_nm))])


def interp_at(x: np.ndarray, y: np.ndarray, target: float) -> float:
    return float(np.interp(target, x, y))


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def metric_rows(
    x: np.ndarray,
    paper_interp: np.ndarray,
    re_norm: np.ndarray,
    abs_norm: np.ndarray,
    feature_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for observable, candidate in (("signed_Re_chi2", re_norm), ("abs_chi2", abs_norm)):
        peak_errors = [
            abs(float(r[f"{observable}_error_nm"]))
            for r in feature_rows
            if str(r["Feature"]).startswith("P") and r[f"{observable}_error_nm"] != ""
        ]
        zero_errors = [
            abs(float(r[f"{observable}_error_nm"]))
            for r in feature_rows
            if str(r["Feature"]).startswith("Z") and r[f"{observable}_error_nm"] != ""
        ]
        for region, low, high in REGIONS:
            mask = (x >= low) & (x <= high)
            residual = candidate[mask] - paper_interp[mask]
            rows.append(
                {
                    "comparison": f"paper_vs_{observable}",
                    "region": region,
                    "wavelength_min_nm": low,
                    "wavelength_max_nm": high,
                    "n_points": int(np.count_nonzero(mask)),
                    "normalized_RMSE": float(np.sqrt(np.mean(residual**2))),
                    "correlation_coefficient": pearson(paper_interp[mask], candidate[mask]),
                    "normalized_MAE": float(np.mean(np.abs(residual))),
                    "matched_peak_count": len(peak_errors) if region == "full_overlap" else "",
                    "peak_wavelength_MAE_nm": float(np.mean(peak_errors)) if peak_errors and region == "full_overlap" else "",
                    "zero_or_minimum_feature_MAE_nm": float(np.mean(zero_errors)) if zero_errors and region == "full_overlap" else "",
                    "zero_crossing_metric_note": (
                        "nearest signed Re zero crossings" if observable == "signed_Re_chi2" else
                        "|chi2| cannot sign-cross; nearest local minima used as zero-feature proxies"
                    ) if region == "full_overlap" else "",
                }
            )
    return rows


def build_feature_rows(
    spectrum: Spectrum, paper: PaperCurve, re_norm: np.ndarray, abs_norm: np.ndarray
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    x = spectrum.wavelength_nm
    crossings = linear_zero_crossings(x, spectrum.real)
    rows: list[dict[str, object]] = []
    zero_rows: list[dict[str, object]] = []

    for name, feature_type, paper_nm, window in FEATURES:
        if name.startswith("P"):
            re_i = find_peak_feature(x, re_norm, window, signed=True)
            abs_i = find_peak_feature(x, abs_norm, window, signed=False)
            re_nm = float(x[re_i]) if re_i is not None else None
            abs_nm = float(x[abs_i]) if abs_i is not None else None
            re_note = "significant signed extremum" if re_i is not None else "no significant interior signed extremum in search window"
            abs_note = "significant magnitude maximum" if abs_i is not None else "no significant interior magnitude maximum in search window"
        else:
            nearest = min(crossings, key=lambda item: abs(item["root_nm"] - paper_nm))
            re_nm = float(nearest["root_nm"])
            abs_i = nearest_extremum(x, abs_norm, paper_nm, "min")
            abs_nm = float(x[abs_i]) if abs_i is not None else None
            re_i = None
            re_note = "nearest actual Re zero crossing (outside paper feature window)" if not (window[0] <= re_nm <= window[1]) else "actual Re zero crossing"
            abs_note = "nearest local |chi2| minimum; magnitude remains nonzero"

            li, ri = int(nearest["left_index"]), int(nearest["right_index"])
            imag_root = interp_at(x, spectrum.imag, re_nm)
            abs_root = interp_at(x, spectrum.magnitude, re_nm)
            zero_rows.append(
                {
                    "paper_feature": name,
                    "paper_wavelength_nm": paper_nm,
                    "nearest_Re_zero_crossing_nm": re_nm,
                    "crossing_error_nm": re_nm - paper_nm,
                    "left_sample_nm": float(x[li]),
                    "Re_before_pm_per_V": float(spectrum.real[li]),
                    "right_sample_nm": float(x[ri]),
                    "Re_after_pm_per_V": float(spectrum.real[ri]),
                    "sign_flip": "YES" if spectrum.real[li] * spectrum.real[ri] < 0 else "NO",
                    "Im_at_interpolated_crossing_pm_per_V": imag_root,
                    "abs_chi_at_interpolated_crossing_pm_per_V": abs_root,
                    "abs_chi_normalized_at_crossing": interp_at(x, abs_norm, re_nm),
                    "Re_at_paper_wavelength_pm_per_V": interp_at(x, spectrum.real, paper_nm),
                    "Im_at_paper_wavelength_pm_per_V": interp_at(x, spectrum.imag, paper_nm),
                    "abs_chi_at_paper_wavelength_pm_per_V": interp_at(x, spectrum.magnitude, paper_nm),
                    "Re_changes_sign_near_paper_feature": "YES" if window[0] <= re_nm <= window[1] else "NO",
                }
            )

        re_error = re_nm - paper_nm if re_nm is not None else None
        abs_error = abs_nm - paper_nm if abs_nm is not None else None
        if re_error is None and abs_error is None:
            better = "neither: no corresponding feature"
        elif re_error is None:
            better = "|chi2|"
        elif abs_error is None:
            better = "signed Re[chi2]"
        elif abs(re_error) < abs(abs_error) - 0.5:
            better = "signed Re[chi2]"
        elif abs(abs_error) < abs(re_error) - 0.5:
            better = "|chi2|"
        else:
            better = "tie within 0.5 nm"
        rows.append(
            {
                "Feature": name,
                "Feature_type": feature_type,
                "Paper_wavelength_nm": paper_nm,
                "Paper_normalized_value": interp_at(paper.wavelength_nm, normalize_absmax(paper.value), paper_nm),
                "signed_Re_chi2_wavelength_nm": "" if re_nm is None else re_nm,
                "signed_Re_chi2_error_nm": "" if re_error is None else re_error,
                "signed_Re_chi2_normalized_value": "" if re_nm is None else interp_at(x, re_norm, re_nm),
                "signed_Re_chi2_note": re_note,
                "abs_chi2_wavelength_nm": "" if abs_nm is None else abs_nm,
                "abs_chi2_error_nm": "" if abs_error is None else abs_error,
                "abs_chi2_normalized_value": "" if abs_nm is None else interp_at(x, abs_norm, abs_nm),
                "abs_chi2_note": abs_note,
                "Which_observable_agrees_better_in_wavelength": better,
            }
        )
    return rows, zero_rows


def plot_setup() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 220,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.20,
            "grid.linewidth": 0.7,
        }
    )


def annotate_features(ax: plt.Axes, paper: PaperCurve, *, peaks: bool = True) -> None:
    paper_norm = normalize_absmax(paper.value)
    for name, _, wavelength, _ in FEATURES:
        if name.startswith("P") and peaks:
            value = interp_at(paper.wavelength_nm, paper_norm, wavelength)
            ax.annotate(name, (wavelength, value), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8, color="black")


def mark_paper_zeros(ax: plt.Axes, visible_range: tuple[float, float] = (400.0, 1850.0)) -> None:
    for wavelength, name in ((605.0, "Z1"), (1330.0, "Z2")):
        if not (visible_range[0] <= wavelength <= visible_range[1]):
            continue
        ax.axvline(wavelength, color="#777777", lw=1.0, ls=":")
        ax.text(wavelength + 7, -0.97, f"{name} {wavelength:.0f} nm", rotation=90, va="bottom", ha="left", fontsize=8, color="#555555")


def savefig(fig: plt.Figure, name: str) -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_DIR / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def comparison_plot(
    spectrum: Spectrum,
    paper: PaperCurve,
    re_norm: np.ndarray,
    abs_norm: np.ndarray,
    name: str,
    title: str,
    show_re: bool = True,
    show_abs: bool = True,
    xlim: tuple[float, float] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(12.0, 6.5))
    ax.plot(paper.wavelength_nm, normalize_absmax(paper.value), "k--", lw=2.4, marker="o", ms=3.0,
            label=r"Paper Fig. 2d eye digitization (published $|\chi^{(2)}|$)")
    if show_re:
        ax.plot(spectrum.wavelength_nm, re_norm, color="#1f77b4", lw=2.0,
                label=r"Demo 23D signed $\mathrm{Re}[\chi^{(2)}] / \max|\mathrm{Re}[\chi^{(2)}]|$")
    if show_abs:
        ax.plot(spectrum.wavelength_nm, abs_norm, color="#d95f02", lw=2.0,
                label=r"Demo 23D $|\chi^{(2)}| / \max|\chi^{(2)}|$")
    ax.axhline(0.0, color="#333333", lw=0.9)
    visible_range = xlim or (400.0, 1850.0)
    mark_paper_zeros(ax, visible_range)
    annotate_features(ax, paper)
    ax.set_xlim(*visible_range)
    ax.set_ylim(-1.08, 1.15)
    ax.set_xlabel("Fundamental wavelength (nm)")
    ax.set_ylabel("Normalized susceptibility")
    ax.set_title(title)
    ax.legend(loc="upper left", frameon=True)
    ax.text(0.995, 0.015, "Paper trace is nonnegative and digitized from the published figure; not author data.",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#555555")
    savefig(fig, name)


def component_plot(x: np.ndarray, y: np.ndarray, name: str, title: str, ylabel: str, color: str, zeros: Iterable[float] = ()) -> None:
    fig, ax = plt.subplots(figsize=(12.0, 5.8))
    ax.plot(x, y, color=color, lw=2.0)
    ax.axhline(0.0, color="#333333", lw=0.9)
    for root in zeros:
        ax.axvline(root, color="#777777", ls="--", lw=1.0)
        ax.annotate(f"Re zero {root:.1f} nm", (root, 0), xytext=(7, 12), textcoords="offset points", rotation=90, fontsize=8)
    for wavelength, label in ((605.0, "paper Z1"), (1330.0, "paper Z2")):
        ax.axvline(wavelength, color="#b2182b", ls=":", lw=1.0)
        ax.text(wavelength + 6, ax.get_ylim()[0] * 0.88, label, rotation=90, fontsize=8, color="#b2182b")
    ax.set_xlim(400, 1850)
    ax.set_xlabel("Fundamental wavelength (nm)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    savefig(fig, name)


def residual_plot(x: np.ndarray, paper_interp: np.ndarray, re_norm: np.ndarray, abs_norm: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(12.0, 5.8))
    ax.plot(x, re_norm - paper_interp, color="#1f77b4", lw=1.8, label="signed Re[chi2] - paper")
    ax.plot(x, abs_norm - paper_interp, color="#d95f02", lw=1.8, label="|chi2| - paper")
    ax.axhline(0.0, color="#333333", lw=0.9)
    mark_paper_zeros(ax)
    ax.set_xlim(400, 1850)
    ax.set_xlabel("Fundamental wavelength (nm)")
    ax.set_ylabel("Normalized residual")
    ax.set_title("Figure 9 - pointwise normalized residuals")
    ax.legend(loc="upper left")
    savefig(fig, "figure09_residual_comparison.png")


def correspondence_plot(feature_rows: Sequence[dict[str, object]]) -> None:
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11.5, 7.8),
        gridspec_kw={"height_ratios": [1.35, 1.0], "hspace": 0.30},
    )
    names = [str(row["Feature"]) for row in feature_rows]
    y = np.arange(len(names))
    for label, key, color, marker in (
        ("Paper", "Paper_wavelength_nm", "black", "o"),
        (r"signed $\mathrm{Re}[\chi^{(2)}]$", "signed_Re_chi2_wavelength_nm", "#1f77b4", "D"),
        (r"$|\chi^{(2)}|$", "abs_chi2_wavelength_nm", "#d95f02", "s"),
    ):
        xs = [float(row[key]) if row[key] != "" else np.nan for row in feature_rows]
        ax1.scatter(xs, y, s=48, color=color, marker=marker, label=label, zorder=3)
    ax1.set_yticks(y, names)
    ax1.invert_yaxis()
    ax1.set_xlim(400, 1650)
    ax1.set_title("Figure 10 - paper/model feature correspondence")
    ax1.legend(ncol=3, loc="lower right")
    for i, row in enumerate(feature_rows):
        if row["signed_Re_chi2_wavelength_nm"] == "":
            ax1.text(1630, i - 0.10, "Re: no feature", ha="right", va="center", fontsize=7, color="#1f77b4")
        if row["abs_chi2_wavelength_nm"] == "":
            ax1.text(1630, i + 0.15, r"$|\chi^{(2)}|$: no feature", ha="right", va="center", fontsize=7, color="#d95f02")

    width = 0.34
    re_errors = [abs(float(row["signed_Re_chi2_error_nm"])) if row["signed_Re_chi2_error_nm"] != "" else np.nan for row in feature_rows]
    abs_errors = [abs(float(row["abs_chi2_error_nm"])) if row["abs_chi2_error_nm"] != "" else np.nan for row in feature_rows]
    ax2.bar(y - width / 2, re_errors, width, color="#1f77b4", label="signed Re error")
    ax2.bar(y + width / 2, abs_errors, width, color="#d95f02", label="|chi2| error")
    ax2.set_xticks(y, names)
    ax2.set_ylabel("Absolute wavelength error (nm)")
    ax2.set_title("Absolute wavelength errors for detected features", fontsize=10, pad=6)
    ax2.legend(ncol=2)
    fig.text(
        0.5, 0.01,
        "Only significant detected extrema/crossings are shown; blank means no corresponding feature in the configured window.",
        ha="center", va="bottom", fontsize=8, color="#555555",
    )
    fig.subplots_adjust(bottom=0.08)
    savefig(fig, "figure10_peak_zero_correspondence_summary.png")


def make_plots(
    spectrum: Spectrum,
    paper: PaperCurve,
    paper_interp: np.ndarray,
    re_norm: np.ndarray,
    abs_norm: np.ndarray,
    feature_rows: Sequence[dict[str, object]],
) -> None:
    plot_setup()
    comparison_plot(
        spectrum, paper, re_norm, abs_norm,
        "figure01_paper_vs_signed_real_vs_magnitude.png",
        r"Figure 1 - paper vs signed $\mathrm{Re}[\chi^{(2)}]$ vs $|\chi^{(2)}|$ (primary observable test)",
    )
    crossings = [item["root_nm"] for item in linear_zero_crossings(spectrum.wavelength_nm, spectrum.real)]
    component_plot(spectrum.wavelength_nm, spectrum.real, "figure02_signed_real_full.png",
                   r"Figure 2 - Demo 23D signed $\mathrm{Re}[\chi^{(2)}]$", r"$\mathrm{Re}[\chi^{(2)}]$ (pm/V)", "#1f77b4", crossings)
    component_plot(spectrum.wavelength_nm, spectrum.imag, "figure03_imaginary_full.png",
                   r"Figure 3 - Demo 23D $\mathrm{Im}[\chi^{(2)}]$", r"$\mathrm{Im}[\chi^{(2)}]$ (pm/V)", "#6a3d9a")
    component_plot(spectrum.wavelength_nm, spectrum.magnitude, "figure04_magnitude_full.png",
                   r"Figure 4 - Demo 23D $|\chi^{(2)}|$", r"$|\chi^{(2)}|$ (pm/V)", "#d95f02")
    comparison_plot(spectrum, paper, re_norm, abs_norm, "figure05_zoom_500_700_nm.png",
                    "Figure 5 - 500-700 nm: paper Z1 vs model observables", xlim=(500, 700))
    comparison_plot(spectrum, paper, re_norm, abs_norm, "figure06_zoom_1200_1400_nm.png",
                    "Figure 6 - 1200-1400 nm: paper Z2 vs model observables", xlim=(1200, 1400))
    comparison_plot(spectrum, paper, re_norm, abs_norm, "figure07_paper_vs_signed_real.png",
                    r"Figure 7 - paper vs signed $\mathrm{Re}[\chi^{(2)}]$", show_abs=False)
    comparison_plot(spectrum, paper, re_norm, abs_norm, "figure08_paper_vs_magnitude.png",
                    r"Figure 8 - paper vs $|\chi^{(2)}|$", show_re=False)
    residual_plot(spectrum.wavelength_nm, paper_interp, re_norm, abs_norm)
    correspondence_plot(feature_rows)


def input_audit() -> str:
    return f"""# Demo 26_real input audit

Demo 26_real uses the shortest reliable route: the existing Demo 23D complex-spectrum CSV. No complex susceptibility is reconstructed because the real and imaginary parts are already preserved and their quadrature exactly reproduces the stored magnitude.

| Data item | Available? | Path | How it is used | Limitation |
|---|---|---|---|---|
| Complex total chi spectrum | YES | `{MODEL_PATH}` | Primary input; reads Re, Im, and magnitude on the 400-1850 nm, 1-nm grid | Analysis product generated from copied Professional data, not a native nextnano chi export |
| Complex 16-pathway spectra | YES | `{PATHWAY_PATH}` | Audit trail confirming the 16 complex contributions exist | Not needed for the shortest-route observable test |
| Complex k-resolved integrands | PARTIAL | Demo 23 tables contain 1550-nm k-integrand summaries; the full in-memory array was not exported as a wavelength-by-k CSV | Confirms integration diagnostics; not used here | A full stored 2D integrand is unavailable, but is unnecessary because total complex chi is present |
| Tracked full kp8 E(k), e1/e2/hh1/hh2 | YES | `{RAW_DISPERSION}` plus Demo 23 state-tracking tables | Source used by Demo 23D to produce the preserved complex spectrum | Raw nextnano output does not itself contain chi |
| M(0), Equation-2 inputs | YES | `{FROZEN_MATRIX_SOURCE}` and `{CONFIG_PATH}` | Existing Demo 23D numerator and physical configuration | M(k)=M(0) approximation; finite-k matrices were not exported |
| Finite-k O(k), z_e(k), z_hh(k) | NO | `{FINITE_K_AUDIT}` | Not used | Would require a new Professional export; deliberately not fabricated |
| Exact paper digitization | YES | `{PAPER_PATH}` | Unchanged 45-point paper comparison | Eye digitization, not raw/tabulated author data |

Input hashes:

- Demo 23D spectrum SHA-256: `{sha256(MODEL_PATH)}`
- Paper digitization SHA-256: `{sha256(PAPER_PATH)}`

The available files are sufficient to answer the Re-vs-magnitude question. No nextnano calculation is required or performed.
"""


def paper_audit() -> str:
    return f"""# Paper observable audit

## What the paper explicitly says

The source is Ramesh et al., *Enhanced Interband Optical Nonlinearities from Coupled Quantum Wells*, `{PAPER_PDF}`. On PDF page 7, Figure 2d labels the dashed simulation axis **`Simulated |chi^(2)| (pm/V)`**. The caption calls it the simulation for the coupled quantum wells. The Methods on pages 11-12 define a complex chi through denominators containing `+ i Gamma`, with Gamma = 5 meV.

## What the plot visually shows

- The simulated curve is entirely nonnegative.
- The left y axis starts at zero; it is not centered on a signed zero axis.
- The two dips near 605 and 1330 nm touch the zero baseline but no negative branch is drawn.
- The repository digitization has 45 nonnegative points and exact zero-valued samples at 605 and 1330 nm.

## What is inferred

The literal label, axis geometry, and rendered curve all support a magnitude observable, not signed Re[chi]. The colleague's interpretation can be made compatible only by assuming both that the absolute-value bars are erroneous and that negative lobes were folded upward or clipped. The paper and repository contain no affirmative evidence for either assumption. There is therefore **no evidence of a labeling inconsistency** in Figure 2d.

The signed-real comparison remains a useful falsification test, but it must not replace the paper's explicit magnitude observable. Because the eye digitization contains no sign information, it cannot independently reconstruct a signed paper curve.

Provenance limitation: `{PAPER_PATH}` is an unchanged eye digitization of the published dashed curve, not raw author data.
"""


def reassessment_rows() -> list[dict[str, object]]:
    return [
        {"Demo24_conclusion": "missing P1/P3", "classification": "STILL VALID", "Demo26_real_evidence": "Neither signed Re nor |chi| has a significant corresponding extremum in the configured P1/P3 windows; changing observable does not create the missing peak pair."},
        {"Demo24_conclusion": "missing 605 node", "classification": "STILL VALID", "Demo26_real_evidence": "Nearest Re zero is about 714 nm, outside 550-650 nm; |chi| at 605 nm is finite."},
        {"Demo24_conclusion": "missing 1330 node", "classification": "STILL VALID", "Demo26_real_evidence": "Nearest Re zero is about 1437 nm, outside 1250-1400 nm; |chi| at 1330 nm is finite."},
        {"Demo24_conclusion": "2.296 eV missing transition", "classification": "STILL VALID", "Demo26_real_evidence": "The P1/P3 one-/two-photon pair remains absent in both observables; taking Re cannot supply a missing denominator resonance."},
        {"Demo24_conclusion": "kmax artifact", "classification": "UNRELATED TO REAL-vs-MAGNITUDE ISSUE", "Demo26_real_evidence": "Changing the displayed complex component cannot cure a feature that moves with the integration cutoff."},
        {"Demo24_conclusion": "finite-k M(k) required", "classification": "WEAKENED", "Demo26_real_evidence": "Finite-k matrices remain required for the next discriminating test of cancellation and high-k damping, but existing perturbations do not prove that physical M(k) will cure the missing features."},
        {"Demo24_conclusion": "additional states required", "classification": "WEAKENED", "Demo26_real_evidence": "The missing 2.296 eV resonance remains, but the paper explicitly states only two bound states per band. Extra optical-sum states would change the stated model; structure/cutoff/state-tracking must be isolated first."},
        {"Demo24_conclusion": "geometry mismatch", "classification": "UNRELATED TO REAL-vs-MAGNITUDE ISSUE", "Demo26_real_evidence": "The published design/abrupt-interface versus Demo 23 linear-1-nm mismatch is independent of whether Re or magnitude is plotted."},
        {"Demo24_conclusion": "need for Demo 25 Professional run", "classification": "STILL VALID", "Demo26_real_evidence": "The observable reinterpretation fails the direct zero-crossing test and gives worse overall normalized RMSE, so unresolved finite-k/model-consistency questions remain."},
    ]


def fmt(value: object, digits: int = 4) -> str:
    if value == "" or value is None:
        return "N/A"
    if isinstance(value, (float, np.floating)):
        if math.isnan(float(value)):
            return "N/A"
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_table(rows: Sequence[dict[str, object]], columns: Sequence[str] | None = None) -> str:
    if not rows:
        return "_No rows._"
    columns = list(columns or rows[0].keys())
    line1 = "| " + " | ".join(columns) + " |"
    line2 = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(fmt(row.get(c, "")) for c in columns) + " |" for row in rows]
    return "\n".join([line1, line2, *body])


def final_report(
    spectrum: Spectrum,
    feature_rows: Sequence[dict[str, object]],
    zero_rows: Sequence[dict[str, object]],
    metrics: Sequence[dict[str, object]],
    reassessment: Sequence[dict[str, object]],
) -> str:
    overall = {row["comparison"]: row for row in metrics if row["region"] == "full_overlap"}
    re_m = overall["paper_vs_signed_Re_chi2"]
    abs_m = overall["paper_vs_abs_chi2"]
    zero_by_name = {row["paper_feature"]: row for row in zero_rows}
    feature_by_name = {row["Feature"]: row for row in feature_rows}
    review_path = OUTPUT_DIR / "PHYSICS_PROFESSOR_REVIEW_DEMO26_REAL.md"
    if review_path.exists():
        review_lines = review_path.read_text(encoding="utf-8").strip().splitlines()
        professor_section = "\n".join(("##" + line) if line.startswith("#") else line for line in review_lines)
    else:
        professor_section = "Independent review pending; see `PHYSICS_PROFESSOR_REVIEW_DEMO26_REAL.md` after the second-pass review."

    peak_lines = []
    for name in ("P1", "P2", "P3", "P4"):
        row = feature_by_name[name]
        peak_lines.append(
            f"- {name}: paper {row['Paper_wavelength_nm']:.0f} nm; signed Re {fmt(row['signed_Re_chi2_wavelength_nm'], 1)} nm; "
            f"|chi| {fmt(row['abs_chi2_wavelength_nm'], 1)} nm; better: {row['Which_observable_agrees_better_in_wavelength']}."
        )

    return f"""# Demo 26_real final report

## 1. Executive summary

The paper does **not** match normalized signed Re[chi2] better than normalized |chi2|. On the unchanged 400-1850 nm overlap, signed Re has normalized RMSE {re_m['normalized_RMSE']:.4f}, versus {abs_m['normalized_RMSE']:.4f} for |chi2|. Signed Re crosses zero at {zero_by_name['Z1']['nearest_Re_zero_crossing_nm']:.2f} and {zero_by_name['Z2']['nearest_Re_zero_crossing_nm']:.2f} nm, not near the paper's 605 and 1330 nm zero-valued features. The paper itself explicitly labels Figure 2d as simulated |chi2|, so the observable-reinterpretation hypothesis is rejected.

## 2. Why Demo 26_real was created

A colleague suggested that the paper curve might be signed Re[chi2], which would allow apparent zeros to be sign changes rather than complex-magnitude nodes. This demo tests only that observable interpretation while freezing all Demo 23D physics.

## 3. Available raw data

The existing data are sufficient. `23D_chi2.csv` contains the complex total as separate Re and Im columns plus |chi2|. Its stored magnitude agrees with `hypot(Re, Im)` to numerical precision. Tracked kp8 E(k) and frozen M(0) inputs also remain available, while finite-k matrix elements do not. See `DEMO26_REAL_INPUT_AUDIT.md`.

## 4. Observable-definition audit

The tested quantities are Re[chi2], Im[chi2], and |chi2| from the identical complex Demo 23D result. No denominator, Gamma, k weighting, kmax, matrix element, geometry, prefactor, or state was changed. The primary signed normalization is `Re/max|Re|`; it is never replaced by `|Re|`.

## 5. Paper figure/provenance audit

The published Figure 2d axis reads `Simulated |chi^(2)| (pm/V)`, begins at zero, and has no negative branch. The 45-point repo curve is an eye digitization, not author data, and is entirely nonnegative. Its zero-valued samples therefore carry no sign information. See `PAPER_OBSERVABLE_AUDIT.md`.

## 6. Re[chi] calculation

Signed Re[chi2] is read directly from the preserved Demo 23D complex spectrum. Its range is {np.min(spectrum.real):.4f} to {np.max(spectrum.real):.4f} pm/V. The normalized signed trace is shown in Figures 1, 2, 5, 6, and 7.

## 7. Im[chi] calculation

Im[chi2] is read from the same complex spectrum and ranges from {np.min(spectrum.imag):.4f} to {np.max(spectrum.imag):.4f} pm/V. Figure 3 shows it separately so the main comparison is not cluttered.

## 8. |chi| calculation

The magnitude is the stored and independently verified `hypot(Re, Im)`, ranging from {np.min(spectrum.magnitude):.4f} to {np.max(spectrum.magnitude):.4f} pm/V. Figure 4 shows the absolute spectrum.

## 9. Normalization conventions

- Paper: digitized nonnegative values divided by their maximum, with no absolute-value conversion.
- Signed real: `Re[chi2]/max|Re[chi2]|`, preserving sign.
- Secondary real envelope: `|Re[chi2]|/max|Re[chi2]|`, exported in the spectrum table but not substituted into the primary test.
- Magnitude: `|chi2|/max|chi2|`.

## 10. Full spectrum comparison

Figure 1 is the decisive overlay. |chi2| has the lower RMSE ({abs_m['normalized_RMSE']:.4f} vs {re_m['normalized_RMSE']:.4f}). Correlations are {re_m['correlation_coefficient']:.4f} for signed Re and {abs_m['correlation_coefficient']:.4f} for |chi2|; the higher Re correlation does not overcome its larger amplitude error, incorrect sign over broad intervals, missing features, or conflict with the paper label. Figure 9 shows the residuals.

## 11. 605-nm sign-flip analysis

At the paper wavelength, Re = {zero_by_name['Z1']['Re_at_paper_wavelength_pm_per_V']:.6f}, Im = {zero_by_name['Z1']['Im_at_paper_wavelength_pm_per_V']:.6f}, and |chi2| = {zero_by_name['Z1']['abs_chi_at_paper_wavelength_pm_per_V']:.6f} pm/V. The nearest Re crossing is {zero_by_name['Z1']['nearest_Re_zero_crossing_nm']:.3f} nm, bracketed by Re = {zero_by_name['Z1']['Re_before_pm_per_V']:.6f} at {zero_by_name['Z1']['left_sample_nm']:.0f} nm and {zero_by_name['Z1']['Re_after_pm_per_V']:.6f} at {zero_by_name['Z1']['right_sample_nm']:.0f} nm. Im and |chi2| at that interpolated crossing are {zero_by_name['Z1']['Im_at_interpolated_crossing_pm_per_V']:.6f} and {zero_by_name['Z1']['abs_chi_at_interpolated_crossing_pm_per_V']:.6f} pm/V. Re changes sign at the crossing, but **not near 605 nm**.

## 12. 1330-nm sign-flip analysis

At the paper wavelength, Re = {zero_by_name['Z2']['Re_at_paper_wavelength_pm_per_V']:.6f}, Im = {zero_by_name['Z2']['Im_at_paper_wavelength_pm_per_V']:.6f}, and |chi2| = {zero_by_name['Z2']['abs_chi_at_paper_wavelength_pm_per_V']:.6f} pm/V. The nearest Re crossing is {zero_by_name['Z2']['nearest_Re_zero_crossing_nm']:.3f} nm, bracketed by Re = {zero_by_name['Z2']['Re_before_pm_per_V']:.6f} at {zero_by_name['Z2']['left_sample_nm']:.0f} nm and {zero_by_name['Z2']['Re_after_pm_per_V']:.6f} at {zero_by_name['Z2']['right_sample_nm']:.0f} nm. Im and |chi2| at the crossing are {zero_by_name['Z2']['Im_at_interpolated_crossing_pm_per_V']:.6f} and {zero_by_name['Z2']['abs_chi_at_interpolated_crossing_pm_per_V']:.6f} pm/V. Re changes sign at the crossing, but **not near 1330 nm**.

## 13. Peak correspondence

{chr(10).join(peak_lines)}

No P1 or P3 correspondence is forced when a significant interior extremum is absent. Full rows are in `DEMO26_REAL_FEATURE_COMPARISON.csv` and Figure 10.

## 14. Quantitative Re-vs-|chi| comparison

{markdown_table([re_m, abs_m], ['comparison', 'normalized_RMSE', 'correlation_coefficient', 'normalized_MAE', 'matched_peak_count', 'peak_wavelength_MAE_nm', 'zero_or_minimum_feature_MAE_nm'])}

Local 500-700, 700-900, 950-1200, 1200-1450, and 1420-1620 nm metrics are in `DEMO26_REAL_METRICS.csv`. The primary decision uses the same paper interpolation and normalization for both model observables.

## 15. Demo 24 reassessment

{markdown_table(reassessment, ['Demo24_conclusion', 'classification', 'Demo26_real_evidence'])}

The real-vs-magnitude idea invalidates none of Demo 24's main discrepancy findings. It weakens causal claims that finite-k M(k) or added states are already established remedies: both remain hypotheses requiring a controlled Professional test, and the paper itself says the optical sum uses the first two bound states per band.

## 16. Independent professor review

{professor_section}

## 17. Do we still need Demo 25?

**DEMO 25 STILL REQUIRED.** Signed Re gives worse normalized RMSE, does not put zero crossings near either paper deep minimum, and does not restore P1/P3. A targeted Professional run remains scientifically justified to obtain a self-consistent extended-k calculation and finite-k complex O_nm(k), z_e(k), and z_hh(k), while isolating the paper geometry/cutoff/state-tracking issues identified by Demo 24. Finite-k M(k) is the quantity required for that test, not a cure already established by the present data. This is not a request to run it on the home laptop.

## 18. Final conclusion

The central hypothesis is rejected: the previous discrepancy was not caused by comparing the paper to the wrong observable. The paper explicitly displays magnitude, and the model's real-part zeros occur roughly 108 nm away from the paper's two digitized baseline contacts. Those eye-digitized contacts are apparent deep minima, not proof of exact analytic zeros. Demo 24 therefore remains materially intact, and Demo 25 remains warranted for the unresolved finite-k/model-consistency questions.
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    spectrum, paper = load_inputs()
    paper_norm = normalize_absmax(paper.value)
    paper_interp = np.interp(spectrum.wavelength_nm, paper.wavelength_nm, paper_norm)
    re_norm = normalize_absmax(spectrum.real)
    abs_re_norm = normalize_absmax(np.abs(spectrum.real))
    abs_norm = normalize_absmax(spectrum.magnitude)

    feature_rows, zero_rows = build_feature_rows(spectrum, paper, re_norm, abs_norm)
    metrics = metric_rows(spectrum.wavelength_nm, paper_interp, re_norm, abs_norm, feature_rows)
    reassessment = reassessment_rows()

    spectra_rows = []
    for i, wavelength in enumerate(spectrum.wavelength_nm):
        spectra_rows.append(
            {
                "wavelength_nm": float(wavelength),
                "Re_chi2_pm_per_V": float(spectrum.real[i]),
                "Im_chi2_pm_per_V": float(spectrum.imag[i]),
                "abs_chi2_pm_per_V": float(spectrum.magnitude[i]),
                "paper_interpolated_pm_per_V": interp_at(paper.wavelength_nm, paper.value, wavelength),
                "paper_normalized": float(paper_interp[i]),
                "signed_Re_normalized": float(re_norm[i]),
                "abs_Re_envelope_normalized": float(abs_re_norm[i]),
                "abs_chi2_normalized": float(abs_norm[i]),
            }
        )

    write_csv(OUTPUT_DIR / "DEMO26_REAL_SPECTRA.csv", spectra_rows)
    write_csv(OUTPUT_DIR / "DEMO26_REAL_FEATURE_COMPARISON.csv", feature_rows)
    write_csv(OUTPUT_DIR / "DEMO26_REAL_ZERO_CROSSINGS.csv", zero_rows)
    write_csv(OUTPUT_DIR / "DEMO26_REAL_METRICS.csv", metrics)
    write_csv(OUTPUT_DIR / "DEMO24_CONCLUSION_REASSESSMENT.csv", reassessment)
    write_text(OUTPUT_DIR / "DEMO26_REAL_INPUT_AUDIT.md", input_audit())
    write_text(OUTPUT_DIR / "PAPER_OBSERVABLE_AUDIT.md", paper_audit())
    make_plots(spectrum, paper, paper_interp, re_norm, abs_norm, feature_rows)
    write_text(OUTPUT_DIR / "DEMO26_REAL_FINAL_REPORT.md", final_report(spectrum, feature_rows, zero_rows, metrics, reassessment))

    overall = {row["comparison"]: row for row in metrics if row["region"] == "full_overlap"}
    summary = {
        "status": "COMPLETE",
        "paper_observable": "explicitly |chi^(2)| in Figure 2d",
        "main_result": "paper does not match signed Re[chi2] better",
        "paper_vs_signed_Re_RMSE": overall["paper_vs_signed_Re_chi2"]["normalized_RMSE"],
        "paper_vs_abs_chi_RMSE": overall["paper_vs_abs_chi2"]["normalized_RMSE"],
        "paper_vs_signed_Re_correlation": overall["paper_vs_signed_Re_chi2"]["correlation_coefficient"],
        "paper_vs_abs_chi_correlation": overall["paper_vs_abs_chi2"]["correlation_coefficient"],
        "demo25_verdict": "DEMO 25 STILL REQUIRED",
        "professional_solver_invoked": False,
        "primary_plot": str((PLOT_DIR / "figure01_paper_vs_signed_real_vs_magnitude.png").resolve()),
    }
    write_text(OUTPUT_DIR / "demo26_real_summary.json", json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
