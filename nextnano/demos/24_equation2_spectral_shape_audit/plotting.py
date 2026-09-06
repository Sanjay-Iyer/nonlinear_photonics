"""Plot-only helpers for Demo 24; no physics is computed here."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from signed_spectrum import normalize


def _finish(fig, path: Path, dpi: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def overlay(path: Path, wavelength: np.ndarray, paper: np.ndarray, models: Mapping[str, np.ndarray],
            features: Sequence[Mapping[str, object]], title: str, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    ax.plot(wavelength, normalize(paper), "k--", lw=2.2, label="Paper Fig. 2d eye digitization")
    for label, values in models.items():
        ax.plot(wavelength, normalize(values), lw=1.6, label=label)
    for row in features:
        x = float(row["Paper wavelength nm"])
        ax.axvline(x, color="0.75", lw=0.7)
        ax.text(x, 1.02, str(row["Feature"]), ha="center", va="bottom", fontsize=8)
    ax.set(xlabel="Fundamental wavelength (nm)", ylabel="Normalized amplitude", title=title, xlim=(400, 1850), ylim=(-0.03, 1.08))
    ax.legend(fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def peak_errors(path: Path, feature_rows: Sequence[Mapping[str, object]], dpi: int) -> None:
    rows = [r for r in feature_rows if r["Feature type"] == "peak"]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    labels = [str(r["Feature"]) for r in rows]
    errors = [float(r["Wavelength error nm"]) for r in rows]
    ax.bar(labels, errors, color=["#d95f02" if abs(x) > 25 else "#1b9e77" for x in errors])
    ax.axhline(0, color="k", lw=0.8)
    ax.set(ylabel="Demo 23D - paper wavelength (nm)", title="Peak correspondence error")
    ax.grid(axis="y", alpha=0.2)
    _finish(fig, path, dpi)


def complex_components(path: Path, wavelength: np.ndarray, chi: np.ndarray, title: str, dpi: int,
                       xlim: tuple[float, float] | None = None) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    ax.plot(wavelength, np.real(chi), label="Re chi", lw=1.4)
    ax.plot(wavelength, np.imag(chi), label="Im chi", lw=1.4)
    ax.plot(wavelength, np.abs(chi), label="|chi|", lw=2.0, color="k")
    ax.axhline(0, color="0.4", lw=0.8)
    ax.set(xlabel="Fundamental wavelength (nm)", ylabel="chi2 (pm/V)", title=title)
    if xlim:
        ax.set_xlim(*xlim)
    ax.legend()
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def subtotals(path: Path, wavelength: np.ndarray, electron: np.ndarray, hh: np.ndarray, title: str,
              dpi: int, xlim: tuple[float, float] | None = None) -> None:
    total = electron + hh
    fig, axes = plt.subplots(2, 1, figsize=(9.2, 6.8), sharex=True)
    for ax, component, name in ((axes[0], np.real, "Real"), (axes[1], np.imag, "Imaginary")):
        ax.plot(wavelength, component(electron), label="electron subtotal")
        ax.plot(wavelength, component(hh), label="signed HH subtotal")
        ax.plot(wavelength, component(total), label="total", color="k", lw=1.8)
        ax.axhline(0, color="0.4", lw=0.7)
        ax.set_ylabel(f"{name} chi2 (pm/V)")
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=8)
    axes[-1].set_xlabel("Fundamental wavelength (nm)")
    axes[0].set_title(title)
    if xlim:
        axes[-1].set_xlim(*xlim)
    _finish(fig, path, dpi)


def pathways(path: Path, wavelength: np.ndarray, terms: np.ndarray, labels: Sequence[str],
             component: str, title: str, dpi: int, xlim: tuple[float, float] | None = None,
             top: int | None = None) -> None:
    transform = np.real if component == "real" else np.imag if component == "imag" else np.abs
    indices = list(range(len(labels)))
    if top:
        mask = np.ones(len(wavelength), dtype=bool) if xlim is None else ((wavelength >= xlim[0]) & (wavelength <= xlim[1]))
        scores = np.max(np.abs(terms[:, mask]), axis=1)
        indices = list(np.argsort(scores)[-top:][::-1])
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    for index in indices:
        ax.plot(wavelength, transform(terms[index]), lw=1.0, label=labels[index])
    ax.axhline(0, color="k", lw=0.7)
    ax.set(xlabel="Fundamental wavelength (nm)", ylabel=f"{component} pathway chi2 (pm/V)", title=title)
    if xlim:
        ax.set_xlim(*xlim)
    ax.legend(fontsize=6, ncol=2)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def resonance_map(path: Path, rows: Sequence[Mapping[str, object]], features: Sequence[Mapping[str, object]], dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.3))
    labels = sorted({str(r["transition"]) for r in rows})
    for label in labels:
        selected = [r for r in rows if r["transition"] == label]
        ax.plot([r["k_per_nm"] for r in selected], [r["two_photon_fundamental_wavelength_nm"] for r in selected], label=f"{label} two-photon")
        ax.plot([r["k_per_nm"] for r in selected], [r["one_photon_fundamental_wavelength_nm"] for r in selected], ls="--", alpha=0.65, label=f"{label} one-photon")
    for row in features:
        ax.axhline(float(row["Paper wavelength nm"]), color="0.8", lw=0.6)
    ax.set(xlabel="k (1/nm)", ylabel="Fundamental resonance wavelength (nm)", title="Equation-2 denominator resonance map", ylim=(350, 1900))
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def sensitivity(path: Path, wavelength: np.ndarray, spectra: Mapping[str, np.ndarray], paper: np.ndarray,
                title: str, dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.1))
    ax.plot(wavelength, normalize(paper), "k--", lw=2, label="paper")
    for label, chi in spectra.items():
        ax.plot(wavelength, normalize(chi), lw=1.15, label=label)
    ax.set(xlabel="Fundamental wavelength (nm)", ylabel="Normalized |chi2|", title=title, xlim=(400, 1850), ylim=(-0.02, 1.05))
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def state_character(path: Path, rows: Sequence[Mapping[str, object]], dpi: int) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    labels = [str(r["state"]) for r in rows]
    bottom = np.zeros(len(rows))
    for key, title, color in (("CB fraction", "CB", "#377eb8"), ("HH fraction", "HH", "#e41a1c"),
                              ("LH fraction", "LH", "#4daf4a"), ("SO fraction", "SO", "#984ea3")):
        values = np.asarray([float(r[key]) for r in rows])
        ax.bar(labels, values, bottom=bottom, label=title, color=color)
        bottom += values
    ax.set(ylabel="k=0 spinor fraction", title="Available state character (finite-k character was not exported)", ylim=(0, 1.02))
    ax.legend(ncol=4, fontsize=8)
    _finish(fig, path, dpi)


DIAGNOSTIC_NOTE = "DIAGNOSTIC PERTURBATION - NOT A PHYSICAL/FITTED MODEL"
_STATES = ("e1", "e2", "hh1", "hh2")
_FEATURES = ("P1", "Z1", "P2", "P3", "Z2", "P4")


def _banner(fig) -> None:
    fig.text(0.5, 0.005, DIAGNOSTIC_NOTE, ha="center", va="bottom", fontsize=7, color="#b2182b")


def feature_energy_sensitivity(path: Path, rows: Sequence[Mapping[str, object]], kind: str,
                               title: str, dpi: int) -> None:
    """Figures 21/22 - feature wavelength versus one-at-a-time subband shifts."""
    wanted = [f for f in _FEATURES if any(str(r["Feature"]) == f and str(r["feature_type"]) == kind for r in rows)]
    fig, axes = plt.subplots(1, max(len(wanted), 1), figsize=(3.4 * max(len(wanted), 1), 4.2), sharey=False)
    axes = np.atleast_1d(axes)
    for ax, feature in zip(axes, wanted):
        for state in _STATES:
            subset = sorted((r for r in rows if r["Feature"] == feature and r["state"] == state),
                            key=lambda r: float(r["shift_meV"]))
            ax.plot([float(r["shift_meV"]) for r in subset],
                    [float(r["model_wavelength_nm"]) for r in subset], marker="o", ms=3.5, lw=1.2, label=state)
        paper = float(next(r for r in rows if r["Feature"] == feature)["paper_wavelength_nm"])
        ax.axhline(paper, color="k", ls="--", lw=1.2)
        ax.set(title=f"{feature} (paper {paper:.0f} nm)", xlabel="one-state shift (meV)")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("model feature wavelength (nm)")
    axes[0].legend(fontsize=7)
    fig.suptitle(title)
    _banner(fig)
    _finish(fig, path, dpi)


def node_amplitude_sensitivity(path: Path, rows: Sequence[Mapping[str, object]], feature: str,
                               title: str, dpi: int) -> None:
    """Figures 23/24 - node depth versus single-pathway numerator scaling."""
    subset = [r for r in rows if r["Feature"] == feature]
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    for pathway in sorted({str(r["pathway"]) for r in subset}):
        chosen = sorted((r for r in subset if r["pathway"] == pathway),
                        key=lambda r: float(r["amplitude_scale"]))
        ax.plot([float(r["amplitude_scale"]) for r in chosen],
                [float(r["normalized_amplitude_at_paper_nm"]) for r in chosen],
                marker="o", ms=3.5, lw=1.2, label=pathway)
    ax.set(xlabel="single-pathway numerator scale", ylabel="normalized |chi2| at the paper wavelength",
           title=title)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7, ncol=2)
    _banner(fig)
    _finish(fig, path, dpi)


def sensitivity_heatmap(path: Path, derivatives: Sequence[Mapping[str, object]], dpi: int) -> None:
    """Figure 25 - feature-to-parameter sensitivity heatmap."""
    features = [f for f in _FEATURES if any(str(r["Feature"]) == f for r in derivatives)]
    matrix = np.zeros((len(features), len(_STATES)))
    for i, feature in enumerate(features):
        for j, state in enumerate(_STATES):
            row = next((r for r in derivatives if r["Feature"] == feature and r["state"] == state), None)
            value = float(row["dLambda_dE_nm_per_meV"]) if row else np.nan
            matrix[i, j] = value if np.isfinite(value) else np.nan
    limit = float(np.nanmax(np.abs(matrix))) if np.isfinite(matrix).any() else 1.0
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    image = ax.imshow(matrix, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set(xticks=range(len(_STATES)), yticks=range(len(features)), xlabel="perturbed subband",
           title="Feature wavelength sensitivity dLambda/dE (nm/meV)")
    ax.set_xticklabels(_STATES)
    ax.set_yticklabels(features)
    for i in range(len(features)):
        for j in range(len(_STATES)):
            if np.isfinite(matrix[i, j]):
                ax.text(j, i, f"{matrix[i, j]:+.2f}", ha="center", va="center", fontsize=8,
                        color="k" if abs(matrix[i, j]) < 0.6 * limit else "w")
    fig.colorbar(image, ax=ax, label="nm per meV")
    _banner(fig)
    _finish(fig, path, dpi)


def causal_traceback_diagram(path: Path, diagnosis: Sequence[Mapping[str, object]], dpi: int) -> None:
    """Figure 26 - feature -> pathway -> k-region -> denominator -> controlling state."""
    rows = [r for r in diagnosis]
    fig, ax = plt.subplots(figsize=(12.6, 0.52 * len(rows) + 1.25))
    columns = ["feature", "dominant pathway", "dominant k (1/nm)", "controlling band edge",
               "most sensitive state", "verdict"]
    x = np.linspace(0.02, 0.78, len(columns))
    for xi, name in zip(x, columns):
        ax.text(xi, 1.0, name, ha="left", va="center", fontsize=9, fontweight="bold")
    step = 0.86 / max(len(rows), 1)
    for row_index, row in enumerate(rows):
        y = 1.0 - step * (row_index + 1.0)
        reachable = str(row["reachable_within_model_resonance_band"]) == "yes"
        colour = "#1b9e77" if reachable else "#d95f02"
        edge = str(row["Controlling_transition"])
        cells = [str(row["Feature"]), str(row["Dominant_pathway"]), f"{float(row['Dominant_k']):.3f}",
                 edge if len(edge) < 34 else "not at a band edge", str(row["Most_sensitive_energy"]),
                 "in resonance band" if reachable else "OUT of resonance band"]
        for xi, text in zip(x, cells):
            ax.text(xi, y, text, ha="left", va="center", fontsize=8.5, color=colour)
        for xi, xj in zip(x[:-1], x[1:]):
            ax.annotate("", xy=(xj - 0.006, y), xytext=(xi + 0.135, y),
                        arrowprops=dict(arrowstyle="->", color="0.75", lw=0.8))
    ax.set_xlim(0, 1.05)
    ax.set_ylim(1.0 - step * (len(rows) + 0.6), 1.06)
    ax.set_axis_off()
    ax.set_title("Per-feature causal traceback: feature -> pathway -> k-region -> denominator -> state")
    _banner(fig)
    _finish(fig, path, dpi)


def ranking(path: Path, rows: Sequence[Mapping[str, object]], dpi: int) -> None:
    ordered = sorted(rows, key=lambda r: int(r["Rank"]), reverse=True)
    fig, ax = plt.subplots(figsize=(9.5, 6.0))
    labels = [str(r["Hypothesis"]) for r in ordered]
    confidence = [float(r["Confidence score"]) for r in ordered]
    ax.barh(labels, confidence, color="#4c78a8")
    ax.set(xlabel="Evidence-weighted confidence (0-1)", title="Demo 24 root-cause ranking", xlim=(0, 1))
    ax.grid(axis="x", alpha=0.2)
    _finish(fig, path, dpi)
