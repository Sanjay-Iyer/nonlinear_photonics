"""Physical-state tracking for scattered Bayesian-optimization trials.

Demos 11 and 12 track states along a *sweep*: neighbouring points differ by one
small step, so "the previous point" is well defined.  A Bayesian optimizer does
not produce a sweep.  It jumps around the design space, and the trial evaluated
just before this one may be nowhere near it.

So Demo 13 keeps the same physics -- normalized envelope overlap, one-to-one
assignment, sign alignment, energy continuity as a secondary criterion, best and
second-best overlap, an explicit confidence -- and changes only what "previous"
means: each new design is assigned against its **nearest already-completed
neighbour in normalized parameter space**, not against the previous trial index
and never against raw energy order.

Why this matters for the optimizer
==================================

Demo 11's 2026-07-31 licensed run produced an 8.5x jump in chi(2) across one
asymmetry step, caused by two states swapping which one is "state 2" through an
avoided crossing.  A discontinuity like that is exactly what an acquisition
function chases: it looks like an enormous local gain.  Tracking states by
overlap, and refusing the trial when the assignment is ambiguous, is what stops
Demo 13 from optimizing a labelling artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
DEMO11_DIR = DEMO_DIR.parent / "11_paper_validation_interband_chi2_acqw"
for _path in (str(SHARED), str(DEMO11_DIR), str(DEMO_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from demo_workflow import DemoError  # noqa: E402

import tracking11  # noqa: E402

import design13  # noqa: E402

BANDS: tuple[str, ...] = ("electron", "heavy_hole")

#: Where each band's real solver energies are found in a Demo 11 observables
#: mapping. These are the only accepted sources in scientific mode.
BAND_ENERGY_KEY: Mapping[str, str] = {
    "electron": "electron_energies_eV",
    "heavy_hole": "heavy_hole_energies_eV",
}

#: Per-band on-disk fallback written by ``demo11.analyse_case``.
BAND_ENERGY_TABLE: Mapping[str, str] = {
    "electron": "electron_states.csv",
    "heavy_hole": "heavy_hole_states.csv",
}

#: The four public provenance labels.  Keep these short and stable: they are
#: written into trial, tracking and anchor records and are part of the audit
#: vocabulary used by the guides.
SOLVER_ENERGY_LABEL = "solver"
HISTORICAL_ENERGY_LABEL = "parsed historical output"
SYNTHETIC_ENERGY_LABEL = "synthetic test"
UNAVAILABLE_ENERGY_LABEL = "unavailable"


class StateEnergyError(DemoError):
    """Real solver energies were required for state tracking and not found.

    Raised rather than substituting an index sequence.  The substitution is not
    neutral: :func:`tracking11._energy_penalty` normalizes the energy gap by the
    spread of the energies it is given, so feeding ``np.arange(n)`` to *both*
    sides of a comparison produces a penalty matrix that is exactly zero on the
    diagonal and grows with ``|i - j|``.  That is an **identity-preferring
    prior**, not an absence of information: at the configured
    ``energy_continuity_weight`` of 0.05 a genuine adjacent-state swap has to
    beat the identity assignment by an overlap margin of 0.0167 before the
    tracker will report it.  Suppressing exactly the reordering this module
    exists to detect is worse than refusing to run.
    """


@dataclass(frozen=True)
class TrialStates:
    """Everything the tracker needs from one completed trial."""

    trial_index: int
    parameters: Mapping[str, Any]
    z_nm: np.ndarray
    electron_energies_eV: np.ndarray
    electron_envelopes: np.ndarray
    heavy_hole_energies_eV: np.ndarray
    heavy_hole_envelopes: np.ndarray
    #: Bands whose energies are an index sequence rather than solver output.
    #: Empty for every scientific trial; non-empty only under an explicit
    #: unit-test opt-in, and propagated into the tracking record so no reader can
    #: mistake such a run for a physical one.
    synthetic_energy_bands: tuple[str, ...] = field(default=())
    #: Per-band source. Older hand-constructed test fixtures leave this empty;
    #: those retain the pre-existing assumption that their supplied arrays are
    #: solver-like data unless ``synthetic_energy_bands`` says otherwise.
    energy_provenance_by_band: Mapping[str, str] = field(default_factory=dict)

    def band(self, name: str) -> tuple[np.ndarray, np.ndarray]:
        if name == "electron":
            return self.electron_energies_eV, self.electron_envelopes
        return self.heavy_hole_energies_eV, self.heavy_hole_envelopes


def _settings(cfg: Mapping[str, Any]) -> dict[str, float]:
    tracking = cfg.get("state_tracking") or {}
    return {
        "minimum_confidence": float(tracking.get("minimum_confidence", 0.60)),
        "minimum_margin": float(tracking.get("minimum_assignment_margin", 0.15)),
        "energy_continuity_weight": float(tracking.get("energy_continuity_weight", 0.05)),
    }


def track_against(
    current: TrialStates,
    reference: TrialStates | None,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    """Assign ``current``'s states to ``reference``'s, band by band.

    With no reference -- the very first completed trial -- the labelling is
    *defined* here.  That is reported as an anchor with confidence 1.0 and the
    method recorded, so a downstream reader can tell "nothing to compare against"
    apart from "compared and matched perfectly".
    """

    settings = _settings(cfg)
    # Any band whose energies were faked on either side of the comparison taints
    # the whole record: the assignment cost mixes both points' energies.
    synthetic_bands = tuple(
        sorted(
            set(current.synthetic_energy_bands)
            | set(() if reference is None else reference.synthetic_energy_bands)
        )
    )
    provenance_by_band = {
        band: _combined_energy_provenance(current, reference, band)
        for band in BANDS
    }
    provenance = _combined_provenance(provenance_by_band.values())
    record: dict[str, Any] = {
        "trial_index": current.trial_index,
        "reference_trial": None if reference is None else reference.trial_index,
        "method": "anchor_defines_labelling"
        if reference is None
        else "nearest_neighbour_overlap_assignment",
        "rows": [],
        "diagnostics": {},
        "ambiguous": False,
        "synthetic_energy_bands": list(synthetic_bands),
        "energy_provenance": provenance,
        "energy_provenance_by_band": provenance_by_band,
    }
    if reference is None:
        record.update(
            {
                "state_tracking_confidence": 1.0,
                "assignment_margin": 1.0,
                "tracked_labels": {
                    band: list(range(1, int(current.band(band)[0].size) + 1))
                    for band in BANDS
                },
                "raw_indices": {
                    band: list(range(1, int(current.band(band)[0].size) + 1))
                    for band in BANDS
                },
                "design_distance": 0.0,
                "note": "first completed trial; its raw solver order defines the labels",
            }
        )
        return record

    distance = design13.design_distance(current.parameters, reference.parameters, cfg)
    confidences: list[float] = []
    margins: list[float] = []
    tracked_labels: dict[str, list[int]] = {}
    raw_indices: dict[str, list[int]] = {}
    ambiguous = False
    for band in BANDS:
        reference_energies, reference_envelopes = reference.band(band)
        current_energies, current_envelopes = current.band(band)
        points = [
            tracking11.SweepPoint(
                case_id=f"t{reference.trial_index:04d}",
                sweep_value=0.0,
                z_nm=np.asarray(reference.z_nm, dtype=float),
                energies_eV=np.asarray(reference_energies, dtype=float),
                envelopes=np.asarray(reference_envelopes, dtype=float),
            ),
            tracking11.SweepPoint(
                case_id=f"t{current.trial_index:04d}",
                # A positive sweep value keeps the reference first in the chain;
                # the number itself is the normalized design distance, which is
                # what "how far did we jump" means for scattered trials.
                sweep_value=max(float(distance), 1e-9),
                z_nm=np.asarray(current.z_nm, dtype=float),
                energies_eV=np.asarray(current_energies, dtype=float),
                envelopes=np.asarray(current_envelopes, dtype=float),
            ),
        ]
        states, diagnostics = tracking11.track_band(
            points,
            band=band,
            minimum_confidence=settings["minimum_confidence"],
            minimum_margin=settings["minimum_margin"],
            energy_continuity_weight=settings["energy_continuity_weight"],
        )
        rows = [
            {
                **state.row(),
                "trial_index": current.trial_index,
                "reference_trial": reference.trial_index,
                "design_distance": float(distance),
            }
            for state in states
            if state.case_id == f"t{current.trial_index:04d}"
        ]
        record["rows"].extend(rows)
        record["diagnostics"][band] = diagnostics
        tracked_labels[band] = [int(row["tracked_label"]) for row in rows]
        raw_indices[band] = [int(row["raw_index"]) for row in rows]
        for row in rows:
            if row.get("overlap_with_previous") is not None:
                confidences.append(float(row["overlap_with_previous"]))
            if row.get("assignment_margin") is not None:
                margins.append(float(row["assignment_margin"]))
            ambiguous = ambiguous or bool(row.get("ambiguous"))

    record.update(
        {
            "state_tracking_confidence": min(confidences) if confidences else None,
            "assignment_margin": min(margins) if margins else None,
            "tracked_labels": tracked_labels,
            "raw_indices": raw_indices,
            "design_distance": float(distance),
            "ambiguous": ambiguous,
            "label_reordering_detected": any(
                tracked_labels[band] != raw_indices[band] for band in BANDS
            ),
        }
    )
    return record


def _state_energy_provenance(states: TrialStates, band: str) -> str:
    if band in states.synthetic_energy_bands:
        return SYNTHETIC_ENERGY_LABEL
    return str(states.energy_provenance_by_band.get(band) or SOLVER_ENERGY_LABEL)


def _combined_provenance(values: Sequence[str]) -> str:
    sources = {str(value) for value in values}
    for label in (
        UNAVAILABLE_ENERGY_LABEL,
        SYNTHETIC_ENERGY_LABEL,
        HISTORICAL_ENERGY_LABEL,
        SOLVER_ENERGY_LABEL,
    ):
        if label in sources:
            return label
    return UNAVAILABLE_ENERGY_LABEL


def _combined_energy_provenance(
    current: TrialStates, reference: TrialStates | None, band: str
) -> str:
    values = [_state_energy_provenance(current, band)]
    if reference is not None:
        values.append(_state_energy_provenance(reference, band))
    return _combined_provenance(values)


def choose_reference(
    current_parameters: Mapping[str, Any],
    history: Sequence[TrialStates],
    cfg: Mapping[str, Any],
) -> TrialStates | None:
    """The completed trial whose design is closest to this one."""

    if not history:
        return None
    match = design13.nearest_neighbour(
        current_parameters, [point.parameters for point in history], cfg
    )
    if match is None:
        return None
    index, _ = match
    return history[index]


def track_sequence(
    points: Sequence[TrialStates], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Track a whole experiment: each trial against its nearest predecessor.

    Trials are processed in the order they completed, so a trial is only ever
    matched against designs that already existed when it ran.  Re-running this
    over a finished experiment therefore reproduces exactly what the closed loop
    saw, which is what makes the recorded confidences auditable.
    """

    ordered = sorted(points, key=lambda point: point.trial_index)
    history: list[TrialStates] = []
    records: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for point in ordered:
        reference = choose_reference(point.parameters, history, cfg)
        record = track_against(point, reference, cfg)
        records.append(record)
        rows.extend(record["rows"])
        history.append(point)
    confidences = [
        float(record["state_tracking_confidence"])
        for record in records
        if record.get("state_tracking_confidence") is not None
    ]
    synthetic_bands = sorted(
        {
            str(band)
            for record in records
            for band in (record.get("synthetic_energy_bands") or ())
        }
    )
    provenances = [
        str(record.get("energy_provenance") or UNAVAILABLE_ENERGY_LABEL)
        for record in records
    ]
    return {
        "records": records,
        "rows": rows,
        "minimum_confidence": min(confidences) if confidences else None,
        "synthetic_energy_bands": synthetic_bands,
        "energy_provenance": _combined_provenance(provenances),
        "ambiguous_trials": [
            int(record["trial_index"]) for record in records if record.get("ambiguous")
        ],
        "method": str(
            (cfg.get("state_tracking") or {}).get(
                "method", "nearest_neighbour_overlap_assignment"
            )
        ),
        "tracked_trials": len(records),
    }


def load_trial_states(
    trial_index: int,
    parameters: Mapping[str, Any],
    extracted_dir: Path,
    *,
    observables: Mapping[str, Any] | None = None,
    allow_synthetic_energies: bool = False,
) -> TrialStates | None:
    """Read one trial's envelopes and its **real** state energies.

    ``envelopes.csv`` is written by ``demo11.analyse_case`` as
    ``z_nm, psi_e1..psi_eN, psi_hh1..psi_hhM``. Reading it back rather than
    re-parsing the solver output keeps the tracker on exactly the arrays the
    chi(2) evaluation used.

    Energies come from ``observables`` when the caller has them in hand -- the
    live loop always does, because ``demo11.analyse_case`` returns
    ``electron_energies_eV`` and ``heavy_hole_energies_eV`` -- and otherwise
    from the per-band state table on disk.  If neither supplies a band's
    energies the trial is refused with :class:`StateEnergyError` rather than
    tracked against an index sequence; see that class for why the substitution
    is not neutral.

    ``allow_synthetic_energies`` exists **only** for unit tests that exercise
    the assignment plumbing without a solver.  It labels every band it fakes,
    and that label is carried into the tracking record and into the trial
    record, so a synthetic run can never be read as a physical one.

    Returns ``None`` when there are no envelopes to track at all, which is the
    "this trial produced no wavefunctions" case and is distinct from "this trial
    produced wavefunctions whose energies I refuse to invent".
    """

    path = Path(extracted_dir) / "envelopes.csv"
    if not path.is_file():
        return None
    header = path.read_text(encoding="utf-8").splitlines()[:1]
    if not header:
        return None
    names = [name.strip() for name in header[0].split(",")]
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    if data.ndim != 2 or data.shape[0] < 2:
        return None
    electron_columns = [i for i, name in enumerate(names) if name.startswith("psi_e")]
    hole_columns = [i for i, name in enumerate(names) if name.startswith("psi_hh")]
    if not electron_columns or not hole_columns:
        return None

    synthetic: list[str] = []
    energies: dict[str, np.ndarray] = {}
    provenance_by_band: dict[str, str] = {}
    for band, count in (
        ("electron", len(electron_columns)),
        ("heavy_hole", len(hole_columns)),
    ):
        values, provenance = _band_energies(
            band,
            count,
            observables=observables,
            extracted_dir=Path(extracted_dir),
            allow_synthetic_energies=allow_synthetic_energies,
        )
        if values is None:
            synthetic.append(band)
            values = np.arange(count, dtype=float)
        energies[band] = values
        provenance_by_band[band] = provenance

    return TrialStates(
        trial_index=int(trial_index),
        parameters=dict(parameters),
        z_nm=data[:, 0],
        electron_energies_eV=energies["electron"],
        electron_envelopes=data[:, electron_columns],
        heavy_hole_energies_eV=energies["heavy_hole"],
        heavy_hole_envelopes=data[:, hole_columns],
        synthetic_energy_bands=tuple(synthetic),
        energy_provenance_by_band=provenance_by_band,
    )


def _band_energies(
    band: str,
    count: int,
    *,
    observables: Mapping[str, Any] | None,
    extracted_dir: Path,
    allow_synthetic_energies: bool,
) -> tuple[np.ndarray | None, str]:
    """One band's solver energies, or ``None`` to signal a labelled fake.

    Order is preserved exactly as the solver reported it: electron energies
    ascend and heavy-hole energies descend, and neither is re-sorted here.  The
    assignment cost only ever uses ``|E_i - E_j|`` normalized by the spread, so
    a descending band is handled correctly and re-sorting would destroy the
    correspondence between an energy and its envelope column.
    """

    values = _energies_from_observables(observables, band, count)
    if values is not None:
        return values, SOLVER_ENERGY_LABEL
    values = _energies_from_state_table(
        extracted_dir / BAND_ENERGY_TABLE[band], count
    )
    if values is not None:
        return values, HISTORICAL_ENERGY_LABEL
    if allow_synthetic_energies:
        return None, SYNTHETIC_ENERGY_LABEL
    raise StateEnergyError(
        f"state tracking needs real {band} energies for this trial and found "
        f"neither observables[{BAND_ENERGY_KEY[band]!r}] with {count} finite "
        f"values nor {extracted_dir / BAND_ENERGY_TABLE[band]}. Refusing to "
        "track against an index sequence: that biases the assignment toward the "
        "identity permutation and hides the state reordering this check exists "
        "to find. Pass allow_synthetic_energies=True only from a unit test."
    )


def _finite_energies(values: Any, count: int) -> np.ndarray | None:
    """``count`` finite floats from a sequence, or ``None`` if unavailable.

    A short, non-numeric or non-finite band is rejected outright rather than
    padded. Padding would silently change which envelope column an energy
    belongs to, which is the same class of error as fabricating the energies.
    """

    if not isinstance(values, (list, tuple, np.ndarray)):
        return None
    numbers: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(number):
            return None
        numbers.append(number)
    if len(numbers) < count:
        return None
    return np.asarray(numbers[:count], dtype=float)


def _energies_from_observables(
    observables: Mapping[str, Any] | None, band: str, count: int
) -> np.ndarray | None:
    if not isinstance(observables, Mapping):
        return None
    return _finite_energies(observables.get(BAND_ENERGY_KEY[band]), count)


def _energies_from_state_table(path: Path, count: int) -> np.ndarray | None:
    """One band's energies from its state table, or ``None`` when unusable.

    Returns ``None`` -- never an index sequence -- so the caller decides what a
    missing table means. Only :func:`_band_energies` may make that decision, and
    in scientific mode it raises.
    """

    if not path.is_file():
        return None
    import csv

    values: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                values.append(float(row["energy_eV"]))
            except (KeyError, TypeError, ValueError):
                continue
    return _finite_energies(values, count)
