"""Publication-quality diagnostic plots for Demo 23."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np


COLORS = {"23A": "#6b7280", "23B": "#d97706", "23C": "#15803d", "23D": "#2563eb"}
STATE_COLORS = {"e1": "#2563eb", "e2": "#7c3aed", "hh1": "#dc2626", "hh2": "#ea580c"}


def _save(fig: Any, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=int(dpi))
    plt.close(fig)


def _decorate(axis: Any, *, xlabel: str, ylabel: str, title: str) -> None:
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.grid(alpha=0.25)


def _k_markers(axis: Any, kmax: float) -> None:
    axis.axvline(0.0, color="black", linewidth=0.8, linestyle=":", label="k = 0")
    axis.axvline(kmax, color="black", linewidth=0.9, linestyle="--", label="nominal kmax")
    axis.axvspan(0.0, kmax, color="#94a3b8", alpha=0.06, label="Eq. 2 range")


def raw_dispersions(path: Path, k: np.ndarray, bands: Mapping[str, np.ndarray], dpi: int) -> None:
    fig, axis = plt.subplots(figsize=(9.2, 5.4))
    for state in ("e1", "e2", "hh1", "hh2"):
        axis.plot(k, bands[state], "o-", markersize=2.4, linewidth=1.0,
                  color=STATE_COLORS[state], label=f"{state} tracked kp8")
    _k_markers(axis, float(k[-1]))
    _decorate(axis, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Energy (eV)",
              title="Figure 1 — tracked Professional nextnano kp8 dispersions")
    axis.legend(fontsize=8, ncol=2)
    _save(fig, path, dpi)
    for suffix, states, title in (
        ("_electron_zoom", ("e1", "e2"), "Figure 1e — electron dispersion zoom"),
        ("_heavy_hole_zoom", ("hh1", "hh2"), "Figure 1h — heavy-hole dispersion zoom"),
    ):
        fig, axis = plt.subplots(figsize=(8.7, 4.8))
        for state in states:
            axis.plot(k, bands[state], "o-", markersize=2.6, linewidth=1.0,
                      color=STATE_COLORS[state], label=f"{state} tracked kp8")
        _k_markers(axis, float(k[-1]))
        _decorate(axis, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Energy (eV)", title=title)
        axis.legend(fontsize=8)
        _save(fig, path.with_name(path.stem + suffix + path.suffix), dpi)


def fit_plot(path: Path, k: np.ndarray, raw: Mapping[str, np.ndarray], fits: Mapping[str, Any],
             states: tuple[str, ...], title: str, dpi: int) -> None:
    fig, axis = plt.subplots(figsize=(9.2, 5.3))
    notes = []
    for state in states:
        fit = fits[state]
        axis.plot(k, raw[state], "o", markersize=2.8, color=STATE_COLORS[state],
                  label=f"{state} tracked kp8")
        axis.plot(k, fit.evaluate(k), "--", linewidth=1.5, color=STATE_COLORS[state],
                  label=f"{state} anchored parabola")
        notes.append(
            f"{state}: m*/m0={fit.effective_mass_m0:.5g}, RMSE={fit.rmse_meV:.3g} meV, "
            f"max={fit.max_abs_residual_meV:.3g} meV, fit 0–{fit.fit_kmax_per_nm:.4g} nm⁻¹"
        )
    _k_markers(axis, float(k[-1]))
    _decorate(axis, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Energy (eV)", title=title)
    axis.text(0.01, 0.01, "\n".join(notes), transform=axis.transAxes, fontsize=8,
              va="bottom", bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#cbd5e1"})
    axis.legend(fontsize=8, ncol=2)
    _save(fig, path, dpi)


def residual_plot(path: Path, k: np.ndarray, raw: Mapping[str, np.ndarray], fits: Mapping[str, Any],
                  states: tuple[str, ...], title: str, dpi: int) -> None:
    fig, axis = plt.subplots(figsize=(9.2, 4.9))
    for state in states:
        residual = 1000.0 * (raw[state] - fits[state].evaluate(k))
        axis.plot(k, residual, color=STATE_COLORS[state], label=state)
        index = int(np.argmax(np.abs(residual)))
        axis.scatter([k[index]], [residual[index]], color=STATE_COLORS[state], zorder=4)
        axis.annotate(f"{state}: {residual[index]:.3g} meV @ {k[index]:.4g}",
                      (k[index], residual[index]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    axis.axhline(0.0, color="black", linewidth=0.8)
    _k_markers(axis, float(k[-1]))
    _decorate(axis, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="E(raw) − E(fit) (meV)", title=title)
    axis.legend(fontsize=8)
    _save(fig, path, dpi)


def local_curvature(path: Path, k: np.ndarray, raw: Mapping[str, np.ndarray], dpi: int) -> None:
    fig, axis = plt.subplots(figsize=(9.2, 4.9))
    for state in ("hh1", "hh2"):
        d1 = np.gradient(raw[state], k)
        d2 = np.gradient(d1, k)
        axis.plot(k, d2, color=STATE_COLORS[state], label=state)
    axis.axhline(0.0, color="black", linewidth=0.8)
    _k_markers(axis, float(k[-1]))
    _decorate(axis, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel=r"$d^2E/dk^2$ (eV nm$^2$)",
              title="Figure 5b — heavy-hole local-curvature diagnostic (not production physics)")
    axis.legend(fontsize=8)
    _save(fig, path, dpi)


def transition_mode_detail(path: Path, k: np.ndarray, result: Any, target_nm: float, hc: float, dpi: int) -> None:
    fig, axis = plt.subplots(figsize=(9.0, 5.1))
    for label, values in result.transitions.as_dict().items():
        axis.plot(k, values, label=label.replace("DeltaE", "ΔE"))
    axis.axhline(2.0 * hc / target_nm, color="black", linestyle="--", linewidth=1.0,
                 label=f"2Ephoton at {target_nm:g} nm")
    _k_markers(axis, float(k[-1]))
    _decorate(axis, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel="Transition energy (eV)",
              title=f"Figure 6 — {result.mode} four same-k transitions")
    axis.legend(fontsize=8, ncol=2)
    _save(fig, path, dpi)


def transition_modes(path: Path, k: np.ndarray, mode_results: Mapping[str, Any],
                     target_nm: float, hc: float, dpi: int) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.5), sharex=True)
    resonance = 2.0 * hc / target_nm
    for axis, label in zip(axes.flat, ("DeltaE_11", "DeltaE_12", "DeltaE_21", "DeltaE_22")):
        for mode, result in mode_results.items():
            axis.plot(k, result.transitions.as_dict()[label], label=mode, color=COLORS[mode])
        axis.axhline(resonance, color="black", linestyle="--", linewidth=0.8)
        axis.set_title(label.replace("DeltaE", "ΔE"))
        axis.grid(alpha=0.25)
    axes[1, 0].set_xlabel(r"$k_\parallel$ (nm$^{-1}$)")
    axes[1, 1].set_xlabel(r"$k_\parallel$ (nm$^{-1}$)")
    axes[0, 0].set_ylabel("Transition energy (eV)")
    axes[1, 0].set_ylabel("Transition energy (eV)")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(f"Figure 7 — A–D transition-energy comparison; dashed = 2Ephoton ({target_nm:g} nm)")
    _save(fig, path, dpi)


def spectra(path: Path, results: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]],
            target_nm: float, dpi: int) -> None:
    fig, axis = plt.subplots(figsize=(10.3, 5.8))
    by_mode = {str(row["mode"]): row for row in metrics}
    for mode, result in results.items():
        axis.plot(result.spectrum.wavelength_nm, result.magnitude, label=mode, color=COLORS[mode])
    axis.axvline(target_nm, color="black", linestyle="--", linewidth=0.9, label=f"{target_nm:g} nm")
    notes = []
    for mode in results:
        row = by_mode[mode]
        fwhm = float(row["FWHM_nm"])
        fwhm_text = f"{fwhm:.1f}" if np.isfinite(fwhm) else "not defined"
        notes.append(f"{mode}: χ1550={float(row['chi2_1550_pm_per_V']):.4g}, peak={float(row['peak_chi2_pm_per_V']):.4g} @ {float(row['peak_wavelength_nm']):.0f} nm, FWHM={fwhm_text}")
    _decorate(axis, xlabel="Fundamental wavelength (nm)", ylabel=r"$|\chi^{(2)}|$ (pm/V)",
              title="Figure 8 — full Demo 23 controlled-dispersion spectrum")
    axis.text(0.01, 0.99, "\n".join(notes), transform=axis.transAxes, fontsize=7.4, va="top",
              bbox={"facecolor": "white", "alpha": 0.86, "edgecolor": "#cbd5e1"})
    axis.legend(fontsize=8)
    _save(fig, path, dpi)


def differences(path: Path, results: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]],
                tolerance: float, dpi: int) -> None:
    if "23D" not in results:
        return
    reference = results["23D"]
    fig, axes = plt.subplots(2, 1, figsize=(10.0, 7.3), sharex=True)
    denominator = np.maximum(reference.magnitude, 1e-6 * np.max(reference.magnitude))
    by_mode = {str(row["mode"]): row for row in metrics}
    for mode, result in results.items():
        if mode == "23D":
            continue
        delta = result.magnitude - reference.magnitude
        axes[0].plot(result.spectrum.wavelength_nm, delta, label=f"{mode} − 23D", color=COLORS[mode])
        axes[1].plot(result.spectrum.wavelength_nm, 100.0 * delta / denominator,
                     label=f"{mode} − 23D", color=COLORS[mode])
    for axis in axes:
        axis.axhline(0.0, color="black", linewidth=0.7)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    axes[0].set_ylabel("Absolute difference (pm/V)")
    axes[1].set_ylabel("Relative difference (%)")
    axes[1].set_xlabel("Fundamental wavelength (nm)")
    c = by_mode.get("23C")
    if c:
        status = "PASS" if float(c["relative_spectrum_RMSE_vs_23D"]) <= tolerance else "FAIL"
        axes[0].set_title(f"Figure 9 — difference from 23D; 23C RMSE={100*float(c['relative_spectrum_RMSE_vs_23D']):.4g}% ≤ {100*tolerance:g}%: {status}")
    notes = [f"{mode}: max rel={100*float(by_mode[mode]['max_relative_deviation_vs_23D']):.4g}% @ {float(by_mode[mode]['max_relative_deviation_wavelength_nm']):.0f} nm" for mode in results if mode != "23D"]
    axes[1].text(0.01, 0.02, "\n".join(notes), transform=axes[1].transAxes, fontsize=8,
                 bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#cbd5e1"})
    _save(fig, path, dpi)


def k_integrand(path: Path, k: np.ndarray, results: Mapping[str, Any], prefactor: float,
                target_nm: float, dpi: int) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(9.5, 8.4), sharex=True)
    for mode, result in results.items():
        iw = int(np.argmin(np.abs(result.spectrum.wavelength_nm - target_nm)))
        contribution = prefactor * result.spectrum.summed_integrand[iw] * result.spectrum.k_weights
        axes[0].plot(k, contribution.real, label=mode, color=COLORS[mode])
        axes[1].plot(k, contribution.imag, label=mode, color=COLORS[mode])
        axes[2].plot(k, np.abs(contribution), label=mode, color=COLORS[mode])
    for axis in axes:
        axis.axvline(float(k[-1]), color="black", linestyle="--", linewidth=0.8)
        axis.axhline(0.0, color="black", linewidth=0.6)
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Real per-node (pm/V)")
    axes[1].set_ylabel("Imag per-node (pm/V)")
    axes[2].set_ylabel("Magnitude per-node (pm/V)")
    axes[2].set_xlabel(r"$k_\parallel$ (nm$^{-1}$)")
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Figure 10 — weighted complex radial Equation 2 integrand at {target_nm:g} nm")
    _save(fig, path, dpi)


def cumulative_k(path: Path, k: np.ndarray, results: Mapping[str, Any], prefactor: float,
                 target_nm: float, dpi: int) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9.5, 7.1), sharex=True)
    for mode, result in results.items():
        iw = int(np.argmin(np.abs(result.spectrum.wavelength_nm - target_nm)))
        increments = prefactor * result.spectrum.summed_integrand[iw] * result.spectrum.k_weights
        cumulative = np.cumsum(increments)
        axes[0].plot(k, np.abs(cumulative), label=mode, color=COLORS[mode])
        final = abs(cumulative[-1])
        axes[1].plot(k, np.abs(cumulative) / max(final, 1e-300), label=mode, color=COLORS[mode])
    for axis in axes:
        axis.axvline(float(k[-1]), color="black", linestyle="--", linewidth=0.8, label="nominal kmax")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel(r"$|\chi^{(2)}(k\leq K)|$ (pm/V)")
    axes[1].set_ylabel("Magnitude / final magnitude")
    axes[1].set_xlabel(r"Upper integration limit K (nm$^{-1}$)")
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Figure 11 — cumulative k contribution at {target_nm:g} nm")
    _save(fig, path, dpi)


def pathway_contributions(path: Path, result: Any, wavelength_nm: float, context: str, dpi: int) -> None:
    index = int(np.argmin(np.abs(result.spectrum.wavelength_nm - wavelength_nm)))
    values = result.spectrum.terms[:, index]
    labels = list(result.spectrum.term_labels)
    electron = np.sum(values[[label.startswith("C_") for label in labels]])
    hole = np.sum(values[[label.startswith("V_") for label in labels]])
    totals = [electron, hole, result.spectrum.chi2[index]]
    fig, axes = plt.subplots(2, 1, figsize=(12.0, 7.7), gridspec_kw={"height_ratios": [2.2, 1]})
    x = np.arange(len(labels))
    axes[0].bar(x - 0.2, values.real, width=0.4, label="real")
    axes[0].bar(x + 0.2, values.imag, width=0.4, label="imag")
    axes[0].set_xticks(x, labels, rotation=55, ha="right", fontsize=7)
    axes[0].set_ylabel("Pathway contribution (pm/V)")
    axes[0].axhline(0, color="black", linewidth=0.7)
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].legend(fontsize=8)
    tx = np.arange(3)
    axes[1].bar(tx - 0.2, [v.real for v in totals], width=0.4, label="real")
    axes[1].bar(tx + 0.2, [v.imag for v in totals], width=0.4, label="imag")
    axes[1].set_xticks(tx, ["electron subtotal", "HH subtotal (signed)", "final"])
    axes[1].set_ylabel("Subtotal (pm/V)")
    axes[1].axhline(0, color="black", linewidth=0.7)
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle(f"Figure 12 — {result.mode} pathways at {result.spectrum.wavelength_nm[index]:g} nm ({context})")
    _save(fig, path, dpi)


def major_pathway_changes(path: Path, results: Mapping[str, Any], target_nm: float, dpi: int) -> None:
    if not results:
        return
    first = next(iter(results.values()))
    index = int(np.argmin(np.abs(first.spectrum.wavelength_nm - target_nm)))
    stack = np.vstack([result.spectrum.terms[:, index] for result in results.values()])
    top = np.argsort(np.max(np.abs(stack), axis=0))[::-1][:8]
    modes = list(results)
    x = np.arange(len(top))
    width = 0.8 / len(modes)
    fig, axis = plt.subplots(figsize=(11.2, 5.6))
    for offset, mode in enumerate(modes):
        values = results[mode].spectrum.terms[top, index]
        axis.bar(x - 0.4 + width / 2 + offset * width, values.real, width=width,
                 color=COLORS[mode], label=mode)
    axis.set_xticks(x, [first.spectrum.term_labels[i] for i in top], rotation=40, ha="right")
    axis.axhline(0.0, color="black", linewidth=0.7)
    _decorate(axis, xlabel="Largest pathways (ranked across modes)", ylabel="Real contribution (pm/V)",
              title=f"Figure 13 — major pathway changes across A–D at {target_nm:g} nm")
    axis.legend(fontsize=8)
    _save(fig, path, dpi)


def convergence(path: Path, rows: list[dict[str, Any]], key: str, title: str,
                tolerance: float, nominal: float | None, dpi: int) -> None:
    if not rows:
        return
    fig, axes = plt.subplots(1, 3, figsize=(13.3, 4.4))
    metrics = (("chi2_1550_pm_per_V", r"$|\chi^{(2)}(1550)|$ (pm/V)"),
               ("peak_chi2_pm_per_V", "Peak |χ²| (pm/V)"),
               ("peak_wavelength_nm", "Peak wavelength (nm)"))
    for mode in sorted({str(row["mode"]) for row in rows}):
        selected = sorted((row for row in rows if row["mode"] == mode), key=lambda row: float(row[key]))
        x = [float(row[key]) for row in selected]
        for axis, (metric, ylabel) in zip(axes, metrics):
            axis.plot(x, [float(row[metric]) for row in selected], "o-", label=mode, color=COLORS[mode])
            axis.set_ylabel(ylabel)
            axis.grid(alpha=0.25)
            if nominal is not None:
                axis.axvline(nominal, color="black", linestyle="--", linewidth=0.8)
    for axis in axes:
        axis.set_xlabel(key.replace("_", " "))
    axes[0].legend(fontsize=8)
    selected_rows = rows if nominal is None else [row for row in rows if np.isclose(float(row[key]), nominal)]
    status = bool(selected_rows) and all(bool(row["converged_vs_finest"]) for row in selected_rows)
    fig.suptitle(f"{title}; tolerance={100*tolerance:.3g}% — {'PASS' if status else 'FAIL'}")
    _save(fig, path, dpi)


def isotropy(path: Path, k: np.ndarray, differences_meV: Mapping[str, np.ndarray],
             rows: Sequence[Mapping[str, Any]], dpi: int) -> None:
    if not differences_meV:
        return
    fig, axis = plt.subplots(figsize=(9.2, 5.1))
    for state, values in differences_meV.items():
        axis.plot(k, values, label=state, color=STATE_COLORS[state])
    tolerance = float(rows[0]["tolerance_meV"])
    axis.axhline(tolerance, color="black", linestyle="--", linewidth=0.8)
    axis.axhline(-tolerance, color="black", linestyle="--", linewidth=0.8)
    maximum = max(float(row["max_absolute_anisotropy_meV"]) for row in rows)
    passed = all(bool(row["radial_assumption_pass"]) for row in rows)
    _decorate(axis, xlabel=r"$k_\parallel$ (nm$^{-1}$)", ylabel=r"$E_y-E_{45^\circ}$ (meV)",
              title=f"Figure 16 — in-plane anisotropy: max={maximum:.4g} meV, limit={tolerance:g} meV — {'PASS' if passed else 'FAIL'}")
    axis.legend(fontsize=8)
    _save(fig, path, dpi)


def paper_full_overlay(path: Path, results: Mapping[str, Any], paper: Any,
                       simulated_peak_nm: float, measured_peak_nm: float, dpi: int) -> None:
    fig, axis = plt.subplots(figsize=(10.3, 5.7))
    for mode, result in results.items():
        axis.plot(result.spectrum.wavelength_nm, result.magnitude, color=COLORS[mode], label=f"Demo {mode}")
    axis.plot(paper.wavelength_nm, paper.chi2_pm_per_V, "k--", linewidth=1.5, label=paper.label)
    axis.axvline(simulated_peak_nm, color="black", linestyle=":", linewidth=0.9,
                 label=f"paper simulated peak ~{simulated_peak_nm:g} nm")
    axis.axvline(measured_peak_nm, color="#dc2626", linestyle=":", linewidth=0.9,
                 label=f"paper measured peak ~{measured_peak_nm:g} nm (location only)")
    _decorate(axis, xlabel="Fundamental wavelength (nm)", ylabel=r"$|\chi^{(2)}|$ (pm/V)",
              title="P1 — full spectrum vs paper Equation 2 simulation")
    axis.legend(fontsize=7.5, ncol=2)
    axis.text(0.01, 0.02, "Paper curve is eye-digitized, not raw/tabulated data; measured SH intensity is not plotted on this axis.",
              transform=axis.transAxes, fontsize=8, bbox={"facecolor": "white", "alpha": 0.85})
    _save(fig, path, dpi)


def paper_normalized(path: Path, results: Mapping[str, Any], paper: Any, dpi: int) -> None:
    fig, axis = plt.subplots(figsize=(10.3, 5.7))
    for mode, result in results.items():
        values = result.magnitude
        axis.plot(result.spectrum.wavelength_nm, values / max(float(np.max(values)), 1e-300),
                  color=COLORS[mode], label=f"Demo {mode}")
    values = paper.chi2_pm_per_V / max(float(np.max(paper.chi2_pm_per_V)), 1e-300)
    axis.plot(paper.wavelength_nm, values, "k--", linewidth=1.5, label=paper.label)
    _decorate(axis, xlabel="Fundamental wavelength (nm)", ylabel="Normalized |χ²|",
              title="P2 — normalized spectral shape and resonance location")
    axis.legend(fontsize=8)
    _save(fig, path, dpi)


def paper_normalized_zero_diagnostic(
    path: Path,
    results: Mapping[str, Any],
    paper: Any,
    zero_rows: Sequence[Mapping[str, Any]],
    dpi: int,
) -> None:
    """Plot normalized shapes and quantify the paper's near-zero spectral nodes."""
    if not zero_rows:
        return
    fig, (axis, bars_axis) = plt.subplots(
        2, 1, figsize=(10.7, 8.0), gridspec_kw={"height_ratios": [2.4, 1.0]}
    )
    normalized_by_mode: dict[str, np.ndarray] = {}
    for mode, result in results.items():
        values = result.magnitude / max(float(np.max(result.magnitude)), 1e-300)
        normalized_by_mode[str(mode)] = values
        linewidth = 2.0 if mode in ("23C", "23D") else 1.1
        alpha = 1.0 if mode in ("23C", "23D") else 0.65
        axis.plot(
            result.spectrum.wavelength_nm, values, color=COLORS[mode],
            linewidth=linewidth, alpha=alpha, label=f"Demo {mode}",
        )
    paper_values = paper.chi2_pm_per_V / max(float(np.max(paper.chi2_pm_per_V)), 1e-300)
    axis.plot(
        paper.wavelength_nm, paper_values, "k--", linewidth=2.0,
        marker="o", markersize=3.0, label=paper.label,
    )
    targets = sorted({float(row["paper_zero_wavelength_nm"]) for row in zero_rows})
    for index, target in enumerate(targets):
        matching = [row for row in zero_rows if np.isclose(float(row["paper_zero_wavelength_nm"]), target)]
        window_min = min(float(row["search_window_min_nm"]) for row in matching)
        window_max = max(float(row["search_window_max_nm"]) for row in matching)
        axis.axvspan(window_min, window_max, color="#94a3b8", alpha=0.10)
        axis.axvline(
            target, color="black", linestyle=":", linewidth=1.0,
            label="paper zero locations" if index == 0 else None,
        )
        axis.annotate(
            f"paper zero\n{target:g} nm", (target, 0.0), xytext=(5, 12),
            textcoords="offset points", fontsize=8, va="bottom",
        )
    _decorate(
        axis, xlabel="Fundamental wavelength (nm)", ylabel=r"Normalized $|\chi^{(2)}|$",
        title="P2b — normalized shape: paper spectral zeros versus Demo 23",
    )
    axis.set_ylim(-0.025, 1.05)
    axis.legend(fontsize=7.5, ncol=2)
    axis.text(
        0.01, 0.98,
        "Zeros are read from the 45-point eye digitization and are diagnostic, not exact author data.",
        transform=axis.transAxes, va="top", fontsize=8,
        bbox={"facecolor": "white", "alpha": 0.86, "edgecolor": "#cbd5e1"},
    )

    modes = list(results)
    x = np.arange(len(targets), dtype=float)
    width = 0.78 / (len(modes) + 1)
    series = [("Paper", "#111827")] + [(mode, COLORS[mode]) for mode in modes]
    for offset, (label, color) in enumerate(series):
        if label == "Paper":
            values = [float(np.interp(target, paper.wavelength_nm, paper_values)) for target in targets]
        else:
            result = results[label]
            values = [
                float(np.interp(target, result.spectrum.wavelength_nm, normalized_by_mode[label]))
                for target in targets
            ]
        positions = x - 0.39 + width / 2 + offset * width
        bars = bars_axis.bar(positions, values, width=width, color=color, label=label)
        bars_axis.bar_label(bars, labels=[f"{value:.3f}" for value in values], fontsize=7, padding=2)
    bars_axis.axhline(0.05, color="#dc2626", linestyle="--", linewidth=0.9,
                      label="5% near-zero diagnostic")
    bars_axis.set_xticks(x, [f"{target:g} nm" for target in targets])
    bars_axis.set_ylabel("Normalized value\nat paper zero")
    bars_axis.set_xlabel("Digitized paper zero location")
    bars_axis.grid(axis="y", alpha=0.25)
    bars_axis.legend(fontsize=7.2, ncol=3)
    _save(fig, path, dpi)


def paper_peaks(path: Path, metrics: Sequence[Mapping[str, Any]], simulated_peak_nm: float,
                measured_peak_nm: float, dpi: int) -> None:
    labels = [str(row["mode"]) for row in metrics] + ["paper simulation", "paper measurement"]
    values = [float(row["peak_wavelength_nm"]) for row in metrics] + [simulated_peak_nm, measured_peak_nm]
    colors = [COLORS[label] for label in labels[:-2]] + ["#111827", "#dc2626"]
    fig, axis = plt.subplots(figsize=(9.2, 5.1))
    bars = axis.bar(labels, values, color=colors)
    axis.bar_label(bars, labels=[f"{v:.0f} nm\nΔsim={v-simulated_peak_nm:+.0f}" for v in values], fontsize=8)
    axis.set_ylim(min(values) - 80, max(values) + 100)
    _decorate(axis, xlabel="Source/model", ylabel="Peak fundamental wavelength (nm)",
              title="P3 — peak-location comparison")
    _save(fig, path, dpi)


def paper_1550(path: Path, metrics: Sequence[Mapping[str, Any]], paper_value: float, dpi: int) -> None:
    labels = [str(row["mode"]) for row in metrics] + ["paper ideal abrupt"]
    values = [float(row["chi2_1550_pm_per_V"]) for row in metrics] + [paper_value]
    colors = [COLORS[label] for label in labels[:-1]] + ["#111827"]
    fig, axis = plt.subplots(figsize=(9.2, 5.1))
    bars = axis.bar(labels, values, color=colors)
    axis.bar_label(bars, labels=[f"{v:.4g}" for v in values], fontsize=8)
    _decorate(axis, xlabel="Source/model", ylabel=r"$|\chi^{(2)}(1550)|$ (pm/V)",
              title="P4 — absolute susceptibility at 1550 nm")
    axis.text(0.01, 0.98, "Paper point: ideal abrupt interfaces. Demo 23: linear 1 nm grading; exact agreement is not expected.",
              transform=axis.transAxes, va="top", fontsize=8,
              bbox={"facecolor": "white", "alpha": 0.85})
    _save(fig, path, dpi)


def paper_errors(path: Path, rows: Sequence[Mapping[str, Any]], dpi: int) -> None:
    if not rows:
        return
    labels = [str(row["mode"]) for row in rows]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.5))
    quantities = (("normalized_RMSE_vs_digitized_paper", "Normalized RMSE"),
                  ("peak_wavelength_error_nm", "Peak wavelength error (nm)"),
                  ("chi2_1550_error_pm_per_V", "χ²(1550) error (pm/V)"))
    for axis, (key, ylabel) in zip(axes, quantities):
        values = [float(row[key]) for row in rows]
        axis.bar(labels, values, color=[COLORS[label] for label in labels])
        axis.axhline(0.0, color="black", linewidth=0.7)
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("P5 — diagnostic errors to eye-digitized paper simulation (not an acceptance gate)")
    _save(fig, path, dpi)
