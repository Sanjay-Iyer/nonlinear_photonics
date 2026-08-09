"""Grading widths, stated three ways, so two conventions can never be confused.

Reading the supplied ``.nnp`` files turned up a difference that would otherwise
have silently invalidated the whole comparison. For ``$GRADE_WIDTH = 0.7`` those
files emit::

    ternary_linear{ alloy_x = [0.55, 0.0]  x = [$QW1_min - 0.7, $QW1_min] }

so 0.7 nm is

* the **full** 0 -> 0.55 ramp, not a 10-90% width, and
* placed **entirely outside** the well, leaving ``QW1_min .. QW1_max`` pure GaAs.

Demo 16E used the same number to mean something else: a **10-90%** width, whose
full ramp is ``1.25 x`` wider, **centred** on the interface so half of it eats
into the well. A "0.70 nm grade" is therefore two different structures depending
on which demo wrote it -- a 0.875 nm ramp straddling the interface, or a 0.70 nm
ramp sitting outside it. The GaAs well is not even the same width.

Demo 16G adopts the ``.nnp`` convention, because Group 1 is fixed and the sweep
has to be comparable with it. Every case reports all three numbers and the
placement, and :func:`describe` is the only way any of them is produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

#: A linear ramp rises 0 -> 1 over its full width; the 10% and 90% crossings sit
#: at 0.1 and 0.9 of it, so the 10-90 span is 0.8 of the full width. Exact, not
#: a fit.
TEN_NINETY_OVER_FULL_RAMP = 0.8

#: Demo 16E's inverse constant, recorded for cross-reading its tables only. It
#: is never used to build anything here.
DEMO16E_FULL_RAMP_OVER_TEN_NINETY = 1.25

#: The two placements a linear grade can have relative to the nominal interface.
PLACEMENTS = ("outside_well", "centred_on_interface")

DEFINITIONS = {
    "full_linear_ramp_outside_well": {
        "meaning": (
            "the stated number is the FULL 0 -> x_max linear ramp width, placed "
            "entirely outside the well so the GaAs well keeps its stated width"
        ),
        "placement": "outside_well",
        "source": (
            "the supplied DoubleQuantumWell_ramesh_arxiv_grades.nnp: "
            "ternary_linear{ alloy_x = [0.55, 0.0] x = [$QW1_min - $GRADE_WIDTH,"
            " $QW1_min] }"
        ),
    },
    "ten_ninety_centred_on_interface": {
        "meaning": (
            "the stated number is the 10-90% transition width; the full ramp is "
            "1.25x wider and is centred on the nominal interface, so half of it "
            "lies inside the well"
        ),
        "placement": "centred_on_interface",
        "source": "Demo 14 / Demo 16E grading14.build_structure_profile",
    },
}

DEFAULT_DEFINITION = "full_linear_ramp_outside_well"


class Grading16GError(ValueError):
    """A grading request whose definition is unstated or unknown."""


@dataclass(frozen=True)
class GradeWidths:
    """One interface's grading, in every unit anyone might mean by it."""

    requested_nm: float
    definition: str
    full_linear_ramp_width_nm: float
    ten_ninety_width_nm: float
    placement: str
    is_abrupt: bool

    def ramp_span_nm(self, interface_nm: float, *, rising: bool) -> tuple[float, float]:
        """Where the ramp actually starts and ends on the growth axis.

        ``rising`` means Al increases with z across this interface (GaAs ->
        AlGaAs). Under ``outside_well`` the ramp is laid on the barrier side, so
        the well edge is untouched; under ``centred_on_interface`` it straddles.
        """

        if self.is_abrupt:
            return (float(interface_nm), float(interface_nm))
        width = self.full_linear_ramp_width_nm
        if self.placement == "centred_on_interface":
            half = 0.5 * width
            return (float(interface_nm) - half, float(interface_nm) + half)
        if self.placement == "outside_well":
            # The barrier side is +z at a rising interface and -z at a falling one.
            if rising:
                return (float(interface_nm), float(interface_nm) + width)
            return (float(interface_nm) - width, float(interface_nm))
        raise Grading16GError(f"unknown placement {self.placement!r}")

    def as_record(self, prefix: str = "") -> dict[str, Any]:
        key = f"{prefix}_" if prefix else ""
        return {
            f"{key}requested_grade_nm": self.requested_nm,
            f"{key}requested_grade_definition": self.definition,
            f"{key}full_linear_ramp_width_nm": self.full_linear_ramp_width_nm,
            f"{key}10_90_width_nm": self.ten_ninety_width_nm,
            f"{key}grade_placement": self.placement,
            f"{key}is_abrupt": self.is_abrupt,
        }


def describe(
    requested_nm: float,
    *,
    definition: str = DEFAULT_DEFINITION,
    abrupt_threshold_nm: float = 0.005,
) -> GradeWidths:
    """The only constructor. Nothing else may compute a grading width.

    A single entry point is the point: the two conventions differ by 1.25x and
    by whether the ramp sits inside the well, and a second place that does this
    arithmetic is a second place for them to diverge.
    """

    if definition not in DEFINITIONS:
        raise Grading16GError(
            f"unknown grading definition {definition!r}; known: {sorted(DEFINITIONS)}"
        )
    value = float(requested_nm)
    if value < 0.0:
        raise Grading16GError(f"a grading width cannot be negative: {value}")
    placement = DEFINITIONS[definition]["placement"]
    if value <= float(abrupt_threshold_nm):
        # Genuinely abrupt: no ramp region is emitted at all, rather than a
        # sub-mesh ramp the grid cannot carry.
        return GradeWidths(value, definition, 0.0, 0.0, placement, True)
    if definition == "full_linear_ramp_outside_well":
        full = value
        ten_ninety = value * TEN_NINETY_OVER_FULL_RAMP
    else:
        ten_ninety = value
        full = value * DEMO16E_FULL_RAMP_OVER_TEN_NINETY
    return GradeWidths(value, definition, full, ten_ninety, placement, False)


def convention_note(definition: str = DEFAULT_DEFINITION) -> dict[str, Any]:
    """Everything a reader needs to interpret a grading column, in one place."""

    entry = DEFINITIONS[definition]
    return {
        "definition": definition,
        "meaning": entry["meaning"],
        "placement": entry["placement"],
        "source": entry["source"],
        "ten_ninety_over_full_ramp": TEN_NINETY_OVER_FULL_RAMP,
        "warning": (
            "Demo 16E's tables use ten_ninety_centred_on_interface. A '0.70 nm "
            "grade' there is a 0.875 nm ramp straddling the interface; here it "
            "is a 0.70 nm ramp outside it, and the GaAs well widths differ too. "
            "Never compare the two columns without converting."
        ),
    }


def compare_definitions(requested_nm: float) -> dict[str, Any]:
    """The same number read both ways, so the difference is visible not implied."""

    both = {
        name: describe(requested_nm, definition=name).as_record()
        for name in DEFINITIONS
    }
    nnp = both["full_linear_ramp_outside_well"]
    e16 = both["ten_ninety_centred_on_interface"]
    return {
        "requested_nm": float(requested_nm),
        "as_full_ramp_outside_well": nnp,
        "as_ten_ninety_centred": e16,
        "full_ramp_width_ratio": (
            None if not nnp["full_linear_ramp_width_nm"]
            else e16["full_linear_ramp_width_nm"] / nnp["full_linear_ramp_width_nm"]
        ),
        "well_width_consumed_by_grade_nm": {
            "outside_well": 0.0,
            "centred_on_interface": 0.5 * e16["full_linear_ramp_width_nm"],
        },
    }
