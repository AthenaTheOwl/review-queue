# STATUS — review-queue

Snapshot of where the repo stands at v0.1. The three sections below are
the contract surface; downstream factory runs read them as input.

## Current state

- Product brief landed at `PRODUCT_BRIEF.md`; system map at
  `SYSTEM_MAP.md`; methodology at `docs/METHODOLOGY.md`. The
  methodology grew a `## What revisits this` section naming the three
  triggers under which the scoring rules (not the numbers) are
  revisited.
- Producer half (carryover from the scaffold): `submit`, `list`,
  `decide`, `publish` CLI commands writing typed promotion-record
  Markdown files under `queue/` and `decided/`, validated against
  `schemas/promotion-record.schema.json` (draft 2020-12).
- Consumer half (new this round): `review_queue.score` computes
  approve-unchanged rate, edit rate, reject rate, and median verdict
  latency over the row set. `review_queue.ledger` reads and appends
  JSONL runs at `data/ledger/runs.jsonl`. `review_queue.report` formats
  ledger rows as a human-readable block.
- CLI commands `score` and `report` are wired through
  `python -m review_queue`. `score --dry-run` computes without
  appending; `report --record-type X` filters the ledger view.
- First scoring run is checked in at `data/ledger/runs.jsonl` line 1:
  `record_type=memory-update`, `sample_count=1`,
  `approve_unchanged_rate=1.0`, `median_latency_seconds=1576`,
  `auto_promote_eligible=false` (below DEC-RQ-001's twenty-row
  threshold).
- First calibration row at `examples/rec-2026-08-14-001.md` is the
  source data for that scoring run; it validates against the schema
  and contributes one row to the `memory-update` row set.
- Gates: `scripts/validate_schemas.py`, `scripts/validate_records.py`,
  `scripts/validate_decisions.py`, `scripts/voice_lint.py` all exit
  zero on a clean tree. The `tests/test_scoring.py` suite covers the
  four scoring metrics, ledger append/read, and the row-eligibility
  exclusions named in `docs/METHODOLOGY.md`.
- Package layout: `review_queue/` at repo root is editable-installed
  via the `[tool.uv] package = true` block in `pyproject.toml`; dev
  deps live under `[dependency-groups]`. `python -m uv sync` plus
  `python -m uv run pytest` is the canonical local-gate invocation.

## Known limits

- The scoring run pulls records from `queue/`, `decided/`, and
  `examples/`. There is no separate calibration set — the checked-in
  example row is the seed of the row set.
- Only `file://` publish is wired end-to-end; `repo://` is parsed but
  the publisher exits with a stub message.
- No GitHub PR target, no Substack target. Both are deferred to spec
  0004 per the requirements ledger.
- The `decide` command does not yet enforce reviewer identity. Any
  string passed to `--reviewer` is accepted. Methodology says drop
  self-review rows, but the CLI does not enforce that filter at
  ingestion.
- No multi-reviewer consensus. A single verdict flips status.
- The diff field is computed by the caller for v0; the submitter
  helper only handles plain text candidates against an empty current
  state. Structured JSON-patch diffs are accepted but not generated.
- `voice_lint` runs on `docs/` and `examples/` only; it does not yet
  scan the source tree.
- No web UI. The CLI is the surface.
- The ledger is append-only but unguarded against concurrent writers.
  The cadence (monthly or quarterly, one human at the keyboard) makes
  this acceptable for v0.1.

## Next feature queue

- Land `repo://` target publisher; clone-or-fetch local cache under
  `data/cache/`, write the candidate at the target path, open a working
  branch.
- Add `scripts/provenance_check.py` enforcing every approved record
  carries a non-empty, URI-shaped provenance ref. Wire into the gate
  set.
- Add reviewer-identity enforcement in `decide`: require the
  `--reviewer` value to match a known entry in `reviewers.yaml`, and
  surface a self-review flag the scoring run can drop.
- Add structured diff support: when the candidate is JSON or YAML,
  compute a JSON Patch (RFC 6902) instead of a unified text diff.
- Add per-record-type latency thresholds to the scoring report so
  `report` flags rows that crossed the methodology's heuristic
  ceilings (30 minutes for `memory-update`, 2 hours for
  `contract-clause`).
- Add a second calibration ledger row exercising the `edit` verdict
  path (one record approved with an `edit_diff`, the original marked
  `superseded`) and a corresponding scoring run row demonstrating a
  non-1.0 approve-unchanged rate.
- Land DEC-RQ-002 documenting the target-scheme decision and the
  conditions under which GitHub PR targets become safe to add.

- Resolve factory defect: missing PRODUCT_BRIEF.md,SYSTEM_MAP.md
- Resolve factory defect: missing data/ledger/*.jsonl
- Resolve factory defect: METHODOLOGY.md missing revisit section
- Resolve factory defect: PRODUCT_BRIEF.md is required for active repos
- Resolve factory defect: SYSTEM_MAP.md is required for active repos
- Resolve factory defect: expected file 'PRODUCT_BRIEF.md' is missing
- Resolve factory defect: expected file 'SYSTEM_MAP.md' is missing
- Resolve factory defect: expected file 'review_queue/cli.py' is missing
- Resolve factory defect: expected file 'review_queue/score.py' is missing
- Resolve factory defect: expected file 'review_queue/ledger.py' is missing
- Resolve factory defect: expected glob 'data/ledger/*.jsonl' matched no files
- Resolve factory defect: module 'cli' declares source 'review_queue/cli.py', but it is missing
- Resolve factory defect: module 'score' declares source 'review_queue/score.py', but it is missing
- Resolve factory defect: module 'ledger' declares source 'review_queue/ledger.py', but it is missing
- Resolve factory defect: module 'report' declares source 'review_queue/report.py', but it is missing
- Resolve factory defect: claude_code review requested patch; inspect defect log
- Resolve factory defect: expected file 'review_queue/cli.py' is missing
- Resolve factory defect: expected file 'review_queue/score.py' is missing
- Resolve factory defect: expected file 'review_queue/ledger.py' is missing
- Resolve factory defect: module 'cli' declares source 'review_queue/cli.py', but it is missing
- Resolve factory defect: module 'score' declares source 'review_queue/score.py', but it is missing
- Resolve factory defect: module 'ledger' declares source 'review_queue/ledger.py', but it is missing
- Resolve factory defect: module 'report' declares source 'review_queue/report.py', but it is missing
- Resolve factory defect: claude_code review requested patch; inspect defect log
