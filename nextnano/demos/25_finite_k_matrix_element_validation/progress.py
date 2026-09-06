"""Terminal completion tracker for Demo 25.

Demo 25 runs in stages across two machines and a Professional solver run that
can take hours, so the tracker persists to JSON and can be rendered at any time
from any process:

    python run_demo25.py --progress          # one-shot snapshot
    python run_demo25.py --progress --watch  # live, refreshes until done

ETA comes from measured per-unit throughput where a stage reports units (k
points), and from stage weights otherwise. A stage with no measurement yet
reports "unknown" rather than a fabricated estimate.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


PENDING, RUNNING, DONE, FAILED, SKIPPED, BLOCKED = (
    "pending", "running", "done", "failed", "skipped", "blocked")
_GLYPH = {PENDING: " ", RUNNING: "*", DONE: "#", FAILED: "!", SKIPPED: "-", BLOCKED: "x"}
_LABEL = {PENDING: "pending", RUNNING: "running", DONE: "done", FAILED: "FAILED",
          SKIPPED: "skipped", BLOCKED: "BLOCKED"}


def _now() -> float:
    return time.time()


def _stamp(value: float | None) -> str:
    if not value:
        return ""
    return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%H:%M:%SZ")


def humanize(seconds: float | None) -> str:
    if seconds is None or seconds != seconds or seconds < 0:
        return "unknown"
    seconds = int(seconds)
    if seconds < 90:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 90:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


@dataclass
class Stage:
    key: str
    title: str
    weight: float = 1.0
    status: str = PENDING
    units_total: int = 0
    units_done: int = 0
    started_at: float | None = None
    finished_at: float | None = None
    note: str = ""
    gate: bool = False          # a gate stage blocks everything after it on failure

    @property
    def fraction(self) -> float:
        if self.status in (DONE, SKIPPED):
            return 1.0
        if self.status in (FAILED, BLOCKED):
            return 0.0
        if self.status == RUNNING and self.units_total > 0:
            return min(1.0, self.units_done / self.units_total)
        return 0.0

    @property
    def elapsed(self) -> float | None:
        if not self.started_at:
            return None
        return (self.finished_at or _now()) - self.started_at

    def eta(self) -> float | None:
        """Remaining seconds from measured throughput, or None if unmeasured."""
        if self.status in (DONE, SKIPPED, FAILED, BLOCKED):
            return 0.0
        if self.status != RUNNING or not self.started_at:
            return None
        if self.units_total <= 0 or self.units_done <= 0:
            return None
        rate = (_now() - self.started_at) / self.units_done
        return rate * (self.units_total - self.units_done)


class Tracker:
    """Persistent, multi-process-safe-enough stage tracker."""

    def __init__(self, path: Path, stages: Iterable[Stage] | None = None,
                 title: str = "Demo 25") -> None:
        self.path = Path(path)
        self.title = title
        self.stages: list[Stage] = list(stages or [])
        self.created_at: float = _now()
        if self.path.is_file():
            self._load(keep=stages is None)

    # -- persistence --------------------------------------------------------
    def _load(self, *, keep: bool) -> None:
        try:
            blob = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.created_at = float(blob.get("created_at", self.created_at))
        self.title = str(blob.get("title", self.title))
        stored = {s["key"]: s for s in blob.get("stages", [])}
        if keep:
            self.stages = [Stage(**s) for s in blob.get("stages", [])]
            return
        for stage in self.stages:      # merge saved state onto the declared plan
            if stage.key in stored:
                saved = stored[stage.key]
                for field_name in ("status", "units_total", "units_done",
                                   "started_at", "finished_at", "note"):
                    setattr(stage, field_name, saved.get(field_name, getattr(stage, field_name)))

    def save(self) -> Path:
        """Persist the plan.

        The atomic rename is preferred so a concurrent ``--progress`` reader
        never sees a half-written file, but on Windows an indexer or scanner
        can briefly hold either path and make ``os.replace`` raise WinError 5.
        Progress bookkeeping must never take down a running solver stage, so
        the rename is retried and then falls back to a direct write.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        blob = {"title": self.title, "created_at": self.created_at,
                "updated_at": _now(), "stages": [asdict(s) for s in self.stages]}
        payload = json.dumps(blob, indent=2)
        tmp = self.path.with_suffix(".tmp")
        for attempt in range(4):
            try:
                tmp.write_text(payload, encoding="utf-8")
                os.replace(tmp, self.path)
                return self.path
            except OSError:
                time.sleep(0.05 * (attempt + 1))
        try:
            self.path.write_text(payload, encoding="utf-8")
        except OSError:
            pass                      # never let progress reporting break a stage
        return self.path

    # -- mutation -----------------------------------------------------------
    def stage(self, key: str) -> Stage:
        for item in self.stages:
            if item.key == key:
                return item
        raise KeyError(f"unknown Demo 25 stage {key!r}")

    def start(self, key: str, *, units_total: int = 0, note: str = "") -> Stage:
        stage = self.stage(key)
        stage.status, stage.started_at, stage.finished_at = RUNNING, _now(), None
        stage.units_total, stage.units_done = int(units_total), 0
        if note:
            stage.note = note
        self.save()
        return stage

    def advance(self, key: str, units: int = 1, *, note: str = "") -> Stage:
        stage = self.stage(key)
        stage.units_done += int(units)
        if note:
            stage.note = note
        self.save()
        return stage

    def finish(self, key: str, status: str = DONE, *, note: str = "") -> Stage:
        stage = self.stage(key)
        stage.status, stage.finished_at = status, _now()
        if stage.units_total:
            stage.units_done = stage.units_total if status == DONE else stage.units_done
        if note:
            stage.note = note
        if status in (FAILED, BLOCKED) and stage.gate:
            self._block_after(key, note=f"blocked by gate '{stage.title}'")
        self.save()
        return stage

    def _block_after(self, key: str, *, note: str) -> None:
        seen = False
        for stage in self.stages:
            if stage.key == key:
                seen = True
                continue
            if seen and stage.status == PENDING:
                stage.status, stage.note = BLOCKED, note

    # -- reporting ----------------------------------------------------------
    @property
    def fraction(self) -> float:
        total = sum(s.weight for s in self.stages) or 1.0
        return sum(s.weight * s.fraction for s in self.stages) / total

    def eta(self) -> float | None:
        """Whole-run ETA: measured for the running stage, weight-scaled for the rest."""
        running = next((s for s in self.stages if s.status == RUNNING), None)
        if running is None:
            return None
        head = running.eta()
        if head is None:
            return None
        remaining_weight = sum(s.weight for s in self.stages
                               if s.status == PENDING)
        done = [s for s in self.stages if s.status == DONE and s.elapsed and s.weight > 0]
        if not done:
            return head if remaining_weight == 0 else None
        per_weight = sum(s.elapsed for s in done) / sum(s.weight for s in done)
        return head + per_weight * remaining_weight

    def render(self, *, width: int = 34, color: bool = True) -> str:
        lines: list[str] = []
        bold, dim, reset = ("\033[1m", "\033[2m", "\033[0m") if color else ("", "", "")
        red, green, yellow = ("\033[31m", "\033[32m", "\033[33m") if color else ("", "", "")
        pct = 100.0 * self.fraction
        filled = int(round(width * self.fraction))
        bar = "#" * filled + "." * (width - filled)
        eta = self.eta()
        lines.append(f"{bold}{self.title}{reset}  [{bar}] {pct:5.1f}%"
                     f"   elapsed {humanize(_now() - self.created_at)}"
                     f"   remaining {humanize(eta)}")
        lines.append("")
        for stage in self.stages:
            tint = {DONE: green, FAILED: red, BLOCKED: red, RUNNING: yellow}.get(stage.status, dim)
            mark = _GLYPH[stage.status]
            counter = ""
            if stage.units_total:
                counter = f" {stage.units_done}/{stage.units_total}"
            timing = ""
            if stage.status == RUNNING:
                timing = f"  ~{humanize(stage.eta())} left"
            elif stage.status == DONE and stage.elapsed:
                timing = f"  {humanize(stage.elapsed)}"
            gate = " (gate)" if stage.gate else ""
            lines.append(f"  [{mark}] {tint}{stage.title:<44}{reset}"
                         f"{_LABEL[stage.status]:>8}{counter}{timing}{gate}")
            if stage.note:
                lines.append(f"      {dim}{stage.note}{reset}")
        return "\n".join(lines)

    def summary(self) -> dict[str, Any]:
        return {
            "title": self.title, "fraction": self.fraction,
            "eta_seconds": self.eta(),
            "stages": {s.key: {"status": s.status, "units_done": s.units_done,
                               "units_total": s.units_total, "note": s.note,
                               "elapsed_seconds": s.elapsed} for s in self.stages},
        }


def default_plan(cfg: Mapping[str, Any]) -> list[Stage]:
    """The Demo 25 stage plan. Weights are rough relative costs, not seconds."""
    pilot_count = len(cfg["pilot"]["variants"])
    return [
        Stage("audit", "Audit Demo 23/24 inputs and freeze structure", 1.0),
        Stage("decks_pilot", "Generate pilot decks", 0.5),
        Stage("syntax", "nextnano --parse syntax validation", 1.0, gate=True),
        Stage("pilot_run", f"PILOT: run {pilot_count} Professional variants", 8.0),
        Stage("pilot_audit", "PILOT GATE: finite-k output audit", 1.5, gate=True),
        Stage("decks_production", "Size and generate production deck", 0.5),
        Stage("production_run", "PRODUCTION: Professional finite-k run", 60.0),
        Stage("parse", "Parse finite-k states, spinors, matrices", 5.0),
        Stage("tracking", "Character-based state tracking", 2.0),
        Stage("transitions", "Extended-state ~2.296 eV search", 2.0),
        Stage("matrices", "Compute O_nm(k), z_e(k), z_hh(k)", 4.0),
        Stage("pathways", "Pathway numerators M_p(k)/M_p(0)", 2.0),
        Stage("chi2", "Recompute Equation 2 with finite-k M(k)", 3.0),
        Stage("figures", "Figures and tables", 2.0),
        Stage("report", "Final report and professor review package", 1.5),
    ]


def watch(path: Path, interval: float = 5.0) -> int:
    """Redraw the tracker until every stage is terminal."""
    terminal = {DONE, FAILED, SKIPPED, BLOCKED}
    try:
        while True:
            tracker = Tracker(path)
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(tracker.render() + "\n")
            sys.stdout.flush()
            if tracker.stages and all(s.status in terminal for s in tracker.stages):
                return 0
            time.sleep(interval)
    except KeyboardInterrupt:
        return 130
