"""Demo 16G figures. Four wavelength plots, then five summary comparisons.

Titles are short and nothing is annotated inside the axes beyond a 1550 nm line,
because the point of these figures is to be readable next to the paper's Fig. 2d
rather than to restate the README. Group identity is carried by colour and
weight: the paper benchmark and the two supplied files are heavy and saturated,
the twenty sweep curves are light and subordinate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

TARGET_NM = 1550.0

GROUP_STYLE = {
    "supplied_nnp": {"color": "#1f4e79", "lw": 2.4, "alpha": 1.0, "zorder": 5},
    "structure_sweep": {"color": "#9aa5b1", "lw": 1.0, "alpha": 0.45, "zorder": 2},
    "paper_benchmark": {"color": "#c0392b", "lw": 2.8, "alpha": 1.0, "zorder": 6},
}
#: The two supplied files need to be told apart from each other.
NNP_COLOURS = ("#1f4e79", "#0f7b8a")
PAPER_REFERENCE_COLOUR = "#7b3f98"


def _available() -> bool:
    try:
        import matplotlib  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def _new_axes(figsize=(10.0, 6.0)):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(figsize=figsize)
    return plt, figure, axes


def _finish(plt, figure, axes, path: Path, title: str, dpi: int = 160) -> Path:
    axes.set_xlabel("Fundamental Wavelength (nm)")
    axes.set_ylabel("$|\\chi^{(2)}|$ (pm/V)")
    axes.set_title(title)
    axes.grid(alpha=0.2)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=dpi)
    plt.close(figure)
    return Path(path)


def _target_line(axes) -> None:
    axes.axvline(TARGET_NM, color="#222222", ls="--", lw=1.4)


def _spectrum(record: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray] | None:
    """Prefer the in-memory spectrum; fall back to the CSV a previous run wrote."""

    inline = record.get("_spectrum")
    if inline is not None:
        return np.asarray(inline[0], dtype=float), np.asarray(inline[1], dtype=float)
    path = record.get("spectrum_csv")
    if path and Path(path).is_file():
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        return np.asarray(data[:, 0], dtype=float), np.asarray(data[:, 1], dtype=float)
    return None


def _solved(records: Sequence[Mapping[str, Any]], group: str) -> list[Mapping[str, Any]]:
    return [r for r in records if r.get("passed") and r.get("group") == group]


# ---------------------------------------------------------------------------
# Plot 1 -- supplied .nnp files
# ---------------------------------------------------------------------------


def supplied_nnp_plot(path: Path, records: Sequence[Mapping[str, Any]]) -> Path | None:
    if not _available():
        return None
    rows = _solved(records, "supplied_nnp")
    if not rows:
        return None
    plt, figure, axes = _new_axes()
    for index, record in enumerate(rows):
        spectrum = _spectrum(record)
        if spectrum is None:
            continue
        axes.plot(spectrum[0], spectrum[1],
                  color=NNP_COLOURS[index % len(NNP_COLOURS)],
                  lw=2.2, label=record.get("label", record["case_id"]))
    _target_line(axes)
    axes.legend(fontsize=9)
    return _finish(plt, figure, axes, path, "Supplied NNP Wavelength Response")


# ---------------------------------------------------------------------------
# Plot 2 -- the sweep
# ---------------------------------------------------------------------------


def sweep_plot(path: Path, records: Sequence[Mapping[str, Any]]) -> Path | None:
    if not _available():
        return None
    rows = _solved(records, "structure_sweep")
    if not rows:
        return None
    plt, figure, axes = _new_axes()
    import matplotlib.cm as cm

    colours = cm.viridis(np.linspace(0.05, 0.95, len(rows)))
    for colour, record in zip(colours, rows):
        spectrum = _spectrum(record)
        if spectrum is None:
            continue
        axes.plot(spectrum[0], spectrum[1], color=colour, lw=1.3, alpha=0.85)
    _target_line(axes)
    return _finish(plt, figure, axes, path, "Structure Sweep Wavelength Response")


# ---------------------------------------------------------------------------
# Plot 3 -- paper benchmark
# ---------------------------------------------------------------------------


def paper_benchmark_plot(
    path: Path, records: Sequence[Mapping[str, Any]],
    digitized: Mapping[str, Any] | None = None,
) -> Path | None:
    """Our calculated paper-like structure, and any digitized curve, kept apart.

    A digitized curve is labelled as digitized. It is somebody's reading of a
    printed figure, not data the authors published as numbers, and presenting it
    as raw paper data would be a misrepresentation regardless of how carefully it
    was traced.
    """

    if not _available():
        return None
    rows = _solved(records, "paper_benchmark")
    if not rows and not digitized:
        return None
    plt, figure, axes = _new_axes()
    for record in rows:
        spectrum = _spectrum(record)
        if spectrum is None:
            continue
        axes.plot(spectrum[0], spectrum[1], color=GROUP_STYLE["paper_benchmark"]["color"],
                  lw=2.6, label="This work: paper-like structure (calculated)")
    if digitized and digitized.get("wavelength_nm"):
        axes.plot(digitized["wavelength_nm"], digitized["value"],
                  color=PAPER_REFERENCE_COLOUR, lw=1.8, ls="--",
                  label="Paper Fig. 2d (digitized reference, not raw data)")
    _target_line(axes)
    axes.legend(fontsize=9)
    return _finish(plt, figure, axes, path, "Paper Benchmark Wavelength Response")


# ---------------------------------------------------------------------------
# Plot 4 -- everything
# ---------------------------------------------------------------------------


def combined_plot(
    path: Path, records: Sequence[Mapping[str, Any]],
    digitized: Mapping[str, Any] | None = None,
) -> Path | None:
    if not _available():
        return None
    plt, figure, axes = _new_axes(figsize=(11.0, 6.6))

    sweep = _solved(records, "structure_sweep")
    for index, record in enumerate(sweep):
        spectrum = _spectrum(record)
        if spectrum is None:
            continue
        axes.plot(spectrum[0], spectrum[1],
                  label="20 swept structures" if index == 0 else None,
                  **GROUP_STYLE["structure_sweep"])

    for index, record in enumerate(_solved(records, "supplied_nnp")):
        spectrum = _spectrum(record)
        if spectrum is None:
            continue
        axes.plot(spectrum[0], spectrum[1],
                  color=NNP_COLOURS[index % len(NNP_COLOURS)], lw=2.2,
                  zorder=5, label=record.get("label", record["case_id"]))

    for record in _solved(records, "paper_benchmark"):
        spectrum = _spectrum(record)
        if spectrum is None:
            continue
        axes.plot(spectrum[0], spectrum[1], lw=2.8, zorder=6,
                  color=GROUP_STYLE["paper_benchmark"]["color"],
                  label="Paper benchmark (calculated)")

    if digitized and digitized.get("wavelength_nm"):
        axes.plot(digitized["wavelength_nm"], digitized["value"],
                  color=PAPER_REFERENCE_COLOUR, lw=1.6, ls="--", zorder=4,
                  label="Paper Fig. 2d (digitized)")

    _target_line(axes)
    axes.legend(fontsize=8, ncol=2, framealpha=0.92)
    return _finish(plt, figure, axes, path, "1550 nm Wavelength Response Curves")


# ---------------------------------------------------------------------------
# Summary comparisons
# ---------------------------------------------------------------------------


def _bar_comparison(
    path: Path, records: Sequence[Mapping[str, Any]], key: str, ylabel: str,
    title: str, *, reference: float | None = None, reference_label: str = "",
) -> Path | None:
    if not _available():
        return None
    rows = [r for r in records if r.get("passed") and r.get(key) is not None]
    if not rows:
        return None
    plt, figure, axes = _new_axes(figsize=(11.0, 5.4))
    labels = [r["case_id"] for r in rows]
    values = [float(r[key]) for r in rows]
    colours = [GROUP_STYLE.get(r["group"], {}).get("color", "#888888") for r in rows]
    axes.bar(range(len(rows)), values, color=colours)
    if reference is not None:
        axes.axhline(reference, color="#7b3f98", ls="--", lw=1.4,
                     label=reference_label or f"{reference:g}")
        axes.legend(fontsize=8)
    axes.set_xticks(range(len(labels)), labels, rotation=60, ha="right", fontsize=7)
    axes.set_ylabel(ylabel)
    axes.set_title(title)
    axes.grid(axis="y", alpha=0.25)
    axes.set_xlabel("")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return Path(path)


def summary_plots(
    plots_dir: Path, records: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> dict[str, str]:
    """The five comparison figures, keyed by filename."""

    target = float(
        cfg["paper_benchmark"]["targets_pm_per_V"]["ideal_abrupt_at_1550"]
    )
    written: dict[str, str] = {}
    specifications = (
        ("chi2_at_1550_comparison.png", "chi2_1550_pm_per_V",
         "$|\\chi^{(2)}|$ at 1550 nm (pm/V)", "Chi2 at 1550 nm",
         target, f"paper stated {target:g} pm/V"),
        ("peak_wavelength_comparison.png", "peak_wavelength_nm",
         "peak wavelength (nm)", "Spectral Peak Wavelength", 1550.0, "1550 nm"),
        ("peak_chi2_comparison.png", "peak_chi2_pm_per_V",
         "peak $|\\chi^{(2)}|$ (pm/V)", "Peak Chi2", None, ""),
        ("detuning_from_1550_comparison.png", "detuning_nm",
         "detuning (nm)", "Detuning from 1550 nm", 0.0, "on target"),
    )
    for filename, key, ylabel, title, reference, reference_label in specifications:
        result = _bar_comparison(
            Path(plots_dir) / filename, records, key, ylabel, title,
            reference=reference, reference_label=reference_label,
        )
        if result:
            written[filename] = str(result)

    energies = energy_transitions_plot(
        Path(plots_dir) / "energy_transitions_comparison.png", records
    )
    if energies:
        written["energy_transitions_comparison.png"] = str(energies)
    return written


def energy_transitions_plot(
    path: Path, records: Sequence[Mapping[str, Any]]
) -> Path | None:
    """E1-HH1 and E2-HH2 per case: the two transitions that set the resonances."""

    if not _available():
        return None
    rows = [
        r for r in records
        if r.get("passed") and (r.get("matrix_elements") or {}).get("E1_minus_HH1_eV")
    ]
    if not rows:
        return None
    plt, figure, axes = _new_axes(figsize=(11.0, 5.4))
    x = np.arange(len(rows), dtype=float)
    first = [float(r["matrix_elements"]["E1_minus_HH1_eV"]) for r in rows]
    second = [float(r["matrix_elements"]["E2_minus_HH2_eV"]) for r in rows]
    axes.bar(x - 0.2, first, 0.4, color="#2e7d32", label="E1 - HH1")
    axes.bar(x + 0.2, second, 0.4, color="#c0392b", label="E2 - HH2")
    axes.set_xticks(x, [r["case_id"] for r in rows], rotation=60, ha="right",
                    fontsize=7)
    axes.set_ylabel("transition energy (eV)")
    axes.set_title("Interband Transition Energies")
    axes.set_xlabel("")
    axes.legend(fontsize=8)
    axes.grid(axis="y", alpha=0.25)
    lowest = min(min(first), min(second))
    highest = max(max(first), max(second))
    axes.set_ylim(lowest - 0.05, highest + 0.05)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return Path(path)


def write_all(
    plots_dir: Path, records: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any],
    digitized: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Every figure. Missing matplotlib degrades to an empty dict, never a crash."""

    plots_dir = Path(plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for name, function in (
        ("supplied_nnp_wavelength_response.png",
         lambda p: supplied_nnp_plot(p, records)),
        ("structure_sweep_wavelength_response.png",
         lambda p: sweep_plot(p, records)),
        ("paper_benchmark_wavelength_response.png",
         lambda p: paper_benchmark_plot(p, records, digitized)),
        ("chi2_wavelength_all_groups.png",
         lambda p: combined_plot(p, records, digitized)),
    ):
        result = function(plots_dir / name)
        if result:
            written[name] = str(result)
    written.update(summary_plots(plots_dir, records, cfg))
    return written
