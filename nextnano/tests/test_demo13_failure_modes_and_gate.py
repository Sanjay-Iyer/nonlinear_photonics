"""Failure modes not already covered elsewhere, and the Stage 5 two-case gate.

This file deliberately does **not** duplicate coverage that exists. The
scenario-to-test mapping lives in
``guides/POTENTIAL_RESULTS_FAILURE_MODE_AUDIT.md``; what is here is the subset
that had no test before, plus the behaviour added with the gate:

* an avoided crossing, as distinct from a plain crossing;
* a high-objective but infeasible design, which must never rank as a winner;
* a campaign in which nothing is feasible;
* a winner sitting on a search bound, computed rather than asserted in prose;
* a run directory missing a file only the licensed solver writes;
* the two-case mesh gate, and the isolation that keeps Stage 5 out of v3.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "nextnano" / "demos" / "13_ax_bayesian_optimization_graded_acqw"
SHARED = DEMO.parent / "_shared"
DEMO11 = DEMO.parent / "11_paper_validation_interband_chi2_acqw"
DEMO12 = DEMO.parent / "12_graded_interface_coupled_quantum_well_optimization"
SCRIPTS = ROOT / "nextnano" / "scripts"
for path in (str(DEMO), str(SHARED), str(DEMO11), str(DEMO12), str(SCRIPTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

import anchor13  # noqa: E402
import bundle_raw_trials as brt  # noqa: E402
import demo13  # noqa: E402
import demo_workflow  # noqa: E402
import design13  # noqa: E402
import feasibility13  # noqa: E402
import tables13  # noqa: E402
import tracking13  # noqa: E402
import validation13  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


T0021 = {
    "asymmetry_s": 0.38756478988695775,
    "central_barrier_thickness_nm": 0.85,
    "grading_thickness_nm": 0.0,
    "grading_profile": "abrupt",
}


def _record(
    trial_index: int,
    *,
    objective: float,
    detuning: float,
    candidate: str | None = None,
    parameters=None,
    valid: bool = True,
    confidence: float = 0.99,
) -> dict:
    parameters = parameters or T0021
    return {
        "trial_index": trial_index,
        "iteration": trial_index,
        "candidate_id": candidate or f"t{trial_index:04d}",
        "status": "completed",
        "trial_valid": valid,
        "relative_chi2_at_target_wavelength_abs": objective,
        "signed_detuning_nm": detuning,
        "absolute_detuning_nm": abs(detuning),
        "peak_wavelength_nm": 1550.0 + detuning,
        "maximum_boundary_probability": 3.4e-5,
        "state_tracking_confidence": confidence,
        "orthonormality_error": 1e-14,
        "origin_independence_valid": 1,
        "required_states_valid": 1,
        "physical_qc_valid": 1,
        "feasible_under_ax_constraints": abs(detuning) <= 15.0,
        **{f"parameter_{name}": value for name, value in parameters.items()},
        "resolved_wide_well_nm": 6.937823949,
        "resolved_narrow_well_nm": 3.062176051,
        "resolved_central_barrier_nm": parameters["central_barrier_thickness_nm"],
    }


# ---------------------------------------------------------------------------
# avoided crossing (distinct from a plain crossing)
# ---------------------------------------------------------------------------

Z = np.linspace(-8.0, 8.0, 321)


def _normalise(values):
    return values / np.sqrt(np.trapezoid(values**2, Z))


def _states(index, envelopes, *, parameters, hole_energies, electron_energies=(2.90, 3.00)):
    return tracking13.TrialStates(
        trial_index=index,
        parameters=dict(parameters),
        z_nm=Z,
        electron_energies_eV=np.asarray(electron_energies, dtype=float),
        electron_envelopes=envelopes,
        heavy_hole_energies_eV=np.asarray(hole_energies, dtype=float),
        heavy_hole_envelopes=envelopes,
    )


def test_avoided_crossing_hybridises_without_swapping_labels(cfg):
    """At an avoided crossing the envelopes MIX and the energies repel.

    Distinct from a plain crossing, where the envelopes pass through unchanged
    and only the energy order swaps. Here neither state keeps a clean identity,
    so the tracker must report a reduced margin rather than a confident match.
    """

    left = _normalise(np.exp(-((Z + 2.2) / 0.9) ** 2))
    right = _normalise(np.exp(-((Z - 2.2) / 0.9) ** 2))
    # Far from the crossing: localized, well separated in energy.
    before = _states(
        0,
        np.column_stack([left, right]),
        parameters={**T0021, "central_barrier_thickness_nm": 1.8},
        hole_energies=(1.4600, 1.4200),
    )
    # At the anticrossing: symmetric/antisymmetric hybrids, energies repelled to
    # their minimum separation.
    bonding = _normalise(left + right)
    antibonding = _normalise(left - right)
    at_gap = _states(
        1,
        np.column_stack([bonding, antibonding]),
        parameters={**T0021, "central_barrier_thickness_nm": 1.75},
        hole_energies=(1.4420, 1.4380),
    )

    record = tracking13.track_against(at_gap, before, cfg)
    margins = [
        row["assignment_margin"]
        for row in record["rows"]
        if row.get("assignment_margin") is not None
    ]
    assert margins, "the anticrossing step produced no assignment margins"
    # A hybrid overlaps both predecessors about equally: the margin collapses.
    assert min(margins) < 0.5
    assert record["state_tracking_confidence"] is not None


def test_plain_crossing_keeps_a_clean_identity(cfg):
    """The contrast case: envelopes unchanged, energy order swapped."""

    left = _normalise(np.exp(-((Z + 2.2) / 0.9) ** 2))
    right = _normalise(np.exp(-((Z - 2.2) / 0.9) ** 2))
    before = _states(
        0, np.column_stack([left, right]), parameters=T0021, hole_energies=(1.4600, 1.4200)
    )
    after = _states(
        1,
        np.column_stack([right, left]),
        parameters={**T0021, "asymmetry_s": 0.40},
        hole_energies=(1.4600, 1.4200),
    )
    record = tracking13.track_against(after, before, cfg)
    hole_rows = [row for row in record["rows"] if row["band"] == "heavy_hole"]
    assert any(row["raw_index"] != row["tracked_label"] for row in hole_rows)
    # Unlike the avoided crossing, each state still has one clear partner.
    assert record["state_tracking_confidence"] > 0.9


# ---------------------------------------------------------------------------
# result patterns
# ---------------------------------------------------------------------------


def test_a_high_objective_infeasible_design_never_ranks_as_a_winner(cfg):
    """The largest chi(2) in the study is 46 nm off target and must not win."""

    import axsearch13

    spec = axsearch13.build_optimization_spec(cfg)
    records = [
        _record(1, objective=0.41, detuning=-13.0),
        # Bigger objective, badly detuned, and therefore not a valid trial.
        _record(2, objective=0.99, detuning=-46.0, valid=False),
    ]
    ranked = tables13.top_ranked_valid_designs(records, spec, limit=10)
    assert [row["trial_index"] for row in ranked] == [1]
    assert all(row["validated"] is False for row in ranked)


def test_a_campaign_with_no_feasible_trial_says_so_plainly(cfg):
    specs = feasibility13.build_constraints(cfg)
    records = [
        _record(1, objective=0.41, detuning=-40.0, valid=False),
        _record(2, objective=0.52, detuning=-33.0, valid=False),
    ]
    summary = feasibility13.feasibility_summary(records, specs)
    assert summary["any_feasible"] is False
    assert summary["feasible_count"] == 0
    assert "must not be read as progress" in summary["interpretation"]


@pytest.mark.parametrize(
    "barrier, expected",
    [
        (0.85, "lower"),
        (2.5, "upper"),
        (1.5, None),
    ],
)
def test_a_winner_on_a_search_bound_is_detected_not_asserted(cfg, barrier, expected):
    """v3's headline claim about t0021 has to be computed, not hardcoded.

    A sentence that says "sits on the barrier lower bound" keeps printing after
    the winner moves. This derives it from the live search space.
    """

    rows = design13.parameters_at_search_bounds(
        {**T0021, "central_barrier_thickness_nm": barrier}, cfg
    )
    sides = {
        row["parameter"]: row["bound"]
        for row in rows
        if row["parameter"] == "central_barrier_thickness_nm"
    }
    assert sides.get("central_barrier_thickness_nm") == expected


def test_the_v3_winner_reproduces_the_documented_bound(cfg):
    assert (
        design13.describe_search_bounds(T0021, cfg)
        == "the central_barrier_thickness_nm **lower bound** (0.85 nm)"
    )


# ---------------------------------------------------------------------------
# a run directory missing a licensed-only file
# ---------------------------------------------------------------------------


def _fake_run(root: Path, trial: str, *, omit=()) -> Path:
    run_dir = root / "runs" / trial
    (run_dir / "extracted").mkdir(parents=True, exist_ok=True)
    files = {
        "demo_resolved.yaml": (
            "scientific:\n"
            "  thick_well_nm: 6.937823949\n"
            "  thin_well_nm: 3.062176051\n"
            "  tunnel_barrier_nm: 0.85\n"
        ),
        "extracted/envelopes.csv": "z_nm,psi_e1,psi_hh1\n0,1,1\n1,0,0\n",
        "extracted/electron_states.csv": "state,energy_eV\n1,2.9\n",
        "extracted/heavy_hole_states.csv": "state,energy_eV\n1,1.45\n",
        "extracted/requested_composition_profile.csv": "z_nm,x\n0,0.55\n",
    }
    for relative, content in files.items():
        if relative in omit:
            continue
        (run_dir / relative).write_text(content, encoding="utf-8")
    return run_dir


def _fake_experiment(root: Path, *, barrier: float = 0.85) -> Path:
    state = root / "demo13_fake_experiment"
    state.mkdir(parents=True, exist_ok=True)
    (state / "trial_ledger.jsonl").write_text(
        json.dumps(
            {
                "trial_index": 21,
                "candidate_id": "t0021",
                "status": "completed",
                "resolved_wide_well_nm": 6.937823949,
                "resolved_narrow_well_nm": 3.062176051,
                "resolved_central_barrier_nm": barrier,
                "canonical_parameters": {"grading_thickness_nm": 0.0},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return state


def test_a_run_missing_a_solver_written_file_is_named_with_what_it_blocks(tmp_path):
    """A file the licensed solver path *does* write, absent from the bundle."""

    state = _fake_experiment(tmp_path)
    _fake_run(state, "t0021", omit=("extracted/heavy_hole_states.csv",))

    manifest = brt.build_bundle(
        state, tmp_path / "out", ["t0021"], ["extracted"], dry_run=True
    )
    missing = {item["what"]: item["reason"] for item in manifest["unavailable"]}
    assert "t0021/extracted/heavy_hole_states.csv" in missing
    assert "heavy-hole state energies" in missing["t0021/extracted/heavy_hole_states.csv"]

    required = {
        item["relative_path"]: item["present"]
        for item in manifest["trials"]["t0021"]["required_files"]
    }
    assert required["extracted/heavy_hole_states.csv"] is False
    assert required["extracted/envelopes.csv"] is True


def test_a_file_demo13_never_writes_is_not_reported_as_a_failure(tmp_path):
    """`requested_composition_profile.csv` is written only by Demo 12.

    Reporting it as a missing *required* file made every bundle on every
    machine -- including the licensed one -- print a line an operator would
    reasonably read as the solver having failed.
    """

    state = _fake_experiment(tmp_path)
    _fake_run(state, "t0021", omit=("extracted/requested_composition_profile.csv",))

    manifest = brt.build_bundle(
        state, tmp_path / "out", ["t0021"], ["extracted"], dry_run=True
    )
    missing = {item["what"] for item in manifest["unavailable"]}
    assert "t0021/extracted/requested_composition_profile.csv" not in missing

    entry = next(
        item
        for item in manifest["trials"]["t0021"]["required_files"]
        if item["relative_path"] == "extracted/requested_composition_profile.csv"
    )
    assert entry["expected"] is False
    assert entry["present"] is False
    assert "not written by Demo 13" in entry["blocks"]


def test_the_bundle_measures_rather_than_asserts_that_the_source_is_untouched(tmp_path):
    state = _fake_experiment(tmp_path)
    _fake_run(state, "t0021")
    manifest = brt.build_bundle(state, tmp_path / "out", ["t0021"], ["extracted"])
    assert manifest["source_modified"] is False


def test_a_run_directory_holding_another_design_is_refused(tmp_path):
    """A directory named t0021 is not proof it contains trial 21."""

    state = _fake_experiment(tmp_path, barrier=0.85)
    run_dir = _fake_run(state, "t0021")
    # Same name, different physics: the barrier was 1.80 nm, not 0.85 nm.
    (run_dir / "demo_resolved.yaml").write_text(
        "scientific:\n"
        "  thick_well_nm: 6.937823949\n"
        "  thin_well_nm: 3.062176051\n"
        "  tunnel_barrier_nm: 1.80\n",
        encoding="utf-8",
    )
    manifest = brt.build_bundle(
        state, tmp_path / "out", ["t0021"], ["extracted"], dry_run=True
    )
    verification = manifest["trials"]["t0021"]["source_verification"]
    assert verification["verified"] is False
    assert "tunnel_barrier_nm" in verification["reason"]


def test_a_matching_run_directory_verifies(tmp_path):
    state = _fake_experiment(tmp_path)
    _fake_run(state, "t0021")
    manifest = brt.build_bundle(
        state, tmp_path / "out", ["t0021"], ["extracted"], dry_run=True
    )
    verification = manifest["trials"]["t0021"]["source_verification"]
    assert verification["verified"] is True
    assert manifest["source_modified"] is False


# ---------------------------------------------------------------------------
# the Stage 5 two-case gate
# ---------------------------------------------------------------------------


def test_the_gate_plans_exactly_two_new_mesh_cases(cfg):
    plan = demo13.stage5_gate_plan(cfg, [_record(21, objective=0.41, detuning=-13.0)])
    assert plan["planned_case_count"] == 2
    assert plan["solver_calls_planned"] == 2
    meshes = sorted(
        case["active_region_grid_spacing_nm"] for case in plan["planned_cases"]
    )
    assert meshes == [0.025, 0.10]
    assert plan["gate_reference_mesh_nm"] == 0.05
    assert plan["gate_anchor_case"] == "t0021"
    assert plan["design_candidate_id"] == "t0021"


def test_the_gate_carries_the_t0021_geometry(cfg):
    plan = demo13.stage5_gate_plan(cfg, [_record(21, objective=0.41, detuning=-13.0)])
    for case in plan["planned_cases"]:
        assert case["resolved_central_barrier_nm"] == pytest.approx(0.85)
        assert case["resolved_wide_well_nm"] == pytest.approx(6.937823949, abs=1e-6)
        assert case["resolved_narrow_well_nm"] == pytest.approx(3.062176051, abs=1e-6)
        assert case["grading_profile"] == "abrupt"
        assert case["grading_selected_thickness_nm"] == pytest.approx(0.0)


def test_the_gate_never_repeats_the_reference_mesh(cfg):
    repeated = copy.deepcopy(cfg)
    repeated["validation_study"]["gate"]["mesh_convergence_nm"] = [0.05, 0.10]
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.settings(repeated)
    assert "already computed" in str(excinfo.value)


@pytest.mark.parametrize("meshes", [[0.025], [0.025, 0.05, 0.10], []])
def test_the_gate_must_be_exactly_two_cases(cfg, meshes):
    wrong = copy.deepcopy(cfg)
    wrong["validation_study"]["gate"]["mesh_convergence_nm"] = meshes
    with pytest.raises(validation13.Stage5Error):
        validation13.settings(wrong)


def test_the_gate_anchor_must_be_the_design_it_recomputes(cfg):
    """Anchoring on a different trial would mislabel one design as another.

    The gate reads the anchor's wavefunctions from the design's own completed
    trial directory. If the two names could differ, t0021's states would be
    assigned t0005's identities and reported as a confident match.
    """

    crossed = copy.deepcopy(cfg)
    crossed["validation_study"]["gate"]["anchor_case"] = "t0005"
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.settings(crossed)
    assert "must equal" in str(excinfo.value)


def test_the_gate_refuses_a_design_that_was_never_evaluated(cfg):
    with pytest.raises(validation13.Stage5Error) as excinfo:
        demo13.stage5_gate_plan(cfg, [_record(5, objective=0.2, detuning=-10.0)])
    assert "not a completed trial" in str(excinfo.value)


def test_the_full_campaign_is_blocked_until_the_gate_passes(cfg, tmp_path):
    allowed, reason = validation13.full_campaign_allowed(cfg, tmp_path)
    assert allowed is False
    assert "gate has not passed" in reason

    (tmp_path / "stage5_gate_result.json").write_text(
        json.dumps({"gate_passed": True}), encoding="utf-8"
    )
    allowed, reason = validation13.full_campaign_allowed(cfg, tmp_path)
    assert allowed is True


@pytest.mark.parametrize(
    "payload",
    [
        {"gate_passed": False},
        {"gate_passed": None},
        {},
        # Truthy but not `true`. `bool(...)` would have unblocked ~69 licensed
        # cases on any of these.
        {"gate_passed": "yes"},
        {"gate_passed": "false"},
        {"gate_passed": 1},
        {"gate_passed": "2026-08-02"},
    ],
)
def test_only_an_exact_true_unblocks_the_campaign(cfg, tmp_path, payload):
    (tmp_path / "stage5_gate_result.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    allowed, _ = validation13.full_campaign_allowed(cfg, tmp_path)
    assert allowed is False


def test_a_malformed_gate_result_does_not_unblock_the_campaign(cfg, tmp_path):
    (tmp_path / "stage5_gate_result.json").write_text("not json", encoding="utf-8")
    allowed, _ = validation13.full_campaign_allowed(cfg, tmp_path)
    assert allowed is False


@pytest.mark.parametrize(
    "name",
    [
        "DEMO13_AX_EXPERIMENT_V3",
        "Demo13_Ax_Experiment_V3",
        "demo13_AX_experiment_v2",
    ],
)
def test_a_differently_cased_protected_name_is_refused(cfg, tmp_path, name):
    """On Windows these name the same directory as the campaign.

    The content check only fires once the campaign directory exists; the name
    check must not depend on that, so it compares case-insensitively.
    """

    with pytest.raises(validation13.Stage5Error):
        validation13.assert_isolated(tmp_path / name, cfg, tmp_path)


def test_reading_a_ledger_for_a_check_creates_nothing(tmp_path):
    """`--stage5-check` prints "Nothing was written" and must mean it.

    `Ledger.__post_init__` creates `trials/`, so constructing one without
    `read_only=True` mutated the protected campaign directory.
    """

    import axsearch13

    experiment = tmp_path / "exp"
    experiment.mkdir()
    (experiment / "trial_ledger.jsonl").write_text("", encoding="utf-8")
    before = {path.name for path in experiment.iterdir()}

    axsearch13.Ledger(experiment, read_only=True)
    assert {path.name for path in experiment.iterdir()} == before

    axsearch13.Ledger(experiment)
    assert "trials" in {path.name for path in experiment.iterdir()}, (
        "the writable Ledger should create trials/, or this test proves nothing"
    )


def test_an_unevaluable_gate_is_none_not_a_pass():
    assert demo13._gate_verdict({}, [], None) is None
    assert demo13._gate_verdict({}, [], "anchor output missing") is None


# --- the verdict must actually establish what the gate claims ---------------


def _anchor_records(n=2, *, labels_match=True, confidence=0.99, margin=0.8):
    return {
        "records": [
            {
                "trial_index": -(i + 1),
                "labels_match_historical": labels_match,
                "state_tracking_confidence": confidence,
                "assignment_margin": margin,
            }
            for i in range(n)
        ],
        "ambiguous_trials": [],
    }


def _comparison(field="relative_chi2_at_target_wavelength_abs", change=0.0):
    return [
        {"case_id": "gate_mesh_0.025nm", "field": field,
         "relative_change": change, "status": "completed"},
        {"case_id": "gate_mesh_0.1nm", "field": field,
         "relative_change": change, "status": "completed"},
    ]


def test_a_clean_gate_passes(cfg):
    assert demo13._gate_verdict(
        _anchor_records(), _comparison(), None, cfg=cfg, expected_cases=2
    ) is True


def test_a_large_chi2_shift_fails_the_gate(cfg):
    """A 60 % move in the objective used to pass."""

    assert demo13._gate_verdict(
        _anchor_records(), _comparison(change=0.60), None, cfg=cfg, expected_cases=2
    ) is False


def test_reordered_state_labels_fail_the_gate(cfg):
    """`labels_match_historical` was never populated on the gate path."""

    assert demo13._gate_verdict(
        _anchor_records(labels_match=False), _comparison(), None,
        cfg=cfg, expected_cases=2,
    ) is False


def test_unpopulated_label_match_is_not_a_pass(cfg):
    assert demo13._gate_verdict(
        _anchor_records(labels_match=None), _comparison(), None,
        cfg=cfg, expected_cases=2,
    ) is False


def test_low_confidence_fails_the_gate(cfg):
    assert demo13._gate_verdict(
        _anchor_records(confidence=0.5), _comparison(), None,
        cfg=cfg, expected_cases=2,
    ) is False


def test_a_small_assignment_margin_fails_the_gate(cfg):
    assert demo13._gate_verdict(
        _anchor_records(margin=0.01), _comparison(), None,
        cfg=cfg, expected_cases=2,
    ) is False


def test_a_gate_that_lost_a_case_is_not_established(cfg):
    """One anchored case out of two is not a two-case gate."""

    assert demo13._gate_verdict(
        _anchor_records(n=1), _comparison(), None, cfg=cfg, expected_cases=2
    ) is None


def test_the_gate_tolerances_are_configurable_and_defaulted(cfg):
    tolerances = validation13.gate_tolerances(cfg)
    assert tolerances["relative_chi2_at_target_wavelength_abs"] == pytest.approx(0.10)
    override = copy.deepcopy(cfg)
    override["validation_study"]["gate"]["tolerances"] = {
        "relative_chi2_at_target_wavelength_abs": 0.99
    }
    assert validation13.gate_tolerances(override)[
        "relative_chi2_at_target_wavelength_abs"
    ] == pytest.approx(0.99)


def test_anchor_results_are_merged_back_onto_the_gate_rows():
    """Three compared fields were structurally `None` on the gate side."""

    rows = [{"trial_index": -1, "case_id": "gate_mesh_0.025nm"}]
    tracking = {
        "records": [
            {
                "trial_index": -1,
                "tracked_labels": {"electron": [1, 2], "heavy_hole": [1, 2]},
                "state_tracking_confidence": 0.97,
                "assignment_margin": 0.8,
                "ambiguous": False,
            }
        ]
    }
    design = {"tracked_state_labels": {"electron": [1, 2], "heavy_hole": [1, 2]}}
    demo13._merge_anchor_results_into_rows(tracking, rows, design)

    assert rows[0]["state_tracking_confidence"] == pytest.approx(0.97)
    assert rows[0]["tracked_state_labels"] == design["tracked_state_labels"]
    assert rows[0]["state_tracking_ambiguous"] is False
    assert rows[0]["labels_match_historical"] is True
    assert tracking["records"][0]["labels_match_historical"] is True


def test_merged_labels_detect_a_reordering():
    rows = [{"trial_index": -1}]
    tracking = {"records": [{"trial_index": -1,
                             "tracked_labels": {"electron": [2, 1]}}]}
    demo13._merge_anchor_results_into_rows(
        tracking, rows, {"tracked_state_labels": {"electron": [1, 2]}}
    )
    assert rows[0]["labels_match_historical"] is False


# --- containment depth and the reference-mesh check -------------------------


def test_a_destination_two_levels_above_a_campaign_is_refused(cfg, tmp_path):
    """The containment scan was one level deep."""

    deep = tmp_path / "13_ax_bayesian_optimization_graded_acqw" / "demo13_ax_experiment_v3"
    deep.mkdir(parents=True)
    (deep / "trial_ledger.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.assert_isolated(tmp_path, cfg, tmp_path)
    assert "contains the protected experiment" in str(excinfo.value)


def test_the_reference_mesh_must_be_the_campaign_mesh(cfg):
    wrong = copy.deepcopy(cfg)
    wrong["validation_study"]["gate"]["reference_mesh_nm"] = 0.2
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.settings(wrong)
    assert "is not numerical.active_region_grid_spacing_nm" in str(excinfo.value)


def test_the_shipped_reference_mesh_matches_the_campaign(cfg):
    resolved = validation13.settings(cfg)
    assert resolved.gate.reference_mesh_nm == pytest.approx(
        cfg["numerical"]["active_region_grid_spacing_nm"]
    )


# --- the two-case guarantee end to end --------------------------------------


def _stage5_records():
    base = {
        "status": "completed", "trial_valid": True,
        "signed_detuning_nm": -13.0, "absolute_detuning_nm": 13.0,
        "peak_wavelength_nm": 1537.0, "maximum_boundary_probability": 3.4e-5,
        "state_tracking_confidence": 0.99, "orthonormality_error": 1e-14,
        "physical_qc_valid": 1, "origin_independence_valid": 1,
        "required_states_valid": 1,
        "tracked_state_labels": {"electron": [1, 2], "heavy_hole": [1, 2]},
        "parameter_asymmetry_s": 0.38756478988695775,
        "parameter_central_barrier_thickness_nm": 0.85,
        "parameter_grading_thickness_nm": 0.0,
        "parameter_grading_profile": "abrupt",
    }
    return [
        {**base, "trial_index": i, "iteration": i, "candidate_id": f"t{i:04d}",
         "relative_chi2_at_target_wavelength_abs": objective}
        for i, objective in ((21, 0.41), (22, 0.39), (17, 0.30))
    ]


@pytest.mark.parametrize("prior_gate_result", [None, {"gate_passed": True}])
def test_a_gate_run_never_falls_through_into_the_full_campaign(
    cfg, tmp_path, monkeypatch, prior_gate_result
):
    """The blocker: a passing gate released ~60 more paid cases in one command.

    `run_stage5_gate` writes `stage5_gate_result.json`, and the same invocation
    then re-read it and continued into the campaign. The gate result must be
    reviewed in a later process, so the gate branch now returns unconditionally.
    """

    import types
    import axsearch13

    state = demo13.stage5_state_dir(cfg, tmp_path)
    state.mkdir(parents=True)
    if prior_gate_result is not None:
        (state / "stage5_gate_result.json").write_text(
            json.dumps(prior_gate_result), encoding="utf-8"
        )
    experiment_dir = demo13.experiment_state_dir(cfg, tmp_path)
    experiment_dir.mkdir(parents=True)

    calls: list[str] = []

    def fake_side_case(context, state_dir, case_id, resolved, *, extra):
        calls.append(case_id)
        return {"case_id": case_id, "status": "completed",
                "output_directory_path": str(state_dir / case_id), **dict(extra)}

    monkeypatch.setattr(demo13, "_run_side_case", fake_side_case)

    machine = types.SimpleNamespace(results_root=tmp_path, run_solver=False)
    context = types.SimpleNamespace(cfg=cfg, machine=machine, demo_dir=DEMO,
                                    dependency_report={}, parent=tmp_path)
    experiment = types.SimpleNamespace(
        state_dir=experiment_dir, spec=axsearch13.build_optimization_spec(cfg)
    )

    result = demo13.run_validation_study(context, experiment, _stage5_records())

    assert len(calls) == 2, f"the gate spent {len(calls)} paid cases, not 2: {calls}"
    assert sorted(calls) == ["gate_mesh_0.025nm", "gate_mesh_0.1nm"]
    assert result["full_campaign_generated"] is False
    assert result["robustness_rows"] == []
    assert "separately authorized" in result["full_campaign_blocked_reason"]


# ---------------------------------------------------------------------------
# Stage 5 isolation
# ---------------------------------------------------------------------------


def test_an_isolated_destination_is_accepted(cfg, tmp_path):
    target = tmp_path / "demo13_stage5_v3_validation"
    assert validation13.assert_isolated(target, cfg, tmp_path) == target.resolve()


@pytest.mark.parametrize(
    "name", ["demo13_ax_experiment_v3", "demo13_ax_experiment_v2", "demo13_ax_experiment"]
)
def test_protected_experiment_names_are_refused(cfg, tmp_path, name):
    with pytest.raises(validation13.Stage5Error):
        validation13.assert_isolated(tmp_path / name, cfg, tmp_path)


def test_a_directory_holding_a_ledger_is_refused_whatever_it_is_called(cfg, tmp_path):
    renamed = tmp_path / "totally_innocent_directory"
    renamed.mkdir()
    (renamed / "trial_ledger.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.assert_isolated(renamed, cfg, tmp_path)
    assert "checkpoint or ledger" in str(excinfo.value)


def test_a_directory_holding_a_checkpoint_is_refused(cfg, tmp_path):
    renamed = tmp_path / "some_other_directory"
    renamed.mkdir()
    (renamed / "ax_experiment_snapshot.json").write_text("{}", encoding="utf-8")
    with pytest.raises(validation13.Stage5Error):
        validation13.assert_isolated(renamed, cfg, tmp_path)


def test_a_destination_inside_a_protected_experiment_is_refused(cfg, tmp_path):
    protected = tmp_path / "demo13_ax_experiment_v3"
    inside = protected / "stage5"
    inside.mkdir(parents=True)
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.assert_isolated(inside, cfg, tmp_path)
    assert "lies inside the protected experiment" in str(excinfo.value)


def test_a_destination_containing_a_protected_experiment_is_refused(cfg, tmp_path):
    umbrella = tmp_path / "stage5_umbrella"
    (umbrella / "demo13_ax_experiment_v3").mkdir(parents=True)
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.assert_isolated(umbrella, cfg, tmp_path)
    assert "contains the protected experiment" in str(excinfo.value)


def test_a_dotdot_alias_of_a_protected_directory_is_refused(cfg, tmp_path):
    (tmp_path / "demo13_ax_experiment_v3").mkdir()
    (tmp_path / "sibling").mkdir()
    alias = tmp_path / "sibling" / ".." / "demo13_ax_experiment_v3"
    with pytest.raises(validation13.Stage5Error):
        validation13.assert_isolated(alias, cfg, tmp_path)


def test_a_symlink_to_a_protected_directory_is_refused(cfg, tmp_path):
    protected = tmp_path / "demo13_ax_experiment_v3"
    protected.mkdir()
    (protected / "trial_ledger.jsonl").write_text("{}\n", encoding="utf-8")
    link = tmp_path / "innocuous_link"
    try:
        link.symlink_to(protected, target_is_directory=True)
    except (OSError, NotImplementedError):  # pragma: no cover - needs privilege
        pytest.skip("this platform/account cannot create directory symlinks")
    with pytest.raises(validation13.Stage5Error):
        validation13.assert_isolated(link, cfg, tmp_path)


def test_the_shipped_configuration_resolves_to_an_isolated_directory(cfg, tmp_path):
    state_dir = demo13.stage5_state_dir(cfg, tmp_path)
    assert state_dir.name == "demo13_stage5_v3_validation"
    assert validation13.assert_isolated(state_dir, cfg, tmp_path)


def test_stage5_is_a_sibling_of_the_experiment_not_a_level_above(cfg, tmp_path):
    """Stage 5 and the campaign must live under the same demo results folder.

    `stage5_state_dir` omitted the demo-id segment that `experiment_state_dir`
    includes, so Stage 5 resolved a level up, beside other demos' results -- and
    the "is this the experiment directory?" comparison was between two
    differently-built paths, so it could never fire.
    """

    stage5 = demo13.stage5_state_dir(cfg, tmp_path)
    experiment = demo13.experiment_state_dir(cfg, tmp_path)
    assert stage5.parent == experiment.parent
    assert stage5.parent.name == cfg["demo_id"]
    assert stage5 != experiment


def test_the_experiment_directory_itself_is_refused_on_the_real_path(cfg, tmp_path):
    """The comparison that used to pass vacuously."""

    experiment = demo13.experiment_state_dir(cfg, tmp_path)
    experiment.mkdir(parents=True)
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.assert_isolated(
            experiment, cfg, tmp_path, experiment_dir=experiment
        )
    assert "optimization experiment" in str(excinfo.value)


def test_a_matching_stage5_directory_may_be_resumed(cfg, tmp_path):
    (tmp_path / "stage5_schema.json").write_text(
        json.dumps(validation13.stage5_schema(cfg)), encoding="utf-8"
    )
    validation13.assert_resume_schema_matches(tmp_path, cfg)


def test_a_stage5_directory_from_another_configuration_is_refused(cfg, tmp_path):
    stale = dict(validation13.stage5_schema(cfg))
    stale["gate_mesh_convergence_nm"] = [0.05, 0.20]
    (tmp_path / "stage5_schema.json").write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(validation13.Stage5Error) as excinfo:
        validation13.assert_resume_schema_matches(tmp_path, cfg)
    assert "gate_mesh_convergence_nm" in str(excinfo.value)


def test_an_absent_stage5_schema_is_not_an_error(cfg, tmp_path):
    validation13.assert_resume_schema_matches(tmp_path, cfg)


# ---------------------------------------------------------------------------
# the work-laptop handoff
# ---------------------------------------------------------------------------

HANDOFF = DEMO / "guides" / "WORK_LAPTOP_FINAL_HANDOFF.md"


@pytest.fixture(scope="module")
def handoff_text():
    return HANDOFF.read_text(encoding="utf-8")


def test_the_handoff_exists_and_labels_every_command(handoff_text):
    for label in (
        "SAFE — no solver",
        "PAID SOLVER — two-case Stage 5 gate",
        "DO NOT RUN UNTIL GATE REVIEW",
    ):
        assert label in handoff_text, f"missing label: {label}"


def test_the_handoff_never_offers_a_full_campaign_launch(handoff_text):
    """The one command that must never appear in a handoff document.

    The gate is two licensed runs; the campaign is roughly sixty-nine. Exactly
    one `validate_top_designs` switch is permitted -- the gate launch in the
    PAID SOLVER step and its matching revert -- and nothing that reads as
    turning the whole campaign loose.
    """

    for phrase in (
        "full Stage 5 campaign",
        "roughly **69 licensed cases**",
    ):
        assert phrase in handoff_text

    assert "DO NOT RUN UNTIL GATE REVIEW" in handoff_text
    # `validate_top_designs` may appear only in the guarded gate launch and the
    # revert that immediately follows it.
    occurrences = handoff_text.count("validate_top_designs")
    assert occurrences == 2, (
        f"expected the gate launch and its revert, found {occurrences} references"
    )


def test_the_handoff_requires_the_raw_bundle_before_the_gate(handoff_text):
    """The gate anchors on completed output it does not recompute."""

    bundle = handoff_text.index("bundle_raw_trials.py --experiment demo13_ax_experiment_v3\n")
    launch = handoff_text.index("PAID SOLVER — two-case Stage 5 gate\n\nOnly after")
    assert bundle < launch, "raw collection must precede the paid gate"
    assert "prerequisite for the gate" in handoff_text


def test_the_handoff_checks_protected_hashes_before_and_after(handoff_text):
    assert handoff_text.count("hashlib.sha256") >= 1
    assert "must be identical" in handoff_text
    assert "must still match" in handoff_text


def test_the_handoff_names_the_isolated_stage5_directory(cfg, handoff_text):
    assert validation13.settings(cfg).output_state_dir in handoff_text
    assert "demo13_ax_experiment_v3" in handoff_text


def test_the_handoff_states_a_passing_gate_is_not_validation(handoff_text):
    assert "A passing gate does not validate t0021" in handoff_text
    assert "lower bound" in handoff_text


def test_the_failure_mode_audit_names_only_tests_that_exist(cfg):
    """Every test the coverage matrix cites must actually be collectable."""

    import re
    import subprocess

    audit = (DEMO / "guides" / "POTENTIAL_RESULTS_FAILURE_MODE_AUDIT.md").read_text(
        encoding="utf-8"
    )
    cited = set(re.findall(r"`(test_[a-z0-9_]+)`", audit))
    assert len(cited) >= 25, f"suspiciously few cited tests: {len(cited)}"

    collected = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "nextnano" / "tests"),
         "--collect-only", "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(ROOT),
    ).stdout
    existing = set(re.findall(r"::(test_[a-z0-9_]+)", collected))
    missing = sorted(cited - existing)
    assert not missing, f"the coverage matrix cites tests that do not exist: {missing}"
