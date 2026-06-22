"""In-code schema validation for promotion-record front-matter.

We avoid jsonschema as a runtime dependency. The constraints encoded
here mirror schemas/promotion-record.schema.json — that file remains
the contract surface; this module is its executable shadow.
"""
from __future__ import annotations

import re
from typing import Any

ALLOWED_STATUSES = {"pending", "approved", "rejected", "published", "superseded"}
ALLOWED_DECISIONS = {"approve", "reject", "edit"}
KNOWN_RECORD_TYPES = {
    "memory-update",
    "test-case",
    "skill",
    "brief",
    "contract-clause",
    "post",
}

REQUIRED_FIELDS = (
    "id",
    "record_type",
    "candidate_ref",
    "provenance_ref",
    "diff",
    "status",
    "target",
    "created_at",
)

ID_RE = re.compile(r"^rec-\d{4}-\d{2}-\d{2}-\d{3,}$")
PROVENANCE_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://")
TARGET_RE = re.compile(r"^(file|repo)://")
ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:?\d{2})$"
)


class SchemaError(ValueError):
    """Raised when a record fails schema validation."""


def validate(record: dict[str, Any]) -> None:
    """Raise SchemaError on any violation. Return None on success."""
    for field in REQUIRED_FIELDS:
        if field not in record:
            raise SchemaError(f"missing required field: {field}")

    rid = record["id"]
    if not isinstance(rid, str) or not ID_RE.match(rid):
        raise SchemaError(f"id does not match rec-YYYY-MM-DD-NNN: {rid!r}")

    rt = record["record_type"]
    if not isinstance(rt, str) or not rt:
        raise SchemaError("record_type must be a non-empty string")

    cref = record["candidate_ref"]
    if not isinstance(cref, str) or not cref:
        raise SchemaError("candidate_ref must be a non-empty string")

    pref = record["provenance_ref"]
    if not isinstance(pref, str) or not pref.strip():
        raise SchemaError("provenance_ref must be a non-empty URI-shaped string")
    if not PROVENANCE_RE.match(pref):
        raise SchemaError(f"provenance_ref must be URI-shaped: {pref!r}")

    diff = record["diff"]
    if not isinstance(diff, str):
        raise SchemaError("diff must be a string")

    status = record["status"]
    if status not in ALLOWED_STATUSES:
        raise SchemaError(
            f"status must be one of {sorted(ALLOWED_STATUSES)}, got {status!r}"
        )

    target = record["target"]
    if not isinstance(target, str) or not TARGET_RE.match(target):
        raise SchemaError(f"target must start with file:// or repo://: {target!r}")

    created = record["created_at"]
    if not isinstance(created, str) or not ISO_RE.match(created):
        raise SchemaError(f"created_at must be ISO 8601: {created!r}")

    verdicts = record.get("verdicts", [])
    if not isinstance(verdicts, list):
        raise SchemaError("verdicts must be a list")
    for i, v in enumerate(verdicts):
        _validate_verdict(v, i)


def _validate_verdict(v: Any, idx: int) -> None:
    if not isinstance(v, dict):
        raise SchemaError(f"verdict[{idx}] must be a mapping")
    for field in ("reviewer", "decided_at", "decision"):
        if field not in v:
            raise SchemaError(f"verdict[{idx}] missing field: {field}")
    if not isinstance(v["reviewer"], str) or not v["reviewer"]:
        raise SchemaError(f"verdict[{idx}].reviewer must be non-empty string")
    if not isinstance(v["decided_at"], str) or not ISO_RE.match(v["decided_at"]):
        raise SchemaError(f"verdict[{idx}].decided_at must be ISO 8601")
    if v["decision"] not in ALLOWED_DECISIONS:
        raise SchemaError(
            f"verdict[{idx}].decision must be one of {sorted(ALLOWED_DECISIONS)}, "
            f"got {v['decision']!r}"
        )
    if v["decision"] == "edit" and not v.get("edit_diff"):
        raise SchemaError(f"verdict[{idx}] with decision=edit must include edit_diff")
