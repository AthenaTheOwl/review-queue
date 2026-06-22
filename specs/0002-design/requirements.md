# Requirements — 0002 Design ledger

Spec 0002 turns the foundation schema into a runnable CLI plus the
calibration discipline that lets ReviewQueue evolve. R-RQ-001 through
R-RQ-010 still hold; this spec adds R-RQ-011 through R-RQ-020.

## CLI behavior

- **R-RQ-011** `submit` writes a record under `queue/<id>.md` with
  `status: pending`. The id is allocated as `rec-<YYYY-MM-DD>-NNN`
  where NNN is the next free integer for that date.
- **R-RQ-012** `submit` exits non-zero when `--provenance` is empty,
  whitespace-only, or not URI-shaped (no scheme prefix). This is the
  same constraint named in R-RQ-004 lifted to the CLI surface.
- **R-RQ-013** `list --status pending` returns only pending records.
  `list` with no filter returns every record across `queue/`,
  `decided/`, and `examples/`, sorted by `created_at`.
- **R-RQ-014** `decide` rejects state transitions outside the design
  state machine. Attempting `pending -> published` exits non-zero and
  does not mutate the record on disk.
- **R-RQ-015** `decide --verdict edit` requires `--edit-diff`; the
  record's status flips to `approved` and the verdict carries the
  edit_diff field.
- **R-RQ-016** `publish` is implemented end-to-end for `file://`
  targets. `repo://` targets parse but exit with a stub message. The
  record moves from `queue/` to `decided/` on success.

## Calibration

- **R-RQ-017** Every published record contributes one row to the
  calibration set for its record_type. The row carries the reviewer
  verdict, the verdict latency (created_at to first decided_at), and
  whether the candidate shipped unchanged or via an edit.
- **R-RQ-018** The calibration set lives at
  `docs/calibration/<record_type>.md`; one section per record_type,
  one bullet per row. Auto-promote opt-in for a record_type cannot
  be considered until its calibration set has at least twenty rows
  meeting the DEC-RQ-001 conditions.

## Methodology

- **R-RQ-019** `docs/methodology.md` documents the scoring/calibration
  approach: what counts as a row, what the approve-unchanged rate
  means, and how verdict latency is computed. The methodology is the
  contract against which future record_types are added.

## Governance

- **R-RQ-020** A new record_type is added by extending the schema
  enum, landing a candidate-shape entry in `candidate.schema.json`,
  and recording the change in a DEC entry. The CLI's `record_type`
  argument is open and accepts any string at v0; future versions may
  tighten this.
