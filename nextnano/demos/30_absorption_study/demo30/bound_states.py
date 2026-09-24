"""All saved single-band states of the D020 run: energies, overlaps, binding, band edges.

Used for the expanded_bound_states comparison. It reads the same files as the Demo 28A
builder (Gamma/HH energy_spectrum_k00000.dat and envelopes_k00000.dat) but keeps every
saved state instead of the first two. It normalizes the envelopes with the same
trapezoid rule, so the 2x2 block reproduces the Eq. 2 overlaps exactly (tested).
"""
from __future__ import annotations

import numpy as np

from . import parse_nextnano as io
from .chi1 import Pair


def read_states(singleband_root) -> dict:
    out = {}
    for band in ("Gamma", "HH"):
        energy = io.read_energy_spectrum(io.find_one(singleband_root, f"{band}/energy_spectrum_k00000.dat"))
        _, tab = io.read_table(io.find_one(singleband_root, f"{band}/envelopes_k00000.dat"))
        z, psi = tab[:, 0], tab[:, 1:]
        if psi.shape[1] != len(energy):
            raise io.RawDataError(f"{band}: {psi.shape[1]} envelopes but {len(energy)} energies")
        out[band] = {"energy_eV": energy, "envelopes": psi / np.sqrt(np.trapezoid(psi * psi, z, axis=0))}
        out["z_nm"] = z
    return out


def band_edges(singleband_root) -> dict:
    """Barrier edges = extreme band-edge values in the structure (the Al0.55Ga0.45As barriers)."""
    header, tab = io.read_table(io.find_one(singleband_root, "bandedges.dat"))
    col = {name.split("[")[0]: i for i, name in enumerate(header)}
    gamma, hh = tab[:, col["Gamma"]], tab[:, col["HH"]]
    return {"barrier_Gamma_eV": float(gamma.max()), "barrier_HH_eV": float(hh.min()),
            "well_Gamma_eV": float(gamma.min()), "well_HH_eV": float(hh.max())}


def bound_indices(states: dict, edges: dict) -> dict:
    return {"Gamma": np.flatnonzero(states["Gamma"]["energy_eV"] < edges["barrier_Gamma_eV"]),
            "HH": np.flatnonzero(states["HH"]["energy_eV"] > edges["barrier_HH_eV"])}


def overlaps(states: dict) -> np.ndarray:
    """O[n, m] = integral e_n(z) hh_m(z) dz over all saved states (trapezoid, as in Eq. 2)."""
    z, e, h = states["z_nm"], states["Gamma"]["envelopes"], states["HH"]["envelopes"]
    return np.array([[np.trapezoid(e[:, n] * h[:, m], z) for m in range(h.shape[1])] for n in range(e.shape[1])])


def edge_probability(states: dict, width_nm: float = 0.5) -> dict:
    """Probability within width_nm of the quantum-region boundaries (Dirichlet edges)."""
    z = states["z_nm"]
    near = (z <= z[0] + width_nm) | (z >= z[-1] - width_nm)
    out = {}
    for band in ("Gamma", "HH"):
        psi2 = states[band]["envelopes"] ** 2
        out[band] = [float(np.trapezoid(np.where(near, psi2[:, i], 0.0), z)) for i in range(psi2.shape[1])]
    return out


def continuum_onset(states: dict, edges: dict) -> dict:
    """Lowest bound-to-continuum transition: min(E_e1 - E_HH,barrier, E_Gamma,barrier - E_hh1)."""
    e1, hh1 = states["Gamma"]["energy_eV"].min(), states["HH"]["energy_eV"].max()
    a, b = e1 - edges["barrier_HH_eV"], edges["barrier_Gamma_eV"] - hh1
    return {"onset_eV": float(min(a, b)), "e1_to_HH_continuum_eV": float(a), "Gamma_continuum_to_hh1_eV": float(b)}


def expanded_pairs(tracked: list[Pair], states: dict, edges: dict, k_per_nm, slope_eV_nm2: float) -> list[Pair]:
    """The four tracked Eq. 2 pairs unchanged, plus every other bound e_n-hh_m pair.

    The extra pairs have no tracked 8-band dispersion, so they get an assumed parabolic
    dispersion T(k) = T(0) + slope*k^2 on the same k grid. T(0) = E_e,n - E_hh,m comes
    from the single-band energies, like the 2x2 anchors. |O|^2 is frozen at k = 0, as in
    the 2x2 model.
    """
    k = np.asarray(k_per_nm, float)
    bound = bound_indices(states, edges)
    o = overlaps(states)
    tracked_labels = {p.label for p in tracked}
    out = list(tracked)
    for n in bound["Gamma"]:
        for m in bound["HH"]:
            label = f"e{n + 1}-hh{m + 1}"
            if label in tracked_labels:
                continue
            t0 = states["Gamma"]["energy_eV"][n] - states["HH"]["energy_eV"][m]
            out.append(Pair(label, t0 + slope_eV_nm2 * k ** 2, np.full(len(k), o[n, m] ** 2),
                            "parabolic (assumed slope)"))
    return out
