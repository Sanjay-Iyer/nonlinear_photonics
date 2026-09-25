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
    p.add_argument("--dense", action="store_true", help="Require 29A3 coverage and metadata")
    p.add_argument("--temperature-study", action="store_true", help="Require complete 29B reference-matched raw data")
    a = p.parse_args(argv)
    try:
        root = a.input.resolve()
        if not root.is_dir() or a.zip.exists() or root in a.zip.resolve().parents:
            raise ValueError("Input missing, ZIP exists, or ZIP is inside solver folder")
        metadata = json.loads((root / "run_metadata.json").read_text(encoding="utf-8"))
        if a.dense and a.temperature_study:
            raise ValueError("Choose one raw-package mode")
        kind = ("temperature_full8_finite_k" if a.temperature_study else
                "dense_finite_k" if a.dense else "finite_k")
        allowed_temperatures = (100, 500) if a.temperature_study else (300,)
        if (metadata.get("temperature_K") not in allowed_temperatures or metadata.get("pilot_kind") != kind or
                metadata.get("jobs", {}).get("kp8", {}).get("status") != "PASS"):
            raise ValueError(f"Expected a successful {kind} run")
        if a.temperature_study:
            from chi2.temperature_study import validate_run
            validate_run(root, metadata["temperature_K"])
        report = run_debug.scan_output(root)
        grid = report["integration_grid"]
        if (report["dispersion"]["points"] != 301 or
                abs(report["dispersion"]["k_max_per_nm"] - 0.555714439232) > 5e-10 or
                grid.get("points") != report["complete_state_frames"] or
                grid.get("complete_target_path_frames", 0) < (8 if a.dense else 3)):
            raise ValueError("Insufficient complete target-path states; send debug ZIP first")
        if a.dense and max((r["ky_per_nm"] for r in grid["rows"] if r["on_target_path"] and
                            r["complex_spinors_complete"]), default=0) < .9 * 0.555714439232:
            raise ValueError("29A3 states do not reach 90% of target kmax; send debug ZIP first")
        logs = Path(metadata["log_dir"]) if (a.dense or a.temperature_study) else None
        required_logs = ("runner.log", "run_manifest.json", "paths_report.txt",
                         "finite_k_diagnostic.json", "warnings_errors.txt")
        if (a.dense or a.temperature_study) and (not logs.is_dir() or any(not (logs / name).is_file() for name in required_logs)):
            raise ValueError("Runtime logs missing; send debug ZIP and retain solver directory")
        a.zip.parent.mkdir(parents=True, exist_ok=True)
        hashes = {}
        with zipfile.ZipFile(a.zip, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6) as archive:
            def add(source: Path, relative: str) -> None:
                hashes[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
                archive.write(source, (Path(root.name) / relative).as_posix())
            for file in sorted(root.rglob("*")):
                if file.is_file():
                    relative = file.relative_to(root).as_posix()
                    add(file, relative)
            if a.dense or a.temperature_study:
                for file in sorted(logs.rglob("*")):
                    if file.is_file() and file.suffix.lower() in (".log", ".json", ".txt", ".tsv"):
                        add(file, (Path("runtime_logs") / file.relative_to(logs)).as_posix())
                demo = Path(__file__).resolve().parents[1]
                names = ["config/study.json", "config/optical_operator.json"]
                if a.temperature_study:
                    names += ["config/29b_reference.json", "nextnano/inputs/29B_300K_reference_kp8.in"]
                for name in names:
                    add(demo / name, name)
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
