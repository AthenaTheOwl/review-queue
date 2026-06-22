"""publish: resolve an approved record's target and ship the candidate."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from review_queue import state
from review_queue.records import Record, find, save


class PublishError(RuntimeError):
    pass


def _resolve_file_target(uri: str, repo_root: Path) -> Path:
    body = uri[len("file://"):]
    if body.startswith("/"):
        return Path(body)
    if body.startswith("./"):
        return (repo_root / body[2:]).resolve()
    return (repo_root / body).resolve()


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
        candidate_ref = record.fm["candidate_ref"]
        candidate_path = (repo_root / candidate_ref).resolve()
        if not candidate_path.exists():
            raise PublishError(f"candidate file missing: {candidate_path}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(candidate_path.read_text(encoding="utf-8"), encoding="utf-8")
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
