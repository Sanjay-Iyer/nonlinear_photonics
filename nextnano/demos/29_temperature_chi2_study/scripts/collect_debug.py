"""Create a small Demo 29 debug ZIP from an existing solver directory; no solver run."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chi2 import run_debug


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="existing Demo 29 solver run root")
    parser.add_argument("--temperature", type=int, help="100, 300 or 500 K")
    parser.add_argument("--output-dir", type=Path, help="new directory for reports and ZIP")
    parser.add_argument("--run-id", help="optional explicit diagnostic label for a predictable ZIP name")
    args = parser.parse_args(argv)
    if args.input is None and args.temperature is None:
        parser.error("Specify --input or --temperature")
    source = (args.input or run_debug.ROOT / "nextnano/work_runs" / f"{args.temperature}K").resolve()
    try:
        metadata_path = source / "run_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
        t = args.temperature or metadata.get("temperature_K")
        if t not in (100, 300, 500):
            raise ValueError("Temperature is missing or outside 100/300/500 K")
        if metadata and int(metadata.get("temperature_K", t)) != t:
            raise ValueError("--temperature disagrees with run_metadata.json")
        is_finite_pilot = metadata.get("pilot_kind") in ("finite_k", "dense_finite_k")
        stage = "29A3" if metadata.get("pilot_kind") == "dense_finite_k" else None
        expected = None  # Determine actual integration-grid size from k_points.txt.
        run_id = args.run_id or run_debug.new_run_id("diagnose")
        if not all(c.isalnum() or c in "_-" for c in run_id):
            raise ValueError("--run-id must contain only letters, digits, underscore, or dash")
        destination = (args.output_dir or run_debug.ROOT / "nextnano/run_logs" / f"{t}K" / run_id).resolve()
        if destination.exists():
            raise ValueError(f"Refusing to overwrite diagnostic folder: {destination}")
        study = metadata.get("source_config", {})
        git_now = run_debug.git_state()
        git_now["dirty_at_diagnosis"] = git_now.pop("dirty_before_run")
        git_now["dirty_before_run"] = None
        provenance = {"git": git_now, "kmax_pi_over_a": study.get("kmax_pi_over_a"),
                      "dispersion_points": 301 if is_finite_pilot else study.get("k_points"),
                      "k_integration": run_debug._settings_from_deck(source).get("k_integration"),
                      "path_checks": {"existing_input": str(source), "exists": source.is_dir(),
                                      "diagnostic_only": True, "scientific_output_modified": False}}
        result = run_debug.collect_debug(source, destination, t, expected, run_id,
                                         provenance, stage=stage)
        diagnostic = result["diagnostic"]
        print(f"Run ID: {run_id}\n8-band dispersion points: {diagnostic['dispersion']['points']}\n"
              f"Finite-k state frames: {diagnostic['actual_finite_k_state_frames']}\n"
              f"Complete frames on target path: {diagnostic['integration_grid'].get('complete_target_path_frames')}\n"
              f"Complete complex 8-component frames: {diagnostic['complete_state_frames']}\n"
              f"Relevant unrecognized files: {diagnostic['relevant_files_ignored_total']}\n"
              f"Runtime reports: {destination}\nDebug bundle: {result['zip']}")
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
