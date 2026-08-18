"""Stage 10 - CSV, JSON and Markdown outputs.

Writing only. No physics, no plotting, no solver. Every artifact is stamped with
the configuration and the k-space convention that produced it, so a file on disk
can always be traced back to a convention rather than being ambiguous.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

import s01_cases as cases
import s02_grading as grading
import s06_chi2 as chi2mod
import s07_analysis as analysis

MASTER_FILENAME = "demo20_master_results.csv"
PRESENTATION_FILENAME = "demo20_presentation_table.csv"
CASES_FILENAME = "demo20_grading_cases.csv"
VALIDATION_FILENAME = "demo20_realized_grading_validation.csv"
AUDIT_FILENAME = "demo20_grading_implementation_audit.csv"
SCALING_FILENAME = "demo20_scaling_comparison.csv"
NORMALIZATION_FILENAME = "demo20_normalization_audit.json"
NORMALIZATION_TEXT_FILENAME = "demo20_normalization_audit.txt"
QC_FILENAME = "demo20_qc_report.json"
SUMMARY_FILENAME = "demo20_summary.md"
RUN_RECORD_FILENAME = "demo20_run_record.json"

SCALING_FIELDS = [
    "case_id", "case_name", "profile", "nominal_grade_width_nm",
    "kspace_convention_raw", "chi2_raw_1550_pm_per_V", "raw_peak_chi2_pm_per_V",
    "raw_peak_wavelength_nm",
    "kspace_convention_scaled", "chi2_scaled_1550_pm_per_V",
    "scaled_peak_chi2_pm_per_V", "scaled_peak_wavelength_nm",
    "kspace_scaling_factor", "peak_wavelength_shift_nm",
    "spectral_shape_max_difference",
    "paper_target_pm_per_V", "raw_ratio_to_paper", "scaled_ratio_to_paper",
    "raw_error_percent", "scaled_error_percent",
]


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]],
              fields: Sequence[str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = [dict(row) for row in rows]
    if fields is None:
        fields = list(materialized[0]) if materialized else []
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields),
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default),
                    encoding="utf-8", newline="\n")
    return path


def write_case_tables(cfg: Mapping[str, Any], destination: Path) -> dict[str, Path]:
    """The three solver-free case tables. Available with no licence."""

    all_cases = cases.all_cases()
    return {
        "cases": write_csv(destination / CASES_FILENAME,
                           [case.as_case_row(cfg) for case in all_cases],
                           cases.CASE_TABLE_FIELDS),
        "validation": write_csv(destination / VALIDATION_FILENAME,
                                [grading.validate_realized(cfg, case)
                                 for case in all_cases]),
        "audit": write_csv(destination / AUDIT_FILENAME,
                           cases.implementation_audit_rows()),
    }


def write_master_table(destination: Path,
                       results: Sequence[analysis.CaseAnalysis]) -> Path:
    return write_csv(destination / MASTER_FILENAME,
                     [result.row for result in results], analysis.MASTER_FIELDS)


def write_presentation_table(destination: Path,
                             results: Sequence[analysis.CaseAnalysis]) -> Path:
    return write_csv(destination / PRESENTATION_FILENAME,
                     analysis.presentation_rows(results),
                     analysis.PRESENTATION_FIELDS)


def write_scaling_table(destination: Path,
                        results: Sequence[analysis.CaseAnalysis]) -> Path:
    """Raw and scaled side by side, for the direct convention comparison."""

    rows = [result.row for result in results if result.has_spectrum]
    return write_csv(destination / SCALING_FILENAME, rows, SCALING_FIELDS)


def write_normalization_audit(destination: Path, audit: Mapping[str, Any],
                              text: str) -> dict[str, Path]:
    return {
        "json": write_json(destination / NORMALIZATION_FILENAME, dict(audit)),
        "text": _write_text(destination / NORMALIZATION_TEXT_FILENAME, text + "\n"),
    }


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def write_qc_report(destination: Path, payload: Mapping[str, Any]) -> Path:
    return write_json(destination / QC_FILENAME, dict(payload))


def write_run_record(destination: Path, payload: Mapping[str, Any]) -> Path:
    return write_json(destination / RUN_RECORD_FILENAME, dict(payload))


def _fmt(value: Any, spec: str = ".5g") -> str:
    if value in (None, ""):
        return "n/a"
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return str(value)


def write_summary(
    destination: Path, cfg: Mapping[str, Any],
    results: Sequence[analysis.CaseAnalysis],
    normalization: Mapping[str, Any], status: Mapping[str, Any],
    paper: Mapping[str, Any], validation: Mapping[str, Any],
) -> Path:
    """The human-readable summary. Says what is and is not established."""

    scaling_on = bool(cfg["chi2"]["apply_kspace_2pi_squared_scaling"])
    factor = chi2mod.two_pi_squared()
    with_spectra = [r for r in results if r.has_spectrum]
    target = float(cfg["chi2"]["target_wavelength_nm"])

    lines = [
        "# Demo 20 - Interface Grading with a Configurable $(2\\pi)^2$ "
        "k-Space Normalization", "",
        "## What this demo is", "",
        "Demo 19's controlled interface-grading study, reorganized into numbered "
        "pipeline stages, with the in-plane k-space measure exposed as an "
        "explicit switchable convention. The structure, the 13 cases, the "
        "grading mathematics, the state count, the broadening, $N_z$, "
        "$r_{e,hh}$, $k_{max}$ and the wavelength grid are all unchanged from "
        "Demo 19.", "",
        "## The normalization finding", "",
        normalization["finding"], "",
        f"- Original convention: `{normalization['original_convention']}`",
        f"- Explicit $1/(2\\pi)^2$ present in Demo 19: "
        f"**{'YES' if normalization['explicit_one_over_2pi_squared_present'] else 'NO'}**"
        f" ({normalization['one_over_2pi_squared_location']})",
        f"- Scaling factor: $(2\\pi)^2$ = {factor:.11f}",
        f"- Scaling enabled in this run: "
        f"**{'YES' if scaling_on else 'NO'}**", "",
        "## Results at "
        f"{target:.0f} nm", "",
    ]
    if with_spectra:
        header = ("| Case | Profile | raw (pm/V) | scaled (pm/V) | reported "
                  "(pm/V) | ratio | peak raw (nm) | peak scaled (nm) |")
        lines += [header, "|---|---|---:|---:|---:|---:|---:|---:|"]
        for result in with_spectra:
            row = result.row
            ratio = (float(row["chi2_scaled_1550_pm_per_V"])
                     / float(row["chi2_raw_1550_pm_per_V"])
                     if float(row["chi2_raw_1550_pm_per_V"]) else float("nan"))
            lines.append(
                f"| {row['case_id']} {row['case_name']} | {row['profile']} | "
                f"{_fmt(row['chi2_raw_1550_pm_per_V'])} | "
                f"{_fmt(row['chi2_scaled_1550_pm_per_V'])} | "
                f"{_fmt(row['chi2_reported_1550_pm_per_V'])} | "
                f"{_fmt(ratio, '.6f')} | "
                f"{_fmt(row['raw_peak_wavelength_nm'], '.1f')} | "
                f"{_fmt(row['scaled_peak_wavelength_nm'], '.1f')} |"
            )
    else:
        lines.append("_No case produced a spectrum; see the failure columns in "
                     "the master table._")
    lines += ["", "## Comparison with the published target", ""]
    if paper.get("evaluated"):
        lines += [
            f"- Published target: **~{paper['paper_target_pm_per_V']:g} pm/V**",
            f"- Reference case: {paper['reference_case_id']} "
            f"{paper['reference_case_name']}",
            f"- Demo 20, Demo 19 convention: "
            f"{_fmt(paper['demo20_raw_pm_per_V'])} pm/V "
            f"(ratio {_fmt(paper['raw_ratio_to_paper'], '.4g')}, "
            f"{_fmt(paper['raw_error_percent'], '.4g')}% from target)",
            f"- Demo 20, $(2\\pi)^2$-scaled: "
            f"{_fmt(paper['demo20_scaled_pm_per_V'])} pm/V "
            f"(ratio {_fmt(paper['scaled_ratio_to_paper'], '.4g')}, "
            f"{_fmt(paper['scaled_error_percent'], '.4g')}% from target)",
            f"- Residual factor still missing after scaling: "
            f"**{_fmt(paper.get('remaining_factor_after_scaling'), '.4g')}x**",
            "", paper["interpretation"],
        ]
        residual = paper.get("residual_analysis") or {}
        if residual.get("evaluated"):
            lines += [
                "", "### Residual lead (not a result)", "",
                f"- Remaining factor: {_fmt(residual['remaining_factor'], '.4g')}x",
                f"- The $N_z$ counting ambiguity is a factor of exactly "
                f"{residual['nz_alternative_multiplier']:g} "
                f"(`period_density` vs `well_density`)",
                f"- $(2\\pi)^2$-scaled AND `well_density`: "
                f"{_fmt(residual['chi2_if_scaled_and_well_density_pm_per_V'])} pm/V, "
                f"ratio {_fmt(residual['ratio_to_paper_if_both'], '.4g')}",
                "", residual["note"],
            ]
    else:
        lines.append(f"_Not evaluated: {paper.get('reason', 'unknown')}._")

    lines += ["", "## Validation status", "",
              "| Level | Validated | Evidence |", "|---|---|---|"]
    for level, entry in validation.items():
        mark = "yes" if entry["status"] else "**no**"
        lines.append(f"| {level} | {mark} | {entry['evidence']} |")

    lines += ["", "## Solver and physical status", "",
              f"- Cases: {status['case_count']}",
              f"- solver_pass: {status['solver_pass_count']}/{status['case_count']}",
              f"- physical_valid: "
              f"{status['physical_valid_count']}/{status['case_count']}", ""]
    for reason in status["physical_invalid_reasons"]:
        lines.append(f"- Recorded reason: {reason}")
    lines += ["", status["interpretation"], "",
              "## Main takeaway", "",
              "Enabling the $(2\\pi)^2$ factor does **not** prove that the "
              "scaled convention is physically correct. Demo 19 already "
              "contains the $1/(2\\pi)^2$ normalization, so the switch removes "
              "an existing denominator rather than supplying a missing one. It "
              "remains an experimental normalization comparison until the "
              "source paper's own $k$-space measure is verified.", ""]
    return _write_text(destination / SUMMARY_FILENAME, "\n".join(lines))


def terminal_summary(
    cfg: Mapping[str, Any], results: Sequence[analysis.CaseAnalysis],
    paper: Mapping[str, Any], status: Mapping[str, Any],
) -> str:
    """The console block, mirroring Demo 19's layout plus the scaling columns."""

    by_id = {result.case_id: result.row for result in results}
    target = float(cfg["chi2"]["target_wavelength_nm"])
    scaling_on = bool(cfg["chi2"]["apply_kspace_2pi_squared_scaling"])
    g = grading.geometry(cfg)
    lines = [
        "", "DEMO 20 - QUANTUM-WELL INTERFACE GRADING, SCALED",
        "=" * 58, "",
        "REFERENCE STRUCTURE", "-" * 19,
        f"Well 1:        {g.thick_well_nm:.1f} nm",
        f"Barrier:       {g.tunnel_barrier_nm:.1f} nm",
        f"Well 2:        {g.thin_well_nm:.1f} nm",
        f"Barrier Al:    {float(cfg['materials']['barrier_al_fraction']):.2f}",
        f"Domain:        {g.domain_nm[1]:.1f} nm", "",
        "REPORTED CONVENTION", "-" * 19,
        f"{'(2pi)^2-scaled' if scaling_on else 'Demo 19 original'}"
        f"   (scaling factor {chi2mod.two_pi_squared():.10f})", "",
        "CASES", "-" * 5,
        f"Total: {status['case_count']}",
        f"solver_pass: {status['solver_pass_count']}",
        f"physical_valid: {status['physical_valid_count']}", "",
        f"LINEAR GRADING SERIES  (|chi2| at {target:.0f} nm, pm/V)",
        "-" * 52,
        f"{'Width':>6} {'raw':>12} {'scaled':>12} {'vs abrupt':>10} {'peak nm':>9}",
    ]
    for case_id in ("00", "01", "02", "03", "04", "05"):
        row = by_id.get(case_id, {})
        lines.append(
            f"{_fmt(row.get('nominal_grade_width_nm'), '.1f'):>6} "
            f"{_fmt(row.get('chi2_raw_1550_pm_per_V')):>12} "
            f"{_fmt(row.get('chi2_scaled_1550_pm_per_V')):>12} "
            f"{_fmt(row.get('chi2_raw_1550_relative_to_reference'), '.3f'):>10} "
            f"{_fmt(row.get('raw_peak_wavelength_nm'), '.1f'):>9}"
        )
    lines += ["", "GRADING LOCATION", "-" * 16]
    for case_id, label in (("08", "Inner-only"), ("09", "Outer-only"),
                           ("06", "Asymmetric A"), ("07", "Asymmetric B")):
        row = by_id.get(case_id, {})
        lines.append(f"{label:<14} raw {_fmt(row.get('chi2_raw_1550_pm_per_V')):>10}"
                     f"   scaled {_fmt(row.get('chi2_scaled_1550_pm_per_V')):>10}")
    lines += ["", "PROFILE SHAPES", "-" * 14]
    for case_id, label in (("03", "Linear"), ("10", "Fermi"), ("11", "erf"),
                           ("12", "Cosine")):
        row = by_id.get(case_id, {})
        lines.append(f"{label:<14} raw {_fmt(row.get('chi2_raw_1550_pm_per_V')):>10}"
                     f"   scaled {_fmt(row.get('chi2_scaled_1550_pm_per_V')):>10}")
    if paper.get("evaluated"):
        lines += ["", "PAPER COMPARISON", "-" * 16,
                  f"Target:                 ~{paper['paper_target_pm_per_V']:g} pm/V",
                  f"Demo 19 convention:     {_fmt(paper['demo20_raw_pm_per_V'])} pm/V"
                  f"   ratio {_fmt(paper['raw_ratio_to_paper'], '.4g')}"
                  f"   error {_fmt(paper['raw_error_percent'], '.4g')}%",
                  f"(2pi)^2-scaled:         {_fmt(paper['demo20_scaled_pm_per_V'])} pm/V"
                  f"   ratio {_fmt(paper['scaled_ratio_to_paper'], '.4g')}"
                  f"   error {_fmt(paper['scaled_error_percent'], '.4g')}%",
                  f"Residual factor:        "
                  f"{_fmt(paper.get('remaining_factor_after_scaling'), '.4g')}x still "
                  "unexplained after scaling"]
    lines += ["", "PRIMARY INTERPRETATION", "-" * 22,
              "Grading comparisons are made only against the otherwise identical",
              "abrupt case. The (2pi)^2 switch changes the absolute magnitude and",
              "nothing else; it is a convention experiment, not a correction.", ""]
    return "\n".join(lines)
