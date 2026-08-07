"""Demo 16C's four fixed cases: one geometry, one grading family, one variable.

Demo 16 sweeps twenty cases over four profile families and a seeded interior.
Demo 16B does eight. Demo 16C does **four**, and everything except the linear
grading width is nailed down:

    thick well 7.1 nm | central barrier 1.8 nm | thin well 2.9 nm, x_Al = 0.55

The four cases differ in exactly one respect -- the 10-90% width of the linear
composition ramp at the two central-barrier interfaces. If the realized
nextnano++ composition of case 03 is not visibly softer than case 01's, the
grading input is not reaching the simulator, and that single statement is what
Demo 16C exists to test.

**Which width drives which interface.** ``grading14`` names its two widths by
*interface type*, not by spatial side, because a growth process grades an
interface according to what is being grown:

===========================  ==============================  ================
interface (increasing z)     type                            driven by
===========================  ==============================  ================
outer left    (z1)           AlGaAs -> GaAs, Al falls        ``right`` width
central left  (z2)           GaAs -> AlGaAs, Al rises        ``left`` width
central right (z3)           AlGaAs -> GaAs, Al falls        ``right`` width
outer right   (z4)           GaAs -> AlGaAs, Al rises        ``left`` width
===========================  ==============================  ================

``left_grading_width_nm`` and ``right_grading_width_nm`` below are named for the
**central barrier**, which is what the four cases are about. Case 04 therefore
shows its asymmetry twice: sharp at the barrier's left edge and soft at its
right, and mirrored at the two outer interfaces. That is the production
convention faithfully reproduced, not a bug in the case list.

**No overlap anywhere.** A linear 10-90 width ``w`` occupies ``1.25 w`` of
physical space (the linear CDF spans 0 -> 1 over one natural scale and the 10-90
portion is 0.8 of it). Two interfaces separated by ``L`` stay disjoint while
``0.625 (w_left + w_right) < L``. The tightest layer here is the 1.8 nm barrier,
and the widest case asks 0.625 * (1.00 + 1.00) = 1.25 nm, leaving 0.55 nm of
margin. Every case renders through the native ``ternary_linear{}`` path; none
falls back to an imported table. Overlap belongs to Demo 16 and Demo 17.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import yaml

import chi2 as chi2mod

CASES_FILENAME = "validation_cases.yaml"

#: The only grading family Demo 16C supports. A constraint, not a default.
GRADING_PROFILE = "linear"

#: The fixed paper-like ACQW. These three numbers never vary across the demo.
THICK_WELL_NM = 7.1
CENTRAL_BARRIER_NM = 1.8
THIN_WELL_NM = 2.9

#: Fixed scientific values.
TOTAL_WELL_NM = THICK_WELL_NM + THIN_WELL_NM      # 10.0
AL_FRACTION = 0.55
MESH_NM = 0.05

#: Converted through the authoritative production formula rather than asserted:
#: s = (7.1 - 2.9) / (7.1 + 2.9) = 0.42 exactly. Demo 14's geometry function
#: takes ``asymmetry_s``, so this is how 7.1 / 2.9 is expressed to it.
PAPER_ASYMMETRY = chi2mod.structural_asymmetry(THICK_WELL_NM, THIN_WELL_NM)

#: Physical extent of one linear 10-90 transition, as a multiple of that width.
LINEAR_RAMP_SPAN_PER_10_90 = 1.25

#: Smallest 10-90 width the production renderer accepts. ``grading14`` has no
#: abrupt branch -- ``ProfileFamily.scale_for`` refuses a width of zero -- so the
#: near-abrupt end of the comparison is the bottom of the Demo 14 range.
MINIMUM_GRADING_NM = 0.40

#: Demo 14 beta ranges. A Demo 16C width outside these would validate something
#: no production campaign can ask for.
GRADING_WIDTH_BOUNDS = (0.40, 1.40)


class Cases16CError(ValueError):
    """A case list that violates one of Demo 16C's own invariants."""


@dataclass(frozen=True)
class GradingCase:
    """One Demo 16C design. Four fields vary; the rest of the world is fixed."""

    case_id: str
    name: str
    purpose: str
    #: 10-90 width of the GaAs -> AlGaAs ramp = the central barrier's LEFT edge.
    left_grading_width_nm: float
    #: 10-90 width of the AlGaAs -> GaAs ramp = the central barrier's RIGHT edge.
    right_grading_width_nm: float
    #: Selected for the optional two-case licensed physics check.
    physics: bool = False
    grading_profile: str = GRADING_PROFILE

    def parameters(self) -> dict[str, Any]:
        """Exactly the mapping Demo 14's geometry and renderer consume.

        Asymmetry and barrier thickness are constants here, which is the whole
        point: they are not case fields, so no case can accidentally move them.
        """

        return {
            "asymmetry_s": PAPER_ASYMMETRY,
            "nominal_central_barrier_thickness_nm": CENTRAL_BARRIER_NM,
            "gaas_to_algaas_grading_width_10_90_nm": float(self.left_grading_width_nm),
            "algaas_to_gaas_grading_width_10_90_nm": float(self.right_grading_width_nm),
            "grading_profile": self.grading_profile,
        }

    # Production-facing aliases.  Demo 14 names widths by interface *type*;
    # Demo 16C names them by the two sides of the central barrier for clarity.
    @property
    def asymmetry_s(self) -> float:
        return PAPER_ASYMMETRY

    @property
    def nominal_central_barrier_thickness_nm(self) -> float:
        return CENTRAL_BARRIER_NM

    @property
    def gaas_to_algaas_grading_width_10_90_nm(self) -> float:
        return float(self.left_grading_width_nm)

    @property
    def algaas_to_gaas_grading_width_10_90_nm(self) -> float:
        return float(self.right_grading_width_nm)

    @property
    def physics_label(self) -> str:
        return {"case_01": "A", "case_03": "B"}.get(self.case_id, "")

    def well_widths_nm(self) -> tuple[float, float]:
        """d_thick, d_thin from the authoritative formula. Never recomputed."""

        return chi2mod.well_widths_from_asymmetry(PAPER_ASYMMETRY, TOTAL_WELL_NM)

    def is_symmetric(self) -> bool:
        return (
            abs(self.left_grading_width_nm - self.right_grading_width_nm) < 1e-12
        )

    def ramp_span_nm(self) -> float:
        """Physical space the two ramps bounding one layer need together."""

        return 0.5 * LINEAR_RAMP_SPAN_PER_10_90 * (
            float(self.left_grading_width_nm) + float(self.right_grading_width_nm)
        )

    def non_overlap_margin_nm(self) -> float:
        """Slack in the no-overlap condition at the tightest layer.

        Must be > 0 for a Demo 16C case; the tightest layer is the 1.8 nm
        central barrier for every one of them.
        """

        tightest = min(THICK_WELL_NM, CENTRAL_BARRIER_NM, THIN_WELL_NM)
        return tightest - self.ramp_span_nm()

    def as_record(self) -> dict[str, Any]:
        thick, thin = self.well_widths_nm()
        record = asdict(self)
        record.update({
            "derived_thick_well_nm": thick,
            "derived_central_barrier_nm": CENTRAL_BARRIER_NM,
            "derived_thin_well_nm": thin,
            "asymmetry_s": PAPER_ASYMMETRY,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
            "symmetric_grading": self.is_symmetric(),
            "linear_ramp_span_nm": self.ramp_span_nm(),
            "non_overlap_margin_nm": self.non_overlap_margin_nm(),
        })
        return record


def all_cases() -> list[GradingCase]:
    """The four fixed cases. Same objects, same numbers, every run."""

    cases = [
        GradingCase(
            case_id="case_01",
            name="near_abrupt_minimum_grading",
            purpose=(
                f"Sharpest interface the production renderer accepts "
                f"({MINIMUM_GRADING_NM} nm 10-90 on both sides). The near-abrupt "
                "end of the comparison."
            ),
            left_grading_width_nm=MINIMUM_GRADING_NM,
            right_grading_width_nm=MINIMUM_GRADING_NM,
            physics=True,
        ),
        GradingCase(
            case_id="case_02",
            name="medium_grading",
            purpose=(
                "0.70 nm on both sides. An intermediate linear transition, "
                "halfway between cases 01 and 03."
            ),
            left_grading_width_nm=0.70,
            right_grading_width_nm=0.70,
        ),
        GradingCase(
            case_id="case_03",
            name="wider_grading",
            purpose=(
                "1.00 nm on both sides. Visibly softer than case 01 and still "
                "clearly non-overlapping across the 1.8 nm barrier "
                "(0.55 nm of margin)."
            ),
            left_grading_width_nm=1.00,
            right_grading_width_nm=1.00,
            physics=True,
        ),
        GradingCase(
            case_id="case_04",
            name="asymmetric_grading",
            purpose=(
                "0.40 nm left, 1.00 nm right, same geometry as every other "
                "case. Proves the two central interfaces are controlled "
                "independently -- and, because the two outer interfaces take "
                "the same widths by interface TYPE, the asymmetry appears "
                "mirrored at the outer barriers too."
            ),
            left_grading_width_nm=MINIMUM_GRADING_NM,
            right_grading_width_nm=1.00,
        ),
    ]
    validate_cases(cases)
    return cases


def physics_cases() -> list[GradingCase]:
    """The two cases in the optional licensed physics check.

    Case 01 (sharpest) and case 03 (widest) bracket the grading range. The
    check asks only whether both graded structures can be solved at all, so two
    endpoints answer it and a third would spend licensed time proving nothing.
    """

    selected = [c for c in all_cases() if c.physics]
    if len(selected) != 2:
        raise Cases16CError(
            f"Demo 16C solves exactly 2 cases, selected {len(selected)}."
        )
    return selected


def validate_cases(cases: list[GradingCase]) -> None:
    """The invariants that make this a Demo 16C case list and not some other."""

    if len(cases) != 4:
        raise Cases16CError(f"Demo 16C requires exactly 4 cases, built {len(cases)}.")
    if len({c.case_id for c in cases}) != 4:
        raise Cases16CError("duplicate case ids.")
    lo, hi = GRADING_WIDTH_BOUNDS
    for case in cases:
        if case.grading_profile != GRADING_PROFILE:
            raise Cases16CError(
                f"{case.case_id}: Demo 16C is linear only, got "
                f"{case.grading_profile!r}."
            )
        for side, width in (
            ("left", case.left_grading_width_nm),
            ("right", case.right_grading_width_nm),
        ):
            if not lo - 1e-9 <= width <= hi + 1e-9:
                raise Cases16CError(
                    f"{case.case_id}: {side} width {width} outside the Demo 14 "
                    f"range [{lo}, {hi}]."
                )
        if case.non_overlap_margin_nm() <= 0.0:
            raise Cases16CError(
                f"{case.case_id}: ramps span {case.ramp_span_nm():.3f} nm across a "
                f"{CENTRAL_BARRIER_NM} nm barrier, so the two grades overlap. "
                "Demo 16C does not test overlap; that is Demo 16 / Demo 17."
            )
    if sum(1 for c in cases if not c.is_symmetric()) != 1:
        raise Cases16CError(
            "Demo 16C expects exactly one asymmetric case (case 04)."
        )


def write_cases_file(path: Path) -> Path:
    """Freeze the resolved case table with explicit numbers."""

    cases = all_cases()
    payload = {
        "demo": "16C_minimal_linear_grading_validation",
        "purpose": (
            "Prove that changing a linear AlGaAs grading width in Python changes "
            "the alloy composition profile nextnano++ actually constructs."
        ),
        "total_cases": len(cases),
        "grading_profile": GRADING_PROFILE,
        "grading_families_supported": [GRADING_PROFILE],
        "deterministic": True,
        "random_seed": None,
        "fixed_geometry": {
            "thick_well_nm": THICK_WELL_NM,
            "central_barrier_nm": CENTRAL_BARRIER_NM,
            "thin_well_nm": THIN_WELL_NM,
            "total_well_thickness_nm": TOTAL_WELL_NM,
            "asymmetry_s": PAPER_ASYMMETRY,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
        },
        "grading_width_bounds_nm": list(GRADING_WIDTH_BOUNDS),
        "width_to_interface_map": {
            "outer_left_algaas_to_gaas": "right_grading_width_nm",
            "central_gaas_to_algaas": "left_grading_width_nm",
            "central_algaas_to_gaas": "right_grading_width_nm",
            "outer_right_gaas_to_algaas": "left_grading_width_nm",
        },
        "physics_cases": [c.case_id for c in physics_cases()],
        "cases": [c.as_record() for c in cases],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8", newline="\n",
    )
    return path


def load_cases(path: Path) -> list[GradingCase]:
    """Read the frozen table. The file, not the generator, is authoritative."""

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fields = set(GradingCase.__dataclass_fields__)
    cases = [
        GradingCase(**{k: v for k, v in record.items() if k in fields})
        for record in payload["cases"]
    ]
    validate_cases(cases)
    return cases


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / CASES_FILENAME
    write_cases_file(target)
    print(f"wrote {target}")
    for case in all_cases():
        thick, thin = case.well_widths_nm()
        print(
            f"  {case.case_id}  {case.name:<28} {case.grading_profile:<7} "
            f"left={case.left_grading_width_nm:.2f} "
            f"right={case.right_grading_width_nm:.2f}  "
            f"wells={thick:.1f}/{CENTRAL_BARRIER_NM:.1f}/{thin:.1f} "
            f"margin={case.non_overlap_margin_nm():+.3f} nm"
            + ("  [physics]" if case.physics else "")
        )
