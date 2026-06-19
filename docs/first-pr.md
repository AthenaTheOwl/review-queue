# First PR

The literal first PR after this scaffold. The goal is the schemas, the
example record, and the decision record justifying the human-gate
default — no runtime yet.

## Files this PR adds

- `schemas/promotion-record.schema.json`
  - JSON Schema draft 2020-12
  - Required: `id`, `record_type`, `candidate_ref`,
    `provenance_ref`, `diff`, `status`, `target`, `created_at`
  - `status` enum: `pending`, `approved`, `rejected`, `published`,
    `superseded`
  - `record_type` enum (v0): `memory-update`, `test-case`, `skill`,
    `brief`, `contract-clause`, `post`
  - `verdicts[]`: array of verdict objects with `reviewer`,
    `decided_at`, `decision`, optional `edit_diff`
- `schemas/candidate.schema.json`
  - Optional wrapper for structured candidates; documents the
    expected shape per record_type
- `schemas/target.schema.json`
  - URI-scheme enumeration: `file://`, `repo://`
  - Each scheme has a required-fields block (e.g., `file://` needs
    a writable path; `repo://` needs a repo name plus a path)
- `examples/rec-2026-08-14-001.md`
  - Populated front-matter block showing a memory-update candidate
  - Body contains a unified diff against a fixture memory file
- `decisions/DEC-RQ-001-human-gate-default.md`
  - Names the human-gate-by-default policy
  - Lists conditions under which an auto-promote opt-in could be
    considered (per record type, with a calibration record)
- `scripts/validate_schemas.py`
  - Loads every file under `schemas/` and confirms it parses as
    JSON Schema
- `scripts/validate_records.py`
  - Loads every Markdown file under `queue/`, `decided/`, and
    `examples/`, parses front-matter, validates against the
    promotion-record schema, and enforces the state-transition
    constraints in design.md

## Verification

```
python -m pytest        # no tests yet; runner exits clean
python scripts/validate_schemas.py
python scripts/validate_records.py
```

All three exit zero. The example record validates. The validator
rejects a hand-edited copy that sets `status: published` without
prior `approved`.

## What this PR does not do

- No CLI commands. PR 2 adds `submit` and `list`.
- No decide or publish behaviour. PR 3 adds those.
- No voice-lint script. That lands in PR 2.
- No live target support. The example record uses a `file://` target
  pointing at a fixture file.
