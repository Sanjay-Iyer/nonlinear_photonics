"""Readers for the nextnano++ output files this package consumes.

Pure file parsing: no physics choices live here. Every reader validates shape and
finiteness and fails with the offending path in the message.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

KP8_COMPONENTS = ("cb1", "cb2", "hh1", "hh2", "lh1", "lh2", "so1", "so2")
BLOCKS = {"cb": ("cb1", "cb2"), "hh": ("hh1", "hh2"), "lh": ("lh1", "lh2"), "so": ("so1", "so2")}


class RawDataError(ValueError):
    """A required nextnano output file is missing or malformed."""


def find_one(root: Path, pattern: str) -> Path:
    found = sorted(p for p in Path(root).rglob(pattern) if p.is_file())
    if len(found) != 1:
        raise RawDataError(f"expected exactly one '{pattern}' below {root}, found {len(found)}")
    return found[0]


def find_optional(root: Path, pattern: str) -> Path | None:
    found = sorted(p for p in Path(root).rglob(pattern) if p.is_file())
    return found[0] if len(found) == 1 else None


def trapezoid_weights(x: np.ndarray) -> np.ndarray:
    """Nonuniform trapezoid weights so that sum(w*f) = integral f dx."""
    x = np.asarray(x, float)
    if x.ndim != 1 or len(x) < 2 or np.any(np.diff(x) <= 0):
        raise RawDataError("grid must be 1D and strictly increasing")
    w = np.empty_like(x)
    w[0], w[-1] = (x[1] - x[0]) / 2, (x[-1] - x[-2]) / 2
    w[1:-1] = (x[2:] - x[:-2]) / 2
    return w


def read_table(path: Path) -> tuple[list[str], np.ndarray]:
    """Header line of column names, then numeric rows (whitespace or fixed width)."""
    lines = [ln for ln in Path(path).read_text(errors="replace").splitlines() if ln.strip()]
    if len(lines) < 2:
        raise RawDataError(f"no data rows: {path}")
    header = lines[0].split()
    ncol = len(header)
    width = len(lines[0]) // ncol if ncol else 0
    rows = []
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) != ncol and width:  # glued fixed-width fields
            parts = [ln[i:i + width] for i in range(0, width * ncol, width)]
        try:
            rows.append([float(p.replace("D", "e").replace("d", "e")) for p in parts])
        except ValueError as exc:
            raise RawDataError(f"unparseable row in {path}: {ln[:80]}") from exc
    data = np.array(rows, float)
    if data.ndim != 2 or data.shape[1] != ncol or not np.all(np.isfinite(data)):
        raise RawDataError(f"malformed numeric table: {path}")
    return header, data


def read_energy_spectrum(path: Path) -> np.ndarray:
    return read_table(path)[1][:, 1]


def read_dispersion(dispersion_dir_root: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return radial k (nm^-1), energies (nk, nstates) in eV and path metadata."""
    disp = find_one(dispersion_dir_root, "dispersion_*.dat")
    vec = find_one(disp.parent, "kVectors_*.dat")
    _, data = read_table(disp)
    k, energies = data[:, 0], data[:, 1:]
    _, xyz = read_table(vec)
    xyz = xyz[:, 1:4]
    kr = np.linalg.norm(xyz, axis=1)
    if kr[0] != 0 or np.any(np.diff(kr) <= 0) or not np.allclose(kr, k, atol=5e-10, rtol=0):
        raise RawDataError(f"dispersion |k| column disagrees with {vec.name}")
    direction = xyz[1:] / kr[1:, None]
    if np.max(np.linalg.norm(np.cross(direction, direction[0]), axis=1)) > 1e-7:
        raise RawDataError("dispersion path is not a single radial direction")
    return k, energies, {"dispersion_file": disp.name, "kvectors_file": vec.name,
                         "direction": (direction[0]).tolist()}


def read_composition(path: Path) -> dict[str, np.ndarray]:
    """spinor_composition_k00000_CbHhLhSo.dat mapped by header name (order varies)."""
    header, data = read_table(path)
    columns = {name.lower(): data[:, i] for i, name in enumerate(header) if i > 0}
    missing = [c for c in KP8_COMPONENTS if c not in columns]
    if missing:
        raise RawDataError(f"{path} lacks components {missing}")
    return columns


def read_kp8_envelopes(kp8_dir: Path, states: list[int]) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    """Complex envelopes (ncomp, nz) in nm^-1/2 for 1-based state numbers."""
    z = None
    psi = {}
    for s in states:
        comps = []
        for c in KP8_COMPONENTS:
            path = Path(kp8_dir) / f"envelope_k00000_{s:04d}_{c}.dat"
            if not path.is_file():
                raise RawDataError(f"missing kp8 envelope {path.name} in {kp8_dir}")
            _, d = read_table(path)
            if z is None:
                z = d[:, 0]
            elif d.shape[0] != len(z) or not np.allclose(d[:, 0], z):
                raise RawDataError(f"envelope grid mismatch: {path.name}")
            comps.append(d[:, 1] + 1j * d[:, 2])
        psi[s] = np.array(comps)
    return z, psi


def read_kp8_dipole(path: Path) -> dict[tuple[int, int], complex]:
    """nextnano <kp8_i|z|kp8_j> in e*nm (growth polarization), 1-based indices."""
    _, d = read_table(path)
    return {(int(r[0]), int(r[1])): complex(r[4], r[5]) for r in d}


def read_single_band(root: Path) -> dict:
    """First two Gamma and HH states: energies (eV) and unit-normalized real envelopes."""
    out = {}
    z_ref = None
    for band in ("Gamma", "HH"):
        energy = read_energy_spectrum(find_one(root, f"{band}/energy_spectrum_k00000.dat"))[:2]
        _, tab = read_table(find_one(root, f"{band}/envelopes_k00000.dat"))
        z, psi = tab[:, 0], tab[:, 1:3]
        w = trapezoid_weights(z)
        norm = (psi * psi * w[:, None]).sum(axis=0)
        if len(energy) != 2 or psi.shape[1] != 2 or np.any(norm <= 0):
            raise RawDataError(f"need two normalizable {band} states below {root}")
        if z_ref is not None and not np.allclose(z, z_ref):
            raise RawDataError("Gamma and HH envelopes use different grids")
        z_ref = z
        # Original trapezoid normalization; solver signs preserved.
        out[band] = (energy, psi / np.sqrt(np.trapezoid(psi * psi, z, axis=0)))
    return {"z_nm": z_ref, "electron_eV": out["Gamma"][0], "hole_eV": out["HH"][0],
            "electron_env": out["Gamma"][1], "hole_env": out["HH"][1]}
