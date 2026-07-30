"""Machine-readable demo status and dependency gating.

The learning sequence only means something if a later demo cannot quietly
inherit an earlier demo's *claim* of validity.  Every demo declares what it
depends on and how far it has actually been validated; every run records the
status of its dependencies in its manifest and says so in its validation report.

Nothing here blocks a run.  Generating inputs for Demo 8 before Demo 7 has been
executed on the licensed laptop is a normal part of authoring.  What is not
allowed is *reporting* Demo 8 as validated on that basis.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

DEMOS_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = DEMOS_ROOT / "demo_registry.yaml"

# The status vocabulary. Order is deliberate: it is also the confidence order.
STATUSES: tuple[str, ...] = (
    "failed",
    "syntax_unverified",
    "implemented_dry_run",
    "licensed_run_pending",
    "solver_passed",
    "parser_passed",
    "physically_validated",
)

#: Statuses that justify describing a demo's *physics* as trustworthy.
PHYSICALLY_TRUSTED: frozenset[str] = frozenset({"physically_validated"})

#: Statuses that justify describing a demo's *plumbing* as exercised for real.
SOLVER_TRUSTED: frozenset[str] = frozenset(
    {"solver_passed", "parser_passed", "physically_validated"}
)

_DEMO_KEYS = {
    "title",
    "status",
    "depends_on",
    "introduces",
    "home_syntax_check",
    "home_solver_check",
    "licensed_validation",
    "pending_licensed_checks",
    "unvalidated_syntax",
}


class RegistryError(RuntimeError):
    """Raised when the registry is malformed or inconsistent."""


@dataclass(frozen=True)
class DemoRecord:
    """One demo's declared capability and validation state."""

    demo_id: str
    title: str
    status: str
    depends_on: tuple[str, ...]
    introduces: tuple[str, ...]
    home_syntax_check: str
    home_solver_check: str
    licensed_validation: Mapping[str, Any]
    pending_licensed_checks: tuple[str, ...]
    unvalidated_syntax: tuple[str, ...]

    @property
    def physically_validated(self) -> bool:
        return self.status in PHYSICALLY_TRUSTED

    @property
    def solver_exercised(self) -> bool:
        return self.status in SOLVER_TRUSTED

    def as_dict(self) -> dict[str, Any]:
        return {
            "demo_id": self.demo_id,
            "title": self.title,
            "status": self.status,
            "depends_on": list(self.depends_on),
            "introduces": list(self.introduces),
            "home_syntax_check": self.home_syntax_check,
            "home_solver_check": self.home_solver_check,
            "licensed_validation": dict(self.licensed_validation),
            "pending_licensed_checks": list(self.pending_licensed_checks),
            "unvalidated_syntax": list(self.unvalidated_syntax),
            "physically_validated": self.physically_validated,
        }


@dataclass(frozen=True)
class Registry:
    """All demo records, keyed by directory name."""

    demos: Mapping[str, DemoRecord]
    source_path: Path

    def record(self, demo_id: str) -> DemoRecord:
        try:
            return self.demos[demo_id]
        except KeyError as exc:
            known = ", ".join(sorted(self.demos))
            raise RegistryError(
                f"demo {demo_id!r} is not in {self.source_path}. Known: {known}"
            ) from exc

    def dependency_records(self, demo_id: str) -> tuple[DemoRecord, ...]:
        return tuple(self.record(name) for name in self.record(demo_id).depends_on)

    def dependency_report(self, demo_id: str) -> dict[str, Any]:
        """Snapshot written into every run manifest and validation report."""

        record = self.record(demo_id)
        dependencies = self.dependency_records(demo_id)
        unvalidated = [
            dependency.demo_id
            for dependency in dependencies
            if not dependency.physically_validated
        ]
        return {
            "demo_id": demo_id,
            "declared_status": record.status,
            "registry_path": str(self.source_path),
            "depends_on": {
                dependency.demo_id: dependency.status for dependency in dependencies
            },
            "dependencies_not_physically_validated": unvalidated,
            "all_dependencies_physically_validated": not unvalidated,
            "interpretation": (
                "Results of this demo may not be presented as physically validated "
                "while any dependency above is not physically_validated."
                if unvalidated
                else "Every declared dependency is physically validated."
            ),
        }

    def ordered_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.demos))


def load_registry(path: Path | None = None) -> Registry:
    """Load, strictly validate, and topologically check the demo registry."""

    source = path or REGISTRY_PATH
    if not source.is_file():
        raise RegistryError(f"demo registry not found: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or "demos" not in data:
        raise RegistryError(f"{source} must contain a top-level 'demos' mapping.")
    raw = data["demos"]
    if not isinstance(raw, dict) or not raw:
        raise RegistryError(f"{source}: 'demos' must be a non-empty mapping.")

    demos: dict[str, DemoRecord] = {}
    for demo_id, entry in raw.items():
        if not isinstance(entry, dict):
            raise RegistryError(f"{source}: demo {demo_id!r} must be a mapping.")
        unknown = sorted(set(entry) - _DEMO_KEYS)
        if unknown:
            raise RegistryError(
                f"{source}: demo {demo_id!r} has unsupported key(s): {', '.join(unknown)}"
            )
        status = str(entry.get("status", "")).strip()
        if status not in STATUSES:
            raise RegistryError(
                f"{source}: demo {demo_id!r} has status {status!r}; allowed: "
                f"{', '.join(STATUSES)}"
            )
        demos[str(demo_id)] = DemoRecord(
            demo_id=str(demo_id),
            title=str(entry.get("title", demo_id)),
            status=status,
            depends_on=tuple(str(name) for name in entry.get("depends_on") or ()),
            introduces=tuple(str(name) for name in entry.get("introduces") or ()),
            home_syntax_check=str(entry.get("home_syntax_check", "not_checked")),
            home_solver_check=str(entry.get("home_solver_check", "not_checked")),
            licensed_validation=dict(entry.get("licensed_validation") or {}),
            pending_licensed_checks=tuple(
                str(item) for item in entry.get("pending_licensed_checks") or ()
            ),
            unvalidated_syntax=tuple(
                str(item) for item in entry.get("unvalidated_syntax") or ()
            ),
        )

    for record in demos.values():
        for dependency in record.depends_on:
            if dependency not in demos:
                raise RegistryError(
                    f"{source}: demo {record.demo_id!r} depends on unknown demo "
                    f"{dependency!r}."
                )
            if dependency >= record.demo_id:
                raise RegistryError(
                    f"{source}: demo {record.demo_id!r} depends on {dependency!r}, "
                    "which does not precede it in the learning sequence."
                )
    return Registry(demos=demos, source_path=source)


def demo_ids_from_directories(demos_root: Path | None = None) -> tuple[str, ...]:
    """Directory names that look like demos, for cross-checking the registry."""

    root = demos_root or DEMOS_ROOT
    return tuple(
        sorted(
            path.name
            for path in root.iterdir()
            if path.is_dir()
            and not path.name.startswith("_")
            and (path / "demo.yaml").is_file()
        )
    )


def missing_from_registry(
    registry: Registry, demos_root: Path | None = None
) -> tuple[str, ...]:
    """Demo directories that exist on disk but are not declared."""

    return tuple(
        demo_id
        for demo_id in demo_ids_from_directories(demos_root)
        if demo_id not in registry.demos
    )


def summarise(registry: Registry, demo_ids: Iterable[str] | None = None) -> str:
    """Human-readable status table used in the demo README and reports."""

    ids = tuple(demo_ids) if demo_ids is not None else registry.ordered_ids()
    lines = [
        "| demo | status | home syntax | home solver | licensed evidence |",
        "|---|---|---|---|---|",
    ]
    for demo_id in ids:
        record = registry.record(demo_id)
        evidence = record.licensed_validation.get("evidence", "—") or "—"
        lines.append(
            f"| {demo_id} | `{record.status}` | {record.home_syntax_check} | "
            f"{record.home_solver_check} | {evidence} |"
        )
    return "\n".join(lines)
