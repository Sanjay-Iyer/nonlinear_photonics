"""The one structure, its states, and the two gates the audit will not waive.

Demo 16F deliberately studies a **single** structure: the paper's ideal-abrupt
7.1 / 1.8 / 2.9 nm coupled pair inside the full 30 nm period, because the
question is a prefactor and ten structures would answer it ten times over. That
structure is the one whose chi2 the paper states outright -- 2340 pm/V at
1550 nm -- so a reproduction either lands on a published number or does not.

Two gates that Demo 16E ran in warning mode are hard failures here:

**Bound states.** The paper's Eq. 2 uses "the first two bound states in the heavy
hole and conduction bands", and says two bound states were guaranteed across the
structures it simulated. Demo 16E recorded ``physical_qc_valid = False`` on all
ten of its cases with one state entering the chi2 sum failing the bound
criterion. That means 16E and the paper were not applying the same state
selection, whatever the energies looked like. A reproduction audit cannot carry
that ambiguity, so ``quasi_bound_state_policy`` is ``fail_case`` here.

**Outer domain.** The absolute chi2 depends directly on ``<psi|z|psi>``, which
converges more slowly with domain size than the eigenvalues do. Energies
agreeing is not evidence the dipoles have converged, so the domain sweep checks
the matrix elements explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import conventions16f as conv
import eq16f

DEMO_ID = conv.DEMO_ID
DEMO_VERSION = conv.DEMO_VERSION

#: Outer AlGaAs half-widths to sweep. The paper's own period barrier is 18.2 nm;
#: the larger two exist to show that answer is converged rather than to replace
#: it.
DOMAIN_SWEEP_NM: tuple[float, ...] = (
    conv.PAPER_PERIOD_BARRIER_NM, 25.0, 35.0,
)

#: What must stop moving before a domain is called converged. Energies are the
#: easy part; the position matrix elements are the ones absolute chi2 rides on,
#: and they are checked to a tighter *relative* budget because a 1% drift in
#: <z> is a 1% drift in chi2 and there are three of them in every term.
DOMAIN_CONVERGENCE_BUDGETS: Mapping[str, float] = {
    "energy_meV": 1.0,
    "position_matrix_relative": 0.01,
}

#: A state entering Eq. 2 may put no more than this much probability in the
#: boundary region. Demo 11's own default; restated here because 16F fails on it
#: rather than warning.
MAX_BOUNDARY_PROBABILITY = 1.0e-3
BOUNDARY_EDGE_FRACTION = 0.05


class Demo16FError(RuntimeError):
    """A reproduction-audit precondition that is violated rather than unusual."""


# ---------------------------------------------------------------------------
# The structure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaperStructure:
    """The paper's layer stack, named the way the paper names it.

    Abrupt interfaces on purpose: 2340 pm/V is the number the paper quotes for
    *ideal* interfaces, so the ideal structure is what the primary target must be
    compared against. The graded variants exist to reach the 1200 / 1363 pm/V
    targets once the abrupt one is settled, and not before.
    """

    thick_well_nm: float = conv.PAPER_THICK_WELL_NM
    tunnel_barrier_nm: float = conv.PAPER_TUNNEL_BARRIER_NM
    thin_well_nm: float = conv.PAPER_THIN_WELL_NM
    period_barrier_nm: float = conv.PAPER_PERIOD_BARRIER_NM
    al_fraction: float = conv.PAPER_AL_FRACTION
    mesh_nm: float = 0.05
    interfaces: str = "abrupt"

    @property
    def total_well_nm(self) -> float:
        return self.thick_well_nm + self.thin_well_nm

    @property
    def period_nm(self) -> float:
        return (
            self.thick_well_nm + self.tunnel_barrier_nm
            + self.thin_well_nm + self.period_barrier_nm
        )

    @property
    def asymmetry_s(self) -> float:
        return (self.thick_well_nm - self.thin_well_nm) / self.total_well_nm

    def validate(self) -> None:
        if abs(self.period_nm - conv.PAPER_PERIOD_NM) > 1.0e-9:
            raise Demo16FError(
                f"period is {self.period_nm} nm; the paper's Sec. 2.2 period is "
                f"{conv.PAPER_PERIOD_NM} nm and N_z is derived from it"
            )
        if abs(self.total_well_nm - conv.PAPER_TOTAL_WELL_NM) > 1.0e-9:
            raise Demo16FError("total GaAs well thickness is not the paper's 10 nm.")

    def as_record(self) -> dict[str, Any]:
        self.validate()
        return {
            "thick_well_nm": self.thick_well_nm,
            "tunnel_barrier_nm": self.tunnel_barrier_nm,
            "thin_well_nm": self.thin_well_nm,
            "period_barrier_nm": self.period_barrier_nm,
            "period_nm": self.period_nm,
            "total_well_nm": self.total_well_nm,
            "asymmetry_s": self.asymmetry_s,
            "aluminium_fraction": self.al_fraction,
            "mesh_nm": self.mesh_nm,
            "interfaces": self.interfaces,
            "source": (
                "Sec. 2.2 and Fig. 1a: 'Each period is 20 nm (10 nm total QW "
                "thickness, 1.8 nm barrier, and 18.2 nm period barrier)' -- the "
                "stated arithmetic sums to 30 nm, which is the period Fig. 1a "
                "labels and the one N_z is taken from"
            ),
        }


PAPER_STRUCTURE = PaperStructure()


# ---------------------------------------------------------------------------
# States from a completed run
# ---------------------------------------------------------------------------


def _trapz(y: np.ndarray, x: np.ndarray) -> float:
    return float(np.trapezoid(np.asarray(y, dtype=float), np.asarray(x, dtype=float)))


def _normalise(envelopes: np.ndarray, z_nm: np.ndarray) -> np.ndarray:
    out = np.empty_like(envelopes, dtype=float)
    for index in range(envelopes.shape[1]):
        norm = _trapz(envelopes[:, index] ** 2, z_nm)
        if not np.isfinite(norm) or norm <= 0:
            raise Demo16FError(f"envelope {index + 1} has zero or non-finite norm.")
        out[:, index] = envelopes[:, index] / np.sqrt(norm)
    return out


def read_envelopes(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``envelopes.csv`` -> (z_nm, electron envelopes, heavy-hole envelopes).

    Written by Demo 11's ``analyse_case``, which Demo 14's ``analyse_real_trial``
    and therefore Demo 16E all route through, so a 16E run directory is a valid
    source and no re-solve is needed to walk the variant ladder.
    """

    path = Path(path)
    if not path.is_file():
        raise Demo16FError(f"no envelope table at {path}")
    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    if data.ndim != 2 or data.shape[1] < 5:
        raise Demo16FError(f"{path} needs z and at least two states per band.")
    electron_columns = [i for i, name in enumerate(header) if name.startswith("psi_e")]
    hole_columns = [i for i, name in enumerate(header) if name.startswith("psi_hh")]
    if len(electron_columns) < 2 or len(hole_columns) < 2:
        raise Demo16FError(
            f"{path} has {len(electron_columns)} electron and {len(hole_columns)} "
            "heavy-hole envelopes; Eq. 2 needs two of each"
        )
    z = np.asarray(data[:, 0], dtype=float)
    return (
        z,
        _normalise(data[:, electron_columns[:2]], z),
        _normalise(data[:, hole_columns[:2]], z),
    )


def matrix_elements(
    z_nm: np.ndarray, electrons: np.ndarray, holes: np.ndarray
) -> dict[str, np.ndarray]:
    """Overlap and position matrices, computed here rather than imported.

    A second implementation of the same integrals the shared ``chi2`` module
    performs. Demo 16E's recorded ``overlap_e1_hh1``, ``z_e1_e2_nm`` and friends
    are the first implementation; :func:`state_set_from_run` compares them, so a
    transcription error in either one is caught rather than assumed away.
    """

    def overlaps(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.array([
            [_trapz(a[:, i] * b[:, j], z_nm) for j in range(b.shape[1])]
            for i in range(a.shape[1])
        ])

    def positions(band: np.ndarray) -> np.ndarray:
        return np.array([
            [_trapz(band[:, i] * z_nm * band[:, j], z_nm)
             for j in range(band.shape[1])]
            for i in range(band.shape[1])
        ])

    return {
        "overlap_eh": overlaps(electrons, holes),
        "z_e_nm": positions(electrons),
        "z_h_nm": positions(holes),
        "gram_electron": overlaps(electrons, electrons),
        "gram_hole": overlaps(holes, holes),
    }


def orthonormality_error(gram: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(gram) - np.eye(gram.shape[0]))))


def state_set_from_run(
    parsed_dir: Path,
    *,
    electron_energies_eV: Sequence[float],
    hole_energies_eV: Sequence[float],
    r_e_hh_nm: float = 0.751,
    orthonormality_tolerance: float = 1.0e-3,
) -> tuple[eq16f.StateSet, dict[str, Any]]:
    """Rebuild the Eq. 2 inputs from a completed run, with a provenance record.

    Returns the state set and a diagnostics dict. Orthonormality is checked
    before anything else because Eq. 2 contains *diagonal* position matrix
    elements, whose individual values depend on where z = 0 sits; that dependence
    cancels between the two terms only if the envelopes within each band are
    orthonormal.
    """

    z_nm, electrons, holes = read_envelopes(Path(parsed_dir) / "envelopes.csv")
    elements = matrix_elements(z_nm, electrons, holes)
    errors = {
        "electron": orthonormality_error(elements["gram_electron"]),
        "heavy_hole": orthonormality_error(elements["gram_hole"]),
    }
    if max(errors.values()) > orthonormality_tolerance:
        raise Demo16FError(
            "envelopes are not orthonormal within "
            f"{orthonormality_tolerance}: {errors}. Eq. 2's diagonal position "
            "matrix elements would then depend on the arbitrary origin of z."
        )
    states = eq16f.StateSet(
        electron_energies_eV=np.asarray(electron_energies_eV, dtype=float)[:2],
        hole_energies_eV=np.asarray(hole_energies_eV, dtype=float)[:2],
        overlap_eh=elements["overlap_eh"][:2, :2],
        z_e_nm=elements["z_e_nm"][:2, :2],
        z_h_nm=elements["z_h_nm"][:2, :2],
        r_e_hh_nm=float(r_e_hh_nm),
    )
    diagnostics = {
        "source": str(Path(parsed_dir) / "envelopes.csv"),
        "grid_points": int(z_nm.size),
        "domain_nm": [float(z_nm[0]), float(z_nm[-1])],
        "orthonormality_error": errors,
        "overlap_eh": elements["overlap_eh"][:2, :2].tolist(),
        "z_e_nm": elements["z_e_nm"][:2, :2].tolist(),
        "z_h_nm": elements["z_h_nm"][:2, :2].tolist(),
        "transitions_eV": states.transitions_eV.tolist(),
    }
    return states, diagnostics


def cross_check_recorded(
    diagnostics: Mapping[str, Any], recorded: Mapping[str, Any],
    *, tolerance: float = 1.0e-6,
) -> dict[str, Any]:
    """Compare our matrix elements with the ones the original run recorded."""

    overlap = np.asarray(diagnostics["overlap_eh"], dtype=float)
    z_e = np.asarray(diagnostics["z_e_nm"], dtype=float)
    z_h = np.asarray(diagnostics["z_h_nm"], dtype=float)
    pairs = {
        "overlap_e1_hh1": (overlap[0, 0], recorded.get("overlap_e1_hh1")),
        "overlap_e2_hh2": (overlap[1, 1], recorded.get("overlap_e2_hh2")),
        "z_e1_e1_nm": (z_e[0, 0], recorded.get("z_e1_e1_nm")),
        "z_e1_e2_nm": (z_e[0, 1], recorded.get("z_e1_e2_nm")),
        "z_e2_e2_nm": (z_e[1, 1], recorded.get("z_e2_e2_nm")),
        "z_hh1_hh1_nm": (z_h[0, 0], recorded.get("z_hh1_hh1_nm")),
        "z_hh1_hh2_nm": (z_h[0, 1], recorded.get("z_hh1_hh2_nm")),
        "z_hh2_hh2_nm": (z_h[1, 1], recorded.get("z_hh2_hh2_nm")),
    }
    rows = []
    for name, (ours, theirs) in pairs.items():
        if theirs is None:
            rows.append({"quantity": name, "ours": float(ours),
                         "recorded": None, "agrees": None})
            continue
        difference = abs(float(ours) - float(theirs))
        scale = max(abs(float(ours)), abs(float(theirs)), 1.0e-12)
        rows.append({
            "quantity": name, "ours": float(ours), "recorded": float(theirs),
            "absolute_difference": difference,
            "relative_difference": difference / scale,
            "agrees": bool(difference / scale <= tolerance),
        })
    compared = [row for row in rows if row["agrees"] is not None]
    return {
        "tolerance": tolerance,
        "comparisons": rows,
        "quantities_compared": len(compared),
        "all_agree": all(row["agrees"] for row in compared) if compared else None,
    }


# ---------------------------------------------------------------------------
# Gate 1: bound states, strictly
# ---------------------------------------------------------------------------


#: The four states Eq. 2 sums over. All four must be found and all four must
#: pass before the gate certifies anything.
REQUIRED_STATES: tuple[str, ...] = ("E1", "E2", "HH1", "HH2")

#: Demo 11 records a band name and a 1-based index within that band; Eq. 2 and
#: this audit speak in E1/E2/HH1/HH2. One mapping, in one place.
_BAND_PREFIX: Mapping[str, str] = {"electron": "E", "heavy_hole": "HH"}


def _state_label(record: Mapping[str, Any]) -> str | None:
    prefix = _BAND_PREFIX.get(str(record.get("band")))
    index = record.get("state")
    if prefix is None or index is None:
        return None
    try:
        return f"{prefix}{int(index)}"
    except (TypeError, ValueError):
        return None


def _state_verdict(record: Mapping[str, Any]) -> dict[str, Any]:
    """One state's bound-state verdict, keeping "not tested" distinct from "passed".

    The distinction is not pedantry. Demo 11 applies the full test to electrons
    -- energy below the enclosing barrier maximum *and* enough probability in
    the wells -- but heavy holes are solved without a matching valence
    barrier-edge profile, so only the probability half runs. A hole that
    "passes" has passed a weaker test, and the record says which.
    """

    passes = record.get("passes_bound_criterion")
    boundary_ok = record.get("boundary_probability_within_threshold")
    if passes is None or boundary_ok is None:
        verdict = "NOT TESTED"
        passed: bool | None = None
    elif bool(passes) and bool(boundary_ok):
        verdict = "BOUND"
        passed = True
    else:
        verdict = "NOT BOUND"
        passed = False
    return {
        "verdict": verdict,
        "passed": passed,
        "energy_eV": record.get("energy_eV"),
        "passes_bound_criterion": passes,
        "bound_criterion_detail": record.get("bound_criterion_detail"),
        "boundary_probability": record.get("boundary_probability"),
        "left_boundary_probability": record.get("left_boundary_probability"),
        "right_boundary_probability": record.get("right_boundary_probability"),
        "boundary_probability_within_threshold": boundary_ok,
        "within_chi2_state_window": record.get("within_chi2_state_window"),
        "included_in_chi2": record.get("included_in_chi2"),
        "exclusion_reason": record.get("exclusion_reason") or "",
        "energy_half_of_test_applied": str(record.get("band")) == "electron",
    }


def bound_state_gate(parsed_dir: Path) -> dict[str, Any]:
    """The strict bound-state verdict for E1, E2, HH1 and HH2 individually.

    Reads the per-state table Demo 11 writes. Demo 16E aggregated it to a count;
    the audit needs the *identity* of the failing state, because "the domain is
    too short", "the outer barrier is too thin" and "this state is genuinely
    quasi-bound" are different defects with different fixes and a count cannot
    tell them apart.

    **This gate fails closed.** An earlier version of it filtered on a key name
    (``in_chi2_sum``) that this schema does not use, so it matched nothing, found
    no failures, and reported ``passed = True`` while printing an empty state
    list -- the worst possible outcome, a silent pass. Certification now requires
    all four of :data:`REQUIRED_STATES` to be present *and* to pass; anything
    else returns ``passed`` as ``None`` with a reason, and ``None`` is never
    treated as success by any caller.
    """

    path = Path(parsed_dir) / "quasi_bound_states.json"
    if not path.is_file():
        return {
            "available": False,
            "path": str(path),
            "passed": None,
            "reason": (
                "no per-state bound-state table in this run; re-run the "
                "producing demo so the state-resolved diagnosis exists"
            ),
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records") or []
    by_state: dict[str, dict[str, Any]] = {}
    unrecognised = 0
    for record in records:
        label = _state_label(record)
        if label is None:
            unrecognised += 1
            continue
        if label in REQUIRED_STATES:
            by_state[label] = _state_verdict(record)

    missing = [label for label in REQUIRED_STATES if label not in by_state]
    failing = [
        label for label, row in by_state.items() if row["passed"] is False
    ]
    untested = [
        label for label, row in by_state.items() if row["passed"] is None
    ]
    outside_window = [
        label for label, row in by_state.items()
        if row["within_chi2_state_window"] is False
    ]

    if unrecognised and not by_state:
        passed: bool | None = None
        reason = (
            f"{unrecognised} record(s) present but none carried a recognised "
            "band/state pair. The table schema is not the one this gate parses, "
            "so no verdict can be given -- which is NOT a pass."
        )
    elif missing:
        passed = None
        reason = (
            f"no record for {missing}; Eq. 2 sums over all four of "
            f"{list(REQUIRED_STATES)}, so a missing state means the gate cannot "
            "certify the sum. An incomplete table is not a pass."
        )
    elif untested:
        passed = None
        reason = (
            f"{untested} were not tested (Demo 11 could not apply the criterion). "
            "An untested state is not a passed state."
        )
    elif failing:
        passed = False
        reason = (
            f"{failing} entering Eq. 2 fail the bound-state criterion; the paper "
            "uses bound states only"
        )
    else:
        passed = True
        reason = "all four states entering Eq. 2 are bound"

    return {
        "available": True,
        "path": str(path),
        "policy_required": "fail_case",
        "policy_in_source_run": payload.get("policy"),
        "strict_verdict_applied_by": DEMO_ID,
        "maximum_boundary_probability": payload.get(
            "maximum_boundary_probability", MAX_BOUNDARY_PROBABILITY
        ),
        "boundary_edge_fraction": payload.get(
            "boundary_edge_fraction", BOUNDARY_EDGE_FRACTION
        ),
        "required_states": list(REQUIRED_STATES),
        "records_seen": len(records),
        "records_unrecognised": unrecognised,
        "by_state": by_state,
        "states_found": sorted(by_state),
        "missing_states": missing,
        "failing_states": failing,
        "untested_states": untested,
        "states_outside_chi2_window": outside_window,
        "failing_count": len(failing),
        "source_run_failing_in_sum_count": payload.get("failing_in_sum_count"),
        "source_run_failing_reasons": payload.get("failing_in_sum_reasons") or [],
        "passed": passed,
        "reason": reason,
        "interpretation": (
            "Methods Sec. 5.1 states the first two bound states of each band are "
            "used and that two bound states were guaranteed across the simulated "
            "structures. A failing state means this calculation and the paper are "
            "not applying the same selection, independent of how close the "
            "energies look."
        ),
    }


# ---------------------------------------------------------------------------
# Gate 2: outer-domain convergence
# ---------------------------------------------------------------------------


def domain_convergence(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Have the energies AND the position matrix elements stopped moving?

    ``entries`` are ``{"outer_barrier_nm": float, "states": StateSet}`` in
    increasing domain size. Reported separately for energies and dipoles because
    the interesting failure -- and the one that would explain a correct spectral
    position with a wrong amplitude -- is energies converging while ``<z>`` has
    not.
    """

    ordered = sorted(entries, key=lambda row: float(row["outer_barrier_nm"]))
    if len(ordered) < 2:
        return {"converged": None, "reason": "at least two domains are needed"}

    reference = ordered[-1]["states"]
    rows = []
    for entry in ordered:
        states: eq16f.StateSet = entry["states"]
        energy_shifts = {
            f"{label}_meV": float(
                (np.asarray(values)[index] - np.asarray(ref_values)[index]) * 1000.0
            )
            for label, index, values, ref_values in (
                ("E1", 0, states.electron_energies_eV, reference.electron_energies_eV),
                ("E2", 1, states.electron_energies_eV, reference.electron_energies_eV),
                ("HH1", 0, states.hole_energies_eV, reference.hole_energies_eV),
                ("HH2", 1, states.hole_energies_eV, reference.hole_energies_eV),
            )
        }
        dipole_shifts = {}
        for name, ours, theirs in (
            ("z_e1_e2", states.z_e_nm[0, 1], reference.z_e_nm[0, 1]),
            ("z_e2_e2_minus_e1_e1",
             states.z_e_nm[1, 1] - states.z_e_nm[0, 0],
             reference.z_e_nm[1, 1] - reference.z_e_nm[0, 0]),
            ("z_hh1_hh2", states.z_h_nm[0, 1], reference.z_h_nm[0, 1]),
            ("z_hh2_hh2_minus_hh1_hh1",
             states.z_h_nm[1, 1] - states.z_h_nm[0, 0],
             reference.z_h_nm[1, 1] - reference.z_h_nm[0, 0]),
        ):
            scale = max(abs(float(theirs)), 1.0e-9)
            dipole_shifts[name] = float(abs(float(ours) - float(theirs)) / scale)
        rows.append({
            "outer_barrier_nm": float(entry["outer_barrier_nm"]),
            "energy_shift_vs_largest": energy_shifts,
            "dipole_relative_shift_vs_largest": dipole_shifts,
            "max_energy_shift_meV": max(abs(v) for v in energy_shifts.values()),
            "max_dipole_relative_shift": max(dipole_shifts.values()),
        })

    paper_row = next(
        (row for row in rows
         if abs(row["outer_barrier_nm"] - conv.PAPER_PERIOD_BARRIER_NM) < 1.0e-9),
        None,
    )
    energies_ok = (
        paper_row is not None
        and paper_row["max_energy_shift_meV"]
        <= DOMAIN_CONVERGENCE_BUDGETS["energy_meV"]
    )
    dipoles_ok = (
        paper_row is not None
        and paper_row["max_dipole_relative_shift"]
        <= DOMAIN_CONVERGENCE_BUDGETS["position_matrix_relative"]
    )
    return {
        "budgets": dict(DOMAIN_CONVERGENCE_BUDGETS),
        "reference_outer_barrier_nm": float(ordered[-1]["outer_barrier_nm"]),
        "rows": rows,
        "paper_domain_energies_converged": energies_ok,
        "paper_domain_dipoles_converged": dipoles_ok,
        "converged": bool(energies_ok and dipoles_ok),
        "diagnostic": (
            None if energies_ok == dipoles_ok else
            "energies converged but position matrix elements did not: absolute "
            "chi2 rides on <psi|z|psi>, so this is exactly the pattern that "
            "produces a correct resonance position with a wrong amplitude"
        ),
    }
