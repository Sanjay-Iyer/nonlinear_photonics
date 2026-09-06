"""The physics stage: the only place in Demo 27 that launches a solver.

Three kinds of physics stage exist.

``professional``
    Demo 27 runs its own decks with nextnano++ Professional and writes a
    manifest per deck.
``delegated``
    Another demo already owns this calculation. Demo 27 runs that demo's runner
    with one explicit command and records what it ran. It never forks the other
    demo's implementation, and it never runs more than the single command mapped
    to this stage.
``none`` / ``external``
    There is nothing to launch. The stage refuses rather than pretending.

Every path here is per-sub-demo. There is no function that iterates over
sub-demos and runs them, by construction.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

from . import Demo27Error
from . import manifest as manifest_module
from .registry import DEMOS_DIR, REPO_ROOT, Resolved, SubDemo
from .report import write_json
from .solver import assert_professional

DEMO14 = DEMOS_DIR / "14_absolute_chi2_graded_acqw_bo"


def run(sub: SubDemo, resolved: Resolved, machine: Mapping,
        cost: Mapping, *, timeout_seconds: float) -> dict:
    kind = sub.stage_kind("physics")
    if kind == "professional":
        return _run_professional(sub, resolved, machine, cost, timeout_seconds=timeout_seconds)
    if kind == "delegated":
        return _run_delegated(sub, resolved, machine, cost)
    raise Demo27Error(
        "%s has no physics stage to run (stage kind %r). %s"
        % (sub.demo_id, kind,
           {"python": "It is analysis-only: use --analyze.",
            "external": "It needs tooling outside nextnano; see its README.",
            "none": "Nothing is defined for it yet."}.get(kind, "")))


def _run_professional(sub: SubDemo, resolved: Resolved, machine: Mapping,
                      cost: Mapping, *, timeout_seconds: float) -> dict:
    solver = assert_professional(machine)
    if str(DEMO14) not in sys.path:
        sys.path.insert(0, str(DEMO14))
    import solver14  # noqa: PLC0415

    decks_dir = sub.inputs_dir
    pairs = []
    for entry in resolved.decks:
        path = decks_dir / ("%s.in" % entry.spec.name)
        if not path.is_file():
            raise Demo27Error("deck %s has not been generated; run --preflight first" % path)
        pairs.append((entry, path))
    if not pairs:
        raise Demo27Error("%s has no decks to run; run --preflight first" % sub.demo_id)

    raw_root = resolved.results_root / "raw"
    manifests = []
    records = []
    for entry, path in pairs:
        case = raw_root / entry.spec.name
        case.mkdir(parents=True, exist_ok=True)
        print("  running %s ..." % path.name, flush=True)
        started = time.time()
        invocation = solver14.execute_real(
            executable=Path(solver["executable"]),
            database=Path(solver["database"]),
            license_path=Path(solver["license"]),
            deck=path, output_dir=case, threads=int(solver["threads"]),
            timeout_seconds=float(timeout_seconds), logs_dir=case / "logs")
        elapsed = time.time() - started
        blob = getattr(invocation, "__dict__", {}) or {}
        record = manifest_module.build(
            sub_demo=sub.demo_id, stage="physics", deck=path, output_dir=case,
            machine=solver, spec_summary=manifest_module.spec_summary(entry.spec),
            changes=entry.changes, seconds=elapsed, returncode=blob.get("returncode"),
            argv=blob.get("argv"), cost_statement=cost)
        manifests.append(record)
        records.append({"deck": path.name, "seconds": elapsed,
                        "returncode": blob.get("returncode"),
                        "files": record["outputs"]["files"],
                        "bytes": record["outputs"]["bytes"]})
        print("    %s: %.1f s, %d files, %.2f MB"
              % (path.name, elapsed, record["outputs"]["files"],
                 record["outputs"]["bytes"] / 1e6), flush=True)
    manifest_module.write(sub.outputs_dir, manifests)
    write_json(resolved.results_root / "physics_invocations.json", records)
    return {"kind": "professional", "runs": records, "manifest_count": len(manifests)}


def _run_delegated(sub: SubDemo, resolved: Resolved, machine: Mapping,
                   cost: Mapping) -> dict:
    delegate = dict(sub.delegate or {})
    for key in ("demo", "runner", "commands"):
        if key not in delegate:
            raise Demo27Error("%s declares a delegated physics stage but its delegate block "
                              "has no %r" % (sub.demo_id, key))
    command = (delegate["commands"] or {}).get("physics")
    if not command:
        raise Demo27Error("%s has no delegate command mapped for the physics stage"
                          % sub.demo_id)
    runner = DEMOS_DIR / str(delegate["demo"]) / str(delegate["runner"])
    if not runner.is_file():
        raise Demo27Error(
            "%s delegates to %s, which does not exist. Demo 27 will not reimplement it."
            % (sub.demo_id, runner))
    assert_professional(machine)
    argv = [sys.executable, str(runner)] + str(command).split()
    print("  delegating to: %s" % " ".join(argv[1:]), flush=True)
    started = time.time()
    done = subprocess.run(argv, cwd=str(REPO_ROOT), check=False)
    elapsed = time.time() - started
    record = manifest_module.build(
        sub_demo=sub.demo_id, stage="physics", deck=runner, output_dir=resolved.results_root,
        machine={"executable": str(machine.get("exe", "")), "database": str(machine.get("database", "")),
                 "license": str(machine.get("license", "")), "threads": int(machine.get("threads", 1))},
        spec_summary={"delegated_to": str(delegate["demo"]), "command": str(command),
                      "reason": str(delegate.get("reason", ""))},
        changes={}, seconds=elapsed, returncode=done.returncode, argv=argv,
        cost_statement=cost)
    manifest_module.write(sub.outputs_dir, [record])
    return {"kind": "delegated", "returncode": done.returncode, "seconds": elapsed,
            "delegate": str(delegate["demo"]), "command": str(command)}
