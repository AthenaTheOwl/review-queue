"""Diff helpers. v0 supports unified text diffs only."""
from __future__ import annotations

import difflib


def unified_text_diff(
    before: str,
    after: str,
    before_label: str = "current",
    after_label: str = "candidate",
) -> str:
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    if before_lines and not before_lines[-1].endswith("\n"):
        before_lines[-1] += "\n"
    if after_lines and not after_lines[-1].endswith("\n"):
        after_lines[-1] += "\n"
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=before_label,
        tofile=after_label,
        n=3,
    )
    return "".join(diff)
