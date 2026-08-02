"""Read-only corrections for derived values stored by historical Demo 13 runs.

The v3 ledger is immutable evidence.  Two of its derived fields were written
with old sign conventions, so reporting must neither rewrite that evidence nor
repeat it as current physics.  This module makes a detached projection of each
record, preserves every stored value under an explicit ``stored_*`` name, and
recomputes the reporting value from primary data when possible.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _finite_sequence(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)):
        return None
    numbers = [_finite(item) for item in value]
    if len(numbers) < 2 or any(item is None for item in numbers):
        return None
    return [float(item) for item in numbers if item is not None]


def _target_wavelength(record: Mapping[str, Any], cfg: Mapping[str, Any]) -> float | None:
    target = _finite(record.get("target_wavelength_nm"))
    if target is not None:
        return target
    return _finite((cfg.get("chi2") or {}).get("reference_wavelength_nm"))


def _detuning(
    record: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[float | None, float | None, str | None, str]:
    peak = _finite(record.get("peak_wavelength_nm"))
    target = _target_wavelength(record, cfg)
    if peak is None or target is None:
        return None, None, None, "unavailable"
    signed = peak - target
    side = "on_target" if signed == 0 else "blue_of_target" if signed < 0 else "red_of_target"
    return signed, abs(signed), side, "recomputed_from_peak_and_target_wavelength"


def _hole_gaps(record: Mapping[str, Any]) -> tuple[list[float] | None, float | None, str]:
    energies = _finite_sequence(record.get("heavy_hole_energies_eV"))
    if energies is None:
        return None, None, "unavailable"
    gaps = [abs(energies[index + 1] - energies[index]) * 1000.0
            for index in range(len(energies) - 1)]
    return gaps, min(gaps), "recomputed_from_heavy_hole_energies_eV"


def _different(stored: Any, corrected: Any) -> bool:
    if stored is None and corrected is None:
        return False
    stored_number = _finite(stored)
    corrected_number = _finite(corrected)
    if stored_number is not None and corrected_number is not None:
        return not math.isclose(stored_number, corrected_number, rel_tol=1e-12, abs_tol=1e-12)
    return stored != corrected


def _sequence_different(stored: Any, corrected: Any) -> bool:
    if stored is None and corrected is None:
        return False
    if not isinstance(stored, (list, tuple)) or not isinstance(corrected, (list, tuple)):
        return stored != corrected
    if len(stored) != len(corrected):
        return True
    return any(_different(left, right) for left, right in zip(stored, corrected))


def corrected_record(
    record: Mapping[str, Any], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """Return a corrected reporting copy; never mutate ``record``."""

    view = dict(record)
    stored_signed = record.get("stored_signed_detuning_nm", record.get("signed_detuning_nm"))
    stored_absolute = record.get("stored_absolute_detuning_nm", record.get("absolute_detuning_nm"))
    stored_side = record.get("stored_detuning_side", record.get("detuning_side"))
    stored_hole_gaps = record.get(
        "stored_heavy_hole_level_gaps_meV", record.get("heavy_hole_level_gaps_meV")
    )
    stored_hole_gap = record.get(
        "stored_heavy_hole_gap_meV", record.get("heavy_hole_anticrossing_gap_meV")
    )

    signed, absolute, side, detuning_provenance = _detuning(record, cfg)
    hole_gaps, hole_gap, gap_provenance = _hole_gaps(record)

    view.update(
        {
            "stored_signed_detuning_nm": stored_signed,
            "corrected_signed_detuning_nm": signed,
            "stored_absolute_detuning_nm": stored_absolute,
            "corrected_absolute_detuning_nm": absolute,
            "stored_detuning_side": stored_side,
            "corrected_detuning_side": side,
            "signed_detuning_nm": signed,
            "absolute_detuning_nm": absolute,
            "detuning_side": side,
            "stored_heavy_hole_level_gaps_meV": stored_hole_gaps,
            "corrected_heavy_hole_level_gaps_meV": hole_gaps,
            "heavy_hole_level_gaps_meV": hole_gaps,
            "stored_heavy_hole_gap_meV": stored_hole_gap,
            "corrected_heavy_hole_gap_meV": hole_gap,
            "heavy_hole_anticrossing_gap_meV": hole_gap,
            "detuning_derived_value_status": (
                "unavailable" if side is None else
                "corrected" if (
                    _different(stored_side, side)
                    or _different(stored_signed, signed)
                    or _different(stored_absolute, absolute)
                )
                else "verified"
            ),
            "heavy_hole_gap_derived_value_status": (
                "unavailable" if hole_gap is None else
                "corrected" if (
                    _different(stored_hole_gap, hole_gap)
                    or _sequence_different(stored_hole_gaps, hole_gaps)
                ) else "verified"
            ),
            "detuning_derived_value_provenance": detuning_provenance,
            "heavy_hole_gap_derived_value_provenance": gap_provenance,
        }
    )
    statuses = {
        view["detuning_derived_value_status"],
        view["heavy_hole_gap_derived_value_status"],
    }
    view["derived_value_status"] = (
        "unavailable" if statuses == {"unavailable"}
        else "partially_unavailable" if "unavailable" in statuses
        else "corrected" if "corrected" in statuses
        else "verified"
    )
    view["derived_value_provenance"] = (
        "read_only_reporting_projection_from_primary_record_fields"
    )

    if not view.get("state_tracking_energy_provenance"):
        has_energies = (
            _finite_sequence(record.get("electron_energies_eV")) is not None
            and _finite_sequence(record.get("heavy_hole_energies_eV")) is not None
        )
        view["state_tracking_energy_provenance"] = (
            "parsed historical output" if has_energies else "unavailable"
        )
    return view


def corrected_records(
    records: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Detached, idempotent reporting projections for a record sequence."""

    return [corrected_record(record, cfg) for record in records]
