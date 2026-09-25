"""Analyze exported 8-band pilot states on the positive Γ-to-y target interval."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

from . import parse_nextnano as io, run_debug
from .acquisition import ROOT, config
from .full8 import choose_k0, matrix_data, pair_score


def _state_frame(folder: Path, n: int):
    energy = io.read_energy_spectrum(folder / "energy_spectrum.dat")
    composition = io.read_composition(folder / "spinor_composition_CbHhLhSo.dat")
    z = None
    states = []
    for state in range(1, n + 1):
        components = []
        for name in io.KP8_COMPONENTS:
            _, table = io.read_table(folder / f"envelope_{state:04d}_{name}.dat")
            if z is None:
                z = table[:, 0]
            elif not np.array_equal(z, table[:, 0]):
                raise ValueError(f"Spatial grid mismatch in {folder}")
            components.append(table[:, 1] + 1j * table[:, 2])
        states.append(components)
    psi = np.asarray(states)
    comp = np.column_stack([composition[name] for name in io.KP8_COMPONENTS])
    if energy.shape != (n,) or comp.shape != (n, 8):
        raise ValueError(f"Wrong state count in {folder}")
    return energy, z, psi, comp


def analyze(run: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"Refusing to overwrite {output}")
    c = config()
    report = run_debug.scan_output(run)
    grid = report["integration_grid"]
    if grid.get("points") is None or report["dispersion"]["points"] != 301:
        raise ValueError("Missing k_points.txt or 301-point dispersion")
    rows = sorted((r for r in grid["rows"] if r["on_target_path"] and
                   r["complex_spinors_complete"]), key=lambda r: r["ky_per_nm"])
    if not rows or rows[0]["magnitude_per_nm"] > 1e-8:
        raise ValueError("No complete k=0 frame on target path")
    output.mkdir(parents=True)
    (output / "matrix_blocks").mkdir()
    selected = None
    previous = None
    track = None
    results = []
    table = []
    previous_energy = None
    native_dipole_max_error = 0.0
    for row in rows:
        energy, z, psi, comp = _state_frame(Path(row["state_folder"]),
                                             c["num_electrons"] + c["num_holes"])
        normalized, tensor, zm, norm = matrix_data(z, psi)
        observed = np.einsum("acz,acz,z->ac", normalized.conj(), normalized,
                             io.trapezoid_weights(z)).real
        if not np.allclose(observed, comp, atol=2e-5, rtol=0):
            raise ValueError(f"Composition mismatch in {row['id']}")
        if selected is None:
            selected = choose_k0(energy, normalized, z)
            track = np.arange(len(energy) // 2)
            score = np.ones(len(track))
            margin = np.full(len(track), np.nan)
            similarity = np.eye(len(track))
        else:
            similarity = pair_score(previous, normalized, io.trapezoid_weights(z))
            a, b = linear_sum_assignment(-similarity)
            track = b[np.argsort(a)]
            score = similarity[np.arange(len(track)), track]
            alternative = similarity.copy()
            alternative[np.arange(len(track)), track] = -np.inf
            margin = score - alternative.max(axis=1)
        pair_character = observed.reshape(len(energy) // 2, 2, 4, 2).mean(axis=1).sum(axis=2)
        well = ((z >= 9.1) & (z <= 16.2)) | ((z >= 18.0) & (z <= 20.9))
        localized = np.einsum("acz,acz,z->a", normalized.conj(), normalized,
                              io.trapezoid_weights(z) * well).real.reshape(-1, 2).mean(axis=1)
        native = (run / "kp8/kp8/bias_00000/Quantum/acqw/kp8_kp8" /
                  row["id"] / "dipole_moment_matrix_elements_growth_z.txt")
        native_error = None
        if native.is_file():
            values = np.loadtxt(native, skiprows=1)
            if values.shape != (len(energy)**2, 6):
                raise ValueError(f"Unexpected native dipole table dimensions: {native}")
            native_matrix = np.empty_like(zm)
            native_matrix[values[:, 0].astype(int)-1, values[:, 1].astype(int)-1] = values[:, 4] + 1j * values[:, 5]
            off_diagonal = ~np.eye(len(energy), dtype=bool)
            native_error = float(np.max(abs(native_matrix - zm)[off_diagonal]))
            native_dipole_max_error = max(native_dipole_max_error, native_error)
        labels = {}
        for label, seed in selected["selected"].items():
            pair = int(track[seed])
            best_alternative = float(max(similarity[seed, j] for j in range(len(track)) if j != pair))
            changed = bool(pair != seed)
            previous_pair_energy = None if previous_energy is None else float(previous_energy[2*seed:2*seed+2].mean())
            labels[label] = {"solver_states": [2 * pair + 1, 2 * pair + 2],
                             "pair_energy_eV": float(energy[2 * pair:2 * pair + 2].mean()),
                             "character": dict(zip(("CB", "HH", "LH", "SO"), map(float, pair_character[pair]))),
                             "well_fraction": float(localized[pair]),
                             "subspace_overlap": float(score[seed]),
                             "next_best_overlap": best_alternative,
                             "assignment_margin": None if np.isnan(margin[seed]) else float(margin[seed]),
                             "energy_change_from_previous_eV": None if previous_pair_energy is None else
                             float(energy[2*pair:2*pair+2].mean() - previous_pair_energy),
                             "solver_pair_reassigned_from_k0": changed,
                             "flag": bool(score[seed] < c["tracking"]["min_overlap"] or
                                          margin[seed] < c["tracking"]["minimum_margin"])}
            item = labels[label]
            table.append([row["id"], row["ky_per_nm"], label, *item["solver_states"],
                          item["pair_energy_eV"], *item["character"].values(), item["well_fraction"],
                          item["subspace_overlap"], item["next_best_overlap"], item["assignment_margin"],
                          item["energy_change_from_previous_eV"], int(changed), int(item["flag"])])
        np.savez_compressed(output / "matrix_blocks" / f"{row['id']}.npz",
                            k_per_nm=row["ky_per_nm"], energy_eV=energy,
                            z_matrix_nm=zm, component_overlap=tensor,
                            pair_to_solver=track, pair_overlap=score,
                            components=np.array(io.KP8_COMPONENTS))
        finite_phases = np.angle(zm[abs(zm) > 1e-6])
        results.append({"id": row["id"], "ky_per_nm": row["ky_per_nm"],
                        "nearest_dispersion_index": row["nearest_dispersion_index"],
                        "nearest_dispersion_k_gap_per_nm": row["nearest_dispersion_k_gap_per_nm"],
                        "normalization_max_error": float(np.max(abs(norm - 1))),
                        "composition_sum_max_error": float(np.max(abs(observed.sum(axis=1) - 1))),
                        "matrix_diagnostics": {
                            "growth_position_shape": list(zm.shape), "growth_position_units": "nm",
                            "component_overlap_shape": list(tensor.shape),
                            "finite": bool(np.isfinite(zm).all() and np.isfinite(tensor).all()),
                            "growth_position_hermitian_max_error_nm": float(np.max(abs(zm - zm.conj().T))),
                            "growth_position_max_abs_nm": float(np.max(abs(zm))),
                            "nonzero_raw_phase_min_rad": float(np.min(finite_phases)),
                            "nonzero_raw_phase_max_rad": float(np.max(finite_phases)),
                            "native_growth_offdiagonal_max_abs_difference_nm": native_error},
                        "labels": labels})
        previous = normalized[np.concatenate([np.arange(2*j, 2*j+2) for j in track])]
        previous_energy = energy[np.concatenate([np.arange(2*j, 2*j+2) for j in track])]
    with (output / "tracking.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["frame", "ky_per_nm", "state", "solver_state_1", "solver_state_2",
                         "energy_eV", "CB", "HH", "LH", "SO", "well_fraction",
                         "overlap_previous", "next_best_overlap", "assignment_margin",
                         "energy_change_eV", "reassigned_from_k0", "weak_overlap_or_margin"])
        writer.writerows(table)
    summary = {"model": "29A full-8-band pilot analysis; no chi2 spectrum",
               "temperature_K": 300, "source_run": str(run.resolve()),
               "integration_grid_points": grid["points"],
               "target_path_complete_frames": len(rows),
               "native_growth_dipole_offdiagonal_max_abs_difference_nm": native_dipole_max_error,
               "k0_selection": selected, "frames": results,
               "optical_mapping": "UNRESOLVED; position matrices alone do not supply interband optical operator"}
    (output / "pilot_analysis.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, default=ROOT / "outputs/29A_full8band_baseline/pilot_analysis")
    args = p.parse_args(argv)
    try:
        result = analyze(args.input, args.output)
        print(json.dumps({key: value for key, value in result.items() if key != "frames"}, indent=2))
        print(f"Target path frames: {result['target_path_complete_frames']}; details: {args.output / 'pilot_analysis.json'}")
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
