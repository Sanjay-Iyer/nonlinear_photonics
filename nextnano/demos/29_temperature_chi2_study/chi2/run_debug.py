"""Read-only nextnano run discovery and small, redacted diagnostic bundles."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ("cb1", "cb2", "hh1", "hh2", "lh1", "lh2", "so1", "so2")
RELEVANT = re.compile(r"state|spinor|wave|envelope|composition|k_|k\d|momentum|dipole|dispersion", re.I)
FRAME = re.compile(r"(?:^|[_-])k[_-]?(\d{1,6})(?:$|[_\-.])", re.I)
STATE_COMPONENT = re.compile(r"envelopes?_(?:k\d{5}_)?(\d{4})_(cb[12]|hh[12]|lh[12]|so[12])\.dat$", re.I)
SENSITIVE_LINE = re.compile(r"(?:license\s*(?:key|content)|password|secret|credential|access[_ -]?token)", re.I)
MAX_LOG_BYTES = 1_500_000
MAX_TREE_FILES = 60_000


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def elapsed_hms(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}_{os.getpid()}"


def git_state() -> dict:
    def git(*args: str) -> str:
        done = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                              text=True, timeout=10, check=False)
        return done.stdout.strip() if done.returncode == 0 else "unavailable"
    changed = git("status", "--porcelain", "--untracked-files=no")
    return {"branch": git("branch", "--show-current"), "commit": git("rev-parse", "HEAD"),
            "dirty_before_run": changed != "" and changed != "unavailable",
            "git_status_available": changed != "unavailable"}


def _frame_id(path: Path, root: Path) -> str | None:
    for part in reversed(path.relative_to(root).parts):
        match = FRAME.search(part)
        if match:
            return f"k{int(match.group(1)):05d}"
    return None


def _complex_columns(path: Path) -> bool:
    """Confirm the exported envelope has position, real and imaginary columns."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for _, line in zip(range(12), handle):
                bits = line.split()
                if len(bits) >= 3:
                    try:
                        [float(value.replace("D", "E")) for value in bits[:3]]
                        return True
                    except ValueError:
                        continue
    except OSError:
        pass
    return False


def _dispersion_summary(files: list[Path]) -> dict:
    choices = [p for p in files if p.name == "dispersion_Gamma_to_y.dat"]
    result = {"candidate_files": [str(p) for p in choices], "points": None,
              "k_min_per_nm": None, "k_max_per_nm": None}
    if len(choices) != 1:
        return result
    values = []
    try:
        with choices[0].open("r", encoding="utf-8", errors="replace") as handle:
            next(handle, None)
            for line in handle:
                bits = line.split()
                if bits:
                    values.append(float(bits[0].replace("D", "E")))
    except (OSError, ValueError):
        result["parse_error"] = "Could not read radial k column"
        return result
    if values:
        result.update(points=len(values), k_min_per_nm=min(values), k_max_per_nm=max(values))
    return result


def scan_output(run_root: Path, expected_frames: int | None = None,
                expected_states: int = 14, quick: bool = False) -> dict:
    """Inventory a single run root without reading or changing scientific arrays."""
    root = Path(run_root).resolve()
    if not root.is_dir():
        raise ValueError(f"Run directory does not exist: {root}")
    files = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: str(p).lower())
    listed = files[:MAX_TREE_FILES]
    records = []
    latest_mtime = None
    for path in listed:
        try:
            stat = path.stat()
        except OSError:
            continue
        records.append({"relative_path": path.relative_to(root).as_posix(), "bytes": stat.st_size,
                        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds")})
        latest_mtime = max(latest_mtime or stat.st_mtime, stat.st_mtime)
    compositions = [p for p in files if "spinor_composition" in p.name.lower() and p.suffix.lower() == ".dat"]
    envelopes = [p for p in files if p.name.lower().startswith(("envelope_", "envelopes_")) and p.suffix.lower() == ".dat"]
    frames: dict[str, dict] = defaultdict(lambda: {"composition_files": [], "envelope_files": [],
                                               "components": set(), "state_components": defaultdict(set),
                                               "complex_files": 0})
    unassigned = []
    for path in compositions + envelopes:
        frame_id = _frame_id(path, root)
        if frame_id is None:
            unassigned.append(path.relative_to(root).as_posix())
            continue
        info = frames[frame_id]
        relative = path.relative_to(root).as_posix()
        if path in compositions:
            info["composition_files"].append(relative)
        else:
            info["envelope_files"].append(relative)
            match = STATE_COMPONENT.search(path.name)
            if match:
                component = match.group(2).lower()
                info["components"].add(component)
                info["state_components"][int(match.group(1))].add(component)
            if not quick and _complex_columns(path):
                info["complex_files"] += 1
    frame_rows = []
    missing_files = []
    for frame_id in sorted(frames):
        info = frames[frame_id]
        file_sets_complete = (len(info["composition_files"]) == 1 and
                    len(info["state_components"]) >= expected_states and
                    all(set(COMPONENTS) <= info["state_components"].get(state, set())
                        for state in range(1, expected_states + 1)))
        complete = file_sets_complete and info["complex_files"] >= expected_states * 8
        missing_components = {str(state): sorted(set(COMPONENTS) - info["state_components"].get(state, set()))
                              for state in range(1, expected_states + 1)
                              if set(COMPONENTS) - info["state_components"].get(state, set())}
        if not info["composition_files"]:
            missing_files.append(f"{frame_id}/spinor_composition_CbHhLhSo.dat")
        for state, components in missing_components.items():
            missing_files.extend(f"{frame_id}/envelope_{int(state):04d}_{component}.dat"
                                 for component in components)
        frame_rows.append({"id": frame_id, "composition_files": info["composition_files"],
                           "envelope_count": len(info["envelope_files"]),
                           "components_present": sorted(info["components"]),
                           "all_eight_components": set(COMPONENTS) <= info["components"],
                           "complex_envelope_files": info["complex_files"],
                           "missing_components_by_state": missing_components,
                           "component_file_sets_complete": file_sets_complete,
                           "state_component_complete": complete})
    duplicate_frames = [row["id"] for row in frame_rows if len(row["composition_files"]) > 1]
    parser_recognized = [row["id"] for row in frame_rows if any(
        Path(path).name == f"spinor_composition_{row['id']}_CbHhLhSo.dat"
        for path in row["composition_files"])]
    relevant = [p.relative_to(root).as_posix() for p in files if RELEVANT.search(p.name)]
    recognized = {path for row in frame_rows for path in row["composition_files"]}
    recognized.update(path.relative_to(root).as_posix() for path in envelopes if _frame_id(path, root))
    recognized.update(path.relative_to(root).as_posix() for path in files if path.name in
                      ("dispersion_Gamma_to_y.dat", "kVectors_Gamma_to_y.dat"))
    ignored_relevant = [path for path in relevant if path not in recognized]
    candidate_roots = sorted({p.parent.relative_to(root).as_posix() for p in files
                              if p.name == "job_done.txt" or p.name == "dispersion_Gamma_to_y.dat"})
    unexpected = [path for path in relevant if "spinor_composition" in path.lower() and
                  not re.search(r"spinor_composition_k\d{5}_CbHhLhSo\.dat$", path, re.I)]
    report = {
        "run_root": str(root), "scanned_utc": now_utc(), "total_files": len(files),
        "tree_truncated": len(files) > MAX_TREE_FILES, "tree": records,
        "latest_file_mtime_utc": (datetime.fromtimestamp(latest_mtime, timezone.utc).isoformat(timespec="seconds")
                                  if latest_mtime else None),
        "dispersion": _dispersion_summary(files),
        "expected_finite_k_frames_nominal": expected_frames,
        "actual_finite_k_state_frames": len([row for row in frame_rows if row["composition_files"]]),
        "complete_state_frames": sum(row["state_component_complete"] for row in frame_rows),
        "component_file_sets_complete": sum(row["component_file_sets_complete"] for row in frame_rows),
        "frame_identifiers": [row["id"] for row in frame_rows],
        "k0_exists": any(row["id"] == "k00000" for row in frame_rows),
        "composition_files": len(compositions), "spinor_envelope_files": len(envelopes),
        "frames": frame_rows, "duplicate_frames": duplicate_frames,
        "missing_frames": ([f"k{i:05d}" for i in range(expected_frames)
                            if f"k{i:05d}" not in frames] if expected_frames is not None else []),
        "missing_file_examples": missing_files[:100],
        "missing_file_count_within_discovered_frames": len(missing_files),
        "discovered_k_values_per_nm": {},
        "k_value_note": "No reliable mapping from k-point directory IDs to k vectors was exported; dispersion vectors describe a separate grid.",
        "parser_recognized_frames": parser_recognized,
        "unassigned_state_files": unassigned[:100],
        "unassigned_state_files_total": len(unassigned),
        "relevant_files_ignored_by_parser": ignored_relevant[:150],
        "relevant_files_ignored_total": len(ignored_relevant),
        "unexpected_file_locations": unexpected[:100],
        "unexpected_file_locations_total": len(unexpected),
        "candidate_output_roots": candidate_roots,
    }
    return report


def _safe_text(path: Path, redactions: list[str], limit: int = MAX_LOG_BYTES) -> str:
    if not path.is_file():
        return "[file not present]\n"
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size <= limit:
            text = handle.read().decode("utf-8", errors="replace")
        else:
            half = limit // 2
            head = handle.read(half).decode("utf-8", errors="replace")
            handle.seek(max(0, size - half))
            tail = handle.read(half).decode("utf-8", errors="replace")
            text = head + f"\n[... {size - 2 * half} bytes omitted from debug ZIP ...]\n" + tail
    for secret in redactions:
        if secret:
            text = text.replace(secret, "<REDACTED>")
    text = "\n".join("<REDACTED SENSITIVE LINE>" if SENSITIVE_LINE.search(line) else line
                     for line in text.splitlines()) + "\n"
    return text


def _preview(path: Path, redactions: list[str]) -> str:
    if path.stat().st_size > 30_000_000:
        return "[preview omitted: large file]\n"
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        head = [line.rstrip("\r\n") for _, line in zip(range(20), handle)]
    with path.open("rb") as handle:
        handle.seek(max(0, path.stat().st_size - 16_384))
        tail = handle.read().decode("utf-8", errors="replace").splitlines()[-20:]
    return _safe_inline("HEAD (up to 20 lines)\n" + "\n".join(head) +
                        "\n\nTAIL (up to 20 lines)\n" + "\n".join(tail) + "\n", redactions)


def _safe_inline(value: str, redactions: list[str]) -> str:
    for secret in redactions:
        if secret:
            value = value.replace(secret, "<REDACTED>")
    return "\n".join("<REDACTED SENSITIVE LINE>" if SENSITIVE_LINE.search(line) else line
                     for line in value.splitlines()) + "\n"


def _solver_messages(paths: list[Path], redactions: list[str]) -> list[str]:
    lines = []
    for path in paths:
        if path.is_file():
            content = _safe_text(path, redactions, 200_000)
            lines.extend(line.strip() for line in content.splitlines() if line.strip())
    return lines


def _settings_from_deck(root: Path) -> dict:
    choices = sorted((root / "decks").glob("kp8.in")) if (root / "decks").is_dir() else []
    if not choices:
        return {}
    body = choices[0].read_text(encoding="utf-8", errors="replace")
    values = {}
    for group in ("k_integration", "output_states"):
        match = re.search(r"\b" + group + r"\s*\{([^{}]*)\}", body, re.S)
        if match:
            values[group] = dict(re.findall(r"\b([A-Za-z_]+)\s*=\s*([^\s{}]+)", match.group(1)))
        elif group == "k_integration" and "k_integration_disabled" in body:
            values[group] = "disabled"
    return values


def collect_debug(run_root: Path, log_dir: Path, temperature: int,
                  expected_frames: int | None = None, run_id: str | None = None,
                  provenance: dict | None = None, redactions: list[str] | None = None) -> dict:
    """Write reports and a compact ZIP outside the solver directory."""
    root = Path(run_root).resolve()
    destination = Path(log_dir).resolve()
    if destination == root or root in destination.parents:
        raise ValueError("Debug reports must be written outside the scientific run directory")
    destination.mkdir(parents=True, exist_ok=True)
    run_id = run_id or new_run_id("diagnose")
    redactions = redactions or []
    report = scan_output(root, expected_frames)
    safe_report = {key: value for key, value in report.items() if key != "tree"}
    inventory = "relative_path\tbytes\tmodified_utc\n" + "\n".join(
        f"{row['relative_path']}\t{row['bytes']}\t{row['modified_utc']}" for row in report["tree"]) + "\n"
    (destination / "output_tree.txt").write_text(inventory, encoding="utf-8")
    (destination / "finite_k_diagnostic.json").write_text(json.dumps(safe_report, indent=2) + "\n", encoding="utf-8")
    summary = [f"Demo 29 finite-k diagnostic: {temperature} K", f"Run ID: {run_id}",
               f"Dispersion points: {report['dispersion']['points']}",
               f"Dispersion k range (nm^-1): {report['dispersion']['k_min_per_nm']} to {report['dispersion']['k_max_per_nm']}",
               f"Expected frames (nominal): {expected_frames if expected_frames is not None else 'unknown'}",
               f"Composition frames: {report['actual_finite_k_state_frames']}",
               f"Complete complex 8-component frames: {report['complete_state_frames']}",
               f"Composition files: {report['composition_files']}",
               f"Envelope files: {report['spinor_envelope_files']}",
               f"Frame IDs: {', '.join(report['frame_identifiers'][:100])}",
               f"Parser-recognized IDs: {', '.join(report['parser_recognized_frames'][:100])}",
               f"Ignored relevant files: {report['relevant_files_ignored_total']}",
               f"Unexpected composition locations: {report['unexpected_file_locations_total']}",
               f"Candidate result roots: {', '.join(report['candidate_output_roots'])}"]
    (destination / "finite_k_diagnostic.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    expected_jobs = sorted(metadata_job for metadata_job in
                           (json.loads((root / "run_metadata.json").read_text(encoding="utf-8")).get("jobs", {})
                            if (root / "run_metadata.json").is_file() else {}))
    found_job_roots = sorted({entry.split("/", 1)[0] for entry in report["candidate_output_roots"]})
    path_lines = [f"Expected run root: {root}", f"Run root exists: {root.is_dir()}",
                  f"Expected job directories: {', '.join(expected_jobs) or 'unknown'}",
                  f"Result-bearing top-level directories: {', '.join(found_job_roots) or 'none'}",
                  f"Unexpected top-level result directories: {', '.join(sorted(set(found_job_roots) - set(expected_jobs))) or 'none'}",
                  f"Candidate actual result roots: {', '.join(report['candidate_output_roots'])}",
                  f"Multiple result-bearing directories: {len(report['candidate_output_roots']) > 1}",
                  f"Nested Quantum/QuantumDispersions structures: {any('Quantum' in value for value in report['candidate_output_roots'])}"]
    if provenance:
        path_lines.extend(f"{key}: {value}" for key, value in provenance.get("path_checks", {}).items())
    (destination / "paths_report.txt").write_text(_safe_inline("\n".join(path_lines), redactions), encoding="utf-8")
    source_meta = root / "run_metadata.json"
    metadata = json.loads(source_meta.read_text(encoding="utf-8")) if source_meta.is_file() else {}
    log_sources = sorted({*root.glob("*.log"), *destination.rglob("*.log")})
    messages = _solver_messages(log_sources, redactions)
    version = next((line for line in messages if re.match(r"nextnano\+\+\s+\d", line, re.I)), None)
    deck_settings = _settings_from_deck(root)
    manifest = {"run_id": run_id, "temperature_K": temperature, "created_utc": now_utc(),
                "run_root": str(root), "git": (provenance or {}).get("git", git_state()),
                "python_version": sys.version, "operating_system": platform.platform(),
                "nextnano_version_build": version,
                "nextnano_executable_path": (provenance or {}).get("path_checks", {}).get("executable"),
                "nextnano_database_path": (provenance or {}).get("path_checks", {}).get("database"),
                "license_configured_and_exists": (provenance or {}).get("path_checks", {}).get("license_configured_and_exists"),
                "requested_kmax_pi_over_a": (provenance or {}).get("kmax_pi_over_a"),
                "requested_dispersion_points": (provenance or {}).get("dispersion_points"),
                "requested_k_integration": (provenance or {}).get("k_integration", deck_settings.get("k_integration")),
                "requested_output_states": (provenance or {}).get("output_states", deck_settings.get("output_states")),
                "environment_variable_status": {key: bool(os.environ.get(key)) for key in
                                                ("NEXTNANO_EXE", "NEXTNANO_DATABASE", "NEXTNANO_LICENSE")},
                "execution": (provenance or {}).get("execution", metadata.get("jobs", {})),
                "source_run_metadata_present": bool(metadata),
                "diagnostic": {"dispersion_points": report["dispersion"]["points"],
                               "composition_frames": report["actual_finite_k_state_frames"],
                               "complete_frames": report["complete_state_frames"]}}
    (destination / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    warnings = [line for line in messages if re.search(r"warning|error|fail|limited free", line, re.I)]
    (destination / "warnings_errors.txt").write_text("\n".join(warnings[-200:]) + "\n", encoding="utf-8")
    preview_candidates = []
    preview_files = [root / row["relative_path"] for row in report["tree"]
                     if row["relative_path"].lower().endswith(".dat")]
    preview_names = ("dispersion_Gamma_to_y.dat", "kVectors_Gamma_to_y.dat",
                     "energy_spectrum.dat", "energy_spectrum_k00000.dat",
                     "spinor_composition_CbHhLhSo.dat", "spinor_composition_k00000_CbHhLhSo.dat")
    for name in preview_names:
        matches = [p for p in preview_files if p.name == name]
        if matches:
            preview_candidates.append(matches[0])
    for prefix in ("envelope_", "dipole", "momentum"):
        matches = [p for p in preview_files if p.name.lower().startswith(prefix)]
        if matches:
            preview_candidates.append(matches[0])
    archive = destination / f"demo29_{temperature}K_debug_{run_id}.zip"
    if archive.exists():
        raise ValueError(f"Refusing to overwrite debug ZIP: {archive}")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in ("run_manifest.json", "paths_report.txt", "output_tree.txt",
                     "finite_k_diagnostic.json", "finite_k_diagnostic.txt", "warnings_errors.txt"):
            z.write(destination / name, name)
        for path in log_sources:
            label = (path.relative_to(destination).as_posix() if destination in path.parents
                     else f"solver_root/{path.name}")
            z.writestr(f"logs/{label}", _safe_text(path, redactions))
        for path in sorted((root / "decks").glob("*.in")) if (root / "decks").is_dir() else []:
            z.writestr(f"executed_decks/{path.name}", _safe_text(path, redactions, 500_000))
        if (ROOT / "config/study.json").is_file():
            z.write(ROOT / "config/study.json", "config/study.json")
        if source_meta.is_file():
            z.writestr("source_run_metadata.json", _safe_text(source_meta, redactions, 500_000))
        for index, path in enumerate(preview_candidates):
            relative = path.relative_to(root).as_posix().replace("/", "__")
            z.writestr(f"file_previews/{index:02d}_{relative}.txt", _preview(path, redactions))
    return {"run_id": run_id, "zip": str(archive), "zip_bytes": archive.stat().st_size,
            "diagnostic": safe_report, "warnings": warnings[-20:]}
