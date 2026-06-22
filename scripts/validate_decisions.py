"""validate_decisions: every file under decisions/ is a Markdown file
with a DEC-RQ-NNN-<slug>.md name and a non-empty body.

Decisions are governance artifacts, not typed records. The check is
deliberately light: a filename pattern and a presence-of-content
assertion. Stronger structure can land later if drift becomes a
problem.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEC_RE = re.compile(r"^DEC-RQ-\d{3,}-[a-z0-9][a-z0-9-]*\.md$")
REQUIRED_HEADINGS = ("# DEC-RQ-", "## Context", "## Decision")


def main() -> int:
    decisions_dir = REPO_ROOT / "decisions"
    if not decisions_dir.exists():
        print("no decisions/ directory; nothing to check")
        return 0
    files = sorted(decisions_dir.glob("*.md"))
    if not files:
        print("no decision files found")
        return 0
    failures: list[str] = []
    for path in files:
        name = path.name
        if not DEC_RE.match(name):
            failures.append(
                f"{name}: filename must match DEC-RQ-NNN-<slug>.md"
            )
            continue
        text = path.read_text(encoding="utf-8")
        if len(text.strip()) < 50:
            failures.append(f"{name}: body is suspiciously short")
            continue
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                failures.append(f"{name}: missing heading {heading!r}")
        print(f"ok   {name}")
    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
