"""Phase 1 - Structure definition and material parameters.

Builds the single-period GaAs/AlGaAs coupled-quantum-well layer stack and its
conduction/valence band-edge profile in the growth direction z, for two variants:
  - ideal : abrupt square wells
  - graded: linearly graded interfaces (Ref38 EDS: ~linear over ~1 nm)

Band edges are computed from the aestimo material database so they are consistent
with the Phase 2 solver. Outputs the position-vs-Al-fraction and band-edge
profiles (npz + csv) and a plot mirroring the paper's Fig. 2a band diagram.

Usage:
  python build_structure.py --config ../config/paper_params.yaml --variant both
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (load_config, start_run_log, append_log, save_plot,
                    AESTIMO_ROOT, NumpyJSONEncoder)

sys.path.insert(0, str(AESTIMO_ROOT))
import database as db  # noqa: E402


# ----------------------------------------------------------------------------
# Material physics (AlGaAs band edges), taken from the aestimo database so that
# Phase 1 and Phase 2 share one parameter set.
# ----------------------------------------------------------------------------
def algaas_bandedges(x, cbo_fraction):
    """Return (E_c, E_v) in eV vs Al fraction x, GaAs valence edge = 0.

    Eg(x) interpolated with bowing; the bandgap increase splits into a
    conduction-band offset (cbo_fraction) above GaAs and a valence-band offset
    (1 - cbo_fraction) below GaAs.
    """
    eg_gaas = db.materialproperty["GaAs"]["Eg"]
    eg_alas = db.materialproperty["AlAs"]["Eg"]
    bow = db.alloyproperty["AlGaAs"]["Bowing_param"]
    x = np.asarray(x, dtype=float)
    eg = (1.0 - x) * eg_gaas + x * eg_alas - x * (1.0 - x) * bow
    d_eg = eg - eg_gaas
    e_c = eg_gaas + cbo_fraction * d_eg          # GaAs CB edge = Eg_GaAs
    e_v = -(1.0 - cbo_fraction) * d_eg           # GaAs VB edge = 0
    return e_c, e_v


# ----------------------------------------------------------------------------
# Geometry: Al-fraction profile x(z) for a single period.
# ----------------------------------------------------------------------------
def build_profile(cfg, variant, grading_nm=None, grid_nm=0.02,
                  outer_barrier_nm=None):
    """Return dict with z (nm), al_fraction x(z), E_c, E_v, and region markers.

    Layer order (growth direction, left->right): outer barrier / wide well /
    coupling barrier / narrow well / outer barrier. Wide well is on the LEFT,
    narrow well on the RIGHT (matches Fig. 2a; HH2->CB2 electron displacement to
    the right).
    """
    tb, d1, cb, d2 = cfg["material"]["period_layers_nm"]   # 18.2, 7.1, 1.8, 2.9
    x_bar = cfg["material"]["al_fraction"]
    if x_bar is None:
        x_bar = cfg["material"]["al_fraction_ref38"]       # 0.55 until calibrated
    cbo = cfg["solver"]["band_offsets"]["cbo_fraction"]
    outer = outer_barrier_nm if outer_barrier_nm is not None else tb

    if grading_nm is None:
        grading_nm = cfg["structure_variants"][variant]["grading_width_nm"]

    # Interface positions (z of each boundary), starting the wide well after the
    # left outer barrier.
    z0 = outer                       # start of wide well
    z1 = z0 + d1                     # wide -> coupling barrier
    z2 = z1 + cb                     # coupling barrier -> narrow well
    z3 = z2 + d2                     # narrow well -> right outer barrier
    total = z3 + outer
    z = np.arange(0.0, total + grid_nm, grid_nm)

    # Abrupt Al fraction: barrier=x_bar in outer+coupling regions, 0 in wells.
    def abrupt_x(zz):
        in_wide = (zz >= z0) & (zz < z1)
        in_narrow = (zz >= z2) & (zz < z3)
        return np.where(in_wide | in_narrow, 0.0, x_bar)

    xa = abrupt_x(z)

    if grading_nm > 0:
        # Convolve abrupt profile with a moving-average window of grading width
        # -> linear ramps across each interface (piecewise-linear, Ref38 EDS).
        w = max(1, int(round(grading_nm / grid_nm)))
        if w % 2 == 0:
            w += 1
        kernel = np.ones(w) / w
        # reflect-pad so the outer barriers keep their full height
        pad = w // 2
        xp = np.pad(xa, pad, mode="edge")
        xg = np.convolve(xp, kernel, mode="valid")
        x_of_z = xg
    else:
        x_of_z = xa

    e_c, e_v = algaas_bandedges(x_of_z, cbo)
    return {
        "variant": variant,
        "grading_nm": float(grading_nm),
        "al_fraction_barrier": float(x_bar),
        "grid_nm": float(grid_nm),
        "z_nm": z,
        "x_of_z": x_of_z,
        "E_c_eV": e_c,
        "E_v_eV": e_v,
        "regions_nm": {
            "left_barrier": (0.0, z0),
            "wide_well": (z0, z1),
            "coupling_barrier": (z1, z2),
            "narrow_well": (z2, z3),
            "right_barrier": (z3, total),
        },
        "layer_widths_nm": {"outer": outer, "d1": d1, "cb": cb, "d2": d2},
    }


def plot_bandedges(profiles, out_dir, cfg):
    """Fig. 2a-style band diagram: E_c and E_v vs z for the given variants."""
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    colors = {"ideal": ("#1f4e79", "#c00000"), "graded": ("#2e75b6", "#e08080")}
    for prof in profiles:
        v = prof["variant"]
        cc, cv = colors.get(v, ("k", "gray"))
        ls = "-" if v == "ideal" else "--"
        ax.plot(prof["z_nm"], prof["E_c_eV"], color=cc, ls=ls, lw=1.8,
                label=f"$E_c$ ({v})")
        ax.plot(prof["z_nm"], prof["E_v_eV"], color=cv, ls=ls, lw=1.8,
                label=f"$E_v$ ({v})")
    # Shade wells using the ideal profile regions
    r = profiles[0]["regions_nm"]
    for key, col in (("wide_well", "#fff2cc"), ("narrow_well", "#ffe0b0")):
        lo, hi = r[key]
        ax.axvspan(lo, hi, color=col, alpha=0.6, zorder=0)
    ax.annotate("wide well\n(7.1 nm)", xy=(np.mean(r["wide_well"]), 1.55),
                ha="center", fontsize=9)
    ax.annotate("narrow well\n(2.9 nm)", xy=(np.mean(r["narrow_well"]), 1.55),
                ha="center", fontsize=9)
    x_bar = profiles[0]["al_fraction_barrier"]
    ax.set_xlabel("Growth direction z (nm)")
    ax.set_ylabel("Energy (eV)")
    ax.set_title(f"Fig. 2a band-edge diagram — GaAs/Al$_{{{x_bar:.2f}}}$Ga$_{{{1-x_bar:.2f}}}$As ACQW")
    ax.legend(fontsize=8, ncol=2, loc="center right")
    ax.grid(alpha=0.25)
    save_plot(fig, out_dir, "fig2a_bandedges")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--variant", choices=["ideal", "graded", "both"], default="both")
    ap.add_argument("--grading-nm", type=float, default=None,
                    help="override graded-variant grading width (nm)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(__file__).resolve().parent
    log = start_run_log("phase1_structure", seed=0,
                        extra={"variant": args.variant})

    variants = ["ideal", "graded"] if args.variant == "both" else [args.variant]
    profiles = []
    for v in variants:
        g = args.grading_nm if (v == "graded" and args.grading_nm is not None) else None
        prof = build_profile(cfg, v, grading_nm=g)
        profiles.append(prof)
        # Save arrays
        np.savez(out_dir / f"structure_{v}.npz",
                 z_nm=prof["z_nm"], x_of_z=prof["x_of_z"],
                 E_c_eV=prof["E_c_eV"], E_v_eV=prof["E_v_eV"])
        # Save a coarse CSV for human inspection
        import csv
        with open(out_dir / f"structure_{v}.csv", "w", newline="", encoding="utf-8") as f:
            wcsv = csv.writer(f)
            wcsv.writerow(["z_nm", "al_fraction", "E_c_eV", "E_v_eV"])
            step = max(1, len(prof["z_nm"]) // 600)
            for i in range(0, len(prof["z_nm"]), step):
                wcsv.writerow([f"{prof['z_nm'][i]:.3f}", f"{prof['x_of_z'][i]:.4f}",
                               f"{prof['E_c_eV'][i]:.5f}", f"{prof['E_v_eV'][i]:.5f}"])
        append_log(log, f"variant={v}: grading={prof['grading_nm']} nm, "
                        f"x_barrier={prof['al_fraction_barrier']}, "
                        f"E_c_barrier={prof['E_c_eV'].max():.4f} eV, "
                        f"E_v_barrier={prof['E_v_eV'].min():.4f} eV, "
                        f"total z={prof['z_nm'][-1]:.1f} nm")

    plot_bandedges(profiles, out_dir, cfg)
    append_log(log, "wrote fig2a_bandedges.png/.svg")

    # Print a short summary
    p0 = profiles[0]
    eg_well = p0["E_c_eV"][np.argmin(np.abs(p0["z_nm"] - np.mean(p0["regions_nm"]["wide_well"])))]
    print(f"[phase1] variants: {variants}")
    print(f"[phase1] barrier Al fraction (pre-calibration): {p0['al_fraction_barrier']}")
    print(f"[phase1] GaAs well CB edge = {eg_well:.4f} eV, barrier CB edge = {p0['E_c_eV'].max():.4f} eV")
    print(f"[phase1] conduction band offset = {p0['E_c_eV'].max()-eg_well:.4f} eV")
    print(f"[phase1] valence band offset    = {0.0 - p0['E_v_eV'].min():.4f} eV")
    print(f"[phase1] log: {log}")


if __name__ == "__main__":
    main()
