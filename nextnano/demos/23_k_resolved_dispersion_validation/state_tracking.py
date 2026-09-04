"""Demo 23 target-state classification and Demo 22 tracking reuse."""

from __future__ import annotations

import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from config23 import DEMO_DIR, Demo23Error


DEMO22 = DEMO_DIR.parent / "22_k_resolved_8band_chi2_validation"
if str(DEMO22) not in sys.path:
    sys.path.insert(0, str(DEMO22))
import kp8io22  # noqa: E402
import state_tracking22  # noqa: E402


TARGETS = ("e1", "e2", "hh1", "hh2")


@dataclass(frozen=True)
class TrackedSubbands:
    k_per_nm: np.ndarray
    energies_eV: Mapping[str, np.ndarray]
    k0_raw_identity: Mapping[str, int]
    tracking: state_tracking22.TrackingResult | None
    rows: tuple[dict[str, Any], ...]


def _component_index(names: tuple[str, ...], token: str) -> int | None:
    target = token.lower()
    for index, name in enumerate(names):
        normalized = name.lower().replace("heavy_hole", "hh").replace("light_hole", "lh")
        if target in normalized:
            return index
    return None


def classify_k0(grid: kp8io22.RawStateGrid) -> dict[str, int]:
    """Identify target states by CB character, then order within each family."""

    cb = _component_index(grid.component_names, "cb")
    if cb is None:
        raise Demo23Error("CB-resolved spinor composition is required for state classification")
    cb_fraction = grid.spinor_components[0, :, cb]
    electron = np.flatnonzero(cb_fraction >= 0.5)
    holes = np.flatnonzero(cb_fraction < 0.5)
    if len(electron) < 2 or len(holes) < 3:
        raise Demo23Error(
            f"k=0 classification found {len(electron)} electron-like and {len(holes)} hole-like states"
        )
    electron = electron[np.argsort(grid.energies_eV[0, electron])]
    holes = holes[np.argsort(grid.energies_eV[0, holes])[::-1]]
    return {
        "e1": int(electron[0]),
        "e2": int(electron[1]),
        "hh1": int(holes[0]),
        "hh2": int(holes[1]),
        "hh3": int(holes[2]),
    }


def validate_radial_path(grid: kp8io22.RawStateGrid, *, angular_tolerance: float = 1e-7) -> None:
    k = np.asarray(grid.k_per_nm, dtype=float)
    if abs(k[0]) > 1e-10 or np.any(np.diff(k) <= 0):
        raise Demo23Error("production data must be a unique, strictly increasing path beginning at k=0")
    vectors = np.asarray(grid.k_vector_per_nm, dtype=float)
    nonzero = np.linalg.norm(vectors, axis=1) > 1e-12
    directions = vectors[nonzero] / np.linalg.norm(vectors[nonzero], axis=1)[:, None]
    if len(directions) and np.max(np.linalg.norm(np.cross(directions, directions[0]), axis=1)) > angular_tolerance:
        raise Demo23Error("radial production input contains multiple k directions; use direct 2D analysis")


def track_targets(grid: kp8io22.RawStateGrid, cfg: Mapping[str, Any]) -> TrackedSubbands:
    validate_radial_path(grid)
    labels = classify_k0(grid)
    settings = cfg["state_tracking"]
    result = state_tracking22.track_states(
        grid.energies_eV,
        np.sqrt(np.clip(grid.spinor_components, 0.0, None)),
        ntrack=grid.energies_eV.shape[1],
        minimum_overlap=float(settings["minimum_overlap_score"]),
        minimum_margin=float(settings["minimum_assignment_margin"]),
        energy_tie_break_weight=float(settings["energy_tie_break_weight"]),
    )
    energies: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    ambiguous: list[str] = []
    for label in TARGETS:
        identity = labels[label]
        raw_at_k = result.tracked_raw_indices[:, identity]
        energies[label] = np.asarray([
            grid.energies_eV[ik, raw] for ik, raw in enumerate(raw_at_k)
        ])
        for ik, raw in enumerate(raw_at_k):
            confidence = str(result.confidence[ik, identity])
            if confidence == "ambiguous":
                ambiguous.append(f"{label}@k={grid.k_per_nm[ik]:.6g}")
            rows.append({
                "k_per_nm": float(grid.k_per_nm[ik]),
                "raw_solver_index": int(grid.raw_state_index[raw]),
                "assigned_physical_state": label,
                "energy_eV": float(grid.energies_eV[ik, raw]),
                "tracking_score": float(result.overlap_scores[ik, identity]),
                "assignment_margin": float(result.assignment_margins[ik, identity]),
                "confidence": confidence,
                "dominant_spinor_character": grid.component_names[
                    int(np.argmax(grid.spinor_components[ik, raw]))
                ],
            })
    if ambiguous and bool(settings.get("fail_on_ambiguous_target", True)):
        preview = ", ".join(ambiguous[:8])
        raise Demo23Error(
            f"ambiguous target-state tracking ({preview}); refusing dispersion fitting"
        )
    return TrackedSubbands(
        np.asarray(grid.k_per_nm), energies, labels, result, tuple(rows)
    )


def _fixed_width_dispersion(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read Professional's combined dispersion table, including touching fields."""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not lines:
        raise Demo23Error(f"empty combined dispersion file: {path}")
    header = lines[0]
    band_count = len(re.findall(r"Band_\d+\[", header))
    if band_count < 4:
        raise Demo23Error(f"combined dispersion header does not expose band columns: {path}")
    number = re.compile(kp8io22.NUMBER)
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        matches = list(number.finditer(line))
        fields = [match.group() for match in matches]
        # Some Professional builds omit the field separator after Band_6 and
        # Band_13. Regex then reads "1.443...2.339..." as a too-long first
        # token followed by ".339...". Move the swallowed leading digit back.
        for index in range(1, len(fields)):
            if (fields[index].startswith(".") and matches[index].start() == matches[index - 1].end()
                    and "." in fields[index - 1] and "e" not in fields[index - 1].lower()):
                fields[index] = fields[index - 1][-1] + fields[index]
                fields[index - 1] = fields[index - 1][:-1]
        if len(fields) != band_count + 1:
            raise Demo23Error(
                f"expected {band_count + 1} numeric fields in combined dispersion row, "
                f"found {len(fields)}: {line[:120]}"
            )
        try:
            rows.append([float(value) for value in fields])
        except ValueError as exc:
            raise Demo23Error(f"cannot parse fixed-width dispersion row in {path}: {line[:120]}") from exc
    table = np.asarray(rows, dtype=float)
    if table.ndim != 2 or table.shape[1] != band_count + 1:
        raise Demo23Error(f"unexpected combined dispersion shape {table.shape} in {path}")
    return table[:, 0], table[:, 1:]


def _combined_files(raw_root: Path) -> tuple[Path, Path, Path, Path] | None:
    dispersion = sorted(raw_root.rglob("dispersion_*.dat"))
    vectors = sorted({*raw_root.rglob("kVectors_*.dat"), *raw_root.rglob("kvectors_*.dat")})
    energies = sorted(raw_root.rglob("*/kp8/energy_spectrum_k00000.dat"))
    spinors = sorted(raw_root.rglob("*/kp8/spinor_composition_k00000_CbHhLhSo.dat"))
    if not dispersion:
        return None
    if not (len(dispersion) == len(vectors) == len(energies) == len(spinors) == 1):
        raise Demo23Error(
            "combined Professional dispersion layout must contain exactly one dispersion, "
            "k-vector, k=0 energy, and CbHhLhSo spinor file"
        )
    return dispersion[0], vectors[0], energies[0], spinors[0]


def _pair_targets(
    k0_energy: np.ndarray,
    k0_spinor: np.ndarray,
    component_names: tuple[str, ...],
    expected_k0_eV: Mapping[str, float],
) -> dict[str, tuple[int, int]]:
    if len(k0_energy) % 2:
        raise Demo23Error("combined kp8 spectrum has an odd number of states; cannot form Kramers pairs")
    pairs = [(index, index + 1) for index in range(0, len(k0_energy), 2)]
    pair_energy = np.asarray([np.mean(k0_energy[list(pair)]) for pair in pairs])
    cb_columns = [i for i, name in enumerate(component_names) if name.lower().startswith("cb")]
    if not cb_columns:
        raise Demo23Error("k=0 spinor file has no Cb components for pair classification")
    pair_cb = np.asarray([
        np.mean(np.sum(k0_spinor[list(pair)][:, cb_columns], axis=1)) for pair in pairs
    ])
    electron_candidates = [i for i, value in enumerate(pair_cb) if value >= 0.80]
    hole_candidates = [i for i, value in enumerate(pair_cb) if value <= 0.20]
    if len(electron_candidates) < 2 or len(hole_candidates) < 2:
        raise Demo23Error(
            "could not identify at least two strongly electron-like and two hole-like Kramers pairs"
        )
    expected_e = np.asarray([expected_k0_eV["e1"], expected_k0_eV["e2"]])
    expected_h = np.asarray([expected_k0_eV["hh1"], expected_k0_eV["hh2"]])
    expected_transition = expected_e[:, None] - expected_h[None, :]
    best: tuple[float, tuple[int, int], tuple[int, int]] | None = None
    for ia, first_e in enumerate(electron_candidates):
        for second_e in electron_candidates[ia + 1:]:
            e = tuple(sorted((first_e, second_e), key=lambda index: pair_energy[index]))
            for ih, first_h in enumerate(hole_candidates):
                for second_h in hole_candidates[ih + 1:]:
                    h = tuple(sorted((first_h, second_h), key=lambda index: pair_energy[index], reverse=True))
                    raw_transition = pair_energy[list(e)][:, None] - pair_energy[list(h)][None, :]
                    score = float(np.sqrt(np.mean((raw_transition - expected_transition) ** 2)))
                    if best is None or score < best[0]:
                        best = (score, e, h)
    if best is None:
        raise Demo23Error("could not assign target Kramers pairs")
    _, electrons, holes = best
    return {
        "e1": pairs[electrons[0]], "e2": pairs[electrons[1]],
        "hh1": pairs[holes[0]], "hh2": pairs[holes[1]],
    }


def load_combined_dispersion(
    raw_root: Path,
    inventory_csv: Path,
    cfg: Mapping[str, Any],
    expected_k0_eV: Mapping[str, float],
) -> TrackedSubbands:
    """Load the actual Professional layout: one E(k) table plus k=0 spinors."""
    kp8io22.inventory(raw_root, inventory_csv)
    found = _combined_files(raw_root)
    if found is None:
        raise Demo23Error(f"no combined dispersion file below {raw_root}")
    dispersion_path, vector_path, energy_path, spinor_path = found
    k_scalar, bands = _fixed_width_dispersion(dispersion_path)
    vector_table = kp8io22.numeric_table(vector_path)
    if vector_table.shape[1] < 4 or len(vector_table) != len(k_scalar):
        raise Demo23Error("combined k-vector and dispersion tables disagree")
    k_vectors = vector_table[:, 1:4]
    k_norm = np.linalg.norm(k_vectors, axis=1)
    if not np.allclose(k_scalar, k_norm, rtol=0.0, atol=5e-10):
        raise Demo23Error("dispersion |k| column disagrees with explicit k-vector table")
    k0_table = kp8io22.numeric_table(energy_path)
    spinor_table = kp8io22.numeric_table(spinor_path)
    nstate = min(len(k0_table), len(spinor_table), bands.shape[1])
    if nstate < 8:
        raise Demo23Error("combined kp8 output has too few states")
    k0_energy = k0_table[:nstate, 1]
    if not np.allclose(k0_energy, bands[0, :nstate], rtol=0.0, atol=1e-9):
        raise Demo23Error("k=0 energy spectrum disagrees with first dispersion row")
    spinor = spinor_table[:nstate, 1:]
    spinor /= np.sum(np.abs(spinor), axis=1)[:, None]
    component_names = kp8io22._component_names(spinor_path, spinor.shape[1])
    targets = _pair_targets(k0_energy, spinor, component_names, expected_k0_eV)
    energies: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    identities: dict[str, int] = {}
    for state, pair in targets.items():
        energies[state] = np.mean(bands[:, list(pair)], axis=1)
        identities[state] = int(pair[0])
        pair_character = np.mean(spinor[list(pair)], axis=0)
        dominant = component_names[int(np.argmax(pair_character))]
        splitting = 1000.0 * np.abs(bands[:, pair[1]] - bands[:, pair[0]])
        for ik, k_value in enumerate(k_norm):
            rows.append({
                "k_per_nm": float(k_value),
                "raw_solver_index": f"{pair[0] + 1}+{pair[1] + 1}",
                "assigned_physical_state": state,
                "energy_eV": float(energies[state][ik]),
                "tracking_score": float("nan"),
                "assignment_margin": float("nan"),
                "confidence": "LIMITED_NO_FINITE_K_SPINOR",
                "dominant_spinor_character": dominant,
                "tracking_method": "fixed solver dispersion columns; Kramers-pair average",
                "finite_k_overlap_available": False,
                "kramers_pair_splitting_meV": float(splitting[ik]),
            })
    return TrackedSubbands(k_norm, energies, identities, None, tuple(rows))


def load_and_track(
    raw_root: Path,
    inventory_csv: Path,
    cfg: Mapping[str, Any],
    expected_k0_eV: Mapping[str, float] | None = None,
) -> TrackedSubbands:
    """Prefer full per-k states; otherwise use the observed combined Professional layout."""
    raw_root = Path(raw_root)
    per_k = list(raw_root.rglob("*/kp8/energy_spectrum_k*.dat"))
    if len(per_k) >= 2:
        grid = kp8io22.extract_state_grid(raw_root, Path(inventory_csv))
        return track_targets(grid, cfg)
    if expected_k0_eV is None:
        raise Demo23Error("combined dispersion parsing requires expected Demo 21 k=0 anchors")
    return load_combined_dispersion(raw_root, Path(inventory_csv), cfg, expected_k0_eV)
