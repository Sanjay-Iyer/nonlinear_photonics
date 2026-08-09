"""Master CSV and JSON, plus the end-of-run console table.

One row per case across all three groups, with the columns that make a row
interpretable on its own: which group it came from, which file was solved, how
its grading width was defined, what the states came out as, and where the chi2
landed. Provenance columns are last so the physics reads first.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import grading16g

#: Explicit and ordered, so the CSV is stable across runs and diffable.
MASTER_FIELDS = [
    # identity
    "group", "case_id", "label", "source", "source_kind", "representation",
    "hole_model",
    # structure
    "thick_well_nm", "thin_well_nm", "barrier_nm", "total_well_nm",
    "asymmetry_s", "period_barrier_nm",
    # grading, all three ways
    "grading_definition",
    "left_requested_grade_nm", "left_full_linear_ramp_width_nm",
    "left_10_90_width_nm", "left_grade_placement", "left_is_abrupt",
    "right_requested_grade_nm", "right_full_linear_ramp_width_nm",
    "right_10_90_width_nm", "right_grade_placement", "right_is_abrupt",
    "fully_abrupt",
    # states
    "E1_eV", "E2_eV", "HH1_eV", "HH2_eV",
    "E2_minus_E1_meV", "HH1_minus_HH2_meV",
    "E1_minus_HH1_eV", "E2_minus_HH2_eV",
    # overlaps and dipoles
    "overlap_e1_hh1", "overlap_e1_hh2", "overlap_e2_hh1", "overlap_e2_hh2",
    "z_e1_e1_nm", "z_e1_e2_nm", "z_e2_e2_nm",
    "z_hh1_hh1_nm", "z_hh1_hh2_nm", "z_hh2_hh2_nm",
    "electron_diagonal_difference_nm", "hole_diagonal_difference_nm",
    "electron_hole_centroid_separation_nm",
    # localization
    "electron1_thick_well_probability", "electron1_thin_well_probability",
    "electron2_thick_well_probability", "electron2_thin_well_probability",
    # optics
    "chi2_1550_pm_per_V", "peak_chi2_pm_per_V", "peak_wavelength_nm",
    "detuning_nm", "chi2_units", "tensor",
    "cartesian_over_radial", "k_implementations_agree",
    # quality
    "passed", "failure_stage", "failure_reason",
    "bound_state_gate_passed", "bound_state_failing", "physical_qc_valid",
    # provenance
    "solver_executable", "solver_return_code", "input_path",
    "sha256_input", "raw_output_dir", "parsed_dir", "case_dir",
    "machine_config_source", "scale_factor_applied",
]


def _localization(record: Mapping[str, Any]) -> dict[str, Any]:
    observables = (record.get("analysis") or {}).get("observables") or {}
    return {
        key: observables.get(key)
        for key in (
            "electron1_thick_well_probability", "electron1_thin_well_probability",
            "electron2_thick_well_probability", "electron2_thin_well_probability",
        )
    }


def flatten(record: Mapping[str, Any]) -> dict[str, Any]:
    """One case record, flattened into the master row schema."""

    elements = record.get("matrix_elements") or {}
    optical = record.get("optical") or {}
    gate = record.get("bound_state_gate") or {}
    solver = record.get("solver") or {}
    workspace = record.get("workspace") or {}
    staging = record.get("nnp_staging") or {}
    row: dict[str, Any] = {
        "group": record.get("group"),
        "case_id": record.get("case_id"),
        "label": record.get("label"),
        "source": record.get("source"),
        "source_kind": record.get("source_kind"),
        "representation": record.get("representation"),
        "hole_model": (
            record.get("hole_model")
            or (record.get("deck") or {}).get("hole_model")
        ),
        "passed": record.get("passed"),
        "failure_stage": record.get("failure_stage"),
        "failure_reason": record.get("failure_reason"),
        "bound_state_gate_passed": gate.get("passed"),
        "bound_state_failing": ";".join(gate.get("failing_states") or []) or None,
        "physical_qc_valid": record.get("physical_qc_valid"),
        "solver_executable": record.get("solver_executable"),
        "solver_return_code": solver.get("return_code"),
        "input_path": (
            staging.get("staged_path") or record.get("generated_input_path")
        ),
        "sha256_input": (
            staging.get("sha256_staged") or record.get("sha256_generated_input")
        ),
        "raw_output_dir": workspace.get("raw"),
        "parsed_dir": workspace.get("parsed"),
        "case_dir": workspace.get("case_dir"),
        "machine_config_source": record.get("machine_config_source"),
        "chi2_units": "pm/V",
        "scale_factor_applied": None,
    }
    for source in (record, elements, optical, _localization(record)):
        for key in MASTER_FIELDS:
            if key not in row or row[key] is None:
                if key in source:
                    row[key] = source[key]
    return {key: row.get(key) for key in MASTER_FIELDS}


def write_master(
    summaries_dir: Path, records: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any], extra: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    summaries_dir = Path(summaries_dir)
    summaries_dir.mkdir(parents=True, exist_ok=True)
    rows = [flatten(record) for record in records]

    csv_path = summaries_dir / "demo16g_master_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MASTER_FIELDS,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    json_path = summaries_dir / "demo16g_master_summary.json"
    payload = {
        "demo_id": cfg.get("demo_id"),
        "version": cfg.get("version"),
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config_path": cfg.get("_config_path"),
        "tensor": cfg["optics"]["tensor"],
        "chi2_units": "pm/V",
        "scale_factor_applied": None,
        "no_empirical_scaling_note": (
            "every chi2 in this table is produced by the physical calculation. "
            "Demo 16G contains no calibration constant, absolute_scale_factor or "
            "fitted multiplier of any kind."
        ),
        "grading_convention": grading16g.convention_note(
            cfg["grading"]["definition"]
        ),
        "paper_targets_pm_per_V": dict(
            cfg["paper_benchmark"]["targets_pm_per_V"]
        ),
        "primary_paper_target": "ideal_abrupt_at_1550",
        "figure2d_peak_is_visual_reference_only": True,
        "unresolved_published_ambiguities": [
            {"name": "eq1_eq2_prefactor", "size": 3.0, "applied": False},
            {"name": "heavy_hole_mj_multiplicity", "size": 2.0, "applied": False},
        ],
        "cases_total": len(records),
        "cases_passed": sum(1 for r in records if r.get("passed")),
        "rows": rows,
        **(dict(extra) if extra else {}),
    }
    json_path.write_text(json.dumps(payload, indent=1, default=str),
                         encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path)}


def console_table(records: Sequence[Mapping[str, Any]]) -> str:
    """The concise end-of-run table."""

    header = (
        f"{'case':<22}{'group':<18}{'solve':<7}{'parse':<7}{'QC':<14}"
        f"{'chi2@1550':>11}{'peak':>10}{'peak nm':>9}  output dir"
    )
    lines = [header, "-" * (len(header) + 12)]
    for record in records:
        solver = record.get("solver") or {}
        gate = record.get("bound_state_gate") or {}
        optical = record.get("optical") or {}
        parsed = "yes" if record.get("matrix_elements") else "no"
        solve = (
            "ok" if solver.get("succeeded")
            else ("rc" + str(solver.get("return_code")) if solver else "-")
        )
        qc = {True: "BOUND", False: "NOT BOUND"}.get(
            gate.get("passed"), "NOT CERTIFIED"
        )
        def number(value, spec):
            return "-" if value is None else format(float(value), spec)
        lines.append(
            f"{record.get('case_id', '?'):<22}{record.get('group', '?'):<18}"
            f"{solve:<7}{parsed:<7}{qc:<14}"
            f"{number(optical.get('chi2_1550_pm_per_V'), '>11.2f')}"
            f"{number(optical.get('peak_chi2_pm_per_V'), '>10.2f')}"
            f"{number(optical.get('peak_wavelength_nm'), '>9.1f')}"
            f"  {(record.get('workspace') or {}).get('case_dir', '-')}"
        )
    return "\n".join(lines)


def comparison_against_paper(
    records: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    """The benchmark case against the paper's stated numbers. States, never fits."""

    targets = cfg["paper_benchmark"]["targets_pm_per_V"]
    benchmark = next(
        (r for r in records
         if r.get("group") == "paper_benchmark" and r.get("passed")), None
    )
    if benchmark is None:
        return {"available": False,
                "reason": "the paper benchmark case did not produce a result"}
    optical = benchmark.get("optical") or {}
    ours = optical.get("chi2_1550_pm_per_V")
    return {
        "available": True,
        "our_chi2_1550_pm_per_V": ours,
        "our_peak_chi2_pm_per_V": optical.get("peak_chi2_pm_per_V"),
        "our_peak_wavelength_nm": optical.get("peak_wavelength_nm"),
        "paper_targets_pm_per_V": dict(targets),
        "primary_target_pm_per_V": targets["ideal_abrupt_at_1550"],
        "remaining_factor_vs_primary_target": (
            None if not ours else float(targets["ideal_abrupt_at_1550"]) / float(ours)
        ),
        "scale_factor_applied": None,
        "note": (
            "the ratio is reported so the gap is visible. It is never applied, "
            "and no convention in this demo was chosen because it reduced it."
        ),
    }
