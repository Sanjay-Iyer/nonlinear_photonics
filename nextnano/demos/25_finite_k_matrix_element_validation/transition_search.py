"""Search the extended state set for an optically relevant ~2.296 eV transition.

Demo 24 showed the paper's P1 (540 nm) and P3 (1080 nm) form an exact
one-photon/two-photon pair of a single 2.296 eV transition, and that no pair of
*bound* subbands in this structure can reach it: the barrier gap is 2.145 eV,
so a bound-bound transition is capped there. Demo 25 tests that claim against a
much larger solved state set, including states above the barrier edge.

The decisive rule, stated in the module because it is easy to get wrong: an
energy match alone is not an explanation. A candidate must also carry optical
weight, so every candidate is scored on envelope overlap and oscillator
strength, and any candidate involving an unconfined state is flagged as a
Dirichlet box state whose energy depends on the quantum-region width.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

import numpy as np

HC_EV_NM = 1239.841984


def one_photon_nm(energy_eV: float) -> float:
    return HC_EV_NM / float(energy_eV)


def two_photon_nm(energy_eV: float) -> float:
    return 2.0 * HC_EV_NM / float(energy_eV)


def bound_bound_ceiling(barrier_conduction_edge_eV: float,
                        barrier_valence_edge_eV: float) -> float:
    """The largest transition any bound pair can reach: the barrier gap."""
    return float(barrier_conduction_edge_eV) - float(barrier_valence_edge_eV)


def search(states_by_k: Sequence[Mapping[str, Any]], *, target_eV: float,
           tolerance_eV: float, barrier_conduction_edge_eV: float,
           barrier_valence_edge_eV: float) -> list[dict[str, Any]]:
    """All electron-hole pairs within ``tolerance_eV`` of ``target_eV``.

    ``states_by_k`` entries carry: k_index, k_per_nm, and a ``states`` list of
    dicts with label, energy_eV, dominant_band, confined, fractions, plus the
    optional ``overlap`` and ``oscillator_strength`` maps keyed by partner label.
    """
    ceiling = bound_bound_ceiling(barrier_conduction_edge_eV, barrier_valence_edge_eV)
    rows: list[dict[str, Any]] = []
    for entry in states_by_k:
        states = list(entry["states"])
        electrons = [s for s in states if str(s["dominant_band"]) == "CB"]
        holes = [s for s in states if str(s["dominant_band"]) in ("HH", "LH", "SO")]
        for e in electrons:
            for h in holes:
                delta = float(e["energy_eV"]) - float(h["energy_eV"])
                if abs(delta - float(target_eV)) > float(tolerance_eV):
                    continue
                both_bound = bool(e.get("confined", False)) and bool(h.get("confined", False))
                overlap = float((e.get("overlap") or {}).get(str(h["label"]), float("nan")))
                strength = float((e.get("oscillator_strength") or {}).get(str(h["label"]), float("nan")))
                rows.append({
                    "k_index": entry["k_index"], "k_per_nm": entry.get("k_per_nm", float("nan")),
                    "electron_state": e["label"], "hole_state": h["label"],
                    "transition_energy_eV": delta,
                    "detuning_from_target_meV": 1000.0 * (delta - float(target_eV)),
                    "one_photon_nm": one_photon_nm(delta), "two_photon_nm": two_photon_nm(delta),
                    "electron_CB_fraction": float((e.get("fractions") or {}).get("CB", float("nan"))),
                    "hole_HH_fraction": float((h.get("fractions") or {}).get("HH", float("nan"))),
                    "hole_LH_fraction": float((h.get("fractions") or {}).get("LH", float("nan"))),
                    "electron_confined": bool(e.get("confined", False)),
                    "hole_confined": bool(h.get("confined", False)),
                    "both_bound": both_bound,
                    "envelope_overlap": overlap,
                    "oscillator_strength": strength,
                    "exceeds_bound_bound_ceiling": bool(delta > ceiling),
                    "bound_bound_ceiling_eV": ceiling,
                })
    return rows


def score_optical_relevance(rows: Iterable[Mapping[str, Any]], *,
                            min_overlap_fraction: float,
                            min_oscillator_fraction: float,
                            reference_overlap: float | None = None,
                            reference_oscillator: float | None = None) -> list[dict[str, Any]]:
    """Add a verdict to every candidate. Energy alone never earns EXPLAINS_P1_P3."""
    items = [dict(r) for r in rows]
    if not items:
        return items
    overlaps = [abs(float(r["envelope_overlap"])) for r in items
                if np.isfinite(r.get("envelope_overlap", np.nan))]
    strengths = [abs(float(r["oscillator_strength"])) for r in items
                 if np.isfinite(r.get("oscillator_strength", np.nan))]
    ref_o = float(reference_overlap) if reference_overlap else (max(overlaps) if overlaps else 0.0)
    ref_f = float(reference_oscillator) if reference_oscillator else (max(strengths) if strengths else 0.0)
    for row in items:
        overlap = abs(float(row.get("envelope_overlap", float("nan"))))
        strength = abs(float(row.get("oscillator_strength", float("nan"))))
        row["overlap_fraction_of_reference"] = overlap / ref_o if ref_o > 0 else float("nan")
        row["oscillator_fraction_of_reference"] = strength / ref_f if ref_f > 0 else float("nan")
        strong_overlap = np.isfinite(overlap) and ref_o > 0 and overlap / ref_o >= min_overlap_fraction
        strong_osc = np.isfinite(strength) and ref_f > 0 and strength / ref_f >= min_oscillator_fraction
        measured = np.isfinite(overlap) or np.isfinite(strength)
        if not measured:
            row["verdict"] = "UNSCORED - no overlap or oscillator strength available"
        elif not (strong_overlap or strong_osc):
            row["verdict"] = ("ENERGY MATCH ONLY - optically negligible, so it does not "
                              "explain P1/P3")
        elif not row["both_bound"]:
            row["verdict"] = ("OPTICALLY RELEVANT BUT UNBOUND - a Dirichlet box state whose "
                              "energy depends on the quantum-region width; not a physical "
                              "explanation without a wider-domain check")
        else:
            row["verdict"] = "CANDIDATE EXPLAINS P1/P3 - bound pair with real optical weight"
        row["optically_relevant"] = bool(strong_overlap or strong_osc)
    return items


def conclusion(scored: Sequence[Mapping[str, Any]], *, target_eV: float,
               ceiling_eV: float) -> dict[str, Any]:
    """The Demo 25 answer to 'is there a ~2.296 eV transition that matters?'"""
    explains = [r for r in scored if str(r.get("verdict", "")).startswith("CANDIDATE EXPLAINS")]
    unbound = [r for r in scored if str(r.get("verdict", "")).startswith("OPTICALLY RELEVANT BUT UNBOUND")]
    energy_only = [r for r in scored if str(r.get("verdict", "")).startswith("ENERGY MATCH ONLY")]
    if explains:
        best = max(explains, key=lambda r: abs(float(r.get("envelope_overlap", 0.0) or 0.0)))
        return {
            "found": True, "class": "bound_and_optically_relevant",
            "answer": (f"a bound {best['electron_state']}-{best['hole_state']} transition at "
                       f"{float(best['transition_energy_eV']):.4f} eV carries real optical weight; "
                       "state-space truncation is a live explanation for P1/P3"),
            "best": dict(best), "counts": {"explains": len(explains), "unbound": len(unbound),
                                           "energy_only": len(energy_only)},
        }
    if unbound:
        best = max(unbound, key=lambda r: abs(float(r.get("envelope_overlap", 0.0) or 0.0)))
        return {
            "found": True, "class": "unbound_only",
            "answer": (f"the only optically active candidates near {target_eV:.3f} eV involve "
                       "states outside the barrier gap, which with Dirichlet walls are box "
                       "states of the quantum region rather than physical bound subbands; this "
                       "does not establish a physical P1/P3 explanation"),
            "best": dict(best), "counts": {"explains": 0, "unbound": len(unbound),
                                           "energy_only": len(energy_only)},
        }
    return {
        "found": False, "class": "none",
        "answer": (f"no transition within tolerance of {target_eV:.3f} eV carries meaningful "
                   f"optical weight; the bound-bound ceiling in this structure is "
                   f"{ceiling_eV:.4f} eV, so Demo 24's exclusion stands and geometry/material "
                   "mismatch becomes the leading remaining explanation for P1/P3"),
        "best": None, "counts": {"explains": 0, "unbound": 0, "energy_only": len(energy_only)},
    }
