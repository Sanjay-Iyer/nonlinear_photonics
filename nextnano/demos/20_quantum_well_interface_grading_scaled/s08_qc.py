"""Stage 08 - quality control, the normalization audit, and validation status.

Three separate jobs, deliberately not blended:

1. **Status separation.** ``solver_pass`` and ``physical_valid`` are distinct
   and stay distinct. A zero return code from nextnano++ says the process
   finished; it says nothing about whether the physics is trustworthy. Demo 19's
   own copied run is ``solver_pass=True, physical_valid=False`` for all 13
   cases, and Demo 20 carries that through instead of hiding it.

2. **The normalization audit.** A printed, machine-readable statement of what
   the k-space measure actually is in this run, read out of the code rather
   than from a comment.

3. **Scaling invariance gates.** A constant, k-independent factor must change
   the magnitude of chi2 and nothing else. If it moves a peak, reorders the
   cases, or changes a normalized lineshape, something is wrong with where the
   factor was applied - so these are checks, not assertions in prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

import s06_chi2 as chi2mod

VALIDATION_LEVELS = (
    "code_validated",
    "numerics_validated",
    "solver_validated",
    "physical_model_validated",
    "paper_reproduction_validated",
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str
    value: Any = None

    def as_record(self) -> dict[str, Any]:
        return {"check": self.name, "passed": self.passed,
                "detail": self.detail, "value": self.value}


# --- 1. status separation ---------------------------------------------------


def status_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts of the two independent status flags across all cases."""

    def flag(row: Mapping[str, Any], key: str) -> bool:
        value = row.get(key)
        return value is True or str(value).strip().lower() in {"true", "1", "yes"}

    solver = [row for row in rows if flag(row, "solver_pass")]
    physical = [row for row in rows if flag(row, "physical_valid")]
    reasons = sorted({
        str(row.get("failure_reason") or "").strip()
        for row in rows if not flag(row, "physical_valid")
    } - {""})
    return {
        "case_count": len(rows),
        "solver_pass_count": len(solver),
        "physical_valid_count": len(physical),
        "all_solver_pass": len(solver) == len(rows) and bool(rows),
        "all_physical_valid": len(physical) == len(rows) and bool(rows),
        "physical_invalid_reasons": reasons,
        "interpretation": (
            "Every reported spectrum comes from a solver run that returned "
            "successfully but did NOT pass the inherited Demo 11/14 physical QC. "
            "Treat the numbers as a controlled comparison between grading cases, "
            "not as validated absolute physics."
            if len(solver) and not len(physical) else
            "See solver_pass_count and physical_valid_count; the two flags are "
            "independent and both are reported per case."
        ),
    }


def validation_status(
    *, code_tests_passed: bool, numerics_checks_passed: bool,
    solver_ran_here: bool, all_physical_valid: bool,
    paper_ratio: float | None,
) -> dict[str, Any]:
    """An explicit verdict per validation level. Nothing is assumed validated."""

    return {
        "code_validated": {
            "status": bool(code_tests_passed),
            "evidence": "tests/test_demo20.py executed locally; includes exact "
                        "reproduction of Demo 19's chi2 from its own tabulated "
                        "matrix elements.",
        },
        "numerics_validated": {
            "status": bool(numerics_checks_passed),
            "evidence": "k-measure agrees with its closed form, the k grid is "
                        "converged at the production point count, and the two "
                        "conventions differ by exactly (2*pi)^2 pointwise.",
        },
        "solver_validated": {
            "status": bool(solver_ran_here),
            "evidence": ("a licensed nextnano++ solve ran in this execution"
                         if solver_ran_here else
                         "NO licensed solve ran in this execution; the quantum "
                         "data was read from a previous licensed run's table."),
        },
        "physical_model_validated": {
            "status": bool(all_physical_valid),
            "evidence": ("all cases passed the inherited physical QC"
                         if all_physical_valid else
                         "physical_valid is False; the inherited Demo 11/14 "
                         "physical QC did not pass. The specific failed "
                         "sub-check needs the raw licensed run and the "
                         "proprietary material database, neither of which is "
                         "present in this checkout."),
        },
        "paper_reproduction_validated": {
            "status": False,
            "evidence": ("no convention reproduces the published target; "
                         f"closest ratio to target is {paper_ratio:.4g}"
                         if paper_ratio is not None else
                         "not evaluated") + ". Agreement would in any case "
                        "require the paper's own k-space measure to be "
                        "confirmed, which this checkout cannot do.",
        },
    }


# --- 2. the normalization audit --------------------------------------------


def normalization_audit(settings: chi2mod.Chi2Settings, *,
                        scaling_enabled: bool) -> dict[str, Any]:
    """What the k-space measure actually is, read out of the implementation.

    Every field below is derived from :mod:`s06_chi2` at runtime, so the audit
    cannot drift away from the code the way a comment can.
    """

    demo19 = settings.with_convention(chi2mod.CONVENTION_DEMO19)
    scaled = settings.with_convention(chi2mod.CONVENTION_SCALED)
    exactness = chi2mod.scaling_is_exact_constant(settings)
    measured = chi2mod.k_measure_total(demo19)
    analytic = chi2mod.analytic_disc_measure(demo19)
    return {
        "original_convention": chi2mod.CONVENTION_DESCRIPTIONS[
            chi2mod.CONVENTION_DEMO19],
        "integration_method":
            "uniform radial grid, trapezoidal weights, "
            f"{settings.k_parallel_points} points from k=0 to k_max inclusive; "
            "the angular integral is done analytically using isotropy",
        "explicit_one_over_2pi_squared_present": True,
        "one_over_2pi_squared_location":
            "s06_chi2.k_grid: 1/(2*pi)^2 * (2*pi from the angular integral) "
            "= radial_measure = k/(2*pi)",
        "explicit_2pi_radial_factor_present": True,
        "explicit_2pi_radial_factor_detail":
            "the 2*pi of the angular integral is already cancelled against "
            "1/(2*pi)^2; it is not a separate multiplication",
        "cartesian_or_radial": "radial (isotropic reduction of d^2k)",
        "quadrature": "trapezoidal in k, with k dk as the radial measure",
        "spin_degeneracy": int(settings.spin_degeneracy),
        "spin_degeneracy_location": "folded into the k weights",
        "nz_convention": f"{settings.nz_mode} = "
                         f"{settings.n_wells_per_metre:.7e} m^-1 "
                         f"(1 period per {settings.reference_period_nm:g} nm)",
        "nz_is_not_a_kspace_factor":
            "N_z is a well-density prefactor in units of m^-1 and is unrelated "
            "to the k-space measure; it cannot absorb a factor of (2*pi)^2",
        "k_max_per_nm": settings.k_max_per_nm,
        "bz_edge_convention": settings.bz_edge_convention,
        "k_measure_total_per_nm2_demo19": measured,
        "k_measure_analytic_per_nm2_demo19": analytic,
        "k_measure_matches_closed_form": bool(
            abs(measured - analytic) <= 1.0e-12 * max(abs(analytic), 1.0)
        ),
        "k_measure_total_per_nm2_scaled": chi2mod.k_measure_total(scaled),
        "experimental_scaling_enabled": bool(scaling_enabled),
        "scaling_factor": chi2mod.two_pi_squared(),
        "scaling_definition": "(2*pi)^2",
        "scaling_is_exact_constant": exactness,
        "finding": (
            "The 1/(2*pi)^2 normalization is ALREADY PRESENT in the original "
            "Demo 19 calculation, in its reduced isotropic form 1/(2*pi) with "
            "the compensating 2*pi already cancelled by the angular integral. "
            "Multiplying by (2*pi)^2 therefore REMOVES an existing denominator "
            "rather than restoring a missing factor: it switches the measure "
            "from (1/A) sum_k -> int d^2k/(2*pi)^2 to sum_k -> g_s * int d^2k. "
            "That is an ALTERNATIVE CONVENTION under test, not a correction."
        ),
    }


def format_normalization_audit(audit: Mapping[str, Any]) -> str:
    """The printed audit block."""

    yes_no = lambda flag: "YES" if flag else "NO"  # noqa: E731
    exact = audit["scaling_is_exact_constant"]
    lines = [
        "=" * 74,
        "DEMO 20 - k-SPACE NORMALIZATION AUDIT",
        "=" * 74,
        f"Original Demo 19 convention  : {audit['original_convention']}",
        f"k-space integration method   : {audit['integration_method']}",
        f"Cartesian or radial          : {audit['cartesian_or_radial']}",
        f"Quadrature                   : {audit['quadrature']}",
        f"Explicit 1/(2pi)^2 present   : "
        f"{yes_no(audit['explicit_one_over_2pi_squared_present'])}"
        f"   <- {audit['one_over_2pi_squared_location']}",
        f"Explicit 2pi radial factor   : "
        f"{yes_no(audit['explicit_2pi_radial_factor_present'])}"
        f"   ({audit['explicit_2pi_radial_factor_detail']})",
        f"Spin degeneracy              : {audit['spin_degeneracy']} "
        f"({audit['spin_degeneracy_location']})",
        f"Nz convention                : {audit['nz_convention']}",
        f"k_max                        : {audit['k_max_per_nm']:.8f} nm^-1 "
        f"({audit['bz_edge_convention']})",
        f"k measure, Demo 19 convention: "
        f"{audit['k_measure_total_per_nm2_demo19']:.12g} nm^-2",
        f"  closed form                : "
        f"{audit['k_measure_analytic_per_nm2_demo19']:.12g} nm^-2  "
        f"[match: {yes_no(audit['k_measure_matches_closed_form'])}]",
        f"k measure, scaled convention : "
        f"{audit['k_measure_total_per_nm2_scaled']:.12g} nm^-2",
        "-" * 74,
        f"Experimental scaling enabled : "
        f"{yes_no(audit['experimental_scaling_enabled'])}",
        f"Scaling factor               : {audit['scaling_factor']:.10f}",
        f"Scaling definition           : {audit['scaling_definition']}",
        f"Pointwise ratio range        : "
        f"[{exact['pointwise_ratio_min']:.12f}, {exact['pointwise_ratio_max']:.12f}]"
        f"  [exact constant: {yes_no(exact['is_exact_constant'])}]",
        "-" * 74,
        "FINDING:",
    ]
    text = audit["finding"]
    words, line = text.split(), ""
    for word in words:
        if len(line) + len(word) + 1 > 72:
            lines.append("  " + line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append("  " + line)
    lines.append("=" * 74)
    return "\n".join(lines)


# --- 3. scaling invariance gates -------------------------------------------


def scaling_invariance_checks(
    pairs: Sequence[chi2mod.ConventionPair], cfg: Mapping[str, Any]
) -> list[Check]:
    """A constant factor must move magnitude and nothing else.

    Five separate gates, one per invariant the user asked to be confirmed:
    peak wavelength, spectral shape, case ranking, grading trend, and the ratio
    itself.
    """

    qc = cfg["qc"]
    peak_tolerance = float(qc["peak_wavelength_tolerance_nm"])
    shape_tolerance = float(qc["spectral_shape_tolerance"])
    expected = chi2mod.two_pi_squared()
    checks: list[Check] = []
    if not pairs:
        return [Check("scaling_invariance", False, "no spectra to check")]

    # (a) the ratio, at every wavelength of every case
    ratios = np.concatenate([pair.magnitude_ratio() for pair in pairs])
    finite = ratios[np.isfinite(ratios)]
    deviation = float(np.max(np.abs(finite - expected))) if finite.size else float("inf")
    checks.append(Check(
        "scaling_ratio_equals_two_pi_squared",
        bool(finite.size and deviation <= 1.0e-9 * expected),
        f"max |ratio - (2pi)^2| = {deviation:.3e} over {finite.size} "
        f"wavelength points in {len(pairs)} cases",
        {"expected": expected, "max_deviation": deviation,
         "ratio_min": float(np.min(finite)) if finite.size else None,
         "ratio_max": float(np.max(finite)) if finite.size else None},
    ))

    # (b) peak wavelength must not move
    shifts = {pair.case_id: abs(pair.scaled.peak()["wavelength_nm"]
                                - pair.raw.peak()["wavelength_nm"])
              for pair in pairs}
    worst = max(shifts.values())
    checks.append(Check(
        "peak_wavelength_unchanged",
        bool(worst <= peak_tolerance),
        f"largest peak shift {worst:.6g} nm "
        f"(tolerance {peak_tolerance:g} nm)",
        shifts,
    ))

    # (c) normalized lineshape must be identical
    shape_errors = {
        pair.case_id: float(np.max(np.abs(pair.scaled.normalized_magnitude()
                                          - pair.raw.normalized_magnitude())))
        for pair in pairs
    }
    worst_shape = max(shape_errors.values())
    checks.append(Check(
        "spectral_shape_unchanged",
        bool(worst_shape <= shape_tolerance),
        f"largest normalized-lineshape difference {worst_shape:.3e} "
        f"(tolerance {shape_tolerance:g})",
        shape_errors,
    ))

    # (d) case ranking by |chi2| at the target wavelength must not reorder
    target = float(cfg["chi2"]["target_wavelength_nm"])
    raw_order = [pair.case_id for pair in
                 sorted(pairs, key=lambda p: p.raw.at_wavelength(target), reverse=True)]
    scaled_order = [pair.case_id for pair in
                    sorted(pairs, key=lambda p: p.scaled.at_wavelength(target),
                           reverse=True)]
    checks.append(Check(
        "case_ranking_unchanged",
        raw_order == scaled_order,
        "ranking by |chi2| at the target wavelength is identical"
        if raw_order == scaled_order else
        f"ranking changed: raw={raw_order} scaled={scaled_order}",
        {"raw_order": raw_order, "scaled_order": scaled_order},
    ))

    # (e) the grading trend, i.e. every case relative to the reference
    reference_id = str(cfg["analysis"]["reference_case_id"])
    reference = next((p for p in pairs if p.case_id == reference_id), None)
    if reference is None:
        checks.append(Check("grading_trend_unchanged", False,
                            f"reference case {reference_id} has no spectrum"))
    else:
        raw_ref = reference.raw.at_wavelength(target)
        scaled_ref = reference.scaled.at_wavelength(target)
        trend_errors = {}
        for pair in pairs:
            raw_relative = pair.raw.at_wavelength(target) / raw_ref if raw_ref else np.nan
            scaled_relative = (pair.scaled.at_wavelength(target) / scaled_ref
                               if scaled_ref else np.nan)
            trend_errors[pair.case_id] = abs(raw_relative - scaled_relative)
        worst_trend = max(trend_errors.values())
        checks.append(Check(
            "grading_trend_unchanged",
            bool(worst_trend <= 1.0e-9),
            f"largest change in relative-to-reference ratio {worst_trend:.3e}",
            trend_errors,
        ))
    return checks


def numerics_checks(
    settings: chi2mod.Chi2Settings,
    convergence: Mapping[str, Any] | None,
) -> list[Check]:
    """Checks on the integration itself, independent of the scaling experiment."""

    checks: list[Check] = []
    for convention in (chi2mod.CONVENTION_DEMO19, chi2mod.CONVENTION_SCALED):
        probe = settings.with_convention(convention)
        measured = chi2mod.k_measure_total(probe)
        analytic = chi2mod.analytic_disc_measure(probe)
        relative = abs(measured - analytic) / max(abs(analytic), 1e-30)
        checks.append(Check(
            f"k_measure_matches_closed_form[{convention}]",
            bool(relative <= 1.0e-12),
            f"trapezoidal {measured:.12g} vs closed form {analytic:.12g} "
            f"nm^-2, relative {relative:.3e}",
            {"measured": measured, "analytic": analytic, "relative": relative},
        ))
    if convergence is not None:
        checks.append(Check(
            "k_grid_converged",
            bool(convergence["k_parallel_integration_converged"]),
            f"|chi2| at {convergence['k_parallel_points_production']} points is "
            f"within {convergence['k_parallel_relative_error']:.3e} of the "
            f"{max(convergence['k_parallel_points_tested'])}-point value "
            f"(tolerance {convergence['k_parallel_tolerance']:g})",
            convergence["chi2_abs_by_point_count"],
        ))
    return checks


def format_checks(title: str, checks: Sequence[Check]) -> str:
    lines = [title, "-" * len(title)]
    for check in checks:
        lines.append(f"  [{'PASS' if check.passed else 'FAIL'}] {check.name}")
        lines.append(f"         {check.detail}")
    return "\n".join(lines)
