"""Plot state character and position matrices from an analyzed 300 K pilot."""
from pathlib import Path
import argparse
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads((args.analysis / "pilot_analysis.json").read_text(encoding="utf-8"))
    rows = []
    for frame in report["frames"]:
        with np.load(args.analysis / "matrix_blocks" / f"{frame['id']}.npz") as block:
            tensor = block["component_overlap"]
            position = block["z_matrix_nm"]
        pairs = {name: np.asarray(frame["labels"][name]["solver_states"]) - 1
                 for name in ("e1", "e2", "hh1", "hh2")}
        character = {}
        for name, states in pairs.items():
            components = np.array([[tensor[s, s, j, j].real for j in range(8)]
                                   for s in states]).mean(axis=0)
            character[name] = components.reshape(4, 2).sum(axis=1)

        def position_strength(left: str, right: str) -> float:
            # Frobenius norm of a two-doublet block, scaled per state pair.
            return float(np.linalg.norm(position[np.ix_(pairs[left], pairs[right])]) / 2)

        energies = {name: frame["labels"][name]["pair_energy_eV"] for name in pairs}
        rows.append({"k": frame["ky_per_nm"], "energy": energies, "character": character,
                     "position": {"e1-e2": position_strength("e1", "e2"),
                                  "hh1-hh2": position_strength("hh1", "hh2"),
                                  "e1-hh1": position_strength("e1", "hh1")},
                     "hh2_flag": frame["labels"]["hh2"]["flag"]})

    k = np.array([row["k"] for row in rows])
    fig, axes = plt.subplots(3, 1, figsize=(8, 10), sharex=True, constrained_layout=True)
    for name, color in (("e1-hh1", "#1f77b4"), ("e1-hh2", "#ff7f0e"),
                        ("e2-hh1", "#2ca02c"), ("e2-hh2", "#9467bd")):
        e, h = name.split("-")
        axes[0].plot(k, [row["energy"][e] - row["energy"][h] for row in rows],
                     marker="o", label=name, color=color)
    axes[0].set_ylabel("Doublet energy difference (eV)")
    axes[0].set_title("300 K full-8-band pilot: exported target-path states")
    axes[0].legend(ncol=2, fontsize=9)

    for name, color in (("hh1", "#1f77b4"), ("hh2", "#ff7f0e")):
        axes[1].plot(k, [row["character"][name][1] for row in rows],
                     marker="o", label=f"{name} HH", color=color)
        axes[1].plot(k, [row["character"][name][2] for row in rows],
                     marker="s", linestyle="--", label=f"{name} LH", color=color)
    axes[1].set_ylabel("Spinor fraction")
    axes[1].set_ylim(0, 1.05)
    axes[1].legend(ncol=2, fontsize=9)

    for name, color in (("e1-e2", "#1f77b4"), ("hh1-hh2", "#ff7f0e"),
                        ("e1-hh1", "#2ca02c")):
        axes[2].plot(k, [row["position"][name] for row in rows],
                     marker="o", label=name, color=color)
    axes[2].set_ylabel("Growth-position block strength (nm)")
    axes[2].set_xlabel("k along Γ→+y (nm⁻¹)")
    axes[2].legend(ncol=3, fontsize=9)
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.set_xlim(0, 0.555714439232)
    for row in rows:
        if row["hh2_flag"]:
            for axis in axes:
                axis.axvline(row["k"], color="crimson", linestyle=":", alpha=0.75)
    axes[2].text(0.52, 0.88, "Dotted red: hh2 tracking flagged", transform=axes[2].transAxes,
                 color="crimson", fontsize=9)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    plt.close(fig)
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
