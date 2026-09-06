"""Demo 25 post-production analysis.

Runs only on real Professional output. Every entry point raises rather than
degrading: if the finite-k envelopes are not on disk there is no finite-k
result to report, and Demo 25 says so instead of quietly reusing k=0 data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from config25 import (DEMO23, DEMO24, Demo25Error, outputs_root, repo_path, results_root)

import finite_k_matrices as fkm  # noqa: E402
import kp8_finite_k_io as kio  # noqa: E402
import pilot_audit  # noqa: E402
import plotting25 as plotting  # noqa: E402
import progress as progress_mod  # noqa: E402
import reporting25 as reporting  # noqa: E402
import state_tracking25 as tracking  # noqa: E402
import transition_search as tsearch  # noqa: E402

# Demo 24 is appended, never inserted: see the note in finite_k_matrices.py.
if str(DEMO23) not in sys.path:
    sys.path.insert(0, str(DEMO23))
if str(DEMO24) not in sys.path:
    sys.path.append(str(DEMO24))


FEATURES = [
    {"name": "P1", "type": "peak", "wavelength_nm": 540.0, "window_nm": [490.0, 575.0]},
    {"name": "Z1", "type": "minimum", "wavelength_nm": 605.0, "window_nm": [550.0, 650.0]},
    {"name": "P2", "type": "peak", "wavelength_nm": 760.0, "window_nm": [680.0, 830.0]},
    {"name": "P3", "type": "peak", "wavelength_nm": 1080.0, "window_nm": [950.0, 1160.0]},
    {"name": "Z2", "type": "minimum", "wavelength_nm": 1330.0, "window_nm": [1250.0, 1400.0]},
    {"name": "P4", "type": "peak", "wavelength_nm": 1520.0, "window_nm": [1420.0, 1620.0]},
]


def production_case(cfg: Mapping[str, Any]) -> Path:
    root = results_root(cfg) / "raw" / "production"
    if not root.is_dir():
        raise Demo25Error(
            "no production output found. Demo 25 analysis needs a completed Professional "
            "run: python run_demo25.py --pilot, --pilot-audit, then --production.")
    cases = sorted(p for p in root.iterdir() if p.is_dir())
    if not cases:
        raise Demo25Error(f"{root} contains no production case directory")
    return cases[-1]


def band_edges(case: Path) -> dict[str, float]:
    matches = sorted(case.rglob("bandedges.dat"))
    if not matches:
        raise Demo25Error(f"bandedges.dat is absent under {case}; confinement cannot be classified")
    table = np.loadtxt(matches[0], skiprows=1)
    gamma, hh = table[:, 1], table[:, 2]
    barrier = int(np.argmax(gamma))
    well = int(np.argmin(gamma))
    return {"barrier_conduction_edge_eV": float(gamma[barrier]),
            "barrier_valence_edge_eV": float(hh[barrier]),
            "barrier_gap_eV": float(gamma[barrier] - hh[barrier]),
            "well_conduction_edge_eV": float(gamma[well]),
            "well_valence_edge_eV": float(hh[well])}


def load_series(case: Path) -> tuple[list[kio.KPointStates], np.ndarray]:
    """Every k point that has envelopes, in ascending k order."""
    energies = kio.read_energy_spectrum(case)
    vectors = kio.read_k_vectors(case)
    indices = sorted(kio.discover_k_points(case))
    if len(indices) < 2:
        raise Demo25Error(
            f"only {len(indices)} k point(s) carry envelopes under {case}. The production run did "
            "not deliver finite-k state output, so no finite-k M(k) result exists. Demo 25 does "
            "not substitute M(k)=M(0). Re-check the pilot gate settings.")
    series, k_values = [], []
    for index in indices:
        vector = None
        if vectors is not None and index < len(vectors):
            vector = np.asarray(vectors[index], dtype=float)
        series.append(kio.load_k_point(case, index, energies=energies, k_vector=vector))
        k_values.append(float(np.linalg.norm(vector[-3:])) if vector is not None else float(index))
    order = np.argsort(k_values)
    return [series[i] for i in order], np.asarray([k_values[i] for i in order])


def equation2_indices(tracked: Mapping[int, tracking.TrackedState]) -> tuple[list[int], list[int]]:
    """Solver indices for e1,e2 and hh1,hh2, by tracked label."""
    by_label = {state.label: state.state_index for state in tracked.values()}
    missing = [label for label in ("e1", "e2", "hh1", "hh2") if label not in by_label]
    if missing:
        raise Demo25Error(
            f"tracking did not identify {missing} at this k point; Equation 2 cannot be assembled "
            "without them. Inspect STATE_TRACKING.csv and TRACKING_EVENTS.csv.")
    return [by_label["e1"], by_label["e2"]], [by_label["hh1"], by_label["hh2"]]


def run(cfg: Mapping[str, Any], track: progress_mod.Tracker) -> dict[str, Any]:
    output = outputs_root(cfg)
    case = production_case(cfg)
    edges = band_edges(case)

    track.start("parse")
    series, k_values = load_series(case)
    track.finish("parse", note=f"{len(series)} k points with envelopes")

    track.start("tracking", units_total=len(series))
    labels = tracking.track(series, barrier_conduction_edge_eV=edges["barrier_conduction_edge_eV"],
                            barrier_valence_edge_eV=edges["barrier_valence_edge_eV"])
    for _ in series:
        track.advance("tracking")
    rows = tracking.rows(labels, k_values)
    events = tracking.detect_events(labels)
    reporting.write_csv(output / "STATE_TRACKING.csv", rows)
    reporting.write_csv(output / "TRACKING_EVENTS.csv", events)
    reporting.write_csv(output / "EXTENDED_STATE_ENERGIES.csv", [
        {"k_index": r["k_index"], "k_per_nm": r["k_per_nm"], "state": r["state"],
         "energy_eV": r["energy_eV"], "dominant_band": r["dominant_band"],
         "confined": r["confined"]} for r in rows])
    track.finish("tracking", note=f"{len(events)} tracking events flagged")

    track.start("transitions")
    entries = []
    for step, (states, mapping) in enumerate(zip(series, labels)):
        entries.append({"k_index": states.k_index, "k_per_nm": float(k_values[step]),
                        "states": [{"label": s.label, "energy_eV": s.energy_eV,
                                    "dominant_band": s.dominant_band, "confined": s.confined,
                                    "fractions": s.fractions} for s in mapping.values()]})
    _attach_optical_weights(series, labels, entries)
    search = cfg["transition_search"]
    candidates = tsearch.search(entries, target_eV=float(search["target_eV"]),
                                tolerance_eV=float(search["tolerance_eV"]),
                                barrier_conduction_edge_eV=edges["barrier_conduction_edge_eV"],
                                barrier_valence_edge_eV=edges["barrier_valence_edge_eV"])
    scored = tsearch.score_optical_relevance(
        candidates, min_overlap_fraction=float(search["min_overlap_fraction"]),
        min_oscillator_fraction=float(search["min_oscillator_strength_fraction"]))
    verdict = tsearch.conclusion(scored, target_eV=float(search["target_eV"]),
                                 ceiling_eV=edges["barrier_gap_eV"])
    reporting.write_csv(output / "EXTENDED_TRANSITION_SEARCH.csv", scored)
    reporting.write_json(output / "P1_P3_VERDICT.json", verdict)
    reporting.write_text(output / "P1_P3_RESONANCE_CANDIDATES.md", _candidates_report(
        scored, verdict, edges, float(search["target_eV"])))
    track.finish("transitions", note=verdict["answer"][:110])

    track.start("matrices", units_total=len(series))
    tables = []
    for states, mapping in zip(series, labels):
        electrons, holes = equation2_indices(mapping)
        tables.append(kio.matrix_element_table(states, electrons, holes))
        track.advance("matrices")
    matrices = fkm.assemble(tables, k_values)
    _write_matrix_tables(output, matrices)
    track.finish("matrices", note=f"O, z_e, z_hh at {len(tables)} k points")

    track.start("pathways")
    ratios = fkm.numerator_ratios(
        matrices, flag_fractions=[float(f) for f in cfg["analysis"]["matrix_variation_flag_fractions"]])
    reporting.write_csv(output / "FINITE_K_PATHWAY_NUMERATORS.csv", ratios)
    track.finish("pathways", note=f"{sum(1 for r in ratios if r['sign_change_vs_k'])} sign changes")

    track.start("chi2")
    spectra = _recompute(cfg, series, k_values, matrices, labels)
    reporting.write_json(output / "DEMO25_SPECTRUM_SUMMARY.json", spectra["summary"])
    reporting.write_csv(output / "DEMO25_FEATURE_SCORECARD.csv", spectra["scorecard"])
    track.finish("chi2", note="finite-k M(k) spectrum computed")

    track.start("figures")
    plotting.write_all(output / "figures", cfg, {
        "series": series, "k_values": k_values, "tracking": rows, "events": events,
        "candidates": scored, "matrices": matrices, "ratios": ratios, **spectra,
        "edges": edges}, dpi=int(cfg["outputs"]["dpi"]))
    track.finish("figures")

    track.start("report")
    reporting.write_text(output / "DEMO25_FINAL_REPORT.md",
                         _final_report(cfg, edges, rows, events, scored, verdict, ratios, spectra))
    track.finish("report")
    return {"verdict": verdict, "spectra": spectra["summary"]}


def _attach_optical_weights(series: Sequence[kio.KPointStates],
                            labels: Sequence[Mapping[int, tracking.TrackedState]],
                            entries: list[dict[str, Any]]) -> None:
    """Envelope overlap for every electron-hole pair, used for optical relevance."""
    for entry, states, mapping in zip(entries, series, labels):
        by_label = {s.label: s.state_index for s in mapping.values()}
        for record in entry["states"]:
            if str(record["dominant_band"]) != "CB":
                continue
            overlaps = {}
            for other in entry["states"]:
                if str(other["dominant_band"]) == "CB":
                    continue
                a, b = by_label[str(record["label"])], by_label[str(other["label"])]
                overlaps[str(other["label"])] = abs(kio.overlap(states, b, a))
            record["overlap"] = overlaps


def _write_matrix_tables(output: Path, matrices: fkm.FiniteKMatrices) -> None:
    def rows_for(block: np.ndarray, label: str, names: Sequence[str]) -> list[dict[str, Any]]:
        out = []
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                for index, k in enumerate(matrices.k_per_nm):
                    value = block[i, j, index]
                    base = block[i, j, 0]
                    out.append({"k_per_nm": float(k), label: f"{a}-{b}",
                                "real": float(value.real), "imag": float(value.imag),
                                "abs": float(abs(value)),
                                "ratio_to_k0": float(abs(value) / abs(base)) if abs(base) > 0 else float("nan")})
        return out

    reporting.write_csv(output / "FINITE_K_OVERLAPS.csv",
                        rows_for(matrices.overlap, "pair", ["e1", "e2"]))
    reporting.write_csv(output / "FINITE_K_ELECTRON_Z.csv",
                        rows_for(matrices.z_e_nm, "pair", ["e1", "e2"]))
    reporting.write_csv(output / "FINITE_K_HOLE_Z.csv",
                        rows_for(matrices.z_hh_nm, "pair", ["hh1", "hh2"]))


def _recompute(cfg: Mapping[str, Any], series: Sequence[kio.KPointStates],
               k_values: np.ndarray, matrices: fkm.FiniteKMatrices,
               labels: Sequence[Mapping[int, tracking.TrackedState]]) -> dict[str, Any]:
    """Equation 2 with finite-k M(k), against the M(k)=M(0) control."""
    import physics23  # noqa: PLC0415
    import signed_spectrum  # noqa: PLC0415

    cfg23 = cfg["_demo23_config"]
    settings = physics23.settings_from_config(cfg23)
    wavelength = physics23.wavelength_grid(cfg23)
    electron = np.zeros((2, len(series)))
    hole = np.zeros((2, len(series)))
    for step, mapping in enumerate(labels):
        by_label = {s.label: s.energy_eV for s in mapping.values()}
        electron[:, step] = [by_label["e1"], by_label["e2"]]
        hole[:, step] = [by_label["hh1"], by_label["hh2"]]
    finite = fkm.spectrum_with_finite_k(wavelength, k_values, electron, hole, matrices,
                                        settings=settings, broadening_meV=settings.broadening_meV)
    frozen = fkm.spectrum_with_frozen_matrices(wavelength, k_values, electron, hole, matrices,
                                               settings=settings, broadening_meV=settings.broadening_meV)
    paper_x, paper_y = _paper_curve(cfg)
    paper = np.interp(wavelength, paper_x, paper_y, left=np.nan, right=np.nan)
    scorecard = []
    for feature in FEATURES:
        lo, hi = feature["window_nm"]
        window = (wavelength >= lo) & (wavelength <= hi)
        local = np.flatnonzero(window)
        picker = np.argmax if feature["type"] == "peak" else np.argmin
        norm_f = signed_spectrum.normalize(finite.chi2)
        norm_z = signed_spectrum.normalize(frozen.chi2)
        i_f = int(local[picker(norm_f[window])])
        i_z = int(local[picker(norm_z[window])])
        paper_nm = float(feature["wavelength_nm"])
        improved = abs(wavelength[i_f] - paper_nm) < abs(wavelength[i_z] - paper_nm) - 1e-9
        scorecard.append({
            "Feature": feature["name"], "Paper_lambda": paper_nm,
            "Demo23D_lambda": float(wavelength[i_z]), "Demo25_lambda": float(wavelength[i_f]),
            "Paper_normalized_amplitude": float(np.interp(paper_nm, paper_x, paper_y)
                                                / max(np.max(paper_y), 1e-300)),
            "Demo23D_amplitude": float(norm_z[i_z]), "Demo25_amplitude": float(norm_f[i_f]),
            "Demo23D_amplitude_at_paper_nm": float(np.interp(paper_nm, wavelength, norm_z)),
            "Demo25_amplitude_at_paper_nm": float(np.interp(paper_nm, wavelength, norm_f)),
            "Improved?": "yes" if improved else "no",
            "Mechanism": "finite-k M(k) only; every other input is identical",
            "Confidence": "high" if abs(wavelength[i_f] - wavelength[i_z]) > 2.0 else "low",
        })
    nodes = {name: {"finite_k": fkm.cancellation_at(wavelength, finite, nm),
                    "frozen": fkm.cancellation_at(wavelength, frozen, nm)}
             for name, nm in (("Z1", 605.0), ("Z2", 1330.0))}
    summary = {
        "k_points": int(len(k_values)), "k_max_per_nm": float(np.max(k_values)),
        "normalized_rmse_finite_vs_frozen": float(np.sqrt(np.mean(
            (signed_spectrum.normalize(finite.chi2) - signed_spectrum.normalize(frozen.chi2)) ** 2))),
        "max_abs_change_pm_per_V": float(np.max(np.abs(finite.chi2 - frozen.chi2))),
        "nodes": nodes,
    }
    return {"wavelength": wavelength, "finite": finite, "frozen": frozen, "paper": paper,
            "paper_x": paper_x, "paper_y": paper_y, "scorecard": scorecard, "summary": summary}


def _paper_curve(cfg: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    import csv  # noqa: PLC0415

    path = repo_path(str(cfg["analysis"]["paper_curve"]))
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    x = np.asarray([float(r["wavelength_nm"]) for r in rows])
    y = np.asarray([float(r["digitized_simulated_chi2_pm_per_V"]) for r in rows])
    return x, y


def _candidates_report(scored: Sequence[Mapping[str, Any]], verdict: Mapping[str, Any],
                       edges: Mapping[str, float], target: float) -> str:
    return "\n".join([
        f"# Demo 25: search for a ~{target:.3f} eV transition", "",
        f"**Verdict: {verdict['answer']}**", "",
        "An energy match alone is never accepted as an explanation for P1/P3. Every candidate is",
        "additionally scored on envelope overlap and oscillator strength, and any candidate that",
        "involves a state outside the barrier gap is flagged: with Dirichlet walls such a state is",
        "a box state of the quantum region, so its energy depends on the region width.", "",
        f"- barrier gap (bound-bound ceiling): **{edges['barrier_gap_eV']:.4f} eV**",
        f"- required for the paper's P1/P3 pair: **{target:.4f} eV**",
        f"- candidates within tolerance: **{len(scored)}**", "",
        reporting.markdown_table(list(scored)[:200], [
            "k_per_nm", "electron_state", "hole_state", "transition_energy_eV",
            "one_photon_nm", "two_photon_nm", "electron_confined", "hole_confined",
            "envelope_overlap", "oscillator_strength", "verdict"]) if scored
        else "_No transition fell within the search tolerance._",
    ]) + "\n"


def _final_report(cfg: Mapping[str, Any], edges: Mapping[str, float],
                  tracking_rows: Sequence[Mapping[str, Any]], events: Sequence[Mapping[str, Any]],
                  scored: Sequence[Mapping[str, Any]], verdict: Mapping[str, Any],
                  ratios: Sequence[Mapping[str, Any]], spectra: Mapping[str, Any]) -> str:
    summary = spectra["summary"]
    varying = [r for r in ratios if r.get("varies_more_than_10pct")]
    signs = [r for r in ratios if r.get("sign_change_vs_k")]
    sections = [
        ("1. Executive summary", _executive(summary, verdict, varying, signs, spectra["scorecard"])),
        ("2. Motivation from Demo 24", (
            "Demo 24 established that Demo 23's spectrum reproduces the paper's P2/P4 pair and "
            "structurally cannot produce P1/P3, and that the model's 1250-1450 nm structure is a "
            "k-truncation artifact. It could not test finite-k M(k), because Demo 23 exported "
            "state and matrix output only at k=0. Demo 25 supplies exactly that missing data.")),
        ("3. Pilot output test", "See `PILOT_FINITE_K_OUTPUT_AUDIT.md` and `PILOT_GATE.json`."),
        ("4. Professional output syntax discovered", (
            "Demo 23 used `k_integration_disabled{}`, so `all_k_points = yes` had a single "
            "k-integration point and only `k00000` state files were written. The pilot varies "
            "`k_integration{}`, `no_density` and `k_point_subdirectories` to establish which "
            "combination emits per-k state output; `PILOT_VARIANT_SUMMARY.csv` records the answer.")),
        ("5. Production run configuration", "See `PROFESSIONAL_RUN_MANIFEST.csv`."),
        ("6. Extended state dispersion", f"{len(tracking_rows)} tracked state records; see `EXTENDED_STATE_ENERGIES.csv`."),
        ("7. State tracking", (
            f"{len(events)} events flagged. Identity follows spinor character and wavefunction "
            "overlap, with energy only as a tie-break, because Demo 24 showed energy ordering "
            "mislabelled an LH-dominated state as `hh2`. See `STATE_TRACKING.csv`.")),
        ("8. HH/LH mixing", reporting.markdown_table(
            [e for e in events if "character" in str(e.get("event", ""))][:40],
            ["k_index", "state", "event", "detail"]) or "_No character changes were detected._"),
        ("9. ~2.296 eV transition search", verdict["answer"]),
        ("10. Optical relevance of candidate states", (
            f"Barrier gap {edges['barrier_gap_eV']:.4f} eV bounds any bound-bound transition. "
            f"{len(scored)} candidates were scored; see `P1_P3_RESONANCE_CANDIDATES.md`.")),
        ("11. Finite-k overlaps", "See `FINITE_K_OVERLAPS.csv` and Figure 8."),
        ("12. Finite-k electron z matrix elements", "See `FINITE_K_ELECTRON_Z.csv` and Figure 9."),
        ("13. Finite-k HH z matrix elements", "See `FINITE_K_HOLE_Z.csv` and Figure 10."),
        ("14. Finite-k pathway numerators", reporting.markdown_table(list(ratios), [
            "pathway", "side", "abs_M_p_at_k0", "max_fractional_deviation",
            "sign_change_vs_k", "varies_more_than_5pct", "varies_more_than_10pct"])),
        ("15. 605-nm cancellation", _node_section("Z1", 605.0, summary)),
        ("16. 1330-nm cancellation", _node_section("Z2", 1330.0, summary)),
        ("17. Full finite-k Equation 2 spectrum", (
            f"Normalized RMSE between the finite-k and M(k)=M(0) spectra: "
            f"{summary['normalized_rmse_finite_vs_frozen']:.4f}. Both use identical energies, "
            "broadening, weighting and pathways, so the difference isolates M(k).")),
        ("18. P1/P2/P3/P4 comparison", reporting.markdown_table(list(spectra["scorecard"]), [
            "Feature", "Paper_lambda", "Demo23D_lambda", "Demo25_lambda",
            "Demo23D_amplitude", "Demo25_amplitude", "Improved?"])),
        ("19. Z1/Z2 comparison", _node_section("Z1", 605.0, summary) + "\n\n" + _node_section("Z2", 1330.0, summary)),
        ("20. Demo 23 vs Demo 25", "Figure 14 overlays the two normalized spectra."),
        ("21. Paper comparison", "Figure 15 overlays Demo 25 with the digitized paper curve."),
        ("22. Root-cause conclusion", _root_cause(verdict, varying, signs, summary)),
        ("23. Independent professor review", "See `professor_review/PHYSICS_PROFESSOR_REVIEW_DEMO25.md`."),
        ("24. Remaining uncertainty", (
            "The kp8 spinor inner product is the physically correct one, but mapping it onto the "
            "paper's one-band Equation 2 envelope quantities is a modelling choice; the CB and HH "
            "purities reported alongside every matrix element show how well that reading holds. "
            "States above the barrier edge are Dirichlet box states of the quantum region and "
            "their energies depend on its width.")),
        ("25. Recommendation for Demo 26, if needed", _demo26(verdict, varying, summary)),
    ]
    report = ["# Demo 25 final report", ""]
    for title, body in sections:
        report += [f"## {title}", "", body, ""]
    return "\n".join(report)


def _executive(summary, verdict, varying, signs, scorecard) -> str:
    improved = [r["Feature"] for r in scorecard if r["Improved?"] == "yes"]
    return (
        f"Finite-k matrix elements were obtained at {summary['k_points']} k points out to "
        f"{summary['k_max_per_nm']:.3f} /nm. Against an otherwise identical M(k)=M(0) control, "
        f"the normalized spectrum changed by RMSE {summary['normalized_rmse_finite_vs_frozen']:.4f}. "
        f"{len(varying)} of 16 pathway numerators vary by more than 10% across k and "
        f"{len(signs)} change sign. "
        + (f"Features moved closer to the paper: {', '.join(improved)}. " if improved
           else "No feature moved materially closer to the paper. ")
        + verdict["answer"])


def _node_section(name: str, nm: float, summary: Mapping[str, Any]) -> str:
    node = summary["nodes"][name]
    a, b = node["finite_k"], node["frozen"]
    direction = ("deeper" if a["cancellation_ratio"] < b["cancellation_ratio"]
                 else "shallower" if a["cancellation_ratio"] > b["cancellation_ratio"] else "unchanged")
    return (f"At {nm:.0f} nm the cancellation ratio |chi|/(|chi_e|+|chi_hh|) is "
            f"**{a['cancellation_ratio']:.4f}** with finite-k M(k) against "
            f"**{b['cancellation_ratio']:.4f}** with M(k)=M(0): the node is {direction}. "
            f"Electron/hole phase difference {a['phase_difference_deg']:+.1f} deg "
            f"(frozen: {b['phase_difference_deg']:+.1f} deg).")


def _root_cause(verdict, varying, signs, summary) -> str:
    parts = []
    if summary["normalized_rmse_finite_vs_frozen"] > 0.02:
        parts.append("Finite-k M(k) materially changes the normalized spectrum, so the "
                     "M(k)=M(0) approximation was not benign.")
    else:
        parts.append("Finite-k M(k) barely changes the normalized spectrum, so freezing the "
                     "numerator was not the cause of the shape mismatch.")
    if signs:
        parts.append(f"{len(signs)} pathway numerator(s) change sign across k, which directly "
                     "affects the electron/heavy-hole cancellation.")
    parts.append(verdict["answer"])
    return " ".join(parts)


def _demo26(verdict, varying, summary) -> str:
    if not verdict["found"] and summary["normalized_rmse_finite_vs_frozen"] <= 0.02:
        return ("Demo 26 is warranted: with finite-k M(k) measured and no optically relevant "
                "~2.296 eV transition present, geometry/material mismatch is the leading remaining "
                "explanation. Demo 26 should be an exact paper-geometry reconstruction. Demo 25 "
                "deliberately did not tune layer widths, Al fractions or grading to fit the curve.")
    if verdict["found"]:
        return ("Demo 26 should test whether the identified transition survives a wider quantum "
                "region, since a state near the barrier edge can be a box artifact.")
    return ("Finite-k M(k) is material. Before any geometry work, re-examine the Demo 24 causal "
            "conclusions with the finite-k numerators in place.")
