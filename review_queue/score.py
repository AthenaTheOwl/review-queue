"""score: compute calibration metrics over a row set.

The row set is a list of `review_queue.records.Record` objects loaded
from `queue/`, `decided/`, and `examples/`. The metrics are defined in
`docs/METHODOLOGY.md`. A row is eligible if it has at least one verdict
and its status is one of `approved`, `published`, `rejected`,
`superseded` (rows with `pending` status are skipped).

This module does not read or write files. The CLI wires it to
`review_queue.ledger` for persistence and `review_queue.report` for
display.
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable

from review_queue.records import Record


ELIGIBLE_STATUSES = frozenset(
    {"approved", "published", "rejected", "superseded"}
)
KNOWN_PROVENANCE_SCHEMES = ("trace://", "evidence://", "cdcp://")
MIN_VERDICT_LATENCY_SECONDS = 10


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def _first_verdict(record: Record) -> dict[str, Any] | None:
    verdicts = record.fm.get("verdicts") or []
    if not verdicts:
        return None
    return verdicts[0]


def _row_latency_seconds(record: Record) -> float | None:
    v = _first_verdict(record)
    if v is None:
        return None
    decided_at = v.get("decided_at")
    created_at = record.fm.get("created_at")
    if not decided_at or not created_at:
        return None
    try:
        return (_parse_iso(decided_at) - _parse_iso(created_at)).total_seconds()
    except ValueError:
        return None


def _row_is_eligible(record: Record) -> bool:
    if record.fm.get("status") not in ELIGIBLE_STATUSES:
        return False
    v = _first_verdict(record)
    if v is None:
        return False
    prov = record.fm.get("provenance_ref") or ""
    if not any(prov.startswith(s) for s in KNOWN_PROVENANCE_SCHEMES):
        return False
    latency = _row_latency_seconds(record)
    if latency is None or latency < MIN_VERDICT_LATENCY_SECONDS:
        return False
    return True


def score_records(
    records: Iterable[Record],
    *,
    record_type: str | None = None,
) -> dict[str, Any]:
    """Compute calibration metrics over `records`.

    If `record_type` is set, only records of that type are scored.
    Returns a dict suitable for JSONL serialization. `record_ids`
    is sorted; rates are floats in [0, 1]; latencies are seconds.
    """
    rows = []
    for r in records:
        if record_type is not None and r.fm.get("record_type") != record_type:
            continue
        if not _row_is_eligible(r):
            continue
        rows.append(r)

    if not rows:
        return {
            "record_type": record_type,
            "sample_count": 0,
            "approve_unchanged_rate": 0.0,
            "edit_rate": 0.0,
            "reject_rate": 0.0,
            "median_latency_seconds": None,
            "min_latency_seconds": None,
            "max_latency_seconds": None,
            "records": [],
        }

    n = len(rows)
    decisions = [(_first_verdict(r) or {}).get("decision") for r in rows]
    approve = sum(1 for d in decisions if d == "approve")
    edit = sum(1 for d in decisions if d == "edit")
    reject = sum(1 for d in decisions if d == "reject")
    latencies = [_row_latency_seconds(r) for r in rows]
    latencies = [int(round(x)) for x in latencies if x is not None]

    return {
        "record_type": record_type,
        "sample_count": n,
        "approve_unchanged_rate": round(approve / n, 6),
        "edit_rate": round(edit / n, 6),
        "reject_rate": round(reject / n, 6),
        "median_latency_seconds": int(round(median(latencies))) if latencies else None,
        "min_latency_seconds": min(latencies) if latencies else None,
        "max_latency_seconds": max(latencies) if latencies else None,
        "records": sorted(r.id for r in rows),
    }


AUTO_PROMOTE_THRESHOLD = {
    "min_samples": 20,
    "min_approve_unchanged_rate": 0.95,
    "source": "DEC-RQ-001",
}


def is_auto_promote_eligible(score_dict: dict[str, Any]) -> bool:
    return (
        score_dict.get("sample_count", 0) >= AUTO_PROMOTE_THRESHOLD["min_samples"]
        and score_dict.get("approve_unchanged_rate", 0.0)
        >= AUTO_PROMOTE_THRESHOLD["min_approve_unchanged_rate"]
    )
