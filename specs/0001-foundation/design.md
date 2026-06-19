# Design — 0001 Foundation

## Shape

review-queue is a Python CLI plus a typed schema. A candidate lands
in the queue as a checked-in Markdown-plus-YAML-front-matter file.
A verdict mutates the file's status field and appends to its
verdicts list. A publish action moves the file to the configured
target.

The architecture has four layers:

1. **Submit.** `submit` reads a candidate, computes a diff, attaches
   provenance, writes a new record under `queue/<id>.md`.
2. **Decide.** `decide` mutates a queued record's status and appends
   a verdict.
3. **Publish.** `publish` reads an approved record, resolves the
   target ref, writes the candidate to the target, updates the
   record's status to `published`.
4. **List.** `list` filters records by status, type, reviewer, or
   age.

## Data flow

```
upstream agent produces candidate
   |
   v
[submit] -> queue/<id>.md (status: pending)
   |
   v
human runs [decide] -> queue/<id>.md (status: approved)
   |
   v
[publish] -> writes to target, updates record status: published
   |
   v
decided/<id>.md  (record moves out of queue)
```

## Record file shape

Each record is a single Markdown file with a YAML front-matter block
holding the typed fields. The body is the candidate content (for
text record types) or a pointer to the structured candidate (for
JSON / YAML record types).

```
---
id: rec-2026-08-14-001
record_type: memory-update
candidate_ref: candidates/mem-2026-08-14.md
provenance_ref: trace://athena-site/ops/event-log/2026-08-14.jsonl#evt-42
status: pending
target: repo://athena-site/memory/MEMORY.md
created_at: 2026-08-14T12:34:56Z
verdicts: []
---

# Candidate diff

(unified diff goes here)
```

## State machine

Allowed transitions:

- `pending -> approved`
- `pending -> rejected`
- `approved -> published`
- `approved -> superseded` (only when an edit verdict creates a new
  record)
- `pending -> superseded` (only when the upstream agent re-submits
  a corrected candidate)

The state machine is enforced by `validate_records.py`. A record
with an illegal transition trail fails the gate.

## Provenance discipline

A record without a provenance ref does not enter the queue. The CLI
exits non-zero on a submit with an empty `--provenance` flag. This
is the discipline that distinguishes ReviewQueue from a generic
todo list; every queued item is traceable back to the agent run
that produced it.

## Out of v0 scope

- A web UI
- Multi-reviewer consensus
- GitHub PR target support
- Auto-promote per record type
- Cross-record diff (when a new candidate conflicts with an already-
  pending candidate)
