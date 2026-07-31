"""Stage 8 — the formal paper-comparison report for Demo 11.

Every comparison is classified, and the classification is the point. A number
that merely *looks* close is not a reproduction if it came from a fitted scale
factor, and a number that disagrees is not a failure if the paper never
published what would be needed to compute it.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

import chi2 as chi2mod
import plots as plotting
import sweeps
from demo_workflow import write_json_atomically, write_text_atomically

#: Stages that vary the structural asymmetry: the original coarse sweep and the
#: refined one that resolves the discontinuity it exposed. Both are plotted and
#: compared; the coarse sweep is never discarded.
ASYMMETRY_STAGES: tuple[str, ...] = ("stage3", "stage3_refined")

DIRECT = "directly_reproduced"
QUALITATIVE = "qualitatively_reproduced"
CALIBRATED = "calibrated_reproduction"
NOT_REPRODUCIBLE = "not_reproducible_from_available_information"
OUT_OF_SCOPE = "outside_nextnano_scope"
NEEDS_AUTHORS = "requires_author_data_or_code"

# ---------------------------------------------------------------------------
# reproduction status
# ---------------------------------------------------------------------------
# `classification` above says what KIND of comparison a quantity is. This says
# how far the work has actually got with it, which is a different question and
# was previously collapsed into a bare PASS. A criterion can be inside its
# tolerance and still not be reproduced -- the asymmetry optimum is exactly that
# case: the number agrees, but the metric that produced it conflates intrinsic
# magnitude with detuning, and the underlying sweep has an unexplained
# discontinuity next to the claimed optimum.

MECHANICAL = "mechanically_completed"
CONVERGED = "numerically_converged"
REPRODUCED = "reproduced"
PROVISIONAL = "provisionally_consistent"
UNRESOLVED = "unresolved"
FAILED = "failed"

STATUS_ORDER: tuple[str, ...] = (
    REPRODUCED,
    CONVERGED,
    PROVISIONAL,
    MECHANICAL,
    UNRESOLVED,
    FAILED,
)

STATUS_MEANING: Mapping[str, str] = {
    MECHANICAL: "the calculation ran to completion; nothing is claimed about the number",
    CONVERGED: "the number is stable against the numerical parameters that were swept",
    REPRODUCED: "computed here, agrees with the paper within a stated tolerance, and "
    "the metric behind it is the one the paper's claim is about",
    PROVISIONAL: "consistent with the paper, but resting on something not yet settled; "
    "not a reproduction",
    UNRESOLVED: "the calculation raises a question this run cannot answer",
    FAILED: "the check did not pass",
}


def _observable(result: sweeps.CaseResult | None, name: str) -> float | None:
    if result is None:
        return None
    value = result.observables.get(name)
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _entry(
    name: str,
    paper_value: float | None,
    ours: float | None,
    classification: str,
    units: str,
    note: str,
    *,
    tolerance: float | None = None,
    provisional: bool = False,
    provisional_reason: str = "",
) -> dict[str, Any]:
    difference = None
    relative = None
    within = None
    at_boundary = False
    if paper_value is not None and ours is not None:
        difference = ours - paper_value
        if paper_value != 0:
            relative = difference / abs(paper_value)
        if tolerance is not None:
            within = abs(difference) <= tolerance
            # Sitting exactly on the tolerance is not a result. The corrected
            # asymmetry optimum lands at |diff| = 0.08000000000000007 against a
            # 0.08 tolerance, so the verdict is decided by how 0.42 rounds in
            # binary. Flagged rather than nudged: widening the tolerance to make
            # it pass, or leaving it to report a hard FAIL, would both be
            # claiming a precision the sweep does not have.
            at_boundary = abs(abs(difference) - tolerance) <= 1e-9 * max(
                abs(tolerance), 1.0
            )
    # `classification` is the KIND of comparison this is. `outcome` is whether
    # it was actually evaluated. Without the split, a dry run would report
    # "directly_reproduced" for a quantity nothing has computed yet.
    if classification in (OUT_OF_SCOPE, NEEDS_AUTHORS, NOT_REPRODUCIBLE):
        outcome = "not_attempted"
    elif ours is None:
        outcome = "pending"
    elif within is None:
        outcome = "reported_without_tolerance"
    elif at_boundary:
        outcome = "at_tolerance_boundary"
    else:
        outcome = "within_tolerance" if within else "outside_tolerance"
    # A number inside its tolerance is not automatically a reproduction: it can
    # rest on an unsettled question, in which case it is consistency and has to
    # be labelled that way. `provisional` carries that, and the status table
    # downgrades the entry no matter how good the agreement looks.
    return {
        "quantity": name,
        "paper_value": paper_value,
        "our_value": ours,
        "units": units,
        "tolerance": tolerance,
        "difference": difference,
        "relative_difference": relative,
        "within_tolerance": within,
        "at_tolerance_boundary": at_boundary,
        "classification": classification,
        "outcome": outcome,
        "evaluated": ours is not None,
        "provisional": bool(provisional),
        "provisional_reason": provisional_reason,
        "note": note,
    }


def build(
    *,
    cfg: Mapping[str, Any],
    targets: Mapping[str, Any],
    results: Sequence[sweeps.CaseResult],
    reference: sweeps.CaseResult | None,
    stage5: Mapping[str, Any],
    stage6: Mapping[str, Any],
    parent: Path,
    stage3b: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble every paper-vs-simulation comparison with its classification."""

    published = targets["targets"]
    validation_cfg = cfg["validation"]
    metric_cfg = cfg.get("metric") or {}
    energy_tolerance_eV = (
        float(validation_cfg.get("transition_energy_tolerance_meV", 40.0)) / 1000.0
    )
    entries: list[dict[str, Any]] = []

    # --- structural: these are inputs, so agreement is a bookkeeping check ---
    scientific = cfg["scientific"]
    for key, ours in (
        ("thick_well_nm", float(scientific["thick_well_nm"])),
        ("thin_well_nm", float(scientific["thin_well_nm"])),
        ("tunnel_barrier_nm", float(scientific["tunnel_barrier_nm"])),
        ("period_barrier_nm", float(scientific["period_barrier_nm"])),
        ("aluminium_fraction", float(scientific["aluminum_fraction"])),
    ):
        entries.append(
            _entry(
                key,
                float(published[key]["value"]),
                ours,
                DIRECT,
                "nm" if key.endswith("_nm") else "",
                "Structural input, transcribed from the paper. Agreement here "
                "confirms transcription, not physics.",
                tolerance=1e-6,
            )
        )
    entries.append(
        _entry(
            "asymmetry_s",
            float(published["asymmetry_optimum"]["value"]),
            chi2mod.structural_asymmetry(
                float(scientific["thick_well_nm"]), float(scientific["thin_well_nm"])
            ),
            DIRECT,
            "",
            "s = (d1 - d2)/(d1 + d2), computed from the transcribed thicknesses.",
            tolerance=0.005,
        )
    )

    # --- electronic structure: the first real physics comparison ------------
    entries.append(
        _entry(
            "ground_interband_transition",
            float(published["ground_interband_transition_eV"]["value"]),
            _observable(reference, "transition_e1_hh1_eV"),
            DIRECT,
            "eV",
            "E_e1 - E_hh1 from a one-band Gamma + HH calculation of the designed "
            "layers. No material parameter was adjusted to improve agreement.",
            tolerance=energy_tolerance_eV,
        )
    )
    entries.append(
        _entry(
            "excited_interband_transition",
            float(published["excited_interband_transition_eV"]["value"]),
            _observable(reference, "transition_e2_hh2_eV"),
            DIRECT,
            "eV",
            "E_e2 - E_hh2. This transition sets the ~1520 nm two-photon resonance.",
            tolerance=energy_tolerance_eV,
        )
    )

    # --- spectral positions --------------------------------------------------
    two_photon = None
    if reference is not None:
        predicted = reference.observables.get("predicted_two_photon_resonances_nm") or []
        excited = [
            value
            for value in predicted
            if 1200.0 <= float(value) <= 1900.0
        ]
        two_photon = min(excited) if excited else None
    entries.append(
        _entry(
            "simulated_resonance_wavelength",
            float(published["simulated_resonance_nm"]["value"]),
            two_photon,
            DIRECT,
            "nm",
            "Two-photon resonance of the excited-state transition, 2hc/E. The "
            "paper's companion peak near 760 nm is the one-photon resonance of "
            "the same transition, so the two are one statement, not two.",
            tolerance=60.0,
        )
    )
    peak = (stage6 or {}).get("focused_peak") or {}
    entries.append(
        _entry(
            "focused_scan_peak_wavelength",
            float(published["simulated_resonance_nm"]["value"]),
            float(peak["wavelength_nm"]) if peak.get("wavelength_nm") else None,
            DIRECT,
            "nm",
            "Peak of |chi(2)| computed over 1400-1800 nm from Eq. 2. This is the "
            "end-to-end check that the resonance really lands where the transition "
            "energies say it should.",
            tolerance=60.0,
        )
    )
    entries.append(
        _entry(
            "measured_resonance_wavelength",
            float(published["measured_resonance_nm"]["value"]),
            None,
            OUT_OF_SCOPE,
            "nm",
            "Measured, not simulated. The paper attributes the ~40 nm offset from "
            "its own simulation to a lower transition energy in the grown sample. "
            "Reproducing it would require modelling the as-grown layers, not the "
            "designed ones.",
        )
    )

    # --- asymmetry and barrier trends ---------------------------------------
    # Two metrics, reported separately and never merged. See METRICS.
    stage3 = [r for r in results if r.spec.metadata.get("stage") == "stage3"]
    stage3_refined = [
        r for r in results if r.spec.metadata.get("stage") == "stage3_refined"
    ]
    asymmetry_tolerance = 0.08
    paper_asymmetry = float(published["asymmetry_optimum"]["value"])
    optima: dict[str, Any] = {"asymmetry": {}, "barrier": {}}

    for metric_name, spec in METRICS.items():
        optima["asymmetry"][metric_name] = {
            "coarse": _optimum(stage3, "asymmetry", spec["observable"]),
            "refined": _optimum(stage3_refined, "asymmetry", spec["observable"]),
        }
    asymmetry_primary = optima["asymmetry"][PRIMARY_METRIC]
    # The refined sweep supersedes the coarse one where it exists; it is denser
    # over exactly the range in question. Where it has not been run, the coarse
    # sweep is used and the entry says so.
    primary_source = (
        "refined" if asymmetry_primary["refined"]["value"] is not None else "coarse"
    )
    entries.append(
        _entry(
            "asymmetry_optimum_peak_metric",
            paper_asymmetry,
            asymmetry_primary[primary_source]["value"],
            QUALITATIVE,
            "",
            "PRIMARY metric for the paper's optimum claim: the asymmetry that "
            "maximises the intrinsic peak |chi(2)| over the focused scan, which "
            "does not depend on where each structure's resonance falls. Taken "
            f"from the {primary_source} sweep. This is NOT the same quantity as "
            "asymmetry_optimum_at_reference_wavelength and the two can disagree.",
            tolerance=asymmetry_tolerance,
            provisional=True,
            provisional_reason=(
                "State identity across the sweep is unresolved: chi(2)(s) is "
                "discontinuous and the states are labelled by energy index "
                "through what looks like an avoided crossing. Until the refined "
                "sweep and physical-state tracking settle that, an agreeing "
                "number here is consistency, not reproduction."
            ),
        )
    )
    entries.append(
        _entry(
            "asymmetry_optimum_at_reference_wavelength",
            paper_asymmetry,
            optima["asymmetry"]["chi2_at_reference_wavelength"][primary_source]["value"],
            QUALITATIVE,
            "",
            "SECONDARY, application-specific: the asymmetry that maximises "
            f"|chi(2)| at {metric_cfg.get('reference_wavelength_nm', 1550.0)} nm. "
            "Across this sweep the two-photon resonance moves by about 100 nm "
            "against a "
            f"{metric_cfg.get('broadening_meV', 5.0)} meV linewidth, so this "
            "metric ranks structures partly by detuning from the fixed reference "
            "and must not be read as the intrinsic chi(2) maximum.",
            tolerance=asymmetry_tolerance,
            provisional=True,
            provisional_reason=(
                "Reported for completeness. It answers 'which of these is best at "
                "one wavelength', not 'which is most nonlinear'."
            ),
        )
    )
    zero_case = next(
        (r for r in stage3 if abs(float(r.spec.swept.get("thin_well_nm", -1)) -
                                 float(r.spec.swept.get("thick_well_nm", -2))) < 1e-9),
        None,
    )
    entries.append(
        _entry(
            "chi2_at_symmetric_limit",
            0.0,
            _observable(zero_case, "chi2_peak_magnitude"),
            QUALITATIVE,
            "relative",
            "s = 0 gives two identical wells. A symmetric structure has "
            "identically zero chi(2) by parity; this checks the calculation "
            "reproduces that rather than merely a small number. Scored on the "
            "peak magnitude over the whole focused scan, which is the strictest "
            "of the two metrics -- a single wavelength could sit in a node.",
        )
    )
    stage4 = [r for r in results if r.spec.metadata.get("stage") == "stage4"]
    for metric_name, spec in METRICS.items():
        optima["barrier"][metric_name] = _optimum(
            stage4, "tunnel_barrier_nm", spec["observable"]
        )
    entries.append(
        _entry(
            "barrier_optimum_peak_metric",
            float(published["barrier_optimum_nm"]["value"]),
            optima["barrier"][PRIMARY_METRIC]["value"],
            QUALITATIVE,
            "nm",
            "PRIMARY: the barrier thickness that maximises the intrinsic peak "
            "|chi(2)|. The paper predicts an ideal optimum near 1 nm while the "
            "fabricated structure used 1.8 nm; those are two different statements "
            "and both are reported. Unlike the asymmetry sweep, this optimum comes "
            "out at the same place under both metrics, which is why it is not "
            "marked provisional.",
            tolerance=0.6,
        )
    )
    entries.append(
        _entry(
            "barrier_optimum_at_reference_wavelength",
            float(published["barrier_optimum_nm"]["value"]),
            optima["barrier"]["chi2_at_reference_wavelength"]["value"],
            QUALITATIVE,
            "nm",
            "SECONDARY, application-specific: the barrier that maximises "
            f"|chi(2)| at {metric_cfg.get('reference_wavelength_nm', 1550.0)} nm.",
            tolerance=0.6,
        )
    )
    smoothness = _monotone_break(
        stage3_refined or stage3, "asymmetry", METRICS[PRIMARY_METRIC]["observable"]
    )
    window_convergence = _state_window_convergence(
        results,
        relative_tolerance=float(
            ((cfg.get("analysis") or {}).get("convergence") or {}).get(
                "chi2_state_window_relative_tolerance", 0.05
            )
        ),
    )

    # --- interface abruptness ------------------------------------------------
    stage7 = {
        str(r.spec.label): r
        for r in results
        if r.spec.metadata.get("stage") == "stage7"
    }
    abrupt = _observable(stage7.get("ideal_abrupt"), "chi2_relative_at_reference")
    graded = _observable(stage7.get("graded_1nm"), "chi2_relative_at_reference")
    ratio = (graded / abrupt) if (abrupt and graded and abrupt != 0) else None
    paper_ratio = (
        float(published["chi2_eds_al_profile_pm_per_V"]["value"])
        / float(published["chi2_ideal_abrupt_pm_per_V"]["value"])
    )
    entries.append(
        _entry(
            "graded_to_abrupt_chi2_ratio",
            paper_ratio,
            ratio,
            QUALITATIVE,
            "",
            "Ratio of graded to abrupt chi(2) at the reference wavelength. A "
            "ratio is comparable even in relative mode, because the unknown "
            "absolute scale cancels. The paper's ratio uses its 1200 pm/V EDS-Al "
            "result against its 2340 pm/V ideal result.",
            tolerance=0.25,
        )
    )

    # --- absolute magnitudes -------------------------------------------------
    absolute_mode = ((stage5 or {}).get("modes") or {}).get("absolute") or {}
    calibrated_mode = ((stage5 or {}).get("modes") or {}).get("calibrated") or {}
    entries.append(
        _entry(
            "chi2_ideal_abrupt_at_1550nm",
            float(published["chi2_ideal_abrupt_pm_per_V"]["value"]),
            float(absolute_mode["magnitude_at_reference"])
            if absolute_mode.get("magnitude_at_reference") is not None
            else None,
            NOT_REPRODUCIBLE if not absolute_mode.get("available") else DIRECT,
            "pm/V",
            absolute_mode.get(
                "reason",
                "Absolute prediction from the supplied r_e_hh and N_z.",
            )
            if not absolute_mode.get("available")
            else "Absolute prediction using externally supplied r_e_hh and N_z.",
        )
    )
    if calibrated_mode.get("magnitude_at_reference") is not None:
        entries.append(
            _entry(
                "chi2_ideal_abrupt_at_1550nm_calibrated",
                float(published["chi2_ideal_abrupt_pm_per_V"]["value"]),
                float(calibrated_mode["magnitude_at_reference"]),
                CALIBRATED,
                "pm/V",
                "This agrees BY CONSTRUCTION: one global factor was fitted to this "
                "very number. It is listed to make the circularity explicit, and "
                "carries no evidential weight on its own.",
            )
        )
    for key, note in (
        ("chi2_growth_interrupted_pm_per_V", "growth-interrupted sample"),
        ("chi2_12_and_16_period_pm_per_V", "12- and 16-period samples"),
        ("chi2_80_period_pm_per_V", "80-period sample"),
        ("chi2_4_period_pm_per_V", "4-period sample"),
    ):
        entries.append(
            _entry(
                key,
                float(published[key]["value"]),
                None,
                OUT_OF_SCOPE,
                "pm/V",
                f"Measured value for the {note}. Depends on surface band bending, "
                "standing waves, sample placement, and the Eq. 3 field-overlap "
                "extraction with its free parameter alpha. An electronic-structure "
                "calculation should not be expected to reproduce it, and this demo "
                "does not try.",
            )
        )
    entries.append(
        _entry(
            "r_e_hh_unit_cell_matrix_element",
            None,
            None,
            NEEDS_AUTHORS,
            "nm",
            "The HSE06 unit-cell interband matrix element sets the absolute scale "
            "and no numerical value appears in the paper. Without it, no "
            "independent pm/V figure is possible.",
        )
    )

    # Classifications are counted only among comparisons that were actually
    # evaluated; the rest are reported as pending so a dry run cannot look like
    # a successful reproduction.
    evaluated = [e for e in entries if e["evaluated"]]
    summary = {
        classification: sum(
            1 for e in evaluated if e["classification"] == classification
        )
        for classification in (
            DIRECT, QUALITATIVE, CALIBRATED, NOT_REPRODUCIBLE, OUT_OF_SCOPE, NEEDS_AUTHORS
        )
    }
    summary["evaluated"] = len(evaluated)
    summary["pending"] = sum(1 for e in entries if e["outcome"] == "pending")
    summary["not_attempted"] = sum(1 for e in entries if e["outcome"] == "not_attempted")
    checked = [e for e in entries if e["within_tolerance"] is not None]
    summary["comparisons_with_a_tolerance"] = len(checked)
    summary["within_tolerance"] = sum(1 for e in checked if e["within_tolerance"])

    criteria: list[tuple[str, bool | None, str]] = [
        (
            "structural parameters transcribed correctly",
            _all_within(entries, ("thick_well_nm", "thin_well_nm", "tunnel_barrier_nm",
                                  "period_barrier_nm", "aluminium_fraction", "asymmetry_s")),
            "bookkeeping check against paper_targets.yaml",
        ),
        (
            "ground interband transition within tolerance",
            _within(entries, "ground_interband_transition"),
            f"paper 1.49 eV, tolerance "
            f"{validation_cfg.get('transition_energy_tolerance_meV', 40.0)} meV",
        ),
        (
            "excited interband transition within tolerance",
            _within(entries, "excited_interband_transition"),
            "paper 1.62 eV",
        ),
        (
            "two-photon resonance lands near the published 1520 nm",
            _within(entries, "focused_scan_peak_wavelength"),
            "computed end-to-end from Eq. 2 over 1400-1800 nm",
        ),
        (
            "chi(2) peak-magnitude maximum occurs near s = 0.42 (PROVISIONAL)",
            _within(entries, "asymmetry_optimum_peak_metric"),
            "scored on the intrinsic peak metric, not on the fixed-wavelength "
            "value. PROVISIONAL: state identity across the sweep is unresolved, "
            "so this is consistency rather than reproduction"
            + (
                ". The optimum sits EXACTLY on the +/-0.08 tolerance, so this "
                "verdict is decided at the boundary and carries no information "
                "either way -- the refined sweep is what settles it"
                if _at_boundary(entries, "asymmetry_optimum_peak_metric")
                else ""
            ),
        ),
        (
            "chi(2) versus asymmetry is smooth enough to have a meaningful optimum",
            None
            if smoothness.get("factor") is None
            else bool(smoothness["factor"] <= 2.0),
            (
                "no adjacent-point data"
                if smoothness.get("factor") is None
                else f"largest step between adjacent asymmetries is a factor of "
                f"{smoothness['factor']:.2f}"
                + (
                    f" between s = {smoothness['between'][0]} and "
                    f"{smoothness['between'][1]}"
                    if smoothness.get("between")
                    else ""
                )
                + ". A physical chi(2)(s) is single-humped and smooth; a large "
                "jump means the states being compared are not the same states"
            ),
        ),
        (
            "chi(2) vanishes at the symmetric limit",
            _vanishes(entries, "chi2_at_symmetric_limit"),
            "parity forbids a second-order response in a symmetric structure",
        ),
        (
            "barrier optimum near the published 1 nm",
            _within(entries, "barrier_optimum_peak_metric"),
            "ideal optimum, distinct from the 1.8 nm fabricated design; agrees "
            "under both metrics",
        ),
        (
            "grading reduces chi(2) in the published proportion",
            _within(entries, "graded_to_abrupt_chi2_ratio"),
            "a ratio, so the unknown absolute scale cancels",
        ),
        (
            "envelopes orthonormal and chi(2) origin independent",
            _all_true(results, "envelopes_orthonormal")
            and _all_true(results, "chi2_origin_independent"),
            "Eq. 2 contains diagonal dipoles; without orthonormality the result "
            "depends on where z = 0 is placed. Near chi(2) = 0 the residual is "
            "judged absolutely rather than relatively, because dividing rounding "
            "noise by rounding noise is not a measurement",
        ),
        (
            "Eq. 2 summed over exactly the configured state window",
            _all_true(results, "chi2_state_window_as_configured"),
            f"metric.max_states_per_band = "
            f"{metric_cfg.get('max_states_per_band', 2)}; this is independent of "
            "numerical.number_of_electron_states, which only sets how many states "
            "the solver returns",
        ),
        (
            "the state-count sweep actually varied the sum",
            _state_count_convergence_meaningful(results),
            "requesting more solver states does not widen Eq. 2's m,n,l sums. A "
            "state-count sweep in which the term count never changes has not "
            "demonstrated convergence of anything. This checks only that the knob "
            "is connected -- see the next criterion for whether chi(2) converged",
        ),
        (
            "chi(2) is converged in the number of states Eq. 2 sums over",
            window_convergence["converged"],
            window_convergence["reason"]
            + (
                f". {len(window_convergence['excluded'])} window(s) excluded for "
                "pulling an unbound state into the sum"
                if window_convergence["excluded"]
                else ""
            ),
        ),
        (
            "every state entering Eq. 2 passes the bound-state criterion",
            _all_true(results, "chi2_states_pass_bound_criterion"),
            f"quasi-bound policy in force: "
            f"{validation_cfg.get('quasi_bound_state_policy', 'warn')}; "
            "state-resolved values are in each case's quasi_bound_states.csv",
        ),
    ]
    status = _status_table(
        entries=entries,
        criteria=criteria,
        results=results,
        stage3b=stage3b or {},
        smoothness=smoothness,
        optima=optima,
        window_convergence=window_convergence,
    )
    return {
        "entries": entries,
        "summary": summary,
        "criteria": criteria,
        "status": status,
        # Carried so the figure writers can mark the paper's published values
        # without re-reading paper_targets.yaml and risking a second, divergent
        # copy of them.
        "published": dict(published),
        # Digitised curves are carried separately from `published` so nothing
        # downstream can mistake a value read off a raster for a quoted one.
        "digitised_figure_2d": dict(
            (targets.get("digitised_figures") or {}).get("figure_2d") or {}
        ),
        "state_window_convergence": window_convergence,
        "metrics": {name: dict(spec) for name, spec in METRICS.items()},
        "primary_metric": PRIMARY_METRIC,
        "optima": optima,
        "smoothness": smoothness,
    }


def _state_count_convergence_meaningful(
    results: Sequence[sweeps.CaseResult],
) -> bool | None:
    """Did the state-count sweep change how many terms Eq. 2 evaluated?

    The 2026-07-31 run swept 3, 4, and 6 solver states and got chi(2) agreeing
    to ~1e-13. That is not convergence: the sum is capped at
    ``max_states_per_band`` regardless, so all three cases evaluated an
    identical number of identical terms. Reporting the agreement as convergence
    would be reporting that a knob which was never connected had no effect.

    This answers only "is the knob connected". Whether chi(2) is actually
    *converged* in the size of the sum is a separate and much harder question,
    answered by :func:`_state_window_convergence` -- conflating the two is
    exactly the mistake this function exists to prevent.
    """

    counts = {
        int(r.observables["chi2_triple_sum_terms_evaluated"])
        for r in results
        if r.spec.metadata.get("stage") == "stage2"
        and r.observables.get("chi2_triple_sum_terms_evaluated") is not None
    }
    if len(counts) < 2:
        return None if not counts else False
    return True


def _state_window_convergence(
    results: Sequence[sweeps.CaseResult], *, relative_tolerance: float
) -> dict[str, Any]:
    """Is chi(2) stable against the number of states Eq. 2 sums over?

    A window sweep that changes the term count proves the knob works. It does
    not prove the answer stopped moving, and on 2026-07-31 it emphatically had
    not: going from two states per band to three dropped the peak |chi(2)| by a
    factor of 20 and moved the resonance from 1519 nm to 1461 nm. The paper
    specifies two states, but at its own design point the third heavy hole sits
    1-3 meV away, so the truncation discards half of a hybridised pair.

    Cases whose widened window pulls in a state that fails the bound-state
    criterion are excluded and listed. Including an unbound state in Eq. 2 is
    not a convergence data point -- it is a different, invalid calculation --
    and silently averaging it in would make the spread look either better or
    worse for the wrong reason.
    """

    points: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for result in results:
        window = result.observables.get("chi2_max_states_per_band")
        magnitude = result.observables.get("chi2_peak_magnitude")
        if window is None or magnitude is None or not result.solver_success:
            continue
        if "max_states_per_band" not in result.spec.swept:
            continue
        entry = {
            "case_id": result.spec.case_id,
            "max_states_per_band": int(window),
            "peak_magnitude": float(magnitude),
            "peak_wavelength_nm": result.observables.get("chi2_peak_wavelength_nm"),
            "terms": result.observables.get("chi2_triple_sum_terms_evaluated"),
        }
        if result.validation.get("chi2_states_pass_bound_criterion") is False:
            entry["reason"] = (
                "the widened window pulls an unbound state into Eq. 2; this is a "
                "different calculation, not a convergence point"
            )
            excluded.append(entry)
            continue
        points.append(entry)

    points.sort(key=lambda item: item["max_states_per_band"])
    record: dict[str, Any] = {
        "relative_tolerance": float(relative_tolerance),
        "points": points,
        "excluded": excluded,
        "converged": None,
        "relative_spread": None,
        "largest_step": None,
    }
    if len(points) < 2:
        record["reason"] = (
            f"only {len(points)} usable window(s); convergence of Eq. 2 in the "
            "number of states it sums over is UNVERIFIED"
            + (
                f". {len(excluded)} case(s) were excluded for pulling an unbound "
                "state into the sum, which is itself a finding: the quantum region "
                "cannot support a wider window as configured"
                if excluded
                else ""
            )
        )
        return record

    magnitudes = [p["peak_magnitude"] for p in points]
    largest = max(abs(m) for m in magnitudes)
    if largest <= 0:
        record["reason"] = "every window gives zero; nothing to compare"
        return record
    record["relative_spread"] = (max(magnitudes) - min(magnitudes)) / largest
    steps = [
        abs(b["peak_magnitude"] - a["peak_magnitude"]) / max(abs(a["peak_magnitude"]), 1e-300)
        for a, b in zip(points, points[1:])
    ]
    record["largest_step"] = max(steps) if steps else None
    record["converged"] = bool(record["relative_spread"] <= float(relative_tolerance))
    record["reason"] = (
        f"windows {[p['max_states_per_band'] for p in points]} give peak |chi(2)| "
        f"{[round(m, 6) for m in magnitudes]}; relative spread "
        f"{record['relative_spread']:.3f} against a tolerance of "
        f"{relative_tolerance:.3f}"
    )
    return record


def _optimum_margin_note(optima: Mapping[str, Any]) -> str:
    """How decisively the asymmetry optimum beats its runner-up, if at all.

    A maximum that leads the next point by less than the sweep's own numerical
    scatter is a ranking, not a maximum, and saying so is the whole point of
    carrying the margin around. Silent when there is nothing to report.
    """

    record = (optima.get("asymmetry") or {}).get(PRIMARY_METRIC) or {}
    record = record.get("refined") or record.get("coarse") or {}
    margin = record.get("runner_up_margin_fraction")
    if margin is None or record.get("value") is None:
        return ""
    return (
        f" On the intrinsic peak metric the optimum is at s = {record['value']:.2f}, "
        f"ahead of s = {record['runner_up']:.2f} by {margin * 100:.1f}%. Treat that "
        "against the residual grid drift of the sweep before reading it as a "
        "located maximum."
    )


def _status_table(
    *,
    entries: Sequence[Mapping[str, Any]],
    criteria: Sequence[tuple[str, bool | None, str]],
    results: Sequence[sweeps.CaseResult],
    stage3b: Mapping[str, Any],
    smoothness: Mapping[str, Any],
    optima: Mapping[str, Any],
    window_convergence: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify each claim on the six-level reproduction scale.

    Deliberately separate claims stay separate. The reference structure's
    resonance is reproduced on its own evidence and is not downgraded because a
    different question -- which asymmetry is optimal -- is unresolved.
    """

    def entry(name: str) -> Mapping[str, Any] | None:
        return next((e for e in entries if e["quantity"] == name), None)

    def verdict(name: str, *, provisional_ok: bool = True) -> str:
        item = entry(name)
        if item is None or not item["evaluated"]:
            return UNRESOLVED
        # A value sitting exactly on its tolerance has not failed and has not
        # passed; calling it either would overstate what the sweep resolved.
        if item.get("at_tolerance_boundary"):
            return PROVISIONAL
        if item["within_tolerance"] is False:
            return FAILED
        if item.get("provisional") and provisional_ok:
            return PROVISIONAL
        return REPRODUCED

    claims: list[dict[str, Any]] = [
        {
            "claim": "transition energies (E1-HH1, E2-HH2)",
            "status": (
                REPRODUCED
                if verdict("ground_interband_transition") == REPRODUCED
                and verdict("excited_interband_transition") == REPRODUCED
                else FAILED
                if FAILED
                in (
                    verdict("ground_interband_transition"),
                    verdict("excited_interband_transition"),
                )
                else UNRESOLVED
            ),
            "detail": "computed for the designed layers with no material parameter "
            "adjusted, and inside the stated tolerance",
        },
        {
            "claim": "resonance wavelength near 1520 nm, reference structure",
            "status": verdict("focused_scan_peak_wavelength"),
            "detail": "an independent statement about the reference structure. It "
            "stands on its own evidence and is NOT downgraded because the "
            "asymmetry optimum is unresolved -- they are different claims about "
            "different things",
        },
        {
            "claim": "tunnelling-barrier optimum near 1 nm",
            "status": verdict("barrier_optimum_peak_metric"),
            "detail": "the optimum falls at the same barrier under both metrics, so "
            "it does not depend on the fixed-wavelength artifact",
        },
        {
            "claim": "graded-to-abrupt chi(2) ratio",
            "status": verdict("graded_to_abrupt_chi2_ratio"),
            "detail": "a ratio, so the unknown absolute scale cancels",
        },
        {
            "claim": "chi(2) origin independence",
            "status": (
                REPRODUCED
                if _all_true(results, "chi2_origin_independent")
                else FAILED
                if _all_true(results, "chi2_origin_independent") is False
                else UNRESOLVED
            ),
            "detail": "passes once the near-zero case is judged on its absolute "
            "residual instead of a relative one. The symmetric structure is still "
            "checked; it is checked against the tolerance that means something "
            "there",
        },
        {
            "claim": "asymmetry optimum near s = 0.42",
            "status": PROVISIONAL
            if verdict("asymmetry_optimum_peak_metric") in (REPRODUCED, PROVISIONAL)
            else verdict("asymmetry_optimum_peak_metric"),
            "detail": "NOT reproduced. Pending physical-state tracking across the "
            "refined sweep."
            + _optimum_margin_note(optima),
        },
        {
            "claim": "smoothness of chi(2) versus asymmetry",
            "status": (
                UNRESOLVED
                if smoothness.get("factor") is None
                else REPRODUCED
                if smoothness["factor"] <= 2.0
                else FAILED
            ),
            "detail": (
                "no adjacent-point data yet"
                if smoothness.get("factor") is None
                else f"largest adjacent-point step is a factor of "
                f"{smoothness['factor']:.2f} under raw energy-index labelling. "
                "Under raw indexing this is a FAIL; whether it survives physical-"
                "state tracking is what the refined sweep decides"
            ),
        },
        {
            # Two separate questions, and collapsing them into one status is how
            # a disconnected knob came to look like convergence in the first
            # place. "The sweep varies the sum" is plumbing; "chi(2) stopped
            # moving" is the physics, and only the second can be `converged`.
            "claim": "state-count sweep is wired to the sum (plumbing)",
            "status": (
                CONVERGED
                if _state_count_convergence_meaningful(results) is True
                else UNRESOLVED
            ),
            "detail": "the summation window changes the term count, so the sweep "
            "measures something. This says nothing about whether chi(2) converged",
        },
        {
            "claim": "chi(2) converged in the size of Eq. 2's state sum",
            "status": (
                CONVERGED
                if window_convergence.get("converged") is True
                else UNRESOLVED
                if window_convergence.get("converged") is None
                else FAILED
            ),
            "detail": window_convergence.get("reason", "not evaluated")
            + (
                ". Eq. 2 as the paper specifies it -- two states per band -- is "
                "NOT converged, so every number downstream of the chi(2) SCAN, "
                "including the resonance position it puts at ~1520 nm, inherits "
                "that. The transition energies themselves are solver eigenvalues "
                "and are unaffected"
                if window_convergence.get("converged") is False
                else ""
            ),
        },
        {
            "claim": "cause of the chi(2)-versus-asymmetry discontinuity",
            "status": (
                UNRESOLVED
                if not stage3b.get("available")
                else PROVISIONAL
                if stage3b.get("reordering_detected")
                or stage3b.get("tracking_changes_chi2_at")
                else FAILED
                if (smoothness.get("factor") or 0) > 2.0
                else REPRODUCED
            ),
            "detail": (
                stage3b.get("reason", "state tracking has not run")
                if not stage3b.get("available")
                else (
                    f"{stage3b.get('points', 0)} refined points tracked with "
                    f"{stage3b.get('ambiguous_assignments', 0)} ambiguous "
                    "assignment(s). "
                    + (
                        "Tracking reorders states and changes chi(2), so the "
                        "raw-index curve was comparing different physical states "
                        "at different sweep points."
                        if stage3b.get("tracking_changes_chi2_at")
                        else "Tracking changes NOTHING: the raw index already is "
                        "the physically continuous labelling. The discontinuity "
                        "is therefore NOT a labelling artifact and needs a "
                        "physical explanation."
                    )
                )
            ),
        },
        {
            "claim": "run completed mechanically",
            "status": MECHANICAL,
            "detail": f"{sum(1 for r in results if r.solver_success)} of "
            f"{len(results)} cases completed. Says nothing about any number",
        },
    ]
    counts = {status: 0 for status in STATUS_ORDER}
    for claim in claims:
        counts[claim["status"]] = counts.get(claim["status"], 0) + 1
    return {
        "vocabulary": dict(STATUS_MEANING),
        "claims": claims,
        "counts": counts,
        "reproduced_claims": [c["claim"] for c in claims if c["status"] == REPRODUCED],
        "unresolved_claims": [
            c["claim"] for c in claims if c["status"] in (UNRESOLVED, PROVISIONAL, FAILED)
        ],
    }


#: The two ways a sweep point's chi(2) can be scored, and what each one means.
#:
#: They are NOT interchangeable. `peak_chi2_magnitude` is the largest |chi(2)|
#: anywhere in the scanned band, so it measures the structure's intrinsic
#: nonlinear strength regardless of where its resonance sits. `chi2_at_
#: reference_wavelength` is the response at one fixed wavelength, which is what
#: a device at that wavelength would see -- and which, across a sweep whose
#: resonance moves by ~100 nm against a 5 meV linewidth, also ranks structures
#: by how close their resonance happens to fall to that wavelength.
METRICS: Mapping[str, Mapping[str, str]] = {
    "peak_chi2_magnitude": {
        "observable": "chi2_peak_magnitude",
        "label": "peak |chi(2)| over the focused scan",
        "meaning": "intrinsic, detuning-independent nonlinear magnitude",
    },
    "chi2_at_reference_wavelength": {
        "observable": "chi2_relative_at_reference",
        "label": "|chi(2)| at the reference wavelength",
        "meaning": "application-specific response at one fixed wavelength; "
        "confounded with resonance detuning across a sweep",
    },
}

#: Which metric the paper's optimum claims are judged against. The paper's
#: statement is about which structure is most nonlinear, not about which one
#: happens to be resonant at 1550 nm.
PRIMARY_METRIC = "peak_chi2_magnitude"


def _optimum(
    results: Sequence[sweeps.CaseResult], parameter: str, observable: str
) -> dict[str, Any]:
    """Where a swept parameter maximises one observable, and by how much.

    The runner-up margin is part of the answer. An optimum that beats its
    neighbour by 2% on a curve whose points scatter by more than that is a
    ranking, not a maximum, and the report has to be able to say so.
    """

    points = sorted(
        (
            (float(r.observables[parameter]), float(r.observables[observable]), r.spec.case_id)
            for r in results
            if r.observables.get(parameter) is not None
            and r.observables.get(observable) is not None
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    if not points:
        return {"value": None, "magnitude": None, "runner_up": None,
                "runner_up_margin_fraction": None, "points": 0, "case_id": None}
    best_x, best_y, best_case = points[0]
    runner_up = points[1] if len(points) > 1 else None
    margin = None
    if runner_up is not None and best_y != 0:
        margin = (best_y - runner_up[1]) / abs(best_y)
    return {
        "value": best_x,
        "magnitude": best_y,
        "case_id": best_case,
        "runner_up": None if runner_up is None else runner_up[0],
        "runner_up_magnitude": None if runner_up is None else runner_up[1],
        "runner_up_margin_fraction": margin,
        "points": len(points),
    }


def _monotone_break(
    results: Sequence[sweeps.CaseResult],
    parameter: str,
    observable: str,
    *,
    relative_floor: float = 1.0e-6,
) -> dict[str, Any]:
    """Largest point-to-point jump in a sweep, as a factor.

    A smooth chi(2)(s) has neighbouring points within a few percent of one
    another. The 2026-07-31 run had an 8.5x step between adjacent asymmetries,
    and nothing in the report registered it because every individual comparison
    was inside its tolerance. This measures it directly.

    Points that are numerically zero are skipped, and the count of skipped pairs
    is reported. The symmetric limit is a parity zero -- required physics, not a
    discontinuity -- and a ratio taken against it is ~1e11, which would swamp
    the real 8.5x step this is meant to find. Skipping is recorded rather than
    silent, because "we did not measure the step next to s = 0" is a different
    statement from "there was no step there".
    """

    points = sorted(
        (
            (float(r.observables[parameter]), float(r.observables[observable]), r.spec.case_id)
            for r in results
            if r.observables.get(parameter) is not None
            and r.observables.get(observable) is not None
        ),
        key=lambda item: item[0],
    )
    magnitudes = [abs(y) for _, y, _ in points]
    floor = (max(magnitudes) * float(relative_floor)) if magnitudes else 0.0
    worst: dict[str, Any] = {"factor": None, "between": None, "case_ids": None}
    skipped: list[str] = []
    for (x0, y0, c0), (x1, y1, c1) in zip(points, points[1:]):
        low, high = sorted((abs(y0), abs(y1)))
        if low <= floor:
            skipped.append(f"{c0}->{c1}")
            continue
        factor = high / low
        if worst["factor"] is None or factor > worst["factor"]:
            worst = {"factor": factor, "between": [x0, x1], "case_ids": [c0, c1]}
    worst["points"] = len(points)
    worst["skipped_pairs"] = skipped
    worst["numerically_zero_floor"] = floor
    return worst


def _within(entries: Sequence[Mapping[str, Any]], name: str) -> bool | None:
    for entry in entries:
        if entry["quantity"] == name:
            return entry["within_tolerance"]
    return None


def _at_boundary(entries: Sequence[Mapping[str, Any]], name: str) -> bool:
    """Is this comparison sitting exactly on its tolerance?"""

    for entry in entries:
        if entry["quantity"] == name:
            return bool(entry.get("at_tolerance_boundary"))
    return False


def _all_within(entries: Sequence[Mapping[str, Any]], names: Sequence[str]) -> bool | None:
    values = [_within(entries, name) for name in names]
    if any(value is None for value in values):
        return None
    return all(values)


def _vanishes(entries: Sequence[Mapping[str, Any]], name: str) -> bool | None:
    for entry in entries:
        if entry["quantity"] == name:
            ours = entry["our_value"]
            if ours is None:
                return None
            return bool(abs(float(ours)) < 1e-6)
    return None


def _all_true(results: Sequence[sweeps.CaseResult], key: str) -> bool | None:
    values = [
        r.validation.get(key) for r in results if r.solver_success and key in r.validation
    ]
    if not values:
        return None
    return all(bool(value) for value in values)


def write_tables(
    parent: Path,
    targets: Mapping[str, Any],
    results: Sequence[sweeps.CaseResult],
    comparison: Mapping[str, Any],
) -> None:
    """paper_targets.csv, our_results.csv, comparison_metrics.csv."""

    published = targets["targets"]
    sweeps.write_table(
        parent,
        "paper_targets",
        [
            {
                "quantity": name,
                "value": entry.get("value"),
                "kind": entry.get("kind"),
                "source": " ".join(str(entry.get("source", "")).split()),
            }
            for name, entry in published.items()
        ],
    )
    sweeps.write_table(
        parent,
        "our_results",
        [
            {
                "case_id": r.spec.case_id,
                "stage": r.spec.metadata.get("stage"),
                "label": r.spec.label,
                "status": r.status,
                **{
                    key: value
                    for key, value in r.observables.items()
                    if isinstance(value, (int, float, str, bool)) or value is None
                },
            }
            for r in results
        ],
    )
    sweeps.write_table(parent, "comparison_metrics", list(comparison["entries"]))


def write_assumptions(parent: Path, targets: Mapping[str, Any], cfg: Mapping[str, Any]) -> None:
    """assumptions_and_unknowns.yaml — everything the reproduction rests on."""

    write_text_atomically(
        parent / "assumptions_and_unknowns.yaml",
        yaml.safe_dump(
            {
                "paper": targets.get("paper", {}),
                "chi2_equation": "Eq. 2 of the paper, implemented in _shared/chi2.py",
                "assumptions": list(chi2mod.ASSUMPTIONS),
                "not_published_by_the_paper": targets.get(
                    "missing_for_absolute_scale", {}
                ),
                "our_settings": (cfg.get("metric") or {}),
                "consequences": {
                    "absolute_magnitude": (
                        "Not independently reproducible. Requires r_e_hh and N_z."
                    ),
                    "resonance_positions": (
                        "Reproducible: they follow from the transition energies alone."
                    ),
                    "trends": (
                        "Reproducible: asymmetry, barrier, and interface trends are "
                        "ratios in which the unknown absolute scale cancels."
                    ),
                    "measured_values": (
                        "Outside scope: they fold in band bending, standing waves, "
                        "sample placement, and a fitted extraction parameter."
                    ),
                },
            },
            sort_keys=False,
            default_flow_style=False,
        ),
    )


def figure2d_comparison(
    path: Path,
    *,
    focused_csv: Path,
    published: Mapping[str, Any],
    window_curves: Sequence[tuple[int, Path]] = (),
) -> None:
    """Rebuild the paper's Fig. 2d and overlay this work on it.

    Fig. 2d plots the SHG response of the coupled-QW sample against fundamental
    wavelength over 1400-1800 nm: a resonance near 1560 nm measured, near
    1520 nm simulated, and a flat control with no resonance at all.

    What can honestly be drawn here is limited, and the figure says so on its
    face rather than in a caption somebody might not read:

    * The paper's *curves* are not published as data. Only the two peak
      positions it states in the text are, so those are drawn as marked
      wavelengths, never as a fabricated lineshape.
    * Fig. 2a-2c are the measurement geometry, the rotation-angle polar
      response and the power-squared linearity. Those are measurement
      signatures, not electronic structure, and this calculation cannot produce
      them. Only 2d is comparable.
    * The control sample is flat by measurement. Nothing is simulated for it,
      so nothing is drawn for it.
    * Our curve is |chi(2)| in arbitrary units and the paper's 2d axis is
      measured SH signal. Both are normalised to their own maximum, which makes
      the peak *positions* comparable and the heights meaningless -- stated on
      the axis label so the normalisation cannot be mistaken for agreement.
    """

    plt = plotting.plt
    if plt is None:
        plotting.placeholder(path, "Figure 2d comparison")
        return
    if not focused_csv.is_file():
        plotting.placeholder(
            path,
            "Figure 2d comparison",
            reason="no focused wavelength scan; needs a completed reference case.",
        )
        return

    data = np.loadtxt(focused_csv, delimiter=",", skiprows=1)
    wavelength, magnitude = data[:, 0], data[:, 3]
    peak_nm = float(wavelength[int(np.argmax(magnitude))])
    scale = float(np.max(magnitude)) or 1.0

    simulated = float(published["simulated_resonance_nm"]["value"])
    measured = float(published["measured_resonance_nm"]["value"])

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.plot(
        wavelength, magnitude / scale, "-", linewidth=2.0, color="#1f77b4",
        label=f"this work, |chi(2)| (2 states/band), peak {peak_nm:.0f} nm",
    )

    # The same quantity with a wider Eq. 2 sum. Not a detail: the 2026-07-31
    # run showed the peak moving 1519 -> 1461 nm when a third state enters, so
    # a Fig. 2d comparison that shows only the two-state curve would be
    # claiming a resonance position the calculation has not converged.
    for states, curve_path in window_curves:
        if not curve_path.is_file():
            continue
        curve = np.loadtxt(curve_path, delimiter=",", skiprows=1)
        values = curve[:, 3]
        top = float(np.max(values)) or 1.0
        ax.plot(
            curve[:, 0], values / top, "--", linewidth=1.2, alpha=0.85,
            label=f"this work, {states} states/band, peak "
            f"{float(curve[int(np.argmax(values)), 0]):.0f} nm",
        )

    ax.axvline(simulated, color="#d62728", linestyle="--", linewidth=1.6,
               label=f"paper, simulated ~{simulated:.0f} nm")
    ax.axvline(measured, color="#2ca02c", linestyle="-.", linewidth=1.6,
               label=f"paper, measured ~{measured:.0f} nm")
    ax.plot([peak_nm], [1.0], "o", color="#1f77b4", markersize=8, zorder=5)

    ax.annotate(
        f"{peak_nm - simulated:+.0f} nm vs the paper's simulation",
        xy=(peak_nm, 1.0), xytext=(peak_nm + 45, 0.86), fontsize=8,
        arrowprops=dict(arrowstyle="->", color="0.4", linewidth=0.8),
    )
    ax.text(
        0.015, 0.03,
        "Paper's control sample shows no resonance (measured). Not simulated "
        "here, so not drawn.\nFig. 2a-2c are measurement signatures and are "
        "outside what this calculation can produce.\nBoth axes normalised to "
        "their own maximum: peak POSITIONS are comparable, heights are not.",
        transform=ax.transAxes, fontsize=7, color="0.35", va="bottom",
    )
    ax.set(
        xlabel="Fundamental wavelength (nm)",
        ylabel="Normalised SHG response / |chi(2)| (arb.)",
        title="Figure 2d comparison — SHG versus fundamental wavelength\n"
        "arXiv:2602.23246v1 Fig. 2d, with this work overlaid",
        xlim=(float(wavelength.min()), float(wavelength.max())),
        ylim=(0.0, 1.18),
    )
    ax.legend(fontsize=7.5, loc="upper right", framealpha=0.9)
    ax.grid(alpha=0.25)
    plotting.save_figure(fig, path)


def _prominent_peaks(
    x: np.ndarray,
    y: np.ndarray,
    *,
    minimum_height: float,
    minimum_prominence: float,
) -> list[float]:
    """Local maxima that stand clear of their surroundings.

    A bare local-maximum test picks up every numerical wiggle on the shoulder of
    a real resonance -- the 2 nm sampling of the broad scan produces a dozen of
    them around 1350 nm alone. Prominence is measured as the drop to the lowest
    point between this maximum and the nearest higher one on each side, which is
    the standard definition and needs no scipy: the licensed ``llm``
    environment is not guaranteed to have it.
    """

    values = np.asarray(y, dtype=float)
    peaks: list[float] = []
    for index in range(1, values.size - 1):
        if values[index] <= values[index - 1] or values[index] <= values[index + 1]:
            continue
        if values[index] < minimum_height:
            continue
        left = values[:index]
        right = values[index + 1:]
        higher_left = np.flatnonzero(left >= values[index])
        higher_right = np.flatnonzero(right >= values[index])
        low_left = float(np.min(left[higher_left[-1]:])) if higher_left.size else float(
            np.min(left)
        )
        low_right = float(np.min(right[: higher_right[0] + 1])) if higher_right.size else (
            float(np.min(right))
        )
        prominence = values[index] - max(low_left, low_right)
        if prominence >= minimum_prominence:
            peaks.append(float(x[index]))
    return peaks


def figure2d_comparison_broad(
    path: Path,
    *,
    broad_csv: Path,
    digitised: Mapping[str, Any] | None,
    annotate_peaks: bool = False,
) -> dict[str, Any]:
    """Fig. 2d over its full published range, paper curve drawn as a curve.

    The companion :func:`figure2d_comparison` marks the paper's two text-quoted
    peak wavelengths as vertical lines over the telecom window. This one
    reproduces Fig. 2d as the paper actually drew it -- 400-1800 nm, simulated
    |chi(2)| on the left axis, measured SH intensity on the right -- so the two
    simulations can be compared as *lineshapes* rather than as two numbers.

    The paper's curve here is **digitised by eye from the published raster**.
    Its reading uncertainty is stated in the provenance note below the axes,
    but the clean comparison itself contains only the curve series requested by
    the user. This is weaker evidence than a quoted number and the figure says
    so on its face.
    """

    plt = plotting.plt
    if plt is None:
        plotting.placeholder(path, "Figure 2d comparison (full range)")
        return
    if not broad_csv.is_file() or not digitised:
        plotting.placeholder(
            path,
            "Figure 2d comparison (full range)",
            reason=(
                "needs the broad 400-1800 nm scan and the digitised Fig. 2d data."
            ),
        )
        return

    data = np.loadtxt(broad_csv, delimiter=",", skiprows=1)
    wavelength, magnitude = data[:, 0], data[:, 3]
    ours = magnitude / (float(np.max(magnitude)) or 1.0)

    simulation = digitised["simulation_pm_per_V"]
    sim_nm = np.asarray(simulation["wavelength_nm"], dtype=float)
    sim_value = np.asarray(simulation["value"], dtype=float)
    sim_norm = sim_value / (float(np.max(sim_value)) or 1.0)
    band = float(digitised.get("amplitude_uncertainty_fraction", 0.15))

    fig, ax = plt.subplots(figsize=(10.0, 6.4))
    # Space reserved below the axes for the verdict and the digitising caveat.
    # save_figure is told not to run tight_layout, which would undo this.
    fig.subplots_adjust(
        bottom=0.30 if annotate_peaks else 0.19,
        top=0.87,
        left=0.085,
        right=0.90,
    )
    ax.plot(
        sim_nm, sim_norm, "--", color="0.25", linewidth=1.8,
        label="paper, simulated (digitised from Fig. 2d)",
    )
    ax.plot(
        wavelength, ours, "-", color="#1f77b4", linewidth=2.0,
        label="this work, |chi(2)| (2 states/band)",
    )

    # Peak classification remains available for diagnostic rerenders, but the
    # publication/default figure is intentionally just the curves and their
    # legend.  The previous annotation boxes obscured the comparison itself.
    matched_peaks: list[float] = []
    missing_peaks: list[float] = []
    extra: list[float] = []
    if annotate_peaks:
        for peak in digitised.get("simulation_peaks_nm", []):
            near = float(ours[np.argmin(np.abs(wavelength - float(peak)))])
            matched = near > 0.4
            (matched_peaks if matched else missing_peaks).append(float(peak))
            ax.axvline(
                float(peak), color="#2ca02c" if matched else "#d62728",
                linestyle=":", linewidth=1.3, alpha=0.8,
            )
            ax.annotate(
                f"{peak:.0f} nm\n{'both' if matched else 'paper only'}",
                xy=(float(peak), 1.30), fontsize=7.5, ha="center", va="center",
                color="#2ca02c" if matched else "#d62728",
                bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                          edgecolor="0.8", linewidth=0.5),
            )

        candidates = _prominent_peaks(
            wavelength, ours, minimum_height=0.4, minimum_prominence=0.1
        )
        sim_on_our_grid = np.interp(wavelength, sim_nm, sim_norm)
        for here in candidates:
            index = int(np.argmin(np.abs(wavelength - here)))
            if any(abs(here - p) < 100 for p in matched_peaks + missing_peaks + extra):
                continue
            if sim_on_our_grid[index] > 0.55:
                continue
            extra.append(here)
        for here in extra:
            ax.axvline(here, color="#9467bd", linestyle=":", linewidth=1.3, alpha=0.8)
            ax.annotate(
                f"{here:.0f} nm\nours only", xy=(here, 1.30), fontsize=7.5,
                ha="center", va="center", color="#9467bd",
                bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                          edgecolor="0.8", linewidth=0.5),
            )

    right = ax.twinx()
    for key, colour, marker, label in (
        ("measured_80_period", "#d62728", "s", "measured, 80-period sample"),
        ("measured_algaas_control", "#bf9000", "s", "measured, AlGaAs control"),
        ("measured_gaas_control", "#1f4e9c", "s", "measured, GaAs control"),
    ):
        series = digitised.get(key)
        if not series:
            continue
        right.plot(
            series["wavelength_nm"], series["value"], marker, color=colour,
            markersize=4.5, linestyle="-", linewidth=0.9, alpha=0.9, label=label,
        )
    right.set_ylabel("Measured normalised SH intensity (arb. u.), digitised")
    right.set_ylim(0, 230)

    ax.set(
        xlabel="Fundamental wavelength (nm)",
        ylabel="Simulated |chi(2)|, each curve normalised to its own maximum",
        xlim=(400, 1800),
        ylim=(0, 1.42 if annotate_peaks else 1.08),
    )
    ax.set_title(
        "Figure 2d comparison, full published range — arXiv:2602.23246v1\n"
        "paper simulation digitised from the figure; this work overlaid",
        fontsize=11, pad=12,
    )
    handles, labels = ax.get_legend_handles_labels()
    rh, rl = right.get_legend_handles_labels()
    ax.legend(
        handles + rh, labels + rl, fontsize=7.5, loc="upper left",
        bbox_to_anchor=(0.008, 0.86), framealpha=0.92, ncol=2,
    )
    ax.grid(alpha=0.22)

    if annotate_peaks:
        verdict = (
            f"Peak positions: {len(matched_peaks)} of "
            f"{len(matched_peaks) + len(missing_peaks)} of the paper's simulated peaks "
            "appear here"
            + (f" ({', '.join(f'{p:.0f}' for p in matched_peaks)} nm)" if matched_peaks else "")
            + (
                f"; {', '.join(f'{p:.0f}' for p in missing_peaks)} nm "
                f"{'are' if len(missing_peaks) > 1 else 'is'} absent"
                if missing_peaks
                else ""
            )
            + (
                f"; this work additionally peaks at {', '.join(f'{p:.0f}' for p in extra)} nm"
                if extra
                else ""
            )
            + "."
        )
        fig.text(
            0.5, 0.135, verdict, fontsize=8.5, color="0.15", ha="center", va="center",
        )
    fig.text(
        0.5, 0.052,
        "Paper curve DIGITISED BY EYE from a raster figure: positions +/-"
        f"{digitised.get('wavelength_uncertainty_nm', 20):.0f} nm, heights +/-"
        f"{band * 100:.0f}%. Not a published data series; do not quote it or "
        "calibrate against it.\nBoth simulations normalised to their own maximum: "
        "the paper's absolute pm/V scale is not independently reproducible here, so "
        "only lineshape and peak positions are being compared.",
        fontsize=7.5, color="0.4", ha="center", va="center",
    )
    plotting.save_figure(fig, path, tight=False)


def _tracking_plots(
    plots_dir: Path,
    results: Sequence[sweeps.CaseResult],
    stage3b: Mapping[str, Any],
    series: Any,
) -> None:
    """Stage 3b figures: the same sweep seen two ways.

    Every figure is emitted even with nothing to draw, as a labelled
    placeholder, so a missing file always means a bug rather than "this machine
    has no licence".
    """

    rows = list(stage3b.get("rows") or [])
    comparison_rows = list(stage3b.get("comparison") or [])

    def branch(band: str, key: str) -> dict[str, tuple[list[float], list[float]]]:
        out: dict[str, tuple[list[float], list[float]]] = {}
        for row in rows:
            if row.get("band") != band:
                continue
            label = row.get(key)
            if label is None:
                continue
            name = f"{band} {key.replace('_', ' ')} {label}"
            xs, ys = out.setdefault(name, ([], []))
            xs.append(float(row["sweep_value"]))
            ys.append(float(row["energy_eV"]))
        return {
            name: tuple(map(list, zip(*sorted(zip(xs, ys))))) if xs else ([], [])
            for name, (xs, ys) in out.items()
        }

    plotting.line_plot(
        plots_dir / "refined_raw_index_branches.png",
        title="Refined sweep: energies labelled by raw solver index",
        xlabel="Asymmetry s",
        ylabel="Energy (eV)",
        series={**branch("electron", "raw_index"), **branch("heavy_hole", "raw_index")},
    )
    plotting.line_plot(
        plots_dir / "refined_tracked_branches.png",
        title="Refined sweep: energies labelled by tracked physical state",
        xlabel="Asymmetry s",
        ylabel="Energy (eV)",
        series={
            **branch("electron", "tracked_label"),
            **branch("heavy_hole", "tracked_label"),
        },
    )

    def by_label(band: str, field: str) -> dict[str, tuple[list[float], list[float]]]:
        out: dict[str, tuple[list[float], list[float]]] = {}
        for row in rows:
            if row.get("band") != band or row.get(field) is None:
                continue
            name = f"{band} state {row['tracked_label']}"
            xs, ys = out.setdefault(name, ([], []))
            xs.append(float(row["sweep_value"]))
            ys.append(float(row[field]))
        return {
            name: tuple(map(list, zip(*sorted(zip(xs, ys))))) if xs else ([], [])
            for name, (xs, ys) in out.items()
        }

    plotting.line_plot(
        plots_dir / "refined_localization.png",
        title="Tracked-state localisation across the refined sweep",
        xlabel="Asymmetry s",
        ylabel="Probability in the thick well",
        series=by_label("electron", "probability_left_well"),
    )
    plotting.line_plot(
        plots_dir / "refined_assignment_overlap.png",
        title=(
            "Adjacent-point assignment overlap — a dip is a crossing the tracker "
            "found hard"
        ),
        xlabel="Asymmetry s",
        ylabel="|<psi_previous|psi_current>|",
        series={
            **by_label("electron", "overlap_with_previous"),
            **by_label("heavy_hole", "overlap_with_previous"),
        },
    )
    plotting.line_plot(
        plots_dir / "refined_boundary_probability.png",
        title="Boundary probability of the tracked states",
        xlabel="Asymmetry s",
        ylabel="Probability within 5% of each domain edge",
        series={
            **by_label("electron", "boundary_probability"),
            **by_label("heavy_hole", "boundary_probability"),
        },
        logy=True,
    )

    def compare(key: str) -> tuple[list[float], list[float]]:
        points = sorted(
            (float(row["asymmetry"]), float(row[key]))
            for row in comparison_rows
            if row.get(key) is not None
        )
        return [p[0] for p in points], [p[1] for p in points]

    plotting.line_plot(
        plots_dir / "refined_chi2_raw_vs_tracked.png",
        title="Peak chi(2): raw energy-index labelling versus tracked physical states",
        xlabel="Asymmetry s",
        ylabel="Peak |chi(2)| (relative, arbitrary units)",
        series={
            "raw solver index": compare("chi2_peak_magnitude_raw_index"),
            "tracked physical state": compare("chi2_peak_magnitude_tracked"),
        },
    )


def _fmt(value: Any) -> str:
    """Table cell: em dash for missing, 6 significant figures for numbers."""

    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def write_report(
    parent: Path,
    cfg: Mapping[str, Any],
    targets: Mapping[str, Any],
    comparison: Mapping[str, Any],
    stage5: Mapping[str, Any],
    stage6: Mapping[str, Any],
    manifest: Mapping[str, Any],
    stage3b: Mapping[str, Any] | None = None,
) -> None:
    """paper_comparison_report.md."""

    write_assumptions(parent, targets, cfg)
    paper = targets.get("paper", {})
    summary = comparison["summary"]
    lines = [
        "# Paper comparison report",
        "",
        f"- Target: **{paper.get('title')}** ({paper.get('arxiv')})",
        f"- Run status: `{manifest.get('status')}`",
        f"- Cases: {manifest.get('case_count')} "
        f"(completed {manifest.get('solver_success_count')}, "
        f"skipped {manifest.get('skipped_count')}, failed {manifest.get('failed_count')})",
        "",
        "## The headline, stated first",
        "",
        "The **absolute** chi(2) magnitude is not independently reproducible from ",
        "this paper. It does not publish the HSE06 unit-cell matrix element ",
        "`r_e_hh`, the wells-per-unit-length `N_z`, or the k-space quadrature ",
        "conventions, and those set the scale. What *is* reproducible, and what ",
        "this demo actually tests, is the electronic structure, the resonance ",
        "positions, and the asymmetry / barrier / interface trends.",
        "",
        "## Reproduction status",
        "",
        "Each claim is graded on one scale. Being inside a tolerance is not the "
        "same as being reproduced, and the two are not merged here.",
        "",
        "| claim | status | detail |",
        "|---|---|---|",
    ]
    status = comparison.get("status") or {}
    for claim in status.get("claims", []):
        lines.append(
            f"| {claim['claim']} | `{claim['status']}` | {claim['detail']} |"
        )
    lines += ["", "Status vocabulary:", ""]
    for name in STATUS_ORDER:
        lines.append(f"- `{name}` — {STATUS_MEANING[name]}")
    lines += [
        "",
        "## The two chi(2) metrics",
        "",
        "Sweep optima are reported under both, and the two are not "
        "interchangeable.",
        "",
        "| metric | what it measures |",
        "|---|---|",
    ]
    for name, spec in (comparison.get("metrics") or METRICS).items():
        primary = " **(primary)**" if name == comparison.get("primary_metric") else ""
        lines.append(f"| `{name}`{primary} | {spec['meaning']} |")
    optima = comparison.get("optima") or {}
    if optima:
        lines += [
            "",
            "| sweep | metric | optimum | runner-up | margin | paper | tolerance | verdict |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
        entry_by_name = {e["quantity"]: e for e in comparison["entries"]}
        for sweep_name, quantity_by_metric in (
            (
                "asymmetry",
                {
                    "peak_chi2_magnitude": "asymmetry_optimum_peak_metric",
                    "chi2_at_reference_wavelength": (
                        "asymmetry_optimum_at_reference_wavelength"
                    ),
                },
            ),
            (
                "barrier",
                {
                    "peak_chi2_magnitude": "barrier_optimum_peak_metric",
                    "chi2_at_reference_wavelength": (
                        "barrier_optimum_at_reference_wavelength"
                    ),
                },
            ),
        ):
            for metric_name, quantity in quantity_by_metric.items():
                item = entry_by_name.get(quantity)
                record = (optima.get(sweep_name) or {}).get(metric_name) or {}
                if sweep_name == "asymmetry":
                    record = record.get("refined") or record.get("coarse") or {}
                if item is None:
                    continue
                within = item["within_tolerance"]
                verdict = (
                    "—"
                    if within is None
                    else ("PASS" if within else "**FAIL**")
                )
                if item.get("provisional") and within:
                    verdict = "PASS (provisional)"
                if item.get("at_tolerance_boundary"):
                    verdict = "**on the boundary**"
                margin = record.get("runner_up_margin_fraction")
                lines.append(
                    f"| {sweep_name} | `{metric_name}` "
                    f"| {_fmt(item['our_value'])} "
                    f"| {_fmt(record.get('runner_up'))} "
                    f"| {'—' if margin is None else f'{margin * 100:.1f}%'} "
                    f"| {_fmt(item['paper_value'])} "
                    f"| {_fmt(item.get('tolerance'))} "
                    f"| {verdict} |"
                )
    lines += [
        "",
        "## Classification summary",
        "",
        "| classification | count |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        if key.startswith("comparisons") or key in {"within_tolerance", "evaluated",
                                                    "pending", "not_attempted"}:
            continue
        lines.append(f"| `{key}` | {value} |")
    lines += [
        "",
        f"Evaluated: {summary['evaluated']}. "
        f"Pending (nothing computed yet): {summary['pending']}. "
        f"Not attempted by design: {summary['not_attempted']}.",
    ]
    lines += [
        "",
        f"Comparisons carrying a numeric tolerance: {summary['comparisons_with_a_tolerance']}; "
        f"within tolerance: {summary['within_tolerance']}.",
        "",
        "## Comparisons",
        "",
        "| quantity | paper | ours | units | diff | within tol | classification / outcome |",
        "|---|---:|---:|---|---:|---|---|",
    ]
    for entry in comparison["entries"]:
        def fmt(value: Any) -> str:
            if value is None:
                return "—"
            if isinstance(value, float):
                return f"{value:.6g}"
            return str(value)

        within = entry["within_tolerance"]
        verdict = "—" if within is None else ("yes" if within else "**no**")
        if entry.get("at_tolerance_boundary"):
            verdict = "**on the boundary**"
        if entry.get("provisional"):
            verdict += " *(provisional)*"
        lines.append(
            f"| {entry['quantity']} | {fmt(entry['paper_value'])} | "
            f"{fmt(entry['our_value'])} | {entry['units'] or '—'} | "
            f"{fmt(entry['difference'])} | {verdict} | "
            f"`{entry['classification']}` / `{entry['outcome']}` |"
        )
    lines += ["", "### Notes on each comparison", ""]
    for entry in comparison["entries"]:
        lines.append(f"- **{entry['quantity']}** — {entry['note']}")
        if entry.get("provisional") and entry.get("provisional_reason"):
            lines.append(f"  - *Provisional:* {entry['provisional_reason']}")

    lines += ["", "## chi(2) modes (Stage 5)", ""]
    for name, record in ((stage5 or {}).get("modes") or {}).items():
        available = record.get("available")
        lines.append(f"### `{name}` — {'available' if available else 'not available'}")
        lines.append("")
        lines.append(f"- permitted by the configuration: {record.get('configured')}")
        if available:
            lines.append(f"- units: `{record.get('units')}`")
            lines.append(
                f"- |chi(2)| at the reference wavelength: "
                f"{record.get('magnitude_at_reference')}"
            )
            if record.get("scale_factor") is not None:
                lines.append(f"- fitted scale factor: {record['scale_factor']:.6g}")
        else:
            lines.append(f"- reason: {record.get('reason')}")
        lines.append(f"- what this may claim: {record.get('claim', '—')}")
        lines.append("")

    resonances = (stage6 or {}).get("predicted_resonances_nm") or {}
    if resonances:
        lines += ["## Resonance positions (Stage 6)", ""]
        lines.append(
            "- two-photon (2hbar.omega = E): "
            + ", ".join(f"{value:.1f} nm" for value in resonances.get("two_photon_resonance_nm", []))
        )
        lines.append(
            "- one-photon (hbar.omega = E): "
            + ", ".join(f"{value:.1f} nm" for value in resonances.get("one_photon_resonance_nm", []))
        )
        lines.append("")

    tracking = stage3b or {}
    lines += ["## Physical-state tracking (Stage 3b)", ""]
    if not tracking.get("available"):
        lines += [
            f"- Not available: {tracking.get('reason', 'not run')}",
            "- Until this runs, the asymmetry optimum stays `provisionally_consistent`: "
            "the states being compared across the sweep have not been shown to be the "
            "same states.",
            "",
        ]
    else:
        lines += [
            f"- Refined sweep points tracked: {tracking.get('points')}",
            f"- Assignment backend: "
            f"`{(tracking.get('bands') or {}).get('electron', {}).get('assignment_backend', 'unknown')}`",
            f"- Ambiguous assignments: {tracking.get('ambiguous_assignments')}"
            + (
                f" (at {', '.join(tracking.get('ambiguous_at', []))})"
                if tracking.get("ambiguous_at")
                else ""
            ),
            f"- Raw index and tracked label disagree somewhere: "
            f"{bool(tracking.get('reordering_detected'))}",
            f"- Cases where tracking changes chi(2): "
            + (
                ", ".join(tracking.get("tracking_changes_chi2_at", []))
                or "none — the two labellings give the same chi(2) everywhere"
            ),
            "",
            "Where the two labellings agree, the discontinuity is not a labelling "
            "artifact and needs a different explanation. Where they disagree, the "
            "raw-index curve was comparing different physical states at different "
            "sweep points and its optimum meant nothing.",
            "",
        ]

    lines += [
        "## What would be needed for an independent absolute reproduction",
        "",
        "1. The numerical HSE06 value of `r_e_hh` used by the authors.",
        "2. An unambiguous `N_z` (the paper's own text says the period is 20 nm "
        "while its figure caption and layer arithmetic both give 30 nm).",
        "3. The k-parallel quadrature, zone-edge convention, in-plane masses, and "
        "whether spin degeneracy is folded into the sum.",
        "4. The nextnano input deck, material database version, and boundary "
        "conditions.",
        "",
        "Items 1-3 are recorded in `assumptions_and_unknowns.yaml`.",
        "",
    ]
    write_text_atomically(parent / "paper_comparison_report.md", "\n".join(lines) + "\n")
    write_json_atomically(parent / "comparison.json", dict(comparison))


def write_plots(
    parent: Path,
    cfg: Mapping[str, Any],
    results: Sequence[sweeps.CaseResult],
    reference: sweeps.CaseResult | None,
    stage5: Mapping[str, Any],
    stage6: Mapping[str, Any],
    comparison: Mapping[str, Any],
    stage3b: Mapping[str, Any] | None = None,
) -> None:
    """The figure set required by the demo's README."""

    plots_dir = parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    def series(
        stage: str | Sequence[str], parameter: str, observable: str
    ) -> tuple[list[float], list[float]]:
        stages = (stage,) if isinstance(stage, str) else tuple(stage)
        points: list[tuple[float, float]] = []
        for r in results:
            if r.spec.metadata.get("stage") not in stages:
                continue
            x = r.observables.get(parameter)
            y = r.observables.get(observable)
            if x is None or y is None:
                continue
            points.append((float(x), float(y)))
        points.sort()
        return [p[0] for p in points], [p[1] for p in points]

    # --- asymmetry: both metrics, plus where the resonance actually sits ------
    # Plotted together and unsmoothed. The discontinuity is the finding, not a
    # blemish, and the resonance curve is what explains why the two metrics
    # disagree about the optimum.
    both = ASYMMETRY_STAGES
    peak_series = series(both, "asymmetry", "chi2_peak_magnitude")
    reference_series = series(both, "asymmetry", "chi2_relative_at_reference")
    optima = (comparison.get("optima") or {}).get("asymmetry") or {}

    def _optimum_marker(metric_name: str) -> tuple[list[float], list[float]]:
        record = optima.get(metric_name) or {}
        record = record.get("refined") or record.get("coarse") or {}
        if record.get("value") is None or record.get("magnitude") is None:
            return [], []
        return [float(record["value"])], [float(record["magnitude"])]

    plotting.line_plot(
        plots_dir / "chi2_vs_asymmetry.png",
        title=(
            "chi(2) versus asymmetry: intrinsic peak vs fixed-wavelength "
            "(paper target s = 0.42)"
        ),
        xlabel="Asymmetry s = (d1 - d2)/(d1 + d2)",
        ylabel="|chi(2)| (relative, arbitrary units)",
        series={
            "peak |chi(2)| (primary, detuning-independent)": peak_series,
            "|chi(2)| at the reference wavelength (secondary)": reference_series,
            "paper target s = 0.42": (
                [0.42, 0.42],
                [0.0, max(peak_series[1] or [1.0])],
            ),
            "optimum, peak metric": _optimum_marker("peak_chi2_magnitude"),
            "optimum, reference wavelength": _optimum_marker(
                "chi2_at_reference_wavelength"
            ),
        },
        axhline=0.0,
    )
    plotting.line_plot(
        plots_dir / "chi2_metrics_vs_asymmetry.png",
        title="The two metrics normalised to their own maxima",
        xlabel="Asymmetry s",
        ylabel="|chi(2)| / max|chi(2)| for that metric",
        series={
            name: (
                xs,
                [y / max(ys) for y in ys] if ys and max(ys) > 0 else ys,
            )
            for name, (xs, ys) in (
                ("peak |chi(2)| (primary)", peak_series),
                ("at the reference wavelength (secondary)", reference_series),
            )
        },
        axhline=0.0,
    )
    plotting.line_plot(
        plots_dir / "resonance_vs_asymmetry.png",
        title=(
            "Two-photon resonance versus asymmetry — why a fixed-wavelength "
            "metric is not a ranking of nonlinear strength"
        ),
        xlabel="Asymmetry s",
        ylabel="Peak |chi(2)| wavelength (nm)",
        series={
            "resonance of each structure": series(
                both, "asymmetry", "chi2_peak_wavelength_nm"
            ),
            "reference wavelength": (
                [x for x in (peak_series[0] or [0.0, 1.0])],
                [
                    float((cfg.get("metric") or {}).get("reference_wavelength_nm", 1550.0))
                    for _ in (peak_series[0] or [0.0, 1.0])
                ],
            ),
        },
    )
    _tracking_plots(plots_dir, results, stage3b or {}, series)

    # The paper's Fig. 2d, rebuilt with this work overlaid. The state-window
    # cases are passed in so the figure shows how far the resonance moves when
    # Eq. 2's truncation is relaxed.
    window_curves = sorted(
        (
            int(r.observables["chi2_max_states_per_band"]),
            r.run_dir / "extracted" / "chi2_focused.csv",
        )
        for r in results
        if "max_states_per_band" in r.spec.swept
        and r.observables.get("chi2_max_states_per_band") is not None
        and int(r.observables["chi2_max_states_per_band"]) != int(
            (cfg.get("metric") or {}).get("max_states_per_band", 2)
        )
    )
    figure2d_comparison(
        plots_dir / "figure2d_comparison.png",
        focused_csv=parent / "extracted" / "chi2_focused_wavelength.csv",
        published=(comparison.get("published") or {}),
        window_curves=window_curves,
    )
    figure2d_comparison_broad(
        plots_dir / "figure2d_comparison_broad.png",
        broad_csv=parent / "extracted" / "chi2_broad_wavelength.csv",
        digitised=(comparison.get("digitised_figure_2d") or None),
    )
    plotting.line_plot(
        plots_dir / "localization_vs_asymmetry.png",
        title="Electron localisation versus asymmetry",
        xlabel="Asymmetry s",
        ylabel="Integrated probability",
        series={
            "e1 in thick well": series(both, "asymmetry", "electron1_thick_well_probability"),
            "e1 in thin well": series(both, "asymmetry", "electron1_thin_well_probability"),
            "e2 in thick well": series(both, "asymmetry", "electron2_thick_well_probability"),
            "e2 in thin well": series(both, "asymmetry", "electron2_thin_well_probability"),
        },
    )
    plotting.line_plot(
        plots_dir / "chi2_vs_barrier.png",
        title="chi(2) versus tunnelling-barrier thickness (paper optimum ~1 nm)",
        xlabel="Tunnelling barrier (nm)",
        ylabel="|chi(2)| (relative, arbitrary units)",
        series={
            "peak |chi(2)| (primary)": series(
                "stage4", "tunnel_barrier_nm", "chi2_peak_magnitude"
            ),
            "at the reference wavelength (secondary)": series(
                "stage4", "tunnel_barrier_nm", "chi2_relative_at_reference"
            ),
        },
    )
    for name, filename, title in (
        ("broad", "chi2_broad_wavelength.png", "Relative chi(2) over 400-1800 nm"),
        ("focused", "chi2_focused_wavelength.png", "Relative chi(2) over 1400-1800 nm"),
    ):
        path = parent / "extracted" / f"chi2_{name}_wavelength.csv"
        if not path.is_file():
            continue
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        plotting.line_plot(
            plots_dir / filename,
            title=title,
            xlabel="Fundamental wavelength (nm)",
            ylabel="chi(2) (relative, arbitrary units)",
            series={
                "Re": (data[:, 0], data[:, 1]),
                "Im": (data[:, 0], data[:, 2]),
                "|chi(2)|": (data[:, 0], data[:, 3]),
            },
            markers=False,
        )

    # Transition-energy comparison.
    published = {
        "E1-HH1": 1.49,
        "E2-HH2": 1.62,
    }
    ours = {
        "E1-HH1": reference.observables.get("transition_e1_hh1_eV") if reference else None,
        "E2-HH2": reference.observables.get("transition_e2_hh2_eV") if reference else None,
    }
    labels = [name for name in published if ours.get(name) is not None]
    if labels:
        plotting.line_plot(
            plots_dir / "transition_energy_comparison.png",
            title="Interband transition energies: paper versus this work",
            xlabel="Transition index",
            ylabel="Energy (eV)",
            series={
                "paper": (list(range(1, len(labels) + 1)), [published[n] for n in labels]),
                "this work": (
                    list(range(1, len(labels) + 1)),
                    [float(ours[n]) for n in labels],
                ),
            },
        )

    # Scorecard.
    entries = comparison["entries"]
    scored = [e for e in entries if e["within_tolerance"] is not None]
    plotting.bar_plot(
        plots_dir / "validation_scorecard.png",
        title="Validation scorecard (1 = within tolerance, 0 = outside)",
        xlabel="Comparison",
        ylabel="Within tolerance",
        labels=[e["quantity"] for e in scored],
        values=[1.0 if e["within_tolerance"] else 0.0 for e in scored],
        excluded=[not e["within_tolerance"] for e in scored],
    )
    plotting.bar_plot(
        plots_dir / "paper_vs_simulation_chi2.png",
        title="Published chi(2) values and what this demo can claim about each",
        xlabel="Published quantity",
        ylabel="chi(2) (pm/V)",
        labels=[
            e["quantity"] for e in entries
            if e["units"] == "pm/V" and e["paper_value"] is not None
        ],
        values=[
            float(e["paper_value"]) for e in entries
            if e["units"] == "pm/V" and e["paper_value"] is not None
        ],
        excluded=[
            e["classification"] in (OUT_OF_SCOPE, NOT_REPRODUCIBLE, NEEDS_AUTHORS)
            for e in entries
            if e["units"] == "pm/V" and e["paper_value"] is not None
        ],
    )

    # Convergence.
    plotting.line_plot(
        plots_dir / "convergence_summary.png",
        title="Numerical convergence of the interband transition energies",
        xlabel="Swept numerical parameter",
        ylabel="E1-HH1 (eV)",
        series={
            "grid spacing (nm)": series(
                "stage2", "active_region_grid_spacing_nm", "transition_e1_hh1_eV"
            ),
            "quantum padding (nm)": series(
                "stage2", "quantum_region_padding_nm", "transition_e1_hh1_eV"
            ),
        },
    )
