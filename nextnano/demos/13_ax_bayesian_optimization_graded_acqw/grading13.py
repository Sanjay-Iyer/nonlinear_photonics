"""One authoritative reading of what a trial's interface grading actually is.

Demo 13 has three different notions of "the grading" and they are not
interchangeable:

* what Ax *searched* -- under ``parameterization: fraction`` that is
  ``grading_fraction_of_feasible_max``, a dimensionless number in [0, 1] and
  **not** a length;
* what that fraction *asked for* in nanometres -- ``fraction x
  maximum_feasible_grading_nm``, before the mesh has had its say;
* what the deck *built* -- the mesh-snapped width, which is what the electrons
  saw and therefore the only width any physical statement may be made about.

Before this module every consumer (plots, tables, hashing, geometry, reports)
re-derived its own answer from whichever field it happened to know about, and
the three notions were silently mixed: a fraction was plotted on an axis
labelled "nm", and a design whose grade snapped to zero was still counted as
evidence about the ``sigmoid`` profile it had nominally requested.

The rules encoded here, once:

* an abrupt design realizes exactly 0 nm of grading;
* a nominally graded design whose realized width is 0 nm **is** an abrupt
  structure, whatever profile label it was proposed under;
* such a design is not evidence about its nominal profile, because that profile
  was never built;
* physical plots, canonical hashes and scientific comparisons use realized
  values; Ax proposal-history plots may use proposed values, and must say so.

Everything is read defensively from the ledger, because the v2 ledger predates
these names.  A record written by the licensed 2026-07-31 run stores the
provenance under two different spellings depending on whether the trial was
rejected at preflight (``maximum_feasible_grading_thickness_nm``) or ran to
completion (``maximum_feasible_grading_nm``), and stores nothing at all under
either name for a synthetic trial.  All three shapes resolve here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

#: Realized-interface vocabulary. "abrupt" means zero realized transition width.
ABRUPT = "abrupt"
GRADED = "graded"

#: Reported when a record is too old or too sparse to say how it was proposed.
UNKNOWN = "unknown"

#: Axis labels. Using these is how a fraction stops being called a nanometre.
AXIS_PROPOSED_FRACTION = "Proposed grading fraction of feasible maximum (-)"
AXIS_REALIZED_THICKNESS = "Realized grading thickness (nm)"
AXIS_UNSNAPPED_THICKNESS = "Proposed grading thickness before mesh snap (nm)"
AXIS_MAXIMUM_FEASIBLE = "Maximum feasible grading thickness (nm)"

#: Ledger spellings of the feasible maximum, newest first. The completed-trial
#: and rejected-trial paths of the v2 run disagreed; both are accepted.
#: ``_maximum_feasible_grading_nm`` is how :func:`design13.canonicalize` stores
#: it inside ``canonical_parameters``; the ``parameter__`` spelling is the same
#: value after ``metrics13.build_record`` prefixed every canonical key, which it
#: did without stripping the provenance fields first.
_MAXIMUM_KEYS: tuple[str, ...] = (
    "maximum_feasible_grading_nm",
    "maximum_feasible_grading_thickness_nm",
    "_maximum_feasible_grading_nm",
    "parameter__maximum_feasible_grading_nm",
)

_FRACTION_KEYS: tuple[str, ...] = (
    "proposed_grading_fraction",
    "_proposed_grading_fraction",
    "parameter__proposed_grading_fraction",
    "grading_fraction_of_feasible_max",
)

_REALIZED_KEYS: tuple[str, ...] = (
    "realized_grading_thickness_nm",
    "parameter_grading_thickness_nm",
)


class GradingError(ValueError):
    """Raised when a record cannot be read as a grading design at all."""


def _first_number(source: Mapping[str, Any], keys: Iterable[str]) -> float | None:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        return number
    return None


@dataclass(frozen=True)
class GradingView:
    """Every grading quantity of one design, each under its own name.

    ``proposed_*`` fields describe the Ax coordinate and the width it asked
    for.  ``realized_*`` fields describe the structure that was built.  They are
    equal only when the mesh happened to grant the request exactly.
    """

    #: The Ax coordinate under ``parameterization: fraction``. Dimensionless.
    #: ``None`` under the thickness parameterization or for an abrupt design.
    proposed_grading_fraction: float | None
    #: Largest grade this candidate's well/barrier geometry could construct.
    maximum_feasible_grading_nm: float | None
    #: ``fraction x maximum``: the width asked for, before mesh snapping.
    proposed_grading_thickness_nm_unsnapped: float | None
    #: The width actually built. The only width physics may be claimed about.
    realized_grading_thickness_nm: float
    #: The branch Ax proposed: ``abrupt``, ``graded`` or ``unknown``.
    proposed_interface_mode: str
    #: What the structure is: ``abrupt`` iff the realized width is 0 nm.
    realized_interface_mode: str
    #: The profile label Ax proposed (``abrupt`` on the abrupt branch).
    proposed_grading_profile: str
    #: The profile actually built; ``abrupt`` whenever the width is 0 nm.
    realized_grading_profile: str
    #: True when a nominally graded proposal realized as an abrupt structure.
    collapsed_to_abrupt: bool
    #: How the numbers were obtained, for provenance in reports.
    source: str

    @property
    def is_genuinely_graded(self) -> bool:
        """True only when a non-zero grade was actually built.

        This is the predicate that decides whether a trial is allowed to be
        evidence about grading at all.
        """

        return self.realized_grading_thickness_nm > 0.0

    @property
    def profile_evidence(self) -> str | None:
        """The profile this trial is evidence about, or ``None``.

        A zero-width cosine is not a cosine.  Returning ``None`` is what stops
        a collapsed proposal being counted in a per-profile comparison.
        """

        return self.realized_grading_profile if self.is_genuinely_graded else None

    def as_record(self) -> dict[str, Any]:
        """Flat mapping for CSV columns and JSON sidecars."""

        record = asdict(self)
        record["is_genuinely_graded"] = self.is_genuinely_graded
        return record


#: Units for every field :meth:`GradingView.as_record` emits, for CSV sidecars.
UNITS: dict[str, str] = {
    "proposed_grading_fraction": "-",
    "maximum_feasible_grading_nm": "nm",
    "proposed_grading_thickness_nm_unsnapped": "nm",
    "realized_grading_thickness_nm": "nm",
    "proposed_interface_mode": "-",
    "realized_interface_mode": "-",
    "proposed_grading_profile": "-",
    "realized_grading_profile": "-",
    "collapsed_to_abrupt": "-",
    "is_genuinely_graded": "-",
    "source": "-",
}


def _view(
    *,
    fraction: float | None,
    maximum: float | None,
    realized: float,
    proposed_mode: str,
    proposed_profile: str,
    source: str,
) -> GradingView:
    """Apply the collapse rules once, so no caller has to remember them."""

    realized = float(realized)
    if realized < 0.0:
        raise GradingError(f"realized grading thickness cannot be negative: {realized}")
    unsnapped = (
        None if fraction is None or maximum is None else float(fraction) * float(maximum)
    )
    if proposed_mode == ABRUPT:
        # An abrupt interface has no transition width. This is not a snap; it is
        # what the branch means, so it is forced rather than inferred.
        realized = 0.0
        fraction, unsnapped = None, None
    graded = realized > 0.0
    return GradingView(
        proposed_grading_fraction=None if fraction is None else float(fraction),
        maximum_feasible_grading_nm=None if maximum is None else float(maximum),
        proposed_grading_thickness_nm_unsnapped=unsnapped,
        realized_grading_thickness_nm=realized,
        proposed_interface_mode=proposed_mode,
        realized_interface_mode=GRADED if graded else ABRUPT,
        proposed_grading_profile=proposed_profile,
        realized_grading_profile=proposed_profile if graded else ABRUPT,
        collapsed_to_abrupt=(proposed_mode == GRADED and not graded),
        source=source,
    )


def from_record(record: Mapping[str, Any]) -> GradingView:
    """Read one immutable ledger record, of any Demo 13 vintage.

    Never raises on a sparse record: a trial that was rejected before its
    geometry was resolved still has a readable interface mode.
    """

    parameters = record.get("parameters")
    parameters = dict(parameters) if isinstance(parameters, Mapping) else {}
    canonical = record.get("canonical_parameters")
    canonical = dict(canonical) if isinstance(canonical, Mapping) else {}

    # `interface_mode` only exists under the hierarchical encoding. Under the
    # flat encoding the proposed profile carries the same information, because
    # `abrupt` is one of its values.
    raw_mode = parameters.get("interface_mode")
    proposed_profile = str(
        parameters.get("grading_profile")
        or canonical.get("grading_profile")
        or record.get("parameter_grading_profile")
        or ABRUPT
    )
    if raw_mode is not None:
        proposed_mode = ABRUPT if str(raw_mode) == ABRUPT else GRADED
    elif parameters or canonical or record.get("parameter_grading_profile"):
        proposed_mode = ABRUPT if proposed_profile == ABRUPT else GRADED
    else:
        proposed_mode = UNKNOWN
    if proposed_mode == ABRUPT:
        proposed_profile = ABRUPT

    fraction = _first_number({**canonical, **parameters, **record}, _FRACTION_KEYS)
    maximum = _first_number({**canonical, **record}, _MAXIMUM_KEYS)
    realized = _first_number({**canonical, **record}, _REALIZED_KEYS)
    if realized is None:
        realized = _first_number(canonical, ("grading_thickness_nm",))
    if realized is None:
        # Nothing in the record says what was built. Saying "0 nm" here would
        # invent an abrupt structure, so the caller is told instead.
        raise GradingError(
            "record carries no realized grading thickness under any known name "
            f"(looked for {', '.join(_REALIZED_KEYS)}); trial_index="
            f"{record.get('trial_index')!r}"
        )
    return _view(
        fraction=fraction,
        maximum=maximum,
        realized=realized,
        proposed_mode=proposed_mode,
        proposed_profile=proposed_profile,
        source="ledger record",
    )


def from_parameters(
    parameters: Mapping[str, Any], cfg: Mapping[str, Any]
) -> GradingView:
    """Resolve a raw Ax parameterization through the real geometry code.

    Used for candidates that have no ledger record yet -- surrogate slice
    points, Stage 5 perturbations, v3 preflight.  It calls the same
    :mod:`design13` canonicalization the solver path uses, so a slice point and
    a trial cannot disagree about what a fraction means.
    """

    import design13

    canonical = design13.canonicalize(parameters, cfg)
    raw_mode = parameters.get("interface_mode")
    proposed_profile = str(parameters.get("grading_profile") or ABRUPT)
    if raw_mode is not None:
        proposed_mode = ABRUPT if str(raw_mode) == ABRUPT else GRADED
    else:
        proposed_mode = ABRUPT if proposed_profile == ABRUPT else GRADED
    if proposed_mode == ABRUPT:
        proposed_profile = ABRUPT
    return _view(
        fraction=canonical.get("_proposed_grading_fraction"),
        maximum=canonical.get("_maximum_feasible_grading_nm"),
        realized=float(canonical.get("grading_thickness_nm", 0.0)),
        proposed_mode=proposed_mode,
        proposed_profile=proposed_profile,
        source="design13.canonicalize",
    )


def try_from_record(record: Mapping[str, Any]) -> GradingView | None:
    """:func:`from_record` that returns ``None`` instead of raising.

    For table and plot paths that must skip an unreadable row rather than kill
    a whole reporting run.
    """

    try:
        return from_record(record)
    except (GradingError, TypeError, ValueError):
        return None


def annotate(record: Mapping[str, Any]) -> dict[str, Any]:
    """A copy of ``record`` with every semantic grading field added.

    Existing keys are preserved untouched: ``parameter_grading_thickness_nm``
    stays exactly where downstream code expects it, and correctly continues to
    mean the realized physical width.
    """

    view = try_from_record(record)
    if view is None:
        return dict(record)
    return {**dict(record), **view.as_record()}


def genuine_graded_records(
    records: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Only the trials that actually built a non-zero grade."""

    kept = []
    for record in records:
        view = try_from_record(record)
        if view is not None and view.is_genuinely_graded:
            kept.append(record)
    return kept


def evidence_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """How much genuine evidence exists about grading, per profile.

    The physics audit turns on these numbers: a per-profile ranking drawn from
    one observation per profile is not a ranking, and a statement that "grading
    is worse" needs the graded count to be large enough to support it.
    """

    per_profile: dict[str, int] = {}
    proposed_per_profile: dict[str, int] = {}
    genuine = collapsed = abrupt = unreadable = 0
    for record in records:
        view = try_from_record(record)
        if view is None:
            unreadable += 1
            continue
        if view.proposed_grading_profile != ABRUPT:
            proposed_per_profile[view.proposed_grading_profile] = (
                proposed_per_profile.get(view.proposed_grading_profile, 0) + 1
            )
        if view.is_genuinely_graded:
            genuine += 1
            per_profile[view.realized_grading_profile] = (
                per_profile.get(view.realized_grading_profile, 0) + 1
            )
        else:
            abrupt += 1
            if view.collapsed_to_abrupt:
                collapsed += 1
    return {
        "records": len(records),
        "unreadable_records": unreadable,
        "genuinely_graded_trials": genuine,
        "realized_abrupt_trials": abrupt,
        "graded_proposals_that_collapsed_to_abrupt": collapsed,
        "genuine_trials_per_realized_profile": dict(sorted(per_profile.items())),
        "proposals_per_nominal_profile": dict(sorted(proposed_per_profile.items())),
        "profile_ranking_supportable": bool(
            per_profile and min(per_profile.values()) >= 3 and len(per_profile) >= 2
        ),
        "profile_ranking_caveat": (
            "A per-profile ranking needs several genuinely graded trials of each "
            "profile. Profiles with fewer than three are reported as observations, "
            "never as a ranking."
        ),
    }
