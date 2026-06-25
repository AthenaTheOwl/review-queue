"""validate_records: every record in queue/, decided/, examples/
parses, validates against the promotion-record schema, and obeys
the state-machine consistency check.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from review_queue import records as records_mod  # noqa: E402
from review_queue import schema, state  # noqa: E402


def main() -> int:
    roots = [REPO_ROOT / "queue", REPO_ROOT / "decided", REPO_ROOT / "examples"]
    records = records_mod.iter_records(roots)
    if not records:
        print("no records found under queue/, decided/, or examples/")
        return 0
    failures: list[str] = []
    for r in records:
        rel = r.path.relative_to(REPO_ROOT)
        try:
            schema.validate(r.fm)
        except schema.SchemaError as exc:
            failures.append(f"{rel}: schema: {exc}")
            continue
        try:
            state.consistency_check(r.fm)
        except state.TransitionError as exc:
            failures.append(f"{rel}: state: {exc}")
            continue
        print(f"ok   {rel}")
    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
