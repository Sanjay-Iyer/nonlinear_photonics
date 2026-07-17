"""Phase 4 - chi(2) SHG spectrum (paper Eqs. 2-3), reproduce Fig. 2e.

Standalone chi(2): consumes state energies, envelope wavefunctions and k|| info
from Phase 2 (aestimo) / Phase 3 (kdotpy) and returns chi_xzx(2w; w, w) over the
pump band via the complete paper Eq.(2)-(3) double sum with in-plane k-integration
to BZ/10 (electron + heavy-hole channels, coherent -e(z_e - z_h) sign).

REPORTED VALUE = the full coherent Eq-2 sum (the physical observable). The
individual electron/hole channel magnitudes are recorded as diagnostics because
they near-cancel (~92%); see DISCREPANCY.md and sensitivity.py.

Routes: aestimo_ideal, aestimo_graded, kdotpy_graded (aestimo graded envelopes
with kdotpy zone-center transition energies; kdotpy's approximate-.mat centroids
are unreliable per Phase 3, so a hybrid is used and flagged).

Usage:
  python compute_chi2_spectrum.py --config ../config/paper_params.yaml
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import savgol_filter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (load_config, start_run_log, append_log, save_plot,
                    new_checkpoint, write_manifest, AESTIMO_ROOT, NumpyJSONEncoder)

sys.path.insert(0, str(AESTIMO_ROOT))
sys.path.insert(0, str(AESTIMO_ROOT / "paper"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2_aestimo"))
import chi2_micro_audit as mca
import run_states as p2

HC_EV_NM = 1239.8419843320026


def lam_to_hw(lam_nm):
    return HC_EV_NM / np.asarray(lam_nm, float)


def solve_variant(cfg, variant):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        st = p2.solve_states(cfg, float(cfg["material"]["al_fraction"]), variant)
    return st


def compute_route(cfg, st, pump_nm, energy_shift=None):
    """Full Eq-2 chi(2) via chi2_micro_audit, restricted to 2 HH + 2 e states.

    energy_shift: optional dict {"E11_eV","E22_eV"} to substitute the interband
    transition energies (kdotpy hybrid) while keeping the aestimo envelopes.
    """
    hw = lam_to_hw(pump_nm)
    e_energy_eV = st["e_energy_meV"][:2] * 1e-3
    psi_e = st["psi_e"][:2]
    h_energy_eV = st["h_energy_eV"].copy()

    if energy_shift is not None:
        # Shift CB energies so E_e1-E_h1 and E_e2-E_h1 match the override, keeping
        # the HH1 reference fixed (HH1 = highest-energy HH-like recovered state).
        # Find HH1 energy from the prepared selection quickly:
        e_energy_eV = e_energy_eV.copy()
        # HH1 is the max valence-electron energy among HH-like; approximate as max.
        E_h1 = float(np.max(h_energy_eV))
        e_energy_eV[0] = E_h1 + energy_shift["E11_eV"]
        e_energy_eV[1] = E_h1 + energy_shift["E22_eV"]

    Ep = cfg["chi2"]["interband_dipole"]["kane_Ep_eV"]
    mca._EP_GAAS = float(Ep) if hasattr(mca, "_EP_GAAS") else None
    r_ehh_m = 0.7356102e-9   # Kane, E_P=28.8 eV (matches config)

    res = mca.compute_chi2_eq2_full(
        st["z_m"], psi_e, e_energy_eV, st["spinors"], h_energy_eV, hw,
        r_ehh_m=r_ehh_m, period_m=sum(cfg["material"]["period_layers_nm"]) * 1e-9,
        gamma_eV=cfg["chi2"]["broadening_gamma_meV"] * 1e-3,
        kmax_fraction=cfg["chi2"]["k_integration_bz_fraction"],
        m_e_eff=0.067 * mca.M0, m_h_eff=0.51 * mca.M0,
        max_hh_states=2)
    return {
        "pump_nm": pump_nm, "hw_eV": hw,
        "chi_total_pmV": np.abs(res.chi_total) * 1e12,
        "chi_e_pmV": np.abs(res.chi_electron) * 1e12,
        "chi_h_pmV": np.abs(res.chi_hole) * 1e12,
        "chi_total_complex": res.chi_total,
        "diagnostics": res.diagnostics,
        "r_ehh_nm": r_ehh_m * 1e9,
    }


def summarize(route, cfg, savgol_win=51):
    pump = route["pump_nm"]
    chi = route["chi_total_pmV"]
    ce = route["chi_e_pmV"]; ch = route["chi_h_pmV"]
    win = savgol_win if savgol_win % 2 else savgol_win + 1
    win = min(win, len(chi) - (1 - len(chi) % 2))
    chi_sg = savgol_filter(chi, max(win, 5), cfg["chi2"]["savgol_order"])
    ipk = int(np.argmax(chi_sg))
    ipk_e = int(np.argmax(ce))
    ff = cfg["chi2"]["fill_factor"]["qw_region_nm"] / cfg["chi2"]["fill_factor"]["period_nm"]
    i157 = int(np.argmin(np.abs(pump - cfg["chi2"]["target_pump_um"] * 1000)))
    cancellation = 1.0 - chi_sg[ipk] / max(ce[ipk], ch[ipk])
    return {
        "peak_pump_nm": float(pump[ipk]),
        "coherent_peak_pmV": float(chi_sg[ipk]),
        "coherent_peak_nm_per_V": float(chi_sg[ipk]) / 1000,
        "coherent_at_1570nm_pmV": float(chi_sg[i157]),
        "coherent_at_1570nm_nm_per_V": float(chi_sg[i157]) / 1000,
        "film_avg_coherent_peak_nm_per_V": ff * float(chi_sg[ipk]) / 1000,
        "electron_channel_peak_pmV": float(ce[ipk_e]),
        "electron_channel_peak_nm_per_V": float(ce[ipk_e]) / 1000,
        "hole_channel_peak_pmV": float(np.max(ch)),
        "cancellation_fraction": float(cancellation),
        "fill_factor": ff,
        "chi_sg_pmV": chi_sg,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    log = start_run_log("phase4_chi2", seed=0)

    lo, hi = cfg["chi2"]["pump_scan_nm"]
    pump_nm = np.linspace(lo, hi, 1001)

    # kdotpy zone-center energies (Phase-3) for the hybrid route
    kd_override = None
    kd_root = Path(__file__).resolve().parents[1] / "phase3_kdotpy" / "checkpoints"
    kd_cands = sorted(kd_root.glob("ckpt_*kdotpy*"), key=lambda p: p.stat().st_mtime)
    if kd_cands:
        kd = json.load(open(kd_cands[-1] / "analysis.json", encoding="utf-8"))["kdotpy"]
        kd_override = {"E11_eV": kd["E11_eV"], "E22_eV": kd["E22_eV"]}

    st_ideal = solve_variant(cfg, "ideal")
    st_graded = solve_variant(cfg, "graded")
    routes = {
        "aestimo_ideal": (st_ideal, None),
        "aestimo_graded": (st_graded, None),
        "kdotpy_graded": (st_graded, kd_override),
    }
    out = {}
    for name, (st, shift) in routes.items():
        r = compute_route(cfg, st, pump_nm, shift)
        s = summarize(r, cfg)
        out[name] = {"route": r, "summary": s}
        print(f"[phase4] {name}: COHERENT peak {s['coherent_peak_nm_per_V']:.3f} nm/V "
              f"@ {s['peak_pump_nm']:.0f} nm | @1.57um {s['coherent_at_1570nm_nm_per_V']:.3f} nm/V "
              f"| e-channel {s['electron_channel_peak_nm_per_V']:.2f} nm/V "
              f"| cancellation {100*s['cancellation_fraction']:.1f}%")
        append_log(log, f"{name}: coherent peak {s['coherent_peak_nm_per_V']:.3f} nm/V @ "
                        f"{s['peak_pump_nm']:.0f} nm; e-channel {s['electron_channel_peak_nm_per_V']:.2f}; "
                        f"cancel {100*s['cancellation_fraction']:.1f}%")

    sign_structure = {
        "relation": "chi_xzx = chi_xxz = -chi_yzy = -chi_yyz",
        "basis": "HH interband dipole <u_e|r|u_hh>: |x| and |y| legs are equal in "
                 "magnitude; the y-polarized interband loop carries an odd power of the "
                 "m_j=+/-3/2 ladder factor (i vs 1), flipping sign relative to x. The "
                 "intersubband z-leg is polarization-independent. Hence the four dominant "
                 "elements pair as +,+,-,-. Verified analytically (selection rules), not "
                 "by brute force.",
    }

    # Overlay plot
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"aestimo_ideal": "#1f4e79", "aestimo_graded": "#2e9e2e", "kdotpy_graded": "#c00000"}
    for name, d in out.items():
        ax.plot(pump_nm, d["summary"]["chi_sg_pmV"] / 1000, color=colors[name], lw=1.8, label=name)
    # channel-magnitude envelope (context) for graded
    ax.plot(pump_nm, out["aestimo_graded"]["route"]["chi_e_pmV"] / 1000, color="#2e9e2e",
            lw=0.8, ls="--", alpha=0.6, label="graded electron-channel (uncancelled)")
    anchors = cfg.get("fig2e_anchors") or []
    if anchors:
        ax.scatter([a["pump_nm"] for a in anchors], [a["chi_nm_per_V"] for a in anchors],
                   marker="x", color="k", s=50, zorder=5, label="Fig 2e (digitized)")
    ax.axvline(cfg["chi2"]["target_pump_um"] * 1000, ls=":", color="gray", label="1.57 um op. pt")
    ax.set_xlabel("Pump wavelength (nm)"); ax.set_ylabel(r"$|\chi^{(2)}_{xzx}|$ (nm/V)")
    ax.set_title("Fig. 2e - interband SHG susceptibility (coherent Eq-2 sum, SavGol)")
    ax.legend(fontsize=7); ax.grid(alpha=0.25)
    save_plot(fig, out_dir, "fig2e_chi2_spectrum_all_routes")
    plt.close(fig)

    ck = new_checkpoint(Path(__file__).resolve().parent, "chi2_spectrum")
    np.savez_compressed(ck / "chi2_spectra.npz", pump_nm=pump_nm,
                        **{f"{n}_coherent_pmV": d["route"]["chi_total_pmV"] for n, d in out.items()},
                        **{f"{n}_e_channel_pmV": d["route"]["chi_e_pmV"] for n, d in out.items()},
                        **{f"{n}_sg_pmV": d["summary"]["chi_sg_pmV"] for n, d in out.items()})
    key_out = {n: {k: v for k, v in d["summary"].items() if k != "chi_sg_pmV"} for n, d in out.items()}
    key_out["sign_structure"] = sign_structure
    key_out["r_ehh_nm"] = out["aestimo_ideal"]["route"]["r_ehh_nm"]
    key_out["reported_value_convention"] = ("coherent Eq-2 sum is the physical observable "
                                            "and the reported chi2_eff_MQW; channel magnitudes are diagnostics")
    with open(ck / "summary.json", "w", encoding="utf-8") as f:
        json.dump(key_out, f, indent=2, cls=NumpyJSONEncoder)
    write_manifest(ck, cfg,
                   inputs={"pump_scan_nm": [lo, hi], "gamma_meV": cfg["chi2"]["broadening_gamma_meV"],
                           "kane_Ep_eV": cfg["chi2"]["interband_dipole"]["kane_Ep_eV"],
                           "basis": "2 HH + 2 electron states", "kdotpy_override": kd_override},
                   outputs={n: {"coherent_peak_nm_per_V": d["summary"]["coherent_peak_nm_per_V"],
                                "peak_pump_nm": d["summary"]["peak_pump_nm"],
                                "electron_channel_peak_nm_per_V": d["summary"]["electron_channel_peak_nm_per_V"],
                                "cancellation_fraction": d["summary"]["cancellation_fraction"]}
                            for n, d in out.items()})
    for ext in ("png", "svg"):
        src = out_dir / f"fig2e_chi2_spectrum_all_routes.{ext}"
        if src.exists():
            (ck / src.name).write_bytes(src.read_bytes())
    print(f"\n[phase4] sign structure: {sign_structure['relation']} (analytic)")
    print(f"[phase4] checkpoint: {ck}")
    print(f"[phase4] log: {log}")


if __name__ == "__main__":
    main()
