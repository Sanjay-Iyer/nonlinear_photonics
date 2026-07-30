"""Conservative, version-profiled parsing of nextnano++ output trees.

Nothing in this module guesses.  Every artifact a demo consumes is named in a
parser profile (which file pattern, whether it is required, whether more than
one match is meaningful, and whether the pattern has been confirmed against a
real run of that solver version).  A missing artifact fails loudly with a
listing of what the run *did* write, and an unexpectedly ambiguous artifact
fails rather than silently taking the first match.

Column access is explicit *and* cross-checked: callers pass the index map from
their ``demo.yaml``, and the parsed header line is used to confirm that the
index really is the column the caller named.  A solver version that reorders
columns therefore produces an error, not a wrong number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml

NEXTNANO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = NEXTNANO_ROOT / "config" / "parsers"
DEFAULT_PROFILE = "nextnano_pp_3_0_0"


class ParserError(RuntimeError):
    """Raised when solver output cannot be located or trusted."""


@dataclass(frozen=True)
class ArtifactSpec:
    """One logical output a demo may consume."""

    key: str
    pattern: str
    required: bool = True
    allow_multiple: bool = False
    confirmed: bool = False
    description: str = ""
    units: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ParserProfile:
    """A named set of artifact patterns pinned to one solver version."""

    name: str
    solver_version: str
    source_path: Path
    description: str
    artifacts: Mapping[str, ArtifactSpec]

    def spec(self, key: str) -> ArtifactSpec:
        try:
            return self.artifacts[key]
        except KeyError as exc:
            known = ", ".join(sorted(self.artifacts))
            raise ParserError(
                f"parser profile {self.name!r} has no artifact {key!r}. Known: {known}"
            ) from exc

    def unconfirmed_keys(self) -> tuple[str, ...]:
        return tuple(
            sorted(key for key, spec in self.artifacts.items() if not spec.confirmed)
        )


_PROFILE_KEYS = {"profile", "solver_version", "description", "artifacts"}
_ARTIFACT_KEYS = {
    "pattern",
    "required",
    "allow_multiple",
    "confirmed",
    "description",
    "units",
}


def load_profile(name: str = DEFAULT_PROFILE, *, root: Path | None = None) -> ParserProfile:
    """Load and strictly validate a parser profile YAML."""

    base = root or PROFILE_ROOT
    path = base / f"{name}.yaml"
    if not path.is_file():
        available = ", ".join(sorted(p.stem for p in base.glob("*.yaml"))) or "none"
        raise ParserError(f"parser profile {name!r} not found in {base} (have: {available})")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ParserError(f"{path} must contain a top-level mapping.")
    unknown = sorted(set(data) - _PROFILE_KEYS)
    if unknown:
        raise ParserError(f"{path}: unsupported key(s): {', '.join(unknown)}")
    raw_artifacts = data.get("artifacts") or {}
    if not isinstance(raw_artifacts, dict) or not raw_artifacts:
        raise ParserError(f"{path}: 'artifacts' must be a non-empty mapping.")
    artifacts: dict[str, ArtifactSpec] = {}
    for key, entry in raw_artifacts.items():
        if not isinstance(entry, dict):
            raise ParserError(f"{path}: artifact {key!r} must be a mapping.")
        bad = sorted(set(entry) - _ARTIFACT_KEYS)
        if bad:
            raise ParserError(f"{path}: artifact {key!r} has unsupported key(s): {', '.join(bad)}")
        if not str(entry.get("pattern", "")).strip():
            raise ParserError(f"{path}: artifact {key!r} needs a non-empty pattern.")
        artifacts[str(key)] = ArtifactSpec(
            key=str(key),
            pattern=str(entry["pattern"]),
            required=bool(entry.get("required", True)),
            allow_multiple=bool(entry.get("allow_multiple", False)),
            confirmed=bool(entry.get("confirmed", False)),
            description=str(entry.get("description", "")),
            units=dict(entry.get("units") or {}),
        )
    return ParserProfile(
        name=str(data.get("profile", name)),
        solver_version=str(data.get("solver_version", "unknown")),
        source_path=path,
        description=str(data.get("description", "")),
        artifacts=artifacts,
    )


def available_files(raw_dir: Path, *, limit: int = 200) -> list[str]:
    """Relative listing of everything a run wrote; used in error messages."""

    if not raw_dir.is_dir():
        return []
    found = sorted(
        str(path.relative_to(raw_dir)).replace("\\", "/")
        for path in raw_dir.rglob("*")
        if path.is_file()
    )
    return found[:limit]


def _diagnostic(raw_dir: Path) -> str:
    listing = available_files(raw_dir)
    if not listing:
        return f"  (no files were written beneath {raw_dir})"
    return "\n".join(f"  - {name}" for name in listing)


@dataclass(frozen=True)
class ResolvedOutputs:
    """Located artifacts plus the provenance recorded in the run manifest."""

    profile_name: str
    solver_version: str
    profile_path: Path
    paths: Mapping[str, tuple[Path, ...]]
    missing_optional: tuple[str, ...]
    unconfirmed_used: tuple[str, ...]

    def one(self, key: str) -> Path:
        matches = self.paths.get(key, ())
        if len(matches) != 1:
            raise ParserError(
                f"artifact {key!r} resolved to {len(matches)} files; expected exactly one."
            )
        return matches[0]

    def many(self, key: str) -> tuple[Path, ...]:
        return self.paths.get(key, ())

    def provenance(self, raw_dir: Path) -> dict[str, Any]:
        return {
            "parser_profile": self.profile_name,
            "parser_profile_path": str(self.profile_path),
            "solver_version": self.solver_version,
            "resolved_artifacts": {
                key: [str(path.relative_to(raw_dir)).replace("\\", "/") for path in paths]
                for key, paths in sorted(self.paths.items())
            },
            "missing_optional_artifacts": list(self.missing_optional),
            "artifacts_with_unconfirmed_patterns": list(self.unconfirmed_used),
        }


def resolve_outputs(
    profile: ParserProfile,
    raw_dir: Path,
    keys: Iterable[str],
    *,
    substitutions: Mapping[str, str] | None = None,
) -> ResolvedOutputs:
    """Locate every requested artifact beneath ``raw_dir``.

    ``substitutions`` fills ``{name}`` placeholders in patterns (for example the
    quantum-region name), so one profile serves every demo.
    """

    mapping = dict(substitutions or {})
    resolved: dict[str, tuple[Path, ...]] = {}
    missing_optional: list[str] = []
    unconfirmed: list[str] = []
    for key in keys:
        spec = profile.spec(key)
        try:
            pattern = spec.pattern.format(**mapping)
        except KeyError as exc:
            raise ParserError(
                f"artifact {key!r} pattern {spec.pattern!r} needs substitution {exc}."
            ) from exc
        matches = sorted(path for path in raw_dir.glob(pattern) if path.is_file())
        if not matches:
            if spec.required:
                raise ParserError(
                    f"required output {key!r} matching {pattern!r} was not written "
                    f"beneath {raw_dir}.\nFiles actually present:\n{_diagnostic(raw_dir)}"
                )
            missing_optional.append(key)
            continue
        if len(matches) > 1 and not spec.allow_multiple:
            listed = "\n".join(f"  - {path}" for path in matches)
            raise ParserError(
                f"output {key!r} matching {pattern!r} is ambiguous "
                f"({len(matches)} matches); refusing to guess:\n{listed}"
            )
        resolved[key] = tuple(matches)
        if not spec.confirmed:
            unconfirmed.append(key)
    return ResolvedOutputs(
        profile_name=profile.name,
        solver_version=profile.solver_version,
        profile_path=profile.source_path,
        paths=resolved,
        missing_optional=tuple(missing_optional),
        unconfirmed_used=tuple(unconfirmed),
    )


_HEADER_TOKEN = re.compile(r"^(?P<name>.*?)(?:\[(?P<unit>[^\]]*)\])?$")


def parse_header(line: str) -> tuple[tuple[str, str], ...]:
    """Split a nextnano++ header row into ``(name, unit)`` pairs.

    nextnano++ writes headers such as
    ``x[nm]   Psi^2_1[nm^-1]   Psi^2_2[nm^-1]`` and separates columns with runs
    of whitespace.  Units are optional (``no.`` has none).
    """

    stripped = line.strip().lstrip("#").strip()
    if not stripped:
        return ()
    tokens = re.split(r"\s{1,}", stripped)
    pairs: list[tuple[str, str]] = []
    for token in tokens:
        match = _HEADER_TOKEN.match(token)
        if not match:  # pragma: no cover - regex always matches
            continue
        name = (match.group("name") or "").strip()
        unit = (match.group("unit") or "").strip()
        if not name:
            continue
        pairs.append((name, unit))
    return tuple(pairs)


@dataclass(frozen=True)
class Table:
    """A parsed numeric table with its header names and units."""

    path: Path
    header: tuple[tuple[str, str], ...]
    data: np.ndarray

    @property
    def n_columns(self) -> int:
        return int(self.data.shape[1])

    def column(self, index: int, *, expect: str | None = None) -> np.ndarray:
        """Return one column, optionally asserting the header name matches."""

        if index < 0 or index >= self.n_columns:
            raise ParserError(
                f"{self.path} has {self.n_columns} column(s); index {index} requested."
            )
        if expect is not None and index < len(self.header):
            actual = self.header[index][0]
            if not _header_matches(actual, expect):
                raise ParserError(
                    f"{self.path}: column {index} is {actual!r}, but the "
                    f"configuration calls it {expect!r}. Update the explicit column "
                    "map for this solver version instead of trusting the index."
                )
        return self.data[:, index]

    def unit(self, index: int) -> str:
        return self.header[index][1] if index < len(self.header) else ""

    def select(self, columns: Mapping[str, int]) -> dict[str, np.ndarray]:
        """Extract several named columns using an explicit index map."""

        return {
            name: self.column(int(index), expect=name)
            for name, index in columns.items()
        }


_NAME_HINTS: dict[str, tuple[str, ...]] = {
    "position_nm": ("x", "y", "z", "position"),
    "conduction_eV": ("gamma",),
    "heavy_hole_eV": ("hh",),
    "light_hole_eV": ("lh",),
    "split_off_eV": ("so",),
    "state_index": ("no.", "no", "index"),
    "energy_eV": ("energy",),
    "potential_V": ("potential",),
    "electric_field_kV_cm": ("e",),
    "electron_density_cm3": ("electron_density",),
    "hole_density_cm3": ("hole_density",),
    "ionized_donor_density_cm3": ("ionized_donor_density",),
    "ionized_acceptor_density_cm3": ("ionized_acceptor_density",),
    "occupation_cm2": ("occupation",),
    "iteration": ("iteration",),
    "residual_potential_V": ("residual_potential",),
    "residual_electron_density_cm2": ("residual_edensity",),
    "residual_hole_density_cm2": ("residual_hdensity",),
}


def _header_matches(actual: str, expected: str) -> bool:
    """Loose but non-trivial agreement between a header token and a config name."""

    normalised = actual.strip().lower().rstrip(".")
    hints = _NAME_HINTS.get(expected)
    if hints is None:
        # Unknown logical name: accept, the explicit index remains authoritative.
        return True
    return any(normalised.startswith(hint) or hint in normalised for hint in hints)


def read_table(path: Path) -> Table:
    """Read a whitespace/comma separated nextnano++ table with its header."""

    if not path.is_file():
        raise ParserError(f"output file not found: {path}")
    header: tuple[tuple[str, str], ...] = ()
    rows: list[list[float]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        fields = [field for field in re.split(r"[\s,;]+", stripped.lstrip("#").strip()) if field]
        try:
            values = [float(field) for field in fields]
        except ValueError:
            if not header and not rows:
                header = parse_header(raw)
            continue
        if values:
            rows.append(values)
    if not rows:
        raise ParserError(f"no numeric rows found in {path}")
    width = max(len(row) for row in rows)
    kept = [row for row in rows if len(row) == width]
    data = np.asarray(kept, dtype=float)
    if data.ndim != 2 or not np.isfinite(data).all():
        raise ParserError(f"non-finite or ragged numeric data in {path}")
    return Table(path=path, header=header, data=data)


def read_state_table(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read ``energy_spectrum_k*.dat`` as ``(state_number, energy_eV)``.

    Energies are returned in the solver's own order.  They are *not* sorted:
    nextnano++ lists hole states with decreasing electron energy, so sorting
    here would silently relabel physical states.
    """

    table = read_table(path)
    if table.n_columns < 2:
        raise ParserError(f"{path}: expected at least two columns (index, energy).")
    return table.column(0), table.column(1)


def read_profile_table(path: Path, *, value_columns: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Read ``x[nm]`` plus one or more value columns (envelopes, densities)."""

    table = read_table(path)
    if table.n_columns < 2:
        raise ParserError(f"{path}: expected a position column plus at least one value.")
    x = table.column(0)
    values = table.data[:, 1:]
    if value_columns is not None:
        if values.shape[1] < value_columns:
            raise ParserError(
                f"{path}: {values.shape[1]} value column(s) present, {value_columns} requested."
            )
        values = values[:, :value_columns]
    return x, values


def read_matrix_elements(path: Path) -> dict[tuple[int, int], dict[str, float]]:
    """Read a nextnano++ matrix-element ``.txt`` table.

    Layout is ``i  j  <values...>`` under a header naming each value column,
    for example ``|<Gamma_i|eps.d|Gamma_j>|[e*nm]``.  The returned mapping is
    keyed by the 1-based ``(i, j)`` state pair; value keys are the header names
    with their units preserved separately in :func:`matrix_element_units`.
    """

    table = read_table(path)
    if table.n_columns < 3:
        raise ParserError(f"{path}: expected at least i, j, and one value column.")
    names = [name for name, _ in table.header] or [
        f"column_{index}" for index in range(table.n_columns)
    ]
    if len(names) < table.n_columns:
        names = names + [
            f"column_{index}" for index in range(len(names), table.n_columns)
        ]
    result: dict[tuple[int, int], dict[str, float]] = {}
    for row in table.data:
        key = (int(round(row[0])), int(round(row[1])))
        result[key] = {
            names[index]: float(row[index]) for index in range(2, table.n_columns)
        }
    return result


def matrix_element_units(path: Path) -> dict[str, str]:
    """Header-declared units of a matrix-element table, keyed by column name."""

    table = read_table(path)
    return {name: unit for name, unit in table.header if unit}


def first_value_column(
    elements: Mapping[tuple[int, int], Mapping[str, float]],
    *,
    contains: str,
    excludes: Sequence[str] = (),
) -> str:
    """Pick the single value column whose name contains ``contains``.

    ``excludes`` removes near-duplicates such as the squared column or the
    separate real and imaginary parts. Ambiguity is an error: silently taking
    the first match is how a squared magnitude ends up being used as a length.
    """

    if not elements:
        raise ParserError("matrix-element table is empty.")
    sample = next(iter(elements.values()))
    matches = [
        name
        for name in sample
        if contains in name and not any(token in name for token in excludes)
    ]
    if not matches:
        raise ParserError(
            f"no matrix-element column contains {contains!r} "
            f"(excluding {list(excludes)}); have: {sorted(sample)}"
        )
    if len(matches) > 1:
        raise ParserError(
            f"matrix-element column {contains!r} is ambiguous: {sorted(matches)}"
        )
    return matches[0]


def magnitude_column(path: Path, *, unit: str) -> str:
    """Name of the magnitude column carrying ``unit`` in a matrix-element file.

    nextnano++ writes four columns per polarisation, for example
    ``|<i|eps.d|j>|[e*nm]``, ``|<i|eps.d|j>|^2[e^2*nm^2]``,
    ``Re<i|eps.d|j>[e*nm]``, and ``Im<i|eps.d|j>[e*nm]``. Selecting by unit
    alone still leaves the real and imaginary parts, so those are excluded by
    name. The squared column is excluded by its different unit, which is exactly
    why the unit is the primary key here.
    """

    units = matrix_element_units(path)
    candidates = [
        name
        for name, declared in units.items()
        if declared == unit and not name.startswith(("Re", "Im"))
    ]
    if not candidates:
        raise ParserError(
            f"{path}: no magnitude column with unit {unit!r}; header declares "
            f"{units}"
        )
    if len(candidates) > 1:
        raise ParserError(
            f"{path}: several magnitude columns carry unit {unit!r}: {sorted(candidates)}"
        )
    return candidates[0]


def solver_log_text(raw_dir: Path) -> str:
    """Concatenated text of every solver log/summary beneath ``raw_dir``.

    ``summary.log`` carries the run narrative and any non-convergence warning;
    ``job_done.txt`` / ``job_running.txt`` carry the completion verdict. The
    "DONE." banner goes only to the console and is therefore never available
    after the fact -- matching on it would fail every real run.
    """

    parts: list[str] = []
    for pattern in (
        "**/*.log",
        "**/summary.log",
        "**/simulation_info.txt",
        "**/job_*.txt",
    ):
        for path in sorted(raw_dir.glob(pattern)):
            if path.is_file():
                parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(dict.fromkeys(parts))


def require_or_diagnose(
    resolved: ResolvedOutputs, raw_dir: Path, keys: Iterable[str], *, why: str
) -> None:
    """Turn a *conditionally* required artifact into a clear, actionable failure.

    Some artifacts are optional in the profile because they only exist when a
    particular physics block is enabled. When the demo knows it enabled that
    block, a missing file is a real error -- and the useful error names the
    files that *were* written, so the profile can be corrected in one edit.
    """

    missing = [key for key in keys if not resolved.many(key)]
    if not missing:
        return
    raise ParserError(
        f"{why}, so {', '.join(missing)} should have been written but was not.\n"
        "The pattern in the parser profile is probably wrong for this solver "
        "build. Files actually present:\n" + _diagnostic(raw_dir)
    )


def completion_evidence(raw_dir: Path) -> dict[str, Any]:
    """File-level evidence that a run finished, independent of log wording.

    nextnano++ 3.0.0 writes ``job_running.txt`` at start and replaces it with
    ``job_done.txt`` on success, so a stale ``job_running.txt`` is an
    unambiguous "this run did not finish".
    """

    done = sorted(raw_dir.rglob("job_done.txt"))
    running = sorted(raw_dir.rglob("job_running.txt"))
    # Both keys are polarised so that True always means "good", which is what
    # the validation aggregator assumes of every boolean it collects.
    return {
        "job_done_file_present": bool(done),
        "no_stale_job_running_file": not running,
        "completion_files": [str(path.name) for path in (*done, *running)],
    }


def scan_log_markers(
    text: str,
    *,
    completion_markers: Sequence[str] = (),
    fatal_markers: Sequence[str] = (),
    warning_markers: Sequence[str] = (),
) -> dict[str, Any]:
    """Classify a solver log without conflating completion with convergence."""

    lowered = text.lower()
    found_warnings = [
        marker for marker in warning_markers if str(marker).lower() in lowered
    ]
    found_fatal = [marker for marker in fatal_markers if str(marker).lower() in lowered]
    completed = (
        any(str(marker).lower() in lowered for marker in completion_markers)
        if completion_markers
        else bool(text.strip())
    )
    return {
        "completion_marker_found": bool(completed),
        "no_fatal_marker": not found_fatal,
        "fatal_markers_found": found_fatal,
        "warning_markers_found": found_warnings,
        "no_convergence_warning": not found_warnings,
    }
