"""State-tracking energy provenance (Phase 2A) and the fixed anchor (Phase 2B).

Two defects motivate this file.

**Fabricated hole energies.** ``tracking13.load_trial_states`` used to hand the
heavy-hole branch ``np.arange(n)`` and describe it as contributing "no
information". It does not: ``tracking11._energy_penalty`` normalizes the energy
gap by the spread of the energies it is given, so an index sequence on *both*
sides produces a penalty matrix that is zero on the diagonal and grows with
``|i-j|`` -- an identity-preferring prior that suppresses exactly the state
reordering the tracker exists to detect.

**An anchor that was never read.** ``state_tracking.anchor_case`` sat in
``demo.yaml`` unread, so the order-independent Stage 5 check the plans describe
could not run at all.
"""

from __future__ import annotations

import copy
import csv
from pathlib import Path
import random
import sys
import types

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "nextnano" / "demos" / "13_ax_bayesian_optimization_graded_acqw"
SHARED = DEMO.parent / "_shared"
DEMO11 = DEMO.parent / "11_paper_validation_interband_chi2_acqw"
DEMO12 = DEMO.parent / "12_graded_interface_coupled_quantum_well_optimization"
for path in (str(DEMO), str(SHARED), str(DEMO11), str(DEMO12)):
    if path not in sys.path:
        sys.path.insert(0, path)

import anchor13  # noqa: E402
import axsearch13  # noqa: E402
import demo13  # noqa: E402
import demo_workflow  # noqa: E402
import design13  # noqa: E402
import metrics13  # noqa: E402
import tables13  # noqa: E402
import tracking11  # noqa: E402
import tracking13  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="module")
def cfg():
    return demo_workflow.load_demo_config(DEMO)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

Z = np.linspace(-8.0, 8.0, 321)


def _normalise(values: np.ndarray) -> np.ndarray:
    return values / np.sqrt(np.trapezoid(values**2, Z))


def _left_right() -> tuple[np.ndarray, np.ndarray]:
    """Two well-separated, normalized envelopes."""

    return (
        _normalise(np.exp(-((Z + 2.2) / 0.9) ** 2)),
        _normalise(np.exp(-((Z - 2.2) / 0.9) ** 2)),
    )


DESIGN = {
    "asymmetry_s": 0.44,
    "central_barrier_thickness_nm": 1.8,
    "grading_thickness_nm": 1.0,
    "grading_profile": "linear",
}


def _states(
    trial_index: int,
    envelopes: np.ndarray,
    *,
    parameters=None,
    electron_energies=(2.90, 3.00),
    hole_energies=(1.45, 1.42),
    z=None,
    synthetic_bands=(),
) -> tracking13.TrialStates:
    return tracking13.TrialStates(
        trial_index=trial_index,
        parameters=dict(parameters or DESIGN),
        z_nm=Z if z is None else z,
        electron_energies_eV=np.asarray(electron_energies, dtype=float),
        electron_envelopes=envelopes,
        heavy_hole_energies_eV=np.asarray(hole_energies, dtype=float),
        heavy_hole_envelopes=envelopes,
        synthetic_energy_bands=tuple(synthetic_bands),
    )


def _write_envelopes(directory: Path, n_electron: int = 2, n_hole: int = 2) -> None:
    left, right = _left_right()
    columns = [Z] + [left, right][:n_electron] + [left, right][:n_hole]
    header = (
        "z_nm,"
        + ",".join(f"psi_e{i + 1}" for i in range(n_electron))
        + ","
        + ",".join(f"psi_hh{i + 1}" for i in range(n_hole))
    )
    directory.mkdir(parents=True, exist_ok=True)
    np.savetxt(
        directory / "envelopes.csv",
        np.column_stack(columns),
        delimiter=",",
        header=header,
        comments="",
    )


def _write_state_table(path: Path, energies, column: str = "energy_eV") -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["state", column])
        for index, energy in enumerate(energies, start=1):
            writer.writerow([index, energy])


# ---------------------------------------------------------------------------
# Phase 2A -- the np.arange substitution is not neutral
# ---------------------------------------------------------------------------


def test_index_energies_bias_the_assignment_toward_the_identity():
    """The regression that justifies refusing the fallback at all.

    With an index sequence on both sides the penalty matrix is zero on the
    diagonal and grows away from it, so a genuine adjacent swap must overcome a
    fixed handicap before the tracker will report it.
    """

    weight = 0.05
    indices = np.arange(4, dtype=float)
    penalty = tracking11._energy_penalty(indices, indices, weight)

    assert np.allclose(np.diag(penalty), 0.0)
    adjacent = float(penalty[0, 1])
    assert adjacent > 0.0
    assert adjacent == pytest.approx(weight / 3.0)
    # Strictly increasing away from the diagonal: an identity-preferring prior.
    assert penalty[0, 3] > penalty[0, 2] > penalty[0, 1] > penalty[0, 0]

    # Real, near-degenerate hole energies produce a far smaller handicap, which
    # is the physically correct answer: two states 7 meV apart are nearly
    # interchangeable on energy grounds and overlap should decide alone.
    real = np.asarray([1.448177, 1.418728, 1.411613, 1.357723])
    real_penalty = tracking11._energy_penalty(real, real, weight)
    assert float(real_penalty[1, 2]) < adjacent


def test_missing_hole_energies_raise_instead_of_being_invented(tmp_path):
    _write_envelopes(tmp_path)
    _write_state_table(tmp_path / "electron_states.csv", [2.90, 3.00])

    with pytest.raises(tracking13.StateEnergyError) as excinfo:
        tracking13.load_trial_states(0, DESIGN, tmp_path)
    message = str(excinfo.value)
    assert "heavy_hole" in message
    assert "index sequence" in message


def test_missing_electron_energies_also_raise(tmp_path):
    _write_envelopes(tmp_path)
    _write_state_table(tmp_path / "heavy_hole_states.csv", [1.45, 1.42])

    with pytest.raises(tracking13.StateEnergyError) as excinfo:
        tracking13.load_trial_states(0, DESIGN, tmp_path)
    assert "electron" in str(excinfo.value)


def test_observables_supply_real_energies_for_both_bands(tmp_path):
    _write_envelopes(tmp_path)
    states = tracking13.load_trial_states(
        7,
        DESIGN,
        tmp_path,
        observables={
            "electron_energies_eV": [2.935729, 3.030838],
            "heavy_hole_energies_eV": [1.448177, 1.418728],
        },
    )
    assert states is not None
    assert states.synthetic_energy_bands == ()
    assert states.energy_provenance_by_band == {
        "electron": "solver", "heavy_hole": "solver"
    }
    assert states.electron_energies_eV[0] == pytest.approx(2.935729)
    # Hole energies DESCEND with index and must not be re-sorted: the order is
    # what pairs an energy with its envelope column.
    assert states.heavy_hole_energies_eV[0] > states.heavy_hole_energies_eV[1]


def test_state_tables_on_disk_are_the_fallback_not_an_index(tmp_path):
    _write_envelopes(tmp_path)
    _write_state_table(tmp_path / "electron_states.csv", [2.90, 3.00])
    _write_state_table(tmp_path / "heavy_hole_states.csv", [1.45, 1.42])

    states = tracking13.load_trial_states(0, DESIGN, tmp_path)
    assert states is not None
    assert states.synthetic_energy_bands == ()
    assert states.energy_provenance_by_band == {
        "electron": "parsed historical output",
        "heavy_hole": "parsed historical output",
    }
    assert states.heavy_hole_energies_eV.tolist() == [1.45, 1.42]


def test_malformed_energy_data_is_rejected_not_coerced(tmp_path):
    _write_envelopes(tmp_path)
    _write_state_table(tmp_path / "electron_states.csv", [2.90, 3.00])
    _write_state_table(tmp_path / "heavy_hole_states.csv", ["not-a-number", 1.42])

    with pytest.raises(tracking13.StateEnergyError):
        tracking13.load_trial_states(0, DESIGN, tmp_path)


def test_non_finite_energies_are_rejected(tmp_path):
    _write_envelopes(tmp_path)
    with pytest.raises(tracking13.StateEnergyError):
        tracking13.load_trial_states(
            0,
            DESIGN,
            tmp_path,
            observables={
                "electron_energies_eV": [2.90, 3.00],
                "heavy_hole_energies_eV": [1.45, float("nan")],
            },
        )


def test_short_energy_band_is_rejected_rather_than_padded(tmp_path):
    _write_envelopes(tmp_path, n_electron=2, n_hole=2)
    with pytest.raises(tracking13.StateEnergyError):
        tracking13.load_trial_states(
            0,
            DESIGN,
            tmp_path,
            observables={
                "electron_energies_eV": [2.90, 3.00],
                "heavy_hole_energies_eV": [1.45],
            },
        )


def test_synthetic_fallback_is_opt_in_and_labelled(tmp_path):
    _write_envelopes(tmp_path)
    states = tracking13.load_trial_states(
        0, DESIGN, tmp_path, allow_synthetic_energies=True
    )
    assert states is not None
    assert set(states.synthetic_energy_bands) == {"electron", "heavy_hole"}
    assert set(states.energy_provenance_by_band.values()) == {"synthetic test"}


def test_missing_energy_failure_is_persistent_and_scoped_to_one_trial(cfg, tmp_path):
    """The campaign can continue, while the failed record retains the cause."""

    _write_envelopes(tmp_path / "extracted")
    _write_state_table(tmp_path / "extracted" / "electron_states.csv", [2.90, 3.00])
    result = types.SimpleNamespace(
        solver_success=True,
        observables={"electron_energies_eV": [2.90, 3.00]},
        run_dir=tmp_path,
        warnings=[],
    )
    tracking, states = demo13._tracking_for(result, 21, DESIGN, cfg, [])
    assert states is None
    assert tracking["energy_provenance"] == "unavailable"
    assert "heavy_hole" in tracking["state_tracking_error"]

    record = metrics13.build_record(
        parameters=DESIGN,
        cfg=cfg,
        observables={},
        validation={},
        status="completed",
        tracking=tracking,
    )
    assert record["state_tracking_energy_provenance"] == "unavailable"
    assert "heavy_hole" in record["state_tracking_error"]

    # A later, complete candidate is still independently trackable.
    complete = _states(22, np.column_stack(_left_right()))
    following = tracking13.track_against(complete, None, cfg)
    assert following["state_tracking_confidence"] == 1.0
    assert following["energy_provenance"] == "solver"


def test_synthetic_label_propagates_into_the_tracking_record(cfg):
    left, right = _left_right()
    envelopes = np.column_stack([left, right])
    first = _states(0, envelopes, synthetic_bands=("heavy_hole",))
    second = _states(1, envelopes, parameters={**DESIGN, "asymmetry_s": 0.45})

    record = tracking13.track_against(second, first, cfg)
    assert record["synthetic_energy_bands"] == ["heavy_hole"]
    assert record["energy_provenance"] == tracking13.SYNTHETIC_ENERGY_LABEL

    summary = tracking13.track_sequence([first, second], cfg)
    assert summary["energy_provenance"] == tracking13.SYNTHETIC_ENERGY_LABEL


def test_all_solver_energies_report_solver_provenance(cfg):
    left, right = _left_right()
    envelopes = np.column_stack([left, right])
    summary = tracking13.track_sequence(
        [
            _states(0, envelopes),
            _states(1, envelopes, parameters={**DESIGN, "asymmetry_s": 0.45}),
        ],
        cfg,
    )
    assert summary["synthetic_energy_bands"] == []
    assert summary["energy_provenance"] == "solver"


def test_no_envelopes_still_returns_none_not_an_error(tmp_path):
    """"No wavefunctions at all" stays distinct from "I refuse to invent energies"."""

    assert tracking13.load_trial_states(0, DESIGN, tmp_path) is None


def test_real_hole_energies_let_a_hole_swap_be_detected(cfg):
    """The physics the fabricated energies were suppressing.

    Two hole states exchange energy order between designs while keeping their
    envelopes. With real energies the tracker follows the envelope and reports
    the reordering; the assignment must not simply be the identity.
    """

    left, right = _left_right()
    first = _states(
        0,
        np.column_stack([left, right]),
        hole_energies=(1.4500, 1.4430),
    )
    second = _states(
        1,
        np.column_stack([right, left]),
        parameters={**DESIGN, "asymmetry_s": 0.45},
        hole_energies=(1.4480, 1.4455),
    )
    record = tracking13.track_against(second, first, cfg)
    hole_rows = [row for row in record["rows"] if row["band"] == "heavy_hole"]
    assert hole_rows
    assert any(row["raw_index"] != row["tracked_label"] for row in hole_rows)
    assert record["label_reordering_detected"] is True


def test_near_degenerate_hole_states_are_tracked_by_overlap(cfg):
    """4 meV apart -- inside the 5 meV broadening -- must still assign by overlap."""

    left, right = _left_right()
    first = _states(0, np.column_stack([left, right]), hole_energies=(1.4500, 1.4460))
    second = _states(
        1,
        np.column_stack([left, right]),
        parameters={**DESIGN, "asymmetry_s": 0.45},
        hole_energies=(1.4490, 1.4450),
    )
    record = tracking13.track_against(second, first, cfg)
    assert record["state_tracking_confidence"] > 0.9
    assert record["ambiguous"] is False


def test_sign_reversal_does_not_change_the_assignment(cfg):
    left, right = _left_right()
    first = _states(0, np.column_stack([left, right]))
    flipped = _states(
        1,
        np.column_stack([-left, -right]),
        parameters={**DESIGN, "asymmetry_s": 0.45},
    )
    record = tracking13.track_against(flipped, first, cfg)
    assert record["tracked_labels"]["electron"] == [1, 2]
    assert any(row["sign_flip_applied"] for row in record["rows"])


# ---------------------------------------------------------------------------
# Phase 2B -- the fixed anchor
# ---------------------------------------------------------------------------


def test_anchor_case_is_read_from_the_configuration(cfg):
    assert anchor13.anchor_case_name(cfg) == "reference_abrupt"
    spec = anchor13.resolve_anchor_spec(cfg)
    assert spec.name == "reference_abrupt"
    assert spec.source == "reference_design"
    assert spec.design_hash
    assert spec.parameters["grading_profile"] == "abrupt"


def test_missing_anchor_configuration_fails_loudly(cfg):
    without = copy.deepcopy(cfg)
    without["state_tracking"]["anchor_case"] = None
    with pytest.raises(anchor13.AnchorError):
        anchor13.resolve_anchor_spec(without)


def test_unrecognised_anchor_name_is_refused_not_defaulted(cfg):
    bogus = copy.deepcopy(cfg)
    bogus["state_tracking"]["anchor_case"] = "whatever_is_handy"
    with pytest.raises(anchor13.AnchorError):
        anchor13.resolve_anchor_spec(bogus)


def test_trial_named_anchor_resolves_to_that_index(cfg):
    named = copy.deepcopy(cfg)
    named["state_tracking"]["anchor_case"] = "t0021"
    spec = anchor13.resolve_anchor_spec(named)
    assert spec.source == "trial"
    assert spec.trial_index == 21


def test_binding_a_different_design_to_the_anchor_is_refused(cfg):
    """The guard against accidentally anchoring on some other trial."""

    spec = anchor13.resolve_anchor_spec(cfg)
    with pytest.raises(anchor13.AnchorError) as excinfo:
        anchor13.bind_anchor_to_trial(
            spec,
            {**DESIGN, "asymmetry_s": 0.52, "grading_profile": "linear"},
            cfg,
        )
    assert "different design" in str(excinfo.value)


def test_incomplete_anchor_data_fails(cfg, tmp_path):
    spec = anchor13.resolve_anchor_spec(cfg)
    reference = design13.reference_parameters(cfg)
    with pytest.raises(anchor13.AnchorError) as excinfo:
        anchor13.load_anchor_states(spec, tmp_path, reference, cfg)
    assert "no usable envelopes" in str(excinfo.value)


def test_anchor_loads_with_real_energies(cfg, tmp_path):
    spec = anchor13.resolve_anchor_spec(cfg)
    reference = design13.reference_parameters(cfg)
    _write_envelopes(tmp_path)
    states, bound = anchor13.load_anchor_states(
        spec,
        tmp_path,
        reference,
        cfg,
        observables={
            "electron_energies_eV": [2.90, 3.00],
            "heavy_hole_energies_eV": [1.45, 1.42],
        },
    )
    assert states.synthetic_energy_bands == ()
    assert bound.design_hash == spec.design_hash


def test_anchor_assignment_reports_the_full_overlap_matrix(cfg):
    left, right = _left_right()
    anchor = _states(0, np.column_stack([left, right]))
    case = _states(1, np.column_stack([left, right]), parameters={**DESIGN, "asymmetry_s": 0.45})

    record = anchor13.assign_to_anchor(case, anchor, cfg)
    assert record["method"] == "fixed_anchor_overlap_assignment"
    assert record["order_independent"] is True
    for band in ("electron", "heavy_hole"):
        matrix = record["overlap_matrix"][band]
        assert len(matrix) == 2 and len(matrix[0]) == 2
        assert record["assignments"][band]
    assert record["minimum_assignment_margin_observed"] is not None
    assert record["ambiguity_threshold"] == pytest.approx(0.15)


def test_anchor_assignment_is_independent_of_case_ordering(cfg):
    left, right = _left_right()
    anchor = _states(0, np.column_stack([left, right]))
    cases = [
        _states(
            index,
            np.column_stack([left, right]),
            parameters={**DESIGN, "asymmetry_s": 0.40 + 0.01 * index},
        )
        for index in range(1, 6)
    ]
    forward = anchor13.assign_all_to_anchor(cases, anchor, cfg)

    shuffled = list(cases)
    random.Random(11).shuffle(shuffled)
    backward = anchor13.assign_all_to_anchor(shuffled, anchor, cfg)

    comparison = anchor13.compare_orderings(forward, backward)
    assert comparison["order_independent"] is True
    assert comparison["disagreeing_trials"] == []
    assert forward["combined_fingerprint"] == backward["combined_fingerprint"]


def test_repeated_anchor_runs_are_identical(cfg):
    left, right = _left_right()
    anchor = _states(0, np.column_stack([left, right]))
    cases = [_states(1, np.column_stack([left, right]), parameters={**DESIGN, "asymmetry_s": 0.45})]
    first = anchor13.assign_all_to_anchor(cases, anchor, cfg)
    second = anchor13.assign_all_to_anchor(cases, anchor, cfg)
    assert first["combined_fingerprint"] == second["combined_fingerprint"]


def test_anchor_does_not_chain_between_cases(cfg):
    """Each case is compared to the anchor, never to another case.

    Evaluating a case alone and evaluating it alongside a very different design
    must give the same answer; a chaining tracker would not.
    """

    left, right = _left_right()
    anchor = _states(0, np.column_stack([left, right]))
    target = _states(2, np.column_stack([left, right]), parameters={**DESIGN, "asymmetry_s": 0.45})
    distractor = _states(
        1,
        np.column_stack([right, left]),
        parameters={**DESIGN, "asymmetry_s": 0.55, "grading_profile": "erf"},
    )

    alone = anchor13.assign_all_to_anchor([target], anchor, cfg)
    together = anchor13.assign_all_to_anchor([distractor, target], anchor, cfg)
    assert alone["fingerprints"][2] == together["fingerprints"][2]


def test_anchor_reports_ambiguity_rather_than_smoothing_it(cfg):
    z = Z
    a = _normalise(np.sin(np.pi * (z + 8.0) / 16.0))
    b = _normalise(np.sin(2 * np.pi * (z + 8.0) / 16.0))
    mixed = np.column_stack([(a + b) / np.sqrt(2), (a - b) / np.sqrt(2)])

    anchor = _states(0, np.column_stack([a, b]))
    case = _states(1, mixed, parameters={**DESIGN, "asymmetry_s": 0.45})

    strict = copy.deepcopy(cfg)
    strict["state_tracking"]["ambiguity_threshold"] = 0.9
    record = anchor13.assign_to_anchor(case, anchor, strict)
    assert record["ambiguous_under_threshold"] is True


def test_incompatible_grids_are_refused(cfg):
    left, right = _left_right()
    anchor = _states(0, np.column_stack([left, right]))
    far = np.linspace(200.0, 216.0, Z.size)
    case = _states(
        1,
        np.column_stack([left, right]),
        parameters={**DESIGN, "asymmetry_s": 0.45},
        z=far,
    )
    with pytest.raises(anchor13.AnchorError) as excinfo:
        anchor13.assign_to_anchor(case, anchor, cfg)
    assert "z-range" in str(excinfo.value)


def test_anchor_sign_reversal_is_handled(cfg):
    left, right = _left_right()
    anchor = _states(0, np.column_stack([left, right]))
    case = _states(
        1,
        np.column_stack([-left, -right]),
        parameters={**DESIGN, "asymmetry_s": 0.45},
    )
    record = anchor13.assign_to_anchor(case, anchor, cfg)
    assert record["tracked_labels"]["electron"] == [1, 2]
    assert record["state_tracking_confidence"] > 0.9


def test_anchor_rows_are_flat_and_carry_provenance(cfg):
    left, right = _left_right()
    anchor = _states(0, np.column_stack([left, right]))
    case = _states(1, np.column_stack([left, right]), parameters={**DESIGN, "asymmetry_s": 0.45})
    spec = anchor13.resolve_anchor_spec(cfg)
    summary = anchor13.assign_all_to_anchor([case], anchor, cfg, spec=spec)
    rows = anchor13.anchor_rows(summary)
    assert rows
    for row in rows:
        assert row["anchor_case"] == "reference_abrupt"
        assert row["energy_provenance"] == "solver"
        assert row["band"] in {"electron", "heavy_hole"}


def test_assignment_matrices_are_dropped_when_not_requested(cfg):
    left, right = _left_right()
    anchor = _states(0, np.column_stack([left, right]))
    case = _states(1, np.column_stack([left, right]), parameters={**DESIGN, "asymmetry_s": 0.45})

    quiet = copy.deepcopy(cfg)
    quiet["state_tracking"]["save_complete_assignment_matrices"] = False
    record = anchor13.assign_to_anchor(case, anchor, quiet)
    assert "diagnostics" not in record
    # The overlap matrix itself is a reported result, not a diagnostic dump, and
    # stays either way.
    assert record["overlap_matrix"]["electron"]


def _validation_row(directory: Path, trial_index: int, parameters) -> dict:
    extracted = directory / "extracted"
    _write_envelopes(extracted)
    _write_state_table(extracted / "electron_states.csv", [2.90, 3.00])
    _write_state_table(extracted / "heavy_hole_states.csv", [1.45, 1.42])
    return {
        "trial_index": trial_index,
        "status": "completed",
        "output_directory_path": str(directory),
        "electron_energies_eV": [2.90, 3.00],
        "heavy_hole_energies_eV": [1.45, 1.42],
        "historical_tracked_state_labels": {
            "electron": [1, 2], "heavy_hole": [1, 2]
        },
        **{f"parameter_{key}": value for key, value in parameters.items()},
    }


def test_stage5_production_entry_is_order_independent_and_uses_constraint(cfg, tmp_path):
    reference = design13.reference_parameters(cfg)
    spec = anchor13.resolve_anchor_spec(cfg)
    anchor_row = _validation_row(tmp_path / "anchor", -1, reference)
    cases = [
        _validation_row(tmp_path / "t0021", 21, reference),
        _validation_row(
            tmp_path / "t0022", 22, {**reference, "asymmetry_s": 0.43}
        ),
    ]

    forward = demo13.validation_anchor_tracking(cfg, spec, anchor_row, cases)
    backward = demo13.validation_anchor_tracking(cfg, spec, anchor_row, list(reversed(cases)))
    assert forward["combined_fingerprint"] == backward["combined_fingerprint"]
    assert forward["acceptance_passed"] is True
    assert forward["acceptance_minimum_confidence"] == pytest.approx(0.80)
    assert all(
        record["labels_match_historical"] is True
        for record in forward["records"]
    )

    stricter = copy.deepcopy(cfg)
    stricter["bo"]["outcome_constraints"]["minimum_state_tracking_confidence"] = 1.01
    failed = demo13.validation_anchor_tracking(stricter, spec, anchor_row, cases)
    assert failed["acceptance_minimum_confidence"] == pytest.approx(1.01)
    assert failed["acceptance_passed"] is False

    unavailable_anchor = {**anchor_row, "status": "pending_no_solver"}
    unavailable = demo13.validation_anchor_tracking(
        cfg, spec, unavailable_anchor, cases
    )
    assert unavailable["derived_value_status"] == "unavailable"
    assert unavailable["energy_provenance"] == "unavailable"


def test_anchor_rows_reach_the_table_writer(cfg, tmp_path, monkeypatch):
    emitted = {}

    def capture(_parent, name, rows, **_kwargs):
        emitted[name] = list(rows)

    monkeypatch.setattr(tables13, "write_table", capture)
    rows = [{"trial_index": 21, "band": "electron", "tracked_label": 1}]
    tables13.write_all(
        tmp_path,
        cfg=cfg,
        records=[],
        spec=axsearch13.build_optimization_spec(cfg),
        anchor_tracking_rows=rows,
    )
    assert emitted["bo_anchor_state_tracking_assignments"] == rows
