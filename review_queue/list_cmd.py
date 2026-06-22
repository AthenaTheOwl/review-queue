"""list: enumerate records filtered by status."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from review_queue.records import Record, iter_records


def list_records(
    *,
    roots: Iterable[Path],
    status: str | None = None,
    record_type: str | None = None,
    reviewer: str | None = None,
) -> list[Record]:
    records = iter_records(roots)
    if status:
        records = [r for r in records if r.fm.get("status") == status]
    if record_type:
        records = [r for r in records if r.fm.get("record_type") == record_type]
    if reviewer:
        records = [
            r
            for r in records
            if any(v.get("reviewer") == reviewer for v in r.fm.get("verdicts", []) or [])
        ]
    records.sort(key=lambda r: r.fm.get("created_at", ""))
    return records


def format_row(r: Record) -> str:
    return (
        f"{r.fm.get('id'):28s}  "
        f"{r.fm.get('status'):11s}  "
        f"{r.fm.get('record_type'):16s}  "
        f"{r.fm.get('created_at')}"
    )
