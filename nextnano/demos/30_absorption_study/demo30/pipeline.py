"""Demo 30 pipeline: 30A inputs -> 30B chi2 control -> 30C chi1/absorption -> 30D propagation -> 30E comparison."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import absorption as ab
from . import absorption_study, baseline, comparison, extension, plotting, propagation_study, rawdata
from .artifacts import write_json
from .meta import run_metadata, sha256_bytes
from .paths import OUTPUTS, PLOTS, REFERENCE


def inputs_report(state: dict, out: Path) -> dict:
    """30A: full verification of every locked raw package and of the reference data."""
    runs = state["runs"]
    packages = {role: {"run_id": r.run_id, **rawdata.verify_package(r.folder)} for role, r in runs.items()}
    refs = {p.name: sha256_bytes(p) for p in sorted(REFERENCE.glob("*")) if p.is_file()}
    meta = run_metadata("30A_inputs", rawdata.provenance(runs), {
        "raw_packages_full_verification": packages, "reference_files_sha256": refs,
        "validation_status": "PASS" if all(p["result"] == "PASS" for p in packages.values()) else "FAIL"})
    write_json(Path(out) / "metadata.json", meta)
    return meta


def summary(b, a, p, e, inputs) -> dict:
    cfg = b["cfg"]
    wl = a["wavelength_nm"]
    i1550 = int(np.argmin(np.abs(wl - 1550.0)))
    return {
        "status": {"30A": inputs["validation_status"], "30B": b["meta"]["validation_status"],
                   "30C": a["meta"]["validation_status"], "30D": p["meta"]["validation_status"],
                   "30E": e["meta"]["validation_status"]},
        "control_k_max": "0.1·π/a = 0.555714439232 nm^-1",
        "alpha_I_2w_at_1550nm_cm-1": {k: float(ab.per_cm(v[i1550])) for k, v in a["alpha_I_2w"].items()},
        "alpha_I_w_at_1550nm_cm-1": {k: float(ab.per_cm(v[i1550])) for k, v in a["alpha_I_w"].items()},
        "validity_min_fundamental_nm": a["validity_min_fundamental_nm"],
        "strict_cutoff_trust_min_fundamental_nm": a["strict_trust"]["min_fundamental_nm"],
        "absorption_comparisons": a["meta"]["comparisons"],
        "A2_table": p["meta"]["table_A2_intensity_factor"], "at_1550nm": p["meta"]["at_1550nm"],
        "phase_mismatch_estimate_NOT_APPLIED": p["meta"]["phase_mismatch_estimate_NOT_APPLIED"],
        "comparison_B": {"window_nm": e["meta"]["comparison_window_nm"], "metrics": e["meta"]["metrics_at_measured_points"],
                         "peaks_nm": e["meta"]["peak_wavelengths_nm"], "absorption_induced_peak_shift_nm": e["meta"]["absorption_induced_peak_shift_nm"]},
        "comparison_A": b["meta"]["comparison_A"],
        "config_note": cfg["baseline_chi2"]["note"]}


def run_all(out: Path = OUTPUTS, raw_root=None, make_plots: bool = True, plots_dir: Path = PLOTS) -> dict:
    out, plots_dir = Path(out), Path(plots_dir)
    b = baseline.run(out / "30B_chi2_baseline", raw_root)
    if b["meta"]["validation_status"] != "PASS":
        raise RuntimeError("30B control does not reproduce Demo 28A; stopping before any new physics")
    inputs = inputs_report(b, out / "30A_inputs")
    a = absorption_study.run(b, out / "30C_chi1_absorption")
    p = propagation_study.run(b, a, out / "30D_propagation")
    e = comparison.run(b, a, p, out / "30E_paper_comparison")
    s = summary(b, a, p, e, inputs)
    f = extension.run(b, a, e, out / "30F_k_extension", raw_root)  # optional; absent runs are reported, never faked
    s["status"]["30F (optional)"] = f["meta"]["validation_status"]
    s["k_extensions"] = {"status": f["meta"]["extensions"], "results": f["meta"]["results"]}
    write_json(out / "summary.json", s)
    if make_plots:
        plots_dir.mkdir(parents=True, exist_ok=True)
        trust = a["strict_trust"]["min_fundamental_nm"]
        plotting.chi2_vs_paper(plots_dir / "30B_chi2_vs_paper_simulation.png", b, b["meta"]["comparison_A"])
        plotting.absorption_coefficients(plots_dir / "30C_absorption_coefficients.png", a, b["cfg"], trust)
        plotting.absorption_factor(plots_dir / "30D_absorption_factor.png", p, a, b["cfg"], trust)
        plotting.fig2d_comparison(plots_dir / "30E_fig2d_comparison.png", b, e, b["cfg"])
        plotting.chi1_diagnostic(plots_dir / "30C_diagnostic_chi1_re_im.png", a, b)
    return s["status"]
