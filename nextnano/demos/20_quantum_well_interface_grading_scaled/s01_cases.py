"""Stage 01 - the 13 frozen grading cases.

These are Demo 19's cases, reproduced here so Demo 20 is self-contained and can
be read without opening Demo 19. They are *not* re-derived, re-tuned or
regenerated: ``tests/test_demo20.py::test_cases_match_demo19`` imports Demo 19's
own ``cases19.all_cases()`` and asserts field-by-field equality, so any drift
fails a test rather than quietly becoming a different study.

``widths_nm`` is always ordered ``(I1, I2, I3, I4)`` and each entry is the
**full** 0 -> 0.55 transition width in nm, centred on that nominal interface.
A width of 0 means that interface stays abrupt in an otherwise graded case.

    I1  outer AlGaAs -> thick GaAs well     (0.55 -> 0)
    I2  thick GaAs well -> tunnel AlGaAs    (0 -> 0.55)
    I3  tunnel AlGaAs -> thin GaAs well     (0.55 -> 0)
    I4  thin GaAs well -> outer AlGaAs      (0 -> 0.55)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

DEMO_ID = "20_quantum_well_interface_grading_scaled"
PARENT_DEMO_ID = "19_quantum_well_interface_grading_showcase"
CASE_COUNT = 13
INTERFACE_IDS = ("I1", "I2", "I3", "I4")
REFERENCE_CASE_ID = "00"

#: Human names for the four interfaces, used in manifests and profile requests.
INTERFACE_NAMES: Mapping[str, str] = {
    "I1": "outer_left_algaas_to_gaas",
    "I2": "central_gaas_to_algaas",
    "I3": "central_algaas_to_gaas",
    "I4": "outer_right_gaas_to_algaas",
}

GEOMETRY_CONVENTION = (
    "Full 0-to-0.55 transition width centered on the nominal abrupt interface; "
    "equal lengths of the adjacent materials are replaced, while nominal "
    "interface positions and total device length remain fixed."
)

PROFILE_FAMILIES = ("abrupt", "linear", "fermi", "erf", "cosine")
#: Families with no native nextnano++ keyword, handed over as a sampled table.
IMPORTED_FAMILIES = frozenset({"fermi", "erf", "cosine"})


class Cases20Error(ValueError):
    """A case definition is not one of Demo 20's 13 controlled cases."""


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
    def is_imported(self) -> bool:
        """True when this case is rendered as a ``ternary_import`` DAT table."""

        return self.profile in IMPORTED_FAMILIES

    @property
    def implementation_type(self) -> str:
        if self.profile in ("abrupt", "linear"):
            return "NATIVE_NEXTNANO_SYNTAX"
        return "PYTHON_GENERATED_PROFILE_RENDERED_TO_NEXTNANO"

    @property
    def render_method(self) -> str:
        if self.is_abrupt:
            return "abrupt_regions"
        return "ternary_linear" if self.profile == "linear" else "ternary_import"

    def width(self, interface_id: str) -> float:
        return float(self.widths_nm[INTERFACE_IDS.index(interface_id)])

    def interface_profile(self, interface_id: str) -> str:
        """The shape actually applied at one interface (zero width => abrupt)."""

        return "abrupt" if self.width(interface_id) == 0.0 else self.profile

    def as_case_row(self, cfg: Mapping[str, Any]) -> dict[str, Any]:
        geometry = cfg["geometry"]
        materials = cfg["materials"]
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
            "well1_nm": float(geometry["thick_well_nm"]),
            "tunnel_barrier_nm": float(geometry["tunnel_barrier_nm"]),
            "well2_nm": float(geometry["thin_well_nm"]),
            "barrier_Al_fraction": float(materials["barrier_al_fraction"]),
            "well_Al_fraction": float(materials["well_al_fraction"]),
            "grading_geometry_convention": GEOMETRY_CONVENTION,
            "implementation_type": self.implementation_type,
            "requires_solver": True,
            "notes": self.notes,
        })
        return row


CASE_TABLE_FIELDS = [
    "case_id", "case_name", "profile", "nominal_grade_width_nm",
    "I1_profile", "I1_width_nm", "I2_profile", "I2_width_nm",
    "I3_profile", "I3_width_nm", "I4_profile", "I4_width_nm",
    "well1_nm", "tunnel_barrier_nm", "well2_nm",
    "barrier_Al_fraction", "well_Al_fraction",
    "grading_geometry_convention", "implementation_type", "requires_solver",
    "notes",
]


def all_cases() -> list[GradingCase]:
    """The 13 controlled cases, in fixed order. Identical to Demo 19."""

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
    expected = [f"{index:02d}" for index in range(CASE_COUNT)]
    if [case.case_id for case in cases] != expected:
        raise Cases20Error(f"Demo 20 case IDs must be exactly {expected}")
    if len({case.case_name for case in cases}) != CASE_COUNT:
        raise Cases20Error("Demo 20 case names must be unique")
    if cases[0].case_id != REFERENCE_CASE_ID:
        raise Cases20Error(f"case {REFERENCE_CASE_ID} must come first")
    if cases[0].profile != "abrupt" or any(cases[0].widths_nm):
        raise Cases20Error("Case 00 must be the zero-width abrupt reference")
    for case in cases:
        if case.profile not in PROFILE_FAMILIES:
            raise Cases20Error(f"{case.case_id}: unsupported profile {case.profile!r}")
        if len(case.widths_nm) != 4 or any(width < 0 for width in case.widths_nm):
            raise Cases20Error(
                f"{case.case_id}: exactly four non-negative widths are required"
            )


def by_id() -> dict[str, GradingCase]:
    return {case.case_id: case for case in all_cases()}


def implementation_audit_rows() -> list[dict[str, Any]]:
    """How each profile family actually reaches nextnano++."""

    return [
        {"profile": "abrupt", "implementation_type": "NATIVE_NEXTNANO_SYNTAX",
         "native_nextnano_keyword": "binary / ternary_constant regions",
         "renderer": "Demo 20 abrupt region renderer", "validated": True,
         "notes": "No grading keyword; sharp GaAs well edges."},
        {"profile": "linear", "implementation_type": "NATIVE_NEXTNANO_SYNTAX",
         "native_nextnano_keyword": "ternary_linear",
         "renderer": "Demo 20 per-interface native renderer", "validated": True,
         "notes": "One ternary_linear region per nonzero I1-I4 width; "
                  "ternary_pyramid is never used."},
        {"profile": "fermi", "implementation_type": "PYTHON_GENERATED_PROFILE_RENDERED_TO_NEXTNANO",
         "native_nextnano_keyword": "ternary_import",
         "renderer": "s02_grading endpoint-normalized logistic + DAT table",
         "validated": True,
         "notes": "Python-generated Fermi-like logistic profile; nextnano++ has "
                  "no native Fermi grading keyword."},
        {"profile": "erf", "implementation_type": "PYTHON_GENERATED_PROFILE_RENDERED_TO_NEXTNANO",
         "native_nextnano_keyword": "ternary_import",
         "renderer": "s02_grading endpoint-normalized erf + DAT table",
         "validated": True,
         "notes": "Sampled x_Al(z); nextnano++ linearly interpolates the table."},
        {"profile": "cosine", "implementation_type": "PYTHON_GENERATED_PROFILE_RENDERED_TO_NEXTNANO",
         "native_nextnano_keyword": "ternary_import",
         "renderer": "s02_grading raised cosine + DAT table", "validated": True,
         "notes": "Sampled x_Al(z); nextnano++ linearly interpolates the table."},
    ]
