"""End-to-end submit / decide / publish flows against a tmp repo root."""
from __future__ import annotations

from pathlib import Path

import pytest

from review_queue import decide, publish, records, submit


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "queue").mkdir()
    (tmp_path / "decided").mkdir()
    (tmp_path / "examples").mkdir()
    candidate = tmp_path / "examples" / "candidate.md"
    candidate.write_text("# New memory\n\nFirst calibration row.\n", encoding="utf-8")
    return tmp_path


def test_submit_writes_pending_record(repo: Path) -> None:
    queue_dir = repo / "queue"
    rec = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/1",
        target="file://./out.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:00:00Z",
    )
    assert rec.fm["status"] == "pending"
    assert rec.fm["id"].startswith("rec-2026-08-14-")
    assert rec.path.exists()
    reloaded = records.load(rec.path)
    assert reloaded.fm["id"] == rec.fm["id"]


def test_submit_next_id_increments_for_same_day(repo: Path) -> None:
    queue_dir = repo / "queue"
    first = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/1",
        target="file://./out.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:00:00Z",
    )
    second = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/2",
        target="file://./out.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:05:00Z",
    )
    assert first.fm["id"] == "rec-2026-08-14-001"
    assert second.fm["id"] == "rec-2026-08-14-002"


def test_submit_next_id_uses_max_not_count(repo: Path) -> None:
    # A gapped queue distinguishes max(existing)+1 from len(existing)+1.
    queue_dir = repo / "queue"
    (queue_dir / "rec-2026-08-14-005.md").write_text("seed\n", encoding="utf-8")
    rec = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/1",
        target="file://./out.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:00:00Z",
    )
    assert rec.fm["id"] == "rec-2026-08-14-006"


def test_submit_refuses_empty_provenance(repo: Path) -> None:
    with pytest.raises(ValueError):
        submit.submit(
            candidate_path=repo / "examples" / "candidate.md",
            provenance_ref="",
            target="file://./out.md",
            record_type="memory-update",
            queue_dir=repo / "queue",
        )


def test_submit_refuses_non_uri_provenance(repo: Path) -> None:
    with pytest.raises(Exception):
        submit.submit(
            candidate_path=repo / "examples" / "candidate.md",
            provenance_ref="not-a-uri",
            target="file://./out.md",
            record_type="memory-update",
            queue_dir=repo / "queue",
        )


def test_decide_appends_verdict_and_flips_status(repo: Path) -> None:
    queue_dir = repo / "queue"
    rec = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/1",
        target="file://./out.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:00:00Z",
    )
    decide.decide(
        record_id=rec.fm["id"],
        decision="approve",
        reviewer="vignesh",
        search_roots=[queue_dir],
        now="2026-08-14T12:30:00Z",
    )
    reloaded = records.load(rec.path)
    assert reloaded.fm["status"] == "approved"
    assert len(reloaded.fm["verdicts"]) == 1
    assert reloaded.fm["verdicts"][0]["reviewer"] == "vignesh"


def test_decide_edit_verdict_approves_and_carries_diff(repo: Path) -> None:
    queue_dir = repo / "queue"
    rec = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/1",
        target="file://./out.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:00:00Z",
    )
    decide.decide(
        record_id=rec.fm["id"],
        decision="edit",
        reviewer="vignesh",
        edit_diff="- old line\n+ new line\n",
        search_roots=[queue_dir],
        now="2026-08-14T12:30:00Z",
    )
    reloaded = records.load(rec.path)
    # an edit verdict lands the record in `approved`, not `rejected`
    assert reloaded.fm["status"] == "approved"
    verdict = reloaded.fm["verdicts"][0]
    assert verdict["decision"] == "edit"
    assert verdict["edit_diff"] == "- old line\n+ new line\n"


def test_decide_refuses_illegal_transition(repo: Path) -> None:
    queue_dir = repo / "queue"
    rec = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/1",
        target="file://./out.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:00:00Z",
    )
    decide.decide(
        record_id=rec.fm["id"],
        decision="reject",
        reviewer="vignesh",
        search_roots=[queue_dir],
        now="2026-08-14T12:30:00Z",
    )
    with pytest.raises(Exception):
        decide.decide(
            record_id=rec.fm["id"],
            decision="approve",
            reviewer="vignesh",
            search_roots=[queue_dir],
            now="2026-08-14T13:00:00Z",
        )


def test_publish_writes_target_and_moves_record(repo: Path) -> None:
    queue_dir = repo / "queue"
    decided_dir = repo / "decided"
    rec = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/1",
        target="file://./out.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:00:00Z",
    )
    decide.decide(
        record_id=rec.fm["id"],
        decision="approve",
        reviewer="vignesh",
        search_roots=[queue_dir],
        now="2026-08-14T12:30:00Z",
    )
    published = publish.publish(
        record_id=rec.fm["id"],
        queue_dir=queue_dir,
        decided_dir=decided_dir,
        repo_root=repo,
    )
    assert published.fm["status"] == "published"
    assert not (queue_dir / f"{rec.fm['id']}.md").exists()
    assert (decided_dir / f"{rec.fm['id']}.md").exists()
    assert (repo / "out.md").exists()
    assert "New memory" in (repo / "out.md").read_text(encoding="utf-8")


def test_publish_refuses_repo_target(repo: Path) -> None:
    queue_dir = repo / "queue"
    decided_dir = repo / "decided"
    rec = submit.submit(
        candidate_path=repo / "examples" / "candidate.md",
        provenance_ref="trace://test/run/1",
        target="repo://athena-site/memory/MEMORY.md",
        record_type="memory-update",
        queue_dir=queue_dir,
        now="2026-08-14T12:00:00Z",
    )
    decide.decide(
        record_id=rec.fm["id"],
        decision="approve",
        reviewer="vignesh",
        search_roots=[queue_dir],
        now="2026-08-14T12:30:00Z",
    )
    with pytest.raises(publish.PublishError):
        publish.publish(
            record_id=rec.fm["id"],
            queue_dir=queue_dir,
            decided_dir=decided_dir,
            repo_root=repo,
        )
