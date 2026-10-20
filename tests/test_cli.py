"""CLI smoke tests via the argparse entry point."""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from review_queue import cli
from review_queue import records as records_mod


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


def test_cli_edit_verdict_publishes_the_edited_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Committed records hold a repo-relative candidate_ref, so decide has to
    # resolve it against --repo-root, not the shell's working directory.
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "c.md").write_text("alpha\nbeta\n", encoding="utf-8")
    root = ["--repo-root", str(tmp_path)]
    assert cli.main(root + ["submit", "--candidate", "examples/c.md",
                            "--provenance", "trace://test/run/cli-edit",
                            "--target", "file://./out.md"]) == 0
    (rec_path,) = (tmp_path / "queue").glob("rec-*.md")
    rec = records_mod.load(rec_path)
    rec.fm["candidate_ref"] = "examples/c.md"
    records_mod.save(rec)
    monkeypatch.chdir(tmp_path.parent)
    edit = "@@ -2 +2 @@\n-beta\n+beta, edited\n"
    assert cli.main(root + ["decide", "--record-id", rec.id, "--verdict", "edit",
                            "--reviewer", "reviewer", "--edit-diff", edit]) == 0
    assert cli.main(root + ["publish", "--record-id", rec.id]) == 0
    assert (tmp_path / "out.md").read_bytes() == b"alpha\nbeta, edited\n"


def test_cli_edit_verdict_refuses_a_diff_that_does_not_apply(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "c.md").write_text("alpha\n", encoding="utf-8")
    root = ["--repo-root", str(tmp_path)]
    assert cli.main(root + ["submit", "--candidate", "examples/c.md",
                            "--provenance", "trace://test/run/cli-bad-edit",
                            "--target", "file://./out.md"]) == 0
    (rec_path,) = (tmp_path / "queue").glob("rec-*.md")
    rc = cli.main(root + ["decide", "--record-id", rec_path.stem, "--verdict", "edit",
                          "--reviewer", "reviewer", "--edit-diff=-alpha\n+gamma\n"])
    assert rc == 2
    assert "no @@ hunk" in capsys.readouterr().err
    assert records_mod.load(rec_path).fm["status"] == "pending"


def test_cli_publish_refuses_a_legacy_edit_and_asks_for_re_review(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "c.md").write_text("alpha\nbeta\n", encoding="utf-8")
    root = ["--repo-root", str(tmp_path)]
    assert cli.main(root + ["submit", "--candidate", "examples/c.md",
                            "--provenance", "trace://test/run/cli-legacy-edit",
                            "--target", "file://./out.md"]) == 0
    (rec_path,) = (tmp_path / "queue").glob("rec-*.md")
    rec = records_mod.load(rec_path)
    rec.fm["candidate_ref"] = "examples/c.md"
    rec.fm.pop("candidate_sha256")
    records_mod.save(rec)
    assert cli.main(root + ["decide", "--record-id", rec.id, "--verdict", "edit",
                            "--reviewer", "reviewer",
                            "--edit-diff", "@@ -2 +2 @@\n-beta\n+beta, edited\n"]) == 0
    capsys.readouterr()
    assert cli.main(root + ["publish", "--record-id", rec.id]) == 2
    err = capsys.readouterr().err
    assert "treated as not approved" in err
    assert "re-review" in err
    assert not (tmp_path / "out.md").exists()
    assert records_mod.load(rec_path).fm["status"] == "approved"


def test_cli_decide_refuses_a_blank_reviewer(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "c.md").write_text("alpha\n", encoding="utf-8")
    root = ["--repo-root", str(tmp_path)]
    assert cli.main(root + ["submit", "--candidate", "examples/c.md",
                            "--provenance", "trace://test/run/cli-reviewer",
                            "--target", "file://./out.md"]) == 0
    (rec_path,) = (tmp_path / "queue").glob("rec-*.md")
    rc = cli.main(root + ["decide", "--record-id", rec_path.stem, "--verdict", "approve", "--reviewer", "   "])
    assert rc == 2
    assert "reviewer is required" in capsys.readouterr().err
    assert records_mod.load(rec_path).fm["status"] == "pending"
