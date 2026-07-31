"""Bundle a demo run's reports and tables for transfer back to the home laptop.

    python nextnano/scripts/bundle_results.py
    python nextnano/scripts/bundle_results.py --demo 11_paper_validation_interband_chi2_acqw
    python nextnano/scripts/bundle_results.py --run-dir <a specific run> --include-plots

Raw solver output is deliberately excluded. A licensed Demo 11 run writes tens
of megabytes of fields, meshes and per-case logs under ``runs/*/raw``, none of
which is needed to read the result, and ``nextnano/results/demo_runs/**`` is
gitignored so the bundle is the transfer mechanism. What goes in is the
reports, the machine-readable tables, the per-case manifests and the extracted
diagnostics -- everything needed to re-derive a conclusion, and nothing that
needs a licence to have produced.

Solver logs are already redacted of licensed-user and key fields by the runner
before they are written; the per-case logs are still excluded here because they
are bulky, not because they are sensitive.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from nn_config import NEXTNANO_ROOT

DEFAULT_DEMO = "11_paper_validation_interband_chi2_acqw"

#: Run-root artifacts: the reports and their machine-readable counterparts.
ROOT_PATTERNS = (
    "*.md",
    "*.json",
    "*.yaml",
    "tables/*.csv",
    "extracted/*.csv",
    "extracted/*.json",
)

#: Per-case artifacts. Small, text, and the evidence behind every claim.
CASE_PATTERNS = (
    "run_manifest.json",
    "demo_resolved.yaml",
    "machine_summary.json",
    "extracted/*.csv",
    "extracted/*.json",
)

PLOT_PATTERNS = ("plots/*.png",)


def latest_run(results_root: Path, demo_id: str) -> Path | None:
    parent = results_root / demo_id
    if not parent.is_dir():
        return None
    runs = sorted((p for p in parent.iterdir() if p.is_dir()), key=lambda p: p.name)
    return runs[-1] if runs else None


def collect(run_dir: Path, *, include_plots: bool, include_case_plots: bool) -> list[Path]:
    """Every file the bundle should carry, deduplicated and sorted."""

    found: set[Path] = set()
    patterns = list(ROOT_PATTERNS) + (list(PLOT_PATTERNS) if include_plots else [])
    for pattern in patterns:
        found.update(p for p in run_dir.glob(pattern) if p.is_file())

    case_patterns = list(CASE_PATTERNS) + (
        list(PLOT_PATTERNS) if include_case_plots else []
    )
    runs_dir = run_dir / "runs"
    if runs_dir.is_dir():
        for case_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
            for pattern in case_patterns:
                found.update(p for p in case_dir.glob(pattern) if p.is_file())
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--demo", default=DEFAULT_DEMO)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--results-root", type=Path, default=NEXTNANO_ROOT / "results" / "demo_runs"
    )
    parser.add_argument("--output", type=Path, help="destination .zip")
    parser.add_argument(
        "--include-plots",
        action="store_true",
        help="add the run-root figures (adds roughly a megabyte)",
    )
    parser.add_argument(
        "--include-case-plots",
        action="store_true",
        help="also add every per-case figure; large",
    )
    args = parser.parse_args(argv)

    run_dir = args.run_dir or latest_run(args.results_root, args.demo)
    if run_dir is None or not run_dir.is_dir():
        print(
            f"ERROR: no run directory found for {args.demo} under {args.results_root}.",
            file=sys.stderr,
        )
        return 2

    files = collect(
        run_dir,
        include_plots=args.include_plots,
        include_case_plots=args.include_case_plots,
    )
    if not files:
        print(f"ERROR: {run_dir} contains none of the expected artifacts.", file=sys.stderr)
        return 2

    output = args.output or (run_dir.parent / f"{run_dir.name}_bundle.zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=str(path.relative_to(run_dir.parent)))

    size_mb = output.stat().st_size / 1.0e6
    print(f"Bundled {len(files)} file(s) from {run_dir}")
    print(f"  -> {output}  ({size_mb:.1f} MB)")
    if not args.include_plots:
        print("  (figures excluded; pass --include-plots to add them)")
    print("  raw solver output excluded by design")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
