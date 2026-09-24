"""30D — 1994 Eq. 5 absorption factor and SH transfer for the measured samples.

Main case: the 80-period sample of Fig. 2d (L = 80 x 30 nm = 2.4 um). The 4-, 12- and
16-period samples are evaluated too, mainly for the 1550 nm table. Phase mismatch is only
estimated (coherence length) and is NOT applied; it belongs to Demo 31.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import propagation as pr
from . import rawdata
from .absorption import HC_EV_NM
from .absorption_study import MODELS, KINDS, variant_names
from .artifacts import write_json
from .meta import run_metadata, write_csv


def lengths_m(cfg) -> dict:
    period = cfg["samples"]["period_nm"] * 1e-9
    return {int(n): n * period for n in cfg["samples"]["periods"]}


def run(state: dict, absorption_res: dict, out: Path) -> dict:
    cfg = state["cfg"]
    out = Path(out)
    wl = absorption_res["wavelength_nm"]
    valid = wl >= absorption_res["validity_min_fundamental_nm"]
    lengths = lengths_m(cfg)
    main_n = cfg["samples"]["fig2d_sample_periods"]
    factors = {name: {n: pr.absorption_factor(absorption_res["alpha_E_w"][name], absorption_res["alpha_E_2w"][name], L)
                      for n, L in lengths.items()} for name in variant_names()}
    cols, head = [wl, valid.astype(float)], ["wavelength_nm", "within_validity_window"]
    for n in lengths:
        for name in variant_names():
            cols.append(np.abs(factors[name][n]) ** 2)
            head.append(f"A2__{n}periods__{name}")
    write_csv(out / "absorption_factor.csv", head, cols)
    # SH transfer |E_2w(L)|/|E_w(0)|^2 (m/V) for the Fig. 2d sample: transparent and absorptive
    chi2 = state["chi2"].chi2_complex
    e_w = HC_EV_NM / wl
    n2 = absorption_res["background_index"]["n_2omega"]
    L = lengths[main_n]
    transparent = pr.sh_transfer_m_per_V(chi2, e_w, n2, L, 1.0)
    cols, head = [wl, valid.astype(float), transparent], ["wavelength_nm", "within_validity_window", "transparent_m_per_V"]
    for name in variant_names():
        cols.append(pr.sh_transfer_m_per_V(chi2, e_w, n2, L, factors[name][main_n]))
        head.append(f"absorptive_m_per_V__{name}")
    write_csv(out / f"sh_transfer_{main_n}periods.csv", head, cols)
    # table at the selected wavelengths
    table = {}
    for lam in cfg["windows"]["table_wavelengths_nm"]:
        i = int(np.argmin(np.abs(wl - lam)))
        table[f"{lam:.0f}"] = {"within_validity_window": bool(valid[i]),
                               **{name: {str(n): float(np.abs(factors[name][n][i]) ** 2) for n in lengths} for name in variant_names()}}
    i1550 = int(np.argmin(np.abs(wl - 1550.0)))
    paper = cfg["samples"]["paper_effective_chi2_at_1550nm_pm_per_V"]
    at1550 = {str(n): {"paper_effective_chi2_pm_per_V": paper[str(n)],
                       "A_field__consistent_2x2__strict": float(np.abs(factors["consistent_2x2__strict"][n][i1550])),
                       "A2_intensity__consistent_2x2__strict": float(np.abs(factors["consistent_2x2__strict"][n][i1550]) ** 2),
                       "A_field__expanded_bound_states__tail": float(np.abs(factors["expanded_bound_states__tail"][n][i1550])),
                       "conditional_note": "IF an extraction ignored MQW absorption, the inferred chi2_eff would be low by the "
                                           "field factor |A| (it scales as sqrt of the SH intensity)"} for n in lengths}
    # strict vs tail and 2x2 vs expanded, measured in the SH suppression of the Fig. 2d sample
    win = valid & (wl >= cfg["windows"]["measured_fundamental_nm"][0]) & (wl <= cfg["windows"]["measured_fundamental_nm"][1])
    a2 = {name: np.abs(factors[name][main_n]) ** 2 for name in variant_names()}
    compare = {
        "tail_minus_strict__consistent_2x2": {"max_abs_in_window": float(np.max(np.abs(a2["consistent_2x2__tail"] - a2["consistent_2x2__strict"])[win])),
                                             "at_nm": float(wl[win][np.argmax(np.abs(a2["consistent_2x2__tail"] - a2["consistent_2x2__strict"])[win])])},
        "tail_minus_strict__expanded": {"max_abs_in_window": float(np.max(np.abs(a2["expanded_bound_states__tail"] - a2["expanded_bound_states__strict"])[win]))},
        "expanded_over_2x2__strict": {"min_in_window": float(np.min((a2["expanded_bound_states__strict"] / a2["consistent_2x2__strict"])[win]))},
        "expanded_over_2x2__tail": {"min_in_window": float(np.min((a2["expanded_bound_states__tail"] / a2["consistent_2x2__tail"])[win]))},
        "window_nm": [float(wl[win][0]), float(wl[win][-1])]}
    # validation of the closed form against numerical integration at the table wavelengths
    worst = 0.0
    for name in ("consistent_2x2__strict", "expanded_bound_states__tail"):
        for lam in cfg["windows"]["table_wavelengths_nm"]:
            i = int(np.argmin(np.abs(wl - lam)))
            a1, a2_ = float(absorption_res["alpha_E_w"][name][i]), float(absorption_res["alpha_E_2w"][name][i])
            closed = float(factors[name][main_n][i])
            for other in (pr.absorption_factor_ode(a1, a2_, L), pr.absorption_factor_overlap(a1, a2_, L)):
                worst = max(worst, abs(other - closed) / closed)
    nb = absorption_res["background_index"]
    coh = pr.coherence_length(1550.0, nb["n_omega"], nb["n_2omega"], L)
    meta = run_metadata("30D_propagation", rawdata.provenance(state["runs"]), {
        "model": "1994 Eq. 5: phase matched, undepleted pump, uniform slab of period-averaged absorption",
        "sample_lengths_um": {str(n): L_ * 1e6 for n, L_ in lengths.items()}, "fig2d_sample_periods": main_n,
        "period_note": cfg["samples"]["period_note"], "path_length_rule": cfg["samples"]["path_length_rule"],
        "validity_min_fundamental_nm": absorption_res["validity_min_fundamental_nm"],
        "table_A2_intensity_factor": table, "at_1550nm": at1550, "comparisons_in_A2": compare,
        "closed_form_vs_numerical_max_relative_difference": worst,
        "phase_mismatch_estimate_NOT_APPLIED": {**coh, "note": "background TE effective indices of the MQW stack at 1550/775 nm; "
                                                               "Demo 30 keeps 1994 Eq. 5's phase-matching assumption; Demo 31 treats this properly"},
        "validation_status": "PASS" if worst < 1e-7 else "FAIL"})
    write_json(out / "metadata.json", meta)
    return {"factors": factors, "transparent_m_per_V": transparent, "lengths_m": lengths, "meta": meta,
            "wavelength_nm": wl, "valid": valid}
