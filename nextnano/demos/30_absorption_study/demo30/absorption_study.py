"""30C — chi1 and linear absorption at the fundamental (w) and second harmonic (2w).

Four variants, all from the same raw data, Gamma and k grid as the chi2 control:

    consistent_2x2 / strict        PRIMARY: the Eq. 2 states, stored k nodes to 0.1·π/a
    consistent_2x2 / tail          + analytical continuation of Im chi1 beyond k_max
    expanded_bound_states / strict every saved bound single-band pair (sensitivity model)
    expanded_bound_states / tail   the same plus the analytical continuation

The expanded model is a SENSITIVITY comparison, not an upper bound. It still omits light
holes, the continuum, k-dependent matrix elements and full 8-band optics.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import absorption as ab
from . import bound_states as bs
from . import chi1 as c1
from . import rawdata
from .artifacts import write_json
from .config import background_index
from .meta import run_metadata, write_csv

MODELS = ("consistent_2x2", "expanded_bound_states")
KINDS = ("strict", "tail")


def variant_names():
    return [f"{m}__{k}" for m in MODELS for k in KINDS]


def pair_sets(state: dict, slope_scale: float = 1.0) -> dict:
    inp = state["inputs"]
    root = state["runs"]["singleband"].parser_root
    states, edges = bs.read_states(root), bs.band_edges(root)
    tracked = c1.pairs_2x2(inp)
    k = np.asarray(inp["k_per_nm"], float)
    mean_slope = float(np.mean([(p.transition_eV[-1] - p.transition_eV[0]) / k[-1] ** 2 for p in tracked]))
    expanded = bs.expanded_pairs(tracked, states, edges, k, slope_scale * mean_slope)
    return {"consistent_2x2": tracked, "expanded_bound_states": expanded, "states": states, "edges": edges,
            "extra_pair_slope_eV_nm2": slope_scale * mean_slope, "mean_tracked_slope_eV_nm2": mean_slope}


def compute(state: dict, slope_scale: float = 1.0) -> dict:
    """chi1 and alphas for all variants on the control wavelength grid."""
    cfg, s, wl = state["cfg"], state["settings"], state["wl"]
    fit = cfg["chi1"]["tail"]["fit_last_fraction_of_k_nodes"]
    nb = background_index(cfg)
    e_w = ab.HC_EV_NM / wl
    e_2w = 2 * e_w
    sets = pair_sets(state, slope_scale)
    k = state["inputs"]["k_per_nm"]
    res = {"wavelength_nm": wl, "E_w_eV": e_w, "E_2w_eV": e_2w, "background_index": nb, "sets": sets,
           "chi1": {}, "alpha_E_w": {}, "alpha_E_2w": {}, "alpha_I_w": {}, "alpha_I_2w": {}, "tail_slopes": {}}
    for model in MODELS:
        at_w = c1.evaluate(e_w, sets[model], k, s, fit)
        at_2w = c1.evaluate(e_2w, sets[model], k, s, fit)
        res["tail_slopes"][model] = dict(zip(at_2w.labels, at_2w.tail_slopes))
        res["chi1"][model] = {"w": at_w, "2w": at_2w}
        for kind in KINDS:
            name = f"{model}__{kind}"
            chi_w, chi_2w = getattr(at_w, kind), getattr(at_2w, kind)
            res["alpha_E_w"][name] = ab.alpha_E(chi_w, e_w, nb["n_omega"], s.gamma_sign)
            res["alpha_E_2w"][name] = ab.alpha_E(chi_2w, e_2w, nb["n_2omega"], s.gamma_sign)
            res["alpha_I_w"][name] = 2 * res["alpha_E_w"][name]
            res["alpha_I_2w"][name] = 2 * res["alpha_E_2w"][name]
    onset = bs.continuum_onset(sets["states"], sets["edges"])
    res["onset"] = onset
    res["validity_min_fundamental_nm"] = 2 * ab.HC_EV_NM / onset["onset_eV"]
    res["strict_trust"] = strict_trust_limit(sets["consistent_2x2"], s)
    return res


def strict_trust_limit(pairs, s, min_overlap_sq: float = 0.01, margin_gammas: float = 3.0) -> dict:
    """Shortest fundamental wavelength at which the STRICT 0.1·π/a absorption is not truncated.

    Each stored pair only absorbs up to T(k_max). Above that SH energy the strict result
    loses the pair's plateau (a k-cutoff artifact). Require the SH photon energy to stay
    margin_gammas * Gamma below the lowest T(k_max) of any pair with |O|^2 >= min_overlap_sq.
    """
    relevant = [p for p in pairs if p.overlap_sq[0] >= min_overlap_sq]
    edge = min(float(p.transition_eV[-1]) for p in relevant)
    limit_eV = edge - margin_gammas * s.gamma_eV
    return {"lowest_truncated_edge_eV": edge, "pair": min(relevant, key=lambda p: p.transition_eV[-1]).label,
            "margin_gammas": margin_gammas, "min_overlap_sq": min_overlap_sq,
            "min_fundamental_nm": 2 * ab.HC_EV_NM / limit_eV}


def _intervals(wl, mask) -> list[list[float]]:
    """Contiguous wavelength intervals where mask is true."""
    idx = np.flatnonzero(mask)
    if not len(idx):
        return []
    groups = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    return [[float(wl[g[0]]), float(wl[g[-1]])] for g in groups]


def _window(res, cfg):
    wl = res["wavelength_nm"]
    lo = max(res["validity_min_fundamental_nm"], cfg["windows"]["measured_fundamental_nm"][0])
    return (wl >= lo) & (wl <= cfg["windows"]["measured_fundamental_nm"][1])


def quantify(res: dict, cfg: dict, state: dict) -> dict:
    """The explicit strict-vs-tail and 2x2-vs-expanded comparisons, plus the validity checks."""
    wl, win = res["wavelength_nm"], _window(res, cfg)
    table_wl = cfg["windows"]["table_wavelengths_nm"]
    idx = [int(np.argmin(np.abs(wl - x))) for x in table_wl]
    a2 = {k: ab.per_cm(v) for k, v in res["alpha_I_2w"].items()}
    out = {"window_nm": [float(wl[win][0]), float(wl[win][-1])], "window_rule":
           "measured window 1400-1800 nm intersected with the validity window (SH below the bound-to-continuum onset)"}
    tail_vs_strict = {}
    for model in MODELS:
        strict, tail = a2[f"{model}__strict"], a2[f"{model}__tail"]
        rel = (tail - strict) / tail
        tail_vs_strict[model] = {
            "max_relative_difference_in_window": float(np.max(rel[win])),
            "at_wavelength_nm": float(wl[win][np.argmax(rel[win])]),
            "intervals_where_tail_exceeds_strict_by_1pct_nm": _intervals(wl, win & (rel > 0.01)),
            "intervals_where_tail_exceeds_strict_by_10pct_nm": _intervals(wl, win & (rel > 0.10)),
            "note": "relative differences far below the absorption edge (1700-1800 nm) are large but alpha is tiny there; "
                    "the effect on the SH (30D |A|^2) is the physically relevant measure",
            "table": {f"{table_wl[j]:.0f}": {"strict_cm-1": float(strict[i]), "tail_cm-1": float(tail[i]),
                                             "relative_difference": float(rel[i])} for j, i in enumerate(idx)}}
    out["alpha_I_2w_tail_vs_strict"] = tail_vs_strict
    expanded_vs_2x2 = {}
    for kind in KINDS:
        ratio = a2[f"expanded_bound_states__{kind}"] / a2[f"consistent_2x2__{kind}"]
        expanded_vs_2x2[kind] = {"ratio_min_in_window": float(np.min(ratio[win])), "ratio_max_in_window": float(np.max(ratio[win])),
                                 "at_max_nm": float(wl[win][np.argmax(ratio[win])]),
                                 "table_ratio": {f"{table_wl[j]:.0f}": float(ratio[i]) for j, i in enumerate(idx)}}
    out["alpha_I_2w_expanded_vs_2x2"] = expanded_vs_2x2
    # fundamental absorption: is alpha_w ~ 0 justified over the measured window?
    l80 = cfg["samples"]["fig2d_sample_periods"] * cfg["samples"]["period_nm"] * 1e-9
    worst = {name: float(np.max(v[win]) * l80) for name, v in res["alpha_E_w"].items()}
    thr = cfg["windows"]["alpha_omega_negligible_if_alphaE_L_below"]
    out["alpha_w_check"] = {"max_alphaE_w_times_L80_by_variant": worst, "threshold": thr,
                            "PASS": bool(max(worst.values()) < thr),
                            "note": "Lorentzian (5 meV) tails of sub-gap transitions; real absorption edges fall faster, so this is an upper bound"}
    # sanity: absorbed fraction per 30 nm period on the e1-hh1 plateau (2x2 strict)
    s = state["settings"]
    t11 = res["sets"]["consistent_2x2"][0].transition_eV[0]
    e_probe = t11 + 0.05
    chi_probe = c1.evaluate(np.array([e_probe]), res["sets"]["consistent_2x2"], state["inputs"]["k_per_nm"], s,
                            cfg["chi1"]["tail"]["fit_last_fraction_of_k_nodes"]).strict
    a_probe = ab.alpha_I(chi_probe, np.array([e_probe]), res["background_index"]["n_2omega"], s.gamma_sign)[0]
    frac = float(1 - np.exp(-a_probe * s.period_nm * 1e-9))
    out["plateau_absorption_per_period"] = {"photon_energy_eV": float(e_probe), "alpha_I_cm-1": float(a_probe / 100),
                                            "absorbed_fraction_per_30nm_period": frac, "sanity_band": [0.003, 0.03],
                                            "PASS": bool(0.003 <= frac <= 0.03),
                                            "note": "single GaAs QWs absorb roughly 0.5-1% per well for HH TE light; a factor of ~2 above is plausible "
                                                    "if r_e,hh = 0.751 nm is the full |<S|x|X>| rather than the heavy-hole in-plane projection"}
    # resonance positions: each strong 2x2 pair's absorption onset sits at its T(0). The onset
    # of a broadened step is where dIm/dE peaks. A half-height test would assume a flat
    # plateau, and the tracked e2-hh2 joint density of states is ~2x larger at its edge
    # (its hh2 dispersion is flat near k = 0), so half-height offsets are kept only as information.
    align = {}
    for pair in res["sets"]["consistent_2x2"]:
        if pair.overlap_sq[0] < 0.1:
            continue
        t0 = float(pair.transition_eV[0])
        grid = np.linspace(t0 - 5 * s.gamma_eV, t0 + 10 * s.gamma_eV, 6001)
        im = -s.gamma_sign * np.imag(c1.strict_terms(grid, [pair], state["inputs"]["k_per_nm"], s)[0])
        onset = float(grid[np.argmax(np.gradient(im, grid))])
        e_half = float(np.interp(0.5 * im[-1], im[:4000], grid[:4000]))
        align[pair.label] = {"T0_eV": t0, "onset_dIm_dE_peak_eV": onset, "onset_offset_meV": 1e3 * (onset - t0),
                             "half_height_offset_meV_info": 1e3 * (e_half - t0),
                             "edge_to_10Gamma_ratio_info": float(np.interp(t0, grid, im) / im[-1]),
                             "PASS": abs(onset - t0) < s.gamma_eV / 2}
    out["resonance_alignment"] = align
    return out


def run(state: dict, out: Path) -> dict:
    cfg = state["cfg"]
    res = compute(state)
    out = Path(out)
    wl = res["wavelength_nm"]
    names = variant_names()
    cols, head = [wl, res["E_w_eV"], res["E_2w_eV"]], ["wavelength_nm", "E_w_eV", "E_2w_eV"]
    for model in MODELS:
        cols += [res["chi1"][model]["w"].strict.real, res["chi1"][model]["2w"].strict.real]
        head += [f"re_chi1_w__{model}__strict", f"re_chi1_2w__{model}__strict"]
        for kind in KINDS:
            cols += [getattr(res["chi1"][model]["w"], kind).imag, getattr(res["chi1"][model]["2w"], kind).imag]
            head += [f"im_chi1_w__{model}__{kind}", f"im_chi1_2w__{model}__{kind}"]
    write_csv(out / "chi1_spectra.csv", head, cols)
    cols, head = [wl], ["wavelength_nm"]
    for name in names:
        for key, label in (("alpha_E_w", "alphaE_w"), ("alpha_I_w", "alphaI_w"), ("alpha_E_2w", "alphaE_2w"), ("alpha_I_2w", "alphaI_2w")):
            cols.append(ab.per_cm(res[key][name]))
            head.append(f"{label}_cm-1__{name}")
        cols += [ab.length_um(res["alpha_I_2w"][name]), ab.length_um(res["alpha_I_w"][name])]
        head += [f"absorption_length_I_2w_um__{name}", f"absorption_length_I_w_um__{name}"]
    write_csv(out / "absorption.csv", head, cols)
    q = quantify(res, cfg, state)
    # sensitivity of the expanded model to the assumed slope of its extra (untracked) pairs
    sens = {}
    for scale in cfg["chi1"]["expanded_bound_states"]["extra_pair_slope_sensitivity"]:
        alt = compute(state, slope_scale=scale)
        win = _window(alt, cfg)
        ratio = alt["alpha_I_2w"]["expanded_bound_states__tail"] / res["alpha_I_2w"]["expanded_bound_states__tail"]
        sens[f"slope_x{scale}"] = {"alpha_I_2w_ratio_min": float(np.min(ratio[win])), "alpha_I_2w_ratio_max": float(np.max(ratio[win]))}
    sets = res["sets"]
    meta = run_metadata("30C_chi1_absorption", rawdata.provenance(state["runs"]), {
        "chi1_prefactor_C1_V": c1.chi1_prefactor(state["settings"]),
        "background_index": res["background_index"],
        "variants": {"consistent_2x2": [p.label for p in sets["consistent_2x2"]],
                     "expanded_bound_states": [{"pair": p.label, "T0_eV": float(p.transition_eV[0]), "O2": float(p.overlap_sq[0]),
                                                "dispersion": p.dispersion} for p in sets["expanded_bound_states"]]},
        "extra_pair_slope_eV_nm2": sets["extra_pair_slope_eV_nm2"], "tail_slopes_eV_nm2": res["tail_slopes"],
        "band_edges": sets["edges"], "continuum_onset": res["onset"],
        "validity_min_fundamental_nm": res["validity_min_fundamental_nm"],
        "strict_cutoff_trust_limit": res["strict_trust"],
        "edge_probability_0p5nm": bs.edge_probability(sets["states"]),
        "comparisons": q, "expanded_slope_sensitivity": sens,
        "conventions": {"alpha_E": "field: E(z) = E0 exp(-alpha_E z)", "alpha_I": "intensity: I(z) = I0 exp(-alpha_I z) = 2 alpha_E",
                        "sign": "alpha_E = (w/2nc)(-gamma_sign) Im chi1; Eq. 2 convention gamma_sign = +1",
                        "tail": "analytical approximation / continuation of Im chi1 beyond k_max; Re chi1 kept strict"},
        "validation_status": "PASS" if q["alpha_w_check"]["PASS"] and all(v["PASS"] for v in q["resonance_alignment"].values()) else "FAIL"})
    write_json(out / "metadata.json", meta)
    res["meta"] = meta
    return res
