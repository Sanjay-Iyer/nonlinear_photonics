"""Figures for Demo 25. Plot-only: no physics is computed here."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


BANDS = ("CB fraction", "HH fraction", "LH fraction", "SO fraction")
BAND_COLOURS = ("#377eb8", "#e41a1c", "#4daf4a", "#984ea3")
FEATURE_NM = {"P1": 540.0, "Z1": 605.0, "P2": 760.0, "P3": 1080.0, "Z2": 1330.0, "P4": 1520.0}


def _finish(fig, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def _normalize(values: np.ndarray) -> np.ndarray:
    array = np.abs(np.asarray(values))
    scale = float(np.max(array)) if array.size else 0.0
    return array / scale if scale > 0 else array


def _mark_features(ax, top: float = 1.02) -> None:
    for name, nm in FEATURE_NM.items():
        ax.axvline(nm, color="0.78", lw=0.7)
        ax.text(nm, top, name, ha="center", va="bottom", fontsize=8)


def pilot_coverage(path: Path, rows: Sequence[Mapping[str, Any]], dpi: int) -> None:
    """Figure 1: which outputs each pilot variant produced, per k point."""
    variants = sorted({str(r["variant"]) for r in rows})
    checks = ["energy output?", "wavefunction output?", "spinor output?",
              "CB/HH/LH/SO character?", "oscillator strength?", "momentum matrix?"]
    fig, ax = plt.subplots(figsize=(9.0, 0.55 * max(len(variants), 1) + 2.4))
    grid = np.zeros((len(variants), len(checks)))
    for i, variant in enumerate(variants):
        subset = [r for r in rows if str(r["variant"]) == variant]
        for j, check in enumerate(checks):
            hits = sum(1 for r in subset if str(r.get(check, "no")).upper() == "YES")
            grid[i, j] = hits / max(len(subset), 1)
    image = ax.imshow(grid, cmap="Greens", vmin=0, vmax=1, aspect="auto")
    ax.set(xticks=range(len(checks)), yticks=range(len(variants)),
           title="Figure 1 - pilot output coverage (fraction of k points)")
    ax.set_xticklabels([c.replace("?", "") for c in checks], rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels(variants, fontsize=8)
    for i in range(len(variants)):
        for j in range(len(checks)):
            ax.text(j, i, f"{grid[i, j]:.0%}", ha="center", va="center", fontsize=7,
                    color="k" if grid[i, j] < 0.6 else "w")
    fig.colorbar(image, ax=ax, label="fraction of k points")
    _finish(fig, path, dpi)


def dispersion(path: Path, rows: Sequence[Mapping[str, Any]], dpi: int) -> None:
    """Figure 2: extended subband dispersion, coloured by dominant character."""
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    colours = {"CB": "#377eb8", "HH": "#e41a1c", "LH": "#4daf4a", "SO": "#984ea3"}
    for label in sorted({str(r["state"]) for r in rows}):
        subset = sorted((r for r in rows if str(r["state"]) == label),
                        key=lambda r: float(r["k_per_nm"]))
        band = str(subset[0]["dominant_band"])
        ax.plot([float(r["k_per_nm"]) for r in subset],
                [float(r["energy_eV"]) for r in subset],
                color=colours.get(band, "0.5"), lw=1.2,
                ls="-" if all(bool(r["confined"]) for r in subset) else ":")
        ax.annotate(label, (float(subset[-1]["k_per_nm"]), float(subset[-1]["energy_eV"])),
                    fontsize=6, xytext=(3, 0), textcoords="offset points")
    handles = [plt.Line2D([], [], color=c, label=b) for b, c in colours.items()]
    handles.append(plt.Line2D([], [], color="0.4", ls=":", label="unconfined (box state)"))
    ax.legend(handles=handles, fontsize=8, ncol=5)
    ax.set(xlabel="k (1/nm)", ylabel="energy (eV)",
           title="Figure 2 - extended subband dispersion with state character")
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def character(path: Path, rows: Sequence[Mapping[str, Any]], dpi: int) -> None:
    """Figure 3: CB/HH/LH/SO fractions versus k for each tracked state."""
    labels = sorted({str(r["state"]) for r in rows})[:12]
    cols = min(4, max(len(labels), 1))
    rows_n = int(np.ceil(len(labels) / cols)) or 1
    fig, axes = plt.subplots(rows_n, cols, figsize=(3.0 * cols, 2.3 * rows_n), squeeze=False)
    for index, label in enumerate(labels):
        ax = axes[index // cols][index % cols]
        subset = sorted((r for r in rows if str(r["state"]) == label),
                        key=lambda r: float(r["k_per_nm"]))
        k = [float(r["k_per_nm"]) for r in subset]
        bottom = np.zeros(len(subset))
        for band, colour in zip(BANDS, BAND_COLOURS):
            values = np.asarray([float(r[band]) for r in subset])
            ax.fill_between(k, bottom, bottom + values, color=colour,
                            label=band.split()[0] if index == 0 else None)
            bottom += values
        ax.set(title=label, ylim=(0, 1), xlim=(min(k) if k else 0, max(k) if k else 1))
        ax.tick_params(labelsize=7)
    for spare in range(len(labels), rows_n * cols):
        axes[spare // cols][spare % cols].axis("off")
    if labels:
        axes[0][0].legend(fontsize=7, loc="lower left")
    fig.suptitle("Figure 3 - spinor character versus k")
    _finish(fig, path, dpi)


def tracking_confidence(path: Path, rows: Sequence[Mapping[str, Any]], dpi: int) -> None:
    """Figure 4: tracking score and assignment margin versus k."""
    fig, axes = plt.subplots(2, 1, figsize=(9.0, 6.0), sharex=True)
    for label in sorted({str(r["state"]) for r in rows}):
        subset = sorted((r for r in rows if str(r["state"]) == label),
                        key=lambda r: float(r["k_per_nm"]))
        k = [float(r["k_per_nm"]) for r in subset]
        axes[0].plot(k, [float(r["tracking_score"]) for r in subset], lw=1.0, label=label)
        axes[1].plot(k, [float(r["assignment_margin"]) for r in subset], lw=1.0)
    axes[0].axhline(0.60, color="k", ls="--", lw=0.8)
    axes[1].axhline(0.15, color="k", ls="--", lw=0.8)
    axes[0].set(ylabel="tracking score", title="Figure 4 - state-tracking confidence")
    axes[1].set(xlabel="k (1/nm)", ylabel="assignment margin")
    axes[0].legend(fontsize=6, ncol=6)
    for ax in axes:
        ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def transition_map(path: Path, rows: Sequence[Mapping[str, Any]], target_eV: float,
                   ceiling_eV: float, dpi: int) -> None:
    """Figure 5/6: transition energies versus k against the target and the ceiling."""
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    electrons = sorted({str(r["state"]) for r in rows if str(r["dominant_band"]) == "CB"})
    holes = sorted({str(r["state"]) for r in rows if str(r["dominant_band"]) in ("HH", "LH", "SO")})
    by_state: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_state.setdefault(str(row["state"]), []).append(row)
    for e in electrons:
        for h in holes:
            a = sorted(by_state[e], key=lambda r: float(r["k_per_nm"]))
            b = sorted(by_state[h], key=lambda r: float(r["k_per_nm"]))
            n = min(len(a), len(b))
            if not n:
                continue
            k = [float(a[i]["k_per_nm"]) for i in range(n)]
            delta = [float(a[i]["energy_eV"]) - float(b[i]["energy_eV"]) for i in range(n)]
            bound = all(bool(a[i]["confined"]) and bool(b[i]["confined"]) for i in range(n))
            ax.plot(k, delta, lw=0.9, alpha=0.85 if bound else 0.35,
                    ls="-" if bound else ":")
    ax.axhline(target_eV, color="#d95f02", lw=2.0, label=f"paper P1/P3 target {target_eV:.3f} eV")
    ax.axhline(ceiling_eV, color="#1b9e77", lw=2.0, ls="--",
               label=f"bound-bound ceiling (barrier gap) {ceiling_eV:.3f} eV")
    ax.set(xlabel="k (1/nm)", ylabel="transition energy (eV)",
           title="Figures 5/6 - all transition energies vs k, and the ~2.296 eV search")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def candidate_strength(path: Path, candidates: Sequence[Mapping[str, Any]], dpi: int) -> None:
    """Figure 7: optical weight of every ~2.296 eV candidate."""
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    if not candidates:
        ax.text(0.5, 0.5, "No transition fell within the search tolerance",
                ha="center", va="center", fontsize=11)
        ax.set_axis_off()
    else:
        overlap = [abs(float(c.get("envelope_overlap") or np.nan)) for c in candidates]
        strength = [abs(float(c.get("oscillator_strength") or np.nan)) for c in candidates]
        bound = [bool(c.get("both_bound")) for c in candidates]
        ax.scatter([o for o, b in zip(overlap, bound) if b],
                   [s for s, b in zip(strength, bound) if b],
                   c="#1b9e77", label="bound pair", s=40)
        ax.scatter([o for o, b in zip(overlap, bound) if not b],
                   [s for s, b in zip(strength, bound) if not b],
                   c="#d95f02", marker="x", label="involves an unconfined state", s=40)
        ax.set(xlabel="envelope overlap |<hole|electron>|", ylabel="oscillator strength",
               title="Figure 7 - optical relevance of ~2.296 eV candidates")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def matrix_ratio(path: Path, matrices, block: str, names: Sequence[str], title: str,
                 dpi: int) -> None:
    """Figures 8/9/10: M(k)/M(0) for one matrix family."""
    array = getattr(matrices, block)
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            base = array[i, j, 0]
            if abs(base) <= 0:
                continue
            ax.plot(matrices.k_per_nm, np.abs(array[i, j] / base), lw=1.3, label=f"{a}-{b}")
    ax.axhline(1.0, color="k", lw=0.8)
    for level, style in ((1.05, ":"), (0.95, ":"), (1.10, "--"), (0.90, "--")):
        ax.axhline(level, color="0.7", lw=0.7, ls=style)
    ax.set(xlabel="k (1/nm)", ylabel="|M(k)| / |M(0)|", title=title)
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def pathway_ratios(path: Path, matrices, ratios: Sequence[Mapping[str, Any]], dpi: int) -> None:
    """Figure 11: every pathway numerator ratio."""
    import finite_k_matrices as fkm  # noqa: PLC0415

    numerators = fkm.pathway_numerators(matrices)
    fig, ax = plt.subplots(figsize=(10.0, 5.8))
    for item in fkm.PATHWAYS:
        base = numerators[item.index, 0]
        if abs(base) <= 1e-12 * float(np.max(np.abs(numerators[:, 0]))):
            continue
        style = "-" if item.side == "electron_side" else "--"
        ax.plot(matrices.k_per_nm, np.real(numerators[item.index] / base),
                lw=1.0, ls=style, label=item.label)
    ax.axhline(1.0, color="k", lw=0.8)
    ax.axhline(0.0, color="#d95f02", lw=0.9)
    ax.set(xlabel="k (1/nm)", ylabel="Re[M_p(k) / M_p(0)]",
           title="Figure 11 - pathway numerator ratios (solid: electron side, dashed: hole side)")
    ax.legend(fontsize=6, ncol=4)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def node_pathways(path: Path, matrices, ratios: Sequence[Mapping[str, Any]],
                  title: str, dpi: int) -> None:
    """Figures 12/13: the pathways that dominate a cancellation node."""
    import finite_k_matrices as fkm  # noqa: PLC0415

    numerators = fkm.pathway_numerators(matrices)
    order = np.argsort(np.abs(numerators[:, 0]))[::-1][:6]
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    for index in order:
        item = fkm.PATHWAYS[int(index)]
        base = numerators[item.index, 0]
        if abs(base) <= 0:
            continue
        ax.plot(matrices.k_per_nm, np.abs(numerators[item.index] / base), lw=1.4,
                ls="-" if item.side == "electron_side" else "--", label=item.label)
    ax.axhline(1.0, color="k", lw=0.8)
    ax.set(xlabel="k (1/nm)", ylabel="|M_p(k)| / |M_p(0)|", title=title)
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def spectrum_pair(path: Path, wavelength, finite, frozen, title: str, dpi: int) -> None:
    """Figure 14: finite-k M(k) against the M(k)=M(0) control."""
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    ax.plot(wavelength, _normalize(frozen.chi2), lw=1.6, label="Demo 23D style: M(k)=M(0)")
    ax.plot(wavelength, _normalize(finite.chi2), lw=1.6, label="Demo 25: finite-k M(k)")
    _mark_features(ax)
    ax.set(xlabel="fundamental wavelength (nm)", ylabel="normalized |chi2|", title=title,
           xlim=(400, 1850), ylim=(-0.03, 1.08))
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def spectrum_vs_paper(path: Path, wavelength, finite, paper_x, paper_y, dpi: int) -> None:
    """Figure 15: Demo 25 against the digitized paper curve."""
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    ax.plot(paper_x, _normalize(paper_y), "k--", lw=2.0, label="paper Fig. 2d (eye digitization)")
    ax.plot(wavelength, _normalize(finite.chi2), lw=1.6, label="Demo 25: finite-k M(k)")
    _mark_features(ax)
    ax.set(xlabel="fundamental wavelength (nm)", ylabel="normalized amplitude",
           title="Figure 15 - Demo 25 vs paper", xlim=(400, 1850), ylim=(-0.03, 1.08))
    ax.legend(fontsize=8)
    ax.grid(alpha=0.2)
    _finish(fig, path, dpi)


def feature_comparison(path: Path, scorecard: Sequence[Mapping[str, Any]], dpi: int) -> None:
    """Figure 16: per-feature wavelength error, Demo 23D against Demo 25."""
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    names = [str(r["Feature"]) for r in scorecard]
    x = np.arange(len(names))
    d23 = [float(r["Demo23D_lambda"]) - float(r["Paper_lambda"]) for r in scorecard]
    d25 = [float(r["Demo25_lambda"]) - float(r["Paper_lambda"]) for r in scorecard]
    ax.bar(x - 0.2, d23, 0.4, label="Demo 23D (M(k)=M(0))", color="#7570b3")
    ax.bar(x + 0.2, d25, 0.4, label="Demo 25 (finite-k M(k))", color="#1b9e77")
    ax.axhline(0, color="k", lw=0.9)
    ax.set(xticks=x, ylabel="model - paper wavelength (nm)",
           title="Figure 16 - feature comparison")
    ax.set_xticklabels(names)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.2)
    _finish(fig, path, dpi)


def write_all(directory: Path, cfg: Mapping[str, Any], data: Mapping[str, Any], dpi: int) -> None:
    """Emit every Demo 25 figure that the available data supports."""
    directory = Path(directory)
    tracking_rows = list(data.get("tracking") or [])
    edges = data.get("edges") or {}
    target = float(cfg["transition_search"]["target_eV"])
    ceiling = float(edges.get("barrier_gap_eV", np.nan))
    if tracking_rows:
        dispersion(directory / "figure02_extended_dispersion.png", tracking_rows, dpi)
        character(directory / "figure03_character_vs_k.png", tracking_rows, dpi)
        tracking_confidence(directory / "figure04_tracking_confidence.png", tracking_rows, dpi)
        transition_map(directory / "figure05_06_transition_search.png", tracking_rows,
                       target, ceiling, dpi)
    candidate_strength(directory / "figure07_candidate_optical_strength.png",
                       list(data.get("candidates") or []), dpi)
    matrices = data.get("matrices")
    if matrices is not None:
        matrix_ratio(directory / "figure08_overlap_ratio.png", matrices, "overlap",
                     ["e1", "e2"], "Figure 8 - O_nm(k) / O_nm(0)", dpi)
        matrix_ratio(directory / "figure09_electron_z_ratio.png", matrices, "z_e_nm",
                     ["e1", "e2"], "Figure 9 - z_e,nl(k) / z_e,nl(0)", dpi)
        matrix_ratio(directory / "figure10_hole_z_ratio.png", matrices, "z_hh_nm",
                     ["hh1", "hh2"], "Figure 10 - z_hh,ml(k) / z_hh,ml(0)", dpi)
        ratios = list(data.get("ratios") or [])
        pathway_ratios(directory / "figure11_pathway_ratios.png", matrices, ratios, dpi)
        node_pathways(directory / "figure12_node605_pathways.png", matrices, ratios,
                      "Figure 12 - dominant 605 nm cancellation pathways vs k", dpi)
        node_pathways(directory / "figure13_node1330_pathways.png", matrices, ratios,
                      "Figure 13 - dominant 1330 nm cancellation pathways vs k", dpi)
    if data.get("finite") is not None and data.get("frozen") is not None:
        spectrum_pair(directory / "figure14_demo23d_vs_demo25.png", data["wavelength"],
                      data["finite"], data["frozen"],
                      "Figure 14 - Demo 23D vs Demo 25 normalized spectrum", dpi)
        spectrum_vs_paper(directory / "figure15_demo25_vs_paper.png", data["wavelength"],
                          data["finite"], data["paper_x"], data["paper_y"], dpi)
    if data.get("scorecard"):
        feature_comparison(directory / "figure16_feature_comparison.png",
                           list(data["scorecard"]), dpi)
