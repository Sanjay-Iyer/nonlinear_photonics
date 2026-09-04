"""Fail-loudly parser for observed nextnano++ kp8 output.

The parser accepts only data it can associate with an explicit k vector. It
never maps file number to k by assumption. Unrecognised Professional output is
inventoried so the adapter can be updated against the actual files.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from config22 import Demo22Error


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
K_VECTOR_RE = re.compile(r"k\s*=\s*\[\s*(%s)\s*[, ]+\s*(%s)\s*[, ]+\s*(%s)\s*\]" % (NUMBER, NUMBER, NUMBER), re.I)
K_INDEX_RE = re.compile(r"_k(\d+)", re.I)


@dataclass(frozen=True)
class RawStateGrid:
    k_vector_per_nm: np.ndarray       # (nk,3)
    k_per_nm: np.ndarray              # (nk,)
    raw_state_index: np.ndarray       # (nstate,)
    energies_eV: np.ndarray           # (nk,nstate)
    spinor_components: np.ndarray     # (nk,nstate,ncomponent)
    component_names: tuple[str, ...]
    energy_files: tuple[str, ...]
    spinor_files: tuple[str, ...]


def numeric_table(path: Path) -> np.ndarray:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = line.strip()
        if not text or text.startswith(("#", "%", "!")):
            continue
        try:
            rows.append([float(x) for x in text.replace(",", " ").split()])
        except ValueError:
            continue
    if not rows:
        raise Demo22Error(f"no numeric rows in {path}")
    width = max(map(len, rows))
    rows = [row for row in rows if len(row) == width]
    return np.asarray(rows, dtype=float)


def _index(path: Path) -> int:
    match = K_INDEX_RE.search(path.stem)
    if not match:
        raise Demo22Error(f"cannot extract k index from {path.name}")
    return int(match.group(1))


def _k_from_header(path: Path) -> np.ndarray | None:
    head = "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[:80])
    match = K_VECTOR_RE.search(head)
    return np.asarray([float(match.group(i)) for i in (1, 2, 3)]) if match else None


def _global_k_vectors(root: Path, count: int) -> np.ndarray | None:
    candidates = sorted({p for pattern in ("*k_vector*.dat", "*kvector*.dat", "*k_points*.dat", "*kpoints*.dat") for p in root.rglob(pattern)})
    for path in candidates:
        try:
            table = numeric_table(path)
        except Demo22Error:
            continue
        if len(table) != count:
            continue
        if table.shape[1] >= 4 and np.allclose(table[:, 0], np.arange(len(table)), atol=1e-6):
            return table[:, 1:4]
        if table.shape[1] >= 3:
            return table[:, :3]
    return None


def inventory(root: Path, destination: Path) -> list[dict[str, object]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append({"relative_path": str(path.relative_to(root)), "size_bytes": path.stat().st_size})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["relative_path", "size_bytes"])
        writer.writeheader(); writer.writerows(rows)
    return rows


def _component_names(path: Path, count: int) -> tuple[str, ...]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:30]
    for line in reversed(lines):
        tokens = line.lstrip("#%! ").replace(",", " ").split()
        if len(tokens) >= count + 1 and any(re.search(r"CB|HH|LH|SO|s1|x1", t, re.I) for t in tokens):
            return tuple(tokens[-count:])
    return tuple(f"component_{i+1}" for i in range(count))


def extract_state_grid(raw_root: Path, inventory_csv: Path) -> RawStateGrid:
    inventory(raw_root, inventory_csv)
    energy_files = sorted(raw_root.rglob("*/kp8/energy_spectrum_k*.dat"), key=_index)
    if len(energy_files) < 2:
        raise Demo22Error(f"expected multiple kp8 energy_spectrum_k*.dat files below {raw_root}")
    energy_tables = [numeric_table(path) for path in energy_files]
    nstates = min(len(x) for x in energy_tables)
    if nstates < 4:
        raise Demo22Error("kp8 output has fewer than four states")
    raw_index = energy_tables[0][:nstates, 0].astype(int)
    energies = np.stack([x[:nstates, 1] for x in energy_tables])
    if not np.all(np.isfinite(energies)):
        raise Demo22Error("non-finite kp8 eigenenergy")
    header_k = [_k_from_header(path) for path in energy_files]
    if all(value is not None for value in header_k):
        k_vector = np.stack(header_k)
    else:
        k_vector = _global_k_vectors(raw_root, len(energy_files))
    if k_vector is None:
        raise Demo22Error(
            "no explicit k vectors found in energy headers or k-vector table; refusing to infer k from file index"
        )
    k_norm = np.linalg.norm(k_vector, axis=1)
    order = np.argsort(k_norm)
    energy_files = [energy_files[i] for i in order]
    energies = energies[order]
    k_vector = k_vector[order]
    k_norm = k_norm[order]

    spinor_files = sorted(raw_root.rglob("*/kp8/spinor_composition_k*CB*HH*LH*SO*.dat"), key=_index)
    if len(spinor_files) != len(energy_files):
        # Fall back to the generic composition only if there is exactly one per k.
        generic = sorted(raw_root.rglob("*/kp8/spinor_composition_k*.dat"), key=_index)
        if len(generic) == len(energy_files):
            spinor_files = generic
    if len(spinor_files) != len(energy_files):
        raise Demo22Error(
            f"need one spinor composition file per k point; found {len(spinor_files)} for {len(energy_files)} energies"
        )
    spin_tables = [numeric_table(path) for path in spinor_files]
    ncomp = min(x.shape[1] - 1 for x in spin_tables)
    spinor = np.stack([x[:nstates, 1:1+ncomp] for x in spin_tables])[order]
    totals = np.sum(np.abs(spinor), axis=2)
    if np.any(totals <= 0):
        raise Demo22Error("zero spinor-composition total")
    spinor = spinor / totals[:, :, None]
    return RawStateGrid(k_vector, k_norm, raw_index, energies, spinor,
                        _component_names(spinor_files[0], ncomp),
                        tuple(str(x) for x in energy_files), tuple(str(x) for x in spinor_files))


def save_npz(grid: RawStateGrid, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, k_vector_per_nm=grid.k_vector_per_nm, k_per_nm=grid.k_per_nm,
                        raw_state_index=grid.raw_state_index, energies_eV=grid.energies_eV,
                        spinor_components=grid.spinor_components,
                        component_names=np.asarray(grid.component_names, dtype=str))
    (path.with_suffix(".provenance.json")).write_text(json.dumps({
        "energy_files": grid.energy_files, "spinor_files": grid.spinor_files,
        "rule": "k vectors read explicitly; no file-index-to-k inference",
    }, indent=2), encoding="utf-8")

