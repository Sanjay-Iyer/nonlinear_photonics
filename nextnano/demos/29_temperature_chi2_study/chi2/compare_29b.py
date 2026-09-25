"""Compare 100/300/500 K full-8-band electronic structure without calculating chi2."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np

from . import parse_nextnano as io, run_debug, temperature_study
from .full8 import matrix_data, pair_score
from .pilot_analysis import _state_frame, analyze
from .sampling import block_strength

LABELS = ("e1", "e2", "hh1", "hh2")
BLOCKS = (("e1", "e2"), ("hh1", "hh2"))


def _csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _k0_spinors(root: Path) -> tuple[np.ndarray, dict]:
    report = run_debug.scan_output(root)
    zero = next((row for row in report["integration_grid"]["rows"] if
                 row["on_target_path"] and row["magnitude_per_nm"] < 1e-8), None)
    if zero is None or not zero["complex_spinors_complete"]:
        raise ValueError(f"Missing complete k=0 spinors in {root}")
    _, z, psi, _ = _state_frame(Path(zero["state_folder"]), 14)
    normalized, _, _, _ = matrix_data(z, psi)
    return normalized, {"z": z, "row": zero}


def compare(raw: dict[int, Path], output: Path) -> dict:
    if output.exists():
        raise ValueError(f"Refusing to overwrite {output}")
    if set(raw) != {100, 300, 500}:
        raise ValueError("Supply the 100, 300 and 500 K raw solver directories explicitly")
    provenance = temperature_study.check_decks(raw[300])
    for t in (100, 300, 500):
        temperature_study.validate_run(raw[t], t)
    output.mkdir(parents=True)
    summaries = {}
    for t in (100, 300, 500):
        name = "300K_reference" if t == 300 else f"{t}K"
        summaries[t] = analyze(raw[t], output / name)
        if summaries[t]["temperature_K"] != t:
            raise ValueError(f"Analysis temperature mismatch for {t} K")
    k_arrays = {t: np.array([f["ky_per_nm"] for f in summaries[t]["frames"]]) for t in raw}
    if (any(len(k_arrays[t]) != len(k_arrays[300]) or
            not np.allclose(k_arrays[t], k_arrays[300], atol=1e-9, rtol=0)
            for t in (100, 500))):
        raise ValueError("Target-path finite-k samples differ from the 300 K reference")
    ref_psi, ref_meta = _k0_spinors(raw[300])
    state_rows, transition_rows, finite_rows, position_rows, native_rows = [], [], [], [], []
    cross_temperature = {}
    for t in (100, 300, 500):
        summary = summaries[t]
        psi, meta = _k0_spinors(raw[t])
        if not np.array_equal(meta["z"], ref_meta["z"]):
            raise ValueError(f"Spatial grid differs at {t} K")
        overlap = pair_score(ref_psi, psi, io.trapezoid_weights(meta["z"]))
        seed_ref = summaries[300]["k0_selection"]["selected"]
        seed_t = summary["k0_selection"]["selected"]
        cross_temperature[t] = {}
        k0 = summary["frames"][0]["labels"]
        energies = {label: k0[label]["pair_energy_eV"] for label in LABELS}
        for label in LABELS:
            r, current = seed_ref[label], seed_t[label]
            best = int(np.argmax(overlap[r]))
            cross_temperature[t][label] = {"reference_pair": r,
                "selected_pair": current, "best_overlap_pair": best,
                "selected_overlap": float(overlap[r, current]),
                "consistent": bool(best == current and overlap[r, current] >= .5)}
            item = k0[label]
            state_rows.append({"temperature_K": t, "state": label,
                "solver_states": ",".join(map(str, item["solver_states"])),
                "energy_eV": item["pair_energy_eV"], **item["character"],
                "well_fraction": item["well_fraction"],
                "k0_overlap_to_300K": cross_temperature[t][label]["selected_overlap"],
                "k0_best_pair_matches": cross_temperature[t][label]["consistent"]})
        for electron in ("e1", "e2"):
            for hole in ("hh1", "hh2"):
                transition_rows.append({"temperature_K": t,
                                        "transition": f"E{electron[1]}{hole[2]}",
                                        "electron": electron, "hole": hole,
                                        "energy_eV": energies[electron] - energies[hole]})
        for frame in summary["frames"]:
            k = frame["ky_per_nm"]
            labels = frame["labels"]
            for label in LABELS:
                item = labels[label]
                finite_rows.append({"temperature_K": t, "frame": frame["id"], "ky_per_nm": k,
                    "state": label, "solver_states": ",".join(map(str, item["solver_states"])),
                    "energy_eV": item["pair_energy_eV"], **item["character"],
                    "well_fraction": item["well_fraction"],
                    "overlap_previous": item["subspace_overlap"],
                    "next_best_overlap": item["next_best_overlap"],
                    "reassigned_from_k0": item["solver_pair_reassigned_from_k0"],
                    "weak_tracking_flag": item["flag"]})
            with np.load(output / ("300K_reference" if t == 300 else f"{t}K") /
                         "matrix_blocks" / f"{frame['id']}.npz") as block:
                matrix = block["z_matrix_nm"]
            for left, right in BLOCKS:
                position_rows.append({"temperature_K": t, "frame": frame["id"],
                    "ky_per_nm": k, "block": f"{left}-{right}",
                    "frobenius_per_doublet_nm": block_strength(matrix,
                        labels[left]["solver_states"], labels[right]["solver_states"])})
            native = frame.get("native_tables", {})
            for table, details in native.items():
                native_rows.append({"temperature_K": t, "frame": frame["id"],
                    "ky_per_nm": k, "table": table, "finite": details["finite"],
                    "max_abs": details["max_abs"],
                    "e1_e2_block": details["e1_e2_block"],
                    "hh1_hh2_block": details["hh1_hh2_block"]})
    if not native_rows or any(not row["finite"] for row in native_rows):
        raise ValueError("Native dipole/momentum temperature comparison is incomplete")
    comparison = output / "comparison"
    comparison.mkdir()
    _csv(comparison / "selected_states_vs_temperature.csv", state_rows)
    _csv(comparison / "transitions_vs_temperature.csv", transition_rows)
    _csv(comparison / "finite_k_states.csv", finite_rows)
    _csv(comparison / "position_blocks_vs_k.csv", position_rows)
    _csv(comparison / "native_dipole_momentum_vs_k.csv", native_rows)
    states_by_key = {(row["temperature_K"], row["state"]): row for row in state_rows}
    transitions_by_key = {(row["temperature_K"], row["transition"]): row for row in transition_rows}
    major_changes = []
    for t in (100, 500):
        for label in LABELS:
            current, baseline = states_by_key[t, label], states_by_key[300, label]
            major_changes.append({"temperature_K": t, "quantity": label,
                "kind": "state", "delta_eV": current["energy_eV"] - baseline["energy_eV"],
                "delta_CB": current["CB"] - baseline["CB"],
                "delta_HH": current["HH"] - baseline["HH"],
                "delta_LH": current["LH"] - baseline["LH"],
                "delta_SO": current["SO"] - baseline["SO"],
                "delta_well_fraction": current["well_fraction"] - baseline["well_fraction"],
                "k0_overlap_to_300K": current["k0_overlap_to_300K"],
                "k0_best_pair_matches": current["k0_best_pair_matches"]})
        for code in ("E11", "E12", "E21", "E22"):
            current, baseline = transitions_by_key[t, code], transitions_by_key[300, code]
            major_changes.append({"temperature_K": t, "quantity": code,
                "kind": "transition", "delta_eV": current["energy_eV"] - baseline["energy_eV"],
                "delta_CB": "", "delta_HH": "", "delta_LH": "", "delta_SO": "",
                "delta_well_fraction": "", "k0_overlap_to_300K": "",
                "k0_best_pair_matches": ""})
    _csv(comparison / "major_changes_vs_300K.csv", major_changes)
    selected = {t: summaries[t]["frames"][0]["labels"] for t in raw}
    shifts = {str(t): {label: selected[t][label]["pair_energy_eV"] -
                      selected[300][label]["pair_energy_eV"] for label in LABELS}
              for t in (100, 500)}
    report = {"status": "PASS", "model": "full-8-band electronic structure only; no chi2",
              "reference": provenance, "raw_roots": {str(t): str(raw[t].resolve()) for t in raw},
              "target_path_k_per_nm": list(map(float, k_arrays[300])),
              "k0_state_energy_shifts_from_300K_eV": shifts,
              "cross_temperature_k0_subspace_match": cross_temperature,
              "weak_tracking_flags": {str(t): {label: sum(frame["labels"][label]["flag"]
                  for frame in summaries[t]["frames"]) for label in LABELS} for t in raw},
              "native_growth_dipole_max_difference_nm": {str(t): summaries[t][
                  "native_growth_dipole_offdiagonal_max_abs_difference_nm"] for t in raw},
              "optical_operator": "UNRESOLVED; no full-8-band chi2 spectrum calculated",
              "temperature_scope": "nextnano solver temperature affects electronic structure; no explicit carrier occupations"}
    (comparison / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _plots(comparison, state_rows, transition_rows, finite_rows, position_rows)
    return report


def _plots(output: Path, states: list[dict], transitions: list[dict],
           finite: list[dict], positions: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures = (("k0_state_energies.png", states, "state", "energy_eV", "energy (eV)", LABELS),
               ("k0_transitions.png", transitions, "transition", "energy_eV", "transition energy (eV)",
                ("E11", "E12", "E21", "E22")),
               ("k0_hh_character.png", states, "state", "HH", "HH fraction", ("hh1", "hh2")),
               ("k0_lh_character.png", states, "state", "LH", "LH fraction", ("hh1", "hh2")))
    for filename, rows, key, value, ylabel, labels in figures:
        fig, ax = plt.subplots(figsize=(6.4, 4))
        for label in labels:
            series = sorted((r for r in rows if r[key] == label), key=lambda r: r["temperature_K"])
            ax.plot([r["temperature_K"] for r in series], [r[value] for r in series], "-o", label=label)
        ax.set(xlabel="solver temperature (K)", ylabel=ylabel)
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)
    for filename, source, x, series_key, y, keys in (
        ("finite_k_hh_character.png", finite, "ky_per_nm", "state", "HH", ("hh1", "hh2")),
        ("finite_k_lh_character.png", finite, "ky_per_nm", "state", "LH", ("hh1", "hh2")),
        ("position_blocks_vs_k.png", positions, "ky_per_nm", "block", "frobenius_per_doublet_nm",
         ("e1-e2", "hh1-hh2"))):
        fig, axes = plt.subplots(1, len(keys), figsize=(10, 3.8), sharex=True)
        for ax, key in zip(axes, keys):
            for t in (100, 300, 500):
                series = sorted((r for r in source if r[series_key] == key and
                                 r["temperature_K"] == t), key=lambda r: r[x])
                ax.plot([r[x] for r in series], [r[y] for r in series], "-o", label=f"{t} K")
            ax.set(xlabel="ky (nm⁻¹)", ylabel=y, title=key)
            ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for t in (100, 300, 500):
        p.add_argument(f"--raw-{t}", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = compare({t: getattr(args, f"raw_{t}") for t in (100, 300, 500)}, args.output)
        print(json.dumps({k: v for k, v in report.items() if k != "reference"}, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
