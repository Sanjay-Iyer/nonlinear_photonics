"""Ten fixed, deterministic ACQW structures for Demo 16E.

The list is frozen in :data:`CASES_FILENAME` and validated on load. Demo 16E is a
comparison study, not a search: no case is proposed, scored, ranked or selected
by any algorithm, and nothing here reads a previous run's results.

Three deck representations appear on purpose, because "how the composition was
written into the deck" is one of the things the study is validating:

``abrupt``
    No grading at all. The two GaAs wells are carved out of the Al0.55 matrix
    with nothing laid over their edges.
``native_linear``
    nextnano++'s own ``ternary_linear{}`` ramps -- Demo 14's default for a
    non-overlapping linear grade.
``imported_profile``
    The same ``x_Al(z)`` handed over as an imported table. Demo 14 switches to
    this automatically when two ramps overlap (case_08); case_10 asks for it
    deliberately so it can be compared against its native twin, case_09.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

import chi2 as chi2mod

CASES_FILENAME = "validation_cases.yaml"
DEMO_ID = "16E_acqw_structure_physics_optical_comparison"
GRADING_PROFILE = "linear"
TOTAL_WELL_NM = 10.0
AL_FRACTION = 0.55
MESH_NM = 0.05
TARGET_WAVELENGTH_NM = 1550.0
PAPER_ASYMMETRY = chi2mod.structural_asymmetry(7.1, 2.9)
LINEAR_RAMP_SPAN_PER_10_90 = 1.25
CASE_COUNT = 10
REFERENCE_CASE_ID = "case_01"

#: Demo 14's profile builder has no abrupt branch -- a 10-90 width must be finite
#: and positive -- so an abrupt interface is requested as a ramp far narrower
#: than anything the 0.05 nm mesh can carry. At 0.001 nm the full transition
#: spans 0.00125 nm, one fortieth of a mesh cell, so the profile is a step at
#: every mesh coordinate and at every solver cell centre. The DECK is abrupt
#: outright: :func:`demo16e.abrupt_blocks` emits no ramp regions at all. The
#: sentinel exists so the intended profile, the interface bookkeeping and the
#: overlap oracle all come from the same production code as every other case.
ABRUPT_SENTINEL_WIDTH_NM = 0.001

ASYMMETRY_BOUNDS = (0.30, 0.55)
BARRIER_BOUNDS_NM = (0.85, 2.50)
GRADING_BOUNDS_NM = (0.40, 1.40)

INTERFACE_MODES = ("graded", "abrupt")
RENDER_REQUESTS = ("auto", "imported")
REPRESENTATIONS = ("abrupt", "native_linear", "imported_profile")


class Cases16EError(ValueError):
    """The frozen Demo 16E case list violates its fixed-comparison design."""


@dataclass(frozen=True)
class GeometryCase:
    """One fixed structure. Nothing about it depends on any other case's result."""

    case_id: str
    name: str
    description: str
    asymmetry_s: float
    central_barrier_nm: float
    left_grading_width_nm: float
    right_grading_width_nm: float
    #: ``graded`` or ``abrupt``. An abrupt case reports 0.0 grading widths.
    interface_mode: str = "graded"
    #: ``auto`` lets Demo 14's renderer choose; ``imported`` forces the table.
    render_request: str = "auto"
    overlap: bool = False
    grading_profile: str = GRADING_PROFILE

    @property
    def is_abrupt(self) -> bool:
        return self.interface_mode == "abrupt"

    @property
    def physics_label(self) -> str:
        """``p01`` .. ``p10``; the short raw-output name for this case."""

        return "p" + self.case_id.rsplit("_", 1)[-1]

    @property
    def expected_representation(self) -> str:
        """The deck encoding this case must end up with.

        Checked against the renderer's actual output rather than assumed: an
        overlapping grade is *supposed* to switch to an imported table, and a
        case that stopped doing so would be a silent regression.
        """

        if self.is_abrupt:
            return "abrupt"
        if self.render_request == "imported" or self.overlap:
            return "imported_profile"
        return "native_linear"

    def well_widths_nm(self) -> tuple[float, float]:
        return chi2mod.well_widths_from_asymmetry(
            float(self.asymmetry_s), TOTAL_WELL_NM
        )

    def build_widths_nm(self) -> tuple[float, float]:
        """The 10-90 widths handed to the production profile builder."""

        if self.is_abrupt:
            return ABRUPT_SENTINEL_WIDTH_NM, ABRUPT_SENTINEL_WIDTH_NM
        return float(self.left_grading_width_nm), float(self.right_grading_width_nm)

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

    def as_record(self) -> dict[str, Any]:
        well_1, well_2 = self.well_widths_nm()
        build_left, build_right = self.build_widths_nm()
        return {
            **asdict(self),
            "well_1_nm": well_1,
            "well_2_nm": well_2,
            "total_gaas_well_nm": well_1 + well_2,
            "expected_representation": self.expected_representation,
            "build_left_grading_width_nm": build_left,
            "build_right_grading_width_nm": build_right,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
            "linear_ramp_span_nm": self.ramp_span_nm(),
            "overlap_width_nm": self.overlap_width_nm(),
            "is_reference_case": self.case_id == REFERENCE_CASE_ID,
        }


def all_cases() -> list[GeometryCase]:
    """The ten fixed structures, in the order every table and plot uses."""

    cases = [
        GeometryCase(
            "case_01", "reference_graded",
            "Paper-like 7.10 / 1.80 / 2.90 nm with 0.70 nm linear grades; the "
            "reference every energy shift is measured against.",
            PAPER_ASYMMETRY, 1.80, 0.70, 0.70,
        ),
        GeometryCase(
            "case_02", "abrupt_reference",
            "Case 01's layer geometry with abrupt interfaces and no grading.",
            PAPER_ASYMMETRY, 1.80, 0.0, 0.0, interface_mode="abrupt",
        ),
        GeometryCase(
            "case_03", "thin_barrier",
            "0.85 nm central barrier with 0.40 nm grades; strongest coupling.",
            PAPER_ASYMMETRY, 0.85, 0.40, 0.40,
        ),
        GeometryCase(
            "case_04", "thick_barrier",
            "2.50 nm central barrier with reference 0.70 nm grades.",
            PAPER_ASYMMETRY, 2.50, 0.70, 0.70,
        ),
        GeometryCase(
            "case_05", "low_asymmetry",
            "The fixed 10 nm GaAs total redistributed as s=0.30 (6.50 / 3.50 nm).",
            0.30, 1.80, 0.70, 0.70,
        ),
        GeometryCase(
            "case_06", "high_asymmetry",
            "The fixed 10 nm GaAs total redistributed as s=0.55 (7.75 / 2.25 nm).",
            0.55, 1.80, 0.70, 0.70,
        ),
        GeometryCase(
            "case_07", "asymmetric_grading",
            "Independent 0.40 / 1.40 nm grades on a 2.50 nm barrier, non-overlapping.",
            PAPER_ASYMMETRY, 2.50, 0.40, 1.40,
        ),
        GeometryCase(
            "case_08", "controlled_overlap",
            "1.40 / 1.40 nm grades across a 0.85 nm barrier; the grades overlap and "
            "the barrier never reaches Al0.55.",
            PAPER_ASYMMETRY, 0.85, 1.40, 1.40, overlap=True,
        ),
        GeometryCase(
            "case_09", "native_linear_wide_grade",
            "Reference layers with 1.00 nm grades, written as native ternary_linear "
            "ramps; the native half of the equivalence pair.",
            PAPER_ASYMMETRY, 1.80, 1.00, 1.00,
        ),
        GeometryCase(
            "case_10", "imported_linear_equivalent",
            "The same structure as case_09 written as an imported composition "
            "table; the imported half of the equivalence pair.",
            PAPER_ASYMMETRY, 1.80, 1.00, 1.00, render_request="imported",
        ),
    ]
    validate_cases(cases)
    return cases


def reference_case() -> GeometryCase:
    return next(case for case in all_cases() if case.case_id == REFERENCE_CASE_ID)


def equivalence_pair() -> tuple[str, str]:
    """(native, imported) case ids that must describe one structure."""

    return "case_09", "case_10"


def abrupt_vs_graded_pair() -> tuple[str, str]:
    """(graded, abrupt) case ids that share one layer geometry."""

    return "case_01", "case_02"


def validate_cases(cases: list[GeometryCase]) -> None:
    """Everything the fixed list must satisfy before a deck is ever written."""

    expected_ids = [f"case_{index:02d}" for index in range(1, CASE_COUNT + 1)]
    if [case.case_id for case in cases] != expected_ids:
        raise Cases16EError(
            f"expected {expected_ids}, got {[c.case_id for c in cases]}."
        )
    if any(case.grading_profile != GRADING_PROFILE for case in cases):
        raise Cases16EError("Demo 16E studies the linear grading family only.")
    for case in cases:
        if case.interface_mode not in INTERFACE_MODES:
            raise Cases16EError(f"{case.case_id}: unknown interface mode.")
        if case.render_request not in RENDER_REQUESTS:
            raise Cases16EError(f"{case.case_id}: unknown render request.")
        if not ASYMMETRY_BOUNDS[0] <= case.asymmetry_s <= ASYMMETRY_BOUNDS[1]:
            raise Cases16EError(f"{case.case_id}: asymmetry outside bounds.")
        if not BARRIER_BOUNDS_NM[0] <= case.central_barrier_nm <= BARRIER_BOUNDS_NM[1]:
            raise Cases16EError(f"{case.case_id}: barrier outside bounds.")
        for width in (case.left_grading_width_nm, case.right_grading_width_nm):
            if case.is_abrupt:
                if width != 0.0:
                    raise Cases16EError(
                        f"{case.case_id}: an abrupt case must report 0.0 grading width."
                    )
            elif not GRADING_BOUNDS_NM[0] <= width <= GRADING_BOUNDS_NM[1]:
                raise Cases16EError(f"{case.case_id}: grading width outside bounds.")
        if case.is_abrupt and case.render_request != "auto":
            raise Cases16EError(
                f"{case.case_id}: an abrupt case has its own renderer and cannot "
                "also request an imported table."
            )
        if abs(sum(case.well_widths_nm()) - TOTAL_WELL_NM) > 1e-12:
            raise Cases16EError(f"{case.case_id}: total GaAs well thickness changed.")
        geometric_overlap = case.overlap_width_nm() > 1e-12
        if geometric_overlap != case.overlap:
            raise Cases16EError(
                f"{case.case_id}: overlap flag {case.overlap} disagrees with geometry."
            )
        if case.expected_representation not in REPRESENTATIONS:
            raise Cases16EError(f"{case.case_id}: unknown representation.")
    if sum(case.overlap for case in cases) != 1:
        raise Cases16EError("Demo 16E contains exactly one overlapping case.")
    if sum(case.is_abrupt for case in cases) != 1:
        raise Cases16EError("Demo 16E contains exactly one abrupt case.")
    if cases[0].case_id != REFERENCE_CASE_ID:
        raise Cases16EError("case_01 must be the reference case.")

    native_id, imported_id = equivalence_pair()
    by_id = {case.case_id: case for case in cases}
    native, imported = by_id[native_id], by_id[imported_id]
    shared = (
        "asymmetry_s", "central_barrier_nm", "left_grading_width_nm",
        "right_grading_width_nm", "grading_profile", "interface_mode",
    )
    differing = [key for key in shared if getattr(native, key) != getattr(imported, key)]
    if differing:
        raise Cases16EError(
            f"the equivalence pair must describe one structure; {differing} differ."
        )
    if (native.expected_representation, imported.expected_representation) != (
        "native_linear", "imported_profile"
    ):
        raise Cases16EError(
            "the equivalence pair must be one native and one imported rendering."
        )

    graded_id, abrupt_id = abrupt_vs_graded_pair()
    graded, sharp = by_id[graded_id], by_id[abrupt_id]
    if (graded.asymmetry_s, graded.central_barrier_nm) != (
        sharp.asymmetry_s, sharp.central_barrier_nm
    ):
        raise Cases16EError(
            "the abrupt-vs-graded pair must share one layer geometry."
        )
    if not sharp.is_abrupt or graded.is_abrupt:
        raise Cases16EError(
            "the abrupt-vs-graded pair must be exactly one graded and one abrupt case."
        )


def write_cases_file(path: Path) -> Path:
    cases = all_cases()
    payload = {
        "demo": DEMO_ID,
        "purpose": (
            "Ten fixed ACQW structures compared through composition, quantum "
            "states, wavefunction localization and the production absolute chi2 "
            "response around 1550 nm."
        ),
        "total_cases": CASE_COUNT,
        "deterministic": True,
        "optimization_performed": False,
        "random_seed": None,
        "grading_profile": GRADING_PROFILE,
        "grading_families_supported": [GRADING_PROFILE],
        "reference_case": REFERENCE_CASE_ID,
        "equivalence_pair": list(equivalence_pair()),
        "abrupt_vs_graded_pair": list(abrupt_vs_graded_pair()),
        "fixed_materials": {
            "well": "GaAs", "barrier": "AlGaAs",
            "aluminium_fraction": AL_FRACTION,
            "total_gaas_well_nm": TOTAL_WELL_NM,
            "mesh_nm": MESH_NM,
            "target_wavelength_nm": TARGET_WAVELENGTH_NM,
        },
        "abrupt_sentinel_width_nm": ABRUPT_SENTINEL_WIDTH_NM,
        "cases": [case.as_record() for case in cases],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8", newline="\n",
    )
    return path


def load_cases(path: Path) -> list[GeometryCase]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fields = set(GeometryCase.__dataclass_fields__)
    cases = [
        GeometryCase(**{key: value for key, value in row.items() if key in fields})
        for row in payload["cases"]
    ]
    validate_cases(cases)
    return cases


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / CASES_FILENAME
    print(write_cases_file(target))
