"""The 21 fixed structures Demo 17E solves: one abrupt reference, 20 realizations.

WHAT VARIES, AND WHAT DOES NOT
==============================
Exactly one thing varies across all 21 cases: the 10-90 transition width of the
interfaces. Everything else is nailed to the reference paper's structure and to
Demo 17's conventions --

    asymmetry s          0.42        (7.10 nm / 2.90 nm wells, 10.0 nm total)
    central barrier      1.80 nm
    aluminium fraction   0.55
    grading family       linear
    deck representation  native ternary_linear (abrupt for case_00)
    mesh                 0.05 nm

-- so a difference between two rows of Demo 17E's table is a difference in
interface roughness and cannot be anything else. Demo 17 varied barrier
thickness, asymmetry, grading width and deck representation together across its
ten cases, which is right for a structure survey and useless for a slope.

``case_00`` is the ideal abrupt reference and is Demo 17's ``case_02``, field for
field. :func:`assert_matches_demo17_reference` enforces that in code, so the
abrupt anchor of this study and the abrupt anchor of the previous one are the
same structure rather than two structures that happen to be described the same
way.

HOW A REALIZATION IS DRAWN
==========================
Three widths per realization, sampled independently because the two interface
chemistries are not equivalent -- an AlGaAs-on-GaAs growth front and a
GaAs-on-AlGaAs one segregate differently:

    gaas_to_algaas_barrier    z2, the tunnelling barrier's leading interface
    algaas_to_gaas_well       z1 and z3, where each well opens
    gaas_to_algaas_cladding   z4, into the period cladding

They are drawn HIERARCHICALLY, because that is what a growth run is: one
run-level width per realization, then a small independent offset per interface.

    sigma_run  ~ TruncNormal(mu, s_run)  on [minimum_nm, maximum_nm]
    sigma_i    =  sigma_run + delta_i,    delta_i ~ Normal(0, s_interface)

A flat i.i.d. draw per interface would be the wrong model twice over. Physically,
the interfaces of one wafer share a substrate temperature, a V/III ratio and a
growth rate, so their widths are strongly correlated and the large variation is
run to run -- which is exactly what STEM/EDS across wafers shows. Statistically,
averaging three independent draws shrinks the ensemble's spread by root-3, so a
flat model would produce twenty realizations that all look the same and a
severity grouping with one member in each tail. The hierarchy keeps the
per-interface independence the study wants and puts the spread where the physics
puts it.

Every draw is one uniform from a ``random.Random(seed)`` stream mapped through an
exact inverse CDF (:class:`statistics.NormalDist`). Both are stdlib and both are
documented as reproducible across Python versions, so a realization depends on
the seed and on nothing else -- not on the numpy version, not on the platform,
and not on the order in which anything else ran.

THE RISE TIE
============
``grading14.build_structure_profile`` takes one width per growth DIRECTION, not
one per interface, because one growth process makes every interface it makes.
The two GaAs -> AlGaAs interfaces (z2, z4) share a chemistry, so they are
sampled separately, reported separately, frozen separately -- and RENDERED with
their mean, with the residual recorded per case in
``rise_tie_residual_nm``. Forking the composition builder instead would fork the
path Demo 16E's realized-composition gate and Demo 17's whole comparison rest
on, which is a far larger claim than a roughness sweep needs to make.

Nothing here is proposed, scored, ranked or selected by any algorithm, and
nothing reads a previous run's results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import random
import statistics
from typing import Any, Mapping, Sequence

import yaml

import chi2 as chi2mod

CASES_FILENAME = "validation_cases.yaml"
CONFIG_FILENAME = "demo17e.yaml"
DEMO_ID = "17e_statistical_grading_sweep"

#: Held fixed across all 21 cases.
GRADING_PROFILE = "linear"
TOTAL_WELL_NM = 10.0
AL_FRACTION = 0.55
MESH_NM = 0.05
CENTRAL_BARRIER_NM = 1.80
TARGET_WAVELENGTH_NM = 1550.0
PAPER_ASYMMETRY = chi2mod.structural_asymmetry(7.1, 2.9)

#: 1 abrupt reference + 20 realizations.
REFERENCE_CASE_ID = "case_00"
REALIZATION_COUNT = 20
CASE_COUNT = REALIZATION_COUNT + 1

#: The paper quotes 2340 pm/V for ideal abrupt interfaces, so the abrupt
#: reference is also the one case a published absolute number describes.
PAPER_TARGET_CASE_ID = REFERENCE_CASE_ID
PAPER_TARGET_PM_PER_V = 2340.0

#: The Demo 17 case this study's reference must equal, field for field.
DEMO17_REFERENCE_CASE_ID = "case_02"

#: Demo 14's profile builder has no abrupt branch -- a 10-90 width must be finite
#: and positive -- so an abrupt interface is requested as a ramp far narrower
#: than the 0.05 nm mesh can carry. At 0.001 nm the full transition spans
#: 0.00125 nm, one fortieth of a cell. The DECK is abrupt outright:
#: ``demo16e.abrupt_blocks`` emits no ramp regions at all. Demo 17's value,
#: reused so the two abrupt references are byte-identical structures.
ABRUPT_SENTINEL_WIDTH_NM = 0.001

#: A linear 10-90 width of w spans 1.25 * w end to end.
LINEAR_RAMP_SPAN_PER_10_90 = 1.25

#: Sampling bounds this module will accept from the config. Wider than Demo 17's
#: (0.40, 1.40) at the low end on purpose: a 0.20 nm transition is about one
#: unit cell, which is what a genuinely sharp measured interface looks like, and
#: its 0.25 nm ramp still spans five mesh cells. ``validate_cases`` refuses
#: anything narrower, and preflight17e re-checks the mesh ratio per case.
GRADING_BOUNDS_NM = (0.20, 1.40)
MINIMUM_RAMP_CELLS = 4.0

INTERFACE_MODES = ("graded", "abrupt")
RENDER_REQUESTS = ("auto", "imported")
REPRESENTATIONS = ("abrupt", "native_linear", "imported_profile")
DISTRIBUTIONS = ("truncated_normal", "uniform")

#: Draw order. Renaming or reordering these changes every realization, which is
#: why preflight17e regenerates the list and compares it to the frozen file.
SAMPLED_INTERFACES: tuple[str, ...] = (
    "gaas_to_algaas_barrier",
    "algaas_to_gaas_well",
    "gaas_to_algaas_cladding",
)

#: Which sampled widths the renderer's two direction knobs are built from.
#: ``rise`` is where Al increases with z, ``fall`` where it decreases.
RISE_INTERFACES = ("gaas_to_algaas_barrier", "gaas_to_algaas_cladding")
FALL_INTERFACES = ("algaas_to_gaas_well",)

#: Severity grouping for the figures and the summary statistics. Bounds are
#: applied to the mean realized interface width. Nothing is selected or excluded
#: by these -- they only decide which panel a curve is drawn in.
SEVERITY_ABRUPT = "abrupt"
DEFAULT_SEVERITY_BANDS: tuple[dict[str, Any], ...] = (
    {"key": "sharp", "label": "Sharp (< 0.5 nm)", "upper_nm": 0.5},
    {"key": "moderate", "label": "Moderate (0.5 - 0.9 nm)",
     "lower_nm": 0.5, "upper_nm": 0.9},
    {"key": "severe", "label": "Severe (> 0.9 nm)", "lower_nm": 0.9},
)

#: Structural fields of the reference case that must equal Demo 17's case_02.
DEMO17_BASELINE_FIELDS = (
    "asymmetry_s", "central_barrier_nm", "left_grading_width_nm",
    "right_grading_width_nm", "interface_mode", "render_request", "overlap",
    "grading_profile",
)


class Cases17EError(ValueError):
    """The frozen Demo 17E case list violates its controlled-comparison design."""


# ---------------------------------------------------------------------------
# The sampler
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SamplingPlan:
    """Everything that decides what the 20 realizations are.

    Frozen, and hashed into every artifact, because two runs claiming to be the
    same study must be provably drawing from the same distribution. Changing any
    field here changes every realization.
    """

    seed: int
    realizations: int
    distribution: str
    mean_nm: float
    #: Run-to-run spread: how much one realization's whole growth differs from
    #: the next. This is what sets the ensemble's width and the severity split.
    standard_deviation_nm: float
    minimum_nm: float
    maximum_nm: float
    #: Interface-to-interface spread WITHIN one realization. Deliberately much
    #: smaller than the run-to-run term -- the interfaces of one wafer share a
    #: growth condition -- and it is what makes the three sampled widths
    #: independent rather than equal.
    interface_standard_deviation_nm: float = 0.08
    round_to_decimals: int = 4
    tie_rule: str = "mean_of_same_chemistry"
    maximum_rise_tie_residual_nm: float = 0.60

    def __post_init__(self) -> None:
        if self.distribution not in DISTRIBUTIONS:
            raise Cases17EError(
                f"sampling.distribution must be one of {DISTRIBUTIONS}, got "
                f"{self.distribution!r}."
            )
        if not 0 < self.realizations <= 999:
            raise Cases17EError(
                f"sampling.realizations must lie in 1..999, got {self.realizations}."
            )
        if self.minimum_nm >= self.maximum_nm:
            raise Cases17EError(
                f"sampling bounds must increase: [{self.minimum_nm}, "
                f"{self.maximum_nm}]."
            )
        low, high = GRADING_BOUNDS_NM
        if self.minimum_nm < low or self.maximum_nm > high:
            raise Cases17EError(
                f"sampling bounds [{self.minimum_nm}, {self.maximum_nm}] nm fall "
                f"outside the {low}-{high} nm window this demo's mesh and barrier "
                "can carry; see cases17e.GRADING_BOUNDS_NM."
            )
        if not self.minimum_nm <= self.mean_nm <= self.maximum_nm:
            raise Cases17EError(
                f"sampling.mean_nm ({self.mean_nm}) lies outside its own bounds."
            )
        if self.distribution == "truncated_normal" and self.standard_deviation_nm <= 0:
            raise Cases17EError(
                "sampling.standard_deviation_nm must be > 0 for a truncated normal."
            )
        if self.interface_standard_deviation_nm < 0:
            raise Cases17EError(
                "sampling.interface_standard_deviation_nm must be >= 0."
            )
        if self.interface_standard_deviation_nm >= self.standard_deviation_nm:
            raise Cases17EError(
                f"sampling.interface_standard_deviation_nm "
                f"({self.interface_standard_deviation_nm}) is not smaller than the "
                f"run-to-run spread ({self.standard_deviation_nm}). The hierarchy "
                "only means anything if one wafer's interfaces resemble each "
                "other more than they resemble another wafer's."
            )
        if self.tie_rule != "mean_of_same_chemistry":
            raise Cases17EError(
                f"unknown sampling.tie_rule {self.tie_rule!r}; this demo renders "
                "the two GaAs -> AlGaAs interfaces with their mean."
            )

    def as_record(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "model": (
                "hierarchical: one truncated-normal run-level width per "
                "realization, plus an independent normal offset per interface"
            ),
            "interfaces_in_draw_order": list(SAMPLED_INTERFACES),
            "rise_interfaces": list(RISE_INTERFACES),
            "fall_interfaces": list(FALL_INTERFACES),
            "uniform_source": "random.Random(seed) -- Mersenne Twister, stdlib",
            "inverse_cdf_source": "statistics.NormalDist -- exact, stdlib",
            "draws_per_realization": 1 + len(SAMPLED_INTERFACES),
        }


def sampling_plan_from_config(cfg: Mapping[str, Any]) -> SamplingPlan:
    """Build the plan from ``demo17e.yaml``'s ``sampling`` block."""

    block = cfg.get("sampling")
    if not isinstance(block, Mapping):
        raise Cases17EError(
            f"{CONFIG_FILENAME} has no 'sampling' block; Demo 17E cannot draw its "
            "realizations from an unstated distribution."
        )
    declared = [str(entry["key"]) for entry in block.get("interfaces", [])]
    if declared and tuple(declared) != SAMPLED_INTERFACES:
        raise Cases17EError(
            f"sampling.interfaces declares {declared} but the sampler draws "
            f"{list(SAMPLED_INTERFACES)} in that order. Reordering them would "
            "silently change every realization."
        )
    return SamplingPlan(
        seed=int(block["seed"]),
        realizations=int(block.get("realizations", REALIZATION_COUNT)),
        distribution=str(block.get("distribution", "truncated_normal")),
        mean_nm=float(block["mean_nm"]),
        standard_deviation_nm=float(block.get("standard_deviation_nm", 0.25)),
        minimum_nm=float(block["minimum_nm"]),
        maximum_nm=float(block["maximum_nm"]),
        interface_standard_deviation_nm=float(
            block.get("interface_standard_deviation_nm", 0.08)
        ),
        round_to_decimals=int(block.get("round_to_decimals", 4)),
        tie_rule=str(block.get("tie_rule", "mean_of_same_chemistry")),
        maximum_rise_tie_residual_nm=float(
            block.get("maximum_rise_tie_residual_nm", 0.60)
        ),
    )


def _draw_run_width(plan: SamplingPlan, rng: random.Random) -> float:
    """One realization's run-level interface width, from one uniform.

    Inverse-CDF rather than rejection sampling, deliberately: rejection consumes
    an unpredictable number of uniforms, so a single unlucky draw would shift
    every subsequent realization. One uniform in, one width out, always.

    For the truncated normal the uniform is mapped into the truncated interval in
    probability space first --

        p = Phi(a) + u * (Phi(b) - Phi(a)),   sigma = mu + s * Phi^-1(p)

    -- so the result is exactly in [minimum_nm, maximum_nm] by construction, not
    by clipping. Clipping would pile probability mass onto the two bounds and
    quietly turn a normal into a normal-plus-two-spikes.
    """

    u = rng.random()
    if plan.distribution == "uniform":
        return plan.minimum_nm + u * (plan.maximum_nm - plan.minimum_nm)
    normal = statistics.NormalDist(plan.mean_nm, plan.standard_deviation_nm)
    lo_p = normal.cdf(plan.minimum_nm)
    hi_p = normal.cdf(plan.maximum_nm)
    return float(normal.inv_cdf(lo_p + u * (hi_p - lo_p)))


def _offset_width(plan: SamplingPlan, run_width: float, rng: random.Random) -> float:
    """One interface's width: the run-level value plus its own small offset.

    The offset is an untruncated normal and the SUM is clipped to the bounds
    rather than re-truncated. That is a guard, not a sampler: the run-level width
    is already interior and the offset is several times smaller than the
    run-to-run spread, so the clip only ever engages for a realization drawn hard
    against a bound, and it is reported in the frozen record like everything
    else. Re-truncating per interface would make the offset's distribution depend
    on where the run landed, which is a stranger model than the clip.
    """

    if plan.interface_standard_deviation_nm > 0:
        offset = statistics.NormalDist(
            0.0, plan.interface_standard_deviation_nm
        ).inv_cdf(rng.random())
    else:
        offset = 0.0
    value = round(run_width + offset, plan.round_to_decimals)
    return min(max(value, plan.minimum_nm), plan.maximum_nm)


def sample_widths(plan: SamplingPlan) -> list[dict[str, float]]:
    """The 20 realizations' three widths each, in draw order.

    One ``random.Random`` seeded once and consumed in a fixed order -- run level
    first, then the three interfaces -- so the whole table is a pure function of
    ``plan``. ``_run_width_nm`` is carried in the record because it is what the
    ensemble's spread is actually drawn from, and a reader checking the
    distribution should not have to reverse it out of three offsets.
    """

    rng = random.Random(plan.seed)
    table: list[dict[str, float]] = []
    for _ in range(plan.realizations):
        run_width = _draw_run_width(plan, rng)
        widths = {
            key: _offset_width(plan, run_width, rng) for key in SAMPLED_INTERFACES
        }
        widths["_run_width_nm"] = round(
            min(max(run_width, plan.minimum_nm), plan.maximum_nm),
            plan.round_to_decimals,
        )
        table.append(widths)
    return table


def severity_for(
    mean_width_nm: float, bands: Sequence[Mapping[str, Any]] | None = None
) -> str:
    """Which grouping band a mean interface width falls in.

    A width on a boundary belongs to the UPPER band (``lower_nm`` is inclusive,
    ``upper_nm`` exclusive), so exactly 0.9 nm reads as severe. Stated because a
    reader comparing a table to a figure will hit that case eventually.
    """

    if mean_width_nm <= 0.0:
        return SEVERITY_ABRUPT
    for band in bands or DEFAULT_SEVERITY_BANDS:
        lower = band.get("lower_nm")
        upper = band.get("upper_nm")
        if (lower is None or mean_width_nm >= float(lower)) and (
            upper is None or mean_width_nm < float(upper)
        ):
            return str(band["key"])
    raise Cases17EError(
        f"mean grading width {mean_width_nm} nm falls in no severity band; the "
        "bands in demo17e.yaml do not cover the sampling range."
    )


# ---------------------------------------------------------------------------
# The case
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GradingCase:
    """One fixed structure. Nothing about it depends on any other case's result.

    The first block of fields is deliberately field-for-field compatible with
    ``cases16e.GeometryCase`` and ``cases17.GeometryCase``: Demo 16E's case
    ladder, metrology, realized-composition gate and solver path all consume a
    case through these names, and Demo 17E reuses every one of them rather than
    reimplementing it. The sampling fields below are additive.
    """

    case_id: str
    name: str
    description: str
    asymmetry_s: float
    central_barrier_nm: float
    #: The RENDERED widths. ``left`` is the GaAs -> AlGaAs (Al rises with z)
    #: direction and ``right`` the AlGaAs -> GaAs one, matching
    #: ``demo14``'s parameter names -- see :meth:`parameters`.
    left_grading_width_nm: float
    right_grading_width_nm: float
    interface_mode: str = "graded"
    render_request: str = "auto"
    overlap: bool = False
    grading_profile: str = GRADING_PROFILE

    #: The three independently SAMPLED widths, before the rise tie. Empty for
    #: the abrupt reference, which is not sampled.
    sampled_widths_nm: Mapping[str, float] = field(default_factory=dict)
    #: The run-level width the three offsets were taken around. Carried because
    #: it is what the ensemble's spread is drawn from, and a reader checking the
    #: distribution should not have to reverse it out of three offsets.
    run_width_nm: float | None = None
    realization_index: int | None = None

    @property
    def is_abrupt(self) -> bool:
        return self.interface_mode == "abrupt"

    @property
    def is_reference(self) -> bool:
        return self.case_id == REFERENCE_CASE_ID

    @property
    def is_paper_target(self) -> bool:
        """True for the one case the paper quotes an absolute number for."""

        return self.case_id == PAPER_TARGET_CASE_ID

    @property
    def physics_label(self) -> str:
        """``p00`` .. ``p20``; the short raw-output name for this case.

        Short on purpose: Demos 16C and 16D both showed a deeply nested raw
        output root is enough to break nextnano++ on Windows.
        """

        return "p" + self.case_id.rsplit("_", 1)[-1]

    @property
    def expected_representation(self) -> str:
        """The deck encoding this case must end up with.

        Checked against the renderer's actual output rather than assumed. Every
        graded realization is native ``ternary_linear``: the barrier is 1.80 nm
        and the widest ramp pair spans 1.75 nm, so no realization can overlap
        into production's imported-table fallback. :func:`validate_cases`
        enforces that rather than hoping for it.
        """

        if self.is_abrupt:
            return "abrupt"
        if self.render_request == "imported" or self.overlap:
            return "imported_profile"
        return "native_linear"

    @property
    def severity(self) -> str:
        return severity_for(self.mean_interface_width_nm())

    def well_widths_nm(self) -> tuple[float, float]:
        return chi2mod.well_widths_from_asymmetry(
            float(self.asymmetry_s), TOTAL_WELL_NM
        )

    def build_widths_nm(self) -> tuple[float, float]:
        """The 10-90 widths handed to the production profile builder."""

        if self.is_abrupt:
            return ABRUPT_SENTINEL_WIDTH_NM, ABRUPT_SENTINEL_WIDTH_NM
        return float(self.left_grading_width_nm), float(self.right_grading_width_nm)

    def mean_interface_width_nm(self) -> float:
        """Mean 10-90 width over the four physical interfaces, as RENDERED.

        z1 and z3 take the fall width, z2 and z4 the rise width, so the mean over
        four interfaces is the mean of the two rendered knobs. This is the
        x-axis of the trend figure and the quantity the severity bands split on:
        it is what the deck actually carries, not what was drawn before the tie.
        """

        if self.is_abrupt:
            return 0.0
        return 0.5 * (
            float(self.left_grading_width_nm) + float(self.right_grading_width_nm)
        )

    def rise_tie_residual_nm(self) -> float:
        """How far each rendered rise interface sits from its own sample.

        Zero for the abrupt reference and for any realization whose two
        GaAs -> AlGaAs draws happened to coincide. Reported per case so the cost
        of the tie is visible in the table rather than buried in this docstring.
        """

        drawn = [self.sampled_widths_nm.get(key) for key in RISE_INTERFACES]
        if any(value is None for value in drawn):
            return 0.0
        return 0.5 * abs(float(drawn[0]) - float(drawn[1]))

    def parameters(self) -> dict[str, Any]:
        """Demo 14's parameter vector for this case."""

        left, right = self.build_widths_nm()
        return {
            "asymmetry_s": float(self.asymmetry_s),
            "nominal_central_barrier_thickness_nm": float(self.central_barrier_nm),
            "gaas_to_algaas_grading_width_10_90_nm": left,
            "algaas_to_gaas_grading_width_10_90_nm": right,
            "grading_profile": self.grading_profile,
        }

    def ramp_span_nm(self) -> float:
        """Combined half-ramp reach of the two central grades."""

        left, right = self.build_widths_nm()
        return 0.5 * LINEAR_RAMP_SPAN_PER_10_90 * (left + right)

    def overlap_width_nm(self) -> float:
        return max(0.0, self.ramp_span_nm() - float(self.central_barrier_nm))

    def narrowest_ramp_span_nm(self) -> float:
        """End-to-end span of the narrowest ramp this case renders.

        The quantity the mesh has to resolve. An abrupt case is excluded from the
        question by construction -- its deck has no ramps at all.
        """

        left, right = self.build_widths_nm()
        return LINEAR_RAMP_SPAN_PER_10_90 * min(left, right)

    def ramp_cells(self, mesh_nm: float = MESH_NM) -> float:
        return self.narrowest_ramp_span_nm() / float(mesh_nm)

    def as_record(self) -> dict[str, Any]:
        well_1, well_2 = self.well_widths_nm()
        build_left, build_right = self.build_widths_nm()
        return {
            **asdict(self),
            "sampled_widths_nm": dict(self.sampled_widths_nm),
            "well_1_nm": well_1,
            "well_2_nm": well_2,
            "total_gaas_well_nm": well_1 + well_2,
            "expected_representation": self.expected_representation,
            "build_left_grading_width_nm": build_left,
            "build_right_grading_width_nm": build_right,
            "mean_interface_grading_width_nm": self.mean_interface_width_nm(),
            "rise_tie_residual_nm": self.rise_tie_residual_nm(),
            "severity": self.severity,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
            "linear_ramp_span_nm": self.ramp_span_nm(),
            "narrowest_ramp_span_nm": self.narrowest_ramp_span_nm(),
            "narrowest_ramp_mesh_cells": (
                None if self.is_abrupt else self.ramp_cells()
            ),
            "overlap_width_nm": self.overlap_width_nm(),
            "is_reference_case": self.is_reference,
            "is_paper_target_case": self.is_paper_target,
        }


# ---------------------------------------------------------------------------
# Building the 21
# ---------------------------------------------------------------------------


def reference_case_only() -> GradingCase:
    """``case_00``: ideal abrupt interfaces, Demo 17's ``case_02`` structure."""

    return GradingCase(
        REFERENCE_CASE_ID,
        "reference_abrupt",
        "Ideal abrupt interfaces on the paper geometry (7.10 / 1.80 / 2.90 nm, "
        "s = 0.42). Structurally identical to Demo 17 case_02, which is the one "
        "structure the paper quotes an absolute value for (2340 pm/V), so every "
        "graded realization below is measured against a solved anchor rather "
        "than against an assumption.",
        PAPER_ASYMMETRY, CENTRAL_BARRIER_NM, 0.0, 0.0, interface_mode="abrupt",
    )


def realization_case(index: int, draw: Mapping[str, float]) -> GradingCase:
    """One graded realization from its run-level width and three offsets.

    ``index`` is 1-based and becomes ``case_01`` .. ``case_20``.
    """

    widths = {key: float(draw[key]) for key in SAMPLED_INTERFACES}
    rise = [widths[key] for key in RISE_INTERFACES]
    fall = [widths[key] for key in FALL_INTERFACES]
    left = sum(rise) / len(rise)          # GaAs -> AlGaAs, Al rises with z
    right = sum(fall) / len(fall)         # AlGaAs -> GaAs, Al falls with z
    return GradingCase(
        f"case_{index:02d}",
        f"realization_{index:02d}",
        "Randomized interface grading realization "
        f"{index:02d}/{REALIZATION_COUNT}: GaAs->AlGaAs barrier "
        f"{widths['gaas_to_algaas_barrier']:.4f} nm, AlGaAs->GaAs well "
        f"{widths['algaas_to_gaas_well']:.4f} nm, GaAs->AlGaAs cladding "
        f"{widths['gaas_to_algaas_cladding']:.4f} nm.",
        PAPER_ASYMMETRY, CENTRAL_BARRIER_NM, left, right,
        sampled_widths_nm=widths,
        run_width_nm=float(draw["_run_width_nm"]),
        realization_index=index,
    )


def all_cases(plan: SamplingPlan | None = None) -> list[GradingCase]:
    """The 21 fixed structures, in the order every table and plot uses.

    ``plan`` defaults to the one in ``demo17e.yaml``. Passing a different plan
    generates a different study, which is why every artifact records the plan it
    was generated from.
    """

    plan = plan or default_plan()
    cases = [reference_case_only()]
    for index, draw in enumerate(sample_widths(plan), start=1):
        cases.append(realization_case(index, draw))
    validate_cases(cases, plan)
    return cases


def default_plan() -> SamplingPlan:
    """The sampling plan from this demo's own config."""

    path = Path(__file__).resolve().parent / CONFIG_FILENAME
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    return sampling_plan_from_config(cfg)


def reference_case(cases: Sequence[GradingCase] | None = None) -> GradingCase:
    pool = list(cases if cases is not None else all_cases())
    return next(case for case in pool if case.is_reference)


def realizations(cases: Sequence[GradingCase] | None = None) -> list[GradingCase]:
    pool = list(cases if cases is not None else all_cases())
    return [case for case in pool if not case.is_reference]


def by_severity(
    cases: Sequence[GradingCase], bands: Sequence[Mapping[str, Any]] | None = None
) -> dict[str, list[GradingCase]]:
    """Realizations grouped for the figures; the reference is not in any band."""

    grouped: dict[str, list[GradingCase]] = {
        str(band["key"]): [] for band in (bands or DEFAULT_SEVERITY_BANDS)
    }
    for case in cases:
        if case.is_reference:
            continue
        grouped.setdefault(
            severity_for(case.mean_interface_width_nm(), bands), []
        ).append(case)
    return grouped


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_cases(
    cases: Sequence[GradingCase], plan: SamplingPlan | None = None
) -> None:
    """Everything the frozen list must satisfy before a deck is ever written."""

    plan = plan or default_plan()
    expected_ids = [REFERENCE_CASE_ID] + [
        f"case_{index:02d}" for index in range(1, plan.realizations + 1)
    ]
    if [case.case_id for case in cases] != expected_ids:
        raise Cases17EError(
            f"expected {expected_ids[0]}..{expected_ids[-1]} "
            f"({len(expected_ids)} cases), got {[c.case_id for c in cases]}."
        )
    if cases[0].case_id != REFERENCE_CASE_ID or not cases[0].is_abrupt:
        raise Cases17EError(
            f"{REFERENCE_CASE_ID} must come first and must be the abrupt "
            "reference; every graded realization is reported against it."
        )
    if sum(case.is_abrupt for case in cases) != 1:
        raise Cases17EError("Demo 17E contains exactly one abrupt case.")

    for case in cases:
        if case.grading_profile != GRADING_PROFILE:
            raise Cases17EError(
                f"{case.case_id}: Demo 17E studies the linear grading family only; "
                "mixing families would confound roughness with profile shape."
            )
        if case.interface_mode not in INTERFACE_MODES:
            raise Cases17EError(f"{case.case_id}: unknown interface mode.")
        if case.render_request not in RENDER_REQUESTS:
            raise Cases17EError(f"{case.case_id}: unknown render request.")
        if abs(case.asymmetry_s - PAPER_ASYMMETRY) > 1e-12:
            raise Cases17EError(
                f"{case.case_id}: asymmetry {case.asymmetry_s} is not the paper's "
                f"{PAPER_ASYMMETRY}. Demo 17E varies grading and nothing else."
            )
        if abs(case.central_barrier_nm - CENTRAL_BARRIER_NM) > 1e-12:
            raise Cases17EError(
                f"{case.case_id}: barrier {case.central_barrier_nm} nm is not the "
                f"fixed {CENTRAL_BARRIER_NM} nm. Demo 17E varies grading and "
                "nothing else."
            )
        if abs(sum(case.well_widths_nm()) - TOTAL_WELL_NM) > 1e-12:
            raise Cases17EError(f"{case.case_id}: total GaAs well thickness changed.")

        for width in (case.left_grading_width_nm, case.right_grading_width_nm):
            if case.is_abrupt:
                if width != 0.0:
                    raise Cases17EError(
                        f"{case.case_id}: an abrupt case must report 0.0 grading width."
                    )
            elif not plan.minimum_nm - 1e-12 <= width <= plan.maximum_nm + 1e-12:
                raise Cases17EError(
                    f"{case.case_id}: rendered grading width {width} nm falls "
                    f"outside the sampled range [{plan.minimum_nm}, "
                    f"{plan.maximum_nm}] nm."
                )
        if case.is_abrupt and case.render_request != "auto":
            raise Cases17EError(
                f"{case.case_id}: an abrupt case has its own renderer and cannot "
                "also request an imported table."
            )

        # The overlap flag and the geometry must agree, and for this demo they
        # must both be False: an overlapping barrier would switch the deck to
        # production's imported-table fallback, so one realization would be
        # rendered differently from the other nineteen and the comparison would
        # stop being controlled.
        geometric_overlap = case.overlap_width_nm() > 1e-12
        if geometric_overlap != case.overlap:
            raise Cases17EError(
                f"{case.case_id}: overlap flag {case.overlap} disagrees with "
                f"geometry (overlap width {case.overlap_width_nm():.6f} nm)."
            )
        if case.overlap:
            raise Cases17EError(
                f"{case.case_id}: grades overlap across the {CENTRAL_BARRIER_NM} nm "
                "barrier, which would render this one case as an imported table "
                "while the rest stay native. Narrow the sampling bounds."
            )
        if case.expected_representation not in REPRESENTATIONS:
            raise Cases17EError(f"{case.case_id}: unknown representation.")
        if not case.is_abrupt and case.expected_representation != "native_linear":
            raise Cases17EError(
                f"{case.case_id}: expected native_linear, got "
                f"{case.expected_representation}."
            )
        if not case.is_abrupt and case.ramp_cells() < MINIMUM_RAMP_CELLS:
            raise Cases17EError(
                f"{case.case_id}: its narrowest ramp spans "
                f"{case.ramp_cells():.2f} mesh cells, below the "
                f"{MINIMUM_RAMP_CELLS} the 0.05 nm grid needs to carry a "
                "transition. A sub-resolution grade is a bug, not a result."
            )
        if not case.is_abrupt:
            missing = [
                key for key in SAMPLED_INTERFACES if key not in case.sampled_widths_nm
            ]
            if missing:
                raise Cases17EError(
                    f"{case.case_id}: sampled widths are missing {missing}; the "
                    "frozen record cannot be traced back to its draws."
                )
            if case.rise_tie_residual_nm() > plan.maximum_rise_tie_residual_nm + 1e-12:
                raise Cases17EError(
                    f"{case.case_id}: the two GaAs -> AlGaAs draws differ by "
                    f"{2 * case.rise_tie_residual_nm():.4f} nm, so rendering their "
                    "mean moves each by more than "
                    f"{plan.maximum_rise_tie_residual_nm} nm."
                )

    graded = [case for case in cases if not case.is_abrupt]
    if len(graded) != plan.realizations:
        raise Cases17EError(
            f"expected {plan.realizations} graded realizations, got {len(graded)}."
        )
    widths = [case.mean_interface_width_nm() for case in graded]
    if max(widths) - min(widths) < 0.10:
        raise Cases17EError(
            f"the {len(graded)} realizations span only "
            f"{max(widths) - min(widths):.4f} nm of mean grading width; a sweep "
            "that does not vary its variable cannot measure a trend."
        )


def assert_matches_demo17_reference(cases: Sequence[GradingCase]) -> str:
    """``case_00`` must be Demo 17's ``case_02``, field for field.

    Demo 17E's whole framing is that the abrupt reference is a SOLVED anchor
    already characterised by Demo 17, not a fresh structure. If the two ever
    drift apart, the ratio each realization is reported against silently stops
    meaning what the tables say it means, so the drift is an error rather than a
    footnote. When Demo 17 is not importable (a bundle that shipped 17E alone)
    this returns a plainly-labelled note instead of pretending the check ran.
    """

    try:
        import cases17  # noqa: PLC0415 - optional; only present in the full repo
    except ImportError:
        return "Demo 17 not importable; reference geometry comparison NOT performed"

    baseline = {case.case_id: case for case in cases17.all_cases()}
    other = baseline.get(DEMO17_REFERENCE_CASE_ID)
    if other is None:
        raise Cases17EError(
            f"Demo 17 has no {DEMO17_REFERENCE_CASE_ID}; the abrupt anchor cannot "
            "be compared."
        )
    if not other.is_abrupt:
        raise Cases17EError(
            f"Demo 17's {DEMO17_REFERENCE_CASE_ID} is not the abrupt case; the "
            "2340 pm/V value is quoted for ideal abrupt interfaces."
        )
    ours = reference_case(cases)
    differing = [
        field_name for field_name in DEMO17_BASELINE_FIELDS
        if getattr(ours, field_name) != getattr(other, field_name)
    ]
    if differing:
        raise Cases17EError(
            f"{ours.case_id} differs from Demo 17 {DEMO17_REFERENCE_CASE_ID} in "
            f"{differing}. Demo 17E varies interface grading, not the anchor."
        )
    for label, ours_value, theirs in (
        ("total well thickness", TOTAL_WELL_NM, cases17.TOTAL_WELL_NM),
        ("aluminium fraction", AL_FRACTION, cases17.AL_FRACTION),
        ("mesh", MESH_NM, cases17.MESH_NM),
        ("abrupt sentinel width", ABRUPT_SENTINEL_WIDTH_NM,
         cases17.ABRUPT_SENTINEL_WIDTH_NM),
    ):
        if ours_value != theirs:
            raise Cases17EError(
                f"{label} is {ours_value} here and {theirs} in Demo 17."
            )
    return (
        f"{ours.case_id} identical to Demo 17 {DEMO17_REFERENCE_CASE_ID} across "
        f"{len(DEMO17_BASELINE_FIELDS)} structural fields"
    )


def demo17_demo_id() -> str:
    """Demo 17's id when it is importable, and a plain note when it is not."""

    try:
        import cases17  # noqa: PLC0415
    except ImportError:
        return "17_paper_chi2_reproduction_corrected (not importable here)"
    return str(cases17.DEMO_ID)


# ---------------------------------------------------------------------------
# Freezing and loading
# ---------------------------------------------------------------------------


def statistics_record(cases: Sequence[GradingCase]) -> dict[str, Any]:
    """What the 20 realizations actually cover, measured rather than intended."""

    graded = [case for case in cases if not case.is_abrupt]
    widths = sorted(case.mean_interface_width_nm() for case in graded)
    per_interface = {
        key: sorted(float(case.sampled_widths_nm[key]) for case in graded)
        for key in SAMPLED_INTERFACES
    }
    grouped = by_severity(cases)

    def summarise(values: Sequence[float]) -> dict[str, float]:
        return {
            "count": len(values),
            "min_nm": min(values),
            "mean_nm": statistics.fmean(values),
            "median_nm": statistics.median(values),
            "max_nm": max(values),
            "stdev_nm": statistics.stdev(values) if len(values) > 1 else 0.0,
        }

    run_widths = [
        float(case.run_width_nm) for case in graded if case.run_width_nm is not None
    ]
    return {
        "mean_interface_grading_width": summarise(widths),
        "run_level_width": summarise(run_widths) if run_widths else None,
        "per_sampled_interface": {
            key: summarise(values) for key, values in per_interface.items()
        },
        "severity_counts": {key: len(value) for key, value in grouped.items()},
        "rise_tie_residual_nm": {
            "max": max(case.rise_tie_residual_nm() for case in graded),
            "mean": statistics.fmean(
                [case.rise_tie_residual_nm() for case in graded]
            ),
        },
        "narrowest_ramp_mesh_cells": min(case.ramp_cells() for case in graded),
    }


def write_cases_file(path: Path, plan: SamplingPlan | None = None) -> Path:
    """Freeze the 21 definitions so a run cannot quietly re-roll them."""

    plan = plan or default_plan()
    cases = all_cases(plan)
    payload = {
        "demo": DEMO_ID,
        "purpose": (
            "One fixed paper-geometry ACQW solved 21 times -- once with ideal "
            "abrupt interfaces and twenty times with seed-locked random "
            "interface grading widths -- to measure how STEM/EDS-scale interface "
            "roughness moves the absolute second-order susceptibility."
        ),
        "reference_structure_identical_to": (
            f"{demo17_demo_id()} {DEMO17_REFERENCE_CASE_ID}"
        ),
        "total_cases": len(cases),
        "deterministic": True,
        "optimization_performed": False,
        "sampling": plan.as_record(),
        "grading_profile": GRADING_PROFILE,
        "grading_families_supported": [GRADING_PROFILE],
        "reference_case": REFERENCE_CASE_ID,
        "paper_target_case": PAPER_TARGET_CASE_ID,
        "paper_target_pm_per_V": PAPER_TARGET_PM_PER_V,
        "fixed_structure": {
            "well": "GaAs", "barrier": "AlGaAs",
            "aluminium_fraction": AL_FRACTION,
            "asymmetry_s": PAPER_ASYMMETRY,
            "central_barrier_nm": CENTRAL_BARRIER_NM,
            "total_gaas_well_nm": TOTAL_WELL_NM,
            "mesh_nm": MESH_NM,
            "target_wavelength_nm": TARGET_WAVELENGTH_NM,
        },
        "abrupt_sentinel_width_nm": ABRUPT_SENTINEL_WIDTH_NM,
        "severity_bands": [dict(band) for band in DEFAULT_SEVERITY_BANDS],
        "realized_statistics": statistics_record(cases),
        "cases": [case.as_record() for case in cases],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8", newline="\n",
    )
    return path


def load_cases(path: Path, plan: SamplingPlan | None = None) -> list[GradingCase]:
    """Read the frozen list back and re-validate it.

    The file is the authority for what gets solved; regenerating from the seed
    is how preflight17e proves the file is what the seed produces.
    """

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fields = set(GradingCase.__dataclass_fields__)
    cases = [
        GradingCase(**{key: value for key, value in row.items() if key in fields})
        for row in payload["cases"]
    ]
    validate_cases(cases, plan)
    return cases


def regenerates_frozen_list(path: Path, plan: SamplingPlan | None = None) -> bool:
    """Whether the seed still reproduces the frozen file, record for record."""

    plan = plan or default_plan()
    frozen = [case.as_record() for case in load_cases(Path(path), plan)]
    fresh = [case.as_record() for case in all_cases(plan)]
    return frozen == fresh


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / CASES_FILENAME
    print(write_cases_file(target))
