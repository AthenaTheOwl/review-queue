"""voice_lint: scan docs/ and examples/ for banned marketing words.

The AGENTS.md voice constraints name a banned-set; this script is the
gate that enforces them. The banned list is intentionally short and
conservative; expand only when a real drift is observed.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

BANNED_FAIL: tuple[str, ...] = (
    "leverage",
    "revolutionary",
    "seamlessly",
    "unleash",
    "game-changing",
    "synergy",
    "best-in-class",
    "world-class",
    "delight",
    "magical",
    "supercharge",
    "blazing fast",
)

SCAN_DIRS: tuple[str, ...] = ("docs", "examples")


def main() -> int:
    failures: list[str] = []
    for sub in SCAN_DIRS:
        root = REPO_ROOT / sub
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            text_lower = text.lower()
            for word in BANNED_FAIL:
                pattern = r"\b" + re.escape(word.lower()) + r"\b"
                if re.search(pattern, text_lower):
                    rel = path.relative_to(REPO_ROOT)
                    failures.append(f"{rel}: banned word {word!r}")
    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    print("ok   voice_lint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
