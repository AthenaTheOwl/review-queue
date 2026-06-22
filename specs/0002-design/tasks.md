# Tasks — 0002 Design ledger

What v0.1 ships. The boxes below match the files actually in the
repo; this is the design ledger, not a plan-of-record.

## Done in this spec

- [x] `pyproject.toml` with `[tool.uv] package = true` and `[dependency-groups]` dev block
- [x] `review_queue/__init__.py` + `__main__.py`
- [x] `review_queue/frontmatter.py` — stdlib-only narrow-YAML parser
- [x] `review_queue/records.py` — Record dataclass, load/save/iter/find
- [x] `review_queue/schema.py` — in-code validator
- [x] `review_queue/state.py` — state machine + consistency check
- [x] `review_queue/submit.py` — submit command
- [x] `review_queue/list_cmd.py` — list command
- [x] `review_queue/decide.py` — decide command
- [x] `review_queue/publish.py` — publish command for `file://`
- [x] `review_queue/cli.py` — argparse front door
- [x] `scripts/validate_schemas.py`
- [x] `scripts/validate_records.py`
- [x] `scripts/validate_decisions.py`
- [x] `scripts/voice_lint.py`
- [x] `examples/rec-2026-08-14-001.md` — first calibration ledger row
- [x] `decisions/DEC-RQ-001-human-gate-default.md`
- [x] `docs/methodology.md`
- [x] `docs/system-map.md`
- [x] `docs/calibration/memory-update.md`
- [x] `tests/` covering frontmatter, schema, state, submit/decide/publish

## Deferred to spec 0003

- [ ] `repo://` publish end-to-end
- [ ] `scripts/provenance_check.py` as a separate gate
- [ ] Structured JSON-patch diff support in submit
- [ ] Reviewer-identity registry under `reviewers.yaml`
- [ ] Second calibration row exercising the `edit` verdict path

## Deferred to spec 0004

- [ ] GitHub PR target
- [ ] Substack target
- [ ] Multi-reviewer consensus
