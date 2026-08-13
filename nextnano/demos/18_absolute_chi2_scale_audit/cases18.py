"""Fixed solver case and explicit post-processing matrix for Demo 18."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import cases16e
import chi2 as chi2mod

DEMO_ID = "18_absolute_chi2_scale_audit"
REFERENCE_CASE_ID = "reference_abrupt"
PERIOD_NM = 30.0
LATTICE_CONSTANT_NM = 0.565325


@dataclass(frozen=True)
class ScaleCase:
    """One post-processing convention set; no row launches a solver."""

    case_id: str
    label: str
    nz_convention: str
    kmax_convention: str
    k_points: int
    spin_degeneracy: int
    r_scale: float = 1.0

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


NZ_CONVENTIONS = {
    "pair_per_period": 1.0 / (PERIOD_NM * 1.0e-9),
    "two_wells_per_period": 2.0 / (PERIOD_NM * 1.0e-9),
}

# Chi2Settings historically defines k_max = fraction*pi/a. Demo 18 selects the
# alternative explicitly by doubling the fraction; shared production defaults
# therefore remain unchanged.
KMAX_CONVENTIONS = {
    "legacy_pi_over_a": {
        "fraction_for_chi2_settings": 0.10,
        "formula": "0.1*pi/a",
    },
    "bz_2pi_over_a": {
        "fraction_for_chi2_settings": 0.20,
        "formula": "0.1*2*pi/a",
    },
}


def reference_solver_case() -> cases16e.GeometryCase:
    """The paper-like 7.1/1.8/2.9 nm abrupt ACQW, solved exactly once."""

    return cases16e.GeometryCase(
        case_id=REFERENCE_CASE_ID,
        name="paper_like_abrupt",
        description=(
            "Fixed paper-like abrupt 7.1/1.8/2.9 nm GaAs/Al0.55Ga0.45As "
            "asymmetric coupled quantum well used only for the absolute-scale audit."
        ),
        asymmetry_s=chi2mod.structural_asymmetry(7.1, 2.9),
        central_barrier_nm=1.8,
        left_grading_width_nm=0.0,
        right_grading_width_nm=0.0,
        interface_mode="abrupt",
    )


def audit_cases() -> tuple[ScaleCase, ...]:
    """The compact eight-row experiment matrix requested for Demo 18."""

    rows = (
        ScaleCase("A_baseline", "Baseline", "pair_per_period",
                  "legacy_pi_over_a", 96, 2),
        ScaleCase("B_two_wells_Nz", "Two-well Nz", "two_wells_per_period",
                  "legacy_pi_over_a", 96, 2),
        ScaleCase("C_large_kmax", "Larger kmax", "pair_per_period",
                  "bz_2pi_over_a", 96, 2),
        ScaleCase("D_Nz_plus_large_kmax", "Nz + larger kmax",
                  "two_wells_per_period", "bz_2pi_over_a", 96, 2),
        ScaleCase("E_kgrid_192", "k grid 192", "two_wells_per_period",
                  "bz_2pi_over_a", 192, 2),
        ScaleCase("F_kgrid_384", "k grid 384", "two_wells_per_period",
                  "bz_2pi_over_a", 384, 2),
        ScaleCase("G_spin1", "Spin 1", "two_wells_per_period",
                  "bz_2pi_over_a", 384, 1),
        ScaleCase("H_spin2", "Spin 2", "two_wells_per_period",
                  "bz_2pi_over_a", 384, 2),
    )
    validate_cases(rows)
    return rows


def validate_cases(rows: tuple[ScaleCase, ...]) -> None:
    expected = (
        "A_baseline", "B_two_wells_Nz", "C_large_kmax",
        "D_Nz_plus_large_kmax", "E_kgrid_192", "F_kgrid_384",
        "G_spin1", "H_spin2",
    )
    if tuple(row.case_id for row in rows) != expected:
        raise ValueError("Demo 18 post-processing case ids/order changed.")
    for row in rows:
        if row.nz_convention not in NZ_CONVENTIONS:
            raise ValueError(f"{row.case_id}: unknown Nz convention")
        if row.kmax_convention not in KMAX_CONVENTIONS:
            raise ValueError(f"{row.case_id}: unknown kmax convention")
        if row.k_points not in (96, 192, 384):
            raise ValueError(f"{row.case_id}: unsupported k point count")
        if row.spin_degeneracy not in (1, 2):
            raise ValueError(f"{row.case_id}: spin degeneracy must be 1 or 2")
        if row.r_scale <= 0:
            raise ValueError(f"{row.case_id}: r scale must be positive")

