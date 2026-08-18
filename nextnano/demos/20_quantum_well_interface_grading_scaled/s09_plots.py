"""Stage 09 - every figure, built from standardized processed data.

Two groups:

**01-10** reproduce Demo 19's figure set one for one, keeping Demo 19's file
numbering so the two demos' output directories can be compared side by side.
Where Demo 19 read a column from its master table, Demo 20 reads the same
quantity from the analysis rows.

**11-13** are Demo 20's normalization diagnostics: raw vs scaled at the target
wavelength, the scaling ratio, and the raw vs scaled spectrum of the reference
case. They exist to make the claim "this changes magnitude and nothing else"
visually checkable.

This module contains no physics. It never recomputes a susceptibility; it plots
what :mod:`s07_analysis` already produced.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import s01_cases as cases
import s02_grading as grading
import s06_chi2 as chi2mod
import s07_analysis as analysis

#: Demo 19's own figure numbering, preserved.
DEMO19_FIGURES = (
    "01_grading_composition_profiles.png",
    "02_grading_profile_shapes.png",
    "03_abrupt_vs_graded_wavefunctions.png",
    "04_chi2_spectra_linear_grading.png",
    "05_grade_width_vs_chi2_1550.png",
    "06_grade_width_relative_to_abrupt.png",
    "07_grade_width_vs_peak_wavelength.png",
    "08_grading_location_comparison.png",
    "09_profile_shape_chi2_comparison.png",
    "10_grading_summary_heatmap.png",
)
DEMO20_FIGURES = (
    "11_raw_vs_scaled_chi2_1550.png",
    "12_scaling_ratio_by_case.png",
    "13_reference_raw_vs_scaled_spectrum.png",
)

LINEAR_SERIES = ("00", "01", "02", "03", "04", "05")
SPECTRA_SERIES = (("00", "Abrupt"), ("02", "0.4 nm"), ("03", "0.7 nm"),
                  ("04", "1.0 nm"), ("05", "1.4 nm"))
LOCATION_SERIES = (("00", "Abrupt"), ("08", "Inner-only"), ("09", "Outer-only"),
                   ("06", "I2=.4 / I3=.8"), ("07", "I2=.8 / I3=.4"))
SHAPE_SERIES = (("03", "Linear 0.7"), ("10", "Fermi 0.7"), ("11", "erf 0.7"),
                ("12", "Cosine 0.7"))
HEATMAP_KEYS = (
    ("E2_HH2_eV", "E2-HH2"), ("O22", "O22"), ("z_e12_nm", "z_e12"),
    ("z_hh12_nm", "z_hh12"), ("chi2_reported_1550_pm_per_V", "chi2"),
    ("raw_peak_wavelength_nm", "peak nm"),
)


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _finish(fig, path: Path, dpi: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    _plt().close(fig)
    return path


def _number(row: Mapping[str, Any], key: str) -> float:
    value = row.get(key)
    if value in (None, ""):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _bar(path: Path, labels: Sequence[str], values: Sequence[float],
         title: str, ylabel: str, dpi: int, color: str = "#3b73a8") -> Path:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    ax.bar(np.arange(len(labels)), values, color=color)
    ax.set_xticks(np.arange(len(labels)), labels, rotation=20, ha="right")
    ax.set(title=title, ylabel=ylabel)
    ax.grid(axis="y", alpha=0.18)
    return _finish(fig, path, dpi)


# --- 01-02: composition profiles (solver-free, always available) -------------


def input_plots(cfg: Mapping[str, Any], destination: Path) -> list[Path]:
    """Figures 01 and 02. These need no solver and no analysis."""

    plt = _plt()
    dpi = int(cfg["plots"]["dpi"])
    destination = Path(destination)
    lookup = cases.by_id()
    g = grading.geometry(cfg)
    high = float(cfg["materials"]["barrier_al_fraction"])

    # 01: whole-device composition across the active stack.
    z = np.linspace(g.active_start_nm - 1.6, g.active_end_nm + 1.6, 6001)
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    for case_id, label in SPECTRA_SERIES:
        ax.plot(z, grading.evaluate_composition(cfg, lookup[case_id], z, rendered=True),
                label=label, lw=1.8)
    ax.set(xlabel="Position z (nm)", ylabel="Al fraction $x_{Al}$",
           title="Interface Grading Profiles")
    ax.set_ylim(-0.025, high + 0.025)
    ax.legend(frameon=False, ncol=3)
    ax.grid(alpha=0.18)
    first = _finish(fig, destination / DEMO19_FIGURES[0], dpi)

    # 02: shape comparison at one interface, all four families at 0.7 nm.
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    offset = np.linspace(-0.55, 0.55, 2001)
    centre = grading.interface_positions(cfg)["I2"]
    for case_id, label in (("00", "Abrupt"), ("03", "Linear"), ("10", "Fermi"),
                           ("11", "erf"), ("12", "Cosine")):
        ax.plot(offset, grading.evaluate_composition(
            cfg, lookup[case_id], centre + offset, rendered=True), label=label, lw=2)
    ax.set(xlabel="Position relative to interface (nm)",
           ylabel="Al fraction $x_{Al}$", title="Grading Profile Shape")
    ax.set_ylim(-0.025, high + 0.025)
    ax.legend(frameon=False)
    ax.grid(alpha=0.18)
    second = _finish(fig, destination / DEMO19_FIGURES[1], dpi)
    return [first, second]


# --- 03-10: Demo 19's physics figures ---------------------------------------


def physics_plots(
    cfg: Mapping[str, Any], destination: Path,
    results: Sequence[analysis.CaseAnalysis],
    *, wavefunction_data: Mapping[str, Path] | None = None,
) -> list[Path]:
    """Figures 03-10, reproducing Demo 19's set.

    Figure 03 needs per-state envelope data, which only exists beside a raw
    licensed run. When that data is absent (the home-laptop path) the figure is
    skipped rather than drawn from something else, and the skip is reported.
    """

    plt = _plt()
    dpi = int(cfg["plots"]["dpi"])
    destination = Path(destination)
    rows = [result.row for result in results]
    by_id = {str(row["case_id"]): row for row in rows}
    spectra = analysis.spectra_by_case(results, convention="reported")
    made: list[Path] = []

    # 03: band edges and the first two states of each band, abrupt vs graded.
    wave_paths = dict(wavefunction_data or {})
    if all(case_id in wave_paths and Path(wave_paths[case_id]).is_file()
           for case_id in ("00", "03")):
        fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True, sharey=True)
        for ax, case_id, label in zip(axes, ("00", "03"), ("Abrupt", "0.7 nm")):
            data = np.genfromtxt(Path(wave_paths[case_id]), delimiter=",", names=True)
            ax.plot(data["z_nm"], data["conduction_eV"], color="black", lw=1.2)
            ax.plot(data["z_nm"], data["heavy_hole_eV"], color="0.35", lw=1.2)
            for key, color in (("E1", "#1f77b4"), ("E2", "#4fa3df"),
                               ("HH1", "#d62728"), ("HH2", "#ff7f7f")):
                ax.plot(data["z_nm"], data[key], color=color, lw=1.0, label=key)
            ax.text(0.01, 0.90, label, transform=ax.transAxes)
            ax.grid(alpha=0.15)
        axes[0].legend(frameon=False, ncol=4)
        axes[-1].set_xlabel("Position z (nm)")
        fig.supylabel("Energy / scaled probability (eV)")
        fig.suptitle("Abrupt vs 0.7 nm Grading")
        made.append(_finish(fig, destination / DEMO19_FIGURES[2], dpi))

    # 04: chi2 spectra across the linear grading series.
    if spectra:
        fig, ax = plt.subplots(figsize=(8.2, 4.8))
        for case_id, label in SPECTRA_SERIES:
            if case_id in spectra:
                ax.plot(*spectra[case_id], label=label, lw=1.8)
        target = float(cfg["chi2"]["target_wavelength_nm"])
        ax.axvline(target, color="black", ls="--", lw=1)
        ax.set(xlabel="Wavelength (nm)", ylabel="$|\\chi^{(2)}|$ (pm/V)",
               title=f"Grading Dependence of $\\chi^{{(2)}}$ "
                     f"({_convention_label(cfg)})")
        ax.legend(frameon=False)
        ax.grid(alpha=0.18)
        made.append(_finish(fig, destination / DEMO19_FIGURES[3], dpi))

    # 05-07: the three grading-width trends.
    widths = [_number(by_id[c], "nominal_grade_width_nm") for c in LINEAR_SERIES]
    series = (
        (DEMO19_FIGURES[4],
         [_number(by_id[c], "chi2_reported_1550_pm_per_V") for c in LINEAR_SERIES],
         "$|\\chi^{(2)}(1550)|$ (pm/V)", "$\\chi^{(2)}$ vs Grading Width"),
        (DEMO19_FIGURES[5],
         [_number(by_id[c], "chi2_raw_1550_relative_to_reference")
          for c in LINEAR_SERIES],
         "$\\chi^{(2)}(1550)$ / Abrupt", "Relative Response to Abrupt"),
        (DEMO19_FIGURES[6],
         [_number(by_id[c], "raw_peak_wavelength_nm") for c in LINEAR_SERIES],
         "Peak wavelength (nm)", "Peak Wavelength vs Grading"),
    )
    for filename, values, ylabel, title in series:
        if not np.any(np.isfinite(values)):
            continue
        fig, ax = plt.subplots(figsize=(7.2, 4.5))
        ax.plot(widths, values, marker="o", lw=1.8)
        if filename.startswith("06_"):
            ax.axhline(1.0, color="black", ls="--", lw=1)
        ax.set(xlabel="Grading width (nm)", ylabel=ylabel, title=title)
        ax.grid(alpha=0.18)
        made.append(_finish(fig, destination / filename, dpi))

    # 08: grading location.
    location_values = [_number(by_id[c], "chi2_reported_1550_pm_per_V")
                       for c, _ in LOCATION_SERIES]
    if np.any(np.isfinite(location_values)):
        made.append(_bar(destination / DEMO19_FIGURES[7],
                         [label for _, label in LOCATION_SERIES], location_values,
                         "Effect of Grading Location",
                         "$|\\chi^{(2)}(1550)|$ (pm/V)", dpi))

    # 09: profile shape.
    shape_values = [_number(by_id[c], "chi2_reported_1550_pm_per_V")
                    for c, _ in SHAPE_SERIES]
    if np.any(np.isfinite(shape_values)):
        made.append(_bar(destination / DEMO19_FIGURES[8],
                         [label for _, label in SHAPE_SERIES], shape_values,
                         "Effect of Grading Profile",
                         "$|\\chi^{(2)}(1550)|$ (pm/V)", dpi))

    # 10: column-normalized summary heatmap over all cases.
    matrix = np.asarray([[_number(row, key) for key, _ in HEATMAP_KEYS]
                         for row in rows], dtype=float)
    if matrix.size and np.all(np.isfinite(matrix)):
        span = np.ptp(matrix, axis=0)
        normalized = (matrix - np.min(matrix, axis=0)) / np.where(span == 0, 1, span)
        fig, ax = plt.subplots(figsize=(8.2, 6.0))
        image = ax.imshow(normalized, aspect="auto", cmap="viridis")
        ax.set_xticks(range(len(HEATMAP_KEYS)), [label for _, label in HEATMAP_KEYS])
        ax.set_yticks(range(len(rows)), [row["case_id"] for row in rows])
        ax.set(title="Grading Summary")
        fig.colorbar(image, ax=ax, label="Column-normalized value")
        made.append(_finish(fig, destination / DEMO19_FIGURES[9], dpi))
    return made


def _convention_label(cfg: Mapping[str, Any]) -> str:
    return ("$(2\\pi)^2$-scaled convention"
            if bool(cfg["chi2"]["apply_kspace_2pi_squared_scaling"])
            else "Demo 19 convention")


# --- 11-13: Demo 20's normalization diagnostics -----------------------------


def scaling_plots(
    cfg: Mapping[str, Any], destination: Path,
    results: Sequence[analysis.CaseAnalysis],
) -> list[Path]:
    """Plots A, B and C from the Demo 20 brief, as figures 11, 12 and 13."""

    plt = _plt()
    dpi = int(cfg["plots"]["dpi"])
    destination = Path(destination)
    with_spectra = [r for r in results if r.has_spectrum]
    if not with_spectra:
        return []
    made: list[Path] = []
    target = float(cfg["chi2"]["target_wavelength_nm"])
    paper = float(cfg["paper"]["target_chi2_pm_per_V"])
    labels = [f"{r.case_id} {r.row['case_name']}" for r in with_spectra]
    raw = [float(r.row["chi2_raw_1550_pm_per_V"]) for r in with_spectra]
    scaled = [float(r.row["chi2_scaled_1550_pm_per_V"]) for r in with_spectra]

    # 11 (Plot A): raw vs scaled side by side. Log scale, because the two
    # conventions differ by a factor of ~39 and a linear axis would flatten the
    # raw series into the baseline.
    fig, ax = plt.subplots(figsize=(10.0, 5.2))
    index = np.arange(len(labels))
    ax.bar(index - 0.2, raw, width=0.4, label="Demo 19 convention (raw)",
           color="#3b73a8")
    ax.bar(index + 0.2, scaled, width=0.4,
           label="$(2\\pi)^2$-scaled convention", color="#c8792b")
    ax.axhline(paper, color="black", ls="--", lw=1.2)
    ax.set_yscale("log")
    # Headroom above the target line, so the legend and the target annotation
    # both sit in clear space instead of colliding with the line.
    floor = max(min(raw) / 4.0, 1e-3)
    ax.set_ylim(floor, paper * 4.0)
    ax.text(len(labels) - 0.5, paper * 1.12, f"Paper target ~{paper:g} pm/V",
            ha="right", va="bottom", fontsize=9)
    ax.set_xticks(index, labels, rotation=28, ha="right", fontsize=8)
    ax.set(ylabel="$|\\chi^{(2)}(1550)|$ (pm/V)",
           title="Raw vs $(2\\pi)^2$-Scaled Susceptibility at "
                 f"{target:.0f} nm")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.grid(axis="y", alpha=0.18, which="both")
    made.append(_finish(fig, destination / DEMO20_FIGURES[0], dpi))

    # 12 (Plot B): the ratio, which must be (2*pi)^2 for every case.
    expected = chi2mod.two_pi_squared()
    ratios = [s / r if r else np.nan for s, r in zip(scaled, raw)]
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    ax.bar(index, ratios, color="#5a8f5a")
    ax.axhline(expected, color="black", ls="--", lw=1.2,
               label=f"$(2\\pi)^2$ = {expected:.6f}")
    ax.set_xticks(index, labels, rotation=28, ha="right", fontsize=8)
    ax.set(ylabel="$|\\chi^{(2)}_{scaled}| / |\\chi^{(2)}_{raw}|$",
           title="Scaling Ratio by Case")
    # A tight window around the expected value, so any real deviation is visible
    # rather than being hidden by an autoscaled axis.
    ax.set_ylim(expected * 0.999, expected * 1.001)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.18)
    made.append(_finish(fig, destination / DEMO20_FIGURES[1], dpi))

    # 13 (Plot C): both spectra of the reference case, plus the normalized
    # lineshapes on a twin axis to show the shape is untouched.
    reference_id = str(cfg["analysis"]["reference_case_id"])
    reference = next((r for r in with_spectra if r.case_id == reference_id),
                     with_spectra[0])
    pair = reference.pair
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8.6, 6.8), sharex=True)
    top.plot(pair.raw.wavelength_nm, pair.raw.magnitude, lw=1.9,
             color="#3b73a8", label="Demo 19 convention (raw)")
    top.plot(pair.scaled.wavelength_nm, pair.scaled.magnitude, lw=1.9,
             color="#c8792b", label="$(2\\pi)^2$-scaled")
    top.axvline(target, color="black", ls="--", lw=1)
    top.set_yscale("log")
    top.set(ylabel="$|\\chi^{(2)}|$ (pm/V)",
            title=f"Case {reference.case_id} - {reference.row['case_name']}: "
                  "magnitude changes, spectrum does not")
    top.legend(frameon=False)
    top.grid(alpha=0.18, which="both")
    bottom.plot(pair.raw.wavelength_nm, pair.raw.normalized_magnitude(), lw=2.6,
                color="#3b73a8", label="raw, normalized")
    bottom.plot(pair.scaled.wavelength_nm, pair.scaled.normalized_magnitude(),
                lw=1.2, ls="--", color="#c8792b", label="scaled, normalized")
    bottom.axvline(target, color="black", ls="--", lw=1)
    bottom.set(xlabel="Wavelength (nm)", ylabel="$|\\chi^{(2)}|$ / peak")
    bottom.legend(frameon=False)
    bottom.grid(alpha=0.18)
    made.append(_finish(fig, destination / DEMO20_FIGURES[2], dpi))
    return made


def all_plots(
    cfg: Mapping[str, Any], destination: Path,
    results: Sequence[analysis.CaseAnalysis],
    *, wavefunction_data: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Every figure Demo 20 can draw from what is available."""

    if not bool(cfg["plots"]["enabled"]):
        return {"enabled": False, "made": [], "skipped": list(DEMO19_FIGURES)
                + list(DEMO20_FIGURES)}
    made = input_plots(cfg, destination)
    made += physics_plots(cfg, destination, results,
                          wavefunction_data=wavefunction_data)
    made += scaling_plots(cfg, destination, results)
    names = {path.name for path in made}
    skipped = [name for name in DEMO19_FIGURES + DEMO20_FIGURES
               if name not in names]
    return {
        "enabled": True,
        "made": [str(path) for path in made],
        "skipped": skipped,
        "skip_reasons": {
            name: ("needs per-state envelope data from a raw licensed run"
                   if name == DEMO19_FIGURES[2] else
                   "no case produced the required column")
            for name in skipped
        },
    }
