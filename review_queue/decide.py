"""decide: record a verdict on a queued record and flip its status."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from review_queue import state
from review_queue.records import Record, find, save


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _decision_to_status(decision: str) -> str:
    if decision == "approve":
        return "approved"
    if decision == "reject":
        return "rejected"
    if decision == "edit":
        return "approved"
    raise ValueError(f"unknown decision: {decision!r}")


def decide(
    *,
    record_id: str,
    decision: str,
    reviewer: str,
    edit_diff: str | None = None,
    note: str | None = None,
    search_roots: Iterable[Path],
    now: str | None = None,
) -> Record:
    if decision not in ("approve", "reject", "edit"):
        raise ValueError(f"decision must be approve|reject|edit, got {decision!r}")
    if decision == "edit" and not edit_diff:
        raise ValueError("decision=edit requires --edit-diff")
    if not reviewer:
        raise ValueError("reviewer is required")

    record = find(record_id, search_roots)
    if record is None:
        raise FileNotFoundError(f"record not found: {record_id}")

    target_status = _decision_to_status(decision)
    state.assert_transition(record.fm["status"], target_status)

    verdict: dict = {
        "reviewer": reviewer,
        "decided_at": now or _now_iso(),
        "decision": decision,
    }
    if edit_diff:
        verdict["edit_diff"] = edit_diff
    if note:
        verdict["note"] = note

    verdicts = list(record.fm.get("verdicts", []) or [])
    verdicts.append(verdict)
    record.fm["verdicts"] = verdicts
    record.fm["status"] = target_status

    state.consistency_check(record.fm)
    save(record)
    return record
