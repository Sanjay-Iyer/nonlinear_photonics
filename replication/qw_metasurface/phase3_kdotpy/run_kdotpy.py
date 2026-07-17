"""Phase 3 - kdotpy 8-band k.p cross-check of the ACQW electronic structure.

Independent multiband check of the Phase-2 aestimo states at the SAME calibrated
Al fraction (x=0.55, no recalibration). Computes E(k_parallel) dispersions out to
~1/10 BZ, zone-center energies / centroids / HH-LH character, and compares
against the Phase-2 aestimo checkpoint.

Reuses the prior session's validated kdotpy backend (git/aestimo/paper) but drives
it with cpu=1 to avoid the multiprocessing pool (which fails under the sandbox),
and reads the calibrated Al fraction from paper_params.yaml.

Usage:
  python run_kdotpy.py --config ../config/paper_params.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (load_config, start_run_log, append_log, save_plot,
                    new_checkpoint, write_manifest, AESTIMO_ROOT, NumpyJSONEncoder)

sys.path.insert(0, str(AESTIMO_ROOT))
sys.path.insert(0, str(AESTIMO_ROOT / "paper"))
import kdotpy_acqw_backend as be  # noqa: E402

HC_EV_NM = 1239.8419843320026


def kdotpy_acqw(cfg, kmax_nm_inv, k_points, zres_nm=0.1):
    """Run kdotpy 2d for holes+electrons at the calibrated x; return states + dispersion.

    A local reimplementation of backend.run_kdotpy_acqw_baseline that (a) reads the
    Al fraction from config and (b) injects `cpu 1`.
    """
    x = float(cfg["material"]["al_fraction"])
    tb, d1, cb, d2 = cfg["material"]["period_layers_nm"]
    spec = be.build_acqw_spec_for_kdotpy(outer_barrier_nm=tb)
    spec["al_fraction"] = x
    spec["layers_nm"] = [tb, d1, cb, d2, tb]
    base = be._common_2d_args(spec) + ["cpu", "1"]

    import tempfile
    all_states, finite_k = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        krange = ["k", "0", str(kmax_nm_inv), "/", str(max(k_points, 2))]
        for tag, target, erange in (("h", "-10", ("-200", "30")),
                                    ("e", "1480", ("1430", "1800"))):
            run = be._run_kdotpy_2d(
                base + ["zres", str(zres_nm), "split", "0.01", *krange,
                        "neig", "12", "targetenergy", target, "erange", *erange,
                        "obs", "z", "out", f"acqw_{tag}"], work)
            disp = work / f"dispersionacqw_{tag}.csv"
            if run["rc"] not in (0, None) or not disp.exists():
                raise be.UnsupportedKdotpyFeature(
                    f"kdotpy ACQW {tag} solve failed (rc={run['rc']}). Log tail:\n{run['log'][-800:]}")
            parsed = be._parse_dispersion_csv(disp)
            all_states += be._classify_k0_states(parsed["records"])
            finite_k[tag] = parsed["records"]
    electrons, holes = be._split_states(all_states)
    return {"electrons": electrons, "holes": holes, "finite_k": finite_k,
            "al_fraction": x, "kmax_nm_inv": kmax_nm_inv,
            "a_lattice_nm": spec["a_lattice_nm"]}


def analyze_kdotpy(res):
    """Extract E11, E22, centroids, HH/LH labels from kdotpy states."""
    e = res["electrons"]      # sorted ascending in energy
    h = res["holes"]          # sorted descending (highest valence-electron first)
    hh = [s for s in h if s["label"] == "HH"]
    e_eV = [s["E_meV"] * 1e-3 for s in e]
    E11 = e_eV[0] - hh[0]["E_meV"] * 1e-3 if len(hh) >= 1 else None
    E22 = e_eV[1] - hh[1]["E_meV"] * 1e-3 if len(hh) >= 2 and len(e) >= 2 else None
    out = {
        "E11_eV": E11, "E22_eV": E22,
        "CB1_eV": e_eV[0], "CB2_eV": e_eV[1] if len(e) >= 2 else None,
        "CB1_centroid_nm": e[0]["z_nm"], "CB2_centroid_nm": e[1]["z_nm"] if len(e) >= 2 else None,
        "HH1_eV": hh[0]["E_meV"] * 1e-3 if hh else None,
        "HH2_eV": hh[1]["E_meV"] * 1e-3 if len(hh) >= 2 else None,
        "HH1_centroid_nm": hh[0]["z_nm"] if hh else None,
        "HH2_centroid_nm": hh[1]["z_nm"] if len(hh) >= 2 else None,
        "n_HH": len(hh),
        "hole_labels": [s["label"] for s in h[:6]],
    }
    if out["CB2_centroid_nm"] is not None and out["HH2_centroid_nm"] is not None:
        out["delta_z_HH2_CB2_nm"] = out["CB2_centroid_nm"] - out["HH2_centroid_nm"]
    return out


def load_aestimo(cfg):
    """Load Phase-2 ideal-variant analysis for comparison (latest x=0.55 checkpoint)."""
    ck_root = Path(__file__).resolve().parents[1] / "phase2_aestimo" / "checkpoints"
    cands = sorted(ck_root.glob("ckpt_*x0p550*"), key=lambda p: p.stat().st_mtime)
    if not cands:
        return None
    d = json.load(open(cands[-1] / "analysis.json", encoding="utf-8"))
    return d["variants"]["ideal"], str(cands[-1])


def plot_dispersion(res, out_dir):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, tag, title in ((axes[0], "e", "Conduction subbands"),
                           (axes[1], "h", "Valence subbands")):
        recs = res["finite_k"][tag]
        ks = sorted({r["k_nm_inv"] for r in recs})
        # group by nearest band via energy ordering at each k
        by_k = {k: sorted([r for r in recs if abs(r["k_nm_inv"] - k) < 1e-9],
                          key=lambda r: r["E_meV"]) for k in ks}
        nb = min(len(v) for v in by_k.values())
        for b in range(nb):
            E = [by_k[k][b]["E_meV"] for k in ks]
            ax.plot(ks, E, "-o", ms=3, lw=1)
        ax.set_xlabel("k$_\\parallel$ (nm$^{-1}$)")
        ax.set_ylabel("E (meV)")
        ax.set_title(title)
        ax.grid(alpha=0.25)
    fig.suptitle(f"kdotpy 8-band ACQW dispersion (x={res['al_fraction']:.2f})")
    save_plot(fig, out_dir, "fig_kdotpy_dispersion")
    plt.close(fig)


def plot_ladder(kd, aes, out_dir):
    """Side-by-side energy-level ladder: aestimo vs kdotpy."""
    fig, ax = plt.subplots(figsize=(6, 5))
    levels = [("E11", aes["E11_eV"], kd["E11_eV"]),
              ("E22", aes["E22_eV"], kd["E22_eV"])]
    for i, (name, a, k) in enumerate(levels):
        ax.hlines(a, 0.1, 0.9, color="#1f4e79", lw=2)
        ax.hlines(k, 1.1, 1.9, color="#c00000", lw=2)
        ax.text(0.5, a, f"{name}={a:.4f}", ha="center", va="bottom", fontsize=9, color="#1f4e79")
        ax.text(1.5, k, f"{name}={k:.4f}", ha="center", va="bottom", fontsize=9, color="#c00000")
        ax.plot([0.9, 1.1], [a, k], "k:", lw=0.8)
    ax.set_xticks([0.5, 1.5]); ax.set_xticklabels(["aestimo\n3x3", "kdotpy\n8-band"])
    ax.set_ylabel("Interband transition energy (eV)")
    ax.set_title("HH->CB transition ladder")
    save_plot(fig, out_dir, "fig_energy_ladder_aestimo_vs_kdotpy")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--kmax", type=float, default=None, help="k_par max (nm^-1); default = BZ/10")
    ap.add_argument("--kpoints", type=int, default=8)
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    log = start_run_log("phase3_kdotpy", seed=0)

    # BZ/10 in nm^-1: k_BZ = 2 pi / a; a in nm
    a_nm = be.ACQW_A_LATTICE_NM
    kmax = args.kmax if args.kmax is not None else 0.1 * (2 * np.pi / a_nm)
    append_log(log, f"a={a_nm} nm, kmax(BZ/10)={kmax:.4f} nm^-1, kpoints={args.kpoints}")

    info = be.check_kdotpy_available()
    print(f"[phase3] kdotpy {info.get('version')} available={info['available']}")
    res = kdotpy_acqw(cfg, kmax, args.kpoints)
    kd = analyze_kdotpy(res)
    print(f"[phase3] kdotpy E11={kd['E11_eV']:.4f} eV  E22={kd['E22_eV']:.4f} eV")
    print(f"[phase3] kdotpy hole labels: {kd['hole_labels']}")
    print(f"[phase3] kdotpy Delta_z(HH2,CB2)={kd.get('delta_z_HH2_CB2_nm')}")

    aes_pair = load_aestimo(cfg)
    comparison = None
    if aes_pair:
        aes, aes_ck = aes_pair
        dE11 = (kd["E11_eV"] - aes["E11_eV"]) * 1e3
        dE22 = (kd["E22_eV"] - aes["E22_eV"]) * 1e3
        comparison = {
            "aestimo_checkpoint": aes_ck,
            "aestimo_E11_eV": aes["E11_eV"], "kdotpy_E11_eV": kd["E11_eV"], "dE11_meV": dE11,
            "aestimo_E22_eV": aes["E22_eV"], "kdotpy_E22_eV": kd["E22_eV"], "dE22_meV": dE22,
            "aestimo_dz22_nm": aes["delta_z_HH2_CB2_nm"],
            "kdotpy_dz22_nm": kd.get("delta_z_HH2_CB2_nm"),
            "gate_E22_within_30meV": bool(abs(dE22) <= 30.0),
            "gate_E11_within_30meV": bool(abs(dE11) <= 30.0),
        }
        print(f"\n[phase3] aestimo vs kdotpy:")
        print(f"  E11: {aes['E11_eV']:.4f} vs {kd['E11_eV']:.4f}  (dE = {dE11:+.1f} meV)")
        print(f"  E22: {aes['E22_eV']:.4f} vs {kd['E22_eV']:.4f}  (dE = {dE22:+.1f} meV)")
        print(f"  GATE E22 within 30 meV: {comparison['gate_E22_within_30meV']}")
        append_log(log, f"dE11={dE11:.1f} meV dE22={dE22:.1f} meV")

    plot_dispersion(res, out_dir)
    if comparison:
        plot_ladder(kd, aes, out_dir)

    ck = new_checkpoint(Path(__file__).resolve().parent, f"kdotpy_x{res['al_fraction']:.2f}".replace(".", "p"))
    # save dispersion arrays
    np.savez_compressed(ck / "kdotpy_states.npz",
                        e_energies_eV=np.array([s["E_meV"] * 1e-3 for s in res["electrons"]]),
                        h_energies_eV=np.array([s["E_meV"] * 1e-3 for s in res["holes"]]),
                        e_centroids_nm=np.array([s["z_nm"] for s in res["electrons"]]),
                        h_centroids_nm=np.array([s["z_nm"] for s in res["holes"]]))
    with open(ck / "analysis.json", "w", encoding="utf-8") as f:
        json.dump({"kdotpy": kd, "comparison": comparison,
                   "electrons": res["electrons"][:4], "holes": res["holes"][:6]},
                  f, indent=2, cls=NumpyJSONEncoder)
    write_manifest(ck, cfg,
                   inputs={"al_fraction": res["al_fraction"], "kmax_nm_inv": kmax,
                           "k_points": args.kpoints, "model": "kdotpy 8o axial"},
                   outputs={"E11_eV": kd["E11_eV"], "E22_eV": kd["E22_eV"],
                            "comparison": comparison})
    for ext in ("png", "svg"):
        for stem in ("fig_kdotpy_dispersion", "fig_energy_ladder_aestimo_vs_kdotpy"):
            src = out_dir / f"{stem}.{ext}"
            if src.exists():
                (ck / src.name).write_bytes(src.read_bytes())
    print(f"\n[phase3] checkpoint: {ck}")
    print(f"[phase3] log: {log}")


if __name__ == "__main__":
    main()
