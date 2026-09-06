"""Demo 24: solver-free Equation-2 spectral-shape audit using copied Demo 23 data."""

from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml


DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[2]
DEMO23 = DEMO_DIR.parent / "23_k_resolved_dispersion_validation"
DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
for module_dir in (DEMO22, DEMO23, DEMO_DIR):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

import analysis23  # noqa: E402
import deck23  # noqa: E402
import kp8io22  # noqa: E402
import physics23  # noqa: E402
import state_tracking as tracking23  # noqa: E402
from config23 import load_config as load_demo23_config  # noqa: E402

import causal_sensitivity  # noqa: E402
import finite_k_matrix_audit  # noqa: E402
import paper_feature_analysis  # noqa: E402
import pathway_analysis  # noqa: E402
import professional_rerun_assessment  # noqa: E402
import resonance_analysis  # noqa: E402
import sensitivity_analysis  # noqa: E402
import signed_spectrum  # noqa: E402


def _load_local_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, DEMO_DIR / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Demo 23 imports modules with these generic names first, so load the Demo 24
# writers explicitly instead of accepting the already-cached Demo 23 modules.
plotting = _load_local_module("demo24_plotting", "plotting.py")
reporting = _load_local_module("demo24_reporting", "reporting.py")


def load_config() -> dict[str, Any]:
    return yaml.safe_load((DEMO_DIR / "demo24_config.yaml").read_text(encoding="utf-8"))


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _valid_demo23_root(path: Path, specs: tuple[deck23.DeckSpec, ...]) -> bool:
    raw = path / "raw"
    if not raw.is_dir():
        return False
    for spec in specs:
        case = raw / spec.name
        if not case.is_dir() or not list(case.rglob("job_done.txt")) or not list(case.rglob("dispersion_*.dat")):
            return False
    return True


def locate_demo23_root(config: Mapping[str, Any], specs: tuple[deck23.DeckSpec, ...]) -> Path:
    base = resolve_repo_path(str(config["inputs"]["demo23_results_root"]))
    candidates = [path for path in base.glob("demo23_*") if path.is_dir()]
    if base.is_dir():
        candidates.append(base)
    valid = [path for path in candidates if _valid_demo23_root(path, specs)]
    if not valid:
        raise RuntimeError(f"no completed Demo 23 run with all seven cases under {base}")
    return max(valid, key=lambda path: max(p.stat().st_mtime for p in (path / "raw").rglob("job_done.txt")))


def _feature_windows(config: Mapping[str, Any]) -> dict[str, tuple[float, float]]:
    return {str(row["name"]): tuple(map(float, row["window_nm"]))
            for row in config["paper_features"]["expected"] if row["type"] == "minimum"}


def _paper_on_grid(wavelength: np.ndarray, paper_x: np.ndarray, paper_y: np.ndarray) -> np.ndarray:
    return paper_feature_analysis.interpolate_paper(wavelength, paper_x, paper_y)


def _local_rmse_rows(label: str, wavelength: np.ndarray, paper: np.ndarray, model: np.ndarray,
                     windows: Mapping[str, list[float]]) -> list[dict[str, object]]:
    p, m = signed_spectrum.normalize(paper), signed_spectrum.normalize(model)
    rows = []
    for name, limits in windows.items():
        mask = (wavelength >= float(limits[0])) & (wavelength <= float(limits[1]))
        rows.append({"model": label, "window": name, "start_nm": limits[0], "stop_nm": limits[1],
                     "local_normalized_RMSE": float(np.sqrt(np.mean((p[mask] - m[mask]) ** 2)))})
    return rows


def _model_feature_rows(mode: str, result, paper_features: list[dict[str, Any]],
                        config: Mapping[str, Any]) -> list[dict[str, object]]:
    x, chi = result.spectrum.wavelength_nm, result.spectrum.chi2
    norm = signed_spectrum.normalize(chi)
    rows = []
    for feature, target in zip(config["paper_features"]["expected"], paper_features):
        lo, hi = map(float, feature["window_nm"])
        mask = (x >= lo) & (x <= hi)
        local = np.flatnonzero(mask)
        index = int(local[np.argmax(norm[mask])]) if feature["type"] == "peak" else int(local[np.argmin(norm[mask])])
        full_zero: object = "n/a"
        real_cross: object = "n/a"
        imag_cross: object = "n/a"
        if feature["type"] == "minimum":
            diag = signed_spectrum.complex_zero_diagnostic(
                x, chi, (lo, hi), float(config["analysis"]["complex_zero_threshold_fraction"]))
            full_zero = diag["full_complex_zero"]
            real_cross = diag["nearest_real_crossing_nm"]
            imag_cross = diag["nearest_imag_crossing_nm"]
        rows.append({
            "Model": mode, "Feature": target["Feature"], "Feature type": feature["type"],
            "Paper wavelength nm": target["Paper wavelength nm"], "Model wavelength nm": float(x[index]),
            "Wavelength error nm": float(x[index] - float(target["Paper wavelength nm"])),
            "Paper normalized amplitude": target["Normalized amplitude"],
            "Model normalized amplitude": float(norm[index]),
            "Model amplitude at paper wavelength": float(np.interp(float(target["Paper wavelength nm"]), x, norm)),
            "Signed full complex zero": full_zero, "Nearest Re crossing nm": real_cross,
            "Nearest Im crossing nm": imag_cross, "Search window nm": f"{lo:g}-{hi:g}",
            "Status": "MATCH" if abs(float(x[index]) - float(target["Paper wavelength nm"])) <= float(target["Digitization uncertainty nm"]) else "MISMATCH",
        })
    return rows


def _signed_zero_rows(results: Mapping[str, Any], config: Mapping[str, Any]) -> list[dict[str, object]]:
    rows = []
    for mode, result in results.items():
        for feature, window in _feature_windows(config).items():
            diag = signed_spectrum.complex_zero_diagnostic(
                result.spectrum.wavelength_nm, result.spectrum.chi2, window,
                float(config["analysis"]["complex_zero_threshold_fraction"]))
            rows.append({"model": mode, "feature": feature, "window_nm": f"{window[0]:g}-{window[1]:g}",
                         **{key: (";".join(f"{v:.6g}" for v in value) if isinstance(value, list) else value)
                            for key, value in diag.items() if key != "index"}})
    return rows


def _audit_rows(run_root: Path, specs: tuple[deck23.DeckSpec, ...], reanalysis: Path) -> list[dict[str, object]]:
    raw = run_root / "raw"
    decks = list((DEMO23 / "inputs").glob("*.in"))
    rows: list[dict[str, object]] = []
    def add(dataset: str, found: bool, path: Path | str, test: str, note: str) -> None:
        rows.append({"FILE / DATASET": dataset, "FOUND?": "YES" if found else "NO", "PATH": str(path),
                     "REQUIRED FOR WHICH DEMO 24 TEST?": test, "QUALITY / LIMITATION": note})
    add("all seven Professional case directories", all((raw / s.name).is_dir() for s in specs), raw, "baseline, convergence, isotropy", "seven of seven expected cases")
    add("all seven Demo 23 input decks", len(decks) == 7, DEMO23 / "inputs", "reproducibility", "repository copies; run-local copies were not included")
    add("completion markers", all(list((raw / s.name).rglob("job_done.txt")) for s in specs), raw, "input validity", "one marker in every case")
    add("tracked kp8 E(k) and explicit vectors", all(list((raw / s.name).rglob("dispersion_*.dat")) and list((raw / s.name).rglob("kVectors_*.dat")) for s in specs), raw, "23D, resonance, grid/kmax", "complete combined dispersion tables")
    add("k=0 spinor composition", all(list((raw / s.name).rglob("spinor_composition_k00000_CbHhLhSo.dat")) for s in specs), raw, "state assignment", "k=0 only; no finite-k tracking score")
    add("finite-k spinors/envelopes", False, raw, "finite-k M(k), state mixing", "REQUIRES_NEW_PROFESSIONAL_DATA")
    add("A/B/C/D complex spectra", (reanalysis / "spectra" / "23D_chi2.csv").is_file(), reanalysis / "spectra", "baseline and comparisons", "regenerated from raw; raw tree untouched")
    add("16 signed pathways", (reanalysis / "tables" / "pathway_contributions_1550_and_peaks.csv").is_file(), reanalysis / "tables", "pathway audit", "full-wavelength terms recomputed by Demo 24")
    add("k-resolved integrand", True, "recomputed in memory from E(k) and frozen M(0)", "cross-k cancellation", "available under the validated M(k)=M(0) assumption")
    add("convergence outputs", (reanalysis / "tables" / "k_grid_convergence.csv").is_file(), reanalysis / "tables", "k-grid/kmax", "regenerated from the copied raw cases")
    add("isotropy output", (reanalysis / "tables" / "isotropy.csv").is_file(), reanalysis / "tables", "radial integration audit", "one alternate direction; not a full 2D integral")
    add("resolved configuration", (reanalysis / "resolved_configuration.json").is_file(), reanalysis / "resolved_configuration.json", "frozen physics audit", "regenerated")
    add("solver metadata", all(list((raw / s.name).rglob("simulation_info.txt")) for s in specs), raw, "provenance", "per-case metadata present; top-level invocation JSON absent")
    return rows


def _state_character_rows(raw_case: Path, tracked) -> list[dict[str, object]]:
    found = tracking23._combined_files(raw_case)
    if found is None:
        return []
    _, _, energy_path, spinor_path = found
    energies = kp8io22.numeric_table(energy_path)[:, 1]
    table = kp8io22.numeric_table(spinor_path)
    spinor = table[:, 1:]
    spinor = spinor / np.sum(np.abs(spinor), axis=1)[:, None]
    names = kp8io22._component_names(spinor_path, spinor.shape[1])
    def fraction(pair: tuple[int, int], token: str) -> float:
        indices = [i for i, name in enumerate(names) if token.lower() in name.lower()]
        return float(np.mean(np.sum(spinor[list(pair)][:, indices], axis=1))) if indices else 0.0
    rows = []
    selections = [(state, int(tracked.k0_raw_identity[state]), "Demo 23 selected")
                  for state in ("e1", "e2", "hh1", "hh2")]
    selections.append(("hh2_character_candidate", 0, "unselected pair 1+2; 100% HH at k=0"))
    for state, first, role in selections:
        pair = (first, first + 1)
        state_rows = [r for r in tracked.rows if r["assigned_physical_state"] == state]
        rows.append({
            "k": 0.0, "state": state, "energy": float(np.mean(energies[list(pair)])),
            "CB fraction": fraction(pair, "Cb"), "HH fraction": fraction(pair, "Hh"),
            "LH fraction": fraction(pair, "Lh"), "SO fraction": fraction(pair, "So"),
            "tracking score": "not available", "assignment margin": "not available",
            "max Kramers splitting meV": (max(float(r["kramers_pair_splitting_meV"]) for r in state_rows)
                                             if state_rows else "not evaluated"),
            "selection role": role,
            "limitation": "finite-k spinor composition was not exported; k=0 fractions only",
        })
    return rows


def _hh2_character_corrected_result(raw_case: Path, tracked, frozen, settings,
                                    wavelength: np.ndarray, cfg23: Mapping[str, Any]):
    """Diagnostic replacement of the LH-like Demo 23 hh2 pair by pair 1+2.

    This retains the same four-state Equation 2 and frozen M(0). It does not
    claim validated finite-k tracking; it only tests the evident k=0 identity
    error using an already-exported dispersion column.
    """
    found = tracking23._combined_files(raw_case)
    if found is None:
        raise RuntimeError("combined Professional dispersion is unavailable")
    dispersion_path, _, _, _ = found
    k_scalar, bands = tracking23._fixed_width_dispersion(dispersion_path)
    energies = {key: np.asarray(value).copy() for key, value in tracked.energies_eV.items()}
    energies["hh2"] = np.mean(bands[:, 0:2], axis=1)
    corrected = tracking23.TrackedSubbands(
        np.asarray(k_scalar), energies, {**tracked.k0_raw_identity, "hh2": 0}, None, tuple())
    models, _, _ = analysis23._models_for(corrected, frozen, settings)
    return physics23.evaluate_mode(
        "23D", models["23D"], np.asarray(k_scalar), wavelength, frozen, settings,
        k0_tolerance_eV=float(cfg23["validation"]["k0_transition_tolerance_eV"]))


def _geometry_audit() -> list[dict[str, object]]:
    return [
        {"Parameter": "thick/thin GaAs wells", "Paper": "7.1 / 2.9 nm (10 nm total, s=0.42)", "Demo 23": "7.1 / 2.9 nm", "Match?": "YES", "Confidence": "high", "Potential spectral consequence": "none"},
        {"Parameter": "tunnel barrier", "Paper": "1.8 nm Al0.55Ga0.45As", "Demo 23": "1.8 nm Al0.55Ga0.45As", "Match?": "YES", "Confidence": "high", "Potential spectral consequence": "none"},
        {"Parameter": "period barrier / period", "Paper": "18.2 nm / 30 nm by Fig. 1 and layer arithmetic; page 6 says 20 nm inconsistently", "Demo 23": "18.2 nm / 30 nm", "Match?": "LIKELY", "Confidence": "high", "Potential spectral consequence": "Nz scale only for isolated periods"},
        {"Parameter": "interfaces", "Paper": "Fig. 2d design simulation appears ideal/abrupt; EDS-profile simulations are treated separately", "Demo 23": "linear 1 nm at all four interfaces", "Match?": "NO / UNCERTAIN", "Confidence": "medium", "Potential spectral consequence": "changes energies, overlaps and z matrix elements; can alter normalized shape"},
        {"Parameter": "temperature", "Paper": "not stated for Fig. 2d calculation", "Demo 23": "300 K", "Match?": "UNKNOWN", "Confidence": "low", "Potential spectral consequence": "band gap and resonance shifts"},
        {"Parameter": "tensor element", "Paper": "chi_xzx^(2)", "Demo 23": "Equation-2 chi_xzx^(2)", "Match?": "YES", "Confidence": "high", "Potential spectral consequence": "none"},
        {"Parameter": "state count", "Paper": "first two conduction and first two HH states only", "Demo 23": "two plus two in Equation 2", "Match?": "YES", "Confidence": "high", "Potential spectral consequence": "extra-state hypothesis is low priority"},
        {"Parameter": "broadening", "Paper": "5 meV", "Demo 23": "5 meV", "Match?": "YES", "Confidence": "high", "Potential spectral consequence": "none"},
        {"Parameter": "wavelength/observable", "Paper": "fundamental wavelength, simulated |chi^(2)|", "Demo 23": "fundamental wavelength, complex chi and |chi|", "Match?": "YES", "Confidence": "high", "Potential spectral consequence": "Re-only zeros cannot be compared as full paper nodes"},
        {"Parameter": "k cutoff", "Paper": "saturation asserted at 0.1 BZ", "Demo 23": "0.1 pi/a", "Match?": "FORMALLY", "Confidence": "medium", "Potential spectral consequence": "copied result is numerically not converged versus 0.125 pi/a"},
    ]


def _root_cause_rows(metrics: Mapping[str, Any]) -> list[dict[str, object]]:
    """Rank hypotheses using the Demo 24N one-at-a-time perturbation evidence.

    The 24N results reorder the earlier ranking on three specific findings:
    the paper's P1/P3 pair needs a transition energy no bound-subband pair in
    this structure can reach; the model's 1250-1450 nm structure is a k-cutoff
    artifact that marches with the cutoff; and a 10% change in one pathway
    numerator opens genuine complex nodes near both paper zeros.
    """
    rows = [
        (1, "missing states / model-space truncation (transition above the bound-subband range)", 0.94,
         "24N reachability: P1 (540 nm) and P3 (1080 nm) are an exact one-photon/two-photon pair of a single 2.296 eV transition; the largest transition any bound-subband pair reaches before the electron leaves the 2.145 eV barrier is 1.966 eV, so no k, energy shift, amplitude, sign, broadening or normalization change can create them; both model 'features' sit on their search-window edges",
         "the paper text restricts Eq. 2 to the first two electron and HH bound states, so this implies the compared curve is not that four-state calculation",
         "yes", "yes", "partly", "yes", "yes", "yes"),
        (2, "missing finite-k M(k)", 0.90,
         "24N amplitude scan: a single -10% change in C_m1_n1_l1 (or +10% in V_m1_n1_l1) opens a genuine complex node at 573 nm (normalized 0.0001) and 1282 nm (0.0018), both moving toward the paper's 605/1330 nm; electron and heavy-hole subtotals are 180.0 deg antiphase and cancel to 4.3-4.9%, so a few-percent numerator error is amplified about 21-24x; a frozen numerator also fails to damp the high-k tail, which is what leaves the cutoff artifact sharp",
         "no finite-k envelope or matrix data exist in the copied output, so the required M(k) variation is bounded, not measured",
         "partly", "yes", "yes", "yes", "no", "yes"),
        (3, "kmax / k-truncation artifact", 0.88,
         "24N cutoff test: the model peak near 1318 nm moves 1502->1431->1376->1318 nm as kmax goes 0.05->0.125 pi/a and matches 2hc/DeltaE(kmax) to 9 nm mean error, so it is a truncation artifact, not a resonance; the 659 nm peak behaves the same way at one photon; the integrand for P1/Z1/P3/Z2 still peaks at the last k sample",
         "the two features that do match the paper (752 and 1503 nm) are stable to 1 nm across all four cutoffs, so truncation does not explain the P2/P4 residual; extending kmax alone would move the artifact rather than remove it",
         "partly", "partly", "yes", "yes", "yes", "yes"),
        (4, "geometry mismatch", 0.72,
         "a structure whose second dominant transition sits at 2.296 eV differs materially from the Demo 23 stack, whose barrier gap is only 2.145 eV; Fig. 2d also appears to use ideal interfaces against Demo 23's 1-nm linear grading",
         "all nominal layer dimensions match and the P2/P4 pair is already reproduced to 8-17 nm",
         "yes", "possible", "possible", "yes", "partly", "yes"),
        (5, "energy-dispersion mismatch", 0.55,
         "24N derivatives: P2 and P4 are controlled by DeltaE_22 with dLambda/dE = -0.46 and -0.92 nm/meV (exactly the 1:2 one-/two-photon ratio), and both close on the paper with a single coherent -17/-18 meV shift of e2",
         "a 17 meV offset is within band-parameter uncertainty and cannot touch P1/Z1/P3/Z2, which are energy-insensitive to machine precision",
         "partly", "no", "no", "partly", "yes", "maybe"),
        (6, "HH/LH state misassignment", 0.45,
         "Demo 23 hh2 pair 3+4 is 97.6% LH at k=0, while the unselected pair 1+2 is 100% HH",
         "24N shows the reassignment moves E_hh2 down 19 meV, which drives P2/P4 the wrong way (dLambda/dE_hh2 = +0.46/+0.92 nm/meV, and the paper needs +17 meV); the state-corrected candidate scores worse on the only two features that currently match",
         "no", "no", "no", "partly", "yes", "yes"),
        (7, "anisotropy / radial reduction", 0.40,
         "alternate direction differs, especially hh1; the radial gate fails",
         "only two directions exist and no 2D chi can be formed; anisotropy cannot supply a 2.296 eV transition",
         "possible", "no", "no", "partly", "partly", "maybe"),
        (8, "Equation-2 specialization / missing frequency permutation", 0.30,
         "published Eq. 1 includes a polarization/permutation sum whose reduction is not fully reproduced in the paper text",
         "literal Eq. 2 and all 16 implemented terms agree; the instrumented mirror reproduces the production engine to 1e-14 relative",
         "possible", "possible", "possible", "partly", "yes", "no"),
        (9, "paper digitization / peak correspondence", 0.24,
         "45 points and eye reading make narrow extrema uncertain",
         "P1 is a well-resolved digitized maximum (1260 between 450 and 680) and the 540/1080 and 760/1520 pairs are both exact 1:2 ratios, which eye error would not manufacture; errors are far larger than plausible digitization uncertainty",
         "partly", "no", "no", "partly", "yes", "no"),
        (10, "broadening", 0.18,
         "Gamma changes absorptive filling and peak widths",
         "the 2.5-10 meV ladder does not restore topology and cannot move a resonance band; paper uses 5 meV",
         "no", "partly", "partly", "partly", "yes", "no"),
        (11, "pathway sign/indexing", 0.12,
         "nodes depend on delicate signed cancellation and 24N confirms the cancellation is 180.0 deg exact",
         "literal-equation, sign, conjugation and phase-invariance audits pass; the 16 terms sum to the total and the electron/heavy-hole split reproduces it",
         "no", "unlikely", "unlikely", "no", "yes", "no"),
        (12, "k-grid", 0.08,
         "coarse grids can affect resonances",
         "101/201/301 copied cases show stable normalized topology; 24N shows the cutoff, not the sampling density, sets the artifact",
         "no", "no", "no", "no", "yes", "no"),
        (13, "normalization", 0.02,
         "absolute scale remains discrepant",
         "global factors cannot alter normalized shape or create nodes",
         "no", "no", "no", "no", "yes", "no"),
    ]
    return [{"Rank": rank, "Hypothesis": name, "Evidence for": pro, "Evidence against": contra,
             "Explains peak positions?": peaks, "Explains 605 zero?": z1, "Explains 1330 zero?": z2,
             "Explains overall shape?": shape, "Can test from existing data?": existing,
             "Requires Pro rerun?": pro_run, "Confidence": f"{score:.2f}", "Confidence score": score}
            for rank, name, score, pro, contra, peaks, z1, z2, shape, existing, pro_run in rows]


def _write_audit_reports(output: Path, audit_rows: list[dict[str, object]], geometry_rows: list[dict[str, object]],
                         finite_rows: list[dict[str, object]]) -> None:
    reporting.write_text(output / "DEMO23_INPUT_AUDIT.md", "# Demo 23 input audit\n\n" + reporting.markdown_table(
        audit_rows, ["FILE / DATASET", "FOUND?", "PATH", "REQUIRED FOR WHICH DEMO 24 TEST?", "QUALITY / LIMITATION"]))
    reporting.write_text(output / "PAPER_STRUCTURE_AUDIT.md", "# Paper/model structure audit\n\nThe comparison is not demonstrably apples-to-apples because the published Fig. 2d simulation appears to be the ideal design while Demo 23 uses 1-nm linear interfaces.\n\n" + reporting.markdown_table(
        geometry_rows, ["Parameter", "Paper", "Demo 23", "Match?", "Confidence", "Potential spectral consequence"]))
    reporting.write_text(output / "FINITE_K_DATA_INVENTORY.md", "# Finite-k matrix-element data inventory\n\nThe copied output supports E(k), but not a valid finite-k M(k) reconstruction. Demo 24 therefore does not fabricate a finite-k spectrum.\n\n" + reporting.markdown_table(
        finite_rows, ["Quantity", "Needed for Equation 2?", "Available in copied Demo 23 raw output?", "Exact file/path", "Can be used directly?", "Needs conversion?", "Missing?"]))


def _write_target_config(output: Path) -> None:
    text = """status: REQUIRES_PROFESSIONAL_NEXTNANO
purpose: finite-k matrix-element and exact-paper-geometry discriminator
geometry:
  thick_well_nm: 7.1
  tunnel_barrier_nm: 1.8
  thin_well_nm: 2.9
  period_barrier_nm: 18.2
  total_period_nm: 30.0
  barrier_al_fraction: 0.55
  interface_model: abrupt
  temperature_K: 300.0
k_path:
  direction: [0.0, 1.0, 0.0]
  start: Gamma
  # Demo 24N: at 0.125 pi/a the integrand still peaks at the cutoff, and the
  # resonance the paper's 1330 nm node needs sits near 0.116 pi/a, so the grid
  # must pass it with margin rather than stop on it.
  stop_fraction_of_pi_over_a: 0.20
  points: 301
required_outputs:
  - explicit k vectors
  - all-k energies for at least 14 states
  - all-k complex spinor/envelope coefficients for state tracking
  - all-k CB/HH/LH/SO fractions per state
  - all-k complex O_nm(k) or sufficient envelopes to construct it
  - all-k complex z_e_nl(k)
  - all-k complex z_hh_ml(k)
  - oscillator strengths for every solved state, to test whether anything reaches 2.296 eV
  - bandedges.dat
  - solver/database/material metadata
pilot_check:
  reason: Demo 23 requested all_k_state_output but received only k00000 state and matrix files.
  action: validate the output syntax on a small k grid before launching the production job.
note: The existing Demo 23 deck renderer exports dispersions but not the required all-k matrices, so this proposal is intentionally not presented as an executable deck.
"""
    reporting.write_text(output / "targeted_professional_run" / "exact_paper_geometry_target.yaml", text)


def _write_professor_input(output: Path, summary: Mapping[str, Any]) -> None:
    prompt = """# Physics professor review prompt

Act as an independent professor of semiconductor physics, nonlinear optics, quantum wells, k.p theory, and second-order susceptibility. Do not defer to the primary agent. Read `professor_review_input.md` and the referenced Demo 24 tables/figures. Independently answer all 17 questions in the user brief, rank the top five causes, identify any Equation-2 sign/index/permutation concern, and decide whether a targeted Professional run is necessary. Distinguish a zero of Re(chi) from a zero of complex |chi|. Write `PHYSICS_PROFESSOR_REVIEW.md` with an independent verdict, agreements/disagreements, top five causes, reasoning, next calculation, Pro-rerun YES/NO, and confidence.

## Demo 24N causal-sensitivity questions (answer these separately)

1. Are the claimed causal relationships supported by the perturbation results?
2. Is each peak truly associated with the identified transition and pathway?
3. Are the left/right peak shifts consistent with the identified transition-energy error?
4. Are the 605 and 1330 nm nodes truly cancellation-controlled?
5. Is any perturbation being overinterpreted (sensitivity vs plausibility vs causality vs proof)?
6. Which result most strongly identifies the actual missing physics?
7. Does the sensitivity study reduce or increase the need for a new Professional nextnano run?
8. If a Pro rerun is needed, which missing quantity is now specifically implicated?

Demo 24N is one-at-a-time diagnostic perturbation only. No perturbed spectrum is a fitted or physical model, and none of them changes Demo 23 production physics.
"""
    reporting.write_text(DEMO_DIR / "professor_review" / "PHYSICS_PROFESSOR_REVIEW_PROMPT.md", prompt)
    lines = ["# Professor review input", "", "## Primary computed summary", "", "```json",
             json.dumps(summary, indent=2, default=str), "```", "", "## Evidence files", "",
             f"- {output / 'FEATURE_SCORECARD.csv'}", f"- {output / 'SIGNED_ZERO_ANALYSIS.csv'}",
             f"- {output / 'ELECTRON_HH_CANCELLATION.csv'}", f"- {output / 'PATHWAY_FEATURE_BREAKDOWN.csv'}",
             f"- {output / 'RESONANCE_MAP.csv'}", f"- {output / 'BROADENING_SENSITIVITY.csv'}",
             f"- {output / 'KGRID_SENSITIVITY.csv'}", f"- {output / 'KMAX_SENSITIVITY.csv'}",
             f"- {output / 'ISOTROPY_SPECTRAL_SENSITIVITY.csv'}", f"- {output / 'STATE_MIXING_AUDIT.csv'}",
             f"- {output / 'FINITE_K_DATA_INVENTORY.md'}", f"- {output / 'ROOT_CAUSE_RANKING.csv'}",
             f"- {output / 'PROFESSIONAL_RERUN_RECOMMENDATION.md'}", "",
             "## Demo 24N causal-sensitivity evidence", "",
             f"- {output / 'RESONANCE_REACHABILITY.csv'}", f"- {output / 'FEATURE_CAUSAL_TRACEBACK.csv'}",
             f"- {output / 'ENERGY_FEATURE_SENSITIVITY.csv'}", f"- {output / 'ENERGY_FEATURE_DERIVATIVES.csv'}",
             f"- {output / 'ENERGY_SHIFT_DIRECTION_STATEMENTS.csv'}",
             f"- {output / 'PATHWAY_AMPLITUDE_SENSITIVITY.csv'}", f"- {output / 'NODE_CANCELLATION_SENSITIVITY.csv'}",
             f"- {output / 'PHASE_SENSITIVITY.csv'}", f"- {output / 'NUMERATOR_PHASE_CONTENT.json'}",
             f"- {output / 'FEATURE_K_REGION_SENSITIVITY.csv'}", f"- {output / 'CUTOFF_ARTIFACT_TEST.csv'}",
             f"- {output / 'EXTRAPOLATION_VALIDATION.csv'}", f"- {output / 'RESONANCE_BAND_EDGES.csv'}",
             f"- {output / 'SPECTRAL_FEATURE_CAUSAL_DIAGNOSIS.csv'}",
             f"- {output / 'FEATURE_CAUSAL_STATEMENTS.md'}", f"- {output / 'BAND_EDGES.json'}", "",
             "The paper source is `2602.23246v1.pdf`, especially Fig. 2d (page 7) and Eq. 2/methods (pages 11-12). The plotted paper simulation is nonnegative `|chi^(2)|`; the digitization is an eye trace, not author data."]
    reporting.write_text(DEMO_DIR / "professor_review" / "professor_review_input.md", "\n".join(lines))
    response = DEMO_DIR / "professor_review" / "professor_review_response.md"
    if not response.exists():
        reporting.write_text(response, "# Professor review response\n\nPending independent professor-agent review.")


def _causal_section(causal: Mapping[str, Any]) -> str:
    """Demo 24N narrative built from the measured perturbation results."""
    diagnosis = causal["diagnosis"]
    reach = {str(r["Feature"]): r for r in causal["reachability"]}
    body = [
        "All Demo 24N results are one-at-a-time diagnostic perturbations. "
        + causal_sensitivity.DIAGNOSTIC_BANNER + ". The instrumented evaluator used for them "
        f"reproduces the production Equation-2 engine to {float(causal['mirror_max_abs_error_pm_per_V']):.2g} pm/V "
        "(about 1e-14 relative), so any change below is caused by the perturbation alone.",
        "",
        "### What creates each feature, and why it is shifted or missing",
        "",
        reporting.markdown_table(diagnosis, [
            "Feature", "Paper_lambda_nm", "Model_lambda_nm", "Delta_lambda_nm", "Dominant_pathway",
            "Controlling_transition", "Most_sensitive_energy", "dLambda_dE",
            "Cancellation_or_resonance", "Likely_root_cause", "Confidence", "Needs_new_Pro_data"]),
        "",
        "### Energy, numerator, cancellation, geometry or missing physics?",
        "",
        "**P2 and P4 are energy/denominator controlled.** Both are driven by the same DeltaE_22 "
        "transition, with dLambda/dE = -0.46 and -0.92 nm/meV against e2. The exact 1:2 ratio is the "
        "signature of a one-photon and a two-photon resonance of one transition, which confirms the "
        "pathway assignment independently. A single coherent shift of about -17 meV in e2 (equivalently "
        "+17 meV in hh2) closes both residuals at once, so the remaining P2/P4 error is one small "
        "band-parameter offset rather than a structural failure.",
        "",
        "**P1, Z1, P3 and Z2 are not controlled by any tracked energy.** Their dLambda/dE is zero to "
        "machine precision (about 1e-14 nm/meV) for all four subbands, and the wavelengths quoted for "
        "them are search-window edges rather than model extrema: the model has no turning point there "
        "at all. The reason is structural. The paper's P1 (540 nm) and P3 (1080 nm) are an exact "
        f"one-photon/two-photon pair of a single {float(reach['P1']['required_transition_energy_eV_one_photon']):.3f} eV "
        "transition, but the largest transition energy any pair of bound subbands in this structure can "
        f"reach - extrapolated to the k where the electron meets the {float(reach['P1']['barrier_gap_eV']) + 0.0:.3f} eV "
        f"barrier and stops being confined - is only {float(reach['P1']['max_bound_subband_transition_energy_eV']):.3f} eV. "
        "No k cutoff, energy shift, pathway amplitude, sign convention, broadening or normalization "
        "change can create those features, because the required resonance does not exist in the model space.",
        "",
        "**The 1250-1450 nm structure is a truncation artifact, not physics.** The cutoff test tracks "
        "the model peak from 1502 to 1431 to 1376 to 1318 nm as kmax goes 0.05 to 0.125 pi/a, matching "
        "2hc/DeltaE(kmax) to a 9 nm mean error. The 659 nm peak behaves the same way at one photon. By "
        "contrast the two peaks that match the paper, 752 and 1503 nm, are stable to 1 nm across all "
        "four cutoffs. A physical resonance does not move when the integration limit moves; a band edge "
        "created by stopping the k sum does. The model's Z2 'minimum' at 1250 nm is therefore just the "
        "trough between a real peak and an artifact.",
        "",
        "**The nodes are cancellation controlled, and reachable.** At both paper zeros the electron and "
        "signed heavy-hole subtotals are antiphase to within 0.1 degree and cancel to 4.3% (Z1) and 4.9% "
        "(Z2) of their individual magnitudes, an amplification of about 21-24x. Scaling the single "
        "dominant electron-side pathway C_m1_n1_l1 by 0.90 - or its heavy-hole partner V_m1_n1_l1 by "
        "1.10 - opens a genuine complex node at 573 nm with normalized amplitude 0.0001 and at 1282 nm "
        "with 0.0018, both moving toward the paper's 605 and 1330 nm. A 10% numerator error is exactly "
        "the size of effect a real finite-k M(k) would introduce, so the missing nodes are well within "
        "reach of the one piece of physics the model freezes.",
        "",
        "### Sufficiency of existing data, and what this implies for a rerun",
        "",
        "Existing data are sufficient to *exclude* energy error, pathway sign or indexing, broadening, "
        "k-grid density, radial weighting and normalization as causes of the four missing features, and "
        "to show that the model's own 1250-1450 nm structure is a cutoff artifact. They are not "
        "sufficient to *confirm* the finite-k M(k) hypothesis, because no finite-k envelope or matrix "
        "data were exported. The perturbation study therefore narrows the required Professional output "
        "to one specific quantity rather than a broad campaign: complex O_nm(k), z_e_nl(k) and "
        "z_hh_ml(k) on an extended k range, which simultaneously tests the node hypothesis and supplies "
        "the high-k damping that would remove the truncation artifact.",
        "",
        "### Scientific limitation",
        "",
        "One-at-a-time perturbation measures sensitivity, not proof. That a 10% change in one pathway "
        "opens a node shows the node is achievable within plausible matrix-element variation; it does "
        "not establish that M(k) is wrong by 10%, and correlated parameters are not separated by this "
        "design. The reachability and cutoff-artifact results are stronger than the amplitude result, "
        "because they are exclusions rather than demonstrations of possibility.",
    ]
    return "\n".join(body)


def _final_report(output: Path, summary: Mapping[str, Any], feature_rows: list[dict[str, object]],
                  root_rows: list[dict[str, object]], cancellation: list[dict[str, object]],
                  causal: Mapping[str, Any]) -> None:
    baseline_features = [r for r in feature_rows if r["Model"] == "23D"]
    professor_path = DEMO_DIR / "professor_review" / "PHYSICS_PROFESSOR_REVIEW.md"
    professor = professor_path.read_text(encoding="utf-8") if professor_path.is_file() else "Independent review pending."
    professor_24n_path = DEMO_DIR / "professor_review" / "PHYSICS_PROFESSOR_REVIEW_24N.md"
    professor_24n = (professor_24n_path.read_text(encoding="utf-8") if professor_24n_path.is_file()
                     else "Independent Demo 24N review pending.")
    sections = [
        ("1. Executive summary", "Demo 23D reproduces two of the paper's six features and structurally cannot produce the other four. The causal sensitivity study (Demo 24N) shows the paper spectrum is generated by two transition energies: 1.631 eV, whose one- and two-photon resonances are the paper's P2 (760 nm) and P4 (1520 nm), and 2.296 eV, whose resonances are P1 (540 nm) and P3 (1080 nm). Demo 23D contains the first and reproduces P2/P4 to 8 and 17 nm, closing on a single coherent -17 meV shift of e2. It cannot contain the second: the largest transition any bound-subband pair in this structure reaches before the electron leaves the 2.145 eV barrier is 1.966 eV. P1, Z1, P3 and Z2 are insensitive to every subband energy to machine precision, and the wavelengths reported for them are search-window edges rather than model extrema. Separately, the model's own 1250-1450 nm structure is a k-truncation artifact: it marches 1502->1318 nm as kmax grows and tracks 2hc/DeltaE(kmax) to 9 nm, while the two genuine peaks stay fixed to 1 nm. The two paper nodes are cancellation controlled - electron and heavy-hole subtotals are antiphase to 0.1 degree and cancel to 4.3-4.9%, a 21-24x amplification - and a 10% change in one pathway numerator opens real complex nodes at 573 and 1282 nm. The k=0 spinor file also shows Demo 23's `hh2` pair is 97.6% light-hole while an unselected pair is 100% heavy-hole; that observation stands, but 24N shows correcting it moves P2/P4 away from the paper, so it is demoted from the leading explanation."),
        ("2. Why Demo 24 was created", "To diagnose normalized spectral shape without rerunning Professional nextnano or changing Demo 23 physics."),
        ("3. Demo 23 baseline", f"Copied seven-case run: `{summary['demo23_root']}`. Baseline is 23D with M(k)=M(0), Gamma=5 meV, Nz=1/(30 nm), gs=2, and radial gs*k*dk/(2*pi)."),
        ("4. Paper-data provenance", "The target is a 45-point eye digitization of the dashed simulated |chi^(2)| curve in Ramesh et al. Fig. 2d, not raw author data. Feature uncertainty is configured as 12 nm."),
        ("5. Paper/model geometry equivalence", "Nominal widths and Al fraction match, but the paper Fig. 2d design simulation appears ideal/abrupt while Demo 23 is linearly graded over 1 nm. This is not a proven apples-to-apples comparison."),
        ("6. Peak and zero feature scorecard", reporting.markdown_table(baseline_features, ["Feature", "Paper wavelength nm", "Model wavelength nm", "Wavelength error nm", "Model normalized amplitude", "Status"])),
        ("7. Signed chi^(2) analysis", "`SIGNED_ZERO_ANALYSIS.csv` separates Re and Im crossings from minima of |chi|. A Re-only crossing is never classified as a full complex zero."),
        ("8. 605-nm sign/cancellation analysis", "The full result is in `SIGNED_ZERO_ANALYSIS.csv` and `ELECTRON_HH_CANCELLATION.csv`; the model minimum and signed crossings do not establish the paper's 605-nm |chi| node."),
        ("9. 1330-nm sign/cancellation analysis", "The model likewise fails the configured full-complex-zero criterion around the second paper dip."),
        ("10. Electron-vs-heavy-hole cancellation", reporting.markdown_table([r for r in cancellation if r["Feature"] in ("Z1", "Z2")], ["Feature", "wavelength_nm", "electron_abs", "heavy_hole_signed_abs", "total_abs", "phase_difference_deg", "cancellation_ratio"])),
        ("11. 16-pathway decomposition", "All 16 signed terms sum to total chi to numerical precision. Dominant positive/negative contributors at P1/Z1/P2/P3/Z2/P4 are ranked in `PATHWAY_FEATURE_BREAKDOWN.csv`. Prior literal-equation tests found no isolated bad term."),
        ("12. Transition/resonance map", "`RESONANCE_MAP.csv` distinguishes E=hw and E=2hw denominator conditions. The map supports an energy/numerator discrimination rather than treating every spectral extremum as one named transition."),
        ("13. Broadening sensitivity", "The 2.5/5/7.5/10 meV ladder changes widths and absorptive filling but is diagnostic only and is not used to tune the paper fit."),
        ("14. k-grid sensitivity", "Copied 101/201/301 grids were recomputed under identical physics. Grid variation is smaller than the topology mismatch."),
        ("15. kmax sensitivity", "The spectrum changes materially through 0.125 pi/a, contradicting a numerical convergence claim at the nominal 0.10 cutoff for this implementation."),
        ("16. Isotropy/radial-integration audit", "The alternate direction changes the energy-only spectrum, and Demo 23's isotropy gate fails. Two rays cannot produce a valid full 2D chi calculation."),
        ("17. State tracking and hh/lh mixing", "Only k=0 spinor composition is available. The selected `hh2` pair 3+4 is 97.6% LH, whereas pair 1+2 is 100% HH. This is direct evidence of a basis misassignment for a paper model that requests two HH states. The corrected-pair spectrum in the scorecard is diagnostic because avoided crossings and finite-k character exchange cannot be certified."),
        ("18. State-count adequacy", "The paper explicitly uses only the first two conduction and HH bound states. Additional states are low priority unless finite-k character shows that the tracked pair ceases to represent those physical states."),
        ("19. Finite-k matrix-element data audit", "E(k) exists; finite-k O(k), z_e(k), z_hh(k), complex envelopes, and spinors do not. The finite-k M(k) test is correctly flagged REQUIRES_NEW_PROFESSIONAL_DATA."),
        ("20. Finite-k M(k) diagnostic if possible", "Not possible from the copied output and therefore not fabricated."),
        ("21. Root-cause ranking", "Ranked using the Demo 24N perturbation evidence: features that respond to an energy shift are classified as denominator problems, features whose amplitude but not position responds are numerator problems, and features that no in-range perturbation can create are model-space problems.\n\n" + reporting.markdown_table(root_rows[:7], ["Rank", "Hypothesis", "Confidence", "Evidence for", "Evidence against", "Requires Pro rerun?"])),
        ("21b. Spectral Feature Causal Sensitivity Analysis (Demo 24N)", _causal_section(causal)),
        ("22. Independent physics-professor review", professor),
        ("22b. Independent physics-professor review of Demo 24N", professor_24n),
        ("23. Disagreements between agents", "Three positions are on the record and are deliberately not merged.\n\nThe first-pass primary analysis ranked HH/LH state misassignment first (0.98), geometry second, finite-k M(k) third and kmax fourth. The independent professor review disagreed, promoting the k cutoff on the grounds that the 540/1080 nm pair is an exact one-photon/two-photon pair of one transition and so points at a resonance the computed k range never reaches.\n\nThe Demo 24N causal study agrees with the professor that the 540/1080 pair is the decisive clue and that it is a resonance-range problem, but disagrees with the professor's remedy: extending kmax alone cannot work, because the electron subband crosses the barrier conduction edge at 0.73-0.85 /nm, where the transition energy has only reached about 1.97 eV, still 0.33 eV short of the 2.296 eV required. On the same evidence 24N demotes HH/LH misassignment from first to sixth, because reassigning hh2 to the pure-HH pair lowers E_hh2 by 19 meV and therefore drives P2 and P4 - the only two features that currently match - in the wrong direction at +0.46 and +0.92 nm/meV. The character observation itself is not disputed; only its status as the leading explanation is."),
        ("24. Professional rerun decision", "B. TARGETED PRO RUN RECOMMENDED, and Demo 24N sharpens what it must contain. The single implicated missing quantity is the finite-k numerator: complex O_nm(k), z_e_nl(k) and z_hh_ml(k) versus k, together with per-k complex spinors for state tracking and enough extra states to see whether anything reaches 2.296 eV. Finite-k M(k) is the one hypothesis that is both untested and capable of the required effect, and it is also what damps the high-k tail and removes the truncation artifact, so a longer k range without it would only relocate the artifact. Extending kmax is worth including in the same deck but is not sufficient on its own."),
        ("25. Exact recommended next step", "Run the proposed `targeted_professional_run/exact_paper_geometry_target.yaml` case on the work laptop after extending the deck output block to export per-k complex envelopes or the three required matrix families. Copy the complete raw result back."),
        ("26. Final conclusion", "The normalized-shape mismatch is not one fault. Demo 24N separates it into three. First, two of the paper's six features are already reproduced and are limited only by a single coherent 17 meV energy offset. Second, the other four require a 2.296 eV transition that no pair of bound subbands in this structure can reach at any k before the electron unbinds, so they are a model-space or structure problem and are untouchable by any parameter in the current calculation - this is the finding that most sharply constrains what to do next. Third, the model's own structure between 1250 and 1450 nm is an artifact of stopping the k integration with a frozen numerator, and should not be compared with the paper's node at all. Normalization, pathway sign and indexing, broadening, k-grid density and radial weighting are excluded as primary causes by direct test. One targeted Professional calculation exporting finite-k matrix elements over an extended k range, with extra states retained, is warranted; a full campaign is not."),
    ]
    report = ["# Demo 24 final report", ""]
    for title, body in sections:
        report.extend([f"## {title}", "", body, ""])
    reporting.write_text(output / "DEMO24_FINAL_REPORT.md", "\n".join(report))


def _causal_sensitivity_stage(config: Mapping[str, Any], baseline, frozen, settings,
                              wavelength: np.ndarray, paper: np.ndarray, tables: Path,
                              figures: Path, dpi: int, raw_case: Path,
                              kmax_spectra: Mapping[str, np.ndarray],
                              kmax_fractions: Mapping[str, float],
                              kmax_transition_max: Mapping[str, float],
                              longest_kmax: Mapping[str, Any]) -> dict[str, Any]:
    """Demo 24N - controlled one-at-a-time diagnostic perturbations.

    Nothing here changes the Demo 23 production physics. The instrumented
    evaluator is proved identical to the production engine before use, and
    every perturbed spectrum is labelled as a diagnostic.
    """
    block = config["causal_sensitivity"]
    specs = causal_sensitivity.feature_specs(config)
    k = baseline.transitions.k_per_nm
    electron = np.vstack([baseline.subbands_eV["e1"], baseline.subbands_eV["e2"]])
    hole = np.vstack([baseline.subbands_eV["hh1"], baseline.subbands_eV["hh2"]])

    def build(amplitude: Mapping[str, float] | None = None,
              phase: Mapping[str, float] | None = None,
              keep: bool = False):
        return causal_sensitivity.instrumented_spectrum(
            wavelength, k, electron, hole, frozen.overlap_eh, frozen.z_e_nm, frozen.z_hh_nm,
            broadening_meV=settings.broadening_meV, settings=settings,
            amplitude_scale=amplitude, phase_shift_rad=phase, keep_k_integrand=keep)

    instrumented = build(keep=True)
    mirror_error = causal_sensitivity.assert_matches_production(instrumented, baseline.spectrum)
    matched = causal_sensitivity.match_features(wavelength, baseline.spectrum.chi2, specs)

    edges = causal_sensitivity.band_edges(raw_case)
    reporting.write_json(tables / "BAND_EDGES.json", edges)
    reach = causal_sensitivity.resonance_reachability(
        instrumented, specs, settings.k_parallel_fraction_of_bz, edges)
    traceback = causal_sensitivity.feature_traceback(instrumented, specs, matched)
    kregion = causal_sensitivity.k_region_sensitivity(
        instrumented, specs, settings.k_parallel_fraction_of_bz, float(np.max(k)))
    reporting.write_csv(tables / "RESONANCE_REACHABILITY.csv", reach)
    reporting.write_csv(tables / "FEATURE_CAUSAL_TRACEBACK.csv", traceback)
    reporting.write_csv(tables / "RESONANCE_BAND_EDGES.csv",
                        causal_sensitivity.band_edges_of_transitions(instrumented))
    reporting.write_csv(tables / "FEATURE_K_REGION_SENSITIVITY.csv", kregion)
    extrapolation = causal_sensitivity.extrapolation_validation(
        k, baseline.subbands_eV, longest_kmax["k_per_nm"], longest_kmax["subbands"],
        float(edges["barrier_conduction_edge_eV"]))
    reporting.write_csv(tables / "EXTRAPOLATION_VALIDATION.csv", extrapolation)

    energy_rows, energy_spectra = causal_sensitivity.energy_sensitivity(
        baseline.subbands_eV, k, wavelength, frozen, settings, paper, specs,
        [float(v) for v in block["energy_shifts_meV"]])
    derivatives = causal_sensitivity.energy_derivatives(energy_rows)
    reach_by_feature = {str(row["Feature"]): row for row in reach}
    statements = causal_sensitivity.shift_direction_statements(derivatives, reach_by_feature)
    reporting.write_csv(tables / "ENERGY_FEATURE_SENSITIVITY.csv", energy_rows)
    reporting.write_csv(tables / "ENERGY_FEATURE_DERIVATIVES.csv", derivatives)
    reporting.write_csv(tables / "ENERGY_SHIFT_DIRECTION_STATEMENTS.csv", statements)

    count = int(block["dominant_pathway_count"])
    labels: list[str] = []
    for spec in specs:
        for label in causal_sensitivity.dominant_pathways(instrumented, float(spec["wavelength_nm"]), count):
            if label not in labels:
                labels.append(label)
    amplitude_rows = causal_sensitivity.amplitude_sensitivity(
        instrumented, lambda scale: build(amplitude=scale), labels,
        [float(v) for v in block["amplitude_scales"]], specs, paper)
    reporting.write_csv(tables / "PATHWAY_AMPLITUDE_SENSITIVITY.csv", amplitude_rows)
    node_rows = causal_sensitivity.node_cancellation_rows(instrumented, specs)
    reporting.write_csv(tables / "NODE_CANCELLATION_SENSITIVITY.csv", node_rows)

    phase_content = causal_sensitivity.numerator_phase_content(instrumented)
    node_labels: list[str] = []
    for spec in specs:
        if str(spec["type"]) != "minimum":
            continue
        for label in causal_sensitivity.dominant_pathways(instrumented, float(spec["wavelength_nm"]), 3):
            if label not in node_labels:
                node_labels.append(label)
    phase_rows = causal_sensitivity.phase_sensitivity(
        instrumented, lambda phase: build(phase=phase), node_labels,
        [float(v) for v in block["phase_degrees"]], specs)
    reporting.write_csv(tables / "PHASE_SENSITIVITY.csv", phase_rows)
    reporting.write_json(tables / "NUMERATOR_PHASE_CONTENT.json", phase_content)

    cutoff_rows = causal_sensitivity.cutoff_artifact_test(
        wavelength, kmax_spectra, kmax_fractions, kmax_transition_max,
        prominence=float(config["analysis"]["peak_prominence_fraction"]),
        distance_nm=float(config["analysis"]["peak_minimum_distance_nm"]))
    reporting.write_csv(tables / "CUTOFF_ARTIFACT_TEST.csv", cutoff_rows)

    diagnosis = causal_sensitivity.causal_diagnosis(
        traceback, derivatives, amplitude_rows, kregion, reach, phase_rows)
    reporting.write_csv(tables / "SPECTRAL_FEATURE_CAUSAL_DIAGNOSIS.csv", diagnosis)
    reporting.write_text(
        tables / "FEATURE_CAUSAL_STATEMENTS.md",
        "# Demo 24N per-feature causal statements\n\n"
        f"{causal_sensitivity.DIAGNOSTIC_BANNER}\n\n```\n"
        + causal_sensitivity.causal_statements(diagnosis, traceback, node_rows, kregion) + "```\n")

    plotting.feature_energy_sensitivity(
        figures / "figure21_peak_energy_sensitivity.png", energy_rows, "peak",
        "Figure 21 - peak wavelength sensitivity to one-at-a-time subband shifts", dpi)
    plotting.feature_energy_sensitivity(
        figures / "figure22_zero_energy_sensitivity.png", energy_rows, "minimum",
        "Figure 22 - zero/minimum location sensitivity to one-at-a-time subband shifts", dpi)
    plotting.node_amplitude_sensitivity(
        figures / "figure23_node605_amplitude_sensitivity.png", amplitude_rows, "Z1",
        "Figure 23 - 605 nm node depth vs single-pathway numerator scaling", dpi)
    plotting.node_amplitude_sensitivity(
        figures / "figure24_node1330_amplitude_sensitivity.png", amplitude_rows, "Z2",
        "Figure 24 - 1330 nm node depth vs single-pathway numerator scaling", dpi)
    plotting.sensitivity_heatmap(figures / "figure25_feature_parameter_heatmap.png", derivatives, dpi)
    plotting.causal_traceback_diagram(figures / "figure26_causal_traceback.png", diagnosis, dpi)

    unreachable = [str(row["Feature"]) for row in reach if str(row["reachable"]) == "no"]
    truncated = [str(row["Feature"]) for row in kregion if bool(row["k_peak_at_grid_edge"])]
    beyond_bound = [str(row["Feature"]) for row in reach
                    if str(row["reachable_with_bound_states_at_any_k"]).startswith("no")]
    return {
        "band_edges": edges,
        "features_beyond_any_bound_subband_transition": beyond_bound,
        "mirror_max_abs_error_pm_per_V": mirror_error,
        "perturbed_spectra": len(energy_spectra),
        "features_outside_model_resonance_band": unreachable,
        "features_with_truncated_k_integrand": truncated,
        "numerator_phase_is_a_free_parameter": bool(phase_content["numerator_phase_is_a_free_parameter"]),
        "cutoff_artifacts": cutoff_rows,
        "extrapolation_validation": extrapolation,
        "reachability": reach,
        "energy_rows": energy_rows,
        "traceback": traceback,
        "k_region": kregion,
        "derivatives": derivatives,
        "direction_statements": statements,
        "node_cancellation": node_rows,
        "diagnosis": diagnosis,
        "perturbed_pathways": labels,
    }


def run() -> dict[str, Any]:
    config = load_config()
    cfg23 = load_demo23_config()
    specs = deck23.deck_specs(cfg23)
    run_root = locate_demo23_root(config, specs)
    output = resolve_repo_path(str(config["outputs"]["root"]))
    tables = output
    figures = output / "figures"
    dpi = int(config["outputs"]["dpi"])
    reanalysis = resolve_repo_path(str(config["inputs"]["demo23_reanalysis"]))

    frozen = physics23.load_frozen_k0_inputs(cfg23)
    settings = physics23.settings_from_config(cfg23)
    wavelength = physics23.wavelength_grid(cfg23)
    production_spec = next(spec for spec in specs if spec.role == "production")
    tracked = analysis23._load_spec(run_root, production_spec, cfg23, output / "inventories", frozen)
    results, fits, aligned = analysis23._evaluate_spec(tracked, frozen, settings, wavelength, cfg23, ("23A", "23B", "23C", "23D"))
    for result in results.values():
        pathway_analysis.assert_consistency(result)
    baseline = results["23D"]
    corrected_label = "24_state_corrected_hh2_pair1+2"
    corrected = _hh2_character_corrected_result(
        run_root / "raw" / production_spec.name, tracked, frozen, settings, wavelength, cfg23)
    pathway_analysis.assert_consistency(corrected)

    paper_x, paper_y = paper_feature_analysis.load_curve(resolve_repo_path(str(config["inputs"]["paper_curve"])))
    paper = _paper_on_grid(wavelength, paper_x, paper_y)
    paper_features = paper_feature_analysis.paper_feature_table(paper_x, paper_y, config["paper_features"])
    reporting.write_csv(tables / "PAPER_TARGET_FEATURES.csv", paper_features)

    comparison_results = {**results, corrected_label: corrected}
    feature_rows = [row for mode, result in comparison_results.items() for row in _model_feature_rows(mode, result, paper_features, config)]
    reporting.write_csv(tables / "FEATURE_SCORECARD.csv", feature_rows)
    zero_rows = _signed_zero_rows(comparison_results, config)
    reporting.write_csv(tables / "SIGNED_ZERO_ANALYSIS.csv", zero_rows)

    zero_windows = _feature_windows(config)
    model_metrics = []
    local_rows = []
    for mode, result in comparison_results.items():
        model_metrics.append(sensitivity_analysis.spectrum_metrics(
            mode, wavelength, result.spectrum.chi2, paper, zero_windows,
            prominence=float(config["analysis"]["peak_prominence_fraction"]),
            distance_nm=float(config["analysis"]["peak_minimum_distance_nm"])))
        local_rows.extend(_local_rmse_rows(mode, wavelength, paper, result.spectrum.chi2, config["analysis"]["local_windows_nm"]))
    reporting.write_csv(tables / "MODEL_SHAPE_METRICS.csv", model_metrics)
    reporting.write_csv(tables / "LOCAL_RMSE.csv", local_rows)

    cancellation = pathway_analysis.cancellation_rows(baseline, paper_features)
    breakdown = pathway_analysis.feature_breakdown(baseline, paper_features)
    reporting.write_csv(tables / "ELECTRON_HH_CANCELLATION.csv", cancellation)
    reporting.write_csv(tables / "PATHWAY_FEATURE_BREAKDOWN.csv", breakdown)
    pathway_spectra = []
    for label, values in zip(baseline.spectrum.term_labels, baseline.spectrum.terms):
        for x, value in zip(wavelength, values):
            pathway_spectra.append({"wavelength_nm": float(x), "pathway": label, "real": float(value.real),
                                    "imag": float(value.imag), "magnitude": float(abs(value))})
    reporting.write_csv(tables / "PATHWAY_SPECTRA.csv", pathway_spectra)

    resonance_rows = resonance_analysis.resonance_rows(
        baseline.transitions.k_per_nm, baseline.transitions.as_dict())
    reporting.write_csv(tables / "RESONANCE_MAP.csv", resonance_rows)

    models, _, _ = analysis23._models_for(tracked, frozen, settings)
    gamma_spectra: dict[str, np.ndarray] = {}
    gamma_rows = []
    for gamma in config["analysis"]["gamma_meV"]:
        gamma_settings = physics23.validated.replace_settings(settings, broadening_meV=float(gamma))
        result = physics23.evaluate_mode("23D", models["23D"], baseline.transitions.k_per_nm, wavelength,
                                         frozen, gamma_settings,
                                         k0_tolerance_eV=float(cfg23["validation"]["k0_transition_tolerance_eV"]))
        label = f"Gamma={float(gamma):g} meV"
        gamma_spectra[label] = result.spectrum.chi2
        row = sensitivity_analysis.spectrum_metrics(label, wavelength, result.spectrum.chi2, paper, zero_windows)
        row["Gamma_meV"] = float(gamma)
        gamma_rows.append(row)
    reporting.write_csv(tables / "BROADENING_SENSITIVITY.csv", gamma_rows)

    grid_spectra: dict[str, np.ndarray] = {}
    grid_rows = []
    kmax_spectra: dict[str, np.ndarray] = {}
    kmax_fractions: dict[str, float] = {}
    kmax_transition_max: dict[str, float] = {}
    longest_kmax: dict[str, Any] = {}
    kmax_rows = []
    iso_spectra: dict[str, np.ndarray] = {"production [010]": baseline.spectrum.chi2}
    iso_rows = []
    for spec in specs:
        if spec.role == "production":
            result = baseline
        else:
            case_tracked = analysis23._load_spec(run_root, spec, cfg23, output / "inventories", frozen)
            case_settings = analysis23._settings_for_spec(settings, spec)
            case_results, _, _ = analysis23._evaluate_spec(case_tracked, frozen, case_settings, wavelength, cfg23, ("23D",))
            result = case_results["23D"]
        if spec.role in ("grid_convergence", "production"):
            label = f"Nk={spec.points}"
            grid_spectra[label] = result.spectrum.chi2
            row = sensitivity_analysis.spectrum_metrics(label, wavelength, result.spectrum.chi2, paper, zero_windows)
            row.update({"N_k": spec.points, "fraction_of_bz": spec.fraction_of_bz})
            grid_rows.append(row)
        if spec.role in ("kmax_convergence", "production"):
            label = f"kmax={spec.fraction_of_bz:g} pi/a"
            kmax_spectra[label] = result.spectrum.chi2
            kmax_fractions[label] = float(spec.fraction_of_bz)
            kmax_transition_max[label] = float(max(np.max(v) for v in result.transitions.as_dict().values()))
            if float(spec.fraction_of_bz) >= float(longest_kmax.get("fraction_of_bz", -1.0)):
                longest_kmax = {"fraction_of_bz": float(spec.fraction_of_bz),
                                "k_per_nm": result.transitions.k_per_nm,
                                "subbands": result.subbands_eV}
            row = sensitivity_analysis.spectrum_metrics(label, wavelength, result.spectrum.chi2, paper, zero_windows)
            row.update({"N_k": spec.points, "fraction_of_bz": spec.fraction_of_bz})
            kmax_rows.append(row)
        if spec.role == "isotropy":
            label = f"alternate {spec.direction}"
            iso_spectra[label] = result.spectrum.chi2
    reporting.write_csv(tables / "KGRID_SENSITIVITY.csv", sorted(grid_rows, key=lambda r: int(r["N_k"])))
    reporting.write_csv(tables / "KMAX_SENSITIVITY.csv", sorted(kmax_rows, key=lambda r: float(r["fraction_of_bz"])))
    for label, chi in iso_spectra.items():
        row = sensitivity_analysis.spectrum_metrics(label, wavelength, chi, paper, zero_windows)
        row["relative_complex_RMSE_vs_production"] = float(np.sqrt(np.mean(np.abs(chi - baseline.spectrum.chi2) ** 2)) / max(np.max(np.abs(baseline.spectrum.chi2)), 1e-300))
        iso_rows.append(row)
    reporting.write_csv(tables / "ISOTROPY_SPECTRAL_SENSITIVITY.csv", iso_rows)

    state_rows = _state_character_rows(run_root / "raw" / production_spec.name, tracked)
    reporting.write_csv(tables / "STATE_MIXING_AUDIT.csv", state_rows)
    finite_rows = finite_k_matrix_audit.inventory(run_root / "raw" / production_spec.name)
    reporting.write_csv(tables / "FINITE_K_DATA_INVENTORY.csv", finite_rows)
    finite_status = "AVAILABLE"
    try:
        finite_k_matrix_audit.require_finite_k_matrices(finite_rows)
    except finite_k_matrix_audit.ProfessionalDataRequired as exc:
        finite_status = str(exc)
    reporting.write_text(tables / "FINITE_K_TEST_STATUS.txt", finite_status)

    causal = _causal_sensitivity_stage(config, baseline, frozen, settings, wavelength, paper,
                                       tables, figures, dpi, run_root / "raw" / production_spec.name,
                                       kmax_spectra, kmax_fractions, kmax_transition_max, longest_kmax)

    audit_rows = _audit_rows(run_root, specs, reanalysis)
    geometry_rows = _geometry_audit()
    _write_audit_reports(output, audit_rows, geometry_rows, finite_rows)
    reporting.write_csv(tables / "PAPER_STRUCTURE_AUDIT.csv", geometry_rows)
    root_rows = _root_cause_rows(causal)
    reporting.write_csv(tables / "ROOT_CAUSE_RANKING.csv", root_rows)
    reporting.write_text(tables / "PROFESSIONAL_RERUN_RECOMMENDATION.md", professional_rerun_assessment.recommendation())
    _write_target_config(output)

    e, h = pathway_analysis.subtotals(baseline)
    plotting.overlay(figures / "figure01_paper_vs_demo23D.png", wavelength, paper, {"Demo 23D |chi|": baseline.spectrum.chi2}, paper_features, "Paper vs Demo 23D normalized spectrum", dpi)
    plotting.peak_errors(figures / "figure02_peak_wavelength_error.png", [r for r in feature_rows if r["Model"] == "23D"], dpi)
    plotting.complex_components(figures / "figure03_signed_complex_full.png", wavelength, baseline.spectrum.chi2, "Demo 23D signed complex spectrum", dpi)
    plotting.complex_components(figures / "figure04_zoom_500_700.png", wavelength, baseline.spectrum.chi2, "Demo 23D around Z1", dpi, (500, 700))
    plotting.complex_components(figures / "figure05_zoom_1200_1400.png", wavelength, baseline.spectrum.chi2, "Demo 23D around Z2", dpi, (1200, 1400))
    plotting.subtotals(figures / "figure06_electron_hh_full.png", wavelength, e, h, "Electron vs signed heavy-hole subtotals", dpi)
    plotting.subtotals(figures / "figure07_electron_hh_605.png", wavelength, e, h, "Cancellation around 605 nm", dpi, (500, 700))
    plotting.subtotals(figures / "figure08_electron_hh_1330.png", wavelength, e, h, "Cancellation around 1330 nm", dpi, (1200, 1400))
    plotting.pathways(figures / "figure09_all_pathways_real.png", wavelength, baseline.spectrum.terms, baseline.spectrum.term_labels, "real", "All 16 pathway real components", dpi)
    plotting.pathways(figures / "figure10_all_pathways_imag.png", wavelength, baseline.spectrum.terms, baseline.spectrum.term_labels, "imag", "All 16 pathway imaginary components", dpi)
    plotting.pathways(figures / "figure11_dominant_P1_Z1_P2.png", wavelength, baseline.spectrum.terms, baseline.spectrum.term_labels, "real", "Dominant pathways: P1/Z1/P2", dpi, (450, 850), 6)
    plotting.pathways(figures / "figure12_dominant_P3_Z2_P4.png", wavelength, baseline.spectrum.terms, baseline.spectrum.term_labels, "real", "Dominant pathways: P3/Z2/P4", dpi, (900, 1650), 6)
    plotting.resonance_map(figures / "figure13_resonance_map.png", resonance_rows, paper_features, dpi)
    plotting.sensitivity(figures / "figure14_broadening_sensitivity.png", wavelength, gamma_spectra, paper, "Broadening sensitivity (diagnostic, not fitting)", dpi)
    plotting.sensitivity(figures / "figure15_kgrid_sensitivity.png", wavelength, grid_spectra, paper, "k-grid sensitivity", dpi)
    plotting.sensitivity(figures / "figure16_kmax_sensitivity.png", wavelength, kmax_spectra, paper, "kmax sensitivity", dpi)
    plotting.state_character(figures / "figure17_state_character.png", state_rows, dpi)
    plotting.sensitivity(figures / "figure18_finite_k_matrix_status.png", wavelength, {"M(k)=M(0) only; finite-k data missing": baseline.spectrum.chi2}, paper, "Finite-k M(k) test unavailable - baseline shown", dpi)
    plotting.overlay(figures / "figure19_best_available_vs_paper.png", wavelength, paper,
                     {"Demo 23D": baseline.spectrum.chi2,
                      "Diagnostic: HH-character pair 1+2": corrected.spectrum.chi2},
                     paper_features, "State-identity diagnostic vs paper (not a validated replacement)", dpi)
    plotting.ranking(figures / "figure20_root_cause_ranking.png", root_rows, dpi)

    # "Best Demo 24 diagnostic" means the closest of every labelled diagnostic candidate:
    # the hh2 state-identity variant and the whole 24N one-at-a-time energy ladder. It is
    # chosen per feature by smallest |error|, never assumed, and it is never a fitted model.
    feature_summary = []
    corrected_by_feature = {r["Feature"]: r for r in feature_rows if r["Model"] == corrected_label}
    causal_by_feature: dict[str, list[dict[str, Any]]] = {}
    for row in causal["energy_rows"]:
        if float(row["shift_meV"]) == 0.0:
            continue
        causal_by_feature.setdefault(str(row["Feature"]), []).append(row)
    mechanism = {str(r["Feature"]): r for r in causal["diagnosis"]}
    for row in [r for r in feature_rows if r["Model"] == "23D"]:
        name = str(row["Feature"])
        paper = float(row["Paper wavelength nm"])
        candidates = [(corrected_label, float(corrected_by_feature[name]["Model wavelength nm"]))]
        candidates += [(f"{r['state']}{float(r['shift_meV']):+g} meV", float(r["model_wavelength_nm"]))
                       for r in causal_by_feature.get(name, [])]
        candidates.append(("23D baseline", float(row["Model wavelength nm"])))
        label, best = min(candidates, key=lambda item: abs(item[1] - paper))
        if mechanism[name]["Model_feature_is_window_edge"]:
            # every candidate lands on the same window edge, so naming one is meaningless
            label = "n/a - the model has no extremum in this window"
        tolerance = float(next(t["Digitization uncertainty nm"] for t in paper_features
                               if t["Feature"] == name))
        feature_summary.append({
            "Feature": name, "Paper": paper, "Demo23D": row["Model wavelength nm"],
            "Best Demo24 diagnostic": best, "Best diagnostic source": label,
            "Difference": best - paper,
            "Status": ("DIAGNOSTIC_ONLY_MATCH" if abs(best - paper) <= tolerance
                       else "DIAGNOSTIC_ONLY_MISMATCH"),
            "24N mechanism": str(mechanism[name]["Likely_root_cause"]).split(":")[0],
            "Model feature is a window edge": mechanism[name]["Model_feature_is_window_edge"],
        })
    reporting.write_csv(tables / "FEATURE_SUMMARY.csv", feature_summary)
    hypothesis_summary = [{"Hypothesis": r["Hypothesis"], "Tested?": r["Can test from existing data?"],
                           "Result": r["Evidence against"], "Likelihood": r["Confidence"], "Pro rerun?": r["Requires Pro rerun?"]}
                          for r in root_rows]
    reporting.write_csv(tables / "HYPOTHESIS_SUMMARY.csv", hypothesis_summary)

    summary = {
        "status": "PRIMARY_ANALYSIS_COMPLETE", "demo23_root": str(run_root), "output": str(output),
        "finite_k_test": finite_status, "model_metrics": model_metrics,
        "baseline_features": [r for r in feature_rows if r["Model"] == "23D"],
        "state_corrected_features": [r for r in feature_rows if r["Model"] == corrected_label],
        "state_corrected_metrics": next(r for r in model_metrics if r["case"] == corrected_label),
        "zero_analysis": [r for r in zero_rows if r["model"] == "23D"],
        "cancellation": cancellation, "top_root_causes": root_rows[:5],
        "professional_rerun": "B. TARGETED PRO RUN RECOMMENDED",
    }
    reporting.write_json(tables / "demo24_summary.json", summary)
    _write_professor_input(output, summary)
    _final_report(output, summary, feature_rows, root_rows, cancellation, causal)
    return summary


def run_tests() -> int:
    """Run the Demo 24 suite.

    pytest's default basetemp is used deliberately. Pointing --basetemp inside
    the repository makes pytest rmtree that directory on every run, which fails
    with WinError 5 on Windows and turns every tmp_path test into a setup error.
    """
    import subprocess
    return subprocess.run([sys.executable, "-m", "pytest", str(DEMO_DIR / "tests"), "-q",
                           "-p", "no:cacheprovider"],
                          cwd=REPO_ROOT, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args(argv)
    if args.tests:
        return run_tests()
    print(json.dumps(run(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
