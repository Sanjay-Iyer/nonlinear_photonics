"""Seven fixed, deterministic linear-grading geometry cases for Demo 16D."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

import chi2 as chi2mod

CASES_FILENAME = "validation_cases.yaml"
DEMO_ID = "16D_acqw_linear_grading_geometry_validation"
GRADING_PROFILE = "linear"
TOTAL_WELL_NM = 10.0
AL_FRACTION = 0.55
MESH_NM = 0.05
PAPER_ASYMMETRY = chi2mod.structural_asymmetry(7.1, 2.9)
LINEAR_RAMP_SPAN_PER_10_90 = 1.25
ASYMMETRY_BOUNDS = (0.30, 0.55)
BARRIER_BOUNDS_NM = (0.85, 2.50)
GRADING_BOUNDS_NM = (0.40, 1.40)


class Cases16DError(ValueError):
    """The frozen Demo 16D case list violates its small validation design."""


@dataclass(frozen=True)
class GeometryCase:
    case_id: str
    name: str
    description: str
    asymmetry_s: float
    central_barrier_nm: float
    left_grading_width_nm: float
    right_grading_width_nm: float
    physics: bool = False
    overlap: bool = False
    grading_profile: str = GRADING_PROFILE

    @property
    def nominal_central_barrier_thickness_nm(self) -> float:
        return float(self.central_barrier_nm)

    @property
    def gaas_to_algaas_grading_width_10_90_nm(self) -> float:
        return float(self.left_grading_width_nm)

    @property
    def algaas_to_gaas_grading_width_10_90_nm(self) -> float:
        return float(self.right_grading_width_nm)

    @property
    def physics_label(self) -> str:
        return self.case_id.replace("case_", "P") if self.physics else ""

    def well_widths_nm(self) -> tuple[float, float]:
        return chi2mod.well_widths_from_asymmetry(
            float(self.asymmetry_s), TOTAL_WELL_NM
        )

    def parameters(self) -> dict[str, Any]:
        return {
            "asymmetry_s": float(self.asymmetry_s),
            "nominal_central_barrier_thickness_nm": float(self.central_barrier_nm),
            "gaas_to_algaas_grading_width_10_90_nm": float(
                self.left_grading_width_nm
            ),
            "algaas_to_gaas_grading_width_10_90_nm": float(
                self.right_grading_width_nm
            ),
            "grading_profile": self.grading_profile,
        }

    def ramp_span_nm(self) -> float:
        return 0.5 * LINEAR_RAMP_SPAN_PER_10_90 * (
            float(self.left_grading_width_nm)
            + float(self.right_grading_width_nm)
        )

    def overlap_width_nm(self) -> float:
        return max(0.0, self.ramp_span_nm() - float(self.central_barrier_nm))

    def as_record(self) -> dict[str, Any]:
        well_1, well_2 = self.well_widths_nm()
        return {
            **asdict(self),
            "well_1_nm": well_1,
            "well_2_nm": well_2,
            "total_gaas_well_nm": well_1 + well_2,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
            "linear_ramp_span_nm": self.ramp_span_nm(),
            "overlap_width_nm": self.overlap_width_nm(),
        }


def all_cases() -> list[GeometryCase]:
    cases = [
        GeometryCase(
            "case_01", "reference", "Paper-like 7.1 / 1.8 / 2.9 nm baseline.",
            PAPER_ASYMMETRY, 1.80, 0.70, 0.70, physics=True,
        ),
        GeometryCase(
            "case_02", "thin_barrier",
            "Thin 0.85 nm barrier with conservative non-overlapping grades.",
            PAPER_ASYMMETRY, 0.85, 0.40, 0.40, physics=True,
        ),
        GeometryCase(
            "case_03", "thick_barrier",
            "Thick 2.50 nm barrier; otherwise reference-like.",
            PAPER_ASYMMETRY, 2.50, 0.70, 0.70,
        ),
        GeometryCase(
            "case_04", "low_asymmetry",
            "Redistribute the fixed 10 nm GaAs total with s=0.30.",
            0.30, 1.80, 0.70, 0.70,
        ),
        GeometryCase(
            "case_05", "high_asymmetry",
            "Redistribute the fixed 10 nm GaAs total with s=0.55.",
            0.55, 1.80, 0.70, 0.70, physics=True,
        ),
        GeometryCase(
            "case_06", "asymmetric_grading",
            "Independent 0.40/1.40 nm grades on a non-overlapping barrier.",
            PAPER_ASYMMETRY, 2.50, 0.40, 1.40,
        ),
        GeometryCase(
            "case_07", "linear_overlap",
            "Exactly one deliberate 1.40/1.40 nm overlap across 0.85 nm.",
            PAPER_ASYMMETRY, 0.85, 1.40, 1.40,
            physics=True, overlap=True,
        ),
    ]
    validate_cases(cases)
    return cases


def physics_cases() -> list[GeometryCase]:
    selected = [case for case in all_cases() if case.physics]
    if [case.case_id for case in selected] != [
        "case_01", "case_02", "case_05", "case_07"
    ]:
        raise Cases16DError("Demo 16D must solve cases 01, 02, 05 and 07 exactly.")
    return selected


def validate_cases(cases: list[GeometryCase]) -> None:
    expected_ids = [f"case_{index:02d}" for index in range(1, 8)]
    if [case.case_id for case in cases] != expected_ids:
        raise Cases16DError(f"expected {expected_ids}, got {[c.case_id for c in cases]}.")
    if any(case.grading_profile != GRADING_PROFILE for case in cases):
        raise Cases16DError("Demo 16D supports linear grading only.")
    for case in cases:
        if not ASYMMETRY_BOUNDS[0] <= case.asymmetry_s <= ASYMMETRY_BOUNDS[1]:
            raise Cases16DError(f"{case.case_id}: asymmetry outside bounds.")
        if not BARRIER_BOUNDS_NM[0] <= case.central_barrier_nm <= BARRIER_BOUNDS_NM[1]:
            raise Cases16DError(f"{case.case_id}: barrier outside bounds.")
        for width in (case.left_grading_width_nm, case.right_grading_width_nm):
            if not GRADING_BOUNDS_NM[0] <= width <= GRADING_BOUNDS_NM[1]:
                raise Cases16DError(f"{case.case_id}: grading width outside bounds.")
        if abs(sum(case.well_widths_nm()) - TOTAL_WELL_NM) > 1e-12:
            raise Cases16DError(f"{case.case_id}: total GaAs well thickness changed.")
        geometric_overlap = case.overlap_width_nm() > 1e-12
        if geometric_overlap != case.overlap:
            raise Cases16DError(
                f"{case.case_id}: overlap flag {case.overlap} disagrees with geometry."
            )
    if sum(case.overlap for case in cases) != 1:
        raise Cases16DError("Demo 16D contains exactly one overlap case.")
    if len([case for case in cases if case.physics]) != 4:
        raise Cases16DError("Demo 16D contains exactly four physics cases.")


def write_cases_file(path: Path) -> Path:
    cases = all_cases()
    payload = {
        "demo": DEMO_ID,
        "purpose": (
            "Fixed-case validation of central-barrier thickness, well asymmetry, "
            "and one overlapping linear grade using the Demo 16C pipeline."
        ),
        "total_cases": 7,
        "deterministic": True,
        "random_seed": None,
        "grading_profile": GRADING_PROFILE,
        "grading_families_supported": [GRADING_PROFILE],
        "fixed_materials": {
            "well": "GaAs", "barrier": "AlGaAs",
            "aluminium_fraction": AL_FRACTION,
            "total_gaas_well_nm": TOTAL_WELL_NM,
            "mesh_nm": MESH_NM,
        },
        "physics_cases": [case.case_id for case in physics_cases()],
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
