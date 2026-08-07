"""Demo 16B's eight fixed validation cases -- linear grading only.

Demo 16 sweeps twenty cases across four profile families, boundary corners and a
seeded interior. Demo 16B deliberately does much less: eight hand-written
designs, one grading family, and no random draw anywhere. The point is a core
workflow that can be read end to end and checked by hand, not coverage.

Every case is expressed in the **Demo 14 parameterization** and resolved through
Demo 14's own geometry function, so ``asymmetry_s`` here means exactly what it
means in a Demo 14 campaign. Demo 16B never recomputes a well width.

The one rule that shapes every number below: no two graded interfaces may
overlap. Linear grading of 10-90 width ``w`` occupies ``1.25 w`` of physical
space centred on its interface, so two neighbouring interfaces separated by
``L`` stay disjoint only while ``0.625 (w_left + w_right) < L``. Where that
fails, the production renderer's region template would let one ramp overwrite
the other, and Demo 16B rejects the geometry rather than measuring a profile
nobody asked for. Demo 16 already covers the overlapped regime through an
imported table; keeping it out of 16B is what makes 16B simple.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping

import yaml

import chi2 as chi2mod

CASES_FILENAME = "validation_cases.yaml"

#: The only grading family Demo 16B supports. Not a default -- a constraint.
GRADING_PROFILE = "linear"

#: Fixed scientific values for the whole demo.
TOTAL_WELL_NM = 10.0
AL_FRACTION = 0.55
MESH_NM = 0.05
TARGET_WAVELENGTH_NM = 1550.0
BROADENING_MEV = 5.0

#: Demo 14 beta ranges. Demo 16B stays strictly inside the production space; a
#: case outside it would validate something no campaign can ask for.
BOUNDS: Mapping[str, tuple[float, float]] = {
    "asymmetry_s": (0.30, 0.55),
    "nominal_central_barrier_thickness_nm": (0.85, 2.50),
    "gaas_to_algaas_grading_width_10_90_nm": (0.40, 1.40),
    "algaas_to_gaas_grading_width_10_90_nm": (0.40, 1.40),
}

#: Paper geometry converted through the authoritative formula rather than
#: asserted: s = (7.1 - 2.9) / (7.1 + 2.9) = 0.42 exactly.
PAPER_ASYMMETRY = chi2mod.structural_asymmetry(7.1, 2.9)

#: What "moderate" means, so a case that varies one parameter really does hold
#: the others fixed.
MODERATE_ASYMMETRY = PAPER_ASYMMETRY
MODERATE_BARRIER_NM = 1.80
MODERATE_GRADING_NM = 0.90

#: Smallest 10-90 width the production renderer accepts. ``grading14`` has no
#: abrupt branch at all -- ``ProfileFamily.scale_for`` refuses a width of zero --
#: so the near-abrupt baseline is the bottom of the Demo 14 range, not zero.
MINIMUM_GRADING_NM = 0.40

#: Physical extent of one linear 10-90 transition, as a multiple of that width.
#: The linear CDF spans its full 0 -> 1 range over one natural scale, and the
#: 10-90 portion is 0.8 of that scale, so the full ramp is 1 / 0.8 = 1.25 w wide.
LINEAR_RAMP_SPAN_PER_10_90 = 1.25


@dataclass(frozen=True)
class SimpleCase:
    """One Demo 16B design. Frozen, explicit, and linear by construction."""

    case_id: str
    name: str
    purpose: str
    asymmetry_s: float
    nominal_central_barrier_thickness_nm: float
    gaas_to_algaas_grading_width_10_90_nm: float
    algaas_to_gaas_grading_width_10_90_nm: float
    grading_profile: str = GRADING_PROFILE
    #: Selected for a real licensed solve. Exactly three cases carry this.
    physics: bool = False
    physics_label: str = ""

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
        """d1, d2 from the authoritative production formula. Never recomputed."""

        return chi2mod.well_widths_from_asymmetry(self.asymmetry_s, TOTAL_WELL_NM)

    def minimum_layer_nm(self) -> float:
        """The shortest gap between two neighbouring graded interfaces."""

        thick, thin = self.well_widths_nm()
        return min(thick, self.nominal_central_barrier_thickness_nm, thin)

    def ramp_span_nm(self) -> float:
        """Physical space the two ramps bounding the tightest layer need."""

        return 0.5 * LINEAR_RAMP_SPAN_PER_10_90 * (
            self.gaas_to_algaas_grading_width_10_90_nm
            + self.algaas_to_gaas_grading_width_10_90_nm
        )

    def non_overlap_margin_nm(self) -> float:
        """Slack in the no-overlap condition. Must be > 0 for a 16B case."""

        return self.minimum_layer_nm() - self.ramp_span_nm()

    def as_record(self) -> dict[str, Any]:
        thick, thin = self.well_widths_nm()
        record = asdict(self)
        record.update({
            "derived_thick_well_nm": thick,
            "derived_thin_well_nm": thin,
            "total_well_thickness_nm": TOTAL_WELL_NM,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
            "minimum_layer_nm": self.minimum_layer_nm(),
            "linear_ramp_span_nm": self.ramp_span_nm(),
            "non_overlap_margin_nm": self.non_overlap_margin_nm(),
        })
        return record


def _case(index: int, name: str, purpose: str, *,
          asymmetry_s: float = MODERATE_ASYMMETRY,
          barrier_nm: float = MODERATE_BARRIER_NM,
          grading_nm: float = MODERATE_GRADING_NM,
          physics: str = "") -> SimpleCase:
    """One case with equal left/right grading -- 16B never splits the two."""

    return SimpleCase(
        case_id=f"case_{index:02d}",
        name=name,
        purpose=purpose,
        asymmetry_s=asymmetry_s,
        nominal_central_barrier_thickness_nm=barrier_nm,
        gaas_to_algaas_grading_width_10_90_nm=grading_nm,
        algaas_to_gaas_grading_width_10_90_nm=grading_nm,
        physics=bool(physics),
        physics_label=physics,
    )


def all_cases() -> list[SimpleCase]:
    """The eight fixed cases. Same objects, same numbers, every run."""

    cases = [
        _case(1, "paper_reference",
              "7.1 / 1.8 / 2.9 nm, converted to asymmetry through the "
              "authoritative formula. The primary reference structure.",
              asymmetry_s=PAPER_ASYMMETRY, barrier_nm=1.80, grading_nm=1.00,
              physics="A"),
        _case(2, "near_abrupt_baseline",
              "Smallest grading width the production renderer accepts "
              f"({MINIMUM_GRADING_NM} nm). The near-abrupt end of the "
              "comparison; grading14 has no abrupt branch at all.",
              grading_nm=MINIMUM_GRADING_NM),
        _case(3, "moderate_grading",
              "Moderate everything. The basic graded reference structure.",
              grading_nm=MODERATE_GRADING_NM),
        _case(4, "wide_grading",
              "Wider grading at the same asymmetry and barrier, so a change in "
              "requested width must show up as a change in realized x_Al(z). "
              "Still clearly non-overlapping (0.30 nm of margin).",
              grading_nm=1.20, physics="B"),
        _case(5, "minimum_barrier",
              "Thinnest barrier the Demo 14 space allows, with the most "
              "conservative grading, so the geometry stays simple and valid. "
              "The strongest inter-well coupling of the eight.",
              barrier_nm=0.85, grading_nm=MINIMUM_GRADING_NM, physics="C"),
        _case(6, "maximum_barrier",
              "Thickest barrier the Demo 14 space allows; the opposite "
              "boundary from case 05, with a wide nominal plateau.",
              barrier_nm=2.50),
        _case(7, "low_asymmetry",
              "Lower asymmetry bound: 6.5 / 3.5 nm wells.",
              asymmetry_s=0.30),
        _case(8, "high_asymmetry",
              "Upper asymmetry bound: 7.75 / 2.25 nm wells.",
              asymmetry_s=0.55),
    ]
    if len(cases) != 8:
        raise ValueError(f"Demo 16B requires exactly 8 cases, built {len(cases)}.")
    return cases


def physics_cases() -> list[SimpleCase]:
    """The three cases selected for a real licensed solve.

    A -- case 01, the paper reference.
    B -- case 04, wide linear grading.
    C -- case 05, the minimum barrier. Chosen over case 08 because barrier
         thickness sets the inter-well tunnel coupling and therefore changes the
         electronic structure qualitatively, while cases 01 and 04 already share
         one barrier and one asymmetry. Case 08 would only move state energies.
    """

    selected = [c for c in all_cases() if c.physics]
    if len(selected) != 3:
        raise ValueError(f"Demo 16B solves exactly 3 cases, selected {len(selected)}.")
    return selected


def write_cases_file(path: Path) -> Path:
    """Freeze the resolved case table with explicit numbers."""

    cases = all_cases()
    payload = {
        "demo": "16B_simple_acqw_grading_validation",
        "total_cases": len(cases),
        "grading_profile": GRADING_PROFILE,
        "grading_families_supported": [GRADING_PROFILE],
        "deterministic": True,
        "random_seed": None,
        "bounds": {k: list(v) for k, v in BOUNDS.items()},
        "fixed": {
            "total_well_thickness_nm": TOTAL_WELL_NM,
            "aluminium_fraction": AL_FRACTION,
            "mesh_nm": MESH_NM,
            "target_wavelength_nm": TARGET_WAVELENGTH_NM,
            "broadening_meV": BROADENING_MEV,
        },
        "paper_asymmetry_s": PAPER_ASYMMETRY,
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


def load_cases(path: Path) -> list[SimpleCase]:
    """Read the frozen table. The file, not the generator, is authoritative."""

    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fields = set(SimpleCase.__dataclass_fields__)
    return [
        SimpleCase(**{k: v for k, v in record.items() if k in fields})
        for record in payload["cases"]
    ]


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / CASES_FILENAME
    write_cases_file(target)
    print(f"wrote {target}")
    for case in all_cases():
        thick, thin = case.well_widths_nm()
        print(
            f"  {case.case_id}  {case.name:<22} {case.grading_profile:<7} "
            f"s={case.asymmetry_s:.4f} b={case.nominal_central_barrier_thickness_nm:.2f} "
            f"w={case.gaas_to_algaas_grading_width_10_90_nm:.2f} "
            f"wells={thick:.3f}/{thin:.3f} "
            f"margin={case.non_overlap_margin_nm():+.3f} nm"
            + (f"  [physics {case.physics_label}]" if case.physics else "")
        )
