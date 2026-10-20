# DEC-RQ-002 — Legacy edit verdicts without a pinned digest are not approvals

Status: accepted, 2026-10-20
Owner: vignesh

## Context

R-RQ-007 makes an `edit` verdict an approval of the edited candidate.
Since that change, `decide --verdict edit` applies the edit to the
submitted bytes (checked against `candidate_sha256`) and records the
edited bytes' digest as `approved_sha256`. `publish` re-applies the
edit, checks the result against `approved_sha256`, and writes exactly
those bytes.

Edit verdicts recorded before that change carry no `approved_sha256`.
Some also lack `candidate_sha256` (for example
`decided/rec-2026-08-17-001.md`), and their `edit_diff` is free text
that was never applied to any bytes. The R-RQ-007 review left the
handling of these records as an owner choice between three options:

- (a) treat an edit verdict without a pinned digest as not approved:
  publish refuses it and the candidate needs a fresh review;
- (b) grandfather it: publish the submitted bytes, or apply the stored
  edit at publish time, without a pinned digest;
- (c) pin at migration time: compute `approved_sha256` for existing
  records in a one-off migration.

## Decision

Option (a), fail closed. An approved record whose latest approving
verdict is an `edit` and which has no `approved_sha256` is treated as
not approved. `publish` refuses it before reading the candidate, writes
nothing, leaves the record `approved` in place, and exits 2 with:

> edited candidate digest missing: this edit verdict was recorded
> without approved_sha256, so it approves no pinned bytes and is
> treated as not approved; resubmit the candidate and have the reviewer
> re-review it

The way forward is the normal path: `submit` the candidate again, and
the reviewer records a new verdict (an `edit` against the new record
pins `approved_sha256`). The tool does not compute a digest for an old
verdict on the reviewer's behalf.

`decide` behaviour is unchanged. On a record without
`candidate_sha256`, an edit is still stored as unchecked text with no
`approved_sha256`; publish then refuses it under this decision.

## Consequences

- No bytes ship on the strength of an edit verdict that never named
  exact bytes. Neither the pre-edit candidate nor an edit computed at
  publish time can go out under an old verdict.
- Old records stay readable and keep their verdicts as history; only
  publication is refused. `decided/rec-2026-08-17-001.md` is such a
  record.
- Each legacy edit that someone still wants shipped costs one
  resubmission and one review.
- The refusal is checked first, so it reads the same whether or not the
  record has `candidate_sha256` and whether or not the candidate file
  still exists.

## Alternatives considered

- (b) Grandfathering. Rejected: shipping the submitted bytes publishes
  text the reviewer changed, and applying the stored edit at publish
  time ships bytes nobody saw as a whole. Legacy `edit_diff` values are
  free text that may not apply at all.
- (c) Pinning at migration time. Rejected: the digest would be computed
  by the migration, not approved by the reviewer, and records without
  `candidate_sha256` have no verified bytes to apply the edit to. It
  would turn an unchecked edit into an apparently checked one.
