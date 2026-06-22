"""ledger: read and append calibration runs in data/ledger/runs.jsonl.

The ledger is append-only JSONL. Each line is one scoring run. Reading
the ledger returns runs in file order (i.e., chronological by append).
This module owns the file format; callers pass plain dicts.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LEDGER_PATH = Path("data") / "ledger" / "runs.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _next_run_id(existing: list[dict[str, Any]], today: str) -> str:
    prefix = f"run-{today}-"
    n = 1
    for row in existing:
        rid = row.get("run_id", "")
        if rid.startswith(prefix):
            tail = rid[len(prefix):]
            try:
                n = max(n, int(tail) + 1)
            except ValueError:
                continue
    return f"{prefix}{n:03d}"


def read_runs(ledger_path: Path) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def append_run(
    ledger_path: Path,
    score_dict: dict[str, Any],
    *,
    threshold: dict[str, Any] | None = None,
    now: str | None = None,
    run_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Append a scoring run to the ledger. Returns the row that was written.

    The score_dict comes from `review_queue.score.score_records`. This
    function adds: `run_id`, `scored_at`, and (if provided) the
    `auto_promote_threshold` and `auto_promote_eligible` fields.
    """
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_runs(ledger_path)
    scored_at = now or _now_iso()
    rid = run_id or _next_run_id(existing, scored_at[:10])

    row: dict[str, Any] = {"run_id": rid, "scored_at": scored_at}
    row.update(score_dict)
    if threshold is not None:
        from review_queue.score import is_auto_promote_eligible

        row["auto_promote_eligible"] = is_auto_promote_eligible(score_dict)
        row["auto_promote_threshold"] = threshold
    if notes:
        row["notes"] = notes

    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=False) + "\n")
    return row
