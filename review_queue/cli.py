"""CLI entry point: python -m review_queue ..."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from review_queue import decide as decide_mod
from review_queue import (
    ledger as ledger_mod,
    list_cmd,
    publish as publish_mod,
    records as records_mod,
    report as report_mod,
    schema as schema_mod,
    score as score_mod,
    state as state_mod,
    submit as submit_mod,
)


def _default_roots(repo_root: Path) -> list[Path]:
    return [repo_root / "queue", repo_root / "decided", repo_root / "examples"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="review_queue",
        description="Human-gated promotion workflow for AI-generated candidates.",
    )
    p.add_argument(
        "--repo-root",
        default=".",
        help="Repo root directory (defaults to cwd).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "validate",
        help=(
            "Validate every committed promotion-record under queue/, decided/, "
            "and examples/ against the schema and state machine. No args needed."
        ),
    )

    s = sub.add_parser("submit", help="Wrap a candidate in a promotion-record.")
    s.add_argument("--candidate", required=True, help="Path to the candidate file.")
    s.add_argument(
        "--provenance",
        required=True,
        help="URI-shaped reference to the producing agent run. Required.",
    )
    s.add_argument(
        "--target",
        required=True,
        help="Target URI (file://path or repo://name/path).",
    )
    s.add_argument(
        "--record-type",
        default="memory-update",
        help="One of: memory-update, test-case, skill, brief, contract-clause, post.",
    )
    s.add_argument(
        "--target-path-for-diff",
        default=None,
        help="Optional path to the current target file used as the diff base.",
    )

    L = sub.add_parser("list", help="List records, optionally filtered.")
    L.add_argument("--status", default=None)
    L.add_argument("--record-type", default=None)
    L.add_argument("--reviewer", default=None)

    d = sub.add_parser("decide", help="Record a verdict on a queued record.")
    d.add_argument("--record-id", required=True)
    d.add_argument("--verdict", required=True, choices=["approve", "reject", "edit"])
    d.add_argument("--reviewer", required=True)
    d.add_argument("--edit-diff", default=None)
    d.add_argument("--note", default=None)

    pub = sub.add_parser("publish", help="Ship an approved record to its target.")
    pub.add_argument("--record-id", required=True)

    sc = sub.add_parser(
        "score",
        help="Score the calibration row set and append a run to data/ledger/runs.jsonl.",
    )
    sc.add_argument(
        "--record-type",
        default=None,
        help="Optional record_type filter (e.g. memory-update).",
    )
    sc.add_argument(
        "--ledger",
        default=None,
        help="Path to the JSONL ledger (defaults to data/ledger/runs.jsonl).",
    )
    sc.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print the score without appending to the ledger.",
    )
    sc.add_argument(
        "--note",
        default=None,
        help="Optional human note attached to the ledger row.",
    )

    rp = sub.add_parser(
        "report",
        help="Print the calibration ledger as a human-readable report.",
    )
    rp.add_argument(
        "--record-type",
        default=None,
        help="Optional record_type filter for displayed rows.",
    )
    rp.add_argument(
        "--ledger",
        default=None,
        help="Path to the JSONL ledger (defaults to data/ledger/runs.jsonl).",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if args.command == "validate":
        roots = _default_roots(repo_root)
        records = records_mod.iter_records(roots)
        if not records:
            print("validate: no records found under queue/, decided/, or examples/")
            return 0
        failures: list[str] = []
        for r in records:
            try:
                rel = r.path.relative_to(repo_root)
            except ValueError:
                rel = r.path
            try:
                schema_mod.validate(r.fm)
                state_mod.consistency_check(r.fm)
            except (schema_mod.SchemaError, state_mod.TransitionError) as exc:
                failures.append(f"{rel}: {exc}")
                continue
            print(f"ok   {rel}")
        if failures:
            for f in failures:
                print(f"FAIL {f}", file=sys.stderr)
            return 1
        print(f"validate: OK  {len(records)} record(s)")
        return 0

    if args.command == "submit":
        candidate_path = (repo_root / args.candidate).resolve()
        target_path = (
            (repo_root / args.target_path_for_diff).resolve()
            if args.target_path_for_diff
            else None
        )
        queue_dir = repo_root / "queue"
        try:
            rec = submit_mod.submit(
                candidate_path=candidate_path,
                provenance_ref=args.provenance,
                target=args.target,
                record_type=args.record_type,
                queue_dir=queue_dir,
                target_path_for_diff=target_path,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"submit failed: {exc}", file=sys.stderr)
            return 2
        print(f"submitted: {rec.id} -> {rec.path}")
        return 0

    if args.command == "list":
        roots = _default_roots(repo_root)
        records = list_cmd.list_records(
            roots=roots,
            status=args.status,
            record_type=args.record_type,
            reviewer=args.reviewer,
        )
        for r in records:
            print(list_cmd.format_row(r))
        return 0

    if args.command == "decide":
        roots = [repo_root / "queue"]
        try:
            rec = decide_mod.decide(
                record_id=args.record_id,
                decision=args.verdict,
                reviewer=args.reviewer,
                edit_diff=args.edit_diff,
                note=args.note,
                search_roots=roots,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"decide failed: {exc}", file=sys.stderr)
            return 2
        print(f"decided: {rec.id} status={rec.fm['status']}")
        return 0

    if args.command == "publish":
        queue_dir = repo_root / "queue"
        decided_dir = repo_root / "decided"
        try:
            rec = publish_mod.publish(
                record_id=args.record_id,
                queue_dir=queue_dir,
                decided_dir=decided_dir,
                repo_root=repo_root,
            )
        except (publish_mod.PublishError, FileNotFoundError) as exc:
            print(f"publish failed: {exc}", file=sys.stderr)
            return 2
        print(f"published: {rec.id} -> {rec.path}")
        return 0

    if args.command == "score":
        ledger_path = (
            Path(args.ledger).resolve()
            if args.ledger
            else repo_root / "data" / "ledger" / "runs.jsonl"
        )
        roots = _default_roots(repo_root)
        records = records_mod.iter_records(roots)
        score_dict = score_mod.score_records(records, record_type=args.record_type)
        if args.dry_run:
            row = dict(score_dict)
            row["auto_promote_eligible"] = score_mod.is_auto_promote_eligible(score_dict)
            row["auto_promote_threshold"] = score_mod.AUTO_PROMOTE_THRESHOLD
            print(report_mod.format_run(row))
            return 0
        row = ledger_mod.append_run(
            ledger_path,
            score_dict,
            threshold=score_mod.AUTO_PROMOTE_THRESHOLD,
            notes=args.note,
        )
        print(report_mod.format_run(row))
        return 0

    if args.command == "report":
        ledger_path = (
            Path(args.ledger).resolve()
            if args.ledger
            else repo_root / "data" / "ledger" / "runs.jsonl"
        )
        rows = ledger_mod.read_runs(ledger_path)
        if args.record_type:
            rows = [r for r in rows if r.get("record_type") == args.record_type]
        print(report_mod.format_report(rows))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
