# review-queue

A draft came in claiming the ERCOT large-load queue doubled quarter over quarter. The source was one screenshot. It sits in the queue now with a recorded verdict — rejected, by a named human, at 14:55:10 — because "doubled quarter over quarter" with no queue export behind it is a headline, not a fact. review-queue is the thing that made someone stop and say no before it shipped.

## What it does

An agent produces a candidate — a test case, a memory update, a draft brief, a skill, a contract clause. Most pipelines auto-promote it. This one doesn't. The candidate lands in a queue as a typed record carrying its provenance, its diff against current state, and a verdict slot that starts empty. A human approves, rejects, or edits. The action is logged. Only then does anything ship.

The record is the point. A `candidate` is whatever the upstream agent wrote. A `promotion-record` wraps it with where it came from, what it changes, and who signed off. A `target` is where an approved record goes — a file path, a PR, a post. review-queue doesn't write candidates; it receives them and stands between them and production. The CLI is the queue, the verdict-recorder, and the publisher, and nothing else.

## Try it

No args, no setup. It reads the committed records and prints the queue, rows awaiting a verdict first:

```
python -m review_queue show
```

```
review-queue - promotion-record queue
4 record(s) - pending=1  approved=1  published=1  rejected=1 (ranked: rows awaiting a verdict first, then most recent)

id                     status      type           decision  created              target
---------------------------------------------------------------------------------------
rec-2026-08-18-001     pending     test-case      -         2026-08-18T09:12:00Z file://tests/test_loader_bare_scheme.py
rec-2026-08-17-001     approved    skill          edit      2026-08-17T10:00:00Z file://skills/redact-check.md
rec-2026-08-14-001     published   memory-update  approve   2026-08-14T12:34:56Z file://docs/memory/scoring-pipeline-quirks.md
rec-2026-08-16-001     rejected    brief          reject    2026-08-16T14:20:00Z file://drafts/ercot-queue-doubled.md

needs attention: 1 record(s) pending a human verdict - oldest is rec-2026-08-18-001 (test-case, queued 2026-08-18T09:12:00Z). decide with `python -m review_queue decide --record-id rec-2026-08-18-001 --verdict approve --reviewer <you>`.
```

One record is still pending. The other three carry a decision and the name of who made it. The queue's whole job is to keep that pending row pending until a human clears it.

## The rest of the verbs

```
python -m review_queue validate                       # schema + state-machine check on every record
python -m review_queue list --status pending          # filter the queue
python -m review_queue submit --candidate path/to/candidate.md \
    --provenance trace://run/1 --target file://out.md  # wrap a candidate as a record
python -m review_queue decide --record-id <id> --verdict approve --reviewer you
python -m review_queue publish --record-id <id>        # ship an approved record to its target
python -m review_queue score --dry-run                 # calibration metrics over the queue
python -m review_queue report                          # read the calibration ledger
```

## Live demo

A Streamlit page renders the same human-gate queue interactively: status metrics, a ranked queue table, and a record inspector — pick a record, read its diff, its provenance, and its verdicts. It reads the committed records directly. No network, no secrets.

```
python -m uv run --with streamlit streamlit run streamlit_app.py
# or, if streamlit + this repo are installed:
streamlit run streamlit_app.py
```

Deploy on Streamlit Community Cloud: New app -> repo `AthenaTheOwl/review-queue`, branch `main`, main file `streamlit_app.py`. The root `requirements.txt` pins `streamlit` plus this repo (`.`).

<!-- live url: (paste the Streamlit Community Cloud URL here once deployed) -->

## How it connects

review-queue is the gate the rest of the portfolio empties into. Other repos produce the candidates; this one holds them until a human acts:

- [ai-field-brief](https://github.com/AthenaTheOwl/ai-field-brief) — drafts briefs that land here as candidates. The rejected ERCOT row above came off one of its traces.
- [procurement-negotiation-lab](https://github.com/AthenaTheOwl/procurement-negotiation-lab) — shares the factory-checkpoint pattern, where an agent's output waits on a recorded decision before it counts.

## Layout

```
review_queue/   cli, show, decide, publish, submit, score, report, schema, state, ledger
schemas/        promotion-record, candidate, target
queue/          typed records, one file per pending candidate
decided/        approved / rejected records
examples/       a published record + the candidates the queue rows wrap
specs/  docs/  scripts/  data/  decisions/
```

## License

MIT. See [LICENSE](LICENSE).
