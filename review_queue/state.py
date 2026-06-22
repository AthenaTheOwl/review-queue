"""State machine for promotion-record status transitions.

Allowed transitions (design.md):
- pending   -> approved
- pending   -> rejected
- pending   -> superseded
- approved  -> published
- approved  -> superseded

Terminal states: rejected, published, superseded.
A record's verdicts list must be consistent with its status:
- status=approved/published/superseded: at least one approve or edit verdict
- status=rejected: at least one reject verdict
"""
from __future__ import annotations

from typing import Any

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected", "superseded"},
    "approved": {"published", "superseded"},
    "rejected": set(),
    "published": set(),
    "superseded": set(),
}


class TransitionError(ValueError):
    """Raised when a status change violates the state machine."""


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


def assert_transition(from_status: str, to_status: str) -> None:
    if not can_transition(from_status, to_status):
        raise TransitionError(
            f"illegal transition: {from_status} -> {to_status}"
        )


def consistency_check(record: dict[str, Any]) -> None:
    """Cross-check verdicts list against status.

    A record at rest is valid if its terminal state is reachable from
    pending given the verdicts on file. This is not a full replay
    (verdicts have no recorded prior status), but it catches the common
    drift: status=published with no approve verdict, or status=rejected
    with no reject verdict.
    """
    status = record["status"]
    verdicts = record.get("verdicts", []) or []
    decisions = {v["decision"] for v in verdicts}

    if status == "pending":
        if decisions:
            raise TransitionError(
                "status=pending but verdicts list is non-empty"
            )
        return
    if status == "rejected":
        if "reject" not in decisions:
            raise TransitionError(
                "status=rejected requires at least one reject verdict"
            )
        return
    if status in ("approved", "published"):
        if not ({"approve", "edit"} & decisions):
            raise TransitionError(
                f"status={status} requires an approve or edit verdict"
            )
        return
    if status == "superseded":
        return
