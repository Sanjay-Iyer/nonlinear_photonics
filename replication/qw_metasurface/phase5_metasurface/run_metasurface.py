"""Phase 5 - Metasurface GMR simulation with grcwa (reproduce Fig. 3).

Unit cell (incidence from air on top):
  air / TiO2 nanopillar array (h=390, r=230 nm) / MQW film (595 nm, homogeneous
  effective index) / Al2O3 substrate. Rectangular lattice 891 x 650 nm. p-pol
  (x-polarized) input. Same RCWA package (GRCWA) as the paper.

Deliverables:
  - transmission T(lambda, angle) map -> identify GMRs A/B/C, angle splitting
  - modal overlap beta(lambda, angle) ~ |int_MQW Ex,w Ez,w Ex,2w* d3x|  (Eq. 1)
  - resonance B at 0.3 deg: wavelength, linewidth -> Q
  - field-enhancement factors vs 45 deg / normal bare film
  - combined chi2_eff,MQW+MS = enhancement * chi2_eff,MQW (Phase 4 honest value)

Units: nm; grcwa freq = 1/lambda (c=1).

Usage:
  python run_metasurface.py --config ../config/paper_params.yaml --mode transmission
  python run_metasurface.py --mode full
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import grcwa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

grcwa.set_backend("numpy")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (load_config, start_run_log, append_log, save_plot,
                    new_checkpoint, write_manifest, NumpyJSONEncoder)

DEG = np.pi / 180.0


def indices(cfg):
    ms = cfg["metasurface"]
    return {
        "air": 1.0,
        "tio2_1550": ms["tio2_index_est"]["n_1550"],
        "tio2_780": ms["tio2_index_est"]["n_780"],
        "mqw_1550": ms["mqw_index_1550nm_est"],
        "mqw_780": complex(ms["mqw_index_780nm"][0], ms["mqw_index_780nm"][1]),
        "al2o3_1550": ms["al2o3_index_est"]["n_1550"],
        "al2o3_780": ms["al2o3_index_est"]["n_780"],
    }


def pillar_eps_grid(cfg, n_bg, n_pillar, Nx=120, Ny=90):
    Lx = cfg["metasurface"]["period_nm"]["x"]
    Ly = cfg["metasurface"]["period_nm"]["y"]
    r = cfg["metasurface"]["pillar"]["radius_nm"]
    x = (np.arange(Nx) + 0.5) / Nx * Lx
    y = (np.arange(Ny) + 0.5) / Ny * Ly
    X, Y = np.meshgrid(x, y, indexing="ij")
    cyl = ((X - Lx / 2) ** 2 + (Y - Ly / 2) ** 2) <= r ** 2
    ep = np.ones((Nx, Ny), complex) * n_bg ** 2
    ep[cyl] = n_pillar ** 2
    return ep


def build(cfg, lam_nm, theta_deg, phi_deg, nG, n_mqw, n_tio2, n_al2o3,
          Nx=120, Ny=90):
    Lx = cfg["metasurface"]["period_nm"]["x"]
    Ly = cfg["metasurface"]["period_nm"]["y"]
    h_p = cfg["metasurface"]["pillar"]["height_nm"]
    h_m = cfg["material"]["film_thickness_nm"]
    obj = grcwa.obj(nG, [Lx, 0.0], [0.0, Ly], 1.0 / lam_nm,
                    theta_deg * DEG, phi_deg * DEG, verbose=0)
    obj.Add_LayerUniform(100.0, 1.0)                 # air (incident, semi-inf)
    obj.Add_LayerGrid(h_p, Nx, Ny)                   # TiO2 pillars
    obj.Add_LayerUniform(h_m, n_mqw ** 2)            # MQW film
    obj.Add_LayerUniform(100.0, n_al2o3 ** 2)        # Al2O3 substrate (exit)
    obj.Init_Setup()
    obj.GridLayer_geteps(pillar_eps_grid(cfg, 1.0, n_tio2, Nx, Ny).flatten())
    obj.MakeExcitationPlanewave(1.0, 0.0, 0.0, 0.0, order=0, direction="forward")
    return obj


def transmission(cfg, lam_nm, theta_deg, phi_deg, nG, n_mqw, n_tio2, n_al2o3):
    obj = build(cfg, lam_nm, theta_deg, phi_deg, nG, n_mqw, n_tio2, n_al2o3)
    R, T = obj.RT_Solve(normalize=1)
    return float(np.real(T))


# ---------------------------------------------------------------------------
# Field extraction (MQW as a uniform-eps grid layer so Solve_FieldOnGrid works)
# ---------------------------------------------------------------------------
def build_fieldable(cfg, lam_nm, theta_deg, phi_deg, nG, n_mqw, n_tio2, n_al2o3,
                    with_pillars=True, Nx=100, Ny=74):
    """Return (obj, mqw_layer_index). MQW is a grid layer (uniform eps) so fields
    can be extracted; optionally omit the TiO2 pillars for the bare-film reference."""
    Lx = cfg["metasurface"]["period_nm"]["x"]
    Ly = cfg["metasurface"]["period_nm"]["y"]
    h_p = cfg["metasurface"]["pillar"]["height_nm"]
    h_m = cfg["material"]["film_thickness_nm"]
    obj = grcwa.obj(nG, [Lx, 0.0], [0.0, Ly], 1.0 / lam_nm,
                    theta_deg * DEG, phi_deg * DEG, verbose=0)
    obj.Add_LayerUniform(100.0, 1.0)                  # air
    if with_pillars:
        obj.Add_LayerGrid(h_p, Nx, Ny)                # pillars (layer 1)
        mqw_layer = 2
    else:
        mqw_layer = 1
    obj.Add_LayerGrid(h_m, Nx, Ny)                    # MQW grid (uniform eps)
    obj.Add_LayerUniform(100.0, n_al2o3 ** 2)         # substrate
    obj.Init_Setup()
    if with_pillars:
        obj.GridLayer_geteps(np.concatenate([
            pillar_eps_grid(cfg, 1.0, n_tio2, Nx, Ny).flatten(),
            (np.ones((Nx, Ny), complex) * n_mqw ** 2).flatten()]))
    else:
        obj.GridLayer_geteps((np.ones((Nx, Ny), complex) * n_mqw ** 2).flatten())
    obj.MakeExcitationPlanewave(1.0, 0.0, 0.0, 0.0, order=0, direction="forward")
    return obj, mqw_layer


def mqw_fields(obj, mqw_layer, nz=9):
    """Sample E-fields across the MQW layer; return Ex,Ey,Ez arrays (nz,Nx,Ny)."""
    h = obj.thickness_list[mqw_layer]
    zs = np.linspace(0.08 * h, 0.92 * h, nz)
    Ex, Ey, Ez = [], [], []
    for zo in zs:
        e, _ = obj.Solve_FieldOnGrid(mqw_layer, float(zo))
        Ex.append(np.asarray(e[0])); Ey.append(np.asarray(e[1])); Ez.append(np.asarray(e[2]))
    return np.array(Ex), np.array(Ey), np.array(Ez)


def field_products(obj, mqw_layer, nz=9):
    """Volume-averaged |Ex||Ez| and |Ex|^2 in the MQW (relative to unit incidence)."""
    Ex, Ey, Ez = mqw_fields(obj, mqw_layer, nz)
    pxz = float(np.mean(np.abs(Ex) * np.abs(Ez)))
    pxx = float(np.mean(np.abs(Ex) ** 2))
    return {"ExEz": pxz, "ExEx": pxx,
            "Ex_rms": float(np.sqrt(np.mean(np.abs(Ex) ** 2))),
            "Ez_rms": float(np.sqrt(np.mean(np.abs(Ez) ** 2)))}


def modal_overlap_beta(cfg, lam_nm, theta_deg, phi_deg, nG, idx, Nx=100, Ny=74, nz=9):
    """beta ~ |int_MQW Ex,w Ez,w Ex,2w* d3x| (Eq. 1), arb. units.

    Pump fields at lam (MQW index n_mqw_1550), SH field at lam/2 (n_mqw_780).
    """
    obj_w, mq_w = build_fieldable(cfg, lam_nm, theta_deg, phi_deg, nG,
                                  idx["mqw_1550"], idx["tio2_1550"], idx["al2o3_1550"],
                                  True, Nx, Ny)
    Exw, Eyw, Ezw = mqw_fields(obj_w, mq_w, nz)
    obj_2w, mq_2w = build_fieldable(cfg, lam_nm / 2, theta_deg, phi_deg, nG,
                                    idx["mqw_780"], idx["tio2_780"], idx["al2o3_780"],
                                    True, Nx, Ny)
    Ex2, Ey2, Ez2 = mqw_fields(obj_2w, mq_2w, nz)
    integrand = Exw * Ezw * np.conj(Ex2)
    beta = np.abs(np.sum(integrand))
    return float(beta)


def scan_transmission(cfg, lam_grid, angles, phi_deg, nG, n_mqw, n_tio2, n_al2o3, log=None):
    T = np.empty((len(angles), len(lam_grid)))
    for i, ang in enumerate(angles):
        for j, lam in enumerate(lam_grid):
            T[i, j] = transmission(cfg, lam, ang, phi_deg, nG, n_mqw, n_tio2, n_al2o3)
        if log:
            append_log(log, f"angle {ang:.2f} deg done (min T={T[i].min():.3f})")
    return T


def find_dips(lam_grid, Trow, min_depth=0.03):
    """Return list of (lambda, T) local minima deeper than min_depth below local baseline."""
    dips = []
    for j in range(1, len(Trow) - 1):
        if Trow[j] < Trow[j - 1] and Trow[j] < Trow[j + 1]:
            baseline = max(Trow[max(0, j - 8)], Trow[min(len(Trow) - 1, j + 8)])
            if baseline - Trow[j] >= min_depth:
                dips.append((float(lam_grid[j]), float(Trow[j])))
    return dips


def lorentzian_q(lam, T):
    """Fit the sharpest dip to a Lorentzian -> (lambda0, FWHM, Q)."""
    j = int(np.argmin(T))
    lam0 = lam[j]
    depth = np.median(T) - T[j]
    half = np.median(T) - depth / 2
    # find FWHM by crossing 'half' around the dip
    left = j
    while left > 0 and T[left] < half:
        left -= 1
    right = j
    while right < len(T) - 1 and T[right] < half:
        right += 1
    fwhm = lam[right] - lam[left]
    q = lam0 / fwhm if fwhm > 0 else np.inf
    return float(lam0), float(fwhm), float(q)


def run_full(cfg, args, log):
    out_dir = Path(__file__).resolve().parent / "results"
    idx = indices(cfg)
    n_mqw = args.n_mqw if args.n_mqw is not None else idx["mqw_1550"]
    n_tio2, n_al2o3 = idx["tio2_1550"], idx["al2o3_1550"]
    nG = args.nG
    tgt = cfg["metasurface"]["gmr_B"]

    # (1) Fine scan near resonance B at 0.3 deg -> Q
    lamB = np.arange(1560.0, 1600.0, 0.05)
    TB = np.array([transmission(cfg, l, tgt["angle_deg"], 0.0, nG, n_mqw, n_tio2, n_al2o3) for l in lamB])
    lam0, fwhm, Q = lorentzian_q(lamB, TB)
    print(f"[full] resonance B @ {tgt['angle_deg']} deg: lambda0={lam0:.2f} nm, "
          f"FWHM={fwhm:.3f} nm, Q={Q:.0f}")
    append_log(log, f"resonance B lambda0={lam0:.2f} FWHM={fwhm:.3f} Q={Q:.0f}")

    # (2) beta vs angle (Fig 3d): show vanishing at normal, peak at finite angle
    beta_angles = [0.0, 0.3, 1.0, 2.0, 4.0]
    beta_vals = {}
    for ang in beta_angles:
        b = modal_overlap_beta(cfg, lam0, ang, 0.0, nG, idx)
        beta_vals[ang] = b
        print(f"[full] beta({ang} deg, {lam0:.0f} nm) = {b:.4e}")
        append_log(log, f"beta({ang})={b:.4e}")

    # (3) field enhancement: metasurface (0.3 deg, resonance) vs bare film
    obj_ms, mq_ms = build_fieldable(cfg, lam0, tgt["angle_deg"], 0.0, nG,
                                    n_mqw, n_tio2, n_al2o3, with_pillars=True)
    fp_ms = field_products(obj_ms, mq_ms)
    obj_45, mq_45 = build_fieldable(cfg, lam0, 45.0, 0.0, nG, n_mqw, n_tio2, n_al2o3,
                                    with_pillars=False)
    fp_45 = field_products(obj_45, mq_45)
    obj_n, mq_n = build_fieldable(cfg, lam0, 0.0, 0.0, nG, n_mqw, n_tio2, n_al2o3,
                                  with_pillars=False)
    fp_n = field_products(obj_n, mq_n)
    enh_57 = fp_ms["ExEz"] / fp_45["ExEz"] if fp_45["ExEz"] > 0 else np.inf
    enh_115 = fp_ms["ExEz"] / fp_n["ExEx"] if fp_n["ExEx"] > 0 else np.inf
    print(f"[full] ExEz enhancement vs 45deg bare film = {enh_57:.1f}x (target 57)")
    print(f"[full] ExEz vs normal ExEx bare film       = {enh_115:.1f}x (target 11.5)")

    # (4) combined chi2 using Phase-4 honest coherent value
    p4 = load_phase4_chi2()
    chi2_mqw = p4["chi2_eff_MQW_nm_per_V"] if p4 else None
    chi2_ms = enh_115 * chi2_mqw if chi2_mqw is not None else None

    # Plots
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(lamB, TB, lw=1)
    ax.axvline(lam0, ls=":", color="r", label=f"B: {lam0:.1f} nm, Q={Q:.0f}")
    ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("T"); ax.legend()
    ax.set_title(f"Resonance B fine scan @ {tgt['angle_deg']} deg")
    save_plot(fig, out_dir, "fig4_resonanceB_Q")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(list(beta_vals.keys()), list(beta_vals.values()), "o-")
    ax.set_xlabel("Incidence angle (deg)"); ax.set_ylabel(r"$\beta$ (arb.)")
    ax.set_title("Fig. 3d - modal overlap vs angle (vanishes at normal)")
    save_plot(fig, out_dir, "fig3d_beta_vs_angle")
    plt.close(fig)

    ck = new_checkpoint(Path(__file__).resolve().parent, "full")
    result = {
        "n_mqw": n_mqw, "nG": nG,
        "resonance_B": {"lambda0_nm": lam0, "fwhm_nm": fwhm, "Q": Q,
                        "target_sim_nm": tgt["sim_nm"], "target_exp_nm": tgt["exp_nm"],
                        "target_Q_exp": tgt["q_factor_exp"]},
        "beta_vs_angle": beta_vals,
        "field_products": {"metasurface_0p3deg": fp_ms, "bare_45deg": fp_45, "bare_normal": fp_n},
        "enhancement_ExEz_vs_45deg": enh_57, "target_57": 57,
        "enhancement_ExEz_vs_normal_ExEx": enh_115, "target_11p5": 11.5,
        "chi2_eff_MQW_nm_per_V": chi2_mqw,
        "chi2_eff_MQW_plus_MS_nm_per_V": chi2_ms,
        "target_chi2_MQW_plus_MS_nm_per_V": cfg["metasurface"]["chi2_eff_MQW_plus_MS_nm_per_V"],
    }
    with open(ck / "full_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, cls=NumpyJSONEncoder)
    np.savez_compressed(ck / "resonanceB.npz", lam=lamB, T=TB)
    write_manifest(ck, cfg, inputs={"n_mqw": n_mqw, "nG": nG},
                   outputs={"Q": Q, "lambda0_nm": lam0, "enh_57": enh_57,
                            "enh_115": enh_115, "chi2_MS": chi2_ms})
    for ext in ("png", "svg"):
        for stem in ("fig4_resonanceB_Q", "fig3d_beta_vs_angle"):
            src = out_dir / f"{stem}.{ext}"
            if src.exists():
                (ck / src.name).write_bytes(src.read_bytes())
    print(f"\n[full] chi2_eff_MQW={chi2_mqw} nm/V -> chi2_eff_MQW+MS={chi2_ms} nm/V "
          f"(target {cfg['metasurface']['chi2_eff_MQW_plus_MS_nm_per_V']})")
    print(f"[full] checkpoint: {ck}")
    return result


def load_phase4_chi2():
    """Load the Phase-4 coherent chi2_eff_MQW (aestimo graded @ 1.57 um)."""
    root = Path(__file__).resolve().parents[1] / "phase4_chi2" / "checkpoints"
    cands = sorted(root.glob("ckpt_*chi2_spectrum*"), key=lambda p: p.stat().st_mtime)
    if not cands:
        return None
    s = json.load(open(cands[-1] / "summary.json", encoding="utf-8"))
    g = s.get("aestimo_graded", {})
    return {"chi2_eff_MQW_nm_per_V": g.get("coherent_at_1570nm_nm_per_V")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--mode", choices=["transmission", "full"], default="transmission")
    ap.add_argument("--nG", type=int, default=101)
    ap.add_argument("--n-mqw", type=float, default=None, help="override MQW index (calibration 3.2-3.4)")
    ap.add_argument("--nlam", type=int, default=241)
    args = ap.parse_args()

    if args.mode == "full":
        cfg = load_config(args.config)
        log = start_run_log("phase5_metasurface_full", seed=0, extra={"nG": args.nG})
        run_full(cfg, args, log)
        print(f"[phase5] log: {log}")
        return
    cfg = load_config(args.config)
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    log = start_run_log("phase5_metasurface", seed=0, extra={"mode": args.mode, "nG": args.nG})

    idx = indices(cfg)
    n_mqw = args.n_mqw if args.n_mqw is not None else idx["mqw_1550"]
    n_tio2 = idx["tio2_1550"]
    n_al2o3 = idx["al2o3_1550"]
    lo, hi = cfg["metasurface"]["scan"]["wavelength_nm"]
    lam_grid = np.linspace(lo, hi, args.nlam)
    angles = [0.0, 0.3, 1.0, 2.0, 4.0, 8.0]

    print(f"[phase5] transmission scan: n_mqw={n_mqw}, nG={args.nG}, "
          f"lam {lo}-{hi} nm ({args.nlam} pts), angles {angles} deg (y-tilt, phi=0)")
    T = scan_transmission(cfg, lam_grid, angles, 0.0, args.nG, n_mqw, n_tio2, n_al2o3, log)

    # identify resonances at each angle
    dip_report = {}
    for i, ang in enumerate(angles):
        dips = find_dips(lam_grid, T[i])
        dip_report[f"{ang:.2f}"] = dips
        print(f"  angle {ang:.2f} deg: dips at "
              + ", ".join(f"{l:.1f}nm(T={t:.2f})" for l, t in dips))

    # plot transmission map (Fig 3c)
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(T, aspect="auto", origin="lower", cmap="viridis",
                   extent=[lam_grid[0], lam_grid[-1], 0, len(angles) - 1])
    ax.set_yticks(range(len(angles))); ax.set_yticklabels([f"{a}" for a in angles])
    ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Incidence angle (deg)")
    ax.set_title(f"Fig. 3c - transmission (n_MQW={n_mqw:.2f}, y-tilt)")
    fig.colorbar(im, label="T")
    save_plot(fig, out_dir, "fig3c_transmission_map")
    plt.close(fig)

    # line plots at each angle
    fig, ax = plt.subplots(figsize=(8, 5))
    for i, ang in enumerate(angles):
        ax.plot(lam_grid, T[i] + i * 0.0, label=f"{ang} deg", lw=1)
    ax.set_xlabel("Wavelength (nm)"); ax.set_ylabel("Transmission")
    ax.set_title(f"Transmission vs angle (n_MQW={n_mqw:.2f})")
    ax.legend(fontsize=8); ax.grid(alpha=0.25)
    save_plot(fig, out_dir, "fig3c_transmission_lines")
    plt.close(fig)

    ck = new_checkpoint(Path(__file__).resolve().parent, f"transmission_nmqw{n_mqw:.2f}".replace(".", "p"))
    np.savez_compressed(ck / "transmission.npz", lam_grid=lam_grid, angles=np.array(angles), T=T)
    with open(ck / "dips.json", "w", encoding="utf-8") as f:
        json.dump({"n_mqw": n_mqw, "nG": args.nG, "dips_by_angle": dip_report}, f, indent=2, cls=NumpyJSONEncoder)
    write_manifest(ck, cfg, inputs={"n_mqw": n_mqw, "nG": args.nG, "angles_deg": angles,
                                    "lam_nm": [lo, hi], "nlam": args.nlam},
                   outputs={"dips_by_angle": dip_report})
    for ext in ("png", "svg"):
        for stem in ("fig3c_transmission_map", "fig3c_transmission_lines"):
            src = out_dir / f"{stem}.{ext}"
            if src.exists():
                (ck / src.name).write_bytes(src.read_bytes())
    print(f"\n[phase5] checkpoint: {ck}")
    print(f"[phase5] log: {log}")


if __name__ == "__main__":
    main()
