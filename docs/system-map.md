# System map

Where the parts live and how the bytes flow.

## Layout

```
review-queue/
  review_queue/          <-- runtime: CLI + record I/O + state machine
    cli.py               argparse front door (python -m review_queue)
    submit.py            wraps candidate, writes queue/<id>.md
    list_cmd.py          filters records by status / type / reviewer
    decide.py            appends verdict, flips status
    publish.py           writes target, moves record to decided/
    records.py           Record dataclass; load, save, iter, find
    frontmatter.py       narrow-YAML parser; the schema is the moat
    schema.py            in-code validator mirroring schemas/*.json
    state.py             state machine + consistency check
    diff.py              difflib-based unified diff helper
  schemas/               JSON Schema draft 2020-12
    promotion-record.schema.json
    candidate.schema.json
    target.schema.json
  scripts/               gates run from repo root
    validate_schemas.py
    validate_records.py
    validate_decisions.py
    voice_lint.py
  queue/                 pending records, one file per record (empty by default)
  decided/               approved / rejected / published records (empty by default)
  examples/              checked-in ledger rows + candidate payloads
    rec-2026-08-14-001.md          <-- first calibration ledger row
    candidates/mem-2026-08-14.md   <-- candidate payload referenced by the row
  decisions/             governance records (DEC-RQ-NNN-<slug>.md)
  docs/                  methodology, system map, first-pr brief, calibration ledger
  specs/                 numbered specs (0001-foundation, 0002-design)
  tests/                 pytest suite
  STATUS.md              three-section contract surface
  AGENTS.md              operating contract for AI agents
  pyproject.toml         uv-aware Python packaging
```

## Data flow

```
  upstream agent produces a candidate
            |
            v
  CLI: submit  ----->  queue/<id>.md  (status: pending, verdicts: [])
            |
            v
  CLI: decide  ----->  queue/<id>.md  (status: approved | rejected, verdicts: [v1])
            |
            v
  CLI: publish ----->  decided/<id>.md (status: published)
                            |
                            v
                  target file written
                  (file://... resolved against repo root)
```

The CLI is the only mutator. Records are checked-in Markdown; the
schema is the contract; the state machine is the gate. A queue entry
without a verdict is pending. A queue entry with a verdict is on its
way out — either to `decided/` (after publish) or annotated in place
(after reject or supersede).

## What lives outside this repo

- Upstream agents producing candidates. ReviewQueue does not generate
  them; it receives them through `submit`.
- Target storage for `repo://` targets. v0 does not write to remote
  repos; the target is parsed but the publisher emits a stub error.
- Provenance traces. The `provenance_ref` is a URI pointing at an
  external trace, run-evidence packet, or CDCP event-log entry. The
  ledger of those traces lives in the producing system, not here.

## Where to look first

- Spec 0001 names the schema and the human-gate default.
- Spec 0002 names the runnable CLI and the calibration ledger.
- DEC-RQ-001 records why human-gate is the default.
- `docs/methodology.md` records what counts as a calibration row.
- `examples/rec-2026-08-14-001.md` is the first checked-in row.
