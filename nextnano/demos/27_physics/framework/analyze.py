"""The analysis stage: post-processing only, never a solver.

Two guarantees this module is responsible for.

* **It never launches nextnano++.** A test asserts that no solver entry point is
  reachable from here.
* **It never fabricates raw physics.** If the Professional output a sub-demo
  needs is absent, the stage says so and stops. There is no code path that
  substitutes a placeholder, an extrapolation or a k=0 value for missing
  finite-k data.

The k-point auditing is Demo 25's, imported rather than copied, because Demo 25
already established what counts as usable finite-k evidence on disk.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Mapping

from . import Demo27Error
from .registry import DEMOS_DIR, Resolved, SubDemo
from .report import markdown_table, write_csv, write_json, write_text

DEMO25 = DEMOS_DIR / "25_finite_k_matrix_element_validation"


def _pilot_audit_module():
    """Demo 25's filesystem auditor. Imported, never reimplemented."""
    if str(DEMO25) not in sys.path:
        sys.path.insert(0, str(DEMO25))
    import pilot_audit  # noqa: PLC0415

    return pilot_audit


def raw_cases(resolved: Resolved) -> list:
    root = resolved.results_root / "raw"
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir())


def audit_raw_output(sub: SubDemo, resolved: Resolved) -> dict:
    """Enumerate what the solver actually left on disk, per deck and per k point."""
    pilot_audit = _pilot_audit_module()
    cases = raw_cases(resolved)
    if not cases:
        return {"status": "NO DATA", "cases": [], "rows": [], "summaries": []}
    rows, summaries = [], []
    for case in cases:
        evidence, summary = pilot_audit.audit_case(case, case.name)
        vectors = pilot_audit.k_vectors_for_case(case)
        summary["k_vectors_found"] = vectors is not None
        summary["k_vector_count"] = 0 if vectors is None else int(len(vectors))
        # A state file tagged with a k index that has no matching k vector cannot
        # be placed in k space, so it is not usable evidence however many files
        # were written.
        indices = list(summary.get("k_indices") or [])
        summary["k_association_valid"] = bool(
            vectors is not None and indices and max(indices) < len(vectors))
        summaries.append(summary)
        rows.extend(e.as_row(case.name) for e in evidence)
    write_csv(sub.outputs_dir / "RAW_OUTPUT_AUDIT.csv", rows)
    write_csv(sub.outputs_dir / "RAW_CASE_SUMMARY.csv", summaries)
    bad = [s["variant"] for s in summaries if not s.get("k_association_valid")]
    status = "PASS" if summaries and not bad else ("FAIL" if summaries else "NO DATA")
    return {"status": status, "cases": [str(c) for c in cases], "rows": rows,
            "summaries": summaries, "unassociated": bad}


def run(sub: SubDemo, resolved: Resolved) -> dict:
    kind = sub.stage_kind("analyze")
    if kind in ("none",):
        raise Demo27Error("%s defines no analysis stage" % sub.demo_id)

    if kind == "delegated":
        delegate = dict(sub.delegate or {})
        command = (delegate.get("commands") or {}).get("analyze")
        raise Demo27Error(
            "%s delegates its analysis to %s. Run it there:\n    python %s %s"
            % (sub.demo_id, delegate.get("demo"),
               (DEMOS_DIR / str(delegate.get("demo", "")) / str(delegate.get("runner", ""))),
               command or "(no analyze command mapped)"))

    audit = audit_raw_output(sub, resolved)
    pending = list((sub.raw.get("analysis") or {}).get("produces") or [])
    report = _report(sub, resolved, audit, pending, kind)
    write_text(sub.outputs_dir / "ANALYSIS.md", report)
    write_json(sub.outputs_dir / "ANALYSIS_STATUS.json", {
        "sub_demo": sub.demo_id,
        "stage_kind": kind,
        "raw_output_status": audit["status"],
        "cases": audit["cases"],
        "planned_artifacts": pending,
        "artifacts_written": sorted(p.name for p in sub.outputs_dir.glob("*")
                                    if p.is_file()),
    })
    if audit["status"] == "NO DATA" and kind != "python_no_solver_data":
        return {"status": "NO DATA", "audit": audit,
                "message": "no raw Professional output under %s; the physics stage has not "
                           "produced data for %s, and Demo 27 does not invent it."
                           % (resolved.results_root / "raw", sub.demo_id)}
    return {"status": audit["status"], "audit": audit}


def _report(sub: SubDemo, resolved: Resolved, audit: Mapping, pending: list,
            kind: str) -> str:
    lines = [
        "# %s analysis" % sub.demo_id,
        "",
        "**%s**" % sub.title,
        "",
        "Question: %s" % sub.question,
        "",
        "Pass condition: %s" % sub.pass_condition,
        "",
        "## Raw Professional output actually on disk",
        "",
        "Searched: `%s`" % (resolved.results_root / "raw"),
        "",
    ]
    if audit["status"] == "NO DATA":
        lines += [
            "**None.** The physics stage has not run, or wrote nothing.",
            "",
            "No analysis is produced from absent data. Demo 27 does not substitute k=0",
            "values, extrapolations or placeholders for missing finite-k output; where an",
            "earlier demo's result is scientifically valid to reuse, the reuse audit names",
            "it explicitly instead.",
            "",
        ]
    else:
        lines += [markdown_table(list(audit["summaries"]), [
            "variant", "total_files", "total_bytes", "k_points_with_evidence",
            "k_points_usable", "finite_k_state_output", "k_vectors_found",
            "k_vector_count", "k_association_valid"]), ""]
        if audit.get("unassociated"):
            lines += ["> **k association FAILED** for: %s. State output that cannot be tied"
                      % ", ".join(audit["unassociated"]),
                      "> to a k vector is not usable evidence, whatever its file count.", ""]
    if pending:
        written = {p.name for p in sub.outputs_dir.glob("*") if p.is_file()}
        lines += ["## Planned analysis artifacts", "",
                  markdown_table(
                      [{"artifact": name,
                        "status": "WRITTEN" if name in written else "PENDING DATA"}
                       for name in pending],
                      ["artifact", "status"]),
                  "",
                  "`PENDING DATA` means the artifact's inputs do not exist yet. It is not a",
                  "placeholder file: nothing has been written for it.",
                  ""]
    return "\n".join(lines)
