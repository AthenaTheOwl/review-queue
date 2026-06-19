# Acceptance — 0001 Foundation

"v0 done" means the following hold simultaneously.

## Artifacts present

- `schemas/promotion-record.schema.json` validates
- `schemas/candidate.schema.json` validates
- `schemas/target.schema.json` validates
- `examples/rec-2026-08-14-001.md` exists with a populated front-
  matter block and validates against the promotion-record schema
- `decisions/DEC-RQ-001-human-gate-default.md` exists

## Gates pass

Run from the repo root:

```
python -m pytest
python scripts/voice_lint.py
python scripts/validate_schemas.py
python scripts/validate_records.py
python scripts/validate_decisions.py
```

All five exit zero.

## CLI smoke

```
python -m review_queue --help
python -m review_queue list --status pending
```

Both exit zero. The `list` command returns the example record
when run from the repo root.

## Manual review

- A reader can read `examples/rec-2026-08-14-001.md` and name the
  upstream agent, the target, and the current status within thirty
  seconds.
- The state-machine validator rejects a hand-edited record that
  jumps from `pending` to `published` without going through
  `approved`.
- The submit command refuses an attempt to submit with an empty
  `--provenance` flag.

## Out of v0 acceptance

- The publish command does not yet write to live targets; it ships
  as a stub. Live publish is spec 0003.
- The decide command does not yet enforce reviewer identity. That
  is spec 0004.
- No GitHub PR or Substack target support.
