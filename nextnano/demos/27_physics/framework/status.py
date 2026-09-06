"""Campaign status: one machine-readable file, one human-readable table.

``MASTER_STATUS.json`` is the state. ``MASTER_STATUS.md`` is regenerated from
it, so the two can never disagree. Nothing else in Demo 27 writes either file.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Mapping

from . import Demo27Error
from . import registry
from .report import markdown_table, read_json, write_json, write_text


def status_paths(parent: Mapping) -> tuple:
    return (registry.DEMO_DIR / str(parent["outputs"]["status_json"]),
            registry.DEMO_DIR / str(parent["outputs"]["status_md"]))


def load(parent: Mapping) -> dict:
    json_path, _ = status_paths(parent)
    blob = read_json(json_path, default=None)
    if blob is None:
        return {"schema": 1, "demos": {}}
    if "demos" not in blob:
        raise Demo27Error("%s has no 'demos' block" % json_path)
    return blob


def statuses(parent: Mapping) -> dict:
    blob = load(parent)
    return {key: str(value.get("status", "NOT RUN")) for key, value in blob["demos"].items()}


def record(parent: Mapping, demo_id: str, status: str, *, conclusion: str | None = None,
           note: str | None = None) -> dict:
    """Set one sub-demo's status and rewrite both files."""
    if status not in registry.STATUSES:
        raise Demo27Error("status %r is not one of %s" % (status, registry.STATUSES))
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
