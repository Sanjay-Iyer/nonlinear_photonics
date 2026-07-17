"""Phase 2 - aestimo envelope states, matrix elements, and Al-fraction calibration.

Drives aestimo's self-consistent Schrodinger(-Poisson) solver for the ideal and
graded ACQW structures, extracts CB/HH/LH states, centroids, intersubband and
interband matrix elements, calibrates the barrier Al fraction so that
E(HH2->CB2) ~= 1.58 eV, and checkpoints everything with Fig. 2a/2b plots.

Reuses the validated valence-spinor recovery + matrix-element helpers from the
prior session's paper_reproduction module (git/aestimo/paper).

Usage:
  python run_states.py --config ../config/paper_params.yaml            # full phase
  python run_states.py --variant ideal --al 0.40 --no-calibrate        # single solve
"""
from __future__ import annotations

import argparse
import contextlib
import io
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
import aestimo
import database
from aestimo import amort_wave
import paper_reproduction as pr  # validated helpers


# ----------------------------------------------------------------------------
# Deck construction (abrupt or graded)
# ----------------------------------------------------------------------------
def build_material_list(cfg, x_bar, variant, grading_nm, substep_nm=0.1):
    """Return aestimo 7-element material rows for one period with outer barriers.

    Abrupt: 5 layers. Graded: interfaces replaced by piecewise-constant ramps of
    width grading_nm (run-length-encoded from a finely resampled Al profile), so
    the barrier<->well transitions slope linearly (Ref38 EDS).
    """
    tb, d1, cb, d2 = cfg["material"]["period_layers_nm"]

    def row(thick, x):
        if x < 1e-6:
            return [float(thick), "GaAs", 0.0, 0.0, 0.0, "n", "w"]
        return [float(thick), "AlGaAs", float(x), 0.0, 0.0, "n", "b"]

    if grading_nm <= 0:
        return [row(tb, x_bar), row(d1, 0.0), row(cb, x_bar),
                row(d2, 0.0), row(tb, x_bar)]

    # Build a fine Al-fraction profile over the *active* region (wells+barriers
    # between the two outer barriers) and RLE it into thin layers. Outer barriers
    # stay as single blocks.
    # nominal interface boundaries measured from start of wide well:
    b = np.array([0.0, d1, d1 + cb, d1 + cb + d2])   # wide|cb, cb|narrow, narrow|right
    active_len = d1 + cb + d2
    zc = np.arange(substep_nm / 2, active_len, substep_nm)   # cell centers

    def abrupt_active_x(z):
        # x_bar in the coupling barrier band [d1, d1+cb], 0 in wells
        in_cb = (z >= b[1]) & (z < b[2])
        return np.where(in_cb, x_bar, 0.0)

    xa = abrupt_active_x(zc)
    # graded: moving average with window = grading_nm, but the outer-barrier
    # boundaries (z=0 and z=active_len) ramp against x_bar -> pad with x_bar.
    w = max(1, int(round(grading_nm / substep_nm)))
    if w % 2 == 0:
        w += 1
    pad = w // 2
    xp = np.concatenate([np.full(pad, x_bar), xa, np.full(pad, x_bar)])
    xg = np.convolve(xp, np.ones(w) / w, mode="valid")

    # RLE into layers
    rows = [row(tb, x_bar)]                     # left outer barrier
    start = 0
    for i in range(1, len(xg) + 1):
        if i == len(xg) or abs(xg[i] - xg[start]) > 1e-4:
            rows.append(row((i - start) * substep_nm, xg[start]))
            start = i
    rows.append(row(tb, x_bar))                 # right outer barrier
    return rows


def solve_states(cfg, x_bar, variant, grading_nm=None):
    """Run aestimo; return dict of electron/hole states + geometry on the active grid."""
    sc = cfg["solver"]["aestimo"]
    tb, d1, cb, d2 = cfg["material"]["period_layers_nm"]
    if grading_nm is None:
        grading_nm = cfg["structure_variants"][variant]["grading_width_nm"]
    grid_nm = float(sc["grid_nm"])
    pad = float(sc["quantum_region_pad_nm"])

    material = build_material_list(cfg, x_bar, variant, grading_nm)
    total = sum(r[0] for r in material)
    n_max = int(total / grid_nm + 0.5)
    active_left = tb
    active_right = tb + d1 + cb + d2
    deck = dict(
        T=float(cfg["material"]["temperature_K"]),
        Fapplied=0.0, vmin=0.0, vmax=0.0, Each_Step=False,
        surface=np.zeros(2), mat_type="Zincblende",
        subnumber_e=int(sc["subnumber_e"]), subnumber_h=int(sc["subnumber_h"]),
        computation_scheme=int(sc["computation_scheme"]),
        gridfactor=grid_nm, maxgridpoints=60000, material=material,
        dop_profile=np.zeros(n_max), Quantum_Regions=True,
        Quantum_Regions_boundary=np.asarray([[active_left - pad, active_right + pad]]),
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        model = aestimo.StructureFrom(deck, database)
        result = aestimo.Poisson_Schrodinger(model)

    wi = 1
    i1, i2, _, _ = amort_wave(wi, result.Well_boundary, model.n_max)
    z_m = np.asarray(result.xaxis[i1:i2], float)
    nreg = i2 - i1

    # Electrons (scalar envelopes)
    e_energy_meV = np.asarray(result.E_statec_general[wi], float)
    psi_e = np.asarray([pr._normalize(np.asarray(result.wfe_general[wi][i][:nreg], float), z_m)
                        for i in range(deck["subnumber_e"])])
    # Holes (3x3 kp spinors), recovered from the retained Hamiltonian
    h_energy_eV, spinors, hdiag = pr.recover_valence_spinors(result, wi, return_diagnostics=True)

    # Poisson triviality: structure is undoped (dop_profile all zero) and
    # computation_scheme=0 is Schrodinger-only, so there is no charge to drive a
    # Poisson term. Record the driving quantities so the manifest can confirm it.
    dop_max = float(np.max(np.abs(np.asarray(deck["dop_profile"]))))

    return {
        "variant": variant, "x_bar": float(x_bar), "grading_nm": float(grading_nm),
        "z_nm": z_m * 1e9, "z_m": z_m,
        "e_energy_meV": e_energy_meV, "psi_e": psi_e,
        "h_energy_eV": h_energy_eV, "spinors": spinors,
        "h_diag": hdiag,
        "regions_m": {"wide": (tb * 1e-9, (tb + d1) * 1e-9),
                      "coupling": ((tb + d1) * 1e-9, (tb + d1 + cb) * 1e-9),
                      "narrow": ((tb + d1 + cb) * 1e-9, (tb + d1 + cb + d2) * 1e-9)},
        "regions_nm": {"wide": (tb, tb + d1),
                       "coupling": (tb + d1, tb + d1 + cb),
                       "narrow": (tb + d1 + cb, tb + d1 + cb + d2)},
        "n_layers": len(material),
        "computation_scheme": int(deck["computation_scheme"]),
        "doping_max_cm3": dop_max,
        "eg_gaas_eV": float(database.materialproperty["GaAs"]["Eg"]),
    }


# ----------------------------------------------------------------------------
# Analysis: labels, centroids, matrix elements, localization
# ----------------------------------------------------------------------------
def _region_weight(density, z_m, lo_m, hi_m):
    """Probability in [lo_m, hi_m]; density is normalized to 1 on the z_m grid."""
    m = (z_m >= lo_m) & (z_m < hi_m)
    return float(np.trapezoid(np.where(m, density, 0.0), z_m))


def _centroid_nm(density, z_m):
    return float(np.trapezoid(z_m * density, z_m) / np.trapezoid(density, z_m)) * 1e9


def analyze(states):
    z_m = states["z_m"]
    reg = states["regions_m"]

    # electron densities/centroids. E_statec_general already includes the host
    # bandgap on the same absolute scale as the recovered valence energies, so
    # the interband transition is simply E_e - E_h (matches prior pipeline).
    e_out = []
    for i, psi in enumerate(states["psi_e"]):
        dens = np.abs(psi) ** 2
        e_out.append({
            "label": f"CB{i+1}", "energy_eV": float(states["e_energy_meV"][i]) * 1e-3,
            "centroid_nm": _centroid_nm(dens, z_m),
            "wide": _region_weight(dens, z_m, *reg["wide"]),
            "narrow": _region_weight(dens, z_m, *reg["narrow"]),
        })

    # valence: classify, then assign HH1/HH2 = 1st/2nd energy-ordered HH-like
    spinors = states["spinors"]
    h_e = states["h_energy_eV"]
    cls = pr.classify_valence_spinors(spinors, z_m)
    v_out = []
    for i, (sp, en, c) in enumerate(zip(spinors, h_e, cls)):
        dens = np.sum(np.abs(sp) ** 2, axis=0)
        v_out.append({
            "raw_index": i, "energy_eV": float(en), "label_char": c["label"],
            "weights_HH_LH_SO": [float(w) for w in c["component_weights"]],
            "centroid_nm": _centroid_nm(dens, z_m),
            "wide": _region_weight(dens, z_m, *reg["wide"]),
            "narrow": _region_weight(dens, z_m, *reg["narrow"]),
        })
    hh_like = [v for v in v_out if v["label_char"] == "HH-like"]
    hh_like.sort(key=lambda v: -v["energy_eV"])   # highest energy first = HH1
    for k, v in enumerate(hh_like):
        v["hh_order"] = k + 1
    lh_like = [v for v in v_out if v["label_char"] == "LH-like"]

    # Branch-tracked / well-character view: among excited HH-like states (below
    # HH1), which is wide-localized? Per ROOT_CAUSE_REPORT the wide branch is
    # typically energy-ordered HH3, exchanging with the narrow HH2 through an
    # anticrossing. Report both so the paper's Fig-2a picture is traceable.
    well_char = None
    if len(hh_like) >= 2:
        excited = hh_like[1:]
        wide_branch = max(excited, key=lambda v: v["wide"])
        well_char = {
            "energy_ordered_HH2_raw_index": hh_like[1]["raw_index"],
            "energy_ordered_HH2_wide": hh_like[1]["wide"],
            "energy_ordered_HH2_narrow": hh_like[1]["narrow"],
            "wide_localized_excited_HH_order": wide_branch["hh_order"],
            "wide_localized_excited_HH_wide": wide_branch["wide"],
        }

    def interband(m, n):
        """E(HHm -> CBn) = Eg + E_e_conf + |E_hh_binding| (eV)."""
        hh = hh_like[m - 1]
        e = e_out[n - 1]
        return e["energy_eV"] - hh["energy_eV"]   # e energy (>0) minus hh (<0)

    E11 = interband(1, 1) if len(hh_like) >= 1 else None
    E22 = interband(2, 2) if len(hh_like) >= 2 else None

    # intersubband z-matrix elements (nm)
    zmel_e = {}
    for a in range(len(states["psi_e"])):
        for bb in range(len(states["psi_e"])):
            zmel_e[f"e{a+1}_z_e{bb+1}"] = float(np.real(
                pr._zmel(states["psi_e"][a], states["psi_e"][bb], z_m))) * 1e9
    zmel_hh = {}
    for a in range(len(hh_like)):
        for bb in range(len(hh_like)):
            i_a = hh_like[a]["raw_index"]
            i_b = hh_like[bb]["raw_index"]
            zmel_hh[f"hh{a+1}_z_hh{bb+1}"] = float(np.real(
                pr._spinor_zmel(spinors[i_a], spinors[i_b], z_m))) * 1e9

    # interband envelope overlaps <hh_m | e_n> (TE-weighted, HH leg)
    overlaps = {}
    for a in range(min(2, len(hh_like))):
        for n in range(len(states["psi_e"])):
            i_a = hh_like[a]["raw_index"]
            overlaps[f"hh{a+1}_e{n+1}"] = complex(
                pr._te_interband_overlap(spinors[i_a], states["psi_e"][n], z_m))

    # centroid offset HH2 vs CB2 (the dipole-like asymmetry)
    dz_22 = None
    if len(hh_like) >= 2 and len(e_out) >= 2:
        dz_22 = e_out[1]["centroid_nm"] - hh_like[1]["centroid_nm"]

    # localization booleans (paper claims)
    def loc(state, well):
        return state[well] > 0.5
    claims = {}
    if len(hh_like) >= 2 and len(e_out) >= 2:
        claims = {
            "HH1_wide": loc(hh_like[0], "wide"),
            "HH2_wide": loc(hh_like[1], "wide"),
            "CB1_wide": loc(e_out[0], "wide"),
            "CB2_narrow": loc(e_out[1], "narrow"),
        }

    return {
        "electrons": e_out, "valence": v_out,
        "hh_like": hh_like, "lh_like": lh_like,
        "E11_eV": E11, "E22_eV": E22,
        "zmel_e_nm": zmel_e, "zmel_hh_nm": zmel_hh,
        "interband_overlaps": {k: {"re": v.real, "im": v.imag} for k, v in overlaps.items()},
        "delta_z_HH2_CB2_nm": dz_22,
        "localization_claims": claims,
        "well_character_HH2": well_char,
        "computation_scheme": states["computation_scheme"],
        "doping_max_cm3": states["doping_max_cm3"],
    }


# ----------------------------------------------------------------------------
# Calibration: scan Al fraction so E(HH2->CB2) = target
# ----------------------------------------------------------------------------
def calibrate_al(cfg, variant="ideal", log=None):
    lo, hi = cfg["calibration"]["scan_al_fraction"]
    step = cfg["calibration"]["scan_step"]
    target = cfg["calibration"]["target_E22_eV"]
    xs = np.round(np.arange(lo, hi + 1e-9, step), 4)
    scan = []
    for x in xs:
        try:
            st = solve_states(cfg, float(x), variant, grading_nm=0.0)
            an = analyze(st)
            e22 = an["E22_eV"]
        except Exception as e:
            e22 = None
            if log:
                append_log(log, f"calib x={x}: FAILED {type(e).__name__}: {e}")
        scan.append({"x": float(x), "E22_eV": e22})
        if log and e22 is not None:
            append_log(log, f"calib x={x:.3f}: E22={e22:.4f} eV (target {target})")
    valid = [s for s in scan if s["E22_eV"] is not None]
    # interpolate to target
    xs_v = np.array([s["x"] for s in valid])
    e22_v = np.array([s["E22_eV"] for s in valid])
    order = np.argsort(e22_v)
    x_star = float(np.interp(target, e22_v[order], xs_v[order]))
    return x_star, scan


# ----------------------------------------------------------------------------
# Plots
# ----------------------------------------------------------------------------
def plot_states(states, analysis, out_dir, cfg, stem):
    z = states["z_nm"]
    reg = states["regions_nm"]
    fig, ax = plt.subplots(figsize=(8, 5))
    # band edge context (conduction) from Phase1 physics
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase1_structure"))
    import build_structure as bs
    prof = bs.build_profile(cfg, states["variant"], grading_nm=states["grading_nm"],
                            grid_nm=0.02)
    ax.plot(prof["z_nm"], prof["E_c_eV"], color="k", lw=1.2, alpha=0.6)
    ax.plot(prof["z_nm"], prof["E_v_eV"], color="k", lw=1.2, alpha=0.6)
    for key, col in (("wide", "#fff2cc"), ("narrow", "#ffe0b0")):
        ax.axvspan(*reg[key], color=col, alpha=0.6, zorder=0)

    # electron states: plot |psi|^2 offset at their energy
    sc = 0.05
    for i, (psi, e) in enumerate(zip(states["psi_e"], analysis["electrons"])):
        y = e["energy_eV"]
        ax.fill_between(z, y, y + sc * np.abs(psi) ** 2 / np.max(np.abs(psi) ** 2),
                        color="#1f4e79", alpha=0.5)
        ax.text(z[0], y, e["label"], color="#1f4e79", fontsize=8, va="bottom")
    # HH1/HH2 densities at their energies
    for k, v in enumerate(analysis["hh_like"][:2]):
        sp = states["spinors"][v["raw_index"]]
        dens = np.sum(np.abs(sp) ** 2, axis=0)
        y = v["energy_eV"]
        ax.fill_between(z, y, y - sc * dens / np.max(dens), color="#c00000", alpha=0.5)
        ax.text(z[0], y, f"HH{k+1}", color="#c00000", fontsize=8, va="top")

    ax.set_xlabel("z (nm)")
    ax.set_ylabel("Energy (eV)")
    ttl = (f"Fig. 2a/2b — {states['variant']} x={states['x_bar']:.3f} "
           f"E11={analysis['E11_eV']:.3f} E22={analysis['E22_eV']:.3f} eV")
    ax.set_title(ttl, fontsize=10)
    ax.set_xlim(reg["wide"][0] - 6, reg["narrow"][1] + 6)
    save_plot(fig, out_dir, stem)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--variant", choices=["ideal", "graded", "both"], default="both")
    ap.add_argument("--al", type=float, default=None, help="fixed Al fraction (skip calibration)")
    ap.add_argument("--no-calibrate", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(exist_ok=True)
    log = start_run_log("phase2_aestimo", seed=0, extra={"variant": args.variant})

    # Calibration. Per DISCREPANCY.md (user-approved 2026-07-17), the barrier Al
    # fraction is calibrated to x=0.55: the literal E22=1.58 eV target is
    # unreachable in x in [0.30,0.60] and forcing x low collapses the chi2
    # asymmetry, whereas x=0.55 (Ref38-documented) reproduces the solver consensus
    # and the Fig-2e ~1500 nm peak. The E22(x) scan is still recorded as evidence.
    _, scan = calibrate_al(cfg, "ideal", log)  # record the scan for the report
    if args.al is not None:
        x_star = args.al
        print(f"[phase2] using fixed Al fraction x={x_star}")
    elif cfg["material"].get("al_fraction") is not None:
        x_star = float(cfg["material"]["al_fraction"])
        print(f"[phase2] calibrated Al fraction x* = {x_star:.4f} "
              f"(config; Fig-2e-peak interpretation, see DISCREPANCY.md)")
    else:
        x_star, scan = calibrate_al(cfg, "ideal", log)
        print(f"[phase2] calibrated Al fraction x* = {x_star:.4f} "
              f"(interp to E22={cfg['calibration']['target_E22_eV']} eV)")
    append_log(log, f"calibrated x* = {x_star}")

    variants = ["ideal", "graded"] if args.variant == "both" else [args.variant]
    results = {}
    for v in variants:
        st = solve_states(cfg, x_star, v)
        an = analyze(st)
        results[v] = {"states": st, "analysis": an}
        plot_states(st, an, out_dir, cfg, f"fig2a_states_{v}")
        print(f"\n[phase2] === {v} (x={x_star:.4f}, grading={st['grading_nm']} nm) ===")
        print(f"  E11(HH1->CB1) = {an['E11_eV']:.4f} eV   E22(HH2->CB2) = {an['E22_eV']:.4f} eV")
        print(f"  Poisson trivial: scheme={an['computation_scheme']} doping_max={an['doping_max_cm3']:.1e} cm^-3")
        print(f"  centroid offset Delta_z(HH2,CB2) = {an['delta_z_HH2_CB2_nm']:.3f} nm")
        print(f"  localization: {an['localization_claims']}")
        append_log(log, f"{v}: E11={an['E11_eV']:.4f} E22={an['E22_eV']:.4f} "
                        f"dz22={an['delta_z_HH2_CB2_nm']:.3f} {an['localization_claims']}")

    # Checkpoint
    ck = new_checkpoint(Path(__file__).resolve().parent, f"states_x{x_star:.3f}".replace(".", "p"))
    save = {}
    for v, r in results.items():
        st = r["states"]
        save[f"{v}_z_nm"] = st["z_nm"]
        save[f"{v}_psi_e"] = st["psi_e"]
        save[f"{v}_e_energy_meV"] = st["e_energy_meV"]
        save[f"{v}_spinors"] = st["spinors"]
        save[f"{v}_h_energy_eV"] = st["h_energy_eV"]
    np.savez_compressed(ck / "states.npz", **save)

    import json
    key_out = {"calibrated_al_fraction": x_star,
               "calibration_scan": scan,
               "variants": {v: {k: r["analysis"][k] for k in
                                ("E11_eV", "E22_eV", "delta_z_HH2_CB2_nm",
                                 "localization_claims", "well_character_HH2",
                                 "zmel_e_nm", "zmel_hh_nm",
                                 "interband_overlaps", "computation_scheme",
                                 "doping_max_cm3")}
                            for v, r in results.items()}}
    with open(ck / "analysis.json", "w", encoding="utf-8") as f:
        json.dump(key_out, f, indent=2, cls=NumpyJSONEncoder)
    write_manifest(ck, cfg,
                   inputs={"calibrated_al_fraction": x_star, "variants": variants},
                   outputs={v: {"E11_eV": results[v]["analysis"]["E11_eV"],
                                "E22_eV": results[v]["analysis"]["E22_eV"],
                                "delta_z_HH2_CB2_nm": results[v]["analysis"]["delta_z_HH2_CB2_nm"],
                                "localization": results[v]["analysis"]["localization_claims"]}
                            for v in variants})
    # copy plots into checkpoint
    for v in variants:
        for ext in ("png", "svg"):
            src = out_dir / f"fig2a_states_{v}.{ext}"
            if src.exists():
                (ck / src.name).write_bytes(src.read_bytes())
    print(f"\n[phase2] checkpoint: {ck}")
    print(f"[phase2] log: {log}")


if __name__ == "__main__":
    main()
