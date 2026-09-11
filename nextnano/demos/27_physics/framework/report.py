"""CSV, JSON, text and markdown writers for Demo 27. No physics here."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> Path:
    records = [dict(row) for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in records:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"])
        writer.writeheader()
        writer.writerows(records)
    return path


def write_json(path: Path, value: Any) -> Path:
    """Write JSON atomically.

    Sub-demos are meant to be runnable in parallel terminals, so a reader must
    never observe a half-written status file or manifest. The content is written
    to a temporary file beside the target and moved into place with os.replace,
    which is atomic on Windows and POSIX alike.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(value, indent=2, default=str) + "\n"
    temp = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))
    try:
        temp.write_text(blob, encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return path


def read_json(path: Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_tolerant(path: Path, default: Any = None) -> Any:
    """Read JSON, returning ``default`` if the file is absent or unreadable.

    Used for status display. A reporting command must not crash because a
    concurrently running sub-demo happened to be mid-write; the writers are
    atomic, so the next read succeeds.
    """
    try:
        return read_json(path, default)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return default


def write_text(path: Path, value: str) -> Path:
    """Write text atomically, for the same reason as :func:`write_json`."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("%s.%d.tmp" % (path.name, os.getpid()))
    try:
        temp.write_text(value.rstrip() + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return path


def markdown_table(rows: list[Mapping[str, Any]], columns: list[str],
                   alignments: Mapping[str, str] | None = None) -> str:
    align = dict(alignments or {})

    def clean(value: Any) -> str:
        if value is None:
            return ""
        return str(value).replace("|", "\\|").replace("\n", " ")

    def rule(column: str) -> str:
        return {"right": "---:", "center": ":---:"}.get(align.get(column, "left"), "---")

    head = "| " + " | ".join(columns) + " |"
    sep = "|" + "|".join(rule(c) for c in columns) + "|"
    body = ["| " + " | ".join(clean(row.get(c, "")) for c in columns) + " |" for row in rows]
    return "\n".join([head, sep, *body])
