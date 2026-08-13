"""Configuration and immutable-input loading for Demo 18C."""

from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml

import cases18b
import cases18c
import config18b


DEMO_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DEMO_DIR / "demo18c.yaml"
RANGES_PATH = DEMO_DIR / "demo18c_parameter_ranges.csv"
COMBINATIONS_PATH = DEMO_DIR / cases18c.COMBINATIONS_FILENAME


class Config18CError(ValueError):
    pass


def load_config(path: Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else CONFIG_PATH
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise Config18CError(f"{source} did not parse to a mapping")
    cfg = dict(payload)
    validate(cfg)
    return cfg


def validate(cfg: Mapping[str, Any]) -> None:
    required = {
        "ensemble", "reference_structure", "solver", "chi2",
        "bound_state_criteria", "spectral_gate", "outcomes",
    }
    missing = required - set(cfg)
    if missing:
        raise Config18CError(f"missing sections: {sorted(missing)}")
    ensemble = cfg["ensemble"]
    if int(ensemble["seed"]) != cases18c.SEED:
        raise Config18CError("the checked-in ensemble is frozen to seed 1803")
    if int(ensemble["combination_count"]) != 20:
        raise Config18CError("Demo 18C requires exactly 20 combinations")
    if int(ensemble["unique_licensed_solve_count"]) != 17:
        raise Config18CError("Demo 18C must deduplicate to exactly 17 licensed solves")
    solver = cfg["solver"]
    if int(solver["states_used_in_eq2"]) != 2:
        raise Config18CError("Eq. 2 must use exactly two states per band")
    if (float(solver["domain_padding_nm"]), float(solver["quantum_region_padding_nm"]),
            float(solver["mesh_nm"])) != (60.0, 42.0, 0.025):
        raise Config18CError("Demo 18C must start from Demo 18B's converged domain and mesh")
    if any(bool(solver[name]) for name in (
        "electron_mass_override_implemented", "hh_mass_override_implemented",
        "cb_offset_override_implemented", "hh_offset_override_implemented",
    )):
        raise Config18CError("material overrides require a separately validated renderer")
    chi = cfg["chi2"]
    if float(chi["broadening_meV"]) != 5.0:
        raise Config18CError("the published 5 meV broadening must remain fixed")
    if float(chi["target_wavelength_nm"]) != 1550.0:
        raise Config18CError("the primary target must remain 1550 nm")
    if str(cfg["reference_structure"]["interfaces"]) != "abrupt":
        raise Config18CError("the paper's 2340 pm/V target is the abrupt-interface case")


def _bool(value: str) -> bool:
    folded = value.strip().casefold()
    if folded in {"true", "1", "yes"}:
        return True
    if folded in {"false", "0", "no"}:
        return False
    raise Config18CError(f"invalid boolean {value!r}")


def load_combinations(path: Path | None = None) -> tuple[cases18c.Combination, ...]:
    source = Path(path) if path else COMBINATIONS_PATH
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        raw = list(csv.DictReader(stream))
    rows = tuple(cases18c.Combination(
        combo_id=row["combo_id"], design_role=row["design_role"],
        r_e_hh_nm=float(row["r_e_hh_nm"]),
        electrostatic_field_kV_per_cm=float(row["electrostatic_field_kV_per_cm"]),
        hh_relative_weight=float(row["hh_relative_weight"]),
        wells_per_period_for_Nz=int(row["wells_per_period_for_Nz"]),
        spin_degeneracy=int(row["spin_degeneracy"]),
        kmax_fraction_2pi_over_a=float(row["kmax_fraction_2pi_over_a"]),
        well1_nm=float(row["well1_nm"]), well2_nm=float(row["well2_nm"]),
        tunneling_barrier_nm=float(row["tunneling_barrier_nm"]),
        electron_mass_scale=float(row["electron_mass_scale"]),
        hh_mass_scale=float(row["hh_mass_scale"]),
        cb_offset_scale=float(row["cb_offset_scale"]),
        hh_offset_scale=float(row["hh_offset_scale"]),
        solver_case_id=row["solver_case_id"],
        requires_new_nextnano_solve=_bool(row["requires_new_nextnano_solve"]),
    ) for row in raw)
    cases18c.validate_combinations(rows)
    expected = cases18c.generate_combinations()
    if rows != expected:
        raise Config18CError(
            f"{source} does not match the seed-1803 deterministic design; do not run physics"
        )
    return rows


def unique_solver_combinations(
    rows: tuple[cases18c.Combination, ...] | None = None,
) -> tuple[cases18c.Combination, ...]:
    rows = rows or load_combinations()
    unique = tuple(row for row in rows if row.requires_new_nextnano_solve)
    if len(unique) != 17:
        raise Config18CError(f"expected 17 unique solver cases, got {len(unique)}")
    return unique


def solver_config(cfg: Mapping[str, Any], combo: cases18c.Combination) -> dict[str, Any]:
    """Project a combination onto Demo 18B's converged validated renderer."""

    numeric = cases18b.NumericalCase(
        case_id=combo.solver_case_id,
        experiment="demo18c_ensemble",
        domain_padding_nm=float(cfg["solver"]["domain_padding_nm"]),
        quantum_padding_nm=float(cfg["solver"]["quantum_region_padding_nm"]),
        mesh_nm=float(cfg["solver"]["mesh_nm"]),
        description=f"Demo 18C solver state for {combo.combo_id}",
    )
    projected = config18b.solver_config(config18b.load_config(), numeric)
    total_well = combo.well1_nm + combo.well2_nm
    period_barrier = (
        float(cfg["reference_structure"]["nominal_period_nm"])
        - total_well - combo.tunneling_barrier_nm
    )
    if period_barrier <= 0:
        raise Config18CError(f"{combo.combo_id}: non-positive derived period barrier")
    projected = deepcopy(projected)
    projected["geometry"]["total_well_thickness_nm"] = total_well
    projected["geometry"]["period_barrier_nm"] = period_barrier
    projected["states"].update({
        "number_of_electron_states": int(cfg["solver"]["number_of_electron_states"]),
        "number_of_hole_states": int(cfg["solver"]["number_of_hole_states"]),
        "output_state_count": int(cfg["solver"]["output_state_count"]),
        "max_states_per_band": 2,
    })
    projected["nextnano"]["solver_timeout_seconds"] = float(cfg["solver"]["timeout_seconds"])
    return projected

