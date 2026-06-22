# Design — 0002 Design ledger

Spec 0002 wires the schema from 0001 into a runnable Python CLI and
adds the calibration discipline that distinguishes ReviewQueue from a
generic checkbox tool.

## Module layout

```
review_queue/
  __init__.py
  __main__.py        # python -m review_queue
  cli.py             # argparse front door
  frontmatter.py     # narrow YAML subset parser (stdlib only)
  records.py         # Record dataclass; load, save, iter, find
  schema.py          # in-code validator mirroring schemas/*.json
  state.py           # state machine + consistency_check
  submit.py          # submit command logic
  list_cmd.py        # list command logic
  decide.py          # decide command logic
  publish.py         # publish command logic
  diff.py            # unified-text-diff helper
```

The package is editable-installed by uv (via `[tool.uv] package = true`
in pyproject.toml). `python -m review_queue` is the canonical entry
point; `review-queue` is a script alias.

## Why stdlib only

The runtime carries no external dependencies. The reasoning: this is a
control-plane tool, not a hot path. Adding PyYAML, jsonschema, or a
diff library would push install-time risk onto every consumer for
features the CLI does not need. The narrow YAML subset in
`frontmatter.py` covers the record shape the schema constrains;
anything outside that subset is a schema violation that should fail
loudly, not be silently parsed.

## Submit flow

1. CLI parses `--candidate`, `--provenance`, `--target`, `--record-type`.
2. Submit allocates the next id for today.
3. The candidate text is read; the diff against `--target-path-for-diff`
   (or against `/dev/null` if absent) is computed via `difflib.unified_diff`.
4. Front-matter is assembled and validated against `schema.py`.
5. The record is written to `queue/<id>.md`.

A record with an empty or non-URI provenance ref is refused at step 4
(`schema.SchemaError` propagates to a non-zero CLI exit).

## Decide flow

1. CLI parses `--record-id`, `--verdict`, `--reviewer`, optional
   `--edit-diff` and `--note`.
2. Decide looks up the record under `queue/`.
3. The target status is derived from the verdict (`approve`/`edit` -> 
   `approved`, `reject` -> `rejected`).
4. `state.assert_transition` confirms the current -> target hop is
   allowed; an illegal hop exits non-zero with the record unchanged.
5. A verdict entry is appended; the record is saved.

The state-machine check runs again after the mutation
(`state.consistency_check`) so a save cannot leave the record in a
verdicts/status mismatch.

## Publish flow

1. CLI parses `--record-id`.
2. Publish loads the record from `queue/`; refuses if status is not
   `approved`.
3. `file://` targets resolve to an absolute path (relative paths are
   resolved against the repo root).
4. The candidate body is read from `candidate_ref` and written to the
   target path.
5. The record's status flips to `published`; the record file moves
   from `queue/<id>.md` to `decided/<id>.md`.

`repo://` raises `PublishError` with a stub message naming the
deferred-to-next-spec status. The CLI prints the error and exits 2.

## Calibration ledger

Each published or decided record contributes to a calibration set
under `docs/calibration/<record_type>.md`. The row records the verdict
(`approve` unchanged, `edit`, `reject`), the verdict latency, and a
short reviewer note. The set is the input to the DEC-RQ-001 auto-
promote conditions; it is not yet enforced by a gate, but
`scripts/validate_records.py` already enforces the structural
invariants needed for the ledger to be parseable.

## Gates

The five gates that must pass for v0.1:

- `python -m pytest`
- `python scripts/voice_lint.py`
- `python scripts/validate_schemas.py`
- `python scripts/validate_records.py`
- `python scripts/validate_decisions.py`

All exit zero on a clean tree. The pytest suite covers the front-matter
parser, the schema validator, the state machine, and the submit /
decide / publish flows against a temporary repo root.

## Out of 0002 scope

- `repo://` publish (deferred to 0003)
- Multi-reviewer consensus
- A reviewer-identity registry
- Structured JSON-patch diffs
- Web UI
