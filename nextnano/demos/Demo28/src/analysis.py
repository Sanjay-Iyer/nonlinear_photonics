"""Script 2 implementation: raw nextnano results -> complex chi2 -> observables, plots, validation."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import sys
import numpy as np

from .equation2 import Settings, evaluate, evaluate_parabolic, prefactor, radial_weights
from .raw_inputs import MODES, available_modes, load_inputs
from . import decks
from . import reporting as rp
from .validation import validate, markdown

ROOT = Path(__file__).resolve().parents[1]
DIRNAME = {"kp8": "kp8", "demo26-baseline": "demo26_baseline", "demo26-cutoff": "demo26_cutoff"}


def _json(v):
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, complex):
        return {"real": v.real, "imag": v.imag}
    if isinstance(v, Path):
        return str(v)
    raise TypeError(type(v).__name__)


def _sub(inputs, keep, electron, valence):
    k = inputs["k_per_nm"] if keep is None else inputs["k_per_nm"][keep]
    sl = slice(None) if keep is None else keep
    return {**inputs, "k_per_nm": k, "electron_eV": electron[..., sl], "valence_eV": valence[..., sl]}


def calculate(wl, inputs, settings, energies="mean", keep=None):
    """Complex chi2 with all 16 pathways.

    energies="mean":   doublet-averaged energies (historical treatment).
    energies="branch": average of chi2 over the four lower/upper electron-hole
                       branch pairings (kp8 production treatment).
    """
    if energies == "mean":
        chi, terms, labels, _ = evaluate(wl, _sub(inputs, keep, inputs["electron_eV"], inputs["valence_eV"]), settings)
        return chi, terms, labels
    chi = terms = 0
    for i in (0, 1):
        for j in (0, 1):
            c, t, labels, _ = evaluate(wl, _sub(inputs, keep, inputs["electron_branches_eV"][:, i],
                                                inputs["valence_branches_eV"][:, j]), settings)
            chi, terms = chi + c / 4, terms + t / 4
    return chi, terms, labels


def finding(feats: dict, metrics: dict, thr: dict) -> dict:
    """Computed, never assumed. Two separate questions with separate evidence."""
    zc = feats["re_zero_crossings"]
    return {
        "mechanism": {
            "question": "At the zeros of Re chi2, is Im chi2 (and therefore |chi2|) still finite?",
            "re_zero_count": len(zc),
            "at_re_zeros": [{"wavelength_nm": c["wavelength_nm"], "abs_real": 0.0,
                             "abs_imag_over_max_abs": c["abs_imag_over_max_abs"],
                             "abs_over_max_abs": c["abs_over_max_abs"]} for c in zc],
            "imag_nonzero_at_every_re_zero": bool(zc) and all(c["abs_imag_over_max_abs"] > thr["imag_nonzero_fraction_of_max_abs"] for c in zc),
            "abs_nonzero_at_every_re_zero": bool(zc) and all(c["abs_over_max_abs"] > thr["abs_nonzero_fraction_of_max_abs"] for c in zc)},
        "shape_comparison": {
            "question": "Does |Re chi2| or |chi2| actually reproduce the digitized Fig. 2d line shape?",
            "null_best_constant_nRMSE": metrics["null_best_constant"]["nRMSE"],
            "abs_real": metrics["abs_real"], "abs": metrics["abs"],
            "comparison_informative": metrics["abs_real"]["informative"] or metrics["abs"]["informative"],
            "abs_real_closer_than_abs": metrics["abs_real"]["nRMSE"] < metrics["abs"]["nRMSE"],
            "rule": "informative = nRMSE below the best flat line AND correlation >= 0.5"},
        "global_min_abs_over_max_abs_info": feats["min_abs_over_max_abs"],
        "note": "|Re chi2| is exactly zero at every refined Re zero crossing and |chi2| equals |Im chi2| there. "
                "Global minima include off-resonance spectral tails and are informational only.",
        "thresholds": thr}


def _brief(wl, chi, paper, reference_chi):
    f, m = rp.features(wl, chi), rp.paper_metrics(wl, chi, paper)
    return {"max_abs": f["max_abs"], "dominant_abs_peak_nm": f["dominant_abs_peak_nm"],
            "re_zero_crossings_nm": [c["wavelength_nm"] for c in f["re_zero_crossings"]],
            "nRMSE_abs_real": m["abs_real"]["nRMSE"], "nRMSE_abs": m["abs"]["nRMSE"],
            "max_abs_difference_over_production_max_abs": float(np.max(np.abs(chi - reference_chi)) / np.max(np.abs(reference_chi)))}


def run_mode(mode, root, cfg, settings, wl, paper, outdir, make_plots=True) -> dict:
    inputs = load_inputs(root, mode)
    k = np.asarray(inputs["k_per_nm"], float)
    pi_a = np.pi / cfg["pi_over_a_lattice_nm"]
    weights = radial_weights(k, settings.spin_degeneracy)
    analytic = settings.spin_degeneracy * k[-1] ** 2 / (4 * np.pi)
    summary = {"mode": mode, "units": "pm/V", "settings": {**asdict(settings), "gamma_eV": settings.gamma_eV},
               "wavelength_is_fundamental": True, "wavelength_points": int(len(wl)),
               "wavelength_range_nm": [float(wl[0]), float(wl[-1])], "k_points": int(len(k)),
               "k_max_per_nm": float(k[-1]), "k_max_over_pi_over_a": float(k[-1] / pi_a),
               "k_weights_relative_error": float(abs(weights.sum() - analytic) / analytic),
               "prefactor_pm_per_V": prefactor(settings), "reference_spectrum": None}
    scan = []
    if mode == "demo26-cutoff":
        cutoff = cfg["cutoff_fraction_pi_over_a"] * np.pi / cfg["cutoff_lattice_nm"]
        chi, terms, labels = evaluate_parabolic(wl, inputs, cutoff, settings)
        evaluator = lambda w: evaluate_parabolic(w, inputs, cutoff, settings)[0]
        factor = prefactor(settings) * settings.spin_degeneracy / (4 * np.pi ** 2)
        legacy = lambda v: -np.conj(v) / factor  # historical: -iGamma, opposite pathway sign, bare measure, no prefactor
        summary["reference_spectrum"] = rp.check_reference(wl, chi, ROOT / "validation/cutoff_reference.csv",
                                                            cfg["cutoff_reference_tolerance_unscaled"], legacy)
        summary["legacy"] = {"max_abs_real": float(np.max(np.abs(legacy(chi).real))),
                             "conversion": "legacy = -conj(chi_pm_per_V) / (prefactor * g_s / (4 pi^2))"}
        summary["integration"] = "analytic 2D integral of extrapolated parabolas, measure g_s k dk/(2 pi), 0..cutoff"
        summary["energy_treatment"] = "parabolas E0 + A k^2 fitted to the doublet-averaged baseline dispersion"
        for f in cfg["cutoff_scan_fractions_pi_over_a"]:
            scan.append((f"$k_{{max}}={f:g}\\,\\pi/a$", evaluate_parabolic(wl, inputs, f * np.pi / cfg["cutoff_lattice_nm"], settings)[0]))
    else:
        energies = "branch" if mode == "kp8" else "mean"
        cutoff = float(k[-1])
        chi, terms, labels = calculate(wl, inputs, settings, energies)
        evaluator = lambda w: calculate(w, inputs, settings, energies)[0]
        summary["energy_treatment"] = ("branch-resolved: chi2 averaged over the four lower/upper electron-hole branch pairings"
                                       if energies == "branch" else "doublet-averaged energies (historical)")
        summary["integration"] = "trapezoid over solved k points, measure g_s k dk/(2 pi), 0..k_max of the nextnano dispersion"
        alg = {**inputs, "ze_nm": inputs["ze_nm"] + 20 * np.eye(2), "zh_nm": inputs["zh_nm"] + 20 * np.eye(2)}
        summary["eq2_diagonal_cancellation_max_abs_change"] = float(np.max(np.abs(calculate(wl, alg, settings, energies)[0] - chi)))
        if mode == "kp8":
            shifted = {**inputs, **inputs["matrices_origin_shifted"]}
            summary["origin_invariance_max_abs_change"] = float(np.max(np.abs(calculate(wl, shifted, settings, energies)[0] - chi)))
            pre = calculate(wl, {**inputs, **inputs["matrices_pre_lowdin"]}, settings, energies)[0]
            pre_s = calculate(wl, {**inputs, **inputs["matrices_pre_lowdin_origin_shifted"]}, settings, energies)[0]
            summary["origin_sensitivity_without_lowdin_max_abs_change"] = float(np.max(np.abs(pre_s - pre)))
            bw = inputs["block_weights"]
            amp = {**inputs, "overlap": np.asarray(inputs["overlap"]) * np.sqrt([bw["e1"], bw["e2"]])[:, None]}
            summary["sensitivity"] = {
                "doublet_averaged_energies": _brief(wl, calculate(wl, inputs, settings, "mean")[0], paper, chi),
                "overlap_weighted_by_conduction_block_amplitude": _brief(wl, calculate(wl, amp, settings, energies)[0], paper, chi)}
        if mode == "demo26-baseline":
            summary["reference_spectrum"] = rp.check_reference(wl, chi, ROOT / "validation/baseline_reference.csv",
                                                                cfg["baseline_reference_tolerance_pm_per_V"])
        for frac in cfg["truncation_scan_fractions_of_solved_k"]:
            keep = k <= frac * k[-1] + 1e-12
            scan.append((f"$k_{{max}}={k[keep][-1] / pi_a:.3f}\\,\\pi/a$", calculate(wl, inputs, settings, energies, keep)[0]))
    summary["integration_cutoff_per_nm"] = float(cutoff)
    summary["pathway_count"], summary["pathway_labels"] = len(labels), labels
    summary["pathway_sum_max_error"] = float(np.max(np.abs(chi - np.sum(terms, axis=0))))
    ob = rp.observables(chi)
    summary["modulus_identity_max_error"] = float(np.max(np.abs(ob["abs"] - np.sqrt(ob["real"] ** 2 + ob["imag"] ** 2))))
    summary["features"] = rp.features(wl, chi, evaluator)
    summary["paper_metrics"] = rp.paper_metrics(wl, chi, paper)
    summary["finding"] = finding(summary["features"], summary["paper_metrics"], cfg["finding_thresholds"])
    summary["cutoff_scan"] = [{"label": lab, "paper_metrics": rp.paper_metrics(wl, c, paper),
                               "re_zero_crossings_nm": [x["wavelength_nm"] for x in rp.features(wl, c)["re_zero_crossings"]],
                               "dominant_abs_real_peak_nm": float(wl[np.argmax(np.abs(c.real))])} for lab, c in scan]
    keep = ("state_ids", "kp8_pair_ids", "overlap", "ze_nm", "zh_nm", "checks", "envelope_reduction", "doublet_table",
            "limitations", "supplied_inputs", "dispersion", "envelope_grid_points", "single_band_gram_error", "model",
            "block_weights")
    summary["inputs"] = {key: inputs[key] for key in keep if key in inputs}
    ee, vv = np.asarray(inputs["electron_eV"]), np.asarray(inputs["valence_eV"])
    summary["inputs"]["k0_energies_eV"] = [float(x) for x in np.r_[ee[:, 0], vv[:, 0]]]
    summary["inputs"]["k0_transition_energies_eV"] = (ee[:, None, 0] - vv[None, :, 0]).tolist()

    outdir.mkdir(parents=True, exist_ok=True)
    rp.write_csv(outdir, wl, chi, paper, "pm/V")
    rp.write_pathways(outdir, wl, terms, labels)
    summary["plots"] = rp.plots(outdir, wl, chi, paper, summary["features"], "pm/V", scan) if make_plots else []
    summary["normalization"] = {"paper": "divided by its own maximum", "abs_real": "divided by its own maximum",
                                "abs": "divided by its own maximum", "signed_plots": "absolute pm/V, no normalization"}
    (outdir / "derived_inputs.json").write_text(json.dumps(inputs, indent=2, default=_json))
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=_json))
    (outdir / "SUMMARY.md").write_text(mode_markdown(summary), encoding="utf-8")
    return summary


def mode_markdown(s: dict) -> str:
    f, m, fd = s["features"], s["paper_metrics"], s["finding"]
    ref = json.dumps(s["reference_spectrum"]) if s["reference_spectrum"] else \
        "none: no pre-existing spectrum for this mode; validated component by component (see VALIDATION.md)"
    L = [f"# chi2 result: {s['mode']}", "", "| quantity | value |", "|---|---|",
         f"| broadening Gamma | {s['settings']['gamma_meV']} meV = {s['settings']['gamma_eV']} eV, denominators `{'+' if s['settings']['gamma_sign'] > 0 else '-'}iGamma` |",
         f"| wavelength | fundamental, {s['wavelength_range_nm'][0]:g}-{s['wavelength_range_nm'][1]:g} nm, {s['wavelength_points']} points |",
         f"| k points / solved k_max | {s['k_points']} / {s['k_max_per_nm']:.6g} nm^-1 ({s['k_max_over_pi_over_a']:.4f} pi/a) |",
         f"| integration cutoff | {s['integration_cutoff_per_nm']:.6g} nm^-1 |",
         f"| integration | {s['integration']} |", f"| energies | {s['energy_treatment']} |",
         f"| pathways | {s['pathway_count']} |", f"| prefactor | {s['prefactor_pm_per_V']:.12g} pm/V per summand |",
         f"| states | {json.dumps(s['inputs'].get('state_ids'))} |", f"| reference spectrum | {ref} |", "",
         "## Re chi2 zero crossings", "", "| wavelength nm | Im chi2 pm/V | abs chi2 pm/V | abs/max abs |", "|---:|---:|---:|---:|"]
    L += [f"| {c['wavelength_nm']:.4f} | {c['imag']:.6g} | {c['abs']:.6g} | {c['abs_over_max_abs']:.3f} |" for c in f["re_zero_crossings"]]
    L += ["", f"|Re| peaks (nm): {[round(p['wavelength_nm']) for p in f['abs_real_peaks']]}  ",
          f"|chi| peaks (nm): {[round(p['wavelength_nm']) for p in f['abs_peaks']]}  ",
          f"|chi| minima (nm): {[round(p['wavelength_nm']) for p in f['abs_minima']]}  ",
          f"dominant |Re| peak {f['dominant_abs_real_peak_nm']:g} nm; dominant |chi| peak {f['dominant_abs_peak_nm']:g} nm "
          f"({f['max_abs']:.6g} pm/V)", "", "## Against digitized Fig. 2d (each curve normalized to its own maximum)", "",
          f"Best flat line: nRMSE {m['null_best_constant']['nRMSE']:.4f}. An observable is informative only if it beats that "
          "and correlates at r >= 0.5.", "", "| observable | nRMSE | correlation | beats flat line | informative |", "|---|---:|---:|---|---|"]
    L += [f"| {k} | {m[k]['nRMSE']:.6f} | {m[k]['correlation']:.4f} | {m[k]['beats_null']} | {m[k]['informative']} |"
          for k in ("real", "abs_real", "abs", "imag")]
    L += ["", "## Finding (computed)", "", "```json", json.dumps(fd, indent=2), "```"]
    if "sensitivity" in s:
        L += ["", "## Sensitivity of the production choices", "", "```json", json.dumps(s["sensitivity"], indent=2), "```"]
    L += ["", "## Limitations", ""] + [f"- {x}" for x in s["inputs"].get("limitations", [])]
    return "\n".join(L) + "\n"


def dataset_conditions(root: Path, cfg: dict, reference: dict) -> dict:
    cond = reference["conditions"]

    def match(job, ref_rel):
        cands = [root / "decks" / f"{job}.in"] + (sorted((root / job).rglob("*.in")) if (root / job).is_dir() else [])
        path = next((p for p in cands if p.is_file()), None)
        return None if path is None else decks.same_deck(path.read_text(errors="replace"), (ROOT / ref_rel).read_text())

    return {"kp8_deck_matches_reference": match("kp8", cond["kp8_deck"]),
            "case04_deck_matches_reference": match("singleband_case04_graded", cond["singleband_case04_deck"]),
            "config_matches_reference": all(cfg.get(key) == value for key, value in cond["analysis_config"].items())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="02_calculate_chi2.py", description=__doc__)
    ap.add_argument("--input", type=Path, help="results root from 01_run_nextnano.py (default: output/raw, else cached_raw)")
    ap.add_argument("--output", type=Path, default=ROOT / "output" / "analysis")
    ap.add_argument("--mode", choices=("all",) + MODES, default="all")
    ap.add_argument("--config", type=Path, default=ROOT / "config" / "analysis.json")
    ap.add_argument("--no-plots", action="store_true")
    ap.add_argument("--check-reference", action="store_true", help="exit 3 if any applicable validation check FAILs")
    args = ap.parse_args(argv)
    try:
        root = args.input
        if root is None:
            root = ROOT / "output" / "raw" if (ROOT / "output/raw/kp8").is_dir() else ROOT / "cached_raw"
            if root.name == "cached_raw":
                print("NOTE: no Script 1 results found; using the shipped cached Professional output in cached_raw/")
        root = root.resolve()
        if not root.is_dir():
            raise ValueError(f"results root not found: {root}")
        cfg = json.loads(args.config.read_text(encoding="utf-8"))
        settings = Settings(**{key: cfg[key] for key in ("gamma_meV", "gamma_sign", "spin_degeneracy", "period_nm", "r_e_hh_nm")})
        step = cfg["wavelength_step_nm"]
        wl = np.arange(cfg["wavelength_min_nm"], cfg["wavelength_max_nm"] + step / 2, step)
        paper = np.loadtxt(ROOT / "validation/paper.csv", delimiter=",", skiprows=1)
        reference_path = ROOT / "validation/reference_demo26.json"
        conditions = dataset_conditions(root, cfg, json.loads(reference_path.read_text(encoding="utf-8")))
        status = available_modes(root)
        modes = [m for m in MODES if args.mode in ("all", m)]
        summaries = {}
        for mode in modes:
            if status[mode] != "available":
                if args.mode != "all":
                    raise ValueError(f"mode {mode} unavailable: {status[mode]}")
                print(f"[{mode}] skipped: {status[mode]}")
                continue
            s = run_mode(mode, root, cfg, settings, wl, paper, args.output / DIRNAME[mode], not args.no_plots)
            summaries[mode] = s
            ref = s["reference_spectrum"]["status"] if s["reference_spectrum"] else "n/a"
            sc = s["finding"]["shape_comparison"]
            print(f"[{mode}] reference spectrum {ref} | nRMSE |Re|={s['paper_metrics']['abs_real']['nRMSE']:.4f} "
                  f"|chi|={s['paper_metrics']['abs']['nRMSE']:.4f} (flat line {sc['null_best_constant_nRMSE']:.4f}; "
                  f"informative {sc['comparison_informative']}) | Re zeros "
                  f"{[round(c['wavelength_nm'], 3) for c in s['features']['re_zero_crossings']]}")
        report = validate(summaries, reference_path, conditions)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "validation.json").write_text(json.dumps(report, indent=2, default=_json))
        (args.output / "VALIDATION.md").write_text(markdown(report), encoding="utf-8")
        files = sorted(p for p in root.rglob("*") if p.is_file())
        meta = {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "input_root": str(root),
                "dataset_conditions": conditions,
                "script1_metadata": json.loads((root / "demo28_run_metadata.json").read_text()) if (root / "demo28_run_metadata.json").is_file() else None,
                "raw_files": [{"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
                "config": cfg, "python": platform.python_version(), "numpy": np.__version__,
                "licensed_solver_executed_by_script2": False, "modes_run": list(summaries)}
        (args.output / "run_metadata.json").write_text(json.dumps(meta, indent=2, default=_json))
        t = report["totals"]
        print(f"validation: PASS {t['PASS']} FAIL {t['FAIL']} NOT APPLICABLE {t['NOT APPLICABLE']} -> {args.output / 'VALIDATION.md'}")
        return 3 if args.check_reference and t["FAIL"] else 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
