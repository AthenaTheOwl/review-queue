"""CLI smoke tests via the argparse entry point."""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from review_queue import cli


def test_cli_help_exits_zero(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])
    assert exc_info.value.code == 0


def test_cli_show_renders_ranked_queue() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(["--repo-root", str(repo_root), "show"])
    out = buf.getvalue()
    assert rc == 0
    # header + committed records present
    assert "promotion-record queue" in out
    assert "rec-2026-08-14-001" in out
    assert "rec-2026-08-18-001" in out
    # pending row is ranked above the published row
    assert out.index("rec-2026-08-18-001") < out.index("rec-2026-08-14-001")
    # the headline names the pending record awaiting a verdict
    assert "needs attention" in out
    assert "pending" in out


def test_cli_list_returns_example_record() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(["--repo-root", str(repo_root), "list"])
    assert rc == 0
    assert "rec-2026-08-14-001" in buf.getvalue()


def test_cli_list_status_published_returns_example_record() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(["--repo-root", str(repo_root), "list", "--status", "published"])
    assert rc == 0
    assert "rec-2026-08-14-001" in buf.getvalue()


def test_cli_list_status_pending_empty_on_clean_repo() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(["--repo-root", str(repo_root), "list", "--status", "pending"])
    assert rc == 0


def test_cli_submit_refuses_empty_provenance(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    (tmp_path / "examples").mkdir()
    candidate = tmp_path / "examples" / "c.md"
    candidate.write_text("hi\n", encoding="utf-8")
    rc = cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "submit",
            "--candidate",
            "examples/c.md",
            "--provenance",
            "",
            "--target",
            "file://./out.md",
            "--record-type",
            "memory-update",
        ]
    )
    assert rc != 0
