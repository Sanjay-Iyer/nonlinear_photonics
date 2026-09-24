"""Temperature-controlled deck preparation and work-laptop Professional execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from . import decks

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


def job_decks(temperature: int, c: dict, pilot: bool = False) -> dict[str, str]:
    if temperature not in c["temperatures_K"]:
        raise ValueError("Temperature must be 100, 300 or 500 K")
    kp_config = {**c, "k_points": 3} if pilot else c
    result = {"kp8": decks.render_full_kp8(temperature, kp_config)}
    if not pilot:
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
    return {"status": "PASS", "temperatures_K": c["temperatures_K"],
            "only_deck_difference": "global temperature", "kmax_pi_over_a": .10,
            "k_points": 301, "state_pool": [6, 8],
            "scope": "static deck check only; finite-k state output is not verified"}


def prepare(c: dict, root: Path) -> dict:
    check = check_decks(c)
    for t in c["temperatures_K"]:
        folder = root / f"{t}K"
        folder.mkdir(parents=True, exist_ok=True)
        for kind, body in job_decks(t, c).items():
            (folder / f"{kind}.in").write_text(body, encoding="utf-8", newline="\n")
    (root / "deck_check.json").write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
    return check


def run(t: int, c: dict, result: Path, pilot: bool = False) -> None:
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
    if result.exists():
        raise ValueError(f"Refusing to overwrite {result}")
    result.mkdir(parents=True)
    (result / "decks").mkdir()
    jobs = job_decks(t, c, pilot)
    metadata = {"temperature_K": t, "pilot": pilot, "professional_execution_performed": False,
                "source_config": c, "jobs": {}, "executable_sha256": hashlib.sha256(Path(paths["exe"]).read_bytes()).hexdigest(),
                "database_sha256": hashlib.sha256(Path(paths["database"]).read_bytes()).hexdigest()}
    manifest = result / "run_metadata.json"
    def save():
        manifest.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    save()
    for name, body in jobs.items():
        deck = result / "decks" / f"{name}.in"
        deck.write_text(body, encoding="utf-8", newline="\n")
        target = result / name
        target.mkdir()
        base = [paths["exe"], "-d", paths["database"], "-l", paths["license"],
                "--threads", str(c["threads"]), "-o", str(target), str(deck)]
        parse = [paths["exe"], "--parse", "-d", paths["database"], "-l", paths["license"],
                 "--threads", "1", "-o", str(result / f"parse_{name}"), str(deck)]
        with (result / f"{name}_parse.log").open("w", encoding="utf-8") as log:
            parsed = subprocess.run(parse, stdout=log, stderr=subprocess.STDOUT, timeout=300, check=False)
        parse_text = (result / f"{name}_parse.log").read_text(encoding="utf-8", errors="replace")
        if parsed.returncode or "DONE." not in parse_text:
            metadata["jobs"][name] = {"status": "PARSE_FAIL", "parse_return_code": parsed.returncode}
            save()
            raise RuntimeError(f"{name} grammar check failed; see parse log")
        metadata["jobs"][name] = {"status": "RUNNING", "deck_sha256": hashlib.sha256(deck.read_bytes()).hexdigest()}
        metadata["professional_execution_performed"] = True
        save()
        started = time.monotonic()
        with (result / f"{name}.log").open("w", encoding="utf-8") as log:
            try:
                completed = subprocess.run(base, stdout=log, stderr=subprocess.STDOUT,
                                           timeout=c["timeout_seconds_per_job"], check=False)
                code = completed.returncode
            except subprocess.TimeoutExpired:
                code = -1
        metadata["jobs"][name].update(status="PASS" if code == 0 else "FAIL", return_code=code,
                                       elapsed_seconds=round(time.monotonic() - started, 1))
        save()
        if code:
            raise RuntimeError(f"{name} solver failed; see {result / (name + '.log')}")
    print(f"Completed {t} K {'pilot' if pilot else 'production'} solver jobs in {result}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="static checks only; no solver")
    mode.add_argument("--prepare", action="store_true", help="write all three temperature deck pairs; no solver")
    mode.add_argument("--run", action="store_true", help="Professional work-laptop execution")
    p.add_argument("--temperature", type=int)
    p.add_argument("--pilot", action="store_true", help="3-point 8-band output-coverage pilot")
    p.add_argument("--output", type=Path)
    a = p.parse_args(argv)
    try:
        c = config()
        check = check_decks(c)
        if a.check:
            print(json.dumps(check, indent=2))
        elif a.prepare:
            print(json.dumps(prepare(c, a.output or ROOT / "nextnano/prepared"), indent=2))
        else:
            if a.temperature is None:
                raise ValueError("--run requires --temperature")
            output = a.output or ROOT / "nextnano/work_runs" / (f"pilot_{a.temperature}K" if a.pilot else f"{a.temperature}K")
            run(a.temperature, c, output.resolve(), a.pilot)
        return 0
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
