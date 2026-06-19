# AGENTS.md — review-queue

Operating contract for AI agents working in this repo. Conventions
match the AthenaTheOwl portfolio so an agent already trained on the
ai-field-brief review queue or the procurement-negotiation-lab factory
checkpoint pattern recognizes the shape.

## What this repo is

A typed CLI for human-gated promotion of AI-generated candidates. The
default in this repo is human-gate; auto-promote is opt-in per record
type and is disabled in v0.

The candidate is a payload; the promotion-record is the typed wrapper
that carries the candidate, its provenance, the diff, and the verdict.
Approved records ship to their configured target.

## Roles you may see in tasks

| Role | What they do |
|---|---|
| `submitter` | Wraps an upstream candidate in a promotion-record and lands it in the queue |
| `differ` | Computes the diff between candidate and current state |
| `provenance-binder` | Attaches a trace ref or run-evidence ref to the record |
| `verdict-recorder` | Logs an approval, rejection, or edit on a queued record |
| `publisher` | Ships an approved record to its target |

These roles exist in the spec ledger; not all are implemented in v0.

## Voice constraints

- No marketing words. The banned set will live in
  `scripts/voice_lint.py::BANNED_FAIL` once the gate lands.
- No antithetical reversals as a structural device.
- Plain assertion. The schema is the moat; the voice is the
  scaffolding.

## Gates (will land in spec 0002)

Planned local gates before pushing:

- `pytest`
- `voice_lint.py` on `docs/` and `examples/`
- `spec_check.py` against `specs/`
- `validate_records.py` — every record in `queue/` and `decided/`
  validates against the promotion-record schema
- `provenance_check.py` — every approved record carries a non-empty
  provenance ref

## Out of scope

- Generating candidates. Upstream agents do that.
- A hosted UI. v0 is CLI plus typed Markdown records.
- Auto-promote defaults. The whole point of this repo is to invert
  that default.
- Multi-reviewer consensus mechanics. v0 records one reviewer per
  verdict.
