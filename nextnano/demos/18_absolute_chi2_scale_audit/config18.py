"""Configuration loading and projection onto the existing Demo 14 solver deck."""

from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
from typing import Any, Mapping

import yaml

import cases18
import demo14

DEMO_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DEMO_DIR / "demo18.yaml"


class Demo18ConfigError(ValueError):
    pass


def load_config(path: Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else CONFIG_PATH
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise Demo18ConfigError(f"{source} did not parse to a mapping")
    cfg = dict(payload)
    validate_config(cfg)
    return cfg


def validate_config(cfg: Mapping[str, Any]) -> None:
    for section in ("reference_structure", "solver", "chi2", "audits"):
        if section not in cfg:
            raise Demo18ConfigError(f"missing '{section}' section")
    structure = cfg["reference_structure"]
    expected = (7.1, 1.8, 2.9, 18.2, 30.0, 0.55, "abrupt")
    actual = (
        float(structure["well_1_nm"]),
        float(structure["tunneling_barrier_nm"]),
        float(structure["well_2_nm"]),
        float(structure["period_barrier_nm"]),
        float(structure["nominal_period_nm"]),
        float(structure["barrier_al_fraction"]),
        str(structure["interfaces"]),
    )
    if actual != expected:
        raise Demo18ConfigError(
            "Demo 18 is fixed to the abrupt paper-like 7.1/1.8/2.9 nm structure"
        )
    if abs(sum(actual[:4]) - actual[4]) > 1.0e-12:
        raise Demo18ConfigError("reference layer arithmetic does not equal 30 nm")
    chi = cfg["chi2"]
    if float(chi["r_e_hh_nm"]) <= 0 or float(chi["broadening_meV"]) <= 0:
        raise Demo18ConfigError("r_e_hh_nm and broadening_meV must be positive")
    if int(chi["wavelength_points"]) < 2:
        raise Demo18ConfigError("wavelength_points must be at least 2")
    if int(cfg["solver"]["states_used_in_eq2"]) != 2:
        raise Demo18ConfigError("Demo 18 reproduces the paper's two-state Eq. 2 basis")
    cases18.validate_cases(cases18.audit_cases())


def solver_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Reuse Demo 14's validated renderer/parser settings with fixed Demo 18 values."""

    base = deepcopy(demo14.load_config())
    structure = cfg["reference_structure"]
    solver = cfg["solver"]
    chi = cfg["chi2"]
    base["geometry"]["total_well_thickness_nm"] = (
        float(structure["well_1_nm"]) + float(structure["well_2_nm"])
    )
    base["geometry"]["period_barrier_nm"] = float(structure["period_barrier_nm"])
    base["materials"]["barrier_al_fraction"] = float(structure["barrier_al_fraction"])
    base["mesh"]["active_region_grid_spacing_nm"] = float(solver["mesh_nm"])
    base["states"].update({
        "number_of_electron_states": int(solver["number_of_electron_states"]),
        "number_of_hole_states": int(solver["number_of_hole_states"]),
        "output_state_count": int(solver["output_state_count"]),
        "max_states_per_band": int(solver["states_used_in_eq2"]),
    })
    base["nextnano"]["solver_timeout_seconds"] = float(solver["timeout_seconds"])
    base["chi2"].update({
        "mode": "absolute",
        "target_wavelength_nm": float(chi["target_wavelength_nm"]),
        "broadening_meV": float(chi["broadening_meV"]),
        "max_states_per_band": int(solver["states_used_in_eq2"]),
        "r_e_hh_nm": float(chi["r_e_hh_nm"]),
        "focused_wavelength_nm": [
            float(chi["wavelength_start_nm"]), float(chi["wavelength_stop_nm"])
        ],
        "focused_wavelength_points": int(chi["wavelength_points"]),
    })
    base["k_parallel"].update({
        "lattice_constant_nm": float(chi["lattice_constant_nm"]),
        "electron_mass_m0": float(chi["electron_mass_m0"]),
        "heavy_hole_inplane_mass_m0": float(chi["heavy_hole_inplane_mass_m0"]),
    })
    return base


def resolved_snapshot(
    cfg: Mapping[str, Any], *, machine: Any | None, solver_cfg: Mapping[str, Any]
) -> dict[str, Any]:
    copy = deepcopy(dict(cfg))
    lattice_nm = float(cfg["chi2"]["lattice_constant_nm"])
    default_r_nm = float(cfg["chi2"]["r_e_hh_nm"])
    copy["post_processing_cases"] = [
        {
            **row.as_record(),
            "Nz_per_metre": cases18.NZ_CONVENTIONS[row.nz_convention],
            "kmax_per_nm": (
                cases18.KMAX_CONVENTIONS[row.kmax_convention][
                    "fraction_for_chi2_settings"
                ]
                * math.pi
                / lattice_nm
            ),
            "r_e_hh_nm": default_r_nm * row.r_scale,
        }
        for row in cases18.audit_cases()
    ]
    copy["resolved_conventions"] = {
        "Nz_per_metre": dict(cases18.NZ_CONVENTIONS),
        "kmax": dict(cases18.KMAX_CONVENTIONS),
    }
    copy["machine"] = {
        "config_path": str(getattr(machine, "source_path", "")) or None,
        "solver_executable": str(getattr(machine, "executable", "")) or None,
        "database": str(getattr(machine, "database", "")) or None,
        "threads": int(getattr(machine, "threads", solver_cfg["nextnano"]["threads"])),
        "run_solver": bool(getattr(machine, "run_solver", False)),
        "results_root": str(getattr(machine, "results_root", "")) or None,
    }
    copy["solver_deck_settings"] = {
        "mesh_nm": solver_cfg["mesh"]["active_region_grid_spacing_nm"],
        "number_of_electron_states": solver_cfg["states"]["number_of_electron_states"],
        "number_of_hole_states": solver_cfg["states"]["number_of_hole_states"],
        "states_used_in_eq2": solver_cfg["states"]["max_states_per_band"],
        "quantum_region_name": solver_cfg["nextnano"]["quantum_region_name"],
    }
    copy["wavelength_step_nm"] = (
        float(cfg["chi2"]["wavelength_stop_nm"])
        - float(cfg["chi2"]["wavelength_start_nm"])
    ) / (int(cfg["chi2"]["wavelength_points"]) - 1)
    return copy
