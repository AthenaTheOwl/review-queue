# METHODOLOGY — scoring and calibration

ReviewQueue is, at heart, a calibration instrument. Every approved
record is a recorded reviewer judgment against an AI-generated
candidate; the ledger of those judgments is the input to the
auto-promote decision named in DEC-RQ-001. This document is the
contract for what counts as a row, how the row set is scored, and how
often the score is read.

## What is a row

A row in the calibration set is a published or decided record with
the following fields populated:

- `id` — the record identifier
- `record_type` — the calibration set the row belongs to
- `provenance_ref` — URI pointing at the producing agent run
- the first verdict in `verdicts[]` — the reviewer, the decision,
  the decided_at timestamp
- `created_at` — used as the start of the verdict-latency window

A record stuck at `pending` is not a row. A record with no verdict is
not a row. A record with status `superseded` is a row only when its
predecessor verdict was `edit`; pure re-submits do not contribute.

## What is scored

Per record_type, we compute four quantities over the row set:

1. **Approve-unchanged rate.** Share of rows whose first verdict is
   `approve` (not `edit`, not `reject`). This is the headline number;
   DEC-RQ-001 names the threshold for auto-promote eligibility at 95%
   over at least twenty rows.

2. **Edit rate.** Share of rows whose first verdict is `edit`. A high
   edit rate means the upstream agent is producing candidates that are
   close-but-not-right; the agent's prompt or grounding needs work.

3. **Reject rate.** Share of rows whose first verdict is `reject`. A
   high reject rate means the upstream agent is producing candidates
   that are not even close; the candidate generator is the problem,
   not the gate.

4. **Verdict latency.** The wall-clock time between `created_at` and
   the first verdict's `decided_at`. Reported as median across the
   row set. The current target is under 30 minutes for `memory-update`
   and under 2 hours for `contract-clause`; these are heuristics, not
   contracts.

## How to compute verdict latency

```
latency_seconds = decoded(first_verdict.decided_at) - decoded(created_at)
```

Both timestamps are ISO 8601 UTC. The first verdict is `verdicts[0]`
after the chronological sort guaranteed by the CLI's append-only
behavior on the verdicts list.

## What does not count

- A row produced by a reviewer reviewing their own candidate. The
  v0 CLI does not enforce this (no reviewer-identity registry yet),
  but the methodology says drop it.
- A row whose `provenance_ref` does not start with a known URI scheme
  (`trace://`, `evidence://`, `cdcp://`). The schema only enforces
  URI-shape; the methodology is stricter about which schemes count.
- A row whose verdict came in under 10 seconds after `created_at`.
  That is either a robot or a reviewer hitting the approve key by
  reflex. Drop it; investigate.

## Cadence

The calibration set is scored once per calendar quarter. The scoring
command (`python -m review_queue score --record-type X`) appends one
row per record_type to `data/ledger/runs.jsonl`. The reviewer reads
each row against its DEC-RQ-001 thresholds, names any record_type
that has crossed into auto-promote territory, and lands the conclusion
in a DEC-RQ-NNN entry. This is the only ritual the ledger requires.

## What revisits this

The methodology itself is revisited under three triggers, each of
which appends a row to `data/ledger/runs.jsonl` regardless of the
calendar quarter:

1. **A new record_type lands.** When the producer half starts
   accepting a record_type the methodology does not name, this
   document must grow a new latency heuristic for it and a new
   DEC-RQ-001 row binding the auto-promote threshold. Until then,
   that record_type is scored but not eligible for auto-promote.

2. **A scoring run trips an unexpected metric.** If a quarterly run
   shows an approve-unchanged rate above 99% with sample_count under
   20, the methodology is wrong about thresholds or the upstream
   agent is being tested on too easy a row set. The reviewer revisits
   the row-eligibility rules above (especially the under-10-seconds
   exclusion) and lands a methodology amendment.

3. **A DEC-RQ-NNN promotion fails in the field.** If a record_type
   was auto-promoted on the strength of a scoring run and the
   resulting candidates produced visible damage, the methodology is
   too permissive. The reviewer revisits the headline number, lands
   a tighter threshold in DEC-RQ-001, and re-scores the historical
   row set against the new rule.

Quarterly readings revisit the numbers. The three triggers above
revisit the rules that produce the numbers. The distinction matters:
the rules are the moat, not the numbers.

## Worked example

The first row in the v0 calibration set is
`examples/rec-2026-08-14-001.md`. Its record_type is `memory-update`,
its `created_at` is 2026-08-14T12:34:56Z, its first verdict's
`decided_at` is 2026-08-14T13:01:12Z. Verdict latency: 26 minutes
16 seconds. Decision: `approve` (unchanged). The row contributes
1/N to the approve-unchanged rate for `memory-update`.

The first scoring run against this row is checked in at
`data/ledger/runs.jsonl` line 1: `record_type=memory-update`,
`sample_count=1`, `approve_unchanged_rate=1.0`,
`median_latency_seconds=1576`. The run is below DEC-RQ-001's
twenty-row threshold, so the record_type is not eligible for
auto-promote. The number is recorded anyway; that is the point of
the ledger.
