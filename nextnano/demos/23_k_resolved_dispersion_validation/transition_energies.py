"""Authoritative same-k transition-energy construction for Demo 23."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np


SUBBAND_ORDER = ("e1", "e2", "hh1", "hh2")
TRANSITION_LABELS = ("DeltaE_11", "DeltaE_12", "DeltaE_21", "DeltaE_22")


@dataclass(frozen=True)
class TransitionEnergies:
    """Four interband transition arrays on one shared radial k grid."""

    k_per_nm: np.ndarray
    values_eV: np.ndarray  # (2 electron, 2 heavy-hole, nk)

    def __post_init__(self) -> None:
        k = np.asarray(self.k_per_nm, dtype=float)
        values = np.asarray(self.values_eV, dtype=float)
        if k.ndim != 1 or values.shape != (2, 2, len(k)):
            raise ValueError("transition values must have shape (2,2,nk)")
        if not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise ValueError("all Ee(k)-Ehh(k) transitions must be finite and positive")

    def as_dict(self) -> dict[str, np.ndarray]:
        return {
            "DeltaE_11": self.values_eV[0, 0],
            "DeltaE_12": self.values_eV[0, 1],
            "DeltaE_21": self.values_eV[1, 0],
            "DeltaE_22": self.values_eV[1, 1],
        }


def build_transition_energies(
    k_per_nm: np.ndarray,
    subbands_eV: Mapping[str, np.ndarray],
) -> TransitionEnergies:
    """Build every transition from electron and heavy-hole states at the same k.

    This is the only Demo 23 function allowed to define ``DeltaE_nm``. The
    heavy-hole values remain nextnano valence-electron eigenenergies; no
    positive-hole quasiparticle transformation is made.
    """

    k = np.asarray(k_per_nm, dtype=float)
    missing = [name for name in SUBBAND_ORDER if name not in subbands_eV]
    if missing:
        raise ValueError("missing subband arrays: " + ", ".join(missing))
    arrays = {name: np.asarray(subbands_eV[name], dtype=float) for name in SUBBAND_ORDER}
    for name, values in arrays.items():
        if values.shape != k.shape:
            raise ValueError(f"{name} has shape {values.shape}; expected {k.shape}")
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{name} contains non-finite energies")
    electron = np.vstack([arrays["e1"], arrays["e2"]])
    heavy_hole = np.vstack([arrays["hh1"], arrays["hh2"]])
    return TransitionEnergies(k, electron[:, None, :] - heavy_hole[None, :, :])


def assert_k0_matches(
    transitions: TransitionEnergies,
    electron_k0_eV: np.ndarray,
    hole_k0_eV: np.ndarray,
    *,
    tolerance_eV: float,
) -> float:
    expected = np.asarray(electron_k0_eV, dtype=float)[:2, None] - np.asarray(
        hole_k0_eV, dtype=float
    )[None, :2]
    error = float(np.max(np.abs(transitions.values_eV[:, :, 0] - expected)))
    if error > float(tolerance_eV):
        raise ValueError(
            f"k=0 transition convention mismatch: max error {error:.6g} eV exceeds "
            f"{tolerance_eV:.6g} eV"
        )
    return error

