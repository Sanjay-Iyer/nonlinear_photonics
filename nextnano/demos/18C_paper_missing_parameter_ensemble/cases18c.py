"""Frozen, reproducible parameter ensemble for Demo 18C.

The ensemble is generated independently of any physics result.  Physics runs only
validate the checked-in CSV; they never redraw or replace a failed combination.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Any, Iterable

import numpy as np


DEMO_ID = "18C_paper_missing_parameter_ensemble"
SEED = 1803
COMBO_COUNT = 20
SPACE_FILLING_COUNT = 15
COMBINATIONS_FILENAME = "demo18c_combinations.csv"


@dataclass(frozen=True)
class Combination:
    combo_id: str
    design_role: str
    r_e_hh_nm: float
    electrostatic_field_kV_per_cm: float
    hh_relative_weight: float
    wells_per_period_for_Nz: int
    spin_degeneracy: int
    kmax_fraction_2pi_over_a: float
    well1_nm: float
    well2_nm: float
    tunneling_barrier_nm: float
    electron_mass_scale: float = 1.0
    hh_mass_scale: float = 1.0
    cb_offset_scale: float = 1.0
    hh_offset_scale: float = 1.0
    solver_case_id: str = ""
    requires_new_nextnano_solve: bool = True

    def as_record(self) -> dict[str, Any]:
        return asdict(self)

    def solver_key(self) -> tuple[float, ...]:
        """Only implemented solver-level quantities belong in this key."""

        return (
            self.electrostatic_field_kV_per_cm,
            self.well1_nm,
            self.well2_nm,
            self.tunneling_barrier_nm,
            self.electron_mass_scale,
            self.hh_mass_scale,
            self.cb_offset_scale,
            self.hh_offset_scale,
        )


def _maximin_latin_hypercube(
    samples: int, dimensions: int, seed: int, candidates: int = 512
) -> np.ndarray:
    """Choose the best of deterministic stratified Latin-hypercube candidates."""

    rng = np.random.default_rng(seed)
    best: np.ndarray | None = None
    best_min_distance = -1.0
    for _ in range(candidates):
        design = np.empty((samples, dimensions), dtype=float)
        for column in range(dimensions):
            design[:, column] = (
                rng.permutation(samples) + rng.random(samples)
            ) / samples
        deltas = design[:, None, :] - design[None, :, :]
        distance2 = np.sum(deltas * deltas, axis=2)
        distance2[np.diag_indices(samples)] = np.inf
        minimum = float(np.min(distance2))
        if minimum > best_min_distance:
            best_min_distance = minimum
            best = design.copy()
    assert best is not None
    return best


def _map(unit: float, lower: float, upper: float, digits: int) -> float:
    return round(lower + float(unit) * (upper - lower), digits)


def generate_combinations(seed: int = SEED) -> tuple[Combination, ...]:
    """Return the exact 20-case design; this does not inspect any solver result."""

    rows: list[Combination] = [
        Combination(
            "Combo_00", "baseline_demo18b_converged", 0.751, 0.0, 1.0,
            2, 2, 0.10, 7.1, 2.9, 1.8,
        )
    ]
    lhs = _maximin_latin_hypercube(SPACE_FILLING_COUNT, 7, seed)
    k_choices = np.asarray([0.10, 0.125, 0.15, 0.175, 0.20])
    # Three LHS rows plus Combo 19 use each alternate convention: 4/20 = 20%.
    nz_one = {4, 9, 14}
    spin_one = {5, 10, 15}
    for index, unit in enumerate(lhs, 1):
        k_index = min(int(unit[6] * len(k_choices)), len(k_choices) - 1)
        rows.append(Combination(
            combo_id=f"Combo_{index:02d}",
            design_role="maximin_latin_hypercube",
            r_e_hh_nm=_map(unit[1], 0.65, 1.00, 6),
            electrostatic_field_kV_per_cm=_map(unit[0], -20.0, 20.0, 6),
            hh_relative_weight=_map(unit[2], 0.55, 1.45, 6),
            wells_per_period_for_Nz=1 if index in nz_one else 2,
            spin_degeneracy=1 if index in spin_one else 2,
            kmax_fraction_2pi_over_a=float(k_choices[k_index]),
            well1_nm=_map(unit[3], 7.0, 7.2, 6),
            well2_nm=_map(unit[4], 2.8, 3.0, 6),
            tunneling_barrier_nm=_map(unit[5], 1.7, 1.9, 6),
        ))
    rows.extend((
        Combination(
            "Combo_16", "hh_low_weight_diagnostic", 0.751, 0.0, 0.60,
            2, 2, 0.10, 7.1, 2.9, 1.8,
        ),
        Combination(
            "Combo_17", "hh_high_weight_diagnostic", 0.751, 0.0, 1.40,
            2, 2, 0.10, 7.1, 2.9, 1.8,
        ),
        Combination(
            "Combo_18", "combined_high_side_bounded", 1.00, 20.0, 0.75,
            2, 2, 0.20, 7.2, 3.0, 1.7,
        ),
        Combination(
            "Combo_19", "convention_cross_check", 0.751, 0.0, 1.0,
            1, 1, 0.20, 7.1, 2.9, 1.8,
        ),
    ))

    first_by_key: dict[tuple[float, ...], str] = {}
    resolved: list[Combination] = []
    for row in rows:
        key = row.solver_key()
        if key not in first_by_key:
            first_by_key[key] = f"Solve_{len(first_by_key):02d}"
            new_solve = True
        else:
            new_solve = False
        values = row.as_record()
        values["solver_case_id"] = first_by_key[key]
        values["requires_new_nextnano_solve"] = new_solve
        resolved.append(Combination(**values))
    validate_combinations(resolved, seed=seed)
    return tuple(resolved)


def validate_combinations(rows: Iterable[Combination], *, seed: int = SEED) -> None:
    rows = tuple(rows)
    if seed != SEED:
        raise ValueError(f"Demo 18C is frozen to seed {SEED}, got {seed}")
    if len(rows) != COMBO_COUNT:
        raise ValueError(f"Demo 18C requires exactly {COMBO_COUNT} combinations")
    if tuple(row.combo_id for row in rows) != tuple(f"Combo_{i:02d}" for i in range(20)):
        raise ValueError("combination IDs must be Combo_00 through Combo_19")
    if sum(row.wells_per_period_for_Nz == 2 for row in rows) != 16:
        raise ValueError("Nz=2 must occur in exactly 80% of the ensemble")
    if sum(row.spin_degeneracy == 2 for row in rows) != 16:
        raise ValueError("spin=2 must occur in exactly 80% of the ensemble")
    bounds = {
        "r_e_hh_nm": (0.65, 1.00),
        "electrostatic_field_kV_per_cm": (-20.0, 20.0),
        "hh_relative_weight": (0.55, 1.45),
        "kmax_fraction_2pi_over_a": (0.10, 0.20),
        "well1_nm": (7.0, 7.2),
        "well2_nm": (2.8, 3.0),
        "tunneling_barrier_nm": (1.7, 1.9),
    }
    for row in rows:
        for name, (lower, upper) in bounds.items():
            value = float(getattr(row, name))
            if not lower <= value <= upper:
                raise ValueError(f"{row.combo_id}: {name}={value} outside [{lower}, {upper}]")
        if row.wells_per_period_for_Nz not in (1, 2) or row.spin_degeneracy not in (1, 2):
            raise ValueError(f"{row.combo_id}: invalid discrete convention")
        for name in ("electron_mass_scale", "hh_mass_scale", "cb_offset_scale", "hh_offset_scale"):
            if float(getattr(row, name)) != 1.0:
                raise ValueError(f"{name} has no clean renderer override and must remain 1.0")
    unique_solves = {row.solver_case_id for row in rows}
    if len(unique_solves) != 17:
        raise ValueError(f"expected 17 unique licensed solves, found {len(unique_solves)}")


def combinations_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

