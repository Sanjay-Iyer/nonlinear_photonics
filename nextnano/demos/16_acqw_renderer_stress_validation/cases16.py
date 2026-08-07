"""Demo 16's twenty fixed validation cases.

The case list is a **regression fixture, not a sample**. It is generated once,
written to ``validation_cases.yaml`` with explicit numbers, and thereafter read
from that file. Regenerating different geometries on every run would make a
failure impossible to reproduce and a pass impossible to trust.

Twelve cases are chosen deliberately to sit on boundaries, corners and known
failure modes. Eight are drawn from a seeded generator (seed 1616) to cover the
interior, with the draw rejected and retried if it lands too close to a
deliberate case -- random points that merely duplicate the corners would add
cost without adding coverage.

Every case is expressed in the Demo 14 parameterization and resolved through
Demo 14's own geometry functions. Demo 16 never recomputes a well width.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import yaml

import chi2 as chi2mod

#: Fixed. Changing this changes the fixture and must be a deliberate act.
SEED = 1616

CASES_FILENAME = "validation_cases.yaml"

#: Demo 14 beta ranges. Demo 16 validates exactly this space.
BOUNDS: Mapping[str, tuple[float, float]] = {
    "asymmetry_s": (0.30, 0.55),
    "nominal_central_barrier_thickness_nm": (0.85, 2.50),
    "gaas_to_algaas_grading_width_10_90_nm": (0.40, 1.40),
    "algaas_to_gaas_grading_width_10_90_nm": (0.40, 1.40),
}
PROFILES = ("linear", "fermi", "erf", "cosine")

#: Fixed scientific values for the whole demo.
TOTAL_WELL_NM = 10.0
AL_FRACTION = 0.55
MESH_NM = 0.05

#: Paper geometry, converted through the authoritative formula rather than
#: asserted: s = (7.1 - 2.9) / (7.1 + 2.9) = 0.42 exactly.
PAPER_ASYMMETRY = chi2mod.structural_asymmetry(7.1, 2.9)

#: Mid-range values used wherever a case says "moderate", so that a case varying
#: one parameter really does hold the others fixed.
MODERATE = {
    "asymmetry_s": PAPER_ASYMMETRY,
    "nominal_central_barrier_thickness_nm": 1.80,
    "gaas_to_algaas_grading_width_10_90_nm": 0.90,
    "algaas_to_gaas_grading_width_10_90_nm": 0.90,
}


@dataclass(frozen=True)
class ValidationCase:
    case_id: str
    name: str
    origin: str                     # "deliberate" | "seeded_random"
    purpose: str
    asymmetry_s: float
    nominal_central_barrier_thickness_nm: float
    gaas_to_algaas_grading_width_10_90_nm: float
    algaas_to_gaas_grading_width_10_90_nm: float
    grading_profile: str
    level3: bool = False            # selected for optional licensed physics

    def parameters(self) -> dict[str, Any]:
        """Exactly the mapping Demo 14's geometry and renderer consume."""

        return {
            "asymmetry_s": self.asymmetry_s,
            "nominal_central_barrier_thickness_nm": (
                self.nominal_central_barrier_thickness_nm
            ),
            "gaas_to_algaas_grading_width_10_90_nm": (
                self.gaas_to_algaas_grading_width_10_90_nm
            ),
            "algaas_to_gaas_grading_width_10_90_nm": (
                self.algaas_to_gaas_grading_width_10_90_nm
            ),
            "grading_profile": self.grading_profile,
        }

    def well_widths_nm(self) -> tuple[float, float]:
        return chi2mod.well_widths_from_asymmetry(self.asymmetry_s, TOTAL_WELL_NM)

    def as_record(self) -> dict[str, Any]:
        thick, thin = self.well_widths_nm()
        record = asdict(self)
        record.update({
            "derived_thick_well_nm": thick,
            "derived_thin_well_nm": thin,
            "total_well_thickness_nm": TOTAL_WELL_NM,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
        })
        return record


def _case(index: int, name: str, purpose: str, *, origin: str = "deliberate",
          profile: str = "linear", level3: bool = False, **overrides: float
          ) -> ValidationCase:
    values = dict(MODERATE)
    values.update(overrides)
    return ValidationCase(
        case_id=f"case_{index:02d}",
        name=name,
        origin=origin,
        purpose=purpose,
        grading_profile=profile,
        level3=level3,
        **values,
    )


def deliberate_cases() -> list[ValidationCase]:
    """The twelve chosen cases: boundaries, corners and known failure modes."""

    return [
        _case(1, "paper_reference",
              "7.1 / 1.8 / 2.9 nm converted through the authoritative asymmetry "
              "formula. The primary structural regression case.",
              asymmetry_s=PAPER_ASYMMETRY,
              nominal_central_barrier_thickness_nm=1.80,
              gaas_to_algaas_grading_width_10_90_nm=1.00,
              algaas_to_gaas_grading_width_10_90_nm=1.00,
              level3=True),
        _case(2, "minimum_barrier",
              "Thinnest allowed central barrier.",
              nominal_central_barrier_thickness_nm=0.85, level3=True),
        _case(3, "maximum_barrier",
              "Thickest central barrier; a clearly separated plateau must exist.",
              nominal_central_barrier_thickness_nm=2.50, level3=True),
        _case(4, "minimum_left_grade",
              "Sharpest GaAs->AlGaAs interface.",
              gaas_to_algaas_grading_width_10_90_nm=0.40),
        _case(5, "maximum_left_grade",
              "Widest GaAs->AlGaAs interface.",
              gaas_to_algaas_grading_width_10_90_nm=1.40),
        _case(6, "minimum_right_grade",
              "Sharpest AlGaAs->GaAs interface.",
              algaas_to_gaas_grading_width_10_90_nm=0.40),
        _case(7, "maximum_right_grade",
              "Widest AlGaAs->GaAs interface.",
              algaas_to_gaas_grading_width_10_90_nm=1.40),
        _case(8, "both_grades_minimum",
              "Near-abrupt structure at both central interfaces.",
              gaas_to_algaas_grading_width_10_90_nm=0.40,
              algaas_to_gaas_grading_width_10_90_nm=0.40),
        _case(9, "maximum_overlap_linear",
              "Widest grades across the thinnest barrier. The renderer must NOT "
              "fabricate a flat Al=0.55 plateau; the two ramps genuinely "
              "overlap and the peak composition falls short of nominal.",
              nominal_central_barrier_thickness_nm=0.85,
              gaas_to_algaas_grading_width_10_90_nm=1.40,
              algaas_to_gaas_grading_width_10_90_nm=1.40,
              level3=True),
        _case(10, "low_asymmetry_boundary",
              "Lower asymmetry bound.", asymmetry_s=0.30, level3=True),
        _case(11, "high_asymmetry_boundary",
              "Upper asymmetry bound.", asymmetry_s=0.55),
        _case(12, "asymmetric_grading_widths",
              "Narrow left, wide right. Proves the two interfaces are handled "
              "independently and localised correctly -- the check that would "
              "have caught well widths being reported as grading widths.",
              gaas_to_algaas_grading_width_10_90_nm=0.40,
              algaas_to_gaas_grading_width_10_90_nm=1.40),
    ]


def _too_close(candidate: Mapping[str, float],
               existing: Iterable[Mapping[str, float]]) -> bool:
    """Reject a draw that merely repeats a case we already have.

    Distance is measured in normalised parameter units so each axis counts
    equally regardless of its physical range.
    """

    for other in existing:
        distance = 0.0
        for name, (lo, hi) in BOUNDS.items():
            span = hi - lo
            distance += ((candidate[name] - other[name]) / span) ** 2
        if distance ** 0.5 < 0.25:
            return True
    return False


def seeded_cases(seed: int = SEED) -> list[ValidationCase]:
    """Eight interior designs, deterministic in ``seed``.

    Every profile family is represented, and one draw is forced into the
    thin-barrier/wide-grade corner so the imported-profile overlap path is
    exercised by a random case as well as by case 09.
    """

    rng = np.random.default_rng(seed)
    fixed = [c.parameters() for c in deliberate_cases()]
    chosen: list[ValidationCase] = []
    # Two of each family, so no family can look better or worse merely through
    # being sampled more often.
    families = ["fermi", "erf", "cosine", "linear", "fermi", "erf", "cosine", "linear"]

    index = 13
    for position, family in enumerate(families):
        for _ in range(500):
            candidate = {
                name: float(rng.uniform(lo, hi))
                for name, (lo, hi) in BOUNDS.items()
            }
            # Case 16 in the spec: one nonlinear profile deliberately pushed into
            # the overlap corner.
            if position == 3:
                candidate["nominal_central_barrier_thickness_nm"] = float(
                    rng.uniform(0.85, 1.10))
                candidate["gaas_to_algaas_grading_width_10_90_nm"] = float(
                    rng.uniform(1.20, 1.40))
                candidate["algaas_to_gaas_grading_width_10_90_nm"] = float(
                    rng.uniform(1.20, 1.40))
            if not _too_close(candidate, fixed + [c.parameters() for c in chosen]):
                break
        chosen.append(ValidationCase(
            case_id=f"case_{index:02d}",
            name=f"seeded_interior_{position + 1:02d}_{family}",
            origin="seeded_random",
            purpose=(
                "Deterministic interior design from seed "
                f"{seed}, rejected if within 0.25 normalised units of an "
                "existing case."
            ),
            grading_profile=family,
            level3=(position in (0, 1, 7)),
            **{k: round(v, 6) for k, v in candidate.items()},
        ))
        index += 1
    return chosen


def all_cases() -> list[ValidationCase]:
    cases = deliberate_cases() + seeded_cases()
    if len(cases) != 20:
        raise ValueError(f"Demo 16 requires exactly 20 cases, built {len(cases)}.")
    return cases


def write_cases_file(path: Path) -> Path:
    """Freeze the resolved case table with explicit numbers."""

    cases = all_cases()
    payload = {
        "seed": SEED,
        "total_cases": len(cases),
        "deliberate_cases": sum(1 for c in cases if c.origin == "deliberate"),
        "seeded_random_cases": sum(1 for c in cases if c.origin == "seeded_random"),
        "bounds": {k: list(v) for k, v in BOUNDS.items()},
        "fixed": {
            "total_well_thickness_nm": TOTAL_WELL_NM,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
            "target_wavelength_nm": 1550.0,
            "broadening_meV": 5.0,
        },
        "paper_asymmetry_s": PAPER_ASYMMETRY,
        "cases": [c.as_record() for c in cases],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8", newline="\n",
    )
    return path


def load_cases(path: Path) -> list[ValidationCase]:
    """Read the frozen table. The file, not the generator, is authoritative."""

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fields = {f for f in ValidationCase.__dataclass_fields__}
    return [
        ValidationCase(**{k: v for k, v in record.items() if k in fields})
        for record in payload["cases"]
    ]


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / CASES_FILENAME
    write_cases_file(target)
    print(f"wrote {target}")
    for case in all_cases():
        thick, thin = case.well_widths_nm()
        print(
            f"  {case.case_id}  {case.name:<34} {case.grading_profile:<7} "
            f"s={case.asymmetry_s:.4f} b={case.nominal_central_barrier_thickness_nm:.2f} "
            f"w={case.gaas_to_algaas_grading_width_10_90_nm:.2f}/"
            f"{case.algaas_to_gaas_grading_width_10_90_nm:.2f} "
            f"wells={thick:.3f}/{thin:.3f}"
            + ("  [L3]" if case.level3 else "")
        )
