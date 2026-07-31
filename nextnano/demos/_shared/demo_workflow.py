"""Shared YAML-driven workflow for the first three nextnano++ learning demos.

The module is intentionally importable without nextnanopy or a licensed
nextnano++ installation.  Home-laptop runs validate configuration, render
inputs, write provenance, and exercise parser/selection code.  Solver imports
and path checks happen only when the machine YAML requests execution.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import logging
import math
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml

import plots as _plots
import schemas

# Demos 1-3 draw their own figures directly. matplotlib is shared with the
# Demo 4-10 helper so that a broken installation degrades identically: figures
# are skipped and recorded, never allowed to abort a licensed solver run. See
# the note at the top of plots.py.
plt = _plots.plt

NEXTNANO_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = NEXTNANO_ROOT.parent
MACHINE_CONFIG = NEXTNANO_ROOT / "config" / "machines" / "nextnano_machine.local.yaml"
MACHINE_EXAMPLE = (
    NEXTNANO_ROOT / "config" / "machines" / "nextnano_machine.example.yaml"
)
LEGACY_MACHINE_CONFIG = NEXTNANO_ROOT / "config" / "paths.local.yaml"
DEFAULT_RESULTS_ROOT = NEXTNANO_ROOT / "results" / "demo_runs"

TOP_LEVEL_KEYS = {
    "demo_id",
    "title",
    "template",
    "scientific",
    "numerical",
    "outputs",
    "validation",
    "sweeps",
}
MACHINE_KEYS = {
    "portable_root",
    "executable",
    "database",
    "license",
    "threads",
    "run_solver",
    "results_root",
}
COMMON_SCIENTIFIC_KEYS = {
    "well_width_nm",
    "left_barrier_width_nm",
    "right_barrier_width_nm",
    "barrier_width_nm",
    "aluminum_fraction",
    "temperature_K",
}
COMMON_NUMERICAL_KEYS = {
    "active_region_grid_spacing_nm",
    "exterior_grid_spacing_nm",
    "number_of_states",
    "quantum_region_padding_nm",
}
OUTPUT_KEYS = {
    "bandedges_glob",
    "energy_spectrum_glob",
    "probability_glob",
    "bandedge_columns",
    "energy_columns",
    "write_csv",
    "write_plots",
}
VALIDATION_KEYS = {
    "completion_markers",
    "fatal_markers",
    "minimum_well_probability",
    "maximum_boundary_probability",
    "normalization_tolerance",
    "absolute_energy_tolerance_meV",
    "relative_energy_tolerance",
}
SWEEP_KEYS = {
    "grid_spacing_nm",
    "domain_padding_nm",
    "quantum_region_padding_nm",
    "number_of_states",
}


class DemoError(RuntimeError):
    """Actionable workflow, configuration, solver, or parser failure."""


@dataclass(frozen=True)
class MachineConfig:
    """Resolved machine-specific execution settings."""

    portable_root: Path | None
    executable: Path | None
    database: Path | None
    license: Path | None
    threads: int
    run_solver: bool
    results_root: Path
    source_path: Path
    discovery_notes: tuple[str, ...]


@dataclass
class RunOutcome:
    """Result returned by one rendered input execution/analysis."""

    run_dir: Path
    solver_status: str
    return_code: int | None
    runtime_seconds: float
    observables: dict[str, Any]
    validation: dict[str, Any]
    warnings: list[str]
    failure_reason: str | None


def _strict_keys(mapping: Any, allowed: set[str], label: str) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        raise DemoError(f"{label} must be a YAML mapping.")
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise DemoError(f"{label} has unsupported key(s): {', '.join(unknown)}")
    return mapping


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DemoError(f"YAML file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise DemoError(f"{path} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise DemoError(f"{path} must contain a top-level mapping.")
    return data


def _finite_number(value: Any, label: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise DemoError(f"{label} must be a finite number, got {value!r}.") from exc
    if not math.isfinite(numeric):
        raise DemoError(f"{label} must be finite, got {value!r}.")
    return numeric


def load_demo_config(demo_dir: Path) -> dict[str, Any]:
    """Load and strictly validate a demo's scientific YAML.

    The rules live in :mod:`schemas`, one schema per demo.  Demos 1-3 share the
    schema transcribed from the key sets they were validated with, so their
    behaviour is unchanged; later demos declare their own richer vocabulary
    instead of widening everybody's.
    """

    path = demo_dir / "demo.yaml"
    raw = _read_yaml(path)
    demo_id = str(raw.get("demo_id", ""))
    expected = demo_dir.name.split("_", 1)[0]
    if not demo_id.startswith(expected):
        raise DemoError(
            f"{path}: demo_id {demo_id!r} does not match directory {demo_dir.name!r}."
        )
    try:
        schema = schemas.schema_for(demo_id)
        return schemas.validate_config(raw, schema, str(path))
    except schemas.SchemaError as exc:
        raise DemoError(str(exc)) from exc


def repository_root(start: Path | None = None) -> Path:
    """Find the enclosing Git repository without relying on the cwd."""

    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise DemoError(f"could not find repository root above {current}")


def _resolve_local_path(raw: Any, *, base: Path = REPOSITORY_ROOT) -> Path | None:
    if raw is None or str(raw).strip() in {"", "null", "None"}:
        return None
    expanded = os.path.expandvars(os.path.expanduser(str(raw).strip()))
    path = Path(expanded)
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def sibling_portable_root(repo_root: Path = REPOSITORY_ROOT) -> Path | None:
    """Return the conventional sibling ``../2026_07_03`` when it exists."""

    candidate = (repo_root / ".." / "2026_07_03").resolve()
    return candidate if candidate.is_dir() else None


def _discover_unique(root: Path, kind: str) -> Path:
    if kind == "executable":
        candidates = [
            p
            for p in root.rglob("*.exe")
            if "nextnano" in p.name.lower()
            and "nextnanomat" not in p.name.lower()
            and "license" not in p.name.lower()
        ]
    elif kind == "database":
        candidates = [
            p
            for pattern in ("*database*.xml", "*database*.nnp", "database*.txt")
            for p in root.rglob(pattern)
        ]
    elif kind == "license":
        candidates = list(root.rglob("*.lic"))
    else:  # pragma: no cover - internal guard
        raise ValueError(kind)
    candidates = sorted({p.resolve() for p in candidates if p.is_file()})
    if not candidates:
        raise DemoError(f"no plausible {kind} found beneath portable_root: {root}")
    if len(candidates) > 1:
        listed = "\n".join(f"  - {p}" for p in candidates)
        raise DemoError(
            f"multiple plausible {kind} files found beneath {root}; set an explicit "
            f"path in nextnano_machine.local.yaml:\n{listed}"
        )
    return candidates[0]


def load_machine_config(config_path: Path | None = None) -> MachineConfig:
    """Resolve execution settings with zero-config work/home laptop behavior.

    An explicit/new local demo config wins.  When it is absent, the runner
    reuses the repository's established ``paths.local.yaml`` or the active
    environment's nextnanopy configuration before trying sibling-portable
    discovery.  ``run_solver: auto`` executes only when a complete licensed
    setup is available; otherwise it performs the successful home dry-run.
    """

    requested = config_path or MACHINE_CONFIG
    source = requested if requested.is_file() else MACHINE_EXAMPLE
    data = _strict_keys(_read_yaml(source), MACHINE_KEYS, str(source))
    run_setting = data.get("run_solver", "auto")
    if isinstance(run_setting, str):
        run_setting = run_setting.strip().lower()
    if run_setting not in (True, False, "auto"):
        raise DemoError(f"{source}: run_solver must be true, false, or auto.")
    auto_mode = run_setting == "auto"
    run_solver = bool(run_setting) if not auto_mode else False

    notes: list[str] = []
    if source != requested:
        notes.append(
            f"local machine override not found; using tracked automatic defaults: {source}"
        )

    # Reuse the original repository-local nextnano configuration when present.
    # This is the most likely zero-setup route on a work laptop that already ran
    # the validated smoke tests.
    if config_path is None and source == MACHINE_EXAMPLE and LEGACY_MACHINE_CONFIG.is_file():
        legacy = _read_yaml(LEGACY_MACHINE_CONFIG)
        section = legacy.get("nextnano++")
        if not isinstance(section, dict):
            raise DemoError(
                f"{LEGACY_MACHINE_CONFIG} must contain a 'nextnano++:' mapping."
            )
        legacy_paths = {
            "executable": section.get("exe"),
            "database": section.get("database"),
            "license": section.get("license"),
        }
        if all(str(value or "").strip() for value in legacy_paths.values()):
            data.update(legacy_paths)
            data["threads"] = section.get("threads", data.get("threads", 4))
            source = LEGACY_MACHINE_CONFIG
            run_solver = True
            auto_mode = False
            notes.append(
                f"reusing established repository machine configuration: {source}"
            )

    # If there is no repository-local setup, reuse the active environment's
    # nextnanopy configuration without modifying or saving it.
    if config_path is None and source == MACHINE_EXAMPLE and auto_mode:
        try:
            import nextnanopy as nn

            options = nn.config.get_options("nextnano++")
            configured = {
                "executable": options.get("exe"),
                "database": options.get("database"),
                "license": options.get("license"),
            }
            configured_paths = {
                kind: _resolve_local_path(value)
                for kind, value in configured.items()
            }
            if all(path is not None and path.is_file() for path in configured_paths.values()):
                data.update(configured)
                data["threads"] = options.get("threads") or data.get("threads", 4)
                source = Path(nn.config.fullpath)
                run_solver = True
                auto_mode = False
                notes.append(
                    "reusing the active environment's existing nextnanopy "
                    f"configuration: {source}"
                )
        except Exception as exc:  # nextnanopy is optional for home dry-runs
            notes.append(f"nextnanopy configuration unavailable: {type(exc).__name__}")

    portable = _resolve_local_path(data.get("portable_root"))
    if portable is None:
        portable = sibling_portable_root()
        if portable:
            notes.append(f"portable_root discovered as repository sibling: {portable}")
    elif portable.is_dir():
        notes.append(f"portable_root resolved from YAML: {portable}")

    if auto_mode and portable is not None and portable.is_dir():
        run_solver = True
        notes.append("licensed execution enabled automatically from portable_root")

    try:
        threads = int(data.get("threads", 4))
    except (TypeError, ValueError) as exc:
        raise DemoError(f"{source}: threads must be an integer.") from exc
    if threads < 1:
        raise DemoError(f"{source}: threads must be >= 1.")

    resolved: dict[str, Path | None] = {}
    for kind in ("executable", "database", "license"):
        explicit = _resolve_local_path(data.get(kind))
        if explicit is not None:
            resolved[kind] = explicit
            selected = explicit.name if kind == "license" else str(explicit)
            notes.append(f"{kind} selected explicitly: {selected}")
        elif run_solver:
            if portable is None or not portable.is_dir():
                raise DemoError(
                    "solver execution is enabled but portable_root is missing. "
                    "Set portable_root or the three explicit machine paths."
                )
            resolved[kind] = _discover_unique(portable, kind)
            selected = (
                resolved[kind].name
                if kind == "license" and resolved[kind] is not None
                else str(resolved[kind])
            )
            notes.append(f"{kind} auto-discovered: {selected}")
        else:
            resolved[kind] = None

    if run_solver:
        for kind, path in resolved.items():
            if path is None or not path.is_file():
                raise DemoError(f"configured {kind} does not exist: {path}")
    results_root = _resolve_local_path(data.get("results_root")) or DEFAULT_RESULTS_ROOT
    return MachineConfig(
        portable_root=portable,
        executable=resolved["executable"],
        database=resolved["database"],
        license=resolved["license"],
        threads=threads,
        run_solver=run_solver,
        results_root=results_root,
        source_path=source,
        discovery_notes=tuple(notes),
    )


_PLACEHOLDER = re.compile(r"{{\s*([A-Za-z_]\w*)\s*}}")


def render_template(template_text: str, values: dict[str, Any]) -> str:
    """Strict deterministic ``{{name}}`` rendering for nextnano input decks."""

    referenced = set(_PLACEHOLDER.findall(template_text))
    missing = sorted(referenced - set(values))
    if missing:
        raise DemoError(f"undefined input-template variable(s): {', '.join(missing)}")

    def replacement(match: re.Match[str]) -> str:
        value = values[match.group(1)]
        if isinstance(value, bool):
            return "yes" if value else "no"
        return str(value)

    rendered = _PLACEHOLDER.sub(replacement, template_text)
    if _PLACEHOLDER.search(rendered):
        raise DemoError("unresolved template variable remains after rendering.")
    return rendered.replace("\r\n", "\n").replace("\r", "\n")


def make_run_id() -> str:
    """Create a sortable run ID with a collision-resistant suffix.

    Kept deliberately short. nextnano++ writes its own nested output tree
    (``raw_output/<deck>/bias_00000/Quantum/<region>/Gamma/...``) beneath each
    run directory, and Windows still refuses paths beyond 260 characters for
    ordinary file APIs, so every component of the prefix has to earn its length.
    """

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{uuid.uuid4().hex[:8]}"


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _atomic_json(path: Path, data: Any) -> None:
    _atomic_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_state() -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        return commit, dirty
    except (OSError, subprocess.SubprocessError):
        return None, None


def machine_summary(machine: MachineConfig) -> dict[str, Any]:
    """Return provenance without exposing the license path or contents."""

    return {
        "config_source": str(machine.source_path),
        "portable_root": str(machine.portable_root) if machine.portable_root else None,
        "executable": str(machine.executable) if machine.executable else None,
        "database": str(machine.database) if machine.database else None,
        "license_filename": machine.license.name if machine.license else None,
        "threads": machine.threads,
        "run_solver": machine.run_solver,
        "results_root": str(machine.results_root),
        "discovery_notes": list(machine.discovery_notes),
    }


def _parameters(cfg: dict[str, Any]) -> dict[str, Any]:
    scientific = dict(cfg["scientific"])
    numerical = dict(cfg["numerical"])
    if "barrier_width_nm" in scientific:
        scientific.setdefault("left_barrier_width_nm", scientific["barrier_width_nm"])
        scientific.setdefault("right_barrier_width_nm", scientific["barrier_width_nm"])
    left = float(scientific["left_barrier_width_nm"])
    well = float(scientific["well_width_nm"])
    right = float(scientific["right_barrier_width_nm"])
    values = {**scientific, **numerical}
    values.update(
        {
            "well_start_nm": f"{left:.12g}",
            "well_end_nm": f"{left + well:.12g}",
            "domain_end_nm": f"{left + well + right:.12g}",
            "quantum_start_nm": f"{max(0.0, left - float(numerical.get('quantum_region_padding_nm', left))):.12g}",
            "quantum_end_nm": f"{min(left + well + right, left + well + float(numerical.get('quantum_region_padding_nm', right))):.12g}",
        }
    )
    return values


def _create_layout(run_dir: Path) -> dict[str, Path]:
    paths = {
        "generated": run_dir / "generated_input",
        "raw": run_dir / "raw_output",
        "extracted": run_dir / "extracted",
        "plots": run_dir / "plots",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=False)
    return paths


def _logger(run_dir: Path) -> logging.Logger:
    logger = logging.getLogger(f"nextnano_demo.{run_dir.name}.{uuid.uuid4().hex}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s")
    formatter.converter = time.gmtime
    file_handler = logging.FileHandler(run_dir / "console.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def _execute_solver(machine: MachineConfig, deck: Path, raw_output: Path) -> tuple[int | None, float]:
    import nextnanopy as nn

    kwargs = {
        "exe": str(machine.executable),
        "database": str(machine.database),
        "license": str(machine.license),
        "outputdirectory": str(raw_output),
        "threads": machine.threads,
    }
    start = time.perf_counter()
    # nextnano++ prints licensed-user/key fields in its live banner. Suppress
    # the vendor stream here; our own logger still reports start, completion,
    # failures, runtime, validation, and artifact locations.
    info = nn.InputFile(str(deck)).execute(show_log=False, **kwargs)
    elapsed = time.perf_counter() - start
    process = info.get("process") if isinstance(info, dict) else None
    code = process.poll() if process is not None else None
    if code is None and process is not None:
        code = process.wait(timeout=10)
    return (int(code) if code is not None else None), elapsed


_SENSITIVE_SOLVER_LOG_LINES = (
    re.compile(r"(?im)^(\s*Licensed\s+to\s*:).*$"),
    re.compile(r"(?im)^(\s*License\s+key\s*:).*$"),
)


def _sanitize_solver_logs(raw_output: Path) -> int:
    """Redact licensed-user/key fields from retained nextnano++ text logs."""

    redacted_files = 0
    for path in sorted(raw_output.rglob("*.log")):
        text = path.read_text(encoding="utf-8", errors="replace")
        sanitized = text
        for pattern in _SENSITIVE_SOLVER_LOG_LINES:
            sanitized = pattern.sub(r"\1 <redacted>", sanitized)
        if sanitized != text:
            # Solver output paths can approach Windows' legacy MAX_PATH. The
            # general atomic writer's UUID suffix is intentionally long, so use
            # one short sibling name here and atomically replace the log.
            temporary = path.with_name("~redact.tmp")
            temporary.write_text(sanitized, encoding="utf-8", newline="\n")
            os.replace(temporary, path)
            redacted_files += 1
    return redacted_files


def _numeric_rows(path: Path) -> np.ndarray:
    rows: list[list[float]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith(("#", "%", "!")):
            continue
        fields = re.split(r"[\s,;]+", stripped)
        try:
            values = [float(field) for field in fields if field]
        except ValueError:
            continue
        if values:
            rows.append(values)
    if not rows:
        raise DemoError(f"no numeric rows found in output file: {path}")
    width = max(map(len, rows))
    rows = [row for row in rows if len(row) == width]
    data = np.asarray(rows, dtype=float)
    if data.ndim != 2 or not np.isfinite(data).all():
        raise DemoError(f"non-finite or malformed numeric data in: {path}")
    return data


def parse_numeric_table(path: Path, columns: dict[str, int]) -> dict[str, np.ndarray]:
    """Parse a nextnano-style comment-headed numeric table by explicit indices."""

    data = _numeric_rows(path)
    parsed: dict[str, np.ndarray] = {}
    for name, raw_index in columns.items():
        index = int(raw_index)
        if index < 0 or index >= data.shape[1]:
            raise DemoError(
                f"{path} has {data.shape[1]} columns; requested {name} index {index}."
            )
        parsed[name] = data[:, index]
    return parsed


def _single_glob(root: Path, pattern: str, label: str) -> Path:
    matches = sorted(p for p in root.glob(pattern) if p.is_file())
    if not matches:
        raise DemoError(f"expected {label} output matching {pattern!r} beneath {root}")
    if len(matches) > 1:
        listed = "\n".join(f"  - {p}" for p in matches)
        raise DemoError(f"ambiguous {label} outputs matching {pattern!r}:\n{listed}")
    return matches[0]


def _solver_grid_points(raw_output: Path) -> int | None:
    """Read nextnano++'s authoritative unique 1D grid dimension from its log."""

    pattern = re.compile(r"Grid\s+dimension:\s*(\d+)\s*\*", re.IGNORECASE)
    for path in sorted(raw_output.rglob("*.log")):
        text = path.read_text(encoding="utf-8", errors="replace")
        match = pattern.search(text)
        if match:
            return int(match.group(1))
    return None


def _write_csv(path: Path, columns: dict[str, np.ndarray]) -> None:
    names = list(columns)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(names)
        writer.writerows(zip(*(columns[name] for name in names)))


def _analyse_bandedges(
    cfg: dict[str, Any], raw: Path, extracted: Path, plots: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    outputs = cfg["outputs"]
    source = _single_glob(
        raw, outputs.get("bandedges_glob", "**/*bandedge*.dat"), "band-edge"
    )
    columns = outputs.get(
        "bandedge_columns",
        {
            "position_nm": 0,
            "conduction_eV": 1,
            "heavy_hole_eV": 2,
            "light_hole_eV": 3,
            "split_off_eV": 4,
        },
    )
    data = parse_numeric_table(source, columns)
    x = data["position_nm"]
    params = _parameters(cfg)
    well_start = float(params["well_start_nm"])
    well_end = float(params["well_end_nm"])
    monotonic = bool(np.all(np.diff(x) > 0))
    inside = (x >= well_start) & (x <= well_end)
    outside = ~inside
    if not inside.any() or not outside.any():
        raise DemoError("band-edge grid does not sample both well and barriers.")
    ec = data["conduction_eV"]
    well_ec = float(np.median(ec[inside]))
    barrier_ec = float(np.median(ec[outside]))
    _write_csv(extracted / "band_edges.csv", data)
    composition = {
        "position_nm": x,
        "aluminum_fraction": np.where(
            inside, 0.0, float(cfg["scientific"]["aluminum_fraction"])
        ),
    }
    _write_csv(extracted / "composition_profile.csv", composition)

    if cfg["outputs"].get("write_plots", True) and _plots.plotting_available():
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for name, values in data.items():
            if name != "position_nm":
                ax.plot(x, values, label=name.replace("_eV", ""))
        ax.axvspan(well_start, well_end, color="0.9", zorder=-1, label="GaAs well")
        ax.set(xlabel="Position (nm)", ylabel="Band edge (eV)", title=cfg["title"])
        ax.legend(fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig(plots / "band_edges.png", dpi=180)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8, 3.6))
        ax.step(
            composition["position_nm"],
            composition["aluminum_fraction"],
            where="mid",
        )
        ax.set(
            xlabel="Position (nm)",
            ylabel="Al mole fraction x",
            ylim=(-0.02, max(0.05, float(cfg["scientific"]["aluminum_fraction"]) * 1.1)),
            title="Al composition profile",
        )
        fig.tight_layout()
        fig.savefig(plots / "composition_profile.png", dpi=180)
        plt.close(fig)

    observables = {
        "bandedges_source": str(source),
        "grid_points": _solver_grid_points(raw) or int(x.size),
        "bandedge_output_rows": int(x.size),
        "well_start_nm": well_start,
        "well_end_nm": well_end,
        "well_conduction_edge_eV": well_ec,
        "barrier_conduction_edge_eV": barrier_ec,
        "conduction_offset_meV": 1000.0 * (barrier_ec - well_ec),
    }
    validation = {
        "position_monotonic": monotonic,
        "finite_values": True,
        "interfaces_sampled": bool(
            np.min(np.abs(x - well_start)) <= np.max(np.diff(x))
            and np.min(np.abs(x - well_end)) <= np.max(np.diff(x))
        ),
        "gaas_is_electron_well": barrier_ec > well_ec,
    }
    validation["passed"] = all(validation.values())
    return observables, validation


def _probability_files(root: Path, pattern: str) -> list[Path]:
    return sorted(p for p in root.glob(pattern) if p.is_file())


def _analyse_quantum(
    cfg: dict[str, Any], raw: Path, extracted: Path, plots: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    observables, validation = _analyse_bandedges(cfg, raw, extracted, plots)
    outputs = cfg["outputs"]
    spectrum_path = _single_glob(
        raw,
        outputs.get("energy_spectrum_glob", "**/energy_spectrum_k*.dat"),
        "electron energy-spectrum",
    )
    energy_columns = outputs.get("energy_columns", {"state_index": 0, "energy_eV": 1})
    spectrum = parse_numeric_table(spectrum_path, energy_columns)
    energies = np.asarray(spectrum["energy_eV"], dtype=float)
    energies = np.sort(np.unique(energies))
    if energies.size == 0:
        raise DemoError(f"no electron eigenenergies parsed from {spectrum_path}")

    params = _parameters(cfg)
    well_start = float(params["well_start_nm"])
    well_end = float(params["well_end_nm"])
    probability_paths = _probability_files(
        raw, outputs.get("probability_glob", "**/probabilities_k*.dat")
    )
    if not probability_paths:
        raise DemoError("no electron probability-density outputs were found.")

    probabilities: list[dict[str, Any]] = []
    probability_csv: dict[str, np.ndarray] = {}
    common_x: np.ndarray | None = None
    state_densities: list[tuple[Path, np.ndarray, np.ndarray]] = []
    if len(probability_paths) == 1:
        # nextnano++ 3.0.0 writes one table:
        # x[nm], Psi^2_1[nm^-1], ..., Psi^2_N[nm^-1].
        path = probability_paths[0]
        table = _numeric_rows(path)
        if table.shape[1] < 2:
            raise DemoError(f"probability file needs at least two columns: {path}")
        for column in range(1, min(table.shape[1], len(energies) + 1)):
            state_densities.append((path, table[:, 0], table[:, column]))
    else:
        # Compatibility with versions that write one probability file per
        # state; the last numeric column is the density in those files.
        for path in probability_paths[: len(energies)]:
            table = _numeric_rows(path)
            if table.shape[1] < 2:
                raise DemoError(
                    f"probability file needs at least two columns: {path}"
                )
            state_densities.append((path, table[:, 0], table[:, -1]))

    if len(state_densities) < min(2, len(energies)):
        raise DemoError(
            f"parsed {len(state_densities)} probability state(s) for "
            f"{len(energies)} eigenenergies."
        )

    for index, (path, x, raw_density) in enumerate(state_densities, start=1):
        density = np.maximum(raw_density, 0.0)
        norm = float(np.trapezoid(density, x))
        if not math.isfinite(norm) or norm <= 0:
            raise DemoError(f"invalid probability normalization in {path}: {norm}")
        normalized = density / norm
        inside = (x >= well_start) & (x <= well_end)
        well_probability = float(np.trapezoid(normalized[inside], x[inside]))
        span = float(x[-1] - x[0])
        left_boundary = x <= x[0] + 0.05 * span
        right_boundary = x >= x[-1] - 0.05 * span
        boundary_probability = float(
            np.trapezoid(normalized[left_boundary], x[left_boundary])
            + np.trapezoid(normalized[right_boundary], x[right_boundary])
        )
        probabilities.append(
            {
                "state": index,
                "source": str(path),
                "source_column": index,
                "raw_integral": norm,
                "well_probability": well_probability,
                "barrier_probability": max(0.0, 1.0 - well_probability),
                "boundary_probability": boundary_probability,
            }
        )
        if common_x is None:
            common_x = x
            probability_csv["position_nm"] = x
        if np.array_equal(x, common_x):
            probability_csv[f"state_{index}"] = normalized

    if probability_csv:
        _write_csv(extracted / "probability_densities.csv", probability_csv)
    with (extracted / "eigenenergies.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["state", "energy_eV"])
        writer.writerows(enumerate(energies, start=1))

    if (
        outputs.get("write_plots", True)
        and probability_csv
        and _plots.plotting_available()
    ):
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for name, density in probability_csv.items():
            if name != "position_nm":
                ax.plot(common_x, density, label=name)
        ax.axvspan(well_start, well_end, color="0.9", zorder=-1)
        ax.set(
            xlabel="Position (nm)",
            ylabel="Normalized probability density (1/nm)",
            title="Electron probability densities",
        )
        ax.legend()
        fig.tight_layout()
        fig.savefig(plots / "probability_densities.png", dpi=180)
        plt.close(fig)

        band_data = parse_numeric_table(
            Path(observables["bandedges_source"]),
            outputs.get(
                "bandedge_columns",
                {"position_nm": 0, "conduction_eV": 1},
            ),
        )
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.plot(
            band_data["position_nm"],
            band_data["conduction_eV"],
            color="black",
            label="Γ conduction edge",
        )
        barrier_offset = (
            float(observables["barrier_conduction_edge_eV"])
            - float(observables["well_conduction_edge_eV"])
        )
        display_height = max(0.02, 0.15 * barrier_offset)
        for index, energy in enumerate(energies[: len(probabilities)], start=1):
            key = f"state_{index}"
            if key not in probability_csv:
                continue
            density = probability_csv[key]
            peak = float(np.max(density))
            displayed = energy + display_height * density / peak
            ax.plot(common_x, displayed, label=f"E{index} + scaled |ψ|²")
            ax.axhline(energy, color="0.7", linewidth=0.6)
        ax.set(
            xlabel="Position (nm)",
            ylabel="Energy (eV)",
            title="Band edge with probability-density display offsets",
        )
        ax.text(
            0.01,
            0.02,
            "Curves are scaled |ψ|² added to each eigenenergy for display; "
            "amplitude is not an energy.",
            transform=ax.transAxes,
            fontsize=7,
        )
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(plots / "band_edge_with_probability_offsets.png", dpi=180)
        plt.close(fig)

    barrier_edge = float(observables["barrier_conduction_edge_eV"])
    minimum_well = float(cfg["validation"].get("minimum_well_probability", 0.5))
    max_boundary = float(cfg["validation"].get("maximum_boundary_probability", 1e-4))
    normalization_tolerance = float(
        cfg["validation"].get("normalization_tolerance", 1e-3)
    )
    bound = [
        bool(
            energy < barrier_edge
            and i < len(probabilities)
            and probabilities[i]["well_probability"] >= minimum_well
        )
        for i, energy in enumerate(energies)
    ]
    validation.update(
        {
            "energies_finite_and_ordered": bool(
                np.isfinite(energies).all() and np.all(np.diff(energies) > 0)
            ),
            "at_least_one_bound_state": any(bound),
            "ground_state_well_probability": probabilities[0]["well_probability"]
            >= minimum_well,
            "ground_state_boundary_probability": probabilities[0][
                "boundary_probability"
            ]
            <= max_boundary,
            "probability_normalized": all(
                abs(item["raw_integral"] - 1.0) <= normalization_tolerance
                for item in probabilities
            ),
        }
    )
    validation["passed"] = all(
        value for key, value in validation.items() if key != "passed"
    )
    observables.update(
        {
            "energy_spectrum_source": str(spectrum_path),
            "electron_eigenenergies_eV": energies.tolist(),
            "E1_eV": float(energies[0]),
            "E2_eV": float(energies[1]) if len(energies) > 1 else None,
            "E2_minus_E1_meV": (
                float(1000.0 * (energies[1] - energies[0]))
                if len(energies) > 1
                else None
            ),
            "bound_state_flags": bound,
            "state_probabilities": probabilities,
            "well_probability": probabilities[0]["well_probability"],
            "boundary_probability": probabilities[0]["boundary_probability"],
        }
    )
    return observables, validation


def _log_checks(raw: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    # nextnano++ 3.0.0 writes its completion evidence to summary.log
    # ("Simulation completed.") and job_done.txt ("Calculation successfully
    # completed."); the word "DONE." only ever reaches the console, which is not
    # part of the preserved output tree. Both files are read here so a real
    # successful run is recognised as one.
    logs = sorted(raw.rglob("*.log")) + sorted(raw.rglob("job_*.txt"))
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in logs
    ).lower()
    fatal = [str(x).lower() for x in cfg["validation"].get("fatal_markers", [])]
    complete = [
        str(x).lower() for x in cfg["validation"].get("completion_markers", [])
    ]
    return {
        "log_files": [str(path) for path in logs],
        "no_fatal_marker": not any(marker in text for marker in fatal),
        "completion_marker_found": (
            any(marker in text for marker in complete) if complete else bool(logs)
        ),
    }


def _manifest_base(
    cfg: dict[str, Any],
    machine: MachineConfig,
    template: Path,
    generated: Path,
) -> dict[str, Any]:
    commit, dirty = _git_state()
    return {
        "schema": 1,
        "demo_id": cfg["demo_id"],
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_commit": commit,
        "git_dirty": dirty,
        "template_path": str(template),
        "generated_input_path": str(generated),
        "generated_input_sha256": _sha256(generated),
        "scientific_parameters": cfg["scientific"],
        "numerical_parameters": cfg["numerical"],
        "machine": machine_summary(machine),
    }


def run_case(
    demo_dir: Path,
    cfg: dict[str, Any],
    machine: MachineConfig,
    run_dir: Path,
) -> RunOutcome:
    """Render, optionally execute, parse, validate, and preserve one case."""

    layout = _create_layout(run_dir)
    logger = _logger(run_dir)
    template = demo_dir / str(cfg["template"])
    if not template.is_file():
        raise DemoError(f"input template not found: {template}")
    values = _parameters(cfg)
    rendered = render_template(template.read_text(encoding="utf-8"), values)
    # Convergence cases are deeply nested on Windows. A short input stem also
    # shortens nextnanopy's automatically-created raw-output subdirectory.
    deck_stem = "case" if cfg["demo_id"].startswith("03") else cfg["demo_id"]
    generated = layout["generated"] / f"{deck_stem}.in"
    _atomic_text(generated, rendered)
    _atomic_text(run_dir / "demo_resolved.yaml", yaml.safe_dump(cfg, sort_keys=True))
    _atomic_json(run_dir / "machine_summary.json", machine_summary(machine))
    manifest = _manifest_base(cfg, machine, template, generated)
    warnings: list[str] = []
    failure_reason: str | None = None
    observables: dict[str, Any] = {}
    validation: dict[str, Any] = {"input_generation": True}
    return_code: int | None = None
    runtime = 0.0

    if not machine.run_solver:
        status = "skipped_no_solver"
        warnings.append(
            "Input generation and validation succeeded. Solver execution was "
            "skipped because no complete licensed nextnano configuration or "
            "portable installation was available on this machine."
        )
        logger.info(warnings[-1])
    else:
        logger.info("Executing %s", generated)
        try:
            try:
                return_code, runtime = _execute_solver(
                    machine, generated, layout["raw"]
                )
            finally:
                redacted_files = _sanitize_solver_logs(layout["raw"])
                if redacted_files:
                    logger.info(
                        "Redacted licensed-user/key fields from %d solver log(s).",
                        redacted_files,
                    )
            if return_code not in (0, None):
                raise DemoError(f"nextnano++ returned nonzero exit code {return_code}")
            log_validation = _log_checks(layout["raw"], cfg)
            if cfg["demo_id"].startswith("01"):
                observables, parsed_validation = _analyse_bandedges(
                    cfg, layout["raw"], layout["extracted"], layout["plots"]
                )
            else:
                observables, parsed_validation = _analyse_quantum(
                    cfg, layout["raw"], layout["extracted"], layout["plots"]
                )
            validation.update(log_validation)
            validation.update(parsed_validation)
            validation["passed"] = all(
                bool(value)
                for key, value in validation.items()
                if key not in {"log_files", "passed"}
            )
            if not validation["passed"]:
                raise DemoError("one or more scientific/output validations failed")
            status = "completed"
            logger.info(
                "Solver and scientific validation completed successfully in %.3f s.",
                runtime,
            )
        except Exception as exc:  # preserve all artifacts and record the failure
            status = "failed"
            failure_reason = f"{type(exc).__name__}: {exc}"
            logger.exception("Run failed: %s", exc)

    manifest.update(
        {
            "solver_execution_status": status,
            "return_code": return_code,
            "runtime_seconds": runtime,
            "completion_status": status,
            "warnings": warnings,
            "observables": observables,
            "validation": validation,
            "failure_reason": failure_reason,
        }
    )
    _atomic_json(run_dir / "run_manifest.json", manifest)
    return RunOutcome(
        run_dir=run_dir,
        solver_status=status,
        return_code=return_code,
        runtime_seconds=runtime,
        observables=observables,
        validation=validation,
        warnings=warnings,
        failure_reason=failure_reason,
    )


def select_coarsest_converged(
    rows: Iterable[dict[str, Any]],
    *,
    reference_e1_eV: float,
    absolute_tolerance_meV: float,
    relative_tolerance: float,
    maximum_boundary_probability: float,
    minimum_well_probability: float,
) -> dict[str, Any] | None:
    """Select the coarsest successful grid satisfying all requested tolerances."""

    eligible: list[dict[str, Any]] = []
    for row in rows:
        energy = row.get("E1_eV")
        if not row.get("solver_success") or energy is None:
            continue
        absolute_meV = abs(float(energy) - reference_e1_eV) * 1000.0
        relative = absolute_meV / max(abs(reference_e1_eV) * 1000.0, 1e-15)
        if (
            absolute_meV <= absolute_tolerance_meV
            and relative <= relative_tolerance
            and float(row.get("boundary_probability", math.inf))
            <= maximum_boundary_probability
            and float(row.get("well_probability", -math.inf))
            >= minimum_well_probability
        ):
            copy = dict(row)
            copy["absolute_difference_meV"] = absolute_meV
            copy["relative_difference"] = relative
            eligible.append(copy)
    if not eligible:
        return None
    return max(eligible, key=lambda row: float(row["value"]))


def _case_cfg(base: dict[str, Any], sweep: str, value: Any) -> dict[str, Any]:
    copied = json.loads(json.dumps(base))
    if sweep == "grid_spacing_nm":
        copied["numerical"]["active_region_grid_spacing_nm"] = value
        copied["numerical"]["exterior_grid_spacing_nm"] = value
    elif sweep == "domain_padding_nm":
        copied["scientific"]["left_barrier_width_nm"] = value
        copied["scientific"]["right_barrier_width_nm"] = value
    elif sweep == "quantum_region_padding_nm":
        copied["numerical"]["quantum_region_padding_nm"] = value
    elif sweep == "number_of_states":
        copied["numerical"]["number_of_states"] = value
    else:  # pragma: no cover
        raise DemoError(f"unsupported sweep: {sweep}")
    return copied


def _summary_row(sweep: str, value: Any, outcome: RunOutcome) -> dict[str, Any]:
    obs = outcome.observables
    return {
        "sweep": sweep,
        "value": value,
        "solver_success": outcome.solver_status == "completed",
        "status": outcome.solver_status,
        "E1_eV": obs.get("E1_eV"),
        "E2_eV": obs.get("E2_eV"),
        "E2_minus_E1_meV": obs.get("E2_minus_E1_meV"),
        "well_probability": obs.get("well_probability"),
        "boundary_probability": obs.get("boundary_probability"),
        "grid_points": obs.get("grid_points"),
        "runtime_seconds": outcome.runtime_seconds,
        "convergence_status": outcome.validation.get("passed"),
        "difference_from_reference_meV": None,
        "E2_difference_from_reference_meV": None,
        "failure_reason": outcome.failure_reason,
        "run_dir": str(outcome.run_dir),
    }


def _write_convergence_artifacts(
    parent: Path, cfg: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    extracted = parent / "extracted"
    plots = parent / "plots"
    extracted.mkdir(exist_ok=True)
    plots.mkdir(exist_ok=True)
    tolerances = cfg["validation"]

    for sweep in SWEEP_KEYS:
        successful = [
            row for row in rows if row["sweep"] == sweep and row["solver_success"]
        ]
        if not successful:
            continue
        if sweep == "grid_spacing_nm":
            reference = min(successful, key=lambda row: float(row["value"]))
        else:
            reference = max(successful, key=lambda row: float(row["value"]))
        reference_e1 = float(reference["E1_eV"])
        reference_e2 = (
            float(reference["E2_eV"]) if reference["E2_eV"] is not None else None
        )
        for row in successful:
            e1_difference = abs(float(row["E1_eV"]) - reference_e1) * 1000.0
            row["difference_from_reference_meV"] = e1_difference
            e2_difference = None
            if reference_e2 is not None and row["E2_eV"] is not None:
                e2_difference = abs(float(row["E2_eV"]) - reference_e2) * 1000.0
            row["E2_difference_from_reference_meV"] = e2_difference
            energy_differences = [e1_difference]
            if e2_difference is not None:
                energy_differences.append(e2_difference)
            absolute_ok = max(energy_differences) <= float(
                tolerances["absolute_energy_tolerance_meV"]
            )
            relative_ok = all(
                difference
                / max(
                    abs(reference_e1 if index == 0 else reference_e2) * 1000.0,
                    1e-15,
                )
                <= float(tolerances["relative_energy_tolerance"])
                for index, difference in enumerate(energy_differences)
            )
            row["convergence_status"] = bool(
                absolute_ok
                and relative_ok
                and float(row["boundary_probability"])
                <= float(tolerances["maximum_boundary_probability"])
                and float(row["well_probability"])
                >= float(tolerances["minimum_well_probability"])
            )

    grid_rows = [
        row
        for row in rows
        if row["sweep"] == "grid_spacing_nm" and row["solver_success"]
    ]
    selected_grid = None
    if grid_rows:
        grid_reference = min(grid_rows, key=lambda row: float(row["value"]))
        selected_grid = select_coarsest_converged(
            grid_rows,
            reference_e1_eV=float(grid_reference["E1_eV"]),
            absolute_tolerance_meV=float(
                tolerances["absolute_energy_tolerance_meV"]
            ),
            relative_tolerance=float(tolerances["relative_energy_tolerance"]),
            maximum_boundary_probability=float(
                tolerances["maximum_boundary_probability"]
            ),
            minimum_well_probability=float(
                tolerances["minimum_well_probability"]
            ),
        )
        if selected_grid and not selected_grid.get("convergence_status"):
            selected_grid = None

    domain_rows = [
        row
        for row in rows
        if row["sweep"] == "domain_padding_nm"
        and row["solver_success"]
        and row.get("convergence_status")
    ]
    selected_domain = (
        min(domain_rows, key=lambda row: float(row["value"])) if domain_rows else None
    )
    recommendation = {
        "grid_spacing_nm": selected_grid,
        "domain_padding_nm": selected_domain,
        "principle": (
            "Choose the coarsest grid and smallest domain that satisfy E1/E2 "
            "and probability tolerances; the finest/largest cases are references."
        ),
    }

    lines = ["# Quantum-well convergence summary", ""]
    lines.append(
        "| sweep | value | status | E1 (eV) | E2 (eV) | ΔE (meV) | "
        "E1 diff (meV) | converged | well P | boundary P | runtime (s) |"
    )
    lines.append("|---|---:|---|---:|---:|---:|---:|---|---:|---:|---:|")
    for row in rows:
        fmt = lambda v: "—" if v is None else f"{float(v):.8g}"
        lines.append(
            f"| {row['sweep']} | {row['value']} | {row['status']} | "
            f"{fmt(row['E1_eV'])} | {fmt(row['E2_eV'])} | "
            f"{fmt(row['E2_minus_E1_meV'])} | "
            f"{fmt(row['difference_from_reference_meV'])} | "
            f"{row['convergence_status']} | {fmt(row['well_probability'])} | "
            f"{fmt(row['boundary_probability'])} | {fmt(row['runtime_seconds'])} |"
        )
    failed = [
        row
        for row in rows
        if not row["solver_success"] or row.get("convergence_status") is False
    ]
    lines.extend(["", "## Failed, skipped, missing, or suspicious runs", ""])
    lines.extend(
        [
            f"- {row['sweep']}={row['value']}: {row['status']} — "
            f"{row['failure_reason'] or ('no licensed execution' if not row['solver_success'] else 'outside one or more convergence tolerances')}"
            for row in failed
        ]
        or ["- None."]
    )
    lines.extend(["", "## Recommendation", ""])
    if selected_grid:
        lines.append(
            f"Use the coarsest tested grid satisfying every tolerance: "
            f"**{selected_grid['value']} nm**. The finest grid is the reference, "
            "not automatically the best production choice."
        )
    else:
        lines.append(
            "No production grid recommendation is available until licensed runs "
            "complete successfully and satisfy all configured tolerances."
        )
    if selected_domain:
        lines.append(
            f"Use the smallest tested outer barrier/domain padding satisfying "
            f"every tolerance: **{selected_domain['value']} nm per side**."
        )
    else:
        lines.append(
            "No production domain-padding recommendation is available until "
            "licensed runs complete successfully and satisfy all tolerances."
        )
    _atomic_json(extracted / "convergence_summary.json", rows)
    fieldnames = list(rows[0]) if rows else []
    with (extracted / "convergence_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    _atomic_text(extracted / "convergence_table.md", "\n".join(lines) + "\n")
    _atomic_json(extracted / "recommendation.json", recommendation)

    plot_specs = [
        ("grid_spacing_nm", "E1_eV", "E1 versus grid spacing", "E1 (eV)", "E1_vs_grid.png"),
        ("grid_spacing_nm", "E2_eV", "E2 versus grid spacing", "E2 (eV)", "E2_vs_grid.png"),
        ("grid_spacing_nm", "E2_minus_E1_meV", "E2 − E1 versus grid spacing", "ΔE (meV)", "spacing_vs_grid.png"),
        ("domain_padding_nm", "E1_eV", "E1 versus domain padding", "E1 (eV)", "energy_vs_domain.png"),
        ("grid_spacing_nm", "runtime_seconds", "Runtime versus grid spacing", "Runtime (s)", "runtime_vs_grid.png"),
    ]
    if not _plots.plotting_available():
        # Numerical artifacts above are already written; only the figures are
        # lost, and plots.status() records which and why.
        for _, _, _, _, filename in plot_specs:
            _plots._skip(plots / filename)
        return recommendation
    for sweep, observable, title, ylabel, filename in plot_specs:
        selected = [
            row
            for row in rows
            if row["sweep"] == sweep and row.get(observable) is not None
        ]
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        if selected:
            selected.sort(key=lambda row: float(row["value"]))
            ax.plot(
                [float(row["value"]) for row in selected],
                [float(row[observable]) for row in selected],
                "o-",
            )
        else:
            ax.text(
                0.5,
                0.5,
                "No licensed solver data yet",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
        ax.set(xlabel=sweep.replace("_", " "), ylabel=ylabel, title=title)
        fig.tight_layout()
        fig.savefig(plots / filename, dpi=180)
        plt.close(fig)
    return recommendation


def run_demo(demo_dir: Path, machine_path: Path | None = None) -> int:
    """Run one demo using only its YAML and the machine-local YAML."""

    demo_dir = demo_dir.resolve()
    cfg = load_demo_config(demo_dir)
    machine = load_machine_config(machine_path)
    parent = machine.results_root / cfg["demo_id"] / make_run_id()
    parent.mkdir(parents=True, exist_ok=False)

    if cfg["demo_id"].startswith("03"):
        _atomic_text(parent / "demo_resolved.yaml", yaml.safe_dump(cfg, sort_keys=True))
        _atomic_json(parent / "machine_summary.json", machine_summary(machine))
        rows: list[dict[str, Any]] = []
        for sweep, values in cfg.get("sweeps", {}).items():
            if not isinstance(values, list) or not values:
                raise DemoError(f"sweeps.{sweep} must be a non-empty list.")
            for index, value in enumerate(values, start=1):
                case_cfg = _case_cfg(cfg, sweep, value)
                safe = str(value).replace(".", "p")
                sweep_slug = {
                    "grid_spacing_nm": "grid",
                    "domain_padding_nm": "domain",
                    "quantum_region_padding_nm": "qregion",
                    "number_of_states": "states",
                }[sweep]
                case_dir = parent / "cases" / sweep_slug / f"{index:02d}_{safe}"
                outcome = run_case(demo_dir, case_cfg, machine, case_dir)
                rows.append(_summary_row(sweep, value, outcome))
        recommendation = _write_convergence_artifacts(parent, cfg, rows)
        commit, dirty = _git_state()
        manifest = {
            "schema": 1,
            "demo_id": cfg["demo_id"],
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "git_commit": commit,
            "git_dirty": dirty,
            "machine": machine_summary(machine),
            "run_count": len(rows),
            "solver_success_count": sum(bool(row["solver_success"]) for row in rows),
            "recommendation": recommendation,
            "status": (
                "completed"
                if machine.run_solver and all(row["solver_success"] for row in rows)
                else "dry_run_complete"
                if not machine.run_solver
                else "failed"
            ),
        }
        _atomic_json(parent / "run_manifest.json", manifest)
        _atomic_text(
            parent / "console.log",
            f"Demo 3 status: {manifest['status']}\n"
            f"Run count: {manifest['run_count']}\n"
            f"Solver successes: {manifest['solver_success_count']}\n",
        )
        print(f"Demo 3 artifacts: {parent}")
        return 0 if not machine.run_solver or manifest["status"] == "completed" else 1

    outcome = run_case(demo_dir, cfg, machine, parent)
    print(f"Demo artifacts: {parent}")
    if outcome.solver_status == "skipped_no_solver":
        return 0
    return 0 if outcome.solver_status == "completed" else 1


def cli(demo_dir: Path) -> int:
    """Small entry point used by each demo-local ``run.py``."""

    try:
        return run_demo(demo_dir)
    except DemoError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# Public surface reused by the Demo 4-10 modules.
#
# Demos 4-10 need the same provenance, logging, solver-invocation, and atomic
# write behaviour that Demos 1-3 were validated with. These aliases exist so
# those modules can share one implementation without reaching into names that
# look private, and so any future change to the mechanics happens in one place.
# ---------------------------------------------------------------------------

write_text_atomically = _atomic_text
write_json_atomically = _atomic_json
sha256_of = _sha256
git_state = _git_state
create_run_layout = _create_layout
run_logger = _logger
execute_solver = _execute_solver
sanitize_solver_logs = _sanitize_solver_logs
manifest_base = _manifest_base
write_csv = _write_csv
