"""Plot actual 8-band pilot state-output points against the target dispersion path."""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = json.loads(args.diagnostic.read_text(encoding="utf-8"))
    grid = report["integration_grid"]["rows"]
    kmax = report["dispersion"]["k_max_per_nm"]
    if not grid or report["dispersion"]["points"] != 301:
        raise ValueError("Expected complete integration diagnostic and 301-point dispersion")
    ky = np.array([r["ky_per_nm"] for r in grid])
    kz = np.array([r["kz_per_nm"] for r in grid])
    on_path = np.array([r["on_target_path"] for r in grid])
    in_range = np.array([r["within_target_range"] for r in grid])
    fig, (ax, detail) = plt.subplots(1, 2, figsize=(11, 4.5),
                                      gridspec_kw={"width_ratios": [1, 1.15]})
    angle = np.linspace(0, 2*np.pi, 300)
    ax.plot(kmax*np.cos(angle), kmax*np.sin(angle), color="0.65", ls="--", lw=1,
            label="|k| = 0.10π/a")
    ax.plot([0, kmax], [0, 0], color="tab:orange", lw=2,
            label="301-point Γ→+y path")
    ax.scatter(ky[~in_range], kz[~in_range], s=20, color="0.7", label="outside range")
    ax.scatter(ky[in_range & ~on_path], kz[in_range & ~on_path], s=28,
               color="tab:blue", label="inside range, off path")
    ax.scatter(ky[on_path], kz[on_path], s=45, color="tab:red", zorder=3,
               label="states on target path")
    ax.set(xlabel=r"$k_y$ (nm$^{-1}$)", ylabel=r"$k_z$ (nm$^{-1}$)",
           title="300 K finite-k state grid")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    dense = np.linspace(0, kmax, 301)
    detail.plot(dense, np.zeros_like(dense), color="tab:orange", lw=4,
                label="301 dispersion energies")
    detail.scatter(ky[on_path], np.ones(on_path.sum()), color="tab:red", s=65,
                   label="exported 8-band spinors", zorder=3)
    detail.set(xlim=(-0.02, kmax + 0.02), ylim=(-0.45, 1.45),
               xlabel=r"positive $k_y$ (nm$^{-1}$)", title="Target interval: 0 to 0.10π/a")
    detail.set_yticks([0, 1], ["energies", "spinors"])
    detail.legend(fontsize=8, frameon=False, loc="upper left")
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=200)
    plt.close(fig)
    print(f"Wrote {args.output}; on-path spinor frames: {on_path.sum()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
