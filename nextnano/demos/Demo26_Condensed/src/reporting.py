"""Observables, features, paper metrics, CSV and figures.

The complex susceptibility is the only input. Re, Im, |Re| and |chi| are derived
here, at the very end, and never substituted for one another.
"""
from __future__ import annotations

import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import brentq
from scipy.signal import find_peaks

HC_EV_NM = 1239.841984


def observables(chi: np.ndarray) -> dict[str, np.ndarray]:
    chi = np.asarray(chi, complex)
    return {"real": np.real(chi), "imag": np.imag(chi),
            "abs_real": np.abs(np.real(chi)), "abs": np.abs(chi)}


def _norm(y):
    scale = float(np.max(np.abs(y)))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("cannot normalize an all-zero or non-finite curve")
    return np.asarray(y) / scale


def features(wl, chi, evaluator=None) -> dict:
    ob = observables(chi)
    peak_mag = float(ob["abs"].max())
    crossings = []
    for i in np.flatnonzero(ob["real"][:-1] * ob["real"][1:] < 0):
        if evaluator is not None:
            root = brentq(lambda x: evaluator(np.array([x]))[0].real, wl[i], wl[i + 1], xtol=1e-10)
            value = complex(evaluator(np.array([root]))[0])
        else:
            root = wl[i] - ob["real"][i] * (wl[i + 1] - wl[i]) / (ob["real"][i + 1] - ob["real"][i])
            value = complex(0.0, np.interp(root, wl, ob["imag"]))
        crossings.append({"wavelength_nm": float(root), "real": float(value.real), "imag": float(value.imag),
                          "abs": float(abs(value)), "abs_over_max_abs": float(abs(value) / peak_mag),
                          "abs_imag_over_max_abs": float(abs(value.imag) / peak_mag)})
    pick = lambda y, sign, prom: [{"wavelength_nm": float(wl[i]), "value": float(y[i])}
                                  for i in find_peaks(sign * y, prominence=prom * float(np.max(np.abs(y))))[0]]
    return {"re_zero_crossings": crossings,
            "abs_real_peaks": pick(ob["abs_real"], 1, 0.02), "abs_real_minima": pick(ob["abs_real"], -1, 0.01),
            "abs_peaks": pick(ob["abs"], 1, 0.02), "abs_minima": pick(ob["abs"], -1, 0.005),
            "dominant_abs_real_peak_nm": float(wl[np.argmax(ob["abs_real"])]),
            "dominant_abs_peak_nm": float(wl[np.argmax(ob["abs"])]),
            "max_abs_real": float(ob["abs_real"].max()), "max_abs": peak_mag,
            "min_abs_over_max_abs": float(ob["abs"].min() / peak_mag),
            "min_abs_real_over_max_abs_real": float(ob["abs_real"].min() / ob["abs_real"].max()),
            "chi2_at_1550nm": ({"real": float(np.interp(1550, wl, ob["real"])),
                                "imag": float(np.interp(1550, wl, ob["imag"]))} if wl[0] <= 1550 <= wl[-1] else None)}


def paper_metrics(wl, chi, paper, min_correlation: float = 0.5) -> dict:
    """nRMSE and correlation of each normalized observable against the normalized paper curve.

    A shape comparison only means something if it beats the best flat line
    (nRMSE = standard deviation of the normalized paper curve) and correlates.
    """
    ref = _norm(np.interp(wl, paper[:, 0], paper[:, 1]))
    null = float(np.sqrt(np.mean((ref - ref.mean()) ** 2)))
    ob = observables(chi)
    out = {"null_best_constant": {"constant": float(ref.mean()), "nRMSE": null}}
    for name in ("real", "abs_real", "abs", "imag"):
        y = _norm(ob[name])
        n = float(np.sqrt(np.mean((y - ref) ** 2)))
        r = float(np.corrcoef(y, ref)[0, 1])
        out[name] = {"nRMSE": n, "correlation": r, "beats_null": n < null,
                     "informative": bool(n < null and r >= min_correlation)}
    return out


def check_reference(wl, chi, reference_path, tolerance, transform=None) -> dict:
    data = np.loadtxt(reference_path, delimiter=",", skiprows=1)
    if not np.array_equal(data[:, 0], wl):
        raise ValueError(f"wavelength grid of {Path(reference_path).name} differs")
    tested = chi if transform is None else transform(chi)
    error = float(np.max(np.abs(tested - (data[:, 1] + 1j * data[:, 2]))))
    return {"reference_file": Path(reference_path).name, "max_complex_error": error,
            "absolute_tolerance": tolerance, "status": "PASS" if error <= tolerance else "FAIL"}


def write_csv(out: Path, wl, chi, paper, units: str) -> None:
    ob = observables(chi)
    ref = np.interp(wl, paper[:, 0], paper[:, 1])
    tag = units.replace("/", "_per_")
    cols = {"wavelength_nm": wl, "photon_energy_eV": HC_EV_NM / wl,
            f"chi2_real_{tag}": ob["real"], f"chi2_imag_{tag}": ob["imag"],
            f"chi2_abs_real_{tag}": ob["abs_real"], f"chi2_abs_{tag}": ob["abs"],
            "abs_real_normalized_to_own_max": _norm(ob["abs_real"]), "abs_normalized_to_own_max": _norm(ob["abs"]),
            "paper_fig2d_normalized_to_own_max": _norm(ref)}
    np.savetxt(out / "chi2_spectrum.csv", np.column_stack(list(cols.values())), delimiter=",",
               header=",".join(cols), comments="", fmt="%.10g")


def write_pathways(out: Path, wl, terms, labels) -> None:
    with (out / "pathways.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wavelength_nm", "pathway", "real", "imag"])
        for label, term in zip(labels, terms):
            w.writerows(zip(wl, [label] * len(wl), np.real(term), np.imag(term)))


def _axes(ylabel, wl):
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.set_xlabel("fundamental wavelength (nm)", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xlim(wl[0], wl[-1])
    ax.spines[["top", "right"]].set_visible(False)
    return fig, ax


def _save(fig, ax, path, loc="upper left"):
    ax.legend(fontsize=9.5, loc=loc, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plots(out: Path, wl, chi, paper, feats, units="pm/V", scan=None) -> list[str]:
    out = Path(out)
    ob = observables(chi)
    zx = np.array([c["wavelength_nm"] for c in feats["re_zero_crossings"]])
    zi = np.array([c["imag"] for c in feats["re_zero_crossings"]])
    pn = _norm(paper[:, 1])
    lab = {"re": r"$\mathrm{Re}\,\chi^{(2)}$", "im": r"$\mathrm{Im}\,\chi^{(2)}$",
           "absre": r"$|\mathrm{Re}\,\chi^{(2)}|$", "abs": r"$|\chi^{(2)}|$"}
    yabs, ynorm = rf"$\chi^{{(2)}}$ ({units})", r"$\chi^{(2)}$ normalized"
    made = []

    fig, ax = _axes(yabs, wl)
    ax.axhline(0, color="0.6", lw=0.9)
    ax.plot(wl, ob["real"], color="crimson", lw=2, label=lab["re"])
    if len(zx):
        ax.plot(zx, np.zeros_like(zx), "o", mfc="none", mec="black", ms=7, label=lab["re"] + " = 0")
    _save(fig, ax, out / "01_chi2_real.png", loc="best"); made.append("01_chi2_real.png")

    fig, ax = _axes(yabs, wl)
    ax.axhline(0, color="0.6", lw=0.9)
    ax.plot(wl, ob["imag"], color="steelblue", lw=2, label=lab["im"])
    if len(zx):
        ax.plot(zx, zi, "o", mfc="none", mec="black", ms=7, label=lab["im"] + " where " + lab["re"] + " = 0")
    _save(fig, ax, out / "02_chi2_imag.png", loc="best"); made.append("02_chi2_imag.png")

    fig, ax = _axes(ynorm, wl)
    ax.plot(paper[:, 0], pn, "ko--", ms=4, lw=1.3, label="paper Fig. 2d")
    ax.plot(wl, _norm(ob["abs_real"]), color="crimson", lw=2, label=lab["absre"])
    ax.set_ylim(0, 1.1)
    _save(fig, ax, out / "03_chi2_abs_real.png"); made.append("03_chi2_abs_real.png")

    fig, ax = _axes(yabs, wl)
    ax.plot(wl, ob["abs"], color="darkgreen", lw=2, label=lab["abs"])
    ax.plot(wl, ob["abs_real"], color="crimson", lw=1.6, ls="--", label=lab["absre"])
    ax.set_ylim(0, None)
    _save(fig, ax, out / "04_chi2_magnitude.png"); made.append("04_chi2_magnitude.png")

    fig, ax = _axes(ynorm, wl)
    ax.plot(paper[:, 0], pn, "ko--", ms=4, lw=1.3, label="paper Fig. 2d")
    ax.plot(wl, _norm(ob["abs_real"]), color="crimson", lw=2, label=lab["absre"])
    ax.plot(wl, _norm(ob["abs"]), color="darkgreen", lw=1.8, ls=":", label=lab["abs"])
    ax.set_ylim(0, 1.1)
    _save(fig, ax, out / "05_paper_vs_absreal_vs_magnitude.png"); made.append("05_paper_vs_absreal_vs_magnitude.png")

    fig, ax = _axes(yabs, wl)
    ax.plot(wl, ob["abs_real"], color="crimson", lw=2, label=lab["absre"] + " (left axis)")
    ax.plot(wl, ob["abs"], color="darkgreen", lw=1.8, ls=":", label=lab["abs"] + " (left axis)")
    ax.set_ylim(0, None)
    ax2 = ax.twinx()
    ax2.plot(paper[:, 0], paper[:, 1], "ko--", ms=4, lw=1.3, label="paper Fig. 2d (right axis)")
    ax2.set_ylabel(r"paper $\chi^{(2)}$ (pm/V)", fontsize=11)
    ax2.set_ylim(0, None)
    ax2.spines[["top"]].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=9.5, loc="upper left", frameon=False)
    fig.tight_layout(); fig.savefig(out / "05b_absreal_vs_magnitude_absolute.png", dpi=200); plt.close(fig)
    made.append("05b_absreal_vs_magnitude_absolute.png")

    fig, ax = _axes(yabs, wl)
    ax.axhline(0, color="0.6", lw=0.9)
    ax.plot(wl, ob["real"], color="crimson", lw=2, label=lab["re"])
    ax.plot(wl, ob["imag"], color="steelblue", lw=1.8, label=lab["im"])
    if len(zx):
        ax.plot(zx, np.zeros_like(zx), "o", mfc="none", mec="black", ms=7, label=lab["re"] + " = 0")
    _save(fig, ax, out / "06_real_and_imag.png", loc="best"); made.append("06_real_and_imag.png")

    if scan:
        fig, ax = _axes(ynorm, wl)
        ax.plot(paper[:, 0], pn, "ko--", ms=4, lw=1.3, label="paper Fig. 2d")
        colors = plt.cm.viridis(np.linspace(0.1, 0.85, len(scan)))
        for (label, curve), c in zip(scan, colors):
            ax.plot(wl, _norm(np.abs(np.real(curve))), color=c, lw=1.7, label=lab["absre"] + ", " + label)
        ax.set_ylim(0, 1.1)
        _save(fig, ax, out / "07_k_cutoff_dependence.png"); made.append("07_k_cutoff_dependence.png")
    return made
