"""Stage 04 - the licensed nextnano++ solver interface.

This is the only module in Demo 20 that can launch a solver, and it does
nothing else: no physics, no analysis, no plotting. On a machine without a
licence it fails fast with a readable message instead of degrading into a
placeholder result.

The launcher itself is genuinely shared infrastructure, so this stage delegates
to the repository's existing, already-validated pieces rather than
reimplementing process handling:

* ``demo_workflow.load_machine_config`` - the repo-wide work/home machine
  resolution (``nextnano/config/machines/``). Demo 20 adds no path of its own,
  which is why no username appears anywhere in this demo.
* ``solver14.execute_real`` - the licensed invocation Demos 14 and 19 use.
* ``demo16b.verify_quantum_outputs`` / ``find_alloy_composition`` - the
  post-solve output presence check and the realized-composition readback.

Those imports are collected here, in one place, and each one is named with the
reason it is not duplicated. Nothing else in Demo 20 imports across demos.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import config20
import s01_cases as cases
import s02_grading as grading
import s03_inputs as inputs

#: Cross-demo modules Demo 20 deliberately reuses, with the reason for each.
SHARED_DEPENDENCIES: Mapping[str, str] = {
    "_shared/demo_workflow.py":
        "repository-wide machine configuration (executable/database/licence "
        "resolution, work vs home laptop). General-purpose infrastructure.",
    "14_absolute_chi2_graded_acqw_bo/solver14.py":
        "the licensed nextnano++ invocation used by Demos 14 and 19. Reused so "
        "Demo 20 runs the solver identically, not merely similarly.",
    "14_absolute_chi2_graded_acqw_bo/runlog14.py":
        "git provenance stamping for a run directory.",
    "16B_simple_acqw_grading_validation/demo16b.py":
        "post-solve output presence check and realized alloy-composition "
        "readback, so the solver's own composition is verified against the "
        "requested profile.",
    "16_acqw_renderer_stress_validation/demo16.py":
        "not called by Demo 20, but imported at module scope by demo16b.py. "
        "Its directory has to be importable or 'import demo16b' fails.",
    "14_absolute_chi2_graded_acqw_bo/demo14.py":
        "analyse_real_trial: the Demo 11 parser chain that turns a raw run into "
        "energies, envelopes and matrix elements. Reused so Demo 20's parsing "
        "provenance is identical to Demo 19's.",
}

_SHARED_PATHS = (
    config20.DEMOS_DIR / "_shared",
    config20.DEMOS_DIR / "11_paper_validation_interband_chi2_acqw",
    config20.DEMOS_DIR / "12_graded_interface_coupled_quantum_well_optimization",
    config20.DEMOS_DIR / "14_absolute_chi2_graded_acqw_bo",
    config20.DEMOS_DIR / "16B_simple_acqw_grading_validation",
    config20.DEMOS_DIR / "16E_acqw_structure_physics_optical_comparison",
    config20.DEMOS_DIR / "16_acqw_renderer_stress_validation",
)


class Solver20Error(RuntimeError):
    """The licensed solver is unavailable or refused to run."""


def enable_shared_imports() -> None:
    """Put the reused demo directories on ``sys.path``.

    Called explicitly by the solver and parse paths only. The home-laptop
    analysis path never calls it, so Demo 20's chi2, QC, plotting and reporting
    stages import nothing from another demo.
    """

    for path in _SHARED_PATHS:
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


@dataclass(frozen=True)
class SolverInvocation:
    """The outcome of one solve. ``solver_pass`` means the process succeeded."""

    case_id: str
    solver_pass: bool
    return_code: int | None
    output_dir: Path | None
    deck_path: Path | None
    composition_max_error: float | None
    message: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "solver_pass": self.solver_pass,
            "return_code": self.return_code,
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "deck_path": str(self.deck_path) if self.deck_path else None,
            "solver_composition_max_error": self.composition_max_error,
            "message": self.message,
        }


@dataclass(frozen=True)
class MachineStatus:
    """Whether this machine can run the licensed solver, and why not if it can't."""

    available: bool
    reason: str
    executable: str | None = None
    database: str | None = None
    license_path: str | None = None
    results_root: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "licensed_solver_available": self.available,
            "reason": self.reason,
            "executable": self.executable,
            "database": self.database,
            "license": self.license_path,
            "results_root": self.results_root,
        }


def machine_status() -> MachineStatus:
    """Probe the machine without launching anything. Safe on the home laptop."""

    try:
        enable_shared_imports()
        import demo_workflow  # noqa: PLC0415 - optional, licensed-path only
    except Exception as exc:  # pragma: no cover - import environment dependent
        return MachineStatus(False, f"machine configuration unavailable: {exc}")
    try:
        machine = demo_workflow.load_machine_config()
    except Exception as exc:
        return MachineStatus(False, f"machine configuration failed to load: {exc}")
    paths = {
        "executable": getattr(machine, "executable", None),
        "database": getattr(machine, "database", None),
        "license": getattr(machine, "license", None),
    }
    missing = [name for name, value in paths.items()
               if not value or not Path(str(value)).is_file()]
    if missing:
        return MachineStatus(
            False,
            "no licensed nextnano++ installation on this machine; missing "
            + ", ".join(missing),
            results_root=str(getattr(machine, "results_root", "") or "") or None,
        )
    if not getattr(machine, "run_solver", False):
        return MachineStatus(
            False, "machine configuration has run_solver disabled",
            executable=str(paths["executable"]), database=str(paths["database"]),
            license_path=str(paths["license"]),
            results_root=str(getattr(machine, "results_root", "") or "") or None,
        )
    return MachineStatus(
        True, "licensed nextnano++ resolved",
        executable=str(paths["executable"]), database=str(paths["database"]),
        license_path=str(paths["license"]),
        results_root=str(getattr(machine, "results_root", "") or "") or None,
    )


def require_machine():
    """The resolved machine config, or a clear refusal."""

    status = machine_status()
    if not status.available:
        raise Solver20Error(
            "Demo 20 cannot run the licensed solver here: " + status.reason
            + "\nRun with --analysis-only on this machine, or run --physics on "
              "the configured licensed work laptop."
        )
    enable_shared_imports()
    import demo_workflow  # noqa: PLC0415
    return demo_workflow.load_machine_config()


def solve_case(
    cfg: Mapping[str, Any], case: cases.GradingCase, machine: Any,
    *, case_dir: Path, raw_output_dir: Path,
) -> SolverInvocation:
    """Render, launch and verify one case. Requires a licensed machine.

    Verification here is deliberately limited to what the *solver* can tell us:
    the process return code, the presence of the requested quantum outputs, and
    whether the alloy composition nextnano++ actually built matches the profile
    that was requested. Physical validity is a separate judgement made in
    :mod:`s08_qc`.
    """

    enable_shared_imports()
    import demo16b  # noqa: PLC0415
    import solver14  # noqa: PLC0415

    input_dir = case_dir / "nextnano_input"
    logs_dir = case_dir / "logs"
    input_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    _g, profile, blocks, deck_text = inputs.build_case(cfg, case)
    deck = input_dir / "case.in"
    deck.write_text(deck_text, encoding="utf-8", newline="\n")
    imported: dict[str, Path] = {}
    if blocks["datafile"]:
        data_path = input_dir / f"{inputs.IMPORT_NAME}.dat"
        data_path.write_text(blocks["datafile"], encoding="utf-8", newline="\n")
        imported[inputs.IMPORT_NAME] = data_path

    invocation = solver14.execute_real(
        executable=Path(machine.executable),
        database=Path(machine.database),
        license_path=Path(machine.license),
        deck=deck,
        output_dir=raw_output_dir,
        threads=int(cfg["solver"]["threads"]),
        timeout_seconds=float(cfg["solver"]["solver_timeout_seconds"]),
        imported_files=imported,
        logs_dir=logs_dir,
    )
    demo16b.verify_quantum_outputs(_demo16b_style_config(cfg), raw_output_dir)

    # Compare the composition nextnano++ built against the one requested.
    alloy_path = demo16b.find_alloy_composition(raw_output_dir)
    z_real, al_real = demo16b.read_alloy_composition(alloy_path)
    intended = np.interp(z_real, profile.x_nm_continuous, profile.al_fraction_continuous)
    composition_error = float(np.max(np.abs(al_real - intended)))
    tolerance = float(cfg["grading"]["profile_tolerance"])
    if composition_error > tolerance:
        raise Solver20Error(
            f"case {case.case_id}: solver-realized composition error "
            f"{composition_error:.6g} exceeds grading.profile_tolerance {tolerance}"
        )
    return SolverInvocation(
        case_id=case.case_id, solver_pass=True,
        return_code=getattr(invocation, "return_code", None),
        output_dir=raw_output_dir, deck_path=deck,
        composition_max_error=composition_error,
        message="solver returned successfully and realized the requested profile",
    )


def _demo16b_style_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Demo 20's solver block under the ``nextnano`` key Demo 16B reads.

    ``demo16b.verify_quantum_outputs`` looks up ``cfg["nextnano"]``. Demo 20
    keeps the same fields under ``solver`` instead, so this is the same
    translation ``_demo14_style_config`` performs, narrowed to the two keys the
    output check actually reads.
    """

    return {
        "nextnano": {
            "parser_profile": str(cfg["solver"]["parser_profile"]),
            "quantum_region_name": str(cfg["solver"]["quantum_region_name"]),
        }
    }


def parse_case(
    cfg: Mapping[str, Any], case: cases.GradingCase, raw_output_dir: Path,
    case_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse one raw run through the Demo 11/14 chain.

    Returns ``(metrics, matrix_elements)``. ``metrics["physical_qc_valid"]`` is
    the inherited Demo 11/14 physical verdict; :mod:`s08_qc` decides what to do
    with it, and it is never conflated with the solver's return code.
    """

    enable_shared_imports()
    import demo14  # noqa: PLC0415
    import json

    optical_root = case_dir / "optical"
    parsed = optical_root / "parsed"
    plots = optical_root / "plots"
    parsed.mkdir(parents=True, exist_ok=True)
    plots.mkdir(parents=True, exist_ok=True)

    demo11_cfg = _demo14_style_config(cfg)
    g = grading.geometry(cfg)
    profile = grading.build_profile(cfg, case)
    metrics = demo14.analyse_real_trial(
        demo11_cfg,
        {"nextnano_output": raw_output_dir, "parsed": parsed, "plots": plots},
        _demo14_geometry(g), _demo14_profile(profile),
    )
    matrix_path = parsed / "matrix_elements.json"
    if not matrix_path.is_file():
        raise Solver20Error(
            f"case {case.case_id}: the parser did not write {matrix_path}."
        )
    matrix_elements = json.loads(matrix_path.read_text(encoding="utf-8"))
    return dict(metrics), matrix_elements


def _demo14_style_config(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Project the Demo 20 config into the shape the Demo 14 parser expects.

    Demo 19 reached the same parser by deep-copying Demo 14's own YAML and
    overwriting the fields it changed. Demo 20 keeps its own YAML authoritative
    and builds the projection explicitly here, so there is exactly one source of
    scientific truth and this function is a translation, not a second config.
    """

    enable_shared_imports()
    import copy
    import yaml

    demo14_yaml = (config20.DEMOS_DIR / "14_absolute_chi2_graded_acqw_bo"
                   / "demo.yaml")
    projected = copy.deepcopy(yaml.safe_load(demo14_yaml.read_text(encoding="utf-8")))
    g = grading.geometry(cfg)
    projected["experiment"]["name"] = cases.DEMO_ID
    projected["experiment"]["demo_id"] = cases.DEMO_ID
    projected["geometry"]["total_well_thickness_nm"] = g.total_well_nm
    projected["geometry"]["period_barrier_nm"] = g.period_barrier_nm
    projected["geometry"]["domain_padding_nm"] = g.outer_barrier_nm
    projected["geometry"]["quantum_region_padding_nm"] = float(
        cfg["geometry"]["quantum_region_padding_nm"])
    projected["mesh"]["active_region_grid_spacing_nm"] = float(
        cfg["mesh"]["active_region_grid_spacing_nm"])
    projected["mesh"]["outer_grid_spacing_nm"] = float(
        cfg["mesh"]["outer_grid_spacing_nm"])
    projected["materials"]["barrier_al_fraction"] = float(
        cfg["materials"]["barrier_al_fraction"])
    projected["materials"]["temperature_K"] = float(cfg["materials"]["temperature_K"])
    projected["states"].update({
        "number_of_electron_states": int(cfg["states"]["number_of_electron_states"]),
        "number_of_hole_states": int(cfg["states"]["number_of_hole_states"]),
        "output_state_count": int(cfg["states"]["output_state_count"]),
        "max_states_per_band": int(cfg["states"]["max_states_per_band"]),
    })
    projected["chi2"].update({
        "mode": str(cfg["chi2"]["mode"]),
        "target_wavelength_nm": float(cfg["chi2"]["target_wavelength_nm"]),
        "broadening_meV": float(cfg["chi2"]["broadening_meV"]),
        "max_states_per_band": int(cfg["states"]["max_states_per_band"]),
        "r_e_hh_nm": float(cfg["chi2"]["r_e_hh_nm"]),
        "nz_mode": str(cfg["chi2"]["nz_mode"]),
        "reference_period_nm": float(cfg["chi2"]["reference_period_nm"]),
        "focused_wavelength_nm": list(cfg["chi2"]["focused_wavelength_nm"]),
        "focused_wavelength_points": int(cfg["chi2"]["focused_wavelength_points"]),
        "broad_wavelength_nm": list(cfg["chi2"]["broad_wavelength_nm"]),
        "broad_wavelength_points": int(cfg["chi2"]["broad_wavelength_points"]),
    })
    projected["nextnano"].update({
        "quantum_region_name": str(cfg["solver"]["quantum_region_name"]),
        "dipole_polarization_name": str(cfg["solver"]["dipole_polarization_name"]),
        "parser_profile": str(cfg["solver"]["parser_profile"]),
        "bandedge_columns": dict(cfg["solver"]["bandedge_columns"]),
        "threads": int(cfg["solver"]["threads"]),
        "solver_timeout_seconds": float(cfg["solver"]["solver_timeout_seconds"]),
    })
    projected["paths"]["results_subdir"] = cases.DEMO_ID
    projected["grading"]["width_definition"] = str(cfg["grading"]["width_definition"])
    projected["grading"]["render"] = dict(cfg["grading"]["render"])
    return projected


def _demo14_geometry(g: grading.Geometry) -> Any:
    """Demo 20's geometry as the ``demo14.Geometry`` the parser expects."""

    enable_shared_imports()
    import demo14  # noqa: PLC0415

    return demo14.Geometry(
        asymmetry_s=(g.thick_well_nm - g.thin_well_nm) / g.total_well_nm,
        thick_well_nm=g.thick_well_nm,
        thin_well_nm=g.thin_well_nm,
        barrier_nm=g.tunnel_barrier_nm,
        total_well_nm=g.total_well_nm,
        active_start_nm=g.active_start_nm,
        active_end_nm=g.active_end_nm,
        barrier_centre_nm=g.barrier_centre_nm,
        domain_nm=g.domain_nm,
    )


def _demo14_profile(profile: grading.CompositionProfile) -> Any:
    """Demo 20's profile as the ``grading14.CompositionProfile`` the parser expects."""

    enable_shared_imports()
    import grading14  # noqa: PLC0415

    return grading14.CompositionProfile(
        x_nm=profile.x_nm,
        al_fraction=profile.al_fraction,
        x_nm_continuous=profile.x_nm_continuous,
        al_fraction_continuous=profile.al_fraction_continuous,
        request=profile.request,
        diagnostics=profile.diagnostics,
    )
