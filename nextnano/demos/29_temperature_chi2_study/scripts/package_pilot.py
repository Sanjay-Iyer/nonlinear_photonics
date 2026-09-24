"""ZIP a successful target-aligned 300 K pilot without modifying solver files."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2 import run_debug


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--zip", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        root = a.input.resolve()
        if not root.is_dir() or a.zip.exists() or root in a.zip.resolve().parents:
            raise ValueError("Input missing, ZIP exists, or ZIP is inside solver folder")
        metadata = json.loads((root / "run_metadata.json").read_text(encoding="utf-8"))
        if (metadata.get("temperature_K") != 300 or metadata.get("pilot_kind") != "finite_k" or
                metadata.get("jobs", {}).get("kp8", {}).get("status") != "PASS"):
            raise ValueError("Expected a successful 300 K finite-k pilot")
        report = run_debug.scan_output(root)
        grid = report["integration_grid"]
        if (report["dispersion"]["points"] != 301 or
                abs(report["dispersion"]["k_max_per_nm"] - 0.555714439232) > 5e-10 or
                grid.get("points") !=
                report["complete_state_frames"] or grid.get("complete_target_path_frames", 0) < 3):
            raise ValueError("Pilot lacks three complete states on target path; send debug ZIP first")
        a.zip.parent.mkdir(parents=True, exist_ok=True)
        hashes = {}
        with zipfile.ZipFile(a.zip, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6) as archive:
            for file in sorted(root.rglob("*")):
                if file.is_file():
                    relative = file.relative_to(root).as_posix()
                    hashes[relative] = hashlib.sha256(file.read_bytes()).hexdigest()
                    archive.write(file, (Path(root.name) / relative).as_posix())
            archive.writestr((Path(root.name) / "transfer_manifest.json").as_posix(),
                             json.dumps({"source_run_id": metadata["run_id"],
                                         "sha256": hashes}, indent=2) + "\n")
        print(json.dumps({"status": "PASS", "archive": str(a.zip),
                          "archive_bytes": a.zip.stat().st_size,
                          "scientific_files": len(hashes),
                          "target_path_frames": grid["complete_target_path_frames"]}, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
