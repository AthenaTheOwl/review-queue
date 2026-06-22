"""Read, write, and locate promotion-record files.

Records live as a single Markdown file with YAML front-matter:

    ---
    id: rec-2026-08-14-001
    status: pending
    ...
    ---

    # Candidate diff
    (unified diff body)

Queue location: queue/<id>.md
Decided location: decided/<id>.md
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from review_queue import frontmatter


@dataclass
class Record:
    fm: dict[str, Any]
    body: str
    path: Path

    @property
    def id(self) -> str:
        return self.fm["id"]

    @property
    def status(self) -> str:
        return self.fm["status"]


def load(path: Path) -> Record:
    text = path.read_text(encoding="utf-8")
    fm_text, body = frontmatter.split(text)
    fm = frontmatter.loads(fm_text)
    return Record(fm=fm, body=body, path=path)


def save(record: Record) -> None:
    record.path.parent.mkdir(parents=True, exist_ok=True)
    record.path.write_text(
        frontmatter.wrap(record.fm, record.body), encoding="utf-8"
    )


def iter_records(roots: Iterable[Path]) -> list[Record]:
    """Load every *.md record under each root that has a front-matter block."""
    out: list[Record] = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.glob("*.md")):
            try:
                out.append(load(p))
            except ValueError:
                continue
    return out


def find(record_id: str, search_roots: Iterable[Path]) -> Record | None:
    for root in search_roots:
        path = root / f"{record_id}.md"
        if path.exists():
            return load(path)
    return None
