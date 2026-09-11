"""Script 1 implementation: render decks, preflight, dry-run, or run nextnano++ Professional.

Preflight and dry-run never launch a physics solve. The only executable they may
start is an explicitly configured (or discovered) nextnano++ parser in --parse mode,
which checks grammar and needs no Professional license.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from . import decks

ROOT = Path(__file__).resolve().parents[1]
FATAL = ("terminating program", "fatal error", "license expired", "validation error", "license is not valid")
METADATA = "demo28_run_metadata.json"
EXPECTED = {
    "kp8": ["dispersion_*.dat", "kVectors_*.dat", "kp8/energy_spectrum_k00000.dat",
            "kp8/spinor_composition_k00000_CbHhLhSo.dat", "kp8/envelope_k00000_0001_cb1.dat",
            "dipole_moment_matrix_elements_k00000_growth_z.txt"],
    "singleband": ["Gamma/energy_spectrum_k00000.dat", "Gamma/envelopes_k00000.dat",
                   "HH/energy_spectrum_k00000.dat", "HH/envelopes_k00000.dat"],
}


def sha256(path) -> str | None:
    p = Path(path) if path else None
    return hashlib.sha256(p.read_bytes()).hexdigest() if p and p.is_file() else None


def command(executable, database, license_path, deck, output, threads) -> list[str]:
    """Argument order used by the Professional runs (-d/-l/-o/--threads)."""
    return [executable or "<NEXTNANO_EXE>", "-d", database or "<NEXTNANO_DATABASE>",
            "-l", license_path or "<NEXTNANO_LICENSE>", "--threads", str(threads),
            "-o", str(output), str(deck)]


def read_machine(path: Path | None) -> dict:
    """Flat 'key: value' machine file (e.g. nextnano_machine.work.yaml)."""
    if not path:
        return {}
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip('"').strip("'")
    return {"exe": out.get("executable") or out.get("exe"), "database": out.get("database"),
            "license": out.get("license"), "threads": out.get("threads")}


def discover_parser() -> tuple[str | None, str | None]:
    exe = os.environ.get("NEXTNANO_PARSER_EXE")
    db = os.environ.get("NEXTNANO_PARSER_DATABASE")
    if exe:
        return exe, db
    for cand in sorted(glob.glob("C:/Program Files/nextnano/*/nextnano++/bin*/nextnano++*.exe"), reverse=True):
        dbs = sorted(glob.glob(str(Path(cand).parents[1] / "database" / "database*.nnp")))
        if dbs:
            return cand, dbs[0]
    return None, None


def parse_check(exe, database, deck: Path, scratch: Path, license=None) -> dict:
    """Grammar-only check. A Free build needs no license; a licensed build is given one when available."""
    argv = [str(exe), "--parse", "-d", str(database)]
    if license:
        argv += ["-l", str(license)]
    argv += ["--threads", "1", "-o", str(scratch), str(deck)]
    tail = []
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=300, check=False)
        blob = (done.stdout or "") + (done.stderr or "")
        ok = done.returncode == 0 and "DONE." in blob
        errors = [l.strip()[:200] for l in blob.splitlines()
                  if "error" in l.lower() and "checking database for errors" not in l.lower()][:3]
        if not ok:
            tail = [l.rstrip()[:200] for l in blob.splitlines() if l.strip()][-15:]
            errors = errors or [f"exit code {done.returncode}"]
    except (OSError, subprocess.TimeoutExpired) as exc:
        ok, errors = False, [str(exc)]
    out = {"status": "PASS" if ok else "FAIL", "parser": Path(exe).name, "errors": errors}
    if tail:
        out["output_tail"] = tail
    return out


def build_jobs(config: dict, which: str, overrides: dict) -> list[dict]:
    params = {k: v for k, v in config["kp8"].items() if k not in ("job", "purpose")}
    params.update({k: v for k, v in overrides.items() if v is not None})
    jobs = [{"job": "kp8", "kind": "kp8", "purpose": config["kp8"]["purpose"], "params": params,
             "text": decks.render_kp8(params, "Demo28 k-space baseline kp8 deck")}]
    if which == "all":
        for j in config["legacy_single_band"]:
            jobs.append({"job": j["job"], "kind": "singleband", "purpose": j["purpose"],
                         "text": decks.read(ROOT / j["deck"])})
    for job in jobs:
        problems = decks.static_check(job["text"], job["kind"])
        if problems:
            raise ValueError(f"deck {job['job']} failed static checks: {problems}")
    return jobs


def verify_outputs(target: Path, kind: str) -> list[str]:
    return [pat for pat in EXPECTED[kind] if not any(p.is_file() for p in target.rglob(pat))]


def parser_probe(root: Path) -> dict:
    """Can Script 2's parser read a results root? (imports Script 2 code only for this probe)"""
    try:
        from .input_builder import build_inputs
        inputs, _ = build_inputs(root)
        return {"baseline_parser":"PASS","kp8_pair_ids":inputs['kp8_pair_ids'],"k_points":len(inputs['k_per_nm'])}
    except Exception as exc:  # report, never crash Script 1 on a probe
        return {"error": f"{type(exc).__name__}: {exc}"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scripts/run_nextnano.py", description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="validate everything, launch nothing (default)")
    mode.add_argument("--dry-run", action="store_true", help="also write decks and the exact commands; launch nothing")
    mode.add_argument("--run", action="store_true", help="execute nextnano++ Professional")
    ap.add_argument("--exe", default=os.environ.get("NEXTNANO_EXE"))
    ap.add_argument("--database", default=os.environ.get("NEXTNANO_DATABASE"))
    ap.add_argument("--license", dest="license_path", default=os.environ.get("NEXTNANO_LICENSE"))
    ap.add_argument("--machine", type=Path, default=os.environ.get("NEXTNANO_MACHINE"),
                    help="flat key: value file with executable/database/license/threads")
    ap.add_argument("--output", type=Path, default=Path(os.environ.get("DEMO28_RAW_OUTPUT", ROOT / "nextnano" / "new_results")))
    ap.add_argument("--config", type=Path, default=ROOT / "config" / "runner.json")
    ap.add_argument("--jobs", choices=["kp8", "all"], default="all",
                    help="kp8 = production run only; all = also the two historical single-band decks")
    ap.add_argument("--threads", type=int)
    ap.add_argument("--timeout", type=float, help="seconds per deck")
    ap.add_argument("--k-max-per-nm", type=float, help="override kp8 dispersion endpoint (default 0.555714439232)")
    ap.add_argument("--k-points", type=int, help="override kp8 dispersion points (default 301)")
    ap.add_argument("--interface", choices=["linear_1nm", "abrupt"], help="override interface model")
    ap.add_argument("--parser-exe", help="nextnano++ build used for --parse grammar checks (Free is fine)")
    ap.add_argument("--parser-database")
    ap.add_argument("--no-parse", action="store_true", help="skip the grammar check")
    args = ap.parse_args(argv)
    run_mode = "run" if args.run else "dry-run" if args.dry_run else "preflight"
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        machine = read_machine(args.machine)
        exe = args.exe or machine.get("exe")
        database = args.database or machine.get("database")
        license_path = args.license_path or machine.get("license")
        threads = args.threads if args.threads is not None else int(machine.get("threads") or config["threads"])
        timeout = args.timeout if args.timeout is not None else float(config["timeout_seconds_per_deck"])
        if threads < 1 or timeout <= 0:
            raise ValueError("threads and timeout must be positive")
        overrides = {"k_max_per_nm": args.k_max_per_nm, "k_points": args.k_points, "interface_model": args.interface}
        jobs = build_jobs(config, args.jobs, overrides)
        output = args.output.expanduser().resolve()
        missing = [n for n, v in (("executable", exe), ("database", database), ("license", license_path))
                   if not v or not Path(v).is_file()]
        if exe and "free" in Path(exe).name.lower():
            missing.append("executable is a Free build; Professional is required for these decks")
        if run_mode == "run":  # refuse before touching the results folder at all
            if missing:
                raise ValueError("--run needs nextnano++ Professional executable, database and license: " + "; ".join(missing))
            busy = [j["job"] for j in jobs if (output / j["job"]).is_dir() and any((output / j["job"]).iterdir())]
            if busy or (output / METADATA).exists():
                raise ValueError(f"refusing to overwrite existing results in {output} "
                                 f"({busy or METADATA}); choose a fresh --output")

        parser_exe, parser_db = (args.parser_exe, args.parser_database) if args.parser_exe else discover_parser()
        output.mkdir(parents=True, exist_ok=True)
        deck_dir = output / "decks"
        records = []
        for job in jobs:
            deck_path = deck_dir / f"{job['job']}.in"
            if run_mode != "preflight":
                deck_dir.mkdir(exist_ok=True)
                deck_path.write_text(job["text"], encoding="utf-8", newline="\n")
            grammar = {"status": "SKIPPED", "reason": "no nextnano++ parser configured or found"}
            if not args.no_parse and parser_exe and parser_db:
                with tempfile.TemporaryDirectory(prefix="demo28_parse_") as tmp:
                    probe = Path(tmp) / f"{job['job']}.in"
                    probe.write_text(job["text"], encoding="utf-8", newline="\n")
                    grammar = parse_check(parser_exe, parser_db, probe, Path(tmp) / "out")
            records.append({"job": job["job"], "kind": job["kind"], "purpose": job["purpose"],
                            "params": job.get("params"), "deck_sha256": hashlib.sha256(job["text"].encode()).hexdigest(),
                            "static_check": "PASS", "grammar_check": grammar,
                            "expected_outputs": EXPECTED[job["kind"]],
                            "argv": command(exe, database, license_path, deck_path, output / job["job"], threads)})

        manifest = {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "mode": run_mode,
                    "professional_execution_performed": False, "missing_configuration": missing,
                    "threads": threads, "timeout_seconds": timeout, "output_root": str(output),
                    "script2_parser_self_test_on_shipped_cached_raw": parser_probe(ROOT / "nextnano/raw_results"),
                    "jobs": records, "python": platform.python_version(), "platform": sys.platform,
                    "executable_sha256": sha256(exe), "database_sha256": sha256(database)}
        report = output / (METADATA if run_mode == "run" else f"{run_mode.replace('-', '_')}_manifest.json")
        save = lambda: report.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        save()
        for r in records:
            print(f"[{r['job']}] static PASS | grammar {r['grammar_check']['status']} | "
                  + subprocess.list2cmdline(r["argv"]))
        if any(r["grammar_check"]["status"] == "FAIL" for r in records):
            print(f"Grammar check FAILED; see {report}", file=sys.stderr)
            return 1
        if run_mode != "run":
            print(f"{run_mode}: no solver launched. Missing for --run: {missing or 'nothing'}. Manifest: {report}")
            return 0

        for r in records:
            target = output / r["job"]
            target.mkdir(parents=True, exist_ok=True)
            log = output / f"{r['job']}.log"
            r["status"], start = "RUNNING", time.time()
            manifest["professional_execution_performed"] = True
            save()
            try:
                with log.open("w", encoding="utf-8") as stream:
                    done = subprocess.run(r["argv"], cwd=output, stdout=stream, stderr=subprocess.STDOUT,
                                          timeout=timeout, check=False)
            except subprocess.TimeoutExpired:
                r.update(status="FAIL", error=f"timeout after {timeout:g} s", seconds=round(time.time() - start, 1))
                save()
                print(f"nextnano job {r['job']} timed out; inspect {log}", file=sys.stderr)
                return 1
            r["return_code"], r["seconds"] = done.returncode, round(time.time() - start, 1)
            text = log.read_text(encoding="utf-8", errors="replace").lower()
            gaps = verify_outputs(target, r["kind"])
            if done.returncode or any(m in text for m in FATAL) or gaps:
                r["status"], r["missing_outputs"] = "FAIL", gaps
                save()
                print(f"nextnano job {r['job']} failed (code {done.returncode}); inspect {log}", file=sys.stderr)
                return 1
            info = next(target.rglob("simulation_info.txt"), None)
            r["simulation_info_head"] = info.read_text(errors="replace").splitlines()[:12] if info else None
            r["status"] = "PASS"
            save()
        manifest["script2_parser_on_this_output"] = parser_probe(output)
        save()
        print(f"All jobs PASS. Next: python scripts/calculate_chi2.py --input \"{output}\"")
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
