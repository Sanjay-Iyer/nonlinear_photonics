"""Licensed solve matrix for Demo 18B's numerical-convergence audit."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


DEMO_ID = "18B_absolute_chi2_reproduction_audit"


@dataclass(frozen=True)
class NumericalCase:
    case_id: str
    experiment: str
    domain_padding_nm: float
    quantum_padding_nm: float
    mesh_nm: float
    description: str

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


def solve_cases() -> tuple[NumericalCase, ...]:
    """Six unique decks: four domains plus two extra meshes on the largest."""

    rows = (
        NumericalCase(
            "D0_reference", "domain", 20.0, 2.0, 0.05,
            "Exact Demo 18 numerical domain and mesh.",
        ),
        NumericalCase(
            "D1_plus10", "domain", 30.0, 12.0, 0.05,
            "Ten additional nanometres of AlGaAs and Dirichlet padding per side.",
        ),
        NumericalCase(
            "D2_plus20", "domain", 40.0, 22.0, 0.05,
            "Twenty additional nanometres of AlGaAs and Dirichlet padding per side.",
        ),
        NumericalCase(
            "D3_plus40", "domain", 60.0, 42.0, 0.05,
            "Forty additional nanometres of AlGaAs and Dirichlet padding per side.",
        ),
        NumericalCase(
            "M0_0p10nm", "mesh", 60.0, 42.0, 0.10,
            "Coarse mesh on the largest numerical domain.",
        ),
        NumericalCase(
            "M2_0p025nm", "mesh", 60.0, 42.0, 0.025,
            "Fine mesh on the largest numerical domain.",
        ),
    )
    validate(rows)
    return rows


def mesh_cases_with_alias() -> tuple[tuple[str, float], ...]:
    """Mesh ladder; D3 is the 0.05 nm member and is not solved twice."""

    return (("M0_0p10nm", 0.10), ("D3_plus40", 0.05), ("M2_0p025nm", 0.025))


def validate(rows: tuple[NumericalCase, ...]) -> None:
    expected = (
        "D0_reference", "D1_plus10", "D2_plus20", "D3_plus40",
        "M0_0p10nm", "M2_0p025nm",
    )
    if tuple(row.case_id for row in rows) != expected:
        raise ValueError("Demo 18B solve matrix changed")
    if len({(r.domain_padding_nm, r.quantum_padding_nm, r.mesh_nm) for r in rows}) != len(rows):
        raise ValueError("Demo 18B contains a duplicate licensed deck")
    for row in rows:
        if row.quantum_padding_nm >= row.domain_padding_nm:
            raise ValueError(f"{row.case_id}: quantum wall must remain inside the domain")
        if min(row.domain_padding_nm, row.quantum_padding_nm, row.mesh_nm) <= 0:
            raise ValueError(f"{row.case_id}: numerical dimensions must be positive")
