"""DEVELOPER TOOL - builds validation/reference_demo26.json. Not needed to run the package.

Check categories
    reference                 value from a file that existed BEFORE Demo26_Condensed (historical saved
                              spectra and tables, the prior audit, Demo 21), or raw nextnano output
    independent_rederivation  recomputed here from raw nextnano files with code that shares nothing
                              with the package pipeline
    consistency               invariant that must hold for any dataset (limits only, no dataset values)

Where a saved table quotes a number, it is also recomputed here from the saved spectrum
and the two must agree. Reference and re-derivation checks apply only when the analysed
deck and config match the "conditions" block.

    python tools/build_reference.py --repo <repository root>
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
import numpy as np

PKG = Path(__file__).resolve().parents[1]
GAMMA_EV = 0.005


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rows(p: Path) -> list[dict]:
    with p.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def zero_crossings(wl, re_, im):
    out = []
    for i in np.flatnonzero(re_[:-1] * re_[1:] < 0):
        t = -re_[i] / (re_[i + 1] - re_[i])
        out.append((wl[i] + t * (wl[i + 1] - wl[i]), im[i] + t * (im[i + 1] - im[i])))
    return out


def nrmse(wl, y, paper):
    ref = np.interp(wl, paper[:, 0], paper[:, 1])
    y, ref = y / np.max(np.abs(y)), ref / ref.max()
    return float(np.sqrt(np.mean((y - ref) ** 2)))


def chk(id_, kind, value, source, category="reference", tol=None):
    out = {"id": id_, "kind": kind, "value": value, "source": source, "category": category}
    if tol is not None:
        out["tol"] = tol
    return out


def rederive_matrices(kp8_dir: Path, roles: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """|O|, |Ze|, |Zh| from raw envelopes: largest single block component, phase-fixed, Loewdin (no SVD)."""
    blocks = {"e": ("cb1", "cb2"), "h": ("hh1", "hh2")}
    env, z = {}, None
    for role, members in roles.items():
        best = None
        for s in members:
            for c in blocks[role[0]]:
                d = np.loadtxt(kp8_dir / f"envelope_k00000_{s:04d}_{c}.dat", skiprows=1)
                z = d[:, 0]
                v = d[:, 1] + 1j * d[:, 2]
                if best is None or np.sum(np.abs(v) ** 2) > np.sum(np.abs(best) ** 2):
                    best = v
        env[role] = best
    w = np.r_[(z[1] - z[0]) / 2, (z[2:] - z[:-2]) / 2, (z[-1] - z[-2]) / 2]
    for role, v in env.items():
        f = (v * np.exp(-1j * np.angle(np.sum(v * v * w)) / 2)).real
        env[role] = f / np.sqrt(np.sum(f * f * w))

    def orth(F):
        vals, vecs = np.linalg.eigh(F.T @ (F * w[:, None]))
        return F @ vecs @ np.diag(vals ** -0.5) @ vecs.T

    Fe = orth(np.column_stack([env["e1"], env["e2"]]))
    Fh = orth(np.column_stack([env["hh1"], env["hh2"]]))
    O = Fe.T @ (Fh * w[:, None])
    Ze = Fe.T @ (Fe * (w * z)[:, None])
    Zh = Fh.T @ (Fh * (w * z)[:, None])
    return np.abs(O), np.abs(Ze), np.abs(Zh)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=PKG.parents[2])
    repo = ap.parse_args().repo.resolve()
    d26 = repo / "nextnano/demos/26_real_chi2_paper_comparison/outputs"
    kp8_raw = PKG / "cached_raw/kp8/bias_00000/Quantum/acqw"
    src = {
        "spectrum_23D": repo / "demo_results/demo24/demo23_reanalysis/spectra/23D_chi2.csv",
        "zero_table": d26 / "DEMO26_REAL_ZERO_CROSSINGS.csv",
        "audit_summary": d26 / "HOME_EXHAUSTIVE_AUDIT/EXHAUSTIVE_HOME_TEST_SUMMARY.csv",
        "kmax_table": repo / "demo_results/demo24/demo23_reanalysis/tables/kmax_convergence.csv",
        "cutoff_spectrum": d26 / "CUTOFF_ARTIFACT_FINDING/fig2d_chi2_components.csv",
        "character_table": d26 / "HOME_EXHAUSTIVE_AUDIT/RAW_K0_STATE_CHARACTER.csv",
        "walkthrough": repo / "nextnano/demos/21_demo20_mathematical_walkthrough/DEMO20_MATH_WALKTHROUGH_LINEAR_1NM.md",
        "paper": repo / "nextnano/demos/23_k_resolved_dispersion_validation/paper_figure2d_digitized_simulation.csv",
        "kp8_spectrum": kp8_raw / "kp8/energy_spectrum_k00000.dat",
        "kp8_dipole": kp8_raw / "kp8_kp8/dipole_moment_matrix_elements_k00000_growth_z.txt",
    }
    paper = np.loadtxt(src["paper"], delimiter=",", skiprows=1)
    wl = np.arange(400.0, 1851.0, 1.0)

    # ---- demo26-baseline -----------------------------------------------------
    s23 = np.loadtxt(src["spectrum_23D"], delimiter=",", skiprows=1)
    assert np.array_equal(s23[:, 0], wl)
    re23, im23 = s23[:, 1], s23[:, 2]
    zt = rows(src["zero_table"])
    zc_saved = [float(r["nearest_Re_zero_crossing_nm"]) for r in zt]
    im_saved = [float(r["Im_at_interpolated_crossing_pm_per_V"]) for r in zt]
    assert np.allclose([z for z, _ in zero_crossings(wl, re23, im23)], zc_saved, atol=1e-6), "zero table vs spectrum"
    audit = {r["test_number"]: r for r in rows(src["audit_summary"])}
    for test, y in (("TEST 01", np.hypot(re23, im23)), ("TEST 02", re23), ("TEST 03", np.abs(re23))):
        assert abs(nrmse(wl, y, paper) - float(audit[test]["normalized_RMSE"])) < 1e-9, test
    kmax = next(r for r in rows(src["kmax_table"]) if r["mode"] == "23D" and float(r["fraction_of_bz"]) == 0.1)
    assert abs(float(kmax["peak_chi2_pm_per_V"]) - np.hypot(re23, im23).max()) < 1e-9
    prefactor = float(re.search(r"prefactor_pm_per_V\s+([0-9.]+)", src["walkthrough"].read_text(encoding="utf-8")).group(1))

    universal = [chk("modulus_identity_max_error", "max", 1e-9, "|chi| = sqrt(Re^2 + Im^2)", "consistency"),
                 chk("pathway_sum_max_error", "max", 1e-9, "chi = sum of the 16 pathway terms", "consistency"),
                 chk("pathway_count", "exact", 16, "Eq. 2: 8 conduction + 8 valence", "consistency")]
    trapezoid = [chk("k_weights_relative_error", "max", 1e-12, "sum g_s k dk/(2 pi) = g_s k_max^2/(4 pi)", "consistency"),
                 chk("eq2_diagonal_cancellation_max_abs_change", "max", 1e-8,
                     "adding c*I to Ze and Zh cancels between conduction and valence terms", "consistency")]
    baseline = [
        chk("spectrum_max_complex_error", "max", 1e-8, "validation/baseline_reference.csv (= 23D_chi2.csv)"),
        chk("re_zero_crossings_nm", "abs", zc_saved, "DEMO26_REAL_ZERO_CROSSINGS.csv", tol=0.01),
        chk("imag_at_re_zero_crossings", "rel", im_saved, "DEMO26_REAL_ZERO_CROSSINGS.csv", tol=0.005),
        chk("nRMSE_abs", "abs", float(audit["TEST 01"]["normalized_RMSE"]), "audit TEST 01", tol=1e-6),
        chk("nRMSE_real", "abs", float(audit["TEST 02"]["normalized_RMSE"]), "audit TEST 02", tol=1e-6),
        chk("nRMSE_abs_real", "abs", float(audit["TEST 03"]["normalized_RMSE"]), "audit TEST 03", tol=1e-6),
        chk("abs_real_peaks_nm", "contains", [float(audit["TEST 03"]["P2_nm"]), float(audit["TEST 03"]["P4_nm"])], "audit TEST 03 P2/P4", tol=1.0),
        chk("dominant_abs_peak_nm", "abs", float(kmax["peak_wavelength_nm"]), "kmax_convergence.csv 23D 0.1", tol=0.5),
        chk("max_abs", "rel", float(kmax["peak_chi2_pm_per_V"]), "kmax_convergence.csv 23D 0.1", tol=1e-6),
        chk("abs_at_1550nm", "rel", float(kmax["chi2_1550_pm_per_V"]), "kmax_convergence.csv 23D 0.1", tol=1e-6),
        chk("k_points", "exact", int(kmax["N_k"]), "kmax_convergence.csv"),
        chk("k_max_per_nm", "abs", float(kmax["kmax_per_nm"]), "kmax_convergence.csv", tol=1e-9),
        chk("kp8_pair_ids", "exact", [[11, 12], [13, 14], [5, 6], [3, 4]], "RAW_K0_STATE_CHARACTER.csv production labels"),
        chk("gamma_eV", "abs", GAMMA_EV, "paper Methods / demo23_config", tol=1e-15),
        chk("wavelength_points", "exact", 1451, "400-1850 nm, 1 nm"),
        chk("prefactor_pm_per_V", "rel", prefactor, "Demo 21 walkthrough", tol=1e-12),
    ] + trapezoid + universal

    # ---- demo26-cutoff (legacy -iGamma, unscaled) ------------------------------
    cut = np.loadtxt(src["cutoff_spectrum"], delimiter=",", skiprows=1)
    zc_cut = zero_crossings(wl, cut[:, 1], cut[:, 2])
    scale = float(np.max(np.abs(cut[:, 1])))
    cutoff = [
        chk("spectrum_max_complex_error", "max", 1e-4, "validation/cutoff_reference.csv (6 significant digits)"),
        chk("re_zero_crossings_nm", "abs", [z for z, _ in zc_cut], "saved cutoff spectrum", tol=0.01),
        chk("imag_over_max_abs_real_at_re_zero", "abs", [i / scale for _, i in zc_cut], "saved cutoff spectrum", tol=0.002),
        chk("nRMSE_abs_real", "abs", nrmse(wl, np.abs(cut[:, 1]), paper), "saved cutoff spectrum + paper", tol=2e-4),
        chk("nRMSE_abs", "abs", nrmse(wl, np.hypot(cut[:, 1], cut[:, 2]), paper), "saved cutoff spectrum + paper", tol=2e-4),
        chk("legacy_max_abs_real", "rel", scale, "saved cutoff spectrum", tol=1e-4),
        chk("integration_cutoff_per_nm", "abs", 0.2 * np.pi / 0.56533, "0.1 x 2pi/a, a = 0.56533 nm (CUTOFF_ARTIFACT_FINDING)", tol=1e-12),
    ] + universal

    # ---- kp8 production -------------------------------------------------------
    e = np.loadtxt(src["kp8_spectrum"], skiprows=1)[:, 1]
    char = rows(src["character_table"])
    cb = {int(r["solver_index"]): float(r["CB_fraction"]) for r in char}
    hh = {int(r["solver_index"]): float(r["HH_fraction"]) for r in char}
    pairs = [(i, i + 1) for i in range(1, 15, 2)]
    elec = sorted([p for p in pairs if cb[p[0]] >= 0.8], key=lambda p: e[p[0] - 1])[:2]
    hole = sorted([p for p in pairs if hh[p[0]] >= 0.8 and e[p[0] - 1] < e[elec[0][0] - 1]], key=lambda p: -e[p[0] - 1])[:2]
    roles = {"e1": elec[0], "e2": elec[1], "hh1": hole[0], "hh2": hole[1]}
    dip = {(int(r[0]), int(r[1])): abs(complex(r[4], r[5])) for r in np.loadtxt(src["kp8_dipole"], skiprows=1)}
    kinv = lambda A, B: float(np.sqrt(sum(dip[(a, b)] ** 2 for a in A for b in B) / 2))
    aO, aZe, aZh = rederive_matrices(kp8_raw / "kp8", roles)
    kp8 = [
        chk("selected_states", "exact", {r: list(p) for r, p in roles.items()},
            "RAW_K0_STATE_CHARACTER.csv + documented rule (CB>=0.8 lowest two; HH>=0.8 highest two)"),
        chk("k0_energies_eV", "abs", [float(e[p[0] - 1]) for p in roles.values()], "raw energy_spectrum_k00000.dat", tol=1e-9),
        chk("abs_zh12_nm", "rel", kinv(roles["hh1"], roles["hh2"]), "nextnano kp8 dipole_moment_matrix_elements (Kramers invariant)", tol=1e-4),
        chk("abs_ze12_nm", "rel", kinv(roles["e1"], roles["e2"]), "nextnano kp8 dipole_moment_matrix_elements (includes non-CB spinor weight)", tol=0.01),
        chk("k_points", "exact", 301, "kVectors_Gamma_to_y.dat"),
        chk("gamma_eV", "abs", GAMMA_EV, "paper Methods", tol=1e-15),
        chk("prefactor_pm_per_V", "rel", prefactor, "Demo 21 walkthrough", tol=1e-12),
        chk("abs_overlap_matrix", "abs", aO.tolist(), "raw envelopes, largest-component extraction + Loewdin (no SVD)", "independent_rederivation", 1e-8),
        chk("abs_ze_matrix", "abs", aZe.tolist(), "raw envelopes, largest-component extraction + Loewdin (no SVD)", "independent_rederivation", 1e-8),
        chk("abs_zh_matrix", "abs", aZh.tolist(), "raw envelopes, largest-component extraction + Loewdin (no SVD)", "independent_rederivation", 1e-8),
        chk("zh12_vs_this_dataset_nextnano_dipole_rel", "max", 1e-4, "package |Zh12| vs the analysed dataset's own nextnano dipole file", "consistency"),
        chk("ze12_vs_this_dataset_nextnano_dipole_rel", "max", 0.01, "package |Ze12| vs the analysed dataset's own nextnano dipole file", "consistency"),
        chk("orthonormality_error_after_lowdin", "max", 1e-10, "definition", "consistency"),
        chk("max_envelope_second_singular_fraction", "max", 1e-6, "one scalar envelope per doublet block", "consistency"),
        chk("max_envelope_imaginary_residue", "max", 1e-6, "envelope real after a global phase", "consistency"),
        chk("composition_file_max_abs_difference", "max", 1e-6, "raw spinor_composition_k00000_CbHhLhSo.dat", "consistency"),
        chk("origin_invariance_max_abs_change", "max", 1e-8, "z origin shifted by 20 nm inside the envelope integrals", "consistency"),
        chk("origin_sensitivity_without_lowdin_max_abs_change", "min", 1e-3,
            "same shift WITHOUT Loewdin must change chi2, proving the origin check can fail", "consistency"),
        chk("min_member_gap_eV", "min", GAMMA_EV, "each selected branch stays >= Gamma from every other dispersion column", "consistency"),
    ] + trapezoid + universal

    conditions = {"kp8_deck": "validation/decks/demo23_production_y_n301_k0100.in",
                  "singleband_case04_deck": "validation/decks/singleband_case04_graded.in",
                  "analysis_config": {"gamma_meV": 5.0, "gamma_sign": 1, "spin_degeneracy": 2, "period_nm": 30.0,
                                      "r_e_hh_nm": 0.751, "wavelength_min_nm": 400.0, "wavelength_max_nm": 1850.0,
                                      "wavelength_step_nm": 1.0, "cutoff_lattice_nm": 0.56533, "cutoff_fraction_pi_over_a": 0.2}}
    out = {"generated_by": "tools/build_reference.py", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "policy": "reference = pre-existing or raw nextnano; independent_rederivation = raw files through unrelated code; "
                     "consistency = dataset-independent limits",
           "conditions": conditions,
           "sources": {k: {"path": (p.relative_to(repo) if p.is_relative_to(repo) else p.relative_to(PKG)).as_posix(), "sha256": sha(p)}
                       for k, p in src.items()},
           "modes": {"demo26-baseline": baseline, "demo26-cutoff": cutoff, "kp8": kp8}}
    (PKG / "validation/reference_demo26.json").write_text(json.dumps(out, indent=2) + "\n")
    count = lambda cs: {c: sum(x["category"] == c for x in cs) for c in ("reference", "independent_rederivation", "consistency")}
    print("wrote validation/reference_demo26.json:", {m: count(v) for m, v in out["modes"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
