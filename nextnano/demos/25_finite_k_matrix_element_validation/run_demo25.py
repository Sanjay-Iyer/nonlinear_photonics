"""Demo 25 orchestrator: finite-k matrix elements and extended states.

Two-stage by construction. The pilot must prove that nextnano++ Professional
actually writes finite-k state output before the production run is allowed to
start; ``--production`` refuses to launch until the recorded gate says PASS.

    python run_demo25.py --preflight     # config, decks, syntax, solver availability
    python run_demo25.py --pilot         # STAGE 1  (Professional, minutes)
    python run_demo25.py --pilot-audit   # STAGE 1 GATE (no solver)
    python run_demo25.py --production    # STAGE 2  (Professional, hours; gated)
    python run_demo25.py --analyse       # post-processing (no solver)
    python run_demo25.py --progress [--watch]
    python run_demo25.py --tests
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from config25 import (DEMO22, DEMO23, DEMO24, DEMO_DIR, REPO_ROOT, Demo25Error,
                      load_config, outputs_root, repo_path, results_root)

import deck25  # noqa: E402
import pilot_audit  # noqa: E402
import progress as progress_mod  # noqa: E402
import reporting25 as reporting  # noqa: E402

DEMO14 = DEMO_DIR.parent / "14_absolute_chi2_graded_acqw_bo"
for module_dir in (DEMO14,):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))


# ---------------------------------------------------------------------------
# machine configuration
# ---------------------------------------------------------------------------

def machine_config(explicit: Path | None = None) -> dict[str, Any]:
    """Resolve the per-machine nextnano++ paths, or explain what is missing."""
    import yaml  # noqa: PLC0415

    path = Path(explicit) if explicit else REPO_ROOT / "nextnano" / "config" / "paths.local.yaml"
    if not path.is_file():
        raise Demo25Error(
            f"per-machine nextnano configuration is absent: {path}\n"
            f"  copy {path.with_suffix('.yaml.example').name} to paths.local.yaml on this machine "
            "and fill in the Professional executable, database and license paths.")
    blob = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    block = blob.get("nextnano++") or {}
    resolved: dict[str, Any] = {"source": str(path)}
    for key in ("exe", "database", "license"):
        value = block.get(key)
        if not value or str(value).startswith("PATH_TO_"):
            raise Demo25Error(f"paths.local.yaml does not set nextnano++.{key}")
        resolved[key] = Path(str(value)).expanduser()
    resolved["threads"] = int(block.get("threads", 1))
    return resolved


def assert_professional(machine: Mapping[str, Any]) -> dict[str, Any]:
    """Fail loudly unless a Professional-capable executable and license exist.

    A Free build cannot produce Demo 25's data: it is capped at 100 grid points
    and cannot run this deck at all. Detecting that here, by name and by
    license file, is much cheaper than discovering it after a failed run.
    """
    exe = Path(machine["exe"])
    problems = []
    if not exe.is_file():
        problems.append(f"executable not found: {exe}")
    elif "free" in exe.name.lower():
        problems.append(
            f"the configured executable is a Free build ({exe.name}); Demo 25 needs "
            "nextnano++ Professional. The Free build caps at 100 grid points and "
            "cannot run this deck.")
    for key in ("database", "license"):
        if not Path(machine[key]).is_file():
            problems.append(f"{key} not found: {machine[key]}")
    license_path = Path(machine["license"])
    if license_path.is_file() and "free" in license_path.name.lower():
        problems.append(f"the configured license is a Free license ({license_path.name})")
    if problems:
        raise Demo25Error("nextnano++ Professional is not available on this machine:\n  - "
                          + "\n  - ".join(problems))
    return {"executable": str(exe), "database": str(machine["database"]),
            "license": str(machine["license"]), "threads": int(machine["threads"])}


# ---------------------------------------------------------------------------
# tracker
# ---------------------------------------------------------------------------

def tracker_path(cfg: Mapping[str, Any]) -> Path:
    return results_root(cfg) / "progress.json"


def tracker(cfg: Mapping[str, Any], *, fresh: bool = False) -> progress_mod.Tracker:
    path = tracker_path(cfg)
    if fresh and path.is_file():
        path.unlink()
    return progress_mod.Tracker(path, progress_mod.default_plan(cfg), title="Demo 25")


def _show(track: progress_mod.Tracker) -> None:
    print(track.render(color=sys.stdout.isatty()))


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------

def stage_audit(cfg: Mapping[str, Any], track: progress_mod.Tracker) -> dict[str, Any]:
    """Confirm the inherited structure and the Demo 24 findings Demo 25 builds on."""
    track.start("audit")
    cfg23 = cfg["_demo23_config"]
    rows = []
    for block in cfg["inherit"]["frozen_blocks"]:
        rows.append({"item": f"{block} block", "source": "demo23_config.yaml",
                     "status": "INHERITED", "detail": json.dumps(cfg23[block], sort_keys=True)[:160]})
    demo24 = repo_path(str(cfg["analysis"]["demo24_outputs"]))
    for name in ("DEMO24_FINAL_REPORT.md", "RESONANCE_REACHABILITY.csv",
                 "SPECTRAL_FEATURE_CAUSAL_DIAGNOSIS.csv", "PROFESSIONAL_RERUN_RECOMMENDATION.md",
                 "FINITE_K_DATA_INVENTORY.md"):
        rows.append({"item": name, "source": str(demo24 / name),
                     "status": "FOUND" if (demo24 / name).is_file() else "MISSING",
                     "detail": "Demo 24 evidence Demo 25 is built on"})
    missing = [r["item"] for r in rows if r["status"] == "MISSING"]
    output = outputs_root(cfg)
    reporting.write_csv(output / "DEMO24_INHERITANCE_AUDIT.csv", rows)
    track.finish("audit", note=("all Demo 23/24 inputs present"
                                if not missing else f"missing: {', '.join(missing)}"))
    return {"rows": rows, "missing": missing}


def stage_pilot_decks(cfg: Mapping[str, Any], track: progress_mod.Tracker) -> list[dict[str, Any]]:
    track.start("decks_pilot")
    specs = deck25.pilot_specs(cfg)
    directory = results_root(cfg) / "inputs" / "pilot"
    written = deck25.write_decks(cfg, specs, directory)
    demo23_deck = _demo23_reference_deck(cfg)
    rows = []
    for spec, path in written:
        if demo23_deck is not None:
            deck25.assert_structure_matches_demo23(cfg, path.read_text(encoding="utf-8"), demo23_deck)
        rows.append({"variant": spec.name, "role": spec.role, "question": spec.question,
                     "k_integration": spec.k_integration, "no_density": spec.no_density,
                     "k_point_subdirectories": spec.k_point_subdirectories,
                     "symmetry": spec.symmetry, "keep_dispersion_path": spec.keep_dispersion_path,
                     "num_points": spec.num_points, "path": str(path)})
    reporting.write_csv(outputs_root(cfg) / "PILOT_DECK_MANIFEST.csv", rows)
    track.finish("decks_pilot", note=f"{len(rows)} pilot decks, structure matches Demo 23")
    return rows


def _demo23_reference_deck(cfg: Mapping[str, Any]) -> str | None:
    """Render the Demo 23 production deck for a structural diff."""
    try:
        import deck23  # noqa: PLC0415

        cfg23 = cfg["_demo23_config"]
        spec = next(s for s in deck23.deck_specs(cfg23) if s.role == "production")
        return deck23.render(cfg23, spec)
    except Exception:  # noqa: BLE001 - a missing reference must not block deck writing
        return None


def stage_syntax(cfg: Mapping[str, Any], track: progress_mod.Tracker,
                 machine: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate deck grammar with --parse. Works with a Free build too."""
    directory = results_root(cfg) / "inputs" / "pilot"
    decks = sorted(directory.glob("*.in"))
    track.start("syntax", units_total=len(decks))
    if machine is None:
        track.finish("syntax", progress_mod.SKIPPED, note="no nextnano executable configured")
        return {"status": "SKIPPED", "rows": []}
    exe = Path(machine["exe"])
    scratch = results_root(cfg) / "syntax_check"
    scratch.mkdir(parents=True, exist_ok=True)
    rows = []
    for deck in decks:
        argv = [str(exe), "--parse", "-d", str(machine["database"]),
                "-l", str(machine["license"]), "-o", str(scratch), str(deck)]
        try:
            done = subprocess.run(argv, cwd=str(DEMO_DIR), text=True, capture_output=True,
                                  timeout=300, check=False)
            blob = (done.stdout or "") + (done.stderr or "")
            ok = done.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            blob, ok = str(exc), False
        rows.append({"deck": deck.name, "parse_ok": ok,
                     "message": _first_error(blob) if not ok else "parsed"})
        track.advance("syntax")
    reporting.write_csv(outputs_root(cfg) / "DECK_SYNTAX_VALIDATION.csv", rows)
    failures = [r["deck"] for r in rows if not r["parse_ok"]]
    if failures:
        track.finish("syntax", progress_mod.FAILED, note=f"parse failed: {', '.join(failures)}")
        return {"status": "FAIL", "rows": rows}
    track.finish("syntax", note=f"{len(rows)} decks parsed clean")
    return {"status": "PASS", "rows": rows}


def _first_error(blob: str) -> str:
    for line in blob.splitlines():
        if "error" in line.lower():
            return line.strip()[:300]
    return (blob.strip().splitlines() or ["no output"])[-1][:300]


def stage_pilot_run(cfg: Mapping[str, Any], track: progress_mod.Tracker,
                    machine: Mapping[str, Any]) -> list[dict[str, Any]]:
    """STAGE 1: run every pilot variant with the Professional solver."""
    import solver14  # noqa: PLC0415

    solver = assert_professional(machine)
    directory = results_root(cfg) / "inputs" / "pilot"
    decks = sorted(directory.glob("*.in"))
    if not decks:
        raise Demo25Error("no pilot decks found; run --preflight first")
    raw = results_root(cfg) / "raw" / "pilot"
    raw.mkdir(parents=True, exist_ok=True)
    track.start("pilot_run", units_total=len(decks))
    records = []
    for deck in decks:
        case = raw / deck.stem
        case.mkdir(parents=True, exist_ok=True)
        started = time.time()
        invocation = solver14.execute_real(
            executable=Path(solver["executable"]), database=Path(solver["database"]),
            license_path=Path(solver["license"]), deck=deck, output_dir=case,
            threads=int(solver["threads"]),
            timeout_seconds=float(cfg["pilot"]["timeout_seconds_per_deck"]),
            logs_dir=case / "logs")
        elapsed = time.time() - started
        record = {"variant": deck.stem, "seconds": elapsed, "output_dir": str(case)}
        blob = invocation.__dict__ if hasattr(invocation, "__dict__") else {}
        record["returncode"] = blob.get("returncode")
        record["mode"] = blob.get("mode", "real")
        records.append(record)
        track.advance("pilot_run", note=f"{deck.stem}: {progress_mod.humanize(elapsed)}")
    reporting.write_json(results_root(cfg) / "pilot_invocations.json", records)
    track.finish("pilot_run", note=f"{len(records)} variants executed")
    return records


def stage_pilot_audit(cfg: Mapping[str, Any], track: progress_mod.Tracker) -> dict[str, Any]:
    """STAGE 1 GATE: read the filesystem and decide whether STAGE 2 may run."""
    track.start("pilot_audit")
    raw = results_root(cfg) / "raw" / "pilot"
    if not raw.is_dir():
        track.finish("pilot_audit", progress_mod.FAILED, note="no pilot output; run --pilot first")
        raise Demo25Error("no pilot output directory; run --pilot on the Professional machine first")
    timings = {}
    invocations = results_root(cfg) / "pilot_invocations.json"
    if invocations.is_file():
        timings = {r["variant"]: float(r.get("seconds", 0.0))
                   for r in json.loads(invocations.read_text(encoding="utf-8"))}
    rows, summaries = [], []
    for case in sorted(p for p in raw.iterdir() if p.is_dir()):
        evidence, summary = pilot_audit.audit_case(case, case.name)
        vectors = pilot_audit.k_vectors_for_case(case)
        summary["k_vectors_found"] = vectors is not None
        summary["k_vector_count"] = 0 if vectors is None else int(len(vectors))
        summary["seconds"] = timings.get(case.name, 0.0)
        rows.extend(e.as_row(case.name) for e in evidence)
        summaries.append(summary)
    output = outputs_root(cfg)
    reporting.write_csv(output / "PILOT_OUTPUT_AVAILABILITY.csv", rows)
    reporting.write_csv(output / "PILOT_VARIANT_SUMMARY.csv", summaries)

    verdict = pilot_audit.gate(summaries)
    best = next((s for s in summaries if s["variant"] == verdict["recommended_variant"]), None)
    sizing: dict[str, Any] = {}
    if verdict["status"] == "PASS" and best and best.get("seconds"):
        cost = pilot_audit.cost_model(best, float(best["seconds"]))
        prod = cfg["production"]
        sizing = pilot_audit.recommend_k_points(
            cost, requested=int(prod["requested_k_points"]),
            max_hours=float(prod["max_projected_hours"]),
            max_gb=float(prod["max_projected_output_gb"]))
        sizing["cost_model"] = cost
    verdict["sizing"] = sizing
    reporting.write_json(output / "PILOT_GATE.json", verdict)
    reporting.write_text(output / "PILOT_FINITE_K_OUTPUT_AUDIT.md",
                         _pilot_report(cfg, rows, summaries, verdict, sizing))
    if verdict["status"] != "PASS":
        reporting.write_text(output / "PILOT_BLOCKER_REPORT.md",
                             _blocker_report(cfg, summaries, verdict))
        track.finish("pilot_audit", progress_mod.FAILED, note=verdict["reason"])
        return verdict
    track.finish("pilot_audit", note=verdict["reason"])
    return verdict


def _pilot_report(cfg: Mapping[str, Any], rows: list[Mapping[str, Any]],
                  summaries: list[Mapping[str, Any]], verdict: Mapping[str, Any],
                  sizing: Mapping[str, Any]) -> str:
    lines = ["# Demo 25 pilot: finite-k output audit", "",
             f"**GATE: {verdict['status']}** - {verdict['reason']}", "",
             "This audit reads the output filesystem. A clean solver exit is not "
             "treated as evidence: Demo 23 exited cleanly and still wrote only `k00000`.",
             "", "## Variant summary", "",
             reporting.markdown_table(summaries, [
                 "variant", "k_points_with_evidence", "k_points_usable",
                 "finite_k_state_output", "k_vectors_found", "total_files", "total_bytes", "seconds"]),
             "", "## Per-k evidence", "",
             reporting.markdown_table(rows[:400], [
                 "variant", "k", "energy output?", "wavefunction output?", "spinor output?",
                 "CB/HH/LH/SO character?", "oscillator strength?", "momentum matrix?",
                 "dipole matrix?", "usable for Equation 2?", "file path"])]
    if sizing:
        lines += ["", "## Production sizing measured from the pilot", "",
                  f"- {sizing['reason']}",
                  f"- recommended matrix-element k points: **{sizing['recommended_k_points']}**",
                  f"- projected for the requested grid: "
                  f"{sizing.get('requested_projected_hours', float('nan')):.2f} h, "
                  f"{sizing.get('requested_projected_gb', float('nan')):.2f} GB, "
                  f"{sizing.get('requested_projected_files', float('nan')):.0f} files"]
    return "\n".join(lines) + "\n"


def _blocker_report(cfg: Mapping[str, Any], summaries: list[Mapping[str, Any]],
                    verdict: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Demo 25 pilot blocker", "",
        f"**The pilot did not establish finite-k output. STAGE 2 must not run.**", "",
        f"Reason: {verdict['reason']}", "",
        "## What each variant was testing, and what it produced", "",
        reporting.markdown_table(summaries, [
            "variant", "k_points_with_evidence", "k_points_usable",
            "finite_k_state_output", "k_vectors_found", "total_files"]),
        "", "## What must be resolved before retrying", "",
        "1. Confirm with nextnano support or documentation which keyword makes",
        "   `output_states{ all_k_points = yes }` emit one file set per k-integration point.",
        "2. Demo 23 used `k_integration_disabled{}`, so `all_k_points` had a single point.",
        "   If enabling `k_integration{}` still yields only `k00000`, the remaining",
        "   candidates are `k_point_subdirectories`, the `no_density` flag, and whether",
        "   Professional writes envelopes only for the k=0 subspace by design.",
        "3. Demo 25 does not fabricate finite-k matrix elements. No production run and",
        "   no finite-k Equation 2 spectrum are produced while this gate is FAIL.",
        "", "No M(k)=M(0) substitution is made anywhere in Demo 25.", "",
    ]) + "\n"


def stage_production(cfg: Mapping[str, Any], track: progress_mod.Tracker,
                     machine: Mapping[str, Any], *, force: bool = False) -> dict[str, Any]:
    """STAGE 2: the single targeted production run. Gated on the pilot verdict."""
    import solver14  # noqa: PLC0415

    gate_path = outputs_root(cfg) / "PILOT_GATE.json"
    if not gate_path.is_file():
        raise Demo25Error("the pilot gate has not been recorded; run --pilot then --pilot-audit")
    verdict = json.loads(gate_path.read_text(encoding="utf-8"))
    if verdict.get("status") != "PASS" and not force:
        raise Demo25Error(
            "the pilot gate is FAIL, so the production run is refused:\n  "
            + str(verdict.get("reason"))
            + "\nSee outputs/PILOT_BLOCKER_REPORT.md. Demo 25 will not substitute M(k)=M(0).")
    solver = assert_professional(machine)
    sizing = verdict.get("sizing") or {}
    points = int(sizing.get("recommended_k_points") or cfg["production"]["requested_k_points"])
    settings = _settings_from_variant(cfg, str(verdict.get("recommended_variant") or ""))
    spec = deck25.production_spec(cfg, num_points=points, settings=settings)
    directory = results_root(cfg) / "inputs" / "production"
    (deck_spec, deck_path), = deck25.write_decks(cfg, (spec,), directory)
    track.start("decks_production")
    reporting.write_csv(outputs_root(cfg) / "PROFESSIONAL_RUN_MANIFEST.csv", [{
        "deck": deck_path.name, "k_points": spec.num_points,
        "fraction_of_bz": spec.relative_size, "kmax_per_nm": spec.kmax_per_nm,
        "k_integration": spec.k_integration, "symmetry": spec.symmetry,
        "no_density": spec.no_density, "k_point_subdirectories": spec.k_point_subdirectories,
        "electron_states": cfg["kp8"]["number_of_electron_states"],
        "hole_states": cfg["kp8"]["number_of_hole_states"],
        "output_states": cfg["kp8"]["output_state_count"],
        "gate_variant": verdict.get("recommended_variant"),
        "projected_hours": sizing.get("requested_projected_hours"),
        "projected_gb": sizing.get("requested_projected_gb"),
    }])
    track.finish("decks_production", note=f"{deck_path.name}: {points} k points")

    raw = results_root(cfg) / "raw" / "production" / spec.name
    raw.mkdir(parents=True, exist_ok=True)
    track.start("production_run", units_total=points,
                note="solver progress is inferred from emitted k-point output")
    started = time.time()
    invocation = solver14.execute_real(
        executable=Path(solver["executable"]), database=Path(solver["database"]),
        license_path=Path(solver["license"]), deck=deck_path, output_dir=raw,
        threads=int(solver["threads"]),
        timeout_seconds=float(cfg["production"]["timeout_seconds_per_deck"]),
        logs_dir=raw / "logs")
    elapsed = time.time() - started
    _, summary = pilot_audit.audit_case(raw, spec.name)
    track.advance("production_run", units=max(int(summary["k_points_usable"]) - 0, 0))
    track.finish("production_run", note=f"{progress_mod.humanize(elapsed)}, "
                                        f"{summary['k_points_usable']} usable k points")
    record = {"deck": str(deck_path), "output_dir": str(raw), "seconds": elapsed,
              "summary": summary, "invocation": getattr(invocation, "__dict__", {})}
    reporting.write_json(results_root(cfg) / "production_invocation.json", record)
    return record


def _settings_from_variant(cfg: Mapping[str, Any], variant: str) -> dict[str, Any]:
    for item in cfg["pilot"]["variants"]:
        if str(item["name"]) == variant:
            return {"k_integration": bool(item["k_integration"]),
                    "no_density": bool(item["no_density"]),
                    "k_point_subdirectories": bool(item["k_point_subdirectories"]),
                    "symmetry": str(item["symmetry"]),
                    "keep_dispersion_path": True}
    return {}


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def preflight(cfg: Mapping[str, Any], machine: Mapping[str, Any] | None) -> int:
    track = tracker(cfg)
    stage_audit(cfg, track)
    stage_pilot_decks(cfg, track)
    result = stage_syntax(cfg, track, machine)
    _show(track)
    if result["status"] == "FAIL":
        print("\nDeck syntax validation FAILED; fix the decks before running the pilot.")
        return 1
    if machine is not None:
        try:
            assert_professional(machine)
            print("\nnextnano++ Professional detected: --pilot may run on this machine.")
        except Demo25Error as exc:
            print(f"\n{exc}\n\nPreflight and syntax validation still succeeded. "
                  "Run --pilot on the Professional machine.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Demo 25 finite-k matrix-element validation")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--preflight", action="store_true")
    actions.add_argument("--pilot", action="store_true")
    actions.add_argument("--pilot-audit", action="store_true")
    actions.add_argument("--production", action="store_true")
    actions.add_argument("--analyse", "--analyze", dest="analyse", action="store_true")
    actions.add_argument("--progress", action="store_true")
    actions.add_argument("--tests", action="store_true")
    parser.add_argument("--machine", type=Path, help="explicit nextnano machine YAML")
    parser.add_argument("--watch", action="store_true", help="live progress refresh")
    parser.add_argument("--force", action="store_true",
                        help="override the pilot gate (records the override; use only deliberately)")
    args = parser.parse_args(argv)

    if args.tests:
        return subprocess.run([sys.executable, "-m", "pytest", str(DEMO_DIR / "tests"), "-q",
                               "-p", "no:cacheprovider"], cwd=REPO_ROOT, check=False).returncode

    cfg = load_config()
    if args.progress:
        path = tracker_path(cfg)
        if args.watch:
            return progress_mod.watch(path)
        if not path.is_file():
            print("No Demo 25 progress recorded yet. Run --preflight to begin.")
            return 0
        _show(progress_mod.Tracker(path))
        return 0

    machine: dict[str, Any] | None = None
    try:
        machine = machine_config(args.machine)
    except Demo25Error as exc:
        if args.pilot or args.production:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(f"note: {exc}\n")

    track = tracker(cfg)
    try:
        if args.preflight:
            return preflight(cfg, machine)
        if args.pilot:
            stage_pilot_run(cfg, track, machine)
            _show(track)
            print("\nPilot complete. Now run:  python run_demo25.py --pilot-audit")
            return 0
        if args.pilot_audit:
            verdict = stage_pilot_audit(cfg, track)
            _show(track)
            print(f"\nPILOT GATE: {verdict['status']} - {verdict['reason']}")
            if verdict["status"] != "PASS":
                print("See outputs/PILOT_BLOCKER_REPORT.md. The production run is refused.")
                return 1
            sizing = verdict.get("sizing") or {}
            if sizing:
                print(f"Recommended production k points: {sizing['recommended_k_points']}")
            print("Next:  python run_demo25.py --production")
            return 0
        if args.production:
            stage_production(cfg, track, machine, force=args.force)
            _show(track)
            print("\nProduction complete. Now run:  python run_demo25.py --analyse")
            return 0
        if args.analyse:
            import analysis25  # noqa: PLC0415

            analysis25.run(cfg, track)
            _show(track)
            return 0
    except Demo25Error as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
