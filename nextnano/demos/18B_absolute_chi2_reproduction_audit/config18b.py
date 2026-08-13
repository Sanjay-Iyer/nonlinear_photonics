"""Configuration projection and validation for Demo 18B."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml

import cases18b
import config18


DEMO_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DEMO_DIR / "demo18b.yaml"


class Config18BError(ValueError):
    pass


def load_config(path: Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else CONFIG_PATH
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise Config18BError(f"{source} did not parse to a mapping")
    cfg = dict(payload)
    validate(cfg)
    return cfg


def validate(cfg: Mapping[str, Any]) -> None:
    required = {
        "reference_structure", "solver", "chi2", "bound_state_criteria",
        "convergence_tolerances", "diagnostics",
    }
    missing = required - set(cfg)
    if missing:
        raise Config18BError(f"missing sections: {sorted(missing)}")
    structure = cfg["reference_structure"]
    actual = (
        float(structure["well_1_nm"]),
        float(structure["tunneling_barrier_nm"]),
        float(structure["well_2_nm"]),
        float(structure["period_barrier_nm"]),
        float(structure["nominal_period_nm"]),
        float(structure["barrier_al_fraction"]),
        str(structure["interfaces"]),
    )
    if actual != (7.1, 1.8, 2.9, 18.2, 30.0, 0.55, "abrupt"):
        raise Config18BError("Demo 18B may not alter the physical reference structure")
    chi = cfg["chi2"]
    if int(chi["primary_states_per_band"]) != 2:
        raise Config18BError("the paper reproduction must remain a two-state model")
    if float(chi["broadening_meV"]) != 5.0:
        raise Config18BError("the paper states Gamma = 5 meV")
    if str(cfg["solver"]["current_equation_mode"]) != "schrodinger_only_no_density_yes":
        raise Config18BError("current solver mode must be documented exactly")
    cases18b.validate(cases18b.solve_cases())


def demo18_compatible_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Project 18B values into Demo 18's already validated configuration schema."""

    base = config18.load_config()
    base["reference_structure"] = deepcopy(dict(cfg["reference_structure"]))
    base["solver"].update({
        "number_of_electron_states": int(cfg["solver"]["number_of_electron_states"]),
        "number_of_hole_states": int(cfg["solver"]["number_of_hole_states"]),
        "output_state_count": int(cfg["solver"]["output_state_count"]),
        "timeout_seconds": float(cfg["solver"]["timeout_seconds"]),
    })
    base["chi2"].update({
        "broadening_meV": float(cfg["chi2"]["broadening_meV"]),
        "r_e_hh_nm": float(cfg["chi2"]["r_e_hh_nm"]),
        "wavelength_start_nm": float(cfg["chi2"]["wavelength_start_nm"]),
        "wavelength_stop_nm": float(cfg["chi2"]["wavelength_stop_nm"]),
        "wavelength_points": int(cfg["chi2"]["wavelength_points"]),
        "target_wavelength_nm": float(cfg["chi2"]["target_wavelength_nm"]),
        "lattice_constant_nm": float(cfg["chi2"]["lattice_constant_nm"]),
        "electron_mass_m0": float(cfg["chi2"]["electron_mass_m0"]),
        "heavy_hole_inplane_mass_m0": float(
            cfg["chi2"]["heavy_hole_inplane_mass_m0"]
        ),
    })
    return base


def solver_config(cfg: Mapping[str, Any], case: cases18b.NumericalCase) -> dict[str, Any]:
    projected = config18.solver_config(demo18_compatible_config(cfg))
    projected["geometry"]["domain_padding_nm"] = float(case.domain_padding_nm)
    projected["geometry"]["quantum_region_padding_nm"] = float(case.quantum_padding_nm)
    projected["mesh"]["active_region_grid_spacing_nm"] = float(case.mesh_nm)
    return projected


def resolved_snapshot(cfg: Mapping[str, Any], machine: Any | None) -> dict[str, Any]:
    result = deepcopy(dict(cfg))
    result["licensed_solve_cases"] = [row.as_record() for row in cases18b.solve_cases()]
    result["licensed_solve_count"] = len(cases18b.solve_cases())
    result["mesh_case_alias"] = {
        "0.05_nm": "D3_plus40",
        "reason": "the largest-domain 0.05 nm deck is reused, not solved twice",
    }
    result["machine"] = {
        "config_path": str(getattr(machine, "source_path", "")) or None,
        "solver_executable": str(getattr(machine, "executable", "")) or None,
        "database": str(getattr(machine, "database", "")) or None,
        "threads": getattr(machine, "threads", None),
        "results_root": str(getattr(machine, "results_root", "")) or None,
    }
    result["paper_limits"] = {
        "first_two_bound_states": "published in Methods 5.1",
        "broadening_meV": 5.0,
        "k_saturation": "one tenth of Brillouin zone; edge convention not stated",
        "schrodinger_poisson": (
            "stated, but doping, carrier density, electrostatic boundary conditions, "
            "and charge state are not published"
        ),
        "r_e_hh": "HSE06/VASP method stated; numerical value not published",
    }
    result["physical_constants_si"] = {
        "elementary_charge_C": 1.602176634e-19,
        "vacuum_permittivity_F_per_m": 8.8541878128e-12,
        "reduced_planck_J_s": 1.054571817e-34,
        "electron_mass_kg": 9.1093837015e-31,
        "speed_of_light_m_per_s": 299792458.0,
        "hc_eV_nm": 1239.841984,
    }
    return result
