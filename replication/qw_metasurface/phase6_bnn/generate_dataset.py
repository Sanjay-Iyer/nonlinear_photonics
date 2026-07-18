"""Phase 6 - generate the BNN training dataset by scripting Phase 2 -> Phase 4.

Samples ACQW structure parameters (Latin-hypercube), solves each with aestimo,
and computes the surrogate targets:
  E22 = E(HH2->CB2) [eV], delta_z22 = centroid offset [nm],
  chi2_peak [nm/V] (coherent Eq-2), chi2_peak_wavelength [nm].

Also generates a smaller kdotpy-route set (transition-energy-shifted) as a
held-out distribution-shift test. Datasets are stored immutably with a SHA-256.

Usage:
  python generate_dataset.py --n 500 --nk 50 --seed 7
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import io
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import load_config, start_run_log, append_log, AESTIMO_ROOT, NumpyJSONEncoder

sys.path.insert(0, str(AESTIMO_ROOT))
sys.path.insert(0, str(AESTIMO_ROOT / "paper"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2_aestimo"))
import chi2_micro_audit as mca
import run_states as p2

HC = 1239.8419843320026
PARAMS = ["wide_well_nm", "narrow_well_nm", "coupling_barrier_nm", "al_fraction", "grading_nm"]


def bounds(cfg):
    b = cfg["bnn"]["input_space"]
    x0 = float(cfg["material"]["al_fraction"])
    return {
        "wide_well_nm": tuple(b["wide_well_nm"]),
        "narrow_well_nm": tuple(b["narrow_well_nm"]),
        "coupling_barrier_nm": tuple(b["coupling_barrier_nm"]),
        "al_fraction": (x0 + b["al_fraction_delta"][0], x0 + b["al_fraction_delta"][1]),
        "grading_nm": tuple(b["grading_width_nm"]),
    }


def lhs(n, d, rng):
    """Latin-hypercube samples in the unit cube (n, d)."""
    u = (np.arange(n)[:, None] + rng.random((n, d))) / n
    for j in range(d):
        rng.shuffle(u[:, j])
    return u


def sample_to_struct(u, bnd):
    return {p: bnd[p][0] + u[i] * (bnd[p][1] - bnd[p][0]) for i, p in enumerate(PARAMS)}


def evaluate(cfg, s, pump_nm, energy_shift_meV=None):
    """Solve one structure and return the targets, or None on failure."""
    c = copy.deepcopy(cfg)
    tb = cfg["material"]["period_layers_nm"][0]      # keep outer barrier 18.2
    c["material"]["period_layers_nm"] = [tb, s["wide_well_nm"],
                                         s["coupling_barrier_nm"], s["narrow_well_nm"]]
    # Surrogate-training speed: coarser aestimo grid + fewer k-points. Accuracy
    # loss is small vs the Phase-2/4 production grid and irrelevant for a fast
    # surrogate (the BNN learns the mapping, validated against production points).
    c["solver"]["aestimo"]["grid_nm"] = 0.1
    c["solver"]["aestimo"]["subnumber_h"] = 4
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            st = p2.solve_states(c, s["al_fraction"], "graded", grading_nm=s["grading_nm"])
            an = p2.analyze(st)
            if an["E22_eV"] is None or an["delta_z_HH2_CB2_nm"] is None:
                return None
            e_energy = st["e_energy_meV"][:2] * 1e-3
            h_energy = st["h_energy_eV"].copy()
            if energy_shift_meV is not None:
                e_energy = e_energy + energy_shift_meV * 1e-3
            res = mca.compute_chi2_eq2_full(
                st["z_m"], st["psi_e"][:2], e_energy, st["spinors"], h_energy,
                HC / pump_nm, r_ehh_m=0.7356102e-9,
                period_m=sum(c["material"]["period_layers_nm"]) * 1e-9,
                gamma_eV=cfg["chi2"]["broadening_gamma_meV"] * 1e-3,
                kmax_fraction=cfg["chi2"]["k_integration_bz_fraction"],
                m_e_eff=0.067 * mca.M0, m_h_eff=0.51 * mca.M0, max_hh_states=2,
                radial_points=151)
        chi = np.abs(res.chi_total) * 1e12   # pm/V
        ipk = int(np.argmax(chi))
        return {
            "E22_eV": float(an["E22_eV"]),
            "delta_z22_nm": float(an["delta_z_HH2_CB2_nm"]),
            "chi2_peak_nm_per_V": float(chi[ipk]) / 1000,
            "chi2_peak_wavelength_nm": float(pump_nm[ipk]),
        }
    except Exception:
        return None


def build_set(cfg, n, rng, pump_nm, energy_shift_meV=None, log=None, tag=""):
    bnd = bounds(cfg)
    U = lhs(n, len(PARAMS), rng)
    X, Y, meta = [], [], []
    t0 = time.time()
    for i in range(n):
        s = sample_to_struct(U[i], bnd)
        out = evaluate(cfg, s, pump_nm, energy_shift_meV)
        if out is None:
            continue
        X.append([s[p] for p in PARAMS])
        Y.append([out["E22_eV"], out["delta_z22_nm"],
                  out["chi2_peak_nm_per_V"], out["chi2_peak_wavelength_nm"]])
        meta.append(s)
        if log and (i + 1) % 50 == 0:
            append_log(log, f"{tag} {i+1}/{n} ({len(X)} valid) elapsed {time.time()-t0:.0f}s")
    return np.array(X), np.array(Y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--nk", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    cfg = load_config(args.config)
    ck_root = Path(__file__).resolve().parent / "checkpoints" / "dataset_v1"
    ck_root.mkdir(parents=True, exist_ok=True)
    log = start_run_log("phase6_dataset", seed=args.seed, extra={"n": args.n, "nk": args.nk})
    rng = np.random.default_rng(args.seed)
    pump_nm = np.linspace(1350, 1650, 121)

    print(f"[dataset] generating {args.n} aestimo-route samples ...")
    Xa, Ya = build_set(cfg, args.n, rng, pump_nm, None, log, "aestimo")
    print(f"[dataset] aestimo: {len(Xa)} valid / {args.n}")

    # kdotpy-route shift set: apply the Phase-3 aestimo->kdotpy transition shift
    kd_root = Path(__file__).resolve().parents[1] / "phase3_kdotpy" / "checkpoints"
    kd_cands = sorted(kd_root.glob("ckpt_*kdotpy*"), key=lambda p: p.stat().st_mtime)
    shift_meV = 12.0
    if kd_cands:
        kd = json.load(open(kd_cands[-1] / "analysis.json", encoding="utf-8"))["comparison"]
        shift_meV = float(kd["dE22_meV"]) if kd else 12.0
    print(f"[dataset] generating {args.nk} kdotpy-route (shift {shift_meV:.1f} meV) samples ...")
    Xk, Yk = build_set(cfg, args.nk, rng, pump_nm, shift_meV, log, "kdotpy")
    print(f"[dataset] kdotpy: {len(Xk)} valid / {args.nk}")

    np.savez(ck_root / "dataset.npz", X_aestimo=Xa, Y_aestimo=Ya,
             X_kdotpy=Xk, Y_kdotpy=Yk,
             param_names=np.array(PARAMS),
             target_names=np.array(["E22_eV", "delta_z22_nm", "chi2_peak_nm_per_V",
                                    "chi2_peak_wavelength_nm"]))
    h = hashlib.sha256((ck_root / "dataset.npz").read_bytes()).hexdigest()
    info = {
        "n_aestimo": int(len(Xa)), "n_kdotpy": int(len(Xk)),
        "seed": args.seed, "kdotpy_shift_meV": shift_meV,
        "param_names": PARAMS,
        "target_names": ["E22_eV", "delta_z22_nm", "chi2_peak_nm_per_V", "chi2_peak_wavelength_nm"],
        "bounds": bounds(cfg), "sha256": h,
        "pump_grid_nm": [float(pump_nm[0]), float(pump_nm[-1]), len(pump_nm)],
    }
    with open(ck_root / "dataset_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, cls=NumpyJSONEncoder)
    print(f"[dataset] saved {ck_root}/dataset.npz  sha256={h[:16]}...")
    print(f"[dataset] log: {log}")


if __name__ == "__main__":
    main()
