"""State machine exercises."""
from __future__ import annotations

import pytest

from review_queue import state


def test_allowed_transitions() -> None:
    assert state.can_transition("pending", "approved")
    assert state.can_transition("pending", "rejected")
    assert state.can_transition("pending", "superseded")
    assert state.can_transition("approved", "published")
    assert state.can_transition("approved", "superseded")


def test_disallowed_transitions() -> None:
    assert not state.can_transition("pending", "published")
    assert not state.can_transition("rejected", "approved")
    assert not state.can_transition("published", "approved")
    assert not state.can_transition("superseded", "approved")


def test_assert_transition_raises_on_illegal_hop() -> None:
    with pytest.raises(state.TransitionError):
        state.assert_transition("pending", "published")


def test_consistency_check_pending_requires_empty_verdicts() -> None:
    rec = {"status": "pending", "verdicts": [
        {"reviewer": "a", "decided_at": "2026-08-14T13:00:00Z", "decision": "approve"}
    ]}
    with pytest.raises(state.TransitionError):
        state.consistency_check(rec)


def test_consistency_check_approved_requires_approve_or_edit_verdict() -> None:
    rec = {"status": "approved", "verdicts": []}
    with pytest.raises(state.TransitionError):
        state.consistency_check(rec)


def test_consistency_check_rejected_requires_reject_verdict() -> None:
    rec = {"status": "rejected", "verdicts": [
        {"reviewer": "a", "decided_at": "2026-08-14T13:00:00Z", "decision": "approve"}
    ]}
    with pytest.raises(state.TransitionError):
        state.consistency_check(rec)


def test_consistency_check_published_requires_approve_or_edit() -> None:
    rec = {
        "status": "published",
        "verdicts": [
            {"reviewer": "a", "decided_at": "2026-08-14T13:00:00Z", "decision": "approve"}
        ],
    }
    state.consistency_check(rec)


def test_consistency_check_pending_with_empty_verdicts_ok() -> None:
    state.consistency_check({"status": "pending", "verdicts": []})
