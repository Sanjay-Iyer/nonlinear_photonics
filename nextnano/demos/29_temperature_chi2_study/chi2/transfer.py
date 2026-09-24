"""Lossless per-k 8-band transfer, plus the eight raw mixed-control inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
import numpy as np

from . import parse_nextnano as io
from .acquisition import config, job_decks
from . import decks

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = io.KP8_COMPONENTS


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def find_one(root: Path, name: str) -> Path:
    matches = [p for p in root.rglob(name) if p.is_file()]
    if len(matches) != 1:
        raise ValueError(f"Expected one {name} below {root}; found {len(matches)}")
    return matches[0]


def raw_frames(kp8: Path, expected_n: int):
    k, dispersion, direction = io.read_dispersion(kp8)
    if dispersion.shape != (len(k), expected_n):
        raise ValueError("Unexpected 8-band state count")
    lookup = {}
    for path in kp8.rglob("*"):
        if path.is_file():
            lookup.setdefault(path.name, []).append(path)
    def one(name: str) -> Path:
        matches = lookup.get(name, [])
        if len(matches) != 1:
            raise ValueError(f"Expected one {name} below {kp8}; found {len(matches)}")
        return matches[0]
    for i, ki in enumerate(k):
        spectrum = one(f"energy_spectrum_k{i:05d}.dat")
        composition = one(f"spinor_composition_k{i:05d}_CbHhLhSo.dat")
        energy = io.read_energy_spectrum(spectrum)
        if energy.shape != (expected_n,) or not np.allclose(energy, dispersion[i], atol=1e-7, rtol=0):
            raise ValueError(f"Energy/dispersion mismatch at k={i}")
        _, data = io.read_table(composition)
        if not np.array_equal(data[:, 0], np.arange(1, expected_n + 1)):
            raise ValueError(f"State-ID mismatch at k={i}")
        parsed = io.read_composition(composition)
        comp = np.column_stack([parsed[name] for name in COMPONENTS])
        if comp.shape != (expected_n, 8) or not np.isfinite(comp).all() or not np.allclose(comp.sum(axis=1), 1, atol=2e-5):
            raise ValueError(f"Invalid composition at k={i}")
        states = []
        z = None
        files = [spectrum, composition]
        for s in range(1, expected_n + 1):
            parts = []
            for name in COMPONENTS:
                path = one(f"envelope_k{i:05d}_{s:04d}_{name}.dat")
                files.append(path)
                _, tab = io.read_table(path)
                if tab.shape[1] != 3:
                    raise ValueError(f"Expected z, real, imag: {path}")
                if z is None:
                    z = tab[:, 0].copy()
                    io.trapezoid_weights(z)
                elif not np.array_equal(z, tab[:, 0]):
                    raise ValueError(f"Spatial grid mismatch at k={i}")
                parts.append(tab[:, 1] + 1j * tab[:, 2])
            states.append(parts)
        psi = np.asarray(states, dtype=np.complex128)
        if not np.isfinite(psi).all():
            raise ValueError(f"Nonfinite spinors at k={i}")
        yield i, float(ki), energy, z, psi, comp, files


def packed_frames(bundle: Path):
    meta = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
    for i in range(meta["k_points"]):
        with np.load(bundle / "full8/frames" / f"k{i:05d}.npz", allow_pickle=False) as d:
            yield (int(d["k_index"]), float(d["k_per_nm"]), d["energy_eV"].copy(),
                   d["z_nm"].copy(), d["psi"].copy(), d["composition"].copy(),
                   d["solver_state"].copy())


def validate(bundle: Path) -> dict:
    c = config()
    meta = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
    t = int(meta["temperature_K"])
    if t not in c["temperatures_K"] or meta["k_points"] != c["k_points"] or meta["candidate_states"] != c["num_electrons"] + c["num_holes"]:
        raise ValueError("Bundle temperature/grid/state count mismatch")
    expected = np.linspace(0, c["k_max_per_nm"], c["k_points"])
    with np.load(bundle / "full8/dispersion.npz", allow_pickle=False) as d:
        k, e, direction = d["k_per_nm"], d["energy_eV"], d["direction"]
    if k.shape != expected.shape or not np.allclose(k, expected, atol=5e-10, rtol=0) or not np.allclose(direction, [0, 1, 0], atol=1e-7):
        raise ValueError("Wrong k grid or direction")
    if e.shape != (len(k), meta["candidate_states"]):
        raise ValueError("Wrong dispersion shape")
    run = json.loads((bundle / "run_metadata.json").read_text(encoding="utf-8"))
    if run.get("temperature_K") != t or run.get("pilot") or run.get("source_config") != c:
        raise ValueError("Run provenance/configuration differs from Demo 29 production")
    if set(run.get("jobs", {})) != {"kp8", "singleband_case04_graded"} or any(
            j.get("status") != "PASS" for j in run["jobs"].values()):
        raise ValueError("Both solver jobs must have completed")
    for name, expected_deck in job_decks(t, c).items():
        if not decks.same_deck((bundle / "decks" / f"{name}.in").read_text(encoding="utf-8"), expected_deck):
            raise ValueError(f"Executed {name} deck does not match the temperature configuration")
    seen = 0
    for i, ki, energy, z, psi, comp, ids in packed_frames(bundle):
        if i != seen or abs(ki - expected[i]) > 5e-10 or not np.array_equal(ids, np.arange(1, meta["candidate_states"] + 1)):
            raise ValueError(f"Frame index/k/state IDs inconsistent at {i}")
        if psi.shape != (meta["candidate_states"], 8, len(z)) or psi.dtype != np.complex128:
            raise ValueError(f"Wrong spinor shape/type at {i}")
        if comp.shape != (meta["candidate_states"], 8) or not np.isfinite(psi).all() or not np.isfinite(comp).all():
            raise ValueError(f"Nonfinite or malformed frame {i}")
        if not np.array_equal(energy, e[i]) or not np.allclose(comp.sum(axis=1), 1, atol=2e-5):
            raise ValueError(f"Frame energies/composition inconsistent at {i}")
        seen += 1
    if seen != c["k_points"]:
        raise ValueError("Incomplete finite-k frames")
    mixed = bundle / "mixed"
    for job, names in {"kp8": ("dispersion_Gamma_to_y.dat", "kVectors_Gamma_to_y.dat",
                               "energy_spectrum_k00000.dat", "spinor_composition_k00000_CbHhLhSo.dat"),
                       "singleband_case04_graded": ("energy_spectrum_k00000.dat", "envelopes_k00000.dat")}.items():
        for name in names:
            count = 2 if job.startswith("single") else 1
            matches = [p for p in (mixed / job).rglob(name) if p.is_file()]
            if len(matches) != count:
                raise ValueError(f"Missing mixed-control {job}/{name}: expected {count}, got {len(matches)}")
    mk, me, _ = io.read_dispersion(mixed / "kp8")
    if not np.allclose(mk, k, atol=5e-10, rtol=0) or not np.allclose(me, e, atol=1e-7, rtol=0):
        raise ValueError("Mixed-control kp8 dispersion differs from full-8-band frames")
    io.read_single_band(mixed / "singleband_case04_graded")
    comp_file = io.find_one(mixed / "kp8", "spinor_composition_k00000_CbHhLhSo.dat")
    parsed_comp = io.read_composition(comp_file)
    k0_comp = np.column_stack([parsed_comp[name] for name in COMPONENTS])
    with np.load(bundle / "full8/frames/k00000.npz", allow_pickle=False) as d:
        if not np.allclose(d["composition"], k0_comp, atol=2e-5, rtol=0):
            raise ValueError("Mixed-control k=0 composition differs from full-8-band frame")
    if not (bundle / "source_checksums.json").is_file():
        raise ValueError("Source raw-file checksum manifest missing")
    rows = json.loads((bundle / "checksums.json").read_text(encoding="utf-8"))
    actual = {p.relative_to(bundle).as_posix(): p for p in bundle.rglob("*") if p.is_file() and p.name != "checksums.json"}
    if {row["file"] for row in rows} != set(actual):
        raise ValueError("Incomplete checksum inventory")
    for row in rows:
        if sha(actual[row["file"]]) != row["sha256"]:
            raise ValueError("Checksum mismatch: " + row["file"])
    return {"status": "PASS", "temperature_K": t, "k_points": seen,
            "candidate_states": meta["candidate_states"], "files": len(actual)}


def pack(run_root: Path, output_dir: Path, archive: Path) -> dict:
    c = config()
    run_root = run_root.resolve()
    report = json.loads((run_root / "run_metadata.json").read_text(encoding="utf-8"))
    t = int(report["temperature_K"])
    if report.get("pilot") or t not in c["temperatures_K"] or not report.get("professional_execution_performed"):
        raise ValueError("Only completed production temperatures may be packaged")
    if set(report["jobs"]) != {"kp8", "singleband_case04_graded"} or any(j["status"] != "PASS" for j in report["jobs"].values()):
        raise ValueError("Both same-temperature solver jobs must pass")
    for name in ("kp8", "singleband_case04_graded"):
        body = (run_root / "decks" / f"{name}.in").read_text(encoding="utf-8")
        if f"temperature = {t}" not in body and f"temperature = {t}.0" not in body:
            raise ValueError(f"Wrong executed deck temperature: {name}")
    frames = list((run_root / "kp8").rglob("spinor_composition*CbHhLhSo.dat"))
    if len(frames) != c["k_points"]:
        raise ValueError(
            f"Full-8-band transfer needs {c['k_points']} spinor-composition frames; "
            f"this run has {len(frames)}. Preserve the original solver run. "
            "nextnano output_states/all_k_points covers the k-integration grid, "
            "not the separate dispersion path. The matched mixed control can "
            "still be analyzed from the original solver run."
        )
    if output_dir.exists() or archive.exists():
        raise ValueError("Refusing to overwrite transfer folder or zip")
    output_dir.mkdir(parents=True)
    (output_dir / "full8/frames").mkdir(parents=True)
    (output_dir / "decks").mkdir()
    for name in ("kp8", "singleband_case04_graded"):
        shutil.copy2(run_root / "decks" / f"{name}.in", output_dir / "decks" / f"{name}.in")
        shutil.copy2(run_root / f"{name}.log", output_dir / f"{name}.log")
        shutil.copy2(run_root / f"{name}_parse.log", output_dir / f"{name}_parse.log")
    shutil.copy2(run_root / "run_metadata.json", output_dir / "run_metadata.json")
    source_hashes = {}
    kp8 = run_root / "kp8"
    k, disp, direction = io.read_dispersion(kp8)
    expected = np.linspace(0, c["k_max_per_nm"], c["k_points"])
    if len(k) != c["k_points"] or not np.allclose(k, expected, atol=5e-10, rtol=0):
        raise ValueError("301-point 0.10 pi/a run required")
    np.savez_compressed(output_dir / "full8/dispersion.npz", k_per_nm=k, energy_eV=disp, direction=direction["direction"])
    n = c["num_electrons"] + c["num_holes"]
    for i, ki, energy, z, psi, comp, files in raw_frames(kp8, n):
        arrays = {"k_index": np.int64(i), "k_per_nm": np.float64(ki), "energy_eV": energy,
                  "z_nm": z, "psi": psi, "composition": comp,
                  "solver_state": np.arange(1, n + 1), "components": np.array(COMPONENTS)}
        path = output_dir / "full8/frames" / f"k{i:05d}.npz"
        np.savez_compressed(path, **arrays)
        with np.load(path, allow_pickle=False) as saved:
            if any(not np.array_equal(saved[key], value) for key, value in arrays.items()):
                raise ValueError(f"Lossless frame round-trip failed at {i}")
        for file in files:
            source_hashes[file.relative_to(run_root).as_posix()] = sha(file)
        if (i + 1) % 50 == 0:
            print(f"Packed {i+1}/{len(k)} finite-k frames", flush=True)
    mixed = output_dir / "mixed"
    for job, names in {"kp8": ("dispersion_Gamma_to_y.dat", "kVectors_Gamma_to_y.dat",
                               "energy_spectrum_k00000.dat", "spinor_composition_k00000_CbHhLhSo.dat"),
                       "singleband_case04_graded": ("Gamma/energy_spectrum_k00000.dat", "Gamma/envelopes_k00000.dat",
                                                   "HH/energy_spectrum_k00000.dat", "HH/envelopes_k00000.dat")}.items():
        for name in names:
            file = io.find_one(run_root / job, name)
            dest = mixed / job / file.relative_to(run_root / job)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)
            source_hashes[file.relative_to(run_root).as_posix()] = sha(file)
    # Small native records are retained for optical-operator and solver-version review.
    for source in run_root.rglob("*"):
        if source.is_file() and (source.name == "simulation_info.txt" or "matrix_elements" in source.name.lower()):
            dest = output_dir / "native_metadata" / source.relative_to(run_root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            source_hashes[source.relative_to(run_root).as_posix()] = sha(source)
    (output_dir / "source_checksums.json").write_text(json.dumps(source_hashes, indent=2) + "\n", encoding="utf-8")
    (output_dir / "bundle.json").write_text(json.dumps({"format": "demo29-full8-numeric-v1", "temperature_K": t,
        "k_points": len(k), "candidate_states": n, "precision": "complex128/float64; exact parsed-number round trip",
        "full_text_retained_on_work": True}, indent=2) + "\n", encoding="utf-8")
    rows = [{"file": p.relative_to(output_dir).as_posix(), "sha256": sha(p)}
            for p in sorted(output_dir.rglob("*")) if p.is_file()]
    (output_dir / "checksums.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    result = validate(output_dir)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in output_dir.rglob("*"):
            if p.is_file():
                z.write(p, (Path(output_dir.name) / p.relative_to(output_dir)).as_posix())
    return {**result, "archive": str(archive), "archive_bytes": archive.stat().st_size}


def unpack(archive: Path, destination: Path) -> dict:
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if not names or any(Path(name).is_absolute() or ".." in Path(name).parts or len(Path(name).parts) < 2 for name in names):
            raise ValueError("Unsafe or malformed transfer archive")
        roots = {Path(name).parts[0] for name in names}
        if len(roots) != 1 or not next(iter(roots)).endswith("K"):
            raise ValueError("Expected one temperature folder in archive")
        target = destination / next(iter(roots))
        if target.exists():
            raise ValueError(f"Refusing to overwrite {target}")
        destination.mkdir(parents=True, exist_ok=True)
        z.extractall(destination)
    return validate(target)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--pack", type=Path, help="completed work run folder")
    group.add_argument("--unpack", type=Path, help="returned zip")
    group.add_argument("--validate", type=Path, help="unpacked temperature folder")
    p.add_argument("--to", type=Path, help="transfer folder for --pack, raw root for --unpack")
    p.add_argument("--zip", type=Path, help="zip output for --pack")
    a = p.parse_args(argv)
    try:
        if a.pack:
            t = json.loads((a.pack / "run_metadata.json").read_text())["temperature_K"]
            result = pack(a.pack, a.to or ROOT / "nextnano/transfer" / f"{t}K",
                          a.zip or ROOT / f"demo29_{t}K_raw.zip")
        elif a.unpack:
            result = unpack(a.unpack, a.to or ROOT / "nextnano/raw")
        else:
            result = validate(a.validate)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
