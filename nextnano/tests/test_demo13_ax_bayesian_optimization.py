"""Home-laptop tests for Demo 13; no nextnano executable is invoked.

Every test here runs without a licensed solver.  Where a test needs an
evaluated design it uses the Stage 1 synthetic surface, which is deterministic
and has an analytically known optimum, and never presents its numbers as
physical results.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "nextnano" / "demos" / "13_ax_bayesian_optimization_graded_acqw"
SHARED = DEMO.parent / "_shared"
DEMO11 = DEMO.parent / "11_paper_validation_interband_chi2_acqw"
DEMO12 = DEMO.parent / "12_graded_interface_coupled_quantum_well_optimization"
for path in (str(DEMO), str(SHARED), str(DEMO11), str(DEMO12)):
    if path not in sys.path:
        sys.path.insert(0, path)

import axsearch13  # noqa: E402
import demo_workflow  # noqa: E402
import design13  # noqa: E402
import metrics13  # noqa: E402
import plots13  # noqa: E402
import replay13  # noqa: E402
import report13  # noqa: E402
import sweeps  # noqa: E402
import synthetic13  # noqa: E402
import tables13  # noqa: E402
import tracking13  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


@pytest.fixture(scope="module")
def fast_cfg(cfg):
    """A small but complete study, so the Ax tests stay quick."""

    small = copy.deepcopy(cfg)
    small["bo"]["num_initial_trials"] = 3
    small["bo"]["num_iterations"] = 2
    small["bo"]["batch_size"] = 1
    return small


# ---------------------------------------------------------------------------
# 1. YAML parsing
# ---------------------------------------------------------------------------


def test_demo_yaml_parses_against_the_registered_schema(cfg):
    assert cfg["demo_id"] == "13_ax_bayesian_optimization_graded_acqw"
    assert cfg["bo"]["library"] == "ax"
    assert cfg["workflow"]["mode"] in sorted(
        __import__("demo13").RUN_MODES
    )


def test_demo_yaml_rejects_an_unknown_top_level_section(cfg, tmp_path):
    import schemas

    broken = {**copy.deepcopy(cfg), "not_a_section": {}}
    with pytest.raises(schemas.SchemaError):
        schemas.validate_config(broken, schemas.schema_for(cfg["demo_id"]), "test")


def test_config_validation_catches_impossible_iteration_settings(cfg):
    import demo13

    demo13.validate_demo13_config(cfg)
    for key, value in (
        ("num_initial_trials", 0),
        ("num_iterations", -1),
        ("batch_size", 0),
        ("num_initial_trials", 1),
    ):
        broken = copy.deepcopy(cfg)
        broken["bo"][key] = value
        with pytest.raises(demo_workflow.DemoError):
            demo13.validate_demo13_config(broken)


def test_unknown_run_mode_is_rejected(cfg):
    import demo13

    broken = copy.deepcopy(cfg)
    broken["workflow"]["mode"] = "make_it_work"
    with pytest.raises(demo_workflow.DemoError):
        demo13.validate_demo13_config(broken)


# ---------------------------------------------------------------------------
# 2-4. search space, bounds, categorical profiles
# ---------------------------------------------------------------------------


def test_search_space_specs_match_the_yaml_bounds(cfg):
    specs = {spec.name: spec for spec in design13.search_space_specs(cfg)}
    assert set(specs) == {
        "asymmetry_s",
        "central_barrier_thickness_nm",
        "grading_thickness_nm",
        "grading_profile",
    }
    assert (specs["asymmetry_s"].lower, specs["asymmetry_s"].upper) == (0.36, 0.56)
    assert (
        specs["central_barrier_thickness_nm"].lower,
        specs["central_barrier_thickness_nm"].upper,
    ) == (0.5, 2.5)
    assert (
        specs["grading_thickness_nm"].lower,
        specs["grading_thickness_nm"].upper,
    ) == (0.0, 3.0)
    assert specs["grading_profile"].values == (
        "abrupt", "linear", "sigmoid", "erf", "cosine",
    )


def test_ax_search_space_is_created_for_both_encodings(cfg):
    for encoding in ("hierarchical", "flat"):
        variant = copy.deepcopy(cfg)
        variant["bo"]["search_space"]["encoding"] = encoding
        spec = axsearch13.build_optimization_spec(variant)
        client = axsearch13.create_client(variant, spec)
        proposals = client.get_next_trials(max_trials=1)
        parameters = next(iter(proposals.values()))
        canonical = design13.canonicalize(parameters, variant)
        assert 0.36 <= canonical["asymmetry_s"] <= 0.56
        assert 0.5 <= canonical["central_barrier_thickness_nm"] <= 2.5
        assert 0.0 <= canonical["grading_thickness_nm"] <= 3.0
        assert canonical["grading_profile"] in design13.GRADING_PROFILES


def test_hierarchical_abrupt_branch_carries_no_grading_parameters(cfg):
    spec = axsearch13.build_optimization_spec(cfg)
    client = axsearch13.create_client(cfg, spec)
    seen_modes = set()
    for _ in range(12):
        for index, parameters in client.get_next_trials(max_trials=1).items():
            seen_modes.add(parameters.get("interface_mode"))
            if parameters.get("interface_mode") == "abrupt":
                assert "grading_thickness_nm" not in parameters
                assert "grading_profile" not in parameters
            else:
                assert parameters["grading_thickness_nm"] > 0
            client.complete_trial(
                index,
                raw_data={name: 1.0 for name in spec.reported_metrics},
            )
    assert seen_modes == {"abrupt", "graded"}


def test_unsupported_grading_profile_is_rejected(cfg):
    broken = copy.deepcopy(cfg)
    broken["bo"]["search_space"]["grading_profile"]["values"] = ["abrupt", "parabolic"]
    with pytest.raises(demo_workflow.DemoError):
        design13.search_space_specs(broken)


def test_optional_parameters_are_disabled_by_default(cfg):
    assert design13.enabled_optional_parameters(cfg) == []


def test_enabling_an_optional_parameter_extends_the_search_space(cfg):
    variant = copy.deepcopy(cfg)
    variant["bo"]["optional_parameters"]["maximum_aluminum_fraction"]["enabled"] = True
    names = [spec.name for spec in design13.search_space_specs(variant)]
    assert "maximum_aluminum_fraction" in names
    resolved = design13.resolve_config(
        {
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 1.0,
            "grading_profile": "linear",
            "maximum_aluminum_fraction": 0.42,
        },
        variant,
    )
    assert resolved["scientific"]["aluminum_fraction"] == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# 5-6. abrupt canonicalization and duplicate prevention
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", ["abrupt", "linear", "sigmoid", "erf", "cosine"])
def test_abrupt_profile_forces_zero_grading_thickness(cfg, profile):
    canonical = design13.canonicalize(
        {
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 0.0,
            "grading_profile": profile,
        },
        cfg,
    )
    assert canonical["grading_thickness_nm"] == 0.0
    assert canonical["grading_profile"] == "abrupt"


def test_sub_resolution_grade_canonicalizes_to_abrupt(cfg):
    minimum = float(cfg["bo"]["search_space"]["minimum_graded_thickness_nm"])
    canonical = design13.canonicalize(
        {
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": minimum / 2,
            "grading_profile": "cosine",
        },
        cfg,
    )
    assert canonical == {
        "asymmetry_s": 0.46,
        "central_barrier_thickness_nm": 1.5,
        "grading_thickness_nm": 0.0,
        "grading_profile": "abrupt",
    }


def test_five_abrupt_labels_collapse_to_one_design_key(cfg):
    keys = {
        design13.design_key(
            {
                "asymmetry_s": 0.46,
                "central_barrier_thickness_nm": 1.5,
                "grading_thickness_nm": 0.0,
                "grading_profile": profile,
            },
            cfg,
        )
        for profile in design13.GRADING_PROFILES
    }
    assert len(keys) == 1


def test_hierarchical_and_flat_encodings_agree_on_the_design_key(cfg):
    hierarchical = design13.design_key(
        {"interface_mode": "abrupt", "asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.5},
        cfg,
    )
    flat = design13.design_key(
        {
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 0.0,
            "grading_profile": "abrupt",
        },
        cfg,
    )
    assert hierarchical == flat


def test_duplicate_detection_uses_the_configured_tolerances(cfg):
    base = {
        "asymmetry_s": 0.46,
        "central_barrier_thickness_nm": 1.5,
        "grading_thickness_nm": 1.0,
        "grading_profile": "linear",
    }
    seen = [design13.design_key(base, cfg)]
    nudged = {**base, "asymmetry_s": 0.46 + 1e-6}
    apart = {**base, "asymmetry_s": 0.50}
    assert design13.is_duplicate(nudged, seen, cfg)
    assert not design13.is_duplicate(apart, seen, cfg)


def test_deduplication_can_be_switched_off(cfg):
    variant = copy.deepcopy(cfg)
    variant["bo"]["search_space"]["deduplicate_canonical_designs"] = False
    base = {
        "asymmetry_s": 0.46,
        "central_barrier_thickness_nm": 1.5,
        "grading_thickness_nm": 0.0,
        "grading_profile": "abrupt",
    }
    assert not design13.is_duplicate(base, [design13.design_key(base, variant)], variant)


def test_geometrically_impossible_designs_are_refused(cfg):
    with pytest.raises(demo_workflow.DemoError):
        design13.resolve_config(
            {
                "asymmetry_s": 0.46,
                "central_barrier_thickness_nm": 0.6,
                # A centred grade wider than the narrowest adjacent layer would
                # overlap its neighbour and lose an interface endpoint.
                "grading_thickness_nm": 2.9,
                "grading_profile": "linear",
            },
            cfg,
        )


def test_resolved_config_preserves_total_well_material(cfg):
    total = design13.total_well_thickness_nm(cfg)
    for asymmetry in (0.36, 0.46, 0.56):
        resolved = design13.resolve_config(
            {
                "asymmetry_s": asymmetry,
                "central_barrier_thickness_nm": 1.8,
                "grading_thickness_nm": 0.0,
                "grading_profile": "abrupt",
            },
            cfg,
        )
        widths = resolved["scientific"]
        assert widths["thick_well_nm"] + widths["thin_well_nm"] == pytest.approx(total)
        assert design13.parameters_from_config(resolved)["asymmetry_s"] == pytest.approx(
            asymmetry
        )


def test_smooth_profiles_use_the_documented_staircase_implementation(cfg):
    for profile, implementation in (
        ("linear", "native"),
        ("abrupt", "native"),
        ("sigmoid", "staircase"),
        ("erf", "staircase"),
        ("cosine", "staircase"),
    ):
        resolved = design13.resolve_config(
            {
                "asymmetry_s": 0.46,
                "central_barrier_thickness_nm": 1.8,
                "grading_thickness_nm": 0.0 if profile == "abrupt" else 1.0,
                "grading_profile": profile,
            },
            cfg,
        )
        assert resolved["grading"]["implementation"] == implementation


# ---------------------------------------------------------------------------
# 7-9. iteration counting, batch size, initial trials
# ---------------------------------------------------------------------------


def test_expected_evaluation_count_is_the_documented_formula(cfg):
    for initial, iterations, batch in ((6, 10, 1), (6, 5, 1), (6, 20, 1), (4, 3, 2)):
        variant = copy.deepcopy(cfg)
        variant["bo"].update(
            {
                "num_initial_trials": initial,
                "num_iterations": iterations,
                "batch_size": batch,
            }
        )
        counts = design13.expected_evaluation_counts(variant)
        assert counts["expected_maximum_new_solver_runs"] == initial + iterations * batch


def test_iteration_label_separates_initial_design_from_bo_rounds(cfg):
    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 3, "num_iterations": 4, "batch_size": 2})
    labels = [axsearch13.iteration_of(index, variant) for index in range(11)]
    assert labels == [0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4]


def test_plan_counts_remaining_iterations_from_the_ledger(cfg, tmp_path):
    variant = copy.deepcopy(cfg)
    variant["bo"].update({"num_initial_trials": 2, "num_iterations": 4, "batch_size": 1})
    ledger = axsearch13.Ledger(tmp_path)
    for index in range(4):
        ledger.write(
            {
                "trial_index": index,
                "iteration": axsearch13.iteration_of(index, variant),
                "status": "completed",
                "runtime_seconds": 10.0,
            }
        )
    plan = axsearch13.plan(variant, ledger)
    assert plan["completed_trials"] == 4
    assert plan["completed_bo_iterations"] == 2
    assert plan["remaining_bo_iterations"] == 2
    assert plan["remaining_trials"] == 2
    assert plan["mean_completed_runtime_seconds"] == pytest.approx(10.0)
    assert plan["estimated_remaining_runtime_seconds"] == pytest.approx(20.0)


def test_changing_the_yaml_iteration_count_changes_the_plan(cfg, tmp_path):
    ledger = axsearch13.Ledger(tmp_path)
    for iterations, expected in ((5, 11), (10, 16), (20, 26)):
        variant = copy.deepcopy(cfg)
        variant["bo"]["num_iterations"] = iterations
        plan = axsearch13.plan(variant, ledger)
        assert plan["expected_maximum_new_solver_runs"] == expected
        assert plan["remaining_bo_iterations"] == iterations


def test_batch_size_generates_a_whole_batch(fast_cfg):
    variant = copy.deepcopy(fast_cfg)
    variant["bo"]["batch_size"] = 3
    variant["bo"]["num_initial_trials"] = 3
    spec = axsearch13.build_optimization_spec(variant)
    client = axsearch13.create_client(variant, spec)
    proposals = client.get_next_trials(max_trials=3)
    assert len(proposals) == 3


# ---------------------------------------------------------------------------
# 10-11. checkpointing and resume
# ---------------------------------------------------------------------------


def test_snapshot_round_trips_and_resumes_generation(fast_cfg, tmp_path):
    spec = axsearch13.build_optimization_spec(fast_cfg)
    client = axsearch13.create_client(fast_cfg, spec)
    for index, _parameters in client.get_next_trials(max_trials=2).items():
        client.complete_trial(index, raw_data={name: 0.5 for name in spec.reported_metrics})
    path = tmp_path / "snapshot.json"
    axsearch13.save_client(client, path)
    assert path.is_file()
    assert not path.with_suffix(".json.tmp").exists()
    reloaded = axsearch13.load_client(path)
    assert len(reloaded._experiment.trials) == 2
    assert list(reloaded.get_next_trials(max_trials=1))[0] == 2


def test_run_subdirectory_agrees_with_the_layout_actually_created(tmp_path):
    """Reconstructing a run's subdirectory must match what was written there.

    Reproduces the work-laptop failure of 2026-07-31, where all sixteen licensed
    trials were marked failed: the alloy-composition check rebuilt the solver
    output path as ``run_dir / "raw"``, but the layout builder creates
    ``raw_output``, so the scan searched a directory that never existed.
    """

    run_dir = tmp_path / "t0000"
    layout = demo_workflow.create_run_layout(run_dir)
    for key, path in layout.items():
        assert path.is_dir()
        assert demo_workflow.run_subdirectory(run_dir, key) == path
    with pytest.raises(demo_workflow.DemoError):
        demo_workflow.run_subdirectory(run_dir, "raw_output")


def test_alloy_composition_check_searches_the_real_solver_output_directory(cfg, tmp_path):
    """The composition check must look where the solver actually wrote."""

    import demo12

    run_dir = tmp_path / "t0000"
    layout = demo_workflow.create_run_layout(run_dir)
    table = layout["raw"] / "Structure" / "alloy_composition.dat"
    table.parent.mkdir(parents=True)
    table.write_text("0.0 0.55\n1.0 0.55\n", encoding="utf-8")

    case = sweeps.CaseSpec(
        case_id="t0000",
        label="probe",
        swept={},
        config=design13.resolve_config(
            {
                "asymmetry_s": 0.46,
                "central_barrier_thickness_nm": 1.8,
                "grading_thickness_nm": 0.0,
                "grading_profile": "abrupt",
            },
            cfg,
        ),
        metadata={},
    )
    result = sweeps.CaseResult(case, run_dir, "completed", 0, 0.0, {}, {}, [], None)
    # It must find the one table rather than raising "found 0".
    comparison = demo12._extract_realized_composition(case, result)
    assert comparison["realized_profile_status"] in {"reproduced", "invalid"}
    assert "source" in comparison


def test_missing_alloy_output_names_the_directory_it_searched(cfg, tmp_path):
    import demo12

    run_dir = tmp_path / "t0000"
    demo_workflow.create_run_layout(run_dir)
    case = sweeps.CaseSpec("t0000", "probe", {}, dict(cfg), {})
    result = sweeps.CaseResult(case, run_dir, "completed", 0, 0.0, {}, {}, [], None)
    with pytest.raises(demo_workflow.DemoError) as failure:
        demo12._extract_realized_composition(case, result)
    message = str(failure.value)
    assert "raw_output" in message
    assert "exists: True" in message


def test_pending_trial_directory_is_archived_not_overwritten(tmp_path):
    """A candidate generated without a solver must be runnable later.

    Reproduces the work-laptop failure of 2026-07-31: the run that proposed
    trial 0 wrote its deck and skipped execution, and executing it afterwards
    hit `FileExistsError` from the shared layout builder.
    """

    import demo13

    run_dir = tmp_path / "runs" / "t0000"
    (run_dir / "generated_input").mkdir(parents=True)
    (run_dir / "generated_input" / "case.in").write_text("deck", encoding="utf-8")
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"completion_status": "skipped_no_solver"}), encoding="utf-8"
    )

    archived = demo13.archive_unexecuted_run_dir(run_dir)

    assert archived is not None
    assert not run_dir.exists(), "the trial directory must be free for the real run"
    archive = Path(archived)
    assert archive.is_dir()
    assert (archive / "generated_input" / "case.in").read_text(encoding="utf-8") == "deck"
    # The shared layout builder can now do its job on a clean directory.
    layout = demo_workflow.create_run_layout(run_dir)
    assert layout["generated"].is_dir()


def test_archiving_a_directory_that_never_ran_is_a_no_op(tmp_path):
    import demo13

    assert demo13.archive_unexecuted_run_dir(tmp_path / "runs" / "t0042") is None


def test_a_completed_licensed_run_directory_is_never_archived(tmp_path):
    import demo13

    run_dir = tmp_path / "runs" / "t0000"
    run_dir.mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"completion_status": "completed"}), encoding="utf-8"
    )
    with pytest.raises(demo_workflow.DemoError) as failure:
        demo13.archive_unexecuted_run_dir(run_dir)
    assert "Refusing to overwrite a licensed result" in str(failure.value)
    assert (run_dir / "run_manifest.json").is_file()


def test_checkpoint_survives_a_transient_windows_rename_denial(fast_cfg, tmp_path, monkeypatch):
    """WinError 5 during the checkpoint rename must not end a licensed run.

    Reproduces the work-laptop failure of 2026-07-31: the fifth checkpoint of a
    run that had already checkpointed four times was denied while an antivirus
    or indexing service held the target file.
    """

    spec = axsearch13.build_optimization_spec(fast_cfg)
    client = axsearch13.create_client(fast_cfg, spec)
    path = tmp_path / "ax_experiment_snapshot.json"
    axsearch13.save_client(client, path)
    first = path.read_text(encoding="utf-8")

    real_replace = axsearch13.os.replace
    calls = {"count": 0}

    def flaky(source, target):
        calls["count"] += 1
        if calls["count"] <= 3:
            raise PermissionError(5, "Access is denied")
        return real_replace(source, target)

    monkeypatch.setattr(axsearch13.os, "replace", flaky)
    monkeypatch.setattr(axsearch13, "REPLACE_BACKOFF_SECONDS", 0.0)
    for index, _parameters in client.get_next_trials(max_trials=1).items():
        client.complete_trial(index, raw_data={name: 0.5 for name in spec.reported_metrics})
    assert axsearch13.save_client(client, path) == path
    assert calls["count"] == 4
    assert path.read_text(encoding="utf-8") != first
    assert not list(tmp_path.glob("*.tmp"))


def test_checkpoint_falls_back_to_a_direct_write_when_rename_never_succeeds(
    fast_cfg, tmp_path, monkeypatch
):
    spec = axsearch13.build_optimization_spec(fast_cfg)
    client = axsearch13.create_client(fast_cfg, spec)
    path = tmp_path / "ax_experiment_snapshot.json"

    def always_denied(source, target):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(axsearch13.os, "replace", always_denied)
    monkeypatch.setattr(axsearch13, "REPLACE_BACKOFF_SECONDS", 0.0)
    axsearch13.save_client(client, path)
    assert path.is_file()
    # The snapshot must still be a loadable Ax experiment, not a partial write.
    assert axsearch13.load_client(path) is not None
    assert not list(tmp_path.glob("*.tmp"))


def test_checkpoint_reports_an_unwritable_target_actionably(fast_cfg, tmp_path, monkeypatch):
    spec = axsearch13.build_optimization_spec(fast_cfg)
    client = axsearch13.create_client(fast_cfg, spec)

    def always_denied(source, target):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(axsearch13.os, "replace", always_denied)
    monkeypatch.setattr(axsearch13, "REPLACE_BACKOFF_SECONDS", 0.0)
    monkeypatch.setattr(
        Path, "write_text", lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError(5, "denied"))
    )
    with pytest.raises(demo_workflow.DemoError) as failure:
        axsearch13.save_client(client, tmp_path / "snapshot.json")
    assert "antivirus" in str(failure.value)


def test_consecutive_checkpoints_do_not_share_a_temporary_path(fast_cfg, tmp_path, monkeypatch):
    """A fixed temporary name makes back-to-back checkpoints contend on Windows."""

    spec = axsearch13.build_optimization_spec(fast_cfg)
    client = axsearch13.create_client(fast_cfg, spec)
    path = tmp_path / "ax_experiment_snapshot.json"
    seen: list[str] = []
    real_replace = axsearch13.os.replace

    def record(source, target):
        seen.append(Path(source).name)
        return real_replace(source, target)

    monkeypatch.setattr(axsearch13.os, "replace", record)
    for _ in range(3):
        axsearch13.save_client(client, path)
    assert len(set(seen)) == 3


def test_ledger_records_are_immutable_once_terminal(tmp_path):
    ledger = axsearch13.Ledger(tmp_path)
    ledger.write({"trial_index": 0, "status": "completed"})
    with pytest.raises(demo_workflow.DemoError):
        ledger.write({"trial_index": 0, "status": "failed"})
    ledger.write({"trial_index": 0, "status": "failed"}, allow_update=True)
    assert ledger.record(0)["status"] == "failed"


def test_ledger_index_is_append_only(tmp_path):
    ledger = axsearch13.Ledger(tmp_path)
    ledger.write({"trial_index": 0, "status": "pending_no_solver"})
    ledger.write({"trial_index": 0, "status": "completed"})
    lines = ledger.index_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["status"] == "pending_no_solver"


def test_experiment_resumes_without_reattaching_warm_start(fast_cfg, tmp_path):
    import demo13

    observations = [
        {
            "parameters": {
                "asymmetry_s": 0.46,
                "central_barrier_thickness_nm": 1.5,
                "grading_thickness_nm": 1.0,
                "grading_profile": "linear",
            },
            "metrics": {name: 0.4 for name in
                        axsearch13.build_optimization_spec(fast_cfg).reported_metrics},
        }
    ]
    first = demo13.Experiment(fast_cfg, tmp_path, warm_start=observations)
    assert not first.resumed
    assert len(first.warm_start_attachments) == 1
    assert first.warm_start_attachments[0]["attached"]
    before = len(first.client._experiment.trials)
    second = demo13.Experiment(fast_cfg, tmp_path, warm_start=observations)
    assert second.resumed
    assert len(second.client._experiment.trials) == before


# ---------------------------------------------------------------------------
# 12-14. failed trials, valid zero chi2, objective and constraints
# ---------------------------------------------------------------------------


def test_mechanically_failed_trial_gets_no_objective(cfg):
    record = metrics13.build_record(
        parameters={
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 1.0,
            "grading_profile": "linear",
        },
        cfg=cfg,
        observables={},
        validation={},
        status="failed",
        failure_reason="nextnano++ returned nonzero exit code 1",
    )
    assert record["trial_outcome_class"] == metrics13.OUTCOME_MECHANICAL_FAILURE
    assert record["objective_available"] is False
    assert metrics13.ax_raw_data(record, ("chi2_at_target_wavelength_abs",)) is None


def test_missing_solver_output_is_pending_not_failed(cfg):
    record = metrics13.build_record(
        parameters={
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 0.0,
            "grading_profile": "abrupt",
        },
        cfg=cfg,
        observables={},
        validation={},
        status="skipped_no_solver",
    )
    assert record["trial_outcome_class"] == metrics13.OUTCOME_NOT_RUN
    assert "no licensed" in record["rejection_reason"]


def _valid_observables(chi2_at_target: float, peak: float = 1.0) -> dict:
    return {
        "chi2_relative_at_reference": chi2_at_target,
        "chi2_peak_magnitude": peak,
        "chi2_peak_wavelength_nm": 1552.0,
        "chi2_mode": "relative",
        "chi2_units": "arbitrary",
        "electron_energies_eV": [0.10, 0.16, 0.30, 0.45],
        "heavy_hole_energies_eV": [-0.02, -0.05, -0.09, -0.13],
        "E_e1_eV": 0.10,
        "E_e2_eV": 0.16,
        "E_hh1_eV": -0.02,
        "E_hh2_eV": -0.05,
        "transition_e1_hh1_eV": 0.12,
        "transition_e2_hh2_eV": 0.21,
        "overlap_e1_hh1": 0.93,
        "overlap_e2_hh2": 0.88,
        "z_e1_e1_nm": 12.0,
        "z_e1_e2_nm": 1.4,
        "z_hh1_hh1_nm": 11.6,
        "orthonormality_error_electron": 2e-7,
        "orthonormality_error_heavy_hole": 3e-7,
        "maximum_boundary_probability_bound_states": 2e-5,
        "maximum_left_boundary_probability": 1e-5,
        "maximum_right_boundary_probability": 1e-5,
        "absolute_residual": 4e-14,
        "relative_residual": 2e-9,
        "origin_independence_comparison_mode": "relative",
        "origin_independence_error": 2e-9,
        "chi2_max_states_per_band": 2,
        "chi2_electron_states_used": 2,
        "chi2_heavy_hole_states_used": 2,
        "chi2_triple_sum_terms_evaluated": 8,
        "chi2_triple_sum_terms_significant": 6,
        "solver_states_not_reaching_the_sum": 0,
        "states_failing_bound_criterion": 0,
        "states_failing_bound_criterion_in_chi2_sum": 0,
        "quasi_bound_policy": "warn",
    }


_VALID_VALIDATION = {
    "job_done_file_present": True,
    "no_stale_job_running_file": True,
    "probability_normalized": True,
    "envelopes_orthonormal": True,
    "electron_energies_ordered": True,
    "two_bound_electron_states": True,
    "bound_state_boundary_probability_small": True,
    "chi2_states_pass_bound_criterion": True,
    "chi2_origin_independent": True,
    "chi2_state_window_as_configured": True,
}


def test_valid_near_zero_chi2_is_distinguishable_from_a_failure(cfg):
    zero = metrics13.build_record(
        parameters={
            "asymmetry_s": 0.36,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 0.0,
            "grading_profile": "abrupt",
        },
        cfg=cfg,
        observables=_valid_observables(0.0, peak=1e-18),
        validation=dict(_VALID_VALIDATION),
        status="completed",
        tracking={"state_tracking_confidence": 0.99, "assignment_margin": 0.5},
    )
    assert zero["trial_outcome_class"] == metrics13.OUTCOME_VALID
    assert zero["trial_valid"] is True
    assert zero["valid_low_response"] is True
    assert zero["objective_available"] is True
    raw = metrics13.ax_raw_data(zero, ("chi2_at_target_wavelength_abs",))
    assert raw == {"chi2_at_target_wavelength_abs": 0.0}


def test_physically_invalid_trial_keeps_its_metrics(cfg):
    observables = _valid_observables(0.9)
    observables["maximum_boundary_probability_bound_states"] = 5e-2
    validation = dict(_VALID_VALIDATION)
    validation["bound_state_boundary_probability_small"] = False
    record = metrics13.build_record(
        parameters={
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 2.0,
            "grading_profile": "cosine",
        },
        cfg=cfg,
        observables=observables,
        validation=validation,
        status="completed",
        tracking={"state_tracking_confidence": 0.97, "assignment_margin": 0.4},
    )
    assert record["trial_outcome_class"] == metrics13.OUTCOME_INVALID
    assert record["chi2_at_target_wavelength_abs"] == pytest.approx(0.9)
    assert "boundary_probability" in record["constraint_violations"]
    assert record["objective_available"] is True


def test_objective_and_constraint_strings_match_the_configured_mode(cfg):
    spec = axsearch13.build_optimization_spec(cfg)
    assert spec.objective == "chi2_at_target_wavelength_abs"
    assert "detuning_nm_abs <= 15" in spec.outcome_constraints
    assert "physical_qc_valid >= 1" in spec.outcome_constraints
    assert not spec.is_multi_objective

    intrinsic = copy.deepcopy(cfg)
    intrinsic["bo"]["optimization_mode"] = "intrinsic_peak"
    assert axsearch13.build_optimization_spec(intrinsic).objective == "peak_chi2_abs"

    multi = copy.deepcopy(cfg)
    multi["bo"]["optimization_mode"] = "multi_objective"
    multi_spec = axsearch13.build_optimization_spec(multi)
    assert multi_spec.is_multi_objective
    assert "-detuning_nm_abs" in multi_spec.objective
    # A metric cannot be both an objective and an outcome constraint.
    assert not any("detuning_nm_abs" in text for text in multi_spec.outcome_constraints)
    assert multi_spec.dropped_constraints


def test_multi_objective_mode_produces_a_pareto_frontier(cfg):
    multi = copy.deepcopy(cfg)
    multi["bo"]["optimization_mode"] = "multi_objective"
    multi["bo"]["num_initial_trials"] = 4
    spec = axsearch13.build_optimization_spec(multi)
    client = axsearch13.create_client(multi, spec)
    # Constraint values a real valid trial would report, so the frontier is
    # computed over feasible points rather than over an empty set.
    feasible = {
        "maximum_boundary_probability": 2e-5,
        "state_tracking_confidence": 0.97,
        "orthonormality_error": 3e-7,
        "origin_independence_valid": 1.0,
        "required_states_valid": 1.0,
        "physical_qc_valid": 1.0,
    }
    for step in range(5):
        for index, parameters in client.get_next_trials(max_trials=1).items():
            canonical = design13.canonicalize(parameters, multi)
            client.complete_trial(
                index,
                raw_data={
                    "peak_chi2_abs": float(canonical["asymmetry_s"]),
                    "chi2_at_target_wavelength_abs": 1.0 - float(canonical["asymmetry_s"]),
                    "robustness_score": 0.5,
                    "detuning_nm_abs": 3.0 + step,
                    **{name: feasible[name] for name in spec.constraint_metrics},
                },
            )
    frontier = axsearch13.pareto_frontier(client)
    assert frontier
    assert {"trial_index", "arm_name"} <= set(frontier[0])


def test_constraint_metric_that_cannot_be_measured_blocks_completion(cfg):
    record = metrics13.build_record(
        parameters={
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 1.0,
            "grading_profile": "linear",
        },
        cfg=cfg,
        observables=_valid_observables(0.8),
        validation=dict(_VALID_VALIDATION),
        status="completed",
        tracking={},
    )
    assert record["state_tracking_confidence"] is None
    assert metrics13.ax_raw_data(record, ("state_tracking_confidence",)) is None


# ---------------------------------------------------------------------------
# 15. synthetic known-optimum recovery
# ---------------------------------------------------------------------------


def test_synthetic_surface_peaks_at_the_known_optimum(cfg):
    best = synthetic13.objective_value(synthetic13.SYNTHETIC_OPTIMUM, cfg)
    assert best == pytest.approx(1.0)
    for offset in ({"asymmetry_s": 0.52}, {"central_barrier_thickness_nm": 2.4},
                   {"grading_thickness_nm": 0.2}, {"grading_profile": "abrupt"}):
        worse = synthetic13.objective_value(
            {**synthetic13.SYNTHETIC_OPTIMUM, **offset}, cfg
        )
        assert worse < best


def test_synthetic_crash_corner_raises_rather_than_returning_zero(cfg):
    with pytest.raises(synthetic13.SyntheticFailure):
        synthetic13.evaluate(
            {
                "asymmetry_s": 0.46,
                "central_barrier_thickness_nm": 0.55,
                "grading_thickness_nm": 2.8,
                "grading_profile": "linear",
            },
            cfg,
        )


def test_synthetic_leaky_band_is_rejected_by_the_configured_constraint(cfg):
    record = synthetic13.evaluate(
        {
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 2.0,
            "grading_thickness_nm": 2.9,
            "grading_profile": "linear",
        },
        cfg,
    )
    assert record["maximum_boundary_probability"] > 1e-3
    assert "boundary_probability" in record["constraint_violations"]
    assert record["trial_valid"] is False


@pytest.mark.slow
def test_bayesian_optimization_recovers_the_synthetic_optimum(cfg, tmp_path):
    import demo13

    variant = copy.deepcopy(cfg)
    variant["bo"].update(
        {"num_initial_trials": 6, "num_iterations": 12, "batch_size": 1}
    )
    outcome = demo13.synthetic_loop(variant, tmp_path / "experiment")
    assert outcome["best"], "no valid synthetic design was found"
    recovery = outcome["recovery"]
    assert recovery["grading_profile_recovered"] is True
    assert recovery["asymmetry_s_absolute_error"] < 0.03
    assert recovery["central_barrier_thickness_nm_absolute_error"] < 0.35
    assert recovery["grading_thickness_nm_absolute_error"] < 0.45
    assert recovery["objective_at_proposed"] > 0.75 * recovery["objective_at_known_optimum"]


# ---------------------------------------------------------------------------
# 16-17. Demo 12 warm start
# ---------------------------------------------------------------------------


def _demo12_case(cfg, **overrides) -> replay13.Demo12Case:
    config = copy.deepcopy(dict(cfg))
    config["scientific"].update({"thick_well_nm": 7.3, "thin_well_nm": 2.7, "tunnel_barrier_nm": 1.8})
    config["grading"].update({"selected_thickness_nm": 1.0, "profile": "linear",
                              "implementation": "native", "location_mode": "all",
                              "center_shift_nm": 0.0, "interface_shift_nm": 0.0})
    for path, value in overrides.pop("config_overrides", {}).items():
        cursor = config
        parts = path.split(".")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value
    defaults = {
        "case_id": "t03",
        "stage": "stage2",
        "run_dir": Path("runs/t03"),
        "config": config,
        "observables": {
            "chi2_relative_at_reference": 0.62,
            "chi2_peak_magnitude": 1.05,
            "chi2_peak_wavelength_nm": 1544.0,
            "maximum_boundary_probability_bound_states": 3e-5,
            "state_tracking_confidence": 0.95,
            "orthonormality_error_electron": 1e-7,
            "orthonormality_error_heavy_hole": 1e-7,
        },
        "validation": {
            "passed": True,
            "chi2_origin_independent": True,
            "chi2_state_window_as_configured": True,
        },
        "status": "completed",
    }
    defaults.update(overrides)
    return replay13.Demo12Case(**defaults)


def test_compatible_demo12_case_is_ingested_with_full_provenance(cfg):
    result = replay13.ingest([_demo12_case(cfg)], cfg)
    row = result["provenance_rows"][0]
    assert row["compatible"] is True
    assert row["used_by_ax"] is True
    assert row["source_demo"] == replay13.DEMO12_ID
    assert row["source_case_id"] == "t03"
    assert row["source_file"].endswith("run_manifest.json")
    assert row["qc_status"] == "passed"
    assert "asymmetry_s<-structural_asymmetry" in row["parameter_mapping"]
    assert "chi2_at_target_wavelength_abs" in row["metric_mapping"]
    assert row["parameter_grading_thickness_nm"] == pytest.approx(1.0)
    assert row["metric_chi2_at_target_wavelength_abs"] == pytest.approx(0.62)


@pytest.mark.parametrize(
    "overrides,fragment",
    [
        ({"status": "failed"}, "not 'completed'"),
        ({"stage": "stage6"}, "compatible_stages"),
        (
            {"config_overrides": {"scientific.aluminum_fraction": 0.40}},
            "scientific.aluminum_fraction differs",
        ),
        (
            {"config_overrides": {"metric.broadening_meV": 12.0}},
            "metric.broadening_meV differs",
        ),
        (
            {"config_overrides": {"grading.profile": "staircase_linear"}},
            "no Demo 13 equivalent",
        ),
        (
            {"config_overrides": {"grading.center_shift_nm": 0.2}},
            "center_shift_nm is nonzero",
        ),
        (
            {"validation": {"passed": False}},
            "validation did not pass",
        ),
    ],
)
def test_incompatible_demo12_cases_are_rejected_with_a_reason(cfg, overrides, fragment):
    result = replay13.ingest([_demo12_case(cfg, **overrides)], cfg)
    row = result["provenance_rows"][0]
    assert row["compatible"] is False
    assert fragment in row["incompatibility_reasons"]
    assert row["used_by_ax"] is False
    assert not result["observations"]


def test_out_of_range_demo12_case_is_rejected(cfg):
    case = _demo12_case(
        cfg, config_overrides={"scientific.thick_well_nm": 9.0, "scientific.thin_well_nm": 1.0}
    )
    row = replay13.ingest([case], cfg)["provenance_rows"][0]
    assert row["compatible"] is False
    assert "outside the search range" in row["incompatibility_reasons"]


def test_warm_start_can_be_disabled_and_the_study_still_starts(cfg, tmp_path):
    import demo13

    disabled = copy.deepcopy(cfg)
    disabled["bo"]["warm_start"]["use_demo12_warm_start"] = False
    disabled["bo"].update({"num_initial_trials": 2, "num_iterations": 1})
    result = replay13.ingest([_demo12_case(cfg)], disabled)
    assert result["provenance_rows"][0]["not_used_reason"] == (
        "use_demo12_warm_start is false"
    )
    experiment = demo13.Experiment(disabled, tmp_path / "cold")
    assert experiment.warm_start_attachments == []
    assert experiment.generate(1)


def test_warm_start_budget_is_respected(cfg):
    limited = copy.deepcopy(cfg)
    limited["bo"]["warm_start"]["maximum_observations"] = 1
    cases = [_demo12_case(cfg, case_id=f"t{index:02d}") for index in range(3)]
    result = replay13.ingest(cases, limited)
    assert result["used_count"] == 1
    reasons = [row["not_used_reason"] for row in result["provenance_rows"]]
    assert any("budget" in reason for reason in reasons)


def test_warm_start_observation_without_a_metric_is_not_attached(fast_cfg, tmp_path):
    import demo13

    experiment = demo13.Experiment(
        fast_cfg,
        tmp_path / "partial",
        warm_start=[
            {
                "parameters": {
                    "asymmetry_s": 0.46,
                    "central_barrier_thickness_nm": 1.5,
                    "grading_thickness_nm": 1.0,
                    "grading_profile": "linear",
                },
                "metrics": {"chi2_at_target_wavelength_abs": 0.5},
            }
        ],
    )
    attachment = experiment.warm_start_attachments[0]
    assert attachment["attached"] is False
    assert "missing metric" in attachment["reason"]


# ---------------------------------------------------------------------------
# 18. state-tracking metric ingestion
# ---------------------------------------------------------------------------


def _states(trial_index, parameters, envelopes, energies=(0.10, 0.16)):
    z = np.linspace(-6, 6, 241)
    return tracking13.TrialStates(
        trial_index=trial_index,
        parameters=parameters,
        z_nm=z,
        electron_energies_eV=np.asarray(energies, dtype=float),
        electron_envelopes=envelopes,
        heavy_hole_energies_eV=np.asarray([-0.02, -0.05]),
        heavy_hole_envelopes=envelopes,
    )


def _normalized_pair():
    z = np.linspace(-6, 6, 241)
    left = np.exp(-((z + 2.0) / 0.9) ** 2)
    right = np.exp(-((z - 2.0) / 0.9) ** 2)
    left /= np.sqrt(np.trapezoid(left**2, z))
    right /= np.sqrt(np.trapezoid(right**2, z))
    return left, right


def test_state_tracking_follows_a_branch_through_a_label_swap(cfg):
    left, right = _normalized_pair()
    first = {
        "asymmetry_s": 0.44,
        "central_barrier_thickness_nm": 1.8,
        "grading_thickness_nm": 1.0,
        "grading_profile": "linear",
    }
    second = {**first, "asymmetry_s": 0.46}
    tracked = tracking13.track_sequence(
        [
            _states(0, first, np.column_stack([left, right])),
            # The solver returns the same two physical states in the opposite
            # energy order, with an arbitrary global sign flip on one of them.
            _states(1, second, np.column_stack([-right, left]), energies=(0.15, 0.155)),
        ],
        cfg,
    )
    rows = [row for row in tracked["rows"] if row["trial_index"] == 1 and row["band"] == "electron"]
    assert any(row["raw_index"] != row["tracked_label"] for row in rows)
    assert any(row["sign_flip_applied"] for row in rows)
    assert tracked["minimum_confidence"] > 0.8


def test_ambiguous_state_assignment_is_recorded_not_smoothed(cfg):
    z = np.linspace(0, 1, 201)
    a = np.sin(np.pi * z)
    b = np.sin(2 * np.pi * z)
    a /= np.sqrt(np.trapezoid(a * a, z))
    b /= np.sqrt(np.trapezoid(b * b, z))
    mixed = np.column_stack([(a + b) / np.sqrt(2), (a - b) / np.sqrt(2)])
    first = {
        "asymmetry_s": 0.44,
        "central_barrier_thickness_nm": 1.8,
        "grading_thickness_nm": 1.0,
        "grading_profile": "linear",
    }
    points = [
        tracking13.TrialStates(0, first, z, np.asarray([0.1, 0.2]), np.column_stack([a, b]),
                               np.asarray([-0.1, -0.2]), np.column_stack([a, b])),
        tracking13.TrialStates(1, {**first, "asymmetry_s": 0.45}, z, np.asarray([0.1, 0.2]),
                               mixed, np.asarray([-0.1, -0.2]), mixed),
    ]
    strict = copy.deepcopy(cfg)
    strict["state_tracking"]["minimum_assignment_margin"] = 0.9
    tracked = tracking13.track_sequence(points, strict)
    assert tracked["ambiguous_trials"] == [1]


def test_nearest_neighbour_reference_is_the_closest_design_not_the_last(cfg):
    left, right = _normalized_pair()
    envelopes = np.column_stack([left, right])
    base = {
        "asymmetry_s": 0.40,
        "central_barrier_thickness_nm": 1.0,
        "grading_thickness_nm": 1.0,
        "grading_profile": "linear",
    }
    history = [
        _states(0, base, envelopes),
        _states(1, {**base, "asymmetry_s": 0.55, "central_barrier_thickness_nm": 2.4}, envelopes),
    ]
    reference = tracking13.choose_reference({**base, "asymmetry_s": 0.405}, history, cfg)
    assert reference is not None and reference.trial_index == 0


def test_tracking_confidence_reaches_the_trial_record_and_constraint(cfg):
    record = metrics13.build_record(
        parameters={
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 1.0,
            "grading_profile": "linear",
        },
        cfg=cfg,
        observables=_valid_observables(0.8),
        validation=dict(_VALID_VALIDATION),
        status="completed",
        tracking={
            "state_tracking_confidence": 0.42,
            "assignment_margin": 0.05,
            "ambiguous": True,
            "reference_trial": 3,
            "method": "nearest_neighbour_overlap_assignment",
        },
    )
    assert record["state_tracking_confidence"] == pytest.approx(0.42)
    assert record["state_tracking_reference_trial"] == 3
    assert "state_tracking_confidence" in record["constraint_violations"]
    assert "state_tracking_ambiguous" in record["constraint_violations"]
    assert record["trial_valid"] is False


def test_first_completed_trial_is_an_anchor_not_a_perfect_match(cfg):
    left, right = _normalized_pair()
    tracked = tracking13.track_sequence(
        [_states(0, {"asymmetry_s": 0.46, "central_barrier_thickness_nm": 1.5,
                     "grading_thickness_nm": 0.0, "grading_profile": "abrupt"},
                 np.column_stack([left, right]))],
        cfg,
    )
    record = tracked["records"][0]
    assert record["method"] == "anchor_defines_labelling"
    assert record["reference_trial"] is None


def test_state_localization_and_boundary_metrics_are_extracted(cfg, tmp_path):
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    (extracted / "electron_states.csv").write_text(
        "state,energy_eV,normalised,bound,boundary_probability,"
        "probability_left_well,probability_right_well,probability_centre_barrier,"
        "probability_left_outer_barrier,probability_right_outer_barrier\n"
        "1,0.10,True,True,2e-05,0.62,0.28,0.07,0.02,0.01\n"
        "2,0.16,True,True,3e-05,0.30,0.60,0.06,0.02,0.02\n",
        encoding="utf-8",
    )
    character = metrics13.state_character(_valid_observables(0.8), extracted)
    assert character["central_barrier_probability"] == pytest.approx(0.07)
    assert character["outer_barrier_probability"] == pytest.approx(0.03)
    assert character["raw_solver_state_index"] == 1
    assert character["bound_state_count"] == 2
    assert character["total_boundary_probability"] == pytest.approx(2e-5)


# ---------------------------------------------------------------------------
# 19. missing nextnano output handling
# ---------------------------------------------------------------------------


def test_missing_chi2_spectrum_is_reported_not_guessed(cfg, tmp_path):
    assert metrics13.read_chi2_spectrum(tmp_path) is None
    record = metrics13.build_record(
        parameters={
            "asymmetry_s": 0.46,
            "central_barrier_thickness_nm": 1.5,
            "grading_thickness_nm": 1.0,
            "grading_profile": "linear",
        },
        cfg=cfg,
        observables=_valid_observables(0.8),
        validation=dict(_VALID_VALIDATION),
        status="completed",
        extracted_dir=tmp_path,
        tracking={"state_tracking_confidence": 0.95, "assignment_margin": 0.4},
    )
    assert record["integrated_chi2_abs"] is None
    assert record["bandwidth_above_fraction_nm"] is None
    assert record["chi2_at_target_wavelength_abs"] == pytest.approx(0.8)


def test_missing_envelopes_file_yields_no_trial_states(tmp_path):
    assert tracking13.load_trial_states(0, {}, tmp_path) is None


def test_spectrum_measures_integrate_and_measure_bandwidth(cfg):
    wavelength = np.linspace(1400.0, 1800.0, 401)
    magnitude = np.exp(-0.5 * ((wavelength - 1550.0) / 20.0) ** 2)
    measures = metrics13.spectrum_measures(wavelength, magnitude, cfg)
    assert measures["integrated_chi2_abs"] == pytest.approx(
        20.0 * np.sqrt(2 * np.pi), rel=1e-3
    )
    # Full width at half maximum of a Gaussian, on a raw sampled grid.
    assert measures["bandwidth_above_fraction_nm"] == pytest.approx(47.0, abs=2.0)


# ---------------------------------------------------------------------------
# 20-22. random search, grid search, Pareto extraction
# ---------------------------------------------------------------------------


def test_random_and_grid_baselines_use_the_same_space_and_objective(cfg):
    random_rows = synthetic13.random_search(cfg, evaluations=25, seed=3)
    grid_rows = synthetic13.grid_search(cfg, points_per_dimension=3)
    assert len(random_rows) == 25
    assert len(grid_rows) == 3 * 3 * 3 * 5
    for row in random_rows + grid_rows:
        assert row["search_method"] in {"random_search", "grid_search"}
        assert 0.36 <= row["parameter_asymmetry_s"] <= 0.56


def test_best_so_far_ignores_invalid_evaluations(cfg):
    rows = [
        {"chi2_at_target_wavelength_abs": 0.4, "trial_valid": True, "status": "completed"},
        {"chi2_at_target_wavelength_abs": 9.9, "trial_valid": False, "status": "completed"},
        {"chi2_at_target_wavelength_abs": None, "trial_valid": False, "status": "failed"},
        {"chi2_at_target_wavelength_abs": 0.6, "trial_valid": True, "status": "completed"},
    ]
    trace = synthetic13.best_so_far(rows)
    assert [row["best_so_far"] for row in trace] == [0.4, 0.4, 0.4, 0.6]
    assert synthetic13.evaluations_to_reach(trace, 0.5) == 4


@pytest.mark.slow
def test_replay_compares_bayesian_random_and_grid_search(cfg):
    pool = replay13.synthetic_pool(cfg, points_per_dimension=3)
    assert pool
    comparison = replay13.efficiency_comparison(
        pool, cfg, evaluations=10, seed=5, fraction_of_best=0.5
    )
    assert comparison["available"] is True
    methods = {row["search_method"] for row in comparison["summary"]}
    assert methods == {"bayesian_optimization", "random_search", "grid_search"}
    for row in comparison["summary"]:
        assert row["best_known_in_pool"] == pytest.approx(comparison["best_known_in_pool"])
    assert set(comparison["traces"]) == methods


def test_replay_drops_constraints_the_pool_cannot_evaluate(cfg):
    pool = [
        replay13.PoolPoint(
            identifier="p0",
            parameters={
                "asymmetry_s": 0.46,
                "central_barrier_thickness_nm": 1.5,
                "grading_thickness_nm": 1.0,
                "grading_profile": "linear",
            },
            metrics={"chi2_at_target_wavelength_abs": 0.5, "detuning_nm_abs": 2.0},
            valid=True,
        )
    ]
    reduced, dropped = replay13.replay_configuration(cfg, pool)
    assert "maximum_detuning_nm" in reduced["bo"]["outcome_constraints"]
    assert "maximum_boundary_probability" not in reduced["bo"]["outcome_constraints"]
    assert any("maximum_boundary_probability" in text for text in dropped)


def test_pareto_extraction_returns_only_nondominated_designs(cfg):
    spec = axsearch13.build_optimization_spec(cfg)
    records = [
        {"trial_index": 0, "status": "completed", "trial_valid": True,
         "peak_chi2_abs": 2.0, "chi2_at_target_wavelength_abs": 1.0, "detuning_nm_abs": 5.0},
        {"trial_index": 1, "status": "completed", "trial_valid": True,
         "peak_chi2_abs": 1.0, "chi2_at_target_wavelength_abs": 2.0, "detuning_nm_abs": 5.0},
        {"trial_index": 2, "status": "completed", "trial_valid": True,
         "peak_chi2_abs": 1.0, "chi2_at_target_wavelength_abs": 1.0, "detuning_nm_abs": 9.0},
        {"trial_index": 3, "status": "completed", "trial_valid": False,
         "peak_chi2_abs": 9.0, "chi2_at_target_wavelength_abs": 9.0, "detuning_nm_abs": 0.0},
    ]
    front = {row["trial_index"] for row in tables13.pareto_designs(records, spec)}
    assert front == {0, 1}


# ---------------------------------------------------------------------------
# 23-26. plots, CSVs, filenames, minimal text
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def synthetic_records(cfg):
    rows: list[dict] = []
    for index, (asymmetry, grading, profile) in enumerate(
        [
            (0.40, 0.0, "abrupt"),
            (0.44, 1.0, "linear"),
            (0.46, 1.4, "cosine"),
            (0.50, 2.0, "sigmoid"),
            (0.54, 2.9, "erf"),
        ]
    ):
        record = synthetic13.evaluate(
            {
                "asymmetry_s": asymmetry,
                "central_barrier_thickness_nm": 1.3,
                "grading_thickness_nm": grading,
                "grading_profile": profile,
            },
            cfg,
        )
        record.update(
            {
                "trial_index": index,
                "iteration": 0 if index < 3 else index - 2,
                "candidate_id": f"t{index:04d}",
                "status": "completed",
                "generation_method": "Sobol" if index < 3 else "MBM",
                "expected_acquisition_value": None if index < 3 else -1.2,
                "reported_to_ax_as": "completed",
                "design_role": "reference" if index == 0 else None,
            }
        )
        rows.append(record)
    rows.append(
        {
            "trial_index": 5,
            "iteration": 3,
            "candidate_id": "t0005",
            "status": "failed",
            "reported_to_ax_as": "failed",
            "failure_reason": "synthetic solver crash",
            "trial_valid": False,
            "parameter_asymmetry_s": 0.48,
            "parameter_central_barrier_thickness_nm": 0.55,
            "parameter_grading_thickness_nm": 2.8,
            "parameter_grading_profile": "linear",
        }
    )
    return rows


def test_every_plot_is_written_with_a_matching_csv(cfg, synthetic_records, tmp_path):
    context = plots13.PlotContext(
        cfg=cfg,
        records=synthetic_records,
        best_by_iteration=tables13.best_so_far_by_iteration(
            synthetic_records, axsearch13.build_optimization_spec(cfg)
        ),
        synthetic=True,
    )
    plots13.write_all(tmp_path / "plots", context)
    for filename, _question in plots13.PLOT_SET:
        png = tmp_path / "plots" / filename
        csv = tmp_path / "plot_data" / f"{Path(filename).stem}.csv"
        assert png.is_file(), f"missing figure {filename}"
        assert csv.is_file(), f"missing CSV for {filename}"
    assert len(plots13.PLOT_SET) == 47


def test_plot_filenames_are_descriptive_and_unique():
    names = [filename for filename, _question in plots13.PLOT_SET]
    assert len(names) == len(set(names))
    for name in names:
        assert name.endswith(".png")
        assert len(Path(name).stem) > 12
        assert Path(name).stem.replace("_", "").isalnum()


def test_plots_carry_no_titles_or_explanatory_text(cfg, synthetic_records, tmp_path):
    """The minimal-text policy, checked on the drawn figures themselves."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    drawn: list[tuple[str, list[str]]] = []
    original = plots13.plotting.save_figure_formats

    def capture(fig, base_path, **kwargs):
        texts = [text.get_text() for text in fig.texts]
        for axis in fig.axes:
            if axis.get_title():
                texts.append(axis.get_title())
        drawn.append((Path(base_path).name, [text for text in texts if text.strip()]))
        return original(fig, base_path, **kwargs)

    plots13.plotting.save_figure_formats = capture
    try:
        plots13.write_all(
            tmp_path / "plots",
            plots13.PlotContext(cfg=cfg, records=synthetic_records, synthetic=True),
        )
    finally:
        plots13.plotting.save_figure_formats = original
        plt.close("all")
    assert drawn, "no figures were drawn"
    for name, texts in drawn:
        assert not texts, f"{name} carries in-figure text: {texts}"


def test_figures_are_written_as_png_and_pdf(cfg, synthetic_records, tmp_path):
    plots13.write_all(
        tmp_path / "plots",
        plots13.PlotContext(cfg=cfg, records=synthetic_records, synthetic=True),
    )
    drawn = tmp_path / "plots" / "bo_chi2_at_1550_by_trial.png"
    assert drawn.is_file()
    assert drawn.with_suffix(".pdf").is_file()


def test_plot_csv_holds_the_plotted_numbers(cfg, synthetic_records, tmp_path):
    import csv as csv_module

    plots13.write_all(
        tmp_path / "plots",
        plots13.PlotContext(cfg=cfg, records=synthetic_records, synthetic=True),
    )
    path = tmp_path / "plot_data" / "bo_chi2_at_1550_by_trial.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv_module.DictReader(handle))
    # The CSV holds the numbers as plotted, so the x coordinate is a float.
    plotted = {int(float(row["trial_index"])) for row in rows}
    expected = {
        int(record["trial_index"])
        for record in synthetic_records
        if record["status"] == "completed"
    }
    assert plotted == expected


# ---------------------------------------------------------------------------
# 27. table generation
# ---------------------------------------------------------------------------


def test_all_required_tables_are_written_with_units(cfg, synthetic_records, tmp_path):
    spec = axsearch13.build_optimization_spec(cfg)
    written = tables13.write_all(
        tmp_path,
        cfg=cfg,
        records=synthetic_records,
        spec=spec,
        plan_record=axsearch13.plan(cfg, axsearch13.Ledger(tmp_path / "state")),
        synthetic=True,
    )
    required = {
        "bo_all_trials_parameters_and_outcomes",
        "bo_trial_input_parameters",
        "bo_trial_nonlinear_optical_outputs",
        "bo_trial_electronic_structure_outputs",
        "bo_trial_state_localization_and_tracking",
        "bo_trial_quality_control_results",
        "bo_best_objective_so_far_by_iteration",
        "bo_top_ranked_valid_designs",
        "bo_invalid_and_failed_trials",
        "demo11_demo12_demo13_best_design_comparison",
        "bo_generated_candidates_by_iteration",
        "bo_surrogate_predictions_selected_parameter_slices",
        "bo_acquisition_values_for_proposed_candidates",
        "bo_parameter_importance",
        "bo_pareto_optimal_designs",
        "bo_top_designs_local_validation_results",
        "bo_top_designs_fabrication_robustness",
        "bo_random_grid_search_efficiency_comparison",
    }
    assert required <= set(written)
    for name in written:
        assert (tmp_path / "tables" / f"{name}.csv").is_file()
        units = json.loads((tmp_path / "tables" / f"{name}.units.json").read_text("utf-8"))
        assert units["columns"]
        assert units["row_meaning"]
    for name in tables13.SUMMARY_TABLES:
        assert (tmp_path / "tables" / f"{name}.md").is_file()
        assert (tmp_path / "tables" / f"{name}.json").is_file()


def test_relative_chi2_columns_are_never_labelled_pm_per_volt():
    for column in ("chi2_at_target_wavelength_abs", "peak_chi2_abs"):
        assert "pm/V" not in tables13.unit_for(column)
        assert "a.u." in tables13.unit_for(column)


def test_invalid_and_failed_trials_table_keeps_every_rejected_trial(cfg, synthetic_records):
    rows = tables13.invalid_and_failed_trials(synthetic_records)
    assert {row["trial_index"] for row in rows} >= {5}
    failed = next(row for row in rows if row["trial_index"] == 5)
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "synthetic solver crash"


def test_best_so_far_table_never_counts_an_invalid_trial(cfg, synthetic_records):
    spec = axsearch13.build_optimization_spec(cfg)
    rows = tables13.best_so_far_by_iteration(synthetic_records, spec)
    best_values = [row["best_objective_so_far"] for row in rows if row["best_objective_so_far"]]
    assert best_values == sorted(best_values)
    invalid = [
        record["chi2_at_target_wavelength_abs"]
        for record in synthetic_records
        if record.get("status") == "completed" and not record.get("trial_valid")
    ]
    if invalid and best_values:
        assert max(best_values) != pytest.approx(max(invalid))


def test_top_designs_are_not_marked_validated(cfg, synthetic_records):
    spec = axsearch13.build_optimization_spec(cfg)
    rows = tables13.top_ranked_valid_designs(synthetic_records, spec)
    assert rows
    assert all(row["validated"] is False for row in rows)
    assert all("Stage 5" in row["validation_note"] for row in rows)


def test_search_space_table_records_the_hierarchical_encoding(cfg):
    rows = tables13.search_space_rows(cfg)
    names = {row["parameter"] for row in rows}
    assert "interface_mode" in names
    grading = next(row for row in rows if row["parameter"] == "grading_thickness_nm")
    assert grading["lower"] == pytest.approx(
        cfg["bo"]["search_space"]["minimum_graded_thickness_nm"]
    )


# ---------------------------------------------------------------------------
# 28. Markdown guide generation
# ---------------------------------------------------------------------------


def test_all_guides_are_generated(cfg, tmp_path):
    written = report13.write_guides(tmp_path, cfg)
    assert {path.name for path in written} == set(report13.GUIDE_FILES)
    for path in written:
        assert path.is_file()
        assert len(path.read_text(encoding="utf-8")) > 800


def test_plots_guide_documents_every_figure(cfg):
    text = report13.plots_guide(cfg)
    for filename, _question in plots13.PLOT_SET:
        assert f"`{filename}`" in text
        assert f"plot_data/{Path(filename).stem}.csv" in text
    assert set(report13.PLOT_GUIDE) == {name for name, _ in plots13.PLOT_SET}


def test_tables_guide_documents_every_table(cfg):
    text = report13.tables_guide(cfg)
    for name in tables13.TABLE_CATALOGUE:
        assert f"`{name}.csv`" in text


def test_ax_guide_reports_the_configured_budget(cfg):
    text = report13.ax_guide(cfg)
    counts = design13.expected_evaluation_counts(cfg)
    assert str(counts["expected_maximum_new_solver_runs"]) in text
    assert "mark_trial_failed" in text
    assert "hierarchical" in text
    assert "resume" in text.lower()


def test_paper_guide_refuses_absolute_units_and_digitized_targets(cfg):
    text = report13.paper_guide(cfg)
    assert "visual reference only" in text
    assert "not used as an optimization" in text
    assert "pm/V" in text  # explicitly discussed and rejected
    assert "measured second-harmonic intensity" in text.lower()


def test_work_laptop_guide_only_names_implemented_commands(cfg):
    text = report13.work_laptop_guide(cfg)
    assert "run_demo13.py" in text
    assert "--check" in text
    assert "bundle_results.py" in text
    assert (DEMO / "run_demo13.py").is_file()
    assert (ROOT / "nextnano" / "scripts" / "bundle_results.py").is_file()
    assert "test_demo13_ax_bayesian_optimization.py" in text


def test_results_overview_states_validation_status_honestly(cfg):
    text = report13.results_overview(cfg, {"licensed_results_present": False})
    assert "No licensed nextnano++ results are present" in text
    assert "proposed" in text


# ---------------------------------------------------------------------------
# final comparison and provenance
# ---------------------------------------------------------------------------


def test_final_comparison_covers_every_required_role(cfg, synthetic_records):
    rows = report13.comparison_rows(demo13_records=synthetic_records)
    assert [row["role"] for row in rows] == [label for _key, label in report13.COMPARISON_ROLES]
    missing = [row for row in rows if row["case_or_trial"] is None]
    assert all("not available" in row["note"] for row in missing)


def test_verdict_refuses_to_claim_validation_that_did_not_run(cfg, synthetic_records):
    rows = report13.comparison_rows(
        demo11={
            "source_demo": "11",
            "case_or_trial": "s1_ref",
            "chi2_at_target_wavelength_abs": 0.2,
            "peak_chi2_abs": 0.9,
            "detuning_nm": -30.0,
        },
        demo13_records=synthetic_records,
    )
    text = report13.verdict(rows)
    assert "Stage 5 validation has not been completed" in text
    assert "Stronger 1550 nm design" in text


def test_verdict_without_a_reference_says_so(cfg):
    assert "No verdict is possible" in report13.verdict([])


def test_optimization_spec_record_is_serializable(cfg):
    record = axsearch13.build_optimization_spec(cfg).as_record()
    assert json.loads(json.dumps(record))["ax_objective_string"]


def test_ax_version_is_checked_against_the_pin(cfg):
    versions = axsearch13.check_ax_version(cfg)
    assert versions["ax_version_installed"]
    assert versions["ax_api"] == "ax.api.client.Client"
    too_new = copy.deepcopy(cfg)
    too_new["bo"]["minimum_ax_version"] = "99.0.0"
    with pytest.raises(demo_workflow.DemoError):
        axsearch13.check_ax_version(too_new)


def test_generated_candidate_records_carry_generation_provenance(fast_cfg, tmp_path):
    spec = axsearch13.build_optimization_spec(fast_cfg)
    client = axsearch13.create_client(fast_cfg, spec)
    ledger = axsearch13.Ledger(tmp_path)
    candidates = axsearch13.generate_candidates(
        client, fast_cfg, ledger, count=1, trial_ordinal=0
    )
    record = candidates[0].as_record()
    assert record["candidate_id"] == "t0000"
    assert record["iteration"] == 0
    assert record["generation_method"] == "Sobol"
    assert "expected_acquisition_value" in record


def test_duplicate_candidate_is_flagged_against_the_ledger(fast_cfg, tmp_path):
    spec = axsearch13.build_optimization_spec(fast_cfg)
    client = axsearch13.create_client(fast_cfg, spec)
    ledger = axsearch13.Ledger(tmp_path)
    first = axsearch13.generate_candidates(
        client, fast_cfg, ledger, count=1, trial_ordinal=0
    )[0]
    ledger.write(
        {
            "trial_index": first.trial_index,
            "status": "completed",
            "parameters": dict(first.parameters),
        }
    )
    client.complete_trial(
        first.trial_index, raw_data={name: 0.5 for name in spec.reported_metrics}
    )
    # A second proposal at the same canonical design must be caught, whatever
    # Ax's own trial index for it happens to be.
    index = client.attach_trial(parameters=dict(first.parameters))
    candidate = axsearch13.Candidate(
        trial_index=index,
        parameters=dict(first.parameters),
        canonical=design13.canonicalize(first.parameters, fast_cfg),
        iteration=1,
        generation={},
        duplicate_of=None,
    )
    assert design13.is_duplicate(
        candidate.parameters, ledger.design_keys(fast_cfg), fast_cfg
    )


def test_expected_improvement_is_zero_without_headroom():
    import demo13

    assert demo13._expected_improvement(0.5, 0.0, 1.0) == 0.0
    assert demo13._expected_improvement(1.5, 0.0, 1.0) == pytest.approx(0.5)
    assert demo13._expected_improvement(1.0, 0.2, 1.0) > 0.0


def test_validation_and_robustness_cases_are_planned_from_the_yaml(cfg):
    import demo13

    design = {
        "parameter_asymmetry_s": 0.46,
        "parameter_central_barrier_thickness_nm": 1.5,
        "parameter_grading_thickness_nm": 1.0,
        "parameter_grading_profile": "linear",
    }
    checks = demo13.validation_cases(cfg, design)
    kinds = {kind for _case_id, kind, _config in checks}
    assert kinds == {
        "nominal", "local_refinement", "mesh_convergence",
        "state_count_convergence", "domain_padding",
    }
    meshes = {
        config["numerical"]["active_region_grid_spacing_nm"]
        for _case_id, kind, config in checks
        if kind == "mesh_convergence"
    }
    assert meshes == {0.05, 0.10}
    perturbations = demo13.robustness_cases(cfg, design)
    assert {parameter for _case, parameter, _delta, _config in perturbations} == {
        "narrow_well_nm", "wide_well_nm", "central_barrier_nm",
        "grading_thickness_nm", "aluminum_fraction",
    }


def test_demo13_reuses_demo11_and_demo12_rather_than_reimplementing_them():
    import demo13

    assert demo13.demo12.__name__ == "demo12_for_demo13"
    assert callable(demo13.demo11.analyse_case)
    assert callable(demo13.demo12.render_values)
    source = (DEMO / "demo13.py").read_text(encoding="utf-8")
    assert "analyse=demo11.analyse_case" in source
    assert "render_values=demo12.render_values" in source


def test_demo13_template_matches_demo12(cfg):
    ours = (DEMO / cfg["template"]).read_text(encoding="utf-8")
    theirs = (DEMO12 / "graded_acqw.in.j2").read_text(encoding="utf-8")
    # Only the header comment may differ; the deck itself must be identical.
    assert ours[ours.index("global{"):] == theirs[theirs.index("global{"):]


def test_registry_declares_demo13(cfg):
    registry = yaml.safe_load(
        (DEMO.parent / "demo_registry.yaml").read_text(encoding="utf-8")
    )
    record = registry["demos"][cfg["demo_id"]]
    assert record["status"] == "implemented_dry_run"
    assert record["licensed_validation"] is None
    assert record["pending_licensed_checks"]
    assert "12_graded_interface_coupled_quantum_well_optimization" in record["depends_on"]


def test_requirements_pin_the_tested_ax_version():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert f"ax-platform=={axsearch13.TESTED_AX_VERSION}" in text
