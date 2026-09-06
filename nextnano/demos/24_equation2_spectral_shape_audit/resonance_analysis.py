"""Map one- and two-photon Equation-2 denominator resonances."""

from __future__ import annotations

from typing import Mapping

import numpy as np


HC_EV_NM = 1239.8419843320026


def resonance_rows(k_per_nm: np.ndarray, transitions: Mapping[str, np.ndarray]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for label, values in transitions.items():
        for k, energy in zip(k_per_nm, values):
            rows.append({
                "transition": label, "k_per_nm": float(k), "transition_energy_eV": float(energy),
                "one_photon_fundamental_wavelength_nm": float(HC_EV_NM / energy),
                "two_photon_fundamental_wavelength_nm": float(2.0 * HC_EV_NM / energy),
            })
    return rows
