"""Compare a run's summaries with validation/reference_demo26.json -> PASS / FAIL / NOT APPLICABLE.

Check categories
    reference                 value predates this package or is raw nextnano output
    independent_rederivation  recomputed from raw nextnano files by different code (tools/build_reference.py)
    consistency               internal invariant that must hold for any dataset

Reference and re-derivation checks describe the shipped dataset and default config.
When the analysed deck or config differs they are NOT APPLICABLE, never FAIL.
Scientific findings are reported elsewhere and are never gates.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np

STATUSES = ("PASS", "FAIL", "NOT APPLICABLE", "NOT RUN")


def _crossings(s):
    return s["features"]["re_zero_crossings"]


def _rel(a, b):
    return abs(a - b) / abs(b)


EXTRACT = {
    "spectrum_max_complex_error": lambda s: (s.get("reference_spectrum") or {}).get("max_complex_error"),
    "re_zero_crossings_nm": lambda s: [c["wavelength_nm"] for c in _crossings(s)],
    "imag_at_re_zero_crossings": lambda s: [c["imag"] for c in _crossings(s)],
    "imag_over_max_abs_real_at_re_zero": lambda s: [c["imag"] / s["features"]["max_abs_real"] for c in _crossings(s)],
    "nRMSE_abs": lambda s: s["paper_metrics"]["abs"]["nRMSE"],
    "nRMSE_real": lambda s: s["paper_metrics"]["real"]["nRMSE"],
    "nRMSE_abs_real": lambda s: s["paper_metrics"]["abs_real"]["nRMSE"],
    "abs_real_peaks_nm": lambda s: [p["wavelength_nm"] for p in s["features"]["abs_real_peaks"]],
    "dominant_abs_peak_nm": lambda s: s["features"]["dominant_abs_peak_nm"],
    "max_abs": lambda s: s["features"]["max_abs"],
    "abs_at_1550nm": lambda s: float(np.hypot(s["features"]["chi2_at_1550nm"]["real"], s["features"]["chi2_at_1550nm"]["imag"])),
    "legacy_max_abs_real": lambda s: s.get("legacy", {}).get("max_abs_real"),
    "k_points": lambda s: s["k_points"],
    "k_max_per_nm": lambda s: s["k_max_per_nm"],
    "integration_cutoff_per_nm": lambda s: s["integration_cutoff_per_nm"],
    "kp8_pair_ids": lambda s: s["inputs"].get("kp8_pair_ids"),
    "pathway_count": lambda s: s["pathway_count"],
    "gamma_eV": lambda s: s["settings"]["gamma_eV"],
    "wavelength_points": lambda s: s["wavelength_points"],
    "prefactor_pm_per_V": lambda s: s["prefactor_pm_per_V"],
    "selected_states": lambda s: s["inputs"].get("state_ids"),
    "k0_energies_eV": lambda s: s["inputs"].get("k0_energies_eV"),
    "abs_zh12_nm": lambda s: s["inputs"]["checks"].get("package_abs_zh12_nm"),
    "abs_ze12_nm": lambda s: s["inputs"]["checks"].get("package_abs_ze12_nm"),
    "abs_overlap_matrix": lambda s: np.abs(np.asarray(s["inputs"]["overlap"])).tolist(),
    "abs_ze_matrix": lambda s: np.abs(np.asarray(s["inputs"]["ze_nm"])).tolist(),
    "abs_zh_matrix": lambda s: np.abs(np.asarray(s["inputs"]["zh_nm"])).tolist(),
    "zh12_vs_this_dataset_nextnano_dipole_rel": lambda s: _rel(s["inputs"]["checks"]["package_abs_zh12_nm"], s["inputs"]["checks"]["nextnano_dipole_hh1_hh2_nm"]),
    "ze12_vs_this_dataset_nextnano_dipole_rel": lambda s: _rel(s["inputs"]["checks"]["package_abs_ze12_nm"], s["inputs"]["checks"]["nextnano_dipole_e1_e2_nm"]),
    "orthonormality_error_after_lowdin": lambda s: s["inputs"]["checks"]["orthonormality_error_after_lowdin"],
    "max_envelope_second_singular_fraction": lambda s: max(d["second_singular_fraction"] for d in s["inputs"]["envelope_reduction"].values()),
    "max_envelope_imaginary_residue": lambda s: max(d["imaginary_residue"] for d in s["inputs"]["envelope_reduction"].values()),
    "composition_file_max_abs_difference": lambda s: s["inputs"]["checks"]["composition_file_max_abs_difference"],
    "origin_invariance_max_abs_change": lambda s: s["origin_invariance_max_abs_change"],
    "origin_sensitivity_without_lowdin_max_abs_change": lambda s: s["origin_sensitivity_without_lowdin_max_abs_change"],
    "eq2_diagonal_cancellation_max_abs_change": lambda s: s["eq2_diagonal_cancellation_max_abs_change"],
    "min_member_gap_eV": lambda s: min(s["inputs"]["checks"]["min_member_gap_to_other_columns_eV"].values()),
    "k_weights_relative_error": lambda s: s["k_weights_relative_error"],
    "modulus_identity_max_error": lambda s: s["modulus_identity_max_error"],
    "pathway_sum_max_error": lambda s: s["pathway_sum_max_error"],
}


def _judge(kind, computed, ref, tol):
    if computed is None:
        return False
    if kind == "exact":
        return computed == ref
    if kind == "max":
        return float(computed) <= float(ref)
    if kind == "min":
        return float(computed) >= float(ref)
    if kind == "contains":
        return all(any(abs(c - r) <= tol for c in computed) for r in ref)
    c, r = np.asarray(computed, float), np.asarray(ref, float)
    if c.shape != r.shape:
        return False
    bound = tol * np.abs(r) if kind == "rel" else tol
    return bool(np.all(np.abs(c - r) <= bound))


def _dataset_ok(mode: str, conditions: dict) -> tuple[bool, str]:
    if not conditions.get("config_matches_reference"):
        return False, "analysis config differs from the reference config"
    if conditions.get("kp8_deck_matches_reference") is not True:
        return False, "kp8 deck differs from (or could not be matched to) the reference deck"
    if mode != "kp8" and conditions.get("case04_deck_matches_reference") is not True:
        return False, "single-band case04 deck differs from the reference deck"
    return True, ""


def validate(summaries: dict[str, dict], reference_path: Path, conditions: dict) -> dict:
    reference = json.loads(Path(reference_path).read_text(encoding="utf-8"))
    results = []
    for mode, checks in reference["modes"].items():
        if mode not in summaries:
            results.append({"mode": mode, "id": "*", "category": "*", "status": "NOT RUN",
                            "detail": "inputs for this mode were not available"})
            continue
        s = summaries[mode]
        ok_data, why = _dataset_ok(mode, conditions)
        for chk in checks:
            category = chk.get("category", "reference")
            row = {"mode": mode, "id": chk["id"], "category": category, "kind": chk["kind"], "reference": chk["value"],
                   "tolerance": chk.get("tol"), "source": chk["source"]}
            if category != "consistency" and not ok_data:
                results.append({**row, "status": "NOT APPLICABLE", "detail": why})
                continue
            try:
                computed = EXTRACT[chk["id"]](s)
            except (KeyError, TypeError, ZeroDivisionError) as exc:
                computed, row["error"] = None, str(exc)
            results.append({**row, "computed": computed,
                            "status": "PASS" if _judge(chk["kind"], computed, chk["value"], chk.get("tol")) else "FAIL"})
    totals = {st: sum(r["status"] == st for r in results) for st in STATUSES}
    by_category = {}
    for r in results:
        by_category.setdefault(r["category"], {st: 0 for st in STATUSES})[r["status"]] += 1
    return {"reference_file": Path(reference_path).name, "reference_generated_utc": reference.get("generated_utc"),
            "dataset_conditions": conditions, "totals": totals, "by_category": by_category, "checks": results}


def markdown(report: dict) -> str:
    fmt = lambda v: json.dumps(v) if isinstance(v, (list, dict)) else ("%.10g" % v if isinstance(v, float) else str(v))
    t = report["totals"]
    lines = ["# Validation against pre-existing Demo 26 references", "",
             f"PASS {t['PASS']} | FAIL {t['FAIL']} | NOT APPLICABLE {t['NOT APPLICABLE']} | NOT RUN {t['NOT RUN']}", "",
             "| category | PASS | FAIL | NOT APPLICABLE |", "|---|---:|---:|---:|"]
    lines += [f"| {c} | {v['PASS']} | {v['FAIL']} | {v['NOT APPLICABLE']} |" for c, v in report["by_category"].items()]
    lines += ["", f"Dataset conditions: `{json.dumps(report['dataset_conditions'])}`", "",
              "| mode | category | check | status | computed | reference | tol | source |", "|---|---|---|---|---|---|---|---|"]
    for r in report["checks"]:
        lines.append(f"| {r['mode']} | {r['category']} | {r['id']} | **{r['status']}** | {fmt(r.get('computed'))[:60]} | "
                     f"{fmt(r.get('reference'))[:60]} | {fmt(r.get('tolerance'))} | {r.get('source', '')} |")
    return "\n".join(lines) + "\n"
