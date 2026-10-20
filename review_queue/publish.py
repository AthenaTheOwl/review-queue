"""publish: resolve an approved record's target and ship the candidate."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from review_queue import diff as diff_mod
from review_queue import state
from review_queue.records import Record, find, save


class PublishError(RuntimeError):
    pass


# An edit verdict without a pinned edited digest is not an approval of any
# bytes (DEC-RQ-002). Publishing it fails closed and asks for a fresh review.
LEGACY_EDIT_REFUSAL = (
    "edited candidate digest missing: this edit verdict was recorded without "
    "approved_sha256, so it approves no pinned bytes and is treated as not approved; "
    "resubmit the candidate and have the reviewer re-review it"
)


def _resolve_file_target(uri: str, repo_root: Path) -> Path:
    body = uri[len("file://"):]
    if body.startswith("/"):
        return Path(body)
    if body.startswith("./"):
        return (repo_root / body[2:]).resolve()
    return (repo_root / body).resolve()


def _approved_bytes(record: Record, repo_root: Path) -> bytes:
    """Read the candidate once and return exactly the bytes the verdict approved.

    A plain approve covers the submitted bytes. An edit covers the edited
    candidate (R-RQ-007): the edit is re-applied to the verified submitted
    bytes and the result must match the digest decide recorded.

    An edit verdict with no recorded `approved_sha256` (one recorded before
    edits were pinned, or on a record without `candidate_sha256`) approves
    no pinned bytes. It is treated as not approved and refused before any
    file is read (DEC-RQ-002): the reviewer re-reviews a resubmitted candidate.
    """
    approving = [v for v in record.fm.get("verdicts") or [] if v.get("decision") in ("approve", "edit")]
    is_edit = bool(approving) and approving[-1]["decision"] == "edit"
    if is_edit and not record.fm.get("approved_sha256"):
        raise PublishError(LEGACY_EDIT_REFUSAL)

    candidate_ref = record.fm["candidate_ref"]
    candidate_path = (repo_root / candidate_ref).resolve()
    if not candidate_path.exists():
        raise PublishError(f"candidate file missing: {candidate_path}")
    expected = record.fm.get("candidate_sha256")
    if not expected:
        raise PublishError("candidate digest missing; resubmit the legacy candidate and review the new record")
    candidate_bytes = candidate_path.read_bytes()
    if hashlib.sha256(candidate_bytes).hexdigest() != expected:
        raise PublishError("candidate changed since submission; resubmit it for review")

    if not is_edit:
        return candidate_bytes
    approved = record.fm["approved_sha256"]
    try:
        edited = diff_mod.apply_edit(candidate_bytes, approving[-1].get("edit_diff") or "")
    except diff_mod.PatchError as exc:
        raise PublishError(f"edit no longer applies to the candidate: {exc}") from exc
    if hashlib.sha256(edited).hexdigest() != approved:
        raise PublishError("edited candidate does not match approved_sha256; resubmit it for review")
    return edited


def publish(
    *,
    record_id: str,
    queue_dir: Path,
    decided_dir: Path,
    repo_root: Path,
    search_roots: Iterable[Path] | None = None,
) -> Record:
    roots = list(search_roots) if search_roots else [queue_dir]
    record = find(record_id, roots)
    if record is None:
        raise FileNotFoundError(f"record not found: {record_id}")

    if record.fm["status"] != "approved":
        raise PublishError(
            f"publish requires status=approved, got {record.fm['status']!r}"
        )

    target = record.fm["target"]
    if target.startswith("file://"):
        dest = _resolve_file_target(target, repo_root)
        approved_bytes = _approved_bytes(record, repo_root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(approved_bytes)
    elif target.startswith("repo://"):
        raise PublishError(
            "repo:// target publish is not wired in v0; see STATUS.md known limits"
        )
    else:
        raise PublishError(f"unsupported target scheme: {target!r}")

    state.assert_transition(record.fm["status"], "published")
    record.fm["status"] = "published"

    decided_path = decided_dir / f"{record.fm['id']}.md"
    record.path = decided_path
    save(record)

    old = queue_dir / f"{record.fm['id']}.md"
    if old.exists() and old != decided_path:
        old.unlink()

    return record
