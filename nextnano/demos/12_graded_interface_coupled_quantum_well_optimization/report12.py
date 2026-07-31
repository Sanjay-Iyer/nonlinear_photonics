"""Solver-free report and optimization helpers for Demo 12.

Running this file creates a clearly labelled synthetic report. It is a plumbing
test only: no row is represented as licensed nextnano output.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

DEMO_DIR = Path(__file__).resolve().parent
SHARED = DEMO_DIR.parent / "_shared"
for path in (str(SHARED), str(DEMO_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import grading12  # noqa: E402
import plots as plotting  # noqa: E402
from demo_workflow import write_json_atomically, write_text_atomically  # noqa: E402


def synthetic_rows() -> list[dict[str, Any]]:
    """Physics-shaped examples that exercise ranking without claiming results."""

    return [
        {"case_id": "synthetic_abrupt", "profile": "abrupt", "grading_thickness_nm": 0.0,
         "peak_chi2_magnitude": 1.00, "chi2_at_target_wavelength": 0.62,
         "peak_wavelength_nm": 1518.0, "target_detuning_nm": -32.0,
         "robustness_score": 0.58, "boundary_probability": 2e-5,
         "state_tracking_confidence": 0.96, "origin_independence_error": 2e-9,
         "bound_states_accepted": True},
        {"case_id": "synthetic_intrinsic", "profile": "linear", "grading_thickness_nm": 1.0,
         "peak_chi2_magnitude": 1.12, "chi2_at_target_wavelength": 0.71,
         "peak_wavelength_nm": 1535.0, "target_detuning_nm": -15.0,
         "robustness_score": 0.67, "boundary_probability": 3e-5,
         "state_tracking_confidence": 0.91, "origin_independence_error": 3e-9,
         "bound_states_accepted": True},
        {"case_id": "synthetic_target", "profile": "cosine", "grading_thickness_nm": 2.0,
         "peak_chi2_magnitude": 0.98, "chi2_at_target_wavelength": 0.94,
         "peak_wavelength_nm": 1548.0, "target_detuning_nm": -2.0,
         "robustness_score": 0.82, "boundary_probability": 4e-5,
         "state_tracking_confidence": 0.94, "origin_independence_error": 4e-9,
         "bound_states_accepted": True},
        {"case_id": "synthetic_robust", "profile": "sigmoid", "grading_thickness_nm": 2.5,
         "peak_chi2_magnitude": 0.91, "chi2_at_target_wavelength": 0.86,
         "peak_wavelength_nm": 1553.0, "target_detuning_nm": 3.0,
         "robustness_score": 0.94, "boundary_probability": 5e-5,
         "state_tracking_confidence": 0.97, "origin_independence_error": 3e-9,
         "bound_states_accepted": True},
        {"case_id": "synthetic_quasibound", "profile": "linear", "grading_thickness_nm": 4.0,
         "peak_chi2_magnitude": 1.05, "chi2_at_target_wavelength": 0.80,
         "peak_wavelength_nm": 1550.0, "target_detuning_nm": 0.0,
         "robustness_score": 0.40, "boundary_probability": 4e-3,
         "state_tracking_confidence": 0.55, "origin_independence_error": 2e-5,
         "bound_states_accepted": False},
    ]


def build_optimization(rows: Sequence[Mapping[str, Any]], constraints: Mapping[str, Any]) -> dict[str, Any]:
    normalized = [{**row, "absolute_target_detuning_nm": abs(float(row["target_detuning_nm"]))}
                  for row in rows]
    annotated = grading12.constraint_filter(normalized, constraints)
    feasible = [row for row in annotated if row["constraint_status"] == "satisfied"]
    pareto = grading12.pareto_front(feasible, {
        "peak_chi2_magnitude": "maximize", "chi2_at_target_wavelength": "maximize",
        "absolute_target_detuning_nm": "minimize", "robustness_score": "maximize",
    })
    # A transparent secondary balanced ranking. Each term is normalized over
    # the feasible grid; individual values remain in the output and Pareto
    # membership is still the primary multi-objective result.
    for row in feasible:
        row["balanced_score"] = 0.0
    score_terms = {
        "peak_chi2_magnitude": (0.25, True),
        "chi2_at_target_wavelength": (0.30, True),
        "absolute_target_detuning_nm": (0.15, False),
        "robustness_score": (0.20, True),
        "state_tracking_confidence": (0.10, True),
    }
    for name, (weight, maximize) in score_terms.items():
        values = [float(row[name]) for row in feasible if row.get(name) is not None]
        if not values:
            continue
        low, high = min(values), max(values)
        for row in feasible:
            if row.get(name) is None:
                continue
            normalized = 1.0 if high == low else (float(row[name]) - low) / (high - low)
            row["balanced_score"] += weight * (normalized if maximize else 1.0 - normalized)
    graded = [row for row in feasible if str(row.get("profile", "abrupt")) != "abrupt"
              and float(row.get("grading_thickness_nm", 0.0)) > 0]
    ranked = graded or feasible
    return {
        "rows": annotated, "pareto": pareto,
        "best_peak": grading12.optimum(ranked, "peak_chi2_magnitude"),
        "best_target": grading12.optimum(ranked, "chi2_at_target_wavelength"),
        "most_robust": grading12.optimum(ranked, "robustness_score"),
        "best_balanced": grading12.optimum(ranked, "balanced_score"),
    }


def write_report(output_dir: Path, cfg: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], *, synthetic: bool) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    optimization = build_optimization(rows, cfg["optimization"]["constraints"])
    write_json_atomically(output_dir / "optimization_results.json", optimization)
    fields = sorted({key for row in optimization["rows"] for key in row})
    with (output_dir / "optimization_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows({key: row.get(key) for key in fields} for row in optimization["rows"])
    label = "SYNTHETIC — NOT LICENSED NEXTNANO OUTPUT" if synthetic else "LICENSED OUTPUT ANALYSIS"
    lines = [f"# Demo 12 report ({label})", "", "This report keeps intrinsic peak response and target-wavelength response separate.", "",
             "| role | case | peak χ² | target χ² | detuning (nm) | robustness |", "|---|---|---:|---:|---:|---:|"]
    abrupt = next((row for row in optimization["rows"] if row.get("profile") == "abrupt"), None)
    role_rows = [("Demo 11 abrupt reference", abrupt)] + [
        ("strongest intrinsic graded", optimization["best_peak"]),
        ("strongest target-wavelength graded", optimization["best_target"]),
        ("most robust graded", optimization["most_robust"]),
        ("best balanced", optimization["best_balanced"]),
    ]
    for role, row in role_rows:
        if row is None:
            continue
        lines.append(f"| {role} | {row['case_id']} | {row['peak_chi2_magnitude']:.3g} | {row['chi2_at_target_wavelength']:.3g} | {row['target_detuning_nm']:.3g} | {row['robustness_score']:.3g} |")
    lines += ["", "The quasi-bound synthetic candidate is deliberately excluded by the configured hard constraints.", ""]
    path = output_dir / "report.md"
    write_text_atomically(path, "\n".join(lines))
    # Exercise the complete publication artifact contract with synthetic points.
    # The values are intentionally repeated across semantic plot names: this is
    # a renderer/plumbing test, not a substitute for the licensed observables.
    import demo12
    figure_dir, data_dir = output_dir / "figures", output_dir / "plot_data"
    figure_dir.mkdir(exist_ok=True); data_dir.mkdir(exist_ok=True)
    x = list(range(len(rows)))
    series = {"synthetic intrinsic peak": (x, [r["peak_chi2_magnitude"] for r in rows]),
              "synthetic target response": (x, [r["chi2_at_target_wavelength"] for r in rows])}
    for filename, title in demo12.PLOT_SET:
        plotting.line_plot(figure_dir / filename, title=f"{title} — {label}",
                           xlabel="Synthetic candidate index", ylabel="Synthetic relative value", series=series)
        with (data_dir / Path(filename).with_suffix(".csv").name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["synthetic_candidate_index", "peak_chi2_magnitude", "chi2_at_target_wavelength"])
            writer.writerows((i, row["peak_chi2_magnitude"], row["chi2_at_target_wavelength"]) for i, row in enumerate(rows))
    return path


def main() -> int:
    cfg = yaml.safe_load((DEMO_DIR / "demo.yaml").read_text(encoding="utf-8"))
    path = write_report(DEMO_DIR / "synthetic_report", cfg, synthetic_rows(), synthetic=True)
    print(f"Synthetic (non-solver) report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
