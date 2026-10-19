"""decide: record a verdict on a queued record and flip its status."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from review_queue import diff as diff_mod
from review_queue import state
from review_queue.records import Record, find, save


# A reviewer is a self-asserted label, not an authenticated identity: the CLI
# records whatever name the caller types. The format only keeps the label
# usable as a name: 1-64 characters, a letter, digit or underscore first, then
# letters, digits and . _ @ + - (no spaces, newlines or other control text).
REVIEWER_RE = re.compile(r"\w[\w.@+-]{0,63}")


def normalize_reviewer(reviewer: str | None) -> str:
    """Trim surrounding whitespace and check the reviewer label's format."""
    value = (reviewer or "").strip()
    if not value:
        raise ValueError("reviewer is required (got an empty or blank value)")
    if not REVIEWER_RE.fullmatch(value):
        raise ValueError(
            f"reviewer {value!r} is not a valid label: use 1-64 characters, a letter, "
            "digit or underscore first, then letters, digits or . _ @ + - (no spaces)"
        )
    return value


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


def _edited_digest(record: Record, edit_diff: str, repo_root: Path) -> str | None:
    """Apply the edit to the submitted bytes and return the edited bytes' sha256.

    An edit approves the edited candidate (R-RQ-007), so the edit has to
    apply to exactly the bytes that were reviewed. A historical record
    without a submitted digest has nothing to pin; publish refuses it.
    """
    expected = record.fm.get("candidate_sha256")
    if not expected:
        return None
    candidate_path = (repo_root / record.fm["candidate_ref"]).resolve()
    if not candidate_path.is_file():
        raise FileNotFoundError(f"candidate file missing: {candidate_path}")
    candidate_bytes = candidate_path.read_bytes()
    if hashlib.sha256(candidate_bytes).hexdigest() != expected:
        raise ValueError("candidate changed since submission; resubmit it for review")
    edited = diff_mod.apply_edit(candidate_bytes, edit_diff)
    return hashlib.sha256(edited).hexdigest()


def decide(
    *,
    record_id: str,
    decision: str,
    reviewer: str,
    edit_diff: str | None = None,
    note: str | None = None,
    search_roots: Iterable[Path],
    now: str | None = None,
    repo_root: Path | None = None,
) -> Record:
    if decision not in ("approve", "reject", "edit"):
        raise ValueError(f"decision must be approve|reject|edit, got {decision!r}")
    if decision == "edit" and not edit_diff:
        raise ValueError("decision=edit requires --edit-diff")
    reviewer = normalize_reviewer(reviewer)

    record = find(record_id, search_roots)
    if record is None:
        raise FileNotFoundError(f"record not found: {record_id}")

    target_status = _decision_to_status(decision)
    state.assert_transition(record.fm["status"], target_status)

    approved_sha256 = None
    if decision == "edit":
        approved_sha256 = _edited_digest(record, edit_diff, repo_root or Path.cwd())

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
    if approved_sha256:
        record.fm["approved_sha256"] = approved_sha256

    state.consistency_check(record.fm)
    save(record)
    return record
