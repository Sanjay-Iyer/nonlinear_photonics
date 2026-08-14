"""Frozen, controlled case definitions for Demo 19.

The four interface identifiers are permanent public data: I1, I2, I3 and I4.
No case is selected from previous physics and no random case generation exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEMO_ID = "19_quantum_well_interface_grading_showcase"
CASE_COUNT = 13
INTERFACE_IDS = ("I1", "I2", "I3", "I4")
THICK_WELL_NM = 7.1
TUNNEL_BARRIER_NM = 1.8
THIN_WELL_NM = 2.9
PERIOD_BARRIER_NM = 18.2
AL_FRACTION = 0.55
WELL_AL_FRACTION = 0.0
TEMPERATURE_K = 300.0
ACTIVE_MESH_NM = 0.05
OUTER_MESH_NM = 0.5
GEOMETRY_CONVENTION = (
    "Full 0-to-0.55 transition width centered on the nominal abrupt interface; "
    "equal lengths of the adjacent materials are replaced, while nominal "
    "interface positions and total device length remain fixed."
)


@dataclass(frozen=True)
class GradingCase:
    case_id: str
    case_name: str
    profile: str
    widths_nm: tuple[float, float, float, float]
    nominal_grade_width_nm: float | None
    notes: str = ""

    @property
    def physics_label(self) -> str:
        return f"p{int(self.case_id):02d}"

    @property
    def is_abrupt(self) -> bool:
        return self.profile == "abrupt"

    @property
    def implementation_type(self) -> str:
        if self.profile == "abrupt":
            return "NATIVE_NEXTNANO_SYNTAX"
        if self.profile == "linear":
            return "NATIVE_NEXTNANO_SYNTAX"
        return "PYTHON_GENERATED_PROFILE_RENDERED_TO_NEXTNANO"

    def width(self, interface_id: str) -> float:
        return float(self.widths_nm[INTERFACE_IDS.index(interface_id)])

    def interface_profile(self, interface_id: str) -> str:
        return "abrupt" if self.width(interface_id) == 0.0 else self.profile

    def as_case_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "profile": self.profile,
            "nominal_grade_width_nm": self.nominal_grade_width_nm,
        }
        for interface_id in INTERFACE_IDS:
            row[f"{interface_id}_profile"] = self.interface_profile(interface_id)
            row[f"{interface_id}_width_nm"] = self.width(interface_id)
        row.update({
            "well1_nm": THICK_WELL_NM,
            "tunnel_barrier_nm": TUNNEL_BARRIER_NM,
            "well2_nm": THIN_WELL_NM,
            "barrier_Al_fraction": AL_FRACTION,
            "well_Al_fraction": WELL_AL_FRACTION,
            "grading_geometry_convention": GEOMETRY_CONVENTION,
            "implementation_type": self.implementation_type,
            "requires_solver": True,
            "notes": self.notes,
        })
        return row


def all_cases() -> list[GradingCase]:
    cases = [
        GradingCase("00", "Abrupt reference", "abrupt", (0, 0, 0, 0), 0.0,
                    "Reference for every normalized comparison."),
        GradingCase("01", "Linear 0.2 nm", "linear", (0.2,) * 4, 0.2),
        GradingCase("02", "Linear 0.4 nm", "linear", (0.4,) * 4, 0.4),
        GradingCase("03", "Linear 0.7 nm", "linear", (0.7,) * 4, 0.7),
        GradingCase("04", "Linear 1.0 nm", "linear", (1.0,) * 4, 1.0),
        GradingCase("05", "Linear 1.4 nm", "linear", (1.4,) * 4, 1.4),
        GradingCase("06", "Asymmetric inner grading A", "linear", (0, 0.4, 0.8, 0), None,
                    "Outer interfaces abrupt; isolates orientation of inner grading."),
        GradingCase("07", "Asymmetric inner grading B", "linear", (0, 0.8, 0.4, 0), None,
                    "Reverse of Case 06."),
        GradingCase("08", "Inner interfaces graded only", "linear", (0, 0.7, 0.7, 0), 0.7,
                    "Isolates changes to inter-well coupling."),
        GradingCase("09", "Outer interfaces graded only", "linear", (0.7, 0, 0, 0.7), 0.7,
                    "Isolates changes primarily associated with outer confinement."),
        GradingCase("10", "Fermi-like 0.7 nm", "fermi", (0.7,) * 4, 0.7,
                    "Python-generated endpoint-normalized logistic profile."),
        GradingCase("11", "erf 0.7 nm", "erf", (0.7,) * 4, 0.7,
                    "Python-generated endpoint-normalized error-function profile."),
        GradingCase("12", "Cosine 0.7 nm", "cosine", (0.7,) * 4, 0.7,
                    "Python-generated raised-cosine profile."),
    ]
    validate_cases(cases)
    return cases


def validate_cases(cases: list[GradingCase]) -> None:
    expected = [f"{i:02d}" for i in range(CASE_COUNT)]
    if [case.case_id for case in cases] != expected:
        raise ValueError(f"Demo 19 case IDs must be {expected}")
    if len({case.case_name for case in cases}) != CASE_COUNT:
        raise ValueError("Demo 19 case names must be unique")
    if cases[0].profile != "abrupt" or any(cases[0].widths_nm):
        raise ValueError("Case 00 must be the zero-width abrupt reference")
    allowed = {"abrupt", "linear", "fermi", "erf", "cosine"}
    for case in cases:
        if case.profile not in allowed:
            raise ValueError(f"{case.case_id}: unsupported profile {case.profile}")
        if len(case.widths_nm) != 4 or any(width < 0 for width in case.widths_nm):
            raise ValueError(f"{case.case_id}: exactly four non-negative widths are required")


CASE_TABLE_FIELDS = [
    "case_id", "case_name", "profile", "nominal_grade_width_nm",
    "I1_profile", "I1_width_nm", "I2_profile", "I2_width_nm",
    "I3_profile", "I3_width_nm", "I4_profile", "I4_width_nm",
    "well1_nm", "tunnel_barrier_nm", "well2_nm",
    "barrier_Al_fraction", "well_Al_fraction",
    "grading_geometry_convention", "implementation_type", "requires_solver", "notes",
]
