"""Configuration and frozen-case loading for Demo 18D."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping

import yaml

import cases18c
import cases18d
import config18c


DEMO_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DEMO_DIR / "demo18d.yaml"
RANGES_PATH = DEMO_DIR / "demo18d_parameter_ranges.csv"
COMBINATIONS_PATH = DEMO_DIR / cases18d.COMBINATIONS_FILENAME


class Config18DError(ValueError):
    pass


def load_config(path: Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else CONFIG_PATH
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise Config18DError(f"{source} did not parse to a mapping")
    cfg = dict(payload)
    validate(cfg)
    return cfg


def validate(cfg: Mapping[str, Any]) -> None:
    required = {"design", "fixed_physics", "solver", "spectrum",
                "r_e_hh_sensitivity_nm", "bound_state_criteria"}
    missing = required - set(cfg)
    if missing:
        raise Config18DError(f"missing sections: {sorted(missing)}")
    if int(cfg["design"]["seed"]) != 1804 or int(cfg["design"]["primary_case_count"]) != 20:
        raise Config18DError("Demo 18D is exactly 20 cases with seed 1804")
    fixed = cfg["fixed_physics"]
    expected = {
        "hh_relative_weight": 1.0, "spin_degeneracy": 2,
        "wells_per_period_for_Nz": 2, "r_e_hh_primary_nm": 0.751,
        "broadening_meV": 5.0, "states_per_band": 2,
        "interfaces": "abrupt",
    }
    for name, value in expected.items():
        if fixed[name] != value:
            raise Config18DError(f"fixed_physics.{name} must be {value!r}")
    solver = cfg["solver"]
    actual_grid = (float(solver["domain_padding_nm"]),
                   float(solver["quantum_region_padding_nm"]), float(solver["mesh_nm"]))
    if actual_grid != (60.0, 42.0, 0.025):
        raise Config18DError("Demo 18D must inherit the converged Demo 18B grid/domain")
    if [float(v) for v in cfg["spectrum"]["desired_peak_window_nm"]] != [1520.0, 1560.0]:
        raise Config18DError("spectral target window must be 1520-1560 nm")
    if [float(v) for v in cfg["r_e_hh_sensitivity_nm"]] != [0.65, 0.751, 1.0]:
        raise Config18DError("r_e_hh diagnostic points must be 0.65, 0.751, 1.00 nm")


def _bool(value: str) -> bool:
    folded = value.strip().casefold()
    if folded in {"true", "1", "yes"}:
        return True
    if folded in {"false", "0", "no"}:
        return False
    raise Config18DError(f"invalid boolean {value!r}")


def load_cases(path: Path | None = None) -> tuple[cases18d.PhysicsCase, ...]:
    source = Path(path) if path else COMBINATIONS_PATH
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        raw = list(csv.DictReader(stream))
    rows = tuple(cases18d.PhysicsCase(
        case_id=row["case_id"], design_role=row["design_role"],
        source_18c_combo_id=row["source_18c_combo_id"],
        electrostatic_field_kV_per_cm=float(row["electrostatic_field_kV_per_cm"]),
        tunneling_barrier_nm=float(row["tunneling_barrier_nm"]),
        well1_nm=float(row["well1_nm"]), well2_nm=float(row["well2_nm"]),
        hh_relative_weight=float(row["hh_relative_weight"]),
        spin_degeneracy=int(row["spin_degeneracy"]),
        wells_per_period_for_Nz=int(row["wells_per_period_for_Nz"]),
        r_e_hh_primary_nm=float(row["r_e_hh_primary_nm"]),
        requires_licensed_solve=_bool(row["requires_licensed_solve"]),
    ) for row in raw)
    cases18d.validate_cases(rows)
    if rows != cases18d.generate_cases():
        raise Config18DError("checked-in combinations do not match the deterministic seed-1804 design")
    return rows


def as_demo18c_combination(case: cases18d.PhysicsCase) -> cases18c.Combination:
    """Use Demo 18C's validated abrupt renderer with every postprocessor fixed."""

    return cases18c.Combination(
        combo_id=case.case_id, design_role=case.design_role,
        r_e_hh_nm=0.751,
        electrostatic_field_kV_per_cm=case.electrostatic_field_kV_per_cm,
        hh_relative_weight=1.0, wells_per_period_for_Nz=2,
        spin_degeneracy=2, kmax_fraction_2pi_over_a=0.10,
        well1_nm=case.well1_nm, well2_nm=case.well2_nm,
        tunneling_barrier_nm=case.tunneling_barrier_nm,
        electron_mass_scale=1.0, hh_mass_scale=1.0,
        cb_offset_scale=1.0, hh_offset_scale=1.0,
        solver_case_id=case.case_id, requires_new_nextnano_solve=True,
    )


def solver_config(cfg: Mapping[str, Any], case: cases18d.PhysicsCase) -> dict[str, Any]:
    return config18c.solver_config(cfg_for_18c(cfg), as_demo18c_combination(case))


def cfg_for_18c(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Small schema bridge; physics values remain the fixed Demo 18D values."""

    return {
        "reference_structure": {
            "nominal_period_nm": float(cfg["fixed_physics"]["nominal_period_nm"]),
            "interfaces": "abrupt",
        },
        "solver": dict(cfg["solver"]),
    }

