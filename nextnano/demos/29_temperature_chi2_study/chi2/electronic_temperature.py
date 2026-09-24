"""Compare tracked k=0 state and transition energies across returned temperatures."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .acquisition import ROOT


def source(t: int) -> Path:
    stage = "29A_full8band_baseline" if t == 300 else "29B_temperature_full8band"
    return ROOT / "outputs" / stage / f"{t}K_prepared/tracked_states.csv"


def summarize(out: Path) -> None:
    if out.exists():
        raise ValueError("Refusing to overwrite electronic temperature summary")
    rows = []
    for t in (100,300,500):
        metadata = json.loads((source(t).parent / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("selected_pair_ambiguities") or metadata.get("selected_character_change_flags"):
            raise ValueError(f"Unresolved tracked-state flags at {t} K")
        if t != 300 and (not metadata.get("cross_temperature_k0") or
                         not all(row["consistent"] for row in metadata["cross_temperature_k0"].values())):
            raise ValueError(f"Unresolved cross-temperature k=0 state matching at {t} K")
        with source(t).open(newline="", encoding="utf-8") as f:
            selected = {r["label"]: r for r in csv.DictReader(f) if r["k_index"] == "0"}
        if set(selected) != {"e1","e2","hh1","hh2"}:
            raise ValueError(f"Incomplete k=0 tracked labels at {t} K")
        energy = {label: float(r["pair_energy_eV"]) for label,r in selected.items()}
        if any(int(r["ambiguous"]) or int(r["character_change"]) for r in selected.values()):
            raise ValueError(f"Unresolved k=0 state flag at {t} K")
        rows.append({"temperature_K":t, **energy,
                     **{f"E_{e}_{h}_eV":energy[e]-energy[h]
                        for e in ("e1","e2") for h in ("hh1","hh2")}})
    out.mkdir(parents=True)
    with (out / "k0_energies_and_transitions.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    fig, ax = plt.subplots(figsize=(6.5,4))
    for key in ("E_e1_hh1_eV","E_e1_hh2_eV","E_e2_hh1_eV","E_e2_hh2_eV"):
        ax.plot([r["temperature_K"] for r in rows], [r[key] for r in rows], "-o", label=key)
    ax.set(xlabel="solver temperature (K)", ylabel="k=0 transition energy (eV)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "k0_transition_energies.png", dpi=200)
    plt.close(fig)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "outputs/comparison/electronic_structure")
    a = p.parse_args(argv)
    try:
        summarize(a.output)
        print("Wrote k=0 state/transition temperature summary")
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
