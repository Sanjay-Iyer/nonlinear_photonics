"""Fourteen concise diagnostic figures for Demo 18B."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _save(fig: Any, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _state_plot(path: Path, analysis: Mapping[str, Any], band: str, density: bool) -> Path:
    data = analysis["data"]
    states = data.electron if band == "electron" else data.heavy_hole
    values = data.electron_density if band == "electron" else data.heavy_hole_density
    edge_key = "conduction_eV" if band == "electron" else "heavy_hole_eV"
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(data.band_position_nm, data.band_edges[edge_key], color="black", lw=1.4, label="band edge")
    for index in range(min(4, states.count)):
        if density:
            curve = values[:, index]
            scale = 0.12 / max(float(np.max(curve)), 1e-30)
            label = f"{band[0].upper()}{index + 1} |psi|²"
        else:
            curve = states.envelopes[:, index]
            scale = 0.12 / max(float(np.max(np.abs(curve))), 1e-30)
            label = f"{band[0].upper()}{index + 1} psi"
        ax.plot(states.z_nm, states.energies_eV[index] + curve * scale, lw=1.2, label=label)
        ax.axhline(states.energies_eV[index], color="0.75", lw=0.5)
    ax.set_title(f"{band.replace('_', ' ').title()} {'Probabilities' if density else 'States'}")
    ax.set_xlabel("z (nm)")
    ax.set_ylabel("Energy (eV), curves offset")
    ax.legend(frameon=False, ncol=2, fontsize=8)
    ax.grid(alpha=0.15)
    return _save(fig, path)


def localization(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    rows = [row for row in rows if int(row["state"]) <= 2]
    labels = [f"{'E' if r['band']=='electron' else 'HH'}{r['state']}" for r in rows]
    left = [float(r["left_well_probability"]) for r in rows]
    barrier = [float(r["central_barrier_probability"]) for r in rows]
    right = [float(r["right_well_probability"]) for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    ax.bar(x, left, label="left well")
    ax.bar(x, barrier, bottom=left, label="barrier")
    ax.bar(x, right, bottom=np.asarray(left) + barrier, label="right well")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Probability")
    ax.set_title("State Localization")
    ax.legend(frameon=False)
    return _save(fig, path)


def convergence(path: Path, rows: Sequence[Mapping[str, Any]], kind: str) -> Path:
    if kind == "energies":
        fields = (("e1_eV", "E1"), ("e2_eV", "E2"), ("hh1_eV", "HH1"), ("hh2_eV", "HH2"))
        ylabel = "Energy (eV)"
    else:
        fields = (("z_e12_nm", "e z12"), ("z_hh12_nm", "HH z12"),
                  ("delta_z_e_nm", "e delta z"), ("delta_z_hh_nm", "HH delta z"))
        ylabel = "Matrix element (nm)"
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for field, label in fields:
        ax.plot(x, [float(row[field]) for row in rows], marker="o", label=label)
    ax.set_xticks(x, [str(row["case_id"]) for row in rows], rotation=20)
    ax.set_ylabel(ylabel)
    ax.set_title(f"Domain Convergence - {kind.title()}")
    ax.legend(frameon=False, ncol=2)
    ax.grid(alpha=0.2)
    return _save(fig, path)


def chi_convergence(path: Path, rows: Sequence[Mapping[str, Any]], title: str) -> Path:
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    ax.plot(x, [float(r["chi2_1550_pm_per_V"]) for r in rows], marker="o")
    ax.set_xticks(x, [str(r["case_id"]) for r in rows], rotation=20)
    ax.set_ylabel(r"$|\chi^{(2)}(1550)|$ (pm/V)")
    ax.set_title(title)
    ax.grid(alpha=0.2)
    return _save(fig, path)


def k_saturation(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    fig, ax = plt.subplots(figsize=(6.7, 4.4))
    ax.plot([r["kmax_per_nm"] for r in rows], [r["chi2_1550_pm_per_V"] for r in rows], marker="o")
    ax.set_xlabel(r"$k_{max}$ (nm$^{-1}$)")
    ax.set_ylabel(r"$|\chi^{(2)}(1550)|$ (pm/V)")
    ax.set_title("k-Space Saturation")
    ax.grid(alpha=0.2)
    return _save(fig, path)


def term_magnitudes(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    top = list(rows[:16])
    labels = [f"{r['path'][0]} m{r['m_hh_state']}n{r['n_electron_state']}l{r['l_partner_state']}" for r in top]
    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    ax.bar(np.arange(len(top)), [r["contribution_pm_per_V_magnitude"] for r in top])
    ax.set_xticks(np.arange(len(top)), labels, rotation=60, ha="right")
    ax.set_ylabel("Contribution magnitude (pm/V)")
    ax.set_title("Eq. 2 Term Magnitudes")
    return _save(fig, path)


def electron_hh(path: Path, cross: Mapping[str, Any]) -> Path:
    values = [abs(complex(cross["electron_contribution"])), abs(complex(cross["heavy_hole_contribution"])),
              abs(complex(cross["independent_chi2"]))]
    fig, ax = plt.subplots(figsize=(6.2, 4.3))
    ax.bar(["electron", "heavy hole", "net"], values, color=["#4776a8", "#c45a42", "#555555"])
    ax.set_ylabel("Magnitude (pm/V)")
    ax.set_title("Electron and Heavy-Hole Contributions")
    ax.grid(axis="y", alpha=0.2)
    return _save(fig, path)


def final_spectrum(path: Path, analysis: Mapping[str, Any]) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.plot(analysis["wavelength_nm"], np.abs(analysis["chi2"]), lw=1.6)
    ax.axvline(1550, color="0.35", ls="--", lw=1)
    ax.set_xlabel("Fundamental wavelength (nm)")
    ax.set_ylabel(r"$|\chi^{(2)}|$ (pm/V)")
    ax.set_title("Best Reproduction Spectrum")
    ax.grid(alpha=0.2)
    return _save(fig, path)


def comparison(path: Path, best: float, paper: float) -> Path:
    values = [30.994195587364835, 84.13778453632841, float(best), float(paper)]
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    ax.bar(["Demo 18\nbaseline", "Demo 18\nadjusted", "Demo 18B\nbest", "paper\ntarget"], values)
    ax.set_ylabel(r"$|\chi^{(2)}(1550)|$ (pm/V)")
    ax.set_title("Absolute Chi2 Comparison")
    ax.grid(axis="y", alpha=0.2)
    return _save(fig, path)


def generate_all(
    root: Path, best: Mapping[str, Any], domain_rows: Sequence[Mapping[str, Any]],
    mesh_rows: Sequence[Mapping[str, Any]], k_rows: Sequence[Mapping[str, Any]],
    terms: Sequence[Mapping[str, Any]], cross: Mapping[str, Any], paper_target: float,
) -> list[Path]:
    root = Path(root)
    paths = [
        _state_plot(root / "01_electron_wavefunctions.png", best, "electron", False),
        _state_plot(root / "02_hh_wavefunctions.png", best, "heavy_hole", False),
        _state_plot(root / "03_electron_probabilities.png", best, "electron", True),
        _state_plot(root / "04_hh_probabilities.png", best, "heavy_hole", True),
        localization(root / "05_state_localization.png", best["localization"]),
        convergence(root / "06_domain_energies.png", domain_rows, "energies"),
        convergence(root / "07_domain_matrices.png", domain_rows, "matrices"),
        chi_convergence(root / "08_domain_chi2.png", domain_rows, "Domain Convergence - Chi2"),
        chi_convergence(root / "09_mesh_chi2.png", mesh_rows, "Mesh Convergence - Chi2"),
        k_saturation(root / "10_k_saturation.png", k_rows),
        term_magnitudes(root / "11_eq2_terms.png", terms),
        electron_hh(root / "12_electron_vs_hh.png", cross),
        final_spectrum(root / "13_final_spectrum.png", best),
        comparison(root / "14_demo18_demo18b_paper.png", best["row"]["chi2_1550_pm_per_V"], paper_target),
    ]
    return paths
