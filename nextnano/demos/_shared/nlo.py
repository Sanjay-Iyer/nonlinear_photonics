"""A *relative* three-level design metric for coupled-quantum-well screening.

WHAT THIS IS NOT
================

This module does not compute chi(2).  It returns a dimensionless, arbitrarily
scaled figure of merit whose only legitimate use is *ranking* candidate
geometries produced by the same sweep with the same settings.  It must never be
reported in pm/V, compared against a measured susceptibility, or described as a
second-order nonlinear optical susceptibility.

WHY IT IS NOT chi(2)
====================

The standard resonant three-level expression for the second-order response of an
intersubband system has the structure

    chi(2) ~ (N e^3 / eps0) * z12 z23 z31
             / [ (E21 - hbar w - i G21) (E31 - 2 hbar w - i G31) ]

Reaching an absolute value in pm/V additionally requires, at minimum:

* the sheet carrier density N and how it is distributed over the subbands
  (this module deliberately takes no density argument);
* the pump photon energy hbar w, since the denominators are frequency dependent;
  the metric here evaluates a photon-energy-independent proxy instead;
* dephasing rates G_ij, which nextnano++ does not supply and which dominate the
  on-resonance magnitude;
* the population differences between the three levels at the operating
  temperature and bias;
* the local-field / effective-medium and confinement-factor treatment relating a
  microscopic polarisation to a macroscopic susceptibility;
* consistent SI unit conversion of z_ij from e*nm.

Every one of those is absent here.  What remains -- the product of the three
position matrix elements divided by an energy-detuning denominator -- captures
the *geometry-driven* part of the design problem, which is exactly what a
structure sweep can legitimately optimise.

The implementation is intentionally isolated from nextnano output parsing so it
can be unit-tested on synthetic numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

METRIC_NAME = "relative_three_level_design_metric"
METRIC_UNITS = "arbitrary relative units"
FORBIDDEN_LABELS = ("chi2", "chi(2)", "chi^(2)", "pm/V", "pm V^-1", "susceptibility")


class MetricError(ValueError):
    """Raised when the inputs cannot support even a relative comparison."""


@dataclass(frozen=True)
class ThreeLevelInputs:
    """The geometry-derived quantities the metric consumes.

    Energies are subband energies in eV; ``z_ij`` are position matrix elements
    in nm (equivalently e*nm once the electron charge is factored out, which is
    how nextnano++ reports them).
    """

    E1_eV: float
    E2_eV: float
    E3_eV: float
    z12_nm: float
    z23_nm: float
    z13_nm: float

    def spacings_meV(self) -> dict[str, float]:
        return {
            "E21_meV": 1000.0 * (self.E2_eV - self.E1_eV),
            "E32_meV": 1000.0 * (self.E3_eV - self.E2_eV),
            "E31_meV": 1000.0 * (self.E3_eV - self.E1_eV),
        }


@dataclass(frozen=True)
class MetricSettings:
    """Documented, configurable assumptions of the proxy.

    ``target_E21_meV`` is the intersubband spacing the design is being tuned
    towards; ``detuning_floor_meV`` keeps a perfectly resonant candidate from
    producing an infinite metric, which would rank numerical noise first.
    ``double_resonance`` additionally rewards E32 ~ E21 (the cascade condition
    that makes a three-level system useful for second-order mixing).
    """

    target_E21_meV: float
    detuning_floor_meV: float = 1.0
    double_resonance: bool = True
    enabled: bool = True

    def __post_init__(self) -> None:
        if not math.isfinite(self.target_E21_meV) or self.target_E21_meV <= 0:
            raise MetricError("target_E21_meV must be finite and > 0.")
        if not math.isfinite(self.detuning_floor_meV) or self.detuning_floor_meV <= 0:
            raise MetricError("detuning_floor_meV must be finite and > 0.")


@dataclass(frozen=True)
class MetricResult:
    """The metric plus every intermediate quantity that produced it."""

    name: str = METRIC_NAME
    units: str = METRIC_UNITS
    value: float | None = None
    matrix_element_product_nm3: float | None = None
    detuning_denominator_meV2: float | None = None
    spacings_meV: Mapping[str, float] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    excluded_reason: str | None = None

    @property
    def is_usable(self) -> bool:
        return self.value is not None and self.excluded_reason is None

    def as_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "metric_name": self.name,
            "metric_units": self.units,
            "relative_metric": self.value,
            "matrix_element_product_nm3": self.matrix_element_product_nm3,
            "detuning_denominator_meV2": self.detuning_denominator_meV2,
            "metric_excluded_reason": self.excluded_reason,
        }
        row.update(self.spacings_meV)
        return row


ASSUMPTIONS: tuple[str, ...] = (
    "Relative ranking only; the value has arbitrary scale and no physical units.",
    "No carrier density, no photon energy, no dephasing, no population "
    "differences, and no local-field correction enter the expression.",
    "Position matrix elements are envelope-function results for the conduction "
    "subbands only; interband and valence contributions are absent.",
    "A detuning floor prevents division by zero at exact resonance, so the "
    "on-resonance ordering is set by that floor rather than by physics.",
)


def three_level_metric(
    inputs: ThreeLevelInputs, settings: MetricSettings
) -> MetricResult:
    """Compute the relative design metric, or explain why it cannot be computed."""

    spacings = inputs.spacings_meV()
    if not settings.enabled:
        return MetricResult(
            spacings_meV=spacings,
            assumptions=ASSUMPTIONS,
            excluded_reason="metric disabled in configuration",
        )
    values = (
        inputs.E1_eV,
        inputs.E2_eV,
        inputs.E3_eV,
        inputs.z12_nm,
        inputs.z23_nm,
        inputs.z13_nm,
    )
    if any(value is None or not math.isfinite(float(value)) for value in values):
        return MetricResult(
            spacings_meV=spacings,
            assumptions=ASSUMPTIONS,
            excluded_reason="one or more energies or matrix elements are missing",
        )
    if not (inputs.E1_eV < inputs.E2_eV < inputs.E3_eV):
        return MetricResult(
            spacings_meV=spacings,
            assumptions=ASSUMPTIONS,
            excluded_reason="subband energies are not strictly ordered E1 < E2 < E3",
        )

    product = abs(float(inputs.z12_nm) * float(inputs.z23_nm) * float(inputs.z13_nm))
    detuning_21 = max(
        abs(spacings["E21_meV"] - settings.target_E21_meV), settings.detuning_floor_meV
    )
    if settings.double_resonance:
        detuning_32 = max(
            abs(spacings["E32_meV"] - spacings["E21_meV"]), settings.detuning_floor_meV
        )
    else:
        detuning_32 = 1.0
    denominator = detuning_21 * detuning_32
    return MetricResult(
        value=product / denominator,
        matrix_element_product_nm3=product,
        detuning_denominator_meV2=denominator,
        spacings_meV=spacings,
        assumptions=ASSUMPTIONS,
    )


def assert_not_labelled_as_chi2(label: str) -> None:
    """Guard used by the tests and by report writers.

    The proxy is easy to mislabel once it is a column in a ranked table, so the
    rename is blocked mechanically rather than by convention.
    """

    lowered = str(label).lower().replace(" ", "")
    for forbidden in FORBIDDEN_LABELS:
        if forbidden.lower().replace(" ", "") in lowered:
            raise MetricError(
                f"{label!r} presents the relative design metric as a susceptibility. "
                "This quantity is not chi(2) and has no pm/V value; see nlo.py."
            )


EXCLUSION_RULES: tuple[str, ...] = (
    "solver_failed",
    "not_converged",
    "state_tracking_ambiguous",
    "states_not_bound",
    "matrix_elements_missing",
    "constraint_violated",
)


def candidate_exclusions(
    row: Mapping[str, Any],
    *,
    minimum_tracking_confidence: float = 0.6,
    constraints: Mapping[str, tuple[float, float]] | None = None,
) -> list[str]:
    """Reasons a candidate must not be ranked as "best".

    A candidate stays in every table and plot; it is only barred from the top of
    the ranking.  Silently dropping it would hide exactly the failures a design
    sweep needs to surface.
    """

    reasons: list[str] = []
    if not row.get("solver_success", False):
        reasons.append("solver_failed")
    if row.get("convergence_status") is False:
        reasons.append("not_converged")
    confidence = row.get("state_tracking_confidence")
    if confidence is not None and float(confidence) < minimum_tracking_confidence:
        reasons.append("state_tracking_ambiguous")
    if row.get("all_states_bound") is False:
        reasons.append("states_not_bound")
    if row.get("relative_metric") is None:
        reasons.append("matrix_elements_missing")
    for name, (low, high) in (constraints or {}).items():
        value = row.get(name)
        if value is None:
            reasons.append("constraint_violated")
            continue
        if not (float(low) <= float(value) <= float(high)):
            reasons.append("constraint_violated")
    return sorted(dict.fromkeys(reasons))


def rank_candidates(
    rows: list[Mapping[str, Any]],
    *,
    metric_key: str = "relative_metric",
    minimum_tracking_confidence: float = 0.6,
    constraints: Mapping[str, tuple[float, float]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(ranked, excluded)``; every input row appears in exactly one."""

    ranked: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        reasons = candidate_exclusions(
            row,
            minimum_tracking_confidence=minimum_tracking_confidence,
            constraints=constraints,
        )
        enriched = dict(row)
        enriched["exclusion_reasons"] = ";".join(reasons)
        if reasons:
            excluded.append(enriched)
        else:
            ranked.append(enriched)
    ranked.sort(key=lambda item: float(item.get(metric_key) or 0.0), reverse=True)
    for position, row in enumerate(ranked, start=1):
        row["rank"] = position
    return ranked, excluded
