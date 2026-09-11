"""Campaign status: one machine-readable file, one human-readable table.

``MASTER_STATUS.json`` is the state. ``MASTER_STATUS.md`` is regenerated from
it, so the two can never disagree. Nothing else in Demo 27 writes either file.
"""

from __future__ import annotations

import datetime as _dt
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Mapping

from . import Demo27Error
from . import registry
from .report import (markdown_table, read_json_tolerant, write_json,
                     write_text)


def status_paths(parent: Mapping) -> tuple:
    return (registry.DEMO_DIR / str(parent["outputs"]["status_json"]),
            registry.DEMO_DIR / str(parent["outputs"]["status_md"]))


def load(parent: Mapping) -> dict:
    json_path, _ = status_paths(parent)
    blob = read_json_tolerant(json_path, default=None)
    if blob is None:
        return {"schema": 1, "demos": {}}
    if "demos" not in blob:
        raise Demo27Error("%s has no 'demos' block" % json_path)
    return blob


def statuses(parent: Mapping) -> dict:
    blob = load(parent)
    return {key: str(value.get("status", "NOT RUN")) for key, value in blob["demos"].items()}


@contextmanager
def _exclusive(parent: Mapping, timeout: float = 60.0):
    """Hold a cross-process lock on the status file.

    Sub-demos are meant to run in parallel terminals, and every ``--physics``
    stage records RUNNING at its start and again at its end. Without a lock,
    two of those read-modify-write cycles can interleave and one update is
    silently lost -- which would show a sub-demo as never having run.

    The lock is a file created with O_EXCL, so it works across processes on
    Windows without a third-party dependency. A stale lock (a run killed
    mid-write) is broken after ``timeout``, because losing a status update is
    recoverable with ``--record`` while a permanently wedged campaign is not.
    """
    json_path, _ = status_paths(parent)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    lock = json_path.with_suffix(".lock")
    deadline = time.time() + float(timeout)
    handle = None
    while True:
        try:
            handle = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() >= deadline:
                try:
                    lock.unlink()
                except OSError:
                    pass
                handle = os.open(str(lock), os.O_CREAT | os.O_WRONLY)
                break
            time.sleep(0.05)
    try:
        os.write(handle, str(os.getpid()).encode("ascii"))
        os.close(handle)
        handle = None
        yield
    finally:
        if handle is not None:
            os.close(handle)
        try:
            lock.unlink()
        except OSError:
            pass


def record(parent: Mapping, demo_id: str, status: str, *, conclusion: str | None = None,
           note: str | None = None) -> dict:
    """Set one sub-demo's status and rewrite both files.

    The read, the modify and the write happen under one lock, so a sub-demo
    running in another terminal cannot overwrite this update with a stale copy.
    """
    if status not in registry.STATUSES:
        raise Demo27Error("status %r is not one of %s" % (status, registry.STATUSES))
    with _exclusive(parent):
        blob = load(parent)
        entry = dict(blob["demos"].get(demo_id) or {})
        entry["status"] = status
        entry["updated"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        if conclusion is not None:
            entry["conclusion"] = conclusion
        if note is not None:
            entry["note"] = note
        blob["demos"][demo_id] = entry
        json_path, _ = status_paths(parent)
        write_json(json_path, blob)
        render(parent)
    return entry


def rows(parent: Mapping, subs=None) -> list:
    subs = subs or registry.discover(parent)
    blob = load(parent)
    recorded = {key: str(value.get("status", "NOT RUN")) for key, value in blob["demos"].items()}
    out = []
    for sub in subs:
        entry = blob["demos"].get(sub.demo_id) or {}
        out.append({
            "Demo": sub.demo_id,
            "Question": sub.question,
            "Tier": sub.tier,
            "Status": registry.derived_status(sub, recorded),
            "Pro required?": "Yes" if sub.professional_required else "No",
            "Runtime estimate": sub.runtime_text(),
            "Prerequisite": ", ".join(sub.prerequisites) or "none",
            "Main conclusion": str(entry.get("conclusion", "")),
        })
    return out


def render(parent: Mapping, subs=None) -> Path:
    """Rewrite MASTER_STATUS.md from MASTER_STATUS.json."""
    subs = subs or registry.discover(parent)
    table = rows(parent, subs)
    _, md_path = status_paths(parent)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    columns = ["Demo", "Question", "Tier", "Status", "Pro required?",
               "Runtime estimate", "Prerequisite", "Main conclusion"]
    text = "\n".join([
        "# Demo 27 master status",
        "",
        "Generated from `MASTER_STATUS.json` by `framework/status.py`. Do not hand-edit:",
        "run `python run_demo27.py --status` to regenerate, and let the stages record",
        "their own outcomes.",
        "",
        "Last written: %s" % stamp,
        "",
        markdown_table(table, columns, alignments={"Tier": "right"}),
        "",
        "## Status vocabulary",
        "",
        "| Status | Meaning |",
        "|---|---|",
        "| NOT RUN | no stage of this sub-demo has been executed |",
        "| READY | preflight passed; the physics stage may be launched |",
        "| RUNNING | a stage is in flight |",
        "| PASS | the sub-demo's stated pass condition was met |",
        "| FAIL | the pass condition was not met; downstream work stays blocked |",
        "| BLOCKED | a prerequisite has not reached PASS/COMPLETE/NOT NEEDED |",
        "| COMPLETE | the question is answered and the conclusion is recorded |",
        "| NOT NEEDED | earlier evidence removed the reason to run this |",
        "",
        "`BLOCKED` is derived, not stored: a sub-demo whose prerequisites are unmet",
        "displays as BLOCKED regardless of what is recorded, so the table cannot show",
        "a runnable sub-demo that is not actually runnable.",
        "",
    ])
    return write_text(md_path, text)
