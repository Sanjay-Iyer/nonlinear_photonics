"""Turn one completed nextnano trial into the full Demo 13 result record.

Section 6 of the Demo 13 specification asks for a complete record per trial, not
one objective number, and this module is where that record is assembled.  It
consumes the observables Demo 11's ``analyse_case`` already produced -- no
physics is re-derived here -- and adds the four things Demo 13 needs on top:
integrated and bandwidth chi(2) measures, the state-character breakdown, an
explicit validity verdict, and the small set of numbers handed to Ax.

Three rules from Section 22 are enforced here rather than left to convention:

* a **mechanical** failure (solver crash, missing output) is never given an
  objective value, so it can only be reported to Ax as a failed trial;
* a **physically computed but invalid** design keeps every metric it produced
  and is rejected through explicit constraints, so the optimizer sees why;
* a **valid design whose chi(2) is genuinely near zero** is a real observation
  with objective ~0, and stays distinguishable from both of the above.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import chi2 as chi2mod  # noqa: E402
from demo_workflow import DemoError  # noqa: E402

import design13  # noqa: E402
import feasibility13  # noqa: E402

#: How a trial ended, from Demo 13's point of view.
#:
#: These five are exhaustive and mutually exclusive. The distinction that
#: matters most is between the middle two: a design that ran and is unusable is
#: a *result*, and a run that never produced a number is not.
#:
#: ``valid``                 every configured check passed.
#: ``valid_with_warning``    ran, usable, but a warn-policy check flagged it.
#: ``scientifically_invalid`` ran and produced metrics, but fails a check whose
#:                           policy rejects it. Metrics are kept.
#: ``mechanically_failed``   solver crashed or output missing. No objective.
#: ``not_evaluated``         never executed on this machine.
OUTCOME_VALID = "valid"
OUTCOME_VALID_WITH_WARNING = "valid_with_warning"
OUTCOME_INVALID = "scientifically_invalid"
OUTCOME_MECHANICAL_FAILURE = "mechanically_failed"
OUTCOME_NOT_RUN = "not_evaluated"

TRIAL_OUTCOME_CLASSES: tuple[str, ...] = (
    OUTCOME_VALID,
    OUTCOME_VALID_WITH_WARNING,
    OUTCOME_INVALID,
    OUTCOME_MECHANICAL_FAILURE,
    OUTCOME_NOT_RUN,
)

#: What ``physical_qc.bound_state_policy`` does with a bound-state QC failure.
#:
#: ``warn``       trial stays usable and is reported as valid_with_warning. The
#:                warning is never presented as a clean pass.
#: ``constraint`` leave the verdict to the continuous boundary-probability
#:                constraint, which Ax already models.
#: ``reject``     scientifically_invalid: metrics kept, excluded from ranking,
#:                and the Ax trial is abandoned so the surrogate is not taught
#:                that this region scores well.
#: ``fail_trial`` treated as a mechanical failure: no objective given to Ax.
BOUND_STATE_POLICIES: tuple[str, ...] = ("warn", "constraint", "reject", "fail_trial")

#: Region roles of the Demo 12 layer stack, mapped onto the physical names the
#: Demo 13 tables use. ``left_well`` is grown first and is the wide well for the
#: positive asymmetries this demo searches over.
WIDE_WELL_REGION = "left_well"
NARROW_WELL_REGION = "right_well"
CENTRAL_BARRIER_REGION = "centre_barrier"
OUTER_BARRIER_REGIONS = ("left_outer_barrier", "right_outer_barrier")


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


# ---------------------------------------------------------------------------
# nonlinear-optical measures beyond the ones Demo 11 already reports
# ---------------------------------------------------------------------------


def read_chi2_spectrum(extracted_dir: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Load ``chi2_focused.csv`` written by Demo 11's ``analyse_case``."""

    path = Path(extracted_dir) / "chi2_focused.csv"
    if not path.is_file():
        return None
    wavelengths: list[float] = []
    magnitudes: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            wavelength = _finite(row.get("wavelength_nm"))
            magnitude = _finite(row.get("chi2_magnitude"))
            if wavelength is not None and magnitude is not None:
                wavelengths.append(wavelength)
                magnitudes.append(magnitude)
    if len(wavelengths) < 2:
        return None
    order = np.argsort(np.asarray(wavelengths))
    return np.asarray(wavelengths)[order], np.asarray(magnitudes)[order]


def spectrum_measures(
    wavelength_nm: Sequence[float],
    magnitude: Sequence[float],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    """Integrated response and above-threshold bandwidth over a configured band.

    The bandwidth is the total wavelength measure above a fraction of the
    maximum, computed from the raw samples.  It is a *measure*, not a fitted
    linewidth: a double-peaked spectrum contributes both peaks, which is the
    honest answer for a structure with two resonances in the window.
    """

    chi2_cfg = cfg.get("chi2") or {}
    window = [float(value) for value in chi2_cfg.get("integrated_wavelength_nm", (1400.0, 1800.0))]
    fraction = float(chi2_cfg.get("bandwidth_fraction_of_peak", 0.5))
    lam = np.asarray(wavelength_nm, dtype=float)
    values = np.abs(np.asarray(magnitude, dtype=float))
    inside = (lam >= min(window)) & (lam <= max(window))
    record: dict[str, Any] = {
        "integrated_wavelength_window_nm": f"{min(window):g}-{max(window):g}",
        "bandwidth_fraction_of_peak": fraction,
    }
    if inside.sum() < 2:
        record.update(
            {"relative_integrated_chi2_abs": None, "bandwidth_above_fraction_nm": None}
        )
        return record
    record["relative_integrated_chi2_abs"] = float(
        np.trapezoid(values[inside], lam[inside])
    )
    peak = float(np.max(values[inside]))
    if peak <= 0:
        record["bandwidth_above_fraction_nm"] = 0.0
        return record
    above = values[inside] >= fraction * peak
    spacing = np.gradient(lam[inside])
    record["bandwidth_above_fraction_nm"] = float(np.sum(spacing[above]))
    return record


# ---------------------------------------------------------------------------
# electronic structure and state character
# ---------------------------------------------------------------------------


def _energy_list(observables: Mapping[str, Any], key: str) -> list[float]:
    values = observables.get(key)
    if not isinstance(values, (list, tuple)):
        return []
    return [float(value) for value in values if _finite(value) is not None]


def electronic_structure(observables: Mapping[str, Any]) -> dict[str, Any]:
    """Energies, gaps and matrix elements, plus the derived quantities.

    ``anticrossing_gap_meV`` is the smallest adjacent-level spacing among the
    tracked electron states.  Near an avoided crossing that spacing is the
    physically meaningful gap; away from one it is simply the tunnel splitting,
    and reporting the same number in both regimes is what makes a crossing
    visible in a table instead of a surprise in a plot.
    """

    electrons = _energy_list(observables, "electron_energies_eV")
    holes = _energy_list(observables, "heavy_hole_energies_eV")
    record: dict[str, Any] = {
        "electron_energies_eV": electrons,
        "heavy_hole_energies_eV": holes,
        "E_e1_eV": _finite(observables.get("E_e1_eV")),
        "E_e2_eV": _finite(observables.get("E_e2_eV")),
        "E_hh1_eV": _finite(observables.get("E_hh1_eV")),
        "E_hh2_eV": _finite(observables.get("E_hh2_eV")),
        "transition_e1_hh1_eV": _finite(observables.get("transition_e1_hh1_eV")),
        "transition_e2_hh2_eV": _finite(observables.get("transition_e2_hh2_eV")),
        "overlap_e1_hh1": _finite(observables.get("overlap_e1_hh1")),
        "overlap_e2_hh2": _finite(observables.get("overlap_e2_hh2")),
        "z_e1_e1_nm": _finite(observables.get("z_e1_e1_nm")),
        "z_e1_e2_nm": _finite(observables.get("z_e1_e2_nm")),
        "z_e2_e2_nm": _finite(observables.get("z_e2_e2_nm")),
        "z_hh1_hh1_nm": _finite(observables.get("z_hh1_hh1_nm")),
        "z_hh1_hh2_nm": _finite(observables.get("z_hh1_hh2_nm")),
        "z_hh2_hh2_nm": _finite(observables.get("z_hh2_hh2_nm")),
        "electron_hole_centroid_separation_nm": _finite(
            observables.get("electron_hole_centroid_separation_nm")
        ),
    }
    gaps = [
        (electrons[index + 1] - electrons[index]) * 1000.0
        for index in range(len(electrons) - 1)
    ]
    record["electron_level_gaps_meV"] = gaps
    record["anticrossing_gap_meV"] = min(gaps) if gaps else None
    hole_gaps = [
        (holes[index + 1] - holes[index]) * 1000.0 for index in range(len(holes) - 1)
    ]
    record["heavy_hole_level_gaps_meV"] = hole_gaps
    record["heavy_hole_anticrossing_gap_meV"] = min(hole_gaps) if hole_gaps else None

    # Intersubband e1->e2 dipole and oscillator strength. Both follow directly
    # from quantities Demo 11 already extracted; the interband transition dipole
    # is NOT reported, because in this one-band envelope model it needs a bulk
    # Kane matrix element the calculation never sets, and a relative chi(2)
    # cannot supply it.
    z12 = record["z_e1_e2_nm"]
    e1, e2 = record["E_e1_eV"], record["E_e2_eV"]
    record["intersubband_dipole_e1_e2_e_nm"] = None if z12 is None else abs(z12)
    if z12 is not None and e1 is not None and e2 is not None:
        delta_j = abs(e2 - e1) * chi2mod.ELEMENTARY_CHARGE_C
        z_m = abs(z12) * 1e-9
        record["intersubband_oscillator_strength_e1_e2"] = float(
            2.0 * chi2mod.ELECTRON_MASS_KG * delta_j * z_m**2 / chi2mod.REDUCED_PLANCK_J_S**2
        )
    else:
        record["intersubband_oscillator_strength_e1_e2"] = None
    record["oscillator_strength_definition"] = (
        "f = 2 m0 dE z^2 / hbar^2 for the intersubband e1->e2 transition, using the "
        "free-electron mass; interband dipoles are not reported because this "
        "one-band relative model does not set the bulk Kane matrix element"
    )
    return record


def state_character(
    observables: Mapping[str, Any], extracted_dir: Path | None
) -> dict[str, Any]:
    """Where each state lives, and how much of it sits on the domain boundary."""

    record: dict[str, Any] = {
        "wide_well_probability": _finite(
            observables.get("electron1_thick_well_probability")
        ),
        "narrow_well_probability": _finite(
            observables.get("electron1_thin_well_probability")
        ),
        "electron2_wide_well_probability": _finite(
            observables.get("electron2_thick_well_probability")
        ),
        "electron2_narrow_well_probability": _finite(
            observables.get("electron2_thin_well_probability")
        ),
        "central_barrier_probability": None,
        "outer_barrier_probability": None,
        "left_boundary_probability": _finite(
            observables.get("maximum_left_boundary_probability")
        ),
        "right_boundary_probability": _finite(
            observables.get("maximum_right_boundary_probability")
        ),
        "maximum_boundary_probability": _finite(
            observables.get("maximum_boundary_probability_bound_states")
        ),
    }
    left = record["left_boundary_probability"] or 0.0
    right = record["right_boundary_probability"] or 0.0
    record["total_boundary_probability"] = float(left + right)

    # Barrier occupancy is per state and only exists in the extracted state
    # table; the ground state's values are the ones the chi(2) sum is most
    # sensitive to, so they are the ones promoted into the summary row.
    rows = _read_state_rows(extracted_dir)
    if rows:
        ground = rows[0]
        record["central_barrier_probability"] = _finite(
            ground.get(f"probability_{CENTRAL_BARRIER_REGION}")
        )
        outer = [
            _finite(ground.get(f"probability_{name}")) for name in OUTER_BARRIER_REGIONS
        ]
        present = [value for value in outer if value is not None]
        record["outer_barrier_probability"] = float(sum(present)) if present else None
        record["raw_solver_state_index"] = _finite(ground.get("state"))
        record["extracted_state_rows"] = len(rows)
        record["all_states_normalized"] = all(
            str(row.get("normalised")).lower() in {"true", "1"} for row in rows
        )
        record["bound_state_count"] = sum(
            1 for row in rows if str(row.get("bound")).lower() in {"true", "1"}
        )
    else:
        record.update(
            {
                "raw_solver_state_index": None,
                "extracted_state_rows": 0,
                "all_states_normalized": None,
                "bound_state_count": None,
            }
        )
    return record


def _read_state_rows(extracted_dir: Path | None) -> list[dict[str, Any]]:
    if extracted_dir is None:
        return []
    path = Path(extracted_dir) / "electron_states.csv"
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------
# numerical quality and the validity verdict
# ---------------------------------------------------------------------------


def numerical_quality(
    observables: Mapping[str, Any],
    validation: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    """Every numerical check, plus the three 0/1 flags Ax constrains on."""

    analysis_cfg = cfg.get("analysis") or {}
    numerical_cfg = cfg.get("numerical") or {}
    orthonormality = max(
        _finite(observables.get("orthonormality_error_electron")) or 0.0,
        _finite(observables.get("orthonormality_error_heavy_hole")) or 0.0,
    )
    requested_states = int(numerical_cfg.get("number_of_electron_states", 0))
    extracted_states = len(_energy_list(observables, "electron_energies_eV"))
    record: dict[str, Any] = {
        "solver_completed": bool(validation.get("job_done_file_present", False)),
        "expected_outputs_available": bool(
            validation.get("no_stale_job_running_file", False)
        ),
        "normalization_valid": bool(validation.get("probability_normalized", False)),
        "orthonormality_error": float(orthonormality),
        "orthonormality_tolerance": float(
            analysis_cfg.get("orthonormality_tolerance", 1e-3)
        ),
        "envelopes_orthonormal": bool(validation.get("envelopes_orthonormal", False)),
        "origin_independence_absolute_residual": _finite(
            observables.get("absolute_residual")
        ),
        "origin_independence_relative_residual": _finite(
            observables.get("relative_residual")
        ),
        "origin_independence_comparison_mode": observables.get(
            "origin_independence_comparison_mode"
        ),
        "origin_independence_error": _finite(observables.get("origin_independence_error")),
        "origin_independence_valid": int(
            bool(validation.get("chi2_origin_independent", False))
        ),
        "bound_states_ok": bool(
            validation.get("bound_state_boundary_probability_small", False)
        ),
        "quasi_bound_policy": observables.get("quasi_bound_policy"),
        "states_failing_bound_criterion": _finite(
            observables.get("states_failing_bound_criterion")
        ),
        "states_failing_bound_criterion_in_chi2_sum": _finite(
            observables.get("states_failing_bound_criterion_in_chi2_sum")
        ),
        "requested_electron_states": requested_states,
        "extracted_electron_states": extracted_states,
        "chi2_max_states_per_band": _finite(observables.get("chi2_max_states_per_band")),
        "chi2_electron_states_used": _finite(observables.get("chi2_electron_states_used")),
        "chi2_heavy_hole_states_used": _finite(
            observables.get("chi2_heavy_hole_states_used")
        ),
        "chi2_triple_sum_terms_evaluated": _finite(
            observables.get("chi2_triple_sum_terms_evaluated")
        ),
        "chi2_triple_sum_terms_significant": _finite(
            observables.get("chi2_triple_sum_terms_significant")
        ),
        "solver_states_not_reaching_the_sum": _finite(
            observables.get("solver_states_not_reaching_the_sum")
        ),
        "chi2_state_window_as_configured": bool(
            validation.get("chi2_state_window_as_configured", False)
        ),
    }
    record["required_states_valid"] = int(
        extracted_states >= requested_states
        and bool(record["chi2_state_window_as_configured"])
    )
    # "The solver exited zero" is not a scientific verdict. Physical validity is
    # the conjunction of the checks Demo 11 already performs, evaluated here so
    # the reason a design was rejected is a named test and not a mood.
    physical_tests = {
        "envelopes_orthonormal": bool(record["envelopes_orthonormal"]),
        "probability_normalized": bool(record["normalization_valid"]),
        "electron_energies_ordered": bool(
            validation.get("electron_energies_ordered", False)
        ),
        "two_bound_electron_states": bool(
            validation.get("two_bound_electron_states", False)
        ),
        "bound_state_boundary_probability_small": bool(record["bound_states_ok"]),
        "chi2_states_pass_bound_criterion": bool(
            validation.get("chi2_states_pass_bound_criterion", False)
        ),
        "chi2_origin_independent": bool(record["origin_independence_valid"]),
        "chi2_state_window_as_configured": bool(record["chi2_state_window_as_configured"]),
    }
    failed = sorted(name for name, passed in physical_tests.items() if not passed)
    record["physical_qc_tests"] = physical_tests
    record["physical_qc_failed_tests"] = failed
    record["physical_qc_valid"] = int(not failed)
    return record


# ---------------------------------------------------------------------------
# the assembled record
# ---------------------------------------------------------------------------


def build_record(
    *,
    parameters: Mapping[str, Any],
    cfg: Mapping[str, Any],
    observables: Mapping[str, Any],
    validation: Mapping[str, Any],
    status: str,
    failure_reason: str | None = None,
    extracted_dir: Path | None = None,
    tracking: Mapping[str, Any] | None = None,
    runtime_seconds: float = 0.0,
) -> dict[str, Any]:
    """Assemble one trial's complete record from Demo 11's observables."""

    canonical = design13.canonicalize(parameters, cfg)
    target = float((cfg.get("chi2") or {}).get("reference_wavelength_nm", 1550.0))
    record: dict[str, Any] = {
        **{f"parameter_{name}": value for name, value in canonical.items()},
        "target_wavelength_nm": target,
        "runtime_seconds": float(runtime_seconds),
        "failure_reason": failure_reason,
    }

    if status != "completed":
        record.update(
            {
                "trial_outcome_class": (
                    OUTCOME_MECHANICAL_FAILURE
                    if status == "failed"
                    else OUTCOME_NOT_RUN
                ),
                "trial_valid": False,
                "objective_available": False,
                "rejection_reason": failure_reason
                or (
                    "no licensed nextnano++ solver on this machine; the input was "
                    "generated and the trial is pending, not failed"
                ),
                "solver_completed": False,
                "expected_outputs_available": False,
            }
        )
        return record

    peak = _finite(observables.get("chi2_peak_magnitude"))
    peak_wavelength = _finite(observables.get("chi2_peak_wavelength_nm"))
    at_target = _finite(observables.get("chi2_relative_at_reference"))
    # Signed and absolute detuning are separate metrics with separate jobs. The
    # signed value says which side of the target a resonance sits on and is
    # reported everywhere; the absolute value is how far away it is and is the
    # only one a "within N nm of target" constraint may ever bind.
    signed_detuning = None if peak_wavelength is None else float(peak_wavelength - target)
    record.update(
        {
            "chi2_mode": observables.get("chi2_mode"),
            "relative_chi2_units": observables.get("chi2_units"),
            "relative_peak_chi2_abs": None if peak is None else abs(peak),
            "peak_wavelength_nm": peak_wavelength,
            "relative_chi2_at_target_wavelength_abs": (
                None if at_target is None else abs(at_target)
            ),
            "signed_detuning_nm": signed_detuning,
            "absolute_detuning_nm": None if signed_detuning is None else abs(signed_detuning),
            "detuning_side": (
                None
                if signed_detuning is None
                else ("on_target" if signed_detuning == 0 else
                      "red_of_target" if signed_detuning < 0 else "blue_of_target")
            ),
        }
    )

    spectrum = read_chi2_spectrum(extracted_dir) if extracted_dir else None
    if spectrum is not None:
        record.update(spectrum_measures(spectrum[0], spectrum[1], cfg))
    else:
        record.update(
            {
                "relative_integrated_chi2_abs": None,
                "bandwidth_above_fraction_nm": None,
                "integrated_wavelength_window_nm": None,
                "bandwidth_fraction_of_peak": None,
            }
        )

    record.update(electronic_structure(observables))
    record.update(state_character(observables, extracted_dir))
    record.update(numerical_quality(observables, validation, cfg))

    tracking_record = dict(tracking or {})
    record.update(
        {
            "state_tracking_confidence": _finite(
                tracking_record.get("state_tracking_confidence")
            ),
            "state_tracking_margin": _finite(tracking_record.get("assignment_margin")),
            "tracked_state_labels": tracking_record.get("tracked_labels"),
            "raw_state_indices": tracking_record.get("raw_indices"),
            "state_tracking_ambiguous": bool(tracking_record.get("ambiguous", False)),
            "state_tracking_reference_trial": tracking_record.get("reference_trial"),
            "state_tracking_method": tracking_record.get("method"),
        }
    )

    # Every configured constraint is evaluated here, whether or not Ax was told
    # about it. `trial_valid` therefore means the same thing as full physical
    # feasibility, while `feasible_under_ax_constraints` records the narrower
    # question the optimizer was actually asked. The first licensed run showed
    # why both are needed: Ax was enforcing a detuning bound this record never
    # checked, so an Ax-excluded design sat at the top of the ranked table.
    specs = feasibility13.build_constraints(cfg)
    rejections: list[str] = []
    ax_rejections: list[str] = []
    for spec in specs:
        if spec.satisfied_by(record.get(spec.metric)) is False:
            rejections.append(spec.name)
            if spec.enforcement == feasibility13.ENFORCEMENT_AX:
                ax_rejections.append(spec.name)
    if record.get("state_tracking_ambiguous"):
        rejections.append("state_tracking_ambiguous")

    # The bound-state policy decides what a boundary-probability QC failure
    # means, rather than that meaning being implicit in the code path taken.
    policy = str(
        (cfg.get("physical_qc") or {}).get("bound_state_policy", "warn")
    )
    if policy not in BOUND_STATE_POLICIES:
        raise DemoError(
            f"physical_qc.bound_state_policy must be one of {list(BOUND_STATE_POLICIES)}, "
            f"got {policy!r}"
        )
    bound_state_failed = "bound_state_boundary_probability_small" in set(
        record.get("physical_qc_failed_tests") or ()
    )
    warnings_raised: list[str] = []
    if bound_state_failed:
        if policy == "warn":
            warnings_raised.append("bound_state_boundary_probability_small")
            # A warn-policy failure must not masquerade as a clean pass, so the
            # named test stays visible in physical_qc_failed_tests and the trial
            # is reported as valid_with_warning rather than valid.
            rejections = [name for name in rejections if name != "require_physical_qc"]
        elif policy == "constraint":
            # Defer entirely to the continuous boundary-probability constraint,
            # which Ax already models and which is the same physics.
            rejections = [name for name in rejections if name != "require_physical_qc"]
        elif policy in {"reject", "fail_trial"} and "require_physical_qc" not in rejections:
            rejections.append("require_physical_qc")

    record["bound_state_policy"] = policy
    record["qc_warnings"] = warnings_raised
    record["constraint_violations"] = rejections
    record["ax_constraint_violations"] = ax_rejections
    record["trial_valid"] = not rejections
    record["feasible_under_ax_constraints"] = not ax_rejections
    record["objective_available"] = (
        record["relative_chi2_at_target_wavelength_abs"] is not None
        and not (bound_state_failed and policy == "fail_trial")
    )
    if bound_state_failed and policy == "fail_trial":
        record["trial_outcome_class"] = OUTCOME_MECHANICAL_FAILURE
        record["failure_reason"] = (
            "physical_qc.bound_state_policy is 'fail_trial' and the bound-state "
            "boundary-probability check failed"
        )
    elif rejections:
        record["trial_outcome_class"] = OUTCOME_INVALID
    elif warnings_raised:
        record["trial_outcome_class"] = OUTCOME_VALID_WITH_WARNING
    else:
        record["trial_outcome_class"] = OUTCOME_VALID
    record["rejection_reason"] = "; ".join(rejections)
    record["warning_reason"] = "; ".join(warnings_raised)
    # A genuinely symmetric or off-resonant structure is a real, valid
    # observation with a near-zero response. Naming that case explicitly is what
    # keeps it from being read as a failure later.
    record["valid_low_response"] = bool(
        not rejections
        and record["relative_chi2_at_target_wavelength_abs"] is not None
        and record["relative_chi2_at_target_wavelength_abs"] < 1e-12
    )
    return record


def ax_raw_data(
    record: Mapping[str, Any], metric_names: Sequence[str]
) -> dict[str, float] | None:
    """The numbers handed to Ax, or ``None`` when the trial must be failed.

    Ax only ever sees metrics that its objective or its outcome constraints name.
    Returning ``None`` is the signal that this trial has no defensible objective
    at all and must be reported through ``mark_trial_failed``.
    """

    if not record.get("objective_available", False):
        return None
    data: dict[str, float] = {}
    for name in metric_names:
        value = _finite(record.get(name))
        if value is None:
            # A constraint metric that could not be measured cannot be silently
            # replaced by a permissive default; the trial is not completable.
            return None
        data[name] = value
    return data
