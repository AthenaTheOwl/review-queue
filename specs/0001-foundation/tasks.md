# Tasks — 0001 Foundation

Checkbox tasks ordered for the first two to three PRs after the
scaffold.

## PR 1 — Schema and example record

- [ ] Write `schemas/promotion-record.schema.json` per R-RQ-001
- [ ] Write `schemas/candidate.schema.json` (the optional wrapper
      for structured candidates)
- [ ] Write `schemas/target.schema.json` enumerating supported URI
      schemes
- [ ] Write one example record at `examples/rec-2026-08-14-001.md`
      with a populated front-matter block
- [ ] Add `decisions/DEC-RQ-001-human-gate-default.md`
- [ ] Add `scripts/validate_schemas.py` skeleton
- [ ] Add `scripts/validate_records.py` skeleton enforcing the state
      machine

## PR 2 — CLI skeleton and submit command

- [ ] Implement `src/review_queue/cli.py` with `submit`, `list`,
      `decide`, `publish` command stubs
- [ ] Implement `src/review_queue/submit.py` (wraps a candidate,
      computes a unified diff, attaches provenance, writes a queue
      record)
- [ ] Implement `src/review_queue/list.py` filtering by status
- [ ] Add `scripts/voice_lint.py` skeleton
- [ ] Wire CLI entry: `python -m review_queue ...`

## PR 3 — Decide and publish commands plus DEC ledger

- [ ] Implement `src/review_queue/decide.py` (mutates status,
      appends verdict, enforces state-machine constraints)
- [ ] Implement `src/review_queue/publish.py` (resolves target ref,
      writes content, updates status, moves record to `decided/`)
- [ ] Add `scripts/validate_decisions.py` skeleton
- [ ] Document the target-scheme decision in DEC-RQ-002
- [ ] Update README install + run section once the CLI runs end-to-
      end on the example record
