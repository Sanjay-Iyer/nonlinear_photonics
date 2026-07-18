"""Phase 6 - train the uncertainty-aware surrogate and run the analyses.

Surrogate: a heteroscedastic DEEP ENSEMBLE (Lakshminarayanan et al. 2017) - the
repo has no existing BNN, so this standard, well-calibrated Bayesian-approximation
is used. Each ensemble member is an MLP with a (mean, log-variance) head trained by
Gaussian NLL; the ensemble mixture gives predictive mean and total (epistemic +
aleatoric) variance. This is the "BNN" third model in the comparison.

Targets: E22_eV, delta_z22_nm, chi2_peak_nm_per_V, chi2_peak_wavelength_nm.

Analyses (plan Phase 6.4):
  - predict the paper nominal structure; compare mean +/- sigma to direct values
  - permutation sensitivity: which input most controls chi2 peak
  - uncertainty inflation on the kdotpy distribution-shift set
  - interface-grading sweep: how grading degrades chi2

Gate: val RMSE E22 < 10 meV, chi2 peak < 20%; calibration ~diagonal.

Usage:
  python train_bnn.py --config ../config/paper_params.yaml --epochs 400
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (load_config, start_run_log, append_log, save_plot,
                    new_checkpoint, write_manifest, NumpyJSONEncoder)

TARGETS = ["E22_eV", "delta_z22_nm", "chi2_peak_nm_per_V", "chi2_peak_wavelength_nm"]
PARAMS = ["wide_well_nm", "narrow_well_nm", "coupling_barrier_nm", "al_fraction", "grading_nm"]


class HetMLP(nn.Module):
    def __init__(self, d_in, d_out, hidden=64):
        super().__init__()
        self.body = nn.Sequential(
            nn.Linear(d_in, hidden), nn.SiLU(),
            nn.Linear(hidden, hidden), nn.SiLU())
        self.mean = nn.Linear(hidden, d_out)
        self.logvar = nn.Linear(hidden, d_out)

    def forward(self, x):
        h = self.body(x)
        return self.mean(h), torch.clamp(self.logvar(h), -8.0, 6.0)


def gauss_nll(mean, logvar, y):
    return (0.5 * (torch.exp(-logvar) * (y - mean) ** 2 + logvar)).mean()


def train_member(Xtr, Ytr, Xva, Yva, epochs, lr, seed, log=None, tag=""):
    torch.manual_seed(seed)
    net = HetMLP(Xtr.shape[1], Ytr.shape[1])
    opt = torch.optim.Adam(net.parameters(), lr=lr, weight_decay=1e-5)
    tr_curve, va_curve = [], []
    best = (1e9, None)
    for ep in range(epochs):
        net.train(); opt.zero_grad()
        m, lv = net(Xtr)
        loss = gauss_nll(m, lv, Ytr)
        loss.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            mv, lvv = net(Xva)
            vloss = gauss_nll(mv, lvv, Yva).item()
        tr_curve.append(loss.item()); va_curve.append(vloss)
        if vloss < best[0]:
            best = (vloss, {k: v.clone() for k, v in net.state_dict().items()})
        if log and (ep + 1) % 100 == 0:
            append_log(log, f"{tag} ep{ep+1} train {loss.item():.3f} val {vloss:.3f}")
    net.load_state_dict(best[1])
    return net, tr_curve, va_curve


def ensemble_predict(nets, X, y_mean, y_std):
    means, vars = [], []
    with torch.no_grad():
        for net in nets:
            m, lv = net(X)
            means.append(m.numpy()); vars.append(np.exp(lv.numpy()))
    means = np.array(means); vars = np.array(vars)
    mu = means.mean(0)
    # total predictive variance = mean(var) + var(mean)  (aleatoric + epistemic)
    var = vars.mean(0) + means.var(0)
    # de-standardize
    mu_o = mu * y_std + y_mean
    sd_o = np.sqrt(var) * y_std
    return mu_o, sd_o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--epochs", type=int, default=400)
    ap.add_argument("--members", type=int, default=5)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    cfg = load_config(args.config)
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    log = start_run_log("phase6_train", seed=args.seed, extra={"epochs": args.epochs})
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    ds = np.load(Path(__file__).resolve().parent / "checkpoints" / "dataset_v1" / "dataset.npz",
                 allow_pickle=True)
    X, Y = ds["X_aestimo"].astype(np.float64), ds["Y_aestimo"].astype(np.float64)
    Xk, Yk = ds["X_kdotpy"].astype(np.float64), ds["Y_kdotpy"].astype(np.float64)
    n = len(X)
    perm = rng.permutation(n)
    ntr = int(0.8 * n)
    tr, va = perm[:ntr], perm[ntr:]

    # standardize
    x_mean, x_std = X[tr].mean(0), X[tr].std(0) + 1e-9
    y_mean, y_std = Y[tr].mean(0), Y[tr].std(0) + 1e-9
    Xs = (X - x_mean) / x_std
    Ys = (Y - y_mean) / y_std
    Xk_s = (Xk - x_mean) / x_std

    def T(a): return torch.tensor(a, dtype=torch.float32)
    Xtr, Ytr = T(Xs[tr]), T(Ys[tr])
    Xva, Yva = T(Xs[va]), T(Ys[va])

    nets, curves = [], []
    for mi in range(args.members):
        net, trc, vac = train_member(Xtr, Ytr, Xva, Yva, args.epochs, args.lr,
                                     seed=100 + mi, log=log, tag=f"member{mi}")
        nets.append(net); curves.append((trc, vac))

    # Validation metrics
    mu_va, sd_va = ensemble_predict(nets, Xva, y_mean, y_std)
    y_va = Y[va]
    rmse = np.sqrt(np.mean((mu_va - y_va) ** 2, axis=0))
    # chi2 peak relative RMSE
    chi_idx = TARGETS.index("chi2_peak_nm_per_V")
    rel_chi = np.sqrt(np.mean(((mu_va[:, chi_idx] - y_va[:, chi_idx])
                               / (np.abs(y_va[:, chi_idx]) + 1e-3)) ** 2))
    e22_rmse_meV = rmse[TARGETS.index("E22_eV")] * 1000
    print(f"[bnn] val RMSE: E22={e22_rmse_meV:.2f} meV, dz22={rmse[1]:.3f} nm, "
          f"chi2peak={rmse[2]:.4f} nm/V (rel {100*rel_chi:.1f}%), lam={rmse[3]:.1f} nm")
    append_log(log, f"val RMSE E22={e22_rmse_meV:.2f} meV chi2 rel {100*rel_chi:.1f}%")

    gate_e22 = bool(e22_rmse_meV < 10.0)
    gate_chi = bool(rel_chi < 0.20)

    # Calibration / reliability: fraction within k-sigma
    z = (mu_va - y_va) / (sd_va + 1e-12)
    levels = [0.5, 1.0, 1.5, 2.0]
    calib = {f"{k}sigma": float(np.mean(np.abs(z) <= k)) for k in levels}
    expected = {0.5: 0.383, 1.0: 0.683, 1.5: 0.866, 2.0: 0.954}

    # kdotpy shift-set uncertainty inflation
    mu_k, sd_k = ensemble_predict(nets, T(Xk_s), y_mean, y_std)
    infl = float(np.mean(sd_k, 0)[chi_idx] / np.mean(sd_va, 0)[chi_idx])
    print(f"[bnn] kdotpy shift-set sigma inflation (chi2 peak): {infl:.2f}x")

    # Nominal-structure prediction
    x0 = float(cfg["material"]["al_fraction"])
    nominal = np.array([[7.1, 2.9, 1.8, x0, 1.0]])
    mu_nom, sd_nom = ensemble_predict(nets, T((nominal - x_mean) / x_std), y_mean, y_std)
    nom = {t: {"mean": float(mu_nom[0, i]), "sigma": float(sd_nom[0, i])}
           for i, t in enumerate(TARGETS)}
    print(f"[bnn] nominal: E22={nom['E22_eV']['mean']:.3f}+/-{nom['E22_eV']['sigma']:.3f} eV, "
          f"chi2peak={nom['chi2_peak_nm_per_V']['mean']:.3f}+/-{nom['chi2_peak_nm_per_V']['sigma']:.3f} nm/V")

    # Permutation sensitivity for chi2 peak
    base_pred = ensemble_predict(nets, Xva, y_mean, y_std)[0][:, chi_idx]
    base_err = np.mean((base_pred - y_va[:, chi_idx]) ** 2)
    sens = {}
    for j, p in enumerate(PARAMS):
        Xp = Xva.clone().numpy()
        Xp[:, j] = Xp[rng.permutation(len(Xp)), j]
        pred = ensemble_predict(nets, T(Xp), y_mean, y_std)[0][:, chi_idx]
        sens[p] = float(np.mean((pred - y_va[:, chi_idx]) ** 2) - base_err)
    order = sorted(sens, key=sens.get, reverse=True)
    print(f"[bnn] chi2-peak sensitivity (permutation importance): "
          + ", ".join(f"{p}={sens[p]:.4f}" for p in order))

    # Interface-grading sweep (fix nominal, vary grading)
    grd = np.linspace(0, 1, 21)
    Xg = np.tile(nominal, (len(grd), 1)); Xg[:, 4] = grd
    mu_g, sd_g = ensemble_predict(nets, T((Xg - x_mean) / x_std), y_mean, y_std)

    # ---- Plots ----
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i, (trc, vac) in enumerate(curves):
        ax.plot(vac, alpha=0.6, label=f"member {i} val")
    ax.set_xlabel("epoch"); ax.set_ylabel("Gaussian NLL (val)"); ax.legend(fontsize=7)
    ax.set_title("BNN ensemble training curves"); ax.set_yscale("symlog")
    save_plot(fig, out_dir, "fig_bnn_training_curves")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([expected[k] for k in levels], [calib[f"{k}sigma"] for k in levels], "o-", label="ensemble")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="ideal")
    ax.set_xlabel("expected coverage"); ax.set_ylabel("empirical coverage")
    ax.set_title("Reliability diagram"); ax.legend()
    save_plot(fig, out_dir, "fig_bnn_calibration")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for i, ti in enumerate([TARGETS.index("E22_eV"), chi_idx]):
        axes[i].errorbar(y_va[:, ti], mu_va[:, ti], yerr=sd_va[:, ti], fmt="o", ms=3, alpha=0.5)
        lim = [min(y_va[:, ti].min(), mu_va[:, ti].min()), max(y_va[:, ti].max(), mu_va[:, ti].max())]
        axes[i].plot(lim, lim, "k--")
        axes[i].set_xlabel(f"true {TARGETS[ti]}"); axes[i].set_ylabel("predicted")
    axes[0].set_title("E22 parity"); axes[1].set_title("chi2 peak parity")
    save_plot(fig, out_dir, "fig_bnn_parity")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(grd, mu_g[:, chi_idx], "-o", ms=3)
    ax.fill_between(grd, mu_g[:, chi_idx] - sd_g[:, chi_idx], mu_g[:, chi_idx] + sd_g[:, chi_idx], alpha=0.3)
    ax.set_xlabel("interface grading (nm)"); ax.set_ylabel("chi2 peak (nm/V)")
    ax.set_title("Interface-grading degradation of chi2 (nominal structure)")
    save_plot(fig, out_dir, "fig_bnn_grading_sweep")
    plt.close(fig)

    # ---- Checkpoint ----
    ck = new_checkpoint(Path(__file__).resolve().parent, "bnn_trained")
    for i, net in enumerate(nets):
        torch.save(net.state_dict(), ck / f"member_{i}.pt")
    np.savez(ck / "standardization.npz", x_mean=x_mean, x_std=x_std, y_mean=y_mean, y_std=y_std)
    result = {
        "val_rmse": {t: float(rmse[i]) for i, t in enumerate(TARGETS)},
        "val_rmse_E22_meV": e22_rmse_meV,
        "val_rel_rmse_chi2_peak": rel_chi,
        "gate_E22_lt_10meV": gate_e22,
        "gate_chi2_lt_20pct": gate_chi,
        "calibration_empirical": calib, "calibration_expected": expected,
        "kdotpy_sigma_inflation_chi2": infl,
        "nominal_prediction": nom,
        "chi2_peak_sensitivity": sens, "sensitivity_ranked": order,
        "grading_sweep": {"grading_nm": grd.tolist(),
                          "chi2_peak_nm_per_V": mu_g[:, chi_idx].tolist(),
                          "sigma": sd_g[:, chi_idx].tolist()},
        "n_train": int(ntr), "n_val": int(n - ntr), "members": args.members,
        "dataset_sha256": json.load(open(Path(__file__).resolve().parent / "checkpoints" /
                                         "dataset_v1" / "dataset_info.json"))["sha256"],
    }
    with open(ck / "bnn_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, cls=NumpyJSONEncoder)
    write_manifest(ck, cfg, inputs={"epochs": args.epochs, "members": args.members},
                   outputs={"val_rmse_E22_meV": e22_rmse_meV, "val_rel_chi2": rel_chi,
                            "gate_E22": gate_e22, "gate_chi2": gate_chi})
    for ext in ("png", "svg"):
        for stem in ("fig_bnn_training_curves", "fig_bnn_calibration", "fig_bnn_parity",
                     "fig_bnn_grading_sweep"):
            src = out_dir / f"{stem}.{ext}"
            if src.exists():
                (ck / src.name).write_bytes(src.read_bytes())
    print(f"[bnn] gates: E22<10meV={gate_e22}, chi2<20%={gate_chi}")
    print(f"[bnn] calibration: {calib} (expected {expected})")
    print(f"[bnn] checkpoint: {ck}")
    print(f"[bnn] log: {log}")


if __name__ == "__main__":
    main()
