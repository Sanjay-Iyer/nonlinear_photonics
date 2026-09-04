"""Run Demo 22 without ever substituting fabricated kp8 data.

The default action is a reproducible preflight. ``--physics`` additionally
requires a real nextnano++ Professional installation, executes the controlled
decks, inventories the raw files, and launches the staged analysis.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from config22 import DEMO_DIR, REPO_ROOT, Demo22Error, load_config, result_root
import analysis22
import deck22


SHARED = DEMO_DIR.parent / "_shared"
SOLVER14 = DEMO_DIR.parent / "14_absolute_chi2_graded_acqw_bo"
for module_dir in (SHARED, SOLVER14):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
import demo_workflow  # noqa: E402
import solver14  # noqa: E402


STAGES = (
    "00_setup_and_provenance", "01_kp8_solver_validation",
    "02_band_dispersion", "03_state_tracking", "04_spinor_composition",
    "05_wavefunction_evolution", "06_matrix_elements",
    "07_neighboring_states", "08_k_domain", "09_energy_only_chi2",
    "10_k_dependent_matrix_chi2", "11_term_decomposition",
    "12_k_resolved_cancellation", "13_observable_comparison",
    "14_broadening_sensitivity", "15_full_paper_comparison",
    "16_root_cause_analysis", "17_final_report",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, text=True, capture_output=True,
            timeout=20, check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def ensure_stage_tree() -> None:
    for stage in STAGES:
        (DEMO_DIR / stage).mkdir(parents=True, exist_ok=True)


def professional_probe(machine_path: Path | None = None) -> tuple[Any | None, dict[str, Any]]:
    record: dict[str, Any] = {"available": False, "edition": "unavailable"}
    try:
        machine = demo_workflow.load_machine_config(machine_path)
    except Exception as exc:
        record["reason"] = f"machine configuration did not resolve: {type(exc).__name__}: {exc}"
        return None, record
    paths = {
        "executable": getattr(machine, "executable", None),
        "database": getattr(machine, "database", None),
        "license": getattr(machine, "license", None),
    }
    record.update({
        "machine_config": str(getattr(machine, "source_path", "")),
        "run_solver": bool(getattr(machine, "run_solver", False)),
        "results_root": str(getattr(machine, "results_root", "")),
        "configured_files": {
            key: {"name": Path(value).name if value else None,
                  "exists": bool(value and Path(value).is_file())}
            for key, value in paths.items()
        },
        "discovery_notes": list(getattr(machine, "discovery_notes", ())),
    })
    missing = [key for key, value in paths.items() if not value or not Path(value).is_file()]
    free_tokens = [str(value).lower() for value in paths.values() if value]
    is_free = any("free" in value for value in free_tokens)
    if missing:
        record["reason"] = "missing configured Professional file(s): " + ", ".join(missing)
        return machine, record
    if is_free:
        record.update(edition="free", reason="a configured path is explicitly a free-edition artifact")
        return machine, record
    if not machine.run_solver:
        record["reason"] = "machine configuration has run_solver disabled"
        return machine, record
    record.update(available=True, edition="professional", reason="complete non-free enabled configuration")
    return machine, record


def _free_parser() -> tuple[Path, Path, Path | None] | None:
    roots = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nextnano"]
    for root in roots:
        if not root.is_dir():
            continue
        executables = sorted(root.rglob("nextnano++_*_free.exe"), reverse=True)
        databases = sorted(root.rglob("database_free.nnp"), reverse=True)
        licences = sorted(root.rglob("License_free.lic"), reverse=True)
        if executables and databases:
            return executables[0], databases[0], licences[0] if licences else None
    return None


def syntax_check(decks: list[Path]) -> list[dict[str, Any]]:
    parser = _free_parser()
    rows: list[dict[str, Any]] = []
    log_dir = DEMO_DIR / "00_setup_and_provenance" / "syntax_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    if parser is None:
        return [{"deck": deck.name, "status": "NOT_RUN", "return_code": "",
                 "parser_edition": "none", "log": "", "notes": "free syntax parser not installed"}
                for deck in decks]
    executable, database, licence = parser
    for deck in decks:
        argv = [str(executable), "--parse", "-d", str(database)]
        if licence:
            argv += ["-l", str(licence)]
        argv.append(str(deck))
        run = subprocess.run(argv, cwd=DEMO_DIR, text=True, capture_output=True,
                             timeout=120, check=False)
        log = log_dir / f"{deck.stem}.txt"
        log.write_text(run.stdout + "\n--- STDERR ---\n" + run.stderr, encoding="utf-8")
        rows.append({"deck": deck.name, "status": "PASS" if run.returncode == 0 else "FAIL",
                     "return_code": run.returncode, "parser_edition": "LIMITED FREE; syntax only",
                     "log": str(log.relative_to(DEMO_DIR)),
                     "notes": "No physics was executed."})
    return rows


def _plot_inputs(cfg: dict[str, Any]) -> None:
    out = DEMO_DIR / "00_setup_and_provenance"
    interfaces = deck22.interfaces(cfg)
    x = np.linspace(0.0, 30.0, 3001)
    al = np.full_like(x, float(cfg["materials"]["barrier_al_fraction"]))
    al[(x >= interfaces[0]) & (x <= interfaces[1])] = 0.0
    al[(x >= interfaces[2]) & (x <= interfaces[3])] = 0.0
    plt.figure(figsize=(9, 3.8))
    plt.plot(x, al, label="primary abrupt Al fraction")
    for boundary in interfaces:
        plt.axvline(boundary, color="0.7", linewidth=.7)
    plt.xlabel("z (nm)"); plt.ylabel("Al mole fraction"); plt.ylim(-.03, .60)
    plt.grid(alpha=.2); plt.legend(); plt.tight_layout()
    plt.savefig(out / "00_geometry_primary_abrupt.png", dpi=220); plt.close()

    count = int(cfg["kp8"]["dispersion_points"])
    maximum = float(cfg["kp8"]["dispersion_kmax_per_nm"])
    k = np.linspace(0, maximum, count)
    plt.figure(figsize=(8, 3.8)); plt.plot(np.arange(count), k, label="requested radial path")
    plt.xlabel("requested point index"); plt.ylabel("k_parallel (nm$^{-1}$)")
    plt.grid(alpha=.2); plt.legend(); plt.tight_layout()
    plt.savefig(out / "00_requested_k_path.png", dpi=220); plt.close()


def _blocked_stage_docs(probe: dict[str, Any]) -> None:
    reason = probe.get("reason", "Professional nextnano++ unavailable")
    statuses = []
    for index, stage in enumerate(STAGES):
        status = "COMPLETE_PREFLIGHT" if index == 0 else "BLOCKED_NO_PROFESSIONAL_OUTPUT"
        statuses.append({"stage": stage, "status": status, "reason": "" if index == 0 else reason})
        if index:
            path = DEMO_DIR / stage / "BLOCKED.md"
            path.write_text(
                f"# {stage}: externally blocked\n\n"
                f"Status: **BLOCKED — no Professional solver output**.\n\n{reason}\n\n"
                "No synthetic bands, hard-coded energies, or scalar fallback were used. "
                "Run `python run_demo22.py --physics` on the licensed work laptop.\n",
                encoding="utf-8",
            )
    _write_csv(DEMO_DIR / "STAGE_STATUS.csv", statuses)
    _write_csv(DEMO_DIR / "01_kp8_solver_validation" / "solver_validation.csv", [
        {"check": "Professional executable/database/licence", "value": probe.get("edition", "unavailable"),
         "expected": "complete Professional installation", "tolerance": "exact",
         "pass_fail": "BLOCKED", "notes": reason},
        {"check": "actual kp8 solver execution", "value": "not run", "expected": "normal completion",
         "tolerance": "exact", "pass_fail": "BLOCKED", "notes": "free --parse is syntax-only"},
        {"check": "real finite-k output", "value": "absent", "expected": "explicit k vectors, energies, spinors",
         "tolerance": "required", "pass_fail": "BLOCKED", "notes": "no substitute was generated"},
    ])
    (DEMO_DIR / "PROFESSIONAL_RUN_BLOCKER.md").write_text(
        "# Professional execution blocker\n\n"
        f"{reason}\n\nThis machine cannot execute the requested k-resolved 8-band calculation. "
        "The installed free parser was used only to validate deck syntax. No solver spectra "
        "or scientific conclusions are claimed.\n",
        encoding="utf-8",
    )
    (DEMO_DIR / "16_root_cause_analysis" / "ROOT_CAUSE_ANALYSIS.md").write_text(
        "# Root-cause analysis — blocked status\n\n"
        "The completed home-laptop controls ruled out elementary χ² algebra, sign, phase, "
        "normalization, and tested quadrature errors as explanations. Demo 22 was designed to "
        "separate denominator/dispersion changes (Model C) from numerator/oscillator-strength "
        "changes (Model D).\n\nNo Demo 22 root cause can yet be ranked from actual kp8 evidence: "
        f"{reason}. All finite-k candidates—especially e2/h2 dispersion, HH/LH mixing, "
        "anticrossings, and k-dependent optical strength—remain **INCONCLUSIVE**.\n",
        encoding="utf-8",
    )
    (DEMO_DIR / "17_final_report" / "DEMO22_FINAL_REPORT.md").write_text(
        "# Demo 22 final report — NOT SCIENTIFICALLY COMPLETE\n\n"
        "## Execution status\n\n"
        f"Professional run blocked: {reason}. Six decks passed syntax parsing, but zero kp8 "
        "physics solves ran. Therefore there are no actual e1/e2/h1/h2 dispersions, no χ² "
        "spectrum, no node positions, no peak position, no RMSE, and no defensible k_max to "
        "report.\n\n"
        "## What is complete\n\n"
        "The exact 30 nm abrupt primary and 1 nm-linear control decks, 48/72/96 integration "
        "convergence, 301-point dispersion request, strict raw-output parser, character-based "
        "state tracker, validated 16-pathway k-resolved χ² adapter, staged plotting/table "
        "analysis, provenance manifest, tests, and fail-loud Professional gate are complete.\n\n"
        "## Required continuation\n\nRun `python run_demo22.py --physics` on the licensed work laptop. "
        "Do not interpret free-parser success as a spectrum.\n",
        encoding="utf-8",
    )


def preflight(cfg: dict[str, Any], machine_path: Path | None = None) -> tuple[list[Path], Any | None, dict[str, Any]]:
    ensure_stage_tree()
    input_dir = DEMO_DIR / "00_setup_and_provenance" / "inputs"
    decks = deck22.write_decks(cfg, input_dir)
    syntax_rows = syntax_check(decks)
    _write_csv(DEMO_DIR / "00_setup_and_provenance" / "syntax_validation.csv", syntax_rows)
    _plot_inputs(cfg)
    machine, probe = professional_probe(machine_path)
    manifest = {
        "demo": cfg["demo"], "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": platform.node(), "platform": platform.platform(), "python": sys.version,
        "repository_root": str(REPO_ROOT), "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")), "configuration": cfg,
        "professional_probe": probe,
        "installed_free_syntax_parser": (
            {"executable": str(_free_parser()[0]), "database": str(_free_parser()[1])}
            if _free_parser() else None
        ),
        "decks": [{"path": str(path.relative_to(DEMO_DIR)), "sha256": _sha256(path)} for path in decks],
        "syntax_validation": syntax_rows,
        "scientific_assertions": {
            "primary_geometry": "30 nm ideal-abrupt paper model",
            "secondary_control": "same 30 nm design with four 1 nm linear interfaces (Demo 21 Case 04)",
            "published_observable": cfg["paper"]["published_observable_label"],
            "synthetic_fallback_allowed": False,
        },
    }
    _write_json(DEMO_DIR / "00_setup_and_provenance" / "RUN_MANIFEST.json", manifest)
    readme = DEMO_DIR / "00_setup_and_provenance" / "README.md"
    readme.write_text(
        "# Demo 22 setup and provenance\n\n"
        "Controlled primary abrupt and secondary 1 nm-linear decks were rendered, with 48/72/96 "
        "point integration convergence and an explicit Gamma-to-y dispersion request. The installed free "
        "edition is used only in `--parse` mode. See `RUN_MANIFEST.json` for hashes and settings.\n",
        encoding="utf-8",
    )
    if not probe["available"]:
        _blocked_stage_docs(probe)
    return decks, machine, probe


def _run_professional(cfg: dict[str, Any], decks: list[Path], machine: Any) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = result_root(cfg) / f"demo22_{stamp}"
    run_root.mkdir(parents=True, exist_ok=False)
    monitor = _start_progress_monitor(run_root)
    try:
        records = []
        for deck in decks:
            raw = run_root / "raw" / deck.stem
            logs = run_root / "logs" / deck.stem
            invocation = solver14.execute_real(
                executable=Path(machine.executable), database=Path(machine.database),
                license_path=Path(machine.license), deck=deck, output_dir=raw,
                threads=int(cfg["solver"]["threads"]),
                timeout_seconds=float(cfg["solver"]["timeout_seconds_per_deck"]), logs_dir=logs,
            )
            records.append(invocation.as_record())
        _write_json(run_root / "solver_invocations.json", records)
    finally:
        _stop_progress_monitor(monitor)
    print("Demo 22 solver progress: 100%. Starting analysis...", flush=True)
    primary = run_root / "raw" / "abrupt_integration"
    summary = analysis22.run_analysis(cfg, primary, interface_model="abrupt", stage_root=DEMO_DIR)
    _write_json(run_root / "analysis_summary.json", summary)
    return run_root


def _start_progress_monitor(run_root: Path) -> subprocess.Popen[str] | None:
    """Show the read-only Demo 22 completion tracker in this terminal."""
    tracker = DEMO_DIR / "progress22.py"
    argv = [
        sys.executable, "-u", str(tracker), "--run", str(run_root),
        "--interval", "60", "--embedded",
    ]
    try:
        print("Starting Demo 22 completion tracker (updates every 60 s)...", flush=True)
        return subprocess.Popen(argv, cwd=REPO_ROOT)
    except OSError as exc:
        print(f"WARNING: completion tracker could not start: {exc}", file=sys.stderr)
        return None


def _stop_progress_monitor(monitor: subprocess.Popen[str] | None) -> None:
    """Stop only the tracker process created for this Demo 22 run."""
    if monitor is None or monitor.poll() is not None:
        return
    monitor.terminate()
    try:
        monitor.wait(timeout=5)
    except subprocess.TimeoutExpired:
        monitor.kill()
        monitor.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physics", action="store_true", help="require and run Professional kp8")
    parser.add_argument("--analyse-existing", type=Path, help="analyse an existing real raw-output root")
    parser.add_argument("--machine", type=Path, help="explicit machine YAML")
    args = parser.parse_args(argv)
    cfg = load_config()
    decks, machine, probe = preflight(cfg, args.machine)
    if args.analyse_existing:
        summary = analysis22.run_analysis(cfg, args.analyse_existing.resolve(),
                                          interface_model="abrupt", stage_root=DEMO_DIR)
        print(json.dumps(summary, indent=2))
        return 0
    if not args.physics:
        print(f"Demo 22 preflight complete: {DEMO_DIR}")
        print(f"Professional available: {probe['available']} ({probe.get('reason', '')})")
        return 0
    if not probe["available"] or machine is None:
        raise Demo22Error(
            "--physics requires a complete non-free nextnano++ Professional configuration; "
            f"{probe.get('reason', 'unavailable')}. See PROFESSIONAL_RUN_BLOCKER.md"
        )
    run_root = _run_professional(cfg, decks, machine)
    print(f"Demo 22 Professional run and analysis complete: {run_root}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Demo22Error as exc:
        print(f"DEMO 22 ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
