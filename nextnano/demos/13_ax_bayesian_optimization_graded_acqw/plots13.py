"""Every Demo 13 figure, and the CSV that sits beside each one.

Plot policy (Section 15), enforced here rather than left to discipline:

* **no titles**, no subtitles, no text boxes, no captions, no interpretation
  inside a figure.  A figure carries axis labels with units, tick labels, a
  concise legend, a colourbar label, and at most a small ``(a)``/``(b)`` panel
  label.  Everything a reader needs to interpret it lives in ``PLOTS_GUIDE.md``;
* **raw evaluated points are never smoothed.**  Observed data is drawn as
  markers.  The only continuous surfaces in this demo are surrogate-model
  predictions, and those are drawn as a filled mesh with the evaluated points
  overlaid on top, so the two can never be confused;
* **every figure has a CSV with the same base filename**, holding exactly the
  numbers that were drawn.

Figures are written as PNG and PDF.  A figure with no data becomes the shared
labelled placeholder, so a missing file is always a bug and never "no licence".
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import plots as plotting  # noqa: E402

#: Axis labels, written once so the same quantity never appears under two names.
AXIS: Mapping[str, str] = {
    "trial": "Trial number",
    "iteration": "BO iteration",
    "objective": "Objective value",
    "best_objective": "Best objective value",
    "chi2_target": "|χ²| at 1550 nm (a.u.)",
    "peak_chi2": "Peak |χ²| (a.u.)",
    "peak_wavelength": "Peak wavelength (nm)",
    "detuning": "Detuning from 1550 nm (nm)",
    "asymmetry": "Quantum-well asymmetry, s",
    "barrier": "Central barrier thickness (nm)",
    "grading": "Grading thickness (nm)",
    "profile": "Grading profile",
    "boundary": "Boundary probability",
    "confidence": "State-tracking confidence",
    "wavelength": "Fundamental wavelength (nm)",
    "normalized_chi2": "Normalized |χ²| (a.u.)",
    "position": "Position (nm)",
    "aluminium": "Al fraction, x",
    "energy": "Energy (eV)",
    "amplitude": "Envelope amplitude (a.u.)",
    "probability": "Probability",
    "importance": "First-order Sobol index",
    "evaluations": "Evaluations",
    "count": "Trials",
    "robustness": "Robustness score",
    "transition": "Transition energy (eV)",
    "sh_intensity": "Measured SH intensity (a.u.)",
}

#: Marker per grading profile, so shape carries the categorical variable and
#: colour is left free for the objective.
PROFILE_MARKERS: Mapping[str, str] = {
    "abrupt": "o",
    "linear": "s",
    "sigmoid": "^",
    "erf": "D",
    "cosine": "v",
}

#: The complete figure set: filename and the scientific question it answers.
PLOT_SET: tuple[tuple[str, str], ...] = (
    ("bo_objective_value_by_trial.png", "Objective of each evaluated trial"),
    ("bo_best_objective_so_far_by_iteration.png", "Best valid objective per BO iteration"),
    ("bo_chi2_at_1550_by_trial.png", "Target-wavelength response per trial"),
    ("bo_peak_chi2_by_trial.png", "Intrinsic peak response per trial"),
    ("bo_resonance_wavelength_by_trial.png", "Resonance wavelength per trial"),
    ("bo_detuning_from_1550_by_trial.png", "Detuning from the target per trial"),
    ("bo_asymmetry_vs_grading_thickness_objective.png", "Sampling in asymmetry and grading"),
    ("bo_barrier_thickness_vs_grading_thickness_objective.png", "Sampling in barrier and grading"),
    ("bo_asymmetry_vs_barrier_thickness_objective.png", "Sampling in asymmetry and barrier"),
    ("bo_grading_profile_objective_distribution.png", "Objective distribution per profile"),
    ("bo_parameter_sampling_by_iteration.png", "Where each iteration sampled"),
    ("bo_surrogate_mean_asymmetry_vs_grading_thickness.png", "Surrogate mean over asymmetry and grading"),
    ("bo_surrogate_uncertainty_asymmetry_vs_grading_thickness.png", "Surrogate uncertainty over asymmetry and grading"),
    ("bo_acquisition_function_asymmetry_vs_grading_thickness.png", "Expected improvement over asymmetry and grading"),
    ("bo_surrogate_mean_barrier_vs_grading_thickness.png", "Surrogate mean over barrier and grading"),
    ("bo_surrogate_uncertainty_barrier_vs_grading_thickness.png", "Surrogate uncertainty over barrier and grading"),
    ("bo_peak_chi2_vs_detuning_pareto.png", "Intrinsic strength against wavelength match"),
    ("bo_chi2_1550_vs_peak_chi2.png", "Target response against intrinsic peak"),
    ("bo_chi2_1550_vs_boundary_probability.png", "Target response against confinement quality"),
    ("bo_chi2_1550_vs_state_tracking_confidence.png", "Target response against tracking confidence"),
    ("bo_nonlinear_strength_vs_robustness_pareto.png", "Strength against fabrication robustness"),
    ("bo_parameter_importance.png", "Surrogate sensitivity per parameter"),
    ("bo_partial_dependence_asymmetry.png", "Surrogate dependence on asymmetry"),
    ("bo_partial_dependence_barrier_thickness.png", "Surrogate dependence on barrier thickness"),
    ("bo_partial_dependence_grading_thickness.png", "Surrogate dependence on grading thickness"),
    ("bo_grading_profile_effect.png", "Observed effect of grading profile"),
    ("bo_valid_and_invalid_trials_by_iteration.png", "Valid and invalid trials per iteration"),
    ("bo_failure_reason_counts.png", "Why trials were rejected or failed"),
    ("bo_boundary_probability_by_trial.png", "Boundary probability per trial"),
    ("bo_state_tracking_confidence_by_trial.png", "Tracking confidence per trial"),
    ("bo_validity_map_asymmetry_vs_grading_thickness.png", "Where valid designs live"),
    ("baseline_and_top_bo_designs_chi2_spectra.png", "Baseline and top BO spectra"),
    ("baseline_and_best_bo_composition_profiles.png", "Baseline and best composition profiles"),
    ("baseline_and_best_bo_conduction_band_edges.png", "Baseline and best conduction band edges"),
    ("baseline_and_best_bo_valence_band_edges.png", "Baseline and best valence band edges"),
    ("baseline_and_best_bo_electron_wavefunctions.png", "Baseline and best electron envelopes"),
    ("baseline_and_best_bo_hole_wavefunctions.png", "Baseline and best hole envelopes"),
    ("baseline_and_best_bo_state_localization.png", "Baseline and best state localization"),
    ("baseline_and_best_bo_transition_energies.png", "Baseline and best transition energies"),
    ("top_bo_designs_chi2_spectra.png", "Spectra of the top BO designs"),
    ("bo_vs_random_search_best_objective.png", "BO against random search"),
    ("bo_vs_grid_search_best_objective.png", "BO against grid search"),
    ("bo_random_grid_evaluations_to_best_known_result.png", "Evaluations to the best known design"),
    ("demo11_demo12_demo13_best_chi2_spectra.png", "Demo 11, 12 and 13 best spectra"),
    ("paper_figure2d_simulation_comparison_full_range.png", "Paper comparison, full range"),
    ("paper_figure2d_simulation_comparison_telecom_range.png", "Paper comparison, telecom range"),
    ("paper_measured_sh_intensity_comparison.png", "Measured SH intensity, plotted separately"),
)

PLACEHOLDER_REASON = (
    "No licensed nextnano++ output for this figure yet; raw points are never "
    "smoothed and never invented"
)


@dataclass
class PlotContext:
    """Everything the figure set draws from."""

    cfg: Mapping[str, Any]
    records: Sequence[Mapping[str, Any]] = ()
    objective_metric: str = "relative_chi2_at_target_wavelength_abs"
    objective_direction: str = "maximize"
    best_by_iteration: Sequence[Mapping[str, Any]] = ()
    surrogate_slices: Mapping[str, Sequence[Mapping[str, Any]]] = field(default_factory=dict)
    partial_dependence: Mapping[str, Sequence[Mapping[str, Any]]] = field(default_factory=dict)
    importance_rows: Sequence[Mapping[str, Any]] = ()
    efficiency: Mapping[str, Any] = field(default_factory=dict)
    spectra: Sequence[Mapping[str, Any]] = ()
    profiles: Sequence[Mapping[str, Any]] = ()
    band_edges: Sequence[Mapping[str, Any]] = ()
    envelopes: Sequence[Mapping[str, Any]] = ()
    paper_curves: Sequence[Mapping[str, Any]] = ()
    measured_curves: Sequence[Mapping[str, Any]] = ()
    robustness_rows: Sequence[Mapping[str, Any]] = ()
    synthetic: bool = False

    @property
    def completed(self) -> list[Mapping[str, Any]]:
        return [row for row in self.records if str(row.get("status")) == "completed"]

    @property
    def valid(self) -> list[Mapping[str, Any]]:
        return [row for row in self.completed if row.get("trial_valid")]


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------


def _write_csv(base: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    """The CSV that matches a figure, written even when the figure is empty."""

    path = base.parent.parent / "plot_data" / f"{base.stem}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [dict(row) for row in rows]
    fieldnames: list[str] = []
    for row in data:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(str(key))
    if not fieldnames:
        fieldnames = ["note"]
        data = [{"note": "no plotted data in this run"}]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(
                {
                    key: (
                        None
                        if isinstance(row.get(key), float) and not math.isfinite(row[key])
                        else row.get(key)
                    )
                    for key in fieldnames
                }
            )
    return path


def _figure(size: tuple[float, float] = (6.4, 4.2)):
    if plotting.plt is None:  # pragma: no cover - environment specific
        return None, None
    return plotting.plt.subplots(figsize=size)


def _finish(fig: Any, path: Path) -> None:
    plotting.save_figure_formats(fig, path, formats=("png", "pdf"))


def _placeholder(path: Path) -> None:
    plotting.placeholder(path, path.stem, reason=PLACEHOLDER_REASON)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _series_plot(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    x_key: str,
    y_key: str,
    xlabel: str,
    ylabel: str,
    step: bool = False,
    axhline: float | None = None,
    logy: bool = False,
    group_key: str | None = None,
) -> None:
    """Markers for observed points; an optional step line for a running best."""

    data = [
        (row, _number(row.get(x_key)), _number(row.get(y_key)))
        for row in rows
    ]
    usable = [(row, x, y) for row, x, y in data if x is not None and y is not None]
    _write_csv(path, [{**dict(row), x_key: x, y_key: y} for row, x, y in usable])
    if not usable:
        _placeholder(path)
        return
    fig, ax = _figure()
    if fig is None:
        _placeholder(path)
        return
    if group_key is None:
        xs = [x for _, x, _ in usable]
        ys = [y for _, _, y in usable]
        if step:
            order = np.argsort(np.asarray(xs))
            ax.step(
                np.asarray(xs)[order], np.asarray(ys)[order], where="post", linewidth=1.4
            )
        ax.plot(xs, ys, "o", markersize=5)
    else:
        groups: dict[str, list[tuple[float, float]]] = {}
        for row, x, y in usable:
            groups.setdefault(str(row.get(group_key, "")), []).append((x, y))
        for name, points in sorted(groups.items()):
            ax.plot(
                [x for x, _ in points],
                [y for _, y in points],
                PROFILE_MARKERS.get(name, "o"),
                markersize=5,
                label=name,
            )
        ax.legend(fontsize=8, frameon=False)
    if axhline is not None:
        ax.axhline(axhline, color="0.6", linewidth=0.8, linestyle="--")
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    _finish(fig, path)


def _scatter_coloured(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    x_key: str,
    y_key: str,
    colour_key: str,
    xlabel: str,
    ylabel: str,
    colour_label: str,
    marker_key: str | None = "parameter_grading_profile",
    extra_keys: Sequence[str] = (),
) -> None:
    """Two design coordinates, colour by objective, marker shape by profile."""

    usable = []
    for row in rows:
        x, y = _number(row.get(x_key)), _number(row.get(y_key))
        colour = _number(row.get(colour_key))
        if x is not None and y is not None and colour is not None:
            usable.append((row, x, y, colour))
    _write_csv(
        path,
        [
            {
                x_key: x,
                y_key: y,
                colour_key: colour,
                **(
                    {marker_key: row.get(marker_key)}
                    if marker_key
                    else {}
                ),
                **{key: row.get(key) for key in extra_keys},
            }
            for row, x, y, colour in usable
        ],
    )
    if not usable:
        _placeholder(path)
        return
    fig, ax = _figure((6.6, 4.6))
    if fig is None:
        _placeholder(path)
        return
    groups: dict[str, list[tuple[float, float, float]]] = {}
    for row, x, y, colour in usable:
        key = str(row.get(marker_key, "")) if marker_key else ""
        groups.setdefault(key, []).append((x, y, colour))
    values = [colour for _, _, _, colour in usable]
    vmin, vmax = min(values), max(values)
    mappable = None
    for name, points in sorted(groups.items()):
        mappable = ax.scatter(
            [x for x, _, _ in points],
            [y for _, y, _ in points],
            c=[colour for _, _, colour in points],
            marker=PROFILE_MARKERS.get(name, "o"),
            s=48,
            vmin=vmin,
            vmax=vmax,
            edgecolors="0.25",
            linewidths=0.5,
            label=name or None,
        )
    if mappable is not None:
        fig.colorbar(mappable, ax=ax).set_label(colour_label)
    if len(groups) > 1:
        ax.legend(fontsize=8, frameon=False, loc="best")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    _finish(fig, path)


def _surface(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    x_key: str,
    y_key: str,
    z_key: str,
    xlabel: str,
    ylabel: str,
    colour_label: str,
    observed: Sequence[tuple[float, float]] = (),
) -> None:
    """A surrogate-predicted surface with the evaluated points drawn on top."""

    usable = [
        (
            _number(row.get(x_key)),
            _number(row.get(y_key)),
            _number(row.get(z_key)),
            row,
        )
        for row in rows
    ]
    usable = [item for item in usable if None not in item[:3]]
    _write_csv(path, [dict(row) for *_ignored, row in usable])
    if len(usable) < 4:
        _placeholder(path)
        return
    xs = sorted({item[0] for item in usable})
    ys = sorted({item[1] for item in usable})
    if len(xs) < 2 or len(ys) < 2:
        _placeholder(path)
        return
    grid = np.full((len(ys), len(xs)), np.nan)
    x_index = {value: index for index, value in enumerate(xs)}
    y_index = {value: index for index, value in enumerate(ys)}
    for x, y, z, _row in usable:
        grid[y_index[y], x_index[x]] = z
    fig, ax = _figure((6.6, 4.6))
    if fig is None:
        _placeholder(path)
        return
    mesh = ax.pcolormesh(np.asarray(xs), np.asarray(ys), grid, shading="nearest")
    fig.colorbar(mesh, ax=ax).set_label(colour_label)
    if observed:
        ax.plot(
            [point[0] for point in observed],
            [point[1] for point in observed],
            "o",
            markersize=5,
            markerfacecolor="none",
            markeredgecolor="white",
            markeredgewidth=1.1,
        )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _finish(fig, path)


def _bars(
    path: Path,
    labels: Sequence[str],
    values: Sequence[float],
    *,
    xlabel: str,
    ylabel: str,
    rows: Sequence[Mapping[str, Any]] | None = None,
    horizontal: bool = False,
) -> None:
    _write_csv(
        path,
        rows
        if rows is not None
        else [{"label": label, "value": value} for label, value in zip(labels, values)],
    )
    if not labels:
        _placeholder(path)
        return
    fig, ax = _figure((max(6.0, 0.55 * len(labels)), 4.2))
    if fig is None:
        _placeholder(path)
        return
    if horizontal:
        ax.barh(range(len(labels)), list(values), color="tab:blue")
        ax.set_yticks(range(len(labels)), labels, fontsize=8)
        ax.set_xlabel(ylabel)
        ax.set_ylabel(xlabel)
    else:
        ax.bar(range(len(labels)), list(values), color="tab:blue")
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right", fontsize=8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25, axis="x" if horizontal else "y")
    _finish(fig, path)


def _curves(
    path: Path,
    curves: Sequence[Mapping[str, Any]],
    *,
    xlabel: str,
    ylabel: str,
    x_key: str = "x",
    y_key: str = "y",
    xlim: tuple[float, float] | None = None,
    axvline: float | None = None,
) -> None:
    """Several named curves on one axis; used for spectra and profiles."""

    rows: list[dict[str, Any]] = []
    usable: list[tuple[str, np.ndarray, np.ndarray]] = []
    for curve in curves:
        x = np.asarray(curve.get(x_key, []), dtype=float)
        y = np.asarray(curve.get(y_key, []), dtype=float)
        if x.size < 2 or x.size != y.size:
            continue
        name = str(curve.get("label", "curve"))
        usable.append((name, x, y))
        rows.extend(
            {"curve": name, x_key: float(a), y_key: float(b)} for a, b in zip(x, y)
        )
    _write_csv(path, rows)
    if not usable:
        _placeholder(path)
        return
    fig, ax = _figure((6.8, 4.4))
    if fig is None:
        _placeholder(path)
        return
    for name, x, y in usable:
        ax.plot(x, y, linewidth=1.5, label=name)
    if axvline is not None:
        ax.axvline(axvline, color="0.6", linewidth=0.8, linestyle="--")
    if xlim is not None:
        ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25)
    _finish(fig, path)


# ---------------------------------------------------------------------------
# the figure set
# ---------------------------------------------------------------------------


def write_all(plots_dir: Path, context: PlotContext) -> list[str]:
    """Draw the complete figure set; return the filenames present afterwards."""

    plots_dir = Path(plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    (plots_dir.parent / "plot_data").mkdir(parents=True, exist_ok=True)

    _optimization_progress(plots_dir, context)
    _parameter_sampling(plots_dir, context)
    _surrogate(plots_dir, context)
    _tradeoffs(plots_dir, context)
    _interpretation(plots_dir, context)
    _quality(plots_dir, context)
    _physics(plots_dir, context)
    _comparisons(plots_dir, context)
    _paper(plots_dir, context)

    plotting.ensure_plot_set(plots_dir, PLOT_SET, reason=PLACEHOLDER_REASON)
    for filename, _question in PLOT_SET:
        base = plots_dir / filename
        target = base.parent.parent / "plot_data" / f"{base.stem}.csv"
        if not target.is_file():
            _write_csv(base, [])
    return sorted(path.name for path in plots_dir.glob("*.png"))


def _optimization_progress(plots_dir: Path, context: PlotContext) -> None:
    records = context.completed
    _series_plot(
        plots_dir / "bo_objective_value_by_trial.png",
        records,
        x_key="trial_index",
        y_key=context.objective_metric,
        xlabel=AXIS["trial"],
        ylabel=AXIS["objective"],
        group_key="parameter_grading_profile",
    )
    _series_plot(
        plots_dir / "bo_best_objective_so_far_by_iteration.png",
        context.best_by_iteration,
        x_key="iteration",
        y_key="best_objective_so_far",
        xlabel=AXIS["iteration"],
        ylabel=AXIS["best_objective"],
        step=True,
    )
    for filename, key, label in (
        ("bo_chi2_at_1550_by_trial.png", "relative_chi2_at_target_wavelength_abs", AXIS["chi2_target"]),
        ("bo_peak_chi2_by_trial.png", "relative_peak_chi2_abs", AXIS["peak_chi2"]),
        ("bo_resonance_wavelength_by_trial.png", "peak_wavelength_nm", AXIS["peak_wavelength"]),
        ("bo_detuning_from_1550_by_trial.png", "signed_detuning_nm", AXIS["detuning"]),
    ):
        _series_plot(
            plots_dir / filename,
            records,
            x_key="trial_index",
            y_key=key,
            xlabel=AXIS["trial"],
            ylabel=label,
            axhline=0.0 if key == "signed_detuning_nm" else None,
            group_key="parameter_grading_profile",
        )


def _parameter_sampling(plots_dir: Path, context: PlotContext) -> None:
    records = context.completed
    metric = context.objective_metric
    for filename, x_key, y_key, xlabel, ylabel in (
        (
            "bo_asymmetry_vs_grading_thickness_objective.png",
            "parameter_asymmetry_s", "parameter_grading_thickness_nm",
            AXIS["asymmetry"], AXIS["grading"],
        ),
        (
            "bo_barrier_thickness_vs_grading_thickness_objective.png",
            "parameter_central_barrier_thickness_nm", "parameter_grading_thickness_nm",
            AXIS["barrier"], AXIS["grading"],
        ),
        (
            "bo_asymmetry_vs_barrier_thickness_objective.png",
            "parameter_asymmetry_s", "parameter_central_barrier_thickness_nm",
            AXIS["asymmetry"], AXIS["barrier"],
        ),
    ):
        _scatter_coloured(
            plots_dir / filename,
            records,
            x_key=x_key,
            y_key=y_key,
            colour_key=metric,
            xlabel=xlabel,
            ylabel=ylabel,
            colour_label=AXIS["objective"],
            extra_keys=("trial_index", "iteration", "trial_valid"),
        )

    groups: dict[str, list[float]] = {}
    for row in context.completed:
        value = _number(row.get(metric))
        if value is not None:
            groups.setdefault(str(row.get("parameter_grading_profile", "")), []).append(value)
    path = plots_dir / "bo_grading_profile_objective_distribution.png"
    rows = [
        {"parameter_grading_profile": name, "objective_value": value}
        for name, values in sorted(groups.items())
        for value in values
    ]
    _write_csv(path, rows)
    if not groups:
        _placeholder(path)
    else:
        fig, ax = _figure((6.4, 4.2))
        if fig is None:
            _placeholder(path)
        else:
            names = sorted(groups)
            ax.boxplot([groups[name] for name in names], tick_labels=names, showfliers=False)
            for index, name in enumerate(names, start=1):
                jitter = np.random.default_rng(index).normal(0, 0.045, len(groups[name]))
                ax.plot(index + jitter, groups[name], "o", markersize=4, alpha=0.85)
            ax.set_xlabel(AXIS["profile"])
            ax.set_ylabel(AXIS["objective"])
            ax.grid(alpha=0.25, axis="y")
            _finish(fig, path)

    _scatter_coloured(
        plots_dir / "bo_parameter_sampling_by_iteration.png",
        context.records,
        x_key="parameter_asymmetry_s",
        y_key="parameter_grading_thickness_nm",
        colour_key="iteration",
        xlabel=AXIS["asymmetry"],
        ylabel=AXIS["grading"],
        colour_label=AXIS["iteration"],
        extra_keys=("trial_index", "status"),
    )


def _surrogate(plots_dir: Path, context: PlotContext) -> None:
    observed_ag = [
        (x, y)
        for x, y in (
            (_number(row.get("parameter_asymmetry_s")), _number(row.get("parameter_grading_thickness_nm")))
            for row in context.completed
        )
        if x is not None and y is not None
    ]
    observed_bg = [
        (x, y)
        for x, y in (
            (
                _number(row.get("parameter_central_barrier_thickness_nm")),
                _number(row.get("parameter_grading_thickness_nm")),
            )
            for row in context.completed
        )
        if x is not None and y is not None
    ]
    metric = context.objective_metric
    slices = context.surrogate_slices
    _surface(
        plots_dir / "bo_surrogate_mean_asymmetry_vs_grading_thickness.png",
        slices.get("asymmetry_grading", ()),
        x_key="asymmetry_s",
        y_key="grading_thickness_nm",
        z_key=f"{metric}_predicted_mean",
        xlabel=AXIS["asymmetry"],
        ylabel=AXIS["grading"],
        colour_label="Predicted " + AXIS["objective"].lower(),
        observed=observed_ag,
    )
    _surface(
        plots_dir / "bo_surrogate_uncertainty_asymmetry_vs_grading_thickness.png",
        slices.get("asymmetry_grading", ()),
        x_key="asymmetry_s",
        y_key="grading_thickness_nm",
        z_key=f"{metric}_predicted_standard_error",
        xlabel=AXIS["asymmetry"],
        ylabel=AXIS["grading"],
        colour_label="Predicted standard error (a.u.)",
        observed=observed_ag,
    )
    _surface(
        plots_dir / "bo_acquisition_function_asymmetry_vs_grading_thickness.png",
        slices.get("asymmetry_grading", ()),
        x_key="asymmetry_s",
        y_key="grading_thickness_nm",
        z_key="expected_improvement",
        xlabel=AXIS["asymmetry"],
        ylabel=AXIS["grading"],
        colour_label="Expected improvement (a.u.)",
        observed=observed_ag,
    )
    _surface(
        plots_dir / "bo_surrogate_mean_barrier_vs_grading_thickness.png",
        slices.get("barrier_grading", ()),
        x_key="central_barrier_thickness_nm",
        y_key="grading_thickness_nm",
        z_key=f"{metric}_predicted_mean",
        xlabel=AXIS["barrier"],
        ylabel=AXIS["grading"],
        colour_label="Predicted " + AXIS["objective"].lower(),
        observed=observed_bg,
    )
    _surface(
        plots_dir / "bo_surrogate_uncertainty_barrier_vs_grading_thickness.png",
        slices.get("barrier_grading", ()),
        x_key="central_barrier_thickness_nm",
        y_key="grading_thickness_nm",
        z_key=f"{metric}_predicted_standard_error",
        xlabel=AXIS["barrier"],
        ylabel=AXIS["grading"],
        colour_label="Predicted standard error (a.u.)",
        observed=observed_bg,
    )


def _tradeoffs(plots_dir: Path, context: PlotContext) -> None:
    records = context.completed
    _scatter_coloured(
        plots_dir / "bo_peak_chi2_vs_detuning_pareto.png",
        records,
        x_key="absolute_detuning_nm",
        y_key="relative_peak_chi2_abs",
        colour_key="relative_chi2_at_target_wavelength_abs",
        xlabel="|Detuning from 1550 nm| (nm)",
        ylabel=AXIS["peak_chi2"],
        colour_label=AXIS["chi2_target"],
        extra_keys=("trial_index", "trial_valid"),
    )
    _scatter_coloured(
        plots_dir / "bo_chi2_1550_vs_peak_chi2.png",
        records,
        x_key="relative_peak_chi2_abs",
        y_key="relative_chi2_at_target_wavelength_abs",
        colour_key="absolute_detuning_nm",
        xlabel=AXIS["peak_chi2"],
        ylabel=AXIS["chi2_target"],
        colour_label="|Detuning from 1550 nm| (nm)",
        extra_keys=("trial_index", "trial_valid"),
    )
    _series_plot(
        plots_dir / "bo_chi2_1550_vs_boundary_probability.png",
        records,
        x_key="maximum_boundary_probability",
        y_key="relative_chi2_at_target_wavelength_abs",
        xlabel=AXIS["boundary"],
        ylabel=AXIS["chi2_target"],
        logy=False,
        group_key="parameter_grading_profile",
    )
    _series_plot(
        plots_dir / "bo_chi2_1550_vs_state_tracking_confidence.png",
        records,
        x_key="state_tracking_confidence",
        y_key="relative_chi2_at_target_wavelength_abs",
        xlabel=AXIS["confidence"],
        ylabel=AXIS["chi2_target"],
        group_key="parameter_grading_profile",
    )
    _scatter_coloured(
        plots_dir / "bo_nonlinear_strength_vs_robustness_pareto.png",
        records,
        x_key="robustness_score",
        y_key="relative_chi2_at_target_wavelength_abs",
        colour_key="relative_peak_chi2_abs",
        xlabel=AXIS["robustness"],
        ylabel=AXIS["chi2_target"],
        colour_label=AXIS["peak_chi2"],
        extra_keys=("trial_index", "trial_valid"),
    )


def _interpretation(plots_dir: Path, context: PlotContext) -> None:
    # Ax fits a surrogate per modelled metric. The figure shows only the
    # objective's sensitivities, because plotting several metrics' indices in one
    # bar chart invites reading them against each other, and they are not
    # comparable. The CSV keeps every metric.
    rows = [
        row
        for row in context.importance_rows
        if row.get("available") and str(row.get("metric")) == context.objective_metric
    ]
    _bars(
        plots_dir / "bo_parameter_importance.png",
        [str(row["parameter"]) for row in rows],
        [float(row["importance"]) for row in rows],
        xlabel="Parameter",
        ylabel=AXIS["importance"],
        rows=list(context.importance_rows),
        horizontal=True,
    )
    for filename, key, xlabel in (
        ("bo_partial_dependence_asymmetry.png", "asymmetry_s", AXIS["asymmetry"]),
        ("bo_partial_dependence_barrier_thickness.png", "central_barrier_thickness_nm", AXIS["barrier"]),
        ("bo_partial_dependence_grading_thickness.png", "grading_thickness_nm", AXIS["grading"]),
    ):
        rows = list(context.partial_dependence.get(key, ()))
        path = plots_dir / filename
        _write_csv(path, rows)
        usable = [
            (
                _number(row.get(key)),
                _number(row.get("predicted_mean")),
                _number(row.get("predicted_standard_error")),
            )
            for row in rows
        ]
        usable = [item for item in usable if item[0] is not None and item[1] is not None]
        if len(usable) < 2:
            _placeholder(path)
            continue
        fig, ax = _figure()
        if fig is None:
            _placeholder(path)
            continue
        xs = np.asarray([item[0] for item in usable])
        means = np.asarray([item[1] for item in usable])
        order = np.argsort(xs)
        ax.plot(xs[order], means[order], linewidth=1.6)
        sems = [item[2] for item in usable]
        if all(value is not None for value in sems):
            band = np.asarray([value for value in sems])
            ax.fill_between(
                xs[order], (means - band)[order], (means + band)[order], alpha=0.22
            )
        observed_x, observed_y = [], []
        for row in context.completed:
            x = _number(row.get(f"parameter_{key}"))
            y = _number(row.get(context.objective_metric))
            if x is not None and y is not None:
                observed_x.append(x)
                observed_y.append(y)
        if observed_x:
            ax.plot(observed_x, observed_y, "o", markersize=4, color="0.25")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(AXIS["objective"])
        ax.grid(alpha=0.25)
        _finish(fig, path)

    groups: dict[str, list[float]] = {}
    for row in context.completed:
        value = _number(row.get(context.objective_metric))
        if value is not None:
            groups.setdefault(str(row.get("parameter_grading_profile", "")), []).append(value)
    labels = sorted(groups)
    _bars(
        plots_dir / "bo_grading_profile_effect.png",
        labels,
        [float(np.mean(groups[name])) for name in labels],
        xlabel=AXIS["profile"],
        ylabel="Mean " + AXIS["objective"].lower(),
        rows=[
            {
                "parameter_grading_profile": name,
                "trials": len(groups[name]),
                "mean_objective_value": float(np.mean(groups[name])),
                "best_objective_value": float(np.max(groups[name])),
                "worst_objective_value": float(np.min(groups[name])),
            }
            for name in labels
        ],
    )


def _quality(plots_dir: Path, context: PlotContext) -> None:
    counts: dict[int, dict[str, int]] = {}
    for row in context.records:
        iteration = int(row.get("iteration", 0) or 0)
        bucket = counts.setdefault(iteration, {"valid": 0, "invalid": 0, "failed": 0})
        if str(row.get("status")) == "failed":
            bucket["failed"] += 1
        elif row.get("trial_valid"):
            bucket["valid"] += 1
        else:
            bucket["invalid"] += 1
    path = plots_dir / "bo_valid_and_invalid_trials_by_iteration.png"
    rows = [{"iteration": key, **value} for key, value in sorted(counts.items())]
    _write_csv(path, rows)
    if not rows:
        _placeholder(path)
    else:
        fig, ax = _figure()
        if fig is None:
            _placeholder(path)
        else:
            iterations = [row["iteration"] for row in rows]
            bottom = np.zeros(len(rows))
            for key, colour in (("valid", "tab:blue"), ("invalid", "tab:orange"), ("failed", "tab:red")):
                values = np.asarray([row[key] for row in rows], dtype=float)
                ax.bar(iterations, values, bottom=bottom, label=key, color=colour)
                bottom += values
            ax.set_xlabel(AXIS["iteration"])
            ax.set_ylabel(AXIS["count"])
            ax.legend(fontsize=8, frameon=False)
            ax.grid(alpha=0.25, axis="y")
            _finish(fig, path)

    reasons: dict[str, int] = {}
    for row in context.records:
        if str(row.get("status")) == "failed":
            reasons["mechanical_failure"] = reasons.get("mechanical_failure", 0) + 1
            continue
        violations = row.get("constraint_violations") or []
        if isinstance(violations, str):
            violations = [item for item in violations.split(";") if item]
        for violation in violations:
            reasons[str(violation)] = reasons.get(str(violation), 0) + 1
    labels = sorted(reasons, key=lambda name: -reasons[name])
    _bars(
        plots_dir / "bo_failure_reason_counts.png",
        labels,
        [reasons[name] for name in labels],
        xlabel="Rejection or failure reason",
        ylabel=AXIS["count"],
        rows=[{"reason": name, "trials": reasons[name]} for name in labels],
        horizontal=True,
    )
    _series_plot(
        plots_dir / "bo_boundary_probability_by_trial.png",
        context.completed,
        x_key="trial_index",
        y_key="maximum_boundary_probability",
        xlabel=AXIS["trial"],
        ylabel=AXIS["boundary"],
        logy=True,
        axhline=_number(
            ((context.cfg.get("bo") or {}).get("outcome_constraints") or {}).get(
                "maximum_boundary_probability"
            )
        ),
    )
    _series_plot(
        plots_dir / "bo_state_tracking_confidence_by_trial.png",
        context.completed,
        x_key="trial_index",
        y_key="state_tracking_confidence",
        xlabel=AXIS["trial"],
        ylabel=AXIS["confidence"],
        axhline=_number(
            ((context.cfg.get("bo") or {}).get("outcome_constraints") or {}).get(
                "minimum_state_tracking_confidence"
            )
        ),
    )

    path = plots_dir / "bo_validity_map_asymmetry_vs_grading_thickness.png"
    rows = [
        {
            "parameter_asymmetry_s": _number(row.get("parameter_asymmetry_s")),
            "parameter_grading_thickness_nm": _number(row.get("parameter_grading_thickness_nm")),
            "trial_index": row.get("trial_index"),
            "outcome": (
                "failed"
                if str(row.get("status")) == "failed"
                else ("valid" if row.get("trial_valid") else "invalid")
            ),
            "rejection_reason": row.get("rejection_reason") or row.get("failure_reason"),
        }
        for row in context.records
    ]
    rows = [
        row
        for row in rows
        if row["parameter_asymmetry_s"] is not None
        and row["parameter_grading_thickness_nm"] is not None
    ]
    _write_csv(path, rows)
    if not rows:
        _placeholder(path)
    else:
        fig, ax = _figure((6.4, 4.4))
        if fig is None:
            _placeholder(path)
        else:
            styles = {
                "valid": ("tab:blue", "o"),
                "invalid": ("tab:orange", "x"),
                "failed": ("tab:red", "s"),
            }
            for outcome, (colour, marker) in styles.items():
                subset = [row for row in rows if row["outcome"] == outcome]
                if not subset:
                    continue
                ax.plot(
                    [row["parameter_asymmetry_s"] for row in subset],
                    [row["parameter_grading_thickness_nm"] for row in subset],
                    marker,
                    color=colour,
                    markersize=6,
                    linestyle="none",
                    label=outcome,
                )
            ax.set_xlabel(AXIS["asymmetry"])
            ax.set_ylabel(AXIS["grading"])
            ax.legend(fontsize=8, frameon=False)
            ax.grid(alpha=0.25)
            _finish(fig, path)


def _physics(plots_dir: Path, context: PlotContext) -> None:
    target = _number((context.cfg.get("chi2") or {}).get("reference_wavelength_nm")) or 1550.0
    baseline = [curve for curve in context.spectra if curve.get("role") == "baseline"]
    best = [curve for curve in context.spectra if curve.get("role") in {"baseline", "best"}]
    tops = [curve for curve in context.spectra if curve.get("role") in {"baseline", "top"}]
    _curves(
        plots_dir / "baseline_and_top_bo_designs_chi2_spectra.png",
        tops,
        xlabel=AXIS["wavelength"],
        ylabel=AXIS["normalized_chi2"],
        axvline=target,
    )
    _curves(
        plots_dir / "top_bo_designs_chi2_spectra.png",
        [curve for curve in context.spectra if curve.get("role") == "top"],
        xlabel=AXIS["wavelength"],
        ylabel=AXIS["normalized_chi2"],
        axvline=target,
    )
    _curves(
        plots_dir / "baseline_and_best_bo_composition_profiles.png",
        context.profiles,
        xlabel=AXIS["position"],
        ylabel=AXIS["aluminium"],
    )
    _curves(
        plots_dir / "baseline_and_best_bo_conduction_band_edges.png",
        [curve for curve in context.band_edges if curve.get("band") == "conduction"],
        xlabel=AXIS["position"],
        ylabel=AXIS["energy"],
    )
    _curves(
        plots_dir / "baseline_and_best_bo_valence_band_edges.png",
        [curve for curve in context.band_edges if curve.get("band") == "heavy_hole"],
        xlabel=AXIS["position"],
        ylabel=AXIS["energy"],
    )
    _curves(
        plots_dir / "baseline_and_best_bo_electron_wavefunctions.png",
        [curve for curve in context.envelopes if curve.get("band") == "electron"],
        xlabel=AXIS["position"],
        ylabel=AXIS["amplitude"],
    )
    _curves(
        plots_dir / "baseline_and_best_bo_hole_wavefunctions.png",
        [curve for curve in context.envelopes if curve.get("band") == "heavy_hole"],
        xlabel=AXIS["position"],
        ylabel=AXIS["amplitude"],
    )

    localization_keys = (
        ("narrow_well_probability", "narrow well"),
        ("wide_well_probability", "wide well"),
        ("central_barrier_probability", "central barrier"),
        ("outer_barrier_probability", "outer barrier"),
        ("total_boundary_probability", "boundary"),
    )
    designs = _highlight_designs(context)
    path = plots_dir / "baseline_and_best_bo_state_localization.png"
    rows = [
        {
            "design": label,
            "region": name,
            "probability": _number(record.get(key)),
        }
        for label, record in designs
        for key, name in localization_keys
    ]
    _write_csv(path, rows)
    usable = [row for row in rows if row["probability"] is not None]
    if not usable:
        _placeholder(path)
    else:
        fig, ax = _figure((6.8, 4.2))
        if fig is None:
            _placeholder(path)
        else:
            names = [name for _key, name in localization_keys]
            labels = [label for label, _record in designs]
            width = 0.8 / max(1, len(labels))
            for index, label in enumerate(labels):
                values = [
                    next(
                        (
                            row["probability"] or 0.0
                            for row in usable
                            if row["design"] == label and row["region"] == name
                        ),
                        0.0,
                    )
                    for name in names
                ]
                ax.bar(
                    np.arange(len(names)) + index * width - 0.4 + width / 2,
                    values,
                    width=width,
                    label=label,
                )
            ax.set_xticks(range(len(names)), names, fontsize=8)
            ax.set_xlabel("Region")
            ax.set_ylabel(AXIS["probability"])
            ax.legend(fontsize=8, frameon=False)
            ax.grid(alpha=0.25, axis="y")
            _finish(fig, path)

    transition_keys = (
        ("transition_e1_hh1_eV", "e1–hh1"),
        ("transition_e2_hh2_eV", "e2–hh2"),
    )
    path = plots_dir / "baseline_and_best_bo_transition_energies.png"
    rows = [
        {"design": label, "transition": name, "energy_eV": _number(record.get(key))}
        for label, record in designs
        for key, name in transition_keys
    ]
    _write_csv(path, rows)
    usable = [row for row in rows if row["energy_eV"] is not None]
    if not usable:
        _placeholder(path)
    else:
        fig, ax = _figure((6.4, 4.2))
        if fig is None:
            _placeholder(path)
        else:
            names = [name for _key, name in transition_keys]
            labels = [label for label, _record in designs]
            width = 0.8 / max(1, len(labels))
            for index, label in enumerate(labels):
                values = [
                    next(
                        (
                            row["energy_eV"] or 0.0
                            for row in usable
                            if row["design"] == label and row["transition"] == name
                        ),
                        0.0,
                    )
                    for name in names
                ]
                ax.bar(
                    np.arange(len(names)) + index * width - 0.4 + width / 2,
                    values,
                    width=width,
                    label=label,
                )
            ax.set_xticks(range(len(names)), names, fontsize=9)
            ax.set_xlabel("Transition")
            ax.set_ylabel(AXIS["transition"])
            ax.legend(fontsize=8, frameon=False)
            ax.grid(alpha=0.25, axis="y")
            _finish(fig, path)


def _highlight_designs(context: PlotContext) -> list[tuple[str, Mapping[str, Any]]]:
    """The reference and the best valid design, in a stable plotting order."""

    designs: list[tuple[str, Mapping[str, Any]]] = []
    reference = next(
        (row for row in context.completed if row.get("design_role") == "reference"), None
    )
    if reference is not None:
        designs.append(("reference (abrupt)", reference))
    valid = [
        row for row in context.valid if _number(row.get(context.objective_metric)) is not None
    ]
    if valid:
        best = max(valid, key=lambda row: float(row[context.objective_metric]))
        designs.append((f"best BO (trial {best.get('trial_index')})", best))
    return designs


def _comparisons(plots_dir: Path, context: PlotContext) -> None:
    traces = (context.efficiency or {}).get("traces") or {}
    for filename, other in (
        ("bo_vs_random_search_best_objective.png", "random_search"),
        ("bo_vs_grid_search_best_objective.png", "grid_search"),
    ):
        path = plots_dir / filename
        rows: list[dict[str, Any]] = []
        for name in ("bayesian_optimization", other):
            for row in traces.get(name, ()):
                rows.append({"search_method": name, **dict(row)})
        _write_csv(path, rows)
        if not rows:
            _placeholder(path)
            continue
        fig, ax = _figure()
        if fig is None:
            _placeholder(path)
            continue
        for name in ("bayesian_optimization", other):
            trace = [row for row in traces.get(name, ()) if row.get("best_so_far") is not None]
            if not trace:
                continue
            ax.step(
                [row["evaluations"] for row in trace],
                [row["best_so_far"] for row in trace],
                where="post",
                linewidth=1.6,
                label=name.replace("_", " "),
            )
        ax.set_xlabel(AXIS["evaluations"])
        ax.set_ylabel(AXIS["best_objective"])
        ax.legend(fontsize=8, frameon=False)
        ax.grid(alpha=0.25)
        _finish(fig, path)

    summary = (context.efficiency or {}).get("summary") or []
    labels = [str(row["search_method"]).replace("_", " ") for row in summary]
    values = [
        float(row["evaluations_to_threshold"])
        if row.get("evaluations_to_threshold") is not None
        else 0.0
        for row in summary
    ]
    _bars(
        plots_dir / "bo_random_grid_evaluations_to_best_known_result.png",
        labels,
        values,
        xlabel="Search method",
        ylabel=AXIS["evaluations"],
        rows=list(summary),
    )

    target = _number((context.cfg.get("chi2") or {}).get("reference_wavelength_nm")) or 1550.0
    _curves(
        plots_dir / "demo11_demo12_demo13_best_chi2_spectra.png",
        [curve for curve in context.spectra if curve.get("role") in {"baseline", "demo12", "best"}],
        xlabel=AXIS["wavelength"],
        ylabel=AXIS["normalized_chi2"],
        axvline=target,
    )


def _paper(plots_dir: Path, context: PlotContext) -> None:
    paper_cfg = context.cfg.get("paper_comparison") or {}
    full = [float(value) for value in paper_cfg.get("full_range_nm", (1200.0, 1800.0))]
    telecom = [float(value) for value in paper_cfg.get("telecom_range_nm", (1450.0, 1650.0))]
    curves = list(context.paper_curves)
    ylabel = (
        AXIS["normalized_chi2"]
        if str(paper_cfg.get("units", "normalized")) == "normalized"
        else "Simulated |χ²| (pm/V)"
    )
    _curves(
        plots_dir / "paper_figure2d_simulation_comparison_full_range.png",
        curves,
        xlabel=AXIS["wavelength"],
        ylabel=ylabel,
        xlim=(min(full), max(full)),
    )
    _curves(
        plots_dir / "paper_figure2d_simulation_comparison_telecom_range.png",
        curves,
        xlabel=AXIS["wavelength"],
        ylabel=ylabel,
        xlim=(min(telecom), max(telecom)),
    )
    # Measured second-harmonic intensity is a different physical quantity from a
    # simulated susceptibility, so it gets its own figure rather than a second
    # axis on someone else's.
    _curves(
        plots_dir / "paper_measured_sh_intensity_comparison.png",
        list(context.measured_curves),
        xlabel=AXIS["wavelength"],
        ylabel=AXIS["sh_intensity"],
    )
