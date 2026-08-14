"""Frozen 20-case solver-physics design for Demo 18D."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Any, Iterable

import numpy as np


DEMO_ID = "18D_solver_physics_dual_objective_reproduction"
SEED = 1804
CASE_COUNT = 20
COMBINATIONS_FILENAME = "demo18d_combinations.csv"


@dataclass(frozen=True)
class PhysicsCase:
    case_id: str
    design_role: str
    source_18c_combo_id: str
    electrostatic_field_kV_per_cm: float
    tunneling_barrier_nm: float
    well1_nm: float
    well2_nm: float
    hh_relative_weight: float = 1.0
    spin_degeneracy: int = 2
    wells_per_period_for_Nz: int = 2
    r_e_hh_primary_nm: float = 0.751
    requires_licensed_solve: bool = True

    def as_record(self) -> dict[str, Any]:
        return asdict(self)

    def solver_key(self) -> tuple[float, float, float, float]:
        return (
            self.electrostatic_field_kV_per_cm, self.tunneling_barrier_nm,
            self.well1_nm, self.well2_nm,
        )


def _maximin_latin_hypercube(
    samples: int, dimensions: int, seed: int, candidates: int = 512,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    best: np.ndarray | None = None
    best_minimum = -1.0
    for _ in range(candidates):
        design = np.empty((samples, dimensions), float)
        for column in range(dimensions):
            design[:, column] = (
                rng.permutation(samples) + rng.random(samples)
            ) / samples
        delta = design[:, None, :] - design[None, :, :]
        distance2 = np.sum(delta * delta, axis=2)
        distance2[np.diag_indices(samples)] = np.inf
        minimum = float(np.min(distance2))
        if minimum > best_minimum:
            best_minimum = minimum
            best = design.copy()
    assert best is not None
    return best


def _map(unit: float, lower: float, upper: float) -> float:
    return round(lower + float(unit) * (upper - lower), 6)


def generate_cases(seed: int = SEED) -> tuple[PhysicsCase, ...]:
    """Generate before physics; no result-dependent case replacement is possible."""

    rows: list[PhysicsCase] = [
        PhysicsCase("Case_00", "demo18b_baseline", "Combo_00", 0.0, 1.8, 7.1, 2.9),
        # Highest normalized unweighted 18C solver result (104.45 pm/V).
        PhysicsCase("Case_01", "demo18c_solver_anchor", "Combo_07",
                    0.582619, 1.740274, 7.034685, 2.883710),
        # Bounded high-side solver corner; original scale removed in 18D.
        PhysicsCase("Case_02", "demo18c_solver_anchor", "Combo_18",
                    20.0, 1.7, 7.2, 3.0),
        PhysicsCase("Case_03", "demo18c_solver_anchor", "Combo_01",
                    4.578990, 1.705461, 7.167789, 2.952000),
        PhysicsCase("Case_04", "demo18c_solver_anchor", "Combo_02",
                    12.932406, 1.774727, 7.189786, 2.908121),
    ]
    lhs = _maximin_latin_hypercube(12, 4, seed)
    for offset, unit in enumerate(lhs, 5):
        rows.append(PhysicsCase(
            f"Case_{offset:02d}", "local_maximin_latin_hypercube", "",
            _map(unit[0], 0.0, 20.0),
            _map(unit[1], 1.70, 1.85),
            _map(unit[2], 7.05, 7.20),
            _map(unit[3], 2.85, 3.00),
        ))
    # Predefined refinements around the best physical 18C region, constrained to
    # the requested local range. They do not depend on any 18D result.
    rows.extend((
        PhysicsCase("Case_17", "predefined_local_refinement", "", 0.5, 1.70, 7.05, 2.88),
        PhysicsCase("Case_18", "predefined_local_refinement", "", 1.5, 1.72, 7.07, 2.90),
        PhysicsCase("Case_19", "predefined_local_refinement", "", 3.0, 1.75, 7.10, 2.92),
    ))
    validate_cases(rows, seed=seed)
    return tuple(rows)


def validate_cases(rows: Iterable[PhysicsCase], *, seed: int = SEED) -> None:
    rows = tuple(rows)
    if seed != SEED:
        raise ValueError(f"Demo 18D is frozen to seed {SEED}")
    if len(rows) != CASE_COUNT:
        raise ValueError(f"Demo 18D requires exactly {CASE_COUNT} cases")
    if tuple(row.case_id for row in rows) != tuple(f"Case_{i:02d}" for i in range(20)):
        raise ValueError("case IDs must be Case_00 through Case_19")
    if len({row.solver_key() for row in rows}) != CASE_COUNT:
        raise ValueError("every primary Demo 18D case must be unique solver physics")
    for row in rows:
        if row.hh_relative_weight != 1.0:
            raise ValueError(f"{row.case_id}: hh_relative_weight must be exactly 1.0")
        if row.spin_degeneracy != 2 or row.wells_per_period_for_Nz != 2:
            raise ValueError(f"{row.case_id}: spin and Nz conventions are fixed at 2")
        if row.r_e_hh_primary_nm != 0.751:
            raise ValueError(f"{row.case_id}: primary r_e_hh must be 0.751 nm")
        if not row.requires_licensed_solve:
            raise ValueError(f"{row.case_id}: every primary case requires real solver physics")
        for value in row.solver_key():
            if not np.isfinite(value):
                raise ValueError(f"{row.case_id}: non-finite solver parameter")


def combinations_sha256(path: Path) -> str:
    """Hash canonical UTF-8/LF CSV content, independent of Git autocrlf."""

    text = Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
