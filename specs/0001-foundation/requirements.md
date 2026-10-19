# Requirements — 0001 Foundation

Numbered requirements for the v0 scaffold of review-queue. The R-RQ-*
prefix is the brand tag and appears in every downstream spec, decision,
and gate.

## Records

- **R-RQ-001** The repo ships a promotion-record schema under
  `schemas/promotion-record.schema.json`. Fields: `id`,
  `record_type`, `candidate_ref`, `provenance_ref`, `diff`,
  `status`, `target`, `created_at`, `verdicts[]`.
- **R-RQ-002** `record_type` is an open enum; v0 recognises
  `memory-update`, `test-case`, `skill`, `brief`, `contract-clause`,
  `post`. New types are added by extending the enum in a DEC entry.
- **R-RQ-003** `status` is one of `pending`, `approved`, `rejected`,
  `published`, `superseded`. State transitions are constrained:
  `pending -> approved -> published`, `pending -> rejected`,
  `approved -> superseded`.

## Provenance

- **R-RQ-004** Every record carries a `provenance_ref`. The ref is a
  URI-shaped string pointing at a trace, a run-evidence packet, or a
  CDCP event ledger entry. The CLI refuses to submit a record with an
  empty provenance ref.
- **R-RQ-005** A `diff` is required on every record. v0 supports a
  unified diff format for text candidates and a structured JSON patch
  for structured candidates. The diff is computed by the submitter,
  not by the reviewer.

## Verdicts

- **R-RQ-006** A verdict has fields `reviewer`, `decided_at`,
  `decision`, and optional `edit_diff`. `decision` is one of
  `approve`, `reject`, `edit`. `reviewer` is a self-asserted label,
  not an authenticated identity; `decide` trims it and requires 1-64
  characters, a letter, digit or underscore first, then letters,
  digits or `. _ @ + -`.
- **R-RQ-007** An `edit` decision attaches an `edit_diff` and is
  treated as an implicit `approve` against the edited candidate. The
  original candidate is marked `superseded`.
  v0 meets the approve half on the same record: the `edit_diff` is a
  unified diff that must apply cleanly to the submitted candidate,
  the record keeps the submitted bytes' `candidate_sha256` and adds
  the edited bytes' `approved_sha256`, and `publish` writes the edited
  bytes. A legacy record without `candidate_sha256` keeps the
  edit_diff as unchecked text and cannot be published until the
  candidate is resubmitted. Splitting the edited candidate into its
  own record and marking the original `superseded` is not wired yet.

## Targets

- **R-RQ-008** A `target` is a typed reference to where an approved
  record ships. v0 supports `file://` and `repo://` targets. Other
  scheme support (GitHub PR, Substack) is deferred to spec 0004.

## CLI

- **R-RQ-009** The CLI exposes `submit`, `list`, `decide`, and
  `publish`. v0 ships the command skeletons; behaviour lands in
  spec 0002.

## Governance

- **R-RQ-010** Architectural choices are recorded in
  `decisions/DEC-RQ-NNN-<slug>.md`. The first decision (DEC-RQ-001)
  justifies the human-gate default and lists the conditions under
  which auto-promote could later be enabled per record type.
