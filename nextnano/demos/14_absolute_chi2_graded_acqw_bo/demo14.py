"""Demo 14 orchestration: config -> Ax -> grading -> solver -> chi(2) -> checkpoint.

One campaign is 30 **completed** solver trials, not 30 proposals. A trial that is
physically unfavourable is a result and consumes a slot; a trial that fails for
infrastructure reasons is a bug, stops the campaign, and consumes nothing --
because discovering a pipeline defect at trial 1 and then proving it 29 more
times is the most expensive mistake this harness can make.

The loop is deliberately boring and writes everything down. Each trial gets its
directory before the solver is invoked, so a crash mid-solve still leaves the
inputs, the rendered composition profile and the partial output behind.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml

import chi2 as chi2mod
import grading14
import physics14
import runlog14
import solver14

DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[2]

PROFILE_FAMILIES = grading14.PROFILE_FAMILIES


class Demo14ConfigError(ValueError):
    """The configuration is internally inconsistent or incomplete."""


class TechnicalFailure(RuntimeError):
    """Infrastructure failed. Preserve everything and stop the campaign."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = Path(path) if path else DEMO_DIR / "demo.yaml"
    if not path.is_file():
        raise Demo14ConfigError(f"Demo 14 configuration not found: {path}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, Mapping):
        raise Demo14ConfigError(f"{path} did not parse to a mapping.")
    return dict(cfg)


def validate_config(cfg: Mapping[str, Any]) -> list[str]:
    """Fail fast on anything that would waste licensed time. Returns warnings."""

    warnings: list[str] = []
    for section in (
        "experiment", "materials", "geometry", "grading", "nextnano", "mesh",
        "states", "chi2", "k_parallel", "optimization", "constraints",
        "failure_policy", "logging", "checkpointing", "plotting",
        "paper_reference", "paths",
    ):
        if section not in cfg:
            raise Demo14ConfigError(f"configuration is missing the '{section}' section.")

    opt = cfg["optimization"]
    initial = int(opt["initialization_trials"])
    bo = int(opt["bo_trials"])
    target = int(opt["target_completed_trials"])
    if initial + bo != target:
        raise Demo14ConfigError(
            f"initialization_trials ({initial}) + bo_trials ({bo}) must equal "
            f"target_completed_trials ({target}); got {initial + bo}."
        )
    if int(opt.get("batch_size", 1)) != 1:
        raise Demo14ConfigError("Demo 14 beta runs one trial at a time (batch_size: 1).")

    space = opt["search_space"]
    families = list(space["grading_profile"]["values"])
    if "abrupt" in families:
        raise Demo14ConfigError(
            "Demo 14 is a grading study and has no abrupt branch; remove it from "
            "optimization.search_space.grading_profile.values."
        )
    unknown = sorted(set(families) - set(PROFILE_FAMILIES))
    if unknown:
        raise Demo14ConfigError(f"unknown grading profiles: {unknown}")
    if opt.get("stratify_initialization_by_profile", True):
        need = len(families) * int(opt.get("minimum_initial_per_profile", 2))
        if initial < need:
            raise Demo14ConfigError(
                f"stratified initialization needs at least {need} trials for "
                f"{len(families)} profiles, but initialization_trials is {initial}."
            )

    for name in (
        "asymmetry_s", "nominal_central_barrier_thickness_nm",
        "gaas_to_algaas_grading_width_10_90_nm", "algaas_to_gaas_grading_width_10_90_nm",
    ):
        spec = space[name]
        if float(spec["lower"]) >= float(spec["upper"]):
            raise Demo14ConfigError(f"{name}: lower must be < upper.")

    metric = cfg["chi2"]
    if str(metric.get("mode")) != "absolute":
        raise Demo14ConfigError(
            "Demo 14 optimizes an absolute pm/V susceptibility; chi2.mode must be "
            f"'absolute', got {metric.get('mode')!r}."
        )
    if metric.get("r_e_hh_nm") is None:
        raise Demo14ConfigError("chi2.r_e_hh_nm is required in absolute mode.")
    if abs(float(metric["r_e_hh_nm"]) - physics14.R_E_HH_NM) > 1e-9:
        warnings.append(
            f"chi2.r_e_hh_nm is {metric['r_e_hh_nm']} nm, not the published "
            f"{physics14.R_E_HH_NM} nm; chi(2) scales as r^2."
        )
    if str(metric.get("nz_mode")) not in physics14.NZ_MODES:
        raise Demo14ConfigError(
            f"chi2.nz_mode must be one of {physics14.NZ_MODES}."
        )

    timeout = float(cfg["nextnano"].get("solver_timeout_seconds", 0))
    if not math.isfinite(timeout) or timeout <= 0:
        raise Demo14ConfigError(
            "nextnano.solver_timeout_seconds must be finite and > 0; an unbounded "
            "solver can stall an unattended campaign indefinitely."
        )

    if cfg["workflow"].get("mock_solver"):
        warnings.append(
            "workflow.mock_solver is TRUE: results will be synthetic and marked "
            "scientific_valid=false. This is never a production setting."
        )
    return warnings


def objective_name(cfg: Mapping[str, Any]) -> str:
    return str(cfg["optimization"]["objective"])


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Geometry:
    """Layer thicknesses realized from one parameter vector."""

    asymmetry_s: float
    thick_well_nm: float
    thin_well_nm: float
    barrier_nm: float
    total_well_nm: float
    active_start_nm: float
    active_end_nm: float
    barrier_centre_nm: float
    domain_nm: tuple[float, float]

    def as_record(self) -> dict[str, Any]:
        return {
            "asymmetry_s": self.asymmetry_s,
            "thick_well_nm": self.thick_well_nm,
            "thin_well_nm": self.thin_well_nm,
            "nominal_central_barrier_thickness_nm": self.barrier_nm,
            "total_well_thickness_nm": self.total_well_nm,
            "active_start_nm": self.active_start_nm,
            "active_end_nm": self.active_end_nm,
            "barrier_centre_nm": self.barrier_centre_nm,
            "domain_start_nm": self.domain_nm[0],
            "domain_end_nm": self.domain_nm[1],
        }


def geometry_for(cfg: Mapping[str, Any], parameters: Mapping[str, Any]) -> Geometry:
    """Layer widths from asymmetry, with the total GaAs thickness held fixed.

    ``d_thick = D (1 + s) / 2`` and ``d_thin = D (1 - s) / 2`` -- the same
    convention as ``chi2.well_widths_from_asymmetry``, so a Demo 14 geometry and
    a Demo 11 one with the same ``s`` are the same structure.
    """

    total = float(cfg["geometry"]["total_well_thickness_nm"])
    s = float(parameters["asymmetry_s"])
    thick, thin = chi2mod.well_widths_from_asymmetry(s, total)
    barrier = float(parameters["nominal_central_barrier_thickness_nm"])
    padding = float(cfg["geometry"]["domain_padding_nm"])
    active_start = padding
    active_end = active_start + thick + barrier + thin
    return Geometry(
        asymmetry_s=s,
        thick_well_nm=thick,
        thin_well_nm=thin,
        barrier_nm=barrier,
        total_well_nm=total,
        active_start_nm=active_start,
        active_end_nm=active_end,
        barrier_centre_nm=active_start + thick + 0.5 * barrier,
        domain_nm=(0.0, active_end + padding),
    )


def build_grading(
    cfg: Mapping[str, Any], parameters: Mapping[str, Any], geometry: Geometry
) -> grading14.CompositionProfile:
    return grading14.build_profile(
        profile=str(parameters["grading_profile"]),
        barrier_thickness_nm=geometry.barrier_nm,
        gaas_to_algaas_width_10_90_nm=float(
            parameters["gaas_to_algaas_grading_width_10_90_nm"]
        ),
        algaas_to_gaas_width_10_90_nm=float(
            parameters["algaas_to_gaas_grading_width_10_90_nm"]
        ),
        barrier_centre_nm=geometry.barrier_centre_nm,
        domain_nm=geometry.domain_nm,
        mesh_nm=float(cfg["mesh"]["active_region_grid_spacing_nm"]),
        max_al_fraction=float(cfg["materials"]["barrier_al_fraction"]),
        continuous_oversample=int(cfg["grading"].get("continuous_oversample", 20)),
    )


def preflight(
    cfg: Mapping[str, Any], parameters: Mapping[str, Any]
) -> dict[str, Any]:
    """Per-candidate checks. Demo 14 should never reject; a rejection is a bug."""

    report: dict[str, Any] = {"accepted": True, "reasons": [], "checks": {}}
    try:
        geometry = geometry_for(cfg, parameters)
        profile = build_grading(cfg, parameters, geometry)
    except Exception as exc:
        report["accepted"] = False
        report["reasons"].append(f"{type(exc).__name__}: {exc}")
        report["checks"]["profile_constructed"] = False
        report["implementation_bug"] = True
        return report

    d = profile.diagnostics
    x_max = float(cfg["materials"]["barrier_al_fraction"])
    report["checks"] = {
        "profile_constructed": True,
        "profile_within_bounds": bool(d["profile_within_bounds"]),
        "profile_monotone_coordinates": bool(d["profile_monotone_coordinates"]),
        "peak_al_fraction": d["realized_peak_al_fraction"],
        "peak_al_within_nominal": bool(d["realized_peak_al_fraction"] <= x_max + 1e-9),
        "peak_referenced_widths_defined": bool(
            d["realized_gaas_to_algaas_grading_width_10_90_peakref_nm"] is not None
            and d["realized_algaas_to_gaas_grading_width_10_90_peakref_nm"] is not None
        ),
    }
    for name, ok in report["checks"].items():
        if isinstance(ok, bool) and not ok:
            report["accepted"] = False
            report["reasons"].append(f"preflight check failed: {name}")
    if not report["accepted"]:
        # There is no legitimate rejection in this parameterization.
        report["implementation_bug"] = True
        report["subresolution_grade"] = False
    return report


# ---------------------------------------------------------------------------
# Stratified initialization
# ---------------------------------------------------------------------------


def stratified_initial_design(
    cfg: Mapping[str, Any], rng: np.random.Generator
) -> list[dict[str, Any]]:
    """Initial points that give every grading family real coverage.

    Without this, a family can look inferior merely for having been sampled
    less, and the per-family comparison the campaign exists to make becomes
    unreadable.
    """

    opt = cfg["optimization"]
    space = opt["search_space"]
    families = list(space["grading_profile"]["values"])
    total = int(opt["initialization_trials"])
    per_family = int(opt.get("minimum_initial_per_profile", 2))

    def draw(name: str) -> float:
        spec = space[name]
        return float(rng.uniform(float(spec["lower"]), float(spec["upper"])))

    assignments: list[str] = []
    for fam in families:
        assignments.extend([fam] * per_family)
    while len(assignments) < total:
        assignments.append(families[len(assignments) % len(families)])
    assignments = assignments[:total]

    design: list[dict[str, Any]] = []
    for fam in assignments:
        design.append({
            "asymmetry_s": draw("asymmetry_s"),
            "nominal_central_barrier_thickness_nm": draw(
                "nominal_central_barrier_thickness_nm"
            ),
            "gaas_to_algaas_grading_width_10_90_nm": draw(
                "gaas_to_algaas_grading_width_10_90_nm"
            ),
            "algaas_to_gaas_grading_width_10_90_nm": draw(
                "algaas_to_gaas_grading_width_10_90_nm"
            ),
            "grading_profile": fam,
        })
    return design


# ---------------------------------------------------------------------------
# Constraint evaluation
# ---------------------------------------------------------------------------


def evaluate_constraints(
    cfg: Mapping[str, Any], metrics: Mapping[str, Any]
) -> dict[str, Any]:
    """Per-metric pass/fail, never a bare feasible boolean.

    A combined flag cannot answer "which constraint bound?", which is the first
    question asked of any infeasible trial.
    """

    limits = cfg["constraints"]
    rows: list[dict[str, Any]] = []

    def check(metric: str, value: Any, bound: Any, comparison: str) -> None:
        if value is None:
            passed = False
        elif comparison == "<=":
            passed = float(value) <= float(bound)
        elif comparison == ">=":
            passed = float(value) >= float(bound)
        else:
            passed = bool(value) == bool(bound)
        rows.append({
            "metric": metric, "value": value, "bound": bound,
            "comparison": comparison, "passed": bool(passed),
        })

    check("absolute_detuning_nm", metrics.get("absolute_detuning_nm"),
          limits["maximum_detuning_nm"], "<=")
    check("maximum_boundary_probability", metrics.get("maximum_boundary_probability"),
          limits["maximum_boundary_probability"], "<=")
    check("state_tracking_confidence", metrics.get("state_tracking_confidence"),
          limits["minimum_state_tracking_confidence"], ">=")
    check("orthonormality_error", metrics.get("orthonormality_error"),
          limits["maximum_orthonormality_error"], "<=")
    if limits.get("require_origin_independence"):
        check("origin_independence_valid", metrics.get("origin_independence_valid"), True, "==")
    if limits.get("require_expected_states"):
        check("required_states_valid", metrics.get("required_states_valid"), True, "==")
    if limits.get("require_physical_qc"):
        check("physical_qc_valid", metrics.get("physical_qc_valid"), True, "==")
    if limits.get("require_absolute_units_valid"):
        check("absolute_units_valid", metrics.get("absolute_units_valid"), True, "==")
    if limits.get("require_k_parallel_converged"):
        check("k_parallel_integration_converged",
              metrics.get("k_parallel_integration_converged"), True, "==")

    feasible = all(row["passed"] for row in rows)
    return {
        "rows": rows,
        "feasible": bool(feasible),
        "failed_metrics": [r["metric"] for r in rows if not r["passed"]],
    }


def sanity_alarms(metrics: Mapping[str, Any], profile_diag: Mapping[str, Any]) -> list[str]:
    """Suspicious-but-not-necessarily-fatal observations. Logged, never silent.

    A large chi(2) is explicitly *not* an alarm on its own -- the whole point of
    the campaign is to find large values, and rejecting them for being large
    would be assuming the answer.
    """

    alarms: list[str] = []
    value = metrics.get("chi2_xzx_abs_at_1550_pm_per_V")
    if value is None:
        alarms.append("objective is None")
    elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        alarms.append(f"objective is not finite: {value}")
    elif value == 0.0:
        alarms.append("objective is exactly zero")
    elif value > 1.0e6:
        alarms.append(f"objective {value:.3e} pm/V is far outside the expected scale")

    peak = metrics.get("peak_wavelength_nm")
    if peak is not None:
        for edge in (metrics.get("scan_start_nm"), metrics.get("scan_end_nm")):
            if edge is not None and abs(float(peak) - float(edge)) < 1e-6:
                alarms.append(f"peak sits exactly on a scan boundary ({peak} nm)")
    if profile_diag.get("realized_peak_al_fraction", 0.0) <= 0.0:
        alarms.append("rendered profile contains no aluminium")
    if not profile_diag.get("profile_within_bounds", True):
        alarms.append("rendered profile left the allowed composition range")
    gap = metrics.get("heavy_hole_anticrossing_gap_meV")
    if gap is not None and 0.0 <= float(gap) < 1.0:
        alarms.append(f"heavy-hole minimum spacing {gap} meV is inside the broadening")
    return alarms


# ---------------------------------------------------------------------------
# Trial records
# ---------------------------------------------------------------------------


def trial_id(index: int) -> str:
    return f"t{index:04d}"


def create_trial_directory(paths: runlog14.RunPaths, tid: str) -> dict[str, Path]:
    root = paths.trials / tid
    layout = {
        "root": root,
        "nextnano_input": root / "nextnano_input",
        "nextnano_output": root / "nextnano_output",
        "logs": root / "logs",
        "parsed": root / "parsed",
        "physics": root / "physics",
        "qc": root / "qc",
        "plots": root / "plots",
    }
    for path in layout.values():
        path.mkdir(parents=True, exist_ok=True)
    return layout


def write_grading_artifacts(
    layout: Mapping[str, Path], profile: grading14.CompositionProfile
) -> None:
    """The exact composition handed to the solver, plus how it was measured."""

    rows = profile.as_rows()
    header = "x_nm,al_fraction_requested_continuous,al_fraction_rendered\n"
    body = "".join(
        f"{r['x_nm']:.6f},{r['al_fraction_requested_continuous']:.8f},"
        f"{r['al_fraction_rendered']:.8f}\n" for r in rows
    )
    runlog14.write_text_atomic(layout["root"] / "grading_profile.csv", header + body)
    runlog14.write_json_atomic(
        layout["root"] / "grading_profile_metadata.json",
        {"request": dict(profile.request), "realized": dict(profile.diagnostics)},
    )


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


@dataclass
class TrialOutcome:
    trial_id: str
    index: int
    phase: str
    parameters: dict[str, Any]
    status: str                  # completed | infeasible | rejected | technical_failure
    metrics: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    geometry: dict[str, Any] = field(default_factory=dict)
    grading: dict[str, Any] = field(default_factory=dict)
    solver: dict[str, Any] = field(default_factory=dict)
    alarms: list[str] = field(default_factory=list)
    failure_stage: str | None = None
    failure_reason: str | None = None
    exception_type: str | None = None
    traceback_text: str | None = None
    scientific_valid: bool = True

    def objective(self) -> float | None:
        value = self.metrics.get("chi2_xzx_abs_at_1550_pm_per_V")
        if value is None:
            return None
        value = float(value)
        return None if (math.isnan(value) or math.isinf(value)) else value

    def as_record(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "trial_index": self.index,
            "generation_phase": self.phase,
            "parameters": self.parameters,
            "status": self.status,
            "objective_pm_per_V": self.objective(),
            "feasible": self.constraints.get("feasible"),
            "metrics": self.metrics,
            "constraints": self.constraints,
            "geometry": self.geometry,
            "grading": self.grading,
            "solver": self.solver,
            "anomalies": self.alarms,
            "failure_stage": self.failure_stage,
            "failure_reason": self.failure_reason,
            "exception_type": self.exception_type,
            "scientific_valid": self.scientific_valid,
        }


def _mock_metrics(
    cfg: Mapping[str, Any], outcome: solver14.MockOutcome
) -> dict[str, Any]:
    target = float(cfg["chi2"]["target_wavelength_nm"])
    peak_nm = outcome.peak_wavelength_nm
    value = outcome.chi2_abs_at_target_pm_per_V
    signed = None if peak_nm is None else float(peak_nm) - target
    return {
        "chi2_xzx_abs_at_1550_pm_per_V": value,
        "chi2_xzx_real_pm_per_V": None if value is None else float(value),
        "chi2_xzx_imag_pm_per_V": 0.0,
        "chi2_xzx_complex_m_per_V": None if value is None else float(value) * 1e-12,
        "peak_chi2_xzx_pm_per_V": outcome.peak_chi2_pm_per_V,
        "peak_wavelength_nm": peak_nm,
        "signed_detuning_nm": signed,
        "absolute_detuning_nm": None if signed is None else abs(signed),
        "detuning_side": None if signed is None else ("blue_of_target" if signed < 0 else "red_of_target"),
        "maximum_boundary_probability": outcome.maximum_boundary_probability,
        "state_tracking_confidence": outcome.state_tracking_confidence,
        "state_tracking_margin": 0.25,
        "orthonormality_error": outcome.orthonormality_error,
        "origin_independence_valid": True,
        "required_states_valid": True,
        "physical_qc_valid": outcome.behaviour != "qc_failure",
        "absolute_units_valid": True,
        "heavy_hole_anticrossing_gap_meV": 7.1,
        "k_parallel_integration_converged": True,
        "scan_start_nm": float(cfg["chi2"]["focused_wavelength_nm"][0]),
        "scan_end_nm": float(cfg["chi2"]["focused_wavelength_nm"][1]),
        solver14.MOCK_MARKER: True,
    }


def run_one_trial(
    *,
    cfg: Mapping[str, Any],
    paths: runlog14.RunPaths,
    events: runlog14.EventLog,
    timing: runlog14.TimingLog,
    logger: Any,
    index: int,
    phase: str,
    parameters: Mapping[str, Any],
    mock: bool,
    mock_behaviour: str = "success",
    machine: Any | None = None,
) -> TrialOutcome:
    """One proposal through the whole pipeline, with evidence written at each step."""

    tid = trial_id(index)
    layout = create_trial_directory(paths, tid)
    outcome = TrialOutcome(
        trial_id=tid, index=index, phase=phase, parameters=dict(parameters),
        status="technical_failure", scientific_valid=not mock,
    )
    events.emit("TRIAL_PROPOSED", trial_id=tid, stage="propose", status="ok",
                phase=phase, parameters=dict(parameters))
    runlog14.write_text_atomic(
        layout["root"] / "parameters_requested.yaml",
        yaml.safe_dump(runlog14.json_safe(dict(parameters)), sort_keys=True),
    )

    try:
        # --- preflight -----------------------------------------------------
        with timing.stage("preflight", tid):
            events.emit("PREFLIGHT_STARTED", trial_id=tid, stage="preflight")
            report = preflight(cfg, parameters)
            runlog14.write_json_atomic(layout["root"] / "preflight.json", report)
        if not report["accepted"]:
            outcome.status = "rejected"
            outcome.failure_stage = "preflight"
            outcome.failure_reason = "; ".join(report["reasons"])
            events.emit("PREFLIGHT_FAILED", trial_id=tid, stage="preflight",
                        status="error", message=outcome.failure_reason,
                        implementation_bug=True)
            if cfg["failure_policy"].get("subresolution_grade_is_a_bug", True):
                raise TechnicalFailure(
                    "Demo 14 is feasible by construction, so a preflight rejection "
                    f"is an implementation bug, not an expected outcome: "
                    f"{outcome.failure_reason}"
                )
            return outcome
        events.emit("PREFLIGHT_PASSED", trial_id=tid, stage="preflight", status="ok")

        # --- geometry and grading -----------------------------------------
        with timing.stage("grading", tid):
            geometry = geometry_for(cfg, parameters)
            profile = build_grading(cfg, parameters, geometry)
            write_grading_artifacts(layout, profile)
            outcome.geometry = geometry.as_record()
            outcome.grading = dict(profile.diagnostics)
        runlog14.write_text_atomic(
            layout["root"] / "parameters_realized.yaml",
            yaml.safe_dump(runlog14.json_safe({
                "geometry": outcome.geometry, "grading": outcome.grading,
            }), sort_keys=True),
        )
        events.emit("GEOMETRY_RENDERED", trial_id=tid, stage="grading", status="ok",
                    realized_peak_al_fraction=profile.diagnostics["realized_peak_al_fraction"],
                    grading_interfaces_overlap=profile.diagnostics["grading_interfaces_overlap"])

        # --- deck ----------------------------------------------------------
        with timing.stage("input_generation", tid):
            blocks = grading14.render_structure_blocks(
                profile, import_name=str(cfg["grading"].get("import_name", "al_profile"))
            )
            deck = layout["nextnano_input"] / "case.in"
            imported: dict[str, Path] = {}
            if blocks["datafile"]:
                data_path = layout["nextnano_input"] / (
                    f"{cfg['grading'].get('import_name', 'al_profile')}.dat"
                )
                runlog14.write_text_atomic(data_path, blocks["datafile"])
                imported["al_profile"] = data_path
            runlog14.write_text_atomic(deck, render_deck(cfg, geometry, profile, blocks))
        events.emit("NEXTNANO_INPUT_WRITTEN", trial_id=tid, stage="input",
                    status="ok", deck=str(deck),
                    imported_files=[str(p) for p in imported.values()])

        # --- solver --------------------------------------------------------
        with timing.stage("solver", tid):
            events.emit("SOLVER_STARTED", trial_id=tid, stage="solver", mock=mock)
            if mock:
                invocation, mock_outcome = solver14.execute_mock(
                    trial_id=tid, parameters=parameters, deck=deck,
                    output_dir=layout["nextnano_output"], logs_dir=layout["logs"],
                    behaviour=mock_behaviour,
                    target_wavelength_nm=float(cfg["chi2"]["target_wavelength_nm"]),
                    imported_files=imported,
                )
            else:
                invocation = solver14.execute_real(
                    executable=Path(machine.executable), database=Path(machine.database)
                    if getattr(machine, "database", None) else None,
                    license_path=Path(machine.license)
                    if getattr(machine, "license", None) else None,
                    deck=deck, output_dir=layout["nextnano_output"],
                    threads=int(cfg["nextnano"].get("threads", 1)),
                    timeout_seconds=float(cfg["nextnano"]["solver_timeout_seconds"]),
                    imported_files=imported, logs_dir=layout["logs"],
                )
                mock_outcome = None
            outcome.solver = invocation.as_record()
        events.emit("SOLVER_FINISHED", trial_id=tid, stage="solver", status="ok",
                    **{k: outcome.solver[k] for k in
                       ("solver_return_code", "solver_elapsed_seconds")})

        # --- analysis ------------------------------------------------------
        with timing.stage("chi2", tid):
            events.emit("CHI2_STARTED", trial_id=tid, stage="chi2")
            if mock:
                metrics = _mock_metrics(cfg, mock_outcome)
                metrics.update(mock_outcome.record)
            else:
                metrics = analyse_real_trial(cfg, layout, geometry, profile)
            outcome.metrics = metrics
            runlog14.write_json_atomic(
                layout["physics"] / "chi2_summary.json",
                {
                    "constants": physics14.constants_record(
                        physics14.settings_from_config(cfg)
                    ),
                    "metrics": metrics,
                    "scientific_valid": not mock,
                },
            )
        events.emit("CHI2_FINISHED", trial_id=tid, stage="chi2", status="ok",
                    objective=metrics.get("chi2_xzx_abs_at_1550_pm_per_V"))

        # --- QC ------------------------------------------------------------
        with timing.stage("qc", tid):
            constraints = evaluate_constraints(cfg, metrics)
            outcome.constraints = constraints
            outcome.alarms = sanity_alarms(metrics, outcome.grading)
            runlog14.write_json_atomic(layout["qc"] / "constraints.json", constraints)
            runlog14.write_json_atomic(
                layout["qc"] / "anomalies.json", {"anomalies": outcome.alarms}
            )
        for alarm in outcome.alarms:
            logger.warning("%s anomaly: %s", tid, alarm)

        objective = outcome.objective()
        if objective is None:
            outcome.status = "technical_failure"
            outcome.failure_stage = "chi2"
            outcome.failure_reason = "objective is not a finite number"
            events.emit("QC_FAILED", trial_id=tid, stage="qc", status="error",
                        message=outcome.failure_reason)
            raise TechnicalFailure(f"{tid}: {outcome.failure_reason}")

        outcome.status = "completed" if constraints["feasible"] else "infeasible"
        events.emit("QC_PASSED" if constraints["feasible"] else "QC_FAILED",
                    trial_id=tid, stage="qc",
                    status="ok" if constraints["feasible"] else "infeasible",
                    failed_metrics=constraints["failed_metrics"])

    except TechnicalFailure as exc:
        outcome.status = "technical_failure"
        outcome.failure_reason = outcome.failure_reason or str(exc)
        outcome.exception_type = type(exc).__name__
        outcome.traceback_text = traceback.format_exc()
        outcome.failure_stage = outcome.failure_stage or "unknown"
    except (solver14.SolverTimeout, solver14.SolverTechnicalFailure) as exc:
        outcome.status = "technical_failure"
        outcome.failure_stage = "solver"
        outcome.failure_reason = str(exc)
        outcome.exception_type = type(exc).__name__
        outcome.traceback_text = traceback.format_exc()
        events.emit("SOLVER_FAILED", trial_id=tid, stage="solver", status="error",
                    message=str(exc))
    except Exception as exc:  # noqa: BLE001 - deliberately broad, fully recorded
        outcome.status = "technical_failure"
        outcome.failure_stage = outcome.failure_stage or "unknown"
        outcome.failure_reason = f"{type(exc).__name__}: {exc}"
        outcome.exception_type = type(exc).__name__
        outcome.traceback_text = traceback.format_exc()

    if outcome.traceback_text:
        runlog14.write_text_atomic(
            layout["logs"] / "traceback.txt", outcome.traceback_text
        )
        logger.error("%s failed at %s: %s", tid, outcome.failure_stage,
                     outcome.failure_reason)

    runlog14.write_json_atomic(layout["root"] / "trial_result.json", outcome.as_record())
    runlog14.write_json_atomic(layout["root"] / "trial_manifest.json", {
        "trial_id": tid,
        "trial_index": index,
        "generation_phase": phase,
        "proposal_timestamp_utc": runlog14.utc_now(),
        "parameters_requested": dict(parameters),
        "parameters_realized": outcome.geometry,
        "grading_profile": parameters.get("grading_profile"),
        "solver": outcome.solver,
        "status": outcome.status,
        "failure_stage": outcome.failure_stage,
        "failure_reason": outcome.failure_reason,
        "exception_type": outcome.exception_type,
        "scientific_valid": outcome.scientific_valid,
        "paths": {k: str(v) for k, v in layout.items()},
    })
    events.emit(
        "TRIAL_COMPLETED" if outcome.status in ("completed", "infeasible")
        else "TRIAL_FAILED",
        trial_id=tid, stage="trial", status=outcome.status,
        objective=outcome.objective(),
    )
    return outcome


def render_deck(
    cfg: Mapping[str, Any],
    geometry: Geometry,
    profile: grading14.CompositionProfile,
    blocks: Mapping[str, str],
) -> str:
    """Fill the Demo 14 template. Kept here so the deck and the profile agree."""

    template_path = DEMO_DIR / str(cfg["nextnano"]["template"])
    text = template_path.read_text(encoding="utf-8")
    mesh = float(cfg["mesh"]["active_region_grid_spacing_nm"])
    outer = float(cfg["mesh"]["outer_grid_spacing_nm"])
    lo, hi = geometry.domain_nm
    padding = float(cfg["geometry"]["quantum_region_padding_nm"])
    grid_lines = "\n".join([
        f"        line{{ pos = {lo:.6f}  spacing = {outer:.6f} }}",
        f"        line{{ pos = {geometry.active_start_nm:.6f}  spacing = {mesh:.6f} }}",
        f"        line{{ pos = {geometry.active_end_nm:.6f}  spacing = {mesh:.6f} }}",
        f"        line{{ pos = {hi:.6f}  spacing = {outer:.6f} }}",
    ])
    substitutions = {
        "temperature_K": cfg["materials"]["temperature_K"],
        "import_block": blocks["import_block"],
        "grid_lines": grid_lines,
        "structure_regions": _structure_regions(cfg, geometry, blocks),
        "quantum_region_name": cfg["nextnano"]["quantum_region_name"],
        "quantum_start_nm": f"{max(lo, geometry.active_start_nm - padding):.6f}",
        "quantum_end_nm": f"{min(hi, geometry.active_end_nm + padding):.6f}",
        "number_of_electron_states": cfg["states"]["number_of_electron_states"],
        "number_of_hole_states": cfg["states"]["number_of_hole_states"],
        "output_state_count": cfg["states"]["output_state_count"],
        "dipole_polarization_name": cfg["nextnano"]["dipole_polarization_name"],
    }
    for key, value in substitutions.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def _structure_regions(
    cfg: Mapping[str, Any], geometry: Geometry, blocks: Mapping[str, str]
) -> str:
    """Region blocks: GaAs everywhere, then the graded barrier on top.

    The composition profile already encodes the barrier, so the graded region
    spans the whole active region rather than being cut at nominal layer edges;
    cutting it there would truncate an interface that deliberately extends past
    them when the two grades overlap.
    """

    lo, hi = geometry.domain_nm
    contact = "qw_contact"
    parts = [
        "    region{",
        f"        everywhere{{}}",
        '        binary{ name = "GaAs" }',
        f"        contact{{ name = {contact} }}",
        "    }",
        "    region{",
        f"        line{{ x = [{geometry.active_start_nm:.6f}, {geometry.active_end_nm:.6f}] }}",
        blocks["structure_block"].rstrip("\n"),
        "    }",
    ]
    return "\n".join(parts)


def analyse_real_trial(
    cfg: Mapping[str, Any],
    layout: Mapping[str, Path],
    geometry: Geometry,
    profile: grading14.CompositionProfile,
) -> dict[str, Any]:
    """Parse a real nextnano++ run and evaluate the absolute susceptibility.

    Delegates parsing to the Demo 11 machinery, which is what Demo 12 and 13
    already use, so a Demo 14 trial and a Demo 11 case of the same structure are
    the same calculation with the same parser provenance.
    """

    import demo11  # noqa: PLC0415 - imported lazily; Demo 11 pulls in a lot

    import adapter14

    demo11_cfg = adapter14.build_demo11_analysis_config_from_demo14(
        cfg, geometry, profile
    )
    observables, validation = demo11.analyse_case(
        demo11_cfg, layout["nextnano_output"], layout["parsed"], layout["plots"]
    )
    metrics = dict(observables)
    metrics.update({
        "physical_qc_valid": bool(validation.get("passed", False)),
        "absolute_units_valid": True,
        "scan_start_nm": float(cfg["chi2"]["focused_wavelength_nm"][0]),
        "scan_end_nm": float(cfg["chi2"]["focused_wavelength_nm"][1]),
    })
    target = float(cfg["chi2"]["target_wavelength_nm"])
    peak = metrics.get("peak_wavelength_nm")
    if peak is not None:
        signed = float(peak) - target
        metrics["signed_detuning_nm"] = signed
        metrics["absolute_detuning_nm"] = abs(signed)
        metrics["detuning_side"] = "blue_of_target" if signed < 0 else "red_of_target"
    # Demo 11 names the objective for its own mode; expose it under the Demo 14
    # name so the ledger, the manifest and Ax all agree on one key.
    for source in ("chi2_at_target_wavelength_abs", "relative_chi2_at_target_wavelength_abs"):
        if source in metrics and "chi2_xzx_abs_at_1550_pm_per_V" not in metrics:
            metrics["chi2_xzx_abs_at_1550_pm_per_V"] = metrics[source]
    return metrics
