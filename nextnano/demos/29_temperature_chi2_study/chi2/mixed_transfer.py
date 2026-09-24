"""Pack and verify the minimal same-temperature 29C mixed-control solver files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

from . import parse_nextnano as io
from .mixed_control import validate_control_run


ROOT = Path(__file__).resolve().parents[1]
RAW = {
    "kp8": ("dispersion_Gamma_to_y.dat", "kVectors_Gamma_to_y.dat",
            "energy_spectrum_k00000.dat", "spinor_composition_k00000_CbHhLhSo.dat"),
    "singleband_case04_graded": ("Gamma/energy_spectrum_k00000.dat",
                                 "Gamma/envelopes_k00000.dat",
                                 "HH/energy_spectrum_k00000.dat",
                                 "HH/envelopes_k00000.dat"),
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_for(root: Path, pattern: str) -> Path:
    alternatives = {"energy_spectrum_k00000.dat": "k00000/energy_spectrum.dat",
                    "spinor_composition_k00000_CbHhLhSo.dat":
                    "k00000/spinor_composition_CbHhLhSo.dat"}
    choices = [p for candidate in (pattern, alternatives.get(pattern)) if candidate
               for p in root.rglob(candidate) if p.is_file()]
    if len(choices) != 1:
        raise ValueError(f"Expected one {pattern} in {root}; found {len(choices)}")
    return choices[0]


def validate(folder: Path) -> dict:
    result = validate_control_run(folder)
    manifest = json.loads((folder / "mixed_transfer_manifest.json").read_text(encoding="utf-8"))
    files = {p.relative_to(folder).as_posix(): p for p in folder.rglob("*") if p.is_file()}
    files.pop("mixed_transfer_manifest.json", None)
    if set(files) != set(manifest["sha256"]):
        raise ValueError("Mixed transfer file inventory differs from manifest")
    for name, expected in manifest["sha256"].items():
        if digest(files[name]) != expected:
            raise ValueError(f"Mixed transfer checksum mismatch: {name}")
    if result["temperature_K"] != manifest["temperature_K"]:
        raise ValueError("Mixed transfer temperature mismatch")
    return {**result, "raw_scientific_files": 8, "total_files": len(files)}


def pack(run: Path, destination: Path, archive: Path) -> dict:
    status = validate_control_run(run)
    t = status["temperature_K"]
    if destination.exists() or archive.exists():
        raise ValueError("Refusing to overwrite mixed transfer folder or ZIP")
    destination.mkdir(parents=True)
    for name in ("run_metadata.json", "kp8.log", "kp8_parse.log",
                 "singleband_case04_graded.log", "singleband_case04_graded_parse.log"):
        shutil.copy2(run / name, destination / name)
    (destination / "decks").mkdir()
    for job in RAW:
        shutil.copy2(run / "decks" / f"{job}.in", destination / "decks" / f"{job}.in")
        for pattern in RAW[job]:
            source = source_for(run / job, pattern)
            target = destination / job / source.relative_to(run / job)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    hashes = {p.relative_to(destination).as_posix(): digest(p)
              for p in sorted(destination.rglob("*")) if p.is_file()}
    (destination / "mixed_transfer_manifest.json").write_text(json.dumps({
        "format": "demo29-mixed-raw-v1", "temperature_K": t,
        "model": "29C historical mixed 8-band dispersion plus single-band anchors/matrices",
        "sha256": hashes}, indent=2) + "\n", encoding="utf-8")
    result = validate(destination)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(destination.rglob("*")):
            if p.is_file():
                z.write(p, (Path(destination.name) / p.relative_to(destination)).as_posix())
    return {**result, "archive": str(archive), "archive_bytes": archive.stat().st_size}


def unpack(archive: Path, destination: Path) -> dict:
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if not names or any(".." in Path(n).parts or Path(n).is_absolute() for n in names):
            raise ValueError("Unsafe mixed transfer ZIP")
        roots = {Path(n).parts[0] for n in names}
        if len(roots) != 1:
            raise ValueError("Expected one top-level mixed transfer folder")
        folder = destination / next(iter(roots))
        if folder.exists():
            raise ValueError(f"Refusing to overwrite {folder}")
        destination.mkdir(parents=True, exist_ok=True)
        z.extractall(destination)
    return validate(folder)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pack", type=Path, help="completed work-laptop 100K or 500K run")
    mode.add_argument("--unpack", type=Path, help="ZIP returned to HOME")
    mode.add_argument("--validate", type=Path, help="unpacked mixed folder")
    parser.add_argument("--to", type=Path, help="new folder for --pack, parent for --unpack")
    parser.add_argument("--zip", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.pack:
            t = validate_control_run(args.pack)["temperature_K"]
            folder = args.to or ROOT / "nextnano/transfer" / f"demo29_{t}K_mixed_raw"
            archive = args.zip or ROOT / "nextnano/transfer" / f"demo29_{t}K_mixed_raw.zip"
            result = pack(args.pack, folder, archive)
        elif args.unpack:
            result = unpack(args.unpack, args.to or ROOT.parents[2] / "nextnano_raw")
        else:
            result = validate(args.validate)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
