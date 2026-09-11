"""DEVELOPER TOOL - not needed to run the package.

Copies the legitimate cached nextnano++ Professional output and reference decks
from this repository into Demo26_Condensed/cached_raw and validation/decks, and
records SHA-256 provenance. Files are byte-for-byte copies; nothing is computed.

Run from the repository that contains the historical Demo 20/23/27 data:
    python tools/build_fixtures.py --repo <repository root>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
COMPONENTS = ["cb1", "cb2", "hh1", "hh2", "lh1", "lh2", "so1", "so2"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=PKG.parents[2])
    repo = ap.parse_args().repo.resolve()

    kp8_run = repo / "demo_results/demo23/raw/production_y_n301_k0100/production_y_n301_k0100"
    sb_run = repo / "docs/case_04/nextnano_output/case"
    kp8_files = [
        "production_y_n301_k0100.in", "simulation_info.txt",
        "bias_00000/QuantumDispersions/acqw/kp8/dispersion_Gamma_to_y.dat",
        "bias_00000/QuantumDispersions/acqw/kp8/kVectors_Gamma_to_y.dat",
        "bias_00000/Quantum/acqw/kp8/energy_spectrum_k00000.dat",
        "bias_00000/Quantum/acqw/kp8/spinor_composition_k00000_CbHhLhSo.dat",
        "bias_00000/Quantum/acqw/kp8_kp8/dipole_moment_matrix_elements_k00000_growth_z.txt",
    ] + [f"bias_00000/Quantum/acqw/kp8/envelope_k00000_{s:04d}_{c}.dat"
         for s in range(1, 15) for c in COMPONENTS]
    sb_files = ["case.in", "simulation_info.txt"] + [
        f"bias_00000/Quantum/acqw/{band}/{name}"
        for band in ("Gamma", "HH") for name in ("energy_spectrum_k00000.dat", "envelopes_k00000.dat")]
    plan = [(kp8_run, PKG / "cached_raw/kp8", kp8_files),
            (sb_run, PKG / "cached_raw/singleband_case04_graded", sb_files)]
    decks = {
        "demo23_production_y_n301_k0100.in": "nextnano/demos/23_k_resolved_dispersion_validation/inputs/production_y_n301_k0100.in",
        "demo27G_bz_0p10_gamma_x.in": "nextnano/demos/27_physics/27G_kmax_and_bz_validation/inputs/bz_0p10_gamma_x.in",
        "demo27D_abrupt_paper_geometry.in": "nextnano/demos/27_physics/27D_exact_paper_geometry/inputs/abrupt_paper_geometry.in",
        "singleband_case04_graded.in": "demo_results/demo20/inputs/case_04/case.in",
        "singleband_case00_abrupt.in": "demo_results/demo20/inputs/case_00/case.in",
    }

    records = []
    for src_root, dst_root, names in plan:
        if dst_root.exists():
            shutil.rmtree(dst_root)
        for name in names:
            src, dst = src_root / name, dst_root / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            records.append({"bundled": dst.relative_to(PKG).as_posix(),
                            "source": src.relative_to(repo).as_posix(), "sha256": sha(dst)})
    deck_dir = PKG / "validation/decks"
    deck_dir.mkdir(parents=True, exist_ok=True)
    for name, rel in decks.items():
        shutil.copy2(repo / rel, deck_dir / name)
        records.append({"bundled": f"validation/decks/{name}", "source": rel, "sha256": sha(deck_dir / name)})

    # Retire the interrupted agent's earlier fixture layout (same sources, new names).
    for old in ("cached_raw/dispersion", "cached_raw/matrices_baseline"):
        if (PKG / old).exists():
            shutil.rmtree(PKG / old)
    old_ckpt = PKG / "cached_raw/supplied_case00_matrix_checkpoint.json"
    new_ckpt = PKG / "cached_raw/supplied/case00_abrupt_matrix_elements.json"
    if old_ckpt.exists():
        new_ckpt.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(old_ckpt.read_text())
        new_ckpt.write_text(json.dumps(data, indent=2) + "\n")
        old_ckpt.unlink()
    records.append({"bundled": new_ckpt.relative_to(PKG).as_posix(),
                    "source": "demo_results/demo19/tables/demo19_master_results.csv (case_00 row, PROCESSED values)",
                    "sha256": sha(new_ckpt)})

    (PKG / "cached_raw/fixture_manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"copied {len(records)} files; manifest cached_raw/fixture_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
