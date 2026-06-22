# PRODUCT_BRIEF — ReviewQueue

ReviewQueue is a monthly-and-quarterly **control plane** that scores,
calibrates, and audits the outputs of upstream AI agents. It is not a
candidate generator; it is the instrument that decides whether the
generator is calibrated enough to be trusted.

## What it does

Upstream agents produce candidates (memory updates, test cases, prompts,
posts, contract clauses). A human reviewer records a verdict
(`approve`, `edit`, `reject`) against each candidate. ReviewQueue ingests
the resulting ledger of reviewer judgments and emits, per record_type:

- approve-unchanged rate
- edit rate
- reject rate
- median verdict latency
- sample count

These numbers feed the auto-promote eligibility decision recorded in
DEC-RQ-001. They are computed by `review_queue.score`, persisted as
JSONL rows in `data/ledger/runs.jsonl` by `review_queue.ledger`, and
formatted for humans by `review_queue.report`.

## Who uses it

- Editorial ops at AI-content publishers, scoring the calibration of a
  candidate-generating agent over a quarter's traffic.
- Prompt-engineering teams running 100+ prompts who need a defensible
  number for "is this prompt safe to take off the human-gate".
- RAG-platform maintainers auditing whether retrieval-grounded answers
  pass reviewer scrutiny at a stable rate.

The audience is the person who must answer "should we still be
human-gating this surface, or has it earned auto-promote". ReviewQueue
returns a number, not an opinion.

## Why now

Every team running production AI has a stash of approved-or-rejected
artifacts. Almost none of them have turned that stash into a
calibration metric. The dream-promotion discipline from the CDCP
operating model names this primitive: the ledger of reviewer judgments
is the contract surface that lets auto-promote be a decision instead
of a vibe. ReviewQueue is the smallest tool that makes that ledger
queryable.

## What it is not

- Not a candidate generator. Upstream agents produce candidates; we
  ingest them.
- Not a UI. The CLI plus checked-in records is the surface.
- Not a real-time gate. Scoring is run monthly or quarterly. The
  promotion path is human-gated by default; scoring is for deciding
  whether to change that default.

## Cadence

Run scoring at the close of each calendar quarter. The output row is
appended to `data/ledger/runs.jsonl`. The reviewer reviews each
record_type against its DEC-RQ-001 threshold (95% approve-unchanged
over at least 20 rows) and lands the conclusion in a DEC-RQ-NNN entry.
This is the only ritual.

## How to run

```
python -m review_queue score --record-type memory-update
python -m review_queue report --record-type memory-update
```

`score` reads queue/ and decided/ and examples/, computes the metric
set, and appends a row to `data/ledger/runs.jsonl`. `report` reads the
ledger and prints a human-readable summary. Both commands exit zero on
success.

## Status

v0.1 ships:

- the four scoring metrics computed from a real reviewer-verdict ledger
- one checked-in JSONL ledger row at `data/ledger/runs.jsonl`
- the methodology contract at `docs/METHODOLOGY.md`
- the CLI commands `score` and `report` in addition to the existing
  `submit`, `list`, `decide`, `publish` from the scaffold

The promotion-workflow CLI is the row-producer; the scoring CLI is the
row-consumer. Both halves are in this repo because the calibration
ledger needs a typed producer to be worth scoring.
