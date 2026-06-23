"""show: print a readable, ranked view of the committed promotion-records.

Read-only and offline. Loads every record under queue/, decided/, and
examples/, ranks them (pending first, since those are the rows awaiting a
human verdict, then most-recent first), and prints a status summary plus a
one-line headline naming what most needs attention.

The CLI wires this to stdout via `python -m review_queue show`.
"""
from __future__ import annotations

from typing import Iterable

from review_queue.records import Record

# rank order: rows that still need a human come first.
_STATUS_RANK = {
    "pending": 0,
    "approved": 1,
    "published": 2,
    "rejected": 3,
    "superseded": 4,
}


def _decision(r: Record) -> str:
    verdicts = r.fm.get("verdicts") or []
    if not verdicts:
        return "-"
    return verdicts[-1].get("decision", "-")


def rank(records: Iterable[Record]) -> list[Record]:
    recs = list(records)
    # primary: status rank ascending; secondary: created_at descending.
    recs.sort(key=lambda r: r.fm.get("created_at", ""), reverse=True)
    recs.sort(key=lambda r: _STATUS_RANK.get(r.fm.get("status", ""), 9))
    return recs


def status_counts(records: Iterable[Record]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in records:
        counts[r.fm.get("status", "?")] = counts.get(r.fm.get("status", "?"), 0) + 1
    return counts


def render(records: Iterable[Record]) -> str:
    recs = rank(records)
    lines: list[str] = []
    lines.append("review-queue - promotion-record queue")
    if not recs:
        lines.append("(no records under queue/, decided/, or examples/)")
        return "\n".join(lines)

    counts = status_counts(recs)
    summary = "  ".join(
        f"{s}={counts[s]}" for s in sorted(counts, key=lambda s: _STATUS_RANK.get(s, 9))
    )
    pending = counts.get("pending", 0)
    lines.append(
        f"{len(recs)} record(s) - {summary} "
        f"(ranked: rows awaiting a verdict first, then most recent)"
    )
    lines.append("")

    header = f"{'id':<22} {'status':<11} {'type':<14} {'decision':<9} {'created':<20} target"
    lines.append(header)
    lines.append("-" * len(header))
    for r in recs:
        lines.append(
            f"{r.fm.get('id', '?')[:22]:<22} "
            f"{r.fm.get('status', '?'):<11} "
            f"{(r.fm.get('record_type') or '?')[:14]:<14} "
            f"{_decision(r):<9} "
            f"{(r.fm.get('created_at') or '?')[:20]:<20} "
            f"{r.fm.get('target', '?')}"
        )

    lines.append("")
    if pending:
        oldest_pending = min(
            (r for r in recs if r.fm.get("status") == "pending"),
            key=lambda r: r.fm.get("created_at", ""),
        )
        lines.append(
            f"needs attention: {pending} record(s) pending a human verdict - "
            f"oldest is {oldest_pending.fm.get('id')} "
            f"({oldest_pending.fm.get('record_type')}, queued {oldest_pending.fm.get('created_at')}). "
            f"decide with `python -m review_queue decide --record-id {oldest_pending.fm.get('id')} "
            f"--verdict approve --reviewer <you>`."
        )
    else:
        lines.append("needs attention: 0 pending records - queue is clear.")
    return "\n".join(lines)
