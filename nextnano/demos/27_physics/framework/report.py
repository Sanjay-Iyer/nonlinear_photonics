"""CSV, JSON, text and markdown writers for Demo 27. No physics here."""

from __future__ import annotations

import csv
import json
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def read_json(path: Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")
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
