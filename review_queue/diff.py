"""Diff helpers. v0 supports unified text diffs only."""
from __future__ import annotations

import difflib
import re

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,(\d+))? @@")


class PatchError(ValueError):
    """Raised when an edit diff does not apply cleanly to the candidate."""


def review_text(candidate_bytes: bytes) -> str:
    """The candidate text a review diff shows: UTF-8, newlines normalised to LF."""
    return candidate_bytes.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


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


def _split_lines(text: str) -> list[str]:
    """Split after each LF only; str.splitlines also breaks on form feeds and U+2028."""
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def apply_unified_diff(before: str, patch: str) -> str:
    """Apply a single-file unified diff to `before` and return the result.

    Strict on purpose: every context and removed line must match `before`
    exactly where its hunk header says, and hunk line counts must agree
    with the header. Anything else raises PatchError instead of guessing.
    File header lines (`---`, `+++`, `diff`, `index`) before the first
    hunk are skipped; `\\ No newline at end of file` markers are honoured.
    """
    src = _split_lines(before)
    patch = patch.replace("\r\n", "\n")
    # Only a marker says "no newline"; a patch that lost its final newline
    # (shell command substitution strips it) still means a complete line,
    # including a CRLF patch whose last line kept only its "\r".
    if not patch.endswith("\n"):
        patch = patch.removesuffix("\r") + "\n"
    lines = _split_lines(patch)
    out: list[str] = []
    pos = 0
    hunks = 0
    i = 0
    while i < len(lines):
        m = _HUNK_RE.match(lines[i])
        if m is None:
            if hunks and lines[i].strip():
                raise PatchError(f"unexpected line after hunk {hunks}: {lines[i]!r}")
            i += 1
            continue
        hunks += 1
        old_start = int(m.group(1))
        old_len = 1 if m.group(2) is None else int(m.group(2))
        new_len = 1 if m.group(3) is None else int(m.group(3))
        # A zero-length old range names the line the hunk inserts after.
        start = old_start - 1 if old_len else old_start
        if start < pos or start > len(src):
            raise PatchError(f"hunk {hunks} starts outside the candidate or overlaps the previous hunk")
        out.extend(src[pos:start])
        pos = start
        i += 1
        old_seen = new_seen = 0
        while old_seen < old_len or new_seen < new_len:
            if i >= len(lines):
                raise PatchError(f"hunk {hunks} is truncated")
            line = lines[i]
            # Some tools drop the leading space on an empty context line.
            tag, text = (" ", "\n") if line == "\n" else (line[:1], line[1:])
            i += 1
            if i < len(lines) and lines[i].startswith("\\"):
                text = text.removesuffix("\n")
                i += 1
            if tag not in (" ", "-", "+"):
                raise PatchError(f"hunk {hunks} has an unrecognised line: {line!r}")
            if tag in (" ", "-"):
                if old_seen == old_len:
                    raise PatchError(f"hunk {hunks} has more old lines than its header says")
                if pos >= len(src) or src[pos] != text:
                    raise PatchError(f"hunk {hunks} does not match the candidate at line {pos + 1}")
                pos += 1
                old_seen += 1
            if tag in (" ", "+"):
                if new_seen == new_len:
                    raise PatchError(f"hunk {hunks} has more new lines than its header says")
                out.append(text)
                new_seen += 1
    if not hunks:
        raise PatchError("edit diff has no @@ hunk to apply")
    out.extend(src[pos:])
    return "".join(out)


def apply_edit(candidate_bytes: bytes, edit_diff: str) -> bytes:
    """The edited candidate: `edit_diff` applied to the text the review diff showed."""
    return apply_unified_diff(review_text(candidate_bytes), edit_diff).encode("utf-8")
