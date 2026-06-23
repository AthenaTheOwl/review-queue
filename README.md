# ReviewQueue

Human-gated promotion workflow for AI-generated content. AI proposes N candidate {memory updates, tests, skills, briefs, contracts, posts}; a reviewer approves, rejects, or edits with full diff and provenance; approved candidates ship via a configured target.

## What this is

A CLI plus a typed schema for candidate-promotion records. The default
in most teams is auto-promote; the default here is human-gate. AI
generates a candidate; the candidate lands in a queue as a typed record;
a human acts on it; the action is logged. Nothing ships without a
recorded approval.

The shape is generic across content types:

- a `candidate` is whatever the upstream agent produced (a YAML test
  case, a Markdown memory update, a draft contract clause)
- a `promotion-record` carries the candidate, its provenance, the
  diff against current state, and the reviewer's verdict
- a `target` is where an approved candidate goes (a file path, a
  GitHub PR, a Substack post)

ReviewQueue does not generate candidates. It receives them. The CLI is
the queue plus the verdict-recorder plus the publisher.

## Who uses it

Editorial ops at AI-content publishers. Prompt-engineering teams at
firms maintaining one hundred or more prompts or skills. Knowledge-base
maintainers at companies running RAG over internal docs. Anyone who
has reinvented this badly in Jira, Notion, or Asana.

## Why now

Every team running production AI has rebuilt this primitive informally,
without typed-artifact discipline or provenance. The dream-promotion
discipline from the CDCP operating model is exactly the missing
primitive. Existing tools (Notion AI, Anthropic Workbench) treat the
queue as a UI feature, not as a typed primitive with a schema.

## Status

v0.1 shipped and runs end to end. The CLI is fully wired: `show`,
`validate`, `submit`, `list`, `decide`, `publish`, `score`, and `report`
all run. Four committed promotion-records (one pending, one approved, one
rejected, one published) ship under `queue/`, `decided/`, and `examples/`
so the queue is demonstrable without a manual submit. See
`specs/0002-design/` for the v0.1 scope and `STATUS.md` for the
next-feature queue.

## How to run

No-arg readable view of the committed queue (rows awaiting a verdict
first, then most recent):

```
python -m review_queue show
```

The rest of the verbs:

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

## live demo

A Streamlit page renders the same human-gate queue interactively: status
metrics, a ranked queue table, and a record inspector (pick a record, see
its diff, provenance, and verdicts). It reads the committed records
directly - no network, no secrets.

Run it locally:

```
python -m uv run --with streamlit streamlit run streamlit_app.py
# or, if streamlit + this repo are installed:
streamlit run streamlit_app.py
```

Deploy on Streamlit Community Cloud: New app -> repo
`AthenaTheOwl/review-queue`, branch `main`, main file `streamlit_app.py`.
The root `requirements.txt` pins `streamlit` plus this repo (`.`).

<!-- live url: (paste the Streamlit Community Cloud URL here once deployed) -->

## Layout

```
review-queue/
  README.md
  LICENSE
  AGENTS.md
  .gitignore
  specs/
    0001-foundation/
      requirements.md
      design.md
      tasks.md
      acceptance.md
  docs/
    first-pr.md
```

Future directories (named in specs, not created yet):

- `review_queue/` — CLI and runtime
- `schemas/` — promotion-record, candidate, target schemas
- `queue/` — typed records, one file per pending candidate
- `decided/` — typed records for approved / rejected candidates
- `examples/` — example promotion records demonstrating the shape

## License

MIT. See [LICENSE](LICENSE).
