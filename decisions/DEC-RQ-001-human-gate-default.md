# DEC-RQ-001 — Human gate is the default; auto-promote is opt-in

Status: accepted, 2026-08-14
Owner: vignesh

## Context

Every team running production AI has rebuilt a candidate-promotion
queue informally — typically in Jira, Notion, or Asana — and most of
those reinventions default to auto-promote. The candidate ships and a
human only intervenes if a downstream signal is loud enough. That
default is the wrong shape for the failure mode it is meant to catch:
silent-bad candidates that pass without notice.

ReviewQueue exists because the reverse default — human-gate by default,
auto-promote as an explicit opt-in per record type — is the missing
primitive. The schema is the moat; the default is the discipline.

## Decision

The default for every record_type in v0 is human-gate. A record enters
`queue/` with `status: pending` and does not progress without a recorded
verdict from a named reviewer.

Auto-promote is not implemented in v0. The schema reserves space for
it: a future field `auto_promote: true` on the record could short-
circuit the verdict step, but the field is not honored by the v0 CLI.

## Conditions under which auto-promote could later be enabled per record type

An auto-promote opt-in for a given record_type is only safe when all of
the following hold:

- The record_type has a per-type calibration record showing the verdict
  rate at which human reviewers approve unchanged. v0 has one such
  record (`examples/rec-2026-08-14-001.md`) for `memory-update`; one
  row is the seed, not the calibration. A calibration set requires at
  least twenty rows for that record_type.
- The approve-unchanged rate is at least 95% over the calibration
  window. Anything below that threshold means the human gate is doing
  real work and removing it would ship bad candidates silently.
- The target supports rollback. A `file://` target on a versioned
  repo qualifies; a `repo://` target with a CI checkpoint qualifies;
  a Substack post does not.
- The decision is recorded in a follow-on DEC entry that names the
  record_type, the calibration set, the rate, and the rollback path.

These conditions are not yet met for any record_type. Until they are,
the default stands.

## Consequences

- Every queued record carries a verdict. The verdicts list on a
  published record is the audit trail.
- The CLI refuses to submit a record with an empty provenance ref;
  see R-RQ-004. A record without provenance cannot be calibrated and
  therefore cannot be a candidate for future auto-promote opt-in.
- A reviewer who cannot decide within the recorded review SLA can mark
  the record `superseded` and re-queue. The state machine permits
  `pending -> superseded`.

## Alternatives considered

- Auto-promote by default, human-gate as opt-in. Rejected because the
  failure mode (silent-bad candidate ships) is harder to recover from
  than the slowness of a human gate.
- Two-reviewer consensus by default. Deferred — adds queue latency
  without evidence that single-reviewer verdicts are wrong often enough
  to justify it. Revisit if a calibration row records a reviewer error.
