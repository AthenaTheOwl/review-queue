"""validate_schemas: confirm every file under schemas/ parses as JSON.

A real JSON Schema validator (jsonschema) is not a v0 dependency. The
schemas are the contract surface; the in-code schema.py mirror is what
the CLI uses at runtime. This script catches malformed JSON and
obvious structural errors.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    schemas_dir = REPO_ROOT / "schemas"
    if not schemas_dir.exists():
        print(f"no schemas/ directory at {schemas_dir}", file=sys.stderr)
        return 1
    failures: list[str] = []
    files = sorted(schemas_dir.glob("*.schema.json"))
    if not files:
        print("no *.schema.json files found", file=sys.stderr)
        return 1
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name}: invalid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            failures.append(f"{path.name}: top-level is not an object")
            continue
        if "$schema" not in data:
            failures.append(f"{path.name}: missing $schema")
        if "title" not in data:
            failures.append(f"{path.name}: missing title")
        print(f"ok   {path.name}")
    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
