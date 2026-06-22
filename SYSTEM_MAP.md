# SYSTEM_MAP — ReviewQueue

Where the parts live and how the bytes flow through the scoring and
calibration pipeline.

## Two halves

ReviewQueue has two distinct halves sharing one record format:

```
  +-------------------+        +----------------------+
  |  PRODUCER half    |        |  CONSUMER half       |
  |  (transactional)  |        |  (analytical)        |
  |                   |        |                      |
  |  submit ----.     |        |   .------> score     |
  |  decide  ---+--> records --+-->-------> report    |
  |  publish ---'     |        |   '------> audit     |
  +-------------------+        +----------------------+
       writes a row              reads N rows,
       per reviewer judgment     emits one ledger run
```

The PRODUCER is run continuously: each reviewer verdict appends a row
to the ledger of records (`queue/`, `decided/`, `examples/`). The
CONSUMER is run monthly or quarterly: it scores the row set, emits a
single JSONL row to `data/ledger/runs.jsonl`, and prints a report.

## Repository layout

```
review-queue/
  PRODUCT_BRIEF.md       what this is and who it is for
  SYSTEM_MAP.md          this file
  STATUS.md              three-section contract surface
  AGENTS.md              operating contract for AI agents

  review_queue/          runtime package (importable as review_queue)
    cli.py               argparse front door (python -m review_queue)
    submit.py            wraps candidate, writes queue/<id>.md
    list_cmd.py          filters records by status / type / reviewer
    decide.py            appends verdict, flips status
    publish.py           writes target, moves record to decided/
    score.py             calibration scoring (approve/edit/reject/latency)
    ledger.py            data/ledger/*.jsonl reader and appender
    report.py            human-readable formatter for scoring runs
    records.py           Record dataclass; load, save, iter, find
    frontmatter.py       narrow-YAML parser
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

  queue/                 pending records, one file per record
  decided/               approved / rejected / published records
  examples/              checked-in calibration rows + candidate payloads
    rec-2026-08-14-001.md
    candidates/mem-2026-08-14.md

  data/                  derived calibration artifacts (CONSUMER half)
    ledger/
      runs.jsonl         one JSON object per scoring run, append-only

  decisions/             governance records (DEC-RQ-NNN-<slug>.md)

  docs/
    METHODOLOGY.md       what counts as a row, what is scored, cadence
    system-map.md        legacy lowercase mirror (do not edit; this file
                         is the canonical map)
    first-pr.md
    calibration/         narrative writeups of past calibration runs

  specs/                 numbered specs (0001-foundation, 0002-design)
  tests/                 pytest suite
  pyproject.toml         uv-aware Python packaging
```

## Producer-side data flow

```
  upstream agent produces a candidate
            |
            v
  CLI: submit  ----->  queue/<id>.md  (status: pending, verdicts: [])
            |
            v
  CLI: decide  ----->  queue/<id>.md  (status: approved | rejected,
                                       verdicts: [v1])
            |
            v
  CLI: publish ----->  decided/<id>.md (status: published)
                            |
                            v
                  target file written
                  (file://... resolved against repo root)
```

## Consumer-side data flow

```
  records under queue/, decided/, examples/
            |
            v
  score.score_records(records, record_type)
            |
            v
  metrics: {approve_unchanged_rate, edit_rate, reject_rate,
            median_latency_seconds, sample_count, ...}
            |
            +------> ledger.append_run() ------> data/ledger/runs.jsonl
            |
            +------> report.format_report() ----> stdout
```

The CONSUMER never mutates a record. It reads the row set and emits
derived artifacts only. The producer-consumer boundary is the contract
that makes the scoring number reproducible: any reviewer can replay
the ledger and obtain the same numbers.

## What lives outside this repo

- Upstream agents producing candidates. ReviewQueue does not generate
  them; it receives them through `submit`.
- Target storage for `repo://` targets. v0 does not write to remote
  repos.
- Provenance traces. The `provenance_ref` is a URI pointing at an
  external trace, run-evidence packet, or CDCP event-log entry.

## Where to look first

- `PRODUCT_BRIEF.md` — what this is and who uses it.
- `docs/METHODOLOGY.md` — what counts as a row and how scoring is
  computed.
- `data/ledger/runs.jsonl` — every scoring run, append-only.
- `examples/rec-2026-08-14-001.md` — first checked-in calibration row.
- Spec `0002-design/` — the runnable CLI and calibration ledger spec.
- DEC-RQ-001 — why human-gate is the default, and the auto-promote
  thresholds the scoring run is measured against.
