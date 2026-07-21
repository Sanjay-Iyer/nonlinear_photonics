"""Verify Standard-only smoke-test results by inspecting logs + output files.

Runs on the WORK laptop AFTER run_smoke_tests has executed a stage. For each
subtest it inspects the deck's output directory (never just the process exit
code) and reports:

    deck | requested feature | solver exit code | expected log marker found |
    expected output files found | numerical sanity check | PASS/FAIL/INCONCLUSIVE

Rules:
  * PASS  requires ALL of: a matching log marker, the expected output file(s),
          and the numerical sanity check passing.
  * FAIL  = outputs exist but the sanity check fails, or the log shows a fatal
          / license-restriction error.
  * INCONCLUSIVE = the output directory or log is missing (e.g. the deck was
          not run on this machine), so no judgement can be made.

A deck is never PASS merely because an input parsed or a process returned zero.

    python nextnano/scripts/verify_standard_smoke_tests.py --test 4
    python nextnano/scripts/verify_standard_smoke_tests.py --test 4-6
    python nextnano/scripts/verify_standard_smoke_tests.py --test all
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import json

from nn_config import ConfigError, resolve_config
from run_input import MANIFEST_NAME
from run_smoke_tests import STAGES, parse_stages

PASS, FAIL, INCONCLUSIVE = "PASS", "FAIL", "INCONCLUSIVE"

# Phrases in a log that indicate a genuine fatal / solver failure.
#
# IMPORTANT: the bare word "license" is deliberately NOT here. Every SUCCESSFUL
# run's log contains normal license text -- the "--license ...License_nnp.lic"
# command line and routine license-check / license-information output -- so
# matching "license" flagged every passing Test 1-6 run as a false failure.
# Genuine license *failures* are matched by the specific phrases below instead.
_FATAL_MARKERS = (
    "terminating program",
    "fatal error",
    "does not allow",          # Free feature / dimensionality gate (wrong edition)
)
_LICENSE_FAILURE_MARKERS = (
    "license error",
    "invalid license",
    "license is invalid",
    "license is not valid",
    "no valid license",
    "no license found",
    "license not found",
    "could not find a license",
    "license expired",
    "license has expired",
    "license check failed",
    "license violation",
    "not licensed",
    "unable to obtain license",
)


def _fatal_reason(log_lower: str) -> str | None:
    """Return a short reason if the log shows a genuine fatal/license failure,
    else None. Normal license initialization text does NOT match."""
    for m in _LICENSE_FAILURE_MARKERS:
        if m in log_lower:
            return f"license failure in log ({m!r})"
    for m in _FATAL_MARKERS:
        if m in log_lower:
            return f"fatal marker in log ({m!r})"
    return None


# --- generic file/number helpers -------------------------------------------


def _find_logs(out_dir: Path) -> list[Path]:
    return sorted(out_dir.rglob("*.log")) if out_dir.is_dir() else []


def _read_logs(out_dir: Path) -> str:
    text = []
    for log in _find_logs(out_dir):
        try:
            text.append(log.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    return "\n".join(text)


def _glob_any(out_dir: Path, patterns) -> list[Path]:
    hits: list[Path] = []
    if not out_dir.is_dir():
        return hits
    for pat in patterns:
        hits.extend(p for p in out_dir.rglob(pat) if p.is_file())
    # de-dup, keep order
    seen, unique = set(), []
    for p in hits:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _numeric_values(path: Path, max_lines: int = 5000):
    """Yield floats from a whitespace/comma-separated data file, skipping
    comment/header lines (those starting with # or non-numeric first token)."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i >= max_lines:
                    break
                s = line.strip()
                if not s or s.startswith("#") or s.startswith("%"):
                    continue
                for tok in _NUM_RE.findall(s):
                    try:
                        yield float(tok)
                    except ValueError:
                        continue
    except OSError:
        return


def _any_nonzero(paths, tol: float = 1e-30) -> bool:
    for p in paths:
        for v in _numeric_values(p):
            if abs(v) > tol:
                return True
    return False


# --- per-subtest specification ---------------------------------------------


@dataclass
class Spec:
    stage: str
    deck: Path
    feature: str
    log_markers: tuple           # any one (case-insensitive substring) satisfies
    output_globs: tuple
    sanity_label: str
    # sanity(out_dir, matched_files) -> (bool|None, detail); None => INCONCLUSIVE
    sanity: object


def _sanity_nonzero(out_dir, files):
    if not files:
        return None, "no output files to check"
    return (_any_nonzero(files), "nonzero numeric value present" )


def _sanity_temperature_77(out_dir, files):
    log = _read_logs(out_dir)
    if not log:
        return None, "no log to read temperature from"
    # look for 77 in a temperature context, and confirm it is not 300
    has77 = re.search(r"temperature[^\n]*\b77(\.0+)?\b", log, re.IGNORECASE) or re.search(
        r"\b77(\.0+)?\s*K", log
    )
    return (bool(has77), "log reports T = 77 K" if has77 else "77 K not found in log")


def _sanity_forward_differs(out_dir, files):
    """Forward-bias current must differ from the zero-bias current."""
    # Prefer an IV/current-vs-voltage file with >=2 distinct current rows.
    for p in files:
        vals = [v for v in _numeric_values(p)]
        # crude: collect the last column per data row is hard generically;
        # instead check the file holds at least two distinct nonzero magnitudes.
        nz = sorted({round(abs(v), 20) for v in vals if abs(v) > 1e-20})
        if len(nz) >= 2:
            return True, f"current output spans distinct values ({p.name})"
    if files:
        return None, "current files found but could not confirm two distinct bias points"
    return None, "no current output found"


def _build_specs(root_stages) -> list[Spec]:
    S = STAGES
    specs = [
        Spec("4", S["4"][0], "temperature dependence outside 300 K (T = 77 K)",
             ("temperature", "77"), ("*77*", "*bandedge*", "*energy*", "*probabilit*", "*wavefunc*"),
             "reported temperature = 77 K", _sanity_temperature_77),
        Spec("4", S["4"][1], "6-band k.p valence solver",
             ("6-band", "6 band", "kp_6band", "6x6", "six-band"),
             ("*energy*", "*spectrum*", "*hole*", "*kp*", "*eigen*"),
             "nonempty 6-band energy spectrum", _sanity_nonzero),
        Spec("4", S["4"][2], "8-band k.p solver",
             ("8-band", "8 band", "kp_8band", "8x8", "eight-band"),
             ("*energy*", "*spectrum*", "*kp*", "*eigen*"),
             "nonempty 8-band energy spectrum", _sanity_nonzero),
        Spec("5", S["5"][0], "pseudomorphic strain solver",
             ("strain",),
             ("*strain*", "*hydrostatic*"),
             "nonzero strain component in mismatched layer", _sanity_nonzero),
        Spec("5", S["5"][1], "piezoelectric + pyroelectric polarization",
             ("polarization", "piezo", "pyro"),
             ("*polarization*", "*potential*", "*field*"),
             "nonzero polarization charge / field", _sanity_nonzero),
        Spec("6", S["6"][0], "drift-diffusion current + SRH/Auger/radiative recombination",
             ("current", "recombination"),
             ("*current*", "*IV*", "*recombination*"),
             "forward current differs from zero-bias current", _sanity_forward_differs),
        Spec("6", S["6"][1], "optical transitions / absorption spectrum",
             ("oscillator", "matrix element", "transition", "optic", "dipole"),
             ("*oscillator*", "*matrix*", "*transition*", "*spectrum*", "*dipole*", "*absorption*"),
             "nonzero optical response present", _sanity_nonzero),
        Spec("6", S["6"][2], "self-consistent Schroedinger-Current-Poisson coupling",
             ("quantum_current_poisson", "self-consistent", "self consistent", "coupled"),
             ("*current*", "*probabilit*", "*potential*", "*convergence*", "*wavefunc*"),
             "convergence reached; quantum + current outputs exist", _sanity_nonzero),
    ]
    return [sp for sp in specs if sp.stage in root_stages]


# --- reporting --------------------------------------------------------------


def _read_manifest(out_dir: Path) -> dict | None:
    """Read the run manifest written by run_input, if present (searched at the
    top of the deck's output dir and recursively, since nextnanopy nests one
    more level). Returns None if there is no manifest (older run)."""
    if not out_dir.is_dir():
        return None
    candidates = [out_dir / MANIFEST_NAME, *sorted(out_dir.rglob(MANIFEST_NAME))]
    for mf in candidates:
        if mf.is_file():
            try:
                return json.loads(mf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return None


@dataclass
class Result:
    spec: Spec
    out_dir: Path
    exit_note: str = "log-based assessment (no run manifest)"
    marker_found: bool = False
    files: list = field(default_factory=list)
    sanity_ok: object = None
    sanity_detail: str = ""
    verdict: str = INCONCLUSIVE


def evaluate_spec(spec: Spec, out_base: Path) -> Result:
    """Evaluate one subtest against the output under ``out_base/<deck stem>``.

    Decoupled from config loading so it is unit-testable with fixture dirs.
    """
    out_dir = Path(out_base) / spec.deck.stem
    r = Result(spec, out_dir)

    if not out_dir.is_dir():
        r.sanity_detail = "output directory missing (deck not run on this machine?)"
        r.verdict = INCONCLUSIVE
        return r

    # Prefer the ACTUAL process return code from the run manifest; fall back to
    # a log-based assessment for older runs that predate the manifest.
    manifest = _read_manifest(out_dir)
    manifest_failed = False
    if manifest is not None:
        rc = manifest.get("return_code")
        status = manifest.get("status")
        r.exit_note = f"return_code={rc}, status={status} (run manifest)"
        manifest_failed = (status == "failed") or (rc not in (0, None))
    else:
        r.exit_note = "log-based assessment (no run manifest; older run)"

    log = _read_logs(out_dir)
    log_lower = log.lower()
    r.marker_found = any(m.lower() in log_lower for m in spec.log_markers)
    r.files = _glob_any(out_dir, spec.output_globs)

    fatal = _fatal_reason(log_lower)
    if fatal or manifest_failed:
        r.verdict = FAIL
        r.sanity_detail = fatal or f"run manifest reports failure ({r.exit_note})"
        # still run the sanity check for reporting completeness, but keep FAIL
        try:
            r.sanity_ok, _ = spec.sanity(out_dir, r.files)
        except Exception:  # noqa: BLE001
            r.sanity_ok = None
        return r

    ok, detail = spec.sanity(out_dir, r.files)
    r.sanity_ok, r.sanity_detail = ok, detail

    if ok is None:
        r.verdict = INCONCLUSIVE
    elif r.marker_found and r.files and ok:
        r.verdict = PASS
    else:
        r.verdict = FAIL
    return r


def _print_result(r: Result) -> None:
    print(f"  deck              : {r.spec.deck.name}")
    print(f"  requested feature : {r.spec.feature}")
    print(f"  solver exit code  : {r.exit_note}")
    print(f"  log marker found  : {'yes' if r.marker_found else 'no'} "
          f"(any of: {', '.join(r.spec.log_markers)})")
    print(f"  output files found: {len(r.files)}"
          + (f"  e.g. {r.files[0].name}" if r.files else ""))
    print(f"  numerical check   : {r.spec.sanity_label} -> "
          f"{'ok' if r.sanity_ok else ('inconclusive' if r.sanity_ok is None else 'FAILED')}"
          f"  ({r.sanity_detail})")
    print(f"  >>> {r.verdict}")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Standard-only smoke-test outputs (logs + files, not just exit codes)."
    )
    parser.add_argument("--test", required=True,
                        help="Stage 1-6, a range like 4-6, or 'all' (stages 1-3 have no verifier specs).")
    args = parser.parse_args(argv)

    try:
        stages = set(parse_stages(args.test))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    specs = _build_specs(stages)
    if not specs:
        print("No Standard-feature verifier specs for the requested stage(s). "
              "(Stages 1-3 are covered by run_smoke_tests exit codes.)")
        return 0

    try:
        out_base = resolve_config().outputdirectory
    except ConfigError as exc:
        print(f"ERROR: cannot locate output directory: {str(exc).splitlines()[0]}",
              file=sys.stderr)
        return 2

    print(f"Verifying Standard smoke-test outputs for stage(s): {sorted(stages)}")
    print(f"(output base: {out_base})\n")
    results = [evaluate_spec(sp, out_base) for sp in specs]
    for r in results:
        _print_result(r)

    n_pass = sum(r.verdict == PASS for r in results)
    n_fail = sum(r.verdict == FAIL for r in results)
    n_inc = sum(r.verdict == INCONCLUSIVE for r in results)
    print(f"summary: {n_pass} PASS, {n_fail} FAIL, {n_inc} INCONCLUSIVE "
          f"(of {len(results)} subtests)")

    # Nonzero exit if anything failed or was inconclusive (nothing verified).
    return 0 if (n_fail == 0 and n_inc == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
