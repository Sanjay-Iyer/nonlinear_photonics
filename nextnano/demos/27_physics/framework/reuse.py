"""Reuse audit: what Demo 27 may take from Demos 23-26 instead of recomputing.

Two jobs.

1. **Scientific reuse.** Say, per artifact, whether it is valid to reuse for a
   given sub-demo. Reuse is valid only when the structure and solver settings
   behind the artifact are the ones the sub-demo needs. Demo 23's production run
   IS the control arm of 27D, 27F, 27G, 27H, 27I and 27J, because each of those
   changes exactly one thing away from it. It is deliberately NOT 27E's control:
   27E must regenerate both of its arms so they move together if 27D changes the
   geometry decision.

2. **Integrity.** Hash every reused artifact and store the hashes. Demo 27 reads
   Demos 23-26 and must never write to them, so a later mismatch is a real
   finding: either an older demo was rerun or something modified its output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from . import Demo27Error
from .manifest import sha256
from .registry import DEMOS_DIR, REPO_ROOT
from .report import read_json, write_json

BASELINE_NAME = "REUSE_BASELINE_HASHES.json"

#: Named artifacts Demo 27 actually depends on, with the reuse rule for each.
ARTIFACTS = (
    {
        "id": "demo23_config",
        "path": "nextnano/demos/23_k_resolved_dispersion_validation/demo23_config.yaml",
        "provides": "the frozen structure, mesh, BZ convention and chi2 settings",
        "reusable_for": "ALL",
        "reuse_rule": "inherited verbatim; a sub-demo may override only fields it declares",
    },
    {
        "id": "demo23_production_raw",
        "path": "demo_results/demo23/raw/production_y_n301_k0100",
        "provides": "kp8 dispersion over 301 k points and k=0 state/matrix output",
        "reusable_for": "27D 27C 27F 27G 27H 27I 27J",
        "reuse_rule": ("valid as the same-structure control wherever geometry, mesh, "
                       "temperature and solver model are unchanged - this IS 27D's graded "
                       "arm, 27F's numerical control, 27G's 0.1 pi/a arm, 27H's [010] arm, "
                       "27I's kp8 arm and 27J's 300 K arm. NOT valid as 27E's flat-band "
                       "control: 27E must regenerate that arm so both of its arms move "
                       "together if 27D changes the geometry decision"),
    },
    {
        "id": "demo23_kmax_sensitivity_raw",
        "path": "demo_results/demo23/raw",
        "provides": "kmax cases at 0.05, 0.075, 0.10, 0.125 pi/a and grids at 101/201/301",
        "reusable_for": "27F 27G",
        "reuse_rule": ("27G's 0.1 pi/a and 0.125 pi/a arms already exist; only the "
                       "0.2 pi/a (Gamma-X) arm is new solver work"),
    },
    {
        "id": "demo24_reachability",
        "path": "nextnano/demos/24_equation2_spectral_shape_audit/outputs/DEMO24_FINAL_REPORT.md",
        "provides": "the reachability finding and the k-truncation artifact identification",
        "reusable_for": "27C 27G 27K",
        "reuse_rule": "conclusions only; re-deriving them is explicitly out of scope",
    },
    {
        "id": "demo24_feature_sensitivity",
        "path": "nextnano/demos/24_equation2_spectral_shape_audit/outputs/FEATURE_CAUSAL_TRACEBACK.csv",
        "provides": "measured dLambda/dE per spectral feature",
        "reusable_for": "27D 27E 27G 27J",
        "reuse_rule": ("converts any energy shift a sub-demo produces into a predicted "
                       "wavelength shift without rerunning the chi2 engine"),
    },
    {
        "id": "demo25_pilot_decks",
        "path": "nextnano/demos/25_finite_k_matrix_element_validation",
        "provides": "the finite-k output pilot, its gate, and the production sizing model",
        "reusable_for": "27A 27B",
        "reuse_rule": ("27A and 27B DELEGATE to this demo rather than reimplementing it; "
                       "Demo 27 must not fork the pilot"),
    },
    {
        "id": "demo26_root_cause_ranking",
        "path": ("nextnano/demos/26_real_chi2_paper_comparison/outputs/"
                 "EXTENDED_IMPLEMENTATION_AUDIT/EXTENDED_ROOT_CAUSE_RANKING.csv"),
        "provides": "the ranked list of remaining hypotheses with confidence and Pro-needed flags",
        "reusable_for": "ALL",
        "reuse_rule": "sets the campaign priority order; re-ranking is 27's job only after new data",
    },
    {
        "id": "demo26_feature_diagnosis",
        "path": ("nextnano/demos/26_real_chi2_paper_comparison/outputs/"
                 "EXTENDED_IMPLEMENTATION_AUDIT/EXTENDED_FEATURE_DIAGNOSIS.csv"),
        "provides": "per-feature (P1 Z1 P2 P3 Z2 P4) paper-vs-model wavelengths and verdicts",
        "reusable_for": "27D 27E 27G 27J",
        "reuse_rule": "the acceptance target every geometry/convention sub-demo is scored against",
    },
    {
        "id": "paper_curve",
        "path": ("nextnano/demos/23_k_resolved_dispersion_validation/"
                 "paper_figure2d_digitized_simulation.csv"),
        "provides": "the digitized Ramesh Fig. 2d simulated curve",
        "reusable_for": "27D 27E 27G 27J 27L",
        "reuse_rule": ("diagnostic only. Demo 23's PAPER_DATA_PROVENANCE.md states these "
                       "are eye-digitized and are not acceptance gates"),
    },
)


def _resolve(relative: str) -> Path:
    return REPO_ROOT / relative


def _fingerprint(path: Path) -> dict:
    if path.is_file():
        return {"kind": "file", "exists": True, "sha256": sha256(path),
                "bytes": path.stat().st_size, "entries": 1}
    if path.is_dir():
        # __pycache__ churns on every import and says nothing about the data,
        # so excluding it is what makes a CHANGED verdict meaningful.
        files = sorted(p for p in path.rglob("*")
                       if p.is_file() and "__pycache__" not in p.parts
                       and p.suffix not in (".pyc", ".pyo"))
        total = sum(p.stat().st_size for p in files)
        # A directory is fingerprinted by its file list and sizes, not by hashing
        # gigabytes of raw solver output on every audit.
        listing = "\n".join("%s:%d" % (p.relative_to(path).as_posix(), p.stat().st_size)
                            for p in files)
        import hashlib  # noqa: PLC0415

        return {"kind": "dir", "exists": True,
                "sha256": hashlib.sha256(listing.encode("utf-8")).hexdigest(),
                "bytes": total, "entries": len(files)}
    return {"kind": "missing", "exists": False, "sha256": None, "bytes": 0, "entries": 0}


def audit(parent: Mapping) -> dict:
    """Fingerprint every reusable artifact and compare against the stored baseline."""
    from .registry import DEMO_DIR  # noqa: PLC0415

    baseline_path = DEMO_DIR / BASELINE_NAME
    stored = read_json(baseline_path, default={"schema": 1, "artifacts": {}})
    rows = []
    drifted = []
    for artifact in ARTIFACTS:
        path = _resolve(artifact["path"])
        print_ = _fingerprint(path)
        previous = (stored.get("artifacts") or {}).get(artifact["id"])
        if previous is None:
            integrity = "BASELINED" if print_["exists"] else "MISSING"
        elif not print_["exists"]:
            integrity = "DISAPPEARED"
        elif previous.get("sha256") != print_["sha256"]:
            integrity = "CHANGED"
        else:
            integrity = "UNCHANGED"
        if integrity in ("CHANGED", "DISAPPEARED"):
            drifted.append(artifact["id"])
        rows.append({
            "artifact": artifact["id"],
            "path": artifact["path"],
            "exists": print_["exists"],
            "kind": print_["kind"],
            "entries": print_["entries"],
            "bytes": print_["bytes"],
            "sha256": print_["sha256"],
            "integrity": integrity,
            "provides": artifact["provides"],
            "reusable_for": artifact["reusable_for"],
            "reuse_rule": artifact["reuse_rule"],
        })
        stored.setdefault("artifacts", {})[artifact["id"]] = print_
    write_json(baseline_path, stored)
    return {"rows": rows, "drifted": drifted,
            "missing": [r["artifact"] for r in rows if not r["exists"]]}


def reusable_for(demo_id: str) -> list:
    """The artifacts a given sub-demo is allowed to reuse."""
    out = []
    for artifact in ARTIFACTS:
        scope = str(artifact["reusable_for"])
        if scope == "ALL" or demo_id.upper() in scope.upper().split():
            out.append(artifact)
    return out


def assert_no_writes_outside_demo27(parent: Mapping) -> None:
    """Guard: Demo 27's results root must not sit inside another demo's tree."""
    root = Path(str(parent["paths"]["results_root"]))
    root = root if root.is_absolute() else REPO_ROOT / root
    for other in ("demo23", "demo24", "demo25", "demo26"):
        forbidden = REPO_ROOT / "demo_results" / other
        try:
            root.relative_to(forbidden)
        except ValueError:
            continue
        raise Demo27Error(
            "Demo 27's results root %s is inside %s. Demo 27 reads earlier demos and "
            "must never write into them." % (root, forbidden))
    for other in DEMOS_DIR.glob("2[3-6]_*"):
        try:
            root.relative_to(other)
        except ValueError:
            continue
        raise Demo27Error(
            "Demo 27's results root %s is inside %s. Demo 27 reads earlier demos and "
            "must never write into them." % (root, other))
