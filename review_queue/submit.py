"""submit: wrap a candidate in a typed promotion-record and land it in queue/."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from review_queue import diff as diff_mod
from review_queue import schema
from review_queue.records import Record, save


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _next_id(queue_dir: Path, today: str) -> str:
    """Allocate the next sequential id for `today`."""
    prefix = f"rec-{today}-"
    existing = []
    if queue_dir.exists():
        for p in queue_dir.glob(f"{prefix}*.md"):
            tail = p.stem.removeprefix(prefix)
            try:
                existing.append(int(tail))
            except ValueError:
                continue
    n = (max(existing) + 1) if existing else 1
    return f"{prefix}{n:03d}"


def submit(
    *,
    candidate_path: Path,
    provenance_ref: str,
    target: str,
    record_type: str,
    queue_dir: Path,
    target_path_for_diff: Path | None = None,
    record_id: str | None = None,
    now: str | None = None,
) -> Record:
    if not provenance_ref or not provenance_ref.strip():
        raise ValueError(
            "provenance_ref is required and must be non-empty. ReviewQueue refuses to enqueue a record without provenance."
        )
    if not candidate_path.exists():
        raise FileNotFoundError(f"candidate not found: {candidate_path}")

    now_iso = now or _now_iso()
    today = now_iso[:10]
    rid = record_id or _next_id(queue_dir, today)

    diff_text = diff_mod.diff_candidate_vs_target(candidate_path, target_path_for_diff)

    fm = {
        "id": rid,
        "record_type": record_type,
        "candidate_ref": str(candidate_path.as_posix()),
        "provenance_ref": provenance_ref,
        "diff": diff_text,
        "status": "pending",
        "target": target,
        "created_at": now_iso,
        "verdicts": [],
    }
    schema.validate(fm)

    body = (
        "# Candidate diff\n\n"
        "```diff\n"
        f"{diff_text}\n"
        "```\n"
    )
    record_path = queue_dir / f"{rid}.md"
    record = Record(fm=fm, body=body, path=record_path)
    save(record)
    return record
