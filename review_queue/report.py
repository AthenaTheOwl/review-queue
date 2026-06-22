"""report: format scoring runs for human consumption.

Reads a list of run rows (as returned by `review_queue.ledger.read_runs`)
and emits a plain-text report. The CLI wires this to stdout.
"""
from __future__ import annotations

from typing import Any, Iterable


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return "  --  "
    return f"{100.0 * x:5.1f}%"


def _fmt_secs(x: int | None) -> str:
    if x is None:
        return "    --"
    return f"{x:>6d}s"


def format_run(row: dict[str, Any]) -> str:
    """Format a single ledger row as a multi-line report block."""
    rtype = row.get("record_type") or "<all>"
    lines = [
        f"run_id:                  {row.get('run_id', '?')}",
        f"scored_at:               {row.get('scored_at', '?')}",
        f"record_type:             {rtype}",
        f"sample_count:            {row.get('sample_count', 0)}",
        f"approve_unchanged_rate:  {_fmt_pct(row.get('approve_unchanged_rate'))}",
        f"edit_rate:               {_fmt_pct(row.get('edit_rate'))}",
        f"reject_rate:             {_fmt_pct(row.get('reject_rate'))}",
        f"median_latency:          {_fmt_secs(row.get('median_latency_seconds'))}",
    ]
    if "auto_promote_eligible" in row:
        eligible = "YES" if row["auto_promote_eligible"] else "no"
        lines.append(f"auto_promote_eligible:   {eligible}")
        thresh = row.get("auto_promote_threshold", {})
        if thresh:
            lines.append(
                f"  threshold:             "
                f"min_samples={thresh.get('min_samples')}, "
                f"min_approve_rate={thresh.get('min_approve_unchanged_rate')}, "
                f"source={thresh.get('source')}"
            )
    records = row.get("records") or []
    if records:
        lines.append("contributing records:")
        for r in records:
            lines.append(f"  - {r}")
    if row.get("notes"):
        lines.append(f"notes: {row['notes']}")
    return "\n".join(lines)


def format_report(rows: Iterable[dict[str, Any]]) -> str:
    blocks = [format_run(r) for r in rows]
    if not blocks:
        return "(no scoring runs in ledger)"
    sep = "\n" + ("-" * 60) + "\n"
    return sep.join(blocks)
