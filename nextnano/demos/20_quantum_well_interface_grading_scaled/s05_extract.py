"""Stage 05 - get solver-derived quantum data into a single standard shape.

Everything downstream of here (chi2, QC, plots, reports) consumes exactly one
type: :class:`s06_chi2.CaseStates`. This module is the only place that knows
where those numbers physically came from, and it offers two sources:

``master_table``
    Read the electron/hole energies and the O / z matrices back out of a Demo 19
    or Demo 20 master results CSV. Those columns were written by a licensed
    solver run, so this is *real solver data being re-postprocessed*, not
    synthetic input. It needs no licence, which is what makes the whole chi2 and
    plotting pipeline testable on a machine with no nextnano++.

``nextnano_output``
    Parse a raw licensed run directory. This delegates to the already-validated
    Demo 11 / Demo 14 parsing chain (``demo14.analyse_real_trial``), which is
    the same parser Demos 12, 13, 14 and 19 all use, so a Demo 20 case and a
    Demo 19 case of the same structure are the same calculation with the same
    provenance.

NOTHING HERE FABRICATES SOLVER OUTPUT. If neither source is available the stage
raises and says so; it never falls back to a placeholder number.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import s06_chi2 as chi2mod

SOURCE_MASTER_TABLE = "master_table"
SOURCE_NEXTNANO_OUTPUT = "nextnano_output"

#: Column names in the Demo 19 master table, for ``max_states_per_band = 2``.
#: Extending the sum to three states needs the corresponding *_13/_31/... columns
#: to exist in the source table; :func:`_matrix_from_row` says so explicitly
#: rather than silently zero-filling.
ENERGY_COLUMNS = {
    "electron": ("E1_eV", "E2_eV"),
    "hole": ("HH1_eV", "HH2_eV"),
}
OVERLAP_COLUMNS = (("O11", "O12"), ("O21", "O22"))
ELECTRON_POSITION_COLUMNS = (("z_e11_nm", "z_e12_nm"), ("z_e21_nm", "z_e22_nm"))
HOLE_POSITION_COLUMNS = (("z_hh11_nm", "z_hh12_nm"), ("z_hh21_nm", "z_hh22_nm"))

TRUTHY = {"true", "1", "yes", "t"}


class Extract20Error(ValueError):
    """The requested solver data could not be obtained."""


@dataclass(frozen=True)
class ExtractedCase:
    """One case's quantum data plus the status flags that came with it.

    ``solver_pass`` and ``physical_valid`` are carried through as *separate*
    concepts and are never merged: a zero solver return code says the process
    finished, not that the physics is valid.
    """

    case_id: str
    states: chi2mod.CaseStates | None
    solver_pass: bool
    physical_valid: bool
    source: str
    source_detail: str
    failure_stage: str = ""
    failure_reason: str = ""
    extras: Mapping[str, Any] = None  # type: ignore[assignment]

    @property
    def has_states(self) -> bool:
        return self.states is not None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in TRUTHY


def _as_float(value: Any) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        return float("nan")
    return float(value)


def _matrix_from_row(
    row: Mapping[str, Any], columns: Sequence[Sequence[str]], label: str
) -> np.ndarray:
    missing = [name for line in columns for name in line if name not in row]
    if missing:
        raise Extract20Error(
            f"{label}: the source table has no column(s) {missing}. Demo 20 reads "
            "the matrix elements it needs; it does not reconstruct them."
        )
    matrix = np.asarray(
        [[_as_float(row[name]) for name in line] for line in columns], dtype=float
    )
    if not np.all(np.isfinite(matrix)):
        raise Extract20Error(f"{label}: contains a blank or non-finite entry.")
    return matrix


def from_master_table(
    path: Path, *, max_states_per_band: int = 2
) -> dict[str, ExtractedCase]:
    """Read solver-derived states back out of a master results CSV.

    Rows whose matrix-element columns are blank (a pending, never-solved run)
    come back with ``states=None`` and their recorded failure text intact, so a
    pending Demo 19 table is reported as pending rather than silently skipped.
    """

    path = Path(path)
    if not path.is_file():
        raise Extract20Error(
            f"analysis.master_table does not exist: {path}\n"
            "Point analysis.master_table at a results CSV that contains the "
            "solver's energies and matrix elements, or run with "
            "analysis.source: nextnano_output on the licensed machine."
        )
    if int(max_states_per_band) != 2:
        raise Extract20Error(
            "the master-table source carries two states per band (E1/E2, "
            f"HH1/HH2); max_states_per_band={max_states_per_band} needs a raw "
            "solver run parsed through analysis.source: nextnano_output."
        )
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise Extract20Error(f"{path} has no data rows.")

    extracted: dict[str, ExtractedCase] = {}
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        if not case_id:
            continue
        solver_pass = _as_bool(row.get("solver_pass"))
        physical_valid = _as_bool(row.get("physical_valid"))
        states: chi2mod.CaseStates | None = None
        failure_stage = str(row.get("failure_stage") or "")
        failure_reason = str(row.get("failure_reason") or "")
        try:
            electron = np.asarray(
                [_as_float(row[name]) for name in ENERGY_COLUMNS["electron"]], float
            )
            hole = np.asarray(
                [_as_float(row[name]) for name in ENERGY_COLUMNS["hole"]], float
            )
            if not (np.all(np.isfinite(electron)) and np.all(np.isfinite(hole))):
                raise Extract20Error("blank energy column(s)")
            states = chi2mod.CaseStates(
                case_id=case_id,
                electron_energies_eV=electron,
                hole_energies_eV=hole,
                overlap_electron_hole=_matrix_from_row(
                    row, OVERLAP_COLUMNS, f"case {case_id} overlap"),
                position_matrix_electron_nm=_matrix_from_row(
                    row, ELECTRON_POSITION_COLUMNS, f"case {case_id} z_e"),
                position_matrix_hole_nm=_matrix_from_row(
                    row, HOLE_POSITION_COLUMNS, f"case {case_id} z_hh"),
                provenance=f"{SOURCE_MASTER_TABLE}:{path.name}",
            )
        except (Extract20Error, KeyError, ValueError) as exc:
            if not failure_stage:
                failure_stage = "no_solver_states_in_source_table"
                failure_reason = f"{type(exc).__name__}: {exc}"
        extracted[case_id] = ExtractedCase(
            case_id=case_id, states=states,
            solver_pass=solver_pass, physical_valid=physical_valid,
            source=SOURCE_MASTER_TABLE, source_detail=str(path),
            failure_stage=failure_stage, failure_reason=failure_reason,
            extras=_carried_columns(row),
        )
    return extracted


#: Demo 19 columns that are solver-derived but are not chi2 inputs. Carried
#: through unchanged so Demo 20's tables keep every Demo 19 field.
CARRIED_COLUMNS = (
    "electron_E1_centroid_nm", "electron_E2_centroid_nm",
    "HH1_centroid_nm", "HH2_centroid_nm",
    "solver_return_code", "spectrum_path",
    "E1_HH1_eV", "E1_HH2_eV", "E2_HH1_eV", "E2_HH2_eV",
    "delta_z_e_nm", "delta_z_hh_nm",
    "chi2_1550_pm_per_V", "peak_chi2_pm_per_V", "peak_wavelength_nm",
    "chi2_1550_relative_to_abrupt", "peak_chi2_relative_to_abrupt",
)


def _carried_columns(row: Mapping[str, Any]) -> dict[str, Any]:
    return {name: row.get(name, "") for name in CARRIED_COLUMNS if name in row}


def states_from_nextnano_metrics(
    case_id: str, metrics: Mapping[str, Any], matrix_elements: Mapping[str, Any],
    *, provenance: str,
) -> chi2mod.CaseStates:
    """Build :class:`CaseStates` from the Demo 11/14 parser's own output.

    ``metrics`` is what ``demo14.analyse_real_trial`` returns and
    ``matrix_elements`` is the ``matrix_elements.json`` it writes beside the
    parsed spectrum. Both are read rather than recomputed, so Demo 20 inherits
    Demo 19's envelope normalization and orthonormality gating exactly.
    """

    try:
        electron = np.asarray(metrics["electron_energies_eV"], dtype=float)
        hole = np.asarray(metrics["heavy_hole_energies_eV"], dtype=float)
        overlap = np.asarray(matrix_elements["overlap_electron_hole"], dtype=float)
        z_e = np.asarray(matrix_elements["position_matrix_electron_nm"], dtype=float)
        z_h = np.asarray(matrix_elements["position_matrix_heavy_hole_nm"], dtype=float)
    except KeyError as exc:
        raise Extract20Error(
            f"case {case_id}: the parsed solver output is missing {exc}. Demo 20 "
            "will not substitute a value for a quantity the solver did not report."
        ) from None
    n = min(electron.size, hole.size, overlap.shape[0], overlap.shape[1],
            z_e.shape[0], z_h.shape[0])
    return chi2mod.CaseStates(
        case_id=case_id,
        electron_energies_eV=electron[:n],
        hole_energies_eV=hole[:n],
        overlap_electron_hole=overlap[:n, :n],
        position_matrix_electron_nm=z_e[:n, :n],
        position_matrix_hole_nm=z_h[:n, :n],
        provenance=provenance,
    )


def describe_source(cfg: Mapping[str, Any], path: Path | None) -> dict[str, Any]:
    """A record of where this run's physics came from, for every artifact."""

    source = str(cfg["analysis"]["source"])
    return {
        "analysis_source": source,
        "analysis_source_path": str(path) if path else None,
        "solver_run_in_this_execution": bool(cfg["solver"]["enabled"]),
        "note": (
            "Energies and matrix elements were read from a licensed solver run's "
            "results table; only the chi2 postprocessing was re-evaluated here."
            if source == SOURCE_MASTER_TABLE else
            "Energies and matrix elements were parsed from a raw licensed "
            "nextnano++ run directory."
        ),
    }
