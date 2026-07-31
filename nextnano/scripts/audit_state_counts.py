"""Audit whether Demo 11's state-count parameters reach the calculations.

    python nextnano/scripts/audit_state_counts.py
    python nextnano/scripts/audit_state_counts.py --run-dir <a specific run>
    python nextnano/scripts/audit_state_counts.py --cases s2n1 s2n2 s2n3

Why this exists
===============

The 2026-07-31 licensed run swept 3, 4 and 6 electron states and produced
chi(2) values agreeing to about 1e-13 relative. Read casually that is
convergence. It is not: ``chi2_spectrum`` sums over the first
``metric.max_states_per_band`` states of each band -- two, as the paper
specifies -- no matter how many the solver returned. All three cases evaluated
an identical number of identical terms, so their agreement says nothing about
convergence at all.

Two independent questions therefore have to be asked separately:

1. **Does ``numerical.number_of_electron_states`` propagate?** YAML, rendered
   deck, solver output, extracted CSVs. If the extracted row counts do not move
   when the requested count does, something in the chain is broken.
2. **Does the extracted count widen Eq. 2's sums?** It should NOT -- that is
   governed by ``metric.max_states_per_band`` -- and confirming it does not is
   what disqualifies the state-count sweep as evidence of convergence.

The audit passes only when both answers are the expected ones AND the run
contains a ``max_states_per_band`` sweep whose term counts genuinely differ. A
run without that sweep is reported as INCONCLUSIVE, never as PASS: closeness of
the final numbers is not evidence and this script will not treat it as such.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from nn_config import NEXTNANO_ROOT

DEMO_ID = "11_paper_validation_interband_chi2_acqw"
#: Cases of the requested-state-count sweep (numerical.number_of_electron_states).
SOLVER_STATE_CASES = ("s2n1", "s2n2", "s2n3")
#: Cases of the summation-window sweep (metric.max_states_per_band).
SUM_WINDOW_CASES = ("s2m1", "s2m2", "s2m3")


def latest_run(results_root: Path) -> Path | None:
    """Most recent timestamped run directory for Demo 11."""

    parent = results_root / DEMO_ID
    if not parent.is_dir():
        return None
    runs = sorted((p for p in parent.iterdir() if p.is_dir()), key=lambda p: p.name)
    return runs[-1] if runs else None


def _rows(path: Path) -> int | None:
    """Data-row count of a CSV, excluding its header."""

    if not path.is_file():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in csv.reader(handle)) - 1)


def _columns(path: Path, prefix: str) -> int | None:
    """How many columns of a CSV header start with ``prefix``."""

    if not path.is_file():
        return None
    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    return sum(1 for name in header if name.strip().startswith(prefix))


def inspect_case(run_dir: Path, case_id: str) -> dict[str, Any]:
    """Every layer of the state-count path for one case.

    Missing files are reported as ``None`` rather than defaulted. A run produced
    before the audit existed will show nulls in the layers it never wrote, and
    that is the honest answer -- not a zero.
    """

    case_dir = run_dir / "runs" / case_id
    extracted = case_dir / "extracted"
    record: dict[str, Any] = {
        "case_id": case_id,
        "present": case_dir.is_dir(),
        "electron_states_csv_rows": _rows(extracted / "electron_states.csv"),
        "envelope_electron_columns": _columns(extracted / "envelopes.csv", "psi_e"),
        "envelope_hole_columns": _columns(extracted / "envelopes.csv", "psi_hh"),
        "quasi_bound_csv_rows": _rows(extracted / "quasi_bound_states.csv"),
    }
    audit_path = extracted / "state_count_audit.json"
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        record["audit_present"] = True
        record["requested_electron_states"] = audit["case_layer_yaml"][
            "numerical.number_of_electron_states"
        ]
        record["requested_hole_states"] = audit["case_layer_yaml"][
            "numerical.number_of_hole_states"
        ]
        record["max_states_per_band"] = audit["case_layer_yaml"][
            "metric.max_states_per_band"
        ]
        record["rendered_electron_states"] = audit["rendered_input_layer"][
            "number_of_electron_states"
        ]
        record["rendered_output_state_count"] = audit["rendered_input_layer"][
            "output_state_count"
        ]
        record["extracted_electron_energy_rows"] = audit["extracted_layer"][
            "electron_energy_rows"
        ]
        record["extracted_hole_energy_rows"] = audit["extracted_layer"][
            "heavy_hole_energy_rows"
        ]
        record["supplied_to_chi2_electron"] = audit["supplied_to_chi2_layer"][
            "electron_states_supplied"
        ]
        record["supplied_to_chi2_hole"] = audit["supplied_to_chi2_layer"][
            "heavy_hole_states_supplied"
        ]
        summation = audit["summation_layer"]
        record["states_used_electron"] = summation.get("electron_states_used")
        record["states_used_hole"] = summation.get("heavy_hole_states_used")
        record["triple_sum_terms_evaluated"] = summation.get("triple_sum_terms_evaluated")
        record["triple_sum_terms_significant"] = summation.get(
            "triple_sum_terms_significant"
        )
        record["states_discarded_by_truncation"] = (
            summation.get("electron_states_discarded_by_truncation", 0)
            + summation.get("heavy_hole_states_discarded_by_truncation", 0)
        )
    else:
        record["audit_present"] = False
        record["note"] = (
            "no state_count_audit.json; this run predates the audit. Re-run the "
            "demo to populate the summation layer."
        )

    manifest_path = case_dir / "run_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        observables = manifest.get("observables") or {}
        record["chi2_relative_at_reference"] = observables.get(
            "chi2_relative_at_reference"
        )
        record["chi2_peak_magnitude"] = observables.get("chi2_peak_magnitude")
        record["status"] = manifest.get("completion_status")
    return record


def _distinct(records: list[dict[str, Any]], key: str) -> set[Any]:
    return {r[key] for r in records if r.get(key) is not None}


def evaluate(run_dir: Path, cases: list[str], window_cases: list[str]) -> dict[str, Any]:
    """Answer both questions and combine them into one verdict."""

    solver_records = [inspect_case(run_dir, case) for case in cases]
    window_records = [inspect_case(run_dir, case) for case in window_cases]
    available = [r for r in solver_records if r["present"]]
    windows = [r for r in window_records if r["present"]]

    findings: list[dict[str, Any]] = []

    # Question 1: does the requested count reach the extracted output?
    requested = _distinct(available, "requested_electron_states")
    extracted_rows = _distinct(available, "extracted_electron_energy_rows")
    if len(available) < 2:
        propagation = "inconclusive"
        detail = f"only {len(available)} of {len(cases)} state-count cases are present"
    elif len(requested) < 2:
        propagation = "inconclusive"
        detail = (
            "the cases do not actually request different state counts; nothing to test"
        )
    elif len(extracted_rows) < 2:
        propagation = "fail"
        detail = (
            f"requested counts {sorted(requested)} but the extracted energy rows are "
            f"all {sorted(extracted_rows)}. The parameter is not reaching the solver "
            "output, so no state-count claim can be made at all."
        )
    else:
        propagation = "pass"
        detail = (
            f"requested {sorted(requested)} -> extracted {sorted(extracted_rows)}. "
            "YAML, deck, solver and extraction all move together."
        )
    findings.append(
        {"question": "requested state count propagates to extracted output",
         "verdict": propagation, "detail": detail}
    )

    # Question 2: does it widen Eq. 2's sums? It must not.
    terms = _distinct(available, "triple_sum_terms_evaluated")
    if not terms:
        truncation = "inconclusive"
        detail = "no summation-layer data; re-run the demo to populate the audit"
    elif len(terms) > 1:
        truncation = "fail"
        detail = (
            f"term counts {sorted(terms)} differ across the requested-state sweep. "
            "Eq. 2 is supposed to be capped at max_states_per_band regardless, so "
            "either the cap or this audit is wrong."
        )
    else:
        truncation = "pass"
        detail = (
            f"every case evaluated {sorted(terms)[0]} terms. The requested state "
            "count does NOT widen the sum -- so agreement of chi(2) across this "
            "sweep is NOT evidence of state-count convergence."
        )
    findings.append(
        {"question": "requested state count is truncated at max_states_per_band",
         "verdict": truncation, "detail": detail}
    )

    # Question 3: is there a sweep that genuinely widens the sum?
    window_terms = _distinct(windows, "triple_sum_terms_evaluated")
    if len(windows) < 2:
        window = "inconclusive"
        detail = (
            f"only {len(windows)} of {len(window_cases)} max_states_per_band cases "
            "are present, so nothing in this run demonstrates convergence of Eq. 2 "
            "in the number of states it sums over."
        )
    elif len(window_terms) < 2:
        window = "fail"
        detail = (
            f"max_states_per_band varies but the term count is always "
            f"{sorted(window_terms)}. The knob is not connected."
        )
    else:
        window = "pass"
        detail = (
            f"max_states_per_band sweep changed the term count: {sorted(window_terms)}. "
            "This is the sweep that can support a convergence claim."
        )
    findings.append(
        {"question": "the summation window sweep really widens the sum",
         "verdict": window, "detail": detail}
    )

    verdicts = [f["verdict"] for f in findings]
    if "fail" in verdicts:
        overall = "FAIL"
    elif "inconclusive" in verdicts:
        overall = "INCONCLUSIVE"
    else:
        overall = "PASS"
    return {
        "run_dir": str(run_dir),
        "demo_id": DEMO_ID,
        "overall": overall,
        "findings": findings,
        "requested_state_cases": solver_records,
        "summation_window_cases": window_records,
        "conclusion": {
            "PASS": "State-count parameters are auditable at every layer and the "
            "summation window is the knob that governs Eq. 2.",
            "FAIL": "At least one layer does not behave as documented. Do not "
            "report any state-count convergence result from this run.",
            "INCONCLUSIVE": "Not enough cases to decide. Convergence is UNVERIFIED; "
            "closeness of the final chi(2) numbers is not a substitute.",
        }[overall],
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "state_count_audit_report.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    rows = report["requested_state_cases"] + report["summation_window_cases"]
    rows = [row for row in rows if row.get("present")]
    csv_path = out_dir / "state_count_audit_report.csv"
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or ["case_id"])
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="a specific timestamped run directory; default is the most recent",
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=NEXTNANO_ROOT / "results" / "demo_runs",
        help="where Demo 11 run directories live",
    )
    parser.add_argument("--cases", nargs="*", default=list(SOLVER_STATE_CASES))
    parser.add_argument("--window-cases", nargs="*", default=list(SUM_WINDOW_CASES))
    args = parser.parse_args(argv)

    run_dir = args.run_dir or latest_run(args.results_root)
    if run_dir is None or not run_dir.is_dir():
        print(
            f"ERROR: no Demo 11 run directory found under {args.results_root}. "
            "Run the demo first.",
            file=sys.stderr,
        )
        return 2

    report = evaluate(run_dir, list(args.cases), list(args.window_cases))
    json_path, csv_path = write_outputs(report, run_dir / "extracted")

    print(f"State-count audit of {run_dir}")
    print("")
    for finding in report["findings"]:
        print(f"  [{finding['verdict'].upper():>12}] {finding['question']}")
        print(f"                 {finding['detail']}")
    print("")
    print(f"  OVERALL: {report['overall']}")
    print(f"  {report['conclusion']}")
    print("")
    print(f"  {json_path}")
    print(f"  {csv_path}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
