"""Safely unpack and SHA-256 verify a Demo 29 scientific raw ZIP on HOME."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--destination", type=Path, required=True,
                   help="existing parent directory, normally nextnano_raw/demo29")
    args = p.parse_args()
    try:
        with zipfile.ZipFile(args.zip) as archive:
            members = [n for n in archive.namelist() if not n.endswith("/")]
            parts = [PurePosixPath(n).parts for n in members]
            if (not parts or any(len(item) < 2 or any(s in ("", ".", "..") for s in item)
                                 or ":" in item[0] for item in parts)):
                raise ValueError("Archive contains unsafe paths")
            roots = {item[0] for item in parts}
            if len(roots) != 1:
                raise ValueError("Archive must contain exactly one run root")
            root_name = roots.pop()
            if not all(ch.isalnum() or ch in "_-" for ch in root_name):
                raise ValueError("Unsafe run root name")
            manifest_name = f"{root_name}/transfer_manifest.json"
            if manifest_name not in members:
                raise ValueError("Missing transfer manifest")
            manifest = json.loads(archive.read(manifest_name))
            hashes = manifest["sha256"]
            if any(PurePosixPath(name).is_absolute() or
                   any(part in ("", ".", "..") for part in PurePosixPath(name).parts) or
                   "\\" in name or ":" in name for name in hashes):
                raise ValueError("Unsafe path in manifest")
            expected = {f"{root_name}/{name}" for name in hashes} | {manifest_name}
            if set(members) != expected or len(members) != len(set(members)):
                raise ValueError("Archive members differ from transfer manifest")
            destination = args.destination.resolve()
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / root_name
            if target.exists():
                raise ValueError(f"Refusing to overwrite {target}")
            # Verify compressed contents before writing any raw files.
            for name, sha in hashes.items():
                digest = hashlib.sha256()
                with archive.open(f"{root_name}/{name}") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() != sha:
                    raise ValueError(f"Checksum mismatch: {name}")
            archive.extractall(destination)
        print(json.dumps({"status": "PASS", "files_verified": len(hashes),
                          "extracted_run": str(target)}, indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
