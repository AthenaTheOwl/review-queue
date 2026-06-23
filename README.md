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


v0.1 shipped and runs end to end. The entry command `python -m review_queue validate` runs. See `specs/0002-design/` for the v0.1 scope and `STATUS.md` (where present) for the current state and next-feature queue.

## How to run

Placeholder; will land in spec 0002. v0 ships the schema, the CLI
skeleton, and one example promotion-record under
`examples/` showing the shape. The CLI commands are not yet wired.

The eventual CLI shape (target for spec 0003):

```
python -m review_queue submit --candidate path/to/candidate.yaml --provenance trace.json
python -m review_queue list --status pending
python -m review_queue decide --record-id <id> --verdict approved --reviewer vignesh
python -m review_queue publish --record-id <id>
```

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
