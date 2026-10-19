"""Schema validator exercises."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from review_queue import schema

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "promotion-record.schema.json"


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


def test_approved_digest_is_optional_and_needs_the_submitted_digest() -> None:
    r = _valid_record()
    r["candidate_sha256"] = "0" * 64
    r["approved_sha256"] = "f" * 64
    schema.validate(r)
    del r["candidate_sha256"]
    with pytest.raises(schema.SchemaError, match="approved_sha256 requires candidate_sha256"):
        schema.validate(r)


@pytest.mark.parametrize("digest", ["NOT-A-DIGEST", "A" * 64, "0" * 63, "", None, 123])
def test_malformed_approved_digest_fails(digest) -> None:
    r = _valid_record()
    r["candidate_sha256"] = "0" * 64
    r["approved_sha256"] = digest
    with pytest.raises(schema.SchemaError, match="approved_sha256"):
        schema.validate(r)


@pytest.mark.parametrize(
    "fields, ok",
    [
        ({}, True),
        ({"candidate_sha256": "0" * 64}, True),
        ({"candidate_sha256": "0" * 64, "approved_sha256": "f" * 64}, True),
        ({"candidate_sha256": "A" * 64}, False),
        ({"candidate_sha256": "0" * 64, "approved_sha256": "nope"}, False),
        ({"approved_sha256": "f" * 64}, False),
    ],
)
def test_digest_rules_match_the_json_schema(fields: dict, ok: bool) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    r = {**_valid_record(), **fields}
    assert validator.is_valid(r) is ok
    if ok:
        schema.validate(r)
    else:
        with pytest.raises(schema.SchemaError):
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
