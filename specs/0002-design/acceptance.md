# Acceptance — 0002 Design ledger

"v0.1 done" means the following hold simultaneously.

## Artifacts present

- `pyproject.toml` with `[tool.uv] package = true` and a
  `[dependency-groups]` dev section
- `STATUS.md` with the three H2 sections "Current state",
  "Known limits", "Next feature queue"
- `review_queue/` package with `cli.py`, `submit.py`, `list_cmd.py`,
  `decide.py`, `publish.py`, `state.py`, `schema.py`, `records.py`,
  `frontmatter.py`, `diff.py`
- `schemas/promotion-record.schema.json`,
  `schemas/candidate.schema.json`, `schemas/target.schema.json`
- `scripts/validate_schemas.py`, `scripts/validate_records.py`,
  `scripts/validate_decisions.py`, `scripts/voice_lint.py`
- `examples/rec-2026-08-14-001.md` validates
- `decisions/DEC-RQ-001-human-gate-default.md` validates
- `docs/methodology.md` and `docs/system-map.md`
- `tests/` directory with at least one test file per major module

## Gates pass

```
python -m uv sync
python -m pytest
python scripts/voice_lint.py
python scripts/validate_schemas.py
python scripts/validate_records.py
python scripts/validate_decisions.py
```

All exit zero.

## CLI smoke

```
python -m review_queue --help
python -m review_queue list
python -m review_queue list --status published
```

All exit zero. The second and third commands return the example
record when run from the repo root.

## End-to-end smoke

A scratch run of submit -> decide -> publish on a fresh candidate:

```
python -m review_queue submit --candidate examples/candidates/mem-2026-08-14.md --provenance trace://test/run/1 --target file://./scratch/out.md
python -m review_queue decide --record-id <id> --verdict approve --reviewer test
python -m review_queue publish --record-id <id>
```

The record moves from `queue/` to `decided/`, the target file is
written under `scratch/`, all three commands exit zero.

## Manual review

- A reader of `docs/methodology.md` can name what counts as a row in
  a calibration set and how verdict latency is computed within 30 sec.
- The state-machine validator rejects a hand-edited record that jumps
  from `pending` to `published` without going through `approved`.
- The submit command refuses an attempt to submit with an empty
  `--provenance` flag.
