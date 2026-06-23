"""Minimal YAML front-matter parser.

Supports the subset of YAML used by promotion-record files:
- scalar key: value (strings, ints, ISO datetimes)
- empty list:  key: []
- list-of-mappings:
    verdicts:
      - reviewer: foo
        decided_at: 2026-08-14T13:00:00Z
        decision: approve

This is intentionally narrow. Adding nested mappings or YAML anchors is
out of scope for v0; the schema constraints keep records simple.
"""
from __future__ import annotations

import re
from typing import Any

FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)


def _unescape(s: str) -> str:
    """Reverse the escaping applied by `_escape` for double-quoted scalars."""
    out: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "t":
                out.append("\t")
                i += 2
                continue
            if nxt == '"':
                out.append('"')
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _escape(s: str) -> str:
    """Escape a string so it stays a single physical line inside double quotes."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def split(text: str) -> tuple[str, str]:
    """Return (frontmatter_text, body). Raises ValueError if no fm block."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("missing YAML front-matter block")
    return m.group("fm"), m.group("body")


def _coerce(raw: str) -> Any:
    s = raw.strip()
    if s == "":
        return ""
    if s == "[]":
        return []
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s == "null" or s == "~":
        return None
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return _unescape(s[1:-1])
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def loads(text: str) -> dict[str, Any]:
    """Parse YAML front-matter into a Python dict.

    Top-level: only scalar mappings and one list-of-mappings (verdicts).
    """
    lines = text.splitlines()
    result: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line.startswith(" "):
            raise ValueError(f"unexpected indented line at top level: {line!r}")
        if ":" not in line:
            raise ValueError(f"missing colon in front-matter line: {line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value == "":
            items, consumed = _parse_block_list(lines, i + 1)
            result[key] = items
            i = i + 1 + consumed
            continue
        result[key] = _coerce(value)
        i += 1
    return result


def _parse_block_list(lines: list[str], start: int) -> tuple[list[Any], int]:
    """Parse a block-list of mappings starting at `start`.

    Each item begins with `  - key: value` (two-space indent + dash).
    Continuation lines (keys after the first inside the same item) use
    four-space indent.

    Returns (items, line_count_consumed).
    """
    items: list[Any] = []
    i = start
    while i < len(lines):
        raw = lines[i]
        if not raw.strip():
            i += 1
            continue
        if raw.startswith("  - "):
            item: dict[str, Any] = {}
            head = raw[4:]
            if ":" not in head:
                raise ValueError(f"list item missing colon: {raw!r}")
            k, _, v = head.partition(":")
            item[k.strip()] = _coerce(v.strip())
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.startswith("    ") and not nxt.startswith("    - "):
                    sub = nxt[4:]
                    if ":" not in sub:
                        raise ValueError(f"continuation line missing colon: {nxt!r}")
                    sk, _, sv = sub.partition(":")
                    item[sk.strip()] = _coerce(sv.strip())
                    j += 1
                elif not nxt.strip():
                    j += 1
                else:
                    break
            items.append(item)
            i = j
            continue
        break
    return items, i - start


def dumps(data: dict[str, Any]) -> str:
    """Render a dict as YAML front-matter (the subset we read)."""
    out: list[str] = []
    for key, value in data.items():
        if key == "verdicts":
            if not value:
                out.append("verdicts: []")
                continue
            out.append("verdicts:")
            for v in value:
                first = True
                for vk, vv in v.items():
                    prefix = "  - " if first else "    "
                    out.append(f"{prefix}{vk}: {_dump_scalar(vv)}")
                    first = False
            continue
        if isinstance(value, list) and not value:
            out.append(f"{key}: []")
            continue
        out.append(f"{key}: {_dump_scalar(value)}")
    return "\n".join(out)


def _dump_scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    needs_quote = any(
        ch in s
        for ch in (":", "#", "[", "]", "{", "}", "&", "*", "!", "|", ">", "%", "@", "`", "\n", "\t", "\\", '"')
    )
    if needs_quote:
        return '"' + _escape(s) + '"'
    return s


def wrap(fm: dict[str, Any], body: str) -> str:
    """Render a complete Markdown file: --- fm --- body."""
    if not body.endswith("\n"):
        body = body + "\n"
    return f"---\n{dumps(fm)}\n---\n\n{body}"
