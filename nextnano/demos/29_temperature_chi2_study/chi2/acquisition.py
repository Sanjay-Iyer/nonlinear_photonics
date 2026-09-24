"""Temperature-controlled deck preparation and work-laptop Professional execution."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from . import decks, run_debug

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/study.json"
SINGLE = ROOT / "nextnano/inputs/singleband_case04_graded.in"
JOBS = ("kp8", "singleband_case04_graded")


def config() -> dict:
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    fixed = {"temperatures_K": [100, 300, 500], "lattice_constant_nm": 0.565325,
             "kmax_pi_over_a": 0.10, "k_max_per_nm": 0.555714439232,
             "k_points": 301, "num_electrons": 6, "num_holes": 8}
    for key, value in fixed.items():
        if c[key] != value:
            raise ValueError(f"Demo 29 fixed configuration changed: {key}")
    expected_settings = {"gamma_meV": 5.0, "gamma_sign": 1, "spin_degeneracy": 2,
                         "period_nm": 30.0, "r_e_hh_nm": 0.751}
    if c["settings"] != expected_settings or c["wavelength_nm"] != {"min": 400.0, "max": 1850.0, "step": 1.0}:
        raise ValueError("Demo 29 Equation 2 settings or wavelength grid changed")
    if abs(c["k_max_per_nm"] - c["kmax_pi_over_a"] * 3.141592653589793 / c["lattice_constant_nm"]) > 1e-9:
        raise ValueError("0.10 pi/a conversion inconsistent")
    return c


def job_decks(temperature: int, c: dict, pilot: bool = False,
              pilot_finite_k: bool = False) -> dict[str, str]:
    if temperature not in c["temperatures_K"]:
        raise ValueError("Temperature must be 100, 300 or 500 K")
    if pilot and pilot_finite_k:
        raise ValueError("Choose only one pilot mode")
    if pilot_finite_k and temperature != 300:
        raise ValueError("The finite-k output pilot is a 300 K diagnostic run")
    kp_config = {**c, "k_points": 3} if pilot else c
    result = {"kp8": decks.render_full_kp8(temperature, kp_config, finite_k_pilot=pilot_finite_k)}
    if not (pilot or pilot_finite_k):
        result["singleband_case04_graded"] = decks.render_singleband(temperature, decks.read(SINGLE))
    for kind, body in result.items():
        problems = decks.static_check(body, "kp8" if kind == "kp8" else "singleband")
        if problems:
            raise ValueError(f"{kind}: {problems}")
        field = re.findall(r"(?m)^\s*temperature\s*=\s*([0-9.]+)\s*$", body)
        if len(field) != 1 or float(field[0]) != temperature:
            raise ValueError(f"{kind}: wrong solver temperature")
    return result


def check_decks(c: dict) -> dict:
    if not decks.same_deck(decks.render_kp8(),
                           decks.read(ROOT / "nextnano/inputs/kp8_dispersion.in")):
        raise ValueError("Local 8-band renderer no longer matches the archived 300 K physics deck")
    prepared = {t: job_decks(t, c) for t in c["temperatures_K"]}
    for kind in JOBS:
        reference = decks.without_temperature(prepared[300][kind])
        if any(decks.without_temperature(prepared[t][kind]) != reference for t in c["temperatures_K"]):
            raise ValueError(f"{kind} changed beyond temperature")
    kp = prepared[300]["kp8"]
    for token in ("point{ k = [0, 0.555714439232, 0] }", "num_points = 301",
                  "num_electrons = 6", "num_holes     = 8", "all_k_points = yes",
                  "envelopes_CB_HH_LH_SO = yes", "spinor_composition_CB_HH_LH_SO = yes"):
        if token not in kp:
            raise ValueError("Missing fixed 8-band field: " + token)
    pilot = job_decks(300, c, pilot_finite_k=True)["kp8"]
    for token in ("num_points = 301", "point{ k = [0, 0.555714439232, 0] }",
                  "relative_size = 0.03", "num_points = 5", "num_subpoints = 1",
                  "force_k0_subspace = no", "all_k_points = yes"):
        if token not in pilot:
            raise ValueError("Finite-k pilot is missing " + token)
    return {"status": "PASS", "temperatures_K": c["temperatures_K"],
            "only_deck_difference": "global temperature", "kmax_pi_over_a": .10,
            "k_points": 301, "state_pool": [6, 8],
            "scope": "static deck check only; finite-k state output is not verified",
            "finite_k_pilot": {"temperature_K": 300, "dispersion_points": 301,
                               "integration_relative_size": 0.03,
                               "integration_num_points": 5,
                               "frame_count": "read from k_points.txt after solver run",
                               "force_k0_subspace": "no"}}


def prepare(c: dict, root: Path) -> dict:
    check = check_decks(c)
    for t in c["temperatures_K"]:
        folder = root / f"{t}K"
        folder.mkdir(parents=True, exist_ok=True)
        for kind, body in job_decks(t, c).items():
            (folder / f"{kind}.in").write_text(body, encoding="utf-8", newline="\n")
    (root / "deck_check.json").write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
    return check


def _solver_paths() -> dict[str, str]:
    machine = ROOT.parents[1] / "config/paths.local.yaml"
    local = {}
    if machine.is_file():
        import yaml
        local = (yaml.safe_load(machine.read_text(encoding="utf-8")) or {}).get("nextnano++") or {}
    paths = {key: os.environ.get(env) for key, env in
             (("exe", "NEXTNANO_EXE"), ("database", "NEXTNANO_DATABASE"), ("license", "NEXTNANO_LICENSE"))}
    paths = {key: value or local.get(key) for key, value in paths.items()}
    missing = [key for key, path in paths.items() if not path or not Path(path).is_file()]
    if missing:
        raise ValueError("Set valid NEXTNANO_EXE, NEXTNANO_DATABASE, NEXTNANO_LICENSE: " + ", ".join(missing))
    if "free" in Path(paths["exe"]).name.lower():
        raise ValueError("A Professional executable is required")
    return {key: str(Path(value).resolve()) for key, value in paths.items()}


def _redact_command(command: list[str]) -> list[str]:
    shown = command.copy()
    for i, word in enumerate(shown[:-1]):
        if word == "-l":
            shown[i + 1] = "<LICENSE_PATH_REDACTED>"
    return shown


def _last_message(*paths: Path) -> str:
    for path in sorted((p for p in paths if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file():
            with path.open("rb") as handle:
                handle.seek(max(0, path.stat().st_size - 32_768))
                lines = handle.read().decode("utf-8", errors="replace").splitlines()
            meaningful = [line.strip() for line in lines if line.strip()]
            if meaningful:
                return meaningful[-1][:200]
    return "No solver message yet"


def _monitor_command(command: list[str], log_dir: Path, result: Path, t: int, label: str,
                     stage: str, expected_frames: int | None, timeout: int,
                     interval: float = 15.0) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    started_wall = time.time()
    with (log_dir / "stdout.log").open("w", encoding="utf-8") as stdout, \
         (log_dir / "stderr.log").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        code = None
        previous_frames = set()
        while code is None:
            alive = process.poll() is None
            scan = run_debug.scan_output(result, expected_frames, quick=True)
            current_frames = set(scan["frame_identifiers"])
            new_frames = sorted(current_frames - previous_frames)
            previous_frames = current_frames
            newest = max([started_wall] + [p.stat().st_mtime for p in
                                           (log_dir / "stdout.log", log_dir / "stderr.log") if p.exists()] +
                         ([datetime.fromisoformat(scan["latest_file_mtime_utc"]).timestamp()]
                          if scan["latest_file_mtime_utc"] else []))
            message = _last_message(log_dir / "stderr.log", log_dir / "stdout.log")
            if "license" in message.lower() or run_debug.SENSITIVE_LINE.search(message):
                message = "<sensitive solver message redacted; see sanitized debug ZIP>"
            print(f"\nDemo 29 — {t} K — {label}\n"
                  f"Started: {time.strftime('%H:%M:%S', time.localtime(started_wall))}\n"
                  f"Current: {time.strftime('%H:%M:%S')}\n"
                  f"Elapsed: {run_debug.elapsed_hms(time.monotonic() - started)}\n"
                  f"Stage: {stage}\n"
                  f"Process: {'running' if alive else 'exited'}, PID {process.pid}\n"
                  f"Last output update: {int(max(0, time.time() - newest))} s ago\n"
                  f"Finite-k state frames detected: {scan['actual_finite_k_state_frames']}"
                  f"{' / ' + str(expected_frames) + ' nominal' if expected_frames else ''}\n"
                  f"Frame IDs (latest): {', '.join(scan['frame_identifiers'][-10:]) or 'none'}\n"
                  f"New frames since last update: {', '.join(new_frames) or 'none'}\n"
                  f"Frames with all component files: {scan['component_file_sets_complete']}\n"
                  f"Composition files: {scan['composition_files']}; envelope files: {scan['spinor_envelope_files']}\n"
                  f"Unrecognized relevant paths: {scan['relevant_files_ignored_total']}\n"
                  f"Latest solver message: {message}", flush=True)
            if not alive:
                code = process.returncode
                break
            if time.monotonic() - started >= timeout:
                process.kill()
                process.wait()
                code = -1
                break
            try:
                code = process.wait(timeout=interval)
            except subprocess.TimeoutExpired:
                continue
            except KeyboardInterrupt:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise
    elapsed = round(time.monotonic() - started, 1)
    print(f"{label} {stage} exited with code {code}; total elapsed {run_debug.elapsed_hms(elapsed)}", flush=True)
    return {"start_utc": datetime.fromtimestamp(started_wall,
             timezone.utc).isoformat(timespec="seconds"),
            "end_utc": run_debug.now_utc(), "elapsed_seconds": elapsed,
            "return_code": code, "termination_status": "timeout" if code == -1 else "exited",
            "pid": process.pid, "command": _redact_command(command)}


def _copy_logs(log_dir: Path, destination: Path) -> None:
    """Keep the historical combined log at the solver root for transfer tools."""
    with destination.open("w", encoding="utf-8") as output:
        for name in ("stdout.log", "stderr.log"):
            path = log_dir / name
            if path.is_file():
                with path.open("r", encoding="utf-8", errors="replace") as source:
                    shutil.copyfileobj(source, output)


def run(t: int, c: dict, result: Path, pilot: bool = False,
        pilot_finite_k: bool = False, poll_seconds: float = 15.0,
        run_id: str | None = None) -> None:
    paths = _solver_paths()
    if result.exists():
        raise ValueError(f"Refusing to overwrite {result}")
    jobs = job_decks(t, c, pilot=pilot, pilot_finite_k=pilot_finite_k)
    audit = subprocess.run([sys.executable, str(ROOT / "scripts/audit_dependencies.py")],
                           capture_output=True, text=True, timeout=30, check=False)
    if audit.returncode:
        raise ValueError(f"Demo isolation audit failed: {audit.stdout} {audit.stderr}")
    result.parent.mkdir(parents=True, exist_ok=True)
    if not result.parent.is_dir():
        raise ValueError(f"Cannot create output root: {result.parent}")
    git_before = run_debug.git_state()
    run_id = run_id or run_debug.new_run_id("pilotfk" if pilot_finite_k else "pilot" if pilot else "production")
    log_dir = ROOT / "nextnano/run_logs" / f"{t}K" / run_id
    if log_dir.exists():
        raise ValueError(f"Run-log directory already exists: {log_dir}")
    log_dir.mkdir(parents=True)
    result.mkdir()
    (result / "decks").mkdir()
    metadata = {"temperature_K": t, "pilot": pilot or pilot_finite_k,
                "pilot_kind": "finite_k" if pilot_finite_k else "legacy_three_point" if pilot else None,
                "run_id": run_id, "log_dir": str(log_dir), "started_utc": run_debug.now_utc(),
                "professional_execution_performed": False,
                "source_config": c, "jobs": {}, "executable_sha256": hashlib.sha256(Path(paths["exe"]).read_bytes()).hexdigest(),
                "database_sha256": hashlib.sha256(Path(paths["database"]).read_bytes()).hexdigest()}
    manifest = result / "run_metadata.json"
    def save():
        manifest.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    def event(message: str):
        with (log_dir / "runner.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{run_debug.now_utc()} {message}\n")
    expected = None  # The solver, not the deck's num_points, determines frame count.
    provenance = {"git": git_before, "kmax_pi_over_a": c["kmax_pi_over_a"],
                  "dispersion_points": 301 if pilot_finite_k else c["k_points"],
                  "k_integration": ({"relative_size": 0.03, "num_points": 5,
                                     "num_subpoints": 1, "symmetry": "none", "force_k0_subspace": "no",
                                     "frame_count": "read from k_points.txt"} if pilot_finite_k else "disabled"),
                  "output_states": {"all_k_points": "yes", "envelopes_CB_HH_LH_SO": "yes",
                                    "spinor_composition_CB_HH_LH_SO": "yes", "in_one_file": "no"},
                  "path_checks": {"executable": paths["exe"], "executable_exists": True,
                                  "database": paths["database"], "database_exists": True,
                                  "license_configured_and_exists": True,
                                  "output_root": str(result), "output_parent_exists": True,
                                  "demo_root": str(ROOT), "numbered_demo_audit": audit.stdout.strip()},
                  "execution": {}}
    print(f"Run ID: {run_id}\nSolver output: {result}\nRuntime logs: {log_dir}", flush=True)
    print(f"Preflight: Professional executable exists: {paths['exe']}\n"
          f"Preflight: database exists: {paths['database']}\n"
          "Preflight: license path configured and exists: yes (path redacted)\n"
          f"Preflight: output parent exists: {result.parent}\n"
          f"Preflight: Demo directory: {ROOT}\n"
          f"Preflight: numbered-demo dependency audit: {audit.stdout.strip()}", flush=True)
    event(f"Run started; temperature={t}K; pilot_finite_k={pilot_finite_k}; output={result}")
    (log_dir / "run_manifest.json").write_text(json.dumps({
        "run_id": run_id, "temperature_K": t, "started_utc": metadata["started_utc"],
        "git_before_run": git_before, "solver_output": str(result),
        "status": "RUNNING", "pilot_kind": metadata["pilot_kind"],
        "license_configured_and_exists": True}, indent=2) + "\n", encoding="utf-8")
    save()
    started_run = time.monotonic()
    failure = None
    try:
        for name, body in jobs.items():
            label = "8-band finite-k pilot" if pilot_finite_k else "8-band" if name == "kp8" else "single-band"
            deck = result / "decks" / f"{name}.in"
            deck.write_text(body, encoding="utf-8", newline="\n")
            print(f"Input deck ready: {deck}", flush=True)
            target = result / name
            target.mkdir()
            provenance["path_checks"][f"{name}_deck_exists"] = deck.is_file()
            provenance["path_checks"][f"{name}_target"] = str(target)
            base = [paths["exe"], "-d", paths["database"], "-l", paths["license"],
                    "--threads", str(c["threads"]), "-o", str(target), str(deck)]
            parse = [paths["exe"], "--parse", "-d", paths["database"], "-l", paths["license"],
                     "--threads", "1", "-o", str(result / f"parse_{name}"), str(deck)]
            event(f"{name}: grammar parse started")
            parse_result = _monitor_command(parse, log_dir / f"parse_{name}", result, t,
                                            label, "grammar parse", expected, 300, poll_seconds)
            provenance["execution"][f"parse_{name}"] = parse_result
            _copy_logs(log_dir / f"parse_{name}", result / f"{name}_parse.log")
            parse_text = (result / f"{name}_parse.log").read_text(encoding="utf-8", errors="replace")
            if parse_result["return_code"] or "DONE." not in parse_text:
                metadata["jobs"][name] = {"status": "PARSE_FAIL", "parse_return_code": parse_result["return_code"]}
                save()
                raise RuntimeError(f"{name} grammar check failed; see parse log")
            metadata["jobs"][name] = {"status": "RUNNING", "deck_sha256": hashlib.sha256(deck.read_bytes()).hexdigest()}
            metadata["professional_execution_performed"] = True
            save()
            event(f"{name}: solver started; output={target}")
            solver_result = _monitor_command(base, log_dir / name, result, t, label,
                                             "solver", expected, c["timeout_seconds_per_job"], poll_seconds)
            provenance["execution"][name] = solver_result
            _copy_logs(log_dir / name, result / f"{name}.log")
            code = solver_result["return_code"]
            metadata["jobs"][name].update(status="PASS" if code == 0 else "FAIL", return_code=code,
                                           elapsed_seconds=solver_result["elapsed_seconds"])
            save()
            event(f"{name}: solver exited with code {code}")
            if code:
                raise RuntimeError(f"{name} solver failed; see {result / (name + '.log')}")
    except BaseException as exc:
        failure = exc
        event(f"Run interrupted/failed: {type(exc).__name__}: {exc}")
    finally:
        metadata["ended_utc"] = run_debug.now_utc()
        metadata["total_elapsed_seconds"] = round(time.monotonic() - started_run, 1)
        save()
        (log_dir / "run_manifest.json").write_text(json.dumps({
            "run_id": run_id, "temperature_K": t, "started_utc": metadata["started_utc"],
            "ended_utc": metadata["ended_utc"], "elapsed_seconds": metadata["total_elapsed_seconds"],
            "git_before_run": git_before, "solver_output": str(result),
            "status": "FAIL" if failure is not None else "PASS",
            "jobs": metadata["jobs"], "execution": provenance["execution"],
            "license_configured_and_exists": True}, indent=2) + "\n", encoding="utf-8")
        try:
            for name in jobs:
                target = result / name
                found = [str(p.relative_to(result)) for p in target.rglob("job_done.txt")]
                provenance["path_checks"][f"{name}_job_done_locations"] = found
                provenance["path_checks"][f"{name}_expected_target_exists"] = target.is_dir()
            debug = run_debug.collect_debug(result, log_dir, t, expected, run_id, provenance,
                                            redactions=[paths["license"]])
            status = debug["diagnostic"]
            print("\nRun complete." if failure is None else "\nRun stopped.")
            print(f"Total elapsed runtime: {run_debug.elapsed_hms(metadata['total_elapsed_seconds'])}")
            print(f"8-band dispersion points: {status['dispersion']['points']}")
            print(f"Finite-k spinor frames found: {status['actual_finite_k_state_frames']}"
                  f"{' / ' + str(expected) + ' nominal' if expected else ''}")
            print(f"Complete complex 8-component frames: {status['complete_state_frames']}")
            print(f"Composition frames found: {status['composition_files']}")
            grid = status.get("integration_grid", {})
            complete = (pilot_finite_k and status["dispersion"]["points"] == 301 and
                        abs(status["dispersion"]["k_max_per_nm"] - c["k_max_per_nm"]) < 5e-10 and
                        grid.get("points") == status["actual_finite_k_state_frames"] and
                        status["complete_state_frames"] == grid.get("points") and
                        grid.get("complete_target_path_frames", 0) >= 3 and
                        status["k0_exists"] and not status["duplicate_frames"])
            if pilot_finite_k:
                print("Target-aligned finite-k pilot has at least three complete path frames." if complete else
                      "WARNING: target-path coverage incomplete; inspect k_points.txt and debug ZIP.")
            if debug["warnings"]:
                print("Recent solver warnings/errors: " + " | ".join(debug["warnings"][-3:]))
            print(f"Runtime logs: {log_dir}\nDebug bundle: {debug['zip']}", flush=True)
        except (ValueError, OSError, KeyError) as exc:
            print(f"WARNING: debug bundle generation failed: {exc}; logs remain at {log_dir}", file=sys.stderr)
    if failure is not None:
        raise failure


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="static checks only; no solver")
    mode.add_argument("--prepare", action="store_true", help="write all three temperature deck pairs; no solver")
    mode.add_argument("--run", action="store_true", help="Professional work-laptop execution")
    p.add_argument("--temperature", type=int)
    p.add_argument("--pilot", action="store_true", help="3-point 8-band output-coverage pilot")
    p.add_argument("--pilot-finite-k", action="store_true",
                   help="300 K small k-integration pilot; retain the 301-point dispersion")
    p.add_argument("--output", type=Path)
    a = p.parse_args(argv)
    try:
        c = config()
        check = check_decks(c)
        if a.check:
            print(json.dumps(check, indent=2))
        elif a.prepare:
            if a.pilot or a.pilot_finite_k:
                raise ValueError("Pilot switches require --run")
            print(json.dumps(prepare(c, a.output or ROOT / "nextnano/prepared"), indent=2))
        else:
            if a.temperature is None:
                raise ValueError("--run requires --temperature")
            if a.pilot and a.pilot_finite_k:
                raise ValueError("Choose only one pilot mode")
            if a.pilot_finite_k and a.temperature != 300:
                raise ValueError("--pilot-finite-k currently requires --temperature 300")
            new_id = run_debug.new_run_id("pilotfk") if a.pilot_finite_k else None
            suffix = f"pilot_finite_k_{a.temperature}K_{new_id}" if a.pilot_finite_k else (
                     f"pilot_{a.temperature}K" if a.pilot else f"{a.temperature}K")
            output = a.output or ROOT / "nextnano/work_runs" / suffix
            run(a.temperature, c, output.resolve(), a.pilot, a.pilot_finite_k, run_id=new_id)
        return 0
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
