"""Demo 13 — Ax Bayesian optimization of graded asymmetric coupled quantum wells.

This is the orchestrator.  It owns the run modes, the closed loop, the
provenance, and nothing else: the design space lives in :mod:`design13`, the Ax
layer in :mod:`axsearch13`, the metric extraction in :mod:`metrics13`, the state
tracking in :mod:`tracking13`, the tables in :mod:`tables13`, the figures in
:mod:`plots13`, and the prose in :mod:`report13`.

The physics is not reimplemented anywhere in Demo 13.  A trial is rendered by
``demo12.render_values`` and analysed by ``demo11.analyse_case`` -- the same two
functions Demo 12 uses -- so a Demo 13 trial and a Demo 12 grid case with the
same geometry are the same calculation, and the warm-start observations are
comparable by construction rather than by hope.
"""

from __future__ import annotations

import copy
import csv
import dataclasses
import datetime as dt
import importlib.util
import json
import math
import platform
from pathlib import Path
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO11_DIR = DEMO_DIR.parent / "11_paper_validation_interband_chi2_acqw"
DEMO12_DIR = DEMO_DIR.parent / "12_graded_interface_coupled_quantum_well_optimization"
for _path in (str(SHARED), str(DEMO11_DIR), str(DEMO12_DIR), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import chi2 as chi2mod  # noqa: E402
import outputs  # noqa: E402
import plots as plotting  # noqa: E402
import quantum1d  # noqa: E402
import sweeps  # noqa: E402
from demo_workflow import (  # noqa: E402
    DemoError,
    git_state,
    machine_summary,
    run_subdirectory,
    write_json_atomically,
    write_text_atomically,
)

import accounting13  # noqa: E402
import analysis13  # noqa: E402
import axsearch13  # noqa: E402
import design13  # noqa: E402
import derived13  # noqa: E402
import feasibility13  # noqa: E402
import grading13  # noqa: E402
import metrics13  # noqa: E402
import plots13  # noqa: E402
import replay13  # noqa: E402
import report13  # noqa: E402
import synthetic13  # noqa: E402
import tables13  # noqa: E402
import tracking13  # noqa: E402
import anchor13  # noqa: E402
import validation13  # noqa: E402


def _load_demo(name: str, path: Path):
    """Load a sibling demo module without duplicating its implementation."""

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DemoError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


demo12 = _load_demo("demo12_for_demo13", DEMO12_DIR / "demo12.py")
demo11 = demo12.demo11

#: Extraction contract version. Bumped when the meaning of a recorded metric
#: changes, so old and new trial records can never be silently mixed.
EXTRACTION_VERSION = "demo13-metrics-2"

#: Bumped whenever the Ax *search space* changes shape. A snapshot written under
#: one schema cannot be resumed under another -- the parameter names differ --
#: so the mismatch is refused with instructions rather than loaded into a
#: confusing half-state.
#: Bumped for v3: the barrier lower bound moved to 0.85 nm, the minimum
#: resolvable grade to 0.80 nm and the active mesh to 0.05 nm. None of those
#: changes the parameter *names*, so without this bump a v2 snapshot would still
#: have looked schema-compatible.
EXPERIMENT_SCHEMA_VERSION = "demo13-search-space-3"


def experiment_schema(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The identity of the search space a snapshot was written against.

    Parameter *names* are not enough. v2 and v3 use the same encoding, the same
    fraction parameterization and the same four parameter names, and differ only
    in their bounds and in the minimum resolvable grade -- so a name-only schema
    would have let a v2 checkpoint resume under v3's search space, silently
    treating observations at a 0.5 nm barrier and a 0.10 nm mesh as though they
    had been computed inside v3's space. The bounds and the mesh are therefore
    part of the identity, and any change to them makes the snapshot
    unresumable rather than quietly reinterpreted.
    """

    bounds = {
        spec.name: [spec.lower, spec.upper]
        for spec in design13.search_space_specs(cfg)
        if isinstance(spec, design13.RangeSpec)
    }
    choices = {
        spec.name: sorted(str(value) for value in spec.values)
        for spec in design13.search_space_specs(cfg)
        if isinstance(spec, design13.ChoiceSpec)
    }
    return {
        "experiment_schema_version": EXPERIMENT_SCHEMA_VERSION,
        "encoding": str(cfg["bo"]["search_space"].get("encoding", "hierarchical")),
        "parameterization": design13.grading_parameterization(cfg),
        "parameters": sorted(spec.name for spec in design13.search_space_specs(cfg)),
        "range_bounds": bounds,
        "choice_values": choices,
        "minimum_resolvable_grading_nm": design13.minimum_resolvable_grading_nm(cfg),
        # Changes what a stored grading fraction *means*, so two snapshots
        # written under different mappings describe different structures from
        # the same numbers. Identity, not a preference.
        "grading_fraction_spans_feasible_interval": design13.fraction_spans_feasible_interval(cfg),
        # The mesh is not an Ax parameter, but two observations computed at
        # different mesh spacings are not observations of the same function.
        "active_region_grid_spacing_nm": float(
            cfg["numerical"]["active_region_grid_spacing_nm"]
        ),
        "target_wavelength_nm": design13.target_wavelength_nm(cfg),
        "metric_broadening_meV": float(cfg["metric"]["broadening_meV"]),
        "number_of_electron_states": int(cfg["numerical"]["number_of_electron_states"]),
        "number_of_hole_states": int(cfg["numerical"]["number_of_hole_states"]),
        "domain_padding_nm": float(cfg["numerical"]["domain_padding_nm"]),
        "quantum_region_padding_nm": float(cfg["numerical"]["quantum_region_padding_nm"]),
        "tracking_minimum_confidence": float(
            cfg["state_tracking"]["minimum_confidence"]
        ),
        "tracking_minimum_assignment_margin": float(
            cfg["state_tracking"]["minimum_assignment_margin"]
        ),
        "tracking_energy_continuity_weight": float(
            cfg["state_tracking"]["energy_continuity_weight"]
        ),
    }

#: Sentinel: this schema field has no "before it existed" default, so a snapshot
#: that predates it cannot be judged compatible on that field at all.
_SCHEMA_NO_DEFAULT = object()

#: What each schema field meant *before it was added*, for snapshots written
#: without it. A field listed here can be introduced without invalidating every
#: existing checkpoint; a field not listed here cannot.
SCHEMA_FIELD_DEFAULTS: Mapping[str, Any] = {
    # v3 ran with the fraction spanning [0, maximum]; the interval mapping is
    # opt-in and postdates the v3 snapshot.
    "grading_fraction_spans_feasible_interval": False,
    # Physics/extraction settings added to the schema after v3 was completed.
    # These are their exact v3 values, so the immutable snapshot remains
    # loadable only under the calculation that produced it.
    "target_wavelength_nm": 1550.0,
    "metric_broadening_meV": 5.0,
    "number_of_electron_states": 4,
    "number_of_hole_states": 4,
    "domain_padding_nm": 0.0,
    "quantum_region_padding_nm": 6.0,
    "tracking_minimum_confidence": 0.60,
    "tracking_minimum_assignment_margin": 0.15,
    "tracking_energy_continuity_weight": 0.05,
}

RUN_MODES: frozenset[str] = frozenset(
    {
        "synthetic_smoke_test",
        "demo12_replay",
        "prepare_candidates",
        "run_pending_candidates",
        "closed_loop",
        "analyze_existing_results",
        "validate_top_designs",
    }
)


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def _require_mapping(cfg: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = cfg.get(name)
    if not isinstance(value, Mapping):
        raise DemoError(f"demo.yaml: {name} must be a mapping")
    return value


def validate_demo13_config(cfg: Mapping[str, Any]) -> None:
    """Check the relationships the scalar schema cannot express."""

    workflow = _require_mapping(cfg, "workflow")
    mode = str(workflow.get("mode", "closed_loop"))
    if mode not in RUN_MODES:
        raise DemoError(
            f"workflow.mode must be one of {sorted(RUN_MODES)}, got {mode!r}"
        )
    bo = _require_mapping(cfg, "bo")
    if str(bo.get("library", "ax")) != "ax":
        raise DemoError("bo.library must be 'ax'; Demo 13 optimizes through the Ax platform")
    for name in ("num_initial_trials", "num_iterations", "batch_size"):
        value = bo.get(name)
        if not isinstance(value, int) or isinstance(value, bool):
            raise DemoError(f"bo.{name} must be an integer, got {value!r}")
    if int(bo["num_initial_trials"]) < 1:
        raise DemoError("bo.num_initial_trials must be at least 1")
    if int(bo["num_iterations"]) < 0:
        raise DemoError("bo.num_iterations cannot be negative")
    if int(bo["batch_size"]) < 1:
        raise DemoError("bo.batch_size must be at least 1")
    # Ax needs a model before it can propose anything, and a model needs data.
    if int(bo["num_initial_trials"]) < 2 and int(bo["num_iterations"]) > 0:
        raise DemoError(
            "bo.num_initial_trials must be at least 2 before any BO iteration can "
            "fit a surrogate"
        )
    axsearch13.build_optimization_spec(cfg)
    design13.search_space_specs(cfg)
    encoding = str(bo["search_space"].get("encoding", "hierarchical"))
    if encoding == "hierarchical":
        design13.graded_thickness_bounds(cfg)
        design13.graded_profiles(cfg)
    _validate_grading_resolution(cfg)
    _validate_stage5_isolation(cfg)
    tracking = _require_mapping(cfg, "state_tracking")
    for name, value in (tracking.get("parameter_scales") or {}).items():
        if float(value) <= 0:
            raise DemoError(f"state_tracking.parameter_scales.{name} must be positive")
    if not 0.0 <= float(tracking.get("minimum_confidence", 0.6)) <= 1.0:
        raise DemoError("state_tracking.minimum_confidence must lie in [0, 1]")


def stage5_state_dir(cfg: Mapping[str, Any], results_root: Path) -> Path:
    """Where Stage 5 writes. Never the optimization experiment.

    Defaults to ``<experiment>_stage5`` beside it, so the isolation holds even
    when nothing is configured.  The settings themselves come from
    :mod:`validation13`, which is the one place Stage 5 numbers are defined.
    """

    workflow = cfg.get("workflow") or {}
    # Same construction as `experiment_state_dir`, including the demo-id
    # segment. Without it Stage 5 landed a level up, beside *other demos'*
    # result folders, and the "is this the experiment directory?" comparison was
    # between two differently-built paths -- so it could never be equal and the
    # check passed vacuously.
    root = Path(results_root) / str(cfg["demo_id"])
    configured = validation13.settings(cfg).output_state_dir
    if configured:
        return root / str(configured)
    experiment = str(workflow.get("experiment_state_dir", "demo13_ax_experiment"))
    return root / f"{experiment}_stage5"


def _validate_stage5_isolation(cfg: Mapping[str, Any]) -> None:
    """Refuse a configuration that would let Stage 5 write into the campaign.

    Startup-time name check only: the results root is not known here.  The
    load-bearing check is :func:`validation13.assert_isolated`, which runs on
    the resolved destination path in :func:`run_validation_study` and catches
    symlinks, aliases, containment and any directory holding a checkpoint or
    ledger. This one exists so an obviously wrong YAML fails before anything
    else happens.
    """

    # Surfaces a malformed gate (wrong case count, reference mesh repeated,
    # unnamed anchor) at startup rather than at the first paid solver call.
    resolved = validation13.settings(cfg)
    configured = resolved.output_state_dir
    if not configured:
        return
    experiment = str((cfg.get("workflow") or {}).get("experiment_state_dir", ""))
    if str(configured).strip() == experiment.strip():
        raise DemoError(
            "validation_study.output_state_dir must not be the optimization "
            f"experiment directory ({experiment!r}). Stage 5 writes validation and "
            "robustness cases; the optimization experiment holds the immutable "
            "ledger of a licensed campaign. Point Stage 5 at its own directory, "
            f"for example {experiment}_stage5."
        )
    # Case-folded, matching `is_protected_experiment_dir`: on Windows a
    # differently-cased name is the same directory.
    if str(configured).strip().casefold() in {
        name.casefold() for name in validation13.PROTECTED_EXPERIMENT_NAMES
    }:
        raise DemoError(
            f"validation_study.output_state_dir={configured!r} names a protected "
            "optimization experiment. Stage 5 must write to its own directory."
        )


def _validate_grading_resolution(cfg: Mapping[str, Any]) -> None:
    """Keep the two grading minimums, and the mesh, mutually consistent.

    v2 shipped ``minimum_graded_thickness_nm: 0.10`` alongside
    ``minimum_grid_points_per_grade: 10`` at a 0.10 nm mesh, which demands
    1.0 nm. Nothing complained, and the result was that "graded" designs one
    mesh cell wide -- steps, not ramps -- were accepted as evidence about
    grading. Each of these checks would have caught it.
    """

    space = cfg["bo"]["search_space"]
    minimum_resolvable = design13.minimum_resolvable_grading_nm(cfg)
    collapse = float(space.get("minimum_graded_thickness_nm", 0.0))
    if minimum_resolvable > 0 and collapse < minimum_resolvable:
        raise DemoError(
            "bo.search_space.minimum_graded_thickness_nm "
            f"({collapse:g} nm) is below "
            "bo.search_space.minimum_mesh_resolvable_nonzero_grading_nm "
            f"({minimum_resolvable:g} nm), so a grade narrower than the mesh can "
            "resolve would be canonicalized as a real graded design and taught to "
            "the surrogate. Raise the collapse threshold to at least the "
            "resolvable minimum."
        )
    if minimum_resolvable <= 0:
        return

    grading = cfg.get("grading") or {}
    active = float(cfg["numerical"]["active_region_grid_spacing_nm"])
    points = int(grading.get("minimum_grid_points_per_grade", 10))
    # Demo 12 refines *inside* a grade to honour this, so the global mesh does
    # not have to. The check is that the demand is satisfiable at all.
    if points >= 2 and minimum_resolvable / points <= 0.0:
        raise DemoError("grading.minimum_grid_points_per_grade is unsatisfiable")

    # A non-native profile is built from constant-composition sublayers. Each
    # one has to be wider than the grade's own mesh spacing, or the staircase is
    # finer than the grid that samples it.
    sublayers = int(grading.get("staircase_sublayers", 16))
    profiles = set(design13.graded_profiles(cfg))
    if sublayers >= 1 and profiles - design13.NATIVE_PROFILES:
        sublayer_nm = minimum_resolvable / sublayers
        grade_spacing = min(active, minimum_resolvable / max(points, 2))
        if sublayer_nm < grade_spacing:
            raise DemoError(
                f"the narrowest resolvable grade ({minimum_resolvable:g} nm) split "
                f"into {sublayers} staircase sublayers gives {sublayer_nm:g} nm per "
                f"sublayer, finer than the {grade_spacing:g} nm mesh inside the "
                "grade. Raise grading.minimum_grid_points_per_grade, lower "
                "grading.staircase_sublayers, or raise the resolvable minimum; "
                f"non-native profiles ({', '.join(sorted(profiles - design13.NATIVE_PROFILES))}) "
                "are built this way."
            )


def experiment_state_dir(cfg: Mapping[str, Any], results_root: Path) -> Path:
    workflow = cfg.get("workflow") or {}
    name = str(workflow.get("experiment_state_dir", "demo13_ax_experiment"))
    return Path(results_root) / str(cfg["demo_id"]) / name


# ---------------------------------------------------------------------------
# one trial
# ---------------------------------------------------------------------------


def _trial_case(
    trial_index: int, parameters: Mapping[str, Any], cfg: Mapping[str, Any], iteration: int
) -> sweeps.CaseSpec:
    canonical = design13.canonicalize(parameters, cfg)
    resolved = design13.resolve_config(parameters, cfg)
    return sweeps.CaseSpec(
        case_id=f"t{int(trial_index):04d}",
        label=(
            f"s={canonical['asymmetry_s']:.4g}, "
            f"b={canonical['central_barrier_thickness_nm']:.4g} nm, "
            f"g={canonical['grading_thickness_nm']:.4g} nm, "
            f"{canonical['grading_profile']}"
        ),
        swept=dict(canonical),
        config=resolved,
        metadata={
            "trial_index": int(trial_index),
            "iteration": int(iteration),
            "sweep_kind": "ax_trial",
        },
    )


def archive_unexecuted_run_dir(run_dir: Path) -> str | None:
    """Move a never-executed trial directory aside so the trial can be rerun.

    A pending trial already has a directory: the run that proposed it wrote the
    generated deck there and then skipped execution, because that machine had no
    licensed solver.  Executing it later has to write into the same place, and
    the shared layout builder refuses to reuse *any* run directory -- which is
    the right default, since it is what stops a rerun silently clobbering real
    results.

    So the stale attempt is renamed aside rather than deleted.  It contains no
    physics, only an input and a manifest saying the solver was skipped, but
    keeping it costs nothing and leaves the audit trail intact.  A directory
    holding a *completed* run is never touched; reaching that state would mean
    the ledger and the filesystem disagree about what has already been paid for,
    and that is worth stopping on.
    """

    run_dir = Path(run_dir)
    if not run_dir.exists():
        return None
    manifest = run_dir / "run_manifest.json"
    status: str | None = None
    if manifest.is_file():
        try:
            status = json.loads(manifest.read_text(encoding="utf-8")).get(
                "completion_status"
            )
        except (json.JSONDecodeError, OSError):
            status = None
    if status == "completed":
        raise DemoError(
            f"{run_dir} already holds a completed nextnano++ run, but this trial "
            "is not recorded as terminal in the ledger. Refusing to overwrite a "
            "licensed result; reconcile the ledger and the run directory by hand."
        )
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archived = run_dir.with_name(f"{run_dir.name}.superseded-{stamp}")
    run_dir.rename(archived)
    return str(archived)


def run_trial(
    *,
    context: sweeps.RunContext,
    trial_index: int,
    parameters: Mapping[str, Any],
    iteration: int,
    state_dir: Path,
) -> tuple[sweeps.CaseResult, sweeps.CaseSpec]:
    """Render, run and analyse one candidate with the Demo 11/12 machinery."""

    cfg = context.cfg
    case = _trial_case(trial_index, parameters, cfg, iteration)
    run_dir = state_dir / "runs" / case.case_id
    archived = archive_unexecuted_run_dir(run_dir)
    result = sweeps.execute_case(
        demo_dir=context.demo_dir,
        spec=case,
        machine=context.machine,
        run_dir=run_dir,
        render_values=demo12.render_values,
        analyse=demo11.analyse_case,
        dependency_report=context.dependency_report,
    )
    # Demo 12's requested-profile artifact is what the realized alloy output is
    # validated against; writing it here keeps a Demo 13 trial directory
    # inspectable with exactly the Demo 12 procedure.
    try:
        demo12._write_requested_profile(case, result.run_dir)
    except Exception as exc:  # pragma: no cover - defensive
        result.warnings.append(f"requested composition profile not written: {exc}")
    if result.solver_success:
        try:
            realized = demo12._extract_realized_composition(case, result)
        except Exception as exc:
            result.status = "failed"
            result.failure_reason = f"grading profile validation failed: {exc}"
            result.validation["grading_profile_realized"] = False
            result.validation["passed"] = False
        else:
            if realized.get("profile_validation_passed") is False:
                result.validation["grading_profile_realized"] = False
                result.validation["passed"] = False
    return result, case


def _tracking_for(
    result: sweeps.CaseResult,
    trial_index: int,
    parameters: Mapping[str, Any],
    cfg: Mapping[str, Any],
    history: list[tracking13.TrialStates],
) -> tuple[dict[str, Any], tracking13.TrialStates | None]:
    if not result.solver_success:
        return {}, None
    # The solver's own energies, in hand from this trial's analysis. Passing them
    # is what keeps the heavy-hole branch off an index sequence; see
    # tracking13.StateEnergyError for why that substitution is not neutral.
    try:
        states = tracking13.load_trial_states(
            trial_index,
            design13.canonicalize(parameters, cfg),
            result.run_dir / "extracted",
            observables=result.observables,
        )
    except tracking13.StateEnergyError as exc:
        # Scoped to this trial rather than fatal to the campaign: licensed solver
        # time already spent on the other trials is not thrown away. The trial
        # still cannot complete, because a null confidence is a null value for a
        # constrained metric and `metrics13.ax_raw_data` refuses to report it.
        result.warnings.append(f"state tracking unavailable: {exc}")
        return (
            {
                "state_tracking_confidence": None,
                "method": "unavailable: real state energies missing",
                "state_tracking_error": str(exc),
                "energy_provenance": tracking13.UNAVAILABLE_ENERGY_LABEL,
            },
            None,
        )
    if states is None:
        return (
            {
                "state_tracking_confidence": None,
                "method": "unavailable: no envelopes.csv for this trial",
                "energy_provenance": tracking13.UNAVAILABLE_ENERGY_LABEL,
            },
            None,
        )
    reference = tracking13.choose_reference(states.parameters, history, cfg)
    record = tracking13.track_against(states, reference, cfg)
    return record, states


def _provenance(
    *,
    cfg: Mapping[str, Any],
    context: sweeps.RunContext,
    ax_versions: Mapping[str, Any],
    case: sweeps.CaseSpec,
    result: sweeps.CaseResult,
    generation: Mapping[str, Any],
) -> dict[str, Any]:
    """Section 18: everything needed to reconstruct one trial later."""

    commit, dirty = git_state()
    generated = result.run_dir / "generated_input" / "case.in"
    return {
        "extraction_version": EXTRACTION_VERSION,
        "git_commit": commit,
        "git_dirty": dirty,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "ax_version": ax_versions.get("ax_version_installed"),
        "ax_api": ax_versions.get("ax_api"),
        "solver_executable": machine_summary(context.machine).get("executable"),
        "solver_run_enabled": context.machine.run_solver,
        "random_seed": cfg["bo"].get("random_seed"),
        "input_file_path": str(generated) if generated.is_file() else None,
        "output_directory_path": str(result.run_dir),
        "resolved_config_path": str(result.run_dir / "demo_resolved.yaml"),
        "case_id": case.case_id,
        "case_label": case.label,
        "completion_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        **{f"generation_{key}": value for key, value in dict(generation).items()},
    }


def _geometry_fields(case: sweeps.CaseSpec) -> dict[str, Any]:
    scientific = case.config["scientific"]
    return {
        "resolved_wide_well_nm": float(scientific["thick_well_nm"]),
        "resolved_narrow_well_nm": float(scientific["thin_well_nm"]),
        "resolved_central_barrier_nm": float(scientific["tunnel_barrier_nm"]),
        "grading_implementation": case.config["grading"].get("implementation"),
    }


# ---------------------------------------------------------------------------
# the closed loop
# ---------------------------------------------------------------------------


class Experiment:
    """The Ax client, its snapshot, and the ledger beside it."""

    def __init__(
        self,
        cfg: Mapping[str, Any],
        state_dir: Path,
        *,
        warm_start: Sequence[Mapping[str, Any]] = (),
        read_only: bool = False,
    ) -> None:
        """``read_only`` forbids every write into the experiment state directory.

        Reanalysis of a finished licensed study must be able to prove it changed
        nothing.  Without this flag the constructor alone rewrote
        ``demo_yaml_snapshot.yaml`` and ``experiment_schema.json`` on every
        load, and created an empty experiment if the directory was missing --
        which would silently manufacture a brand-new study rather than report
        that the requested one is not there.
        """

        self.cfg = cfg
        self.state_dir = Path(state_dir)
        self.read_only = bool(read_only)
        if not self.read_only:
            self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = axsearch13.Ledger(self.state_dir, read_only=self.read_only)
        self.spec = axsearch13.build_optimization_spec(cfg)
        self.versions = axsearch13.check_ax_version(cfg)
        self.snapshot_path = self.state_dir / "ax_experiment_snapshot.json"
        self.warm_start_path = self.state_dir / "warm_start_attachments.json"
        self.resumed = False
        self.warm_start_attachments: list[dict[str, Any]] = []
        self.schema_path = self.state_dir / "experiment_schema.json"
        resume = bool((cfg.get("workflow") or {}).get("resume", True))
        if self.read_only and not self.snapshot_path.is_file():
            # Creating the study here would produce an empty experiment named
            # like the real one, and every report downstream would describe it
            # as if it were the licensed run.
            existing = (
                sorted(
                    path.name
                    for path in self.state_dir.parent.iterdir()
                    if path.is_dir() and (path / "ax_experiment_snapshot.json").is_file()
                )
                if self.state_dir.parent.is_dir()
                else []
            )
            raise DemoError(
                f"analysis mode found no Ax snapshot in {self.state_dir}. It will not "
                "create one, because an empty experiment would then be reported as "
                "though it were the completed study.\n"
                f"Experiment directories that do hold a snapshot: "
                + (", ".join(existing) if existing else "(none)")
                + "\nSet workflow.experiment_state_dir to the one you meant."
            )
        if resume and self.snapshot_path.is_file():
            self._check_schema_compatible(cfg)
            self.client = axsearch13.load_client(self.snapshot_path)
            self.resumed = True
            if self.warm_start_path.is_file():
                self.warm_start_attachments = json.loads(
                    self.warm_start_path.read_text(encoding="utf-8")
                )
        else:
            self.client = axsearch13.create_client(cfg, self.spec)
            # Warm-start observations may only be attached to a *new*
            # experiment. Re-attaching them on resume would duplicate them in
            # the surrogate's training data every time the study restarts.
            if warm_start:
                self.warm_start_attachments = axsearch13.attach_warm_start(
                    self.client, cfg, self.spec, warm_start
                )
                write_json_atomically(self.warm_start_path, self.warm_start_attachments)
            self.checkpoint()
        if not self.read_only:
            write_text_atomically(
                self.state_dir / "demo_yaml_snapshot.yaml",
                yaml.safe_dump(dict(cfg), sort_keys=True),
            )
            write_json_atomically(self.schema_path, experiment_schema(cfg))

    def _check_schema_compatible(self, cfg: Mapping[str, Any]) -> None:
        """Refuse to resume a snapshot whose search space no longer matches."""

        wanted = experiment_schema(cfg)
        if not self.schema_path.is_file():
            # Written before schema stamping existed. Its parameters are
            # discoverable from the snapshot itself, so say what to do rather
            # than guess.
            raise DemoError(
                f"{self.state_dir} holds an Ax snapshot with no recorded search-space "
                "schema, so it predates the grading parameterization change and "
                "cannot be safely resumed. Either point workflow.experiment_state_dir "
                "at a new directory, or set bo.search_space.parameterization back to "
                "'thickness' and delete experiment_schema.json to pin the old shape."
            )
        stored = json.loads(self.schema_path.read_text(encoding="utf-8"))
        differences = [
            f"{key}: snapshot has {stored.get(key)!r}, configuration asks for {value!r}"
            for key, value in wanted.items()
            # A schema field added after a snapshot was written is absent from
            # it. That absence means "whatever the behaviour was before the
            # field existed", so it is compatible with exactly that default and
            # incompatible with anything else. Without this, adding any new
            # identity field would invalidate every existing checkpoint.
            if key not in stored
            and value != SCHEMA_FIELD_DEFAULTS.get(key, _SCHEMA_NO_DEFAULT)
            or key in stored
            and stored[key] != value
        ]
        if differences:
            detail = "\n  ".join(differences)
            raise DemoError(
                "cannot resume this experiment: the Ax search space has changed.\n  "
                + detail
                + f"\nThe snapshot in {self.state_dir} was built with different "
                "parameters, and Ax cannot reinterpret its trials under new ones. "
                "Either restore the configuration above, or start a fresh study by "
                "pointing workflow.experiment_state_dir at a new directory. The old "
                "directory is never modified."
            )

    def _refuse_if_read_only(self, action: str) -> None:
        """Turn "analysis must not mutate" from a convention into an exception.

        A silent no-op would be worse than an error: the run would appear to
        succeed while the caller believed it had generated or completed a
        trial.
        """

        if self.read_only:
            raise DemoError(
                f"refusing to {action}: this experiment was opened read-only for "
                "analysis. Reanalysis never generates candidates, never completes "
                "or fails trials, and never rewrites the checkpoint."
            )

    def checkpoint(self) -> None:
        self._refuse_if_read_only("write the Ax checkpoint")
        axsearch13.save_client(self.client, self.snapshot_path)

    @property
    def plan(self) -> dict[str, Any]:
        return axsearch13.plan(self.cfg, self.ledger)

    def next_trial_ordinal(self) -> int:
        return len(self.ledger.records())

    def generate(self, count: int) -> list[axsearch13.Candidate]:
        self._refuse_if_read_only("generate candidates")
        candidates = axsearch13.generate_candidates(
            self.client,
            self.cfg,
            self.ledger,
            count=count,
            trial_ordinal=self.next_trial_ordinal(),
        )
        self.checkpoint()
        return candidates

    def complete(self, trial_index: int, raw_data: Mapping[str, float]) -> None:
        self._refuse_if_read_only("complete a trial")
        self.client.complete_trial(int(trial_index), raw_data=dict(raw_data))
        self.checkpoint()

    def fail(self, trial_index: int, reason: str) -> None:
        self._refuse_if_read_only("fail a trial")
        self.client.mark_trial_failed(int(trial_index), failed_reason=str(reason)[:400])
        self.checkpoint()

    def abandon(self, trial_index: int, reason: str) -> None:
        self._refuse_if_read_only("abandon a trial")
        try:
            self.client.mark_trial_abandoned(int(trial_index))
        except Exception:  # pragma: no cover - Ax version tolerant
            self.client.mark_trial_failed(int(trial_index), failed_reason=reason[:400])
        self.checkpoint()


def _record_trial(
    experiment: Experiment,
    *,
    candidate: axsearch13.Candidate,
    record: Mapping[str, Any],
    status: str,
    reported_to_ax_as: str,
    provenance: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "trial_index": candidate.trial_index,
        "iteration": candidate.iteration,
        "candidate_id": f"t{candidate.trial_index:04d}",
        "parameters": dict(candidate.parameters),
        "canonical_parameters": dict(candidate.canonical),
        "status": status,
        "reported_to_ax_as": reported_to_ax_as,
        **{key: value for key, value in dict(candidate.generation).items()},
        **dict(record),
        **dict(provenance),
        **dict(extra or {}),
    }
    experiment.ledger.write(payload)
    return payload


def _accepted_candidates(
    experiment: Experiment,
    cfg: Mapping[str, Any],
    wanted: int,
    rejection_log: list[dict[str, Any]],
) -> tuple[list[axsearch13.Candidate], list[dict[str, Any]]]:
    """Ask Ax for candidates until ``wanted`` of them survive preflight.

    A proposal rejected here never launches nextnano and never consumes one of
    the requested BO iterations; a replacement is requested inside the same
    iteration. The attempt limit is what stops this becoming an infinite loop
    when the feasible region is empty.
    """

    limit = int(cfg["bo"].get("max_candidate_regeneration_attempts", 20))
    if limit < 1:
        raise DemoError("bo.max_candidate_regeneration_attempts must be at least 1")
    accepted: list[axsearch13.Candidate] = []
    events: list[dict[str, Any]] = []
    attempt = 0
    while len(accepted) < wanted and attempt < limit:
        proposals = experiment.generate(1)
        if not proposals:
            break
        for candidate in proposals:
            attempt += 1
            seen = axsearch13.seen_design_hashes(experiment.ledger, cfg)
            verdict = axsearch13.preflight(candidate.parameters, cfg, seen)
            if verdict["accepted"]:
                candidate.design_hash = verdict["design_hash"]
                candidate.preflight = verdict
                accepted.append(candidate)
                continue
            # Rejected: abandon in Ax, record immutably, and try again.
            experiment.abandon(candidate.trial_index, verdict["rejection_reason"])
            record = {
                "trial_valid": False,
                "trial_outcome_class": metrics13.OUTCOME_INVALID,
                "objective_available": False,
                "rejection_reason": verdict["rejection_reason"],
                "failure_reason": None,
                "design_hash": verdict["design_hash"],
                "duplicate_of_trial": verdict["duplicate_of_trial"],
                "maximum_feasible_grading_thickness_nm": verdict["maximum_feasible_grading_nm"],
                "realized_grading_thickness_nm": verdict["realized_grading_thickness_nm"],
                "proposed_grading_fraction": verdict["proposed_grading_fraction"],
                "geometry_reason": verdict["geometry_reason"],
                "solver_launched": False,
                **{
                    f"parameter_{name}": value
                    for name, value in design13.physical_design(
                        verdict["canonical"]
                    ).items()
                },
            }
            _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="rejected",
                reported_to_ax_as="abandoned",
                provenance={"extraction_version": EXTRACTION_VERSION},
            )
            rejection_log.append(
                {
                    "requested_bo_iteration": candidate.iteration,
                    "proposal_attempt": attempt,
                    "ax_trial_index": candidate.trial_index,
                    "original_parameters": dict(candidate.parameters),
                    "canonical_parameters": design13.physical_design(verdict["canonical"]),
                    "maximum_feasible_grading_thickness_nm": verdict["maximum_feasible_grading_nm"],
                    "realized_grading_thickness_nm": verdict["realized_grading_thickness_nm"],
                    "proposed_grading_fraction": verdict["proposed_grading_fraction"],
                    "canonical_hash": verdict["design_hash"],
                    "rejection_reason": verdict["rejection_reason"],
                    "duplicate_of_trial": verdict["duplicate_of_trial"],
                    "replacement_trial_index": None,
                    "solver_launched": False,
                }
            )
            events.append(
                {
                    "stage": "candidate_rejected",
                    "trial_index": candidate.trial_index,
                    "reason": verdict["rejection_reason"],
                }
            )
    # Attribute each rejection to the replacement that eventually ran.
    if accepted and rejection_log:
        replacement = accepted[0].trial_index
        for row in reversed(rejection_log):
            if row["replacement_trial_index"] is None:
                row["replacement_trial_index"] = replacement
    return accepted, events


def closed_loop(
    context: sweeps.RunContext,
    experiment: Experiment,
    *,
    generate: bool = True,
    run_solver_trials: bool = True,
) -> dict[str, Any]:
    """Run pending trials, then iterate until the configured budget is met."""

    cfg = context.cfg
    rejection_log: list[dict[str, Any]] = []
    counts = design13.expected_evaluation_counts(cfg)
    batch = counts["batch_size"]
    history: list[tracking13.TrialStates] = []
    events: list[dict[str, Any]] = []
    stop_reason = ""

    def execute(candidate: axsearch13.Candidate) -> dict[str, Any] | None:
        started = time.monotonic()
        try:
            result, case = run_trial(
                context=context,
                trial_index=candidate.trial_index,
                parameters=candidate.parameters,
                iteration=candidate.iteration,
                state_dir=experiment.state_dir,
            )
        except DemoError as exc:
            experiment.fail(candidate.trial_index, str(exc))
            record = metrics13.build_record(
                parameters=candidate.parameters,
                cfg=cfg,
                observables={},
                validation={},
                status="failed",
                failure_reason=str(exc),
            )
            return _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="failed",
                reported_to_ax_as="failed",
                provenance={"extraction_version": EXTRACTION_VERSION},
            )
        runtime = time.monotonic() - started
        tracking_record, states = _tracking_for(
            result, candidate.trial_index, candidate.parameters, cfg, history
        )
        if states is not None:
            history.append(states)
        record = metrics13.build_record(
            parameters=candidate.parameters,
            cfg=cfg,
            observables=result.observables,
            validation=result.validation,
            status=result.status,
            failure_reason=result.failure_reason,
            extracted_dir=result.run_dir / "extracted",
            tracking=tracking_record,
            runtime_seconds=runtime,
        )
        record = {**record, **_geometry_fields(case),
                  "design_hash": candidate.design_hash,
                  **{key: value for key, value in (candidate.preflight or {}).items()
                     if key in {"maximum_feasible_grading_nm",
                                "realized_grading_thickness_nm",
                                "proposed_grading_fraction"}},
                  "solver_launched": True}
        provenance = _provenance(
            cfg=cfg,
            context=context,
            ax_versions=experiment.versions,
            case=case,
            result=result,
            generation=candidate.generation,
        )
        if result.status == "failed":
            experiment.fail(candidate.trial_index, result.failure_reason or "solver failure")
            return _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="failed",
                reported_to_ax_as="failed",
                provenance=provenance,
            )
        if result.status != "completed":
            # No licensed solver on this machine. The input exists and the trial
            # stays pending in Ax; it is neither completed nor failed, because
            # neither would be true.
            return _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="pending_no_solver",
                reported_to_ax_as="left running",
                provenance=provenance,
            )
        raw = metrics13.ax_raw_data(record, experiment.spec.reported_metrics)
        if raw is None:
            reason = (
                "completed but produced no defensible objective: "
                + (
                    record.get("state_tracking_error")
                    or record.get("rejection_reason")
                    or "missing metric"
                )
            )
            experiment.fail(candidate.trial_index, reason)
            return _record_trial(
                experiment,
                candidate=candidate,
                record={**record, "failure_reason": reason},
                status="failed",
                reported_to_ax_as="failed",
                provenance=provenance,
            )
        experiment.complete(candidate.trial_index, raw)
        return _record_trial(
            experiment,
            candidate=candidate,
            record=record,
            status="completed",
            reported_to_ax_as="completed",
            provenance=provenance,
            extra={"ax_raw_data": raw},
        )

    # 1. Unfinished trials from an earlier run come first.
    for pending in experiment.ledger.records():
        if str(pending.get("status")) in axsearch13.TERMINAL_STATUSES:
            continue
        if not run_solver_trials or not context.machine.run_solver:
            continue
        candidate = axsearch13.Candidate(
            trial_index=int(pending["trial_index"]),
            parameters=dict(pending["parameters"]),
            canonical=dict(pending.get("canonical_parameters") or {}),
            iteration=int(pending.get("iteration", 0)),
            generation=axsearch13.generation_metadata(
                experiment.client, int(pending["trial_index"])
            ),
        )
        payload = execute(candidate)
        if payload is not None:
            experiment.ledger.write(payload, allow_update=True)
            events.append({"stage": "resumed_pending", "trial_index": candidate.trial_index})

    if not generate:
        return {"events": events, "stop_reason": "generation disabled for this mode",
                "rejections": rejection_log}

    # 2. Then generate and evaluate until the configured budget is spent.
    while True:
        plan = experiment.plan
        if plan["pending_trials"] > 0:
            # Candidates whose inputs exist but which have never been executed.
            # Generating more would pile up unrunnable work every time the demo
            # is run on a machine without a licence, and would ask Ax for a
            # proposal it has no new data to inform.
            stop_reason = (
                f"{plan['pending_trials']} candidate(s) already await execution "
                f"({plan['pending_trial_indices']}); run them before generating more"
            )
            break
        if plan["remaining_initial_trials"] > 0:
            wanted = min(batch, plan["remaining_initial_trials"])
        elif plan["remaining_bo_iterations"] > 0:
            wanted = batch
        else:
            stop_reason = "configured initial trials and BO iterations are complete"
            break
        try:
            accepted, rejected = _accepted_candidates(
                experiment, cfg, wanted, rejection_log
            )
        except DemoError as exc:
            stop_reason = str(exc)
            break
        events.extend(rejected)
        if not accepted:
            stop_reason = (
                "no valid unique candidate within "
                f"{int(cfg['bo'].get('max_candidate_regeneration_attempts', 20))} "
                "regeneration attempts; the search space may be mostly infeasible"
                if rejected
                else "Ax generated no further candidates"
            )
            break
        for candidate in accepted:
            payload = execute(candidate)
            events.append(
                {
                    "stage": "evaluated",
                    "trial_index": candidate.trial_index,
                    "iteration": candidate.iteration,
                    "status": None if payload is None else payload.get("status"),
                }
            )
            if payload is not None and payload.get("status") == "pending_no_solver":
                stop_reason = (
                    "no licensed nextnano++ solver on this machine; the candidate "
                    "input was generated and the trial is left pending"
                )
                return {"events": events, "stop_reason": stop_reason,
                        "rejections": rejection_log}
    return {"events": events, "stop_reason": stop_reason, "rejections": rejection_log}


# ---------------------------------------------------------------------------
# synthetic and replay modes
# ---------------------------------------------------------------------------


def synthetic_loop(cfg: Mapping[str, Any], state_dir: Path) -> dict[str, Any]:
    """Stage 1: the same loop, with the synthetic surface standing in for nextnano."""

    experiment = Experiment(cfg, state_dir)
    counts = design13.expected_evaluation_counts(cfg)
    batch = counts["batch_size"]
    events: list[dict[str, Any]] = []
    while True:
        plan = experiment.plan
        if plan["remaining_initial_trials"] > 0:
            wanted = min(batch, plan["remaining_initial_trials"])
        elif plan["remaining_bo_iterations"] > 0:
            wanted = batch
        else:
            break
        try:
            candidates = experiment.generate(wanted)
        except DemoError:
            break
        if not candidates:
            break
        for candidate in candidates:
            if candidate.duplicate_of is not None:
                experiment.abandon(candidate.trial_index, "canonical duplicate")
                _record_trial(
                    experiment,
                    candidate=candidate,
                    record={
                        "trial_valid": False,
                        "rejection_reason": f"canonical duplicate of trial {candidate.duplicate_of}",
                        "synthetic": True,
                        "data_label": synthetic13.SYNTHETIC_LABEL,
                    },
                    status="rejected",
                    reported_to_ax_as="abandoned",
                    provenance={"extraction_version": EXTRACTION_VERSION},
                )
                continue
            try:
                record = synthetic13.evaluate(candidate.parameters, cfg)
            except (synthetic13.SyntheticFailure, DemoError) as exc:
                experiment.fail(candidate.trial_index, str(exc))
                _record_trial(
                    experiment,
                    candidate=candidate,
                    record={
                        "failure_reason": str(exc),
                        "trial_valid": False,
                        "trial_outcome_class": metrics13.OUTCOME_MECHANICAL_FAILURE,
                        "objective_available": False,
                        "synthetic": True,
                        "data_label": synthetic13.SYNTHETIC_LABEL,
                    },
                    status="failed",
                    reported_to_ax_as="failed",
                    provenance={"extraction_version": EXTRACTION_VERSION},
                )
                events.append({"stage": "synthetic_failed", "trial_index": candidate.trial_index})
                continue
            raw = metrics13.ax_raw_data(record, experiment.spec.reported_metrics)
            if raw is None:
                experiment.fail(candidate.trial_index, "synthetic record has no objective")
                continue
            experiment.complete(candidate.trial_index, raw)
            _record_trial(
                experiment,
                candidate=candidate,
                record=record,
                status="completed",
                reported_to_ax_as="completed",
                provenance={"extraction_version": EXTRACTION_VERSION},
                extra={"ax_raw_data": raw},
            )
            events.append({"stage": "synthetic_completed", "trial_index": candidate.trial_index})
    records = experiment.ledger.records()
    best = _best_valid(records, experiment.spec)
    recovery = (
        synthetic13.recovery_error(
            {
                key[len("parameter_"):]: value
                for key, value in best.items()
                if str(key).startswith("parameter_")
            },
            cfg,
        )
        if best
        else {}
    )
    return {
        "experiment": experiment,
        "records": records,
        "events": events,
        "best": best,
        "recovery": recovery,
        "known_optimum": dict(synthetic13.SYNTHETIC_OPTIMUM),
    }


def _best_valid(records: Sequence[Mapping[str, Any]], spec: Any) -> dict[str, Any]:
    metric = tables13.objective_metric_name(spec)
    minimize = metric in set(spec.minimized_metrics)
    usable = [
        record
        for record in records
        if str(record.get("status")) == "completed"
        and record.get("trial_valid")
        and record.get(metric) is not None
    ]
    if not usable:
        return {}
    return dict(
        (min if minimize else max)(usable, key=lambda record: float(record[metric]))
    )


def replay_study(cfg: Mapping[str, Any], results_root: Path | None) -> dict[str, Any]:
    """Stage 2: Ax against random and grid search over completed Demo 12 data."""

    run_dir = replay13.find_demo12_run(cfg, results_root)
    cases = replay13.load_demo12_cases(run_dir) if run_dir else []
    ingested = replay13.ingest(cases, cfg)
    pool = replay13.pool_from_ingest(ingested, cfg)
    source = "demo12"
    if not pool:
        pool = replay13.synthetic_pool(cfg)
        source = "synthetic_stand_in"
    counts = design13.expected_evaluation_counts(cfg)
    comparison = replay13.efficiency_comparison(
        pool,
        cfg,
        evaluations=min(len(pool), counts["expected_maximum_new_solver_runs"]),
        seed=int(cfg["bo"].get("random_seed", 0)),
    )
    return {
        "demo12_run_dir": str(run_dir) if run_dir else None,
        "pool_source": source,
        "pool_size": len(pool),
        "ingested": ingested,
        "comparison": comparison,
    }


# ---------------------------------------------------------------------------
# surrogate slices, partial dependence, acquisition surface
# ---------------------------------------------------------------------------


def _slice_base_point(
    cfg: Mapping[str, Any], fixed: Mapping[str, Any]
) -> dict[str, Any]:
    """The held-fixed design a surrogate slice varies two coordinates of.

    Carries whichever grading variable the search space declares: under the
    fraction parameterization there is no `grading_thickness_nm` to hold fixed,
    and asking for one raises.
    """

    point: dict[str, Any] = {
        "asymmetry_s": float(fixed.get("asymmetry_s", 0.46)),
        "central_barrier_thickness_nm": float(
            fixed.get("central_barrier_thickness_nm", 1.8)
        ),
        "grading_profile": str(fixed.get("grading_profile", "linear")),
    }
    grading = design13.grading_parameter_name(cfg)
    if grading == "grading_thickness_nm":
        point[grading] = float(fixed.get("grading_thickness_nm", 1.5))
    else:
        lower, upper = design13.graded_fraction_bounds(cfg)
        # A fixed value carried over from the thickness parameterization is a
        # nanometre count, not a fraction, and 1.5 is not even in [0, 1]. Only
        # a value stored under the *fraction's own name* may be honoured.
        point[grading] = float(
            fixed.get(grading, min(max(0.5, lower), upper))
        )
    return point


def _ax_encoded_slice_points(
    cfg: Mapping[str, Any], points: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Encode canonical slice points for the hierarchical Ax search space.

    Two failures this prevents, both of which silently emptied a figure:

    * an abrupt point carrying the inactive grading children -- Ax rejects the
      whole parameterization, not just the extra keys;
    * a graded point missing one of them -- same outcome.

    :func:`axsearch13.ax_parameters` already does the encoding; this exists so
    every surrogate consumer goes through one place and the tests have one
    thing to target.
    """

    return [axsearch13.ax_parameters(dict(point), cfg) for point in points]


def _encode_search_point(
    cfg: Mapping[str, Any], point: Mapping[str, Any]
) -> dict[str, Any]:
    """Express a point that is *already in Ax coordinates* for the Ax space.

    :func:`axsearch13.ax_parameters` converts a **canonical** design -- one
    carrying a realized ``grading_thickness_nm`` -- into Ax's encoding.  A
    surrogate slice point is not that: under the fraction parameterization it
    carries ``grading_fraction_of_feasible_max`` and no thickness at all, so
    ``ax_parameters`` read a thickness of zero and encoded *every* slice point
    onto the abrupt branch.  The grading axis of every surrogate figure was
    therefore constant, which is a quieter failure than an empty plot.

    Here the grading coordinate is taken at face value, and only the
    hierarchical branch structure is imposed.
    """

    grading = design13.grading_parameter_name(cfg)
    values: dict[str, Any] = {
        "asymmetry_s": float(point["asymmetry_s"]),
        "central_barrier_thickness_nm": float(point["central_barrier_thickness_nm"]),
    }
    for name in design13.enabled_optional_parameters(cfg):
        if name in point:
            values[name] = point[name]
    if str(cfg["bo"]["search_space"].get("encoding", "hierarchical")) != "hierarchical":
        values[grading] = float(point[grading])
        values["grading_profile"] = str(point.get("grading_profile", "abrupt"))
        return values

    profile = str(point.get("grading_profile", "abrupt"))
    if str(point.get("interface_mode", "graded")) == "abrupt" or profile == "abrupt":
        values["interface_mode"] = "abrupt"
        return values
    values["interface_mode"] = "graded"
    values[grading] = float(point[grading])
    profiles = design13.graded_profiles(cfg)
    values["grading_profile"] = profile if profile in profiles else profiles[0]
    return values


def _slice_points(
    cfg: Mapping[str, Any], x_name: str, y_name: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """A 2-D grid of search-space points and their Ax-encoded counterparts."""

    slices = (cfg["bo"].get("surrogate_slices") or {})
    count = int(slices.get("grid_points", 21))
    fixed = dict(slices.get("fixed_values") or {})
    bounds = {}
    for spec in design13.search_space_specs(cfg):
        if isinstance(spec, design13.RangeSpec):
            bounds[spec.name] = (spec.lower, spec.upper)
    for name in (x_name, y_name):
        if name not in bounds:
            raise DemoError(
                f"surrogate slice asked for {name!r}, which is not a range parameter "
                f"of this search space (it has {sorted(bounds)}). This usually means "
                "the plot still assumes the thickness parameterization."
            )
    search_points: list[dict[str, Any]] = []
    for x in np.linspace(*bounds[x_name], count):
        for y in np.linspace(*bounds[y_name], count):
            point = _slice_base_point(cfg, fixed)
            point[x_name] = float(x)
            point[y_name] = float(y)
            search_points.append(point)
    encoded = [_encode_search_point(cfg, point) for point in search_points]
    return search_points, encoded


def _grading_columns(record: Mapping[str, Any]) -> dict[str, Any]:
    """Semantic grading columns for one ledger record, or a stated absence.

    Delegates to :func:`tables13._grading_columns` so a plot's CSV and the
    ranked-design table cannot end up describing the same trial with different
    column names. Never invents a zero: a record too old or too sparse to say
    what was built gets a reason instead of a number.
    """

    return tables13._grading_columns(record)


def _branch_validity(
    cfg: Mapping[str, Any], point: Mapping[str, Any]
) -> dict[str, Any]:
    """Whether a slice point is a physically valid member of its own branch.

    A graded grid point whose realized width falls below the mesh-resolvable
    minimum is not a graded design at all.  The v3 bundle nevertheless kept
    hundreds of such points marked ``prediction_available`` with a graded
    coordinate attached, so a surrogate surface showed a continuum of "graded"
    predictions where the physical structure was the *same abrupt design*
    repeated -- once per profile label, four times over.

    Such a point is reported here as unavailable **for the branch it claims**,
    with the reason, rather than silently canonicalized and plotted.
    """

    minimum = design13.minimum_resolvable_grading_nm(cfg)
    requested = str(point.get("interface_mode", "graded"))
    if requested == "abrupt" or str(point.get("grading_profile", "")) == "abrupt":
        return {
            "requested_branch": "abrupt",
            "branch_valid": True,
            "branch_invalid_reason": "",
        }
    try:
        view = grading13.from_parameters(dict(point), cfg)
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "requested_branch": "graded",
            "branch_valid": False,
            "branch_invalid_reason": f"{type(exc).__name__}: {exc}",
        }
    if view.realized_grading_thickness_nm < minimum:
        maximum = view.maximum_feasible_grading_nm
        return {
            "requested_branch": "graded",
            "branch_valid": False,
            "branch_invalid_reason": (
                f"a graded point here realizes {view.realized_grading_thickness_nm:.4g} nm, "
                f"below the {minimum:.4g} nm minimum this mesh can resolve"
                + (
                    f"; the largest grade this geometry allows is {maximum:.4g} nm"
                    if maximum is not None
                    else ""
                )
                + ". The physical structure is abrupt, so it is not plotted as a "
                "graded prediction."
            ),
        }
    return {
        "requested_branch": "graded",
        "branch_valid": True,
        "branch_invalid_reason": "",
    }


def _realized_grading_columns(
    cfg: Mapping[str, Any], point: Mapping[str, Any]
) -> dict[str, Any]:
    """Physical grading quantities for one search-space point.

    A slice grid is drawn in Ax coordinates, but a reader wants to know what
    structure each cell corresponds to.  Resolving that here means a figure can
    label its axis with the coordinate it actually varied while the CSV still
    carries the nanometres.
    """

    try:
        view = grading13.from_parameters(dict(point), cfg)
    except Exception as exc:  # pragma: no cover - defensive
        return {"realized_grading_unavailable_reason": f"{type(exc).__name__}: {exc}"}
    return {
        key: value
        for key, value in view.as_record().items()
        if key != "source"
    }


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(float(z) / math.sqrt(2.0)))


def _feasibility_probabilities(
    experiment: "Experiment", row: Mapping[str, Any]
) -> dict[str, Any]:
    """Per-constraint and joint probability that a point satisfies the constraints.

    Each modelled outcome constraint gets a Gaussian tail probability from the
    surrogate's own posterior for that metric.  The direction matters and is
    taken from the constraint, not assumed: an upper bound needs
    ``P(y <= bound)`` and a lower bound needs ``P(y >= bound)``.  Getting that
    backwards would make the most infeasible region look the most promising.

    The joint probability multiplies them, which assumes the constraint
    outcomes are independent given the design.  Ax's own acquisition does not
    assume that, so this is a *proxy* and is labelled as one.
    """

    per_constraint: dict[str, Any] = {}
    joint = 1.0
    modelled = 0
    for spec in feasibility13.build_constraints(experiment.cfg):
        # Only constraints Ax actually models have a posterior. The binary 0/1
        # validity flags are enforced as trial status and post-processing QC and
        # are deliberately never given to the surrogate.
        if spec.enforcement != "ax_outcome_constraint" or spec.is_binary_flag:
            continue
        mean = row.get(f"{spec.metric}_predicted_mean")
        sem = row.get(f"{spec.metric}_predicted_standard_error")
        if mean is None or sem is None:
            continue
        sigma = max(float(sem), 1e-12)
        z = (float(spec.threshold) - float(mean)) / sigma
        # "<=" is an upper bound and needs P(y <= threshold); ">=" is a lower
        # bound and needs P(y >= threshold). Reversing these would make the
        # most infeasible region look the most promising.
        probability = _normal_cdf(z) if spec.operator == "<=" else 1.0 - _normal_cdf(z)
        per_constraint[f"probability_satisfies_{spec.metric}"] = float(probability)
        joint *= float(probability)
        modelled += 1
    if not modelled:
        return {
            "probability_of_feasibility": None,
            "feasibility_probability_note": (
                "no modelled constraint had a posterior at this point"
            ),
        }
    return {
        **per_constraint,
        "probability_of_feasibility": float(joint),
        "feasibility_probability_note": (
            f"product of {modelled} independent Gaussian tail probabilities from the "
            "reconstructed posterior; independence is an approximation and this is "
            "not Ax's own feasibility weighting"
        ),
    }


def _expected_improvement(mean: float, sem: float, best: float) -> float:
    """Analytic expected improvement, for the acquisition-surface figure."""

    if sem is None or not math.isfinite(sem) or sem <= 0:
        return max(0.0, float(mean) - float(best))
    z = (float(mean) - float(best)) / float(sem)
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    pdf = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    return float((float(mean) - float(best)) * cdf + float(sem) * pdf)


def surrogate_artifacts(
    experiment: Experiment,
    records: Sequence[Mapping[str, Any]],
    model: analysis13.ReconstructedModel | None = None,
) -> dict[str, Any]:
    """Surrogate slices, partial dependence, acquisition surface and importance.

    ``model`` is the refitted analysis surrogate.  It is passed in rather than
    taken from ``experiment.client`` because a deserialized client has no
    fitted adapter at all: that is exactly the defect that emptied every
    surrogate figure of the completed licensed study.  When it is absent or
    could not be fitted, every row still appears, carrying the real reason.
    """

    cfg = experiment.cfg
    if model is None:
        model = analysis13.ReconstructedModel(
            None,
            None,
            None,
            {
                "fit_status": "not_attempted",
                "fit_status_reason": (
                    "no analysis surrogate was reconstructed for this run"
                ),
            },
        )
    metric = tables13.objective_metric_name(experiment.spec)
    best_record = _best_valid(records, experiment.spec)
    best_value = float(best_record.get(metric, 0.0) or 0.0)
    fixed = dict((cfg["bo"].get("surrogate_slices") or {}).get("fixed_values") or {})
    slices: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for name, (x_name, y_name) in (
        ("asymmetry_grading", ("asymmetry_s", design13.grading_parameter_name(cfg))),
        ("barrier_grading", ("central_barrier_thickness_nm",
                             design13.grading_parameter_name(cfg))),
    ):
        search_points, encoded = _slice_points(cfg, x_name, y_name)
        predictions = model.predict(encoded)
        slice_rows: list[dict[str, Any]] = []
        for point, prediction in zip(search_points, predictions):
            validity = _branch_validity(cfg, point)
            available = bool(prediction.get("prediction_available", False))
            reason = str(prediction.get("reason", ""))
            if not validity["branch_valid"]:
                # The model can predict here, but the point is not a member of
                # the branch it claims: its physical structure is abrupt. It is
                # withheld from the graded surface rather than drawn as one of
                # hundreds of identical "graded" predictions.
                available = False
                reason = validity["branch_invalid_reason"]
            row = {
                "slice": name,
                **{key: value for key, value in point.items()},
                # The physical structure each Ax coordinate corresponds to, so a
                # reader is never left to guess whether the grading column is a
                # fraction or a length.
                **_realized_grading_columns(cfg, point),
                **validity,
                **{
                    f"fixed_{key}": value
                    for key, value in fixed.items()
                    if key not in (x_name, y_name)
                },
                "prediction_available": available,
                "reason": reason,
            }
            if available:
                for key, value in prediction.items():
                    if str(key).endswith(
                        ("_predicted_mean", "_predicted_standard_error")
                    ):
                        row[key] = value
            mean = row.get(f"{metric}_predicted_mean")
            sem = row.get(f"{metric}_predicted_standard_error")
            row["expected_improvement"] = (
                None if mean is None else _expected_improvement(float(mean), sem, best_value)
            )
            # Feasibility is the whole story on this campaign: three of sixteen
            # completed trials satisfied the constraints, and the five genuine
            # graded designs failed on detuning alone. An acquisition surface
            # that ignores the constraints therefore points at designs the
            # study already knows are infeasible.
            row.update(_feasibility_probabilities(experiment, row))
            joint = row.get("probability_of_feasibility")
            row["constrained_expected_improvement_proxy"] = (
                None
                if row["expected_improvement"] is None or joint is None
                else float(row["expected_improvement"]) * float(joint)
            )
            row["expected_improvement_method"] = (
                "analytic expected improvement from the reconstructed posterior; "
                "NOT the original constrained Ax acquisition. Ax generated with a "
                "Monte-Carlo, constraint-weighted, noisy-observation acquisition "
                "(qLogNoisyEI); this is a different function of the same posterior, "
                "and the exact acquisition cannot be replayed from a snapshot. The "
                "constrained proxy multiplies it by the modelled joint probability "
                "of feasibility."
            )
            slice_rows.append(row)
        slices[name] = slice_rows
        rows.extend(slice_rows)

    partial: dict[str, list[dict[str, Any]]] = {}
    for spec in design13.search_space_specs(cfg):
        if not isinstance(spec, design13.RangeSpec):
            continue
        count = int((cfg["bo"].get("surrogate_slices") or {}).get("grid_points", 21))
        points: list[dict[str, Any]] = []
        for value in np.linspace(spec.lower, spec.upper, count):
            point = _slice_base_point(cfg, fixed)
            point[spec.name] = float(value)
            points.append(point)
        predictions = model.predict(
            [_encode_search_point(cfg, point) for point in points]
        )
        partial[spec.name] = [
            {
                spec.name: point[spec.name],
                "predicted_mean": prediction.get(f"{metric}_predicted_mean"),
                "predicted_standard_error": prediction.get(
                    f"{metric}_predicted_standard_error"
                ),
                "prediction_available": prediction.get("prediction_available", False),
                "reason": prediction.get("reason", ""),
                **_realized_grading_columns(cfg, point),
                **{f"fixed_{key}": value for key, value in fixed.items() if key != spec.name},
                "holding_note": (
                    "one coordinate varied, the rest held at the configured fixed "
                    "values; this is a slice through the surrogate, not an average "
                    "over the search space, so it never mixes the abrupt and graded "
                    "branches in a single curve"
                ),
            }
            for point, prediction in zip(points, predictions)
        ]

    acquisition_rows = [
        {
            "trial_index": record.get("trial_index"),
            "iteration": record.get("iteration"),
            "generation_method": record.get("generation_method"),
            "expected_acquisition_value": record.get("expected_acquisition_value"),
            "status": record.get("status"),
            **{
                key: record.get(key)
                for key in (
                    "parameter_asymmetry_s", "parameter_central_barrier_thickness_nm",
                    "parameter_grading_thickness_nm", "parameter_grading_profile",
                )
            },
            # Proposed-versus-realized, so an acquisition history can be read
            # without inferring the structure from the parameter columns.
            **_grading_columns(record),
            "note": "Sobol proposals have no acquisition value; the field is empty for them",
        }
        for record in records
    ]
    return {
        "slices": slices,
        "slice_rows": rows,
        "partial_dependence": partial,
        "acquisition_rows": acquisition_rows,
        "importance": model.parameter_importance(),
        "model_reconstruction": dict(model.record),
        "grading_evidence": grading13.evidence_counts(records),
        "ax_frontier": axsearch13.pareto_frontier(experiment.client)
        if experiment.spec.is_multi_objective
        else [],
    }


# ---------------------------------------------------------------------------
# curves for the physics figures
# ---------------------------------------------------------------------------


def _normalized_spectrum(extracted: Path) -> tuple[list[float], list[float]] | None:
    spectrum = metrics13.read_chi2_spectrum(extracted)
    if spectrum is None:
        return None
    wavelength, magnitude = spectrum
    peak = float(np.max(np.abs(magnitude))) if magnitude.size else 0.0
    if peak <= 0:
        return list(map(float, wavelength)), [0.0] * len(wavelength)
    return list(map(float, wavelength)), list(map(float, np.abs(magnitude) / peak))


def _read_two_column_csv(path: Path) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    if not path.is_file():
        return xs, ys
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                xs.append(float(row[0]))
                ys.append(float(row[1]))
            except ValueError:
                continue
    return xs, ys


def physics_curves(
    cfg: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    state_dir: Path,
    *,
    top: int = 3,
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Spectra, composition, band edges and envelopes for the best designs.

    ``baseline`` is the Demo 11 abrupt reference, looked up from that demo's own
    results.  It has to be passed in: Demo 13's ledger contains only Demo 13
    trials, so the previous search for a record with ``design_role ==
    "reference"`` inside ``records`` found nothing on a normal run, and every
    figure named ``baseline_and_best_*`` was drawn with no baseline in it.
    """

    spectra: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    band_edges: list[dict[str, Any]] = []
    envelopes: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []

    ranked = sorted(
        (
            record
            for record in records
            if str(record.get("status")) == "completed"
            and record.get("trial_valid")
            and record.get("relative_chi2_at_target_wavelength_abs") is not None
            and math.isfinite(float(record["relative_chi2_at_target_wavelength_abs"]))
        ),
        # Same deterministic tie-break as the ranked table, so the figures and
        # the tables can never disagree about which trial is best.
        key=lambda record: (
            -float(record["relative_chi2_at_target_wavelength_abs"]),
            int(record.get("trial_index", 0)),
        ),
    )
    selected: list[tuple[str, str, Mapping[str, Any]]] = []
    reference = next(
        (record for record in records if record.get("design_role") == "reference"), None
    )
    if reference is None and baseline is not None:
        reference = baseline
    if reference is not None:
        source = str(reference.get("source_demo") or "this experiment")
        selected.append((f"reference (abrupt, {source})", "baseline", reference))
    else:
        provenance.append(
            {
                "role": "baseline",
                "included": False,
                "reason": (
                    "no Demo 11 abrupt reference result was found under the results "
                    "root, and Demo 13's own ledger holds no record marked as the "
                    "reference design"
                ),
            }
        )
    for position, record in enumerate(ranked[:top]):
        role = "best" if position == 0 else "top"
        selected.append((f"trial {record.get('trial_index')}", role, record))

    for label, role, record in selected:
        directory = record.get("output_directory_path")
        if not directory:
            provenance.append(
                {
                    "role": role,
                    "label": label,
                    "trial_index": record.get("trial_index"),
                    "included": False,
                    "reason": "this record carries no output directory, so its raw "
                    "solver output cannot be located",
                }
            )
            continue
        provenance.append(
            {
                "role": role,
                "label": label,
                "trial_index": record.get("trial_index"),
                "included": True,
                "output_directory_path": str(directory),
            }
        )
        extracted = Path(str(directory)) / "extracted"
        spectrum = _normalized_spectrum(extracted)
        if spectrum is not None:
            spectra.append({"label": label, "role": role, "x": spectrum[0], "y": spectrum[1]})
        xs, ys = _read_two_column_csv(extracted / "requested_composition_profile.csv")
        if xs:
            profiles.append({"label": label, "x": xs, "y": ys})
        envelopes.extend(_envelope_curves(extracted, label))
        band_edges.extend(
            _band_edge_curves(cfg, run_subdirectory(Path(str(directory)), "raw"), label)
        )
    return {
        "spectra": spectra,
        "profiles": profiles,
        "band_edges": band_edges,
        "envelopes": envelopes,
        # Which rows a `baseline_and_best_*` figure actually contains, and the
        # stated reason for each one that is missing. Silence here was how a
        # file named for the baseline came to be drawn without it.
        "curve_provenance": provenance,
    }


def _envelope_curves(extracted: Path, label: str) -> list[dict[str, Any]]:
    path = extracted / "envelopes.csv"
    if not path.is_file():
        return []
    try:
        header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
        data = np.genfromtxt(path, delimiter=",", skip_header=1)
    except (OSError, IndexError, ValueError):
        return []
    if data.ndim != 2 or data.shape[0] < 2:
        return []
    curves: list[dict[str, Any]] = []
    for index, name in enumerate(header):
        name = name.strip()
        if not name.startswith("psi_"):
            continue
        band = "heavy_hole" if name.startswith("psi_hh") else "electron"
        curves.append(
            {
                "label": f"{label}: {name}",
                "band": band,
                "x": list(map(float, data[:, 0])),
                "y": list(map(float, data[:, index])),
            }
        )
    return curves


def _band_edge_curves(cfg: Mapping[str, Any], raw: Path, label: str) -> list[dict[str, Any]]:
    """Solver band edges, parsed exactly as Demo 11 parses them."""

    if not raw.is_dir():
        return []
    try:
        profile = outputs.load_profile(
            str(cfg["outputs"].get("parser_profile", outputs.DEFAULT_PROFILE))
        )
        run = quantum1d.parse_one_band_run(
            raw,
            profile=profile,
            region_name=str(cfg["analysis"].get("quantum_region_name", "acqw")),
            bandedge_columns=cfg["outputs"]["bandedge_columns"],
            want_envelopes=False,
        )
    except Exception:
        return []
    curves: list[dict[str, Any]] = []
    for key, band in (("conduction_eV", "conduction"), ("heavy_hole_eV", "heavy_hole")):
        values = run.band_edges.get(key)
        if values is None:
            continue
        curves.append(
            {
                "label": label,
                "band": band,
                "x": list(map(float, run.position_nm)),
                "y": list(map(float, values)),
            }
        )
    return curves


def paper_curves(cfg: Mapping[str, Any], spectra: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    paper = cfg.get("paper_comparison") or {}
    curves = [
        {"label": curve["label"], "x": curve["x"], "y": curve["y"]}
        for curve in spectra
        if curve.get("role") in {"baseline", "best"}
    ]
    name = paper.get("digitized_simulation_csv")
    if name:
        xs, ys = _read_two_column_csv(DEMO_DIR / str(name))
        if xs:
            peak = max(ys) or 1.0
            curves.append(
                {
                    "label": "paper Fig. 2d (digitized)",
                    "x": xs,
                    "y": [value / peak for value in ys],
                }
            )
    return curves


def measured_curves(cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    name = (cfg.get("paper_comparison") or {}).get("measured_intensity_csv")
    if not name:
        return []
    xs, ys = _read_two_column_csv(DEMO_DIR / str(name))
    return [{"label": "measured SH intensity", "x": xs, "y": ys}] if xs else []


# ---------------------------------------------------------------------------
# Stage 5 validation
# ---------------------------------------------------------------------------


def _set(config: dict[str, Any], dotted: str, value: Any) -> None:
    cursor: Any = config
    parts = dotted.split(".")
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value


def validation_cases(
    cfg: Mapping[str, Any], design: Mapping[str, Any]
) -> list[tuple[str, str, dict[str, Any]]]:
    """Local refinement, mesh, state-count and padding checks for one design."""

    study = cfg.get("validation_study") or {}
    base_parameters = {
        key[len("parameter_"):]: value
        for key, value in design.items()
        if str(key).startswith("parameter_")
    }
    cases: list[tuple[str, str, dict[str, Any]]] = []
    cases.append(("nominal", "nominal", design13.resolve_config(base_parameters, cfg)))
    for name, deltas in (study.get("local_refinement") or {}).items():
        for delta in deltas:
            parameters = dict(base_parameters)
            try:
                parameters[name] = float(parameters[name]) + float(delta)
                resolved = design13.resolve_config(parameters, cfg)
            except (KeyError, DemoError):
                continue
            cases.append((f"local_{name}{float(delta):+g}", "local_refinement", resolved))
    for spacing in study.get("mesh_convergence_nm") or []:
        resolved = design13.resolve_config(base_parameters, cfg)
        _set(resolved, "numerical.active_region_grid_spacing_nm", float(spacing))
        cases.append((f"mesh_{float(spacing):g}nm", "mesh_convergence", resolved))
    for count in study.get("state_count_convergence") or []:
        resolved = design13.resolve_config(base_parameters, cfg)
        _set(resolved, "numerical.number_of_electron_states", int(count))
        _set(resolved, "numerical.number_of_hole_states", int(count))
        cases.append((f"states_{int(count)}", "state_count_convergence", resolved))
    for padding in study.get("domain_padding_nm") or []:
        resolved = design13.resolve_config(base_parameters, cfg)
        _set(resolved, "numerical.domain_padding_nm", float(padding))
        cases.append((f"padding_{float(padding):g}nm", "domain_padding", resolved))
    return cases


def robustness_cases(
    cfg: Mapping[str, Any], design: Mapping[str, Any]
) -> list[tuple[str, str, float, dict[str, Any]]]:
    """Fabrication perturbations around one design."""

    study = (cfg.get("validation_study") or {}).get("fabrication_perturbations") or {}
    base_parameters = {
        key[len("parameter_"):]: value
        for key, value in design.items()
        if str(key).startswith("parameter_")
    }
    paths = {
        "narrow_well_nm": "scientific.thin_well_nm",
        "wide_well_nm": "scientific.thick_well_nm",
        "central_barrier_nm": "scientific.tunnel_barrier_nm",
        "grading_thickness_nm": "grading.selected_thickness_nm",
        "aluminum_fraction": "scientific.aluminum_fraction",
    }
    view = grading13.try_from_record(design)
    realized_grading = view.realized_grading_thickness_nm if view is not None else None
    cases: list[tuple[str, str, float, dict[str, Any]]] = []
    for name, deltas in study.items():
        path = paths.get(str(name))
        if path is None:
            continue
        for delta in deltas:
            resolved = design13.resolve_config(base_parameters, cfg)
            cursor: Any = resolved
            for part in path.split("."):
                cursor = cursor[part]
            nominal = float(cursor)
            new_value = nominal + float(delta)
            if new_value <= 0:
                continue
            # A fabrication tolerance perturbs a dimension. Adding grading to a
            # design that realizes none does not perturb a width -- it changes
            # the interface *mode*, producing a structurally different device
            # and calling the difference "robustness". The winning v2 design is
            # abrupt, so this is not hypothetical.
            if str(name) == "grading_thickness_nm" and not realized_grading:
                continue
            _set(resolved, path, new_value)
            cases.append((f"{name}{float(delta):+g}", str(name), float(delta), resolved))
    return cases


def perturbation_fraction(
    cfg: Mapping[str, Any], design: Mapping[str, Any], parameter: str, delta: float
) -> float | None:
    """A perturbation's size *relative to the dimension it perturbs*.

    A +/-0.2 nm tolerance is 3 % of a 7 nm well and 40 % of a 0.5 nm barrier.
    Averaging those into one robustness score hides the only sensitivity that
    matters for a design sitting at the lower barrier bound.
    """

    paths = {
        "narrow_well_nm": "scientific.thin_well_nm",
        "wide_well_nm": "scientific.thick_well_nm",
        "central_barrier_nm": "scientific.tunnel_barrier_nm",
        "grading_thickness_nm": "grading.selected_thickness_nm",
        "aluminum_fraction": "scientific.aluminum_fraction",
    }
    path = paths.get(str(parameter))
    if path is None:
        return None
    base_parameters = {
        key[len("parameter_"):]: value
        for key, value in design.items()
        if str(key).startswith("parameter_")
    }
    try:
        cursor: Any = design13.resolve_config(base_parameters, cfg)
        for part in path.split("."):
            cursor = cursor[part]
        nominal = float(cursor)
    except (KeyError, TypeError, ValueError):
        return None
    return abs(float(delta)) / abs(nominal) if nominal else None


def stage5_gate_plan(
    cfg: Mapping[str, Any], records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """What the two-case gate *would* run. Pure: no solver, no writes.

    This is the function ``--check`` and the dry-run tests call, so what a
    reviewer inspects before authorizing paid time is built by the same code
    that will spend it.
    """

    resolved = validation13.settings(cfg)
    gate = resolved.gate
    design = validation13.gate_design_record(cfg, records)
    cases = validation13.gate_cases(cfg, design)
    return {
        **gate.as_record(),
        "design_candidate_id": str(design.get("candidate_id")),
        "design_trial_index": design.get("trial_index"),
        "design_parameters": {
            key[len("parameter_"):]: value
            for key, value in design.items()
            if str(key).startswith("parameter_")
        },
        "reference_mesh_nm": gate.reference_mesh_nm,
        "planned_cases": [
            {
                "case_id": case_id,
                "check_kind": kind,
                "active_region_grid_spacing_nm": float(
                    config["numerical"]["active_region_grid_spacing_nm"]
                ),
                "resolved_wide_well_nm": float(config["scientific"]["thick_well_nm"]),
                "resolved_narrow_well_nm": float(config["scientific"]["thin_well_nm"]),
                "resolved_central_barrier_nm": float(
                    config["scientific"]["tunnel_barrier_nm"]
                ),
                "grading_profile": str(config["grading"]["profile"]),
                "grading_selected_thickness_nm": float(
                    config["grading"]["selected_thickness_nm"]
                ),
            }
            for case_id, kind, config in cases
        ],
        "planned_case_count": len(cases),
        "solver_calls_planned": len(cases),
    }


def _gate_anchor_extracted_dir(
    record: Mapping[str, Any],
    cfg: Mapping[str, Any] | None = None,
    results_root: Path | None = None,
) -> Path | None:
    """The historical anchor trial's extracted directory, read-only.

    The gate anchors on a *completed licensed trial*, not on a freshly computed
    reference: computing one would be a third paid case, and the gate is two by
    definition. That directory lives inside the protected campaign and is only
    ever opened for reading.

    Resolved **relative to this machine first**. ``output_directory_path`` is an
    absolute path recorded on whichever machine ran the campaign -- for v3 it is
    a work-laptop path under ``C:\\Code\\optics\\...`` -- so following it alone
    is a portability trap that fails on any other checkout.
    """

    candidate = str(record.get("candidate_id") or "")
    if cfg is not None and results_root is not None and candidate:
        local = (
            experiment_state_dir(cfg, results_root) / "runs" / candidate / "extracted"
        )
        if local.is_dir():
            return local
    directory = record.get("output_directory_path")
    if not directory:
        return None
    extracted = Path(str(directory)) / "extracted"
    return extracted if extracted.is_dir() else None


def run_stage5_gate(
    context: sweeps.RunContext,
    state_dir: Path,
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """The first paid Stage 5 action: exactly two new-mesh cases, anchored.

    Passing means every gate case assigns to the anchor with acceptable
    confidence and margin, keeps the anchor's state labels, and reproduces the
    reference-mesh physics within the configured tolerances.  A gate that could
    not be evaluated reports ``gate_passed: None`` and says why -- it never
    reports a pass it did not establish.
    """

    cfg = context.cfg
    plan = stage5_gate_plan(cfg, records)
    design = validation13.gate_design_record(cfg, records)
    resolved = validation13.settings(cfg)
    spec = anchor13.resolve_anchor_spec(
        {**cfg, "state_tracking": {
            **(cfg.get("state_tracking") or {}),
            "anchor_case": resolved.gate.anchor_case,
        }}
    )

    gate_rows: list[dict[str, Any]] = []
    for position, (case_id, kind, config) in enumerate(
        validation13.gate_cases(cfg, design), start=1
    ):
        gate_rows.append(
            _run_side_case(
                context,
                state_dir,
                case_id,
                config,
                extra={
                    # Distinct per case. Sharing the design's index collapsed both
                    # cases into one entry of `assign_all_to_anchor`'s fingerprint
                    # dict, so the order-independence guarantee did not hold and
                    # `ambiguous_trials` could not say which mesh was ambiguous.
                    "trial_index": -position,
                    "design_trial_index": design.get("trial_index"),
                    "check_kind": kind,
                    "case_id": case_id,
                    "gate_case": True,
                    "anchor_case": spec.name,
                    "reference_mesh_nm": resolved.gate.reference_mesh_nm,
                    "active_region_grid_spacing_nm": float(
                        config["numerical"]["active_region_grid_spacing_nm"]
                    ),
                    "historical_tracked_state_labels": design.get(
                        "tracked_state_labels"
                    ),
                },
            )
        )

    anchor_extracted = _gate_anchor_extracted_dir(
        design, cfg, context.machine.results_root
    )
    anchor_tracking: dict[str, Any] = {}
    unavailable: str | None = None
    if anchor_extracted is None:
        unavailable = (
            "the anchor trial's extracted output is not present on this machine. "
            "The gate assigns against the completed "
            f"{design.get('candidate_id')} and does not recompute it, so its "
            "solver output must exist at "
            f"{experiment_state_dir(cfg, context.machine.results_root)}"
            f"\\runs\\{design.get('candidate_id')}\\extracted. Run the gate on the "
            "machine that executed the campaign."
        )
    elif not any(str(row.get("status")) == "completed" for row in gate_rows):
        unavailable = "no gate case completed with solver output"
    else:
        anchor_states, bound = anchor13.load_anchor_states(
            spec,
            anchor_extracted,
            plan["design_parameters"],
            cfg,
            observables=design,
        )
        cases: list[tracking13.TrialStates] = []
        for row in gate_rows:
            if str(row.get("status")) != "completed":
                continue
            states = tracking13.load_trial_states(
                int(row.get("trial_index", -1)),
                design13.canonicalize(_parameters_from_validation_row(row), cfg),
                Path(str(row["output_directory_path"])) / "extracted",
                observables=row,
            )
            if states is None:
                # A completed case with no envelopes cannot be anchored. Dropping
                # it silently turned a two-case gate into a one-case gate with no
                # signal, so the whole gate is unavailable instead.
                unavailable = (
                    f"gate case {row.get('case_id')} completed but produced no "
                    "envelopes, so it cannot be assigned against the anchor"
                )
                break
            cases.append(states)
        if unavailable is None:
            anchor_tracking = anchor13.assign_all_to_anchor(
                cases, anchor_states, cfg, spec=bound
            )
            _merge_anchor_results_into_rows(anchor_tracking, gate_rows, design)

    comparison = _gate_comparison(design, gate_rows)
    passed = _gate_verdict(
        anchor_tracking, comparison, unavailable, cfg=cfg, expected_cases=len(gate_rows)
    )
    result = {
        **plan,
        "gate_rows": gate_rows,
        "anchor_tracking": anchor_tracking,
        "anchor_tracking_rows": anchor13.anchor_rows(anchor_tracking)
        if anchor_tracking
        else [],
        "comparison": comparison,
        "gate_passed": passed,
        "gate_unavailable_reason": unavailable,
        "solver_ran": bool(context.machine.run_solver),
    }
    write_json_atomically(state_dir / "stage5_gate_result.json", result)
    write_json_atomically(state_dir / "stage5_schema.json", validation13.stage5_schema(cfg))
    return result


def _merge_anchor_results_into_rows(
    anchor_tracking: Mapping[str, Any],
    gate_rows: Sequence[dict[str, Any]],
    design: Mapping[str, Any],
) -> None:
    """Write the anchored tracking results back onto each gate row.

    ``_run_side_case`` builds its record with ``tracking=None``, so a gate row
    left alone carries ``state_tracking_confidence: None`` and
    ``tracked_state_labels: None``. Three of the eleven compared fields --
    including the gate's headline question, "does the state assignment survive a
    mesh change?" -- were therefore reported as ``0.99`` versus ``None`` while
    the real answer sat unused in ``anchor_tracking``.

    ``labels_match_historical`` is set here for the same reason
    :func:`validation_anchor_tracking` sets it: nothing else does, and
    :func:`_gate_verdict` checks it.
    """

    historical = design.get("tracked_state_labels")
    by_index = {
        int(record.get("trial_index", 0)): record
        for record in anchor_tracking.get("records", ())
    }
    for row in gate_rows:
        record = by_index.get(int(row.get("trial_index", 0)))
        if record is None:
            continue
        record["historical_tracked_state_labels"] = historical
        record["labels_match_historical"] = (
            None if historical is None else historical == record.get("tracked_labels")
        )
        row["state_tracking_confidence"] = record.get("state_tracking_confidence")
        row["state_tracking_margin"] = record.get("assignment_margin")
        row["tracked_state_labels"] = record.get("tracked_labels")
        row["state_tracking_ambiguous"] = bool(
            record.get("ambiguous") or record.get("ambiguous_under_threshold")
        )
        row["state_tracking_method"] = record.get("method")
        row["labels_match_historical"] = record.get("labels_match_historical")


def _gate_comparison(
    reference: Mapping[str, Any], gate_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Reference-mesh value beside each new-mesh value, field by field."""

    rows: list[dict[str, Any]] = []
    for row in gate_rows:
        for field_name in validation13.GATE_COMPARISON_FIELDS:
            reference_value = reference.get(field_name)
            gate_value = row.get(field_name)
            numeric_reference = metrics13._finite(reference_value)
            numeric_gate = metrics13._finite(gate_value)
            relative = None
            if (
                numeric_reference is not None
                and numeric_gate is not None
                and numeric_reference != 0
            ):
                relative = abs(numeric_gate - numeric_reference) / abs(numeric_reference)
            rows.append(
                {
                    "case_id": row.get("case_id"),
                    "active_region_grid_spacing_nm": row.get(
                        "active_region_grid_spacing_nm"
                    ),
                    "field": field_name,
                    "reference_mesh_value": reference_value,
                    "gate_mesh_value": gate_value,
                    "relative_change": relative,
                    "status": row.get("status"),
                }
            )
    return rows


def _gate_verdict(
    anchor_tracking: Mapping[str, Any],
    comparison: Sequence[Mapping[str, Any]],
    unavailable: str | None,
    *,
    cfg: Mapping[str, Any] | None = None,
    expected_cases: int | None = None,
) -> bool | None:
    """``True``/``False``/``None``. ``None`` means "not established", never "fine".

    Tests all three things the gate claims: that every case anchored with
    acceptable confidence and margin, that the anchor's state labels held, and
    that the reference-mesh physics is reproduced within the configured
    tolerances. The earlier version checked none of them -- it passed a 60 %
    shift in chi(2), it passed a reordered label set because
    ``labels_match_historical`` was never populated on this path, and it passed
    a gate that had silently lost one of its two cases.
    """

    if unavailable:
        return None
    records = list(anchor_tracking.get("records", ())) if anchor_tracking else []
    if not records:
        return None
    if expected_cases is not None and len(records) != int(expected_cases):
        return None
    if not comparison or not all(row.get("status") == "completed" for row in comparison):
        return False

    labels_held = all(
        record.get("labels_match_historical") is True for record in records
    )
    unambiguous = not anchor_tracking.get("ambiguous_trials")

    minimum_confidence, minimum_margin = _gate_acceptance_thresholds(cfg)
    tracked_well = all(
        record.get("state_tracking_confidence") is not None
        and float(record["state_tracking_confidence"]) >= minimum_confidence
        and record.get("assignment_margin") is not None
        and float(record["assignment_margin"]) >= minimum_margin
        for record in records
    )

    tolerances = validation13.gate_tolerances(cfg or {})
    within_tolerance = True
    for row in comparison:
        tolerance = tolerances.get(str(row.get("field")))
        if tolerance is None:
            continue
        change = row.get("relative_change")
        if change is None or float(change) > float(tolerance):
            within_tolerance = False
            break

    return bool(labels_held and unambiguous and tracked_well and within_tolerance)


def _gate_acceptance_thresholds(cfg: Mapping[str, Any] | None) -> tuple[float, float]:
    """The same confidence and margin bounds the campaign itself enforces."""

    if not cfg:
        return 0.80, 0.15
    constraint = next(
        (
            spec
            for spec in feasibility13.build_constraints(cfg)
            if spec.metric == "state_tracking_confidence"
        ),
        None,
    )
    minimum_confidence = float(constraint.threshold) if constraint is not None else 0.80
    minimum_margin = float(
        (cfg.get("state_tracking") or {}).get("minimum_assignment_margin", 0.15)
    )
    return minimum_confidence, minimum_margin


def run_validation_study(
    context: sweeps.RunContext, experiment: Experiment, records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Stage 5: refine, converge and perturb the top designs.

    Without a licensed solver this returns the *planned* cases and says so; it
    never reports a check as passed that was not run.
    """

    cfg = context.cfg
    resolved_settings = validation13.settings(cfg)
    if not resolved_settings.enabled:
        return {"enabled": False, "validation_rows": [], "robustness_rows": []}
    validation_rows: list[dict[str, Any]] = []
    robustness_rows: list[dict[str, Any]] = []
    # Stage 5 writes into its OWN directory, never inside the optimization
    # experiment. The experiment holds the immutable ledger of a licensed
    # campaign; validation cases are side calculations and must not be able to
    # reach it, even through a bug. The resolved-path check catches symlinks,
    # aliases, containment, and any directory holding a checkpoint or ledger.
    state_dir = stage5_state_dir(cfg, context.machine.results_root)
    validation13.assert_isolated(
        state_dir,
        cfg,
        context.machine.results_root,
        experiment_dir=experiment.state_dir,
    )
    validation13.assert_resume_schema_matches(state_dir, cfg)
    if state_dir.resolve() == experiment.state_dir.resolve():
        raise DemoError(
            "Stage 5 resolved to the optimization experiment directory "
            f"({state_dir}). Set validation_study.output_state_dir to a separate "
            "directory."
        )

    # The gate comes first and is the whole of the first paid Stage 5 action.
    # The full campaign is roughly forty licensed cases; generating it before
    # knowing whether two meshes even agree is the expensive mistake.
    gate = resolved_settings.gate
    if gate.enabled:
        gate_result = run_stage5_gate(context, state_dir, records)
        validation_rows.extend(gate_result["gate_rows"])
        # STOP. The gate result must be reviewed by a human in a *later*
        # invocation, never consumed by the process that produced it: otherwise
        # a passing gate falls straight through into the ~60-case campaign in
        # the same command, and the handoff's promise that this step "runs two
        # licensed calculations and nothing else" is false.
        write_json_atomically(
            state_dir / "stage5_schema.json", validation13.stage5_schema(cfg)
        )
        return {
            "enabled": True,
            "gate": gate_result,
            "validation_rows": validation_rows,
            "robustness_rows": [],
            "designs_checked": [],
            "full_campaign_generated": False,
            "full_campaign_blocked_reason": (
                "the gate ran in this invocation; the full campaign requires a "
                "separate, separately authorized run after the gate result has "
                "been reviewed"
            ),
            "solver_ran": bool(context.machine.run_solver),
            "anchor_tracking": gate_result.get("anchor_tracking", {}),
            "anchor_tracking_rows": gate_result.get("anchor_tracking_rows", []),
        }
    gate_result = {"gate_enabled": False, "gate_rows": [], "gate_passed": None}
    allowed, reason = validation13.full_campaign_allowed(cfg, state_dir)
    if not allowed:
        write_json_atomically(
            state_dir / "stage5_schema.json", validation13.stage5_schema(cfg)
        )
        return {
            "enabled": True,
            "gate": gate_result,
            "validation_rows": validation_rows,
            "robustness_rows": [],
            "designs_checked": [],
            "full_campaign_generated": False,
            "full_campaign_blocked_reason": reason,
            "solver_ran": bool(context.machine.run_solver),
            "anchor_tracking": gate_result.get("anchor_tracking", {}),
            "anchor_tracking_rows": gate_result.get("anchor_tracking_rows", []),
        }

    top = tables13.top_ranked_valid_designs(
        records, experiment.spec, limit=resolved_settings.top_designs
    )
    anchor_spec = anchor13.resolve_anchor_spec(cfg)
    anchor_row: dict[str, Any] | None = None
    if anchor_spec.source == "reference_design":
        anchor_resolved = design13.resolve_config(anchor_spec.parameters, cfg)
        anchor_row = _run_side_case(
            context,
            state_dir,
            "anchor_reference_abrupt",
            anchor_resolved,
            extra={
                "trial_index": -1,
                "check_kind": "state_tracking_anchor",
                "case_id": "anchor_reference_abrupt",
                "anchor_case": anchor_spec.name,
            },
        )
        validation_rows.append(anchor_row)
    for design in top:
        source = next(
            (
                record
                for record in records
                if int(record.get("trial_index", -1)) == int(design.get("trial_index", -2))
            ),
            None,
        )
        if source is None:
            continue
        nominal_target = metrics13._finite(source.get("relative_chi2_at_target_wavelength_abs"))
        for case_id, kind, resolved in validation_cases(cfg, source):
            row = _run_side_case(
                context,
                state_dir,
                f"v{int(design['trial_index']):04d}_{case_id}",
                resolved,
                extra={
                    "trial_index": design["trial_index"],
                    "check_kind": kind,
                    "case_id": case_id,
                    "nominal_chi2_at_target_wavelength_abs": nominal_target,
                    "historical_tracked_state_labels": source.get("tracked_state_labels"),
                },
            )
            validation_rows.append(row)
        drifts: list[float] = []
        for case_id, parameter, delta, resolved in robustness_cases(cfg, source):
            fraction = perturbation_fraction(cfg, source, parameter, delta)
            row = _run_side_case(
                context,
                state_dir,
                f"r{int(design['trial_index']):04d}_{case_id}",
                resolved,
                extra={
                    "trial_index": design["trial_index"],
                    "perturbed_parameter": parameter,
                    "perturbation": delta,
                    "perturbation_fraction_of_nominal": fraction,
                    "case_id": case_id,
                    "nominal_chi2_at_target_wavelength_abs": nominal_target,
                },
            )
            value = metrics13._finite(row.get("relative_chi2_at_target_wavelength_abs"))
            if value is not None and nominal_target:
                drift = abs(value - nominal_target) / abs(nominal_target)
                row["relative_drift"] = drift
                # Sensitivity per unit *fractional* change, so a 40 % barrier
                # perturbation and a 3 % well perturbation can be compared at
                # all. The raw drift alone makes the thin barrier look robust
                # only because the same 0.2 nm is a much larger relative change
                # there.
                row["relative_drift_per_fractional_change"] = (
                    drift / fraction if fraction else None
                )
                drifts.append(drift)
            robustness_rows.append(row)
        if drifts:
            score = 1.0 / (1.0 + float(np.mean(drifts)))
            for record in records:
                if int(record.get("trial_index", -1)) == int(design["trial_index"]):
                    record["robustness_score"] = score
                    record["robustness_worst_case_relative_drift"] = max(drifts)
    if anchor_spec.source == "trial":
        anchor_row = next(
            (
                row for row in validation_rows
                if int(row.get("trial_index", -2)) == int(anchor_spec.trial_index)
                and row.get("case_id") == "nominal"
            ),
            None,
        )
    anchor_tracking = validation_anchor_tracking(
        cfg,
        anchor_spec,
        anchor_row,
        [row for row in validation_rows if row.get("case_id") == "nominal"],
    )
    write_json_atomically(state_dir / "anchor_state_tracking.json", anchor_tracking)
    return {
        "enabled": True,
        "validation_rows": validation_rows,
        "robustness_rows": robustness_rows,
        "designs_checked": [row.get("trial_index") for row in top],
        "solver_ran": bool(context.machine.run_solver),
        "anchor_tracking": anchor_tracking,
        "anchor_tracking_rows": anchor13.anchor_rows(anchor_tracking),
    }


def _parameters_from_validation_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key)[len("parameter_"):]: value
        for key, value in row.items()
        if str(key).startswith("parameter_")
    }


def validation_anchor_tracking(
    cfg: Mapping[str, Any],
    spec: anchor13.AnchorSpec,
    anchor_row: Mapping[str, Any] | None,
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Production Stage 5 entry point for fixed-anchor state assignment.

    The function reads only Stage 5 side-case outputs.  It never reaches into
    the protected optimization directory and therefore cannot rewrite v3.
    Planned/no-solver runs return a stated unavailable result; malformed
    completed data raise because silently weakening this validation gate would
    be worse than stopping it.
    """

    if not anchor_row or str(anchor_row.get("status")) != "completed":
        return {
            **spec.as_record(),
            "records": [],
            "fingerprints": {},
            "anchored_cases": 0,
            "method": "fixed_anchor_overlap_assignment",
            "order_independent": True,
            "energy_provenance": tracking13.UNAVAILABLE_ENERGY_LABEL,
            "derived_value_status": "unavailable",
            "unavailable_reason": "anchor side case has not completed with solver output",
        }

    anchor_parameters = _parameters_from_validation_row(anchor_row)
    anchor_states, bound_spec = anchor13.load_anchor_states(
        spec,
        Path(str(anchor_row["output_directory_path"])) / "extracted",
        anchor_parameters,
        cfg,
        observables=anchor_row,
    )
    cases: list[tracking13.TrialStates] = []
    historical_labels: dict[int, Any] = {}
    for row in case_rows:
        if str(row.get("status")) != "completed":
            continue
        trial_index = int(row.get("trial_index", -1))
        states = tracking13.load_trial_states(
            trial_index,
            design13.canonicalize(_parameters_from_validation_row(row), cfg),
            Path(str(row["output_directory_path"])) / "extracted",
            observables=row,
        )
        if states is None:
            raise anchor13.AnchorError(
                f"nominal validation case for t{trial_index:04d} has no envelopes"
            )
        cases.append(states)
        historical_labels[trial_index] = row.get("historical_tracked_state_labels")

    summary = anchor13.assign_all_to_anchor(cases, anchor_states, cfg, spec=bound_spec)
    confidence_constraint = next(
        (
            constraint
            for constraint in feasibility13.build_constraints(cfg)
            if constraint.metric == "state_tracking_confidence"
        ),
        None,
    )
    minimum_confidence = (
        float(confidence_constraint.threshold)
        if confidence_constraint is not None
        else 0.80
    )
    minimum_margin = float(
        (cfg.get("state_tracking") or {}).get("minimum_assignment_margin", 0.15)
    )
    for record in summary.get("records", []):
        old = historical_labels.get(int(record["trial_index"]))
        record["historical_tracked_state_labels"] = old
        record["labels_match_historical"] = (
            None if old is None else old == record.get("tracked_labels")
        )
    summary.update(
        {
            "acceptance_minimum_confidence": minimum_confidence,
            "acceptance_minimum_assignment_margin": minimum_margin,
            "acceptance_passed": bool(cases) and all(
                record.get("state_tracking_confidence") is not None
                and float(record["state_tracking_confidence"]) >= minimum_confidence
                and record.get("assignment_margin") is not None
                and float(record["assignment_margin"]) >= minimum_margin
                and not record.get("ambiguous")
                and not record.get("ambiguous_under_threshold")
                and record.get("labels_match_historical") is not False
                for record in summary.get("records", [])
            ),
            "derived_value_status": "available",
        }
    )
    return summary


def _run_side_case(
    context: sweeps.RunContext,
    state_dir: Path,
    case_id: str,
    resolved: Mapping[str, Any],
    *,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    """One Stage 5 case, run through exactly the same path as a trial."""

    case = sweeps.CaseSpec(
        case_id=case_id,
        label=case_id,
        swept={},
        config=dict(resolved),
        metadata={"sweep_kind": "validation"},
    )
    result = sweeps.execute_case(
        demo_dir=context.demo_dir,
        spec=case,
        machine=context.machine,
        run_dir=state_dir / case_id,
        render_values=demo12.render_values,
        analyse=demo11.analyse_case,
        dependency_report=context.dependency_report,
    )
    record = metrics13.build_record(
        parameters=design13.parameters_from_config(dict(resolved)),
        cfg=context.cfg,
        observables=result.observables,
        validation=result.validation,
        status=result.status,
        failure_reason=result.failure_reason,
        extracted_dir=result.run_dir / "extracted",
        runtime_seconds=result.runtime_seconds,
    )
    return {
        **dict(extra),
        **record,
        "status": result.status,
        "output_directory_path": str(result.run_dir),
        "checked": result.status == "completed",
        "not_checked_reason": ""
        if result.status == "completed"
        else "no licensed nextnano++ solver on this machine; case planned and generated only",
    }


# ---------------------------------------------------------------------------
# prior-demo baselines
# ---------------------------------------------------------------------------


def load_prior_demo_best(
    results_root: Path | None, demo_id: str, cfg: Mapping[str, Any], *, case_id: str | None = None
) -> dict[str, Any] | None:
    """The reference (Demo 11) or best graded (Demo 12) design, if one exists."""

    if results_root is None:
        return None
    demo_root = Path(results_root) / demo_id
    if not demo_root.is_dir():
        return None
    runs = sorted((path for path in demo_root.iterdir() if path.is_dir()), reverse=True)
    for run in runs:
        cases = replay13.load_demo12_cases(run)
        candidates = [case for case in cases if case.status == "completed"]
        if case_id is not None:
            candidates = [case for case in candidates if case.case_id == case_id]
        best: dict[str, Any] | None = None
        for case in candidates:
            metrics = replay13.map_metrics(case.observables, cfg)
            if metrics.get("relative_chi2_at_target_wavelength_abs") is None:
                continue
            parameters = design13.parameters_from_config(case.config)
            row = {
                "source_demo": demo_id,
                "case_or_trial": case.case_id,
                "wide_well_nm": float(case.config["scientific"]["thick_well_nm"]),
                "narrow_well_nm": float(case.config["scientific"]["thin_well_nm"]),
                **{f"parameter_{name}": value for name, value in parameters.items()},
                **metrics,
                "trial_valid": case.validation.get("passed") is not False,
                "note": f"from {run.name}",
            }
            if best is None or float(row["relative_chi2_at_target_wavelength_abs"]) > float(
                best["relative_chi2_at_target_wavelength_abs"]
            ):
                best = row
        if best is not None:
            return best
    return None


# ---------------------------------------------------------------------------
# reporting the whole run
# ---------------------------------------------------------------------------


def write_run_artifacts(
    context: sweeps.RunContext,
    experiment: Experiment,
    *,
    records: Sequence[Mapping[str, Any]],
    plan_record: Mapping[str, Any],
    surrogate: Mapping[str, Any],
    replay: Mapping[str, Any] | None,
    validation: Mapping[str, Any],
    synthetic: bool,
    rejection_rows: Sequence[Mapping[str, Any]] = (),
    iteration_mapping: Sequence[Mapping[str, Any]] = (),
    proposed_vs_realized_rows: Sequence[Mapping[str, Any]] = (),
    budget_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Tables, figures and guides for one run bundle."""

    cfg = context.cfg
    records = derived13.corrected_records(records, cfg)
    parent = context.parent
    results_root = context.machine.results_root
    demo11_best = load_prior_demo_best(
        results_root, "11_paper_validation_interband_chi2_acqw", cfg, case_id="s1_ref"
    )
    demo12_best = load_prior_demo_best(
        results_root, replay13.DEMO12_ID, cfg
    )
    counts = design13.expected_evaluation_counts(cfg)
    comparison = report13.comparison_rows(
        demo11=demo11_best,
        demo12=demo12_best,
        demo13_records=records,
        evaluations_used={
            "demo11_abrupt_reference": 1 if demo11_best else None,
            "demo12_best_grid_graded": replay.get("pool_size") if replay else None,
            "demo13_best_target_wavelength": plan_record.get("completed_trials"),
            "demo13_best_intrinsic_peak": plan_record.get("completed_trials"),
            "demo13_most_robust": plan_record.get("completed_trials"),
            "demo13_final_validated": plan_record.get("completed_trials"),
        },
    )
    efficiency = (replay or {}).get("comparison") or {}
    tables13.write_all(
        parent,
        cfg=cfg,
        records=records,
        spec=experiment.spec,
        candidates=[
            {
                "trial_index": record.get("trial_index"),
                "iteration": record.get("iteration"),
                "candidate_id": record.get("candidate_id"),
                "generation_method": record.get("generation_method"),
                "generator": record.get("generator"),
                "expected_acquisition_value": record.get("expected_acquisition_value"),
                "lifecycle": _lifecycle(record),
                "duplicate_of_trial": record.get("duplicate_of_trial"),
                "status": record.get("status"),
                "reported_to_ax_as": record.get("reported_to_ax_as"),
                **{
                    key: record.get(key)
                    for key in (
                        "parameter_asymmetry_s",
                        "parameter_central_barrier_thickness_nm",
                        "parameter_grading_thickness_nm",
                        "parameter_grading_profile",
                    )
                },
            }
            for record in records
        ],
        surrogate_rows=surrogate.get("slice_rows", []),
        acquisition_rows=surrogate.get("acquisition_rows", []),
        importance=surrogate.get("importance"),
        ax_frontier=surrogate.get("ax_frontier", []),
        comparison_rows=comparison,
        validation_rows=validation.get("validation_rows", []),
        robustness_rows=validation.get("robustness_rows", []),
        anchor_tracking_rows=validation.get("anchor_tracking_rows", []),
        efficiency_rows=efficiency.get("summary", []),
        warm_start_rows=((replay or {}).get("ingested") or {}).get("provenance_rows", []),
        plan_record=plan_record,
        rejection_rows=rejection_rows,
        iteration_mapping=iteration_mapping,
        proposed_vs_realized_rows=proposed_vs_realized_rows,
        budget_record=budget_record,
        synthetic=synthetic,
    )

    # The Demo 11 abrupt reference was already loaded above for the comparison
    # table; it is the same design the `baseline_and_best_*` figures are named
    # after, and passing it here is what actually puts it in them.
    curves = physics_curves(
        cfg, records, experiment.state_dir, baseline=demo11_best
    )
    write_json_atomically(
        parent / "extracted" / "baseline_and_best_curve_provenance.json",
        {
            "rows": curves.get("curve_provenance", []),
            "baseline_source": "11_paper_validation_interband_chi2_acqw case s1_ref",
            "baseline_found": demo11_best is not None,
            "demo12_reference_found": demo12_best is not None,
            "demo12_note": (
                "Demo 12 has no licensed results under this results root; its "
                "comparison rows are reported as unavailable and are never inferred "
                "from Demo 13 trials"
            )
            if demo12_best is None
            else "Demo 12 licensed result located",
        },
    )
    context_plots = plots13.PlotContext(
        cfg=cfg,
        records=records,
        objective_metric=tables13.objective_metric_name(experiment.spec),
        objective_direction=(
            "minimize"
            if tables13.objective_metric_name(experiment.spec)
            in set(experiment.spec.minimized_metrics)
            else "maximize"
        ),
        best_by_iteration=tables13.best_so_far_by_iteration(records, experiment.spec),
        surrogate_slices=surrogate.get("slices", {}),
        partial_dependence=surrogate.get("partial_dependence", {}),
        importance_rows=tables13._importance_rows(surrogate.get("importance")),
        efficiency=efficiency,
        spectra=curves["spectra"],
        profiles=curves["profiles"],
        band_edges=curves["band_edges"],
        envelopes=curves["envelopes"],
        paper_curves=paper_curves(cfg, curves["spectra"]),
        measured_curves=measured_curves(cfg),
        robustness_rows=validation.get("robustness_rows", []),
        synthetic=synthetic,
    )
    plots13.write_all(parent / "plots", context_plots)

    best = _best_valid(records, experiment.spec)
    summary = {
        "licensed_results_present": any(
            str(record.get("status")) == "completed" and not record.get("synthetic")
            for record in records
        ),
        "completed_trials": plan_record.get("completed_trials"),
        "valid_trials": sum(1 for record in records if record.get("trial_valid")),
        "failed_trials": plan_record.get("failed_trials"),
        "best_objective": best.get(tables13.objective_metric_name(experiment.spec)),
        "best_trial_index": best.get("trial_index"),
        "ax_objective_string": experiment.spec.objective,
        "stage5_validated": bool(
            validation.get("enabled") and validation.get("solver_ran")
        ),
        "best_design": {
            key: best.get(key)
            for key in (
                "parameter_asymmetry_s",
                "parameter_central_barrier_thickness_nm",
                "parameter_grading_thickness_nm",
                "parameter_grading_profile",
                "relative_peak_chi2_abs",
                "peak_wavelength_nm",
                "relative_chi2_at_target_wavelength_abs",
                "signed_detuning_nm",
                "maximum_boundary_probability",
                "state_tracking_confidence",
            )
        }
        if best
        else {},
        "verdict": report13.verdict(comparison),
    }
    report13.write_guides(parent, cfg, summary)
    return {"summary": summary, "comparison": comparison, "counts": counts}


def validation_lifecycle(
    *,
    records: Sequence[Mapping[str, Any]],
    plan_record: Mapping[str, Any],
    mode: str,
    solver_ran_this_process: bool,
    model_available: bool,
    validation: Mapping[str, Any],
    dependency_report: Mapping[str, Any] | None,
    accounting: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Five separable questions the single "is it validated?" flag used to blur.

    The important one is the first: a run that reloads sixteen completed
    licensed trials has licensed execution *behind* it even though this process
    launched no solver.  Reading licensed completion from
    ``result.solver_success`` -- which reflects only this invocation -- made the
    validation report announce "no licensed nextnano++ solver ran on this
    machine" for a study of sixteen premium trials.  It is read from the ledger
    instead.

    Synthetic trials are excluded: the Stage 1 surface completes trials without
    a solver, and counting those as licensed execution would let a
    no-licence machine claim a licensed run.
    """

    completed = [
        record for record in records if str(record.get("status")) == "completed"
    ]
    licensed_completed = [
        record for record in completed if not record.get("synthetic")
    ]
    lifecycle: dict[str, Any] = {
        "licensed_execution_completed": bool(licensed_completed),
        "licensed_trials_completed": len(licensed_completed),
        "licensed_trials_expected": int(plan_record["num_initial_trials"])
        + int(plan_record["num_iterations"]) * int(plan_record["batch_size"]),
        "synthetic_trials_completed": len(completed) - len(licensed_completed),
        # Reanalysis reloads completed records, so `solver_success` is true for
        # all of them without nextnano having been invoked. The mode is what
        # settles whether this process could have called it.
        "solver_invoked_by_this_run": bool(solver_ran_this_process)
        and mode != "analyze_existing_results",
        # Read from the authoritative accounting. This used to read
        # `plan_record["remaining_new_solver_runs"]`, a key `plan()` does not
        # return, so the `.get` default of 1 was used on every run and the flag
        # was permanently False -- including for the completed 16/16 campaign.
        "optimization_completed": bool(
            (accounting or {}).get("optimization_completed", False)
        ),
        "remaining_evaluations": int((accounting or {}).get("remaining_evaluations", -1)),
        "reporting_completed": bool(model_available),
        "stage5_physical_validation_completed": bool(
            validation.get("enabled") and validation.get("solver_ran")
        ),
        "dependency_validation_complete": bool(
            (dependency_report or {}).get(
                "all_dependencies_physically_validated", False
            )
        ),
        "dependencies_not_physically_validated": list(
            (dependency_report or {}).get("dependencies_not_physically_validated", [])
        ),
    }
    lifecycle["state"] = (
        "physically_validated"
        if lifecycle["stage5_physical_validation_completed"]
        else "licensed_optimization_completed_validation_pending"
        if lifecycle["licensed_execution_completed"]
        else "implemented_dry_run"
    )
    return lifecycle


def _lifecycle(record: Mapping[str, Any]) -> str:
    """Delegates to the one place that classifies a proposal's outcome.

    This used to hard-code "rejected as a canonical duplicate" for every
    rejected record, which on the v3 campaign was wrong seven times out of
    seven: all seven refusals were sub-resolution grades, and none was a
    duplicate of anything.
    """

    return accounting13.lifecycle_phrase(record)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def main(demo_dir: Path, machine_path: Path | None = None) -> int:
    context = sweeps.prepare_run(demo_dir, machine_path)
    cfg = context.cfg
    validate_demo13_config(cfg)
    versions = axsearch13.check_ax_version(cfg)

    simulation = cfg.get("simulation") or {}
    if not bool(simulation.get("run_solver", False)):
        # The YAML gate can only ever disable the solver, never enable one that
        # the machine does not have.
        context = dataclasses.replace(
            context, machine=dataclasses.replace(context.machine, run_solver=False)
        )
    if simulation.get("threads") is not None:
        # Thread count is a scheduling preference, not a capability, so unlike
        # run_solver the demo's YAML may raise it as well as lower it.
        context = dataclasses.replace(
            context,
            machine=dataclasses.replace(
                context.machine, threads=int(simulation["threads"])
            ),
        )

    mode = str((cfg.get("workflow") or {}).get("mode", "closed_loop"))
    state_dir = experiment_state_dir(cfg, context.machine.results_root)
    if mode == "synthetic_smoke_test":
        state_dir = state_dir.parent / f"{state_dir.name}_synthetic"

    synthetic = mode == "synthetic_smoke_test"
    replay: dict[str, Any] | None = None
    loop_result: dict[str, Any] = {"events": [], "stop_reason": "mode did not run trials"}
    state_manifest_before: dict[str, Any] | None = None
    terminal_before: dict[str, str] = {}

    # Warm starting is a file read; the Stage 2 replay is a whole study. Only
    # demo12_replay pays for the second.
    warm_start_enabled = bool(
        (cfg["bo"].get("warm_start") or {}).get("use_demo12_warm_start", False)
    ) and not synthetic
    ingested: dict[str, Any] = (
        replay13.ingest_warm_start(cfg, context.machine.results_root)
        if warm_start_enabled
        else {"enabled": False, "provenance_rows": [], "observations": [],
              "candidate_count": 0, "compatible_count": 0, "used_count": 0}
    )

    if synthetic:
        outcome = synthetic_loop(cfg, state_dir)
        experiment = outcome["experiment"]
        write_json_atomically(
            context.parent / "extracted" / "synthetic_optimum_recovery.json",
            {
                "known_optimum": outcome["known_optimum"],
                "recovery": outcome["recovery"],
                "label": synthetic13.SYNTHETIC_LABEL,
            },
        )
        loop_result = {"events": outcome["events"], "stop_reason": "synthetic study complete"}
    else:
        # Reanalysis opens the finished study read-only: no checkpoint write, no
        # ledger write, no candidate generation, and a hard error rather than a
        # freshly invented experiment if the directory is not the one meant.
        analysis_only = mode == "analyze_existing_results"
        experiment = Experiment(
            cfg,
            state_dir,
            warm_start=ingested.get("observations", ()),
            read_only=analysis_only,
        )
        if analysis_only:
            state_manifest_before = analysis13.state_manifest(state_dir)
            terminal_before = analysis13.terminal_ledger_fingerprint(state_dir)
        for row in ingested.get("provenance_rows", []):
            row["ax_trial_index"] = None
        for row, attachment in zip(
            [row for row in ingested.get("provenance_rows", []) if row.get("used_by_ax")],
            experiment.warm_start_attachments,
        ):
            row["ax_trial_index"] = attachment.get("ax_trial_index")
            row["used_by_ax"] = bool(attachment.get("attached"))
            if not attachment.get("attached"):
                row["not_used_reason"] = str(attachment.get("reason"))
        if mode == "demo12_replay":
            replay = replay_study(cfg, context.machine.results_root)
        elif mode == "prepare_candidates":
            loop_result = closed_loop(context, experiment, generate=True, run_solver_trials=False)
        elif mode == "run_pending_candidates":
            loop_result = closed_loop(context, experiment, generate=False, run_solver_trials=True)
        elif mode == "closed_loop":
            loop_result = closed_loop(context, experiment)
        elif mode in {"analyze_existing_results", "validate_top_designs"}:
            loop_result = {"events": [], "stop_reason": f"{mode} does not generate candidates"}

    records = derived13.corrected_records(experiment.ledger.records(), cfg)
    if replay is None:
        replay = {
            "demo12_run_dir": ingested.get("demo12_run_dir"),
            "pool_source": "not run (warm-start ingestion only)",
            "pool_size": None,
            "ingested": ingested,
            "comparison": {},
        }
    else:
        replay.setdefault("ingested", ingested)

    plan_record = experiment.plan
    print("\n".join(axsearch13.plan_report_lines(plan_record)))
    write_json_atomically(context.parent / "extracted" / "run_plan.json", plan_record)

    # Section 11: say plainly whether anything feasible exists, and warn loudly
    # if a modelled constraint cannot be resolved by the surrogate -- the defect
    # that produced BoTorch's all-infeasible warning on 2026-07-31.
    constraint_specs = feasibility13.build_constraints(cfg)
    feasibility = feasibility13.feasibility_summary(records, constraint_specs)
    spread = feasibility13.constraint_spread(records, constraint_specs)
    unresolvable = feasibility13.unresolvable_modelled_constraints(spread)
    write_json_atomically(
        context.parent / "extracted" / "feasibility_summary.json",
        {**feasibility, "unresolvable_modelled_constraints": unresolvable,
         "constraint_modelling": [dict(row) for row in spread]},
    )
    print(f"  feasible trials             : {feasibility['feasible_count']} "
          f"of {feasibility['completed_trials']} completed")
    if feasibility["initial_design_all_infeasible"]:
        print("  NOTE: the initial design contained no feasible point; "
              "improvement among infeasible designs is not progress.")
    if unresolvable:
        print("  WARNING: modelled constraint(s) the surrogate cannot resolve, "
              "which will make every observation infeasible: "
              + ", ".join(unresolvable))

    validation = (
        run_validation_study(context, experiment, records)
        if mode == "validate_top_designs"
        else {"enabled": False, "validation_rows": [], "robustness_rows": [], "solver_ran": False}
    )
    if validation.get("enabled"):
        records = derived13.corrected_records(experiment.ledger.records(), cfg)

    # The one authoritative count. Everything that reports a number -- console,
    # both manifests, the validation report, the results overview, the budget
    # table and the candidate history -- projects from this dict rather than
    # recomputing, which is how the v3 bundle came to report 0 preflight-invalid
    # proposals beside 7 abandoned trials.
    accounting = accounting13.campaign_accounting(records, cfg)
    accounting["analysis_only_run"] = mode == "analyze_existing_results"
    write_json_atomically(
        context.parent / "extracted" / "campaign_accounting.json", accounting
    )
    print("\n".join(accounting13.report_lines(accounting)))

    # The budget table is a projection of the same dict, never a second
    # derivation: two derivations is exactly what disagreed.
    budget = accounting13.budget_table_row(accounting)
    write_json_atomically(context.parent / "extracted" / "budget_accounting.json", budget)

    # A deserialized Ax client has no fitted adapter, so the surrogate is
    # rebuilt here -- from the completed observations, on a private copy of the
    # client, without advancing the generation strategy and without writing
    # anything back. Everything downstream that needs a prediction uses this.
    model = analysis13.reconstruct_predictive_model(experiment.snapshot_path)
    analysis13.write_reconstruction_report(context.parent / "extracted", model)
    print(
        f"  analysis surrogate          : {model.record.get('fit_status')} "
        f"({model.record.get('model_class') or 'no adapter'}; "
        f"{model.record.get('observations_used')} observations)"
    )
    if not model.available:
        print(f"  NOTE: {model.reason}")

    surrogate = surrogate_artifacts(experiment, records, model)
    artifacts = write_run_artifacts(
        context,
        experiment,
        records=records,
        plan_record=plan_record,
        surrogate=surrogate,
        replay=replay,
        validation=validation,
        synthetic=synthetic,
        # Rebuilt from the ledger, not from this run's in-memory loop state.
        # Reanalysis never runs the loop, so the old source was empty on every
        # reanalysis -- for a campaign with seven refusals on record.
        rejection_rows=accounting13.rejection_history(records, cfg),
        iteration_mapping=accounting13.trial_iteration_mapping(records),
        proposed_vs_realized_rows=accounting13.proposed_versus_realized_grading(records, cfg),
        budget_record=budget,
    )

    # A refused proposal is not a solver case: no deck was rendered and nothing
    # was executed, so it cannot be a case that failed to complete. Including
    # them here made the shared manifest writer compare 16 completed against 23
    # cases and stamp the whole campaign `status: failed` -- a campaign with
    # sixteen successes and zero failures. They remain fully reported in the
    # candidate-history and rejection-history tables.
    evaluated_records = [
        record for record in records if str(record.get("status")) != "rejected"
    ]
    results = [
        sweeps.CaseResult(
            spec=sweeps.CaseSpec(
                case_id=str(record.get("candidate_id", f"t{record.get('trial_index')}")),
                label=str(record.get("candidate_id", "")),
                swept=dict(record.get("canonical_parameters") or {}),
                config={},
                metadata={"iteration": record.get("iteration")},
            ),
            run_dir=Path(str(record.get("output_directory_path") or state_dir)),
            status="completed" if str(record.get("status")) == "completed" else "failed"
            if str(record.get("status")) == "failed"
            else "skipped_no_solver",
            runtime_seconds=float(record.get("runtime_seconds") or 0.0),
            observables={
                key: value
                for key, value in record.items()
                if isinstance(value, (int, float, str, bool)) or value is None
            },
            validation={"passed": bool(record.get("trial_valid"))},
            failure_reason=record.get("failure_reason"),
        )
        for record in evaluated_records
    ]
    sweeps.write_sweep_summary(context.parent, results)
    sweeps.write_failed_and_suspicious(context.parent, results)
    sweeps.write_state_tracking(
        context.parent,
        [
            {
                "trial_index": record.get("trial_index"),
                "reference_trial": record.get("state_tracking_reference_trial"),
                "state_tracking_confidence": record.get("state_tracking_confidence"),
                "assignment_margin": record.get("state_tracking_margin"),
                "ambiguous": record.get("state_tracking_ambiguous"),
                "raw_indices": record.get("raw_state_indices"),
                "tracked_labels": record.get("tracked_state_labels"),
                "method": record.get("state_tracking_method"),
            }
            for record in records
        ],
    )

    lifecycle = validation_lifecycle(
        records=records,
        plan_record=plan_record,
        mode=mode,
        solver_ran_this_process=any(result.solver_success for result in results),
        model_available=model.available,
        validation=validation,
        dependency_report=context.dependency_report,
        accounting=accounting,
    )
    write_json_atomically(
        context.parent / "extracted" / "validation_lifecycle.json", lifecycle
    )

    manifest = sweeps.write_sweep_manifest(
        context.parent,
        cfg=cfg,
        machine=context.machine,
        results=results,
        dependency_report=context.dependency_report,
        parser_provenance={"profile": cfg["outputs"].get("parser_profile")},
        extra={
            "workflow_mode": mode,
            "ax": versions,
            "optimization": experiment.spec.as_record(),
            "run_plan": plan_record,
            "experiment_state_dir": str(state_dir),
            "experiment_resumed": experiment.resumed,
            "loop_stop_reason": loop_result.get("stop_reason"),
            "loop_events": loop_result.get("events"),
            "extraction_version": EXTRACTION_VERSION,
            "warm_start": {
                key: value
                for key, value in ((replay or {}).get("ingested") or {}).items()
                if key != "provenance_rows"
            },
            "replay": {
                key: value
                for key, value in (replay or {}).items()
                if key not in {"ingested", "comparison"}
            },
            "validation_study": {
                key: value
                for key, value in validation.items()
                if key not in {"validation_rows", "robustness_rows"}
            },
            "summary": artifacts["summary"],
            "synthetic_study": synthetic,
            # The shared manifest's own `status` field answers "did THIS process
            # run a solver". In analyze mode it is derived from reloaded records
            # and so reads `completed` without a solver having been invoked.
            # These two keys keep that from being read as a licensed run.
            "validation_lifecycle": lifecycle,
            "campaign_accounting": accounting,
            # The shared `status` field answers "did every case in this manifest
            # complete". Refused proposals are not cases and are excluded from
            # `results`, so their count is carried here instead of silently
            # turning a successful campaign into `status: failed`.
            "proposals_refused_at_preflight": accounting["preflight_rejected"],
            "proposals_total": accounting["proposed_candidates"],
            "licensed_result_claim": (
                "not run"
                if not lifecycle["licensed_execution_completed"]
                else "licensed trials completed; see the criterion-level validation "
                "report and extracted/validation_lifecycle.json"
            ),
            "solver_invoked_by_this_run": lifecycle["solver_invoked_by_this_run"],
        },
    )
    experiment_manifest = {
        "demo_id": cfg["demo_id"],
        "experiment_name": (cfg.get("workflow") or {}).get("experiment_name"),
        "ax": versions,
        "optimization": experiment.spec.as_record(),
        "run_plan": plan_record,
        "last_run_bundle": str(context.parent),
        "extraction_version": EXTRACTION_VERSION,
        "updated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if experiment.read_only:
        # Even this bookkeeping file is a write into the protected directory.
        # It goes into the run bundle instead, so the experiment state after a
        # reanalysis is byte-for-byte what it was before.
        write_json_atomically(
            context.parent / "extracted" / "experiment_manifest_not_written.json",
            {
                **experiment_manifest,
                "written_to_experiment_state_dir": False,
                "reason": "analyze_existing_results opens the experiment read-only",
            },
        )
    else:
        write_json_atomically(
            experiment.state_dir / "experiment_manifest.json", experiment_manifest
        )

    # Phase 1's promise, checked rather than asserted: reanalysis leaves the
    # snapshot, the ledger, every trial record and every trial directory exactly
    # as it found them.
    if state_manifest_before is not None:
        protection = {
            "experiment_state_dir": str(state_dir),
            "workflow_mode": mode,
            "manifest_before": state_manifest_before,
            "verification": analysis13.verify_state_manifest(
                state_dir, state_manifest_before
            ),
            "terminal_records_before": len(terminal_before),
            "terminal_records_changed": sorted(
                index
                for index, digest in analysis13.terminal_ledger_fingerprint(
                    state_dir
                ).items()
                if terminal_before.get(index) != digest
            ),
            "terminal_records_removed": sorted(
                set(terminal_before)
                - set(analysis13.terminal_ledger_fingerprint(state_dir))
            ),
            "ax_snapshot_modified": bool(
                model.record.get("original_experiment_state_modified")
            ),
            "generation_strategy_advanced": bool(
                model.record.get("generation_strategy_advanced")
            ),
            "new_trials_generated": bool(model.record.get("new_trials_generated")),
        }
        protection["experiment_state_unchanged"] = bool(
            protection["verification"]["unchanged"]
            and not protection["terminal_records_changed"]
            and not protection["terminal_records_removed"]
            and not protection["ax_snapshot_modified"]
            and not protection["generation_strategy_advanced"]
            and not protection["new_trials_generated"]
        )
        write_json_atomically(
            context.parent / "extracted" / "experiment_state_protection.json", protection
        )
        verdict = "unchanged" if protection["experiment_state_unchanged"] else "MODIFIED"
        print(f"  experiment state            : {verdict} after reanalysis")
        if not protection["experiment_state_unchanged"]:
            print(
                "  WARNING: reanalysis changed the protected experiment state; see "
                "extracted/experiment_state_protection.json"
            )

    licensed = lifecycle["licensed_execution_completed"]
    sweeps.write_validation_report(
        context.parent,
        cfg=cfg,
        manifest=manifest,
        registry_record=context.registry_record,
        dependency_report=context.dependency_report,
        criteria=[
            (
                "Ax version is installed and matches the repository pin",
                bool(versions["ax_version_matches_pin"]),
                f"installed {versions['ax_version_installed']}, pinned "
                f"{versions['ax_version_pinned']}",
            ),
            (
                "the configured BO budget was produced from the YAML",
                plan_record["expected_maximum_new_solver_runs"]
                == plan_record["num_initial_trials"]
                + plan_record["num_iterations"] * plan_record["batch_size"],
                "initial + iterations x batch, recomputed on every run",
            ),
            (
                "every generated candidate has an immutable ledger record",
                len(records) == len({int(record["trial_index"]) for record in records}),
                "one JSON file per trial; terminal records are never rewritten",
            ),
            (
                "licensed trials completed",
                True if licensed else None,
                "no licensed nextnano++ trial exists in this experiment"
                if not licensed
                else f"{lifecycle['licensed_trials_completed']} of "
                f"{lifecycle['licensed_trials_expected']} completed in the "
                "experiment ledger"
                + (
                    "; this run reloaded them and called no solver"
                    if not lifecycle["solver_invoked_by_this_run"]
                    else ""
                ),
            ),
            (
                "an analysis surrogate was reconstructed for the reports",
                True if model.available else False,
                str(model.record.get("fit_status_reason") or "")[:240],
            ),
            (
                "top designs passed Stage 5 validation",
                True if lifecycle["stage5_physical_validation_completed"] else None,
                "run workflow.mode: validate_top_designs on the licensed machine",
            ),
        ],
        notes=[
            "Demo 11 extraction, interband chi(2), origin-independence and quasi-bound "
            "diagnostics are reused unchanged; Demo 12 renders every input.",
            "A mechanically failed trial is reported to Ax as failed and never as a "
            "zero objective.",
            "The highest Ax objective is a proposed optimum until Stage 5 passes.",
            f"Workflow mode for this run: {mode}.",
            f"Validation lifecycle state: {lifecycle['state']}.",
            "The objective is a RELATIVE nonlinear-optical merit in arbitrary units. "
            "It is not calibrated chi(2) in pm/V, and ratios between designs are "
            "ratios on that relative scale.",
        ],
        unvalidated_syntax=[
            "inherits Demo 12's unvalidated ternary_linear/ternary_constant "
            "alloy-composition output layout"
        ],
    )
    return sweeps.finish_run(context, results=results, manifest=manifest)


def check(demo_dir: Path, machine_path: Path | None = None) -> int:
    """``--check``: report the environment and the planned budget, run nothing."""

    from demo_workflow import load_demo_config, load_machine_config

    cfg = load_demo_config(demo_dir)
    validate_demo13_config(cfg)
    machine = load_machine_config(machine_path)
    versions = axsearch13.check_ax_version(cfg)
    state_dir = experiment_state_dir(cfg, machine.results_root)
    # read_only: `Ledger.__post_init__` creates `trials/` otherwise, so a
    # command advertised as writing nothing would mutate a protected campaign.
    ledger = axsearch13.Ledger(state_dir, read_only=True) if state_dir.is_dir() else None
    plan_record = (
        axsearch13.plan(cfg, ledger)
        if ledger is not None
        else {
            **design13.expected_evaluation_counts(cfg),
            "completed_trials": 0,
            "failed_trials": 0,
            "pending_trials": 0,
            "remaining_trials": design13.expected_evaluation_counts(cfg)[
                "expected_maximum_new_solver_runs"
            ],
            "completed_bo_iterations": 0,
            "remaining_bo_iterations": int(cfg["bo"]["num_iterations"]),
            "estimated_remaining_runtime_seconds": None,
            "estimated_runtime_basis": "no experiment state yet",
            "evaluation_formula": "initial_trials + num_iterations * batch_size",
        }
    )
    summary = machine_summary(machine)
    print(f"Demo:                 {cfg['demo_id']}")
    print(f"Workflow mode:        {(cfg.get('workflow') or {}).get('mode')}")
    print(f"Ax version:           {versions['ax_version_installed']} "
          f"(pinned {versions['ax_version_pinned']}, api {versions['ax_api']})")
    print(f"Solver executable:    {summary.get('executable')}")
    print(f"Solver enabled:       {machine.run_solver and bool((cfg.get('simulation') or {}).get('run_solver'))}")
    print(f"Results root:         {summary.get('results_root')}")
    print(f"Experiment state dir: {state_dir}")
    print("Search space:")
    for spec in design13.search_space_specs(cfg):
        row = spec.as_row()
        print(
            f"  {row['parameter']:<34} {row['type']:<8} "
            + (f"[{row['lower']}, {row['upper']}]" if row["type"] == "range" else str(row["values"]))
        )
    print("\n".join(axsearch13.plan_report_lines(plan_record)))
    return 0


def stage5_check(demo_dir: Path, machine_path: Path | None = None) -> int:
    """``--stage5-check``: print exactly what the paid gate would run, run nothing.

    Everything a reviewer needs before authorizing licensed time, produced by
    the same functions that will spend it: the destination and its isolation
    verdict, the anchor, the two meshes, the resolved geometry of each case, and
    whether the full campaign is still blocked.
    """

    from demo_workflow import load_demo_config, load_machine_config

    cfg = load_demo_config(demo_dir)
    validate_demo13_config(cfg)
    machine = load_machine_config(machine_path)
    resolved = validation13.settings(cfg)
    state_dir = stage5_state_dir(cfg, machine.results_root)

    print(f"Stage 5 destination : {state_dir}")
    try:
        validation13.assert_isolated(
            state_dir,
            cfg,
            machine.results_root,
            experiment_dir=experiment_state_dir(cfg, machine.results_root),
        )
        validation13.assert_resume_schema_matches(state_dir, cfg)
        print("Isolation           : OK (not, inside, or containing any campaign)")
    except validation13.Stage5Error as exc:
        print(f"Isolation           : REFUSED - {exc}")
        return 2

    experiment = experiment_state_dir(cfg, machine.results_root)
    # read_only: see `check()`. This command prints "Nothing was written".
    ledger = (
        axsearch13.Ledger(experiment, read_only=True) if experiment.is_dir() else None
    )
    records = ledger.records() if ledger is not None else []
    if not records:
        print(f"Gate                : cannot plan - no ledger at {experiment}")
        return 2
    try:
        plan = stage5_gate_plan(cfg, records)
    except validation13.Stage5Error as exc:
        print(f"Gate                : REFUSED - {exc}")
        return 2

    print(f"Gate design/anchor  : {plan['design_candidate_id']} / {plan['gate_anchor_case']}")
    print(f"Reference mesh      : {plan['gate_reference_mesh_nm']:g} nm (already computed, not re-run)")
    print(f"Paid solver calls   : {plan['solver_calls_planned']}")
    for case in plan["planned_cases"]:
        print(
            f"  {case['case_id']:<24} mesh {case['active_region_grid_spacing_nm']:g} nm  "
            f"wide {case['resolved_wide_well_nm']:.6f} nm  "
            f"narrow {case['resolved_narrow_well_nm']:.6f} nm  "
            f"barrier {case['resolved_central_barrier_nm']:g} nm  "
            f"{case['grading_profile']} {case['grading_selected_thickness_nm']:g} nm"
        )
    anchor_record = validation13.gate_design_record(cfg, records)
    anchor_extracted = _gate_anchor_extracted_dir(
        anchor_record, cfg, machine.results_root
    )
    print(
        f"Anchor output       : "
        + (
            str(anchor_extracted)
            if anchor_extracted
            else (
                "MISSING at "
                f"{experiment / 'runs' / str(anchor_record.get('candidate_id'))/ 'extracted'}"
                " - the gate anchors on the completed trial and does not recompute "
                "it; run on the machine that executed the campaign"
            )
        )
    )
    allowed, reason = validation13.full_campaign_allowed(cfg, state_dir)
    print(f"Full campaign       : {'ALLOWED' if allowed else 'BLOCKED'} - {reason}")
    print("Nothing was written and no solver was called.")
    return 0
