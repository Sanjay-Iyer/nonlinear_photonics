"""Demo 30 optional k extension to 0.2·π/a: the WORK-laptop package.

    HOME  prepare     render the decks from the locked control deck and syntax-check them
                      with the Free parser (not a licensed run)
    WORK  preflight   find the licensed exe/database/license; licensed --parse of both decks
    WORK  pilot       7 k points to 0.2·π/a (~1-2 min): proves finite-k dispersion output
    WORK  full        601 k points to 0.2·π/a (~20 min): the extension run
    WORK  validate    check a finished run folder (also run automatically after pilot/full)
    WORK  package     RUN_RECORD.json + SHA256SUMS.txt + zip for Google Drive
    HOME  lock-entry  after downloading and unzipping: print (or --write) the lock entry

The decks differ from the control deck (D023_2026-09-04_kp8-disp-k0p10pia-n301-300K) ONLY
in the k endpoint and num_points. The endpoint is exactly 2 x the control endpoint
(1.111428878464 nm^-1 = 0.2·π/a within 5e-13), so the new k nodes coincide with the
control grid and validation can compare energies node by node. Per-k STATES are not
requested, as in the control: the Demo 30 model freezes matrix elements at k = 0 and
needs only the dispersion. That avoids the Demo 28K failure mode (per-k states came
back only at k = 0).

See work_laptop/README.md for the exact command sequence.
"""
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
import tempfile
import zipfile

WL = Path(__file__).resolve().parent
DEMO_ROOT = WL.parent
REPO_ROOT = DEMO_ROOT.parents[2]
sys.path.insert(0, str(DEMO_ROOT))

from demo30 import parse_nextnano as io  # noqa: E402

DECKS = WL / "decks"
PLAN = WL / "run_plan.json"
REFERENCE = WL / "control_reference_nodes.json"
CONTROL_POINT = "point{ k = [0, 0.555714439232, 0] }"
CONTROL_NPTS = "num_points = 301"
EXT_KMAX = "1.111428878464"
MODES = {"pilot": {"points": 7, "deck": DECKS / "k0p20pia_n7_pilot.in", "tag": "kp8-disp-k0p20pia-n7-pilot-300K",
                   "control_nodes": [0, 100, 200, 300], "new_nodes": [0, 1, 2, 3]},
         "full": {"points": 601, "deck": DECKS / "k0p20pia_n601.in", "tag": "kp8-disp-k0p20pia-n601-300K",
                  "control_nodes": [0, 100, 200, 300], "new_nodes": [0, 100, 200, 300]}}
FREE_EXE = Path("C:/Program Files/nextnano/2026_07_03/nextnano++/bin 32bit/nextnano++_Microsoft_32bit_free.exe")
FREE_DB = Path("C:/Program Files/nextnano/2026_07_03/nextnano++/database/database_free.nnp")
REDACT = re.compile(r"licensed to|license key|serial", re.IGNORECASE)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- HOME: prepare
def render(control: str, points: int) -> str:
    for token in (CONTROL_POINT, CONTROL_NPTS):
        if control.count(token) != 1:
            raise ValueError(f"control deck must contain {token!r} exactly once")
    return (control.replace(CONTROL_POINT, f"point{{ k = [0, {EXT_KMAX}, 0] }}")
                   .replace(CONTROL_NPTS, f"num_points = {points}"))


def free_parse(deck: Path) -> dict:
    if not FREE_EXE.is_file() or not FREE_DB.is_file():
        return {"status": "NOT_RUN", "reason": "Free nextnano++ parser not found on this machine"}
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run([str(FREE_EXE), "--parse", "-d", str(FREE_DB), "-o", tmp, str(deck)],
                              capture_output=True, text=True, timeout=300)
    text = proc.stdout + proc.stderr
    errors = [line for line in text.splitlines() if line.strip().upper().startswith("ERROR")]
    ok = proc.returncode == 0 and not errors and "DONE." in text  # "Checking database for errors..." is normal
    return {"status": "PASS" if ok else "FAIL", "return_code": proc.returncode, "error_lines": errors,
            "parser": "Free nextnano++ 3.0.0 (grammar check only; not a licensed run)"}


def prepare(args) -> int:
    from demo30 import rawdata
    run = rawdata.resolve("kp8_dispersion", root=args.raw_root)
    control_deck = run.folder / run.entry["deck"]["path"]
    control = control_deck.read_text(encoding="utf-8")
    DECKS.mkdir(parents=True, exist_ok=True)
    plan = {"control_run": run.run_id, "control_deck_sha256": sha256(control_deck),
            "changed_lines": [CONTROL_POINT + f"  ->  point{{ k = [0, {EXT_KMAX}, 0] }}", CONTROL_NPTS + "  ->  num_points = N"],
            "k_max_per_nm": float(EXT_KMAX), "k_max_label": "0.2·π/a (a = 0.565325 nm; exactly 2x the control endpoint)",
            "decks": {}}
    for mode, spec in MODES.items():
        text = render(control, spec["points"])
        spec["deck"].write_text(text, encoding="utf-8", newline="\n")
        diff = [(a, b) for a, b in zip(control.splitlines(), text.splitlines()) if a != b]
        if len(diff) != 2 or len(control.splitlines()) != len(text.splitlines()):
            raise RuntimeError(f"{mode}: expected exactly two changed lines, got {diff}")
        plan["decks"][mode] = {"path": spec["deck"].relative_to(DEMO_ROOT).as_posix(), "sha256": sha256(spec["deck"]),
                               "k_points": spec["points"], "run_id_pattern": f"D030_<YYYY-MM-DD>_{spec['tag']}",
                               "free_parse_check": free_parse(spec["deck"])}
    k, energies, _ = io.read_dispersion(run.parser_root)
    nodes = MODES["full"]["control_nodes"]
    REFERENCE.write_text(json.dumps({"control_run": run.run_id, "note": "control 8-band energies (eV) at k nodes shared with the new grids",
                                     "nodes": {str(i): {"k_per_nm": float(k[i]), "energies_eV": energies[i].tolist()} for i in nodes}},
                                    indent=2) + "\n", encoding="utf-8")
    plan["runtime_estimate"] = {"basis": "control run D023 (301 k points, 14 states) took 10 min 20 s on WORK; 28K (601 k, 24 states) took 16.6 min",
                                "pilot": "about 1-2 min", "full": "about 20 min"}
    plan["storage_estimate"] = {"basis": "control run folder = 18 MB, 738 files, dominated by k=0 state output; k-dependent files ~0.2 MB per 301 points",
                                "pilot": "about 18 MB", "full": "about 18.5 MB (zip about 5-7 MB)"}
    PLAN.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    for mode, d in plan["decks"].items():
        print(f"{mode}: {d['path']} ({d['k_points']} k points) Free --parse: {d['free_parse_check']['status']}")
    return 0 if all(d["free_parse_check"]["status"] in ("PASS", "NOT_RUN") for d in plan["decks"].values()) else 1


# ---------------------------------------------------------------- WORK: paths
def licensed_paths(args) -> dict:
    """CLI flag > NEXTNANO_* environment > nextnano/config/paths.local.yaml > tracked work machine YAML."""
    import yaml
    local, machine = {}, {}
    p = REPO_ROOT / "nextnano" / "config" / "paths.local.yaml"
    if p.is_file():
        local = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("nextnano++") or {}
    m = REPO_ROOT / "nextnano" / "config" / "machines" / "nextnano_machine.work.yaml"
    if m.is_file():
        machine = yaml.safe_load(m.read_text(encoding="utf-8")) or {}

    def pick(flag, env, local_key, machine_key):
        for value in (flag, os.environ.get(env), local.get(local_key), machine.get(machine_key)):
            if value and "PATH_TO" not in str(value):
                return Path(os.path.expandvars(os.path.expanduser(str(value))))
        return None
    out = {"exe": pick(args.exe, "NEXTNANO_EXE", "exe", "executable"),
           "database": pick(args.database, "NEXTNANO_DATABASE", "database", "database"),
           "license": pick(args.license, "NEXTNANO_LICENSE", "license", "license"),
           "results_root": Path(args.results_root) if args.results_root else Path(machine.get("results_root", "C:/nn_results"))}
    missing = [k for k in ("exe", "database", "license") if not out[k] or not out[k].is_file()]
    if missing:
        raise SystemExit(f"licensed nextnano paths not found: {missing}. Set them in nextnano/config/paths.local.yaml "
                         "or pass --exe/--database/--license.")
    if "free" in out["exe"].name.lower():
        raise SystemExit("refusing the Free executable: this package needs the licensed Professional build")
    return out


def preflight(args) -> int:
    paths = licensed_paths(args)
    ok = True
    for mode, spec in MODES.items():
        if not spec["deck"].is_file():
            raise SystemExit(f"{spec['deck']} is missing: run 'prepare' on HOME and git pull")
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run([str(paths["exe"]), "--parse", "-d", str(paths["database"]), "-l", str(paths["license"]),
                                   "-o", tmp, str(spec["deck"])], capture_output=True, text=True, timeout=600)
        text = proc.stdout + proc.stderr
        parsed = proc.returncode == 0 and "LIMITED FREE VERSION" not in text
        ok &= parsed
        print(f"{mode}: licensed --parse {'PASS' if parsed else 'FAIL'} (return code {proc.returncode})")
    paths["results_root"].mkdir(parents=True, exist_ok=True)
    print(f"results root: {paths['results_root']} (writable)")
    return 0 if ok else 1


# ---------------------------------------------------------------- WORK: run
def run(args, mode: str) -> int:
    spec = MODES[mode]
    paths = licensed_paths(args)
    start = utc_now()
    run_id = f"D030_{start:%Y-%m-%d}_{spec['tag']}"
    folder = paths["results_root"] / run_id
    command = [str(paths["exe"]), "-d", str(paths["database"]), "-l", str(paths["license"]),
               "--threads", str(args.threads), "-o", str(folder / "data"), str(spec["deck"])]
    if args.dry_run:
        print("would run:", " ".join(command))
        return 0
    if folder.exists():
        raise SystemExit(f"{folder} exists; never reuse a run folder (rerun on another day or add -r2 by hand)")
    (folder / "data").mkdir(parents=True)
    print(f"{run_id}: running nextnano++ ({spec['points']} k points); log -> solver_log_redacted.txt")
    proc = subprocess.run(command, capture_output=True, text=True)
    end = utc_now()
    log = "\n".join("[redacted license line]" if REDACT.search(line) else line
                    for line in (proc.stdout + "\n" + proc.stderr).splitlines())
    (folder / "solver_log_redacted.txt").write_text(log + "\n", encoding="utf-8")
    info = {"run_id": run_id, "mode": mode, "started_utc": start.isoformat(timespec="seconds"),
            "finished_utc": end.isoformat(timespec="seconds"), "runtime_s": round((end - start).total_seconds(), 1),
            "return_code": proc.returncode, "threads": args.threads,
            "command": [c if c != str(paths["license"]) else "<license>" for c in command],
            "executable_sha256": sha256(paths["exe"]), "database_sha256": sha256(paths["database"]),
            "deck": spec["deck"].relative_to(DEMO_ROOT).as_posix(), "deck_sha256": sha256(spec["deck"])}
    (folder / "run_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    report = validate_folder(folder)
    print(f"{run_id}: {report['result']} after {info['runtime_s']} s")
    for problem in report["problems"]:
        print("  " + problem)
    return 0 if report["result"] == "PASS" else 1


# ---------------------------------------------------------------- validation
def validate_folder(folder: Path) -> dict:
    folder = Path(folder)
    info = json.loads((folder / "run_info.json").read_text(encoding="utf-8"))
    spec = MODES[info["mode"]]
    problems, facts = [], {}
    if info["return_code"] != 0:
        problems.append(f"solver return code {info['return_code']}")
    log = (folder / "solver_log_redacted.txt").read_text(encoding="utf-8", errors="replace")
    if "LIMITED FREE VERSION" in log:
        problems.append("solver log shows the Free edition")
    data = folder / "data"
    if len(list(data.rglob("job_done.txt"))) != 1:
        problems.append("job_done.txt missing (solver did not finish)")
    try:
        k, energies, _ = io.read_dispersion(data)
        facts.update(k_points=len(k), k_max_per_nm=float(k[-1]), states=int(energies.shape[1]))
        if len(k) != spec["points"]:
            problems.append(f"dispersion has {len(k)} k points, expected {spec['points']}")
        if abs(k[-1] - float(EXT_KMAX)) > 1e-9:
            problems.append(f"k_max {k[-1]} != {EXT_KMAX}")
        if energies.shape[1] != 14:
            problems.append(f"{energies.shape[1]} states, expected 14")
        spread = float(abs(energies[-1] - energies[0]).max())
        facts["max_energy_change_k0_to_kmax_eV"] = spread
        if not spread > 0.05:
            problems.append("energies barely change with k: no genuine finite-k dispersion (the 28K failure mode)")
        ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
        worst = 0.0
        for c, n in zip(spec["control_nodes"], spec["new_nodes"]):
            node = ref["nodes"][str(c)]
            if abs(k[n] - node["k_per_nm"]) > 1e-9:
                problems.append(f"node {n} k={k[n]} does not coincide with control node {c}")
            worst = max(worst, float(abs(energies[n] - node["energies_eV"]).max()))
        facts["max_abs_energy_difference_vs_control_eV"] = worst
        if worst > 1e-6:
            problems.append(f"energies differ from the control run by {worst:.2e} eV at shared k nodes")
    except (io.RawDataError, OSError, ValueError, KeyError) as exc:
        problems.append(f"dispersion unreadable: {exc}")
    for name in ("energy_spectrum_k00000.dat", "spinor_composition_k00000_CbHhLhSo.dat"):
        if len(list(data.rglob(name))) != 1:
            problems.append(f"k=0 file {name} missing or duplicated (needed for the pair assignment)")
    facts["per_k_state_files_beyond_k0"] = sum(1 for p in data.rglob("*_k0*.dat") if "_k00000" not in p.name)
    report = {"run_id": info["run_id"], "result": "PASS" if not problems else "FAIL", "problems": problems, "facts": facts,
              "note": "per-k states are intentionally NOT requested (frozen-matrix model); finite-k data = the dispersion",
              "validated_utc": utc_now().isoformat(timespec="seconds")}
    (folder / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def validate(args) -> int:
    report = validate_folder(Path(args.folder))
    print(f"{report['run_id']}: {report['result']}")
    for problem in report["problems"]:
        print("  " + problem)
    return 0 if report["result"] == "PASS" else 1


# ---------------------------------------------------------------- packaging
def package(args) -> int:
    folder = Path(args.folder)
    info = json.loads((folder / "run_info.json").read_text(encoding="utf-8"))
    report = json.loads((folder / "validation.json").read_text(encoding="utf-8"))
    spec = MODES[info["mode"]]
    data = folder / "data"
    hashes = {("data/" + p.relative_to(data).as_posix()): sha256(p) for p in sorted(data.rglob("*")) if p.is_file()}
    decks = [n for n in hashes if n.endswith(".in")]
    if any(n.lower().endswith(".lic") for n in hashes):
        raise SystemExit("a license file is inside data/: refusing to package")
    (folder / "SHA256SUMS.txt").write_bytes("".join(f"{d}  {n}\n" for n, d in sorted(hashes.items())).encode())
    record = {"run_id": info["run_id"], "originating_demo": 30, "sub_study": "30F",
              "date": info["run_id"].split("_")[1], "started_utc": info["started_utc"], "finished_utc": info["finished_utc"],
              "machine": "WORK", "licensed": True,
              "solver": {"name": "nextnano++", "executable_sha256": info["executable_sha256"],
                         "database_sha256": info["database_sha256"], "log": "solver_log_redacted.txt"},
              "deck": {"path": decks[0] if len(decks) == 1 else None, "sha256": hashes.get(decks[0]) if len(decks) == 1 else None,
                       "repository_deck": info["deck"], "repository_deck_sha256": info["deck_sha256"]},
              "physics": {"model": "8-band k.p (kp8): dispersion path Gamma->y plus k=0 spinor envelopes and composition",
                          "temperature_K": 300.0, "k_direction": [0, 1, 0], "k_max_per_nm": float(EXT_KMAX),
                          "k_max_label": "0.2·π/a (a = 0.565325 nm)", "k_points": spec["points"],
                          "states": {"num_electrons": 6, "num_holes": 8, "output_states": 14}},
              "structure": "identical to the Demo 30 control deck except the k endpoint and num_points",
              "status": "valid" if report["result"] == "PASS" else "failed", "validation": report,
              "provenance": "Demo 30 work_laptop/kmax_run.py on the WORK laptop; transferred by hand via Google Drive",
              "sha256sums_sha256": sha256(folder / "SHA256SUMS.txt"),
              "registered_utc": None, "notes": ""}
    (folder / "RUN_RECORD.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    archive = folder.parent / f"{info['run_id']}.zip"
    if archive.exists():
        raise SystemExit(f"{archive} exists; not overwriting")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, Path(info["run_id"]) / p.relative_to(folder))
    size = archive.stat().st_size / 1e6
    print(f"packaged {archive} ({size:.1f} MB, status {record['status']})")
    print("Upload this zip to Google Drive, folder nextnano_raw/demo_030/. Do NOT commit it to Git.")
    return 0


# ---------------------------------------------------------------- HOME: lock entry
def lock_entry(args) -> int:
    folder = Path(args.folder)
    record = json.loads((folder / "RUN_RECORD.json").read_text(encoding="utf-8"))
    if record["status"] != "valid":
        raise SystemExit(f"{record['run_id']} has status {record['status']}; not adding it to the lock")
    data_root = next(p for p in (folder / "data").iterdir() if p.is_dir())
    rel = lambda p: p.relative_to(folder).as_posix()  # noqa: E731
    pinned = [io.find_one(data_root, "dispersion_*.dat"), io.find_one(data_root, "kVectors_*.dat"),
              io.find_one(data_root, "kp8/energy_spectrum_k00000.dat"),
              io.find_one(data_root, "spinor_composition_k00000_CbHhLhSo.dat")]
    entry = {"required": False, "run_id": record["run_id"], "originating_demo": 30, "date": record["date"],
             "model": "8-band k.p dispersion path Gamma->y, k=0 spinors and composition", "temperature_K": 300.0,
             "k_max": "0.2·π/a = 1.111428878464 nm^-1 (a = 0.565325 nm)", "k_points": record["physics"]["k_points"],
             "expected_dir": f"demo_030/{record['run_id']}", "parser_root": rel(data_root), "status": "valid",
             "deck": {"path": record["deck"]["path"], "sha256": record["deck"]["sha256"]},
             "files": {rel(p): sha256(p) for p in pinned}, "sha256sums_sha256": record["sha256sums_sha256"],
             "used_for": "30F optional k extension to 0.2·π/a (deck identical to the control except the k endpoint and num_points)"}
    role = "kp8_dispersion_k0p20"
    print(json.dumps({role: entry}, indent=2))
    if args.write:
        lock_path = DEMO_ROOT / "inputs" / "raw_data.lock.json"
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["runs"][role] = entry
        lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"written to {lock_path}")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--raw-root")
    for name in ("preflight", "pilot", "full"):
        s = sub.add_parser(name)
        for flag in ("--exe", "--database", "--license", "--results-root"):
            s.add_argument(flag)
        s.add_argument("--threads", type=int, default=4)
        s.add_argument("--dry-run", action="store_true")
    for name in ("validate", "package", "lock-entry"):
        s = sub.add_parser(name)
        s.add_argument("folder")
        if name == "lock-entry":
            s.add_argument("--write", action="store_true", help="insert the entry into inputs/raw_data.lock.json")
    args = parser.parse_args(argv)
    if args.command == "prepare":
        return prepare(args)
    if args.command == "preflight":
        return preflight(args)
    if args.command in ("pilot", "full"):
        return run(args, args.command)
    return {"validate": validate, "package": package, "lock-entry": lock_entry}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
