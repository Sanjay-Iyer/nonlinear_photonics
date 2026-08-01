"""One count of what a Demo 13 campaign did, used by everything that reports it.

Before this module the console, the run manifest, the experiment manifest, the
validation report, the results overview, the budget table and the candidate
history each derived their own counts, and on the v3 campaign they disagreed:

* the budget table reported **0** preflight-invalid proposals and **0**
  duplicates while simultaneously reporting **7** abandoned Ax trials -- because
  it classified rejections by searching for ``geometry_preflight`` or
  ``canonical_duplicate`` in the reason string, and every v3 rejection carried
  ``subresolution_grade``, which matches neither;
* the run manifest reported ``status: failed`` for a campaign with sixteen
  completed trials and zero failures, because the shared writer compares
  completed cases against *all* cases and the seven rejected proposals are cases;
* ``optimization_completed`` was **always** false, because it read a key
  (``remaining_new_solver_runs``) that ``plan()`` does not return, so the
  ``.get`` default of 1 was used every time;
* the candidate-lifecycle column described every rejected proposal as
  "rejected as a canonical duplicate", which for v3 was wrong seven times out of
  seven.

The rule this module enforces: **a proposal is classified by what actually
happened to it**, from the immutable ledger, once. A rejection is only a
duplicate when its canonical realized design hash matched an existing design.
Anything that reports a count imports it from here.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import axsearch13
import design13

#: Ledger statuses that mean "this proposal never became an evaluation".
NON_EVALUATION_STATUSES: frozenset[str] = frozenset({"rejected"})

#: Rejection reason prefixes, mapped to the category each one belongs to. Order
#: matters: the first match wins, so a more specific reason must come first.
_REJECTION_CATEGORIES: tuple[tuple[str, str], ...] = (
    (axsearch13.REJECT_DUPLICATE, "canonical_duplicate"),
    (axsearch13.REJECT_SUBRESOLUTION, "subresolution_grade"),
    (axsearch13.REJECT_GEOMETRY, "geometry_preflight"),
    (axsearch13.REJECT_UNRESOLVABLE, "canonicalization_failed"),
)

#: Every rejection category that is a *preflight* refusal -- the proposal was
#: examined and refused before any deck was rendered. All of them are invalid
#: proposals; only one of them is a duplicate.
PREFLIGHT_CATEGORIES: frozenset[str] = frozenset(
    {"subresolution_grade", "geometry_preflight", "canonicalization_failed"}
)


def rejection_category(record: Mapping[str, Any]) -> str:
    """Which kind of refusal this rejected record was.

    Returns ``"unclassified_rejection"`` rather than guessing when the reason
    matches nothing known -- silently folding an unknown reason into
    "duplicate" is exactly the defect this replaces.
    """

    reason = str(record.get("rejection_reason", ""))
    for token, category in _REJECTION_CATEGORIES:
        if token in reason:
            return category
    return "unclassified_rejection"


def is_duplicate(record: Mapping[str, Any]) -> bool:
    """True only when this proposal repeated an already-claimed realized design.

    Decided by the rejection *reason*, which is what the defect was about: v3's
    seven sub-resolution refusals were being counted and described as
    duplicates. ``duplicate_of_trial`` is reported alongside as provenance but
    is deliberately **not** required -- a ledger that recorded the reason but
    not the trial index still describes a duplicate, and demanding both would
    under-count rather than mislabel.
    """

    return rejection_category(record) == "canonical_duplicate"


def lifecycle_phrase(record: Mapping[str, Any]) -> str:
    """One sentence describing what happened to this proposal.

    Replaces a hard-coded "rejected as a canonical duplicate" that was applied
    to every rejected record regardless of why it was rejected.
    """

    status = str(record.get("status"))
    if status == "rejected":
        category = rejection_category(record)
        if category == "canonical_duplicate":
            other = record.get("duplicate_of_trial")
            suffix = f" of trial {other}" if other is not None else ""
            return f"proposed, rejected as a canonical duplicate{suffix}, never simulated"
        if category == "subresolution_grade":
            return (
                "proposed on the graded branch, rejected because the realized grade "
                "would be below the mesh-resolvable minimum, never simulated"
            )
        if category == "geometry_preflight":
            return "proposed, rejected as unbuildable geometry, never simulated"
        if category == "canonicalization_failed":
            return "proposed, rejected because it could not be canonicalized, never simulated"
        return "proposed, rejected, never simulated"
    if status == "failed":
        return "proposed, executed, failed"
    if status == "completed":
        return "proposed, executed, completed" + (
            "" if record.get("trial_valid") else ", rejected by outcome constraints"
        )
    return "proposed, input generated, execution pending"


def campaign_accounting(
    records: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """The single authoritative count of a campaign, derived from the ledger.

    Every field is computed here and nowhere else. ``analysis_only`` is set by
    the caller because it is a property of *this invocation*, not of the ledger.
    """

    counts = design13.expected_evaluation_counts(cfg)
    rows = list(records)

    rejected = [r for r in rows if str(r.get("status")) == "rejected"]
    evaluations = [
        r for r in rows if str(r.get("status")) not in NON_EVALUATION_STATUSES
    ]
    completed = [r for r in evaluations if str(r.get("status")) == "completed"]
    failed = [r for r in evaluations if str(r.get("status")) == "failed"]
    pending = [
        r for r in rows if str(r.get("status")) not in axsearch13.TERMINAL_STATUSES
    ]

    categories: dict[str, int] = {}
    for record in rejected:
        category = rejection_category(record)
        categories[category] = categories.get(category, 0) + 1
    duplicates = [r for r in rejected if is_duplicate(r)]
    preflight_invalid = [
        r for r in rejected if rejection_category(r) in PREFLIGHT_CATEGORIES
    ]

    def _generated_by(rows_: Sequence[Mapping[str, Any]], method: str) -> list:
        return [r for r in rows_ if str(r.get("generation_method")) == method]

    sobol_completed = _generated_by(completed, "Sobol")
    model_completed = _generated_by(completed, "MBM")
    feasible = [r for r in completed if r.get("trial_valid")]
    invalid_completed = [r for r in completed if not r.get("trial_valid")]

    requested = int(counts["num_initial_trials"]) + int(counts["num_iterations"]) * int(
        counts["batch_size"]
    )
    # Budget is spent by *evaluations*, never by refused proposals: a rejected
    # proposal costs an attempt, not a licensed solver run.
    remaining = max(0, requested - len(completed) - len(failed))

    accounting: dict[str, Any] = {
        "proposed_candidates": len(rows),
        "preflight_rejected": len(preflight_invalid),
        "canonical_duplicates": len(duplicates),
        "rejected_total": len(rejected),
        "rejections_by_category": dict(sorted(categories.items())),
        "abandoned_ax_trials": len(rejected),
        "solver_launched": len([r for r in evaluations if r.get("solver_launched")]),
        "solver_completed": len(completed),
        "solver_failed": len(failed),
        "sobol_proposed": len(_generated_by(rows, "Sobol")),
        "sobol_completed": len(sobol_completed),
        "model_based_proposed": len(_generated_by(rows, "MBM")),
        "model_based_completed": len(model_completed),
        "feasible_completed": len(feasible),
        "scientifically_invalid_completed": len(invalid_completed),
        "pending": len(pending),
        "requested_evaluations": requested,
        "remaining_evaluations": remaining,
        "optimization_completed": bool(remaining == 0 and not pending),
        "analysis_only_run": False,
        "requested_initial_trials": int(counts["num_initial_trials"]),
        "requested_bo_iterations": int(counts["num_iterations"]),
        "batch_size": int(counts["batch_size"]),
        "feasible_trial_indices": sorted(
            int(r.get("trial_index", -1)) for r in feasible
        ),
        "rejected_trial_indices": sorted(
            int(r.get("trial_index", -1)) for r in rejected
        ),
        "model_based_completed_trial_indices": sorted(
            int(r.get("trial_index", -1)) for r in model_completed
        ),
        "iteration_definition": (
            "one requested BO iteration = one completed model-based evaluation; a "
            "proposal refused at preflight costs a regeneration attempt and no "
            "licensed solver run, so it does not consume one"
        ),
    }
    # An identity, asserted rather than assumed: every proposal is either an
    # evaluation or a refusal, and there is no third place for one to hide.
    accounting["accounting_identity_holds"] = bool(
        accounting["proposed_candidates"]
        == accounting["rejected_total"]
        + accounting["solver_completed"]
        + accounting["solver_failed"]
        + accounting["pending"]
    )
    accounting["rejection_identity_holds"] = bool(
        accounting["rejected_total"]
        == sum(accounting["rejections_by_category"].values())
    )
    return accounting


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def rejection_history(
    records: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The complete refusal record, rebuilt from the immutable ledger.

    This used to be assembled from in-memory loop state and passed down from
    ``closed_loop``.  Reanalysis never runs that loop, so on every
    ``analyze_existing_results`` pass the table came out as
    ``note,no rows for this table in this run`` -- for a campaign with seven
    refusals sitting in the ledger.  Deriving it from the ledger instead means
    the history survives the run that produced it, which is the whole point of
    having an immutable ledger.

    The proposed geometry is read from ``parameters`` (what Ax asked for), never
    from the ``parameter_*`` columns, which hold the *canonicalized* design and
    therefore show a refused graded proposal as an abrupt 0 nm one.
    """

    import design13
    import geometry13

    minimum = design13.minimum_resolvable_grading_nm(cfg)
    snap = geometry13.mesh_snap_nm(cfg)
    rows: list[dict[str, Any]] = []
    ordered = sorted(records, key=lambda r: int(r.get("trial_index", -1)))
    rejected_seen = 0
    for record in ordered:
        if str(record.get("status")) != "rejected":
            continue
        rejected_seen += 1
        proposed = dict(record.get("parameters") or {})
        canonical = dict(record.get("canonical_parameters") or {})
        fraction = _number(
            record.get("proposed_grading_fraction")
            or canonical.get("_proposed_grading_fraction")
            or proposed.get("grading_fraction_of_feasible_max")
        )
        maximum = _number(
            record.get("maximum_feasible_grading_nm")
            or record.get("maximum_feasible_grading_thickness_nm")
            or canonical.get("_maximum_feasible_grading_nm")
        )
        unsnapped = None if fraction is None or maximum is None else fraction * maximum
        # The width that *would* have been built, before the abrupt collapse.
        # Recorded directly on newer runs; recomputed here for the v3 ledger,
        # which predates that field.
        before_collapse = _number(record.get("realized_grading_before_collapse_nm"))
        if before_collapse is None and unsnapped is not None:
            before_collapse = (
                geometry13.snap_to_mesh(unsnapped, snap) if snap > 0 else unsnapped
            )
        category = rejection_category(record)
        rows.append(
            {
                "proposal_attempt_index": rejected_seen,
                "trial_index": record.get("trial_index"),
                "candidate_id": record.get("candidate_id"),
                "requested_bo_iteration": record.get("iteration"),
                "generation_method": record.get("generation_method"),
                "expected_acquisition_value": record.get("expected_acquisition_value"),
                "proposed_interface_mode": str(
                    proposed.get("interface_mode")
                    or ("graded" if fraction is not None else "abrupt")
                ),
                "proposed_grading_profile": str(
                    proposed.get("grading_profile") or "abrupt"
                ),
                "proposed_asymmetry_s": _number(proposed.get("asymmetry_s")),
                "proposed_central_barrier_thickness_nm": _number(
                    proposed.get("central_barrier_thickness_nm")
                ),
                "proposed_grading_fraction": fraction,
                "proposed_grading_thickness_nm_unsnapped": unsnapped,
                "maximum_feasible_grading_nm": maximum,
                "minimum_required_grading_nm": minimum,
                "realized_grading_thickness_nm_before_collapse": before_collapse,
                "realized_grading_thickness_nm_after_collapse": _number(
                    record.get("realized_grading_thickness_nm")
                ),
                "rejection_category": category,
                "rejection_reason": record.get("rejection_reason"),
                "duplicate_of_trial": record.get("duplicate_of_trial"),
                "solver_launched": bool(record.get("solver_launched", False)),
                "consumed_bo_budget": _consumed_budget(record, cfg),
                "replacement_trial_index": _replacement_for(record, ordered),
                "note": (
                    "the proposed columns are what Ax asked for; the parameter_* "
                    "columns of this trial hold the canonicalized design and show "
                    "it as abrupt, which is why they are not used here"
                ),
            }
        )
    return rows


def _consumed_budget(record: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    """Whether this refusal cost one of the requested BO iterations."""

    bo = cfg.get("bo") or {}
    if rejection_category(record) == "canonical_duplicate":
        return bool(bo.get("duplicate_counts_as_bo_iteration", False))
    return bool(bo.get("invalid_preflight_counts_as_bo_iteration", False))


def _replacement_for(
    record: Mapping[str, Any], ordered: Sequence[Mapping[str, Any]]
) -> int | None:
    """The next proposal that actually became an evaluation."""

    index = int(record.get("trial_index", -1))
    for candidate in ordered:
        if int(candidate.get("trial_index", -1)) <= index:
            continue
        if str(candidate.get("status")) == "completed":
            return int(candidate["trial_index"])
    return None


def proposed_versus_realized_grading(
    records: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """One row per proposal, with what Ax asked for beside what was built.

    The v3 bundle plotted refused graded proposals as *evaluated abrupt
    zero-grade designs*, because their ``parameter_*`` columns hold the
    canonicalized structure -- and canonicalization turns a refused grade into
    abrupt 0 nm. Seven graded proposals therefore appeared in the abrupt
    population, and the profiles they asked for vanished.

    Here the proposal is read from ``parameters`` and the structure from the
    canonical design, and the two are never merged into one column.
    """

    import design13
    import grading13

    minimum = design13.minimum_resolvable_grading_nm(cfg)
    rows: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda r: int(r.get("trial_index", -1))):
        proposed = dict(record.get("parameters") or {})
        canonical = dict(record.get("canonical_parameters") or {})
        status = str(record.get("status"))
        rejected = status == "rejected"
        view = grading13.try_from_record(record)
        fraction = _number(
            record.get("proposed_grading_fraction")
            or canonical.get("_proposed_grading_fraction")
            or proposed.get("grading_fraction_of_feasible_max")
        )
        maximum = _number(
            record.get("maximum_feasible_grading_nm")
            or record.get("maximum_feasible_grading_thickness_nm")
            or canonical.get("_maximum_feasible_grading_nm")
        )
        proposed_mode = str(
            proposed.get("interface_mode")
            or ("graded" if fraction is not None else "abrupt")
        )
        proposed_profile = str(proposed.get("grading_profile") or "abrupt")
        # A refused proposal has no realized structure at all: nothing was
        # built. Reporting "abrupt, 0 nm" for it is the defect.
        realized_mode = (
            "not_realized"
            if rejected
            else (view.realized_interface_mode if view else grading13.UNKNOWN)
        )
        realized_profile = (
            "not_realized" if rejected else (view.realized_grading_profile if view else None)
        )
        realized_nm = None if rejected else (view.realized_grading_thickness_nm if view else None)
        rows.append(
            {
                "trial_index": record.get("trial_index"),
                "candidate_id": record.get("candidate_id"),
                "status": status,
                "generation_method": record.get("generation_method"),
                "proposed_interface_mode": proposed_mode,
                "proposed_grading_profile": proposed_profile,
                "proposed_grading_fraction": fraction,
                "proposed_grading_thickness_nm_unsnapped": (
                    None if fraction is None or maximum is None else fraction * maximum
                ),
                "maximum_feasible_grading_nm": maximum,
                "minimum_required_grading_nm": minimum,
                "realized_interface_mode": realized_mode,
                "realized_grading_profile": realized_profile,
                "realized_grading_thickness_nm": realized_nm,
                "was_rejected": rejected,
                "rejection_category": rejection_category(record) if rejected else None,
                "collapsed_to_abrupt": bool(
                    (not rejected) and view is not None and view.collapsed_to_abrupt
                ),
                "is_genuinely_graded": bool(
                    (not rejected) and view is not None and view.is_genuinely_graded
                ),
                "counts_as_profile_evidence": (
                    None
                    if rejected
                    else (view.profile_evidence if view else None)
                ),
                "trial_valid": record.get("trial_valid"),
            }
        )
    return rows


def grading_population_counts(
    records: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """How much grading evidence exists, split so it cannot be over-read."""

    rows = proposed_versus_realized_grading(records, cfg)
    completed = [r for r in rows if r["status"] == "completed"]
    genuine = [r for r in completed if r["is_genuinely_graded"]]
    per_profile: dict[str, int] = {}
    per_profile_feasible: dict[str, int] = {}
    for row in genuine:
        profile = str(row["realized_grading_profile"])
        per_profile[profile] = per_profile.get(profile, 0) + 1
        if row["trial_valid"]:
            per_profile_feasible[profile] = per_profile_feasible.get(profile, 0) + 1
    return {
        "proposed_graded": sum(1 for r in rows if r["proposed_interface_mode"] == "graded"),
        "rejected_graded": sum(
            1 for r in rows if r["was_rejected"] and r["proposed_interface_mode"] == "graded"
        ),
        "evaluated_genuine_graded": len(genuine),
        "feasible_genuine_graded": sum(1 for r in genuine if r["trial_valid"]),
        "evaluated_abrupt": sum(
            1 for r in completed if r["realized_interface_mode"] == "abrupt"
        ),
        "collapsed_to_abrupt": sum(1 for r in completed if r["collapsed_to_abrupt"]),
        "genuine_graded_per_profile": dict(sorted(per_profile.items())),
        "feasible_genuine_graded_per_profile": dict(sorted(per_profile_feasible.items())),
        "profile_ranking_supportable": bool(
            per_profile and len(per_profile) >= 2 and min(per_profile.values()) >= 3
        ),
        "interpretation": (
            "A refused proposal built nothing and is counted only as a proposal. "
            "A per-profile ranking needs several genuinely graded trials of each "
            "profile; below that these are observations, never a ranking. Counts "
            "restricted to feasible trials are the only ones that may be compared "
            "on the objective at all."
        ),
    }


def trial_iteration_mapping(
    records: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """One row per proposal, tying together the five numbers that get confused.

    * **proposal attempt** -- position in the order Ax was asked for a point;
    * **Ax trial index** -- the identifier in the snapshot and the ledger;
    * **completed evaluation number** -- 1..N over trials that produced data;
    * **Sobol evaluation number** -- 1..6 over completed initialization trials;
    * **MBM iteration number** -- 1..10 over completed model-based trials.

    A figure captioned "by BO iteration" must use the MBM number. Using the
    ledger's ``iteration`` field instead counts *proposal attempts*, so seven
    refusals pushed the last v3 evaluation to iteration 16 of a 10-iteration
    study.
    """

    ordered = sorted(records, key=lambda r: int(r.get("trial_index", -1)))
    rows: list[dict[str, Any]] = []
    attempt = completed = sobol = model = 0
    for record in ordered:
        attempt += 1
        status = str(record.get("status"))
        method = str(record.get("generation_method"))
        evaluation_number = sobol_number = model_number = None
        if status == "completed":
            completed += 1
            evaluation_number = completed
            if method == "Sobol":
                sobol += 1
                sobol_number = sobol
            elif method == "MBM":
                model += 1
                model_number = model
        rows.append(
            {
                "proposal_attempt": attempt,
                "trial_index": record.get("trial_index"),
                "candidate_id": record.get("candidate_id"),
                "status": status,
                "generation_method": method,
                "requested_bo_iteration_recorded": record.get("iteration"),
                "completed_evaluation_number": evaluation_number,
                "sobol_evaluation_number": sobol_number,
                "mbm_iteration_number": model_number,
                "rejection_category": (
                    rejection_category(record) if status == "rejected" else None
                ),
                "appears_in_iteration_plots": model_number is not None,
            }
        )
    return rows


def budget_table_row(accounting: Mapping[str, Any]) -> dict[str, Any]:
    """The flat row written to ``bo_budget_accounting.csv``.

    Kept a projection of :func:`campaign_accounting` rather than a second
    derivation, so the table cannot drift from the console.
    """

    return {
        "proposed_candidates": accounting["proposed_candidates"],
        "preflight_rejected": accounting["preflight_rejected"],
        "canonical_duplicates": accounting["canonical_duplicates"],
        "abandoned_ax_trials": accounting["abandoned_ax_trials"],
        "solver_launched": accounting["solver_launched"],
        "solver_completed": accounting["solver_completed"],
        "solver_failed": accounting["solver_failed"],
        "sobol_proposed": accounting["sobol_proposed"],
        "sobol_completed": accounting["sobol_completed"],
        "model_based_proposed": accounting["model_based_proposed"],
        "model_based_completed": accounting["model_based_completed"],
        "feasible_completed": accounting["feasible_completed"],
        "scientifically_invalid_completed": accounting[
            "scientifically_invalid_completed"
        ],
        "pending": accounting["pending"],
        "requested_evaluations": accounting["requested_evaluations"],
        "remaining_evaluations": accounting["remaining_evaluations"],
        "optimization_completed": accounting["optimization_completed"],
        "analysis_only_run": accounting["analysis_only_run"],
        "iteration_definition": accounting["iteration_definition"],
    }


def report_lines(accounting: Mapping[str, Any]) -> list[str]:
    """The console block. ASCII only: this prints to a cp1252 Windows console."""

    lines = [
        "Demo 13 - campaign accounting",
        f"  proposed candidates         : {accounting['proposed_candidates']}",
        f"  preflight rejected          : {accounting['preflight_rejected']}"
        f"  (duplicates: {accounting['canonical_duplicates']})",
    ]
    for category, count in accounting["rejections_by_category"].items():
        lines.append(f"      {category:<24}: {count}")
    lines += [
        f"  solver completed            : {accounting['solver_completed']}"
        f"  (Sobol {accounting['sobol_completed']}, MBM {accounting['model_based_completed']})",
        f"  solver failed               : {accounting['solver_failed']}",
        f"  feasible completed          : {accounting['feasible_completed']}",
        f"  pending                     : {accounting['pending']}",
        f"  remaining evaluations       : {accounting['remaining_evaluations']}"
        f" of {accounting['requested_evaluations']} requested",
        f"  optimization completed      : {accounting['optimization_completed']}",
    ]
    if accounting.get("analysis_only_run"):
        lines.append("  analysis-only run           : no solver was invoked")
    if not accounting.get("accounting_identity_holds", True):
        lines.append(
            "  WARNING: proposals != rejected + completed + failed + pending; "
            "the ledger is inconsistent"
        )
    return lines
