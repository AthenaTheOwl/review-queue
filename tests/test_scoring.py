"""Tests for score/ledger/report modules."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from review_queue import ledger as ledger_mod
from review_queue import records as records_mod
from review_queue import report as report_mod
from review_queue import score as score_mod


def _make_record(
    rid: str,
    *,
    record_type: str = "memory-update",
    status: str = "published",
    decision: str = "approve",
    created_at: str = "2026-08-14T12:00:00Z",
    decided_at: str = "2026-08-14T12:30:00Z",
    provenance: str = "trace://athena-site/event-log/x.jsonl#evt-1",
    tmp_path: Path | None = None,
) -> records_mod.Record:
    fm = {
        "id": rid,
        "record_type": record_type,
        "candidate_ref": f"examples/candidates/{rid}.md",
        "provenance_ref": provenance,
        "diff": "",
        "status": status,
        "target": f"file://out/{rid}.md",
        "created_at": created_at,
        "verdicts": [
            {
                "reviewer": "vignesh",
                "decided_at": decided_at,
                "decision": decision,
            }
        ],
    }
    path = (tmp_path or Path(".")) / f"{rid}.md"
    return records_mod.Record(fm=fm, body="", path=path)


def test_score_empty_set_returns_zero_sample_count() -> None:
    out = score_mod.score_records([])
    assert out["sample_count"] == 0
    assert out["approve_unchanged_rate"] == 0.0
    assert out["median_latency_seconds"] is None


def test_score_single_approve_row() -> None:
    r = _make_record("rec-1")
    out = score_mod.score_records([r], record_type="memory-update")
    assert out["sample_count"] == 1
    assert out["approve_unchanged_rate"] == 1.0
    assert out["edit_rate"] == 0.0
    assert out["reject_rate"] == 0.0
    assert out["median_latency_seconds"] == 1800
    assert out["records"] == ["rec-1"]


def test_score_min_and_max_latency_are_distinct() -> None:
    rows = [
        _make_record(
            "rec-fast",
            created_at="2026-08-14T12:00:00Z",
            decided_at="2026-08-14T12:10:00Z",  # 600s
        ),
        _make_record(
            "rec-slow",
            created_at="2026-08-14T12:00:00Z",
            decided_at="2026-08-14T12:30:00Z",  # 1800s
        ),
    ]
    out = score_mod.score_records(rows, record_type="memory-update")
    assert out["sample_count"] == 2
    # min and max must not be swapped
    assert out["min_latency_seconds"] == 600
    assert out["max_latency_seconds"] == 1800


def test_score_mixed_rows() -> None:
    rows = [
        _make_record("rec-a", decision="approve"),
        _make_record("rec-b", decision="edit"),
        _make_record("rec-c", decision="reject"),
        _make_record("rec-d", decision="approve"),
    ]
    out = score_mod.score_records(rows, record_type="memory-update")
    assert out["sample_count"] == 4
    assert out["approve_unchanged_rate"] == 0.5
    assert out["edit_rate"] == 0.25
    assert out["reject_rate"] == 0.25


def test_score_excludes_pending_rows() -> None:
    rows = [
        _make_record("rec-pending", status="pending"),
        _make_record("rec-pub", status="published"),
    ]
    out = score_mod.score_records(rows)
    assert out["sample_count"] == 1
    assert out["records"] == ["rec-pub"]


def test_score_excludes_unknown_provenance_scheme() -> None:
    rows = [_make_record("rec-x", provenance="http://example.com")]
    out = score_mod.score_records(rows)
    assert out["sample_count"] == 0


def test_score_excludes_under_10s_latency() -> None:
    rows = [
        _make_record(
            "rec-fast",
            created_at="2026-08-14T12:00:00Z",
            decided_at="2026-08-14T12:00:05Z",
        ),
    ]
    out = score_mod.score_records(rows)
    assert out["sample_count"] == 0


def test_score_record_type_filter() -> None:
    rows = [
        _make_record("rec-m", record_type="memory-update"),
        _make_record("rec-c", record_type="contract-clause"),
    ]
    out = score_mod.score_records(rows, record_type="memory-update")
    assert out["sample_count"] == 1
    assert out["records"] == ["rec-m"]


def test_auto_promote_eligibility() -> None:
    assert not score_mod.is_auto_promote_eligible(
        {"sample_count": 1, "approve_unchanged_rate": 1.0}
    )
    assert not score_mod.is_auto_promote_eligible(
        {"sample_count": 20, "approve_unchanged_rate": 0.94}
    )
    assert score_mod.is_auto_promote_eligible(
        {"sample_count": 20, "approve_unchanged_rate": 0.95}
    )


def test_ledger_append_and_read(tmp_path: Path) -> None:
    ledger_path = tmp_path / "runs.jsonl"
    score_dict = {
        "record_type": "memory-update",
        "sample_count": 3,
        "approve_unchanged_rate": 0.67,
        "edit_rate": 0.33,
        "reject_rate": 0.0,
        "median_latency_seconds": 900,
        "min_latency_seconds": 600,
        "max_latency_seconds": 1200,
        "records": ["rec-1", "rec-2", "rec-3"],
    }
    row = ledger_mod.append_run(
        ledger_path,
        score_dict,
        threshold=score_mod.AUTO_PROMOTE_THRESHOLD,
        now="2026-09-01T12:00:00Z",
    )
    assert row["run_id"] == "run-2026-09-01-001"
    assert row["auto_promote_eligible"] is False

    rows = ledger_mod.read_runs(ledger_path)
    assert len(rows) == 1
    assert rows[0]["sample_count"] == 3


def test_ledger_append_assigns_sequential_ids(tmp_path: Path) -> None:
    ledger_path = tmp_path / "runs.jsonl"
    s = {"record_type": "x", "sample_count": 0}
    a = ledger_mod.append_run(ledger_path, s, now="2026-09-01T12:00:00Z")
    b = ledger_mod.append_run(ledger_path, s, now="2026-09-01T13:00:00Z")
    assert a["run_id"] == "run-2026-09-01-001"
    assert b["run_id"] == "run-2026-09-01-002"


def test_report_format_run_contains_expected_fields() -> None:
    row = {
        "run_id": "run-2026-09-01-001",
        "scored_at": "2026-09-01T12:00:00Z",
        "record_type": "memory-update",
        "sample_count": 4,
        "approve_unchanged_rate": 0.75,
        "edit_rate": 0.25,
        "reject_rate": 0.0,
        "median_latency_seconds": 900,
        "records": ["rec-a", "rec-b"],
        "auto_promote_eligible": False,
        "auto_promote_threshold": score_mod.AUTO_PROMOTE_THRESHOLD,
    }
    out = report_mod.format_run(row)
    assert "run-2026-09-01-001" in out
    assert "75.0%" in out
    assert "memory-update" in out
    assert "rec-a" in out


def test_report_format_empty_ledger() -> None:
    assert report_mod.format_report([]) == "(no scoring runs in ledger)"


def test_checked_in_ledger_row_is_valid_json() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ledger_path = repo_root / "data" / "ledger" / "runs.jsonl"
    assert ledger_path.exists(), "data/ledger/runs.jsonl must be checked in"
    rows = ledger_mod.read_runs(ledger_path)
    assert len(rows) >= 1
    first = rows[0]
    assert first["record_type"] == "memory-update"
    assert first["sample_count"] == 1
    assert first["approve_unchanged_rate"] == 1.0
    assert "rec-2026-08-14-001" in first["records"]
