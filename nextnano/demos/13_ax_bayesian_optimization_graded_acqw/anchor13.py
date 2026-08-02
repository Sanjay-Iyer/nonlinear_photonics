"""Order-independent state tracking against one fixed anchor design.

Why a second tracker
====================

:mod:`tracking13` assigns each trial to its *nearest already-completed
neighbour*.  That is the right thing during a closed loop -- it is the only
comparison available while the campaign is still running, and it reproduces
exactly what the optimizer saw -- but it has two properties that make it unfit
for a validation gate:

* it is **order dependent**.  The reference for trial *n* is chosen from the
  trials that finished before it, so re-running the same designs in a different
  order can assign them differently.
* it **chains**.  Trial *n* is compared to *n-1*, which was compared to *n-2*.
  A small labelling error early on is inherited by everything downstream and
  never re-examined.

Stage 5 asks a different question: *do these designs' state identities agree
with one fixed, independently chosen reference?*  Answering it needs every case
compared directly and only to that reference, so the answer for one case cannot
depend on which other cases were evaluated, or in what order.  That is what this
module does, and it is what ``state_tracking.anchor_case`` in ``demo.yaml`` has
been configured for while being read by no code.

What "order independent" means here, precisely
==============================================

:func:`assign_to_anchor` is a pure function of ``(anchor, case, cfg)``.  It
never sees the other cases, keeps no state between calls, and is therefore
invariant under any permutation of the case list and idempotent under repetition.
:func:`assign_all_to_anchor` verifies that property rather than asserting it: it
records a content hash of each per-case result so a caller (and the test suite)
can compare two shuffled evaluations directly.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for _path in (str(SHARED), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import DemoError  # noqa: E402

import design13  # noqa: E402
import tracking13  # noqa: E402

#: ``anchor_case`` value meaning "the abrupt reference design this demo
#: inherits from Demos 11 and 12", as opposed to a named trial.
REFERENCE_ANCHOR = "reference_abrupt"

#: Fraction of the anchor's z-range a case must also span before its envelopes
#: may be interpolated onto the anchor grid. Below this the resampling
#: zero-fills most of the domain and every overlap collapses toward zero, which
#: would be reported as "all assignments ambiguous" when the real fault is that
#: the two calculations do not describe the same region of space.
MINIMUM_GRID_OVERLAP_FRACTION = 0.90


class AnchorError(DemoError):
    """The configured anchor is missing, incomplete, or not the one meant."""


@dataclass(frozen=True)
class AnchorSpec:
    """Which design is the anchor, and how it was named.

    ``design_hash`` is the identity guard.  It is computed from the *canonical
    physical structure*, so it is the thing that must match -- not a trial index
    and not a directory name, either of which can point at a different design
    after a re-run.
    """

    name: str
    source: str
    parameters: Mapping[str, Any]
    design_hash: str
    trial_index: int | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "anchor_case": self.name,
            "anchor_source": self.source,
            "anchor_design_hash": self.design_hash,
            "anchor_trial_index": self.trial_index,
            "anchor_parameters": dict(self.parameters),
        }


def anchor_case_name(cfg: Mapping[str, Any]) -> str | None:
    """The configured ``state_tracking.anchor_case``, or ``None`` if unset."""

    value = (cfg.get("state_tracking") or {}).get("anchor_case")
    if value is None:
        return None
    name = str(value).strip()
    return name or None


def save_assignment_matrices(cfg: Mapping[str, Any]) -> bool:
    """Whether ``state_tracking.save_complete_assignment_matrices`` is on."""

    return bool(
        (cfg.get("state_tracking") or {}).get("save_complete_assignment_matrices", False)
    )


def resolve_anchor_spec(cfg: Mapping[str, Any]) -> AnchorSpec:
    """Turn the configured name into an explicit, hashed design.

    Two forms are accepted and nothing else:

    ``reference_abrupt``
        the abrupt reference design of Demos 11 and 12, recovered from the
        configuration itself so it does not depend on any campaign having run.

    ``t0021`` / ``trial:21``
        one explicitly named completed trial.

    Anything else raises rather than falling back to a default, because a
    silently defaulted anchor is exactly the "accidental use of a different
    trial" this function exists to prevent.
    """

    name = anchor_case_name(cfg)
    if name is None:
        raise AnchorError(
            "state_tracking.anchor_case is not set; an anchor-based check needs "
            f"an explicit anchor. Use {REFERENCE_ANCHOR!r} or a trial id like 't0021'."
        )
    if name == REFERENCE_ANCHOR:
        parameters = design13.reference_parameters(cfg)
        return AnchorSpec(
            name=name,
            source="reference_design",
            parameters=design13.physical_design(parameters),
            design_hash=design13.design_hash(parameters, cfg),
        )
    index = _trial_index_from_name(name)
    if index is None:
        raise AnchorError(
            f"state_tracking.anchor_case={name!r} is not understood; expected "
            f"{REFERENCE_ANCHOR!r} or a trial id such as 't0021'."
        )
    return AnchorSpec(
        name=name,
        source="trial",
        parameters={},
        design_hash="",
        trial_index=index,
    )


def _trial_index_from_name(name: str) -> int | None:
    text = name.strip()
    for prefix in ("trial:", "trial_", "t"):
        if text.startswith(prefix):
            digits = text[len(prefix):]
            if digits.isdigit():
                return int(digits)
    return None


def bind_anchor_to_trial(
    spec: AnchorSpec, parameters: Mapping[str, Any], cfg: Mapping[str, Any]
) -> AnchorSpec:
    """Attach a concrete design to a trial-named anchor, or verify a hashed one.

    Called once the anchor trial's parameters are known.  For a
    ``reference_abrupt`` anchor the hash is already fixed, so this *checks* it
    instead of overwriting it: a mismatch means the directory handed in is not
    the reference design, which is precisely the accident worth refusing.
    """

    canonical = design13.canonicalize(parameters, cfg)
    design_hash = design13.design_hash(parameters, cfg)
    if spec.design_hash and design_hash != spec.design_hash:
        raise AnchorError(
            f"anchor {spec.name!r} should have design hash {spec.design_hash} but "
            f"the states supplied hash to {design_hash}. Refusing to anchor on a "
            "different design than the one configured."
        )
    return AnchorSpec(
        name=spec.name,
        source=spec.source,
        parameters=design13.physical_design(canonical),
        design_hash=design_hash,
        trial_index=spec.trial_index,
    )


def load_anchor_states(
    spec: AnchorSpec,
    extracted_dir: Path,
    parameters: Mapping[str, Any],
    cfg: Mapping[str, Any],
    *,
    observables: Mapping[str, Any] | None = None,
    allow_synthetic_energies: bool = False,
) -> tuple[tracking13.TrialStates, AnchorSpec]:
    """Read the anchor's envelopes and energies, refusing anything partial.

    An anchor with missing wavefunctions, missing energies, or a band the case
    side does not have is not a usable reference, and every downstream number
    would be meaningless.  All three fail here rather than producing confident
    nonsense.
    """

    bound = bind_anchor_to_trial(spec, parameters, cfg)
    states = tracking13.load_trial_states(
        -1 if bound.trial_index is None else int(bound.trial_index),
        design13.canonicalize(parameters, cfg),
        Path(extracted_dir),
        observables=observables,
        allow_synthetic_energies=allow_synthetic_energies,
    )
    if states is None:
        raise AnchorError(
            f"anchor {bound.name!r} has no usable envelopes at "
            f"{Path(extracted_dir) / 'envelopes.csv'}; an anchor-based check "
            "cannot run without the reference wavefunctions."
        )
    for band in tracking13.BANDS:
        energies, envelopes = states.band(band)
        if energies.size == 0 or envelopes.size == 0:
            raise AnchorError(
                f"anchor {bound.name!r} has no {band} states; the anchor data are "
                "incomplete."
            )
        if energies.size != envelopes.shape[1]:
            raise AnchorError(
                f"anchor {bound.name!r} has {energies.size} {band} energies for "
                f"{envelopes.shape[1]} envelopes; the anchor data are inconsistent."
            )
    return states, bound


def _check_grids(anchor: tracking13.TrialStates, case: tracking13.TrialStates) -> None:
    """Refuse a case whose domain barely overlaps the anchor's.

    ``tracking11.interpolate_onto`` resamples with ``left=0, right=0``, so a
    case covering a different span is silently zero-filled and every overlap
    collapses. That reads as "ambiguous assignment" when the truth is that the
    two runs do not describe the same structure.
    """

    anchor_z = np.asarray(anchor.z_nm, dtype=float)
    case_z = np.asarray(case.z_nm, dtype=float)
    if anchor_z.size < 2 or case_z.size < 2:
        raise AnchorError("anchor or case grid has fewer than two points")
    span = float(anchor_z.max() - anchor_z.min())
    if span <= 0:
        raise AnchorError("anchor grid has zero extent")
    overlap = float(
        min(anchor_z.max(), case_z.max()) - max(anchor_z.min(), case_z.min())
    )
    fraction = overlap / span
    if fraction < MINIMUM_GRID_OVERLAP_FRACTION:
        raise AnchorError(
            f"case grid covers {fraction:.1%} of the anchor's z-range, below the "
            f"{MINIMUM_GRID_OVERLAP_FRACTION:.0%} required. Interpolating would "
            "zero-fill most of the domain and report false ambiguity."
        )


def assign_to_anchor(
    case: tracking13.TrialStates,
    anchor: tracking13.TrialStates,
    cfg: Mapping[str, Any],
    *,
    spec: AnchorSpec | None = None,
) -> dict[str, Any]:
    """Assign one case's states to the anchor's. Pure in ``(case, anchor, cfg)``.

    Reuses :func:`tracking13.track_against` so the assignment *physics* -- the
    normalized envelope overlap, the one-to-one solve, the sign alignment, the
    energy-continuity tie-breaker -- is the same code the closed loop ran, and
    only the choice of reference differs. What this adds is the full overlap
    matrix per band, per-state assignment rows, and the anchor's identity, all
    surfaced at the top level so an order-independence check has something
    concrete to compare.
    """

    _check_grids(anchor, case)
    record = tracking13.track_against(case, anchor, cfg)
    record["method"] = "fixed_anchor_overlap_assignment"
    record["order_independent"] = True

    ambiguity_threshold = float(
        (cfg.get("state_tracking") or {}).get("ambiguity_threshold", 0.15)
    )
    overlap_matrices: dict[str, list[list[float]]] = {}
    assignments: dict[str, list[dict[str, Any]]] = {}
    for band in tracking13.BANDS:
        diagnostics = (record.get("diagnostics") or {}).get(band) or {}
        steps = diagnostics.get("steps") or []
        step = steps[0] if steps else {}
        overlap_matrices[band] = [
            [float(value) for value in row]
            for row in (step.get("similarity_matrix") or [])
        ]
        assignments[band] = [dict(entry) for entry in (step.get("assignments") or [])]

    margins = [
        float(entry["margin"])
        for band in tracking13.BANDS
        for entry in assignments[band]
        if entry.get("margin") is not None
    ]
    # `ambiguity_threshold` is a separate, stricter reading of the same margin
    # than `minimum_assignment_margin`: the latter decides whether the tracker
    # calls a single assignment ambiguous, this one decides whether the whole
    # anchored comparison is safe to draw a conclusion from.
    record.update(
        {
            "overlap_matrix": overlap_matrices,
            "assignments": assignments,
            "assignment_margins": margins,
            "minimum_assignment_margin_observed": min(margins) if margins else None,
            "ambiguity_threshold": ambiguity_threshold,
            "ambiguous_under_threshold": bool(
                margins and min(margins) < ambiguity_threshold
            ),
            **(spec.as_record() if spec is not None else {}),
        }
    )
    if not save_assignment_matrices(cfg):
        record.pop("diagnostics", None)
    return record


def result_fingerprint(record: Mapping[str, Any]) -> str:
    """Content hash of the parts of a record an evaluation order could disturb.

    Deliberately excludes the anchor identity block and the raw diagnostics: the
    question is whether the *assignment* is stable, and a hash over everything
    would answer a different, easier question.
    """

    payload = {
        "trial_index": record.get("trial_index"),
        "tracked_labels": record.get("tracked_labels"),
        "raw_indices": record.get("raw_indices"),
        "overlap_matrix": record.get("overlap_matrix"),
        "state_tracking_confidence": record.get("state_tracking_confidence"),
        "assignment_margin": record.get("assignment_margin"),
        "ambiguous": record.get("ambiguous"),
    }
    text = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def assign_all_to_anchor(
    cases: Iterable[tracking13.TrialStates],
    anchor: tracking13.TrialStates,
    cfg: Mapping[str, Any],
    *,
    spec: AnchorSpec | None = None,
) -> dict[str, Any]:
    """Anchor every case, and report the evidence that order did not matter.

    Results are returned sorted by trial index so two shuffled inputs produce
    byte-identical output, and each case carries its own fingerprint so a
    disagreement can be localised to one case rather than reported as "the run
    changed".
    """

    records = [assign_to_anchor(case, anchor, cfg, spec=spec) for case in cases]
    records.sort(key=lambda record: int(record.get("trial_index", 0)))
    fingerprints = {
        int(record.get("trial_index", 0)): result_fingerprint(record)
        for record in records
    }
    confidences = [
        float(record["state_tracking_confidence"])
        for record in records
        if record.get("state_tracking_confidence") is not None
    ]
    synthetic = sorted(
        {
            str(band)
            for record in records
            for band in (record.get("synthetic_energy_bands") or ())
        }
    )
    return {
        "records": records,
        "fingerprints": fingerprints,
        "combined_fingerprint": hashlib.sha256(
            json.dumps(fingerprints, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16],
        "anchored_cases": len(records),
        "minimum_confidence": min(confidences) if confidences else None,
        "ambiguous_trials": [
            int(record["trial_index"])
            for record in records
            if record.get("ambiguous") or record.get("ambiguous_under_threshold")
        ],
        "method": "fixed_anchor_overlap_assignment",
        "order_independent": True,
        "synthetic_energy_bands": synthetic,
        "energy_provenance": (
            "solver" if not synthetic else tracking13.SYNTHETIC_ENERGY_LABEL
        ),
        **(spec.as_record() if spec is not None else {}),
    }


def anchor_rows(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flat, CSV-ready rows: one per (trial, band, state)."""

    rows: list[dict[str, Any]] = []
    for record in summary.get("records", ()):
        for band, entries in (record.get("assignments") or {}).items():
            for entry in entries:
                rows.append(
                    {
                        "trial_index": record.get("trial_index"),
                        "anchor_case": record.get("anchor_case"),
                        "anchor_design_hash": record.get("anchor_design_hash"),
                        "band": band,
                        "raw_index": entry.get("raw_index"),
                        "tracked_label": entry.get("tracked_label"),
                        "matched_anchor_index": entry.get("matched_previous_index"),
                        "best_overlap": entry.get("best_overlap"),
                        "second_best_overlap": entry.get("second_best_overlap"),
                        "assignment_margin": entry.get("margin"),
                        "sign_flip_applied": entry.get("sign_flip_applied"),
                        "ambiguous": entry.get("ambiguous"),
                        "reason": entry.get("reason"),
                        "energy_provenance": record.get("energy_provenance"),
                    }
                )
    return rows


def compare_orderings(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> dict[str, Any]:
    """Whether two evaluations of the same cases agree, and where they do not."""

    left = dict(first.get("fingerprints") or {})
    right = dict(second.get("fingerprints") or {})
    disagreeing = sorted(
        index
        for index in set(left) | set(right)
        if left.get(index) != right.get(index)
    )
    return {
        "order_independent": not disagreeing,
        "compared_cases": len(set(left) | set(right)),
        "disagreeing_trials": disagreeing,
        "first_combined_fingerprint": first.get("combined_fingerprint"),
        "second_combined_fingerprint": second.get("combined_fingerprint"),
    }
