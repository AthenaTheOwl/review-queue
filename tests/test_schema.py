"""Schema validator exercises."""
from __future__ import annotations

import pytest

from review_queue import schema


def _valid_record() -> dict:
    return {
        "id": "rec-2026-08-14-001",
        "record_type": "memory-update",
        "candidate_ref": "examples/candidates/mem.md",
        "provenance_ref": "trace://athena-site/ops/event-log/2026-08-14.jsonl#evt-42",
        "diff": "--- a\n+++ b\n",
        "status": "pending",
        "target": "file://docs/memory/scoring.md",
        "created_at": "2026-08-14T12:34:56Z",
        "verdicts": [],
    }


def test_valid_record_passes() -> None:
    schema.validate(_valid_record())


def test_missing_required_field_fails() -> None:
    r = _valid_record()
    del r["provenance_ref"]
    with pytest.raises(schema.SchemaError):
        schema.validate(r)


def test_empty_provenance_fails() -> None:
    r = _valid_record()
    r["provenance_ref"] = ""
    with pytest.raises(schema.SchemaError):
        schema.validate(r)


def test_non_uri_provenance_fails() -> None:
    r = _valid_record()
    r["provenance_ref"] = "just-some-string"
    with pytest.raises(schema.SchemaError):
        schema.validate(r)


def test_bad_status_fails() -> None:
    r = _valid_record()
    r["status"] = "queued"
    with pytest.raises(schema.SchemaError):
        schema.validate(r)


def test_bad_target_scheme_fails() -> None:
    r = _valid_record()
    r["target"] = "https://example.com/foo.md"
    with pytest.raises(schema.SchemaError):
        schema.validate(r)


def test_bad_id_format_fails() -> None:
    r = _valid_record()
    r["id"] = "rec-bad"
    with pytest.raises(schema.SchemaError):
        schema.validate(r)


def test_candidate_digest_is_optional() -> None:
    r = _valid_record()
    assert "candidate_sha256" not in r
    schema.validate(r)
    r["candidate_sha256"] = "0" * 64
    schema.validate(r)


@pytest.mark.parametrize(
    "digest", ["NOT-A-DIGEST", "F65A9BA6", "A" * 64, "0" * 63, "", None, 123]
)
def test_malformed_candidate_digest_fails(digest) -> None:
    r = _valid_record()
    r["candidate_sha256"] = digest
    with pytest.raises(schema.SchemaError, match="candidate_sha256"):
        schema.validate(r)


def test_verdict_decision_validated() -> None:
    r = _valid_record()
    r["status"] = "approved"
    r["verdicts"] = [
        {
            "reviewer": "vignesh",
            "decided_at": "2026-08-14T13:00:00Z",
            "decision": "approve",
        }
    ]
    schema.validate(r)


def test_edit_verdict_requires_edit_diff() -> None:
    r = _valid_record()
    r["status"] = "approved"
    r["verdicts"] = [
        {
            "reviewer": "vignesh",
            "decided_at": "2026-08-14T13:00:00Z",
            "decision": "edit",
        }
    ]
    with pytest.raises(schema.SchemaError):
        schema.validate(r)
