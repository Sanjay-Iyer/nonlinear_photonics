"""Phase 5 - pump-bandwidth-averaged (effective) field enhancement.

The raw on-resonance ExEz enhancement of a high-Q GMR is huge, but the paper's
57x / 11.5x are EFFECTIVE values: the 70 fs pump is ~100x spectrally broader than
the 0.55 nm GMR, so only the pump slice within the GMR is enhanced. This module
scans the metasurface ExEz product across the resonance, weights it by the pump
spectrum, and computes the pump-averaged enhancement for an apples-to-apples
comparison with the paper.

Usage:
  python effective_enhancement.py --config ../config/paper_params.yaml
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
                    new_checkpoint, write_manifest, NumpyJSONEncoder)
import run_metasurface as m

DEG = np.pi / 180.0


def pump_spectrum(lam_nm, center_nm=1560.0, pulse_fs=70.0):
    """Transform-limited Gaussian intensity spectrum of a 70 fs pulse."""
    c = 2.99792458e8
    dnu = 0.441 / (pulse_fs * 1e-15)                 # intensity FWHM in Hz
    dlam = (center_nm * 1e-9) ** 2 * dnu / c * 1e9   # FWHM in nm
    sigma = dlam / 2.3548
    return np.exp(-0.5 * ((lam_nm - center_nm) / sigma) ** 2), dlam


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--nG", type=int, default=101)
    ap.add_argument("--lam0", type=float, default=1574.1)
    args = ap.parse_args()
    cfg = load_config(args.config)
    out_dir = Path(__file__).resolve().parent / "results"
    log = start_run_log("phase5_effective_enh", seed=0)
    idx = m.indices(cfg)
    n_mqw, n_tio2, n_al2o3 = idx["mqw_1550"], idx["tio2_1550"], idx["al2o3_1550"]
    ang = cfg["metasurface"]["gmr_B"]["angle_deg"]

    # Scan the metasurface ExEz product across the resonance (fine near peak)
    lam = np.concatenate([np.arange(args.lam0 - 30, args.lam0 - 3, 1.0),
                          np.arange(args.lam0 - 3, args.lam0 + 3, 0.1),
                          np.arange(args.lam0 + 3, args.lam0 + 30, 1.0)])
    lam = np.unique(np.round(lam, 3))
    pxz_ms = np.empty(len(lam))
    for i, l in enumerate(lam):
        obj, mq = m.build_fieldable(cfg, float(l), ang, 0.0, args.nG, n_mqw, n_tio2, n_al2o3, True)
        pxz_ms[i] = m.field_products(obj, mq)["ExEz"]
    append_log(log, f"scanned {len(lam)} lambda for metasurface ExEz")

    # Bare-film references (weakly wavelength-dependent -> evaluate at lam0)
    obj45, mq45 = m.build_fieldable(cfg, args.lam0, 45.0, 0.0, args.nG, n_mqw, n_tio2, n_al2o3, False)
    pxz_45 = m.field_products(obj45, mq45)["ExEz"]
    objn, mqn = m.build_fieldable(cfg, args.lam0, 0.0, 0.0, args.nG, n_mqw, n_tio2, n_al2o3, False)
    pxx_n = m.field_products(objn, mqn)["ExEx"]

    enh_xz = pxz_ms / pxz_45          # vs 45 deg bare film (per lambda)
    enh_xx = pxz_ms / pxx_n           # vs normal bare film ExEx

    w, dlam = pump_spectrum(lam)
    w /= w.sum()
    eff_xz = float(np.sum(enh_xz * w))
    eff_xx = float(np.sum(enh_xx * w))
    peak_xz = float(enh_xz.max())
    peak_xx = float(enh_xx.max())

    print(f"[eff] pump intensity FWHM = {dlam:.1f} nm (70 fs); GMR FWHM ~0.55 nm -> ratio ~{dlam/0.55:.0f}x")
    print(f"[eff] ExEz vs 45deg : peak {peak_xz:.0f}x -> pump-averaged EFFECTIVE {eff_xz:.1f}x (target 57)")
    print(f"[eff] ExEz vs normal ExEx: peak {peak_xx:.0f}x -> EFFECTIVE {eff_xx:.1f}x (target 11.5)")
    append_log(log, f"effective enh: {eff_xz:.1f}x (t57), {eff_xx:.1f}x (t11.5)")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(lam, enh_xz, lw=1.5, label="ExEz enh vs 45deg (per-lambda)")
    ax2 = ax.twinx()
    ax2.plot(lam, w / w.max(), color="gray", ls="--", lw=1, label="pump spectrum")
    ax.axhline(eff_xz, color="r", ls=":", label=f"pump-avg effective {eff_xz:.0f}x")
    ax.axhline(57, color="g", ls="--", label="paper 57x")
    ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("ExEz enhancement")
    ax2.set_ylabel("pump intensity (norm)")
    ax.set_title("Effective (pump-bandwidth-averaged) field enhancement")
    ax.legend(fontsize=8, loc="upper left")
    save_plot(fig, out_dir, "fig_effective_enhancement")
    plt.close(fig)

    # combined chi2 with Phase-4 honest value
    p4 = m.load_phase4_chi2()
    chi2_mqw = p4["chi2_eff_MQW_nm_per_V"] if p4 else None
    chi2_ms_eff = eff_xx * chi2_mqw if chi2_mqw is not None else None

    ck = new_checkpoint(Path(__file__).resolve().parent, "effective_enhancement")
    res = {
        "lam0_nm": args.lam0, "angle_deg": ang,
        "pump_fwhm_nm": dlam, "gmr_fwhm_nm": 0.55,
        "peak_ExEz_vs_45deg": peak_xz, "effective_ExEz_vs_45deg": eff_xz, "target_57": 57,
        "peak_ExEz_vs_normal_ExEx": peak_xx, "effective_ExEz_vs_normal_ExEx": eff_xx, "target_11p5": 11.5,
        "chi2_eff_MQW_nm_per_V": chi2_mqw,
        "chi2_eff_MQW_plus_MS_effective_nm_per_V": chi2_ms_eff,
        "target_chi2_MQW_plus_MS": cfg["metasurface"]["chi2_eff_MQW_plus_MS_nm_per_V"],
        "note": ("Paper 57x/11.5x are effective (pump-bandwidth-averaged) values; peak "
                 "on-resonance enhancement is ~30x larger. Effective values computed by "
                 "weighting per-lambda enhancement with the 70 fs pump spectrum."),
    }
    with open(ck / "effective_enhancement.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, cls=NumpyJSONEncoder)
    np.savez_compressed(ck / "enh_scan.npz", lam=lam, enh_xz=enh_xz, enh_xx=enh_xx, pump_w=w)
    write_manifest(ck, cfg, inputs={"lam0_nm": args.lam0, "nG": args.nG},
                   outputs={"effective_ExEz_vs_45deg": eff_xz,
                            "effective_ExEz_vs_normal_ExEx": eff_xx,
                            "chi2_MS_effective": chi2_ms_eff})
    for ext in ("png", "svg"):
        src = out_dir / f"fig_effective_enhancement.{ext}"
        if src.exists():
            (ck / src.name).write_bytes(src.read_bytes())
    print(f"[eff] chi2_eff_MQW+MS (effective) = {chi2_ms_eff} nm/V (target 14)")
    print(f"[eff] checkpoint: {ck}")
    print(f"[eff] log: {log}")


if __name__ == "__main__":
    main()
