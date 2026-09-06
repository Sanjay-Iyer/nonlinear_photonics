"""Read finite-k kp8 state output and build the Equation 2 matrix elements.

The physics convention this module commits to is stated once, here, because
everything downstream depends on it.

An 8-band k.p state is a spinor: eight complex envelope components over z,
one per basis band (CB up/down, HH up/down, LH up/down, SO up/down in the
nextnano ordering). The correct inner product between two kp8 states is the
sum over components,

    <a|b> = sum_c integral conj(a_c(z)) b_c(z) dz,

and the correct position matrix element is likewise

    <a|z|b> = sum_c integral conj(a_c(z)) z b_c(z) dz.

The paper's Equation 2 is written in a one-band envelope language, where
``O_nm`` is an electron-hole envelope overlap and ``z_e``/``z_hh`` are
intraband position matrix elements. The bridge between the two is that the
kp8 electron-like states are CB-dominated and the hole-like states are
HH-dominated, so the Equation 2 quantities are recovered as the full spinor
inner products restricted to the physically corresponding states. That
restriction is a modelling choice, not an identity: ``spinor_purity`` is
reported alongside every matrix element so a reader can see how well the
one-band reading holds at each k.

No routine here fabricates data. If envelopes for a k point are absent the
functions raise ``FiniteKDataUnavailable`` rather than falling back to k=0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from pilot_audit import FiniteKDataUnavailable


# nextnano writes one file per (k, state, component). Component tags follow the
# 8-band basis; `_cb1/_cb2` are the two conduction spinor components and so on.
COMPONENT_TAGS = ("cb1", "cb2", "hh1", "hh2", "lh1", "lh2", "so1", "so2")
BAND_OF_COMPONENT = {"cb1": "CB", "cb2": "CB", "hh1": "HH", "hh2": "HH",
                     "lh1": "LH", "lh2": "LH", "so1": "SO", "so2": "SO"}
ENVELOPE_RE = re.compile(
    r"envelope_k(?P<k>\d{5})_(?P<state>\d{4})_(?P<component>[a-z]+\d?)\.dat$", re.IGNORECASE)


@dataclass(frozen=True)
class KPointStates:
    """All exported states at one k point."""

    k_index: int
    k_vector_per_nm: np.ndarray | None
    z_nm: np.ndarray
    energies_eV: np.ndarray                  # (n_states,)
    spinor: np.ndarray                       # (n_states, n_components, n_z) complex
    component_tags: tuple[str, ...]

    @property
    def n_states(self) -> int:
        return int(self.spinor.shape[0])

    def band_fractions(self) -> np.ndarray:
        """(n_states, 4) CB/HH/LH/SO weights from the exported spinor."""
        weights = np.zeros((self.n_states, 4))
        order = {"CB": 0, "HH": 1, "LH": 2, "SO": 3}
        for index, tag in enumerate(self.component_tags):
            band = BAND_OF_COMPONENT.get(tag.lower())
            if band is None:
                continue
            density = np.abs(self.spinor[:, index, :]) ** 2
            weights[:, order[band]] += np.trapezoid(density, self.z_nm, axis=1)
        total = weights.sum(axis=1, keepdims=True)
        return np.divide(weights, total, out=np.zeros_like(weights), where=total > 0)


def _read_envelope(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (z, complex amplitude). Two data columns mean (re, im)."""
    data = np.loadtxt(path, skiprows=1)
    data = np.atleast_2d(data)
    z = data[:, 0].astype(float)
    if data.shape[1] >= 3:
        values = data[:, 1].astype(float) + 1j * data[:, 2].astype(float)
    elif data.shape[1] == 2:
        values = data[:, 1].astype(complex)
    else:
        raise FiniteKDataUnavailable(f"envelope file has no data column: {path}")
    return z, values


def discover_k_points(case_dir: Path) -> dict[int, list[Path]]:
    """Map k index -> envelope files, from filenames or k subdirectories."""
    found: dict[int, list[Path]] = {}
    for path in Path(case_dir).rglob("envelope*"):
        if not path.is_file():
            continue
        match = ENVELOPE_RE.search(path.name)
        if match:
            found.setdefault(int(match.group("k")), []).append(path)
            continue
        for part in path.parts:                       # k_point_subdirectories layout
            sub = re.fullmatch(r"k(\d{3,5})", part, re.IGNORECASE)
            if sub:
                found.setdefault(int(sub.group(1)), []).append(path)
                break
    return found


def load_k_point(case_dir: Path, k_index: int, *, energies: Mapping[int, np.ndarray] | None = None,
                 k_vector: np.ndarray | None = None) -> KPointStates:
    """Assemble the spinor array for one k point. Raises if it is not on disk."""
    files = discover_k_points(case_dir).get(int(k_index))
    if not files:
        raise FiniteKDataUnavailable(
            f"no envelope files for k index {k_index} under {case_dir}; "
            "Demo 25 does not substitute k=0 data")
    by_state: dict[int, dict[str, Path]] = {}
    for path in files:
        match = ENVELOPE_RE.search(path.name)
        if not match:
            continue
        by_state.setdefault(int(match.group("state")), {})[match.group("component").lower()] = path
    if not by_state:
        raise FiniteKDataUnavailable(f"envelope filenames at k {k_index} are not parseable")
    tags = tuple(t for t in COMPONENT_TAGS
                 if any(t in components for components in by_state.values()))
    if not tags:
        raise FiniteKDataUnavailable(f"no recognised spinor components at k {k_index}")
    states = sorted(by_state)
    z_reference: np.ndarray | None = None
    spinor_rows = []
    for state in states:
        components = by_state[state]
        row = []
        for tag in tags:
            if tag not in components:
                row.append(None)
                continue
            z, values = _read_envelope(components[tag])
            if z_reference is None:
                z_reference = z
            elif len(z) != len(z_reference) or not np.allclose(z, z_reference):
                raise FiniteKDataUnavailable(
                    f"envelope grids differ within k {k_index}; cannot form matrix elements")
            row.append(values)
        spinor_rows.append(row)
    if z_reference is None:
        raise FiniteKDataUnavailable(f"no readable envelope data at k {k_index}")
    n_z = len(z_reference)
    array = np.zeros((len(states), len(tags), n_z), dtype=complex)
    for i, row in enumerate(spinor_rows):
        for j, values in enumerate(row):
            if values is not None:
                array[i, j, :] = values
    energy = np.full(len(states), np.nan)
    if energies is not None and int(k_index) in energies:
        supplied = np.asarray(energies[int(k_index)], dtype=float)
        energy[:min(len(energy), len(supplied))] = supplied[:len(energy)]
    return KPointStates(int(k_index), k_vector, z_reference, energy, array, tags)


def read_energy_spectrum(case_dir: Path) -> dict[int, np.ndarray]:
    """k index -> eigenvalues, from energy_spectrum_kNNNNN.dat files."""
    out: dict[int, np.ndarray] = {}
    for path in sorted(Path(case_dir).rglob("energy_spectrum*")):
        match = re.search(r"_k(\d{5})", path.name)
        index = int(match.group(1)) if match else None
        if index is None:
            for part in path.parts:
                sub = re.fullmatch(r"k(\d{3,5})", part, re.IGNORECASE)
                if sub:
                    index = int(sub.group(1))
                    break
        if index is None:
            continue
        try:
            data = np.atleast_2d(np.loadtxt(path, skiprows=1))
        except (OSError, ValueError):
            continue
        if data.size:
            out[index] = data[:, -1].astype(float)
    return out


def read_k_vectors(case_dir: Path) -> np.ndarray | None:
    for pattern in ("**/kVectors*.dat", "**/k_vectors*.dat", "**/kvectors*.dat"):
        for path in sorted(Path(case_dir).glob(pattern)):
            try:
                data = np.atleast_2d(np.loadtxt(path, skiprows=1))
            except (OSError, ValueError):
                continue
            if data.size:
                return data
    return None


# ---------------------------------------------------------------------------
# spinor inner products
# ---------------------------------------------------------------------------

def normalization(states: KPointStates) -> np.ndarray:
    """<n|n> for every state; should be 1 for a normalized kp8 spinor."""
    density = np.sum(np.abs(states.spinor) ** 2, axis=1)
    return np.trapezoid(density, states.z_nm, axis=1)


def overlap(states: KPointStates, a: int, b: int) -> complex:
    """Full spinor inner product <a|b>, summed over all eight components."""
    integrand = np.sum(np.conj(states.spinor[a]) * states.spinor[b], axis=0)
    return complex(np.trapezoid(integrand, states.z_nm))


def position_matrix_element(states: KPointStates, a: int, b: int) -> complex:
    """Full spinor position matrix element <a|z|b> in nm."""
    integrand = np.sum(np.conj(states.spinor[a]) * states.spinor[b], axis=0) * states.z_nm
    return complex(np.trapezoid(integrand, states.z_nm))


def spinor_purity(states: KPointStates, index: int, band: str) -> float:
    """Fraction of state ``index`` carried by ``band`` (CB/HH/LH/SO).

    This is how far the one-band Equation 2 reading can be trusted at this k.
    """
    order = {"CB": 0, "HH": 1, "LH": 2, "SO": 3}
    if band not in order:
        raise ValueError(f"band must be one of {sorted(order)}")
    return float(states.band_fractions()[index, order[band]])


def matrix_element_table(states: KPointStates, electrons: Sequence[int],
                         holes: Sequence[int]) -> dict[str, Any]:
    """Every Equation 2 numerator ingredient at one k point.

    ``O`` is indexed [electron, hole]; ``z_e`` and ``z_hh`` are intraband.
    """
    o = np.zeros((len(electrons), len(holes)), dtype=complex)
    for i, n in enumerate(electrons):
        for j, m in enumerate(holes):
            o[i, j] = overlap(states, m, n)          # <hole | electron>
    z_e = np.zeros((len(electrons), len(electrons)), dtype=complex)
    for i, n in enumerate(electrons):
        for j, l in enumerate(electrons):
            z_e[i, j] = position_matrix_element(states, n, l)
    z_h = np.zeros((len(holes), len(holes)), dtype=complex)
    for i, m in enumerate(holes):
        for j, l in enumerate(holes):
            z_h[i, j] = position_matrix_element(states, m, l)
    fractions = states.band_fractions()
    return {
        "k_index": states.k_index,
        "O": o, "z_e_nm": z_e, "z_hh_nm": z_h,
        "electron_indices": list(electrons), "hole_indices": list(holes),
        "electron_CB_purity": [float(fractions[n, 0]) for n in electrons],
        "hole_HH_purity": [float(fractions[m, 1]) for m in holes],
        "hole_LH_fraction": [float(fractions[m, 2]) for m in holes],
        "normalization": normalization(states).tolist(),
    }


def hermiticity_error(matrix: np.ndarray) -> float:
    """max |A - A^dagger|; a position matrix element table must be Hermitian."""
    array = np.asarray(matrix)
    return float(np.max(np.abs(array - array.conj().T))) if array.size else 0.0
