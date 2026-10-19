"""End-to-end submit / decide / publish flows against a tmp repo root."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from review_queue import decide, publish, records, submit

# A reviewer's edit of the fixture candidate, as `decide --edit-diff` takes it.
EDIT_DIFF = (
    "--- examples/candidate.md\n"
    "+++ examples/candidate.md\n"
    "@@ -1,3 +1,3 @@\n"
    " # New memory\n"
    " \n"
    "-First calibration row.\n"
    "+First calibration row, edited by the reviewer.\n"
)
EDITED = b"# New memory\n\nFirst calibration row, edited by the reviewer.\n"


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
    # a plain approve covers the submitted bytes; no edited digest is recorded
    assert "approved_sha256" not in reloaded.fm


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
        edit_diff=EDIT_DIFF,
        search_roots=[queue_dir],
        now="2026-08-14T12:30:00Z",
    )
    reloaded = records.load(rec.path)
    # an edit verdict lands the record in `approved`, not `rejected`
    assert reloaded.fm["status"] == "approved"
    verdict = reloaded.fm["verdicts"][0]
    assert verdict["decision"] == "edit"
    assert verdict["edit_diff"] == EDIT_DIFF
    # the submitted digest stays for provenance; the edited bytes are what got approved
    assert reloaded.fm["candidate_sha256"] == rec.fm["candidate_sha256"]
    assert reloaded.fm["approved_sha256"] == hashlib.sha256(EDITED).hexdigest()


def test_decide_edit_refuses_diff_that_does_not_apply(repo: Path) -> None:
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/badedit", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    with pytest.raises(ValueError, match="does not match the candidate"):
        decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                      edit_diff="@@ -1 +1 @@\n-Not the first line\n+Replacement\n",
                      search_roots=[repo / "queue"])
    reloaded = records.load(rec.path)
    assert reloaded.fm["status"] == "pending"
    assert reloaded.fm["verdicts"] == []


def test_decide_edit_refuses_candidate_changed_before_verdict(repo: Path) -> None:
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/early", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    (repo / "examples" / "candidate.md").write_text("Unreviewed replacement\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since submission"):
        decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                      edit_diff=EDIT_DIFF, search_roots=[repo / "queue"])
    assert records.load(rec.path).fm["status"] == "pending"


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


def test_publish_blocks_candidate_changed_after_review(repo: Path) -> None:
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/changed", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    decide.decide(record_id=rec.fm["id"], decision="approve", reviewer="reviewer",
                  search_roots=[repo / "queue"])
    (repo / "examples" / "candidate.md").write_text("Unreviewed replacement\n", encoding="utf-8")
    with pytest.raises(publish.PublishError, match="changed since submission"):
        publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                        decided_dir=repo / "decided", repo_root=repo)
    assert not (repo / "out.md").exists()
    assert records.load(rec.path).fm["status"] == "approved"


def test_publish_requires_digest_on_legacy_approval(repo: Path) -> None:
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/legacy", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    rec.fm.pop("candidate_sha256", None)
    records.save(rec)
    decide.decide(record_id=rec.fm["id"], decision="approve", reviewer="reviewer",
                  search_roots=[repo / "queue"])
    with pytest.raises(publish.PublishError, match="digest missing"):
        publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                        decided_dir=repo / "decided", repo_root=repo)
    assert not (repo / "out.md").exists()
    assert records.load(rec.path).fm["status"] == "approved"


def test_published_bytes_equal_the_submitted_bytes(repo: Path) -> None:
    content = b"# Candidate\r\n\r\nExact bytes.\r\n"
    candidate = repo / "examples" / "candidate.md"
    candidate.write_bytes(content)
    rec = submit.submit(candidate_path=candidate, provenance_ref="trace://test/run/bytes",
                        target="file://./out.md", record_type="test-case", queue_dir=repo / "queue")
    decide.decide(record_id=rec.fm["id"], decision="approve", reviewer="reviewer",
                  search_roots=[repo / "queue"])
    publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                    decided_dir=repo / "decided", repo_root=repo)
    assert (repo / "out.md").read_bytes() == content


def test_publish_after_edit_writes_the_edited_bytes(repo: Path) -> None:
    candidate = repo / "examples" / "candidate.md"
    submitted = candidate.read_bytes()
    rec = submit.submit(candidate_path=candidate, provenance_ref="trace://test/run/edit",
                        target="file://./out.md", record_type="test-case", queue_dir=repo / "queue")
    decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                  edit_diff=EDIT_DIFF, search_roots=[repo / "queue"])
    published = publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                                decided_dir=repo / "decided", repo_root=repo)
    assert (repo / "out.md").read_bytes() == EDITED
    assert published.fm["status"] == "published"
    # the source stays the submitted candidate; only the target carries the edit
    assert candidate.read_bytes() == submitted


def test_publish_blocks_candidate_changed_after_edit_verdict(repo: Path) -> None:
    # Same rule as a plain approve: the edit was approved against the
    # submitted bytes, so a changed source (even one carrying the edit) stops publication.
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/edit-changed", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                  edit_diff=EDIT_DIFF, search_roots=[repo / "queue"])
    (repo / "examples" / "candidate.md").write_bytes(EDITED)
    with pytest.raises(publish.PublishError, match="changed since submission"):
        publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                        decided_dir=repo / "decided", repo_root=repo)
    assert not (repo / "out.md").exists()
    assert records.load(rec.path).fm["status"] == "approved"


def test_publish_refuses_edit_verdict_without_edited_digest(repo: Path) -> None:
    # An edit recorded before decide captured the edited digest must not
    # ship the pre-edit bytes.
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/edit-legacy", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                  edit_diff=EDIT_DIFF, search_roots=[repo / "queue"])
    rec = records.load(rec.path)
    rec.fm.pop("approved_sha256")
    records.save(rec)
    with pytest.raises(publish.PublishError, match="edited candidate digest missing"):
        publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                        decided_dir=repo / "decided", repo_root=repo)
    assert not (repo / "out.md").exists()
    assert records.load(rec.path).fm["status"] == "approved"


def test_publish_refuses_edit_that_does_not_reproduce_approved_digest(repo: Path) -> None:
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/edit-tamper", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                  edit_diff=EDIT_DIFF, search_roots=[repo / "queue"])
    rec = records.load(rec.path)
    rec.fm["approved_sha256"] = "f" * 64
    records.save(rec)
    with pytest.raises(publish.PublishError, match="does not match approved_sha256"):
        publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                        decided_dir=repo / "decided", repo_root=repo)
    assert not (repo / "out.md").exists()


def test_legacy_edit_without_digests_is_recorded_but_not_published(repo: Path) -> None:
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/legacy-edit", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    rec.fm.pop("candidate_sha256")
    records.save(rec)
    decided = decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                            edit_diff="@@ scope @@\n-free text\n+as older records hold it\n",
                            search_roots=[repo / "queue"])
    assert decided.fm["status"] == "approved"
    assert "approved_sha256" not in decided.fm
    with pytest.raises(publish.PublishError, match="candidate digest missing"):
        publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                        decided_dir=repo / "decided", repo_root=repo)
    assert not (repo / "out.md").exists()


@pytest.mark.parametrize("strip_final_newline", [False, True])
def test_crlf_candidate_edit_survives_save_and_publishes(repo: Path, strip_final_newline: bool) -> None:
    # `diff -u` on a CRLF candidate yields a CRLF edit diff; the record must stay readable.
    # `--edit-diff "$(cat e.diff)"` strips the final "\n" and leaves the last "\r".
    candidate = repo / "examples" / "crlf.md"
    candidate.write_bytes(b"alpha\r\nbeta\r\n")
    crlf_diff = "--- crlf.md\r\n+++ edited.md\r\n@@ -1,2 +1,2 @@\r\n alpha\r\n-beta\r\n+BETA\r\n"
    if strip_final_newline:
        crlf_diff = crlf_diff.removesuffix("\n")
    rec = submit.submit(candidate_path=candidate, provenance_ref="trace://test/run/crlf",
                        target="file://./out.md", record_type="test-case", queue_dir=repo / "queue")
    decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                  edit_diff=crlf_diff, search_roots=[repo / "queue"])
    reloaded = records.load(rec.path)
    assert reloaded.fm["verdicts"][0]["edit_diff"] == crlf_diff
    assert [r.fm["id"] for r in records.iter_records([repo / "queue"])] == [rec.fm["id"]]
    publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                    decided_dir=repo / "decided", repo_root=repo)
    assert (repo / "out.md").read_bytes() == b"alpha\nBETA\n"


def test_publish_refuses_an_edit_diff_that_no_longer_applies(repo: Path) -> None:
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/edit-broken", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                  edit_diff=EDIT_DIFF, search_roots=[repo / "queue"])
    rec = records.load(rec.path)
    rec.fm["verdicts"][-1]["edit_diff"] = "@@ -1 +1 @@\n-Not the first line\n+Replacement\n"
    records.save(rec)
    with pytest.raises(publish.PublishError, match="edit no longer applies"):
        publish.publish(record_id=rec.fm["id"], queue_dir=repo / "queue",
                        decided_dir=repo / "decided", repo_root=repo)
    assert not (repo / "out.md").exists()
    assert records.load(rec.path).fm["status"] == "approved"


def test_decide_edit_refuses_a_missing_candidate(repo: Path) -> None:
    rec = submit.submit(candidate_path=repo / "examples" / "candidate.md",
                        provenance_ref="trace://test/run/edit-gone", target="file://./out.md",
                        record_type="test-case", queue_dir=repo / "queue")
    (repo / "examples" / "candidate.md").unlink()
    with pytest.raises(FileNotFoundError, match="candidate file missing"):
        decide.decide(record_id=rec.fm["id"], decision="edit", reviewer="reviewer",
                      edit_diff=EDIT_DIFF, search_roots=[repo / "queue"])
    reloaded = records.load(rec.path)
    assert reloaded.fm["status"] == "pending"
    assert reloaded.fm["verdicts"] == []


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
