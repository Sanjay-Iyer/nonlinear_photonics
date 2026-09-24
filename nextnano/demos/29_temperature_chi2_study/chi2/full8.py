"""Full-8-band state and finite-k matrix preparation; optical response is gated."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import linear_sum_assignment

from . import parse_nextnano as io
from .acquisition import ROOT, config
from .transfer import packed_frames, validate

LABELS = ("e1", "e2", "hh1", "hh2")


def matrix_data(z: np.ndarray, psi: np.ndarray):
    """Complex full-spinor T_abuv and growth-position Z_ab in the documented basis."""
    w = io.trapezoid_weights(z)
    if psi.ndim != 3 or psi.shape[1:] != (8, len(z)) or not np.isfinite(psi).all():
        raise ValueError("Expected finite (states,8,z) complex spinors")
    norm = np.einsum("acz,acz,z->a", psi.conj(), psi, w).real
    if np.any(abs(norm - 1) > .02):
        raise ValueError("Spinor normalization differs from unity by >2%")
    normalized = psi / np.sqrt(norm)[:, None, None]
    tensor = np.einsum("auz,bvz,z->abuv", normalized.conj(), normalized, w, optimize=True)
    zm = np.einsum("auz,buz,z->ab", normalized.conj(), normalized, w * z, optimize=True)
    gram = np.einsum("abuu->ab", tensor)
    if np.max(abs(gram - np.eye(len(psi)))) > .02:
        raise ValueError("Full-spinor Gram matrix differs from identity by >2%")
    if np.max(abs(zm - zm.conj().T)) > 1e-8:
        raise ValueError("Growth-position matrix is not Hermitian")
    return normalized, tensor, zm, norm


def pair_score(previous: np.ndarray, current: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Rotation-invariant mean principal overlap between candidate two-state spaces."""
    def basis(pair):
        q, _ = np.linalg.qr((pair * np.sqrt(weights)[None, None, :]).reshape(2, -1).T)
        return q
    left = [basis(previous[2*i:2*i+2]) for i in range(len(previous)//2)]
    right = [basis(current[2*i:2*i+2]) for i in range(len(current)//2)]
    return np.array([[np.sum(abs(a.conj().T @ b)**2).real / 2 for b in right] for a in left])


def choose_k0(energy: np.ndarray, psi: np.ndarray, z: np.ndarray, minimum_character=.6) -> dict:
    """Seed two CB and two HH-like doublets from 8-band character/localization."""
    w = io.trapezoid_weights(z)
    pairs = []
    well = ((z >= 9.1) & (z <= 16.2)) | ((z >= 18.0) & (z <= 20.9))
    for i in range(len(energy)//2):
        block = psi[2*i:2*i+2]
        density = abs(block)**2
        character = np.einsum("acz,z->ac", density, w).mean(axis=0).reshape(4, 2).sum(axis=1)
        local = float(np.einsum("acz,z->", density, w * well) / 2)
        pairs.append({"pair": i, "energy_eV": float(energy[2*i:2*i+2].mean()),
                      "CB": float(character[0]), "HH": float(character[1]),
                      "LH": float(character[2]), "SO": float(character[3]), "well_fraction": local})
    cb = sorted((p for p in pairs if p["CB"] >= minimum_character and p["well_fraction"] >= .3),
                key=lambda p: p["energy_eV"])
    hh = sorted((p for p in pairs if p["HH"] >= minimum_character and p["well_fraction"] >= .3),
                key=lambda p: p["energy_eV"], reverse=True)
    if len(cb) < 2 or len(hh) < 2:
        raise ValueError("Cannot identify two localized CB and two HH-like k=0 doublets")
    return {"selected": dict(zip(LABELS, [cb[0]["pair"], cb[1]["pair"], hh[0]["pair"], hh[1]["pair"]])),
            "candidate_pairs": pairs, "selection_rule": "two lowest localized CB pairs; two highest localized HH pairs"}


def contract_interband(component_tensor: np.ndarray, operator: np.ndarray) -> np.ndarray:
    """Contract a sourced 8x8 dimensionless Bloch operator with finite-k spinors."""
    b = np.asarray(operator, complex)
    if b.shape != (8, 8) or not np.isfinite(b).all() or np.allclose(b, np.eye(8)):
        raise ValueError("A non-identity, finite 8x8 optical operator is required")
    return np.einsum("abuv,uv->ab", component_tensor, b)


def optical_gate(operator_file: Path) -> dict:
    """Fail closed until basis, polarization, units, prefactor and spin are resolved."""
    setting = json.loads(operator_file.read_text(encoding="utf-8"))
    required = ("operator_matrix", "operator_units", "operator_source", "relationship_to_r_e_hh", "spin_reduction")
    if setting.get("status") != "APPROVED" or any(not setting.get(key) for key in required):
        raise ValueError("Full-8-band optical operator/spin convention UNRESOLVED; no chi2 calculated")
    if setting.get("basis") != list(io.KP8_COMPONENTS):
        raise ValueError("Optical operator basis does not match saved spinor basis")
    if setting["operator_units"] != "dimensionless_relative_to_r_e_hh" or setting["relationship_to_r_e_hh"] != "retain_r_e_hh_squared_once":
        raise ValueError("Operator units/prefactor relation must prevent optical-factor double counting")
    if setting["spin_reduction"] not in ("explicit_spin_resolved_no_degeneracy_factor",
                                      "one_channel_times_two_with_documented_symmetry"):
        raise ValueError("Unreviewed spin reduction or double-counted spin degeneracy")
    contract_interband(np.zeros((1, 1, 8, 8), complex), setting["operator_matrix"])
    return setting


def compare_k0_to_reference(reference_bundle: Path, current_energy: np.ndarray,
                            current_z: np.ndarray, current_psi: np.ndarray,
                            current_selection: dict) -> dict:
    """Match named 300 K doublet subspaces to another temperature at k=0."""
    validate(reference_bundle)
    _, _, reference_energy, reference_z, reference_psi, _, _ = next(packed_frames(reference_bundle))
    if not np.array_equal(reference_z, current_z):
        raise ValueError("300 K and target-temperature spatial grids differ")
    normalized_ref, _, _, _ = matrix_data(reference_z, reference_psi)
    reference_selection = choose_k0(reference_energy, normalized_ref, reference_z)
    scores = pair_score(normalized_ref, current_psi, io.trapezoid_weights(current_z))
    result = {}
    for label in LABELS:
        ref_pair = reference_selection["selected"][label]
        target_pair = current_selection["selected"][label]
        best = int(np.argmax(scores[ref_pair]))
        result[label] = {"reference_pair": ref_pair, "selected_target_pair": target_pair,
                         "maximum_overlap_target_pair": best,
                         "selected_subspace_overlap": float(scores[ref_pair, target_pair]),
                         "consistent": bool(best == target_pair and scores[ref_pair, target_pair] >= .5)}
    return result


def prepare(bundle: Path, output: Path, reference_bundle: Path | None = None) -> dict:
    validation = validate(bundle)
    if output.exists():
        raise ValueError("Refusing to overwrite existing full-8-band preparation")
    c = config()
    output.mkdir(parents=True)
    (output / "operator_blocks").mkdir()
    selected = None
    previous = None
    tracked = None
    rows = []
    ambiguous = 0
    selected_ambiguous = 0
    selected_character_changes = 0
    cross_temperature = None
    for i, k, energy, z, psi, composition, ids in packed_frames(bundle):
        normalized, tensor, zm, norm = matrix_data(z, psi)
        w = io.trapezoid_weights(z)
        observed = np.einsum("acz,acz,z->ac", normalized.conj(), normalized, w).real
        if not np.allclose(observed, composition, atol=.02, rtol=0):
            raise ValueError(f"Spinor/composition disagreement at k={i}")
        if i == 0:
            selected = choose_k0(energy, normalized, z)
            if reference_bundle is not None:
                cross_temperature = compare_k0_to_reference(reference_bundle, energy, z, normalized, selected)
            tracked = np.arange(len(energy)//2)
            score = np.ones(len(tracked))
            margin = np.full(len(tracked), np.nan)
        else:
            similarity = pair_score(previous, normalized, w)
            row, col = linear_sum_assignment(-similarity)
            tracked = col[np.argsort(row)]
            score = similarity[np.arange(len(tracked)), tracked]
            alternatives = similarity.copy()
            alternatives[np.arange(len(tracked)), tracked] = -np.inf
            margin = score - alternatives.max(axis=1)
        flags = (score < c["tracking"]["min_overlap"]) | (margin < c["tracking"]["minimum_margin"])
        ambiguous += int(flags.sum())
        for label, initial in selected["selected"].items():
            solver_pair = int(tracked[initial])
            ids_pair = (2*solver_pair+1, 2*solver_pair+2)
            character = observed[2*solver_pair:2*solver_pair+2].mean(axis=0).reshape(4, 2).sum(axis=1)
            character_flag = (label.startswith("hh") and character[1] < character[2]) or (label.startswith("e") and character[0] < .5)
            selected_ambiguous += int(flags[initial])
            selected_character_changes += int(character_flag)
            rows.append([i, k, label, *ids_pair, float(energy[2*solver_pair:2*solver_pair+2].mean()),
                         *map(float, character), float(score[initial]), float(margin[initial]),
                         int(flags[initial]), int(character_flag)])
        np.savez_compressed(output / "operator_blocks" / f"k{i:05d}.npz", k_per_nm=k,
                            energy_eV=energy, z_nm=zm, component_overlap=tensor,
                            pair_to_solver=tracked, pair_overlap=score, pair_margin=margin,
                            pair_ambiguous=flags, solver_state=ids,
                            components=np.array(io.KP8_COMPONENTS), normalization_before=norm)
        previous = normalized[np.concatenate([np.arange(2*j, 2*j+2) for j in tracked])]
    with (output / "tracked_states.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["k_index", "k_per_nm", "label", "solver_state_1", "solver_state_2", "pair_energy_eV",
                         "CB", "HH", "LH", "SO", "subspace_overlap", "assignment_margin", "ambiguous", "character_change"])
        writer.writerows(rows)
    status = {"temperature_K": validation["temperature_K"], "k_points": validation["k_points"],
              "k0_selection": selected, "ambiguous_pair_assignments": ambiguous,
              "selected_pair_ambiguities": selected_ambiguous,
              "selected_character_change_flags": selected_character_changes,
              "cross_temperature_k0": cross_temperature,
              "finite_k_matrices": "complete; complex position and component-overlap blocks saved",
              "full8_chi2": "PENDING optical operator, prefactor and spin review; no spectrum produced"}
    (output / "metadata.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True, help="unpacked temperature bundle")
    p.add_argument("--output", type=Path)
    p.add_argument("--reference-bundle", type=Path, help="300 K bundle for k=0 cross-temperature state matching")
    a = p.parse_args(argv)
    try:
        dest = a.output or ROOT / "outputs/29A_full8band_baseline" / f"{a.input.name}_prepared"
        print(json.dumps(prepare(a.input, dest, a.reference_bundle), indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
