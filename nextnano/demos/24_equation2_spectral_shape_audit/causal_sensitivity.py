"""Demo 24N - spectral-feature causal sensitivity debugger.

Every routine here is a *diagnostic* post-processing experiment on the copied
Demo 23 Professional output. Nothing in this module launches nextnano, edits
Demo 23, or claims that a perturbed spectrum is a physical or fitted model.

The instrumented evaluator below is a line-by-line mirror of the production
adapter ``chi2_22.chi2_from_k_inputs``. It exists only so that a single
pathway numerator can be scaled or phase-rotated and so that the k-resolved
integrand survives per pathway. ``assert_matches_production`` proves the mirror
reproduces the production engine to machine precision before any perturbation
is trusted.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import chi2_22
import signed_spectrum
from physics23 import validated


DIAGNOSTIC_BANNER = "DIAGNOSTIC PERTURBATION - NOT A PHYSICAL/FITTED MODEL"
STATE_KEYS = ("e1", "e2", "hh1", "hh2")


@dataclass(frozen=True)
class PathwayMeta:
    """Static Equation-2 bookkeeping for one of the 16 pathways."""

    index: int
    label: str
    side: str                    # electron_side | heavy_hole_side_signed
    m: int                       # hole index (1-based)
    n: int                       # electron index (1-based)
    ell: int                     # intermediate index (1-based)
    two_photon_transition: str   # denominator resonant at 2*hbar*omega
    one_photon_transition: str   # denominator resonant at 1*hbar*omega
    numerator_expression: str


@dataclass(frozen=True)
class InstrumentedSpectrum:
    wavelength_nm: np.ndarray
    k_per_nm: np.ndarray
    chi2: np.ndarray
    terms: np.ndarray                    # (16, n_lambda)
    term_labels: tuple[str, ...]
    k_weights: np.ndarray
    transition_eV: np.ndarray            # (2, 2, n_k) indexed [n, m]
    electron_energies_eV: np.ndarray     # (2, n_k)
    hole_energies_eV: np.ndarray         # (2, n_k)
    numerators: np.ndarray               # (16, n_k) complex
    k_integrand: np.ndarray | None       # (16, n_lambda, n_k); sums over k to `terms`


def pathway_metadata() -> tuple[PathwayMeta, ...]:
    """Return the 16 pathways in exactly the production emission order."""
    meta: list[PathwayMeta] = []
    index = 0
    for m in range(2):
        for n in range(2):
            two_photon = f"DeltaE_{n + 1}{m + 1}"
            for ell in range(2):
                meta.append(PathwayMeta(
                    index, f"C_m{m + 1}_n{n + 1}_l{ell + 1}", "electron_side",
                    m + 1, n + 1, ell + 1, two_photon, f"DeltaE_{ell + 1}{m + 1}",
                    f"O[{n + 1},{m + 1}]*z_e[{n + 1},{ell + 1}]*O[{ell + 1},{m + 1}]"))
                index += 1
            for ell in range(2):
                meta.append(PathwayMeta(
                    index, f"V_m{m + 1}_n{n + 1}_l{ell + 1}", "heavy_hole_side_signed",
                    m + 1, n + 1, ell + 1, two_photon, f"DeltaE_{n + 1}{ell + 1}",
                    f"-O[{n + 1},{m + 1}]*z_hh[{m + 1},{ell + 1}]*O[{n + 1},{ell + 1}]"))
                index += 1
    return tuple(meta)


PATHWAYS = pathway_metadata()
PATHWAY_BY_LABEL = {item.label: item for item in PATHWAYS}


def instrumented_spectrum(
    wavelengths_nm: np.ndarray,
    k_per_nm: np.ndarray,
    electron_energies_eV: np.ndarray,
    hole_energies_eV: np.ndarray,
    overlap_eh: np.ndarray,
    z_e_nm: np.ndarray,
    z_h_nm: np.ndarray,
    *,
    broadening_meV: float,
    settings: validated.Chi2Settings,
    amplitude_scale: Mapping[str, float] | None = None,
    phase_shift_rad: Mapping[str, float] | None = None,
    keep_k_integrand: bool = False,
) -> InstrumentedSpectrum:
    """Mirror of ``chi2_22.chi2_from_k_inputs`` with per-pathway instrumentation.

    ``amplitude_scale``/``phase_shift_rad`` multiply a single pathway numerator
    by a real factor / ``exp(i*phi)``. With both omitted the result reproduces
    the production calculation (see ``assert_matches_production``).
    """
    k = np.asarray(k_per_nm, dtype=float)
    ee = np.asarray(electron_energies_eV, dtype=float)
    eh = np.asarray(hole_energies_eV, dtype=float)
    if ee.shape != (2, len(k)) or eh.shape != (2, len(k)):
        raise ValueError("electron/hole energies must each have shape (2,nk)")
    transition = ee[:, None, :] - eh[None, :, :]
    if np.any(transition <= 0) or not np.all(np.isfinite(transition)):
        raise ValueError("all Ee-Eh transition energies must be finite and positive")
    o = chi2_22._as_k_matrix(overlap_eh, (2, 2), len(k))
    ze = chi2_22._as_k_matrix(z_e_nm, (2, 2), len(k))
    zh = chi2_22._as_k_matrix(z_h_nm, (2, 2), len(k))
    config = settings
    if abs(config.broadening_meV - float(broadening_meV)) > 1e-15:
        config = validated.replace_settings(config, broadening_meV=float(broadening_meV))
    weights = chi2_22.radial_weights(k, config.spin_degeneracy)
    prefactor = validated.absolute_prefactor(config)
    lam = np.asarray(wavelengths_nm, dtype=float)
    hw = validated.HC_EV_NM / lam
    gamma = float(broadening_meV) * 1e-3
    scales = dict(amplitude_scale or {})
    phases = dict(phase_shift_rad or {})
    unknown = (set(scales) | set(phases)) - set(PATHWAY_BY_LABEL)
    if unknown:
        raise ValueError(f"unknown pathway label(s): {sorted(unknown)}")

    terms = np.empty((len(PATHWAYS), len(lam)), dtype=complex)
    numerators = np.empty((len(PATHWAYS), len(k)), dtype=complex)
    integrand = np.empty((len(PATHWAYS), len(lam), len(k)), dtype=complex) if keep_k_integrand else None
    for item in PATHWAYS:
        m, n, ell = item.m - 1, item.n - 1, item.ell - 1
        d2 = transition[n, m][None, :] - 2 * hw[:, None] + 1j * gamma
        if item.side == "electron_side":
            numerator = o[n, m] * ze[n, ell] * o[ell, m]
            d1 = transition[ell, m][None, :] - hw[:, None] + 1j * gamma
        else:
            numerator = -o[n, m] * zh[m, ell] * o[n, ell]
            d1 = transition[n, ell][None, :] - hw[:, None] + 1j * gamma
        numerator = np.asarray(numerator, dtype=complex)
        factor = float(scales.get(item.label, 1.0)) * np.exp(1j * float(phases.get(item.label, 0.0)))
        numerator = numerator * factor
        numerators[item.index] = numerator
        value = numerator / (d2 * d1)
        terms[item.index] = prefactor * (value @ weights)
        if integrand is not None:
            integrand[item.index] = prefactor * value * weights[None, :]
    return InstrumentedSpectrum(
        lam, k, terms.sum(axis=0), terms, tuple(item.label for item in PATHWAYS),
        weights, transition, ee, eh, numerators, integrand)


def assert_matches_production(instrumented: InstrumentedSpectrum, production) -> float:
    """Fail loudly unless the mirror reproduces the production engine."""
    if tuple(instrumented.term_labels) != tuple(production.term_labels):
        raise AssertionError("instrumented pathway ordering differs from production")
    error = float(np.max(np.abs(instrumented.chi2 - production.chi2)))
    scale = max(float(np.max(np.abs(production.chi2))), 1e-300)
    term_error = float(np.max(np.abs(instrumented.terms - production.terms)))
    if error / scale > 1e-12 or term_error / scale > 1e-12:
        raise AssertionError(
            f"instrumented mirror disagrees with production: chi {error:g}, terms {term_error:g}")
    if instrumented.k_integrand is not None:
        summed = instrumented.k_integrand.sum(axis=2)
        if float(np.max(np.abs(summed - instrumented.terms))) / scale > 1e-12:
            raise AssertionError("k-resolved integrand does not sum back to the pathway terms")
    return error


# ---------------------------------------------------------------------------
# feature bookkeeping shared with the primary Demo 24 scorecard
# ---------------------------------------------------------------------------

def feature_specs(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in config["paper_features"]["expected"]]


def match_features(wavelength_nm: np.ndarray, chi: np.ndarray,
                   specs: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    """Locate each paper feature in a model spectrum using the primary rule.

    Peaks take the window maximum and minima the window minimum of the
    normalized magnitude, exactly as ``run_demo24._model_feature_rows`` does.
    """
    x = np.asarray(wavelength_nm, dtype=float)
    norm = signed_spectrum.normalize(chi)
    out: dict[str, dict[str, float]] = {}
    for spec in specs:
        lo, hi = map(float, spec["window_nm"])
        local = np.flatnonzero((x >= lo) & (x <= hi))
        window = norm[local]
        index = int(local[np.argmax(window)]) if spec["type"] == "peak" else int(local[np.argmin(window)])
        out[str(spec["name"])] = {
            "wavelength_nm": float(x[index]),
            "normalized_amplitude": float(norm[index]),
            "amplitude_at_paper_nm": float(np.interp(float(spec["wavelength_nm"]), x, norm)),
            # A hit on the first or last sample of the window is the window edge, not a
            # turning point: the model has no extremum there and the reported wavelength
            # is set by the search window rather than by any physics.
            "at_window_edge": float(index in (int(local[0]), int(local[-1]))),
        }
    return out


def local_rmse(wavelength_nm: np.ndarray, paper: np.ndarray, model: np.ndarray,
               window_nm: Sequence[float]) -> float:
    x = np.asarray(wavelength_nm, dtype=float)
    mask = (x >= float(window_nm[0])) & (x <= float(window_nm[1]))
    p, m = signed_spectrum.normalize(paper), signed_spectrum.normalize(model)
    return float(np.sqrt(np.mean((p[mask] - m[mask]) ** 2)))


def _window_for(spec: Mapping[str, Any], span_nm: float = 90.0) -> tuple[float, float]:
    centre = float(spec["wavelength_nm"])
    return (centre - 0.5 * span_nm, centre + 0.5 * span_nm)


# ---------------------------------------------------------------------------
# 24N.1 - feature-by-feature traceback
# ---------------------------------------------------------------------------

def _k_region(weights_abs: np.ndarray, k: np.ndarray) -> dict[str, float]:
    """Peak k and the contiguous bands carrying 50% and 90% of the contribution.

    The band is grown outward from the peak rather than assembled from the
    largest samples anywhere, so the reported interval is the region that
    actually dominates and its endpoints bracket the peak.
    """
    total = float(np.sum(weights_abs))
    if total <= 0.0:
        return {"k_peak_per_nm": float("nan"), "k50_lo_per_nm": float("nan"),
                "k50_hi_per_nm": float("nan"), "k90_lo_per_nm": float("nan"),
                "k90_hi_per_nm": float("nan")}
    peak = int(np.argmax(weights_abs))

    def span(fraction: float) -> tuple[float, float]:
        lo = hi = peak
        captured = float(weights_abs[peak])
        target = fraction * total
        while captured < target and (lo > 0 or hi < len(k) - 1):
            left = float(weights_abs[lo - 1]) if lo > 0 else -1.0
            right = float(weights_abs[hi + 1]) if hi < len(k) - 1 else -1.0
            if right >= left:
                hi += 1
                captured += right
            else:
                lo -= 1
                captured += left
        return float(k[lo]), float(k[hi])

    lo50, hi50 = span(0.5)
    lo90, hi90 = span(0.9)
    return {"k_peak_per_nm": float(k[peak]),
            "k50_lo_per_nm": lo50, "k50_hi_per_nm": hi50,
            "k90_lo_per_nm": lo90, "k90_hi_per_nm": hi90}


def band_edges_of_transitions(instrumented: InstrumentedSpectrum) -> list[dict[str, object]]:
    """Wavelengths of every one- and two-photon resonance band edge.

    Inside a band every wavelength is resonant at *some* k, so the integrated
    spectrum is smooth there; the sharp features sit at the band edges, where
    the resonant k reaches the start or the end of the grid. The k=0 edge is
    physical (a joint-density-of-states edge); the k=kmax edge is created by
    stopping the integration and is therefore a truncation artifact.
    """
    k = instrumented.k_per_nm
    rows: list[dict[str, object]] = []
    for n in range(2):
        for m in range(2):
            row = instrumented.transition_eV[n, m]
            for order, factor in (("one-photon", 1.0), ("two-photon", 2.0)):
                for where, energy in (("k=0", float(row[0])), ("k=kmax", float(row[-1]))):
                    rows.append({
                        "transition": f"DeltaE_{n + 1}{m + 1}",
                        "order": order,
                        "edge": where,
                        "transition_energy_eV": energy,
                        "wavelength_nm": factor * validated.HC_EV_NM / energy,
                        "origin": "physical joint-density edge" if where == "k=0"
                                  else "k-truncation edge (artifact)",
                    })
    del k
    return rows


def nearest_band_edge(edges: Sequence[Mapping[str, Any]], wavelength_nm: float) -> dict[str, object]:
    best = min(edges, key=lambda row: abs(float(row["wavelength_nm"]) - float(wavelength_nm)))
    return {**best, "distance_nm": abs(float(best["wavelength_nm"]) - float(wavelength_nm))}


def feature_traceback(instrumented: InstrumentedSpectrum,
                      specs: Sequence[Mapping[str, Any]],
                      matched: Mapping[str, Mapping[str, float]]) -> list[dict[str, object]]:
    """24N.1 - trace each paper feature back through Equation 2.

    The trace is evaluated at the *paper* wavelength: for P1/P3/Z1/Z2 the model
    has no corresponding feature, so the paper wavelength is the only defined
    place to ask what the model is doing there.
    """
    if instrumented.k_integrand is None:
        raise ValueError("feature_traceback needs an instrumented spectrum with keep_k_integrand=True")
    x = instrumented.wavelength_nm
    edges = band_edges_of_transitions(instrumented)
    rows: list[dict[str, object]] = []
    for spec in specs:
        name = str(spec["name"])
        paper_nm = float(spec["wavelength_nm"])
        index = int(np.argmin(np.abs(x - paper_nm)))
        values = instrumented.terms[:, index]
        order = np.argsort(np.abs(values))[::-1]
        top = PATHWAYS[int(order[0])]
        total = instrumented.chi2[index]
        coherent = float(abs(total))
        incoherent = float(np.sum(np.abs(values)))
        ratio = coherent / incoherent if incoherent > 0 else float("nan")
        contribution = np.abs(instrumented.k_integrand[top.index, index, :])
        region = _k_region(contribution, instrumented.k_per_nm)
        kpeak = int(np.argmax(contribution))
        hw = validated.HC_EV_NM / x[index]
        gamma = 0.0  # denominators reported as the real detuning at the dominant k
        n, m, ell = top.n - 1, top.m - 1, top.ell - 1
        two_photon = float(instrumented.transition_eV[n, m, kpeak] - 2.0 * hw + gamma)
        if top.side == "electron_side":
            one_photon = float(instrumented.transition_eV[ell, m, kpeak] - hw)
        else:
            one_photon = float(instrumented.transition_eV[n, ell, kpeak] - hw)
        smallest = min(abs(one_photon), abs(two_photon))
        resonant = smallest <= 0.05
        cancelling = ratio < 0.35
        if resonant and cancelling:
            mechanism = "resonance-driven inside a strongly cancelling sum"
        elif resonant:
            mechanism = "resonance-driven"
        elif cancelling:
            mechanism = "off-resonant tail of a strongly cancelling sum"
        else:
            mechanism = "off-resonant tail"
        edge = float(instrumented.k_per_nm[kpeak]) >= 0.95 * float(np.max(instrumented.k_per_nm))
        confidence = "high" if incoherent > 0 and abs(values[order[0]]) / incoherent > 0.2 else "medium"
        # The peaks of an integrated spectrum sit at resonance *band edges*, not at the
        # largest single pathway, so identify the nearest edge separately.
        edge = nearest_band_edge(edges, float(matched[name]["wavelength_nm"]))
        rows.append({
            "Feature": name,
            "Paper_wavelength_nm": paper_nm,
            "Model_wavelength_nm": float(matched[name]["wavelength_nm"]),
            "Model_feature_is_window_edge": bool(matched[name].get("at_window_edge", 0.0)),
            "Dominant_pathway": top.label,
            "Dominant_pathway_side": top.side,
            "Dominant_pathway_fraction_of_incoherent_sum": float(abs(values[order[0]]) / incoherent) if incoherent else float("nan"),
            "Second_pathway": PATHWAYS[int(order[1])].label,
            "Dominant_pathway_k_peak_per_nm": region["k_peak_per_nm"],
            "Dominant_pathway_k50_range_per_nm": f"{region['k50_lo_per_nm']:.4g}-{region['k50_hi_per_nm']:.4g}",
            "Dominant_pathway_k90_range_per_nm": f"{region['k90_lo_per_nm']:.4g}-{region['k90_hi_per_nm']:.4g}",
            "Dominant_pathway_two_photon_transition": top.two_photon_transition,
            "Dominant_pathway_one_photon_transition": top.one_photon_transition,
            "Nearest_band_edge_transition": str(edge["transition"]),
            "Nearest_band_edge_order": str(edge["order"]),
            "Nearest_band_edge_side": str(edge["edge"]),
            "Nearest_band_edge_wavelength_nm": float(edge["wavelength_nm"]),
            "Nearest_band_edge_distance_nm": float(edge["distance_nm"]),
            "Nearest_band_edge_origin": str(edge["origin"]),
            "One_photon_denominator_eV": one_photon,
            "Two_photon_denominator_eV": two_photon,
            "Dominant_numerator": top.numerator_expression,
            "Dominant_numerator_value_nm": float(np.real(instrumented.numerators[top.index, kpeak])),
            "Coherent_over_incoherent_sum": ratio,
            "Cancellation_amplification_factor": 1.0 / ratio if ratio > 0 else float("inf"),
            "Dominant_k_is_at_grid_edge": edge,
            "Mechanism": mechanism,
            "Confidence": confidence,
        })
    return rows


# ---------------------------------------------------------------------------
# 24N.2 / 24N.3 - one-at-a-time subband energy perturbations
# ---------------------------------------------------------------------------

def perturbed_subbands(subbands: Mapping[str, np.ndarray], state: str, shift_meV: float) -> dict[str, np.ndarray]:
    """Rigidly shift one tracked subband; dispersion curvature is preserved."""
    if state not in STATE_KEYS:
        raise ValueError(f"state must be one of {STATE_KEYS}, got {state!r}")
    out = {key: np.array(value, dtype=float, copy=True) for key, value in subbands.items()}
    out[state] = out[state] + float(shift_meV) * 1e-3
    return out


def energy_sensitivity(
    baseline_subbands: Mapping[str, np.ndarray],
    k_per_nm: np.ndarray,
    wavelength_nm: np.ndarray,
    frozen,
    settings: validated.Chi2Settings,
    paper_on_grid: np.ndarray,
    specs: Sequence[Mapping[str, Any]],
    shifts_meV: Sequence[float],
) -> tuple[list[dict[str, object]], dict[str, np.ndarray]]:
    """24N.2 - perturb each tracked subband alone and re-measure every feature."""
    rows: list[dict[str, object]] = []
    spectra: dict[str, np.ndarray] = {}
    for state in STATE_KEYS:
        for shift in shifts_meV:
            bands = perturbed_subbands(baseline_subbands, state, float(shift))
            spectrum = instrumented_spectrum(
                wavelength_nm, k_per_nm,
                np.vstack([bands["e1"], bands["e2"]]),
                np.vstack([bands["hh1"], bands["hh2"]]),
                frozen.overlap_eh, frozen.z_e_nm, frozen.z_hh_nm,
                broadening_meV=settings.broadening_meV, settings=settings)
            label = f"{state}{float(shift):+g} meV"
            if float(shift) != 0.0:
                spectra[label] = spectrum.chi2
            matched = match_features(wavelength_nm, spectrum.chi2, specs)
            for spec in specs:
                name = str(spec["name"])
                info = matched[name]
                rows.append({
                    "state": state,
                    "shift_meV": float(shift),
                    "Feature": name,
                    "feature_type": str(spec["type"]),
                    "paper_wavelength_nm": float(spec["wavelength_nm"]),
                    "model_wavelength_nm": info["wavelength_nm"],
                    "model_normalized_amplitude": info["normalized_amplitude"],
                    "normalized_amplitude_at_paper_nm": info["amplitude_at_paper_nm"],
                    "local_normalized_RMSE": local_rmse(wavelength_nm, paper_on_grid, spectrum.chi2, _window_for(spec)),
                    "global_normalized_RMSE": signed_spectrum.normalized_rmse(paper_on_grid, spectrum.chi2),
                    "note": DIAGNOSTIC_BANNER,
                })
    return rows, spectra


def energy_derivatives(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    """Least-squares d(lambda)/dE and d(node depth)/dE from the perturbation ladder."""
    out: list[dict[str, object]] = []
    features = sorted({str(row["Feature"]) for row in rows}, key=lambda n: _FEATURE_ORDER.index(n))
    for feature in features:
        for state in STATE_KEYS:
            subset = sorted((row for row in rows if row["Feature"] == feature and row["state"] == state),
                            key=lambda row: float(row["shift_meV"]))
            shifts = np.asarray([float(row["shift_meV"]) for row in subset])
            lam = np.asarray([float(row["model_wavelength_nm"]) for row in subset])
            depth = np.asarray([float(row["normalized_amplitude_at_paper_nm"]) for row in subset])
            base = next(row for row in subset if float(row["shift_meV"]) == 0.0)
            dlam = float(np.polyfit(shifts, lam, 1)[0]) if len(set(shifts)) > 1 else float("nan")
            ddepth = float(np.polyfit(shifts, depth, 1)[0]) if len(set(shifts)) > 1 else float("nan")
            out.append({
                "Feature": feature,
                "state": state,
                "paper_wavelength_nm": float(base["paper_wavelength_nm"]),
                "baseline_model_wavelength_nm": float(base["model_wavelength_nm"]),
                "baseline_error_nm": float(base["model_wavelength_nm"]) - float(base["paper_wavelength_nm"]),
                "dLambda_dE_nm_per_meV": dlam,
                "dNodeDepth_dE_per_meV": ddepth,
                "span_of_model_wavelength_nm": float(np.max(lam) - np.min(lam)),
                "shift_needed_meV_if_linear": (float(base["paper_wavelength_nm"]) - float(base["model_wavelength_nm"])) / dlam
                if dlam not in (0.0,) and np.isfinite(dlam) and abs(dlam) > 1e-9 else float("nan"),
                "note": DIAGNOSTIC_BANNER,
            })
    return out


_FEATURE_ORDER = ["P1", "Z1", "P2", "P3", "Z2", "P4"]


def shift_direction_statements(derivatives: Sequence[Mapping[str, Any]],
                               reach: Mapping[str, Mapping[str, Any]]) -> list[dict[str, object]]:
    """24N.3 - numerically grounded left/right shift interpretation per feature."""
    out: list[dict[str, object]] = []
    for feature in _FEATURE_ORDER:
        subset = [row for row in derivatives if row["Feature"] == feature]
        if not subset:
            continue
        strongest = max(subset, key=lambda row: abs(float(row["dLambda_dE_nm_per_meV"]))
                        if np.isfinite(float(row["dLambda_dE_nm_per_meV"])) else -1.0)
        error = float(strongest["baseline_error_nm"])
        slope = float(strongest["dLambda_dE_nm_per_meV"])
        need = float(strongest["shift_needed_meV_if_linear"])
        side = "shorter" if error < 0 else "longer"
        if not np.isfinite(slope) or abs(slope) < 1e-6:
            statement = (f"{feature} is insensitive to every single-state energy shift "
                         f"(max |dLambda/dE| = {abs(slope):.3g} nm/meV); its position is not set by "
                         f"the four tracked subband energies alone.")
            verdict = "NOT_ENERGY_CONTROLLED"
        else:
            direction = "decreasing" if (error > 0) == (slope > 0) else "increasing"
            statement = (f"{feature} is most sensitive to {strongest['state']} "
                         f"(dLambda/dE = {slope:+.3g} nm/meV). The model feature sits at "
                         f"{float(strongest['baseline_model_wavelength_nm']):.0f} nm, "
                         f"{abs(error):.0f} nm to {side} wavelength than the paper's "
                         f"{float(strongest['paper_wavelength_nm']):.0f} nm; {direction} "
                         f"{strongest['state']} moves it toward the paper, and closing the gap "
                         f"linearly would need {need:+.0f} meV.")
            verdict = "ENERGY_CONTROLLED" if abs(need) <= 30.0 else "ENERGY_CONTROLLED_BUT_OUT_OF_RANGE"
        info = reach.get(feature, {})
        out.append({
            "Feature": feature,
            "most_sensitive_state": strongest["state"],
            "dLambda_dE_nm_per_meV": slope,
            "baseline_error_nm": error,
            "shift_needed_meV_if_linear": need,
            "verdict": verdict,
            "reachable_within_model_resonance_band": info.get("reachable", ""),
            "statement": statement,
        })
    return out


# ---------------------------------------------------------------------------
# 24N.4 / 24N.5 - pathway numerator amplitude and cancellation sensitivity
# ---------------------------------------------------------------------------

def dominant_pathways(instrumented: InstrumentedSpectrum, wavelength_nm: float, count: int) -> list[str]:
    index = int(np.argmin(np.abs(instrumented.wavelength_nm - float(wavelength_nm))))
    order = np.argsort(np.abs(instrumented.terms[:, index]))[::-1]
    return [PATHWAYS[int(i)].label for i in order[:count]]


def amplitude_sensitivity(
    base: InstrumentedSpectrum,
    build,
    labels: Sequence[str],
    scales: Sequence[float],
    specs: Sequence[Mapping[str, Any]],
    paper_on_grid: np.ndarray,
) -> list[dict[str, object]]:
    """24N.4/24N.5 - scale one pathway numerator at a time, denominators fixed."""
    wavelength = base.wavelength_nm
    baseline_matched = match_features(wavelength, base.chi2, specs)
    rows: list[dict[str, object]] = []
    for label in labels:
        for scale in scales:
            spectrum = base if float(scale) == 1.0 else build({label: float(scale)})
            matched = match_features(wavelength, spectrum.chi2, specs)
            for spec in specs:
                name = str(spec["name"])
                info, ref = matched[name], baseline_matched[name]
                rows.append({
                    "pathway": label,
                    "amplitude_scale": float(scale),
                    "Feature": name,
                    "feature_type": str(spec["type"]),
                    "paper_wavelength_nm": float(spec["wavelength_nm"]),
                    "model_wavelength_nm": info["wavelength_nm"],
                    "peak_shift_nm": info["wavelength_nm"] - ref["wavelength_nm"],
                    "model_normalized_amplitude": info["normalized_amplitude"],
                    "normalized_amplitude_change": info["normalized_amplitude"] - ref["normalized_amplitude"],
                    "normalized_amplitude_at_paper_nm": info["amplitude_at_paper_nm"],
                    "node_depth_change_at_paper_nm": info["amplitude_at_paper_nm"] - ref["amplitude_at_paper_nm"],
                    "local_normalized_RMSE": local_rmse(wavelength, paper_on_grid, spectrum.chi2, _window_for(spec)),
                    "note": DIAGNOSTIC_BANNER,
                })
    return rows


def node_cancellation_rows(instrumented: InstrumentedSpectrum,
                           specs: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    """24N.5 - opposing complex contributions inside each paper zero window."""
    rows: list[dict[str, object]] = []
    x = instrumented.wavelength_nm
    for spec in specs:
        if str(spec["type"]) != "minimum":
            continue
        paper_nm = float(spec["wavelength_nm"])
        index = int(np.argmin(np.abs(x - paper_nm)))
        values = instrumented.terms[:, index]
        electron = complex(np.sum([v for v, p in zip(values, PATHWAYS) if p.side == "electron_side"]))
        hole = complex(np.sum([v for v, p in zip(values, PATHWAYS) if p.side != "electron_side"]))
        real = np.real(values)
        positive = [(PATHWAYS[i].label, float(real[i])) for i in np.argsort(real)[::-1][:3]]
        negative = [(PATHWAYS[i].label, float(real[i])) for i in np.argsort(real)[:3]]
        rows.append({
            "Feature": str(spec["name"]),
            "paper_wavelength_nm": paper_nm,
            "chi_e_real": float(electron.real), "chi_e_imag": float(electron.imag),
            "chi_e_abs": float(abs(electron)),
            "chi_hh_signed_real": float(hole.real), "chi_hh_signed_imag": float(hole.imag),
            "chi_hh_signed_abs": float(abs(hole)),
            "total_abs": float(abs(instrumented.chi2[index])),
            "phase_difference_deg": signed_spectrum.phase_difference_deg(electron, hole),
            "cancellation_ratio_e_vs_hh": signed_spectrum.cancellation_metric(electron, hole),
            "coherent_over_incoherent_16_terms": float(abs(np.sum(values)) / np.sum(np.abs(values))),
            "dominant_positive_pathways": "; ".join(f"{n}={v:.4g}" for n, v in positive),
            "dominant_negative_pathways": "; ".join(f"{n}={v:.4g}" for n, v in negative),
        })
    return rows


# ---------------------------------------------------------------------------
# 24N.6 - optional complex phase sensitivity
# ---------------------------------------------------------------------------

def numerator_phase_content(instrumented: InstrumentedSpectrum) -> dict[str, object]:
    """Report whether pathway numerators carry a free phase in this representation."""
    imaginary = float(np.max(np.abs(np.imag(instrumented.numerators))))
    real = float(np.max(np.abs(np.real(instrumented.numerators))))
    separable = imaginary > 1e-12 * max(real, 1e-300)
    return {
        "max_abs_imaginary_numerator": imaginary,
        "max_abs_real_numerator": real,
        "numerator_phase_is_a_free_parameter": separable,
        "interpretation": (
            "Overlaps and z matrix elements are real, so every pathway numerator phase is "
            "pinned to 0 or pi by construction. The k-integrated pathway terms are still "
            "genuinely complex through the iGamma denominators, so a rotation of a term is a "
            "well-defined robustness probe, not a free physical parameter."),
    }


def phase_sensitivity(
    base: InstrumentedSpectrum,
    build,
    labels: Sequence[str],
    degrees: Sequence[float],
    specs: Sequence[Mapping[str, Any]],
) -> list[dict[str, object]]:
    """24N.6 - COMPLEX PHASE SENSITIVITY DIAGNOSTIC (robustness probe only)."""
    wavelength = base.wavelength_nm
    baseline_matched = match_features(wavelength, base.chi2, specs)
    rows: list[dict[str, object]] = []
    for label in labels:
        for angle in degrees:
            spectrum = base if float(angle) == 0.0 else build({label: float(np.radians(angle))})
            matched = match_features(wavelength, spectrum.chi2, specs)
            for spec in specs:
                if str(spec["type"]) != "minimum":
                    continue
                name = str(spec["name"])
                info, ref = matched[name], baseline_matched[name]
                rows.append({
                    "pathway": label,
                    "phase_deg": float(angle),
                    "Feature": name,
                    "paper_wavelength_nm": float(spec["wavelength_nm"]),
                    "model_wavelength_nm": info["wavelength_nm"],
                    "node_wavelength_shift_nm": info["wavelength_nm"] - ref["wavelength_nm"],
                    "normalized_amplitude_at_paper_nm": info["amplitude_at_paper_nm"],
                    "node_depth_change": info["amplitude_at_paper_nm"] - ref["amplitude_at_paper_nm"],
                    "note": "COMPLEX PHASE SENSITIVITY DIAGNOSTIC - " + DIAGNOSTIC_BANNER,
                })
    return rows


# ---------------------------------------------------------------------------
# 24N.7 - dominant k-region per feature
# ---------------------------------------------------------------------------

def k_region_sensitivity(instrumented: InstrumentedSpectrum,
                         specs: Sequence[Mapping[str, Any]],
                         fraction_of_bz: float, kmax_per_nm: float) -> list[dict[str, object]]:
    if instrumented.k_integrand is None:
        raise ValueError("k_region_sensitivity needs keep_k_integrand=True")
    x = instrumented.wavelength_nm
    k = instrumented.k_per_nm
    rows: list[dict[str, object]] = []
    for spec in specs:
        paper_nm = float(spec["wavelength_nm"])
        index = int(np.argmin(np.abs(x - paper_nm)))
        total = np.abs(instrumented.k_integrand[:, index, :].sum(axis=0))
        region = _k_region(total, k)
        scale = kmax_per_nm if kmax_per_nm > 0 else float("nan")
        rows.append({
            "Feature": str(spec["name"]),
            "paper_wavelength_nm": paper_nm,
            "k_peak_contribution_per_nm": region["k_peak_per_nm"],
            "k_peak_as_fraction_of_kmax": region["k_peak_per_nm"] / scale,
            "k50_lo_per_nm": region["k50_lo_per_nm"], "k50_hi_per_nm": region["k50_hi_per_nm"],
            "k90_lo_per_nm": region["k90_lo_per_nm"], "k90_hi_per_nm": region["k90_hi_per_nm"],
            "k50_fraction_of_bz_hi": region["k50_hi_per_nm"] / scale * float(fraction_of_bz),
            "k90_fraction_of_bz_hi": region["k90_hi_per_nm"] / scale * float(fraction_of_bz),
            "diagnosis_uses_finite_k": bool(region["k_peak_per_nm"] > 0.05 * scale),
            # A dominant contribution pinned to the last k sample means the integrand is
            # still rising where the grid stops, i.e. the feature is cut off rather than
            # converged. Interior maxima are the converged case.
            "k_peak_at_grid_edge": bool(region["k_peak_per_nm"] >= 0.95 * scale),
            "integration_status": ("TRUNCATED - integrand peaks at the k cutoff"
                                   if region["k_peak_per_nm"] >= 0.95 * scale
                                   else "CONVERGED - integrand peaks inside the grid"),
        })
    return rows


# ---------------------------------------------------------------------------
# resonance reachability - can any tracked-energy perturbation reach a feature?
# ---------------------------------------------------------------------------

def band_edges(raw_case: Path) -> dict[str, float]:
    """Read barrier and well band edges from the copied Professional output.

    The edges share the eigenvalue energy reference, so they bound where a
    subband stops being confined.
    """
    matches = sorted(raw_case.rglob("bandedges.dat"))
    if not matches:
        raise FileNotFoundError(f"bandedges.dat not found under {raw_case}")
    table = np.loadtxt(matches[0], skiprows=1)
    x, gamma, hh = table[:, 0], table[:, 1], table[:, 2]
    barrier = int(np.argmax(gamma))
    well = int(np.argmin(gamma))
    return {
        "source": str(matches[0]),
        "barrier_conduction_edge_eV": float(gamma[barrier]),
        "barrier_valence_edge_eV": float(hh[barrier]),
        "barrier_gap_eV": float(gamma[barrier] - hh[barrier]),
        "barrier_position_nm": float(x[barrier]),
        "well_conduction_edge_eV": float(gamma[well]),
        "well_valence_edge_eV": float(hh[well]),
        "well_gap_eV": float(gamma[well] - hh[well]),
        "well_position_nm": float(x[well]),
    }


def _parabolic_coefficient(k: np.ndarray, band: np.ndarray) -> float:
    return float(np.polyfit(np.asarray(k) ** 2, np.asarray(band) - float(band[0]), 1)[0])


def confinement_limited_transition_energy(instrumented: InstrumentedSpectrum,
                                          barrier_conduction_edge_eV: float) -> dict[str, object]:
    """Largest Ee-Ehh reachable while the electron subband is still confined.

    Each electron subband is fitted as ``E(k) = E(0) + a k^2`` on the computed
    range and extrapolated to the barrier conduction-band edge. Past that k the
    state is no longer a bound subband, so the parabolic continuation is not a
    physical bound-state transition and cannot host a bound-state resonance.
    This bound is what separates "the k grid was too short" from "no pair of
    bound subbands in this structure can reach that energy at all".
    """
    k = instrumented.k_per_nm
    electron = instrumented.electron_energies_eV
    transition = instrumented.transition_eV
    best = -np.inf
    detail: dict[str, object] = {"max_bound_transition_energy_eV": float("nan")}
    for n in range(2):
        a_e = _parabolic_coefficient(k, electron[n])
        headroom = float(barrier_conduction_edge_eV) - float(electron[n][0])
        if a_e <= 0 or headroom <= 0:
            continue
        k_unbind = float(np.sqrt(headroom / a_e))
        for m in range(2):
            a = _parabolic_coefficient(k, transition[n, m])
            if a <= 0:
                continue
            value = float(transition[n, m][0] + a * k_unbind ** 2)
            if value > best:
                best = value
                detail = {
                    "limiting_transition": f"DeltaE_{n + 1}{m + 1}",
                    "electron_unbinding_k_per_nm": k_unbind,
                    "electron_unbinding_k_over_computed_kmax": k_unbind / float(np.max(k)),
                    "max_bound_transition_energy_eV": value,
                }
    return detail


def extrapolation_validation(short_k: np.ndarray, short_bands: Mapping[str, np.ndarray],
                             long_k: np.ndarray, long_bands: Mapping[str, np.ndarray],
                             barrier_conduction_edge_eV: float) -> list[dict[str, object]]:
    """Check the parabolic extrapolation against a genuinely longer k range.

    ``confinement_limited_transition_energy`` extrapolates a parabola fitted on
    the production grid out to the barrier edge. The copied 0.125 pi/a case
    reaches 25% further in k than the production 0.10 case, so it can test that
    extrapolation directly instead of asking the reader to trust it.
    """
    rows: list[dict[str, object]] = []
    target = float(np.max(long_k))
    for state in STATE_KEYS:
        short = np.asarray(short_bands[state], dtype=float)
        long = np.asarray(long_bands[state], dtype=float)
        a_short = _parabolic_coefficient(short_k, short)
        a_long = _parabolic_coefficient(long_k, long)
        predicted = float(short[0] + a_short * target ** 2)
        actual = float(long[-1])
        headroom = float(barrier_conduction_edge_eV) - float(short[0])
        rows.append({
            "state": state,
            "parabolic_coefficient_short_eV_nm2": a_short,
            "parabolic_coefficient_long_eV_nm2": a_long,
            "curvature_change": "flattening (non-parabolic)" if a_long < a_short else "steepening",
            "extrapolation_reach": target / float(np.max(short_k)),
            "predicted_energy_at_long_kmax_eV": predicted,
            "actual_energy_at_long_kmax_eV": actual,
            "error_meV": 1000.0 * (predicted - actual),
            "unbinding_k_from_short_fit_per_nm": float(np.sqrt(headroom / a_short)) if a_short > 0 and headroom > 0 else float("nan"),
            "unbinding_k_from_long_fit_per_nm": float(np.sqrt((barrier_conduction_edge_eV - long[0]) / a_long)) if a_long > 0 and barrier_conduction_edge_eV > long[0] else float("nan"),
            "note": ("a flattening band makes the parabolic extrapolation an OVER-estimate of the "
                     "transition energy at large k, so the reachability conclusion is conservative"),
        })
    return rows


def resonance_reachability(instrumented: InstrumentedSpectrum,
                           specs: Sequence[Mapping[str, Any]],
                           fraction_of_bz: float,
                           edges: Mapping[str, float] | None = None) -> list[dict[str, object]]:
    """Compare each paper feature with the model's accessible resonance bands.

    A one-photon denominator can vanish only where ``hc/lambda`` equals some
    ``DeltaE(k)``; a two-photon denominator only where ``2hc/lambda`` does. The
    tracked dispersions bound ``DeltaE`` over the computed k range, so those
    bounds bound where the model can place any resonant feature at all. The
    k needed to reach a wavelength outside the band is obtained by fitting
    ``DeltaE(k) = DeltaE(0) + a k^2`` to the tracked data and extrapolating,
    and is reported as an explicit extrapolation.
    """
    k = instrumented.k_per_nm
    transition = instrumented.transition_eV
    energies = transition.reshape(-1, len(k))
    names = [f"DeltaE_{n + 1}{m + 1}" for n in range(2) for m in range(2)]
    emin, emax = float(np.min(energies)), float(np.max(energies))
    one_photon_band = (validated.HC_EV_NM / emax, validated.HC_EV_NM / emin)
    two_photon_band = (2.0 * validated.HC_EV_NM / emax, 2.0 * validated.HC_EV_NM / emin)
    kmax = float(np.max(k))
    limit: dict[str, object] = {}
    if edges:
        limit = confinement_limited_transition_energy(
            instrumented, float(edges["barrier_conduction_edge_eV"]))
    curvature = {}
    for name, row in zip(names, energies):
        a = float(np.polyfit(k ** 2, row - row[0], 1)[0])
        curvature[name] = (float(row[0]), a)
    rows: list[dict[str, object]] = []
    for spec in specs:
        lam = float(spec["wavelength_nm"])
        needed_one = validated.HC_EV_NM / lam
        needed_two = 2.0 * validated.HC_EV_NM / lam
        inside_one = one_photon_band[0] <= lam <= one_photon_band[1]
        inside_two = two_photon_band[0] <= lam <= two_photon_band[1]
        best_k = float("inf")
        best_name = ""
        best_order = ""
        for name, (e0, a) in curvature.items():
            for order, needed in (("one-photon", needed_one), ("two-photon", needed_two)):
                if a <= 0:
                    continue
                delta = needed - e0
                if delta < 0:
                    continue
                k_needed = float(np.sqrt(delta / a))
                if k_needed < best_k:
                    best_k, best_name, best_order = k_needed, name, order
        reachable = "yes" if (inside_one or inside_two) else "no"
        bound_limit = float(limit.get("max_bound_transition_energy_eV", float("nan")))
        # A transition energy is only attainable between its k=0 value and the
        # confinement limit: DeltaE(k) rises with k, so a requirement *below* the
        # smallest k=0 transition is as unreachable as one above the limit.
        candidates = [("one-photon", needed_one), ("two-photon", needed_two)]
        attainable = [(order, value) for order, value in candidates
                      if np.isfinite(bound_limit) and emin <= value <= bound_limit]
        needed = min((value for _, value in candidates), key=lambda v: abs(v - emin))
        if attainable:
            needed = attainable[0][1]
        if reachable == "yes":
            bound_reachable = "yes (already inside the computed band)"
        elif not np.isfinite(bound_limit):
            bound_reachable = "unknown (no barrier edge supplied)"
        elif attainable:
            bound_reachable = f"yes via {attainable[0][0]}, but only beyond the computed k cutoff"
        elif min(needed_one, needed_two) > bound_limit:
            bound_reachable = "no - above the largest bound-subband transition in this structure"
        else:
            bound_reachable = "no - the required energy falls outside the bound-subband range at every k"
        rows.append({
            "Feature": str(spec["name"]),
            "paper_wavelength_nm": lam,
            "required_transition_energy_eV_one_photon": needed_one,
            "required_transition_energy_eV_two_photon": needed_two,
            "model_transition_energy_min_eV": emin,
            "model_transition_energy_max_eV": emax,
            "one_photon_band_nm": f"{one_photon_band[0]:.1f}-{one_photon_band[1]:.1f}",
            "two_photon_band_nm": f"{two_photon_band[0]:.1f}-{two_photon_band[1]:.1f}",
            "inside_one_photon_band": inside_one,
            "inside_two_photon_band": inside_two,
            "reachable": reachable,
            "closest_transition": best_name,
            "closest_resonance_order": best_order,
            "extrapolated_k_needed_per_nm": best_k if np.isfinite(best_k) else float("nan"),
            "extrapolated_k_needed_over_computed_kmax": best_k / kmax if np.isfinite(best_k) and kmax > 0 else float("nan"),
            "extrapolated_fraction_of_bz_needed": best_k / kmax * float(fraction_of_bz) if np.isfinite(best_k) and kmax > 0 else float("nan"),
            "model_transition_energy_min_at_k0_eV": emin,
            "governing_required_energy_eV": needed,
            "max_bound_subband_transition_energy_eV": bound_limit,
            "electron_unbinding_k_per_nm": float(limit.get("electron_unbinding_k_per_nm", float("nan"))),
            "barrier_gap_eV": float(edges["barrier_gap_eV"]) if edges else float("nan"),
            "required_energy_above_barrier_gap_eV": (needed - float(edges["barrier_gap_eV"]))
            if edges and np.isfinite(needed) else float("nan"),
            "reachable_with_bound_states_at_any_k": bound_reachable,
            "extrapolation_warning": "parabolic fit extrapolated beyond the computed k range; indicative only",
        })
    return rows


# ---------------------------------------------------------------------------
# cutoff-artifact detection - does a model peak track the k cutoff?
# ---------------------------------------------------------------------------

def cutoff_artifact_test(wavelength_nm: np.ndarray,
                         kmax_spectra: Mapping[str, np.ndarray],
                         kmax_fractions: Mapping[str, float],
                         transition_max_eV: Mapping[str, float],
                         *, prominence: float = 0.04,
                         distance_nm: float = 70.0,
                         stable_tolerance_nm: float = 25.0) -> list[dict[str, object]]:
    """Separate physical resonances from k-truncation artifacts.

    A physical resonance sits at a wavelength set by a transition energy and
    does not move when the integration cutoff changes. An artifact created by
    stopping the k sum sits at the resonance of the *largest included* k, so it
    marches with the cutoff. Comparing the observed motion with
    ``hc/DeltaE(kmax)`` and ``2hc/DeltaE(kmax)`` decides which is which.
    """
    x = np.asarray(wavelength_nm, dtype=float)
    order = sorted(kmax_spectra, key=lambda name: float(kmax_fractions[name]))
    peaks = {name: [float(x[i]) for i in signed_spectrum.peak_indices(
        x, kmax_spectra[name], prominence_fraction=prominence, minimum_distance_nm=distance_nm)]
        for name in order}
    rows: list[dict[str, object]] = []
    reference = order[-1]
    for candidate in peaks[reference]:
        tracked: dict[str, float] = {}
        for name in order:
            if not peaks[name]:
                continue
            nearest = min(peaks[name], key=lambda value: abs(value - candidate))
            if abs(nearest - candidate) <= 260.0:
                tracked[name] = nearest
        if len(tracked) < 2:
            continue
        values = np.asarray(list(tracked.values()))
        spread = float(np.max(values) - np.min(values))
        fractions = np.asarray([float(kmax_fractions[name]) for name in tracked])
        slope = float(np.polyfit(fractions, values, 1)[0]) if len(set(fractions.tolist())) > 1 else float("nan")
        edges = {name: float(transition_max_eV[name]) for name in tracked}
        predicted_one = {name: validated.HC_EV_NM / value for name, value in edges.items()}
        predicted_two = {name: 2.0 * validated.HC_EV_NM / value for name, value in edges.items()}
        err_one = float(np.mean([abs(tracked[name] - predicted_one[name]) for name in tracked]))
        err_two = float(np.mean([abs(tracked[name] - predicted_two[name]) for name in tracked]))
        artifact = spread > stable_tolerance_nm
        matches = "one-photon at kmax" if err_one < err_two else "two-photon at kmax"
        rows.append({
            "peak_wavelength_at_largest_kmax_nm": candidate,
            "tracked_wavelengths_nm": "; ".join(f"{name}={tracked[name]:.0f}" for name in order if name in tracked),
            "spread_across_kmax_nm": spread,
            "dLambda_dFractionOfBZ_nm": slope,
            "classification": "TRACKS_CUTOFF (truncation artifact)" if artifact else "STABLE (physical resonance)",
            "best_match_to_cutoff_resonance": matches if artifact else "n/a",
            "mean_abs_error_vs_one_photon_at_kmax_nm": err_one,
            "mean_abs_error_vs_two_photon_at_kmax_nm": err_two,
        })
    return sorted(rows, key=lambda row: float(row["peak_wavelength_at_largest_kmax_nm"]))


# ---------------------------------------------------------------------------
# 24N.8 / 24N.9 - assembled causal diagnosis
# ---------------------------------------------------------------------------

def causal_diagnosis(traceback: Sequence[Mapping[str, Any]],
                     derivatives: Sequence[Mapping[str, Any]],
                     amplitude: Sequence[Mapping[str, Any]],
                     kregion: Sequence[Mapping[str, Any]],
                     reach: Sequence[Mapping[str, Any]],
                     phase: Sequence[Mapping[str, Any]]) -> list[dict[str, object]]:
    trace = {str(row["Feature"]): row for row in traceback}
    kmap = {str(row["Feature"]): row for row in kregion}
    reachmap = {str(row["Feature"]): row for row in reach}
    rows: list[dict[str, object]] = []
    for feature in _FEATURE_ORDER:
        if feature not in trace:
            continue
        t, kr, rc = trace[feature], kmap[feature], reachmap[feature]
        derived = [row for row in derivatives if row["Feature"] == feature]
        best_energy = max(derived, key=lambda row: abs(float(row["dLambda_dE_nm_per_meV"]))
                          if np.isfinite(float(row["dLambda_dE_nm_per_meV"])) else -1.0)
        amp = [row for row in amplitude if row["Feature"] == feature]
        best_amp = max(amp, key=lambda row: abs(float(row["node_depth_change_at_paper_nm"])), default=None)
        phase_rows = [row for row in phase if row["Feature"] == feature]
        phase_span = max((abs(float(row["node_depth_change"])) for row in phase_rows), default=float("nan"))
        energy_span = float(best_energy["span_of_model_wavelength_nm"])
        slope = abs(float(best_energy["dLambda_dE_nm_per_meV"]))
        amp_span = abs(float(best_amp["node_depth_change_at_paper_nm"])) if best_amp else float("nan")
        bound = str(rc.get("reachable_with_bound_states_at_any_k", ""))
        if str(rc["reachable"]) == "no" and bound.startswith("no"):
            cause = ("MISSING PHYSICS / MODEL SPACE: the required transition energy exceeds the "
                     "largest transition any pair of bound subbands in this structure can reach, "
                     "even extrapolated to the k where the electron leaves the barrier. No k "
                     "cutoff, energy shift, pathway amplitude, sign, broadening or normalization "
                     "change can create this feature")
            needs_pro = "yes"
            confidence = "high"
        elif str(rc["reachable"]) == "no":
            cause = ("k CUTOFF: the wavelength lies outside every one- and two-photon resonance "
                     "band the four tracked subbands produce over the computed k range, but a "
                     "bound-subband pair does reach it beyond the cutoff")
            if bool(kr["k_peak_at_grid_edge"]):
                cause += "; the integrand is still peaking at the k cutoff, so the sum is truncated"
            needs_pro = "yes"
            confidence = "high"
        elif slope > 0.05:
            cause = ("ENERGY / DENOMINATOR: the feature tracks a tracked subband energy "
                     f"({best_energy['state']} at {float(best_energy['dLambda_dE_nm_per_meV']):+.2f} nm/meV)")
            needs_pro = "maybe"
            confidence = "high"
        elif np.isfinite(amp_span) and amp_span > 0.02:
            cause = "NUMERATOR / MATRIX ELEMENT: position is fixed but amplitude responds to pathway strength"
            needs_pro = "yes"
            confidence = "medium"
        else:
            cause = "NEITHER: no single-parameter perturbation in range materially moves this feature"
            needs_pro = "yes"
            confidence = "medium"
        rows.append({
            "Feature": feature,
            "Paper_lambda_nm": float(t["Paper_wavelength_nm"]),
            "Model_lambda_nm": float(t["Model_wavelength_nm"]),
            "Delta_lambda_nm": float(t["Model_wavelength_nm"]) - float(t["Paper_wavelength_nm"]),
            "Dominant_pathway": str(t["Dominant_pathway"]),
            "Dominant_k": float(kr["k_peak_contribution_per_nm"]),
            "Controlling_transition": (f"{t['Nearest_band_edge_transition']} "
                                      f"{t['Nearest_band_edge_order']} {t['Nearest_band_edge_side']} edge"
                                      if float(t["Nearest_band_edge_distance_nm"]) <= 30.0
                                      else "none within 30 nm (feature is not at a resonance band edge)"),
            "Controlling_band_edge_distance_nm": float(t["Nearest_band_edge_distance_nm"]),
            "Most_sensitive_energy": str(best_energy["state"]),
            "dLambda_dE": float(best_energy["dLambda_dE_nm_per_meV"]),
            "Most_sensitive_pathway_amplitude": str(best_amp["pathway"]) if best_amp else "",
            "Cancellation_or_resonance": str(t["Mechanism"]),
            "Likely_root_cause": cause,
            "Confidence": confidence,
            "Needs_new_Pro_data": needs_pro,
            "energy_span_nm_over_pm10meV": energy_span,
            "amplitude_node_depth_span_over_pm10pct": amp_span,
            "phase_node_depth_span": phase_span,
            "Model_feature_is_window_edge": bool(t.get("Model_feature_is_window_edge", False)),
            "reachable_within_model_resonance_band": str(rc["reachable"]),
            "reachable_with_bound_states_at_any_k": bound,
            "integration_status": str(kr["integration_status"]),
            "extrapolated_fraction_of_bz_needed": float(rc["extrapolated_fraction_of_bz_needed"]),
        })
    return rows


def causal_statements(diagnosis: Sequence[Mapping[str, Any]],
                      traceback: Sequence[Mapping[str, Any]],
                      node_rows: Sequence[Mapping[str, Any]],
                      kregion: Sequence[Mapping[str, Any]]) -> str:
    """24N.8 - the required per-feature mechanistic statement block."""
    trace = {str(row["Feature"]): row for row in traceback}
    nodes = {str(row["Feature"]): row for row in node_rows}
    kmap = {str(row["Feature"]): row for row in kregion}
    lines: list[str] = []
    for row in diagnosis:
        feature = str(row["Feature"])
        t = trace[feature]
        lines.append(f"{feature} (paper {float(row['Paper_lambda_nm']):.0f} nm):")
        if bool(row.get("Model_feature_is_window_edge", False)):
            lines.append("    NOTE: the model has no extremum in this window; the quoted model "
                         "wavelength is the window edge, not a feature")
        lines.append(f"    dominant pathway = {row['Dominant_pathway']} ({t['Dominant_pathway_side']})")
        kr = kmap[feature]
        lines.append(f"    dominant k = {float(kr['k_peak_contribution_per_nm']):.4g} /nm "
                     f"({float(kr['k_peak_as_fraction_of_kmax']):.2f} of kmax; 50% band "
                     f"{float(kr['k50_lo_per_nm']):.4g}-{float(kr['k50_hi_per_nm']):.4g} /nm; "
                     f"{kr['integration_status']})")
        lines.append(f"    controlling transition = {row['Controlling_transition']} "
                     f"(nearest edge {float(t['Nearest_band_edge_wavelength_nm']):.0f} nm, "
                     f"{float(t['Nearest_band_edge_distance_nm']):.0f} nm away; "
                     f"{t['Nearest_band_edge_origin']})")
        lines.append(f"    most sensitive state energy = {row['Most_sensitive_energy']} "
                     f"(dLambda/dE = {float(row['dLambda_dE']):+.3g} nm/meV)")
        lines.append(f"    most sensitive numerator/pathway = {row['Most_sensitive_pathway_amplitude'] or 'none in +/-10%'}")
        lines.append(f"    mechanism = {row['Cancellation_or_resonance']}")
        if feature in nodes:
            node = nodes[feature]
            lines.append(f"    energy-sensitive? {'YES' if float(row['energy_span_nm_over_pm10meV']) > 15.0 else 'NO'}")
            lines.append(f"    amplitude-sensitive? {'YES' if float(row['amplitude_node_depth_span_over_pm10pct']) > 0.02 else 'NO'}")
            lines.append(f"    phase-sensitive? {'YES' if float(row['phase_node_depth_span']) > 0.02 else 'NO'}"
                         " (robustness probe; numerator phase is not a free parameter)")
            lines.append(f"    electron/heavy-hole cancellation ratio = {float(node['cancellation_ratio_e_vs_hh']):.4g}, "
                         f"phase difference {float(node['phase_difference_deg']):+.1f} deg")
        lines.append(f"    likely cause of wavelength mismatch = {row['Likely_root_cause']}")
        lines.append(f"    confidence = {row['Confidence']}")
        lines.append("")
    return "\n".join(lines)
