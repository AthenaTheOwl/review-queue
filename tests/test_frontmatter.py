"""Front-matter parser exercises."""
from __future__ import annotations

import pytest

from review_queue import frontmatter


SAMPLE = """---
id: rec-2026-08-14-001
record_type: memory-update
candidate_ref: examples/candidates/mem-2026-08-14.md
provenance_ref: trace://athena-site/ops/event-log/2026-08-14.jsonl#evt-42
diff: "--- /dev/null\\n+++ examples/mem.md\\n"
status: pending
target: "file://docs/memory/scoring.md"
created_at: 2026-08-14T12:34:56Z
verdicts: []
---

body line one
body line two
"""


def test_split_returns_frontmatter_and_body() -> None:
    fm, body = frontmatter.split(SAMPLE)
    assert "id: rec-2026-08-14-001" in fm
    assert "body line one" in body


def test_split_rejects_missing_fm() -> None:
    with pytest.raises(ValueError):
        frontmatter.split("no front matter here")


def test_loads_scalar_fields() -> None:
    fm_text, _ = frontmatter.split(SAMPLE)
    fm = frontmatter.loads(fm_text)
    assert fm["id"] == "rec-2026-08-14-001"
    assert fm["record_type"] == "memory-update"
    assert fm["status"] == "pending"
    assert fm["verdicts"] == []


def test_loads_quoted_string_preserves_escapes() -> None:
    fm_text, _ = frontmatter.split(SAMPLE)
    fm = frontmatter.loads(fm_text)
    assert "--- /dev/null" in fm["diff"]


def test_loads_block_list_of_mappings() -> None:
    text = """id: rec-2026-08-14-001
verdicts:
  - reviewer: vignesh
    decided_at: 2026-08-14T13:01:12Z
    decision: approve
"""
    fm = frontmatter.loads(text)
    assert len(fm["verdicts"]) == 1
    assert fm["verdicts"][0]["reviewer"] == "vignesh"
    assert fm["verdicts"][0]["decision"] == "approve"


def test_dumps_roundtrip_preserves_scalars() -> None:
    data = {
        "id": "rec-2026-08-14-001",
        "status": "pending",
        "verdicts": [],
    }
    rendered = frontmatter.dumps(data)
    assert "id: rec-2026-08-14-001" in rendered
    assert "verdicts: []" in rendered


def test_wrap_renders_record_file() -> None:
    out = frontmatter.wrap({"id": "rec-2026-08-14-001", "verdicts": []}, "hello\n")
    assert out.startswith("---\n")
    assert "id: rec-2026-08-14-001" in out
    assert out.endswith("hello\n")
